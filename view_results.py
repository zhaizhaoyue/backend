"""
快速查看处理结果的脚本
"""
import json
from collections import Counter

# 读取结果
with open('results_20251129-085815-108f90ca.json', 'r') as f:
    data = json.load(f)

print("\n" + "="*70)
print("域名处理结果查看器")
print("="*70 + "\n")

# 基本信息
print(f"📊 基本信息:")
print(f"  Run ID: {data['run_id']}")
print(f"  总域名数: {data['domains_count']}")
print(f"  开始时间: {data['started_at']}")
print(f"  结束时间: {data['finished_at']}")

# 统计成功获取的数据
registrars = [r['registrar'] for r in data['results'] if r['registrar']]
registries = [r['registry'] for r in data['results'] if r['registry']]
creation_dates = [r['creation_date'] for r in data['results'] if r['creation_date']]

print(f"\n📈 数据获取统计:")
print(f"  成功获取注册商信息: {len(registrars)}/{data['domains_count']} ({len(registrars)*100//data['domains_count']}%)")
print(f"  成功获取注册局信息: {len(registries)}/{data['domains_count']} ({len(registries)*100//data['domains_count']}%)")
print(f"  成功获取创建日期: {len(creation_dates)}/{data['domains_count']} ({len(creation_dates)*100//data['domains_count']}%)")

# 主要注册商
print(f"\n🏢 主要注册商分布:")
for reg, count in Counter(registrars).most_common(5):
    print(f"  {count:2}个 - {reg}")

# TLD分布
tlds = [r['domain'].split('.')[-1] for r in data['results']]
print(f"\n🌍 域名后缀(TLD)分布:")
for tld, count in Counter(tlds).most_common():
    print(f"  .{tld}: {count}个")

# 成功案例展示
print(f"\n✅ 成功获取完整信息的域名示例 (前5个):")
count = 0
for r in data['results']:
    if r['registrar'] and r['registry'] and count < 5:
        print(f"\n  📍 {r['domain']}")
        print(f"     注册商: {r['registrar']}")
        print(f"     注册局: {r['registry']}")
        if r['creation_date']:
            print(f"     创建日期: {r['creation_date'][:10]}")
        if r['nameservers']:
            print(f"     名称服务器: {', '.join(r['nameservers'][:3])}")
        count += 1

# 失败案例
failed = [r['domain'] for r in data['results'] if not r['registrar']]
print(f"\n⚠️  未获取到注册商信息的域名: {len(failed)}个")
if len(failed) <= 10:
    for domain in failed:
        print(f"  - {domain}")
else:
    print(f"  前10个:")
    for domain in failed[:10]:
        print(f"  - {domain}")
    print(f"  ... 还有 {len(failed)-10} 个")

print("\n" + "="*70)
print(f"💡 完整数据请查看:")
print(f"   - JSON: results_20251129-085815-108f90ca.json")
print(f"   - 报告: processing_summary.md")
print("="*70 + "\n")

