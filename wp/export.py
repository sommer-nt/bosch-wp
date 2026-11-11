"""Export: Kurzbericht (Text) und Projektmappe (.zip) – wie kurzbericht()/exportMappe() in index.html.

Die Projektmappe enthält Projektdatei (.json), Kurzbericht, bei MFH-Musterlösungen den Bestellvorschlag als GAEB (.d83)
und CSV und in der Streamlit-Version zusätzlich das PDF der Auslegung.
"""
from __future__ import annotations

import io
import zipfile

from . import daten as D
from . import hydraulik as HY
from . import mfh as M
from . import projekt as P
from . import texte as T


def dateiname(e: dict) -> str:
    import re
    return re.sub(r"[^\wäöüÄÖÜß-]+", "_", e["projekt"].get("name") or "Projekt")


def bestell_vorlage(r: dict) -> dict | None:
    v = r.get("mfh")
    if not v or not v["auswahl"]:
        return None
    a = next((a for a in v["auswahl"] if a["zelle"].get("vorlage")), None)
    return D.mfh()["vorlagen"].get(a["zelle"]["vorlage"]) if a else None


def kurzbericht(e: dict, r: dict, katalog: dict) -> str:
    z = ["Bosch WP-Schnellauslegung – " + (e["projekt"].get("name") or "Projekt ohne Namen"),
         "Entwickelt von Daniel Sommer · HC/SDE3-PSD", "", "Auf einen Blick"]
    z += ["- " + x["text"].replace("**", "") for x in T.klartext(e, r, katalog)]
    if r.get("gewaehlt"):
        hd = D.hydraulik()
        z += ["", "Hydraulikschemata (Bosch-Hydraulikdatenbank)"]
        z += [f"- {s['nr']} {s['titel']} ({s['stand']}): {HY.link(hd, s['nr'], 'pdf')}"
              for s in HY.schemata(e, r, hd, T.inneneinheit(e, r, katalog))]
    return "\r\n".join(z) + "\r\n"


def mappe_bytes(e: dict, r: dict, katalog: dict, pdf: bytes | None = None) -> bytes:
    n = dateiname(e)
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"WP-Auslegung_{n}.json", P.dumps(e))
        z.writestr("Kurzbericht.txt", kurzbericht(e, r, katalog))
        v = bestell_vorlage(r)
        if v:
            md, we = D.mfh(), r["mfh"]["we"]
            z.writestr(f"Bestellvorschlag_{v['nr']}.d83", M.d83_bytes(v, md["langtexte"], we))
            z.writestr(f"Bestellvorschlag_{v['nr']}.csv", ("﻿" + M.csv_text(M.positionen(v, md["langtexte"], we))).encode("utf-8"))
        if pdf:
            z.writestr(f"WP-Auslegung_{n}.pdf", pdf)
    return puffer.getvalue()
