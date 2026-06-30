# Part B — FastAPI Classifier Service (`app/`)

This folder is the **Part B** deliverable: a small web service that takes a guest
message, asks the (mock) LLM to classify it, validates the result, stores it, and
returns a clean response.

## How to run

### 1. Set up once
```bash
# from the project root (travelio-ai-test/)
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS / Linux
pip install -r requirements.txt
```

### 2. Start the service
```bash
uvicorn app.main:app --reload
```
Wait for `Application startup complete`, then the service is live at
**http://localhost:8000**.

### 3. Try it
The easiest way is the built-in interactive docs:
- Open **http://localhost:8000/docs** → expand `POST /classify-message` →
  **Try it out** → edit the message → **Execute**.

Or from a second terminal:
```bash
curl -X POST http://localhost:8000/classify-message \
  -H "Content-Type: application/json" \
  -d "{\"message\": \"AC di kamar bocor parah, tolong kirim teknisi secepatnya\"}"
```

> The mock LLM returns a **random** intent (that is intentional — see Appendix 1 of
> the test), so a single call may not match the message. The reliable, tested
> behaviour is the *pipeline*: validation, retry, and correct status codes.

### 4. Run the tests
```bash
pytest -q
```
Expected: **all tests pass** (happy path, malformed→502, timeout→504, validation→422).

## Endpoints
| Method | Path | What it does |
|--------|------|--------------|
| `POST` | `/classify-message` | Classify one message; returns intent + entities + latency + attempts |
| `GET`  | `/classifications` | List recently stored results |
| `GET`  | `/health` | Liveness + how many results are stored |
| `GET`  | `/` | Redirects to `/docs` |

## How the code is organised
```
app/
├── main.py            # the web routes (POST /classify-message, /health, ...)
├── config.py          # settings read from env / .env (retry count, timeout, backend)
├── models.py          # the data shapes (Pydantic) — request, response, stored record
├── logging_config.py  # one JSON log line per request
├── dependencies.py    # picks which LLM client + database to use
├── llm/
│   ├── client.py      # the LLM "interface" (so mock and real client are swappable)
│   ├── mock_llm.py    # the provided fake LLM (random output, sometimes broken)
│   └── classifier.py  # the core logic: build prompt → call → retry → validate
└── repository/
    ├── base.py        # the storage "interface"
    ├── memory.py      # default storage (in memory, no database needed)
    └── mongo.py       # optional MongoDB storage
```

## Configuration (optional)
All settings have sensible defaults, so you can run with zero configuration. To
override, set environment variables (or copy `.env.example` to `.env`):

| Variable | Default | Meaning |
|----------|---------|---------|
| `REPO_BACKEND` | `memory` | `memory` (no database) or `mongo` |
| `LLM_MAX_ATTEMPTS` | `3` | How many times to retry the LLM before giving up |
| `LLM_TIMEOUT_SECONDS` | `5.0` | Per-call timeout |

Using MongoDB instead of in-memory storage:
```bash
docker compose up -d                          # starts MongoDB
REPO_BACKEND=mongo uvicorn app.main:app --reload
```
