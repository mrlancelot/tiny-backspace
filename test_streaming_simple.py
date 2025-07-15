#!/usr/bin/env python3
"""Simple test for streaming functionality"""

import asyncio
from streaming_response import StreamingResponseHandler, ResponseType
from rich.console import Console

async def test_streaming():
    console = Console()
    handler = StreamingResponseHandler(console)
    
    # Mock execution function that simulates Daytona sandbox response
    def mock_sandbox_exec(command: str):
        # Simulate different responses based on command
        if "claude" in command:
            return type('Response', (), {
                'result': '''{"type": "thinking", "content": "Analyzing the request for a hello world function..."}
{"type": "thinking", "content": "I'll create a simple Python function..."}
{"type": "content", "content": "Here's a simple hello world function in Python:"}
{"type": "code", "content": "```python\\ndef hello_world():\\n    print('Hello, World!')\\n\\n# Call the function\\nhello_world()\\n```"}
{"type": "content", "content": "This function simply prints 'Hello, World!' when called."}'''
            })()
        else:
            return type('Response', (), {'result': 'Command executed successfully'})()
    
    console.print("[bold cyan]Testing Streaming Response Handler[/bold cyan]\n")
    
    # Test 1: Claude response streaming
    console.print("[yellow]Test 1: Claude response with thinking, content, and code[/yellow]")
    command = "claude --print 'Write a hello world function'"
    
    response_gen = handler.stream_claude_response(command, mock_sandbox_exec)
    await handler.display_streaming_response(response_gen)
    
    console.print("\n[green]✅ Streaming test completed![/green]")

if __name__ == "__main__":
    asyncio.run(test_streaming())