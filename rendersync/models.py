from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class ChatMessage(BaseModel):
    role: str = Field(..., description="user|assistant|system")
    content: str

class ChatRequest(BaseModel):
    model: Optional[str] = None
    messages: List[ChatMessage]
    stream: bool = False
    options: Optional[Dict[str, Any]] = None

class ChatToken(BaseModel):
    token: str
    done: bool = False

class ChatResponse(BaseModel):
    content: str
    model: str
    total_time_ms: int
