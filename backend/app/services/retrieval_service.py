import logging
import re
from typing import List, Optional, Tuple

from app.config.settings import get_settings
from app.models.incident import Incident
from app.services.embedding_service import get_embedding_service_instance, get_faiss_index

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self):
        self.settings = get_settings()
        self.embedding_service = get_embedding_service_instance()
        self.faiss_index = get_faiss_index()

    def search_similar(
        self,
        query: str,
        application: Optional[str] = None,
        environment: Optional[str] = None,
        severity: Optional[str] = None,
        error_codes: Optional[List[str]] = None,
        k: int = 10,
    ) -> List[Tuple[str, float]]:
        """Hybrid search combining semantic, keyword, error, and application matching."""
        query_embedding = self.embedding_service.embed(query)
        semantic_results = self.faiss_index.search(query_embedding, k=k)

        if not semantic_results:
            return []

        # Import here to avoid circular dependency
        from app.repositories.incident_repository import get_incident_repository
        repo = get_incident_repository()

        scored_results = []
        for incident_id, semantic_score in semantic_results:
            incident = repo.get_by_id(incident_id)
            if incident is None:
                continue

            # Apply filters
            if environment and incident.environment != environment:
                continue
            if severity and incident.severity != severity:
                continue

            # Compute weighted score
            final_score = self._compute_weighted_score(
                semantic_score=semantic_score,
                query=query,
                incident=incident,
                application=application,
                error_codes=error_codes,
            )
            scored_results.append((incident_id, final_score))

        scored_results.sort(key=lambda x: x[1], reverse=True)
        return scored_results[:k]

    def _compute_weighted_score(
        self,
        semantic_score: float,
        query: str,
        incident: Incident,
        application: Optional[str] = None,
        error_codes: Optional[List[str]] = None,
    ) -> float:
        settings = self.settings

        # Semantic score component
        weighted_semantic = semantic_score * settings.search_weight_semantic

        # Keyword matching
        query_tokens = set(re.findall(r'\b\w+\b', query.lower()))
        incident_text = f"{incident.problem_summary} {incident.root_cause or ''} {' '.join(incident.symptoms or [])}".lower()
        incident_tokens = set(re.findall(r'\b\w+\b', incident_text))
        common = query_tokens & incident_tokens
        keyword_score = len(common) / max(len(query_tokens), 1)
        weighted_keyword = keyword_score * settings.search_weight_keyword

        # Error code matching
        error_score = 0.0
        if error_codes and incident.error_codes:
            incident_errors = set(e.upper() for e in incident.error_codes)
            query_errors = set(e.upper() for e in error_codes)
            if incident_errors & query_errors:
                error_score = 1.0
        elif error_codes is None:
            # Try to extract error codes from query
            found_errors = re.findall(r'(?:HTTP\s*)?[45]\d{2}', query)
            if found_errors and incident.error_codes:
                for err in found_errors:
                    clean_err = err.replace("HTTP ", "").replace("HTTP", "").strip()
                    if any(clean_err in e for e in incident.error_codes):
                        error_score = 1.0
                        break
        weighted_error = error_score * settings.search_weight_error_match

        # Application matching
        app_score = 0.0
        if application and incident.application:
            if application.lower() == incident.application.lower():
                app_score = 1.0
            elif application.lower() in incident.application.lower() or incident.application.lower() in application.lower():
                app_score = 0.7
        weighted_app = app_score * settings.search_weight_application

        return weighted_semantic + weighted_keyword + weighted_error + weighted_app

    def index_incident(self, incident: Incident):
        """Generate embedding and add to FAISS index."""
        text = self._build_embedding_text(incident)
        embedding = self.embedding_service.embed(text)
        self.faiss_index.add(incident.incident_id, embedding)
        self.faiss_index.save()

    def index_incidents_batch(self, incidents: List[Incident]):
        """Batch-embed incidents and persist the FAISS index once."""
        if not incidents:
            return
        texts = [self._build_embedding_text(inc) for inc in incidents]
        embeddings = self.embedding_service.embed_batch(texts)
        for inc, embedding in zip(incidents, embeddings):
            self.faiss_index.add(inc.incident_id, embedding)
        self.faiss_index.save()

    def clear_index(self):
        """Empty the FAISS index and persist the cleared state."""
        self.faiss_index.clear()
        self.faiss_index.save()

    def _build_embedding_text(self, incident: Incident) -> str:
        parts = [
            f"Application: {incident.application}",
            f"Problem: {incident.problem_summary}",
            f"Symptoms: {', '.join(incident.symptoms or [])}",
            f"Error codes: {', '.join(incident.error_codes or [])}",
            f"Root cause: {incident.root_cause or 'unknown'}",
            f"Resolution: {', '.join(incident.resolution or [])}",
        ]
        return " | ".join(parts)


_retrieval_service: Optional[RetrievalService] = None


def get_retrieval_service() -> RetrievalService:
    global _retrieval_service
    if _retrieval_service is None:
        _retrieval_service = RetrievalService()
    return _retrieval_service
