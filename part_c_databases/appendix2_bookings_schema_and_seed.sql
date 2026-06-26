-- Appendix 2 — Sample data (MySQL)
-- The `bookings` DDL is taken verbatim from the assessment PDF; the INSERTs are
-- a small, illustrative seed so the C1 query can be run and eyeballed.
--
-- Run order: this file first (create + seed), then c1_mysql_avg_nightly_revenue.sql.
-- (A runnable, no-install version of this lives in demo/run_c1_sqlite.py.)

-- ---- Schema (verbatim from Appendix 2) --------------------------------------
CREATE TABLE bookings (
    id BIGINT PRIMARY KEY,
    property_id BIGINT,
    property_type VARCHAR(32),    -- 'studio','1br','2br','3br'
    checkin_date DATE,
    checkout_date DATE,
    status VARCHAR(16),           -- 'completed','cancelled','refunded','pending'
    total_amount DECIMAL(15,2),
    currency CHAR(3),             -- 'IDR','USD'
    source VARCHAR(32),           -- 'direct','ota','partner_x'  (new partner here)
    created_at DATETIME
);

-- ---- Seed -------------------------------------------------------------------
-- Dates are written relative to "now" so they fall inside the last-90-days
-- window. Adjust if you seed a real MySQL instance with fixed dates.
--
-- The rows are chosen so the per-night math is easy to verify by hand:
--   2br : (3,000,000 / 3 nights) and (2,000,000 / 2 nights) -> both 1,000,000
--   1br : (4,000,000 / 4 nights)                            -> 1,000,000
--   studio: (1,500,000 / 3 nights)                          ->   500,000
-- Plus rows that must be EXCLUDED (cancelled, older than 90 days) and one
-- partner_x row in USD that demonstrates the C3 currency-mixing trap.

INSERT INTO bookings VALUES
-- completed, in-window, IDR  (counted)
(1, 101, '2br',    DATE_SUB(CURDATE(), INTERVAL 10 DAY), DATE_SUB(CURDATE(), INTERVAL 7 DAY),  'completed', 3000000.00, 'IDR', 'direct',    NOW() - INTERVAL 10 DAY),
(2, 102, '2br',    DATE_SUB(CURDATE(), INTERVAL 20 DAY), DATE_SUB(CURDATE(), INTERVAL 18 DAY), 'completed', 2000000.00, 'IDR', 'ota',       NOW() - INTERVAL 20 DAY),
(3, 103, '1br',    DATE_SUB(CURDATE(), INTERVAL 30 DAY), DATE_SUB(CURDATE(), INTERVAL 26 DAY), 'completed', 4000000.00, 'IDR', 'direct',    NOW() - INTERVAL 30 DAY),
(4, 104, 'studio', DATE_SUB(CURDATE(), INTERVAL 5 DAY),  DATE_SUB(CURDATE(), INTERVAL 2 DAY),  'completed', 1500000.00, 'IDR', 'direct',    NOW() - INTERVAL 5 DAY),
-- cancelled -> excluded by status filter
(5, 105, '2br',    DATE_SUB(CURDATE(), INTERVAL 8 DAY),  DATE_SUB(CURDATE(), INTERVAL 5 DAY),  'cancelled', 9000000.00, 'IDR', 'direct',    NOW() - INTERVAL 8 DAY),
-- completed but older than 90 days -> excluded by date filter
(6, 106, '1br',    DATE_SUB(CURDATE(), INTERVAL 200 DAY),DATE_SUB(CURDATE(), INTERVAL 196 DAY),'completed', 8000000.00, 'IDR', 'direct',    NOW() - INTERVAL 200 DAY),
-- NEW PARTNER, completed, but amount is in USD (~tens, not millions): the C3 trap.
-- It is counted by C1 as-written and visibly drags the 2br average down, which is
-- the whole point of the currency caveat noted in the query.
(7, 107, '2br',    DATE_SUB(CURDATE(), INTERVAL 3 DAY),  DATE_SUB(CURDATE(), INTERVAL 1 DAY),  'completed',     130.00, 'USD', 'partner_x', NOW() - INTERVAL 3 DAY);
