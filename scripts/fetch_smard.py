"""Fetch one year of hourly German electricity market data from SMARD once.

Source: Bundesnetzagentur | SMARD.de, licensed CC BY 4.0
(https://www.smard.de/home/datennutzung). The result is committed as a small CSV
so the dashboard and all tests run offline. Run again only to refresh the file:

    uv run python scripts/fetch_smard.py --year 2025
"""

from __future__ import annotations

import argparse
import csv
import json
import time
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

BASE = "https://www.smard.de/app/chart_data"
BERLIN = ZoneInfo("Europe/Berlin")

# filter id -> (column name, region)
SERIES: dict[int, tuple[str, str]] = {
    4169: ("price_eur_mwh", "DE-LU"),
    410: ("load_mwh", "DE"),
    4068: ("solar_mwh", "DE"),
    4067: ("wind_onshore_mwh", "DE"),
    1225: ("wind_offshore_mwh", "DE"),
    4066: ("biomass_mwh", "DE"),
    1226: ("hydro_mwh", "DE"),
    1228: ("other_renewable_mwh", "DE"),
    1223: ("lignite_mwh", "DE"),
    4069: ("hard_coal_mwh", "DE"),
    4071: ("natural_gas_mwh", "DE"),
    4070: ("pumped_storage_mwh", "DE"),
}


def _get_json(url: str) -> dict:
    if not url.startswith(BASE):
        raise ValueError(f"unexpected host: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "product-data-checker/0.1"})
    with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310 (fixed https host)
        raw = resp.read(5_000_000)
    return json.loads(raw)


def fetch_year(year: int) -> dict[int, dict[str, float | None]]:
    start = datetime(year, 1, 1, tzinfo=BERLIN).timestamp() * 1000
    end = datetime(year + 1, 1, 1, tzinfo=BERLIN).timestamp() * 1000
    week_ms = 7 * 24 * 3600 * 1000
    rows: dict[int, dict[str, float | None]] = {}
    for filter_id, (column, region) in SERIES.items():
        index = _get_json(f"{BASE}/{filter_id}/{region}/index_hour.json")["timestamps"]
        chunks = [t for t in index if t + week_ms > start and t < end]
        for ts in chunks:
            url = f"{BASE}/{filter_id}/{region}/{filter_id}_{region}_hour_{ts}.json"
            for point_ts, value in _get_json(url)["series"]:
                if start <= point_ts < end:
                    rows.setdefault(point_ts, {})[column] = value
            time.sleep(0.15)
        print(f"{column}: {len(chunks)} chunks")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2025)
    parser.add_argument("--out", type=Path, default=Path("data/smard/smard_hourly.csv"))
    args = parser.parse_args()

    rows = fetch_year(args.year)
    columns = [name for name, _ in SERIES.values()]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["timestamp_utc", *columns])
        for ts in sorted(rows):
            stamp = datetime.fromtimestamp(ts / 1000, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
            values = rows[ts]
            out = []
            for col in columns:
                v = values.get(col)
                if v is None:
                    out.append("")
                elif col == "price_eur_mwh":
                    out.append(f"{v:.2f}")
                else:
                    out.append(f"{v:.0f}")
            writer.writerow([stamp, *out])
    print(f"wrote {len(rows)} rows to {args.out}")


if __name__ == "__main__":
    main()
