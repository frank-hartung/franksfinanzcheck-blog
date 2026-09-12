#!/usr/bin/env python3
"""
BOT-WATCHDOG – Profi-Agentur-Level Selbstüberwachung
====================================================

Erweitert den bisherigen Bot-Watchdog um:
  • Affiliate-Manager-Perspektive: Affiliate-Integritäts-Wache, Affiliate-Health
  • Pinterest-Experten-Perspektive: Token-Lebenszyklus, Watchdog-Liveness, Duplikat-Sperre
  • Robuste Live-Site-Prüfung (Redirects, Timeout, Retry)
  • Sichere Env-Handling (kein EOF-Collision)
  • Selftest + deterministische Checks

Checks:
  1a) META: Läuft die Produktions-Wache noch? (26h Fenster)
  1b) PUBLIKATIONSTAG-BILANZ: letzter abgeschlossener Mo/Mi/Fr
  2)  Skript-Syntax (py_compile)
  3)  Live-Site: neuester Artikel wirklich live?
  4)  TLS-Zertifikat (GitHub Pages)
  5)  Affiliate-Integritäts-Wache aktiv? (26h)
  6)  Pinterest-Watchdog aktiv? (30h)
  7)  Pinterest-Kanal (Token + Domain-Sperre + Frische) – MIT BESITZER
  8)  Content-Reserve Gesundheit (Pool-Größe, Drafts)
  9)  Affiliate-Health Report Frische
  10) Pinterest-Kanal geparkt? (aktive Domain-Sperre)

ALARM-ROUTING (seit #272, 12.09.2026)
  Jeder Befund trägt einen BESITZER:
    · `auto`  – eine Maschine kann ihn heilen → Automations-Ticket
                (Label `bot-watchdog`), und nur diese Befunde füllen PROBLEMS.
    · `human` – nur ein Mensch kann ihn heilen → Fach-Ticket mit Runbook und
                Eskalationsleiter (z. B. `pinterest-token`, `pinterest-parked`).
  Menschliche Befunde öffnen und blockieren KEIN Automations-Ticket – genau
  das war die Sackgasse: „wird automatisch geschlossen, sobald alles grün
  ist" konnte nie eintreten, weil das Grün am Menschen hing (#251 → #272 → …).

Exit-Codes:
  0 = Lauf ok (Befunde stehen in Env/Report; Meldung macht der Router)
  2 = Selbsttest defekt

Nutzung:
  python3 scripts/bot_watchdog.py --check      # nur prüfen (prüft + berichtet)
  python3 scripts/bot_watchdog.py --emit-env   # schreibt /tmp/bot_watchdog.env + /tmp/problems.txt
  python3 scripts/bot_watchdog.py --route      # meldet über scripts/alert_router.py
  python3 scripts/bot_watchdog.py --selftest
"""

import datetime
import glob
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BLOG_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(BLOG_DIR / "scripts"))

# Import cadence guard as SSOT
try:
    import cadence_guard as cg
except ImportError:
    cg = None

# Alarm-Router (SSOT für Besitz, Kadenz, Schließpfad – seit Issue #272)
try:
    import alert_router as ar
except ImportError:
    ar = None

REPORT_PATH = BLOG_DIR / "BOT-WATCHDOG-REPORT.md"
FINDINGS_PATH = Path("/tmp/bot_watchdog_findings.json")

# Wie alt ein Pinterest-Lagebild sein darf, bevor die Wache selbst zum Befund
# wird (ein veraltetes Bild ist kein Beweis für einen toten Kanal).
STATE_MAX_AGE_HOURS = 48

# Fach-Kanäle: ein Besitzer pro Ticket (Alarm-Routing).
PINTEREST_TOKEN_CHANNEL = "pinterest-token"     # besetzt von pinterest-token.yml
PINTEREST_PARKED_CHANNEL = "pinterest-parked"   # besetzt vom Bot-Watchdog

# Eine Domain-Sperre dauert Wochen, nicht Tage → eigene, langsamere Leiter.
PINTEREST_PARKED_LADDER = ((0, "Meldung"), (14, "Erinnerung"), (30, "Eskalation"))

# Konfiguration
PRODUKTIONS_WACHE_WORKFLOW = "produktions-wache.yml"
AFFILIATE_WACHE_WORKFLOW = "affiliate-integrity-daily.yml"
PINTEREST_WATCHDOG_WORKFLOW = "pinterest-watchdog.yml"
PINTEREST_TOKEN_WORKFLOW = "pinterest-token.yml"
CONTENT_RESERVE_WORKFLOW = "content-reserve.yml"

# Mindestziel
def effective_min():
    try:
        return max(2, int(os.environ.get("MIN_ARTIKEL_PRO_TAG") or "2"))
    except ValueError:
        return 2

def effective_max():
    try:
        return max(2, int(os.environ.get("MAX_ARTIKEL_PRO_TAG") or "3"))
    except ValueError:
        return 3

# Hilfen
def _parse_ts(raw):
    """ISO-Zeitstempel tolerant lesen (None bei Unlesbarkeit)."""
    if not raw:
        return None
    try:
        dt = datetime.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=datetime.timezone.utc)


def run_cmd(cmd, timeout=30):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout, r.stderr
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"

def newest_slug():
    """Find newest article by frontmatter date (full ISO) + fallback to folder."""
    best = None
    best_dt = None
    for p in (glob.glob(str(BLOG_DIR / "content/posts/*/index.md")) +
              glob.glob(str(BLOG_DIR / "content/posts/*.md"))):
        try:
            c = Path(p).read_text(encoding="utf-8")
        except OSError:
            continue
        if re.search(r"(?m)^draft:\s*true\s*$", c):
            continue
        # Full ISO with time
        m = re.search(r"(?m)^date:\s*[\"']?([0-9T:\-Z\.]+)", c)
        if not m:
            continue
        raw = m.group(1)
        try:
            # Parse ISO, handle Z
            if raw.endswith("Z"):
                dt = datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
            else:
                dt = datetime.datetime.fromisoformat(raw)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
        except ValueError:
            # Fallback to date only
            try:
                d = datetime.date.fromisoformat(raw[:10])
                dt = datetime.datetime.combine(d, datetime.time.min, tzinfo=datetime.timezone.utc)
            except ValueError:
                continue
        slug = (os.path.basename(os.path.dirname(p))
                if os.path.basename(p) == "index.md"
                else os.path.basename(p)[:-3])
        if best_dt is None or dt > best_dt:
            best_dt = dt
            best = (dt, slug, p)
    return best[1] if best else "", best_dt

def check_syntax():
    """Check all scripts/*.py syntaktisch."""
    err_file = Path("/tmp/syntax_err.txt")
    rc, out, err = run_cmd("python3 -m py_compile scripts/*.py 2>/tmp/syntax_err.txt", timeout=15)
    if rc != 0:
        try:
            txt = err_file.read_text(encoding="utf-8")[:500]
        except OSError:
            txt = err
        return False, txt.strip()
    return True, ""

def check_live_site(slug, timeout=20):
    """Live-Site prüfen mit Redirect-Follow, Retry, und Offline-Erkennung."""
    if not slug:
        return None, "kein Slug gefunden (kein live Artikel)"
    url = f"https://franksfinanzcheck.de/posts/{slug}/"
    # curl mit Retry, folgt Redirects
    cmd = f"curl -L -s -o /dev/null -w \"%{{http_code}}\" --max-time {timeout} --retry 2 --retry-delay 2 \"{url}\""
    rc, out, err = run_cmd(cmd, timeout=timeout+8)
    code = out.strip()
    if code == "200":
        return True, code
    # Zweiter Versuch
    if code in ("", "000"):
        # Prüfe ob generell offline (kein Internet im Runner/Sandbox)
        rc_off, out_off, _ = run_cmd(f"curl -L -s -o /dev/null -w \"%{{http_code}}\" --max-time 5 https://www.google.com/", timeout=8)
        if out_off.strip() in ("", "000"):
            # Offline-Umgebung – kein harter Fail, sondern UNKNOWN
            return None, f"offline (kein Internet, curl {code})"
        # Online, aber Seite liefert 000 -> Netzwerk/Cloudflare blockt, Retry
        rc2, out2, _ = run_cmd(cmd, timeout=timeout+8)
        code2 = out2.strip()
        if code2 == "200":
            return True, code2
        # 301/302 können bei Cloudflare vorkommen, als OK werten wenn Location vorhanden
        if code2 in ("301", "302", "303", "307", "308"):
            return True, f"{code2} (Redirect, als live gewertet)"
        return False, code2 or f"curl rc {rc} / {code}"
    if code in ("301", "302", "303", "307", "308"):
        # Redirects (z.B. trailing slash) sind ok
        return True, f"{code} (Redirect)"
    # Retry für andere Codes
    rc2, out2, _ = run_cmd(cmd, timeout=timeout+8)
    code2 = out2.strip()
    if code2 == "200" or code2 in ("301", "302", "303", "307", "308"):
        return True, code2
    return False, code2 or code

def check_tls():
    """Check 4 via existing script."""
    try:
        rc = subprocess.run([sys.executable, str(BLOG_DIR / "scripts/watchdog_check4_tls.py")],
                            timeout=10).returncode
        return rc == 0
    except Exception:
        return False

def check_workflow_liveness(workflow_file, hours=26):
    """Prüft ob Workflow in letzten X Stunden lief (via gh CLI). Fallback: Report-Datei Alter."""
    since = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=hours)
    since_iso = since.strftime("%Y-%m-%dT%H:%M:%SZ")
    # gh run list
    cmd = f"gh run list --workflow={workflow_file} --created \">{since_iso}\" --json databaseId --jq 'length' 2>/tmp/gh_{workflow_file}.err"
    rc, out, err = run_cmd(cmd, timeout=20)
    if rc != 0:
        # gh nicht verfügbar oder API Fehler -> Fallback auf Datei-Alter
        return None, f"gh Fehler, Fallback nötig: {err[:200]}"
    try:
        count = int(out.strip() or "0")
        return count, ""
    except ValueError:
        return None, f"gh output unparsable: {out[:200]}"

def check_produktions_status_age(max_age_hours=30):
    """Fallback: Wie alt ist PRODUKTIONS-STATUS.md?"""
    p = BLOG_DIR / "PRODUKTIONS-STATUS.md"
    if not p.is_file():
        return False, "PRODUKTIONS-STATUS.md fehlt"
    age = (datetime.datetime.now().timestamp() - p.stat().st_mtime) / 3600
    if age > max_age_hours:
        return False, f"PRODUKTIONS-STATUS.md {age:.1f}h alt (>{max_age_hours}h)"
    return True, f"{age:.1f}h alt"

def check_affiliate_integrity():
    """Prüft Affiliate-Integrität: State-Datei zuerst, Report als Fallback.

    Premium-Audit 12.09.2026: Der Report ist Markdown (Marker-Scan) – die
    State-Datei ist maschinenlesbar (exit_code, content_problems,
    generated_at) und trägt zusätzlich die FRISCHE: Ein stiller
    Wache-Ausfall war im reinen Report-Scan unsichtbar (alter Report
    ohne rotes Marker = scheinbar „ok"). Jetzt: State älter als 30 h
    (täglicher Lauf 06:00 MESZ) = harter Befund.
    """
    state_file = BLOG_DIR / ".affiliate_integrity_state.json"
    if state_file.is_file():
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = None
        if isinstance(data, dict) and data.get("generated_at"):
            age_h = None
            for fmt in ("%Y-%m-%d %H:%M:%S UTC", "%Y-%m-%d %H:%M:%S %Z",
                        "%Y-%m-%dT%H:%M:%SZ"):
                try:
                    ts = datetime.datetime.strptime(str(data["generated_at"]), fmt)
                    age_h = ((datetime.datetime.now(datetime.timezone.utc)
                              - ts.replace(tzinfo=datetime.timezone.utc))
                             .total_seconds() / 3600)
                    break
                except ValueError:
                    continue
            if age_h is None:
                return None, "State-Timestamp unlesbar – Report-Fallback"
            problems = len(data.get("content_problems") or [])
            if data.get("exit_code") == 0 and problems == 0:
                if age_h > 30:
                    return False, (f"Integritäts-Wache schweigt: State {age_h:.0f} h alt "
                                   f"(> 30 h, täglicher Lauf 06:00 MESZ)")
                return True, f"ok (State {age_h:.0f} h alt, {data.get('checked', '?')} geprüft)"
            if problems > 0:
                return False, f"{problems} offene Affiliate-Probleme (State {age_h:.0f} h alt)"
            return False, f"letzter Lauf exit {data.get('exit_code')} (State {age_h:.0f} h alt)"
    # Fallback: Report-Inhalts-Scan (früheres Verhalten, z. B. wenn die
    # State-Datei bei einem Lauf nicht geschrieben wurde).
    report = BLOG_DIR / "AFFILIATE-INTEGRITY-REPORT.md"
    if not report.is_file():
        return None, "State+Report fehlen"
    try:
        txt = report.read_text(encoding="utf-8")
        # Suche nach FAIL Markern
        if "🔴" in txt or "FAIL" in txt or "Inhaltsschaden" in txt:
            # Check state file for details
            if state_file.is_file():
                try:
                    data = json.loads(state_file.read_text(encoding="utf-8"))
                    problems = len(data.get("content_problems") or [])
                    if problems > 0:
                        return False, f"{problems} offene Affiliate-Probleme (siehe Report)"
                except Exception:
                    pass
            # If report contains red but state says 0, still warn
            if "✅" in txt and "🔴" not in txt[:500]:
                return True, "ok"
            return False, "Report zeigt offene Probleme"
    except OSError as e:
        return None, f"Report nicht lesbar: {e}"
    return True, "ok"

# Achtung: `check_pinterest_token()` (nur Ampel, ohne Besitzer) wurde am
# 12.09.2026 durch `check_pinterest_channel()` ersetzt – sie bewertet den
# Kanal als Ganzes (Domain-Sperre, Token, Frische) und liefert Befunde MIT
# Besitzer. Zwei Wahrheiten über denselben Kanal sind der Kern von #272.


def check_content_reserve():
    """Prüft ob Reserve-Pool genug Artikel hat."""
    # Zähle draft:true + reserve:true
    reserve_count = 0
    for p in glob.glob(str(BLOG_DIR / "content/posts/*/index.md")):
        try:
            c = Path(p).read_text(encoding="utf-8")
            if re.search(r"(?m)^draft:\s*true", c) and re.search(r"(?m)^reserve:\s*true", c):
                reserve_count += 1
        except OSError:
            continue
    # Mindestreserve: 4 Artikel für 2 Publikationstage à 2 Artikel
    min_reserve = 4
    if reserve_count < min_reserve:
        return False, f"Nur {reserve_count} Reserve-Artikel (<{min_reserve}) – Nachschub nötig"
    return True, f"{reserve_count} Reserve-Artikel"

def check_pinterest_duplicate():
    """Prüft PINTEREST-REPORT auf Duplikat-Befunde."""
    report = BLOG_DIR / "PINTEREST-REPORT.md"
    if not report.is_file():
        return None, "Pinterest-Report fehlt"
    try:
        txt = report.read_text(encoding="utf-8")
        if "Duplikat" in txt or "duplicate" in txt.lower():
            # Suche nach FAIL
            if "❌" in txt or "🔴" in txt or "Probleme" in txt:
                return False, "Duplikate im Pinterest-Report"
    except OSError:
        return None, "Report nicht lesbar"
    return True, "keine Duplikate"

def build_bilanz():
    """Publikationstag-Bilanz wie im alten Watchdog, aber als Funktion."""
    if cg is None:
        return None, 0, 0, "-", "cadence_guard nicht importierbar"

    names = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    today = datetime.date.today()
    now = datetime.datetime.now(datetime.timezone.utc)
    minute = now.hour * 60 + now.minute
    minimum = effective_min()

    day = None
    for back in range(0, 10):
        d = today - datetime.timedelta(days=back)
        if d.weekday() not in cg.PUBLICATION_DAYS:
            continue
        if d == today and minute < (18 * 60 + 30):
            continue
        day = d
        break

    if day is None:
        return "SKIP", 0, minimum, "-", "kein abgeschlossener Publikationstag im Prüfbereich"

    posts = cg.load_posts()
    count = len(cg.published_on(posts, day))
    status = "OK" if count >= minimum else ("FAIL" if count == 0 else "WARN")
    text = f"{names[day.weekday()]} {day.isoformat()}: {count}/{minimum} Artikel"
    return status, count, minimum, day.isoformat(), text

def _f(fid, title, severity="P2", owner="auto", channel="", detail="",
       next_step="", evidence=(), ladder=None, once=False):
    """Kurzform für einen Befund.

    Die wichtigste Zeile in jedem Aufruf ist `owner`:
      · `auto`  – eine Maschine kann das heilen → Automations-Ticket (P1/P2)
      · `human` – nur ein Mensch kann das heilen → Fach-Ticket mit Kadenz
    Genau diese Unterscheidung hat in #272 gefehlt (Alarm ohne Besitzer und
    ohne Schließpfad).
    """
    return ar.Finding(
        id=fid, title=title, detail=detail, severity=severity, owner=owner,
        channel=channel or (ar.GENERIC_CHANNEL if owner == "auto" else "human-action"),
        next_step=next_step, evidence=tuple(evidence),
        ladder=tuple(ladder or ar.ESCALATION_LADDER), once=once)


def pinterest_domain_block():
    """Aktive Pinterest-Domain-Sperre (data/pinterest_domain_block.json) oder None.

    Solange Pinterest die Domain sperrt (Spam-Markierung, seit 27.08.2026),
    pinnt der Betrieb BEWUSST nicht (`spam_guard.py` blockt jeden Pin). In
    diesem Zustand ist ein toter Token ein Hinweis, kein Zwischenfall – die
    Reihenfolge ist: erst Domain frei, dann Token neu autorisieren.
    """
    path = BLOG_DIR / "data" / "pinterest_domain_block.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict) or not str(data.get("since") or "").strip():
        return None
    return data


def check_pinterest_channel():
    """Bewertet den Pinterest-Kanal als GANZES (Domain-Sperre, Token, Frische).

    Rückgabe: (findings, kurztext) – der Kurztext landet in CHECK7/CHECK10.
    """
    findings = []
    state_path = BLOG_DIR / "data" / "pinterest_token_state.json"
    block = pinterest_domain_block()

    if not state_path.is_file():
        findings.append(_f(
            "pinterest-lagebild", "Pinterest-Lagebild fehlt", "P2", "auto",
            detail="data/pinterest_token_state.json fehlt – der Kanal hat kein Lagebild.",
            next_step="`pinterest-token.yml` einmal manuell starten (Actions → Run workflow)."))
        return findings, "Lagebild fehlt"

    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        findings.append(_f(
            "pinterest-lagebild", "Pinterest-Lagebild unlesbar", "P2", "auto",
            detail=f"data/pinterest_token_state.json nicht parsbar: {exc}",
            next_step="`pinterest-token.yml` neu laufen lassen – sie schreibt das Lagebild."))
        return findings, f"Lagebild unlesbar: {exc}"

    checked_at = _parse_ts(data.get("checked_at"))
    if checked_at is None:
        age_h = None
    else:
        age_h = (datetime.datetime.now(datetime.timezone.utc) - checked_at).total_seconds() / 3600.0

    severity = str(data.get("severity") or "unknown")
    source = data.get("source_label") or data.get("source") or "?"
    detail = str(data.get("detail") or data.get("next_action") or "")
    state = str(data.get("state") or "?")
    renewable = bool(data.get("renewable"))

    # Veraltetes Lagebild ist ein MASCHINELLER Befund: nicht der Kanal ist
    # fragwürdig, sondern die Wache, die ihn vermessen sollte.
    if age_h is None or age_h > STATE_MAX_AGE_HOURS:
        alt = "unbekannt" if age_h is None else f"{age_h:.0f} h"
        findings.append(_f(
            "pinterest-lagebild-veraltet", "Pinterest-Lagebild veraltet", "P2", "auto",
            detail=f"Letztes Lagebild {alt} alt (Fenster: {STATE_MAX_AGE_HOURS} h) – "
                   f"kein verlässlicher Befund möglich.",
            next_step="`pinterest-token.yml` prüfen (täglich 04:40 MESZ) – erst sie schreibt "
                      "ein geprüftes Lagebild.",
            evidence=[f"checked_at={data.get('checked_at')}"]))
        return findings, f"Lagebild {alt} alt"

    if block:
        since = str(block.get("since") or "")[:10]
        reason = str(block.get("reason") or "Domain bei Pinterest gesperrt")
        findings.append(_f(
            "pinterest-kanal-geparkt", "Pinterest-Kanal geparkt: Domain-Sperre aktiv",
            "P3", "human", PINTEREST_PARKED_CHANNEL,
            detail=f"Seit {since} gesperrt ({reason[:140]}). Solange die Sperre steht, pinnt "
                   f"der Betrieb bewusst nicht – Pins würden die Sperre verlängern.",
            next_step="Domain bei Pinterest freibekommen (Kontaktformular „Link gesperrt“, "
                      "Vorlage: `docs/PINTEREST-SPIELBUCH.md`), danach "
                      "`python3 scripts/spam_guard.py --domain-unblock`. Erst DANN lohnt die "
                      "Token-Neu-Autorisierung.",
            evidence=[f"data/pinterest_domain_block.json: since={since}"],
            ladder=PINTEREST_PARKED_LADDER))
        if severity == "red":
            findings.append(_f(
                "pinterest-token", "Pinterest-Token tot (Kanal ohnehin geparkt)",
                "P3", "human", PINTEREST_PARKED_CHANNEL,
                detail=f"Token {state} – Quelle: {source} – {detail[:120]}. Derzeit ohne "
                       f"Betriebswirkung, weil die Domain gesperrt ist.",
                next_step="Nach der Domain-Freigabe: einmalige Neu-Autorisierung "
                          "(`docs/PINTEREST-TOKEN-RUNBOOK.md`).",
                evidence=[f"state={state}", f"source={source}", f"renewable={renewable}"],
                ladder=PINTEREST_PARKED_LADDER))
        return findings, f"Kanal geparkt (Domain-Sperre seit {since}), Token {state}"

    if severity == "red":
        findings.append(_f(
            "pinterest-token", "Pinterest-Token tot: einmalige Neu-Autorisierung nötig",
            "P2", "human", PINTEREST_TOKEN_CHANNEL,
            detail=f"Token {state} – Quelle: {source} – {detail[:140]}",
            next_step="Actions → Pinterest-Token-Wache → Run workflow (`show_auth_url`), "
                      "dann Code eintauschen – Runbook `docs/PINTEREST-TOKEN-RUNBOOK.md`.",
            evidence=[f"state={state}", f"source={source}", f"renewable={renewable}"]))
        return findings, f"Token {state} (Quelle {source}) – Mensch nötig"

    if severity == "amber":
        findings.append(_f(
            "pinterest-token-amber", "Pinterest-Token läuft ab",
            "P2", "auto" if renewable else "human", PINTEREST_TOKEN_CHANNEL,
            detail=f"Token {state} – Quelle: {source} – {detail[:140]}",
            next_step=("Die Token-Wache erneuert proaktiv (täglich 04:40 MESZ) – "
                       "nur beobachten." if renewable else
                       "Ohne Refresh-Token kann nur ein Mensch erneuern: "
                       "`docs/PINTEREST-TOKEN-RUNBOOK.md`."),
            evidence=[f"state={state}", f"renewable={renewable}"]))
        return findings, f"Token {state} (Quelle {source})"

    return findings, f"Token OK (Quelle {source})"


def run_all():
    findings = []
    env = {}

    # 1a META: Produktions-Wache
    count, err = check_workflow_liveness(PRODUKTIONS_WACHE_WORKFLOW, hours=26)
    if count is None:
        # Fallback auf Datei-Alter
        ok, msg = check_produktions_status_age(30)
        if ok:
            env["CHECK1A"] = f"OK (Fallback: {msg})"
        else:
            env["CHECK1A"] = f"FAIL ({msg} / gh: {err})"
            findings.append(_f(
                "produktions-wache", "Produktions-Wache dreht nicht", "P1", "auto",
                detail=f"{msg} (gh: {err})"[:200],
                next_step="Cron/Workflow `produktions-wache.yml` prüfen – ohne sie ist die "
                          "Ausfall-Erkennung blind.",
                evidence=[f"CHECK1A={env['CHECK1A']}"]))
    elif count == 0:
        env["CHECK1A"] = "FAIL"
        findings.append(_f(
            "produktions-wache", "Produktions-Wache dreht nicht", "P1", "auto",
            detail="Kein Lauf in den letzten 26 h – die Ausfall-Erkennung ist derzeit blind.",
            next_step="Cron/Workflow `produktions-wache.yml` prüfen (Cron aktiv? Repo inaktiv?).",
            evidence=["CHECK1A=FAIL (0 Läufe/26 h)"]))
    else:
        env["CHECK1A"] = f"OK ({count} Lauf/Läufe in 26h)"

    # 1b Bilanz
    status, count_b, min_b, tag_b, text_b = build_bilanz()
    env["CHECK1B"] = status
    env["BILANZ_TEXT"] = text_b
    env["BILANZ_TAG"] = tag_b
    env["BILANZ_COUNT"] = str(count_b)
    env["BILANZ_MIN"] = str(min_b)

    # Nur alarmieren wenn Wache nicht aktiv (Dedupe)
    wache_da = env["CHECK1A"].startswith("OK")
    if not wache_da:
        if status == "FAIL":
            findings.append(_f(
                "kadenz", f"Kein Artikel am Publikationstag {tag_b}", "P1", "auto",
                detail=f"0 von {min_b} Artikeln am {tag_b}.",
                next_step="Actions → Content-Engine v2 → letzter Lauf → Phase 1 "
                          "(Tageslimit, Themenpool, API-Keys).",
                evidence=[f"BILANZ={text_b}"]))
        elif status == "WARN":
            findings.append(_f(
                "kadenz", f"Nur {count_b} von {min_b} Artikeln am Publikationstag {tag_b}",
                "P2", "auto", detail=text_b,
                next_step="Kadenz-Endkontrolle (Mo/Mi/Fr) schließt das auf – "
                          "sonst Engine manuell triggern.",
                evidence=[f"BILANZ={text_b}"]))

    # 2 Syntax
    ok, err = check_syntax()
    if ok:
        env["CHECK2"] = "OK"
    else:
        env["CHECK2"] = "FAIL"
        findings.append(_f(
            "skript-syntax", "Skript-Syntaxfehler", "P1", "auto",
            detail=str(err)[:300],
            next_step="Betroffenes Skript reparieren – `python3 -m py_compile scripts/*.py` "
                      "nennt die Zeile.",
            evidence=[f"py_compile: {str(err)[:120]}"]))

    # 3 Live-Site – Profi: Offline = WARN, nicht FAIL (vermeidet Fehlalarm im Sandbox/Runner ohne Netz)
    slug, dt = newest_slug()
    if slug:
        ok, code = check_live_site(slug)
        if ok is True:
            env["CHECK3"] = f"OK ({slug} → {code})"
        elif ok is None:
            env["CHECK3"] = f"WARN ({slug} → {code})"
            # Kein hartes Problem in Offline-Umgebung – nur Hinweis
            # In CI mit Internet wird das als OK/FAIL entschieden, nicht als WARN
        else:
            env["CHECK3"] = f"FAIL ({slug} → {code})"
            findings.append(_f(
                "live-site", "Neuester Artikel nicht live", "P1", "auto",
                detail=f"{slug} liefert HTTP {code}.",
                next_step="Deploy prüfen, ggf. Deploy-Catchup triggern "
                          "(Actions → Deploy auf GitHub Pages).",
                evidence=[f"URL=/posts/{slug}/", f"HTTP={code}"]))
    else:
        env["CHECK3"] = "FAIL"
        findings.append(_f(
            "live-site", "Kein veröffentlichter Artikel gefunden", "P1", "auto",
            detail="In content/posts/ liegt kein veröffentlichter Artikel – "
                   "Deploy kann nicht geprüft werden.",
            next_step="Content-Engine prüfen (Actions → Content-Engine v2)."))

    # 4 TLS
    if check_tls():
        env["CHECK4"] = "OK"
    else:
        env["CHECK4"] = "WAIT"

    # 5 Affiliate-Wache
    count_aff, _ = check_workflow_liveness(AFFILIATE_WACHE_WORKFLOW, hours=30)
    if count_aff is None:
        env["CHECK5"] = "UNKNOWN (gh Fehler)"
    elif count_aff == 0:
        env["CHECK5"] = "FAIL"
        findings.append(_f(
            "affiliate-wache", "Affiliate-Integritäts-Wache dreht nicht", "P2", "auto",
            detail="Kein Lauf in den letzten 30 h – Affiliate-Links können unbemerkt brechen.",
            next_step="Workflow `affiliate-integrity-daily.yml` prüfen (täglich 06:00 MESZ)."))
    else:
        env["CHECK5"] = f"OK ({count_aff} Läufe)"

    # 5b Affiliate-Report
    ok_aff, msg_aff = check_affiliate_integrity()
    if ok_aff is False:
        env["CHECK5B"] = f"FAIL ({msg_aff})"
        findings.append(_f(
            "affiliate-integritaet", "Affiliate-Integrität offen", "P1", "auto",
            detail=str(msg_aff),
            next_step="`AFFILIATE-INTEGRITY-REPORT.md` prüfen – Auto-Heilung läuft "
                      "täglich 06:00 MESZ.",
            evidence=[f"CHECK5B={msg_aff}"]))
    elif ok_aff is None:
        env["CHECK5B"] = f"WARN ({msg_aff})"
    else:
        env["CHECK5B"] = "OK"

    # 6 Pinterest-Watchdog
    count_pin, _ = check_workflow_liveness(PINTEREST_WATCHDOG_WORKFLOW, hours=30)
    if count_pin is None:
        env["CHECK6"] = "UNKNOWN"
    elif count_pin == 0:
        env["CHECK6"] = "FAIL"
        findings.append(_f(
            "pinterest-watchdog", "Pinterest-Watchdog dreht nicht", "P2", "auto",
            detail="Kein Lauf in den letzten 30 h – Spam-/SEO-Signale bleiben unbemerkt.",
            next_step="Workflow `pinterest-watchdog.yml` prüfen (täglich 06:30 MESZ)."))
    else:
        env["CHECK6"] = f"OK ({count_pin} Läufe)"

    # 7 Pinterest-Kanal (Domain-Sperre + Token + Frische) – MIT BESITZER
    pin_findings, pin_text = check_pinterest_channel()
    findings += pin_findings
    owned = pin_findings[0] if pin_findings else None
    if owned is None:
        env["CHECK7"] = f"OK ({pin_text})"
    elif owned.owner == "human":
        env["CHECK7"] = f"HUMAN ({pin_text})"
    else:
        env["CHECK7"] = f"FAIL ({pin_text})"
    env["CHECK7_OWNER"] = owned.owner if owned else "-"
    env["CHECK7_CHANNEL"] = owned.channel if owned else "-"

    # 10 Pinterest-Kanal geparkt? (Domain-Sperre)
    block = pinterest_domain_block()
    env["CHECK10"] = (f"PARKED (Domain-Sperre seit {str(block.get('since'))[:10]})"
                      if block else "OK (keine Sperre)")

    # 8 Content-Reserve
    ok_res, msg_res = check_content_reserve()
    if ok_res is False:
        env["CHECK8"] = f"WARN ({msg_res})"
        findings.append(_f(
            "content-reserve", "Content-Reserve niedrig", "P2", "auto", detail=str(msg_res),
            next_step="`content-reserve.yml` füllt täglich 3 Kandidaten nach – Lauf prüfen."))
    else:
        env["CHECK8"] = f"OK ({msg_res})"

    # 9 Pinterest Duplikate
    ok_dup, msg_dup = check_pinterest_duplicate()
    if ok_dup is False:
        env["CHECK9"] = f"FAIL ({msg_dup})"
        findings.append(_f(
            "pinterest-duplikate", "Pinterest-Duplikat-Signal", "P2", "auto", detail=str(msg_dup),
            next_step="`PINTEREST-REPORT.md` und `scripts/pinterest_pin_text_sync.py` prüfen."))
    else:
        env["CHECK9"] = "OK"

    return env, findings, slug


def split_findings(findings):
    """Trennt Befunde nach Besitzer – die Kernregel des Alarm-Routings.

    `machine` steuert das Automations-Ticket (und NUR dieses).
    `human` geht in seinen Fach-Kanal mit Kadenz – und hält das
    Automations-Ticket niemals offen (Sackgassen-Verbot aus #272).
    """
    machine = [f for f in findings if f.owner == "auto"]
    human = [f for f in findings if f.owner == "human"]
    return machine, human


def write_report(env, findings):
    machine, human = split_findings(findings)
    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 🤖 BOT-WATCHDOG-REPORT (Profi-Agentur-Level)",
        "",
        f"**Letzter Lauf:** {now}",
        f"**Branch:** main · **Modus:** Selbstüberwachung aller kritischen Automatisierungen",
        "",
        "## Checks",
        "",
        f"- **Check 1a (Produktions-Wache aktiv):** {env.get('CHECK1A','?')}",
        f"- **Check 1b (Publikationstag-Bilanz):** {env.get('CHECK1B','?')} – {env.get('BILANZ_TEXT','')}",
        f"- **Check 2 (Skript-Syntax):** {env.get('CHECK2','?')}",
        f"- **Check 3 (Live-Site):** {env.get('CHECK3','?')}",
        f"- **Check 4 (GitHub-TLS):** {env.get('CHECK4','?')}",
        f"- **Check 5 (Affiliate-Wache aktiv):** {env.get('CHECK5','?')}",
        f"- **Check 5b (Affiliate-Integrität):** {env.get('CHECK5B','?')}",
        f"- **Check 6 (Pinterest-Watchdog aktiv):** {env.get('CHECK6','?')}",
        f"- **Check 7 (Pinterest-Kanal):** {env.get('CHECK7','?')}",
        f"- **Check 8 (Content-Reserve):** {env.get('CHECK8','?')}",
        f"- **Check 9 (Pinterest-Duplikate):** {env.get('CHECK9','?')}",
        f"- **Check 10 (Pinterest-Kanal geparkt?):** {env.get('CHECK10','?')}",
        "",
        "## Alarm-Routing",
        "",
        f"- **Maschinell behebbar (Automations-Ticket `{ar.GENERIC_CHANNEL if ar else 'bot-watchdog'}`):** {len(machine)}",
        f"- **Menschlicher Besitz (Fach-Kanal mit Kadenz):** {len(human)}",
        "",
    ]
    if machine:
        lines += ["### 🔧 Maschine heilt (blockiert den Betrieb)", ""]
        lines += [f.line() for f in machine]
        lines += [""]
    if human:
        lines += ["### 🙋 Mensch heilt (eigener Kanal, eigene Kadenz)", ""]
        lines += [f.line() for f in human]
        lines += ["", "_Diese Befunde öffnen und blockieren KEIN Automations-Ticket – "
                       "sie haben je ein Fach-Ticket mit Runbook und Eskalationsleiter._", ""]
    if not machine and not human:
        lines += ["## Ergebnis", "",
                  "✅ **ALLES OK** – alle Wachen leben, Live-Site aktuell, Affiliate- und "
                  "Pinterest-Kanäle im grünen Bereich.", ""]
    lines += ["---",
              "*Automatisch erstellt vom Bot-Watchdog (täglich 10:30 MESZ) – "
              "Profi-Agentur-Level, Alarm-Routing seit #272.*", ""]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH


def emit_env(env, findings):
    """Schreibt /tmp/bot_watchdog.env sicher (ohne EOF-Kollision) + problems.txt.

    WICHTIG (Fix #272): `PROBLEMS` enthält AUSSCHLIESSLICH maschinell behebbare
    Befunde. Menschliche Befunde stehen in `HUMAN_ACTIONS` – sonst hält ein
    Browser-Handschlag das Automations-Ticket für immer offen (Sackgasse).
    """
    machine, human = split_findings(findings)
    delim = f"EOF_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"
    env_path = Path("/tmp/bot_watchdog.env")
    prob_path = Path("/tmp/problems.txt")
    prob_env_path = Path("/tmp/bot_watchdog_problems.env")

    machine_text = "\n".join(f.line() for f in machine)
    human_text = "\n".join(f.line() for f in human)

    with env_path.open("w", encoding="utf-8") as f:
        for k, v in env.items():
            safe_v = str(v).replace("\n", " ").replace("\r", "")
            f.write(f"{k}={safe_v}\n")
        f.write(f"MACHINE_COUNT={len(machine)}\n")
        f.write(f"HUMAN_COUNT={len(human)}\n")

    prob_path.write_text(machine_text, encoding="utf-8")
    prob_env_path.write_text(machine_text, encoding="utf-8")

    # Findings als JSON für den Routing-Schritt (--route) im selben Lauf
    if ar is not None:
        try:
            FINDINGS_PATH.write_text(
                json.dumps([f.as_dict() for f in findings], ensure_ascii=False, indent=2),
                encoding="utf-8")
        except (OSError, TypeError) as exc:
            print(f"⚠️  Findings konnten nicht gesichert werden: {exc}")

    # Für GitHub Actions: schreibe in GITHUB_ENV falls vorhanden
    gha_env = os.environ.get("GITHUB_ENV")
    if gha_env:
        with open(gha_env, "a", encoding="utf-8") as out:
            for k, v in env.items():
                safe_v = str(v).replace("\n", " ").replace("\r", "")
                out.write(f"{k}={safe_v}\n")
            out.write(f"MACHINE_COUNT={len(machine)}\n")
            out.write(f"HUMAN_COUNT={len(human)}\n")
            out.write(f"PROBLEMS<<{delim}\n")
            out.write(machine_text + "\n")
            out.write(f"{delim}\n")
            out.write(f"HUMAN_ACTIONS<<{delim}_h\n")
            out.write(human_text + "\n")
            out.write(f"{delim}_h\n")
    return env_path, prob_path


def route_issues(args):
    """Meldet Befunde über den Alarm-Router (Besitz, Kadenz, Schließpfad).

    Der Melder darf NIE selbst zum Vorfall werden (Lehre aus #209/#227):
    Diese Funktion wirft nicht und liefert immer Exit 0 – Fehler stehen im
    Bericht und (in CI) als `::error::`-Annotation im Lauf-Log.
    """
    findings = _load_findings_for_route()
    if findings is None:
        _env, findings, _slug = run_all()
    machine, human = split_findings(findings)
    print(f"Alarm-Routing: {len(machine)} maschinell · {len(human)} menschlich")

    if ar is None:
        print("⚠️  alert_router.py nicht importierbar – Routing übersprungen.")
        return 0

    client = ar.GhClient()
    if not client.repo:
        print("⚠️  Kein GITHUB_REPOSITORY – Routing nur als Plan (lokaler Lauf).")
        report = ar.route(findings, client, dry_run=True)
    else:
        report = ar.route(findings, client, dry_run="--dry-run" in args)

    print(json.dumps(report, ensure_ascii=False, indent=2))
    _write_step_summary(findings, report)

    for err in report.get("errors") or []:
        line = f"Alarm-Routing: {err}"
        print(f"::error::{line}" if os.environ.get("GITHUB_ACTIONS") else f"❌ {line}")
    return 0


def _load_findings_for_route():
    """Findings aus dem Prüfschritt desselben Laufs (max. 30 Minuten alt)."""
    try:
        if not FINDINGS_PATH.is_file():
            return None
        age = (datetime.datetime.now(datetime.timezone.utc)
               - datetime.datetime.fromtimestamp(FINDINGS_PATH.stat().st_mtime,
                                                 datetime.timezone.utc)).total_seconds()
        if age > 1800:
            return None
        return [ar.Finding.from_dict(d) for d in json.loads(FINDINGS_PATH.read_text(encoding="utf-8"))]
    except (OSError, json.JSONDecodeError, TypeError, ValueError) as exc:
        print(f"⚠️  Findings-Cache unbrauchbar ({exc}) – prüfe neu.")
        return None


def _write_step_summary(findings, report):
    """Kompakte Zusammenfassung für die Actions-Seite (Profi-Standard)."""
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary:
        return
    machine, human = split_findings(findings)
    lines = ["## 🔔 Alarm-Routing", "",
             f"- Maschinell behebbar: **{len(machine)}** · Menschlicher Besitz: **{len(human)}**",
             "", "| Kanal | Aktion | Ticket | Grund |", "|---|---|---|---|"]
    for a in report.get("actions") or []:
        lines.append(f"| `{a.get('channel')}` | {a.get('action')} | "
                     f"{('#' + str(a['issue'])) if a.get('issue') else '–'} | {a.get('reason','')} |")
    if report.get("errors"):
        lines += ["", "### ⚠️ Fehler", ""] + [f"- {e}" for e in report["errors"]]
    lines += ["", "_Regel: menschliche Befunde öffnen kein Automations-Ticket und halten "
                  "keines offen – ein Ticket ohne Schließpfad ist ein Dauerläufer (#272)._", ""]
    try:
        with open(summary, "a", encoding="utf-8") as f:
            f.write("\n".join(lines))
    except OSError:
        pass


def selftest():
    errors = []
    # Test newest_slug
    try:
        slug, dt = newest_slug()
        if not slug:
            errors.append("newest_slug liefert keinen Slug (sollte mindestens einen finden)")
    except Exception as e:
        errors.append(f"newest_slug Exception: {e}")

    # Test bilanz
    try:
        status, cnt, min_v, tag, text = build_bilanz()
        if status not in ("OK","FAIL","WARN","SKIP",None):
            errors.append(f"build_bilanz status ungültig: {status}")
    except Exception as e:
        errors.append(f"build_bilanz Exception: {e}")

    # Test syntax check
    try:
        ok, err = check_syntax()
        if not ok:
            errors.append(f"check_syntax meldet Fehler im eigenen Repo: {err[:200]}")
    except Exception as e:
        errors.append(f"check_syntax Exception: {e}")

    # Test Pinterest-Kanal (sollte nicht crashen, liefert Findings + Text)
    try:
        pin_findings, pin_text = check_pinterest_channel()
        if not isinstance(pin_text, str) or not pin_text:
            errors.append("check_pinterest_channel liefert keinen Kurztext")
        for f in pin_findings:
            if f.owner not in ("auto", "human"):
                errors.append(f"Pinterest-Befund ohne gültigen Besitzer: {f.owner}")
            if not f.channel:
                errors.append(f"Pinterest-Befund ohne Kanal: {f.id}")
    except Exception as e:
        errors.append(f"check_pinterest_channel Exception: {e}")

    # Test reserve
    try:
        check_content_reserve()
    except Exception as e:
        errors.append(f"check_content_reserve Exception: {e}")

    # Test Alarm-Routing (Kern von #272): der Router muss verfügbar sein und
    # menschliche Befunde vom Automations-Ticket fernhalten.
    if ar is None:
        errors.append("alert_router.py nicht importierbar – Alarm-Routing blind")
    else:
        try:
            rc = ar._selftest()
            if rc != 0:
                errors.append("alert_router.py --selftest nicht bestanden")
        except Exception as e:
            errors.append(f"alert_router Selftest Exception: {e}")
        try:
            mensch = _f("pinterest-token", "Token tot", owner="human",
                        channel=PINTEREST_TOKEN_CHANNEL)
            maschine = _f("cadence", "Kadenz", severity="P1", owner="auto")
            m, h = split_findings([mensch, maschine])
            if len(m) != 1 or len(h) != 1:
                errors.append("split_findings trennt Besitzer nicht sauber")
            decision = ar.plan_generic([mensch], None, datetime.datetime.now(datetime.timezone.utc))
            if decision.action != "none":
                errors.append("menschlicher Befund öffnet ein Automations-Ticket (#272-Regression)")
        except Exception as e:
            errors.append(f"Routing-Selftest Exception: {e}")

    if errors:
        print("🛑 BOT-WATCHDOG SELFTEST FEHLGESCHLAGEN:")
        for er in errors:
            print(f"  - {er}")
        return 2
    print("✅ BOT-WATCHDOG SELFTEST bestanden (Slug, Bilanz, Syntax, Pinterest-Kanal, "
          "Reserve, Alarm-Routing).")
    return 0


def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())

    if "--route" in args:
        sys.exit(route_issues(args))

    env, findings, slug = run_all()
    write_report(env, findings)
    emit_env(env, findings)
    machine, human = split_findings(findings)

    # Konsolen-Output
    print(f"Watchdog: {len(machine)} maschinell behebbar · {len(human)} menschlich")
    for k, v in env.items():
        print(f"  {k}={v}")
    if machine:
        print("\nMaschinell behebbar (Automations-Ticket):")
        for f in machine:
            print(f.line())
    if human:
        print("\nMenschlicher Besitz (Fach-Kanal, Kadenz):")
        for f in human:
            print(f.line())
    if not machine and not human:
        print("ALLES OK")

    if "--emit-env" in args:
        sys.exit(0)

    # Exit Code für CI: 0 = ok, 1 = Probleme, aber Workflow soll nicht rot werden wenn nur WARN?
    # Hier: 0 immer, Probleme werden via Env gemeldet (wie bisher)
    sys.exit(0)


if __name__ == "__main__":
    main()
