-- Usable share per supplier and field: the heatmap in the dashboard.
SELECT
    supplier,
    field_label AS field,
    field_order,
    round(100.0 * avg(CASE WHEN usable THEN 1 ELSE 0 END), 1) AS usable_pct
FROM field_checks
GROUP BY supplier, field_label, field_order
ORDER BY supplier, field_order;
