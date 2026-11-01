#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""skills_vertrag.py – der Kern hat ein Budget, jeder Skill einen Nachweis.

WARUM DIESES WERKZEUG EXISTIERT (01.11.2026)
-------------------------------------------
Am 01.11.2026 las JEDER Agent beim Start 2.532 Zeilen / 158 KB Regelwerk
(`CLAUDE.md`) – Details über Backup-Wachen, Snippet-Pixel und
Reserve-Löschrechte inklusive. Das ist kein Dokument, das ist eine Steuer:
rund 40.000 Tokens vor dem ersten Auftrag, und ein Teil davon veraltet, weil
niemand 67 Abschnitte gegen den Code prüft.

Der Umbau legt die Details in repo-eigene Skills (`.claude/skills/ff-*`).
Ohne Wache wäre das eine Verschiebung auf Zeit: Regelwerke wachsen zurück an
die erste Stelle, Verweise veralten lautlos, vendored Fremd-Skills stehen ohne
Lizenz im Repo, und ein `ff-*`-Skill, den `npx skills update` überschreibt,
verliert ungezählt Regelwerk. Genau diese Klasse hat dieser Repo schon
anderweitig geheilt – ein Schritt ohne Erzeuger, eine Wache ohne Fahrer, ein
Report ohne Messquelle.

PRÜFUNGEN
  K1  Budget: `CLAUDE.md` ≤ 420 Zeilen und ≤ 32 KB; jeder `ff-*/SKILL.md` ≤ 200
      Zeilen (das Entry hält den Auftrag, das Detail liegt in `references/`).
  K2  Form: jeder Skill hat `SKILL.md` mit Frontmatter; `name` == Ordnername,
      kleinschreibig mit Bindestrichen, ≤ 64 Zeichen; `description` 80–1024
      Zeichen (1.024 ist die harte Obergrenze der Skill-Validierung).
  K3  Erreichbarkeit: jeder `ff-*`-Skill steht im Router des Kerns; jede
      `references/*.md` ist im Skill verlinkt, und jede verlinkte Datei existiert.
      Eine ungelesene Regel ist eine abgeschaffte Regel.
  K4  Herkunft: jeder vendored Skill steht in `skills-lock.json` und umgekehrt;
      kein `ff-*` darf dort stehen (der Lock gehört `npx skills`).
  K5  Befehle in Code-Zäunen sind ausführbar: jedes `npm run …` aus
      `package.json`, jeder `scripts/*.py`- und `*.mjs`-Pfad vorhanden, jede
      Flagge im Zieltext lesbar. Vorlagen mit `<…>` bleiben ausgenommen.
  K6  Lizenz: `data/skill_lizenzen.json` deckt jeden vendored Skill ab, der
      Lizenztext liegt neben dem `SKILL.md`; Apache-2.0 verlangt zusätzlich
      die NOTICE. „unbekannt“ nur mit Ausnahme (grund + entscheidung + faellig);
      eine abgelaufene Frist ist eine Warnung im Bericht, nie ein Exit-Code.
  K7  Verweise ins Regelwerk lösen auf: `CLAUDE.md §N` / „Regel N“ zeigt auf
      ein existierendes nummeriertes Gebot, „Abschnitt X“ auf eine Überschrift
      in `CLAUDE.md` oder einem Skill.
  K8  Siegelstand: das Integritätsschloss (`data/integrity_lock.json`) muss den
      Regelkern der Skills mittragen – Wache und Lizenz-Register entscheiden
      über den Bestand, das sind keine Notizen. Gelesen wird, was `scripts/integrity_guard.py` als
      KRITISCH/FEST führt. Immer eine Warnung mit Schlusszeile, nie ein Befund:
      Zeichnen ist ein Betreiberakt, und ein Gate, das dafür rot wird, bestraft
      die falsche Seite (Issue #316 – der HARD STOP traf die Content-Engine).
  K9  Beschreibungs-Budget: die Summe aller `description`-Zeichen liegt unter
      `BESCHREIBUNG_KB_MAX`. Jede Beschreibung steht dauerhaft im Kontext jeder
      Session; 53 nachgeladene Fremd-Skills sind eine Entscheidung über rund
      12.000 Tokens, nicht über 53 Dateien.
  K10 Herkunft der Zusatzdateien: liegt in einem Fremd-Ordner eine `*-de.md`,
      `evals-de.json` oder `SKILL_DE.md`, die nicht im Lock steht, ist sie
      repo-eigen – und der nächste `npx skills update` löscht sie still. Am
      01.11.2026 so geschehen mit der deutschen `copy-editing`-Ausgabe.

Aufruf:
  python3 scripts/skills_vertrag.py                  # prüfen (Befund = Exit 1)
  python3 scripts/skills_vertrag.py --md             # Markdown für die Lauf-Summary
  python3 scripts/skills_vertrag.py --json           # maschinenlesbar
  python3 scripts/skills_vertrag.py --selftest       # Sabotage-Schutz, offline

Exit: 0 = sauber · 1 = Befund · 2 = Hausfehler (unlesbare Quelle, Selbsttest)
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from collections import namedtuple
from datetime import date
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent

KERN = "CLAUDE.md"
SKILL_ORDNER = Path(".claude/skills")
LOCK = "skills-lock.json"
LIZENZ_DATEI = Path("data/skill_lizenzen.json")

ZEILEN_MAX = 420
KB_MAX = 32.0
SKILL_ZEILEN_MAX = 200
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
DESC_MIN, DESC_MAX = 80, 1024
EIGEN_PRÄFIX = "ff-"
LIZENZ_MUSTER = ("LICENSE", "LICENCE", "COPYING")
SIEGEL_GUARD = Path("scripts/integrity_guard.py")
SIEGEL_LOCK = Path("data/integrity_lock.json")
# Wer diese zwei Dateien ändert, ändert die Regel – nicht nur ihren Text. Das
# Integritätsschloss soll den Austausch laut machen; geprüft wird das in K8.
SIEGEL_PFLICHT = ("scripts/skills_vertrag.py", "data/skill_lizenzen.json")
# Lizenzen, deren Text hier liegend nachgeprüft werden kann. Alles andere – auch
# eine im Upstream-Ordnerbehälter zu lesende Sonderklausel – braucht denselben
# Ausnahmekern wie „unbekannt“: Grund, Entscheidung, Frist.
FREIE_LIZENZEN = ("mit", "apache-2.0")
# Die Oberklasse aller Beschreibungen. Am 01.11.2026 lag der Bestand bei 75
# Skills × bis zu 1.024 Zeichen ≈ 14.000 Tokens Dauerlast in jeder Session –
# eine Bibliothek, die jeden Auftrag mitbezahlt. Das Budget ist der Grund,
# warum ein weiterer Schwung nur mit Entscheidung dazukommt (K9).
BESCHREIBUNG_KB_MAX = 56.0
# K10: Dateien, die im Fremd-Ordner bleiben dürfen, obwohl der CLI ihn beim
# nächsten `update` ersetzt. `SKILL_DE.md` ist die repo-eigene deutsche
# Ausgabe von `copy-editing` (SKILL_DE.md + evals-de.json + vier
# references/*-de.md, seit 21.09.2026). Am 01.11.2026 hat `npx skills update`
# sie gelöscht, ohne dass eine Wache etwas merkte – der Vertrag war grün.
NACHWEIS_DATEIEN = ("SKILL_DE.md",)
NACHWEIS_MUSTER = ("-de.md", "evals-de.json")
# Wo die umgezogenen Ergänzungen verzeichnet sind (K10).
ERGAENZUNGEN = Path("data/skill_ergaenzungen.json")

Fund = namedtuple("Fund", "klasse pfad stelle meldung")
Warn = namedtuple("Warn", "klasse pfad stelle meldung")


def kurz(self) -> str:  # Anzeigestil der übrigen Wachen: Klasse · Pfad · Stelle
    ort = f"{self.pfad}" + (f":{self.stelle}" if self.stelle else "")
    return f"[{self.klasse}] {ort} – {self.meldung}"


Fund.kurz = kurz  # type: ignore[attr-defined]
Warn.kurz = kurz  # type: ignore[attr-defined]


# ---------------------------------------------------------------- Lesen
def _text(root: Path, rel: str | Path) -> str | None:
    pfad = root / rel
    if not pfad.is_file():
        return None
    try:
        return pfad.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _zeilen(root: Path, rel: str | Path) -> list[str]:
    t = _text(root, rel)
    return t.split("\n") if t is not None else []


def frontmatter(zeilen: list[str]) -> dict[str, str]:
    """Frontmatter zeilenweise lesen – kein rückverfolgendes Muster über
    mehrere Zeilen (Kern-Regel 6). Unterstützt `key: wert`, `key: "…"`,
    `key: >`/`|` mit eingerücktem Block."""
    daten: dict[str, str] = {}
    if not zeilen or zeilen[0].strip() != "---":
        return daten
    key = None
    block: list[str] = []
    for roh in zeilen[1:]:
        if roh.strip() == "---":
            if key:
                daten[key] = " ".join(block).strip() if block else daten.get(key, "")
            break
        m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", roh)
        if m and not roh.startswith((" ", "\t")):
            if key:
                daten[key] = " ".join(block).strip() if block else daten.get(key, "")
            key, wert = m.group(1), m.group(2).strip()
            block = []
            if wert in (">", "|", ">-", "|-", ""):
                daten[key] = ""
            else:
                daten[key] = wert.strip().strip('"').strip("'")
                key = None
        elif key and (roh.startswith((" ", "\t")) or roh.strip() == ""):
            block.append(roh.strip())
        elif roh.strip() == "" and key:
            block.append("")
    return daten


def _nummerierte(zeilen: list[str]) -> dict[int, str]:
    """`1. **Text**`-Gebote eines Abschnitts, unabhängig vom Abschnitt."""
    out: dict[int, str] = {}
    for ln in zeilen:
        m = re.match(r"^([0-9]{1,2})\. \*\*(.+?)\*\*", ln)
        if m:
            out[int(m.group(1))] = m.group(2)
    return out


def _ueberschriften(root: Path) -> list[str]:
    """Alle Überschriften des Regelwerks: Kern plus alle Skills (Titel-Zeile
    und `#`-Überschriften, Code-Zäune übersprungen)."""
    titel: list[str] = []
    quellen = [Path(KERN)]
    quellen += sorted((root / SKILL_ORDNER).glob("*/*.md"))
    quellen += sorted((root / SKILL_ORDNER).glob("*/**/*.md"))
    seen: set[str] = set()
    for rel in quellen:
        if str(rel) in seen:
            continue
        seen.add(str(rel))
        fence = False
        for ln in _zeilen(root, rel):
            if ln.startswith("```"):
                fence = not fence
                continue
            if fence:
                continue
            m = re.match(r"^#{1,4} (.+)$", ln)
            if m:
                titel.append(m.group(1).strip())
    return titel


# ---------------------------------------------------------------- K1 Budget
def k1_budget(root: Path) -> list[Fund]:
    funde: list[Fund] = []
    zeilen = _zeilen(root, KERN)
    if not zeilen:
        return [Fund("K1", KERN, "", "Der Kern fehlt – ohne ihn kennt kein Agent die Regeln.")]
    anzahl = len(zeilen)
    kilo = len("\n".join(zeilen).encode("utf-8")) / 1024
    if anzahl > ZEILEN_MAX:
        funde.append(Fund("K1", KERN, "1", f"Kern-Budget gerissen: {anzahl} Zeilen "
                                           f"(erlaubt ≤ {ZEILEN_MAX}). Neue Details gehören in den "
                                           f"zuständigen Skill unter `{SKILL_ORDNER}/{EIGEN_PRÄFIX}…`, "
                                           "nicht in diese Datei."))
    if kilo > KB_MAX:
        funde.append(Fund("K1", KERN, "1", f"Kern-Budget gerissen: {kilo:.1f} KB "
                                           f"(erlaubt ≤ {KB_MAX:.0f} KB) – jeder Zeile dieses Textes "
                                           "liegt bei jedem Start aller Agenten."))
    for skill in sorted(p.parent.name for p in (root / SKILL_ORDNER).glob(f"{EIGEN_PRÄFIX}*/SKILL.md")):
        s_zeilen = _zeilen(root, SKILL_ORDNER / skill / "SKILL.md")
        if len(s_zeilen) > SKILL_ZEILEN_MAX:
            funde.append(Fund("K1", f"{SKILL_ORDNER}/{skill}/SKILL.md", str(len(s_zeilen)),
                              f"Skill-Einstieg ist {len(s_zeilen)} Zeilen lang "
                              f"(erlaubt ≤ {SKILL_ZEILEN_MAX}): Details gehören in `references/`, "
                              "sonst zahlt jeder Auftrag sie beim ersten Blick."))
    return funde


# ---------------------------------------------------------------- K2 Form
def k2_form(root: Path) -> list[Fund]:
    funde: list[Fund] = []
    ordner = root / SKILL_ORDNER
    if not ordner.is_dir():
        return [Fund("K2", str(SKILL_ORDNER), "", "Skill-Ordner fehlt.")]
    for d in sorted(p for p in ordner.iterdir() if p.is_dir()):
        rel = f"{SKILL_ORDNER}/{d.name}"
        skill_md = d / "SKILL.md"
        if not skill_md.is_file():
            funde.append(Fund("K2", rel, "", "kein SKILL.md – der Ordner ist kein Skill."))
            continue
        fm = frontmatter(_zeilen(root, f"{SKILL_ORDNER}/{d.name}/SKILL.md"))
        name = fm.get("name", "").strip()
        if not name:
            funde.append(Fund("K2", f"{rel}/SKILL.md", "2", "Frontmatter ohne `name:` – "
                                                            "der Skill wird nicht gefunden."))
        elif name != d.name:
            funde.append(Fund("K2", f"{rel}/SKILL.md", "2",
                              f"`name: {name}` passt nicht zum Ordner `{d.name}`."))
        elif len(name) > 64 or not NAME_RE.match(name):
            funde.append(Fund("K2", f"{rel}/SKILL.md", "2",
                              f"Name `{name}` verstößt gegen die Skill-Namensregel "
                              "(klein, Bindestriche, ≤ 64 Zeichen)."))
        desc = fm.get("description", "").strip()
        if not desc:
            funde.append(Fund("K2", f"{rel}/SKILL.md", "3", "keine `description:` – "
                                                             "kein Agent kann den Skill selbst auswählen."))
        else:
            if len(desc) > DESC_MAX:
                funde.append(Fund("K2", f"{rel}/SKILL.md", "3", f"Beschreibung ist "
                                  f"{len(desc)} Zeichen (hartes Limit der Skill-Validierung: "
                                  f"{DESC_MAX})."))
            if len(desc) < DESC_MIN and d.name.startswith(EIGEN_PRÄFIX):
                funde.append(Fund("K2", f"{rel}/SKILL.md", "3", f"Beschreibung ist {len(desc)} "
                                  "Zeichen – zu kurz für Auslöser, Verbote und Abgrenzung; "
                                  "die Auswahl des Skills ist die halbe Arbeit."))
            for verbot in ("<", "[think", "[INST]"):
                if verbot in desc:
                    funde.append(Fund("K2", f"{rel}/SKILL.md", "3",
                                      f"Beschreibung enthält `{verbot}` – Markup gehört nicht "
                                      "in die Auswahl-Texte."))
                    break
    return funde


# ---------------------------------------------------------------- K3 Erreichbarkeit
def k3_erreichbarkeit(root: Path) -> list[Fund]:
    funde: list[Fund] = []
    kern = "\n".join(_zeilen(root, KERN))
    ordner = root / SKILL_ORDNER
    if not ordner.is_dir():
        return funde
    for d in sorted(p for p in ordner.iterdir() if p.is_dir() and p.name.startswith(EIGEN_PRÄFIX)):
        rel = f"{SKILL_ORDNER}/{d.name}"
        if d.name not in kern:
            funde.append(Fund("K3", rel, "", f"`{d.name}` steht in keinem Router des Kerns – "
                                             "der Agent weiß nicht, wann er lesen soll, und lässt ihn an."))
        skill_md = _text(root, f"{rel}/SKILL.md") or ""
        for ref in sorted((d / "references").glob("*.md")) if (d / "references").is_dir() else []:
            if ref.name not in skill_md:
                funde.append(Fund("K3", f"{rel}/references/{ref.name}", "",
                                  "im SKILL.md nicht verlinkt – Details, die niemand adressiert, "
                                  "werden nie gelesen."))
        for m in re.findall(r"`?(references/[A-Za-z0-9_.-]+\.md)`?", skill_md):
            if not (d / m).is_file():
                funde.append(Fund("K3", f"{rel}/SKILL.md", "", f"verlinkt {m}, die Datei fehlt."))
    return funde


# ---------------------------------------------------------------- K4 Herkunft
def k4_herkunft(root: Path) -> tuple[list[Fund], list[Warn]]:
    funde: list[Fund] = []
    warnungen: list[Warn] = []
    lock_text = _text(root, LOCK)
    if lock_text is None:
        return [Fund("K4", LOCK, "", "fehlt – ohne Lock weiß niemand, woher ein vendored Skill kommt.")], warnungen
    try:
        lock = json.loads(lock_text)
    except json.JSONDecodeError as exc:
        return [Fund("K4", LOCK, str(exc.lineno or ""), f"ungültiges JSON: {exc.msg}")], warnungen
    eintraege = (lock or {}).get("skills") or {}
    ordner = root / SKILL_ORDNER
    installiert = {p.name for p in ordner.iterdir() if p.is_dir()} if ordner.is_dir() else set()
    eigene = {n for n in installiert if n.startswith(EIGEN_PRÄFIX)}
    for name in sorted(installiert - eigene):
        if name not in eintraege:
            funde.append(Fund("K4", f"{SKILL_ORDNER}/{name}", "",
                              "installiert, aber nicht in `skills-lock.json` – keine Herkunft, "
                              "kein Update-Pfad, kein Prüfsiegel auf dem Stand."))
    for name in sorted(eigene):
        if name in eintraege:
            funde.append(Fund("K4", LOCK, name, f"repo-eigener Skill im Lock – `npx skills update` "
                                                 "dürfte Regelwerk des Repos überschreiben."))
    for name, daten in sorted(eintraege.items()):
        if name not in installiert:
            warnungen.append(Warn("K4", LOCK, name, "im Lock geführt, aber nicht installiert – "
                                                     "der nächste `npx skills update` legt ihn neu an."))
            continue
        pfad = daten.get("skillPath") if isinstance(daten, dict) else None
        if not pfad:
            funde.append(Fund("K4", LOCK, name, "Eintrag ohne `skillPath`."))
    return funde, warnungen


# ---------------------------------------------------------------- K5 Befehle
def _zaeune(zeilen: list[str]) -> list[tuple[int, str]]:
    out: list[tuple[int, str]] = []
    drin = False
    for nr, ln in enumerate(zeilen, 1):
        if ln.lstrip().startswith("```"):
            drin = not drin
            continue
        if drin:
            out.append((nr, ln))
    return out


def _vorlage(wert: str) -> bool:
    return any(z in wert for z in ("<", ">", "…", "*", "$", "{"))


def k5_befehle(root: Path) -> list[Fund]:
    funde: list[Fund] = []
    skripte: dict[str, list[str]] = {}
    pkg = _text(root, "package.json")
    laufnamen: set[str] = set()
    if pkg:
        try:
            laufnamen = set((json.loads(pkg).get("scripts") or {}).keys())
        except json.JSONDecodeError as exc:
            return [Fund("K5", "package.json", str(exc.lineno or ""), f"ungültiges JSON: {exc.msg}")]
    quellen = [Path(KERN)]
    quellen += sorted((root / SKILL_ORDNER).glob(f"{EIGEN_PRÄFIX}*/*.md"))
    quellen += sorted((root / SKILL_ORDNER).glob(f"{EIGEN_PRÄFIX}*/**/*.md"))
    for rel in dict.fromkeys(quellen):
        Anzeige = rel.relative_to(root) if rel.is_absolute() else rel
        zeilen = _zeilen(root, rel)
        for nr, ln in _zaeune(zeilen):
            for lauf in re.findall(r"\bnpm run ([A-Za-z0-9:_-]+)", ln):
                if lauf not in laufnamen:
                    funde.append(Fund("K5", str(Anzeige), str(nr),
                                      f"`npm run {lauf}` existiert nicht in package.json – "
                                      "ein Runbook-Befehl, der nicht läuft, ist ein Erzeuger ohne Schritt."))
            for pfad in re.findall(r"\bpython3 (scripts/[A-Za-z0-9_./-]+\.py)", ln):
                if _vorlage(pfad):
                    continue
                if not (root / pfad).is_file():
                    funde.append(Fund("K5", str(Anzeige), str(nr), f"{pfad} fehlt."))
            for pfad in re.findall(r"\bnode ([a-zA-Z0-9_./-]+\.(?:mjs|js))", ln):
                if _vorlage(pfad):
                    continue
                if not (root / pfad).is_file():
                    funde.append(Fund("K5", str(Anzeige), str(nr), f"{pfad} fehlt."))
            for pfad, flagge in re.findall(
                    r"\bpython3 (scripts/[A-Za-z0-9_./-]+\.py)\s+((?:--[a-z][a-z0-9-]*)(?:\s+--[a-z][a-z0-9-]*)*)", ln):
                if _vorlage(pfad) or not (root / pfad).is_file():
                    continue
                quell = skripte.setdefault(pfad, _zeilen(root, pfad))
                for f in re.findall(r"--[a-z][a-z0-9-]*", flagge):
                    unter = f.replace("-", "_")
                    if not any(f in ln or unter in ln for ln in quell):
                        funde.append(Fund("K5", str(Anzeige), str(nr),
                                          f"{pfad} kennt die Flagge {f} nicht – Befund oder Doku ist falsch."))
    return funde


# ---------------------------------------------------------------- K6 Lizenz
def _datum(wert: str) -> date | None:
    try:
        return date.fromisoformat(str(wert).strip())
    except (TypeError, ValueError):
        return None


def k6_lizenz(root: Path, stichtag: date) -> tuple[list[Fund], list[Warn]]:
    funde: list[Fund] = []
    warnungen: list[Warn] = []
    text = _text(root, LIZENZ_DATEI)
    if text is None:
        return [Fund("K6", str(LIZENZ_DATEI), "", "fehlt – kein Herkunftsnachweis für vendored Skills.")], warnungen

    def _keine_duplikate(paare):
        seen: set[str] = set()
        out = {}
        for k, v in paare:
            if k in seen:
                raise ValueError(f"doppelter Schlüssel {k!r}")
            seen.add(k)
            out[k] = v
        return out

    try:
        register = json.loads(text, object_pairs_hook=_keine_duplikate)
    except (json.JSONDecodeError, ValueError) as exc:
        return [Fund("K6", str(LIZENZ_DATEI), "", f"unlesbar: {exc}")], warnungen

    skills = register.get("skills") or {}
    eigene = set((register.get("eigene") or {}).get("skills") or [])
    ordner = root / SKILL_ORDNER
    installiert = {p.name for p in ordner.iterdir() if p.is_dir()} if ordner.is_dir() else set()

    for name in sorted(installiert):
        if name.startswith(EIGEN_PRÄFIX):
            if name not in eigene:
                funde.append(Fund("K6", f"{SKILL_ORDNER}/{name}", "",
                                  "repo-eigener Skill nicht in `eigene.skills` des Registers – "
                                  "die Wache kann ihn sonst für Fremd-Code halten."))
            continue
        daten = skills.get(name)
        rel = f"{SKILL_ORDNER}/{name}"
        if not isinstance(daten, dict):
            funde.append(Fund("K6", rel, "", "kein Eintrag in der Lizenz-Datei – bei fremdem Code "
                                             "ist das keine Lücke, sondern eine Nutzung ohne Erlaubnis."))
            continue
        lizenz = str(daten.get("lizenz", "")).strip()
        if not lizenz:
            funde.append(Fund("K6", str(LIZENZ_DATEI), name, "Eintrag ohne `lizenz`."))
            continue
        if lizenz.strip().casefold().replace("_", "-") not in FREIE_LIZENZEN:
            # Kein „unbekannt“ und doch keine Freigabe: Das Haus anthropics/skills
            # mischt die Lizenzen je Ordner (skill-creator/frontend-design/
            # webapp-testing Apache-2.0, xlsx/pdf/docx eine vorbehaltene Lizenz mit
            # Verbot, die Materialien außerhalb des Dienstes zu behalten). Wer so
            # einen Ordner vendort, braucht die gleiche Entscheidung wie bei
            # „unbekannt“ – das Repo-Zeichen allein ist kein Nachweis.
            ausnahme = daten.get("ausnahme")
            if not isinstance(ausnahme, dict):
                funde.append(Fund("K6", rel, "", f"Lizenz „{lizenz}“ ohne Ausnahme – "
                                                  "ein Vermerk ohne Entscheidung ist ein Wegsehen."))
                continue
            for feld in ("grund", "entscheidung", "faellig"):
                if not str(ausnahme.get(feld, "")).strip():
                    funde.append(Fund("K6", str(LIZENZ_DATEI), f"{name}.ausnahme.{feld}",
                                      "fehlt – eine Ausnahme ohne Frist ist eine stille Abschaffung."))
            frist = _datum(ausnahme.get("faellig", ""))
            if frist is None:
                funde.append(Fund("K6", str(LIZENZ_DATEI), f"{name}.ausnahme.faellig",
                                  f"„{ausnahme.get('faellig')}“ ist kein ISO-Datum."))
            elif frist < stichtag:
                warnungen.append(Warn("K6", rel, str(frist.isoformat()),
                                      "Ausnahme abgelaufen – Lizenzfrage wieder offen "
                                      "(Bericht und Warnung, kein Blocker; so verhindert eine "
                                      "Frist einen Dauerläufer, ohne die Auslieferung zu geiseln)."))
            if lizenz.strip().casefold() == "unbekannt":
                # Nur hier endet der Block: „unbekannt“ heißt, es gibt keinen
                # Text, der neben dem SKILL.md liegen könnte. Bei einer
                # bekannten Sonderlizenz gilt der nächste Prüfschritt weiter –
                # die Ausnahme dokumentiert die Entscheidung, sie ersetzt
                # nicht den Volltext.
                continue
        hat = [p.name for p in sorted((root / rel).iterdir())
               if any(p.name.upper().startswith(m) for m in LIZENZ_MUSTER)]
        if not hat:
            funde.append(Fund("K6", rel, "", f"Lizenztext ({lizenz}) liegt nicht neben dem SKILL.md – "
                                              "MIT und Apache-2.0 verlangen den Volltext bei der Kopie."))
        if lizenz.startswith("Apache"):
            notice = [p for p in (root / rel).iterdir() if p.name.upper().startswith("NOTICE")]
            if daten.get("notiz") and not notice:
                funde.append(Fund("K6", rel, "", "Apache-2.0 mit NOTICE im Upstream, aber keiner Kopie – "
                                                  "§4(d) verlangt seine Weitergabe."))
    for name in sorted(set(skills) - installiert):
        warnungen.append(Warn("K6", str(LIZENZ_DATEI), name, "Register führt einen Skill, der nicht "
                                                              "installiert ist – Eintrag löschen oder installieren."))
    return funde, warnungen


# ---------------------------------------------------------------- K7 Verweise
def k7_verweise(root: Path) -> list[Fund]:
    funde: list[Fund] = []
    kern_zeilen = _zeilen(root, KERN)
    gebote = _nummerierte(kern_zeilen)
    uebersriften = _ueberschriften(root)
    quellen = sorted((root / "scripts").glob("*.py")) + sorted((root / ".github/workflows").glob("*.yml"))
    for quelldatei in quellen:
        rel = str(quelldatei.relative_to(root))
        for nr, ln in enumerate(_text(root, rel).split("\n") if _text(root, rel) else [], 1):
            if "CLAUDE.md" not in ln:
                continue
            for n in re.findall(r"(?:§\s*|Regel\s+)(\d{1,2})", ln):
                if int(n) not in gebote:
                    funde.append(Fund("K7", rel, str(nr),
                                          f"verweist auf Gebot {n} des Kerns – die nummerierten "
                                          f"Listen kennen nur {max(gebote) if gebote else 0} Punkte; "
                                          "der Verweis laeuft ins Leere."))
            for abschnitt in re.findall(r"Abschnitt[s]? ([A-ZÄÖÜ][A-Za-zÄÖÜäöüß0-9/_-]{2,})", ln):
                if not any(h.lower().startswith(abschnitt.lower()) for h in uebersriften):
                    funde.append(Fund("K7", rel, str(nr), f"verweist auf „Abschnitt {abschnitt}“ – "
                                                           "weder im Kern noch in einem Skill eine solche Überschrift."))
            m = re.search(r"([A-Za-zÄÖÜäöüß0-9_-]+)-Abschnitt", ln)
            if m and "CLAUDE.md" in ln:
                stich = m.group(1)
                if len(stich) > 2 and not any(h.lower().startswith(stich.lower()) for h in uebersriften):
                    funde.append(Fund("K7", rel, str(nr), f"verweist auf den „{stich}-Abschnitt“ – "
                                                           "die Überschrift existiert nirgends mehr."))
    return funde


# ---------------------------------------------------------------- K8 Siegelstand
def _siegel_klassen(root: Path) -> tuple[set[str], set[str]]:
    """`KRITISCH` und `FEST` aus `scripts/integrity_guard.py` – gelesen, nicht importiert.

    Der Import würde das Skript ausführen: es liest `sys.argv` schon beim Laden
    und signiert je nach Aufruf. `ast` reicht, so stehen die beiden Mengen da.
    """
    quelltext = _text(root, SIEGEL_GUARD)
    if quelltext is None:
        return set(), set()
    try:
        modul = ast.parse(quelltext)
    except SyntaxError:
        return set(), set()
    mengen: dict[str, set[str]] = {}
    for knoten in getattr(modul, "body", []):
        if not isinstance(knoten, ast.Assign) or not isinstance(knoten.value, (ast.Set, ast.List, ast.Tuple)):
            continue
        for ziel in knoten.targets:
            if isinstance(ziel, ast.Name) and ziel.id in ("KRITISCH", "FEST"):
                werte = {e.value for e in knoten.value.elts if isinstance(e, ast.Constant) and isinstance(e.value, str)}
                mengen.setdefault(ziel.id, set()).update(werte)
    return mengen.get("KRITISCH", set()), mengen.get("FEST", set())


def k8_siegel(root: Path) -> list[Warn]:
    """K8 meldet den Siegelstand – als Warnung, nie als Befund.

    Signieren ist ein Betreiberakt: Ein Gate, das eine ungezeichnete Datei hart
    rot macht, bestraft die falsche Seite. Am 19.09.2026 (Issue #316) stoppte
    genau so ein HARD STOP die Content-Engine im ersten Schritt, weil sechs
    geheilte Skripte nicht neu gezeichnet waren – der Alarm galt der Produktion,
    nicht dem Saboteur. Deshalb: Hinweis mit der Schlusszeile, Entscheidung beim
    Menschen.
    """
    text = _text(root, SIEGEL_LOCK)
    if text is None:
        return [Warn("K8", str(SIEGEL_LOCK), "",
                     "kein Siegel – der Schutz vor Austausch der Regelwachen ist ungeklärt "
                     "(Betreiberakt: `python3 scripts/integrity_guard.py --set-current`).")]
    try:
        lock = json.loads(text)
    except ValueError as exc:
        return [Warn("K8", str(SIEGEL_LOCK), str(getattr(exc, "lineno", "")),
                     "unlesbar – ein kaputtes Siegel meldet Scheinsicherheit, nie Sicherheit. "
                     "Belegte Heilung: `python3 scripts/integrity_guard.py --repair-lock --dry-run`.")]
    dateien = lock.get("files") if isinstance(lock, dict) else None
    if not isinstance(dateien, dict):
        return [Warn("K8", str(SIEGEL_LOCK), "files",
                     "fehlt oder ist kein Objekt – das Siegel ist nicht prüfbar "
                     "(`--repair-lock --dry-run` zeigt die Fassung aus Git).")]
    kritisch, fest = _siegel_klassen(root)
    if not kritisch and not fest:
        return [Warn("K8", str(SIEGEL_GUARD), "",
                     "KRITISCH/FEST nicht lesbar – der Siegelumfang ist nicht feststellbar. "
                     "Das ist kein Grund zum Wegsehen: `python3 scripts/integrity_guard.py --drift-audit` "
                     "antwortet trotzdem.")]
    warnungen: list[Warn] = []
    for rel in SIEGEL_PFLICHT:
        gezeichnet = rel in dateien
        in_der_klasse = rel in kritisch or rel in fest
        if not in_der_klasse and not gezeichnet:
            warnungen.append(Warn("K8", rel, "",
                                  "steht weder in KRITISCH/FEST noch im Siegel – die Datei entscheidet über "
                                  "Lizenzen und Kernbudget, ihr Austausch wäre lautlos. Schluss in einem Zug: "
                                  "in `FEST` aufnehmen UND `python3 scripts/integrity_guard.py "
                                  f"--add={rel}` zeichnen (nur ein Stand mit grünen Selbsttests), sonst steht "
                                  "das PR-Gate auf Rot, ohne dass jemand etwas verschuldet hätte."))
            continue
        if in_der_klasse and not gezeichnet:
            warnungen.append(Warn("K8", rel, "",
                                  "in KRITISCH/FEST, aber nie gezeichnet – jede Abweichung bleibt unbemerkt. "
                                  f"Schluss: `python3 scripts/integrity_guard.py --add={rel}`."))
            continue
        pfad = root / rel
        if not pfad.is_file():
            warnungen.append(Warn("K8", rel, "Siegel",
                                  "das Siegel trägt diese Datei, sie liegt aber nicht im Baum – "
                                  "`python3 scripts/integrity_guard.py --drift-audit` zeigt die Herkunft."))
            continue
        if hashlib.sha256(pfad.read_bytes()).hexdigest() != dateien.get(rel):
            warnungen.append(Warn("K8", rel, "Siegel",
                                  "Abweichung vom gezeichneten Stand. Belegt (committet, bytegleich, kein "
                                  "KRITISCH) ist das signierbar mit `python3 scripts/integrity_guard.py --heal`; "
                                  "ungeklärt ist es ein Fall für den Betreiber, nicht für eine Unterschrift unter "
                                  "einem defekten Stand."))
    return warnungen


# ---------------------------------------------------------------- K9 Beschreibungs-Budget
def k9_beschreibungs_budget(root: Path) -> list[Fund]:
    """Die Beschreibungen sind der Preis der Bibliothek – und niemand sieht ihn.

    Jede `description` steht in jeder Session im Kontext, unabhängig vom Auftrag;
    am 01.11.2026 waren das bei 75 Skills rund 14.000 Tokens. Ein Befund ist
    deshalb nicht die einzelne lange Beschreibung (die prüft K2), sondern die
    Summe: Wer sie überschreitet, entscheidet über Vorladelast, nicht über Dateien.
    """
    ordner = root / SKILL_ORDNER
    if not ordner.is_dir():
        return []
    zeichen = 0
    for d in sorted(p for p in ordner.iterdir() if p.is_dir()):
        fm = frontmatter(_zeilen(root, f"{SKILL_ORDNER}/{d.name}/SKILL.md"))
        zeichen += len(" ".join(str(fm.get("description", "")).split()))
    kilo = zeichen / 1024
    if kilo <= BESCHREIBUNG_KB_MAX:
        return []
    return [Fund("K9", str(SKILL_ORDNER), f"{kilo:.1f} KB",
                 f"alle Beschreibungen zusammen sind {kilo:.1f} KB (~{zeichen // 4} Tokens) und "
                 f"liegen über dem Budget von {BESCHREIBUNG_KB_MAX:.0f} KB. Diese Last zahlt jede "
                 "Session, auch wenn der Skill nie gelesen wird: Beschreibungen kürzen, Skills "
                 "entfernen oder die Grenze bewusst anheben – aber nicht stillschweigend wachsen lassen.")]


# ---------------------------------------------------------------- K10 Zusatzdateien
def _ist_nachweis(name: str) -> bool:
    """Trägt diese Datei einen repo-eigenen Zusatz? Nur dann ist sie gefährdet."""
    return name in NACHWEIS_DATEIEN or any(name.endswith(m) for m in NACHWEIS_MUSTER)


def k10_zusatzdateien(root: Path) -> tuple[list[Fund], list[Warn]]:
    """Ein Update, das fremde Ordner neu schreibt, löscht Eigenes – laut oder nie.

    Der Skills-CLI kennt nur, was im Upstream liegt, und schreibt beim `update`
    den ganzen Ordner neu. Am 01.11.2026 hat `npx -y skills@1.7.4 add … --skill '*'`
    die deutsche `copy-editing`-Ausgabe entfernt (SKILL_DE.md, evals-de.json,
    vier references/*-de.md) – und der Vertrag blieb grün, weil er nur Lizenzen
    und `ff-*` kannte.

    Die Heilung ist nicht „retten und hoffen", sondern **umziehen**: die
    Ergänzung gehört in ein `ff-*`-Skill, wo sie niemand überschreibt. Der
    geschlossene Fall steht deshalb mit Ziel in `data/skill_ergaenzungen.json`,
    und diese Prüfung fragt ab jetzt genau eine Sache: Liegt jede dort
    verzeichnete Datei **noch** da, wo sie nicht hingehört (Warnung), oder ist
    sie an ihrem Ziel (still)? Fehlt sie an beiden Orten, ist das ein Befund –
    dann war es ein `update`, kein Umzug.

    Dazu bleibt die alte Warnung für jeden **neuen** Fund in einem Fremd-Ordner:
    Wer künftig eine `*-de.md` in fremdes Haus legt, hört das sofort.
    """
    funde: list[Fund] = []
    warnungen: list[Warn] = []
    ordner = root / SKILL_ORDNER
    if not ordner.is_dir():
        return funde, warnungen

    # 1) Was liegt JETZT repo-eigen in einem Fremd-Ordner? (Warnung, ein Fund je Ordner)
    for d in sorted(p for p in ordner.iterdir() if p.is_dir()):
        if d.name.startswith(EIGEN_PRÄFIX):
            continue
        eigene = [datei.relative_to(d).as_posix() for datei in sorted(d.rglob("*"))
                  if datei.is_file() and _ist_nachweis(datei.name)]
        if not eigene:
            continue
        warnungen.append(Warn("K10", f"{SKILL_ORDNER}/{d.name}", str(len(eigene)),
                              f"repo-eigene Datei(en) in einem Fremd-Ordner – `npx skills update` "
                              f"ersetzt diesen Ordner und löscht sie: {', '.join(eigene)}. Nach jedem "
                              "Update `git status .claude/skills` prüfen; dauerhaft gehört die Regel "
                              "in einen `ff-*`-Skill, nicht in fremdes Haus."))

    # 2) Was stand früher dort? Jeder Eintrag muss an seinem Ziel angekommen sein.
    text = _text(root, ERGAENZUNGEN)
    if text is None:
        return funde, warnungen
    try:
        register = json.loads(text)
    except ValueError as enc:
        return [Fund("K10", str(ERGAENZUNGEN), "", f"unlesbar: {enc} – ohne Register ist "
                                                   "„verschwunden“ von „umgezogen“ nicht zu trennen.")], warnungen
    staende = (register or {}).get("staende") or []
    if not isinstance(staende, list):
        return [Fund("K10", str(ERGAENZUNGEN), "staende", "kein Verzeichnis von Ständen.")], warnungen
    for stand in staende:
        if not isinstance(stand, dict):
            funde.append(Fund("K10", str(ERGAENZUNGEN), "", "Eintrag ohne Angaben."))
            continue
        for datei in stand.get("dateien") or []:
            alt_pfad = str(datei.get("alt") or "")
            ziel = str(datei.get("ziel") or "")
            if not alt_pfad:
                funde.append(Fund("K10", str(ERGAENZUNGEN), str(stand.get("fall")),
                                  "Eintrag ohne `alt` – ohne Herkunft ist der Umzug nicht prüfbar."))
                continue
            if ziel and (root / ziel).is_file():
                continue                      # angekommen
            if (root / alt_pfad).is_file():
                warnungen.append(Warn("K10", alt_pfad, "",
                                      "liegt wieder (oder noch) im Fremd-Ordner – der nächste "
                                      f"`npx skills update` löscht sie. Ziel laut Register: `{ziel or '—'}`."))
                continue
            funde.append(Fund("K10", alt_pfad, "",
                              "fehlt und ist am Ziel nicht angekommen – das ist kein Umzug, sondern "
                              f"ein Verlust durch ein `update`. Ziel laut Register: `{ziel or '—'}`; "
                              "aus Git wiederherstellen und umziehen."))
    return funde, warnungen


# ---------------------------------------------------------------- Bilanz
def befunde(root: Path, stichtag: date | None = None) -> tuple[list[Fund], list[Warn], int]:
    tag = stichtag or date.today()
    alle: list[Fund] = []
    warnungen: list[Warn] = []
    geprueft = 0
    for funde in (k1_budget(root), k2_form(root), k3_erreichbarkeit(root), k5_befehle(root),
                  k7_verweise(root), k9_beschreibungs_budget(root)):
        alle += funde
    k4_f, k4_w = k4_herkunft(root)
    k6_f, k6_w = k6_lizenz(root, tag)
    k10_f, k10_w = k10_zusatzdateien(root)
    alle += k4_f + k6_f + k10_f
    warnungen += k4_w + k6_w + k10_w + k8_siegel(root)
    ordner = root / SKILL_ORDNER
    geprueft = len([p for p in ordner.iterdir() if p.is_dir()]) if ordner.is_dir() else 0
    return alle, warnungen, geprueft


def bericht(funde: list[Fund], warnungen: list[Warn], geprueft: int) -> str:
    zeilen = [
        "## Skill-Vertrag – Kernbudget, Herkunft, Lizenz, Siegelstand",
        "",
        f"Geprüft: {geprueft} Skill(s) unter `{SKILL_ORDNER}`, Kern `{KERN}`, "
        f"Lock `{LOCK}`, Lizenz-Register `{LIZENZ_DATEI}`.",
        "",
    ]
    if not funde and not warnungen:
        zeilen.append("✅ Befundfrei: der Kern hält sein Budget, jeder Skill ist erreichbar, "
                      "vendored Skills sind lizenziert, jeder Befehl im Runbook läuft und der "
                      "Siegelstand ist geklärt.")
    if warnungen:
        zeilen += ["", "**Warnungen (kein Blocker):**", ""]
        zeilen += [f"- {w.kurz()}" for w in warnungen]
    if funde:
        zeilen += ["", f"**🛑 {len(funde)} Befund(e):**", ""]
        zeilen += [f"- `{f.kurz()}`" for f in funde]
        zeilen += ["", "Heilung: Regel in den zuständigen Skill verschieben, Link nachziehen, "
                       "Lizenztext aus der Upstream-Quelle ablegen oder die Ausnahme begründen. "
                       "Nichts davon ist eine Unterdrückung – die Liste ist der Stand."]
    return "\n".join(zeilen)


# ---------------------------------------------------------------- Selbsttest
def _schreibe(wurzel: Path, rel: str, text: str) -> None:
    pfad = wurzel / rel
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(text, encoding="utf-8")


GRUND_SKILL = """---
name: {name}
description: "{desc}"
metadata:
  version: 1.0.0
---

# {titel}

Detail: `references/{ref}`
"""


def _sauberer_kern() -> str:
    gebote = "\n".join(f"{i}. **Regel {i}.** Text mit genug Länge zum Prüfen." for i in range(1, 7))
    return ("# CLAUDE.md – Kern\n\n"
            "## Sicherheitsregeln für Agenten\n\n" + gebote + "\n\n"
            "## Wo welches Detail steht (Skill-Router)\n\n"
            "`ff-eins` ist der Router-Skill.\n\n"
            "## Wichtige Konventionen\n\n- Commits auf Deutsch.\n")


def _fixture(wurzel: Path, *, kern: str | None = None, skill_md: str | None = None,
             refs: dict[str, str] | None = None, lock: dict | None = None,
             lizenz: dict | None = None, pakete: dict | None = None,
             fremd: dict[str, str] | None = None, siegel: dict | None = None,
             guard_fest: list[str] | None = "default") -> Path:
    _schreibe(wurzel, KERN, kern if kern is not None else _sauberer_kern())
    _schreibe(wurzel, "package.json", json.dumps({"name": "x", "scripts": pakete or {}}))
    desc = ("Benutzen, wenn dieses Repo geprüft werden muss: Commit, Merge, Befund, "
            "neue Wache oder ein Selbsttest, der nicht das eigene Modul prüft. Auslöser "
            "sind auch 'welcher Test?' und 'das Gate ist rot'. Nicht für Deploy-Reihenfolge.")
    _schreibe(wurzel, f"{SKILL_ORDNER}/ff-eins/SKILL.md",
              skill_md if skill_md is not None
              else GRUND_SKILL.format(name="ff-eins", titel="Prüfen", ref="eins.md", desc=desc))
    for name, text in (refs or {"eins.md": "# Eins\n\nText.\n"}).items():
        _schreibe(wurzel, f"{SKILL_ORDNER}/ff-eins/references/{name}", text)
    for name, text in (fremd or {}).items():
        _schreibe(wurzel, f"{SKILL_ORDNER}/{name}/SKILL.md", text)
    _schreibe(wurzel, LOCK, json.dumps(
        lock if lock is not None else {"version": 1, "skills": {}}, ensure_ascii=False))
    if lizenz is None:
        lizenz = {"schema": 1, "skills": {}, "eigene": {"skills": ["ff-eins"]}}
    _schreibe(wurzel, str(LIZENZ_DATEI), json.dumps(lizenz, ensure_ascii=False))
    # Siegel: ohne Angabe trägt der Fixture-Baum beide Schutzdateien – sonst
    # meldet jede Gegenprobe eine K8-Warnung, die mit dem Fall nichts zu tun hat.
    if guard_fest is not None:
        mengen = "KRITISCH = set()\nFEST = {%s}\n" % ", ".join(
            '"%s"' % rel for rel in (guard_fest if isinstance(guard_fest, list) else SIEGEL_PFLICHT))
        _schreibe(wurzel, str(SIEGEL_GUARD), "#!/usr/bin/env python3\n" + mengen)
        # Die Wache selbst liegt im Fixture nicht im Baum – ohne Platzhalter
        # wäre jeder saubere Fall ein „Siegel trägt eine fehlende Datei".
        if not (wurzel / SIEGEL_PFLICHT[0]).is_file():
            _schreibe(wurzel, SIEGEL_PFLICHT[0],
                      "#!/usr/bin/env python3\n# Fixture-Platzhalter für die Wache.\n")
    if siegel is None and guard_fest is not None:
        gezeichnet = {rel: hashlib.sha256((wurzel / rel).read_bytes()).hexdigest()
                      for rel in SIEGEL_PFLICHT if (wurzel / rel).is_file()}
        siegel = {"schema": 1, "files": gezeichnet}
    if siegel is not None:
        _schreibe(wurzel, str(SIEGEL_LOCK), json.dumps(siegel, ensure_ascii=False))
    return wurzel


def selftest() -> int:
    geprueft = 0
    fehler: list[str] = []

    def erzwinge(name: str, wurzel: Path, erwartete_klasse: str | None):
        nonlocal geprueft
        funde, _, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        gefunde = {f.klasse for f in funde}
        if erwartete_klasse is None:
            if funde:
                fehler.append(f"{name}: Gegenprobe erwartet 0 Befunde, gekommen: "
                              + "; ".join(f.kurz() for f in funde[:3]))
        elif erwartete_klasse not in gefunde:
            fehler.append(f"{name}: erwartete {erwartete_klasse}, gekommen: "
                          + (", ".join(sorted(gefunde)) or "nichts"))
        geprueft += 1

    with tempfile.TemporaryDirectory() as tmp:
        # 1) GEGENPROBE: ein sauberer Stand meldet nichts.
        wurzel = _fixture(Path(tmp) / "sauber")
        erzwinge("Gegenprobe sauber", wurzel, None)

        # 2) K1: Kern über dem Budget.
        wurzel = _fixture(Path(tmp) / "k1", kern=_sauberer_kern() + "\n" + "Zeile.\n" * (ZEILEN_MAX + 5))
        erzwinge("K1 Kern zu lang", wurzel, "K1")

        # 3) K2: name passt nicht zum Ordner.
        wurzel = _fixture(Path(tmp) / "k2a",
                          skill_md=GRUND_SKILL.format(name="ff-anders", titel="Prüfen", ref="eins.md",
                                                      desc="x" * (DESC_MIN + 1)))
        erzwinge("K2 Name ungleich Ordner", wurzel, "K2")

        # 4) K2: Beschreibung über dem harten Limit.
        wurzel = _fixture(Path(tmp) / "k2b",
                          skill_md=GRUND_SKILL.format(name="ff-eins", titel="Prüfen", ref="eins.md",
                                                      desc="y" * (DESC_MAX + 20)))
        erzwinge("K2 Beschreibung zu lang", wurzel, "K2")

        # 5) K3: Detaildatei ohne Link im Skill.
        wurzel = _fixture(Path(tmp) / "k3", refs={"eins.md": "# Eins\n", "zwei.md": "# Zwei\n"})
        erzwinge("K3 Referenz verwaist", wurzel, "K3")

        # 6) K4: eigener Skill im Lock – Update würde Regelwerk überschreiben.
        wurzel = _fixture(Path(tmp) / "k4", lock={"version": 1, "skills": {
            "ff-eins": {"source": "ich/ich", "skillPath": "skills/x/SKILL.md"}}})
        erzwinge("K4 ff-* im Lock", wurzel, "K4")

        # 7) K4: installierter Fremd-Skill ohne Herkunftsnachweis.
        wurzel = _fixture(Path(tmp) / "k4b",
                          fremd={"fremd-skill": "---\nname: fremd-skill\ndescription: „d“\n---\n\n# F\n"},
                          lock={"version": 1, "skills": {}})
        erzwinge("K4 Fremd-Skill im Lock", wurzel, "K4")

        # 8) K5: Runbook-Befehl ohne Lauf, Skript ohne Datei, Flagge ohne Quelltext.
        wurzel = _fixture(Path(tmp) / "k5",
                          kern=_sauberer_kern() + "\n```bash\nnpm run es-gibt-es-nicht\n"
                                                 "python3 scripts/fehlt.py --flagge\npython3 scripts/<wache>.py --selber\n```\n")
        funde, _, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        k5 = [f for f in funde if f.klasse == "K5"]
        geprueft += 1
        if len(k5) != 2:
            fehler.append(f"K5: 2 Befunde erwartet (Laufname + fehlende Datei, Vorlage ignoriert), "
                          f"gekommen {len(k5)}: " + "; ".join(f.meldung for f in k5))

        # 9) K6: Fremd-Skill ohne Lizenzdatei.
        wurzel = _fixture(Path(tmp) / "k6a",
                          fremd={"fremd-skill": "---\nname: fremd-skill\ndescription: „d“\n---\n\n# F\n"},
                          lock={"version": 1, "skills": {"fremd-skill": {"source": "a/b", "skillPath": "s/SKILL.md"}}},
                          lizenz={"schema": 1, "eigene": {"skills": ["ff-eins"]},
                                  "skills": {"fremd-skill": {"quelle": "a/b", "lizenz": "MIT"}}})
        erzwinge("K6 Lizenztext fehlt", wurzel, "K6")

        # 10) K6: „unbekannt“ ohne Ausnahme = Wegsehen.
        wurzel = _fixture(Path(tmp) / "k6b",
                          fremd={"fremd-skill": "---\nname: fremd-skill\ndescription: „d“\n---\n\n# F\n"},
                          lock={"version": 1, "skills": {"fremd-skill": {"source": "a/b", "skillPath": "s/SKILL.md"}}},
                          lizenz={"schema": 1, "eigene": {"skills": ["ff-eins"]},
                                  "skills": {"fremd-skill": {"quelle": "a/b", "lizenz": "unbekannt"}}})
        funde, _, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        if not any(f.klasse == "K6" and "Ausnahme" in f.meldung for f in funde):
            fehler.append("K6: unbekannte Lizenz ohne Ausnahme bleibt ohne Befund.")

        # 11) K6: abgelaufene Frist warnt, blockiert nicht.
        wurzel = _fixture(Path(tmp) / "k6c",
                          fremd={"fremd-skill": "---\nname: fremd-skill\ndescription: „d“\n---\n\n# F\n"},
                          lock={"version": 1, "skills": {"fremd-skill": {"source": "a/b", "skillPath": "s/SKILL.md"}}},
                          lizenz={"schema": 1, "eigene": {"skills": ["ff-eins"]}, "skills": {
                              "fremd-skill": {"quelle": "a/b", "lizenz": "unbekannt",
                                              "ausnahme": {"grund": "g", "entscheidung": "e",
                                                           "faellig": "2026-12-31"}}}})
        funde, warnungen, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        if any(f.klasse == "K6" for f in funde) or not any(w.klasse == "K6" for w in warnungen):
            fehler.append("K6: abgelaufene Ausnahme muss warnen ohne Befund zu sein.")

        # 12) K7: Verweis auf ein Gebot, das es nicht gibt.
        wurzel = _fixture(Path(tmp) / "k7")
        # Die Sperre nennt ihren Gegenstand im Selbsttest – wie `fremdmessung_sperre.py`
        # seine BEISPIEL_ANBINDUNG baut, damit der eigene Test nicht zum Fund wird.
        marke = "".join(["CLAUDE", ".", "md"])
        _schreibe(wurzel, "scripts/beispiel.py",
                  f"# ({marke}, Regel 42)\n# siehe {marke}, Abschnitt Nirgendwo\n")
        funde, _, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        klassen = {f.klasse for f in funde}
        if "K7" not in klassen:
            fehler.append(f"K7: toter Verweis ins Regelwerk bleibt ohne Befund (Klassen: {sorted(klassen)}).")

        # 13) K8: Siegelumfang kennt die zwei Schutzdateien nicht = Warnung, nie
        #     Befund (Zeichnen bleibt Betreiberakt, das Gate darf nicht kneifen).
        wurzel = _fixture(Path(tmp) / "k8a", guard_fest=["assets/css/extended/custom.css"],
                          siegel={"schema": 1, "files": {}})
        funde, warnungen, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        if any(f.klasse == "K8" for f in funde):
            fehler.append("K8: ungezeichnete Datei darf das Gate nicht blockieren – Zeichnen ist Betreiberakt.")
        if sum(1 for w in warnungen if w.klasse == "K8") != 2:
            fehler.append(f"K8: 2 Warnungen (Wache + Register) erwartet, gekommen "
                          f"{sum(1 for w in warnungen if w.klasse == 'K8')}.")

        # 14) K8: in der Klasse, aber nie gezeichnet – und: gezeichnet = still.
        wurzel = _fixture(Path(tmp) / "k8b", siegel={"schema": 1, "files": {}})
        _, warnungen, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        if not any(w.klasse == "K8" and "nie gezeichnet" in w.meldung for w in warnungen):
            fehler.append("K8: Datei in FEST, aber ohne Zeichnung bleibt ohne Hinweis.")
        wurzel = _fixture(Path(tmp) / "k8c")
        _, warnungen, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        if any(w.klasse == "K8" for w in warnungen):
            fehler.append("K8: ein tragendes Siegel meldet trotzdem – " + warnungen[0].kurz())

        # 15) K6: eine Lizenz außerhalb des Freie-Sets braucht denselben
        #     Ausnahmekern wie „unbekannt“ (der Fall xlsx: vorbehaltene Lizenz).
        wurzel = _fixture(Path(tmp) / "k6d",
                          fremd={"fremd-skill": "---\nname: fremd-skill\ndescription: „d“\n---\n\n# F\n"},
                          lock={"version": 1, "skills": {"fremd-skill": {"source": "a/b", "skillPath": "s/SKILL.md"}}},
                          lizenz={"schema": 1, "eigene": {"skills": ["ff-eins"]}, "skills": {
                              "fremd-skill": {"quelle": "a/b", "lizenz": "vorbehalten"}}})
        funde, _, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        if not any(f.klasse == "K6" and "vorbehalten" in f.meldung for f in funde):
            fehler.append("K6: eine Lizenz außerhalb des Freie-Sets ohne Ausnahme bleibt ohne Befund.")

        # 16) K9: Summe der Beschreibungen über dem Budget – nicht die einzelne
        #     Beschreibung (das ist K2), sondern die Vorladelast der Bibliothek.
        viele = {f"fremd-{i}": "---\nname: fremd-%d\ndescription: „%s“\n---\n\n# F\n" % (i, "z" * 400)
                 for i in range(int(BESCHREIBUNG_KB_MAX * 1024 / 400) + 2)}
        wurzel = _fixture(Path(tmp) / "k9", fremd=viele,
                          lock={"version": 1, "skills": {n: {"source": "a/b", "skillPath": "s/SKILL.md"}
                                                         for n in viele}},
                          lizenz={"schema": 1, "eigene": {"skills": ["ff-eins"]},
                                  "skills": {n: {"quelle": "a/b", "lizenz": "MIT", "notiz": ""}
                                             for n in viele}})
        for n in viele:
            _schreibe(wurzel, f"{SKILL_ORDNER}/{n}/LICENSE.txt", "MIT License\n")
        funde, _, _ = befunde(wurzel, stichtag=date(2027, 1, 15))
        geprueft += 1
        if not any(f.klasse == "K9" for f in funde):
            fehler.append("K9: Beschreibungs-Summe über dem Budget bleibt ohne Befund.")

        # 17) K10: drei Zustände eines Umzugs – angekommen (still), Rückfall
        #     (Warnung), Verlust (Befund). Der echte Fall copy-editing → ff-lektorat.
        def _k10_wurzel(marke: str, *, alt_datei: bool, ziel_datei: bool) -> Path:
            w = _fixture(Path(tmp) / marke,
                         fremd={"fremd-skill": "---\nname: fremd-skill\ndescription: „d“\n---\n\n# F\n"},
                         lock={"version": 1, "skills": {"fremd-skill": {"source": "a/b",
                                                                       "skillPath": "s/SKILL.md"}}},
                         lizenz={"schema": 1, "eigene": {"skills": ["ff-eins", "ff-neu"]},
                                 "skills": {"fremd-skill": {"quelle": "a/b", "lizenz": "MIT"}}})
            _schreibe(w, f"{SKILL_ORDNER}/fremd-skill/LICENSE.txt", "MIT License\n")
            _schreibe(w, str(ERGAENZUNGEN), json.dumps({"schema": 1, "staende": [{
                "fall": "x", "dateien": [{"alt": f"{SKILL_ORDNER}/fremd-skill/SKILL_DE.md",
                                          "ziel": f"{SKILL_ORDNER}/ff-neu/SKILL_DE.md"}]}]}))
            _schreibe(w, f"{SKILL_ORDNER}/ff-neu/SKILL.md",
                      "---\nname: ff-neu\ndescription: \"d\"\n---\n\n# N\n")
            if alt_datei:
                _schreibe(w, f"{SKILL_ORDNER}/fremd-skill/SKILL_DE.md", "# Eigenes\n")
            if ziel_datei:
                _schreibe(w, f"{SKILL_ORDNER}/ff-neu/SKILL_DE.md", "# Eigenes\n")
            return w

        # angekommen: still
        funde, warnungen, _ = befunde(_k10_wurzel("k10a", alt_datei=False, ziel_datei=True),
                                      stichtag=date(2027, 1, 15))
        geprueft += 1
        if [f for f in funde + warnungen if f.klasse == "K10"]:
            fehler.append("K10: ein abgeschlossener Umzug darf nichts melden.")
        # Rückfall: Warnung, kein Befund
        funde, warnungen, _ = befunde(_k10_wurzel("k10b", alt_datei=True, ziel_datei=True),
                                      stichtag=date(2027, 1, 15))
        geprueft += 1
        if [f for f in funde if f.klasse == "K10"] or not [w for w in warnungen if w.klasse == "K10"]:
            fehler.append("K10: eine zurückgelegte Datei muss warnen, nicht blockieren.")
        # Verlust: Befund
        funde, _, _ = befunde(_k10_wurzel("k10c", alt_datei=False, ziel_datei=False),
                              stichtag=date(2027, 1, 15))
        geprueft += 1
        if not [f for f in funde if f.klasse == "K10" and "Verlust" in f.meldung]:
            fehler.append("K10: eine verschwundene Ergänzung ist ein Befund, keine Warnung.")

        # 18) Der Selbsttest prüft sich selbst, nicht das Netz: kein Befund
        #     hängt an einer Wanduhr (Datum ist gesetzt, nicht geraten).
        funde_heute, _, _ = befunde(Path(tmp) / "sauber")
        geprueft += 1
        if funde_heute:
            fehler.append("Selbsttest hängt an der Wanduhr: derselbe Stand meldet je nach Datum "
                          f"{len(funde_heute)} Befund(e).")

    if fehler:
        print("🛑 skills_vertrag --selftest FEHLERHALFT (Selbsttest prüft die Detektoren):")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ skills_vertrag --selftest OK ({geprueft} eingefrorene Fälle: Gegenprobe, Kernbudget, "
          "Name und Beschreibung, verwaiste Referenz, ff-* im Lock, Fremd-Skill ohne Herkunft, "
          "toter Befehl, Vorlagen-Ausnahme, Lizenztext, Ausnahme ohne und mit abgelaufener Frist, "
          "Lizenz außerhalb des Freie-Sets, toter Regelwerk-Verweis, Siegelumfang und fehlende "
          "Zeichnung, Beschreibungs-Budget, Umzug/Rückfall/Verlust einer Zusatzdatei, Uhr-Unabhängigkeit).")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Skill-Vertrag: Kernbudget, Herkunft, "
                                                 "Erreichbarkeit, Befehle, Lizenzen, Verweise, Siegelstand")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Schutz (offline, uhrfest)")
    parser.add_argument("--json", action="store_true", help="Maschinenausgabe")
    parser.add_argument("--md", action="store_true", help="Markdown für die Lauf-Summary")
    parser.add_argument("root", nargs="?", default=None, help="Prüfwurzel (Standard: Repo)")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()

    root = Path(args.root).resolve() if args.root else BLOG_DIR
    if not (root / KERN).is_file():
        print(f"🛑 skills_vertrag: {root} ist keine Prüfwurzel ({KERN} fehlt).", file=sys.stderr)
        return 2
    funde, warnungen, geprueft = befunde(root)

    if args.json:
        print(json.dumps({"geprueft": geprueft,
                          "funde": [f._asdict() for f in funde],
                          "warnungen": [w._asdict() for w in warnungen]}, ensure_ascii=False, indent=2))
    else:
        text = bericht(funde, warnungen, geprueft)
        print(text)
        if not args.md:
            for f in funde:
                print(f"  🛑 {f.kurz()}", file=sys.stderr)
            print(f"skills_vertrag: {geprueft} Skill(s) geprüft, {len(funde)} Befund(e), "
                  f"{len(warnungen)} Warnung(en)")
        for f in funde:
            print(f"::error title=Skill-Vertrag {f.klasse}::{f.kurz()}")
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
