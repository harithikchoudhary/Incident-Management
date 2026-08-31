import logging
import re
from collections import Counter
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.schemas.incident import IncidentResponse, IncidentListResponse
from app.schemas.resolution import AnalyzeRequest, ResolutionResponse, ChatRequest, ChatResponse
from app.services.incident_service import get_incident_service
from app.services.llm_service import get_llm_service
from app.graph.incident_graph import get_incident_graph

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/incidents", tags=["incidents"])


@router.get("", response_model=IncidentListResponse)
def list_incidents(lob: Optional[str] = None):
    service = get_incident_service()
    if lob:
        incidents = service.get_incidents_by_lob(lob)
    else:
        incidents = service.get_all_incidents()
    return IncidentListResponse(
        incidents=[_incident_to_response(i) for i in incidents],
        total=len(incidents),
    )


@router.get("/lobs")
def list_lobs():
    service = get_incident_service()
    return {"lobs": service.get_lobs()}


@router.get("/search")
def search_incidents(q: str, application: Optional[str] = None, environment: Optional[str] = None):
    service = get_incident_service()
    results = service.search_incidents(query=q, application=application, environment=environment)
    return {
        "results": [
            {
                "incident": _incident_to_response(r["incident"]),
                "score": round(r["score"], 3),
            }
            for r in results
        ],
        "total": len(results),
    }


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(incident_id: str):
    service = get_incident_service()
    incident = service.get_incident(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail="Incident not found")
    return _incident_to_response(incident)


@router.get("/{incident_id}/conversation")
def get_conversation(incident_id: str):
    service = get_incident_service()
    conversation = service.get_conversation(incident_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return {"incident_id": incident_id, "conversation": conversation}


@router.post("/analyze", response_model=ResolutionResponse)
def analyze_incident(request: AnalyzeRequest):
    try:
        graph = get_incident_graph()
        result = graph.invoke({
            "description": request.description,
            "application": request.application,
            "environment": request.environment or "PROD",
            "structured_incident": None,
            "retrieved_incidents": None,
            "evidence": None,
            "recommendation": None,
            "confidence": None,
            "error": None,
        })
        recommendation = result.get("recommendation", {})
        return ResolutionResponse(**recommendation)
    except Exception as e:
        logger.error(f"Incident analysis failed: {e}")
        raise HTTPException(status_code=500, detail=f"Analysis failed: {str(e)}")


_GENERIC_TOKENS = {
    "service", "services", "system", "application", "app", "portal", "server",
    "prod", "production", "cluster", "platform", "middleware", "web", "api",
    "all", "lob", "lobs", "the", "and", "for", "with", "impacted", "loan", "unknown",
}


def _significant_tokens(value: str) -> set:
    """Meaningful lowercase tokens from an application/LOB value for matching."""
    tokens = re.findall(r"[A-Za-z0-9]+", (value or "").lower())
    return {t for t in tokens if len(t) >= 2 and t not in _GENERIC_TOKENS}


def _gather_relevant_incidents(service, all_incidents, message: str, limit: int = 8):
    """Find incidents relevant to a natural-language message using incident-ID,
    application, LOB, and semantic matching. Returns a ranked, deduped list of
    (incident, reason) tuples so answers stay grounded in ingested data."""
    msg = (message or "").lower()

    def word_in(token: str) -> bool:
        return bool(token) and re.search(r"\b" + re.escape(token) + r"\b", msg) is not None

    picked = {}

    def add(inc, rank, reason):
        if inc is None:
            return
        current = picked.get(inc.incident_id)
        if current is None or rank < current[0]:
            picked[inc.incident_id] = (rank, inc, reason)

    for inc in all_incidents:
        if word_in((inc.incident_id or "").lower()):
            add(inc, 0, "incident ID match")
    for inc in all_incidents:
        if any(word_in(t) for t in _significant_tokens(inc.application)):
            add(inc, 1, f"application match ({inc.application})")
    for inc in all_incidents:
        if inc.lob and any(word_in(t) for t in _significant_tokens(inc.lob)):
            add(inc, 2, f"LOB match ({inc.lob})")
    try:
        for r in service.search_incidents(query=message):
            add(r["incident"], 3, f"semantic match ({r['score']:.0%})")
    except Exception as e:
        logger.warning(f"Semantic search failed during chat retrieval: {e}")

    ranked = sorted(picked.values(), key=lambda x: (x[0], x[1].incident_id))
    return [(inc, reason) for _, inc, reason in ranked[:limit]]


@router.post("/chat", response_model=ChatResponse)
def chat_about_incident(request: ChatRequest):
    try:
        llm = get_llm_service()
        service = get_incident_service()

        all_incidents = service.get_all_incidents()

        if not all_incidents:
            return ChatResponse(
                response="No incidents have been ingested yet. Please go to Data Ingestion and load the mock chat data first.",
                has_analysis=False,
            )

        # Retrieve incidents relevant to the message (ID, application, LOB, semantic)
        relevant = _gather_relevant_incidents(service, all_incidents, request.message)

        # Build context ONLY from ingested incidents
        retrieved_context = ""
        if relevant:
            retrieved_context = "RETRIEVED HISTORICAL INCIDENTS (from ingested data):\n\n"
            for i, (inc, reason) in enumerate(relevant, 1):
                retrieved_context += f"--- Incident {i} ({reason}) ---\n"
                retrieved_context += f"ID: {inc.incident_id}\n"
                retrieved_context += f"Application: {inc.application}\n"
                retrieved_context += f"LOB: {inc.lob or 'Unspecified'}\n"
                retrieved_context += f"Environment: {inc.environment}\n"
                retrieved_context += f"Severity: {inc.severity}\n"
                retrieved_context += f"Status: {inc.status}\n"
                retrieved_context += f"Problem: {inc.problem_summary}\n"
                if inc.issue:
                    retrieved_context += f"Issue: {inc.issue}\n"
                if inc.identified_time:
                    retrieved_context += f"Identified at: {inc.identified_time}\n"
                retrieved_context += f"Symptoms: {', '.join(inc.symptoms or [])}\n"
                retrieved_context += f"Error Codes: {', '.join(inc.error_codes or [])}\n"
                if inc.impacted_users:
                    retrieved_context += f"Impacted users: {inc.impacted_users}\n"
                if inc.failed_cases:
                    retrieved_context += f"Stuck/failed cases: {inc.failed_cases}\n"
                if inc.business_impact:
                    retrieved_context += f"Business impact: {inc.business_impact}\n"
                retrieved_context += f"Root Cause: {inc.root_cause or 'Unknown'}\n"
                retrieved_context += f"Resolution: {'; '.join(inc.resolution or [])}\n\n"

        # Aggregate breakdowns so the assistant can answer statistical questions
        def _fmt_counts(counter):
            return ', '.join(f"{name} ({count})" for name, count in counter.most_common()) or "none"

        lob_counts = Counter((i.lob or "Unspecified").strip() for i in all_incidents)
        severity_counts = Counter((i.severity or "UNKNOWN") for i in all_incidents)
        app_counts = Counter((i.application or "Unknown") for i in all_incidents)
        status_counts = Counter((i.status or "UNKNOWN") for i in all_incidents)

        stats_context = "\nINGESTED DATA SUMMARY (all incidents):\n"
        stats_context += f"Total incidents: {len(all_incidents)}\n"
        stats_context += f"By LOB (most to least): {_fmt_counts(lob_counts)}\n"
        stats_context += f"By Severity: {_fmt_counts(severity_counts)}\n"
        stats_context += f"By Application: {_fmt_counts(app_counts)}\n"
        stats_context += f"By Status: {_fmt_counts(status_counts)}\n"

        history_context = ""
        if request.conversation_history:
            recent = request.conversation_history[-6:]
            history_context = "\nConversation history:\n"
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_context += f"{role}: {content}\n"

        # Check if this looks like a new incident report — run full analysis
        is_incident = any(keyword in request.message.lower() for keyword in [
            "500", "503", "error", "down", "failing", "timeout", "crash",
            "connection pool", "memory", "cpu", "spike", "lag", "deadlock",
            "certificate", "expired", "deployment", "dns", "redis", "kafka",
        ])

        prompt = f"""You are an AI incident management assistant for an internal incident knowledge base. Reply conversationally and helpfully, but ground EVERY factual statement in the ingested incident data below. Do NOT use outside or general knowledge. Do NOT invent incidents, IDs, root causes, numbers, or resolutions.

You can help the user:
- Look up a specific incident by ID
- Find incidents by application, LOB, severity, or symptom
- Explain what happened, the root cause, and how it was resolved (always citing incident IDs)
- Answer statistical questions using the summary
- Recommend resolution steps for a new problem based ONLY on similar past incidents

{stats_context}
{retrieved_context}
{history_context}
User's message: "{request.message}"

RULES:
1. Use ONLY the data above. If a requested detail isn't present, state what IS known and note the rest isn't in the ingested data.
2. When describing an incident, always cite its incident ID.
3. For statistical/aggregate questions, use the INGESTED DATA SUMMARY.
4. For a new problem the user reports, recommend steps only from similar past incidents and cite them.
5. If no relevant incident is found, do not give a generic refusal - briefly tell the user what you can help with and mention the available applications and LOBs from the summary.
6. Be concise, specific, and conversational."""

        analysis = None
        if is_incident and relevant:
            # Run the graph for structured analysis
            try:
                graph = get_incident_graph()
                result = graph.invoke({
                    "description": request.message,
                    "application": None,
                    "environment": "PROD",
                    "structured_incident": None,
                    "retrieved_incidents": None,
                    "evidence": None,
                    "recommendation": None,
                    "confidence": None,
                    "error": None,
                })
                recommendation = result.get("recommendation", {})
                if recommendation:
                    analysis = ResolutionResponse(**recommendation)
            except Exception as e:
                logger.warning(f"Graph analysis failed, using search results only: {e}")

        response_text = llm.generate(prompt)
        return ChatResponse(response=response_text, analysis=analysis, has_analysis=analysis is not None)

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


def _incident_to_response(incident) -> IncidentResponse:
    return IncidentResponse(
        incident_id=incident.incident_id,
        application=incident.application,
        environment=incident.environment,
        severity=incident.severity,
        problem_summary=incident.problem_summary,
        symptoms=incident.symptoms or [],
        error_codes=incident.error_codes or [],
        root_cause=incident.root_cause,
        resolution=incident.resolution or [],
        status=incident.status,
        lob=incident.lob,
        issue=incident.issue,
        identified_time=incident.identified_time,
        upstream_downstream=incident.upstream_downstream,
        impacted_users=incident.impacted_users,
        failed_cases=incident.failed_cases,
        business_impact=incident.business_impact,
        created_at=incident.created_at,
        resolved_at=incident.resolved_at,
        source_space=incident.source_space,
        source_thread_id=incident.source_thread_id,
        source_message_ids=incident.source_message_ids or [],
        conversation_text=incident.conversation_text,
    )
