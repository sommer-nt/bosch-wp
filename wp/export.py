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
    name = e["projekt"].get("name") or "Projekt"
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue"), ("ß", "ss")):
        name = name.replace(a, b)
    return re.sub(r"[^\w-]+", "_", name, flags=re.ASCII)   # Dateinamen ohne Umlaute


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


def dokumentation(e: dict, r: dict, katalog: dict) -> dict | None:
    return M.dokumentation(e, r, D.mfh(), D.hydraulik(), T.inneneinheit(e, r, katalog))


def dokumentation_text(d: dict) -> str:
    zeichen = {"ok": "[OK]   ", "warn": "[!]    ", "bad": "[FEHLER] ", "": "       "}
    return ("Dokumentation vollständig und valide" if d["valide"] else "Dokumentation unvollständig – Hinweise beachten") + "\r\n\r\n" + \
        "\r\n".join(zeichen[x["status"]] + x["text"] for x in d["pruefungen"]) + "\r\n"


def schema_fuer_export(e: dict, r: dict, katalog: dict) -> dict | None:
    """Hydraulikschema der Auslegung (bei MFH das Schema zur Musterlösung) – wie schemaFuerExport() in index.html."""
    if not r.get("gewaehlt"):
        return None
    d = dokumentation(e, r, katalog)
    if d and d["schema"]:
        return d["schema"]
    hs = HY.schemata(e, r, D.hydraulik(), T.inneneinheit(e, r, katalog), 1)
    return hs[0] if hs else None


def lade_schema(nr: str, art: str = "pdf", timeout: float = 30) -> bytes | None:
    """Original-Schema (PDF/DWG) aus der Hydraulikdatenbank laden; None, wenn offline."""
    import urllib.request
    try:
        with urllib.request.urlopen(HY.link(D.hydraulik(), nr, art), timeout=timeout) as f:
            daten = f.read()
            return daten if daten[:4] == b"%PDF" else None
    except Exception:   # noqa: BLE001 – offline oder Datenbank nicht erreichbar
        return None


def pdf_mit_schema(pdf: bytes, schema_pdf: bytes | None) -> bytes:
    """Auslegung + Original-Hydraulikschema als ein PDF (Gesamtdokumentation)."""
    if not schema_pdf:
        return pdf
    from pypdf import PdfWriter
    w = PdfWriter()
    for teil in (pdf, schema_pdf):
        w.append(io.BytesIO(teil))
    out = io.BytesIO()
    w.write(out)
    return out.getvalue()


def mappe_bytes(e: dict, r: dict, katalog: dict, pdf: bytes | None = None, schema_dateien: dict | None = None) -> bytes:
    """schema_dateien: {"pdf": bytes, "dwg": bytes} des Hydraulikschemas (lade_schema), sonst nur Link im Kurzbericht."""
    n = dateiname(e)
    puffer = io.BytesIO()
    with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr(f"WP-Auslegung_{n}.json", P.dumps(e))
        z.writestr("Kurzbericht.txt", kurzbericht(e, r, katalog))
        v = bestell_vorlage(r)
        if v:
            md, we = D.mfh(), r["mfh"]["we"]
            z.writestr(f"Bestellvorschlag_{v['nr']}.d83", M.d83_bytes(v, md["langtexte"], we))
            z.writestr(f"Bestellvorschlag_{v['nr']}.csv", ("\ufeff" + M.csv_text(M.positionen(v, md["langtexte"], we))).encode("utf-8"))
            zl = next(c for c in md["zellen"] if c.get("vorlage") == v["nr"])
            z.writestr(f"Rapida-Import_{v['nr']}.csv", M.rapida_bytes(v, md["langtexte"], we, e["projekt"], M.rapida_hinweis(v, zl)))
        d = dokumentation(e, r, katalog)
        if d:
            z.writestr("Dokumentation_Bestellvorschlag.txt", dokumentation_text(d))
        sch = schema_fuer_export(e, r, katalog)
        for art, daten in (schema_dateien or {}).items():
            if sch and daten:
                z.writestr(f"Hydraulikschema_{sch['nr']}.{art}", daten)
        if pdf:
            z.writestr(f"WP-Auslegung_{n}.pdf", pdf_mit_schema(pdf, (schema_dateien or {}).get("pdf")))
    return puffer.getvalue()
