"""
Verify that CSV export includes all successful domains (Stage 1 + Stage 2)
"""
import asyncio
from pathlib import Path
from complete_domain_pipeline import CompleteDomainPipeline
from datetime import datetime

async def test_csv_export():
    """Test CSV export with small dataset."""
    
    # Create test CSV with domains that will need Playwright
    test_csv = Path("test_csv_export.csv")
    with open(test_csv, 'w') as f:
        f.write("1,google.com\n")  # Should succeed in Stage 1
        f.write("2,microsoft.com\n")  # Should succeed in Stage 1
        f.write("3,delhaize.be\n")  # Should fail Stage 1, succeed in Stage 2
    
    run_id = f"test_csv_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    print("=" * 80)
    print("Testing CSV Export with All Successful Domains")
    print("=" * 80)
    print(f"\nRun ID: {run_id}")
    print("\nExpected:")
    print("  - google.com (Stage 1 API)")
    print("  - microsoft.com (Stage 1 API)")
    print("  - delhaize.be (Stage 2 Playwright)")
    print("\nRunning pipeline...\n")
    
    pipeline = CompleteDomainPipeline(run_id)
    
    await pipeline.run_complete_pipeline(
        input_csv=str(test_csv),
        enable_txt_verification=False
    )
    
    # Check CSV output
    csv_file = Path(f"data/run_{run_id}/results/all_results_{run_id}.csv")
    
    if csv_file.exists():
        with open(csv_file, 'r') as f:
            lines = f.readlines()
            domain_count = len(lines) - 1  # Minus header
            
            print("\n" + "=" * 80)
            print("CSV EXPORT VERIFICATION")
            print("=" * 80)
            print(f"\n✅ CSV file created: {csv_file}")
            print(f"📊 Total domains in CSV: {domain_count}")
            print(f"\nCSV Contents:")
            print("".join(lines[:10]))  # Show first 10 lines
            
            if domain_count >= 3:
                print(f"\n✅ SUCCESS: CSV contains all {domain_count} successful domains!")
            else:
                print(f"\n⚠️  WARNING: Expected at least 3 domains, got {domain_count}")
    else:
        print(f"\n❌ ERROR: CSV file not found at {csv_file}")
    
    # Cleanup
    test_csv.unlink(missing_ok=True)
    
    print("\n" + "=" * 80)

if __name__ == "__main__":
    asyncio.run(test_csv_export())

