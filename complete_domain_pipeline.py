"""
Complete Domain Verification Pipeline

Pipeline stages:
1. RDAP/WHOIS API lookup
2. Playwright scraping for API failures
3. TXT verification setup
4. TXT verification execution (DNS checking)

All data organized by run_id in data/ folder
"""
import asyncio
import csv
import json
import os
import shutil
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
import sys
from typing import List, Dict, Tuple, Optional

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
import re
import httpx

from src.core.rdap_client import RDAPClient
from src.core.txt_verification import TXTVerificationManager
from src.models.domain import DomainResult
from src.utils.csv_exporter import CSVExporter
from config.settings import settings


class CompleteDomainPipeline:
    """Complete pipeline for domain verification."""
    
    def __init__(self, run_id: str):
        """Initialize pipeline with run ID."""
        self.run_id = run_id
        self.run_dir = Path(f"data/run_{run_id}")
        
        # Create directory structure
        self.screenshots_dir = self.run_dir / "screenshots"
        self.intermediate_dir = self.run_dir / "intermediate"
        self.results_dir = self.run_dir / "results"
        
        for dir_path in [self.screenshots_dir, self.intermediate_dir, self.results_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize clients
        self.rdap_client = RDAPClient(api_ninjas_key=settings.api_ninjas_key)
        self.txt_manager = TXTVerificationManager(
            db_path=str(self.run_dir / "txt_verification.db")
        )
        
        # Storage for results at each stage
        self.stage1_results = []  # API results
        self.stage2_results = []  # Playwright results
        self.stage3_results = []  # TXT verification tasks
        self.stage4_results = []  # TXT verification execution results
        
        self.domains = []
    
    def save_metadata(self, stage: str, data: dict):
        """Save metadata for a stage."""
        metadata_file = self.intermediate_dir / f"stage_{stage}_metadata.json"
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
        print(f"   💾 Metadata saved: {metadata_file.name}")
    
    async def parse_with_llm(self, page_text: str, domain: str, source_url: str) -> Dict:
        """Parse WHOIS text scraped by Playwright using LLM
        
        Args:
            page_text: Page text content
            domain: Domain name
            source_url: Data source URL
            
        Returns:
            Parsed structured data
        """
        # Check if DeepSeek API key is configured
        if not settings.deepseek_api_key:
            # Show warning only once
            if not hasattr(self, '_deepseek_warning_shown'):
                print(f"\n      💡 DeepSeek API not configured, using regex parsing (current accuracy 70%)")
                print(f"      💡 Enable AI parsing to improve to 75-80%, cost ~¥0.15/75 domains")
                print(f"      💡 Set: export DEEPSEEK_API_KEY=sk-your-key")
                print(f"      💡 Free key: https://platform.deepseek.com\n")
                self._deepseek_warning_shown = True
            return {}
        
        # Generate timestamp
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
                    usage = data.get('usage', {})
                    
                    # Clean possible markdown markers
                    content = content.replace('```json', '').replace('```', '').strip()
                    
                    try:
                        parsed = json.loads(content)
                        
                        # New prompt returns {"domains": [...]} structure
                        # Extract first domain
                        if 'domains' in parsed and len(parsed['domains']) > 0:
                            domain_data = parsed['domains'][0]
                            
                            # Display token usage
                            total_tokens = usage.get('total_tokens', 0)
                            print(f"      🤖 LLM parsing successful | 📊 Tokens: {total_tokens}")
                            
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
                            print(f"      ⚠️  LLM returned empty result, fallback to regex")
                            return {}
                    except Exception as e:
                        print(f"      ⚠️  LLM parsing failed: {str(e)[:30]}, fallback to regex")
                        return {}
                else:
                    print(f"      ⚠️  LLM API error: {response.status_code}, fallback to regex")
                    return {}
        
        except Exception as e:
            print(f"      ⚠️  LLM call failed: {e}")
            return {}
    
    async def stage1_api_lookup(self, domains: List[str]):
        """Stage 1: RDAP/WHOIS API lookup."""
        
        print("\n" + "=" * 80)
        print("📡 STAGE 1: RDAP/WHOIS API Lookup")
        print("=" * 80)
        
        print(f"\n🔍 Processing {len(domains)} domains with API...")
        
        api_success = []
        api_failed = []
        
        for i, domain in enumerate(domains, 1):
            print(f"[{i}/{len(domains)}] {domain:30}", end=" ", flush=True)
            
            try:
                lookup_data, source_url = await self.rdap_client.lookup_domain(domain)
                
                if lookup_data.get('data_source_type') == 'failed':
                    print("❌ API failed")
                    api_failed.append(domain)
                else:
                    print(f"✅ {lookup_data.get('data_source_type', 'unknown')}")
                    
                    # Create domain result
                    domain_result = DomainResult(
                        domain=domain,
                        registrant_organization=lookup_data.get('registrant_org'),
                        registrar=lookup_data.get('registrar'),
                        registry=lookup_data.get('registry'),
                        creation_date=lookup_data.get('creation_date'),
                        expiry_date=lookup_data.get('expiry_date'),
                        nameservers=lookup_data.get('nameservers', []),
                        data_source=lookup_data.get('data_source'),
                        timestamp=datetime.now(timezone.utc)
                    )
                    
                    self.stage1_results.append(domain_result)
                    api_success.append(domain)
                
                await asyncio.sleep(2.0)
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:40]}")
                api_failed.append(domain)
        
        # Save Stage 1 results
        stage1_file = self.intermediate_dir / "stage1_api_results.json"
        with open(stage1_file, 'w', encoding='utf-8') as f:
            json.dump(
                [r.model_dump(mode='json') for r in self.stage1_results],
                f, indent=2, default=str
            )
        
        # Save failed domains list for Stage 2
        failed_file = self.intermediate_dir / "stage1_failed_domains.txt"
        with open(failed_file, 'w') as f:
            f.write('\n'.join(api_failed))
        
        # Save metadata
        self.save_metadata('1', {
            'stage': 'RDAP/WHOIS API Lookup',
            'total_domains': len(domains),
            'successful': len(api_success),
            'failed': len(api_failed),
            'success_rate': f"{len(api_success)/len(domains)*100:.1f}%",
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"\n📊 Stage 1 Summary:")
        print(f"   ✅ API Success: {len(api_success)}")
        print(f"   ❌ API Failed: {len(api_failed)}")
        print(f"   📝 Failed domains saved for Stage 2")
        
        return api_failed
    
    async def stage2_playwright_scraping(self, failed_domains: List[str]):
        """Stage 2: Playwright scraping for API failures."""
        
        if not failed_domains:
            print("\n✅ No domains need Playwright scraping (all succeeded in Stage 1)")
            return []
        
        print("\n" + "=" * 80)
        print("🌐 STAGE 2: Playwright Scraping (who.is + sidn.nl for .nl domains)")
        print("=" * 80)
        
        print(f"\n🔍 Processing {len(failed_domains)} failed domains with Playwright...")
        print(f"   📍 Source 1: who.is (all domains)")
        print(f"   📍 Source 2: sidn.nl (fallback for .nl domains)")
        print()
        
        playwright_success = []
        playwright_failed = []
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            for i, domain in enumerate(failed_domains, 1):
                print(f"[{i}/{len(failed_domains)}] {domain:30}", end=" ", flush=True)
                
                try:
                    # First try who.is
                    result = await self.scrape_with_playwright(browser, domain, i)
                    
                    # If who.is failed and domain is .nl, try sidn.nl
                    if not result['success'] and domain.endswith('.nl'):
                        print(f"⚠️  No data on who.is")
                        print(f"      🔄 Trying sidn.nl...")
                        
                        await asyncio.sleep(2.0)
                        result = await self.scrape_sidn_nl(browser, domain, i)
                    
                    if result['success']:
                        print(f"✅ Data found ({result.get('data_source', 'unknown')})")
                        if result.get('creation_date'):
                            print(f"      Created: {result['creation_date']}")
                        if result.get('registrar'):
                            print(f"      Registrar: {result['registrar'][:40]}")
                        playwright_success.append(domain)
                    else:
                        print(f"⚠️  No data")
                        playwright_failed.append(domain)
                    
                    self.stage2_results.append(result)
                    
                    await asyncio.sleep(3.0)
                    
                except Exception as e:
                    print(f"❌ Error: {str(e)[:40]}")
                    playwright_failed.append(domain)
                    self.stage2_results.append({
                        'domain': domain,
                        'success': False,
                        'error': str(e)
                    })
            
            await browser.close()
        
        # Save Stage 2 results
        stage2_file = self.intermediate_dir / "stage2_playwright_results.json"
        with open(stage2_file, 'w', encoding='utf-8') as f:
            json.dump(self.stage2_results, f, indent=2)
        
        # Save domains that still need TXT verification
        txt_needed_file = self.intermediate_dir / "stage2_need_txt_verification.txt"
        with open(txt_needed_file, 'w') as f:
            f.write('\n'.join(playwright_failed))
        
        # Save metadata
        self.save_metadata('2', {
            'stage': 'Playwright Scraping',
            'total_domains': len(failed_domains),
            'successful': len(playwright_success),
            'failed': len(playwright_failed),
            'success_rate': f"{len(playwright_success)/len(failed_domains)*100:.1f}%" if failed_domains else "N/A",
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"\n📊 Stage 2 Summary:")
        print(f"   ✅ Playwright Success: {len(playwright_success)}")
        print(f"   ❌ Still Failed: {len(playwright_failed)}")
        print(f"   📝 Domains saved for Stage 3 (TXT verification)")
        
        return playwright_failed
    
    async def scrape_sidn_nl(self, browser, domain: str, index: int):
        """Scrape .nl domain from sidn.nl website.
        
        Args:
            browser: Playwright browser instance
            domain: Domain name to scrape
            index: Domain index for screenshot naming
            
        Returns:
            Result dictionary with domain information
        """
        result = {
            'domain': domain,
            'registrant_org': None,
            'registrar': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'data_source': 'sidn.nl (Playwright)',
            'success': False,
            'parsing_method': 'llm'
        }
        
        try:
            page = await browser.new_page()
            
            # Go to SIDN WHOIS page
            url = f"https://www.sidn.nl/whois"
            await page.goto(url, wait_until='networkidle', timeout=10000)
            await page.wait_for_timeout(1000)
            
            # Find and fill the search input
            # The input field might be named 'domain' or have a specific id
            try:
                await page.fill('input[name="domain"]', domain)
            except:
                # Try alternative selector
                await page.fill('input[type="text"]', domain)
            
            await page.wait_for_timeout(500)
            
            # Submit the form (click search button or press Enter)
            try:
                await page.click('button[type="submit"]')
            except:
                await page.press('input[name="domain"]', 'Enter')
            
            # Wait for results to load
            await page.wait_for_timeout(1500)
            
            # Take screenshot of results
            screenshot_file = self.screenshots_dir / f"{index:03d}_{domain.replace('.', '_')}_sidn.png"
            await page.screenshot(path=str(screenshot_file))
            
            # Look for "Toon mij de gegevens" (Show me the data) button/link
            # This might be a button or link, try to click it
            try:
                # Try different possible selectors
                selectors_to_try = [
                    'text="Toon mij de gegevens"',
                    'text="toon mij de gegevens"',
                    'button:has-text("Toon")',
                    'a:has-text("Toon")',
                    '.show-details',
                    '#show-details'
                ]
                
                clicked = False
                for selector in selectors_to_try:
                    try:
                        await page.click(selector, timeout=3000)
                        clicked = True
                        break
                    except:
                        continue
                
                if clicked:
                    await page.wait_for_timeout(1000)
                    
                    # Take another screenshot after clicking
                    screenshot_file2 = self.screenshots_dir / f"{index:03d}_{domain.replace('.', '_')}_sidn_details.png"
                    await page.screenshot(path=str(screenshot_file2))
                
            except Exception as e:
                print(f"      ⚠️  Could not click 'Toon mij de gegevens': {str(e)[:50]}")
            
            # Get the page content after clicking (or without if button not found)
            page_text = await page.inner_text('body')
            
            # Use LLM to parse the content (same prompt as who.is)
            if settings.deepseek_api_key:
                llm_result = await self.parse_with_llm(page_text, domain, url)
                
                if llm_result:
                    result.update(llm_result)
                    result['data_source'] = 'sidn.nl (Playwright + LLM)'
                    result['success'] = True
                else:
                    # Try regex as fallback
                    result.update(self._parse_sidn_with_regex(page_text))
                    if result['creation_date'] or result['registrar']:
                        result['success'] = True
                        result['parsing_method'] = 'regex'
            
            await page.close()
            
        except Exception as e:
            result['error'] = str(e)
            print(f"      ⚠️  SIDN.nl scraping error: {str(e)[:50]}")
        
        return result
    
    def _parse_sidn_with_regex(self, page_text: str) -> Dict:
        """Parse SIDN page content with regex as fallback.
        
        Args:
            page_text: Page text content
            
        Returns:
            Dictionary with extracted fields
        """
        result = {
            'creation_date': None,
            'registrar': None,
            'registrant_org': None,
            'nameservers': []
        }
        
        # SIDN might have Dutch labels
        # Registrar
        registrar_patterns = [
            r'Registrar:\s*(.+)',
            r'Beheerder:\s*(.+)',
        ]
        for pattern in registrar_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                result['registrar'] = match.group(1).strip()[:100]
                break
        
        # Creation date (various date formats)
        date_patterns = [
            r'Creation Date:\s*(\d{4}-\d{2}-\d{2})',
            r'Aangemaakt:\s*(\d{4}-\d{2}-\d{2})',
            r'Date registered:\s*(\d{4}-\d{2}-\d{2})',
        ]
        for pattern in date_patterns:
            match = re.search(pattern, page_text, re.IGNORECASE)
            if match:
                result['creation_date'] = match.group(1)
                break
        
        return result
    
    async def scrape_with_playwright(self, browser, domain: str, index: int):
        """Scrape single domain with Playwright."""
        
        result = {
            'domain': domain,
            'registrant_org': None,
            'registrar': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'data_source': 'who.is (Playwright)',
            'success': False,
            'parsing_method': 'regex'  # Track which method was used
        }
        
        try:
            page = await browser.new_page()
            
            url = f"https://who.is/whois/{domain}"
            await page.goto(url, wait_until='networkidle', timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Take screenshot
            screenshot_file = self.screenshots_dir / f"{index:03d}_{domain.replace('.', '_')}.png"
            await page.screenshot(path=str(screenshot_file))
            
            # Get page content
            page_text = await page.inner_text('body')
            
            # Try LLM parsing first if available
            if settings.deepseek_api_key:
                llm_result = await self.parse_with_llm(page_text, domain, url)
                
                if llm_result:
                    # Use LLM results
                    result.update(llm_result)
                    result['parsing_method'] = 'llm'
                    result['success'] = True
                    await page.close()
                    return result
            
            # Fallback to regex parsing if LLM not available or failed
            # Extract creation date
            created_match = re.search(r'Created\s+(\d{1,2}/\d{1,2}/\d{4})', page_text)
            if created_match:
                result['creation_date'] = created_match.group(1)
                result['success'] = True
            
            # Extract registrar
            registrar_match = re.search(r'Registrar:\s*(.+)', page_text, re.IGNORECASE)
            if registrar_match:
                result['registrar'] = registrar_match.group(1).strip()[:100]
                result['success'] = True
            
            # Extract registrant
            registrant_patterns = [
                r'Registrant\s+Organization:\s*(.+)',
                r'Organization:\s*(.+)',
            ]
            
            for pattern in registrant_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    org = match.group(1).strip()
                    if 'privacy' not in org.lower() and 'redacted' not in org.lower():
                        result['registrant_org'] = org[:100]
                        result['success'] = True
                        break
            
            await page.close()
            
        except Exception as e:
            result['error'] = str(e)
        
        return result
    
    async def stage3_txt_verification(self, uncertain_domains: List[str]):
        """Stage 3: TXT verification for uncertain ownership."""
        
        if not uncertain_domains:
            print("\n✅ No domains need TXT verification")
            return
        
        print("\n" + "=" * 80)
        print("🔐 STAGE 3: TXT Verification Setup")
        print("=" * 80)
        
        print(f"\n📝 Creating TXT verification tasks for {len(uncertain_domains)} domains...")
        
        txt_tasks = []
        
        for i, domain in enumerate(uncertain_domains, 1):
            print(f"[{i}/{len(uncertain_domains)}] {domain:30}", end=" ", flush=True)
            
            try:
                # Create TXT verification task
                task_id, token = self.txt_manager.create_txt_task(
                    domain=domain,
                    case_id=self.run_id,
                    max_attempts=60
                )
                
                txt_tasks.append({
                    'domain': domain,
                    'task_id': task_id,
                    'token': token,
                    'txt_name': '@',
                    'instructions': f"Add TXT record: @ = {token}"
                })
                
                print(f"✅ Task created")
                print(f"      Token: {token}")
                
                self.stage3_results.append({
                    'domain': domain,
                    'task_id': task_id,
                    'token': token
                })
                
            except Exception as e:
                print(f"❌ Error: {str(e)[:40]}")
        
        # Save Stage 3 results
        stage3_file = self.intermediate_dir / "stage3_txt_tasks.json"
        with open(stage3_file, 'w', encoding='utf-8') as f:
            json.dump(txt_tasks, f, indent=2)
        
        # Create instructions file
        instructions_file = self.results_dir / "TXT_VERIFICATION_INSTRUCTIONS.txt"
        with open(instructions_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("TXT Verification Instructions\n")
            f.write(f"Run ID: {self.run_id}\n")
            f.write("=" * 80 + "\n\n")
            
            for task in txt_tasks:
                f.write(f"Domain: {task['domain']}\n")
                f.write(f"  Add DNS TXT record:\n")
                f.write(f"  Host/Name: {task['txt_name']}\n")
                f.write(f"  Type: TXT\n")
                f.write(f"  Value: {task['token']}\n")
                f.write(f"  Task ID: {task['task_id']}\n")
                f.write("\n" + "-" * 80 + "\n\n")
        
        # Save metadata
        self.save_metadata('3', {
            'stage': 'TXT Verification Setup',
            'total_domains': len(uncertain_domains),
            'tasks_created': len(txt_tasks),
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"\n📊 Stage 3 Summary:")
        print(f"   📝 TXT Tasks Created: {len(txt_tasks)}")
        print(f"   📄 Instructions: {instructions_file.name}")
        print(f"\n💡 Users can now add TXT records to verify domain ownership")
        
        return txt_tasks
    
    def check_txt_via_dig(self, domain: str, expected_token: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """Check TXT record using dig command.
        
        Args:
            domain: Domain name to check
            expected_token: Expected verification token
            
        Returns:
            Tuple of (success, dns_raw_output, error_message)
        """
        try:
            # Use Cloudflare DNS (1.1.1.1) with dig
            cmd = ["dig", "@1.1.1.1", "TXT", domain, "+short"]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            output = result.stdout.strip()
            
            # Check if there's any output
            if not output:
                return False, output, "NO_ANSWER"
            
            # Parse TXT records
            lines = output.splitlines()
            for line in lines:
                # Remove quotes from TXT record value
                txt_value = line.strip().strip('"')
                
                # Check if token is present
                if expected_token in txt_value:
                    return True, output, None
            
            return False, output, "TOKEN_NOT_FOUND"
            
        except subprocess.TimeoutExpired:
            return False, None, "TIMEOUT"
        except FileNotFoundError:
            return False, None, "DIG_NOT_INSTALLED"
        except Exception as e:
            return False, None, str(e)
    
    async def stage4_txt_verification_execution(self, txt_tasks: List[Dict], 
                                                wait_time: int = 300,
                                                max_attempts: int = 1,
                                                poll_interval: int = 60):
        """Stage 4: Execute TXT verification by checking DNS records.
        
        Args:
            txt_tasks: List of TXT tasks from stage 3
            wait_time: Initial wait time before first check (seconds, default: 300 = 5 minutes)
            max_attempts: Maximum number of polling attempts (default: 1)
            poll_interval: Time between polling attempts (seconds, default: 60 = 1 minute)
            
        Note:
            Total wait time = wait_time + (max_attempts * poll_interval)
            Default: 5 minutes + (1 * 1 minute) = 6 minutes total
        """
        
        if not txt_tasks:
            print("\n⏭️  No TXT verification tasks to execute, skipping Stage 4")
            return
        
        print("\n" + "=" * 80)
        print("🔐 STAGE 4: TXT Verification Execution (DNS Checking)")
        print("=" * 80)
        
        print(f"\n📋 Will verify {len(txt_tasks)} domains")
        print(f"⏱️  Initial wait: {wait_time} seconds")
        print(f"🔄 Max attempts: {max_attempts} (every {poll_interval}s)")
        print()
        
        # Display instructions
        print("=" * 80)
        print("📝 INSTRUCTIONS: Please add the following TXT records to your DNS")
        print("=" * 80)
        for i, task in enumerate(txt_tasks, 1):
            print(f"\n[{i}/{len(txt_tasks)}] {task['domain']}")
            print(f"   Record Type: TXT")
            print(f"   Host/Name: @ (or leave blank for root domain)")
            print(f"   Value: {task['token']}")
        
        print("\n" + "=" * 80)
        print(f"⏳ Waiting {wait_time} seconds for DNS records to be added...")
        print("   (You can add records during this time)")
        print("=" * 80)
        
        # Wait for initial setup time
        await asyncio.sleep(wait_time)
        
        # Start verification
        print("\n🚀 Starting DNS verification...")
        
        verified_count = 0
        failed_count = 0
        pending_tasks = list(txt_tasks)
        
        for attempt in range(1, max_attempts + 1):
            print(f"\n{'=' * 80}")
            print(f"🔍 Verification Attempt {attempt}/{max_attempts}")
            print(f"📊 Remaining: {len(pending_tasks)} domains")
            print(f"{'=' * 80}\n")
            
            still_pending = []
            
            for i, task in enumerate(pending_tasks, 1):
                domain = task['domain']
                token = task['token']
                task_id = task['task_id']
                
                print(f"[{i}/{len(pending_tasks)}] {domain:30}", end=" ", flush=True)
                
                # Check DNS
                success, dns_output, error = self.check_txt_via_dig(domain, token)
                
                if success:
                    print(f"✅ VERIFIED!")
                    verified_count += 1
                    
                    # Update database
                    now = datetime.now(timezone.utc)
                    self.txt_manager.db.mark_task_verified(task_id, dns_output, now)
                    self.txt_manager.update_domain_verified(domain, self.run_id, now)
                    
                    # Add to stage4 results
                    self.stage4_results.append({
                        'domain': domain,
                        'status': 'VERIFIED',
                        'attempt': attempt,
                        'dns_output': dns_output,
                        'verified_at': now.isoformat()
                    })
                    
                else:
                    print(f"⏳ Not yet ({error})")
                    still_pending.append(task)
                    
                    # Update attempt count in database
                    now = datetime.now(timezone.utc)
                    self.txt_manager.db.increment_task_attempt(task_id, dns_output, error, now)
            
            # Update pending list
            pending_tasks = still_pending
            
            if not pending_tasks:
                print(f"\n🎉 All domains verified!")
                break
            
            # Wait before next attempt (unless last attempt)
            if attempt < max_attempts and pending_tasks:
                print(f"\n⏳ Waiting {poll_interval} seconds before next attempt...")
                await asyncio.sleep(poll_interval)
        
        # Mark remaining as failed
        failed_count = len(pending_tasks)
        for task in pending_tasks:
            self.stage4_results.append({
                'domain': task['domain'],
                'status': 'FAILED',
                'reason': 'Max attempts reached'
            })
        
        # Save Stage 4 results
        stage4_file = self.intermediate_dir / "stage4_txt_results.json"
        with open(stage4_file, 'w', encoding='utf-8') as f:
            json.dump(self.stage4_results, f, indent=2)
        
        # Save metadata
        self.save_metadata('4', {
            'stage': 'TXT Verification Execution',
            'total_domains': len(txt_tasks),
            'verified': verified_count,
            'failed': failed_count,
            'max_attempts': max_attempts,
            'timestamp': datetime.now().isoformat()
        })
        
        print(f"\n📊 Stage 4 Summary:")
        print(f"   ✅ Verified: {verified_count}")
        print(f"   ❌ Failed: {failed_count}")
        print(f"   📝 Results saved: {stage4_file.name}")
    
    async def run_complete_pipeline(self, input_csv: str, 
                                    enable_txt_verification: bool = True,
                                    txt_wait_time: int = 30,
                                    txt_max_attempts: int = 10,
                                    txt_poll_interval: int = 30):
        """Run the complete 4-stage pipeline.
        
        Args:
            input_csv: Path to input CSV file
            enable_txt_verification: Whether to execute Stage 4 (TXT verification)
            txt_wait_time: Initial wait time before first DNS check (seconds)
            txt_max_attempts: Maximum polling attempts for TXT verification
            txt_poll_interval: Time between polling attempts (seconds)
        """
        
        print("=" * 80)
        print(f"🚀 Complete Domain Verification Pipeline")
        print(f"   Run ID: {self.run_id}")
        print(f"   Data Directory: {self.run_dir}")
        print("=" * 80)
        
        # Copy input file to run directory
        input_copy = self.run_dir / "input.csv"
        shutil.copy(input_csv, input_copy)
        print(f"\n📥 Input copied to: {input_copy}")
        
        # Read domains from CSV
        domains = []
        with open(input_csv, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row in reader:
                if len(row) >= 2 and row[1]:
                    domain = row[1].strip()
                    if domain and '.' in domain:
                        domains.append(domain)
        
        self.domains = domains
        print(f"📋 Total domains: {len(domains)}")
        
        start_time = datetime.now()
        
        # Stage 1: API Lookup
        stage1_failed = await self.stage1_api_lookup(domains)
        
        # Stage 2: Playwright Scraping
        stage2_failed = await self.stage2_playwright_scraping(stage1_failed)
        
        # Stage 3: TXT Verification Setup
        txt_tasks = await self.stage3_txt_verification(stage2_failed)
        
        # Stage 4: TXT Verification Execution (optional)
        if enable_txt_verification and txt_tasks:
            await self.stage4_txt_verification_execution(
                txt_tasks=txt_tasks,
                wait_time=txt_wait_time,
                max_attempts=txt_max_attempts,
                poll_interval=txt_poll_interval
            )
        
        # Generate final report
        total_time = (datetime.now() - start_time).total_seconds()
        
        await self.generate_final_report(total_time)
        
        print("\n" + "=" * 80)
        print("✅ PIPELINE COMPLETE!")
        print("=" * 80)
        print(f"\n📁 All results saved in: {self.run_dir}")
        print(f"   📊 Final report: results/FINAL_REPORT.txt")
        print(f"   📸 Screenshots: screenshots/")
        print(f"   📝 Intermediate files: intermediate/")
    
    async def generate_final_report(self, total_time: float):
        """Generate comprehensive final report."""
        
        report_file = self.results_dir / "FINAL_REPORT.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("=" * 80 + "\n")
            f.write("COMPLETE DOMAIN VERIFICATION PIPELINE - FINAL REPORT\n")
            f.write("=" * 80 + "\n\n")
            
            f.write(f"Run ID: {self.run_id}\n")
            f.write(f"Timestamp: {datetime.now().isoformat()}\n")
            f.write(f"Total Processing Time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)\n")
            f.write(f"Total Domains: {len(self.domains)}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("STAGE 1: RDAP/WHOIS API LOOKUP\n")
            f.write("-" * 80 + "\n")
            f.write(f"Successful: {len(self.stage1_results)}\n")
            f.write(f"Failed: {len(self.domains) - len(self.stage1_results)}\n")
            f.write(f"Success Rate: {len(self.stage1_results)/len(self.domains)*100:.1f}%\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("STAGE 2: PLAYWRIGHT SCRAPING\n")
            f.write("-" * 80 + "\n")
            successful_stage2 = sum(1 for r in self.stage2_results if r.get('success'))
            f.write(f"Processed: {len(self.stage2_results)}\n")
            f.write(f"Successful: {successful_stage2}\n")
            f.write(f"Screenshots Captured: {len(list(self.screenshots_dir.glob('*.png')))}\n\n")
            
            f.write("-" * 80 + "\n")
            f.write("STAGE 3: TXT VERIFICATION SETUP\n")
            f.write("-" * 80 + "\n")
            f.write(f"Tasks Created: {len(self.stage3_results)}\n\n")
            
            # Stage 4 stats
            if self.stage4_results:
                f.write("-" * 80 + "\n")
                f.write("STAGE 4: TXT VERIFICATION EXECUTION\n")
                f.write("-" * 80 + "\n")
                verified_count = sum(1 for r in self.stage4_results if r.get('status') == 'VERIFIED')
                failed_count = sum(1 for r in self.stage4_results if r.get('status') == 'FAILED')
                f.write(f"Processed: {len(self.stage4_results)}\n")
                f.write(f"Verified: {verified_count}\n")
                f.write(f"Failed: {failed_count}\n")
                if len(self.stage4_results) > 0:
                    f.write(f"Verification Rate: {verified_count/len(self.stage4_results)*100:.1f}%\n")
                f.write("\n")
            
            f.write("-" * 80 + "\n")
            f.write("OVERALL SUMMARY\n")
            f.write("-" * 80 + "\n")
            total_resolved = len(self.stage1_results) + successful_stage2
            verified_by_txt = sum(1 for r in self.stage4_results if r.get('status') == 'VERIFIED')
            total_resolved += verified_by_txt
            
            f.write(f"Resolved by API (Stage 1): {len(self.stage1_results)}\n")
            f.write(f"Resolved by Playwright (Stage 2): {successful_stage2}\n")
            f.write(f"Resolved by TXT (Stage 4): {verified_by_txt}\n")
            f.write(f"Total Resolved: {total_resolved}/{len(self.domains)} ({total_resolved/len(self.domains)*100:.1f}%)\n")
            
            pending_txt = len(self.stage3_results) - verified_by_txt
            if pending_txt > 0:
                f.write(f"Still Pending TXT Verification: {pending_txt}\n")
            
            f.write(f"Overall Success Rate: {total_resolved/len(self.domains)*100:.1f}%\n")
        
        # Also save as JSON
        report_json = self.results_dir / "FINAL_REPORT.json"
        
        verified_by_txt = sum(1 for r in self.stage4_results if r.get('status') == 'VERIFIED')
        successful_stage2 = sum(1 for r in self.stage2_results if r.get('success'))
        total_resolved = len(self.stage1_results) + successful_stage2 + verified_by_txt
        
        report_data = {
            'run_id': self.run_id,
            'timestamp': datetime.now().isoformat(),
            'total_time_seconds': total_time,
            'total_domains': len(self.domains),
            'stage1': {
                'successful': len(self.stage1_results),
                'failed': len(self.domains) - len(self.stage1_results)
            },
            'stage2': {
                'processed': len(self.stage2_results),
                'successful': successful_stage2
            },
            'stage3': {
                'tasks_created': len(self.stage3_results)
            },
            'overall': {
                'total_resolved': total_resolved,
                'success_rate': total_resolved / len(self.domains) * 100 if self.domains else 0
            }
        }
        
        # Add stage4 data if available
        if self.stage4_results:
            failed_count = sum(1 for r in self.stage4_results if r.get('status') == 'FAILED')
            report_data['stage4'] = {
                'processed': len(self.stage4_results),
                'verified': verified_by_txt,
                'failed': failed_count,
                'verification_rate': verified_by_txt / len(self.stage4_results) * 100 if self.stage4_results else 0
            }
        
        with open(report_json, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        
        # Combine Stage 1 and Stage 2 successful results for CSV export
        all_successful_results = list(self.stage1_results)
        
        # Add Stage 2 Playwright successful results
        for stage2_result in self.stage2_results:
            if stage2_result.get('success'):
                # Convert Stage 2 result to DomainResult format
                domain_result = DomainResult(
                    domain=stage2_result['domain'],
                    registrant_organization=stage2_result.get('registrant_org'),
                    registrar=stage2_result.get('registrar'),
                    registry=None,  # Playwright doesn't provide registry info
                    creation_date=stage2_result.get('creation_date'),
                    expiry_date=stage2_result.get('expiry_date'),
                    nameservers=stage2_result.get('nameservers', []),
                    data_source=stage2_result.get('data_source', 'Playwright'),
                    timestamp=datetime.now(timezone.utc)
                )
                all_successful_results.append(domain_result)
        
        # Save combined results as CSV
        csv_file = self.results_dir / f"all_results_{self.run_id}.csv"
        CSVExporter.save_to_file(all_successful_results, str(csv_file))
        
        print(f"\n📄 Final report generated:")
        print(f"   {report_file}")
        print(f"   {report_json}")
        print(f"\n📊 CSV exported:")
        print(f"   Total domains in CSV: {len(all_successful_results)}")
        print(f"   - From Stage 1 (API): {len(self.stage1_results)}")
        print(f"   - From Stage 2 (Playwright): {sum(1 for r in self.stage2_results if r.get('success'))}")


async def main():
    """Main entry point."""
    
    # Check DeepSeek API configuration
    if not settings.deepseek_api_key:
        print("\n" + "=" * 80)
        print("💡 Notice: DeepSeek API not configured")
        print("=" * 80)
        print("Currently will use regex parsing (accuracy ~70%)")
        print()
        print("To enable AI smart parsing (accuracy improves to 75-80%):")
        print("  1. Get free key: https://platform.deepseek.com")
        print("  2. Set environment variable: export DEEPSEEK_API_KEY=sk-your-key")
        print("  3. Or create .env file: echo 'DEEPSEEK_API_KEY=sk-xxx' > .env")
        print()
        print("Cost: ~¥0.15/75 domains (very cheap)")
        print("=" * 80)
        
        response = input("\nContinue with regex parsing? (Y/n): ").strip().lower()
        if response == 'n':
            print("\nPlease configure DeepSeek API and run again")
            return
        print()
    else:
        print(f"\n✅ DeepSeek API configured, will use AI smart parsing")
        print(f"   API Key: {settings.deepseek_api_key[:10]}...{settings.deepseek_api_key[-4:]}\n")
    
    # Generate run ID
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Input CSV
    input_csv = "../Houthoff-Challenge_Domain-Names.csv"
    
    if not Path(input_csv).exists():
        print(f"❌ Error: Input file not found: {input_csv}")
        return
    
    # Create and run pipeline
    pipeline = CompleteDomainPipeline(run_id)
    await pipeline.run_complete_pipeline(input_csv)
    
    print(f"\n🎉 Complete! Check results in: data/run_{run_id}/")


if __name__ == "__main__":
    asyncio.run(main())
