#!/bin/bash

# Setup DeepSeek API configuration
# 配置DeepSeek API密钥

echo "======================================================================"
echo "🚀 DeepSeek API 配置工具"
echo "======================================================================"
echo ""

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Check if .env exists
if [ -f ".env" ]; then
    echo -e "${YELLOW}📄 发现现有的 .env 文件${NC}"
    
    # Check if DEEPSEEK_API_KEY already exists
    if grep -q "DEEPSEEK_API_KEY" .env; then
        echo -e "${YELLOW}⚠️  DEEPSEEK_API_KEY 已存在${NC}"
        echo ""
        echo "当前值："
        grep "DEEPSEEK_API_KEY" .env
        echo ""
        read -p "是否要更新? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            echo "取消更新"
            exit 0
        fi
    fi
else
    echo -e "${BLUE}📝 创建新的 .env 文件${NC}"
fi

echo ""
echo "======================================================================"
echo "📋 获取 DeepSeek API Key"
echo "======================================================================"
echo ""
echo "1. 访问: ${BLUE}https://platform.deepseek.com${NC}"
echo "2. 注册/登录账号"
echo "3. 创建 API key"
echo "4. 复制 key (格式: sk-xxxxxxxxxxxx)"
echo ""
echo -e "${YELLOW}💡 DeepSeek 提供免费额度，非常便宜！${NC}"
echo ""

# Ask for API key
read -p "请输入你的 DeepSeek API Key (或按 Ctrl+C 取消): " api_key

# Validate format
if [[ ! $api_key =~ ^sk- ]]; then
    echo -e "${RED}❌ API Key 格式错误！应该以 'sk-' 开头${NC}"
    exit 1
fi

# Update or create .env
if [ -f ".env" ]; then
    # Update existing
    if grep -q "DEEPSEEK_API_KEY" .env; then
        # Replace existing line
        sed -i.bak "s/DEEPSEEK_API_KEY=.*/DEEPSEEK_API_KEY=$api_key/" .env
        rm .env.bak 2>/dev/null
        echo -e "${GREEN}✅ 已更新 DEEPSEEK_API_KEY${NC}"
    else
        # Append new line
        echo "DEEPSEEK_API_KEY=$api_key" >> .env
        echo -e "${GREEN}✅ 已添加 DEEPSEEK_API_KEY${NC}"
    fi
else
    # Create new .env
    cat > .env << EOF
# API Keys
API_NINJAS_KEY=your_api_ninjas_key_here
DEEPSEEK_API_KEY=$api_key

# Server Configuration
DEBUG=True
HOST=0.0.0.0
PORT=8000
EOF
    echo -e "${GREEN}✅ 已创建 .env 文件${NC}"
fi

echo ""
echo "======================================================================"
echo "🧪 测试配置"
echo "======================================================================"
echo ""

# Test the configuration
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    python check_deepseek_config.py
else
    echo -e "${RED}❌ 虚拟环境未找到${NC}"
    echo "请先运行: python3 -m venv venv && source venv/bin/activate"
fi

echo ""
echo "======================================================================"
echo "✅ 配置完成！"
echo "======================================================================"
echo ""
echo -e "${GREEN}现在运行 pipeline 将会使用 DeepSeek LLM 进行智能解析！${NC}"
echo ""
echo "运行 pipeline:"
echo "  bash RUN_PIPELINE_WITH_TXT.sh"
echo ""
echo "你会看到类似的输出:"
echo "  [1/43] domain.com                     🤖 LLM parsed successfully"
echo "  [2/43] domain.nl                     📊 Tokens: 2,341"
echo ""
echo -e "${YELLOW}💰 成本估算: 75个域名约 ¥0.15 (非常便宜)${NC}"
echo ""

