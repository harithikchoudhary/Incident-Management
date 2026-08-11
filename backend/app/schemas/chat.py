from pydantic import BaseModel
from typing import List, Optional


class ChatMessageSchema(BaseModel):
    message_id: str
    thread_id: str
    user: str
    timestamp: str
    text: str


class ChatSpaceSchema(BaseModel):
    space_id: str
    space_name: str
    messages: List[ChatMessageSchema]


class MockChatData(BaseModel):
    spaces: List[ChatSpaceSchema]
