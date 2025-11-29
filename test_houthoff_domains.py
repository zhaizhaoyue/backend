"""
Test script to process Houthoff Challenge domains using the refactored API.
测试脚本：使用重构后的API处理Houthoff挑战域名。
"""
import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.rdap_client import RDAPClient
from src.core.legal_intel import LegalIntelligence
from src.utils.csv_exporter import CSVExporter
from src.models.domain import DomainResult
from config.settings import settings


async def process_domains_from_csv(csv_file: str):
    """Process domains from CSV file."""
    
    print("=" * 60)
    print("🚀 Houthoff Challenge - Domain Lookup Test")
    print("=" * 60)
    
    # Read domains from CSV
    domains = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1]:  # Check if domain exists in second column
                domain = row[1].strip()
                if domain and '.' in domain:  # Basic domain validation
                    domains.append(domain)
    
    print(f"\n📋 Found {len(domains)} domains to process")
    print(f"📁 Input file: {csv_file}")
    
    # Initialize RDAP client
    rdap_client = RDAPClient(api_ninjas_key=settings.api_ninjas_key)
    
    # Initialize Legal Intelligence (optional - for classification)
    expected_companies = [
        "Ahold",
        "Delhaize",
        "Albert Heijn",
        "Bol.com",
        "Etos",
        "Gall & Gall"
    ]
    legal_intel = LegalIntelligence(expected_group_names=expected_companies)
    
    print(f"\n⚙️  Configuration:")
    print(f"   API Ninjas: {'✓ Configured' if settings.api_ninjas_key else '✗ Not configured'}")
    print(f"   DeepSeek: {'✓ Configured' if settings.deepseek_api_key else '✗ Not configured (not needed)'}")
    print(f"   Expected companies: {', '.join(expected_companies)}")
    
    # Process domains
    results = []
    failed = []
    
    print(f"\n🔍 Processing domains...")
    print("-" * 60)
    
    for i, domain in enumerate(domains, 1):
        print(f"\n[{i}/{len(domains)}] Processing: {domain}")
        
        try:
            # Perform RDAP/WHOIS lookup
            lookup_data, source_url = await rdap_client.lookup_domain(domain)
            
            # Check if we got data
            if lookup_data.get('data_source_type') == 'failed':
                print(f"   ⚠️  No data available")
                failed.append(domain)
                continue
            
            # Display key information
            registrant = lookup_data.get('registrant_org') or lookup_data.get('registrant_name_raw') or 'Unknown'
            registrar = lookup_data.get('registrar') or 'Unknown'
            creation = lookup_data.get('creation_date')
            expiry = lookup_data.get('expiry_date')
            
            print(f"   ✓ Data source: {lookup_data.get('data_source_type', 'unknown')}")
            print(f"   📋 Registrant: {registrant}")
            print(f"   🏢 Registrar: {registrar}")
            if creation:
                print(f"   📅 Created: {creation.strftime('%Y-%m-%d')}")
            if expiry:
                print(f"   ⏰ Expires: {expiry.strftime('%Y-%m-%d')}")
            
            # Classify legal risk (optional)
            is_privacy = rdap_client.detect_privacy_protection(lookup_data)
            if not is_privacy:
                risk_flag, ownership_tag, risk_reasons = legal_intel.classify(
                    registrant_org=lookup_data.get('registrant_org'),
                    registrant_name=lookup_data.get('registrant_name_raw'),
                    is_privacy_protected=is_privacy,
                    expiry_date=expiry
                )
                print(f"   🎯 Risk: {risk_flag} ({ownership_tag})")
                if risk_reasons:
                    for reason in risk_reasons[:1]:  # Show first reason
                        print(f"      • {reason}")
            else:
                print(f"   🔒 Privacy protected")
            
            # Create result
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
            
            results.append(domain_result)
            
            # Delay to avoid rate limiting (RDAP servers have strict limits)
            await asyncio.sleep(2.0)  # 2 second delay between requests
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
            failed.append(domain)
    
    # Generate report
    print("\n" + "=" * 60)
    print("📊 Processing Summary")
    print("=" * 60)
    print(f"✅ Successful: {len(results)}")
    print(f"❌ Failed: {len(failed)}")
    print(f"📈 Success rate: {len(results)/len(domains)*100:.1f}%")
    
    if failed:
        print(f"\n⚠️  Failed domains:")
        for domain in failed[:10]:  # Show first 10
            print(f"   • {domain}")
        if len(failed) > 10:
            print(f"   ... and {len(failed)-10} more")
    
    # Save results
    if results:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Save as JSON
        json_file = f"houthoff_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(
                [result.model_dump(mode='json') for result in results],
                f,
                indent=2,
                default=str
            )
        print(f"\n💾 Saved JSON: {json_file}")
        
        # Save as CSV
        csv_file_out = f"houthoff_results_{timestamp}.csv"
        CSVExporter.save_to_file(results, csv_file_out)
        print(f"💾 Saved CSV: {csv_file_out}")
        
        print(f"\n✅ Processing complete!")
    
    return results


async def main():
    """Main entry point."""
    # Check if CSV file exists
    csv_file = "../Houthoff-Challenge_Domain-Names.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ Error: CSV file not found: {csv_file}")
        return
    
    # Process domains
    results = await process_domains_from_csv(csv_file)
    
    print("\n" + "=" * 60)
    print(f"🎉 Done! Processed {len(results)} domains")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())

