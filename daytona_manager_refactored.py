#!/usr/bin/env python3
"""
Refactored Daytona Manager for Claude Integration
Manages Daytona sandboxes with enhanced features for the Tiny Backspace project
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from daytona import Daytona, DaytonaConfig, SandboxState
from daytona import CreateSandboxFromImageParams, Resources
from rich.console import Console
from dotenv import load_dotenv


class PermissionManager:
    """Simple permission manager for automated operations"""
    def __init__(self):
        self.saved_permissions = {
            "CREATE_SANDBOX": {"all": True},
            "EXECUTE_COMMAND": {"all": True},
            "DELETE_SANDBOX": {"all": True}
        }


class DaytonaManagerRefactored:
    """Manages Daytona sandboxes with Claude Code integration"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize Daytona client and configuration"""
        load_dotenv()
        
        self.console = console or Console()
        print(f"DaytonaManagerRefactored initialized with console: {self.console}", flush=True)
        self.api_key = os.getenv('DAYTONA_API_KEY')
        self.api_url = os.getenv('DAYTONA_API_URL', 'https://app.daytona.io/api')
        
        # Initialize permission manager
        self.permission_manager = PermissionManager()
        
        if not self.api_key:
            self.console.print("[red]❌ DAYTONA_API_KEY not found in environment variables[/red]")
            sys.exit(1)
        
        # Initialize Daytona client
        try:
            config = DaytonaConfig(
                api_key=self.api_key,
                api_url=self.api_url
            )
            self.daytona = Daytona(config)
            self.console.print(f"[green]✅ Connected to Daytona at {self.api_url}[/green]")
        except Exception as e:
            self.console.print(f"[red]❌ Failed to connect to Daytona: {e}[/red]")
            sys.exit(1)
    
    def create_sandbox(
        self,
        name: str,
        sandbox_type: str = "claude",
        resources: Optional[Dict[str, Any]] = None
    ) -> Optional[Any]:
        """Create a new Daytona sandbox with Claude pre-configured"""
        
        # Default resources if not provided
        if resources is None:
            resources = {"cpu": 1, "memory": 2}  # Reduced defaults to avoid quota
        
        # Map sandbox type to image
        image_map = {
            "claude": "ubuntu:22.04",  # Use Ubuntu and install Claude CLI manually
            "gemini": "ubuntu:22.04",  # Use Ubuntu and install Gemini CLI manually
            "basic": "daytonaio/sandbox:latest",
            "python": "python:3.11-slim"
        }
        
        image = image_map.get(sandbox_type, image_map["basic"])
        
        try:
            self.console.print(f"\n[cyan]Creating sandbox '{name}' with {sandbox_type} image...[/cyan]")
            self.console.print(f"[dim]Image: {image}[/dim]")
            self.console.print(f"[dim]Resources: CPU={resources.get('cpu', 2)}, Memory={resources.get('memory', 4)}GB[/dim]")
            
            # Create sandbox parameters
            params = CreateSandboxFromImageParams(
                name=name,
                image=image,
                resources=Resources(
                    cpu=resources.get("cpu", 2),
                    memory=resources.get("memory", 4)
                ),
                tags={"type": sandbox_type, "created": datetime.now().isoformat()}
            )
            
            # Create the sandbox
            self.console.print("[dim]Creating sandbox via Daytona API...[/dim]")
            sandbox = self.daytona.create(params)
            
            self.console.print(f"[green]✅ Sandbox created successfully![/green]")
            self.console.print(f"   ID: {sandbox.id}")
            self.console.print(f"   State: {sandbox.state}")
            
            # Wait for sandbox to be ready
            self._wait_for_sandbox_ready(sandbox.id)
            
            return sandbox
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to create sandbox: {e}[/red]")
            print(f"ERROR in create_sandbox: {e}", flush=True)
            import traceback
            traceback_str = traceback.format_exc()
            self.console.print(f"[dim]{traceback_str}[/dim]")
            print(f"Traceback: {traceback_str}", flush=True)
            return None
    
    def _wait_for_sandbox_ready(self, sandbox_id: str, timeout: int = 120):
        """Wait for sandbox to be in running state"""
        import time
        start_time = time.time()
        last_state = None
        
        while time.time() - start_time < timeout:
            try:
                sandbox = self.daytona.get(sandbox_id)
                
                # Log state changes
                if sandbox.state != last_state:
                    self.console.print(f"[dim]Sandbox state: {sandbox.state}[/dim]")
                    last_state = sandbox.state
                
                # Check if sandbox is ready
                if sandbox.state == SandboxState.STARTED:
                    self.console.print(f"[green]✅ Sandbox is ready![/green]")
                    return True
                elif sandbox.state == SandboxState.BUILD_FAILED or sandbox.state == SandboxState.ERROR:
                    raise Exception(f"Sandbox failed to start: {sandbox.state}")
                elif sandbox.state in [SandboxState.CREATING, SandboxState.STARTING, SandboxState.PENDING_BUILD]:
                    # These are expected transitional states
                    pass
                else:
                    self.console.print(f"[yellow]Unexpected state: {sandbox.state}[/yellow]")
                
                time.sleep(2)
            except Exception as e:
                if "Sandbox failed" in str(e):
                    raise
                self.console.print(f"[yellow]Waiting for sandbox... {e}[/yellow]")
                time.sleep(2)
        
        raise Exception(f"Timeout waiting for sandbox to be ready after {timeout} seconds")
    
    def execute_command(
        self,
        sandbox: Any,
        command: str,
        show_output: bool = True
    ) -> Optional[str]:
        """Execute a command in the sandbox"""
        try:
            # Execute command in sandbox using the process interface
            exec_result = sandbox.process.exec(command)
            
            # Extract the actual output from the ExecuteResponse object
            # The ExecuteResponse has a 'result' attribute containing the command output
            output = exec_result.result if hasattr(exec_result, 'result') else str(exec_result)
            
            if show_output and output:
                self.console.print(f"[dim]{output}[/dim]")
            
            return output
            
        except Exception as e:
            self.console.print(f"[red]❌ Command execution failed: {e}[/red]")
            print(f"ERROR in execute_command: {command} - {e}", flush=True)
            # Return empty string instead of None to avoid TypeError
            return ""
    
    def list_sandboxes(self) -> Optional[List[Any]]:
        """List all sandboxes"""
        try:
            sandboxes = self.daytona.list()
            
            if not sandboxes:
                self.console.print("[yellow]No sandboxes found[/yellow]")
                return []
            
            # Display sandboxes in a table
            from rich.table import Table
            table = Table(title="Daytona Sandboxes")
            table.add_column("Name", style="cyan")
            table.add_column("ID", style="dim")
            table.add_column("State", style="green")
            table.add_column("Created", style="yellow")
            
            for sandbox in sandboxes:
                created = sandbox.tags.get("created", "Unknown") if hasattr(sandbox, 'tags') else "Unknown"
                table.add_row(
                    f"Sandbox-{sandbox.id[:8]}",  # Use ID as name since sandbox doesn't have name attribute
                    sandbox.id[:12] + "...",
                    sandbox.state,
                    created
                )
            
            self.console.print(table)
            return sandboxes
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to list sandboxes: {e}[/red]")
            return None
    
    def delete_sandbox(self, sandbox_id: str) -> bool:
        """Delete a sandbox"""
        try:
            self.console.print(f"[yellow]Deleting sandbox {sandbox_id}...[/yellow]")
            
            self.daytona.delete(sandbox_id)
            
            self.console.print(f"[green]✅ Sandbox deleted successfully[/green]")
            return True
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to delete sandbox: {e}[/red]")
            return False
    
    def get_sandbox_info(self, sandbox_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a sandbox"""
        try:
            sandbox = self.daytona.sandboxes.get(sandbox_id)
            
            info = {
                "id": sandbox.id,
                "name": sandbox.name,
                "state": sandbox.state,
                "image": getattr(sandbox, 'image', 'Unknown'),
                "resources": {
                    "cpu": getattr(sandbox.resources, 'cpu', 'Unknown'),
                    "memory": getattr(sandbox.resources, 'memory', 'Unknown')
                },
                "tags": getattr(sandbox, 'tags', {})
            }
            
            return info
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to get sandbox info: {e}[/red]")
            return None


# Main entry point for testing
if __name__ == "__main__":
    manager = DaytonaManagerRefactored()
    
    # Test listing sandboxes
    manager.list_sandboxes()