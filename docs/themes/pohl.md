# Akzent `pohl` (POHL Handels GmbH)

Aufruf: `?firma=pohl`. Die Firma bestimmt nur die Akzentfarbe; Aufbau, Schrift (Allo),
Rundungen und alles andere bleiben gleich. Keine Logos, Bilder oder Texte der Firma, keine
Verbindung zu ihr.

| | Hell | Dunkel |
| :--- | :--- | :--- |
| Akzent (Cerulean-Blau) | `#1667b8` | `#3d93e0` |

Etwas heller und klarer als das neutrale Blau.

Alle Werte stehen in `frontend/src/styles/tokens.css`. `tests/test_themes.py` prüft den
Kontrast (WCAG AA) in Hell und Dunkel, `e2e/test_themes_e2e.py` jede Ansicht im Browser.
Der Excel-Kopf des Blatts Kennzahlen nimmt mit `pdc build --firma pohl` dieselbe Farbe.
