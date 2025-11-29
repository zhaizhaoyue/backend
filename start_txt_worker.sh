#!/bin/bash
# Start script for TXT Verification Worker

echo "==================================="
echo "TXT Verification Worker"
echo "==================================="
echo ""

# Check if dig is installed
if ! command -v dig &> /dev/null; then
    echo "ERROR: 'dig' command not found."
    echo ""
    echo "Please install dig using one of these commands:"
    echo ""
    echo "  macOS:     brew install bind"
    echo "  Ubuntu:    sudo apt-get install dnsutils"
    echo "  CentOS:    sudo yum install bind-utils"
    echo "  Alpine:    apk add bind-tools"
    echo ""
    exit 1
fi

# Default settings
DB_PATH="${DB_PATH:-./txt_verification.db}"
POLL_INTERVAL="${POLL_INTERVAL:-60}"

echo "Configuration:"
echo "  Database: $DB_PATH"
echo "  Poll Interval: $POLL_INTERVAL seconds"
echo ""

# Start worker
python3 txt_worker.py --db-path "$DB_PATH" --poll-interval "$POLL_INTERVAL"


