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
  2) URL im Browser öffnen, erlauben – die Seite franksfinanzcheck.de/pinterest-oauth
     zeigt den Code an (oder Adresszeile: ?code=...). Austauschen:
       PINTEREST_APP_ID=... PINTEREST_APP_SECRET=... PINTEREST_TOKEN_KEY=... \
       python3 scripts/pinterest_auth.py --exchange <CODE-oder-komplette-URL>
     (im Workflow: Feld `auth_code` der Pinterest-Token-Wache)
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TOKEN_FILE = ROOT / "data" / "pinterest_tokens.enc"
OAUTH_URL = "https://api.pinterest.com/v5/oauth/token"
AUTHORIZE_URL = "https://www.pinterest.com/oauth/"
REDIRECT_URI = "https://franksfinanzcheck.de/pinterest-oauth"
# SCOPES (korrigiert 08.09.2026, #219) – exakt die v5-Namen, minimal, vollständig:
#   boards:read/write, pins:read/write → Pinnen, Boards, Dedup (Live-Pins lesen)
#   user_accounts:read                 → /v5/user_account: Live-Probe des Brokers
#                                        + Profil-Audit (Name/Bio/Website)
# Pin-Analytics (/v5/pins/{id}/analytics) braucht laut Pinterest-Doku NUR
# boards:read + pins:read. Der frühere Eintrag `read_ads` ist KEIN v5-Scope
# (v5 kennt `ads:read`) – ein unbekannter oder für die App nicht freigegebener
# Scope lässt die Autorisierungsseite mit einem Fehler abbrechen, ohne dass
# der Nutzer versteht, warum. Genau so scheitern Neu-Autorisierungen still.
# Überschreibbar per Env PINTEREST_SCOPES (z. B. zusätzlich `ads:read`).
DEFAULT_SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"
SCOPES = os.environ.get("PINTEREST_SCOPES", "").strip().replace(" ", ",") or DEFAULT_SCOPES


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

def build_auth_url(app_id: str, state: str = "") -> str:
    params = {
        "client_id": app_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "scope": SCOPES,
    }
    if state:
        params["state"] = state
    return f"{AUTHORIZE_URL}?{urllib.parse.urlencode(params)}"


def extract_code(raw: str) -> str:
    """Nimmt alles, was ein Mensch nach der Autorisierung einfügt, und liefert
    den nackten Code: die komplette Redirect-URL, `code=…&state=…`, den Code
    mit angehängtem `&state=`, mit Anführungszeichen oder Leerzeichen.

    Hintergrund (#219): Zwei Neu-Autorisierungsversuche am 07.09.2026 scheiterten
    im Schritt „Code → Token" – ein falsch ausgeschnittener Code ist dafür die
    häufigste Ursache, und die Fehlermeldung sagte dazu nichts.
    """
    txt = (raw or "").strip().strip("\"'\u201c\u201d\u201e").strip()
    if not txt:
        return ""
    if "://" in txt or "?" in txt or "code=" in txt:
        query = txt.split("?", 1)[1] if "?" in txt else txt
        query = query.split("#", 1)[0]
        for key, val in urllib.parse.parse_qsl(query, keep_blank_values=True):
            if key == "code":
                return val.strip()
        # kein `code=` gefunden, aber URL-artig → nichts erraten
        return ""
    return txt.split("&", 1)[0].strip()


def print_auth_url() -> None:
    app_id = os.environ.get("PINTEREST_APP_ID", "").strip()
    if not app_id:
        sys.exit("FEHLER: PINTEREST_APP_ID nicht gesetzt "
                 "(steht im Pinterest-Dashboard unter My apps).")
    state = "ffc" + datetime.now(timezone.utc).strftime("%Y%m%d%H%M")
    print("\n🌐 Diese URL im Browser öffnen (mit dem Pinterest-Konto eingeloggt):\n")
    print(build_auth_url(app_id, state) + "\n")
    print("Nach dem Erlauben landest du auf franksfinanzcheck.de/pinterest-oauth –")
    print("die Seite zeigt den Code groß an (Kopier-Knopf). Alternativ steht er in")
    print("der Adresszeile hinter ?code= (bis vor &state=).")
    print("Danach: Actions → Pinterest-Token-Wache → Run workflow → Feld auth_code.")
    print("(Du darfst auch die komplette Adresszeile einfügen – der Code wird erkannt.)\n")
    print(f"Scopes: {SCOPES}")
    print(f"HINWEIS: Die Redirect-URI muss in der App hinterlegt sein: {REDIRECT_URI}")
    print("Der Code ist nur wenige Minuten und genau EINMAL gültig – zügig eintauschen.")


def _explain_exchange_error(exc: Exception) -> str:
    """Aus dem OAuth-Fehler eine Handlungsanweisung machen (kein Secret-Material)."""
    msg = str(exc)
    if "HTTP 400" in msg or "invalid_grant" in msg or "invalid_request" in msg:
        return ("Pinterest hat den Code abgelehnt (HTTP 400). Drei Ursachen, in dieser "
                "Reihenfolge prüfen: (1) Code ist abgelaufen oder wurde schon einmal "
                "eingetauscht – jeder Code gilt nur Minuten und genau EINMAL → neue URL "
                "holen, erneut erlauben, neuen Code sofort einfügen. (2) Code falsch "
                "ausgeschnitten → einfach die komplette Adresszeile einfügen. (3) Die "
                f"Redirect-URI der App ist nicht exakt `{REDIRECT_URI}` (ohne Slash am Ende).")
    if "HTTP 401" in msg:
        return ("Pinterest lehnt die App-Zugangsdaten ab (HTTP 401): PINTEREST_APP_ID / "
                "PINTEREST_APP_SECRET prüfen (Developer-Portal → My apps → App secret; "
                "nach einem Reset des Secrets gilt nur noch das neue).")
    if "HTTP 403" in msg:
        return ("Pinterest verweigert die App (HTTP 403): App noch nicht freigegeben "
                "(Trial access ausstehend) oder ein angeforderter Scope ist für die App "
                "nicht aktiviert (Developer-Portal → App → Scopes). "
                f"Aktuell angefordert: {SCOPES}")
    if "HTTP 429" in msg:
        return "Pinterest-Rate-Limit (HTTP 429) – in ein paar Minuten erneut versuchen."
    return "Unerwarteter OAuth-Fehler – Netz/Proxy prüfen und erneut versuchen."


def exchange_code(code: str) -> None:
    app_id = os.environ.get("PINTEREST_APP_ID", "").strip()
    app_secret = os.environ.get("PINTEREST_APP_SECRET", "").strip()
    if not app_id or not app_secret:
        sys.exit("FEHLER: PINTEREST_APP_ID und PINTEREST_APP_SECRET nötig.")
    _key_bytes()   # früh scheitern: ohne Schlüssel wäre der Tausch verschwendet
    clean = extract_code(code)
    if not clean:
        sys.exit("FEHLER: Kein Autorisierungs-Code erkannt. Erwartet wird der Wert "
                 "hinter `?code=` – oder einfach die komplette Adresszeile.")
    if clean != (code or "").strip():
        print("ℹ️  Code aus der Eingabe herausgelöst (URL/Anführungszeichen/&state entfernt).")
    try:
        resp = _oauth_post(
            {"grant_type": "authorization_code", "code": clean,
             "redirect_uri": REDIRECT_URI,
             # Für Apps von vor dem 25.09.2025 nötig, für neuere wirkungslos –
             # ohne den Schalter gäbe es dort den alten 365-Tage-Token ohne
             # Rotation, und der Kanal stürbe nach einem Jahr endgültig.
             "continuous_refresh": "true"},
            app_id, app_secret,
        )
    except RuntimeError as exc:
        print(f"❌ {exc}")
        print(f"→ {_explain_exchange_error(exc)}")
        sys.exit(1)
    if not resp.get("access_token") or not resp.get("refresh_token"):
        sys.exit("FEHLER: Pinterest lieferte keinen vollständigen Token-Satz "
                 f"(Felder: {', '.join(sorted(resp))}).")
    now = datetime.now(timezone.utc)
    data = {
        "app_id": app_id,
        "app_secret": app_secret,
        "access_token": resp["access_token"],
        "refresh_token": resp["refresh_token"],
        # Zeitstempel sind Pflicht: der Broker rechnet daraus die Restlaufzeit
        # aus und erneuert PROAKTIV, statt auf den ersten 401 zu warten (#206).
        "refreshed_at": now.isoformat(),
        "refresh_rotated_at": now.isoformat(),
        "scope": str(resp.get("scope") or SCOPES.replace(",", " ")),
        "authorized_at": now.isoformat(),
    }
    try:
        if resp.get("refresh_token_expires_in"):
            data["refresh_expires_at"] = (
                now + timedelta(seconds=int(resp["refresh_token_expires_in"]))).isoformat()
    except (TypeError, ValueError):
        pass
    _save(data)
    granted = set(data["scope"].replace(",", " ").split())
    wanted = set(SCOPES.replace(",", " ").split())
    print("✅ Pinterest-Autorisierung abgeschlossen!")
    print(f"   Scopes erteilt: {' '.join(sorted(granted))}")
    if wanted - granted:
        print(f"   ⚠️ nicht erteilt: {' '.join(sorted(wanted - granted))} – im Developer-Portal "
              "für die App aktivieren und einmal neu autorisieren.")
    print("   Access-Token gültig: 30 Tage | Refresh-Token: 60 Tage, rotiert täglich (Wache)")
    if os.environ.get("GITHUB_ACTIONS"):
        print("   Der Workflow committet data/pinterest_tokens.enc jetzt automatisch.")
    else:
        print("   JETZT (einmalig): git add data/pinterest_tokens.enc && git commit && git push")


def print_status() -> None:
    data = _load()
    if not data:
        print("Keine Token-Datei (data/pinterest_tokens.enc) vorhanden.")
        print("→ Lagebild des gesamten Zugangs (alle Quellen): "
              "python3 scripts/pinterest_token.py --status")
        return
    # Kein Token-Material ausgeben – auch keine Präfixe (#219: Logs sind öffentlich).
    print(f"✔ Token-Datei vorhanden, gespeichert: {data.get('saved_at', '?')}")
    print(f"✔ App-ID: {data.get('app_id')}")
    print(f"✔ Scopes: {data.get('scope') or '(unbekannt – vor 08.09.2026 autorisiert)'}")
    print(f"✔ Zuletzt erneuert: {data.get('refreshed_at', '?')} · Refresh rotiert: "
          f"{data.get('refresh_rotated_at', '?')} · Ablauf Refresh: "
          f"{data.get('refresh_expires_at', 'unbekannt')}")
    print(f"✔ Access-Token: {'vorhanden' if data.get('access_token') else 'FEHLT'} · "
          f"Refresh-Token: {'vorhanden' if data.get('refresh_token') else 'FEHLT'}")


def _selftest() -> int:
    """Offline-Fälle für die Eingabe-Toleranz und die Fehlerdiagnose."""
    fails = []
    url = "https://franksfinanzcheck.de/pinterest-oauth?code=abc123XYZ&state=ffc2026"
    cases = {
        url: "abc123XYZ",
        "https://franksfinanzcheck.de/pinterest-oauth/?code=abc123XYZ": "abc123XYZ",
        "code=abc123XYZ&state=ffc2026": "abc123XYZ",
        "abc123XYZ&state=ffc2026": "abc123XYZ",
        '  "abc123XYZ"  ': "abc123XYZ",
        "abc123XYZ": "abc123XYZ",
        "https://franksfinanzcheck.de/pinterest-oauth?error=access_denied": "",
        "": "",
    }
    for raw, want in cases.items():
        got = extract_code(raw)
        if got != want:
            fails.append(f"extract_code({raw!r}) = {got!r}, erwartet {want!r}")
    if "read_ads" in DEFAULT_SCOPES or "user_accounts:read" not in DEFAULT_SCOPES:
        fails.append("Scopes: `read_ads` ist kein v5-Scope / `user_accounts:read` fehlt "
                     "(Broker-Probe /user_account würde 403 liefern)")
    for tok in DEFAULT_SCOPES.split(","):
        if ":" not in tok:
            fails.append(f"Scope-Syntax ungültig: {tok}")
    u = build_auth_url("123", "st")
    if "client_id=123" not in u or "response_type=code" not in u or "state=st" not in u \
            or urllib.parse.quote(REDIRECT_URI, safe="") not in u:
        fails.append("Autorisierungs-URL unvollständig")
    if "einmal" not in _explain_exchange_error(RuntimeError("OAuth-Fehler (HTTP 400): x")).lower():
        fails.append("400-Diagnose erklärt nicht, dass Codes einmalig sind")
    if "APP_SECRET" not in _explain_exchange_error(RuntimeError("OAuth-Fehler (HTTP 401): x")):
        fails.append("401-Diagnose zeigt nicht auf die App-Zugangsdaten")
    if "Scope" not in _explain_exchange_error(RuntimeError("OAuth-Fehler (HTTP 403): x")):
        fails.append("403-Diagnose zeigt nicht auf Freigabe/Scopes")
    if fails:
        print("❌ PINTEREST-AUTH-SELFTEST FEHLGESCHLAGEN:")
        for f in fails:
            print("   -", f)
        return 2
    print("✅ PINTEREST-AUTH-SELFTEST bestanden (Code-Erkennung, v5-Scopes, URL, Diagnose).")
    return 0


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        sys.exit(_selftest())
    elif "--auth-url" in sys.argv:
        print_auth_url()
    elif "--exchange" in sys.argv:
        # Code bevorzugt aus dem Env (PINTEREST_AUTH_CODE): erscheint so weder in
        # `ps` noch im Workflow-Log, und ein Sonderzeichen kann keine Shell brechen.
        idx = sys.argv.index("--exchange")
        code = os.environ.get("PINTEREST_AUTH_CODE", "").strip()
        if idx + 1 < len(sys.argv) and not sys.argv[idx + 1].startswith("--"):
            code = sys.argv[idx + 1]
        if not code:
            sys.exit("FEHLER: --exchange <CODE> erwartet einen Code "
                     "(oder Env PINTEREST_AUTH_CODE).")
        exchange_code(code)
    elif "--status" in sys.argv:
        print_status()
    elif "--refresh" in sys.argv:
        sys.exit(refresh_now())
    else:
        print(__doc__)
