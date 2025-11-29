"""
Check DeepSeek API configuration and test the API
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config.settings import settings
import httpx
import asyncio

def check_config():
    """Check if DeepSeek API key is configured."""
    print("=" * 80)
    print("🔍 DeepSeek API Configuration Check")
    print("=" * 80)
    
    # Check environment variable
    env_key = os.environ.get("DEEPSEEK_API_KEY")
    print(f"\n1️⃣  Environment Variable DEEPSEEK_API_KEY:")
    if env_key:
        print(f"   ✅ Configured: {env_key[:10]}...{env_key[-4:]}")
    else:
        print(f"   ❌ Not set in environment")
    
    # Check settings
    print(f"\n2️⃣  Settings deepseek_api_key:")
    if settings.deepseek_api_key:
        print(f"   ✅ Configured: {settings.deepseek_api_key[:10]}...{settings.deepseek_api_key[-4:]}")
    else:
        print(f"   ❌ Not configured")
    
    # Check .env file
    env_file = Path(".env")
    print(f"\n3️⃣  .env File:")
    if env_file.exists():
        print(f"   ✅ File exists: {env_file.absolute()}")
        with open(env_file) as f:
            content = f.read()
            if "DEEPSEEK_API_KEY" in content:
                print(f"   ✅ Contains DEEPSEEK_API_KEY")
            else:
                print(f"   ⚠️  No DEEPSEEK_API_KEY found in file")
    else:
        print(f"   ❌ .env file not found")
        print(f"   💡 Create {env_file.absolute()}")
    
    return settings.deepseek_api_key is not None


async def test_api():
    """Test DeepSeek API connection."""
    print("\n" + "=" * 80)
    print("🧪 Testing DeepSeek API Connection")
    print("=" * 80)
    
    if not settings.deepseek_api_key:
        print("\n❌ Cannot test: No API key configured")
        return False
    
    try:
        print("\n📡 Sending test request...")
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0)) as client:
            response = await client.post(
                "https://api.deepseek.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.deepseek_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "deepseek-chat",
                    "messages": [
                        {
                            "role": "user",
                            "content": "Hello, respond with: API_TEST_OK"
                        }
                    ],
                    "temperature": 0.1,
                    "max_tokens": 50
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                usage = data.get('usage', {})
                
                print(f"\n✅ API Test Successful!")
                print(f"   Response: {content}")
                print(f"\n📊 Usage:")
                print(f"   Prompt tokens: {usage.get('prompt_tokens', 0)}")
                print(f"   Completion tokens: {usage.get('completion_tokens', 0)}")
                print(f"   Total tokens: {usage.get('total_tokens', 0)}")
                
                return True
            else:
                print(f"\n❌ API Error: {response.status_code}")
                print(f"   Response: {response.text}")
                return False
                
    except Exception as e:
        print(f"\n❌ Connection Error: {str(e)}")
        return False


async def main():
    """Main check."""
    
    # Check configuration
    has_config = check_config()
    
    if has_config:
        # Test API
        api_works = await test_api()
        
        if api_works:
            print("\n" + "=" * 80)
            print("✅ DeepSeek API is properly configured and working!")
            print("=" * 80)
            print("\n💡 The pipeline will use LLM for parsing Playwright results.")
        else:
            print("\n" + "=" * 80)
            print("⚠️  API key configured but connection failed")
            print("=" * 80)
            print("\n💡 Check your API key and network connection.")
    else:
        print("\n" + "=" * 80)
        print("❌ DeepSeek API is NOT configured")
        print("=" * 80)
        print("\n💡 To enable LLM parsing:")
        print("   1. Get API key from: https://platform.deepseek.com")
        print("   2. Create backend/.env file:")
        print("      echo 'DEEPSEEK_API_KEY=sk-xxxxxxxxxx' > backend/.env")
        print("   3. Or set environment variable:")
        print("      export DEEPSEEK_API_KEY=sk-xxxxxxxxxx")
        print("\n⚠️  Currently using regex-only parsing (less accurate)")


if __name__ == "__main__":
    asyncio.run(main())

