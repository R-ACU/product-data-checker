import pytest

from product_data_checker.ean import check_digit, is_valid, normalize_ean


@pytest.mark.parametrize(
    "body, expected",
    [
        ("400638133393", 1),  # 4006381333931, the textbook GS1 example
        ("590123412345", 7),  # 5901234123457
        ("9638507", 4),  # EAN-8 96385074
        ("000000000000", 0),
    ],
)
def test_check_digit(body, expected):
    assert check_digit(body) == expected


def test_check_digit_by_hand():
    # 4 0 0 6 3 8 1 3 3 3 9 3, weights 1 3 1 3 ... from the left (3 for the rightmost body digit)
    digits = [4, 0, 0, 6, 3, 8, 1, 3, 3, 3, 9, 3]
    total = sum(d * (3 if i % 2 else 1) for i, d in enumerate(digits))
    assert total == 89
    assert (10 - total % 10) % 10 == check_digit("400638133393") == 1


def test_valid_and_invalid():
    assert is_valid("4006381333931")
    assert is_valid("96385074")
    assert not is_valid("4006381333932")
    assert not is_valid("400638133393")
    assert not is_valid("40063813339A1")


def test_normalize_ok_with_spaces():
    r = normalize_ean(" 4 006381 333931 ")
    assert (r.code, r.status) == ("4006381333931", "ok")
    assert r.note == "Leerzeichen entfernt"


def test_normalize_wrong_check_digit_names_expected_digit():
    r = normalize_ean("4006381333935")
    assert r.status == "checksum"
    assert "erwartet 1" in r.note


@pytest.mark.parametrize("raw", ["4,00638E+12", "4.006381E+12", "2,16297E+12"])
def test_scientific_notation_is_unrecoverable(raw):
    r = normalize_ean(raw)
    assert r.status == "scientific"
    assert r.code == ""


def test_excel_float_suffix_is_stripped():
    assert normalize_ean("4006381333931.0").status == "ok"


def test_upc_a_is_padded():
    r = normalize_ean("036000291452")  # UPC-A, valid
    assert (r.code, r.status) == ("0036000291452", "ok")


@pytest.mark.parametrize(
    "raw, status",
    [
        ("40063813", "checksum"),
        ("4006381O33931", "format"),
        ("40063813339", "format"),
        ("", "empty"),
    ],
)
def test_bad_formats(raw, status):
    assert normalize_ean(raw).status == status
