# SMARD data

`smard_hourly.csv`: hourly values for calendar year 2025 (Europe/Berlin), timestamps in UTC.

- Source: Bundesnetzagentur | SMARD.de, https://www.smard.de
- License: CC BY 4.0, https://creativecommons.org/licenses/by/4.0/
- Fetched once with `scripts/fetch_smard.py --year 2025`, values stored unchanged
  (prices rounded to cents, energy to whole MWh).

Columns: `price_eur_mwh` (day-ahead, bidding zone DE-LU), `load_mwh` (grid load) and
generation per source in MWh. The series "sonstige Konventionelle" is not included:
SMARD ends it in early 2024.
