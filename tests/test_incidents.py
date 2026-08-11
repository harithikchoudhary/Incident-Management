import sys
import os
import json
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
os.chdir(os.path.join(os.path.dirname(__file__), "..", "backend"))

from app.services.ingestion_service import MockChatSource
from app.models.chat_message import ChatThread
from app.agents.incident_extractor import IncidentExtractor
from app.agents.incident_analyzer import IncidentAnalyzer
from app.agents.resolution_agent import ResolutionAgent
from app.services.embedding_service import SimpleEmbeddingService, FAISSIndex
from app.config.settings import Settings


@pytest.fixture
def mock_chat_path():
    return os.path.join(os.path.dirname(__file__), "..", "backend", "data", "mock_google_chat.json")


@pytest.fixture
def settings():
    return Settings(
        database_url="sqlite:///./test_incidents.db",
        faiss_index_path="./test_data/faiss_index",
    )


class TestIngestion:
    def test_load_mock_data(self, mock_chat_path):
        source = MockChatSource(file_path=mock_chat_path)
        spaces = source.get_spaces()
        assert len(spaces) >= 1
        assert len(spaces[0].messages) > 0

    def test_get_threads(self, mock_chat_path):
        source = MockChatSource(file_path=mock_chat_path)
        threads = source.get_threads()
        assert len(threads) >= 15

    def test_thread_grouping(self, mock_chat_path):
        source = MockChatSource(file_path=mock_chat_path)
        threads = source.get_threads()
        for thread in threads:
            thread_ids = set(m.thread_id for m in thread.messages)
            assert len(thread_ids) == 1, "All messages in a thread must have same thread_id"

    def test_thread_has_messages(self, mock_chat_path):
        source = MockChatSource(file_path=mock_chat_path)
        threads = source.get_threads()
        for thread in threads:
            assert len(thread.messages) >= 5, f"Thread {thread.thread_id} has too few messages"


class TestIncidentExtraction:
    def test_heuristic_extraction(self, mock_chat_path):
        source = MockChatSource(file_path=mock_chat_path)
        threads = source.get_threads()
        extractor = IncidentExtractor()

        # Use heuristic extraction directly
        thread = threads[0]
        conversation_text = extractor._format_conversation(thread)
        incident = extractor._heuristic_extract(thread, conversation_text)

        assert incident is not None
        assert incident.incident_id.startswith("INC-")
        assert incident.application != ""
        assert incident.source_thread_id == thread.thread_id
        assert incident.conversation_text is not None

    def test_application_detection(self):
        extractor = IncidentExtractor()
        assert extractor._detect_application("Payment API is down") == "Payment API"
        assert extractor._detect_application("Order Service timeout") == "Order Service"
        assert extractor._detect_application("something unknown") == "Unknown Service"

    def test_error_code_detection(self):
        extractor = IncidentExtractor()
        codes = extractor._detect_error_codes("HTTP 500 errors and also seeing 503")
        assert "HTTP 500" in codes
        assert "HTTP 503" in codes


class TestIncidentAnalyzer:
    def test_analyze_payment_incident(self):
        analyzer = IncidentAnalyzer()
        result = analyzer.analyze(
            description="Payment API returning 500 errors. Database connection pool exhausted.",
            application="Payment API",
            environment="PROD",
        )
        assert result["application"] == "Payment API"
        assert result["environment"] == "PROD"
        assert "HTTP 500" in result["error_codes"]
        assert result["severity"] in ("HIGH", "CRITICAL")

    def test_analyze_unknown_app(self):
        analyzer = IncidentAnalyzer()
        result = analyzer.analyze("Some service is slow")
        assert result["application"] is not None
        assert result["environment"] == "PROD"


class TestResolutionAgent:
    def test_no_match_response(self):
        agent = ResolutionAgent()
        result = agent.generate_resolution(
            incident_summary={"description": "Unknown error"},
            matched_incidents=[],
            evidence=[],
        )
        assert result["confidence"] == 0.0
        assert result["confidence_level"] == "LOW"
        assert len(result["warnings"]) > 0
        assert "No sufficiently similar" in result["warnings"][0]

    def test_high_confidence_resolution(self):
        agent = ResolutionAgent()
        result = agent.generate_resolution(
            incident_summary={
                "description": "Payment API HTTP 500",
                "application": "Payment API",
            },
            matched_incidents=[
                {
                    "incident_id": "INC-001",
                    "application": "Payment API",
                    "similarity": 0.94,
                    "problem_summary": "Payment API HTTP 500",
                    "root_cause": "DB connection pool exhaustion",
                    "resolution": ["Increase pool size", "Restart service"],
                }
            ],
            evidence=[
                {
                    "incident_id": "INC-001",
                    "source_thread_id": "thread-001",
                    "source_message_ids": ["msg-001"],
                }
            ],
        )
        assert result["confidence"] == 0.94
        assert result["confidence_level"] == "HIGH"
        assert len(result["recommended_resolution"]) > 0
        assert result["likely_root_cause"] is not None


class TestEmbeddings:
    def test_simple_embedding(self):
        service = SimpleEmbeddingService()
        vec = service.embed("Payment API error HTTP 500")
        assert len(vec) == 1536
        assert any(v != 0 for v in vec)

    def test_embedding_similarity(self):
        import numpy as np
        service = SimpleEmbeddingService()
        v1 = np.array(service.embed("Payment API HTTP 500 database connection pool"))
        v2 = np.array(service.embed("Payment API HTTP 500 database connection exhausted"))
        v3 = np.array(service.embed("Notification email DNS configuration"))

        sim_12 = np.dot(v1, v2)
        sim_13 = np.dot(v1, v3)
        # Similar texts should have higher similarity
        assert sim_12 > sim_13


class TestDuplicatePrevention:
    def test_thread_id_uniqueness(self, mock_chat_path):
        source = MockChatSource(file_path=mock_chat_path)
        threads = source.get_threads()
        thread_ids = [t.thread_id for t in threads]
        assert len(thread_ids) == len(set(thread_ids)), "Thread IDs must be unique"
