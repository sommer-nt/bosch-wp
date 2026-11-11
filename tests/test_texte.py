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
    assert "Aus der MFH-Musterlösung: **2 × CS8800iAW 11 O-T**" in texte and "MFH-Musterlösung 10 WE" in texte
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



def test_projektmappe():
    import io
    import zipfile
    from wp import export as X
    e = mfh_eingabe("neubau", 10, "dle")
    e["projekt"]["name"] = "Muster MFH"
    r = M.rechne(e, D.geraete(), D.katalog(), D.mfh())
    z = zipfile.ZipFile(io.BytesIO(X.mappe_bytes(e, r, D.katalog(), b"%PDF-1.4")))
    h = HY.gewaehlt(e, r, D.hydraulik())
    assert set(z.namelist()) == {"WP-Auslegung_Muster_MFH.json", "Kurzbericht.txt", "WP-Auslegung_Muster_MFH.pdf", f"Hydraulik_{h['id']}.jpg"}
    assert "Hydraulik" in z.read("Kurzbericht.txt").decode("utf-8")
