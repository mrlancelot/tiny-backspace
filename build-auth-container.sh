#!/bin/bash
# Build authenticated Claude Code Docker container
# Usage: ./build-auth-container.sh

echo "🚀 Building Claude Code authenticated container..."

# Check if authentication files exist
if [ ! -f "$HOME/.claude.json" ]; then
    echo "❌ Authentication file not found: $HOME/.claude.json"
    echo "   Please login to Claude Code first: claude"
    exit 1
fi

if [ ! -f "$HOME/.claude/.credentials.json" ]; then
    echo "❌ Credentials file not found: $HOME/.claude/.credentials.json"
    echo "   Please login to Claude Code first: claude"
    exit 1
fi

# Copy authentication files to build directory
echo "🔐 Copying authentication files..."
cp "$HOME/.claude.json" ".claude.json"
mkdir -p .claude
cp "$HOME/.claude/.credentials.json" ".claude/.credentials.json"

# Build the Docker container
echo "🐳 Building Docker container..."
docker build -f Dockerfile.simple -t claude-auth:latest .

# Clean up auth files from build directory (security)
echo "🧹 Cleaning up build files..."
rm -f .claude.json
rm -rf .claude

echo "✅ Claude authenticated container built successfully!"
echo ""
echo "🚀 Usage:"
echo "  # Test the container:"
echo "  docker run --rm claude-auth:latest claude --print \"Hello world\""
echo ""
echo "  # Interactive mode:"
echo "  docker run -it --rm claude-auth:latest claude"
echo ""
echo "  # With workspace:"
echo "  docker run --rm -v \"\$(pwd)/workspace:/workspace\" claude-auth:latest claude --print \"your prompt\""