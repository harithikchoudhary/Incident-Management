import json
import re
import logging
from datetime import datetime
from typing import Optional
import uuid

from app.models.incident import Incident
from app.models.chat_message import ChatThread
from app.services.llm_service import LLMService, get_llm_service

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """You are an expert incident extraction agent. 
Given a Google Chat conversation about a production incident, extract structured incident data.

You must distinguish between:
- Symptoms (what was observed)
- Investigation findings (what was discovered during troubleshooting)  
- Root cause (the actual underlying cause)
- Attempted fixes (things tried that may or may not have worked)
- Final resolution (the fix that actually resolved the issue, confirmed by the conversation)

Do NOT assume an attempted fix was successful unless the conversation explicitly confirms it worked.

Return a JSON object with these fields:
{
    "application": "name of the affected application/service",
    "environment": "PROD or STAGING or DEV",
    "severity": "CRITICAL or HIGH or MEDIUM or LOW",
    "problem_summary": "brief summary of the problem",
    "symptoms": ["list of observed symptoms"],
    "error_codes": ["HTTP 500", "etc"],
    "root_cause": "the actual root cause",
    "resolution": ["list of steps taken to resolve"],
    "status": "RESOLVED or OPEN",
    "lob": "the Line of Business (LOB) impacted, e.g. ML, PL, GL, Retail Banking",
    "issue": "short statement of what the issue is",
    "identified_time": "when the issue was identified, as stated in the chat (e.g. 06:15 AM)",
    "upstream_downstream": "any upstream/downstream app or infra affected, or null",
    "impacted_users": "count/description of impacted or logged-in users, or null",
    "failed_cases": "count of stuck or failed cases, or null",
    "business_impact": "business/revenue impact described, or null",
    "created_at": "ISO timestamp of first message",
    "resolved_at": "ISO timestamp of resolution message or null"
}

Return ONLY valid JSON, no additional text."""


class IncidentExtractor:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or get_llm_service()

    def extract(self, thread: ChatThread) -> Optional[Incident]:
        conversation_text = self._format_conversation(thread)
        template_fields = self._extract_template_fields(conversation_text)
        prompt = f"Extract the incident from this Google Chat conversation:\n\n{conversation_text}"

        try:
            response = self.llm.generate(prompt, system_prompt=EXTRACTION_SYSTEM_PROMPT)
            incident_data = self._parse_response(response)
            if incident_data:
                return self._build_incident(incident_data, thread, conversation_text, template_fields)
        except Exception as e:
            logger.error(f"LLM extraction failed for thread {thread.thread_id}: {e}")

        # Fallback: heuristic extraction
        return self._heuristic_extract(thread, conversation_text, template_fields)

    def _format_conversation(self, thread: ChatThread) -> str:
        lines = []
        for msg in sorted(thread.messages, key=lambda m: m.timestamp):
            lines.append(f"[{msg.timestamp}] {msg.user}: {msg.text}")
        return "\n".join(lines)

    def _extract_template_fields(self, text: str) -> dict:
        """Parse the structured 'Kindly share details' Q&A answers from the conversation."""
        patterns = {
            "issue": r"What is the issue\?[ \t]*(.+)",
            "lob": r"Which LOB is impacted\?[ \t]*(.+)",
            "identified_time": r"What time was it identified\?[ \t]*(.+)",
            "upstream_downstream": r"Any upstream[\/ ]?downstream[^?]*\?[ \t]*(.+)",
            "impacted_users": r"Count of impacted[^?]*\?[ \t]*(.+)",
            "failed_cases": r"Count of stuck[^?]*\?[ \t]*(.+)",
            "business_impact": r"Business revenue impacted\?[ \t]*(.+)",
        }
        # An unanswered template line is followed by the next question, not an answer
        question_start = re.compile(r"(?i)^(which|what|any|count|business|how)\b")
        result = {}
        for field, pat in patterns.items():
            for m in re.finditer(pat, text, re.IGNORECASE):
                value = m.group(1).strip()
                if not value or value.endswith("?") or question_start.match(value):
                    continue
                result[field] = value
                break
        # Fallback: many status updates state the LOB in an "Issue Statement" block as "LOB: <value>"
        if "lob" not in result:
            m = re.search(r"(?im)^[ \t]*LOB[ \t]*:[ \t]*(.+)$", text)
            if m:
                value = m.group(1).strip()
                if value and not question_start.match(value):
                    result["lob"] = value
        return result

    def _parse_response(self, response: str) -> Optional[dict]:
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        return None

    def _derive_incident_id(self, thread: ChatThread) -> str:
        """Derive a traceable incident ID from the source thread instead of a random UUID.

        The thread_id is "thread-<source_incident_id>" (optionally with a "-reopened"
        suffix), so stripping the prefix maps the record straight back to the source data.
        """
        thread_id = (thread.thread_id or "").strip()
        source_id = re.sub(r'^thread-', '', thread_id).strip()
        if source_id:
            return source_id
        return f"INC-{uuid.uuid4().hex[:8].upper()}"

    def _build_incident(self, data: dict, thread: ChatThread, conversation_text: str, template_fields: Optional[dict] = None) -> Incident:
        incident_id = self._derive_incident_id(thread)
        created_at = data.get("created_at", thread.messages[0].timestamp if thread.messages else datetime.now().isoformat())
        resolved_at = data.get("resolved_at")
        tf = template_fields or {}

        def pick(key):
            v = data.get(key)
            if v is None or (isinstance(v, str) and not v.strip()):
                v = tf.get(key)
            return v

        return Incident(
            incident_id=incident_id,
            application=data.get("application", "Unknown"),
            environment=data.get("environment", "PROD"),
            severity=data.get("severity", "MEDIUM"),
            problem_summary=data.get("problem_summary", ""),
            symptoms=data.get("symptoms", []),
            error_codes=data.get("error_codes", []),
            root_cause=data.get("root_cause"),
            resolution=data.get("resolution", []),
            status=data.get("status", "RESOLVED"),
            lob=pick("lob"),
            issue=pick("issue") or data.get("problem_summary"),
            identified_time=pick("identified_time"),
            upstream_downstream=pick("upstream_downstream"),
            impacted_users=pick("impacted_users"),
            failed_cases=pick("failed_cases"),
            business_impact=pick("business_impact"),
            created_at=self._parse_datetime(created_at),
            resolved_at=self._parse_datetime(resolved_at) if resolved_at else None,
            source_space=thread.space_id,
            source_thread_id=thread.thread_id,
            source_message_ids=[m.message_id for m in thread.messages],
            conversation_text=conversation_text,
        )

    def _heuristic_extract(self, thread: ChatThread, conversation_text: str, template_fields: Optional[dict] = None) -> Incident:
        """Fallback extraction when LLM is unavailable."""
        messages = sorted(thread.messages, key=lambda m: m.timestamp)
        first_msg = messages[0] if messages else None
        last_msg = messages[-1] if messages else None
        tf = template_fields or {}

        # Extract application from conversation
        application = self._detect_application(conversation_text)
        error_codes = self._detect_error_codes(conversation_text)
        severity = "HIGH" if any(c in ["500", "503"] for c in error_codes) else "MEDIUM"

        # Build symptoms from early messages
        symptoms = [m.text for m in messages[:2]] if len(messages) >= 2 else []

        # Root cause from later messages mentioning "root cause", "cause", "because"
        root_cause = None
        resolution = []
        for msg in messages:
            text_lower = msg.text.lower()
            if any(kw in text_lower for kw in ["root cause", "caused by", "the issue was", "problem was"]):
                root_cause = msg.text
            if any(kw in text_lower for kw in ["resolved", "fixed", "stable now", "back to normal"]):
                resolution.append(msg.text)

        incident_id = self._derive_incident_id(thread)

        return Incident(
            incident_id=incident_id,
            application=application,
            environment="PROD",
            severity=severity,
            problem_summary=first_msg.text if first_msg else "Unknown incident",
            symptoms=symptoms,
            error_codes=error_codes,
            root_cause=root_cause,
            resolution=resolution if resolution else ["See conversation for details"],
            status="RESOLVED",
            lob=tf.get("lob"),
            issue=tf.get("issue") or (first_msg.text if first_msg else None),
            identified_time=tf.get("identified_time"),
            upstream_downstream=tf.get("upstream_downstream"),
            impacted_users=tf.get("impacted_users"),
            failed_cases=tf.get("failed_cases"),
            business_impact=tf.get("business_impact"),
            created_at=self._parse_datetime(first_msg.timestamp) if first_msg else datetime.now(),
            resolved_at=self._parse_datetime(last_msg.timestamp) if last_msg else None,
            source_space=thread.space_id,
            source_thread_id=thread.thread_id,
            source_message_ids=[m.message_id for m in messages],
            conversation_text=conversation_text,
        )

    def _detect_application(self, text: str) -> str:
        apps = [
            "Payment API", "Order Service", "Customer Service",
            "Authentication Service", "Notification Service",
            "Inventory Service", "Loan Service", "Reporting Service",
        ]
        text_lower = text.lower()
        for app in apps:
            if app.lower() in text_lower:
                return app
        return "Unknown Service"

    def _detect_error_codes(self, text: str) -> list:
        codes = re.findall(r'(?:HTTP\s*)?([45]\d{2})', text)
        return list(set(f"HTTP {c}" for c in codes))

    def _parse_datetime(self, dt_str) -> datetime:
        if isinstance(dt_str, datetime):
            return dt_str
        if not dt_str:
            return datetime.now()
        try:
            return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return datetime.now()
