import json
import logging
from abc import ABC, abstractmethod
from typing import List, Optional

from app.models.chat_message import ChatMessage, ChatThread, ChatSpace
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class ChatSource(ABC):
    """Interface for chat data sources. Implement this to add new sources."""

    @abstractmethod
    def get_spaces(self) -> List[ChatSpace]:
        pass

    @abstractmethod
    def get_messages(self, space_id: str) -> List[ChatMessage]:
        pass

    @abstractmethod
    def get_threads(self, space_id: str) -> List[ChatThread]:
        pass


class MockChatSource(ChatSource):
    """Reads chat data from a local JSON file."""

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or get_settings().mock_chat_path

    def _load_data(self) -> dict:
        with open(self.file_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_spaces(self) -> List[ChatSpace]:
        data = self._load_data()
        spaces = []
        for space_data in data.get("spaces", []):
            messages = [
                ChatMessage(
                    message_id=m["message_id"],
                    thread_id=m["thread_id"],
                    user=m["user"],
                    timestamp=m["timestamp"],
                    text=m["text"],
                )
                for m in space_data.get("messages", [])
            ]
            spaces.append(
                ChatSpace(
                    space_id=space_data["space_id"],
                    space_name=space_data["space_name"],
                    messages=messages,
                )
            )
        return spaces

    def get_messages(self, space_id: str) -> List[ChatMessage]:
        spaces = self.get_spaces()
        for space in spaces:
            if space.space_id == space_id:
                return space.messages
        return []

    def get_threads(self, space_id: Optional[str] = None) -> List[ChatThread]:
        data = self._load_data()
        threads = {}
        for space_data in data.get("spaces", []):
            if space_id and space_data["space_id"] != space_id:
                continue
            for m in space_data.get("messages", []):
                tid = m["thread_id"]
                if tid not in threads:
                    threads[tid] = ChatThread(
                        thread_id=tid,
                        space_id=space_data["space_id"],
                        space_name=space_data["space_name"],
                    )
                threads[tid].messages.append(
                    ChatMessage(
                        message_id=m["message_id"],
                        thread_id=m["thread_id"],
                        user=m["user"],
                        timestamp=m["timestamp"],
                        text=m["text"],
                    )
                )
        return list(threads.values())
