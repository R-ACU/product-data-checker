"""Excel and CSV output: right sheets, right rows, and never a live formula."""

import csv
import zipfile

import pytest
from conftest import FIXTURES
from openpyxl import load_workbook

from product_data_checker.ingest import FORMULA_PREFIXES, looks_like_formula
from product_data_checker.llm import MockProvider
from product_data_checker.metrics import quality_metrics
from product_data_checker.pipeline import run
from product_data_checker.report_excel import write_csv, write_excel


@pytest.fixture(scope="module")
def outputs(tmp_path_factory, demo_result):
    out = tmp_path_factory.mktemp("out")
    xlsx = write_excel(demo_result, quality_metrics(demo_result), out / "ergebnis.xlsx")
    csv_path = write_csv(demo_result, out / "sauber.csv")
    return xlsx, csv_path


def test_sheets_and_row_counts(outputs, demo_result):
    wb = load_workbook(outputs[0])
    assert wb.sheetnames == ["Sauber", "Prüfen", "Kennzahlen"]
    assert wb["Sauber"].max_row - 1 == len(demo_result.released())
    assert wb["Prüfen"].max_row - 1 == len(demo_result.to_review())


def test_no_formula_cells_and_no_macros(outputs):
    xlsx = outputs[0]
    wb = load_workbook(xlsx)
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                assert cell.data_type != "f", f"{ws.title}!{cell.coordinate}"
                if isinstance(cell.value, str) and looks_like_formula(cell.value):
                    # stored as text and flagged like a typed apostrophe in Excel
                    assert cell.data_type == "s", f"{ws.title}!{cell.coordinate}"
                    assert cell.quotePrefix, f"{ws.title}!{cell.coordinate}"
    with zipfile.ZipFile(xlsx) as zf:
        assert not any("vbaProject" in n for n in zf.namelist())
        for name in zf.namelist():
            if name.startswith("xl/worksheets/"):
                assert b"<f>" not in zf.read(name)


def test_formula_text_survives_as_visible_text(write_csv_rows):
    path = write_csv_rows(
        'F-1;L;4006381333931;=HYPERLINK("x");M;Bohrer;Metall;6 mm;84 mm;14 g;HSS;;4,90;@SUM(1)'
    )
    result = run(path, MockProvider(FIXTURES))
    out = path.parent / "out.xlsx"
    write_excel(result, quality_metrics(result), out)
    ws = load_workbook(out)["Prüfen"]
    cells = {c.value: c for row in ws.iter_rows(min_row=2) for c in row}
    cell = cells['=HYPERLINK("x")']  # readable as written, no visible apostrophe
    assert cell.data_type == "s" and cell.quotePrefix
    assert not any(isinstance(v, str) and v.startswith("'") for v in cells)
    with zipfile.ZipFile(out) as zf:
        assert b'quotePrefix="1"' in zf.read("xl/styles.xml")


def test_csv_output_is_safe(outputs):
    with outputs[1].open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh, delimiter=";"))
    assert rows[0][0] == "Zeile"
    for row in rows[1:]:
        for value in row:
            assert not value.startswith(FORMULA_PREFIXES), value


def test_csv_uses_decimal_comma(outputs):
    with outputs[1].open(encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    assert any("," in r["Nennmaß (mm)"] for r in rows)  # e.g. 5,5
    assert not any("." in r["Länge (mm)"] for r in rows)


@pytest.fixture
def write_csv_rows(write_csv):
    return write_csv
