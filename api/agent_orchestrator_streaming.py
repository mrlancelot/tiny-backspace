"""
Agent Orchestrator with Streaming Support
Enhanced version that uses Daytona's native streaming capabilities
"""

import os
import asyncio
import re
import uuid
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime
from pathlib import Path

from config import Settings
from models import StreamEvent, StreamEventType
from sse_adapter import SSEAdapter
from daytona_manager_refactored import DaytonaManagerRefactored
from rich.console import Console
from daytona import SessionExecuteRequest


class StreamingAgentOrchestrator:
    """Orchestrates the agent workflow with real-time streaming support"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.sse_adapter = SSEAdapter()
        self.console = Console(quiet=True)
        self.manager = DaytonaManagerRefactored(console=self.console)
        
        # Base directory will be set dynamically based on sandbox
        self.base_dir = None
        # Full path to the cloned repository
        self.repo_path = None
        
        # Override permission checks for automated operation
        self.manager.permission_manager.saved_permissions = {
            "CREATE_SANDBOX": {"all": True},
            "EXECUTE_COMMAND": {"all": True},
            "DELETE_SANDBOX": {"all": True}
        }
    
    async def _execute_streaming_command(
        self,
        sandbox: Any,
        command: str,
        on_output: Optional[Callable[[str], None]] = None
    ) -> Dict[str, Any]:
        """Execute a command with streaming output using Daytona sessions"""
        session_id = f"stream-{uuid.uuid4().hex[:8]}"
        
        try:
            # Create a session
            sandbox.process.create_session(session_id)
            
            # Execute command asynchronously
            req = SessionExecuteRequest(
                command=command,
                run_async=True  # Important for streaming
            )
            
            # Start command execution
            response = sandbox.process.execute_session_command(session_id, req)
            cmd_id = response.cmd_id
            
            # Collect output
            full_output = []
            
            async def collect_logs(chunk: str):
                full_output.append(chunk)
                if on_output:
                    on_output(chunk)
            
            # Stream logs using async method
            if hasattr(sandbox.process, 'get_session_command_logs_async'):
                await sandbox.process.get_session_command_logs_async(
                    session_id,
                    cmd_id,
                    collect_logs
                )
            else:
                # Fallback to polling
                await self._poll_command_logs(sandbox, session_id, cmd_id, collect_logs)
            
            # Get final command status
            cmd_info = sandbox.process.get_session_command(session_id, cmd_id)
            
            return {
                "success": True,
                "exit_code": cmd_info.exit_code or 0,
                "output": "".join(full_output)
            }
            
        except Exception as e:
            return {
                "success": False,
                "exit_code": -1,
                "output": str(e)
            }
        finally:
            # Cleanup session
            try:
                sandbox.process.delete_session(session_id)
            except:
                pass
    
    async def _poll_command_logs(self, sandbox, session_id: str, cmd_id: str, on_output: Callable):
        """Fallback polling method for streaming logs"""
        last_position = 0
        while True:
            # Get command status
            cmd_info = await asyncio.to_thread(
                sandbox.process.get_session_command,
                session_id,
                cmd_id
            )
            
            # Get logs
            logs = await asyncio.to_thread(
                sandbox.process.get_session_command_logs,
                session_id,
                cmd_id
            )
            
            # Send new output
            if logs and len(logs) > last_position:
                new_output = logs[last_position:]
                await on_output(new_output)
                last_position = len(logs)
            
            # Check if command completed
            if cmd_info.exit_code is not None:
                break
            
            # Small delay
            await asyncio.sleep(0.1)
    
    async def _execute_agent_streaming(
        self, 
        sandbox: Any, 
        repo: str,
        prompt: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Execute Claude agent with real-time streaming"""
        
        # Format prompt for Claude
        agent_prompt = f"""You are working in the repository {self.repo_path}.
        
Task: {prompt}

Instructions:
1. First explore the repository structure to understand the codebase
2. Identify the files that need to be modified
3. Make the necessary changes to implement the requested feature
4. Ensure your changes follow the existing code style and conventions
5. Do not modify configuration files unless necessary
6. Focus only on the specific task requested

Start by exploring the repository structure."""
        
        # Stream Claude execution
        command = f'cd {self.repo_path} && claude --print "{agent_prompt}"'
        
        yield await self.sse_adapter.create_tool_event(
            "AI Message",
            message="Starting code analysis and implementation...",
            thinking=True
        )
        
        # Buffer for parsing multi-line outputs
        output_buffer = []
        
        async def handle_output(chunk: str):
            """Process streaming output from Claude"""
            nonlocal output_buffer
            
            # Add chunk to buffer
            output_buffer.append(chunk)
            
            # Process complete lines
            full_text = "".join(output_buffer)
            lines = full_text.split('\n')
            
            # Keep incomplete line in buffer
            if not full_text.endswith('\n'):
                output_buffer = [lines[-1]]
                lines = lines[:-1]
            else:
                output_buffer = []
            
            # Process each complete line
            for line in lines:
                if line.strip():
                    # Detect different types of output
                    if line.startswith("Reading ") or line.startswith("Editing "):
                        yield await self.sse_adapter.create_tool_event(
                            "File Operation",
                            message=line
                        )
                    elif line.startswith("$ "):
                        yield await self.sse_adapter.create_tool_event(
                            "Bash",
                            command=line[2:],
                            output=""
                        )
                    elif line.startswith("```"):
                        # Code block marker
                        continue
                    else:
                        # Regular output
                        yield await self.sse_adapter.create_tool_event(
                            "AI Message",
                            message=line
                        )
        
        # Create async generator wrapper
        output_queue = asyncio.Queue()
        
        async def output_handler(chunk: str):
            async for event in handle_output(chunk):
                await output_queue.put(event)
        
        # Start streaming execution
        exec_task = asyncio.create_task(
            self._execute_streaming_command(
                sandbox,
                command,
                lambda chunk: asyncio.create_task(output_handler(chunk))
            )
        )
        
        # Yield events as they come
        while True:
            try:
                # Wait for either a new event or execution completion
                get_event = asyncio.create_task(output_queue.get())
                done, pending = await asyncio.wait(
                    [get_event, exec_task],
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                if get_event in done:
                    event = await get_event
                    yield event
                
                if exec_task in done:
                    # Execution completed, drain remaining events
                    while not output_queue.empty():
                        yield await output_queue.get()
                    break
                    
            except Exception as e:
                yield await self.sse_adapter.create_tool_event(
                    "Error",
                    message=f"Streaming error: {str(e)}"
                )
                break
        
        # Get execution result
        result = await exec_task
        if not result["success"]:
            yield await self.sse_adapter.create_tool_event(
                "Error",
                message=f"Agent execution failed: {result['output']}"
            )
    
    async def debug_sandbox(self, sandbox: Any) -> None:
        """Debug sandbox state using streaming commands"""
        debug_commands = [
            ("pwd", "Current directory"),
            ("ls -la /", "Root directory"),
            ("ls -la ~", "Home directory"),
            ("ls -la /root", "/root directory"),
            ("find / -name '.git' -type d 2>/dev/null | head -10", "Git repositories"),
            ("env | grep -E 'HOME|USER|PWD'", "Environment variables")
        ]
        
        for cmd, description in debug_commands:
            print(f"\n=== {description} ===")
            result = await self._execute_streaming_command(
                sandbox,
                cmd,
                lambda chunk: print(chunk, end="")
            )
            if result["exit_code"] != 0:
                print(f"\nError: Exit code {result['exit_code']}")
    
    # Include all other methods from original AgentOrchestrator
    # (process_request, _parse_github_url, _clone_repository, etc.)
    # Just replace _execute_agent with _execute_agent_streaming
    
    async def process_request(
        self,
        request_id: str,
        repo_url: str,
        prompt: str
    ) -> AsyncGenerator[StreamEvent, None]:
        """Process a code change request with streaming support"""
        
        sandbox = None
        sandbox_id = None
        
        try:
            # ... (same initial setup as original) ...
            
            # When executing agent, use streaming version
            async for event in self._execute_agent_streaming(sandbox, repo, prompt):
                yield event
            
            # ... (rest of the process_request method) ...
            
        except Exception as e:
            yield StreamEvent(
                type=StreamEventType.ERROR,
                data={
                    "error_type": type(e).__name__,
                    "message": str(e),
                    "request_id": request_id
                }
            )
        
        finally:
            if sandbox_id:
                try:
                    await asyncio.to_thread(
                        self.manager.delete_sandbox,
                        sandbox_id
                    )
                except:
                    pass