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
    "created_at": "ISO timestamp of first message",
    "resolved_at": "ISO timestamp of resolution message or null"
}

Return ONLY valid JSON, no additional text."""


class IncidentExtractor:
    def __init__(self, llm_service: Optional[LLMService] = None):
        self.llm = llm_service or get_llm_service()

    def extract(self, thread: ChatThread) -> Optional[Incident]:
        conversation_text = self._format_conversation(thread)
        prompt = f"Extract the incident from this Google Chat conversation:\n\n{conversation_text}"

        try:
            response = self.llm.generate(prompt, system_prompt=EXTRACTION_SYSTEM_PROMPT)
            incident_data = self._parse_response(response)
            if incident_data:
                return self._build_incident(incident_data, thread, conversation_text)
        except Exception as e:
            logger.error(f"LLM extraction failed for thread {thread.thread_id}: {e}")

        # Fallback: heuristic extraction
        return self._heuristic_extract(thread, conversation_text)

    def _format_conversation(self, thread: ChatThread) -> str:
        lines = []
        for msg in sorted(thread.messages, key=lambda m: m.timestamp):
            lines.append(f"[{msg.timestamp}] {msg.user}: {msg.text}")
        return "\n".join(lines)

    def _parse_response(self, response: str) -> Optional[dict]:
        try:
            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                return json.loads(json_match.group())
        except json.JSONDecodeError:
            logger.warning("Failed to parse LLM response as JSON")
        return None

    def _build_incident(self, data: dict, thread: ChatThread, conversation_text: str) -> Incident:
        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"
        created_at = data.get("created_at", thread.messages[0].timestamp if thread.messages else datetime.now().isoformat())
        resolved_at = data.get("resolved_at")

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
            created_at=self._parse_datetime(created_at),
            resolved_at=self._parse_datetime(resolved_at) if resolved_at else None,
            source_space=thread.space_id,
            source_thread_id=thread.thread_id,
            source_message_ids=[m.message_id for m in thread.messages],
            conversation_text=conversation_text,
        )

    def _heuristic_extract(self, thread: ChatThread, conversation_text: str) -> Incident:
        """Fallback extraction when LLM is unavailable."""
        messages = sorted(thread.messages, key=lambda m: m.timestamp)
        first_msg = messages[0] if messages else None
        last_msg = messages[-1] if messages else None

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

        incident_id = f"INC-{uuid.uuid4().hex[:8].upper()}"

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
