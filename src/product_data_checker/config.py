"""Static rules of the checker: limits, mandatory fields, taxonomy, text rules.

Everything a reviewer may want to change lives here, in one place, as plain data.
"""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SQL_DIR = Path(__file__).resolve().parent / "sql"

# --- Input limits -----------------------------------------------------------------
MAX_FILE_BYTES = 5 * 1024 * 1024  # 5 MB
MAX_ROWS = 5_000
MAX_COLUMNS = 40
MAX_CELL_CHARS = 1_000
# Supplier text that reaches a model (name to the classifier, the others to the copy
# writer) gets tighter caps; anything longer is blocked, not truncated.
MODEL_FIELD_MAX_CHARS: dict[str, int] = {
    "name": 150,
    "brand": 60,
    "variant": 120,
    "material": 60,
}
ALLOWED_SUFFIXES = {".csv", ".xlsx"}  # never .xlsm/.xls: no macros, no legacy binary format

# --- Column mapping: supplier header (lower-case, trimmed) -> internal field -------
COLUMN_ALIASES: dict[str, str] = {
    "artikelnummer": "sku",
    "artikel-nr.": "sku",
    "art.-nr.": "sku",
    "sku": "sku",
    "lieferant": "supplier",
    "ean": "ean",
    "gtin": "ean",
    "ean-code": "ean",
    "bezeichnung": "name",
    "artikelbezeichnung": "name",
    "marke": "brand",
    "hersteller": "brand",
    "kategorie": "category",
    "warengruppe": "category",
    "ausführung": "variant",
    "nennmaß": "nominal",
    "länge": "length",
    "gewicht": "weight",
    "material": "material",
    "teile": "pieces",
    "ek netto": "price",
    "preis": "price",
    "beschreibung lieferant": "supplier_note",
    "beschreibung": "supplier_note",
}

FIELD_LABELS: dict[str, str] = {
    "sku": "Artikelnummer",
    "supplier": "Lieferant",
    "ean": "EAN",
    "name": "Bezeichnung",
    "brand": "Marke",
    "category": "Kategorie",
    "variant": "Ausführung",
    "nominal": "Nennmaß",
    "length": "Länge",
    "weight": "Gewicht",
    "material": "Material",
    "pieces": "Teile",
    "price": "EK netto",
    "supplier_note": "Beschreibung Lieferant",
}

# Mandatory for every article
REQUIRED_FIELDS = [
    "sku",
    "supplier",
    "ean",
    "name",
    "brand",
    "category",
    "length",
    "weight",
    "price",
]

# --- Category taxonomy ------------------------------------------------------------
# category -> what the nominal dimension means, and which extra field is mandatory
CATEGORIES: dict[str, dict] = {
    "Schraubendreher": {"nominal_label": "Klingenbreite", "requires": ["nominal"]},
    "Bohrer": {"nominal_label": "Durchmesser", "requires": ["nominal"]},
    "Maulschlüssel": {"nominal_label": "Schlüsselweite", "requires": ["nominal"]},
    "Steckschlüsseleinsätze": {"nominal_label": "Schlüsselweite", "requires": ["nominal"]},
    "Zangen": {"nominal_label": None, "requires": []},
    "Bit-Sets": {"nominal_label": None, "requires": ["pieces"]},
}
CATEGORY_UNCLEAR = "unklar"

MATERIAL_SYNONYMS: dict[str, str] = {
    "chrom-vanadium-stahl": "Chrom-Vanadium-Stahl",
    "chrom vanadium": "Chrom-Vanadium-Stahl",
    "crv": "Chrom-Vanadium-Stahl",
    "cr-v": "Chrom-Vanadium-Stahl",
    "hss": "HSS",
    "hss schnellarbeitsstahl": "HSS",
    "hss-co": "HSS-Co",
    "hss-co 5%": "HSS-Co",
    "hssco": "HSS-Co",
    "werkzeugstahl": "Werkzeugstahl",
    "werkzeug-stahl": "Werkzeugstahl",
    "s2-stahl": "S2-Stahl",
    "s2": "S2-Stahl",
    "s2 stahl": "S2-Stahl",
    "edelstahl": "Edelstahl",
    "edelstahl rostfrei": "Edelstahl rostfrei",
    "rostfreier stahl": "Edelstahl rostfrei",
}
# Canonical material names. Only these count as evidence for a claim in generated copy.
KNOWN_MATERIALS = frozenset(MATERIAL_SYNONYMS.values())

# --- Plausibility ranges (after normalisation) -------------------------------------
LENGTH_MM_RANGE = (5.0, 1_000.0)
NOMINAL_MM_RANGE = (0.5, 80.0)
WEIGHT_G_RANGE = (0.5, 10_000.0)
PRICE_EUR_RANGE = (0.05, 5_000.0)

# --- Product copy rules -----------------------------------------------------------
TITLE_MAX_CHARS = 80
DESCRIPTION_MAX_CHARS = 250
DESCRIPTION_MIN_CHARS = 40

# Claims a model likes to add. They may only appear if the same word is in the source.
# key: lower-case pattern (regex), value: German reason shown to the reviewer
UNSUPPORTED_CLAIMS: dict[str, str] = {
    r"\bvde\b": "VDE-Prüfung",
    r"isoliert": "Isolierung",
    r"rostfrei|rostbeständig|korrosionsfest": "Rostschutz",
    r"gehärtet|gehaertet": "Härtung",
    r"\btüv\b|\bgs\b": "Prüfsiegel",
    r"garantie|gewährleistung": "Garantieversprechen",
    r"\bdin\b|\biso\b|\ben\s?\d": "Normangabe",
    r"magnetisch|magnet": "Magnetspitze",
    r"\bprofi\b|\bprofi-|professionell": "Profi-Versprechen",
    # word boundaries on both sides: "besteht aus", "bestehend", "Bestellnummer" are fine
    r"\bbeste[nrs]?\b|\btestsieger\b|nr\.\s?1\b": "Superlativ",
    r"lebenslang": "Lebensdauer-Versprechen",
    r"ergonomisch": "Ergonomie",
}

# The variant is supplier text. It may back a technical mark ("VDE 1000 V isoliert"),
# never a promise: these claims are not accepted from the variant at all.
VARIANT_NEVER_EVIDENCE: frozenset[str] = frozenset(
    {"Garantieversprechen", "Lebensdauer-Versprechen", "Superlativ", "Profi-Versprechen"}
)
# Claims the variant backs only when it also carries the technical value they need.
VARIANT_EVIDENCE_REQUIRES: dict[str, str] = {
    "VDE-Prüfung": r"\bvde\b.*\b\d+\s?v\b",  # VDE only with a voltage, "VDE 1000 V"
}

# --- Models (real mode only) ------------------------------------------------------
TEXT_MODEL = "claude-sonnet-5-5"
CLASSIFY_MODEL = "claude-haiku-5-5"

# --- Themes (dashboard ?firma=<slug>, Excel `pdc build --firma <slug>`) -------------
# A fixed list. The dashboard checks the URL parameter against the same list in
# frontend/public/boot.js and frontend/src/lib/theme.ts (a test keeps all three in sync);
# anything else is "neutral".
# "excel": header fill and header text of the Kennzahlen sheet (hex without #).
DEFAULT_THEME = "neutral"
THEMES: dict[str, dict] = {
    "neutral": {"label": None, "excel": ("2B5BE0", "FFFFFF")},
    "gedore": {"label": "GEDORE Gruppe", "excel": ("1E4FC0", "FFFFFF")},
    "pohl": {"label": "POHL Handels GmbH", "excel": ("1667B8", "FFFFFF")},
    "amalock": {"label": "AMALOCK", "excel": ("0B7A6E", "FFFFFF")},
    "metergrid": {"label": "metergrid", "excel": ("2350D8", "FFFFFF")},
}
