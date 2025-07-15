#!/usr/bin/env python3
"""Test simple clone in sandbox"""

import os
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager()

try:
    # Create sandbox
    console.print("[yellow]Creating sandbox...[/yellow]")
    sandbox = manager.create_sandbox(
        name="test-clone",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Test basic commands
    console.print("\n[yellow]Testing basic commands...[/yellow]")
    
    # Check working directory
    result = manager.execute_command(sandbox, "pwd", show_output=True)
    console.print(f"Working directory: {result}")
    
    # List root directory
    console.print("\nContents of /:")
    manager.execute_command(sandbox, "ls -la /", show_output=True)
    
    # List home directory
    console.print("\nContents of ~:")
    manager.execute_command(sandbox, "ls -la ~", show_output=True)
    
    # Try to clone
    console.print("\n[yellow]Testing clone...[/yellow]")
    repo_url = "https://github.com/mrlancelot/tb-test"
    
    # With authentication
    github_token = os.getenv("GITHUB_TOKEN")
    github_username = os.getenv("GITHUB_USERNAME")
    
    if github_token and github_username:
        auth_url = f"https://{github_username}:{github_token}@github.com/mrlancelot/tb-test.git"
        console.print("Cloning with authentication...")
        result = manager.execute_command(
            sandbox,
            f"cd ~ && git clone {auth_url} tb-test",
            show_output=True
        )
    else:
        console.print("Cloning without authentication...")
        result = manager.execute_command(
            sandbox,
            f"cd ~ && git clone {repo_url}",
            show_output=True
        )
    
    # Check if clone succeeded
    console.print("\nChecking clone result:")
    manager.execute_command(sandbox, "ls -la ~/tb-test 2>&1 || echo 'Not found'", show_output=True)
    
finally:
    # Cleanup
    if 'sandbox' in locals() and sandbox:
        console.print("\n[yellow]Cleaning up...[/yellow]")
        try:
            manager.delete_sandbox(sandbox.id)
            console.print("[green]✓ Sandbox deleted[/green]")
        except:
            console.print("[red]Failed to delete sandbox[/red]")