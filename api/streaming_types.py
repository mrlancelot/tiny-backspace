"""
Streaming types for API
"""

from enum import Enum
from dataclasses import dataclass
from typing import Optional, Dict, Any


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