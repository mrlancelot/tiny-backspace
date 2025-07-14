#!/bin/bash

# Quick Start Script for Claude Code + Gemini CLI Environment
# Run this after adding your API keys to .env file

set -e

echo "🚀 Quick Start: Claude Code + Gemini CLI Environment"
echo "=================================================="

# Check if .env exists and has API keys
if [ ! -f ".env" ]; then
    echo "❌ .env file not found. Please create it first."
    exit 1
fi

if grep -q "your_claude_api_key_here" .env; then
    echo "❌ Please add your actual Claude API key to .env file"
    echo "   Edit ANTHROPIC_API_KEY=your_claude_api_key_here"
    exit 1
fi

if grep -q "your_gemini_api_key_here" .env; then
    echo "❌ Please add your actual Gemini API key to .env file"
    echo "   Edit GEMINI_API_KEY=your_gemini_api_key_here"
    exit 1
fi

echo "✅ API keys configured"

# Build and start
echo "🔨 Building and starting environment..."
docker-compose up -d --build

echo ""
echo "🎉 Environment is ready!"
echo ""
echo "Next steps:"
echo "1. Enter the container: docker-compose exec dev-environment bash"
echo "2. Test Claude Code: claude --version"  
echo "3. Test Gemini CLI: gemini --version"
echo "4. Start coding!"
echo ""
echo "To stop: docker-compose down"
echo "To restart: docker-compose restart"