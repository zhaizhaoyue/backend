"""
Quick test of the complete pipeline with TXT verification
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

from complete_domain_pipeline import CompleteDomainPipeline


async def main():
    """Test the pipeline with a small set of domains."""
    
    # Generate test run ID
    run_id = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Use test CSV
    input_csv = "test_domains.csv"
    
    if not Path(input_csv).exists():
        print(f"❌ Error: Test file not found: {input_csv}")
        return
    
    print("=" * 80)
    print("🧪 Testing Pipeline with TXT Verification")
    print("=" * 80)
    print(f"\nRun ID: {run_id}")
    print(f"Input: {input_csv}")
    print("\nThis is a quick test with reduced wait times:")
    print("  - Initial wait: 10 seconds")
    print("  - Max attempts: 3")
    print("  - Poll interval: 15 seconds")
    print("\n" + "=" * 80 + "\n")
    
    # Create and run pipeline
    pipeline = CompleteDomainPipeline(run_id)
    
    await pipeline.run_complete_pipeline(
        input_csv=input_csv,
        enable_txt_verification=True,
        txt_wait_time=10,  # Short wait for testing
        txt_max_attempts=3,  # Few attempts
        txt_poll_interval=15  # Shorter interval
    )
    
    print(f"\n🎉 Test complete! Check results in: data/run_{run_id}/")


if __name__ == "__main__":
    asyncio.run(main())

