import logging
from typing import List, Optional

from app.tools.search_incidents import search_similar_incidents
from app.tools.get_incident import get_incident
from app.tools.get_source_conversation import get_source_conversation

logger = logging.getLogger(__name__)


class IncidentRetriever:
    """Retrieves similar historical incidents using the tool interface."""

    def retrieve(self, query: str, application: Optional[str] = None, k: int = 5) -> List[dict]:
        results = search_similar_incidents(query=query, application=application, k=k)
        return results

    def get_evidence(self, incident_ids: List[str]) -> List[dict]:
        evidence = []
        for iid in incident_ids:
            conv = get_source_conversation(iid)
            if conv:
                evidence.append(conv)
        return evidence

    def get_incident_details(self, incident_id: str) -> Optional[dict]:
        return get_incident(incident_id)
