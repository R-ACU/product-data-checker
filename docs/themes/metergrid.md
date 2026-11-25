# Akzent `metergrid` (metergrid)

Aufruf: `?firma=metergrid`. Die Firma bestimmt nur die Akzentfarbe; Aufbau, Schrift (Allo),
Rundungen und alles andere bleiben gleich. Keine Logos, Bilder oder Texte der Firma, keine
Verbindung zu ihr.

| | Hell | Dunkel |
| :--- | :--- | :--- |
| Akzent (Blau mit Grün) | `#2350d8` | `#5b7ff4` |

Grün als zweite Diagrammfarbe; die App startet im Reiter Strommarkt.

Alle Werte stehen in `frontend/src/styles/tokens.css`. `tests/test_themes.py` prüft den
Kontrast (WCAG AA) in Hell und Dunkel, `e2e/test_themes_e2e.py` jede Ansicht im Browser.
Der Excel-Kopf des Blatts Kennzahlen nimmt mit `pdc build --firma metergrid` dieselbe Farbe.
