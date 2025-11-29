"""
Quick test: Process first 3 failed domains with Playwright
快速测试：用Playwright处理前3个失败的域名
"""
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from playwright.async_api import async_playwright
import re


async def scrape_domain_info(domain: str):
    """Scrape who.is for domain information."""
    print(f"\n🔍 Scraping {domain}...")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            url = f"https://who.is/whois/{domain}"
            print(f"   → Visiting: {url}")
            
            await page.goto(url, wait_until='domcontentloaded', timeout=30000)
            await page.wait_for_timeout(2000)
            
            # Get page text
            page_text = await page.inner_text('body')
            
            # Extract information
            result = {
                'domain': domain,
                'registrant_org': None,
                'registrar': None,
                'creation_date': None,
                'expiry_date': None,
                'nameservers': [],
                'data_source': 'who.is (Playwright)'
            }
            
            # Extract registrant
            registrant_patterns = [
                r'Registrant.*?Organization:\s*(.+)',
                r'Registrant Organization:\s*(.+)',
                r'Registrant:\s*(.+)',
            ]
            
            for pattern in registrant_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    result['registrant_org'] = match.group(1).strip()
                    break
            
            # Extract registrar
            match = re.search(r'Registrar:\s*(.+)', page_text, re.IGNORECASE | re.MULTILINE)
            if match:
                result['registrar'] = match.group(1).strip()
            
            # Extract creation date
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
            
            # Extract expiry date
            expiry_patterns = [
                r'Expir.*?:\s*(.+)',
                r'Registry Expiry Date:\s*(.+)',
            ]
            
            for pattern in expiry_patterns:
                match = re.search(pattern, page_text, re.IGNORECASE | re.MULTILINE)
                if match:
                    result['expiry_date'] = match.group(1).strip()
                    break
            
            # Extract nameservers
            ns_matches = re.findall(r'Name Server:\s*(.+)', page_text, re.IGNORECASE)
            if ns_matches:
                result['nameservers'] = [ns.strip() for ns in ns_matches]
            
            await browser.close()
            
            # Display results
            print(f"   ✅ Data retrieved:")
            if result['registrant_org']:
                print(f"      📋 Registrant: {result['registrant_org']}")
            if result['registrar']:
                print(f"      🏢 Registrar: {result['registrar']}")
            if result['creation_date']:
                print(f"      📅 Created: {result['creation_date']}")
            if result['expiry_date']:
                print(f"      ⏰ Expires: {result['expiry_date']}")
            if result['nameservers']:
                print(f"      🌐 Nameservers: {', '.join(result['nameservers'][:2])}...")
            
            return result
            
    except Exception as e:
        print(f"   ❌ Error: {str(e)}")
        return {'domain': domain, 'error': str(e)}


async def quick_test():
    """Test with first 3 failed domains."""
    
    print("=" * 70)
    print("🌐 Playwright Quick Test - Failed Domains")
    print("=" * 70)
    
    # Test domains (from failed list)
    test_domains = [
        "aholddelhaize.be",
        "delhaize.be",
        "pingodoce.pt"
    ]
    
    print(f"\n📋 Testing {len(test_domains)} domains that failed with API approach")
    print(f"   Using Playwright to scrape who.is website")
    
    results = []
    
    for i, domain in enumerate(test_domains, 1):
        print(f"\n[{i}/{len(test_domains)}] Processing: {domain}")
        result = await scrape_domain_info(domain)
        results.append(result)
        
        # Delay between requests
        if i < len(test_domains):
            print(f"   ⏳ Waiting 3 seconds...")
            await asyncio.sleep(3.0)
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Quick Test Complete")
    print("=" * 70)
    
    success_count = sum(1 for r in results if r.get('registrant_org') or r.get('registrar'))
    print(f"\n✅ Successfully retrieved: {success_count}/{len(test_domains)}")
    
    # Save results
    output_file = "playwright_quick_test.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2)
    
    print(f"💾 Results saved to: {output_file}")
    
    return results


if __name__ == "__main__":
    print("🚀 Testing Playwright scraping for domains not supported by API...")
    print()
    asyncio.run(quick_test())

