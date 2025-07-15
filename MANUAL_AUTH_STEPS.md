# Manual Steps to Create Authenticated Claude Docker Image

Since the authentication requires interactive browser login, here are the manual steps:

## Step 1: Start Interactive Container

Open a terminal and run:

```bash
docker run -it --name claude-auth-session tiny-backspace-claude:base
```

## Step 2: Authenticate Claude Inside Container

Once inside the container:

```bash
# You should be at /workspace directory
# Run Claude to start authentication
claude

# This will show a URL like:
# Please visit https://claude.ai/authorize?... to authenticate

# Open this URL in your browser and complete the authentication
# After authentication, Claude will start in the terminal
# Type 'exit' or Ctrl+D to exit Claude

# Verify authentication worked
claude --version
# Should show: 1.0.51 (Claude Code) or similar

# Exit the container (but don't remove it)
exit
```

## Step 3: Save Authenticated Container as New Image

Back in your host terminal:

```bash
# Commit the container with authentication preserved
docker commit claude-auth-session tiny-backspace-claude:authenticated

# Tag as latest
docker tag tiny-backspace-claude:authenticated tiny-backspace-claude:latest

# Test the authenticated image
docker run --rm tiny-backspace-claude:latest claude --version
```

## Step 4: (Optional) Push to Docker Hub

If you want to use this image in Daytona from anywhere:

```bash
# Login to Docker Hub
docker login

# Tag for your Docker Hub account
docker tag tiny-backspace-claude:latest YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest

# Push to Docker Hub
docker push YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest
```

## Step 5: Update Code to Use the Image

Edit `daytona_manager_cleaned.py` and update the image_map:

```python
image_map = {
    "claude": "YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest",  # Your authenticated image
    # or if using locally:
    # "claude": "tiny-backspace-claude:latest",
    "python": "python:3.11-bullseye",
    "docker": "docker:20.10-dind"
}
```

## Verification

Test that everything works:

```bash
# Test locally
docker run --rm tiny-backspace-claude:latest claude --print "Hello world"

# Should output something like:
# Hello world! I'm Claude, an AI assistant created by Anthropic.
```

If you see "Invalid API key" or authentication errors, the authentication didn't persist properly. Try the process again.