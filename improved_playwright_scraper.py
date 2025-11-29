"""
Improved Playwright scraper for who.is WHOIS data
改进的Playwright爬虫，用于获取who.is的WHOIS数据
"""
import asyncio
import json
import re
from playwright.async_api import async_playwright


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
        'success': False
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

