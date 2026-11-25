-- Price by hourly renewable share (buckets of 10 points): the more wind and sun cover
-- the load, the lower the price. Relevant for anyone selling local solar power.
SELECT
    least(floor(100.0 * renewable_mwh / load_mwh / 10) * 10, 100)::INTEGER AS share_bucket_pct,
    count(*)                                                   AS hours,
    round(avg(price_eur_mwh), 2)                               AS avg_price_eur_mwh,
    round(100.0 * count(*) FILTER (WHERE price_eur_mwh < 0) / count(*), 1) AS negative_share_pct
FROM smard
WHERE load_mwh > 0
GROUP BY 1
ORDER BY 1;
