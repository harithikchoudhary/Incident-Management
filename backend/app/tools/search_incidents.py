from typing import List, Optional
from app.services.retrieval_service import get_retrieval_service


def search_similar_incidents(query: str, application: Optional[str] = None, k: int = 5) -> List[dict]:
    """Search for incidents similar to the given query."""
    service = get_retrieval_service()
    results = service.search_similar(query=query, application=application, k=k)

    from app.repositories.incident_repository import get_incident_repository
    repo = get_incident_repository()

    incidents = []
    for incident_id, score in results:
        incident = repo.get_by_id(incident_id)
        if incident:
            incidents.append({
                "incident_id": incident.incident_id,
                "application": incident.application,
                "problem_summary": incident.problem_summary,
                "root_cause": incident.root_cause,
                "resolution": incident.resolution,
                "similarity": score,
            })
    return incidents
