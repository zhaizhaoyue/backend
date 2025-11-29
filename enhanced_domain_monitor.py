"""
增强域名监控系统 - 多API查询 + who.is爬取 + 持续监控
"""
import asyncio
import json
import csv
import os
import re
import socket
import dns.resolver
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple
from pathlib import Path

import httpx
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout


class EnhancedDomainMonitor:
    """增强版域名监控器 - 多数据源 + 自动fallback"""
    
    # 官方WHOIS服务器地址
    WHOIS_SERVERS = {
        ".com": "whois.verisign-grs.com",
        ".net": "whois.verisign-grs.com",
        ".org": "whois.pir.org",
        ".nl": "whois.domain-registry.nl",
        ".be": "whois.dns.be",
        ".eu": "whois.eu",
        ".uk": "whois.nic.uk",
        ".de": "whois.denic.de",
        ".fr": "whois.nic.fr",
        ".it": "whois.nic.it",
        ".es": "whois.nic.es",
        ".pt": "whois.dns.pt",
        ".biz": "whois.biz",
        ".info": "whois.afilias.net",
        ".us": "whois.nic.us",
        ".ca": "whois.cira.ca",
        ".au": "whois.auda.org.au",
        ".jp": "whois.jprs.jp",
        ".cn": "whois.cnnic.cn",
        ".in": "whois.registry.in",
        ".io": "whois.nic.io",
        ".co": "whois.nic.co",
        ".me": "whois.nic.me",
        ".tv": "whois.nic.tv",
        ".cc": "whois.nic.cc",
        ".ws": "whois.website.ws",
        ".mobi": "whois.dotmobiregistry.net",
        ".pro": "whois.registry.pro",
        ".tel": "whois.nic.tel",
        ".travel": "whois.nic.travel",
        ".xxx": "whois.nic.xxx",
        ".asia": "whois.nic.asia",
        ".lu": "whois.dns.lu",
    }
    
    # 三个RDAP/WHOIS API端点（保留作为备用）
    RDAP_ENDPOINTS = {
        "primary": {
            ".com": "https://rdap.verisign.com/com/v1/domain/{}",
            ".net": "https://rdap.verisign.com/net/v1/domain/{}",
            ".org": "https://rdap.publicinterestregistry.org/rdap/domain/{}",
            ".nl": "https://rdap.sidn.nl/domain/{}",
            ".be": "https://rdap.dns.be/domain/{}",
            ".eu": "https://rdap.eu/domain/{}",
        },
        "secondary": {
            ".com": "https://rdap.arin.net/registry/domain/{}",
            ".net": "https://rdap.arin.net/registry/domain/{}",
        },
        "bootstrap": "https://rdap.org/domain/{}"  # RDAP Bootstrap
    }
    
    def __init__(self, api_ninjas_key: Optional[str] = None, deepseek_key: Optional[str] = None):
        """初始化监控器"""
        self.api_ninjas_key = api_ninjas_key or os.environ.get("API_NINJAS_KEY")
        self.deepseek_key = deepseek_key or os.environ.get("DEEPSEEK_API_KEY")
        self.timeout = httpx.Timeout(30.0)
        self.results_cache = {}
    
    def get_tld(self, domain: str) -> str:
        """提取TLD"""
        parts = domain.lower().split('.')
        if len(parts) >= 2:
            return '.' + parts[-1]
        return ''
    
    async def query_official_whois(self, domain: str) -> Dict:
        """直接查询官方WHOIS服务器
        
        Args:
            domain: 域名
            
        Returns:
            包含原始WHOIS文本的字典
        """
        tld = self.get_tld(domain)
        whois_server = self.WHOIS_SERVERS.get(tld, "whois.iana.org")
        
        print(f"      📡 查询官方WHOIS: {whois_server}")
        
        try:
            # 使用socket直接连接WHOIS服务器
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            # 连接WHOIS服务器（端口43）
            await asyncio.get_event_loop().run_in_executor(
                None, sock.connect, (whois_server, 43)
            )
            
            # 发送查询
            query = f"{domain}\r\n"
            await asyncio.get_event_loop().run_in_executor(
                None, sock.sendall, query.encode('utf-8')
            )
            
            # 接收响应
            response_parts = []
            while True:
                chunk = await asyncio.get_event_loop().run_in_executor(
                    None, sock.recv, 4096
                )
                if not chunk:
                    break
                response_parts.append(chunk.decode('utf-8', errors='ignore'))
            
            sock.close()
            
            whois_text = ''.join(response_parts)
            
            if not whois_text or len(whois_text) < 50:
                print(f"      ✗ WHOIS响应为空或太短")
                return {'source': 'official_whois', 'success': False, 'data': {}}
            
            print(f"      ✓ 获取WHOIS文本: {len(whois_text)} 字符")
            
            # 如果有DeepSeek，使用LLM解析
            if self.deepseek_key:
                print(f"      🤖 使用DeepSeek解析WHOIS...")
                llm_result = await self.parse_with_deepseek(whois_text, domain)
                
                if llm_result:
                    llm_result['raw_whois'] = whois_text[:1000]  # 保存前1000字符
                    llm_result['llm_parsed'] = True
                    return {'source': 'official_whois', 'success': True, 'data': llm_result}
            
            # 没有LLM，使用正则解析
            parsed = self._parse_raw_whois(whois_text)
            parsed['raw_whois'] = whois_text[:1000]
            parsed['llm_parsed'] = False
            
            has_data = any([
                parsed.get('registrar'),
                parsed.get('creation_date'),
                parsed.get('nameservers')
            ])
            
            return {'source': 'official_whois', 'success': has_data, 'data': parsed}
            
        except socket.timeout:
            print(f"      ✗ WHOIS查询超时")
            return {'source': 'official_whois', 'success': False, 'data': {}}
        except Exception as e:
            print(f"      ✗ WHOIS查询失败: {e}")
            return {'source': 'official_whois', 'success': False, 'data': {}}
    
    async def query_rdap_primary(self, domain: str) -> Dict:
        """查询主RDAP服务器"""
        tld = self.get_tld(domain)
        endpoint = self.RDAP_ENDPOINTS["primary"].get(tld)
        
        if not endpoint:
            return {'source': 'rdap_primary', 'success': False, 'data': {}}
        
        url = endpoint.format(domain)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    parsed = self._parse_rdap_response(data, url)
                    return {'source': 'rdap_primary', 'success': True, 'data': parsed}
        except:
            pass
        
        return {'source': 'rdap_primary', 'success': False, 'data': {}}
    
    async def query_rdap_bootstrap(self, domain: str) -> Dict:
        """查询RDAP Bootstrap服务"""
        url = self.RDAP_ENDPOINTS["bootstrap"].format(domain)
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    parsed = self._parse_rdap_response(data, url)
                    return {'source': 'rdap_bootstrap', 'success': True, 'data': parsed}
        except:
            pass
        
        return {'source': 'rdap_bootstrap', 'success': False, 'data': {}}
    
    def extract_whois_context(self, full_text: str, anchor_text: str = "Raw WHOIS", 
                             before_tokens: int = 100, after_tokens: int = 1900) -> Optional[str]:
        """提取Raw WHOIS附近的文本内容
        
        Args:
            full_text: 完整的页面文本
            anchor_text: 锚点文本
            before_tokens: 锚点前的token数（约等于单词数）
            after_tokens: 锚点后的token数
            
        Returns:
            提取的上下文文本
        """
        # 查找锚点位置
        patterns = [
            "Raw WHOIS responses from registry and registrar servers",
            "Raw WHOIS",
            "WHOIS Record",
            "Domain Information"
        ]
        
        anchor_pos = -1
        for pattern in patterns:
            pos = full_text.find(pattern)
            if pos != -1:
                anchor_pos = pos
                break
        
        if anchor_pos == -1:
            # 没找到锚点，尝试提取整个WHOIS部分
            return None
        
        # 简单的token分割（按空格和换行）
        words = full_text.split()
        
        # 计算锚点在words中的位置
        text_before_anchor = full_text[:anchor_pos]
        words_before = text_before_anchor.split()
        anchor_word_pos = len(words_before)
        
        # 提取上下文
        start_pos = max(0, anchor_word_pos - before_tokens)
        end_pos = min(len(words), anchor_word_pos + after_tokens)
        
        context_words = words[start_pos:end_pos]
        context = ' '.join(context_words)
        
        return context
    
    async def parse_with_deepseek(self, whois_text: str, domain: str, source_url: str = None) -> Dict:
        """使用DeepSeek LLM解析WHOIS文本
        
        Args:
            whois_text: WHOIS文本内容
            domain: 域名
            source_url: 数据源URL (可选)
            
        Returns:
            解析后的结构化数据
        """
        if not self.deepseek_key:
            return {}
        
        # 生成时间戳
        from datetime import datetime, timezone
        timestamp = datetime.now(timezone.utc).isoformat()
        
        # 如果没有提供source_url，使用默认值
        if not source_url:
            source_url = f"https://who.is/whois/{domain}"
        
        prompt = f"""You are a domain registration information extraction engine.

Goal

From the input below, extract domain registration facts into a STRICT JSON table.

You will receive:

1. A small metadata header:
   DATA_SOURCE: {source_url}
   QUERY_TIMESTAMP: {timestamp}

2. Raw HTML or plain text of a WHOIS / RDAP / registrar web page, including any legal notices, rate-limit warnings, or other noise.

Your tasks:

- Detect all domain records contained in the text. There may be one or multiple domains.
- For each domain, create ONE JSON object with the following fields:

  - domain                 (string)
  - registrant_organization (string or null)
  - registrar              (string or null)
  - registry               (string, the TLD with a leading dot, e.g. ".be", ".com")
  - creation_date          (string or null, preferred format "YYYY-MM-DD" if clearly given; otherwise copy the exact date string as-is)
  - expiry_date            (string or null, same rule as creation_date)
  - nameservers            (array of strings, each a nameserver hostname; empty array if none clearly present)
  - data_sources           (array of strings; must at least contain the value from DATA_SOURCE)
  - timestamp              (string; must exactly copy the value from QUERY_TIMESTAMP)

Output format (VERY IMPORTANT):
- Return ONLY a single JSON object, with this exact top-level structure:

{{
  "domains": [
    {{
      "domain": "example.com",
      "registrant_organization": null,
      "registrar": "Example Registrar Ltd.",
      "registry": ".com",
      "creation_date": "2015-06-24",
      "expiry_date": null,
      "nameservers": [
        "ns1.example.net",
        "ns2.example.net"
      ],
      "data_sources": [
        "https://www.example-registrar.com/whois/example.com"
      ],
      "timestamp": "{timestamp}"
    }}
  ]
}}

Extraction rules (CRITICAL):

1. Do NOT invent, infer, or guess values.
   - If a field is not explicitly present in the input, set it to:
     - null for scalar fields (registrant_organization, registrar, creation_date, expiry_date)
     - [] (empty array) for lists (nameservers, data_sources if DATA_SOURCE is missing for some reason).

2. Domain:
   - Use the exact domain labels as they appear in the record (e.g. "aholddelhaize.be").
   - If the page clearly contains only one domain, still output an array with one JSON object.

3. Registrar:
   - Use the value next to labels such as "Registrar:", "Registrar Name:", "Registrar Name" or similar.
   - Copy the registrar name as shown, without modification.

4. Registrant_organization:
   - Use the organization / company name of the registrant if it is explicitly provided under labels such as
     "Registrant Organization:", "Registrant:", "Holder:", "Domain holder", etc.
   - If only a person name or email is shown and it is not clearly an organization, you may still put the exact text
     into registrant_organization.
   - If the registrant is hidden, redacted, or not shown, set registrant_organization to null.
   - NEVER infer the registrant from brand names, website content, or your own knowledge.

5. Registry:
   - Derive from the domain's top-level domain:
       "aholddelhaize.be" -> ".be"
       "example.com"      -> ".com"
       "foo.org"          -> ".org"
   - Always include the leading dot.

6. Creation_date:
   - Look for labels such as "Creation Date", "Created On", "Registered:", "Registered On", "Domain registered:" etc.
   - If multiple date formats appear for the same field, pick the one most clearly linked to domain creation.
   - If the date is clearly a standard format (e.g. "2015-06-24"), keep it as is.
   - If the date is a long string (e.g. "Wed Jun 24 2015"), you may either:
       (a) normalize to "2015-06-24" if it is unambiguous, OR
       (b) copy the full original string.
   - If no creation date is present, set creation_date to null.

7. Expiry_date:
   - Look for labels such as "Expiry Date", "Expiration Date", "Registry Expiry Date", "Renewal date", etc.
   - Apply the same formatting rules as for creation_date.
   - If no expiry date is present, set expiry_date to null.

8. Nameservers:
   - Collect all hostnames under labels such as "Name Server", "Nameservers", "Name servers", etc.
   - Normalize by trimming spaces; keep them as plain strings (no need to lower-case, but you may do so).
   - If no nameservers are clearly listed, use an empty array.

9. Data_sources:
   - Always include the exact string from DATA_SOURCE as one element of the array.
   - If the input text itself clearly lists additional sources (for example: "Data from registry X and registrar Y"), you may add those as extra array elements, but only if they are explicitly named.
   - NEVER fabricate additional sources.

10. Timestamp:
   - Copy the value from QUERY_TIMESTAMP exactly, without modification or reformatting.
   - Do NOT generate your own timestamps.

11. Ignore noise:
   - Completely ignore WHOIS legal disclaimers, terms of use, anti-spam policies, and rate-limit messages.
   - Do NOT place disclaimer text into any field.

12. If the input contains zero recognizable domains:
   - Return {{"domains": []}}

The raw input starts after the line:
=====BEGIN INPUT=====
and ends before the line:
=====END INPUT=====

Now read the input and return ONLY the JSON described above.

=====BEGIN INPUT=====
{whois_text}
=====END INPUT====="""

        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
                response = await client.post(
                    "https://api.deepseek.com/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.deepseek_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "deepseek-chat",
                        "messages": [
                            {
                                "role": "user",
                                "content": prompt
                            }
                        ],
                        "temperature": 0.1,
                        "max_tokens": 1000
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                    
                    # 提取JSON
                    # 尝试找到JSON对象
                    import json as json_module
                    
                    # 清理可能的markdown标记
                    content = content.replace('```json', '').replace('```', '').strip()
                    
                    try:
                        parsed = json_module.loads(content)
                        
                        # 新的prompt返回 {"domains": [...]} 结构
                        # 提取第一个domain并转换为旧格式以兼容现有代码
                        if 'domains' in parsed and len(parsed['domains']) > 0:
                            domain_data = parsed['domains'][0]
                            
                            # 映射字段名称 (新格式 -> 旧格式)
                            result = {
                                'registrar': domain_data.get('registrar'),
                                'registry': domain_data.get('registry'),
                                'registrant_org': domain_data.get('registrant_organization'),  # 映射到旧字段名
                                'creation_date': domain_data.get('creation_date'),
                                'expiry_date': domain_data.get('expiry_date'),
                                'nameservers': domain_data.get('nameservers', []),
                                'data_source': domain_data.get('data_sources', [source_url])[0] if domain_data.get('data_sources') else source_url,
                                'timestamp': domain_data.get('timestamp'),
                            }
                            
                            print(f"      ✓ DeepSeek解析成功")
                            return result
                        else:
                            print(f"      ⚠️ DeepSeek返回的JSON中没有domains字段或为空")
                            return {}
                    except Exception as e:
                        print(f"      ⚠️ DeepSeek返回的不是有效JSON: {e}")
                        return {}
                else:
                    print(f"      ⚠️ DeepSeek API错误: {response.status_code}")
                    return {}
        
        except Exception as e:
            print(f"      ⚠️ DeepSeek调用失败: {e}")
            return {}
    
    async def query_api_ninjas(self, domain: str) -> Dict:
        """查询API Ninjas WHOIS服务"""
        if not self.api_ninjas_key:
            return {'source': 'api_ninjas', 'success': False, 'data': {}}
        
        url = f"https://api.api-ninjas.com/v1/whois?domain={domain}"
        headers = {"X-Api-Key": self.api_ninjas_key}
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)
                if response.status_code == 200:
                    data = response.json()
                    parsed = self._parse_api_ninjas_response(data)
                    return {'source': 'api_ninjas', 'success': True, 'data': parsed}
        except:
            pass
        
        return {'source': 'api_ninjas', 'success': False, 'data': {}}
    
    async def scrape_whois_website(self, domain: str) -> Dict:
        """使用Playwright爬取who.is网站，并用DeepSeek LLM解析"""
        print(f"      🌐 使用Playwright爬取 who.is: {domain}")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
                )
                page = await context.new_page()
                
                # 访问who.is
                url = f"https://who.is/whois/{domain}"
                await page.goto(url, wait_until='networkidle', timeout=30000)
                
                # 等待页面完全加载
                await asyncio.sleep(5)
                
                # 获取整个页面文本
                page_text = await page.inner_text('body')
                
                # 提取数据
                result = {
                    'registrar': None,
                    'registrant_org': None,
                    'creation_date': None,
                    'expiry_date': None,
                    'nameservers': [],
                    'raw_whois': None,
                    'registry': None,
                    'status': [],
                    'llm_parsed': False
                }
                
                # 步骤1: 提取Raw WHOIS附近的文本
                whois_context = self.extract_whois_context(
                    page_text, 
                    "Raw WHOIS",
                    before_tokens=100,
                    after_tokens=1900
                )
                
                # 步骤2: 如果找到WHOIS上下文，使用DeepSeek解析
                if whois_context and self.deepseek_key:
                    print(f"      🤖 使用DeepSeek LLM解析WHOIS数据...")
                    llm_result = await self.parse_with_deepseek(whois_context, domain)
                    
                    if llm_result:
                        # 合并LLM解析的结果
                        for key, value in llm_result.items():
                            if value:  # 只使用非空值
                                result[key] = value
                        result['llm_parsed'] = True
                        result['raw_whois'] = whois_context[:500]  # 保存部分原始数据
                
                # 步骤3: 尝试直接提取Raw WHOIS数据区块（fallback）
                if not result['llm_parsed']:
                    try:
                        for selector in ['pre', 'code', '[class*="whois"]', '[class*="raw"]']:
                            try:
                                whois_text = await page.inner_text(selector, timeout=3000)
                                if whois_text and len(whois_text) > 100:
                                    result['raw_whois'] = whois_text
                                    
                                    # 如果有DeepSeek，尝试解析
                                    if self.deepseek_key:
                                        print(f"      🤖 使用DeepSeek解析Raw WHOIS块...")
                                        llm_result = await self.parse_with_deepseek(whois_text, domain)
                                        if llm_result:
                                            for key, value in llm_result.items():
                                                if value:
                                                    result[key] = value
                                            result['llm_parsed'] = True
                                    else:
                                        # 没有LLM，使用正则解析
                                        parsed = self._parse_raw_whois(whois_text)
                                        result.update(parsed)
                                    break
                            except:
                                continue
                    except:
                        pass
                
                # 步骤4: 从整个页面文本提取信息（最后的fallback）
                if not result['registrar']:
                    match = re.search(r'Registrar:\s*([^\n\r]+)', page_text, re.I)
                    if match:
                        result['registrar'] = match.group(1).strip()
                
                if not result['creation_date']:
                    match = re.search(r'(?:Created|Creation Date|Registered):\s*([^\n\r]+)', page_text, re.I)
                    if match:
                        result['creation_date'] = match.group(1).strip()
                
                if not result['expiry_date']:
                    match = re.search(r'(?:Expir[^:]*Date|Registry Expiry Date):\s*([^\n\r]+)', page_text, re.I)
                    if match:
                        result['expiry_date'] = match.group(1).strip()
                
                if not result['nameservers']:
                    ns_matches = re.findall(r'(?:Name Server|Nameserver):\s*([^\n\r]+)', page_text, re.I)
                    if ns_matches:
                        result['nameservers'] = [ns.strip() for ns in ns_matches[:10]]
                
                if not result['registry']:
                    match = re.search(r'Registry:\s*([^\n\r]+)', page_text, re.I)
                    if match:
                        result['registry'] = match.group(1).strip()
                
                await browser.close()
                
                # 检查是否获取到任何有用信息
                has_data = any([
                    result['registrar'],
                    result['creation_date'],
                    result['raw_whois'],
                    result['nameservers'],
                    result['registry']
                ])
                
                # 显示解析方式
                if result['llm_parsed']:
                    print(f"      ✓ LLM解析成功")
                elif has_data:
                    print(f"      ✓ 规则解析成功")
                
                return {'source': 'whois_scraper', 'success': has_data, 'data': result}
        
        except Exception as e:
            print(f"      ❌ Playwright爬取失败: {e}")
            return {'source': 'whois_scraper', 'success': False, 'data': {}}
    
    def _parse_raw_whois(self, raw_text: str) -> Dict:
        """从raw WHOIS文本解析信息"""
        result = {}
        
        # 提取注册商
        match = re.search(r'Registrar:\s*(.+)', raw_text, re.I)
        if match:
            result['registrar'] = match.group(1).strip()
        
        # 提取创建日期
        match = re.search(r'(?:Created|Creation Date):\s*(.+)', raw_text, re.I)
        if match:
            result['creation_date'] = match.group(1).strip()
        
        # 提取过期日期
        match = re.search(r'(?:Expir[^:]*Date|Registry Expiry Date):\s*(.+)', raw_text, re.I)
        if match:
            result['expiry_date'] = match.group(1).strip()
        
        # 提取名称服务器
        ns_matches = re.findall(r'(?:Name Server|nameserver):\s*(.+)', raw_text, re.I)
        if ns_matches:
            result['nameservers'] = [ns.strip() for ns in ns_matches]
        
        return result
    
    def _parse_rdap_response(self, rdap_data: Dict, source_url: str) -> Dict:
        """解析RDAP响应"""
        result = {
            'registrar': None,
            'registry': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'registrant_org': None,
            'data_source': source_url
        }
        
        # 提取注册商
        entities = rdap_data.get('entities', [])
        for entity in entities:
            roles = entity.get('roles', [])
            if 'registrar' in roles:
                result['registrar'] = entity.get('vcardArray', [[]])[1][0][3] if entity.get('vcardArray') else None
                break
        
        # 提取日期
        events = rdap_data.get('events', [])
        for event in events:
            action = event.get('eventAction', '')
            date = event.get('eventDate', '')
            if action == 'registration':
                result['creation_date'] = date
            elif action == 'expiration':
                result['expiry_date'] = date
        
        # 提取名称服务器
        nameservers = rdap_data.get('nameservers', [])
        result['nameservers'] = [ns.get('ldhName', '') for ns in nameservers]
        
        return result
    
    def _parse_api_ninjas_response(self, data: Dict) -> Dict:
        """解析API Ninjas响应"""
        return {
            'registrar': data.get('registrar'),
            'creation_date': data.get('creation_date'),
            'expiry_date': data.get('expiration_date'),
            'nameservers': data.get('name_servers', []),
            'registrant_org': data.get('registrant_organization')
        }
    
    def _count_fields(self, data: Dict) -> int:
        """计算有效字段数量"""
        count = 0
        for key, value in data.items():
            if key in ['source', 'success', 'data_source']:
                continue
            if value:
                if isinstance(value, list):
                    if len(value) > 0:
                        count += 1
                elif isinstance(value, str):
                    if value.strip():
                        count += 1
                elif value is not None:
                    count += 1
        return count
    
    def _select_best_result(self, results: List[Dict]) -> Dict:
        """选择信息最多的结果"""
        best = None
        best_count = 0
        
        for result in results:
            if not result['success']:
                continue
            
            count = self._count_fields(result['data'])
            
            if count > best_count:
                best_count = count
                best = result
        
        return best if best else results[0]
    
    async def query_dns_info(self, domain: str) -> Dict:
        """查询DNS信息"""
        info = {
            'a_records': [],
            'mx_records': [],
            'txt_records': [],
            'ns_records': []
        }
        
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5
        
        # A记录
        try:
            answers = resolver.resolve(domain, 'A')
            info['a_records'] = [str(rdata) for rdata in answers]
        except:
            pass
        
        # MX记录
        try:
            answers = resolver.resolve(domain, 'MX')
            info['mx_records'] = [f"{rdata.preference} {rdata.exchange}" for rdata in answers]
        except:
            pass
        
        # TXT记录
        try:
            answers = resolver.resolve(domain, 'TXT')
            for rdata in answers:
                txt_value = ''.join([s.decode('utf-8') if isinstance(s, bytes) else str(s) for s in rdata.strings])
                info['txt_records'].append(txt_value)
        except:
            pass
        
        # NS记录
        try:
            answers = resolver.resolve(domain, 'NS')
            info['ns_records'] = [str(rdata) for rdata in answers]
        except:
            pass
        
        return info
    
    async def process_domain(self, domain: str, iteration: int = 0) -> Dict:
        """处理单个域名 - 官方WHOIS优先 + 多层fallback"""
        print(f"\n   [{iteration}] 处理: {domain}")
        
        # 策略1: 优先使用官方WHOIS服务器（直接socket连接）
        whois_result = await self.query_official_whois(domain)
        
        if whois_result['success']:
            best_result = whois_result
            # 显示结果
            count = self._count_fields(whois_result.get('data', {}))
            llm_used = whois_result.get('data', {}).get('llm_parsed', False)
            method = "LLM解析" if llm_used else "规则解析"
            print(f"      ✓ 官方WHOIS成功 ({method}): {count}个字段")
        else:
            # 策略2: 官方WHOIS失败，尝试RDAP API
            print(f"      📡 官方WHOIS失败，尝试RDAP API...")
            api_tasks = [
                self.query_rdap_primary(domain),
                self.query_rdap_bootstrap(domain),
                self.query_api_ninjas(domain)
            ]
            
            api_results = await asyncio.gather(*api_tasks, return_exceptions=True)
            valid_results = [r for r in api_results if isinstance(r, dict)]
            
            # 显示各API结果
            for r in valid_results:
                status = "✓" if r['success'] else "✗"
                count = self._count_fields(r.get('data', {})) if r['success'] else 0
                print(f"      {status} {r['source']}: {count}个字段")
            
            # 选择最佳结果
            best_result = self._select_best_result(valid_results)
            
            # 策略3: 所有API都失败，使用Playwright爬虫
            if not best_result['success']:
                print(f"      ⚠️  所有API失败，启动Playwright爬虫...")
                scrape_result = await self.scrape_whois_website(domain)
                if scrape_result['success']:
                    best_result = scrape_result
                    count = self._count_fields(scrape_result['data'])
                    print(f"      ✓ 爬虫成功: {count}个字段")
                else:
                    print(f"      ✗ 爬虫也失败")
        
        # 4. 查询DNS信息
        dns_info = await self.query_dns_info(domain)
        
        # 5. 合并结果
        final_result = {
            'domain': domain,
            'data_source': best_result['source'],
            'rdap_data': best_result.get('data', {}),
            'dns_info': dns_info,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'success': best_result['success']
        }
        
        # 显示摘要
        rdap_count = self._count_fields(best_result.get('data', {}))
        dns_count = sum(1 for v in dns_info.values() if v)
        print(f"      ✅ 完成: WHOIS/RDAP={rdap_count}字段, DNS={dns_count}类型")
        
        return final_result
    
    async def monitor_domains(self, domains: List[str], interval: int = 300, max_iterations: int = None):
        """持续监控域名列表"""
        print("\n" + "="*70)
        print("🔄 增强域名监控系统 - 持续监控模式")
        print("="*70)
        print(f"\n📊 配置:")
        print(f"   域名数量: {len(domains)}")
        print(f"   监控间隔: {interval}秒 ({interval//60}分钟)")
        print(f"   最大迭代: {max_iterations if max_iterations else '无限制'}")
        print(f"   数据源: 官方WHOIS → RDAP API → Playwright爬虫")
        print(f"   LLM解析: {'启用 (DeepSeek)' if self.deepseek_key else '禁用'}")
        print("\n" + "="*70)
        
        iteration = 0
        
        while True:
            iteration += 1
            
            if max_iterations and iteration > max_iterations:
                print(f"\n✓ 达到最大迭代次数 {max_iterations}，停止监控")
                break
            
            print(f"\n\n{'='*70}")
            print(f"📍 第 {iteration} 轮监控 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"{'='*70}")
            
            start_time = datetime.now()
            
            # 处理所有域名
            results = []
            for i, domain in enumerate(domains, 1):
                result = await self.process_domain(domain, i)
                results.append(result)
                
                # 避免请求过快
                if i < len(domains):
                    await asyncio.sleep(1)
            
            # 保存结果
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # JSON
            json_file = f"monitor_results_iter{iteration}_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'iteration': iteration,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'domains_count': len(domains),
                    'results': results
                }, f, indent=2, ensure_ascii=False, default=str)
            
            # CSV
            csv_file = f"monitor_results_iter{iteration}_{timestamp}.csv"
            self._save_csv(results, csv_file)
            
            # 统计
            success_count = sum(1 for r in results if r['success'])
            
            elapsed = (datetime.now() - start_time).total_seconds()
            
            print(f"\n{'='*70}")
            print(f"📊 第 {iteration} 轮统计:")
            print(f"   ✅ 成功: {success_count}/{len(domains)} ({success_count*100//len(domains)}%)")
            print(f"   ⏱️  耗时: {elapsed:.1f}秒")
            print(f"   💾 保存: {json_file}")
            print(f"   💾 保存: {csv_file}")
            
            # 等待下一轮
            if max_iterations is None or iteration < max_iterations:
                print(f"\n⏳ 等待 {interval} 秒后开始下一轮监控...")
                print(f"   (按 Ctrl+C 可随时停止)")
                
                try:
                    await asyncio.sleep(interval)
                except KeyboardInterrupt:
                    print(f"\n\n⚠️  收到中断信号，停止监控")
                    break
    
    def _save_csv(self, results: List[Dict], filename: str):
        """保存CSV文件"""
        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            
            # 表头
            writer.writerow([
                'domain', 'success', 'data_source', 'registrar', 'registry',
                'creation_date', 'expiry_date', 'rdap_nameservers',
                'dns_a_records', 'dns_mx_records', 'dns_txt_records',
                'dns_ns_records', 'timestamp'
            ])
            
            # 数据
            for r in results:
                rdap = r.get('rdap_data', {})
                dns = r.get('dns_info', {})
                
                writer.writerow([
                    r['domain'],
                    'Y' if r['success'] else 'N',
                    r['data_source'],
                    rdap.get('registrar', ''),
                    rdap.get('registry', ''),
                    rdap.get('creation_date', ''),
                    rdap.get('expiry_date', ''),
                    '; '.join(rdap.get('nameservers', [])),
                    '; '.join(dns.get('a_records', [])),
                    '; '.join(dns.get('mx_records', [])),
                    '; '.join(dns.get('txt_records', [])),
                    '; '.join(dns.get('ns_records', [])),
                    r['timestamp']
                ])


async def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='增强域名监控系统 (支持LLM解析)')
    parser.add_argument('csv_file', help='输入CSV文件')
    parser.add_argument('--interval', type=int, default=300, help='监控间隔(秒)，默认300秒(5分钟)')
    parser.add_argument('--iterations', type=int, default=None, help='最大迭代次数，默认无限')
    parser.add_argument('--api-key', help='API Ninjas密钥')
    parser.add_argument('--deepseek-key', help='DeepSeek API密钥(用于LLM解析WHOIS)')
    
    args = parser.parse_args()
    
    # 读取域名
    if not Path(args.csv_file).exists():
        print(f"❌ 文件不存在: {args.csv_file}")
        return
    
    domains = []
    with open(args.csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1].strip():
                domains.append(row[1].strip())
    
    if not domains:
        print("❌ CSV中没有域名")
        return
    
    # 创建监控器
    monitor = EnhancedDomainMonitor(
        api_ninjas_key=args.api_key,
        deepseek_key=args.deepseek_key
    )
    
    # 显示LLM状态
    if monitor.deepseek_key:
        print("🤖 DeepSeek LLM已启用 - 将用于解析WHOIS数据")
    else:
        print("ℹ️  DeepSeek LLM未配置 - 将使用规则解析")
    
    # 开始监控
    try:
        await monitor.monitor_domains(
            domains=domains,
            interval=args.interval,
            max_iterations=args.iterations
        )
    except KeyboardInterrupt:
        print("\n\n✓ 监控已停止")


if __name__ == "__main__":
    asyncio.run(main())

