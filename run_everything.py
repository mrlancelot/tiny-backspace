#!/usr/bin/env python3
"""Run everything - start API and run tests"""

import subprocess
import time
import os
import sys
import signal

def run_command(cmd, cwd=None):
    """Run command and return process"""
    print(f"🚀 Running: {cmd}")
    return subprocess.Popen(
        cmd, shell=True, cwd=cwd,
        stdout=subprocess.PIPE, 
        stderr=subprocess.STDOUT,
        universal_newlines=True,
        preexec_fn=os.setsid if sys.platform != 'win32' else None
    )

def kill_process_group(proc):
    """Kill process and all children"""
    if sys.platform != 'win32':
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except:
            pass
    else:
        proc.terminate()

def main():
    api_process = None
    
    try:
        # Load environment
        from dotenv import load_dotenv
        load_dotenv()
        
        print("🧪 Tiny Backspace - Complete Test Run")
        print("=" * 50)
        
        # Kill any existing API processes
        print("\n🔧 Cleaning up existing processes...")
        subprocess.run("pkill -f 'uvicorn.*api.main' || true", shell=True)
        time.sleep(2)
        
        # Start API in background
        print("\n📡 Starting API server...")
        api_process = run_command("cd api && python -m uvicorn main:app --reload", cwd=".")
        
        # Wait for API to start
        print("⏳ Waiting for API to start...")
        for i in range(30):
            try:
                import requests
                response = requests.get("http://localhost:8000/health")
                if response.status_code == 200:
                    print("✅ API is ready!")
                    break
            except:
                pass
            time.sleep(1)
            if i == 29:
                print("❌ API failed to start!")
                return 1
        
        # Run the test
        print("\n🧪 Running private repository test...")
        test_result = subprocess.run(
            ["python", "test_private_repo.py"],
            capture_output=False
        )
        
        if test_result.returncode == 0:
            print("\n✅ Test completed successfully!")
        else:
            print("\n❌ Test failed!")
            return 1
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted by user")
    
    finally:
        # Cleanup
        if api_process:
            print("\n🛑 Stopping API server...")
            kill_process_group(api_process)
            time.sleep(1)
        
        # Final cleanup
        subprocess.run("pkill -f 'uvicorn.*api.main' || true", shell=True)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())