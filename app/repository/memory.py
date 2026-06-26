"""In-memory repository — the default backend.

Requires no external services, so the whole app runs and tests with `pip install`
alone. Records live in a list for the process lifetime.
"""

from __future__ import annotations

from app.models import ClassificationRecord


class InMemoryRepository:
    def __init__(self) -> None:
        self._records: list[ClassificationRecord] = []

    async def save(self, record: ClassificationRecord) -> str:
        self._records.append(record)
        return str(len(self._records) - 1)  # index doubles as the id

    async def list(self, limit: int = 100) -> list[ClassificationRecord]:
        return list(reversed(self._records[-limit:]))
