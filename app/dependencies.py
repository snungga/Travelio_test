"""Dependency wiring.

Builds the singletons (repository, LLM client) from `settings` and exposes them
as FastAPI dependencies. Centralizing construction here keeps `main.py` focused on
routing, and lets tests override these providers with fakes.
"""

from __future__ import annotations

from functools import lru_cache

from app.config import settings
from app.llm.client import LLMClient
from app.llm.mock_llm import MockLLMClient
from app.repository.base import ClassificationRepository
from app.repository.memory import InMemoryRepository


@lru_cache
def get_repository() -> ClassificationRepository:
    """Pick the persistence backend based on settings (built once)."""
    if settings.repo_backend == "mongo":
        # Imported lazily so the default path never needs motor/Mongo running.
        from app.repository.mongo import MongoRepository

        return MongoRepository(
            settings.mongo_uri, settings.mongo_db, settings.mongo_collection
        )
    return InMemoryRepository()


@lru_cache
def get_llm_client() -> LLMClient:
    """The LLM client. The mock is the only client per the assessment rules."""
    return MockLLMClient()
