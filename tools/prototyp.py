"""Erzeugt prototyp.html – abgespeckte Vorführversion der WP-Schnellauslegung aus index.html.

    python tools/prototyp.py

Gleicher Rechenweg und gleiche Darstellung wie index.html, aber
- ohne Preise (UVP aus Katalog- und Paketdaten entfernt, Spalten ausgeblendet),
- ohne Expertenmodus (Standardwerte fest), ohne Excel-Vergleichstabelle VDI 4650 und ohne Zubehörliste,
- deutlich als „Prototyp“ gekennzeichnet (Kopf, Ausdruck, Fußzeile) und mit eigener Browser-Sicherung.
Nach jeder Änderung an index.html neu erzeugen (Test prüft, dass prototyp.html aktuell ist).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent

CSS = """
  /* ---- Prototyp: Vorführversion ---- */
  #bExperte, .exp, .preis, label.f.nur-intern, details { display:none !important }
  .proto{font-size:12px;font-weight:800;letter-spacing:.8px;color:#fff;background:#e20015;border-radius:6px;padding:4px 10px}
  .proto-hinweis{background:#fff1f2;border:1px solid #f5c2c7;color:#9b1c24;border-radius:8px;padding:8px 12px;margin:0 0 14px;font-size:13px}
  [data-theme="dark"] .proto-hinweis{background:#3a1418;border-color:#6b2730;color:#ffb3ba}
  .dk-proto{position:absolute;top:0;right:0;font-size:8pt;font-weight:800;color:#e20015;letter-spacing:.6px}
"""

JS = r"""
<script id="prototyp">
// Prototyp: Expertenmodus aus, keine Preise, keine VDI-Vergleichstabelle, keine Zubehörliste
(function () {
  const kandidatenOrig = kandidatenTabelle, paketeOrig = paketeHtml, druckOrig = baueDruck;
  kandidatenTabelle = (r, preise, nurPassend) => kandidatenOrig(r, false, nurPassend);
  paketeHtml = (r, preise, druck) => paketeOrig(r, false, druck);
  vdiTabelle = () => '';
  const wpKarteOrig = wpKarte;
  wpKarte = r => wpKarteOrig(r).replace(/<div>UVP \(intern\)<b>[\s\S]*?<\/b><\/div>/, '');
  baueDruck = function () {
    E.preise_drucken = false; druckOrig();
    document.querySelectorAll('#druck .seite').forEach(s => s.insertAdjacentHTML('afterbegin', '<div class="dk-proto">PROTOTYP</div>'));
  };
  window.addEventListener('beforeprint', baueDruck);
  const akt = aktualisiere;
  aktualisiere = function () { E.experte = false; E.preise_drucken = false; akt(); };
  aktualisiere();
})();
</script>
"""


def ohne_preise(daten: str) -> str:
    """Alle UVP-Werte in eingebetteten JSON-Daten auf null setzen."""
    return re.sub(r'"uvp":\s*[\d.]+', '"uvp":null', daten)


def baue() -> str:
    s = (HIER / "index.html").read_text(encoding="utf-8")
    ersetze = [
        ("<title>Bosch WP-Schnellauslegung</title>", "<title>Bosch WP-Schnellauslegung – Prototyp</title>"),
        ('<div class="logo">BOSCH <span>WP-Schnellauslegung</span></div>',
         '<div class="logo">BOSCH <span>WP-Schnellauslegung</span></div>\n  <div class="proto">PROTOTYP</div>'),
        ("const SPEICHER_KEY = 'wp_auslegung_v1';", "const SPEICHER_KEY = 'wp_auslegung_prototyp_v1';"),
        ('<label class="f">Preise (UVP) drucken – intern', '<label class="f nur-intern">Preise (UVP) drucken – intern'),
        ("<span>© Bosch Thermotechnik GmbH · WP-Schnellauslegung</span>",
         "<span>© Bosch Thermotechnik GmbH · WP-Schnellauslegung · Prototyp</span>"),
        ('<div class="grid">',
         '<div class="proto-hinweis"><b>Prototyp zur Vorführung</b> – Funktionsumfang reduziert, ohne Preise. '
         'Ergebnisse unverbindlich, ersetzen keine Fachplanung.</div>\n<div class="grid">'),
        ("</style>", CSS + "</style>"),
    ]
    for alt, neu in ersetze:
        assert s.count(alt) == 1, alt
        s = s.replace(alt, neu)
    a, b = s.index("/*DATEN-START*/"), s.index("/*DATEN-ENDE*/")
    s = s[:a] + ohne_preise(s[a:b]) + s[b:]
    i = s.rindex("</body>")
    return s[:i] + JS + s[i:]


if __name__ == "__main__":
    (HIER / "prototyp.html").write_text(baue(), encoding="utf-8")
    print("prototyp.html erzeugt")
