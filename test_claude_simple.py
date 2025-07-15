#!/usr/bin/env python3
"""Simple test of Claude without --print"""

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
        name="test-simple",
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
        "cd /root/test-repo && echo '# Old Title' > README.md",
        "cd /root/test-repo && git add README.md",
        "cd /root/test-repo && git commit -m 'Initial commit'"
    ]
    
    for cmd in commands:
        manager.execute_command(sandbox, cmd, show_output=False)
    
    # Show initial content
    console.print("\n[yellow]Before Claude:[/yellow]")
    manager.execute_command(sandbox, "cat /root/test-repo/README.md", show_output=True)
    
    # Test Claude with simple prompt
    console.print("\n[yellow]Running Claude...[/yellow]")
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    
    # Write prompt to file to avoid escaping issues
    prompt_content = """Please update the README.md file in this repository. 
Change the title to '# Test Project' and add a description that says 'This is a test project.'"""
    
    manager.execute_command(
        sandbox,
        f"echo '{prompt_content}' > /tmp/prompt.txt",
        show_output=False
    )
    
    # Run Claude with prompt from file
    result = manager.execute_command(
        sandbox,
        f'cd /root/test-repo && CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}" claude "$(cat /tmp/prompt.txt)"',
        show_output=True
    )
    
    # Check results
    console.print("\n[yellow]After Claude:[/yellow]")
    manager.execute_command(sandbox, "cat /root/test-repo/README.md", show_output=True)
    
    console.print("\n[yellow]Git status:[/yellow]")
    manager.execute_command(sandbox, "cd /root/test-repo && git status --porcelain", show_output=True)
    
finally:
    # Cleanup
    if 'sandbox' in locals() and sandbox:
        console.print("\n[yellow]Cleaning up...[/yellow]")
        try:
            manager.delete_sandbox(sandbox.id)
            console.print("[green]✓ Sandbox deleted[/green]")
        except:
            console.print("[red]Failed to delete sandbox[/red]")