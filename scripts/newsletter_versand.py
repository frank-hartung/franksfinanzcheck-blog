#!/usr/bin/env python3
"""newsletter_versand.py – der Mail-Versand des Newsletters im Eigenbetrieb.

ERSETZT (24.09.2026): die Brevo-API-Ebene (Kampagnen, sendTest/sendNow,
Kontakt-Nachträge) in newsletter_digest.py. Brevo ist raus, weil jede
Änderung seiner API und Kontosemantik den Versand kaputt machte (drei
Reparatur-Reports in einer Woche: leere Testliste, „Testmails nur an
bestehende Kontakte“, Teilversand-Zustände).

ARCHITEKTUR (Details: docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md)
  Adressen    Cloudflare Worker (KV) – nie in diesem Repo (Repo ist ÖFFENTLICH:
              das Journal speichert nur Adress-HASHES, nie Roh-Adressen).
  Versand     dieser Aufruf, EIN Mailer für ALLES:
                – Liste (Di/Fr):   --send-file  (Empfänger-Datei aus dem Digest)
                – Test:            --send-file  (1 Empfänger, gleiche Regeln)
                – Bestätigung:     --bestaetigung TOKEN  (Worker holt Adresse)
                – Nachgang:        --nachgang  (offene Bestätigungen, ≤3×)
  Transport   resend (Default, API-Key) | smtp (jedes Postfach) | dryrun
              – pro EMPFÄNGER eine Mail (echte Envelope, eigener
                List-Unsubscribe-Link, kein BCC-Trick),
              – Rate-Limit (Standard 40/Minute, konfigurierbar),
              – transienter Fehler: genau ein Retry nach Pause,
              – harte Bounce (SMTP 5xx): Empfänger wird unterdrückt
                (Worker: /export/versuch ergebnis=bounce).

NUR Standardbibliothek – der Versand-Workflow installiert bewusst nichts.

Umgabe (vom Workflow als env gesetzt, nie als Skripttext-Interpolation):
  NEWSLETTER_TRANSPORT         resend | smtp | dryrun  (sonst Studio-Konfig)
  RESEND_API_KEY               für transport=resend
  NEWSLETTER_SMTP_HOST/PORT/USER/PASS/SECURE   für transport=smtp
  NEWSLETTER_WORKER_BASE       https://abos.franksfinanzcheck.de
  NEWSLETTER_WORKER_EXPORT_KEY Secret des Worker-Export (auch als Secret
                               NEWSLETTER_WORKER_EXPORT_KEY im Repo)

Exit: 0 = alles zugestellt (oder dry-run) · 1 = Teilversand · 2 = Fehler.
"""
from __future__ import annotations

import argparse
import datetime
import html as _html
import json
import os
import re
import smtplib
import socket
import socketserver
import tempfile
import ssl
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, make_msgid

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import newsletter_studio as studio      # noqa: E402  (Marke, Rechtliches, eine Quelle)

JOURNAL_REL = os.path.join("data", "newsletter_journal.jsonl")
GRUND_URL = getattr(studio, "GRUND_URL", "https://franksfinanzcheck.de")
RESEND_URL = "https://api.resend.com/emails"
HAERT_BOUNCE_MUSTER = re.compile(
    r"user unknown|no such user|undeliverable|invalid recipient|does not exist|"
    r"unknown user|mailbox unavailable|5\.1\.[12]|account is deactivated", re.I)

DEFAULT_RAT_PRO_MINUTE = 40
MAX_RETRY_PAUSE_SEK = 20
NACHGANG_MIN_MINUTEN_DEFAULT = 15
NACHGANG_MAX_VERSUCHE = 3
SMTP_PORT_DEFAULT = 587


# ------------------------------------------------------------------ Grundlagen
def jetzt_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def hash16(adresse: str) -> str:
    """Adress-Hash für das Journal – das Repo ist öffentlich, deshalb
    NIE die Roh-Adresse in Git. 16 Hex-Zeichen (64 Bit) genügen, um
    Duplikate und Reihenfolgen zu erkennen, nicht um jemanden zu
    identifizieren (bewusst ohne Salts-Pflege: es ist ein Log, kein DB)."""
    import hashlib
    return hashlib.sha256(adresse.lower().encode("utf-8")).hexdigest()[:16]


def lese_json_datei(pfad: str) -> dict:
    with open(pfad, encoding="utf-8") as fh:
        return json.load(fh)


def journal_zeile(root: str, zeile: dict) -> None:
    pfad = os.path.join(root, JOURNAL_REL)
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(zeile, ensure_ascii=False) + "\n")


def _http_json(url: str, payload: dict | None = None, key: str | None = None,
               methode: str | None = None, zeit_limited: int = 30) -> tuple[int, dict | str]:
    """POST/GET als JSON. key = Bearer/Secret-Header je Zweck.
    → (HTTP-Status, geparst-JSON-oder-Rohstring)."""
    headers = {"Accept": "application/json"}
    daten = None
    if payload is not None:
        daten = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if key:
        headers["Authorization"] = f"Bearer {key}"
    anfrage = urllib.request.Request(url, data=daten, headers=headers,
                                     method=methode or ("POST" if daten else "GET"))
    try:
        with urllib.request.urlopen(anfrage, timeout=zeit_limited) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
            try:
                return antwort.status, json.loads(roh)
            except json.JSONDecodeError:
                return antwort.status, roh
    except urllib.error.HTTPError as exc:
        roh = exc.read().decode("utf-8", "replace")
        try:
            return exc.code, json.loads(roh)
        except json.JSONDecodeError:
            return exc.code, roh
    except (urllib.error.URLError, socket.timeout, OSError) as exc:
        raise RuntimeError(f"Netzwerkfehler ({url}): {exc}") from exc


# ------------------------------------------------------------------ Transport
def transport_waehle(root: str, konf: dict, env: dict | None = None) -> tuple[str, dict]:
    """→ (Name, Einstellungen). Präzedenz: env > Studio-JSON > Default resend."""
    env = env or os.environ
    versand = (konf.get("email") or {}).get("versand") or {}
    name = env.get("NEWSLETTER_TRANSPORT") or versand.get("transport") or "resend"
    if name not in ("resend", "smtp", "dryrun"):
        raise SystemExit(f"❌ Newsletter-Versand: unbekannter Transport „{name}“ "
                         "(erlaubt: resend, smtp, dryrun)")
    rat = int(versand.get("rat_pro_minute") or DEFAULT_RAT_PRO_MINUTE)
    return name, {
        "rat_pro_minute": max(1, rat),
        "resend_key": env.get("RESEND_API_KEY") or env.get("NEWSLETTER_RESEND_KEY") or "",
        "smtp_host": env.get("NEWSLETTER_SMTP_HOST") or "",
        "smtp_port": int(env.get("NEWSLETTER_SMTP_PORT") or SMTP_PORT_DEFAULT),
        "smtp_user": env.get("NEWSLETTER_SMTP_USER") or "",
        "smtp_pass": env.get("NEWSLETTER_SMTP_PASS") or "",
        "smtp_secure": (env.get("NEWSLETTER_SMTP_SECURE") or "starttls").lower(),
    }


def one_klick_abmeldung(token: str, env: dict | None = None) -> str:
    """Die URL für den List-Unsubscribe-Header (One-Click-GET).

    Sie muss auf den WORKER zeigen (GET /abmelden meldet direkt ab) –
    der Mail-Client feuert einen headless GET ab, und dort darf das
    Ergebnis stehen, ohne dass ein Mensch noch klickt. Die Hugo-Seite
    /newsletter/abmelden/ ist die Bestätigungsseite für echte Browser-
    Klicks im Mail-Body; beim headless GET bliebe dort beim Rendern
    des Formulars nichts weiter passieren.
    """
    env = env or os.environ
    base = (env.get("NEWSLETTER_WORKER_BASE") or "").rstrip("/")
    if base:
        return f"{base}/abmeldung?token={token}"
    return f"{GRUND_URL}/newsletter/abmelden/?token={token}"


def resend_payload(empfaenger: dict, konf: dict, env: dict | None = None) -> dict:
    """Reines Payload-Modell (für Tests OHNE Netz). Der Abmeldelink ist
    pro Empfänger real (Token) – kein Platzhalter, kein Provider-Routing."""
    e_mail = (konf.get("email") or {})
    absender = e_mail.get("absender") or {}
    token = empfaenger.get("token", "")
    unsubscribe = one_klick_abmeldung(token, env)
    return {
        "from": formataddr((str(absender.get("name") or "FranksFinanzcheck"),
                            str(absender.get("email") or "news@franksfinanzcheck.de"))),
        "to": [empfaenger["email"]],
        "subject": empfaenger.get("betreff") or (e_mail.get("betreff_default") or "FranksFinanzcheck"),
        "html": empfaenger["html"],
        "text": empfaenger.get("text") or "",
        "reply_to": e_mail.get("antwort_an") or "",
        "headers": {
            "List-Unsubscribe": f"<{unsubscribe}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        },
    }


def resend_senden(payload: dict, key: str) -> tuple[bool, str]:
    """→ (ok, meldung). 429 wird genau einmal nach 20 s wiederholt."""
    for versuch in (1, 2):
        try:
            status, antwort = _http_json(RESEND_URL, payload, key=key)
        except RuntimeError as exc:
            if versuch == 1:
                time.sleep(MAX_RETRY_PAUSE_SEK)
                continue
            return False, f"netzwerk: {exc}"
        if status in (200, 202):
            return True, "annimmt"
        meldung = f"HTTP {status}"
        if isinstance(antwort, dict):
            meldung += f": {json.dumps(antwort, ensure_ascii=False)[:200]}"
        elif isinstance(antwort, str):
            meldung += f": {antwort[:200]}"
        if status == 429 and versuch == 1:
            time.sleep(MAX_RETRY_PAUSE_SEK)
            continue
        return False, meldung
    return False, "unklar nach Retry"


def smtp_mime_bauen(empfaenger: dict, konf: dict, env: dict | None = None) -> EmailMessage:
    """Pro Empfänger eine echte Mail (Envelop 1:1) – kein BCC-Envelop,
    damit Bounce und Abmeldung sauber auf EINE Adresse referenzieren."""
    e_mail = (konf.get("email") or {})
    absender = e_mail.get("absender") or {}
    msg = EmailMessage()
    msg["From"] = formataddr((str(absender.get("name") or "FranksFinanzcheck"),
                              str(absender.get("email") or "news@franksfinanzcheck.de")))
    msg["To"] = empfaenger["email"]
    msg["Subject"] = empfaenger.get("betreff") or (e_mail.get("betreff_default") or "FranksFinanzcheck")
    reply = e_mail.get("antwort_an") or ""
    if reply:
        msg["Reply-To"] = reply
    token = empfaenger.get("token") or ""
    if token:
        msg["List-Unsubscribe"] = f"<{one_klick_abmeldung(token, env)}>"
        msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    if empfaenger.get("preheader"):
        msg["X-Preheader"] = str(empfaenger["preheader"])[:300]
    msg["Message-ID"] = make_msgid(domain="franksfinanzcheck.de")
    text = empfaenger.get("text") or ""
    if text:
        msg.set_content(text)
    msg.add_alternative(empfaenger["html"], subtype="html")
    return msg


def smtp_senden(empfaenger: dict, konf: dict, einstellungen: dict,
                env: dict | None = None) -> tuple[str, str]:
    """→ (status, meldung): zugestellt | weich | hart | netzwerk."""
    msg = smtp_mime_bauen(empfaenger, konf, env)
    host = einstellungen["smtp_host"]
    if not host:
        return "fehler", "SMTP-Host nicht konfiguriert (NEWSLETTER_SMTP_HOST)"
    for versuch in (1, 2):
        try:
            if einstellungen["smtp_secure"] == "ssl":
                ctx = ssl.create_default_context()
                conn = smtplib.SMTP_SSL(host, einstellungen["smtp_port"], timeout=45, context=ctx)
            else:
                conn = smtplib.SMTP(host, einstellungen["smtp_port"], timeout=45)
            with conn:
                if einstellungen["smtp_secure"] == "starttls":
                    conn.starttls(context=ssl.create_default_context())
                # "keine" = plain (lokaler Relay, Selftest-Sink) – sonst starttls.
                if einstellungen["smtp_user"]:
                    conn.login(einstellungen["smtp_user"], einstellungen["smtp_pass"])
                fehler_dict = conn.send_message(msg)
            if not fehler_dict:
                return "zugestellt", "annahmen"
            code, antwort = next(iter(fehler_dict.values()))
            meldung = antwort.decode("utf-8", "replace")[:200] if antwort else ""
            return ("hart" if code >= 500 else "weich", f"SMTP {code} {meldung}")
        except smtplib.SMTPRecipientsRefused as exc:
            if exc.recipients:
                code, antwort = next(iter(exc.recipients.values()))
                meldung = antwort.decode("utf-8", "replace")[:200] if antwort else ""
                return ("hart" if code >= 500 else "weich", f"SMTP {code} {meldung}")
            return "weich", f"SMTP-Abweisung: {str(exc)[:200]}"
        except (smtplib.SMTPException, socket.timeout, OSError) as exc:
            if versuch == 1:
                time.sleep(MAX_RETRY_PAUSE_SEK)
                continue
            return "netzwerk", str(exc)[:200]
    return "netzwerk", "unklar nach Retry"


# ------------------------------------------------------------------ Worker-Export
def worker_konfig(env: dict | None = None) -> tuple[str, str]:
    env = env or os.environ
    base = (env.get("NEWSLETTER_WORKER_BASE") or "").rstrip("/")
    key = env.get("NEWSLETTER_WORKER_EXPORT_KEY") or ""
    return base, key


def worker_abfrage(pfad: str, param: dict | None = None, *, base: str, key: str) -> dict:
    url = base + pfad
    if param:
        url += "?" + urllib.parse.urlencode(param)
    status, antwort = _http_json(url, None, methode="GET")
    if status == 200 and isinstance(antwort, dict):
        return antwort
    if status == 404 and isinstance(antwort, dict):
        return antwort  # z. B. {"status": "unbekannt"}
    meldung = antwort if isinstance(antwort, str) else json.dumps(antwort, ensure_ascii=False)
    raise RuntimeError(f"Worker-Antwort {status} ({pfad}): {str(meldung)[:200]}")


def worker_melden(base: str, key: str, token: str, ergebnis: str) -> None:
    """Versuch/Bounce ans Worker-Backend melden. Fail-laut, nicht fail-hard:
    die Mail ist raus; der Status-Nachtrag darf den Lauf nicht roten."""
    try:
        anfrage = urllib.request.Request(
            base + "/export/versuch",
            data=urllib.parse.urlencode({"token": token, "ergebnis": ergebnis}).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded", "X-FF-Key": key})
        with urllib.request.urlopen(anfrage, timeout=20) as antwort:
            if antwort.status not in (200, 204):
                print(f"   ⚠ Worker-Statusnachtrag unbeantwortet (HTTP {antwort.status}) – "
                      "Empfänger-Zustand im Worker prüfen.")
    except (urllib.error.URLError, OSError) as exc:
        print(f"   ⚠ Worker-Statusnachtrag fehlgeschlagen ({exc}) – "
              "Empfänger-Zustand im Worker prüfen.")


# ------------------------------------------------------------------ Sendefile
def sende_datei(datei: str, root: str = BLOG_DIR, env: dict | None = None,
                konf: dict | None = None, schlafen=None) -> int:
    """Die eigentliche Versand-Verbindungsstrecke: Datei lesen → pro
    Empfänger senden (Rate-Limit) → Journal → Exit-Code.

    schlafen = Zeitverschiebung (Tests: kein echtes Warten)."""
    env = env or os.environ
    schlafen = schlafen or time.sleep
    konf = konf or studio.konfiguration(root, streng=False)
    daten = lese_json_datei(datei)
    empfaenger = daten.get("empfaenger") or []
    if not empfaenger:
        print("📭 Versand: keine Empfänger in der Datei – nichts zu senden.")
        return 0
    transport, einstellungen = transport_waehle(root, konf, env)
    if transport == "resend" and not einstellungen["resend_key"]:
        raise SystemExit("❌ Versand transport=resend, aber RESEND_API_KEY fehlt – "
                         "nichts versendet. Secret setzen oder NEWSLETTER_TRANSPORT=smtp.")
    if transport == "smtp" and not einstellungen["smtp_host"]:
        raise SystemExit("❌ Versand transport=smtp, aber NEWSLETTER_SMTP_HOST fehlt – "
                         "nichts versendet.")
    ausgabe = daten.get("ausgabe") or "ohne-nummer"
    betreff = daten.get("betreff") or ""
    preheader = daten.get("preheader") or ""
    base, key = worker_konfig(env)
    rat = einstellungen["rat_pro_minute"]
    interval = 60.0 / rat

    print(f"📬 Versand ({transport}): {len(empfaenger)} Empfänger · Ausgabe {ausgabe} · "
          f"Rate-Limit {rat}/Minute")
    zugestellt = 0
    fehler = 0
    bounces = 0
    for index, person in enumerate(empfaenger):
        if index and transport != "dryrun":
            schlafen(interval)
        mail = {
            "email": person["email"],
            "token": person.get("token") or "",
            "html": person["html"],
            "text": person.get("text") or "",
            "betreff": person.get("betreff") or betreff,
            "preheader": person.get("preheader") or preheader,
        }
        if transport == "dryrun":
            status, meldung = "dryrun", "nicht gesendet (dry-run)"
        elif transport == "resend":
            ok, meldung = resend_senden(resend_payload(mail, konf, env),
                                        einstellungen["resend_key"])
            status = "zugestellt" if ok else "fehler"
        else:
            status, meldung = smtp_senden(mail, konf, einstellungen, env)
        if status in ("zugestellt", "dryrun"):
            zugestellt += 1
        elif status == "hart" or (status == "fehler" and HAERT_BOUNCE_MUSTER.search(meldung or "")):
            bounces += 1
            status = "bounce"
            if base and key and mail["token"]:
                worker_melden(base, key, mail["token"], "bounce")
        else:
            fehler += 1
        journal_zeile(root, {
            "ts": jetzt_iso(), "modus": "sendefile", "ausgabe": ausgabe,
            "empfaenger": hash16(mail["email"]), "bytes": len(mail["html"].encode("utf-8")),
            "transport": transport, "status": status, "detail": (meldung or "")[:160],
        })
        marke = {"zugestellt": "✅", "dryrun": "⚪", "bounce": "🚫", "weich": "⏳"}.get(status, "❌")
        print(f"  {marke} {hash16(mail['email'])} · {status} {('· ' + meldung) if meldung else ''}")
    if transport == "dryrun":
        print(f"⚪ Dry-Run: {zugestellt}/{len(empfaenger)} durchgespielt, nichts versendet.")
        return 0
    print(f"📬 Versand-Fazit: {zugestellt} zugestellt · {fehler} Fehler · {bounces} Bounce "
          f"· {len(empfaenger)} Empfänger")
    if fehler == 0 and bounces == 0:
        return 0
    if zugestellt > 0:
        print("⚠ TEILVERSAND – Rest am nächsten Versandtag oder manuell nachsenden "
              "(Journal: data/newsletter_journal.jsonl).")
        return 1
    return 2


# ------------------------------------------------------------------ Bestätigung
def bestaetigung_html(token: str, konf: dict, env: dict | None = None) -> tuple[str, str, str]:
    """Bestätigungs-Mail (Double-Opt-In): eigene Domain, eigener Takt,
    eigener Token – die Adresse verlässt den Worker nie einen zweiten
    Weg. → (html, text, betreff)."""
    env = env or os.environ
    e_mail = (konf.get("email") or {})
    design = ((konf.get("design") or {}).get("hell")) or {}
    text_primary = design.get("text", "#2E2E33")
    marke = design.get("headline", "#0E5A43")
    karte = design.get("karte", "#FFFFFF")
    grenze = design.get("grenze", "#DCE6E1")
    seite = design.get("seite", "#FAFCFB")
    recht = e_mail.get("rechtliches") or {}
    absender_name = (e_mail.get("absender") or {}).get("name") or "FranksFinanzcheck"
    basis = (env.get("NEWSLETTER_WORKER_BASE") or "").rstrip("/")
    token_q = _html.escape(token, quote=True)
    if basis:
        # Der Worker rendert pro Anfrage: das Token darf ins HTML, und ohne
        # JavaScript funktioniert der Klick über das normale Formular.
        link = f"{basis}/bestaetigung?token={token_q}"
        ablink = f"{basis}/abmeldung?token={token_q}"
    else:
        link = f"{GRUND_URL}/newsletter/bestaetigung/"
        ablink = f"{GRUND_URL}/newsletter/abmelden/"
    impressum = recht.get("impressum_url") or f"{GRUND_URL}/impressum/"
    datenschutz = recht.get("datenschutz_url") or f"{GRUND_URL}/datenschutz/"
    betreff = "FranksFinanzcheck: Bestätigung deines Newsletters"
    html_seite = (
        '<!doctype html><html lang="de"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width">'
        f'<title>{_html.escape(betreff)}</title></head>'
        f'<body style="margin:0;background:{seite};padding:24px 12px;">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0">'
        '<tr><td align="center">'
        f'<table role="presentation" width="600" cellpadding="0" cellspacing="0" '
        f'style="max-width:600px;width:100%;background:{karte};border:1px solid {grenze};'
        'border-radius:10px;padding:32px 28px;">'
        '<tr><td style="padding:0 4px;">'
        f'<p style="color:{marke};font-size:15px;font-weight:700;margin:0 0 16px;">'
        f'{_html.escape(absender_name)}</p>'
        '<h1 style="margin:0 0 12px;font-size:22px;line-height:1.3;color:' + marke + ';">'
        'Noch ein Klick: Newsletter bestätigen</h1>'
        '<p style="margin:0 0 16px;font-size:15px;line-height:1.6;color:' + text_primary + ';">'
        'Du hast dich für den Spar-Newsletter von FranksFinanzcheck angemeldet – '
        'dienstags die Zahlen der Woche, freitags die Fristen davor, nie mehr als '
        'zwei Mails pro Woche. Klicke jetzt, damit deine Adresse auf die Liste kommt '
        '(Double-Opt-In):</p>'
        f'<table role="presentation" cellpadding="0" cellspacing="0" style="margin:8px 0 16px;">'
        '<tr><td style="background:' + marke + ';border-radius:8px;">'
        f'<a href="{link}" style="display:inline-block;padding:13px 26px;'
        'font-size:15px;font-weight:700;color:#ffffff;text-decoration:none;">'
        'Ja, ich möchte den Newsletter</a></td></tr></table>'
        '<p style="margin:0 0 16px;font-size:13px;line-height:1.5;color:' + text_primary + ';">'
        'Der Link ist 14 Tage gültig. Wenn du dich nicht angemeldet hast: keine Aktion '
        'nötig – diese Mail bleibt ohne Wirkung.</p>'
        '<p style="margin:0;font-size:12px;line-height:1.5;color:#6C6C6C;">'
        f'<a href="{ablink}" style="color:{marke};">Jetzt abmelden</a> · '
        f'<a href="{impressum}" style="color:{marke};">Impressum</a> · '
        f'<a href="{datenschutz}" style="color:{marke};">Datenschutz</a></p>'
        '</td></tr></table>'
        '</td></tr></table></body></html>')
    text_alt = (
        "Noch ein Klick: Newsletter bestätigen\n"
        "\n"
        "Du hast dich für den Spar-Newsletter von FranksFinanzcheck angemeldet – "
        "dienstags die Zahlen der Woche, freitags die Fristen davor, nie mehr als "
        "zwei Mails pro Woche.\n"
        "\n"
        "Bestätigen (14 Tage gültig):\n"
        f"{link}\n"
        "\n"
        "Wenn du dich nicht angemeldet hast: keine Aktion nötig – diese Mail "
        "bleibt ohne Wirkung.\n"
        f"Abmelden: {ablink}\n"
        f"Impressum: {impressum}\n"
        f"Datenschutz: {datenschutz}\n"
    )
    return html_seite, text_alt, betreff


def sende_bestaetigung(token: str, root: str = BLOG_DIR, env: dict | None = None,
                       schlafen=None) -> int:
    """Bestätigungs-Mail für EINEN Token: Worker-Abfrage → Versand →
    Versuch melden. Exit 0 = raus, 1 = Teilzustand (Adresse offen), 2 = Fehler."""
    env = env or os.environ
    konf = studio.konfiguration(root, streng=False)
    base, key = worker_konfig(env)
    if not base or not key:
        raise SystemExit("❌ Bestätigung: NEWSLETTER_WORKER_BASE / "
                         "NEWSLETTER_WORKER_EXPORT_KEY fehlen – die Adresse ist "
                         "im Worker, nicht im Repo.")
    antwort = worker_abfrage("/export/token", {"token": token}, base=base, key=key)
    status = antwort.get("status")
    email = antwort.get("email") or ""
    if status == "unbekannt":
        print("📭 Bestätigung: Token unbekannt – nichts versendet (Seite zeigt den Weg).")
        return 0
    if status in ("unsubscribed", "abgelaufen"):
        print(f"📭 Bestätigung: Adresse im Zustand „{status}“ – nichts versendet.")
        return 0
    if status != "pending" or not email:
        print(f"⚠ Bestätigung: unerwarteter Zustand „{status}“ – nichts versendet, "
              "Worker-Zustand prüfen.")
        return 2
    html_seite, text_alt, betreff = bestaetigung_html(token, konf, env)
    datei = os.path.join(tempfile.gettempdir(), "ff-bestaetigung.json")
    with open(datei, "w", encoding="utf-8") as fh:
        json.dump({
            "ausgabe": f"bestaetigung-{token[:8]}",
            "betreff": betreff,
            "empfaenger": [{"email": email, "token": token,
                            "html": html_seite, "text": text_alt}],
        }, fh, ensure_ascii=False)
    try:
        rc = sende_datei(datei, root=root, env=env, konf=konf, schlafen=schlafen)
    finally:
        try:
            os.remove(datei)
        except OSError:
            pass
    if rc == 0:
        worker_melden(base, key, token, "gesendet")
        print(f"✅ Bestätigungsmail versendet an {hash16(email)} (Token …{token[-4:]}).")
    elif rc == 1:
        worker_melden(base, key, token, "gesendet")
        print(f"⚠ Bestätigungsmail TEILWEISE an {hash16(email)} – Nachgang holt nach.")
    return rc


# ------------------------------------------------------------------ Nachgang
def sende_nachgang(root: str = BLOG_DIR, env: dict | None = None, schlafen=None) -> int:
    """Stündlicher Catch-up: offene Bestätigungen, die den Dispatch nicht
    erreicht haben (Rate-Limit, GitHub-Wartung) oder deren Mail nie ankam.
    Regeln: erst nach NACHGANG_MIN_MINUTEN, max. NACHGANG_MAX_VERSUCHE,
    danach „abgelaufen“ im Worker. Exit 0 = nichts übrig, 1 = Rest offen."""
    env = env or os.environ
    schlafen = schlafen or time.sleep
    konf = studio.konfiguration(root, streng=False)
    base, key = worker_konfig(env)
    if not base or not key:
        print("ℹ️ Nachgang: Worker-Konfiguration fehlt – nichts zu tun.")
        return 0
    antwort = worker_abfrage("/export/pending", None, base=base, key=key)
    offen = antwort.get("offen") or []
    min_minuten = int(env.get("NEWSLETTER_NACHGANG_MIN_MINUTEN") or NACHGANG_MIN_MINUTEN_DEFAULT)
    nun = datetime.datetime.now(datetime.timezone.utc)
    zugestellt = 0
    for person in offen:
        token = person.get("token") or ""
        seit = person.get("seit") or ""
        letzter_versuch = person.get("bestaetigung_gesendet") or ""
        versuche = int(person.get("versuche") or 0)
        if versuche >= NACHGANG_MAX_VERSUCHE:
            worker_melden(base, key, token, "abgelaufen")
            print(f"🚫 Nachgang: {hash16(person.get('email', ''))} abgelaufen "
                  f"(≥{NACHGANG_MAX_VERSUCHE} Versuche ohne Klick) – nicht wiederholt.")
            continue
        try:
            seit_dt = datetime.datetime.fromisoformat(seit.replace("Z", "+00:00"))
            min_ersfuellt = (nun - seit_dt) >= datetime.timedelta(minutes=min_minuten)
        except ValueError:
            min_ersfuellt = True
        pause_abbgelaufen = True
        if letzter_versuch:
            try:
                letzter = datetime.datetime.fromisoformat(letzter_versuch.replace("Z", "+00:00"))
                pause_abbgelaufen = (nun - letzter) >= datetime.timedelta(minutes=60)
            except ValueError:
                pause_abbgelaufen = True
        if not min_ersfuellt and not pause_abbgelaufen:
            continue
        html_seite, text_alt, betreff = bestaetigung_html(token, konf, env)
        datei = os.path.join(tempfile.gettempdir(), "ff-nachgang.json")
        with open(datei, "w", encoding="utf-8") as fh:
            json.dump({
                "ausgabe": f"bestaetigung-nachgang-{token[:8]}",
                "betreff": betreff,
                "empfaenger": [{"email": person["email"], "token": token,
                                "html": html_seite, "text": text_alt}],
            }, fh, ensure_ascii=False)
        try:
            rc = sende_datei(datei, root=root, env=env, konf=konf, schlafen=schlafen)
        finally:
            try:
                os.remove(datei)
            except OSError:
                pass
        if rc == 0:
            worker_melden(base, key, token, "gesendet")
            zugestellt += 1
            print(f"✅ Nachgang: Bestätigung an {hash16(person['email'])} (Versuch {versuche + 1}).")
        else:
            worker_melden(base, key, token, "gesendet")
            print(f"⚠ Nachgang: Bestätigung an {hash16(person['email'])} unvollständig "
                  f"(Versuch {versuche + 1}) – nächster Durchgang wiederholt.")
        schlafen(5)
    print(f"📬 Nachgang: {zugestellt} Bestätigung(en) nachgesendet, {len(offen)} offen geprüft.")
    return 0


# ------------------------------------------------------------------ Selftest
class _SmtpHandler(socketserver.BaseRequestHandler):
    """Minimaler SMTP-Server (nur für den Selftest): beantwortet
    EHLO/MAIL/RCPT/DATA/QUIT, speichert jede Mail, kann pro Empfänger
    550 antworten (Bounce-Prüfung). Reines Socket-Protokoll – keine
    smtpd-Abhängigkeit (in Python 3.12 entfernt, in 3.14 weg)."""

    abgewiesene: set = set()
    empfangene: list = []

    def handle(self):  # noqa: N802 (socketserver-Vertrag)
        rfile = self.request.makefile("rb")
        wfile = self.request.makefile("wb")

        def send(text: str) -> None:
            wfile.write((text + "\r\n").encode("utf-8"))
            wfile.flush()

        send("220 ff-newsletter-selftest.de OK")
        im_datum = False
        buffer = []
        rcpt = ""
        try:
            while True:
                zeile = rfile.readline()
                if not zeile:
                    break
                if im_datum:
                    if zeile.strip() == b".":
                        _SmtpHandler.empfangene.append({
                            "to": rcpt,
                            "datum": "".join(b.decode("utf-8", "replace") for b in buffer),
                        })
                        send("250 OK gespeichert")
                        im_datum = False
                        buffer = []
                    else:
                        buffer.append(zeile)
                    continue
                text = zeile.decode("utf-8", "replace").strip()
                gebot = text.split(" ", 1)[0].upper()
                if gebot in ("EHLO", "HELO"):
                    send("250-ff-newsletter-selftest.de")
                    send("250 OK")
                elif gebot == "MAIL":
                    send("250 OK")
                elif gebot == "RCPT":
                    rcpt = text.split(":", 1)[-1].strip().strip("<>")
                    send("550 5.1.1 user unknown" if rcpt in _SmtpHandler.abgewiesene else "250 OK")
                elif gebot == "DATA":
                    send("354 Go ahead")
                    im_datum = True
                elif gebot == "QUIT":
                    send("221 Tschüss")
                    break
                else:
                    send("250 OK")
        finally:
            try:
                wfile.flush()
                self.request.close()
            except OSError:
                pass


def _selftest() -> int:
    pruefungen = 0

    def pruefe(bedingung: bool, meldung: str) -> None:
        nonlocal pruefungen
        pruefungen += 1
        if not bedingung:
            raise AssertionError(f"❌ Selftest #{pruefungen}: {meldung}")

    konf = {
        "email": {
            "absender": {"name": "Frank von FranksFinanzcheck",
                         "email": "news@franksfinanzcheck.de"},
            "antwort_an": "kontakt@franksfinanzcheck.de",
            "versand": {"transport": "resend", "rat_pro_minute": 600},
            "rechtliches": {"impressum_url": "https://franksfinanzcheck.de/impressum/",
                            "datenschutz_url": "https://franksfinanzcheck.de/datenschutz/"},
        },
        "design": {"hell": {"seite": "#FAFCFB", "karte": "#FFFFFF", "grenze": "#DCE6E1",
                            "text": "#2E2E33", "headline": "#0E5A43"}},
    }

    # 1) Resend-Payload: pro Empfänger, echter Abmeldelink, One-Click-Header.
    #    Der One-Click muss auf den WORKER zeigen: der Mail-Client feuert einen
    #    headless GET ab, der direkt abmeldet. Die Hugo-Seite ist nur für echte
    #    Browser-Klicks (Bestätigungsseite) gedacht und würde im headless GET
    #    nichts abmelden – genau der Bug, den dieser Selftest einklemmt.
    worker_env = {"NEWSLETTER_WORKER_BASE": "https://abos.beispiel.de"}
    payload = resend_payload({"email": "A@Beispiel.de", "token": "t-123",
                              "html": "<p>hi</p>", "text": "hi",
                              "betreff": "Betreff der Woche", "preheader": "x"},
                             konf, env=worker_env)
    pruefe(payload["to"] == ["A@Beispiel.de"], "Resend: Empfänger fehlt")
    pruefe(payload["from"].endswith("news@franksfinanzcheck.de>"), "Resend: Absender falsch")
    pruefe(payload["headers"]["List-Unsubscribe"]
           == "<https://abos.beispiel.de/abmeldung?token=t-123>",
           f"Resend: One-Click zeigt nicht auf den Worker: "
           f"{payload['headers']['List-Unsubscribe']}")
    pruefe(payload["headers"]["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click",
           "Resend: One-Click-Header fehlt")
    pruefe(payload["subject"] == "Betreff der Woche", "Resend: Betreff fehlt")
    # Ohne Worker-Basis: ehrlicher Fallback auf die Hugo-Seite (menschlich
    # klickbar), nicht ein erfundener Endpunkt.
    payload_fallback = resend_payload({"email": "A@Beispiel.de", "token": "t-123",
                                       "html": "<p>hi</p>", "text": "hi"}, konf,
                                      env={})
    pruefe(payload_fallback["headers"]["List-Unsubscribe"]
           == f"<{GRUND_URL}/newsletter/abmelden/?token=t-123>",
           f"Resend: Fallback ohne Worker-Basis falsch: "
           f"{payload_fallback['headers']['List-Unsubscribe']}")

    # 2) SMTP-MIME: Envelop 1:1, alternative Teils, List-Unsubscribe (Worker).
    msg = smtp_mime_bauen({"email": "b@beispiel.de", "token": "t-456",
                           "html": "<html><body>hi</body></html>", "text": "hi"},
                          konf, env=worker_env)
    pruefe(msg["To"] == "b@beispiel.de", "SMTP: To fehlt")
    pruefe(str(msg["List-Unsubscribe"])
           == "<https://abos.beispiel.de/abmeldung?token=t-456>",
           f"SMTP: One-Click zeigt nicht auf den Worker: {msg['List-Unsubscribe']}")
    pruefe(msg["List-Unsubscribe-Post"] == "List-Unsubscribe=One-Click",
           "SMTP: One-Click-Header fehlt")
    teile = [t.get_content_type() for t in msg.get_payload()]
    pruefe("text/plain" in teile and "text/html" in teile, "SMTP: Alternative fehlt")

    # 3) Rate-Limit + Journal + Bounce gegen den SMTP-Sink.
    _SmtpHandler.empfangene.clear()
    _SmtpHandler.abgewiesene = {"hart@beispiel.de"}
    server = socketserver.ThreadingTCPServer(("127.0.0.1", 0), _SmtpHandler)
    server.daemon_threads = True
    with server:
        port = server.server_address[1]
        th = threading.Thread(target=server.serve_forever, daemon=True)
        th.start()
        # Unser Minimal-Sink kennt kein STARTTLS → plain-Modus ("keine").
        einstellungen = {"smtp_host": "127.0.0.1", "smtp_port": port, "smtp_user": "",
                         "smtp_pass": "", "smtp_secure": "keine"}
        try:
            resultate = []
            for adresse in ("gut@beispiel.de", "hart@beispiel.de"):
                mail = {"email": adresse, "token": "t-x", "html": "<p>hi</p>", "text": "hi"}
                status, meldung = smtp_senden(mail, konf, einstellungen)
                resultate.append(status)
            pruefe(resultate[0] == "zugestellt", f"Sink: gute Adresse nicht zugestellt ({resultate[0]})")
            pruefe(resultate[1] == "hart", f"Sink: harte Bounce nicht erkannt ({resultate[1]})")
            pruefe(len(_SmtpHandler.empfangene) == 1, "Sink: Mail nicht empfangen")
            pruefe(_SmtpHandler.empfangene[0]["to"] == "gut@beispiel.de", "Sink: falscher Empfänger")
        finally:
            server.shutdown()
            server.server_close()

    # 4) Bestätigungs-Mail: Link, Token, 14-Tage-Hinweis, Rechtszeile.
    #    Mit Worker-Basis zeigt der Link auf den Worker (er rendert pro
    #    Anfrage – der Klick funktioniert auch ohne JavaScript); ohne
    #    Basis bleibt die ehrliche Info-Seite der Site.
    lc_env = {"NEWSLETTER_WORKER_BASE": "https://abos.beispiel.de"}
    html_seite, text_alt, betreff = bestaetigung_html("tok-XYZ", konf, lc_env)
    pruefe("https://abos.beispiel.de/bestaetigung?token=tok-XYZ" in html_seite,
           "Bestätigung: Link zeigt nicht auf den Worker")
    pruefe("https://abos.beispiel.de/abmeldung?token=tok-XYZ" in html_seite,
           "Bestätigung: Abmelde-Link zeigt nicht auf den Worker")
    pruefe("14 Tage" in html_seite, "Bestätigung: Ablauf-Frist fehlt")
    pruefe("/impressum/" in html_seite and "/datenschutz/" in html_seite,
           "Bestätigung: Rechtszeile unvollständig")
    pruefe("https://abos.beispiel.de/bestaetigung?token=tok-XYZ" in text_alt,
           "Bestätigung: Textalternative ohne Link")
    html_fb, text_fb, _ = bestaetigung_html("tok-XYZ", konf, {})
    pruefe("/newsletter/bestaetigung/" in html_fb and "?token=" not in html_fb,
           "Bestätigung: Fallback ohne Worker-Basis falsch")
    pruefe(betreff, "Bestätigung: Betreff fehlt")

    # 5) Transport-Auswahl: env schlägt Studio-Konfig.
    name, _ = transport_waehle(BLOG_DIR, konf, {"NEWSLETTER_TRANSPORT": "smtp"})
    pruefe(name == "smtp", "Transport: env-Überschreibung ignoriert")
    name, _ = transport_waehle(BLOG_DIR, konf, {})
    pruefe(name == "resend", "Transport: Studio-Default ignoriert")

    # 6) sende_datei: dry-run ohne Netz, Journal-Hash statt Adresse.
    tmp = os.path.join(tempfile.gettempdir(), "ff-vertest.json")
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump({
            "ausgabe": "selftest", "betreff": "Selbsttest",
            "empfaenger": [{"email": "dry@beispiel.de", "token": "t-d",
                            "html": "<p>hi</p>", "text": "hi"}],
        }, fh)
    journal_pfad = os.path.join(BLOG_DIR, JOURNAL_REL)
    vorher = 0
    if os.path.exists(journal_pfad):
        vorher = sum(1 for _ in open(journal_pfad, encoding="utf-8"))
    rc = sende_datei(tmp, root=BLOG_DIR, env={"NEWSLETTER_TRANSPORT": "dryrun"}, konf=konf)
    pruefe(rc == 0, f"dry-run: Exit {rc} statt 0")
    with open(journal_pfad, encoding="utf-8") as fh:
        zeilen = fh.readlines()
    neu = zeilen[vorher:]
    pruefe(len(neu) == 1, "dry-run: keine Journal-Zeile")
    eintrag = json.loads(neu[-1])
    pruefe(eintrag["empfaenger"] == hash16("dry@beispiel.de"), "Journal: Hash statt Adresse fehlt")
    pruefe("dry@beispiel.de" not in neu[-1], "Journal: Roh-Adresse gelakt!")
    os.remove(tmp)

    # 7) Resend-Key-Pflicht: ohne Key kein Netzwerkversuch (fail-closed).
    try:
        tmp2 = os.path.join(tempfile.gettempdir(), "ff-vertest2.json")
        with open(tmp2, "w", encoding="utf-8") as fh:
            json.dump({"empfaenger": [{"email": "x@y.de", "html": "<p>hi</p>"}]}, fh)
        try:
            sende_datei(tmp2, root=BLOG_DIR, env={"NEWSLETTER_TRANSPORT": "resend"}, konf=konf)
            pruefe(False, "Resend: fehlender Key nicht abgefangen")
        except SystemExit as exc:
            pruefe("RESEND_API_KEY" in str(exc), "Resend: Abbruchmeldung ohne Klickweg")
        finally:
            os.remove(tmp2)
    except AssertionError:
        raise

    print(f"✅ newsletter_versand Selftest: {pruefungen} Fälle grün "
          "(Resend-Payload, MIME, SMTP-Sink mit Bounce, Bestätigung, Transports, Journal).")
    return 0


# ------------------------------------------------------------------ CLI
def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Newsletter-Mail-Versand (Eigenbetrieb: Resend/SMTP/dry-run)")
    ap.add_argument("--root", default=BLOG_DIR)
    ap.add_argument("--send-file", default="", help="Empfänger-Datei (JSON: ausgabe, betreff, empfaenger[])")
    ap.add_argument("--bestaetigung", default="", help="Token: Bestätigungs-Mail senden")
    ap.add_argument("--nachgang", action="store_true", help="offene Bestätigungen nachsenden (Catch-up)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)
    if args.selftest:
        return _selftest()
    if args.send_file:
        return sende_datei(os.path.abspath(args.send_file), root=os.path.abspath(args.root))
    if args.bestaetigung:
        return sende_bestaetigung(args.bestaetigung.strip(), root=os.path.abspath(args.root))
    if args.nachgang:
        return sende_nachgang(root=os.path.abspath(args.root))
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
