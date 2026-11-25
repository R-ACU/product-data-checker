-- Daily price line: average, lowest and highest hourly price per local day, and the
-- renewable share of that day's load.
SELECT
    ts_local::DATE                                               AS day,
    round(avg(price_eur_mwh), 2)                                 AS avg_price_eur_mwh,
    round(min(price_eur_mwh), 2)                                 AS min_price_eur_mwh,
    round(max(price_eur_mwh), 2)                                 AS max_price_eur_mwh,
    round(100.0 * sum(renewable_mwh) / sum(load_mwh), 1)         AS renewable_share_pct,
    count(*) FILTER (WHERE price_eur_mwh < 0)                    AS negative_price_hours
FROM smard
GROUP BY 1
ORDER BY 1;
