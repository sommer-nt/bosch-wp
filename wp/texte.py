"""Texte und Formatierung für App und PDF (wie die Anzeige in index.html)."""
from __future__ import annotations

from . import rechnen as R

BETRIEBSWEISE = {"monovalent": "monovalent", "monoenergetisch": "monoenergetisch", "hybrid": "GEG-Hybrid"}
VERTEILUNG_VL = {"fbh": 35, "hk": 55, "beides": 55, "konvektor": 45}
VERTEILUNG_TEXT = {"fbh": "Fußbodenheizung", "hk": "Heizkörper", "beides": "Fußbodenheizung + Heizkörper",
                   "konvektor": "Konvektoren"}
SPEZ = {"neubau": [(22, "KfW-Effizienzhaus 40+ (20–25 W/m²)"), (30, "KfW-Effizienzhaus 55 (30 W/m²)"),
                   (35, "KfW-Effizienzhaus 85 (35 W/m²)"), (38, "EnEV 2009 / GEG (35–40 W/m²)"), (15, "Passivhaus (15 W/m²)")],
        "sanierung": [(100, "Bestand WSchVO 1982 (80–120 W/m²)"), (70, "Bestand WSchVO 1995 (60–80 W/m²)"),
                      (50, "EnEV 2002 (40–60 W/m²)"), (45, "MFH-Musterlösung Bestand (45 W/m²)"),
                      (40, "KfW-Effizienzhaus 100 (40 W/m²)"), (38, "EnEV 2009 (35–40 W/m²)")]}
HK_TYP = {"hk": "Heizkörper", "fbh": "Fußbodenheizung", "konvektor": "Konvektoren"}
HK_MAX = 4


def heizkreis_liste(e: dict) -> list[dict]:
    """Heizkreise wie index.html: der Kreis mit dem höchsten Vorlauf ungemischt, die anderen gemischt."""
    hk = e.get("heizkreise") or [{"typ": e.get("verteilung") if e.get("verteilung") in ("fbh", "konvektor") else "hk"}]
    vmax = max(VERTEILUNG_VL.get(h["typ"], 55) for h in hk)
    return [{"nr": i + 1, "typ": h["typ"], "vl": VERTEILUNG_VL.get(h["typ"], 55),
             "gemischt": VERTEILUNG_VL.get(h["typ"], 55) < vmax} for i, h in enumerate(hk)]


def heizkreis_text(e: dict) -> str:
    return " + ".join(HK_TYP[h["typ"]] + (" (gem.)" if h["gemischt"] else "") for h in heizkreis_liste(e))


KRITERIUM = {"monovalent": "QGES bei θe (monovalent)",
             "monoenergetisch": "0,7 · QGES bei A-7 (Außenluft −7 °C; monoenergetisch, ca. 98 % Deckung)",
             "hybrid": "0,3 · QH bei A-7 (Außenluft −7 °C; GEG § 71 Hybrid)"}


def f(x, d: int = 1) -> str:
    if x is None:
        return "–"
    s = f"{x:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return s


def ft(x) -> str:
    return "–" if x is None else f(x, 1).replace("-", "−")


def euro(x) -> str:
    return "–" if x is None else f(x, 0) + " €"


def euro2(x) -> str:
    return "–" if x is None else f(x, 2) + " €"


def biv_text(g: dict | None) -> str:
    if not g or not g.get("moeglich"):
        return "–"
    if g["bivalenz_art"] == "nicht":
        return "nicht erreicht"
    if g["bivalenz_art"] == "unter":
        return "≤ " + ft(g["bivalenz"]) + " °C"
    return ft(g["bivalenz"]) + " °C"


def _regelungen(katalog: dict, g: dict) -> list[dict]:
    """Inneneinheiten/Regelungen der Baureihe; bei einer Kaskade nur der Kaskadenregler (HPC 301 C, HPC800i C)."""
    liste = [i for i in katalog["inneneinheiten"].get(g["serie"], []) if not i.get("ab_anzahl") or g["n"] >= i["ab_anzahl"]]
    regler = [i for i in liste if i.get("ab_anzahl")]
    return regler or liste


def inneneinheit(e: dict, r: dict, katalog: dict) -> dict | None:
    g = r.get("gewaehlt")
    if not g:
        return None
    liste = _regelungen(katalog, g)
    return next((i for i in liste if i["typ"] == e["auswahl"].get("inneneinheit")), liste[0] if liste else None)


def inneneinheiten(r: dict, katalog: dict) -> list[dict]:
    g = r.get("gewaehlt")
    if not g:
        return []
    return _regelungen(katalog, g)


def experten_abweichungen(e: dict) -> list[str]:
    """Experteneinstellungen abweichend vom Standard (wirken auch bei ausgeblendetem Expertenmodus)."""
    a, t = [], e["tww"]
    if e.get("serien"):
        a.append("Baureihen-Filter")
    if t.get("bezug", "liter") != "liter":
        a.append("Warmwasser nach DIN V 18599" + (" (je m²)" if t.get("bezug") == "flaeche" else ""))
    if t.get("methode", "auto") != "auto":
        a.append("Warmwasser-Zuschlag fest")
    if int(e.get("sperrzeit_h") or 0):
        a.append(f"Sperrzeit {int(e['sperrzeit_h'])} h")
    if e.get("auslegung") != ("monovalent" if e.get("waermequelle") == "sole" else "monoenergetisch"):
        a.append(f"Betriebsweise {e.get('auslegung')}")
    if e["heizlast"]["methode"] == "huelle":
        a.append("Heizlast über Gebäudehülle")
    return a


def experten_zuruecksetzen(e: dict) -> None:
    e["serien"] = []
    e["tww"]["bezug"], e["tww"]["methode"], e["sperrzeit_h"] = "liter", "auto", 0
    e["auslegung"] = "monovalent" if e.get("waermequelle") == "sole" else "monoenergetisch"
    if e["heizlast"]["methode"] == "huelle":
        e["heizlast"]["methode"] = "vorgabe"


def meldungen(e: dict, r: dict, katalog: dict) -> list[str]:
    m = list(r["hinweise"])
    if r["tww"]["aktiv"] and e["tww"].get("bezug") == "flaeche" and not float(e["tww"].get("flaeche_m2") or 0) > 0:
        m.append("Warmwasser flächenbezogen, aber keine Nutzfläche ANGF eingegeben – Warmwasserbedarf ist 0 (Expertenmodus).")
    g = r.get("gewaehlt")
    if g and not g["moeglich"]:
        m.append(f"{g['geraet']}: {g['grund']}.")
    elif g and not g["ok"]:
        m.append(f"{g['geraet']}{' (' + str(g['n']) + '×)' if g['n'] > 1 else ''} erfüllt das Kriterium nicht: {g['grund']}.")
    if g and g.get("ueberdimensioniert"):
        m.append("Gewählte Wärmepumpe ist deutlich überdimensioniert (Abdeckung bei θe über 150 %) – Taktverhalten prüfen.")
    tw = r["tww"]
    if g and g["moeglich"] and r["nat"] < g["t_daten_min"]:
        m.append(f"Leistungsdaten erst ab {ft(g['t_daten_min'])} °C – darunter wird der letzte Wert angesetzt "
                 "(Kurve im Diagramm nicht verlängert).")
    if g and g["moeglich"] and tw["aktiv"] and not g["vl_tww_ok"]:
        m.append(f"Warmwasser: {'Puffer' if tw['system'] == 'friwa' else 'Speicher'} {f(tw['t_speicher'], 0)} °C braucht ca. "
                 f"{f(tw['vl_tww'], 0)} °C Vorlauf – über {f(g['vl_max_geraet'], 0)} °C des Geräts, Nacherwärmung (E-Heizer) einplanen.")
    if tw["aktiv"] and tw["grossanlage"]:
        m.append(f"Warmwasser-Tagesbedarf ca. {f(tw['volumen_tag_l'], 0)} l: voraussichtlich Großanlage nach DVGW W 551 – "
                 "Speicheraustritt ≥ 60 °C (Nacherwärmung) oder Frischwasserstation einplanen.")
    ie = inneneinheit(e, r, katalog)
    if ie and ie.get("vl_max") and r["vl"] > ie["vl_max"]:
        m.append(f"{ie['typ']}: max. Vorlauftemperatur {ie['vl_max']} °C.")
    if r["waermequelle"] == "sole" and r["kriterium"] != "monovalent":
        m.append("Sole/Wasser-Wärmepumpen werden üblicherweise monovalent ausgelegt (Betriebsweise im Expertenmodus).")
    if not r["empfehlung"] and r["qges"] > 0:
        m.append("Keine passende Wärmepumpe in den gewählten Baureihen – Kaskade, Vorlauf oder Betriebsweise prüfen.")
    if r["heizlast"]["methode"] != "vorgabe":
        m.append("Überschlägige Heizlast – vor Ausführung ist eine Heizlastberechnung nach DIN EN 12831 erforderlich.")
    return m


def herleitung(e: dict, r: dict) -> list[tuple[str, str, str]]:
    """Zeilen (Größe, Formel, Wert) wie „Herleitung Heizlast“ in index.html."""
    h, hl, t = r["heizlast"], e["heizlast"], e["tww"]
    z: list[tuple[str, str, str]] = []
    if h["methode"] == "vorgabe":
        z.append(("Heizlast QH (Vorgabe)", "z. B. aus Heizlastberechnung DIN EN 12831", f(r["qh"], 2) + " kW"))
    elif h["methode"] == "flaeche":
        z.append(("Überschlägige Heizlast QH", f"A · q = {f(hl['flaeche_m2'], 0)} m² · {f(hl['spez_w_m2'], 0)} W/m²", f(r["qh"], 2) + " kW"))
    elif h["methode"] == "huelle":
        z.append(("Transmission QT", f"(θi − θe) · A · H'T = ({f(r['innen'], 0)} − {ft(r['nat'])}) · {f(hl['huell_a_m2'], 0)} · {f(hl['ht'], 2)}",
                  f(h["transmission_kw"], 2) + " kW"))
        z.append(("Lüftung QL", f"0,5 · n · V · 0,36 · (θi − θe) = 0,5 · {f(hl['luftwechsel'], 1)} · {f(hl['volumen_m3'], 0)} · 0,36 · {f(r['innen'] - r['nat'], 1)}",
                  f(h["lueftung_kw"], 2) + " kW"))
        z.append(("Heizlast QH", "QT + QL", f(r["qh"], 2) + " kW"))
    else:
        einheit = R.HEIZWERT.get(hl.get("energietraeger"), R.HEIZWERT["gas"])[1]
        z.append(("Jahres-Endenergie Eg,in", f"Verbrauch · Hu = {f(hl['menge'], 0)} {einheit} · {f(hl['heizwert'], 2)} kWh/{einheit}", f(h["eg_kwh"], 0) + " kWh/a"))
        z.append(("Trinkwarmwasser Ew,g,in", tww_formel(e, r) if hl.get("ww_im_verbrauch") else "nicht im Verbrauch enthalten", f(h["ew_kwh"], 0) + " kWh/a"))
        z.append(("Heizung Ehg,in", "Eg,in − Ew,g,in", f(h["ehg_kwh"], 0) + " kWh/a"))
        z.append(("Leistung Wärmeerzeuger Øh,g = QH", f"Ehg,in · η / th = {f(h['ehg_kwh'], 0)} · {f(h['eta'], 2)} / {f(h['th'], 0)} h/a", f(r["qh"], 2) + " kW"))
        z.append(("Øh,in (Heizung + TWW, Excel-Blatt)", f"Øh,g + Ew,g,in / (td · 365), td = {f(t['td'], 0)} h/d", f(h["oh_in_kw"], 2) + " kW"))
    tw = r["tww"]
    if not tw["aktiv"]:
        z.append(("Warmwasserzuschlag QTW", "Warmwasser nicht über die WP", "0,00 kW"))
    else:
        liter = t.get("bezug", "liter") == "liter"
        if h["methode"] != "verbrauch":
            if liter:
                z.append(("Warmwasser je Person Qw,b", f"V · c · (45 °C − ϑKW) = {f(t['liter_p'], 0)} l · 1,163 Wh/(l·K) · "
                          f"{f(45 - (t.get('t_kw') or 10), 0)} K", f(tw["qwb_person"], 2) + " kWh/(P·d)"))
            z.append(("Trinkwarmwasser Ew,g,in", tww_formel(e, r), f(r["tww_kwh"], 0) + " kWh/a"))
        if tw["methode"] == "nachheizzeit":
            z.append(("Warmwasserzuschlag QTW", f"Ew,g,in / (td · 365) = {f(r['tww_kwh'], 0)} / ({f(t['td'], 0)} · 365)", f(r["qtw"], 2) + " kW"))
        else:
            zus = f" (aus {f(t['liter_p'], 0)} l/(P·d))" if t.get("methode", "auto") == "auto" and liter else ""
            z.append(("Warmwasserzuschlag QTW", f"np · Lastprofil = {f(t['personen'], 0)} P · {f(tw['kw_person'], 2)} kW/P{zus}",
                      f(r["qtw"], 2) + " kW"))
    sp = int(e.get("sperrzeit_h") or 0)
    z.append(("Sperrzeitzuschlag QSperr", f"(QH + QTW) · {({2: 5, 4: 10, 6: 15}).get(sp, 0)} % ({sp} h/d)" if sp else "keine Sperrzeit",
              f(r["qsperr"], 2) + " kW"))
    z.append(("Gesamtheizlast QGES", "QH + QTW + QSperr", f(r["qges"], 2) + " kW"))
    z.append(("Mindestleistung Wärmepumpe", KRITERIUM[r["kriterium"]], f(r["mindestleistung"], 2) + " kW"))
    return z


def tww_formel(e: dict, r: dict) -> str:
    t = e["tww"]
    if t.get("bezug") == "flaeche":
        return f"Qw,b · ANGF · 1,1 · 365 = {f(t['qwb'], 4)} · {f(t['flaeche_m2'], 0)} · 1,1 · 365"
    return f"Qw,b · np · 365 = {f(r['tww']['qwb_person'], 2)} · {f(t['personen'], 0)} · 365"


def eheizer_zeilen(r: dict) -> list[dict]:
    """E-Heizer je Baugröße wie index.html (Text für Tabelle)."""
    out = []
    for x in r.get("eheizer") or []:
        if x["status"] == "E-Heizer":
            bew = "E-Heizer unterstützt" + (f" (max. {f(x['eheizer_max_kw'], 0)} kW)" if x.get("eheizer_max_kw") is not None else " (bauseits)")
        else:
            bew = x["status"]
        out.append({**x, "text_q": "–" if x["q_nat"] is None else f(x["q_nat"], 2) + " kW",
                    "text_eh": "–" if x["eheizer_kw"] is None else f(x["eheizer_kw"], 1) + " kW",
                    "text_w": "–" if x["eheizer_kw"] is None else f(round(x["eheizer_kw"] * 10) * 100, 0) + " W",
                    "bewertung": bew})
    return out


def min_hinweis(r: dict) -> str:
    """Erläuterung der Mindestleistung (Modulationsgrenze) wie minHinweis() in index.html."""
    k, g = r.get("kennlinien"), r.get("gewaehlt")
    if not k or not g:
        return ""
    if not k["min"]:
        return "Für diese Baureihe liegen keine Mindestleistungen vor – keine Taktgrenze."
    v = [x for x in k["min"] if x is not None]
    sprung = max((abs(b - a) for a, b in zip(v, v[1:])), default=0.0)
    if r["waermequelle"] == "sole":
        quelle = "Mindestleistung laut Katalog (Modulationsbereich" + (", bei Supraeco T 1. Verdichter" if g["serie"] == "SupraecoT" else "") + ")"
    else:
        quelle = "Mindestleistung je Gerät laut Excel-Werkzeug" + (" (gilt für ein Gerät der Kaskade)" if g["n"] > 1 else "")
    if sprung > 0.5:
        quelle += f" · Stufen bis {f(sprung, 1)} kW stammen aus den Herstellerdaten (Temperaturbänder), sie werden nicht geglättet."
    return quelle


def pakete_fuer(r: dict, ie: dict | None, pk: dict) -> list[dict]:
    """Systempakete zur gewählten Wärmepumpe (Einzelgerät): passende Inneneinheit zuerst, dann nach UVP.

    Gleiche Auswahl wie paketeFuer() in index.html.
    """
    g = r.get("gewaehlt")
    if not g or g["n"] > 1:
        return []
    typ = ie["typ"] if ie else None
    liste = [dict(p, passt=bool(typ and p.get("inneneinheit") == typ)) for p in pk["pakete"] if p["geraet"] == g["geraet"]]
    return sorted(liste, key=lambda p: (not p["passt"], p["uvp"], p["paket"]))


def zubehoer_fuer(r: dict, pk: dict) -> list[dict]:
    """Empfohlene Zubehörpakete und Zubehöre der Baureihe (aus dem Paketteil des Katalogs)."""
    g = r.get("gewaehlt")
    return pk["zubehoer"].get(g["serie"], []) if g else []


def anbindung(e: dict, r: dict) -> list[tuple[str, str, str]]:
    """Kacheln (Titel, Wert, Zusatz) „Warmwasser & Anbindung“ wie index.html."""
    tw, ltg, er, k = r["tww"], r.get("leitung"), r.get("erdreich"), []
    if tw["aktiv"]:
        k.append(("Warmwasser je Tag", f(tw["q_tag_kwh"], 1) + " kWh/d",
                  f"{f(tw['volumen_tag_l'], 0)} l bei {f(tw['t_speicher'], 0)} °C · " +
                  (f(tw["qwb_person"], 2) + " kWh/(P·d)" if tw["qwb_person"] is not None else "flächenbezogen")))
        k.append(("Frischwasserstation" if tw["system"] == "friwa" else "Speichersystem", f(tw["t_speicher"], 0) + " °C",
                  f"{'Puffer' if tw['system'] == 'friwa' else 'Speicher'} für {f(tw['t_zapf'], 0)} °C Zapftemperatur · "
                  f"Ladevorlauf ≈ {f(tw['vl_tww'], 0)} °C"))
        k.append(("Zuschlag Warmwasser QTW", f(r["qtw"], 2) + " kW",
                  f"Ew,g,in / (td · 365), td = {f(e['tww']['td'], 0)} h" if tw["methode"] == "nachheizzeit"
                  else f"{f(e['tww']['personen'], 0)} P · {f(tw['kw_person'], 2)} kW/P"))
    if ltg:
        k.append(("Verbindungsleitung", ltg["rohr"],
                  f"{f(ltg['volumenstrom_m3h'], 2)} m³/h (Δϑ {f(ltg['spreizung'], 0)} K) · v {f(ltg['v_ms'], 2)} m/s · "
                  f"R {f(ltg['r_pa_m'], 0)} Pa/m · Δp ≈ {f(ltg['dp_kpa'], 1)} kPa für 2 × {f(ltg['laenge_m'], 0)} m"))
    if er:
        k.append(("Erdwärmesonde (Richtwert)", f(er["sondenlaenge_m"], 0) + " m",
                  f"Entzug {f(er['q_entzug_kw'], 2)} kW (COP B0/W35 {f(er['cop'], 2)}) bei {f(er['entzug_w_m'], 0)} W/m – "
                  "Bemessung nach VDI 4640 / Geologie"))
    return k


HAFTUNG = ("Die Schnellauslegung dient der Produktvor- und Systemauswahl und ersetzt nicht die fachtechnische Planung. Sie "
           "berücksichtigt nicht die individuellen Eigenschaften eines Bauvorhabens. Leistungsdaten nach Herstellerangaben "
           "(Excel-Werkzeug „WP-Auslegung_S“, Gesamtkatalog März 2026); Zwischenwerte linear interpoliert. Die Heizlast ist "
           "nach der im Land gültigen Norm (DIN EN 12831) zu berechnen; eine Auslegung über Vorjahresverbräuche oder "
           "Flächenkennwerte ist nur überschlägig und kann zu Unter- oder Überdimensionierung führen. Der Deckungsanteil "
           "nach VDI 4650 gilt für parallelen Betrieb. Energiewerte sind Näherungen ohne Gewähr; Schallimmissionen sind "
           "gesondert nachzuweisen (TA Lärm). Vor Ausführung sind Planung und Angaben durch den ausführenden Fachbetrieb "
           "oder ein Planungsbüro auf Plausibilität, Aktualität, Richtigkeit und Vollständigkeit zu prüfen. "
           "Aufstellbedingungen, Einsatzgrenzen, R290-Sicherheitsbereiche und die elektrischen Anschlussbedingungen des "
           "Netzbetreibers sind zu beachten.")


# ------------------------------------------------------------------------------------------------ Erklärungen
# Glossar: kurze Erklärungen der Fachbegriffe (gleicher Text wie GLOSSAR in index.html, <script id="texte">)
GLOSSAR = {
    "qges": "Gesamtheizlast QGES: Leistung, die das Gebäude bei der Norm-Außentemperatur braucht – Heizung (QH) plus "
            "Zuschlag für Warmwasser (QTW) und Sperrzeiten des Energieversorgers (QSperr).",
    "mindest": "Mindestleistung der Wärmepumpe bei A-7 (Außenluft −7 °C): monoenergetisch 70 % von QGES (Heizstab "
               "übernimmt den Rest an wenigen kalten Tagen), monovalent 100 % bei θe, GEG-Hybrid 30 % von QH.",
    "biv": "Bivalenzpunkt: Außentemperatur, bis zu der die Wärmepumpe den Bedarf allein deckt. Darunter hilft der "
           "Heizstab (monoenergetisch) bzw. der zweite Wärmeerzeuger. Je tiefer, desto besser.",
    "qnat": "Leistung bei θe: Heizleistung der Wärmepumpe bei der Norm-Außentemperatur und dem gewählten Vorlauf; "
            "Abdeckung = Anteil an QGES.",
    "heizstab": "Heizstab bei θe: elektrische Zusatzleistung am kältesten Auslegungstag (QGES minus WP-Leistung). "
                "Der E-Heizer der Inneneinheit liefert bis 9 kW.",
    "deckung": "WP-Deckungsanteil: Anteil der Jahres-Heizwärme, den die Wärmepumpe selbst liefert (VDI 4650 aus dem "
               "Bivalenzpunkt). Ab ca. 98 % ist der Heizstab im Jahr kaum relevant.",
    "takt": "Taktgrenze: Oberhalb dieser Außentemperatur braucht das Gebäude weniger als die kleinste Leistung der "
            "Wärmepumpe – sie schaltet dann ein und aus. Puffer bzw. ausreichend Wasservolumen beruhigen den Betrieb.",
    "a7": "A-7: Prüfpunkt nach EN 14511 – Außenluft −7 °C. A-7/W55 = Leistung bei −7 °C Luft und 55 °C Vorlauf.",
    "nat": "θe (Norm-Außentemperatur): tiefste Auslegungstemperatur am Standort nach DIN/TS 12831-1, aus der PLZ.",
    "heizgrenze": "Heizgrenze: Außentemperatur, ab der nicht mehr geheizt wird (Neubau ca. 12 °C, Bestand ca. 15 °C). "
                  "Dort endet die Gebäudekennlinie bei 0 kW.",
    "kennlinie": "Gebäudekennlinie: Bedarf über der Außentemperatur – QGES bei θe, linear fallend bis 0 kW an der "
                 "Heizgrenze. Wo die WP-Kurve darüber liegt, schafft die Wärmepumpe den Bedarf allein.",
    "heizkurve": "Heizkurve: nötige Vorlauftemperatur je Außentemperatur. Bei milderem Wetter reicht ein niedrigerer "
                 "Vorlauf – das steigert Effizienz (COP) und Leistung der Wärmepumpe.",
    "scop": "SCOP: Jahresarbeitszahl nach EN 14825 (mittleres Klima) – Wärme je kWh Strom über das Jahr; bei 35 °C "
            "(Fußbodenheizung) höher als bei 55 °C (Heizkörper).",
    "kaskade": "Kaskade: mehrere Wärmepumpen über einen Kaskadenregler (HPC800i C, HPC 301 C) – mehr Leistung, feinere "
               "Modulation und Redundanz.",
}


def klartext(e: dict, r: dict, katalog: dict) -> list[dict]:
    """Auslegung in Sätzen erklärt (wie klartext() in index.html). Fett: **…**; Status: ok / warn / bad / ''."""
    from .schema import zahl   # gleiche Rundung wie schemaZahl() in index.html

    def z(x, d: int = 1) -> str:
        return "–" if x is None else zahl(x, d)

    def zt(x) -> str:
        return "–" if x is None else z(x, 1).replace("-", "−")

    if not r["qges"] > 0:
        return [{"text": "Noch keine Eingaben: Wärmebedarf in Karte ② eingeben (Heizlast, W/m² oder Jahresverbrauch) – "
                         "dann schlägt das Tool die passende Wärmepumpe vor und erklärt das Ergebnis hier.", "status": ""}]
    out = []
    qs = f"**{z(r['qges'], 1)} kW**: {z(r['qh'], 1)} kW Heizung"
    if r["qtw"] > 0:
        qs += f" + {z(r['qtw'], 1)} kW Warmwasser"
    if r["qsperr"] > 0:
        qs += f" + {z(r['qsperr'], 1)} kW Sperrzeit"
    out.append({"text": f"Das Gebäude braucht bei der Norm-Außentemperatur {zt(r['nat'])} °C insgesamt {qs}.", "status": ""})
    g = r.get("gewaehlt")
    if not g:
        out.append({"text": "Noch keine passende Wärmepumpe – Heizlast, Vorlauf oder Baureihen prüfen.", "status": "bad" if r["qges"] > 0 else ""})
        return out
    ie = inneneinheit(e, r, katalog)
    woher = ("Aus der MFH-Musterlösung" if r.get("mfh_wp") else "Empfohlen") if not e["auswahl"].get("geraet") else "Gewählt"
    out.append({"text": f"{woher}: **{(str(g['n']) + ' × ') if g['n'] > 1 else ''}{g['geraet']}**"
                        + (f" mit {ie['typ']}" if ie else "") + ".", "status": ""})
    if not g["moeglich"]:
        out.append({"text": f"Nicht möglich: {g['grund']}.", "status": "bad"})
        return out
    art = g["bivalenz_art"]
    if art == "unter":
        out.append({"text": f"Die Wärmepumpe deckt den Bedarf allein – auch bei {zt(r['nat'])} °C (Abdeckung "
                            f"**{z(g['abdeckung'] * 100, 0)} %**), kein Heizstab nötig.", "status": "ok"})
    elif art == "punkt":
        zu_viel = g["heizstab_max_kw"] is not None and g["heizstab_kw"] > g["heizstab_max_kw"] + 1e-9
        t = (f"Die Wärmepumpe schafft den Bedarf allein bis **{zt(g['bivalenz'])} °C** (Bivalenzpunkt). Nur darunter hilft "
             f"der Heizstab – bei {zt(r['nat'])} °C mit **{z(g['heizstab_kw'], 1)} kW**")
        if g["heizstab_max_kw"] is not None:
            t += f" (eingebaut {z(g['heizstab_max_kw'], 0)} kW)"
        out.append({"text": t + ("; das reicht nicht – größere Wärmepumpe oder Kaskade wählen." if zu_viel else "."),
                    "status": "bad" if zu_viel else ("ok" if g["ok"] else "warn")})
    else:
        out.append({"text": "Die Wärmepumpe reicht selbst an der Heizgrenze nicht – größere Wärmepumpe oder Kaskade wählen.", "status": "bad"})
    krit = {"monovalent": "monovalent", "monoenergetisch": "monoenergetisch", "hybrid": "GEG-Hybrid"}[r["kriterium"]]
    if g["ok"]:
        out.append({"text": f"Damit ist die Auslegung **{krit}** erfüllt: gefordert {z(r['mindestleistung'], 1)} kW, die Wärmepumpe "
                            f"liefert {z(g['q_a7'], 1)} kW bei {'B0' if r['waermequelle'] == 'sole' else 'A-7'}.", "status": "ok"})
    else:
        out.append({"text": f"Auslegung **{krit}** nicht erfüllt: {g['grund']}.", "status": "bad"})
    en = r.get("energie")
    t = f"Übers Jahr liefert die Wärmepumpe rund **{z(g['deckung'] * 100, 0)} %** der Wärme"
    if en and en.get("scop"):
        t += f", Strombedarf ca. **{z(en['strom_wp_kwh'] + en['strom_heizstab_kwh'], 0)} kWh/a** (SCOP ≈ {z(en['scop'], 2)})"
    out.append({"text": t + ".", "status": "ok" if g["deckung"] >= 0.98 else "warn"})
    if g.get("taktgrenze") is not None and g["taktgrenze"] < r["heizgrenze"]:
        out.append({"text": f"Ab ca. **{zt(g['taktgrenze'])} °C** braucht das Gebäude weniger als die kleinste Leistung der "
                            "Wärmepumpe – sie taktet dann; Puffer bzw. Wasservolumen einplanen.", "status": ""})
    hk = r.get("heizkurve")
    if hk:
        p_ = hk["punkte"]
        t = f"Vorlauf {z(r['vl'], 0)} °C bei {zt(r['nat'])} °C"
        if "-7" in p_:
            t += f", bei −7 °C ca. {z(p_['-7'], 0)} °C"
        if "7" in p_:
            t += f", bei +7 °C ca. {z(p_['7'], 0)} °C"
        vmax = g.get("vl_max_geraet")
        zu_hoch = vmax is not None and r["vl"] > vmax
        out.append({"text": t + (f" – über dem max. Vorlauf der Wärmepumpe ({z(vmax, 0)} °C)." if zu_hoch
                                 else " (Heizkurve) – je niedriger der Vorlauf, desto effizienter."), "status": "bad" if zu_hoch else ""})
    v = r.get("mfh")
    if v and v["auswahl"]:
        z = v["auswahl"][0]["zelle"]
        out.append({"text": f"MFH-Musterlösung {z['we']} WE / {z['kw']} kW: **{' · '.join(z['komponenten'])}**.", "status": ""})
    return out


STATUS_ICON = {"ok": "✅", "warn": "⚠️", "bad": "❌", "": "•"}
# KPI-Kachel → Glossar-Schlüssel (wie kpis() in index.html)
KPI_GLOSSAR = {"Gesamtheizlast QGES": "qges", "Mindestleistung WP": "mindest", "Bivalenzpunkt": "biv", "Leistung bei θe": "qnat",
               "Heizstab bei θe": "heizstab", "WP-Deckungsanteil": "deckung"}
# Rechenweg in Schritten (wie RECHENWEG in index.html)
RECHENWEG = [
    ("Heizlast QH", "aus Vorgabe (DIN EN 12831), Wohnfläche × W/m², Jahresverbrauch (Excel-Blatt „Heizlast nach Verbrauch mit TWW“) "
                    "oder Gebäudehülle."),
    ("Zuschläge → QGES", "Warmwasser QTW aus Personen und Liter je Person (bzw. Nachheizzeit), Sperrzeit 2/4/6 h → +5/10/15 %."),
    ("Mindestleistung", "nach Betriebsweise: monoenergetisch 0,7 · QGES bei A-7, monovalent QGES bei θe, GEG-Hybrid 0,3 · QH bei A-7."),
    ("Gebäudekennlinie", "QGES bei θe, linear bis 0 kW an der Heizgrenze."),
    ("Gerätekurven", "maximale und minimale Heizleistung je Gerät aus dem Excel-Werkzeug (Sole: Katalog), "
                     "zwischen 35/45/55/65 °C Vorlauf interpoliert; Kaskaden addieren."),
    ("Bivalenzpunkt und Taktgrenze", "Schnitt der Gerätekurve bzw. der Mindestleistung mit der Gebäudekennlinie."),
    ("Heizstab und Deckungsanteil", "Heizstab = QGES − WP-Leistung bei θe; Jahres-Deckungsanteil nach VDI 4650 aus dem Bivalenzpunkt."),
    ("Empfehlung", "kleinste Größe je Baureihe, die das Kriterium erfüllt; beim Mehrfamilienhaus die geprüfte Musterlösung."),
    ("Heizkurve und Anbindung", "Vorlauf über der Außentemperatur (DIN EN 442), Rohrdimension der Verbindungsleitung "
                                "(v ≤ 1 m/s, R ≤ 200 Pa/m), Erdsonden-Richtwert bei Sole."),
]
