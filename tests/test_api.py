"""Endpoint tests — drive the real FastAPI app with injected fakes.

We override the LLM and repository dependencies so the route is exercised end to
end without randomness or a database.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.dependencies import get_llm_client, get_repository
from app.main import app
from app.repository.memory import InMemoryRepository
from tests.conftest import FakeLLMClient, TimeoutLLMClient


def build_client(llm) -> TestClient:
    """A TestClient wired to the given LLM and a fresh in-memory repo."""
    repo = InMemoryRepository()
    app.dependency_overrides[get_repository] = lambda: repo
    app.dependency_overrides[get_llm_client] = lambda: llm
    return TestClient(app)


@pytest.fixture(autouse=True)
def clear_overrides():
    yield
    app.dependency_overrides.clear()


def test_classify_message_happy_path(valid_llm_json):
    client = build_client(FakeLLMClient(valid_llm_json))

    response = client.post("/classify-message", json={"message": "AC bocor"})

    assert response.status_code == 200
    body = response.json()
    assert body["classification"]["intent"] == "maintenance_request"
    assert body["attempts"] == 1
    assert body["latency_ms"] >= 0

    # The result was persisted.
    assert client.get("/health").json()["stored"] == 1


def test_classify_message_malformed_returns_502(truncated_llm_json):
    client = build_client(FakeLLMClient(truncated_llm_json))

    response = client.post("/classify-message", json={"message": "hi"})

    assert response.status_code == 502


def test_classify_message_timeout_returns_504():
    client = build_client(TimeoutLLMClient())

    response = client.post("/classify-message", json={"message": "hi"})

    assert response.status_code == 504


def test_empty_message_is_rejected_422(valid_llm_json):
    """Pydantic request validation rejects an empty message before the LLM."""
    client = build_client(FakeLLMClient(valid_llm_json))

    response = client.post("/classify-message", json={"message": ""})

    assert response.status_code == 422
