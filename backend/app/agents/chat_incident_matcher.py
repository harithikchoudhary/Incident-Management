import difflib
import re
from typing import Dict, Optional

from app.services.incident_service import IncidentService


_GENERIC_TOKENS = {
    "service", "services", "system", "application", "app", "portal", "server",
    "prod", "production", "cluster", "platform", "middleware", "web", "api",
    "all", "lob", "lobs", "the", "and", "for", "with", "impacted", "loan", "unknown",
}

# Below this, an embedding-only hit is too weak to present as a confident answer.
# Kept modest (rather than higher) because the hybrid semantic+keyword score for a
# genuinely correct match can legitimately land just above this in the 0.3-0.4 range.
MIN_SEMANTIC_SCORE = 0.30
FUZZY_CUTOFF = 0.82


class ChatIncidentMatcherAgent:
    """Retrieve and rank incidents using semantic + deterministic matching."""

    def __init__(self, service: IncidentService):
        self.service = service

    def _significant_tokens(self, value: str) -> set:
        tokens = re.findall(r"[A-Za-z0-9]+", (value or "").lower())
        return {t for t in tokens if len(t) >= 2 and t not in _GENERIC_TOKENS}

    def _fuzzy_hit(self, token_set: set, value: str) -> bool:
        """Catch typos/abbreviations that exact token matching misses."""
        candidate_tokens = self._significant_tokens(value)
        if not candidate_tokens or not token_set:
            return False
        for candidate in candidate_tokens:
            if difflib.get_close_matches(candidate, token_set, n=1, cutoff=FUZZY_CUTOFF):
                return True
        return False


    def _to_payload(self, inc) -> Dict:
        return {
            "incident_id": inc.incident_id,
            "application": inc.application,
            "lob": inc.lob,
            "environment": inc.environment,
            "severity": inc.severity,
            "status": inc.status,
            "problem_summary": inc.problem_summary,
            "issue": inc.issue,
            "identified_time": inc.identified_time,
            "symptoms": inc.symptoms or [],
            "error_codes": inc.error_codes or [],
            "impacted_users": inc.impacted_users,
            "failed_cases": inc.failed_cases,
            "business_impact": inc.business_impact,
            "root_cause": inc.root_cause,
            "resolution": inc.resolution or [],
            "source_thread_id": inc.source_thread_id,
            "source_message_ids": inc.source_message_ids or [],
        }

    def retrieve(self, query_analysis: Dict, top_k: int = 5) -> Dict:
        message = query_analysis.get("message", "")
        mentioned_ids = set(query_analysis.get("mentioned_incident_ids") or [])
        carried_ids = set(query_analysis.get("carried_incident_ids") or [])
        token_set = set(query_analysis.get("tokens") or [])

        all_incidents = self.service.get_all_incidents()
        all_payload = [self._to_payload(i) for i in all_incidents]

        picked = {}

        def add(inc, rank: int, reason: str, score: Optional[float] = None):
            payload = self._to_payload(inc)
            cur = picked.get(payload["incident_id"])
            candidate = (rank, 0.0 if score is None else float(score), reason, payload)
            if cur is None or (candidate[0], -candidate[1]) < (cur[0], -cur[1]):
                picked[payload["incident_id"]] = candidate

        for inc in all_incidents:
            iid = (inc.incident_id or "").upper()
            if iid in mentioned_ids:
                add(inc, 0, "incident-id match", 1.0)
            elif iid in carried_ids:
                add(inc, 0, "incident-id match (carried from earlier in conversation)", 0.95)

        for inc in all_incidents:
            if any(t in token_set for t in self._significant_tokens(inc.application)):
                add(inc, 1, f"application token match ({inc.application})", 0.85)
            elif self._fuzzy_hit(token_set, inc.application):
                add(inc, 1, f"application fuzzy match ({inc.application})", 0.7)

        for inc in all_incidents:
            if inc.lob and any(t in token_set for t in self._significant_tokens(inc.lob)):
                add(inc, 2, f"LOB token match ({inc.lob})", 0.8)
            elif inc.lob and self._fuzzy_hit(token_set, inc.lob):
                add(inc, 2, f"LOB fuzzy match ({inc.lob})", 0.65)

        semantic_results = self.service.search_incidents(query=message)
        top_k_semantic = max(top_k, query_analysis.get("use_top_k_embeddings", 5))
        for row in semantic_results[:top_k_semantic]:
            score = row.get("score", 0.0)
            if score >= MIN_SEMANTIC_SCORE:
                add(row["incident"], 3, "embedding similarity", score)

        # If nothing cleared the bar, surface the single closest hit but flag it
        # as low-confidence instead of silently answering off weak/irrelevant data.
        if not picked and semantic_results:
            best = semantic_results[0]
            add(best["incident"], 4, "closest available match (low confidence)", best.get("score", 0.0))

        ranked = sorted(picked.values(), key=lambda x: (x[0], -x[1], x[3]["incident_id"]))[:top_k]

        matches = [
            {
                "reason": reason,
                "score": round(score, 3),
                "incident": payload,
            }
            for rank, score, reason, payload in ranked
        ]

        low_confidence = (not ranked) or ranked[0][0] == 4

        return {
            "all_incidents": all_payload,
            "top_matches": matches,
            "semantic_top_k_used": query_analysis.get("use_top_k_embeddings", 5),
            "low_confidence": low_confidence,
        }
