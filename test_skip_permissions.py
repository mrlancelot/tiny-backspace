#!/usr/bin/env python3
"""Test Claude with --dangerously-skip-permissions flag"""

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
        name="test-skip-perms",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Setup git
    manager.execute_command(sandbox, 'git config --global user.email "test@example.com"', show_output=False)
    manager.execute_command(sandbox, 'git config --global user.name "Test User"', show_output=False)
    
    # Create test repo
    console.print("\n[yellow]Creating test repository...[/yellow]")
    commands = [
        "mkdir -p /root/test-repo",
        "cd /root/test-repo && git init",
        "cd /root/test-repo && echo '# Initial Title' > README.md",
        "cd /root/test-repo && git add README.md",
        "cd /root/test-repo && git commit -m 'Initial commit'"
    ]
    
    for cmd in commands:
        manager.execute_command(sandbox, cmd, show_output=False)
    
    # Show initial content
    console.print("\n[yellow]Before Claude:[/yellow]")
    manager.execute_command(sandbox, "cat /root/test-repo/README.md", show_output=True)
    
    # Test Claude with --dangerously-skip-permissions
    console.print("\n[yellow]Running Claude with --dangerously-skip-permissions...[/yellow]")
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    
    # Simple prompt
    prompt = "Update README.md to have title 'Test Project' and description 'This is a test.'"
    
    # Run with OAuth token and skip permissions flag
    command = f'''cd /root/test-repo && CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}" claude --dangerously-skip-permissions "{prompt}"'''
    
    console.print(f"\n[blue]Command:[/blue] claude --dangerously-skip-permissions ...")
    result = manager.execute_command(sandbox, command, show_output=True)
    
    # Check results
    console.print("\n[yellow]After Claude:[/yellow]")
    manager.execute_command(sandbox, "cat /root/test-repo/README.md", show_output=True)
    
    console.print("\n[yellow]Git status:[/yellow]")
    manager.execute_command(sandbox, "cd /root/test-repo && git status --porcelain", show_output=True)
    
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