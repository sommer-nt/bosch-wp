"""Bosch WP-Schnellauslegung (Streamlit) – gleicher Rechenweg wie index.html.

Start:  streamlit run app.py
"""
from __future__ import annotations

import os
import sys
from datetime import date
from pathlib import Path

import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
st.set_page_config(page_title="Bosch WP-Schnellauslegung", page_icon="♨️", layout="wide")

from wp import bericht as B  # noqa: E402
from wp import daten as D  # noqa: E402
from wp import export as X  # noqa: E402
from wp import hydraulik as HY  # noqa: E402
from wp import mfh as M  # noqa: E402
from wp import projekt as P  # noqa: E402
from wp import rechnen as R  # noqa: E402
from wp import schema as S  # noqa: E402
from wp import texte as T  # noqa: E402

BLAU, ROT, VIOLETT = "#007BC0", "#ED0007", "#7a3e9d"
ss = st.session_state

# ------------------------------------------------------------------ Zugang (optional, wie Bosch Flow)
_pw = os.environ.get("APP_PASSWORT", "").strip()
if _pw and not ss.get("angemeldet"):
    st.title("Bosch WP-Schnellauslegung")
    if st.text_input("Passwort", type="password") == _pw:
        ss.angemeldet = True
        st.rerun()
    st.stop()

if "e" not in ss:
    ss.e = P.neu()
E = ss.e
DATEN, KAT = D.geraete(), D.katalog()

# Bosch-Gestaltung wie index.html: Tokens des Bosch Frontend-Kits (blue-50 #007BC0, gray-95 #EFF1F2, green-50, red-50,
# yellow-85), eckige Kanten ohne Schatten, Bosch Sans falls installiert (keine Google Fonts)
st.markdown("""<style>
html,body,[class*="css"],.stMarkdown,.stButton button,input,select,textarea{font-family:"Bosch Sans","BoschSans",Arial,Helvetica,sans-serif}
.block-container{padding-top:3rem}
*{border-radius:0!important}
.stButton button,.stDownloadButton button{border:1px solid #007BC0;color:#007BC0;background:#fff;font-weight:400;min-height:40px}
.stButton button:hover,.stDownloadButton button:hover{background:#E8F1FF;color:#00629A;border-color:#00629A}
.stButton button[kind="primary"]{background:#007BC0;color:#fff}
.stTextInput input,.stNumberInput input,.stSelectbox div[data-baseweb="select"]>div{background:#E0E2E5;border:0;border-bottom:1px solid #000}
.stNumberInput input{text-align:right}
.stTabs [data-baseweb="tab"][aria-selected="true"]{color:#007BC0}
.stTabs [data-baseweb="tab-highlight"]{background-color:#007BC0}
.kpi{border:1px solid #E0E2E5;padding:8px 12px;background:#fff;margin-bottom:8px}
.kpi .t{font-size:11px;color:#43464A;text-transform:uppercase}.kpi .v{font-size:21px;font-weight:700;color:#000}
.kpi .s{font-size:11px;color:#71767C}.kpi.ok{border-left:4px solid #00884A}.kpi.warn{border-left:4px solid #FFCF00}.kpi.bad{border-left:4px solid #ED0007}
</style>""", unsafe_allow_html=True)
st.markdown(f"<span style='color:{ROT};font-weight:800;font-size:22px'>BOSCH</span> "
            "<span style='font-size:20px;font-weight:400'>WP-Schnellauslegung</span> "
            "<span style='color:#4a5866'>· Luft/Wasser- und Sole/Wasser-Wärmepumpen · Heizlast, Bivalenzpunkt, Geräteauswahl</span> "
            "<span style='font-size:12px;color:#4a5866;background:#E0E2E5;padding:3px 6px;"
            "margin-left:8px'>Entwickelt von <b style='color:#007BC0'>Daniel Sommer</b> · HC/SDE3-PSD</span>",
            unsafe_allow_html=True)


def zahl(label, pfad, **kw):
    teile = pfad.split(".")
    ziel = E
    for t in teile[:-1]:
        ziel = ziel[t]
    ziel[teile[-1]] = st.number_input(label, value=float(ziel[teile[-1]]), key="n_" + pfad, **kw)


def wahl(label, pfad, optionen: dict, horizontal=True, radio=True):
    """Auswahl (Radio als Segment) für E[pfad]; liefert True bei Änderung."""
    teile = pfad.split(".")
    ziel = E
    for t in teile[:-1]:
        ziel = ziel[t]
    alt = ziel[teile[-1]]
    liste = list(optionen)
    idx = liste.index(alt) if alt in liste else 0
    if radio:
        neu_ = st.radio(label, liste, index=idx, format_func=optionen.get, horizontal=horizontal, key="w_" + pfad)
    else:
        neu_ = st.selectbox(label, liste, index=idx, format_func=optionen.get, key="w_" + pfad)
    ziel[teile[-1]] = neu_
    return neu_ != alt


def neu_setzen(*pfade):
    """Nach automatischer Vorbelegung die Eingabefelder neu aus E lesen."""
    for p_ in pfade:
        ss.pop("n_" + p_, None)
        ss.pop("w_" + p_, None)


def mfh_bereich(r: dict, e: dict) -> None:
    v, MD = r["mfh"], D.mfh()
    a_ = MD["annahmen"][v["tabelle"]]
    st.markdown("**MFH-Musterlösung** – Musterlösungen Bosch · Kostenübersicht 20.08.2026")
    st.caption(f"{'Neubau' if v['tabelle'] == 'neubau' else 'Bestand'} · {MD['systeme'][v['system']]} · {M.WW_TEXT[v['ww']]} · "
               f"{v['we']} WE · Heizlast QH {T.f(v['qh'], 1)} kW · Musterannahmen: {a_['flaeche_we']} m² und "
               f"{T.f(a_['personen_we'], 1)} Personen je WE, {a_['spez_w_m2']} W/m²")
    if not v["zellen"]:
        st.info("Für diese Kombination gibt es noch keine Musterlösung.")
        return
    ids = [z_["id"] for z_ in v["zellen"]]
    gew = {a["zelle"]["id"] for a in v["auswahl"]}
    beschr = {z_["id"]: f"{z_['we']} WE · {z_['kw']} kW" + (f" · {z_['variante'].replace('Gas-Brennwert ', '')}" if z_.get("variante") else "")
              for z_ in v["zellen"]}
    wahl_ = st.radio("Musterlösung", ["auto"] + ids, horizontal=True, key="mfh_zelle",
                     index=(ids.index(e["mfh"]["zelle"]) + 1) if e["mfh"].get("zelle") in ids else 0,
                     format_func=lambda x: "automatisch (" + " / ".join(beschr[i_] for i_ in ids if i_ in gew) + ")" if x == "auto" else beschr[x])
    if (wahl_ if wahl_ != "auto" else "") != (e["mfh"].get("zelle") or ""):
        e["mfh"]["zelle"] = "" if wahl_ == "auto" else wahl_
        st.rerun()
    if v["ausserhalb"]:
        st.warning("Heizlast bzw. Wohneinheiten liegen über den Musterlösungen – größte Musterlösung angezeigt, Anlage individuell planen.")
    g_ = r["gewaehlt"]
    for a in v["auswahl"]:
        z_ = a["zelle"]
        st.markdown(f"<div style='font-size:12px;font-weight:700;color:#4a5866;text-transform:uppercase;margin-top:8px'>"
                    f"{z_.get('erzeuger') or 'Monoenergetisch'} · {z_['we']} WE / {z_['kw']} kW{' · ' + z_['variante'] if z_.get('variante') else ''}</div>"
                    f"<b>{' · '.join(z_['komponenten'])}</b> · Summe netto {T.euro(z_['summe'])}", unsafe_allow_html=True)
        st.caption(f"Muster-Heizlast {z_['we']} WE · {a_['flaeche_we']} m² · {a_['spez_w_m2']} W/m² = {T.f(a['muster_qh'], 1)} kW · "
                   f"Prüfung mit Ihren Eingaben: {M.pruef_text(a, r)}")
        if g_ and g_["geraet"] == z_["geraet"] and g_["n"] == z_["n"]:
            st.caption("✓ als Wärmepumpe gewählt")
        elif st.button("Wärmepumpe übernehmen", key="mfh_ueb_" + z_["id"]):
            e["auswahl"].update(geraet=z_["geraet"], anzahl=z_["n"], inneneinheit="")
            st.rerun()
    st.caption("Die passende Hydraulik zur Musterlösung wählen Sie im Reiter „Hydraulik“. Musterlösungen ersetzen keine Fachplanung.")


STUFE_ZEICHEN = {"passt": "✅", "vorlage": "🟡", "prinzip": "❌"}


def hydraulik_bereich(r: dict, e: dict) -> None:
    """Hydraulik-Auswahl aus den Musterlösungen – wie hydHtml() in index.html."""
    lib, g_ = D.hydraulik(), r["gewaehlt"]
    st.markdown("**Hydraulik auswählen** – Hydraulikschemata der Musterlösungen")
    if not g_:
        st.caption("Erst eine Wärmepumpe auslegen – dann erscheinen hier die passenden Hydrauliken zur Auswahl.")
        return
    liste = HY.schemata(e, r, lib)
    passend = [x for x in liste if x["passend"]]
    gew = HY.gewaehlt(e, r, lib)
    st.caption(f"Maschine: {(str(g_['n']) + ' × ') if g_['n'] > 1 else ''}{g_['geraet']} · {HY.WW_TEXT[HY.ww_art(e, r)]} · "
               f"{'Hybrid (mit zweitem Wärmeerzeuger)' if HY.system_art(e, lib) == 'hybrid' else 'monoenergetisch/monovalent'}"
               + (f" · {len(passend)} passende Hydraulik(en) aus den Musterlösungen." if passend else "."))
    for t_ in HY.hinweise(e, r, lib):
        st.warning(t_)
    st.caption("Ampel: ✅ passt direkt = Schema 1 : 1 verwendbar · 🟡 Vorlage = gleiche Baureihe, die genannten Punkte ergänzen · "
               "❌ Prinzip = andere Baureihe, nur zur Orientierung.")

    def stufe(x: dict) -> str:
        return f"{STUFE_ZEICHEN[x['stufe']]} {HY.STUFE_TEXT[x['stufe']]}"

    if gew:
        st.markdown(f"**{'Ausgewählt' if gew['manuell'] else 'Vorgeschlagen'}: {gew['titel']}** · {stufe(gew)}")
        if gew["anpassen"]:
            st.markdown("**Anpassen:**\n" + "\n".join("- " + t_ for t_ in gew["anpassen"]))
        st.image(str(D.hydraulik_bild(gew["id"])), width="stretch")
        st.caption("Musterlösungen mit diesem Schema: " + ", ".join(gew["loesungen"]))
    alle = st.toggle(f"Alle {len(liste)} Hydrauliken zeigen", key="hyd_alle")
    zeigen = liste if alle else (passend or liste[:4])
    for x in zeigen:
        c_b, c_t = st.columns([1, 2])
        c_b.image(str(D.hydraulik_bild(x["id"])), width="stretch")
        c_t.markdown(f"**{x['titel']}** · {stufe(x)}  \n" + " · ".join(f"{'✅' if x['passt'][k] else '❌'} {t}" for k, t, _ in HY.MERKMALE)
                     + "".join("  \n– " + t_ for t_ in x["anpassen"])
                     + f"  \nMusterlösungen: {', '.join(x['loesungen'])}")
        aktiv = gew and gew["id"] == x["id"] and gew["manuell"]
        if c_t.button("Auswahl aufheben" if aktiv else "Diese Hydraulik wählen", key="hyd_" + x["id"]):
            e["hydraulik"] = {**(e.get("hydraulik") or {}), "schema": "" if aktiv else x["id"]}
            st.rerun()
    ls = HY.loesungen(e, r, lib)
    if ls:
        st.markdown("**Musterlösungen mit Excel-Auslegung zu dieser Maschine**")
        st.caption("„Auslegung übernehmen“ setzt die Eingaben der Excel-Auslegung (PLZ, Heizlast, Warmwasser, Vorlauf, Kriterium, "
                   "Wärmepumpe) – der Rechenkern prüft die Musterlösung dann nach.")
        for L in ls:
            a = L["auslegung"]
            c_a, c_b = st.columns([4, 1])
            c_a.caption(f"{L['id']} · {'Neubau' if L['gebaeude'] == 'neubau' else 'Bestand'} · {L['we'] or '–'} WE · "
                        f"{(str(L['n']) + ' × ') if L['n'] > 1 else ''}{L['geraet']} · QGES {T.f(a['qges'], 1)} kW · Vorlauf "
                        f"{T.f(a['vl'], 0)} °C{' (angenommen)' if a.get('vl_angenommen') else ''} · "
                        f"{ {'hybrid': 'GEG-Hybrid (0,3 · Q)', 'monoenergetisch': 'monoenergetisch', 'monovalent': 'monovalent'}.get(a['auslegung'], '–')} · "
                        f"PLZ {a['plz']} (θe {T.ft(a['nat'])} °C)" + ("" if L["schemata"] else " · ohne eigenes Schema"))
            if c_b.button("Auslegung übernehmen", key="ausl_" + L["id"]):
                ss.e = HY.uebernehmen(e, L)
                for k_ in [k_ for k_ in ss if str(k_).startswith(("n_", "w_", "hk_", "mfh_"))]:
                    del ss[k_]
                st.rerun()


kopf_l, kopf_r = st.columns([3, 1])
with kopf_r:
    E["experte"] = st.toggle("Expertenmodus", E.get("experte", False),
                             help="Zusätzlich: Gebäudehülle, Heizwert, Nutzungsgrad, Vollbenutzungsstunden, Warmwasser nach "
                                  "DIN V 18599, Lastprofil/Nachheizzeit, Sperrzeit, Betriebsweise, Baureihen")
EX = E["experte"]
# gewählte Baureihe immer in der Liste (Filter erweitern), wie index.html
if E["auswahl"]["geraet"] and E.get("serien"):
    _sid = (D.geraet(E["auswahl"]["geraet"]) or {}).get("serie")
    if _sid and _sid not in E["serien"]:
        E["serien"].append(_sid)
links, rechts = st.columns([1, 2.2], gap="large")

# ================================================================== Eingaben (Reihenfolge der Schnellauslegung)
with links:
    with st.expander("① Projekt, Gebäude & Standort", expanded=True):
        E["projekt"]["name"] = st.text_input("Projekt / Bauvorhaben", E["projekt"]["name"])
        E["projekt"]["kunde"] = st.text_input("Kunde / Interessent", E["projekt"]["kunde"])
        c_s1, c_s2 = st.columns([3, 1])
        E["projekt"]["strasse"] = c_s1.text_input("Straße", E["projekt"].get("strasse", ""))
        E["projekt"]["hausnr"] = c_s2.text_input("Nr.", E["projekt"].get("hausnr", ""))
        if EX:
            E["projekt"]["bearbeiter"] = st.text_input("Bearbeiter", E["projekt"]["bearbeiter"])
        if wahl("Gebäude", "gebaeude.typ", {"neubau": "Neubau", "sanierung": "Sanierung / Bestand"}):
            neubau = E["gebaeude"]["typ"] == "neubau"
            E["klima"]["heizgrenze"] = 12.0 if neubau else 15.0
            E["heizkreise"] = [{"typ": "fbh" if neubau else "hk"}]
            E["vl"] = float(T.VERTEILUNG_VL["fbh" if neubau else "hk"])
            for k_ in [k_ for k_ in ss if str(k_).startswith("hk_")]:
                del ss[k_]
            E["heizlast"]["spez_w_m2"] = float(T.SPEZ[E["gebaeude"]["typ"]][1][0])
            M.eingaben_folgen(E, "gebaeude.typ")
            neu_setzen("klima.heizgrenze", "vl", "heizlast.methode", "heizlast.spez_w_m2", "heizlast.flaeche_m2", "heizlast.gebaeudeart", "heizlast.vbh", "tww.personen", "tww.system")
            st.rerun()
        # Mehrfamilienhaus: Wohneinheiten und Warmwasserbereitung gleich zu Beginn (MFH-Musterbestellvorschläge)
        if wahl("Gebäudegröße", "mfh.art", {"efh": "Ein-/Zweifamilienhaus", "mfh": "Mehrfamilienhaus"}):
            M.eingaben_folgen(E, "mfh.art")
            neu_setzen("heizlast.methode", "heizlast.spez_w_m2", "heizlast.flaeche_m2", "heizlast.gebaeudeart", "heizlast.vbh", "tww.personen", "tww.system")
            st.rerun()
        if E["mfh"]["art"] == "mfh":
            we_neu = st.number_input("Wohneinheiten [WE]", 2, 40, int(E["mfh"]["we"]), key="mfh_we")
            if we_neu != E["mfh"]["we"]:
                E["mfh"]["we"] = int(we_neu)
                M.eingaben_folgen(E, "mfh.we")
                neu_setzen("heizlast.methode", "heizlast.spez_w_m2", "heizlast.flaeche_m2", "heizlast.gebaeudeart", "heizlast.vbh", "tww.personen", "tww.system")
                st.rerun()
            if wahl("Warmwasserbereitung", "mfh.ww", {"friwa": "Zentral · FriWa", "hiu": "Dezentral · HIU", "dle": "Ohne · DLE",
                                                      "speicher": "Speicher · bis 4 WE"}):
                M.eingaben_folgen(E, "mfh.ww")
                neu_setzen("heizlast.methode", "heizlast.spez_w_m2", "heizlast.flaeche_m2", "heizlast.gebaeudeart", "heizlast.vbh", "tww.personen", "tww.system")
                st.rerun()
            st.caption("MFH-Musterlösungen: je WE 80 m² und 3,5 Personen (Personen und Wohnfläche werden vorbelegt). "
                       "Zentral = Frischwasserstation mit eigenem Puffer (> 60 °C), dezentral = Wohnungsstationen (HIU, 2-Leiter, "
                       "< 60 °C), ohne = elektrische Durchlauferhitzer je Wohnung, Speicher = Warmwasserspeicher an der Wärmepumpe – "
                       "nur für kleine MFH bis Leistungskennzahl NL 4 (etwa 4 Wohnungen).")
        arten = {a: a for a in R.VOLLBENUTZUNGSSTUNDEN}
        if wahl("Gebäudeart", "heizlast.gebaeudeart", arten, radio=False):
            E["heizlast"]["vbh"] = float(R.VOLLBENUTZUNGSSTUNDEN[E["heizlast"]["gebaeudeart"]])
            neu_setzen("heizlast.vbh")
        zahl("Raumtemperatur θi [°C]", "klima.innen", step=1.0)
        plz = st.text_input("PLZ", E["projekt"]["plz"], max_chars=5)
        if plz != E["projekt"]["plz"]:
            E["projekt"]["plz"] = plz
            treffer = D.plz_suche(plz) if len(plz) >= 4 else None
            if treffer:
                E["projekt"]["ort"], E["klima"]["nat"] = treffer
                neu_setzen("klima.nat")
                st.rerun()
        E["projekt"]["ort"] = st.text_input("Ort", E["projekt"]["ort"])
        c1, c2 = st.columns(2)
        with c1:
            zahl("Norm-Außentemp. θe [°C]", "klima.nat", step=0.5, help="Über die PLZ vorbelegt (DIN/TS 12831-1)")
        with c2:
            zahl("Heizgrenze [°C]", "klima.heizgrenze", step=1.0, help="Neubau 12 °C, Bestand 15 °C")

    with st.expander("② Wärmebedarf", expanded=True):
        h = E["heizlast"]
        methoden = {"vorgabe": "Heizlast kW", "flaeche": "W/m²", "verbrauch": "Jahresverbrauch"}
        if EX or h["methode"] == "huelle":
            methoden["huelle"] = "Gebäudehülle"
        wahl("Methode", "heizlast.methode", methoden)
        if h["methode"] == "vorgabe":
            zahl("Heizlast (Berechnung DIN EN 12831) [kW]", "heizlast.vorgabe_kw", min_value=0.0, step=0.1)
        elif h["methode"] == "flaeche":
            zahl("Beheizte Wohnfläche [m²]", "heizlast.flaeche_m2", min_value=0.0, step=1.0)
            standards = {float(v): t for v, t in T.SPEZ[E["gebaeude"]["typ"]]}
            if h["spez_w_m2"] in standards or not EX:
                if h["spez_w_m2"] not in standards:
                    h["spez_w_m2"] = next(iter(standards))
                wahl("Gebäudestandard", "heizlast.spez_w_m2", standards, radio=False)
            if EX:
                zahl("Spezifischer Wärmebedarf [W/m²]", "heizlast.spez_w_m2", min_value=0.0, step=1.0)
        elif h["methode"] == "huelle":
            zahl("Gebäudehüllfläche A [m²]", "heizlast.huell_a_m2", min_value=0.0)
            zahl("H'T [W/m²K]", "heizlast.ht", min_value=0.0, step=0.01)
            zahl("Luftvolumen V (Ve · 0,76) [m³]", "heizlast.volumen_m3", min_value=0.0)
            zahl("Luftwechsel n [1/h]", "heizlast.luftwechsel", min_value=0.0, step=0.1)
        else:
            traeger = {"gas": "Erdgas", "oel": "Heizöl", "pellet": "Pellets", "kwh": "kWh (Fernwärme, Strom …)"}
            if wahl("Energieträger", "heizlast.energietraeger", traeger, radio=False):
                h["heizwert"] = R.HEIZWERT[h["energietraeger"]][0]
                neu_setzen("heizlast.heizwert")
            einheit = R.HEIZWERT[h["energietraeger"]][1]
            zahl(f"Jahres-Gesamtverbrauch [{einheit}]", "heizlast.menge", min_value=0.0, step=10.0)
            h["ww_im_verbrauch"] = st.checkbox("Warmwasser im Verbrauch enthalten", h["ww_im_verbrauch"])
            if EX:
                zahl(f"Heizwert Hu [kWh/{einheit}]", "heizlast.heizwert", min_value=0.0, step=0.01)
                zahl("Vollbenutzungsstunden th (VDI 2067) [h/a]", "heizlast.vbh", min_value=1.0, step=50.0)
                zahl("Jahresnutzungsgrad Altanlage η", "heizlast.nutzungsgrad", min_value=0.5, max_value=1.1, step=0.01,
                     help="1,0 = Rechenweg Excel (ohne Umrechnungsfaktoren und Gradtage)")
            st.caption("Excel-Blatt „DIN EN 12831 Heizlast nach Verbrauch mit TWW“: Øh,in = Øh,g + Ew,g,in / (td · 365). "
                       "Der Warmwasser-Zuschlag läuft dabei automatisch über die Nachheizzeit.")

    with st.expander("③ Heizkreise & Wärmeverteilung", expanded=True):
        kreise = T.heizkreis_liste(E)
        neu_kreise = []
        for h_ in kreise:
            typ = st.selectbox(f"Heizkreis {h_['nr']} · {'gemischt' if h_['gemischt'] else 'ungemischt'} · {h_['vl']} °C",
                               list(T.HK_TYP), index=list(T.HK_TYP).index(h_["typ"]), format_func=T.HK_TYP.get, key=f"hk_{h_['nr']}")
            neu_kreise.append({"typ": typ})
        b1, b2 = st.columns(2)
        if b1.button("+ Heizkreis", disabled=len(kreise) >= T.HK_MAX, width="stretch"):
            neu_kreise.append({"typ": "hk" if any(k_["typ"] == "fbh" for k_ in neu_kreise) else "fbh"})
        if b2.button("− Heizkreis", disabled=len(kreise) <= 1, width="stretch"):
            neu_kreise.pop()
            ss.pop(f"hk_{len(kreise)}", None)
        if neu_kreise != [{"typ": h_["typ"]} for h_ in kreise]:
            E["heizkreise"] = neu_kreise
            E["vl"] = float(max(T.VERTEILUNG_VL[k_["typ"]] for k_ in neu_kreise))
            neu_setzen("vl")
            st.rerun()
        zahl("Max. erforderliche Vorlauftemperatur [°C]", "vl", min_value=30.0, max_value=70.0, step=1.0,
             help="Vorschlag aus dem Heizkreis mit dem höchsten Vorlauf: FBH 35 °C, Konvektoren 45 °C, Heizkörper 55 °C. "
                  "Kreise mit niedrigerem Vorlauf werden gemischt.")

    with st.expander("④ Warmwasser", expanded=True):
        t = E["tww"]
        ist_mfh = E["mfh"]["art"] == "mfh"
        if ist_mfh:
            st.caption(f"Mehrfamilienhaus: Warmwasserbereitung „{M.WW_TEXT[E['mfh']['ww']]}“ (Karte ①).")
        t["aktiv"] = st.checkbox("Warmwasser über die Wärmepumpe", t["aktiv"], disabled=ist_mfh)
        zahl("Anzahl Personen", "tww.personen", min_value=0.0, step=1.0)
        if ist_mfh:
            st.caption("System: " + ("Speichersystem" if t["system"] == "speicher" else "Frischwasserstation / Wohnungsstation mit Puffer"))
        else:
            wahl("System", "tww.system", {"speicher": "Speichersystem", "friwa": "Frischwasserstation"})
        zahl("Zapftemperatur [°C]", "tww.zapftemp", min_value=35.0, max_value=65.0, step=1.0)
        if t.get("bezug", "liter") == "liter":
            zahl("Warmwassermenge je Person bei 45 °C [l/(P·d)]", "tww.liter_p", min_value=0.0, step=5.0)
        if EX:
            st.markdown("**Experte · Warmwasser**")
            wahl("Leistungszuschlag QTW", "tww.methode",
                 {"auto": "automatisch", "personen": "Personen × Lastprofil", "nachheizzeit": "Jahresbedarf / Nachheizzeit"}, radio=False)
            if t["methode"] == "personen":
                wahl("Lastprofil", "tww.kw_person", {0.1: "Standard 0,10 kW/P", 0.2: "Standard Plus 0,20 kW/P",
                                                     0.25: "Regendusche 0,25 kW/P"}, radio=False)
            wahl("Nachheizzeit td", "tww.td", {4: "Standard · 4 h/d", 3: "Gehobener Standard · 3 h/d", 2: "Luxus · 2 h/d"}, radio=False)
            zahl("Kaltwassertemperatur [°C]", "tww.t_kw", min_value=5.0, max_value=20.0, step=1.0)
            bezug = {"liter": "Liter je Person (45 °C)", "personen": "DIN V 18599-10 je Person", "flaeche": "DIN V 18599-10 je m²"}
            alt_n = t["nutzung"]
            geaendert = wahl("Bedarf nach", "tww.bezug", bezug, radio=False)
            if t["bezug"] != "liter":
                wahl("Nutzung (DIN V 18599-10)", "tww.nutzung", {n: n for n in R.TWW_BEDARF}, radio=False)
                if geaendert or alt_n != t["nutzung"]:
                    t["qwb"] = R.TWW_BEDARF[t["nutzung"]][1 if t["bezug"] == "flaeche" else 0]
                    neu_setzen("tww.qwb")
                    st.rerun()
                zahl("Qw,b [kWh/(m²·d)]" if t["bezug"] == "flaeche" else "Qw,b [kWh/(P·d)]", "tww.qwb",
                     min_value=0.0, step=0.0001, format="%.4f")
                if t["bezug"] == "flaeche":
                    zahl("Nutzfläche ANGF [m²]", "tww.flaeche_m2", min_value=0.0)

    with st.expander("⑤ Wärmepumpe & Aufstellung", expanded=True):
        if wahl("Wärmequelle", "waermequelle", {"luft": "Luft/Wasser", "sole": "Sole/Wasser"}):
            E["auslegung"] = "monovalent" if E["waermequelle"] == "sole" else "monoenergetisch"
            E["auswahl"].update(geraet="", anzahl=1, inneneinheit="")
            neu_setzen("auslegung")
            st.rerun()
        if E["waermequelle"] == "luft":
            st.caption("Außenaufstellung der Außeneinheit (Monoblock) – R290-Sicherheitsbereich und Schall beachten.")
            zahl("Entfernung Außeneinheit – Gebäude [m]", "aufstellung.entfernung_m", min_value=0.0, step=1.0)
        else:
            st.caption("Innenaufstellung; Wärmequelle Erdwärmesonde/Flächenkollektor (Sole ≈ 0 °C). Üblich: monovalent.")
        if EX:
            st.markdown("**Experte · Auslegung**")
            if wahl("Betriebsweise", "auslegung", {"monoenergetisch": "monoenergetisch (0,7 · QGES bei A-7 = −7 °C Außenluft)",
                                                   "monovalent": "monovalent (QGES bei θe)",
                                                   "hybrid": "GEG-Hybrid (0,3 · QH bei A-7 = −7 °C Außenluft)"}, radio=False):
                M.eingaben_folgen(E, "auslegung")
            wahl("Sperrzeit Energieversorger", "sperrzeit_h", {0: "keine", 2: "2 h → +5 %", 4: "4 h → +10 %", 6: "6 h → +15 %"}, radio=False)
            if E["waermequelle"] == "luft":
                zahl("Spreizung Verbindungsleitung [K]", "aufstellung.spreizung", min_value=3.0, max_value=10.0, step=1.0)
            else:
                zahl("Spez. Entzugsleistung Erdsonde [W/m]", "aufstellung.entzug_w_m", min_value=10.0, max_value=100.0, step=5.0)
            quelle_ids = [s_["id"] for s_ in DATEN["serien"] if s_.get("quelle", "luft") == E["waermequelle"]]
            andere = [x for x in (E["serien"] or [s_["id"] for s_ in DATEN["serien"]]) if x not in quelle_ids]
            gew = st.multiselect("Baureihen", quelle_ids, default=[x for x in (E["serien"] or quelle_ids) if x in quelle_ids],
                                 format_func=lambda x: D.serie(x)["name"].replace("Compress ", ""))
            alle_ids = andere + gew
            E["serien"] = [] if set(alle_ids) == {s_["id"] for s_ in DATEN["serien"]} else alle_ids

    with st.expander("⑥ Produktwahl", expanded=True):
        R_ = R.rechne(E, DATEN, KAT)
        modus = st.radio("Auswahl", ["auto", "manuell"], horizontal=True, index=1 if E["auswahl"]["geraet"] else 0,
                         format_func={"auto": "Beste Lösung", "manuell": "Produkt wählen"}.get)
        if modus == "auto" and E["auswahl"]["geraet"]:
            E["auswahl"].update(geraet="", anzahl=1, inneneinheit="")
            st.rerun()
        if modus == "manuell":
            ok = {c["geraet"]: c for c in R_["kandidaten"]}
            optionen = [g_["id"] for g_ in DATEN["geraete"] if D.serie(g_["serie"]).get("quelle", "luft") == E["waermequelle"]]
            vorher = E["auswahl"]["geraet"] or (R_["gewaehlt"]["geraet"] if R_["gewaehlt"] else optionen[0])
            gw = st.selectbox("Wärmepumpe", optionen, index=optionen.index(vorher) if vorher in optionen else 0,
                              format_func=lambda x: x + (" ✓" if ok.get(x, {}).get("ok") else ""))
            if gw != E["auswahl"]["geraet"]:
                E["auswahl"].update(geraet=gw, anzahl=ok[gw]["n"] if gw in ok else 1, inneneinheit="")
                st.rerun()
            smax = D.serie(D.geraet(gw)["serie"])["kaskade_max"]
            if smax > 1:
                n = st.number_input("Anzahl (Kaskade)", 1, smax, min(int(E["auswahl"]["anzahl"]), smax))
                if n != E["auswahl"]["anzahl"]:
                    E["auswahl"]["anzahl"] = n
                    st.rerun()
            else:
                E["auswahl"]["anzahl"] = 1
                st.caption("Diese Baureihe ist nicht kaskadierbar.")
        R_ = R.rechne(E, DATEN, KAT)
        ies = T.inneneinheiten(R_, KAT)
        if ies:
            typen = [i_["typ"] for i_ in ies]
            akt = E["auswahl"]["inneneinheit"] if E["auswahl"]["inneneinheit"] in typen else typen[0]
            E["auswahl"]["inneneinheit"] = st.selectbox("Inneneinheit / Regelung", typen, index=typen.index(akt),
                                                        format_func=lambda x: x + " – " + next(i_["art"] for i_ in ies if i_["typ"] == x))
        E["preise_drucken"] = st.checkbox("Preise (UVP) im PDF – intern", E["preise_drucken"])
        E["projekt"]["notiz"] = st.text_area("Notiz", E["projekt"]["notiz"], height=70)
        R_ = R.rechne(E, DATEN, KAT)

    st.divider()
    if not E["projekt"]["datum"]:
        E["projekt"]["datum"] = date.today().isoformat()
    name = (E["projekt"]["name"] or "Projekt").replace(" ", "_")
    c_s, c_r = st.columns(2)
    c_s.download_button("💾 Projekt speichern (.json)", P.dumps(E), f"WP-Auslegung_{name}.json", "application/json",
                        width="stretch")
    if c_r.button("↺ Zurücksetzen", width="stretch", help="Alle Eingaben auf leer zurücksetzen (vorher speichern!)"):
        ss.e = P.neu()
        for k_ in [k_ for k_ in ss if str(k_).startswith(("n_", "w_", "hk_", "mfh_"))]:
            del ss[k_]
        st.rerun()
    datei = st.file_uploader("Projekt öffnen (.json, auch aus der HTML-Version)", type="json")
    if datei is not None and ss.get("geladen") != datei.file_id:
        try:
            ss.e = P.loads(datei.getvalue().decode("utf-8"))
            ss.geladen = datei.file_id
            for k in [k for k in ss if str(k).startswith("n_")]:
                del ss[k]
            st.rerun()
        except ValueError as fehler:
            st.error(str(fehler))

# ================================================================== Ergebnisse
r = M.rechne(E, DATEN, KAT, D.mfh())   # MFH: Wärmepumpe der Musterlösung bei „Beste Lösung“
g = r["gewaehlt"]
ie = T.inneneinheit(E, r, KAT)
with rechts:
    bestell_titel = "Musterlösung" if r.get("mfh") else "Systempakete"
    t_ueb, t_leis, t_ger, t_hyd, t_best, t_rech = st.tabs(["Überblick", "Leistung & Heizkurve", "Geräteauswahl",
                                                           "Hydraulik & Warmwasser", bestell_titel, "Rechenweg"])
    with t_ueb:
        st.markdown("**Auf einen Blick**")
        st.markdown("\n".join(f"- {T.STATUS_ICON[x['status']]} {x['text']}" for x in T.klartext(E, r, KAT)))
        for m in T.meldungen(E, r, KAT):
            st.warning(m)
        abw = [] if EX else T.experten_abweichungen(E)
        if abw:
            c_a, c_b = st.columns([4, 1])
            c_a.warning("Experteneinstellungen aktiv: " + ", ".join(abw) + ".")
            if c_b.button("Auf Standard zurücksetzen"):
                T.experten_zuruecksetzen(E)
                for k_ in [k_ for k_ in ss if str(k_).startswith(("w_", "n_"))]:
                    del ss[k_]
                st.rerun()
        ks = [("Gesamtheizlast QGES", f"{T.f(r['qges'], 2)} kW", f"QH {T.f(r['qh'], 2)} + QTW {T.f(r['qtw'], 2)} + QSperr {T.f(r['qsperr'], 2)}", ""),
              ("Mindestleistung WP", f"{T.f(r['mindestleistung'], 2)} kW", T.KRITERIUM[r["kriterium"]], "")]
        if g and g["moeglich"]:
            ks += [("Bivalenzpunkt", T.biv_text(g), "Schnitt mit Gebäudekennlinie", "ok" if g["ok"] else "bad"),
                   ("Leistung bei θe", f"{T.f(g['q_nat'], 2)} kW", f"Abdeckung {T.f(g['abdeckung'] * 100, 0)} %", "ok" if g["abdeckung"] >= 1 else "warn"),
                   ("Heizstab bei θe", f"{T.f(g['heizstab_kw'], 2)} kW",
                    f"verfügbar {T.f(g['heizstab_max_kw'], 0)} kW" if g["heizstab_max_kw"] is not None else "bauseits",
                    "ok" if g["heizstab_kw"] <= 0 else "warn"),
                   ("WP-Deckungsanteil", f"{T.f(g['deckung'] * 100, 1)} %", f"VDI 4650 ({'Sole' if r['waermequelle'] == 'sole' else 'Luft'}/Wasser, parallel)", "ok" if g["deckung"] >= 0.98 else "warn")]
        spalten = st.columns(3)
        for i, (a, b, c, klasse) in enumerate(ks):
            tip = T.GLOSSAR.get(T.KPI_GLOSSAR.get(a, ""), "").replace("'", "&#39;")
            spalten[i % 3].markdown(f"<div class='kpi {klasse}' title='{tip}'><div class='t'>{a}{' ⓘ' if tip else ''}</div><div class='v'>{b}</div>"
                                    f"<div class='s'>{c}</div></div>", unsafe_allow_html=True)

        if g:
            k = KAT["geraete"].get(g["geraet"], {})
            s = D.serie(g["serie"])
            bilder = [(KAT.get("bilder", {}).get(g["geraet"]), g["geraet"]), ((ie or {}).get("bild"), (ie or {}).get("typ"))]
            bilder = [(D.DATEN / "bilder" / f"{b_}.jpg", t_) for b_, t_ in bilder if b_ and (D.DATEN / "bilder" / f"{b_}.jpg").exists()]
            if bilder:
                st.image([str(b_) for b_, _ in bilder], caption=[t_ for _, t_ in bilder], width=150)
            st.subheader(("{} × ".format(g["n"]) if g["n"] > 1 else "") + g["geraet"])
            st.caption(f"{s['name']} · {s['bauart']} · {('aus MFH-Musterlösung' if r.get('mfh_wp') else 'Empfehlung') if not E['auswahl']['geraet'] else 'manuell gewählt'}"
                       + (f" · mit {ie['typ']} ({ie['art']})" if ie else ""))
            d = st.columns(4)
            d[0].metric("Bestell-Nr. Außeneinheit", k.get("artnr") or "–")
            d[1].metric("Bestell-Nr. Inneneinheit", (ie or {}).get("artnr") or "–")
            d[2].metric(f"Max. Leistung {'B0' if r['waermequelle'] == 'sole' else 'A-7'}/W{T.f(r['vl'], 0)}", f"{T.f(g.get('q_a7'), 2)} kW")
            d[3].metric("Taktgrenze", f"≈ {T.ft(g['taktgrenze'])} °C" if g.get("taktgrenze") is not None else "–")
            st.caption(f"SCOP 35/55 °C: {T.f(k.get('scop35'), 2)} / {T.f(k.get('scop55'), 2)} · Schallleistung ErP: "
                       f"{k.get('lw_db', '–')} dB(A) · {k.get('masse', '')} · UVP (intern): {T.euro(k['uvp'] * g['n']) if k.get('uvp') else '–'}"
                       + (f" + {T.euro(ie['uvp'])}" if ie and ie.get("uvp") else ""))

        if r.get("kennlinien"):
            kl = r["kennlinien"]
            fig = go.Figure()
            for d_ in DATEN["geraete"]:
                if d_["serie"] == g["serie"] and d_["id"] != g["geraet"]:
                    kk = R.kurve_bei_vl(d_["max"], r["vl"])
                    if kk:
                        fig.add_scatter(x=kl["t"], y=R.werte_im_bereich(kk, kl["t"], g["n"]), name=d_["kurz"], mode="lines",
                                        line=dict(color="#a0aab5", width=1, dash="dot"))
            if kl["min"]:
                fig.add_scatter(x=kl["t"], y=kl["min"], name="Mindestleistung (1 Gerät)", mode="lines", line=dict(color=BLAU, dash="dash"))
            fig.add_scatter(x=kl["t"], y=kl["last"], name="Gebäudekennlinie", mode="lines", line=dict(color="#141e29", width=2.5))
            fig.add_scatter(x=kl["t"], y=kl["max"], name=g["geraet"] + " (max.)", mode="lines", line=dict(color=BLAU, width=3.5))
            if g["bivalenz_art"] == "punkt":
                qb = R.last(g["bivalenz"], r["qh"] + r["qsperr"], r["qtw"], r["nat"], r["heizgrenze"])
                fig.add_scatter(x=[g["bivalenz"]], y=[qb], mode="markers+text", text=[f"Bivalenzpunkt {T.ft(g['bivalenz'])} °C"],
                                textposition="bottom left", marker=dict(size=11, color=BLAU), showlegend=False)
            fig.add_vline(x=r["nat"], line_dash="dot", line_color="#78889a", annotation_text=f"θe {T.ft(r['nat'])} °C")
            # Ablese-Linie (verschiebbar, Standard θe) – wie im HTML, nur Veranschaulichung
            tm_ = (E.get("ansicht") or {}).get("t_marke")
            ab_ = R.ablesen(r, tm_)
            if ab_:
                fig.add_vline(x=ab_["t"], line_color=VIOLETT, line_width=2, annotation_text=f"Ablesen {T.ft(ab_['t'])} °C",
                              annotation_font_color=VIOLETT, annotation_position="top left")
                fig.add_scatter(x=[ab_["t"]] * (2 if ab_["wp_max"] is not None else 1),
                                y=[ab_["bedarf"]] + ([ab_["wp_max"]] if ab_["wp_max"] is not None else []), mode="markers",
                                marker=dict(size=9, color=["#141e29", BLAU][:2 if ab_["wp_max"] is not None else 1]), showlegend=False)
            if g["bivalenz_art"] == "punkt":
                fig.add_vrect(x0=g["bivalenz"] - 0.8, x1=g["bivalenz"] + 0.8, fillcolor="#f28c28", opacity=0.14, line_width=0)
            fig.update_layout(height=420, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="Außentemperatur in °C",
                              yaxis_title="Heizleistung in kW", yaxis_rangemode="tozero", legend=dict(orientation="h", y=1.12), template="plotly_white")
            st.plotly_chart(fig, width="stretch")
            if ab_:
                c_s, c_b = st.columns([4, 1])
                t_neu = c_s.slider("Ablese-Linie bei Außentemperatur [°C]", float(kl["t"][0]), float(kl["t"][-1]), float(ab_["t"]), 0.5,
                                   key="t_marke", help="Zur Veranschaulichung verschiebbar (z. B. −5 °C oder tiefer, je nach Gebiet) – "
                                                       "ändert die Auslegung nicht. Standard: Norm-Außentemperatur θe.")
                if c_b.button("auf θe", key="t_marke_nat"):
                    E.setdefault("ansicht", {})["t_marke"] = None
                    ss.pop("t_marke", None)
                    st.rerun()
                if abs(t_neu - ab_["t"]) > 1e-9:
                    E.setdefault("ansicht", {})["t_marke"] = t_neu
                    st.rerun()
                st.caption(f"Bei {T.ft(ab_['t'])} °C{' (θe)' if abs(ab_['t'] - r['nat']) < 1e-9 else ''}: Bedarf {T.f(ab_['bedarf'], 1)} kW · "
                           f"Wärmepumpe max. {T.f(ab_['wp_max'], 1) + ' kW' if ab_['wp_max'] is not None else '–'}"
                           + (f" (min. {T.f(ab_['wp_min'], 1)} kW je Gerät)" if ab_["wp_min"] is not None else "") + " · "
                           + (f"Heizstab {T.f(ab_['heizstab'], 1)} kW" if ab_["heizstab"] else
                              ("Wärmepumpe deckt allein" if ab_["wp_max"] is not None else "außerhalb der Herstellerdaten")))
            st.caption(T.min_hinweis(r))

    with t_leis:
        hkv = r.get("heizkurve")
        if hkv:
            st.markdown("**Heizkurve** – Vorlauf- und Rücklauftemperatur über der Außentemperatur (DIN EN 442)")
            fh = go.Figure()
            fh.add_scatter(x=hkv["t"], y=hkv["vl"], name="Vorlauf", mode="lines", line=dict(color=ROT, width=3))
            fh.add_scatter(x=hkv["t"], y=hkv["rl"], name="Rücklauf", mode="lines", line=dict(color=BLAU, width=2, dash="dash"))
            pk = hkv["punkte"]
            fh.add_scatter(x=[float(t_) for t_ in pk], y=list(pk.values()), mode="markers+text", showlegend=False,
                           text=[f"A{t_}: {T.f(v_, 1)} °C" for t_, v_ in pk.items()], textposition="top right", marker=dict(size=9, color=ROT))
            if g and g.get("vl_max_geraet"):
                fh.add_hline(y=g["vl_max_geraet"], line_dash="dash", line_color="#78889a",
                             annotation_text=f"max. Vorlauf WP {T.f(g['vl_max_geraet'], 0)} °C")
            fh.update_layout(height=280, margin=dict(l=10, r=10, t=30, b=10), xaxis_title="Außentemperatur in °C",
                             yaxis_title="Temperatur in °C", legend=dict(orientation="h", y=1.15), template="plotly_white")
            st.plotly_chart(fh, width="stretch")
            st.caption(f"Maßgebend: {T.HK_TYP.get(hkv['typ'], hkv['typ'])} (Exponent n = {T.f(hkv['exponent'], 1)}, Spreizung "
                       f"{T.f(hkv['spreizung'], 0)} K bei θe) · {T.f(r['vl'], 0)} °C Vorlauf bei θe {T.ft(r['nat'])} °C bis zur Heizgrenze "
                       f"{T.ft(r['heizgrenze'])} °C. Bei milderen Außentemperaturen sinkt der Vorlauf – die Wärmepumpe arbeitet dann effizienter "
                       f"und mit mehr Leistung als im Diagramm oben (dort konstant {T.f(r['vl'], 0)} °C wie Excel-Werkzeug).")

        if r.get("eheizer"):
            st.markdown(f"**E-Heizer je Baugröße** – QGES {T.f(r['qges'], 2)} kW − Heizleistung bei θe {T.ft(r['nat'])} °C "
                        f"und {T.f(r['vl'], 0)} °C Vorlauf (wie Excel-Werkzeug)")
            st.dataframe([{"Bild": D.bild_uri(KAT.get("bilder", {}).get(x["geraet"])),
                           "Wärmepumpe": (f"{x['n']} × " if x["n"] > 1 else "") + x["geraet"] + (" (gewählt)" if x["geraet"] == g["geraet"] else ""),
                           f"Leistung bei θe": x["text_q"], "E-Heizer": x["text_eh"], "in Watt": x["text_w"], "Bewertung": x["bewertung"]}
                          for x in T.eheizer_zeilen(r)], hide_index=True, width="stretch",
                         column_config={"Bild": st.column_config.ImageColumn("", width="small")})
            vb = r.get("vdi_bivalenz")
            tab = {"ϑBiv in °C": ["Leistungsanteil μ", "αH,a bivalent-parallel", "αH,a bivalent-alternativ"]}
            for i_, t_ in enumerate(R.VDI_BIV_T):
                tab[("+" if t_ > 0 else "") + str(t_)] = [R.VDI_BIV_MU[i_], R.VDI_BIV_PAR[i_], R.VDI_BIV_ALT[i_]]
            naechst = min(R.VDI_BIV_T, key=lambda t_: abs(t_ - vb["t_biv"])) if vb else None
            st.markdown("**Deckungsanteil nach Bivalenzpunkt** (DIN V 4701-10 / VDI 4650)")
            import pandas as pd
            df = pd.DataFrame(tab)
            spalte = ("+" if naechst and naechst > 0 else "") + str(naechst) if vb else None
            st.dataframe(df.style.format({c_: "{:.2f}" for c_ in df.columns[1:]}).set_properties(
                subset=[spalte] if spalte else [], **{"background-color": "#005691", "color": "white", "font-weight": "bold"}),
                hide_index=True, width="stretch")
            if vb:
                st.caption(f"Bivalenzpunkt {T.ft(g['bivalenz'])} °C: αH,a parallel ≈ {T.f(vb['alpha_parallel'], 2)}, "
                           f"alternativ ≈ {T.f(vb['alpha_alternativ'], 2)} (linear interpoliert).")

        en = r.get("energie")
        if en:
            st.markdown("**Jahresbilanz (Schätzung)**")
            if True:
                c = st.columns(4)
                c[0].metric("Jahreswärme Heizung + WW", f"{T.f(en['waerme_kwh'], 0)} kWh/a")
                if en.get("scop"):
                    c[1].metric("Strom Wärmepumpe", f"{T.f(en['strom_wp_kwh'], 0)} kWh/a", help=f"SCOP ≈ {T.f(en['scop'], 2)}")
                    c[2].metric("Strom Heizstab", f"{T.f(en['strom_heizstab_kwh'], 0)} kWh/a")
                    c[3].metric("Umweltwärme", f"{T.f(en['umwelt_kwh'], 0)} kWh/a")

    with t_ger:
        st.markdown("**Mögliche Wärmepumpen** – kleinste passende Größe je Gerät (★ kleinste der Baureihe)")
        emp = set(r["empfehlung_je_serie"])
        zeilen = []
        # gewählte Baureihe zuerst, darunter die Alternativen aus anderen Baureihen (wie index.html)
        liste = sorted(r["kandidaten"], key=lambda c: 0 if g and c["serie"] == g["serie"] else 1)
        for c in liste:
            zeilen.append({"": "🟢" if c["ok"] else ("⚪" if not c["moeglich"] else "🔴"),
                           "Gruppe": "gewählte Baureihe" if g and c["serie"] == g["serie"] else "Alternative",
                           "Bild": D.bild_uri(KAT.get("bilder", {}).get(c["geraet"])),
                           "Wärmepumpe": c["geraet"] + (" ★" if f"{c['geraet']}|{c['n']}" in emp else ""), "Anz.": c["n"],
                           f"{'B0' if r['waermequelle'] == 'sole' else 'A-7'}/W{T.f(r['vl'], 0)} [kW]": round(c["q_a7"], 2) if c["moeglich"] else None,
                           "bei θe [kW]": round(c["q_nat"], 2) if c["moeglich"] else None,
                           "Abdeckung [%]": round(c["abdeckung"] * 100) if c["moeglich"] else None,
                           "Bivalenzpunkt": T.biv_text(c), "Heizstab [kW]": round(c["heizstab_kw"], 1) if c["moeglich"] else None,
                           "Deckung [%]": round(c["deckung"] * 100, 1) if c["moeglich"] else None,
                           "UVP [€]": KAT["geraete"].get(c["geraet"], {}).get("uvp", 0) * c["n"] or None,
                           "Hinweis": c["grund"] or ("überdimensioniert" if c.get("ueberdimensioniert") else "")})
        st.dataframe(zeilen, hide_index=True, width="stretch", column_config={"Bild": st.column_config.ImageColumn("", width="small")})
        st.caption("A-7/W.. = Heizleistung bei −7 °C Außenluft und Auslegungsvorlauf (Prüfpunkt nach EN 14511, Bezug der Mindestleistung); "
                   "B0/W.. bei Sole/Wasser = Sole 0 °C. θe = Norm-Außentemperatur.")

    with t_hyd:
        hydraulik_bereich(r, E)
        if g:
            st.markdown("**Vereinfachte Prinzipskizze** – Übersicht zur Auslegung")
            svg = S.schema_svg(r, ie, T.heizkreis_liste(E), S.FARBEN_DRUCK).replace('width="900" height="470"', 'width="100%"')
            st.markdown("<div style='background:#fff;border:1px solid #d3dce5;border-radius:12px;padding:8px'>" + svg + "</div>",
                        unsafe_allow_html=True)
            st.caption("Vereinfachte Prinzipdarstellung der Auslegung. Maßgeblich ist die oben ausgewählte Hydraulik der Musterlösung.")
        kacheln = T.anbindung(E, r)
        if kacheln:
            st.markdown("**Warmwasser & Anbindung**")
            sp_ = st.columns(len(kacheln) if len(kacheln) <= 4 else 3)
            for i_, (a_, b_, c_) in enumerate(kacheln):
                sp_[i_ % len(sp_)].markdown(f"<div class='kpi'><div class='t'>{a_}</div><div class='v'>{b_}</div><div class='s'>{c_}</div></div>",
                                            unsafe_allow_html=True)
    with t_best:
        # ---- MFH-Musterlösung – wie mfhHtml() in index.html
        if r["mfh"]:
            mfh_bereich(r, E)

        # ---- Passende Systempakete (BOPA) – wie index.html
        if g and not r["mfh"]:
            PK = D.pakete()
            st.markdown("**Passende Systempakete (BOPA)** – Komplettpaket mit Speicher und Zubehör · Preisvorteil 6 %")
            if g["n"] > 1:
                st.caption("Für Kaskaden gibt es keine Komplettpakete – Zubehör und Speicher in der Planung festlegen.")
            else:
                pl = T.pakete_fuer(r, ie, PK)
                if not pl:
                    st.caption(f"Für {g['geraet']} sind im Produktkatalog keine Systempakete aufgeführt.")
                if pl and r["tww"]["system"] == "friwa" and r["tww"]["aktiv"]:
                    st.caption("Hinweis: Die Pakete enthalten Warmwasserspeicher – für eine Frischwasserstation Paket ohne Speicher wählen.")
                titel = []
                for p_ in pl:
                    if p_["titel"] not in titel:
                        titel.append(p_["titel"])
                for t_ in titel:
                    gruppe = [p_ for p_ in pl if p_["titel"] == t_]
                    st.markdown(f"<div style='font-size:12px;font-weight:700;color:#4a5866;text-transform:uppercase;margin-top:6px'>{t_}</div>",
                                unsafe_allow_html=True)
                    st.dataframe([{"Paket": p_["paket"] + (" ★" if p_["passt"] else ""), "Variante": p_["variante"],
                                   "WW-Speicher [l]": p_["ww_l"], "Puffer [l]": p_["puffer_l"], "Bestell-Nr.": p_["artnr"],
                                   "UVP [€]": p_["uvp"]} for p_ in gruppe], hide_index=True, width="stretch")
                    with st.expander("Paketinhalt"):
                        st.markdown("\n".join("- " + x_ for x_ in gruppe[0]["inhalt"]))
                if pl:
                    st.caption(f"★ passt zur gewählten Inneneinheit{' (' + ie['typ'] + ')' if ie else ''}. "
                               "Quelle: Produktkatalog Klima-, Lüftungs- und Wärmepumpen-Sortiment, März 2026.")
                zub = T.zubehoer_fuer(r, PK)
                if zub:
                    with st.expander(f"Empfohlenes Zubehör zur Baureihe ({len(zub)})"):
                        st.dataframe([{"Zubehör": z_["text"], "Bestell-Nr.": z_["artnr"], "UVP [€]": z_["uvp"]} for z_ in zub],
                                     hide_index=True, width="stretch")
                        hk_ = T.heizkreis_liste(E)
                        st.caption(f"Heizkreise laut Eingabe: {sum(not x['gemischt'] for x in hk_)} ungemischt, "
                                   f"{sum(x['gemischt'] for x in hk_)} gemischt – Heizkreispaket BOPA HK HP je Heizkreis berücksichtigen.")

        if not r.get("mfh") and not g:
            st.caption("Heizlast eingeben – dann erscheinen hier die passenden Systempakete.")
    with t_rech:
        st.markdown("**So rechnet die Schnellauslegung**")
        st.markdown("\n".join(f"{i_ + 1}. **{a_}** – {b_}" for i_, (a_, b_) in enumerate(T.RECHENWEG)))
        st.markdown("**Herleitung Heizlast**")
        if True:
            st.table([{"Größe": a, "Formel": b, "Wert": c} for a, b, c in T.herleitung(E, r)])

    pdf_ = B.pdf_bytes(E, r, DATEN, KAT)
    c_p, c_m = st.columns(2)
    c_p.download_button("📄 Auslegung als PDF", pdf_, f"WP-Auslegung_{name}{'_intern' if E['preise_drucken'] else ''}.pdf",
                        "application/pdf", type="primary", width="stretch")
    c_m.download_button("🗂 Projektmappe (.zip)", X.mappe_bytes(E, r, KAT, pdf_), f"WP-Auslegung_{X.dateiname(E)}.zip",
                        "application/zip", width="stretch", help="Projektdatei, Kurzbericht, PDF der Auslegung und Bild der gewählten Hydraulik")
    st.caption(f"Entwickelt von Daniel Sommer · HC/SDE3-PSD · Leistungsdaten: {DATEN['quelle']} · Katalog: Gesamtkatalog März 2026 · "
               "Ergebnis ersetzt keine Fachplanung.")
