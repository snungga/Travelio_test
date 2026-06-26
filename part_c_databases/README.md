# Part C — Databases & Data Debugging

| Item | Canonical answer | Sample data (Appendix 2) | Runnable demo (no DB server) |
|------|------------------|--------------------------|------------------------------|
| C1 (MySQL) | [`c1_mysql_avg_nightly_revenue.sql`](c1_mysql_avg_nightly_revenue.sql) | [`appendix2_bookings_schema_and_seed.sql`](appendix2_bookings_schema_and_seed.sql) | [`demo/run_c1_sqlite.py`](demo/run_c1_sqlite.py) |
| C2 (MongoDB) | [`c2_mongo_messages_per_intent_per_day.js`](c2_mongo_messages_per_intent_per_day.js) | [`appendix2_messages_seed.js`](appendix2_messages_seed.js) | [`demo/run_c2_mongomock.py`](demo/run_c2_mongomock.py) |
| C3 / C4 | reasoning below | — | — |

## Running the demos
The `.sql` / `.js` files are the deliverables (paste into MySQL / `mongosh`). The
`demo/` scripts let you **run C1 and C2 in pure Python without any DB server**, so
the output can be verified directly.

```bash
# C1 — uses Python's built-in sqlite3, nothing to install
python part_c_databases/demo/run_c1_sqlite.py

# C2 — needs mongomock (in-memory Mongo)
pip install -r part_c_databases/demo/requirements.txt
python part_c_databases/demo/run_c2_mongomock.py
```

Expected highlights: C1 shows `2br` averaging **~666,688** instead of 1,000,000 —
because seed booking #7 is a `partner_x` row in **USD** summed alongside IDR, the
exact C3 currency trap made visible. C2 buckets messages by day/intent for the last
7 days and excludes a 10-day-old message.

> Dialect notes: the C1 demo translates MySQL `DATEDIFF`/`INTERVAL` to SQLite
> `julianday()`/`date('now', ...)`; the C2 demo uses `$dateToString` because
> mongomock doesn't implement `$dateTrunc` (equivalent for daily buckets). The
> canonical files keep the idiomatic MySQL / MongoDB forms.

---

## C3 — Root cause: GMV dropped ~40% but booking count is normal

**Key facts:** GMV fell ~40% starting last Tuesday; booking *count* is unchanged;
nothing deployed to the booking service; last Tuesday a teammate onboarded a **new
channel partner** whose bookings flow into the same `bookings` table via an
ingestion job. Since count is flat but the *sum of value* dropped, the problem is
in the **`total_amount` (or its currency) of the new rows**, not in volume.

### Top 3 hypotheses (ranked)

**1. Currency mismatch — partner rows are in USD but GMV sums raw `total_amount` as IDR.**
The new `source='partner_x'` rows carry `currency='USD'` (or amounts already in a
different unit), but the GMV report `SUM(total_amount)` without converting to a base
currency. A USD amount (~tens) replacing an IDR amount (~millions) per booking would
crater the total while keeping the count identical.
- *Confirm/kill:*
  ```sql
  SELECT source, currency, COUNT(*), AVG(total_amount), SUM(total_amount)
  FROM bookings
  WHERE created_at >= NOW() - INTERVAL 14 DAY
  GROUP BY source, currency;
  ```
  If `partner_x` rows are `USD` and/or their `AVG(total_amount)` is orders of
  magnitude smaller than `direct`/`ota`, this is confirmed. Kill it if all sources
  share one currency and similar averages.

**2. Null / zero `total_amount` from a field-mapping bug in the ingestion job.**
The partner's payload maps to a different field name (e.g. `amount` vs `gross`), so
`total_amount` lands `NULL` or `0`. Counts stay normal (rows exist) but contribute
nothing to GMV.
- *Confirm/kill:*
  ```sql
  SELECT source,
         SUM(total_amount IS NULL OR total_amount = 0) AS zero_or_null,
         COUNT(*) AS total
  FROM bookings
  WHERE created_at >= NOW() - INTERVAL 14 DAY
  GROUP BY source;
  ```
  A high `zero_or_null` ratio concentrated in `partner_x` confirms it.

**3. Status mismatch — partner bookings land in a non-`completed` status the GMV report filters out.**
If GMV only counts `status='completed'` and the partner's rows arrive as `pending`
(or a new status string), they're silently excluded from value but still counted in
a raw booking count.
- *Confirm/kill:*
  ```sql
  SELECT source, status, COUNT(*)
  FROM bookings
  WHERE created_at >= NOW() - INTERVAL 14 DAY
  GROUP BY source, status;
  ```
  If `partner_x` rows are overwhelmingly non-`completed` (or an unexpected status),
  confirmed. Cross-check the exact `WHERE` clause of the GMV report.

### Single most likely root cause
**Currency not normalized for the new `partner_x` rows (Hypothesis 1).** It best
explains the *magnitude* (a ~40% drop is consistent with one new channel's bookings
being valued in USD instead of IDR) and the timing (exactly when the partner was
onboarded), with no booking-service deploy involved. Fix: normalize all amounts to a
base currency (store `amount_idr` via an FX step in ingestion) and make the GMV
report currency-aware; backfill the affected rows.

---

## C4 — ClickHouse: reporting query got slow past tens of millions of rows

```sql
SELECT toDate(created_at) d, count()
FROM events
WHERE event_type = 'booking'
GROUP BY d
```
**Table `ORDER BY` key is `(id)`.**

**Likely cause.** In ClickHouse (MergeTree) the `ORDER BY` key *is* the primary/sort
key that drives the sparse index and data layout. With `ORDER BY (id)`, the table is
sorted by `id`, so a query that filters on `event_type` and groups by
`toDate(created_at)` has **no useful index** — ClickHouse must full-scan and read the
`event_type` and `created_at` columns across every granule. That scales linearly with
table size, hence the slowdown past tens of millions of rows.

**What I'd change.**
- **Reorder the sort key to match access patterns**, putting the filter column first
  and time second:
  ```sql
  ORDER BY (event_type, created_at)
  ```
  Now `event_type = 'booking'` prunes granules via the primary index and the rows are
  already time-clustered for the daily group-by.
- **Add a monthly partition** so date-bounded reports prune whole partitions:
  ```sql
  PARTITION BY toYYYYMM(created_at)
  ```
- Because the sort key can't be changed in place, create a **new table** with the
  better `ORDER BY`/`PARTITION BY` and backfill via `INSERT INTO new SELECT FROM old`
  (or an `ALTER TABLE ... MODIFY` into a fresh table), then swap.
- For a fixed daily-count report at scale, a **materialized view** keyed by
  `(event_type, day)` with a `SummingMergeTree`/`AggregatingMergeTree` target turns
  the query into a tiny pre-aggregated lookup.
