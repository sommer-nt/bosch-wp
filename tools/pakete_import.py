"""Systempakete (BOPA) aus dem Produktkatalog „Klima-, Lüftungs- und Wärmepumpen-Sortiment“ übernehmen.

    python tools/pakete_import.py  EKWP_Bosch-Klima-Lueftungs-Waermepumpen-Sortiment.pdf

Liest die Paketseiten (Luft/Wasser und Sole/Wasser) mit `pdftotext -raw`, ordnet jedes Paket einem Gerät aus
daten/geraete.json zu und schreibt daten/pakete.json: Paketname, Bestell-Nr., UVP, Warmwasser-/Pufferspeicher,
Paketinhalt und die empfohlenen Zubehörpakete je Baureihe. Danach `python tools/excel_import.py --nur-einbetten`.
Der Katalog selbst wird nicht eingecheckt.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
DATEN = HIER / "daten"
PREIS = r"([\d.]+),(––|\d{2})"


def preis(ganz: str, rest: str) -> float:
    return float(ganz.replace(".", "")) + (0 if rest == "––" else int(rest) / 100)


def seiten(pdf: Path) -> list[str]:
    with tempfile.TemporaryDirectory() as tmp:
        ziel = Path(tmp) / "k.txt"
        subprocess.run(["pdftotext", "-raw", str(pdf), str(ziel)], check=True)
        return ziel.read_text(encoding="utf-8").split("\f")


def geraet_zuordnen(text: str, geraete: list[dict]) -> str | None:
    """Variantentext des Katalogs -> Geräte-ID aus geraete.json (Farbvarianten B und Ausführungen zählen mit)."""
    t = " ".join(text.split())
    m = re.search(r"CS8800iAW (\d+) O-T", t)
    if m:
        return f"CS8800iAW {m.group(1)} O-T"
    m = re.search(r"AW (?:OR )?(\d+)[ -]?(?:OR- ?)?-? ?([ST])\b", t)
    if m and ("CS6800" in t or "CS5800" in t):
        return f"CS5800/6800iAW {m.group(1)} OR-{m.group(2)}"
    m = re.search(r"CS3800iAW (\d+) O[ERM]?-?([ST])", t)
    if m:
        return f"CS3800iAW {m.group(1)} O-{m.group(2)}"
    m = re.search(r"CS700[01]iAW (\d+)", t)
    if m:
        return f"CS7000iAW {m.group(1)}"
    m = re.search(r"CS7400iAW (\d+)", t)
    if m:
        return f"CS7400iAW {m.group(1)}"
    m = re.search(r"CS7800i ?LW (\d+)", t)
    if m:
        return f"CS7800iLW {m.group(1)}"
    return None


def zubehoerpakete(seite: str) -> dict:
    """Seiten „Zubehörpakete“: Beschreibung, Paketname (BOPA …), Bestell-Nr., UVP."""
    out = {}
    text = seite[seite.find("Bestell-Nr. €") + len("Bestell-Nr. €"):]
    pos = 0
    for m in re.finditer(r"(BOPA [^\n]*?)\s*(?:\n(\d{2}))?\s*\n?(\d{10}) " + PREIS, text):
        besch = " ".join(z.strip() for z in text[pos:m.start()].splitlines() if z.strip() and not z.startswith(("Deutschland", "Unverbindliche")))
        pos = m.end()
        name = (m.group(1) + (" " + m.group(2) if m.group(2) else "")).strip()
        out[m.group(3)] = {"text": f"{name} – {besch}" if besch else name, "artnr": m.group(3), "uvp": preis(m.group(4), m.group(5))}
    return out


INNEN = ["AWMBi D", "AWEi D", "CS6800iAW 12 MB", "CS6800iAW 12 M", "CS6800iAW 12 E", "CS5800iAW 12 MB", "CS5800iAW 12 M",
         "CS5800iAW 12 E", "AWMi", "AWEi"]


def inneneinheit(variante: str) -> str | None:
    """Inneneinheit eines Pakets (Typ wie in katalog.json), CS3800: OM = AWMi, OE = AWEi."""
    for typ in INNEN:
        if re.search(re.escape(typ) + r"(?![\w])", variante):
            return typ
    if re.search(r"CS3800iAW \d+ OM", variante):
        return "AWMi"
    if re.search(r"CS3800iAW \d+ OE", variante):
        return "AWEi"
    return None


def lese(pdf: Path) -> dict:
    ids = {g["id"] for g in json.loads((DATEN / "geraete.json").read_text(encoding="utf-8"))["geraete"]}
    s = seiten(pdf)
    pakete, zubehoer, unbekannt, allgemein = [], {}, [], {}
    for nr, seite in enumerate(s, start=1):
        if "Paketinhalt" not in seite or "BOPA" not in seite:
            continue
        zeilen = [z.strip() for z in seite.splitlines()]
        if not any(re.search(r"Pakete? (für|mit)|- Pakete", z) for z in zeilen):
            allgemein.update(zubehoerpakete(seite))      # Seiten „Zubehörpakete“ (Heizkreispakete u. a.)
            continue
        # Titel: Zeilen ab „… Pakete …“ bis „Paketinhalt“ bzw. „Empfohlene …“
        i0 = next(i for i, z in enumerate(zeilen) if re.search(r"Pakete? (für|mit)|- Pakete", z))
        titel = []
        for z in zeilen[i0:]:
            if z.startswith(("Paketinhalt", "Empfohlene")):
                break
            titel.append(z)
        # Inhalt: Aufzählung „–…“ bis „Anlagenschema“
        inhalt, j = [], zeilen.index("Paketinhalt") + 1
        for z in zeilen[j:]:
            if z.startswith("Anlagenschema"):
                break
            if z.startswith("–"):
                inhalt.append(z.lstrip("–").strip())
            elif inhalt and z and not z.startswith("Alle Pakete"):
                inhalt[-1] += " " + z
        kopf = seite.index("Paket Bestell-Nr. €")
        block = seite[kopf + len("Paket Bestell-Nr. €"):]
        ende = block.find("Typ Bezeichnung Bestell-Nr. €")
        teil = block if ende < 0 else block[:ende]
        pos, letzte = 0, ""
        for m in re.finditer(r"(\d+|–) (\d+|–)\s*\nBOPA\s*\n(\S+)\s*\n(77\d{8}) " + PREIS, teil):
            variante = " ".join(teil[pos:m.start()].split()) or letzte   # leere Zeile = weitere Speichervariante
            letzte, pos = variante, m.end()
            gid = geraet_zuordnen(variante, [])
            if gid not in ids:
                unbekannt.append((nr, variante))
                continue
            pakete.append({"paket": "BOPA " + m.group(3), "artnr": m.group(4), "uvp": preis(m.group(5), m.group(6)),
                           "geraet": gid, "variante": variante, "ww_l": None if m.group(1) == "–" else int(m.group(1)),
                           "puffer_l": None if m.group(2) == "–" else int(m.group(2)),
                           "titel": " ".join(titel), "inhalt": inhalt, "seite": nr})
        # Empfohlene Zubehörpakete (auf der Seite selbst oder der folgenden Seite)
        for quelle in (block[ende:] if ende >= 0 else "", s[nr] if nr < len(s) and "Paketinhalt" not in s[nr] else ""):
            serie = re.match(r"(CS\d{4})", pakete[-1]["geraet"]).group(1) if pakete else None
            if not serie or not quelle:
                continue
            serie = {"CS6800": "CS5800"}.get(serie, serie)
            puffer = []
            for z in quelle.splitlines():
                z = z.strip()
                m = re.search(r"^(.*?)\s*(\d{7,10}) " + PREIS + r"$", z)
                if m and not z.startswith("Deutschland"):
                    text = " ".join(puffer + [m.group(1)]).strip()
                    text = re.sub(r"^.*?(Dienstleistungen|Wärmepumpen)\s+", "", text) if "Empfohlene" in text or "Pakete" in text else text
                    text = text.lstrip("– ").strip()
                    puffer = []
                    if text and "Bestell-Nr." not in text:
                        zubehoer.setdefault(serie, {})[m.group(2)] = {"text": text, "artnr": m.group(2),
                                                                    "uvp": preis(m.group(3), m.group(4))}
                elif z and not z.startswith(("Typ Bezeichnung", "Unverbindliche", "Deutschland", "INKL.")) and not re.match(r"^\d{4}$", z):
                    puffer.append(z)
                    puffer = puffer[-4:]
    for p_ in pakete:
        p_["inneneinheit"] = inneneinheit(p_["variante"])
    for liste in zubehoer.values():
        for z_ in liste.values():
            z_["text"] = re.sub(r"^.*?Empfohlene Zubehörpakete, Zubehöre und Dienstleistungen\s*", "", z_["text"]).lstrip("– ").strip()
    zubehoer = {{"CS7800": "CS7800LW"}.get(k, k): v for k, v in zubehoer.items()}
    return {"quelle": f"Produktkatalog {pdf.name}", "pakete": pakete, "zubehoerpakete": list(allgemein.values()),
            "zubehoer": {k: list(v.values()) for k, v in zubehoer.items()}, "unbekannt": unbekannt}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    d = lese(Path(sys.argv[1]))
    for nr, v in d.pop("unbekannt"):
        print(f"nicht zugeordnet (Seite {nr}): {v}")
    (DATEN / "pakete.json").write_text(json.dumps(d, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{len(d['pakete'])} Pakete, Zubehör für {', '.join(f'{k} ({len(v)})' for k, v in d['zubehoer'].items())}")
