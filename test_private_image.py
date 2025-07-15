#!/usr/bin/env python3
"""Test if Daytona can pull the private Docker image"""

import os
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager()

console.print("[yellow]Testing Private Docker Image Access[/yellow]")
console.print("=" * 50)

try:
    # Try to create a sandbox with the private image
    console.print("\n[yellow]Creating sandbox with private image...[/yellow]")
    console.print("Image: pridhvikrishna/tiny-backspace-claude:latest")
    
    sandbox = manager.create_sandbox(
        name="test-private-image",
        sandbox_type="claude",
        resources={"cpu": 1, "memory": 2}
    )
    
    if sandbox:
        console.print(f"[green]✓ Successfully created sandbox: {sandbox.id}[/green]")
        
        # Test Claude
        console.print("\n[yellow]Testing Claude in sandbox...[/yellow]")
        result = manager.execute_command(
            sandbox,
            "claude --version",
            show_output=True
        )
        
        # Test Claude with a simple prompt
        console.print("\n[yellow]Testing Claude functionality...[/yellow]")
        test_result = manager.execute_command(
            sandbox,
            'claude --print "Say hello"',
            show_output=True
        )
        
        # Cleanup
        console.print("\n[yellow]Cleaning up...[/yellow]")
        manager.delete_sandbox(sandbox.id)
        console.print("[green]✓ Test completed successfully![/green]")
        
    else:
        console.print("[red]✗ Failed to create sandbox[/red]")
        console.print("\n[yellow]Possible issues:[/yellow]")
        console.print("1. Daytona cannot access private Docker Hub repositories")
        console.print("2. The image name is incorrect")
        console.print("3. Network connectivity issues")
        console.print("\n[yellow]Solution:[/yellow]")
        console.print("Make the Docker Hub repository public temporarily:")
        console.print("  1. Go to https://hub.docker.com/r/pridhvikrishna/tiny-backspace-claude")
        console.print("  2. Settings → Make Public")
        
except Exception as e:
    console.print(f"[red]Error: {e}[/red]")
    console.print("\n[yellow]Troubleshooting:[/yellow]")
    console.print("1. Check if the image exists locally:")
    console.print("   docker images | grep tiny-backspace-claude")
    console.print("2. Try pulling manually:")
    console.print("   docker pull pridhvikrishna/tiny-backspace-claude:latest")