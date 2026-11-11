"""Liest den Index der Bosch-Hydraulikdatenbank (bosch-de-de.boschhc-documents.com/hdb) und schreibt daten/hydraulik.json.

    python tools/hdb_import.py
    python tools/excel_import.py --nur-einbetten

Übernommen werden nur die Hydraulikschemata mit Wärmepumpe (Luft/Wasser, Sole/Wasser) – Titel, Nummer, Stand,
Komponenten, BOPA-Pakete und Kategorien. PDF, DWG und Vorschaubild bleiben in der Datenbank und werden verlinkt.
Die Datenbank liefert über /api/v3/domainconfig einen öffentlichen Sitzungs-Token (wie die Webseite selbst).
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request
from pathlib import Path

HIER = Path(__file__).resolve().parent.parent
ZIEL = HIER / "daten" / "hydraulik.json"
BASIS = "https://bosch-de-de.boschhc-documents.com"


def lade(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=60) as f:
        return json.load(f)


def main() -> None:
    token = lade(f"{BASIS}/api/v3/domainconfig?domain={urllib.parse.urlparse(BASIS).hostname}")["token"]
    alle, off = [], 0
    while True:
        q = urllib.parse.urlencode({"token": token, "limit": 100, "offset": off, "query": "", "orderBy": "validSince", "orderDirection": "desc"})
        d = lade(f"{BASIS}/api/v3/hydraulicdocuments?{q}")
        alle += d["documents"]
        off += len(d["documents"])
        if not d["documents"] or off >= d["totalDocuments"]:
            break
    wp = [x for x in alle if any(t.startswith("waermepumpe") for t in x.get("heat_appliance_type") or [])
          and not x.get("sales_discontinued")]
    out = {"quelle": "Bosch Hydraulikdatenbank (bosch-de-de.boschhc-documents.com/hdb)", "basis": BASIS,
           "schemata": [{"nr": x["document_id"], "titel": x["title"].strip(), "stand": x.get("validSince") or "",
                         "komponenten": (x.get("coversheet_buderusname") or "").strip(" ,"),
                         "bopa": (x.get("coversheet_logasys") or "").strip(" ,"),
                         "kategorien": sorted(x.get("hydraulic_categories") or []), "dwg": bool(x.get("dwgfilename"))}
                        for x in sorted(wp, key=lambda x: x["document_id"])]}
    ZIEL.write_text(json.dumps(out, ensure_ascii=False, indent=0), encoding="utf-8")
    print(f"{len(alle)} Schemata gelesen, {len(out['schemata'])} mit Wärmepumpe -> {ZIEL.relative_to(HIER)}")


if __name__ == "__main__":
    main()
