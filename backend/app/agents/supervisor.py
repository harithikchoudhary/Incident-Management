"""Supervisor agent that orchestrates the incident analysis workflow."""
import logging

from app.agents.incident_analyzer import IncidentAnalyzer
from app.agents.incident_retriever import IncidentRetriever
from app.agents.resolution_agent import ResolutionAgent

logger = logging.getLogger(__name__)


class Supervisor:
    """Coordinates the full incident analysis pipeline."""

    def __init__(self):
        self.analyzer = IncidentAnalyzer()
        self.retriever = IncidentRetriever()
        self.resolution_agent = ResolutionAgent()

    def analyze_incident(self, description: str, application: str = None, environment: str = None) -> dict:
        # Step 1: Analyze
        structured = self.analyzer.analyze(description, application, environment)

        # Step 2: Retrieve
        matches = self.retriever.retrieve(
            query=structured["search_query"],
            application=structured["application"],
        )

        # Step 3: Get evidence
        incident_ids = [m["incident_id"] for m in matches[:3]]
        evidence = self.retriever.get_evidence(incident_ids)

        # Step 4: Generate resolution
        result = self.resolution_agent.generate_resolution(
            incident_summary=structured,
            matched_incidents=matches,
            evidence=evidence,
        )

        return result
