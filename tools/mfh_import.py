"""Liest die MFH-Musterbestellvorschläge (GAEB DA 1990, *.D83) ein und schreibt daten/mfh_vorlagen.json.

    python tools/mfh_import.py <Ordner> [<Ordner> ...]
    python tools/excel_import.py --nur-einbetten

Durchsucht die Ordner rekursiv nach *.D83 (auch in Zip-Dateien entpackte Ordner). Je Datei entsteht eine Vorlage
(Bestellvorschlag-Nr. = Vergabe-Nr., Hinweis/Annahmen, Positionen mit Bestell-Nr., Menge, Einheit, Einzelpreis und
Positionsart). Positionsart wie GAEB: N = Normalposition, G = Grundposition, A = Alternativposition (Wahlposition,
gleiche Gruppe), zweite Stelle E = Bedarfsposition (Eventualposition). Langtexte werden je Bestell-Nr. einmal gespeichert
und beim Export wieder eingesetzt.

Die Übersicht (welche Lösung für wie viele Wohneinheiten) steht von Hand gepflegt in daten/mfh_matrix.json
(Kostenübersicht MFH-Musterbestellvorschläge Bestand/Neubau). Die D83-Dateien selbst werden nicht eingecheckt.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
ZIEL = HIER / "daten" / "mfh_vorlagen.json"


def lies_d83(pfad: Path) -> dict:
    """Satzarten: 01 Titel, 11/12 Gruppe (Los), 20 Text (Vorbemerkung), 21 Position, 23 Preis, 25 Kurztext, 26 Langtext."""
    zeilen = pfad.read_bytes().decode("cp850").splitlines()
    titel, datum, gruppen, cur, akt = "", "", [], None, None
    for z in zeilen:
        sa, t = z[:2], z[2:74].rstrip(" ")
        if sa == "01":
            titel, datum = t[:40].strip(), t[40:50].strip()
        elif sa == "11":
            akt = {"nr": t[:2], "titel": "", "elemente": []}
            gruppen.append(akt)
            cur = None
        elif sa == "12" and akt is not None and cur is None:
            akt["titel"] = t.strip()
        elif sa == "20" and akt is not None:
            cur = {"text": []}
            akt["elemente"].append(cur)
        elif sa == "21" and akt is not None:
            cur = {"oz": t[:6], "art": t[9:12], "wahl": t[12:16].strip(), "menge": int(t[21:32]) / 1000,
                   "einheit": t[32:36].strip(), "artnr": "", "tt": False, "kurz": [], "lang": [], "ep": None}
            akt["elemente"].append(cur)
        elif sa == "23" and cur is not None and "oz" in cur:
            cur["ep"] = int(t[10:20]) / 100 if t[10:20].strip() else None
        elif sa == "25" and cur is not None and "oz" in cur:
            if t.startswith("Typ-Teile-Nr.:"):
                cur["artnr"], cur["tt"] = t.split(":", 1)[1].strip(), True
            else:
                cur["kurz"].append(t)
        elif sa == "26" and cur is not None:
            (cur["lang"] if "oz" in cur else cur["text"]).append(t)
    for g in gruppen:   # Bestell-Nr. bei Dienstleistungen nur im Langtext („Bestell-Nr.: …“)
        for p in g["elemente"]:
            if "oz" in p and not p["artnr"]:
                for s in p["lang"]:
                    if s.strip().startswith("Bestell-Nr.:"):
                        p["artnr"] = s.split(":", 1)[1].strip()
    # Bestellvorschlag-Nr.: vollständig nur im Dateinamen (Satz 00 kürzt die Vergabe-Nr. auf 8 Stellen)
    nr = "".join(c for c in pfad.name.split("_")[0] if c.isdigit())
    return {"nr": nr, "titel": titel, "datum": datum, "datei": pfad.name, "gruppen": gruppen}


def main(ordner: list[str]) -> None:
    vorlagen, langtexte = {}, {}
    for o in ordner:
        for f in sorted(Path(o).rglob("*")):
            if f.suffix.lower() != ".d83":
                continue
            v = lies_d83(f)
            n = 0
            for g in v["gruppen"]:
                for p in g["elemente"]:
                    if "oz" not in p:
                        continue
                    n += 1
                    schluessel = p["artnr"] or "|".join(p["kurz"])
                    lang = p.pop("lang")
                    if lang and langtexte.setdefault(schluessel, lang) != lang:   # abweichender Text: eigener Schlüssel
                        schluessel = f"{schluessel}#{v['nr']}{p['oz']}"
                        langtexte[schluessel] = lang
                    p["lang"] = schluessel if lang else None
            print(f"{v['nr']}  {n:3d} Positionen  {f.name}")
            vorlagen[v["nr"]] = v
    out = {"quelle": "MFH-Musterbestellvorschläge Bosch Home Comfort (GAEB DA 1990 *.D83)",
           "vorlagen": dict(sorted(vorlagen.items())), "langtexte": langtexte}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"{len(vorlagen)} Vorlagen, {len(langtexte)} Langtexte -> {ZIEL.relative_to(HIER)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
