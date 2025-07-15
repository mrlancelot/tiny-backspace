#!/usr/bin/env python3
"""Test Claude full interaction without --print"""

import os
import time
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager()

try:
    # Create sandbox
    console.print("[yellow]Creating test sandbox...[/yellow]")
    sandbox = manager.create_sandbox(
        name="test-claude-full",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Setup git config
    console.print("\n[yellow]Setting up git configuration...[/yellow]")
    manager.execute_command(sandbox, 'git config --global user.email "test@example.com"', show_output=False)
    manager.execute_command(sandbox, 'git config --global user.name "Test User"', show_output=False)
    
    # Create a test repository
    console.print("\n[yellow]Setting up test repository...[/yellow]")
    manager.execute_command(sandbox, "mkdir -p /root/test-repo && cd /root/test-repo && git init", show_output=True)
    manager.execute_command(sandbox, "cd /root/test-repo && echo '# Initial README' > README.md", show_output=True)
    manager.execute_command(sandbox, "cd /root/test-repo && git add README.md && git commit -m 'Initial commit'", show_output=True)
    
    # Show initial state
    console.print("\n[yellow]Initial README.md content:[/yellow]")
    manager.execute_command(sandbox, "cd /root/test-repo && cat README.md", show_output=True)
    
    # Test Claude WITHOUT --print - give it time to work
    console.print("\n[yellow]Running Claude to update README.md...[/yellow]")
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    
    prompt = "Update the README.md file to have the title 'Test Project' and add a description 'This is a test project created by Tiny Backspace.'"
    
    # Use timeout to give Claude time to work
    command = f'''cd /root/test-repo && timeout 30 bash -c 'CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}" claude "{prompt}"' '''
    
    console.print(f"\n[blue]Executing Claude...[/blue]")
    result = manager.execute_command(sandbox, command, show_output=True)
    
    # Give Claude a moment to complete
    time.sleep(2)
    
    # Check if file was modified
    console.print("\n[yellow]Updated README.md content:[/yellow]")
    manager.execute_command(sandbox, "cd /root/test-repo && cat README.md", show_output=True)
    
    # Check git status
    console.print("\n[yellow]Git status:[/yellow]")
    manager.execute_command(sandbox, "cd /root/test-repo && git status --porcelain", show_output=True)
    
    # Check git diff
    console.print("\n[yellow]Git diff:[/yellow]")
    manager.execute_command(sandbox, "cd /root/test-repo && git diff", show_output=True)
    
finally:
    # Cleanup
    if 'sandbox' in locals() and sandbox:
        console.print("\n[yellow]Cleaning up...[/yellow]")
        try:
            manager.delete_sandbox(sandbox.id)
            console.print("[green]✓ Sandbox deleted[/green]")
        except:
            console.print("[red]Failed to delete sandbox[/red]")