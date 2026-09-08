#!/usr/bin/env python3
"""
PINTEREST-TOKEN-BROKER – eine Quelle der Wahrheit für den Pinterest-Zugang.

WARUM ES DIESE DATEI GIBT (Governance-Report #206, 07.09.2026)
==============================================================
Der wöchentliche Governance-Lauf meldete seit Wochen genau einen roten Befund:

    PINTEREST_ACCESS_TOKEN – Live-Check abgelehnt (401)

Dahinter steckte kein Einzelfall, sondern ein Konstruktionsfehler mit drei
Schichten – und alle drei erzeugen dieselbe Sorte Folgeschaden (stille Kanäle,
rote Läufe, Alarm-Müdigkeit):

  1. **Kein Lebenszyklus.** Pinterest-Access-Tokens sterben nach 30 Tagen.
     Der Betrieb hing an einem *einmal von Hand eingefügten* Secret. Es gab
     zwar eine Auto-Refresh-Mechanik (`scripts/pinterest_auth.py` +
     `data/pinterest_tokens.enc`), aber nie einen Lauf, der sie regelmäßig
     benutzt – die Datei existiert im Repo gar nicht. Ergebnis: Der Kanal
     stirbt planmäßig jeden Monat.

  2. **Sechs verschiedene Token-Wahrheiten.** Jedes Skript entschied selbst,
     woher der Token kommt – und zwar widersprüchlich:
       · pinterest_engine.py / generate_pins.py → Auto-Refresh zuerst
       · secrets_age_guard.py / spam_guard.py / pinterest_perf_feedback.py /
         pinterest_profile_audit.py → Env-Secret zuerst
     Die Wache prüfte damit systematisch einen ANDEREN Token als den, mit dem
     der Bot arbeitet. Ein grüner Report konnte einen toten Kanal bedeuten –
     und ein roter Report einen gesunden. Genau diese Sorte Messfehler ist im
     Agentur-Betrieb teurer als der Ausfall selbst.

  3. **Kein Failover, keine Vorwarnung.** 401 = harter Abbruch (rote Läufe,
     Folge-Issues #153/#209) statt sauberem Rückfall in den Queue-Modus. Und
     niemand warnte VOR dem Ablauf, obwohl das Ablaufdatum bekannt ist.

DIESER BROKER LÖST GENAU DAS
============================
  * **Eine Priorität für alle** (`get_token()`):
      1. verschlüsselter Token-Speicher `data/pinterest_tokens.enc`
         (continuous refresh – Pinterest stellt bei jeder Erneuerung einen
         neuen 60-Tage-Refresh-Token aus → praktisch unbegrenzt)
      2. Bootstrap aus dem Env: `PINTEREST_REFRESH_TOKEN` + `PINTEREST_APP_ID`
         + `PINTEREST_APP_SECRET` → holt einen frischen Access-Token UND legt
         (falls `PINTEREST_TOKEN_KEY` gesetzt ist) den Speicher aus 1. an
      3. klassisches Secret `PINTEREST_ACCESS_TOKEN` (Notnagel, 30 Tage)
  * **Failover statt Absturz:** Jede Quelle wird live geprüft; die erste, die
    HTTP 200 liefert, gewinnt. Ein toter Env-Token blockiert den Betrieb nicht
    mehr, solange der Auto-Refresh lebt (und umgekehrt).
  * **Proaktive Erneuerung:** Der gespeicherte Access-Token wird erneuert,
    bevor er stirbt (Alter > REFRESH_AFTER_DAYS) – nicht erst beim 401.
    Anders als vorher wird NICHT bei jedem Aufruf blind erneuert: Der
    Refresh-Token rotiert, paralleles Erneuern kann ihn entwerten. Deshalb:
    Dateisperre + nur erneuern, wenn nötig.
  * **Sichtbarer Lebenszyklus:** `data/pinterest_token_state.json` hält Quelle,
    Zustand, Fingerabdruck (SHA-256-Kürzel, KEIN Token) und Restlaufzeit fest.
    Die Secrets-Wache liest das und warnt gelb, BEVOR es rot wird.
  * **Keine Secrets in Logs/Reports:** ausschließlich Fingerabdrücke.

NUTZUNG
=======
  Im Code (alle Pinterest-Skripte):
      import pinterest_token
      token = pinterest_token.get_token()        # None = kein lebender Zugang

  Auf der Kommandozeile:
      python3 scripts/pinterest_token.py --status     # Klartext-Lagebild
      python3 scripts/pinterest_token.py --json       # maschinenlesbar
      python3 scripts/pinterest_token.py --refresh    # Erneuerung erzwingen
      python3 scripts/pinterest_token.py --offline    # ohne Netz (nur Bestand)
      python3 scripts/pinterest_token.py --selftest   # eingefrorene Fälle

Exit-Codes: 0 = lebender Zugang · 1 = Handlungsbedarf · 2 = Selbsttest/Fehler.
Runbook bei echtem Handlungsbedarf: docs/PINTEREST-TOKEN-RUNBOOK.md
"""

import base64
import datetime
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

STATE_FILE = os.path.join(BLOG_DIR, "data", "pinterest_token_state.json")
LOCK_FILE = os.path.join(BLOG_DIR, "data", "pinterest_token.lock")
STORE_FILE = os.path.join(BLOG_DIR, "data", "pinterest_tokens.enc")
RUNBOOK = "docs/PINTEREST-TOKEN-RUNBOOK.md"

API = "https://api.pinterest.com/v5"
# /v5/user_account ist der dokumentierte v5-Endpunkt. Die alte Wache prüfte
# `/v5/users/me` – ein Pfad aus der v3-Zeit, den v5 nicht kennt. Eine Wache,
# die einen nicht existierenden Endpunkt befragt, misst nicht den Kanal,
# sondern sich selbst (vgl. #206).
PROBE_PATH = "/user_account"
# Fallback, wenn /user_account mit 403 antwortet: Der Token lebt dann meist,
# ihm fehlt nur der Scope `user_accounts:read` (Altbestand vor 08.09.2026).
# Ein lebender Token ohne Profil-Scope darf nicht als „tot" gelten – sonst
# rotiert der Broker sinnlos und meldet ROT für einen funktionierenden Kanal.
PROBE_FALLBACK_PATH = "/boards?page_size=1"
PROBE_TIMEOUT = 20

# Wer darf den Refresh-Token PROAKTIV rotieren? Nur die Token-Wache
# (pinterest-token.yml setzt PINTEREST_TOKEN_WACHE=1) und lokale Aufrufe mit
# --refresh. Alle anderen Prozesse (Pinterest-AI, Watchdog, Governance …)
# erneuern nur nach einem echten 401 (Failover). Grund (#219, 08.09.2026):
# Zwei Runner, die denselben Refresh-Token gleichzeitig rotieren, entwerten
# sich gegenseitig – der Verlierer committet einen toten Speicher.
WACHE_ENV = "PINTEREST_TOKEN_WACHE"

# Access-Token: 30 Tage. Wir erneuern deutlich früher – ein Lauf darf ruhig
# einmal ausfallen, ohne dass der Kanal stirbt.
ACCESS_TTL_DAYS = 30
REFRESH_AFTER_DAYS = 20
# Refresh-Token: 60 Tage, rotiert bei jeder Erneuerung. Läuft die Automatik
# länger nicht (Repo pausiert, Workflow deaktiviert), wird es eng → Vorwarnung.
REFRESH_TTL_DAYS = 60
REFRESH_WARN_DAYS = 40
REFRESH_CRITICAL_DAYS = 52

SOURCE_LABELS = {
    "store": "Auto-Refresh-Speicher (data/pinterest_tokens.enc)",
    "refresh_env": "Refresh-Token aus dem Env (PINTEREST_REFRESH_TOKEN)",
    "env": "klassisches Secret PINTEREST_ACCESS_TOKEN",
}

_PROCESS_CACHE = {}          # ein Lauf, eine Auflösung (kein Refresh-Sturm)


# --------------------------------------------------------------------- Helfer

def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def fingerprint(token):
    """Wiedererkennbare, aber unumkehrbare Kennung – nie das Token selbst."""
    if not token:
        return ""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()[:12]


def _redact(text, *secrets):
    out = str(text or "")
    for sec in secrets:
        if sec and len(sec) >= 6:
            out = out.replace(sec, "***")
    return " ".join(out.split())[:200]


def _parse_ts(raw):
    if not raw or not isinstance(raw, str):
        return None
    try:
        return datetime.datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_days(raw, now=None):
    ts = _parse_ts(raw)
    if not ts:
        return None
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=datetime.timezone.utc)
    return max(0, int(((now or _now()) - ts).total_seconds() // 86400))


def _lock():
    """Dateisperre: Der Refresh-Token rotiert – zwei Läufe gleichzeitig würden
    sich gegenseitig entwerten. Ohne fcntl (Windows) läuft es unverriegelt."""
    try:
        import fcntl
    except ImportError:
        return None
    try:
        os.makedirs(os.path.dirname(LOCK_FILE), exist_ok=True)
        fh = open(LOCK_FILE, "a+", encoding="utf-8")
    except OSError:
        return None
    for _ in range(60):                       # bis ~15 s auf den Nachbarlauf warten
        try:
            fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            return fh
        except OSError:
            time.sleep(0.25)
    return fh


def _unlock(fh):
    if fh is None:
        return
    try:
        import fcntl
        fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
    except Exception:  # noqa: BLE001
        pass
    try:
        fh.close()
    except OSError:
        pass


# ------------------------------------------------------- Austauschbare Backends
# Alle Netz-/Krypto-Zugriffe laufen über diese vier Funktionen. Der Selbsttest
# ersetzt sie durch eingefrorene Attrappen – dadurch ist die gesamte Logik
# offline, deterministisch und ohne echte Secrets prüfbar.

def _http_get(path, token):
    """→ (status|None, fehlertext|None) – nie Secret-Material."""
    req = urllib.request.Request(
        API + path,
        headers={"Authorization": f"Bearer {token}",
                 "User-Agent": "franksfin-pinterest-token/1.1"})
    try:
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            resp.read(512)
            return getattr(resp, "status", 200), None
    except urllib.error.HTTPError as exc:
        return exc.code, f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, f"Netzwerkfehler ({exc.__class__.__name__})"


def _default_probe(token):
    """→ ('live'|'dead'|'unreachable', Detailtext). Nie Secret-Material.

    /v5/user_account verlangt den Scope `user_accounts:read`. Fehlt er (Token
    aus der Zeit vor 08.09.2026), antwortet Pinterest 403, obwohl der Token
    für Boards/Pins völlig in Ordnung ist. Deshalb Gegenprobe auf /v5/boards.
    """
    code, err = _http_get(PROBE_PATH, token)
    if code == 200:
        return "live", f"GET /v5{PROBE_PATH} 200"
    if code == 403:
        code2, _ = _http_get(PROBE_FALLBACK_PATH, token)
        if code2 == 200:
            return "live", ("GET /v5/boards 200 – Token lebt, aber ohne Scope "
                            "`user_accounts:read` (Profil-Audit eingeschränkt; "
                            "bei nächster Neu-Autorisierung automatisch dabei)")
        if code2 in (401, 403):
            return "dead", f"Pinterest lehnt den Token ab (HTTP {code2})"
    if code in (401, 403):
        return "dead", f"Pinterest lehnt den Token ab (HTTP {code})"
    if code == 429:
        return "unreachable", "Pinterest-Rate-Limit (HTTP 429)"
    if code is None:
        return "unreachable", err or "Netzwerkfehler"
    return "unreachable", f"Pinterest antwortet HTTP {code}"


def _default_store_load():
    """Entschlüsselter Token-Speicher oder None (nie Absturz)."""
    try:
        import pinterest_auth
        return pinterest_auth.load_store()
    except Exception:  # noqa: BLE001  – Krypto-Lib/Key fehlt: kein Grund zu sterben
        return None


def _default_store_save(data):
    try:
        import pinterest_auth
        pinterest_auth.save_store(data)
        return True
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Token-Speicher nicht schreibbar ({exc.__class__.__name__}) – "
              f"Erneuerung gilt nur für diesen Lauf.")
        return False


def _default_oauth_refresh(app_id, app_secret, refresh_token):
    """Refresh-Grant gegen Pinterest. → dict(access_token, refresh_token?)."""
    basic = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    body = urllib.parse.urlencode({"grant_type": "refresh_token",
                                   "refresh_token": refresh_token}).encode()
    req = urllib.request.Request(
        API + "/oauth/token", data=body, method="POST",
        headers={"Authorization": f"Basic {basic}",
                 "Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=PROBE_TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = _redact(exc.read().decode()[:200], refresh_token, app_secret)
        raise RuntimeError(f"OAuth-Refresh HTTP {exc.code}: {detail}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise RuntimeError(f"OAuth-Refresh nicht erreichbar ({exc.__class__.__name__})") from exc


HOOKS = {
    "probe": _default_probe,
    "store_load": _default_store_load,
    "store_save": _default_store_save,
    "oauth_refresh": _default_oauth_refresh,
    "env": lambda name: os.environ.get(name, "").strip(),
}


def _hook(hooks, name):
    return (hooks or {}).get(name) or HOOKS[name]


def _is_wache(env):
    """Läuft dieser Prozess als Token-Wache (darf proaktiv rotieren)?"""
    return str(env(WACHE_ENV) or "").strip().lower() in ("1", "true", "yes", "ja")


# ------------------------------------------------------------------- Auflösung

def _store_credentials(store, hooks):
    """App-Zugangsdaten: bevorzugt aus dem Speicher, sonst aus dem Env."""
    env = _hook(hooks, "env")
    app_id = (store or {}).get("app_id") or env("PINTEREST_APP_ID")
    app_secret = (store or {}).get("app_secret") or env("PINTEREST_APP_SECRET")
    return app_id, app_secret


def _refresh_store(store, hooks, now):
    """Erneuert den Speicher (unter Sperre). → (neuer_store|None, Detailtext)."""
    app_id, app_secret = _store_credentials(store, hooks)
    refresh_token = (store or {}).get("refresh_token")
    if not (app_id and app_secret and refresh_token):
        return None, ("Speicher ohne App-Zugangsdaten/Refresh-Token – "
                      "keine Erneuerung möglich")
    lock = _lock()
    try:
        # Unter der Sperre neu laden: Ein Nachbarlauf kann gerade rotiert haben.
        fresh = _hook(hooks, "store_load")() or store
        refresh_token = fresh.get("refresh_token") or refresh_token
        try:
            resp = _hook(hooks, "oauth_refresh")(app_id, app_secret, refresh_token)
        except Exception as exc:  # noqa: BLE001
            return None, _redact(str(exc), refresh_token, app_secret)
        new = dict(fresh)
        new["app_id"], new["app_secret"] = app_id, app_secret
        new["access_token"] = resp.get("access_token") or ""
        if resp.get("refresh_token"):
            new["refresh_token"] = resp["refresh_token"]
            new["refresh_rotated_at"] = now.isoformat()
        new["refreshed_at"] = now.isoformat()
        _absorb_oauth_meta(new, resp)
        if not new["access_token"]:
            return None, "Pinterest lieferte keinen Access-Token zurück"
        _hook(hooks, "store_save")(new)
        return new, "Access-Token erneuert (continuous refresh)"
    finally:
        _unlock(lock)


def _absorb_oauth_meta(store, resp):
    """Scope + Ablaufdaten aus der OAuth-Antwort merken (kein Token-Material).

    Pinterest liefert `scope`, `expires_in` (Access, 30 d) und
    `refresh_token_expires_at` (Unix-Zeit der Zwangs-Rotation). Damit rechnet
    das Lagebild mit Pinterests Uhr statt mit unserer Annahme.
    """
    if resp.get("scope"):
        store["scope"] = str(resp["scope"])
    try:
        if resp.get("refresh_token_expires_at"):
            store["refresh_expires_at"] = datetime.datetime.fromtimestamp(
                int(resp["refresh_token_expires_at"]), datetime.timezone.utc).isoformat()
        elif resp.get("refresh_token_expires_in"):
            store["refresh_expires_at"] = (
                _now() + datetime.timedelta(seconds=int(resp["refresh_token_expires_in"]))
            ).isoformat()
    except (TypeError, ValueError, OverflowError, OSError):
        pass
    return store


def _bootstrap_from_env(hooks, now):
    """Refresh-Token als GitHub-Secret → frischer Access-Token (+ Speicher).

    Damit ist die Auto-Erneuerung ohne den einmaligen Browser-Handschlag
    scharfzuschalten – der wichtigste Bootstrap-Pfad für einen Betrieb,
    der ausschließlich in GitHub Actions läuft.
    """
    env = _hook(hooks, "env")
    app_id, app_secret = env("PINTEREST_APP_ID"), env("PINTEREST_APP_SECRET")
    refresh_token = env("PINTEREST_REFRESH_TOKEN")
    if not (app_id and app_secret and refresh_token):
        return None, "unvollständig (APP_ID/APP_SECRET/REFRESH_TOKEN)"
    try:
        resp = _hook(hooks, "oauth_refresh")(app_id, app_secret, refresh_token)
    except Exception as exc:  # noqa: BLE001
        return None, _redact(str(exc), refresh_token, app_secret)
    data = {
        "app_id": app_id, "app_secret": app_secret,
        "access_token": resp.get("access_token") or "",
        "refresh_token": resp.get("refresh_token") or refresh_token,
        "refreshed_at": now.isoformat(),
        "refresh_rotated_at": now.isoformat() if resp.get("refresh_token") else None,
        "bootstrapped_from": "env",
    }
    _absorb_oauth_meta(data, resp)
    if not data["access_token"]:
        return None, "Pinterest lieferte keinen Access-Token zurück"
    if env("PINTEREST_TOKEN_KEY"):
        # Ab jetzt trägt sich der Kanal selbst: der rotierte Refresh-Token
        # landet verschlüsselt im Repo, das Env-Secret ist nur noch Startpunkt.
        _hook(hooks, "store_save")(data)
    return data, "Access-Token aus Env-Refresh-Token geholt"


def resolve(verify=True, allow_refresh=True, force_refresh=False,
            hooks=None, now=None):
    """Vollständige Lagebeurteilung. → dict (enthält `token` – nur intern nutzen).

    Reihenfolge: Speicher (mit proaktiver Erneuerung) → Env-Refresh-Bootstrap →
    klassisches Env-Secret. Die erste Quelle, die live antwortet, gewinnt.
    """
    now = now or _now()
    probe = _hook(hooks, "probe")
    env = _hook(hooks, "env")
    attempts = []
    token, source, state, detail = None, None, "absent", "keine Token-Quelle konfiguriert"

    store = _hook(hooks, "store_load")()
    store_age = _age_days((store or {}).get("refreshed_at")
                          or (store or {}).get("saved_at"), now) if store else None
    rotate_age = _age_days((store or {}).get("refresh_rotated_at")
                           or (store or {}).get("refreshed_at")
                           or (store or {}).get("saved_at"), now) if store else None

    # ---------------------------------------------------------------- 1) Speicher
    if store:
        stale = store_age is None or store_age >= REFRESH_AFTER_DAYS
        # Proaktiv rotiert nur die Token-Wache (oder ein expliziter --refresh).
        # Alle anderen dürfen NUR nach 401 erneuern – sonst Rotations-Kollision.
        proactive_ok = force_refresh or _is_wache(env)
        if allow_refresh and proactive_ok and (force_refresh or stale):
            new, why = _refresh_store(store, hooks, now)
            attempts.append({"source": "store", "action": "refresh",
                             "result": "ok" if new else "failed", "detail": why})
            if new:
                store = new
                store_age, rotate_age = 0, _age_days(
                    new.get("refresh_rotated_at") or new.get("refreshed_at"), now)
        cand = (store or {}).get("access_token") or ""
        if cand:
            if verify:
                kind, why = probe(cand)
            else:
                kind, why = "unverified", "ohne Live-Probe übernommen"
            attempts.append({"source": "store", "action": "probe", "result": kind,
                             "detail": why, "fingerprint": fingerprint(cand)})
            if kind in ("live", "unverified"):
                token, source, state, detail = cand, "store", kind, why
            elif kind == "dead" and allow_refresh and not force_refresh:
                # 401 trotz frischem Speicher → jetzt doch erneuern (Failover).
                new, why2 = _refresh_store(store, hooks, now)
                attempts.append({"source": "store", "action": "refresh-after-401",
                                 "result": "ok" if new else "failed", "detail": why2})
                if new and new.get("access_token"):
                    kind2, why3 = probe(new["access_token"]) if verify else ("unverified", "")
                    attempts.append({"source": "store", "action": "probe",
                                     "result": kind2, "detail": why3,
                                     "fingerprint": fingerprint(new["access_token"])})
                    if kind2 in ("live", "unverified"):
                        store, store_age = new, 0
                        token, source, state, detail = new["access_token"], "store", kind2, why3
            if not token:
                state, detail = kind, why
        else:
            attempts.append({"source": "store", "action": "read", "result": "empty",
                             "detail": "Speicher ohne Access-Token"})

    # ------------------------------------------------- 2) Bootstrap aus dem Env
    if not token and allow_refresh:
        if env("PINTEREST_REFRESH_TOKEN"):
            data, why = _bootstrap_from_env(hooks, now)
            attempts.append({"source": "refresh_env", "action": "bootstrap",
                             "result": "ok" if data else "failed", "detail": why})
            cand = (data or {}).get("access_token") or ""
            if cand:
                kind, why2 = probe(cand) if verify else ("unverified", "ohne Live-Probe")
                attempts.append({"source": "refresh_env", "action": "probe",
                                 "result": kind, "detail": why2,
                                 "fingerprint": fingerprint(cand)})
                if kind in ("live", "unverified"):
                    token, source, state, detail = cand, "refresh_env", kind, why2
                    if not store:
                        store, store_age, rotate_age = data, 0, 0
                else:
                    state, detail = kind, why2

    # ------------------------------------------------- 3) klassisches Env-Secret
    if not token:
        cand = env("PINTEREST_ACCESS_TOKEN")
        if cand:
            kind, why = probe(cand) if verify else ("unverified", "ohne Live-Probe übernommen")
            attempts.append({"source": "env", "action": "probe", "result": kind,
                             "detail": why, "fingerprint": fingerprint(cand)})
            if kind in ("live", "unverified"):
                token, source, state, detail = cand, "env", kind, why
            else:
                state, detail = kind, why
        elif not attempts:
            attempts.append({"source": "env", "action": "read", "result": "absent",
                             "detail": "PINTEREST_ACCESS_TOKEN nicht gesetzt"})

    renewable = bool(
        ((store or {}).get("refresh_token") and all(_store_credentials(store, hooks)))
        or (env("PINTEREST_REFRESH_TOKEN") and env("PINTEREST_APP_ID")
            and env("PINTEREST_APP_SECRET")))

    if token:
        state = "live" if state in ("live",) else ("unverified" if state == "unverified" else "live")
    elif state == "absent" and (store or env("PINTEREST_ACCESS_TOKEN")):
        state = "dead"

    health = {
        "checked_at": now.isoformat(timespec="seconds"),
        "verified": bool(verify),
        "written_by": (env("GITHUB_WORKFLOW") or "lokal").strip()[:60],
        "scopes": (store or {}).get("scope") or "",
        "state": state,
        "source": source,
        "source_label": SOURCE_LABELS.get(source or "", "keine"),
        "detail": detail,
        "fingerprint": fingerprint(token),
        "renewable": renewable,
        "auto_renew_armed": bool(store and (store or {}).get("refresh_token")),
        "store_present": bool(store),
        "access_age_days": store_age,
        "refresh_age_days": rotate_age,
        "refresh_days_left": _refresh_days_left(store, rotate_age, now),
        "refresh_expires_at": (store or {}).get("refresh_expires_at") or None,
        "attempts": attempts,
        "runbook": RUNBOOK,
        "token": token,
    }
    health["next_action"] = _next_action(health)
    health["severity"] = _severity(health)
    return health


def _refresh_days_left(store, rotate_age, now):
    """Restlaufzeit des Refresh-Tokens – nach Pinterests Uhr, wenn bekannt.

    Pinterest liefert `refresh_token_expires_at` in jeder Erneuerungsantwort.
    Liegt das vor, zählt es; sonst die eigene Rechnung (60 d ab Rotation).
    """
    exp = _parse_ts((store or {}).get("refresh_expires_at"))
    if exp is not None:
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=datetime.timezone.utc)
        return max(0, int((exp - now).total_seconds() // 86400))
    if rotate_age is None:
        return None
    return max(0, REFRESH_TTL_DAYS - rotate_age)


def _next_action(h):
    if h["state"] == "live":
        if not h["auto_renew_armed"]:
            return ("Zugang lebt, hängt aber am 30-Tage-Handbetrieb. Auto-Erneuerung "
                    f"scharfschalten: {RUNBOOK} (5 Minuten, danach nie wieder).")
        left = h.get("refresh_days_left")
        if left is not None and left <= (REFRESH_TTL_DAYS - REFRESH_WARN_DAYS):
            return (f"Auto-Erneuerung läuft, aber der Refresh-Token ist "
                    f"{h.get('refresh_age_days')} Tage alt (Rotation nach "
                    f"{REFRESH_TTL_DAYS} Tagen). Token-Wache muss täglich laufen.")
        return "Nichts zu tun – der Kanal erneuert sich selbst."
    if h["state"] == "unreachable":
        return ("Pinterest war nicht erreichbar (Netz/Rate-Limit). Kein Handlungsbedarf: "
                "Der nächste Lauf prüft erneut; erst dauerhafte Ausfälle werden rot.")
    if h["renewable"]:
        return ("Erneuerung war möglich, ist aber fehlgeschlagen – App-Zugangsdaten "
                f"(PINTEREST_APP_ID/SECRET) und Refresh-Token prüfen: {RUNBOOK}")
    return ("Einmalige Neu-Autorisierung nötig (danach trägt sich der Kanal selbst): "
            f"{RUNBOOK} – `python3 scripts/pinterest_auth.py --auth-url`")


def _severity(h):
    """green = alles gut · amber = kümmern · red = Kanal steht."""
    if h["state"] == "live":
        if not h["auto_renew_armed"]:
            return "amber"
        left = h.get("refresh_days_left")
        if left is not None and left <= (REFRESH_TTL_DAYS - REFRESH_CRITICAL_DAYS):
            return "red"
        if left is not None and left <= (REFRESH_TTL_DAYS - REFRESH_WARN_DAYS):
            return "amber"
        return "green"
    if h["state"] in ("unverified",):
        return "amber"
    if h["state"] == "unreachable":
        return "amber"
    return "red"


# ------------------------------------------------------------------- Zustand

def _may_persist(health, exists):
    """Darf dieses Lagebild die Datei überschreiben?

    Befund #219 (08.09.2026): JEDER Prozess schrieb die Datei – auch der
    Deploy-Lauf ohne ein einziges Secret (→ `absent/red`) und der Nachweis-
    Schritt ohne Live-Probe (→ `unverified/amber`). Das Cockpit zeigte damit
    den Stand des am schlechtesten informierten Prozesses, nicht die Wahrheit.
    Regel: Nur ein LIVE geprüftes Lagebild darf schreiben – und „nichts
    konfiguriert" überschreibt niemals einen vorhandenen Befund.
    """
    if not health.get("verified"):
        return False
    if health.get("state") == "absent" and exists:
        return False
    return True


def save_state(health, force=False):
    """Schreibt das Lagebild – ohne Token, atomar, tolerant, nur wenn beglaubigt."""
    public = {k: v for k, v in health.items() if k != "token"}
    public["attempts"] = [
        {k: v for k, v in a.items()} for a in health.get("attempts", [])]
    if not force and not _may_persist(health, os.path.exists(STATE_FILE)):
        return public
    try:
        os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
        tmp = f"{STATE_FILE}.tmp-{os.getpid()}"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(public, f, ensure_ascii=False, indent=2, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, STATE_FILE)
    except OSError as exc:
        print(f"⚠ Token-Lagebild nicht schreibbar: {exc.__class__.__name__}")
    return public


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


# --------------------------------------------------------------- Öffentliche API

def get_token(verify=True, allow_refresh=True, record_state=True, quiet=True):
    """DER Weg an einen Pinterest-Token. → str oder None (kein lebender Zugang).

    Alle Pinterest-Skripte benutzen ausschließlich diese Funktion – damit prüft
    die Wache exakt den Token, mit dem der Bot arbeitet (Kernbefund #206).
    """
    key = (verify, allow_refresh)
    if key in _PROCESS_CACHE:
        return _PROCESS_CACHE[key]
    health = resolve(verify=verify, allow_refresh=allow_refresh)
    if record_state:
        save_state(health)
    if not quiet:
        print(describe(health))
    _PROCESS_CACHE[key] = health.get("token")
    return _PROCESS_CACHE[key]


def health(verify=True, allow_refresh=True, record_state=True):
    """Lagebild ohne Token-Material (für Wachen, Reports, Governance)."""
    h = resolve(verify=verify, allow_refresh=allow_refresh)
    if record_state:
        save_state(h)
    return {k: v for k, v in h.items() if k != "token"}


def describe(h):
    icon = {"green": "🟢", "amber": "🟡", "red": "🔴"}.get(h.get("severity"), "⚪")
    lines = [
        f"{icon} Pinterest-Zugang: {h.get('state')} "
        f"(Quelle: {h.get('source_label')})",
        f"   Nachweis: {h.get('detail')}",
        f"   Auto-Erneuerung: {'scharf' if h.get('auto_renew_armed') else 'NICHT scharf'}"
        f" · erneuerbar: {'ja' if h.get('renewable') else 'nein'}",
    ]
    if h.get("access_age_days") is not None:
        lines.append(f"   Access-Token-Alter: {h['access_age_days']}d "
                     f"(Ablauf nach {ACCESS_TTL_DAYS}d)")
    if h.get("refresh_days_left") is not None:
        lines.append(f"   Refresh-Token: noch {h['refresh_days_left']}d bis zur "
                     f"Zwangs-Rotation")
    if h.get("scopes"):
        lines.append(f"   Scopes: {h['scopes']}")
    if h.get("fingerprint"):
        lines.append(f"   Fingerabdruck: {h['fingerprint']} (kein Token-Material)")
    lines.append(f"   Live geprüft: {'ja' if h.get('verified') else 'nein (Bestand)'}"
                 f" · Lagebild von: {h.get('written_by') or '?'}")
    lines.append(f"   Nächster Schritt: {h.get('next_action')}")
    return "\n".join(lines)


# ------------------------------------------------------------------- Selbsttest

def _selftest():
    """Eingefrorene Fälle – ohne Netz, ohne echte Secrets, deterministisch."""
    failures = []
    now = datetime.datetime(2026, 9, 7, 6, 0, tzinfo=datetime.timezone.utc)

    def mk(probe_map, store=None, env=None, refresh_result=None, saved=None):
        saved = saved if saved is not None else []

        def probe(tok):
            return probe_map.get(tok, ("dead", "unbekannter Token"))

        def store_load():
            return dict(store) if store else None

        def store_save(data):
            saved.append(dict(data))
            return True

        def oauth_refresh(app_id, app_secret, refresh_token):
            if refresh_result is None:
                raise RuntimeError("OAuth-Refresh HTTP 401: invalid_grant")
            return dict(refresh_result)

        return {"probe": probe, "store_load": store_load, "store_save": store_save,
                "oauth_refresh": oauth_refresh,
                "env": lambda name: (env or {}).get(name, "")}, saved

    # --- Fall 1 (#206-Kern): Env-Secret tot, Auto-Refresh lebt → GRÜN statt ROT
    hooks, saved = mk(
        probe_map={"alt": ("dead", "HTTP 401"), "neu": ("live", "200")},
        store={"access_token": "alt", "refresh_token": "r1", "app_id": "a",
               "app_secret": "s", "refreshed_at": now.isoformat()},
        env={"PINTEREST_ACCESS_TOKEN": "envtot"},
        refresh_result={"access_token": "neu", "refresh_token": "r2"})
    h = resolve(hooks=hooks, now=now)
    if h["token"] != "neu" or h["state"] != "live" or h["source"] != "store":
        failures.append(f"Failover nach 401 im Speicher misslingt: {h['state']}/{h['source']}")
    if h["severity"] != "green":
        failures.append("lebender Auto-Refresh-Kanal wird nicht grün bewertet")
    if not saved or saved[-1]["refresh_token"] != "r2":
        failures.append("rotierter Refresh-Token wird nicht gespeichert (Kanal stirbt in 60d)")

    # --- Fall 2: gar keine Erneuerung möglich, Env-Token tot → ROT + Runbook
    hooks, _ = mk(probe_map={"envtot": ("dead", "HTTP 401")},
                  env={"PINTEREST_ACCESS_TOKEN": "envtot"})
    h = resolve(hooks=hooks, now=now)
    if h["token"] or h["severity"] != "red":
        failures.append("toter Token ohne Erneuerungspfad meldet nicht ROT")
    if RUNBOOK not in h["next_action"]:
        failures.append("roter Befund ohne Runbook-Verweis (nicht handlungsfähig)")

    # --- Fall 3: Env-Secret tot, aber Bootstrap über PINTEREST_REFRESH_TOKEN
    hooks, saved = mk(probe_map={"envtot": ("dead", "401"), "boot": ("live", "200")},
                      env={"PINTEREST_ACCESS_TOKEN": "envtot",
                           "PINTEREST_REFRESH_TOKEN": "r0", "PINTEREST_APP_ID": "a",
                           "PINTEREST_APP_SECRET": "s", "PINTEREST_TOKEN_KEY": "k" * 20},
                      refresh_result={"access_token": "boot", "refresh_token": "r1"})
    h = resolve(hooks=hooks, now=now)
    if h["token"] != "boot" or h["source"] != "refresh_env":
        failures.append("Bootstrap aus dem Env-Refresh-Token funktioniert nicht")
    if not saved:
        failures.append("Bootstrap legt den Auto-Refresh-Speicher nicht an "
                        "(bliebe Handbetrieb)")

    # --- Fall 4: Env-Token lebt, Speicher fehlt → grün, aber AMBER (Handbetrieb)
    hooks, _ = mk(probe_map={"envlive": ("live", "200")},
                  env={"PINTEREST_ACCESS_TOKEN": "envlive"})
    h = resolve(hooks=hooks, now=now)
    if h["state"] != "live" or h["severity"] != "amber":
        failures.append("Handbetrieb (30-Tage-Secret ohne Auto-Refresh) wird nicht "
                        "als Risiko markiert – genau so entstand #206")

    # --- Fall 5: Pinterest gestört → AMBER, niemals rot, niemals grün
    hooks, _ = mk(probe_map={"x": ("unreachable", "HTTP 500")},
                  env={"PINTEREST_ACCESS_TOKEN": "x"})
    h = resolve(hooks=hooks, now=now)
    if h["severity"] != "amber" or h["token"]:
        failures.append("Störung bei Pinterest wird nicht als AMBER behandelt")

    # --- Fall 6: proaktive Erneuerung VOR Ablauf (Alter > REFRESH_AFTER_DAYS)
    #     … aber NUR durch die Token-Wache (#219: Rotations-Kollision).
    old = (now - datetime.timedelta(days=25)).isoformat()
    old_store = {"access_token": "alt", "refresh_token": "r1", "app_id": "a",
                 "app_secret": "s", "refreshed_at": old}
    hooks, saved = mk(probe_map={"alt": ("live", "200"), "neu": ("live", "200")},
                      store=old_store, env={WACHE_ENV: "1"},
                      refresh_result={"access_token": "neu", "refresh_token": "r2",
                                      "scope": "boards:read pins:read",
                                      "refresh_token_expires_at": 1762000000})
    h = resolve(hooks=hooks, now=now)
    if h["token"] != "neu":
        failures.append("alter Access-Token wird von der Wache nicht proaktiv erneuert "
                        "(Kanal stirbt am 30. Tag)")
    if not saved or saved[-1].get("scope") != "boards:read pins:read" \
            or not saved[-1].get("refresh_expires_at"):
        failures.append("Scope/Ablaufdatum aus der OAuth-Antwort werden nicht gespeichert")
    hooks, saved = mk(probe_map={"alt": ("live", "200"), "neu": ("live", "200")},
                      store=old_store, env={},
                      refresh_result={"access_token": "neu", "refresh_token": "r2"})
    h = resolve(hooks=hooks, now=now)
    if h["token"] != "alt" or saved:
        failures.append("Fremdprozess (kein Wache-Flag) rotiert den Refresh-Token proaktiv – "
                        "zwei Runner würden sich gegenseitig aussperren (#219)")
    if h["state"] != "live":
        failures.append("lebender Alt-Token ohne Wache-Rotation gilt nicht als live")
    # … der Failover nach 401 bleibt aber JEDEM Prozess erlaubt (Kanal darf nie stehen):
    hooks, saved = mk(probe_map={"alt": ("dead", "401"), "neu": ("live", "200")},
                      store=old_store, env={},
                      refresh_result={"access_token": "neu", "refresh_token": "r2"})
    h = resolve(hooks=hooks, now=now)
    if h["token"] != "neu" or not saved:
        failures.append("Failover nach 401 ohne Wache-Flag funktioniert nicht")
    # … und --refresh (explizit) darf immer:
    hooks, saved = mk(probe_map={"alt": ("live", "200"), "neu": ("live", "200")},
                      store=old_store, env={},
                      refresh_result={"access_token": "neu", "refresh_token": "r2"})
    h = resolve(hooks=hooks, now=now, force_refresh=True)
    if h["token"] != "neu":
        failures.append("--refresh erzwingt keine Erneuerung")

    # --- Fall 6c: Live-Probe mit 403 auf /user_account, aber 200 auf /boards
    #     (Token ohne `user_accounts:read`) → LIVE, nicht tot.
    calls = []

    def fake_get(path, token, _calls=calls):
        _calls.append(path)
        if path == PROBE_PATH:
            return 403, "HTTP 403"
        if path == PROBE_FALLBACK_PATH:
            return 200, None
        return 500, "HTTP 500"
    orig_get = globals()["_http_get"]
    globals()["_http_get"] = fake_get
    try:
        kind, why = _default_probe("tok")
        if kind != "live" or "user_accounts:read" not in why:
            failures.append("Token ohne Profil-Scope (403) wird als tot behandelt – "
                            "Broker würde einen lebenden Kanal rot melden und sinnlos rotieren")
        calls.clear()
        globals()["_http_get"] = lambda path, token: (401, "HTTP 401")
        if _default_probe("tok")[0] != "dead":
            failures.append("401 wird nicht als tot erkannt")
        globals()["_http_get"] = lambda path, token: (403, "HTTP 403")
        if _default_probe("tok")[0] != "dead":
            failures.append("403 auf beiden Endpunkten wird nicht als tot erkannt")
        globals()["_http_get"] = lambda path, token: (None, "Netzwerkfehler (URLError)")
        if _default_probe("tok")[0] != "unreachable":
            failures.append("Netzwerkfehler wird nicht als unreachable erkannt")
    finally:
        globals()["_http_get"] = orig_get

    # --- Fall 6d: Lagebild-Schreibrecht (#219 – Cockpit zeigte den dümmsten Prozess)
    if _may_persist({"verified": False, "state": "unverified"}, exists=True):
        failures.append("ungeprüftes Lagebild überschreibt den Live-Befund")
    if _may_persist({"verified": True, "state": "absent"}, exists=True):
        failures.append("Prozess ohne Secrets (absent) überschreibt einen vorhandenen Befund")
    if not _may_persist({"verified": True, "state": "absent"}, exists=False):
        failures.append("Erstbefund `absent` wird nicht geschrieben (Datei bliebe leer)")
    if not _may_persist({"verified": True, "state": "live"}, exists=True):
        failures.append("live geprüfter Befund darf nicht schreiben")
    if not _may_persist({"verified": True, "state": "dead"}, exists=True):
        failures.append("live geprüfter Tod darf nicht schreiben (Kanaltod bliebe unsichtbar)")

    # --- Fall 7: Refresh-Token altert unbemerkt → Vorwarnung vor der Rotation
    stale_rot = (now - datetime.timedelta(days=REFRESH_CRITICAL_DAYS + 1)).isoformat()
    hooks, _ = mk(probe_map={"tok": ("live", "200")},
                  store={"access_token": "tok", "refresh_token": "r1", "app_id": "a",
                         "app_secret": "s", "refreshed_at": now.isoformat(),
                         "refresh_rotated_at": stale_rot})
    h = resolve(hooks=hooks, now=now)
    if h["severity"] != "red":
        failures.append("überalterter Refresh-Token (Rotation überfällig) wird nicht "
                        "vor dem Ausfall gemeldet")

    # --- Fall 8: kein Token, keine Quelle → rot, aber ohne Traceback
    hooks, _ = mk(probe_map={}, env={})
    h = resolve(hooks=hooks, now=now)
    if h["state"] not in ("absent", "dead") or h["severity"] != "red":
        failures.append("fehlende Konfiguration wird nicht sauber gemeldet")

    # --- Fall 9: offline-Modus liefert Token ohne Netz (Notbetrieb)
    hooks, _ = mk(probe_map={}, env={"PINTEREST_ACCESS_TOKEN": "irgendwas"})
    h = resolve(verify=False, allow_refresh=False, hooks=hooks, now=now)
    if h["token"] != "irgendwas":
        failures.append("--offline liefert keinen Token aus dem Bestand")

    # --- Kein Secret-Material in Fingerabdruck/Zustand
    fp = fingerprint("pina_supergeheim_1234567890")
    if "pina_" in fp or len(fp) != 12:
        failures.append("Fingerabdruck verrät Token-Material")
    if "geheim" in json.dumps({k: v for k, v in h.items() if k != "token"}):
        failures.append("Token-Material im Lagebild")
    if _redact("Fehler mit pinr_abc123456789", "pinr_abc123456789") != "Fehler mit ***":
        failures.append("Redaktion von Secret-Material greift nicht")

    # --- Ampel-Logik konsistent
    if _severity({"state": "live", "auto_renew_armed": True, "refresh_days_left": 55}) != "green":
        failures.append("gesunder Kanal ist nicht grün")
    if _severity({"state": "dead", "auto_renew_armed": True, "renewable": True}) != "red":
        failures.append("toter Kanal ist nicht rot")

    if failures:
        print("❌ PINTEREST-TOKEN-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ PINTEREST-TOKEN-SELFTEST bestanden (Failover, Bootstrap, proaktive "
          "Erneuerung nur durch die Wache, 403-Scope-Gegenprobe, Lagebild-Schreibrecht, "
          "Rotations-Vorwarnung, Störungs-Toleranz, Secret-Dichtigkeit).")
    return 0


# ------------------------------------------------------------------------- CLI

def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    offline = "--offline" in argv
    h = resolve(verify=not offline, allow_refresh=not offline,
                force_refresh="--refresh" in argv)
    # Die Token-Wache ist die einzige Instanz, deren Lagebild auch „absent"
    # sagen darf – sie hat alle Secrets und hat live geprüft.
    public = save_state(h, force=("--refresh" in argv and not offline))
    if "--json" in argv:
        print(json.dumps(public, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(describe(h))
    if os.environ.get("GITHUB_OUTPUT"):
        try:
            with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as f:
                f.write(f"state={h.get('state')}\n")
                f.write(f"severity={h.get('severity')}\n")
                f.write(f"source={h.get('source') or 'none'}\n")
                f.write(f"renewable={'true' if h.get('renewable') else 'false'}\n")
                f.write(f"auto_renew={'true' if h.get('auto_renew_armed') else 'false'}\n")
        except OSError:
            pass
    return 0 if h.get("severity") == "green" else (0 if h.get("state") == "live"
                                                   and "--strict" not in argv else 1)


if __name__ == "__main__":
    sys.exit(main())
