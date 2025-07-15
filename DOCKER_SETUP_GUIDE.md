# Docker Setup Guide for Tiny Backspace

## 1. Install Docker

### On macOS:
```bash
# Download Docker Desktop from:
# https://www.docker.com/products/docker-desktop/

# Or use Homebrew:
brew install --cask docker
```

### On Ubuntu/Debian:
```bash
# Update package index
sudo apt-get update

# Install prerequisites
sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg

# Set up stable repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Install Docker Engine
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io

# Add your user to docker group
sudo usermod -aG docker $USER

# Log out and back in for group changes to take effect
```

## 2. Build the Claude Auth Container

First, ensure you have authenticated with Claude Code locally:

```bash
# Login to Claude Code (if not already logged in)
claude

# This will create authentication files:
# ~/.claude.json
# ~/.claude/.credentials.json
```

Then build the Docker image:

```bash
# Navigate to the project directory
cd /path/to/tiny-backspace

# Build the authenticated container
./build-auth-container.sh
```

## 3. Test the Docker Image

```bash
# Test Claude in the container
docker run --rm claude-auth:latest claude --print "Hello world"

# Interactive mode
docker run -it --rm claude-auth:latest claude

# With workspace mounting
docker run --rm -v "$(pwd)/workspace:/workspace" claude-auth:latest claude --print "List files in the current directory"
```

## 4. Run Tiny Backspace with Docker

### Option A: Using Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Option B: Run API with Docker

```bash
# Build the API container
docker build -t tiny-backspace-api -f Dockerfile.api .

# Run the API
docker run -d \
  --name tiny-backspace-api \
  -p 8000:8000 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -e DAYTONA_API_KEY="$DAYTONA_API_KEY" \
  -e GITHUB_TOKEN="$GITHUB_TOKEN" \
  -e GITHUB_USERNAME="$GITHUB_USERNAME" \
  -e CLAUDE_CODE_OAUTH_TOKEN="$CLAUDE_CODE_OAUTH_TOKEN" \
  tiny-backspace-api
```

### Option C: Use Docker in Daytona Sandboxes

Update your Daytona manager to use the Docker image:

```python
# In daytona_manager_cleaned.py
image_map = {
    "claude": "claude-auth:latest",  # Your built Docker image
    "python": "python:3.11-slim",
    "docker": "docker:20.10-dind"
}
```

## 5. Verify Everything is Working

```bash
# Check Docker is running
docker --version
docker ps

# Check the Claude auth image
docker images | grep claude-auth

# Test the private repo flow
python test_private_repo.py
```

## Troubleshooting

### Docker Permission Issues
```bash
# If you get permission denied
sudo chmod 666 /var/run/docker.sock

# Or add user to docker group
sudo usermod -aG docker $USER
newgrp docker
```

### Building Issues
```bash
# Clean up and rebuild
docker rmi claude-auth:latest
./build-auth-container.sh
```

### Authentication Issues
```bash
# Ensure your Claude authentication is valid
claude --version

# Re-authenticate if needed
claude logout
claude
```