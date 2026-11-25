"""The SQL results are cross-checked against an independent pandas calculation."""

import pandas as pd
import pytest
from conftest import SMARD_CSV

from product_data_checker.issues import BLOCKING
from product_data_checker.metrics import build_tables, load_sql, quality_metrics, smard_metrics


@pytest.fixture(scope="module")
def quality(demo_result):
    return quality_metrics(demo_result)


def test_overview_matches_python(quality, demo_result):
    ov = quality["quality_overview"].frame.iloc[0]
    assert ov["articles"] == 200
    assert ov["released"] == len(demo_result.released())
    assert ov["to_review"] == len(demo_result.to_review())
    assert ov["usable_released_pct"] == 100.0


def test_error_rate_by_supplier_matches_pandas(quality, demo_result):
    blocked = demo_result.blocking_rows()
    df = pd.DataFrame(
        [{"supplier": p.supplier, "blocked": p.row in blocked} for p in demo_result.products]
    )
    expected = (df.groupby("supplier")["blocked"].mean() * 100).round(1)
    got = quality["error_rate_by_supplier"].frame.set_index("supplier")["error_rate_pct"]
    pd.testing.assert_series_equal(got.sort_index(), expected.sort_index(), check_names=False)
    # worst supplier first
    assert list(got) == sorted(got, reverse=True)


def test_reasons_match_issue_list(quality, demo_result):
    frame = quality["reasons"].frame.set_index("code")
    for code, row in frame.iterrows():
        rows = {i.row for i in demo_result.issues if i.code == code and i.severity == BLOCKING}
        assert row["articles"] == len(rows)


def test_field_checks_respect_category_rules(demo_result):
    tables = build_tables(demo_result)
    checks = tables["field_checks"]
    # pieces is only mandatory for bit sets
    rows_with_pieces = set(checks.loc[checks["field"] == "pieces", "row"])
    bit_sets = {p.row for p in demo_result.products if p.category == "Bit-Sets"}
    assert rows_with_pieces == bit_sets


def test_sql_files_are_plain_sql():
    sql = load_sql("error_rate_by_supplier")
    assert sql.lstrip().startswith("--")
    assert "SELECT" in sql


@pytest.mark.skipif(not SMARD_CSV.exists(), reason="SMARD file not present")
def test_smard_kpis_match_pandas():
    result = smard_metrics(SMARD_CSV)
    raw = pd.read_csv(SMARD_CSV)
    ov = result["smard_overview"].frame.iloc[0]
    assert ov["hours"] == len(raw)
    assert ov["negative_price_hours"] == int((raw["price_eur_mwh"] < 0).sum())
    assert ov["avg_price_eur_mwh"] == pytest.approx(raw["price_eur_mwh"].mean(), abs=0.01)
    renewables = (
        raw[
            [
                "solar_mwh",
                "wind_onshore_mwh",
                "wind_offshore_mwh",
                "biomass_mwh",
                "hydro_mwh",
                "other_renewable_mwh",
            ]
        ]
        .sum()
        .sum()
    )
    assert ov["renewable_share_pct"] == pytest.approx(
        100 * renewables / raw["load_mwh"].sum(), abs=0.05
    )

    monthly = result["smard_monthly"].frame
    assert len(monthly) == 12
    assert monthly["negative_price_hours"].sum() == ov["negative_price_hours"]
    # the sums let the dashboard combine months exactly; the year must come out the same
    assert monthly["hours"].sum() == ov["hours"]
    assert monthly["price_sum"].sum() / monthly["hours"].sum() == pytest.approx(
        ov["avg_price_eur_mwh"], abs=0.01
    )
    assert 100 * monthly["renewable_mwh"].sum() / monthly["load_mwh"].sum() == pytest.approx(
        ov["renewable_share_pct"], abs=0.05
    )
    daily = result["smard_daily"].frame
    assert 364 <= len(daily) <= 366
    assert daily["negative_price_hours"].sum() == ov["negative_price_hours"]
    assert daily["min_price_eur_mwh"].min() == pytest.approx(ov["min_price_eur_mwh"], abs=0.01)
    assert daily["max_price_eur_mwh"].max() == pytest.approx(ov["max_price_eur_mwh"], abs=0.01)
    heat = result["smard_price_by_hour"].frame
    assert len(heat) == 12 * 24
    buckets = result["smard_price_by_renewable_share"].frame
    assert buckets["hours"].sum() == ov["hours"]
