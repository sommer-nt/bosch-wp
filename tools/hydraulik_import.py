"""Hydraulik-Bibliothek aus den Musterlösungs-Ordnern (ZIP-Daten) erzeugen.

    python tools/hydraulik_import.py <Ordner> [<Ordner> ...]
    python tools/excel_import.py --nur-einbetten

Durchsucht die entpackten ZIP-Ordner (z. B. „1.1_Monoenergetisch/…/1.1.3.7_16WE_58kW_CS5001AW42/Techn_Doku“) nach
- Hydraulikschemata (PDF: Bosch-Schemata 6721…, Planungszeichnungen „…_1ug“) → Bild der ersten Seite
  in daten/hydrauliken/<id>.jpg,
- WP-Auslegungen aus dem Excel-Werkzeug („Auslegung WP …“, „WP-Auslegung_S …“) → Eingabewerte (PLZ, θe, Heizgrenze,
  W/m², Fläche bzw. kW, Personen, Lastprofil, Sperrzeit, Kriterium, Vorlauf, Wärmepumpe) für den Rechenkern,
und schreibt daten/hydrauliken.json. Ordnerstruktur: 1.x Bestand, 2.x Neubau; x.1 monoenergetisch, 1.2 bivalent,
1.3 Hybrid, x.4/2.2 Fernwärme (ohne Wärmepumpe, nicht übernommen); Warmwasser aus dem Unterordner (Zentral = FriWa,
Dezentral = HIU, Ohne WW = DLE, Speicher). Bestellvorschläge und Checklisten werden nicht übernommen.
Braucht pdftotext/pdftoppm (poppler-utils) und Pillow.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
ZIEL = HIER / "daten" / "hydrauliken.json"
BILDER = HIER / "daten" / "hydrauliken"
RX_LOES = re.compile(r"^([12])\.(\d)\.(\d)\.(\d+)[_ ]")


def text(pdf: Path) -> str:
    return subprocess.run(["pdftotext", "-layout", str(pdf), "-"], capture_output=True, text=True).stdout


def zahl(s: str) -> float:
    return float(s.replace(".", "").replace(",", "."))


def art(f: Path) -> str | None:
    n = f.name.lower()
    if f.suffix.lower() != ".pdf":
        return None
    if re.match(r"4000\d{3,}", n) or "checkliste" in n or "news" in n or "deckungsanteil" in n:
        return None                       # Bestellvorschläge / Checklisten / Infoblätter nicht übernehmen
    if n.startswith("hiu"):
        return "hiu"
    if "tww" in n or n.startswith("ww-"):
        return "tww"
    if "auslegung" in n:
        return "wp"
    return "schema"


# ------------------------------------------------------------------------------------------------ Einordnung
GERAET = [  # (Muster im Ordnernamen, Geräte-ID der Schnellauslegung)
    (r"CS5001\s*(?:AW)?\s*42|CS5001AW42|CS5001 42", "CS5001 AW42"), (r"CS500[01]\s*(?:AW)?\s*22|CS5001 22|CS5000AW22", "CS5001 AW22"),
    (r"CS88[08]0i?AW\s*15", "CS8800iAW 15 O-T"), (r"CS88[08]0i?AW\s*13", "CS8800iAW 13 O-T"), (r"CS8[08]00i?AW\s*11", "CS8800iAW 11 O-T"),
    (r"CS5800i?AW\s*12|CS5800iAW12", "CS5800/6800iAW 12 OR-T"), (r"CS5800AW\s*10", "CS5800/6800iAW 10 OR-T"),
    (r"CS5800AW\s*7", "CS5800/6800iAW 7 OR-S"),
]


def einordnen(pfad: Path, nr: str) -> dict:
    teile = [p.lower() for p in pfad.parts]
    ordner = next(p for p in pfad.parts if p.startswith(nr))
    g, s = nr.split(".")[0], nr.split(".")[1]
    system = {"1": "mono", "2": "bivalent", "3": "hybrid", "4": "fernwaerme"}[s] if g == "1" else {"1": "mono", "2": "fernwaerme"}[s]
    # Warmwasser aus der Ordnernummer: x.x.1 zentral (FriWa), x.x.2 dezentral (HIU), x.x.3 ohne WW (DLE), 1.1.4 Speicher
    ww = {"1": "friwa", "2": "hiu", "3": "dle", "4": "speicher"}[nr.split(".")[2]]
    rest = ordner[len(nr) + 1:]
    we = int(re.search(r"(\d+)\s*_?WE", rest).group(1)) if re.search(r"(\d+)\s*_?WE", rest) else None
    kw = zahl(re.search(r"(\d+)\s*KW", rest, re.I).group(1)) if re.search(r"(\d+)\s*KW", rest, re.I) else None
    m = re.search(r"(\d)\s*x\s*CS|_(\d)CS", rest)          # „2xCS8800…“, „3x CS…“, „_2CS8800…“
    n = int(next(x for x in m.groups() if x)) if m else 1
    geraet = next((gid for muster, gid in GERAET if re.search(muster, rest, re.I)), None)
    return {"id": nr, "ordner": ordner, "gebaeude": "bestand" if g == "1" else "neubau", "system": system, "ww": ww,
            "we": we, "kw": kw, "geraet": geraet, "n": n}


# ------------------------------------------------------------------------------------------------ Excel-Auslegung
def auslegung(pdf: Path) -> dict | None:
    t = text(pdf)
    if "Wärmepumpen - Auslegung" not in t and "Heizlast QH" not in t:
        return None

    def wert(muster, default=None):
        m = re.search(muster, t)
        return zahl(m.group(1)) if m else default
    m = re.search(r"PLZ:\s+(\d{4,5})\s+(.+?)\s{2,}(-?\d+)", t)
    a = {"datei": pdf.name, "plz": m.group(1) if m else "", "ort": m.group(2).strip() if m else "",
         "nat": float(m.group(3)) if m else wert(r"Norm-Außentemperatur.*?(-?\d+)\s*°C"),
         "vorgabe_kw": wert(r"Heizlast Annahme/Vorgabe\s+([\d.,]+)\s*kW", 0.0),
         "spez_w_m2": wert(r"Spezifischer Wärmebedarf W/m²\s+([\d.,]+)", 0.0),
         "flaeche_m2": wert(r"Beheizte Wohnfläche\s+([\d.,]+)", 0.0),
         "heizgrenze": wert(r"Heizgrenztemperatur \(12°C/15°C\)\s+(-?\d+)"),
         "innen": wert(r"Innentemperatur\s+([\d.,]+)", 20.0),
         "personen": wert(r"Personenanzahl\s+([\d.,]+)", 0.0),
         "kw_person": wert(r"Lastprofil\s+([\d.,]+)\s*kW/P", 0.1),
         "sperrzeit_h": wert(r"Sperrzeiten pro Stunde am Tag\s+([\d.,]+)", 0.0),
         "qges": wert(r"Summe der Heizlasten\s+([\d.,]+)"),
         "mindest_kw": wert(r"Mindestleistung Wärmepumpe.*?([\d.,]+)\s*kW")}
    # Kriterium aus der ausgewiesenen Mindestleistung (der Ausdruck nennt immer auch „GEG-Hybrid“)
    qh = (a["vorgabe_kw"] or a["spez_w_m2"] * a["flaeche_m2"] / 1000) if (a["vorgabe_kw"] or a["flaeche_m2"]) else None
    mi, qg = a["mindest_kw"], a["qges"]
    if mi and ((qh and abs(mi - 0.3 * qh) < 0.05) or (qg and abs(mi - 0.3 * qg) < 0.05)):
        a["auslegung"] = "hybrid"
    elif mi and qg and abs(mi - 0.7 * qg) < 0.05:
        a["auslegung"] = "monoenergetisch"
    elif mi and qg and abs(mi - qg) < 0.05:
        a["auslegung"] = "monovalent"
    else:
        a["auslegung"] = None
    m = re.search(r"Diagramm\s+(.+?)\s{3,}(.+?)\s*$", t, re.M)
    a["diagramm"] = re.sub(r"\s{2,}", " ", (m.group(1) + " " + m.group(2)) if m else "").strip()
    m = re.search(r"W(\d{2})\s*°C|(\d{2})\s*°C\s*$", a["diagramm"])
    a["vl"] = float(next(x for x in m.groups() if x)) if m else None
    return a


# ------------------------------------------------------------------------------------------------ Schema
def schema_titel(pdf: Path, ordner: str = "", nr: str = "") -> str:
    t = text(pdf)
    zeilen = [z.strip() for z in t.splitlines() if z.strip()]
    for i, z in enumerate(zeilen):
        if z.startswith("Hydraulikschema") and i + 1 < len(zeilen):
            return zeilen[i + 1]
    if re.fullmatch(r"[A-Za-z0-9_-]{3,8}\d", pdf.stem) and ordner:     # Kurzname (HPC8001, CC80001 …): Titel aus dem Ordner
        return re.sub(r"[_ ]+", " ", ordner[len(nr) + 1:]).strip()
    return re.sub(r"_1u?g.*$", "", pdf.stem).replace("_", " ")


def schema_id(pdf: Path, nr: str, vorhanden: dict, inhalt: dict) -> str:
    """Gleicher Inhalt = gleiches Schema (auch in mehreren Ordnern); gleicher Dateiname mit anderem Inhalt bekommt die
    Ordnernummer angehängt (die Nachlieferungen heißen oft nur HPC8001.PDF, CC80001.PDF …)."""
    md5 = hashlib.md5(pdf.read_bytes()).hexdigest()
    if md5 in inhalt:
        return inhalt[md5]
    sid = re.sub(r"[^\w-]+", "_", pdf.stem)
    if sid in vorhanden:
        sid = f"{sid}_{nr.replace('.', '-')}"
    inhalt[md5] = sid
    return sid


def hydraulik_seite(pdf: Path) -> int:
    """Seite mit dem eigentlichen Schema: bei Bosch-Schemata (Deckblatt + „Hydraulik“) die Seite „Hydraulik“, sonst Seite 1."""
    for seite in (1, 2, 3):
        t = subprocess.run(["pdftotext", "-layout", "-f", str(seite), "-l", str(seite), str(pdf), "-"], capture_output=True, text=True).stdout
        erste = next((z.strip() for z in t.splitlines() if z.strip()), "")
        if erste.startswith("Hydraulik") and "Verdrahtungsplan" not in erste:
            return seite
    return 1


def bild(pdf: Path, ziel: Path) -> None:
    from PIL import Image
    seite = str(hydraulik_seite(pdf))
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(["pdftoppm", "-r", "100", "-f", seite, "-l", seite, "-png", str(pdf), str(Path(tmp) / "s")], check=True)
        png = next(Path(tmp).glob("s*.png"))
        im = Image.open(png).convert("RGB")
        im.thumbnail((1400, 1400))
        im.save(ziel, "JPEG", quality=62, optimize=True, progressive=True)


def matrix_geraet(info: dict) -> tuple[str | None, int]:
    """Wärmepumpe aus der Kostenübersicht (daten/mfh_matrix.json): gleiche Tabelle, Betriebsweise, Warmwasser und WE."""
    m = json.loads((HIER / "daten" / "mfh_matrix.json").read_text(encoding="utf-8"))
    sys_ = "hybrid" if info["system"] in ("hybrid", "bivalent") else "mono"
    z = [c for c in m["zellen"] if c["tabelle"] == info["gebaeude"] and c["system"] == sys_ and c["ww"] == info["ww"] and c["we"] == info["we"]]
    return (z[0]["geraet"], z[0]["n"]) if z else (None, 1)


def main(ordner: list[str]) -> None:
    BILDER.mkdir(parents=True, exist_ok=True)
    loesungen, schemata, inhalt = {}, {}, {}
    for o in ordner:
        for f in sorted(Path(o).rglob("*")):
            if not f.is_file():
                continue
            nr_teil = next((p for p in f.parts if RX_LOES.match(p)), None)
            if not nr_teil or art(f) is None:
                continue
            nr = ".".join(RX_LOES.match(nr_teil).groups())
            info = einordnen(f.parent, nr)
            if info["system"] == "fernwaerme":
                continue
            if not info["geraet"]:
                info["geraet"], info["n"] = matrix_geraet(info)
            L = loesungen.setdefault(nr, {**info, "schemata": [], "auslegung": None, "tww": [], "hiu": []})
            a = art(f)
            if a == "wp":
                if L["auslegung"]:
                    continue                                          # zweite (gleiche) Auslegung im Ordner
                L["auslegung"] = auslegung(f)
                if L["auslegung"] and L["auslegung"]["vl"] is None:   # CS5001-Blatt ohne Vorlauf im Diagrammtitel
                    L["auslegung"]["vl"] = 55.0 if info["gebaeude"] == "bestand" else 35.0
                    L["auslegung"]["vl_angenommen"] = True
            elif a in ("tww", "hiu"):
                L[a].append(f.name)
            else:
                sid = schema_id(f, nr, schemata, inhalt)
                if sid not in schemata:
                    bild(f, BILDER / f"{sid}.jpg")
                    schemata[sid] = {"id": sid, "datei": f.name, "titel": schema_titel(f, info["ordner"], nr), "loesungen": []}
                if nr not in schemata[sid]["loesungen"]:
                    schemata[sid]["loesungen"].append(nr)
                if sid not in L["schemata"]:
                    L["schemata"].append(sid)
    # Merkmale der Schemata aus den Musterlösungen, in denen sie vorkommen
    for s in schemata.values():
        ls = [loesungen[n] for n in s["loesungen"]]
        s["serien"] = sorted({l_["geraet"].split("iAW")[0].split(" AW")[0].split("/")[0] for l_ in ls if l_["geraet"]})
        s["anzahl"] = sorted({l_["n"] for l_ in ls})
        s["ww"] = sorted({l_["ww"] for l_ in ls})
        s["system"] = sorted({l_["system"] for l_ in ls})
        s["gebaeude"] = sorted({l_["gebaeude"] for l_ in ls})
        s["loesungen"].sort(key=lambda x: [int(t) for t in x.split(".")])
    out = {"quelle": "Musterlösungen MFH (Bosch Home Comfort, Techn. Doku der Musterlösungs-Ordner)",
           "schemata": [schemata[k] for k in sorted(schemata)],
           "loesungen": [loesungen[k] for k in sorted(loesungen, key=lambda x: [int(t) for t in x.split(".")])]}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(schemata)} Hydraulikschemata, {len(out['loesungen'])} Musterlösungen "
          f"({sum(1 for l_ in out['loesungen'] if l_['auslegung'])} mit Excel-Auslegung) -> {ZIEL.relative_to(HIER)}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    main(sys.argv[1:])
