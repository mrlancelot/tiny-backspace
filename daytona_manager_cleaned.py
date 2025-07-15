#!/usr/bin/env python3
"""
Daytona Development Environment Manager - Cleaned Version
Creates and manages Claude Code environments using Daytona SDK
"""

import os
import sys
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

from daytona import Daytona, DaytonaConfig, CreateSandboxFromImageParams, Resources, Image

# Fix Windows console encoding for Unicode emojis
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)


class DaytonaManager:
    def __init__(self):
        """Initialize Daytona client with API credentials"""
        self.api_key = os.getenv('DAYTONA_API_KEY')
        self.api_url = os.getenv('DAYTONA_API_URL', 'https://app.daytona.io/api')
        
        if not self.api_key:
            print("❌ DAYTONA_API_KEY not found in environment variables")
            print("   Please check your .env file")
            sys.exit(1)
            
        # Initialize Daytona client
        try:
            config = DaytonaConfig(
                api_key=self.api_key,
                api_url=self.api_url
            )
            self.daytona = Daytona(config)
            print(f"✅ Connected to Daytona at {self.api_url}")
        except Exception as e:
            print(f"❌ Failed to connect to Daytona: {e}")
            sys.exit(1)
    
    def _print_status(self, message: str):
        """Print status message"""
        print(message)
    
    def create_sandbox(self, name: Optional[str] = None, 
                      sandbox_type: str = "claude",
                      resources: Optional[Dict[str, int]] = None) -> Any:
        """Create a new sandbox with specified configuration"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name = f"{sandbox_type}-{timestamp}"
            
        print(f"🚀 Creating {sandbox_type} sandbox: {name}")
        
        # Default resources if not specified
        if not resources:
            resources = {"cpu": 2, "memory": 4}
        
        try:
            # Gather all relevant environment variables
            env_vars = {
                "ANTHROPIC_API_KEY": os.getenv('ANTHROPIC_API_KEY', ''),
                "SANDBOX_TYPE": sandbox_type,
            }
            
            # Add any additional API keys if present
            for key in ['GEMINI_API_KEY', 'GOOGLE_API_KEY', 'OPENAI_API_KEY']:
                if os.getenv(key):
                    env_vars[key] = os.getenv(key)
            
            # Select image based on sandbox type
            image_map = {
                "claude": "node:20-slim",  # Base image - will install Claude
                # Note: pridhvikrishna/tiny-backspace-claude:latest is available for local use
                "python": "python:3.11-bullseye",
                "docker": "docker:20.10-dind"
            }
            
            image = image_map.get(sandbox_type, "ubuntu:latest")
            
            params = CreateSandboxFromImageParams(
                name=name,
                image=image,
                resources=Resources(**resources),
                env_vars=env_vars
            )
            
            sandbox = self.daytona.create(params)
            print(f"✅ Sandbox created: {sandbox.id}")
            
            # Setup the environment based on type
            self.setup_environment(sandbox, sandbox_type)
            
            return sandbox
            
        except Exception as e:
            print(f"❌ Failed to create sandbox: {e}")
            return None
    
    def setup_environment(self, sandbox: Any, env_type: str = "claude"):
        """Setup development environment in sandbox"""
        print(f"📦 Setting up {env_type} environment...")
        
        setup_commands = {
            "claude": [
                # Install required system packages
                "apt-get update",
                "apt-get install -y git curl",
                # Install Claude Code CLI
                "npm install -g @anthropic-ai/claude-code",
                # Verify installation
                "which claude || echo 'Claude command not found'",
                "claude --version || echo 'Claude version check failed'",
            ],
            "python": [
                "apt-get update",
                "apt-get install -y git curl",
                "python3 -m pip install --upgrade pip",
                "pip install ipython jupyter numpy pandas",
            ],
            "docker": [
                "apk add --no-cache git curl bash nodejs npm",
                "dockerd-entrypoint.sh &",
                "sleep 10",
            ]
        }
        
        commands = setup_commands.get(env_type, [])
        
        for cmd in commands:
            try:
                print(f"⚙️  Running: {cmd[:50]}{'...' if len(cmd) > 50 else ''}")
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'exit_code') and response.exit_code == 0:
                    print("✅ Command completed")
                elif hasattr(response, 'result'):
                    print("✅ Command completed")
            except Exception as e:
                print(f"❌ Command failed: {e}")
        
        # Setup authentication if needed
        if env_type == "claude":
            self.setup_claude_auth(sandbox)
    
    def setup_claude_auth(self, sandbox: Any):
        """Setup Claude authentication - currently not working with OAuth token"""
        self._print_status("⚠️  Claude authentication via OAuth token is not working")
        self._print_status("   Claude will require manual authentication or use --print mode")
    
    def list_sandboxes(self):
        """List all active sandboxes"""
        try:
            sandboxes = self.daytona.list()
            print("\n📋 Active Sandboxes:")
            print("-" * 50)
            
            if not sandboxes:
                print("No active sandboxes found")
                return
                
            for sandbox in sandboxes:
                print(f"ID: {sandbox.id}")
                print(f"Name: {getattr(sandbox, 'name', 'N/A')}")
                print(f"Status: {getattr(sandbox, 'status', 'Unknown')}")
                print(f"Created: {getattr(sandbox, 'created_at', 'N/A')}")
                print("-" * 30)
                
        except Exception as e:
            print(f"❌ Failed to list sandboxes: {e}")
    
    def connect_to_sandbox(self, sandbox_id: str) -> Optional[Any]:
        """Connect to an existing sandbox"""
        try:
            sandbox = self.daytona.get(sandbox_id)
            print(f"🔗 Connected to sandbox: {sandbox_id}")
            
            # Test installed tools
            self.test_sandbox_tools(sandbox)
            
            return sandbox
            
        except Exception as e:
            print(f"❌ Failed to connect to sandbox: {e}")
            return None
    
    def test_sandbox_tools(self, sandbox: Any):
        """Test available tools in sandbox"""
        print("\n🧪 Testing sandbox tools...")
        
        test_commands = [
            ("Python", "python3 --version"),
            ("Node.js", "node --version 2>/dev/null || echo 'Not installed'"),
            ("Claude", "claude --version 2>/dev/null || echo 'Not installed'"),
            ("Docker", "docker --version 2>/dev/null || echo 'Not installed'"),
        ]
        
        for tool_name, cmd in test_commands:
            try:
                response = sandbox.process.exec(cmd)
                if hasattr(response, 'result'):
                    result = response.result.strip()
                    if result and "Not installed" not in result:
                        print(f"✅ {tool_name}: {result}")
                    else:
                        print(f"⚠️  {tool_name}: Not available")
            except Exception as e:
                print(f"❌ {tool_name} test failed: {e}")
    
    def execute_command(self, sandbox: Any, command: str, 
                       show_output: bool = True) -> Optional[str]:
        """Execute a command in sandbox and return output"""
        try:
            response = sandbox.process.exec(command)
            
            if hasattr(response, 'result'):
                output = response.result.strip()
                if show_output and output:
                    print(output)
                return output
            
            return None
            
        except Exception as e:
            print(f"❌ Command execution failed: {e}")
            return None
    
    def delete_sandbox(self, sandbox_id: str):
        """Delete a sandbox"""
        try:
            sandbox = self.daytona.get(sandbox_id)
            sandbox.delete()
            print(f"🗑️  Deleted sandbox: {sandbox_id}")
        except Exception as e:
            print(f"❌ Failed to delete sandbox: {e}")


def main():
    """Main CLI interface"""
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    manager = DaytonaManager()
    
    if len(sys.argv) < 2:
        print("\n🌟 Daytona Development Environment Manager")
        print("=" * 50)
        print("Commands:")
        print("  create [name] [type]  - Create new sandbox (types: claude, python, docker)")
        print("  list                  - List all sandboxes")
        print("  connect <id>          - Connect to existing sandbox")
        print("  exec <id> <command>   - Execute command in sandbox")
        print("  delete <id>           - Delete a sandbox")
        print("\nExamples:")
        print("  python daytona_manager_cleaned.py create my-sandbox claude")
        print("  python daytona_manager_cleaned.py list")
        print("  python daytona_manager_cleaned.py exec <id> 'python --version'")
        return
    
    command = sys.argv[1]
    
    if command == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        sandbox_type = sys.argv[3] if len(sys.argv) > 3 else "claude"
        sandbox = manager.create_sandbox(name, sandbox_type)
        if sandbox:
            print(f"\n🎉 Sandbox ready! ID: {sandbox.id}")
            print(f"Connect with: python {sys.argv[0]} connect {sandbox.id}")
    
    elif command == "list":
        manager.list_sandboxes()
    
    elif command == "connect":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        manager.connect_to_sandbox(sys.argv[2])
    
    elif command == "exec":
        if len(sys.argv) < 4:
            print("❌ Usage: exec <sandbox-id> <command>")
            return
        sandbox = manager.connect_to_sandbox(sys.argv[2])
        if sandbox:
            manager.execute_command(sandbox, sys.argv[3])
    
    elif command == "delete":
        if len(sys.argv) < 3:
            print("❌ Please provide sandbox ID")
            return
        manager.delete_sandbox(sys.argv[2])
    
    else:
        print(f"❌ Unknown command: {command}")


if __name__ == "__main__":
    main()