from pydantic import BaseModel
from typing import List, Optional


class AnalyzeRequest(BaseModel):
    description: str
    application: Optional[str] = None
    environment: Optional[str] = "PROD"
    severity: Optional[str] = None


class MatchedIncident(BaseModel):
    incident_id: str
    similarity: float
    reason: str


class Evidence(BaseModel):
    incident_id: str
    source_thread_id: Optional[str] = None
    source_message_ids: List[str] = []


class ResolutionResponse(BaseModel):
    incident_summary: str
    likely_root_cause: Optional[str] = None
    confidence: float
    confidence_level: str
    matched_incidents: List[MatchedIncident] = []
    recommended_resolution: List[str] = []
    evidence: List[Evidence] = []
    warnings: List[str] = []


class IngestionResponse(BaseModel):
    total_threads: int
    incidents_extracted: int
    successful: int
    failed: int


class ChatRequest(BaseModel):
    message: str
    conversation_history: List[dict] = []


class ChatResponse(BaseModel):
    response: str
    analysis: Optional[ResolutionResponse] = None
    has_analysis: bool = False
