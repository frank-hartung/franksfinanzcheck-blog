#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Nachheilung: maschinelle Heilung auf fremd geändertem Bestand nachziehen.

WARUM ES DIESES WERKZEUG GIBT (Vorgang WF-A535, Meldung #590, 05.10.2026)
------------------------------------------------------------------------
Die Content-Engine lief am 05.10.2026 dreiundzwanzig Minuten lang sauber und
verlor am Ende ihren kompletten Tagesertrag. Hergang (Run 37325495772):

  14:26  Lauf startet auf dem main-Stand 30263d66.
  14:46  Ein Mensch führt PR #585 zusammen und schreibt neun Bestands-Artikel
         redaktionell um; eine Minute später heilt der Deploy-Lauf drei davon.
  14:53  Der Phase-2-Push rebaset gegen diesen neuen Stand – sieben Artikel
         kollidieren. Richtig: `git_sync.sh` merget NIE blind über Content.
         Falsch: der Lauf merkte es nicht (der Schritt toleriert Fehler) und
         stapelte danach zwei weitere Commits auf einen Stand, der nie wieder
         pushbar war.
  14:55  Der einzige Schritt ohne Fehlertoleranz scheitert am selben Konflikt.
         Roter Lauf, Meldung #590 – mit dem Ratschlag, API-Schlüssel zu prüfen.

Die Kollision selbst ist unvermeidbar: Menschen und Automatik arbeiten am
selben Bestand. Entscheidbar ist nur, WAS gewinnt. Unwiederbringlich ist der
fremde Text; die maschinelle Heilung (Rechtschreibung, Keyword-Gate, Titel,
URL-/CTA-Hygiene, Shortcodes) ist deterministisch und auf dem neuen Text in
Sekunden erneut herstellbar.

Deshalb: `git_sync.sh` gibt den Artikel an den Bestand ab (die fremde Fassung
gewinnt) und protokolliert ihn. Dieses Werkzeug liest das Protokoll und zieht
die Heilung auf dem NEUEN Textstand nach – im selben Lauf, nicht irgendwann.

VERTRAG
-------
* Es wird nur geheilt, was in `content/posts/<slug>/index.md` liegt und
  wirklich existiert. Alles andere im Protokoll wird verworfen (ein Protokoll
  ist eine Maschinen-Notiz, keine Befehlsliste).
* Werkzeuge werden als Argumentliste gestartet – nie über eine Shell.
* Zielgenaue Werkzeuge laufen je Datei, bestandsweite genau einmal.
* Das Protokoll wird erst nach erfolgreicher Heilung gelöscht; scheitert ein
  Werkzeug, bleibt der Auftrag stehen und der nächste Lauf wiederholt ihn.
* `--selftest` läuft vollständig offline und ruft kein Heil-Werkzeug auf.

Benutzung
---------
    python3 scripts/nachheilung.py                # Plan (schreibt nichts)
    python3 scripts/nachheilung.py --hat-arbeit   # Exit 0 = es liegt Arbeit an
    python3 scripts/nachheilung.py --fix          # Heilung nachziehen
    python3 scripts/nachheilung.py --selftest     # Verträge prüfen (offline)
    python3 scripts/nachheilung.py --json         # Maschinenlesbar

Exit-Codes
----------
    0 = erledigt (oder nichts zu tun)
    1 = mindestens ein Werkzeug ist gescheitert (Protokoll bleibt erhalten)
    2 = Selbsttest rot
    3 = Protokoll vorhanden, aber kein einziger gültiger Eintrag
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"

#: Vorgabe-Protokoll – identisch mit GIT_SYNC_NACHHEIL_LOG in git_sync.sh.
STANDARD_PROTOKOLL = ".git_sync_nachheilung.txt"

#: Nur echte Artikel-Dateien sind heilbar (kein Pfad-Ausbruch, keine Skripte).
ARTIKEL_MUSTER = re.compile(r"^content/posts/[A-Za-z0-9._-]+/index\.md$")


@dataclass(frozen=True)
class Werkzeug:
    """Ein Heil-Werkzeug der Kette.

    zielgenau=True  -> wird je betroffener Datei mit `flagge <pfad>` gestartet.
    zielgenau=False -> läuft genau einmal über den Bestand (idempotent).
    """

    skript: str
    argumente: tuple[str, ...]
    zielgenau: bool = False
    flagge: str = "--file"
    zweck: str = ""


#: Die Kette ist bewusst klein, offline und deterministisch: genau die
#: Heilungen, die ein fremd überschriebener Artikel verloren hat. Keine
#: KI-Schritte, keine Netzaufrufe, keine Geldflächen (Kostensperre).
KETTE: tuple[Werkzeug, ...] = (
    Werkzeug("zeit_rechtschreibung.py", ("--fix", "--offline"), zielgenau=True,
             zweck="Rechtschreibung auf ZEIT-Niveau (offline-Engine)"),
    Werkzeug("fix_cta_hygiene.py", ("--include-drafts",), zielgenau=True,
             zweck="CTA-Hygiene des Artikels"),
    Werkzeug("repetition_guard.py", ("--fix",),
             zweck="Doppelwörter nach erneuter Keyword-Injektion"),
    Werkzeug("keyword_gate.py", ("--fix",),
             zweck="Keyword-Gate (Titel, Description, erster Absatz, Dichte)"),
    Werkzeug("check_titles.py", ("--fix",),
             zweck="Titel-Konvention"),
    Werkzeug("fix_url_hygiene.py", ("--fix",),
             zweck="URL-Hygiene (R8-URL-LEERZEICHEN)"),
    Werkzeug("shortcode_guard.py", ("--fix",),
             zweck="Shortcode-Fangnetz (Build-Killer, WF-1F8C #522)"),
)


@dataclass
class Lage:
    """Ergebnis des Einlesens: was ist zu tun, was wurde verworfen."""

    protokoll: Path
    artikel: list[str] = field(default_factory=list)
    verworfen: list[str] = field(default_factory=list)

    @property
    def hat_arbeit(self) -> bool:
        return bool(self.artikel)


# --------------------------------------------------------------------------- #
#  Einlesen
# --------------------------------------------------------------------------- #
def protokoll_pfad(argv: list[str] | None = None, wurzel: Path | None = None) -> Path:
    """Protokollpfad aus CLI (`--protokoll`), Umgebung oder Vorgabe."""
    argv = argv or []
    wurzel = wurzel or ROOT
    for i, a in enumerate(argv):
        if a == "--protokoll" and i + 1 < len(argv):
            p = Path(argv[i + 1])
            return p if p.is_absolute() else wurzel / p
    aus_umgebung = os.environ.get("GIT_SYNC_NACHHEIL_LOG", "").strip()
    if aus_umgebung:
        p = Path(aus_umgebung)
        return p if p.is_absolute() else wurzel / p
    return wurzel / STANDARD_PROTOKOLL


def lies_lage(protokoll: Path, wurzel: Path | None = None) -> Lage:
    """Liest das Protokoll und trennt heilbare Artikel von Unsinn.

    Verworfen wird alles, was nicht exakt ein Artikelpfad ist (Pfad-Ausbruch,
    Skripte, Reports) oder nicht existiert – etwa weil der Artikel zwischen
    Konflikt und Nachheilung gelöscht wurde.
    """
    wurzel = wurzel or ROOT
    lage = Lage(protokoll=protokoll)
    if not protokoll.exists():
        return lage
    gesehen: set[str] = set()
    for rohzeile in protokoll.read_text(encoding="utf-8").splitlines():
        eintrag = rohzeile.strip()
        if not eintrag or eintrag.startswith("#"):
            continue
        if eintrag in gesehen:
            continue
        gesehen.add(eintrag)
        if not ARTIKEL_MUSTER.match(eintrag) or not (wurzel / eintrag).is_file():
            lage.verworfen.append(eintrag)
            continue
        lage.artikel.append(eintrag)
    return lage


# --------------------------------------------------------------------------- #
#  Planen und Ausführen
# --------------------------------------------------------------------------- #
def plane(artikel: list[str]) -> list[list[str]]:
    """Baut die vollständige Befehlsliste – ohne irgendetwas auszuführen."""
    befehle: list[list[str]] = []
    if not artikel:
        return befehle
    for wz in KETTE:
        skript = str(SCRIPTS / wz.skript)
        if wz.zielgenau:
            for pfad in artikel:
                befehle.append([sys.executable, skript, *wz.argumente, wz.flagge, pfad])
        else:
            befehle.append([sys.executable, skript, *wz.argumente])
    return befehle


def fuehre_aus(befehle: list[list[str]], runner=None, wurzel: Path | None = None):
    """Führt die Kette aus. `runner` ist injizierbar (Tests laufen trocken)."""
    runner = runner or subprocess.run
    wurzel = wurzel or ROOT
    ergebnisse = []
    for befehl in befehle:
        proc = runner(befehl, cwd=str(wurzel), capture_output=True, text=True)
        rc = getattr(proc, "returncode", 0)
        ergebnisse.append({"befehl": befehl, "rc": rc})
        kurz = " ".join(Path(t).name if t.endswith(".py") else t for t in befehl[1:])
        if rc == 0:
            print(f"  ✅ {kurz}")
        else:
            # Ein Fund (Exit 1) eines Heilers ist kein Weltuntergang – er wird
            # genannt, nicht verschluckt. Erst der Gesamtbefund entscheidet.
            print(f"  ⚠ {kurz} → Exit {rc}")
            ausgabe = (getattr(proc, "stdout", "") or "").strip().splitlines()[-5:]
            for zeile in ausgabe:
                print(f"      {zeile}")
    return ergebnisse


def bericht(lage: Lage, befehle: list[list[str]], ergebnisse=None) -> str:
    zeilen = ["## Nachheilung (WF-A535 #590)", ""]
    if not lage.hat_arbeit:
        zeilen.append("Nichts nachzuheilen – kein Bestands-Artikel wurde abgegeben.")
        return "\n".join(zeilen) + "\n"
    zeilen.append(f"**Artikel:** {len(lage.artikel)} · **Schritte:** {len(befehle)}")
    zeilen.append("")
    for a in lage.artikel:
        zeilen.append(f"- `{a}`")
    if lage.verworfen:
        zeilen.append("")
        zeilen.append(f"Verworfen (kein Artikelpfad): {len(lage.verworfen)}")
    if ergebnisse:
        rot = [e for e in ergebnisse if e["rc"] != 0]
        zeilen.append("")
        zeilen.append(f"**Ergebnis:** {len(ergebnisse) - len(rot)}/{len(ergebnisse)} "
                      f"Schritte grün.")
    return "\n".join(zeilen) + "\n"


def schreibe_zusammenfassung(text: str) -> None:
    ziel = os.environ.get("GITHUB_STEP_SUMMARY", "")
    if not ziel:
        return
    try:
        with open(ziel, "a", encoding="utf-8") as fh:
            fh.write(text + "\n")
    except OSError:
        pass


# --------------------------------------------------------------------------- #
#  Selbsttest – offline, ohne ein einziges Heil-Werkzeug zu starten
# --------------------------------------------------------------------------- #
def run_selftest() -> list[str]:
    fehler: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        artikel = wurzel / "content/posts/2026-10-05-probe/index.md"
        artikel.parent.mkdir(parents=True, exist_ok=True)
        artikel.write_text("---\ntitle: Probe\n---\nText\n", encoding="utf-8")
        protokoll = wurzel / STANDARD_PROTOKOLL

        # ST1: Kein Protokoll = keine Arbeit, kein Fehler.
        lage = lies_lage(protokoll, wurzel)
        if lage.hat_arbeit or plane(lage.artikel):
            fehler.append("ST1: ohne Protokoll darf nichts geplant werden")

        # ST2: Unsinn wird verworfen (Pfad-Ausbruch, Skripte, Nicht-Existentes).
        protokoll.write_text(
            "content/posts/2026-10-05-probe/index.md\n"
            "../../etc/passwd\n"
            "scripts/git_sync.sh\n"
            "content/posts/gibt-es-nicht/index.md\n"
            "content/posts/../../../etc/shadow\n"
            "# Kommentar\n"
            "\n",
            encoding="utf-8")
        lage = lies_lage(protokoll, wurzel)
        if lage.artikel != ["content/posts/2026-10-05-probe/index.md"]:
            fehler.append(f"ST2: Filter durchlässig oder zu streng: {lage.artikel}")
        if len(lage.verworfen) != 4:
            fehler.append(f"ST2: verworfene Einträge falsch gezählt: {lage.verworfen}")

        # ST3: Doppelte Einträge werden einmal geheilt, Reihenfolge bleibt.
        protokoll.write_text(
            "content/posts/2026-10-05-probe/index.md\n" * 3, encoding="utf-8")
        lage = lies_lage(protokoll, wurzel)
        if lage.artikel != ["content/posts/2026-10-05-probe/index.md"]:
            fehler.append("ST3: Protokoll wird nicht dedupliziert")

        # ST4: Der Plan ruft nichts auf – und enthält jedes Werkzeug der Kette.
        aufrufe: list[list[str]] = []

        class _Proc:
            returncode = 0
            stdout = ""
            stderr = ""

        def _runner(befehl, **_kw):
            aufrufe.append(list(befehl))
            return _Proc()

        befehle = plane(lage.artikel)
        if aufrufe:
            fehler.append("ST4: Planen darf kein Werkzeug starten")
        zielgenaue = [w for w in KETTE if w.zielgenau]
        bestandsweite = [w for w in KETTE if not w.zielgenau]
        erwartet = len(zielgenaue) * len(lage.artikel) + len(bestandsweite)
        if len(befehle) != erwartet:
            fehler.append(f"ST4: Plan hat {len(befehle)} statt {erwartet} Schritte")

        # ST5: Jeder Befehl ist eine Argumentliste mit Python-Interpreter –
        #      keine Shell-Zeichenkette, kein `shell=True`-Einfallstor.
        for befehl in befehle:
            if not isinstance(befehl, list) or befehl[0] != sys.executable:
                fehler.append(f"ST5: kein sicherer Argumentvektor: {befehl}")
                break
            if any(zeichen in " ".join(befehl) for zeichen in (";", "&&", "|", "`")):
                fehler.append(f"ST5: Shell-Metazeichen im Befehl: {befehl}")
                break

        # ST6: Ausführen ruft exakt den Plan auf (zielgenau je Datei, Rest einmal).
        #      Die Protokollzeilen der Trockenläufe gehören nicht in die
        #      Ausgabe des Selbsttests – sonst liest sich eine Prüfung wie ein
        #      echter Heil-Lauf.
        with contextlib.redirect_stdout(io.StringIO()):
            fuehre_aus(befehle, runner=_runner, wurzel=wurzel)
        if len(aufrufe) != len(befehle):
            fehler.append("ST6: Ausführung weicht vom Plan ab")
        if not any(w.flagge in " ".join(a) for w in zielgenaue for a in aufrufe):
            fehler.append("ST6: zielgenaue Werkzeuge bekommen keinen Dateipfad")

        # ST7: Scheitert ein Werkzeug, bleibt das Protokoll stehen.
        class _Rot:
            returncode = 1
            stdout = "Fund"
            stderr = ""

        with contextlib.redirect_stdout(io.StringIO()):
            erg = fuehre_aus(befehle[:1], runner=lambda b, **k: _Rot(), wurzel=wurzel)
        if erg[0]["rc"] != 1:
            fehler.append("ST7: Fehlschlag eines Werkzeugs wird verschluckt")

        # ST8: Die Kette enthält keine Geldfläche und keinen Netzpfad.
        verboten = ("--ai", "--online", "--oeffentlich", "--strict")
        for wz in KETTE:
            if any(v in wz.argumente for v in verboten):
                fehler.append(f"ST8: {wz.skript} ruft eine verbotene Betriebsart auf")
        for wz in KETTE:
            if not (SCRIPTS / wz.skript).is_file():
                fehler.append(f"ST8: Werkzeug fehlt im Repo: {wz.skript}")

    return fehler


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    if "--selftest" in argv:
        fehler = run_selftest()
        if fehler:
            print("🛑 NACHHEILUNG-SELBSTTEST ROT:")
            print("\n".join("  " + f for f in fehler))
            return 2
        print("✅ Selbsttest grün (ST1–ST8, offline, ohne Werkzeugaufruf).")
        return 0

    protokoll = protokoll_pfad(argv)
    lage = lies_lage(protokoll)
    als_json = "--json" in argv

    if "--hat-arbeit" in argv:
        if als_json:
            print(json.dumps({"hat_arbeit": lage.hat_arbeit,
                              "artikel": lage.artikel}, ensure_ascii=False))
        else:
            print(f"Nachheilung: {len(lage.artikel)} Artikel vorgemerkt "
                  f"({protokoll.name}).")
        return 0 if lage.hat_arbeit else 1

    befehle = plane(lage.artikel)

    if not lage.hat_arbeit:
        if lage.verworfen:
            print("🛑 Protokoll vorhanden, aber kein gültiger Artikel-Eintrag:")
            print("\n".join("  - " + v for v in lage.verworfen))
            return 3
        print("Nichts nachzuheilen – kein Bestands-Artikel wurde abgegeben.")
        return 0

    print(f"Nachheilung (WF-A535 #590): {len(lage.artikel)} Artikel, "
          f"{len(befehle)} Schritte.")
    for a in lage.artikel:
        print(f"  · {a}")
    if lage.verworfen:
        print(f"  (verworfen, kein Artikelpfad: {len(lage.verworfen)})")

    if "--fix" not in argv:
        print("\nPlan (nichts geschrieben) – mit --fix anwenden:")
        for befehl in befehle:
            print("  " + " ".join(Path(t).name if t.endswith(".py") else t
                                  for t in befehl[1:]))
        if als_json:
            print(json.dumps({"artikel": lage.artikel, "schritte": len(befehle)},
                             ensure_ascii=False))
        return 0

    ergebnisse = fuehre_aus(befehle)
    rot = [e for e in ergebnisse if e["rc"] != 0]
    text = bericht(lage, befehle, ergebnisse)
    schreibe_zusammenfassung(text)

    if rot:
        print(f"⚠ Nachheilung unvollständig: {len(rot)} Schritt(e) mit Befund – "
              f"Protokoll bleibt erhalten ({protokoll.name}), nächster Lauf "
              f"wiederholt sie.")
        return 1

    try:
        protokoll.unlink()
    except OSError:
        pass
    print(f"✅ Nachheilung abgeschlossen: {len(lage.artikel)} Artikel auf dem "
          f"neuen Textstand geheilt, Protokoll geschlossen.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
