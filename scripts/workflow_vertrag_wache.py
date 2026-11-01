#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  WORKFLOW-VERTRAG-WACHE – die Stelle, an der PyYAML blind ist
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (Vorgang WF-SPRACHE / 31.10.2026)
#
#  Die Sprach-Qualitäts-Pipeline (`.github/workflows/
#  sprach-qualitaet-pipeline.yml`) war monatelang tot – und niemand
#  konnte es sehen:
#
#      labels: ["qualitaet", "sprach-qualitaet", "automatisiert"]
#
#  `peter-evans/create-issue-from-file` erwartet `labels` als
#  KOMMA-GETRENNTE ZEICHENKETTE. GitHub prüft das schon beim
#  Einlesen der Workflow-Datei:
#
#      Invalid workflow file: …#L1
#      (Line: 205, Col: 19): A sequence was not expected
#
#  Folge: Der Workflow wird am Tag des Commits vollständig verworfen.
#  Jeder Push auf einen beliebigen Branch erzeugt einen Lauf mit
#  NULL Jobs, der in derselben Sekunde rot endet. Kein Check-Run am
#  Commit, keine Benachrichtigung, kein Hinweis im PR. Das Skript in
#  der Datei hat nie eine Zeile ausgeführt.
#
#  WARUM KEINE DER BESTEHENDEN WACHEN DAS GEFANGEN HAT
#  ---------------------------------------------------
#  Es gibt 62 Dateien im Repo, die `.github/workflows` erwähnen – und
#  alle prüfen Eigenschaften, die man in PyYAML sieht: Rechte,
#  Push-Weg, `${{ }}`-Injection, Aktions-Versionen, Cron-Zeiten.
#  Der Fehler liegt aber in einer Schicht, die PyYAML GAR NICHT
#  betrachtet:
#
#    · `yaml.safe_load` löst `on:` zu `True` auf (YAML-1.1-Wahrheit)
#      und liefert den `with:`-Block als normalen Dict – ob die
#      Action den Wert als Liste verträgt, weiß PyYAML nicht.
#    · `trigger_wache.py` liest bewusst nur den `on:`-Ausschnitt.
#    · `actions_version_guard.py` lässt SHA-Pins per Regel A3
#      ABSICHTLICH unangetastet – ein Pin, den es beim Anbieter nicht
#      (mehr) gibt, ist für diese Wache unsichtbar.
#
#  Genau diese beiden Lücken schließt diese Wache:
#
#    V1  AKTION-EXISTIERT: Jeder gepinnte 40-stellige `uses:`-SHA
#        muss im Anbieter-Repository auflösbar sein. Ein getippter
#        oder veralteter Pin heißt: der Lauf stirbt, sobald GitHub
#        ihn ziehen will. (`actions/upload-artifact@49538c08…` in
#        derselben Datei war genau so ein Fall.)
#    V2  EINGABEN-VERTRAG: Jedes `with:`-Feld einer fremden Action
#        muss in deren `action.yml` deklariert sein – und der
#        YAML-Typ muss zum deklarierten Typ passen (Liste vs.
#        Zeichenkette). Unbekannte Eingaben Warnung, Typbruch
#        Befund.
#    V3  TOP-LEVEL-SCHLÜSSEL: Nur was GitHub im Workflow kennt
#        (`name`, `on`, `jobs`, `env`, `permissions`, …). Ein
#        Tippfehler wie `job:` statt `jobs:` wird sonst still
#        ignoriert.
#    V4  SCHRITT-SCHLÜSSEL: Nur `name`, `uses`, `with`, `run`, `env`,
#        `if`, `id`, `shell`, `working-directory`, `continue-on-error`,
#        `timeout-minutes`, `uses` und `env` – ein `argument:` statt
#        `with:` ist sonst still.
#    V5  AUSDRUCK-SYNTAX: jedes `${{ … }}` schließt. Ein fehlendes
#        `}}` macht die Datei ungültig, PyYAML sieht nur Text.
#    V6  SCHRITT-PFLICHT: Ein Schritt ohne `run:` und ohne `uses:`
#        ist ein Befund (er tut nichts und meldet trotzdem Erfolg).
#
#  WICHTIG – WAS DIESE WACHE NICHT KANN
#  ------------------------------------
#  Sie ist ein OFFLINE-Vertreter für GitHubs Parser, keine Kopie
#  davon. Sie kennt die Eingabe-Verträge nur für Actions mit
#  gepinntem SHA (SHA → `action.yml` ist eindeutig; ein Tag kann
#  wandern) und nur, wenn das Anbieter-Repo erreichbar ist. Ohne Netz
#  prüft sie V3–V6 vollständig und V1/V2 nur gegen den lokalen
#  Vertragsspeicher (`--vertraege`, aus einem Online-Lauf erzeugt).
#  Was sie nicht ersetzt: einen echten Dispatch. Der einzige
#  vollständige Beweis bleibt ein Lauf mit Jobs.
#
#  Aufruf:
#    python3 scripts/workflow_vertrag_wache.py             # Bericht
#    python3 scripts/workflow_vertrag_wache.py --gate      # CI, Exit 1
#    python3 scripts/workflow_vertrag_wache.py --online    # V1/V2 mit Netz
#    python3 scripts/workflow_vertrag_wache.py --vertraege data/workflow_vertraege.json
#    python3 scripts/workflow_vertrag_wache.py --selftest  # Sabotage-Schutz
# ============================================================
from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = Path(".github") / "workflows"
VERTRAG_DATEI = Path("data") / "workflow_vertraege.json"

# ------------------------------------------------------------ Schemawissen
# Quelle: GitHub-Dokumentation „Workflow syntax for GitHub Actions“.
TOP_LEVEL = {
    "name", "on", "jobs", "env", "permissions", "concurrency", "defaults",
    "run-name",
}

JOB_SCHLUESSEL = {
    "name", "runs-on", "needs", "if", "uses", "with", "secrets", "strategy",
    "continue-on-error", "timeout-minutes", "env", "permissions",
    "environment", "concurrency", "outputs", "container", "services",
    "steps", "if",
}

SCHRITT_SCHLUESSEL = {
    "name", "uses", "with", "run", "env", "if", "id", "shell",
    "working-directory", "continue-on-error", "timeout-minutes",
}

TRIGGER = {
    "push", "pull_request", "pull_request_target", "schedule",
    "workflow_dispatch", "workflow_call", "workflow_run", "release",
    "issues", "issue_comment", "repository_dispatch", "merge_group",
    "create", "delete", "fork", "gollum", "label", "milestone", "page_build",
    "public", "pull_request_review", "pull_request_review_comment",
    "pull_request_review_thread", "registry_package", "status", "watch",
    "deployment", "deployment_status", "discussion",
    "discussion_comment", "check_run", "check_suite", "branch_protection_rule",
}

SHA_RE = re.compile(r"^[0-9a-f]{40}$")
# Merker im Vertragsspeicher: „dieser Pin existiert beim Anbieter nicht".
FEHLT = "__fehlt__"
USES_RE = re.compile(r"^(?P<action>[^@\s]+)@(?P<ref>[^\s]+)$")
AUSDRUCK_RE = re.compile(r"\$\{\{")


class Befund(NamedTuple):
    regel: str          # V1 … V6
    ort: str            # datei:zeile
    text: str           # was ist falsch

    def __str__(self) -> str:
        return f"  [{self.regel}] {self.ort}  {self.text}"


# ------------------------------------------------------------ YAML lesen
# PyYAML ist im Repo überall verfügbar (requirements-ci.txt, --require-hashes),
# aber die Wache darf nicht daran sterben, wenn sie in einem nackten
# Container läuft: V3–V6 sind dann nicht prüfbar und sagen das auch.
try:  # pragma: no cover
    import yaml

    class _Strikt(yaml.SafeLoader):
        """SafeLoader, der doppelte Schlüssel NICHT still überschreibt.

        PyYAML nimmt bei `a: 1\na: 2` wortlos den letzten Wert. GitHub
        nicht – dort ist die Datei ungültig. Zwei Zeilen Code, um die
        häufigste Copy-Paste-Verletzung sichtbar zu machen.
        """

    def _kein_doppelter_schluessel(loader, node, deep=False):
        gesehen = set()
        for schluessel_knoten, _ in node.value:
            try:
                schluessel = loader.construct_object(schluessel_knoten, deep=deep)
            except Exception:  # pragma: no cover – exotische Schlüssel
                continue
            if schluessel in gesehen:
                raise yaml.constructor.ConstructorError(
                    None, None,
                    f"doppelter Schlüssel: {schluessel!r}", schluessel_knoten.start_mark,
                )
            gesehen.add(schluessel)
        return yaml.SafeLoader.construct_mapping(loader, node, deep=deep)

    _Strikt.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _kein_doppelter_schluessel
    )
except ImportError:  # pragma: no cover
    yaml = None
    _Strikt = None


def dateien(root: Path) -> List[Path]:
    basis = root / WORKFLOW_DIR
    if not basis.is_dir():
        return []
    return sorted(list(basis.glob("*.yml")) + list(basis.glob("*.yaml")))


def _lade(text: str):
    """Gibt (daten, fehler). `on:` landet in PyYAML als `True`."""
    if _Strikt is None:
        return None, "PyYAML fehlt – Struktur nicht prüfbar"
    try:
        return yaml.load(text, Loader=_Strikt), None
    except Exception as exc:  # noqa: BLE001 – jede YAML-Panne ist ein Befund
        return None, f"YAML ungültig: {exc}"


def _on_schluessel(daten: dict):
    """`on:` ist nach PyYAML mal `True`, mal der String – beides zulassen."""
    if not isinstance(daten, dict):
        return None
    for k in (True, "on"):
        if k in daten:
            return daten[k]
    return None


def _zeile_von(text: str, muster: str) -> int:
    for no, zeile in enumerate(text.splitlines(), start=1):
        if muster in zeile:
            return no
    return 0


# ------------------------------------------------------------ V3–V6 (offline)

def pruefe_struktur(text: str, name: str) -> Tuple[List[Befund], Optional[dict]]:
    befunde: List[Befund] = []
    daten, fehler = _lade(text)
    if fehler:
        befunde.append(Befund("V0", name, fehler))
        return befunde, None
    if not isinstance(daten, dict):
        befunde.append(Befund("V3", name, "Workflow ist kein Mapping"))
        return befunde, None

    # V3 – Top-Level
    for schluessel in daten:
        if schluessel is True or schluessel == "on":
            continue
        if schluessel not in TOP_LEVEL:
            befunde.append(Befund(
                "V3", f"{name}:{_zeile_von(text, str(schluessel) + ':')}",
                f"unbekannter Workflow-Schlüssel »{schluessel}«"))

    # on: → nur bekannte Auslöser
    on = _on_schluessel(daten)
    if on is None:
        befunde.append(Befund(
            "V3", f"{name}:{_zeile_von(text, 'on:')}",
            "kein `on:` – der Workflow kann nie starten"))
    elif isinstance(on, dict):
        for ausloeser in on:
            if ausloeser not in TRIGGER:
                befunde.append(Befund(
                    "V3", f"{name}:{_zeile_von(text, str(ausloeser) + ':')}",
                    f"unbekannter Auslöser »{ausloeser}«"))
    elif not isinstance(on, (str, list)):
        befunde.append(Befund(
            "V3", f"{name}:{_zeile_von(text, 'on:')}",
            f"`on:` hat unbrauchbaren Typ {type(on).__name__}"))

    jobs = daten.get("jobs")
    if not isinstance(jobs, dict) or not jobs:
        befunde.append(Befund(
            "V3", f"{name}:{_zeile_von(text, 'jobs:')}", "keine `jobs:`"))
        return befunde, daten

    for job_name, job in jobs.items():
        if not isinstance(job, dict):
            befunde.append(Befund("V3", f"{name}", f"Job »{job_name}« ist kein Mapping"))
            continue
        for schluessel in job:
            if schluessel not in JOB_SCHLUESSEL:
                befunde.append(Befund(
                    "V4", name, f"Job »{job_name}«: unbekannter Schlüssel »{schluessel}«"))
        schritte = job.get("steps")
        if schritte is None:
            if "uses" not in job:  # Reusable-Workflow-Aufruf ist erlaubt
                befunde.append(Befund(
                    "V6", name, f"Job »{job_name}« hat keine `steps:`"))
            continue
        if not isinstance(schritte, list):
            befunde.append(Befund(
                "V6", name, f"Job »{job_name}«: `steps:` ist keine Liste"))
            continue
        for nr, schritt in enumerate(schritte, start=1):
            if not isinstance(schritt, dict):
                befunde.append(Befund(
                    "V6", name, f"Job »{job_name}« Schritt {nr} ist kein Mapping"))
                continue
            for schluessel in schritt:
                if schluessel not in SCHRITT_SCHLUESSEL:
                    befunde.append(Befund(
                        "V4", name,
                        f"Job »{job_name}« Schritt {nr}: unbekannter Schlüssel "
                        f"»{schluessel}«"))
            hat_run = "run" in schritt
            hat_uses = "uses" in schritt
            if not hat_run and not hat_uses:
                befunde.append(Befund(
                    "V6", name,
                    f"Job »{job_name}« Schritt {nr} (»{schritt.get('name', '?')}«) "
                    f"hat weder `run:` noch `uses:`"))
            if hat_run and hat_uses:
                befunde.append(Befund(
                    "V4", name,
                    f"Job »{job_name}« Schritt {nr}: `run:` und `uses:` zusammen"))

    # V5 – Ausdrucks-Klammern, BLOCKWEISE.
    #
    # `${{` und `}}` dürfen in YAML über mehrere Zeilen laufen –
    # `if: >-` mit einem dreizeiligen Ausdruck ist gültig und kommt im
    # Repo vor. Eine Zeilenprüfung meldet das fälschlich als Fehler,
    # also wird je YAML-Block (durch Leerzeile getrennt) gezählt.
    # Kommentarzeilen zählen nicht mit; ein `${{` IN einem Kommentar
    # ist Text.
    zeilen = text.splitlines()
    block_start = 1
    tiefe = 0
    block_hat_ausdruck = False
    for no, zeile in enumerate(zeilen, start=1):
        if not zeile.strip():
            if tiefe > 0:
                befunde.append(Befund(
                    "V5", f"{name}:{block_start}",
                    f"`${{{{` ohne schließendes `}}}}` (Block ab Zeile {block_start})"))
            block_start = no + 1
            tiefe = 0
            block_hat_ausdruck = False
            continue
        if zeile.lstrip().startswith("#"):
            continue
        auf = zeile.count("${{")
        zu = zeile.count("}}")
        if auf:
            block_hat_ausdruck = True
        tiefe += auf - zu
        if tiefe < 0:  # mehr `}}` als `${{` – ebenfalls kaputt
            befunde.append(Befund(
                "V5", f"{name}:{no}", "`}}` ohne zugehöriges `${{`"))
            tiefe = 0
    if tiefe > 0:
        befunde.append(Befund(
            "V5", f"{name}:{block_start}",
            f"`${{{{` ohne schließendes `}}}}` (Block ab Zeile {block_start})"))
    return befunde, daten


# ------------------------------------------------------------ V1/V2 (Verträge)

def _repo_von(action: str) -> str:
    """`owner/repo` einer Action – auch wenn die Action IM Repo liegt
    (`github/codeql-action/init` → `github/codeql-action`)."""
    teile = action.split("/")
    return "/".join(teile[:2]) if len(teile) >= 2 else action


def _aktion_und_ref(uses: str) -> Optional[Tuple[str, str]]:
    m = USES_RE.match(uses.strip())
    if not m:
        return None
    return m.group("action"), m.group("ref")


def vertrag_laden(root: Path, pfad: Optional[Path]) -> Dict[str, dict]:
    ziel = pfad if pfad else root / VERTRAG_DATEI
    if not ziel.is_file():
        return {}
    try:
        return json.loads(ziel.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def vertrag_holen(action: str, sha: str, timeout: float = 20.0) -> Tuple[Optional[dict], str]:
    """`action.yml` des gepinnten Commits über die GitHub-API.

    Rückgabe: (vertrag, status) mit status
      · "ok"    – Pin existiert, Vertrag gelesen
      · "fehlt" – Anbieter kennt den Commit nicht (404/422) → V1
      · "netz"  – nicht erreichbar / kein Zugang → NICHT als Fehler werten
                  (eine Wache, die ohne Netz rot wird, wird abgeschaltet)
    """
    import base64
    import os

    kopf = {"Accept": "application/vnd.github+json",
            "User-Agent": "workflow-vertrag-wache"}
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if token:
        kopf["Authorization"] = f"Bearer {token}"

    def _hole(url: str) -> Tuple[int, bytes]:
        anfrage = urllib.request.Request(url, headers=kopf)
        try:
            with urllib.request.urlopen(anfrage, timeout=timeout) as antwort:  # noqa: S310
                return antwort.status, antwort.read()
        except urllib.error.HTTPError as exc:
            return exc.code, b""
        except (urllib.error.URLError, TimeoutError, OSError):
            return 0, b""

    repo = _repo_von(action)
    # Bei `owner/repo/pfad` liegt die `action.yml` IM Unterordner
    # (`github/codeql-action/init` → `init/action.yml`). Am Repo-Kopf
    # liegt dann eine andere Datei – die zu lesen ergäbe lauter
    # Falschmeldungen über unbekannte Eingaben.
    unterpfad = "/".join(action.split("/")[2:]).strip("/")
    datei = f"{unterpfad}/action.yml" if unterpfad else "action.yml"
    status, roh = _hole(
        f"https://api.github.com/repos/{repo}/contents/{datei}?ref={sha}")
    if status in (404, 422):
        # Nicht unterscheidbar am Statuscode: fehlender Commit oder fehlende
        # Datei. Der Commit-Endpunkt trennt das eindeutig.
        cstatus, _ = _hole(f"https://api.github.com/repos/{repo}/commits/{sha}")
        if cstatus in (404, 422):
            return None, "fehlt"
        if cstatus != 200:
            return None, "netz"
        # Commit existiert, aber am Repo-Kopf liegt keine `action.yml`
        # (z. B. `github/codeql-action` – dort liegen `action.yml` in
        # `init/`, `analyze/`, `upload-sarif/`). Der Pin ist gesund; über
        # die Eingaben sagt das nichts. Also nicht prüfbar, nicht „fehlt".
        return None, "unbekannt"
    if status != 200:
        return None, "netz"

    try:
        antwort = json.loads(roh.decode("utf-8"))
        roh = base64.b64decode(antwort["content"]).decode("utf-8")
    except (KeyError, ValueError, UnicodeDecodeError):
        return None, "netz"
    if yaml is None:
        return None, "netz"
    try:
        daten = yaml.safe_load(roh) or {}
    except Exception:  # noqa: BLE001
        return None, "netz"
    eingaben = daten.get("inputs") or {}
    vertrag: Dict[str, str] = {}
    for name, beschreibung in eingaben.items():
        typ = "string"
        if isinstance(beschreibung, dict):
            typ = str(beschreibung.get("type") or "string")
        vertrag[str(name)] = typ
    return vertrag, "ok"


def _typ_vertraeglich(yaml_typ: str, deklariert: str) -> bool:
    """GitHub-Actions vergleichen: eine Liste ist NICHT `string`.

    `boolean`/`number`/`choice` nimmt GitHub als Zeichenkette an (die
    Action bekommt IMMER Text), deshalb sind sie hier unkritisch –
    genau wie `string`. Nur `list` != Liste ist der harte Bruch.
    """
    yaml_typ = yaml_typ.lower()
    if deklariert not in ("string", "boolean", "number", "choice"):
        return True
    if deklariert == "string":
        # String-Eingaben vertragen alles, was GitHub zu Text macht –
        # ABER eine YAML-Liste wird nicht zu Text, sondern zu einem
        # Array im Runner-Kontext → genau der Fehler aus dem Vorgang.
        return yaml_typ not in ("sequence", "mapping")
    return True


def pruefe_vertraege(root: Path, daten_je_datei: Iterable[Tuple[str, dict]],
                     vertraege: Dict[str, dict], online: bool,
                     timeout: float = 20.0) -> List[Befund]:
    befunde: List[Befund] = []
    for name, daten in daten_je_datei:
        jobs = (daten or {}).get("jobs") or {}
        if not isinstance(jobs, dict):
            continue
        for job_name, job in jobs.items():
            if not isinstance(job, dict):
                continue
            for nr, schritt in enumerate(job.get("steps") or [], start=1):
                if not isinstance(schritt, dict):
                    continue
                uses = schritt.get("uses")
                if not isinstance(uses, str):
                    continue
                paar = _aktion_und_ref(uses)
                if not paar:
                    continue
                action, ref = paar
                if action.startswith("./") or action.startswith("docker://"):
                    continue
                if not SHA_RE.match(ref):
                    # Ohne SHA ist der Vertrag nicht eindeutig (Tags wandern).
                    continue
                schluessel = f"{action}@{ref}"
                vertrag = vertraege.get(schluessel)
                if vertrag is None and online:
                    geholt, status = vertrag_holen(action, ref, timeout=timeout)
                    if geholt is not None:
                        vertrag = geholt
                        vertraege[schluessel] = geholt
                    elif status == "fehlt":
                        befunde.append(Befund(
                            "V1", name,
                            f"»{action}@{ref[:12]}«: diesen Commit kennt der Anbieter "
                            f"nicht – GitHub kann die Action nicht ziehen, der Lauf "
                            f"stirbt beim Start"))
                        # Merker statt zweitem Netzaufruf – und NICHT zu
                        # verwechseln mit „kein Vertrag bekannt" (None).
                        vertraege[schluessel] = {FEHLT: True}
                        continue
                    else:
                        continue  # nicht erreichbar – kein Fehler daraus machen
                if vertrag is None:
                    continue
                if vertrag.get(FEHLT):
                    befunde.append(Befund(
                        "V1", name,
                        f"»{action}@{ref[:12]}«: diesen Commit kennt der Anbieter "
                        f"nicht – GitHub kann die Action nicht ziehen, der Lauf "
                        f"stirbt beim Start"))
                    continue
                with_block = schritt.get("with")
                if not isinstance(with_block, dict):
                    continue
                for feld, wert in with_block.items():
                    if feld not in vertrag:
                        befunde.append(Befund(
                            "V2", name,
                            f"»{action}« kennt keine Eingabe »{feld}« "
                            f"(Schritt {nr} in »{job_name}«)"))
                        continue
                    typ = "sequence" if isinstance(wert, list) else (
                        "mapping" if isinstance(wert, dict) else "scalar")
                    if not _typ_vertraeglich(typ, vertrag[feld]):
                        befunde.append(Befund(
                            "V2", name,
                            f"»{feld}« ist bei »{action}.{ref[:7]}« "
                            f"{vertrag[feld]}, hier aber eine YAML-{typ} – "
                            f"GitHub verwirft die ganze Datei "
                            f"(»A sequence was not expected«)"))
    return befunde


# ------------------------------------------------------------ Gesamtlauf

def pruefen(root: Path = ROOT, *, online: bool = False,
            vertragsdatei: Optional[Path] = None,
            timeout: float = 20.0) -> Tuple[List[Befund], int, Dict[str, dict]]:
    befunde: List[Befund] = []
    geladen: List[Tuple[str, dict]] = []
    pfade = dateien(root)
    for pfad in pfade:
        rel = str(pfad.relative_to(root))
        text = pfad.read_text(encoding="utf-8")
        teil, daten = pruefe_struktur(text, rel)
        befunde.extend(teil)
        if daten is not None:
            geladen.append((rel, daten))
    vertraege = vertrag_laden(root, vertragsdatei)
    befunde.extend(pruefe_vertraege(root, geladen, vertraege, online, timeout=timeout))
    befunde.sort(key=lambda b: (b.ort, b.regel))
    return befunde, len(pfade), vertraege


def bericht(befunde: Sequence[Befund], geprueft: int, online: bool) -> str:
    zeilen = ["🛡️  WORKFLOW-VERTRAG-WACHE", ""]
    zeilen.append(f"Geprüft: {geprueft} Workflow-Datei(en), Regeln V1–V6 "
                  f"({'online, inkl. Anbieter-Auflösung' if online else 'offline'}).")
    zeilen.append("")
    if not befunde:
        zeilen.append("✅ Alle Workflows sind vertragsgemäß – kein stiller Totalausfall.")
        return "\n".join(zeilen)
    zeilen.append(f"❌ {len(befunde)} Befund(e):")
    zeilen.extend(str(b) for b in befunde)
    zeilen.append("")
    zeilen.append("Hintergrund: Ein einziger Typfehler macht die GANZE Datei ungültig; "
                  "GitHub startet dann einen Lauf mit 0 Jobs, ohne Check-Run am Commit.")
    return "\n".join(zeilen)


# ------------------------------------------------------------ Selbsttest

def _selftest_struktur(fehler: List[str]) -> None:
    """YAML-abhängige Proben: Grundfall, V3–V6, Doppelschlüssel.

    Braucht PyYAML. Ohne PyYAML werden diese Proben übersprungen – sie
    dürfen ein karges Umfeld nicht mit Exit 2 bestrafen.
    """
    gut = """
name: X
on: [push]
jobs:
  a:
    runs-on: ubuntu-24.04
    steps:
      - name: Melden
        uses: peter-evans/create-issue-from-file@433e51abf769039ee20ba1293a088ca19d573b7f
        with:
          title: "T"
          content-filepath: R.md
          labels: "qualitaet, sprach-qualitaet"
"""

    # Grundfall: ein gesunder Workflow wird nicht beanstandet.
    b, _ = pruefe_struktur(gut, "gut.yml")
    if b:
        fehler.append(f"gesunder Workflow beanstandet: {b}")

    # V3 – Top-Level-Tippfehler
    b, _ = pruefe_struktur(gut.replace("jobs:", "job:"), "V3.yml")
    if not any(x.regel == "V3" for x in b):
        fehler.append(f"V3 nicht erkannt: {b}")

    # V4 – unbekannter Schritt-Schlüssel
    b, _ = pruefe_struktur(gut.replace("        with:", "        argument:"), "V4.yml")
    if not any(x.regel == "V4" for x in b):
        fehler.append(f"V4 nicht erkannt: {b}")

    # V5 – `${{` ohne `}}` (für PyYAML bloß Text, für GitHub Syntaxfehler)
    b, _ = pruefe_struktur(gut.replace('title: "T"', 'title: "${{ github.job"'), "V5.yml")
    if not any(x.regel == "V5" for x in b):
        fehler.append(f"V5 nicht erkannt: {b}")

    # V5-Gegenprobe: mehrzeiliger Ausdruck ist GÜLTIG (kommt im Repo vor).
    mehrzeilig = """
name: X
on: [push]
jobs:
  a:
    if: >-
      ${{ github.event.workflow_run.conclusion == 'failure' ||
          github.event.workflow_run.conclusion == 'timed_out' }}
    runs-on: ubuntu-24.04
    steps:
      - run: echo hi
"""
    b, _ = pruefe_struktur(mehrzeilig, "mehrzeilig.yml")
    if any(x.regel == "V5" for x in b):
        fehler.append(f"mehrzeiliger Ausdruck fälschlich beanstandet: {b}")

    # V6 – Schritt ohne `run:` und ohne `uses:`
    ohne_arbeit = """
name: X
on: [push]
jobs:
  a:
    runs-on: ubuntu-24.04
    steps:
      - name: Tut nichts
        env:
          X: "1"
"""
    b, _ = pruefe_struktur(ohne_arbeit, "V6.yml")
    if not any(x.regel == "V6" for x in b):
        fehler.append(f"V6 nicht erkannt: {b}")

    # Doppelter Schlüssel muss auffallen (PyYAML allein schluckt ihn).
    doppelt = """
name: X
on: [push]
jobs:
  a:
    runs-on: ubuntu-24.04
    runs-on: ubuntu-22.04
    steps:
      - run: echo hi
"""
    b, _ = pruefe_struktur(doppelt, "doppelt.yml")
    if not any(x.regel == "V0" for x in b):
        fehler.append(f"doppelter Schlüssel nicht erkannt: {b}")


def _selftest_vertraege(fehler: List[str]) -> None:
    """Pin- und Eingabe-Vertrag (V1/V2) – reine Dict-Prüfung, braucht kein YAML."""
    action = "peter-evans/create-issue-from-file@433e51abf769039ee20ba1293a088ca19d573b7f"
    vertrag = {"labels": "string", "title": "string", "content-filepath": "string"}

    def daten_mit(with_block: dict) -> dict:
        return {"jobs": {"a": {"runs-on": "ubuntu-24.04", "steps": [
            {"name": "Melden", "uses": action, "with": with_block}]}}}

    # V2 – der teure Fall: `labels` als YAML-Liste statt Zeichenkette.
    treffer = pruefe_vertraege(
        ROOT, [("liste.yml", daten_mit(
            {"labels": ["qualitaet", "sprach-qualitaet"],
             "title": "T", "content-filepath": "R.md"}))],
        {action: vertrag}, online=False)
    if len(treffer) != 1 or treffer[0].regel != "V2":
        fehler.append(f"V2 (Liste) nicht erkannt: {treffer}")
    elif "A sequence was not expected" not in treffer[0].text:
        fehler.append(f"V2 nennt die Originalmeldung nicht: {treffer[0].text}")

    # Gegenprobe: dieselbe Eingabe als Zeichenkette ist erlaubt.
    satz = pruefe_vertraege(
        ROOT, [("satz.yml", daten_mit(
            {"labels": "qualitaet, sprach-qualitaet",
             "title": "T", "content-filepath": "R.md"}))],
        {action: vertrag}, online=False)
    if satz:
        fehler.append(f"Zeichenkette darf nicht beanstandet werden: {satz}")

    # V2 – unbekannte Eingabe
    fremd = pruefe_vertraege(
        ROOT, [("fremd.yml", daten_mit(
            {"titel": "T", "content-filepath": "R.md"}))],
        {action: vertrag}, online=False)
    if not any(x.regel == "V2" and "titel" in x.text for x in fremd):
        fehler.append(f"unbekannte Eingabe nicht erkannt: {fremd}")

    # V1 – gemerkter „diesen Pin gibt es nicht"-Eintrag. Der Schlüssel muss
    # GENAU dem `uses:` der Probe entsprechen (fehlte hier zuerst – die
    # Probe war falsch, nicht die Wache).
    treffer = pruefe_vertraege(
        ROOT, [("tot.yml", daten_mit({"title": "T"}))],
        {action: {FEHLT: True}}, online=False)
    if not any(x.regel == "V1" for x in treffer):
        fehler.append(f"V1 nicht erkannt: {treffer}")

    # Negativ: ein LEERER Vertragsspeicher ist „nicht geprüft", nicht „V1".
    ohne = pruefe_vertraege(ROOT, [("tot.yml", daten_mit({"title": "T"}))], {}, online=False)
    if any(x.regel == "V1" for x in ohne):
        fehler.append(f"V1 falsch-positiv ohne Vertrag: {ohne}")


def _selftest() -> int:
    """Eingefrorene echte Fälle. Abweichung = Exit 2, nichts wird geschrieben."""
    fehler: List[str] = []
    ohne_yaml = _Strikt is None

    if ohne_yaml:
        # Ohne YAML sind die Strukturproben nicht durchführbar. Sie werden
        # übersprungen (mit Ansage) – der Vertragsteil ist reine Dict-Prüfung
        # und läuft weiter. Ein Selbsttest, der ein karges Umfeld mit Exit 2
        # bestraft, wäre selbst eine Fehlerquelle: Genau so wurde das PR-Gate
        # am 31.10.2026 rot, ohne dass die Wache etwas falsch machte.
        print("ℹ️  PyYAML fehlt – die YAML-Strukturproben (V0, V3–V6) werden "
              "übersprungen; Pin- und Eingabe-Vertrag (V1/V2) laufen weiter.")
        print("   Im PR-Gate gehört dieser Schritt HINTER die Installation "
              "(requirements-ci.txt).")
        _selftest_vertraege(fehler)
        beschriftung = "V1/V2 (ohne YAML-Strukturproben)"
    else:
        _selftest_struktur(fehler)
        _selftest_vertraege(fehler)
        beschriftung = "V1–V6, Typvertrag, Doppelschlüssel, Negativ-Proben"

    if fehler:
        print("❌ Selbsttest fehlgeschlagen:")
        for f in fehler:
            print(f"   · {f}")
        return 2
    print(f"✅ Selbsttest bestanden ({beschriftung}).")
    return 0


# ------------------------------------------------------------ CLI

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(
        description="Workflow-Vertrag-Wache – prüft die Schicht, die PyYAML nicht sieht.")
    ap.add_argument("--gate", action="store_true", help="Exit 1 bei Befund (CI)")
    ap.add_argument("--online", action="store_true",
                    help="Anbieter-Verträge über raw.githubusercontent.com auflösen")
    ap.add_argument("--vertraege", default=None,
                    help=f"lokaler Vertragsspeicher (Standard: {VERTRAG_DATEI})")
    ap.add_argument("--schreibe-vertraege", action="store_true",
                    help="aufgelöste Verträge in den Vertragsspeicher schreiben")
    ap.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe")
    ap.add_argument("--selftest", action="store_true", help="Sabotage-Schutz")
    ap.add_argument("--root", default=str(ROOT))
    args = ap.parse_args(argv)

    if args.selftest:
        return _selftest()

    root = Path(args.root).resolve()
    vertragsdatei = Path(args.vertraege) if args.vertraege else None
    befunde, geprueft, vertraege = pruefen(
        root, online=args.online, vertragsdatei=vertragsdatei)

    if args.schreibe_vertraege and args.online:
        ziel = vertragsdatei or (root / VERTRAG_DATEI)
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(json.dumps(vertraege, ensure_ascii=False,
                                   indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print(f"📝 Vertragsspeicher geschrieben: {ziel} ({len(vertraege)} Actions)")

    if args.json:
        print(json.dumps({
            "geprueft": geprueft,
            "online": args.online,
            "befunde": [b._asdict() for b in befunde],
            "regeln": sorted({b.regel for b in befunde}),
        }, ensure_ascii=False, indent=2))
    else:
        print(bericht(befunde, geprueft, args.online))

    if befunde and args.gate:
        print("::error::Workflow-Vertragsverletzung – Details oben (Regeln V1–V6).")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
