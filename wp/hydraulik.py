"""Hydraulik-Auswahl aus den Musterlösungen (ZIP-Daten, tools/hydraulik_import.py) – wie HYD in index.html.

Zur ausgelegten Maschine (Baureihe, Anzahl/Kaskade, Warmwasser, Betriebsweise) werden die Hydraulikschemata der
Musterlösungen bewertet: passend = alle vier Merkmale stimmen. Jede Hydraulik kennt ihre Musterlösungen mit der
Excel-Auslegung; „übernehmen“ setzt deren Eingaben in die Schnellauslegung (Rechenkern prüft gegen).
"""
from __future__ import annotations

import copy

MERKMALE = (("serie", "Baureihe", 8), ("anzahl", "Anzahl Wärmepumpen", 4), ("ww", "Warmwasser", 3), ("system", "Betriebsweise", 2))
WW_TEXT = {"friwa": "Frischwasserstation", "hiu": "Wohnungsstationen (HIU)", "dle": "ohne zentrales Warmwasser (DLE)",
           "speicher": "Warmwasserspeicher"}


def ww_art(e: dict, r: dict) -> str:
    m = e.get("mfh") or {}
    if m.get("art") == "mfh":
        return m.get("ww") or "friwa"
    if not r["tww"]["aktiv"]:
        return "dle"
    return "friwa" if r["tww"]["system"] == "friwa" else "speicher"


def system_art(e: dict, lib: dict | None = None) -> str:
    """Anlagenart: aus der übernommenen Musterlösung (deren Excel-Auslegung nutzt oft das GEG-Hybrid-Kriterium auch bei
    monoenergetischen Anlagen), sonst aus der Betriebsweise (GEG-Hybrid → Hybrid mit zweitem Wärmeerzeuger)."""
    nr = (e.get("hydraulik") or {}).get("loesung")
    L = next((x for x in (lib or {}).get("loesungen", []) if x["id"] == nr), None) if nr else None
    if L:
        return "mono" if L["system"] == "mono" else "hybrid"
    return "hybrid" if e.get("auslegung") == "hybrid" else "mono"


def bewerte(e: dict, r: dict, s: dict, lib: dict | None = None) -> dict:
    g = r["gewaehlt"]
    sys_ = system_art(e, lib)
    passt = {"serie": g["serie"] in s["serien"], "anzahl": g["n"] in s["anzahl"], "ww": ww_art(e, r) in s["ww"],
             "system": sys_ in s["system"] or (sys_ == "hybrid" and "bivalent" in s["system"])}
    punkte = sum(p for k, _, p in MERKMALE if passt[k])
    return {"id": s["id"], "titel": s["titel"], "loesungen": s["loesungen"], "passt": passt, "punkte": punkte,
            "passend": all(passt.values())}


def schemata(e: dict, r: dict, lib: dict) -> list[dict]:
    """Alle Hydraulikschemata, bewertet und sortiert (passende zuerst)."""
    if not r.get("gewaehlt") or not lib:
        return []
    loes = {L["id"]: L for L in lib["loesungen"]}
    g = r["gewaehlt"]
    we = int((e.get("mfh") or {}).get("we") or 0) if (e.get("mfh") or {}).get("art") == "mfh" else 0
    out = []
    for s in lib["schemata"]:
        x = bewerte(e, r, s, lib)
        # Nähe zur Musterlösung: Wohneinheiten und gleiche Gerätegröße (bei gleicher Punktzahl entscheidend)
        x["naehe"] = min(abs((loes[n]["we"] or 0) - we) + (0 if loes[n]["geraet"] == g["geraet"] else 5) for n in s["loesungen"])
        out.append(x)
    out.sort(key=lambda x: (-x["punkte"], x["naehe"], x["id"]))
    return out


def gewaehlt(e: dict, r: dict, lib: dict) -> dict | None:
    """Gewählte Hydraulik (e["hydraulik"]["schema"]) oder automatisch die beste passende."""
    liste = schemata(e, r, lib)
    wahl = (e.get("hydraulik") or {}).get("schema") or ""
    if wahl:
        x = next((x for x in liste if x["id"] == wahl), None)
        if x:
            return {**x, "manuell": True}
    x = next((x for x in liste if x["passend"]), None)
    return {**x, "manuell": False} if x else None


def loesungen(e: dict, r: dict, lib: dict) -> list[dict]:
    """Musterlösungen mit Excel-Auslegung zur Maschine (gleiche Baureihe, Anzahl und Warmwasser)."""
    g = r.get("gewaehlt")
    if not g or not lib:
        return []
    ww = ww_art(e, r)
    out = [L for L in lib["loesungen"] if L["auslegung"] and L["geraet"] and L["n"] == g["n"] and L["ww"] == ww
           and serie_von(L["geraet"]) == g["serie"]]
    return sorted(out, key=lambda L: (abs((L["auslegung"]["qges"] or 0) - r["qges"]), L["id"]))


def serie_von(gid: str) -> str:
    return gid.split("iAW")[0].split(" AW")[0].split("/")[0]


def uebernehmen(e: dict, L: dict) -> dict:
    """Eingaben der Excel-Auslegung einer Musterlösung in die Schnellauslegung übernehmen (neue Eingaben)."""
    a, n = L["auslegung"], copy.deepcopy(e)
    neubau = L["gebaeude"] == "neubau"
    n["gebaeude"]["typ"] = "neubau" if neubau else "sanierung"
    n["projekt"]["plz"], n["projekt"]["ort"] = a.get("plz") or "", a.get("ort") or ""
    n["klima"]["nat"] = a["nat"]
    if a.get("heizgrenze") is not None:
        n["klima"]["heizgrenze"] = a["heizgrenze"]
    n["klima"]["innen"] = a.get("innen") or 20.0
    if a.get("flaeche_m2"):
        n["heizlast"].update(methode="flaeche", flaeche_m2=a["flaeche_m2"], spez_w_m2=a["spez_w_m2"])
    else:
        n["heizlast"].update(methode="vorgabe", vorgabe_kw=a.get("vorgabe_kw") or (a.get("qges") or 0.0))
    n["heizlast"]["gebaeudeart"], n["heizlast"]["vbh"] = "MFH", 2000
    n["mfh"].update(art="mfh", we=L["we"] or n["mfh"]["we"], ww=L["ww"], zelle="", system="mono" if L["system"] == "mono" else "hybrid")
    n["tww"].update(aktiv=a.get("personen", 0) > 0, system="speicher" if L["ww"] == "speicher" else "friwa",
                    personen=a.get("personen") or 0, methode="personen", kw_person=a.get("kw_person") or 0.1)
    n["sperrzeit_h"] = int(a.get("sperrzeit_h") or 0)
    n["auslegung"] = a.get("auslegung") or "monoenergetisch"
    n["vl"] = a.get("vl") or (35.0 if neubau else 55.0)
    n["heizkreise"] = [{"typ": "fbh" if n["vl"] <= 35 else "hk"}]
    n["verteilung"] = n["heizkreise"][0]["typ"]
    n["auswahl"].update(geraet=L["geraet"], anzahl=L["n"], inneneinheit="")
    n["hydraulik"] = {"schema": L["schemata"][0] if L["schemata"] else "", "loesung": L["id"]}
    return n
