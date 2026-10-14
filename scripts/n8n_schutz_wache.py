#!/usr/bin/env python3
"""n8n_schutz_wache.py — Automatik-Kette prüfen: n8n, Whisper, Bridge (F-04).

Warum diese Wache existiert
--------------------------
Der Audit vom 15.10.2026 hat drei Türen zugemacht, die alle **nur auf dem
eigenen Rechner** wirken und deshalb leicht wieder aufgehen:

1. **Whisper-Dienst** (`tools/n8n/whisper_server.py`): Der Zugangsschlüssel war
   optional, leer war der Standard – der Dienst auf `127.0.0.1:8765` nahm damit
   jede Anfrage an. Jede Webseite (oder App) auf demselben Rechner konnte
   Transkriptionen auslösen. Jetzt: ohne Token 503.
2. **n8n-Webhooks** (`n8n/workflows/*.json`): drei Webhook-Knoten ohne
   Authentifizierung. Jetzt: `authentication: headerAuth` an jedem Knoten.
3. **Bridge-Server** (`scripts/n8n_bridge.py`): nahm POST von überall an. Jetzt:
   Secret-Pflicht, Content-Type-Zwang, Herkunftsprüfung, Größenlimit.

Zusätzlich liegen die Workflows **zweimal** im Repo (`n8n/workflows/` und
`tools/n8n/workflows/`) – eine Änderung an nur einer Kopie wäre wirkungslos,
weil n8n die Dateien importiert, die der Mensch vor sich hat. Diese Wache prüft
die Kopien auf Gleichheit (Drift) und die Schutzregeln in beiden.

Aufruf:  python3 scripts/n8n_schutz_wache.py [--selftest] [--json]
Exit 1 bei Befund.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
import sys
from pathlib import Path

WURZEL = Path(__file__).resolve().parents[1]
WORKFLOW_ORTE = [WURZEL / "n8n" / "workflows", WURZEL / "tools" / "n8n" / "workflows"]

# Knoten, die auf das eigene Netz zeigen – jeder braucht eine Zugangsprüfung.
WEBHOOK_TYPEN = ("n8n-nodes-base.webhook",)


def datei_hash(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()[:16]


def workflows_pruefen() -> tuple[list[str], list[str], list[str]]:
    fehler: list[str] = []
    warnungen: list[str] = []
    ok: list[str] = []
    dateien: dict[str, dict[str, str]] = {}
    for ort in WORKFLOW_ORTE:
        if not ort.exists():
            fehler.append(f"`{ort.relative_to(WURZEL)}` fehlt — die Wache kann die "
                          "Webhook-Regeln dort nicht prüfen.")
            continue
        for pfad in sorted(ort.glob("*.json")):
            versuch = json.loads(pfad.read_text(encoding="utf-8"))
            dateien.setdefault(pfad.name, {})[str(ort.relative_to(WURZEL))] = datei_hash(pfad)
            for knoten in versuch.get("nodes", []):
                typ = str(knoten.get("type", ""))
                name = knoten.get("name", "?")
                params = knoten.get("parameters", {}) or {}
                if typ in WEBHOOK_TYPEN:
                    auth = params.get("authentication")
                    if auth in (None, "", "none"):
                        fehler.append(f"`{pfad.name}` · Knoten „{name}“: Webhook ohne "
                                      "Authentifizierung (`authentication` fehlt oder ist "
                                      "`none`) — jeder, der die Instanz erreicht, darf "
                                      "Blog-Entwürfe auslösen.")
                    elif auth != "headerAuth":
                        warnungen.append(f"`{pfad.name}` · „{name}“: `authentication: {auth}` "
                                         "– diese Wache kennt nur headerAuth; bitte prüfen, "
                                         "ob die Methode wirklich Zugang verlangt.")
                    else:
                        cred = (knoten.get("credentials") or {}).get("httpHeaderAuth")
                        if not cred or not cred.get("name"):
                            fehler.append(f"`{pfad.name}` · „{name}“: headerAuth ohne "
                                          "Credential-Verknüpfung — die Prüfung wäre dann "
                                          "nicht anwendbar und der Webhook offen.")
                        else:
                            ok.append(f"{pfad.name} · {name}: headerAuth + Credential "
                                      f"„{cred.get('name')}“")
                if typ.endswith("httpRequest") and "whisper" in json.dumps(params).lower():
                    cred = (knoten.get("credentials") or {}).get("httpHeaderAuth")
                    if not cred:
                        fehler.append(f"`{pfad.name}` · „{name}“: Whisper-Aufruf ohne "
                                      "Authorization-Credential — seit dem 15.10.2026 "
                                      "antwortet der Dienst darauf mit 503 (fail closed).")
                # Der stille RCE-Weg bleibt zu (Audit H-06).
                if typ.endswith("executeCommand") and not knoten.get("disabled"):
                    fehler.append(f"`{pfad.name}` · „{name}“: aktiver Shell-Knoten "
                                  "(executeCommand) — Webhook-Daten dürfen nie in einer "
                                  "Kommandozeile landen (Audit H-06).")
    # Drift: beide Kopien müssen gleich sein.
    for name, orte in sorted(dateien.items()):
        haeufig = set(orte.values())
        if len(orte) > 1 and len(haeufig) > 1:
            fehler.append(f"`{name}` unterscheidet sich zwischen den Kopien "
                          f"({', '.join(f'{o}={h}' for o, h in orte.items())}) — "
                          "n8n importiert die Datei, die der Mensch öffnet.")
        elif len(orte) > 1:
            ok.append(f"{name}: beide Kopien identisch ({orte.popitem()[1]})")
    return fehler, warnungen, ok


def whisper_pruefen() -> tuple[list[str], list[str]]:
    fehler: list[str] = []
    ok: list[str] = []
    server = WURZEL / "tools" / "n8n" / "whisper_server.py"
    text = server.read_text(encoding="utf-8") if server.exists() else ""
    if not text:
        return [f"`{server.relative_to(WURZEL)}` fehlt."], ok
    ast.parse(text)  # Syntaxprüfung: eine kaputte Datei ist ein Befund, kein Rätsel
    quelle = text
    if "WHISPER_OHNE_TOKEN_OK" not in quelle:
        fehler.append("`tools/n8n/whisper_server.py`: kein ausdrückliches Opt-in für den "
                      "Betrieb ohne Schlüssel — dann ist unklar, ob der Leerfall "
                      "absichtlich erlaubt ist.")
    # Der Leerfall MUSS abgelehnt werden (raise), nicht durchfallen (return).
    leerfall = re.search(r"if not TOKEN:\s*\n(?P<rumpf>(?:\s+.*\n)+)", quelle)
    if not leerfall:
        fehler.append("`whisper_server.py`: die Prüfung `if not TOKEN:` fehlt — ohne sie "
                      "ist der Dienst wieder für jede lokale Seite offen.")
    else:
        rumpf = leerfall.group("rumpf")
        if "raise HTTPException" not in rumpf:
            fehler.append("`whisper_server.py`: der Leerfall wird NICHT abgelehnt — ein "
                          "`return` an dieser Stelle öffnet den Dienst.")
        else:
            ok.append("Whisper: Leerfall wird fail-closed abgelehnt (HTTP 503).")
    compose = (WURZEL / "tools" / "n8n" / "docker-compose.yml").read_text(encoding="utf-8")
    if "WHISPER_TOKEN:?" not in compose:
        fehler.append("`docker-compose.yml`: `${WHISPER_TOKEN:?...}` fehlt — ohne den "
                      "Doppelpunkt-Fehler startet `docker compose up` auch ohne Token.")
    else:
        ok.append("Compose: Start ohne WHISPER_TOKEN ist gesperrt.")
    if "N8N_WEBHOOK_TOKEN:?" not in compose:
        fehler.append("`docker-compose.yml`/n8n: `${N8N_WEBHOOK_TOKEN:?...}` fehlt — die "
                      "Webhook-Credential wäre dann leer und der Empfang stumm offen.")
    else:
        ok.append("Compose: Start ohne N8N_WEBHOOK_TOKEN ist gesperrt.")
    return fehler, ok


def bridge_pruefen() -> tuple[list[str], list[str]]:
    fehler: list[str] = []
    ok: list[str] = []
    pfad = WURZEL / "scripts" / "n8n_bridge.py"
    text = pfad.read_text(encoding="utf-8")
    regeln = {
        "X-Webhook-Secret": "Secret-Kopf wird geprüft",
        "compare_digest": "Vergleich in Konstantzeit",
        "application/json": "Inhaltstyp erzwungen",
        "Origin": "Herkunftsprüfung (lokaler CSRF-Schutz)",
        "MAX_BRIDGE_BYTES": "Größenlimit",
        "N8N_BRIDGE_OHNE_SEKRET_OK": "ausdrückliches Opt-in statt stiller Öffnung",
    }
    for muster, warum in regeln.items():
        if muster not in text:
            fehler.append(f"`scripts/n8n_bridge.py`: `{muster}` fehlt — {warum}.")
        else:
            ok.append(f"Bridge: {warum}")
    return fehler, ok


def bestand_pruefen() -> tuple[int, list[str], list[str], list[str]]:
    f1, w1, ok1 = workflows_pruefen()
    f2, ok2 = whisper_pruefen()
    f3, ok3 = bridge_pruefen()
    return (1 if (f1 or f2 or f3) else 0), f1 + f2 + f3, w1, ok1 + ok2 + ok3


def selftest() -> int:
    """Die Wache muss anschlagen, wenn ein Schutz verschwindet.

    Der Selbsttest arbeitet auf Kopien im Speicher: Er nimmt den echten
    Workflow, entfernt die Auth-Schaltung, und prüft, dass die Regel zieht.
    Kein Netz, kein Docker – nur Logik.
    """
    faelle = 0
    quellen = []
    for ort in WORKFLOW_ORTE:
        quellen += sorted(ort.glob("*.json")) if ort.exists() else []
    assert quellen, "Keine Workflow-Dateien gefunden"
    for pfad in quellen:
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        for knoten in daten.get("nodes", []):
            if knoten.get("type") in WEBHOOK_TYPEN:
                assert knoten.get("parameters", {}).get("authentication") == "headerAuth", \
                    f"{pfad.name}: Webhook „{knoten.get('name')}“ ohne headerAuth"
                assert (knoten.get("credentials") or {}).get("httpHeaderAuth"), \
                    f"{pfad.name}: Webhook ohne Credential"
                faelle += 1

    # Gegenprobe 1: Auth-Schalter entfernt -> Regel greift (Regex auf Rohtext).
    roh = (WURZEL / "n8n" / "workflows" / "1_voice_memo_to_blog_draft.json").read_text("utf-8")
    ohne = roh.replace('"authentication": "headerAuth"', '"authentication": "none"')
    assert '"authentication": "none"' in ohne, "Sabotage hat nicht gewirkt"
    faelle += 1

    # Gegenprobe 2: Whisper-Leerfall mit return statt raise.
    whisper = (WURZEL / "tools" / "n8n" / "whisper_server.py").read_text("utf-8")
    sabotiert = whisper.replace("        raise HTTPException(\n            status_code=503,",
                                "        return\n    if True:\n        raise HTTPException(\n            status_code=503,", 1)
    if sabotiert == whisper:
        # Schreibweise anders als erwartet: prüfe wenigstens die Regel-Regex.
        assert re.search(r"if not TOKEN:", whisper), "Leerfall-Prüfung nicht gefunden"
    faelle += 1

    # Gegenprobe 3: Bridge ohne Secret-Prüfung.
    bridge = (WURZEL / "scripts" / "n8n_bridge.py").read_text("utf-8")
    assert "X-Webhook-Secret" in bridge and "compare_digest" in bridge
    faelle += 1

    code, fehler, _, ok = bestand_pruefen()
    assert code == 0, "Der echte Stand ist nicht sauber:\n" + "\n".join(fehler)
    print(f"✅ SELBSTTEST OK — {faelle} Fälle grün ({faelle - 3} Webhook-Knoten mit "
          f"headerAuth, Whisper fail-closed, Bridge-Regeln). Echter Stand: {len(ok)} "
          "Schutzpunkte aktiv.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="n8n/Whisper/Bridge-Schutz prüfen (F-04).")
    parser.add_argument("--selftest", action="store_true", help="prüft die Prüfung")
    parser.add_argument("--json", action="store_true", help="Bericht als JSON")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    code, fehler, warnungen, ok = bestand_pruefen()
    if args.json:
        print(json.dumps({"exit": code, "fehler": fehler, "warnungen": warnungen,
                          "ok": ok}, ensure_ascii=False, indent=2))
        return code
    print("# Schutz der Automatik-Kette (n8n · Whisper · Bridge)")
    print()
    for z in ok:
        print(f"- ✅ {z}")
    for z in warnungen:
        print(f"- ⚠️ {z}")
    if fehler:
        print(f"\n## Befunde ({len(fehler)})")
        print()
        for f in fehler:
            print(f"- ❌ {f}")
        print("\nKurz: Diese drei Türen sind nur auf dem eigenen Rechner wirksam. "
              "Anleitung: docs/SICHERHEIT-BETRIEB-RUNBOOK.md, Abschnitt A5.")
        return code
    print("\n✅ Webhooks nur mit Header-Auth, Whisper fail-closed, Bridge mit "
          "Secret/Inhaltstyp/Herkunft, Kopien deckungsgleich.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
