"""Passende Hydraulikschemata aus der Bosch-Hydraulikdatenbank zur Auslegung (wie hydraulikSchemata() in index.html).

Punkte je Schema: Baureihe (Pflicht), Anzahl/Kaskade, Warmwasser (Speicher, Frischwasserstation, Wohnungsstation/HIU,
ohne), Hybrid, Inneneinheit, Aktualität; Sonderfälle (Solar, Festbrennstoff, Pool) nach hinten.
"""
from __future__ import annotations

import re

SERIE_TOKEN = {"CS3800": ["3800"], "CS5800": ["5800", "6800"], "CS8800": ["8800i", "CS8800"], "CS5001": ["5001AW", "5001 AW"],
               "CS7000": ["7000i AW", "CS7000i"], "CS7400": ["7400"], "CS7800LW": ["7800i LW", "CS7800 "],
               "SupraecoT": ["T220", "T280", "T380", "T480", "Supraeco"]}
SONDER = ("solar_", "festbrennstoff", "kaminofen", "heat_distribution_pool", "ventilation")
LINK = {"pdf": "/download/pdf/file/{nr}.pdf", "bild": "/public/thumbs/{nr}.jpg",
        "suche": "/hdb?query={nr}"}   # DWG gibt die Datenbank nur über ihre Oberfläche heraus (Link „suche“)


def ww_art(e: dict, r: dict) -> str:
    m = e.get("mfh") or {}
    if m.get("art") == "mfh":
        return m.get("ww") or "friwa"
    if not r["tww"]["aktiv"]:
        return "dle"
    return "friwa" if r["tww"]["system"] == "friwa" else "speicher"


def anzahl_titel(titel: str) -> int:
    m = re.match(r"\s*(?:HY)?\s*(\d)\s*x", titel, re.I)
    return int(m.group(1)) if m else 1


def kennworte(komponenten: list[str]) -> list[str]:
    """Kennworte aus den Komponenten einer MFH-Musterlösung (z. B. „2x BP500-7EM“ → „BP500-7EM“)."""
    out = []
    for k in komponenten:
        w = re.sub(r"^\s*\d\s*x\s*", "", k).split(" ")[0].replace("…", "").replace("...", "")
        if len(w) >= 4 and w not in out:
            out.append(w)
    return out


def schemata(e: dict, r: dict, hdb: dict, ie: dict | None, n_max: int = 5, worte: list[str] | None = None) -> list[dict]:
    g = r.get("gewaehlt")
    if not g or not hdb:
        return []
    token = SERIE_TOKEN.get(g["serie"], [])
    ww = ww_art(e, r)
    hybrid = e.get("auslegung") == "hybrid"
    out = []
    for s in hdb["schemata"]:
        text = s["titel"] + " " + s["komponenten"]
        if not any(t in text for t in token) or s["titel"].startswith("CSH"):   # CSH = Gas-Hybridwärmepumpe, andere Baureihe
            continue
        k = s["kategorien"]
        p = 10.0
        n_t = anzahl_titel(s["titel"])
        kask = "waermepumpeluftwasser_kaskade" in k or "waermepumpesolewasser_kaskade" in k or n_t > 1
        if g["n"] > 1:
            p += (6 if n_t == g["n"] else 3) if kask else -6
        elif kask:
            p -= 6
        anzahl_ok = (kask and n_t == g["n"]) if g["n"] > 1 else not kask
        if ww == "hiu":
            ww_ok = "wohnungsstation_zwei_leiter" in k or "Flow 7002" in text or "F7002" in text
            p += 6 if ww_ok else -2
        else:
            ww_ok = {"friwa": "trinkwassererwaermung_frischwasserstation", "speicher": "trinkwassererwaermung_warmwasserspeicher",
                     "dle": "trinkwassererwaermung_ohne"}[ww] in k
            p += 4 if ww_ok else -1
        ist_hybrid = ("Hybrid" in s["titel"] or "HF-Set" in text or "MH200" in text or s["titel"].startswith("HY")
                      or any(c.startswith(("gas_", "oel_")) for c in k))
        p += (4 if ist_hybrid else -3) if hybrid else (-4 if ist_hybrid else 0)
        if ie and ie.get("typ") and ie["typ"].replace("CS5800iAW ", "").replace("CS6800iAW ", "") in text:
            p += 2
        if any(c.startswith(SONDER) for c in k):
            p -= 3
        if worte:   # Komponenten der Musterlösung im Schema (je Treffer +1, höchstens +4)
            kompakt = text.replace(" ", "")
            p += min(4, sum(1 for w in worte if w.replace(" ", "") in kompakt))
        jahr = int(s["stand"][:4]) if s["stand"][:4].isdigit() else 2020
        p += max(0, jahr - 2020) * 0.1
        out.append({"nr": s["nr"], "titel": s["titel"], "stand": s["stand"], "komponenten": s["komponenten"], "bopa": s["bopa"],
                    "dwg": s["dwg"], "punkte": round(p, 2), "passt": {"anzahl": anzahl_ok, "ww": ww_ok, "hybrid": ist_hybrid == hybrid}})
    out.sort(key=lambda x: (-x["punkte"], x["nr"]))
    return [x for x in out if x["punkte"] >= 10][:n_max]


def link(hdb: dict, nr: str, art: str) -> str:
    return hdb["basis"] + LINK[art].format(nr=nr)

