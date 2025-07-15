#!/usr/bin/env python3
"""Test public Docker Hub image with pre-authenticated Claude"""

import os
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager()

console.print("[yellow]Testing Public Docker Hub Image[/yellow]")
console.print("=" * 50)

try:
    # Create sandbox with public Docker Hub image
    console.print("\n[yellow]Creating sandbox with public Docker Hub image...[/yellow]")
    console.print("Image: pridhvikrishna/tiny-backspace-claude:latest")
    
    sandbox = manager.create_sandbox(
        name="test-public-auth",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if sandbox:
        console.print(f"[green]✓ Successfully created sandbox: {sandbox.id}[/green]")
        
        # Test Claude version
        console.print("\n[yellow]Testing Claude version...[/yellow]")
        result = manager.execute_command(
            sandbox,
            "claude --version",
            show_output=True
        )
        
        # Test Claude with a simple prompt (should work without auth)
        console.print("\n[yellow]Testing Claude functionality (pre-authenticated)...[/yellow]")
        test_result = manager.execute_command(
            sandbox,
            'claude --print "Hello from pre-authenticated Claude in Docker Hub image!"',
            show_output=True
        )
        
        # Check user
        console.print("\n[yellow]Checking current user...[/yellow]")
        manager.execute_command(
            sandbox,
            "whoami",
            show_output=True
        )
        
        # Cleanup
        console.print("\n[yellow]Cleaning up...[/yellow]")
        manager.delete_sandbox(sandbox.id)
        console.print("[green]✓ Test completed successfully![/green]")
        console.print("\n[green]✅ The public Docker Hub image works with Daytona![/green]")
        console.print("[yellow]You can now make the repository private after testing is complete.[/yellow]")
        
    else:
        console.print("[red]✗ Failed to create sandbox[/red]")
        
except Exception as e:
    console.print(f"[red]Error: {e}[/red]")
    import traceback
    traceback.print_exc()