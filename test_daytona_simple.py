#!/usr/bin/env python3
"""Simple test to check if Daytona is working"""

import os
from dotenv import load_dotenv
load_dotenv()

from daytona_manager_cleaned import DaytonaManager

def test_daytona():
    """Test basic Daytona functionality"""
    manager = DaytonaManager()
    
    # List sandboxes
    print("Listing existing sandboxes...")
    sandboxes = manager.list_sandboxes()
    
    # Try to create a simple sandbox
    print("\nCreating test sandbox...")
    sandbox = manager.create_sandbox(name="test-simple", sandbox_type="claude")
    
    if sandbox:
        print(f"✅ Sandbox created: {sandbox.id}")
        
        # Execute a simple command
        print("\nExecuting command...")
        manager.execute_command(sandbox, "echo 'Hello from sandbox'", show_output=True)
        
        # Delete sandbox
        print("\nDeleting sandbox...")
        manager.delete_sandbox(sandbox.id)
        print("✅ Cleanup complete")
    else:
        print("❌ Failed to create sandbox")

if __name__ == "__main__":
    test_daytona()