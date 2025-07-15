#!/usr/bin/env python3
"""Simple test to debug the issue"""

import asyncio
import sys
sys.path.append('/Users/pridhvi/Documents/Github/tiny-backspace')

from daytona_manager_refactored import DaytonaManagerRefactored

async def test_directory_issue():
    """Test what happens when we clone and navigate"""
    manager = DaytonaManagerRefactored()
    
    try:
        # Create sandbox
        print("Creating sandbox...")
        sandbox = await asyncio.to_thread(
            manager.create_sandbox,
            name="debug-test",
            sandbox_type="claude"
        )
        print(f"Sandbox created: {sandbox.id}")
        
        # Check current directory
        print("\nChecking current directory...")
        pwd_result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "pwd",
            show_output=True
        )
        
        # List root directory
        print("\nListing root directory...")
        ls_root = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "ls -la /",
            show_output=True
        )
        
        # Create workspace directory
        print("\nCreating /workspace directory...")
        mkdir_result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "mkdir -p /workspace",
            show_output=True
        )
        
        # Clone repository
        print("\nCloning repository...")
        clone_result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "cd /workspace && git clone https://github.com/mrlancelot/tb-test",
            show_output=True
        )
        
        # List workspace
        print("\nListing /workspace/...")
        ls_result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "ls -la /workspace/",
            show_output=True
        )
        
        # Check if we can cd into the repo
        print("\nTrying to cd into tb-test...")
        cd_result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "cd /workspace/tb-test && pwd",
            show_output=True
        )
        
        # Get remote URL
        print("\nGetting remote URL...")
        remote_result = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "cd /workspace/tb-test && git remote get-url origin",
            show_output=True
        )
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        await asyncio.to_thread(manager.delete_sandbox, sandbox.id)

if __name__ == "__main__":
    asyncio.run(test_directory_issue())