#!/bin/bash
# Test the authenticated Claude Docker image

IMAGE_NAME="${1:-tiny-backspace-claude:latest}"

echo "🧪 Testing Claude Docker Image: $IMAGE_NAME"
echo "=========================================="

# Test 1: Check if Claude is installed
echo ""
echo "📋 Test 1: Checking Claude installation..."
docker run --rm $IMAGE_NAME claude --version

# Test 2: Test Claude with a simple prompt
echo ""
echo "📋 Test 2: Testing Claude with simple prompt..."
docker run --rm $IMAGE_NAME claude --print "Say hello"

# Test 3: Test with a file operation
echo ""
echo "📋 Test 3: Testing file operations..."
docker run --rm $IMAGE_NAME bash -c "echo '# Test' > test.md && claude --print 'What is in test.md?'"

echo ""
echo "✅ Basic tests completed!"
echo ""
echo "🎯 For interactive testing:"
echo "   docker run -it --rm $IMAGE_NAME"