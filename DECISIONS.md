# Decisions

Why the checker is built this way, what happens on errors, and what the model is not
allowed to do.

## What the model may do, and what it may not

| The model may | The model may not |
| :--- | :--- |
| Write a title and a short description from structured facts | See the supplier's free-text column (untrusted, may contain instructions) |
| Read brand, variant and material, capped at 60, 120 and 60 characters | Receive any of them if they look like an instruction or are too long: the article is blocked before any request |
| Pick a category from a fixed list, or answer "unklar" | Invent a category: the schema is an enum, and the parser refuses anything else |
| Report missing information in `fehlende_angaben` | Fill a gap by guessing; missing mandatory data blocks the article before the model is asked |
| | Calculate, convert or validate anything: units, EAN check digits, duplicates and KPIs are code |
| | Release an article: only the checks in code decide between "Sauber" and "Prüfen" |

## Why these checks

- **Every number is compared with the source.** The most damaging model error in
  product data is a plausible wrong number (89 mm instead of 84 mm). A regex extracts
  every number from the copy; numbers with a unit are converted to mm or g and must
  equal a source value (so 8,4 cm for 84 mm passes, 0,14 kg for 14 g does not), bare
  numbers must appear in the facts the model saw. Sizes inside the variant text
  ("Doppelmaul 12 x 13") count as mm by trade convention; fractions such as `1/2 Zoll`
  only count as the token `1/2`, so they cannot be borrowed as "1 mm" or "2 mm".
- **Risky claims need a source.** VDE, insulation, rustproof, hardened, test seals,
  warranty, standards, magnetic tip, "Profi", superlatives and "lifetime" are only
  allowed if the same word is in a controlled value: the category, a material in its
  canonical spelling, or a variant that reads like a spec ("VDE 1000 V", at most six
  words, no sentence punctuation). The variant never backs a promise (warranty,
  lifetime, superlative, "Profi") and backs VDE only with a voltage, because a short
  line without punctuation can still be an injected claim. The brand and free supplier
  prose never count as evidence. This is a fixed list, kept in `config.py`, so a reviewer can extend it
  without touching the logic. Every pattern has word boundaries; a regression
  catalogue of correct sentences ("besteht aus", "Bestellnummer") keeps it honest.
- **Text is normalised before it is checked.** Unicode NFKC, invisible format
  characters (zero-width space, soft hyphen, direction marks) and letters from other
  scripts (a Cyrillic "Е" in "VDЕ") are rule violations of their own, and the claim
  check runs on the cleaned text, so none of these tricks hide a claim.
- **Format rules in code, not just in the prompt.** Title max 80 characters,
  description 40 to 250, no links (any scheme, `www.`, or a bare domain such as
  `zangen.shop/x`), no `<` or `>` at all, no line breaks, no emojis, and no leading
  `= + - @` (a model bullet "- " would become a formula in Excel).
- **Structured output plus validation.** The real mode asks for JSON via
  `output_config.format` and still validates with Pydantic. Prose, a missing field or
  an extra field puts the article into review as "Kein Text erzeugt".

## What happens when something fails

| Situation | Result |
| :--- | :--- |
| File too big, too many rows, wrong type, macros, broken or hostile XML | The whole file is refused with a German message, nothing is written |
| Value unreadable (`ca. 12`, `auf Anfrage`) | Never guessed, article goes to review |
| Unit missing (`125`) | Read as mm and noted (not blocking): tool lists use mm by default |
| EAN check digit wrong | Review, with the expected digit in the detail |
| EAN in scientific notation | Review: the digits are lost and cannot be restored |
| Same EAN or article number twice | First occurrence stays, later ones go to review |
| Model refuses, hits `max_tokens`, rate limit, network or key error | That article goes to review with the reason; the run continues |
| Unexpected API response, a category that is not a string, a damaged cache file | Same: review with the reason, the run continues |
| Instruction or overlong text in name, brand, variant or material | Blocked before any model call, shown as "Anweisung in Datenfeld" or "Feld zu lang" |
| Model answer fails a check | Review with the exact number or word that failed, highlighted in the dashboard |

No article ever ends up in "Sauber" with an open blocking issue; a test asserts that
every released article is complete and within all limits.

## Why this stack

- **pandas for loading, plain Python for the rules.** Each rule is a small function
  with its own test; no hidden behaviour in a dataframe chain.
- **DuckDB for the KPIs.** The KPI definitions are SQL files you can read, copy into
  another tool (Metabase, a warehouse) and discuss in an interview. DuckDB runs them
  in-process, no server. Tests compare each SQL result with an independent pandas
  calculation.
- **openpyxl for Excel**, with `defusedxml` installed so hostile XML in an input
  workbook is refused.
- **A static dashboard instead of Streamlit** (the original plan said Streamlit). A
  generated `data.json` plus a prebuilt React app loads instantly, works offline, needs
  no Python process per user, and allows a strict Content-Security-Policy with no inline
  scripts or styles. React with Vite, shadcn/ui components on own design tokens (so it
  does not look like stock shadcn), Recharts for charts and motion for animation. The
  build is committed inside the Python package, so `pdc serve` runs without Node; CI
  rebuilds it and fails if the committed build is stale. Icons are `lucide-react`, the
  font is Allo (SIL OFL), self-hosted.
- **Models:** `claude-sonnet-5-5` for copy (quality matters, effort `low` because the
  task is short and constrained), `claude-haiku-5-5` for the category (a choice from
  six values). Sonnet requests use the server-side fallback (`fallbacks: "default"`), so
  a declined request is retried on a suitable model inside the same call.
- **Mock mode by default.** Fixed answers from `fixtures/llm/` make every run free and
  reproducible. The fixtures are template text, and ten of them contain planted
  defects to prove the checks; five more are correct variants that must pass (two in
  cm instead of mm, three phrased like real model copy with "besteht aus" and
  "Bestellnummer"). All are labelled as such in the file.

## Why SMARD for the second tab

metergrid works on local solar power; the interesting KPIs are price level,
renewable share and hours with negative prices. SMARD (Bundesnetzagentur) publishes
exactly that as open data under CC BY 4.0. It is fetched once by
`scripts/fetch_smard.py` and stored as a 700 KB CSV, so the tab and its tests run
offline. The renewable share is measured against load, as SMARD reports it. The
series "sonstige Konventionelle" ends in early 2024 on SMARD and is not used.

## Why the dashboard looks like this

- **An analysis app with the run as its spine.** The five steps of a run (read, data
  check, copy, copy check, released) are what a reviewer thinks in, so they sit under the
  header with their numbers and double as filters. The views are tabs in the header bar;
  content uses the full width instead of a side bar.
- **Readable in a second, quiet by default.** A first version marked the current step,
  the active tab and the hero card at once, with white blocks in dark mode, and stacked
  columns fell apart into separate dots. Now a step is only marked while the list is
  filtered to it, a selection is a raised surface on a grey track (never a black or white
  block), every area has at most one highlighted element, a stacked column is one pill
  with nested segments, and explanations moved from sentences under cards into icons,
  short labels, tooltips and the detail sheet.
- **Each chart has one job.** One equal pill per supplier answers "who sends the
  problems" at a glance; the ring shows the split of one whole; the gauge shows a single
  share against the state after the checks; reasons and fixes are short bars with an
  icon, sorted by count; the daily price line has a hover rule because single days
  matter. No dual axes, no rainbow ramps, sequential colours in one hue, diverging colours
  with a grey middle.
- **Quarters are exact.** The quarter switch does not average monthly averages: the
  monthly SQL returns sums (hours, price sum, MWh), so every quarter KPI is a real ratio of
  sums, and the year gives back exactly the value of `smard_overview.sql` (tested).
- **One accent per company, by link, not a copy of its website.** A first version took
  each company's site style (colours, type, corners); it looked like a theme kit and was
  dropped. Now `?firma=<slug>` only picks one calm, cool accent (blue, teal, green), in
  light and dark; everything else is the same product. Only a fixed list is accepted,
  logos and texts of the companies are never used, and every accent passes WCAG AA in both
  modes, checked from the tokens and on the rendered pages.
- **Colour has one meaning.** The accent is "released" and the main series; on the hero,
  "stopped at the data" is a lighter step of it and "stopped at the copy" is hatched, red
  is reserved for errors. A first draft used teal for
  "failed at the data", which read as good.
- **Calm price line.** Daily day-ahead prices jump a lot; the main line is the trailing
  7-day mean, the daily values stay behind it as a faint area and in the tooltip.
- **Light and dark.** Light by default, dark in neutral black (not blue-tinted), the
  choice is remembered. A small `boot.js` sets mode and accent before the first paint, so
  nothing flashes.
- **Everything that changes moves, briefly.** Pressed buttons sink, tab and step
  highlights glide, views cross fade, numbers count up and glide to new values when the
  quarter changes, bars grow. 150 to 300 ms with spring easing; `prefers-reduced-motion`
  turns it off. No gradients, no glow: areas are flat or faintly transparent, the hatching
  for "still to check" is a pattern.

## What I would do next

- Measure the real mode on the 200 demo rows: hit rate, tokens and cost per article,
  plus a hand-checked sample of 50 texts.
- Batches API for large lists (half price, asynchronous).
- Fuzzy duplicate detection on normalised names within a supplier.
- Per-supplier header mapping saved as a profile, because real suppliers rename
  columns.
