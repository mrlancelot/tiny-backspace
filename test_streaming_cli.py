#!/usr/bin/env python3
"""Test script for streaming functionality without permission prompts"""

import asyncio
import sys
from daytona_manager_refactored import DaytonaManagerRefactored
from rich.console import Console

async def test_streaming():
    console = Console()
    manager = DaytonaManagerRefactored(console)
    
    # Override permission checks for testing
    manager.permission_manager.saved_permissions = {
        "EXECUTE_COMMAND": {"sandbox": True}
    }
    
    if len(sys.argv) < 3:
        console.print("[red]Usage: python test_streaming_cli.py <sandbox-id> '<prompt>'")
        return
    
    sandbox_id = sys.argv[1]
    prompt = sys.argv[2]
    
    # Connect to sandbox
    sandbox = manager.connect_to_sandbox(sandbox_id)
    if not sandbox:
        console.print(f"[red]Failed to connect to sandbox {sandbox_id}")
        return
    
    console.print(f"[green]Connected to sandbox: {sandbox_id}")
    
    # Execute with streaming
    await manager.execute_with_streaming(sandbox, prompt, use_claude=True)

if __name__ == "__main__":
    asyncio.run(test_streaming())