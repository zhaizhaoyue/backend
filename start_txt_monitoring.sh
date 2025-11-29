#!/bin/bash

# TXT Verification Monitoring Starter
# TXT验证监控启动脚本

RUN_ID=$1

if [ -z "$RUN_ID" ]; then
    echo "=========================================="
    echo "🔐 TXT Verification Monitoring"
    echo "=========================================="
    echo ""
    echo "Usage: ./start_txt_monitoring.sh <run_id>"
    echo ""
    echo "Example:"
    echo "  ./start_txt_monitoring.sh 20251129_113205"
    echo ""
    echo "📁 Available runs:"
    ls -1 data/ 2>/dev/null | grep "^run_" | sed 's/run_/  - /'
    echo ""
    exit 1
fi

RUN_DIR="data/run_${RUN_ID}"

if [ ! -d "$RUN_DIR" ]; then
    echo "❌ Error: Run directory not found: $RUN_DIR"
    echo ""
    echo "Available runs:"
    ls -1 data/ 2>/dev/null | grep "^run_"
    exit 1
fi

DB_PATH="$RUN_DIR/txt_verification.db"

if [ ! -f "$DB_PATH" ]; then
    echo "❌ Error: Database not found: $DB_PATH"
    echo ""
    echo "This run may not have reached stage 3 (TXT verification)."
    echo "Run the complete pipeline first."
    exit 1
fi

echo "=========================================="
echo "🔐 TXT Verification Monitoring"
echo "=========================================="
echo ""
echo "Run ID: $RUN_ID"
echo "Database: $DB_PATH"
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "⚠️  Warning: Virtual environment not found"
fi

# Count pending tasks
PENDING=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM txt_verification_tasks WHERE status='WAITING';" 2>/dev/null || echo "0")
VERIFIED=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM txt_verification_tasks WHERE status='VERIFIED';" 2>/dev/null || echo "0")
FAILED=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM txt_verification_tasks WHERE status='FAILED';" 2>/dev/null || echo "0")
TOTAL=$(sqlite3 "$DB_PATH" "SELECT COUNT(*) FROM txt_verification_tasks;" 2>/dev/null || echo "0")

echo "📊 Status:"
echo "   Total tasks: $TOTAL"
echo "   ⏳ Waiting: $PENDING"
echo "   ✅ Verified: $VERIFIED"
echo "   ❌ Failed: $FAILED"
echo ""

if [ "$TOTAL" -eq 0 ]; then
    echo "⚠️  No TXT verification tasks found in this run."
    echo ""
    echo "Possible reasons:"
    echo "  1. All domains were resolved in stages 1 & 2"
    echo "  2. Pipeline didn't reach stage 3"
    echo "  3. Database is empty"
    echo ""
    echo "Run the complete pipeline to create TXT tasks."
    exit 0
fi

if [ "$PENDING" -eq 0 ]; then
    echo "✅ All tasks are complete! No monitoring needed."
    echo ""
    echo "Summary:"
    echo "  Verified: $VERIFIED"
    echo "  Failed: $FAILED"
    exit 0
fi

# Show instructions
INSTRUCTIONS="$RUN_DIR/results/TXT_VERIFICATION_INSTRUCTIONS.txt"
if [ -f "$INSTRUCTIONS" ]; then
    echo "📄 TXT Verification Instructions:"
    echo "   See: $INSTRUCTIONS"
    echo ""
    echo "First 3 tasks:"
    head -20 "$INSTRUCTIONS"
    echo ""
    echo "   ... (see file for complete instructions)"
    echo ""
fi

echo "🔄 Starting monitoring worker..."
echo "   Checking every 60 seconds"
echo "   Press Ctrl+C to stop"
echo ""
echo "----------------------------------------"

# Start worker with proper Python path
PYTHONPATH=$PWD python txt_worker.py --db-path "$DB_PATH" --poll-interval 60

echo ""
echo "=========================================="
echo "Monitoring stopped"
echo "=========================================="

