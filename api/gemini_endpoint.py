#!/usr/bin/env python3
"""
FastAPI endpoint for Gemini-based autonomous coding agent
Implements POST /code endpoint with Server-Sent Events streaming
"""

import os
import sys
import asyncio
from typing import Optional
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, HttpUrl
from rich.console import Console

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gemini_daytona_manager import GeminiDaytonaManager
from gemini_streaming import GeminiStreamingHandler


# Request model
class CodeRequest(BaseModel):
    repoUrl: HttpUrl
    prompt: str


# Sandbox cleanup manager
active_sandboxes = []


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifecycle - cleanup sandboxes on shutdown"""
    yield
    # Cleanup sandboxes on shutdown
    console = Console()
    if active_sandboxes:
        console.print("[yellow]🧹 Cleaning up sandboxes...[/yellow]")
        manager = GeminiDaytonaManager(console)
        for sandbox_id in active_sandboxes:
            try:
                manager.delete_sandbox(sandbox_id)
            except:
                pass


# Create FastAPI app
app = FastAPI(
    title="Gemini Autonomous Coding Agent",
    description="Creates PRs automatically using Gemini CLI in Daytona sandboxes",
    version="1.0.0",
    lifespan=lifespan
)

# Initialize console for logging
console = Console()


@app.get("/")
async def root():
    """Root endpoint with API information"""
    return {
        "name": "Gemini Autonomous Coding Agent",
        "version": "1.0.0",
        "endpoints": {
            "POST /code": "Create PR from repo URL and prompt",
            "GET /health": "Health check"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "active_sandboxes": len(active_sandboxes)
    }


@app.post("/code")
async def create_code_pr(request: CodeRequest):
    """
    Create a PR based on the provided repository URL and coding prompt.
    Streams the entire process via Server-Sent Events.
    """
    console.print(f"\n[bold blue]📥 New coding request received[/bold blue]")
    console.print(f"  Repository: {request.repoUrl}")
    console.print(f"  Prompt: {request.prompt[:100]}...")
    
    # Initialize managers
    manager = GeminiDaytonaManager(console)
    stream_handler = GeminiStreamingHandler(console)
    
    # Create sandbox
    sandbox_name = f"gemini-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    
    async def process_request():
        """Process the coding request with streaming"""
        sandbox = None
        sandbox_id = None
        
        try:
            # Create sandbox
            yield stream_handler._format_sse({
                "type": "status",
                "message": "Creating Daytona sandbox...",
                "timestamp": datetime.now().isoformat()
            })
            
            sandbox = await asyncio.to_thread(
                manager.create_gemini_sandbox,
                sandbox_name
            )
            
            if not sandbox:
                yield stream_handler._format_sse({
                    "type": "error",
                    "message": "Failed to create sandbox",
                    "timestamp": datetime.now().isoformat()
                })
                return
            
            sandbox_id = sandbox.id
            active_sandboxes.append(sandbox_id)
            
            yield stream_handler._format_sse({
                "type": "status",
                "message": f"Sandbox created: {sandbox_id}",
                "timestamp": datetime.now().isoformat()
            })
            
            # Create operation functions for the streaming handler
            sandbox_operations = {
                'clone': lambda url: manager.clone_repository(sandbox, url),
                'execute_gemini': lambda prompt, repo: manager.execute_gemini_prompt(sandbox, prompt, repo),
                'create_pr': lambda repo, branch, title, body: manager.create_pull_request(
                    sandbox, repo, branch, title, body
                )
            }
            
            # Stream the coding process
            async for event in stream_handler.stream_coding_process(
                sandbox_operations,
                str(request.repoUrl),
                request.prompt
            ):
                yield event
            
        except Exception as e:
            console.print(f"[red]❌ Error: {e}[/red]")
            yield stream_handler._format_sse({
                "type": "error",
                "message": str(e),
                "timestamp": datetime.now().isoformat()
            })
        
        finally:
            # Cleanup sandbox after a delay
            if sandbox_id:
                async def cleanup():
                    await asyncio.sleep(300)  # Wait 5 minutes before cleanup
                    try:
                        if sandbox_id in active_sandboxes:
                            active_sandboxes.remove(sandbox_id)
                            manager.delete_sandbox(sandbox_id)
                            console.print(f"[dim]🧹 Cleaned up sandbox: {sandbox_id}[/dim]")
                    except:
                        pass
                
                asyncio.create_task(cleanup())
    
    # Return streaming response
    return StreamingResponse(
        process_request(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"  # Disable Nginx buffering
        }
    )


# Run the application
if __name__ == "__main__":
    import uvicorn
    
    port = int(os.getenv("API_PORT", "8000"))
    host = os.getenv("API_HOST", "0.0.0.0")
    
    console.print(f"\n[bold green]🚀 Starting Gemini Coding Agent API[/bold green]")
    console.print(f"[dim]Server running at http://{host}:{port}[/dim]\n")
    
    uvicorn.run(
        app,
        host=host,
        port=port,
        log_level="info"
    )