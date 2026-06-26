"""Unit tests for the classification pipeline (no FastAPI involved)."""

from __future__ import annotations

import json

import pytest

from app.llm.classifier import (
    LLMMalformedError,
    LLMTimeoutError,
    classify,
)
from app.models import Intent, Urgency
from tests.conftest import (
    FakeLLMClient,
    SequenceLLMClient,
    TimeoutLLMClient,
)


@pytest.mark.asyncio
async def test_happy_path_returns_valid_classification(valid_llm_json):
    """Happy path: valid JSON parses into a Classification on the first try."""
    classification, attempts = await classify(
        "AC bocor tolong kirim teknisi",
        None,
        FakeLLMClient(valid_llm_json),
        max_attempts=3,
        timeout=5.0,
    )

    assert attempts == 1
    assert classification.intent is Intent.MAINTENANCE_REQUEST
    assert classification.entities.urgency is Urgency.HIGH
    assert classification.needs_human is False


@pytest.mark.asyncio
async def test_malformed_output_retries_then_fails(truncated_llm_json):
    """Failure path: truncated JSON is retried N times, then raises."""
    llm = SequenceLLMClient([truncated_llm_json] * 3)

    with pytest.raises(LLMMalformedError):
        await classify("hi", None, llm, max_attempts=3, timeout=5.0)

    assert llm.calls == 3  # all attempts were used


@pytest.mark.asyncio
async def test_retries_then_succeeds(truncated_llm_json, valid_llm_json):
    """Resilience: fails twice, succeeds on the third attempt."""
    llm = SequenceLLMClient([truncated_llm_json, truncated_llm_json, valid_llm_json])

    classification, attempts = await classify(
        "hi", None, llm, max_attempts=3, timeout=5.0
    )

    assert attempts == 3
    assert classification.intent is Intent.MAINTENANCE_REQUEST


@pytest.mark.asyncio
async def test_timeout_is_retried_then_raises():
    """Timeouts are retried and ultimately surface as LLMTimeoutError."""
    with pytest.raises(LLMTimeoutError):
        await classify("hi", None, TimeoutLLMClient(), max_attempts=2, timeout=0.1)


@pytest.mark.asyncio
async def test_unknown_intent_is_coerced_not_failed():
    """An out-of-enum intent is normalized to 'unknown' + needs_human, not an error."""
    weird = json.dumps(
        {
            "intent": "please_refund_me",  # not in our closed enum
            "entities": {"dates": [], "location": None, "unit_type": None},
            "urgency": "low",
            "confidence": 0.6,
            "needs_human": False,
        }
    )

    classification, _ = await classify(
        "hi", None, FakeLLMClient(weird), max_attempts=2, timeout=5.0
    )

    assert classification.intent is Intent.UNKNOWN
    assert classification.needs_human is True


@pytest.mark.asyncio
async def test_top_level_urgency_is_lifted_into_entities():
    """The mock puts `urgency` at the top level; we lift it into entities."""
    raw = json.dumps(
        {
            "intent": "booking_inquiry",
            "entities": {"dates": [], "location": None, "unit_type": None},
            "urgency": "medium",  # top-level, like the mock client
            "confidence": 0.8,
            "needs_human": False,
        }
    )

    classification, _ = await classify(
        "hi", None, FakeLLMClient(raw), max_attempts=2, timeout=5.0
    )

    assert classification.entities.urgency is Urgency.MEDIUM
