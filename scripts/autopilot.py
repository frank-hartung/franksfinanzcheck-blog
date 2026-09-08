#!/usr/bin/env python3
# ============================================================
#  AUTOPILOT – Orchestrator & Cockpit (AGC-Parität, Stufe 5)
#  ------------------------------------------------------------
#  Bildet die AGC-Pipeline "Brand Brain → Research → Kalender →
#  Content-Agenten → Publishing" als EINEN Befehl ab:
#
#    python3 scripts/autopilot.py --run       # Research + Kalender + Status
#    python3 scripts/autopilot.py --status    # Cockpit-Übersicht
#    python3 scripts/autopilot.py --selftest  # alle Bausteine prüfen (Exit 2)
#
#  Arbeitsteilung (wichtig – KEINE doppelten Veröffentlicher):
#    - autopilot.py ERZEUGT NIE Artikel und veröffentlicht NIE. Es bereitet
#      die Intelligenz vor (Brand Brain, Research-Report, Redaktionskalender),
#      die die bestehende Content-Engine v2 (scripts/engine_generate.py)
#      über scripts/agc_context.py beim Schreiben konsumiert.
#    - Die harten Gates (cadence_guard, publish_gate, quality_score) bleiben
#      der einzige Weg, auf dem ein Artikel live geht.
# ============================================================
import datetime
import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import brand_brain as bb          # noqa: E402
import campaign_manager as cm     # noqa: E402
import research_engine as re_     # noqa: E402

STATUS_FILE = os.path.join(BLOG_DIR, "AGC-AUTOPILOT-STATUS.md")


def _selftest_all():
    errs = []
    try:
        errs += bb.validate(bb.load_brand_brain())
        drift, lock_ok = bb.lock_drift(bb.load_brand_brain())
        if not lock_ok:
            errs.append("brand_lock.yaml nicht lesbar (fail-closed)")
        errs += [f"Drift: {d['brain_key']}" for d in drift]
    except Exception as e:  # noqa: BLE001
        errs.append(f"brand_brain: {e}")
    try:
        errs += re_.run_selftest()
    except Exception as e:  # noqa: BLE001
        errs.append(f"research_engine: {e}")
    try:
        errs += cm.run_selftest()
    except Exception as e:  # noqa: BLE001
        errs.append(f"campaign_manager: {e}")
    return errs


def write_status(report=None, plan=None):
    today = datetime.date.today()
    report = report or re_._load_yaml(re_.LATEST_FILE)
    plan = plan or (__import__("yaml").safe_load(open(cm.CALENDAR_FILE,
                     encoding="utf-8")) if os.path.exists(cm.CALENDAR_FILE) else None)
    active = cm.active_campaigns(today)
    lines = [
        "# AGC-Autopilot-Status",
        "",
        f"- Stand: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        "- Kadenz: **Mo/Mi/Fr · 2–3 Artikel/Tag** (DAUERVORGABE – unverändert)",
        "",
    ]
    brain = bb.load_brand_brain()
    lines.append("## 🧠 Brand Brain")
    lines.append(f"- Marke: {brain.get('brand', {}).get('name')} · "
                 f"Anrede: {brain.get('voice', {}).get('anrede', 'du')}-Form")
    lines.append(f"- Default-CTA: {brain.get('default_cta', '')}")
    lines.append("")
    lines.append("## 🔬 Recherche")
    if report and "teams" in report:
        lines.append(f"- Letzter Report: {report.get('generated_at')} "
                     f"· Modus: {report.get('mode')}")
        for key in ("trending", "news", "evergreen", "pain_points",
                    "viral_outliers", "niche_hooks"):
            lines.append(f"  - {key}: {len(report['teams'].get(key, []))} Signale")
        live = report.get("live_web", {}).get("findings", [])
        lines.append(f"  - live_web: {len(live)} "
                     f"({'unverifizierte Winkel' if live else 'aus/leer'})")
    else:
        lines.append("- Kein Report – `autopilot.py --run` ausführen.")
    lines.append("")
    lines.append(f"## 📣 Kampagnen (aktiv: {len(active)})")
    if active:
        for c in active:
            lines.append(f"- **{c.get('id')}** ({c.get('type')}) bis {c.get('end')} "
                         f"· CTA: {c.get('cta') or 'default'}")
    else:
        lines.append("- keine aktive Kampagne (alle `paused`/`draft`)")
    lines.append("")
    lines.append("## 🗓️ Redaktionskalender (nächste Slots)")
    if plan and plan.get("slots"):
        for s in plan["slots"][:6]:
            camp = f" · Kampagne {s.get('campaign')}" if s.get("campaign") else ""
            lines.append(f"- {s['date']} ({s['weekday']}) · `{s.get('pillar') or '–'}` "
                         f"· {s.get('topic', '')[:58]}{camp}")
    else:
        lines.append("- noch nicht erstellt – `campaign_manager.py --calendar`.")
    lines.append("")
    lines.append("---")
    lines.append("_Erzeugt von scripts/autopilot.py – der Autopilot plant und "
                 "recherchiert, veröffentlicht aber nie selbst (Gates bleiben aktiv)._")
    with open(STATUS_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))


def run_pipeline(dry_run=False):
    today = datetime.date.today()
    report = re_.build_report(today, skip_live="--skip-live" in sys.argv)
    re_.write_report(report, dry_run=dry_run)
    re_.write_markdown(report, dry_run=dry_run)
    plan = cm.generate_calendar(weeks=4, day=today, report=report)
    cm.save_calendar(plan, dry_run=dry_run)
    write_status(report, plan)
    total = sum(len(report["teams"][k]) for k in report["teams"])
    print(f"🤖 AUTOPILOT-LAUF {today.isoformat()} "
          f"({'dry-run' if dry_run else 'gespeichert'})")
    print(f"   Recherche: {total} Signale · Modus {report['mode']}")
    print(f"   Kalender:  {len(plan['slots'])} Slots (Mo/Mi/Fr)")
    print(f"   Kampagnen: {len(cm.active_campaigns(today))} aktiv")
    print("   → Veröffentlichung läuft unverändert über die Content-Engine v2.")
    return 0


def main():
    if "--selftest" in sys.argv:
        errs = _selftest_all()
        if errs:
            print("🛑 AUTOPILOT-SELFTEST FEHLGESCHLAGEN:")
            for e in errs:
                print(f"   - {e}")
            return 2
        print("✅ AUTOPILOT-SELFTEST bestanden "
              "(Brand Brain + Research + Kampagnen + Kalender).")
        return 0

    if "--status" in sys.argv:
        report = re_._load_yaml(re_.LATEST_FILE)
        plan = None
        import yaml
        if os.path.exists(cm.CALENDAR_FILE):
            plan = yaml.safe_load(open(cm.CALENDAR_FILE, encoding="utf-8"))
        write_status(report, plan)
        print(open(STATUS_FILE, encoding="utf-8").read())
        return 0

    dry = "--dry-run" in sys.argv
    return run_pipeline(dry_run=dry)


if __name__ == "__main__":
    sys.exit(main())
