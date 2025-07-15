#!/usr/bin/env python3
"""Test Claude as non-root user"""

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
        name="test-nonroot",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Create a non-root user
    console.print("\n[yellow]Creating non-root user...[/yellow]")
    manager.execute_command(sandbox, "useradd -m -s /bin/bash claude-user || true", show_output=True)
    manager.execute_command(sandbox, "echo 'claude-user ALL=(ALL) NOPASSWD:ALL' >> /etc/sudoers", show_output=False)
    
    # Setup git for both users
    manager.execute_command(sandbox, 'git config --global user.email "test@example.com"', show_output=False)
    manager.execute_command(sandbox, 'git config --global user.name "Test User"', show_output=False)
    manager.execute_command(sandbox, 'sudo -u claude-user git config --global user.email "test@example.com"', show_output=False)
    manager.execute_command(sandbox, 'sudo -u claude-user git config --global user.name "Test User"', show_output=False)
    
    # Create test repo as claude-user
    console.print("\n[yellow]Creating test repository as claude-user...[/yellow]")
    commands = [
        "sudo -u claude-user mkdir -p /home/claude-user/test-repo",
        "cd /home/claude-user/test-repo && sudo -u claude-user git init",
        "cd /home/claude-user/test-repo && echo '# Initial Title' | sudo -u claude-user tee README.md",
        "cd /home/claude-user/test-repo && sudo -u claude-user git add README.md",
        "cd /home/claude-user/test-repo && sudo -u claude-user git commit -m 'Initial commit'"
    ]
    
    for cmd in commands:
        manager.execute_command(sandbox, cmd, show_output=False)
    
    # Show initial content
    console.print("\n[yellow]Before Claude:[/yellow]")
    manager.execute_command(sandbox, "cat /home/claude-user/test-repo/README.md", show_output=True)
    
    # Test Claude as non-root user
    console.print("\n[yellow]Running Claude as non-root user...[/yellow]")
    oauth_token = os.getenv('CLAUDE_CODE_OAUTH_TOKEN')
    
    # Simple prompt
    prompt = "Update README.md to have title 'Test Project' and description 'This is a test.'"
    
    # Run as claude-user with OAuth token
    command = f'''cd /home/claude-user/test-repo && sudo -u claude-user CLAUDE_CODE_OAUTH_TOKEN="{oauth_token}" claude --dangerously-skip-permissions "{prompt}"'''
    
    console.print(f"\n[blue]Running as claude-user with --dangerously-skip-permissions...[/blue]")
    result = manager.execute_command(sandbox, command, show_output=True)
    
    # Check results
    console.print("\n[yellow]After Claude:[/yellow]")
    manager.execute_command(sandbox, "cat /home/claude-user/test-repo/README.md", show_output=True)
    
    console.print("\n[yellow]Git status:[/yellow]")
    manager.execute_command(sandbox, "cd /home/claude-user/test-repo && git status --porcelain", show_output=True)
    
finally:
    # Cleanup
    if 'sandbox' in locals() and sandbox:
        console.print("\n[yellow]Cleaning up...[/yellow]")
        try:
            manager.delete_sandbox(sandbox.id)
            console.print("[green]✓ Sandbox deleted[/green]")
        except:
            console.print("[red]Failed to delete sandbox[/red]")