"""LangGraph-based incident chat workflow."""
import logging
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from app.agents.chat_incident_matcher import ChatIncidentMatcherAgent
from app.agents.chat_response_composer import ChatResponseComposerAgent
from app.services.incident_service import get_incident_service

logger = logging.getLogger(__name__)


class ChatGraphState(TypedDict):
    message: str
    conversation_history: Optional[List[dict]]
    query_analysis: Optional[Dict[str, Any]]
    retrieval_result: Optional[Dict[str, Any]]
    top_matches: Optional[List[Dict[str, Any]]]
    sources: Optional[List[str]]
    final_response: Optional[str]
    error: Optional[str]


def chat_query_analyzer_node(state: ChatGraphState) -> dict:
    """Placeholder node - the regex-based ChatQueryAnalyzerAgent is disabled for now
    (to be replaced with a smarter/LLM-based analyzer later). Passes the raw message
    straight through so the rest of the graph (semantic retrieval + LLM composition)
    keeps working without any keyword/ID pre-parsing."""
    message = state.get("message", "")
    return {
        "query_analysis": {
            "message": message,
            "intent": "general",
            "mentioned_incident_ids": [],
            "carried_incident_ids": [],
            "is_followup": False,
            "tokens": [],
            "use_top_k_embeddings": 5,
            "conversation_turns": len(state.get("conversation_history") or []),
        }
    }


def chat_incident_matcher_node(state: ChatGraphState) -> dict:
    """Retrieve and rank top matching incidents from embeddings + deterministic signals."""
    try:
        if state.get("error"):
            return {}
        service = get_incident_service()
        matcher = ChatIncidentMatcherAgent(service)
        retrieval = matcher.retrieve(query_analysis=state.get("query_analysis") or {}, top_k=5)
        return {
            "retrieval_result": retrieval,
            "top_matches": retrieval.get("top_matches", []),
        }
    except Exception as e:
        logger.error(f"Chat incident matching failed: {e}")
        return {
            "retrieval_result": {"all_incidents": [], "top_matches": []},
            "top_matches": [],
            "error": str(e),
        }


def chat_response_composer_node(state: ChatGraphState) -> dict:
    """Compose grounded answer with source-of-truth references."""
    try:
        if state.get("error"):
            return {
                "final_response": (
                    "I could not complete retrieval because of an internal error. "
                    "Please retry your query with an incident ID, application, LOB, or error code."
                )
            }

        composer = ChatResponseComposerAgent()
        result = composer.compose(
            query_analysis=state.get("query_analysis") or {},
            retrieval_result=state.get("retrieval_result") or {"all_incidents": [], "top_matches": []},
            conversation_history=state.get("conversation_history") or [],
        )
        return {
            "final_response": result.get("response", ""),
            "sources": result.get("sources", []),
        }
    except Exception as e:
        logger.error(f"Chat response composition failed: {e}")
        return {
            "final_response": "I could not generate a grounded response at the moment. Please try again.",
            "sources": [],
            "error": str(e),
        }


def build_incident_chat_graph() -> StateGraph:
    """Build the 3-agent LangGraph workflow for incident chat."""
    workflow = StateGraph(ChatGraphState)

    workflow.add_node("query_analyzer", chat_query_analyzer_node)
    workflow.add_node("incident_matcher", chat_incident_matcher_node)
    workflow.add_node("response_composer", chat_response_composer_node)

    workflow.set_entry_point("query_analyzer")
    workflow.add_edge("query_analyzer", "incident_matcher")
    workflow.add_edge("incident_matcher", "response_composer")
    workflow.add_edge("response_composer", END)

    return workflow.compile()


# Singleton compiled chat graph
_chat_graph = None


def get_incident_chat_graph():
    global _chat_graph
    if _chat_graph is None:
        _chat_graph = build_incident_chat_graph()
    return _chat_graph
