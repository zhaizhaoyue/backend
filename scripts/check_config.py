"""
Configuration checker script.
Run this to verify your API keys and configuration are set correctly.
"""
from config.settings import settings

print("=" * 60)
print("Configuration Check")
print("=" * 60)

# Check API keys
print("\n[API Keys]")
if settings.deepseek_api_key:
    print(f"  ✓ DeepSeek API Key: {settings.deepseek_api_key[:10]}...")
else:
    print("  ✗ DeepSeek API Key: Not set")

if settings.api_ninjas_key:
    print(f"  ✓ API Ninjas Key: {settings.api_ninjas_key[:10]}...")
else:
    print("  ✗ API Ninjas Key: Not set")

if settings.openai_api_key:
    print(f"  ✓ OpenAI API Key: {settings.openai_api_key[:10]}...")
else:
    print("  ○ OpenAI API Key: Not set (optional)")

# Check paths
print("\n[Path Configuration]")
print(f"  Data Directory: {settings.data_dir}")
print(f"  Database Path: {settings.database_path}")
print(f"  Screenshots: {settings.screenshots_dir}")
print(f"  Exports: {settings.exports_dir}")

# Check server config
print("\n[Server Configuration]")
print(f"  Host: {settings.host}")
print(f"  Port: {settings.port}")
print(f"  Debug: {settings.debug}")
print(f"  App Name: {settings.app_name}")
print(f"  Version: {settings.app_version}")

# Check CORS
print("\n[CORS Configuration]")
print(f"  Allowed Origins: {settings.cors_origins}")

print("\n" + "=" * 60)
print("Configuration Check Complete")
print("=" * 60)
