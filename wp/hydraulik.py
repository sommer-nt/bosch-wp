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
# Ampel je Hydraulik: passt direkt / als Vorlage (gleiche Baureihe, Rest anpassen) / nur Prinzip (andere Baureihe)
STUFE_TEXT = {"passt": "passt direkt", "vorlage": "als Vorlage nutzbar – anpassen", "prinzip": "nur als Prinzip – andere Baureihe"}
WW_ERGAENZEN = {"friwa": "Frischwasserstation mit eigenem Warmwasser-Puffer ergänzen (nicht am Trennpuffer)",
                "hiu": "Wohnungsstationen (HIU) über ein 2-Leiter-Netz ab dem Heizungspuffer ergänzen",
                "dle": "Warmwasserteil entfällt – Durchlauferhitzer je Wohnung",
                "speicher": "Warmwasserspeicher an der Wärmepumpe ergänzen"}
SYSTEM_TEXT = {"mono": "monoenergetisch/monovalent", "hybrid": "Hybrid MH200 (Gas-Brennwert + Wärmepumpe)",
               "bivalent": "bivalent CC8000 (Kessel + Wärmepumpe)"}
SYSTEM_ERGAENZEN = {"hybrid": "Gas-Brennwertgerät als Hybrid über das Hybridmodul MH200 einbinden",
                    "bivalent": "Gaskessel bivalent über den Kaskadenregler CC8000 einbinden",
                    "mono": "zweiten Wärmeerzeuger des Schemas weglassen (monoenergetisch mit Heizstab)"}


def ww_art(e: dict, r: dict) -> str:
    m = e.get("mfh") or {}
    if m.get("art") == "mfh":
        return m.get("ww") or "friwa"
    if not r["tww"]["aktiv"]:
        return "dle"
    return "friwa" if r["tww"]["system"] == "friwa" else "speicher"


def system_art(e: dict, lib: dict | None = None) -> str:
    """Anlagenart mono / hybrid (MH200) / bivalent (CC8000): aus der übernommenen Musterlösung (deren Excel-Auslegung nutzt
    oft das GEG-Hybrid-Kriterium auch bei monoenergetischen Anlagen), sonst aus der Wahl beim Mehrfamilienhaus, sonst aus der
    Betriebsweise (GEG-Hybrid → Hybrid mit zweitem Wärmeerzeuger)."""
    nr = (e.get("hydraulik") or {}).get("loesung")
    L = next((x for x in (lib or {}).get("loesungen", []) if x["id"] == nr), None) if nr else None
    if L:
        return L["system"]
    m = e.get("mfh") or {}
    if m.get("art") == "mfh" and m.get("system") in SYSTEM_TEXT:
        return m["system"]
    return "hybrid" if e.get("auslegung") == "hybrid" else "mono"


def bewerte(e: dict, r: dict, s: dict, lib: dict | None = None) -> dict:
    g = r["gewaehlt"]
    sys_ = system_art(e, lib)
    passt = {"serie": g["serie"] in s["serien"], "anzahl": g["n"] in s["anzahl"], "ww": ww_art(e, r) in s["ww"],
             "system": sys_ in s["system"]}
    punkte = sum(p for k, _, p in MERKMALE if passt[k])
    passend = all(passt.values())
    return {"id": s["id"], "titel": s["titel"], "loesungen": s["loesungen"], "passt": passt, "punkte": punkte,
            "passend": passend, "stufe": "passt" if passend else ("vorlage" if passt["serie"] else "prinzip"),
            "anpassen": anpassen(passt, g, s, ww_art(e, r), sys_)}


def anpassen(passt: dict, g: dict, s: dict, ww: str, sys_: str) -> list[str]:
    """Was an der Hydraulik zu ändern ist, damit sie zur ausgelegten Maschine passt (Klartext)."""
    t = []
    if not passt["serie"]:
        t.append(f"Baureihe: Schema zeigt {' / '.join(s['serien'])} statt {g['serie']} – Wärmepumpe, Inneneinheit und Anschlüsse "
                 f"nach Unterlage der {g['serie']}; Puffer und Heizkreise sind übertragbar")
    if not passt["anzahl"]:
        t.append(f"Anzahl: Schema für {' oder '.join(str(a) for a in s['anzahl'])} Wärmepumpe(n) statt {g['n']} – "
                 + ("Kaskade mit Kaskadenregler, jede Wärmepumpe an den Puffer" if g["n"] > 1 else "nur eine Wärmepumpe an den Puffer"))
    if not passt["ww"]:
        t.append("Warmwasser: " + WW_ERGAENZEN[ww])
    if not passt["system"]:
        t.append("Anlagenart: " + SYSTEM_ERGAENZEN[sys_])
    return t


def hinweise(e: dict, r: dict, lib: dict) -> list[str]:
    """Erklärende Hinweise zur Hydraulik-Auswahl (Speicher im MFH, fehlende Hydraulikzeichnung)."""
    if not r.get("gewaehlt") or not lib:
        return []
    m, t = e.get("mfh") or {}, []
    we = int(m.get("we") or 0) if m.get("art") == "mfh" else 0
    if ww_art(e, r) == "speicher" and we > 4:
        t.append(f"Ein Warmwasserspeicher an der Wärmepumpe reicht nur für kleine Mehrfamilienhäuser bis Leistungskennzahl NL 4 "
                 f"(etwa 4 Wohnungen). Für {we} WE besser „Zentral · FriWa“ oder „Dezentral · HIU“ wählen.")
    h = gewaehlt(e, r, lib)
    s = next((s for s in lib["schemata"] if h and s["id"] == h["id"]), None)
    if s and s.get("hps"):
        t.append("Wohnungsstationen mit E-Nacherwärmung (HPS): Das Heiznetz läuft nur mit ca. 45 °C, ein Durchlauferhitzer "
                 "(ca. 13 kW) in jeder Station heizt das Warmwasser nach. Die Wärmepumpe arbeitet dadurch effizienter, "
                 "dafür kommt Strom in den Wohnungen dazu.")
    if system_art(e, lib) != "mono" and e.get("zweiter") in ("oel", "pellet"):
        k = {"oel": "Ölkessel", "pellet": "Pelletkessel"}[e["zweiter"]]
        t.append(f"Zweiter Wärmeerzeuger {k}: Die Hydrauliken der Musterlösungen zeigen einen Gaskessel – den {k} an gleicher "
                 f"Stelle einbinden{' (mit Pufferspeicher für den Pelletkessel)' if e['zweiter'] == 'pellet' else ''}; "
                 "Kessel nach Herstellerunterlage planen.")
    if not any(x["passend"] for x in schemata(e, r, lib)):
        t.append("Für diese Kombination enthalten die Musterlösungen keine Hydraulikzeichnung (bei einigen Ordnern liegen dort nur "
                 "die Auslegungen bei). Vorgeschlagen ist die ähnlichste Hydraulik als Vorlage – was anzupassen ist, steht darunter.")
    return t


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
    """Gewählte Hydraulik (e["hydraulik"]["schema"]) oder automatisch die beste passende, sonst die ähnlichste."""
    liste = schemata(e, r, lib)
    wahl = (e.get("hydraulik") or {}).get("schema") or ""
    if wahl:
        x = next((x for x in liste if x["id"] == wahl), None)
        if x:
            return {**x, "manuell": True}
    x = next((x for x in liste if x["passend"]), liste[0] if liste else None)   # sonst die ähnlichste als Vorlage
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
    n["mfh"].update(art="mfh", we=L["we"] or n["mfh"]["we"], ww=L["ww"], zelle="", system=L["system"])
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
