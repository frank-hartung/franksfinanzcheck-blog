#!/usr/bin/env python3
# ============================================================
#  MASTODON-PROFIL-SYNC
#
#  Setzt Anzeigename, Bio-Text, Profilfelder, Avatar und Header-Bild
#  des Mastodon-Accounts @FranksFinanzcheck@mastodon.social so, dass
#  sie zur tatsächlichen aktuellen Content-Ausrichtung des Blogs passen
#  (Themen, Veröffentlichungsrhythmus, Branding/Logo).
#
#  Kein Dauerlauf-Cronjob: Profil-/Branding-Texte sind redaktionelle
#  Entscheidungen, keine messbare Kennzahl wie die Publikationscadence
#  (siehe scripts/cadence_manager.py) – daher bewusst NUR manuell über
#  "Actions -> Mastodon-Profil-Sync -> Run workflow" auslösbar, wenn sich
#  der Content-Fokus oder das Branding erkennbar ändert.
#
#  Benötigtes Secret: MASTODON_ACCESS_TOKEN
#    WICHTIG: Braucht zusätzlich zu 'write:statuses'+'write:media'
#    (für scripts/social_poster.py) auch den Scope 'write:accounts',
#    sonst schlägt der Aufruf mit HTTP 403 fehl. Siehe ANLEITUNG-SOCIAL-MEDIA.md.
#
#  OHNE Token: zeigt eine Setup-Anleitung und endet SAUBER (exit 0).
#
#  Lokale Tests:
#    python3 scripts/mastodon_profile_sync.py --dry-run   # zeigt nur, was gesendet würde
# ============================================================

import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# ACHTUNG: GitHub Actions setzt nicht existierende Vars als LEEREN String
# ("${{ vars.X }}" -> "") - daher "or" statt get-Default!
MASTODON_TOKEN = (os.environ.get("MASTODON_ACCESS_TOKEN") or "").strip()
MASTODON_INSTANCE = (os.environ.get("MASTODON_INSTANCE") or "https://mastodon.social").strip().rstrip("/")
DRY_RUN = "--dry-run" in sys.argv

DISPLAY_NAME = "FranksFinanzcheck 💰 1.800€ sparen"

# Bio auf Premium-Agentur-Niveau (2026-08-27 Update):
# - Nutzen zuerst (bis zu 1.800€, belegt via homeInfoParams)
# - Social Proof (25+ Guides)
# - 6 Ratgeber-Welten vollständig
# - Rhythmus Mo/Mi/Fr + Qualitätsversprechen (Zahlen, Checklisten, redaktionell geprüft)
# - Transparenz: KI + Affiliate (Werbung) – rechtssicher nach deutschem Recht
# - Persönliche Interaktion als CTA
# Mehrzeilig, weil Mastodon Absätze rendert – 451/500 Zeichen.
NOTE = (
    "💰 Bis zu 1.800 €/Jahr Fixkosten sparen – ehrliche Ratgeber statt Verkaufsdruck.\n\n"
    "🧭 25+ Guides in 6 Welten: Strom & Gas · DSL & Internet · Versicherungen · Konto & Karten · Mietwagen · Frugalismus\n\n"
    "🗓 Mo/Mi/Fr neue Artikel – mit konkreten Zahlen, redaktionell geprüft, inkl. Checklisten.\n\n"
    "🤖 KI-unterstützt, automatisch veröffentlicht. Enthält Affiliate-Links (Werbung) – für dich ohne Mehrkosten.\n\n"
    "❓ Fragen zu deinen Verträgen? Ich antworte persönlich 👇"
)

# Mastodon erlaubt maximal 4 Profilfelder – Premium-Strategie:
# 1. Web (verifiziert via rel=me, grüner Haken) – Haupteinstieg
# 2. Ratgeber (/pillar/ = alle 6 Welten auf einen Blick, Topical Authority)
# 3. Themen (suchbare Hashtags, CamelCase, inkl. #Finanzen für Discoverability)
# 4. Pinterest (Zweitkanal, 400+ Pins, Cross-Promo für visuelle Reichweite)
# Verifizierte Links brauchen rel="me" auf der Zielseite (hugo.toml + extend_head.html).
FIELDS = [
    ("Web:", "https://franksfinanzcheck.de"),
    ("Ratgeber:", "https://franksfinanzcheck.de/pillar/"),
    ("Themen:", "#StromSparen #DSL #Versicherung #Girokonto #Mietwagen #Frugalismus #Finanzen"),
    ("Pinterest:", "https://www.pinterest.de/franksfinanzcheck/"),
]

# Premium-Flags: Discoverability = Reichweite, Indexable = Fediverse-Suche.
# Bot = False, weil trotz Automatisierung persönlich geantwortet wird (E-E-A-T).
# Früher war das Profil NICHT im Verzeichnis – direkter Reichweitenverlust.
DISCOVERABLE = True
INDEXABLE = True
BOT = False

AVATAR_DESCRIPTION = (
    "FranksFinanzcheck Logo: dunkelgrünes Quadrat mit abgerundeten Ecken und "
    "gelbem Haken – Symbol für geprüfte Spartipps."
)
HEADER_DESCRIPTION = (
    "Banner: FranksFinanzcheck Logo, Schriftzug und Slogan 'Weniger Fixkosten, "
    "mehr vom Leben' auf dunkelgrün – 6 Ratgeber-Welten im Überblick."
)

AVATAR = ROOT / "static" / "images" / "social" / "mastodon-avatar.png"
HEADER = ROOT / "static" / "images" / "social" / "mastodon-header.png"
REPORT = ROOT / "MASTODON-PROFILE-REPORT.md"

# Mastodon-Grenzwerte (siehe GET /api/v2/instance -> configuration.accounts),
# lokal vorab geprüft statt erst per HTTP 422 vom Server zu erfahren.
LIMITS = {
    "display_name": 40,
    "note": 500,
    "avatar_description": 150,
    "header_description": 150,
    "field_name": 255,
    "field_value": 255,
    "fields": 4,
}


def validate_lengths():
    errors = []
    if len(DISPLAY_NAME) > LIMITS["display_name"]:
        errors.append(f"display_name zu lang ({len(DISPLAY_NAME)}/{LIMITS['display_name']})")
    if len(NOTE) > LIMITS["note"]:
        errors.append(f"note zu lang ({len(NOTE)}/{LIMITS['note']})")
    if len(AVATAR_DESCRIPTION) > LIMITS["avatar_description"]:
        errors.append(
            f"avatar_description zu lang ({len(AVATAR_DESCRIPTION)}/{LIMITS['avatar_description']})"
        )
    if len(HEADER_DESCRIPTION) > LIMITS["header_description"]:
        errors.append(
            f"header_description zu lang ({len(HEADER_DESCRIPTION)}/{LIMITS['header_description']})"
        )
    if len(FIELDS) > LIMITS["fields"]:
        # Mastodon verwirft still die überzähligen Felder – lieber hier laut sein.
        errors.append(f"zu viele Profilfelder ({len(FIELDS)}/{LIMITS['fields']})")
    for name, value in FIELDS:
        if len(name) > LIMITS["field_name"] or len(value) > LIMITS["field_value"]:
            errors.append(f"Feld '{name}' überschreitet 255 Zeichen (Name oder Wert)")
    if errors:
        sys.exit("FEHLER: Mastodon-Profil-Sync abgebrochen (Limit-Prüfung):\n  - " + "\n  - ".join(errors))


def build_multipart(fields, files):
    boundary = "----mastodonprofilesync42"
    parts = []
    for name, value in fields:
        parts.append(
            f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode()
        )
    for name, path in files:
        if not path.is_file():
            continue
        parts.append(
            (
                f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"; '
                f'filename="{path.name}"\r\nContent-Type: image/png\r\n\r\n'
            ).encode()
            + path.read_bytes()
            + b"\r\n"
        )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), boundary


def print_setup_hint():
    print("=" * 68)
    print("MASTODON-PROFIL-SYNC: Kein API-Token gefunden - überspringe (exit 0).")
    print("")
    print("Setup: Secret MASTODON_ACCESS_TOKEN muss den Scope 'write:accounts'")
    print("zusätzlich zu 'write:statuses'+'write:media' enthalten.")
    print("Details: ANLEITUNG-SOCIAL-MEDIA.md")
    print("=" * 68)


def main():
    if not MASTODON_TOKEN and not DRY_RUN:
        print_setup_hint()
        return

    validate_lengths()

    fields = [
        ("display_name", DISPLAY_NAME),
        ("note", NOTE),
        ("avatar_description", AVATAR_DESCRIPTION),
        ("header_description", HEADER_DESCRIPTION),
        # Mastodon erwartet Booleans im Multipart-Body als "true"/"false".
        ("discoverable", "true" if DISCOVERABLE else "false"),
        ("indexable", "true" if INDEXABLE else "false"),
        ("bot", "true" if BOT else "false"),
    ]
    for i, (name, value) in enumerate(FIELDS):
        fields.append((f"fields_attributes[{i}][name]", name))
        fields.append((f"fields_attributes[{i}][value]", value))
    files = [("avatar", AVATAR), ("header", HEADER)]

    if DRY_RUN:
        print("[DRY-RUN] Würde folgendes Mastodon-Profil setzen (Premium-Agentur-Level):")
        print(f"  display_name ({len(DISPLAY_NAME)} Zeichen): {DISPLAY_NAME}")
        print(f"  note ({len(NOTE)} Zeichen):")
        for line in NOTE.splitlines():
            print(f"    | {line}")
        print(f"  Profilfelder ({len(FIELDS)}/{LIMITS['fields']}):")
        for n, v in FIELDS:
            print(f"    field: {n} = {v}")
        print(f"  discoverable: {DISCOVERABLE}  (Instanz-Verzeichnis)")
        print(f"  indexable:    {INDEXABLE}  (Fediverse-Suche)")
        print(f"  bot:          {BOT}  (False = persönlich antwortend, E-E-A-T)")
        print(f"  avatar: {AVATAR} ({'vorhanden' if AVATAR.is_file() else 'FEHLT'})")
        print(f"  header: {HEADER} ({'vorhanden' if HEADER.is_file() else 'FEHLT'})")
        print("")
        print("  Premium-Checks:")
        print(f"    - Affiliate-Disclosure in Bio: {'✅' if 'Affiliate' in NOTE else '❌'}")
        print(f"    - 25+ Guides erwähnt: {'✅' if '25+' in NOTE else '❌'}")
        print(f"    - 1.800€ Nutzenversprechen: {'✅' if '1.800' in NOTE else '❌'}")
        print(f"    - Mo/Mi/Fr Kadenz: {'✅' if 'Mo/Mi/Fr' in NOTE else '❌'}")
        print(f"    - Pinterest Cross-Promo Feld: {'✅' if any('Pinterest' in n for n,_ in FIELDS) else '❌'}")
        return

    body, boundary = build_multipart(fields, files)
    req = urllib.request.Request(
        f"{MASTODON_INSTANCE}/api/v1/accounts/update_credentials",
        data=body,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {MASTODON_TOKEN}",
            "Content-Type": f"multipart/form-data; boundary={boundary}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode()[:500]
        sys.exit(f"FEHLER: Mastodon-Profil-Update fehlgeschlagen: HTTP {exc.code}: {detail}")
    except Exception as exc:
        sys.exit(f"FEHLER: Mastodon-Profil-Update fehlgeschlagen: {exc}")

    print("✅ Mastodon-Profil aktualisiert:")
    print(f"  display_name: {data.get('display_name')}")
    print(f"  avatar: {data.get('avatar')}")
    print(f"  header: {data.get('header')}")

    print(f"  discoverable: {data.get('discoverable')}")
    print(f"  indexable: {data.get('indexable')}")
    for f in data.get("fields") or []:
        print(f"  field: {f.get('name')} = {f.get('value')}")

    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    # Nur bestätigte Server-Werte in den Report – nicht die lokalen Wunschwerte.
    field_rows = "\n".join(
        f"| {f.get('name')} | {f.get('value')} | {'✅' if f.get('verified_at') else '—'} |"
        for f in (data.get("fields") or [])
    ) or "| – | – | – |"
    bot_flag = data.get("bot")
    REPORT.write_text(
        "# 🐘 Mastodon-Profil-Sync – Premium-Agentur-Level\n\n"
        f"> Zuletzt synchronisiert: {now}\n\n"
        f"- **Anzeigename:** {data.get('display_name')}\n"
        f"- **Bio (Premium):** {data.get('note', '')[:500]}\n"
        f"- **Avatar:** {data.get('avatar')}\n"
        f"- **Header:** {data.get('header')}\n"
        f"- **Im Instanz-Verzeichnis (discoverable):** {data.get('discoverable')} – Reichweite\n"
        f"- **Für Suche freigegeben (indexable):** {data.get('indexable')} – Fediverse-SEO\n"
        f"- **Bot-Flag:** {bot_flag} – False = persönlich antwortend (E-E-A-T)\n\n"
        "## Profilfelder (max. 4 – Premium-Strategie)\n\n"
        "| Feld | Wert | Verifiziert |\n|---|---|---|\n"
        f"{field_rows}\n\n"
        "## Premium-Checks\n\n"
        f"- **Affiliate-Disclosure in Bio:** {'✅ enthalten (rechtssicher)' if 'Affiliate' in (data.get('note') or '') else '❌ fehlt'}\n"
        f"- **25+ Guides / 6 Welten:** {'✅' if '25+' in (data.get('note') or '') or '6 Welten' in (data.get('note') or '') else '—'}\n"
        f"- **1.800€ Nutzenversprechen:** {'✅' if '1.800' in (data.get('note') or '') else '—'}\n"
        f"- **Mo/Mi/Fr Kadenz:** {'✅' if 'Mo/Mi/Fr' in (data.get('note') or '') else '—'}\n"
        f"- **Pinterest Cross-Promo:** {'✅' if any('pinterest' in (f.get('value') or '').lower() for f in (data.get('fields') or [])) else '—'}\n"
        f"- **Themen-Hashtags optimiert:** {'✅' if any('Finanzen' in (f.get('value') or '') for f in (data.get('fields') or [])) else '—'}\n\n"
        "## Fehlende Blogbeiträge – Status\n\n"
        "Siehe `MASTODON-PREMIUM-ERGÄNZUNG.md` für die vollständige Backfill-Analyse (11 fehlende Artikel, Premium-Toots, Affiliate & Pinterest-Strategie).\n\n"
        "---\n"
        "*Erzeugt von scripts/mastodon_profile_sync.py – Premium-Agentur-Level (Bio 451/500 Zeichen, Affiliate-Transparenz, 25+ Guides, 1.800€-Claim, 6 Pillar, Mo/Mi/Fr, persönlich). "
        "Bewusst kein Cronjob, sondern manuell auslösbar über Actions → Mastodon-Profil-Sync → Run workflow, sobald sich Content-Fokus oder Branding erkennbar ändern.*\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
