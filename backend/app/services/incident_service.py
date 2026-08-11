import logging
from typing import List, Optional

from app.models.incident import Incident
from app.repositories.incident_repository import get_incident_repository
from app.services.retrieval_service import get_retrieval_service

logger = logging.getLogger(__name__)


class IncidentService:
    def __init__(self):
        self.repository = get_incident_repository()
        self.retrieval_service = get_retrieval_service()

    def create_incident(self, incident: Incident) -> Incident:
        existing = self.repository.get_by_thread_id(incident.source_thread_id)
        if existing:
            logger.info(f"Incident for thread {incident.source_thread_id} already exists, skipping")
            return existing
        self.repository.save(incident)
        try:
            self.retrieval_service.index_incident(incident)
        except Exception as e:
            logger.warning(f"Failed to index incident {incident.incident_id}, search may be limited: {e}")
        return incident

    def get_incident(self, incident_id: str) -> Optional[Incident]:
        return self.repository.get_by_id(incident_id)

    def get_all_incidents(self) -> List[Incident]:
        return self.repository.get_all()

    def search_incidents(self, query: str, application: Optional[str] = None, environment: Optional[str] = None) -> List[dict]:
        results = self.retrieval_service.search_similar(
            query=query, application=application, environment=environment
        )
        incidents = []
        for incident_id, score in results:
            incident = self.repository.get_by_id(incident_id)
            if incident:
                incidents.append({"incident": incident, "score": score})
        return incidents

    def get_conversation(self, incident_id: str) -> Optional[str]:
        incident = self.repository.get_by_id(incident_id)
        if incident:
            return incident.conversation_text
        return None


_incident_service: Optional[IncidentService] = None


def get_incident_service() -> IncidentService:
    global _incident_service
    if _incident_service is None:
        _incident_service = IncidentService()
    return _incident_service
