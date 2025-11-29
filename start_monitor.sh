#!/bin/bash
# 启动增强域名监控系统

echo "=========================================="
echo "🔄 增强域名监控系统"
echo "=========================================="
echo ""

# 默认配置
CSV_FILE="${1:-example_input.csv}"
INTERVAL="${2:-300}"  # 默认5分钟
ITERATIONS="${3:-}"   # 默认无限

# 检查CSV文件
if [ ! -f "$CSV_FILE" ]; then
    echo "❌ 错误: 找不到文件 '$CSV_FILE'"
    echo ""
    echo "使用方法:"
    echo "  $0 <csv_file> [interval_seconds] [max_iterations]"
    echo ""
    echo "示例:"
    echo "  $0 example_input.csv           # 使用默认配置(5分钟间隔)"
    echo "  $0 example_input.csv 600       # 10分钟间隔"
    echo "  $0 example_input.csv 300 3     # 5分钟间隔，最多3轮"
    exit 1
fi

echo "📋 配置:"
echo "  CSV文件: $CSV_FILE"
echo "  监控间隔: $INTERVAL 秒 ($((INTERVAL/60)) 分钟)"
if [ -n "$ITERATIONS" ]; then
    echo "  最大轮数: $ITERATIONS"
else
    echo "  最大轮数: 无限制"
fi
echo ""

# 激活虚拟环境
if [ -d "venv" ]; then
    echo "🔧 激活虚拟环境..."
    source venv/bin/activate
fi

# 检查依赖
echo "🔍 检查依赖..."
python3 -c "import playwright" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "⚠️  Playwright未安装，正在安装..."
    pip install playwright
    playwright install chromium
fi

echo ""
echo "🚀 启动监控..."
echo "   (按 Ctrl+C 可随时停止)"
echo ""
echo "=========================================="
echo ""

# 启动监控
if [ -n "$ITERATIONS" ]; then
    python3 enhanced_domain_monitor.py "$CSV_FILE" --interval "$INTERVAL" --iterations "$ITERATIONS"
else
    python3 enhanced_domain_monitor.py "$CSV_FILE" --interval "$INTERVAL"
fi

echo ""
echo "✓ 监控已结束"

