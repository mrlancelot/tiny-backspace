#!/usr/bin/env python3
"""
Tiny Backspace API - Autonomous Coding Agent Service
Main FastAPI application for streaming code changes and PR creation
"""

import os
import uuid
import asyncio
import time
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from dotenv import load_dotenv

from models import CodeRequest, CodeResponse, StreamEvent
from sse_adapter import SSEAdapter
from agent_orchestrator import AgentOrchestrator
from config import Settings

# Optional telemetry - skip if not installed
try:
    from telemetry import get_telemetry_manager
    HAS_TELEMETRY = True
except ImportError:
    HAS_TELEMETRY = False
    print("ℹ️  OpenTelemetry not installed - running without telemetry")

# Load environment variables
load_dotenv()

# Initialize settings
settings = Settings()

# Create FastAPI app
app = FastAPI(
    title="Tiny Backspace API",
    description="Autonomous coding agent that creates PRs from prompts",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
sse_adapter = SSEAdapter()
agent_orchestrator = AgentOrchestrator(settings)

# Initialize telemetry if available
if HAS_TELEMETRY:
    telemetry = get_telemetry_manager(settings)
    telemetry.instrument_app(app)
else:
    telemetry = None


async def verify_api_key(x_api_key: Optional[str] = Header(None)) -> str:
    """Verify API key if authentication is enabled"""
    if not settings.require_auth:
        return "anonymous"
    
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key required")
    
    # In production, validate against database
    if x_api_key != settings.api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return x_api_key


@app.get("/")
async def root():
    """Root endpoint with service information"""
    return {
        "service": "Tiny Backspace API",
        "version": "1.0.0",
        "status": "active",
        "endpoints": {
            "code": "/api/code",
            "health": "/health"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "sandbox_provider": settings.sandbox_provider,
        "agent": settings.agent_type
    }


@app.post("/api/code", response_class=StreamingResponse)
async def create_code_pr(
    request: CodeRequest,
    api_key: str = Depends(verify_api_key)
):
    """
    Create a pull request based on the provided prompt
    
    Streams the process via Server-Sent Events (SSE)
    """
    # Generate request ID for tracking
    request_id = str(uuid.uuid4())
    start_time = time.time()
    
    # Validate GitHub URL
    if not request.repo_url.startswith("https://github.com/"):
        raise HTTPException(
            status_code=400, 
            detail="Only public GitHub repositories are supported"
        )
    
    # Record request in telemetry
    if telemetry:
        telemetry.record_request(request.repo_url, len(request.prompt))
    
    # Create async generator for SSE streaming
    async def generate_events():
        pr_created = False
        files_changed = 0
        
        try:
            # Start with initial event
            yield sse_adapter.format_event(StreamEvent(
                type="start",
                data={
                    "request_id": request_id,
                    "repo_url": request.repo_url,
                    "prompt": request.prompt,
                    "timestamp": datetime.utcnow().isoformat(),
                    "trace_id": telemetry.create_trace_id() if telemetry else ""
                }
            ))
                
            # Execute agent orchestration
            async for event in agent_orchestrator.process_request(
                request_id=request_id,
                repo_url=request.repo_url,
                prompt=request.prompt
            ):
                # Track PR creation
                if event.type == "pr_created":
                    pr_created = True
                    files_changed = event.data.get("files_changed", 0)
                
                yield sse_adapter.format_event(event)
            
            # Send completion event
            yield sse_adapter.format_event(StreamEvent(
                type="complete",
                data={
                    "request_id": request_id,
                    "timestamp": datetime.utcnow().isoformat()
                }
            ))
            
            # Record success metrics
            if pr_created and telemetry:
                duration = time.time() - start_time
                telemetry.record_success(request.repo_url, files_changed, duration)
            
        except Exception as e:
            # Record error metrics
            if telemetry:
                duration = time.time() - start_time
                telemetry.record_error(type(e).__name__, duration)
            
            # Send error event
            yield sse_adapter.format_event(StreamEvent(
                type="error",
                data={
                    "request_id": request_id,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            ))
    
    # Return SSE response
    return StreamingResponse(
        generate_events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Request-ID": request_id
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info"
    )