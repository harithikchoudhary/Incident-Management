import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, JSON, String, Text

from app.models.incident import Base


def _new_uuid() -> str:
    return str(uuid.uuid4())


class ChatSession(Base):
    """A single chat conversation, identified by a UUID session_id."""

    __tablename__ = "chat_sessions"

    session_id = Column(String, primary_key=True, default=_new_uuid)
    title = Column(String, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class ChatHistoryMessage(Base):
    """One user or assistant turn within a chat session."""

    __tablename__ = "chat_history_messages"

    message_id = Column(String, primary_key=True, default=_new_uuid)
    # No FK constraint (consistent with Incident.source_thread_id elsewhere) - keeps
    # schema-qualified cross-table references simple across DB backends.
    session_id = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    analysis = Column(JSON, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, index=True)
