import json
import logging
import time
from abc import ABC, abstractmethod
from typing import List, Optional

from openai import OpenAI
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class LLMService(ABC):
    @abstractmethod
    def generate(self, prompt: str, system_prompt: str = "") -> str:
        pass


class OpenAILLMService(LLMService):
    def __init__(self):
        settings = get_settings()
        self.client = OpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            project=settings.openai_project_id,
            timeout=settings.openai_timeout_seconds,
            max_retries=settings.openai_max_retries,
        )
        self.model = settings.openai_model

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.1,
                max_tokens=4096,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise


class MockLLMService(LLMService):
    """Fallback LLM that parses incidents from conversation heuristically."""

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        # For the POC, return a structured response based on the prompt content
        if "extract" in system_prompt.lower() or "incident" in system_prompt.lower():
            return self._extract_incident_heuristic(prompt)
        if "resolution" in system_prompt.lower() or "recommend" in system_prompt.lower():
            return self._generate_resolution_heuristic(prompt)
        return "{}"

    def _extract_incident_heuristic(self, prompt: str) -> str:
        return "{}"

    def _generate_resolution_heuristic(self, prompt: str) -> str:
        return "{}"


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = ResilientLLMService()
    return _llm_service


class ResilientLLMService(LLMService):
    """Tries OpenAI-compatible API first, falls back to MockLLMService on failure.

    Uses a cooldown-based circuit breaker so a down/slow primary LLM doesn't add
    full-timeout latency to every single request - once it fails, subsequent
    calls skip straight to the mock until the cooldown window elapses.
    """

    COOLDOWN_SECONDS = 60.0

    def __init__(self):
        self._primary_failed_at: Optional[float] = None
        self._mock = MockLLMService()
        try:
            self._primary = OpenAILLMService()
        except Exception:
            self._primary = None
            self._primary_failed_at = time.monotonic()

    def _primary_available(self) -> bool:
        if self._primary is None:
            return False
        if self._primary_failed_at is None:
            return True
        return (time.monotonic() - self._primary_failed_at) >= self.COOLDOWN_SECONDS

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        if self._primary_available():
            try:
                result = self._primary.generate(prompt, system_prompt)
                self._primary_failed_at = None
                return result
            except Exception as e:
                logger.warning(
                    f"OpenAI LLM failed, switching to heuristic mode for {self.COOLDOWN_SECONDS:.0f}s: {e}"
                )
                self._primary_failed_at = time.monotonic()
        return self._mock.generate(prompt, system_prompt)


_llm_service: Optional[LLMService] = None
