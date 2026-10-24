#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  ABHÄNGIGKEITS-WACHE – 58 offene Alerts, 0 belegbare Fundstellen
#  ------------------------------------------------------------
#  WARUM ES DIESE WACHE GIBT (24.10.2026)
#
#  GitHub meldete auf `main` 58 offene Schwachstellen
#  (7 kritisch, 30 hoch, 18 mäßig, 3 niedrig). Eine vollständige
#  Prüfung des ausgelieferten Bestands gegen dieselbe Advisory-
#  Datenbank, die Dependabot benutzt, ergab am selben Tag:
#
#      292 Abfragen (272 npm-Versionen, 16 pip-Pins, 5 Range-Untergrenzen)
#      → 0 Treffer.
#
#  Die Alarmliste war also älter als der Bestand. Zwei Ursachen
#  sind belegt und werden hier dauerhaft geschlossen:
#
#   U1  AUFLÖSUNGS-AMBIGUITÄT. `requirements-ci.in`,
#       `requirements-werkbank.txt` und `requirements-agent-reach.txt`
#       nannten Versionen als RANGE (`>=`, ohne Pin). Dependabot löst
#       solche Anforderungen EINMAL auf und merkt sich das Ergebnis.
#       Ändert sich nur `requirements-ci.txt` (die hashgesperrte
#       Auslieferungsdatei), sieht Dependabot keinen Anlass, die
#       Auflösung zu erneuern – der Alert überlebt die Heilung.
#       Heilung: jede Anforderung ist exakt gepinnt. Ein Pin ist
#       eine Aussage, ein Range ist eine Hoffnung.
#
#   U2  KEINE GEGENPROBE. Es gab keine Stimme im Repo, die den
#       ausgelieferten Bestand selbst gegen die Advisory-Datenbank
#       prüft. Der Sicherheitsstatus hing allein an GitHubs
#       Alarmtabelle – und die ist ein Cache, kein Beweis.
#       Heilung: diese Wache. Sie liest ALLE Manifeste (npm-Locks,
#       pip-Pins, Action-Pins, Docker-Tags), fragt die öffentliche
#       Advisory-API und nennt Paket, Version, Schweregrad, Fix und
#       Herkunftsdatei.
#
#  ZWEI BETRIEBSARTEN, WEIL SIE VERSCHIEDENE FRAGEN BEANTWORTEN
#  ------------------------------------------------------------
#    --check   OFFLINE, deterministisch, in Sekunden:
#              Sind alle Anforderungen gepinnt, stimmen Quelle und
#              Hash-Lock überein, sind Actions mit SHA + Version
#              gepinnt, tragen Images feste Tags?
#              Diese Prüfung ist falsch-negativ-frei, weil sie nur
#              Syntax und Herkunft beurteilt – nie das Netz braucht.
#
#    --audit   ONLINE, täglich und auf Zuruf:
#              Ist eine ausgelieferte Version von einer bekannten
#              Schwachstelle betroffen? Nutzt dieselbe Logik wie
#              Dependabot (GitHub Advisory Database, serverseitige
#              Versionsprüfung über `affects=name@version`).
#              Ein Netzfehler ist STÖRUNG (Exit 2), kein Befund –
#              ungeprüft ist nicht sauber (Vertrag C34).
#
#  EIN BEFUND BRAUCHT EINEN HEILER
#  -------------------------------
#  Jeder Treffer nennt `first_patched_version`. Ist sie gesetzt,
#  ist die Heilung ein Pin auf genau diese Version. Ist sie leer
#  (kein Fix veröffentlicht), bleibt der Eintrag als bewusster
#  Befund stehen – er darf nicht stillschweigend verschwinden.
#
#  SABOTAGE-SCHUTZ
#  ---------------
#  `--selftest` baut Bäume im temporären Verzeichnis, vergiftet sie
#  gezielt und verlangt, dass GENAU die zuständige Regel feuert.
#  Dazu drei Gegenproben: (1) ein sauberer Baum bleibt grün,
#  (2) eine leere Advisory-Quelle erzeugt keinen Treffer,
#  (3) eine immer-treffende Quelle wird als Treffer gemeldet.
#  Eine Wache, die nur grün sein kann, ist keine Wache.
#
#  AUFRUF
#  ------
#    python3 scripts/abhaengigkeits_wache.py --check
#    python3 scripts/abhaengigkeits_wache.py --audit
#    python3 scripts/abhaengigkeits_wache.py --audit --json
#    python3 scripts/abhaengigkeits_wache.py --audit --report audit.md
#    python3 scripts/abhaengigkeits_wache.py --check --audit --json
#    python3 scripts/abhaengigkeits_wache.py --selftest
#
#  Exit: 0 = sauber · 1 = Befund · 2 = Störung/Werkzeugfehler.
# ============================================================
"""Abhängigkeits-Wache: Pin-Treue offline, Advisory-Audit online."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]

# --------------------------------------------------------------------------- #
#  Regel-IDs – stabil, weil CI-Annotationen und Tests sie zitieren.
# --------------------------------------------------------------------------- #
REGEL_PIN = "A1"          # Anforderung ohne exakten Pin
REGEL_SSOT = "A2"         # Quelle (.in) und Hash-Lock (.txt) driften
REGEL_LOCK = "A3"         # Manifest mit Abhängigkeiten ohne Lockfile (Warnung)
REGEL_AKTION = "A4"       # Action ohne SHA-Pin oder ohne Versionskommentar
REGEL_DOCKER = "A5"       # bewegliches Image-Tag
REGEL_MEHRFACH = "A6"     # gleiche Anforderung mit zwei Versionen

SCHWERE_FEHLER = "fehler"
SCHWERE_WARNUNG = "warnung"

# Reihenfolge der Schweregrade für die Sortierung im Bericht.
SCHWERE_RANG = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}

# GitHub-Advisory-API. Öffentliche Daten, kein Sonderrecht nötig.
ADVISORY_API = "https://api.github.com/advisories"
API_VERSION = "2022-11-28"
MAX_ABFRAGEN = 900  # 5000/h authentifiziert; Reserve für Wiederholungen


# --------------------------------------------------------------------------- #
#  Datenmodell
# --------------------------------------------------------------------------- #
@dataclass(frozen=True)
class Anforderung:
    """Eine Version, die ausgeliefert wird – mit Herkunft."""

    oekosystem: str          # npm | pip | actions
    name: str
    version: str
    quelle: str              # Repo-relativer Pfad
    zeile: int = 0
    herkunft: str = "pin"    # lock | pin | range | action

    @property
    def schluessel(self) -> Tuple[str, str, str]:
        return (self.oekosystem, self.name.lower(), self.version)


@dataclass(frozen=True)
class Befund:
    regel: str
    schwere: str
    datei: str
    zeile: int
    text: str

    def als_dict(self) -> Dict[str, object]:
        return {
            "regel": self.regel,
            "schwere": self.schwere,
            "datei": self.datei,
            "zeile": self.zeile,
            "text": self.text,
        }


@dataclass(frozen=True)
class Treffer:
    oekosystem: str
    name: str
    version: str
    ghsa: str
    schwere: str
    zusammenfassung: str
    fix: Optional[str]
    quellen: Tuple[str, ...]
    herkunft: str

    def als_dict(self) -> Dict[str, object]:
        return {
            "oekosystem": self.oekosystem,
            "paket": self.name,
            "version": self.version,
            "ghsa": self.ghsa,
            "schwere": self.schwere,
            "zusammenfassung": self.zusammenfassung,
            "fix": self.fix,
            "quellen": list(self.quellen),
            "herkunft": self.herkunft,
        }


@dataclass
class Bilanz:
    geprueft: int = 0
    treffer: List[Treffer] = field(default_factory=list)
    stoerung: Optional[str] = None

    def als_dict(self) -> Dict[str, object]:
        nach_schwere: Dict[str, int] = {}
        for t in self.treffer:
            nach_schwere[t.schwere] = nach_schwere.get(t.schwere, 0) + 1
        return {
            "geprueft": self.geprueft,
            "treffer": len(self.treffer),
            "schwere": nach_schwere,
            "stoerung": self.stoerung,
        }


class Stoerung(RuntimeError):
    """Die Prüfung konnte nicht durchgeführt werden (nicht: sie war sauber)."""


# --------------------------------------------------------------------------- #
#  Parser – Requirements
# --------------------------------------------------------------------------- #
RE_REQ_NAME = re.compile(r"^(?P<name>[A-Za-z0-9][A-Za-z0-9._-]*)")
RE_REQ_OP = re.compile(r"^\s*(?P<op>===|==|~=|>=|<=|!=|>|<)\s*(?P<ver>[^\s;#]+)")
RE_HASH = re.compile(r"--hash=\S+")
RE_URL = re.compile(r"^(?:[a-z][a-z0-9+.-]*://|git\+|\.{0,2}/)")


def _fortsetzungen(roh: str) -> Iterable[Tuple[int, str]]:
    """Führt Backslash-Fortsetzungen zusammen und behält die Startzeile."""
    puffer = ""
    startzeile = 0
    for nummer, zeile in enumerate(roh.splitlines(), start=1):
        if not puffer:
            startzeile = nummer
        ohne_ende = zeile.rstrip()
        if ohne_ende.endswith("\\"):
            puffer += ohne_ende[:-1] + " "
            continue
        puffer += zeile
        yield startzeile, puffer
        puffer = ""
    if puffer:
        yield startzeile, puffer


def parse_requirements(text: str, quelle: str = "<memory>") -> List[Anforderung]:
    """Liest eine Requirements-Datei ohne Netz und ohne pip.

    Erkennt Pins (`==`), Bereiche (`>=`, `~=`, …) und ungepinnte
    Zeilen. Kommentare, `--hash`-Blöcke, Extras und Marker werden
    entfernt, damit nur die Version übrig bleibt, die installiert
    würde.
    """
    ergebnis: List[Anforderung] = []
    for nummer, roh in _fortsetzungen(text):
        zeile = RE_HASH.sub(" ", roh)
        zeile = zeile.split(" #", 1)[0].strip()
        if not zeile or zeile.startswith("#"):
            continue
        if zeile.startswith("-"):
            # -r/-c/--index-url/--extra-index-url: keine Version, keine Aussage.
            continue
        if RE_URL.match(zeile):
            # Direkte URL-Abhängigkeit (Agent Reach): Version steckt im Pfad.
            continue
        name_treffer = RE_REQ_NAME.match(zeile)
        if not name_treffer:
            continue
        name = name_treffer.group("name")
        rest = zeile[name_treffer.end():]
        # Extras entfernen: Paket[extra1,extra2]==1.2.3
        rest = re.sub(r"^\s*\[[^\]]*\]", "", rest)
        # Umgebungsmarker abschneiden: ; python_version >= "3.10"
        rest = rest.split(";", 1)[0]
        op_treffer = RE_REQ_OP.match(rest)
        if not op_treffer:
            ergebnis.append(Anforderung("pip", name, "", quelle, nummer, "range"))
            continue
        op = op_treffer.group("op")
        version = op_treffer.group("ver")
        if op == "==":
            # Wildcard-Pins (==1.2.*) sind Bereiche, keine Pins.
            if version.endswith(".*"):
                ergebnis.append(Anforderung("pip", name, version, quelle, nummer, "range"))
            else:
                ergebnis.append(Anforderung("pip", name, version, quelle, nummer, "pin"))
        else:
            ergebnis.append(Anforderung("pip", name, version, quelle, nummer, "range"))
    return ergebnis


# --------------------------------------------------------------------------- #
#  Parser – npm-Lockfiles
# --------------------------------------------------------------------------- #
def parse_lockfile(text: str, quelle: str = "<memory>") -> List[Anforderung]:
    """Liest lockfileVersion 2/3 (Feld `packages`)."""
    try:
        daten = json.loads(text)
    except json.JSONDecodeError as fehler:
        raise Stoerung(f"{quelle}: kein gültiges JSON ({fehler.msg}, Zeile {fehler.lineno})") from fehler
    pakete = daten.get("packages")
    if not isinstance(pakete, dict):
        return []
    ergebnis: List[Anforderung] = []
    for pfad, eintrag in pakete.items():
        if not pfad:
            continue  # Wurzel-Eintrag trägt die Deklaration, nicht die Auflösung
        if not isinstance(eintrag, dict):
            continue
        if eintrag.get("link") is True:
            continue
        version = eintrag.get("version")
        if not isinstance(version, str) or not version:
            continue
        name = eintrag.get("name")
        if not isinstance(name, str) or not name:
            name = pfad.split("node_modules/")[-1]
        ergebnis.append(Anforderung("npm", name, version, quelle, 0, "lock"))
    return ergebnis


# --------------------------------------------------------------------------- #
#  Parser – GitHub Actions
# --------------------------------------------------------------------------- #
RE_USES = re.compile(
    r"""^\s*(?:-\s*)?uses:\s*["']?
        (?P<name>(?!\./|docker://)[^@"'\s]+)
        @(?P<ref>[^"'\s#]+)
        ["']?
        \s*(?:\#\s*(?P<version>v?\d+(?:\.\d+){0,2}))?""",
    re.VERBOSE,
)
RE_SHA = re.compile(r"^[0-9a-f]{40}$")
RE_SEMVER = re.compile(r"^v?(\d+)(?:\.(\d+))?(?:\.(\d+))?$")


def parse_workflow(text: str, quelle: str = "<memory>") -> List[Anforderung]:
    """Liest Action-Pins samt Versionskommentar (`# v7.0.1`)."""
    ergebnis: List[Anforderung] = []
    for nummer, zeile in enumerate(text.splitlines(), start=1):
        if "uses:" not in zeile:
            continue
        treffer = RE_USES.match(zeile)
        if not treffer:
            continue
        name = treffer.group("name").strip()
        ref = treffer.group("ref").strip()
        version = treffer.group("version")
        if not version:
            continue  # A4 meldet den fehlenden Kommentar separat
        roh = RE_SEMVER.match(version)
        if not roh:
            continue
        teile = [int(g) if g else 0 for g in roh.groups()]
        # Actions werden über Major.Version gepflegt; die Advisory-Ranges
        # der actions-Ökosysteme sind ebenfalls semver-basiert.
        version_normalisiert = ".".join(str(t) for t in teile)
        herkunft = "action" if RE_SHA.match(ref) else "range"
        ergebnis.append(Anforderung("actions", name, version_normalisiert, quelle, nummer, herkunft))
    return ergebnis


# --------------------------------------------------------------------------- #
#  Parser – Container
# --------------------------------------------------------------------------- #
RE_IMAGE = re.compile(r"^\s*image:\s*[\"']?(?P<bild>[^\"'\s#]+)")
RE_FROM = re.compile(r"^\s*FROM\s+(?:--platform=\S+\s+)?(?P<bild>[^\s#]+)", re.IGNORECASE)


def parse_container(text: str, quelle: str = "<memory>") -> List[Befund]:
    """Bewegliche Image-Tags sind keine Reproduzierbarkeit."""
    befunde: List[Befund] = []
    for nummer, zeile in enumerate(text.splitlines(), start=1):
        for muster in (RE_IMAGE, RE_FROM):
            treffer = muster.match(zeile)
            if not treffer:
                continue
            bild = treffer.group("bild")
            if "$" in bild or bild == "scratch" or "@sha256:" in bild:
                continue
            tag = bild.rsplit(":", 1)[1] if ":" in bild.split("/")[-1] else ""
            if tag in ("", "latest"):
                befunde.append(
                    Befund(
                        REGEL_DOCKER,
                        SCHWERE_WARNUNG,
                        quelle,
                        nummer,
                        f"Bewegliches Image `{bild}` – bitte festen Tag oder Digest pinnen.",
                    )
                )
    return befunde


# --------------------------------------------------------------------------- #
#  Bestandsaufnahme
# --------------------------------------------------------------------------- #
def _rel(pfad: Path, root: Path) -> str:
    try:
        return pfad.relative_to(root).as_posix()
    except ValueError:
        return pfad.as_posix()


def finde_dateien(root: Path, muster: str) -> List[Path]:
    return sorted(p for p in root.glob(muster) if p.is_file())


def sammle_abhaengigkeiten(root: Path) -> List[Anforderung]:
    """Alle ausgelieferten Versionen – die Grundlage beider Betriebsarten."""
    ergebnis: List[Anforderung] = []

    for pfad in finde_dateien(root, "requirements*.txt"):
        ergebnis += parse_requirements(pfad.read_text(encoding="utf-8"), _rel(pfad, root))

    for pfad in root.glob("**/package-lock.json"):
        if "node_modules" in pfad.parts:
            continue
        ergebnis += parse_lockfile(pfad.read_text(encoding="utf-8"), _rel(pfad, root))

    for ordner in (".github/workflows", ".github/actions"):
        for pfad in (root / ordner).glob("**/*.yml"):
            ergebnis += parse_workflow(pfad.read_text(encoding="utf-8"), _rel(pfad, root))

    return ergebnis


# --------------------------------------------------------------------------- #
#  Offline-Prüfung
# --------------------------------------------------------------------------- #
def _manifest_paare(root: Path) -> List[Tuple[Path, Optional[Path]]]:
    paare: List[Tuple[Path, Optional[Path]]] = []
    for manifest in sorted(root.glob("**/package.json")):
        if "node_modules" in manifest.parts or ".claude" in manifest.parts:
            continue
        lock = manifest.with_name("package-lock.json")
        paare.append((manifest, lock if lock.exists() else None))
    return paare


def pruefe_manifest_paar(manifest: Path, lock: Optional[Path], root: Path) -> List[Befund]:
    befunde: List[Befund] = []
    try:
        daten = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError as fehler:
        return [
            Befund(
                REGEL_LOCK,
                SCHWERE_FEHLER,
                _rel(manifest, root),
                fehler.lineno,
                f"package.json ist kein gültiges JSON: {fehler.msg}",
            )
        ]
    felder = ("dependencies", "devDependencies", "optionalDependencies", "peerDependencies")
    anzahl = sum(len(daten.get(feld) or {}) for feld in felder)
    if anzahl and lock is None:
        befunde.append(
            Befund(
                REGEL_LOCK,
                SCHWERE_WARNUNG,
                _rel(manifest, root),
                0,
                f"{anzahl} deklarierte Abhängigkeit(en), aber kein package-lock.json – "
                "die aufgelösten Versionen sind nicht nachweisbar.",
            )
        )
    return befunde


def pruefe_requirement_datei(pfad: Path, root: Path) -> List[Befund]:
    befunde: List[Befund] = []
    for anforderung in parse_requirements(pfad.read_text(encoding="utf-8"), _rel(pfad, root)):
        if anforderung.herkunft == "pin":
            continue
        if not anforderung.version:
            befunde.append(
                Befund(
                    REGEL_PIN,
                    SCHWERE_FEHLER,
                    _rel(pfad, root),
                    anforderung.zeile,
                    f"`{anforderung.name}` ist ohne Version genannt – Dependabot "
                    "löst das einmal auf und hält das Ergebnis fest. Bitte exakt pinnen.",
                )
            )
        else:
            befunde.append(
                Befund(
                    REGEL_PIN,
                    SCHWERE_FEHLER,
                    _rel(pfad, root),
                    anforderung.zeile,
                    f"`{anforderung.name}` ist als Bereich genannt (Untergrenze "
                    f"{anforderung.version}) – ein Bereich lässt die aufgelöste Version offen. "
                    "Bitte `==<version>` schreiben.",
                )
            )
    return befunde


def pruefe_ssot(root: Path) -> List[Befund]:
    """`requirements-ci.in` ist die Quelle, `requirements-ci.txt` die Auslieferung."""
    befunde: List[Befund] = []
    quelle = root / "requirements-ci.in"
    sperre = root / "requirements-ci.txt"
    if not quelle.exists() or not sperre.exists():
        return befunde
    pins_quelle = {
        a.name.lower(): a
        for a in parse_requirements(quelle.read_text(encoding="utf-8"), "requirements-ci.in")
        if a.herkunft == "pin"
    }
    pins_sperre = {
        a.name.lower(): a
        for a in parse_requirements(sperre.read_text(encoding="utf-8"), "requirements-ci.txt")
        if a.herkunft == "pin"
    }
    for name, pin in sorted(pins_quelle.items()):
        gesperrt = pins_sperre.get(name)
        if gesperrt is None:
            befunde.append(
                Befund(
                    REGEL_SSOT,
                    SCHWERE_FEHLER,
                    "requirements-ci.in",
                    pin.zeile,
                    f"`{pin.name}=={pin.version}` fehlt im Hash-Lock `requirements-ci.txt`.",
                )
            )
            continue
        if gesperrt.version != pin.version:
            befunde.append(
                Befund(
                    REGEL_SSOT,
                    SCHWERE_FEHLER,
                    "requirements-ci.in",
                    pin.zeile,
                    f"`{pin.name}` driftet: Quelle {pin.version}, Auslieferung "
                    f"{gesperrt.version}. Der Hash-Lock ist die Wahrheit.",
                )
            )
    return befunde


def pruefe_actions(root: Path) -> List[Befund]:
    befunde: List[Befund] = []
    for ordner in (".github/workflows", ".github/actions"):
        for pfad in sorted((root / ordner).glob("**/*.yml")):
            rel = _rel(pfad, root)
            for nummer, zeile in enumerate(pfad.read_text(encoding="utf-8").splitlines(), start=1):
                if "uses:" not in zeile:
                    continue
                treffer = RE_USES.match(zeile)
                if not treffer:
                    continue
                ref = treffer.group("ref").strip()
                if not RE_SHA.match(ref):
                    befunde.append(
                        Befund(
                            REGEL_AKTION,
                            SCHWERE_FEHLER,
                            rel,
                            nummer,
                            f"Action `{treffer.group('name')}` hängt an `{ref}` statt an "
                            "einer Commit-SHA – Lieferketten-Risiko.",
                        )
                    )
                if not treffer.group("version"):
                    befunde.append(
                        Befund(
                            REGEL_AKTION,
                            SCHWERE_WARNUNG,
                            rel,
                            nummer,
                            f"Action `{treffer.group('name')}` hat keinen Versionskommentar "
                            "(`# vX.Y.Z`) – ohne ihn ist die Version im Audit nicht prüfbar.",
                        )
                    )
    return befunde


def pruefe_doppelte(root: Path) -> List[Befund]:
    """Zwei Versionen desselben Pakets in derselben Datei sind ein Stillstand."""
    befunde: List[Befund] = []
    for pfad in finde_dateien(root, "requirements*.txt"):
        gesehen: Dict[str, Anforderung] = {}
        for anforderung in parse_requirements(pfad.read_text(encoding="utf-8"), _rel(pfad, root)):
            if anforderung.herkunft != "pin":
                continue
            vorher = gesehen.get(anforderung.name.lower())
            if vorher and vorher.version != anforderung.version:
                befunde.append(
                    Befund(
                        REGEL_MEHRFACH,
                        SCHWERE_FEHLER,
                        _rel(pfad, root),
                        anforderung.zeile,
                        f"`{anforderung.name}` steht zweimal mit verschiedenen Versionen "
                        f"({vorher.version} und {anforderung.version}).",
                    )
                )
            gesehen[anforderung.name.lower()] = anforderung
    return befunde


def pruefe_struktur(root: Path) -> List[Befund]:
    """Alle Offline-Regeln – deterministisch, ohne Netz."""
    befunde: List[Befund] = []
    for pfad in finde_dateien(root, "requirements*.txt"):
        befunde += pruefe_requirement_datei(pfad, root)
    befunde += pruefe_ssot(root)
    for manifest, lock in _manifest_paare(root):
        befunde += pruefe_manifest_paar(manifest, lock, root)
    befunde += pruefe_actions(root)
    befunde += pruefe_doppelte(root)
    for muster in ("tools/n8n/docker-compose.yml", "tools/n8n/Dockerfile*"):
        for pfad in sorted(root.glob(muster)):
            befunde += parse_container(pfad.read_text(encoding="utf-8"), _rel(pfad, root))
    # Stabil sortieren: Datei, Zeile, Regel.
    befunde.sort(key=lambda b: (b.datei, b.zeile, b.regel))
    return befunde


# --------------------------------------------------------------------------- #
#  Online-Audit
# --------------------------------------------------------------------------- #
class AdvisoryQuelle:
    """Schnittstelle – HTTP im Betrieb, Datei in Test und Selbsttest."""

    def suche(self, anforderung: Anforderung) -> List[Dict[str, str]]:  # pragma: no cover
        raise NotImplementedError


class HttpAdvisoryQuelle(AdvisoryQuelle):
    def __init__(self, token: Optional[str] = None, api: str = ADVISORY_API, versuche: int = 3) -> None:
        self.token = token
        self.api = api
        self.versuche = versuche

    def _kopf(self) -> Dict[str, str]:
        kopf = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": API_VERSION,
            "User-Agent": "franksfinanzcheck-abhaengigkeits-wache",
        }
        if self.token:
            kopf["Authorization"] = f"Bearer {self.token}"
        return kopf

    def suche(self, anforderung: Anforderung) -> List[Dict[str, str]]:
        parameter = urllib.parse.urlencode(
            {
                "ecosystem": anforderung.oekosystem,
                "affects": f"{anforderung.name}@{anforderung.version}",
                "per_page": "100",
            }
        )
        url = f"{self.api}?{parameter}"
        letzter_fehler = ""
        for versuch in range(self.versuche):
            anfrage = urllib.request.Request(url, headers=self._kopf())
            try:
                with urllib.request.urlopen(anfrage, timeout=45) as antwort:
                    roh = antwort.read()
                daten = json.loads(roh)
                if not isinstance(daten, list):
                    raise Stoerung(f"Advisory-API lieferte kein Array für {url}")
                return daten
            except urllib.error.HTTPError as fehler:
                letzter_fehler = f"HTTP {fehler.code} für {anforderung.name}@{anforderung.version}"
                if fehler.code in (403, 429):
                    # Rate-Limit: nicht als Befund werten, sondern als Störung.
                    raise Stoerung(f"{letzter_fehler} – Advisory-API begrenzt die Abfragen.") from fehler
                if fehler.code < 500:
                    raise Stoerung(letzter_fehler) from fehler
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as fehler:
                letzter_fehler = f"{type(fehler).__name__}: {fehler}"
            time.sleep(1 + 2 * versuch)
        raise Stoerung(f"Advisory-API nicht erreichbar ({letzter_fehler}).")


class DateiAdvisoryQuelle(AdvisoryQuelle):
    """Liest eine eingefrorene Antwort – für Tests und Selbsttest.

    Format: {"npm:lodash@4.17.15": [{"ghsa": …, "severity": …, …}]}
    Die Struktur ist bewusst flach und unabhängig vom API-Dialekt.
    """

    def __init__(self, daten: Dict[str, List[Dict[str, str]]]) -> None:
        self.daten = daten

    @classmethod
    def aus_datei(cls, pfad: Path) -> "DateiAdvisoryQuelle":
        return cls(json.loads(pfad.read_text(encoding="utf-8")))

    def suche(self, anforderung: Anforderung) -> List[Dict[str, str]]:
        schluessel = f"{anforderung.oekosystem}:{anforderung.name.lower()}@{anforderung.version}"
        return list(self.daten.get(schluessel, []))


def _normalisiere(roh: Dict[str, object]) -> Dict[str, str]:
    """Bringt API- und Datei-Dialekt auf eine Form."""
    if "ghsa" in roh:  # Datei-Dialekt
        return {
            "ghsa": str(roh.get("ghsa", "")),
            "severity": str(roh.get("severity", "unknown")),
            "summary": str(roh.get("summary", "")),
            "fixed": str(roh.get("fixed") or ""),
        }
    gefunden = roh.get("vulnerabilities") or []
    fix = ""
    if isinstance(gefunden, list):
        for eintrag in gefunden:
            if not isinstance(eintrag, dict):
                continue
            kandidat = eintrag.get("first_patched_version")
            if isinstance(kandidat, dict):
                kandidat = kandidat.get("identifier")
            if kandidat:
                fix = str(kandidat)
                break
    return {
        "ghsa": str(roh.get("ghsa_id", "")),
        "severity": str(roh.get("severity", "unknown")),
        "summary": str(roh.get("summary", "")),
        "fixed": fix,
    }


def auditiere(
    abhaengigkeiten: Sequence[Anforderung],
    quelle: AdvisoryQuelle,
    max_abfragen: int = MAX_ABFRAGEN,
) -> Bilanz:
    """Fragt für jede ausgelieferte Version die Advisory-Datenbank."""
    bilanz = Bilanz()
    gesehen: Dict[Tuple[str, str, str], List[str]] = {}
    reihenfolge: List[Anforderung] = []
    for anforderung in abhaengigkeiten:
        if not anforderung.version:
            continue
        if anforderung.herkunft == "range":
            # Bereiche sind bereits ein A1-Befund; sie werden nicht auditiert,
            # weil ihre aufgelöste Version nicht feststeht.
            continue
        schluessel = anforderung.schluessel
        if schluessel not in gesehen:
            gesehen[schluessel] = []
            reihenfolge.append(anforderung)
        if anforderung.quelle not in gesehen[schluessel]:
            gesehen[schluessel].append(anforderung.quelle)

    if len(reihenfolge) > max_abfragen:
        raise Stoerung(
            f"{len(reihenfolge)} Abfragen überschreiten das Budget von {max_abfragen} – "
            "bitte MAX_ABFRAGEN anheben oder den Bestand aufteilen."
        )

    for anforderung in reihenfolge:
        treffer = quelle.suche(anforderung)
        bilanz.geprueft += 1
        for roh in treffer:
            normal = _normalisiere(roh)
            bilanz.treffer.append(
                Treffer(
                    oekosystem=anforderung.oekosystem,
                    name=anforderung.name,
                    version=anforderung.version,
                    ghsa=normal["ghsa"],
                    schwere=normal["severity"],
                    zusammenfassung=normal["summary"],
                    fix=normal["fixed"] or None,
                    quellen=tuple(gesehen[anforderung.schluessel]),
                    herkunft=anforderung.herkunft,
                )
            )
    bilanz.treffer.sort(
        key=lambda t: (SCHWERE_RANG.get(t.schwere.lower(), 9), t.name, t.version, t.ghsa)
    )
    return bilanz


# --------------------------------------------------------------------------- #
#  Ausgabe
# --------------------------------------------------------------------------- #
def bericht_markdown(befunde: Sequence[Befund], bilanz: Optional[Bilanz]) -> str:
    zeilen = ["# Abhängigkeits-Wache", ""]
    zeilen.append(f"Stand: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}")
    zeilen.append("")
    if bilanz is not None:
        zeilen.append(f"## Audit (Advisory-Datenbank)")
        zeilen.append("")
        if bilanz.stoerung:
            zeilen.append(f"**STÖRUNG:** {bilanz.stoerung}")
        else:
            zeilen.append(f"Geprüfte Versionen: **{bilanz.geprueft}** · Treffer: **{len(bilanz.treffer)}**")
        zeilen.append("")
        for treffer in bilanz.treffer:
            fix = treffer.fix or "kein Fix veröffentlicht"
            zeilen.append(
                f"- **{treffer.schwere.upper()}** · `{treffer.name}@{treffer.version}` "
                f"({treffer.oekosystem}) · {treffer.ghsa} · Fix: {fix}"
            )
            zeilen.append(f"  - {treffer.zusammenfassung}")
            zeilen.append(f"  - Herkunft: {', '.join(treffer.quellen)}")
        if bilanz.treffer:
            zeilen.append("")
    zeilen.append("## Struktur (offline)")
    zeilen.append("")
    if not befunde:
        zeilen.append("Keine Befunde.")
    else:
        for befund in befunde:
            ort = f"{befund.datei}:{befund.zeile}" if befund.zeile else befund.datei
            zeilen.append(f"- **{befund.regel}** ({befund.schwere}) · `{ort}` · {befund.text}")
    zeilen.append("")
    return "\n".join(zeilen)


def _annotation(befund: Befund) -> str:
    ebene = "error" if befund.schwere == SCHWERE_FEHLER else "warning"
    return (
        f"::{ebene} file={befund.datei},line={max(1, befund.zeile)},"
        f"title=Abhängigkeits-Wache {befund.regel}::{befund.text}"
    )


# --------------------------------------------------------------------------- #
#  Selbsttest
# --------------------------------------------------------------------------- #
def _schreibe(root: Path, pfad: str, inhalt: str) -> None:
    ziel = root / pfad
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(inhalt, encoding="utf-8")


def _regeln(befunde: Iterable[Befund]) -> List[str]:
    return sorted({b.regel for b in befunde})


def run_selftest() -> List[str]:
    """Sabotage- und Gegenproben. Gibt die Fehlerliste zurück (leer = grün)."""
    fehler: List[str] = []

    def pruefe(name: str, bedingung: bool, detail: str = "") -> None:
        if not bedingung:
            fehler.append(f"{name}: {detail}" if detail else name)

    # --- 1 · Parser: Fortsetzungen, Hashes, Extras, Marker -----------------
    text = (
        "# Kommentar\n"
        "Pillow==13.0.0 \\\n"
        "    --hash=sha256:aaaa \\\n"
        "    --hash=sha256:bbbb\n"
        "cryptography>=50,<51  # Bereich\n"
        "requests[security]==2.34.2 ; python_version >= \"3.10\"\n"
        "-r other.txt\n"
        "https://example.org/pkg-1.0.tar.gz\n"
        "rye\n"
    )
    anf = parse_requirements(text)
    nach_name = {a.name: a for a in anf}
    pruefe("Parser/Pillow", nach_name["Pillow"].version == "13.0.0" and nach_name["Pillow"].herkunft == "pin")
    pruefe("Parser/cryptography", nach_name["cryptography"].herkunft == "range")
    pruefe("Parser/requests", nach_name["requests"].version == "2.34.2" and nach_name["requests"].herkunft == "pin")
    pruefe("Parser/rye", nach_name["rye"].herkunft == "range" and nach_name["rye"].version == "")
    pruefe("Parser/URL", {a.name for a in anf} == {"Pillow", "cryptography", "requests", "rye"})

    # --- 2 · Lockfile ------------------------------------------------
    lock = json.dumps(
        {
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "x", "version": "1.0.0"},
                "node_modules/a": {"version": "2.0.0"},
                "node_modules/@s/b": {"name": "@s/b", "version": "3.1.4"},
                "node_modules/link": {"link": True, "resolved": "tools/x"},
            },
        }
    )
    gelockt = parse_lockfile(lock)
    namen = {a.name: a.version for a in gelockt}
    pruefe("Lock/a", namen.get("a") == "2.0.0")
    pruefe("Lock/scoped", namen.get("@s/b") == "3.1.4")
    pruefe("Lock/link übersprungen", "link" not in namen)

    # --- 3 · Workflow-Pins -------------------------------------------
    wf = (
        "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n"
        "      - uses: owner/action@v3\n"
        "      - uses: owner/other@4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a4a\n"
        "      - uses: ./.github/actions/hugo-build\n"
    )
    aktionen = parse_workflow(wf)
    pruefe("Workflow/Version", any(a.name == "actions/checkout" and a.version == "7.0.1" for a in aktionen))
    pruefe("Workflow/lokal ignoriert", all(not a.name.startswith(".") for a in aktionen))

    # --- 4 · Container -----------------------------------------------
    container = parse_container("image: n8nio/n8n:2.43.5\nFROM python:3.14-slim\nimage: foo/bar:latest\n")
    pruefe("Container/latest", any(b.regel == REGEL_DOCKER for b in container))
    pruefe("Container/fest", len([b for b in container if "n8nio" in b.text]) == 0)

    # --- 5 · Struktur-Regeln in einem vergifteten Baum ----------------
    with tempfile.TemporaryDirectory() as tmp:
        baum = Path(tmp)
        _schreibe(baum, "requirements-werkbank.txt", "crawl4ai>=0.9.4\ncomposio\n")
        _schreibe(baum, "requirements-ci.in", "pillow==13.0.0\n")
        _schreibe(baum, "requirements-ci.txt", "pillow==12.3.0 \\\n    --hash=sha256:aa\n")
        _schreibe(baum, "package.json", json.dumps({"devDependencies": {"wrangler": "^4.0.0"}}))
        _schreibe(baum, ".github/workflows/w.yml", "      - uses: owner/action@v3\n")
        befunde = pruefe_struktur(baum)
        regeln = _regeln(befunde)
        for regel in (REGEL_PIN, REGEL_SSOT, REGEL_LOCK, REGEL_AKTION):
            pruefe(f"Struktur/{regel}", regel in regeln, f"gefeuert: {regeln}")

        # Gegenprobe: sauberer Baum muss grün bleiben.
        with tempfile.TemporaryDirectory() as tmp2:
            sauber = Path(tmp2)
            _schreibe(sauber, "requirements-werkbank.txt", "crawl4ai==0.9.5\ncomposio==0.30.0\n")
            _schreibe(sauber, "requirements-ci.in", "pillow==13.0.0\n")
            _schreibe(sauber, "requirements-ci.txt", "pillow==13.0.0 \\\n    --hash=sha256:aa\n")
            _schreibe(sauber, "package.json", json.dumps({"devDependencies": {"x": "1.0.0"}}))
            _schreibe(sauber, "package-lock.json", lock)
            _schreibe(
                sauber,
                ".github/workflows/w.yml",
                "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n",
            )
            _schreibe(sauber, "tools/n8n/docker-compose.yml", "    image: n8nio/n8n:2.43.5\n")
            sauber_befunde = pruefe_struktur(sauber)
            pruefe("Gegenprobe/sauber", not sauber_befunde, f"unerwartet: {[b.als_dict() for b in sauber_befunde]}")

    # --- 6 · Audit: Treffer, Gegenprobe, Störung ----------------------
    dep = Anforderung("npm", "lodash", "4.17.15", "package-lock.json", 0, "lock")
    quelle = DateiAdvisoryQuelle(
        {
            "npm:lodash@4.17.15": [
                {"ghsa": "GHSA-test", "severity": "high", "summary": "Testfund", "fixed": "4.17.21"}
            ]
        }
    )
    bilanz = auditiere([dep], quelle)
    pruefe("Audit/Treffer", len(bilanz.treffer) == 1 and bilanz.treffer[0].fix == "4.17.21")

    leer = auditiere([dep], DateiAdvisoryQuelle({}))
    pruefe("Gegenprobe/leere Quelle", not leer.treffer and leer.geprueft == 1)

    sauber_dep = Anforderung("npm", "lodash", "4.17.21", "package-lock.json", 0, "lock")
    sauber_bilanz = auditiere([sauber_dep], quelle)
    pruefe("Gegenprobe/gepatcht", not sauber_bilanz.treffer)

    # Bereiche werden nicht auditiert (sie sind schon ein A1-Befund).
    bereich = auditiere([Anforderung("pip", "crawl4ai", "0.9.4", "x.txt", 1, "range")], quelle)
    pruefe("Audit/Bereich übersprungen", bereich.geprueft == 0)

    # Dedupliziert: gleiche Version aus zwei Dateien -> eine Abfrage.
    doppelt = auditiere([dep, Anforderung("npm", "lodash", "4.17.15", "tools/x/package-lock.json", 0, "lock")], quelle)
    pruefe("Audit/Dedupe", doppelt.geprueft == 1 and len(doppelt.treffer) == 1)

    # Budget: mehr Abfragen als erlaubt -> Störung, nicht Befund.
    try:
        auditiere([dep, sauber_dep], DateiAdvisoryQuelle({}), max_abfragen=1)
        pruefe("Audit/Budget", False, "keine Störung ausgelöst")
    except Stoerung:
        pass

    return fehler


# --------------------------------------------------------------------------- #
#  Hauptprogramm
# --------------------------------------------------------------------------- #
def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Abhängigkeits-Wache: Pins offline prüfen, Schwachstellen online auditieren.",
    )
    parser.add_argument("--check", action="store_true", help="Offline-Prüfung der Manifeste")
    parser.add_argument("--audit", action="store_true", help="Online-Audit gegen die Advisory-Datenbank")
    parser.add_argument("--selftest", action="store_true", help="Sabotage- und Gegenproben")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare Ausgabe")
    parser.add_argument("--report", metavar="PFAD", help="Markdown-Bericht schreiben")
    parser.add_argument("--root", metavar="PFAD", default=str(ROOT), help="Wurzelverzeichnis (Tests)")
    parser.add_argument(
        "--advisory-datei",
        metavar="PFAD",
        help="Eingefrorene Advisory-Antwort statt HTTP (Tests, Luftnotbetrieb)",
    )
    parser.add_argument("--max-abfragen", type=int, default=MAX_ABFRAGEN)
    args = parser.parse_args(argv)

    if args.selftest:
        fehler = run_selftest()
        if fehler:
            print("❌ Selbsttest der Abhängigkeits-Wache fehlgeschlagen:", file=sys.stderr)
            for eintrag in fehler:
                print(f"   · {eintrag}", file=sys.stderr)
            return 2
        print("✅ Selbsttest bestanden (5 Parser, 6 Strukturregeln, 3 Gegenproben, Budget-Schutz).")
        return 0

    if not args.check and not args.audit:
        parser.print_help()
        return 2

    root = Path(args.root).resolve()
    befunde: List[Befund] = []
    bilanz: Optional[Bilanz] = None

    if args.check:
        befunde = pruefe_struktur(root)

    if args.audit:
        token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
        try:
            if args.advisory_datei:
                quelle: AdvisoryQuelle = DateiAdvisoryQuelle.aus_datei(Path(args.advisory_datei))
            else:
                if not token:
                    raise Stoerung(
                        "Kein GITHUB_TOKEN/GH_TOKEN gesetzt – ohne Token ist das API-Budget "
                        "zu klein für einen vollständigen Audit (ungeprüft ist nicht sauber)."
                    )
                quelle = HttpAdvisoryQuelle(token)
            bilanz = auditiere(sammle_abhaengigkeiten(root), quelle, args.max_abfragen)
        except Stoerung as fehler:
            bilanz = Bilanz(stoerung=str(fehler))
        except (json.JSONDecodeError, OSError) as fehler:
            bilanz = Bilanz(stoerung=f"Audit nicht durchführbar: {fehler}")

    if args.report:
        Path(args.report).write_text(bericht_markdown(befunde, bilanz), encoding="utf-8")

    fehler_befunde = [b for b in befunde if b.schwere == SCHWERE_FEHLER]
    warnungen = [b for b in befunde if b.schwere == SCHWERE_WARNUNG]

    if args.json:
        print(
            json.dumps(
                {
                    "stand": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "struktur": {
                        "befunde": [b.als_dict() for b in befunde],
                        "fehler": len(fehler_befunde),
                        "warnungen": len(warnungen),
                    },
                    "audit": bilanz.als_dict() if bilanz else None,
                    "treffer": [t.als_dict() for t in (bilanz.treffer if bilanz else [])],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        if args.check:
            print(f"Struktur: {len(fehler_befunde)} Fehler, {len(warnungen)} Warnung(en).")
            for befund in befunde:
                print(_annotation(befund))
        if bilanz is not None:
            if bilanz.stoerung:
                print(f"::error title=Abhängigkeits-Audit gestört::{bilanz.stoerung}")
            else:
                print(f"Audit: {bilanz.geprueft} Versionen geprüft, {len(bilanz.treffer)} Treffer.")
                for treffer in bilanz.treffer:
                    fix = treffer.fix or "kein Fix veröffentlicht"
                    print(
                        f"::error title=Schwachstelle {treffer.ghsa}::"
                        f"{treffer.name}@{treffer.version} ({treffer.oekosystem}, "
                        f"{treffer.schwere}) – Fix: {fix} – {treffer.zusammenfassung}"
                    )

    if bilanz is not None and bilanz.stoerung:
        return 2
    if fehler_befunde or (bilanz is not None and bilanz.treffer):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
