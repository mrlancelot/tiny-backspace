#!/usr/bin/env python3
"""Test Claude without --print flag"""

import os
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
        name="test-no-print",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Create a test repository
    console.print("\n[yellow]Setting up test repository...[/yellow]")
    manager.execute_command(sandbox, "mkdir -p /root/test-repo && cd /root/test-repo && git init", show_output=True)
    manager.execute_command(sandbox, "cd /root/test-repo && echo '# Initial' > README.md", show_output=True)
    manager.execute_command(sandbox, "cd /root/test-repo && git add README.md && git commit -m 'Initial commit'", show_output=True)
    
    # Test Claude WITHOUT --print
    console.print("\n[yellow]Testing Claude WITHOUT --print flag...[/yellow]")
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    
    prompt = "Update the README.md file to have the title 'Test Project' and add a description 'This is a test'."
    
    command = f'''cd /root/test-repo && CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}" claude "{prompt}"'''
    
    console.print(f"\n[blue]Command:[/blue] {command[:100]}...")
    result = manager.execute_command(sandbox, command, show_output=True)
    
    # Check if file was modified
    console.print("\n[yellow]Checking if README.md was modified...[/yellow]")
    manager.execute_command(sandbox, "cd /root/test-repo && cat README.md", show_output=True)
    
    # Check git status
    console.print("\n[yellow]Checking git status...[/yellow]")
    manager.execute_command(sandbox, "cd /root/test-repo && git status", show_output=True)
    
finally:
    # Cleanup
    if 'sandbox' in locals() and sandbox:
        console.print("\n[yellow]Cleaning up...[/yellow]")
        try:
            manager.delete_sandbox(sandbox.id)
            console.print("[green]✓ Sandbox deleted[/green]")
        except:
            console.print("[red]Failed to delete sandbox[/red]")