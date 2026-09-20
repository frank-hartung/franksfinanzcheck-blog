#!/usr/bin/env python3
"""
MARKE IM REPO-KOPF – Beschreibung, Homepage, Wiki, Themen, Sichtbarkeit
=======================================================================

WARUM ES DIESE DATEI GIBT (20.09.2026)
--------------------------------------
Die Marken-Oberflächen-Wache (`scripts/brand_surface_guard.py`) hält die
Außenseite des Repos sauber – aber drei Dinge davon kann die Automatik
nicht selbst ändern: die **Repo-Beschreibung** („(Affiliate-Blog, Hugo)",
sie erscheint in Suchergebnissen), die fehlende **Homepage-URL**, das
**Wiki** als zweite ungepflegte Textfläche – und die **Sichtbarkeit** des
Repositories selbst. Dafür fehlt dem Automatik-Token das Admin-Recht.

Dieses Skript macht genau diese vier Admin-Griffe in EINEM Aufruf –
schreibfrei planbar (`--dry-run`, Standard) und mit Prüfung danach
(`--apply`). Es schreibt nur, was es vorher angezeigt hat.

WAS ES SETZT (Vorschlagswerte, änderbar)
----------------------------------------
  · Beschreibung   „FranksFinanzcheck – unabhängiger Finanz-Ratgeber von
                    Frank Hartung: Strom, Gas, DSL, Versicherungen, Sparen."
  · Homepage       https://franksfinanzcheck.de/
  · Wiki           aus
  · Themen         geld-sparen, finanzen, frugalismus, stromvergleich,
                   versicherungen, ratgeber
  · Sichtbarkeit   nur mit `--privat`: Repository privat (siehe Vorsicht unten)

VORSICHT BEI `--privat` (deshalb nicht Standard)
------------------------------------------------
GitHub Pages aus einem **privaten** Repository gibt es erst mit GitHub Pro/
Team. Auf dem kostenlosen Plan geht die Website offline, sobald das Repo
privat wird. Dieses Skript prüft das nach dem Umschalten live: Ist
https://franksfinanzcheck.de/ danach nicht mehr erreichbar, schaltet es
selbst zurück auf öffentlich und sagt, welcher Weg stattdessen trägt
(Entscheidungsmatrix in docs/MARKEN-OBERFLAECHE-RUNBOOK.md, Wege A/B1/B2).

FAHRPLAN (was ein Lauf tut)
---------------------------
  1. Zustand lesen  (GET /repos/{owner}/{repo}) – inkl. `viewer_can_administer`
  2. Plan anzeigen  (Nur-Differenz: was ist, was soll)
  3. Schreiben      (nur mit --apply, ein PATCH je Bereich)
  4. Nachlesen      (jede Änderung wird aus der API zurückgelesen)
  5. Markenfläche   (brand_surface_guard.py --gate)
  6. Website        (nur bei --privat: HTTP-Probe; bei Ausfall Rollback)

Berechtigung: Das Token braucht **Admin**-Recht auf das Repository
(`gh auth login` bzw. ein PAT mit `repo`-Scope). Die Automatik-Token dieses
Repos haben das nicht – dieses Skript ist ein Admin-Werkzeug, kein Bot.

Nutzung
-------
    python3 scripts/repo_brand_switch.py                # Plan zeigen (nichts ändern)
    python3 scripts/repo_brand_switch.py --apply        # Kopf-Daten setzen + nachlesen
    python3 scripts/repo_brand_switch.py --apply --privat   # inkl. Umschalten auf privat
    python3 scripts/repo_brand_switch.py --beschreibung "…" --apply
    python3 scripts/repo_brand_switch.py --selftest     # Logik-Beweis ohne Netz

Exit-Codes: 0 = erreicht bzw. sauber geplant · 1 = Ziel nicht erreicht
            (inkl. Rollback nach --privat) · 2 = Aufruf-/Werkzeugfehler
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API = "https://api.github.com"
STANDARD_REPO = "frank-hartung/franksfinanzcheck-blog"
WEBSITE = "https://franksfinanzcheck.de/"

STANDARD_BESCHREIBUNG = ("FranksFinanzcheck – unabhängiger Finanz-Ratgeber von "
                         "Frank Hartung: Strom, Gas, DSL, Versicherungen, Sparen.")
STANDARD_THEMEN = ["geld-sparen", "finanzen", "frugalismus",
                   "stromvergleich", "versicherungen", "ratgeber"]


def api(pfad: str, token: str, methode: str = "GET", daten: dict | None = None):
    koerper = json.dumps(daten).encode() if daten is not None else None
    anfrage = urllib.request.Request(API + pfad, data=koerper, method=methode)
    anfrage.add_header("Accept", "application/vnd.github+json")
    anfrage.add_header("X-GitHub-Api-Version", "2022-11-28")
    anfrage.add_header("User-Agent", "repo-brand-switch")
    if token:
        anfrage.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(anfrage, timeout=30) as antwort:
        text = antwort.read().decode("utf-8", "replace")
    return json.loads(text) if text.strip() else {}


def http_code(url: str, timeout: int = 20) -> str:
    """HTTP-Status der Website; 'NETZ' wenn die Probe nicht möglich war."""
    try:
        anfrage = urllib.request.Request(url, headers={"User-Agent": "repo-brand-switch"})
        with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:
            return str(getattr(antwort, "status", 200))
    except urllib.error.HTTPError as fehler:
        return str(fehler.code)
    except Exception:  # noqa: BLE001 – Netzfehler ist ein eigener Zustand, kein Absturz
        return "NETZ"


def website_erreichbar(code: str) -> bool:
    """Nur ein 2xx/3xx-Code beweist die laufende Website. 'NETZ' beweist nichts."""
    return code[:1] in ("2", "3")


def plan(repo_daten: dict, ziel: dict) -> list[tuple[str, str, str]]:
    """Nur-Differenz: (Feld, ist, soll) – zeigt, was ein --apply schreiben würde."""
    schritte: list[tuple[str, str, str]] = []
    if (repo_daten.get("description") or "") != ziel["beschreibung"]:
        schritte.append(("description", repo_daten.get("description") or "",
                         ziel["beschreibung"]))
    if (repo_daten.get("homepage") or "") != ziel["homepage"]:
        schritte.append(("homepage", repo_daten.get("homepage") or "", ziel["homepage"]))
    if bool(repo_daten.get("has_wiki")) and ziel["wiki_aus"]:
        schritte.append(("has_wiki", "true", "false"))
    if sorted(repo_daten.get("topics") or []) != sorted(ziel["themen"]):
        schritte.append(("topics", ", ".join(repo_daten.get("topics") or []) or "(keine)",
                         ", ".join(ziel["themen"])))
    if ziel["privat"] and not repo_daten.get("private", False):
        schritte.append(("visibility", "public", "private"))
    return schritte


def selftest() -> int:
    fehler: list[str] = []
    ziel = {"beschreibung": STANDARD_BESCHREIBUNG, "homepage": WEBSITE,
            "wiki_aus": True, "themen": STANDARD_THEMEN, "privat": False}

    leer = plan({"description": "", "homepage": None, "has_wiki": True,
                 "topics": [], "private": False}, ziel)
    felder = [s[0] for s in leer]
    if felder != ["description", "homepage", "has_wiki", "topics"]:
        fehler.append(f"F1: Plan unvollständig: {felder}")

    fertig = plan({"description": STANDARD_BESCHREIBUNG, "homepage": WEBSITE,
                   "has_wiki": False, "topics": STANDARD_THEMEN, "private": True}, ziel)
    if fertig:
        fehler.append(f"F2: fertiger Zustand erzeugt Schritte: {fertig}")

    mit_privat = plan({"description": STANDARD_BESCHREIBUNG, "homepage": WEBSITE,
                       "has_wiki": False, "topics": STANDARD_THEMEN, "private": False},
                      {**ziel, "privat": True})
    if [s[0] for s in mit_privat] != ["visibility"]:
        fehler.append(f"F3: Sichtbarkeit nicht geplant: {mit_privat}")

    if not website_erreichbar("200") or not website_erreichbar("301"):
        fehler.append("F4: 2xx/3xx wurde nicht als erreichbar gewertet")
    if website_erreichbar("404") or website_erreichbar("NETZ"):
        fehler.append("F5: 404/NETZ darf NICHT als erreichbar gelten "
                      "(sonst bliebe eine tote Website unbemerkt)")

    if fehler:
        print("🛑 Selbsttest fehlgeschlagen:")
        for f in fehler:
            print(f"   · {f}")
        return 2
    print("✅ Selbsttest: Plan-Differenz und Website-Probe (inkl. Netz-Ausfall) belegt.")
    return 0


def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(description="Repo-Kopf auf Marke bringen (Admin-Werkzeug)")
    zerleger.add_argument("--repo", default=STANDARD_REPO)
    zerleger.add_argument("--beschreibung", default=STANDARD_BESCHREIBUNG)
    zerleger.add_argument("--homepage", default=WEBSITE)
    zerleger.add_argument("--themen", default=",".join(STANDARD_THEMEN))
    zerleger.add_argument("--wiki-an", action="store_true", help="Wiki bewusst eingeschaltet lassen")
    zerleger.add_argument("--privat", action="store_true",
                          help="Repository auf privat umschalten (mit Website-Prüfung und Rollback)")
    zerleger.add_argument("--apply", action="store_true", help="Änderungen wirklich schreiben")
    zerleger.add_argument("--selftest", action="store_true")
    args = zerleger.parse_args(argv)

    if args.selftest:
        return selftest()

    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        print("::error::Kein GH_TOKEN/GITHUB_TOKEN in der Umgebung – dieses Werkzeug braucht "
              "ein Admin-Token (gh auth login).")
        return 2

    try:
        ist = api(f"/repos/{args.repo}", token)
    except Exception as fehler:  # noqa: BLE001
        print(f"::error::Repository {args.repo} nicht lesbar: {fehler}")
        return 2

    # Admin-Recht wird erst beim Schreiben verlangt: Der Plan (lesend) ist auch
    # mit einem reinen Automatik-Token nützlich – genau er zeigt dem Admin, was
    # zu tun ist. Schreiben ohne Admin-Recht: Abbruch statt Fehlversuch.
    admin = bool(ist.get("viewer_can_administer"))
    if not admin and args.apply:
        print(f"::error::Das Token hat keine Admin-Rechte auf {args.repo} "
              f"(viewer_can_administer=false) – Schreiben nicht möglich. "
              f"Mit Admin-Login (gh auth login) ausführen; der Plan unten gilt unverändert.")
        return 2

    ziel = {
        "beschreibung": args.beschreibung,
        "homepage": args.homepage,
        "wiki_aus": not args.wiki_an,
        "themen": [t.strip() for t in args.themen.split(",") if t.strip()],
        "privat": args.privat,
    }

    print(f"Repository: {args.repo}")
    print(f"  Sichtbarkeit : {'privat' if ist.get('private') else 'öffentlich'}")
    print(f"  Beschreibung : {ist.get('description') or '(keine)'}")
    print(f"  Homepage     : {ist.get('homepage') or '(keine)'}")
    print(f"  Wiki         : {'an' if ist.get('has_wiki') else 'aus'}")
    print(f"  Themen       : {', '.join(ist.get('topics') or []) or '(keine)'}")
    print()

    schritte = plan(ist, ziel)
    if not schritte:
        print("✅ Repo-Kopf ist bereits auf Marke – nichts zu tun.")
        return 0

    print("Geplant:")
    for feld, von, nach in schritte:
        print(f"  · {feld}: „{von}“ → „{nach}“")
    print()

    if not args.apply:
        print("Nur-Plan (Standard, nichts geschrieben). Schreiben mit:  --apply"
              + ("  --privat" if args.privat else ""))
        if not admin:
            print("   (Dieses Token hat keine Admin-Rechte – der Plan zeigt den Admin-Griff.)")
        return 0

    # ---- Schreiben (ein PATCH je Bereich, danach wird nachgelesen) ----
    felder: dict = {"description": ziel["beschreibung"], "homepage": ziel["homepage"]}
    if ziel["wiki_aus"]:
        felder["has_wiki"] = False
    if args.privat:
        felder["private"] = True
    try:
        api(f"/repos/{args.repo}", token, "PATCH", felder)
    except Exception as fehler:  # noqa: BLE001
        print(f"::error::PATCH fehlgeschlagen: {fehler}")
        return 1
    try:
        api(f"/repos/{args.repo}/topics", token, "PUT", {"names": ziel["themen"]})
    except Exception as fehler:  # noqa: BLE001
        print(f"::warning::Themen konnten nicht gesetzt werden: {fehler}")

    # ---- Nachlesen: nichts gilt, was nicht zurückgelesen wurde ----
    nach = api(f"/repos/{args.repo}", token)
    pruefungen = [
        ("Beschreibung", (nach.get("description") or "") == ziel["beschreibung"]),
        ("Homepage", (nach.get("homepage") or "") == ziel["homepage"]),
        ("Wiki aus", (not nach.get("has_wiki")) if ziel["wiki_aus"] else True),
        ("Themen", sorted(nach.get("topics") or []) == sorted(ziel["themen"])),
    ]
    if args.privat:
        pruefungen.append(("privat", bool(nach.get("private"))))
    offen = [name for name, ok in pruefungen if not ok]
    for name, ok in pruefungen:
        print(f"  {'✅' if ok else '🛑'} {name}")
    if offen:
        print(f"::error::Nachprüfung offen: {', '.join(offen)}")
        return 1

    # ---- Website-Prüfung nach dem Privatstellen (sonst rollt es zurück) ----
    if args.privat:
        code = http_code(WEBSITE)
        print(f"\nWebsite-Probe nach dem Umschalten: HTTP {code}")
        if website_erreichbar(code):
            print("✅ Website läuft weiter – privates Repository trägt den Betrieb.")
        elif code == "NETZ":
            print("::warning::Website nicht prüfbar (Netzfehler) – Umschaltung bleibt aktiv. "
                  "Bitte in den nächsten Minuten prüfen: " + WEBSITE)
            print("   Rückweg, falls die Seite fehlt:  "
                  f"gh api -X PATCH repos/{args.repo} -F private=false")
        else:
            print(f"::error::Website antwortet mit HTTP {code} – dieser Plan trägt keine "
                  f"GitHub Pages aus privaten Repositories. Rollback auf öffentlich.")
            api(f"/repos/{args.repo}", token, "PATCH", {"private": False})
            zurueck = api(f"/repos/{args.repo}", token)
            print("   Rollback belegt: private=" + str(bool(zurueck.get("private"))))
            print("   Nächster Schritt: Weg B1/B2 aus docs/MARKEN-OBERFLAECHE-RUNBOOK.md.")
            return 1

    print("\n✅ Repo-Kopf steht auf Marke (jede Änderung zurückgelesen).")
    print("   Kontrolle: python3 scripts/brand_surface_guard.py --gate")
    return 0


if __name__ == "__main__":
    sys.exit(main())
