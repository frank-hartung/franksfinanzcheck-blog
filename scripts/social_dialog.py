#!/usr/bin/env python3
# ============================================================
#  DIALOG-AUTOPILOT – Kommentare, Erwähnungen und Antworten
#  ------------------------------------------------------------
#  AUFTRAG (Frank, 29.09.2026): Der Blog soll auf allen Kanälen
#  automatisch zuhören, einordnen und antworten – Premium-Niveau
#  einer Profi-Agentur, passend zu einem FINANZBLOG.
#
#  ABLAUF EINES LAUFS
#    1 SAMMELN   neue Erwähnungen/Kommentare je Kanal (nur lesend)
#    2 EINORDNEN deterministische Signale + optionale Gratis-KI
#    3 BELEGEN   passenden EIGENEN Artikel als Beleg suchen
#    4 ENTWERFEN Vorlage je Klasse, danach optionale KI-Politur
#    5 PRÜFEN    hartes Gate (Beratungsanschein, Versprechen, PII, Links)
#    6 ZUSTELLEN auto senden ODER in die Freigabemappe legen
#    7 BERICHTEN Cockpit SOCIAL-DIALOG-STATUS.md
#
#  DIE SICHERHEITSARCHITEKTUR (warum das hier anders aussieht als
#  ein üblicher „Auto-Reply-Bot"):
#    · ABGESTUFTE AUTONOMIE. Nur risikoarme Klassen (Dank, Teilen)
#      antworten selbstständig. Alles, was nach individueller Beratung
#      riecht, wird FERTIG FORMULIERT und wartet auf ein Ja.
#    · FAIL-CLOSED. Unbekannte Klasse, fehlender Beleg, Gate-Verstoß,
#      LLM-Ausfall → Freigabemappe, niemals „trotzdem senden".
#    · KEINE ERFUNDENEN ZAHLEN. Eine Zahl darf nur in der Antwort
#      stehen, wenn sie im belegten eigenen Artikel vorkommt.
#    · KEINE ENDLOSSCHLEIFE. Cooldown je Person, Obergrenze je Lauf
#      und Tag, nie zweimal auf denselben Beitrag, nie auf sich selbst.
#    · SPAM UND TROLLE BEKOMMEN NICHTS. Jede Antwort wäre ein
#      Lebenszeichen und zieht mehr davon nach.
#
#  KOSTEN: 0 € – nur Gratis-APIs und Gratis-LLMs (Groq/Gemini).
#
#  Aufruf:
#    python3 scripts/social_dialog.py --run            # sammeln + zustellen
#    python3 scripts/social_dialog.py --run --dry-run  # sendet nichts
#    python3 scripts/social_dialog.py --freigeben m7f3a2
#    python3 scripts/social_dialog.py --freigeben alle
#    python3 scripts/social_dialog.py --verwerfen m7f3a2
#    python3 scripts/social_dialog.py --status
#    python3 scripts/social_dialog.py --selftest
#
#  Playbook: data/social/dialog.yaml
#  Anleitung: docs/ANLEITUNG-DIALOG-AUTOPILOT.md
# ============================================================
from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import json
import os
import re
import sys
import urllib.parse

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import social_channels as sch          # noqa: E402  (HTTP-Helfer, Standby-Regel)

CONFIG_PATH = os.path.join(BLOG_DIR, "data", "social", "dialog.yaml")
STATE_PATH = os.path.join(BLOG_DIR, "data", "social", "dialog_state.yaml")
REPORT_PATH = os.path.join(BLOG_DIR, "SOCIAL-DIALOG-STATUS.md")

AUTO, REVIEW, ESKALATION, MUTE = "auto", "review", "eskalation", "mute"
MODI = (AUTO, REVIEW, ESKALATION, MUTE)


# =============================================================== Grundlagen
def _yaml():
    import yaml
    return yaml


def load_config(path: str | None = None) -> dict:
    try:
        with open(path or CONFIG_PATH, encoding="utf-8") as fh:
            return _yaml().safe_load(fh) or {}
    except FileNotFoundError:
        return {}
    except Exception as exc:  # noqa: BLE001 – Konfiguration killt nie den Lauf
        print(f"⚠ dialog.yaml nicht lesbar ({exc}) – Dialog-Autopilot im Leerlauf.")
        return {}


def load_state() -> dict:
    try:
        with open(STATE_PATH, encoding="utf-8") as fh:
            data = _yaml().safe_load(fh) or {}
    except Exception:  # noqa: BLE001
        data = {}
    data.setdefault("version", 1)
    data.setdefault("gesehen", [])        # bereits verarbeitete Fremd-Beitrags-IDs
    data.setdefault("offen", [])          # Freigabemappe
    data.setdefault("verlauf", [])        # gesendete Antworten
    data.setdefault("chefsache", [])      # Eskalationen
    data.setdefault("telegram_offset", 0)
    return data


def save_state(state: dict) -> None:
    os.makedirs(os.path.dirname(STATE_PATH), exist_ok=True)
    # Der Zustand darf nicht unbegrenzt wachsen.
    state["gesehen"] = list(dict.fromkeys(state.get("gesehen") or []))[-4000:]
    state["verlauf"] = (state.get("verlauf") or [])[-1500:]
    state["chefsache"] = (state.get("chefsache") or [])[-300:]
    with open(STATE_PATH, "w", encoding="utf-8") as fh:
        _yaml().safe_dump(state, fh, allow_unicode=True, sort_keys=False, width=100)


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _berlin(dt: _dt.datetime | None = None) -> str:
    dt = dt or _now()
    try:
        from zoneinfo import ZoneInfo
        return dt.astimezone(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y %H:%M")
    except Exception:  # noqa: BLE001
        return dt.strftime("%d.%m.%Y %H:%M")


def _parse_ts(value) -> _dt.datetime:
    if isinstance(value, _dt.datetime):
        return value if value.tzinfo else value.replace(tzinfo=_dt.timezone.utc)
    try:
        return _dt.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except Exception:  # noqa: BLE001
        return _now()


def _kurz_id(channel: str, remote_id: str) -> str:
    h = hashlib.sha1(f"{channel}:{remote_id}".encode("utf-8")).hexdigest()
    return f"{channel[:2]}{h[:6]}"


def _strip_html(text: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", text or "")
    text = re.sub(r"</p>", "\n", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = (text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                .replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " "))
    return re.sub(r"[ \t]+", " ", text).strip()


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


# ============================================================ 1 · SAMMELN
# Jeder Sammler ist NUR LESEND und gibt eine Liste einheitlicher Beiträge
# zurück. Fehlt das Secret, liefert er (None, "Standby-Grund") – kein Fehler.

def _env(key: str) -> str:
    return (os.environ.get(key) or "").strip()


def _eintrag(channel: str, remote_id: str, author: str, text: str,
             created: str, permalink: str = "", ref: dict | None = None) -> dict:
    return {
        "id": _kurz_id(channel, remote_id),
        "kanal": channel,
        "remote_id": str(remote_id),
        "autor": author,
        "text": text,
        "erstellt": created,
        "permalink": permalink,
        "ref": ref or {},
    }


def fetch_mastodon(cfg_ch: dict, limit: int) -> tuple[list | None, str]:
    token = _env("MASTODON_ACCESS_TOKEN")
    if not token:
        return None, "MASTODON_ACCESS_TOKEN fehlt"
    instance = (_env("MASTODON_INSTANCE") or "https://mastodon.social").rstrip("/")
    if not instance.startswith("http"):
        instance = "https://" + instance
    status, data, err = sch.http_json(
        f"{instance}/api/v1/notifications?types[]=mention&limit={int(limit)}",
        headers={"Authorization": f"Bearer {token}"}, method="GET", retries=2)
    if err or not isinstance(data, list):
        return None, f"Abruf fehlgeschlagen ({err or status})"
    out = []
    for n in data:
        st = (n or {}).get("status") or {}
        acct = ((n or {}).get("account") or {}).get("acct") or "?"
        out.append(_eintrag("mastodon", st.get("id") or n.get("id"), f"@{acct}",
                            _strip_html(st.get("content") or ""),
                            st.get("created_at") or n.get("created_at") or "",
                            st.get("url") or "",
                            {"in_reply_to": st.get("id"), "visibility": st.get("visibility") or "public"}))
    return out, ""


def fetch_bluesky(cfg_ch: dict, limit: int) -> tuple[list | None, str]:
    ident, pw = _env("BLUESKY_IDENTIFIER"), _env("BLUESKY_APP_PASSWORD")
    if not ident or not pw:
        return None, "BLUESKY_IDENTIFIER/BLUESKY_APP_PASSWORD fehlt"
    pds = (_env("BLUESKY_PDS") or "https://bsky.social").rstrip("/")
    status, ses, err = sch.http_json(
        f"{pds}/xrpc/com.atproto.server.createSession",
        data=json.dumps({"identifier": ident, "password": pw}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST", retries=2)
    if err or not isinstance(ses, dict) or not ses.get("accessJwt"):
        return None, f"Anmeldung fehlgeschlagen ({err or status})"
    auth = {"Authorization": f"Bearer {ses['accessJwt']}"}
    status, data, err = sch.http_json(
        f"{pds}/xrpc/app.bsky.notification.listNotifications?limit={int(limit)}",
        headers=auth, method="GET", retries=2)
    if err or not isinstance(data, dict):
        return None, f"Abruf fehlgeschlagen ({err or status})"
    out = []
    for n in data.get("notifications") or []:
        if (n.get("reason") or "") not in ("mention", "reply"):
            continue
        rec = n.get("record") or {}
        handle = (n.get("author") or {}).get("handle") or "?"
        reply = rec.get("reply") or {}
        out.append(_eintrag("bluesky", n.get("uri") or "", f"@{handle}",
                            rec.get("text") or "", rec.get("createdAt") or "",
                            _bsky_link(handle, n.get("uri") or ""),
                            {"uri": n.get("uri"), "cid": n.get("cid"),
                             "root": (reply.get("root") or {"uri": n.get("uri"), "cid": n.get("cid")}),
                             "session_handle": ses.get("handle"), "pds": pds}))
    return out, ""


def _bsky_link(handle: str, uri: str) -> str:
    rkey = uri.rsplit("/", 1)[-1] if uri else ""
    return f"https://bsky.app/profile/{handle}/post/{rkey}" if rkey else ""


def fetch_telegram(cfg_ch: dict, limit: int, offset: int = 0) -> tuple[list | None, str]:
    token = _env("TELEGRAM_BOT_TOKEN")
    if not token:
        return None, "TELEGRAM_BOT_TOKEN fehlt"
    url = (f"https://api.telegram.org/bot{token}/getUpdates"
           f"?limit={int(limit)}&timeout=0&allowed_updates=%5B%22message%22%5D")
    if offset:
        url += f"&offset={int(offset)}"
    status, data, err = sch.http_json(url, method="GET", retries=2)
    if err or not isinstance(data, dict) or not data.get("ok"):
        return None, f"Abruf fehlgeschlagen ({err or status})"
    out, max_update = [], offset
    for upd in data.get("result") or []:
        max_update = max(max_update, int(upd.get("update_id") or 0))
        msg = upd.get("message") or {}
        text = msg.get("text") or msg.get("caption") or ""
        frm = msg.get("from") or {}
        if not text or frm.get("is_bot"):
            continue
        chat = msg.get("chat") or {}
        name = "@" + (frm.get("username") or (frm.get("first_name") or "?"))
        out.append(_eintrag("telegram", f"{chat.get('id')}:{msg.get('message_id')}", name,
                            text, _tg_ts(msg.get("date")), "",
                            {"chat_id": chat.get("id"), "message_id": msg.get("message_id"),
                             "next_offset": max_update + 1}))
    return out, ""


def _tg_ts(unix) -> str:
    try:
        return _dt.datetime.fromtimestamp(int(unix), _dt.timezone.utc).isoformat()
    except Exception:  # noqa: BLE001
        return _now().isoformat()


def fetch_youtube(cfg_ch: dict, limit: int) -> tuple[list | None, str]:
    token = _youtube_token()
    if not token:
        return None, "kein YouTube-Zugang (YOUTUBE_REFRESH_TOKEN u. a. fehlen)"
    status, data, err = sch.http_json(
        "https://www.googleapis.com/youtube/v3/commentThreads"
        f"?part=snippet&allThreadsRelatedToChannelId={urllib.parse.quote(_env('YOUTUBE_CHANNEL_ID'))}"
        f"&maxResults={min(int(limit), 50)}&order=time&textFormat=plainText"
        if _env("YOUTUBE_CHANNEL_ID") else
        "https://www.googleapis.com/youtube/v3/commentThreads"
        f"?part=snippet&maxResults={min(int(limit), 50)}&order=time&textFormat=plainText&mine=true",
        headers={"Authorization": f"Bearer {token}"}, method="GET", retries=2)
    if err or not isinstance(data, dict):
        return None, f"Abruf fehlgeschlagen ({err or status})"
    out = []
    for t in data.get("items") or []:
        top = ((t.get("snippet") or {}).get("topLevelComment") or {})
        sn = top.get("snippet") or {}
        out.append(_eintrag("youtube", top.get("id") or t.get("id"),
                            sn.get("authorDisplayName") or "?",
                            sn.get("textOriginal") or "",
                            sn.get("publishedAt") or "",
                            f"https://www.youtube.com/watch?v={sn.get('videoId')}"
                            f"&lc={top.get('id')}" if sn.get("videoId") else "",
                            {"parent_id": top.get("id"),
                             "author_channel": (sn.get("authorChannelId") or {}).get("value", "")}))
    return out, ""


def _youtube_token() -> str:
    """Holt ein frisches Access-Token aus dem Refresh-Token (Gratis, OAuth2)."""
    refresh = _env("YOUTUBE_REFRESH_TOKEN")
    cid, secret = _env("YOUTUBE_CLIENT_ID"), _env("YOUTUBE_CLIENT_SECRET")
    if not (refresh and cid and secret):
        return ""
    status, data, err = sch.http_json(
        "https://oauth2.googleapis.com/token",
        data=sch.form_encode({"client_id": cid, "client_secret": secret,
                              "refresh_token": refresh, "grant_type": "refresh_token"}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST", retries=2)
    if err or not isinstance(data, dict):
        return ""
    return str(data.get("access_token") or "")


def _graph_comments(kind: str, obj_env: str, token_env: str, limit: int) -> tuple[list | None, str]:
    """Kommentare unter eigenen Facebook-/Instagram-Beiträgen (Graph API)."""
    token, obj = _env(token_env), _env(obj_env)
    if not token:
        return None, f"{token_env} fehlt"
    if not obj:
        return None, f"{obj_env} fehlt"
    status, media, err = sch.http_json(
        f"https://graph.facebook.com/v20.0/{urllib.parse.quote(obj)}/"
        f"{'media' if kind == 'instagram' else 'posts'}?limit=8"
        f"&access_token={urllib.parse.quote(token)}", method="GET", retries=2)
    if err or not isinstance(media, dict):
        return None, f"Beiträge nicht lesbar ({err or status})"
    out = []
    for post in (media.get("data") or [])[:8]:
        pid = post.get("id")
        if not pid:
            continue
        cstatus, cdata, cerr = sch.http_json(
            f"https://graph.facebook.com/v20.0/{pid}/comments"
            f"?limit={min(int(limit), 25)}&order=reverse_chronological"
            f"&fields=id,message,text,from,username,timestamp"
            f"&access_token={urllib.parse.quote(token)}", method="GET", retries=2)
        if cerr or not isinstance(cdata, dict):
            continue
        for c in cdata.get("data") or []:
            autor = c.get("username") or ((c.get("from") or {}).get("name")) or "?"
            out.append(_eintrag(kind, c.get("id") or "", autor,
                                c.get("message") or c.get("text") or "",
                                c.get("timestamp") or "", "",
                                {"comment_id": c.get("id"), "post_id": pid}))
    return out, ""


def fetch_facebook(cfg_ch: dict, limit: int) -> tuple[list | None, str]:
    return _graph_comments("facebook", "FACEBOOK_PAGE_ID", "FACEBOOK_PAGE_TOKEN", limit)


def fetch_instagram(cfg_ch: dict, limit: int) -> tuple[list | None, str]:
    return _graph_comments("instagram", "INSTAGRAM_ACCOUNT_ID", "INSTAGRAM_ACCESS_TOKEN", limit)


FETCHER = {
    "mastodon": fetch_mastodon,
    "bluesky": fetch_bluesky,
    "telegram": fetch_telegram,
    "youtube": fetch_youtube,
    "facebook": fetch_facebook,
    "instagram": fetch_instagram,
}


# ========================================================== 2 · EINORDNEN
def klassifiziere(text: str, cfg: dict) -> tuple[str, float, str]:
    """Deterministische Einordnung. Rückgabe: (klasse, sicherheit, begründung).

    Reihenfolge ist Absicht: Gefahrenklassen schlagen Freundlichkeit.
    Ein „Danke, aber ich verklage dich" ist keine Dankesnachricht.
    """
    t = _norm(text)
    klassen = cfg.get("klassen") or {}
    vorrang = ["rechtlich", "troll", "spam", "kooperation", "korrektur",
               "kritik", "frage_beratung", "frage_faktisch", "dank", "lob_reichweite"]
    treffer: dict[str, list[str]] = {}
    for name in vorrang:
        for sig in (klassen.get(name) or {}).get("signale") or []:
            if sig and sig in t:
                treffer.setdefault(name, []).append(sig)

    for name in vorrang:
        if name in treffer:
            sig = treffer[name]
            # Sicherheit steigt mit der Zahl der Treffer, bleibt aber ehrlich.
            konf = min(0.55 + 0.15 * len(sig), 0.95)
            return name, konf, "Signal: " + ", ".join(sig[:3])

    # Fragezeichen ohne Signalwort: eher Sachfrage, aber unsicher.
    if "?" in (text or ""):
        return "frage_faktisch", 0.40, "Fragezeichen ohne eindeutiges Signal"
    return "sonstiges", 0.30, "kein Signal erkannt"


def klassifiziere_ki(text: str, vorschlag: str, cfg: dict) -> tuple[str, str]:
    """Zweitmeinung der Gratis-KI bei unsicherer Einordnung.

    Die KI darf NUR zwischen den bekannten Klassen wählen und niemals eine
    riskante Klasse entschärfen: Sie kann in Richtung „vorsichtiger"
    korrigieren, nie in Richtung „harmloser".
    """
    meta = cfg.get("meta") or {}
    llm_cfg = meta.get("llm") or {}
    mode = (os.environ.get("DIALOG_LLM_MODE") or llm_cfg.get("mode") or "auto").lower()
    if mode == "off":
        return vorschlag, "KI aus"
    try:
        import llm_client
    except Exception:  # noqa: BLE001
        return vorschlag, "kein LLM-Client"
    provider = next((p for p in (llm_cfg.get("providers") or ["groq", "gemini"])
                     if llm_client.available(p)), "")
    if not provider:
        return vorschlag, "kein Gratis-Key"
    namen = list((cfg.get("klassen") or {}).keys())
    system = ("Du ordnest Kommentare auf den Social-Media-Kanälen eines deutschen "
              "Finanzblogs ein. Antworte mit GENAU EINEM Wort aus dieser Liste: "
              + ", ".join(namen) + ". Keine Erklärung, kein Satzzeichen.")
    try:
        out = llm_client.chat(provider=provider,
                              messages=[{"role": "user", "content": text[:1200]}],
                              system=system, temperature=0.0, max_tokens=12)
    except Exception as exc:  # noqa: BLE001
        return vorschlag, f"KI-Ausfall ({str(exc)[:60]})"
    wahl = _norm(out).strip(" .\n\"'")
    if wahl not in namen:
        return vorschlag, "KI-Antwort unbrauchbar"
    if _risiko_rang(wahl, cfg) < _risiko_rang(vorschlag, cfg):
        # KI will entschärfen → abgelehnt. Vorsicht schlägt Bequemlichkeit.
        return vorschlag, f"KI schlug {wahl} vor (entschärfend, verworfen)"
    return wahl, f"KI bestätigte/verschärfte auf {wahl}"


_RISIKO = {MUTE: 1, AUTO: 1, REVIEW: 2, ESKALATION: 3}


def _risiko_rang(klasse: str, cfg: dict) -> int:
    modus = ((cfg.get("klassen") or {}).get(klasse) or {}).get("modus") or REVIEW
    return _RISIKO.get(modus, 2)


# ============================================================ 3 · BELEGEN
_STOPP = {"der", "die", "das", "und", "oder", "ist", "sind", "ein", "eine", "einen",
          "mit", "für", "fuer", "von", "wie", "was", "wo", "wann", "ich", "du",
          "mein", "dein", "nicht", "auch", "aber", "noch", "dass", "sich", "auf",
          "bei", "zum", "zur", "den", "dem", "des", "man", "kann", "hat", "habe",
          "mir", "mich", "dir", "wenn", "dann", "schon", "mehr", "viel", "beim"}


def _tokens(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-zäöüß]{4,}", _norm(text)) if w not in _STOPP}


def finde_beleg(text: str, artikel: list[dict]) -> dict | None:
    """Sucht den besten EIGENEN Artikel als Beleg. Kein Treffer → None.

    Bewusst konservativ: Lieber kein Beleg (und damit Freigabemappe) als
    ein schwacher Link, der am Thema vorbeigeht.
    """
    frage = _tokens(text)
    if not frage:
        return None
    bester, bestwert = None, 0.0
    for art in artikel:
        if art.get("draft") or art.get("reserve"):
            continue
        heu = _tokens(" ".join([art.get("title", ""), " ".join(art.get("tags") or []),
                                " ".join(art.get("keywords") or [])]))
        if not heu:
            continue
        gemeinsam = frage & heu
        if not gemeinsam:
            continue
        # Gewichtung: Überlappung relativ zur Frage, Bonus für Titel-Treffer.
        wert = len(gemeinsam) / max(len(frage), 1)
        if _tokens(art.get("title", "")) & frage:
            wert += 0.15
        if wert > bestwert:
            bester, bestwert = art, wert
    # Schwelle: mindestens ein Drittel der inhaltlichen Wörter muss passen.
    return bester if bestwert >= 0.34 else None


# ========================================================== 4 · ENTWERFEN
def entwirf(item: dict, klasse: str, beleg: dict | None, cfg: dict) -> tuple[str, str]:
    """Baut den Antworttext. Rückgabe: (text, herkunft)."""
    kcfg = (cfg.get("klassen") or {}).get(klasse) or {}
    haltung = cfg.get("haltung") or {}
    vorlage = (kcfg.get("vorlage") or "").strip()
    if not vorlage:
        return "", "keine Vorlage (Klasse antwortet nicht)"

    antwortkern = ""
    if beleg:
        kern = (beleg.get("kurzantwort") or beleg.get("description") or "").strip()
        antwortkern = _erster_satz(kern)

    text = (vorlage
            .replace("{beratungsklausel}", haltung.get("beratungsklausel") or "")
            .replace("{korrekturformel}", haltung.get("korrekturformel") or "")
            .replace("{antwortkern}", antwortkern)
            .replace("{beleg_url}", (beleg or {}).get("url") or ""))
    text = re.sub(r"\s+", " ", text).strip()
    # Leere Platzhalter hinterlassen keine Satzruinen.
    text = re.sub(r"\s*(Ausführlich steht das hier:|Was ich allgemein dazu erklärt habe, steht hier:)\s*$",
                  "", text).strip()

    if klasse.startswith("frage") and haltung.get("beratungsklausel"):
        if _norm(haltung["beratungsklausel"])[:30] not in _norm(text):
            text = f"{text} {haltung['beratungsklausel']}"

    herkunft = "Vorlage"
    poliert = poliere(text, item, klasse, beleg, cfg)
    if poliert and poliert != text:
        text, herkunft = poliert, "Vorlage + KI-Politur"
    return re.sub(r"\s+", " ", text).strip(), herkunft


def _erster_satz(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    if not text:
        return ""
    m = re.match(r"(.{20,220}?[.!?])(\s|$)", text)
    return (m.group(1) if m else text[:200]).strip()


def poliere(text: str, item: dict, klasse: str, beleg: dict | None, cfg: dict) -> str:
    """Optionale KI-Politur. Bei jedem Zweifel gilt die Vorlage."""
    meta = cfg.get("meta") or {}
    llm_cfg = meta.get("llm") or {}
    mode = (os.environ.get("DIALOG_LLM_MODE") or llm_cfg.get("mode") or "auto").lower()
    if mode == "off":
        return ""
    try:
        import llm_client
    except Exception:  # noqa: BLE001
        return ""
    provider = next((p for p in (llm_cfg.get("providers") or ["groq", "gemini"])
                     if llm_client.available(p)), "")
    if not provider:
        return ""
    haltung = cfg.get("haltung") or {}
    grenze = int(((cfg.get("kanaele") or {}).get(item["kanal"]) or {}).get("max_chars")
                 or (cfg.get("gate") or {}).get("max_chars_default") or 480)
    system = (
        "Du bist die Community-Redaktion eines deutschen Finanzblogs. Du schleifst "
        "einen fertigen Antwortentwurf sprachlich – mehr nicht.\n"
        "HARTE REGELN:\n"
        "- Du-Form, ruhig, konkret, kein Marketing, keine Floskeln.\n"
        "- KEINE individuelle Empfehlung, keine Handlungsanweisung, kein Rat.\n"
        "- KEINE Zahl, kein Fakt und KEIN Link, der nicht schon im Entwurf steht.\n"
        "- Nichts hinzuerfinden, nichts weglassen, was rechtlich drinsteht.\n"
        f"- Höchstens {grenze} Zeichen, höchstens {int(haltung.get('max_emoji') or 0)} Emoji.\n"
        "- Antworte NUR mit dem fertigen Antworttext, ohne Anführungszeichen."
    )
    nutzer = (f"Kommentar von {item.get('autor')}:\n{(item.get('text') or '')[:800]}\n\n"
              f"Einordnung: {klasse}\n\nEntwurf:\n{text}")
    try:
        out = llm_client.chat(provider=provider, messages=[{"role": "user", "content": nutzer}],
                              system=system,
                              temperature=float(llm_cfg.get("temperature") or 0.3),
                              max_tokens=int(llm_cfg.get("max_tokens") or 400))
    except Exception:  # noqa: BLE001
        return ""
    cand = re.sub(r"\s+", " ", (out or "").strip().strip('"').strip("'")).strip()
    if not cand or len(cand) > grenze:
        return ""
    # Die Politur darf keinen Link erfinden und keinen entfernen.
    if set(re.findall(r"https?://\S+", cand)) != set(re.findall(r"https?://\S+", text)):
        return ""
    return cand


# ============================================================= 5 · PRÜFEN
def pruefe(text: str, item: dict, klasse: str, beleg: dict | None, cfg: dict) -> list[str]:
    """Hartes Gate. Leere Liste = sendbar. Fail-closed."""
    g = cfg.get("gate") or {}
    verstoesse: list[str] = []
    t = _norm(text)
    if not text.strip():
        return ["leerer Antworttext"]

    grenze = int(((cfg.get("kanaele") or {}).get(item["kanal"]) or {}).get("max_chars")
                 or g.get("max_chars_default") or 480)
    if len(text) > grenze:
        verstoesse.append(f"zu lang ({len(text)} > {grenze} Zeichen)")
    if len(text) < int(g.get("min_chars") or 12):
        verstoesse.append("zu kurz für eine ernsthafte Antwort")

    for phrase in g.get("beratungsanschein") or []:
        if phrase and phrase in t:
            verstoesse.append(f"Beratungsanschein: „{phrase}\"")
    for phrase in g.get("versprechen") or []:
        if phrase and phrase in t:
            verstoesse.append(f"unzulässiges Versprechen: „{phrase}\"")
    for phrase in g.get("erlaubnispflichtig") or []:
        if phrase and phrase in t:
            verstoesse.append(f"erlaubnispflichtige Auskunft: „{phrase}\"")
    for phrase in g.get("floskeln") or []:
        if phrase and phrase in t:
            verstoesse.append(f"Bot-Floskel: „{phrase}\"")

    links = re.findall(r"https?://\S+", text)
    if len(links) > int(g.get("max_links") or 1):
        verstoesse.append(f"zu viele Links ({len(links)})")
    erlaubt = tuple(g.get("erlaubte_link_praefixe") or [])
    for link in links:
        if erlaubt and not link.startswith(erlaubt):
            verstoesse.append(f"fremder Link: {link[:60]}")
        for muster in g.get("verbotene_link_muster") or []:
            if muster and muster in link:
                verstoesse.append(f"verbotenes Linkmuster „{muster}\"")

    for muster in g.get("pii_muster") or []:
        try:
            if re.search(muster, text):
                verstoesse.append("personenbezogene Daten in der Antwort")
                break
        except re.error:
            continue

    emoji_max = int((cfg.get("haltung") or {}).get("max_emoji") or 0)
    if _zaehle_emoji(text) > emoji_max:
        verstoesse.append(f"zu viele Emoji (max. {emoji_max})")

    # Halluzinationsschutz: jede Zahl muss belegt sein.
    if g.get("zahlen_nur_aus_beleg", True):
        quelle = " ".join(filter(None, [
            (beleg or {}).get("title", ""), (beleg or {}).get("kurzantwort", ""),
            (beleg or {}).get("description", ""), item.get("text", ""),
        ]))
        for zahl in set(re.findall(r"\d[\d.,]*\s?(?:€|%|Euro|Prozent)?", text)):
            kern = zahl.strip()
            if len(re.sub(r"\D", "", kern)) < 2:      # einstellige Zahlen sind harmlos
                continue
            if kern not in quelle and re.sub(r"\D", "", kern) not in re.sub(r"[^\d]", "", quelle):
                verstoesse.append(f"unbelegte Zahl „{kern}\"")

    kcfg = (cfg.get("klassen") or {}).get(klasse) or {}
    if kcfg.get("belegpflicht") and not beleg:
        verstoesse.append("Belegpflicht: kein passender eigener Artikel gefunden")

    return verstoesse


_EMOJI_RX = re.compile("[\U0001F300-\U0001FAFF\u2600-\u27BF\u2190-\u21FF\uFE0F]")


def _zaehle_emoji(text: str) -> int:
    return len(_EMOJI_RX.findall(text or ""))


# ========================================================== 6 · ZUSTELLEN
def sende(item: dict, text: str) -> tuple[bool, str]:
    """Verschickt eine Antwort im richtigen Thread. Nie eine Exception."""
    kanal = item["kanal"]
    try:
        if kanal == "mastodon":
            return _send_mastodon(item, text)
        if kanal == "bluesky":
            return _send_bluesky(item, text)
        if kanal == "telegram":
            return _send_telegram(item, text)
        if kanal == "youtube":
            return _send_youtube(item, text)
        if kanal in ("facebook", "instagram"):
            return _send_graph(item, text)
    except Exception as exc:  # noqa: BLE001
        return False, f"Versand abgebrochen: {str(exc)[:120]}"
    return False, f"kein Versandweg für {kanal}"


def _send_mastodon(item, text):
    instance = (_env("MASTODON_INSTANCE") or "https://mastodon.social").rstrip("/")
    payload = {"status": text, "in_reply_to_id": item["ref"].get("in_reply_to"),
               "language": "de", "visibility": item["ref"].get("visibility") or "public"}
    status, data, err = sch.http_json(
        f"{instance}/api/v1/statuses", data=json.dumps(payload).encode("utf-8"),
        headers={"Authorization": f"Bearer {_env('MASTODON_ACCESS_TOKEN')}",
                 "Content-Type": "application/json"}, method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("id"):
        return False, f"{err or status}"
    return True, data.get("url") or ""


def _send_bluesky(item, text):
    ref = item["ref"]
    pds = ref.get("pds") or "https://bsky.social"
    status, ses, err = sch.http_json(
        f"{pds}/xrpc/com.atproto.server.createSession",
        data=json.dumps({"identifier": _env("BLUESKY_IDENTIFIER"),
                         "password": _env("BLUESKY_APP_PASSWORD")}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST", retries=2)
    if err or not isinstance(ses, dict) or not ses.get("accessJwt"):
        return False, f"Anmeldung: {err or status}"
    try:
        from social_channels.bluesky import build_facets
        facets = build_facets(text)
    except Exception:  # noqa: BLE001
        facets = []
    record = {"$type": "app.bsky.feed.post", "text": text,
              "createdAt": _now().isoformat().replace("+00:00", "Z"),
              "langs": ["de"],
              "reply": {"root": {"uri": (ref.get("root") or {}).get("uri") or ref.get("uri"),
                                 "cid": (ref.get("root") or {}).get("cid") or ref.get("cid")},
                        "parent": {"uri": ref.get("uri"), "cid": ref.get("cid")}}}
    if facets:
        record["facets"] = facets
    status, data, err = sch.http_json(
        f"{pds}/xrpc/com.atproto.repo.createRecord",
        data=json.dumps({"repo": ses.get("did"), "collection": "app.bsky.feed.post",
                         "record": record}).encode("utf-8"),
        headers={"Authorization": f"Bearer {ses['accessJwt']}",
                 "Content-Type": "application/json"}, method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("uri"):
        return False, f"{err or status}"
    return True, _bsky_link(ses.get("handle") or "", data.get("uri") or "")


def _send_telegram(item, text):
    token = _env("TELEGRAM_BOT_TOKEN")
    status, data, err = sch.http_json(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=sch.form_encode({"chat_id": item["ref"].get("chat_id"), "text": text,
                              "reply_to_message_id": item["ref"].get("message_id"),
                              "disable_web_page_preview": "false"}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("ok"):
        return False, f"{err or status}"
    return True, ""


def _send_youtube(item, text):
    token = _youtube_token()
    if not token:
        return False, "kein YouTube-Zugang"
    status, data, err = sch.http_json(
        "https://www.googleapis.com/youtube/v3/comments?part=snippet",
        data=json.dumps({"snippet": {"parentId": item["ref"].get("parent_id"),
                                     "textOriginal": text}}).encode("utf-8"),
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("id"):
        return False, f"{err or status}"
    return True, item.get("permalink") or ""


def _send_graph(item, text):
    token = _env("FACEBOOK_PAGE_TOKEN") if item["kanal"] == "facebook" \
        else _env("INSTAGRAM_ACCESS_TOKEN")
    cid = item["ref"].get("comment_id")
    status, data, err = sch.http_json(
        f"https://graph.facebook.com/v20.0/{urllib.parse.quote(str(cid))}/replies",
        data=sch.form_encode({"message": text, "access_token": token}),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST", retries=2)
    if err or not isinstance(data, dict) or not data.get("id"):
        return False, f"{err or status}"
    return True, item.get("permalink") or ""


# =============================================================== HAUPTLAUF
def lauf(dry_run: bool = False, nur_kanal: str = "", offline: bool = False) -> dict:
    cfg = load_config()
    if not cfg:
        return {"fehler": "dialog.yaml fehlt", "kanaele": {}, "neu": [], "gesendet": [],
                "offen": [], "chefsache": [], "stumm": 0}
    meta = cfg.get("meta") or {}
    state = load_state()
    bericht = {"fehler": "", "kanaele": {}, "neu": [], "gesendet": [], "offen": [],
               "chefsache": [], "stumm": 0, "blockiert": []}

    gesehen = set(state.get("gesehen") or [])
    lookback = _now() - _dt.timedelta(hours=int(meta.get("lookback_hours") or 72))
    limit = int(meta.get("max_fetch_per_channel") or 40)

    # ---------------------------------------------------------- 1 Sammeln
    eingang: list[dict] = []
    for cid, kc in (cfg.get("kanaele") or {}).items():
        if nur_kanal and cid != nur_kanal:
            continue
        if not (kc or {}).get("aktiv"):
            bericht["kanaele"][cid] = "ruht (bewusst aus)"
            continue
        fn = FETCHER.get(cid)
        if not fn:
            bericht["kanaele"][cid] = "kein Sammler hinterlegt"
            continue
        if offline:
            bericht["kanaele"][cid] = "Offline-Lauf"
            continue
        if cid == "telegram":
            items, grund = fn(kc, limit, int(state.get("telegram_offset") or 0))
        else:
            items, grund = fn(kc, limit)
        if items is None:
            bericht["kanaele"][cid] = f"Standby – {grund}"
            continue
        neu = 0
        for it in items:
            if cid == "telegram":
                state["telegram_offset"] = max(int(state.get("telegram_offset") or 0),
                                               int(it["ref"].get("next_offset") or 0))
            if it["id"] in gesehen:
                continue
            if len((it.get("text") or "").strip()) < int(meta.get("min_incoming_chars") or 12):
                gesehen.add(it["id"])
                continue
            if _parse_ts(it.get("erstellt")) < lookback:
                gesehen.add(it["id"])
                continue
            eingang.append(it)
            neu += 1
        bericht["kanaele"][cid] = f"{neu} neu von {len(items)} geprüft"

    # ------------------------------------------- 2–5 Einordnen bis Prüfen
    try:
        import social_copywriter as cw
        artikel = cw.article_pool(meta.get("base_url") or "https://franksfinanzcheck.de")
    except Exception:  # noqa: BLE001
        artikel = []

    heute = _berlin()[:10]
    heute_gesendet = sum(1 for v in state.get("verlauf") or []
                         if str(v.get("zeit", ""))[:10] == heute)
    tageslimit = int(meta.get("max_replies_per_day_total") or 20)
    laufgrenze = int(meta.get("max_replies_per_run") or 8)
    cooldown = int(meta.get("user_cooldown_hours") or 20)
    gesendet_in_lauf = 0

    for item in eingang:
        klasse, konf, grund = klassifiziere(item.get("text", ""), cfg)
        if konf < 0.6:
            klasse, kigrund = klassifiziere_ki(item.get("text", ""), klasse, cfg)
            grund = f"{grund}; {kigrund}"
        kcfg = (cfg.get("klassen") or {}).get(klasse) or {}
        modus = kcfg.get("modus") or REVIEW

        eintrag = dict(item)
        eintrag.update({"klasse": klasse, "klasse_label": kcfg.get("label") or klasse,
                        "sicherheit": round(konf, 2), "begruendung": grund,
                        "modus": modus, "erfasst": _now().isoformat()})
        bericht["neu"].append(eintrag)
        gesehen.add(item["id"])

        if modus == MUTE:
            bericht["stumm"] += 1
            continue

        if modus == ESKALATION:
            eintrag["grund"] = kcfg.get("hinweis") or "Chefsache"
            state.setdefault("chefsache", []).append(_schlank(eintrag))
            bericht["chefsache"].append(eintrag)
            continue

        beleg = finde_beleg(item.get("text", ""), artikel)
        eintrag["beleg"] = (beleg or {}).get("url") or ""
        eintrag["beleg_titel"] = (beleg or {}).get("title") or ""

        text, herkunft = entwirf(item, klasse, beleg, cfg)
        eintrag["antwort"] = text
        eintrag["herkunft"] = herkunft

        verstoesse = pruefe(text, item, klasse, beleg, cfg)
        eintrag["verstoesse"] = verstoesse

        # Frequenzschutz: nie zweimal kurz hintereinander an dieselbe Person.
        if _im_cooldown(item.get("autor", ""), item["kanal"], state, cooldown):
            verstoesse = verstoesse + ["Cooldown: dieser Person wurde gerade erst geantwortet"]
            eintrag["verstoesse"] = verstoesse

        darf_auto = (modus == AUTO and not verstoesse
                     and gesendet_in_lauf < laufgrenze
                     and heute_gesendet + gesendet_in_lauf < tageslimit)

        if verstoesse:
            bericht["blockiert"].append(eintrag)

        if darf_auto and not dry_run:
            ok, info = sende(item, text)
            eintrag["gesendet"] = ok
            eintrag["ergebnis"] = info
            if ok:
                gesendet_in_lauf += 1
                state.setdefault("verlauf", []).append(
                    {"zeit": _berlin(), "kanal": item["kanal"], "autor": item.get("autor"),
                     "klasse": klasse, "id": item["id"], "url": info, "text": text})
                bericht["gesendet"].append(eintrag)
                continue
            eintrag["verstoesse"] = verstoesse + [f"Versand fehlgeschlagen: {info}"]
        elif darf_auto and dry_run:
            eintrag["ergebnis"] = "Trockenlauf – nicht gesendet"
            bericht["gesendet"].append(eintrag)
            continue

        # Alles Übrige wandert fertig formuliert in die Freigabemappe.
        eintrag["status"] = "wartet"
        state.setdefault("offen", []).append(_schlank(eintrag))
        bericht["offen"].append(eintrag)

    state["gesehen"] = list(gesehen)
    state["offen"] = _entruempeln(state.get("offen") or [],
                                  int(meta.get("draft_expiry_days") or 5))
    if not dry_run:
        save_state(state)
    bericht["wartend"] = len(state.get("offen") or [])
    return bericht


def _schlank(eintrag: dict) -> dict:
    """Nur das, was für Freigabe und Nachvollzug nötig ist."""
    return {k: eintrag.get(k) for k in
            ("id", "kanal", "autor", "text", "permalink", "klasse", "klasse_label",
             "modus", "antwort", "beleg", "beleg_titel", "verstoesse", "herkunft",
             "erfasst", "remote_id", "ref", "begruendung")}


def _im_cooldown(autor: str, kanal: str, state: dict, stunden: int) -> bool:
    if not autor:
        return False
    grenze = _now() - _dt.timedelta(hours=stunden)
    for v in reversed(state.get("verlauf") or []):
        if v.get("kanal") != kanal or v.get("autor") != autor:
            continue
        try:
            wann = _dt.datetime.strptime(str(v.get("zeit")), "%d.%m.%Y %H:%M")
            wann = wann.replace(tzinfo=_dt.timezone.utc)
        except Exception:  # noqa: BLE001
            continue
        if wann > grenze:
            return True
    return False


def _entruempeln(offen: list, tage: int) -> list:
    grenze = _now() - _dt.timedelta(days=max(1, tage))
    return [o for o in offen if _parse_ts(o.get("erfasst")) >= grenze]


# ============================================================== FREIGABE
def freigeben(ids: list[str], dry_run: bool = False) -> dict:
    """Sendet freigegebene Entwürfe. Das Gate läuft VOR dem Versand erneut."""
    cfg, state = load_config(), load_state()
    offen = state.get("offen") or []
    ziel = [o for o in offen if (o.get("id") in ids or "alle" in ids)]
    ergebnis = {"gesendet": [], "abgelehnt": [], "unbekannt": []}
    if not ziel:
        ergebnis["unbekannt"] = ids
        return ergebnis

    for o in ziel:
        # Zweite Prüfung: Ein Ja darf das Gate nicht aushebeln. Wenn der
        # Entwurf inzwischen gegen eine Regel verstößt, geht er nicht raus.
        verstoesse = pruefe(o.get("antwort") or "", o, o.get("klasse") or "sonstiges",
                            {"url": o.get("beleg"), "title": o.get("beleg_titel")}
                            if o.get("beleg") else None, cfg)
        # Die Belegpflicht wurde bereits beim Entwurf gewürdigt; eine
        # bewusste Freigabe darf sie überstimmen, das Recht-Gate nie.
        verstoesse = [v for v in verstoesse if not v.startswith("Belegpflicht")]
        if verstoesse:
            o["verstoesse"] = verstoesse
            ergebnis["abgelehnt"].append(o)
            continue
        if dry_run:
            ergebnis["gesendet"].append(dict(o, ergebnis="Trockenlauf"))
            continue
        ok, info = sende(o, o.get("antwort") or "")
        if ok:
            state.setdefault("verlauf", []).append(
                {"zeit": _berlin(), "kanal": o.get("kanal"), "autor": o.get("autor"),
                 "klasse": o.get("klasse"), "id": o.get("id"), "url": info,
                 "text": o.get("antwort"), "freigabe": "manuell"})
            ergebnis["gesendet"].append(dict(o, ergebnis=info))
        else:
            o["verstoesse"] = [f"Versand fehlgeschlagen: {info}"]
            ergebnis["abgelehnt"].append(o)

    erledigt = {o.get("id") for o in ergebnis["gesendet"]}
    if not dry_run:
        state["offen"] = [o for o in offen if o.get("id") not in erledigt]
        save_state(state)
    return ergebnis


def verwerfen(ids: list[str]) -> int:
    state = load_state()
    vorher = len(state.get("offen") or [])
    state["offen"] = [o for o in (state.get("offen") or [])
                      if not (o.get("id") in ids or "alle" in ids)]
    save_state(state)
    return vorher - len(state["offen"])


# ============================================================== BERICHT
def cockpit(bericht: dict | None = None) -> str:
    cfg, state = load_config(), load_state()
    offen = state.get("offen") or []
    chef = state.get("chefsache") or []
    verlauf = state.get("verlauf") or []
    heute = _berlin()[:10]

    z = [
        "# 💬 Dialog-Autopilot – Stand der Community-Arbeit",
        "",
        f"**Stand:** {_berlin()} Uhr",
        "",
        f"**Wartet auf dein Ja: {len(offen)}** · Chefsache: {len(chef)} · "
        f"heute automatisch beantwortet: {sum(1 for v in verlauf if str(v.get('zeit', ''))[:10] == heute)} · "
        f"Verlauf gesamt: {len(verlauf)}",
        "",
    ]

    if bericht and bericht.get("kanaele"):
        z += ["## Kanäle in diesem Lauf", "", "| Kanal | Ergebnis |", "|---|---|"]
        for cid, info in bericht["kanaele"].items():
            z.append(f"| {cid} | {info} |")
        z.append("")

    if offen:
        z += ["## ✋ Freigabemappe – fertig formuliert, wartet auf dich", ""]
        for o in offen:
            z += [
                f"### `{o.get('id')}` · {o.get('kanal')} · {o.get('klasse_label') or o.get('klasse')}",
                "",
                f"**{o.get('autor')} schrieb:** {_kurztext(o.get('text'), 260)}",
                "",
                f"**Antwortentwurf ({o.get('herkunft') or 'Vorlage'}):**",
                "",
                f"> {o.get('antwort') or '– kein Entwurf –'}",
                "",
            ]
            if o.get("beleg"):
                z.append(f"Beleg: [{o.get('beleg_titel') or o.get('beleg')}]({o.get('beleg')})")
                z.append("")
            if o.get("verstoesse"):
                z.append("**Gate-Befund:** " + "; ".join(o["verstoesse"]))
                z.append("")
            if o.get("permalink"):
                z.append(f"Original: {o['permalink']}")
                z.append("")
            z.append(f"Freigeben: `python3 scripts/social_dialog.py --freigeben {o.get('id')}` · "
                     f"Verwerfen: `--verwerfen {o.get('id')}`")
            z.append("")
    else:
        z += ["## ✋ Freigabemappe", "", "Leer – nichts wartet auf dich.", ""]

    if chef:
        z += ["## 🚨 Chefsache – kein Bot antwortet hier", ""]
        for c in chef[-10:]:
            z += [f"- **{c.get('kanal')}** · {c.get('klasse_label') or c.get('klasse')} · "
                  f"{c.get('autor')}: {_kurztext(c.get('text'), 200)}"
                  + (f" · {c.get('permalink')}" if c.get("permalink") else "")]
        z.append("")

    if bericht and bericht.get("stumm"):
        z += [f"## 🔇 Stummgeschaltet", "",
              f"{bericht['stumm']} Beitrag/Beiträge als Spam oder Provokation eingeordnet "
              "und bewusst NICHT beantwortet (jede Antwort wäre ein Lebenszeichen).", ""]

    if verlauf:
        z += ["## Zuletzt automatisch beantwortet", "", "| Zeit | Kanal | Klasse | Antwort |",
              "|---|---|---|---|"]
        for v in verlauf[-8:][::-1]:
            z.append(f"| {v.get('zeit')} | {v.get('kanal')} | {v.get('klasse')} | "
                     f"{_kurztext(v.get('text'), 90)} |")
        z.append("")

    z += [
        "## Wie dieser Autopilot denkt",
        "",
        "- **auto** – nur risikoarme Klassen (Dank, Weiterempfehlung) antworten selbstständig.",
        "- **review** – alles, was nach individueller Beratung riechen könnte, wird fertig "
        "formuliert und wartet auf dein Ja. Du tippst nicht, du entscheidest.",
        "- **eskalation** – Rechtliches bekommt nie eine Bot-Antwort.",
        "- **mute** – Spam und Trolle bekommen nichts. Kein Lebenszeichen, kein Nachschub.",
        "",
        "Playbook: `data/social/dialog.yaml` · Anleitung: `docs/ANLEITUNG-DIALOG-AUTOPILOT.md`",
        "",
        "*Erzeugt von `scripts/social_dialog.py`.*",
    ]
    return "\n".join(z) + "\n"


def _kurztext(text: str, n: int) -> str:
    t = re.sub(r"\s+", " ", str(text or "")).strip()
    return t[:n] + ("…" if len(t) > n else "")


# ============================================================== SELBSTTEST
def selftest() -> int:
    fehler: list[str] = []
    cfg = load_config()
    if not cfg:
        print("❌ dialog.yaml fehlt")
        return 1

    klassen = cfg.get("klassen") or {}
    for name, k in klassen.items():
        if (k or {}).get("modus") not in MODI:
            fehler.append(f"Klasse {name}: unbekannter Modus {k.get('modus')}")

    # --- Einordnung ------------------------------------------------------
    faelle = [
        ("Danke dir, hat mir sehr geholfen!", "dank"),
        ("Soll ich meinen Stromvertrag jetzt kündigen?", "frage_beratung"),
        ("Wie hoch ist die Grundgebühr eigentlich?", "frage_faktisch"),
        ("Das stimmt nicht, seit 2026 gilt etwas anderes.", "korrektur"),
        ("Das ist doch nur Werbung mit Affiliate-Provision.", "kritik"),
        ("Mein Anwalt schickt Ihnen eine Abmahnung.", "rechtlich"),
        ("Schreib mir privat, ich habe Trading Signale für dich.", "spam"),
        ("Du Idiot.", "troll"),
        ("Interesse an einem Linktausch für einen Gastbeitrag?", "kooperation"),
    ]
    for text, erwartet in faelle:
        got, _, _ = klassifiziere(text, cfg)
        if got != erwartet:
            fehler.append(f"Einordnung „{text[:35]}…\" → {got}, erwartet {erwartet}")

    # Gefahr schlägt Freundlichkeit
    got, _, _ = klassifiziere("Danke, aber mein Anwalt meldet sich wegen Unterlassung.", cfg)
    if got != "rechtlich":
        fehler.append(f"Vorrangregel verletzt: {got} statt rechtlich")

    # --- Gate ------------------------------------------------------------
    item = {"kanal": "mastodon", "text": "Frage zum Tarif", "autor": "@x", "ref": {}}
    proben = [
        ("Ich empfehle dir, sofort zu wechseln.", "Beratungsanschein"),
        ("Das ist garantiert günstiger.", "Versprechen"),
        ("Das kannst du steuerlich absetzen.", "erlaubnispflichtig"),
        ("Schau hier: https://example.com/angebot", "fremder Link"),
        ("Mehr dazu: https://franksfinanzcheck.de/go/check24", "verbotenes Linkmuster"),
        ("Melde dich unter frank@example.com bei mir.", "personenbezogene Daten"),
        ("Vielen Dank für deine Nachricht, gerne helfe ich dir weiter.", "Floskel"),
        ("Du sparst damit 4.200 € im Jahr.", "unbelegte Zahl"),
    ]
    for text, was in proben:
        if not pruefe(text, item, "frage_faktisch", None, cfg):
            fehler.append(f"Gate ließ durch ({was}): {text[:45]}")

    # Saubere Antwort muss durchkommen
    beleg = {"url": "https://franksfinanzcheck.de/posts/test/", "title": "Test",
             "kurzantwort": "Die Grundgebühr steht auf der Rechnung."}
    sauber = "Die Grundgebühr steht auf der Rechnung. Ausführlich hier: " + beleg["url"]
    rest = pruefe(sauber, item, "frage_faktisch", beleg, cfg)
    if rest:
        fehler.append(f"Gate blockierte eine saubere Antwort: {rest}")

    # --- Entwurf ---------------------------------------------------------
    os.environ["DIALOG_LLM_MODE"] = "off"     # Selbsttest bleibt offline
    text, _ = entwirf({"kanal": "mastodon", "autor": "@a", "text": "Wie hoch ist die Gebühr?"},
                      "frage_faktisch", beleg, cfg)
    if beleg["url"] not in text:
        fehler.append("Entwurf verlinkt den Beleg nicht")
    if _norm((cfg.get("haltung") or {}).get("beratungsklausel", ""))[:25] not in _norm(text):
        fehler.append("Beratungsklausel fehlt in der Fragen-Antwort")
    leer, _ = entwirf({"kanal": "mastodon", "autor": "@a", "text": "x"}, "spam", None, cfg)
    if leer:
        fehler.append("Spam erzeugt einen Antworttext (darf nie)")

    # --- Beleg-Suche -----------------------------------------------------
    pool = [{"title": "Stromvertrag wechseln: So sparst du", "tags": ["Strom", "Wechsel"],
             "keywords": ["stromvertrag"], "url": "https://franksfinanzcheck.de/posts/strom/",
             "kurzantwort": "Ein Wechsel spart im Schnitt Geld.", "draft": False},
            {"title": "Mietwagen buchen ohne Fallen", "tags": ["Mietwagen"], "keywords": [],
             "url": "https://franksfinanzcheck.de/posts/mietwagen/", "kurzantwort": "",
             "draft": False}]
    if (finde_beleg("Frage zum Stromvertrag wechseln", pool) or {}).get("url") \
            != "https://franksfinanzcheck.de/posts/strom/":
        fehler.append("Beleg-Suche findet den passenden Artikel nicht")
    if finde_beleg("Wie ist das Wetter morgen", pool) is not None:
        fehler.append("Beleg-Suche liefert einen Treffer, wo keiner sein darf")

    # --- Standby-Regel (ohne Secrets kein Netzverkehr) -------------------
    gesichert = dict(os.environ)
    try:
        for key in ("MASTODON_ACCESS_TOKEN", "BLUESKY_IDENTIFIER", "BLUESKY_APP_PASSWORD",
                    "TELEGRAM_BOT_TOKEN", "YOUTUBE_REFRESH_TOKEN", "FACEBOOK_PAGE_TOKEN",
                    "INSTAGRAM_ACCESS_TOKEN"):
            os.environ.pop(key, None)
        for cid, fn in FETCHER.items():
            items, grund = fn({}, 5)
            if items is not None:
                fehler.append(f"{cid}: sammelt ohne Zugangsdaten")
            if not grund:
                fehler.append(f"{cid}: Standby ohne Begründung")
    finally:
        os.environ.clear()
        os.environ.update(gesichert)

    # --- Cockpit ---------------------------------------------------------
    if not cockpit().startswith("# "):
        fehler.append("Cockpit-Bericht fehlerhaft")

    if fehler:
        print("❌ Selbsttest fehlgeschlagen:")
        for f in fehler:
            print(f"   · {f}")
        return 1
    print(f"✅ Selbsttest bestanden ({len(klassen)} Klassen, {len(faelle)} Einordnungsfälle, "
          f"{len(proben)} Gate-Proben, Standby-Regel sauber).")
    return 0


# =================================================================== CLI
def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="Dialog-Autopilot: Kommentare erfassen, "
                                            "einordnen, beantworten (abgestufte Autonomie).")
    p.add_argument("--run", action="store_true", help="Lauf ausführen")
    p.add_argument("--dry-run", action="store_true", help="nichts senden, nur zeigen")
    p.add_argument("--kanal", default="", help="nur diesen Kanal")
    p.add_argument("--offline", action="store_true", help="kein Netzzugriff (nur Bericht)")
    p.add_argument("--freigeben", default="", help="IDs (Komma) oder 'alle' senden")
    p.add_argument("--verwerfen", default="", help="IDs (Komma) oder 'alle' verwerfen")
    p.add_argument("--status", action="store_true", help="nur das Cockpit schreiben")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args(argv)

    if a.selftest:
        return selftest()

    if a.verwerfen:
        n = verwerfen([s.strip() for s in a.verwerfen.split(",") if s.strip()])
        print(f"🗑  {n} Entwurf/Entwürfe verworfen.")
        _schreibe_cockpit()
        return 0

    if a.freigeben:
        ids = [s.strip() for s in a.freigeben.split(",") if s.strip()]
        erg = freigeben(ids, dry_run=a.dry_run)
        for o in erg["gesendet"]:
            print(f"✅ {o.get('id')} {o.get('kanal')} → {o.get('ergebnis') or 'gesendet'}")
        for o in erg["abgelehnt"]:
            print(f"❌ {o.get('id')} blockiert: {'; '.join(o.get('verstoesse') or [])}")
        if erg["unbekannt"]:
            print(f"❓ unbekannte ID(s): {', '.join(erg['unbekannt'])}")
        _schreibe_cockpit()
        return 0

    if a.status:
        _schreibe_cockpit()
        return 0

    if not a.run:
        p.print_help()
        return 0

    bericht = lauf(dry_run=a.dry_run, nur_kanal=a.kanal, offline=a.offline)
    if bericht.get("fehler"):
        print(f"⚠ {bericht['fehler']}")
        return 0

    if a.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2, default=str))
    else:
        print("=" * 64)
        print("  DIALOG-AUTOPILOT" + ("  (Trockenlauf – es wird nichts gesendet)" if a.dry_run else ""))
        print("=" * 64)
        for cid, info in (bericht.get("kanaele") or {}).items():
            print(f"  {cid:<12} {info}")
        print("-" * 64)
        print(f"  Neu {len(bericht['neu'])} · automatisch beantwortet {len(bericht['gesendet'])} · "
              f"wartet auf Freigabe {len(bericht['offen'])} · Chefsache {len(bericht['chefsache'])} · "
              f"stumm {bericht['stumm']}")
        for o in bericht["offen"]:
            print(f"    ✋ {o['id']} {o['kanal']} [{o['klasse']}] {_kurztext(o.get('antwort'), 70)}")
            if o.get("verstoesse"):
                print(f"       Gate: {'; '.join(o['verstoesse'])}")
        for c in bericht["chefsache"]:
            print(f"    🚨 {c['kanal']} {c['klasse']}: {_kurztext(c.get('text'), 70)}")

    _schreibe_cockpit(bericht)
    return 0


def _schreibe_cockpit(bericht: dict | None = None) -> None:
    try:
        with open(REPORT_PATH, "w", encoding="utf-8") as fh:
            fh.write(cockpit(bericht))
        print(f"  Cockpit: {os.path.relpath(REPORT_PATH, BLOG_DIR)}")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Cockpit nicht schreibbar: {exc}")


if __name__ == "__main__":
    raise SystemExit(main())
