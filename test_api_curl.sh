#!/bin/bash

# Test the Tiny Backspace API with curl

echo "=== Testing Tiny Backspace API ==="
echo ""

# Check if API is running
echo "1. Checking API health..."
curl -s http://localhost:8000/health | jq . || echo "API not running or jq not installed"

echo ""
echo "2. Creating PR with test prompt..."
echo ""

# Create the request
curl -X POST http://localhost:8000/api/code \
  -H "Content-Type: application/json" \
  -H "Accept: text/event-stream" \
  -d '{
    "repo_url": "https://github.com/mrlancelot/tb-test",
    "prompt": "Add a simple Python hello world script that prints \"Hello from Tiny Backspace!\" and shows the current date. Save it as hello_world.py"
  }' \
  --no-buffer 2>&1 | while IFS= read -r line; do
    # Print each line with timestamp
    echo "[$(date '+%H:%M:%S')] $line"
done

echo ""
echo "=== Test Complete ==="
echo ""
echo "Check the output above for:"
echo "- Any error messages"
echo "- PR creation events"
echo "- The final PR URL"