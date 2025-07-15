"""
Server-Sent Events (SSE) adapter for streaming responses
Converts internal streaming events to SSE format
"""

import json
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from datetime import datetime

from models import StreamEvent, StreamEventType, ToolEvent, AIMessageEvent, ProgressEvent
from streaming_types import ResponseType, StreamChunk


class SSEAdapter:
    """Adapter to convert streaming responses to SSE format"""
    
    def __init__(self):
        pass  # No longer need StreamingResponseHandler
        
    def format_event(self, event: StreamEvent) -> str:
        """Format a StreamEvent as SSE data"""
        # SSE format: "data: {json}\n\n"
        event_data = {
            "type": event.type,
            **event.data,
            "timestamp": event.timestamp.isoformat() if event.timestamp else datetime.utcnow().isoformat()
        }
        
        return f"data: {json.dumps(event_data)}\n\n"
    
    def format_raw_event(self, event_type: str, data: Dict[str, Any]) -> str:
        """Format raw event data as SSE"""
        event = StreamEvent(type=event_type, data=data)
        return self.format_event(event)
    
    async def convert_stream_chunk(self, chunk: StreamChunk) -> Optional[StreamEvent]:
        """Convert a StreamChunk to StreamEvent"""
        
        # Map ResponseType to StreamEventType
        type_mapping = {
            ResponseType.THINKING: StreamEventType.AI_MESSAGE,
            ResponseType.CONTENT: StreamEventType.AI_MESSAGE,
            ResponseType.CODE: StreamEventType.AI_MESSAGE,
            ResponseType.ERROR: StreamEventType.ERROR,
            ResponseType.PROGRESS: StreamEventType.PROGRESS
        }
        
        event_type = type_mapping.get(chunk.type, StreamEventType.AI_MESSAGE)
        
        # Build event data based on chunk type
        if chunk.type == ResponseType.THINKING:
            data = {
                "message": chunk.content,
                "thinking": True
            }
        elif chunk.type == ResponseType.CODE:
            data = {
                "message": f"Generated code:\n```{chunk.metadata.get('language', 'text')}\n{chunk.content}\n```",
                "code": True,
                "language": chunk.metadata.get('language', 'text')
            }
        elif chunk.type == ResponseType.ERROR:
            data = {
                "error_type": chunk.metadata.get('error_type', 'Unknown'),
                "message": chunk.content,
                "details": chunk.metadata
            }
        elif chunk.type == ResponseType.PROGRESS:
            data = {
                "stage": chunk.metadata.get('stage', 'unknown'),
                "message": chunk.content,
                "percentage": chunk.metadata.get('percentage')
            }
        else:
            data = {
                "message": chunk.content
            }
        
        return StreamEvent(type=event_type, data=data)
    
    def parse_tool_output(self, output: str) -> AsyncGenerator[StreamEvent, None]:
        """Parse tool output and generate appropriate events"""
        lines = output.strip().split('\n')
        
        for line in lines:
            if not line.strip():
                continue
            
            # Try to detect tool usage patterns
            if line.startswith("Reading file:"):
                yield StreamEvent(
                    type=StreamEventType.TOOL_READ,
                    data={"filepath": line.replace("Reading file:", "").strip()}
                )
            elif line.startswith("Editing file:"):
                yield StreamEvent(
                    type=StreamEventType.TOOL_EDIT,
                    data={"filepath": line.replace("Editing file:", "").strip()}
                )
            elif line.startswith("$ "):  # Bash command
                yield StreamEvent(
                    type=StreamEventType.TOOL_BASH,
                    data={"command": line[2:].strip()}
                )
            else:
                # Generic output
                yield StreamEvent(
                    type=StreamEventType.AI_MESSAGE,
                    data={"message": line}
                )
    
    # This method is not currently used - removed to fix import issues
    # async def stream_claude_events(
    #     self, 
    #     command: str, 
    #     sandbox_exec_func
    # ) -> AsyncGenerator[StreamEvent, None]:
    #     """Stream Claude responses as SSE events"""
    #     pass
    
    async def create_progress_event(
        self,
        stage: str,
        message: str,
        percentage: Optional[int] = None
    ) -> StreamEvent:
        """Create a progress event"""
        return StreamEvent(
            type=StreamEventType.PROGRESS,
            data={
                "stage": stage,
                "message": message,
                "percentage": percentage
            }
        )
    
    async def create_tool_event(
        self,
        tool_name: str,
        **kwargs
    ) -> StreamEvent:
        """Create a tool event"""
        event_type = f"Tool: {tool_name}"
        
        # Filter out None values
        data = {k: v for k, v in kwargs.items() if v is not None}
        
        return StreamEvent(
            type=event_type,
            data=data
        )