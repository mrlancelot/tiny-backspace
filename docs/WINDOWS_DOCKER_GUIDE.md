# Windows Docker Setup Guide for Tiny Backspace

This guide helps you create a pre-authenticated Claude Docker image on Windows and upload it to Docker Hub.

## Prerequisites

1. **Docker Desktop for Windows** installed and running
2. **Git Bash** or **PowerShell** (Git Bash recommended)
3. **Node.js** installed locally (for initial Claude authentication)
4. **Docker Hub account**

## Step 1: Initial Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/tiny-backspace.git
cd tiny-backspace
```

2. Install Claude locally (if not already installed):
```bash
npm install -g @anthropic-ai/claude-code
```

3. Authenticate Claude locally:
```bash
claude
# Follow the browser authentication flow
# Test with: claude --version
```

## Step 2: Build the Authenticated Image

### Option A: Use PowerShell Script (Recommended)

Run the PowerShell script:
```powershell
.\build-and-push-windows.ps1
```

### Option B: Manual Steps

1. Build base image:
```bash
docker build -f Dockerfile.base -t tiny-backspace-claude:base .
```

2. Run container for authentication:
```bash
# Run in interactive mode
docker run -it --name claude-auth-session tiny-backspace-claude:base

# Inside container:
claude
# Complete authentication in browser
# Test: claude --version
# Exit container: exit
```

3. Commit authenticated container:
```bash
docker commit claude-auth-session tiny-backspace-claude:authenticated
docker tag tiny-backspace-claude:authenticated tiny-backspace-claude:latest
```

## Step 3: Push to Docker Hub

1. Login to Docker Hub:
```bash
docker login
# Enter your Docker Hub username and password
```

2. Tag and push:
```bash
# Replace YOUR_DOCKERHUB_USERNAME with your actual username
docker tag tiny-backspace-claude:latest YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest
docker push YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest
```

## Step 4: Test the Image

Test locally:
```bash
docker run --rm YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest claude --version
docker run --rm YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest claude --print "Hello world"
```

## Step 5: Update Configuration

Update `daytona_manager_cleaned.py`:
```python
image_map = {
    "claude": "YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest",
    "python": "python:3.11-bullseye",
    "docker": "docker:20.10-dind"
}
```

## Step 6: Run Tiny Backspace

1. Set up environment variables in `.env`:
```
DAYTONA_API_KEY=your_key
GITHUB_TOKEN=your_token
GITHUB_USERNAME=your_username
```

2. Run the API:
```bash
cd api
python main.py
```

3. In another terminal, run the test:
```bash
python test_private_repo.py
```

## Troubleshooting

### Docker Desktop Not Running
- Ensure Docker Desktop is started
- Check Docker icon in system tray
- Run: `docker version` to verify

### Authentication Issues
- Make sure you complete the full Claude authentication in browser
- Test Claude works before exiting container: `claude --version`
- The session may expire after some time

### Push Failures
- Ensure you're logged in: `docker login`
- Check repository name matches your Docker Hub username
- Make repository public temporarily if needed

### Windows Path Issues
- Use forward slashes in paths: `C:/Users/name/project`
- Or use Git Bash for Unix-style paths

## Security Notes

- The authenticated image contains your Claude session
- Only push to private repositories for production use
- Regenerate authentication periodically for security