"""Shared test doubles.

`MockLLMClient` is random by design, so tests inject these deterministic fakes
instead. Each fake satisfies the `LLMClient` protocol (just an async `complete`).
"""

from __future__ import annotations

import asyncio
import json

import pytest


class FakeLLMClient:
    """Always returns the same canned text."""

    def __init__(self, response: str) -> None:
        self._response = response

    async def complete(self, prompt: str, *, timeout: float = 5.0) -> str:
        return self._response


class TimeoutLLMClient:
    """Always times out (simulates a perpetually slow model)."""

    async def complete(self, prompt: str, *, timeout: float = 5.0) -> str:
        raise asyncio.TimeoutError("always times out")


class SequenceLLMClient:
    """Returns a scripted sequence of responses, one per call.

    Lets us test 'fails twice, then succeeds' style retry behaviour.
    """

    def __init__(self, responses: list[str]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def complete(self, prompt: str, *, timeout: float = 5.0) -> str:
        response = self._responses[self.calls]
        self.calls += 1
        return response


@pytest.fixture
def valid_llm_json() -> str:
    """A well-formed classification matching our schema."""
    return json.dumps(
        {
            "intent": "maintenance_request",
            "entities": {
                "dates": [],
                "location": None,
                "unit_type": None,
                "urgency": "high",
            },
            "confidence": 0.97,
            "needs_human": False,
        }
    )


@pytest.fixture
def truncated_llm_json() -> str:
    """The exact malformed shape the mock client emits (~8% of the time)."""
    return '{"intent": "booking_inquiry", "confidence": 0.9'
