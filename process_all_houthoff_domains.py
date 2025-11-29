"""
Process ALL domains from Houthoff Challenge CSV file.
处理Houthoff挑战CSV文件中的所有域名。

This script will take approximately 2-3 minutes to complete (75 domains * 2 seconds = 150 seconds).
此脚本大约需要2-3分钟完成（75个域名 * 2秒 = 150秒）。
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


async def process_all_domains():
    """Process all domains from CSV file."""
    
    print("=" * 80)
    print("🚀 Houthoff Challenge - Complete Domain Analysis")
    print("=" * 80)
    
    # Read all domains from CSV
    csv_file = "../Houthoff-Challenge_Domain-Names.csv"
    domains = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1]:
                domain = row[1].strip()
                if domain and '.' in domain:
                    domains.append(domain)
    
    print(f"\n📋 Total domains to process: {len(domains)}")
    print(f"⏱️  Estimated time: ~{len(domains) * 2 / 60:.1f} minutes")
    print(f"📁 Input file: {csv_file}")
    
    # Initialize clients
    rdap_client = RDAPClient(api_ninjas_key=settings.api_ninjas_key)
    
    # Expected companies for Ahold Delhaize group
    expected_companies = [
        "Ahold",
        "Ahold Delhaize",
        "Delhaize",
        "Albert Heijn",
        "Bol.com",
        "Etos",
        "Gall & Gall",
        "Ahold Licensing"
    ]
    legal_intel = LegalIntelligence(expected_group_names=expected_companies)
    
    print(f"\n⚙️  Configuration:")
    print(f"   ✓ API Ninjas Key: {'*' * 10}...{settings.api_ninjas_key[-4:] if settings.api_ninjas_key else 'NOT SET'}")
    print(f"   ✓ Expected group: Ahold Delhaize and subsidiaries")
    print(f"   ✓ Delay between requests: 2 seconds (to avoid rate limiting)")
    
    # Process domains
    results = []
    failed = []
    stats = {
        'rdap': 0,
        'whois_api': 0,
        'failed': 0,
        'privacy_protected': 0,
        'inside_group': 0,
        'outside_group': 0
    }
    
    print(f"\n🔍 Processing domains...")
    print("-" * 80)
    
    start_time = datetime.now()
    
    for i, domain in enumerate(domains, 1):
        progress = f"[{i:2d}/{len(domains)}]"
        print(f"\n{progress} {domain:35}", end=" ", flush=True)
        
        try:
            # Perform RDAP/WHOIS lookup
            lookup_data, source_url = await rdap_client.lookup_domain(domain)
            
            # Check if we got data
            if lookup_data.get('data_source_type') == 'failed':
                print("❌ No data available")
                failed.append(domain)
                stats['failed'] += 1
                await asyncio.sleep(2.0)
                continue
            
            # Track data source
            if lookup_data.get('data_source_type') == 'rdap_registry':
                stats['rdap'] += 1
                print("✅ RDAP", end=" ")
            elif lookup_data.get('data_source_type') == 'whois_api':
                stats['whois_api'] += 1
                print("✅ WHOIS", end=" ")
            
            # Get key information
            registrant = lookup_data.get('registrant_org') or lookup_data.get('registrant_name_raw')
            registrar = lookup_data.get('registrar') or 'Unknown'
            creation = lookup_data.get('creation_date')
            expiry = lookup_data.get('expiry_date')
            
            # Check privacy protection
            is_privacy = rdap_client.detect_privacy_protection(lookup_data)
            if is_privacy:
                stats['privacy_protected'] += 1
                print("🔒 Privacy", end="")
            else:
                # Classify legal risk
                if registrant:
                    risk_flag, ownership_tag, risk_reasons = legal_intel.classify(
                        registrant_org=lookup_data.get('registrant_org'),
                        registrant_name=lookup_data.get('registrant_name_raw'),
                        is_privacy_protected=is_privacy,
                        expiry_date=expiry
                    )
                    
                    if ownership_tag == "INSIDE_GROUP":
                        stats['inside_group'] += 1
                        print(f"✓ {registrant[:30]}", end="")
                    else:
                        stats['outside_group'] += 1
                        if registrant:
                            print(f"⚠️  {registrant[:30]}", end="")
                        else:
                            print("⚠️  Unknown registrant", end="")
                else:
                    print("ℹ️  No registrant info", end="")
            
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
            
            # Progress indicator every 10 domains
            if i % 10 == 0:
                elapsed = (datetime.now() - start_time).total_seconds()
                remaining = (len(domains) - i) * 2
                print(f"\n   Progress: {i/len(domains)*100:.0f}% | Elapsed: {elapsed:.0f}s | ETA: ~{remaining:.0f}s")
            
            # Delay to avoid rate limiting
            await asyncio.sleep(2.0)
            
        except Exception as e:
            print(f"❌ Error: {str(e)[:40]}")
            failed.append(domain)
            stats['failed'] += 1
            await asyncio.sleep(2.0)
    
    # Calculate total time
    total_time = (datetime.now() - start_time).total_seconds()
    
    # Generate comprehensive report
    print("\n" + "=" * 80)
    print("📊 PROCESSING COMPLETE - FINAL STATISTICS")
    print("=" * 80)
    
    print(f"\n📈 Overall Results:")
    print(f"   ✅ Successfully processed: {len(results)}/{len(domains)} ({len(results)/len(domains)*100:.1f}%)")
    print(f"   ❌ Failed to retrieve: {len(failed)}")
    print(f"   ⏱️  Total processing time: {total_time:.1f} seconds ({total_time/60:.1f} minutes)")
    print(f"   ⚡ Average per domain: {total_time/len(domains):.1f} seconds")
    
    print(f"\n🔍 Data Sources:")
    print(f"   📡 RDAP (Official Registry): {stats['rdap']}")
    print(f"   🌐 WHOIS API (Fallback): {stats['whois_api']}")
    print(f"   ❌ Failed: {stats['failed']}")
    
    print(f"\n🎯 Ownership Analysis:")
    print(f"   ✅ Inside Group: {stats['inside_group']}")
    print(f"   ⚠️  Outside Group: {stats['outside_group']}")
    print(f"   🔒 Privacy Protected: {stats['privacy_protected']}")
    print(f"   ℹ️  Unknown: {len(results) - stats['inside_group'] - stats['outside_group'] - stats['privacy_protected']}")
    
    if failed:
        print(f"\n⚠️  Failed Domains ({len(failed)}):")
        for domain in failed[:20]:  # Show first 20
            print(f"   • {domain}")
        if len(failed) > 20:
            print(f"   ... and {len(failed)-20} more")
    
    # Save results
    if results:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        
        # Save as JSON (detailed)
        json_file = f"houthoff_complete_results_{timestamp}.json"
        with open(json_file, 'w', encoding='utf-8') as f:
            json.dump(
                [result.model_dump(mode='json') for result in results],
                f,
                indent=2,
                default=str
            )
        
        # Save as CSV (simplified)
        csv_file_out = f"houthoff_complete_results_{timestamp}.csv"
        CSVExporter.save_to_file(results, csv_file_out)
        
        print(f"\n💾 Results Files:")
        print(f"   📄 JSON (detailed): {json_file}")
        print(f"   📊 CSV (simplified): {csv_file_out}")
        
        # Generate summary statistics
        summary = {
            "timestamp": datetime.now().isoformat(),
            "total_domains": len(domains),
            "successful": len(results),
            "failed": len(failed),
            "success_rate": f"{len(results)/len(domains)*100:.1f}%",
            "processing_time_seconds": total_time,
            "stats": stats,
            "failed_domains": failed
        }
        
        summary_file = f"houthoff_summary_{timestamp}.json"
        with open(summary_file, 'w', encoding='utf-8') as f:
            json.dump(summary, f, indent=2)
        
        print(f"   📋 Summary: {summary_file}")
    
    print("\n" + "=" * 80)
    print("✅ ANALYSIS COMPLETE!")
    print("=" * 80)
    
    return results, stats


async def main():
    """Main entry point."""
    csv_file = "../Houthoff-Challenge_Domain-Names.csv"
    
    if not Path(csv_file).exists():
        print(f"❌ Error: CSV file not found: {csv_file}")
        return
    
    # Process all domains
    results, stats = await process_all_domains()
    
    print(f"\n🎉 Successfully analyzed {len(results)} domains from Houthoff Challenge dataset!")


if __name__ == "__main__":
    asyncio.run(main())

