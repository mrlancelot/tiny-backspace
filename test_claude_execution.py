#!/usr/bin/env python3
"""Test Claude execution in sandbox"""

import os
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager()

try:
    # Create sandbox
    console.print("[yellow]Creating Claude sandbox...[/yellow]")
    sandbox = manager.create_sandbox(
        name="claude-exec-test",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Clone a test repo
    console.print("\n[yellow]Cloning test repository...[/yellow]")
    
    github_token = os.getenv("GITHUB_TOKEN")
    github_username = os.getenv("GITHUB_USERNAME")
    
    if github_token and github_username:
        auth_url = f"https://{github_username}:{github_token}@github.com/mrlancelot/tb-test.git"
        result = manager.execute_command(
            sandbox,
            f"cd /root && git clone {auth_url} tb-test",
            show_output=True
        )
    
    # Navigate to repo
    console.print("\n[yellow]Testing Claude in repository...[/yellow]")
    
    # Simple Claude test
    console.print("\nTest 1: Claude help")
    result = manager.execute_command(
        sandbox,
        "cd /root/tb-test && claude --help 2>&1 || echo 'Claude help failed'",
        show_output=True
    )
    
    # Test with a simple prompt
    console.print("\nTest 2: Claude with simple prompt")
    simple_prompt = "List all files in the current directory"
    result = manager.execute_command(
        sandbox,
        f'cd /root/tb-test && claude --print "{simple_prompt}" 2>&1',
        show_output=True
    )
    
    # Test creating a file
    console.print("\nTest 3: Claude creating README")
    create_prompt = "Create a README.md file with the title 'TB Test Project' and a description that says 'This is a test project for Tiny Backspace autonomous coding agent.'"
    result = manager.execute_command(
        sandbox,
        f'cd /root/tb-test && claude --print "{create_prompt}" 2>&1',
        show_output=True
    )
    
    # Check if file was created
    console.print("\n[yellow]Checking if README.md was created...[/yellow]")
    manager.execute_command(
        sandbox,
        "ls -la /root/tb-test/README.md 2>&1 || echo 'README.md not found'",
        show_output=True
    )
    
    # Show git status
    console.print("\n[yellow]Git status:[/yellow]")
    manager.execute_command(
        sandbox,
        "cd /root/tb-test && git status",
        show_output=True
    )
    
finally:
    # Cleanup
    if 'sandbox' in locals() and sandbox:
        console.print("\n[yellow]Cleaning up...[/yellow]")
        try:
            manager.delete_sandbox(sandbox.id)
            console.print("[green]✓ Sandbox deleted[/green]")
        except:
            console.print("[red]Failed to delete sandbox[/red]")