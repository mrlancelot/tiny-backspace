#!/usr/bin/env python3
"""Final diagnosis of the issue"""

import asyncio
import os
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from daytona_manager_refactored import DaytonaManagerRefactored

async def diagnose_issue():
    """Diagnose the exact issue"""
    manager = DaytonaManagerRefactored()
    
    try:
        # Create sandbox
        print("1. Creating sandbox...")
        sandbox = await asyncio.to_thread(
            manager.create_sandbox,
            name="diagnose",
            sandbox_type="claude"
        )
        print(f"✅ Sandbox created: {sandbox.id}\n")
        
        # Get working directory
        print("2. Checking working directory:")
        pwd = await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            "pwd",
            show_output=True
        )
        work_dir = pwd.strip() if pwd else "/root"
        
        # Clone
        print(f"\n3. Cloning to {work_dir}:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"cd {work_dir} && git clone https://github.com/mrlancelot/tb-test",
            show_output=True
        )
        
        # Check if it exists
        print(f"\n4. Checking if {work_dir}/tb-test exists:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"test -d {work_dir}/tb-test && echo 'EXISTS' || echo 'NOT EXISTS'",
            show_output=True
        )
        
        # Try git -C
        print(f"\n5. Testing git -C command:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"git -C {work_dir}/tb-test status",
            show_output=True
        )
        
        # Create branch
        print(f"\n6. Creating branch:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"git -C {work_dir}/tb-test checkout -b test-branch",
            show_output=True
        )
        
        # Create a file
        print(f"\n7. Creating README.md:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"echo '# Test' > {work_dir}/tb-test/README.md",
            show_output=True
        )
        
        # Add and commit
        print(f"\n8. Adding and committing:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"git -C {work_dir}/tb-test add -A && git -C {work_dir}/tb-test commit -m 'Test commit'",
            show_output=True
        )
        
        # Check remote
        print(f"\n9. Checking remote:")
        await asyncio.to_thread(
            manager.execute_command,
            sandbox,
            f"git -C {work_dir}/tb-test remote get-url origin",
            show_output=True
        )
        
        print("\n✅ All operations successful!")
        
    finally:
        # Cleanup
        print("\nCleaning up...")
        await asyncio.to_thread(manager.delete_sandbox, sandbox.id)

if __name__ == "__main__":
    asyncio.run(diagnose_issue())