"""Stücklisten der MFH-Musterlösungen aus den Bestellvorschlägen (PDF) erzeugen.

    python tools/stueckliste_import.py <Ordner> [<Ordner> ...]
    python tools/excel_import.py --nur-einbetten

Durchsucht die entpackten Musterlösungs-Ordner (z. B. „1.1.1.1_4WE_15kW_CS8800AW13/…“) nach den Bestellvorschlägen
(PDF „4000…“), liest den Abschnitt „Ihre Artikel in der Kurzübersicht“ (Position, Menge, Bezeichnung, Typ, TTNR,
Stückpreis, Alternativen, Bedarfspositionen) und schreibt daten/stuecklisten.json – nur für Musterlösungen aus daten/hydrauliken.json.
Die PDF-Dateien selbst werden nicht übernommen. Prüft je Bestellvorschlag die Summe gegen den Nettowert im PDF.
Braucht pdftotext (poppler-utils).
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
ZIEL = HIER / "daten" / "stuecklisten.json"
RX_LOES = re.compile(r"^(\d\.\d\.\d\.\d+)")
RX_POS = re.compile(r"^(\d+(?:\.\d+)+)\s+(\d+(?:,\d+)?)\s*(x|m|Stk\.?|St\.?)?\s+(.+?)\s{2,}(?:Stückpreis:\s+([\d.,]+))?\s*$")
OHNE_TYP = ("TTNR", "EAN", "https", "pe=", "Link", "Sitz", "Aufsichtsrat", "Nora", "Nummer", "Name des", "Bestellvorschlags",
            "---", "HINWEIS", "Ihre Artikel", "Position", "technische", "Unterlagen")


def zahl(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def pdfs(ordner: list[Path]) -> dict[str, Path]:
    """Bestellvorschlag je Musterlösung (erster Fund gewinnt)."""
    m: dict[str, Path] = {}
    for o in ordner:
        for f in sorted(o.rglob("*.pdf")) + sorted(o.rglob("*.PDF")):
            if not f.name.startswith("4000"):
                continue
            ids = [x.group(1) for x in (RX_LOES.match(t) for t in f.parent.parts) if x]
            if ids and ids[-1] not in m:
                m[ids[-1]] = f
    return m


def lies(pdf: Path) -> dict | None:
    t = subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout
    zeilen = t.splitlines()
    start = next((i for i, z in enumerate(zeilen) if z.startswith("Ihre Artikel in der Kurzübersicht")), None)
    if start is None:
        return None
    ende = next((i for i, z in enumerate(zeilen) if i > start and re.match(r"^\s*(Ihre )?Artikeldetails", z)), len(zeilen))
    gruppen: list[dict] = []
    akt, alternative, bedarf = None, False, False
    for z in zeilen[start:ende]:
        s = z.strip()
        mt = re.match(r"^(\d+) - (.+)$", s)
        if mt and not z.startswith(" "):
            titel = re.sub(r"\s*\(Bedarfs-Titel\)\s*$", "", mt.group(2)).strip()
            if not gruppen or gruppen[-1]["titel"] != titel:   # Titel wiederholt sich je PDF-Seite
                # Bedarfs-Titel: ganze Gruppe optional (z. B. Durchlauferhitzer, Inbetriebnahme) – nicht in der Summe
                gruppen.append({"titel": titel, "bedarf": "(Bedarfs-Titel)" in mt.group(2), "pos": []})
            continue
        if s == "Alternative":
            alternative = True
            continue
        if s == "Bedarfsposition":   # optional, nicht in der Summe des Bestellvorschlags
            bedarf = True
            continue
        m = RX_POS.match(z)
        if m and not z.startswith(" "):
            if not gruppen:
                gruppen.append({"titel": "", "bedarf": False, "pos": []})
            akt = {"pos": m.group(1), "menge": zahl(m.group(2)), "einheit": "m" if m.group(3) == "m" else "Stk",
                   "text": m.group(4).strip(), "typ": "", "ttnr": "", "ep": zahl(m.group(5)) if m.group(5) else None,
                   "summe": None, "alternative": alternative and m.group(1).count(".") >= 2,
                   "bedarf": bedarf or gruppen[-1].get("bedarf", False)}
            alternative = bedarf = False
            gruppen[-1]["pos"].append(akt)
            continue
        if akt is None:
            continue
        mm = re.search(r"TTNR:\s*(\S+)", s)
        if mm:
            akt["ttnr"] = mm.group(1)
        ms = re.search(r"Summe:\s+([\d.,]+)", s)
        if ms:
            akt["summe"] = zahl(ms.group(1))
        if not akt["typ"] and s and not s.startswith(OHNE_TYP) and "Summe:" not in s and not akt["ttnr"]:
            akt["typ"] = s
    netto = re.search(r"Nettowert\s+EUR\s+([\d.]+,\d\d)", t)
    return {"summe": zahl(netto.group(1)) if netto else None, "gruppen": gruppen}


def main(ordner: list[Path]) -> None:
    loes = {L["id"]: L.get("bv_nr") or "" for L in json.loads((HIER / "daten" / "hydrauliken.json").read_text(encoding="utf-8"))["loesungen"]}
    gefunden = pdfs(ordner)
    out, fehlt = {}, []
    for lid in loes:
        if lid not in gefunden:
            fehlt.append(lid)
            continue
        s = lies(gefunden[lid])
        if not s:
            fehlt.append(lid)
            continue
        haupt = [p for g in s["gruppen"] for p in g["pos"] if not p["alternative"]]
        summe = sum(p["summe"] or 0 for p in haupt)
        if s["summe"] and abs(summe - s["summe"]) > 1:
            print(f"{lid}: Summe {summe:.2f} ≠ Nettowert {s['summe']:.2f}")
        out[lid] = {"bv_nr": loes[lid], **s}
    ZIEL.write_text(json.dumps({"quelle": "Bestellvorschläge der MFH-Musterlösungen (Kurzübersicht, Nettopreise)",
                                "loesungen": out}, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n = sum(len(g["pos"]) for s in out.values() for g in s["gruppen"])
    print(f"{len(out)} Stücklisten, {n} Positionen" + (f" · ohne Bestellvorschlag: {', '.join(fehlt)}" if fehlt else ""))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main([Path(a) for a in sys.argv[1:]])
