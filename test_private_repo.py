#!/usr/bin/env python3
"""
Test script for private repository PR creation
"""

import asyncio
import json
import sys
import httpx
from datetime import datetime


async def test_private_repo():
    """Test the complete flow with a private repository"""
    
    # Configuration
    api_url = "http://localhost:8000/api/code"
    
    # Your private repo
    repo_url = "https://github.com/mrlancelot/tb-test"
    
    # Simple test prompt
    prompt = "Create a README.md file with the title 'TB Test Project' and a description that says 'This is a test project for Tiny Backspace autonomous coding agent.'"
    
    print("🚀 Testing Tiny Backspace with Private Repository")
    print(f"📦 Repository: {repo_url}")
    print(f"💬 Prompt: {prompt}")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        try:
            print("\n📡 Sending request to API...")
            
            # Make streaming request
            async with client.stream(
                "POST",
                api_url,
                json={
                    "repo_url": repo_url,
                    "prompt": prompt
                },
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                if response.status_code != 200:
                    print(f"❌ Error: HTTP {response.status_code}")
                    content = await response.aread()
                    print(content.decode())
                    return
                
                print("✅ Connected to streaming endpoint\n")
                
                # Process SSE stream
                pr_url = None
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            # Parse SSE data
                            data = json.loads(line[6:])
                            
                            # Format output based on event type
                            event_type = data.get("type", "unknown")
                            
                            if event_type == "start":
                                print(f"🏁 Request started: {data.get('request_id')}")
                                print(f"🔍 Trace ID: {data.get('trace_id', 'N/A')}\n")
                            
                            elif event_type == "progress":
                                stage = data.get("stage", "")
                                message = data.get("message", "")
                                percentage = data.get("percentage", 0)
                                print(f"📊 [{stage.upper()}] {message} ({percentage}%)")
                            
                            elif event_type.startswith("Tool:"):
                                tool = event_type.split(": ")[1]
                                if tool == "Read":
                                    print(f"  📖 Reading: {data.get('filepath', 'unknown')}")
                                elif tool == "Edit":
                                    print(f"  ✏️  Editing: {data.get('filepath', 'unknown')}")
                                elif tool == "Bash":
                                    cmd = data.get("command", "")
                                    output = data.get("output", "")
                                    print(f"  💻 $ {cmd}")
                                    if output and len(output) > 100:
                                        print(f"     → {output[:100]}...")
                                    elif output:
                                        print(f"     → {output}")
                            
                            elif event_type == "AI Message":
                                message = data.get("message", "")
                                if data.get("thinking"):
                                    print(f"  🤔 {message}")
                                else:
                                    print(f"  💭 {message}")
                            
                            elif event_type == "pr_created":
                                pr_url = data.get('pr_url')
                                print(f"\n✅ Pull Request Created!")
                                print(f"🔗 URL: {pr_url}")
                                print(f"🌿 Branch: {data.get('branch_name')}")
                                print(f"📝 Files changed: {data.get('files_changed')}")
                            
                            elif event_type == "error":
                                print(f"\n❌ Error: {data.get('message')}")
                                print(f"   Type: {data.get('error_type')}")
                                if data.get('details'):
                                    print(f"   Details: {data.get('details')}")
                            
                            elif event_type == "complete":
                                print(f"\n🎉 Request completed successfully!")
                            
                        except json.JSONDecodeError as e:
                            print(f"⚠️  Invalid JSON: {line}")
                            print(f"   Error: {e}")
                
                if pr_url:
                    print(f"\n🎊 Success! You can view your PR at:")
                    print(f"   {pr_url}")
                else:
                    print(f"\n⚠️  No PR was created. Check the logs above for errors.")
                
        except Exception as e:
            print(f"\n❌ Request failed: {str(e)}")
            print(f"   Type: {type(e).__name__}")


async def check_api_health():
    """Check if the API is running"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/health")
            if response.status_code == 200:
                data = response.json()
                print("✅ API is running")
                print(f"   Status: {data.get('status')}")
                print(f"   Sandbox: {data.get('sandbox_provider')}")
                print(f"   Agent: {data.get('agent')}")
                return True
            else:
                print(f"❌ API returned status {response.status_code}")
                return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        print("\n💡 Make sure the API is running:")
        print("   ./run_api.sh")
        print("   or")
        print("   cd api && python main.py")
        return False


async def main():
    """Run the test"""
    print("🧪 Tiny Backspace Private Repository Test")
    print("=" * 60)
    
    # Check API health first
    print("\n🏥 Checking API health...")
    if not await check_api_health():
        sys.exit(1)
    
    print("\n" + "=" * 60)
    
    # Run the test
    await test_private_repo()


if __name__ == "__main__":
    asyncio.run(main())