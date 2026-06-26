"""The LLM client interface.

Defining a `Protocol` (structural type) means the real `MockLLMClient` and the
test-only `FakeLLMClient` are interchangeable without inheritance. The classifier
depends on this interface, never on a concrete client — that's what makes it
unit-testable with deterministic fakes.
"""

from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    async def complete(self, prompt: str, *, timeout: float = 5.0) -> str:
        """Return the model's raw text completion for `prompt`.

        May raise `asyncio.TimeoutError` and may return malformed JSON — callers
        must handle both.
        """
        ...
