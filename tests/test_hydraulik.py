"""Hydraulik-Auswahl aus den Musterlösungen (ZIP-Daten): Bibliothek, Auswahl, Übernahme der Excel-Auslegung, Python = HTML."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from test_mfh import mfh_eingabe
from test_rechnen import gleich
from wp import daten as D
from wp import hydraulik as HY
from wp import mfh as M
from wp import projekt as P

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent
LIB = D.hydraulik()


def rechne(e):
    return M.rechne(e, D.geraete(), D.katalog(), D.mfh())


def test_bibliothek_vollstaendig():
    ids = {s["id"] for s in LIB["schemata"]}
    assert len(ids) == 12
    for s in LIB["schemata"]:
        assert D.hydraulik_bild(s["id"]).exists(), s["id"]
        assert s["serien"] and s["anzahl"] and s["ww"] and s["system"] and s["loesungen"]
    loes = {L["id"]: L for L in LIB["loesungen"]}
    for s in LIB["schemata"]:
        assert all(s["id"] in loes[n]["schemata"] for n in s["loesungen"])
    assert sum(1 for L in LIB["loesungen"] if L["auslegung"]) >= 40
    assert not any(L["system"] == "fernwaerme" for L in LIB["loesungen"])


def test_auswahl_passend_und_manuell():
    e = mfh_eingabe("neubau", 10, "dle")
    r = rechne(e)
    h = HY.gewaehlt(e, r, LIB)
    assert h and h["passend"] and not h["manuell"] and r["gewaehlt"]["n"] == 2
    e["hydraulik"]["schema"] = "CS8800_AWMB_WPS_1ug"
    h = HY.gewaehlt(e, r, LIB)
    assert h["manuell"] and not h["passend"] and not h["passt"]["anzahl"]


def test_ohne_passende_hydraulik_vorlage_mit_anpassungen():
    """7 WE mit Speicher und CS5001: keine Musterlösungs-Hydraulik passt – ähnlichste als Vorlage, Anpassungen und Hinweise."""
    e = mfh_eingabe("sanierung", 7, "speicher")
    e["auswahl"].update(geraet="CS5001 AW22", anzahl=1)
    r = rechne(e)
    h = HY.gewaehlt(e, r, LIB)
    assert h and not h["passend"] and not h["manuell"] and h["stufe"] == "vorlage" and h["passt"]["serie"]
    assert any(t.startswith("Warmwasser: Warmwasserspeicher") for t in h["anpassen"])
    hw = HY.hinweise(e, r, LIB)
    assert any("NL 4" in t for t in hw) and any("keine Hydraulikzeichnung" in t for t in hw)
    e = mfh_eingabe("neubau", 10, "dle")
    r = rechne(e)
    assert HY.gewaehlt(e, r, LIB)["anpassen"] == [] and HY.hinweise(e, r, LIB) == []


def test_excel_auslegung_uebernehmen():
    """Musterlösung 2.1.3.6 (14 WE, 2 × CS8800 AW15, 35 °C, GEG-Hybrid): Rechenkern bestätigt die Excel-Auslegung."""
    L = next(L for L in LIB["loesungen"] if L["id"] == "2.1.3.6")
    e = HY.uebernehmen(P.neu(), L)
    r = rechne(e)
    assert abs(r["qges"] - L["auslegung"]["qges"]) < 0.05
    assert abs(r["mindestleistung"] - L["auslegung"]["mindest_kw"]) < 0.05
    g = r["gewaehlt"]
    assert g["geraet"] == "CS8800iAW 15 O-T" and g["n"] == 2 and g["ok"]
    h = HY.gewaehlt(e, r, LIB)
    assert h["id"] == "14WE_2CS8800_BP500-7EM" and h["passend"]   # Anlagenart aus der Musterlösung, Kriterium aus Excel


def faelle():
    out = [mfh_eingabe(t, we, ww, a) for t in ("sanierung", "neubau") for ww in ("friwa", "hiu", "dle", "speicher")
           for we in (4, 10, 16) for a in ("monoenergetisch", "hybrid")]
    e = mfh_eingabe("neubau", 10, "dle")
    e["hydraulik"]["schema"] = "6721896658"
    return out + [e] + [HY.uebernehmen(P.neu(), L) for L in LIB["loesungen"] if L["auslegung"]][:12]


@pytest.mark.skipif(shutil.which("node") is None, reason="node nicht installiert")
def test_hydraulik_python_gleich_html(tmp_path):
    ein = faelle()
    loes = [L["id"] for L in LIB["loesungen"] if L["auslegung"]]
    datei = tmp_path / "ein.json"
    datei.write_text(json.dumps({"eingaben": ein, "loesungen": loes, "neu": P.neu()}, ensure_ascii=False), encoding="utf-8")
    js = json.loads(subprocess.run(["node", str(HIER / "hyd_html.js"), str(ROOT / "index.html"), str(datei)],
                                   capture_output=True, text=True, check=True).stdout)
    for e, j in zip(ein, js["auswahl"]):
        r = rechne(e)
        gleich({"schemata": HY.schemata(e, r, LIB), "gewaehlt": HY.gewaehlt(e, r, LIB), "loesungen": [L["id"] for L in HY.loesungen(e, r, LIB)],
               "hinweise": HY.hinweise(e, r, LIB)}, j)
    for nr, j in zip(loes, js["uebernehmen"]):
        gleich(HY.uebernehmen(P.neu(), next(L for L in LIB["loesungen"] if L["id"] == nr)), j)
