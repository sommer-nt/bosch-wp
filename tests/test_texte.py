"""Erklärungen: Klartext-Zusammenfassung und Glossar gleich in Python und HTML (node)."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from test_mfh import mfh_eingabe
from test_rechnen import szenarien
from wp import daten as D
from wp import mfh as M
from wp import hydraulik as HY
from wp import texte as T

HIER = Path(__file__).resolve().parent
ROOT = HIER.parent


def faelle():
    from wp import projekt as P
    return [P.neu()] + [s["eingaben"] if "eingaben" in s else s for s in szenarien()] + [
        mfh_eingabe("neubau", 10, "dle"), mfh_eingabe("sanierung", 12, "friwa"), mfh_eingabe("sanierung", 8, "friwa", "hybrid")]


def klartext(e):
    r = M.rechne(e, D.geraete(), D.katalog(), D.mfh())
    return T.klartext(e, r, D.katalog())


def test_klartext_inhalt():
    k = klartext(mfh_eingabe("neubau", 10, "dle"))
    texte = " ".join(x["text"] for x in k)
    assert "Aus der MFH-Musterlösung: **2 × CS8800iAW 11 O-T**" in texte and "4000194338" in texte
    assert all(x["status"] in T.STATUS_ICON for x in k)


@pytest.mark.skipif(shutil.which("node") is None, reason="node nicht installiert")
def test_klartext_python_gleich_html(tmp_path):
    ein = faelle()
    datei = tmp_path / "ein.json"
    datei.write_text(json.dumps(ein, ensure_ascii=False), encoding="utf-8")
    js = json.loads(subprocess.run(["node", str(HIER / "texte_html.js"), str(ROOT / "index.html"), str(datei)],
                                   capture_output=True, text=True, check=True).stdout)
    assert js["glossar"] == T.GLOSSAR
    for e, j in zip(ein, js["klartext"]):
        assert klartext(e) == j


def schemata(e):
    r = M.rechne(e, D.geraete(), D.katalog(), D.mfh())
    return HY.schemata(e, r, D.hydraulik(), T.inneneinheit(e, r, D.katalog()))


def test_hydraulikschemata_passen():
    s = schemata(mfh_eingabe("sanierung", 12, "hiu"))
    assert s and s[0]["nr"] == "6721896998"   # 3x Compress 8800iAW mit Flow 7002 HPS
    s = schemata(mfh_eingabe("neubau", 16, "dle"))
    assert s[0]["titel"].startswith("2xCompress 8800iAW")


@pytest.mark.skipif(shutil.which("node") is None, reason="node nicht installiert")
def test_hydraulik_python_gleich_html(tmp_path):
    ein = []
    for e in faelle():
        r = M.rechne(e, D.geraete(), D.katalog(), D.mfh())
        ein.append([e, T.inneneinheit(e, r, D.katalog())])
    datei = tmp_path / "ein.json"
    datei.write_text(json.dumps(ein, ensure_ascii=False), encoding="utf-8")
    js = json.loads(subprocess.run(["node", str(HIER / "hdb_html.js"), str(ROOT / "index.html"), str(datei)],
                                   capture_output=True, text=True, check=True).stdout)
    for (e, _), j in zip(ein, js):
        assert schemata(e) == j


def test_projektmappe():
    import io
    import zipfile
    from wp import export as X
    e = mfh_eingabe("neubau", 10, "dle")
    e["projekt"]["name"] = "Muster MFH"
    r = M.rechne(e, D.geraete(), D.katalog(), D.mfh())
    z = zipfile.ZipFile(io.BytesIO(X.mappe_bytes(e, r, D.katalog(), b"%PDF-1.4")))
    namen = set(z.namelist())
    assert namen == {"WP-Auslegung_Muster_MFH.json", "Kurzbericht.txt", "Dokumentation_Bestellvorschlag.txt", "Rapida-Import_4000194338.csv", "Bestellvorschlag_4000194338.d83",
                     "Bestellvorschlag_4000194338.csv", "WP-Auslegung_Muster_MFH.pdf"}
    assert "Aus der MFH-Musterlösung" in z.read("Kurzbericht.txt").decode("utf-8")


def doku(e):
    r = M.rechne(e, D.geraete(), D.katalog(), D.mfh())
    return M.dokumentation(e, r, D.mfh(), D.hydraulik(), T.inneneinheit(e, r, D.katalog()))


def mfh_faelle():
    out = []
    for typ in ("sanierung", "neubau"):
        for ww in ("friwa", "hiu", "dle", "speicher"):
            for we in (4, 8, 10, 12, 16):
                out.append(mfh_eingabe(typ, we, ww))
        for we in (6, 8, 14):
            out.append(mfh_eingabe(typ, we, "dle", "hybrid"))
    e = mfh_eingabe("neubau", 10, "dle")
    e["auswahl"].update(geraet="CS5001 AW22", anzahl=1)
    return out + [e]


def test_dokumentation_valide():
    d = doku(mfh_eingabe("neubau", 10, "dle"))
    assert d["valide"] and d["vorlage"] == "4000194338" and d["schema"]["nr"] == "6721897067"
    assert doku(mfh_eingabe("sanierung", 4, "dle"))["schema"]["nr"] == "6721896965"   # aus den Unterlagen der Musterlösung
    e = mfh_eingabe("neubau", 10, "dle")
    e["auswahl"].update(geraet="CS5001 AW22", anzahl=1)
    assert not doku(e)["valide"]   # abweichende Wärmepumpe


@pytest.mark.skipif(shutil.which("node") is None, reason="node nicht installiert")
def test_dokumentation_python_gleich_html(tmp_path):
    ein = []
    for e in mfh_faelle():
        r = M.rechne(e, D.geraete(), D.katalog(), D.mfh())
        ein.append([e, T.inneneinheit(e, r, D.katalog())])
    datei = tmp_path / "ein.json"
    datei.write_text(json.dumps(ein, ensure_ascii=False), encoding="utf-8")
    js = json.loads(subprocess.run(["node", str(HIER / "doku_html.js"), str(ROOT / "index.html"), str(datei)],
                                   capture_output=True, text=True, check=True).stdout)
    for (e, _), j in zip(ein, js):
        assert doku(e) == j
