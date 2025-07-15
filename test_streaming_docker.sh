#!/bin/bash
# Test streaming functionality using Docker

echo "🐳 Testing Streaming Functionality with Docker"
echo "============================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ docker-compose is not installed. Please install docker-compose first."
    exit 1
fi

# Build and start the Docker environment
echo "📦 Building Docker environment..."
docker-compose build

echo "🚀 Starting Docker containers..."
docker-compose up -d

# Wait for containers to be ready
echo "⏳ Waiting for containers to start..."
sleep 5

# Run streaming tests inside the container
echo "🧪 Running streaming tests..."
docker-compose exec -T dev-environment bash -c "
    cd /workspace
    echo '1. Installing dependencies...'
    pip install -r requirements.txt
    
    echo '2. Running unit tests...'
    pytest test_daytona_manager.py::TestStreamingResponse -v
    
    echo '3. Running streaming example...'
    python streaming_response.py
"

# Clean up
echo "🧹 Cleaning up..."
docker-compose down

echo "✅ Docker-based streaming tests completed!"