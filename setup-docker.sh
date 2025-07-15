#!/bin/bash
# Setup script for Docker-based Tiny Backspace

set -e

echo "🚀 Tiny Backspace Docker Setup"
echo "=============================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed!"
    echo "Please install Docker first:"
    echo "  - macOS: https://www.docker.com/products/docker-desktop/"
    echo "  - Linux: sudo apt-get install docker.io"
    exit 1
fi

# Check if Docker is running
if ! docker info &> /dev/null; then
    echo "❌ Docker is not running!"
    echo "Please start Docker Desktop or the Docker service."
    exit 1
fi

echo "✅ Docker is installed and running"

# Check for Claude authentication files
if [ ! -f "$HOME/.claude.json" ] || [ ! -f "$HOME/.claude/.credentials.json" ]; then
    echo ""
    echo "⚠️  Claude authentication files not found!"
    echo "Please authenticate with Claude Code first:"
    echo "  1. Install Claude Code: npm install -g @anthropic-ai/claude-code"
    echo "  2. Run: claude"
    echo "  3. Follow the authentication prompts"
    echo ""
    read -p "Press Enter once you've authenticated with Claude..."
fi

# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env and add your API keys:"
    echo "  - DAYTONA_API_KEY"
    echo "  - GITHUB_TOKEN (with Contents permission)"
    echo "  - GITHUB_USERNAME"
    echo "  - CLAUDE_CODE_OAUTH_TOKEN"
    exit 1
fi

# Load environment variables
source .env

# Verify required variables
missing_vars=()
[ -z "$DAYTONA_API_KEY" ] && missing_vars+=("DAYTONA_API_KEY")
[ -z "$GITHUB_TOKEN" ] && missing_vars+=("GITHUB_TOKEN")
[ -z "$GITHUB_USERNAME" ] && missing_vars+=("GITHUB_USERNAME")

if [ ${#missing_vars[@]} -ne 0 ]; then
    echo "❌ Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo "Please edit .env and add the missing values."
    exit 1
fi

# Build Claude auth container
echo ""
echo "🐳 Building Claude authenticated container..."
if ./build-auth-container.sh; then
    echo "✅ Claude container built successfully"
else
    echo "❌ Failed to build Claude container"
    exit 1
fi

# Test Claude container
echo ""
echo "🧪 Testing Claude container..."
if docker run --rm claude-auth:latest claude --version > /dev/null 2>&1; then
    echo "✅ Claude container is working"
else
    echo "⚠️  Claude container test failed, but continuing..."
fi

# Build API container
echo ""
echo "🐳 Building API container..."
docker build -f Dockerfile.api -t tiny-backspace-api:latest .
echo "✅ API container built"

# Start services
echo ""
echo "🚀 Starting services..."
docker-compose -f docker-compose.full.yml up -d

# Wait for API to be ready
echo ""
echo "⏳ Waiting for API to start..."
for i in {1..30}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ API is ready!"
        break
    fi
    sleep 1
done

# Show status
echo ""
echo "📊 Service Status:"
docker-compose -f docker-compose.full.yml ps

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps:"
echo "  1. Test the API: curl http://localhost:8000/health"
echo "  2. Run the test: python test_private_repo.py"
echo "  3. View logs: docker-compose -f docker-compose.full.yml logs -f"
echo "  4. Stop services: docker-compose -f docker-compose.full.yml down"
echo ""
echo "📚 For more information, see DOCKER_SETUP_GUIDE.md"