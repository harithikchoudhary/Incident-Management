from typing import Optional
from app.repositories.incident_repository import get_incident_repository


def get_source_conversation(incident_id: str) -> Optional[dict]:
    """Retrieve the original chat conversation for an incident."""
    repo = get_incident_repository()
    incident = repo.get_by_id(incident_id)
    if not incident:
        return None
    return {
        "incident_id": incident.incident_id,
        "source_space": incident.source_space,
        "source_thread_id": incident.source_thread_id,
        "source_message_ids": incident.source_message_ids,
        "conversation_text": incident.conversation_text,
    }
