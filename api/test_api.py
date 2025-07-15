"""
Test script for Tiny Backspace API
"""

import asyncio
import json
import httpx
from datetime import datetime


async def test_streaming_api():
    """Test the streaming API endpoint"""
    
    # Test configuration
    api_url = "http://localhost:8000/api/code"
    test_request = {
        "repo_url": "https://github.com/octocat/Hello-World",
        "prompt": "Add a Python script that prints the current date and time"
    }
    
    print(f"🚀 Testing Tiny Backspace API")
    print(f"📍 Endpoint: {api_url}")
    print(f"📦 Repository: {test_request['repo_url']}")
    print(f"💬 Prompt: {test_request['prompt']}")
    print("-" * 60)
    
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            # Make streaming request
            async with client.stream(
                "POST",
                api_url,
                json=test_request,
                headers={"Accept": "text/event-stream"}
            ) as response:
                
                if response.status_code != 200:
                    print(f"❌ Error: {response.status_code}")
                    print(await response.aread())
                    return
                
                # Process SSE stream
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        try:
                            # Parse SSE data
                            data = json.loads(line[6:])
                            
                            # Format output based on event type
                            event_type = data.get("type", "unknown")
                            timestamp = data.get("timestamp", "")
                            
                            if event_type == "start":
                                print(f"\n🏁 Request started: {data.get('request_id')}")
                            
                            elif event_type == "progress":
                                stage = data.get("stage", "")
                                message = data.get("message", "")
                                percentage = data.get("percentage", 0)
                                print(f"📊 [{stage}] {message} ({percentage}%)")
                            
                            elif event_type.startswith("Tool:"):
                                tool = event_type.split(": ")[1]
                                if tool == "Read":
                                    print(f"📖 Reading: {data.get('filepath', 'unknown')}")
                                elif tool == "Edit":
                                    print(f"✏️  Editing: {data.get('filepath', 'unknown')}")
                                elif tool == "Bash":
                                    cmd = data.get("command", "")
                                    print(f"💻 $ {cmd}")
                                    if data.get("output"):
                                        print(f"   → {data['output'][:100]}...")
                            
                            elif event_type == "AI Message":
                                message = data.get("message", "")
                                if data.get("thinking"):
                                    print(f"🤔 Thinking: {message}")
                                else:
                                    print(f"💭 {message}")
                            
                            elif event_type == "pr_created":
                                print(f"\n✅ Pull Request Created!")
                                print(f"🔗 URL: {data.get('pr_url')}")
                                print(f"📝 Branch: {data.get('branch_name')}")
                                print(f"📊 Files changed: {data.get('files_changed')}")
                                print(f"📄 Summary: {data.get('summary')}")
                            
                            elif event_type == "error":
                                print(f"\n❌ Error: {data.get('message')}")
                                print(f"   Type: {data.get('error_type')}")
                            
                            elif event_type == "complete":
                                print(f"\n🎉 Request completed!")
                                print(f"⏱️  Duration: Calculate from timestamps")
                            
                        except json.JSONDecodeError:
                            print(f"⚠️  Invalid JSON: {line}")
                
        except Exception as e:
            print(f"❌ Request failed: {str(e)}")


async def test_health_endpoint():
    """Test the health check endpoint"""
    
    api_url = "http://localhost:8000/health"
    
    print("\n🏥 Testing Health Endpoint")
    print(f"📍 URL: {api_url}")
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(api_url)
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Status: {data.get('status')}")
                print(f"🕒 Timestamp: {data.get('timestamp')}")
                print(f"📦 Sandbox Provider: {data.get('sandbox_provider')}")
                print(f"🤖 Agent: {data.get('agent')}")
            else:
                print(f"❌ Error: {response.status_code}")
                
        except Exception as e:
            print(f"❌ Health check failed: {str(e)}")


async def main():
    """Run all tests"""
    
    # Test health first
    await test_health_endpoint()
    
    # Then test streaming
    print("\n" + "=" * 60)
    await test_streaming_api()


if __name__ == "__main__":
    print("🧪 Tiny Backspace API Test Suite")
    print("=" * 60)
    
    asyncio.run(main())