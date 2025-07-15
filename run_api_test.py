#!/usr/bin/env python3
"""
Run the API and test PR creation
"""

import subprocess
import time
import requests
import json
import os

def start_api():
    """Start the API server"""
    print("Starting API server...")
    
    # Set environment variables
    env = os.environ.copy()
    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env['PYTHONPATH'] = script_dir
    
    # Start API server
    api_process = subprocess.Popen(
        ['python3', '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'],
        cwd=os.path.join(script_dir, 'api'),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start
    time.sleep(5)
    
    # Check if server is running
    try:
        response = requests.get('http://localhost:8000/health')
        if response.status_code == 200:
            print("✓ API server is running")
            print(f"Health check: {response.json()}")
            return api_process
        else:
            print(f"✗ API returned status {response.status_code}")
            api_process.terminate()
            return None
    except Exception as e:
        print(f"✗ Failed to connect to API: {e}")
        # Print stderr output
        stderr = api_process.stderr.read().decode()
        if stderr:
            print(f"API Error output:\n{stderr}")
        api_process.terminate()
        return None

def test_pr_creation():
    """Test PR creation"""
    print("\nTesting PR creation...")
    
    url = "http://localhost:8000/code"
    data = {
        "repoUrl": "https://github.com/mrlancelot/tb-test",
        "prompt": "Add a simple Python hello world script that prints 'Hello from Tiny Backspace!' and shows the current date. Save it as hello_world.py"
    }
    
    # Make streaming request
    response = requests.post(
        url,
        json=data,
        stream=True,
        headers={'Accept': 'text/event-stream'}
    )
    
    print(f"Response status: {response.status_code}")
    
    if response.status_code == 200:
        print("\nStreaming response:")
        print("-" * 60)
        
        for line in response.iter_lines():
            if line:
                line_str = line.decode('utf-8')
                print(line_str)
                
                # Check for PR creation
                if 'pr_created' in line_str:
                    try:
                        if line_str.startswith('data: '):
                            event_data = json.loads(line_str[6:])
                            if event_data.get('type') == 'pr_created':
                                print("\n" + "=" * 60)
                                print("✓ PR CREATED SUCCESSFULLY!")
                                print(f"URL: {event_data.get('pr_url', 'Unknown')}")
                                print("=" * 60)
                    except:
                        pass
    else:
        print(f"✗ API returned error: {response.text}")

if __name__ == "__main__":
    # Load environment variables
    from dotenv import load_dotenv
    load_dotenv()
    
    # Start API
    api_process = start_api()
    
    if api_process:
        try:
            # Test PR creation
            test_pr_creation()
        finally:
            # Stop API
            print("\nStopping API server...")
            api_process.terminate()
            api_process.wait()
    else:
        print("Failed to start API server")
        print("\nChecking API logs...")
        
        # Try to run API directly to see error
        result = subprocess.run(
            ['python3', '-m', 'uvicorn', 'main:app', '--host', '0.0.0.0', '--port', '8000'],
            cwd='/Users/pridhvi/Documents/Github/tiny-backspace/api',
            env={'PYTHONPATH': '/Users/pridhvi/Documents/Github/tiny-backspace'},
            capture_output=True,
            text=True
        )
        
        if result.stderr:
            print(f"Error output:\n{result.stderr}")