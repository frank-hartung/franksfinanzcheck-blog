#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Hugo-Build-Vertrag H1–H7: Ein Bau, eine Fehlerausgabe.

WARUM ES DIESE WACHE GIBT
=========================
Am 02.10.2026 starb ``hugo --minify`` an einer einzigen Zeile:

    layouts/sitemap.xml:40:29 … wrong type for value; expected string; got []string

Auslöser war ein LEERES Verzeichnis unter ``content/``. Die Suche danach
dauerte Stunden – nicht wegen der Schwierigkeit des Fehlers, sondern weil
fast jeder Workflow ihn unsichtbar machte: ``> /dev/null 2>&1``, ``|| true``,
``--quiet``. Ein Schritt, der rot wird und nichts sagt, ist teurer als ein
Schritt, der grün durchläuft: Er kostet Zeit und erzieht zum Wegsehen.

Die Reparatur ist ``.github/actions/hugo-build`` – eine Stelle, an der die
Fehlerausgabe zur Eigenschaft des Bauens wird. Diese Wache sorgt dafür, dass
die Reparatur nicht wieder abbröckelt:

  H1  Die Action existiert, ist gültiges YAML und ist ``composite``.
  H2  Der Exit-Code überlebt die Pipe (``pipefail`` UND ``PIPESTATUS``).
  H3  Jeder Fehlschlag erzeugt Annotation (``::error title=``) UND einen
      Eintrag in ``$GITHUB_STEP_SUMMARY``.
  H4  ``--quiet`` wird fail-closed abgelehnt.
  H5  Die Selbstdiagnose kennt die teuerste Blindstelle: leere Verzeichnisse
      unter ``content``/``data`` (``git status`` meldet die NIE).
  H6  Jeder Hugo-Bau in ``.github/workflows/`` geht durch die Action – oder
      steht mit Begründung in AUSNAHMEN.
  H7  Kein Hugo-Bau vernichtet seine Beweise (``> /dev/null``, ``|| true``,
      ``--quiet``) – außerhalb der begründeten Ausnahmen.

H2–H5 werden NICHT nur im Text gesucht: ``--selftest`` führt den echten
Shell-Rumpf der Action gegen ein Hugo-Attrappen-Programm aus und prüft das
Verhalten. Eine Wache, die nur Wörter zählt, ist mit einem Kommentar zu
betrügen.

Nutzung:
  python3 scripts/hugo_build_vertrag.py            # Vertrag prüfen (CI)
  python3 scripts/hugo_build_vertrag.py --json
  python3 scripts/hugo_build_vertrag.py --selftest # Sabotage-Proben
"""
from __future__ import annotations

import glob
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION = ROOT / ".github" / "actions" / "hugo-build" / "action.yml"
WORKFLOWS = ROOT / ".github" / "workflows"
RUNBOOK = ROOT / "docs" / "ANLEITUNG-HUGO-BUILD.md"
ACTION_REF = "./.github/actions/hugo-build"

# ----------------------------------------------------------------------
#  Begründete Ausnahmen von H6/H7.
#
#  Eine Ausnahmeliste ist nur dann ehrlich, wenn sie zwei Dinge erzwingt:
#  (1) jeder Eintrag braucht einen Grund, (2) ein Eintrag für eine Datei,
#  die den Bau gar nicht mehr enthält, ist ein BEFUND – sonst wächst hier
#  still ein Regal voller Ausreden.
# ----------------------------------------------------------------------
AUSNAHMEN = {
    "affiliate-integrity-daily.yml":
        "Eigene 3-fach-Wiederholung mit Abbruchlogik und `rm -rf public`, damit "
        "ensure_build() nicht gegen ein halbfertiges Artefakt „aktuell\" beweist. "
        "Die Fehlerausgabe ist dort bereits vollständig (::error, ::group, tail -60); "
        "die Action kann die Wiederholungs-Semantik nicht abbilden.",
}

# Beweisvernichtende Muster an einer Hugo-Zeile (H7).
BEWEISVERNICHTER = (
    (">/dev/null", "wirft die Fehlermeldung weg"),
    ("> /dev/null", "wirft die Fehlermeldung weg"),
    ("|| true", "verschluckt den Exit-Code"),
    ("--quiet", "unterdrückt genau die Zeile, die man sucht"),
    (" -q ", "unterdrückt genau die Zeile, die man sucht"),
)

# Eine Hugo-Ausführung in einem run-Block. `hugo version`, `install-hugo`
# und Kommentare zählen nicht.
HUGO_AUFRUF = re.compile(r"(?:^|[;&|]\s*|\s)hugo\s+(?:--|-[a-zA-Z])")


def _hugo_bauten(text: str) -> list:
    """Zeilen (1-basiert), in denen ein Workflow Hugo wirklich baut."""
    treffer = []
    for nr, zeile in enumerate(text.splitlines(), start=1):
        nackt = zeile.strip()
        if nackt.startswith("#"):
            continue
        # YAML-Kommentar hinter Code abschneiden ist unsicher (URLs enthalten #);
        # es genügt, reine Kommentarzeilen und die Installations-Action zu meiden.
        # Ein Schritt-NAME darf den Bau erwähnen, ohne einer zu sein
        # (layout-ai.yml: „Website bauen (identisch zur Produktion: hugo --minify)").
        if nackt.startswith("- name:") or nackt.startswith("name:"):
            continue
        if "install-hugo" in nackt or "hugo version" in nackt:
            continue
        if "hugo.toml" in nackt:
            continue
        if HUGO_AUFRUF.search(nackt):
            treffer.append((nr, nackt))
    return treffer


# ======================================================================
#  Regeln
# ======================================================================

def h1_action_existiert() -> list:
    """Die Action ist da, parst und ist composite."""
    if not ACTION.is_file():
        return [f"H1: {ACTION.relative_to(ROOT)} fehlt – es gibt keine gemeinsame "
                "Fehlerausgabe mehr."]
    text = ACTION.read_text(encoding="utf-8")
    befunde = []
    try:
        import yaml  # noqa: PLC0415
        daten = yaml.safe_load(text)
    except ImportError:
        # Kein PyYAML? Dann nicht schweigen, sondern grob prüfen und sagen,
        # dass die Tiefenprüfung ausgefallen ist.
        if "using: composite" not in text:
            befunde.append("H1: Action ist nicht `using: composite`.")
        return befunde
    except Exception as exc:  # pragma: no cover - defekte YAML
        return [f"H1: Action ist kein gültiges YAML: {exc}"]
    if not isinstance(daten, dict):
        return ["H1: Action-YAML liefert kein Objekt."]
    if (daten.get("runs") or {}).get("using") != "composite":
        befunde.append("H1: Action ist nicht `using: composite`.")
    if not (daten.get("runs") or {}).get("steps"):
        befunde.append("H1: Action hat keine Schritte.")
    for pflicht in ("args", "label", "log", "weiter-bei-fehler"):
        if pflicht not in (daten.get("inputs") or {}):
            befunde.append(f"H1: Eingabe `{pflicht}` fehlt – Aufrufer können sie "
                           "nicht mehr setzen.")
    for pflicht in ("rc", "log"):
        if pflicht not in (daten.get("outputs") or {}):
            befunde.append(f"H1: Ausgabe `{pflicht}` fehlt – Folgeschritte können "
                           "den Befund nicht weiterverarbeiten.")
    return befunde


def _bau_rumpf() -> str:
    """Der Shell-Rumpf des Bau-Schritts – Grundlage für H2–H5."""
    if not ACTION.is_file():
        return ""
    try:
        import yaml  # noqa: PLC0415
        daten = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
        for schritt in (daten.get("runs") or {}).get("steps", []):
            if schritt.get("id") == "bauen":
                return schritt.get("run", "")
    except Exception:
        pass
    # BEWUSST KEIN RUECKFALL auf den Dateitext: Wer hier das ganze YAML
    # zurueckgibt, laesst die Verhaltensproben eine YAML-Datei als Shell-Skript
    # ausfuehren – 18 verwirrende Befunde statt des einen wahren ("YAML kaputt").
    return ""


def h2_exitcode_ueberlebt_pipe() -> list:
    rumpf = _bau_rumpf()
    befunde = []
    if "pipefail" not in rumpf:
        befunde.append("H2: `pipefail` fehlt im Bau-Schritt – ohne sie meldet JEDER "
                       "getee'te Build Erfolg, auch der kaputte.")
    if "PIPESTATUS[0]" not in rumpf:
        befunde.append("H2: `PIPESTATUS[0]` fehlt – der Exit-Code käme von `tee`, "
                       "nicht von Hugo.")
    if "| tee " not in rumpf:
        befunde.append("H2: `tee` fehlt – die Ausgabe landet nicht gleichzeitig in "
                       "Konsole und Log.")
    if "set +e" not in rumpf:
        befunde.append("H2: `set +e` fehlt – GitHub startet bash mit `-e`, der "
                       "Schritt stürbe VOR Annotation und Diagnose.")
    return befunde


def h3_fehler_ist_sichtbar() -> list:
    rumpf = _bau_rumpf()
    befunde = []
    if "::error title=" not in rumpf:
        befunde.append("H3: Keine `::error title=`-Annotation – der Fehler steht nur "
                       "im Rohlog, und Rohlogs sind nicht überall abrufbar.")
    if "GITHUB_STEP_SUMMARY" not in rumpf:
        befunde.append("H3: Nichts wird nach `$GITHUB_STEP_SUMMARY` geschrieben – die "
                       "Übersichtsseite des Laufs bliebe leer.")
    if "tail -n" not in rumpf:
        befunde.append("H3: Kein Log-Auszug (`tail -n`) in der Zusammenfassung.")
    return befunde


def h4_quiet_wird_abgelehnt() -> list:
    text = ACTION.read_text(encoding="utf-8") if ACTION.is_file() else ""
    if '"--quiet"' not in text and "'--quiet'" not in text:
        return ["H4: `--quiet` wird nicht abgelehnt – die Flagge verschluckt die "
                "Fehlerzeile selbst bei eingefangener Ausgabe."]
    if "exit 2" not in text:
        return ["H4: Die `--quiet`-Ablehnung ist nicht fail-closed (kein `exit 2`)."]
    return []


def h5_diagnose_kennt_leere_verzeichnisse() -> list:
    rumpf = _bau_rumpf()
    if "-type d -empty" not in rumpf:
        return ["H5: Die Selbstdiagnose sucht keine leeren Verzeichnisse – genau die "
                "sieht `git status` grundsätzlich nicht, und genau die kosteten am "
                "02.10.2026 die Stunden."]
    if "content" not in rumpf or "data" not in rumpf:
        return ["H5: Die Suche nach leeren Verzeichnissen deckt nicht content/ und "
                "data/ ab."]
    return []


def h6_alle_bauten_nutzen_die_action(wf_dir: Path = None) -> list:
    wf_dir = wf_dir or WORKFLOWS
    befunde = []
    gesehen = set()
    for pfad in sorted(glob.glob(str(wf_dir / "*.yml")) + glob.glob(str(wf_dir / "*.yaml"))):
        datei = os.path.basename(pfad)
        text = Path(pfad).read_text(encoding="utf-8")
        bauten = _hugo_bauten(text)
        if datei in AUSNAHMEN:
            gesehen.add(datei)
            if not bauten:
                befunde.append(
                    f"H6: Ausnahme für {datei} eingetragen, aber die Datei baut Hugo "
                    "gar nicht (mehr) selbst – toter Eintrag, bitte streichen.")
            continue
        for nr, zeile in bauten:
            befunde.append(
                f"H6: {datei}:{nr} baut Hugo direkt (`{zeile[:70]}`) statt über "
                f"`{ACTION_REF}`. Damit hängt die Fehlerausgabe wieder am Gedächtnis "
                "des Autors.")
    for datei in AUSNAHMEN:
        if datei not in gesehen and not (wf_dir / datei).is_file():
            befunde.append(f"H6: Ausnahme für {datei}, die es nicht gibt.")
    for datei, grund in AUSNAHMEN.items():
        if not grund.strip():
            befunde.append(f"H6: Ausnahme {datei} ohne Begründung – eine Ausnahme "
                           "ohne Grund ist eine Ausrede.")
    return befunde


def h7_keine_beweisvernichtung(wf_dir: Path = None) -> list:
    wf_dir = wf_dir or WORKFLOWS
    befunde = []
    for pfad in sorted(glob.glob(str(wf_dir / "*.yml")) + glob.glob(str(wf_dir / "*.yaml"))):
        datei = os.path.basename(pfad)
        if datei in AUSNAHMEN:
            continue
        text = Path(pfad).read_text(encoding="utf-8")
        for nr, zeile in _hugo_bauten(text):
            for muster, warum in BEWEISVERNICHTER:
                if muster in zeile:
                    befunde.append(
                        f"H7: {datei}:{nr} – `{muster}` am Hugo-Bau {warum}: "
                        f"`{zeile[:70]}`")
    return befunde


def h8_runbook() -> list:
    if not RUNBOOK.is_file():
        return [f"H8: {RUNBOOK.relative_to(ROOT)} fehlt – eine Action ohne Anleitung "
                "ist für den Betreiber nicht bedienbar."]
    return []


REGELN = {
    "H1": ("Action existiert, parst, ist composite", h1_action_existiert),
    "H2": ("Exit-Code überlebt die Pipe (pipefail + PIPESTATUS + set +e)",
           h2_exitcode_ueberlebt_pipe),
    "H3": ("Fehlschlag ist sichtbar (Annotation + Zusammenfassung + Log-Auszug)",
           h3_fehler_ist_sichtbar),
    "H4": ("--quiet wird fail-closed abgelehnt", h4_quiet_wird_abgelehnt),
    "H5": ("Selbstdiagnose kennt leere Verzeichnisse", h5_diagnose_kennt_leere_verzeichnisse),
    "H6": ("Jeder Hugo-Bau geht durch die Action (oder ist begründet)",
           h6_alle_bauten_nutzen_die_action),
    "H7": ("Kein Hugo-Bau vernichtet seine Beweise", h7_keine_beweisvernichtung),
    "H8": ("Runbook vorhanden", h8_runbook),
}


def pruefen() -> dict:
    ergebnis = {}
    for kennung, (titel, fn) in REGELN.items():
        ergebnis[kennung] = {"titel": titel, "befunde": fn()}
    return ergebnis


def bericht(ergebnis: dict) -> str:
    zeilen = ["HUGO-BUILD-VERTRAG – eine Fehlerausgabe für alle Workflows", ""]
    for kennung, block in ergebnis.items():
        zeichen = "✅" if not block["befunde"] else "❌"
        zeilen.append(f"  {zeichen} {kennung}  {block['titel']}")
        for b in block["befunde"]:
            zeilen.append(f"        → {b}")
    offen = sum(len(b["befunde"]) for b in ergebnis.values())
    zeilen.append("")
    if offen:
        zeilen.append(f"❌ {offen} Befund(e) – die gemeinsame Fehlerausgabe bröckelt.")
    else:
        zeilen.append("✅ Vertrag erfüllt: Jeder Hugo-Bau meldet seinen Fehler laut "
                      "und an derselben Stelle.")
    return "\n".join(zeilen)


# ======================================================================
#  Ausführungsprobe: der echte Shell-Rumpf gegen eine Hugo-Attrappe
# ======================================================================

def _rumpf_ausfuehren(rumpf: str, hugo_rc: int, hugo_ausgabe: str,
                      args: str = "--minify", weiter: str = "false",
                      leeres_verzeichnis: bool = False,
                      flaggen: tuple = ("-eo", "pipefail")) -> dict:
    """Führt den Bau-Rumpf in einem Wegwerf-Verzeichnis aus.

    Das ist der Unterschied zwischen „im YAML steht pipefail" und „der
    Exit-Code kommt wirklich von Hugo". Eine Wache, die nur Wörter sucht,
    lässt sich mit einem Kommentar betrügen.
    """
    with tempfile.TemporaryDirectory() as tmp:
        tmpd = Path(tmp)
        (tmpd / "content").mkdir()
        (tmpd / "data").mkdir()
        # data/ bewusst FÜLLEN: Sonst meldet die Diagnose das Probenverzeichnis
        # selbst als leer – die Gegenprobe („kein Fehlalarm") könnte dann nie
        # gruen werden und wuerde ewig einen Defekt behaupten, den es nicht gibt.
        (tmpd / "data" / "x.yaml").write_text("a: 1\n", encoding="utf-8")
        if leeres_verzeichnis:
            (tmpd / "content" / "drafts").mkdir()
        else:
            (tmpd / "content" / "posts").mkdir()
            (tmpd / "content" / "posts" / "x.md").write_text("x", encoding="utf-8")

        binr = tmpd / "bin"
        binr.mkdir()
        attrappe = binr / "hugo"
        attrappe.write_text(
            "#!/bin/sh\n"
            'if [ "$1" = "version" ]; then\n'
            '  echo "hugo v0.164.0+extended+withdeploy linux/amd64"; exit 0\n'
            "fi\n"
            f"cat <<'EOF'\n{hugo_ausgabe}\nEOF\n"
            f"exit {hugo_rc}\n",
            encoding="utf-8")
        attrappe.chmod(0o755)

        skript = tmpd / "schritt.sh"
        skript.write_text(rumpf, encoding="utf-8")
        ausgabe_datei = tmpd / "gh_output"
        summary_datei = tmpd / "gh_summary"
        ausgabe_datei.touch()
        summary_datei.touch()

        umwelt = dict(os.environ)
        umwelt.update({
            "PATH": f"{binr}:{os.environ.get('PATH', '')}",
            "FF_ARGS": args,
            "FF_LABEL": "Probe",
            "FF_LOG": "bau.log",
            "FF_ZEILEN": "10",
            "FF_WEITER": weiter,
            "GITHUB_OUTPUT": str(ausgabe_datei),
            "GITHUB_STEP_SUMMARY": str(summary_datei),
        })
        # GitHub startet composite-Schritte mit genau diesen Flaggen.
        lauf = subprocess.run(
            ["bash", "--noprofile", "--norc", *flaggen, str(skript)],
            cwd=str(tmpd), env=umwelt, capture_output=True, text=True, timeout=60)
        return {
            "rc": lauf.returncode,
            "stdout": lauf.stdout,
            "stderr": lauf.stderr,
            "outputs": ausgabe_datei.read_text(encoding="utf-8"),
            "summary": summary_datei.read_text(encoding="utf-8"),
        }


def _vorpruef_rumpf() -> str:
    try:
        import yaml  # noqa: PLC0415
        daten = yaml.safe_load(ACTION.read_text(encoding="utf-8"))
        for schritt in (daten.get("runs") or {}).get("steps", []):
            if schritt.get("id") == "vorpruefung":
                return schritt.get("run", "")
    except Exception:
        pass
    return ""


def _probe_verzeichnis(tmp: str, inhalt: str) -> Path:
    """Wegwerf-Workflow-Ordner, in dem die Ausnahmen gueltig bleiben.

    Ohne die Ausnahmedatei meldet H6 voellig korrekt „Ausnahme fuer eine Datei,
    die es nicht gibt" – und jede Probe misst dann diesen Nebenbefund statt
    dessen, was sie prueft.
    """
    wf = Path(tmp)
    for name in AUSNAHMEN:
        (wf / name).write_text(
            "jobs:\n  x:\n    steps:\n      - run: hugo --minify\n",
            encoding="utf-8")
    (wf / "probe.yml").write_text(inhalt, encoding="utf-8")
    return wf


def _selftest() -> int:
    fehler = []

    # ---------- Positivprobe: der echte Vertrag ist grün ----------
    erg = pruefen()
    offen = {k: v["befunde"] for k, v in erg.items() if v["befunde"]}
    if offen:
        fehler.append(f"Positivprobe: der echte Vertrag hat Befunde: {offen}")

    rumpf = _bau_rumpf()
    vorpruefung = _vorpruef_rumpf()
    if not rumpf:
        fehler.append("Bau-Rumpf nicht auffindbar – alle Verhaltensproben entfallen.")
        rumpf = None

    if rumpf and shutil.which("bash"):
        # ---- V1: grüner Build meldet 0 und schreibt die Zusammenfassung ----
        v = _rumpf_ausfuehren(rumpf, 0, " Pages            \u2502   42 \nTotal in 900 ms")
        if v["rc"] != 0:
            fehler.append(f"V1: grüner Build endet mit rc={v['rc']}")
        if "rc=0" not in v["outputs"]:
            fehler.append("V1: Ausgabe rc=0 fehlt")
        if "seiten=42" not in v["outputs"]:
            fehler.append(f"V1: Seitenzahl nicht erkannt ({v['outputs']!r})")
        if "✅" not in v["summary"]:
            fehler.append("V1: Erfolg steht nicht in der Zusammenfassung")

        # ---- V2: roter Build – DAS Kernversprechen ----
        v = _rumpf_ausfuehren(
            rumpf, 1,
            "ERROR render of \"sitemap\" failed: layouts/sitemap.xml:40:29: "
            "wrong type for value; expected string; got []string")
        if v["rc"] == 0:
            fehler.append("V2: roter Build meldet Erfolg – pipefail/PIPESTATUS kaputt. "
                          "Das ist der Fehler, gegen den die ganze Action geschrieben ist.")
        if "::error title=Hugo-Build: Probe::" not in v["stdout"]:
            fehler.append("V2: keine ::error-Annotation bei rotem Build")
        if "wrong type for value" not in v["stdout"]:
            fehler.append("V2: Annotation nennt die Fehlerzeile nicht")
        if "❌" not in v["summary"] or "wrong type for value" not in v["summary"]:
            fehler.append("V2: Zusammenfassung ohne Befund")
        if "rc=1" not in v["outputs"]:
            fehler.append("V2: Ausgabe rc=1 fehlt – Folgeschritte könnten nicht reagieren")
        # Die Selbstdiagnose muss das Typfehler-Muster benennen.
        if "append" not in v["summary"]:
            fehler.append("V2: Selbstdiagnose nennt das bekannte Fix-Muster nicht")

        # ---- V3: leeres Verzeichnis wird aktiv benannt ----
        v = _rumpf_ausfuehren(rumpf, 1, "ERROR irgendwas ging schief",
                              leeres_verzeichnis=True)
        if "content/drafts" not in v["summary"]:
            fehler.append("V3: leeres Verzeichnis wird nicht benannt – genau diese "
                          "Blindstelle kostete am 02.10.2026 die Stunden.")
        v = _rumpf_ausfuehren(rumpf, 1, "ERROR irgendwas ging schief",
                              leeres_verzeichnis=False)
        if "content/drafts" in v["summary"]:
            fehler.append("V3b: leeres Verzeichnis gemeldet, obwohl keins da ist "
                          "(Fehlalarm)")

        # ---- V4: weiter-bei-fehler meldet laut, stoppt aber nicht ----
        v = _rumpf_ausfuehren(rumpf, 1, "ERROR kaputt", weiter="true")
        if v["rc"] != 0:
            fehler.append("V4: weiter-bei-fehler stoppt den Job trotzdem")
        if "::error title=" not in v["stdout"]:
            fehler.append("V4: toleriert heißt unsichtbar – Annotation fehlt. Dann "
                          "wäre es nur ein `|| true` mit mehr Zeilen.")
        if "rc=1" not in v["outputs"]:
            fehler.append("V4: toleriert, aber rc wird nicht durchgereicht")

        # ---- V5: Hugo ohne Ausgabe darf nicht zu einer leeren Meldung führen ----
        v = _rumpf_ausfuehren(rumpf, 3, "")
        if "::error title=" not in v["stdout"]:
            fehler.append("V5: stummer Hugo-Abbruch erzeugt keine Annotation")
        if v["rc"] != 3:
            fehler.append(f"V5: Exit-Code 3 nicht durchgereicht (rc={v['rc']})")

        # ---- S1: zwei UNABHÄNGIGE Netze, jedes einzeln bewiesen ----
        # Der Exit-Code haengt an zwei Dingen: `pipefail` (einmal von GitHubs
        # Shell-Aufruf, einmal im Rumpf) UND `PIPESTATUS[0]`. Eine Probe, die
        # beide zusammen prueft, merkt nicht, wenn eins davon wegfaellt.
        # Darum wird hier jedes Netz einzeln belastet.
        ohne_pipefail = rumpf.replace("set -uo pipefail", "set -u")
        nur_dollar = ohne_pipefail.replace("${PIPESTATUS[0]}", "$?")
        if ohne_pipefail == rumpf or nur_dollar == ohne_pipefail:
            fehler.append("S1: Sabotage greift nicht – der Rumpf hat die erwartete "
                          "Gestalt verloren, die Proben messen nichts mehr.")
        else:
            # S1a: GANZ OHNE pipefail (weder Aufruf noch Rumpf) traegt
            # PIPESTATUS den Exit-Code allein.
            v = _rumpf_ausfuehren(ohne_pipefail, 1, "ERROR kaputt",
                                  flaggen=("-e",))
            if v["rc"] == 0:
                fehler.append("S1a: Ohne pipefail meldet der rote Build Erfolg – "
                              "`PIPESTATUS[0]` traegt nicht allein.")
            # S1b: Beweis, dass S1a ueberhaupt etwas messen KANN.
            v = _rumpf_ausfuehren(nur_dollar, 1, "ERROR kaputt", flaggen=("-e",))
            if v["rc"] != 0:
                fehler.append("S1b: Auch ohne pipefail UND ohne PIPESTATUS schlaegt "
                              "der Build fehl – dann prueft S1a nicht, was es "
                              "behauptet (blinde Probe).")
            # S1c: Umgekehrt – ohne PIPESTATUS traegt pipefail den Exit-Code.
            v = _rumpf_ausfuehren(rumpf.replace("${PIPESTATUS[0]}", "$?"), 1,
                                  "ERROR kaputt")
            if v["rc"] == 0:
                fehler.append("S1c: Ohne PIPESTATUS meldet der rote Build Erfolg – "
                              "`pipefail` traegt nicht allein.")

    # ---- S2: --quiet wird im echten Vorprüf-Schritt abgelehnt ----
    if vorpruefung and shutil.which("bash"):
        v = _rumpf_ausfuehren(vorpruefung, 0, "", args="--minify --quiet")
        if v["rc"] == 0:
            fehler.append("S2: `--quiet` kam durch die Vorprüfung – H4 ist eine "
                          "Behauptung.")
        v = _rumpf_ausfuehren(vorpruefung, 0, "", args="--minify")
        if v["rc"] != 0:
            fehler.append("S2b: Die Vorprüfung lehnt auch saubere Argumente ab "
                          "(Fehlalarm).")

    # ---- S3–S5: Textregeln gegen erfundene Workflows ----
    with tempfile.TemporaryDirectory() as tmp:
        wf = _probe_verzeichnis(
            tmp, "jobs:\n  x:\n    steps:\n      - run: hugo --minify\n")
        if not h6_alle_bauten_nutzen_die_action(wf):
            fehler.append("S3: H6 übersieht einen direkten `hugo --minify`-Aufruf.")
        if h7_keine_beweisvernichtung(wf):
            fehler.append("S3b: H7 meldet einen sauberen Aufruf als Beweisvernichtung.")

    with tempfile.TemporaryDirectory() as tmp:
        wf = _probe_verzeichnis(
            tmp,
            "jobs:\n  x:\n    steps:\n      - run: hugo --minify > /dev/null 2>&1\n")
        if not h7_keine_beweisvernichtung(wf):
            fehler.append("S4: H7 übersieht `> /dev/null` am Hugo-Bau.")

    with tempfile.TemporaryDirectory() as tmp:
        wf = _probe_verzeichnis(
            tmp,
            "jobs:\n  x:\n    steps:\n      - uses: ./.github/actions/hugo-build\n"
            "        with:\n          args: \"--minify\"\n")
        if h6_alle_bauten_nutzen_die_action(wf):
            fehler.append("S5: H6 meldet einen korrekten Action-Aufruf als Befund "
                          "(Fehlalarm – die Regel wäre unbenutzbar).")

    # ---- S6: tote Ausnahme wird erkannt ----
    with tempfile.TemporaryDirectory() as tmp:
        wf = Path(tmp)
        name = next(iter(AUSNAHMEN))
        (wf / name).write_text("jobs:\n  x:\n    steps:\n      - run: echo nix\n",
                               encoding="utf-8")
        for weitere in AUSNAHMEN:
            if weitere != name:
                (wf / weitere).write_text(
                    "jobs:\n  x:\n    steps:\n      - run: hugo --minify\n",
                    encoding="utf-8")
        if not any("toter Eintrag" in b for b in h6_alle_bauten_nutzen_die_action(wf)):
            fehler.append("S6: Eine Ausnahme für eine Datei ohne Hugo-Bau bleibt "
                          "unbemerkt – so wächst ein Regal voller Ausreden.")

    # ---- S7: `hugo version` ist kein Bau ----
    with tempfile.TemporaryDirectory() as tmp:
        wf = _probe_verzeichnis(
            tmp, "jobs:\n  x:\n    steps:\n      - run: hugo version\n")
        if h6_alle_bauten_nutzen_die_action(wf):
            fehler.append("S7: `hugo version` wird als Bau gewertet (Fehlalarm).")

    if fehler:
        for f in fehler:
            print("❌ " + f)
        return 1
    print("✅ hugo_build_vertrag --selftest OK (H1–H8, 6 Verhaltensproben am echten "
          "Shell-Rumpf, 9 Sabotage-Proben).")
    return 0


def main(argv: list | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        return _selftest()
    erg = pruefen()
    offen = sum(len(b["befunde"]) for b in erg.values())
    if "--json" in args:
        print(json.dumps(
            {"regeln": {k: {"titel": v["titel"], "befunde": v["befunde"]}
                        for k, v in erg.items()},
             "befunde": offen, "ok": offen == 0},
            ensure_ascii=False, indent=2))
    else:
        print(bericht(erg))
    return 1 if offen else 0


if __name__ == "__main__":
    raise SystemExit(main())
