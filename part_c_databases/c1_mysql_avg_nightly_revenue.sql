-- C1 — MySQL
-- Average nightly revenue per property type, for COMPLETED bookings
-- created in the last 90 days.
--
-- "Nightly revenue" = total_amount / number of nights, where
-- number of nights = checkout_date - checkin_date (in days).
--
-- Notes / assumptions:
--  * We average the per-booking nightly revenue (AVG of the ratio), which the
--    question's wording asks for. (If the business instead wants total revenue /
--    total nights, that is SUM(total_amount) / SUM(nights) — see the commented
--    variant at the bottom.)
--  * DATEDIFF gives whole nights; we guard against zero/negative night spans
--    with NULLIF so a bad row can't divide-by-zero — those rows are excluded
--    from the average rather than crashing the query.
--  * total_amount mixes currencies (IDR/USD). This query intentionally does NOT
--    convert currency; in production you'd normalize to a base currency first
--    (this is exactly the trap behind the Part C3 GMV drop).

SELECT
    property_type,
    AVG(total_amount / NULLIF(DATEDIFF(checkout_date, checkin_date), 0))
        AS avg_nightly_revenue,
    COUNT(*) AS completed_bookings
FROM bookings
WHERE status = 'completed'
  AND created_at >= NOW() - INTERVAL 90 DAY
  AND DATEDIFF(checkout_date, checkin_date) > 0
GROUP BY property_type
ORDER BY avg_nightly_revenue DESC;


-- Alternative interpretation — pooled nightly revenue (total revenue / total nights):
--
-- SELECT
--     property_type,
--     SUM(total_amount) / SUM(DATEDIFF(checkout_date, checkin_date))
--         AS pooled_nightly_revenue
-- FROM bookings
-- WHERE status = 'completed'
--   AND created_at >= NOW() - INTERVAL 90 DAY
--   AND DATEDIFF(checkout_date, checkin_date) > 0
-- GROUP BY property_type;
