"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and type safety.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration for the Deep Research Agent backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── LLM (Google Gemini) ──
    google_api_key: str = ""
    gemini_model: str = "gemini-2.0-flash"
    embedding_model: str = "models/text-embedding-004"

    # ── Search APIs ──
    tavily_api_key: str = ""

    # ── Qdrant (Vector DB) ──
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "research_knowledge_base"

    # ── Neo4j (Graph DB) ──
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "mowsis_dev_2026"

    # ── PostgreSQL ──
    postgres_url: str = "postgresql://mowsis:mowsis_dev_2026@localhost:5432/mowsis_db"

    # ── App Settings ──
    app_env: str = "development"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    cors_origins: str = "http://localhost:5173"

    # ── Budget Defaults ──
    max_loops: int = 3
    max_tavily_calls: int = 4
    max_scholar_calls: int = 6
    max_documents_to_read: int = 8
    max_total_input_tokens: int = 150_000

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_development(self) -> bool:
        return self.app_env == "development"


# Singleton instance — import this throughout the app
settings = Settings()
