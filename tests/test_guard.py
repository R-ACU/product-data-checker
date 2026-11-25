import pytest

from product_data_checker.guard import check_claims, check_numbers, check_rules, review_copy

DRILL = {
    "marke": "Nordfels",
    "kategorie": "Bohrer",
    "ausfuehrung": "Metall",
    "laenge_mm": 84.0,
    "gewicht_g": 14.0,
    "material": "HSS-Co",
    "nennmass_bezeichnung": "Durchmesser",
    "nennmass_mm": 6.0,
}
WRENCH = {
    "marke": "Ostwerk",
    "kategorie": "Maulschlüssel",
    "ausfuehrung": "Doppelmaul 12 x 13",
    "laenge_mm": 198.0,
    "gewicht_g": 79.0,
    "nennmass_mm": 12.0,
}
SOCKET = {
    "marke": "Brennwald",
    "kategorie": "Steckschlüsseleinsätze",
    "ausfuehrung": "1/2 Zoll Antrieb",
    "laenge_mm": 38.0,
    "gewicht_g": 80.0,
    "nennmass_mm": 19.0,
    "material": "Chrom-Vanadium-Stahl",
}
BITS = {
    "marke": "Nordfels",
    "kategorie": "Bit-Sets",
    "ausfuehrung": "PH/PZ/TX gemischt",
    "laenge_mm": 60.0,
    "gewicht_g": 45.0,
    "material": "S2-Stahl",
    "teile": 10,
}


def codes(findings):
    return [f.code for f in findings]


def test_correct_text_passes():
    findings, marks = review_copy(
        "Nordfels Metallbohrer HSS-Co Ø 6 mm, Länge 84 mm",
        "Metallbohrer mit 6 mm Durchmesser und 84 mm Gesamtlänge. Material: HSS-Co. Gewicht 14 g.",
        DRILL,
    )
    assert findings == []
    assert all(m.kind == "ok" for m in marks["title"] + marks["description"])


def test_changed_number_is_caught():
    findings, _ = check_numbers("Gesamtlänge 89 mm", DRILL)
    assert codes(findings) == ["TEXT_NUMBER_MISMATCH"]
    assert "89 mm" in findings[0].detail and "84 mm" in findings[0].detail


def test_unit_conversion_with_same_value_is_accepted():
    assert check_numbers("Länge 8,4 cm, Gewicht 0,014 kg", DRILL)[0] == []


def test_wrong_unit_is_caught():
    # 0,14 kg would be 140 g, the source says 14 g
    assert codes(check_numbers("Gewicht 0,14 kg", DRILL)[0]) == ["TEXT_NUMBER_MISMATCH"]


def test_invented_bare_number_is_caught():
    assert codes(check_numbers("Set mit 18 Teilen", BITS)[0]) == ["TEXT_NUMBER_MISMATCH"]
    assert check_numbers("Set mit 10 Teilen", BITS)[0] == []


def test_variant_numbers_and_names_are_allowed():
    assert check_numbers("Doppelmaulschlüssel 12 x 13 mm, Länge 198 mm", WRENCH)[0] == []
    assert check_numbers("Antrieb 1/2 Zoll, SW 19 mm", SOCKET)[0] == []
    assert check_numbers("Bits PH/PZ/TX, S2-Stahl", BITS)[0] == []


def test_fraction_tokens_cannot_be_borrowed_as_lengths():
    # "1/2" in the variant must not make "1 mm" or "2 mm" acceptable
    assert codes(check_numbers("Länge 2 mm", SOCKET)[0]) == ["TEXT_NUMBER_MISMATCH"]


def test_claims_without_source_are_flagged():
    text = "VDE-geprüft, rostfrei, mit lebenslanger Garantie, ideal für Profis"
    findings, marks = check_claims(text, DRILL)
    labels = {f.detail.split(":")[0] for f in findings}
    assert {"VDE-Prüfung", "Rostschutz", "Garantieversprechen", "Lebensdauer-Versprechen"} <= labels
    assert {m.kind for m in marks} == {"claim"}


def test_claim_is_fine_when_source_has_it():
    facts = dict(DRILL, material="Edelstahl rostfrei")
    assert check_claims("Material rostfrei", facts)[0] == []


def test_profil_is_not_profi():
    assert check_claims("Schraubendreher mit Schlitz-Profil", DRILL)[0] == []


def test_rules():
    long_title = "x" * 81
    assert codes(check_rules(long_title, "y" * 60)) == ["TEXT_RULE_VIOLATION"]
    found = check_rules("- Titel", "Siehe www.example.invalid <b>fett</b>")
    details = " ".join(f.detail for f in found)
    assert "Formel-Zeichen" in details and "Link" in details and "HTML" in details
    assert check_rules("Titel", "kurz")  # description too short
    assert "Emojis" in " ".join(f.detail for f in check_rules("Titel \U0001f527", "y" * 60))
    assert (
        check_rules("Titel ok", "Eine sachliche Beschreibung mit genug Zeichen für die Regel.")
        == []
    )


def test_duplicate_findings_are_merged():
    findings, _ = review_copy("Bohrer 89 mm", "Länge 89 mm, " + "x" * 40, DRILL)
    assert codes(findings).count("TEXT_NUMBER_MISMATCH") == 1


def test_marks_point_at_the_right_text():
    text = "Länge 89 mm, Gewicht 14 g"
    _, marks = check_numbers(text, DRILL)
    assert [(text[m.start : m.end], m.kind) for m in marks] == [("89 mm", "bad"), ("14 g", "ok")]


def test_digits_in_names_are_checked_but_not_highlighted():
    text = "Bits PH/PZ/TX, S2-Stahl, 10 Teile"
    findings, marks = check_numbers(text, BITS)
    assert findings == []
    assert [text[m.start : m.end] for m in marks] == ["10"]
    # a wrong digit inside a name is still caught
    assert check_numbers("S3-Stahl", BITS)[0]


# --- Regression catalogue: correct German copy that must never be blocked ------------
# Real model text says "besteht aus" far more often than the mock's "Material: X." The
# superlative pattern used to match inside "besteht", "bestehend" and "Bestellnummer".
ALLOWED_SENTENCES = [
    (DRILL, "Der Bohrer besteht aus HSS-Co und ist 84 mm lang."),
    (DRILL, "Metallbohrer bestehend aus HSS-Co, Durchmesser 6 mm, Gesamtlänge 84 mm."),
    (DRILL, "Die Bestellnummer steht auf dem Etikett. Gewicht 14 g."),
    (DRILL, "Gefertigt aus HSS-Co; der Schaft besteht aus einem Stück."),
    (SOCKET, "Der Einsatz besteht aus Chrom-Vanadium-Stahl, Schlüsselweite 19 mm."),
    (BITS, "Das Set besteht aus 10 Teilen aus S2-Stahl in einer 60 mm langen Box."),
    (WRENCH, "Doppelmaulschlüssel mit den Schlüsselweiten 12 und 13 mm, Länge 198 mm."),
    (dict(DRILL, ausfuehrung="Magnethalter"), "Bithalter mit Magnethalter, Länge 84 mm."),
    (DRILL, "Material: HSS-Co. Gewicht 14 g, Länge 8,4 cm."),
]


@pytest.mark.parametrize("facts, text", ALLOWED_SENTENCES)
def test_regression_catalogue_correct_text_passes(facts, text):
    findings, _ = review_copy("Titel ohne Zahl", text, facts)
    assert findings == [], findings


@pytest.mark.parametrize(
    "text, label",
    [
        ("Der beste Bohrer im Sortiment.", "Superlativ"),
        ("Unser bester Schraubendreher.", "Superlativ"),
        ("Testsieger bei Handwerkern.", "Superlativ"),
        ("Die Nr. 1 im Werkzeughandel.", "Superlativ"),
        ("Mit praktischem Magnethalter.", "Magnetspitze"),  # no magnet in the source
    ],
)
def test_real_claims_are_still_caught(text, label):
    findings, _ = check_claims(text, DRILL)
    assert [f.detail.split(":")[0] for f in findings] == [label]


# --- Supplier prose is not evidence ---------------------------------------------------


def test_prose_in_variant_does_not_count_as_evidence():
    facts = dict(DRILL, ausfuehrung="VDE-geprüft, lebenslange Garantie")
    findings, _ = check_claims("VDE-geprüft, mit lebenslanger Garantie.", facts)
    assert {f.detail.split(":")[0] for f in findings} >= {"VDE-Prüfung", "Garantieversprechen"}


def test_non_canonical_material_does_not_count_as_evidence():
    facts = dict(DRILL, material="rostfrei und gehärtet, VDE")
    assert check_claims("Rostfrei und gehärtet.", facts)[0]


def test_brand_is_never_evidence():
    facts = dict(DRILL, marke="Profi Garantie")
    assert check_claims("Mit Garantie.", facts)[0]


def test_short_spec_variant_still_counts():
    facts = dict(DRILL, ausfuehrung="VDE 1000 V isoliert")
    assert check_claims("VDE-geprüft und isoliert.", facts)[0] == []


def test_spec_like_variant_cannot_back_promises():
    """R-C-01: a short variant without punctuation is still no evidence for a promise."""
    facts = dict(DRILL, ausfuehrung="VDE geprüft lebenslange Garantie")
    findings, _ = check_claims("Bohrer, VDE geprüft mit lebenslanger Garantie.", facts)
    labels = {f.detail.split(":")[0] for f in findings}
    assert {"VDE-Prüfung", "Garantieversprechen", "Lebensdauer-Versprechen"} <= labels


@pytest.mark.parametrize(
    "variant, text, label",
    [
        ("Profi Ausführung", "Für Profis gemacht, Profi-Qualität.", "Profi-Versprechen"),
        ("beste Qualität", "Die beste Wahl für die Werkstatt.", "Superlativ"),
        ("Testsieger Metall", "Testsieger im Vergleich.", "Superlativ"),
        ("Garantie 5 Jahre", "Mit Garantie.", "Garantieversprechen"),
        ("lebenslang scharf", "Bleibt lebenslang scharf.", "Lebensdauer-Versprechen"),
        ("VDE Griff", "VDE-geprüfter Griff.", "VDE-Prüfung"),
    ],
)
def test_variant_never_backs_promises_or_vde_without_voltage(variant, text, label):
    findings, _ = check_claims(text, dict(DRILL, ausfuehrung=variant))
    assert label in {f.detail.split(":")[0] for f in findings}


@pytest.mark.parametrize("variant", ["VDE 1000 V", "VDE 1000V isoliert", "isoliert VDE 1000 V"])
def test_vde_with_voltage_in_variant_still_counts(variant):
    assert check_claims("VDE-geprüft für 1000 V.", dict(DRILL, ausfuehrung=variant))[0] == []


# --- Bypass attempts on the link, HTML and claim rules ------------------------------
BYPASSES = [
    "Mehr auf zangen.shop/x zu diesem Artikel.",
    "Infos unter beispiel.eu zu diesem Artikel.",
    "Siehe HTTPS://example.invalid/datenblatt bitte.",
    "Datenblatt per ftp://files.example.invalid/x laden.",
    "<img src=x onerror=alert(document.domain) class=aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa>",
    "Kontakt javascript:alert(document.cookie) bitte.",
    "Griff V\u200bDE-geprüft und sehr bequem.",  # zero-width space
    "Klinge Rost\u00adfrei und sehr bequem zu halten.",  # soft hyphen
    "Griff VD\u0415-geprüft und sehr bequem.",  # Cyrillic Е
    "Griff \uff36\uff24\uff25-geprüft und sehr bequem.",  # full-width VDE
    "Bohrer \u202eVDE\u202c mit Richtungszeichen im Text.",  # bidi override
]


@pytest.mark.parametrize("text", BYPASSES)
def test_bypass_variants_are_blocked(text):
    findings, _ = review_copy("Nordfels Bohrer", text + " Länge 84 mm.", DRILL)
    assert findings, text


def test_sentence_ends_are_not_links():
    text = "Material: HSS-Co. Gewicht 14 g. Länge 84 mm, z. B. für Stahl."
    assert check_rules("Nordfels Bohrer", text) == []


def test_marks_skip_normalised_text_but_findings_stay():
    findings, marks = review_copy(
        "Bohrer", "Klinge Rost\u00adfrei, Länge 89 mm, " + "x" * 20, DRILL
    )
    found = {f.code for f in findings}
    assert {"TEXT_RULE_VIOLATION", "TEXT_UNSUPPORTED_CLAIM", "TEXT_NUMBER_MISMATCH"} <= found
    assert marks["description"] == []
