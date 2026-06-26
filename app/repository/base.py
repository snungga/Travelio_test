"""The persistence interface.

The classifier endpoint depends on this `Protocol`, not on a concrete database.
Swapping in-memory for Mongo (or a test double) is then a one-line change in
`dependencies.py` with zero impact on the route handler.
"""

from __future__ import annotations

from typing import Protocol

from app.models import ClassificationRecord


class ClassificationRepository(Protocol):
    async def save(self, record: ClassificationRecord) -> str:
        """Persist a record and return its id."""
        ...

    async def list(self, limit: int = 100) -> list[ClassificationRecord]:
        """Return the most recent records (newest first)."""
        ...
