# Part D — Proving It's Production-Ready (Eval & Observability)

For the message classifier from Parts A/B.

## 1. Eval set — how to build it
- **Source from real production traffic, not just hand-written examples.** Log every
  `(message, context, parsed output, confidence, needs_human)` from the live service.
  Real guest messages capture the actual mix of Bahasa/English, typos, and slang that
  synthetic data misses.
- **Sampling strategy:** stratified, not uniform. Take (a) a random sample for an
  unbiased baseline, plus (b) oversampled hard cases — low-confidence,
  `needs_human=true`, `unknown`, and adversarial/out-of-scope messages — because those
  are where the model is weakest and where errors are most expensive.
- **Size:** start with ~200–500 human-labeled messages; enough for stable per-intent
  numbers without being a labeling burden. Grow it over time as new failure modes
  appear in production.
- **Rare intents:** stratify so every intent has a meaningful floor (e.g. ≥30 examples
  each). Backfill genuinely rare intents (extension, adversarial) with a few realistic
  synthetic examples and clearly tag them as synthetic so we can measure real-vs-synthetic
  performance separately.
- **Labeling:** two annotators + a tiebreaker; track inter-annotator agreement. Disagreements
  are usually genuinely-ambiguous messages and belong in the `needs_human` bucket.

## 2. Metrics — and why overall accuracy is misleading here
- **Measure per-intent precision, recall, and F1, plus a full confusion matrix** — not a
  single accuracy number.
- **Why accuracy misleads:** the intent distribution is heavily imbalanced (most messages
  are booking/payment; maintenance and adversarial are rare). A model that always predicts
  the majority intent scores high accuracy while completely missing the rare-but-critical
  ones. Missing a `maintenance_request` (a leak, a broken AC) is far more costly than
  mislabeling a booking question, but accuracy treats every error equally.
- **Additional signals:** recall on `maintenance_request` (safety-critical), precision on
  `out_of_scope` (don't auto-dismiss real guests), confidence calibration (does confidence
  correlate with correctness?), and the `needs_human` trigger rate (escalates the right
  cases without flooding agents).

## 3. Regression — knowing a prompt/model change didn't make it worse
- Keep a **frozen, versioned eval set** and run it on every prompt edit or model swap.
- **Gate in CI:** compare per-intent F1 against the current production baseline; fail the
  build if any intent regresses beyond a small tolerance — this stops a fix for one intent
  silently breaking another.
- **Report deltas, not just absolutes:** a side-by-side table (old vs new per intent) plus
  the changed examples makes regressions obvious in review.
- Pin model version and decoding params (temperature, seed where supported) so the only
  variable is the change under test.

## 4. Production monitoring — degradation signals *before* a user complains
- **Confidence-distribution drift:** a rising share of low-confidence outputs means inputs
  have shifted away from what the prompt handles.
- **`needs_human` / `unknown` rate climbing:** the model is increasingly unsure → new slang,
  new topics, or a degraded model.
- **Intent mix drift vs. a rolling baseline:** e.g. `maintenance_request` suddenly doubling,
  or one intent collapsing to ~0 (often a parsing/format break).
- **Operational health:** p50/p95 latency, LLM timeout rate, and **retry/validation-failure
  rate** from Part B (malformed-output rate creeping up = upstream model trouble).
- **Sampled human review / thumbs-down from agents** feeding back into the eval set, closing
  the loop. Alert on these leading indicators so we react before guests do.
