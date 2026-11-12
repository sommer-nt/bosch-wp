# Bosch WP-Schnellauslegung

Entwickelt von Daniel Sommer · HC/SDE3-PSD

Schnellauslegung von Luft/Wasser-Wärmepumpen für den Außendienst – auch für Großanlagen (Compress 5000 AW / CS5001AW
als Kaskade), die der Heat Pump Advisor nicht abdeckt. Ersetzt das interne Excel-Werkzeug „WP-Auslegung_S“ für die
Weitergabe.

Eigenes Projekt neben Bosch Flow (Netzrechner) und Bosch Speicher. Zwei Versionen mit **identischem Rechenweg**
(Test vergleicht beide):

| | `index.html` | Python / Streamlit (`app.py`, `wp/`) |
|---|---|---|
| Start | Datei im Browser öffnen, läuft offline | `pip install -r requirements.txt` und `streamlit run app.py` |
| Ausdruck | „Drucken / PDF“ (A4, 3 Seiten) | „Auslegung als PDF“ (fpdf2, gleicher Aufbau) |
| Projektdatei | `.json` | dasselbe `.json`, in beide Richtungen austauschbar |

## Bedienung (Reihenfolge der Schnellauslegung)

1. Neubau oder Sanierung, **Ein-/Zweifamilienhaus oder Mehrfamilienhaus** (MFH: Wohneinheiten und gleich zu Beginn die
   Warmwasserbereitung – zentral FriWa, dezentral HIU, ohne/DLE oder Speicher bis 4 WE / NL 4), Gebäudeart, Raumtemperatur,
   PLZ → Norm-Außentemperatur, Heizgrenze (Neubau 12 °C, Bestand 15 °C)
2. Wärmebedarf: Heizlast in kW, W/m² (Gebäudestandard je Neubau/Bestand) oder Jahresverbrauch
3. Heizkreise (bis 4): Heizkörper (55 °C), FBH (35 °C), Konvektoren (45 °C) → max. Vorlauf aus dem höchsten Kreis,
   Kreise mit niedrigerem Vorlauf gemischt (z. B. Sanierung: Heizkörperkreis + FBH-Kreis); im Schema mit Pumpe/Mischer
4. Warmwasser: Personen, Speichersystem oder Frischwasserstation, Zapftemperatur, Liter je Person bei 45 °C
5. Wärmequelle Luft/Wasser (Außenaufstellung, Entfernung zum Gebäude) oder Sole/Wasser (Innenaufstellung)
6. Beste Lösung oder Produkt wählen (Kaskade nur, wo die Baureihe es erlaubt)

**Start, Zurücksetzen, Export:** Das Tool startet leer (keine vorbelegte Wärmepumpe); „Letztes Projekt“ holt die
zuletzt im Browser bearbeitete Auslegung zurück, „Zurücksetzen“ leert alle Eingaben. Menü „Export“: Projektdatei
(.json, auch in Streamlit zu öffnen), PDF (Drucken) und die **Projektmappe (.zip)** mit Projektdatei, Kurzbericht und
Bild der gewählten Hydraulik – in Streamlit zusätzlich mit dem PDF (`wp/export.py`).

**Ergebnis in Reitern:** Überblick (Klartext „Auf einen Blick“, Kennzahlen, gewählte Wärmepumpe, Leistungsdiagramm) ·
Leistung & Heizkurve · Geräteauswahl · Hydraulik & Warmwasser · Bestellvorschlag (MFH) bzw. Systempakete · Rechenweg
(Schritte, Herleitung, Begriffe). Fachbegriffe sind über „?“ erklärt; Klartext und Glossar stehen in `wp/texte.py` und
`<script id="texte">` (Test vergleicht beide). Der Klartext steht auch auf Seite 1 von Ausdruck und PDF.

**Expertenmodus:** Gebäudehülle, Heizwert, Vollbenutzungsstunden, Nutzungsgrad, Warmwasser nach DIN V 18599-10,
Lastprofil/Nachheizzeit, Kaltwassertemperatur, Sperrzeit, Betriebsweise, Spreizung, Entzugsleistung, Baureihen.

## Prototyp (Vorführversion)

`prototyp.html` ist eine abgespeckte Fassung zum Zeigen: gleicher Rechenweg und gleiche Darstellung, aber ohne
Preise (auch nicht im Ausdruck), ohne Expertenmodus, ohne VDI-Vergleichstabelle und Zubehörliste, überall als
„Prototyp“ gekennzeichnet und mit eigener Browser-Sicherung. Erzeugt mit `python tools/prototyp.py` aus
`index.html` – nach jeder Änderung neu erzeugen (Test prüft das).

## Rechenweg

1. **Heizlast QH** – Vorgabe (DIN EN 12831), Wohnfläche × W/m², Gebäudehülle (Transmission + Lüftung) oder
   **Jahresverbrauch** wie Excel-Blatt „DIN EN 12831 Heizlast nach Verbrauch mit TWW“:
   Eg,in = Verbrauch · Hu · Ehg,in = Eg,in − Ew,g,in · Øh,g = Ehg,in · η / th · Øh,in = Øh,g + Ew,g,in / (td · 365)
   (th nach VDI 2067, η = 1 wie Excel). Beim Jahresverbrauch ist QGES = Øh,in.
2. **Warmwasser** – Qw,b = V · 1,163 Wh/(l·K) · (45 °C − ϑKW) je Person (oder DIN V 18599-10), Ew,g,in = Qw,b · np · 365.
   Zuschlag QTW automatisch: Jahresverbrauch → Nachheizzeit wie oben, sonst Personen × Lastprofil aus der Literzahl
   (≤ 30 l: 0,10 · ≤ 50 l: 0,20 · darüber 0,25 kW/P). Speicher = Zapftemperatur + 5 K, Puffer für Frischwasserstation
   + 10 K, Ladevorlauf + 5 K (Hinweis, wenn über dem max. Vorlauf des Geräts). Hinweis auf Großanlage nach DVGW W 551.
3. **Sperrzeit** 2/4/6 h → +5/10/15 %. QGES = QH + QTW + QSperr.
4. **Kriterium**: monoenergetisch 0,7 · QGES bei A-7, monovalent QGES bei θe (Standard bei Sole), GEG-Hybrid 0,3 · QH.
5. Je Gerät und Kaskade (CS3800 und CS7400 nicht kaskadierbar, CS5800/6800, CS8800, CS7000 2er, CS5001 bis 14):
   max. Heizleistung beim Auslegungsvorlauf (zwischen 35/45/55/65 °C interpoliert), Bivalenzpunkt mit der
   Gebäudekennlinie (QGES linear bis 0 kW an der Heizgrenze), Heizstab-Bedarf bei θe, Deckungsanteil nach
   VDI 4650 (Luft- bzw. Sole/Wasser, parallel), Taktgrenze über die Mindestleistung. Kurven werden nur im Bereich der
   Herstellerdaten gezeichnet. Sole/Wasser: Leistung konstant (B0), Entzugsleistung und Sondenlänge als Richtwert.
6. Luft/Wasser: Verbindungsleitung Außeneinheit – Gebäude (kleinstes Rohr mit v ≤ 1 m/s und R ≤ 200 Pa/m, Δp mit 30 %
   Einzelwiderständen).
7. Empfehlung: kleinste passende Größe je Baureihe, gesamt Einzelgerät vor Kaskade. Jahresbilanz über SCOP.
8. **E-Heizer je Baugröße** wie Excel-Diagramm: QGES − Heizleistung bei θe (z. B. CS8800 bei 15 kW/−11 °C:
   11 O-T 5,0 · 13 O-T 2,9 · 15 O-T 1,5 kW). Gebäudekennlinie wie Excel unterhalb θe konstant QGES.
   Dazu die Tabelle **Deckungsanteil nach Bivalenzpunkt** (DIN V 4701-10 / VDI 4650) mit markierter Spalte.
9. **Mindestleistung (Modulation):** Herstellerdaten unverändert; Stufen (z. B. CS3800 O-S, Temperaturbänder) werden
   nicht geglättet und im Diagramm erläutert. In der Kaskade gilt die Mindestleistung eines Geräts.
10. **Kennzahlen** auf einen Blick: Jahreswärme, Deckungsanteil (VDI 4650), SCOP und Aufteilung WP-Strom / Heizstab /
    Umweltwärme (`rechnen.energie`).
11. **Geräuschpegel** (`rechnen.schall`): Lp = LWA + 10·lg n + DΩ − 20·lg s − 11 dB (TA Lärm A.2.4.3, vereinfacht) mit dem
    Schallleistungspegel nach ErP aus dem Katalog; DΩ frei 3 / Wand 6 / Ecke 9 dB; Vergleich mit den Immissionsrichtwerten
    TA Lärm 6.1 (Tag/Nacht je Gebiet).
12. **Energiekosten** (`rechnen.kosten`): WP-Strom und Heizstab gegen Erdgas, Heizöl oder Strom-Direktheizung
    (Jahreswärme / Nutzungsgrad · Preis); Vorgabepreise 0,28 / 0,35 €/kWh Strom, Gas 0,12 (η 0,90), Öl 0,11 (η 0,85) – im Tool änderbar.

## MFH-Bestellvorschläge (Musterlösungen)

Beim Mehrfamilienhaus wählt das Tool aus der Kostenübersicht der MFH-Musterlösungen (Bestand 45 W/m², Neubau
30 W/m², je WE 80 m² und 3,5 Personen; Stand 20.08.2026, 62 Lösungen in `daten/mfh_matrix.json`) die passende Musterlösung:
Gebäudetyp → Tabelle, Anlagenart (Hybrid MH200 bzw. bivalent CC8000, sonst monoenergetisch), Warmwasserbereitung → Zeile,
dann die kleinste Lösung mit mindestens so vielen WE, deren Muster-Heizlast die berechnete Heizlast QH abdeckt (von Hand
umschaltbar). Die Wärmepumpe der Musterlösung wird mit dem Rechenkern gegen die eigene Anlage geprüft und bei „Beste
Lösung“ übernommen.

Kaskaden: CS8800 mit Kaskadenregler HPC800i C bis 3 Geräte (wie Musterlösungen), CS5001 mit HPC 301 C bis 14.
Im Schema hängt die Frischwasserstation an einem eigenen FriWa-Puffer, nicht am Trennpuffer der Heizung;
Wohnungsstationen (HIU) hängen über das 2-Leiter-Netz am Puffer, bei DLE zeigt das Schema die Durchlauferhitzer je
Wohnung, bei GEG-Hybrid den Gas-Brennwertkessel als zweiten Wärmeerzeuger am Puffer.

## Gestaltung

Bosch-Gestaltung nach den Tokens des Bosch Frontend-Kits, wie auf bosch-homecomfortgroup.com eingesetzt: Bosch-Blau
blue-50 #007BC0 (Hover #00629A), Rot red-50 #ED0007, Grün green-50 #00884A, Warnung yellow-85 #FFCF00, Grautöne gray-95/90/80;
eckige Buttons, Eingabefelder und Flächen ohne Schatten; Reiter mit blauem Unterstrich; Schrift Bosch Sans, sofern auf dem Rechner
installiert, sonst Arial (keine Google Fonts, keine Schriftdateien im Repo). Aus der HC-Spezifikation: Farbwechsel aufeinander-
folgender Inhaltsbereiche (Weiß / gray-95), weißer Rahmen für Buttons auf blauem Grund, Zahlenfelder rechtsbündig, Linien-Icons
(viewBox 24, Strich 2), Datenschutzhinweis im Fuß mit einem Klick. Streamlit über .streamlit/config.toml und CSS gleich gestaltet.

## Hydraulik-Auswahl (Musterlösungen)

Im Reiter „Hydraulik & Warmwasser“ wählt man zur ausgelegten Maschine die passende Hydraulik aus den Musterlösungen
(Techn. Doku der Musterlösungs-Ordner aus den ZIP-Daten und Nachlieferungen): 58 Hydraulikschemata (Bosch-Schemata
6721… und Planungszeichnungen) zu allen 62 Musterlösungen mit Wärmepumpe, alle mit Excel-WP-Auslegung; Neubau-HIU mit
Wohnungsstationen mit E-Nacherwärmung (HPS, 45-°C-Netz) ist gekennzeichnet; gleiche Zeichnungen in mehreren Ordnern
werden am Inhalt erkannt und zusammengefasst. Bilder: PNG mit Farbpalette, 220 dpi, bis 2600 px (scharf bei kleiner Dateigröße). Fernwärme ist noch nicht im Tool. Bewertet werden Baureihe, Anzahl
(Kaskade), Warmwasser (FriWa, HIU, ohne/DLE, Speicher) und Anlagenart; vorgeschlagen wird die passende Hydraulik, deren
Musterlösung in WE und Gerät am nächsten liegt – jede andere lässt sich von Hand wählen. „Auslegung übernehmen“ setzt die
Eingaben der Excel-Auslegung einer Musterlösung (PLZ, θe, Heizgrenze, W/m² und Fläche, Personen, Lastprofil, Sperrzeit,
Vorlauf, Kriterium, Wärmepumpe); der Rechenkern prüft die Musterlösung nach (Test: QGES und Mindestleistung wie Excel).
Hinweis: Die Excel-Auslegungen der Musterlösungen nutzen das GEG-Hybrid-Kriterium (0,3 · Q) und 35 °C (Neubau) bzw.
55 °C (Bestand) Vorlauf. Die gewählte Hydraulik steht in Ausdruck, PDF und Projektmappe.

Ampel je Hydraulik: ✓ passt direkt (alle Merkmale) · ● Vorlage (gleiche Baureihe – was anzupassen ist, steht dabei,
z. B. „Frischwasserstation mit eigenem Warmwasser-Puffer ergänzen“) · ✗ Prinzip (andere Baureihe, nur zur Orientierung).
Passt keine, wird die ähnlichste als Vorlage vorgeschlagen. Hintergrund: In den Musterlösungs-Ordnern für FriWa, HIU und
bivalent liegen nur Auslegungen, keine Hydraulikzeichnung – fast alle Schemata stammen aus „ohne WW / DLE“. Hinweis bei
Speicher über 4 WE (Leistungskennzahl NL 4).

Übernahme der Daten: `python tools/hydraulik_import.py ORDNER…` (entpackte ZIP-Ordner; erzeugt `daten/hydrauliken.json`
und `daten/hydrauliken/*.jpg`), danach `python tools/excel_import.py --nur-einbetten`. Logik in `wp/hydraulik.py` und
`<script id="hydkern">` (Test vergleicht beide). Fernwärme-Ordner (ohne Wärmepumpe) werden nicht übernommen.

## Heizkurve

Vorlauf-/Rücklauftemperatur über der Außentemperatur nach DIN EN 442 für den maßgebenden Heizkreis (Heizkörper n = 1,3,
10 K; FBH n = 1,1, 5 K; Konvektoren n = 1,4, 10 K) von θe bis zur Heizgrenze, mit max. Vorlauf der Wärmepumpe und den
Werten bei A-7, A2 und A7. Das Leistungsdiagramm rechnet wie das Excel-Werkzeug mit konstantem Vorlauf; die
Gebäudekennlinie läuft von QGES bei θe linear auf 0 kW an der Heizgrenze.

## Systempakete (BOPA)

Zur gewählten Wärmepumpe (Einzelgerät) zeigt das Tool die fertigen Systempakete aus dem Produktkatalog
„Klima-, Lüftungs- und Wärmepumpen-Sortiment“ (März 2026): Paket, Variante, Warmwasser-/Pufferspeicher, Bestell-Nr.,
UVP (im Ausdruck nur „intern“) und Paketinhalt; Pakete zur gewählten Inneneinheit stehen oben (★). Dazu das
empfohlene Zubehör der Baureihe (Heizkreispakete, Nachfüllpaket, MAG, Kabel …). 107 Pakete für CS3800, CS5800/6800,
CS8800, CS7000, CS7400 und CS7800i LW; für CS5001, Supraeco T und Kaskaden gibt es keine Pakete.
Übernahme: `python tools/pakete_import.py KATALOG.pdf`, danach `python tools/excel_import.py --nur-einbetten`.

## Anlagenschema

`wp/schema.py` und `schemaSvg()` in `index.html` erzeugen dasselbe SVG (Test vergleicht beide); das PDF bettet es als
Vektorgrafik ein, Streamlit zeigt es direkt. Piktogramme im Bosch-Planungsstil (Verteilerbalken, FBH mit Wärmewellen,
Heizkörper, Dusche, Außeneinheit mit Ventilator, Speicher mit Heizwendel, nummerierte Abschnitte 1–4).
`node tools/schema_pruefen.js index.html` prüft alle Varianten auf Überschneidungen
(Text über Rohr, Text über Text) – läuft auch in `pytest`.

Die Kurven sind maximale Heizleistungen; bei A-7/W35 stimmen sie auf ±6 % mit „Max. Heizleistung“ im Katalog überein
(Test). Die A2/A7-Werte im Katalog sind Teillastpunkte nach EN 14511 und deshalb kleiner.

## Daten

- `daten/geraete.json` – Leistungskurven (max./min.) aus dem Excel-Werkzeug 2.8.3, VDI-4650-Tabelle.
- `daten/klima.json` – PLZ → Ort, Norm-Außentemperatur (Blatt „Klimadaten“).
- `daten/katalog.json` – von Hand aus dem Gesamtkatalog März 2026: Bestell-Nr., UVP, Technische Daten,
  Inneneinheiten mit E-Heizer, Sole/Wasser (Compress 7800i LW, Supraeco T).

- `daten/bilder/*.jpg` – Produktbilder aus dem Gesamtkatalog (CS3800 O-S aus dem Heat-Pump-Advisor-Ausdruck), erzeugt mit
  `python tools/bilder_import.py KATALOG.pdf [HPA.pdf]` (braucht `pdfimages` aus poppler-utils).

Der Rechenkern stammt aus den Zellformeln des Excel-Werkzeugs; die VBA-Makros enthalten nur Navigation, Druck und
Eingabeprüfung.

Neue Excel-Version übernehmen (die Excel-Datei wird nicht eingecheckt):

```bash
python tools/excel_import.py PFAD/WP-Auslegung_S.xlsm
```

Nach Änderungen an `katalog.json`: `python tools/excel_import.py --nur-einbetten` (bettet alle Daten in
`index.html` ein). Tests: `python -m pytest -q` (vergleicht Python und HTML über `node`).

## Offen

- CS3800iAW 10/13 O-T: Kurven aus dem Excel, Katalogdaten (SCOP, Schall) noch offen – ohne sie keine Strom-, Kosten- und Schallwerte.
- CS8800iAW 11/13/15 O-T: SCOP aus den Bosch-Bestellvorschlägen (Produktdaten) ergänzt.
- CS5001AW 30 und CS5000 AW 22/38: keine Leistungsdaten im Excel. CS7000i/CS7400i nur als Kurven (Katalog: Pakete).
- Sole/Wasser bei 55 °C: Nennwärmeleistung (ErP) statt max. Leistung angesetzt; Kaskaden bei Sole noch nicht freigegeben.

## Betrieb

Docker-Container hinter nginx auf dem eigenen Server (wp.sommer-nt.de, Port 8506), Schritt für Schritt in
[deploy/ANLEITUNG.md](deploy/ANLEITUNG.md). Optionales Passwort über `APP_PASSWORT` in `deploy/.env`.
