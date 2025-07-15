#!/usr/bin/env python3
"""Test what happens when we try to create a sandbox with different images"""

import os
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager(console=console)

# Test different image approaches
test_images = [
    ("node:20-slim", "Standard Node image"),
    ("claude-auth:latest", "Local Docker image"),
    ("ubuntu:22.04", "Ubuntu base image"),
]

for image, description in test_images:
    console.print(f"\n[yellow]Testing: {description} ({image})[/yellow]")
    
    # Override the image directly
    original_create = manager.create_sandbox
    
    def custom_create(name=None, sandbox_type="test", resources=None):
        # Temporarily change the image map
        manager.image_map = {"test": image}
        return original_create(name, sandbox_type, resources)
    
    manager.create_sandbox = custom_create
    
    try:
        sandbox = manager.create_sandbox(
            name=f"test-{image.replace(':', '-').replace('/', '-')}",
            sandbox_type="test",
            resources={"cpu": 1, "memory": 2}
        )
        
        if sandbox:
            console.print(f"[green]✓ Success with {image}[/green]")
            # Check if Claude is available
            result = manager.execute_command(
                sandbox,
                "which claude || echo 'Claude not found'",
                show_output=False
            )
            console.print(f"  Claude check: {result.strip()}")
            
            # Cleanup
            manager.delete_sandbox(sandbox.id)
        else:
            console.print(f"[red]✗ Failed with {image}[/red]")
            
    except Exception as e:
        console.print(f"[red]✗ Error with {image}: {e}[/red]")
    
    # Restore original method
    manager.create_sandbox = original_create