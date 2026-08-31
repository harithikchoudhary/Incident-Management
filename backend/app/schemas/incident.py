from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime


class IncidentBase(BaseModel):
    application: str
    environment: str
    severity: str
    problem_summary: str
    symptoms: List[str] = []
    error_codes: List[str] = []
    root_cause: Optional[str] = None
    resolution: List[str] = []
    status: str = "RESOLVED"
    lob: Optional[str] = None
    issue: Optional[str] = None
    identified_time: Optional[str] = None
    upstream_downstream: Optional[str] = None
    impacted_users: Optional[str] = None
    failed_cases: Optional[str] = None
    business_impact: Optional[str] = None


class IncidentCreate(IncidentBase):
    incident_id: str
    created_at: datetime
    resolved_at: Optional[datetime] = None
    source_space: Optional[str] = None
    source_thread_id: Optional[str] = None
    source_message_ids: List[str] = []
    conversation_text: Optional[str] = None


class IncidentResponse(IncidentCreate):
    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    incidents: List[IncidentResponse]
    total: int
