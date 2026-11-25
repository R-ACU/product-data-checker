"""KPIs in SQL. Python prepares tidy tables, DuckDB does every aggregation.

The SQL lives in ``sql/*.sql`` so it can be read, reviewed and shown in the dashboard
as it is, without Python around it.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import duckdb
import pandas as pd

from . import config
from .issues import BLOCKING
from .pipeline import RunResult
from .units import is_empty

QUALITY_QUERIES = [
    "quality_overview",
    "error_rate_by_supplier",
    "reasons",
    "completeness_by_field",
    "completeness_matrix",
]
SMARD_QUERIES = [
    "smard_overview",
    "smard_monthly",
    "smard_daily",
    "smard_price_by_hour",
    "smard_price_by_renewable_share",
]


@dataclass
class QueryResult:
    name: str
    sql: str
    frame: pd.DataFrame


def load_sql(name: str) -> str:
    return (config.SQL_DIR / f"{name}.sql").read_text(encoding="utf-8")


def _value_of(product, field: str):
    return {
        "sku": product.sku,
        "supplier": product.supplier,
        "ean": product.ean,
        "name": product.name,
        "brand": product.brand,
        "category": product.category,
        "length": product.length_mm,
        "weight": product.weight_g,
        "price": product.price_eur,
        "nominal": product.nominal_mm,
        "pieces": product.pieces,
    }[field]


def build_tables(result: RunResult) -> dict[str, pd.DataFrame]:
    blocked = result.blocking_rows()
    articles = pd.DataFrame(
        [
            {
                "row": p.row,
                "sku": p.sku,
                "supplier": p.supplier or "(ohne Lieferant)",
                "category": p.category or None,
                "status": "pruefen" if p.row in blocked else "freigegeben",
            }
            for p in result.products
        ],
        columns=["row", "sku", "supplier", "category", "status"],
    )
    order = {f: i for i, f in enumerate(config.REQUIRED_FIELDS + ["nominal", "pieces"])}
    checks = []
    for p in result.products:
        required = list(config.REQUIRED_FIELDS)
        required += config.CATEGORIES.get(p.category, {}).get("requires", [])
        for f in required:
            value = _value_of(p, f)
            checks.append(
                {
                    "row": p.row,
                    "supplier": p.supplier or "(ohne Lieferant)",
                    "field": f,
                    "field_label": config.FIELD_LABELS[f],
                    "field_order": order[f],
                    "filled_raw": not is_empty(p.raw.get(f, "")),
                    "usable": value not in (None, ""),
                }
            )
    issues = result.issues_frame()
    issues["supplier"] = issues["supplier"].replace("", "(ohne Lieferant)")
    return {"articles": articles, "field_checks": pd.DataFrame(checks), "issues": issues}


def quality_metrics(result: RunResult) -> dict[str, QueryResult]:
    tables = build_tables(result)
    con = duckdb.connect(":memory:")
    try:
        for name, frame in tables.items():
            con.register(name, frame)
        return {q: QueryResult(q, load_sql(q), con.sql(load_sql(q)).df()) for q in QUALITY_QUERIES}
    finally:
        con.close()


def load_smard(con: duckdb.DuckDBPyConnection, csv_path: Path) -> None:
    """Create the ``smard`` view: typed columns plus local time and renewable sum."""
    con.execute(
        """
        CREATE OR REPLACE TABLE smard AS
        SELECT
            timezone('Europe/Berlin', timestamp_utc::TIMESTAMPTZ) AS ts_local,
            * EXCLUDE (timestamp_utc),
            solar_mwh + wind_onshore_mwh + wind_offshore_mwh + biomass_mwh
                + hydro_mwh + other_renewable_mwh AS renewable_mwh
        FROM read_csv(?, header = true, auto_detect = false, columns = {
            'timestamp_utc': 'VARCHAR', 'price_eur_mwh': 'DOUBLE', 'load_mwh': 'DOUBLE',
            'solar_mwh': 'DOUBLE', 'wind_onshore_mwh': 'DOUBLE', 'wind_offshore_mwh': 'DOUBLE',
            'biomass_mwh': 'DOUBLE', 'hydro_mwh': 'DOUBLE', 'other_renewable_mwh': 'DOUBLE',
            'lignite_mwh': 'DOUBLE', 'hard_coal_mwh': 'DOUBLE', 'natural_gas_mwh': 'DOUBLE',
            'pumped_storage_mwh': 'DOUBLE'})
        WHERE price_eur_mwh IS NOT NULL AND load_mwh IS NOT NULL
        """,
        [str(csv_path)],
    )


def smard_metrics(csv_path: Path) -> dict[str, QueryResult]:
    con = duckdb.connect(":memory:")
    try:
        load_smard(con, csv_path)
        return {q: QueryResult(q, load_sql(q), con.sql(load_sql(q)).df()) for q in SMARD_QUERIES}
    finally:
        con.close()


def blocking_count(result: RunResult) -> int:
    return sum(1 for i in result.issues if i.severity == BLOCKING)
