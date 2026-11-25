"""Safe loading of supplier files and safe writing of cell values.

Two directions, two defences:
* Reading: size, row, column and cell limits; only .csv and .xlsx; macro-enabled
  workbooks are refused even if renamed; formulas are never evaluated (every cell is
  read as its stored text, never as a cached result).
* Writing: any text that a spreadsheet would treat as a formula is neutralised
  (CSV/Formula injection, OWASP).
"""

from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path
from xml.etree.ElementTree import ParseError

import pandas as pd
from defusedxml import DefusedXmlException
from openpyxl import load_workbook

from . import config


class InputRejected(ValueError):
    """The file violates a limit or is of a type we do not process."""


FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r", "\n", "＝", "＋", "－", "＠")


def neutralize_formula(value: object) -> object:
    """Return a value that no spreadsheet will execute.

    Text starting with = + - @ (or tab/CR/LF, or their full-width forms) gets a leading
    apostrophe, the OWASP recommendation. Numbers stay numbers.
    """
    if isinstance(value, str) and value and value.lstrip(" ").startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def looks_like_formula(value: object) -> bool:
    return isinstance(value, str) and value.lstrip(" ").startswith(FORMULA_PREFIXES)


def _check_file(path: Path) -> None:
    if not path.is_file():
        raise InputRejected(f"Datei nicht gefunden: {path.name}")
    suffix = path.suffix.lower()
    if suffix not in config.ALLOWED_SUFFIXES:
        raise InputRejected(
            f"Dateityp {suffix or '(ohne Endung)'} wird nicht verarbeitet. Erlaubt: .csv, .xlsx"
        )
    size = path.stat().st_size
    if size > config.MAX_FILE_BYTES:
        raise InputRejected(
            f"Datei ist {size / 1_048_576:.1f} MB groß, erlaubt sind "
            f"{config.MAX_FILE_BYTES / 1_048_576:.0f} MB."
        )
    if size == 0:
        raise InputRejected("Datei ist leer.")


def _read_xlsx(path: Path) -> list[list[str]]:
    try:
        with zipfile.ZipFile(path) as zf:
            names = zf.namelist()
            if any(n.lower().endswith("vbaproject.bin") for n in names):
                raise InputRejected(
                    "Arbeitsmappe enthält Makros (vbaProject.bin) und wird abgelehnt."
                )
            # zip-bomb guard: the uncompressed size must stay reasonable as well
            if sum(i.file_size for i in zf.infolist()) > config.MAX_FILE_BYTES * 20:
                raise InputRejected("Arbeitsmappe ist entpackt zu groß.")
    except zipfile.BadZipFile as exc:
        raise InputRejected("Keine gültige .xlsx-Datei.") from exc

    # read_only streams rows; data_only=False keeps formulas as their text, so a planted
    # "=HYPERLINK(...)" arrives as a string and is never evaluated or trusted.
    try:
        wb = load_workbook(path, read_only=True, data_only=False)
    except (DefusedXmlException, ParseError, KeyError, ValueError) as exc:
        raise InputRejected("Arbeitsmappe enthält unzulässiges oder defektes XML.") from exc
    try:
        ws = wb.worksheets[0]
        # In read_only mode openpyxl pads every row up to the declared last column. One
        # cell in column XFD would turn 5,000 rows into 80 million cells, so the declared
        # width is checked before reading, and rows are cut at the limit either way
        # (the <dimension> element can be missing or wrong).
        declared = ws.max_column
        if declared is not None and declared > config.MAX_COLUMNS:
            raise InputRejected(f"Mehr als {config.MAX_COLUMNS} Spalten.")
        rows: list[list[str]] = []
        for i, row in enumerate(ws.iter_rows(max_col=config.MAX_COLUMNS + 1, values_only=True)):
            if i > config.MAX_ROWS:
                raise InputRejected(f"Mehr als {config.MAX_ROWS} Zeilen.")
            values = _trim(["" if v is None else str(v) for v in row])
            if len(values) > config.MAX_COLUMNS:
                raise InputRejected(f"Mehr als {config.MAX_COLUMNS} Spalten.")
            rows.append(values)
        return rows
    except (DefusedXmlException, ParseError) as exc:  # sheet XML is parsed lazily
        raise InputRejected("Arbeitsmappe enthält unzulässiges oder defektes XML.") from exc
    finally:
        wb.close()


def _trim(row: list[str]) -> list[str]:
    """Drop empty cells at the end of a row (trailing separators, padded sheet rows)."""
    end = len(row)
    while end and not row[end - 1].strip():
        end -= 1
    return row[:end]


def _read_csv(path: Path) -> list[list[str]]:
    raw = path.read_bytes()
    for encoding in ("utf-8-sig", "cp1252"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:  # pragma: no cover - cp1252 decodes almost anything
        raise InputRejected("Zeichensatz nicht erkannt (erwartet UTF-8 oder Windows-1252).")
    sample = text[:4096]
    delimiter = ";" if sample.count(";") >= sample.count(",") else ","
    reader = csv.reader(io.StringIO(text), delimiter=delimiter)
    rows: list[list[str]] = []
    try:
        for i, row in enumerate(reader):
            if i > config.MAX_ROWS:
                raise InputRejected(f"Mehr als {config.MAX_ROWS} Zeilen.")
            row = _trim(row)
            if len(row) > config.MAX_COLUMNS:
                raise InputRejected(f"Mehr als {config.MAX_COLUMNS} Spalten.")
            rows.append(row)
    except csv.Error as exc:  # e.g. "field larger than field limit"
        raise InputRejected("Zelle zu lang oder CSV defekt.") from exc
    return rows


def load_supplier_file(path: Path) -> pd.DataFrame:
    """Load a supplier list into a DataFrame of strings with internal column names."""
    path = Path(path)
    _check_file(path)
    rows = _read_xlsx(path) if path.suffix.lower() == ".xlsx" else _read_csv(path)
    rows = [r for r in rows if any(c.strip() for c in r)]
    if len(rows) < 2:
        raise InputRejected("Keine Datenzeilen gefunden.")
    header, body = rows[0], rows[1:]
    if len(header) > config.MAX_COLUMNS:
        raise InputRejected(f"Mehr als {config.MAX_COLUMNS} Spalten.")

    mapped: list[str] = []
    for h in header:
        key = config.COLUMN_ALIASES.get(h.strip().lower())
        mapped.append(key or f"_ignored_{len(mapped)}")
    missing = [f for f in ("sku", "supplier", "ean", "name") if f not in mapped]
    if missing:
        labels = ", ".join(config.FIELD_LABELS[m] for m in missing)
        raise InputRejected(f"Pflichtspalten fehlen: {labels}")

    width = len(header)
    records = []
    for row in body:
        row = (row + [""] * width)[:width]
        record = {}
        for col, value in zip(mapped, row, strict=True):
            if col.startswith("_ignored_"):
                continue
            if len(value) > config.MAX_CELL_CHARS:
                value = value[: config.MAX_CELL_CHARS]
            record[col] = value
        records.append(record)

    df = pd.DataFrame.from_records(records)
    for field in config.FIELD_LABELS:
        if field not in df.columns:
            df[field] = ""
    df = df[list(config.FIELD_LABELS)].fillna("").astype(str)
    df.insert(0, "row", range(2, len(df) + 2))  # spreadsheet row number incl. header
    return df
