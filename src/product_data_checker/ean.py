"""EAN-13 / EAN-8 normalisation and check-digit validation (GS1 modulo 10)."""

from __future__ import annotations

import re
from dataclasses import dataclass

_SCIENTIFIC = re.compile(r"^\d([.,]\d+)?e[+-]?\d+$", re.IGNORECASE)


@dataclass(frozen=True)
class EanResult:
    code: str  # digits only, as far as recoverable
    status: str  # "ok" | "empty" | "checksum" | "format" | "scientific"
    note: str = ""


def check_digit(body: str) -> int:
    """GS1 check digit for the digits *without* the check digit.

    Weights alternate 3 and 1 starting from the rightmost digit of the body.
    Example: 400638133393 -> 1, so the full EAN-13 is 4006381333931.
    """
    total = 0
    for i, digit in enumerate(reversed(body)):
        total += int(digit) * (3 if i % 2 == 0 else 1)
    return (10 - total % 10) % 10


def is_valid(code: str) -> bool:
    return code.isdigit() and len(code) in (8, 13) and check_digit(code[:-1]) == int(code[-1])


def normalize_ean(raw: str) -> EanResult:
    text = raw.strip()
    if not text:
        return EanResult("", "empty")
    compact = re.sub(r"[\s\-]", "", text)
    if _SCIENTIFIC.match(compact):
        return EanResult(
            "",
            "scientific",
            "EAN im Exponentialformat gespeichert, Ziffern unwiederbringlich verloren",
        )
    if compact.endswith(".0") and compact[:-2].isdigit():  # Excel number read as float
        compact = compact[:-2]
    if not compact.isdigit():
        return EanResult(compact, "format", "EAN enthält ungültige Zeichen")
    if len(compact) == 12:  # UPC-A: same check digit, pad to EAN-13
        compact = "0" + compact
    if len(compact) not in (8, 13):
        return EanResult(compact, "format", f"EAN hat {len(compact)} statt 13 Stellen")
    if not is_valid(compact):
        expected = check_digit(compact[:-1])
        return EanResult(
            compact, "checksum", f"Prüfziffer {compact[-1]} falsch, erwartet {expected}"
        )
    note = "Leerzeichen entfernt" if compact != text else ""
    return EanResult(compact, "ok", note)
