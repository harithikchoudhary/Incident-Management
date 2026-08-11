import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class IncidentAnalyzer:
    """Analyzes a new incident description and extracts structured information."""

    def analyze(self, description: str, application: Optional[str] = None, environment: Optional[str] = None) -> dict:
        error_codes = self._extract_error_codes(description)
        detected_app = application or self._detect_application(description)
        symptoms = self._extract_symptoms(description)
        severity = self._assess_severity(description, error_codes)

        return {
            "description": description,
            "application": detected_app,
            "environment": environment or "PROD",
            "severity": severity,
            "error_codes": error_codes,
            "symptoms": symptoms,
            "search_query": self._build_search_query(description, detected_app, error_codes),
        }

    def _extract_error_codes(self, text: str) -> list:
        codes = re.findall(r'(?:HTTP\s*)?([45]\d{2})', text)
        return list(set(f"HTTP {c}" for c in codes))

    def _detect_application(self, text: str) -> str:
        apps = {
            "payment": "Payment API",
            "order": "Order Service",
            "customer": "Customer Service",
            "auth": "Authentication Service",
            "notification": "Notification Service",
            "inventory": "Inventory Service",
            "loan": "Loan Service",
            "reporting": "Reporting Service",
        }
        text_lower = text.lower()
        for key, name in apps.items():
            if key in text_lower:
                return name
        return "Unknown Service"

    def _extract_symptoms(self, text: str) -> list:
        symptoms = []
        patterns = [
            r'(returning\s+\d{3}\s+errors?)',
            r'(connection\s+pool\s+exhaust\w*)',
            r'(timeout\w*)',
            r'(memory\s+(?:leak|exhaust|spike)\w*)',
            r'(CPU\s+spike\w*)',
            r'(consumer\s+lag\w*)',
            r'(certificate\s+expir\w*)',
            r'(deadlock\w*)',
            r'(DNS\s+(?:resolution|failure)\w*)',
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            symptoms.extend(matches)
        return symptoms if symptoms else [text[:100]]

    def _assess_severity(self, text: str, error_codes: list) -> str:
        text_lower = text.lower()
        if any(kw in text_lower for kw in ["critical", "all users", "complete outage", "data loss"]):
            return "CRITICAL"
        if any(c in ["HTTP 500", "HTTP 503"] for c in error_codes):
            return "HIGH"
        if any(kw in text_lower for kw in ["slow", "degraded", "intermittent"]):
            return "MEDIUM"
        return "HIGH"

    def _build_search_query(self, description: str, application: str, error_codes: list) -> str:
        parts = [description]
        if application != "Unknown Service":
            parts.append(f"application:{application}")
        if error_codes:
            parts.append(f"errors:{','.join(error_codes)}")
        return " ".join(parts)
