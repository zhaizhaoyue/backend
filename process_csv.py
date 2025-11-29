"""
处理输入CSV文件并调用域名查询API的脚本
"""
import csv
import json
import asyncio
import sys
from pathlib import Path
from datetime import datetime

try:
    import httpx
except ImportError:
    print("安装 httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx"])
    import httpx


def read_domains_from_csv(csv_file: str) -> list[str]:
    """
    从CSV文件读取域名列表
    
    Args:
        csv_file: CSV文件路径
        
    Returns:
        域名列表
    """
    domains = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        
        for row in reader:
            if len(row) >= 2 and row[1].strip():
                domain = row[1].strip()
                domains.append(domain)
    
    return domains


async def process_domains(domains: list[str], base_url: str = "http://localhost:8000", auto_confirm: bool = False):
    """
    批量处理域名查询
    
    Args:
        domains: 域名列表
        base_url: API基础URL
        auto_confirm: 是否自动确认，不询问用户
    """
    print(f"\n{'='*70}")
    print(f"域名处理工具")
    print(f"{'='*70}\n")
    
    print(f"📊 总共 {len(domains)} 个域名需要处理\n")
    print(f"前10个域名预览:")
    for i, domain in enumerate(domains[:10], 1):
        print(f"  {i}. {domain}")
    
    if len(domains) > 10:
        print(f"  ... 还有 {len(domains) - 10} 个域名")
    
    print(f"\n{'='*70}\n")
    
    # 询问是否继续
    if not auto_confirm:
        try:
            response = input("是否继续处理这些域名? (y/n): ")
            if response.lower() != 'y':
                print("取消处理")
                return
        except EOFError:
            # 非交互式环境，自动继续
            print("检测到非交互式环境，自动继续处理...")
    else:
        print("自动确认模式，开始处理...")
    
    print("\n开始处理...\n")
    
    # 创建请求
    request_data = {
        "domains": domains
    }
    
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # 1. 检查服务健康状态
            print("1️⃣  检查API服务状态...")
            try:
                health_response = await client.get(f"{base_url}/api/health")
                if health_response.status_code == 200:
                    print("   ✅ API服务正常运行\n")
                else:
                    print(f"   ⚠️  API返回状态: {health_response.status_code}\n")
            except Exception as e:
                print(f"   ❌ 无法连接到API服务: {e}")
                print(f"   请确保后端服务运行在 {base_url}")
                return
            
            # 2. 发送域名查询请求
            print("2️⃣  发送域名查询请求...")
            print(f"   提交 {len(domains)} 个域名进行处理...\n")
            
            response = await client.post(
                f"{base_url}/api/domains/lookup",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                
                run_id = result['run_id']
                print(f"   ✅ 处理成功!")
                print(f"   Run ID: {run_id}")
                print(f"   处理域名数: {result['domains_count']}")
                print(f"   开始时间: {result['started_at']}")
                print(f"   完成时间: {result['finished_at']}")
                print(f"   CSV下载URL: {base_url}{result['csv_download_url']}\n")
                
                # 3. 显示结果摘要
                print("3️⃣  结果摘要:\n")
                print(f"{'序号':<6} {'域名':<30} {'注册商':<30} {'所有者':<30}")
                print(f"{'-'*96}")
                
                for idx, domain_result in enumerate(result['results'], 1):
                    domain = domain_result.get('domain', 'N/A')
                    registrar = domain_result.get('registrar') or 'N/A'
                    registrant = domain_result.get('registrant_organization') or 'N/A'
                    
                    # 截断过长的字符串
                    if registrar != 'N/A' and len(registrar) > 27:
                        registrar = registrar[:27] + "..."
                    if registrant != 'N/A' and len(registrant) > 27:
                        registrant = registrant[:27] + "..."
                    
                    print(f"{idx:<6} {domain:<30} {registrar:<30} {registrant:<30}")
                
                # 4. 下载CSV
                print(f"\n4️⃣  下载CSV结果...")
                csv_response = await client.get(f"{base_url}/api/results/{run_id}/csv")
                
                if csv_response.status_code == 200:
                    csv_filename = f"results_{run_id}.csv"
                    with open(csv_filename, 'wb') as f:
                        f.write(csv_response.content)
                    
                    print(f"   ✅ CSV文件已保存: {csv_filename}\n")
                else:
                    print(f"   ❌ CSV下载失败: {csv_response.status_code}\n")
                
                # 5. 保存JSON结果
                json_filename = f"results_{run_id}.json"
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, ensure_ascii=False, default=str)
                
                print(f"   ✅ JSON结果已保存: {json_filename}\n")
                
            else:
                print(f"   ❌ 请求失败: {response.status_code}")
                print(f"   错误信息: {response.text}\n")
    
    except Exception as e:
        print(f"\n❌ 处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*70}")
    print(f"总耗时: {duration:.2f} 秒")
    print(f"平均每个域名: {duration/len(domains):.2f} 秒")
    print(f"{'='*70}\n")


async def main():
    """主函数"""
    # 默认CSV文件路径
    csv_file = "example_input.csv"
    auto_confirm = False
    
    # 检查命令行参数
    import argparse
    parser = argparse.ArgumentParser(description='处理CSV文件中的域名')
    parser.add_argument('csv_file', nargs='?', default='example_input.csv', help='CSV文件路径')
    parser.add_argument('-y', '--yes', action='store_true', help='自动确认，不询问')
    parser.add_argument('--url', default='http://localhost:8000', help='API基础URL')
    
    args = parser.parse_args()
    csv_file = args.csv_file
    auto_confirm = args.yes
    base_url = args.url
    
    # 检查文件是否存在
    if not Path(csv_file).exists():
        print(f"❌ 错误: 找不到文件 '{csv_file}'")
        print(f"\n使用方法: python process_csv.py [csv_file] [-y]")
        print(f"示例: python process_csv.py example_input.csv -y")
        return
    
    print(f"📁 读取CSV文件: {csv_file}")
    
    # 读取域名
    try:
        domains = read_domains_from_csv(csv_file)
        
        if not domains:
            print("❌ 错误: CSV文件中没有找到任何域名")
            return
        
        # 处理域名
        await process_domains(domains, base_url=base_url, auto_confirm=auto_confirm)
        
    except Exception as e:
        print(f"❌ 读取CSV文件时出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

