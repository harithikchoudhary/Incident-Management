import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import incidents, ingestion
from app.config.settings import get_settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Incident Management Platform",
    description="AI-powered Incident Management with historical retrieval and resolution recommendations",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(incidents.router)
app.include_router(ingestion.router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/api/dashboard")
def dashboard():
    from app.repositories.incident_repository import get_incident_repository
    repo = get_incident_repository()
    all_incidents = repo.get_all()
    
    applications = set()
    root_causes = {}
    high_severity = 0
    resolved = 0

    for inc in all_incidents:
        applications.add(inc.application)
        if inc.severity in ("HIGH", "CRITICAL"):
            high_severity += 1
        if inc.status == "RESOLVED":
            resolved += 1
        if inc.root_cause:
            rc = inc.root_cause[:50]
            root_causes[rc] = root_causes.get(rc, 0) + 1

    top_root_causes = sorted(root_causes.items(), key=lambda x: x[1], reverse=True)[:5]

    return {
        "total_incidents": len(all_incidents),
        "resolved_incidents": resolved,
        "applications_affected": list(applications),
        "high_severity_count": high_severity,
        "top_root_causes": [{"cause": c, "count": n} for c, n in top_root_causes],
    }
