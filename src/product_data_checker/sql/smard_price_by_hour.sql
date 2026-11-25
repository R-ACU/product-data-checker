-- Average day-ahead price per month and local hour of day (heatmap).
SELECT
    month(ts_local)                    AS month,
    hour(ts_local)                     AS hour,
    round(avg(price_eur_mwh), 1)       AS avg_price_eur_mwh,
    count(*) FILTER (WHERE price_eur_mwh < 0) AS negative_hours
FROM smard
GROUP BY 1, 2
ORDER BY 1, 2;
