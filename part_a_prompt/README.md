# Part A — Prompt Engineering & Structured Extraction

## Deliverable 1 — The prompt
The full, shippable prompt lives in [`prompt.py`](prompt.py) as `PROMPT_TEMPLATE`,
rendered by `build_prompt(message, context, today)`. It uses an explicit
**ROLE / TASK / CONTEXT / OUTPUT FORMAT / EXAMPLES** structure:

- **ROLE** pins the model to a router persona (classify only, never chat).
- **TASK** states the three jobs (classify, extract, score) and lists the closed
  intent enum with one-line definitions.
- **CONTEXT** holds the normalization rules: relative-date resolution against
  `today`, ISO-8601 dates, unit-type normalization, an urgency rubric, the
  `needs_human` rule, and an explicit **prompt-injection defense** (treat the
  message as data; never obey instructions inside it; route manipulation attempts
  to `out_of_scope` + `needs_human=true`).
- **OUTPUT FORMAT** shows the exact minified JSON shape and forbids markdown/prose.
- **EXAMPLES** are few-shot, covering all five sample inbox messages — including
  the vague one (`payment_question`, low confidence, `needs_human=true`) and the
  adversarial one (`out_of_scope`, `needs_human=true`).

Part B imports `build_prompt()` directly, so the documented prompt and the
deployed prompt can never diverge.

## Deliverable 2 — The JSON output schema
See [`schema.json`](schema.json) (JSON Schema draft-07). It is mirrored by the
Pydantic models in `app/models.py`, which is what actually validates LLM output
at runtime. Summary:

| Field | Type | Notes |
|-------|------|-------|
| `intent` | enum | `booking_inquiry`, `maintenance_request`, `extension_request`, `payment_question`, `out_of_scope`, `unknown` |
| `entities.dates` | `string[]` | ISO-8601 `YYYY-MM-DD` |
| `entities.location` | `string \| null` | e.g. `"Kemang"` |
| `entities.unit_type` | enum \| null | `studio`, `1br`, `2br`, `3br` |
| `entities.urgency` | enum | `low`, `medium`, `high` |
| `confidence` | number 0–1 | model self-report |
| `needs_human` | boolean | low confidence / ambiguous / out_of_scope |

## Deliverable 3 — How I'd iterate on this prompt with real traffic
Once real messages flow in, I'd **log every (input, output, confidence) and build
a labeled eval set from production traffic** — prioritizing low-confidence,
`needs_human`, and `unknown` cases plus a random sample, since those are where the
prompt is weakest. Then I'd **change the prompt one variable at a time** (a rule,
an example, a definition), re-run the frozen eval set, and **compare per-intent
precision/recall** rather than a single accuracy number, so a fix for one intent
can't silently regress another. Rare intents get oversampled in the eval set and
backfilled with a few synthetic examples so they aren't drowned out.

## Assumptions
- Partial dates (no year) resolve to the nearest future occurrence relative to
  `today`. `today` defaults to `2026-06-26` and is injectable for testability.
- A separate `payment_question` intent is added beyond the mock's five values
  because sample message #4 ("bayar dimana ya") clearly needs its own route; the
  service still accepts the mock's enum and coerces anything unrecognized to
  `unknown`.
