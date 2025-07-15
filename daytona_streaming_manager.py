"""
Daytona Streaming Manager - Provides real-time command execution with streaming output
Uses Daytona's native session API for streaming capabilities
"""

import asyncio
import uuid
from typing import AsyncGenerator, Callable, Optional, Dict, Any
from daytona import Daytona, SessionExecuteRequest
from rich.console import Console


class DaytonaStreamingManager:
    """Manages streaming command execution using Daytona's session API"""
    
    def __init__(self, daytona_url: str = "https://app.daytona.io/api", api_key: Optional[str] = None):
        from daytona import DaytonaConfig
        
        config = DaytonaConfig(
            api_key=api_key,
            api_url=daytona_url
        )
        self.daytona = Daytona(config)
        self.console = Console()
    
    async def execute_streaming_command(
        self,
        sandbox_id: str,
        command: str,
        on_output: Callable[[str], None],
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Execute a command with streaming output using Daytona sessions
        
        Args:
            sandbox_id: ID of the sandbox to execute in
            command: Command to execute
            on_output: Callback function for streaming output
            timeout: Optional timeout in seconds
            
        Returns:
            Dict with execution results including exit_code and full output
        """
        session_id = f"stream-{uuid.uuid4().hex[:8]}"
        
        try:
            # Get sandbox
            sandbox = self.daytona.get_sandbox(sandbox_id)
            
            # Create a session
            sandbox.process.create_session(session_id)
            
            # Execute command asynchronously
            req = SessionExecuteRequest(
                command=command,
                run_async=True  # Important: run asynchronously to enable streaming
            )
            
            # Start command execution
            response = sandbox.process.execute_session_command(session_id, req)
            cmd_id = response.cmd_id
            
            # Stream logs
            full_output = []
            
            async def collect_logs(chunk: str):
                # Callback for streaming chunks
                full_output.append(chunk)
                on_output(chunk)
            
            # Use async version if available, otherwise convert sync to async
            if hasattr(sandbox.process, 'get_session_command_logs_async'):
                # Use native async method
                await sandbox.process.get_session_command_logs_async(
                    session_id,
                    cmd_id,
                    collect_logs
                )
            else:
                # Fallback: use sync version in thread
                await asyncio.to_thread(
                    self._stream_logs_sync,
                    sandbox,
                    session_id,
                    cmd_id,
                    collect_logs
                )
            
            # Get final command status
            cmd_info = sandbox.process.get_session_command(session_id, cmd_id)
            
            return {
                "exit_code": cmd_info.exit_code or 0,
                "output": "".join(full_output),
                "cmd_id": cmd_id,
                "session_id": session_id
            }
            
        finally:
            # Cleanup session
            try:
                sandbox.process.delete_session(session_id)
            except:
                pass  # Best effort cleanup
    
    def _stream_logs_sync(self, sandbox, session_id: str, cmd_id: str, on_output: Callable):
        """Synchronous helper for streaming logs"""
        import time
        
        # Poll for logs until command completes
        last_position = 0
        while True:
            # Get command status
            cmd_info = sandbox.process.get_session_command(session_id, cmd_id)
            
            # Get logs
            logs = sandbox.process.get_session_command_logs(session_id, cmd_id)
            
            # Send new output
            if logs and len(logs) > last_position:
                new_output = logs[last_position:]
                on_output(new_output)
                last_position = len(logs)
            
            # Check if command completed
            if cmd_info.exit_code is not None:
                break
            
            # Small delay to avoid overwhelming the API
            time.sleep(0.1)
    
    async def execute_claude_streaming(
        self,
        sandbox_id: str,
        repo_path: str,
        prompt: str,
        on_output: Callable[[str], None]
    ) -> Dict[str, Any]:
        """
        Execute Claude Code with streaming output
        
        Args:
            sandbox_id: ID of the sandbox
            repo_path: Path to repository in sandbox
            prompt: Prompt for Claude
            on_output: Callback for streaming output
            
        Returns:
            Execution results
        """
        # Format Claude command
        command = f'cd {repo_path} && claude --print "{prompt}"'
        
        # Execute with streaming
        return await self.execute_streaming_command(
            sandbox_id,
            command,
            on_output
        )
    
    async def debug_sandbox_state(self, sandbox_id: str) -> None:
        """Debug helper to check sandbox state and directories"""
        sandbox = self.daytona.get_sandbox(sandbox_id)
        
        # Commands to debug
        debug_commands = [
            "pwd",
            "ls -la /",
            "ls -la ~",
            "ls -la /root",
            "find / -name '.git' -type d 2>/dev/null | head -10",
            "env | grep -E 'HOME|USER|PWD'"
        ]
        
        for cmd in debug_commands:
            self.console.print(f"\n[yellow]$ {cmd}[/yellow]")
            result = await self.execute_streaming_command(
                sandbox_id,
                cmd,
                lambda chunk: self.console.print(chunk, end="")
            )
            if result["exit_code"] != 0:
                self.console.print(f"[red]Exit code: {result['exit_code']}[/red]")


# Example usage
async def main():
    """Example of using the streaming manager"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # Initialize streaming manager
    manager = DaytonaStreamingManager(
        api_key=os.getenv("DAYTONA_API_KEY")
    )
    
    # Example: Execute a streaming command
    sandbox_id = "your-sandbox-id"
    
    # Stream output from a long-running command
    print("Executing streaming command...")
    result = await manager.execute_streaming_command(
        sandbox_id,
        "for i in {1..5}; do echo \"Line $i\"; sleep 1; done",
        lambda chunk: print(f"STREAM: {chunk}", end="")
    )
    
    print(f"\nCommand completed with exit code: {result['exit_code']}")
    
    # Debug sandbox state
    print("\n--- Debugging Sandbox State ---")
    await manager.debug_sandbox_state(sandbox_id)


if __name__ == "__main__":
    asyncio.run(main())