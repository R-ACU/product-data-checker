# Akzent `gedore` (GEDORE Gruppe)

Aufruf: `?firma=gedore`. Die Firma bestimmt nur die Akzentfarbe; Aufbau, Schrift (Allo),
Rundungen und alles andere bleiben gleich. Keine Logos, Bilder oder Texte der Firma, keine
Verbindung zu ihr.

| | Hell | Dunkel |
| :--- | :--- | :--- |
| Akzent (Tiefes Blau) | `#1e4fc0` | `#5479ea` |

Blau statt Navy-Kopf und Gelb-Marker der Webseite.

Alle Werte stehen in `frontend/src/styles/tokens.css`. `tests/test_themes.py` prüft den
Kontrast (WCAG AA) in Hell und Dunkel, `e2e/test_themes_e2e.py` jede Ansicht im Browser.
Der Excel-Kopf des Blatts Kennzahlen nimmt mit `pdc build --firma gedore` dieselbe Farbe.
