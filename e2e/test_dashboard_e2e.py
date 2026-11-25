"""Browser tests (headless Chromium). Run with: uv run pytest e2e

They build the dashboard into a temp folder, serve it on a free port and click through
it like a user: navigation, filters with the keyboard, the detail sheet, empty and
error states, light and dark mode, and an XSS attempt through supplier data. Every
page fails on a console error, which includes CSP violations.
"""

from __future__ import annotations

import sys
import threading
from pathlib import Path

import pytest

pytest.importorskip("playwright")
from playwright.sync_api import expect, sync_playwright  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser import launch  # noqa: E402

from product_data_checker.dashboard import build_payload, write_site  # noqa: E402
from product_data_checker.llm import MockProvider  # noqa: E402
from product_data_checker.metrics import quality_metrics, smard_metrics  # noqa: E402
from product_data_checker.pipeline import run  # noqa: E402
from product_data_checker.server import make_server  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "fixtures" / "llm"
SMARD = ROOT / "data" / "smard" / "smard_hourly.csv"
XSS_NAME = '<img src=x onerror="window.__pwned=1">Bohrer'
XSS_SUPPLIER = "<script>window.__pwned=1</script>"
HEADER = (
    "Artikelnummer;Lieferant;EAN;Bezeichnung;Marke;Kategorie;Ausführung;Nennmaß;Länge;"
    "Gewicht;Material;Teile;EK netto;Beschreibung Lieferant"
)
HEADINGS = {
    "uebersicht": "Übersicht",
    "pruefen": "Prüfliste",
    "freigegeben": "Freigegeben",
    "sql": "SQL-Kennzahlen",
    "strommarkt": "Strommarkt Deutschland 2025",
}


def build(tmp: Path, source: Path) -> Path:
    result = run(source, MockProvider(FIXTURES))
    payload = build_payload(
        result, quality_metrics(result), smard_metrics(SMARD) if SMARD.exists() else None
    )
    return write_site(payload, tmp / "site", [])


def serve(site: Path):
    srv = make_server(site, 0)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


@pytest.fixture(scope="module")
def browser():
    with sync_playwright() as p:
        b = launch(p)
        yield b
        b.close()


@pytest.fixture(scope="module")
def demo_url(tmp_path_factory):
    site = build(tmp_path_factory.mktemp("demo"), ROOT / "data" / "raw" / "lieferantenliste.xlsx")
    srv = serve(site)
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
    srv.server_close()


def watch(pg) -> list[str]:
    errors: list[str] = []
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("dialog", lambda d: (errors.append(f"dialog: {d.message}"), d.dismiss()))
    return errors


@pytest.fixture
def page(browser):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    errors = watch(pg)
    yield pg
    ctx.close()
    assert errors == []


def test_overview_and_navigation(page, demo_url):
    page.goto(demo_url)
    expect(page.locator("h1")).to_have_text("Übersicht")
    expect(page.locator(".hero")).to_contain_text("119")
    for route, heading in HEADINGS.items():
        page.click(f'.tab[data-route="{route}"]')
        expect(page.locator("h1")).to_have_text(heading)
        expect(page.locator(f'.tab[data-route="{route}"]')).to_have_attribute(
            "aria-current", "page"
        )


def test_supplier_column_filters_review_list(page, demo_url):
    page.goto(demo_url)
    bar = page.locator(".recharts-bar-rectangle").first
    bar.scroll_into_view_if_needed()
    page.wait_for_timeout(900)  # columns grown in
    bar.click()
    expect(page.locator("h1")).to_have_text("Prüfliste")
    expect(page.locator(".toolbar .select-button").first).to_contain_text("Brennwald")
    expect(page.locator(".count-line")).not_to_have_text("81 von 81 Artikeln")


def test_reason_row_filters_review_list(page, demo_url):
    page.goto(demo_url)
    page.get_by_role("button", name="Maß fehlt").click()
    expect(page.locator("h1")).to_have_text("Prüfliste")
    expect(page.locator(".toolbar .select-button").nth(1)).to_contain_text("Maß fehlt")
    expect(page.locator(".count-line")).to_have_text("34 von 81 Artikeln")


def test_dropdown_works_with_keyboard(page, demo_url):
    page.goto(f"{demo_url}/#/pruefen")
    count = page.locator(".count-line")
    expect(count).to_have_text("81 von 81 Artikeln")
    button = page.locator(".toolbar .select-button").nth(1)  # Grund
    button.focus()
    page.keyboard.press("ArrowDown")
    listbox = page.locator(".listbox")
    expect(listbox).to_be_visible()
    expect(page.get_by_role("menuitemradio").first).to_be_focused()
    page.wait_for_timeout(200)  # a person does not press twice within a frame
    page.keyboard.press("ArrowDown")
    expect(page.get_by_role("menuitemradio").nth(1)).to_be_focused()
    page.keyboard.press("Enter")
    expect(listbox).to_have_count(0)
    expect(count).not_to_have_text("81 von 81 Artikeln")
    # Escape closes without choosing
    page.locator(".toolbar .select-button").nth(0).click()
    expect(listbox).to_be_visible()
    page.keyboard.press("Escape")
    expect(listbox).to_have_count(0)


def test_detail_sheet_marks_the_wrong_number_and_returns_focus(page, demo_url):
    page.goto(f"{demo_url}/#/pruefen")
    page.fill("input[type=search]", "VH-10027")
    expect(page.locator(".count-line")).to_have_text("1 von 81 Artikeln")
    row = page.locator("tbody tr").first
    row.click()
    sheet = page.locator("#drawer")
    expect(sheet).to_be_visible()
    expect(sheet).to_contain_text("Zahl im Text weicht ab")
    expect(sheet.locator(".marked mark.bad")).to_have_text("89 mm")
    expect(sheet).to_contain_text("0.084 m")  # what the supplier sent ...
    expect(sheet).to_contain_text("84 mm")  # ... and the cleaned value
    page.keyboard.press("Escape")
    expect(sheet).to_be_hidden()
    expect(row).to_be_focused()


def test_released_cards_open_the_sheet(page, demo_url):
    page.goto(f"{demo_url}/#/freigegeben")
    expect(page.locator(".count-line")).to_have_text("119 von 119 Artikeln")
    expect(page.locator(".product-card")).to_have_count(24)
    page.get_by_role("button", name="Weitere 24 anzeigen").click()
    expect(page.locator(".product-card")).to_have_count(48)
    page.locator(".product-card").first.click()
    expect(page.locator("#drawer")).to_be_visible()
    expect(page.locator("#drawer")).to_contain_text("Freigegeben")
    expect(page.locator("#drawer .marked mark.bad")).to_have_count(0)
    page.get_by_role("button", name="Detail schließen").click()
    expect(page.locator("#drawer")).to_be_hidden()


def test_sql_view_shows_queries_and_results(page, demo_url):
    page.goto(f"{demo_url}/#/sql")
    expect(page.locator(".query-card")).to_have_count(5)
    first = page.locator(".query-card").first
    expect(first.locator("pre.sql")).to_contain_text("SELECT")
    expect(first.locator("table.result tbody tr").first).to_be_visible()
    page.get_by_role("radio", name="Strommarkt").click()
    expect(page.locator(".query-card").first).to_contain_text("Strommarkt 2025 im Überblick")


def test_empty_state_shows_one_reset_button(page, demo_url):
    page.goto(f"{demo_url}/#/pruefen")
    page.fill("input[type=search]", "gibt es nicht")
    expect(page.locator(".empty")).to_contain_text("Keine Artikel für diese Filter")
    expect(page.get_by_role("button", name="Filter zurücksetzen")).to_have_count(1)
    page.get_by_role("button", name="Filter zurücksetzen").click()
    expect(page.locator(".count-line")).to_have_text("81 von 81 Artikeln")


def test_error_state_when_data_is_missing(browser, tmp_path):
    site = build(tmp_path, ROOT / "data" / "raw" / "lieferantenliste.csv")
    (site / "data.json").unlink()
    srv = serve(site)
    pg = browser.new_page()  # own page: the 404 for data.json is the point of this test
    try:
        pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/")
        expect(pg.locator(".error-box")).to_contain_text("Daten konnten nicht geladen werden")
        expect(pg.locator(".error-box button")).to_have_text("Neu laden")
    finally:
        pg.close()
        srv.shutdown()
        srv.server_close()


def test_supplier_data_is_never_rendered_as_html(browser, tmp_path):
    csv_path = tmp_path / "xss.csv"
    csv_path.write_text(
        HEADER + "\n"
        f"X-1;{XSS_SUPPLIER};4006381333931;{XSS_NAME};M;Bohrer;Metall;;84 mm;14 g;HSS;;4,90;\n",
        encoding="utf-8",
    )
    site = build(tmp_path, csv_path)
    srv = serve(site)
    pg = browser.new_page()
    dialogs: list[str] = []
    pg.on("dialog", lambda d: (dialogs.append(d.message), d.dismiss()))
    try:
        pg.goto(f"http://127.0.0.1:{srv.server_address[1]}/#/pruefen")
        expect(pg.locator("tbody tr")).to_have_count(1)
        expect(pg.locator("tbody")).to_contain_text("<img src=x")
        pg.locator("tbody tr").click()
        expect(pg.locator("#drawer")).to_contain_text(XSS_SUPPLIER)
        assert pg.evaluate("window.__pwned") is None
        assert pg.locator("tbody img, #drawer img").count() == 0
        assert dialogs == []
    finally:
        pg.close()
        srv.shutdown()
        srv.server_close()


def test_steps_navigate_and_filter(page, demo_url):
    page.goto(demo_url)
    steps = page.locator(".step")
    expect(steps).to_have_count(5)
    # nothing is marked while the list is not filtered to a step (the tab says where you are)
    expect(page.locator(".step[aria-current]")).to_have_count(0)
    steps.nth(1).click()  # Datenprüfung
    expect(page.locator("h1")).to_have_text("Prüfliste")
    expect(page.locator(".count-line")).to_have_text("71 von 81 Artikeln")
    expect(steps.nth(1)).to_have_attribute("aria-current", "step")
    steps.nth(3).click()  # Textprüfung
    expect(page.locator(".count-line")).to_have_text("10 von 81 Artikeln")
    expect(steps.nth(3)).to_have_attribute("aria-current", "step")
    expect(page.locator(".step[aria-current]")).to_have_count(1)
    steps.nth(4).click()
    expect(page.locator("h1")).to_have_text("Freigegeben")
    expect(page.locator(".step[aria-current]")).to_have_count(0)


def test_keyboard_shortcuts_and_help(page, demo_url):
    page.goto(demo_url)
    expect(page.locator("h1")).to_have_text("Übersicht")
    page.keyboard.press("2")
    expect(page.locator("h1")).to_have_text("Prüfliste")
    page.keyboard.press("/")
    expect(page.locator("input[type=search]")).to_be_focused()
    page.locator("h1").click()
    page.keyboard.press("?")
    expect(page.locator("#help")).to_be_visible()
    expect(page.locator("#help")).to_contain_text("Tastaturkürzel")
    page.keyboard.press("Escape")
    expect(page.locator("#help")).to_be_hidden()
    page.keyboard.press("5")
    expect(page.locator("h1")).to_have_text("Strommarkt Deutschland 2025")


def test_light_dark_toggle_is_remembered(page, demo_url):
    page.goto(demo_url)
    html = page.locator("html")
    expect(html).to_have_attribute("data-mode", "light")  # light by default
    page.get_by_role("button", name="Zu dunklem Design wechseln").click()
    expect(html).to_have_attribute("data-mode", "dark")
    page.reload()
    expect(html).to_have_attribute("data-mode", "dark")
    bg = page.evaluate("getComputedStyle(document.documentElement).backgroundColor")
    assert bg == "rgb(11, 11, 12)"  # deep black, not blue
    page.keyboard.press("t")
    expect(html).to_have_attribute("data-mode", "light")


def test_unknown_view_shows_a_404_page(page, demo_url):
    page.goto(f"{demo_url}/#/gibt-es-nicht")
    expect(page.get_by_role("heading", name="Diese Ansicht gibt es nicht")).to_be_visible()
    expect(page).to_have_title("Nicht gefunden · Produktdaten-Prüfer")
    page.get_by_role("link", name="Zur Startansicht", exact=True).click()
    expect(page.locator("h1")).to_have_text("Übersicht")


def test_range_switch_recomputes_the_hero_exactly(page, demo_url):
    page.goto(f"{demo_url}/#/strommarkt")
    hero = page.locator(".hero")
    expect(hero).to_contain_text("89,32")  # the year, as smard_overview.sql returns it
    page.get_by_role("radio", name="Q2").click()
    expect(hero).to_contain_text("Q2 2025")
    expect(hero).not_to_contain_text("89,32")
    page.get_by_role("radio", name="Jahr").click()
    expect(hero).to_contain_text("89,32")


REVISIT_SCRIPT = """
([route, heading]) => new Promise((resolve) => {
  const started = performance.now();
  const frames = [];
  document.querySelector(`.tab[data-route="${route}"]`).click();
  const tick = () => {
    const view = document.querySelector("main > div");
    if (view && view.querySelector("h1")?.textContent === heading) {
      const moving = [...view.querySelectorAll("[style]")].filter(
        (el) => el !== view && /translateY\\((?!0px)|translate3d\\(0px, (?!0px)|scaleY\\(0/.test(el.style.transform),
      ).length;
      frames.push({ numbers: [...view.querySelectorAll(".num")].map((n) => n.textContent).join("|"), moving });
    }
    if (performance.now() - started > 1500) return resolve(frames);
    requestAnimationFrame(tick);
  };
  tick();
})
"""


def test_coming_back_to_a_view_shows_it_as_it_is(page, demo_url):
    """Numbers do not count up again, rows do not slide in again: on every tab switch that looked like loading."""
    page.goto(demo_url)
    expect(page.locator(".hero")).to_contain_text("119")
    page.wait_for_timeout(1200)  # the first entrance has run
    page.click('.tab[data-route="pruefen"]')
    expect(page.locator("h1")).to_have_text("Prüfliste")
    page.wait_for_timeout(1200)

    frames = page.evaluate(REVISIT_SCRIPT, ["uebersicht", "Übersicht"])
    assert frames, "the overview did not appear"
    # Every figure on the first frame is already its final value (charts may add theirs a frame later).
    first, last = frames[0]["numbers"].split("|"), frames[-1]["numbers"].split("|")
    assert "119" in first
    assert set(first) <= set(last)

    frames = page.evaluate(REVISIT_SCRIPT, ["pruefen", "Prüfliste"])
    assert frames, "the review list did not appear"
    assert max(f["moving"] for f in frames) == 0  # no row slides in again

    # Changes still animate and land exactly: the range switch on the energy view after coming back.
    page.click('.tab[data-route="strommarkt"]')
    page.click('.tab[data-route="sql"]')
    page.click('.tab[data-route="strommarkt"]')
    hero = page.locator(".hero")
    expect(hero).to_contain_text("89,32")
    page.get_by_role("radio", name="Q2").click()
    expect(hero).to_contain_text("Q2 2025")
    expect(hero).not_to_contain_text("89,32")


def test_page_titles_and_favicon(page, demo_url):
    page.goto(demo_url)
    expect(page).to_have_title("Übersicht · Produktdaten-Prüfer")
    page.click('.tab[data-route="sql"]')
    expect(page).to_have_title("SQL-Kennzahlen · Produktdaten-Prüfer")
    href = page.evaluate("document.querySelector('link[rel=icon]').getAttribute('href')")
    assert href == "./favicon.svg"


def test_reduced_motion_shows_final_numbers_at_once(browser, demo_url):
    ctx = browser.new_context(reduced_motion="reduce", viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    try:
        pg.goto(demo_url)
        pg.wait_for_selector(".hero")
        assert "119" in pg.locator(".hero").inner_text()  # no count-up from 0
    finally:
        ctx.close()


@pytest.fixture
def phone(browser):
    ctx = browser.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
    )
    pg = ctx.new_page()
    errors: list[str] = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    yield pg
    ctx.close()
    assert errors == []


def test_phone_tab_bar_reaches_every_view(phone, demo_url):
    phone.goto(demo_url)
    items = phone.locator(".tab")
    expect(items).to_have_count(5)
    for i in range(5):
        box = items.nth(i).bounding_box()
        assert box and box["x"] >= 0 and box["x"] + box["width"] <= 390
    assert phone.evaluate("document.documentElement.scrollWidth") <= 390
    # the tab row stays at the top while the page scrolls
    phone.evaluate("window.scrollTo(0, 1500)")
    phone.wait_for_timeout(300)
    assert phone.locator(".tabs").bounding_box()["y"] <= 16
    phone.locator('.tab[data-route="strommarkt"]').click()
    expect(phone.locator("h1")).to_have_text("Strommarkt Deutschland 2025")


def test_phone_dropdown_stays_inside_the_screen(phone, demo_url):
    phone.goto(f"{demo_url}/#/pruefen")
    phone.locator(".toolbar .select-button").nth(1).click()
    listbox = phone.locator(".listbox")
    expect(listbox).to_be_visible()
    box = listbox.bounding_box()
    assert box["x"] >= 0 and box["x"] + box["width"] <= 390
    assert phone.evaluate("window.scrollX") == 0
    assert phone.evaluate("document.documentElement.scrollWidth") <= 390


def test_phone_downloads_are_reachable(phone, demo_url):
    phone.goto(demo_url)
    expect(phone.locator('.appbar a[href="downloads/sauber.csv"]')).to_be_visible()
    expect(phone.locator('.appbar a[href="downloads/ergebnis.xlsx"]')).to_be_visible()


def test_phone_chart_labels_keep_their_size(phone, demo_url):
    phone.goto(f"{demo_url}/#/strommarkt")
    phone.wait_for_selector(".recharts-cartesian-axis-tick-value")
    size = phone.evaluate(
        "document.querySelector('.recharts-cartesian-axis-tick-value').getBoundingClientRect().height"
    )
    assert size >= 10
