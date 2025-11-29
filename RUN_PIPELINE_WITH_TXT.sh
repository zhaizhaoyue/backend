#!/bin/bash

# Complete Domain Verification Pipeline Runner with TXT Verification
# 完整域名验证Pipeline运行脚本（包含TXT验证）

echo "=========================================="
echo "🚀 Complete Domain Verification Pipeline"
echo "   (WITH TXT Verification Execution)"
echo "=========================================="
echo ""

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if input file exists
INPUT_FILE="../Houthoff-Challenge_Domain-Names.csv"

if [ ! -f "$INPUT_FILE" ]; then
    echo -e "${RED}❌ Error: Input file not found: $INPUT_FILE${NC}"
    exit 1
fi

# Activate virtual environment
if [ -d "venv" ]; then
    echo "🔧 Activating virtual environment..."
    source venv/bin/activate
else
    echo -e "${RED}❌ Error: Virtual environment not found${NC}"
    exit 1
fi

# Check dependencies
echo "📦 Checking dependencies..."
python -c "import playwright; from src.core.rdap_client import RDAPClient" 2>/dev/null
if [ $? -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Installing dependencies...${NC}"
    pip install -q playwright pydantic-settings python-dotenv
    playwright install chromium
fi

# Check for dig command
if ! command -v dig &> /dev/null; then
    echo -e "${YELLOW}⚠️  Warning: 'dig' command not found. TXT verification may fail.${NC}"
    echo -e "${YELLOW}   Please install: brew install bind (macOS) or apt install dnsutils (Linux)${NC}"
fi

# Run pipeline
echo ""
echo "🎯 Starting complete 4-stage pipeline..."
echo "   Input: $INPUT_FILE"
echo ""
echo "Pipeline stages:"
echo "  1️⃣  RDAP/WHOIS API Lookup"
echo "  2️⃣  Playwright Scraping"
echo "  3️⃣  TXT Verification Setup"
echo "  4️⃣  TXT Verification Execution (DNS Checking)"
echo ""

RUN_ID=$(date +"%Y%m%d_%H%M%S")
echo "📋 Run ID: $RUN_ID"
echo ""

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}Stage 4 Configuration:${NC}"
echo -e "${BLUE}================================================${NC}"
echo "  ⏱️  Initial wait: 30 seconds"
echo "  🔄 Max attempts: 10"
echo "  ⏲️  Poll interval: 30 seconds"
echo ""
echo -e "${YELLOW}Note: You will have 30 seconds to add DNS TXT records${NC}"
echo -e "${YELLOW}      before the pipeline starts checking.${NC}"
echo ""

# Run the pipeline
PYTHONPATH=$PWD python complete_domain_pipeline.py

# Check if successful
if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}=========================================="
    echo "✅ Pipeline Complete!"
    echo "==========================================${NC}"
    echo ""
    echo "📁 Results location:"
    echo "   data/run_${RUN_ID}/"
    echo ""
    echo "📄 Key files:"
    echo "   results/FINAL_REPORT.txt - Final report"
    echo "   results/all_results_*.csv - All results CSV"
    echo "   screenshots/ - Domain screenshots"
    echo "   intermediate/ - Stage results (including TXT verification)"
    echo ""
    echo "👀 View results:"
    echo "   cat data/run_${RUN_ID}/results/FINAL_REPORT.txt"
    echo ""
else
    echo ""
    echo -e "${RED}=========================================="
    echo "❌ Pipeline failed"
    echo "==========================================${NC}"
    exit 1
fi

