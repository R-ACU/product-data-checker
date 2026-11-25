import pytest

from product_data_checker.units import (
    format_number_de,
    parse_count,
    parse_length_mm,
    parse_price_eur,
    parse_weight_g,
)


@pytest.mark.parametrize(
    "raw, mm",
    [
        ("12mm", 12),
        ("12 mm", 12),
        ("12 MM", 12),
        ("12,5 mm", 12.5),
        ("1,2 cm", 12),
        ("1.2cm", 12),
        ("12,5 cm", 125),
        ("0.125 m", 125),
        ("0,084 m", 84),
        (" 5,5mm ", 5.5),
    ],
)
def test_lengths(raw, mm):
    parsed = parse_length_mm(raw)
    assert parsed.status == "ok"
    assert parsed.value == pytest.approx(mm)


def test_conversion_is_noted():
    assert parse_length_mm("1,2 cm").note == "umgerechnet von cm"
    assert parse_length_mm("12 mm").note == ""


def test_bare_number_assumes_mm_and_says_so():
    parsed = parse_length_mm("125")
    assert parsed.value == 125
    assert parsed.note.startswith("Einheit fehlte")


@pytest.mark.parametrize("raw", ["", " ", "-", "k.A.", "n/a", "?"])
def test_empty_markers(raw):
    assert parse_length_mm(raw).status == "empty"


@pytest.mark.parametrize("raw", ["ca. 12", "lang", "12-15 cm", "12 Zoll", "1/2"])
def test_unreadable_is_never_guessed(raw):
    parsed = parse_length_mm(raw)
    assert parsed.status == "unreadable"
    assert parsed.value is None


@pytest.mark.parametrize(
    "raw, g", [("250 g", 250), ("250g", 250), ("0,25 kg", 250), ("0.018 kg", 18), ("1,5kg", 1500)]
)
def test_weights(raw, g):
    assert parse_weight_g(raw).value == pytest.approx(g)


@pytest.mark.parametrize(
    "raw, eur", [("4,90", 4.9), ("4.90", 4.9), ("4,90 €", 4.9), ("EUR 23,42", 23.42), ("€12", 12.0)]
)
def test_prices(raw, eur):
    assert parse_price_eur(raw).value == pytest.approx(eur)


def test_price_on_request_is_unreadable():
    assert parse_price_eur("auf Anfrage").status == "unreadable"


def test_counts():
    assert parse_count("61").value == 61
    assert parse_count("61 Stück").status == "unreadable"


def test_float_precision_does_not_leak():
    # 0.3 cm must be exactly 3 mm, not 2.9999999
    assert parse_length_mm("0,3 cm").value == 3


def test_format_number_de():
    assert format_number_de(12.5) == "12,5"
    assert format_number_de(125.0) == "125"
