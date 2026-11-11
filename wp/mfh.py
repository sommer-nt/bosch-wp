"""MFH-Musterlösungen – passende Lösung aus der Kostenübersicht zur Auslegung.

Gleiche Logik wie MFK.vorschlag()/rechneMitMuster() in index.html (Tests vergleichen beide über node).

Grundlage: Kostenübersicht MFH-Musterlösungen (Bestand 45 W/m², Neubau 30 W/m², je WE 80 m² und 3,5 Personen)
in daten/mfh_matrix.json.

Auswahl: Gebäudetyp (Neubau/Bestand) → Tabelle, Betriebsweise (GEG-Hybrid → Hybrid/bivalent, sonst monoenergetisch),
Warmwasserbereitung (zentral FriWa / dezentral HIU / ohne – DLE / Speicher) → Zeile, dann die kleinste Musterlösung mit
mindestens so vielen Wohneinheiten, deren Muster-Heizlast (WE · 80 m² · W/m²) die berechnete Heizlast QH abdeckt.
Die Wärmepumpe der Musterlösung wird mit dem Rechenkern (bewerte) gegen die eingegebene Anlage geprüft.
"""
from __future__ import annotations

from . import rechnen as R

WW_TEXT = {"friwa": "Zentral (Frischwasserstation)", "hiu": "Dezentral (HIU / Wohnungsstation)",
           "dle": "Ohne – dezentral elektrisch (DLE)", "speicher": "Speicher (max. NL 4)"}
MUSTER_SPEZ = {"bestand": 45, "neubau": 30}   # W/m² wie Kostenübersicht (mfh_matrix.json „annahmen“)


def eingaben_folgen(e: dict, k: str) -> None:
    """Abhängige Eingaben beim Mehrfamilienhaus setzen (wie mfhFolgen() in index.html).

    Mehrfamilienhaus/Gebäudetyp → Heizlast über die Fläche mit 45 W/m² (Bestand) bzw. 30 W/m² (Neubau);
    Warmwasserbereitung → Warmwasser über die WP (DLE: nein) und System (Speicher bzw. Frischwasserstation/HIU,
    beide mit Puffer); Wohneinheiten → Personen (3,5 je WE) und Wohnfläche (80 m² je WE) wie in den Musterlösungen.
    """
    m = e["mfh"]
    if k in ("mfh.art", "mfh.ww", "mfh.we", "gebaeude.typ", "auslegung"):
        m["zelle"] = ""
    if k in ("mfh.art", "mfh.ww", "gebaeude.typ", "auslegung") and e.get("hydraulik"):
        e["hydraulik"]["loesung"] = ""   # Bezug zur übernommenen Musterlösung lösen
    if k == "auslegung":
        m["system"] = ""
    if m.get("art") != "mfh":
        return
    if k in ("mfh.art", "mfh.ww"):
        e["tww"]["aktiv"] = m["ww"] != "dle"
        e["tww"]["system"] = "speicher" if m["ww"] == "speicher" else "friwa"
    if k in ("mfh.art", "gebaeude.typ"):   # Heizlast über die Fläche mit den Musterannahmen (änderbar)
        e["heizlast"]["methode"] = "flaeche"
        e["heizlast"]["spez_w_m2"] = MUSTER_SPEZ["neubau" if e["gebaeude"]["typ"] == "neubau" else "bestand"]
    if k in ("mfh.art", "mfh.we"):
        we = max(1, int(m.get("we") or 1))
        e["tww"]["personen"] = int(we * 3.5 + 0.5)   # kaufmännisch gerundet wie Math.round
        e["heizlast"]["flaeche_m2"] = we * 80
        e["heizlast"]["gebaeudeart"], e["heizlast"]["vbh"] = "MFH", 2000


def zeile(e: dict, matrix: dict) -> tuple[str, str, str, list]:
    m = e.get("mfh") or {}
    tab = "neubau" if e["gebaeude"]["typ"] == "neubau" else "bestand"
    sys_ = m.get("system") or ("hybrid" if e.get("auslegung") == "hybrid" else "mono")   # Anlagenart (übernommene Musterlösung)
    ww = m.get("ww") or "friwa"
    zellen = [z for z in matrix["zellen"] if z["tabelle"] == tab and z["system"] == sys_ and z["ww"] == ww]
    return tab, sys_, ww, sorted(zellen, key=lambda z: (z["we"], z["kw"]))


def muster_heizlast(z: dict, matrix: dict) -> float:
    a = matrix["annahmen"][z["tabelle"]]
    return z["we"] * a["flaeche_we"] * a["spez_w_m2"] / 1000


def vorschlag(e: dict, r: dict, matrix: dict, daten: dict, katalog: dict | None = None) -> dict | None:
    """Passende Musterlösung(en) zur Eingabe; None, wenn kein Mehrfamilienhaus."""
    m = e.get("mfh") or {}
    if m.get("art") != "mfh":
        return None
    we = max(1, int(m.get("we") or 1))
    tab, sys_, ww, zellen = zeile(e, matrix)
    out = {"tabelle": tab, "system": sys_, "ww": ww, "we": we, "qh": r["qh"], "zellen": zellen, "auswahl": [],
           "ausserhalb": False, "manuell": False}
    if not zellen:
        return out
    gewaehlt = None
    if m.get("zelle"):
        gewaehlt = next((z for z in zellen if z["id"] == m["zelle"]), None)
        out["manuell"] = gewaehlt is not None
    if gewaehlt is None:
        gewaehlt = next((z for z in zellen if z["we"] >= we and muster_heizlast(z, matrix) >= r["qh"] - 1e-9), None)
    if gewaehlt is None:
        gewaehlt, out["ausserhalb"] = zellen[-1], True
    for z in zellen:
        if z["we"] != gewaehlt["we"]:
            continue
        g = next((x for x in daten["geraete"] if x["id"] == z["geraet"]), None)
        b = R.bewerte(g, z["n"], r["vl"], r, daten, katalog) if g else None
        out["auswahl"].append({"zelle": z, "muster_qh": muster_heizlast(z, matrix), "pruefung": b})
    return out


def pruef_text(a: dict, r: dict) -> str:
    """Prüfung der Musterlösungs-Wärmepumpe mit den eigenen Eingaben (Text wie mfhPruefText() in index.html)."""
    from . import texte as T
    z, b = a["zelle"], a["pruefung"]
    name = (f"{z['n']} × " if z["n"] > 1 else "") + z["geraet"]
    if not b:
        return f"{name}: keine Leistungsdaten."
    if not b["moeglich"]:
        return f"✗ {name}: {b['grund']}"
    krit = {"monovalent": "monovalent", "monoenergetisch": "monoenergetisch", "hybrid": "GEG-Hybrid"}.get(r["kriterium"], r["kriterium"])
    return (("✓ " if b["ok"] else "✗ ") + f"{name} {'erfüllt' if b['ok'] else 'erfüllt nicht'} das Kriterium {krit} für diese Anlage"
            + f" · Bivalenzpunkt {T.biv_text(b)} · Abdeckung bei θe {T.f(b['abdeckung'] * 100, 0)} %" + ("" if b["ok"] else f" – {b['grund']}"))


def rechne(e: dict, daten: dict, katalog: dict, matrix: dict) -> dict:
    """Auslegung mit MFH-Musterlösung (wie rechneMitMuster() in index.html).

    Mehrfamilienhaus und „Beste Lösung“: Wärmepumpe der Musterlösung übernehmen, wenn sie die Prüfung besteht
    (r["mfh_wp"] = True). Von Hand gewählte Wärmepumpen bleiben unverändert.
    """
    import copy
    r = R.rechne(e, daten, katalog)
    v = vorschlag(e, r, matrix, daten, katalog)
    r["mfh"], r["mfh_wp"] = v, False
    if v and not e["auswahl"].get("geraet"):
        a = next((a for a in v["auswahl"] if a["pruefung"] and a["pruefung"]["ok"]), None)
        if a:
            e2 = copy.deepcopy(e)
            e2["auswahl"].update(geraet=a["zelle"]["geraet"], anzahl=a["zelle"]["n"])
            r = R.rechne(e2, daten, katalog)
            r["mfh"], r["mfh_wp"] = v, True
    return r
