#!/usr/bin/env python3
"""
PINTEREST-PROFILE-AUDIT (Premium, 25.08.2026)
==============================================

Vergleicht das LIVE-Pinterest-Profil (de.pinterest.com/franksfinanzcheck)
mit dem Soll-Zustand aus `data/pinterest_profile_target.yaml` +
`data/pinterest_boards.yaml` und erzeugt einen Report mit
Copy-Paste-Anleitung für jede Abweichung.

Prüft (mit Token, API v5):
  A1  Display-Name      (full_name)       gegen Soll
  A2  Bio               (about)           gegen Soll (Keyword-Dichte,
                                          Affiliate-Offenlegung)
  A3  Website           (website_url)     gegen Soll
  A4  Board-Vollstand   alle 6 Premium-Boards vorhanden?
  A5  Board-Namen       exakte Übereinstimmung (SEO-Meeting-Point)
  A6  Board-Description  SEO-Texte wie im Soll (≤ 500 Zeichen)
  A7  Board-Fülle       min. 5 Pins je Board (leere Boards verwässern
                                          die Topical Authority)
  A8  Account-Typ       business

API v5 (WICHTIG, FIX 26.08.):
  - GET /v5/user_account  (NICHT /me – /me existiert in v5 nicht)
  - Profilfelder: full_name, about, website_url, account_type,
    username, profile_image, board_count, pin_count, follower_count
  - Die alten Schlüssel "description" und "website" gibt es in der
    /v5/user_account-Antwort nicht und würden immer leer bleiben.

Ohne Token (oder ohne profile:read-Scope):
  Der Audit liefert das komplette Copy-Paste-Paket aus dem
  Soll-Zustand als manuelle Checkliste – der Lauf bleibt grün
  (Konvention: Reporting, kein Fehler-Alerting).

API-Scopes: boards:read + boards:write (vorhanden) reichen für
Boards; für Name/Bio/Website zusätzlich `user_accounts:read` in der
Pinterest-Developer-App aktivieren (siehe ANLEITUNG-PINTEREST-API.md).

Ausgabe: PINTEREST-PROFILE-REPORT.md
Exit:    0 = ok (Reporting) · 2 = Selbsttest-Sabotage

Aufruf:
  python3 scripts/pinterest_profile_audit.py          # Audit
  python3 scripts/pinterest_profile_audit.py --json   # zusätzlich JSON
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import unicodedata
import urllib.error
import urllib.parse
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402

TARGET_FILE = os.path.join(BLOG_DIR, "data", "pinterest_profile_target.yaml")
BOARDS_FILE = os.path.join(BLOG_DIR, "data", "pinterest_boards.yaml")
REPORT = os.path.join(BLOG_DIR, "PINTEREST-PROFILE-REPORT.md")
API = "https://api.pinterest.com/v5"
PROFILE_URL = "https://de.pinterest.com/franksfinanzcheck/"
AS_JSON = "--json" in sys.argv

# v5-Feldnamen (Fix 26.08.): Der Namespace der /user_account-Antwort
# nutzt `about` und `website_url` – `description`/`website` existieren nicht.
USER_FIELDS = "full_name,about,website_url,account_type,username,board_count,pin_count,follower_count"

# Board-Cover-Zuordnung (Premium, 26.08.): Die Dateien liegen in
# static/images/boards/*.png und sind im Dashboard bei jeder Board-Bearbeitung
# als Cover hochzuladen. Name → Datei ist hier fest definiert (Single Source).
BOARD_COVERS = {
    "Geld sparen im Alltag | Frugalismus-Tipps": "images/boards/cover-geld-sparen.png",
    "Budget & Haushaltskasse: clever planen": "images/boards/cover-budget.png",
    "Strom & Gas sparen | Tarife clever wechseln": "images/boards/cover-strom-gas.png",
    "Internet & DSL | WLAN-Tipps & Tarife": "images/boards/cover-internet-dsl.png",
    "Günstig reisen | Reisebudget & Mietwagen": "images/boards/cover-reisen.png",
    "Versicherungen clever wechseln & sparen": "images/boards/cover-versicherungen.png",
}


# ---------------------------------------------------------------- Token
def get_token() -> str:
    env = os.environ.get("PINTEREST_ACCESS_TOKEN", "")
    if env:
        return env.strip()
    try:
        import pinterest_auth
        return (pinterest_auth.get_access_token() or "").strip()
    except Exception:
        return ""


# ---------------------------------------------------------------- API
def api_get(path: str, token: str) -> tuple[int, dict]:
    req = urllib.request.Request(f"{API}{path}",
                                 headers={"Authorization": f"Bearer {token}",
                                          "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            body = json.loads(e.read().decode() or "{}")
        except Exception:
            body = {}
        return e.code, body
    except Exception as e:  # noqa: BLE001
        return 0, {"error": str(e)}


# ---------------------------------------------------------------- Vergleich
def norm(s: str) -> str:
    s = unicodedata.normalize("NFKD", (s or "").strip())
    return " ".join(s.split())


def diff_status(actual: str, expected: str) -> tuple[bool, str]:
    a, e = norm(actual), norm(expected)
    if not e:
        return True, "keine Vorgabe"
    if a == e:
        return True, "identisch"
    if a:
        return False, "weich ab"
    return False, "leer"


# ---------------------------------------------------------------- Main
def main() -> int:
    if norm("x") != "x":
        print("🛑 SELBSTTEST fehlerhaft (Norm-Logik).")
        return 2

    target = yaml.safe_load(open(TARGET_FILE, encoding="utf-8")) or {}
    boards_cfg = (yaml.safe_load(open(BOARDS_FILE, encoding="utf-8")) or {}).get("boards", [])
    prof = target.get("profile", {})
    min_pins = int(target.get("min_pins_per_board", 5))

    token = get_token()
    mode = "LIVE-API"
    profile_live: dict = {}
    boards_live: list[dict] = []
    api_notes: list[str] = []

    if not token:
        mode = "MANUELL (kein Token)"
        api_notes.append("Kein PINTEREST_ACCESS_TOKEN/Tokens-Datei – "
                         "Copy-Paste-Checkliste unten (Dashboard-Abgleich).")
    else:
        st, me = api_get(f"/user_account?fields={urllib.parse.quote(USER_FIELDS)}", token)
        if st == 200:
            profile_live = me
        else:
            err = me.get("error") or me.get("message") or me.get("detail") or f"HTTP {st}"
            api_notes.append(f"/user_account nicht verfügbar ({err}). Name/Bio/Website "
                             "werden aus dem Soll-Zustand als Checkliste geliefert. "
                             "→ Scope `user_accounts:read` in der Pinterest-Developer-App "
                             "hinzufügen (ANLEITUNG-PINTEREST-API.md, Abschnitt Scopes).")
        st, boards_resp = api_get("/boards?page_size=100&board_fields=id,name,description,pins_count", token)
        if st == 200:
            boards_live = boards_resp.get("items", [])
        else:
            api_notes.append(f"/boards nicht verfügbar (HTTP {st}) – Board-Prüfung nur per Soll-Zustand.")

    # ---------------- A1–A3 Profil
    checks: list[tuple[str, str, bool, str, str, str]] = []  # code, name, ok, status, aktuell, soll
    a_ok, a_st = diff_status(profile_live.get("full_name", ""), prof.get("display_name", ""))
    checks.append(("A1", "Display-Name", a_ok, a_st, profile_live.get("full_name", "–"), prof.get("display_name", "")))
    b_ok, b_st = diff_status(profile_live.get("about", ""), prof.get("bio", ""))
    checks.append(("A2", "Bio (500 Z.)", b_ok, b_st, (profile_live.get("about", "–") or "–")[:120], prof.get("bio", "")))
    c_ok, c_st = diff_status(profile_live.get("website_url", ""), prof.get("website", ""))
    checks.append(("A3", "Website", c_ok, c_st, profile_live.get("website_url", "–") or "–", prof.get("website", "")))
    acct = profile_live.get("account_type", "")
    if acct:
        checks.append(("A8", "Account-Typ", acct.lower() == "business",
                       acct or "–", acct or "–", "business"))
    # Counts (pure Info, machen das Profil-Leistungsbild im Report sichtbar)
    profile_stats = {
        "username": profile_live.get("username", "–"),
        "board_count": profile_live.get("board_count", "–"),
        "pin_count": profile_live.get("pin_count", "–"),
        "follower_count": profile_live.get("follower_count", "–"),
    }

    # ---------------- A4–A7 Boards
    live_by_name = {}
    for b in boards_live:
        live_by_name[norm(b.get("name", ""))] = b
    board_rows = []
    for exp in boards_cfg:
        name = exp["name"]
        live = live_by_name.get(norm(name))
        if live is None:
            board_rows.append({"name": name, "status": "FEHLT", "desc_ok": False,
                               "pins": None, "desc_live": ""})
            continue
        d_ok, d_st = diff_status(live.get("description", ""), exp.get("description", ""))
        pins = live.get("pins_count")
        board_rows.append({
            "name": name,
            "status": "OK" if d_ok else "DESC-ABWEICHUNG",
            "desc_ok": d_ok,
            "desc_status": d_st,
            "pins": pins,
            "desc_live": (live.get("description") or "")[:120],
        })
        if d_ok and pins is not None and pins < min_pins:
            board_rows[-1]["status"] = f"ZU LEER ({pins} < {min_pins} Pins)"
    extra = [b for b in boards_live if norm(b.get("name", "")) not in {norm(x["name"]) for x in boards_cfg}]

    # ---------------- Report
    now = dt.datetime.now(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    n_issues = sum(1 for c in checks if not c[2]) + sum(1 for r in board_rows if r["status"] != "OK") + len(extra)
    lines = [
        "# 🏆 PINTEREST-PROFILE-REPORT (Premium-Profil-Audit)",
        "",
        f"**Profil:** [{PROFILE_URL}]({PROFILE_URL}) · **Stand:** {now} · **Modus:** {mode}",
        "",
        f"**Abweichungen:** {n_issues} · **Soll-Zustand:** `data/pinterest_profile_target.yaml` + `data/pinterest_boards.yaml`",
        "",
    ]
    if api_notes:
        lines += ["## API-Hinweise", ""] + [f"- {n}" for n in api_notes] + [""]

    lines += ["## Profil", "", "| Check | Status | Aktuell | Soll |", "|---|---|---|---|"]
    for code, name, ok, status, act, soll in checks:
        lines.append(f"| {code} {name} | {'✅' if ok else '❌'} {status} | {act[:80]} | {soll[:80]} |")
    # Profil-Kennzahlen nur als Info-Zeile, wenn LIVE-API (sonst kein Wert).
    if mode == "LIVE-API":
        lines += ["", "### Live-Kennzahlen", "",
                  f"- **Username:** {profile_stats.get('username', '–')}",
                  f"- **Boards:** {profile_stats.get('board_count', '–')}",
                  f"- **Pins:** {profile_stats.get('pin_count', '–')}",
                  f"- **Follower:** {profile_stats.get('follower_count', '–')}",
                  ""]
    lines += ["", "## Boards", "", "| Board | Status | Pins | Beschreibung (Live) |", "|---|---|---|---|"]
    for r in board_rows:
        lines.append(f"| {r['name']} | {'✅' if r['status'] == 'OK' else '❌'} {r['status']} | {r['pins'] if r['pins'] is not None else '–'} | {r.get('desc_live', '')} |")
    for b in extra:
        lines.append(f"| {b.get('name', '?')} | ⚠️ UNERWARTET (nicht im Soll) | {b.get('pins_count', '–')} | {(b.get('description') or '')[:80]} |")

    # ---------------- Copy-Paste (nur bei Abweichungen oder ohne Live-Daten)
    needs_manual = (not token) or any(not c[2] for c in checks) or any(r["status"] != "OK" for r in board_rows) or bool(extra)
    if needs_manual:
        lines += ["", "## 📋 Copy-Paste (Dashboard → Einstellungen → Öffentliches Profil bearbeiten / Board-Bearbeitung)", ""]
        lines.append(f"**Anzeigename:** `{prof.get('display_name', '')}`")
        lines.append("")
        lines.append("**Bio:**")
        lines.append("```")
        lines.append(prof.get("bio", ""))
        lines.append("```")
        lines.append("")
        lines.append(f"**Website:** `{prof.get('website', '')}`")
        lines.append("")
        lines.append("**Board-Namen + Beschreibungen** (Board → Bearbeiten):")
        for b in boards_cfg:
            lines.append("")
            lines.append(f"### {b['name']}")
            lines.append("```")
            lines.append(b.get("description", ""))
            lines.append("```")
            cover = BOARD_COVERS.get(b["name"])
            if cover:
                lines.append("")
                lines.append(f"**Board-Cover:** `static/{cover}` "
                             "(als Cover-Bild in der Board-Bearbeitung hochladen)")
        if extra:
            lines.append("")
            lines.append("**Boards auflösen/umbenennen** (nicht im Soll-Zustand): "
                         + ", ".join(f"„{b.get('name', '?')}" for b in extra))

    lines += [
        "",
        "## Manuelle Checkpunkte (nicht per API prüfbar)",
        "",
        "- [ ] Profilbild: `static/images/social/pinterest-profilbild-marke-1000.png` (Foto + Gold-Ring + Badge) hochgeladen",
        "- [ ] Board-Cover: 6er-Set hochgeladen (Zuordnung siehe Board-Liste oben)",
        "- [ ] Business-Account aktiv (Einstellungen → Konto) – Anzeigename/Bio/Website nur im Business-Konto voll editierbar",
        "- [ ] Verifizierte Website: `franksfinanzcheck.de` (Claim-Datei + `p:domain_verify` liegen live)",
        "- [ ] Rich Pins aktiviert (1× validieren: developers.pinterest.com/tools/url-debugger)",
        "", "## Board-Cover-Zuordnung (Premium, 26.08.2026)", "",
        *[f"- **{name}** → `static/{cover}`" for name, cover in BOARD_COVERS.items()],
        "",
        "---",
        "",
        "_Erzeugt von `scripts/pinterest_profile_audit.py`._",
        "",
    ]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))

    print(f"Profile-Audit ({mode}): {n_issues} Abweichungen. Report: {os.path.relpath(REPORT, BLOG_DIR)}")
    for c in checks:
        if not c[2]:
            print(f"  ❌ {c[0]} {c[1]}: {c[3]}")
    for r in board_rows:
        if r["status"] != "OK":
            print(f"  ❌ Board {r['name']}: {r['status']}")
    if AS_JSON:
        print(json.dumps({"checks": checks, "boards": board_rows, "extra": extra}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
