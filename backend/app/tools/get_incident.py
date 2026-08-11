from typing import Optional
from app.repositories.incident_repository import get_incident_repository


def get_incident(incident_id: str) -> Optional[dict]:
    """Get a specific incident by ID."""
    repo = get_incident_repository()
    incident = repo.get_by_id(incident_id)
    if not incident:
        return None
    return {
        "incident_id": incident.incident_id,
        "application": incident.application,
        "environment": incident.environment,
        "severity": incident.severity,
        "problem_summary": incident.problem_summary,
        "symptoms": incident.symptoms,
        "error_codes": incident.error_codes,
        "root_cause": incident.root_cause,
        "resolution": incident.resolution,
        "status": incident.status,
        "created_at": str(incident.created_at),
        "resolved_at": str(incident.resolved_at) if incident.resolved_at else None,
    }
