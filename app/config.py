"""Application settings, loaded from environment variables (or a .env file).

Centralizing config here keeps tunables (retry count, timeout, backend choice)
out of the business logic and makes them easy to override in tests.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Persistence: "memory" (default, no external deps) or "mongo".
    repo_backend: str = "memory"

    # LLM retry/timeout behaviour.
    llm_max_attempts: int = 3
    llm_timeout_seconds: float = 5.0

    # MongoDB — only used when repo_backend == "mongo".
    mongo_uri: str = "mongodb://localhost:27017"
    mongo_db: str = "travelio"
    mongo_collection: str = "classifications"


# Single shared instance imported across the app.
settings = Settings()
