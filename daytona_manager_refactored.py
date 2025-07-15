#!/usr/bin/env python3
"""
Daytona Development Environment Manager - Refactored Version
Integrates streaming responses, permissions, and enhanced UI
"""

import os
import sys
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any
from pathlib import Path

from rich.console import Console
from dotenv import load_dotenv

from daytona_manager_cleaned import DaytonaManager
from streaming_response import StreamingResponseHandler
from permission_manager import PermissionManager, OperationType
from enhanced_cli import EnhancedCLI


class DaytonaManagerRefactored(DaytonaManager):
    """Enhanced Daytona Manager with streaming and permissions"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize with enhanced features"""
        super().__init__()
        self.console = console or Console()
        self.permission_manager = PermissionManager(console=self.console)
        self.stream_handler = StreamingResponseHandler(console=self.console)
        
    async def create_sandbox_with_permission(self, 
                                           name: Optional[str] = None,
                                           sandbox_type: str = "claude",
                                           resources: Optional[Dict[str, int]] = None) -> Any:
        """Create sandbox with permission check"""
        # Request permission
        if not self.permission_manager.request_permission(
            OperationType.CREATE_SANDBOX,
            name or f"new-{sandbox_type}-sandbox",
            {
                "type": sandbox_type,
                "resources": resources or {"cpu": 2, "memory": 4}
            },
            risk_level="low"
        ):
            self.console.print("[red]❌ Permission denied for sandbox creation")
            return None
        
        # Create with progress tracking
        with self.console.status(f"Creating {sandbox_type} sandbox..."):
            return self.create_sandbox(name, sandbox_type, resources)
    
    async def execute_with_streaming(self, 
                                   sandbox: Any,
                                   prompt: str,
                                   use_claude: bool = True) -> None:
        """Execute command with streaming response"""
        # Request permission
        if not self.permission_manager.request_permission(
            OperationType.EXECUTE_COMMAND,
            getattr(sandbox, 'id', 'unknown'),
            {
                "type": "claude_prompt" if use_claude else "command",
                "content": prompt[:100] + "..." if len(prompt) > 100 else prompt
            },
            risk_level="medium"
        ):
            self.console.print("[red]❌ Permission denied")
            return
        
        if use_claude:
            # Stream Claude response
            command = f"claude --print '{prompt}'"
            
            self.console.print(f"\n[bold]🚀 Streaming Claude response...[/bold]\n")
            
            # Create async wrapper for sync execute
            async def async_execute(cmd):
                return await asyncio.to_thread(
                    self.execute_command, 
                    sandbox, 
                    cmd, 
                    show_output=False
                )
            
            # Stream response
            response_gen = self.stream_handler.stream_claude_response(
                command,
                async_execute
            )
            
            await self.stream_handler.display_streaming_response(response_gen)
        else:
            # Regular command execution
            self.execute_command(sandbox, prompt)
    
    def delete_sandbox_with_permission(self, sandbox_id: str) -> bool:
        """Delete sandbox with permission check"""
        # Get sandbox info for permission request
        try:
            sandbox = self.daytona.get(sandbox_id)
            sandbox_info = {
                "id": sandbox_id,
                "name": getattr(sandbox, 'name', 'Unknown'),
                "created": getattr(sandbox, 'created_at', 'Unknown')
            }
        except:
            sandbox_info = {"id": sandbox_id}
        
        # Request permission
        if not self.permission_manager.request_permission(
            OperationType.DELETE_SANDBOX,
            sandbox_id,
            sandbox_info,
            risk_level="high"
        ):
            self.console.print("[red]❌ Permission denied for sandbox deletion")
            return False
        
        # Delete sandbox
        self.delete_sandbox(sandbox_id)
        return True
    
    async def setup_environment_with_progress(self, 
                                            sandbox: Any, 
                                            env_type: str = "claude"):
        """Setup environment with progress tracking"""
        steps = {
            "claude": [
                {"name": "Update package manager", "command": "apt-get update"},
                {"name": "Install dependencies", "command": "apt-get install -y curl git"},
                {"name": "Install Node Version Manager", "command": "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"},
                {"name": "Install Node.js", "command": 'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && nvm install 20'},
                {"name": "Install Claude Code", "command": 'export NVM_DIR="$HOME/.nvm" && [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh" && npm install -g @anthropic-ai/claude-code'},
            ],
            "python": [
                {"name": "Update package manager", "command": "apt-get update"},
                {"name": "Install system packages", "command": "apt-get install -y git curl"},
                {"name": "Upgrade pip", "command": "python3 -m pip install --upgrade pip"},
                {"name": "Install Python packages", "command": "pip install ipython jupyter numpy pandas"},
            ]
        }
        
        setup_steps = steps.get(env_type, [])
        
        # Execute with progress
        await self.stream_handler.show_operation_progress(
            f"Setting up {env_type} environment",
            setup_steps,
            lambda cmd: self.execute_command(sandbox, cmd, show_output=False)
        )
        
        # Setup authentication if needed
        if env_type == "claude":
            self.setup_claude_auth(sandbox)


async def main_async():
    """Async main function for enhanced features"""
    load_dotenv()
    
    console = Console()
    
    # Check for command line arguments
    if len(sys.argv) > 1:
        # Use refactored manager for CLI commands
        manager = DaytonaManagerRefactored(console)
        
        command = sys.argv[1]
        
        if command == "create":
            name = sys.argv[2] if len(sys.argv) > 2 else None
            sandbox_type = sys.argv[3] if len(sys.argv) > 3 else "claude"
            
            sandbox = await manager.create_sandbox_with_permission(name, sandbox_type)
            if sandbox:
                console.print(f"\n[green]✅ Sandbox created: {sandbox.id}[/green]")
        
        elif command == "stream":
            if len(sys.argv) < 4:
                console.print("[red]Usage: stream <sandbox-id> '<prompt>'")
                return
            
            sandbox_id = sys.argv[2]
            prompt = sys.argv[3]
            
            sandbox = manager.connect_to_sandbox(sandbox_id)
            if sandbox:
                await manager.execute_with_streaming(sandbox, prompt, use_claude=True)
        
        elif command == "delete":
            if len(sys.argv) < 3:
                console.print("[red]Usage: delete <sandbox-id>")
                return
            
            sandbox_id = sys.argv[2]
            manager.delete_sandbox_with_permission(sandbox_id)
        
        else:
            # Fallback to basic commands
            from daytona_manager_cleaned import main as simple_main
            simple_main()
    
    else:
        # Run enhanced interactive CLI
        cli = EnhancedCLI()
        await cli.run_interactive()


def main():
    """Main entry point"""
    if sys.platform == "win32":
        # Windows event loop policy
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    
    asyncio.run(main_async())


if __name__ == "__main__":
    main()