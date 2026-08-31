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
    """Reads chat data from a local JSON file. Supports both original_incident_data.json and mock_google_chat.json formats."""

    def __init__(self, file_path: Optional[str] = None):
        self.file_path = file_path or get_settings().mock_chat_path

    def _load_data(self):
        with open(self.file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Check if it's the original_incident_data.json format (list) or standard format (dict)
        if isinstance(data, list):
            logger.info("Detected original_incident_data.json format")
            return self._convert_original_format(data)
        return data

    def _convert_original_format(self, incidents_data: list) -> dict:
        """Convert original_incident_data.json format to standard ChatSpace format."""
        spaces = []
        space_id = "incident-space"
        space_name = "Incident Management"
        
        for incident in incidents_data:
            incident_id = incident.get("incident_id", "unknown")
            
            # Process initial_thread
            if "initial_thread" in incident:
                thread_id = f"thread-{incident_id}"
                messages = self._extract_messages_from_thread(
                    incident["initial_thread"], 
                    thread_id, 
                    incident_id
                )
                
                # Add messages to space
                if not spaces:
                    spaces.append({
                        "space_id": space_id,
                        "space_name": space_name,
                        "messages": []
                    })
                spaces[0]["messages"].extend(messages)
            
            # Process reopened_thread if exists
            if "reopened_thread" in incident:
                thread_id = f"thread-{incident_id}-reopened"
                messages = self._extract_messages_from_thread(
                    incident["reopened_thread"], 
                    thread_id, 
                    incident_id
                )
                spaces[0]["messages"].extend(messages)
            
            # Process thread format (for other incident types)
            elif "thread" in incident:
                thread_id = f"thread-{incident_id}"
                messages = self._extract_messages_from_thread(
                    incident["thread"], 
                    thread_id, 
                    incident_id
                )
                if not spaces:
                    spaces.append({
                        "space_id": space_id,
                        "space_name": space_name,
                        "messages": []
                    })
                spaces[0]["messages"].extend(messages)
        
        return {"spaces": spaces}

    def _extract_messages_from_thread(self, thread_data: dict, thread_id: str, incident_id: str) -> List[dict]:
        """Extract messages from a thread in original_incident_data.json format."""
        messages = []
        msg_counter = 0
        
        # Process original_message
        if "original_message" in thread_data:
            original = thread_data["original_message"]
            messages.append({
                "message_id": f"msg-{incident_id}-{msg_counter}",
                "thread_id": thread_id,
                "user": original.get("author", "Unknown"),
                "timestamp": original.get("timestamp", ""),
                "text": original.get("text", "")
            })
            msg_counter += 1
        
        # Process replies
        if "replies" in thread_data:
            for reply in thread_data["replies"]:
                messages.append({
                    "message_id": f"msg-{incident_id}-{msg_counter}",
                    "thread_id": thread_id,
                    "user": reply.get("author", "Unknown"),
                    "timestamp": reply.get("timestamp", ""),
                    "text": reply.get("text", "")
                })
                msg_counter += 1
        
        return messages

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
