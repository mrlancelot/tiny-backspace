"""
Pydantic models for request/response validation
"""

from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, HttpUrl, validator
from datetime import datetime


class CodeRequest(BaseModel):
    """Request model for code generation endpoint"""
    repo_url: str = Field(
        ..., 
        description="Public GitHub repository URL",
        example="https://github.com/example/simple-api"
    )
    prompt: str = Field(
        ..., 
        description="Natural language description of code changes",
        example="Add input validation to all POST endpoints"
    )
    
    @validator('repo_url')
    def validate_github_url(cls, v):
        """Ensure URL is a valid GitHub repository"""
        if not v.startswith('https://github.com/'):
            raise ValueError('Only GitHub repositories are supported')
        
        # Basic validation for repo format
        parts = v.replace('https://github.com/', '').split('/')
        if len(parts) < 2 or not all(parts[:2]):
            raise ValueError('Invalid GitHub repository URL format')
        
        return v
    
    @validator('prompt')
    def validate_prompt(cls, v):
        """Validate prompt is not empty and reasonable length"""
        if not v.strip():
            raise ValueError('Prompt cannot be empty')
        
        if len(v) > 1000:
            raise ValueError('Prompt too long (max 1000 characters)')
        
        return v.strip()


class CodeResponse(BaseModel):
    """Response model for successful PR creation"""
    request_id: str = Field(..., description="Unique request identifier")
    pr_url: str = Field(..., description="Created pull request URL")
    branch_name: str = Field(..., description="Created branch name")
    files_changed: int = Field(..., description="Number of files modified")
    summary: str = Field(..., description="Summary of changes made")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class StreamEventType(str):
    """Enumeration of stream event types"""
    START = "start"
    TOOL_READ = "Tool: Read"
    TOOL_EDIT = "Tool: Edit"
    TOOL_BASH = "Tool: Bash"
    AI_MESSAGE = "AI Message"
    PROGRESS = "progress"
    ERROR = "error"
    COMPLETE = "complete"


class StreamEvent(BaseModel):
    """Model for Server-Sent Event data"""
    type: str = Field(..., description="Event type")
    data: Dict[str, Any] = Field(..., description="Event payload")
    timestamp: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    class Config:
        use_enum_values = True


class ToolEvent(BaseModel):
    """Model for tool execution events"""
    tool_name: Literal["Read", "Edit", "Bash"]
    filepath: Optional[str] = None
    command: Optional[str] = None
    old_str: Optional[str] = None
    new_str: Optional[str] = None
    output: Optional[str] = None
    error: Optional[str] = None


class ProgressEvent(BaseModel):
    """Model for progress update events"""
    stage: Literal["cloning", "analyzing", "coding", "committing", "pushing", "pr_creation"]
    message: str
    percentage: Optional[int] = Field(None, ge=0, le=100)


class AIMessageEvent(BaseModel):
    """Model for AI agent messages"""
    message: str
    thinking: Optional[bool] = False
    
    
class ErrorEvent(BaseModel):
    """Model for error events"""
    error_type: str
    message: str
    details: Optional[Dict[str, Any]] = None
    recoverable: bool = False