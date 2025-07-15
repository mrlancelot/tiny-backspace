#!/bin/bash
# Run Tiny Backspace using Docker containers

echo "🐳 Running Tiny Backspace with Docker"
echo "===================================="

# Check if claude-auth image exists
if ! docker images | grep -q "claude-auth"; then
    echo "❌ claude-auth:latest image not found!"
    echo "Please run ./setup-docker.sh first"
    exit 1
fi

# Option 1: Run test using Docker directly
echo ""
echo "Option 1: Direct Docker Execution"
echo "---------------------------------"
echo "Testing Claude in Docker container..."

docker run --rm \
    -v "$(pwd):/workspace" \
    -e GITHUB_TOKEN="$GITHUB_TOKEN" \
    -e GITHUB_USERNAME="$GITHUB_USERNAME" \
    claude-auth:latest \
    bash -c "cd /workspace && git clone https://github.com/mrlancelot/tb-test && cd tb-test && claude --print 'Create a README.md file with a title TB Test Project'"

echo ""
echo "Option 2: Using Docker Compose"
echo "------------------------------"
echo "Starting services with docker-compose..."

# Create a minimal docker-compose for testing
cat > docker-compose.test.yml << EOF
version: '3.8'

services:
  claude-agent:
    image: claude-auth:latest
    container_name: claude-agent
    environment:
      - GITHUB_TOKEN=\${GITHUB_TOKEN}
      - GITHUB_USERNAME=\${GITHUB_USERNAME}
    volumes:
      - ./workspace:/workspace
    working_dir: /workspace
    command: >
      bash -c "
        git clone https://\${GITHUB_USERNAME}:\${GITHUB_TOKEN}@github.com/mrlancelot/tb-test.git &&
        cd tb-test &&
        claude --print 'Create a README.md file with the title TB Test Project and a description that says This is a test project for Tiny Backspace autonomous coding agent.' &&
        git add -A &&
        git commit -m 'Add README.md' &&
        git push origin main
      "
EOF

# Run with docker-compose
docker-compose -f docker-compose.test.yml run --rm claude-agent

echo ""
echo "✅ Docker execution complete!"