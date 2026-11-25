# Security

The checker processes files from outside parties (suppliers) and text from a language
model. Both are treated as untrusted. This page lists the threats, the defences, the
tests that prove them and the known limits. Every statement here is covered by a test
named in the second table.

## Threats and defences

| Threat | Defence | Where |
| :--- | :--- | :--- |
| **Formula injection** (CSV/Excel injection): a cell like `=HYPERLINK(...)` or `+cmd\|' /C calc'!A0` runs when someone opens the output | Excel: every text cell is stored with type *string*, never *formula*, and formula-like text (`=`, `+`, `-`, `@`, tab, CR, LF or their full-width forms) gets the cell's `quotePrefix` flag, the same thing Excel sets for a typed apostrophe; the value stays readable as written. CSV has no cell types, so there the value gets a leading apostrophe (OWASP). Input formulas are reported as a note | `report_excel.set_cell`, `ingest.neutralize_formula` |
| **Macros**: a `.xlsm` or a renamed macro workbook | Only `.csv` and `.xlsx` are accepted; any archive containing `vbaProject.bin` is refused even if renamed. Output is written by openpyxl, which never writes a VBA project | `ingest._check_file`, `ingest._read_xlsx` |
| **Oversized input / zip bomb** | Max 5 MB file, 5,000 rows, 40 columns, 1,000 characters per cell; uncompressed xlsx content max 20 times the file limit | `config.py`, `ingest.py` |
| **Memory blow-up through a wide sheet**: openpyxl pads every row to the declared last column, so one cell in column XFD turned 5,000 rows into 80 million cells | The declared width (`<dimension>`) is checked before any row is read; rows are read with `max_col = 41` either way, because the dimension can be missing or wrong; a value past column 40 rejects the file. CSV rows are checked one by one | `ingest._read_xlsx`, `ingest._read_csv` |
| **Malformed CSV** (a field above Python's 131,072-character limit, broken quoting) | Becomes a German rejection ("Zelle zu lang oder CSV defekt"), never a traceback with internal paths | `ingest._read_csv` |
| **Hostile XML** in an xlsx (entity expansion, external entities) | `defusedxml` is a dependency, so openpyxl refuses DTDs and entities; the error becomes a clear rejection | `ingest._read_xlsx` |
| **Formula evaluation on read** | Workbooks are read with `data_only=False`: a formula arrives as its text and is never evaluated or trusted as a value | `ingest._read_xlsx` |
| **Prompt injection** through supplier data ("Ignoriere alle Regeln ...") | The free-text note never reaches the model. The fields that do (name to the classifier; brand, variant and material to the copy writer) are capped at 150, 60, 120 and 60 characters and scanned for instruction phrases; a hit or an overlong value blocks the article before any model call. Facts go inside `<produktdaten>` tags with the instruction that they are data. The classifier can only answer from an enum | `cleaning.normalize_rows`, `pipeline._classify_missing`, `prompts.py` |
| **Injected text used as its own evidence** ("VDE geprüft lebenslange Garantie" in the variant, then repeated by the model) | Claims are only accepted when a source value backs them: the category, a material in its canonical spelling, or a variant that reads like a spec (at most six words, no sentence punctuation). The variant never backs a promise (warranty, lifetime, superlative, "Profi"), and it backs VDE only together with a voltage ("VDE 1000 V"). Brand and supplier prose never count | `guard.claim_evidence`, `config.VARIANT_NEVER_EVIDENCE`, `config.VARIANT_EVIDENCE_REQUIRES` |
| **Model output that lies or breaks things** | JSON schema plus Pydantic validation, length limits, number check against the source, claim list, format rules; anything failing goes to review | `llm.parse_*`, `guard.py` |
| **Rule bypass in model output**: bare domains (`zangen.shop/x`), long HTML tags, zero-width spaces or soft hyphens inside a word (`V` + U+200B + `DE`), full-width letters, Cyrillic look-alikes | Text is NFKC-normalised and stripped of format characters before the claim and number checks; invisible characters and letters from other scripts are rule violations themselves. Links: any scheme, `www.`, `mailto:`/`javascript:`/`data:` and any `name.tld`. HTML: `<` and `>` are not allowed at all | `guard.normalize_text`, `guard.check_rules` |
| **Unexpected model or API responses** (a category that is a list or object, `APIResponseValidationError`, a damaged cache file) | Parsed defensively: the article goes to review with the reason and the run continues; a damaged cache entry is ignored and asked again | `llm.parse_category_answer`, `llm.ClaudeProvider._call` |
| **XSS in the dashboard** through supplier text | The React frontend never builds HTML from data: every value is rendered as text, there is no `dangerouslySetInnerHTML`, `innerHTML` or `eval` anywhere (a test scans the sources). Marks in the generated copy are split into text nodes, not markup. The built page has no inline script or style, and the server sends `Content-Security-Policy: default-src 'none'; script-src 'self'; style-src 'self'; ...`. Components that would inject a `<style>` tag (Radix modal scroll lock) are replaced by native `<dialog>` | `frontend/src/`, `server.py` |
| **Accent parameter** (`?firma=`) used to inject markup, CSS or prototype keys | `boot.js` accepts only an own property of a fixed object (`neutral`, `gedore`, `pohl`, `amalock`, `metergrid`); anything else, including `__proto__`, `constructor`, other casing and markup, becomes `neutral`. The URL value is never written into the page: only the slug from the list goes into `data-theme`, and the company label comes from the same list in `theme.ts`, rendered as text. Review filters from the link (`?lieferant=`, `?grund=`) are only applied when they match a supplier or reason in the data | `frontend/public/boot.js`, `frontend/src/lib/theme.ts`, `views/Review.tsx` |
| **Error pages that echo the request** | The server's own error pages are fixed German texts per status code, link only the local stylesheets and never contain the requested path | `server.ERROR_TEXTS`, `DashboardHandler.send_error` |
| **Local server exposure** | Binds to 127.0.0.1 only, GET/HEAD only, no directory listing, dot segments, backslashes and NUL refused, no version in the `Server` header, `nosniff`, `X-Frame-Options: DENY`, `no-referrer`, `no-store` | `server.py` |
| **DNS rebinding**: a foreign web page points its own domain at 127.0.0.1 and reads `data.json` as same-origin | Only `Host: 127.0.0.1:<port>` and `localhost:<port>` are served; any other or missing Host header gets `421 Misdirected Request` | `server.DashboardHandler._foreign_host` |
| **API key leakage** | The key is read only from the local `.env` (never from the process environment, never global), `.env*` is git-ignored except `.env.example`. It is handed to the SDK client and not stored on the provider object, so it never appears in a `repr`, a log line or a traceback with local variables | `llm.load_api_key`, `llm.ClaudeProvider`, `.gitignore` |
| **Cost runaway in real mode** | Text is only requested for articles that passed the data checks; answers are cached by input hash; `max_tokens` is capped per request; effort is `low` | `pipeline.run`, `llm.ClaudeProvider` |
| **Supply chain** | Dependencies locked in `uv.lock`; CI installs with `--locked`, runs `pip-audit` on the exported lock, and pins GitHub Actions to commit SHAs; Dependabot watches uv and Actions | `.github/` |
| **Scraping third-party shops** | Not done. Product data is invented; the only network access is the one-off SMARD download from the official open-data endpoint, restricted to that host | `scripts/fetch_smard.py` |
| **Real data in a public repo** | Only invented data. EANs use GS1 prefixes 20 to 29 (restricted circulation), never assigned to real products | `scripts/generate_supplier_data.py` |

## Tests

Run `uv run pytest` and `uv run pytest e2e`.

| File | What it proves |
| :--- | :--- |
| `tests/test_ingest.py` | Formula prefixes, wrong suffix, renamed macro workbook, non-zip xlsx, size, row and column limits, a cell in XFD refused in under 2 s, a wide sheet without `<dimension>`, trailing empty columns, cell cap, oversized CSV field, entity-expansion XML in workbook and sheet, formulas read as text |
| `tests/test_reports.py` | No cell of type formula, no `<f>` element in any sheet XML, no VBA part, formula text stored as string with `quotePrefix` and without a visible apostrophe, CSV cells never start with a formula character |
| `tests/test_guard.py` | A regression catalogue of correct sentences ("besteht aus", "bestehend aus", "Bestellnummer", "Magnethalter" with a magnetic source) passes; real superlatives are still caught; supplier prose, a non-canonical material and the brand are not evidence; a spec-like variant ("VDE geprüft lebenslange Garantie") backs no promise and no VDE without a voltage, "VDE 1000 V" still does; eleven bypass variants (bare domains, long tag, `javascript:`, zero-width space, soft hyphen, Cyrillic, full-width, bidi marks) are blocked |
| `tests/test_pipeline.py` | Every planted model defect is blocked, all five correct variants are released, the supplier note never appears in the model input, an instruction in the variant or name never reaches either model, a claim hidden in a spec-like variant and repeated by the model is blocked, overlong brand, variant or material are blocked |
| `tests/test_llm.py` | Refusal, `max_tokens`, rate limit, auth, server, connection and response-validation errors end in review; list, object, number and null as category end in "unklar"; damaged cache entries are ignored; the key is not in `repr(provider)`; the key is ignored when it only exists in the process environment |
| `tests/test_server_and_site.py` | CSP and security headers, German error pages that never echo the request, path traversal variants, no listing, write methods refused, localhost binding, foreign and missing `Host` headers refused, no inline script or style, no HTML sinks (`innerHTML`, `eval`, ...) in the frontend code |
| `tests/test_themes.py` | Accent list identical in Python, `boot.js`, `theme.ts` and the tokens; every mode and accent defines every token; WCAG AA for every text pair and 3:1 for chart marks and focus, per accent in light and dark, computed from the tokens; accents only cool hues; dark mode neutral; no gradients, glow, noise or external font URLs; the CLI refuses an unknown `--firma` |
| `e2e/test_themes_e2e.py` | Every accent in every view in light and dark, detail sheet, dropdown, empty and error state and on a phone, with a contrast audit of the rendered text; 13 unknown or hostile `?firma=` values end in `neutral` with nothing injected |
| `e2e/test_dashboard_e2e.py` | Supplier name `<img src=x onerror=...>` and supplier `<script>...</script>` are shown as text, no script runs, no dialog opens |

## Known limits

- The claim list is fixed. A new kind of invented property without a number passes
  unless it is added to `config.UNSUPPORTED_CLAIMS`.
- The instruction scan is a word list. Brand, variant and material are supplier text
  and reach the model; an injection that avoids every trigger word is still sent,
  capped to 60, 120 and 60 characters. The output still has to pass every check.
- The variant is supplier text and still counts as evidence for technical marks
  (insulated, rustproof, hardened, magnetic, standards, test seals, ergonomic, VDE with
  a voltage) as long as it reads like a spec. A supplier who writes "isoliert" into a
  short variant gets "isoliert" into the copy; the checker trusts the supplier for
  technical facts and only refuses promises. Whether the fact is true is not checked.
- Number words ("zwei Bits") are not checked.
- Letters from non-Latin scripts are rejected in generated copy. That is right for a
  German shop, but a product name with a Greek "µ" would need an allow-list.
- In a sheet without a correct `<dimension>` element, the reader stops at column 41:
  a value in column 41 refuses the file, values further right are ignored.
- The dashboard has no login. It is meant for `127.0.0.1`; putting it on a network
  would need authentication in front of it.
- Supplier text inside the Excel output is neutralised but otherwise unchanged; a
  reviewer still has to read it with care. A CSV export of the Excel file by hand
  would lose the `quotePrefix` flag; use the supplied `sauber.csv` instead.
- `pip-audit` and Dependabot are configured but have not run yet, because the repo
  has no remote. The same audit run locally over the 37 exported packages (all groups)
  found no known vulnerabilities. The pinned Action SHAs were checked against their
  tags (`checkout` v4.4.0, `setup-uv` v6.8.0) with `git ls-remote`; whether the first CI
  run is green is only known after the first push.
