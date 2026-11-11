"""MFH-Musterbestellvorschläge – Auswahl zur Auslegung, Bestellvorschlag und GAEB-Export (D83).

Gleiche Logik wie mfhVorschlag()/mfhPositionen()/mfhD83() in index.html (Tests vergleichen beide über node).

Grundlage: Kostenübersicht MFH-Musterbestellvorschläge (Bestand 45 W/m², Neubau 30 W/m², je WE 80 m² und 3,5 Personen)
in daten/mfh_matrix.json und die GAEB-Bestellvorschläge in daten/mfh_vorlagen.json (tools/mfh_import.py).

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
ART_TEXT = {"G": "Grundposition", "A": "Alternative", "N": ""}


def eingaben_folgen(e: dict, k: str) -> None:
    """Abhängige Eingaben beim Mehrfamilienhaus setzen (wie mfhFolgen() in index.html).

    Mehrfamilienhaus/Gebäudetyp → Heizlast über die Fläche mit 45 W/m² (Bestand) bzw. 30 W/m² (Neubau);
    Warmwasserbereitung → Warmwasser über die WP (DLE: nein) und System (Speicher bzw. Frischwasserstation/HIU,
    beide mit Puffer); Wohneinheiten → Personen (3,5 je WE) und Wohnfläche (80 m² je WE) wie in den Musterlösungen.
    """
    m = e["mfh"]
    if k in ("mfh.art", "mfh.ww", "mfh.we", "gebaeude.typ", "auslegung"):
        m["zelle"] = ""
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
    sys_ = "hybrid" if e.get("auslegung") == "hybrid" else "mono"
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
        out["auswahl"].append({"zelle": z, "muster_qh": muster_heizlast(z, matrix), "pruefung": b,
                               "positionen": bool(z.get("vorlage"))})
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


def positionen(vorlage: dict, langtexte: dict, we: int | None = None) -> list[dict]:
    """Positionen der GAEB-Vorlage als flache Liste; Durchlauferhitzer je Wohneinheit auf die eingegebenen WE angepasst."""
    we_muster = muster_we(vorlage)
    out = []
    for g in vorlage["gruppen"]:
        for p in g["elemente"]:
            if "oz" not in p:
                continue
            menge = p["menge"]
            if we and we_muster and menge == we_muster and "TR5001" in " ".join(p["kurz"]):
                menge = float(we)
            bedarf = p["art"][1] != "N"
            out.append({"gruppe": g["titel"], "gnr": g["nr"], "oz": p["oz"], "art": p["art"][0], "bedarf": bedarf,
                        "wahl": p["wahl"], "menge": menge, "menge_muster": p["menge"], "einheit": p["einheit"],
                        "artnr": p["artnr"], "text": " – ".join(p["kurz"]), "ep": p["ep"],
                        "gp": round(menge * p["ep"], 2) if p["ep"] is not None else None,
                        "summe": p["art"][0] in ("N", "G") and not bedarf})
    return out


def muster_we(vorlage: dict) -> int | None:
    for g in vorlage["gruppen"]:
        for e in g["elemente"]:
            for s in e.get("text", []):
                if "Wohneinheiten (WE):" in s:
                    return int("".join(c for c in s.split(":")[1] if c.isdigit()) or 0) or None
    return None


def summe(pos: list[dict]) -> float:
    return round(sum(p["gp"] or 0 for p in pos if p["summe"]), 2)


def art_text(p: dict) -> str:
    t = ART_TEXT.get(p["art"], "")
    return (t + " · " if t else "") + "bei Bedarf" if p["bedarf"] else t


# ------------------------------------------------------------------------------------------------ GAEB DA 1990 (D83)
def _zeile(sa: str, inhalt: str, nr: int) -> str:
    return (sa + inhalt)[:74].ljust(74) + f"{nr:06d}"


def d83_text(vorlage: dict, langtexte: dict, we: int | None = None) -> str:
    """Bestellvorschlag als GAEB-DA-1990-Datei (Satzaufbau wie die Bosch-Musterbestellvorschläge)."""
    pos = {(p["gnr"], p["oz"]): p for p in positionen(vorlage, langtexte, we)}
    z = []
    z.append(("00", f"        83LVergabe-Nr. AG {vorlage['nr'][:8]:<8}{'':26}11PPPP00090 "))
    z.append(("01", f"{vorlage['titel']:<40}{vorlage['datum']}"))
    z += [("02", ""), ("03", ""), ("08", "EUR   EUR")]
    for g in vorlage["gruppen"]:
        z.append(("11", f"{g['nr']}       N"))
        z.append(("12", g["titel"]))
        for e in g["elemente"]:
            if "oz" not in e:
                z.append(("20", ""))
                z += [("26", s) for s in e["text"]]
                continue
            p = pos[(g["nr"], e["oz"])]
            z.append(("21", f"{e['oz']}   {e['art']}{e['wahl']:<4}     {round(p['menge'] * 1000):011d}{e['einheit']}"))
            if e["ep"] is not None:
                z.append(("23", f"{e['oz']}    {round(e['ep'] * 100):010d}  {round(p['gp'] * 100):012d}"))
            if e["tt"]:
                z.append(("25", f"Typ-Teile-Nr.: {e['artnr']}"))
            z += [("25", s) for s in e["kurz"]]
            z += [("26", s) for s in (langtexte.get(e["lang"]) or [])]
        z.append(("31", g["nr"]))
    z.append(("99", ""))
    return "\r\n".join(_zeile(sa, t, i + 1) for i, (sa, t) in enumerate(z))


def d83_bytes(vorlage: dict, langtexte: dict, we: int | None = None) -> bytes:
    return d83_text(vorlage, langtexte, we).encode("cp850", errors="replace")


def csv_text(pos: list[dict]) -> str:
    kopf = "Pos;Gruppe;Menge;Einheit;Bestell-Nr.;Bezeichnung;Art;EP;GP;in Summe"
    zeilen = [kopf] + [";".join([p["oz"], p["gruppe"], f"{p['menge']:g}".replace(".", ","), p["einheit"], p["artnr"],
                                 p["text"].replace(";", ","), art_text(p),
                                 "" if p["ep"] is None else f"{p['ep']:.2f}".replace(".", ","),
                                 "" if p["gp"] is None else f"{p['gp']:.2f}".replace(".", ","),
                                 "ja" if p["summe"] else "nein"]) for p in pos]
    return "\r\n".join(zeilen) + "\r\n"


def dokumentation(e: dict, r: dict, matrix: dict, hdb: dict, ie: dict | None) -> dict | None:
    """Prüfprotokoll zum Bestellvorschlag (wie mfhDokumentation() in index.html).

    Prüft Auslegung, Übereinstimmung mit der Musterlösung, Heizlast/WE im Musterbereich, GAEB-Bestellvorschlag und das
    passende Bosch-Hydraulikschema (Anzahl Wärmepumpen, Warmwasser, Hybrid). valide = keine Warnung, kein Fehler.
    """
    from . import hydraulik as HY
    from .schema import zahl

    def z(x, d=1):
        return zahl(x, d)

    v, g = r.get("mfh"), r.get("gewaehlt")
    if not v or not v["auswahl"]:
        return None
    a = next((x for x in v["auswahl"] if g and x["zelle"]["geraet"] == g["geraet"] and x["zelle"]["n"] == g["n"]), v["auswahl"][0])
    zl = a["zelle"]
    p = []
    name = (f"{zl['n']} × " if zl["n"] > 1 else "") + zl["geraet"]
    p.append({"text": f"Musterlösung {zl['we']} WE / {zl['kw']} kW: {' · '.join(zl['komponenten'])}", "status": ""})
    krit = {"monovalent": "monovalent", "monoenergetisch": "monoenergetisch", "hybrid": "GEG-Hybrid"}[r["kriterium"]]
    if g and g["moeglich"] and g["ok"]:
        p.append({"text": f"Auslegung {krit} erfüllt: {(str(g['n']) + ' × ') if g['n'] > 1 else ''}{g['geraet']}, "
                          f"Bivalenzpunkt {T_biv(g)}", "status": "ok"})
    else:
        p.append({"text": f"Auslegung {krit} nicht erfüllt – Wärmepumpe prüfen.", "status": "bad"})
    if g and g["geraet"] == zl["geraet"] and g["n"] == zl["n"]:
        p.append({"text": f"Gewählte Wärmepumpe entspricht der Musterlösung ({name}).", "status": "ok"})
    else:
        p.append({"text": f"Gewählte Wärmepumpe weicht von der Musterlösung ab (Muster: {name}) – Bestellvorschlag anpassen.", "status": "warn"})
    if v["ausserhalb"]:
        p.append({"text": "Heizlast bzw. Wohneinheiten über den Musterlösungen – Anlage individuell planen.", "status": "bad"})
    else:
        ok = v["qh"] <= a["muster_qh"] + 1e-9 and v["we"] <= zl["we"]
        p.append({"text": f"Heizlast {z(v['qh'])} kW / {v['we']} WE im Musterbereich ({z(a['muster_qh'])} kW / {zl['we']} WE).",
                  "status": "ok" if ok else "warn"})
    vo = matrix["vorlagen"].get(zl.get("vorlage") or "")
    if vo:
        n_pos = sum(1 for gr in vo["gruppen"] for x in gr["elemente"] if "oz" in x)
        p.append({"text": f"GAEB-Bestellvorschlag {vo['nr']} vom {vo['datum']} ({n_pos} Positionen).", "status": "ok"})
    else:
        p.append({"text": "Kein GAEB-Bestellvorschlag zu dieser Musterlösung – nur Komponentenliste; Bestellung im SysCon erstellen.",
                  "status": "warn"})
    s = schema_zur_loesung(e, r, hdb, ie, zl) if g else None
    if s and all(s["passt"].values()):
        p.append({"text": f"Hydraulikschema {s['nr']} „{s['titel']}“ (Stand {s['stand']}"
                          + (", aus den Unterlagen der Musterlösung" if zl.get("hydraulik") == s["nr"] else "")
                          + ") passt: Anzahl Wärmepumpen, Warmwasser und Betriebsweise.", "status": "ok"})
    elif s:
        fehlt = [t for k, t in (("anzahl", "Anzahl Wärmepumpen"), ("ww", "Warmwasser"), ("hybrid", "Betriebsweise")) if not s["passt"][k]]
        p.append({"text": f"Hydraulikschema {s['nr']} „{s['titel']}“ passt nur teilweise ({', '.join(fehlt)} abweichend) – "
                          "Sonderfall, Hydraulik prüfen.", "status": "warn"})
    else:
        p.append({"text": "Kein passendes Schema in der Hydraulikdatenbank – Sonderfall, Hydraulik individuell planen.", "status": "warn"})
    p.append({"text": f"Preisstand: {('Bestellvorschlag ' + vo['datum'] + ', ') if vo else ''}Kostenübersicht {matrix['stand']}.", "status": ""})
    return {"pruefungen": p, "schema": s, "vorlage": vo["nr"] if vo else None,
            "valide": not any(x["status"] in ("warn", "bad") for x in p)}


def schema_zur_loesung(e: dict, r: dict, hdb: dict, ie: dict | None, zl: dict) -> dict | None:
    """Hydraulikschema zur Musterlösung: aus den Unterlagen der Lösung (zelle „hydraulik“), sonst das passendste aus der
    Hydraulikdatenbank (mit den Komponenten der Lösung als Kennworten)."""
    from . import hydraulik as HY
    alle = HY.schemata(e, r, hdb, ie, 999, HY.kennworte(zl["komponenten"]))
    if zl.get("hydraulik"):
        fest = next((x for x in alle if x["nr"] == zl["hydraulik"]), None)
        if fest:
            return fest
    return alle[0] if alle else None


def T_biv(g: dict) -> str:
    """Bivalenzpunkt als Text – Rundung wie schemaZahl() (gleich in index.html)."""
    from .schema import zahl
    if not g or not g.get("moeglich"):
        return "–"
    if g["bivalenz_art"] == "nicht":
        return "nicht erreicht"
    return ("≤ " if g["bivalenz_art"] == "unter" else "") + zahl(g["bivalenz"], 1).replace("-", "−") + " °C"
