#!/usr/bin/env python3
"""
Test if Claude Code is available in Daytona sandboxes
"""

import os
from dotenv import load_dotenv
from daytona_manager_refactored import DaytonaManagerRefactored
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManagerRefactored(console=console)

# Override permissions
manager.permission_manager.saved_permissions = {
    "CREATE_SANDBOX": {"all": True},
    "EXECUTE_COMMAND": {"all": True},
    "DELETE_SANDBOX": {"all": True}
}

console.print("[bold]Testing Claude Code in Daytona Sandbox[/bold]")

try:
    # Create sandbox using Docker image
    console.print("\n[yellow]Creating test sandbox with Docker image...[/yellow]")
    
    # First, let's check if we need to use docker type
    sandbox = manager.create_sandbox(
        name="claude-test",
        sandbox_type="docker",  # Changed from 'claude' to 'docker'
        resources={"cpu": 1, "memory": 2}
    )
    
    if not sandbox:
        console.print("[red]Failed to create sandbox[/red]")
        exit(1)
    
    console.print(f"[green]✓ Sandbox created: {sandbox.id}[/green]")
    
    # Test Claude availability
    console.print("\n[yellow]Testing Claude Code availability...[/yellow]")
    
    # Check if claude command exists
    result = manager.execute_command(
        sandbox,
        "which claude",
        show_output=True
    )
    
    if result and "claude" in result:
        console.print(f"[green]✓ Claude found at: {result.strip()}[/green]")
    else:
        console.print("[red]✗ Claude command not found[/red]")
    
    # Check Claude version
    console.print("\n[yellow]Checking Claude version...[/yellow]")
    result = manager.execute_command(
        sandbox,
        "claude --version 2>&1 || echo 'Claude not available'",
        show_output=True
    )
    
    # Test Claude with a simple prompt
    console.print("\n[yellow]Testing Claude with a simple prompt...[/yellow]")
    result = manager.execute_command(
        sandbox,
        'claude --print "Say hello and tell me the current date"',
        show_output=True
    )
    
    if result:
        console.print(f"[green]Claude response:[/green]\n{result}")
    else:
        console.print("[red]No response from Claude[/red]")
    
    # Check environment
    console.print("\n[yellow]Checking environment...[/yellow]")
    result = manager.execute_command(
        sandbox,
        "env | grep -E 'ANTHROPIC|CLAUDE' || echo 'No Claude env vars found'",
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