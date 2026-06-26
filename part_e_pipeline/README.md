# Part E — Data Pipeline Design (Dagster)

**Goal:** a daily pipeline that ingests yesterday's bookings → enriches each with the
LLM categorizer → loads into ClickHouse for reporting.

## Asset structure & daily partitioning (a)
Model the flow as three **daily-partitioned assets**, one partition per calendar day,
so each day is computed, retried, and back-filled independently:

```
daily_partitions = DailyPartitionsDefinition(start_date="2026-01-01")

@asset(partitions_def=daily_partitions)
def raw_bookings(context):
    day = context.partition_key                       # e.g. "2026-06-25"
    return read_mysql(
        "SELECT * FROM bookings "
        "WHERE created_at >= %(day)s AND created_at < %(day)s + INTERVAL 1 DAY",
        day=day,
    )

@asset(partitions_def=daily_partitions)
def enriched_bookings(context, raw_bookings):
    # LLM categorize each row (see partial-failure handling below)
    ...

@asset(partitions_def=daily_partitions)
def clickhouse_report(context, enriched_bookings):
    # idempotent load (see below)
    ...
```

A daily schedule materializes yesterday's partition each morning. Partitions also make
backfills trivial (re-run a date range) and give per-day observability in the Dagster UI.

## Idempotency — re-running yesterday must not double-load (b)
The load must be **deterministic per partition**, never blind appends:
- **Delete-then-insert by partition key:** before loading day `D`, delete existing
  ClickHouse rows for `event_date = D`, then insert. Re-running replaces, never duplicates.
  In ClickHouse: `ALTER TABLE report DELETE WHERE event_date = {D}` (or drop the
  `PARTITION BY toDate(event_date)` partition) then `INSERT`.
- **Or use a `ReplacingMergeTree`** keyed by `(booking_id)` so re-inserted rows collapse to
  the latest version on merge — combined with a deterministic `version` column.
- Carry the **partition key into the row** (`event_date = D`) so the unit of idempotency is
  explicit and the delete is a cheap partition operation.

## Partial failure — LLM fails on 5% of rows (c)
The 95% must still land; the 5% must not be silently dropped:
- **Per-row try/except** around the LLM call. On failure (timeout / malformed after the
  retry budget from Part B), don't fail the whole asset.
- **Route failures to a dead-letter asset/table** (`enrichment_failures` with the raw row +
  error + attempt count). Load the 95% successes to ClickHouse normally; tag failed rows
  with `category = NULL` / `enrichment_status = 'failed'` if they must still appear.
- **Emit metadata** (`success_count`, `failure_count`, `failure_rate`) on the asset
  materialization, and a **Dagster asset check that warns/fails if `failure_rate` exceeds a
  threshold** (e.g. >10%) — a 5% miss is tolerable, a spike is not.
- A small **retry asset** can re-process the dead-letter table on the next run, so transient
  failures self-heal without re-running the whole day.

## Detecting bad upstream data before poisoning the report (d)
Put **data-quality asset checks between ingest and load** that *block* the load on failure:
- **Row-count sanity:** compare today's `raw_bookings` count against the trailing 7–14 day
  average; fail if it deviates beyond a band (e.g. drops >40% or doubles). This directly
  catches the "row count suddenly halves" case.
- **Null-rate guards:** assert critical fields (`total_amount`, `property_type`,
  `checkin_date`) stay under a max null rate; a field going 100% null trips it — exactly the
  Part C3 ingestion-bug signature.
- **Value/domain checks:** `status` and `currency` ∈ known sets; `total_amount > 0`;
  `checkout_date > checkin_date`. A new partner emitting `USD` amounts or a new status string
  would fail here (catching the Part C3 GMV-drop class of bug at the source).
- **Wire as Dagster `@asset_check`** with `blocking=True` so a failed check **stops the
  pipeline before `clickhouse_report` runs** — the stale-but-correct report is kept rather
  than overwritten with poisoned data. Alert to Slack/PagerDuty on failure.

```python
@asset_check(asset=raw_bookings, blocking=True)
def row_count_not_collapsed(context, raw_bookings):
    today = len(raw_bookings)
    baseline = trailing_avg_count(context.partition_key, days=14)
    ok = today >= 0.6 * baseline                      # no >40% drop
    return AssetCheckResult(passed=ok, metadata={"today": today, "baseline": baseline})
```

### Summary
Daily-partitioned assets give isolation + cheap backfills; idempotency comes from
delete-then-insert per partition (or `ReplacingMergeTree`); partial failures are
dead-lettered so the 95% still loads; and blocking quality checks on row count, null rate,
and value domains stop bad upstream data before it reaches the report.
