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
SECRETS = {
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
        "proof_by": ("pinterest-ai", "pinterest-watchdog", "premium-governance", "repin-weekly"),
    },
    "MASTODON_ACCESS_TOKEN": {
        "days": 45, "label": "Mastodon Access-Token", "probe": "mastodon",
        "proof_by": ("social-ai", "mastodon-seo", "mastodon-profile-sync", "mastodon-manual-post"),
    },
    "PINTEREST_TOKEN_KEY": {
        "days": 60, "label": "Pinterest Verschlüsselungs-Key",
        "optional": True, "alt_of": "PINTEREST_ACCESS_TOKEN", "probe": None,
        "proof_by": ("pinterest-ai",),
    },
    # 07.09.2026 (#206): Die Klick-Datenbank der Monetarisierungs-Schleife war
    # dauerhaft „0 Klicks“, ohne dass jemand sagte, WORAN das liegt (Export
    # fehlt? Token fehlt? API tot?). Mit registriert => die Wache unterscheidet
    # „Kanal tot" von „Kanal nie eingerichtet“.
    "UMAMI_API_TOKEN": {
        "days": 45, "label": "Umami Analytics-API-Token", "probe": "umami",
        "optional": True,
        "proof_by": ("premium-governance",),
    },
}

# Levels: red > amber > info. „info" ist bewusst KEIN Handlungsbedarf.
LEVELS = ("red", "amber", "info")

# Befunde, die NIEMALS ein Governance-Issue auslösen sollen (nur Hinweis).
INFO_ONLY_CODES = {"not_configured", "not_used", "untracked_optional", "probe_skipped"}


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
    var = var.strip().upper()
    if var not in SECRETS:
        print(f"❌ Unbekanntes Secret '{var}' (erlaubt: {', '.join(sorted(SECRETS))})")
        return 1
    reg = SECRETS[var]
    allowed = reg.get("proof_by") or ()
    quality = "declared"
    if allowed and proof_by and proof_by not in allowed:
        # Der Nachweis kommt aus einem Lauf, der das Secret gar nicht benutzt:
        # zählbar, aber als `declared_foreign` sichtbar – die Wache meldet das
        # als Info und die Scorecard verlässt sich nicht darauf.
        quality = "declared_foreign"
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
    label = SECRETS[var]["label"]
    print(f"✅ {label} ({var}): Erfolg am {_today().isoformat()} vermerkt ({quality}, via {proof_by}).")
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


def _pinterest_token():
    """Env-Token, sonst der verschlüsselte Bestand aus pinterest_auth."""
    tok = os.environ.get("PINTEREST_ACCESS_TOKEN", "").strip()
    if tok:
        return tok
    try:
        import pinterest_auth
        tok = pinterest_auth.get_access_token() or ""
        return tok.strip()
    except SystemExit:
        return ""                        # Key fehlt → kein Zugriff, kein Crash
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


def _probe_pinterest(secret):
    code, err = _http_status("https://api.pinterest.com/v5/users/me",
                             {"Authorization": f"Bearer {secret}"})
    if code == 200:
        return "ok", "Pinterest /users/me 200"
    if code in (401, 403):
        return "dead", f"Pinterest-Token abgelaufen/ungültig ({code})"
    return "error", _sanitize(err or f"Pinterest HTTP {code}", secret)


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


def _probe_none(_secret):
    return "skipped", "kein Live-Check für dieses Secret definiert"


PROBES = {
    "groq": _probe_groq,
    "gemini": _probe_gemini,
    "pinterest": _probe_pinterest,
    "mastodon": _probe_mastodon,
    "umami": _probe_umami,
    None: _probe_none,
}


def _secret_value(var):
    """Wert des Secrets so wie die Automatisierung ihn sieht (inkl. Token-Datei)."""
    val = os.environ.get(var, "").strip()
    if val:
        return val
    if var == "PINTEREST_ACCESS_TOKEN":
        return _pinterest_token()
    return ""


def verify_secret(var, retries=PROBE_RETRIES):
    """Ein Live-Check pro Secret. → dict(ok, kind, detail, http_like)."""
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
    """Secret im Env – oder bei Pinterest alternativ als verschlüsselte Datei."""
    if os.environ.get(var, "").strip():
        return True
    return var == "PINTEREST_ACCESS_TOKEN" and os.path.exists(PIN_FILE)


def _alt_active(meta):
    alt = meta.get("alt_of")
    return bool(alt and _present(alt))


def classify(var, meta, ent, today=None, verification=None, live_check_available=False):
    """Ein Secret → (status_text, nachweis_text, finding|None).

    `finding` = None (grün) oder dict(level, code, msg).
    """
    today = today or _today()
    if verification is None:
        verification = {}
    present = _present(var)
    if not present:
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
    if verification.get("ran"):
        return (f"PRÜFUNG NICHT MÖGLICH ({v_detail})", "Netzwerk/API", {
            "level": "amber", "code": "unreachable", "var": var,
            "msg": f"{meta['label']}: Live-Check nicht möglich ({v_detail or 'unbekannt'}) – "
                   f"Health gilt NICHT als bestätigt"})

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


def audit(verification=None, live_check_available=False):
    verification = verification or {}
    state, state_warning = _read_state_file()
    entries = state.get("entries") or {}
    findings = []
    summary = []
    for var, meta in SECRETS.items():
        status, proof, finding = classify(var, meta, entries.get(var) or {},
                                          today=_today(),
                                          verification=verification.get(var),
                                          live_check_available=live_check_available)
        summary.append((var, status, proof))
        if finding:
            findings.append(finding)
    if state_warning:
        findings.append({"level": "amber", "code": "state_corrupt", "var": "STATE",
                         "msg": f"State-Datei: {state_warning}"})
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

def render_report(findings, summary, verification=None):
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
        recs.append("**Token tot (401/403):** sofort erneuern – Pinterest via "
                    "`python3 scripts/pinterest_auth.py --auth-url` + `--exchange <code>`, "
                    "danach `--verify` zur Gegenprobe.")
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
        # --- optional + nirgends eingerichtet -> info, nicht red
        globals()["_present"] = lambda var: False
        st = classify("UMAMI_API_TOKEN",
                      {"days": 45, "label": "Umami Analytics-API-Token", "probe": "umami",
                       "optional": True}, ent(), today=today)
        if not st[2] or st[2]["level"] != "info":
            failures.append("nicht eingerichteter optionaler Kanal meldet keinen info-Hinweis")
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
        for var, reg in SECRETS.items():
            print(f"{var}\t{reg['days']}d\t{'optional' if reg.get('optional') else 'pflicht'}"
                  f"\tprobe={reg.get('probe') or '-'}\tproof_by={','.join(reg.get('proof_by') or ())}")
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
    verification = None
    if live:
        targets = [only] if only else [v for v in SECRETS if (SECRETS[v].get("probe"))]
        verification = run_verifications(targets)

    findings, summary = audit(verification, live_check_available=live)
    report = render_report(findings, summary, verification)
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
