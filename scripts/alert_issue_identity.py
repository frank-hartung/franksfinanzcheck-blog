#!/usr/bin/env python3
# ============================================================
#  ALARM-IDENTITÄT – Fehlermeldungen ohne Betriebssprache im Titel
#  ------------------------------------------------------------
#  WARUM (01.10.2026, Folge von Issue #496):
#    Offene Issue-Titel sind eine öffentliche Markenfläche: GitHub
#    indexiert sie, und „⚠️ Workflow fehlgeschlagen: KI-Redaktion
#    (failure)" erzählt bei einer Markensuche die Betriebsgeschichte
#    statt der Expertenpositionierung. Die Marken-Wache meldete das
#    als GELB (O6) – zu Recht.
#
#  WARUM NICHT EINFACH UMBENENNEN:
#    Das Fehler-Alerting hat den Titel als IDENTITÄT benutzt
#    (Dedupe beim Anlegen, Auto-Close bei Grün, Aufräumlauf). Ein
#    schöner Titel ohne neue Identität hätte drei Folgen gehabt:
#    Doppel-Issues bei jedem Lauf, nie wieder automatisch
#    geschlossene Meldungen, ein volllaufender Issue-Tracker.
#
#  DIE LÖSUNG (eine Quelle der Wahrheit – diese Datei):
#    · IDENTITÄT = stabiler Marker im Body: <!-- alert-key: WF-XXXX -->
#      Technik bleibt technisch, aber unsichtbar (HTML-Kommentar).
#    · TITEL = markenneutral und trotzdem informativ:
#      „🔧 Wartung · Inhaltsqualität · Vorgang WF-7F3A"
#      Kein Workflow-Name, kein „fehlgeschlagen", kein Betriebsjargon –
#      und für Frank auf einen Blick einsortierbar (Bereich + Code).
#    · Der Code ist deterministisch aus dem Workflow-Namen abgeleitet,
#      also über Jahre und Umbenennungen des Alerting-Codes stabil.
#    · `--tabelle` übersetzt jeden Code zurück in den Workflow –
#      die Zuordnung geht nicht verloren, sie steht nur nicht mehr
#      öffentlich im Titel.
#
#  SELBSTTEST: `--selftest` beweist Eindeutigkeit der Codes über die
#  echte Wacht-Liste, Markenfreiheit der erzeugten Titel (gegen die
#  Wortliste der Marken-Wache) und die Erkennung von Alt-Titeln für
#  die Migration. Ein blinder Namensgeber wäre schlimmer als keiner.
# ============================================================
"""Markenneutrale Identität für automatische Fehlermeldungen."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.request

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALERT_WORKFLOW = os.path.join(HIER, ".github", "workflows", "alert-on-failure.yml")
API = "https://api.github.com"

LABEL = "auto-report"
MARKER_PRAEFIX = "alert-key"
# Alt-Form, die es zu ersetzen gilt (und die die Migration erkennen muss).
ALT_TITEL = re.compile(r"^⚠️\s*Workflow fehlgeschlagen:\s*(?P<wf>.+?)\s*\((?P<schluss>[a-z_]+)\)\s*$")

# ------------------------------------------------------------
#  Bereichsnamen: markenneutrale Alltagssprache statt Werkzeugnamen.
#  Reihenfolge = Priorität (erste Regel, die greift, gewinnt).
#  Bewusst grob: der Bereich ordnet ein, die Diagnose steht im Body.
# ------------------------------------------------------------
BEREICHE: list[tuple[str, str]] = [
    (r"newsletter", "Newsletter"),
    (r"pinterest|mastodon|social|shorts|dialog|repin|backlink|reichweite",
     "Reichweite"),
    (r"deploy|pages|uptime|catchup|publication", "Veröffentlichung"),
    (r"backup|offsite|integrity|security|token|secret", "Sicherung"),
    (r"kennzahl|radar|revenue|umsatz|analytics|governance|report",
     "Auswertung"),
    (r"affiliate|partner|link", "Partnerhinweise"),
    (r"lesehilfen|hemingway|rechtschreib|politur|redaktions|lesbarkeit|layout|design|e2e",
     "Lesbarkeit & Gestaltung"),
    (r"content|engine|reserve|faktenfrische|artikel|kadenz|ki-redaktion|agc|recherche|agent",
     "Inhaltsqualität"),
    (r"issue|triage|cleanup|dependabot|watchdog|wache|marken", "Betriebspflege"),
    (r"frist|recht", "Rechtliches"),
]
BEREICH_SONST = "Technik"


# =====================================================================
#  Namensgebung (rein rechnerisch, ohne Netz)
# =====================================================================
def code(workflow: str) -> str:
    """Stabiler, nichtssagender Vorgangscode aus dem Workflow-Namen.

    Deterministisch (sha256), damit derselbe Workflow nach Monaten
    denselben Code trägt – die Identität darf nicht vom Zufall abhängen.
    """
    roh = hashlib.sha256(workflow.strip().encode("utf-8")).hexdigest().upper()
    return "WF-" + roh[:4]


def bereich(workflow: str) -> str:
    text = workflow.lower()
    for muster, name in BEREICHE:
        if re.search(muster, text):
            return name
    return BEREICH_SONST


def marker(workflow: str) -> str:
    """Unsichtbare Identität im Issue-Body (HTML-Kommentar)."""
    return f"<!-- {MARKER_PRAEFIX}: {code(workflow)} -->"


def titel(workflow: str) -> str:
    """Markenfläche: informativ für Frank, nichtssagend für die Suche."""
    return f"🔧 Wartung · {bereich(workflow)} · Vorgang {code(workflow)}"


def identitaet(workflow: str) -> dict:
    return {
        "workflow": workflow,
        "code": code(workflow),
        "bereich": bereich(workflow),
        "titel": titel(workflow),
        "marker": marker(workflow),
        "label": LABEL,
    }


# =====================================================================
#  Wacht-Liste lesen (ohne YAML-Bibliothek – der Runner hat keine)
# =====================================================================
def wacht_liste(pfad: str = ALERT_WORKFLOW) -> list[str]:
    """Liest die überwachten Workflow-Namen aus alert-on-failure.yml.

    Bewusst ein kleiner, erklärbarer Parser: der Block beginnt bei
    `workflows:` und endet bei `types:`; jede Zeile `- "Name"` zählt.
    """
    if not os.path.exists(pfad):
        return []
    namen: list[str] = []
    drin = False
    with open(pfad, encoding="utf-8") as datei:
        for zeile in datei:
            nackt = zeile.strip()
            if nackt.startswith("workflows:"):
                drin = True
                continue
            if drin and nackt.startswith("types:"):
                break
            if drin and nackt.startswith("- "):
                wert = nackt[2:].split("#", 1)[0].strip()
                if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in "\"'":
                    wert = wert[1:-1]
                if wert:
                    namen.append(wert)
    return namen


# =====================================================================
#  Migration bestehender Meldungen (mit Nachprüfung)
# =====================================================================
class Api:
    def __init__(self, repo: str, token: str, timeout: int = 30):
        self.repo = repo
        self.token = token
        self.timeout = timeout

    def ruf(self, pfad: str, methode: str = "GET", daten: dict | None = None):
        koerper = json.dumps(daten).encode() if daten is not None else None
        anfrage = urllib.request.Request(API + pfad, data=koerper, method=methode)
        anfrage.add_header("Accept", "application/vnd.github+json")
        anfrage.add_header("X-GitHub-Api-Version", "2022-11-28")
        anfrage.add_header("User-Agent", "alert-issue-identity")
        if self.token:
            anfrage.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(anfrage, timeout=self.timeout) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
        return json.loads(roh) if roh.strip() else {}

    def offene_alarme(self) -> list:
        daten = self.ruf(f"/repos/{self.repo}/issues?state=open&labels={LABEL}&per_page=100")
        return [i for i in daten if isinstance(i, dict) and "pull_request" not in i]

    def issue(self, nummer: int) -> dict:
        return self.ruf(f"/repos/{self.repo}/issues/{nummer}")

    def aktualisiere(self, nummer: int, felder: dict) -> dict:
        self.ruf(f"/repos/{self.repo}/issues/{nummer}", "PATCH", felder)
        return self.issue(nummer)


def migriere(api: Api, anwenden: bool) -> tuple[list[str], list[str]]:
    """Alt-Titel → neutraler Titel + Marker im Body. Jede Änderung wird
    zurückgelesen; „migriert" gilt nur, was die Nachprüfung bestätigt."""
    getan: list[str] = []
    offen: list[str] = []
    for issue in api.offene_alarme():
        alt = (issue.get("title") or "").strip()
        treffer = ALT_TITEL.match(alt)
        if not treffer:
            continue
        workflow = treffer.group("wf").strip()
        neu = titel(workflow)
        mark = marker(workflow)
        body = issue.get("body") or ""
        if mark not in body:
            body = (f"{mark}\n> Vorgang **{code(workflow)}** · Bereich "
                    f"*{bereich(workflow)}* · Zuordnung: "
                    f"`python3 scripts/alert_issue_identity.py --tabelle`\n\n{body}")
        nummer = issue.get("number")
        if not anwenden:
            getan.append(f"#{nummer}: „{alt}“ → „{neu}“ (Plan, nichts geschrieben)")
            continue
        try:
            nach = api.aktualisiere(nummer, {"title": neu, "body": body})
        except Exception as fehler:  # noqa: BLE001
            offen.append(f"#{nummer}: Umbenennung fehlgeschlagen ({fehler})")
            continue
        if (nach.get("title") or "").strip() == neu and mark in (nach.get("body") or ""):
            getan.append(f"#{nummer}: → „{neu}“ (nachgelesen: Titel und Marker stehen)")
        else:
            offen.append(f"#{nummer}: Nachprüfung widerspricht – Titel/Marker fehlen")
    return getan, offen


# =====================================================================
#  Selbsttest – ein blinder Namensgeber wäre schlimmer als keiner
# =====================================================================
def selftest() -> int:
    fehler: list[str] = []

    # F1: Determinismus
    if code("Faktenfrische (Bestand)") != code("Faktenfrische (Bestand)"):
        fehler.append("F1: Code ist nicht deterministisch")

    # F2: Verschiedene Workflows → verschiedene Codes (echte Wacht-Liste)
    namen = wacht_liste()
    if len(namen) < 20:
        fehler.append(f"F2: Wacht-Liste nicht gelesen (nur {len(namen)} Namen)")
    codes = {}
    for name in namen:
        codes.setdefault(code(name), []).append(name)
    kollision = {k: v for k, v in codes.items() if len(v) > 1}
    if kollision:
        fehler.append(f"F2: Code-Kollision – Identität wäre mehrdeutig: {kollision}")

    # F3: Titel sind frei von Betriebssprache (Prüfung mit der Marken-Wache selbst)
    try:
        sys.path.insert(0, os.path.join(HIER, "scripts"))
        import brand_surface_guard as wache  # noqa: PLC0415
        for name in namen or ["Content-Engine v2"]:
            funde = wache.pruefe_text(titel(name), "titel", "O6 Öffentliche Issue-Titel", [])
            if funde:
                fehler.append(f"F3: Titel für „{name}“ enthält Betriebssprache: "
                              f"{[f.text for f in funde]}")
                break
    except ImportError as importfehler:  # pragma: no cover
        fehler.append(f"F3: Marken-Wache nicht importierbar ({importfehler})")

    # F4: Alt-Titel werden erkannt, neue nicht (sonst migriert der Lauf endlos)
    if not ALT_TITEL.match("⚠️ Workflow fehlgeschlagen: KI-Redaktion (failure)"):
        fehler.append("F4: Alt-Titel wird nicht erkannt")
    if ALT_TITEL.match(titel("KI-Redaktion")):
        fehler.append("F4: Neuer Titel wird fälschlich als Alt-Titel gelesen")

    # F5: Alt-Titel liefert exakt den Workflow-Namen zurück
    t = ALT_TITEL.match("⚠️ Workflow fehlgeschlagen: Faktenfrische (Bestand) (failure)")
    if not t or t.group("wf") != "Faktenfrische (Bestand)":
        fehler.append(f"F5: Workflow-Name falsch zurückgelesen: {t.group('wf') if t else None}")

    # F6: Marker ist unsichtbar und eindeutig wiederfindbar
    mark = marker("Content-Engine v2")
    if not (mark.startswith("<!--") and mark.endswith("-->")):
        fehler.append("F6: Marker ist kein HTML-Kommentar (wäre sichtbarer Betriebstext)")
    if marker("Content-Engine v2") == marker("Pinterest-AI"):
        fehler.append("F6: Marker unterscheidet Workflows nicht")

    # F7: Bereichszuordnung greift (Stichproben) und fällt sauber zurück
    proben = {
        "Newsletter-Daily (Capture-Wache + Digest)": "Newsletter",
        "Deploy auf GitHub Pages": "Veröffentlichung",
        "Offsite-Backup": "Sicherung",
        "Faktenfrische (Bestand)": "Inhaltsqualität",
    }
    for name, erwartet in proben.items():
        if bereich(name) != erwartet:
            fehler.append(f"F7: Bereich für „{name}“ ist {bereich(name)}, erwartet {erwartet}")
    if bereich("Völlig Unbekanntes") != BEREICH_SONST:
        fehler.append("F7: Unbekannter Workflow fällt nicht auf den Sammelbereich zurück")

    # F8: Migration schreibt nichts im Planmodus
    class TrockenApi(Api):
        def __init__(self):
            super().__init__("x/y", "")
            self.schreibzugriffe = 0

        def offene_alarme(self):
            return [{"number": 1, "title": "⚠️ Workflow fehlgeschlagen: Pinterest-AI (failure)",
                     "body": "alt"}]

        def aktualisiere(self, nummer, felder):  # pragma: no cover
            self.schreibzugriffe += 1
            return {}

    trocken = TrockenApi()
    plan, offen = migriere(trocken, anwenden=False)
    if trocken.schreibzugriffe or len(plan) != 1 or offen:
        fehler.append("F8: Planmodus ist nicht schreibfrei")

    # F9: Migration akzeptiert nur nachgewiesene Änderungen
    class LuegenApi(TrockenApi):
        def aktualisiere(self, nummer, felder):
            return {"title": "etwas anderes", "body": ""}

    _, luegen_offen = migriere(LuegenApi(), anwenden=True)
    if not luegen_offen:
        fehler.append("F9: Unbelegte Heilung wird als Erfolg gewertet")

    if fehler:
        for f in fehler:
            print(f"::error::{f}")
        print(f"❌ Selbsttest Alarm-Identität: {len(fehler)} Fehler.")
        return 1
    print(f"✅ Selbsttest Alarm-Identität: 9 Fallgruppen bestanden "
          f"({len(namen)} Workflows, {len(codes)} eindeutige Codes, "
          f"Titel markenfrei, Migration nur mit Nachprüfung).")
    return 0


# =====================================================================
#  Hauptlauf
# =====================================================================
def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        description="Markenneutrale Identität für automatische Fehlermeldungen")
    zerleger.add_argument("--workflow", help="Workflow-Name → Titel, Marker, Code")
    zerleger.add_argument("--json", action="store_true", help="Ausgabe als JSON")
    zerleger.add_argument("--tabelle", action="store_true",
                          help="Zuordnung Vorgangscode → Workflow (für Menschen)")
    zerleger.add_argument("--selftest", action="store_true", help="Logik-Beweis ohne Netz")
    zerleger.add_argument("--migrate", action="store_true",
                          help="offene Alt-Meldungen neutral umbenennen (Plan)")
    zerleger.add_argument("--apply", action="store_true", help="Migration wirklich schreiben")
    args = zerleger.parse_args(argv)

    if args.selftest:
        return selftest()

    if args.workflow:
        daten = identitaet(args.workflow)
        if args.json:
            print(json.dumps(daten, ensure_ascii=False))
        else:
            for schluessel, wert in daten.items():
                print(f"{schluessel:9}: {wert}")
        return 0

    if args.tabelle:
        namen = wacht_liste()
        breite = max((len(n) for n in namen), default=10)
        print(f"{'Vorgang':10} {'Bereich':24} Workflow")
        print("-" * (36 + breite))
        for name in sorted(namen, key=bereich):
            print(f"{code(name):10} {bereich(name):24} {name}")
        print(f"\n{len(namen)} überwachte Workflows · Quelle: "
              ".github/workflows/alert-on-failure.yml")
        return 0

    if args.migrate:
        repo = os.environ.get("GITHUB_REPOSITORY", "frank-hartung/franksfinanzcheck-blog")
        token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
        if not token:
            print("::error::Kein Token (GH_TOKEN) – Migration braucht Issue-Schreibrecht.")
            return 2
        api = Api(repo, token)
        try:
            getan, offen = migriere(api, anwenden=args.apply)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as fehler:
            print(f"::warning::Migration nicht möglich – API nicht erreichbar ({fehler}).")
            return 0
        for zeile in getan:
            print("· " + zeile)
        for zeile in offen:
            print(f"::error::{zeile}")
        if not getan and not offen:
            print("Keine Alt-Meldungen offen – nichts zu migrieren.")
        return 1 if offen else 0

    zerleger.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
