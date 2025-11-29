"""
Improved Playwright scraper for who.is WHOIS data
改进的Playwright爬虫，用于获取who.is的WHOIS数据
"""
import asyncio
import json
import re
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from playwright.async_api import async_playwright
import httpx

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))
from config.settings import settings


async def parse_with_llm(page_text: str, domain: str, source_url: str):
    """使用LLM解析playwright爬取的WHOIS文本
    
    Args:
        page_text: 页面文本内容
        domain: 域名
        source_url: 数据源URL
        
    Returns:
        解析后的结构化数据
    """
    # 检查是否配置了DeepSeek API key
    if not settings.deepseek_api_key:
        return {}
    
    # 生成时间戳
    timestamp = datetime.now(timezone.utc).isoformat()
    
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
{page_text}
=====END INPUT====="""

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(60.0)) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
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
                    "max_tokens": 1500
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                
                # 清理可能的markdown标记
                content = content.replace('```json', '').replace('```', '').strip()
                
                try:
                    parsed = json.loads(content)
                    
                    # 新的prompt返回 {"domains": [...]} 结构
                    # 提取第一个domain
                    if 'domains' in parsed and len(parsed['domains']) > 0:
                        domain_data = parsed['domains'][0]
                        
                        return {
                            'registrant_org': domain_data.get('registrant_organization'),
                            'registrar': domain_data.get('registrar'),
                            'creation_date': domain_data.get('creation_date'),
                            'expiry_date': domain_data.get('expiry_date'),
                            'nameservers': domain_data.get('nameservers', []),
                            'registry': domain_data.get('registry'),
                            'data_source': source_url,
                            'timestamp': domain_data.get('timestamp'),
                        }
                    else:
                        return {}
                except Exception:
                    return {}
            else:
                return {}
    
    except Exception:
        return {}


async def scrape_domain_whois(domain: str):
    """Scrape WHOIS data from who.is with improved parsing."""
    
    print(f"\n🔍 Scraping: {domain}")
    
    result = {
        'domain': domain,
        'registrant_org': None,
        'registrar': None,
        'creation_date': None,
        'expiry_date': None,
        'nameservers': [],
        'status': None,
        'data_source': 'who.is (Playwright)',
        'success': False,
        'parsing_method': 'regex'
    }
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            )
            page = await context.new_page()
            
            url = f"https://who.is/whois/{domain}"
            print(f"   → Visiting: {url}")
            
            # Go to page and wait for content
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(3000)
            
            # Try to click "Raw WHOIS Data" if available
            try:
                # Look for Raw WHOIS section
                raw_whois_button = page.locator("text=Raw WHOIS Data")
                if await raw_whois_button.count() > 0:
                    print(f"   → Expanding Raw WHOIS Data...")
                    await raw_whois_button.click()
                    await page.wait_for_timeout(2000)
            except:
                pass
            
            # Get all text content
            page_text = await page.inner_text('body')
            
            # Try LLM parsing first if available
            if settings.deepseek_api_key:
                print(f"   🤖 Trying LLM parsing...")
                llm_result = await parse_with_llm(page_text, domain, url)
                
                if llm_result:
                    # Use LLM results
                    result.update(llm_result)
                    result['parsing_method'] = 'llm'
                    result['success'] = True
                    result['status'] = 'REGISTERED'
                    print(f"   ✓ LLM parsing successful")
                    if result.get('creation_date'):
                        print(f"   ✓ Creation Date: {result['creation_date']}")
                    if result.get('registrar'):
                        print(f"   ✓ Registrar: {result['registrar']}")
                    if result.get('registrant_org'):
                        print(f"   ✓ Registrant: {result['registrant_org']}")
                    
                    await browser.close()
                    return result
            
            # Fallback to regex parsing if LLM not available or failed
            print(f"   → Using regex parsing (fallback)")
            
            # Extract creation date from the "Important Dates" section
            created_match = re.search(r'Created\s+(\d{1,2}/\d{1,2}/\d{4})', page_text)
            if created_match:
                result['creation_date'] = created_match.group(1)
                result['success'] = True
                print(f"   ✓ Creation Date: {result['creation_date']}")
            
            # Try to find registrar in various formats
            registrar_patterns = [
                r'Registrar:\s*(.+)',
                r'Registrar Name:\s*(.+)',
                r'Sponsoring Registrar:\s*(.+)',
            ]
            
            for pattern in registrar_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    result['registrar'] = match.group(1).strip()[:100]
                    result['success'] = True
                    print(f"   ✓ Registrar: {result['registrar']}")
                    break
            
            # Try to find registrant organization
            registrant_patterns = [
                r'Registrant\s+Organization:\s*(.+)',
                r'Registrant:\s*(.+)',
                r'Organization:\s*(.+)',
            ]
            
            for pattern in registrant_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    org = match.group(1).strip()
                    # Filter out privacy messages
                    if 'privacy' not in org.lower() and 'redacted' not in org.lower():
                        result['registrant_org'] = org[:100]
                        result['success'] = True
                        print(f"   ✓ Registrant: {result['registrant_org']}")
                        break
            
            # Look for nameservers
            ns_matches = re.findall(r'Name\s+Server[:\s]*(\S+\.\S+)', page_text, re.IGNORECASE)
            if ns_matches:
                result['nameservers'] = list(set(ns_matches))[:5]  # Deduplicate and limit
                result['success'] = True
                print(f"   ✓ Nameservers: {', '.join(result['nameservers'][:2])}...")
            
            # Check if domain is registered
            if 'domain is not found' in page_text.lower() or 'no match' in page_text.lower():
                result['status'] = 'NOT_REGISTERED'
                print(f"   ⚠️  Domain not registered")
            elif result['creation_date'] or result['registrar']:
                result['status'] = 'REGISTERED'
                print(f"   ✓ Domain is registered")
            
            await browser.close()
            
            return result
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)[:80]}")
        result['error'] = str(e)
        return result


async def test_improved_scraper():
    """Test the improved scraper with some failed domains."""
    
    print("=" * 75)
    print("🌐 Improved Playwright Scraper - Testing")
    print("=" * 75)
    
    # Test domains
    test_domains = [
        "delhaize.be",          # .be domain
        "aholddelhaize.be",     # .be domain
        "pingodoce.pt",         # .pt domain
        "aholddelhaize.eu",     # .eu domain
        "delhaizewineworld.lu", # .lu domain
    ]
    
    print(f"\n📋 Testing {len(test_domains)} domains")
    print(f"   These domains failed with RDAP/WHOIS API\n")
    
    results = []
    success_count = 0
    
    for i, domain in enumerate(test_domains, 1):
        print(f"[{i}/{len(test_domains)}]", end=" ")
        result = await scrape_domain_whois(domain)
        results.append(result)
        
        if result['success']:
            success_count += 1
        
        # Delay between requests
        if i < len(test_domains):
            print(f"   ⏳ Waiting 3 seconds...\n")
            await asyncio.sleep(3.0)
    
    # Summary
    print("\n" + "=" * 75)
    print("📊 Test Results")
    print("=" * 75)
    
    print(f"\n✅ Successfully retrieved: {success_count}/{len(test_domains)} ({success_count/len(test_domains)*100:.0f}%)")
    
    # Show summary table
    print(f"\n📋 Results Summary:")
    print("-" * 75)
    print(f"{'Domain':<30} {'Status':<15} {'Created':<12} {'Registrar':<20}")
    print("-" * 75)
    
    for r in results:
        status = '✓' if r['success'] else '✗'
        created = r['creation_date'][:10] if r['creation_date'] else 'N/A'
        registrar = (r['registrar'][:17] + '...') if r['registrar'] and len(r['registrar']) > 17 else (r['registrar'] or 'N/A')
        print(f"{r['domain']:<30} {status:<15} {created:<12} {registrar:<20}")
    
    # Save results
    output_file = "improved_playwright_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    print("🚀 Testing improved Playwright scraper...")
    print("   This will handle domains not supported by RDAP/WHOIS API\n")
    asyncio.run(test_improved_scraper())

