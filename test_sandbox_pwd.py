#!/usr/bin/env python3
"""Test to determine Daytona sandbox directory structure"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from daytona_manager_refactored import DaytonaManagerRefactored

async def test_sandbox_structure():
    """Test sandbox directory structure"""
    manager = DaytonaManagerRefactored()
    
    try:
        # Create sandbox
        print("Creating sandbox...")
        sandbox = await asyncio.to_thread(
            manager.create_sandbox,
            name="pwd-test",
            sandbox_type="claude"
        )
        print(f"✅ Sandbox created: {sandbox.id}\n")
        
        # Check working directory
        print("1. Current working directory (pwd):")
        pwd = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "pwd",
            show_output=True
        )
        
        print("\n2. User info (whoami):")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "whoami",
            show_output=True
        )
        
        print("\n3. Home directory ($HOME):")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "echo $HOME",
            show_output=True
        )
        
        print("\n4. List current directory:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "ls -la",
            show_output=True
        )
        
        print("\n5. List home directory:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "ls -la ~",
            show_output=True
        )
        
        print("\n6. Test git clone in current directory:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "git clone https://github.com/mrlancelot/tb-test && ls -la",
            show_output=True
        )
        
        print("\n7. Can we cd into the cloned repo:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "cd tb-test && pwd",
            show_output=True
        )
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        await asyncio.to_thread(manager.delete_sandbox, sandbox.id)
        print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(test_sandbox_structure())