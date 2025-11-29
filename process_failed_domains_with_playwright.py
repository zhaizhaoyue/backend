"""
Process failed domains using Playwright (who.is scraping).
使用Playwright爬取who.is网站来处理失败的域名。

This will handle domains that RDAP/WHOIS API doesn't support (.be, .eu, .pt, .lu, etc.)
这将处理RDAP/WHOIS API不支持的域名（.be、.eu、.pt、.lu等）。
"""
import asyncio
import json
import csv
from datetime import datetime
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
import re


class PlaywrightDomainMonitor:
    """Use Playwright to scrape who.is for domain information."""
    
    def __init__(self):
        self.results = []
    
    async def scrape_whois_info(self, domain: str):
        """Scrape who.is website for domain information."""
        try:
            async with async_playwright() as p:
                # Launch browser in headless mode
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to who.is
                url = f"https://who.is/whois/{domain}"
                print(f"      Navigating to: {url}")
                
                await page.goto(url, wait_until='domcontentloaded', timeout=30000)
                await page.wait_for_timeout(2000)  # Wait for content to load
                
                # Get page text
                page_text = await page.inner_text('body')
                
                # Extract information using regex patterns
                result = {
                    'domain': domain,
                    'registrant_org': None,
                    'registrar': None,
                    'creation_date': None,
                    'expiry_date': None,
                    'nameservers': [],
                    'status': None,
                    'data_source': 'who.is (Playwright)',
                    'success': False
                }
                
                # Try to extract registrant
                registrant_patterns = [
                    r'Registrant.*?Organization:\s*(.+)',
                    r'Registrant Organization:\s*(.+)',
                    r'Registrant:\s*(.+)',
                    r'Organization:\s*(.+)',
                ]
                
                for pattern in registrant_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        result['registrant_org'] = match.group(1).strip()
                        break
                
                # Try to extract registrar
                registrar_patterns = [
                    r'Registrar:\s*(.+)',
                    r'Registrar Name:\s*(.+)',
                ]
                
                for pattern in registrar_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        result['registrar'] = match.group(1).strip()
                        break
                
                # Try to extract dates
                creation_patterns = [
                    r'Created.*?:\s*(.+)',
                    r'Creation Date:\s*(.+)',
                    r'Registered.*?:\s*(.+)',
                ]
                
                for pattern in creation_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        result['creation_date'] = match.group(1).strip()
                        break
                
                expiry_patterns = [
                    r'Expir.*?:\s*(.+)',
                    r'Registry Expiry Date:\s*(.+)',
                    r'Expiration Date:\s*(.+)',
                ]
                
                for pattern in expiry_patterns:
                    match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                    if match:
                        result['expiry_date'] = match.group(1).strip()
                        break
                
                # Try to extract nameservers
                ns_matches = re.findall(r'Name Server:\s*(.+)', page_text, re.IGNORECASE)
                if ns_matches:
                    result['nameservers'] = [ns.strip() for ns in ns_matches]
                
                # Check if we got any data
                if result['registrant_org'] or result['registrar'] or result['creation_date']:
                    result['success'] = True
                
                await browser.close()
                
                return result
                
        except Exception as e:
            print(f"      ❌ Playwright error: {str(e)[:50]}")
            return {
                'domain': domain,
                'success': False,
                'error': str(e),
                'data_source': 'who.is (Playwright - failed)'
            }


async def process_failed_domains():
    """Process domains that failed with API approach."""
    
    print("=" * 80)
    print("🌐 Processing Failed Domains with Playwright")
    print("=" * 80)
    
    # Load failed domains from summary
    summary_file = "houthoff_summary_20251129-112315.json"
    
    if not Path(summary_file).exists():
        print(f"❌ Summary file not found: {summary_file}")
        print("Please run process_all_houthoff_domains.py first.")
        return
    
    with open(summary_file, 'r') as f:
        summary = json.load(f)
    
    failed_domains = summary.get('failed_domains', [])
    
    print(f"\n📋 Failed domains to retry: {len(failed_domains)}")
    print(f"⏱️  Estimated time: ~{len(failed_domains) * 5 / 60:.1f} minutes")
    print(f"   (5 seconds per domain for page load)")
    
    # Initialize monitor
    monitor = PlaywrightDomainMonitor()
    
    print(f"\n🔍 Processing with Playwright...")
    print("-" * 80)
    
    results = []
    success_count = 0
    
    for i, domain in enumerate(failed_domains, 1):
        print(f"\n[{i:2d}/{len(failed_domains)}] {domain:35}", end=" ", flush=True)
        
        try:
            result = await monitor.scrape_whois_info(domain)
            
            if result['success']:
                print(f"✅")
                if result.get('registrant_org'):
                    print(f"      Registrant: {result['registrant_org'][:50]}")
                if result.get('registrar'):
                    print(f"      Registrar: {result['registrar'][:50]}")
                if result.get('creation_date'):
                    print(f"      Created: {result['creation_date'][:20]}")
                success_count += 1
            else:
                print(f"⚠️  No data found on who.is")
            
            results.append(result)
            
            # Delay to be respectful to who.is server
            await asyncio.sleep(3.0)
            
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
            results.append({
                'domain': domain,
                'success': False,
                'error': str(e)
            })
    
    # Generate report
    print("\n" + "=" * 80)
    print("📊 Playwright Processing Complete")
    print("=" * 80)
    
    print(f"\n📈 Results:")
    print(f"   ✅ Successfully retrieved: {success_count}/{len(failed_domains)} ({success_count/len(failed_domains)*100:.1f}%)")
    print(f"   ❌ Still failed: {len(failed_domains) - success_count}")
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    # Save as JSON
    json_file = f"houthoff_playwright_results_{timestamp}.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"\n💾 Results saved:")
    print(f"   📄 JSON: {json_file}")
    
    # Save as CSV
    csv_file = f"houthoff_playwright_results_{timestamp}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=[
            'domain', 'registrant_org', 'registrar', 'creation_date',
            'expiry_date', 'nameservers', 'status', 'data_source', 'success'
        ])
        writer.writeheader()
        
        for result in results:
            row = {
                'domain': result.get('domain', ''),
                'registrant_org': result.get('registrant_org', ''),
                'registrar': result.get('registrar', ''),
                'creation_date': result.get('creation_date', ''),
                'expiry_date': result.get('expiry_date', ''),
                'nameservers': '; '.join(result.get('nameservers', [])),
                'status': result.get('status', ''),
                'data_source': result.get('data_source', ''),
                'success': result.get('success', False)
            }
            writer.writerow(row)
    
    print(f"   📊 CSV: {csv_file}")
    
    print("\n✅ Processing complete!")
    print(f"\n💡 Tip: You can now merge these results with the API results")
    print(f"   to get a complete dataset for all 75 domains.")
    
    return results


async def main():
    """Main entry point."""
    print("🎯 This script uses Playwright to scrape who.is for domains")
    print("   that failed with RDAP/WHOIS API approach.")
    print()
    
    results = await process_failed_domains()
    
    print(f"\n🎉 Retrieved data for {sum(1 for r in results if r.get('success'))} additional domains!")


if __name__ == "__main__":
    asyncio.run(main())

