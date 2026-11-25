-- Headline numbers of one run.
-- articles: one row per supplier line; field_checks: one row per mandatory field per article.
WITH per_article AS (
    SELECT
        row,
        avg(CASE WHEN filled_raw THEN 1 ELSE 0 END) AS filled_share,
        avg(CASE WHEN usable THEN 1 ELSE 0 END)     AS usable_share
    FROM field_checks
    GROUP BY row
)
SELECT
    count(*)                                                    AS articles,
    count(*) FILTER (WHERE a.status = 'freigegeben')            AS released,
    count(*) FILTER (WHERE a.status = 'pruefen')                AS to_review,
    round(100.0 * count(*) FILTER (WHERE a.status = 'freigegeben') / count(*), 1)
                                                                AS release_rate_pct,
    round(100.0 * avg(p.filled_share), 1)                       AS filled_before_pct,
    round(100.0 * avg(p.usable_share), 1)                       AS usable_before_pct,
    round(100.0 * avg(p.usable_share) FILTER (WHERE a.status = 'freigegeben'), 1)
                                                                AS usable_released_pct,
    round(100.0 * count(*) FILTER (WHERE p.usable_share = 1) / count(*), 1)
                                                                AS complete_articles_before_pct
FROM articles a
JOIN per_article p USING (row);
