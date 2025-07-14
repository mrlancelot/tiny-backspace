# Claude Code Authenticated Docker Container

This repository contains a Docker setup for running Claude Code with pre-baked authentication, eliminating the need to login every time.

## Quick Start

### 1. Prerequisites
- Docker installed and running
- Claude Code authenticated on your local machine (`claude` command working)

### 2. Build the Authenticated Container

```bash
# Make the build script executable
chmod +x build-auth-container.sh

# Build the container (copies your auth automatically)
./build-auth-container.sh
```

### 3. Use the Container

```bash
# Simple prompt
docker run --rm claude-auth:latest claude --print "Write a hello world script"

# Interactive mode
docker run -it --rm claude-auth:latest claude

# With workspace volume
mkdir workspace
docker run --rm -v "$(pwd)/workspace:/workspace" claude-auth:latest claude --print "Create a Python script"
```

## Daytona Integration

### Create Authenticated Daytona Sandbox

```bash
# Install Python dependencies
pip install -r requirements.txt

# Set up your Daytona API key in .env
cp .env.example .env
# Edit .env and add your DAYTONA_API_KEY

# Create authenticated sandbox
python daytona_manager.py create-auth

# Test Claude Code in sandbox
python daytona_manager.py prompt <sandbox-id> "your prompt here"
```

## Files Structure

- `Dockerfile.simple` - Minimal Docker setup with Claude Code + auth
- `build-auth-container.sh` - Build script that handles authentication
- `daytona_manager.py` - Python script for Daytona integration
- `requirements.txt` - Python dependencies
- `.env` - Environment variables (API keys)

## Security Notes

- Authentication files are copied during build and removed from the build context
- The container includes your OAuth tokens - treat it as sensitive
- Don't push the built container to public registries with your auth

## Troubleshooting

### "claude: command not found"
- Ensure you've logged into Claude Code locally first
- Run `claude` to verify it works on your host machine

### Authentication issues
- Delete the container and rebuild: `docker rmi claude-auth:latest`
- Re-login to Claude Code: `claude` and go through auth flow
- Rebuild the container

### Daytona sandbox issues
- Check your `DAYTONA_API_KEY` in `.env`
- Ensure you have access to Daytona API
- Check sandbox logs: `python daytona_manager.py list`