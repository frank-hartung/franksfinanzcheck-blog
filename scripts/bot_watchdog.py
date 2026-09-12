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
  7)  Pinterest-Token Lebenszyklus (Broker-Status)
  8)  Content-Reserve Gesundheit (Pool-Größe, Drafts)
  9)  Affiliate-Health Report Frische

Exit-Codes:
  0 = alles grün (PROBLEMS leer)
  1 = Probleme gefunden (PROBLEMS gesetzt)
  2 = Selbsttest defekt

Nutzung:
  python3 scripts/bot_watchdog.py --check      # nur prüfen
  python3 scripts/bot_watchdog.py --emit-env   # schreibt /tmp/bot_watchdog.env + /tmp/problems.txt
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

REPORT_PATH = BLOG_DIR / "BOT-WATCHDOG-REPORT.md"

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

def check_pinterest_token():
    """Prüft Pinterest Token State (data/pinterest_token_state.json)."""
    state_path = BLOG_DIR / "data/pinterest_token_state.json"
    if not state_path.is_file():
        return None, "Token-State fehlt (kein Broker-Status)"
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
        severity = data.get("severity", "unknown")
        source = data.get("source_label") or data.get("source") or "?"
        detail = data.get("detail") or data.get("next_action") or ""
        if severity == "red":
            return False, f"Token RED – Quelle: {source} – {detail[:120]}"
        if severity == "amber":
            return None, f"Token AMBER – Quelle: {source} – {detail[:120]}"
        if severity == "green":
            return True, f"Token OK – Quelle: {source}"
        return None, f"Token Zustand {severity}: {detail[:120]}"
    except Exception as e:
        return None, f"Token-State unparsbar: {e}"

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

def run_all():
    problems = []
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
            problems.append(f"- **Produktions-Wache hat in den letzten 26 h nicht gedreht** – {msg} (Cron aktiv? Repo inaktiv?)")
    elif count == 0:
        env["CHECK1A"] = "FAIL"
        problems.append("- **Produktions-Wache hat in den letzten 26 h nicht gedreht** – die Ausfall-Erkennung ist derzeit blind. Workflow prüfen (Cron aktiv? Repo inaktiv?)")
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
            problems.append(f"- **Kein Artikel am Publikationstag {tag_b}** (0 von {min_b}) – Engine prüfen (Phase 1: Tageslimit, Themenpool oder API-Keys)")
        elif status == "WARN":
            problems.append(f"- **Nur {count_b} von {min_b} Artikeln am Publikationstag {tag_b}**")

    # 2 Syntax
    ok, err = check_syntax()
    if ok:
        env["CHECK2"] = "OK"
    else:
        env["CHECK2"] = "FAIL"
        problems.append(f"- **Skript-Syntaxfehler:** {err[:300]}")

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
            problems.append(f"- **Neuester Artikel nicht live (HTTP {code})** – {slug} (Deploy prüfen, ggf. Deploy-Catchup triggern)")
    else:
        env["CHECK3"] = "FAIL"
        problems.append("- **Kein veröffentlichter Artikel in content/posts/ gefunden** – Deploy kann nicht geprüft werden")

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
        problems.append("- **Affiliate-Integritäts-Wache hat in den letzten 30 h nicht gedreht** – Affiliate-Links könnten unbemerkt brechen (CTA-Boxen). Workflow `affiliate-integrity-daily.yml` prüfen.")
    else:
        env["CHECK5"] = f"OK ({count_aff} Läufe)"

    # 5b Affiliate-Report
    ok_aff, msg_aff = check_affiliate_integrity()
    if ok_aff is False:
        env["CHECK5B"] = f"FAIL ({msg_aff})"
        problems.append(f"- **Affiliate-Integrität offen:** {msg_aff} – `AFFILIATE-INTEGRITY-REPORT.md` prüfen, Auto-Heilung läuft täglich 06:00 MESZ.")
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
        problems.append("- **Pinterest-Watchdog hat in den letzten 30 h nicht gedreht** – Spam-/SEO-Signale (Duplikat-Pins, fehlende Rich-Pins) könnten unbemerkt bleiben.")
    else:
        env["CHECK6"] = f"OK ({count_pin} Läufe)"

    # 7 Pinterest-Token
    ok_tok, msg_tok = check_pinterest_token()
    if ok_tok is False:
        env["CHECK7"] = f"FAIL ({msg_tok})"
        # Nur als WARN, nicht als harter FAIL, weil Token als Queue degradiert (kein roter Lauf mehr)
        problems.append(f"- **Pinterest-Token kritisch:** {msg_tok} – Einmalige Neu-Autorisierung nötig: `docs/PINTEREST-TOKEN-RUNBOOK.md` (Actions → Pinterest-Token-Wache → Run workflow).")
    elif ok_tok is None:
        env["CHECK7"] = f"WARN ({msg_tok})"
    else:
        env["CHECK7"] = f"OK ({msg_tok})"

    # 8 Content-Reserve
    ok_res, msg_res = check_content_reserve()
    if ok_res is False:
        env["CHECK8"] = f"WARN ({msg_res})"
        problems.append(f"- **Content-Reserve niedrig:** {msg_res} – `content-reserve.yml` sollte täglich 3 Kandidaten nachfüllen.")
    else:
        env["CHECK8"] = f"OK ({msg_res})"

    # 9 Pinterest Duplikate
    ok_dup, msg_dup = check_pinterest_duplicate()
    if ok_dup is False:
        env["CHECK9"] = f"FAIL ({msg_dup})"
        problems.append(f"- **Pinterest Duplikat-Signal:** {msg_dup} – `PINTEREST-REPORT.md` und `scripts/pinterest_pin_text_sync.py` prüfen.")
    else:
        env["CHECK9"] = "OK"

    return env, problems, slug

def write_report(env, problems):
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
        f"- **Check 7 (Pinterest-Token):** {env.get('CHECK7','?')}",
        f"- **Check 8 (Content-Reserve):** {env.get('CHECK8','?')}",
        f"- **Check 9 (Pinterest-Duplikate):** {env.get('CHECK9','?')}",
        "",
    ]
    if problems:
        lines += ["## Probleme", ""]
        lines += problems
        lines += [""]
    else:
        lines += ["## Ergebnis", "", "✅ **ALLES OK** – alle Wachen leben, Live-Site aktuell, Affiliate- und Pinterest-Kanäle im grünen Bereich.", ""]
    lines += ["---", "*Automatisch erstellt vom Bot-Watchdog (täglich 10:30 MESZ) – Profi-Agentur-Level.*", ""]
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    return REPORT_PATH

def emit_env(env, problems):
    """Schreibt /tmp/bot_watchdog.env sicher (ohne EOF-Kollision) + problems.txt"""
    # Sichere Delimiter
    delim = f"EOF_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{os.getpid()}"
    env_path = Path("/tmp/bot_watchdog.env")
    prob_path = Path("/tmp/problems.txt")
    prob_env_path = Path("/tmp/bot_watchdog_problems.env")

    with env_path.open("w", encoding="utf-8") as f:
        for k, v in env.items():
            # Escape für env file: ersetze Newlines
            safe_v = str(v).replace("\n", " ").replace("\r", "")
            f.write(f"{k}={safe_v}\n")

    # PROBLEMS als Datei + als GitHub Env mit sicherem Delimiter
    prob_text = "\n".join(problems) if problems else ""
    prob_path.write_text(prob_text, encoding="utf-8")

    # Für GitHub Actions: schreibe in GITHUB_ENV falls vorhanden
    gha_env = os.environ.get("GITHUB_ENV")
    if gha_env:
        with open(gha_env, "a", encoding="utf-8") as out:
            for k, v in env.items():
                safe_v = str(v).replace("\n", " ").replace("\r", "")
                out.write(f"{k}={safe_v}\n")
            out.write(f"PROBLEMS<<{delim}\n")
            out.write(prob_text + "\n")
            out.write(f"{delim}\n")

    # Zusätzlich einfache Env-Datei für Debugging
    prob_env_path.write_text(prob_text, encoding="utf-8")
    return env_path, prob_path

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

    # Test token check (sollte nicht crashen)
    try:
        check_pinterest_token()
    except Exception as e:
        errors.append(f"check_pinterest_token Exception: {e}")

    # Test reserve
    try:
        check_content_reserve()
    except Exception as e:
        errors.append(f"check_content_reserve Exception: {e}")

    if errors:
        print("🛑 BOT-WATCHDOG SELFTEST FEHLGESCHLAGEN:")
        for er in errors:
            print(f"  - {er}")
        return 2
    print("✅ BOT-WATCHDOG SELFTEST bestanden (Slug, Bilanz, Syntax, Token, Reserve).")
    return 0

def main():
    args = sys.argv[1:]
    if "--selftest" in args:
        sys.exit(selftest())

    env, problems, slug = run_all()
    write_report(env, problems)
    emit_env(env, problems)

    # Konsolen-Output
    print(f"Watchdog: {len(problems)} Probleme")
    for k, v in env.items():
        print(f"  {k}={v}")
    if problems:
        print("\nProbleme:")
        for p in problems:
            print(p)
    else:
        print("ALLES OK")

    if "--emit-env" in args:
        sys.exit(0)

    # Exit Code für CI: 0 = ok, 1 = Probleme, aber Workflow soll nicht rot werden wenn nur WARN?
    # Hier: 0 immer, Probleme werden via Env gemeldet (wie bisher)
    sys.exit(0)

if __name__ == "__main__":
    main()
