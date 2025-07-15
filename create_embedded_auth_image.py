#!/usr/bin/env python3
"""Create an image with embedded Claude authentication data"""

import os
import json
import base64
from pathlib import Path
from daytona import Image

def create_claude_auth_image():
    """Create a Daytona Image with Claude pre-authenticated"""
    
    # Read the local Claude authentication files
    claude_json_path = Path.home() / ".claude.json"
    claude_dir = Path.home() / ".claude"
    
    # Create base64 encoded auth data
    auth_data = {}
    
    # Read .claude.json if it exists
    if claude_json_path.exists():
        with open(claude_json_path, 'r') as f:
            # Only include non-sensitive config
            full_data = json.load(f)
            auth_data['claude_json'] = json.dumps({
                "autoUpdates": full_data.get("autoUpdates", True),
                "installMethod": "npm"
            })
    
    # Check for OAuth token in environment
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    if oauth_token:
        auth_data['oauth_token'] = oauth_token
    
    # Create the image programmatically
    image = Image.base("node:20-slim") \
        .run_commands(
            # Install dependencies
            "apt-get update",
            "apt-get install -y git curl sudo vim",
            "rm -rf /var/lib/apt/lists/*",
            
            # Create non-root user
            "useradd -m -s /bin/bash claude-user",
            "echo 'claude-user ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers",
            
            # Install Claude Code
            "npm install -g @anthropic-ai/claude-code",
            
            # Create directories
            "mkdir -p /home/claude-user/.claude",
            "mkdir -p /home/claude-user/.config/claude-code",
            "mkdir -p /home/claude-user/.local/share/claude-code"
        )
    
    # Add authentication setup if OAuth token is available
    if oauth_token:
        # Create session file content
        session_data = {
            "session": {
                "access_token": oauth_token,
                "expires_at": "2025-12-31T23:59:59.999Z"
            }
        }
        
        image = image.run_commands(
            # Write session file
            f"echo '{json.dumps(session_data)}' > /home/claude-user/.local/share/claude-code/session.json",
            
            # Set permissions
            "chmod 600 /home/claude-user/.local/share/claude-code/session.json",
            
            # Also set as environment variables
            f"echo 'export CLAUDE_CODE_OAUTH_TOKEN={oauth_token}' >> /home/claude-user/.bashrc",
            f"echo 'export CLAUDE_SESSION_KEY={oauth_token}' >> /home/claude-user/.bashrc",
            
            # Fix ownership
            "chown -R claude-user:claude-user /home/claude-user"
        )
    
    # Set user and working directory
    image = image \
        .run_commands("USER claude-user") \
        .workdir("/workspace") \
        .env({"PATH": "/usr/local/bin:$PATH"})
    
    return image

# Export for use in daytona_manager
CLAUDE_AUTH_IMAGE = create_claude_auth_image()