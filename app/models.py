"""Pydantic models — the typed contract for the whole service.

These mirror `part_a_prompt/schema.json`. The LLM's raw JSON is validated against
`Classification`; the HTTP layer uses `ClassifyRequest` / `ClassifyResponse`; and
`ClassificationRecord` is what we persist.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field


class Intent(str, Enum):
    """Closed set of routable intents (kept in sync with part_a_prompt)."""

    BOOKING_INQUIRY = "booking_inquiry"
    MAINTENANCE_REQUEST = "maintenance_request"
    EXTENSION_REQUEST = "extension_request"
    PAYMENT_QUESTION = "payment_question"
    OUT_OF_SCOPE = "out_of_scope"
    UNKNOWN = "unknown"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Entities(BaseModel):
    dates: list[str] = Field(default_factory=list, description="ISO-8601 dates")
    location: str | None = None
    unit_type: str | None = None
    urgency: Urgency = Urgency.LOW


class Classification(BaseModel):
    """Validated LLM output. Malformed JSON fails to parse into this model."""

    intent: Intent
    entities: Entities
    confidence: float = Field(ge=0.0, le=1.0)
    needs_human: bool


# ---- HTTP contract ----------------------------------------------------------


class ClassifyRequest(BaseModel):
    message: str = Field(min_length=1, description="The guest message to classify")
    context: str | None = Field(
        default=None, description="Optional prior conversation text"
    )


class ClassifyResponse(BaseModel):
    classification: Classification
    latency_ms: float
    attempts: int
    timestamp: datetime


# ---- Persistence ------------------------------------------------------------


class ClassificationRecord(BaseModel):
    """One persisted classification (input + parsed output + latency + time)."""

    message: str
    context: str | None
    classification: Classification
    latency_ms: float
    attempts: int
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
