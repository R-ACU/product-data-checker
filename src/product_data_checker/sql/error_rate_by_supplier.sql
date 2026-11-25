-- Error rate per supplier: share of articles with at least one blocking issue,
-- plus the reason that hits this supplier most often. Sorted worst first, because
-- this list decides whom to call about their data quality.
WITH blocking AS (
    SELECT row, supplier, label
    FROM issues
    WHERE severity = 'blockierend'
),
top_reason AS (
    SELECT supplier, label, count(*) AS n,
           row_number() OVER (PARTITION BY supplier ORDER BY count(*) DESC, label) AS rk
    FROM blocking
    GROUP BY supplier, label
)
SELECT
    a.supplier,
    count(DISTINCT a.row)                                             AS articles,
    count(DISTINCT b.row)                                             AS blocked,
    round(100.0 * count(DISTINCT b.row) / count(DISTINCT a.row), 1)   AS error_rate_pct,
    any_value(t.label)                                                AS top_reason,
    coalesce(any_value(t.n), 0)                                       AS top_reason_count
FROM articles a
LEFT JOIN blocking b ON b.row = a.row
LEFT JOIN top_reason t ON t.supplier = a.supplier AND t.rk = 1
GROUP BY a.supplier
ORDER BY error_rate_pct DESC, a.supplier;
