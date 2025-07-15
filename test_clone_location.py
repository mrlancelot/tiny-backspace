#!/usr/bin/env python3
"""Test where repositories actually get cloned"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from daytona_manager_refactored import DaytonaManagerRefactored

async def test_clone_location():
    """Test where git clone actually puts the repository"""
    manager = DaytonaManagerRefactored()
    
    try:
        # Create sandbox
        print("Creating sandbox...")
        sandbox = await asyncio.to_thread(
            manager.create_sandbox,
            name="clone-test",
            sandbox_type="claude"
        )
        print(f"✅ Sandbox created: {sandbox.id}\n")
        
        # Get working directory
        print("1. Getting working directory:")
        pwd = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "pwd",
            show_output=True
        )
        work_dir = pwd.strip() if pwd else "/root"
        print(f"Working directory: {work_dir}\n")
        
        # List initial contents
        print("2. Initial directory contents:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"ls -la {work_dir}",
            show_output=True
        )
        
        # Clone with explicit path
        print(f"\n3. Cloning to {work_dir}:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"cd {work_dir} && git clone https://github.com/mrlancelot/tb-test",
            show_output=True
        )
        
        # Check what happened
        print(f"\n4. After clone, contents of {work_dir}:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"ls -la {work_dir}",
            show_output=True
        )
        
        # Check if we can cd into it
        print(f"\n5. Trying to cd into {work_dir}/tb-test:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"cd {work_dir}/tb-test && pwd && ls -la",
            show_output=True
        )
        
        # Try git commands
        print(f"\n6. Git status in cloned repo:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"cd {work_dir}/tb-test && git status",
            show_output=True
        )
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        await asyncio.to_thread(manager.delete_sandbox, sandbox.id)
        print("✅ Done!")

if __name__ == "__main__":
    asyncio.run(test_clone_location())