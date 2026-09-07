#!/usr/bin/env python3
"""
PINTEREST-AUTH – automatische Token-Erneuerung (OAuth 2.0)
============================================================

WARUM (offizielle Pinterest-Doku):
  - Access-Token (pina_...) laufen nach **30 Tagen** ab.
  - Bei Apps, die ab 25.09.2025 erstellt wurden, gibt es den
    **„continuous refresh token"** (pinr_...): 60 Tage gültig, wird aber
    BEI JEDER ERNEUERUNG neu ausgestellt -> praktisch unbegrenzt nutzbar,
    solange die Automatisierung regelmäßig läuft (unsere: 2x täglich).
  - Darum: Bei jedem Lauf wird der Token proaktiv erneuert. Kein manuelles
    Eingreifen mehr nötig, kein monatliches Abdrehen des Pin-Bots.

SPEICHERUNG:
  - Tokens liegen AES-256-GCM-verschlüsselt in **data/pinterest_tokens.enc**
    (wird mit-committet; ohne Schlüssel unlesbar – das Repo ist öffentlich!).
  - Der Schlüssel liegt als GitHub-Secret **PINTEREST_TOKEN_KEY**
    (lange zufällige Zeichenkette) – NIE im Repo, NIE im Klartext.
  - Fallback: Wenn keine Token-Datei existiert, wird weiterhin das
    klassische Secret PINTEREST_ACCESS_TOKEN verwendet (altes Verhalten).

NUTZUNG (einmalige Ersteinrichtung, Schritt 3-4 der Anleitung):
  1) Autorisierungs-URL erzeugen:
       python3 scripts/pinterest_auth.py --auth-url
       (liest App-ID aus PINTEREST_APP_ID)
  2) URL im Browser öffnen, erlauben, aus der Adresszeile den Code
     kopieren (?code=...) und austauschen:
       PINTEREST_APP_ID=... PINTEREST_APP_SECRET=... PINTEREST_TOKEN_KEY=... \
       python3 scripts/pinterest_auth.py --exchange <CODE>
  3) data/pinterest_tokens.enc committen (verschlüsselt – sicher).
  4) Status prüfen: python3 scripts/pinterest_auth.py --status
"""

import base64
import hashlib
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / "data" / "pinterest_tokens.enc"
OAUTH_URL = "https://api.pinterest.com/v5/oauth/token"
AUTHORIZE_URL = "https://www.pinterest.com/oauth/"
REDIRECT_URI = "https://franksfinanzcheck.de/pinterest-oauth"
# read_ads = PIN-ANALYTICS/Pin-Metriken (Impressions, Outbound-Clicks, Saves)
# für die Performance-Feedback-Schleife. Ohne diesen Scope liefert die API v5
# keine Pin-Metriken. Die anderen Scopes bleiben für Board-/Pin-Verwaltung.
SCOPES = "boards:read,boards:write,pins:read,pins:write,read_ads"


# ------------------------------------------------------------ Krypto (AES-GCM)

def _key_bytes() -> bytes:
    key = os.environ.get("PINTEREST_TOKEN_KEY", "").strip()
    if len(key) < 16:
        sys.exit("FEHLER: Umgebungsvariable PINTEREST_TOKEN_KEY fehlt oder zu kurz "
                 "(min. 16 Zeichen, als GitHub-Secret hinterlegen).")
    return hashlib.sha256(key.encode("utf-8")).digest()


def _save(token_data: dict) -> None:
    """Verschlüsselt das Token-Paket und schreibt data/pinterest_tokens.enc."""
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    token_data["saved_at"] = datetime.now(timezone.utc).isoformat()
    nonce = os.urandom(12)
    blob = AESGCM(_key_bytes()).encrypt(nonce, json.dumps(token_data).encode(), None)
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    TOKEN_FILE.write_bytes(nonce + blob)
    print(f"💾 Tokens verschlüsselt gespeichert: {TOKEN_FILE.relative_to(ROOT)}")


def _load() -> dict | None:
    """Liest und entschlüsselt das Token-Paket (None, wenn nicht vorhanden).

    Bei fehlendem/falschem Schlüssel wird NICHT mehr das ganze Skript
    beendet (SystemExit), sondern None zurückgegeben – die Pinterest-Engine
    fällt dann sauber auf den klassischen Env-Token (PINTEREST_ACCESS_TOKEN)
    zurück. Nur der explizite CLI-Status-Befehl alarmiert weiterhin.
    """
    if not TOKEN_FILE.exists():
        return None
    try:
        _key_bytes()
    except SystemExit:
        # Kein Schlüssel im Env: das ist eine Konfigurationslage, kein Absturz.
        # Der Broker (scripts/pinterest_token.py) fällt sauber auf die nächste
        # Quelle zurück – Härtung aus #206.
        return None
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = TOKEN_FILE.read_bytes()
    try:
        return json.loads(AESGCM(_key_bytes()).decrypt(raw[:12], raw[12:], None))
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ data/pinterest_tokens.enc nicht entschlüsselbar "
              f"(falscher PINTEREST_TOKEN_KEY?) – nutze Env-Token: {exc}")
        return None


# Öffentliche, stabile Namen für den Token-Broker (scripts/pinterest_token.py).
# Der Broker kennt die Krypto-Details bewusst nicht – hier liegt die einzige
# Stelle, die verschlüsselt liest und schreibt.
def load_store() -> dict | None:
    """Entschlüsselter Token-Bestand oder None."""
    return _load()


def save_store(data: dict) -> None:
    """Token-Bestand verschlüsselt schreiben (rotierter Refresh-Token!)."""
    _save(data)


# ---------------------------------------------------------------- OAuth-Calls

def _oauth_post(data: dict, app_id: str, app_secret: str) -> dict:
    basic = base64.b64encode(f"{app_id}:{app_secret}".encode()).decode()
    req = urllib.request.Request(
        OAUTH_URL,
        data=urllib.parse.urlencode(data).encode(),
        headers={
            "Authorization": f"Basic {basic}",
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        body = exc.read().decode()[:300]
        raise RuntimeError(f"OAuth-Fehler (HTTP {exc.code}): {body}") from exc


def refresh_tokens(data: dict) -> dict:
    """Erneuert Access- UND Refresh-Token (continuous refresh)."""
    resp = _oauth_post(
        {"grant_type": "refresh_token", "refresh_token": data["refresh_token"]},
        data["app_id"], data["app_secret"],
    )
    data["access_token"] = resp["access_token"]
    if resp.get("refresh_token"):
        data["refresh_token"] = resp["refresh_token"]  # neuer 60-Tage-Refresh-Token!
    return data


# ------------------------------------------------------------- Öffentliche API

def get_access_token() -> str | None:
    """Gibt einen GÜLTIGEN Access-Token zurück (erneuert ihn bei Bedarf).

    ALTLAST-SCHNITTSTELLE (seit 07.09.2026, #206): Die Entscheidung, WELCHE
    Quelle gilt, trifft nur noch der Broker `scripts/pinterest_token.py`.
    Diese Funktion bleibt bestehen, damit älterer Code weiterläuft – sie
    delegiert aber vollständig.

    Warum das wichtig ist: Vorher hat diese Funktion bei JEDEM Aufruf blind
    einen Refresh ausgelöst. Der Refresh-Token rotiert dabei; zwei parallele
    Läufe konnten sich gegenseitig aussperren. Der Broker erneuert nur, wenn
    es nötig ist – unter Dateisperre.
    """
    try:
        import pinterest_token          # lazy: verhindert Zirkel-Import
        return pinterest_token.get_token()
    except Exception as exc:  # noqa: BLE001 – nie den Aufrufer mitreißen
        print(f"⚠ Token-Broker nicht verfügbar ({exc.__class__.__name__}) – "
              f"nutze den Bestand ohne Erneuerung.")
        data = _load() or {}
        return data.get("access_token") or os.environ.get("PINTEREST_ACCESS_TOKEN") or None


def refresh_now() -> int:
    """CLI-Pfad: Erneuerung erzwingen (Token-Wache, täglich)."""
    import pinterest_token
    health = pinterest_token.resolve(force_refresh=True)
    pinterest_token.save_state(health)
    print(pinterest_token.describe(health))
    return 0 if health.get("state") == "live" else 1


# ------------------------------------------------------------------- CLI-Teil

def print_auth_url() -> None:
    app_id = os.environ.get("PINTEREST_APP_ID", "").strip()
    if not app_id:
        sys.exit("FEHLER: PINTEREST_APP_ID nicht gesetzt "
                 "(steht im Pinterest-Dashboard unter My apps).")
    params = {
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
    }
    print("\n🌐 Diese URL im Browser öffnen (mit dem Pinterest-Konto eingeloggt):\n")
    print(f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}\n")
    print("Nach dem Erlauben landest du auf einer Pinterest-404-Seite – egal!")
    print(f"Kopiere aus der Adresszeile den Teil nach ?code= (bis vor &state=)")
    print("und übergib ihn an: python3 scripts/pinterest_auth.py --exchange <CODE>\n")
    print(f"HINWEIS: Die Redirect-URI muss in der App hinterlegt sein: {REDIRECT_URI}")


def exchange_code(code: str) -> None:
    app_id = os.environ.get("PINTEREST_APP_ID", "").strip()
    app_secret = os.environ.get("PINTEREST_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        sys.exit("FEHLER: PINTEREST_APP_ID und PINTEREST_APP_SECRET nötig.")
    resp = _oauth_post(
        {"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
        app_id, app_secret,
    )
    now = datetime.now(timezone.utc).isoformat()
    data = {
        "app_id": app_id,
        "app_secret": app_secret,
        "access_token": resp["access_token"],
        "refresh_token": resp["refresh_token"],
        # Zeitstempel sind Pflicht: der Broker rechnet daraus die Restlaufzeit
        # aus und erneuert PROAKTIV, statt auf den ersten 401 zu warten (#206).
        "refreshed_at": now,
        "refresh_rotated_at": now,
    }
    _save(data)
    print("✅ Pinterest-Autorisierung abgeschlossen!")
    print("   Access-Token gültig: 30 Tage | Refresh: automatisch bei jedem Bot-Lauf")
    print("   JETZT (einmalig): git add data/pinterest_tokens.enc && git commit && git push")


def print_status() -> None:
    data = _load()
    if not data:
        print("Keine Token-Datei (data/pinterest_tokens.enc) vorhanden.")
        print("→ Lagebild des gesamten Zugangs (alle Quellen): "
              "python3 scripts/pinterest_token.py --status")
        return
    print(f"✔ Token-Datei vorhanden, gespeichert: {data.get('saved_at', '?')}")
    print(f"✔ App-ID: {data.get('app_id')}")
    print(f"✔ Scopes vorhanden: {data.get('access_token', '(leer)')[:12]}… (pina_…) / "
          f"{data.get('refresh_token', '(leer)')[:12]}… (pinr_…)")


if __name__ == "__main__":
    if "--auth-url" in sys.argv:
        print_auth_url()
    elif "--exchange" in sys.argv:
        idx = sys.argv.index("--exchange")
        if idx + 1 >= len(sys.argv):
            sys.exit("FEHLER: --exchange <CODE> erwartet einen Code.")
        exchange_code(sys.argv[idx + 1])
    elif "--status" in sys.argv:
        print_status()
    elif "--refresh" in sys.argv:
        sys.exit(refresh_now())
    else:
        print(__doc__)
