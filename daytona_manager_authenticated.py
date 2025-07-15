#!/usr/bin/env python3
"""
Example configuration for using pre-authenticated Claude Docker image
Copy this over daytona_manager_cleaned.py after creating your authenticated image
"""

# This is just the image_map section that needs to be updated
# Replace YOUR_DOCKERHUB_USERNAME with your actual Docker Hub username

# For Docker Hub hosted image (accessible from anywhere):
image_map = {
    "claude": "YOUR_DOCKERHUB_USERNAME/tiny-backspace-claude:latest",  # Pre-authenticated image
    "python": "python:3.11-bullseye",
    "docker": "docker:20.10-dind"
}

# For locally available image (only works if Daytona can access your local Docker):
# image_map = {
#     "claude": "tiny-backspace-claude:latest",  # Local pre-authenticated image
#     "python": "python:3.11-bullseye",
#     "docker": "docker:20.10-dind"
# }

# Note: After updating the image_map in daytona_manager_cleaned.py,
# the setup_environment method can be simplified since Claude is already
# installed and authenticated in the image. You can remove:
# - npm install -g @anthropic-ai/claude-code
# - All authentication setup code