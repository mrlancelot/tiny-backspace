#!/usr/bin/env python3
"""
Gemini Streaming Response Handler
Handles real-time streaming of Gemini CLI output with SSE support
"""

import re
import json
import asyncio
from typing import AsyncGenerator, Dict, Any, Optional, Callable
from datetime import datetime
from rich.console import Console


class GeminiStreamingHandler:
    """Handles streaming responses from Gemini CLI"""
    
    def __init__(self, console: Optional[Console] = None):
        """Initialize the streaming handler"""
        self.console = console or Console()
        self.tool_patterns = {
            'read': re.compile(r'Reading file:\s*(.+)'),
            'write': re.compile(r'Writing to file:\s*(.+)'),
            'edit': re.compile(r'Editing file:\s*(.+)'),
            'bash': re.compile(r'Executing command:\s*(.+)'),
            'analyze': re.compile(r'Analyzing:\s*(.+)'),
            'git': re.compile(r'Git operation:\s*(.+)')
        }
    
    def parse_gemini_output(self, line: str) -> Optional[Dict[str, Any]]:
        """Parse Gemini CLI output and identify tool usage"""
        # Skip empty lines
        if not line.strip():
            return None
        
        # Check for tool usage patterns
        for tool_type, pattern in self.tool_patterns.items():
            match = pattern.search(line)
            if match:
                return {
                    "type": f"Tool: {tool_type.capitalize()}",
                    "content": match.group(1),
                    "timestamp": datetime.now().isoformat()
                }
        
        # Check for Git operations
        if any(keyword in line.lower() for keyword in ['git', 'commit', 'push', 'branch']):
            return {
                "type": "Tool: Git",
                "content": line.strip(),
                "timestamp": datetime.now().isoformat()
            }
        
        # Default to AI message
        return {
            "type": "AI Message",
            "message": line.strip(),
            "timestamp": datetime.now().isoformat()
        }
    
    async def stream_gemini_response(self, 
                                   command: str,
                                   execute_func: Callable) -> AsyncGenerator[str, None]:
        """Stream Gemini response as Server-Sent Events"""
        try:
            # Start with initial event
            yield self._format_sse({
                "type": "start",
                "message": "Starting Gemini analysis...",
                "timestamp": datetime.now().isoformat()
            })
            
            # Execute command and capture output
            output = await execute_func(command)
            
            # Process output line by line
            lines = output.split('\n') if isinstance(output, str) else []
            
            for line in lines:
                event = self.parse_gemini_output(line)
                if event:
                    yield self._format_sse(event)
                    await asyncio.sleep(0.1)  # Small delay for streaming effect
            
            # End event
            yield self._format_sse({
                "type": "complete",
                "message": "Gemini analysis complete",
                "timestamp": datetime.now().isoformat()
            })
            
        except Exception as e:
            yield self._format_sse({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })
    
    def _format_sse(self, data: Dict[str, Any]) -> str:
        """Format data as Server-Sent Event"""
        return f"data: {json.dumps(data)}\n\n"
    
    async def stream_coding_process(self,
                                  sandbox_operations: Dict[str, Callable],
                                  repo_url: str,
                                  prompt: str) -> AsyncGenerator[str, None]:
        """Stream the entire coding process including clone, code changes, and PR creation"""
        
        # Step 1: Clone repository
        yield self._format_sse({
            "type": "Tool: Git",
            "operation": "clone",
            "message": f"Cloning repository: {repo_url}",
            "timestamp": datetime.now().isoformat()
        })
        
        clone_result = await asyncio.to_thread(sandbox_operations['clone'], repo_url)
        
        if not clone_result:
            yield self._format_sse({
                "type": "error",
                "message": "Failed to clone repository",
                "timestamp": datetime.now().isoformat()
            })
            return
        
        yield self._format_sse({
            "type": "Tool: Git",
            "operation": "clone_complete",
            "message": "Repository cloned successfully",
            "timestamp": datetime.now().isoformat()
        })
        
        # Step 2: Execute Gemini prompt
        yield self._format_sse({
            "type": "AI Message",
            "message": f"Analyzing request: {prompt}",
            "timestamp": datetime.now().isoformat()
        })
        
        repo_name = repo_url.rstrip('/').split('/')[-1].replace('.git', '')
        gemini_result = await asyncio.to_thread(
            sandbox_operations['execute_gemini'], 
            prompt, 
            repo_name
        )
        
        # Stream Gemini output
        if gemini_result.get('output'):
            for line in gemini_result['output'].split('\n'):
                if line.strip():
                    event = self.parse_gemini_output(line)
                    if event:
                        yield self._format_sse(event)
                        await asyncio.sleep(0.05)
        
        # Step 3: Create PR
        if gemini_result.get('success'):
            yield self._format_sse({
                "type": "Tool: Git",
                "operation": "pr_start",
                "message": "Creating pull request...",
                "timestamp": datetime.now().isoformat()
            })
            
            branch_name = f"gemini-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            pr_title = f"Implement: {prompt[:50]}..."
            pr_body = f"This PR implements the following request:\n\n{prompt}\n\n---\n*Generated by Gemini CLI*"
            
            pr_url = await asyncio.to_thread(
                sandbox_operations['create_pr'],
                repo_name,
                branch_name,
                pr_title,
                pr_body
            )
            
            if pr_url:
                yield self._format_sse({
                    "type": "Tool: Git",
                    "operation": "pr_complete",
                    "message": f"Pull request created: {pr_url}",
                    "pr_url": pr_url,
                    "timestamp": datetime.now().isoformat()
                })
                
                yield self._format_sse({
                    "type": "complete",
                    "message": "Task completed successfully",
                    "pr_url": pr_url,
                    "timestamp": datetime.now().isoformat()
                })
            else:
                yield self._format_sse({
                    "type": "error",
                    "message": "Failed to create pull request",
                    "timestamp": datetime.now().isoformat()
                })
        else:
            yield self._format_sse({
                "type": "error",
                "message": "Gemini execution failed",
                "timestamp": datetime.now().isoformat()
            })
    
    async def display_streaming_response(self, response_generator: AsyncGenerator[str, None]) -> None:
        """Display streaming response in the console"""
        self.console.print("\n[bold]📡 Streaming Gemini Response:[/bold]\n")
        
        async for event_data in response_generator:
            try:
                # Parse SSE data
                if event_data.startswith("data: "):
                    data = json.loads(event_data[6:])
                    
                    # Format and display based on type
                    if data.get("type") == "Tool: Read":
                        self.console.print(f"[blue]📖 Reading: {data.get('content', '')}[/blue]")
                    elif data.get("type") == "Tool: Write":
                        self.console.print(f"[green]✏️  Writing: {data.get('content', '')}[/green]")
                    elif data.get("type") == "Tool: Edit":
                        self.console.print(f"[yellow]📝 Editing: {data.get('content', '')}[/yellow]")
                    elif data.get("type") == "Tool: Bash":
                        self.console.print(f"[magenta]🖥️  Command: {data.get('content', '')}[/magenta]")
                    elif data.get("type") == "Tool: Git":
                        self.console.print(f"[cyan]🔀 Git: {data.get('message', data.get('content', ''))}[/cyan]")
                    elif data.get("type") == "AI Message":
                        self.console.print(f"[dim]🤖 {data.get('message', '')}[/dim]")
                    elif data.get("type") == "error":
                        self.console.print(f"[red]❌ Error: {data.get('message', '')}[/red]")
                    elif data.get("type") == "complete":
                        self.console.print(f"\n[bold green]✅ {data.get('message', '')}[/bold green]")
                        if data.get("pr_url"):
                            self.console.print(f"[bold blue]🔗 PR URL: {data.get('pr_url')}[/bold blue]")
                    
            except json.JSONDecodeError:
                # Handle non-JSON output
                self.console.print(f"[dim]{event_data}[/dim]")
            except Exception as e:
                self.console.print(f"[red]Error processing event: {e}[/red]")


# Example usage
async def test_streaming():
    """Test the streaming handler"""
    handler = GeminiStreamingHandler()
    
    # Mock execute function
    async def mock_execute(cmd):
        await asyncio.sleep(1)
        return """
Reading file: src/main.py
Analyzing: Code structure and dependencies
Writing to file: src/feature.py
Executing command: python -m pytest
Git operation: Creating feature branch
"""
    
    # Test streaming
    response_gen = handler.stream_gemini_response("gemini 'Add new feature'", mock_execute)
    await handler.display_streaming_response(response_gen)


if __name__ == "__main__":
    asyncio.run(test_streaming())