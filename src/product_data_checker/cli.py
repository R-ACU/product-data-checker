"""Command line: ``pdc build`` runs everything, ``pdc serve`` shows the dashboard."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .ingest import InputRejected

DEFAULT_INPUT = config.PROJECT_ROOT / "data" / "raw" / "lieferantenliste.xlsx"
DEFAULT_OUT = config.PROJECT_ROOT / "build"
SMARD_CSV = config.PROJECT_ROOT / "data" / "smard" / "smard_hourly.csv"
FIXTURES = config.PROJECT_ROOT / "fixtures" / "llm"
ENV_FILE = config.PROJECT_ROOT / ".env"
DEFAULT_PORT = 3230


def _provider(mode: str, out: Path):
    from .llm import ClaudeProvider, MockProvider, load_api_key

    if mode == "mock":
        return MockProvider(FIXTURES)
    key = load_api_key(ENV_FILE)
    if not key:
        raise SystemExit(
            "Echter Modus braucht ANTHROPIC_API_KEY in der lokalen .env (siehe .env.example)."
        )
    return ClaudeProvider(api_key=key, cache_dir=out / "cache" / "llm")


def cmd_build(args: argparse.Namespace) -> int:
    from .dashboard import build_payload, write_site
    from .metrics import quality_metrics, smard_metrics
    from .pipeline import run
    from .report_excel import write_csv, write_excel

    out: Path = args.out
    provider = _provider(args.mode, out)
    try:
        result = run(args.input, provider, workers=4 if args.mode == "claude" else 1)
    except InputRejected as exc:
        print(f"Datei abgelehnt: {exc}", file=sys.stderr)
        return 2

    quality = quality_metrics(result)
    smard = smard_metrics(SMARD_CSV) if SMARD_CSV.exists() else None
    xlsx = write_excel(result, quality, out / "ergebnis.xlsx", firma=args.firma)
    csv_path = write_csv(result, out / "sauber.csv")
    payload = build_payload(result, quality, smard)
    site = write_site(payload, out / "site", [xlsx, csv_path])

    summary = {
        "input": result.source_file,
        "mode": provider.name,
        "articles": len(result.products),
        "released": len(result.released()),
        "to_review": len(result.to_review()),
        "seconds": round(result.seconds, 3),
    }
    if hasattr(provider, "usage"):
        summary["api_usage"] = provider.usage
    (out / "run.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        f"{summary['articles']} Artikel: {summary['released']} freigegeben, "
        f"{summary['to_review']} zur Prüfung ({summary['seconds']} s, Modus {provider.name})"
    )
    print(f"Excel:     {xlsx}")
    print(f"CSV:       {csv_path}")
    print(f"Dashboard: {site / 'index.html'}  ->  pdc serve")
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    from .server import make_server, port_is_free

    port = args.port
    while not port_is_free(port):  # never kill a foreign process; take the next port
        print(f"Port {port} ist belegt, versuche {port + 1}")
        port += 1
    server = make_server(args.dir, port)
    print(f"Dashboard läuft auf http://127.0.0.1:{port}/  (Strg+C beendet)")
    for slug in list(config.THEMES)[1:]:
        print(f"  Theme {slug}: http://127.0.0.1:{port}/?firma={slug}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pdc", description="Produktdaten-Prüfer")
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("build", help="Liste prüfen, Excel, CSV und Dashboard erzeugen")
    b.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    b.add_argument("--out", type=Path, default=DEFAULT_OUT)
    b.add_argument(
        "--mode",
        choices=["mock", "claude"],
        default="mock",
        help="mock: feste Antworten aus fixtures/ (Standard); claude: echte API",
    )
    b.add_argument(
        "--firma",
        choices=list(config.THEMES),
        default=config.DEFAULT_THEME,
        help="Farbe des Excel-Blatts Kennzahlen; das Dashboard wählt sein Theme per ?firma=",
    )
    b.set_defaults(func=cmd_build)

    s = sub.add_parser("serve", help="Dashboard lokal anzeigen")
    s.add_argument("--port", type=int, default=DEFAULT_PORT)
    s.add_argument("--dir", type=Path, default=DEFAULT_OUT / "site")
    s.set_defaults(func=cmd_serve)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
