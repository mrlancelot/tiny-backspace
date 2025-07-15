#!/usr/bin/env python3
"""
Streaming Response Handler for Claude interactions
Provides real-time streaming output with thinking process visibility
"""

import asyncio
import json
import sys
import time
from typing import AsyncGenerator, Optional, Dict, Any, Callable
from dataclasses import dataclass
from enum import Enum
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax


class ResponseType(Enum):
    THINKING = "thinking"
    CONTENT = "content"
    CODE = "code"
    ERROR = "error"
    PERMISSION = "permission"
    PROGRESS = "progress"


@dataclass
class StreamChunk:
    type: ResponseType
    content: str
    metadata: Optional[Dict[str, Any]] = None


class StreamingResponseHandler:
    def __init__(self, console: Optional[Console] = None):
        """Initialize streaming response handler"""
        self.console = console or Console()
        self.thinking_buffer = []
        self.content_buffer = []
        self.is_streaming = False
        
    async def stream_claude_response(self, 
                                   command: str,
                                   sandbox_exec_func: Callable) -> AsyncGenerator[StreamChunk, None]:
        """Stream Claude response with real-time output"""
        self.is_streaming = True
        
        # Start with thinking indicator
        yield StreamChunk(
            type=ResponseType.THINKING,
            content="Analyzing request...",
            metadata={"phase": "initialization"}
        )
        
        try:
            # Execute command with streaming output format
            stream_cmd = f'{command} --output-format stream-json --verbose'
            
            # Simulate async execution (in real implementation, this would be truly async)
            response = await asyncio.to_thread(sandbox_exec_func, stream_cmd)
            
            if hasattr(response, 'result') and response.result:
                # Parse streaming JSON output
                lines = response.result.strip().split('\n')
                
                for line in lines:
                    if not line.strip():
                        continue
                        
                    try:
                        # Try to parse as JSON streaming event
                        if line.startswith('{'):
                            event = json.loads(line)
                            chunk = self._parse_claude_event(event)
                            if chunk:
                                yield chunk
                        else:
                            # Regular text output
                            yield StreamChunk(
                                type=ResponseType.CONTENT,
                                content=line
                            )
                            
                    except json.JSONDecodeError:
                        # Fallback for non-JSON output
                        yield StreamChunk(
                            type=ResponseType.CONTENT,
                            content=line
                        )
                    
                    # Small delay to simulate streaming
                    await asyncio.sleep(0.01)
            
        except Exception as e:
            yield StreamChunk(
                type=ResponseType.ERROR,
                content=f"Error: {str(e)}",
                metadata={"error_type": type(e).__name__}
            )
        
        finally:
            self.is_streaming = False
    
    def _parse_claude_event(self, event: Dict[str, Any]) -> Optional[StreamChunk]:
        """Parse Claude streaming event into StreamChunk"""
        event_type = event.get('type', '')
        
        if event_type == 'thinking':
            return StreamChunk(
                type=ResponseType.THINKING,
                content=event.get('content', ''),
                metadata={"reasoning_step": event.get('step', 0)}
            )
        
        elif event_type == 'content':
            content = event.get('content', '')
            
            # Detect code blocks
            if '```' in content:
                return StreamChunk(
                    type=ResponseType.CODE,
                    content=content,
                    metadata={"language": self._detect_language(content)}
                )
            
            return StreamChunk(
                type=ResponseType.CONTENT,
                content=content
            )
        
        elif event_type == 'error':
            return StreamChunk(
                type=ResponseType.ERROR,
                content=event.get('message', 'Unknown error')
            )
        
        return None
    
    def _detect_language(self, content: str) -> str:
        """Detect programming language from code block"""
        if '```python' in content:
            return 'python'
        elif '```javascript' in content or '```js' in content:
            return 'javascript'
        elif '```bash' in content or '```sh' in content:
            return 'bash'
        return 'text'
    
    async def display_streaming_response(self, 
                                       response_generator: AsyncGenerator[StreamChunk, None]):
        """Display streaming response with rich formatting"""
        with Live(console=self.console, refresh_per_second=10) as live:
            thinking_panel = None
            content_parts = []
            
            async for chunk in response_generator:
                if chunk.type == ResponseType.THINKING:
                    # Update thinking panel
                    self.thinking_buffer.append(chunk.content)
                    thinking_text = "\n".join(self.thinking_buffer[-5:])  # Show last 5 thoughts
                    thinking_panel = Panel(
                        thinking_text,
                        title="🧠 Claude's Thinking Process",
                        border_style="blue"
                    )
                    live.update(thinking_panel)
                
                elif chunk.type == ResponseType.CONTENT:
                    # Add to content buffer
                    content_parts.append(chunk.content)
                    
                    # Create combined display
                    if thinking_panel:
                        display = Table.grid()
                        display.add_row(thinking_panel)
                        display.add_row("")  # Spacer
                        display.add_row(Panel(
                            "\n".join(content_parts),
                            title="💬 Response",
                            border_style="green"
                        ))
                        live.update(display)
                    else:
                        live.update("\n".join(content_parts))
                
                elif chunk.type == ResponseType.CODE:
                    # Display code with syntax highlighting
                    code_content = chunk.content.strip('`')
                    language = chunk.metadata.get('language', 'python')
                    
                    syntax = Syntax(
                        code_content,
                        language,
                        theme="monokai",
                        line_numbers=True
                    )
                    
                    content_parts.append("")  # Add spacing
                    display = Table.grid()
                    if thinking_panel:
                        display.add_row(thinking_panel)
                    display.add_row(Panel(syntax, title=f"📝 Code ({language})"))
                    live.update(display)
                
                elif chunk.type == ResponseType.ERROR:
                    # Display error
                    error_panel = Panel(
                        chunk.content,
                        title="❌ Error",
                        border_style="red"
                    )
                    live.update(error_panel)
                
                await asyncio.sleep(0.01)  # Small delay for smooth updates
    
    def create_progress_indicator(self, total_steps: int = 100) -> Progress:
        """Create a progress indicator for long-running operations"""
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=self.console
        )
    
    async def show_operation_progress(self, 
                                    operation_name: str,
                                    steps: list,
                                    execute_func: Callable):
        """Show progress for multi-step operations"""
        with self.create_progress_indicator(len(steps)) as progress:
            task = progress.add_task(f"[cyan]{operation_name}", total=len(steps))
            
            for i, step in enumerate(steps):
                # Update progress description
                progress.update(task, description=f"[cyan]{operation_name}: {step['name']}")
                
                # Execute step
                try:
                    result = await asyncio.to_thread(execute_func, step['command'])
                    
                    if step.get('validate'):
                        # Validate step result if validation function provided
                        if not step['validate'](result):
                            self.console.print(f"[yellow]⚠️  Warning: {step['name']} validation failed")
                    
                except Exception as e:
                    self.console.print(f"[red]❌ Error in {step['name']}: {e}")
                
                # Update progress
                progress.update(task, advance=1)
                
                # Small delay for visual feedback
                await asyncio.sleep(0.1)
        
        self.console.print(f"[green]✅ {operation_name} completed!")


class ThinkingVisualizer:
    """Visualize Claude's thinking process in real-time"""
    
    def __init__(self, console: Console):
        self.console = console
        self.thoughts = []
        
    def add_thought(self, thought: str, reasoning_type: str = "general"):
        """Add a thought to the visualization"""
        timestamp = time.strftime("%H:%M:%S")
        self.thoughts.append({
            "time": timestamp,
            "type": reasoning_type,
            "content": thought
        })
    
    def render_thinking_tree(self):
        """Render thinking process as a tree structure"""
        tree = Table(title="🧠 Reasoning Process", show_header=True)
        tree.add_column("Time", style="dim", width=8)
        tree.add_column("Type", style="cyan", width=12)
        tree.add_column("Thought", style="white")
        
        for thought in self.thoughts[-10:]:  # Show last 10 thoughts
            tree.add_row(
                thought["time"],
                thought["type"],
                thought["content"][:80] + "..." if len(thought["content"]) > 80 else thought["content"]
            )
        
        return tree


# Example usage function
async def example_streaming_usage():
    """Example of how to use the streaming response handler"""
    console = Console()
    handler = StreamingResponseHandler(console)
    
    # Example mock sandbox execution function
    def mock_sandbox_exec(command: str) -> Dict[str, Any]:
        # Simulate streaming response
        return {
            'result': '''{"type": "thinking", "content": "Understanding the user's request..."}
{"type": "thinking", "content": "Breaking down the problem into steps..."}
{"type": "content", "content": "I'll help you create a Python function."}
{"type": "code", "content": "```python\\ndef hello_world():\\n    print('Hello, World!')\\n```"}
{"type": "content", "content": "This function prints a greeting message."}'''
        }
    
    # Create mock command
    command = "claude --print 'Create a hello world function'"
    
    # Stream and display response
    response_gen = handler.stream_claude_response(command, mock_sandbox_exec)
    await handler.display_streaming_response(response_gen)


if __name__ == "__main__":
    # Run example
    asyncio.run(example_streaming_usage())