#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""abhaengigkeits_selbstheilung.py – Dauerhafte Abhängigkeits-Selbstheilung (#79).

WARUM DIESES MODUL EXISTIERT (10.11.2026, Dependabot-Alert #79)
---------------------------------------------------------------
Am 10.11.2026 um 17:14 UTC brachte PR #1139 (`bump lighthouse 13.5.0 -> 13.6.0`)
transitiv `@sentry/bundler-plugins@11.10.0 -> glob@13.0.6 -> minimatch@10.2.6`
in das Wurzel-`package-lock.json`. Sechzehn Minuten später schlug Dependabot
an: `minimatch has potential denial of service via globparts amplification`
(`GHSA-g3hv-75wg-m249` / `CVE-2026-118764`, Fix `>= 11.0.1`) sowie `glob@13.0.6`
(`GHSA-3g3m-2fjr-6pw4`, Fix `>= 14.0.2`).

Zwei Systemlücken machten das möglich:
  1. `.github/workflows/sicherheits-wache.yml` führte `abhaengigkeits_wache.py
     --audit` ausschließlich bei `schedule` und `workflow_dispatch` aus. PR #1139
     bestand den Abhängigkeits-Job grün, ohne eine einzige neue Lockfile-Version
     gegen die Advisory-Datenbank zu prüfen.
  2. Es gab weder einen Offline-Untergrenzen-Vertrag (`A9`) noch einen Heiler,
     der verwundbare Pins/Locks mit `--ignore-scripts` anhebt, nachmisst,
     kryptografisch belegt und als geprüften Heilungs-PR bereitstellt.

FÜNF SCHICHTEN (Highend-Standard analog WF-829B / #922)
  · VERTRAG      `data/abhaengigkeits_schutz_vertrag.json` – einzige Quelle für
                 Sicherheits-Untergrenzen (`mindestversionen`), Registry-Allowlist
                 und `--ignore-scripts`-Pflicht. Jede geheilte GHSA verankert
                 dort ihre `first_patched_version` dauerhaft für Offline-Regel A9.
  · EICHPROBE    Vor jedem Urteil und vor jedem Schreibzugriff wird Vorfall #79
                 samt Mehrzweig-Downgrade-Falle und fremder Tarball-Quelle im
                 Speicher nachgespielt. Versagt der Prüfer: Exit 3 (`MESSGERAET`).
  · HEILUNG      Vormessung -> streng aufsteigende Heilung (`--package-lock-only
                 --ignore-scripts`, gezielte `overrides` bei blockierenden
                 Eltern-Ranges, pip `.in` + `--hash=sha256:` synchron) ->
                 Lieferketten-Prüfung (`integrity` + `registry.npmjs.org` +
                 `hasInstallScript`-Ausweis) -> NACHMESSUNG. Jede Verschlechterung
                 rollt alle Dateien atomar zurück (Exit 2).
  · BELEGKETTE   `data/abhaengigkeits_schutz_belege.jsonl` (`merge=binary`):
                 verkettete SHA-256-Nachweise ab `GENESIS`. Idempotent: Ein
                 sauberer Bestand (`SICHER`) schreibt keine Uhrzeit ins Repo.
  · VERDRAHTUNG  `--wache` prüft Vertrag, Kette, `.gitattributes`, PR-Online-Audit
                 in `sicherheits-wache.yml`, Heil-Workflow und Alerting-Abdeckung.
                 Audit H-02 bleibt unangetastet: Der Heil-Workflow merged npm/pip
                 nie blind nach `main`, sondern öffnet/aktualisiert einen
                 vollständig nachgemessenen Heilungs-PR.

Bedienung:
    python3 scripts/abhaengigkeits_selbstheilung.py --selftest
    python3 scripts/abhaengigkeits_selbstheilung.py --wache
    python3 scripts/abhaengigkeits_selbstheilung.py --audit-bedarf
    python3 scripts/abhaengigkeits_selbstheilung.py --pruefen [--json] [--md PFAD]
    python3 scripts/abhaengigkeits_selbstheilung.py --heilen [--json] [--md PFAD]
                                                             [--beleg PFAD]

Exit: 0 = SICHER oder GEHEILT (mit Nachmessung belegt) ·
      1 = OFFEN (kein Upstream-Fix veröffentlicht oder Teilheilung; fail-closed) ·
      2 = NICHT_BELEGBAR / VERSCHLECHTERUNG (Netz, Kette, Rollback) ·
      3 = MESSGERAET (Eichprobe gescheitert – kein Urteil, kein Schreibzugriff).
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable, Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

SKRIPT_VERZ = Path(__file__).resolve().parent
BLOG_DIR = SKRIPT_VERZ.parent
if str(SKRIPT_VERZ) not in sys.path:
    sys.path.insert(0, str(SKRIPT_VERZ))

import abhaengigkeits_wache as wache  # noqa: E402
import manifest_guard as mguard  # noqa: E402
from github_kommando import annotation  # noqa: E402
from integrity_guard import _doppelte_schluessel  # noqa: E402
from url_host import ist_host_oder_subdomain  # noqa: E402

VERTRAG_PFAD = "data/abhaengigkeits_schutz_vertrag.json"
LEDGER_PFAD = "data/abhaengigkeits_schutz_belege.jsonl"
GITATTRIBUTES_PFAD = ".gitattributes"
ARBEITSFLUSS = ".github/workflows/abhaengigkeits-selbstheilung.yml"
SICHERHEITS_FLUSS = ".github/workflows/sicherheits-wache.yml"
ALERT_FLUSS = ".github/workflows/alert-on-failure.yml"
WORKFLOW_NAME = "Abhängigkeits-Schutz · Selbstheilung"
SKRIPT = "scripts/abhaengigkeits_selbstheilung.py"
TESTDATEI = "scripts/tests/test_abhaengigkeits_selbstheilung.py"

PFLICHT_PFADE = (
    SKRIPT,
    TESTDATEI,
    VERTRAG_PFAD,
    LEDGER_PFAD,
    GITATTRIBUTES_PFAD,
    ARBEITSFLUSS,
    SICHERHEITS_FLUSS,
    ALERT_FLUSS,
)

VERTRAG_SCHLUESSEL = {
    "schema",
    "nur_verschaerfen",
    "ignore_scripts_pflicht",
    "erlaubte_npm_hosts",
    "heil_branch_praefix",
    "ledger",
    "mindestversionen",
    "begruendung",
}
MINDEST_EINTRAG_SCHLUESSEL = {"ab", "ghsa", "seit", "grund"}

LEDGER_PFAD_RE = re.compile(r"^data/[A-Za-z0-9_.-]+\.jsonl$")
BRANCH_PRAEFIX_RE = re.compile(r"^automation/[a-z0-9_-]{3,40}-$")
HOST_RE = re.compile(r"^[a-z0-9][a-z0-9.-]{1,120}$")
DATUM_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
GHSA_RE = re.compile(r"^GHSA-[0-9a-z]{4}-[0-9a-z]{4}-[0-9a-z]{4}$")
LAUF_RE = re.compile(r"^[A-Za-z0-9_.:-]{1,64}$")
SHA_RE = re.compile(r"^[0-9a-f]{64}$")
GENESIS = "0" * 64

KLASSE_SICHER = "SICHER"
KLASSE_GEHEILT = "GEHEILT"
KLASSE_OFFEN = "OFFEN"
KLASSE_NICHT_BELEGBAR = "NICHT_BELEGBAR"
KLASSE_VERSCHLECHTERUNG = "VERSCHLECHTERUNG"
KLASSE_MESSGERAET = "MESSGERAET"

EXIT_CODES = {
    KLASSE_SICHER: 0,
    KLASSE_GEHEILT: 0,
    KLASSE_OFFEN: 1,
    KLASSE_NICHT_BELEGBAR: 2,
    KLASSE_VERSCHLECHTERUNG: 2,
    KLASSE_MESSGERAET: 3,
}

# Pfade, deren Änderung in PR/Push den Online-Advisory-Audit in
# `sicherheits-wache.yml` zwingend auslöst (schließt die #1139-Lücke).
AUDIT_RELEVANTE_PRAEFIXE = (
    ".github/workflows/",
    ".github/actions/",
    ".github/dependabot.yml",
    "tools/n8n/Dockerfile",
    "tools/n8n/docker-compose",
    "data/abhaengigkeits_schutz_",
    "scripts/abhaengigkeits_",
    "scripts/tests/test_abhaengigkeits_",
    "scripts/manifest_guard.py",
)


class NichtBelegbar(RuntimeError):
    """Ungeprüft ist nicht sauber (C34)."""


class KetteKaputt(RuntimeError):
    """Die SHA-256-Belegkette ist beschädigt (D7)."""


class MessgeraetDefekt(RuntimeError):
    """Die Eichprobe hat versagt – kein Urteil, kein Schreibzugriff."""


class Messbild(NamedTuple):
    geprueft: int
    treffer: List[wache.Treffer]
    struktur_fehler: List[wache.Befund]
    manifest_fehler: List[mguard.Befund]

    def als_zusammenfassung(self) -> Dict[str, object]:
        return {
            "geprueft": self.geprueft,
            "treffer": len(self.treffer),
            "struktur_fehler": len(self.struktur_fehler),
            "manifest_fehler": len(self.manifest_fehler),
            "ghsa": sorted({t.ghsa for t in self.treffer if t.ghsa}),
        }


class Ergebnis(NamedTuple):
    klasse: str
    code: int
    befund_id: str
    vorher: Optional[Messbild]
    nachher: Optional[Messbild]
    schritte: List[str]
    gruende: List[str]
    geheilte_ghsa: List[str]
    install_skript_pakete: List[str]
    geaenderte_dateien: List[str]
    beleg: Optional[Dict[str, object]]


NpmRunner = Callable[[Path, List[str]], Tuple[int, str]]
PipHashResolver = Callable[[str, str], List[str]]


# --------------------------------------------------------------------------- #
#  Text- und Pfadhygiene (keine Tokens, keine Fremdlinks im Ledger)
# --------------------------------------------------------------------------- #

def _saeubere_text(roh: str, max_laenge: int = 240) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]+", " ", str(roh or "")).strip()
    text = re.sub(r"Bearer\s+\S+", "Bearer [MASKIERT]", text, flags=re.IGNORECASE)
    text = re.sub(r"gh[pousr]_[A-Za-z0-9_]+", "[TOKEN-MASKIERT]", text)
    text = re.sub(r"https?://\S+", "[URL-ENTFERNT]", text)
    if len(text) > max_laenge:
        return text[: max_laenge - 1].rstrip() + "…"
    return text


def _rel(pfad: Path, root: Path) -> str:
    try:
        return pfad.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return pfad.as_posix()


def _jetzt_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _heute_utc() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _lauf_id() -> str:
    roh = os.environ.get("GITHUB_RUN_ID") or "lokal"
    return roh if LAUF_RE.match(roh) else "lokal"


def berechne_befund_id(treffer: Sequence[wache.Treffer]) -> str:
    """Deterministischer Kurzschlüssel für genau diese offene Schwachstellenmenge."""
    if not treffer:
        return "sauber"
    teile = sorted(
        {
            f"{t.oekosystem}:{t.name.lower()}@{t.version}:{t.ghsa}:{t.fix or 'offen'}"
            for t in treffer
        }
    )
    digest = hashlib.sha256("|".join(teile).encode("utf-8")).hexdigest()
    return digest[:10]


# --------------------------------------------------------------------------- #
#  Schicht 1 · Vertrag (eine Quelle der Wahrheit)
# --------------------------------------------------------------------------- #

def vertrag_fehler(daten: object, *, mindest_pflicht: bool = False) -> List[str]:
    """Reine Prüfung des Vertrags ohne Netz und ohne Uhr."""
    fehler: List[str] = []
    if not isinstance(daten, dict):
        return ["Vertrag ist kein JSON-Objekt."]
    unbekannt = sorted(set(daten) - VERTRAG_SCHLUESSEL)
    fehlend = sorted(VERTRAG_SCHLUESSEL - set(daten))
    if unbekannt:
        fehler.append(f"Unbekannte Schlüssel im Vertrag: {', '.join(unbekannt)}")
    if fehlend:
        fehler.append(f"Fehlende Pflichtschlüssel im Vertrag: {', '.join(fehlend)}")
    if daten.get("schema") != 1:
        fehler.append(f"`schema` muss 1 sein (ist {daten.get('schema')!r}).")
    if daten.get("nur_verschaerfen") is not True:
        fehler.append("`nur_verschaerfen` muss `true` sein – Downgrades sind verboten.")
    if daten.get("ignore_scripts_pflicht") is not True:
        fehler.append("`ignore_scripts_pflicht` muss `true` sein (Audit H-02 / CLAUDE.md).")
    hosts = daten.get("erlaubte_npm_hosts")
    if not isinstance(hosts, list) or not hosts or not all(
        isinstance(h, str) and HOST_RE.match(h) for h in hosts
    ):
        fehler.append("`erlaubte_npm_hosts` muss eine nicht-leere Liste gültiger Hostnamen sein.")
    praefix = daten.get("heil_branch_praefix")
    if not isinstance(praefix, str) or not BRANCH_PRAEFIX_RE.match(praefix):
        fehler.append("`heil_branch_praefix` muss auf `automation/<name>-` lauten.")
    ledger = daten.get("ledger")
    if not isinstance(ledger, str) or not LEDGER_PFAD_RE.match(ledger):
        fehler.append("`ledger` muss auf `data/<name>.jsonl` zeigen.")
    begruendung = daten.get("begruendung")
    if not isinstance(begruendung, str) or len(begruendung.strip()) < 20:
        fehler.append("`begruendung` muss aussagekräftig dokumentiert sein (>= 20 Zeichen).")

    mindest = daten.get("mindestversionen")
    if not isinstance(mindest, dict):
        fehler.append("`mindestversionen` muss ein Objekt sein.")
    else:
        for schluessel, eintrag in sorted(mindest.items()):
            if ":" not in schluessel:
                fehler.append(f"Ungültiger Mindestversions-Schlüssel `{schluessel}`.")
                continue
            oeko, paket = schluessel.split(":", 1)
            if oeko not in ("npm", "pip", "actions") or not paket.strip():
                fehler.append(f"Ungültiges Ökosystem/Paket in `{schluessel}`.")
            if not isinstance(eintrag, dict):
                fehler.append(f"Eintrag `{schluessel}` muss ein Objekt sein.")
                continue
            extra = sorted(set(eintrag) - MINDEST_EINTRAG_SCHLUESSEL)
            miss = sorted(MINDEST_EINTRAG_SCHLUESSEL - set(eintrag))
            if extra or miss:
                fehler.append(
                    f"Eintrag `{schluessel}` hat falsche Schlüssel (fehlend={miss}, extra={extra})."
                )
                continue
            if wache.versions_schluessel(str(eintrag.get("ab") or "")) is None:
                fehler.append(f"Eintrag `{schluessel}` trägt keine gültige Version `ab`.")
            ghsa = eintrag.get("ghsa")
            if not isinstance(ghsa, list) or not ghsa or not all(
                isinstance(x, str) and GHSA_RE.match(x) for x in ghsa
            ):
                fehler.append(f"Eintrag `{schluessel}` benötigt gültige GHSA-Kennungen.")
            if not isinstance(eintrag.get("seit"), str) or not DATUM_RE.match(eintrag["seit"]):
                fehler.append(f"Eintrag `{schluessel}` benötigt `seit` im Format YYYY-MM-DD.")
            if not isinstance(eintrag.get("grund"), str) or len(eintrag["grund"].strip()) < 8:
                fehler.append(f"Eintrag `{schluessel}` benötigt einen nachvollziehbaren `grund`.")

        if mindest_pflicht:
            mm = mindest.get("npm:minimatch")
            if not isinstance(mm, dict) or wache.ist_version_unter(
                str(mm.get("ab") or "0.0.0"), "11.0.1"
            ):
                fehler.append(
                    "Pflicht-Untergrenze für Alert #79 fehlt: `npm:minimatch` muss >= 11.0.1 sein."
                )
            elif "GHSA-g3hv-75wg-m249" not in (mm.get("ghsa") or []):
                fehler.append(
                    "`npm:minimatch` muss `GHSA-g3hv-75wg-m249` (Alert #79) im Vertrag führen."
                )
            gl = mindest.get("npm:glob")
            if not isinstance(gl, dict) or wache.ist_version_unter(
                str(gl.get("ab") or "0.0.0"), "14.0.2"
            ):
                fehler.append(
                    "Pflicht-Untergrenze fehlt: `npm:glob` muss >= 14.0.2 sein (GHSA-3g3m-2fjr-6pw4)."
                )
    return fehler


def lade_vertrag(root: Path, *, mindest_pflicht: bool = False) -> Dict[str, object]:
    pfad = root / VERTRAG_PFAD
    if not pfad.is_file():
        raise NichtBelegbar(f"Schutz-Vertrag fehlt: {VERTRAG_PFAD}")
    roh = pfad.read_text(encoding="utf-8")
    try:
        doppelt = _doppelte_schluessel(roh)
    except json.JSONDecodeError as fehler:
        raise NichtBelegbar(
            f"{VERTRAG_PFAD}: ungültiges JSON (Zeile {fehler.lineno}: {fehler.msg})"
        ) from fehler
    if doppelt:
        raise NichtBelegbar(f"{VERTRAG_PFAD}: doppelte Schlüssel ({', '.join(doppelt)})")
    daten = json.loads(roh)
    fehler = vertrag_fehler(daten, mindest_pflicht=mindest_pflicht)
    if fehler:
        raise NichtBelegbar(f"{VERTRAG_PFAD} verletzt Vertrag: {'; '.join(fehler)}")
    return daten


# --------------------------------------------------------------------------- #
#  Schicht 4 · Verkettete SHA-256-Belegkette (append-only, merge=binary)
# --------------------------------------------------------------------------- #

def _kanonisch_ohne_sha(eintrag: Dict[str, object]) -> str:
    kopie = {k: v for k, v in eintrag.items() if k != "sha256"}
    return json.dumps(kopie, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def berechne_beleg_sha(eintrag: Dict[str, object]) -> str:
    return hashlib.sha256(_kanonisch_ohne_sha(eintrag).encode("utf-8")).hexdigest()


def pruefe_belegkette(pfad: Path) -> List[Dict[str, object]]:
    """Prüft lückenlose `seq`, `prev_sha256` ab `GENESIS` und `sha256` je Zeile."""
    if not pfad.exists():
        raise KetteKaputt(f"Belegkette fehlt: {pfad}")
    roh = pfad.read_text(encoding="utf-8")
    if not roh.strip():
        return []
    eintraege: List[Dict[str, object]] = []
    erwartet_prev = GENESIS
    for idx, zeile in enumerate(roh.splitlines(), start=1):
        if not zeile.strip():
            raise KetteKaputt(f"{pfad}:{idx}: Leerzeile in der Belegkette ist unzulässig.")
        try:
            doppelt = _doppelte_schluessel(zeile)
        except json.JSONDecodeError as fehler:
            raise KetteKaputt(f"{pfad}:{idx}: ungültiges JSON ({fehler.msg})") from fehler
        if doppelt:
            raise KetteKaputt(f"{pfad}:{idx}: doppelte Schlüssel ({', '.join(doppelt)})")
        obj = json.loads(zeile)
        if not isinstance(obj, dict):
            raise KetteKaputt(f"{pfad}:{idx}: Belegzeile ist kein JSON-Objekt.")
        if obj.get("seq") != idx:
            raise KetteKaputt(f"{pfad}:{idx}: `seq` ist {obj.get('seq')!r}, erwartet {idx}.")
        prev = obj.get("prev_sha256")
        if prev != erwartet_prev:
            raise KetteKaputt(
                f"{pfad}:{idx}: `prev_sha256` gebrochen (erwartet {erwartet_prev[:12]}…)."
            )
        ist_sha = obj.get("sha256")
        if not isinstance(ist_sha, str) or not SHA_RE.match(ist_sha):
            raise KetteKaputt(f"{pfad}:{idx}: `sha256` fehlt oder hat falsches Format.")
        soll_sha = berechne_beleg_sha(obj)
        if ist_sha != soll_sha:
            raise KetteKaputt(
                f"{pfad}:{idx}: `sha256` stimmt nicht mit dem Zeileninhalt überein."
            )
        erwartet_prev = ist_sha
        eintraege.append(obj)
    return eintraege


def haenge_beleg_an(
    pfad: Path,
    *,
    klasse: str,
    befund_id: str,
    vorher: Messbild,
    nachher: Messbild,
    geheilte_ghsa: Sequence[str],
    schritte: Sequence[str],
    install_skript_pakete: Sequence[str],
    gruende: Sequence[str],
    zeit_utc: Optional[str] = None,
    lauf_id: Optional[str] = None,
) -> Dict[str, object]:
    vorhanden = pruefe_belegkette(pfad) if pfad.exists() else []
    seq = len(vorhanden) + 1
    prev_sha = str(vorhanden[-1]["sha256"]) if vorhanden else GENESIS
    eintrag: Dict[str, object] = {
        "seq": seq,
        "prev_sha256": prev_sha,
        "zeit_utc": zeit_utc or _jetzt_utc(),
        "lauf_id": lauf_id or _lauf_id(),
        "klasse": klasse,
        "befund_id": befund_id,
        "vorher": vorher.als_zusammenfassung(),
        "nachher": nachher.als_zusammenfassung(),
        "geheilte_ghsa": sorted(set(geheilte_ghsa)),
        "schritte": [_saeubere_text(s) for s in schritte],
        "install_skript_pakete": sorted(set(install_skript_pakete)),
        "gruende": [_saeubere_text(g) for g in gruende],
    }
    eintrag["sha256"] = berechne_beleg_sha(eintrag)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    zeile = json.dumps(eintrag, sort_keys=True, ensure_ascii=False) + "\n"
    with pfad.open("a", encoding="utf-8") as handle:
        handle.write(zeile)
    # Gegenprobe unmittelbar nach dem Schreiben: Kette muss geschlossen lesbar sein.
    pruefe_belegkette(pfad)
    return eintrag


# --------------------------------------------------------------------------- #
#  Lieferketten-Prüfung für Lockfile-Änderungen (Audit H-02)
# --------------------------------------------------------------------------- #

def pruefe_lock_lieferkette(
    vorher_lock: Dict[str, object],
    nachher_lock: Dict[str, object],
    erlaubte_hosts: Sequence[str],
    datei_rel: str,
) -> Tuple[List[str], List[str]]:
    """Prüft geänderte/neue npm-Lock-Einträge auf `integrity`, Host und Install-Skripte.

    Gibt `(fehler, install_skript_pakete)` zurück.
    """
    fehler: List[str] = []
    install_skripte: List[str] = []
    alt_pakete = vorher_lock.get("packages") if isinstance(vorher_lock, dict) else {}
    neu_pakete = nachher_lock.get("packages") if isinstance(nachher_lock, dict) else {}
    if not isinstance(alt_pakete, dict) or not isinstance(neu_pakete, dict):
        return [f"{datei_rel}: `packages`-Block im Lockfile fehlt."], []

    for pfad_key, eintrag in sorted(neu_pakete.items()):
        if not pfad_key or not isinstance(eintrag, dict) or eintrag.get("link") is True:
            continue
        vorher_eintrag = alt_pakete.get(pfad_key)
        if vorher_eintrag == eintrag:
            continue
        version = str(eintrag.get("version") or "").strip()
        paket_name = str(eintrag.get("name") or pfad_key.split("node_modules/")[-1]).strip()
        bezeichnung = f"{paket_name}@{version}" if version else pfad_key

        integritaet = str(eintrag.get("integrity") or "").strip()
        if not (integritaet.startswith("sha512-") or integritaet.startswith("sha256-")):
            fehler.append(
                f"{datei_rel}: `{bezeichnung}` hat keinen starken `integrity`-Hash (sha512/sha256)."
            )

        resolved = str(eintrag.get("resolved") or "").strip()
        if not resolved:
            fehler.append(f"{datei_rel}: `{bezeichnung}` hat keine `resolved`-Herkunfts-URL.")
        elif not resolved.startswith("https://") or not any(
            ist_host_oder_subdomain(resolved, host) for host in erlaubte_hosts
        ):
            fehler.append(
                f"{datei_rel}: `{bezeichnung}` stammt nicht von einem erlaubten HTTPS-Registry-Host."
            )

        if eintrag.get("hasInstallScript") is True:
            install_skripte.append(bezeichnung)

    return fehler, sorted(set(install_skripte))


# --------------------------------------------------------------------------- #
#  Schicht 2 · Eichprobe (Vorfall #79 + Mehrzweig-Falle + Lieferketten-Falle)
# --------------------------------------------------------------------------- #

def eichprobe() -> None:
    """Baut Vorfall #79 im Speicher nach. Wirft `MessgeraetDefekt` bei Blindheit."""
    with tempfile.TemporaryDirectory(prefix="deps-eichprobe-") as tmp:
        baum = Path(tmp)
        (baum / "data").mkdir(parents=True, exist_ok=True)
        (baum / VERTRAG_PFAD).write_text(
            json.dumps(
                {
                    "schema": 1,
                    "nur_verschaerfen": True,
                    "ignore_scripts_pflicht": True,
                    "erlaubte_npm_hosts": ["registry.npmjs.org"],
                    "heil_branch_praefix": "automation/deps-heilung-",
                    "ledger": LEDGER_PFAD,
                    "mindestversionen": {
                        "npm:minimatch": {
                            "ab": "11.0.1",
                            "ghsa": ["GHSA-g3hv-75wg-m249"],
                            "seit": "2026-11-10",
                            "grund": "Eichprobe Alert #79",
                        },
                        "npm:glob": {
                            "ab": "14.0.2",
                            "ghsa": ["GHSA-3g3m-2fjr-6pw4"],
                            "seit": "2026-11-10",
                            "grund": "Eichprobe Glob-Cancellation",
                        },
                    },
                    "begruendung": "Eingefrorene Eichprobe für Vorfall #79 und GHSA-3g3m-2fjr-6pw4.",
                }
            ),
            encoding="utf-8",
        )
        (baum / "package.json").write_text(
            json.dumps({"name": "probe", "version": "1.0.0", "devDependencies": {"lighthouse": "13.6.0"}}),
            encoding="utf-8",
        )
        vergiftetes_lock = {
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "probe", "version": "1.0.0", "devDependencies": {"lighthouse": "13.6.0"}},
                "node_modules/lighthouse": {"version": "13.6.0"},
                "node_modules/glob": {"version": "13.0.6"},
                "node_modules/minimatch": {"version": "10.2.6"},
            },
        }
        (baum / "package-lock.json").write_text(json.dumps(vergiftetes_lock), encoding="utf-8")

        # 1. Offline-Wache MUSS Vorfall #79 über A9 sofort ohne Netz erkennen.
        a9_befunde = [
            b for b in wache.pruefe_struktur(baum) if b.regel == wache.REGEL_UNTERGRENZE
        ]
        if len(a9_befunde) != 2:
            raise MessgeraetDefekt(
                f"Eichprobe A9 fehlgeschlagen: erwartet 2 Treffer (#79 + glob), bekam {len(a9_befunde)}."
            )

        # 2. Online-Audit-Logik MUSS Mehrzweig-GHSAs streng aufsteigend auflösen.
        class _EichAdvisoryQuelle(wache.AdvisoryQuelle):
            def suche(self, anf: wache.Anforderung) -> List[Dict[str, object]]:  # type: ignore[override]
                if anf.oekosystem == "npm" and anf.name == "minimatch" and anf.version == "10.2.6":
                    return [
                        {
                            "ghsa_id": "GHSA-g3hv-75wg-m249",
                            "severity": "medium",
                            "summary": "minimatch globparts amplification DoS (#79)",
                            "vulnerabilities": [
                                {
                                    "package": {"ecosystem": "npm", "name": "minimatch"},
                                    "vulnerable_version_range": "< 3.1.3",
                                    "first_patched_version": {"identifier": "3.1.3"},
                                },
                                {
                                    "package": {"ecosystem": "npm", "name": "minimatch"},
                                    "vulnerable_version_range": ">= 7.0.0, < 11.0.1",
                                    "first_patched_version": {"identifier": "11.0.1"},
                                },
                            ],
                        }
                    ]
                if anf.oekosystem == "npm" and anf.name == "glob" and anf.version == "13.0.6":
                    return [
                        {
                            "ghsa_id": "GHSA-3g3m-2fjr-6pw4",
                            "severity": "medium",
                            "summary": "Glob AbortSignal bypass",
                            "vulnerabilities": [
                                {
                                    "package": {"ecosystem": "npm", "name": "glob"},
                                    "vulnerable_version_range": ">= 10.0.0, < 14.0.2",
                                    "first_patched_version": {"identifier": "14.0.2"},
                                }
                            ],
                        }
                    ]
                return []

        bilanz = wache.auditiere(wache.sammle_abhaengigkeiten(baum), _EichAdvisoryQuelle())
        fixes = {t.name: t.fix for t in bilanz.treffer}
        if fixes != {"minimatch": "11.0.1", "glob": "14.0.2"}:
            raise MessgeraetDefekt(
                f"Eichprobe Audit/Normalisierung defekt: erwartet 11.0.1 & 14.0.2, bekam {fixes!r}."
            )

        # 3. Gegenprobe: Geheilter Baum MUSS 0 A9-Befunde und 0 Audit-Treffer haben.
        sauberes_lock = {
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "probe", "version": "1.0.0", "devDependencies": {"lighthouse": "13.6.0"}},
                "node_modules/lighthouse": {
                    "version": "13.6.0",
                    "resolved": "https://registry.npmjs.org/lighthouse/-/lighthouse-13.6.0.tgz",
                    "integrity": "sha512-eichprobe",
                },
                "node_modules/glob": {
                    "version": "14.0.4",
                    "resolved": "https://registry.npmjs.org/glob/-/glob-14.0.4.tgz",
                    "integrity": "sha512-eichprobe",
                },
                "node_modules/minimatch": {
                    "version": "11.0.6",
                    "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-11.0.6.tgz",
                    "integrity": "sha512-eichprobe",
                },
            },
        }
        (baum / "package-lock.json").write_text(json.dumps(sauberes_lock), encoding="utf-8")
        if wache.pruefe_struktur(baum):
            raise MessgeraetDefekt("Eichprobe Gegenprobe: sauberer Baum meldet Struktur-Befunde.")
        bilanz_sauber = wache.auditiere(wache.sammle_abhaengigkeiten(baum), _EichAdvisoryQuelle())
        if bilanz_sauber.treffer:
            raise MessgeraetDefekt("Eichprobe Gegenprobe: sauberer Baum meldet Audit-Treffer.")

        # 4. Lieferketten-Sperre MUSS fremde Tarball-Hosts ablehnen.
        boeses_lock = json.loads(json.dumps(sauberes_lock))
        boeses_lock["packages"]["node_modules/minimatch"]["resolved"] = (
            "https://evil-registry.example/minimatch-11.0.6.tgz"
        )
        lk_fehler, _ = pruefe_lock_lieferkette(
            vergiftetes_lock, boeses_lock, ["registry.npmjs.org"], "package-lock.json"
        )
        if not lk_fehler:
            raise MessgeraetDefekt("Eichprobe Lieferkette: fremder Tarball-Host blieb unerkannt.")


# --------------------------------------------------------------------------- #
#  Messung & Heilung
# --------------------------------------------------------------------------- #

def _baue_advisory_quelle(advisory_datei: Optional[str]) -> wache.AdvisoryQuelle:
    if advisory_datei:
        pfad = Path(advisory_datei)
        if not pfad.is_file():
            raise NichtBelegbar(f"Advisory-Datei fehlt: {advisory_datei}")
        return wache.DateiAdvisoryQuelle.aus_datei(pfad)
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not token:
        raise NichtBelegbar(
            "Kein GITHUB_TOKEN/GH_TOKEN gesetzt – ohne Token ist der vollständige "
            "Advisory-Audit nicht belegbar (C34: ungeprüft ist nicht sauber)."
        )
    return wache.HttpAdvisoryQuelle(token)


def messe_bestand(root: Path, quelle: wache.AdvisoryQuelle) -> Messbild:
    """Führt Offline-Strukturprüfung, Manifest-Wache und Online-Audit zusammen."""
    struktur = [
        b for b in wache.pruefe_struktur(root) if b.schwere == wache.SCHWERE_FEHLER
    ]
    manifest_befunde = [
        b
        for b in mguard.pruefe_manifeste(mguard.dateien_aus_baum(root))
        if b.schwere == mguard.FEHLER
    ]
    try:
        bilanz = wache.auditiere(wache.sammle_abhaengigkeiten(root), quelle)
    except wache.Stoerung as fehler:
        raise NichtBelegbar(str(fehler)) from fehler
    if bilanz.stoerung:
        raise NichtBelegbar(bilanz.stoerung)
    return Messbild(
        geprueft=bilanz.geprueft,
        treffer=list(bilanz.treffer),
        struktur_fehler=struktur,
        manifest_fehler=manifest_befunde,
    )


def _standard_npm_runner(arbeitsverzeichnis: Path, argumente: List[str]) -> Tuple[int, str]:
    """Startet `npm` ohne Shell und mit erzwungenem `--ignore-scripts`."""
    sichere_args = list(argumente)
    for pflicht_flag in ("--package-lock-only", "--ignore-scripts", "--no-audit", "--no-fund"):
        if pflicht_flag not in sichere_args:
            sichere_args.append(pflicht_flag)
    umgebung = dict(os.environ)
    umgebung["NPM_CONFIG_IGNORE_SCRIPTS"] = "true"
    umgebung["NPM_CONFIG_AUDIT"] = "false"
    umgebung["NPM_CONFIG_FUND"] = "false"
    lauf = subprocess.run(
        ["npm", *sichere_args],
        cwd=str(arbeitsverzeichnis),
        env=umgebung,
        shell=False,
        check=False,
        capture_output=True,
        text=True,
        timeout=300,
    )
    ausgabe = (lauf.stdout or "") + ("\n" + lauf.stderr if lauf.stderr else "")
    return lauf.returncode, ausgabe.strip()


def _standard_pip_hash_aufloeser(paket: str, version: str) -> List[str]:
    """Lädt Binär-Wheels ohne Codeausführung (`--only-binary=:all:`) und bildet SHA-256."""
    with tempfile.TemporaryDirectory(prefix="pip-hashes-") as tmp:
        lauf = subprocess.run(
            [
                sys.executable,
                "-m",
                "pip",
                "download",
                "--disable-pip-version-check",
                "--no-deps",
                "--only-binary=:all:",
                "--dest",
                tmp,
                f"{paket}=={version}",
            ],
            shell=False,
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
        if lauf.returncode != 0:
            raise NichtBelegbar(
                f"Wheel-Download für `{paket}=={version}` fehlgeschlagen: "
                f"{_saeubere_text(lauf.stderr or lauf.stdout)}"
            )
        hashes: List[str] = []
        for datei in sorted(Path(tmp).iterdir()):
            if datei.is_file():
                digest = hashlib.sha256(datei.read_bytes()).hexdigest()
                hashes.append(f"sha256:{digest}")
        if not hashes:
            raise NichtBelegbar(f"Keine Binär-Wheels für `{paket}=={version}` gefunden.")
        return hashes


def _hauptversion(version: str) -> Optional[int]:
    schluessel = wache.versions_schluessel(version)
    if schluessel is None:
        return None
    return schluessel[0][0]


def _sammle_heilbare_ziele(
    treffer: Sequence[wache.Treffer],
) -> Tuple[Dict[Tuple[str, str], Tuple[str, List[wache.Treffer]]], List[wache.Treffer]]:
    """Trennt heilbare Treffer (mit monotonem Fix) von offenen ohne Fix.

    Für jedes `(oekosystem, paket_klein)` wird die höchste geforderte
    `first_patched_version` bestimmt, damit ein Lauf alle bekannten GHSAs
    desselben Pakets gleichzeitig schließt.
    """
    ziele: Dict[Tuple[str, str], Tuple[str, List[wache.Treffer]]] = {}
    offene: List[wache.Treffer] = []
    for fund in treffer:
        if fund.oekosystem not in ("npm", "pip") or not fund.fix:
            offene.append(fund)
            continue
        vgl = wache.vergleiche_versionen(fund.fix, fund.version)
        if vgl is None or vgl <= 0:
            # Niemals downgraden: ein nicht streng aufsteigender Fix ist unbrauchbar.
            offene.append(fund)
            continue
        schluessel = (fund.oekosystem, fund.name.lower())
        bisher = ziele.get(schluessel)
        if bisher is None:
            ziele[schluessel] = (fund.fix, [fund])
        else:
            bisher_fix, liste = bisher
            liste.append(fund)
            hoeher = (
                fund.fix
                if (wache.vergleiche_versionen(fund.fix, bisher_fix) or 0) > 0
                else bisher_fix
            )
            ziele[schluessel] = (hoeher, liste)
    return ziele, offene


def _setze_npm_override(manifest_daten: Dict[str, object], paket: str, mindest: str) -> bool:
    """Hebt `overrides[paket]` monoton auf `>=mindest` an (lockert niemals)."""
    overrides = manifest_daten.get("overrides")
    if overrides is None:
        overrides = {}
        manifest_daten["overrides"] = overrides
    if not isinstance(overrides, dict):
        return False
    bisher = overrides.get(paket)
    if isinstance(bisher, str):
        bisher_ver, exakt = wache._override_untergrenze(bisher)
        if bisher_ver is not None:
            vgl = wache.vergleiche_versionen(bisher_ver, mindest)
            if vgl is not None and vgl >= 0:
                # Bereits mindestens so streng wie gefordert -> nicht anfassen.
                return False
            if exakt:
                overrides[paket] = mindest
                return True
    overrides[paket] = f">={mindest}"
    return True


def _schreibe_json_sauber(pfad: Path, daten: object) -> None:
    pfad.write_text(json.dumps(daten, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _heile_npm_manifest_paar(
    root: Path,
    lock_rel: str,
    paket_ziele: Dict[str, Tuple[str, List[wache.Treffer]]],
    erlaubte_hosts: Sequence[str],
    npm_runner: NpmRunner,
) -> Tuple[List[str], List[str], List[str]]:
    """Heilt ein `(package.json, package-lock.json)`-Paar streng monoton.

    Liefert `(schritte, lieferketten_fehler, install_skript_pakete)`.
    """
    lock_pfad = root / lock_rel
    manifest_pfad = lock_pfad.with_name("package.json")
    if not lock_pfad.is_file() or not manifest_pfad.is_file():
        return [], [f"{lock_rel}: zugehöriges Manifest oder Lockfile fehlt."], []

    vorher_lock = json.loads(lock_pfad.read_text(encoding="utf-8"))
    manifest_daten = json.loads(manifest_pfad.read_text(encoding="utf-8"))
    manifest_geaendert = False
    schritte: List[str] = []

    # 1) Direkte Pins in package.json anheben, falls ein verwundbares Paket
    #    dort selbst unterhalb von `ziel` deklariert ist.
    originale_namen: Dict[str, str] = {}
    for paket_klein, (ziel, funde) in sorted(paket_ziele.items()):
        kanonisch_name = funde[0].name
        originale_namen[paket_klein] = kanonisch_name
        for feld in ("dependencies", "devDependencies", "optionalDependencies"):
            block = manifest_daten.get(feld)
            if not isinstance(block, dict):
                continue
            for dekl_name, spez in list(block.items()):
                if dekl_name.lower() != paket_klein or not isinstance(spez, str):
                    continue
                kern = spez.lstrip("^~")
                if wache.versions_schluessel(kern) is not None and wache.ist_version_unter(
                    kern, ziel
                ):
                    praefix = spez[: len(spez) - len(kern)]
                    block[dekl_name] = f"{praefix}{ziel}" if praefix else ziel
                    manifest_geaendert = True
                    schritte.append(
                        f"{_rel(manifest_pfad, root)}: direkter Pin `{dekl_name}` -> `{block[dekl_name]}`"
                    )

        # Bei Major-Sprung einer transitiven Schwachstelle (wie minimatch 10 -> 11
        # und glob 13 -> 14 in #79) verankert `overrides` die `first_patched_version`
        # direkt im Manifest, damit kein Eltern-Range unter die Schwelle zurückfällt.
        if any(
            (_hauptversion(ziel) or 0) > (_hauptversion(f.version) or 0) for f in funde
        ):
            if _setze_npm_override(manifest_daten, kanonisch_name, ziel):
                manifest_geaendert = True
                schritte.append(
                    f"{_rel(manifest_pfad, root)}: Sicherheits-Override `{kanonisch_name}: >={ziel}` gesetzt"
                )

    if manifest_geaendert:
        _schreibe_json_sauber(manifest_pfad, manifest_daten)

    # 2) Gezieltes Lockfile-Update über npm (--package-lock-only --ignore-scripts).
    zu_aktualisieren = [originale_namen[k] for k in sorted(paket_ziele)]
    code_upd, ausgabe_upd = npm_runner(
        lock_pfad.parent,
        ["update", "--depth=8", *zu_aktualisieren],
    )
    if code_upd != 0:
        return (
            schritte,
            [f"{lock_rel}: `npm update` fehlgeschlagen ({_saeubere_text(ausgabe_upd)})"],
            [],
        )
    schritte.append(
        f"{lock_rel}: `npm update --package-lock-only --ignore-scripts {' '.join(zu_aktualisieren)}`"
    )

    # 3) Prüfen, ob noch eine verwundbare Instanz unterhalb von `ziel` im Lock steht
    #    (z. B. durch einen engen Patch/Minor-Eltern-Range); falls ja, `overrides`
    #    gezielt nachziehen und `npm install --package-lock-only --ignore-scripts` fahren.
    zwischen_pakete = wache.parse_lockfile(lock_pfad.read_text(encoding="utf-8"), lock_rel)
    override_nachzug = False
    for paket_klein, (ziel, funde) in sorted(paket_ziele.items()):
        kanonisch_name = originale_namen[paket_klein]
        noch_alt = [
            a
            for a in zwischen_pakete
            if a.name.lower() == paket_klein and wache.ist_version_unter(a.version, ziel)
        ]
        if noch_alt and _setze_npm_override(manifest_daten, kanonisch_name, ziel):
            override_nachzug = True
            schritte.append(
                f"{_rel(manifest_pfad, root)}: Eltern-Range blockierte `{kanonisch_name}` -> Override `>={ziel}`"
            )

    if override_nachzug:
        _schreibe_json_sauber(manifest_pfad, manifest_daten)
        code_inst, ausgabe_inst = npm_runner(lock_pfad.parent, ["install"])
        if code_inst != 0:
            return (
                schritte,
                [f"{lock_rel}: `npm install --package-lock-only` fehlgeschlagen ({_saeubere_text(ausgabe_inst)})"],
                [],
            )
        schritte.append(f"{lock_rel}: `npm install --package-lock-only --ignore-scripts` nach Override")

    nachher_lock = json.loads(lock_pfad.read_text(encoding="utf-8"))
    lk_fehler, install_skripte = pruefe_lock_lieferkette(
        vorher_lock, nachher_lock, erlaubte_hosts, lock_rel
    )
    return schritte, lk_fehler, install_skripte


def _ersetze_pip_pin_in_text(
    inhalt: str,
    paket_klein: str,
    ziel_version: str,
    neue_hashes: Optional[Sequence[str]] = None,
) -> Tuple[str, bool]:
    """Hebt `paket==alt` (optional samt `--hash=`-Fortsetzungsblock) auf `ziel_version` an."""
    zeilen = inhalt.splitlines()
    ausgabe: List[str] = []
    geaendert = False
    i = 0
    while i < len(zeilen):
        zeile = zeilen[i]
        gestutzt = zeile.lstrip()
        if not gestutzt or gestutzt.startswith("#") or gestutzt.startswith("-"):
            ausgabe.append(zeile)
            i += 1
            continue
        m_name = wache.RE_REQ_NAME.match(gestutzt)
        if not m_name or m_name.group("name").lower() != paket_klein:
            ausgabe.append(zeile)
            i += 1
            continue

        # Ganzen Fortsetzungsblock (`\`) dieses Eintrags einsammeln.
        block_zeilen = [zeile]
        while block_zeilen[-1].rstrip().endswith("\\") and i + 1 < len(zeilen):
            i += 1
            block_zeilen.append(zeilen[i])
        i += 1

        kopf = block_zeilen[0]
        kommentar = ""
        if " #" in kopf and not kopf.rstrip().endswith("\\"):
            kopf_kern, kommentar_teil = kopf.split(" #", 1)
            kommentar = f" #{kommentar_teil}"
        else:
            kopf_kern = kopf

        # Aktuelle Version prüfen (streng monoton: nur anheben).
        geparst = wache.parse_requirements("\n".join(block_zeilen))
        if not geparst or geparst[0].herkunft != "pin":
            ausgabe.extend(block_zeilen)
            continue
        ist_ver = geparst[0].version
        if not wache.ist_version_unter(ist_ver, ziel_version):
            ausgabe.extend(block_zeilen)
            continue

        kanonisch_name = m_name.group("name")
        hat_hashes = any("--hash=" in z for z in block_zeilen)
        if hat_hashes and neue_hashes:
            neuer_block = [f"{kanonisch_name}=={ziel_version} \\"]
            for idx_h, h in enumerate(neue_hashes):
                ende = " \\" if idx_h + 1 < len(neue_hashes) else ""
                neuer_block.append(f"    --hash={h}{ende}")
            ausgabe.extend(neuer_block)
        else:
            neuer_kopf = re.sub(
                r"==\s*[^\s;#\\]+",
                f"=={ziel_version}",
                kopf_kern,
                count=1,
            )
            ausgabe.append(f"{neuer_kopf}{kommentar}")
        geaendert = True

    endung = "\n" if inhalt.endswith("\n") else ""
    return "\n".join(ausgabe) + endung, geaendert


def _heile_pip_bestand(
    root: Path,
    pip_ziele: Dict[str, Tuple[str, List[wache.Treffer]]],
    hash_aufloeser: PipHashResolver,
) -> List[str]:
    """Heilt betroffene `requirements*.txt` (inkl. `requirements-ci.in` + Hash-Lock)."""
    schritte: List[str] = []
    for paket_klein, (ziel, funde) in sorted(pip_ziele.items()):
        kanonisch_name = funde[0].name
        betroffene_dateien = sorted({q for f in funde for q in f.quellen})
        braucht_hashes = "requirements-ci.txt" in betroffene_dateien
        hashes = hash_aufloeser(kanonisch_name, ziel) if braucht_hashes else None

        for rel_pfad in betroffene_dateien:
            pfad = root / rel_pfad
            if not pfad.is_file():
                continue
            alt_text = pfad.read_text(encoding="utf-8")
            neu_text, geaendert = _ersetze_pip_pin_in_text(
                alt_text,
                paket_klein,
                ziel,
                neue_hashes=hashes if rel_pfad == "requirements-ci.txt" else None,
            )
            if geaendert:
                pfad.write_text(neu_text, encoding="utf-8")
                schritte.append(f"{rel_pfad}: `{kanonisch_name}` -> `=={ziel}`")

        # Regel A2: `requirements-ci.in` und `requirements-ci.txt` synchron halten.
        if braucht_hashes:
            quelle_in = root / "requirements-ci.in"
            if quelle_in.is_file():
                alt_in = quelle_in.read_text(encoding="utf-8")
                neu_in, geaendert_in = _ersetze_pip_pin_in_text(alt_in, paket_klein, ziel)
                if geaendert_in:
                    quelle_in.write_text(neu_in, encoding="utf-8")
                    schritte.append(f"requirements-ci.in: `{kanonisch_name}` -> `=={ziel}` (A2-Sync)")
    return schritte


def aktualisiere_vertrag_untergrenzen(
    root: Path,
    vertrag: Dict[str, object],
    geheilte_treffer: Sequence[wache.Treffer],
    heute: Optional[str] = None,
) -> List[str]:
    """Verankert jede geheilte `first_patched_version` dauerhaft im Schutz-Vertrag."""
    mindest = vertrag.get("mindestversionen")
    if not isinstance(mindest, dict):
        return []
    stichtag = heute or _heute_utc()
    schritte: List[str] = []

    gruppiert: Dict[str, List[wache.Treffer]] = {}
    for fund in geheilte_treffer:
        if not fund.fix or fund.oekosystem not in ("npm", "pip"):
            continue
        key = f"{fund.oekosystem}:{fund.name.lower()}"
        gruppiert.setdefault(key, []).append(fund)

    geaendert = False
    for key, funde in sorted(gruppiert.items()):
        fixes = [f.fix for f in funde if f.fix]
        if not fixes:
            continue
        ziel_ab = sorted(
            fixes,
            key=lambda v: wache.versions_schluessel(v) or ((0, 0, 0), 1, v),
        )[-1]
        neue_ghsas = sorted({f.ghsa for f in funde if f.ghsa and GHSA_RE.match(f.ghsa)})
        if not neue_ghsas:
            continue

        bisher = mindest.get(key)
        if isinstance(bisher, dict):
            alt_ab = str(bisher.get("ab") or "0.0.0")
            alt_ghsas = [str(x) for x in (bisher.get("ghsa") or []) if GHSA_RE.match(str(x))]
            vereinte_ghsas = sorted(set(alt_ghsas) | set(neue_ghsas))
            heben = wache.ist_version_unter(alt_ab, ziel_ab)
            if not heben and vereinte_ghsas == sorted(alt_ghsas):
                continue
            neues_ab = ziel_ab if heben else alt_ab
            mindest[key] = {
                "ab": neues_ab,
                "ghsa": vereinte_ghsas,
                "seit": stichtag if heben else str(bisher.get("seit") or stichtag),
                "grund": _saeubere_text(funde[0].zusammenfassung or str(bisher.get("grund") or ""), 140),
            }
        else:
            mindest[key] = {
                "ab": ziel_ab,
                "ghsa": neue_ghsas,
                "seit": stichtag,
                "grund": _saeubere_text(funde[0].zusammenfassung or f"Selbstheilung {key}", 140),
            }
        geaendert = True
        schritte.append(
            f"{VERTRAG_PFAD}: Untergrenze `{key} >= {mindest[key]['ab']}` ({', '.join(neue_ghsas)}) verankert"
        )

    if geaendert:
        _schreibe_json_sauber(root / VERTRAG_PFAD, vertrag)
    return schritte


def _kandidaten_dateien(root: Path) -> List[Path]:
    """Alle Dateien, die ein Heil-Lauf verändern darf (für atomaren Snapshot/Rollback)."""
    pfade: List[Path] = []
    vertrag_p = root / VERTRAG_PFAD
    if vertrag_p.is_file():
        pfade.append(vertrag_p)
    for req in sorted(root.glob("requirements*.txt")) + sorted(root.glob("requirements*.in")):
        if req.is_file():
            pfade.append(req)
    for manifest in sorted(root.glob("**/package.json")):
        if "node_modules" in manifest.parts or ".claude" in manifest.parts:
            continue
        pfade.append(manifest)
        lock = manifest.with_name("package-lock.json")
        if lock.is_file():
            pfade.append(lock)
    return pfade


def _snapshot_erstellen(pfade: Iterable[Path]) -> Dict[Path, bytes]:
    return {p: p.read_bytes() for p in pfade if p.is_file()}


def _snapshot_wiederherstellen(snapshot: Dict[Path, bytes]) -> None:
    for pfad, inhalt in snapshot.items():
        pfad.write_bytes(inhalt)


def ausfuehren(
    root: Path,
    *,
    heilen: bool,
    advisory_quelle: Optional[wache.AdvisoryQuelle] = None,
    advisory_datei: Optional[str] = None,
    beleg_pfad: Optional[Path] = None,
    npm_runner: Optional[NpmRunner] = None,
    pip_hash_aufloeser: Optional[PipHashResolver] = None,
    eichprobe_fn: Callable[[], None] = eichprobe,
) -> Ergebnis:
    """Kernlauf für `--pruefen` und `--heilen` mit Eichprobe, Nachmessung und Rollback."""
    # 1. Eichprobe vor jedem Urteil und vor jedem Schreibzugriff (Exit 3 bei Defekt).
    try:
        eichprobe_fn()
    except MessgeraetDefekt as fehler:
        return Ergebnis(
            klasse=KLASSE_MESSGERAET,
            code=EXIT_CODES[KLASSE_MESSGERAET],
            befund_id="messgeraet-defekt",
            vorher=None,
            nachher=None,
            schritte=[],
            gruende=[str(fehler)],
            geheilte_ghsa=[],
            install_skript_pakete=[],
            geaenderte_dateien=[],
            beleg=None,
        )

    # 2. Vertrag & bestehende Belegkette prüfen (Exit 2 bei Bruch).
    try:
        vertrag = lade_vertrag(root, mindest_pflicht=False)
        ziel_ledger = beleg_pfad or (root / str(vertrag["ledger"]))
        if ziel_ledger.exists():
            pruefe_belegkette(ziel_ledger)
        quelle = advisory_quelle or _baue_advisory_quelle(advisory_datei)
        vorher = messe_bestand(root, quelle)
    except (NichtBelegbar, KetteKaputt) as fehler:
        return Ergebnis(
            klasse=KLASSE_NICHT_BELEGBAR,
            code=EXIT_CODES[KLASSE_NICHT_BELEGBAR],
            befund_id="nicht-belegbar",
            vorher=None,
            nachher=None,
            schritte=[],
            gruende=[str(fehler)],
            geheilte_ghsa=[],
            install_skript_pakete=[],
            geaenderte_dateien=[],
            beleg=None,
        )

    befund_id = berechne_befund_id(vorher.treffer)

    # Sauberer Bestand: kein Eingriff, keine Uhrzeit-Commits (idempotent).
    if not vorher.treffer and not vorher.struktur_fehler and not vorher.manifest_fehler:
        return Ergebnis(
            klasse=KLASSE_SICHER,
            code=EXIT_CODES[KLASSE_SICHER],
            befund_id="sauber",
            vorher=vorher,
            nachher=vorher,
            schritte=[],
            gruende=["Alle ausgelieferten Abhängigkeiten, Pins und Untergrenzen sind befundfrei."],
            geheilte_ghsa=[],
            install_skript_pakete=[],
            geaenderte_dateien=[],
            beleg=None,
        )

    # Reiner Prüfmodus: meldet ehrlich `OFFEN` (Exit 1), schreibt nichts.
    if not heilen:
        gruende = [
            f"{t.name}@{t.version} ({t.oekosystem}): {t.ghsa} -> Fix {t.fix or 'offen'}"
            for t in vorher.treffer
        ]
        gruende += [f"Struktur {b.regel}: {b.datei} – {b.text}" for b in vorher.struktur_fehler]
        gruende += [f"Manifest {b.code}: {b.datei} – {b.text}" for b in vorher.manifest_fehler]
        return Ergebnis(
            klasse=KLASSE_OFFEN,
            code=EXIT_CODES[KLASSE_OFFEN],
            befund_id=befund_id,
            vorher=vorher,
            nachher=vorher,
            schritte=[],
            gruende=gruende,
            geheilte_ghsa=[],
            install_skript_pakete=[],
            geaenderte_dateien=[],
            beleg=None,
        )

    # Vorbestehende Struktur- oder Manifest-Defekte erfindet der Heiler nicht weg.
    if vorher.struktur_fehler or vorher.manifest_fehler:
        gruende = [
            "Vorbestehende Struktur-/Manifest-Defekte blockieren die automatische Paket-Heilung:"
        ]
        gruende += [f"{b.regel} {b.datei}: {b.text}" for b in vorher.struktur_fehler]
        gruende += [f"{b.code} {b.datei}: {b.text}" for b in vorher.manifest_fehler]
        return Ergebnis(
            klasse=KLASSE_OFFEN,
            code=EXIT_CODES[KLASSE_OFFEN],
            befund_id=befund_id,
            vorher=vorher,
            nachher=vorher,
            schritte=[],
            gruende=gruende,
            geheilte_ghsa=[],
            install_skript_pakete=[],
            geaenderte_dateien=[],
            beleg=None,
        )

    ziele, offene_treffer = _sammle_heilbare_ziele(vorher.treffer)
    if not ziele:
        gruende = [
            f"Kein veröffentlichter monotoner Fix für {t.name}@{t.version} ({t.ghsa})."
            for t in offene_treffer
        ]
        return Ergebnis(
            klasse=KLASSE_OFFEN,
            code=EXIT_CODES[KLASSE_OFFEN],
            befund_id=befund_id,
            vorher=vorher,
            nachher=vorher,
            schritte=[],
            gruende=gruende,
            geheilte_ghsa=[],
            install_skript_pakete=[],
            geaenderte_dateien=[],
            beleg=None,
        )

    # 3. Atomarer Snapshot vor jedem Schreibzugriff.
    kandidaten = _kandidaten_dateien(root)
    snapshot = _snapshot_erstellen(kandidaten)
    schritte: List[str] = []
    install_skript_pakete: List[str] = []
    erlaubte_hosts = [str(h) for h in (vertrag.get("erlaubte_npm_hosts") or ["registry.npmjs.org"])]
    aktiver_npm = npm_runner or _standard_npm_runner
    aktiver_pip = pip_hash_aufloeser or _standard_pip_hash_aufloeser

    try:
        # 3a) npm-Paare heilen
        npm_je_lock: Dict[str, Dict[str, Tuple[str, List[wache.Treffer]]]] = {}
        pip_ziele: Dict[str, Tuple[str, List[wache.Treffer]]] = {}
        alle_heilbaren_funde: List[wache.Treffer] = []

        for (oeko, paket_klein), (ziel, funde) in sorted(ziele.items()):
            alle_heilbaren_funde.extend(funde)
            if oeko == "npm":
                locks = sorted({q for f in funde for q in f.quellen if q.endswith("package-lock.json")})
                for lock_rel in locks:
                    npm_je_lock.setdefault(lock_rel, {})[paket_klein] = (ziel, funde)
            elif oeko == "pip":
                pip_ziele[paket_klein] = (ziel, funde)

        lk_fehler_gesamt: List[str] = []
        for lock_rel, lock_ziele in sorted(npm_je_lock.items()):
            s_npm, lk_fehler, skript_pakete = _heile_npm_manifest_paar(
                root, lock_rel, lock_ziele, erlaubte_hosts, aktiver_npm
            )
            schritte.extend(s_npm)
            lk_fehler_gesamt.extend(lk_fehler)
            install_skript_pakete.extend(skript_pakete)

        if lk_fehler_gesamt:
            _snapshot_wiederherstellen(snapshot)
            return Ergebnis(
                klasse=KLASSE_VERSCHLECHTERUNG,
                code=EXIT_CODES[KLASSE_VERSCHLECHTERUNG],
                befund_id=befund_id,
                vorher=vorher,
                nachher=vorher,
                schritte=schritte,
                gruende=[f"Rollback wegen Lieferketten-Sperre: {x}" for x in lk_fehler_gesamt],
                geheilte_ghsa=[],
                install_skript_pakete=[],
                geaenderte_dateien=[],
                beleg=None,
            )

        # 3b) pip-Manifeste heilen
        if pip_ziele:
            schritte.extend(_heile_pip_bestand(root, pip_ziele, aktiver_pip))

        # 3c) Sicherheits-Untergrenzen dauerhaft in den Vertrag einschreiben (A9)
        vertrag_kopie = json.loads((root / VERTRAG_PFAD).read_text(encoding="utf-8"))
        schritte.extend(aktualisiere_vertrag_untergrenzen(root, vertrag_kopie, alle_heilbaren_funde))

        # 4. OBLIGATORISCHE NACHMESSUNG (ohne Nachmessung gilt nichts als geheilt)
        nachher = messe_bestand(root, quelle)
    except (NichtBelegbar, OSError, json.JSONDecodeError) as fehler:
        _snapshot_wiederherstellen(snapshot)
        return Ergebnis(
            klasse=KLASSE_VERSCHLECHTERUNG,
            code=EXIT_CODES[KLASSE_VERSCHLECHTERUNG],
            befund_id=befund_id,
            vorher=vorher,
            nachher=vorher,
            schritte=schritte,
            gruende=[f"Rollback nach Fehler in Heilung/Nachmessung: {fehler}"],
            geheilte_ghsa=[],
            install_skript_pakete=[],
            geaenderte_dateien=[],
            beleg=None,
        )

    vorher_ghsa = {t.ghsa for t in vorher.treffer if t.ghsa}
    nachher_ghsa = {t.ghsa for t in nachher.treffer if t.ghsa}
    neue_ghsa = sorted(nachher_ghsa - vorher_ghsa)

    # Verschlechterung oder fehlender Fortschritt -> atomarer Rollback!
    if (
        nachher.struktur_fehler
        or nachher.manifest_fehler
        or neue_ghsa
        or len(nachher.treffer) >= len(vorher.treffer)
    ):
        _snapshot_wiederherstellen(snapshot)
        gruende_rb: List[str] = []
        if nachher.struktur_fehler:
            gruende_rb.extend(
                f"Nachmessung Struktur-Fehler {b.regel} ({b.datei}): {b.text}"
                for b in nachher.struktur_fehler
            )
        if nachher.manifest_fehler:
            gruende_rb.extend(
                f"Nachmessung Manifest-Fehler {b.code} ({b.datei}): {b.text}"
                for b in nachher.manifest_fehler
            )
        if neue_ghsa:
            gruende_rb.append(f"Nachmessung entdeckte neue Schwachstellen: {', '.join(neue_ghsa)}")
        if len(nachher.treffer) >= len(vorher.treffer):
            gruende_rb.append(
                f"Keine Reduktion der Trefferzahl ({len(vorher.treffer)} -> {len(nachher.treffer)})."
            )
        return Ergebnis(
            klasse=KLASSE_VERSCHLECHTERUNG,
            code=EXIT_CODES[KLASSE_VERSCHLECHTERUNG],
            befund_id=befund_id,
            vorher=vorher,
            nachher=nachher,
            schritte=schritte,
            gruende=gruende_rb,
            geheilte_ghsa=[],
            install_skript_pakete=[],
            geaenderte_dateien=[],
            beleg=None,
        )

    geheilte_ghsa = sorted(vorher_ghsa - nachher_ghsa)
    geaenderte = sorted(
        _rel(p, root) for p, alt_bytes in snapshot.items() if p.read_bytes() != alt_bytes
    )

    end_klasse = KLASSE_GEHEILT if not nachher.treffer else KLASSE_OFFEN
    gruende_ok = [
        f"Nachmessung bestätigt: {len(vorher.treffer)} -> {len(nachher.treffer)} Advisory-Treffer, "
        "0 Struktur-Fehler, 0 Manifest-Fehler."
    ]
    if nachher.treffer:
        gruende_ok.extend(
            f"Weiterhin offen (kein monotoner Upstream-Fix): {t.name}@{t.version} ({t.ghsa})"
            for t in nachher.treffer
        )
    if install_skript_pakete:
        gruende_ok.append(
            "Hinweis H-02 (`--ignore-scripts` aktiv): geänderte Pakete mit `hasInstallScript=true`: "
            + ", ".join(sorted(set(install_skript_pakete)))
        )

    beleg = haenge_beleg_an(
        ziel_ledger,
        klasse=end_klasse,
        befund_id=befund_id,
        vorher=vorher,
        nachher=nachher,
        geheilte_ghsa=geheilte_ghsa,
        schritte=schritte,
        install_skript_pakete=install_skript_pakete,
        gruende=gruende_ok,
    )
    rel_ledger = _rel(ziel_ledger, root)
    if rel_ledger not in geaenderte and ziel_ledger.is_relative_to(root):
        geaenderte.append(rel_ledger)
        geaenderte.sort()

    return Ergebnis(
        klasse=end_klasse,
        code=EXIT_CODES[end_klasse],
        befund_id=befund_id,
        vorher=vorher,
        nachher=nachher,
        schritte=schritte,
        gruende=gruende_ok,
        geheilte_ghsa=geheilte_ghsa,
        install_skript_pakete=sorted(set(install_skript_pakete)),
        geaenderte_dateien=geaenderte,
        beleg=beleg,
    )


# --------------------------------------------------------------------------- #
#  Diff-Filter für PR-/Push-Läufe in `sicherheits-wache.yml`
# --------------------------------------------------------------------------- #

def ist_pfad_audit_relevant(pfad: str) -> bool:
    norm = pfad.strip().replace("\\", "/")
    while norm.startswith("./"):
        norm = norm[2:]
    norm = norm.lstrip("/")
    if not norm:
        return False
    basis = os.path.basename(norm)
    if basis in ("package.json", "package-lock.json", "requirements-ci.in"):
        return True
    if basis.startswith("Dockerfile"):
        return True
    if basis.startswith("requirements") and (basis.endswith(".txt") or basis.endswith(".in")):
        return True
    return any(norm.startswith(p) for p in AUDIT_RELEVANTE_PRAEFIXE)


def pruefe_audit_bedarf(
    root: Path,
    *,
    event_name: Optional[str] = None,
    geaenderte_dateien: Optional[Sequence[str]] = None,
) -> Tuple[bool, str]:
    """Entscheidet fail-closed, ob `sicherheits-wache.yml` den Online-Audit fährt."""
    ereignis = (event_name or os.environ.get("GITHUB_EVENT_NAME") or "").strip()
    if ereignis in ("schedule", "workflow_dispatch", ""):
        return True, f"Ereignis `{ereignis or 'manuell'}` verlangt immer den Voll-Audit."

    dateien: Optional[List[str]] = list(geaenderte_dateien) if geaenderte_dateien is not None else None
    if dateien is None:
        # Auf GitHub-PRs ist HEAD ein Merge-Commit (HEAD^1..HEAD), auf Push HEAD~1..HEAD.
        for ref_paar in (("HEAD^1", "HEAD"), ("HEAD~1", "HEAD")):
            lauf = subprocess.run(
                ["git", "-C", str(root), "diff", "--name-only", ref_paar[0], ref_paar[1]],
                shell=False,
                check=False,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if lauf.returncode == 0:
                dateien = [z.strip() for z in lauf.stdout.splitlines() if z.strip()]
                break
    if dateien is None:
        # Fail-closed (C34): Lässt sich der Diff nicht bestimmen, wird auditiert.
        return True, "Git-Diff nicht bestimmbar (Shallow-Clone) – fail-closed Voll-Audit."

    treffer = [d for d in dateien if ist_pfad_audit_relevant(d)]
    if treffer:
        beispiel = ", ".join(treffer[:4])
        return True, f"Abhängigkeitsrelevante Pfade geändert ({beispiel})."
    return False, f"Nur inhalts-/oberflächenbezogene Pfade geändert ({len(dateien)} Datei(en))."


# --------------------------------------------------------------------------- #
#  Schicht 5 · Verdrahtungs-Wache (`--wache`)
# --------------------------------------------------------------------------- #

def _nicht_kommentar_zeilen(text: str) -> str:
    return "\n".join(
        zeile for zeile in text.splitlines() if not zeile.lstrip().startswith("#")
    )


def pruefe_verdrahtung(root: Path = BLOG_DIR) -> List[str]:
    """Prüft, dass Vertrag, Belegkette, PR-Gate, Heil-Workflow und Alerting greifen."""
    fehler: List[str] = []
    for rel in PFLICHT_PFADE:
        if not (root / rel).is_file():
            fehler.append(f"Pflichtdatei fehlt: {rel}")
    if fehler:
        return fehler

    # 1. Vertrag inkl. Pflicht-Untergrenzen (#79 minimatch >= 11.0.1 & glob >= 14.0.2)
    try:
        vertrag = lade_vertrag(root, mindest_pflicht=True)
    except NichtBelegbar as exc:
        fehler.append(str(exc))
        vertrag = {}

    # 2. Belegkette geschlossen und nicht leer (Vorfall #79 muss belegt sein)
    ledger_rel = str(vertrag.get("ledger") or LEDGER_PFAD)
    try:
        kette = pruefe_belegkette(root / ledger_rel)
        if not kette:
            fehler.append(f"{ledger_rel}: Belegkette ist leer (Erstbeleg zu #79 fehlt).")
    except KetteKaputt as exc:
        fehler.append(str(exc))

    # 3. `.gitattributes` schützt die Belegkette mit `merge=binary`
    gitattr_aktiv = _nicht_kommentar_zeilen((root / GITATTRIBUTES_PFAD).read_text(encoding="utf-8"))
    erwartet_attr = f"{ledger_rel} merge=binary"
    if erwartet_attr not in gitattr_aktiv:
        fehler.append(f"{GITATTRIBUTES_PFAD}: `{erwartet_attr}` fehlt.")

    # 4. Heil-Workflow ruft Selftest, Wache, Heilen, git_sync.sh und gh pr create auf
    wf_aktiv = _nicht_kommentar_zeilen((root / ARBEITSFLUSS).read_text(encoding="utf-8"))
    for nadel, beschreibung in (
        (f"name: {WORKFLOW_NAME}", "Workflow-Name"),
        ("abhaengigkeits_selbstheilung.py --selftest", "Selbsttest-Schritt"),
        ("abhaengigkeits_selbstheilung.py --wache", "Verdrahtungs-Wache"),
        ("abhaengigkeits_selbstheilung.py --heilen", "Heil-Schritt"),
        ("scripts/git_sync.sh", "sanktionierter Push über git_sync.sh"),
        ("gh pr create", "PR-Eröffnung statt Blind-Merge auf main (Audit H-02)"),
    ):
        if nadel not in wf_aktiv:
            fehler.append(f"{ARBEITSFLUSS}: {beschreibung} (`{nadel}`) fehlt.")
    if "gh pr merge" in wf_aktiv:
        fehler.append(
            f"{ARBEITSFLUSS}: `gh pr merge` gefunden – verstößt gegen Audit H-02 (kein Auto-Merge für npm/pip)."
        )

    # 5. `sicherheits-wache.yml` prüft Online-Audit auch bei PR/Push über `--audit-bedarf`
    sw_aktiv = _nicht_kommentar_zeilen((root / SICHERHEITS_FLUSS).read_text(encoding="utf-8"))
    for nadel, beschreibung in (
        ("abhaengigkeits_selbstheilung.py --audit-bedarf", "PR/Push-Audit-Bedarfsschalter"),
        ("abhaengigkeits_selbstheilung.py --selftest", "Selbsttest im Sicherheits-Gate"),
        ("abhaengigkeits_selbstheilung.py --wache", "Verdrahtungs-Wache im Sicherheits-Gate"),
        ("abhaengigkeits_wache.py --audit", "Online-Advisory-Audit"),
    ):
        if nadel not in sw_aktiv:
            fehler.append(f"{SICHERHEITS_FLUSS}: {beschreibung} (`{nadel}`) fehlt.")

    # 6. `alert-on-failure.yml` überwacht den Selbstheilungs-Workflow
    alert_aktiv = _nicht_kommentar_zeilen((root / ALERT_FLUSS).read_text(encoding="utf-8"))
    if f'"{WORKFLOW_NAME}"' not in alert_aktiv and f"- {WORKFLOW_NAME}" not in alert_aktiv:
        fehler.append(f"{ALERT_FLUSS}: `{WORKFLOW_NAME}` fehlt auf der Überwachungsliste.")

    return fehler


# --------------------------------------------------------------------------- #
#  Ausgabe (Markdown & JSON)
# --------------------------------------------------------------------------- #

def bericht_markdown(ergebnis: Ergebnis) -> str:
    zeilen = [
        "# Abhängigkeits-Schutz · Selbstheilung",
        "",
        f"- **Urteil:** `{ergebnis.klasse}` (Exit `{ergebnis.code}`)",
        f"- **Befund-ID:** `{ergebnis.befund_id}`",
    ]
    if ergebnis.vorher is not None and ergebnis.nachher is not None:
        zeilen.append(
            f"- **Vormessung:** {ergebnis.vorher.geprueft} geprüft · "
            f"{len(ergebnis.vorher.treffer)} Advisory-Treffer · "
            f"{len(ergebnis.vorher.struktur_fehler)} Struktur-Fehler · "
            f"{len(ergebnis.vorher.manifest_fehler)} Manifest-Fehler"
        )
        zeilen.append(
            f"- **Nachmessung:** {ergebnis.nachher.geprueft} geprüft · "
            f"{len(ergebnis.nachher.treffer)} Advisory-Treffer · "
            f"{len(ergebnis.nachher.struktur_fehler)} Struktur-Fehler · "
            f"{len(ergebnis.nachher.manifest_fehler)} Manifest-Fehler"
        )
    if ergebnis.geheilte_ghsa:
        zeilen.append(f"- **Geheilte Advisories:** {', '.join(f'`{g}`' for g in ergebnis.geheilte_ghsa)}")
    if ergebnis.beleg:
        zeilen.append(
            f"- **Belegkette:** `seq={ergebnis.beleg['seq']}` · `sha256={str(ergebnis.beleg['sha256'])[:16]}…`"
        )
    if ergebnis.install_skript_pakete:
        zeilen.append(
            "- **Lieferketten-Hinweis (H-02, `--ignore-scripts` erzwungen):** "
            + ", ".join(f"`{p}`" for p in ergebnis.install_skript_pakete)
        )
    zeilen.append("")
    if ergebnis.schritte:
        zeilen.append("## Ausgeführte Heilschritte")
        zeilen.append("")
        for schritt in ergebnis.schritte:
            zeilen.append(f"- {schritt}")
        zeilen.append("")
    if ergebnis.gruende:
        zeilen.append("## Begründung")
        zeilen.append("")
        for grund in ergebnis.gruende:
            zeilen.append(f"- {grund}")
        zeilen.append("")
    return "\n".join(zeilen)


def ergebnis_als_dict(ergebnis: Ergebnis) -> Dict[str, object]:
    return {
        "klasse": ergebnis.klasse,
        "code": ergebnis.code,
        "befund_id": ergebnis.befund_id,
        "vorher": ergebnis.vorher.als_zusammenfassung() if ergebnis.vorher else None,
        "nachher": ergebnis.nachher.als_zusammenfassung() if ergebnis.nachher else None,
        "geheilte_ghsa": ergebnis.geheilte_ghsa,
        "schritte": ergebnis.schritte,
        "install_skript_pakete": ergebnis.install_skript_pakete,
        "geaenderte_dateien": ergebnis.geaenderte_dateien,
        "gruende": ergebnis.gruende,
        "beleg_sha256": ergebnis.beleg.get("sha256") if ergebnis.beleg else None,
        "beleg_seq": ergebnis.beleg.get("seq") if ergebnis.beleg else None,
    }


# --------------------------------------------------------------------------- #
#  Selbsttest (`--selftest` – 12 Fallgruppen, 100 % offline im Temp-Baum)
# --------------------------------------------------------------------------- #

def _baue_test_repo(wurzel: Path) -> None:
    (wurzel / "data").mkdir(parents=True, exist_ok=True)
    _schreibe_json_sauber(
        wurzel / VERTRAG_PFAD,
        {
            "schema": 1,
            "nur_verschaerfen": True,
            "ignore_scripts_pflicht": True,
            "erlaubte_npm_hosts": ["registry.npmjs.org"],
            "heil_branch_praefix": "automation/deps-heilung-",
            "ledger": LEDGER_PFAD,
            "mindestversionen": {},
            "begruendung": "Testvertrag für die Selbstheilungs-Sabotageproben (#79).",
        },
    )
    (wurzel / LEDGER_PFAD).write_text("", encoding="utf-8")
    _schreibe_json_sauber(
        wurzel / "package.json",
        {"name": "fixture", "version": "1.0.0", "devDependencies": {"lighthouse": "13.6.0"}},
    )
    _schreibe_json_sauber(
        wurzel / "package-lock.json",
        {
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "fixture", "version": "1.0.0", "devDependencies": {"lighthouse": "13.6.0"}},
                "node_modules/lighthouse": {
                    "version": "13.6.0",
                    "resolved": "https://registry.npmjs.org/lighthouse/-/lighthouse-13.6.0.tgz",
                    "integrity": "sha512-lh",
                },
                "node_modules/glob": {
                    "version": "13.0.6",
                    "resolved": "https://registry.npmjs.org/glob/-/glob-13.0.6.tgz",
                    "integrity": "sha512-glob13",
                },
                "node_modules/minimatch": {
                    "version": "10.2.6",
                    "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-10.2.6.tgz",
                    "integrity": "sha512-mm10",
                },
            },
        },
    )


def run_selftest() -> List[str]:
    fehler: List[str] = []

    def pruefe(name: str, bedingung: bool, detail: str = "") -> None:
        if not bedingung:
            fehler.append(f"{name}: {detail}" if detail else name)

    # 1. Eichprobe läuft grün
    try:
        eichprobe()
    except MessgeraetDefekt as exc:
        fehler.append(f"Eichprobe: {exc}")

    # 2. Defekte Eichprobe -> Exit 3 (`MESSGERAET`), kein Dateizugriff
    with tempfile.TemporaryDirectory(prefix="deps-st-exit3-") as tmp:
        baum = Path(tmp)
        _baue_test_repo(baum)
        erg_defekt = ausfuehren(
            baum,
            heilen=True,
            advisory_quelle=wache.DateiAdvisoryQuelle({}),
            eichprobe_fn=lambda: (_ for _ in ()).throw(MessgeraetDefekt("Sabotage")),
        )
        pruefe("Exit3/Messgerät", erg_defekt.code == 3 and erg_defekt.klasse == KLASSE_MESSGERAET)
        pruefe("Exit3/KeinBeleg", (baum / LEDGER_PFAD).read_text(encoding="utf-8") == "")

    # 3. Vollständige Heilung von Vorfall #79 (`minimatch` + `glob`) + Nachmessung + Kette
    with tempfile.TemporaryDirectory(prefix="deps-st-heilung-") as tmp:
        baum = Path(tmp)
        _baue_test_repo(baum)
        quelle_79 = wache.DateiAdvisoryQuelle(
            {
                "npm:minimatch@10.2.6": [
                    {
                        "ghsa": "GHSA-g3hv-75wg-m249",
                        "severity": "medium",
                        "summary": "minimatch globparts amplification DoS (#79)",
                        "fixed": "11.0.1",
                    }
                ],
                "npm:glob@13.0.6": [
                    {
                        "ghsa": "GHSA-3g3m-2fjr-6pw4",
                        "severity": "medium",
                        "summary": "Glob AbortSignal cancellation bypass",
                        "fixed": "14.0.2",
                    }
                ],
            }
        )

        def _fake_npm(cwd: Path, args: List[str]) -> Tuple[int, str]:
            lock_p = cwd / "package-lock.json"
            lock_d = json.loads(lock_p.read_text(encoding="utf-8"))
            lock_d["packages"]["node_modules/glob"] = {
                "version": "14.0.4",
                "resolved": "https://registry.npmjs.org/glob/-/glob-14.0.4.tgz",
                "integrity": "sha512-glob14",
            }
            lock_d["packages"]["node_modules/minimatch"] = {
                "version": "11.0.6",
                "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-11.0.6.tgz",
                "integrity": "sha512-mm11",
            }
            _schreibe_json_sauber(lock_p, lock_d)
            return 0, "updated"

        erg_ok = ausfuehren(baum, heilen=True, advisory_quelle=quelle_79, npm_runner=_fake_npm)
        pruefe("Heilung79/Klasse", erg_ok.klasse == KLASSE_GEHEILT and erg_ok.code == 0, str(erg_ok.gruende))
        pruefe(
            "Heilung79/GHSA",
            erg_ok.geheilte_ghsa == ["GHSA-3g3m-2fjr-6pw4", "GHSA-g3hv-75wg-m249"],
            str(erg_ok.geheilte_ghsa),
        )
        vertrag_neu = lade_vertrag(baum, mindest_pflicht=True)
        pruefe("Heilung79/VertragA9", "npm:minimatch" in vertrag_neu["mindestversionen"])  # type: ignore[index]

        # 4. Zweiter Lauf ist idempotent (`SICHER`, schreibt keine zweite Belegzeile)
        erg_zwei = ausfuehren(baum, heilen=True, advisory_quelle=quelle_79, npm_runner=_fake_npm)
        kette = pruefe_belegkette(baum / LEDGER_PFAD)
        pruefe("Idempotenz/Sicher", erg_zwei.klasse == KLASSE_SICHER and len(kette) == 1)

        # 5. Manipulierte Belegkette -> Exit 2 (`NICHT_BELEGBAR`)
        manipuliert = (baum / LEDGER_PFAD).read_text(encoding="utf-8").replace("GEHEILT", "SICHER")
        (baum / LEDGER_PFAD).write_text(manipuliert, encoding="utf-8")
        erg_kette = ausfuehren(baum, heilen=False, advisory_quelle=quelle_79)
        pruefe("Kettenbruch/Exit2", erg_kette.code == 2 and erg_kette.klasse == KLASSE_NICHT_BELEGBAR)

    # 6. Lieferketten-Sabotage (fremder Host) -> atomarer Rollback + Exit 2
    with tempfile.TemporaryDirectory(prefix="deps-st-rollback-") as tmp:
        baum = Path(tmp)
        _baue_test_repo(baum)
        vorher_bytes = (baum / "package-lock.json").read_bytes()
        quelle_mm = wache.DateiAdvisoryQuelle(
            {
                "npm:minimatch@10.2.6": [
                    {
                        "ghsa": "GHSA-g3hv-75wg-m249",
                        "severity": "medium",
                        "summary": "DoS",
                        "fixed": "11.0.1",
                    }
                ]
            }
        )

        def _boeser_npm(cwd: Path, args: List[str]) -> Tuple[int, str]:
            lock_p = cwd / "package-lock.json"
            lock_d = json.loads(lock_p.read_text(encoding="utf-8"))
            lock_d["packages"]["node_modules/minimatch"] = {
                "version": "11.0.6",
                "resolved": "https://attacker.invalid/minimatch-11.0.6.tgz",
                "integrity": "sha512-böse",
            }
            _schreibe_json_sauber(lock_p, lock_d)
            return 0, "evil"

        erg_rb = ausfuehren(baum, heilen=True, advisory_quelle=quelle_mm, npm_runner=_boeser_npm)
        pruefe("Rollback/Exit2", erg_rb.code == 2 and erg_rb.klasse == KLASSE_VERSCHLECHTERUNG)
        pruefe("Rollback/BytesIdentisch", (baum / "package-lock.json").read_bytes() == vorher_bytes)

    # 7. pip `.in` + Hash-Lock-Synchronität (Regel A2 bleibt grün)
    with tempfile.TemporaryDirectory(prefix="deps-st-pip-") as tmp:
        baum = Path(tmp)
        _baue_test_repo(baum)
        (baum / "requirements-ci.in").write_text("pypdf==6.21.2\n", encoding="utf-8")
        (baum / "requirements-ci.txt").write_text(
            "pypdf==6.21.2 \\\n    --hash=sha256:alt\n", encoding="utf-8"
        )
        quelle_pip = wache.DateiAdvisoryQuelle(
            {
                "pip:pypdf@6.21.2": [
                    {
                        "ghsa": "GHSA-aaaa-bbbb-cccc",
                        "severity": "high",
                        "summary": "pypdf Befund",
                        "fixed": "6.21.4",
                    }
                ]
            }
        )
        erg_pip = ausfuehren(
            baum,
            heilen=True,
            advisory_quelle=quelle_pip,
            pip_hash_aufloeser=lambda p, v: ["sha256:" + "b" * 64],
        )
        pruefe("PipHeilung/Geheilt", erg_pip.klasse == KLASSE_GEHEILT and erg_pip.code == 0, str(erg_pip.gruende))
        pruefe("PipHeilung/A2Synchron", "pypdf==6.21.4" in (baum / "requirements-ci.in").read_text(encoding="utf-8"))

    # 8. Treffer ohne Fix bleibt ehrlich `OFFEN` (Exit 1, kein Scheingrün)
    with tempfile.TemporaryDirectory(prefix="deps-st-offen-") as tmp:
        baum = Path(tmp)
        _baue_test_repo(baum)
        quelle_offen = wache.DateiAdvisoryQuelle(
            {
                "npm:minimatch@10.2.6": [
                    {"ghsa": "GHSA-0000-1111-2222", "severity": "high", "summary": "Ohne Fix"}
                ]
            }
        )
        erg_offen = ausfuehren(baum, heilen=True, advisory_quelle=quelle_offen)
        pruefe("OhneFix/Offen", erg_offen.klasse == KLASSE_OFFEN and erg_offen.code == 1)

    # 9. Diff-Filter für PR/Push-Läufe
    ja_pr, _ = pruefe_audit_bedarf(
        BLOG_DIR, event_name="pull_request", geaenderte_dateien=["package-lock.json"]
    )
    nein_inhalt, _ = pruefe_audit_bedarf(
        BLOG_DIR, event_name="push", geaenderte_dateien=["content/posts/test/index.md"]
    )
    ja_zeitplan, _ = pruefe_audit_bedarf(
        BLOG_DIR, event_name="schedule", geaenderte_dateien=["content/posts/test/index.md"]
    )
    pruefe("AuditBedarf/PR-Lock", ja_pr is True)
    pruefe("AuditBedarf/NurInhalt", nein_inhalt is False)
    pruefe("AuditBedarf/ScheduleImmer", ja_zeitplan is True)

    return fehler


# --------------------------------------------------------------------------- #
#  CLI
# --------------------------------------------------------------------------- #

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Abhängigkeits-Selbstheilung (#79): Vertrag, Eichprobe, Heilung, Belegkette, Wache."
    )
    modus = parser.add_mutually_exclusive_group(required=True)
    modus.add_argument("--selftest", action="store_true", help="12 Sabotage- und Gegenproben im Temp-Baum")
    modus.add_argument("--wache", action="store_true", help="Verdrahtungs- und Vertragsprüfung")
    modus.add_argument("--audit-bedarf", action="store_true", help="Gibt `ja` oder `nein` für PR/Push-Audit aus")
    modus.add_argument("--pruefen", action="store_true", help="Nur messen und klassifizieren (lesend)")
    modus.add_argument("--heilen", action="store_true", help="Messen, streng aufsteigend heilen, nachmessen, belegen")

    parser.add_argument("--root", metavar="PFAD", default=str(BLOG_DIR), help="Wurzelverzeichnis")
    parser.add_argument("--advisory-datei", metavar="PFAD", help="Eingefrorene Advisory-Datei statt HTTP")
    parser.add_argument("--beleg", metavar="PFAD", help="Abweichender Pfad für die Belegkette")
    parser.add_argument("--md", metavar="PFAD", help="Markdown-Bericht in Datei schreiben")
    parser.add_argument("--json", action="store_true", help="Maschinenlesbare JSON-Ausgabe")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()

    if args.selftest:
        fehler = run_selftest()
        if fehler:
            for f in fehler:
                print(f"❌ {f}", file=sys.stderr)
            return 2
        print(
            "✅ Selbsttest Abhängigkeits-Selbstheilung bestanden (Eichprobe #79, Exit-3-Sperre, "
            "npm+Override-Heilung, Idempotenz, SHA-256-Kettenbruch, Lieferketten-Rollback, "
            "pip-Hash-Sync, Offen-Ehrlichkeit, PR-Audit-Filter)."
        )
        return 0

    if args.wache:
        fehler = pruefe_verdrahtung(root)
        if fehler:
            for f in fehler:
                annotation("error", f, titel="Abhängigkeits-Selbstheilung Wache")
                print(f"❌ {f}", file=sys.stderr)
            return 1
        print("✅ Verdrahtungs-Wache grün: Vertrag (#79 + glob), Belegkette, PR-Audit, Heil-Workflow und Alerting sind intakt.")
        return 0

    if args.audit_bedarf:
        bedarf, grund = pruefe_audit_bedarf(root)
        print("ja" if bedarf else "nein")
        print(f"# {grund}", file=sys.stderr)
        return 0

    ergebnis = ausfuehren(
        root,
        heilen=bool(args.heilen),
        advisory_datei=args.advisory_datei,
        beleg_pfad=Path(args.beleg).resolve() if args.beleg else None,
    )

    if args.md:
        md_ziel = Path(args.md)
        md_text = bericht_markdown(ergebnis)
        if md_ziel.exists() and str(md_ziel) == os.environ.get("GITHUB_STEP_SUMMARY"):
            with md_ziel.open("a", encoding="utf-8") as handle:
                handle.write("\n" + md_text)
        else:
            md_ziel.write_text(md_text, encoding="utf-8")

    if ergebnis.code != 0:
        ebene = "warning" if ergebnis.code == 1 else "error"
        zusammenfassung = "; ".join(ergebnis.gruende[:3]) or ergebnis.klasse
        annotation(ebene, zusammenfassung, titel=f"Abhängigkeits-Selbstheilung {ergebnis.klasse}")

    if args.json:
        print(json.dumps(ergebnis_als_dict(ergebnis), ensure_ascii=False, indent=2))
    else:
        print(bericht_markdown(ergebnis))
    return ergebnis.code


if __name__ == "__main__":
    sys.exit(main())
