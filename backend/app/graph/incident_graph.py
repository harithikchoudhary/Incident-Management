"""LangGraph-based incident analysis workflow."""
import logging
from typing import TypedDict, List, Optional, Any

from langgraph.graph import StateGraph, END

from app.agents.incident_analyzer import IncidentAnalyzer
from app.agents.incident_retriever import IncidentRetriever
from app.agents.resolution_agent import ResolutionAgent

logger = logging.getLogger(__name__)


class IncidentGraphState(TypedDict):
    description: str
    application: Optional[str]
    environment: Optional[str]
    structured_incident: Optional[dict]
    retrieved_incidents: Optional[List[dict]]
    evidence: Optional[List[dict]]
    recommendation: Optional[dict]
    confidence: Optional[float]
    error: Optional[str]


def incident_analyzer_node(state: IncidentGraphState) -> dict:
    """Analyze and structure the incoming incident."""
    try:
        analyzer = IncidentAnalyzer()
        structured = analyzer.analyze(
            description=state["description"],
            application=state.get("application"),
            environment=state.get("environment"),
        )
        return {"structured_incident": structured}
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return {"error": str(e)}


def incident_retriever_node(state: IncidentGraphState) -> dict:
    """Retrieve similar historical incidents."""
    try:
        if state.get("error"):
            return {}
        retriever = IncidentRetriever()
        structured = state["structured_incident"]
        results = retriever.retrieve(
            query=structured["search_query"],
            application=structured.get("application"),
        )
        return {"retrieved_incidents": results}
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return {"retrieved_incidents": [], "error": str(e)}


def evidence_retriever_node(state: IncidentGraphState) -> dict:
    """Retrieve source conversations for matched incidents."""
    try:
        if state.get("error"):
            return {}
        retriever = IncidentRetriever()
        incident_ids = [m["incident_id"] for m in (state.get("retrieved_incidents") or [])[:3]]
        evidence = retriever.get_evidence(incident_ids)
        return {"evidence": evidence}
    except Exception as e:
        logger.error(f"Evidence retrieval failed: {e}")
        return {"evidence": [], "error": str(e)}


def resolution_agent_node(state: IncidentGraphState) -> dict:
    """Generate resolution recommendation from evidence."""
    try:
        agent = ResolutionAgent()
        result = agent.generate_resolution(
            incident_summary=state.get("structured_incident", {}),
            matched_incidents=state.get("retrieved_incidents", []),
            evidence=state.get("evidence", []),
        )
        return {
            "recommendation": result,
            "confidence": result.get("confidence", 0.0),
        }
    except Exception as e:
        logger.error(f"Resolution generation failed: {e}")
        return {"error": str(e)}


def response_formatter_node(state: IncidentGraphState) -> dict:
    """Format the final response."""
    if state.get("error") and not state.get("recommendation"):
        return {
            "recommendation": {
                "incident_summary": state.get("description", ""),
                "likely_root_cause": None,
                "confidence": 0.0,
                "confidence_level": "LOW",
                "matched_incidents": [],
                "recommended_resolution": [],
                "evidence": [],
                "warnings": [f"Analysis encountered an error: {state.get('error')}"],
            }
        }
    return {}


def build_incident_graph() -> StateGraph:
    """Build the LangGraph workflow for incident analysis."""
    workflow = StateGraph(IncidentGraphState)

    workflow.add_node("incident_analyzer", incident_analyzer_node)
    workflow.add_node("incident_retriever", incident_retriever_node)
    workflow.add_node("evidence_retriever", evidence_retriever_node)
    workflow.add_node("resolution_agent", resolution_agent_node)
    workflow.add_node("response_formatter", response_formatter_node)

    workflow.set_entry_point("incident_analyzer")
    workflow.add_edge("incident_analyzer", "incident_retriever")
    workflow.add_edge("incident_retriever", "evidence_retriever")
    workflow.add_edge("evidence_retriever", "resolution_agent")
    workflow.add_edge("resolution_agent", "response_formatter")
    workflow.add_edge("response_formatter", END)

    return workflow.compile()


# Singleton compiled graph
_graph = None


def get_incident_graph():
    global _graph
    if _graph is None:
        _graph = build_incident_graph()
    return _graph
