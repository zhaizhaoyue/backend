#!/usr/bin/env python3
"""
Quick setup script to enable DeepSeek API
快速启用DeepSeek API的配置脚本
"""
import os
from pathlib import Path
import sys

def main():
    print("=" * 80)
    print("🚀 启用 DeepSeek API")
    print("=" * 80)
    print()
    
    # Check current directory
    if not Path("complete_domain_pipeline.py").exists():
        print("❌ 错误: 请在 backend 目录下运行此脚本")
        print("   cd backend && python enable_deepseek.py")
        sys.exit(1)
    
    env_file = Path(".env")
    
    # Step 1: Get API key
    print("📋 获取 DeepSeek API Key:")
    print()
    print("   1. 访问: https://platform.deepseek.com")
    print("   2. 注册/登录")
    print("   3. 创建 API key")
    print("   4. 复制 key (格式: sk-xxxxxxxxxxxx)")
    print()
    print("   💡 提供免费额度，75个域名约¥0.15")
    print()
    
    api_key = input("请输入你的 DeepSeek API Key: ").strip()
    
    if not api_key:
        print("❌ 未输入API key，退出")
        sys.exit(1)
    
    if not api_key.startswith("sk-"):
        print("⚠️  警告: API key 通常以 'sk-' 开头")
        confirm = input("确定要继续吗? (y/N): ").strip().lower()
        if confirm != 'y':
            sys.exit(1)
    
    # Step 2: Update or create .env
    print()
    print("📝 配置 .env 文件...")
    
    if env_file.exists():
        # Read existing content
        with open(env_file, 'r') as f:
            lines = f.readlines()
        
        # Check if DEEPSEEK_API_KEY exists
        found = False
        new_lines = []
        for line in lines:
            if line.startswith("DEEPSEEK_API_KEY="):
                new_lines.append(f"DEEPSEEK_API_KEY={api_key}\n")
                found = True
                print("   ✅ 更新了现有的 DEEPSEEK_API_KEY")
            else:
                new_lines.append(line)
        
        if not found:
            new_lines.append(f"\n# DeepSeek LLM API\nDEEPSEEK_API_KEY={api_key}\n")
            print("   ✅ 添加了 DEEPSEEK_API_KEY")
        
        with open(env_file, 'w') as f:
            f.writelines(new_lines)
    else:
        # Create new .env
        content = f"""# API Keys
API_NINJAS_KEY=your_api_ninjas_key_here
DEEPSEEK_API_KEY={api_key}

# Server Configuration
DEBUG=True
HOST=0.0.0.0
PORT=8000
"""
        with open(env_file, 'w') as f:
            f.write(content)
        print("   ✅ 创建了新的 .env 文件")
    
    # Step 3: Test configuration
    print()
    print("🧪 测试配置...")
    print()
    
    # Set environment variable for immediate testing
    os.environ['DEEPSEEK_API_KEY'] = api_key
    
    try:
        # Import and test
        from config.settings import settings
        
        if settings.deepseek_api_key:
            print(f"   ✅ API Key 已加载: {settings.deepseek_api_key[:10]}...{settings.deepseek_api_key[-4:]}")
            
            # Quick API test
            print()
            print("   🔌 测试 API 连接...")
            
            import asyncio
            import httpx
            
            async def test_api():
                try:
                    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
                        response = await client.post(
                            "https://api.deepseek.com/v1/chat/completions",
                            headers={
                                "Authorization": f"Bearer {api_key}",
                                "Content-Type": "application/json"
                            },
                            json={
                                "model": "deepseek-chat",
                                "messages": [{"role": "user", "content": "Test"}],
                                "max_tokens": 10
                            }
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            usage = data.get('usage', {})
                            print(f"   ✅ API 连接成功!")
                            print(f"   📊 测试用量: {usage.get('total_tokens', 0)} tokens")
                            return True
                        else:
                            print(f"   ❌ API 返回错误: {response.status_code}")
                            return False
                except Exception as e:
                    print(f"   ❌ 连接失败: {str(e)}")
                    return False
            
            success = asyncio.run(test_api())
            
            if success:
                print()
                print("=" * 80)
                print("✅ DeepSeek API 已成功启用!")
                print("=" * 80)
                print()
                print("🎉 现在运行 pipeline 将使用 LLM 进行智能解析!")
                print()
                print("运行命令:")
                print("   bash RUN_PIPELINE_WITH_TXT.sh")
                print()
                print("预期输出:")
                print("   [1/43] domain.com     🤖 LLM parsed successfully")
                print("   [2/43] domain.nl      📊 Tokens: 2,341")
                print()
                print("💡 预期准确率提升: 70.7% → 75-80%")
                print("💰 预估成本: 约 ¥0.15 (75个域名)")
                print()
            else:
                print()
                print("⚠️  API key 已保存，但连接测试失败")
                print("   请检查:")
                print("   1. API key 是否正确")
                print("   2. 网络连接是否正常")
                print("   3. API key 是否有效")
                
        else:
            print("   ❌ API Key 未能加载")
            print("   请检查 .env 文件")
            
    except Exception as e:
        print(f"   ❌ 配置测试失败: {e}")
        print()
        print("   💡 .env 文件已保存，重启服务器后生效")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        sys.exit(1)

