# Creating Pre-Authenticated Claude Docker Image

This guide explains how to create a Docker image with Claude pre-installed and authenticated, which can be used directly in Daytona sandboxes without needing to pass credentials.

## Prerequisites

- Docker installed and running
- Claude Code account with active subscription
- (Optional) Docker Hub account for sharing the image

## Steps

### 1. Build the Base Image

First, build the base Docker image with Claude installed but not authenticated:

```bash
docker build -f Dockerfile.base -t tiny-backspace-claude:base .
```

### 2. Authenticate Claude Interactively

Run the automated script that will guide you through the process:

```bash
# Set your Docker Hub username (optional)
export DOCKER_USERNAME=yourusername

# Run the authentication script
./create-authenticated-image.sh
```

The script will:
1. Build the base image
2. Start an interactive container
3. Guide you to authenticate Claude
4. Save the authenticated state as a new image
5. (Optional) Push to Docker Hub

### Manual Process (Alternative)

If you prefer to do it manually:

```bash
# 1. Run container interactively
docker run -it --name claude-auth-session tiny-backspace-claude:base

# 2. Inside the container, authenticate Claude
claude
# Follow the browser authentication flow

# 3. Exit the container (Ctrl+D or 'exit')

# 4. Commit the container as a new image
docker commit claude-auth-session tiny-backspace-claude:authenticated

# 5. Tag it as latest
docker tag tiny-backspace-claude:authenticated tiny-backspace-claude:latest

# 6. (Optional) Push to Docker Hub
docker tag tiny-backspace-claude:latest yourusername/tiny-backspace-claude:latest
docker push yourusername/tiny-backspace-claude:latest
```

### 3. Update Daytona Manager

Update `daytona_manager_cleaned.py` to use your authenticated image:

```python
image_map = {
    "claude": "yourusername/tiny-backspace-claude:latest",  # Your authenticated image
    "python": "python:3.11-bullseye",
    "docker": "docker:20.10-dind"
}
```

### 4. Test the Image

Test locally before using with Daytona:

```bash
# Test the image
./test-docker-image.sh tiny-backspace-claude:latest

# Or test manually
docker run --rm tiny-backspace-claude:latest claude --version
docker run --rm tiny-backspace-claude:latest claude --print "Hello world"
```

## Security Considerations

⚠️ **Important**: The authenticated image contains your Claude session token. 

- Only push to private Docker registries if sharing
- Or ensure you're comfortable with the access level
- The token may expire after some time, requiring re-authentication

## Troubleshooting

### Authentication Not Persisting

Make sure to:
1. Complete the full authentication flow in the browser
2. Test Claude works before exiting the container
3. Use `docker commit` (not `docker build`) to save the state

### Image Not Found in Daytona

Ensure:
1. The image is pushed to a public registry (Docker Hub)
2. Or Daytona has access to your private registry
3. The image name in `daytona_manager_cleaned.py` matches exactly

### Claude Not Working in Sandbox

Check:
1. Test the image locally first with `./test-docker-image.sh`
2. Ensure the authentication is still valid
3. Check Daytona sandbox logs for errors

## Updating the Image

When you need to update Claude or refresh authentication:

1. Pull the latest base image
2. Rebuild and re-authenticate
3. Push the new version
4. Update the tag in your code if needed