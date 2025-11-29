"""
Configuration checker script.
Run this to verify your API keys and configuration are set correctly.
"""
from config.settings import settings

print("=" * 60)
print("配置检查 / Configuration Check")
print("=" * 60)

# Check API keys
print("\n[API密钥 / API Keys]")
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
print("\n[路径配置 / Path Configuration]")
print(f"  数据目录 / Data Directory: {settings.data_dir}")
print(f"  数据库路径 / Database Path: {settings.database_path}")
print(f"  截图目录 / Screenshots: {settings.screenshots_dir}")
print(f"  导出目录 / Exports: {settings.exports_dir}")

# Check server config
print("\n[服务器配置 / Server Configuration]")
print(f"  地址 / Host: {settings.host}")
print(f"  端口 / Port: {settings.port}")
print(f"  调试模式 / Debug: {settings.debug}")
print(f"  应用名称 / App Name: {settings.app_name}")
print(f"  版本 / Version: {settings.app_version}")

# Check CORS
print("\n[CORS配置 / CORS Configuration]")
print(f"  允许的源 / Allowed Origins: {settings.cors_origins}")

print("\n" + "=" * 60)
print("配置检查完成 / Configuration Check Complete")
print("=" * 60)
