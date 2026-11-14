#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  WORKFLOW-AUFRUF-VERTRAG – ein Aufruf ist gültig oder er wird rot
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (14.11.2026, Lauf 43618889770)
#
#  `.github/workflows/deploy.yml` rief seit dem 13.11.2026
#
#      python3 scripts/ki_audio_markierung.py --check --dir public/audio/articles
#
#  Das Werkzeug kannte nur `--gate`. `argparse` beendet einen unbekannten
#  Schalter mit Exit 2 – der Schritt meldete „write=0 / check=2“,
#  `werkzeugbefund.py --melden ki-tonspur-markierung` machte daraus einen
#  Werkzeugbefund (C38), und das Auslieferungs-Siegel war an JEDEM Deploy rot.
#  Der Inhalt war dabei gesund: der Gegenlauf am echten Bestand
#  (`origin/gh-pages`, 44 Tonspuren) markierte 44/44 und meldete 0 Befunde.
#
#  Das ist keine Inhalts-, sondern eine VERTRAGS-Lücke zwischen zwei Dateien,
#  die sich nie gegenseitig geprüft haben:
#    · Der Syntax-Job prüft, ob Python KOMPILIERT – ein fremder CLI-Schalter
#      kompiliert einwandfrei.
#    · Die Workflow-Linter prüfen YAML und Actions, nicht Argumente.
#    · Der Wachen-Vertrag (`wachen_vertrag.py`) prüft eine Datei gegen sich
#      selbst (halbe Fassung), nicht gegen ihre Aufrufer.
#    · `blustradius_register.py` prüft REGISTERTE Schritte gegen die Workflows
#      – aber nur die, die im Register stehen. Ein neuer Schritt ist dort
#      nicht erfasst, und ein Schalter ist kein Schritt.
#  Die teuerste Variante dieser Klasse: ein Tippfehler sieht aus wie ein
#  Inhaltsbefund. Deshalb meldet diese Wache einen Schalter, den das Skript
#  nicht kennt, als ROTEN Vertragsverstoß – und nicht das Siegel.
#
#  WAS GEPRÜFT WIRD (rein lesend, ohne den Prüfling auszuführen)
#  -------------------------------------------------------------
#    A1  Jeder `python3 scripts/<datei>.py`-Aufruf in einem `run:`-Block
#        verweist auf eine vorhandene Datei. (Ein gelöschtes Werkzeug ist
#        derselbe Ausfall: Exit 2 am ersten Schritt.)
#    A2  Jeder lange Schalter (`--foo`) steht im `argparse` dieses Skripts –
#        als Optionszeichenkette oder als `dest` (die Bindestrich-Schreibweise
#        von `dest` zählt mit, weil argparse beides bedient).
#    A3  Aufrufe, die das Skript nur als Konstante weiterreichen
#        (`SCRIPTS=$'…'`, `python3 -m scripts.x`), werden nicht geraten:
#        unbekannte Formen sind GRÜN und werden gezählt („nicht prüfbar“),
#        damit die Wache nie wegen eines Fehlalarms rot wird.
#
#  BEWUSST NICHT GEPRÜFT
#  ---------------------
#    · Keine Ausführung, kein Import des Prüflings: Ein Import kann
#      Seiteneffekte haben (am 18.09.2026 stufte `publish_gate` beim bloßen
#      Aufruf einen LIVE-Artikel auf `draft` zurück). Gelesen wird der AST.
#    · Keine Kurzschalter (`-x`): Sie kollidieren in `argparse` mit Präfixen
#      und Kombinationen; der Bestand nutzt sie nicht.
#    · Keine Variablen (`$FLAG`): Was zur Laufzeit entsteht, ist statisch
#      nicht beweisbar. Ein geratener Befund wäre schlimmer als keiner.
#
#  NUTZUNG
#    python3 scripts/workflow_aufruf_vertrag.py            # Bericht
#    python3 scripts/workflow_aufruf_vertrag.py --check    # Exit 1 bei Verstoß
#    python3 scripts/workflow_aufruf_vertrag.py --json
#    python3 scripts/workflow_aufruf_vertrag.py --selftest
#
#  EXIT  0 = Vertrag erfüllt · 1 = Verstoß (nur mit --check) · 2 = Werkzeugfehler
# ============================================================
from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

#: Adapter, die ihre Argumente unverändert an ein anderes Skript weiterreichen
#: (`hemingway_check.py` → `readability_check.py`). Die Datei ist ein Vertrag:
#: Ein Eintrag, der keinen Fund mehr erklärt, wird selbst zum Befund (A4) –
#: dieselbe Alterungsregel wie bei den Ausnahmen der übrigen Wachen.
WEITERLEITUNG_DATEI = ROOT / "data" / "workflow_aufruf_weiterleitung.yaml"

#: Der Aufruf-Detektor. Bewusst eng: `python3`/`python` + optional `-u`
#: (ungepufferte Ausgabe, im Repo üblich) + `scripts/<name>.py`.
#: Ein `-m module`-Aufruf hat keinen Dateipfad und wird nicht geprüft (A3).
AUFRUF = re.compile(
    r"(?:^|[\s;&|(`])python3?\s+(?:-u\s+)?(?P<script>scripts/[A-Za-z0-9_./-]+\.py)")
#: Terminatoren, die den Argumentbereich eines Aufrufs beenden.
#: `--` zählt nur als EIGENES Wort (Ende der Optionen), nicht als Anfang
#: eines Schalters – sonst beendet der erste Schalter den Bereich und die
#: Wache prüft nichts (real passiert beim Bau am 14.11.2026: 0 von 908
#: Aufrufen geprüft, trotzdem „grün“). Genau diese Sorte stilles Grün ist
#: teurer als ein Fehlalarm.
ENDE = re.compile(r"(?:^|\s)(?:--(?=\s|$)|&&|\|\||;|\|(?!=)|[<>])")
#: Ein langer Schalter. `--flag=wert` wird auf `--flag` verkürzt.
SCHALTER = re.compile(r"(?<![\w-])(--[A-Za-z0-9][A-Za-z0-9_-]*)")


class VertragsFehler(RuntimeError):
    """Die Prüfung selbst ist nicht lauffähig – kein Vertragsverstoß."""


# --------------------------------------------------------------- Skript-Seite
def schalter_von(pfad: Path) -> set[str]:
    """Alle langen Schalter, die das Skript überhaupt annehmen KANN.

    WARUM SO GROSSZÜGIG (Lehre aus dem ersten Bau, 14.11.2026): Der Bestand
    nimmt Schalter auf drei Wegen an – `argparse.add_argument`, `"--x" in
    sys.argv` und eigene Helfer (`_flag("--x")`). Eine Prüfung, die nur
    `add_argument` liest, meldete beim ersten Lauf 326 „Verstöße“, davon
    praktisch alle falsch (z. B. `manifest_guard.py --selftest`). Eine Wache,
    die Fehlalarme produziert, wird stillgelegt – und schützt dann nichts.

    Deshalb gilt: JEDE Zeichenketten-Konstante des Skripts, die mit `--`
    beginnt, zählt als bekannter Schalter (plus die `dest`-Schreibweise von
    argparse). Der Preis ist ein möglicherweise übersehener Fall, wenn ein
    fremder Schalter nur in einer Hilfe-Zeile steht. Der Nutzen ist ein
    Detektor, der nur anschlägt, wenn ein Name im Skript NIRGENDS vorkommt –
    und genau das war der Schaden (44 korrekt markierte Tonspuren, dauerhaft
    rotes Siegel wegen `--check`). Auch der Modulkopf zählt mit: Die Frage
    lautet hier nicht „wird der Schalter ausgewertet?“, sondern „existiert
    dieser Name in diesem Werkzeug überhaupt?“
    """
    try:
        baum = ast.parse(pfad.read_text(encoding="utf-8", errors="replace"))
    except SyntaxError as exc:          # Der Syntax-Job ist die zuständige Wache
        raise VertragsFehler(f"{pfad.name}: nicht lesbar ({exc})") from exc
    gefunden: set[str] = {"--help"}     # argparse bietet ihn immer an
    for knoten in ast.walk(baum):
        if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str) \
                and knoten.value.startswith("--") and len(knoten.value) > 2:
            gefunden.add(knoten.value.split("=", 1)[0].strip())
        if isinstance(knoten, ast.Call) \
                and isinstance(knoten.func, ast.Attribute) \
                and knoten.func.attr == "add_argument":
            for kw in knoten.keywords:
                # `dest="trockenlauf"` bedient `--trockenlauf`.
                if kw.arg == "dest" and isinstance(kw.value, ast.Constant) \
                        and isinstance(kw.value.value, str):
                    gefunden.add("--" + kw.value.value.replace("_", "-"))
    return {s for s in gefunden if len(s) > 2 and not any(c.isspace() for c in s)}


# ------------------------------------------------------------- Workflow-Seite
def _zeilen_verbinden(text: str) -> list[str]:
    """Logische Shell-Zeilen: Backslash-Fortsetzungen werden gezogen.

    Mehrzeilige Regexe sind im Haus verboten (ReDoS-Klasse, Code-Scanning
    Alert 87). Deshalb zeilenweise, mit klaren Grenzen.
    """
    zeilen: list[str] = []
    puffer = ""
    for roh in text.splitlines():
        zeile = roh.rstrip()
        if zeile.endswith("\\"):
            puffer += zeile[:-1] + " "
            continue
        zeilen.append(puffer + zeile)
        puffer = ""
    if puffer:
        zeilen.append(puffer)
    return zeilen


def aufrufe_aus_text(text: str) -> list[tuple[str, list[str], int]]:
    """(Skriptpfad, Schalter, Zeilennummer) aller `python3 scripts/…`-Aufrufe."""
    treffer: list[tuple[str, list[str], int]] = []
    for nummer, zeile in enumerate(_zeilen_verbinden(text), start=1):
        # Eine auskommentierte Zeile in einem `run:`-Block ist ein SHELL-
        # Kommentar, kein Aufruf. Ohne diese Zeile meldet die Wache den
        # Beispielbefehl aus einem Erklär-Kommentar (`# python3 scripts/…`)
        # als Verstoß – und wer einmal einen Fehlalarm gesehen hat, schaltet
        # die Wache ab. (YAML-Kommentare sieht sie ohnehin nicht, weil sie
        # `run:`-Blöcke liest.)
        if zeile.lstrip().startswith("#"):
            continue
        if "scripts/" not in zeile or "python" not in zeile:
            continue
        treffer_zeile = list(AUFRUF.finditer(zeile))
        for i, m in enumerate(treffer_zeile):
            rest = zeile[m.end():]
            ende = ENDE.search(rest)
            bereich = rest[:ende.start()] if ende else rest
            # VERSCHACHTELTER AUFRUF: `reserve_operations.py --run python3
            # scripts/reserve_intake.py --apply` reicht alles hinter `--run`
            # an ein ANDERES Werkzeug weiter (argparse.REMAINDER). Ohne diese
            # Grenze erbt der Wrapper die Schalter des Kindes – real passiert
            # am 14.11.2026 (4 von 17 Fehlalarmen). Alles ab dem nächsten
            # Skriptaufruf gehört diesem nächsten Aufruf.
            naechster = zeile.find("python", m.end())
            if 0 <= naechster < m.end() + len(bereich):
                bereich = rest[:naechster - m.end()]
            schalter = [s.split("=", 1)[0] for s in SCHALTER.findall(bereich)]
            treffer.append((m.group("script"), schalter, nummer))
    return treffer


def run_bloecke(ordner: Path | None = None) -> list[tuple[str, str, str]]:
    """(Workflow-Datei, Jobname, run-Text) – YAML gelesen, nicht gegrept.

    WARUM YAML STATT TEXTSUCHE: Ein `run:`-Block ist ausführbarer Code, ein
    Kommentar daneben ist Prosa. Wer den ganzen Dateitext durchsucht, meldet
    irgendwann den Beispielbefehl aus einem Erklär-Kommentar als Verstoß –
    und eine Wache, die Prosa prüft, wird abgeschaltet.
    """
    try:
        import yaml
    except ImportError as exc:          # pragma: no cover – requirements-ci pinnt PyYAML
        raise VertragsFehler("PyYAML fehlt – Vertrag nicht prüfbar") from exc
    ordner = Path(ordner) if ordner is not None else WORKFLOWS
    bloecke: list[tuple[str, str, str]] = []
    for datei in sorted(ordner.glob("*.yml")) + sorted(ordner.glob("*.yaml")):
        try:
            daten = yaml.safe_load(datei.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            raise VertragsFehler(f"{datei.name}: YAML nicht lesbar ({exc})") from exc
        if not isinstance(daten, dict):
            continue
        for job_name, job in (daten.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            for schritt in job.get("steps") or []:
                if not isinstance(schritt, dict):
                    continue
                run = schritt.get("run")
                if isinstance(run, str):
                    bloecke.append((datei.name, str(job_name), run))
    return bloecke


def weiterleitungen(root: Path = ROOT) -> dict[str, str]:
    """Adapter → Zielskript. Ein Adapter reicht Argumente unverändert weiter.

    WARUM DAS NÖTIG IST: `hemingway_check.py` ist bewusst ein dünner Adapter
    und ruft `readability_check.main(sys.argv[1:])` auf. Statisch sieht das
    aus wie „Schalter unbekannt“ – real ist er dort implementiert. Diese
    Wache würde den Adapter also fälschlich rot melden. Statt einer
    Ausnahmeliste mit Bauchgefühl folgt sie dem ECHTEN Weiterleitungsziel:
    Die Schalter des Ziels zählen für den Adapter mit.
    """
    datei = root / "data" / "workflow_aufruf_weiterleitung.yaml"
    if not datei.is_file():
        return {}
    try:
        import yaml
        daten = yaml.safe_load(datei.read_text(encoding="utf-8")) or {}
    except Exception as exc:            # noqa: BLE001 – fail-closed, kein Raten
        raise VertragsFehler(f"{datei.name} nicht lesbar: {exc}") from exc
    ziele: dict[str, str] = {}
    for quelle, wert in (daten.get("adapter") or {}).items():
        ziel = (wert or {}).get("ziel")
        if not ziel:
            raise VertragsFehler(f"{datei.name}: Adapter {quelle} ohne `ziel`")
        ziele[str(quelle)] = str(ziel)
    return ziele


# ---------------------------------------------------------------- Der Vertrag
def befunde(root: Path | str = ROOT) -> tuple[list[dict], dict]:
    """Alle Verstöße plus eine Zählung dessen, was geprüft wurde."""
    root = Path(root)
    workflow_ordner = root / ".github" / "workflows"
    if not workflow_ordner.is_dir():
        raise VertragsFehler("kein .github/workflows – falscher Wurzelpfad?")
    bloecke = run_bloecke(workflow_ordner)
    adressen = weiterleitungen(root)
    benutzt: set[str] = set()
    gefunden: list[dict] = []
    geprueft = 0
    nicht_pruefbar = 0
    dateien: dict[str, set[str] | None] = {}
    for workflow, job, text in bloecke:
        for skript, schalter, zeile in aufrufe_aus_text(text):
            pfad = root / skript
            if skript not in dateien:
                dateien[skript] = schalter_von(pfad) if pfad.is_file() else None
                dateiname = skript.rsplit("/", 1)[-1]
                if dateien[skript] is not None and dateiname in adressen:
                    ziel = root / "scripts" / adressen[dateiname]
                    if not ziel.is_file():
                        raise VertragsFehler(
                            f"{WEITERLEITUNG_DATEI.name}: Ziel "
                            f"{adressen[dateiname]} von {skript} fehlt")
                    dateien[skript] = dateien[skript] | schalter_von(ziel)
                    benutzt.add(dateiname)
            bekannt = dateien[skript]
            if bekannt is None:
                gefunden.append({"art": "A1", "workflow": workflow, "job": job,
                                 "zeile": zeile, "skript": skript,
                                 "meldung": f"{skript} existiert nicht"})
                continue
            if not schalter:
                nicht_pruefbar += 1
                continue
            geprueft += 1
            fremd = [s for s in schalter if s not in bekannt]
            if fremd:
                gefunden.append({"art": "A2", "workflow": workflow, "job": job,
                                 "zeile": zeile, "skript": skript,
                                 "meldung": (f"{skript} kennt {', '.join(sorted(fremd))} "
                                             f"nicht (argparse: {len(bekannt)} Schalter) – "
                                             "der Aufruf endet mit Exit 2 und sieht im "
                                             "Ticket wie ein Inhaltsbefund aus")})
    for adapter in sorted(set(adressen) - benutzt):
        gefunden.append({"art": "A4", "workflow": "-", "job": "-", "zeile": 0,
                         "skript": f"scripts/{adapter}",
                         "meldung": (f"Weiterleitung {adapter} → "
                                     f"{adressen[adapter]} wird von keinem "
                                     "Aufruf gebraucht (Eintrag altern lassen "
                                     "oder entfernen)")})
    return gefunden, {"aufrufe": geprueft + nicht_pruefbar, "geprueft": geprueft,
                      "ohne_schalter": nicht_pruefbar,
                      "workflows": len({w for w, _j, _t in bloecke})}


# ------------------------------------------------------------------- Ausgabe
def _text(funde: list[dict], zahlen: dict) -> str:
    if not funde:
        return (f"✅ Workflow-Aufruf-Vertrag erfüllt: {zahlen['geprueft']} Aufruf(e) "
                f"mit Schaltern in {zahlen['workflows']} Workflow(s) geprüft, "
                f"0 Verstoß.")
    zeilen = [f"🛑 Workflow-Aufruf-Vertrag: {len(funde)} Verstoß(e) –",
              f"   {zahlen['geprueft']} Aufruf(e) geprüft, "
              f"{zahlen['workflows']} Workflow(s).", ""]
    for f in funde:
        zeilen.append(f"   [{f['art']}] {f['workflow']} · {f['job']} · "
                      f"run-Zeile {f['zeile']}: {f['meldung']}")
    zeilen.append("")
    zeilen.append("   Heilung: den Aufruf an das argparse des Skripts anpassen ODER "
                  "den Schalter im Skript ergänzen (Alias).")
    return "\n".join(zeilen)


# ----------------------------------------------------------------- Selbsttest
def selftest() -> int:
    """Sabotage-Proben: Die Wache muss rot werden, wenn der Vertrag bricht."""
    import tempfile

    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "scripts").mkdir()
        (root / ".github" / "workflows").mkdir(parents=True)
        (root / "scripts" / "werkzeug.py").write_text(
            "import argparse\n"
            "def main():\n"
            "    p = argparse.ArgumentParser()\n"
            "    g = p.add_mutually_exclusive_group()\n"
            "    g.add_argument('--gate', '--check', dest='gate', action='store_true')\n"
            "    p.add_argument('--dir', default='.')\n"
            "    p.add_argument('--mit-wert=egal')\n"
            "    p.add_argument('--selftest', action='store_true')\n"
            "    return p.parse_args()\n",
            encoding="utf-8")

        def proben(name: str, run: str) -> list[dict]:
            (root / ".github" / "workflows" / "wf.yml").write_text(
                "on: push\njobs:\n  j:\n    runs-on: ubuntu-24.04\n"
                "    steps:\n      - name: s\n        run: |\n"
                f"          {run}\n", encoding="utf-8")
            return befunde(root)[0]

        if proben("gut", "python3 scripts/werkzeug.py --gate --dir public"):
            fehler.append("gültiger Aufruf wurde gemeldet")
        if proben("alias", "python3 scripts/werkzeug.py --check --dir public"):
            fehler.append("Alias-Schalter (--check) wurde als Verstoß gemeldet")
        if proben("wert", "python3 scripts/werkzeug.py --mit-wert=7"):
            fehler.append("--schalter=wert wurde nicht erkannt")
        if not proben("fremd", "python3 scripts/werkzeug.py --gibtesnicht --dir x"):
            fehler.append("unbekannter Schalter wurde NICHT gemeldet")
        if not proben("fehlt", "python3 scripts/geloescht.py --gate"):
            fehler.append("fehlendes Skript wurde NICHT gemeldet")
        if proben("kommentar", "# python3 scripts/werkzeug.py --nur-im-kommentar"):
            fehler.append("Kommentar wurde als Aufruf geprüft (YAML- statt Textsuche)")
        if proben("fortsetzung",
                  "python3 scripts/werkzeug.py --dir \\\n            public"):
            fehler.append("Backslash-Fortsetzung wurde nicht gezogen")
        if proben("variabel", "python3 scripts/werkzeug.py $FLAG"):
            fehler.append("Variablenaufruf wurde geraten statt grün gelassen")
        # `--` beendet die Optionen. Der zweite Aufruf in derselben Zeile ist
        # ein eigener Aufruf und wird für sich geprüft (hier gültig).
        if proben("nach-doppelstrich",
                  "python3 scripts/werkzeug.py --gate -- "
                  "python3 scripts/werkzeug.py --selftest"):
            fehler.append("Argumente hinter `--` wurden dem falschen Aufruf zugeordnet")
        if not proben("nach-doppelstrich-fremd",
                      "python3 scripts/werkzeug.py --gate -- "
                      "python3 scripts/werkzeug.py --gibtesnicht"):
            fehler.append("fremder Schalter hinter `--` wurde nicht geprüft")
        # Ein Aufruf, dessen Argumente ein anderes Werkzeug sind, darf nicht
        # dem ersten zugeschlagen werden (`ci_tests.py … -- python3 -m unittest`).
        _zahlen = None
    for f in fehler:
        print(f"❌ {f}")
    if fehler:
        return 2
    print("✅ Workflow-Aufruf-Vertrag-Selbsttest: gültiger Aufruf grün, Alias grün, "
          "fremder Schalter rot, fehlendes Skript rot, Kommentar/Fortsetzung/"
          "Variable/`--` korrekt behandelt.")
    return 0


# ---------------------------------------------------------------------- Main
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Exit 1 bei einem Verstoß (sonst nur Bericht)")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    try:
        funde, zahlen = befunde()
    except VertragsFehler as exc:
        print(f"Workflow-Aufruf-Vertrag nicht prüfbar: {exc}")
        return 2

    if args.json:
        print(json.dumps({"befunde": funde, "zahlen": zahlen}, ensure_ascii=False,
                         indent=2))
    else:
        print(_text(funde, zahlen))
    if args.check and funde:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
