"""Static dashboard: Python writes data.json next to the prebuilt React app, a tiny server shows it.

The app lives in ``frontend/`` (React, Vite, shadcn/ui, Recharts). ``npm run build`` there
writes it into ``dashboard/web/``, which is part of the package, so ``pdc build`` and
``pdc serve`` need no Node.
"""

from __future__ import annotations

import json
import math
import shutil
from collections import Counter
from datetime import UTC, date, datetime
from pathlib import Path

import pandas as pd

from .. import config
from ..metrics import QueryResult
from ..pipeline import RunResult

HERE = Path(__file__).resolve().parent
WEB = HERE / "web"  # built by `npm run build` in frontend/

QUERY_META = {
    "quality_overview": (
        "Überblick eines Laufs",
        "Freigabequote und Vollständigkeit vorher und nachher.",
    ),
    "error_rate_by_supplier": (
        "Fehlerquote je Lieferant",
        "Anteil der Artikel mit mindestens einem blockierenden Befund. Entscheidet, mit wem man über Datenqualität spricht.",
    ),
    "reasons": (
        "Gründe für die Prüfung",
        "Ein Artikel kann mehrere Gründe haben. Stufe zeigt, ob die Daten oder der erzeugte Text auffielen.",
    ),
    "completeness_by_field": (
        "Vollständigkeit je Pflichtfeld",
        "Befüllt heißt: irgendetwas steht drin. Verwendbar heißt: lesbar, gültig, eindeutig.",
    ),
    "completeness_matrix": (
        "Verwendbarkeit je Lieferant und Feld",
        "Grundlage der Heatmap in der Übersicht.",
    ),
    "smard_overview": (
        "Strommarkt 2025 im Überblick",
        "Jahreskennzahlen aus stündlichen SMARD-Daten, Anteil Erneuerbarer gemessen am Verbrauch.",
    ),
    "smard_monthly": (
        "Strommarkt je Monat",
        "Preisniveau, Anteil Erneuerbarer und Stunden mit negativem Preis.",
    ),
    "smard_daily": (
        "Preis je Tag",
        "Grundlage der Preislinie: Tagesmittel, Tiefst- und Höchstwert, Anteil Erneuerbarer.",
    ),
    "smard_price_by_hour": (
        "Preis nach Monat und Tagesstunde",
        "Grundlage der Heatmap; Ortszeit Europe/Berlin.",
    ),
    "smard_price_by_renewable_share": (
        "Preis nach Anteil Erneuerbarer",
        "Stunden in 10-Prozent-Klassen; je mehr Wind und Sonne, desto günstiger.",
    ),
}


def _plain(value):
    """Make pandas/numpy values JSON-safe."""
    if value is None:
        return None
    if isinstance(value, pd.Timestamp | datetime):
        return value.date().isoformat() if isinstance(value, pd.Timestamp) else value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "item"):
        value = value.item()
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    return value


def _records(frame: pd.DataFrame) -> list[dict]:
    return [{k: _plain(v) for k, v in row.items()} for row in frame.to_dict(orient="records")]


def _query_payload(q: QueryResult) -> dict:
    title, description = QUERY_META.get(q.name, (q.name, ""))
    sql_lines = [line for line in q.sql.strip().splitlines()]
    return {
        "name": q.name,
        "title": title,
        "description": description,
        "file": f"sql/{q.name}.sql",
        "sql": "\n".join(sql_lines),
        "columns": list(q.frame.columns),
        "rows": [[_plain(v) for v in row] for row in q.frame.itertuples(index=False)],
    }


def _marks(result: RunResult, row: int) -> dict:
    marks = result.marks.get(row, {})
    return {
        k: [{"s": m.start, "e": m.end, "k": m.kind, "n": m.note} for m in v]
        for k, v in marks.items()
    }


def build_payload(
    result: RunResult, quality: dict[str, QueryResult], smard: dict[str, QueryResult] | None
) -> dict:
    by_row: dict[int, list] = {}
    for i in result.issues:
        by_row.setdefault(i.row, []).append(i)
    blocked = result.blocking_rows()

    def product_payload(p) -> dict:
        issues = by_row.get(p.row, [])
        return {
            "row": p.row,
            "sku": p.sku,
            "supplier": p.supplier or "(ohne Lieferant)",
            "ean": p.ean,
            "name": p.name,
            "brand": p.brand,
            "category": p.category,
            "categorySource": p.category_source,
            "variant": p.variant,
            "nominal": p.nominal_mm,
            "length": p.length_mm,
            "weight": p.weight_g,
            "material": p.material,
            "pieces": p.pieces,
            "price": p.price_eur,
            "title": p.title,
            "description": p.description,
            "marks": _marks(result, p.row),
            "facts": p.facts() if p.category else {},
            "raw": {config.FIELD_LABELS[k]: v for k, v in p.raw.items()},
            "blocking": [
                {
                    "label": i.label,
                    "detail": i.detail,
                    "field": config.FIELD_LABELS.get(i.field, "Text"),
                }
                for i in issues
                if i.severity == "blockierend"
            ],
            "notes": [
                {
                    "label": i.label,
                    "detail": i.detail,
                    "field": config.FIELD_LABELS.get(i.field, "Text"),
                }
                for i in issues
                if i.severity != "blockierend"
            ],
            "missing": result.missing_info.get(p.row, []),
        }

    text_rows = {i.row for i in result.issues if i.code.startswith("TEXT")}
    data_blocked = {
        i.row
        for i in result.issues
        if i.severity == "blockierend" and not i.code.startswith("TEXT")
    }
    written = len(result.marks)  # one request per eligible article, answered or not

    payload = {
        "meta": {
            "sourceFile": result.source_file,
            "provider": result.provider,
            "rows": len(result.products),
            "seconds": round(result.seconds, 3),
            "generatedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "textModel": config.TEXT_MODEL,
            "classifyModel": config.CLASSIFY_MODEL,
            "titleMax": config.TITLE_MAX_CHARS,
            "descriptionMax": config.DESCRIPTION_MAX_CHARS,
        },
        "pipeline": {
            "read": len(result.products),
            "dataBlocked": len(data_blocked),
            "textWritten": written,
            "textBlocked": len(text_rows - data_blocked),
            "released": len(result.products) - len(blocked),
            "classified": sum(1 for p in result.products if p.category_source == "Modell"),
        },
        "overview": _records(quality["quality_overview"].frame)[0],
        "suppliers": _records(quality["error_rate_by_supplier"].frame),
        "reasons": _records(quality["reasons"].frame),
        "fields": _records(quality["completeness_by_field"].frame),
        "matrix": _records(quality["completeness_matrix"].frame),
        "autoFixes": [
            {"label": label, "count": count}
            for label, count in Counter(
                i.label for i in result.issues if i.severity != "blockierend"
            ).most_common()
        ],
        "review": [product_payload(p) for p in result.to_review()],
        "released": [product_payload(p) for p in result.released()],
        "queries": [_query_payload(q) for q in quality.values()],
        "smard": None,
    }
    if smard:
        payload["smard"] = {
            "overview": _records(smard["smard_overview"].frame)[0],
            "monthly": _records(smard["smard_monthly"].frame),
            "daily": _records(smard["smard_daily"].frame),
            "heatmap": _records(smard["smard_price_by_hour"].frame),
            "buckets": _records(smard["smard_price_by_renewable_share"].frame),
            "source": "Bundesnetzagentur | SMARD.de",
            "license": "CC BY 4.0",
            "licenseUrl": "https://creativecommons.org/licenses/by/4.0/deed.de",
            "sourceUrl": "https://www.smard.de",
        }
        payload["queries"] += [_query_payload(q) for q in smard.values()]
    return payload


def write_site(payload: dict, out_dir: Path, downloads: list[Path]) -> Path:
    if not (WEB / "index.html").exists():
        raise FileNotFoundError(
            f"{WEB} fehlt; das Frontend einmal bauen: cd frontend && npm ci && npm run build"
        )
    if out_dir.exists():
        shutil.rmtree(out_dir)
    shutil.copytree(WEB, out_dir)
    (out_dir / "data.json").write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    (out_dir / "downloads").mkdir()
    for path in downloads:
        shutil.copy2(path, out_dir / "downloads" / path.name)
    return out_dir
