#!/bin/bash
# Script to create a pre-authenticated Claude Docker image

set -e

echo "🚀 Creating Pre-Authenticated Claude Docker Image"
echo "================================================"

# Configuration
IMAGE_NAME="tiny-backspace-claude"
DOCKER_USERNAME="${DOCKER_USERNAME:-}"

if [ -z "$DOCKER_USERNAME" ]; then
    echo "⚠️  DOCKER_USERNAME not set. The image will only be available locally."
    echo "   Set DOCKER_USERNAME to push to Docker Hub."
    PUSH_TO_HUB=false
else
    PUSH_TO_HUB=true
fi

# Step 1: Build base image
echo ""
echo "📦 Step 1: Building base Docker image..."
docker build -f Dockerfile.base -t ${IMAGE_NAME}:base .

# Step 2: Run container for authentication
echo ""
echo "🔐 Step 2: Starting container for Claude authentication..."
echo "   This will open an interactive session."
echo ""
echo "   Once inside the container:"
echo "   1. Run: claude"
echo "   2. Follow the browser authentication flow"
echo "   3. Test with: claude --version"
echo "   4. Type 'exit' when done"
echo ""
read -p "Press Enter to continue..."

# Run container interactively
docker run -it \
    --name claude-auth-session \
    -v /tmp:/tmp \
    ${IMAGE_NAME}:base

# Step 3: Commit the authenticated container
echo ""
echo "💾 Step 3: Saving authenticated container as new image..."
docker commit \
    -m "Claude authenticated and ready" \
    claude-auth-session \
    ${IMAGE_NAME}:authenticated

# Step 4: Tag for release
docker tag ${IMAGE_NAME}:authenticated ${IMAGE_NAME}:latest

if [ "$PUSH_TO_HUB" = true ]; then
    # Tag for Docker Hub
    docker tag ${IMAGE_NAME}:latest ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
    
    echo ""
    echo "🌐 Step 4: Pushing to Docker Hub..."
    echo "   Make sure you're logged in: docker login"
    docker push ${DOCKER_USERNAME}/${IMAGE_NAME}:latest
    
    echo ""
    echo "✅ Success! Image available at: ${DOCKER_USERNAME}/${IMAGE_NAME}:latest"
else
    echo ""
    echo "✅ Success! Image available locally as: ${IMAGE_NAME}:latest"
fi

# Cleanup
echo ""
echo "🧹 Cleaning up..."
docker rm claude-auth-session

echo ""
echo "🎉 Done! Your authenticated Claude image is ready."
echo ""
echo "📝 Next steps:"
echo "   1. Update daytona_manager_cleaned.py to use:"
if [ "$PUSH_TO_HUB" = true ]; then
    echo "      image = '${DOCKER_USERNAME}/${IMAGE_NAME}:latest'"
else
    echo "      image = '${IMAGE_NAME}:latest'"
fi
echo "   2. Test with: python test_private_repo.py"