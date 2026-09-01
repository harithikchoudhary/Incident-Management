import re
from typing import Dict, List, Optional


class ChatQueryAnalyzerAgent:
    """Analyze user chat query intent and extract retrieval hints."""

    # Broadened beyond plain 6-8 digit numbers to also catch prefixed ticket IDs
    # (INC-1234567, P-1234567, SNOW1234567, etc). False positives are filtered
    # downstream by the matcher, which only treats a candidate as an ID match
    # if it equals a real ingested incident_id.
    INCIDENT_ID_PATTERN = re.compile(r"\b(?:[A-Za-z]{2,6}-?)?\d{5,10}(?:-reopened)?\b", re.IGNORECASE)

    FOLLOWUP_MARKERS = [
        "that", "this", "it", "those", "these", "same", "previous", "again",
        "more", "other one", "the second", "the first", "above",
    ]

    STATS_KEYWORDS = [
        "how many", "count", "most", "least", "top", "breakdown", "summary",
        "trend", "percentage", "percent", "average", "stats", "statistics",
        "number of",
    ]

    INCIDENT_KEYWORDS = [
        "error", "incident", "failed", "failure", "down", "outage", "timeout",
        "slow", "slowness", "degraded", "500", "503", "cpu", "memory", "disk",
        "redis", "kafka", "mongodb", "elasticsearch", "certificate", "deadlock",
    ]

    def _extract_ids(self, text: str) -> List[str]:
        ids = []
        for raw in self.INCIDENT_ID_PATTERN.findall(text or ""):
            cleaned = re.sub(r"^(INC|P)-?", "", raw.upper())
            ids.append(cleaned)
        return ids

    def _word_in(self, phrase: str, text_l: str) -> bool:
        return re.search(r"\b" + re.escape(phrase) + r"\b", text_l) is not None

    def _introduces_new_specifics(self, text: str) -> bool:
        """True if the message carries its own concrete reference (IP, digits, etc.)
        rather than being a vague follow-up - carrying forward an old incident ID
        over a message like this would misattribute an unrelated new topic."""
        return bool(re.search(r"\d", text))

    def analyze(self, message: str, conversation_history: Optional[List[dict]] = None) -> Dict:
        text = (message or "").strip()
        text_l = text.lower()
        history = conversation_history or []

        mentioned_ids = list(dict.fromkeys(self._extract_ids(text)))

        # Short messages or ones with pronouns like "that"/"it" are likely follow-ups
        # referring to an incident already discussed earlier in the conversation.
        is_followup = any(self._word_in(w, text_l) for w in self.FOLLOWUP_MARKERS) or len(text_l.split()) <= 4

        carried_ids: List[str] = []
        if not mentioned_ids and is_followup and not self._introduces_new_specifics(text):
            for turn in reversed(history[-6:]):
                found = self._extract_ids(str(turn.get("content", "")))
                if found:
                    carried_ids = list(dict.fromkeys(found))
                    break

        is_stats = any(self._word_in(k, text_l) for k in self.STATS_KEYWORDS)
        looks_like_incident = any(self._word_in(k, text_l) for k in self.INCIDENT_KEYWORDS)

        if is_stats:
            intent = "stats"
        elif mentioned_ids or carried_ids:
            intent = "lookup"
        elif looks_like_incident:
            intent = "incident_help"
        else:
            intent = "general"

        tokens = re.findall(r"[a-z0-9][a-z0-9_\-/]*", text_l)

        return {
            "message": text,
            "intent": intent,
            "mentioned_incident_ids": mentioned_ids,
            "carried_incident_ids": carried_ids,
            "is_followup": is_followup,
            "tokens": tokens,
            "use_top_k_embeddings": 5,
            "conversation_turns": len(history),
        }
