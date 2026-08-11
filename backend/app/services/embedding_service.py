import json
import logging
import os
import numpy as np
from abc import ABC, abstractmethod
from typing import List, Optional

import faiss
from app.config.settings import get_settings

logger = logging.getLogger(__name__)


class EmbeddingService(ABC):
    @abstractmethod
    def embed(self, text: str) -> List[float]:
        pass

    @abstractmethod
    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        pass


class SimpleEmbeddingService(EmbeddingService):
    """Hash-based embedding for local use without external API."""

    def __init__(self):
        self.dimension = get_settings().embedding_dimension

    def _tokenize(self, text: str) -> List[str]:
        import re
        return re.findall(r'\b\w+\b', text.lower())

    def embed(self, text: str) -> List[float]:
        tokens = self._tokenize(text)
        vec = np.zeros(self.dimension, dtype=np.float32)
        for token in tokens:
            # Stable hash-based indexing
            idx = hash(token) % self.dimension
            vec[idx] += 1.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec = vec / norm
        return vec.tolist()

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        return [self.embed(text) for text in texts]


class FAISSIndex:
    def __init__(self):
        settings = get_settings()
        self.dimension = settings.embedding_dimension
        self.index_path = settings.faiss_index_path
        self.index: Optional[faiss.IndexFlatIP] = None
        self.id_map: List[str] = []
        self._load_or_create()

    def _load_or_create(self):
        index_file = f"{self.index_path}/index.faiss"
        map_file = f"{self.index_path}/id_map.json"
        if os.path.exists(index_file) and os.path.exists(map_file):
            self.index = faiss.read_index(index_file)
            with open(map_file, "r") as f:
                self.id_map = json.load(f)
        else:
            self.index = faiss.IndexFlatIP(self.dimension)
            self.id_map = []

    def add(self, incident_id: str, embedding: List[float]):
        vec = np.array([embedding], dtype=np.float32)
        faiss.normalize_L2(vec)
        self.index.add(vec)
        self.id_map.append(incident_id)

    def search(self, query_embedding: List[float], k: int = 5) -> List[tuple]:
        if self.index.ntotal == 0:
            return []
        vec = np.array([query_embedding], dtype=np.float32)
        faiss.normalize_L2(vec)
        k = min(k, self.index.ntotal)
        scores, indices = self.index.search(vec, k)
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx >= 0 and idx < len(self.id_map):
                results.append((self.id_map[idx], float(score)))
        return results

    def save(self):
        os.makedirs(self.index_path, exist_ok=True)
        faiss.write_index(self.index, f"{self.index_path}/index.faiss")
        with open(f"{self.index_path}/id_map.json", "w") as f:
            json.dump(self.id_map, f)

    def clear(self):
        self.index = faiss.IndexFlatIP(self.dimension)
        self.id_map = []

    def contains(self, incident_id: str) -> bool:
        return incident_id in self.id_map


def get_embedding_service() -> EmbeddingService:
    return SimpleEmbeddingService()


# Singleton instances
_embedding_service: Optional[EmbeddingService] = None
_faiss_index: Optional[FAISSIndex] = None


def get_embedding_service_instance() -> EmbeddingService:
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = get_embedding_service()
    return _embedding_service


def get_faiss_index() -> FAISSIndex:
    global _faiss_index
    if _faiss_index is None:
        _faiss_index = FAISSIndex()
    return _faiss_index
