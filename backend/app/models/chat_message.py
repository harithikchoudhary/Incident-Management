from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ChatMessage:
    message_id: str
    thread_id: str
    user: str
    timestamp: str
    text: str


@dataclass
class ChatThread:
    thread_id: str
    space_id: str
    space_name: str
    messages: List[ChatMessage] = field(default_factory=list)


@dataclass
class ChatSpace:
    space_id: str
    space_name: str
    messages: List[ChatMessage] = field(default_factory=list)
