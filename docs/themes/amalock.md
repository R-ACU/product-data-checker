# Akzent `amalock` (AMALOCK)

Aufruf: `?firma=amalock`. Die Firma bestimmt nur die Akzentfarbe; Aufbau, Schrift (Allo),
Rundungen und alles andere bleiben gleich. Keine Logos, Bilder oder Texte der Firma, keine
Verbindung zu ihr.

| | Hell | Dunkel |
| :--- | :--- | :--- |
| Akzent (Teal) | `#0b7a6e` | `#23ab9b` |

Teal statt Dunkelbraun und Gold der Webseite: Gold, Gelb und Braun sind als Akzent ausgeschlossen.

Alle Werte stehen in `frontend/src/styles/tokens.css`. `tests/test_themes.py` prüft den
Kontrast (WCAG AA) in Hell und Dunkel, `e2e/test_themes_e2e.py` jede Ansicht im Browser.
Der Excel-Kopf des Blatts Kennzahlen nimmt mit `pdc build --firma amalock` dieselbe Farbe.
