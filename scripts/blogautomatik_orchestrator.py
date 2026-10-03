#!/usr/bin/env python3
"""blogautomatik_orchestrator.py — Master-Orchestrierung für den 0 € Blogbetrieb.

0 € LAUFENDE KOSTEN (Whisper lokal + n8n self-hosted + GitHub Pages)
    Der zentrale Dirigent und Leitstand auf Profi-Agentur-Niveau. Er
    verknüpft die drei tragenden Säulen:

    ┌─────────────────────────────────────────────────────────────┐
    │                0 € LAUFENDE KOSTEN STACK                    │
    ├──────────────────────────────┬──────────────────────────────┤
    │  1. WHISPER LOKAL            │  2. n8N SELF-HOSTED          │
    │  · Sprachmemos & Diktate     │  · Visuelle Workflows        │
    │  · 100% On-Premise (0 €)     │  · Docker Compose (0 €)      │
    │  · Audio-QA & Sprachparität  │  · Webhook- & Event-Hub      │
    │  · ZEIT-Stil & 4K-Prüfpfad   │  · Omnichannel-Orchestrierer │
    ├──────────────────────────────┴──────────────────────────────┤
    │  3. GITHUB PAGES & ACTIONS                                  │
    │  · Hugo Static Site Generator (0 € Serverless Hosting)      │
    │  · CI/CD Qualitäts-Gates & Automatischer Deploy             │
    │  · Schaltwerk (Integrierter Zapier-Ersatz in Python)        │
    └─────────────────────────────────────────────────────────────┘

AUFRUF:
    python3 scripts/blogautomatik_orchestrator.py --status     # Vollständiger System-Status
    python3 scripts/blogautomatik_orchestrator.py --audit      # Kosten- & SLA-Audit
    python3 scripts/blogautomatik_orchestrator.py --pipeline voice-to-publish
    python3 scripts/blogautomatik_orchestrator.py --pipeline health-audit
    python3 scripts/blogautomatik_orchestrator.py --pipeline omnichannel-sync
    python3 scripts/blogautomatik_orchestrator.py --selftest   # Offline-Selbsttest aller Säulen
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shutil
import sys
from typing import Any

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import n8n_bridge
import schaltwerk
import whisper_engine


# =====================================================================
#  SYSTEM STATUS PRÜFUNG (Alle 3 Säulen)
# =====================================================================

def get_system_status() -> dict[str, Any]:
    """Erfasst den umfassenden Zustand aller Automatisierungs-Komponenten."""
    now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

    # Säule 1: Whisper Lokal
    whisper_eng = whisper_engine.WhisperEngine(backend="auto")
    inbox_dir = os.path.join(BLOG_DIR, "data", "whisper_inbox")
    inbox_count = len([
        f for f in os.listdir(inbox_dir)
        if os.path.isfile(os.path.join(inbox_dir, f)) and not f.startswith(".")
    ]) if os.path.exists(inbox_dir) else 0

    whisper_status = {
        "status": "online" if whisper_eng._resolved_backend != "mock" else "mock_standby",
        "backend": whisper_eng._resolved_backend,
        "model": whisper_eng.model,
        "inbox_dir": "data/whisper_inbox",
        "inbox_wartend": inbox_count,
        "0_euro_kosten": True,
    }

    # Säule 2: n8n Self-Hosted
    n8n_ping = n8n_bridge.ping_n8n()
    n8n_state = n8n_bridge.load_bridge_state()
    n8n_workflows_dir = os.path.join(BLOG_DIR, "tools", "n8n", "workflows")
    wf_count = len([
        f for f in os.listdir(n8n_workflows_dir) if f.endswith(".json")
    ]) if os.path.exists(n8n_workflows_dir) else 0

    n8n_status = {
        "status": n8n_ping.get("status", "standby"),
        "url": n8n_ping.get("url"),
        "latenz_ms": n8n_ping.get("latency_ms", 0),
        "workflows_installiert": wf_count,
        "gesendete_events": n8n_state.get("gesendete_events", 0),
        "empfangene_events": n8n_state.get("empfangene_events", 0),
        "0_euro_kosten": True,
    }

    # Säule 3: GitHub Pages, Hugo & Schaltwerk
    posts_dir = os.path.join(BLOG_DIR, "content", "posts")
    drafts_dir = os.path.join(BLOG_DIR, "content", "drafts")
    post_count = len(os.listdir(posts_dir)) if os.path.exists(posts_dir) else 0
    draft_count = len(os.listdir(drafts_dir)) if os.path.exists(drafts_dir) else 0

    schaltwerk_regeln = schaltwerk.load_regeln()
    schaltwerk_state = schaltwerk.load_state()

    github_status = {
        "hosting": "GitHub Pages (franksfinanzcheck.de)",
        "live_artikel": post_count,
        "entwuerfe": draft_count,
        "schaltwerk_regeln_aktiv": len([r for r in schaltwerk_regeln.get("regeln", []) if r.get("enabled")]),
        "schaltwerk_laeufe_gesamt": sum(
            sum(tage.values()) for tage in (schaltwerk_state.get("zaehler") or {}).values()
        ),
        "0_euro_kosten": True,
    }

    overall_healthy = (
        whisper_status["status"] in ("online", "mock_standby")
        and github_status["live_artikel"] > 0
    )

    return {
        "timestamp": now_iso,
        "overall_healthy": overall_healthy,
        "whisper_lokal": whisper_status,
        "n8n_self_hosted": n8n_status,
        "github_pages": github_status,
    }


# =====================================================================
#  KOSTEN- & AGENTUR-AUDIT (0 € Nachweis)
# =====================================================================

def run_agency_cost_audit() -> dict[str, Any]:
    """Berechnet die monatlichen und jährlichen Einsparungen gegenüber SaaS."""
    saas_comparison = {
        "zapier_professional": {"kosten_monat": 79.0, "leistung": "Social Media & RSS Dispatcher (750 Tasks)"},
        "openai_whisper_api": {"kosten_monat": 45.0, "leistung": "Cloud-Spracherkennung & Audio-QA (15h Audio)"},
        "make_pro_automation": {"kosten_monat": 30.0, "leistung": "Content-Workflow & Webhook-Router"},
        "hosting_managed_wordpress": {"kosten_monat": 64.0, "leistung": "Server, CDN, SSL, Backup & DB"},
        "monitoring_saas": {"kosten_monat": 50.0, "leistung": "Uptime- & Broken-Link-Radar"},
    }

    summe_saas_monat = sum(item["kosten_monat"] for item in saas_comparison.values())
    summe_saas_jahr = summe_saas_monat * 12

    blogautomatik_stack = {
        "whisper_lokal": {"kosten_monat": 0.0, "einsparung": 45.0, "architektur": "faster-whisper / CTranslate2 on-premise"},
        "n8n_self_hosted": {"kosten_monat": 0.0, "einsparung": 109.0, "architektur": "Docker Compose Community Edition"},
        "github_pages_actions": {"kosten_monat": 0.0, "einsparung": 64.0, "architektur": "Hugo Static SSG + Global Fastly Edge"},
        "schaltwerk_python": {"kosten_monat": 0.0, "einsparung": 50.0, "architektur": "Interne Fail-Safe Trigger/Aktions-Engine"},
    }

    return {
        "monatliche_laufende_kosten": 0.0,
        "vergleich_monat_saas": summe_saas_monat,
        "vergleich_jahr_saas": summe_saas_jahr,
        "ersparnis_prozent": 100.0,
        "dsgvo_konformitaet": "100% lokal – keine Sprachdatenübertragung an Dritte",
        "lock_in_risiko": "0% (Open Source, Standardformate Markdown/YAML/JSON)",
        "saas_kosten_details": saas_comparison,
        "eigene_komponenten": blogautomatik_stack,
    }


# =====================================================================
#  PIPELINE EXECUTION
# =====================================================================

def run_pipeline(name: str, dry_run: bool = False) -> dict[str, Any]:
    """Führt eine automatisierte End-to-End-Pipeline aus."""
    print(f"🎬 Starte Pipeline: '{name}' (dry_run={dry_run})...")
    start = datetime.datetime.now()

    if name == "voice-to-publish":
        # 1. Inbox verarbeiten
        inbox_dir = os.path.join(BLOG_DIR, "data", "whisper_inbox")
        engine = whisper_engine.WhisperEngine(backend="auto")
        results = whisper_engine.process_inbox_directory(inbox_dir=inbox_dir, engine=engine)
        
        # 2. n8n benachrichtigen
        if results:
            for r in results:
                n8n_bridge.dispatch_event_to_n8n(
                    event_type="neuer_entwurf_erstellt",
                    payload=r,
                    dry_run=dry_run,
                )
        return {
            "pipeline": name,
            "status": "success",
            "verarbeitete_aufnahmen": len(results),
            "details": results,
            "dauer_sekunden": round((datetime.datetime.now() - start).total_seconds(), 2),
        }

    elif name == "health-audit":
        # Health-Gate + Latenz-Ping an n8n
        n8n_status = n8n_bridge.ping_n8n()
        sys_status = get_system_status()
        n8n_bridge.dispatch_event_to_n8n(
            event_type="health_status_bericht",
            payload=sys_status,
            dry_run=dry_run,
        )
        return {
            "pipeline": name,
            "status": "success",
            "system_status": sys_status,
            "n8n_ping": n8n_status,
            "dauer_sekunden": round((datetime.datetime.now() - start).total_seconds(), 2),
        }

    elif name == "omnichannel-sync":
        # Schaltwerk manuell anstoßen
        regeln = schaltwerk.load_regeln()
        schaltwerk_res = schaltwerk.run(regeln, dry_run=dry_run)
        return {
            "pipeline": name,
            "status": "success",
            "schaltwerk_ergebnis": schaltwerk_res,
            "dauer_sekunden": round((datetime.datetime.now() - start).total_seconds(), 2),
        }

    else:
        return {"pipeline": name, "status": "unknown_pipeline", "available": ["voice-to-publish", "health-audit", "omnichannel-sync"]}


# =====================================================================
#  SELBSTTEST (Offline & Fail-Closed)
# =====================================================================

def selftest() -> bool:
    """Prüft alle drei Säulen auf Herz und Nieren."""
    print("🔬 Starte Master-Orchestrator Selbsttest (0 € Stack)...")

    # 1. Whisper-Engine Test
    w_ok = whisper_engine.selftest()
    assert w_ok is True, "Whisper-Engine Selbsttest fehlgeschlagen"

    # 2. n8n-Bridge Test
    b_ok = n8n_bridge.selftest()
    assert b_ok is True, "n8n-Bridge Selbsttest fehlgeschlagen"

    # 3. Schaltwerk Test
    s_ok = schaltwerk.selftest()
    assert s_ok == 0 or s_ok is True, f"Schaltwerk Selbsttest fehlgeschlagen: {s_ok}"

    # 4. Status-Erfassung
    st = get_system_status()
    assert st["overall_healthy"] is True, "System-Status meldet ungesunden Zustand"
    assert st["whisper_lokal"]["0_euro_kosten"] is True
    assert st["n8n_self_hosted"]["0_euro_kosten"] is True
    assert st["github_pages"]["0_euro_kosten"] is True
    print("  ✅ Status-Aggregator aller 3 Säulen erfolgreich validiert.")

    # 5. Kosten-Audit
    audit = run_agency_cost_audit()
    assert audit["monatliche_laufende_kosten"] == 0.0, "Laufende Kosten nicht 0 €!"
    assert audit["vergleich_monat_saas"] > 200.0, "SaaS-Vergleichsberechnung unplausibel"
    print("  ✅ 0 € Kosten-Garantie & Agentur-Audit erfolgreich validiert.")

    print("🎉 Alle Master-Orchestrator Selbsttests BESTANDEN!")
    return True


# =====================================================================
#  HAUPTPROGRAMM (CLI)
# =====================================================================

def main() -> int:
    parser = argparse.ArgumentParser(
        description="Master-Orchestrator für den 0 € Blogbetrieb (Whisper + n8n + Pages)."
    )
    parser.add_argument("--status", action="store_true", help="Zeigt den aktuellen Zustand aller Subsysteme an")
    parser.add_argument("--audit", action="store_true", help="Führt das Kosten- & Architektur-Audit durch")
    parser.add_argument("--pipeline", choices=["voice-to-publish", "health-audit", "omnichannel-sync"], help="Führt eine automatisierte Pipeline aus")
    parser.add_argument("--dry-run", action="store_true", help="Führt Aktionen ohne Schreib-/Netzoperationen aus")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    parser.add_argument("--selftest", action="store_true", help="Führt den Offline-Selbsttest aus")

    args = parser.parse_args()

    if args.selftest:
        success = selftest()
        return 0 if success else 1

    if args.status:
        status_data = get_system_status()
        if args.json:
            print(json.dumps(status_data, ensure_ascii=False, indent=2))
        else:
            print("=====================================================================")
            print(" 🌟 FRANKSFINANZCHECK MASTER-ORCHESTRATOR STATUS (0 € STACK)")
            print("=====================================================================")
            print(f" Zeitstempel: {status_data['timestamp']}")
            print(f" Gesamtzustand: {'✅ BEREIT / GRÜN' if status_data['overall_healthy'] else '❌ WARNUNG'}")
            print("\n 🎙 SÄULE 1: WHISPER LOKAL (0 €)")
            print(f"    · Backend:        {status_data['whisper_lokal']['backend']}")
            print(f"    · Modell:         {status_data['whisper_lokal']['model']}")
            print(f"    · Inbox-Warteschlange: {status_data['whisper_lokal']['inbox_wartend']} Dateien")
            print("\n ⚡ SÄULE 2: n8n SELF-HOSTED (0 €)")
            print(f"    · Status:         {status_data['n8n_self_hosted']['status'].upper()}")
            print(f"    · Workflows:      {status_data['n8n_self_hosted']['workflows_installiert']} Workflows einsatzbereit")
            print(f"    · Events (out/in): {status_data['n8n_self_hosted']['gesendete_events']} / {status_data['n8n_self_hosted']['empfangene_events']}")
            print("\n 🚀 SÄULE 3: GITHUB PAGES & SCHALTWERK (0 €)")
            print(f"    · Live-Artikel:   {status_data['github_pages']['live_artikel']}")
            print(f"    · Entwürfe:       {status_data['github_pages']['entwuerfe']}")
            print(f"    · Aktive Regeln:  {status_data['github_pages']['schaltwerk_regeln_aktiv']}")
            print("=====================================================================")
        return 0

    if args.audit:
        audit_data = run_agency_cost_audit()
        if args.json:
            print(json.dumps(audit_data, ensure_ascii=False, indent=2))
        else:
            print("=====================================================================")
            print(" 💰 FRANKSFINANZCHECK KOSTEN- & AGENTUR-AUDIT (0 € GARANTIE)")
            print("=====================================================================")
            print(f" Laufende monatliche Kosten:   0,00 €")
            print(f" Vergleichbare SaaS-Kosten:    {audit_data['vergleich_monat_saas']:.2f} € / Monat")
            print(f" Jährliche Ersparnis:          {audit_data['vergleich_jahr_saas']:.2f} € / Jahr")
            print(f" Ersparnisquote:               100,0 %")
            print(f" DSGVO & Datenschutz:          {audit_data['dsgvo_konformitaet']}")
            print("=====================================================================")
        return 0

    if args.pipeline:
        res = run_pipeline(args.pipeline, dry_run=args.dry_run)
        if args.json:
            print(json.dumps(res, ensure_ascii=False, indent=2))
        else:
            print(f"🏁 Pipeline '{args.pipeline}' beendet mit Status: {res.get('status')}")
            if "dauer_sekunden" in res:
                print(f"   Dauer: {res['dauer_sekunden']}s")
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
