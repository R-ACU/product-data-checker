"""Accents per target company, light and dark mode, and WCAG contrast in every pairing.

The colours come from frontend/src/styles/tokens.css: one block per mode (surfaces,
text, status) and one block per company accent and mode. Contrast is computed from the
hex values (WCAG 2.x relative luminance), not estimated: text pairs need 4.5:1, chart
marks, focus rings and icons 3:1. The e2e suite repeats the text check on the pages.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from openpyxl import load_workbook

from product_data_checker import config
from product_data_checker.cli import main as cli_main
from product_data_checker.metrics import quality_metrics
from product_data_checker.report_excel import write_excel

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
STYLES = FRONTEND / "src" / "styles"
TOKENS = (STYLES / "tokens.css").read_text(encoding="utf-8")
INDEX_CSS = (STYLES / "index.css").read_text(encoding="utf-8")
ERROR_CSS = (FRONTEND / "public" / "error.css").read_text(encoding="utf-8")
BOOT_JS = (FRONTEND / "public" / "boot.js").read_text(encoding="utf-8")
THEME_TS = (FRONTEND / "src" / "lib" / "theme.ts").read_text(encoding="utf-8")
SLUGS = list(config.THEMES)
MODES = ("light", "dark")


def _blocks() -> dict[str, dict[str, str]]:
    css = re.sub(r"/\*.*?\*/", "", TOKENS, flags=re.DOTALL)
    out = {}
    for selector, body in re.findall(r"([^{}]+)\{([^}]*)\}", css):
        key = " ".join(selector.split())
        out[key] = dict(re.findall(r"(--[\w-]+):\s*([^;]+);", body))
    return out


BLOCKS = _blocks()
MODE_SELECTOR = {"light": ':root, [data-mode="light"]', "dark": '[data-mode="dark"]'}


def accent_selector(slug: str, mode: str) -> str:
    if mode == "light":
        return ':root, [data-theme="neutral"]' if slug == "neutral" else f'[data-theme="{slug}"]'
    if slug == "neutral":
        return '[data-mode="dark"], [data-mode="dark"][data-theme="neutral"]'
    return f'[data-mode="dark"][data-theme="{slug}"]'


def palette(slug: str, mode: str) -> dict[str, str]:
    return {**BLOCKS[MODE_SELECTOR[mode]], **BLOCKS[accent_selector(slug, mode)]}


def hex_color(value: str) -> tuple[float, float, float]:
    value = value.strip()
    assert re.fullmatch(r"#[0-9a-fA-F]{6}", value), f"not a solid hex colour: {value}"
    return tuple(int(value[i : i + 2], 16) / 255 for i in (1, 3, 5))


def luminance(rgb) -> float:
    def channel(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in rgb)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a: str, b: str) -> float:
    la, lb = sorted((luminance(hex_color(a)), luminance(hex_color(b))), reverse=True)
    return (la + 0.05) / (lb + 0.05)


SURFACES = ["--bg", "--card", "--card-2", "--muted"]
TEXT_PAIRS = (
    [(fg, bg) for fg in ("--text", "--text-2", "--text-3") for bg in SURFACES]
    + [("--accent-text", bg) for bg in ("--card", "--muted", "--accent-soft")]
    + [("--on-accent", "--accent"), ("--on-primary", "--primary")]
    # tabs and switches: text on the track and on the raised selection (--pill)
    + [(fg, bg) for fg in ("--text", "--text-2") for bg in ("--seg", "--pill")]
    + [("--tooltip-fg", "--tooltip-bg")]
    + [("--danger", "--card"), ("--danger", "--danger-soft")]
    + [("--good", "--card"), ("--good", "--good-soft")]
    + [("--text", "--mark-ok-bg"), ("--text-2", "--mark-ok-bg")]
    + [("--mark-bad-ink", "--mark-bad-bg"), ("--mark-claim-ink", "--mark-claim-bg")]
    + [
        (fg, "--code-bg")
        for fg in ("--code-text", "--code-kw", "--code-fn", "--code-str", "--code-nm", "--code-cm")
    ]
    + [(fg, bg) for fg in ("--hero-fg", "--hero-fg-2") for bg in ("--hero-bg", "--hero-inner")]
    + [("--text", "--tip-bg"), ("--text-2", "--tip-bg")]
)
# Chart marks, icons and focus rings: WCAG 1.4.11 asks for 3:1 against the neighbour.
# Not listed on purpose: --day-band, --rest, --track and the heatmap scale. They are
# backdrops or "everything else" parts whose numbers stand as text next to them
# (legend, tooltip, SQL table).
MARK_PAIRS = (
    [
        (m, "--card")
        for m in ("--accent", "--chart-1", "--chart-2", "--chart-3", "--review-1", "--review-2")
    ]
    + [("--accent", "--bg")]  # focus ring
    + [
        (m, bg)
        for m in ("--hero-accent", "--hero-accent-2")
        for bg in ("--hero-bg", "--hero-inner")
    ]
    + [("--mark-ok-line", "--mark-ok-bg")]
)


def test_firm_list_is_the_same_in_python_boot_js_theme_ts_and_css():
    boot = re.search(r"var FIRMS = \{([^}]*)\}", BOOT_JS)
    assert boot
    assert re.findall(r"(\w+): 1", boot.group(1)) == SLUGS
    ts = re.search(r"export const FIRMS[^=]*= \{(.*?)\n\};", THEME_TS, re.DOTALL)
    assert ts
    assert re.findall(r"^\s{2}(\w+): \{", ts.group(1), re.MULTILINE) == SLUGS
    light = re.findall(r'^\[data-theme="(\w+)"\] \{', TOKENS, re.MULTILINE)
    dark = re.findall(r'^\[data-mode="dark"\]\[data-theme="(\w+)"\] \{', TOKENS, re.MULTILINE)
    assert light == SLUGS
    assert dark == SLUGS
    assert config.DEFAULT_THEME == "neutral" and SLUGS[0] == "neutral"


def test_every_mode_and_accent_defines_every_variable():
    assert set(BLOCKS[MODE_SELECTOR["light"]]) == set(BLOCKS[MODE_SELECTOR["dark"]])
    reference = set(BLOCKS[accent_selector("neutral", "light")])
    for slug in SLUGS:
        for mode in MODES:
            assert set(BLOCKS[accent_selector(slug, mode)]) == reference, (slug, mode)


def test_colours_are_solid_hex_values():
    for selector, values in BLOCKS.items():
        for name, value in values.items():
            hex_color(value), (selector, name)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("slug", SLUGS)
def test_text_contrast_is_wcag_aa(slug, mode):
    v = palette(slug, mode)
    fails = [
        f"{fg} on {bg}: {contrast(v[fg], v[bg]):.2f}"
        for fg, bg in TEXT_PAIRS
        if contrast(v[fg], v[bg]) < 4.5
    ]
    assert fails == []


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("slug", SLUGS)
def test_chart_marks_and_focus_reach_3_to_1(slug, mode):
    v = palette(slug, mode)
    fails = [
        f"{a} on {b}: {contrast(v[a], v[b]):.2f}" for a, b in MARK_PAIRS if contrast(v[a], v[b]) < 3
    ]
    assert fails == []


def hue(value: str) -> float:
    r, g, b = hex_color(value)
    mx, mn = max(r, g, b), min(r, g, b)
    if mx == mn:
        return -1.0  # grey
    d = mx - mn
    if mx == r:
        h = ((g - b) / d) % 6
    elif mx == g:
        h = (b - r) / d + 2
    else:
        h = (r - g) / d + 4
    return h * 60


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("slug", SLUGS)
def test_accents_are_cool_never_yellow_gold_orange_or_brown(slug, mode):
    v = palette(slug, mode)
    for name in ("--accent", "--primary", "--chart-1", "--hero-accent"):
        h = hue(v[name])
        assert 150 <= h <= 275, f"{name} {v[name]} hue {h:.0f}"


def test_dark_mode_surfaces_are_neutral_black_not_blue():
    dark = BLOCKS[MODE_SELECTOR["dark"]]
    for name in ("--bg", "--card", "--muted"):
        r, g, b = hex_color(dark[name])
        assert max(r, g, b) - min(r, g, b) <= 0.03, f"{name} {dark[name]} is tinted"
        assert luminance((r, g, b)) < 0.03


def test_no_gradients_glow_or_noise():
    sources = [TOKENS, INDEX_CSS, ERROR_CSS]
    sources += [p.read_text(encoding="utf-8") for p in (FRONTEND / "src").rglob("*.tsx")]
    for text in sources:
        assert "gradient(" not in text
        assert "linearGradient" not in text and "radialGradient" not in text
        assert "text-shadow" not in text and "drop-shadow" not in text
        assert "feTurbulence" not in text and "noise" not in text.lower()


def test_boot_js_reads_the_parameter_against_the_fixed_list_only():
    # own-property lookup: "__proto__", "constructor" or "toString" are no firms
    assert "Object.prototype.hasOwnProperty.call(FIRMS" in BOOT_JS
    for sink in (
        "innerHTML",
        "outerHTML",
        "insertAdjacentHTML",
        "document.write",
        "eval(",
        "cssText",
    ):
        assert sink not in BOOT_JS, sink


def test_font_is_allo_self_hosted_with_its_license():
    faces = re.findall(r"url\(\"([^\"]+)\"\)", INDEX_CSS)
    assert faces and all(url.endswith("AlloVariableFriendly.woff2") for url in faces)
    assert (FRONTEND / "src" / "fonts" / "AlloVariableFriendly.woff2").exists()
    assert (
        "SIL OPEN FONT LICENSE"
        in (FRONTEND / "src" / "fonts" / "OFL.txt").read_text(encoding="utf-8").upper()
    )
    assert '--font-sans: "Allo"' in INDEX_CSS
    assert "tabular-nums" in INDEX_CSS and "font-optical-sizing: auto" in INDEX_CSS
    assert "@import url(" not in INDEX_CSS and "http" not in re.sub(
        r"/\*.*?\*/", "", INDEX_CSS, flags=re.DOTALL
    )


@pytest.mark.parametrize("bad", ["GEDORE", "acme", "__proto__", "<script>", ""])
def test_cli_refuses_unknown_firma(bad):
    with pytest.raises(SystemExit) as exc:
        cli_main(["build", "--firma", bad, "--out", "nicht-angelegt"])
    assert exc.value.code == 2  # argparse error, nothing was built


def test_excel_kpi_sheet_takes_the_theme_colour(tmp_path, demo_result):
    quality = quality_metrics(demo_result)
    for slug in ("neutral", "gedore", "amalock", "metergrid"):
        path = write_excel(demo_result, quality, tmp_path / f"{slug}.xlsx", firma=slug)
        ws = load_workbook(path)["Kennzahlen"]
        header = next(
            c for row in ws.iter_rows() for c in row if c.value == "Lieferant" and c.fill.fgColor
        )
        fill, ink = config.THEMES[slug]["excel"]
        assert header.fill.fgColor.rgb.endswith(fill)
        assert header.font.color.rgb.endswith(ink)
        assert contrast(f"#{fill}", f"#{ink}") >= 4.5
    with pytest.raises(KeyError):
        write_excel(demo_result, quality, tmp_path / "x.xlsx", firma="acme")
