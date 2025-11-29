"""
Simplified test script for domain lookup using only standard library + httpx.
Tests the top 20 companies by market cap.
"""
import asyncio
import json
from datetime import datetime
import sys

try:
    import httpx
except ImportError:
    print("Installing httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


# Top 20 companies by market cap and their domains
TOP_20_COMPANIES = {
    "apple.com": "Apple Inc.",
    "microsoft.com": "Microsoft Corporation",
    "google.com": "Alphabet Inc. (Google)",
    "amazon.com": "Amazon.com Inc.",
    "nvidia.com": "NVIDIA Corporation",
    "meta.com": "Meta Platforms (Facebook)",
    "tesla.com": "Tesla Inc.",
    "berkshirehathaway.com": "Berkshire Hathaway",
    "visa.com": "Visa Inc.",
    "tsmc.com": "Taiwan Semiconductor",
    "walmart.com": "Walmart Inc.",
    "jpmorgan.com": "JPMorgan Chase",
    "samsung.com": "Samsung",
    "mastercard.com": "Mastercard",
    "unitedhealth.com": "UnitedHealth Group",
    "jnj.com": "Johnson & Johnson",
    "oracle.com": "Oracle Corporation",
    "exxonmobil.com": "Exxon Mobil",
    "pg.com": "Procter & Gamble",
    "coca-cola.com": "The Coca-Cola Company"
}

RDAP_ENDPOINTS = {
    ".com": "https://rdap.verisign.com/com/v1/domain/{}",
    ".net": "https://rdap.verisign.com/net/v1/domain/{}",
    ".org": "https://rdap.publicinterestregistry.org/rdap/domain/{}",
    ".nl": "https://rdap.sidn.nl/domain/{}",
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


async def lookup_domain(domain, company_name):
    """Perform RDAP lookup for a domain."""
    tld = get_tld(domain)
    
    if tld not in RDAP_ENDPOINTS:
        return {
            'domain': domain,
            'company': company_name,
            'status': '❌ Unsupported TLD',
            'registrar': None,
            'registrant_org': None,
            'expiry_date': None,
            'is_privacy': False
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
                'company': company_name,
                'status': '✅ Success',
                'registrar': None,
                'registry': None,
                'registrant_org': None,
                'expiry_date': None,
                'is_privacy': False,
                'nameservers': []
            }
            
            # Extract dates
            events = rdap_data.get('events', [])
            for event in events:
                if event.get('eventAction') == 'expiration':
                    result['expiry_date'] = event.get('eventDate', '')[:10]  # Just date part
            
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
            
            # Registry
            if 'verisign' in rdap_url:
                result['registry'] = 'Verisign'
            
            return result
            
    except httpx.HTTPError as e:
        return {
            'domain': domain,
            'company': company_name,
            'status': f'⚠️ HTTP Error: {str(e)[:50]}',
            'registrar': None,
            'registrant_org': None,
            'expiry_date': None,
            'is_privacy': False
        }
    except Exception as e:
        return {
            'domain': domain,
            'company': company_name,
            'status': f'❌ Error: {str(e)[:50]}',
            'registrar': None,
            'registrant_org': None,
            'expiry_date': None,
            'is_privacy': False
        }


async def main():
    """Run domain lookup test."""
    print("=" * 80)
    print("🔍 Domain Ownership Due Diligence Tool - Test Run")
    print("Testing Top 20 Companies by Market Cap")
    print("=" * 80)
    print()
    
    results = []
    
    for i, (domain, company) in enumerate(TOP_20_COMPANIES.items(), 1):
        print(f"[{i}/20] Querying {domain} ({company})...")
        result = await lookup_domain(domain, company)
        results.append(result)
        
        # Print quick status
        if result['status'] == '✅ Success':
            privacy_flag = "🔒 PRIVATE" if result['is_privacy'] else "✅ PUBLIC"
            print(f"        {result['status']} - {privacy_flag}")
            if result['registrant_org']:
                print(f"        Registrant: {result['registrant_org']}")
        else:
            print(f"        {result['status']}")
        print()
        
        # Small delay to be nice to servers
        await asyncio.sleep(0.5)
    
    # Print summary table
    print("=" * 80)
    print("📊 SUMMARY RESULTS")
    print("=" * 80)
    print()
    print(f"{'#':<4} {'Domain':<25} {'Status':<12} {'Privacy':<10} {'Registrant Org':<30}")
    print("-" * 95)
    
    for i, r in enumerate(results, 1):
        privacy = "🔒 Yes" if r['is_privacy'] else "✅ No"
        registrant = (r['registrant_org'] or 'N/A')[:28]
        status_icon = "✅" if r['status'] == '✅ Success' else "❌"
        
        print(f"{i:<4} {r['domain']:<25} {status_icon:<12} {privacy:<10} {registrant:<30}")
    
    # Statistics
    print()
    print("=" * 80)
    print("📈 STATISTICS")
    print("=" * 80)
    success_count = sum(1 for r in results if r['status'] == '✅ Success')
    privacy_count = sum(1 for r in results if r['is_privacy'])
    
    print(f"Total domains tested: {len(results)}")
    print(f"Successful lookups: {success_count}")
    print(f"Failed lookups: {len(results) - success_count}")
    print(f"Privacy protected: {privacy_count}")
    print(f"Public registration: {success_count - privacy_count}")
    
    # Save to file
    output_file = "test_results.json"
    with open(output_file, 'w') as f:
        json.dump({
            'timestamp': datetime.now().isoformat(),
            'domains_tested': len(results),
            'results': results
        }, f, indent=2)
    
    print()
    print(f"✅ Results saved to: {output_file}")
    print("=" * 80)
    
    # Detailed results
    print()
    print("📋 DETAILED RESULTS")
    print("=" * 80)
    
    for i, r in enumerate(results, 1):
        print(f"\n{i}. {r['domain']} - {r['company']}")
        print(f"   Status: {r['status']}")
        if r['status'] == '✅ Success':
            print(f"   Registrar: {r.get('registrar', 'N/A')}")
            print(f"   Registry: {r.get('registry', 'N/A')}")
            print(f"   Registrant: {r.get('registrant_org', 'N/A')}")
            print(f"   Expiry: {r.get('expiry_date', 'N/A')}")
            print(f"   Privacy Protected: {'Yes' if r['is_privacy'] else 'No'}")
            if r.get('nameservers'):
                print(f"   Nameservers: {', '.join(r['nameservers'])}")


if __name__ == "__main__":
    asyncio.run(main())

