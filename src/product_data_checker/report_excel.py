"""Excel and CSV output. Every text cell passes through the formula guard.

Excel: text cells are stored with type *string* (never formula), and formula-like text
gets the cell's quotePrefix flag, the same thing Excel sets when a user types a leading
apostrophe. The value stays as written ("- 5 mm") and Excel keeps treating it as text
even after editing. CSV has no cell types, so there the apostrophe goes into the value.
"""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.cell.cell import TYPE_STRING
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from . import config
from .ingest import looks_like_formula, neutralize_formula
from .issues import BLOCKING
from .metrics import QueryResult
from .pipeline import RunResult
from .units import format_number_de

HEADER_FILL = PatternFill("solid", fgColor="1F2328")
HEADER_FONT = Font(bold=True, color="FFFFFF")
TITLE_FONT = Font(bold=True, size=13)
MUTED_FONT = Font(color="6B7280", size=9)
THIN = Border(bottom=Side(style="thin", color="D0D4DA"))

CLEAN_COLUMNS = [
    ("Zeile", 7, None),
    ("Artikelnummer", 14, None),
    ("Lieferant", 26, None),
    ("EAN", 15, None),
    ("Marke", 15, None),
    ("Kategorie", 22, None),
    ("Kategorie-Quelle", 15, None),
    ("Ausführung", 20, None),
    ("Nennmaß (mm)", 13, "0.0#"),
    ("Länge (mm)", 11, "0.0#"),
    ("Gewicht (g)", 11, "0.0#"),
    ("Material", 20, None),
    ("Teile", 7, "0"),
    ("EK netto (EUR)", 13, "#,##0.00"),
    ("Titel", 60, None),
    ("Kurzbeschreibung", 80, None),
    ("Hinweise", 50, None),
]
REVIEW_COLUMNS = [
    ("Zeile", 7, None),
    ("Artikelnummer", 14, None),
    ("Lieferant", 26, None),
    ("Gründe", 36, None),
    ("Details", 70, None),
    ("EAN (Original)", 18, None),
    ("Bezeichnung (Original)", 36, None),
    ("Kategorie", 22, None),
    ("Nennmaß (Original)", 16, None),
    ("Länge (Original)", 14, None),
    ("Gewicht (Original)", 14, None),
    ("EK netto (Original)", 14, None),
    ("Titel (Entwurf)", 60, None),
    ("Kurzbeschreibung (Entwurf)", 80, None),
]


def safe(value):
    """Neutralise formula-like text for CSV; leave numbers and None alone."""
    return neutralize_formula(value) if isinstance(value, str) else value


def set_cell(ws, row: int, column: int, value):
    """Write one value so that no spreadsheet will ever evaluate it."""
    cell = ws.cell(row=row, column=column, value=value)
    if isinstance(value, str):
        cell.data_type = TYPE_STRING  # openpyxl would store "=..." as a formula otherwise
        if looks_like_formula(value):
            cell.quotePrefix = True
    return cell


def _write_row(ws, row_idx: int, values: list, formats: list | None = None) -> None:
    for col_idx, value in enumerate(values, start=1):
        cell = set_cell(ws, row_idx, col_idx, value)
        if formats and formats[col_idx - 1] and isinstance(value, int | float):
            cell.number_format = formats[col_idx - 1]


def _header(ws, row_idx: int, columns: list[tuple]) -> None:
    for col_idx, (label, width, _) in enumerate(columns, start=1):
        cell = ws.cell(row=row_idx, column=col_idx, value=label)
        cell.fill, cell.font = HEADER_FILL, HEADER_FONT
        cell.alignment = Alignment(vertical="center")
        ws.column_dimensions[get_column_letter(col_idx)].width = width
    ws.row_dimensions[row_idx].height = 20


def _notes_by_row(result: RunResult) -> dict[int, list]:
    grouped: dict[int, list] = defaultdict(list)
    for issue in result.issues:
        grouped[issue.row].append(issue)
    return grouped


def clean_rows(result: RunResult) -> list[list]:
    grouped = _notes_by_row(result)
    rows = []
    for p in result.released():
        notes = "; ".join(f"{i.label}: {i.detail}" for i in grouped[p.row])
        rows.append(
            [
                p.row,
                p.sku,
                p.supplier,
                p.ean,
                p.brand,
                p.category,
                p.category_source,
                p.variant,
                p.nominal_mm,
                p.length_mm,
                p.weight_g,
                p.material,
                p.pieces,
                p.price_eur,
                p.title,
                p.description,
                notes,
            ]
        )
    return rows


def review_rows(result: RunResult) -> list[list]:
    grouped = _notes_by_row(result)
    rows = []
    for p in result.to_review():
        blocking = [i for i in grouped[p.row] if i.severity == BLOCKING]
        reasons = ", ".join(dict.fromkeys(i.label for i in blocking))
        details = "; ".join(i.detail for i in blocking)
        rows.append(
            [
                p.row,
                p.sku,
                p.supplier,
                reasons,
                details,
                p.raw.get("ean", ""),
                p.raw.get("name", ""),
                p.category,
                p.raw.get("nominal", ""),
                p.raw.get("length", ""),
                p.raw.get("weight", ""),
                p.raw.get("price", ""),
                p.title,
                p.description,
            ]
        )
    return rows


def _sheet_table(ws, columns, rows) -> None:
    _header(ws, 1, columns)
    formats = [c[2] for c in columns]
    for i, values in enumerate(rows, start=2):
        _write_row(ws, i, values, formats)
    ws.freeze_panes = "C2"
    if rows:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{len(rows) + 1}"


KPI_SECTIONS = [
    (
        "error_rate_by_supplier",
        "Fehlerquote je Lieferant",
        {
            "supplier": "Lieferant",
            "articles": "Artikel",
            "blocked": "zur Prüfung",
            "error_rate_pct": "Fehlerquote %",
            "top_reason": "häufigster Grund",
            "top_reason_count": "Anzahl",
        },
    ),
    (
        "reasons",
        "Gründe für die Prüfung",
        {
            "reason": "Grund",
            "stage": "Stufe",
            "articles": "Artikel",
            "findings": "Befunde",
            "share_of_all_pct": "Anteil an allen %",
        },
    ),
    (
        "completeness_by_field",
        "Vollständigkeit je Pflichtfeld",
        {
            "field": "Feld",
            "required_in": "Pflicht in",
            "filled_pct": "befüllt %",
            "usable_pct": "verwendbar %",
        },
    ),
]


def _kpi_sheet(
    ws, result: RunResult, quality: dict[str, QueryResult], firma: str = config.DEFAULT_THEME
) -> None:
    # header colours of the chosen theme; an unknown slug is a KeyError, never a guess
    fill_hex, ink_hex = config.THEMES[firma]["excel"]
    header_fill = PatternFill("solid", fgColor=fill_hex)
    header_font = Font(bold=True, color=ink_hex)
    ws.column_dimensions["A"].width = 34
    for col in "BCDEF":
        ws.column_dimensions[col].width = 18
    ws["A1"] = "Kennzahlen Produktdatenprüfung"
    ws["A1"].font = Font(bold=True, size=13, color=fill_hex)
    set_cell(
        ws,
        2,
        1,
        f"Quelle: {result.source_file}, Textmodus: {result.provider}. "
        "Alle Werte per SQL (DuckDB), Abfragen im Ordner sql/.",
    ).font = MUTED_FONT

    ov = quality["quality_overview"].frame.iloc[0]
    overview = [
        ("Artikel gesamt", int(ov["articles"]), "0"),
        ("Freigegeben", int(ov["released"]), "0"),
        ("Zur Prüfung", int(ov["to_review"]), "0"),
        ("Freigabequote %", float(ov["release_rate_pct"]), "0.0"),
        ("Vollständige Artikel vorher %", float(ov["complete_articles_before_pct"]), "0.0"),
        ("Pflichtfelder verwendbar vorher %", float(ov["usable_before_pct"]), "0.0"),
        ("Pflichtfelder verwendbar, freigegeben %", float(ov["usable_released_pct"]), "0.0"),
    ]
    row = 4
    for label, value, fmt in overview:
        ws.cell(row=row, column=1, value=label).border = THIN
        cell = ws.cell(row=row, column=2, value=value)
        cell.number_format, cell.border = fmt, THIN
        row += 1

    for key, title, mapping in KPI_SECTIONS:
        row += 2
        ws.cell(row=row, column=1, value=title).font = TITLE_FONT
        row += 1
        frame = quality[key].frame[list(mapping)]
        columns = [(label, None, None) for label in mapping.values()]
        for col_idx, (label, _, _) in enumerate(columns, start=1):
            cell = ws.cell(row=row, column=col_idx, value=label)
            cell.fill, cell.font = header_fill, header_font
        for values in frame.itertuples(index=False):
            row += 1
            _write_row(ws, row, [v.item() if hasattr(v, "item") else v for v in values])


def write_excel(
    result: RunResult,
    quality: dict[str, QueryResult],
    path: Path,
    firma: str = config.DEFAULT_THEME,
) -> Path:
    wb = Workbook()
    ws_clean = wb.active
    ws_clean.title = "Sauber"
    _sheet_table(ws_clean, CLEAN_COLUMNS, clean_rows(result))
    ws_review = wb.create_sheet("Prüfen")
    _sheet_table(ws_review, REVIEW_COLUMNS, review_rows(result))
    _kpi_sheet(wb.create_sheet("Kennzahlen"), result, quality, firma)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)  # .xlsx via openpyxl never contains a VBA project
    return path


def _csv_value(value) -> str:
    """German spreadsheet conventions: decimal comma, no formulas."""
    if value is None:
        return ""
    if isinstance(value, float):
        return format_number_de(value)
    return str(safe(value))


def write_csv(result: RunResult, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.writer(fh, delimiter=";")
        writer.writerow([c[0] for c in CLEAN_COLUMNS])
        for values in clean_rows(result):
            writer.writerow([_csv_value(v) for v in values])
    return path
