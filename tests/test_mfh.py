"""MFH-Musterlösungen: Daten, Auswahl und Gleichheit Python ↔ HTML (node)."""
from __future__ import annotations

import copy
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from wp import daten as D
from wp import mfh as M
from wp import projekt as P
from wp import rechnen as R

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent
MD = D.mfh()


def mfh_eingabe(typ="sanierung", we=8, ww="friwa", auslegung="monoenergetisch", **aend):
    e = P.neu()
    e["gebaeude"]["typ"] = typ
    e["klima"]["heizgrenze"] = 12.0 if typ == "neubau" else 15.0
    e["mfh"].update(art="mfh", we=we, ww=ww)
    for k in ("mfh.art", "gebaeude.typ"):
        M.eingaben_folgen(e, k)
    e["auslegung"] = auslegung
    for k, v in aend.items():
        ziel = e
        teile = k.split("__")
        for t in teile[:-1]:
            ziel = ziel[t]
        ziel[teile[-1]] = v
    return e


def faelle():
    out = []
    for typ in ("sanierung", "neubau"):
        for ww in ("friwa", "hiu", "dle", "speicher"):
            for we in (4, 8, 12, 16, 30):
                out.append(mfh_eingabe(typ, we, ww))
        for we in (6, 8, 14, 16):
            out.append(mfh_eingabe(typ, we, "friwa", "hybrid"))
    out.append(mfh_eingabe("sanierung", 10, "dle", mfh__zelle="B-mono-dle-14"))
    out.append(mfh_eingabe("neubau", 10, "dle", heizlast__spez_w_m2=60))
    out.append(mfh_eingabe("sanierung", 12, "friwa", vl=35.0, klima__nat=-16.0))
    return out


def vorschlag(e):
    r = R.rechne(e, D.geraete(), D.katalog())
    return M.vorschlag(e, r, MD, D.geraete(), D.katalog())



def test_matrix_vollstaendig():
    ids = [z["id"] for z in MD["zellen"]]
    assert len(ids) == len(set(ids)) == 62
    geraete = {g["id"] for g in D.geraete()["geraete"]}
    for z in MD["zellen"]:
        assert z["geraet"] in geraete, z
        assert "vorlage" not in z and "hydraulik" not in z



def test_auswahl():
    v = vorschlag(mfh_eingabe("neubau", 10, "dle"))
    assert [a["zelle"]["id"] for a in v["auswahl"]] == ["N-mono-dle-10"]
    a = v["auswahl"][0]
    assert a["pruefung"]["ok"]
    # 12 WE Bestand zentral: zwei Varianten (CS5001-Kaskade, CS8800-Kaskade)
    v = vorschlag(mfh_eingabe("sanierung", 12, "friwa"))
    assert {a["zelle"]["id"] for a in v["auswahl"]} == {"B-mono-friwa-12-a", "B-mono-friwa-12-b"}
    # über den Mustern
    v = vorschlag(mfh_eingabe("sanierung", 30, "dle"))
    assert v["ausserhalb"] and v["auswahl"][0]["zelle"]["we"] == 16
    # höhere Heizlast als im Muster -> größere Musterlösung
    v = vorschlag(mfh_eingabe("neubau", 10, "dle", heizlast__spez_w_m2=60))
    assert v["auswahl"][0]["zelle"]["we"] > 10
    assert vorschlag(P.neu()) is None


def test_eingaben_folgen():
    e = mfh_eingabe("sanierung", 6, "dle")
    assert e["tww"]["aktiv"] is False and e["tww"]["personen"] == 21 and e["heizlast"]["flaeche_m2"] == 480
    assert e["heizlast"]["methode"] == "flaeche" and e["heizlast"]["spez_w_m2"] == 45
    e["mfh"]["ww"] = "hiu"
    M.eingaben_folgen(e, "mfh.ww")
    assert e["tww"]["aktiv"] is True and e["tww"]["system"] == "friwa"




@pytest.mark.skipif(shutil.which("node") is None, reason="node nicht installiert")
def test_mfh_python_gleich_html(tmp_path):
    ein = faelle()
    folgen = []
    for k in ("mfh.art", "mfh.we", "mfh.ww", "gebaeude.typ"):
        e = P.neu()
        e["mfh"].update(art="mfh", we=7, ww="dle")
        folgen.append([e, k])
    datei = tmp_path / "faelle.json"
    datei.write_text(json.dumps({"eingaben": ein, "folgen": folgen}, ensure_ascii=False), encoding="utf-8")
    js = json.loads(subprocess.run(["node", str(HIER / "mfh_html.js"), str(ROOT / "index.html"), str(datei)],
                                   capture_output=True, text=True, check=True).stdout)
    from test_rechnen import gleich
    for e, j in zip(ein, js["vorschlag"]):
        gleich(vorschlag(copy.deepcopy(e)), j)
    for e, j in zip(ein, js["rechne"]):
        r = M.rechne(copy.deepcopy(e), D.geraete(), D.katalog(), MD)
        assert ([r["gewaehlt"]["geraet"], r["gewaehlt"]["n"]] if r["gewaehlt"] else None) == j["g"]
        assert r["mfh_wp"] == j["wp"]
    for (e, k), j in zip(folgen, js["folgen"]):
        e = copy.deepcopy(e)
        M.eingaben_folgen(e, k)
        gleich(e, j)



def test_auto_waehlt_muster_wp():
    e = mfh_eingabe("neubau", 10, "dle")
    r = M.rechne(e, D.geraete(), D.katalog(), MD)
    assert r["mfh_wp"] and r["gewaehlt"]["geraet"] == "CS8800iAW 11 O-T" and r["gewaehlt"]["n"] == 2
    e["auswahl"].update(geraet="CS5001 AW22", anzahl=1)
    r = M.rechne(e, D.geraete(), D.katalog(), MD)
    assert not r["mfh_wp"] and r["gewaehlt"]["geraet"] == "CS5001 AW22"
