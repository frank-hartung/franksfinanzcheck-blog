#!/usr/bin/env python3
"""Agent-Reach-Gate: Gesundheitsprüfung der Recherche-Integration.

Teil der Agent-Reach-Premium-Integration (12.09.2026, siehe
ANLEITUNG-AGENT-REACH.md). Das Gate beantwortet eine Frage:
„Kann dieses Repository gerade mit Agent Reach im Internet lesen?“

Prüfschritte
------------
1. agent-reach-Binary vorhanden und ausführbar?
2. Erwartete Version installiert (Pin aus requirements-agent-reach.txt)?
3. `agent-reach doctor --json` liefert eine Kanalmatrix.
4. Mindest-Kanäle erreichbar (Standard: rss ODER web muss „ok“ sein –
   das sind die Zero-Config-Kanäle der Redaktion).

Exit-Codes: 0 = einsatzbereit, 1 = Mindestanforderung nicht erfüllt,
2 = schwerer Fehler (kein Binary/doctor defekt).

Aufruf
------
  python3 scripts/agent_reach_gate.py            # menschenlesbar
  python3 scripts/agent_reach_gate.py --json     # maschinenlesbar
  python3 scripts/agent_reach_gate.py --min rss,youtube,github,web
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ERWARTETE_VERSION = "1.5.0"   # Pin aus requirements-agent-reach.txt (Tag v1.5.0)
MINDEST_KANALE_STD = ("rss", "web")


def finde_binary() -> str | None:
    return shutil.which("agent-reach") or (
        str(ROOT / ".venv" / "bin" / "agent-reach")
        if (ROOT / ".venv" / "bin" / "agent-reach").exists() else None)


def hole_version(binpfad: str) -> str:
    proc = subprocess.run([binpfad, "--version"], capture_output=True,
                          text=True, timeout=30)
    m = re.search(r"(\d+\.\d+\.\d+)", (proc.stdout or proc.stderr))
    return m.group(1) if m else "unbekannt"


def hole_doctor(binpfad: str) -> dict:
    proc = subprocess.run([binpfad, "doctor", "--json"], capture_output=True,
                          text=True, timeout=120)
    if proc.returncode != 0:
        raise RuntimeError(f"doctor lieferte Exit-Code {proc.returncode}")
    daten = json.loads(proc.stdout)
    if not isinstance(daten, dict):
        raise RuntimeError("doctor-Ausgabe ist kein JSON-Objekt")
    return daten


def main() -> int:
    ap = argparse.ArgumentParser(description="Agent-Reach-Gesundheitsgate")
    ap.add_argument("--json", action="store_true", help="JSON-Ausgabe")
    ap.add_argument("--min", default=",".join(MINDEST_KANALE_STD),
                    help="Kommaliste der Mindest-Kanäle (eines davon muss ok sein)")
    args = ap.parse_args()

    bericht: dict = {"einsatzbereit": False, "fehler": []}

    binpfad = finde_binary()
    if not binpfad:
        bericht["fehler"].append("agent-reach-Binary nicht gefunden "
                                 "(pip install -r requirements-agent-reach.txt)")
        _ausgabe(bericht, args.json)
        return 2
    bericht["binary"] = binpfad

    try:
        version = hole_version(binpfad)
    except Exception as exc:  # noqa: BLE001
        bericht["fehler"].append(f"Versionsprüfung fehlgeschlagen: {exc}")
        _ausgabe(bericht, args.json)
        return 2
    bericht["version"] = version
    if version != ERWARTETE_VERSION:
        bericht["fehler"].append(
            f"Versionsdrift: installiert {version}, gepinnt {ERWARTETE_VERSION} "
            "– requirements-agent-reach.txt bewusst aktualisieren!")

    try:
        kanale = hole_doctor(binpfad)
    except Exception as exc:  # noqa: BLE001
        bericht["fehler"].append(f"agent-reach doctor fehlgeschlagen: {exc}")
        _ausgabe(bericht, args.json)
        return 2

    bericht["kanalmatrix"] = {
        name: {"status": info.get("status"), "backend": info.get("active_backend")}
        for name, info in kanale.items()
    }

    ok_kanale = {n for n, i in kanale.items() if i.get("status") == "ok"}
    mindest = [k.strip() for k in args.min.split(",") if k.strip()]
    erfuellt = ok_kanale & set(mindest)
    bericht["mindest_kanale"] = mindest
    bericht["mindest_erfuellt_durch"] = sorted(erfuellt)
    bericht["einsatzbereit"] = bool(erfuellt) and not bericht["fehler"]

    if not erfuellt:
        bericht["fehler"].append(
            f"Keiner der Mindest-Kanäle ({', '.join(mindest)}) ist ok – "
            "Netz/Installation prüfen.")

    _ausgabe(bericht, args.json)
    return 0 if bericht["einsatzbereit"] else 1


def _ausgabe(bericht: dict, als_json: bool) -> None:
    if als_json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2))
        return
    print("Agent-Reach-Gate")
    print("================")
    if "binary" in bericht:
        print(f"Binary:   {bericht['binary']}")
        print(f"Version:  {bericht.get('version', '?')}")
    for name, info in (bericht.get("kanalmatrix") or {}).items():
        backend = f" ({info['backend']})" if info.get("backend") else ""
        print(f"  {name:14} {info['status']}{backend}")
    if bericht["fehler"]:
        print("\nFeststellungen:")
        for f in bericht["fehler"]:
            print(f"  - {f}")
    print("\nErgebnis:",
          "EINSATZBEREIT" if bericht["einsatzbereit"] else "NICHT EINSATZBEREIT")


if __name__ == "__main__":
    sys.exit(main())
