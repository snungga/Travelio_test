"""Runnable demo for C1 — average nightly revenue per property type.

Uses Python's built-in `sqlite3` (no install, no server). It seeds the same data
as appendix2_bookings_schema_and_seed.sql, then runs the C1 query translated to
SQLite dialect and prints the result.

Why a translated query? The canonical answer in
`c1_mysql_avg_nightly_revenue.sql` is MySQL (DATEDIFF / INTERVAL). SQLite has no
DATEDIFF or INTERVAL, so here:
    DATEDIFF(checkout, checkin)   ->  julianday(checkout) - julianday(checkin)
    NOW() - INTERVAL 90 DAY       ->  datetime('now', '-90 days')
The logic is identical; only the date built-ins differ.

Run:  python part_c_databases/demo/run_c1_sqlite.py
"""

from __future__ import annotations

import sqlite3

SCHEMA = """
CREATE TABLE bookings (
    id INTEGER PRIMARY KEY,
    property_id INTEGER,
    property_type TEXT,
    checkin_date TEXT,
    checkout_date TEXT,
    status TEXT,
    total_amount REAL,
    currency TEXT,
    source TEXT,
    created_at TEXT
);
"""

# Same rows as the .sql seed, with dates expressed via SQLite date() so they fall
# inside / outside the 90-day window deterministically.
SEED = """
INSERT INTO bookings VALUES
 (1,101,'2br',   date('now','-10 days'),date('now','-7 days'), 'completed',3000000,'IDR','direct',   datetime('now','-10 days')),
 (2,102,'2br',   date('now','-20 days'),date('now','-18 days'),'completed',2000000,'IDR','ota',      datetime('now','-20 days')),
 (3,103,'1br',   date('now','-30 days'),date('now','-26 days'),'completed',4000000,'IDR','direct',   datetime('now','-30 days')),
 (4,104,'studio',date('now','-5 days'), date('now','-2 days'), 'completed',1500000,'IDR','direct',   datetime('now','-5 days')),
 (5,105,'2br',   date('now','-8 days'), date('now','-5 days'), 'cancelled',9000000,'IDR','direct',   datetime('now','-8 days')),
 (6,106,'1br',   date('now','-200 days'),date('now','-196 days'),'completed',8000000,'IDR','direct', datetime('now','-200 days')),
 (7,107,'2br',   date('now','-3 days'), date('now','-1 days'), 'completed',     130,'USD','partner_x',datetime('now','-3 days'));
"""

# C1 query, SQLite dialect. `nights` is julianday difference (whole days here).
C1_QUERY = """
SELECT
    property_type,
    AVG(total_amount / NULLIF(julianday(checkout_date) - julianday(checkin_date), 0))
        AS avg_nightly_revenue,
    COUNT(*) AS completed_bookings
FROM bookings
WHERE status = 'completed'
  AND created_at >= datetime('now', '-90 days')
  AND (julianday(checkout_date) - julianday(checkin_date)) > 0
GROUP BY property_type
ORDER BY avg_nightly_revenue DESC;
"""


def main() -> None:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    conn.executescript(SEED)

    rows = conn.execute(C1_QUERY).fetchall()

    print("C1 - average nightly revenue per property type (completed, last 90 days)\n")
    print(f"{'property_type':<14}{'avg_nightly_revenue':>22}{'completed_bookings':>22}")
    print("-" * 58)
    for property_type, avg_revenue, count in rows:
        print(f"{property_type:<14}{avg_revenue:>22,.2f}{count:>22}")

    print(
        "\nNote: the 2br average is dragged down because booking #7 is a partner_x "
        "row in USD (130) summed alongside IDR amounts - the C3 currency trap. "
        "Cancelled (#5) and the >90-day row (#6) are correctly excluded."
    )
    conn.close()


if __name__ == "__main__":
    main()
