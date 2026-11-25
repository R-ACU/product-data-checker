"""Issue codes and their German labels. One issue = one row in the review list."""

from __future__ import annotations

from dataclasses import asdict, dataclass

BLOCKING = "blockierend"
NOTE = "hinweis"

# code -> (severity, German label shown in Excel and dashboard)
ISSUE_TYPES: dict[str, tuple[str, str]] = {
    "MISSING_REQUIRED": (BLOCKING, "Pflichtfeld fehlt"),
    "MISSING_DIMENSION": (BLOCKING, "Maß fehlt"),
    "UNREADABLE_VALUE": (BLOCKING, "Wert nicht lesbar"),
    "IMPLAUSIBLE_VALUE": (BLOCKING, "Wert unplausibel"),
    "EAN_CHECKSUM": (BLOCKING, "EAN-Prüfziffer falsch"),
    "EAN_FORMAT": (BLOCKING, "EAN-Format ungültig"),
    "EAN_SCIENTIFIC": (BLOCKING, "EAN von Excel zerstört"),
    "DUPLICATE_EAN": (BLOCKING, "Dublette (gleiche EAN)"),
    "DUPLICATE_SKU": (BLOCKING, "Dublette (gleiche Artikelnummer)"),
    "CATEGORY_UNCLEAR": (BLOCKING, "Kategorie unklar"),
    "FIELD_TOO_LONG": (BLOCKING, "Feld zu lang"),
    "INSTRUCTION_IN_FIELD": (BLOCKING, "Anweisung in Datenfeld"),
    "TEXT_NUMBER_MISMATCH": (BLOCKING, "Zahl im Text weicht ab"),
    "TEXT_UNSUPPORTED_CLAIM": (BLOCKING, "Eigenschaft nicht belegt"),
    "TEXT_RULE_VIOLATION": (BLOCKING, "Textregel verletzt"),
    "TEXT_UNAVAILABLE": (BLOCKING, "Kein Text erzeugt"),
    "FORMULA_NEUTRALIZED": (NOTE, "Formel neutralisiert"),
    "UNIT_CONVERTED": (NOTE, "Einheit umgerechnet"),
    "UNIT_ASSUMED": (NOTE, "Einheit angenommen"),
    "VALUE_NORMALIZED": (NOTE, "Schreibweise vereinheitlicht"),
    "CATEGORY_BY_MODEL": (NOTE, "Kategorie vom Modell eingeordnet"),
    "UNTRUSTED_SUPPLIER_TEXT": (NOTE, "Anweisung im Lieferantentext ignoriert"),
}


@dataclass(frozen=True)
class Issue:
    row: int
    sku: str
    supplier: str
    field: str
    code: str
    detail: str

    @property
    def severity(self) -> str:
        return ISSUE_TYPES[self.code][0]

    @property
    def label(self) -> str:
        return ISSUE_TYPES[self.code][1]

    def to_record(self) -> dict:
        record = asdict(self)
        record["severity"] = self.severity
        record["label"] = self.label
        return record
