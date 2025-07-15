#!/bin/bash
# Script to run Tiny Backspace API

echo "🚀 Starting Tiny Backspace API..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your API keys:"
    echo "  cp .env.example .env"
    echo "  # Edit .env with your credentials"
    exit 1
fi

# Load environment variables
export $(cat .env | grep -v '^#' | xargs)

# Check required environment variables
if [ -z "$DAYTONA_API_KEY" ]; then
    echo "⚠️  Warning: DAYTONA_API_KEY not set"
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "⚠️  Warning: GITHUB_TOKEN not set - PR creation will fail"
fi

# Install dependencies if needed
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

echo "📦 Installing dependencies..."
source venv/bin/activate
pip install -q -r requirements.txt
pip install -q -r api/requirements.txt

# Start the API
echo "🎯 Starting API server..."
echo "📍 API will be available at: http://localhost:8000"
echo "📊 API docs available at: http://localhost:8000/docs"
echo "🧪 Test client available at: file://$(pwd)/api/client_example.html"
echo ""
echo "Press Ctrl+C to stop the server"
echo "------------------------------------------------------------"

# Set PYTHONPATH to include parent directory
export PYTHONPATH="$(pwd):$PYTHONPATH"
cd api && python main.py