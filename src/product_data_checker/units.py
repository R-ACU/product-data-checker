"""Parse the many ways suppliers write lengths, weights and prices.

Every parser returns a ``Parsed`` value: the normalised number (or None) plus a short
note when something was assumed or converted, so the reviewer can see what happened.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

EMPTY_MARKERS = {"", "-", "--", "k.a.", "k. a.", "n/a", "na", "keine angabe", "?"}

_NUMBER = r"(?P<num>\d{1,6}(?:[.,]\d{1,4})?)"
_LENGTH_RE = re.compile(rf"^{_NUMBER}\s*(?P<unit>mm|cm|m)?$", re.IGNORECASE)
_WEIGHT_RE = re.compile(rf"^{_NUMBER}\s*(?P<unit>g|kg)?$", re.IGNORECASE)
_PRICE_RE = re.compile(
    r"^(?:eur|€)?\s*(?P<num>\d{1,6}(?:[.,]\d{1,2})?)\s*(?:eur|€)?$", re.IGNORECASE
)

LENGTH_FACTORS = {"mm": Decimal(1), "cm": Decimal(10), "m": Decimal(1000)}
WEIGHT_FACTORS = {"g": Decimal(1), "kg": Decimal(1000)}


@dataclass(frozen=True)
class Parsed:
    value: float | None
    status: str  # "ok" | "empty" | "unreadable"
    note: str = ""


def is_empty(raw: str) -> bool:
    return raw.strip().lower() in EMPTY_MARKERS


def to_decimal(text: str) -> Decimal:
    """'1,25' and '1.25' both mean 1.25. Thousand separators are not expected here."""
    return Decimal(text.replace(",", "."))


def _parse_with_unit(raw: str, pattern: re.Pattern, factors: dict, default: str) -> Parsed:
    text = raw.strip()
    if is_empty(text):
        return Parsed(None, "empty")
    m = pattern.match(text)
    if not m:
        return Parsed(None, "unreadable", f"Wert nicht lesbar: '{text}'")
    try:
        number = to_decimal(m.group("num"))
    except InvalidOperation:  # pragma: no cover - regex already guarantees digits
        return Parsed(None, "unreadable", f"Wert nicht lesbar: '{text}'")
    unit = (m.group("unit") or "").lower()
    note = ""
    if not unit:
        unit = default
        note = f"Einheit fehlte, als {default} gelesen"
    elif unit != default:
        note = f"umgerechnet von {unit}"
    value = (number * factors[unit]).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Parsed(float(value.normalize()), "ok", note)


def parse_length_mm(raw: str) -> Parsed:
    return _parse_with_unit(raw, _LENGTH_RE, LENGTH_FACTORS, "mm")


def parse_weight_g(raw: str) -> Parsed:
    return _parse_with_unit(raw, _WEIGHT_RE, WEIGHT_FACTORS, "g")


def parse_price_eur(raw: str) -> Parsed:
    text = raw.strip()
    if is_empty(text):
        return Parsed(None, "empty")
    m = _PRICE_RE.match(text)
    if not m:
        return Parsed(None, "unreadable", f"Preis nicht lesbar: '{text}'")
    value = to_decimal(m.group("num")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return Parsed(float(value), "ok")


def parse_count(raw: str) -> Parsed:
    text = raw.strip()
    if is_empty(text):
        return Parsed(None, "empty")
    if re.fullmatch(r"\d{1,4}", text):
        return Parsed(float(int(text)), "ok")
    return Parsed(None, "unreadable", f"Anzahl nicht lesbar: '{text}'")


def format_number_de(value: float) -> str:
    """12.5 -> '12,5', 125.0 -> '125'."""
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")
