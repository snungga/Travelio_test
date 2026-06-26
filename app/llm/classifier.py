"""The classification pipeline: prompt -> LLM call -> retry -> validate.

This is the heart of Part B. It is intentionally a plain async function with an
injected `LLMClient`, so it can be tested without FastAPI or a real model.

Failure handling (per the requirements):
- Timeouts and malformed/invalid JSON are retried up to `max_attempts`.
- After the budget is exhausted, a typed error is raised so the HTTP layer can
  return the right status code (502 vs 504).
- An *unknown intent* (a value outside our closed enum) is NOT a failure — it is
  normalized to `unknown` + `needs_human=true` and returned, because that is a
  valid, routable outcome.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from pydantic import ValidationError

from app.llm.client import LLMClient
from app.models import Classification, Intent
from part_a_prompt.prompt import build_prompt

logger = logging.getLogger("classifier")

_VALID_INTENTS = {intent.value for intent in Intent}


class ClassifierError(Exception):
    """Base class for unrecoverable classification failures."""


class LLMTimeoutError(ClassifierError):
    """The LLM timed out on every attempt."""


class LLMMalformedError(ClassifierError):
    """The LLM never returned valid, schema-conforming JSON."""


def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
    """Adapt a raw LLM object to our `Classification` schema.

    The mock client (and real models) can drift from our exact shape, so we
    reconcile two known cases before validation:
    1. `urgency` arrives at the top level instead of inside `entities`.
    2. `intent` is a value outside our closed enum -> coerce to `unknown` and
       flag for a human instead of rejecting the whole response.
    """
    data = dict(raw)
    entities = dict(data.get("entities") or {})

    # (1) Lift a top-level `urgency` into entities if entities lacks it.
    if "urgency" in data and "urgency" not in entities:
        entities["urgency"] = data["urgency"]
    data["entities"] = entities

    # (2) Coerce an out-of-enum intent to a safe, human-routed default.
    if data.get("intent") not in _VALID_INTENTS:
        logger.info("coerced_unknown_intent", extra={"raw_intent": data.get("intent")})
        data["intent"] = Intent.UNKNOWN.value
        data["needs_human"] = True

    return data


async def classify(
    message: str,
    context: str | None,
    llm: LLMClient,
    *,
    max_attempts: int,
    timeout: float,
    today: str = "2026-06-26",
) -> tuple[Classification, int]:
    """Classify one message, retrying on timeout/malformed output.

    Returns the validated `Classification` and the number of attempts used.
    Raises `LLMTimeoutError` or `LLMMalformedError` once attempts are exhausted.
    """
    prompt = build_prompt(message, context=context, today=today)
    last_error: ClassifierError | None = None

    for attempt in range(1, max_attempts + 1):
        # --- call ---
        try:
            raw_text = await llm.complete(prompt, timeout=timeout)
        except asyncio.TimeoutError:
            last_error = LLMTimeoutError("LLM timed out")
            logger.warning("llm_timeout", extra={"attempt": attempt})
            continue

        # --- parse + validate ---
        try:
            data = _normalize(json.loads(raw_text))
            classification = Classification.model_validate(data)
        except (json.JSONDecodeError, ValidationError) as exc:
            last_error = LLMMalformedError(str(exc))
            logger.warning(
                "llm_malformed", extra={"attempt": attempt, "error": str(exc)}
            )
            continue

        logger.info(
            "classify_ok",
            extra={"attempt": attempt, "intent": classification.intent.value},
        )
        return classification, attempt

    # Every attempt failed; surface the last failure type to the caller.
    assert last_error is not None
    raise last_error
