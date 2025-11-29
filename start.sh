#!/bin/bash

# Domain Ownership Due Diligence Tool - Startup Script

echo "🚀 Starting Domain Ownership Due Diligence API..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run setup first:"
    echo "   python -m venv venv"
    echo "   source venv/bin/activate"
    echo "   pip install -r requirements.txt"
    echo "   playwright install chromium"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if Playwright is installed
if ! python -c "import playwright" 2>/dev/null; then
    echo "⚠️  Playwright not installed. Installing..."
    pip install playwright
    playwright install chromium
fi

# Create evidence directory if it doesn't exist
mkdir -p evidence

# Check for .env file
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Using defaults..."
    echo "   (Copy .env.example to .env and configure if needed)"
fi

# Start the server
echo "✅ Starting FastAPI server on http://localhost:8000"
echo "📖 API Documentation: http://localhost:8000/docs"
echo ""

python main.py

