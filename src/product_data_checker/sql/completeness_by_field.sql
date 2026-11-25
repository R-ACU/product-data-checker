-- Completeness per mandatory field: filled at all, and filled with a usable value
-- (parsable unit, valid EAN, known category). The gap between both columns is the
-- work the checker does automatically or sends back to the supplier.
SELECT
    field_label                                         AS field,
    count(*)                                            AS required_in,
    round(100.0 * avg(CASE WHEN filled_raw THEN 1 ELSE 0 END), 1) AS filled_pct,
    round(100.0 * avg(CASE WHEN usable THEN 1 ELSE 0 END), 1)     AS usable_pct
FROM field_checks
GROUP BY field_label, field_order
ORDER BY field_order;
