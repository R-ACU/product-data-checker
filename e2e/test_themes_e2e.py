"""Company accents in the browser: every view in light and dark mode per accent, the
phone and error states, and the fallback for unknown or hostile ?firma= values.

The contrast audit runs on the rendered page: for every visible text it takes the
computed colour and composites the backgrounds of its ancestors, then checks WCAG AA
(4.5:1, large text 3:1). SVG chart labels are checked with their fill.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import expect  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_dashboard_e2e import HEADINGS, ROOT, browser, build, demo_url, serve  # noqa: E402, F401

from product_data_checker import config  # noqa: E402

THEMES = list(config.THEMES)

AUDIT = r"""
(scope) => {
  const parse = (c) => { const m = c.match(/rgba?\(([^)]+)\)/); if (!m) return [0, 0, 0, 0];
    const p = m[1].split(/[ ,/]+/).filter(Boolean).map(Number); return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1]; };
  const over = (top, bottom) => { const a = top[3]; return [0, 1, 2].map((i) => top[i] * a + bottom[i] * (1 - a)).concat(1); };
  const lum = (c) => { const f = (v) => { v /= 255; return v <= 0.04045 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]); };
  const ratio = (a, b) => { const x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); };
  const page = parse(getComputedStyle(document.documentElement).backgroundColor);
  const background = (el) => {
    const layers = [];
    for (let n = el; n; n = n.parentElement) {
      // the sliding highlight of tabs, steps and switches is a sibling layer (.pill-bg)
      const pill = n.querySelector(":scope > .pill-bg");
      if (pill) { const p = parse(getComputedStyle(pill).backgroundColor); if (p[3] > 0) { layers.push(p); if (p[3] >= 1) break; } }
      const c = parse(getComputedStyle(n).backgroundColor);
      if (c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
    }
    let bg = page[3] ? page : [255, 255, 255, 1];
    for (const layer of layers.reverse()) bg = over(layer, bg);
    return bg;
  };
  const root = document.querySelector(scope) || document.body;
  const fails = [];
  let checked = 0;
  for (const el of root.querySelectorAll("*")) {
    const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    if (!own) continue;
    const s = getComputedStyle(el);
    const r = el.getBoundingClientRect();
    if (!r.width || !r.height || s.visibility === "hidden" || el.closest("[hidden]") || el.closest(".sr-only")) continue;
    if (el.closest("[aria-hidden=true]")) continue;
    const isSvg = el instanceof SVGElement;
    let fg = parse(isSvg ? s.fill : s.color);
    if (fg[3] === 0) continue;
    const bg = background(isSvg ? el.closest("div, section, article") : el);
    if (fg[3] < 1) fg = over(fg, bg);
    const size = parseFloat(s.fontSize), weight = Number(s.fontWeight) || 400;
    const need = size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
    const got = ratio(fg, bg);
    checked++;
    if (got < need) fails.push(`${el.tagName} "${el.textContent.trim().slice(0, 30)}" ${got.toFixed(2)} < ${need}`);
  }
  return { checked, fails };
}
"""


def audit(page, scope: str = "body") -> int:
    page.wait_for_timeout(1300)  # entrance animations and count-ups done
    result = page.evaluate(AUDIT, scope)
    assert result["fails"] == [], result["fails"]
    return result["checked"]


def theme_url(base: str, theme: str, route: str = "") -> str:
    query = "" if theme == "neutral" else f"?firma={theme}"
    return f"{base}/{query}" + (f"#/{route}" if route else "")


@pytest.mark.parametrize("mode", ["light", "dark"])
@pytest.mark.parametrize("theme", THEMES)
def test_accent_carries_every_view(browser, demo_url, theme, mode):  # noqa: F811
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('pdc-mode', '{mode}') }} catch (e) {{}}")
    page = ctx.new_page()
    errors: list[str] = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    try:
        page.goto(theme_url(demo_url, theme))
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        expect(page.locator("html")).to_have_attribute("data-mode", mode)
        label = config.THEMES[theme]["label"]
        expect(page.locator("#brand-sub")).to_have_text(
            f"Demo für {label}" if label else "Lieferantenlisten prüfen"
        )
        first = "strommarkt" if theme == "metergrid" else "uebersicht"
        expect(page.locator("h1")).to_have_text(HEADINGS[first])
        expect(page.locator(".tab").first).to_have_attribute("data-route", first)

        checked = 0
        for route, heading in HEADINGS.items():
            page.click(f'.tab[data-route="{route}"]')
            expect(page.locator("h1")).to_have_text(heading)
            assert page.evaluate("location.search") == (
                "" if theme == "neutral" else f"?firma={theme}"
            )
            checked += audit(page)

        page.evaluate("document.fonts.ready")
        loaded = page.evaluate(
            "[...document.fonts].filter((f) => f.status === 'loaded').map((f) => f.family.replace(/\"/g, ''))"
        )
        assert "Allo" in loaded, loaded
        assert (
            page.evaluate("getComputedStyle(document.querySelector('h1')).fontFamily")
            .strip('"')
            .startswith("Allo")
        )

        # detail sheet, dropdown, empty state
        page.click('.tab[data-route="pruefen"]')
        page.fill("input[type=search]", "VH-10027")
        expect(page.locator(".count-line")).to_have_text("1 von 81 Artikeln")
        page.locator("tbody tr").first.click()
        expect(page.locator("#drawer")).to_be_visible()
        expect(page.locator("#drawer .marked mark.bad")).to_have_text("89 mm")
        checked += audit(page, "#drawer")
        page.keyboard.press("Escape")
        expect(page.locator("#drawer")).to_be_hidden()
        page.fill("input[type=search]", "")
        page.locator(".toolbar .select-button").nth(1).click()
        expect(page.locator(".listbox")).to_be_visible()
        checked += audit(page, ".listbox")
        page.keyboard.press("Escape")
        page.fill("input[type=search]", "gibt es nicht")
        expect(page.locator(".empty")).to_contain_text("Keine Artikel für diese Filter")
        checked += audit(page)
        assert checked > 400
    finally:
        ctx.close()
    assert errors == []


@pytest.mark.parametrize("theme", THEMES)
def test_accent_on_a_phone_and_in_the_error_state(browser, demo_url, tmp_path, theme):  # noqa: F811
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
    )
    phone = ctx.new_page()
    try:
        for route in ("uebersicht", "pruefen", "strommarkt"):
            phone.goto(theme_url(demo_url, theme, route))
            expect(phone.locator("h1")).to_have_text(HEADINGS[route])
            audit(phone)
            assert phone.evaluate("document.documentElement.scrollWidth") <= 390
        expect(phone.locator(".tab")).to_have_count(5)
    finally:
        ctx.close()

    site = build(tmp_path, ROOT / "data" / "raw" / "lieferantenliste.csv")
    (site / "data.json").unlink()
    srv = serve(site)
    page = browser.new_page()
    try:
        page.goto(theme_url(f"http://127.0.0.1:{srv.server_address[1]}", theme))
        expect(page.locator(".error-box")).to_contain_text("Daten konnten nicht geladen werden")
        expect(page.locator("html")).to_have_attribute("data-theme", theme)
        audit(page, ".error-box")
    finally:
        page.close()
        srv.shutdown()
        srv.server_close()


HOSTILE = [
    "acme",
    "GEDORE",
    " gedore",
    "gedore%00",
    "__proto__",
    "constructor",
    "toString",
    "hasOwnProperty",
    "%3Cimg%20src%3Dx%20onerror%3D%22window.__pwned%3D1%22%3E",
    "gedore%22%3E%3Cscript%3Ewindow.__pwned%3D1%3C%2Fscript%3E",
    "neutral%22%20data-x%3D%22",
    "metergrid%5D%2C%5Bdata-theme",
    "",
]


@pytest.mark.parametrize("value", HOSTILE)
def test_unknown_or_hostile_firma_falls_back_to_neutral(browser, demo_url, value):  # noqa: F811
    page = browser.new_page()
    dialogs: list[str] = []
    page.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    try:
        page.goto(f"{demo_url}/?firma={value}#/uebersicht")
        expect(page.locator("h1")).to_have_text(HEADINGS["uebersicht"])
        expect(page.locator("html")).to_have_attribute("data-theme", "neutral")
        expect(page.locator("#brand-sub")).to_have_text("Lieferantenlisten prüfen")
        assert page.evaluate("window.__pwned") is None
        assert page.locator("img, script:not([src])").count() == 0
        attrs = page.evaluate("[...document.documentElement.attributes].map((a) => a.name)")
        assert sorted(attrs) == ["data-mode", "data-theme", "lang", "style"]
        assert page.evaluate("document.documentElement.getAttribute('style')") == (
            "color-scheme: light;"
        )
        assert dialogs == []
    finally:
        page.close()


def test_first_value_of_a_repeated_parameter_wins(browser, demo_url):  # noqa: F811
    page = browser.new_page()
    try:
        page.goto(f"{demo_url}/?firma=pohl&firma=%3Cx%3E")
        expect(page.locator("html")).to_have_attribute("data-theme", "pohl")
    finally:
        page.close()
