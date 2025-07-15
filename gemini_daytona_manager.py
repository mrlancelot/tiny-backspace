#!/usr/bin/env python3
"""
Gemini-Daytona Development Environment Manager
Creates and manages Gemini CLI environments using Daytona SDK
"""

import os
import sys
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List
from pathlib import Path

from daytona import Daytona, DaytonaConfig
from daytona import CreateSandboxFromImageParams, Resources
from rich.console import Console
from dotenv import load_dotenv


class GeminiDaytonaManager:
    """Manages Daytona sandboxes with Gemini CLI integration"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize Daytona client and Gemini configuration"""
        load_dotenv()
        
        self.console = console or Console()
        self.api_key = os.getenv('DAYTONA_API_KEY')
        self.api_url = os.getenv('DAYTONA_API_URL', 'https://app.daytona.io/api')
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            self.console.print("[red]❌ DAYTONA_API_KEY not found in environment variables[/red]")
            sys.exit(1)
            
        if not self.gemini_api_key:
            self.console.print("[yellow]⚠️  GEMINI_API_KEY not found - Gemini CLI will need manual authentication[/yellow]")
        
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
    
    def create_gemini_sandbox(self, 
                            name: Optional[str] = None,
                            resources: Optional[Dict[str, int]] = None) -> Any:
        """Create a new sandbox with Gemini CLI installed"""
        if not name:
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            name = f"gemini-sandbox-{timestamp}"
        
        self.console.print(f"[bold blue]🚀 Creating Gemini sandbox: {name}[/bold blue]")
        
        try:
            # Default resources if not specified
            if not resources:
                resources = {"cpu": 2, "memory": 4}
            
            # Create sandbox with Node.js base image
            params = CreateSandboxFromImageParams(
                name=name,
                image="node:20-slim",
                resources=Resources(**resources),
                env_vars={
                    "GEMINI_API_KEY": self.gemini_api_key or "",
                    "SANDBOX_TYPE": "gemini"
                }
            )
            
            sandbox = self.daytona.create(params)
            self.console.print(f"[green]✅ Sandbox created: {sandbox.id}[/green]")
            
            # Setup Gemini CLI in the sandbox
            self.setup_gemini_cli(sandbox)
            
            return sandbox
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to create sandbox: {e}[/red]")
            return None
    
    def setup_gemini_cli(self, sandbox: Any) -> bool:
        """Install and configure Gemini CLI in the sandbox"""
        self.console.print("[blue]🔧 Setting up Gemini CLI...[/blue]")
        
        setup_commands = [
            # Update and install basic tools
            "apt-get update -qq",
            "apt-get install -y curl git build-essential python3 python3-pip",
            
            # Install Gemini CLI globally
            "npm install -g @google/generative-ai-cli",
            
            # Setup Gemini configuration if API key is available
            f"mkdir -p /home/developer/.gemini && echo '{{\"apiKey\": \"{self.gemini_api_key}\"}}' > /home/developer/.gemini/config.json" if self.gemini_api_key else "echo 'Skipping Gemini auth setup'",
            
            # Install GitHub CLI for PR creation
            "curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | apt-key add -",
            "echo 'deb https://cli.github.com/packages stable main' > /etc/apt/sources.list.d/github-cli.list",
            "apt-get update -qq && apt-get install -y gh",
            
            # Verify installations
            "gemini --version || echo 'Gemini CLI not found'",
            "gh --version || echo 'GitHub CLI not found'"
        ]
        
        for cmd in setup_commands:
            try:
                self.console.print(f"[dim]⚙️  {cmd[:50]}...[/dim]")
                result = self.execute_command(sandbox, cmd, show_output=False)
                if result and "error" not in str(result).lower():
                    self.console.print(f"[green]   ✅[/green]")
                else:
                    self.console.print(f"[yellow]   ⚠️  Command completed with warnings[/yellow]")
            except Exception as e:
                self.console.print(f"[red]   ❌ Failed: {str(e)[:50]}[/red]")
                # Continue with other commands even if one fails
        
        self.console.print("[green]✅ Gemini CLI setup complete[/green]")
        return True
    
    def execute_command(self, sandbox: Any, command: str, show_output: bool = True) -> str:
        """Execute a command in the sandbox"""
        try:
            result = sandbox.process.exec(command)
            
            if hasattr(result, 'stdout'):
                output = result.stdout
            elif hasattr(result, 'result'):
                output = result.result
            else:
                output = str(result)
            
            if show_output and output:
                self.console.print(f"[dim]{output}[/dim]")
            
            return output
            
        except Exception as e:
            error_msg = f"Command execution failed: {e}"
            if show_output:
                self.console.print(f"[red]{error_msg}[/red]")
            return error_msg
    
    def clone_repository(self, sandbox: Any, repo_url: str) -> bool:
        """Clone a GitHub repository in the sandbox"""
        self.console.print(f"[blue]📦 Cloning repository: {repo_url}[/blue]")
        
        # Extract repo name from URL
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        
        commands = [
            "mkdir -p /workspace",
            f"cd /workspace && git clone {repo_url}",
            f"cd /workspace/{repo_name} && pwd"
        ]
        
        for cmd in commands:
            result = self.execute_command(sandbox, cmd)
            if cmd.startswith("mkdir"):
                continue  # mkdir doesn't produce output on success
            if "error" in str(result).lower() or "fatal" in str(result).lower():
                self.console.print(f"[red]❌ Failed to clone repository[/red]")
                return False
        
        self.console.print(f"[green]✅ Repository cloned successfully[/green]")
        return True
    
    def execute_gemini_prompt(self, sandbox: Any, prompt: str, repo_name: str) -> Dict[str, Any]:
        """Execute a Gemini prompt in the sandbox context"""
        self.console.print(f"[blue]🤖 Executing Gemini prompt...[/blue]")
        
        # Create a context-aware prompt
        gemini_prompt = f"""
You are working in a Git repository located at /workspace/{repo_name}.
Your task is to: {prompt}

Please analyze the codebase and make the necessary changes.
After making changes, create a feature branch and prepare for a pull request.
"""
        
        # Execute Gemini CLI with the prompt
        gemini_command = f'cd /workspace/{repo_name} && gemini "{gemini_prompt}"'
        
        result = self.execute_command(sandbox, gemini_command)
        
        return {
            "success": "error" not in str(result).lower(),
            "output": result,
            "repo_path": f"/workspace/{repo_name}"
        }
    
    def create_pull_request(self, sandbox: Any, repo_name: str, branch_name: str, pr_title: str, pr_body: str) -> Optional[str]:
        """Create a pull request using GitHub CLI"""
        self.console.print("[blue]🔀 Creating pull request...[/blue]")
        
        github_token = os.getenv('GITHUB_TOKEN')
        if not github_token:
            self.console.print("[red]❌ GITHUB_TOKEN not found in environment[/red]")
            return None
        
        commands = [
            f"cd /workspace/{repo_name}",
            f"git config --global user.email '{os.getenv('GITHUB_EMAIL', 'bot@example.com')}'",
            f"git config --global user.name '{os.getenv('GITHUB_USERNAME', 'Gemini Bot')}'",
            f"git checkout -b {branch_name}",
            "git add -A",
            f'git commit -m "{pr_title}"',
            f"GH_TOKEN={github_token} gh auth login --with-token",
            f"git push origin {branch_name}",
            f'gh pr create --title "{pr_title}" --body "{pr_body}"'
        ]
        
        pr_url = None
        for cmd in commands:
            result = self.execute_command(sandbox, cmd)
            if "github.com" in str(result) and "/pull/" in str(result):
                pr_url = result.strip()
        
        if pr_url:
            self.console.print(f"[green]✅ Pull request created: {pr_url}[/green]")
        else:
            self.console.print("[red]❌ Failed to create pull request[/red]")
        
        return pr_url
    
    def list_sandboxes(self) -> List[Dict[str, Any]]:
        """List all Daytona sandboxes"""
        try:
            sandboxes = self.daytona.list()
            sandbox_list = []
            
            for sandbox in sandboxes:
                sandbox_info = {
                    "id": getattr(sandbox, 'id', 'Unknown'),
                    "name": getattr(sandbox, 'name', 'Unknown'),
                    "status": getattr(sandbox, 'status', 'Unknown'),
                    "created": getattr(sandbox, 'created_at', 'Unknown')
                }
                sandbox_list.append(sandbox_info)
            
            return sandbox_list
            
        except Exception as e:
            self.console.print(f"[red]❌ Failed to list sandboxes: {e}[/red]")
            return []
    
    def delete_sandbox(self, sandbox_id: str) -> bool:
        """Delete a sandbox"""
        try:
            sandbox = self.daytona.get(sandbox_id)
            sandbox.delete()
            self.console.print(f"[green]✅ Sandbox {sandbox_id} deleted[/green]")
            return True
        except Exception as e:
            self.console.print(f"[red]❌ Failed to delete sandbox: {e}[/red]")
            return False
    
    def connect_to_sandbox(self, sandbox_id: str) -> Optional[Any]:
        """Connect to an existing sandbox"""
        try:
            sandbox = self.daytona.get(sandbox_id)
            self.console.print(f"[green]✅ Connected to sandbox: {sandbox_id}[/green]")
            return sandbox
        except Exception as e:
            self.console.print(f"[red]❌ Failed to connect to sandbox: {e}[/red]")
            return None


def main():
    """Main CLI interface"""
    console = Console()
    manager = GeminiDaytonaManager(console)
    
    if len(sys.argv) < 2:
        console.print("[bold]Gemini-Daytona Manager[/bold]")
        console.print("\nUsage:")
        console.print("  create [name]     - Create a new Gemini sandbox")
        console.print("  list             - List all sandboxes")
        console.print("  delete <id>      - Delete a sandbox")
        console.print("  code <id> <repo_url> '<prompt>' - Execute coding task")
        return
    
    command = sys.argv[1]
    
    if command == "create":
        name = sys.argv[2] if len(sys.argv) > 2 else None
        sandbox = manager.create_gemini_sandbox(name)
        if sandbox:
            console.print(f"\n[bold green]Sandbox ID: {sandbox.id}[/bold green]")
    
    elif command == "list":
        sandboxes = manager.list_sandboxes()
        if sandboxes:
            console.print("\n[bold]Active Sandboxes:[/bold]")
            for sb in sandboxes:
                console.print(f"  • {sb['id']} - {sb['name']} ({sb['status']})")
        else:
            console.print("[yellow]No sandboxes found[/yellow]")
    
    elif command == "delete":
        if len(sys.argv) < 3:
            console.print("[red]Usage: delete <sandbox-id>[/red]")
            return
        manager.delete_sandbox(sys.argv[2])
    
    elif command == "code":
        if len(sys.argv) < 5:
            console.print("[red]Usage: code <sandbox-id> <repo-url> '<prompt>'[/red]")
            return
        
        sandbox_id = sys.argv[2]
        repo_url = sys.argv[3]
        prompt = sys.argv[4]
        
        sandbox = manager.connect_to_sandbox(sandbox_id)
        if sandbox:
            # Clone repo
            if manager.clone_repository(sandbox, repo_url):
                repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
                
                # Execute Gemini prompt
                result = manager.execute_gemini_prompt(sandbox, prompt, repo_name)
                
                if result["success"]:
                    # Create PR
                    branch_name = f"gemini-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
                    pr_title = f"Implement: {prompt[:50]}..."
                    pr_body = f"This PR implements the following request:\n\n{prompt}\n\n---\n*Generated by Gemini CLI*"
                    
                    pr_url = manager.create_pull_request(sandbox, repo_name, branch_name, pr_title, pr_body)
                    if pr_url:
                        console.print(f"\n[bold green]✅ Task completed! PR: {pr_url}[/bold green]")
    
    else:
        console.print(f"[red]Unknown command: {command}[/red]")


if __name__ == "__main__":
    main()