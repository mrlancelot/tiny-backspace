#!/usr/bin/env python3
"""Test using local authenticated Docker image with Daytona"""

import os
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager()

console.print("[yellow]Testing Local Authenticated Docker Image[/yellow]")
console.print("=" * 50)

try:
    # Try to create a sandbox with the local authenticated image
    console.print("\n[yellow]Creating sandbox with local authenticated image...[/yellow]")
    console.print("Using Dockerfile.authenticated which references: tiny-backspace-claude:authenticated")
    
    sandbox = manager.create_sandbox(
        name="test-local-auth",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if sandbox:
        console.print(f"[green]✓ Successfully created sandbox: {sandbox.id}[/green]")
        
        # Test Claude - should work without authentication
        console.print("\n[yellow]Testing Claude (should be pre-authenticated)...[/yellow]")
        result = manager.execute_command(
            sandbox,
            "claude --version",
            show_output=True
        )
        
        # Test Claude with a simple prompt
        console.print("\n[yellow]Testing Claude functionality...[/yellow]")
        test_result = manager.execute_command(
            sandbox,
            'claude --print "Hello from pre-authenticated Claude!"',
            show_output=True
        )
        
        # Check if we can see the authentication files
        console.print("\n[yellow]Checking authentication files...[/yellow]")
        manager.execute_command(
            sandbox,
            "ls -la ~/.claude* 2>/dev/null | head -5",
            show_output=True
        )
        
        # Cleanup
        console.print("\n[yellow]Cleaning up...[/yellow]")
        manager.delete_sandbox(sandbox.id)
        console.print("[green]✓ Test completed successfully![/green]")
        
    else:
        console.print("[red]✗ Failed to create sandbox[/red]")
        
except Exception as e:
    console.print(f"[red]Error: {e}[/red]")
    import traceback
    traceback.print_exc()