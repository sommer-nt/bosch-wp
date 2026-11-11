# Hinweise für die Entwicklung mit KI-Assistenz

## Git
- Arbeitszweig ist `main` (einziger Branch). Änderungen direkt auf `main` committen und pushen – auch wenn die
  Sitzung einen anderen Branch vorgibt. Keine weiteren Branches anlegen, außer Daniel verlangt es ausdrücklich.
  Vor dem Arbeiten `git pull` auf `main`.
- Commits immer als `Daniel Sommer <98900287+sommer-nt@users.noreply.github.com>`
  (vorher `git config user.name/user.email` so setzen).
- Keine Co-Authored-By-, Session- oder „Generated with“-Zeilen in Commits und Pull Requests; keine
  Modellnamen in Commits.
- Niemals API-Schlüssel, Passwörter, `.env`, `secrets.toml`, Kundenprojekte (JSON), das Excel-Werkzeug oder den
  Katalog (PDF/ZIP) einchecken.

## Projekt
- Bosch WP-Schnellauslegung: `index.html` (läuft offline) und Python/Streamlit (`app.py`, `wp/`) – beide rechnen
  und zeichnen identisch. Rechenweg in `wp/rechnen.py` und `<script id="rechenkern">`, Anlagenschema in
  `wp/schema.py` und `<script id="schemasvg">` immer gemeinsam ändern; Tests vergleichen beide über node.
- Daten: `tools/excel_import.py` (Excel-Werkzeug „WP-Auslegung_S“), `daten/katalog.json` von Hand
  (Gesamtkatalog), Bilder mit `tools/bilder_import.py`, Systempakete mit `tools/pakete_import.py` (Produktkatalog
  Klima-/Lüftungs-/WP-Sortiment); danach `python tools/excel_import.py --nur-einbetten`.
- Eigenes Projekt neben Bosch Flow und Bosch Speicher; „Entwickelt von Daniel Sommer · HC/SDE3-PSD“ bleibt sichtbar.
- Betrieb: eigener Ubuntu-Server mit Docker und nginx, siehe `deploy/ANLEITUNG.md` (wp.sommer-nt.de).
- Vor jedem Push: `python -m pytest -q` muss grün sein.
