#!/usr/bin/env python3
# ============================================================
#  SOCIAL-PREFLIGHT – Verifikations-Lauf für Kanal-Zugänge
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 29.09.2026): Bevor ein Kanal scharf geschaltet
#  wird, muss beweisbar sein, dass sein Zugang WIRKLICH funktioniert –
#  und zwar OHNE etwas zu veröffentlichen.
#
#  WAS DER LAUF TUT
#    Für jeden in data/social/channels.yaml aktivierten Kanal:
#      1 Secrets/Variablen vorhanden?      → sonst „Standby"
#      2 NUR-LESEND gegen die echte API:   „Wer bin ich?"
#         Mastodon  GET /api/v1/accounts/verify_credentials
#         Bluesky   com.atproto.server.createSession
#         LinkedIn  GET /v2/userinfo  (Fallback /v2/me)
#         X         GET /2/users/me   (OAuth 1.0a)
#         Threads   GET /v1.0/me
#         Facebook  GET /v20.0/<page_id>
#         Instagram GET /v20.0/<account_id>
#         Pinterest GET /v5/user_account (+ Board-Probe)
#         Telegram  getMe + getChat(<chat_id>)
#         Reddit    OAuth-Login + GET /api/v1/me
#      3 Klartext-Befund + nächster Handgriff bei Fehlern
#      4 Cockpit SOCIAL-PREFLIGHT-STATUS.md
#
#  ES WIRD NICHTS GEPOSTET. Kein Schreibzugriff, keine Statusänderung,
#  keine Datei in data/social/ wird angefasst.
#
#  BETRIEBSRUHE (Dauervorgabe): Fehlendes Secret = Standby = KEIN Fehler.
#  Nur ein KONFIGURIERTER Kanal, dessen Token nicht trägt, ist ein Befund
#  (Exit-Code 1 nur mit --strict).
#
#  KOSTEN: 0 € – ausschließlich Standardbibliothek und Gratis-API-Aufrufe.
#
#  Aufruf:
#    python3 scripts/social_preflight.py                 # alle Kanäle
#    python3 scripts/social_preflight.py --kanal bluesky # einzeln
#    python3 scripts/social_preflight.py --json
#    python3 scripts/social_preflight.py --strict        # CI-Wache
#    python3 scripts/social_preflight.py --selftest
#
#  Anleitung: docs/RUNBUCH-SOCIAL-SECRETS.md
# ============================================================
from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import sys
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import social_channels as sch  # noqa: E402

REPORT_PATH = os.path.join(BLOG_DIR, "SOCIAL-PREFLIGHT-STATUS.md")
RUNBUCH = "docs/RUNBUCH-SOCIAL-SECRETS.md"

OK, STANDBY, FAIL, UNKNOWN = "ok", "standby", "fail", "unbekannt"

SYMBOL = {OK: "✅", STANDBY: "⚪", FAIL: "❌", UNKNOWN: "❓"}

# Reihenfolge = empfohlene Einrichtungs-Reihenfolge (Aufwand/Nutzen)
SETUP_ORDER = ["bluesky", "telegram", "mastodon", "linkedin", "facebook",
               "instagram", "threads", "x", "pinterest", "reddit", "youtube"]

# Kanäle, die NICHT in channels.yaml stehen, weil sie kein Textkanal sind.
# YouTube gehört der Shorts-Schmiede (data/social/video.yaml) – geprüft
# wird er trotzdem hier, damit es EINEN Ort für Zugangs-Wahrheit gibt.
VIRTUELLE_KANAELE = {
    "youtube": {
        "label": "YouTube Shorts",
        "enabled": True,
        "secrets": ["YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"],
        "vars": ["YOUTUBE_CHANNEL_ID"],
    },
}

# Kurzer nächster Handgriff, wenn ein Kanal im Standby steht.
SETUP_HINT = {
    "mastodon": "Einstellungen → Entwicklung → Neue Anwendung, Scopes write:statuses + write:media.",
    "bluesky": "Einstellungen → Datenschutz und Sicherheit → App-Passwörter (NICHT das Kontopasswort).",
    "linkedin": "developer.linkedin.com → App → Products „Share on LinkedIn\" + „Sign In with OpenID Connect\".",
    "x": "developer.x.com → Projekt → App → User authentication: Read and write, dann Keys + Access-Token.",
    "threads": "developers.facebook.com → App mit Produkt „Threads API\", Long-Lived-Token holen.",
    "facebook": "Graph-API-Explorer → Seiten-Token (pages_manage_posts) → in einen nicht ablaufenden Token tauschen.",
    "instagram": "Business-/Creator-Konto mit Facebook-Seite verknüpfen, dann instagram_content_publish.",
    "pinterest": "Pinterest-Developer-App, Token über den Broker: python3 scripts/pinterest_token.py.",
    "telegram": "@BotFather → /newbot → Token; Bot als Administrator in den Kanal aufnehmen.",
    "youtube": ("console.cloud.google.com → Projekt → YouTube Data API v3 aktivieren → "
                "OAuth-Client (Desktop) → einmalig Refresh-Token holen "
                "(docs/ANLEITUNG-SHORTS-SCHMIEDE.md, Abschnitt 4)."),
    "reddit": "reddit.com/prefs/apps → „script\"-App anlegen (Client-ID + Secret + Konto-Login).",
}


# --------------------------------------------------------------- Hilfsmittel
def _env(key: str) -> str:
    return (os.environ.get(key) or "").strip()


def _missing(keys) -> list[str]:
    return [k for k in (keys or []) if not _env(k)]


def _short(err: str, limit: int = 160) -> str:
    err = " ".join(str(err or "").split())
    return err[:limit] + ("…" if len(err) > limit else "")


def _result(status: str, detail: str = "", identity: str = "", hinweis: str = "") -> dict:
    # Eine Netzwerkstörung ist KEIN Zugangsfehler. Sie darf niemanden dazu
    # verleiten, ein funktionierendes Token wegzuwerfen.
    if status == FAIL and _ist_netzfehler(detail):
        return {"status": UNKNOWN, "detail": f"Netzwerk nicht erreichbar ({detail})",
                "identity": identity,
                "hinweis": "Kein Zugangsproblem – Prüfung wiederholen, sobald die Verbindung steht."}
    return {"status": status, "detail": detail, "identity": identity, "hinweis": hinweis}


# Muster, an denen eine Transport-/Netzstörung erkennbar ist (Runner ohne
# Netz, Proxy, DNS, TLS-Abbruch) – im Gegensatz zu einer echten Abweisung.
_NETZ_MUSTER = ("urlopen error", "ssl", "timed out", "timeout", "connection reset",
                "name or service not known", "temporary failure in name resolution",
                "network is unreachable", "certificate")


def _ist_netzfehler(text: str) -> bool:
    t = str(text or "").lower()
    if t.startswith("http "):        # echte API-Antwort, kein Transportproblem
        return False
    return any(m in t for m in _NETZ_MUSTER)


def _http_hint(status_code: int, channel_id: str) -> str:
    """Übersetzt HTTP-Codes in einen konkreten nächsten Handgriff."""
    if status_code in (401, 403):
        return ("Token abgelaufen oder Berechtigungen (Scopes) fehlen – "
                f"Zugang neu erzeugen: {SETUP_HINT.get(channel_id, '')}").strip()
    if status_code == 404:
        return "ID stimmt nicht (Seiten-/Konto-/Board-/Chat-ID prüfen)."
    if status_code == 429:
        return "Rate-Limit erreicht – später erneut prüfen, kein Konfigurationsfehler."
    if status_code >= 500:
        return "Störung beim Anbieter – Prüfung später wiederholen."
    return ""


# ----------------------------------------------------------------- Prüfungen
# Jede Prüfung ist NUR-LESEND und gibt ein _result() zurück.

def _check_mastodon(ch: dict, cfg: dict) -> dict:
    instance = (_env("MASTODON_INSTANCE") or "https://mastodon.social").rstrip("/")
    if not instance.startswith("http"):
        instance = "https://" + instance
    status, data, err = sch.http_json(
        f"{instance}/api/v1/accounts/verify_credentials",
        headers={"Authorization": f"Bearer {_env('MASTODON_ACCESS_TOKEN')}"},
        method="GET", retries=2)
    if err or not isinstance(data, dict):
        return _result(FAIL, _short(err or "unerwartete Antwort"), hinweis=_http_hint(status, "mastodon"))
    return _result(OK, f"Instanz {instance}", identity="@" + str(data.get("acct") or data.get("username") or "?"))


def _check_bluesky(ch: dict, cfg: dict) -> dict:
    pds = (_env("BLUESKY_PDS") or "https://bsky.social").rstrip("/")
    if not pds.startswith("http"):
        pds = "https://" + pds
    body = json.dumps({"identifier": _env("BLUESKY_IDENTIFIER"),
                       "password": _env("BLUESKY_APP_PASSWORD")}).encode("utf-8")
    status, data, err = sch.http_json(
        f"{pds}/xrpc/com.atproto.server.createSession",
        data=body, headers={"Content-Type": "application/json"}, method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("accessJwt"):
        hint = _http_hint(status, "bluesky")
        if status == 401:
            hint = ("Kennung oder App-Passwort falsch. Kennung ist der volle Handle "
                    "(z. B. franksfinanzcheck.de), das Passwort ein APP-Passwort.")
        return _result(FAIL, _short(err or "keine Sitzung erhalten"), hinweis=hint)
    return _result(OK, f"PDS {pds}", identity="@" + str(data.get("handle") or "?"))


def _check_linkedin(ch: dict, cfg: dict) -> dict:
    token = _env("LINKEDIN_ACCESS_TOKEN")
    headers = {"Authorization": f"Bearer {token}", "X-Restli-Protocol-Version": "2.0.0"}
    status, data, err = sch.http_json("https://api.linkedin.com/v2/userinfo",
                                      headers=headers, method="GET", retries=2)
    if err or not isinstance(data, dict):
        status2, data2, err2 = sch.http_json("https://api.linkedin.com/v2/me",
                                             headers=headers, method="GET", retries=2)
        if err2 or not isinstance(data2, dict):
            return _result(FAIL, _short(err or err2), hinweis=_http_hint(status or status2, "linkedin"))
        data, status = data2, status2
    person = _env("LINKEDIN_PERSON_URN")
    org = _env("LINKEDIN_ORG_URN")
    if not person and not org:
        sub = data.get("sub") or data.get("id")
        return _result(FAIL, "Token gültig, aber kein Absender gesetzt",
                       identity=str(data.get("name") or sub or "?"),
                       hinweis=(f"Variable LINKEDIN_PERSON_URN setzen – laut API: urn:li:person:{sub}"
                                if sub else "LINKEDIN_PERSON_URN oder LINKEDIN_ORG_URN setzen."))
    absender = org or person
    warn = ""
    if not str(absender).startswith("urn:li:"):
        warn = "Absender muss das Format urn:li:person:XXXX bzw. urn:li:organization:123 haben."
    return _result(FAIL if warn else OK,
                   f"Absender {absender}",
                   identity=str(data.get("name") or data.get("sub") or data.get("id") or "?"),
                   hinweis=warn or "Token verfällt nach ~60 Tagen – Erneuerung einplanen.")


def _check_x(ch: dict, cfg: dict) -> dict:
    try:
        from social_channels.x import oauth1_header
    except Exception as exc:  # noqa: BLE001
        return _result(UNKNOWN, f"Adapter nicht ladbar ({_short(exc)})")
    url = "https://api.twitter.com/2/users/me"
    header = oauth1_header("GET", url, _env("X_API_KEY"), _env("X_API_SECRET"),
                           _env("X_ACCESS_TOKEN"), _env("X_ACCESS_SECRET"))
    status, data, err = sch.http_json(url, headers={"Authorization": header},
                                      method="GET", retries=2)
    if err or not isinstance(data, dict) or not data.get("data"):
        hint = _http_hint(status, "x")
        if status in (401, 403):
            hint = ("Schlüssel passen nicht zusammen oder die App steht auf „Read\". "
                    "In den App-Einstellungen „Read and write\" setzen und danach die "
                    "Access-Token NEU erzeugen – alte Token behalten sonst Nur-Lese-Rechte.")
        return _result(FAIL, _short(err or "unerwartete Antwort"), hinweis=hint)
    return _result(OK, "OAuth 1.0a trägt", identity="@" + str((data.get("data") or {}).get("username") or "?"))


def _check_threads(ch: dict, cfg: dict) -> dict:
    token = _env("THREADS_ACCESS_TOKEN")
    status, data, err = sch.http_json(
        "https://graph.threads.net/v1.0/me?fields=id,username&access_token="
        + urllib.parse.quote(token), method="GET", retries=2)
    if err or not isinstance(data, dict) or not data.get("id"):
        return _result(FAIL, _short(err or "unerwartete Antwort"), hinweis=_http_hint(status, "threads"))
    uid, konf = str(data.get("id")), _env("THREADS_USER_ID")
    if konf and konf != uid:
        return _result(FAIL, f"THREADS_USER_ID={konf}, Token gehört zu {uid}",
                       identity="@" + str(data.get("username") or "?"),
                       hinweis=f"Variable THREADS_USER_ID auf {uid} korrigieren.")
    return _result(OK, f"User-ID {uid}", identity="@" + str(data.get("username") or "?"),
                   hinweis="" if konf else f"Variable THREADS_USER_ID={uid} nachtragen (spart einen API-Aufruf).")


def _check_facebook(ch: dict, cfg: dict) -> dict:
    token, page = _env("FACEBOOK_PAGE_TOKEN"), _env("FACEBOOK_PAGE_ID")
    if not page:
        return _result(FAIL, "FACEBOOK_PAGE_ID fehlt",
                       hinweis="Variable FACEBOOK_PAGE_ID setzen (Seite → Info → Seiten-ID).")
    status, data, err = sch.http_json(
        f"https://graph.facebook.com/v20.0/{urllib.parse.quote(page)}"
        f"?fields=name,link&access_token={urllib.parse.quote(token)}", method="GET", retries=2)
    if err or not isinstance(data, dict) or not data.get("id"):
        return _result(FAIL, _short(err or "unerwartete Antwort"), hinweis=_http_hint(status, "facebook"))
    return _result(OK, f"Seiten-ID {page}", identity=str(data.get("name") or "?"),
                   hinweis="Prüfen, dass es ein SEITEN-Token ist (kein Nutzer-Token) – sonst läuft er ab.")


def _check_instagram(ch: dict, cfg: dict) -> dict:
    token, acc = _env("INSTAGRAM_ACCESS_TOKEN"), _env("INSTAGRAM_ACCOUNT_ID")
    if not acc:
        return _result(FAIL, "INSTAGRAM_ACCOUNT_ID fehlt",
                       hinweis="Variable INSTAGRAM_ACCOUNT_ID setzen (Graph: /<page-id>?fields=instagram_business_account).")
    status, data, err = sch.http_json(
        f"https://graph.facebook.com/v20.0/{urllib.parse.quote(acc)}"
        f"?fields=username,media_count&access_token={urllib.parse.quote(token)}",
        method="GET", retries=2)
    if err or not isinstance(data, dict) or not data.get("id"):
        return _result(FAIL, _short(err or "unerwartete Antwort"), hinweis=_http_hint(status, "instagram"))
    return _result(OK, f"Konto-ID {acc}", identity="@" + str(data.get("username") or "?"),
                   hinweis="Instagram braucht IMMER ein Bild – der Autopilot liefert die 4:5-Variante.")


def _check_pinterest(ch: dict, cfg: dict) -> dict:
    try:
        import pinterest_token
        token = pinterest_token.get_token() or ""
    except Exception as exc:  # noqa: BLE001
        return _result(FAIL, f"Token-Broker nicht nutzbar ({_short(exc)})",
                       hinweis="python3 scripts/pinterest_token.py ausführen und Secret PINTEREST_TOKEN_KEY prüfen.")
    if not token:
        return _result(STANDBY, "kein lebender Token", hinweis=SETUP_HINT["pinterest"])
    headers = {"Authorization": f"Bearer {token}"}
    status, data, err = sch.http_json("https://api.pinterest.com/v5/user_account",
                                      headers=headers, method="GET", retries=2)
    if err or not isinstance(data, dict):
        return _result(FAIL, _short(err or "unerwartete Antwort"), hinweis=_http_hint(status, "pinterest"))
    ident = "@" + str(data.get("username") or "?")
    board = _env("PINTEREST_BOARD_ID")
    if board:
        bstatus, bdata, berr = sch.http_json(
            f"https://api.pinterest.com/v5/boards/{urllib.parse.quote(board)}",
            headers=headers, method="GET", retries=2)
        if berr or not isinstance(bdata, dict):
            return _result(FAIL, f"Board {board} nicht erreichbar", identity=ident,
                           hinweis=_http_hint(bstatus, "pinterest") or "Board-ID prüfen.")
        return _result(OK, f"Board „{bdata.get('name') or board}\"", identity=ident)
    return _result(OK, "Konto erreichbar, Board wird dynamisch aufgelöst", identity=ident)


def _check_telegram(ch: dict, cfg: dict) -> dict:
    token, chat = _env("TELEGRAM_BOT_TOKEN"), _env("TELEGRAM_CHAT_ID")
    status, data, err = sch.http_json(f"https://api.telegram.org/bot{token}/getMe",
                                      method="GET", retries=2)
    if err or not isinstance(data, dict) or not data.get("ok"):
        return _result(FAIL, _short(err or "Bot-Token ungültig"),
                       hinweis="Token bei @BotFather mit /mybots prüfen oder neu erzeugen.")
    bot = "@" + str(((data.get("result") or {}).get("username")) or "?")
    if not chat:
        return _result(FAIL, "TELEGRAM_CHAT_ID fehlt", identity=bot,
                       hinweis="Variable TELEGRAM_CHAT_ID setzen (z. B. @franksfinanzcheck oder -100…).")
    cstatus, cdata, cerr = sch.http_json(
        f"https://api.telegram.org/bot{token}/getChat?chat_id={urllib.parse.quote(chat)}",
        method="GET", retries=2)
    if cerr or not isinstance(cdata, dict) or not cdata.get("ok"):
        return _result(FAIL, f"Kanal {chat} nicht erreichbar", identity=bot,
                       hinweis="Den Bot als ADMINISTRATOR in den Kanal aufnehmen (Recht „Nachrichten posten\").")
    titel = (cdata.get("result") or {}).get("title") or chat
    return _result(OK, f"Kanal „{titel}\"", identity=bot)


def _check_youtube(ch: dict, cfg: dict) -> dict:
    """Prüft den Shorts-Zugang: Refresh-Token tauschen + Kanal lesen."""
    status, data, err = sch.http_json(
        "https://oauth2.googleapis.com/token",
        data=sch.form_encode({"client_id": _env("YOUTUBE_CLIENT_ID"),
                              "client_secret": _env("YOUTUBE_CLIENT_SECRET"),
                              "refresh_token": _env("YOUTUBE_REFRESH_TOKEN"),
                              "grant_type": "refresh_token"}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("access_token"):
        hint = _http_hint(status, "youtube")
        if status in (400, 401):
            hint = ("Refresh-Token ungültig oder widerrufen. Ein Token aus einer App im "
                    "Test-Modus verfällt nach 7 Tagen – App auf „In Produktion\" setzen "
                    "und Token neu holen.")
        return _result(FAIL, _short(err or "kein Access-Token"), hinweis=hint)
    token = data["access_token"]
    kstatus, kdata, kerr = sch.http_json(
        "https://www.googleapis.com/youtube/v3/channels?part=snippet&mine=true",
        headers={"Authorization": f"Bearer {token}"}, method="GET", retries=2)
    if kerr or not isinstance(kdata, dict) or not (kdata.get("items") or []):
        return _result(FAIL, _short(kerr or "kein Kanal am Konto"),
                       hinweis=_http_hint(kstatus, "youtube")
                       or "Das Google-Konto hat keinen YouTube-Kanal – erst einen anlegen.")
    kanal = (kdata["items"][0].get("snippet") or {}).get("title") or "?"
    kid = kdata["items"][0].get("id") or ""
    konf = _env("YOUTUBE_CHANNEL_ID")
    if konf and kid and konf != kid:
        return _result(FAIL, f"YOUTUBE_CHANNEL_ID={konf}, Token gehört zu {kid}",
                       identity=kanal, hinweis=f"Variable auf {kid} korrigieren.")
    return _result(OK, f"Kanal-ID {kid}", identity=kanal,
                   hinweis="" if konf else f"Variable YOUTUBE_CHANNEL_ID={kid} nachtragen.")


def _check_reddit(ch: dict, cfg: dict) -> dict:
    user = _env("REDDIT_USERNAME")
    body = sch.form_encode({"grant_type": "password", "username": user,
                            "password": _env("REDDIT_PASSWORD")})
    import base64
    basic = base64.b64encode(
        f"{_env('REDDIT_CLIENT_ID')}:{_env('REDDIT_CLIENT_SECRET')}".encode("utf-8")).decode("ascii")
    status, data, err = sch.http_json(
        "https://www.reddit.com/api/v1/access_token", data=body,
        headers={"Authorization": f"Basic {basic}",
                 "Content-Type": "application/x-www-form-urlencoded"},
        method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("access_token"):
        hint = _http_hint(status, "reddit")
        if status in (401, 400):
            hint = ("Client-ID/Secret oder Login falsch. Bei aktivierter Zwei-Faktor-"
                    "Anmeldung funktioniert der Passwort-Fluss NICHT.")
        return _result(FAIL, _short(err or "kein Token erhalten"), hinweis=hint)
    mstatus, mdata, merr = sch.http_json(
        "https://oauth.reddit.com/api/v1/me",
        headers={"Authorization": f"bearer {data['access_token']}",
                 "User-Agent": sch.USER_AGENT}, method="GET", retries=2)
    if merr or not isinstance(mdata, dict):
        return _result(FAIL, _short(merr), hinweis=_http_hint(mstatus, "reddit"))
    ziel = _env("REDDIT_SUBREDDIT") or f"u_{user}"
    return _result(OK, f"Ziel r/{ziel}", identity="u/" + str(mdata.get("name") or "?"),
                   hinweis="Fremde Subreddits nur mit deren Regeln – Selbstpromo-Sperren sind hart.")


CHECKS = {
    "mastodon": _check_mastodon,
    "bluesky": _check_bluesky,
    "linkedin": _check_linkedin,
    "x": _check_x,
    "threads": _check_threads,
    "facebook": _check_facebook,
    "instagram": _check_instagram,
    "pinterest": _check_pinterest,
    "telegram": _check_telegram,
    "reddit": _check_reddit,
    "youtube": _check_youtube,
}


# ------------------------------------------------------------------- Ablauf
def pruefe_kanal(cid: str, ch: dict, cfg: dict, offline: bool = False) -> dict:
    """Prüft EINEN Kanal. Wirft nie – ein Fehler wird zum Befund."""
    eintrag = {
        "kanal": cid,
        "label": (ch or {}).get("label") or cid,
        "enabled": bool((ch or {}).get("enabled")),
        "secrets": list((ch or {}).get("secrets") or []),
        "vars": list((ch or {}).get("vars") or []),
        "fehlende_secrets": [],
        "fehlende_vars": [],
        "status": UNKNOWN,
        "detail": "",
        "identity": "",
        "hinweis": "",
    }
    if not eintrag["enabled"]:
        eintrag.update(status=STANDBY, detail="in channels.yaml deaktiviert")
        return eintrag
    if cid not in VIRTUELLE_KANAELE and sch.adapter_class(cid) is None:
        eintrag.update(status=FAIL, detail="Adapter nicht ladbar",
                       hinweis=f"scripts/social_channels/{cid}.py prüfen.")
        return eintrag

    eintrag["fehlende_secrets"] = _missing(eintrag["secrets"])
    eintrag["fehlende_vars"] = _missing(eintrag["vars"])

    # Pinterest holt seinen Token über den Broker – fehlendes Secret ist dort
    # kein K.-o.-Kriterium, das entscheidet die Kanal-Prüfung selbst.
    if eintrag["fehlende_secrets"] and cid != "pinterest":
        eintrag.update(status=STANDBY,
                       detail="fehlt: " + ", ".join(eintrag["fehlende_secrets"]),
                       hinweis=SETUP_HINT.get(cid, ""))
        return eintrag

    if offline:
        eintrag.update(status=UNKNOWN, detail="Zugangsdaten vollständig (kein Netz-Test angefordert)")
        return eintrag

    fn = CHECKS.get(cid)
    if not fn:
        eintrag.update(status=UNKNOWN, detail="keine Verifikation für diesen Kanal hinterlegt")
        return eintrag
    try:
        eintrag.update(fn(ch, cfg))
    except Exception as exc:  # noqa: BLE001 – Preflight darf nie abstürzen
        eintrag.update(status=FAIL, detail=f"Prüfung abgebrochen: {_short(exc)}")
    return eintrag


def preflight(kanaele: list[str] | None = None, offline: bool = False) -> dict:
    cfg = sch.load_config()
    channels = dict(sch.channel_map(cfg))
    if not channels:
        return {"zeit": _jetzt(), "kanaele": [], "fehler": "channels.yaml fehlt oder ist leer"}
    for cid, ch in VIRTUELLE_KANAELE.items():
        channels.setdefault(cid, dict(ch))
    ids = [c for c in SETUP_ORDER if c in channels] + \
          [c for c in channels if c not in SETUP_ORDER]
    if kanaele:
        unbekannt = [k for k in kanaele if k not in channels]
        ids = [c for c in ids if c in kanaele]
        if unbekannt:
            print(f"⚠ Unbekannte Kanäle übersprungen: {', '.join(unbekannt)}")
    ergebnisse = [pruefe_kanal(cid, channels.get(cid) or {}, cfg, offline=offline) for cid in ids]
    return {"zeit": _jetzt(), "kanaele": ergebnisse, "fehler": ""}


def _jetzt() -> str:
    try:
        from zoneinfo import ZoneInfo
        return _dt.datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M Uhr")
    except Exception:  # noqa: BLE001
        return _dt.datetime.now().strftime("%d.%m.%Y %H:%M Uhr")


def zaehle(bericht: dict) -> dict:
    z = {OK: 0, STANDBY: 0, FAIL: 0, UNKNOWN: 0}
    for e in bericht.get("kanaele") or []:
        z[e["status"]] = z.get(e["status"], 0) + 1
    return z


# ------------------------------------------------------------------ Ausgabe
def konsole(bericht: dict) -> None:
    print("=" * 64)
    print("  SOCIAL-PREFLIGHT – Verifikation der Kanal-Zugänge")
    print(f"  {bericht['zeit']} · nur lesend, es wird NICHTS veröffentlicht")
    print("=" * 64)
    if bericht.get("fehler"):
        print(f"⚠ {bericht['fehler']}")
        return
    for e in bericht["kanaele"]:
        kopf = f"{SYMBOL.get(e['status'], '·')} {e['label']:<18} {e['status'].upper()}"
        if e["identity"]:
            kopf += f"  als {e['identity']}"
        print(kopf)
        if e["detail"]:
            print(f"     {e['detail']}")
        if e["fehlende_vars"] and e["status"] != STANDBY:
            print(f"     Variablen nicht gesetzt (Standardwert greift): "
                  f"{', '.join(e['fehlende_vars'])}")
        if e["hinweis"]:
            print(f"     → {e['hinweis']}")
    z = zaehle(bericht)
    print("-" * 64)
    print(f"  Sendebereit {z[OK]} · Standby {z[STANDBY]} · Befund {z[FAIL]} · offen {z[UNKNOWN]}")
    print(f"  Runbuch: {RUNBUCH}")


def markdown(bericht: dict) -> str:
    z = zaehle(bericht)
    zeilen = [
        "# 🛰️ Social-Preflight – Status der Kanal-Zugänge",
        "",
        f"**Stand:** {bericht['zeit']} · **Prüfung:** nur lesend "
        "(„Wer bin ich?\"-Aufruf je Kanal, es wird nichts veröffentlicht)",
        "",
        f"**Sendebereit {z[OK]}** · Standby {z[STANDBY]} · Befund {z[FAIL]} · offen {z[UNKNOWN]}",
        "",
        "| | Kanal | Status | Konto | Detail |",
        "|---|---|---|---|---|",
    ]
    for e in bericht.get("kanaele") or []:
        zeilen.append(f"| {SYMBOL.get(e['status'], '·')} | {e['label']} | {e['status']} | "
                      f"{e['identity'] or '–'} | {e['detail'] or '–'} |")
    offen = [e for e in (bericht.get("kanaele") or []) if e["status"] in (FAIL, STANDBY) and e["hinweis"]]
    if offen:
        zeilen += ["", "## Nächste Handgriffe", ""]
        for e in offen:
            zeilen.append(f"- **{e['label']}** ({e['status']}): {e['hinweis']}")
    zeilen += [
        "",
        "## Lesart",
        "",
        "- ✅ **ok** – Zugang verifiziert, der Autopilot sendet auf diesem Kanal.",
        "- ⚪ **standby** – Secret fehlt. Kein Fehler, kein Alarm; der Kanal ruht.",
        "- ❌ **befund** – Zugangsdaten hinterlegt, aber die API weist sie ab. Handgriff siehe oben.",
        "- ❓ **offen** – keine Netzprüfung möglich (Offline-Lauf oder unbekannter Kanal).",
        "",
        f"Einrichtung Schritt für Schritt: `{RUNBUCH}` · "
        "Kanal-Playbook: `data/social/channels.yaml`",
        "",
        "*Erzeugt von `scripts/social_preflight.py` – dieser Lauf verändert keine Inhalte.*",
    ]
    return "\n".join(zeilen) + "\n"


# ----------------------------------------------------------------- Selbsttest
def selftest() -> int:
    fehler = []
    cfg = sch.load_config()
    channels = dict(sch.channel_map(cfg))
    for cid, ch in VIRTUELLE_KANAELE.items():
        channels.setdefault(cid, dict(ch))
    if not channels:
        fehler.append("channels.yaml nicht lesbar")
    for cid in channels:
        if cid not in CHECKS:
            fehler.append(f"keine Verifikation für Kanal {cid} hinterlegt")
        if cid not in SETUP_HINT:
            fehler.append(f"kein Einrichtungs-Hinweis für Kanal {cid}")

    # Standby-Regel: ohne Secrets darf NIE eine Netzprüfung laufen.
    gesichert = dict(os.environ)
    try:
        for key in [k for ch in channels.values() for k in (ch.get("secrets") or [])]:
            os.environ.pop(key, None)
        bericht = preflight()
        for e in bericht["kanaele"]:
            if e["kanal"] == "pinterest":
                continue  # Broker-Sonderweg
            if e["status"] not in (STANDBY, UNKNOWN):
                fehler.append(f"{e['kanal']}: ohne Secret nicht im Standby ({e['status']})")
    finally:
        os.environ.clear()
        os.environ.update(gesichert)

    # Offline-Modus darf nie ins Netz gehen und nie FAIL melden.
    off = preflight(offline=True)
    for e in off["kanaele"]:
        if e["status"] == FAIL and e["detail"] != "Adapter nicht ladbar":
            fehler.append(f"{e['kanal']}: Offline-Lauf meldet Fehler ({e['detail']})")

    # Bericht ist erzeugbar
    if not markdown(off).startswith("# "):
        fehler.append("Markdown-Bericht fehlerhaft")
    # HTTP-Hinweise sind gefüllt
    if not _http_hint(401, "bluesky") or not _http_hint(404, "telegram"):
        fehler.append("HTTP-Hinweise unvollständig")
    # Netzstörung darf NIE als Zugangsfehler durchgehen (sonst wirft Frank
    # ein funktionierendes Token weg).
    if _result(FAIL, "<urlopen error TLS/SSL connection has been closed (EOF)>")["status"] != UNKNOWN:
        fehler.append("Netzwerkfehler wird faelschlich als Zugangsfehler gewertet")
    if _result(FAIL, "HTTP 401: invalid token")["status"] != FAIL:
        fehler.append("Echte Abweisung (401) wird nicht als Befund gewertet")

    if fehler:
        print("❌ Selbsttest fehlgeschlagen:")
        for f in fehler:
            print(f"   · {f}")
        return 1
    print(f"✅ Selbsttest bestanden ({len(channels)} Kanäle, Standby-Regel und Offline-Lauf sauber).")
    return 0


# ---------------------------------------------------------------------- CLI
def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        description="Verifiziert die Social-Zugänge – nur lesend, veröffentlicht nichts.")
    p.add_argument("--kanal", action="append", default=[],
                   help="nur diesen Kanal prüfen (mehrfach möglich)")
    p.add_argument("--offline", action="store_true",
                   help="keine API-Aufrufe, nur prüfen ob Secrets/Variablen gesetzt sind")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    p.add_argument("--bericht", default=REPORT_PATH,
                   help=f"Pfad des Markdown-Cockpits (Standard: {REPORT_PATH})")
    p.add_argument("--kein-bericht", action="store_true", help="kein Markdown schreiben")
    p.add_argument("--strict", action="store_true",
                   help="Exit 1, wenn ein konfigurierter Kanal seinen Zugang nicht bestätigt")
    p.add_argument("--selftest", action="store_true", help="Eigenprüfung des Skripts")
    a = p.parse_args(argv)

    if a.selftest:
        return selftest()

    bericht = preflight(kanaele=a.kanal or None, offline=a.offline)

    if a.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2))
    else:
        konsole(bericht)

    if not a.kein_bericht and not a.kanal:
        try:
            with open(a.bericht, "w", encoding="utf-8") as fh:
                fh.write(markdown(bericht))
            if not a.json:
                print(f"  Cockpit geschrieben: {os.path.relpath(a.bericht, BLOG_DIR)}")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠ Bericht nicht schreibbar: {exc}")

    z = zaehle(bericht)
    if a.strict and z[FAIL]:
        print(f"❌ {z[FAIL]} Kanal/Kanäle mit hinterlegten Zugangsdaten senden nicht.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
