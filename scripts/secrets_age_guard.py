#!/usr/bin/env python3
"""
SECRETS-AGE-GUARD – Secrets-/Token-Alters-Wache (Agentur-Betriebssicherheit)

Ein totes Secret ist der klassische lautlose Kanaltod: Pinterest-Tokens laufen
nach 30 Tagen ab, Mastodon-Access-Tokens ebenfalls, KI-Keys werden rotiert.
Wird der Fehler nicht gemeldet, fehlen Pins/Toots/Artikel einfach – ohne Alarm.

So arbeitet der Wächter (v2, Härtung 07.09.2026 aus Governance-Report #206):

  1. **Vorhandensein** – welche Secrets stehen im CI-Env (oder als
     verschlüsselte Token-Datei)?
  2. **Nachweis** – zwei Qualitäten, klar getrennt:
       · `proven`     → die API hat im Live-Check mit 200 geantwortet
                        (`--verify`, HTTP-Head gegen den echten Kanal)
       · `declared`   → ein Workflow hat `--record-success` aufgerufen
                        (mit Vermerk WELCHER Workflow das war)
     Ein Lauf, der ein Secret nur *vorhanden* findet und trotzdem Erfolg
    vermerkt, wäscht sich die eigene Gesundheit – das war ein Befund in #206
     (`OK (6d)` für KI-Keys, die der Governance-Lauf nie benutzt).
  3. **Alters-Ampel** – kein Erfolg innerhalb `days` = gelb/rot.

NEU in v2 (Grund für die Dauer-Falschmeldung in #206):
  * `--verify`  : live gegen die Kanal-API prüfen und den Erfolg NUR bei HTTP 200
                  vermerken. Damit kann „UNBEKANNT" nicht mehr dauerhaft stehen,
                  weil ein manueller Workflow (Pinterest-AI lief seit 20.08.
                  nur noch per workflow_dispatch) zufällig den Nachweis liefert.
  * `info`-Ebene: „Kanal ist gar nicht eingerichtet" ist eine Konfigurations-
                  info, KEIN Betriebsbefund. Vorher erzeugte genau das jede
                  Woche einen AMBER-Lauf und ein Governance-Issue.
  * State-Datei `data/secrets_state.json` wird atomar und mit Dateisperre
                  geschrieben (mehrere Workflows schreiben parallel!) und überlebt
                  einen kaputten/partialen Stand (Toleranz statt Traceback).

AUSGABE:
  - `SECRETS-REPORT.md`            – Übersicht + Ampel (Report für Scorecard/Gate)
  - `data/secrets_state.json`      – Nachweis-Historie (proven/declared)
  - `--issue`                      – GitHub-Issue-Body (bei rotem/gelbem Befund)
  - `--verify`                     – Live-Probe gegen die Kanal-APIs (nur Hash-/
                                     Token-Länge, NIE Secret-Material im Log)
  - `--record-success <VAR> [--proof-by <name>]`
  - `--quiet`                      – nur Quittung, Report-Datei unangetastet
  - `--list`                       – registrierte Secrets (für Workflow-Checks)
  - `--selftest`                   – eingefrorene Fälle, ohne Netzwerk

Exit-Codes: 0 = grün (oder nur Info), 1 = Handlungsbedarf, 2 = Selftest/Fehler.

Nutzung:
  python3 scripts/secrets_age_guard.py                     # prüfen (+Report)
  python3 scripts/secrets_age_guard.py --verify            # live prüfen + vermerken
  python3 scripts/secrets_age_guard.py --record-success PINTEREST_ACCESS_TOKEN \
      --proof-by pinterest-watchdog
  python3 scripts/secrets_age_guard.py --selftest
"""
import datetime
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

REPORT = os.path.join(BLOG_DIR, "SECRETS-REPORT.md")
STATE = os.path.join(BLOG_DIR, "data", "secrets_state.json")
LOCK_FILE = STATE + ".lock"
PIN_FILE = os.path.join(BLOG_DIR, "data", "pinterest_tokens.enc")

TODAY = datetime.date.today()
NOW = datetime.datetime.now(datetime.timezone.utc)

# HTTP-Budgets für die Live-Probe (CI: lieber kurz und oft als lang und still).
PROBE_TIMEOUT = 20
PROBE_RETRIES = 2
PROBE_BACKOFF = 3          # Sekunden, linear wachsend

# Wichtige Secrets und ihre „frische Erwartung" (Tage bis zur Erinnerung).
#
# `optional`  : alternativer Weg / Kann-Kanal – fehlt er, ist das eine
#               Konfigurations-Info, kein Betriebsbefund (vorher: Dauer-AMBER).
# `alt_of`    : Secret ist nur ein Ersatz für ein anderes.
# `probe`     : Live-Check-Funktion (Schlüssel in PROBES). `None` = nicht prüfbar.
# `proof_by`  : Workflows, die den Erfolg berechtigt vermerken dürfen
#               (dient `scripts/governance_contract.py` als Leitplanke).
CONFIG_ENV_VARS = {
    "GROQ_API_KEY": {
        "days": 60, "label": "Groq KI-Key", "probe": "groq",
        "proof_by": ("content-engine-v2", "redaktions-standard-neu", "redaktions-standard-bestand",
                     "willkommenstext-refresh", "seo-weekly", "update-quarterly"),
    },
    "GEMINI_API_KEY": {
        "days": 60, "label": "Gemini KI-Key", "probe": "gemini",
        "proof_by": ("content-engine-v2", "redaktions-standard-neu", "redaktions-standard-bestand",
                     "willkommenstext-refresh", "seo-weekly", "update-quarterly"),
    },
    "PINTEREST_ACCESS_TOKEN": {
        "days": 15, "label": "Pinterest Access-Token", "probe": "pinterest",
        "proof_by": ("pinterest-ai", "pinterest-watchdog", "premium-governance",
                     "repin-weekly", "pinterest-token"),
    },
    "MASTODON_ACCESS_TOKEN": {
        "days": 45, "label": "Mastodon Access-Token", "probe": "mastodon",
        "proof_by": ("social-ai", "mastodon-seo", "mastodon-profile-sync", "mastodon-manual-post"),
    },
    "PINTEREST_TOKEN_KEY": {
        "days": 60, "label": "Pinterest Verschlüsselungs-Key",
        "optional": True, "alt_of": "PINTEREST_ACCESS_TOKEN", "probe": None,
        "proof_by": ("pinterest-ai", "pinterest-token"),
    },
    # 07.09.2026 (#206): Der Pinterest-Kanal starb planmäßig alle 30 Tage, weil
    # er an einem von Hand eingefügten Access-Token hing. Mit Refresh-Token +
    # App-Zugangsdaten trägt sich der Kanal selbst (continuous refresh). Das
    # Secret ist optional – aber sein FEHLEN ist der eigentliche Dauerbefund,
    # deshalb steht es hier sichtbar in der Registrierung.
    "PINTEREST_REFRESH_TOKEN": {
        "days": 365, "label": "Pinterest Refresh-Token (Auto-Erneuerung)",
        "optional": True, "probe": None,
        "proof_by": ("pinterest-token",),
    },
    # 07.09.2026 (#206): Die Klick-Datenbank der Monetarisierungs-Schleife war
    # dauerhaft „0 Klicks“, ohne dass jemand sagte, WORAN das liegt (Export
    # fehlt? Token fehlt? API tot?). Mit registriert => die Wache unterscheidet
    # „Kanal tot" von „Kanal nie eingerichtet“.
    "UMAMI_API_TOKEN": {
        "days": 45, "label": "Umami Analytics-API-Token", "probe": "umami",
        "optional": True,
        "proof_by": ("premium-governance", "revenue-import"),
    },
    # 19.09.2026 (Auftrag: „vollständige Umsatzmessung“): die letzte Stufe des
    # Trichters – Klick → Antrag → Provision – braucht den Awin-Zugang. Als
    # registriertes Secret unterscheidet die Wache „nie eingerichtet“ (Info +
    # Funnel-Lücke) von „Token tot“ (rot) und altern lässt (STALE).
    "AWIN_API_TOKEN": {
        "days": 90, "label": "Awin Publisher-API-Token", "probe": "awin",
        "optional": True,
        "proof_by": ("premium-governance", "revenue-import"),
    },
}

SECRETS = CONFIG_ENV_VARS

# Levels: red > amber > info. „info" ist bewusst KEIN Handlungsbedarf.
LEVELS = ("red", "amber", "info")

# Befunde, die NIEMALS ein Governance-Issue auslösen sollen (nur Hinweis).
INFO_ONLY_CODES = {"not_configured", "not_used", "untracked_optional", "probe_skipped",
                   "channel_parked", "operating_boundary"}

# Lebenszyklus-Befunde des Pinterest-Zugangs (Quelle: scripts/pinterest_token.py).
# Sie beantworten die Frage, die #206 wochenlang offen ließ: Läuft der Kanal nur
# gerade zufällig – oder trägt er sich selbst?
PIN_RUNBOOK = "docs/PINTEREST-TOKEN-RUNBOOK.md"


# ------------------------------------------------------------------ State (robust)

def _today() -> datetime.date:
    return datetime.date.today()


def _parse_date(raw):
    """Tolerantes Datums-Parsing: kaputte Einträge => None, kein Traceback."""
    if not raw or not isinstance(raw, str):
        return None
    m = re.match(r"(\d{4})-(\d{2})-(\d{2})", raw.strip())
    if not m:
        return None
    try:
        return datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return None


def _read_state_file():
    """Liest den State; bei Schaden: leerer State + Warnhinweis (nie Crash)."""
    if not os.path.exists(STATE):
        return {"version": 2, "entries": {}}, None
    try:
        with open(STATE, encoding="utf-8") as f:
            raw = f.read()
    except OSError as exc:  # Leserecht, Platz, …
        return {"version": 2, "entries": {}}, f"State nicht lesbar: {exc.__class__.__name__}"
    if not raw.strip():
        return {"version": 2, "entries": {}}, "State-Datei ist leer (Schreibvorgang abgebrochen?)"
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        # Härtung: ein halber Write (paralleler Workflow) darf die Wache nicht
        # abschießen – der Report-Step würde sonst rot, ohne dass ein Secret
        # das Problem ist. Kaputten Stand sichern, neu anfangen, transparent melden.
        try:
            backup = f"{STATE}.corrupt-{int(time.time())}"
            with open(backup, "w", encoding="utf-8") as f:
                f.write(raw)
            return ({"version": 2, "entries": {}},
                    f"State war beschädigt ({exc.msg}) – gesichert nach "
                    f"{os.path.relpath(backup, BLOG_DIR)}, Neu begonnen")
        except OSError:
            return {"version": 2, "entries": {}}, "State war beschädigt – Neu begonnen"
    if not isinstance(data, dict) or not isinstance(data.get("entries"), dict):
        return {"version": 2, "entries": {}}, "State-Format unbekannt – Neu begonnen"
    clean = {"version": data.get("version", 2), "entries": {}}
    for var, ent in data["entries"].items():
        if isinstance(ent, dict):
            clean["entries"][var] = {k: v for k, v in ent.items() if isinstance(v, (str, int, float))}
    return clean, None


def _lock():
    """Best-effort-Dateisperre (POSIX). Ohne fcntl (z. B. Windows) läuft es weiter."""
    try:
        import fcntl
    except ImportError:
        return None
    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        fh = open(LOCK_FILE, "a+", encoding="utf-8")
    except OSError:
        return None
    for _ in range(40):                     # max ~10 s auf den Nachbarn warten
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fh
        except OSError:
            time.sleep(0.25)
    return fh                                # ohne Sperre weiter (besser als Blocker)


def _unlock(handle):
    if handle is None:
        return
    try:
        import fcntl
        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    except Exception:  # noqa: BLE001
        pass
    try:
        handle.close()
    except OSError:
        pass


def _write_state_atomic(state):
    """Atomar schreiben (tmp + os.replace) – kein halber JSON-Stand bei Parallel-Läufen."""
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    tmp = f"{STATE}.tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, STATE)


def _mutate_state(mutator):
    """Read-Modify-Write unter Sperre: parallele Workflows überschreiben sich nicht."""
    handle = _lock()
    try:
        state, _ = _read_state_file()
        state = mutator(state) or state
        _write_state_atomic(state)
        return state
    finally:
        _unlock(handle)


def _load_state():
    state, _ = _read_state_file()
    return state


def _save_state(state):
    _write_state_atomic(state)


# ------------------------------------------------------------------ Recordings

def _record_success(var, proof_by="workflow"):
    var = str(var).strip().upper()
    if var not in CONFIG_ENV_VARS:
        # Ausgabe nennt nur den NAMEN der Umgebungsvariablen und die
        # erlaubten Registry-Schlüssel – nie einen Secret-Wert.
        print(f"❌ Unbekanntes Secret '{var}' (erlaubt: {', '.join(sorted(CONFIG_ENV_VARS))})")
        return 1
    reg = CONFIG_ENV_VARS[var]
    allowed = reg.get("proof_by") or ()
    quality = "declared"
    if allowed and proof_by and proof_by not in allowed:
        # Der Nachweis kommt aus einem Lauf, der das Secret gar nicht benutzt:
        # zählbar, aber als `declared_foreign` sichtbar – die Wache meldet das
        # als Info und die Scorecard verlässt sich nicht darauf.
        quality = "declared_foreign"
        # Nur Variablen-Name und Workflow-Namen (Metadaten) – kein Wert.
        print(f"⚠️  {var}: Erfolg wird von '{proof_by}' vermerkt, vorgesehen für "
              f"{', '.join(allowed)} – gilt nur als deklariert, nicht als bewiesen.")

    def mutate(state):
        ent = state.setdefault("entries", {}).setdefault(var, {})
        ent["last_success"] = _today().isoformat()
        ent["last_attempt"] = _today().isoformat()
        ent["proven_by"] = proof_by
        ent["quality"] = quality
        return state

    _mutate_state(mutate)
    label = str(CONFIG_ENV_VARS[var].get("label") or var)
    today_iso = _today().isoformat()
    # Label, Variablen-Name, Datum, Nachweis-Qualität – Metadaten der Registry, kein Secret-Wert.
    print(f"✅ {label} ({var}): Erfolg am {today_iso} vermerkt ({quality}, via {proof_by}).")
    try:
        from audit_log import log_event
        log_event(module="secrets_age_guard", action="record-success",
                  input={"var": var, "proof_by": proof_by},
                  output={"quality": quality}, status="ok")
    except Exception:  # noqa: BLE001  – Audit darf den Nachweis nicht blockieren
        pass
    return 0


# ------------------------------------------------------------------ Live-Probes

def _sanitize(text, secret):
    """Secret-Material darf nie ins Log/Report (auch nicht in Fehlermeldungen)."""
    out = str(text or "")
    if secret and len(secret) >= 4:
        out = out.replace(secret, "***")
    return re.sub(r"\s+", " ", out)[:180]


def _http_status(url, headers=None, timeout=PROBE_TIMEOUT):
    """→ (status_code | None, error_text | None). Folgt keinen Redirects ins Leere."""
    req = urllib.request.Request(url, headers={"User-Agent": "franksfin-gov/2.0", **(headers or {})})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            resp.read(512)
            return getattr(resp, "status", 200), None
    except urllib.error.HTTPError as exc:
        return exc.code, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"{exc.__class__.__name__}"


_PIN_HEALTH_VERIFIED = {}


def _pinterest_health(verify=True):
    """Lagebild des Pinterest-Zugangs vom zentralen Broker (nie Token-Material).

    #206-Kern: Vorher prüfte diese Wache das Env-Secret, während der Bot mit
    einer ganz anderen Quelle arbeitete (Auto-Refresh-Speicher). Ein grüner
    Report konnte einen toten Kanal bedeuten – und ein roter einen gesunden.
    Jetzt fragt die Wache exakt den Zugang ab, den der Betrieb benutzt.
    """
    if not verify and _PIN_HEALTH_VERIFIED:
        # Im selben Lauf schon live geprüft: Report und Befund zeigen denselben
        # Stand (sonst steht im Cockpit „unverified", während die Probe 200 sah).
        return _PIN_HEALTH_VERIFIED
    try:
        import pinterest_token
        h = pinterest_token.health(verify=verify, allow_refresh=verify)
        if verify:
            _PIN_HEALTH_VERIFIED.clear()
            _PIN_HEALTH_VERIFIED.update(h)
        return h
    except Exception as exc:  # noqa: BLE001 – die Wache stirbt nie am Broker
        return {"state": "unknown", "severity": "amber", "source": None,
                "detail": f"Token-Broker nicht verfügbar ({exc.__class__.__name__})",
                "renewable": False, "auto_renew_armed": False, "runbook": PIN_RUNBOOK,
                "next_action": "scripts/pinterest_token.py prüfen (Selbsttest)"}


def _pinterest_token():
    """Nur für Vorhandensein/Länge – ohne Netz, ohne Erneuerung."""
    tok = os.environ.get("PINTEREST_ACCESS_TOKEN", "").strip()
    if tok:
        return tok
    try:
        import pinterest_token
        h = pinterest_token.resolve(verify=False, allow_refresh=False)
        return (h.get("token") or "").strip()
    except Exception:  # noqa: BLE001  – Krypto-Bibliotheken können fehlen
        return ""


# Jede Probe gibt ("ok" | "dead" | "error", detail) zurück.
def _probe_groq(secret):
    code, err = _http_status("https://api.groq.com/openai/v1/models",
                             {"Authorization": f"Bearer {secret}"})
    if code == 200:
        return "ok", "Groq /models 200"
    if code in (401, 403):
        return "dead", f"Groq Key abgelehnt ({code})"
    return "error", _sanitize(err or f"Groq HTTP {code}", secret)


def _probe_gemini(secret):
    code, err = _http_status(
        "https://generativelanguage.googleapis.com/v1beta/models?key=" + urllib.parse.quote(secret))
    if code == 200:
        return "ok", "Gemini /models 200"
    if code in (400, 401, 403):
        return "dead", f"Gemini Key abgelehnt ({code})"
    return "error", _sanitize(err or f"Gemini HTTP {code}", secret)


def _probe_pinterest(_secret):
    """Delegiert an den Token-Broker: Failover über alle Quellen inklusive.

    Zwei alte Fehler stecken in der ersetzten Zeile:
      1. `/v5/users/me` gibt es in der Pinterest-API v5 gar nicht (v3-Altlast) –
         die Wache befragte einen Pfad, den niemand benutzt.
      2. Geprüft wurde nur das Env-Secret. Lebt der Kanal über den
         Auto-Refresh-Speicher weiter, meldete die Wache trotzdem ROT.
    """
    h = _pinterest_health(verify=True)
    state = h.get("state")
    src = h.get("source_label") or "unbekannte Quelle"
    if state == "live":
        return "ok", f"Pinterest /v5/user_account 200 (Quelle: {src})"
    if state in ("dead", "absent"):
        return "dead", h.get("next_action") or "Pinterest lehnt alle Token ab"
    return "error", h.get("detail") or "Pinterest-Live-Probe nicht möglich"


def _probe_mastodon(secret):
    inst = (os.environ.get("MASTODON_INSTANCE") or "https://mastodon.social").strip().rstrip("/")
    code, err = _http_status(f"{inst}/api/v1/accounts/verify_credentials",
                             {"Authorization": f"Bearer {secret}"})
    if code == 200:
        return "ok", "Mastodon verify_credentials 200"
    if code in (401, 403):
        return "dead", f"Mastodon-Token abgelehnt ({code})"
    return "error", _sanitize(err or f"Mastodon HTTP {code}", secret)


def _probe_umami(secret):
    base = (os.environ.get("UMAMI_API_BASE") or "https://api.umami.is/v1").strip().rstrip("/")
    code, err = _http_status(f"{base}/websites", {"x-umami-api-key": secret})
    if code == 200:
        return "ok", "Umami /websites 200"
    if code in (401, 403):
        return "dead", f"Umami-API-Token abgelehnt ({code})"
    return "error", _sanitize(err or f"Umami HTTP {code}", secret)


def _probe_awin(secret):
    """Awin Publisher-API: GET auf das eigene Publisher-Konto.

    Ohne `AWIN_PUBLISHER_ID` ist die Probe nicht ausführbar (skipped statt
    Fehlalarm) – die ID ist kein Geheimnis, aber Kontext, den die Wache braucht."""
    pid = (os.environ.get("AWIN_PUBLISHER_ID") or "").strip()
    if not pid.isdigit():
        return "skipped", "AWIN_PUBLISHER_ID fehlt – Probe braucht die Publisher-ID"
    base = (os.environ.get("AWIN_API_BASE") or "https://api.awin.com").strip().rstrip("/")
    code, err = _http_status(f"{base}/publishers/{pid}",
                             {"Authorization": f"Bearer {secret}"})
    if code == 200:
        return "ok", "Awin /publishers 200"
    if code in (401, 403):
        return "dead", f"Awin-API-Token abgelehnt ({code})"
    return "error", _sanitize(err or f"Awin HTTP {code}", secret)


def _probe_none(_secret):
    return "skipped", "kein Live-Check für dieses Secret definiert"


PROBES = {
    "groq": _probe_groq,
    "gemini": _probe_gemini,
    "pinterest": _probe_pinterest,
    "mastodon": _probe_mastodon,
    "umami": _probe_umami,
    "awin": _probe_awin,
    None: _probe_none,
}


def _umami_api_import_enabled(config_path=None):
    path = config_path or os.path.join(BLOG_DIR, "data", "monetization.yaml")
    try:
        with open(path, encoding="utf-8") as f:
            txt = f.read()
        if re.search(r"^umami_api_import_enabled:\s*false\s*$", txt, re.M):
            return False
    except OSError:
        pass
    return True


def _secret_value(var):
    """Wert des Secrets so wie die Automatisierung ihn sieht (inkl. Token-Datei)."""
    val = os.environ.get(var, "").strip()
    if val:
        return val
    if var == "PINTEREST_ACCESS_TOKEN":
        return _pinterest_token()
    return ""


def verify_secret(var, retries=PROBE_RETRIES, config_path=None):
    """Ein Live-Check pro Secret. → dict(ok, kind, detail, http_like)."""
    if var == "UMAMI_API_TOKEN" and not _umami_api_import_enabled(config_path):
        return {"ran": False, "kind": "disabled", "detail": "API-Import in data/monetization.yaml bewusst deaktiviert (Umami Free)"}
    reg = SECRETS.get(var) or {}
    probe = PROBES.get(reg.get("probe"))
    secret = _secret_value(var)
    if probe is None or probe is _probe_none:
        return {"ran": False, "kind": "skipped", "detail": "kein Live-Check definiert"}
    if not secret:
        return {"ran": False, "kind": "absent", "detail": "kein Secret im Env/Token-Datei"}
    detail = "unbekannt"
    for attempt in range(1, retries + 1):
        try:
            kind, detail = probe(secret)
        except Exception as exc:  # noqa: BLE001  – eine kaputte Probe nie fatal
            kind, detail = "error", _sanitize(exc.__class__.__name__, secret)
        if kind == "ok":
            break
        if kind == "dead":                 # Authentifizierung tot: nie retryn
            break
        if attempt < retries:
            time.sleep(PROBE_BACKOFF * attempt)
    return {"ran": True, "kind": kind, "detail": _sanitize(detail, secret), "value_len": len(secret)}


def run_verifications(vars_to_check):
    """Führt Proben aus und vermerkt Erfolge NUR bei 200 (quality=proven)."""
    results = {}
    for var in vars_to_check:
        res = verify_secret(var)
        results[var] = res
        if res.get("ran") and res.get("kind") == "ok":
            def mutate(state, var=var, detail=res.get("detail", "")):
                ent = state.setdefault("entries", {}).setdefault(var, {})
                ent["last_success"] = _today().isoformat()
                ent["last_attempt"] = _today().isoformat()
                ent["last_verified"] = _today().isoformat()
                ent["verify"] = "ok"
                ent["verify_detail"] = detail[:160]
                ent["proven_by"] = "live-probe"
                ent["quality"] = "proven"
                return state
            _mutate_state(mutate)
        elif res.get("ran") and res.get("kind") == "dead":
            def mutate(state, var=var, detail=res.get("detail", "")):
                ent = state.setdefault("entries", {}).setdefault(var, {})
                ent["last_attempt"] = _today().isoformat()
                ent["verify"] = "dead"
                ent["verify_detail"] = detail[:160]
                return state
            _mutate_state(mutate)
        elif res.get("ran"):
            def mutate(state, var=var, detail=res.get("detail", "")):
                ent = state.setdefault("entries", {}).setdefault(var, {})
                ent["last_attempt"] = _today().isoformat()
                ent["verify"] = "unreachable"
                ent["verify_detail"] = detail[:160]
                return state
            _mutate_state(mutate)
    try:
        from audit_log import log_event
        log_event(module="secrets_age_guard", action="verify",
                  input={"vars": sorted(vars_to_check)},
                  output={v: r.get("kind", "?") for v, r in results.items()},
                  status="ok" if all(r.get("kind") != "dead" for r in results.values()) else "error",
                  critical=any(r.get("kind") == "dead" for r in results.values()))
    except Exception:  # noqa: BLE001
        pass
    return results


# ------------------------------------------------------------------ Audit

def _present(var):
    """Secret im Env – oder bei Pinterest über einen der Erneuerungspfade.

    Der Pinterest-Zugang hat drei mögliche Quellen (Broker-Reihenfolge):
    verschlüsselter Auto-Refresh-Speicher, Env-Refresh-Token + App-Daten,
    klassisches Access-Secret. „Vorhanden" heißt: mindestens eine davon.
    """
    if os.environ.get(var, "").strip():
        return True
    if var != "PINTEREST_ACCESS_TOKEN":
        return False
    if os.path.exists(PIN_FILE):
        return True
    return bool(os.environ.get("PINTEREST_REFRESH_TOKEN", "").strip()
                and os.environ.get("PINTEREST_APP_ID", "").strip()
                and os.environ.get("PINTEREST_APP_SECRET", "").strip())


def _alt_active(meta):
    alt = meta.get("alt_of")
    return bool(alt and _present(alt))


def classify(var, meta, ent, today=None, verification=None, live_check_available=False, config_path=None):
    """Ein Secret → (status_text, nachweis_text, finding|None).

    `finding` = None (grün) oder dict(level, code, msg).
    """
    today = today or _today()
    if verification is None:
        verification = {}
    present = _present(var)
    if not present:
        if var == "UMAMI_API_TOKEN" and not _umami_api_import_enabled(config_path):
            return ("BEWUSST DEAKTIVIERT (Umami Free)", "–", {
                "level": "info", "code": "operating_boundary", "var": var,
                "msg": f"{meta['label']} (`{var}`) ist in data/monetization.yaml bewusst "
                       f"deaktiviert (Umami Free – Tracking im Browser aktiv, kein API-Import)"})
        if meta.get("optional"):
            if _alt_active(meta):
                return (f"NICHT GENUTZT (via {meta['alt_of']})", "–", None)
            return ("NICHT EINGERICHTET", "–", {
                "level": "info", "code": "not_configured", "var": var,
                "msg": f"{meta['label']} fehlt – optionaler Kanal, kein Betrieb, "
                       f"kein Befund (einrichten: GitHub-Secret `{var}`)"})
        return ("FEHLT", "–", {
            "level": "red", "code": "missing", "var": var,
            "msg": f"{meta['label']} (`{var}`) fehlt im Env – der Kanal kann nicht arbeiten"})

    v_kind = verification.get("kind")
    v_detail = verification.get("detail", "")
    # Nachweis-Kontinuität: ein in einem früheren Lauf abgelehnter Token bleibt
    # ROT, auch wenn ein einzelner Lauf ihn wegen Netzwerkproblemen nicht neu
    # prüfen konnte. Sonst würde ein transienter Ausfall den Alarm „weglächeln".
    if not verification.get("ran") and ent.get("verify") == "dead":
        last_try = _parse_date(ent.get("last_attempt"))
        last_ok = _parse_date(ent.get("last_success"))
        if not (last_ok and last_try and last_ok >= last_try):
            return ("TOT (letzter Live-Check)", f"verify=dead {ent.get('verify_detail') or ''}".strip(), {
                "level": "red", "code": "dead", "var": var,
                "msg": f"{meta['label']}: letzter Live-Check abgelehnt "
                       f"({ent.get('verify_detail') or '401/403'}) und seither nicht "
                       f"bestätigt – Token erneuern"})
    if verification.get("ran") and v_kind == "ok":
        return (f"VERIFIZIERT (live, {today.isoformat()})", "API 200", None)
    if verification.get("ran") and v_kind == "dead":
        return ("TOT (live-Probe)", "API-Lehnung", {
            "level": "red", "code": "dead", "var": var,
            "msg": f"{meta['label']}: Live-Check abgelehnt – {v_detail or 'Token abgelaufen'}"})
    if verification.get("ran") and v_kind == "skipped":
        # Die Probe existiert, konnte aber nicht laufen (z. B. Awin ohne
        # Publisher-ID). Kein Alarm, aber sichtbar im Report.
        return (f"PRÜFUNG ÜBERSPRUNGEN ({v_detail})", "–", {
            "level": "info", "code": "probe_skipped", "var": var,
            "msg": f"{meta['label']}: {v_detail or 'Probe übersprungen'}"})
    if verification.get("ran"):
        return (f"PRÜFUNG NICHT MÖGLICH ({v_detail})", "Netzwerk/API", {
            "level": "amber", "code": "unreachable", "var": var,
            "msg": f"{meta['label']}: Live-Check nicht möglich ({v_detail or 'unbekannt'}) – "
                   f"Health gilt NICHT als bestätigt"})

    # Optionale Stütz-Secrets ohne eigene API-Probe (z. B.
    # PINTEREST_TOKEN_KEY/PINTEREST_REFRESH_TOKEN) dürfen den wöchentlichen
    # Governance-Report nicht offen halten, nur weil sie zwar gesetzt sind,
    # aber naturgemäß keinen Live-200 liefern können. Ihre echte Wirkung wird
    # über den primären Kanal (`PINTEREST_ACCESS_TOKEN` via Token-Broker) und
    # dessen Lebenszyklusblock geprüft. Vorher wurde ein vorhandener
    # Verschlüsselungs-Key als `untracked` AMBER geführt – genau der
    # Dauerbefund aus Governance #439.
    if meta.get("optional") and meta.get("probe") is None:
        if _alt_active(meta):
            return (f"VORHANDEN (Reserve via {meta['alt_of']})",
                    "Struktur-Secret, primärer Kanal beweist Health", None)
        return ("VORHANDEN (nicht live prüfbar)", "Struktur-Secret", {
            "level": "info", "code": "untracked_optional", "var": var,
            "msg": f"{meta['label']} ist gesetzt, hat aber keine eigene Live-Probe; "
                   "die Betriebsfähigkeit wird über den primären Kanal geprüft"})

    last_success = _parse_date(ent.get("last_success"))
    quality = ent.get("quality") or ("proven" if ent.get("last_verified") else "declared")
    if last_success:
        age = (today - last_success).days
        note = f"{quality} ({ent.get('proven_by') or 'unbekannt'})"
        if age > meta["days"]:
            return (f"STALE {age}d", note, {
                "level": "red", "code": "stale", "var": var, "age": age, "days": meta["days"],
                "msg": f"{meta['label']} seit {age} Tagen ohne Erfolg (erwartet ≤ {meta['days']})"})
        if age > meta["days"] * 0.5:
            return (f"ALTERN {age}d", note, {
                "level": "amber", "code": "aging", "var": var, "age": age, "days": meta["days"],
                "msg": f"{meta['label']}: {age} Tage ohne Erfolg (Schwelle {meta['days']}d)"})
        if quality == "declared_foreign":
            return (f"OK ({age}d)", note, {
                "level": "info", "code": "foreign_proof", "var": var,
                "msg": f"{meta['label']}: Nachweis kommt aus `{ent.get('proven_by')}`, "
                       f"das Secret dort aber nicht nutzt – gilt nicht als Beweis"})
        return (f"OK ({age}d)", note, None)

    # Vorhanden, aber ohne jeden Nachweis.
    if live_check_available:
        return ("UNBEKANNT", "kein Nachweis", {
            "level": "amber", "code": "untracked", "var": var,
            "msg": f"{meta['label']}: kein Erfolgs-/Live-Nachweis – im Workflow "
                   f"`scripts/secrets_age_guard.py --verify` (oder --record-success "
                   f"{var} --proof-by <workflow>) einhängen"})
    # Die Wache selbst läuft hier ohne Live-Check (z. B. lokal): kein Alarm.
    return ("UNBEKANNT (lokal)", "–", {
        "level": "info", "code": "probe_skipped", "var": var,
        "msg": f"{meta['label']} vorhanden, aber ohne --verify nicht beweisbar – "
               f"die Live-Probe läuft im Premium-Governance-Workflow"})


# ------------------------------------------------- Empfänger der OAuth-Rückleitung
# NAMENSVERTRAG (Alert #80): Bezeichner in diesem Abschnitt heißen
# `rueckleitung_*` und nicht `oauth_*`. Hier liegen Dateipfade und Prüfbefunde
# zur statischen Landeseite – kein Zugangsmaterial. Der alte Name behauptete
# fälschlich einen sensiblen Rückgabewert und vergiftete dessen Ausgabe für die
# namensbasierte CodeQL-Analyse.
RUECKLEITUNG_SEITE = os.path.join(BLOG_DIR, "static", "pinterest-oauth.html")
RUECKLEITUNG_ZWILLING = os.path.join(BLOG_DIR, "static", "pinterest-oauth", "index.html")
# Was die Seite können muss, damit die Handlungsanweisung aus #246 funktioniert.
RUECKLEITUNG_MARKEN = (("URLSearchParams", "liest den code-Parameter nicht (der Code "
                 "landet nirgends – Kopieren unmöglich)"),
                ("opy", "kein Kopierweg (clipboard-Knopf oder select-all) – "
                 "manuelles Abtipieren eines 200-Zeichen-Codes ist der übliche Fehler"),
                ("noindex", "Seite ist indexierbar – Autorender-Links gehören "
                 "nicht in Suchmaschinen (meta robots noindex)"))


def rueckleitung_findings(pruef_pfad: str = "", zwilling_pfad: str = "") -> list:
    """Prüft den Empfänger der Pinterest-Rückleitung – die Empfehlung muss helfen.

    Liefert ausschließlich Befund-Dicts zu einer statischen HTML-Seite;
    Zugangsdaten sind weder Ein- noch Ausgabe. Bis Alert #80 hieß die Funktion
    `oauth_empfaenger_findings`: Der sensible Name machte die spätere Ausgabe
    der harmlosen Befunde für CodeQL formal zu einem Klartext-Leck.

    Der Fund `manual_token` (und jeder #246-Lauf) schickt den Betreiber auf
    /pinterest-oauth.html: dort liegt der `?code=…` aus der Pinterest-Umleitung,
    von dort wandert er in den Workflow-Input `auth_code`. Diese Seite ist der
    EINZIGE Weg zurück in den Auto-Betrieb. Fällt sie weg – Aufräumen im static/-
    Baum, ein Build-Filter, ein Umbau der Verzeichnisstruktur –, bleibt der
    Kanal tot, während die Wache parallel einen toten Link empfiehlt. Das ist
    die klassische Schein-Sicherheit: Anleitung vorhanden, Ausführung unmöglich.

    Bewusst syntaktisch geprüft (kein Build, kein Netz): der Fehler ist genau
    dann da, wenn gerade niemand hinsieht, und die Prüfung muss in jedem Lauf
    laufen können – auch offline im Selbsttest.
    """
    haupt = pruef_pfad or RUECKLEITUNG_SEITE
    zwil = zwilling_pfad or RUECKLEITUNG_ZWILLING
    out = []
    if not os.path.isfile(haupt):
        return [{"level": "red", "code": "oauth_page_missing",
                 "var": "PINTEREST_ACCESS_TOKEN",
                 "msg": "Empfänger-Seite der Pinterest-Rückleitung fehlt "
                        f"(`static/{os.path.basename(os.path.dirname(haupt))}/…` bzw. "
                        "pinterest-oauth.html) – die Neu-Autorisierung aus #246 "
                        "läuft ins Leere"}]
    try:
        with open(haupt, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        return [{"level": "red", "code": "oauth_page_missing",
                 "var": "PINTEREST_ACCESS_TOKEN",
                 "msg": f"Empfänger-Seite ist nicht lesbar ({exc.strerror})"}]
    for marke, grund in RUECKLEITUNG_MARKEN:
        if marke not in text:
            out.append({"level": "red", "code": "oauth_page_incomplete",
                        "var": "PINTEREST_ACCESS_TOKEN",
                        "msg": f"pinterest-oauth.html: {grund}"})
    if not os.path.isfile(zwil):
        out.append({"level": "amber", "code": "oauth_page_zwilling",
                    "var": "PINTEREST_ACCESS_TOKEN",
                    "msg": "Zwilling `static/pinterest-oauth/index.html` fehlt – "
                           "Pinterest leitet auf /pinterest-oauth/ (mit Slash) um, "
                           "ohne ihn gibt es 404 statt Code"})
    return out



def pinterest_lifecycle_findings(health, token_dead=False):
    """Vorwarnung statt Nachruf: Was passiert mit dem Zugang in den nächsten Tagen?

    Der teuerste Teil von #206 war nicht der tote Token, sondern dass sein Tod
    planbar war und trotzdem niemand vorher gewarnt hat. Diese Befunde melden
    das Risiko, BEVOR der Kanal steht.
    """
    out = []
    if not health or token_dead:
        return out          # ein toter Kanal hat schon seinen roten Befund
    if health.get("state") not in ("live", "unverified"):
        return out
    if not health.get("auto_renew_armed"):
        out.append({
            "level": "amber", "code": "manual_token", "var": "PINTEREST_ACCESS_TOKEN",
            "msg": ("Pinterest läuft im Handbetrieb: Der Access-Token stirbt "
                    f"planmäßig nach 30 Tagen und niemand erneuert ihn. "
                    f"Auto-Erneuerung scharfschalten (5 Min., einmalig): `{PIN_RUNBOOK}` "
                    "– danach trägt sich der Kanal selbst.")})
        return out
    left = health.get("refresh_days_left")
    age = health.get("refresh_age_days")
    if isinstance(left, int) and left <= 8:
        out.append({
            "level": "red", "code": "refresh_rotation", "var": "PINTEREST_ACCESS_TOKEN",
            "msg": (f"Der Refresh-Token rotiert in {left} Tagen zwangsweise "
                    f"(Alter {age} Tage) und wurde seither nicht erneuert – die "
                    "tägliche Token-Wache (`pinterest-token.yml`) läuft offenbar "
                    "nicht. Ohne Erneuerung steht der Kanal danach still.")})
    elif isinstance(left, int) and left <= 20:
        out.append({
            "level": "amber", "code": "refresh_rotation", "var": "PINTEREST_ACCESS_TOKEN",
            "msg": (f"Refresh-Token seit {age} Tagen nicht rotiert (noch {left} Tage "
                    "Reserve). Die tägliche Token-Wache sollte das automatisch tun – "
                    "Lauf prüfen: `gh run list --workflow=pinterest-token.yml`.")})
    return out


# ------------------------------------------------------------------ Kanalzustand

def pinterest_channel_parked(path=None):
    """Aktive Pinterest-Domain-Sperre oder ``None``.

    Die Domain-Sperre ist ein bewusst gesetzter Kill-Switch: Es dürfen keine
    Pins auf die gesperrte Domain gehen, bis der Betreiber die Freigabe
    bestätigt. Der Bot-Watchdog besitzt dafür den Kanal `pinterest-parked`.
    Ein abgelehnter Access-Token ist in diesem Zustand kein zweiter,
    unabhängiger Produktionsnotfall und darf das zentrale Governance-Issue
    nicht dauerhaft offenhalten. Die Datei wird absichtlich nicht nach Alter
    verworfen – aufheben darf nur der explizite `--domain-unblock`-Weg.
    """
    path = path or os.path.join(BLOG_DIR, "data", "pinterest_domain_block.json")
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(doc, dict):
        return None
    reason = str(doc.get("reason") or "Pinterest-Domain-Sperre aktiv").strip()
    return {"since": str(doc.get("since") or "unbekannt")[:32], "reason": reason[:220]}


def parked_pinterest_finding(parked):
    """Transparenter Hinweis statt Doppelalarm für den geparkten Kanal."""
    return {
        "level": "info", "code": "channel_parked", "var": "PINTEREST_ACCESS_TOKEN",
        "msg": ("Pinterest-Kanal ist seit " + parked["since"] +
                " bewusst geparkt (Domain-Sperre; Ticket-Kanal `pinterest-parked`). "
                "Token-Erneuerung wird erst nach bestätigter Domain-Freigabe erwartet."),
    }


# ------------------------------------------------------------------ Audit

def audit(verification=None, live_check_available=False, pin_health=None):
    verification = verification or {}
    state, state_warning = _read_state_file()
    entries = state.get("entries") or {}
    findings = []
    summary = []
    parked = pinterest_channel_parked()
    for var, meta in SECRETS.items():
        status, proof, finding = classify(var, meta, entries.get(var) or {},
                                          today=_today(),
                                          verification=verification.get(var),
                                          live_check_available=live_check_available)
        # A parked channel has a dedicated human escalation path. Keep its
        # state visible, but do not make a known consequence (an expired or
        # absent token) reopen the all-up governance report every week.
        if parked and var == "PINTEREST_ACCESS_TOKEN" and finding and \
                finding.get("code") in {"dead", "missing", "stale", "aging", "untracked"}:
            status, proof = "GEPAUSIERT (Domain-Sperre)", "Kanal geparkt"
            finding = parked_pinterest_finding(parked)
        summary.append((var, status, proof))
        if finding:
            findings.append(finding)
    if state_warning:
        findings.append({"level": "amber", "code": "state_corrupt", "var": "STATE",
                         "msg": f"State-Datei: {state_warning}"})
    token_dead = any(f.get("var") == "PINTEREST_ACCESS_TOKEN"
                     and f.get("code") in ("dead", "missing") for f in findings)
    if pin_health is None and _present("PINTEREST_ACCESS_TOKEN"):
        pin_health = _pinterest_health(verify=False)     # ohne Netz, nur Bestand
    findings += pinterest_lifecycle_findings(pin_health, token_dead=token_dead)
    findings += rueckleitung_findings()
    return findings, summary


def verdict_of(findings):
    levels = {f.get("level") for f in findings}
    if "red" in levels:
        return "RED"
    if "amber" in levels:
        return "AMBER"
    return "GREEN"


def actionable(findings):
    """Nur Befunde, die einen Menschen (oder Autopiloten) wirklich etwas angehen."""
    return [f for f in findings
            if f.get("level") in ("red", "amber") and f.get("code") not in INFO_ONLY_CODES]


# ------------------------------------------------------------------ Report

def render_pinterest_lifecycle(health):
    """Kurzer Lebenszyklus-Block: Woher kommt der Zugang, wie lange trägt er?"""
    if not health:
        return []
    icon = {"green": "🟢", "amber": "🟡", "red": "🔴"}.get(health.get("severity"), "⚪")
    armed = "scharf" if health.get("auto_renew_armed") else "**nicht scharf**"
    rows = [
        "", "## 🔁 Pinterest-Zugang (Lebenszyklus)", "",
        "| Merkmal | Wert |", "|---|---|",
        f"| Zustand | {icon} {health.get('state')} |",
        f"| Aktive Quelle | {health.get('source_label') or '–'} |",
        f"| Auto-Erneuerung | {armed} |",
    ]
    if health.get("access_age_days") is not None:
        rows.append(f"| Access-Token-Alter | {health['access_age_days']} Tage "
                    f"(Ablauf nach 30) |")
    if health.get("refresh_days_left") is not None:
        rows.append(f"| Refresh-Token-Reserve | {health['refresh_days_left']} Tage "
                    "bis zur Zwangs-Rotation |")
    if health.get("fingerprint"):
        rows.append(f"| Fingerabdruck | `{health['fingerprint']}` (kein Token-Material) |")
    rows.append(f"| Nächster Schritt | {health.get('next_action') or '–'} |")
    rows += ["", f"_Quelle: `scripts/pinterest_token.py` · Runbook: `{PIN_RUNBOOK}` · "
                 "täglich erneuert von `pinterest-token.yml`._"]
    return rows


def render_report(findings, summary, verification=None, pin_health=None):
    verdict = verdict_of(findings)
    lines = [
        "# 🔐 Secrets-/Token-Alters-Wache",
        f"**Stand:** {_today().isoformat()} · **Modus:** "
        f"{'Live-Probe (--verify)' if verification else 'Nachweis-Log (deklariert)'}",
        "",
        f"## Gesamt-Ampel: **{verdict}**",
        "",
        "| Secret | Status | Nachweis |",
        "|---|---|---|",
    ]
    for var, st, proof in summary:
        lines.append(f"| `{var}` | {st} | {proof} |")
    lines += render_pinterest_lifecycle(pin_health)
    infos = [f for f in findings if f.get("level") == "info"]
    hard = [f for f in findings if f.get("level") in ("red", "amber")]
    lines += ["", "## Befunde", ""]
    if hard:
        lines += ["| Ebene | Code | Meldung |", "|---|---|---|"]
        for f in hard:
            lines.append(f"| {f['level'].upper()} | {f['code']} | `{f['var']}` – {f['msg']} |")
    else:
        lines.append("_Alle Secret-Kanäle bestätigt einsatzfähig._")
    if infos:
        lines += ["", "<details><summary>ℹ️ Hinweise (kein Handlungsbedarf)</summary>", ""]
        for f in infos:
            lines.append(f"- `{f['var']}` – {f['msg']}")
        lines += ["", "</details>"]
    lines += ["", "## Empfehlungen", ""]
    recs = []
    if any(f["code"] == "dead" for f in findings):
        recs.append("**Token tot (401/403):** Der Pinterest-Zugang wird über die "
                    f"Token-Wache erneuert – Runbook `{PIN_RUNBOOK}` (Actions → "
                    "„Pinterest-Token-Wache\" → *Run workflow* → Autorisierungs-Code "
                    "einfügen). Danach erneuert sich der Kanal täglich selbst; "
                    "Gegenprobe: `python3 scripts/pinterest_token.py --status`.")
    if any(f["code"] == "manual_token" for f in findings):
        recs.append("**Handbetrieb beenden:** Solange nur `PINTEREST_ACCESS_TOKEN` "
                    "existiert, stirbt der Kanal alle 30 Tage erneut. Einmalig "
                    f"Auto-Erneuerung scharfschalten: `{PIN_RUNBOOK}`.")
    if any(f["code"] in ("oauth_page_missing", "oauth_page_incomplete",
                         "oauth_page_zwilling") for f in findings):
        recs.append("**Empfänger der Rückleitung reparieren:** die Neu-Autorisierung "
                    "führt über `static/pinterest-oauth.html` (Code lesen + Kopierknopf"
                    ") und dessen Zwilling `static/pinterest-oauth/index.html`. Ohne "
                    "diese Seiten ist jeder Anleitungs-Link aus #246 tot – erst "
                    "reparieren, dann autorisieren.")
    if any(f["code"] == "refresh_rotation" for f in findings):
        recs.append("**Erneuerungs-Lauf prüfen:** Der Refresh-Token rotiert nach 60 "
                    "Tagen. Läuft `pinterest-token.yml` täglich? "
                    "`gh run list --workflow=pinterest-token.yml --limit 5`.")
    if any(f["code"] == "stale" for f in findings):
        recs.append("Pflicht-Secret seit über der Frist ohne Erfolg: Kanal läuft "
                    "stumm ins Leere – Workflow-Log prüfen (`gh run list`).")
    if any(f["code"] == "unreachable" for f in findings):
        recs.append("Live-Check nicht möglich (Netzwerk/API-Störung): Die Gesundheit gilt als "
                    "**offen**, nicht als grün – nächsten Lauf abwarten, bei Dauer "
                    "manuell `--verify-only <VAR>` starten.")
    if any(f["code"] == "untracked" for f in findings):
        recs.append("Kein Nachweis, obwohl Secret gesetzt: `--verify` im "
                    "Premium-Governance-Workflow ergänzt diesen Lauf; einmaliger "
                    "`--record-success <VAR> --proof-by <workflow>` genügt als Start.")
    if any(f["code"] == "foreign_proof" for f in findings):
        recs.append("Ein Nachweis kam aus einem Workflow, der das Secret nicht nutzt – "
                    "Vermerk dorthin verlegen, wo das Secret wirklich gebraucht wird.")
    if not recs:
        recs.append("Keine Maßnahmen – Wache läuft wöchentlich mit Live-Probe "
                    "(siehe `premium-governance.yml`).")
    lines += [f"{i}. {r}" for i, r in enumerate(recs, 1)]
    lines += ["", f"_Automatisch erzeugt von `scripts/secrets_age_guard.py` am {_today().isoformat()}._"]
    return "\n".join(lines) + "\n"


# ------------------------------------------------------------------ Selftest

def _selftest():
    """Eingefrorene Fälle – ohne Netzwerk, ohne Seiteneffekte im echten State."""
    failures = []
    today = datetime.date(2026, 9, 7)

    def ent(**kw):
        base = {"last_success": None, "last_attempt": None}
        base.update(kw)
        return base

    meta = {"days": 15, "label": "Pinterest Access-Token", "probe": "pinterest"}
    meta_opt = {"days": 60, "label": "Pinterest Verschlüsselungs-Key",
                "optional": True, "alt_of": "PINTEREST_ACCESS_TOKEN", "probe": None}

    _env = dict(os.environ)

    def fake_secret_value(val):
        return val

    orig_present = globals()["_present"]
    orig_secret = globals()["_secret_value"]
    try:
        # --- #206-Hauptfall: Secret gesetzt, kein Nachweis, kein Live-Check gelaufen
        globals()["_present"] = lambda var: var == "PINTEREST_ACCESS_TOKEN"
        st = classify("PINTEREST_ACCESS_TOKEN", meta, ent(), today=today,
                      live_check_available=False)
        if st[2] is None or st[2]["level"] != "info":
            failures.append("ohne --verify darf 'untracked' keinen Alarm auslösen "
                            "(Dauer-AMBER aus #206)")
        # --- mit Live-Check-Angebot (Workflow hängt --verify nicht ein) -> amber
        st = classify("PINTEREST_ACCESS_TOKEN", meta, ent(), today=today,
                      live_check_available=True)
        if not st[2] or st[2]["code"] != "untracked":
            failures.append("fehlender Nachweis bei verfügbarem Live-Check muss AMBER sein")
        # --- Live-Probe 200 -> grün
        st = classify("PINTEREST_ACCESS_TOKEN", meta, ent(), today=today,
                      verification={"ran": True, "kind": "ok", "detail": "200"})
        if st[2] is not None:
            failures.append("verifiziertes Secret meldet trotzdem einen Befund")
        # --- Live-Probe 401 -> ROT (das ist der Alarm, den wir wollen)
        st = classify("PINTEREST_ACCESS_TOKEN", meta, ent(), today=today,
                      verification={"ran": True, "kind": "dead", "detail": "HTTP 401"})
        if not st[2] or st[2]["level"] != "red" or st[2]["code"] != "dead":
            failures.append("toter Token meldet nicht ROT")
        # --- Alarm-Kontinuität: dead aus Vorlauf bleibt rot ohne neuen Erfolg
        st = classify("PINTEREST_ACCESS_TOKEN", meta,
                      {"verify": "dead", "verify_detail": "HTTP 401",
                       "last_attempt": "2026-09-07", "last_success": "2026-08-01"},
                      today=today)
        if not st[2] or st[2]["level"] != "red" or st[2]["code"] != "dead":
            failures.append("toter Token aus Vorlauf wird ohne neuen Live-Check nicht mehr gemeldet")
        # --- … und heilt, sobald ein Live-Check erfolgreich war
        st = classify("PINTEREST_ACCESS_TOKEN", meta,
                      {"verify": "ok", "last_attempt": "2026-09-07",
                       "last_success": "2026-09-07"}, today=today)
        if st[2] is not None:
            failures.append("nach erfolgreichem Check meldet der geheilte Token weiter rot")
        # --- Netzwerkfehler -> amber, niemals grün
        st = classify("PINTEREST_ACCESS_TOKEN", meta, ent(last_success=str(today)), today=today,
                      verification={"ran": True, "kind": "error", "detail": "URLError"})
        if not st[2] or st[2]["level"] != "amber":
            failures.append("unerreichbare Probe gilt als gesund (falsch)")
        # --- Alter: frisch / altern / stale
        st = classify("PINTEREST_ACCESS_TOKEN", meta, ent(last_success="2026-09-05"), today=today)
        if st[2] is not None:
            failures.append(f"frischer Eintrag meldet ({st[0]})")
        st = classify("PINTEREST_ACCESS_TOKEN", meta, ent(last_success="2026-08-25"), today=today)
        if not st[2] or st[2]["code"] != "aging":
            failures.append("altern (13d von 15d) meldet nicht AMBER")
        st = classify("PINTEREST_ACCESS_TOKEN", meta, ent(last_success="2026-08-01"), today=today)
        if not st[2] or st[2]["code"] != "stale" or st[2]["level"] != "red":
            failures.append("stale meldet nicht ROT")
        # --- Müll im State darf nicht crashen, sondern muss toleriert werden
        st = classify("PINTEREST_ACCESS_TOKEN", meta, {"last_success": "gestern"}, today=today)
        if "UNBEKANNT" not in st[0]:
            failures.append("unparsbares Datum führt nicht zu 'unbekannt'")
        # --- optionale Secrets: kein Alarm, wenn der Alternativpfad aktiv ist
        globals()["_present"] = lambda var: var in ("PINTEREST_ACCESS_TOKEN",)
        st = classify("PINTEREST_TOKEN_KEY", meta_opt, ent(), today=today)
        if st[2] is not None:
            failures.append("optionales Secret mit aktivem Alternativpfad meldet Befund")
        # --- #439: Auch ein GESETZTES Stütz-Secret ohne eigene Live-Probe darf
        # bei verfügbarem --verify nicht als `untracked` in den Governance-Alarm
        # rutschen. Der primäre Pinterest-Kanal beweist die Health.
        globals()["_present"] = lambda var: var in (
            "PINTEREST_ACCESS_TOKEN", "PINTEREST_TOKEN_KEY")
        st = classify("PINTEREST_TOKEN_KEY", meta_opt, ent(), today=today,
                      live_check_available=True)
        if st[2] is not None:
            failures.append("gesetztes optionales Stütz-Secret ohne Probe alarmiert (#439)")
        globals()["_present"] = lambda var: var == "PINTEREST_REFRESH_TOKEN"
        refresh_meta = {"days": 365, "label": "Pinterest Refresh-Token (Auto-Erneuerung)",
                        "optional": True, "probe": None}
        st = classify("PINTEREST_REFRESH_TOKEN", refresh_meta, ent(), today=today,
                      live_check_available=True)
        if not st[2] or st[2]["level"] != "info" or st[2]["code"] != "untracked_optional":
            failures.append("gesetzter optionaler Refresh-Stützkanal ohne Probe ist kein Info-Hinweis")
        if st[2] and actionable([st[2]]):
            failures.append("untracked_optional wird als handlungsbedürftig gezählt")
        # --- optional + nirgends eingerichtet -> info, nicht red
        globals()["_present"] = lambda var: False
        import tempfile as _tf_sec
        with _tf_sec.NamedTemporaryFile("w+", encoding="utf-8") as _tf_sec_cfg:
            _tf_sec_cfg.write("umami_api_import_enabled: true\n")
            _tf_sec_cfg.flush()
            st = classify("UMAMI_API_TOKEN",
                          {"days": 45, "label": "Umami Analytics-API-Token", "probe": "umami",
                           "optional": True}, ent(), today=today, config_path=_tf_sec_cfg.name)
            if not st[2] or st[2]["level"] != "info":
                failures.append("nicht eingerichteter optionaler Kanal meldet keinen info-Hinweis")

        with _tf_sec.NamedTemporaryFile("w+", encoding="utf-8") as _tf_sec_cfg2:
            _tf_sec_cfg2.write("umami_api_import_enabled: false\n")
            _tf_sec_cfg2.flush()
            st_free = classify("UMAMI_API_TOKEN",
                               {"days": 45, "label": "Umami Analytics-API-Token", "probe": "umami",
                                "optional": True}, ent(), today=today, config_path=_tf_sec_cfg2.name)
            if st_free[0] != "BEWUSST DEAKTIVIERT (Umami Free)" or not st_free[2] or st_free[2]["code"] != "operating_boundary":
                failures.append(f"Umami Free Modus liefert nicht BEWUSST DEAKTIVIERT: {st_free}")
        # --- Pflicht-Secret fehlt -> ROT (harter Kanal-Ausfall bleibt sichtbar)
        st = classify("GROQ_API_KEY", {"days": 60, "label": "Groq KI-Key", "probe": "groq"},
                      ent(), today=today)
        if not st[2] or st[2]["level"] != "red":
            failures.append("fehlendes Pflicht-Secret meldet nicht ROT")
        # --- foreign proof: Nachweis aus falschem Workflow ist Info, kein Erfolg
        globals()["_present"] = lambda var: True
        st = classify("GROQ_API_KEY", {"days": 60, "label": "Groq KI-Key", "probe": "groq",
                                       "proof_by": ("content-engine-v2",)},
                      ent(last_success="2026-09-07", quality="declared_foreign",
                          proven_by="premium-governance"), today=today)
        if not st[2] or st[2]["code"] != "foreign_proof":
            failures.append("Selbst-Waschen (Nachweis aus fremdem Workflow) bleibt unsichtbar")
        # --- #206-Lebenszyklus: Handbetrieb ist ein Risiko, kein grüner Zustand
        live_manual = {"state": "live", "severity": "amber", "auto_renew_armed": False,
                       "source_label": "klassisches Secret"}
        res = pinterest_lifecycle_findings(live_manual)
        if not res or res[0]["code"] != "manual_token" or res[0]["level"] != "amber":
            failures.append("Pinterest im 30-Tage-Handbetrieb wird nicht als Risiko "
                            "gemeldet – genau daran starb der Kanal in #206")
        if PIN_RUNBOOK not in res[0]["msg"]:
            failures.append("Handbetrieb-Befund ohne Runbook (nicht handlungsfähig)")
        # --- gesunder Auto-Refresh-Kanal: kein Befund
        healthy = {"state": "live", "severity": "green", "auto_renew_armed": True,
                   "refresh_days_left": 57, "refresh_age_days": 3}
        if pinterest_lifecycle_findings(healthy):
            failures.append("selbsttragender Pinterest-Kanal erzeugt trotzdem Befunde")
        # --- Rotation überfällig: rot BEVOR der Kanal steht
        overdue = {"state": "live", "severity": "red", "auto_renew_armed": True,
                   "refresh_days_left": 4, "refresh_age_days": 56}
        res = pinterest_lifecycle_findings(overdue)
        if not res or res[0]["level"] != "red" or res[0]["code"] != "refresh_rotation":
            failures.append("überfällige Refresh-Rotation wird nicht vorab rot gemeldet")
        soon = {"state": "live", "severity": "amber", "auto_renew_armed": True,
                "refresh_days_left": 15, "refresh_age_days": 45}
        res = pinterest_lifecycle_findings(soon)
        if not res or res[0]["level"] != "amber":
            failures.append("alternder Refresh-Token wird nicht gelb vorgewarnt")
        # --- toter Token: KEIN zweiter Befund (Doppel-Alarm war #206-Muster)
        if pinterest_lifecycle_findings(live_manual, token_dead=True):
            failures.append("toter Kanal erzeugt zusätzlich einen Lebenszyklus-Befund "
                            "(Doppel-Alarm)")
        # --- OAuth-Empfänger: die Handlungsanweisung muss ausführbar bleiben
        if rueckleitung_findings():
            failures.append("intakter Pinterest-Code-Empfänger meldet Befunde "
                            "(die Wache wäre bei #246 störend, nicht helfend): "
                            f"{rueckleitung_findings()}")
        if not rueckleitung_findings(pruef_pfad=os.path.join(
                os.sep, "gibt", "es", "nicht", "pinterest-oauth.html")):
            failures.append("fehlende Empfänger-Seite bleibt unsichtbar – die "
                            "Anweisung aus #246 führte ins Leere")
        import tempfile as _tf
        with _tf.TemporaryDirectory() as _td:
            _bl = os.path.join(_td, "pinterest-oauth.html")
            with open(_bl, "w", encoding="utf-8") as _fh:
                _fh.write("<html><body><p>Umgebaut, ohne Code-Leserei</p></body></html>")
            _f = rueckleitung_findings(
                pruef_pfad=_bl, zwilling_pfad=os.path.join(_td, "weg", "index.html"))
            if len([x for x in _f if x["code"] == "oauth_page_incomplete"]) != 3:
                failures.append("stumpfe Empfänger-Seite wird nicht vollständig "
                                f"benannt: {[x['code'] for x in _f]}")
            if not any(x["code"] == "oauth_page_zwilling" for x in _f):
                failures.append("fehlender Zwilling bleibt ungemeldet (404 für "
                                "Pinterests Umleitung mit Slash)")
        # --- Broker-Ausfall darf die Wache nicht mitreißen
        if pinterest_lifecycle_findings(None):
            failures.append("fehlendes Lagebild erzeugt Phantom-Befunde")
        # --- Auto-Erneuerungspfad ist registriert und dokumentiert
        if "PINTEREST_REFRESH_TOKEN" not in SECRETS:
            failures.append("Refresh-Token nicht in der Secret-Registrierung "
                            "(der Erneuerungspfad bliebe unsichtbar)")
        if "pinterest-token" not in (SECRETS["PINTEREST_ACCESS_TOKEN"].get("proof_by") or ()):
            failures.append("Token-Wache darf den Pinterest-Nachweis nicht führen")
        # --- Lebenszyklus-Block landet im Report (Cockpit-Sichtbarkeit)
        rep = render_report([], [("PINTEREST_ACCESS_TOKEN", "OK", "live")],
                            pin_health=healthy)
        if "Pinterest-Zugang (Lebenszyklus)" not in rep or "Auto-Erneuerung" not in rep:
            failures.append("Report zeigt den Token-Lebenszyklus nicht")
        # --- Verdict-Hierarchie + Actionable-Filter
        fs = [{"level": "info", "code": "not_configured"}, {"level": "amber", "code": "aging"}]
        if verdict_of(fs) != "AMBER":
            failures.append("Verdict-Hierarchie")
        if actionable([{"level": "info", "code": "not_configured"}]):
            failures.append("info-Befund wird als handlungsbedürftig gezählt")
        if actionable([{"level": "amber", "code": "untracked_optional"}]):
            failures.append("INFO_ONLY-Code löst Handlungsbedarf aus")
        # --- _parse_date
        if _parse_date("2026-09-07T05:00:00Z") != today:
            failures.append("ISO-Datetime nicht parst")
        if _parse_date("quatsch") is not None or _parse_date(None) is not None:
            failures.append("Mülldatum parst zu etwas")
        # --- Geparkter Pinterest-Kanal: Domain-Sperre besitzt die Eskalation;
        # der Token darf nicht zusätzlich Governance rot halten.
        import tempfile
        with tempfile.TemporaryDirectory() as td:
            parked_file = os.path.join(td, "pinterest_domain_block.json")
            with open(parked_file, "w", encoding="utf-8") as fh:
                json.dump({"since": "2026-08-27T13:58:16Z", "reason": "Domain gesperrt"}, fh)
            parked = pinterest_channel_parked(parked_file)
            if not parked or parked.get("since") != "2026-08-27T13:58:16Z":
                failures.append("Pinterest-Domain-Sperre wird nicht erkannt")
            pf = parked_pinterest_finding(parked or {"since": "?", "reason": "?"})
            if pf.get("level") != "info" or pf.get("code") not in INFO_ONLY_CODES:
                failures.append("geparkter Pinterest-Kanal eskaliert falsch")
            if pinterest_channel_parked(os.path.join(td, "fehlt.json")) is not None:
                failures.append("fehlende Park-Datei wird fälschlich als Sperre gelesen")
        # --- #439 komplett: geparkter Pinterest-Kanal + gesetzter Token-Key +
        # tote Access-Probe darf nur als Info sichtbar sein, nicht als
        # Governance-Handlungsbefund.
        orig_parked = globals()["pinterest_channel_parked"]
        orig_rueckleitung = globals()["rueckleitung_findings"]
        try:
            globals()["pinterest_channel_parked"] = lambda path=None: {
                "since": "2026-08-27T13:58:16Z", "reason": "Domain gesperrt"}
            globals()["rueckleitung_findings"] = lambda *a, **k: []
            globals()["_present"] = lambda var: var in {
                "GROQ_API_KEY", "GEMINI_API_KEY", "MASTODON_ACCESS_TOKEN",
                "PINTEREST_ACCESS_TOKEN", "PINTEREST_TOKEN_KEY"}
            verification = {
                "GROQ_API_KEY": {"ran": True, "kind": "ok", "detail": "200"},
                "GEMINI_API_KEY": {"ran": True, "kind": "ok", "detail": "200"},
                "MASTODON_ACCESS_TOKEN": {"ran": True, "kind": "ok", "detail": "200"},
                "PINTEREST_ACCESS_TOKEN": {"ran": True, "kind": "dead", "detail": "HTTP 401"},
            }
            f439, _s439 = audit(verification, live_check_available=True,
                                pin_health={"state": "unknown"})
            hard439 = [f for f in actionable(f439)
                       if f.get("var") in {"PINTEREST_ACCESS_TOKEN", "PINTEREST_TOKEN_KEY"}]
            if hard439:
                failures.append("#439-Pinterest-Parklage bleibt handlungsbedürftig: "
                                f"{[(f.get('var'), f.get('code')) for f in hard439]}")
            if not any(f.get("var") == "PINTEREST_ACCESS_TOKEN" and
                       f.get("code") == "channel_parked" for f in f439):
                failures.append("#439-Parklage wird im Report nicht transparent als Hinweis gezeigt")
        finally:
            globals()["pinterest_channel_parked"] = orig_parked
            globals()["rueckleitung_findings"] = orig_rueckleitung
            globals()["_present"] = orig_present
        # --- Report-Format muss vom Governance-Gate parsebar bleiben
        rep = render_report([{"level": "red", "code": "dead", "var": "X", "msg": "tot"}],
                            [("X", "TOT (live-Probe)", "API-Lehnung")])
        if "## Gesamt-Ampel: **RED**" not in rep or "| RED | dead |" not in rep:
            failures.append("Report-Format für Gate nicht parsebar")
        # --- Registrierung konsistent
        for var, reg in SECRETS.items():
            if not reg.get("label") or reg.get("days", 0) <= 0:
                failures.append(f"Registrierung {var} unvollständig")
            if reg.get("probe") is not None and reg["probe"] not in PROBES:
                failures.append(f"{var}: Probe '{reg['probe']}' nicht implementiert")
        if "PINTEREST_ACCESS_TOKEN" not in SECRETS or "GROQ_API_KEY" not in SECRETS:
            failures.append("Pflicht-Secrets aus Registrierung gefallen")
        # --- _sanitize: Secret-Material darf nirgends auftauchen
        tok = "pina_supergeheim123456"
        if tok in _sanitize(f"HTTP 401 for {tok}", tok):
            failures.append("Secret im Log sichtbar")
    finally:
        globals()["_present"] = orig_present
        globals()["_secret_value"] = orig_secret
        os.environ.clear()
        os.environ.update(_env)
    if failures:
        print("❌ SECRETS-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ SECRETS-SELFTEST bestanden (Live-Probe, Nachweis-Qualität, Toleranz, "
          "Ampel-Hierarchie, Report-Format).")
    return 0


# ------------------------------------------------------------------ CLI

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    if "--list" in argv:
        for var_name, spec in CONFIG_ENV_VARS.items():
            # --list: Registry-Katalog (Name, Frist, Prüf-Adapter, berechtigende Workflows) – reine Metadaten.
            days_limit = spec.get("days", 0)
            is_opt = "optional" if spec.get("optional") else "pflicht"
            probe_name = spec.get("probe") or "-"
            allowed_workflows = ",".join(spec.get("proof_by") or ())
            print(f"{var_name}\t{days_limit}d\t{is_opt}\tprobe={probe_name}\tproof_by={allowed_workflows}")
        return 0
    for i, arg in enumerate(argv):
        if arg == "--record-success" and i + 1 < len(argv):
            proof_by = "workflow"
            if "--proof-by" in argv:
                proof_by = argv[argv.index("--proof-by") + 1]
            elif "GITHUB_WORKFLOW" in os.environ:
                proof_by = os.environ["GITHUB_WORKFLOW"].lower().replace(" ", "-")
            return _record_success(argv[i + 1], proof_by=proof_by)

    live = "--verify" in argv
    only = None
    if "--verify-only" in argv:
        only = argv[argv.index("--verify-only") + 1].strip().upper()
        if only not in SECRETS:
            print(f"❌ Unbekanntes Secret '{only}'")
            return 1
        # #219 (08.09.2026): Drei Workflows riefen `--verify-only X` OHNE
        # `--verify` auf – und es lief nie eine Probe. Der Pinterest-Nachweis
        # blieb monatelang „unverified". `--verify-only` heißt ab jetzt, was es
        # sagt: genau dieses eine Secret LIVE prüfen.
        live = True
    verification = None
    if live:
        targets = [only] if only else [v for v in SECRETS if (SECRETS[v].get("probe"))]
        verification = run_verifications(targets)

    pin_health = (_pinterest_health(verify=False)
                  if _present("PINTEREST_ACCESS_TOKEN") else None)
    findings, summary = audit(verification, live_check_available=live,
                              pin_health=pin_health)
    report = render_report(findings, summary, verification, pin_health=pin_health)
    quiet = "--quiet" in argv
    if not quiet:
        with open(REPORT, "w", encoding="utf-8") as f:
            f.write(report)
        print(report)
    if quiet:
        # Nur die Proben-Quittung (für andere Workflows, die den Report nicht
        # schreiben sollen – der entsteht einmal wöchentlich in Governance).
        for var, res in sorted((verification or {}).items()):
            mark = {"ok": "🟢", "dead": "🔴"}.get(res.get("kind"), "🟡")
            print(f"{mark} {var}: {res.get('detail') or res.get('kind')}")
        if only:
            act = [f for f in actionable(findings) if f.get("var") == only]
            return 0 if not act else 1
    act = actionable(findings)
    if "--issue" in argv and act:
        n_red = sum(1 for f in act if f["level"] == "red")
        print("\n===== ISSUE BODY =====\n")
        print(f"## 🔐 Secrets-Wache: {len(act)} Befunde ({n_red} rot)\n\n—\n{report}")
    return 0 if not act else 1


if __name__ == "__main__":
    sys.exit(main())
