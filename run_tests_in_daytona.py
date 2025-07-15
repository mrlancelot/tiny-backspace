#!/usr/bin/env python3
"""Run tests inside Daytona sandbox"""

import os
import sys
from daytona_manager_cleaned import DaytonaManager

def main():
    if len(sys.argv) < 2:
        print("Usage: python run_tests_in_daytona.py <sandbox-id>")
        return
    
    sandbox_id = sys.argv[1]
    
    # Initialize manager
    manager = DaytonaManager()
    
    # Connect to sandbox
    sandbox = manager.connect_to_sandbox(sandbox_id)
    if not sandbox:
        print(f"Failed to connect to sandbox {sandbox_id}")
        return
    
    print(f"✅ Connected to sandbox: {sandbox_id}")
    
    # Install Python if not available
    print("\n📦 Setting up Python environment in sandbox...")
    manager.execute_command(sandbox, "apt-get update -qq", show_output=False)
    manager.execute_command(sandbox, "apt-get install -y python3 python3-pip python3-venv", show_output=False)
    
    # Create a working directory
    print("\n📁 Creating test directory...")
    manager.execute_command(sandbox, "mkdir -p /workspace/tests")
    
    # Copy test files to sandbox
    test_files = [
        "streaming_response.py",
        "test_daytona_manager.py", 
        "permission_manager.py",
        "daytona_manager_cleaned.py",
        "daytona_manager_refactored.py",
        "enhanced_cli.py",
        "requirements.txt"
    ]
    
    print("\n📤 Uploading test files...")
    for file in test_files:
        if os.path.exists(file):
            print(f"  - Uploading {file}")
            with open(file, 'r') as f:
                content = f.read()
            # Escape single quotes and create file
            escaped_content = content.replace("'", "'\"'\"'")
            manager.execute_command(
                sandbox, 
                f"cat > /workspace/tests/{file} << 'EOF'\n{content}\nEOF",
                show_output=False
            )
    
    # Create virtual environment
    print("\n🐍 Creating Python virtual environment...")
    manager.execute_command(sandbox, "cd /workspace/tests && python3 -m venv venv")
    
    # Install dependencies
    print("\n📦 Installing Python dependencies...")
    manager.execute_command(sandbox, "cd /workspace/tests && ./venv/bin/pip install -r requirements.txt")
    
    # Run tests
    print("\n🧪 Running streaming tests...")
    print("=" * 60)
    
    # Run unit tests
    print("\n1. Unit Tests for Streaming:")
    manager.execute_command(
        sandbox, 
        "cd /workspace/tests && ./venv/bin/python -m pytest test_daytona_manager.py::TestStreamingResponse -v"
    )
    
    # Run the streaming example
    print("\n2. Streaming Example:")
    manager.execute_command(
        sandbox,
        "cd /workspace/tests && ./venv/bin/python streaming_response.py"
    )
    
    print("\n✅ All tests completed in Daytona sandbox!")

if __name__ == "__main__":
    main()