#!/usr/bin/env python3
"""
Alternative approach: Setup Claude authentication using OAuth token
This avoids the need for private Docker images
"""

import os
import json
from daytona_manager_cleaned import DaytonaManager

class DaytonaManagerWithAuth(DaytonaManager):
    """Extended manager that sets up Claude authentication"""
    
    def setup_claude_auth(self, sandbox):
        """Setup Claude authentication using OAuth token"""
        oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
        
        if not oauth_token:
            self._print_status("⚠️  No CLAUDE_CODE_OAUTH_TOKEN found")
            return
            
        self._print_status("🔐 Setting up Claude authentication...")
        
        # Create the OAuth configuration that Claude expects
        # This mimics what happens when you authenticate interactively
        oauth_config = {
            "session": {
                "access_token": oauth_token,
                "expires_at": "2025-12-31T23:59:59.999Z"
            }
        }
        
        # Setup commands to create Claude's auth structure
        auth_commands = [
            # Create necessary directories
            "mkdir -p ~/.local/share/claude-code",
            "mkdir -p ~/.config/claude-code",
            
            # Write the session file
            f"echo '{json.dumps(oauth_config)}' > ~/.local/share/claude-code/session.json",
            
            # Set proper permissions
            "chmod 600 ~/.local/share/claude-code/session.json",
            
            # Also try environment variable approach
            f"echo 'export CLAUDE_SESSION_KEY={oauth_token}' >> ~/.bashrc",
            f"echo 'export CLAUDE_CODE_OAUTH_TOKEN={oauth_token}' >> ~/.bashrc",
            "source ~/.bashrc"
        ]
        
        for cmd in auth_commands:
            try:
                self.execute_command(sandbox, cmd, show_output=False)
            except Exception as e:
                print(f"⚠️  Auth setup warning: {e}")
        
        self._print_status("✅ Authentication configured")
        
        # Test authentication
        self._print_status("🧪 Testing Claude authentication...")
        test_result = self.execute_command(
            sandbox,
            f'CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}" claude --version 2>&1',
            show_output=True
        )
        
        if "Invalid API key" in test_result or "login" in test_result:
            self._print_status("⚠️  Authentication may not be working properly")
        else:
            self._print_status("✅ Claude is ready!")

# Usage:
# manager = DaytonaManagerWithAuth()
# sandbox = manager.create_sandbox("test", "claude")