from fastapi import APIRouter
from typing import Optional

from app.services.incident_service import get_incident_service

router = APIRouter(prefix="/api/incidents", tags=["search"])


@router.get("/search")
def search_incidents(q: str, application: Optional[str] = None, environment: Optional[str] = None):
    service = get_incident_service()
    results = service.search_incidents(query=q, application=application, environment=environment)
    return {
        "results": [
            {
                "incident_id": r["incident"].incident_id,
                "application": r["incident"].application,
                "problem_summary": r["incident"].problem_summary,
                "score": round(r["score"], 3),
            }
            for r in results
        ],
        "total": len(results),
    }
