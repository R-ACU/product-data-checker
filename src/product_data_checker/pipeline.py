"""End-to-end run: load -> normalise -> classify -> validate -> write copy -> check copy."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import config
from .cleaning import UNTRUSTED_FIELD_CODES, Product, normalize_rows, validate
from .guard import Mark, review_copy
from .ingest import load_supplier_file
from .issues import BLOCKING, Issue
from .llm import Provider, parse_category_answer, parse_text_answer


@dataclass
class RunResult:
    source_file: str
    provider: str
    raw: pd.DataFrame
    products: list[Product]
    issues: list[Issue]
    marks: dict[int, dict[str, list[Mark]]] = field(default_factory=dict)
    missing_info: dict[int, list[str]] = field(default_factory=dict)
    seconds: float = 0.0

    def blocking_rows(self) -> set[int]:
        return {i.row for i in self.issues if i.severity == BLOCKING}

    def released(self) -> list[Product]:
        blocked = self.blocking_rows()
        return [p for p in self.products if p.row not in blocked]

    def to_review(self) -> list[Product]:
        blocked = self.blocking_rows()
        return [p for p in self.products if p.row in blocked]

    def issues_frame(self) -> pd.DataFrame:
        cols = ["row", "sku", "supplier", "field", "code", "detail", "severity", "label"]
        return pd.DataFrame([i.to_record() for i in self.issues], columns=cols)


def _classify_missing(products: list[Product], provider: Provider, issues: list[Issue]) -> None:
    # rows whose category is already disputed, or whose model-bound fields carry an
    # instruction or are too long, are never sent to the classifier
    skip = {i.row for i in issues if i.code in {"CATEGORY_UNCLEAR", *UNTRUSTED_FIELD_CODES}}
    for p in products:
        if p.category or p.row in skip:
            continue
        fields = {"bezeichnung": p.name, "ausfuehrung": p.variant, "material": p.material}
        answer = provider.classify(p.sku, fields)
        category = parse_category_answer(answer.text)
        if category == config.CATEGORY_UNCLEAR:
            reason = answer.error or "Modell konnte nicht eindeutig zuordnen"
            issues.append(Issue(p.row, p.sku, p.supplier, "category", "CATEGORY_UNCLEAR", reason))
        else:
            p.category, p.category_source = category, "Modell"
            issues.append(
                Issue(
                    p.row,
                    p.sku,
                    p.supplier,
                    "category",
                    "CATEGORY_BY_MODEL",
                    f"als '{category}' eingeordnet",
                )
            )


def _write_copy(
    product: Product, provider: Provider
) -> tuple[list[Issue], dict[str, list[Mark]], list[str]]:
    facts = product.facts()
    answer = provider.write_copy(product.sku, facts)
    parsed, parse_error = parse_text_answer(answer.text)

    def issue(code: str, detail: str, fld: str = "text") -> Issue:
        return Issue(product.row, product.sku, product.supplier, fld, code, detail)

    if parsed is None:
        return [issue("TEXT_UNAVAILABLE", answer.error or parse_error)], {}, []
    product.title = parsed.titel.strip()
    product.description = parsed.kurzbeschreibung.strip()
    findings, checks = review_copy(product.title, product.description, facts)
    return [issue(f.code, f.detail) for f in findings], checks, parsed.fehlende_angaben


def run(path: Path, provider: Provider, *, workers: int = 1) -> RunResult:
    started = time.perf_counter()
    raw = load_supplier_file(path)
    products, issues = normalize_rows(raw)
    _classify_missing(products, provider, issues)
    issues += validate(products, issues)

    result = RunResult(
        source_file=Path(path).name,
        provider=provider.name,
        raw=raw,
        products=products,
        issues=issues,
    )

    # Copy is only written for articles whose data passed every check: no tokens are
    # spent on rows that go back to the supplier anyway.
    eligible = [p for p in products if p.row not in result.blocking_rows()]
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        outcomes = list(pool.map(lambda p: _write_copy(p, provider), eligible))
    for product, (new_issues, checks, missing) in zip(eligible, outcomes, strict=True):
        result.issues.extend(new_issues)
        result.marks[product.row] = checks
        if missing:
            result.missing_info[product.row] = missing

    result.issues.sort(key=lambda i: (i.row, i.severity != BLOCKING, i.code))
    result.seconds = time.perf_counter() - started
    return result
