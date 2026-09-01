from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


class ChatSessionSummary(BaseModel):
    session_id: str
    title: Optional[str] = None
    preview: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ChatSessionListResponse(BaseModel):
    sessions: List[ChatSessionSummary]


class ChatHistoryMessageSchema(BaseModel):
    role: str
    content: str
    analysis: Optional[dict] = None
    created_at: datetime


class ChatSessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[ChatHistoryMessageSchema]


class NewChatSessionResponse(BaseModel):
    session_id: str
