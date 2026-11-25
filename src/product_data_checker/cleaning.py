"""Turn raw supplier strings into typed, normalised product records and find defects."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

import pandas as pd

from . import config
from .ean import normalize_ean
from .ingest import looks_like_formula
from .issues import Issue
from .units import Parsed, is_empty, parse_count, parse_length_mm, parse_price_eur, parse_weight_g

_INSTRUCTION_RE = re.compile(
    r"ignorier|ignore (all|previous)|disregard|anweisung|vergiss|system ?prompt|du bist jetzt"
    r"|you are now",
    re.IGNORECASE,
)

# Supplier fields that are sent to a model. They are short by nature (a brand, a variant
# like "Doppelmaul 12 x 13"), so a hard cap plus an instruction scan keeps prose out.
MODEL_FIELDS = ("name", "brand", "variant", "material")
UNTRUSTED_FIELD_CODES = {"INSTRUCTION_IN_FIELD", "FIELD_TOO_LONG"}


@dataclass
class Product:
    row: int
    sku: str
    supplier: str
    ean: str
    name: str
    brand: str
    category: str
    category_source: str  # "Lieferant" | "Modell" | ""
    variant: str
    nominal_mm: float | None
    length_mm: float | None
    weight_g: float | None
    material: str
    pieces: int | None
    price_eur: float | None
    supplier_note: str
    raw: dict = field(default_factory=dict)  # original strings, for the review sheet
    title: str = ""
    description: str = ""

    def facts(self) -> dict:
        """The only data the text model ever sees: structured, normalised fields.

        The free-text supplier note is deliberately excluded (untrusted input). Brand,
        variant and material are still supplier text: they are capped in length and
        scanned for instructions in ``normalize_rows`` before any model call.
        """
        spec = config.CATEGORIES.get(self.category, {})
        facts = {
            "marke": self.brand,
            "kategorie": self.category,
            "ausfuehrung": self.variant or None,
            "laenge_mm": self.length_mm,
            "gewicht_g": self.weight_g,
            "material": self.material or None,
        }
        if spec.get("nominal_label") and self.nominal_mm is not None:
            facts["nennmass_bezeichnung"] = spec["nominal_label"]
            facts["nennmass_mm"] = self.nominal_mm
        if self.pieces is not None:
            facts["teile"] = self.pieces
        return {k: v for k, v in facts.items() if v not in (None, "")}


def _clean_text(value: str) -> tuple[str, bool]:
    cleaned = re.sub(r"\s+", " ", value).strip()
    return cleaned, cleaned != value


def _match_category(raw: str) -> str | None:
    key = raw.strip().lower()
    for name in config.CATEGORIES:
        if name.lower() == key:
            return name
    return None


def normalize_rows(df: pd.DataFrame) -> tuple[list[Product], list[Issue]]:
    products: list[Product] = []
    issues: list[Issue] = []

    for rec in df.to_dict(orient="records"):
        row = int(rec["row"])
        sku, _ = _clean_text(rec["sku"])
        supplier, _ = _clean_text(rec["supplier"])

        def add(field_name: str, code: str, detail: str, *, _row=row, _sku=sku, _sup=supplier):
            issues.append(Issue(_row, _sku, _sup, field_name, code, detail))

        # Formulas anywhere in the input are reported once per cell; the value itself is
        # only ever used as inert text and neutralised again on every export.
        for name, value in rec.items():
            if name != "row" and looks_like_formula(value) and not is_empty(value):
                add(name, "FORMULA_NEUTRALIZED", f"Zelle begann mit '{value.strip()[0]}'")

        name, changed = _clean_text(rec["name"])
        if changed and name:
            add("name", "VALUE_NORMALIZED", "Leerzeichen bereinigt")
        brand, _ = _clean_text(rec["brand"])
        variant, _ = _clean_text(rec["variant"])

        ean_result = normalize_ean(rec["ean"])
        if ean_result.status == "checksum":
            add("ean", "EAN_CHECKSUM", ean_result.note)
        elif ean_result.status == "format":
            add("ean", "EAN_FORMAT", ean_result.note)
        elif ean_result.status == "scientific":
            add("ean", "EAN_SCIENTIFIC", ean_result.note)
        elif ean_result.status == "ok" and ean_result.note:
            add("ean", "VALUE_NORMALIZED", ean_result.note)

        category = ""
        category_source = ""
        if not is_empty(rec["category"]):
            matched = _match_category(rec["category"])
            if matched:
                category, category_source = matched, "Lieferant"
            else:
                add(
                    "category",
                    "CATEGORY_UNCLEAR",
                    f"'{rec['category'].strip()}' ist keine bekannte Kategorie",
                )

        def measured(field_name: str, parsed: Parsed) -> float | None:
            if parsed.status == "unreadable":
                add(field_name, "UNREADABLE_VALUE", parsed.note)
            elif parsed.note.startswith("Einheit fehlte"):
                add(field_name, "UNIT_ASSUMED", parsed.note)
            elif parsed.note:
                add(field_name, "UNIT_CONVERTED", parsed.note)
            return parsed.value

        nominal = measured("nominal", parse_length_mm(rec["nominal"]))
        length = measured("length", parse_length_mm(rec["length"]))
        weight = measured("weight", parse_weight_g(rec["weight"]))
        price = measured("price", parse_price_eur(rec["price"]))
        pieces_parsed = measured("pieces", parse_count(rec["pieces"]))

        material_raw, _ = _clean_text(rec["material"])
        material = config.MATERIAL_SYNONYMS.get(material_raw.lower(), material_raw)
        if material and material != material_raw:
            add("material", "VALUE_NORMALIZED", f"'{material_raw}' als '{material}' geführt")

        for field_name, value in (
            ("name", name),
            ("brand", brand),
            ("variant", variant),
            ("material", material_raw),
        ):
            limit = config.MODEL_FIELD_MAX_CHARS[field_name]
            if len(value) > limit:
                add(
                    field_name,
                    "FIELD_TOO_LONG",
                    f"{len(value)} Zeichen, erlaubt sind {limit}; das Feld geht ans Modell",
                )
            if _INSTRUCTION_RE.search(value):
                add(
                    field_name,
                    "INSTRUCTION_IN_FIELD",
                    "enthält eine Anweisung an eine KI; der Artikel geht nicht ans Modell",
                )

        note, _ = _clean_text(rec["supplier_note"])
        if _INSTRUCTION_RE.search(note):
            add(
                "supplier_note",
                "UNTRUSTED_SUPPLIER_TEXT",
                "Freitext enthält eine Anweisung; er geht nie ans Modell",
            )

        products.append(
            Product(
                row=row,
                sku=sku,
                supplier=supplier,
                ean=ean_result.code if ean_result.status == "ok" else "",
                name=name,
                brand=brand,
                category=category,
                category_source=category_source,
                variant=variant,
                nominal_mm=nominal,
                length_mm=length,
                weight_g=weight,
                material=material,
                pieces=int(pieces_parsed) if pieces_parsed is not None else None,
                price_eur=price,
                supplier_note=note,
                raw={k: v for k, v in rec.items() if k != "row"},
            )
        )
    return products, issues


def _in_range(value: float | None, bounds: tuple[float, float]) -> bool:
    return value is None or bounds[0] <= value <= bounds[1]


def validate(products: list[Product], issues: list[Issue]) -> list[Issue]:
    """Mandatory fields, category-specific fields, plausibility, duplicates."""
    new: list[Issue] = []
    already = {
        (i.row, i.field)
        for i in issues
        if i.code
        in {"UNREADABLE_VALUE", "EAN_CHECKSUM", "EAN_FORMAT", "EAN_SCIENTIFIC", "CATEGORY_UNCLEAR"}
    }

    values = {
        "sku": lambda p: p.sku,
        "supplier": lambda p: p.supplier,
        "ean": lambda p: p.ean,
        "name": lambda p: p.name,
        "brand": lambda p: p.brand,
        "category": lambda p: p.category,
        "length": lambda p: p.length_mm,
        "weight": lambda p: p.weight_g,
        "price": lambda p: p.price_eur,
        "nominal": lambda p: p.nominal_mm,
        "pieces": lambda p: p.pieces,
    }

    for p in products:

        def add(field_name: str, code: str, detail: str, *, _p=p):
            new.append(Issue(_p.row, _p.sku, _p.supplier, field_name, code, detail))

        required = list(config.REQUIRED_FIELDS)
        required += config.CATEGORIES.get(p.category, {}).get("requires", [])
        for f in required:
            if (p.row, f) in already:
                continue
            if values[f](p) in (None, ""):
                code = "MISSING_DIMENSION" if f in {"length", "nominal"} else "MISSING_REQUIRED"
                add(f, code, f"{config.FIELD_LABELS[f]} fehlt")

        checks = [
            ("length", p.length_mm, config.LENGTH_MM_RANGE, "mm"),
            ("nominal", p.nominal_mm, config.NOMINAL_MM_RANGE, "mm"),
            ("weight", p.weight_g, config.WEIGHT_G_RANGE, "g"),
            ("price", p.price_eur, config.PRICE_EUR_RANGE, "EUR"),
        ]
        for f, value, bounds, unit in checks:
            if not _in_range(value, bounds):
                add(
                    f,
                    "IMPLAUSIBLE_VALUE",
                    f"{value:g} {unit} liegt außerhalb {bounds[0]:g} bis {bounds[1]:g}",
                )
        if p.nominal_mm and p.length_mm and p.nominal_mm >= p.length_mm:
            add("nominal", "IMPLAUSIBLE_VALUE", "Nennmaß ist größer als die Länge")

    first_ean: dict[str, Product] = {}
    first_sku: dict[str, Product] = {}
    for p in products:
        if p.ean:
            if p.ean in first_ean:
                orig = first_ean[p.ean]
                new.append(
                    Issue(
                        p.row,
                        p.sku,
                        p.supplier,
                        "ean",
                        "DUPLICATE_EAN",
                        f"gleiche EAN wie Zeile {orig.row} ({orig.sku})",
                    )
                )
            else:
                first_ean[p.ean] = p
        key = p.sku.lower()
        if key:
            if key in first_sku:
                orig = first_sku[key]
                new.append(
                    Issue(
                        p.row,
                        p.sku,
                        p.supplier,
                        "sku",
                        "DUPLICATE_SKU",
                        f"gleiche Artikelnummer wie Zeile {orig.row}",
                    )
                )
            else:
                first_sku[key] = p
    return new
