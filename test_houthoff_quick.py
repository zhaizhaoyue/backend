"""
Quick test: Process first 10 domains from Houthoff Challenge
快速测试：处理Houthoff挑战的前10个域名
"""
import asyncio
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent))

from src.core.rdap_client import RDAPClient
from src.core.legal_intel import LegalIntelligence
from src.utils.csv_exporter import CSVExporter
from src.models.domain import DomainResult
from config.settings import settings


async def quick_test():
    """Quick test with first 10 domains."""
    
    print("=" * 70)
    print("🚀 Houthoff Challenge - Quick Test (First 10 Domains)")
    print("=" * 70)
    
    # Read first 10 domains
    csv_file = "../Houthoff-Challenge_Domain-Names.csv"
    domains = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= 10:  # Only first 10
                break
            if len(row) >= 2 and row[1]:
                domain = row[1].strip()
                if domain and '.' in domain:
                    domains.append(domain)
    
    print(f"\n📋 Testing {len(domains)} domains")
    
    # Initialize clients
    rdap_client = RDAPClient(api_ninjas_key=settings.api_ninjas_key)
    expected_companies = ["Ahold", "Delhaize", "Albert Heijn"]
    legal_intel = LegalIntelligence(expected_group_names=expected_companies)
    
    # Process domains
    results = []
    success_count = 0
    
    print(f"\n🔍 Processing...")
    print("-" * 70)
    
    for i, domain in enumerate(domains, 1):
        print(f"\n[{i}/{len(domains)}] {domain:30}", end=" ")
        
        try:
            lookup_data, source_url = await rdap_client.lookup_domain(domain)
            
            if lookup_data.get('data_source_type') == 'failed':
                print("❌ No data")
                continue
            
            registrant = lookup_data.get('registrant_org') or 'Unknown'
            registrar = lookup_data.get('registrar') or 'Unknown'
            
            print(f"✅")
            print(f"      Registrant: {registrant[:40]}")
            print(f"      Registrar: {registrar[:40]}")
            print(f"      Source: {lookup_data.get('data_source_type', 'unknown')}")
            
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
            success_count += 1
            
            # Delay to avoid rate limiting
            await asyncio.sleep(2.0)
            
        except Exception as e:
            print(f"❌ Error: {str(e)[:50]}")
    
    # Summary
    print("\n" + "=" * 70)
    print(f"📊 Results: {success_count}/{len(domains)} successful ({success_count/len(domains)*100:.0f}%)")
    print("=" * 70)
    
    # Save results
    if results:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # JSON
        json_file = f"houthoff_quick_test_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(
                [r.model_dump(mode='json') for r in results],
                f,
                indent=2,
                default=str
            )
        
        # CSV
        csv_file_out = f"houthoff_quick_test_{timestamp}.csv"
        CSVExporter.save_to_file(results, csv_file_out)
        
        print(f"\n💾 Results saved:")
        print(f"   JSON: {json_file}")
        print(f"   CSV: {csv_file_out}")
    
    print("\n✅ Test complete!")
    return results


if __name__ == "__main__":
    asyncio.run(quick_test())

