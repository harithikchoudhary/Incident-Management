import logging
from fastapi import APIRouter, HTTPException

from app.schemas.chat_history import (
    ChatSessionListResponse,
    ChatSessionMessagesResponse,
    NewChatSessionResponse,
)
from app.services.chat_history_service import get_chat_history_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat-history"])


@router.post("/sessions", response_model=NewChatSessionResponse)
def create_session():
    service = get_chat_history_service()
    session_id = service.ensure_session(None)
    return NewChatSessionResponse(session_id=session_id)


@router.get("/sessions", response_model=ChatSessionListResponse)
def list_sessions():
    service = get_chat_history_service()
    return ChatSessionListResponse(sessions=service.list_sessions())


@router.get("/sessions/{session_id}/messages", response_model=ChatSessionMessagesResponse)
def get_session_messages(session_id: str):
    service = get_chat_history_service()
    messages = service.get_full_messages(session_id)
    return ChatSessionMessagesResponse(session_id=session_id, messages=messages)


@router.delete("/sessions/{session_id}")
def delete_session(session_id: str):
    service = get_chat_history_service()
    deleted = service.delete_session(session_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Session not found")
    return {"deleted": True}
