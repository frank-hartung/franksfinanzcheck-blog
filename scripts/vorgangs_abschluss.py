#!/usr/bin/env python3
# ============================================================
#  VORGANGS-ABSCHLUSS – jede Meldung bekommt ihren Abschlussvermerk
#  ------------------------------------------------------------
#  WARUM ES DAS GIBT (04.10.2026, Rest aus Vorgang WF-A4E0 / #552):
#    Eine behobene Meldung schließt sich beim Zusammenführen über
#    „Closes #552" von selbst – aber ohne ein Wort dazu, was getan
#    wurde. Wer die Meldung später liest, sieht nur „geschlossen".
#    Beim Versuch, den Vermerk von Hand nachzutragen, fiel der eigent-
#    liche Befund auf: Das persönliche Zugangsrecht darf keine Kommen-
#    tare schreiben. Ein Abschluss, der vom Zugangsrecht einer einzelnen
#    Person abhängt, ist kein Verfahren, sondern ein Zufall.
#
#  DIE LÖSUNG:
#    Der Vermerk wird nicht mehr von Hand geschrieben, sondern vom
#    Repository selbst – mit dem Recht, das der Lauf ohnehin hat
#    (`issues: write`). Zwei Wege, damit kein Vermerk verloren geht:
#      1. SOFORT  – beim Zusammenführen eines Änderungsvorschlags
#      2. NACHTRAG – täglicher Nachlauf über die zuletzt zusammen-
#         geführten Vorschläge; was fehlt, wird nachgetragen
#    Beides ist wiederholbar: ein unsichtbarer Marker im Kommentar
#    verhindert Doppelungen, und geschrieben gilt nur, was danach
#    zurückgelesen wurde.
#
#  MARKENFLÄCHE: Issue-Kommentare sind öffentlich und werden indexiert.
#    Der Text läuft deshalb vor dem Absenden durch die Marken-Wache
#    (scripts/brand_surface_guard.py). Findet sie Betriebssprache,
#    wird der Vermerk auf die neutrale Kurzform zurückgenommen – und
#    erst wenn auch die sauber ist, geht er raus. Lieber knapper
#    Vermerk als öffentliche Betriebsgeschichte.
#
#  BEFEHLE:
#    --pr 558 [--apply]        Vermerk für einen Vorschlag (Standard: Plan)
#    --issue 552 --pr 558      Meldung ausdrücklich benennen
#    --nachtrag [--tage 14]    fehlende Vermerke der letzten Tage finden
#    --selftest                Beweis ohne Netz
#
#  Exit: 0 = erledigt/nichts zu tun · 1 = etwas blieb offen
#        2 = Werkzeugfehler (kein Zugangsrecht, Text nicht markenrein)
# ============================================================
"""Abschlussvermerke für behobene Meldungen – vom Repo geschrieben, nicht von Hand."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import urllib.error
import urllib.request

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
API = "https://api.github.com"
STANDARD_REPO = "frank-hartung/franksfinanzcheck-blog"

MARKER_PRAEFIX = "vorgangs-abschluss"
# GitHub-Schlüsselwörter, die eine Meldung beim Zusammenführen schließen.
SCHLIESST = re.compile(
    r"\b(clos(?:e|es|ed)|fix(?:e[sd])?|resolv(?:e|es|ed))\b[\s:]+#(?P<nr>\d+)",
    re.IGNORECASE)
# Vorgangscode aus dem Meldungstitel („🔧 Wartung · Betriebspflege · Vorgang WF-A4E0")
VORGANG = re.compile(r"\bVorgang\s+(WF-[0-9A-F]{4})\b", re.IGNORECASE)


def marker(pr: int) -> str:
    """Unsichtbare Identität des Vermerks – verhindert Doppelungen."""
    return f"<!-- {MARKER_PRAEFIX}: PR-{pr} -->"


# =====================================================================
#  Textbau (rein rechnerisch, ohne Netz – deshalb prüfbar)
# =====================================================================
def _datum(iso: str) -> str:
    try:
        zeit = dt.datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except ValueError:
        return ""
    return zeit.strftime("%d.%m.%Y")


def _markenfunde(text: str) -> list[str]:
    """Prüft den Vermerk mit der Marken-Wache (öffentliche Fläche!)."""
    sys.path.insert(0, os.path.join(HIER, "scripts"))
    try:
        import brand_surface_guard as wache  # noqa: PLC0415
    except ImportError as fehler:  # pragma: no cover - Wache gehört zum Bestand
        return [f"Marken-Wache nicht importierbar ({fehler})"]
    allowlist = wache.lies_allowlist()
    funde = wache.pruefe_text(text, "vermerk", "O6 Öffentliche Issue-Titel", allowlist)
    return [b.text for b in funde]


def vermerk(pr: dict, issue: dict) -> tuple[str, list[str]]:
    """Baut den Abschlussvermerk. Gibt (Text, Hinweise) zurück.

    Der Text ist bewusst kurz: Was getan wurde, steht im Änderungs-
    vorschlag; hier steht, DASS es getan und nachgeprüft wurde, und wo
    es nachzulesen ist. Trägt der Titel des Vorschlags Betriebssprache,
    fällt der Vermerk auf die neutrale Kurzform zurück, statt die
    Betriebsgeschichte öffentlich zu wiederholen.
    """
    hinweise: list[str] = []
    nummer = int(pr.get("number") or 0)
    datum = _datum(pr.get("merged_at") or "")
    code = ""
    treffer = VORGANG.search(issue.get("title") or "")
    if treffer:
        code = treffer.group(1).upper()

    kopf = f"{marker(nummer)}\n✅ **Erledigt und nachgeprüft.**"
    zeilen = [kopf, ""]
    satz = f"Behoben mit #{nummer}"
    if datum:
        satz += f", zusammengeführt am {datum}"
    satz += "."
    if code:
        satz += f" Vorgang **{code}**."
    zeilen.append(satz)

    titel = (pr.get("title") or "").strip()
    if titel:
        kurz = re.sub(r"^[a-z]+(\([^)]*\))?:\s*", "", titel)      # „fix(x): " weg
        kurz = re.sub(r"\s*\((?:[^()]*#\d+[^()]*)\)\s*$", "", kurz).strip()
        probe = f"Kurzfassung: {kurz}"
        if kurz and not _markenfunde(probe):
            zeilen += ["", probe]
        elif kurz:
            hinweise.append("Titel des Vorschlags trägt Betriebssprache – "
                            "Vermerk bleibt in der neutralen Kurzform.")

    zeilen += [
        "",
        f"Einzelheiten, Beweislage und bewusst unterlassene Eingriffe: #{nummer}.",
        "",
        "<sub>Automatischer Abschlussvermerk des Repositorys – damit kein "
        "behobener Vorgang ohne Nachweis schließt.</sub>",
    ]
    text = "\n".join(zeilen)

    funde = _markenfunde(text)
    if funde:
        hinweise.append("Vermerk enthielt Betriebssprache: " + "; ".join(funde))
    return text, hinweise


def meldungen_aus(pr: dict) -> list[int]:
    """Welche Meldungen schließt dieser Vorschlag? (Titel + Beschreibung)"""
    quelle = f"{pr.get('title') or ''}\n{pr.get('body') or ''}"
    gesehen: list[int] = []
    for treffer in SCHLIESST.finditer(quelle):
        nummer = int(treffer.group("nr"))
        if nummer not in gesehen:
            gesehen.append(nummer)
    return gesehen


# =====================================================================
#  Zugriff auf GitHub (klein, austauschbar – der Selbsttest ersetzt ihn)
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
        anfrage.add_header("User-Agent", "vorgangs-abschluss")
        anfrage.add_header("Content-Type", "application/json")
        if self.token:
            anfrage.add_header("Authorization", f"Bearer {self.token}")
        with urllib.request.urlopen(anfrage, timeout=self.timeout) as antwort:
            roh = antwort.read().decode("utf-8", "replace")
        return json.loads(roh) if roh.strip() else {}

    def pr(self, nummer: int) -> dict:
        return self.ruf(f"/repos/{self.repo}/pulls/{nummer}")

    def zusammengefuehrte_prs(self, menge: int = 50) -> list:
        daten = self.ruf(f"/repos/{self.repo}/pulls?state=closed&sort=updated"
                         f"&direction=desc&per_page={menge}")
        return [p for p in daten if isinstance(p, dict) and p.get("merged_at")]

    def issue(self, nummer: int) -> dict:
        return self.ruf(f"/repos/{self.repo}/issues/{nummer}")

    def kommentare(self, nummer: int) -> list:
        daten = self.ruf(f"/repos/{self.repo}/issues/{nummer}/comments?per_page=100")
        return daten if isinstance(daten, list) else []

    def kommentiere(self, nummer: int, text: str) -> dict:
        return self.ruf(f"/repos/{self.repo}/issues/{nummer}/comments", "POST",
                        {"body": text})


# =====================================================================
#  Vermerk setzen (idempotent, mit Nachprüfung)
# =====================================================================
def vermerke_vorschlag(api: Api, pr_nummer: int, anwenden: bool,
                       nur_issue: int | None = None) -> tuple[list[str], list[str]]:
    """Setzt den Abschlussvermerk an allen Meldungen eines Vorschlags."""
    getan: list[str] = []
    offen: list[str] = []

    pr = api.pr(pr_nummer)
    if not pr.get("merged_at"):
        return getan, [f"#{pr_nummer} ist nicht zusammengeführt – kein Abschluss."]

    ziele = [nur_issue] if nur_issue else meldungen_aus(pr)
    if not ziele:
        return getan, offen   # kein „Closes #…": nichts zu vermerken, kein Fehler

    for nummer in ziele:
        try:
            issue = api.issue(nummer)
        except Exception as fehler:  # noqa: BLE001
            offen.append(f"#{nummer}: nicht lesbar ({fehler})")
            continue
        if issue.get("pull_request"):
            continue   # ein Vorschlag ist keine Meldung

        text, hinweise = vermerk(pr, issue)
        schwer = [h for h in hinweise if h.startswith("Vermerk enthielt")]
        if schwer:
            offen.append(f"#{nummer}: {schwer[0]} – nichts geschrieben "
                         "(öffentlicher Kommentar ist Markenfläche).")
            continue

        try:
            vorhanden = api.kommentare(nummer)
        except Exception as fehler:  # noqa: BLE001
            offen.append(f"#{nummer}: Kommentare nicht lesbar ({fehler})")
            continue
        if any(marker(pr_nummer) in (k.get("body") or "") for k in vorhanden):
            getan.append(f"#{nummer}: Vermerk steht bereits (nichts zu tun)")
            continue

        if not anwenden:
            getan.append(f"#{nummer}: Vermerk vorbereitet (Plan, nichts geschrieben)")
            continue

        try:
            api.kommentiere(nummer, text)
        except Exception as fehler:  # noqa: BLE001
            offen.append(f"#{nummer}: Vermerk konnte nicht geschrieben werden "
                         f"({fehler}) – fehlt dem Lauf `issues: write`?")
            continue

        # Nachprüfung: geschrieben gilt nur, was zurückgelesen wird.
        try:
            nach = api.kommentare(nummer)
        except Exception as fehler:  # noqa: BLE001
            offen.append(f"#{nummer}: Nachprüfung nicht möglich ({fehler})")
            continue
        if any(marker(pr_nummer) in (k.get("body") or "") for k in nach):
            getan.append(f"#{nummer}: Vermerk gesetzt und nachgelesen")
        else:
            offen.append(f"#{nummer}: Nachprüfung widerspricht – Vermerk fehlt")

    return getan, offen


def nachtrag(api: Api, tage: int, anwenden: bool,
             heute: dt.datetime | None = None) -> tuple[list[str], list[str]]:
    """Nachlauf: zuletzt zusammengeführte Vorschläge ohne Vermerk nachtragen.

    Der zweite Weg ist der wichtigere: Ereignisse fallen aus, Läufe
    werden abgebrochen, Rechte fehlen zeitweise. Ein täglicher Nachlauf
    macht das Verfahren unabhängig vom einzelnen Augenblick.
    """
    getan: list[str] = []
    offen: list[str] = []
    jetzt = heute or dt.datetime.now(dt.timezone.utc)
    grenze = jetzt - dt.timedelta(days=tage)

    for pr in api.zusammengefuehrte_prs():
        zeit = pr.get("merged_at") or ""
        try:
            wann = dt.datetime.fromisoformat(zeit.replace("Z", "+00:00"))
        except ValueError:
            continue
        if wann < grenze:
            continue
        g, o = vermerke_vorschlag(api, int(pr.get("number")), anwenden)
        getan += g
        offen += o
    return getan, offen


# =====================================================================
#  Selbsttest – ohne Netz, mit erfundener API
# =====================================================================
class _ProbeApi(Api):
    """Nachbau der GitHub-API für den Selbsttest (schreibt nirgendwohin)."""

    def __init__(self, prs: dict, issues: dict, kommentare: dict | None = None,
                 schreibfehler: bool = False, luegt: bool = False):
        super().__init__("x/y", "")
        self._prs = prs
        self._issues = issues
        self._kommentare = kommentare or {}
        self._schreibfehler = schreibfehler
        self._luegt = luegt
        self.schreibzugriffe = 0

    def pr(self, nummer):
        return self._prs[nummer]

    def zusammengefuehrte_prs(self, menge: int = 50):
        return [p for p in self._prs.values() if p.get("merged_at")]

    def issue(self, nummer):
        return self._issues[nummer]

    def kommentare(self, nummer):
        return list(self._kommentare.get(nummer, []))

    def kommentiere(self, nummer, text):
        self.schreibzugriffe += 1
        if self._schreibfehler:
            raise urllib.error.HTTPError(API, 403, "Forbidden", None, None)
        if not self._luegt:
            self._kommentare.setdefault(nummer, []).append({"body": text})
        return {}


def selftest() -> int:
    fehler: list[str] = []

    pr = {"number": 558, "merged_at": "2026-10-04T09:30:30Z",
          "title": "fix(marke): README-Markenfläche heilen (WF-A4E0, #552)",
          "body": "Erklärung …\n\nCloses #552"}
    issue = {"number": 552, "title": "🔧 Wartung · Betriebspflege · Vorgang WF-A4E0"}

    # F1: Schließende Meldungen werden erkannt – in allen üblichen Formen
    proben = {
        "Closes #552": [552],
        "fixes #12 und resolved #13": [12, 13],
        "Closes #7\nCloses #7": [7],
        "siehe #99": [],
    }
    for text, erwartet in proben.items():
        gefunden = meldungen_aus({"title": "", "body": text})
        if gefunden != erwartet:
            fehler.append(f"F1: „{text}“ → {gefunden}, erwartet {erwartet}")

    # F2: Der Vermerk nennt Vorschlag, Datum und Vorgangscode
    text, hinweise = vermerk(pr, issue)
    for teil in ("#558", "04.10.2026", "WF-A4E0", "Erledigt und nachgeprüft"):
        if teil not in text:
            fehler.append(f"F2: „{teil}“ fehlt im Vermerk")
    if hinweise:
        fehler.append(f"F2: unerwartete Hinweise {hinweise}")

    # F3: Der Vermerk ist markenrein (er steht öffentlich)
    if _markenfunde(text):
        fehler.append(f"F3: Vermerk trägt Betriebssprache: {_markenfunde(text)}")

    # F4: Betriebssprache im Titel landet NICHT im öffentlichen Vermerk
    lauter = dict(pr, title="chore: Workflow-Gates in scripts/ nachziehen")
    text2, hinweise2 = vermerk(lauter, issue)
    if _markenfunde(text2):
        fehler.append("F4: Betriebssprache aus dem Titel wurde durchgereicht")
    if not any("Kurzform" in h for h in hinweise2):
        fehler.append("F4: Rückfall auf die Kurzform wurde nicht gemeldet")

    # F5: Marker ist unsichtbar und je Vorschlag eindeutig
    if not marker(558).startswith("<!--") or marker(558) == marker(559):
        fehler.append("F5: Marker taugt nicht als Identität")

    # F6: Planmodus schreibt nichts
    probe = _ProbeApi({558: pr}, {552: issue})
    getan, offen = vermerke_vorschlag(probe, 558, anwenden=False)
    if probe.schreibzugriffe or offen or len(getan) != 1:
        fehler.append(f"F6: Planmodus ist nicht schreibfrei ({getan}, {offen})")

    # F7: Anwenden schreibt genau einmal – ein zweiter Lauf ist still
    probe = _ProbeApi({558: pr}, {552: issue})
    vermerke_vorschlag(probe, 558, anwenden=True)
    vermerke_vorschlag(probe, 558, anwenden=True)
    if probe.schreibzugriffe != 1:
        fehler.append(f"F7: nicht wiederholbar – {probe.schreibzugriffe} Schreibzugriffe")

    # F8: Fehlendes Schreibrecht ist ein sichtbarer Fehler, kein stilles Nichts
    probe = _ProbeApi({558: pr}, {552: issue}, schreibfehler=True)
    _, offen = vermerke_vorschlag(probe, 558, anwenden=True)
    if not offen or "issues: write" not in offen[0]:
        fehler.append("F8: fehlendes Schreibrecht wird nicht benannt")

    # F9: Ohne Nachweis gilt nichts als erledigt
    probe = _ProbeApi({558: pr}, {552: issue}, luegt=True)
    getan, offen = vermerke_vorschlag(probe, 558, anwenden=True)
    if getan or not offen:
        fehler.append("F9: unbelegter Vermerk wird als Erfolg gewertet")

    # F10: Nicht zusammengeführte Vorschläge bekommen keinen Abschluss
    probe = _ProbeApi({559: {"number": 559, "merged_at": None, "body": "Closes #1"}},
                      {1: {"number": 1, "title": "x"}})
    getan, offen = vermerke_vorschlag(probe, 559, anwenden=True)
    if getan or not offen or probe.schreibzugriffe:
        fehler.append("F10: offener Vorschlag wurde abgeschlossen")

    # F11: Der Nachlauf greift nur ins vereinbarte Zeitfenster
    alt = {"number": 500, "merged_at": "2026-09-01T10:00:00Z",
           "title": "alt", "body": "Closes #400"}
    probe = _ProbeApi({558: pr, 500: alt},
                      {552: issue, 400: {"number": 400, "title": "alt"}})
    heute = dt.datetime(2026, 10, 4, tzinfo=dt.timezone.utc)
    getan, offen = nachtrag(probe, tage=14, anwenden=True, heute=heute)
    if probe.schreibzugriffe != 1:
        fehler.append(f"F11: Nachlauf traf das Zeitfenster nicht "
                      f"({probe.schreibzugriffe} Schreibzugriffe)")

    # F12: Ein Vorschlag ohne „Closes" ist kein Fehler
    ohne = {"number": 560, "merged_at": "2026-10-04T10:00:00Z",
            "title": "docs: Kleinigkeit", "body": "nichts zu schließen"}
    probe = _ProbeApi({560: ohne}, {})
    getan, offen = vermerke_vorschlag(probe, 560, anwenden=True)
    if offen or probe.schreibzugriffe:
        fehler.append("F12: Vorschlag ohne Meldung erzeugt Lärm")

    if fehler:
        for eintrag in fehler:
            print(f"::error::{eintrag}")
        print(f"❌ Selbsttest Vorgangs-Abschluss: {len(fehler)} Fehler.")
        return 1
    print("✅ Selbsttest Vorgangs-Abschluss: 12 Fallgruppen bestanden "
          "(Meldungen erkannt, Vermerk vollständig und markenrein, Betriebssprache "
          "abgefangen, Planmodus schreibfrei, wiederholbar, fehlendes Schreibrecht "
          "sichtbar, Nachprüfung verlangt, Zeitfenster eingehalten).")
    return 0


# =====================================================================
#  Hauptlauf
# =====================================================================
def main(argv: list[str] | None = None) -> int:
    zerleger = argparse.ArgumentParser(
        description="Abschlussvermerke für behobene Meldungen")
    zerleger.add_argument("--pr", type=int, help="Nummer des Änderungsvorschlags")
    zerleger.add_argument("--issue", type=int,
                          help="Meldung ausdrücklich benennen (sonst aus „Closes #…“)")
    zerleger.add_argument("--nachtrag", action="store_true",
                          help="fehlende Vermerke der letzten Tage nachtragen")
    zerleger.add_argument("--tage", type=int, default=14,
                          help="Zeitfenster des Nachlaufs (Standard: 14)")
    zerleger.add_argument("--apply", action="store_true",
                          help="wirklich schreiben (sonst nur Plan)")
    zerleger.add_argument("--selftest", action="store_true", help="Beweis ohne Netz")
    args = zerleger.parse_args(argv)

    if args.selftest:
        return selftest()

    if not args.pr and not args.nachtrag:
        zerleger.print_help()
        return 0

    repo = os.environ.get("GITHUB_REPOSITORY", STANDARD_REPO)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    if not token:
        print("::error::Kein Zugangsrecht (GH_TOKEN) – der Abschlussvermerk "
              "braucht Leserecht und `issues: write`.")
        return 2
    api = Api(repo, token)

    try:
        if args.nachtrag:
            getan, offen = nachtrag(api, args.tage, args.apply)
        else:
            getan, offen = vermerke_vorschlag(api, args.pr, args.apply, args.issue)
    except (urllib.error.URLError, TimeoutError, OSError) as fehler:
        print(f"::error::GitHub nicht erreichbar ({fehler}).")
        return 2

    for zeile in getan:
        print("· " + zeile)
    for zeile in offen:
        print(f"::error::{zeile}")
    if not getan and not offen:
        print("Nichts zu vermerken.")

    zusammenfassung = os.environ.get("GITHUB_STEP_SUMMARY")
    if zusammenfassung:
        with open(zusammenfassung, "a", encoding="utf-8") as datei:
            datei.write("### Abschlussvermerke\n\n")
            for zeile in getan:
                datei.write(f"- ✅ {zeile}\n")
            for zeile in offen:
                datei.write(f"- 🛑 {zeile}\n")
            if not getan and not offen:
                datei.write("- Nichts zu vermerken.\n")

    return 1 if offen else 0


if __name__ == "__main__":
    sys.exit(main())
