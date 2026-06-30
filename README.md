# Travelio — AI Developer Take-Home

A guest-message classifier for Travelio: an LLM prompt (Part A) wired into a
production-ish FastAPI service (Part B), plus written deliverables on databases
(Part C), evaluation (Part D), and pipeline design (Part E).

> Design goal throughout: **clean, readable code that I can explain line by line.**
> Small modules, clear names, dependency injection so the LLM client and the
> database are swappable and testable.

## Repository layout
| Path | What's there |
|------|--------------|
| [`part_a_prompt/`](part_a_prompt/) | The shippable prompt (`prompt.py`), JSON schema, and iteration notes |
| [`app/`](app/) | **Part B** — the FastAPI service ([app/README.md](app/README.md) has its own run guide) |
| [`tests/`](tests/) | Unit + endpoint tests (happy / malformed / timeout paths) |
| [`part_c_databases/`](part_c_databases/) | C1 MySQL, C2 MongoDB, C3 root-cause, C4 ClickHouse |
| [`part_d_eval/`](part_d_eval/) | Eval set, metrics, regression, monitoring |
| [`part_e_pipeline/`](part_e_pipeline/) | Daily Dagster pipeline design |

> Each part folder that contains code has its own **README with a "How to run"
> section**: [Part A](part_a_prompt/README.md), [Part B](app/README.md),
> [Part C](part_c_databases/README.md).

## How to run

```bash
# 1. Set up the environment
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux
pip install -r requirements.txt

# 2. Run the tests
pytest -q

# 3. Start the service (in-memory backend, no Docker needed)
uvicorn app.main:app --reload
```

Then classify a message:

```bash
curl -X POST http://localhost:8000/classify-message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"AC di kamar bocor parah, tolong kirim teknisi secepatnya dong\"}"
```

Interactive docs at <http://localhost:8000/docs>; recent results at
`GET /classifications`; liveness at `GET /health`.

> The mock LLM returns a *random* intent (per Appendix 1), so a single live call
> won't necessarily match the message. The deterministic behaviour — parsing,
> retry, normalization — is what the tests pin down.

### Optional: MongoDB backend
```bash
docker compose up -d
REPO_BACKEND=mongo uvicorn app.main:app --reload
```

## Part B — design decisions
- **Dependency injection via Protocols.** `LLMClient` and `ClassificationRepository`
  are structural interfaces. The classifier depends on the interface, never a concrete
  class — so tests inject deterministic fakes and the DB swaps with a one-line change in
  [`app/dependencies.py`](app/dependencies.py).
- **The prompt has one home.** Part B imports `build_prompt()` from
  [`part_a_prompt/prompt.py`](part_a_prompt/prompt.py), so the documented and deployed
  prompts can't drift.
- **Robust failure handling** ([`app/llm/classifier.py`](app/llm/classifier.py)):
  - Timeouts and malformed/invalid JSON are **retried up to N times** (configurable).
  - Exhausted retries raise a typed error → mapped to **502** (bad output) or **504**
    (timeout) in [`app/main.py`](app/main.py).
  - An **unknown intent** (value outside the closed enum) is *not* a failure — it's
    normalized to `unknown` + `needs_human=true` and returned.
  - The mock emits `urgency` at the top level; we **normalize** it into `entities`
    before validation, demonstrating real-world shape reconciliation.
- **Validation everywhere.** LLM output is validated against the Pydantic
  `Classification` model ([`app/models.py`](app/models.py)), which mirrors
  `part_a_prompt/schema.json`.
- **Persistence** stores input, parsed output, latency, and timestamp per the spec.
  In-memory by default; injectable Mongo adapter for the real thing.
- **Structured JSON logging** ([`app/logging_config.py`](app/logging_config.py)) — one
  greppable line per request (request id, intent, attempts, latency, outcome).
- **Tests** ([`tests/`](tests/)) cover the happy path, the malformed→retry→502 failure
  path, timeout→504, request validation (422), unknown-intent coercion, and
  retry-then-succeed — all deterministic via fakes, never the random mock.

## Assumptions
- No real API keys; the provided `MockLLMClient` (Appendix 1) is used verbatim.
- A `payment_question` intent is added beyond the mock's five values (sample message
  #4 needs its own route); unrecognized intents coerce to `unknown`.
- Partial dates resolve to the nearest future date relative to a configurable `today`.
- Currency is intentionally *not* normalized in the C1 query — that's the deliberate
  trap behind the C3 GMV-drop scenario.

## What I'd do with more time
- Real concurrency-safe Mongo indexes + a migration for the `classifications` collection.
- Per-intent eval harness (Part D) wired into CI as a regression gate.
- Confidence calibration and a `needs_human` review queue UI.
- Replace the mock with a real model behind the same `LLMClient` protocol — zero change
  to the classifier.
- Containerize the service and add request-level tracing (OpenTelemetry).
