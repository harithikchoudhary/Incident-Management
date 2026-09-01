import logging
from typing import List, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

from app.config.settings import get_settings
from app.models.incident import Base
from app.models.chat_history import ChatSession, ChatHistoryMessage

logger = logging.getLogger(__name__)


class ChatHistoryRepository:
    def __init__(self):
        settings = get_settings()
        engine_kwargs = {}
        if settings.database_url.startswith('postgresql'):
            engine_kwargs['connect_args'] = {'options': '-csearch_path=incident,public'}
        self.engine = create_engine(settings.database_url, **engine_kwargs)

        if settings.database_url.startswith('postgresql'):
            with self.engine.connect() as conn:
                conn.execute(text("CREATE SCHEMA IF NOT EXISTS incident"))
                conn.commit()

        # Shared Base metadata also creates the incidents table if not already present.
        Base.metadata.schema = 'incident' if settings.database_url.startswith('postgresql') else None
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(bind=self.engine)

    def _get_session(self) -> Session:
        return self.SessionLocal()

    def create_session(self, title: Optional[str] = None) -> ChatSession:
        session = self._get_session()
        try:
            chat_session = ChatSession(title=title)
            session.add(chat_session)
            session.commit()
            session.refresh(chat_session)
            return chat_session
        finally:
            session.close()

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        session = self._get_session()
        try:
            return session.query(ChatSession).filter(ChatSession.session_id == session_id).first()
        finally:
            session.close()

    def touch_session(self, session_id: str) -> None:
        session = self._get_session()
        try:
            from datetime import datetime
            session.query(ChatSession).filter(ChatSession.session_id == session_id).update(
                {"updated_at": datetime.utcnow()}
            )
            session.commit()
        finally:
            session.close()

    def list_sessions(self, limit: int = 50) -> List[ChatSession]:
        session = self._get_session()
        try:
            return (
                session.query(ChatSession)
                .order_by(ChatSession.updated_at.desc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def delete_session(self, session_id: str) -> bool:
        session = self._get_session()
        try:
            session.query(ChatHistoryMessage).filter(ChatHistoryMessage.session_id == session_id).delete()
            deleted = session.query(ChatSession).filter(ChatSession.session_id == session_id).delete()
            session.commit()
            return bool(deleted)
        finally:
            session.close()

    def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
        analysis: Optional[dict] = None,
    ) -> ChatHistoryMessage:
        session = self._get_session()
        try:
            message = ChatHistoryMessage(
                session_id=session_id, role=role, content=content, analysis=analysis
            )
            session.add(message)
            session.commit()
            session.refresh(message)
            return message
        finally:
            session.close()

    def get_messages(self, session_id: str, limit: int = 200) -> List[ChatHistoryMessage]:
        session = self._get_session()
        try:
            return (
                session.query(ChatHistoryMessage)
                .filter(ChatHistoryMessage.session_id == session_id)
                .order_by(ChatHistoryMessage.created_at.asc())
                .limit(limit)
                .all()
            )
        finally:
            session.close()

    def get_last_message_preview(self, session_id: str) -> Optional[str]:
        session = self._get_session()
        try:
            row = (
                session.query(ChatHistoryMessage)
                .filter(ChatHistoryMessage.session_id == session_id)
                .order_by(ChatHistoryMessage.created_at.desc())
                .first()
            )
            return row.content if row else None
        finally:
            session.close()


_repository: Optional[ChatHistoryRepository] = None


def get_chat_history_repository() -> ChatHistoryRepository:
    global _repository
    if _repository is None:
        _repository = ChatHistoryRepository()
    return _repository
