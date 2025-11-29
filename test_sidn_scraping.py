"""
Test SIDN.nl scraping for .nl domains
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from complete_domain_pipeline import CompleteDomainPipeline


async def main():
    """Test the pipeline with .nl domains to verify sidn.nl scraping."""
    
    # Generate test run ID
    run_id = f"test_sidn_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Use test CSV with .nl domains
    input_csv = "test_nl_domains.csv"
    
    if not Path(input_csv).exists():
        print(f"❌ Error: Test file not found: {input_csv}")
        return
    
    print("=" * 80)
    print("🧪 Testing SIDN.nl Scraping for .nl Domains")
    print("=" * 80)
    print(f"\nRun ID: {run_id}")
    print(f"Input: {input_csv}")
    print("\nThis test will:")
    print("  1️⃣  Try RDAP/WHOIS API (expected to fail for these domains)")
    print("  2️⃣  Try who.is (expected to fail)")
    print("  3️⃣  Try sidn.nl (should succeed for .nl domains)")
    print("\n" + "=" * 80 + "\n")
    
    # Create and run pipeline (disable TXT verification for this test)
    pipeline = CompleteDomainPipeline(run_id)
    
    await pipeline.run_complete_pipeline(
        input_csv=input_csv,
        enable_txt_verification=False  # Skip TXT verification for this test
    )
    
    print(f"\n🎉 Test complete! Check results in: data/run_{run_id}/")
    print(f"\n📸 Check screenshots in: data/run_{run_id}/screenshots/")
    print(f"    Look for files ending with '_sidn.png' to see sidn.nl results")


if __name__ == "__main__":
    asyncio.run(main())

