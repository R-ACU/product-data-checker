"""Check generated product copy against its source data.

The model is never trusted: every number in the title and description must come from
the facts it was given (a measurement may change unit, 125 mm = 12,5 cm, but not its
value), risky claims need a source, and the format rules are enforced in code.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

from . import config
from .ingest import looks_like_formula
from .units import format_number_de

_FRACTION = r"\d+/\d+"
_NUMBER = r"\d+(?:[.,]\d+)?"
_TOKEN_RE = re.compile(
    rf"(?P<num>{_FRACTION}|{_NUMBER})(?:\s*(?P<unit>mm|cm|kg|g|m)(?![a-zäöüß]))?",
    re.IGNORECASE,
)
# Any scheme, any "www.", and any bare domain such as "zangen.shop/x" or "beispiel.eu".
# A space after the dot ("HSS-Co. Gewicht") is a sentence, not a domain.
_URL_RE = re.compile(
    r"\b[a-z][a-z0-9+.-]*://|\bwww\.|\b(?:mailto|javascript|data):|\b[\w-]+\.[a-z]{2,}(?:/|\b)",
    re.IGNORECASE,
)
_HTML_RE = re.compile(r"[<>]")  # product copy never needs angle brackets
_EMOJI_RE = re.compile("[\U0001f300-\U0001faff☀-➿]")

UNIT_TO_BASE = {
    "mm": ("length", 1.0),
    "cm": ("length", 10.0),
    "m": ("length", 1000.0),
    "g": ("weight", 1.0),
    "kg": ("weight", 1000.0),
}


@dataclass(frozen=True)
class Finding:
    code: str  # issue code from issues.ISSUE_TYPES
    detail: str


@dataclass(frozen=True)
class Mark:
    """A checked span of the text, for the dashboard's highlighted view."""

    start: int
    end: int
    kind: str  # "ok" (number found in source) | "bad" (number not in source) | "claim"
    note: str = ""


def normalize_text(text: str) -> str:
    """NFKC (full-width letters, ligatures) and without invisible format characters.

    Claims and numbers are checked on this form, so a zero-width space inside "VDE",
    a soft hyphen inside "rostfrei" or full-width letters cannot slip past the claim list.
    """
    folded = unicodedata.normalize("NFKC", text)
    return "".join(ch for ch in folded if unicodedata.category(ch) != "Cf")


def _hidden_chars(text: str) -> bool:
    return any(unicodedata.category(ch) == "Cf" for ch in text)


def _non_latin_letters(text: str) -> list[str]:
    """Letters outside the Latin script, e.g. a Cyrillic "Е" posing as "E"."""
    return sorted(
        {
            ch
            for ch in unicodedata.normalize("NFKC", text)
            if ch.isalpha() and "LATIN" not in unicodedata.name(ch, "")
        }
    )


def _norm_number(text: str) -> str:
    if "/" in text:
        return text
    value = float(text.replace(",", "."))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _source_numbers(facts: dict) -> tuple[set[str], dict[str, set[float]]]:
    """Bare number tokens the model was given, and measured values per dimension.

    Sizes written inside the variant ("Doppelmaul 12 x 13") are mm by convention of the
    tool trade, so they count as length values too.
    """
    tokens: set[str] = set()
    measures: dict[str, set[float]] = {"length": set(), "weight": set()}
    for m in re.finditer(rf"{_FRACTION}|{_NUMBER}", str(facts.get("ausfuehrung", ""))):
        if "/" not in m.group(0):
            measures["length"].add(round(float(m.group(0).replace(",", ".")), 2))
    for key, value in facts.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            tokens.add(_norm_number(str(value)))
            if key.endswith("_mm"):
                measures["length"].add(round(float(value), 2))
            elif key.endswith("_g"):
                measures["weight"].add(round(float(value), 2))
        elif isinstance(value, str):
            for m in re.finditer(rf"{_FRACTION}|{_NUMBER}", value):
                tokens.add(_norm_number(m.group(0)))
    return tokens, measures


def check_numbers(text: str, facts: dict) -> tuple[list[Finding], list[Mark]]:
    tokens, measures = _source_numbers(facts)
    findings: list[Finding] = []
    checks: list[Mark] = []
    for m in _TOKEN_RE.finditer(text):
        raw_num, unit = m.group("num"), (m.group("unit") or "").lower()
        # digits glued to letters (PH2, TX20, S2) are names; compare them as tokens too
        ok: bool
        if unit:
            dimension, factor = UNIT_TO_BASE[unit]
            if "/" in raw_num:
                ok = False
            else:
                base = round(float(raw_num.replace(",", ".")) * factor, 2)
                ok = any(abs(base - v) < 0.01 for v in measures[dimension])
            if not ok:
                known = (
                    ", ".join(
                        f"{format_number_de(v)} {'mm' if dimension == 'length' else 'g'}"
                        for v in sorted(measures[dimension])
                    )
                    or "keine"
                )
                findings.append(
                    Finding(
                        "TEXT_NUMBER_MISMATCH",
                        f"'{m.group(0).strip()}' steht nicht in der Quelle (Quelle: {known})",
                    )
                )
        else:
            ok = _norm_number(raw_num) in tokens
            if not ok:
                findings.append(
                    Finding("TEXT_NUMBER_MISMATCH", f"Zahl '{raw_num}' steht nicht in der Quelle")
                )
        span = m.group(0).rstrip()
        glued = m.start() > 0 and text[m.start() - 1].isalpha()  # PH2, S2, TX20: part of a name
        if not (glued and ok):  # checked either way; only highlighted when it is a quantity
            checks.append(Mark(m.start(), m.start() + len(span), "ok" if ok else "bad"))
    return findings, checks


# A variant counts as evidence only while it looks like a short spec ("Doppelmaul 12 x 13",
# "VDE 1000 V"), not like prose: few words, no sentence punctuation.
_PROSE_RE = re.compile(r"[!?:;\"'<>()]|[.,](?!\d)")


def _variant_evidence(facts: dict) -> str:
    """The variant, normalised, if it reads like a spec; otherwise an empty string."""
    variant = str(facts.get("ausfuehrung", ""))
    if variant and len(variant.split()) <= 6 and not _PROSE_RE.search(variant):
        return normalize_text(variant).lower()
    return ""


def claim_evidence(facts: dict, label: str | None = None) -> str:
    """Source text a claim may rely on: controlled values only, never free supplier prose.

    Category and nominal label come from the taxonomy, material only in a canonical
    spelling from ``config.MATERIAL_SYNONYMS``. The variant counts only if it reads like a
    spec, never for promises (``config.VARIANT_NEVER_EVIDENCE``) and for some marks only
    together with their technical value (``config.VARIANT_EVIDENCE_REQUIRES``).
    Brand and anything else are never evidence.
    """
    parts = [str(facts.get("kategorie", "")), str(facts.get("nennmass_bezeichnung", ""))]
    material = facts.get("material")
    if material in config.KNOWN_MATERIALS:
        parts.append(material)
    source = normalize_text(" ".join(parts)).lower()
    variant = _variant_evidence(facts)
    if not variant or label in config.VARIANT_NEVER_EVIDENCE:
        return source
    required = config.VARIANT_EVIDENCE_REQUIRES.get(label or "")
    if required and not re.search(required, variant):
        return source
    return f"{source} {variant}"


def check_claims(text: str, facts: dict) -> tuple[list[Finding], list[Mark]]:
    normalized = normalize_text(text)
    lowered = normalized.lower()
    # marks point into the original text; only valid when normalising changed nothing
    can_mark = normalized == text
    findings: list[Finding] = []
    marks: list[Mark] = []
    for pattern, label in config.UNSUPPORTED_CLAIMS.items():
        if re.search(pattern, claim_evidence(facts, label)):
            continue
        for hit in re.finditer(pattern, lowered):
            findings.append(
                Finding("TEXT_UNSUPPORTED_CLAIM", f"{label}: '{hit.group(0)}' ohne Beleg")
            )
            if can_mark:
                marks.append(Mark(hit.start(), hit.end(), "claim", label))
    return findings, marks


def check_rules(title: str, description: str) -> list[Finding]:
    findings = []

    def rule(detail: str) -> None:
        findings.append(Finding("TEXT_RULE_VIOLATION", detail))

    if not title.strip():
        rule("Titel ist leer")
    if len(title) > config.TITLE_MAX_CHARS:
        rule(f"Titel hat {len(title)} Zeichen, erlaubt sind {config.TITLE_MAX_CHARS}")
    if len(description) > config.DESCRIPTION_MAX_CHARS:
        rule(
            f"Beschreibung hat {len(description)} Zeichen, erlaubt sind {config.DESCRIPTION_MAX_CHARS}"
        )
    if len(description) < config.DESCRIPTION_MIN_CHARS:
        rule(f"Beschreibung hat nur {len(description)} Zeichen")
    for label, value in (("Titel", title), ("Beschreibung", description)):
        if looks_like_formula(value):
            rule(f"{label} beginnt mit '{value.lstrip()[0]}' (Formel-Zeichen)")
        if "\n" in value or "\r" in value:
            rule(f"{label} enthält Zeilenumbrüche")
        plain = normalize_text(value)
        if _URL_RE.search(plain):
            rule(f"{label} enthält einen Link")
        if _HTML_RE.search(plain):
            rule(f"{label} enthält HTML oder spitze Klammern")
        if _EMOJI_RE.search(value):
            rule(f"{label} enthält Emojis")
        if _hidden_chars(value):
            rule(f"{label} enthält unsichtbare Steuerzeichen")
        if foreign := _non_latin_letters(value):
            rule(f"{label} enthält Buchstaben fremder Schrift ({''.join(foreign[:5])})")
    return findings


def review_copy(
    title: str, description: str, facts: dict
) -> tuple[list[Finding], dict[str, list[Mark]]]:
    """All checks on one generated text. Returns findings and the marks per field."""
    findings = check_rules(title, description)
    marks: dict[str, list[Mark]] = {}
    for name, text in (("title", title), ("description", description)):
        normalized = normalize_text(text)
        num_findings, num_marks = check_numbers(normalized, facts)
        if normalized != text:
            num_marks = []  # positions would not match the original text
        claim_findings, claim_marks = check_claims(text, facts)
        findings += num_findings + claim_findings
        marks[name] = sorted(num_marks + claim_marks, key=lambda m: m.start)
    unique = list(dict.fromkeys(findings))  # same defect in title and text counts once
    return unique, marks
