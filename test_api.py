"""
Test the FastAPI server
"""
import requests
import json
import time

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("=" * 80)
    print("Testing Health Endpoint")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/api/health")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()


def test_pipeline_run():
    """Test pipeline run endpoint."""
    print("=" * 80)
    print("Testing Pipeline Run Endpoint")
    print("=" * 80)
    
    payload = {
        "domains": [
            "google.com",
            "microsoft.com",
            "aholdholding.nl"
        ],
        "enable_txt_verification": False
    }
    
    print(f"Sending request with payload:")
    print(json.dumps(payload, indent=2))
    print()
    
    response = requests.post(
        f"{BASE_URL}/api/pipeline/run",
        json=payload
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    print()
    
    if response.status_code == 200:
        run_id = response.json()["run_id"]
        print(f"✅ Pipeline started with run_id: {run_id}")
        
        # Poll for status
        print("\n" + "=" * 80)
        print("Polling for Status...")
        print("=" * 80)
        
        for i in range(20):  # Poll for up to 20 times
            time.sleep(5)
            status_response = requests.get(f"{BASE_URL}/api/pipeline/status/{run_id}")
            status_data = status_response.json()
            
            print(f"[{i+1}] Status: {status_data['status']} | Stage: {status_data.get('stage', 'N/A')}")
            
            if status_data["status"] in ["completed", "failed"]:
                print(f"\n{'✅' if status_data['status'] == 'completed' else '❌'} Pipeline {status_data['status']}!")
                
                if status_data["status"] == "completed":
                    print(f"\n📥 CSV Download URL: {BASE_URL}{status_data.get('csv_url')}")
                    print(f"📄 Report URL: {BASE_URL}{status_data.get('report_url')}")
                
                break
        
        return run_id
    else:
        print(f"❌ Failed to start pipeline")
        return None


def test_csv_download(run_id):
    """Test CSV download."""
    print("\n" + "=" * 80)
    print("Testing CSV Download")
    print("=" * 80)
    
    response = requests.get(f"{BASE_URL}/api/pipeline/{run_id}/csv")
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        print(f"✅ CSV downloaded successfully")
        print(f"Content-Type: {response.headers.get('content-type')}")
        print(f"Content-Length: {len(response.content)} bytes")
        print(f"\nFirst 500 characters:")
        print(response.text[:500])
    else:
        print(f"❌ Failed to download CSV: {response.text}")


def main():
    """Run all tests."""
    print("\n🧪 Testing FastAPI Server\n")
    
    # Test 1: Health check
    test_health()
    
    # Test 2: Pipeline run
    run_id = test_pipeline_run()
    
    # Test 3: CSV download (if pipeline completed)
    if run_id:
        time.sleep(2)  # Wait a bit more
        test_csv_download(run_id)
    
    print("\n" + "=" * 80)
    print("✅ All tests completed!")
    print("=" * 80)


if __name__ == "__main__":
    main()

