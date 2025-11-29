"""
将JSON结果转换为CSV格式
"""
import json
import csv
import sys
from pathlib import Path

def convert_json_to_csv(json_file: str, csv_file: str = None):
    """
    将JSON结果文件转换为CSV格式
    
    Args:
        json_file: JSON输入文件路径
        csv_file: CSV输出文件路径（可选，默认使用相同文件名）
    """
    # 读取JSON文件
    print(f"📁 读取JSON文件: {json_file}")
    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 确定输出文件名
    if csv_file is None:
        csv_file = json_file.replace('.json', '.csv')
    
    print(f"📝 转换为CSV: {csv_file}")
    print(f"   处理 {data['domains_count']} 个域名...")
    
    # CSV字段
    fieldnames = [
        'domain',
        'registrant_organization',
        'registrar',
        'registry',
        'creation_date',
        'expiry_date',
        'nameservers',
        'data_source',
        'timestamp'
    ]
    
    # 写入CSV
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        # 写入表头
        writer.writeheader()
        
        # 写入数据行
        for result in data['results']:
            row = {}
            for field in fieldnames:
                value = result.get(field)
                
                # 格式化值
                if value is None:
                    row[field] = ''
                elif isinstance(value, list):
                    # 列表用分号连接
                    row[field] = '; '.join(str(item) for item in value)
                else:
                    row[field] = str(value)
            
            writer.writerow(row)
    
    print(f"✅ CSV文件已生成!")
    print(f"   文件位置: {csv_file}")
    print(f"   共 {data['domains_count']} 行数据")
    
    # 显示统计信息
    success_count = sum(1 for r in data['results'] if r.get('registrar'))
    print(f"\n📊 数据统计:")
    print(f"   成功获取注册商信息: {success_count}/{data['domains_count']} ({success_count*100//data['domains_count']}%)")
    
    return csv_file


def main():
    """主函数"""
    if len(sys.argv) < 2:
        # 默认使用最新的结果文件
        json_file = "results_20251129-085815-108f90ca.json"
        print(f"使用默认文件: {json_file}")
    else:
        json_file = sys.argv[1]
    
    # 检查文件是否存在
    if not Path(json_file).exists():
        print(f"❌ 错误: 找不到文件 '{json_file}'")
        print(f"\n使用方法: python convert_to_csv.py [json_file]")
        return
    
    # 转换
    try:
        csv_file = convert_json_to_csv(json_file)
        
        print(f"\n💡 提示:")
        print(f"   - 可以用Excel打开: {csv_file}")
        print(f"   - 可以用命令行查看: head {csv_file}")
        
    except Exception as e:
        print(f"❌ 转换失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

