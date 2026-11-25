"""Build the mock model answers in fixtures/llm/ for the demo supplier list.

These are NOT real Claude outputs. They are written by a fixed template from the same
facts the real model would receive, so the demo and the tests run offline and for free.
To prove that the guard works, a handful of answers contain planted mistakes that are
typical for language models (a changed number, an invented certification, a bullet
dash at the start, prose instead of JSON). The list of planted mistakes is stored next
to the answers under "_planted" so tests can assert that every one of them is caught.

    uv run python scripts/build_mock_fixtures.py
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from product_data_checker import config
from product_data_checker.cleaning import normalize_rows, validate
from product_data_checker.ingest import load_supplier_file
from product_data_checker.issues import BLOCKING
from product_data_checker.units import format_number_de as n

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "llm"

KEYWORDS = [
    ("schraubendreher", "Schraubendreher"),
    ("bohrer", "Bohrer"),
    ("maulschlüssel", "Maulschlüssel"),
    ("steckschlüssel", "Steckschlüsseleinsätze"),
    ("zange", "Zangen"),
    ("seitenschneider", "Zangen"),
    ("bit-set", "Bit-Sets"),
]


def recorded_category(name: str) -> str:
    lowered = name.lower()
    for needle, category in KEYWORDS:
        if needle in lowered:
            return category
    return config.CATEGORY_UNCLEAR


def template_copy(facts: dict) -> dict:
    brand, cat = facts["marke"], facts["kategorie"]
    variant = facts.get("ausfuehrung", "")
    length = facts.get("laenge_mm")
    weight = facts.get("gewicht_g")
    material = facts.get("material")
    nominal = facts.get("nennmass_mm")
    label = facts.get("nennmass_bezeichnung", "")
    mat_title = f", {material}" if material else ""
    mat_sentence = f" Material: {material}." if material else ""

    if cat == "Schraubendreher":
        title = f"{brand} Schraubendreher {variant} {n(nominal)} x {n(length)} mm{mat_title}"
        desc = (
            f"Schraubendreher mit {variant}-Profil, {label} {n(nominal)} mm, Länge "
            f"{n(length)} mm.{mat_sentence} Gewicht {n(weight)} g."
        )
    elif cat == "Bohrer":
        title = f"{brand} {variant}bohrer {material or ''} Ø {n(nominal)} mm, Länge {n(length)} mm"
        desc = (
            f"{variant}bohrer mit {n(nominal)} mm Durchmesser und {n(length)} mm "
            f"Gesamtlänge.{mat_sentence} Gewicht {n(weight)} g."
        )
    elif cat == "Maulschlüssel":
        title = f"{brand} {variant} mm, Länge {n(length)} mm{mat_title}"
        desc = (
            f"Doppelmaulschlüssel mit den Schlüsselweiten aus der Ausführung {variant} mm, "
            f"Länge {n(length)} mm.{mat_sentence} Gewicht {n(weight)} g."
        )
    elif cat == "Steckschlüsseleinsätze":
        title = f"{brand} Steckschlüsseleinsatz {variant}, SW {n(nominal)} mm{mat_title}"
        desc = (
            f"Steckschlüsseleinsatz für {variant}, Schlüsselweite {n(nominal)} mm, "
            f"Länge {n(length)} mm.{mat_sentence} Gewicht {n(weight)} g."
        )
    elif cat == "Zangen":
        title = f"{brand} {variant} {n(length)} mm{mat_title}"
        desc = f"{variant} mit einer Länge von {n(length)} mm.{mat_sentence} Gewicht {n(weight)} g."
    else:  # Bit-Sets
        pieces = facts.get("teile")
        title = f"{brand} Bit-Set {pieces}-teilig, {variant}{mat_title}"
        desc = (
            f"Bit-Set mit {pieces} Teilen, Bits in der Ausführung {variant}.{mat_sentence} "
            f"Länge der Box {n(length)} mm, Gewicht {n(weight)} g."
        )
    title = re.sub(r"\s+", " ", title).strip()
    missing = [k for k in ("material",) if k not in facts]
    return {"titel": title, "kurzbeschreibung": desc, "fehlende_angaben": missing}


# (index among eligible products, what goes wrong, how to break the answer)
def plant(copy: dict, kind: str, facts: dict) -> dict | str:
    c = dict(copy)
    if kind == "changed_length":
        old = n(facts["laenge_mm"])
        c["kurzbeschreibung"] = c["kurzbeschreibung"].replace(
            f"{old} mm", f"{n(facts['laenge_mm'] + 5)} mm", 1
        )
    elif kind == "wrong_weight_unit":
        c["kurzbeschreibung"] = c["kurzbeschreibung"].replace(
            f"Gewicht {n(facts['gewicht_g'])} g", f"Gewicht {n(facts['gewicht_g'] / 100)} kg"
        )
    elif kind == "vde_claim":
        c["kurzbeschreibung"] = c["kurzbeschreibung"].rstrip(".") + ", VDE-geprüft bis 1000 V."
    elif kind == "rust_claim":
        c["kurzbeschreibung"] = c["kurzbeschreibung"].replace(".", ", rostfrei.", 1)
    elif kind == "warranty_claim":
        c["kurzbeschreibung"] += " Mit lebenslanger Garantie."
    elif kind == "title_too_long":
        c["titel"] = c["titel"] + " für Werkstatt, Montage, Industrie und Heimwerker"
    elif kind == "bullet_dash":
        c["titel"] = "- " + c["titel"]
    elif kind == "wrong_pieces":
        c["titel"] = c["titel"].replace(f"{facts['teile']}-teilig", f"{facts['teile'] + 8}-teilig")
    elif kind == "link":
        c["kurzbeschreibung"] += " Datenblatt unter www.example.invalid."
    elif kind == "prose_not_json":
        return f"Gerne! Hier ist ein Vorschlag: {c['titel']}. {c['kurzbeschreibung']}"
    elif kind.startswith("natural_phrasing_ok"):
        # Correct, phrased the way a real model writes German copy. "besteht aus",
        # "bestehend aus" and "Bestellnummer" once tripped the superlative rule.
        material = facts["material"]
        phrasing = NATURAL_PHRASINGS[int(kind.rsplit(":", 1)[1])].format(material=material)
        c["kurzbeschreibung"] = c["kurzbeschreibung"].replace(f" Material: {material}.", phrasing)
        return json.dumps(c, ensure_ascii=False)
    elif kind == "unit_converted_ok":
        # Correct, but in cm: the guard must accept 12,5 cm for 125 mm.
        old = n(facts["laenge_mm"])
        c["kurzbeschreibung"] = c["kurzbeschreibung"].replace(
            f"{old} mm", f"{n(facts['laenge_mm'] / 10)} cm", 1
        )
        return json.dumps(c, ensure_ascii=False)
    else:
        raise ValueError(kind)
    return json.dumps(c, ensure_ascii=False) if isinstance(c, dict) else c


NATURAL_PHRASINGS = [
    " Der Artikel besteht aus {material}.",
    " Bestehend aus {material}.",
    " Er besteht aus {material}; die Bestellnummer steht auf der Verpackung.",
]

PLANTED = [
    (3, "changed_length"),
    (11, "wrong_weight_unit"),
    (19, "vde_claim"),
    (27, "rust_claim"),
    (35, "warranty_claim"),
    (43, "title_too_long"),
    (51, "bullet_dash"),
    (59, "wrong_pieces"),
    (67, "link"),
    (75, "prose_not_json"),
]
ACCEPTED_VARIANTS = [
    (7, "unit_converted_ok"),
    (15, "unit_converted_ok"),
    (23, "natural_phrasing_ok:0"),
    (31, "natural_phrasing_ok:1"),
    (47, "natural_phrasing_ok:2"),
]


def main() -> None:
    df = load_supplier_file(ROOT / "data" / "raw" / "lieferantenliste.xlsx")
    products, issues = normalize_rows(df)

    categories: dict = {}
    for p in products:
        if not p.category:
            category = recorded_category(p.name)
            categories[p.sku] = {"raw": json.dumps({"kategorie": category}, ensure_ascii=False)}
            p.category = category
    # one recorded answer outside the taxonomy, which the parser must refuse
    first_missing = next(iter(categories))
    categories[first_missing] = {"raw": json.dumps({"kategorie": "Handwerkzeug"})}
    next(p for p in products if p.sku == first_missing).category = ""
    issues += validate(products, issues)
    blocked = {i.row for i in issues if i.severity == BLOCKING}

    texts: dict = {}
    eligible = [p for p in products if p.category in config.CATEGORIES]
    with_facts = []
    for p in eligible:
        facts = p.facts()
        needed = {"marke", "laenge_mm", "gewicht_g"}
        needed |= (
            {"nennmass_mm"} if config.CATEGORIES[p.category]["requires"] == ["nominal"] else set()
        )
        needed |= {"teile"} if p.category == "Bit-Sets" else set()
        if not needed <= facts.keys():
            continue  # never reaches the model: data checks block it first
        if p.row not in blocked:
            with_facts.append((p, facts))  # planting only where the guard will look
        texts[p.sku] = {"raw": json.dumps(template_copy(facts), ensure_ascii=False)}

    planted_log = []
    for index, kind in PLANTED + ACCEPTED_VARIANTS:
        candidates = with_facts[index:] + with_facts[:index]
        if kind == "wrong_pieces":
            candidates = [c for c in candidates if c[0].category == "Bit-Sets"]
        if kind in ("vde_claim",):
            candidates = [c for c in candidates if c[0].category in ("Schraubendreher", "Zangen")]
        if kind.startswith("natural_phrasing_ok"):
            candidates = [c for c in candidates if "material" in c[1]]
        planted_skus = {e["sku"] for e in planted_log}
        product, facts = next(c for c in candidates if c[0].sku not in planted_skus)
        copy = json.loads(texts[product.sku]["raw"])
        texts[product.sku] = {"raw": plant(copy, kind, facts)}
        planted_log.append(
            {
                "sku": product.sku,
                "kind": kind.split(":")[0],
                "should_block": not kind.endswith("_ok") and "_ok:" not in kind,
            }
        )

    FIXTURES.mkdir(parents=True, exist_ok=True)
    texts_out = {
        "_note": "Template-generated stand-ins for model answers, not real Claude output.",
        "_planted": planted_log,
        **texts,
    }
    cats_out = {
        "_note": "Recorded classification answers for rows without a category.",
        "_planted": [{"sku": first_missing, "kind": "outside_taxonomy"}],
        **categories,
    }
    (FIXTURES / "texts.json").write_text(
        json.dumps(texts_out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    (FIXTURES / "categories.json").write_text(
        json.dumps(cats_out, ensure_ascii=False, indent=1), encoding="utf-8"
    )
    print(
        f"{len(texts)} text answers, {len(categories)} category answers, "
        f"{len(planted_log)} planted variants"
    )


if __name__ == "__main__":
    main()
