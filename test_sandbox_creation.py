#!/usr/bin/env python3
"""Simple test to check sandbox creation"""

import os
from dotenv import load_dotenv
from daytona_manager_cleaned import DaytonaManager
from rich.console import Console

load_dotenv()

console = Console()
manager = DaytonaManager()

console.print("[yellow]Testing Sandbox Creation[/yellow]")
console.print("=" * 50)

# Test different images
test_configs = [
    ("node:20-slim", "Standard Node.js image"),
    ("pridhvikrishna/tiny-backspace-claude:latest", "Pre-authenticated Claude image"),
]

for image, description in test_configs:
    console.print(f"\n[yellow]Testing: {description}[/yellow]")
    console.print(f"Image: {image}")
    
    # Temporarily override the image
    original_create = manager.create_sandbox
    
    def custom_create(name, sandbox_type, resources=None):
        # Override image selection
        manager._test_image = image
        return original_create(name, sandbox_type, resources)
    
    manager.create_sandbox = custom_create
    
    try:
        sandbox = manager.create_sandbox(
            name=f"test-{image.replace(':', '-').replace('/', '-')[:20]}",
            sandbox_type="claude",
            resources={"cpu": 1, "memory": 2}
        )
        
        if sandbox:
            console.print(f"[green]✓ Success: Created sandbox {sandbox.id}[/green]")
            
            # Quick test
            result = manager.execute_command(
                sandbox,
                "echo 'Sandbox is working'",
                show_output=False
            )
            console.print(f"[green]✓ Sandbox responsive[/green]")
            
            # Cleanup
            manager.delete_sandbox(sandbox.id)
        else:
            console.print(f"[red]✗ Failed to create sandbox[/red]")
            
    except Exception as e:
        console.print(f"[red]✗ Error: {e}[/red]")
    
    # Restore original method
    manager.create_sandbox = original_create

console.print("\n[yellow]Test complete![/yellow]")