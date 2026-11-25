from __future__ import annotations

from pathlib import Path

import pytest

from product_data_checker.llm import MockProvider
from product_data_checker.pipeline import RunResult, run

ROOT = Path(__file__).resolve().parents[1]
DEMO_XLSX = ROOT / "data" / "raw" / "lieferantenliste.xlsx"
DEMO_CSV = ROOT / "data" / "raw" / "lieferantenliste.csv"
FIXTURES = ROOT / "fixtures" / "llm"
SMARD_CSV = ROOT / "data" / "smard" / "smard_hourly.csv"

HEADER = (
    "Artikelnummer;Lieferant;EAN;Bezeichnung;Marke;Kategorie;Ausführung;Nennmaß;Länge;"
    "Gewicht;Material;Teile;EK netto;Beschreibung Lieferant"
)


@pytest.fixture(scope="session")
def demo_result() -> RunResult:
    return run(DEMO_XLSX, MockProvider(FIXTURES))


@pytest.fixture
def write_csv(tmp_path):
    """Write a small supplier CSV with the demo header and return its path."""

    def _write(*rows: str, name: str = "liste.csv", encoding: str = "utf-8-sig") -> Path:
        path = tmp_path / name
        path.write_text("\n".join([HEADER, *rows]) + "\n", encoding=encoding)
        return path

    return _write
