#!/usr/bin/env python3
"""Test where files actually get created in Daytona sandbox"""

import asyncio
import sys
import os

# Add parent to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from daytona_manager_refactored import DaytonaManagerRefactored

async def test_sandbox_directories():
    """Test sandbox directory structure"""
    # Load env vars
    from dotenv import load_dotenv
    load_dotenv()
    
    manager = DaytonaManagerRefactored()
    
    try:
        # Create sandbox
        print("Creating sandbox...")
        sandbox = await asyncio.to_thread(
            manager.create_sandbox,
            name="dir-test",
            sandbox_type="claude"
        )
        print(f"Sandbox created: {sandbox.id}")
        
        # Check working directory
        print("\n1. Current working directory:")
        result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "pwd",
            show_output=True
        )
        
        # List home directory
        print("\n2. Home directory contents:")
        result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "ls -la ~",
            show_output=True
        )
        
        # Check if we can create directories
        print("\n3. Creating test directories:")
        result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "mkdir -p ~/workspace && mkdir -p /tmp/workspace && ls -la ~ /tmp/",
            show_output=True
        )
        
        # Clone to home directory
        print("\n4. Cloning to home directory:")
        result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "cd ~ && git clone https://github.com/mrlancelot/tb-test && ls -la",
            show_output=True
        )
        
        # Check if we can navigate
        print("\n5. Navigating to cloned repo:")
        result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "cd ~/tb-test && pwd && git remote get-url origin",
            show_output=True
        )
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        await asyncio.to_thread(manager.delete_sandbox, sandbox.id)
        print("Done!")

if __name__ == "__main__":
    asyncio.run(test_sandbox_directories())