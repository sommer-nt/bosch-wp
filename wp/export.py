"""Export: Kurzbericht (Text) und Projektmappe (.zip) – wie kurzbericht()/exportMappe() in index.html.

Die Projektmappe enthält Projektdatei (.json), Kurzbericht, das Bild der gewählten Hydraulik und in der
Streamlit-Version zusätzlich das PDF der Auslegung.
"""
from __future__ import annotations

import io
import re
import zipfile

from . import daten as D
from . import hydraulik as HY
from . import projekt as P
from . import texte as T


def dateiname(e: dict) -> str:
    name = e["projekt"].get("name") or "Projekt"
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        name = name.replace(a, b)
    return re.sub(r"[^\w-]+", "_", name, flags=re.ASCII)   # Dateinamen ohne Umlaute


def kurzbericht(e: dict, r: dict, katalog: dict) -> str:
    z = ["Bosch WP-Schnellauslegung – " + (e["projekt"].get("name") or "Projekt ohne Namen"),
         "Entwickelt von Daniel Sommer · HC/SDE3-PSD", "", "Auf einen Blick"]
    z += ["- " + x["text"].replace("**", "") for x in T.klartext(e, r, katalog)]
    h = HY.gewaehlt(e, r, D.hydraulik()) if r.get("gewaehlt") else None
    if h:
        z += ["", "Hydraulik", f"- {h['titel']} ({'ausgewählt' if h['manuell'] else 'vorgeschlagen'} · "
              f"{HY.STUFE_TEXT[h['stufe']]}) – Musterlösungen {', '.join(D.mit_bv(x) for x in h['loesungen'])}"]
        z += ["- Anpassen: " + t for t in h["anpassen"]]
    return "\r\n".join(z) + "\r\n"


def mappe_bytes(e: dict, r: dict, katalog: dict, pdf: bytes | None = None) -> bytes:
    n = dateiname(e)
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"WP-Auslegung_{n}.json", P.dumps(e))
        z.writestr("Kurzbericht.txt", kurzbericht(e, r, katalog))
        h = HY.gewaehlt(e, r, D.hydraulik()) if r.get("gewaehlt") else None
        if h and D.hydraulik_bild(h["id"]).exists():
            z.write(D.hydraulik_bild(h["id"]), f"Hydraulik_{h['id']}.png")
        if pdf:
            z.writestr(f"WP-Auslegung_{n}.pdf", pdf)
    return puffer.getvalue()
