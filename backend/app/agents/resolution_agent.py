import logging
from typing import List, Optional

from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class ResolutionAgent:
    """Generates resolution recommendations based on retrieved historical incidents.
    
    This agent does NOT invent solutions. It only recommends based on evidence.
    """

    def __init__(self):
        self.settings = get_settings()

    def generate_resolution(
        self,
        incident_summary: dict,
        matched_incidents: List[dict],
        evidence: List[dict],
    ) -> dict:
        if not matched_incidents:
            return self._no_match_response(incident_summary)

        top_match = matched_incidents[0]
        confidence = top_match.get("similarity", 0.0)
        confidence_level = self._get_confidence_level(confidence)

        # Build match reasons
        matched_with_reasons = []
        for match in matched_incidents[:3]:
            reason = self._build_match_reason(incident_summary, match)
            matched_with_reasons.append({
                "incident_id": match["incident_id"],
                "similarity": round(match["similarity"], 2),
                "reason": reason,
            })

        # Build resolution from historical evidence
        recommended_resolution = self._build_resolution(matched_incidents)
        likely_root_cause = self._infer_root_cause(matched_incidents)
        warnings = self._build_warnings(confidence_level, incident_summary)

        evidence_refs = []
        for ev in evidence:
            evidence_refs.append({
                "incident_id": ev.get("incident_id"),
                "source_thread_id": ev.get("source_thread_id"),
                "source_message_ids": ev.get("source_message_ids", []),
            })

        return {
            "incident_summary": incident_summary.get("description", ""),
            "likely_root_cause": likely_root_cause,
            "confidence": round(confidence, 2),
            "confidence_level": confidence_level,
            "matched_incidents": matched_with_reasons,
            "recommended_resolution": recommended_resolution,
            "evidence": evidence_refs,
            "warnings": warnings,
        }

    def _no_match_response(self, incident_summary: dict) -> dict:
        return {
            "incident_summary": incident_summary.get("description", ""),
            "likely_root_cause": None,
            "confidence": 0.0,
            "confidence_level": "LOW",
            "matched_incidents": [],
            "recommended_resolution": [],
            "evidence": [],
            "warnings": ["No sufficiently similar historical incident was found. Manual investigation required."],
        }

    def _get_confidence_level(self, score: float) -> str:
        if score >= self.settings.confidence_high_threshold:
            return "HIGH"
        elif score >= self.settings.confidence_medium_threshold:
            return "MEDIUM"
        return "LOW"

    def _build_match_reason(self, incident: dict, match: dict) -> str:
        reasons = []
        if incident.get("application") and match.get("application"):
            if incident["application"].lower() == match["application"].lower():
                reasons.append(f"Same application: {match['application']}")
        if match.get("root_cause"):
            reasons.append(f"Similar root cause pattern: {match['root_cause'][:80]}")
        if not reasons:
            reasons.append(f"Similar problem description")
        return ". ".join(reasons)

    def _build_resolution(self, matches: List[dict]) -> List[str]:
        resolutions = []
        seen = set()
        for match in matches:
            for step in (match.get("resolution") or []):
                if step.lower() not in seen:
                    resolutions.append(step)
                    seen.add(step.lower())
        return resolutions[:5]

    def _infer_root_cause(self, matches: List[dict]) -> Optional[str]:
        for match in matches:
            if match.get("root_cause"):
                return match["root_cause"]
        return None

    def _build_warnings(self, confidence_level: str, incident: dict) -> List[str]:
        warnings = []
        if confidence_level == "LOW":
            warnings.append("Low confidence match. Manual investigation strongly recommended.")
        elif confidence_level == "MEDIUM":
            warnings.append("Medium confidence. Verify conditions match before applying resolution.")
        warnings.append("Verify current system state before applying historical resolution steps.")
        return warnings
