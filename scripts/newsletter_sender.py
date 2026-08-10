#!/usr/bin/env python3
# ============================================================
#  NEWSLETTER-SENDER (Brevo) – vollautomatischer Tages-Digest
#
#  Auftrag: Neue Blogartikel kündigen sich ABENDS ALS EINE E-Mail an
#  (kein 2×/Tag-Spam!); Einrichtung: Secrets s. ANLEITUNG-NEWSLETTER.md.
#
#  Ablauf:
#    1. Findet heute veröffentlichte Artikel ohne Front-Matter-Flag
#       `mailed: true` (Deduplikation – nie doppelt mailen).
#    2. Baut EINE Brevo-Campaign (Digest-Format: je Artikel Titel +
#       Kurzantwort + Cover + Button). Bei einem Artikel: klassische
#       Einzelkampagne. HTML vollständig inline (E-Mail-Clients!).
#    3. Sendet per Brevo-API v3 (create + sendNow) an die Empfängerliste.
#    4. Setzt `mailed: true`, schreibt NEWSLETTER-STATUS.md.
#
#  Recht (DE, Pflicht-Programm in der Vorlage enthalten): Absender mit
#  Klarnamen, Impressums-/Datenschutz-Link + Abmeldelink (von Brevo ge-
#  zwungen {% unsubscribe %}) + Affiliate-Hinweis. DOI macht Brevo.
#
#  Konfiguration:
#    Secret    BREVO_API_KEY         (Brevo → SMTP & API → API Keys)
#    Variable  BREVO_LIST_ID         (Liste „Blog-Abonnenten", Zahl)
#    Variable  BREVO_SENDER_NAME     (Default: „Frank von FranksFinanzcheck")
#    Variable  BREVO_SENDER_EMAIL    (Default: kontakt@franksfinanzcheck.de)
#    Optional  NEWSLETTER_TEST=1     → sendet nur an Testliste/Preview
#
#  OHNE Secret/Variable: sauberer Skip mit Anleitung (exit 0).
#  Lokal testen: BREVO_API_KEY=… python3 scripts/newsletter_sender.py --dry-run
# ============================================================

import json
import os
import re
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
STATUS = ROOT / "NEWSLETTER-STATUS.md"
API = "https://api.brevo.com/v3"
BASE = "https://franksfinanzcheck.de"

API_KEY = os.environ.get("BREVO_API_KEY", "").strip()
LIST_ID = os.environ.get("BREVO_LIST_ID", "").strip()
TEST_LIST = os.environ.get("BREVO_TEST_LIST_ID", "").strip()
TEST_MODE = os.environ.get("NEWSLETTER_TEST", "") == "1"
SENDER_NAME = os.environ.get("BREVO_SENDER_NAME") or "Frank von FranksFinanzcheck"
SENDER_EMAIL = os.environ.get("BREVO_SENDER_EMAIL") or "kontakt@franksfinanzcheck.de"
DRY_RUN = "--dry-run" in sys.argv


def html_esc(t: str) -> str:
    return (t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def find_today_articles() -> list[dict]:
    """Heute datierte Artikel ohne mailed-Flag."""
    today = date.today().isoformat()
    found = []
    for p in sorted((ROOT / "content" / "posts").glob(f"{today}-*/index.md")):
        text = p.read_text(encoding="utf-8")
        if re.search(r"^mailed:\s*true", text, re.M) or re.search(r"^draft:\s*true", text, re.M):
            continue
        def fm(name):
            m = re.search(rf'^{name}:\s*["\']?(.+?)["\']?\s*$', text[:4000], re.M)
            return m.group(1).strip() if m else ""
        found.append({
            "slug": p.parent.name, "path": p,
            "title": fm("title"), "desc": fm("description") or fm("kurzantwort"),
            "url": f"{BASE}/posts/{p.parent.name}/",
            "img": f"{BASE}/images/covers/{p.parent.name}.jpg",
        })
    return found


def mark_mailed(articles: list[dict]) -> None:
    for a in articles:
        text = a["path"].read_text(encoding="utf-8")
        start = text.find("---\n", 4)
        if start != -1:
            text = text[:start] + "mailed: true\n" + text[start:]
            a["path"].write_text(text, encoding="utf-8")


def build_html(arts: list[dict]) -> str:
    """Inline-Styled E-Mail-HTML (Tabellen-Layout = Client-sicher)."""
    items = ""
    for a in arts:
        items += f"""
<tr><td style="padding:24px 0 8px">
  <a href="{a['url']}" style="text-decoration:none"><img src="{a['img']}" width="520" alt="" style="width:100%;max-width:520px;border-radius:10px;display:block"></a>
  <h2 style="font-family:Georgia,serif;color:#19324c;font-size:20px;margin:12px 0 6px; line-height:1.3">
    <a href="{a['url']}" style="color:#19324c;text-decoration:none">{html_esc(a['title'])}</a></h2>
  <p style="font-family:Helvetica,Arial,sans-serif;color:#4a5568;font-size:14px;line-height:1.6;margin:0 0 10px">{html_esc(a['desc'])[:260]}</p>
  <a href="{a['url']}" style="display:inline-block;background:#0f6049;color:#fff;font-family:Helvetica,Arial,sans-serif;font-size:14px;font-weight:bold;padding:11px 22px;border-radius:8px;text-decoration:none">Jetzt lesen →</a>
</td></tr>"""
    heute = date.today().strftime("%d.%m.%Y")
    return f"""<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f6f8">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f4f6f8"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="560" cellpadding="0" cellspacing="0" style="max-width:560px;background:#fff;border-radius:12px;overflow:hidden">
  <tr><td style="background:#0f6049;padding:20px 28px">
    <span style="font-family:Georgia,serif;color:#fff;font-size:22px">💰 FranksFinanzcheck</span><br>
    <span style="font-family:Helvetica,Arial,sans-serif;color:#cde9da;font-size:12px">Dein täglicher Spar-Kompass · {heute}</span>
  </td></tr>
  <tr><td style="padding:8px 28px 0">
    <p style="font-family:Helvetica,Arial,sans-serif;color:#2d3748;font-size:15px;line-height:1.6">Hallo 👋<br>heute gibt es {'einen neuen' if len(arts)==1 else 'zwei neue'} Artikel für dich:</p>
    <table width="100%" cellpadding="0" cellspacing="0">{items}</table>
  </td></tr>
  <tr><td style="padding:16px 28px 28px;border-top:1px solid #e2e8f0">
    <p style="font-family:Helvetica,Arial,sans-serif;color:#718096;font-size:11px;line-height:1.6">
      Du erhältst diese Mail, weil du den Newsletter auf <a href="{BASE}/" style="color:#2a7fbf">{BASE.replace('https://','')}</a> abonniert hast.
      Hinweis: Artikel enthalten ggf. Affiliate-Links (Werbung).<br>
      <a href="{BASE}/impressum/" style="color:#2a7fbf">Impressum</a> ·
      <a href="{BASE}/datenschutz/" style="color:#2a7fbf">Datenschutz</a> ·
      {{{{ unsubscribe }}}} (Abmelden jederzeit mit einem Klick)
    </p>
    <p style="font-family:Helvetica,Arial,sans-serif;color:#a0aec0;font-size:11px;margin:0">{html_esc(SENDER_NAME)} · {SENDER_EMAIL}</p>
  </td></tr>
</table></td></tr></table></body></html>"""


def brevo(method: str, path: str, payload: dict | None = None) -> dict:
    req = urllib.request.Request(
        API + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={"api-key": API_KEY, "Content-Type": "application/json", "accept": "application/json"},
        method=method)
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read().decode()
        return json.loads(raw) if raw else {}


def main() -> None:
    arts = find_today_articles()
    print(f"📰 {len(arts)} unversandte Artikel von heute gefunden.")
    if not arts:
        print("Nichts zu versenden – sauberer Skip.")
        return
    for a in arts:
        print(f"  • {a['title']}")

    if not API_KEY or not (LIST_ID or (TEST_MODE and TEST_LIST)):
        print("\n⚠️  Newsletter noch nicht aktiviert – Setup: ANLEITUNG-NEWSLETTER.md")
        print("   (Secret BREVO_API_KEY + Variable BREVO_LIST_ID fehlen – sauberer Skip, exit 0)")
        return

    eff_list = int(TEST_LIST if (TEST_MODE and TEST_LIST) else LIST_ID)
    subject = (f"Neu im Blog: {arts[0]['title']}" if len(arts) == 1
               else f"Neu im Blog: {arts[0]['title']} (+{len(arts)-1} mehr)")
    html = build_html(arts)

    if DRY_RUN:
        Path("/tmp/newsletter_preview.html").write_text(html, encoding="utf-8")
        print(f"\n[DRY-RUN] Betreff: {subject}")
        print(f"[DRY-RUN] Liste: {eff_list} | Artikel: {len(arts)} | Vorschau: /tmp/newsletter_preview.html")
        return

    payload = {
        "name": f"Blog-Digest {date.today().isoformat()} ({len(arts)} Artikel)",
        "subject": subject,
        "sender": {"name": SENDER_NAME, "email": SENDER_EMAIL},
        "type": "classic",
        "htmlContent": html,
        "recipients": {"listIds": [eff_list]},
        "inlineImageActivation": True,
        "trackSettings": {"openTracking": True, "clickTracking": True},
    }
    try:
        camp = brevo("POST", "/emailCampaigns", payload)
        camp_id = camp.get("id")
        brevo("POST", f"/emailCampaigns/{camp_id}/sendNow")
        print(f"✅ Newsletter versendet (Kampagne {camp_id}, Liste {eff_list})")
        if not TEST_MODE:
            mark_mailed(arts)
        state = "Testliste" if TEST_MODE else "Abonnenten"
        STATUS.write_text(f"""# 📬 NEWSLETTER-STATUS
> Automatisch: {datetime.now(timezone.utc):%d.%m.%Y %H:%M} UTC

- **Zuletzt versendet:** {date.today().isoformat()} ({len(arts)} Artikel, Kampagne {camp_id}, Ziel: {state})
- **Heute in der Mail:** {', '.join(a['title'] for a in arts)}
- **Modus:** Tages-Digest (1 Mail/Tag max), Dedupe-Flag `mailed: true`
- Setup/Anleitung: ANLEITUNG-NEWSLETTER.md
""", encoding="utf-8")
    except urllib.error.HTTPError as e:
        sys.exit(f"FEHLER Brevo-API (HTTP {e.code}): {e.read().decode()[:400]}")


if __name__ == "__main__":
    main()
