from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    database_url: str = "postgresql://postgres:postgres@localhost:5432/incident_management"
    openai_api_key: str = ""
    openai_base_url: str = "https://bedrock-mantle.us-east-1.api.aws/v1"
    openai_project_id: str = "default"
    openai_model: str = "openai.gpt-oss-120b"
    openai_timeout_seconds: float = 30.0
    openai_max_retries: int = 1
    ingestion_max_workers: int = 8
    faiss_index_path: str = "./data/faiss_index"
    mock_chat_path: str = "./data/original_incident_data.json"
    log_level: str = "INFO"
    embedding_dimension: int = 384

    search_weight_semantic: float = 0.5
    search_weight_keyword: float = 0.2
    search_weight_error_match: float = 0.2
    search_weight_application: float = 0.1

    confidence_high_threshold: float = 0.85
    confidence_medium_threshold: float = 0.65

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
