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

DISPLAY_NAME = "FranksFinanzcheck 💰 Geld sparen"

NOTE = (
    "💰 Geld sparen ohne Verzicht: Ehrliche Ratgeber zu Strom, Gas, Internet & DSL, "
    "Versicherungen sowie Konto & Karten – verständlich erklärt, mit konkreten Zahlen "
    "und ohne Verkaufsdruck. Regelmäßig neue Artikel (mehrmals pro Woche) auf "
    "franksfinanzcheck.de. 🤖 Inhalte KI-unterstützt erstellt, automatisiert "
    "veröffentlicht und redaktionell geprüft. Fragen beantworte ich gerne persönlich!"
)

FIELDS = [
    ("Website:", "https://franksfinanzcheck.de"),
    ("Themen:", "#Strom #Gas #DSL #Versicherungen"),
]

AVATAR = ROOT / "static" / "images" / "social" / "mastodon-avatar.png"
HEADER = ROOT / "static" / "images" / "social" / "mastodon-header.png"
REPORT = ROOT / "MASTODON-PROFILE-REPORT.md"


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

    fields = [("display_name", DISPLAY_NAME), ("note", NOTE)]
    for i, (name, value) in enumerate(FIELDS):
        fields.append((f"fields_attributes[{i}][name]", name))
        fields.append((f"fields_attributes[{i}][value]", value))
    files = [("avatar", AVATAR), ("header", HEADER)]

    if DRY_RUN:
        print("[DRY-RUN] Würde folgendes Mastodon-Profil setzen:")
        print(f"  display_name ({len(DISPLAY_NAME)} Zeichen): {DISPLAY_NAME}")
        print(f"  note ({len(NOTE)} Zeichen): {NOTE}")
        for n, v in FIELDS:
            print(f"  field: {n} = {v}")
        print(f"  avatar: {AVATAR} ({'vorhanden' if AVATAR.is_file() else 'FEHLT'})")
        print(f"  header: {HEADER} ({'vorhanden' if HEADER.is_file() else 'FEHLT'})")
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

    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    REPORT.write_text(
        "# 🐘 Mastodon-Profil-Sync\n\n"
        f"> Zuletzt synchronisiert: {now}\n\n"
        f"- **Anzeigename:** {data.get('display_name')}\n"
        f"- **Bio:** {data.get('note', '')[:400]}\n"
        f"- **Avatar:** {data.get('avatar')}\n"
        f"- **Header:** {data.get('header')}\n\n"
        "---\n"
        "*Erzeugt von scripts/mastodon_profile_sync.py – bewusst kein Cronjob, "
        "sondern manuell auslösbar über Actions → Mastodon-Profil-Sync → Run workflow, "
        "sobald sich Content-Fokus oder Branding erkennbar ändern.*\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
