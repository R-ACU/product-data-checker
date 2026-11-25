import zipfile

import pytest
from openpyxl import Workbook

from product_data_checker import config
from product_data_checker.ingest import (
    InputRejected,
    load_supplier_file,
    looks_like_formula,
    neutralize_formula,
)

ROW = "BW-1;Brennwald;4006381333931;Bohrer 6 mm;Brennwald;Bohrer;Metall;6 mm;84 mm;14 g;HSS;;4,90;"


@pytest.mark.parametrize(
    "value", ["=1+1", "+1", "-1+cmd", "@SUM(A1)", "\t=1", "\r=1", " =1", "＝1"]
)
def test_formula_prefixes_are_neutralised(value):
    assert looks_like_formula(value)
    assert neutralize_formula(value) == "'" + value


@pytest.mark.parametrize("value", ["Bohrer", "6 mm", "", 12, 4.5, None])
def test_harmless_values_stay(value):
    assert neutralize_formula(value) == value


def test_csv_semicolon_and_header_mapping(write_csv):
    df = load_supplier_file(write_csv(ROW))
    assert df.loc[0, "sku"] == "BW-1"
    assert df.loc[0, "length"] == "84 mm"
    assert df.loc[0, "row"] == 2


def test_csv_windows_1252(write_csv):
    path = write_csv(ROW.replace("Brennwald;Bohrer;", "Ostwerk & Söhne;Bohrer;"), encoding="cp1252")
    df = load_supplier_file(path)
    assert df.loc[0, "brand"] == "Ostwerk & Söhne"


def test_formula_in_xlsx_arrives_as_text_and_is_not_evaluated(tmp_path):
    wb = Workbook()
    ws = wb.active
    ws.append(["Artikelnummer", "Lieferant", "EAN", "Bezeichnung", "Beschreibung Lieferant"])
    ws.append(
        ["X-1", "Test", "4006381333931", "Bohrer", '=HYPERLINK("http://example.invalid";"x")']
    )
    path = tmp_path / "formel.xlsx"
    wb.save(path)
    df = load_supplier_file(path)
    assert df.loc[0, "supplier_note"].startswith("=HYPERLINK")


def test_rejects_macro_suffix(tmp_path):
    path = tmp_path / "liste.xlsm"
    path.write_bytes(b"PK\x03\x04")
    with pytest.raises(InputRejected, match="Dateityp"):
        load_supplier_file(path)


def test_rejects_renamed_macro_workbook(tmp_path):
    path = tmp_path / "harmlos.xlsx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/vbaProject.bin", b"\x00" * 16)
    with pytest.raises(InputRejected, match="Makros"):
        load_supplier_file(path)


def test_rejects_non_zip_xlsx(tmp_path):
    path = tmp_path / "kaputt.xlsx"
    path.write_text("kein Zip")
    with pytest.raises(InputRejected, match="gültige"):
        load_supplier_file(path)


def test_rejects_too_large_file(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "MAX_FILE_BYTES", 1_000)
    path = tmp_path / "gross.csv"
    path.write_text("a;b\n" + "x;y\n" * 400)
    with pytest.raises(InputRejected, match="MB"):
        load_supplier_file(path)


def test_rejects_too_many_rows(write_csv, monkeypatch):
    monkeypatch.setattr(config, "MAX_ROWS", 3)
    path = write_csv(*[ROW] * 5)
    with pytest.raises(InputRejected, match="Zeilen"):
        load_supplier_file(path)


def test_rejects_missing_mandatory_columns(tmp_path):
    path = tmp_path / "liste.csv"
    path.write_text("Artikelnummer;Preis\nA;1\n", encoding="utf-8")
    with pytest.raises(InputRejected, match="Pflichtspalten fehlen"):
        load_supplier_file(path)


def test_rejects_empty_and_header_only(tmp_path):
    empty = tmp_path / "leer.csv"
    empty.write_text("")
    with pytest.raises(InputRejected, match="leer"):
        load_supplier_file(empty)
    header_only = tmp_path / "kopf.csv"
    header_only.write_text("Artikelnummer;Lieferant;EAN;Bezeichnung\n")
    with pytest.raises(InputRejected, match="Keine Datenzeilen"):
        load_supplier_file(header_only)


def test_long_cells_are_capped(write_csv):
    long_note = "x" * (config.MAX_CELL_CHARS + 500)
    df = load_supplier_file(write_csv(ROW + long_note))
    assert len(df.loc[0, "supplier_note"]) == config.MAX_CELL_CHARS


def test_unknown_columns_are_ignored(tmp_path):
    path = tmp_path / "liste.csv"
    path.write_text("Artikelnummer;Lieferant;EAN;Bezeichnung;Geheim\nA;B;4006381333931;C;x\n")
    df = load_supplier_file(path)
    assert "Geheim" not in df.columns


def test_xml_parsing_is_hardened():
    from openpyxl.xml import DEFUSEDXML

    assert DEFUSEDXML, "defusedxml must be installed so openpyxl refuses XML entity attacks"


@pytest.mark.parametrize("target", ["xl/workbook.xml", "xl/worksheets/sheet1.xml"])
def test_entity_expansion_workbook_is_refused(tmp_path, target):
    """A workbook whose sheet XML declares entities (billion laughs) must not be parsed."""
    good = tmp_path / "good.xlsx"
    wb = Workbook()
    wb.active.append(["Artikelnummer", "Lieferant", "EAN", "Bezeichnung"])
    wb.active.append(["A", "B", "4006381333931", "C"])
    wb.save(good)
    evil = tmp_path / "evil.xlsx"
    bomb = (
        '<?xml version="1.0"?><!DOCTYPE lolz [<!ENTITY lol "lol">'
        '<!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">]>'
    )
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(evil, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == target:
                data = bomb.encode() + data.split(b"?>", 1)[-1]
            dst.writestr(item, data)
    with pytest.raises(InputRejected, match="XML"):
        load_supplier_file(evil)


def test_cell_in_column_xfd_is_refused_before_rows_are_padded(tmp_path):
    """One cell in XFD used to make openpyxl pad every row to 16,384 cells (685 MB)."""
    import time

    wb = Workbook()
    ws = wb.active
    ws.append(["Artikelnummer", "Lieferant", "EAN", "Bezeichnung"])
    for i in range(2, 2_000):
        ws.append([f"A-{i}", "B", "4006381333931", "C"])
    ws["XFD1"] = "x"
    path = tmp_path / "breit.xlsx"
    wb.save(path)
    started = time.perf_counter()
    with pytest.raises(InputRejected, match="Spalten"):
        load_supplier_file(path)
    assert time.perf_counter() - started < 2


def test_wide_sheet_without_dimension_is_still_capped(tmp_path):
    """The <dimension> element is optional and can lie; rows are cut at the limit anyway."""
    wb = Workbook()
    ws = wb.active
    ws.append(["Artikelnummer", "Lieferant", "EAN", "Bezeichnung"])
    ws.append(["A-1", "B", "4006381333931", "C"])
    ws.cell(row=2, column=config.MAX_COLUMNS + 1, value="zu breit")
    good = tmp_path / "good.xlsx"
    wb.save(good)
    evil = tmp_path / "ohne-dimension.xlsx"
    with zipfile.ZipFile(good) as src, zipfile.ZipFile(evil, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "xl/worksheets/sheet1.xml":
                start = data.index(b"<dimension")
                data = data[:start] + data[data.index(b"/>", start) + 2 :]
            dst.writestr(item, data)
    with pytest.raises(InputRejected, match="Spalten"):
        load_supplier_file(evil)


def test_trailing_empty_columns_are_not_counted(tmp_path):
    path = tmp_path / "liste.csv"
    header = "Artikelnummer;Lieferant;EAN;Bezeichnung" + ";" * 60
    path.write_text(f"{header}\nA;B;4006381333931;C\n", encoding="utf-8")
    assert load_supplier_file(path).loc[0, "sku"] == "A"


def test_too_many_csv_columns_are_refused(tmp_path):
    path = tmp_path / "liste.csv"
    header = ";".join(f"Spalte {i}" for i in range(config.MAX_COLUMNS + 5))
    path.write_text(f"{header}\n" + ";".join("x" * 50) + "\n", encoding="utf-8")
    with pytest.raises(InputRejected, match="Spalten"):
        load_supplier_file(path)


def test_oversized_csv_field_gives_a_clear_message(tmp_path):
    """A cell above Python's csv field limit used to end in a raw _csv.Error traceback."""
    path = tmp_path / "liste.csv"
    huge = '"' + "x" * 200_000 + '"'
    path.write_text(f"Artikelnummer;Lieferant;EAN;Bezeichnung\nA;B;4006381333931;{huge}\n")
    with pytest.raises(InputRejected, match="Zelle zu lang"):
        load_supplier_file(path)
