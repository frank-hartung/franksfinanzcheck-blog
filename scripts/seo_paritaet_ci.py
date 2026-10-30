#!/usr/bin/env python3
# ============================================================
#  SEO-PARITÄT – der CI-Einstieg für die vier Werkzeuge
#  (28.10.2026, CI-Einbindung)
# ------------------------------------------------------------
#  WARUM ES DIESE DATEI GIBT
#  -------------------------
#  Vier Werkzeuge, vier Exit-Code-Geschichten, zwei davon Gates, zwei
#  Berichte. Diese Entscheidung gehört NICHT in 20 YAML-Zeilen: Ein
#  Workflow, der `… || true` schreibt, ist ein grüner Haken ohne
#  Aussage; ein Workflow, der jede P3-Meldung als Fehler behandelt,
#  wird nach zwei Tagen ignoriert. Beides ist in diesem Repo schon
#  passiert (Governance #206, Robustheit C31).
#
#  Deshalb gibt es EINEN Einstiegspunkt mit einer dokumentierten,
#  testbaren Policy. Der Workflow ruft nur noch ihn auf.
#
#  DIE POLICY (bewusst eng, bewusst begründet)
#  -------------------------------------------
#  SPERRE (Exit 1, blockiert den PR):
#    · Selbsttest eines Werkzeugs rot            → der Detektor ist defekt
#    · Unit-/DOM-Tests rot                        → der Vertrag ist gebrochen
#    · Befund mit Schwere P1 aus irgendeinem Werkzeug
#    · Fokus-Keywords P2 (F1–F8)                  → der Autor hat das Feld
#                                                   gesetzt, also gilt der Vertrag
#    · Cornerstone C1/C2/C3/C5                    → eine ausdrückliche
#                                                   Markierung wird gebrochen
#
#  BERNSTEIN (Exit 0, sichtbar im Job-Summary und im Artefakt):
#    · alle P3-Befunde (Berichte: Social-Karten, Linkvorschläge, C6)
#    · Cornerstone C4 („älter als 180 Tage")
#
#  WARUM C4 NICHT SPERRT (die Lehre vom 07.10.2026)
#  -------------------------------------------------
#  C4 zählt Tage. Ein Gate, das von der Uhr abhängt, wird irgendwann rot,
#  ohne dass jemand Code angefasst hat – genau die Zeitbombe, die
#  `scripts/selftest_clock.py` (+97 Tage) im Repo bereits dingfest gemacht
#  hat. Alter ist ein Redaktionssignal, kein Merge-Hindernis. Wer es
#  strenger will: `--streng` macht alle Bernstein-Befunde zur Sperre –
#  dann aber bewusst und von Hand, nicht als Dauerzustand.
#
#  WAS HIER NICHT PASSIERT
#  -----------------------
#  · kein Hugo-Build (die Quelle `frontmatter` genügt für den Gate-Lauf;
#    die gebaute Wahrheit prüft der zweite Job des Workflows)
#  · keine Netzaufrufe, keine Schreibzugriffe auf `content/`
#  · keine erfundenen Zahlen: Was nicht gemessen wurde, steht als
#    „nicht gemessen" im Bericht, nicht als 0.
#
#  BENUTZUNG
#  ---------
#    python3 scripts/seo_paritaet_ci.py                 # Standardlauf
#    python3 scripts/seo_paritaet_ci.py --streng        # auch P3 sperrt
#    python3 scripts/seo_paritaet_ci.py --md bericht.md # Markdown schreiben
#    python3 scripts/seo_paritaet_ci.py --json out.json
#    python3 scripts/seo_paritaet_ci.py --summary       # Markdown auf stdout
#    python3 scripts/seo_paritaet_ci.py --ohne-tests    # nur Befunde (lokal)
#    python3 scripts/seo_paritaet_ci.py --selftest
#
#  Exit: 0 ohne Sperre, 1 bei Sperre, 2 bei Werkzeug-/Eingabefehlern.
# ============================================================
"""Ein Einstiegspunkt, eine Policy: CI-Gate für die vier SEO-Paritäts-Werkzeuge."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

# Werkzeuge mit Selbsttest – der Selbsttest läuft IMMER zuerst (Familien-
# standard dieses Repos: eine Wache, die sich nicht selbst beweist, ist ein
# grüner Haken ohne Aussage).
WERKZEUGE = (
    "social_limits",
    "fokus_keywords",
    "cornerstone_wache",
    "link_vorschlaege",
    "social_vorschau",
)

# PyUnit-Suiten, die den Vertrag der vier Werkzeuge prüfen.
SUITEN = (
    "scripts.tests.test_fokus_keywords",
    "scripts.tests.test_cornerstone_wache",
    "scripts.tests.test_link_vorschlaege",
    "scripts.tests.test_social_vorschau",
    "scripts.tests.test_seo_paritaet_ci",
)

# Nodesuiten (DOM-Vertrag der Vorschau). Fehlt Node, ist das ein Befund
# „nicht gemessen" – kein stilles Grün.
NODE_SUITEN = ("tools/social-vorschau/app.test.cjs",)

# Cornerstone-Regeln, die eine ausdrückliche Markierung brechen.
CORNERSTONE_SPERRE = {"C1", "C2", "C3", "C5"}

# Zeitlimit je Unterprozess (Sekunden). Ein hängender Test darf den Lauf
# nicht blockieren – er wird als Sperre gemeldet, nicht als Timeout der CI.
ZEITLIMIT = 600


@dataclass
class Posten:
    """Ein Befund, wie ihn der Bericht zeigt."""
    werkzeug: str
    regel: str
    schwere: str
    ort: str
    text: str
    massnahme: str = ""

    def als_dict(self) -> dict:
        return {"werkzeug": self.werkzeug, "regel": self.regel,
                "schwere": self.schwere, "ort": self.ort,
                "text": self.text, "massnahme": self.massnahme}


@dataclass
class Schritt:
    """Ergebnis eines ausgeführten Schritts (Selbsttest, Testsuite, …)."""
    name: str
    ok: bool
    detail: str = ""
    dauer_s: float = 0.0
    uebersprungen: bool = False

    def als_dict(self) -> dict:
        return {"name": self.name, "ok": self.ok, "detail": self.detail,
                "dauer_s": round(self.dauer_s, 2), "uebersprungen": self.uebersprungen}


@dataclass
class Befund:
    """Gesamtlage eines Laufs."""
    schritte: list[Schritt] = field(default_factory=list)
    posten: list[Posten] = field(default_factory=list)
    kennzahlen: dict = field(default_factory=dict)
    sperren: list[Posten] = field(default_factory=list)
    warnungen: list[Posten] = field(default_factory=list)
    fehler: list[str] = field(default_factory=list)

    @property
    def exit_code(self) -> int:
        if self.fehler:
            return 2
        return 1 if self.sperren else 0


# --------------------------------------------------------------------------- #
#  Policy – eine reine Funktion, damit sie ohne Repo prüfbar ist
# --------------------------------------------------------------------------- #
def ist_sperre(posten: Posten) -> bool:
    """Entscheidet, ob EIN Befund den Merge blockiert.

    Reihenfolge der Prüfungen = Reihenfolge der Begründung im Kopf dieser
    Datei. Neue Regeln gehören hierher und in den Selbsttest, sonst
    entsteht eine Policy, die nur im Workflow existiert.
    """
    if posten.schwere == "P1":
        return True
    if posten.werkzeug == "cornerstone" and posten.regel in CORNERSTONE_SPERRE:
        return True
    if posten.werkzeug == "fokus_keywords" and posten.schwere == "P2":
        return True
    return False


def bewerte(posten: list[Posten], *, streng: bool = False) -> tuple[list[Posten], list[Posten]]:
    """Teilt Befunde in Sperren und Bernstein. `streng` hebt alles auf Sperre."""
    sperren: list[Posten] = []
    warnungen: list[Posten] = []
    for eintrag in posten:
        if streng or ist_sperre(eintrag):
            sperren.append(eintrag)
        else:
            warnungen.append(eintrag)
    return sperren, warnungen


# --------------------------------------------------------------------------- #
#  Schritte ausführen
# --------------------------------------------------------------------------- #
def fuehre_aus(name: str, befehl: list[str], *, cwd: str = BLOG_DIR,
               umgebung: dict | None = None) -> Schritt:
    """Unterprozess mit Zeitlimit. Ausgabe wird IMMER gezeigt (Lehre vom
    02.10.2026: ein Schritt, der rot wird und nichts sagt, ist schlimmer als
    einer, der durchläuft)."""
    import time
    start = time.monotonic()
    env = {**os.environ, **(umgebung or {})}
    try:
        ergebnis = subprocess.run(befehl, cwd=cwd, env=env, timeout=ZEITLIMIT,
                                  capture_output=True, text=True)
    except FileNotFoundError:
        return Schritt(name, False, f"nicht ausführbar: {befehl[0]}", time.monotonic() - start)
    except subprocess.TimeoutExpired:
        return Schritt(name, False, f"Zeitlimit {ZEITLIMIT}s überschritten",
                       time.monotonic() - start)
    dauer = time.monotonic() - start
    ausgabe = (ergebnis.stdout + ergebnis.stderr).strip()
    zeilen = ausgabe.splitlines()

    def _aussage() -> str:
        """Der Satz, der die Reparatur beginnt – nicht die letzte Zeile.

        `unittest` endet mit „FAILED (failures=1)"; welche Prüfung das war,
        steht eine Zeile darüber als `FAIL: test_…`. Genau diese Zeile fehlt
        sonst in jeder Zusammenfassung (Lehre aus dem roten Gate-Lauf vom
        28.10.2026, in dem nur „failures=1" zu lesen war).
        """
        for zeile in zeilen:
            if zeile.startswith(("FAIL:", "ERROR:")):
                return zeile.strip()
        for zeile in reversed(zeilen):
            if zeile.strip():
                return zeile.strip()
        return ""

    if ergebnis.returncode != 0:
        schwanz = "\n".join(zeilen[-12:])
        print(f"── {name}: Exit {ergebnis.returncode} ──\n{schwanz}\n"
              f"── {name}: {_aussage()}", file=sys.stderr)
    return Schritt(name, ergebnis.returncode == 0, _aussage() if ausgabe else "", dauer)


def selbsttests() -> list[Schritt]:
    return [fuehre_aus(f"Selbsttest {werkzeug}",
                       [sys.executable, os.path.join("scripts", f"{werkzeug}.py"), "--selftest"])
            for werkzeug in WERKZEUGE]


def unittests() -> list[Schritt]:
    return [fuehre_aus("Unit-Tests der SEO-Parität",
                       [sys.executable, "-m", "unittest", "-v", *SUITEN])]


def node_tests() -> list[Schritt]:
    """DOM-Vertrag der Vorschau. Ohne Node: „nicht gemessen", nicht grün."""
    from shutil import which
    if which("node") is None:
        print("⚠ Node fehlt – DOM-Test der Social-Vorschau wird als "
              "„nicht gemessen“ gemeldet.", file=sys.stderr)
        return [Schritt("DOM-Test Social-Vorschau", False,
                        "Node nicht verfügbar – nicht gemessen", 0.0, uebersprungen=True)]
    return [fuehre_aus("DOM-Test Social-Vorschau", ["node", "--test", *NODE_SUITEN])]


# --------------------------------------------------------------------------- #
#  Befunde einsammeln (in-process, keine Unterprozesse nötig)
# --------------------------------------------------------------------------- #
def _lade(modul: str):
    """Importiert ein Werkzeug und meldet fehlende Abhängigkeiten als Fehler."""
    try:
        return __import__(modul)
    except ImportError as fehler:
        raise RuntimeError(f"{modul} nicht ladbar: {fehler} "
                           f"(PyYAML ist in requirements-ci.in gepinnt)") from fehler


def sammle_posten(root: str, *, mit_linkvorschlaegen: bool = True,
                  quelle: str = "frontmatter") -> tuple[list[Posten], dict]:
    """Führt die Werkzeuge aus und übersetzt ihre Befunde in Posten.

    Die Werkzeuge bleiben die Wahrheit über ihre Regeln (Schwere, Text,
    Maßnahme). Hier wird nur übersetzt – keine Regel wird nachgebaut.
    """
    posten: list[Posten] = []
    kennzahlen: dict = {}

    # Cornerstone -----------------------------------------------------------
    cw = _lade("cornerstone_wache")
    stand = cw.pruefe(root)
    markiert = sum(1 for s in stand["seiten"].values() if s["cornerstone"])
    kennzahlen["cornerstone"] = {
        "seiten": len(stand["seiten"]),
        "markiert": markiert,
        "befunde": len(stand["befunde"]),
        "kandidaten": len(stand["kandidaten"]),
    }
    for befund in stand["befunde"]:
        seite = stand["seiten"].get(befund["slug"], {})
        posten.append(Posten("cornerstone", befund["regel"], befund["schwere"],
                             seite.get("datei", befund["slug"]),
                             befund["text"], befund["massnahme"]))

    # Fokus-Keywords --------------------------------------------------------
    fk = _lade("fokus_keywords")
    fokus_befunde, fokus_seiten, _ = fk.lauf(root)
    kennzahlen["fokus_keywords"] = {
        "seiten": len(fokus_seiten),
        "befunde": len(fokus_befunde),
        "ohne_feld": sum(1 for b in fokus_befunde if b.regel == "F9"),
        "kannibalisierung": sum(1 for b in fokus_befunde if b.regel == "F8"),
    }
    for befund in fokus_befunde:
        posten.append(Posten("fokus_keywords", befund.regel, befund.schwere,
                             befund.datei, befund.text, befund.massnahme))

    # Social-Vorschau -------------------------------------------------------
    sv = _lade("social_vorschau")
    with tempfile.TemporaryDirectory() as tmp:
        # `quelle` reicht die Quelle an die Vorschau durch: `frontmatter` im
        # schnellen Gate (kein Hugo), `build` im Nachtlauf gegen das
        # tatsächlich gerenderte HTML. Dieselbe Policy, zwei Messpunkte.
        daten = sv.sammle(root, quelle, tmp)
    kennzahlen["social"] = {**daten["summary"], "quelle": daten["quelle"]}
    for seite in daten["pages"]:
        for befund in seite["befunde"]:
            posten.append(Posten("social", befund["code"], befund["schwere"],
                                 seite["url"], befund["detail"], befund["massnahme"]))

    # Linkvorschläge (Bericht, keine Sperre) --------------------------------
    if mit_linkvorschlaegen:
        lv = _lade("link_vorschlaege")
        vorschlaege = lv.erzeuge()
        kennzahlen["linkvorschlaege"] = {
            "vorschlaege": len(vorschlaege),
            "artikel": len({v["quelle"] for v in vorschlaege}),
        }
        # Linkvorschläge sind per Definition keine Fehler. Sie erscheinen im
        # Bericht als Kennzahl, nicht als Befund – ein Vorschlag, der den
        # Build rot macht, wäre ein Denkfehler.
    return posten, kennzahlen


# --------------------------------------------------------------------------- #
#  Bericht
# --------------------------------------------------------------------------- #
def _tabelle(zeilen: list[list[str]]) -> str:
    kopf, *rest = zeilen
    aus = ["| " + " | ".join(kopf) + " |",
           "|" + "|".join(["---"] * len(kopf)) + "|"]
    aus += ["| " + " | ".join(z) + " |" for z in rest]
    return "\n".join(aus)


def summary_md(lage: Befund, *, streng: bool) -> str:
    """Kompakter Bericht für `$GITHUB_STEP_SUMMARY` und für Menschen."""
    zeilen = ["## SEO-Parität", ""]
    status = "🔴 Sperre" if lage.sperren else ("🟡 nur Hinweise" if lage.warnungen else "🟢 ohne Befund")
    zeilen.append(f"**Ergebnis:** {status} · Sperren: {len(lage.sperren)} · "
                  f"Hinweise: {len(lage.warnungen)} · Policy: "
                  f"{'alles sperrt (--streng)' if streng else 'P1 + Fokus P2 + Cornerstone C1/C2/C3/C5'}")
    zeilen.append("")

    if lage.schritte:
        zeilen.append("### Prüfschritte")
        zeilen.append("")
        zeilen.append(_tabelle([["Schritt", "Ergebnis", "Dauer", "Detail"]] + [
            [s.name.replace("|", "\\|"), "✅" if s.ok else ("⚪" if s.uebersprungen else "❌"),
             f"{s.dauer_s:.1f}s", (s.detail or "").replace("|", "\\|")[:120]]
            for s in lage.schritte]))
        zeilen.append("")

    if lage.kennzahlen:
        zeilen.append("### Messwerte")
        zeilen.append("")
        cs = lage.kennzahlen.get("cornerstone", {})
        fokus = lage.kennzahlen.get("fokus_keywords", {})
        social = lage.kennzahlen.get("social", {})
        links = lage.kennzahlen.get("linkvorschlaege", {})
        zeilen.append(_tabelle([
            ["Werkzeug", "Seiten", "Befunde", "Bemerkung"],
            ["Cornerstones", str(cs.get("seiten", "–")), str(cs.get("befunde", "–")),
             f"{cs.get('markiert', '–')} markiert, {cs.get('kandidaten', '–')} Kandidaten"],
            ["Fokus-Keywords", str(fokus.get("seiten", "–")), str(fokus.get("befunde", "–")),
             f"{fokus.get('ohne_feld', '–')} ohne Feld, {fokus.get('kannibalisierung', '–')} Kannibalisierung"],
            ["Social-Vorschau", str(social.get("seiten", "–")), str(social.get("befunde", "–")),
             f"{social.get('ohne_bild', '–')} ohne Bild"],
            ["Linkvorschläge", str(links.get("artikel", "–")), str(links.get("vorschlaege", "–")),
             "Bericht – schreibt nichts"],
        ]))
        zeilen.append("")

    for titel, gruppe in (("Sperren (blockieren den Merge)", lage.sperren),
                          ("Hinweise (kein Merge-Hindernis)", lage.warnungen)):
        if not gruppe:
            continue
        zeilen.append(f"### {titel} – {len(gruppe)}")
        zeilen.append("")
        for posten in gruppe[:25]:
            zeilen.append(f"- **{posten.schwere} · {posten.werkzeug}/{posten.regel}** "
                          f"`{posten.ort}` — {posten.text}")
        if len(gruppe) > 25:
            zeilen.append(f"- … und {len(gruppe) - 25} weitere (vollständig im Artefakt `seo-paritaet.json`)")
        zeilen.append("")

    if lage.fehler:
        zeilen.append("### Werkzeugfehler")
        zeilen.append("")
        zeilen += [f"- {f}" for f in lage.fehler]
        zeilen.append("")

    zeilen.append("_Ein grüner Lauf heißt: die formalen Bedingungen sind erfüllt. "
                  "Er ist keine Aussage über Rankings, Suchvolumen oder Textqualität._")
    return "\n".join(zeilen) + "\n"


def bericht_json(lage: Befund, *, streng: bool) -> dict:
    return {
        "version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "policy": {"streng": streng,
                   "sperre": "P1 · Fokus P2 (F1–F8) · Cornerstone C1/C2/C3/C5",
                   "bernstein": "alle P3 · Cornerstone C4/C6"},
        "ergebnis": {"sperren": len(lage.sperren), "hinweise": len(lage.warnungen),
                     "exit": lage.exit_code},
        "schritte": [s.als_dict() for s in lage.schritte],
        "kennzahlen": lage.kennzahlen,
        "sperren": [p.als_dict() for p in lage.sperren],
        "hinweise": [p.als_dict() for p in lage.warnungen],
        "fehler": lage.fehler,
    }


# --------------------------------------------------------------------------- #
#  Lauf
# --------------------------------------------------------------------------- #
def lauf(root: str = BLOG_DIR, *, streng: bool = False, ohne_tests: bool = False,
         mit_linkvorschlaegen: bool = True, quelle: str = "frontmatter") -> Befund:
    lage = Befund()
    if not ohne_tests:
        lage.schritte += selbsttests()
        lage.schritte += unittests()
        lage.schritte += node_tests()
        for schritt in lage.schritte:
            if not schritt.ok and not schritt.uebersprungen:
                lage.fehler.append(f"{schritt.name}: {schritt.detail or 'fehlgeschlagen'}")
    try:
        posten, kennzahlen = sammle_posten(root, mit_linkvorschlaegen=mit_linkvorschlaegen,
                                           quelle=quelle)
        lage.posten = posten
        lage.kennzahlen = kennzahlen
    except (RuntimeError, OSError, ValueError) as fehler:
        lage.fehler.append(f"Befunde nicht erhebbar: {fehler}")
    lage.sperren, lage.warnungen = bewerte(lage.posten, streng=streng)
    return lage


# --------------------------------------------------------------------------- #
#  Selbsttest
# --------------------------------------------------------------------------- #
def selftest() -> int:
    fails: list[str] = []

    def p(werkzeug: str, regel: str, schwere: str) -> Posten:
        return Posten(werkzeug, regel, schwere, "content/posts/x/index.md", "Text", "Maßnahme")

    # Policy: P1 sperrt immer, unabhängig vom Werkzeug.
    for werkzeug, regel in (("cornerstone", "C1"), ("fokus_keywords", "F3"),
                            ("social", "social-bild"), ("linkvorschlaege", "X")):
        if not ist_sperre(p(werkzeug, regel, "P1")):
            fails.append(f"P1 aus {werkzeug} sperrt nicht")
    # Fokus P2 sperrt (der Autor hat das Feld gesetzt), Fokus P3 nicht.
    if not ist_sperre(p("fokus_keywords", "F2", "P2")):
        fails.append("Fokus-P2 (F2) sperrt nicht")
    if ist_sperre(p("fokus_keywords", "F7", "P3")):
        fails.append("Fokus-P3 (F7) sperrt fälschlich")
    # Cornerstone: Markierungsbruch sperrt, Alter/Breite nicht.
    for regel in sorted(CORNERSTONE_SPERRE):
        if not ist_sperre(p("cornerstone", regel, "P2")):
            fails.append(f"Cornerstone {regel} sperrt nicht")
    for regel in ("C4", "C6"):
        if ist_sperre(p("cornerstone", regel, "P2")):
            fails.append(f"Cornerstone {regel} sperrt fälschlich (Zeitbombe/Hinweis)")
    # Social-P3 (Kartenhinweis) sperrt nie.
    if ist_sperre(p("social", "social-beschreibung", "P3")):
        fails.append("Social-P3 sperrt fälschlich")
    # streng hebt alles auf Sperre.
    sperren, warnungen = bewerte([p("social", "social-beschreibung", "P3")], streng=True)
    if len(sperren) != 1 or warnungen:
        fails.append("--streng hebt P3 nicht auf Sperre")
    sperren, warnungen = bewerte([p("social", "social-beschreibung", "P3")], streng=False)
    if sperren or len(warnungen) != 1:
        fails.append("Standard-Policy macht P3 zur Sperre")
    # Exit-Codes: Werkzeugfehler ist 2, Sperre 1, sauber 0.
    lage = Befund()
    if lage.exit_code != 0:
        fails.append("leere Lage hat Exit ungleich 0")
    lage.sperren = [p("fokus_keywords", "F2", "P2")]
    if lage.exit_code != 1:
        fails.append("Lage mit Sperre hat nicht Exit 1")
    lage.fehler = ["Test rot"]
    if lage.exit_code != 2:
        fails.append("Lage mit Werkzeugfehler hat nicht Exit 2")
    # Summary nennt Policy, Ehrlichkeitsgrenze und Zählung.
    md = summary_md(Befund(sperren=[p("fokus_keywords", "F2", "P2")]), streng=False)
    if "Sperren: 1" not in md or "keine Aussage über Rankings" not in md:
        fails.append("Summary nennt Zählung oder Ehrlichkeitsgrenze nicht")
    if "--streng" not in summary_md(Befund(), streng=True):
        fails.append("Summary weist die strenge Policy nicht aus")
    # JSON ist serialisierbar und trägt die Policy.
    daten = bericht_json(Befund(), streng=False)
    if daten["policy"]["streng"] is not False or "sperre" not in daten["policy"]:
        fails.append("JSON trägt die Policy nicht")
    with contextlib.suppress(TypeError, ValueError):
        json.dumps(daten, ensure_ascii=False)

    # Ende-zu-Ende auf einem Mini-Repo: ein markierter, unterverlinkter
    # Cornerstone und ein Artikel ohne keywords_fokus.
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        # hugo.toml ist Pflicht: Die Social-Vorschau bildet og:url aus der
        # baseURL. Fehlt sie, meldet der Lauf „Befunde nicht erhebbar" –
        # genau das soll er auch (fail-closed), aber der Test braucht ein
        # realistisches Mini-Repo.
        with open(os.path.join(tmp, "hugo.toml"), "w", encoding="utf-8") as fh:
            fh.write('baseURL = "https://franksfinanzcheck.de/"\n')

        def schreibe(slug: str, text: str) -> None:
            ordner = os.path.join(tmp, "content", "posts", slug)
            os.makedirs(ordner, exist_ok=True)
            with open(os.path.join(ordner, "index.md"), "w", encoding="utf-8") as fh:
                fh.write(text)

        schreibe("cs", '---\ntitle: "Cornerstone"\ndescription: "Beschreibung"\n'
                       'date: 2026-10-01\nlastmod: 2026-10-01\ndraft: false\n'
                       'pillar: "strom"\ncornerstone: true\n---\n\nText.\n')
        schreibe("normal", '---\ntitle: "Normal"\ndescription: "Beschreibung"\n'
                          'date: 2026-10-01\ndraft: false\npillar: "strom"\n---\n\nText.\n')
        lage = lauf(tmp, ohne_tests=True, mit_linkvorschlaegen=False)
        regeln = {(p.werkzeug, p.regel) for p in lage.sperren}
        if ("cornerstone", "C3") not in regeln:
            fails.append("Mini-Repo: unterverlinkter Cornerstone sperrt nicht")
        if ("cornerstone", "C5") not in regeln:
            fails.append("Mini-Repo: unvollständiger Cornerstone sperrt nicht")
        if any(w == "fokus_keywords" and r == "F9" for w, r in regeln):
            fails.append("Mini-Repo: fehlendes keywords_fokus sperrt (F9 ist Empfehlung)")
        if not any(p.werkzeug == "fokus_keywords" and p.regel == "F9" for p in lage.warnungen):
            fails.append("Mini-Repo: F9 erscheint nicht als Hinweis")
        if lage.exit_code != 1:
            fails.append(f"Mini-Repo: Exit {lage.exit_code} statt 1")
        # --streng macht aus Hinweisen Sperren.
        streng_lage = lauf(tmp, ohne_tests=True, streng=True, mit_linkvorschlaegen=False)
        if not any(p.regel == "F9" for p in streng_lage.sperren):
            fails.append("--streng hebt F9 nicht auf Sperre")
        # Kein Schreibzugriff auf content/
        vorher = {os.path.join(dp, f): os.path.getmtime(os.path.join(dp, f))
                  for dp, _, fs in os.walk(os.path.join(tmp, "content")) for f in fs}
        lauf(tmp, ohne_tests=True, mit_linkvorschlaegen=False)
        nachher = {os.path.join(dp, f): os.path.getmtime(os.path.join(dp, f))
                   for dp, _, fs in os.walk(os.path.join(tmp, "content")) for f in fs}
        if vorher != nachher:
            fails.append("Lauf hat Inhalte verändert")

    if fails:
        for f in fails:
            print(f"❌ SEO-Parität CI: {f}")
        return 2
    print("✅ SEO-Parität CI: Selbsttest bestanden – Policy (P1, Fokus-P2, "
          "Cornerstone-Markierung sperren; P3 und Alter nicht), Exit-Codes, "
          "Summary-Ehrlichkeit und der Ende-zu-Ende-Lauf sind belegt.")
    return 0


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--streng", action="store_true",
                        help="auch P3-Hinweise sperren (bewusst, nicht als Dauerzustand)")
    parser.add_argument("--ohne-tests", action="store_true",
                        help="Selbsttests und Suiten überspringen (nur lokale Befunde)")
    parser.add_argument("--md", metavar="PFAD", help="Markdown-Bericht schreiben")
    parser.add_argument("--json", metavar="PFAD", help="JSON-Bericht schreiben ('-' = stdout)")
    parser.add_argument("--summary", action="store_true", help="Markdown auf stdout")
    parser.add_argument("--ohne-linkvorschlaege", action="store_true",
                        help="Linkvorschläge nicht erzeugen (sie sind immer nur Bericht)")
    parser.add_argument("--quelle", choices=("frontmatter", "build", "auto"),
                        default="frontmatter",
                        help="Datenquelle der Social-Vorschau (build verlangt public/)")
    parser.add_argument("--root", default=BLOG_DIR)
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    # Ein Absturz ist KEINE Policy-Aussage. Ohne diesen Fänger endet eine
    # Ausnahme mit Exit 1 – und der Workflow meldete „ein Befund sperrt",
    # obwohl in Wahrheit das Werkzeug gestorben ist (real passiert im ersten
    # CI-Lauf am 28.10.2026). Exit 2 heißt: nichts wird freigegeben.
    try:
        return _pruefe_und_berichte(args)
    except Exception as fehler:  # noqa: BLE001 – Beweislast: alles melden
        import traceback
        traceback.print_exc()
        print(f"❌ SEO-Parität CI: Werkzeug gestorben – {type(fehler).__name__}: {fehler}",
              file=sys.stderr)
        return 2


def _pruefe_und_berichte(args) -> int:
    if args.json == "-" or args.summary:
        with contextlib.redirect_stdout(sys.stderr):
            if selftest() != 0:
                return 2
    elif selftest() != 0:
        return 2

    lage = lauf(args.root, streng=args.streng, ohne_tests=args.ohne_tests,
                mit_linkvorschlaegen=not args.ohne_linkvorschlaege,
                quelle=args.quelle)
    md = summary_md(lage, streng=args.streng)

    # Fehler gehören AUCH auf stderr – im Summary-Betrieb der CI ist stderr
    # das Einzige, was im Log steht, und der Workflow baut daraus seine
    # Annotation. Stand nur im Markdown, blieb der Befund unsichtbar.
    for fehler in lage.fehler:
        print(f"❌ {fehler}", file=sys.stderr)

    if args.md:
        ziel = os.path.abspath(args.md)
        os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(md)
    if args.json and args.json != "-":
        ziel = os.path.abspath(args.json)
        os.makedirs(os.path.dirname(ziel) or ".", exist_ok=True)
        with open(ziel, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(bericht_json(lage, streng=args.streng),
                                ensure_ascii=False, indent=2) + "\n")
    if args.json == "-":
        print(json.dumps(bericht_json(lage, streng=args.streng), ensure_ascii=False, indent=2))
    elif args.summary:
        print(md)
    else:
        print(f"SEO-Parität: Sperren {len(lage.sperren)} · Hinweise {len(lage.warnungen)}"
              f"{' · Werkzeugfehler ' + str(len(lage.fehler)) if lage.fehler else ''}")
        for posten in lage.sperren[:20]:
            print(f"  🔴 {posten.schwere} {posten.werkzeug}/{posten.regel} {posten.ort}: {posten.text}")
        for posten in lage.warnungen[:10]:
            print(f"  🟡 {posten.schwere} {posten.werkzeug}/{posten.regel} {posten.ort}: {posten.text}")
        if len(lage.warnungen) > 10:
            print(f"  … {len(lage.warnungen) - 10} weitere Hinweise (--md für den Bericht)")
        for fehler in lage.fehler:
            print(f"  ❌ {fehler}")
    return lage.exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
