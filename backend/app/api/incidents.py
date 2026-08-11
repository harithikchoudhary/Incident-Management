import logging
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
def list_incidents():
    service = get_incident_service()
    incidents = service.get_all_incidents()
    return IncidentListResponse(
        incidents=[_incident_to_response(i) for i in incidents],
        total=len(incidents),
    )


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


@router.post("/chat", response_model=ChatResponse)
def chat_about_incident(request: ChatRequest):
    try:
        llm = get_llm_service()
        service = get_incident_service()

        # Always search ingested data first
        search_results = service.search_incidents(query=request.message)
        all_incidents = service.get_all_incidents()

        if not all_incidents:
            return ChatResponse(
                response="No incidents have been ingested yet. Please go to Data Ingestion and load the mock chat data first.",
                has_analysis=False,
            )

        # Build context ONLY from ingested incidents
        retrieved_context = ""
        matched_ids = []
        if search_results:
            retrieved_context = "RETRIEVED HISTORICAL INCIDENTS (from ingested data):\n\n"
            for i, r in enumerate(search_results[:5], 1):
                inc = r["incident"]
                score = r["score"]
                matched_ids.append(inc.incident_id)
                retrieved_context += f"--- Incident {i} (Relevance: {score:.0%}) ---\n"
                retrieved_context += f"ID: {inc.incident_id}\n"
                retrieved_context += f"Application: {inc.application}\n"
                retrieved_context += f"Environment: {inc.environment}\n"
                retrieved_context += f"Severity: {inc.severity}\n"
                retrieved_context += f"Problem: {inc.problem_summary}\n"
                retrieved_context += f"Symptoms: {', '.join(inc.symptoms or [])}\n"
                retrieved_context += f"Error Codes: {', '.join(inc.error_codes or [])}\n"
                retrieved_context += f"Root Cause: {inc.root_cause or 'Unknown'}\n"
                retrieved_context += f"Resolution: {'; '.join(inc.resolution or [])}\n"
                retrieved_context += f"Status: {inc.status}\n\n"

        # Summary of all ingested data for stats questions
        apps = sorted(set(i.application for i in all_incidents))
        stats_context = f"\nINGESTED DATA SUMMARY:\n"
        stats_context += f"Total incidents: {len(all_incidents)}\n"
        stats_context += f"Applications: {', '.join(apps)}\n"
        stats_context += f"Resolved: {sum(1 for i in all_incidents if i.status == 'RESOLVED')}\n"

        history_context = ""
        if request.conversation_history:
            recent = request.conversation_history[-6:]
            history_context = "\nConversation history:\n"
            for msg in recent:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                history_context += f"{role}: {content}\n"

        prompt = f"""You are an AI incident management assistant. You must ONLY answer based on the ingested historical incident data provided below. Do NOT use any general knowledge. Do NOT invent or fabricate information.

If the user's question cannot be answered from the provided data, say: "I don't have information about that in the ingested incident data."

If the user describes a new incident, find the most similar historical incidents from the data below and recommend resolution steps ONLY from those historical incidents.

{stats_context}
{retrieved_context}
{history_context}
User's message: "{request.message}"

RULES:
1. ONLY use information from the retrieved incidents above
2. NEVER make up solutions or root causes not present in the data
3. Always cite which incident ID your answer is based on
4. If no relevant incidents are found, say so clearly
5. Be concise and actionable"""

        # Check if this looks like a new incident report — run full analysis
        is_incident = any(keyword in request.message.lower() for keyword in [
            "500", "503", "error", "down", "failing", "timeout", "crash",
            "connection pool", "memory", "cpu", "spike", "lag", "deadlock",
            "certificate", "expired", "deployment", "dns", "redis", "kafka",
        ])

        analysis = None
        if is_incident and search_results:
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
        created_at=incident.created_at,
        resolved_at=incident.resolved_at,
        source_space=incident.source_space,
        source_thread_id=incident.source_thread_id,
        source_message_ids=incident.source_message_ids or [],
        conversation_text=incident.conversation_text,
    )
