"""
Enhanced test script with:
- Creation date extraction
- Data source URL
- Playwright evidence screenshots
- Dutch domains (.nl)
- Typo/defensive registrations test
"""
import asyncio
import json
from datetime import datetime
import sys
from pathlib import Path

# Install required packages
try:
    import httpx
    from playwright.async_api import async_playwright
except ImportError:
    print("Installing required packages...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "httpx", "playwright"])
    print("Installing Playwright browser...")
    subprocess.check_call([sys.executable, "-m", "playwright", "install", "chromium"])
    import httpx
    from playwright.async_api import async_playwright


# Test domains - including top companies, typos, defensive, and Dutch domains
TEST_DOMAINS = {
    # Top 10 companies
    "apple.com": {"type": "legitimate", "company": "Apple Inc."},
    "microsoft.com": {"type": "legitimate", "company": "Microsoft Corporation"},
    "google.com": {"type": "legitimate", "company": "Alphabet Inc. (Google)"},
    "amazon.com": {"type": "legitimate", "company": "Amazon.com Inc."},
    "meta.com": {"type": "legitimate", "company": "Meta Platforms"},
    
    # Typo squatting / defensive registrations (likely owned by companies)
    "amazom.com": {"type": "typo/defensive", "company": "Possible Amazon defensive"},
    "gooogle.com": {"type": "typo/defensive", "company": "Possible Google defensive"},
    "microsft.com": {"type": "typo/defensive", "company": "Possible Microsoft typo"},
    
    # Dutch domains (.nl)
    "ing.nl": {"type": "legitimate", "company": "ING Bank (Netherlands)"},
    "abn-amro.nl": {"type": "legitimate", "company": "ABN AMRO Bank"},
    "philips.nl": {"type": "legitimate", "company": "Philips (Netherlands)"},
    "heineken.nl": {"type": "legitimate", "company": "Heineken"},
    "booking.nl": {"type": "defensive", "company": "Booking.com (defensive)"},
}

RDAP_ENDPOINTS = {
    ".com": "https://rdap.verisign.com/com/v1/domain/{}",
    ".net": "https://rdap.verisign.com/net/v1/domain/{}",
    ".org": "https://rdap.publicinterestregistry.org/rdap/domain/{}",
    ".nl": "https://rdap.sidn.nl/domain/{}",  # Dutch domains - SIDN
}


def get_tld(domain):
    """Extract TLD from domain."""
    parts = domain.lower().split('.')
    if len(parts) >= 2:
        return '.' + parts[-1]
    return ''


def detect_privacy(data):
    """Detect privacy protection."""
    privacy_keywords = [
        "REDACTED FOR PRIVACY",
        "Contact Privacy",
        "WhoisGuard",
        "Privacy Protect",
        "REDACTED"
    ]
    
    registrant_org = data.get('registrant_org', '') or ''
    for keyword in privacy_keywords:
        if keyword.lower() in registrant_org.lower():
            return True
    return False


async def capture_evidence_screenshot(domain, source_url, tld, evidence_dir):
    """
    Capture screenshot evidence from the data source.
    
    Args:
        domain: Domain name
        source_url: RDAP API URL
        tld: Top-level domain
        evidence_dir: Directory to save screenshots
        
    Returns:
        Path to screenshot or None
    """
    screenshot_path = evidence_dir / f"{domain}.png"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            # Special handling for .nl domains - use SIDN web interface
            if tld == '.nl':
                try:
                    # Go to SIDN WHOIS lookup page
                    print(f"      📸 Capturing evidence from SIDN web interface...")
                    await page.goto("https://www.sidn.nl/en/whois", wait_until="networkidle", timeout=15000)
                    
                    # Find and fill search input
                    search_input = await page.query_selector('input[name="domain"], input[type="text"]')
                    if search_input:
                        await search_input.fill(domain)
                        
                        # Submit search
                        submit_button = await page.query_selector('button[type="submit"], input[type="submit"]')
                        if submit_button:
                            await submit_button.click()
                        else:
                            await search_input.press("Enter")
                        
                        # Wait for results
                        await page.wait_for_timeout(2000)
                        
                        # Take screenshot
                        await page.screenshot(path=str(screenshot_path), full_page=True)
                        print(f"      ✅ Evidence saved: {screenshot_path.name}")
                        await browser.close()
                        return str(screenshot_path)
                except Exception as e:
                    print(f"      ⚠️ SIDN web capture failed: {e}, trying API page...")
            
            # For other domains or fallback - capture RDAP JSON page
            print(f"      📸 Capturing evidence from RDAP API page...")
            await page.goto(source_url, wait_until="networkidle", timeout=15000)
            await page.wait_for_timeout(1000)
            
            # Take screenshot
            await page.screenshot(path=str(screenshot_path), full_page=True)
            print(f"      ✅ Evidence saved: {screenshot_path.name}")
            
            await browser.close()
            return str(screenshot_path)
            
    except Exception as e:
        print(f"      ❌ Screenshot failed: {e}")
        return None


async def lookup_domain(domain, domain_info, evidence_dir):
    """Perform enhanced RDAP lookup for a domain."""
    tld = get_tld(domain)
    
    if tld not in RDAP_ENDPOINTS:
        return {
            'domain': domain,
            'type': domain_info['type'],
            'company': domain_info['company'],
            'status': '❌ Unsupported TLD',
            'tld': tld,
            'registrar': None,
            'registry': None,
            'registrant_org': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'data_source': None,
            'data_source_type': None,
            'lookup_timestamp': datetime.now().isoformat(),
            'is_privacy': False,
            'evidence_file': None
        }
    
    rdap_url = RDAP_ENDPOINTS[tld].format(domain)
    
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(rdap_url)
            response.raise_for_status()
            rdap_data = response.json()
            
            # Parse response
            result = {
                'domain': domain,
                'type': domain_info['type'],
                'company': domain_info['company'],
                'status': '✅ Success',
                'tld': tld,
                'registrar': None,
                'registry': None,
                'registrant_org': None,
                'creation_date': None,  # ← NEW: Domain creation date
                'expiry_date': None,
                'nameservers': [],
                'data_source': rdap_url,  # ← NEW: RDAP API URL
                'data_source_type': 'rdap_registry',
                'lookup_timestamp': datetime.now().isoformat(),
                'is_privacy': False,
                'evidence_file': None
            }
            
            # Extract dates
            events = rdap_data.get('events', [])
            for event in events:
                event_action = event.get('eventAction', '')
                event_date = event.get('eventDate', '')
                
                if event_action == 'registration':
                    result['creation_date'] = event_date[:10] if event_date else None
                elif event_action == 'expiration':
                    result['expiry_date'] = event_date[:10] if event_date else None
            
            # Extract nameservers
            nameservers = rdap_data.get('nameservers', [])
            for ns in nameservers[:3]:  # First 3 only
                ns_name = ns.get('ldhName')
                if ns_name:
                    result['nameservers'].append(ns_name)
            
            # Extract entities
            entities = rdap_data.get('entities', [])
            for entity in entities:
                roles = entity.get('roles', [])
                
                if 'registrar' in roles:
                    vcards = entity.get('vcardArray', [])
                    if len(vcards) > 1:
                        for vcard_item in vcards[1]:
                            if isinstance(vcard_item, list) and len(vcard_item) > 3:
                                if vcard_item[0] == 'fn':
                                    result['registrar'] = vcard_item[3]
                                    break
                
                if 'registrant' in roles:
                    vcards = entity.get('vcardArray', [])
                    if len(vcards) > 1:
                        for vcard_item in vcards[1]:
                            if isinstance(vcard_item, list) and len(vcard_item) > 3:
                                if vcard_item[0] == 'org':
                                    result['registrant_org'] = vcard_item[3]
                                    break
            
            # Detect privacy
            result['is_privacy'] = detect_privacy(result)
            
            # Set registry based on TLD
            if tld == '.com' or tld == '.net':
                result['registry'] = 'Verisign'
            elif tld == '.org':
                result['registry'] = 'Public Interest Registry'
            elif tld == '.nl':
                result['registry'] = 'SIDN (Netherlands)'
            
            # ← NEW: Capture evidence screenshot
            evidence_file = await capture_evidence_screenshot(domain, rdap_url, tld, evidence_dir)
            result['evidence_file'] = evidence_file
            
            return result
            
    except httpx.HTTPError as e:
        return {
            'domain': domain,
            'type': domain_info['type'],
            'company': domain_info['company'],
            'status': f'⚠️ HTTP Error: {str(e)[:50]}',
            'tld': tld,
            'registrar': None,
            'registry': None,
            'registrant_org': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'data_source': rdap_url,
            'data_source_type': 'rdap_registry',
            'lookup_timestamp': datetime.now().isoformat(),
            'is_privacy': False,
            'evidence_file': None
        }
    except Exception as e:
        return {
            'domain': domain,
            'type': domain_info['type'],
            'company': domain_info['company'],
            'status': f'❌ Error: {str(e)[:50]}',
            'tld': tld,
            'registrar': None,
            'registry': None,
            'registrant_org': None,
            'creation_date': None,
            'expiry_date': None,
            'nameservers': [],
            'data_source': None,
            'data_source_type': None,
            'lookup_timestamp': datetime.now().isoformat(),
            'is_privacy': False,
            'evidence_file': None
        }


async def main():
    """Run enhanced domain lookup test."""
    print("=" * 90)
    print("🔍 Enhanced Domain Ownership Due Diligence Tool - Test Run")
    print("Testing: Legitimate domains, Typo registrations, Dutch domains")
    print("=" * 90)
    print()
    
    # Create evidence directory
    evidence_dir = Path("evidence_screenshots")
    evidence_dir.mkdir(exist_ok=True)
    print(f"📁 Evidence directory: {evidence_dir.absolute()}")
    print()
    
    results = []
    
    for i, (domain, info) in enumerate(TEST_DOMAINS.items(), 1):
        type_icon = "🏢" if info['type'] == 'legitimate' else "🔄" if 'defensive' in info['type'] else "⚠️"
        print(f"[{i}/{len(TEST_DOMAINS)}] {type_icon} Querying {domain}")
        print(f"        Type: {info['type']}")
        print(f"        Expected: {info['company']}")
        
        result = await lookup_domain(domain, info, evidence_dir)
        results.append(result)
        
        # Print quick status
        if result['status'] == '✅ Success':
            privacy_flag = "🔒 PRIVATE" if result['is_privacy'] else "✅ PUBLIC"
            print(f"        Status: {result['status']} - {privacy_flag}")
            if result['registrant_org']:
                print(f"        Registrant: {result['registrant_org']}")
            if result['creation_date']:
                print(f"        Created: {result['creation_date']}")
            print(f"        Data Source: {result['data_source']}")
        else:
            print(f"        Status: {result['status']}")
        print()
        
        # Small delay to be nice to servers
        await asyncio.sleep(0.8)
    
    # Print summary table
    print("=" * 90)
    print("📊 SUMMARY RESULTS")
    print("=" * 90)
    print()
    print(f"{'#':<4} {'Domain':<25} {'Type':<20} {'Created':<12} {'Expires':<12} {'Evidence':<10}")
    print("-" * 90)
    
    for i, r in enumerate(results, 1):
        created = r.get('creation_date') or 'N/A'
        expires = r.get('expiry_date') or 'N/A'
        evidence = "✅ Yes" if r.get('evidence_file') else "❌ No"
        status_icon = "✅" if r['status'] == '✅ Success' else "❌"
        
        print(f"{i:<4} {r['domain']:<25} {r['type']:<20} {created:<12} {expires:<12} {evidence:<10}")
    
    # Statistics
    print()
    print("=" * 90)
    print("📈 STATISTICS")
    print("=" * 90)
    success_count = sum(1 for r in results if r['status'] == '✅ Success')
    evidence_count = sum(1 for r in results if r.get('evidence_file'))
    privacy_count = sum(1 for r in results if r['is_privacy'])
    
    # Count by type
    legitimate_count = sum(1 for r in results if r['type'] == 'legitimate')
    typo_count = sum(1 for r in results if 'typo' in r['type'])
    dutch_count = sum(1 for r in results if r['tld'] == '.nl')
    
    print(f"Total domains tested: {len(results)}")
    print(f"Successful lookups: {success_count}")
    print(f"Failed lookups: {len(results) - success_count}")
    print(f"Evidence screenshots: {evidence_count}")
    print(f"Privacy protected: {privacy_count}")
    print()
    print("By type:")
    print(f"  Legitimate domains: {legitimate_count}")
    print(f"  Typo/Defensive registrations: {typo_count}")
    print(f"  Dutch (.nl) domains: {dutch_count}")
    
    # Save to file
    output_file = "enhanced_test_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'test_name': 'Enhanced Domain Lookup Test',
            'timestamp': datetime.now().isoformat(),
            'domains_tested': len(results),
            'evidence_directory': str(evidence_dir),
            'results': results
        }, f, indent=2)
    
    print()
    print(f"✅ Results saved to: {output_file}")
    print(f"📸 Evidence screenshots saved to: {evidence_dir}/")
    print("=" * 90)
    
    # Detailed results
    print()
    print("📋 DETAILED RESULTS")
    print("=" * 90)
    
    for i, r in enumerate(results, 1):
        type_icon = "🏢" if r['type'] == 'legitimate' else "🔄" if 'defensive' in r['type'] else "⚠️"
        print(f"\n{i}. {type_icon} {r['domain']} - {r['company']}")
        print(f"   Type: {r['type']}")
        print(f"   Status: {r['status']}")
        if r['status'] == '✅ Success':
            print(f"   Registrar: {r.get('registrar', 'N/A')}")
            print(f"   Registry: {r.get('registry', 'N/A')}")
            print(f"   Registrant: {r.get('registrant_org', 'N/A')}")
            print(f"   Created: {r.get('creation_date', 'N/A')}")  # ← NEW
            print(f"   Expires: {r.get('expiry_date', 'N/A')}")
            print(f"   Data Source: {r.get('data_source', 'N/A')}")  # ← NEW
            print(f"   Privacy Protected: {'Yes' if r['is_privacy'] else 'No'}")
            if r.get('nameservers'):
                print(f"   Nameservers: {', '.join(r['nameservers'])}")
            if r.get('evidence_file'):
                print(f"   Evidence: {r['evidence_file']}")  # ← NEW
    
    print()
    print("=" * 90)
    print("🎉 Test Complete!")
    print(f"Check the '{evidence_dir}' folder for screenshot evidence.")
    print("=" * 90)


if __name__ == "__main__":
    asyncio.run(main())

