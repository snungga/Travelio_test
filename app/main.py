"""FastAPI app — Part B.

Exposes:
- POST /classify-message : classify one guest message (the core endpoint)
- GET  /health           : liveness + how many records have been stored
- GET  /classifications  : recent persisted results (handy for the demo)

The route handler stays thin: it delegates classification to `classify()`, maps
typed errors to HTTP status codes, persists the result, and returns a structured
response.
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import RedirectResponse

from app.config import settings
from app.dependencies import get_llm_client, get_repository
from app.llm.classifier import (
    LLMMalformedError,
    LLMTimeoutError,
    classify,
)
from app.llm.client import LLMClient
from app.logging_config import configure_logging
from app.models import (
    ClassificationRecord,
    ClassifyRequest,
    ClassifyResponse,
)
from app.repository.base import ClassificationRepository

configure_logging()
logger = logging.getLogger("api")

app = FastAPI(title="Travelio Message Classifier", version="1.0.0")


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    # Send the bare URL to the interactive API docs instead of a 404.
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health(repo: ClassificationRepository = Depends(get_repository)) -> dict:
    return {"status": "ok", "stored": len(await repo.list(limit=10_000))}


@app.get("/classifications", response_model=list[ClassificationRecord])
async def recent(
    limit: int = 20, repo: ClassificationRepository = Depends(get_repository)
) -> list[ClassificationRecord]:
    return await repo.list(limit=limit)


@app.post("/classify-message", response_model=ClassifyResponse)
async def classify_message(
    request: ClassifyRequest,
    repo: ClassificationRepository = Depends(get_repository),
    llm: LLMClient = Depends(get_llm_client),
) -> ClassifyResponse:
    request_id = str(uuid.uuid4())
    started = time.perf_counter()

    try:
        classification, attempts = await classify(
            request.message,
            request.context,
            llm,
            max_attempts=settings.llm_max_attempts,
            timeout=settings.llm_timeout_seconds,
        )
    except LLMTimeoutError:
        # Upstream model unavailable in time -> Gateway Timeout.
        logger.error("classify_failed_timeout", extra={"request_id": request_id})
        raise HTTPException(status_code=504, detail="LLM timed out after retries")
    except LLMMalformedError:
        # Upstream returned unusable output -> Bad Gateway.
        logger.error("classify_failed_malformed", extra={"request_id": request_id})
        raise HTTPException(
            status_code=502, detail="LLM returned invalid output after retries"
        )

    latency_ms = (time.perf_counter() - started) * 1000

    record = ClassificationRecord(
        message=request.message,
        context=request.context,
        classification=classification,
        latency_ms=latency_ms,
        attempts=attempts,
    )
    await repo.save(record)

    logger.info(
        "request_complete",
        extra={
            "request_id": request_id,
            "intent": classification.intent.value,
            "attempts": attempts,
            "latency_ms": round(latency_ms, 2),
            "needs_human": classification.needs_human,
        },
    )

    return ClassifyResponse(
        classification=classification,
        latency_ms=latency_ms,
        attempts=attempts,
        timestamp=datetime.now(timezone.utc),
    )
