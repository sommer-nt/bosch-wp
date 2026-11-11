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
LINK = {"pdf": "/download/pdf/file/{nr}.pdf", "dwg": "/download/dwg/file/{nr}.dwg", "bild": "/public/thumbs/{nr}.jpg",
        "suche": "/hdb?query={nr}"}


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


def schemata(e: dict, r: dict, hdb: dict, ie: dict | None, n_max: int = 5) -> list[dict]:
    g = r.get("gewaehlt")
    if not g or not hdb:
        return []
    token = SERIE_TOKEN.get(g["serie"], [])
    ww = ww_art(e, r)
    hybrid = e.get("auslegung") == "hybrid"
    out = []
    for s in hdb["schemata"]:
        text = s["titel"] + " " + s["komponenten"]
        if not any(t in text for t in token):
            continue
        k = s["kategorien"]
        p = 10.0
        n_t = anzahl_titel(s["titel"])
        kask = "waermepumpeluftwasser_kaskade" in k or "waermepumpesolewasser_kaskade" in k or n_t > 1
        if g["n"] > 1:
            p += (6 if n_t == g["n"] else 3) if kask else -6
        elif kask:
            p -= 6
        if ww == "hiu":
            p += 6 if ("wohnungsstation_zwei_leiter" in k or "Flow 7002" in text or "F7002" in text) else -2
        elif ww == "friwa":
            p += 4 if "trinkwassererwaermung_frischwasserstation" in k else -1
        elif ww == "speicher":
            p += 4 if "trinkwassererwaermung_warmwasserspeicher" in k else -1
        else:
            p += 4 if "trinkwassererwaermung_ohne" in k else -1
        ist_hybrid = ("Hybrid" in s["titel"] or "HF-Set" in text or "MH200" in text or s["titel"].startswith("HY")
                      or any(c.startswith(("gas_", "oel_")) for c in k))
        p += (4 if ist_hybrid else -3) if hybrid else (-4 if ist_hybrid else 0)
        if ie and ie.get("typ") and ie["typ"].replace("CS5800iAW ", "").replace("CS6800iAW ", "") in text:
            p += 2
        if any(c.startswith(SONDER) for c in k):
            p -= 3
        jahr = int(s["stand"][:4]) if s["stand"][:4].isdigit() else 2020
        p += max(0, jahr - 2020) * 0.1
        out.append({"nr": s["nr"], "titel": s["titel"], "stand": s["stand"], "komponenten": s["komponenten"], "bopa": s["bopa"],
                    "dwg": s["dwg"], "punkte": round(p, 2)})
    out.sort(key=lambda x: (-x["punkte"], x["nr"]))
    return [x for x in out if x["punkte"] >= 10][:n_max]


def link(hdb: dict, nr: str, art: str) -> str:
    return hdb["basis"] + LINK[art].format(nr=nr)
