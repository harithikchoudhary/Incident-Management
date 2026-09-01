import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.models.chat_history import ChatSession
from app.repositories.chat_history_repository import ChatHistoryRepository, get_chat_history_repository

logger = logging.getLogger(__name__)


class ChatHistoryService:
    def __init__(self):
        self.repository: ChatHistoryRepository = get_chat_history_repository()

    def ensure_session(self, session_id: Optional[str]) -> str:
        """Return a valid session_id, creating a new session if none was given or it's unknown."""
        if session_id:
            existing = self.repository.get_session(session_id)
            if existing:
                return existing.session_id
            logger.info(f"Unknown chat session_id {session_id}, creating a new session")
        return self.repository.create_session().session_id

    def record_turn(
        self,
        session_id: str,
        user_message: str,
        assistant_response: str,
        analysis: Optional[dict] = None,
    ) -> None:
        self.repository.add_message(session_id, "user", user_message)
        self.repository.add_message(session_id, "assistant", assistant_response, analysis=analysis)
        # First user message becomes the session title for the history list.
        existing = self.repository.get_session(session_id)
        if existing and not existing.title:
            self._set_title(session_id, user_message[:80])
        else:
            self.repository.touch_session(session_id)

    def _set_title(self, session_id: str, title: str) -> None:
        session = self.repository._get_session()
        try:
            session.query(ChatSession).filter(ChatSession.session_id == session_id).update(
                {"title": title, "updated_at": datetime.utcnow()}
            )
            session.commit()
        finally:
            session.close()

    def get_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        messages = self.repository.get_messages(session_id, limit=limit)
        return [{"role": m.role, "content": m.content} for m in messages]

    def get_full_messages(self, session_id: str, limit: int = 200) -> List[Dict]:
        messages = self.repository.get_messages(session_id, limit=limit)
        return [
            {
                "role": m.role,
                "content": m.content,
                "analysis": m.analysis,
                "created_at": m.created_at,
            }
            for m in messages
        ]

    def list_sessions(self, limit: int = 50) -> List[Dict]:
        sessions = self.repository.list_sessions(limit=limit)
        result = []
        for s in sessions:
            preview = s.title or self.repository.get_last_message_preview(s.session_id)
            result.append({
                "session_id": s.session_id,
                "title": s.title,
                "preview": preview,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            })
        return result

    def delete_session(self, session_id: str) -> bool:
        return self.repository.delete_session(session_id)


_service: Optional[ChatHistoryService] = None


def get_chat_history_service() -> ChatHistoryService:
    global _service
    if _service is None:
        _service = ChatHistoryService()
    return _service
