#!/bin/bash
# Script to start the Tiny Backspace API server

echo "Starting Tiny Backspace API Server..."
echo "=================================="

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your API keys and configuration"
    echo ""
fi

# Navigate to API directory
cd api

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv ../venv
fi

# Activate virtual environment
source ../venv/bin/activate

# Install dependencies if needed
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the server
echo ""
echo "Starting FastAPI server on http://localhost:8000"
echo "API documentation available at http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop the server"
echo "=================================="
echo ""

# Run the server
uvicorn main:app --reload --host 0.0.0.0 --port 8000