-- Monthly KPIs: price level, renewable share and hours with negative prices.
-- The sums (hours, price sum, MWh) let the dashboard combine months into a quarter
-- exactly: the average of a quarter is sum(price_sum) / sum(hours), not an average of
-- monthly averages.
SELECT
    date_trunc('month', ts_local)::DATE                          AS month,
    round(avg(price_eur_mwh), 2)                                 AS avg_price_eur_mwh,
    round(100.0 * sum(renewable_mwh) / sum(load_mwh), 1)         AS renewable_share_pct,
    round(100.0 * sum(solar_mwh) / sum(load_mwh), 1)             AS solar_share_pct,
    round(100.0 * sum(wind_onshore_mwh + wind_offshore_mwh) / sum(load_mwh), 1) AS wind_share_pct,
    count(*) FILTER (WHERE price_eur_mwh < 0)                    AS negative_price_hours,
    count(*)                                                     AS hours,
    round(sum(price_eur_mwh), 2)                                 AS price_sum,
    round(sum(load_mwh))                                         AS load_mwh,
    round(sum(renewable_mwh))                                    AS renewable_mwh,
    round(sum(solar_mwh))                                        AS solar_mwh,
    round(sum(wind_onshore_mwh + wind_offshore_mwh))             AS wind_mwh
FROM smard
GROUP BY 1
ORDER BY 1;
