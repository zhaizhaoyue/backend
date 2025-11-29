"""
处理CSV文件，包含DNS TXT记录查询
"""
import csv
import json
import asyncio
import sys
import dns.resolver
from pathlib import Path
from datetime import datetime

try:
    import httpx
except ImportError:
    print("安装 httpx...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "httpx", "dnspython"])
    import httpx


def read_domains_from_csv(csv_file: str) -> list[str]:
    """从CSV文件读取域名列表"""
    domains = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 2 and row[1].strip():
                domain = row[1].strip()
                domains.append(domain)
    return domains


def query_txt_records(domain: str) -> list[str]:
    """查询域名的TXT记录"""
    try:
        resolver = dns.resolver.Resolver()
        resolver.timeout = 5
        resolver.lifetime = 5
        answers = resolver.resolve(domain, 'TXT')
        txt_records = []
        for rdata in answers:
            # TXT记录可能包含多个字符串，需要拼接
            txt_value = ''.join([s.decode('utf-8') if isinstance(s, bytes) else str(s) for s in rdata.strings])
            txt_records.append(txt_value)
        return txt_records
    except dns.resolver.NXDOMAIN:
        return ["NXDOMAIN - 域名不存在"]
    except dns.resolver.NoAnswer:
        return []
    except dns.resolver.Timeout:
        return ["TIMEOUT - 查询超时"]
    except Exception as e:
        return [f"ERROR: {str(e)}"]


def query_dns_info(domain: str) -> dict:
    """查询域名的DNS信息（A记录、MX记录、TXT记录）"""
    info = {
        'a_records': [],
        'mx_records': [],
        'txt_records': [],
        'ns_records': []
    }
    
    resolver = dns.resolver.Resolver()
    resolver.timeout = 5
    resolver.lifetime = 5
    
    # 查询A记录
    try:
        answers = resolver.resolve(domain, 'A')
        info['a_records'] = [str(rdata) for rdata in answers]
    except:
        pass
    
    # 查询MX记录
    try:
        answers = resolver.resolve(domain, 'MX')
        info['mx_records'] = [f"{rdata.preference} {rdata.exchange}" for rdata in answers]
    except:
        pass
    
    # 查询TXT记录
    try:
        answers = resolver.resolve(domain, 'TXT')
        for rdata in answers:
            txt_value = ''.join([s.decode('utf-8') if isinstance(s, bytes) else str(s) for s in rdata.strings])
            info['txt_records'].append(txt_value)
    except:
        pass
    
    # 查询NS记录
    try:
        answers = resolver.resolve(domain, 'NS')
        info['ns_records'] = [str(rdata) for rdata in answers]
    except:
        pass
    
    return info


async def process_domains_with_txt(domains: list[str], base_url: str = "http://localhost:8000"):
    """批量处理域名，包含TXT记录查询"""
    print(f"\n{'='*70}")
    print(f"域名处理工具 (含DNS TXT记录)")
    print(f"{'='*70}\n")
    
    print(f"📊 总共 {len(domains)} 个域名需要处理\n")
    print(f"开始处理...\n")
    
    start_time = datetime.now()
    
    try:
        async with httpx.AsyncClient(timeout=300.0) as client:
            # 1. 检查API服务
            print("1️⃣  检查API服务状态...")
            try:
                health_response = await client.get(f"{base_url}/api/health")
                if health_response.status_code == 200:
                    print("   ✅ API服务正常\n")
                else:
                    print(f"   ⚠️  API状态: {health_response.status_code}\n")
            except Exception as e:
                print(f"   ❌ 无法连接API: {e}")
                print(f"   将只查询DNS记录\n")
                base_url = None
            
            results = []
            
            # 2. 处理每个域名
            print("2️⃣  处理域名 (RDAP + DNS TXT)...\n")
            
            for idx, domain in enumerate(domains, 1):
                print(f"   [{idx}/{len(domains)}] {domain}", end=" ... ")
                
                result = {
                    'domain': domain,
                    'rdap_data': {},
                    'dns_info': {}
                }
                
                # 查询RDAP
                if base_url:
                    try:
                        response = await client.post(
                            f"{base_url}/api/domains/lookup",
                            json={"domains": [domain]}
                        )
                        if response.status_code == 200:
                            data = response.json()
                            if data['results']:
                                result['rdap_data'] = data['results'][0]
                    except:
                        pass
                
                # 查询DNS信息（包括TXT记录）
                try:
                    result['dns_info'] = query_dns_info(domain)
                    txt_count = len(result['dns_info']['txt_records'])
                    print(f"DNS✓ TXT:{txt_count}")
                except Exception as e:
                    print(f"DNS✗ {e}")
                
                results.append(result)
            
            # 3. 生成结果
            print(f"\n3️⃣  生成结果文件...\n")
            
            run_id = datetime.now().strftime("%Y%m%d-%H%M%S")
            
            # 保存JSON
            json_filename = f"results_with_txt_{run_id}.json"
            output_data = {
                'run_id': run_id,
                'started_at': start_time.isoformat(),
                'finished_at': datetime.now().isoformat(),
                'domains_count': len(domains),
                'results': results
            }
            
            with open(json_filename, 'w', encoding='utf-8') as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False, default=str)
            print(f"   ✅ JSON: {json_filename}")
            
            # 保存CSV
            csv_filename = f"results_with_txt_{run_id}.csv"
            with open(csv_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                
                # 表头
                writer.writerow([
                    'domain',
                    'registrar',
                    'registry',
                    'creation_date',
                    'expiry_date',
                    'rdap_nameservers',
                    'dns_a_records',
                    'dns_mx_records',
                    'dns_txt_records',
                    'dns_ns_records',
                    'data_source'
                ])
                
                # 数据行
                for result in results:
                    rdap = result.get('rdap_data', {})
                    dns = result.get('dns_info', {})
                    
                    writer.writerow([
                        result['domain'],
                        rdap.get('registrar', ''),
                        rdap.get('registry', ''),
                        rdap.get('creation_date', ''),
                        rdap.get('expiry_date', ''),
                        '; '.join(rdap.get('nameservers', [])),
                        '; '.join(dns.get('a_records', [])),
                        '; '.join(dns.get('mx_records', [])),
                        '; '.join(dns.get('txt_records', [])),
                        '; '.join(dns.get('ns_records', [])),
                        rdap.get('data_source', '')
                    ])
            
            print(f"   ✅ CSV: {csv_filename}")
            
            # 4. 统计
            print(f"\n4️⃣  统计信息:\n")
            
            rdap_success = sum(1 for r in results if r['rdap_data'].get('registrar'))
            txt_found = sum(1 for r in results if r['dns_info'].get('txt_records'))
            a_found = sum(1 for r in results if r['dns_info'].get('a_records'))
            
            print(f"   RDAP数据获取: {rdap_success}/{len(domains)} ({rdap_success*100//len(domains)}%)")
            print(f"   有TXT记录: {txt_found}/{len(domains)} ({txt_found*100//len(domains) if len(domains) > 0 else 0}%)")
            print(f"   有A记录(活跃): {a_found}/{len(domains)} ({a_found*100//len(domains) if len(domains) > 0 else 0}%)")
            
            # 显示一些TXT记录示例
            print(f"\n   📋 TXT记录示例:")
            shown = 0
            for r in results:
                if r['dns_info'].get('txt_records') and shown < 5:
                    print(f"\n   {r['domain']}:")
                    for txt in r['dns_info']['txt_records'][:3]:
                        if len(txt) > 80:
                            txt = txt[:77] + "..."
                        print(f"     - {txt}")
                    shown += 1
            
            if shown == 0:
                print("     (未找到TXT记录)")
    
    except Exception as e:
        print(f"\n❌ 处理错误: {e}")
        import traceback
        traceback.print_exc()
    
    end_time = datetime.now()
    duration = (end_time - start_time).total_seconds()
    
    print(f"\n{'='*70}")
    print(f"总耗时: {duration:.2f} 秒")
    print(f"平均: {duration/len(domains):.2f} 秒/域名")
    print(f"{'='*70}\n")


async def main():
    """主函数"""
    csv_file = "example_input.csv"
    
    if len(sys.argv) > 1:
        csv_file = sys.argv[1]
    
    if not Path(csv_file).exists():
        print(f"❌ 错误: 找不到文件 '{csv_file}'")
        return
    
    print(f"📁 读取CSV: {csv_file}")
    
    try:
        domains = read_domains_from_csv(csv_file)
        
        if not domains:
            print("❌ CSV中没有域名")
            return
        
        await process_domains_with_txt(domains)
        
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())

