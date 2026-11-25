-- Why articles go back to review. One article can have several reasons.
SELECT
    label                                                          AS reason,
    code,
    count(*)                                                       AS findings,
    count(DISTINCT row)                                            AS articles,
    round(100.0 * count(DISTINCT row) / (SELECT count(*) FROM articles), 1) AS share_of_all_pct,
    CASE WHEN code LIKE 'TEXT_%' THEN 'Text' ELSE 'Daten' END      AS stage
FROM issues
WHERE severity = 'blockierend'
GROUP BY label, code
ORDER BY articles DESC, reason;
