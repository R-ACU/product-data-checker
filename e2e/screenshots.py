"""Capture the README screenshots headless. Needs a running dashboard (pdc serve).

uv run python e2e/screenshots.py --url http://127.0.0.1:3230
uv run python e2e/screenshots.py --review          # every view and state, into docs/review/

Curated shots go to docs/screenshots/<accent>-<mode>-<view>.png. With --review every
view, the detail sheet, dropdown, hover, help, empty state and 404 of every accent in
light and dark go to docs/review/ui/ (git-ignored) for a look by eye.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from playwright.sync_api import Browser, Page, sync_playwright

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser import launch  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
REVIEW = ROOT / "docs" / "review" / "ui"
THEMES = ["neutral", "gedore", "pohl", "amalock", "metergrid"]
ROUTES = ["uebersicht", "pruefen", "freigegeben", "sql", "strommarkt"]


def url_for(base: str, theme: str, route: str = "") -> str:
    query = "" if theme == "neutral" else f"?firma={theme}"
    return f"{base}/{query}#/{route}" if route else f"{base}/{query}"


def new_page(browser: Browser, mode: str, errors: list[str], phone: bool = False) -> Page:
    if phone:
        ctx = browser.new_context(
            viewport={"width": 390, "height": 844},
            device_scale_factor=2,
            is_mobile=True,
            has_touch=True,
        )
    else:
        ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    ctx.add_init_script(f"try {{ localStorage.setItem('pdc-mode', '{mode}') }} catch (e) {{}}")
    page = ctx.new_page()
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    return page


def open_view(page: Page, base: str, theme: str, route: str) -> None:
    page.goto(url_for(base, theme, route))
    page.wait_for_selector(".page-head")
    page.evaluate("document.fonts.ready")
    page.wait_for_timeout(1800)  # entrance animations and count-ups finished


def full_shot(page: Page, path: Path) -> None:
    """Full-page shot without a resize mid-capture: charts redraw (and animate again)
    when their container changes size, so the viewport grows first and the charts settle."""
    size = page.viewport_size or {"width": 1440, "height": 900}
    height = page.evaluate("document.documentElement.scrollHeight")
    page.set_viewport_size({"width": size["width"], "height": height})
    page.wait_for_timeout(1800)
    page.screenshot(path=path, full_page=True)
    page.set_viewport_size(size)
    page.wait_for_timeout(300)


def open_detail(page: Page, base: str, theme: str, sku: str = "VH-10027") -> None:
    open_view(page, base, theme, "pruefen")
    page.fill("input[type=search]", sku)
    page.wait_for_timeout(300)
    page.click("tbody tr >> nth=0")
    page.wait_for_selector("#drawer[open]")
    page.wait_for_timeout(450)


def hover_supplier_chart(page: Page) -> None:
    bar = page.locator(".recharts-bar-rectangle").nth(1)
    bar.scroll_into_view_if_needed()
    page.wait_for_timeout(300)
    bar.hover()
    page.wait_for_timeout(450)


def curated(browser: Browser, base: str, theme: str, errors: list[str]) -> None:
    first = "strommarkt" if theme == "metergrid" else "uebersicht"
    for mode in ("light", "dark"):
        desk = new_page(browser, mode, errors)
        open_view(desk, base, theme, first)
        desk.screenshot(path=OUT / f"{theme}-{mode}-{first}.png")
        if theme == "neutral":
            full_shot(desk, OUT / f"{theme}-{mode}-{first}-full.png")
            open_view(desk, base, theme, "strommarkt")
            full_shot(desk, OUT / f"{theme}-{mode}-strommarkt.png")
            for route in ("pruefen", "freigegeben", "sql"):
                open_view(desk, base, theme, route)
                desk.screenshot(path=OUT / f"{theme}-{mode}-{route}.png")
            open_detail(desk, base, theme)
            desk.screenshot(path=OUT / f"{theme}-{mode}-detail.png")
            desk.keyboard.press("Escape")
            if mode == "light":
                open_view(desk, base, theme, "uebersicht")
                hover_supplier_chart(desk)
                desk.screenshot(path=OUT / f"{theme}-{mode}-tooltip.png")
        desk.context.close()

    if theme in ("neutral", "metergrid"):
        phone = new_page(browser, "light", errors, phone=True)
        routes = ("uebersicht", "pruefen", "strommarkt") if theme == "neutral" else ("strommarkt",)
        for route in routes:
            open_view(phone, base, theme, route)
            phone.screenshot(path=OUT / f"{theme}-mobile-{route}.png")
        phone.context.close()


def review(browser: Browser, base: str, theme: str, errors: list[str]) -> None:
    out = REVIEW / theme
    out.mkdir(parents=True, exist_ok=True)
    for mode in ("light", "dark"):
        m = mode[0]
        desk = new_page(browser, mode, errors)
        for route in ROUTES:
            open_view(desk, base, theme, route)
            full_shot(desk, out / f"{m}-{route}.png")
        open_detail(desk, base, theme)
        desk.screenshot(path=out / f"{m}-detail.png")
        desk.keyboard.press("Escape")
        open_view(desk, base, theme, "pruefen")
        desk.click(".toolbar .select-button >> nth=1")
        desk.wait_for_timeout(300)
        desk.screenshot(path=out / f"{m}-dropdown.png")
        desk.keyboard.press("Escape")
        desk.fill("input[type=search]", "gibt es nicht")
        desk.wait_for_timeout(300)
        desk.screenshot(path=out / f"{m}-empty.png")
        desk.locator("h1").click()
        desk.keyboard.press("?")
        desk.wait_for_timeout(300)
        desk.screenshot(path=out / f"{m}-help.png")
        desk.keyboard.press("Escape")
        desk.goto(url_for(base, theme, "gibt-es-nicht"))
        desk.wait_for_timeout(600)
        desk.screenshot(path=out / f"{m}-404.png")
        open_view(desk, base, theme, "uebersicht")
        hover_supplier_chart(desk)
        desk.screenshot(path=out / f"{m}-tooltip.png")
        desk.context.close()

    phone = new_page(browser, "light", errors, phone=True)
    for route in ROUTES:
        open_view(phone, base, theme, route)
        phone.screenshot(path=out / f"m-{route}.png")
    open_detail(phone, base, theme)
    phone.screenshot(path=out / "m-detail.png")
    phone.context.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:3230")
    parser.add_argument("--theme", default="", help="only this accent")
    parser.add_argument("--review", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    errors: list[str] = []
    themes = [args.theme] if args.theme else THEMES
    with sync_playwright() as p:
        browser = launch(p)
        for theme in themes:
            (review if args.review else curated)(browser, args.url, theme, errors)
        browser.close()
    if errors:
        print("Browser errors:", *errors, sep="\n  ")
        raise SystemExit(1)
    print(f"screenshots written to {REVIEW if args.review else OUT}")


if __name__ == "__main__":
    main()
