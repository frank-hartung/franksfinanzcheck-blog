#!/usr/bin/env python3
"""cadence_manager.py – Automatische Anpassung der Publikationsfrequenz
(13.08.2026, Betriebsregel Frank: "Anzahl der Artikel soll dauerhaft
automatisch angepasst werden").

FACHLICHE GRUNDENTSCHEIDUNG (Profi-SEO-Manager + Profi-Affiliate-Marketer,
13.08.2026 – Details siehe CADENCE-ENTSCHEIDUNG.md):

  Ausgangslage: Domain gültig seit 08.08.2026 (zum Entscheidungszeitpunkt
  5 Tage alt), YMYL-Nische (Finanzen), vollautomatisierter Solo-Betrieb.
  Google bewertet keine feste Publikationsfrequenz, sondern Content-
  Qualität und Domain-Vertrauen – bei einer brandneuen YMYL-Domain ist
  vorsichtiges, stetiges Wachstum die professionell richtige Wahl statt
  aggressiven Hochfahrens.

  RAMPE (nach Domain-Alter in Wochen seit Launch 08.08.2026):
    Woche  0- 3 (Monat 1):  3 Artikel/Woche
    Woche  4- 7 (Monat 2):  4 Artikel/Woche
    Woche  8-11 (Monat 3):  5 Artikel/Woche
    ab Woche 12:            5 Artikel/Woche (dauerhafter Deckel für eine
                            Solo-Automatisierung in einer YMYL-Nische –
                            darüber hinaus nur mit echten Performance-Daten
                            aus der Google Search Console skalieren, siehe
                            ANLEITUNG-GOOGLE-SEARCH-CONSOLE.md)

  SICHERHEITSBREMSE (automatisch, unabhängig vom Domain-Alter): Die letzten
  14 Tage Audit-Log (engine_generate + daily_post_guard) werden ausgewertet.
  Liegt die Erfolgsquote (Läufe mit "published" vs. "skip"/"error") unter
  50 %, wird die Rampe NICHT weiter hochgefahren bzw. um 1 Tag/Woche
  reduziert (Boden: 2/Woche) – ein Symptom für strukturelle Probleme
  (Themenpool, KI-Provider, Prompt-Qualität), die zuerst behoben werden
  sollten, bevor mehr Volumen sinnvoll ist.

  Diese Automatik ersetzt NICHT eine echte, datengetriebene Skalierung
  anhand von Google Search Console (Indexierungsrate, Impressions,
  Positionsverlauf) – dafür fehlt aktuell der API-Zugang. Sobald die GSC
  API eingerichtet ist, kann dieses Skript um echte Performance-Signale
  erweitert werden (aktuell nur interne Qualitäts-/Erfolgssignale).

WIRKUNG: Schreibt die Cron-Tage in beiden Workflow-Dateien
(.github/workflows/content-engine-v2.yml, tagesziel-1-post.yml) neu und
committet die Änderung, falls sich die Zielfrequenz geändert hat. Läuft
wöchentlich (siehe .github/workflows/cadence-manager.yml).

Nutzung:
  python3 scripts/cadence_manager.py             # anwenden
  python3 scripts/cadence_manager.py --dry-run   # nur anzeigen
"""
import datetime
import glob
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIT_DIR = os.path.join(BLOG_DIR, "data", "audit")
CE_WORKFLOW = os.path.join(BLOG_DIR, ".github", "workflows", "content-engine-v2.yml")
TZ_WORKFLOW = os.path.join(BLOG_DIR, ".github", "workflows", "tagesziel-1-post.yml")
REPORT = os.path.join(BLOG_DIR, "CADENCE-REPORT.md")

LAUNCH_DATE = datetime.date(2026, 8, 8)  # Domain gültig seit diesem Tag
DRY_RUN = "--dry-run" in sys.argv

# Ramp-Stufen: (ab Woche X seit Launch, Ziel-Artikel/Woche)
RAMP = [(0, 3), (4, 4), (8, 5)]
CEILING = 5
FLOOR = 2
HEALTH_WINDOW_DAYS = 14
HEALTH_THRESHOLD = 0.5  # Erfolgsquote, unter der die Rampe gebremst wird

# Wochentags-Sets je Ziel-Frequenz (Cron day-of-week: Mo=1 ... So=0)
DAY_SETS = {
    1: [3],                    # Mi
    2: [1, 4],                 # Mo, Do
    3: [1, 3, 5],              # Mo, Mi, Fr
    4: [1, 3, 5, 6],           # Mo, Mi, Fr, Sa
    5: [1, 2, 4, 5, 6],        # Mo, Di, Do, Fr, Sa
    6: [1, 2, 3, 4, 5, 6],     # Mo-Sa
    7: [0, 1, 2, 3, 4, 5, 6],  # täglich
}
DAY_NAMES = {0: "So", 1: "Mo", 2: "Di", 3: "Mi", 4: "Do", 5: "Fr", 6: "Sa"}


def ramp_target(today: datetime.date) -> int:
    weeks = max(0, (today - LAUNCH_DATE).days // 7)
    target = RAMP[0][1]
    for week_threshold, value in RAMP:
        if weeks >= week_threshold:
            target = value
    return min(target, CEILING)


def health_success_rate(today: datetime.date):
    """Erfolgsquote der letzten HEALTH_WINDOW_DAYS Tage aus dem Audit-Log.
    Rückgabe: (rate|None, n_events). None = zu wenig Daten für eine Aussage
    (z. B. ganz am Anfang) -> Sicherheitsbremse greift dann NICHT."""
    cutoff = today - datetime.timedelta(days=HEALTH_WINDOW_DAYS)
    ok, total = 0, 0
    for path in glob.glob(os.path.join(AUDIT_DIR, "*.jsonl")):
        day_str = os.path.basename(path).replace(".jsonl", "")
        try:
            day = datetime.datetime.strptime(day_str, "%Y-%m-%d").date()
        except ValueError:
            continue
        if day < cutoff:
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    ev = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if ev.get("module") not in ("engine_generate", "daily_post_guard"):
                    continue
                total += 1
                if ev.get("status") == "ok":
                    ok += 1
    if total < 5:  # zu wenig Datenpunkte für eine belastbare Aussage
        return None, total
    return ok / total, total


def current_day_count(workflow_path: str) -> int:
    """Liest die aktuell im Workflow konfigurierte Tage/Woche-Zahl aus."""
    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()
    m = re.search(r'cron:\s*"\S+\s+\S+\s+\*\s+\*\s+([\d,]+)"', content)
    if not m:
        return 0
    return len(m.group(1).split(","))


def apply_day_set(workflow_path: str, days: list, cron_times: list):
    """Ersetzt ALLE Cron-Zeilen in der Workflow-Datei auf dieselbe Tages-
    Auswahl (Uhrzeiten bleiben, wie sie in der Datei vorgefunden werden)."""
    with open(workflow_path, encoding="utf-8") as f:
        content = f.read()
    days_str = ",".join(str(d) for d in days)

    def repl(m):
        return f'cron: "{m.group(1)} {m.group(2)} * * {days_str}"'

    new_content = re.sub(r'cron:\s*"(\S+)\s+(\S+)\s+\*\s+\*\s+[\d,]+"', repl, content)
    if new_content != content:
        with open(workflow_path, "w", encoding="utf-8") as f:
            f.write(new_content)
        return True
    return False


def main():
    today = datetime.date.today()
    weeks_since_launch = max(0, (today - LAUNCH_DATE).days // 7)
    target = ramp_target(today)
    rate, n_events = health_success_rate(today)

    braked = False
    if rate is not None and rate < HEALTH_THRESHOLD:
        braked = True
        target = max(FLOOR, target - 1)

    days = DAY_SETS.get(target, DAY_SETS[CEILING])
    day_names = ", ".join(DAY_NAMES[d] for d in sorted(days, key=lambda x: (x == 0, x)))

    current = current_day_count(CE_WORKFLOW)

    print(f"Domain-Alter: {weeks_since_launch} Wochen seit {LAUNCH_DATE.isoformat()}")
    print(f"Ramp-Ziel (ohne Bremse): {ramp_target(today)}/Woche")
    if rate is None:
        print(f"Erfolgsquote: noch zu wenig Daten ({n_events} Events in {HEALTH_WINDOW_DAYS} Tagen) – Sicherheitsbremse inaktiv")
    else:
        print(f"Erfolgsquote (letzte {HEALTH_WINDOW_DAYS} Tage, {n_events} Läufe): {rate:.0%}"
              + (" – UNTER 50%, Rampe gebremst" if braked else " – OK"))
    print(f"→ Ziel-Frequenz: {target}/Woche ({day_names})")
    print(f"  Aktuell konfiguriert: {current}/Woche")

    changed = False
    if target != current:
        print(f"  Ändere Konfiguration: {current} → {target} Artikel/Woche")
        if not DRY_RUN:
            changed |= apply_day_set(CE_WORKFLOW, days, None)
            changed |= apply_day_set(TZ_WORKFLOW, days, None)
    else:
        print("  Keine Änderung nötig.")

    if not DRY_RUN:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write(
                "# 📅 CADENCE-REPORT (automatische Publikationsfrequenz)\n\n"
                f"**Stand:** {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC\n\n"
                f"- Domain-Alter: {weeks_since_launch} Wochen (Launch {LAUNCH_DATE.isoformat()})\n"
                f"- Ramp-Ziel laut Zeitplan: {ramp_target(today)}/Woche\n"
                f"- Erfolgsquote (letzte {HEALTH_WINDOW_DAYS} Tage): "
                + (f"{rate:.0%} ({n_events} Läufe)\n" if rate is not None else "noch keine ausreichenden Daten\n")
                + f"- Sicherheitsbremse aktiv: {'JA – 1 Tag/Woche reduziert' if braked else 'nein'}\n"
                f"- **Aktuelle Ziel-Frequenz: {target} Artikel/Woche ({day_names})**\n\n"
                "_Automatisch erzeugt von scripts/cadence_manager.py "
                "(läuft wöchentlich, siehe .github/workflows/cadence-manager.yml)._\n"
            )

    return 1 if changed else 0


if __name__ == "__main__":
    sys.exit(main())
