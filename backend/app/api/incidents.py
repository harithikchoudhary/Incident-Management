import logging
from fastapi import APIRouter, HTTPException
from typing import Optional

from app.schemas.incident import IncidentResponse, IncidentListResponse
from app.schemas.resolution import ResolutionResponse, ChatRequest, ChatResponse
from app.services.incident_service import get_incident_service
from app.services.chat_history_service import get_chat_history_service
from app.graph.incident_graph import get_incident_chat_graph

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


@router.post("/chat", response_model=ChatResponse)
def chat_about_incident(request: ChatRequest):
    try:
        service = get_incident_service()
        history_service = get_chat_history_service()
        session_id = history_service.ensure_session(request.session_id)

        all_incidents = service.get_all_incidents()

        if not all_incidents:
            response_text = "No incidents have been ingested yet. Please go to Data Ingestion and load the mock chat data first."
            history_service.record_turn(session_id, request.message, response_text)
            return ChatResponse(
                response=response_text,
                has_analysis=False,
                session_id=session_id,
            )

        chat_graph = get_incident_chat_graph()
        result = chat_graph.invoke({
            "message": request.message,
            "conversation_history": request.conversation_history or [],
            "query_analysis": None,
            "retrieval_result": None,
            "top_matches": None,
            "sources": None,
            "final_response": None,
            "error": None,
        })

        response_text = (result.get("final_response") or "").strip()
        if not response_text:
            response_text = (
                "I could not generate a grounded response right now. "
                "Try querying by incident ID, application, LOB, symptom, or error code."
            )

        # Stats answers are exact Counter-based math; the ranked top_matches used for
        # the analysis card are unrelated to that filter and would show a misleading,
        # unrelated "supporting incident" alongside a pure count/aggregate answer.
        intent = (result.get("query_analysis") or {}).get("intent")
        analysis = None
        if intent != "stats" and not _response_says_no_match(response_text):
            analysis = _build_chat_analysis(request.message, result.get("top_matches") or [])

        history_service.record_turn(
            session_id,
            request.message,
            response_text,
            analysis=analysis.model_dump() if analysis else None,
        )
        return ChatResponse(
            response=response_text,
            analysis=analysis,
            has_analysis=analysis is not None,
            session_id=session_id,
        )

    except Exception as e:
        logger.error(f"Chat failed: {e}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


_NO_MATCH_PHRASES = [
    "could not find", "couldn't find", "no previously-recorded incident",
    "no previously recorded incident", "not found in the ingested data",
    "none of the", "no match", "no relevant incident", "no record of",
]


def _response_says_no_match(response_text: str) -> bool:
    """Guards against the analysis card citing a match the answer text itself denies."""
    text_l = (response_text or "").lower()
    return any(phrase in text_l for phrase in _NO_MATCH_PHRASES)


def _build_chat_analysis(user_message: str, top_matches: list) -> Optional[ResolutionResponse]:
    if not top_matches:
        return None

    best_score = float(top_matches[0].get("score", 0.0))
    if best_score >= 0.85:
        confidence_level = "HIGH"
    elif best_score >= 0.65:
        confidence_level = "MEDIUM"
    else:
        confidence_level = "LOW"

    matched_incidents = []
    likely_root_cause = None
    recommended_resolution = []
    seen_resolution = set()
    evidence = []

    for row in top_matches[:3]:
        inc = row.get("incident") or {}
        incident_id = inc.get("incident_id")
        if not incident_id:
            continue

        matched_incidents.append({
            "incident_id": incident_id,
            "similarity": round(float(row.get("score", 0.0)), 2),
            "reason": row.get("reason", "retrieval match"),
        })

        evidence.append({
            "incident_id": incident_id,
            "source_thread_id": inc.get("source_thread_id"),
            "source_message_ids": inc.get("source_message_ids") or [],
        })

        if not likely_root_cause and inc.get("root_cause"):
            likely_root_cause = inc.get("root_cause")

        for step in inc.get("resolution") or []:
            key = step.strip().lower()
            if key and key not in seen_resolution:
                seen_resolution.add(key)
                recommended_resolution.append(step)
            if len(recommended_resolution) >= 5:
                break
        if len(recommended_resolution) >= 5:
            break

    warnings = ["Verify production conditions before applying historical resolution steps."]
    if confidence_level == "LOW":
        warnings.insert(0, "Low-confidence match. Manual investigation is recommended.")
    elif confidence_level == "MEDIUM":
        warnings.insert(0, "Medium-confidence match. Validate assumptions before action.")

    if not matched_incidents:
        return None

    return ResolutionResponse(
        incident_summary=user_message,
        likely_root_cause=likely_root_cause,
        confidence=round(best_score, 2),
        confidence_level=confidence_level,
        matched_incidents=matched_incidents,
        recommended_resolution=recommended_resolution,
        evidence=evidence,
        warnings=warnings,
    )


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
