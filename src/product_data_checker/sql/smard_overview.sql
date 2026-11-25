-- Year KPIs from SMARD hourly data (Bundesnetzagentur | SMARD.de, CC BY 4.0).
-- Renewable share is measured against grid load, as SMARD reports it.
SELECT
    min(ts_local)::DATE                                          AS first_day,
    max(ts_local)::DATE                                          AS last_day,
    count(*)                                                     AS hours,
    round(avg(price_eur_mwh), 2)                                 AS avg_price_eur_mwh,
    round(median(price_eur_mwh), 2)                              AS median_price_eur_mwh,
    count(*) FILTER (WHERE price_eur_mwh < 0)                    AS negative_price_hours,
    round(min(price_eur_mwh), 2)                                 AS min_price_eur_mwh,
    round(max(price_eur_mwh), 2)                                 AS max_price_eur_mwh,
    round(100.0 * sum(renewable_mwh) / sum(load_mwh), 1)         AS renewable_share_pct,
    round(100.0 * sum(solar_mwh) / sum(load_mwh), 1)             AS solar_share_pct,
    round(sum(load_mwh) / 1e6, 1)                                AS load_twh
FROM smard;
