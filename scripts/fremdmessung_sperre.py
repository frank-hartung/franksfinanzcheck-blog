#!/usr/bin/env python3
"""
FREMDMESSUNG-SPERRE – Umami ist entfernt und bleibt es.

WARUM (Governance-Report #806, 19.10.2026):
Am 11.10.2026 wurde Umami aus dem Frontend genommen (Skript, Einwilligungs-
Banner). Die ANBINDUNG lebte weiter: zwei Import-Skripte, je zwei Workflow-
Schritte in zwei Workflows, ein Secret mit Live-Probe, vier Datenstände, ein
Trichter, der „Klicks und Besuche werden im Umami-Dashboard erfasst" behauptete
(falsch: nichts wurde erfasst) und zwei Info-Zeilen im Governance-Issue. Nichts
davon hat etwas gemessen – alles hat Aufmerksamkeit gekostet und eine Messung
vorgetäuscht, die nicht stattfand. Der Vorfall hatte zwei Ursachen: Es gab
keinen Ort, an dem „Anbindung ohne Dienst" auffällt, und die Entfernung des
Frontends hat die Anbindung nicht mitgenommen.

Diese Wache ist der Ort. Sie liest den Quelltext (und auf Wunsch den gebauten
Baum), ohne etwas auszuführen, und meldet – hart, Exit 1:

  F1-DATEI      Eine Datei heißt „umami" (Skript, Datenstand, Workflow, Doku).
  F2-ANBINDUNG  Ein Anbindungs-Merkmal steht im Text: Skript-Host (umami.is),
                Attribut `data-umami-…` / `data-website-id`, `umami.track`,
                Secret/Variable `UMAMI_…`, Konfig-Schlüssel (`params.umami`,
                `umami_api_import_enabled` …). Überall – auch in content/ und
                data/ –, denn diese Merkmale sind nie Prosa.
  F3-ERWAEHNUNG Das Wort „Umami" in einer lebenden technischen Datei
                (Workflow, Skript, Layout, Doku …). NICHT in content/ und data/:
                dort ist es als Geschmacksrichtung redaktionell erlaubt, nur die
                Anbindungs-Merkmale (F2) nicht.
  F4-GEBAUT     (nur mit --public) Der gebaute Baum trägt ein Anbindungs-Merkmal
                oder – in Skripten und Stilen, die Besucher laden – das Wort.
  F5-AUSNAHME   Eine Ausnahme ist unbegründet, unbekannt oder veraltet (deckt
                keinen Fund mehr). Eine veraltete Ausnahme ist ein offenes Tor.

NICHT GESCANNT (HISTORISCH): Das Gedächtnis des Repos darf den Namen behalten –
datierte Berichte, `docs/archiv/`, das Patch-Archiv der Awin-Entfernung und alle
append-only Ledger (`data/**/*.jsonl`). Eine Geschichte umzuschreiben wäre
Fälschung, keine Sauberkeit.

NICHT GESCANNT (GENERIERT): Maschinell erzeugte Momentaufnahmen des letzten Laufs
(Cockpit, Governance-Ledger) hinken dem Code um höchstens einen Bot-Lauf nach.
Die URSACHE einer Spur dort läge im Code, den diese Wache prüft – ein Lauf-
Rückstand ist kein Befund und würde `main` nach einem Merge-Konflikt grundlos
rot färben.

AUSNAHMEN (ERLAUBT) stehen unten, jede mit Grund – die Wache selbst und ihre
Tests, das Runbook, die Dauervorgabe, Absenz-Tests und die Sperrliste der
Newsletter-QA (sie VERBIETEN den Namen, statt ihn zu benutzen) sowie zwei
Kommentar-Altlasten in KRITISCH gesiegelten Dateien (Änderung = menschliche
Neu-Signatur, siehe Eintrag).

Aufruf:
  python3 scripts/fremdmessung_sperre.py                  # Quelltext prüfen (Exit 0/1)
  python3 scripts/fremdmessung_sperre.py --public public/ # zusätzlich den gebauten Baum
  python3 scripts/fremdmessung_sperre.py --json           # maschinenlesbar
  python3 scripts/fremdmessung_sperre.py --selftest       # Logik-Beweis (schreibt nie)

Verdrahtung: Governance-Vertrag C40 (läuft mit dem Qualitäts-Gate über
`governance_contract.py --quick`), `scripts/tests/test_fremdmessung_sperre.py`
(läuft in der PR-Regression nach einem echten Hugo-Bau, prüft dort auch
`public/`), `npm run test:fremdmessung`. Runbook:
docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md.

Exit-Codes: 0 = sauber, 1 = Befund, 2 = Selbsttest/Hausfehler.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from collections import namedtuple
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

Fund = namedtuple("Fund", "klasse pfad stelle meldung")

# ---------------------------------------------------------------- Muster

# Anbindungs-Merkmale: nie Prosa, überall verboten (außer in HISTORISCH/ERLAUBT).
SIGNAL_TEILE = (
    r"umami\.(?:is|js)\b",                               # Hosts + Skriptname
    r"data-umami-[a-z0-9-]+",                            # Ereignis-Attribute
    r"data-website-id",                                  # Attribut des Tracking-Skripts
    r"\bwindow\.umami\b",                                # JS-Objekt
    r"\bumami\.(?:track|identify|trackview)\b",          # JS-API
    r"\bUMAMI_[A-Z0-9_]+\b",                             # Secrets/Variablen
    r"x-umami-api-key",                                  # API-Kopf
    r"umami_api_import_enabled",                         # alter Betriebsschalter
    r"\[params\.umami\]|\bparams\.umami\b",              # Hugo-Konfiguration
    r"\bsite\.Params\.umami\b|\bParams\.umami\b",        # Hugo-Template-Zugriff
    r"\b(?:provider|analytics)\s*:\s*umami",             # YAML-Schlüssel
    r"\bumami_(?:clicks|views|ctas)\b",                  # alte Skript-/Datenstand-Namen
    r"--emit\s+umami",                                   # alte Governance-Gate-Kennung
)
SIGNAL_RE = re.compile("|".join(SIGNAL_TEILE), re.IGNORECASE)
# Das Wort allein (Geschmacksrichtung ist redaktionell erlaubt, siehe EDITORIAL).
WORT_RE = re.compile(r"\bumami\b", re.IGNORECASE)
# Schneller Vorfilter je Datei/Zeile. `data-website-id` gehört dazu, obwohl das Wort
# „umami" dort nicht steht: Ein SELBST GEHOSTETES Snippet (eigene Domain) trägt nur
# dieses Attribut – der wahrscheinlichste Weg zurück.
VORFILTER = re.compile(r"umami|data-website-id", re.IGNORECASE)
# Eine typische Spur als Beispiel – für Selbsttests anderer Verträge (C40), damit diese
# den Namen nicht selbst als Literal tragen müssen (die Sperre würde ihn dort finden).
BEISPIEL_ANBINDUNG = '<script defer src="https://cloud.umami.is/script.js"></script>'
# Dateiname: Wortgrenze im Namen, nur für text-/code-artige Endungen (ein Foto
# „umami-pilze.jpg" zu einem Kochartikel ist keine Anbindung).
NAME_RE = re.compile(r"(?:^|[-_.])umami(?:[-_.]|$)", re.IGNORECASE)
# Fuer die Schwaerzung: jede Nennung des Namens, ohne Wortgrenze (Dienst,
# Skript, Datei, Konfiguration) - so bleibt der Befund namenlos.
NAME_FREI_RE = re.compile(r"umami", re.IGNORECASE)
TEXT_ENDUNGEN = {".py", ".js", ".mjs", ".cjs", ".ts", ".json", ".yaml", ".yml", ".toml",
                 ".html", ".md", ".txt", ".sh", ".css", ".xml", ".patch", ".csv"}

# Wo das bloße Wort verboten ist: überall, außer in redaktionellen Zonen.
EDITORIAL = ("content/", "data/")
# Im gebauten Baum: das Wort nur dort verbieten, wo Besucher CODE laden.
GEBAUT_WORT_ENDUNGEN = {".js", ".mjs", ".css", ".map", ".webmanifest"}
GEBAUT_TEXT_ENDUNGEN = TEXT_ENDUNGEN | {".map", ".webmanifest", ".svg"}

MAX_BYTES = 2_000_000          # größere Dateien sind keine Quelltexte
NICHT_DURCHSUCHEN = {".git", "node_modules", "public", "resources", ".cache", ".venv",
                     "__pycache__", ".pytest_cache", ".mypy_cache"}

# ---------------------------------------------------------------- Zonen

# HISTORISCH: Das Gedächtnis des Repos. Wird nicht gescannt.
HISTORISCH = (
    re.compile(r"^docs/archiv/"),
    re.compile(r"^[A-Za-z0-9._-]*-20\d\d-\d\d-\d\d[A-Za-z0-9._-]*\.(?:md|patch)$"),   # datierte Berichte (Root)
    re.compile(r"^docs/[A-Za-z0-9._-]*-20\d\d-\d\d-\d\d[A-Za-z0-9._-]*\.(?:md|patch)$"),  # datierte Berichte (docs/)
    re.compile(r"^docs/awin-entfernung-workflows\.patch$"),      # Patch-Archiv: Kontextzeilen des damaligen Standes
    re.compile(r"^data/.*\.jsonl$"),                              # append-only Ledger und Protokolle
)

# GENERIERT: Pfad → Grund. Momentaufnahmen, die ein Bot-Lauf komplett neu schreibt.
GENERIERT = {
    "COCKPIT.md":
        "Cockpit-Seite des letzten Laufs (scripts/cockpit.py, täglich) – wird komplett neu geschrieben.",
    "data/cockpit_status.json":
        "Maschinenlesbare Cockpit-Momentaufnahme (scripts/cockpit.py, täglich) – wird komplett neu geschrieben.",
    "data/governance_status.json":
        "Ledger des letzten Governance-Laufs (scripts/governance_gate.py, wöchentlich; --reset leert es zu Laufbeginn).",
    "docs/GOVERNANCE-KONTRAKT.md":
        "Vertrags-Report (scripts/governance_contract.py --md) - wird bei jedem Lauf "
        "vollstaendig neu geschrieben; sein Inhalt stammt aus den gescannten "
        "Quellen. Ihn selbst zu scannen waere die Rueckkopplung: Der Befund "
        "stuende dann in der Datei, die er meldet (#806).",
}

# ERLAUBT: Pfad → Grund. Jede Ausnahme muss einen Fund decken, sonst ist sie ein
# Befund (F5). Neue Einträge brauchen einen Grund, der vor einem Menschen besteht.
ERLAUBT = {
    "scripts/fremdmessung_sperre.py":
        "Die Sperre selbst: ihre Muster und ihr Selbsttest nennen den Gegenstand.",
    "scripts/tests/test_fremdmessung_sperre.py":
        "Sabotage-Proben der Sperre: sie müssen den Gegenstand enthalten, um ihn zu finden.",
    "docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md":
        "Runbook der Sperre: erklärt, was verboten ist und warum.",
    "CLAUDE.md":
        "Dauervorgabe „Keine Fremdmessung“: das Regelwerk benennt den Gegenstand.",
    "scripts/newsletter_qa.py":
        "Q19 ist eine SPERRLISTE für Tracker im Newsletter – sie verbietet den Namen, statt ihn zu benutzen.",
    "scripts/tests/test_datenschutz_freigabe.py":
        "Absenz-Test: beweist, dass Konfiguration, Layouts und Rechtstext den Gegenstand NICHT enthalten.",
    "scripts/tests/test_dom_audit.py":
        "Absenz-Test: beweist, dass Head und Fußskripte keinen Loader des Gegenstands tragen.",
    "scripts/tests/test_suche_pagefind.py":
        "Absenz-Test: das Such-Skript darf den Gegenstand nicht ansprechen.",
    "layouts/_default/_markup/render-link.html":
        "KRITISCH gesiegelt: zwei Kommentarzeilen aus der Zeit vor der Entfernung. Eine Änderung braucht die "
        "menschliche Neu-Signatur (python3 scripts/integrity_guard.py --set-current). Beim nächsten Siegel-"
        "Termin Kommentare bereinigen und DIESEN Eintrag löschen (F5 erinnert daran).",
    "scripts/check24_links.yaml":
        "KRITISCH gesiegelt: eine Kommentarzeile (Kanal-Attribution) aus der Zeit vor der Entfernung. "
        "Gleiche Regel wie oben: Neu-Signatur durch den Menschen, danach Eintrag löschen.",
}


# ---------------------------------------------------------------- Dateien einsammeln

def _git_dateien(root: Path):
    """Versionierte UND neue, nicht ignorierte Dateien; None, wenn kein Git-Repo.
    So fällt auch eine frisch angelegte, noch nicht committete Datei auf – im CI
    (sauberer Checkout) sind beide Mengen gleich."""
    try:
        r = subprocess.run(["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
                           cwd=str(root), capture_output=True,
                           timeout=60, check=False)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if r.returncode != 0:
        return None
    teile = [t for t in r.stdout.decode("utf-8", "replace").split("\0") if t]
    return sorted(teile) if teile else None


def _walk_dateien(root: Path):
    out = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in NICHT_DURCHSUCHEN)
        for name in sorted(filenames):
            full = Path(dirpath) / name
            out.append(full.relative_to(root).as_posix())
    return out


def dateien(root: Path):
    """Alle zu prüfenden Pfade (relativ, mit `/`). Bevorzugt `git ls-files`: so
    zählen weder gebaute Verzeichnisse noch lokale Umgebungen als Quelltext.
    Bereits gelöschte, noch indizierte Dateien (Arbeitsbaum) werden übersprungen."""
    liste = _git_dateien(root)
    if liste is None:
        liste = _walk_dateien(root)
    return [p for p in liste if (root / p).is_file()]


def _lies(pfad: Path):
    """Text einer Datei oder None (zu groß, binär, unlesbar)."""
    try:
        if pfad.stat().st_size > MAX_BYTES:
            return None
        daten = pfad.read_bytes()
    except OSError:
        return None
    if b"\x00" in daten[:8192]:
        return None
    return daten.decode("utf-8", "replace")


def _historisch(rel: str) -> bool:
    return any(rx.search(rel) for rx in HISTORISCH)


def _redaktionell(rel: str) -> bool:
    return rel.startswith(EDITORIAL)


def _zeilen(text: str):
    for nr, zeile in enumerate(text.splitlines(), 1):
        yield nr, zeile


def _kurz(zeile: str, m) -> str:
    """Fundstelle als kurzer Ausschnitt (nie die ganze Zeile: keine Geheimnisse ins Log)."""
    a = max(0, m.start() - 24)
    b = min(len(zeile), m.end() + 24)
    return _schwaerze(zeile[a:b].strip()[:90])


def _schwaerze(text: str) -> str:
    """Fundstellen ohne den Namen des entfernten Dienstes.

    Die Wache schreibt ihren Befund in lebende Dateien (Vertrags-Report,
    Issue-Text). Wuerde sie den Namen mitschreiben, erzeugte ihr eigener
    Befund die Spur, die sie verbietet - eine Meldung, die sich selbst
    erzeugt und nie wieder still wird (#806: eine Zeile "Datenlage offen"
    ohne jeden Dienst).
    Der Fund bleibt benannt (Pfad, Zeile, Klasse); nur der Name fehlt.
    """
    return NAME_FREI_RE.sub("[entfernter Dienst]", text)


# ---------------------------------------------------------------- Prüfung

def befunde(root: Path = ROOT, public: Path | None = None, ausnahmen: dict | None = None,
            nur_pfade=None):
    """Alle Funde über den Quelltext (und optional den gebauten Baum).

    `ausnahmen` ersetzt ERLAUBT (Tests), `nur_pfade` beschränkt die Prüfung auf
    eine Pfadliste (Tests). DIESELBE Funktion benutzt der Governance-Vertrag C40 –
    eine zweite Messung wäre die nächste Doppel-Wahrheit."""
    root = Path(root)
    erlaubt = dict(ERLAUBT if ausnahmen is None else ausnahmen)
    funde = []
    getroffen = set()            # Ausnahme-Pfade, die einen Fund gedeckt haben
    pfade = list(nur_pfade) if nur_pfade is not None else dateien(root)

    for rel in pfade:
        if _historisch(rel) or rel in GENERIERT:
            continue
        ist_ausnahme = rel in erlaubt
        treffer = []             # (klasse, stelle, meldung)

        # F1 – der Dateiname selbst
        basis = rel.rsplit("/", 1)[-1]
        ende = os.path.splitext(basis)[1].lower()
        if ende in TEXT_ENDUNGEN and NAME_RE.search(basis):
            treffer.append(("F1-DATEI", "Dateiname",
                            "Datei trägt den Namen des entfernten Dienstes – Skript, Datenstand "
                            "oder Doku gehören nicht (mehr) ins Repo"))
        # Ordner im Pfad (z. B. data/umami/)
        for teil in rel.split("/")[:-1]:
            if NAME_RE.search(teil) and ende in TEXT_ENDUNGEN:
                treffer.append(("F1-DATEI", f"Ordner {teil}/",
                                "Ordner trägt den Namen des entfernten Dienstes"))
                break

        text = _lies(root / rel)
        if text is not None and VORFILTER.search(text):
            wort_erlaubt_hier = not _redaktionell(rel)
            for nr, zeile in _zeilen(text):
                if not VORFILTER.search(zeile):
                    continue
                m = SIGNAL_RE.search(zeile)
                if m:
                    treffer.append(("F2-ANBINDUNG", f"Zeile {nr}",
                                    f"Anbindungs-Merkmal im Text: „{_kurz(zeile, m)}“"))
                elif wort_erlaubt_hier:
                    m = WORT_RE.search(zeile)
                    if m:
                        treffer.append(("F3-ERWAEHNUNG", f"Zeile {nr}",
                                        f"Der Name steht in einer lebenden Datei: „{_kurz(zeile, m)}“"))
        if not treffer:
            continue
        if ist_ausnahme:
            getroffen.add(rel)
            continue
        for klasse, stelle, meldung in treffer[:6]:
            funde.append(Fund(klasse, rel, stelle, meldung))
        if len(treffer) > 6:
            funde.append(Fund(treffer[6][0], rel, "…", f"und {len(treffer) - 6} weitere Fundstelle(n) in dieser Datei"))

    # F5 – Ausnahmen: begründet, vorhanden, nicht veraltet
    if nur_pfade is None:
        for rel, grund in sorted(erlaubt.items()):
            if not str(grund or "").strip():
                funde.append(Fund("F5-AUSNAHME", rel, "Begründung", "Ausnahme ohne Begründung"))
            elif not (root / rel).is_file():
                funde.append(Fund("F5-AUSNAHME", rel, "Pfad", "Ausnahme für eine Datei, die es nicht gibt – Eintrag löschen"))
            elif rel not in getroffen:
                funde.append(Fund("F5-AUSNAHME", rel, "veraltet",
                                  "Ausnahme deckt keinen Fund mehr – Eintrag löschen (ein offenes Tor "
                                  "für eine spätere Rückkehr)"))

    # F4 – der gebaute Baum
    if public is not None:
        funde += befunde_gebaut(Path(public))
    return funde


def befunde_gebaut(public: Path):
    """F4: Was Besucher bekommen. Anbindungs-Merkmale überall; das Wort allein nur
    in Skripten und Stilen (in Artikeltext wäre es Redaktion)."""
    funde = []
    public = Path(public)
    if not public.is_dir():
        return [Fund("F4-GEBAUT", str(public), "Pfad", "gebauter Baum nicht gefunden – erst bauen (hugo --minify)")]
    for dirpath, dirnames, filenames in os.walk(public):
        dirnames[:] = sorted(dirnames)
        for name in sorted(filenames):
            full = Path(dirpath) / name
            ende = full.suffix.lower()
            if ende not in GEBAUT_TEXT_ENDUNGEN:
                continue
            text = _lies(full)
            if text is None or not VORFILTER.search(text):
                continue
            rel = full.relative_to(public).as_posix()
            for nr, zeile in _zeilen(text):
                if not VORFILTER.search(zeile):
                    continue
                m = SIGNAL_RE.search(zeile)
                if m:
                    funde.append(Fund("F4-GEBAUT", rel, f"Zeile {nr}",
                                      f"Anbindungs-Merkmal im gebauten Baum: „{_kurz(zeile, m)}“"))
                elif ende in GEBAUT_WORT_ENDUNGEN:
                    m = WORT_RE.search(zeile)
                    if m:
                        funde.append(Fund("F4-GEBAUT", rel, f"Zeile {nr}",
                                          f"Der Name steht in einem ausgelieferten Skript/Stil: „{_kurz(zeile, m)}“"))
                if len(funde) > 200:
                    return funde
    return funde


# ---------------------------------------------------------------- Ausgabe

def _drucke(funde):
    if not funde:
        print("✅ Fremdmessung-Sperre: keine Spur des entfernten Dienstes – weder in Quelltext noch (falls geprüft) im gebauten Baum.")
        return
    print(f"🛑 Fremdmessung-Sperre: {len(funde)} Fund(e) – der entfernte Dienst ist zurück (oder nie ganz weg):\n")
    for f in funde[:60]:
        print(f"  {f.klasse:<14} {f.pfad}:{f.stelle} – {f.meldung}")
    if len(funde) > 60:
        print(f"  … und {len(funde) - 60} weitere")
    print("\nWas tun: Anbindung entfernen (nicht ausnehmen). Eine Ausnahme nur mit Grund in "
          "scripts/fremdmessung_sperre.py (ERLAUBT) – Runbook: docs/ANLEITUNG-FREMDMESSUNG-SPERRE.md")


# ---------------------------------------------------------------- Selbsttest

def _baum(td: Path, dateien_: dict):
    for rel, inhalt in dateien_.items():
        p = td / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(inhalt, bytes):
            p.write_bytes(inhalt)
        else:
            p.write_text(inhalt, encoding="utf-8")


def _klassen(funde):
    return sorted({f.klasse for f in funde})


def _selftest() -> int:
    fehler = []

    def erwarte(titel, funde, klassen):
        ist = _klassen(funde)
        if ist != sorted(klassen):
            fehler.append(f"{titel}: erwartet {sorted(klassen)}, bekommen {ist} {[tuple(f) for f in funde][:3]}")

    # 1) Sauberer Baum bleibt still – inkl. redaktionellem Wort, Foto, Historie, Binärdatei
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        _baum(td, {
            "scripts/ok.py": "print('nichts zu sehen')\n",
            "layouts/index.html": "<p>kein Tracking</p>\n",
            "content/posts/kochen/index.md": "Pilze liefern Umami – sparsam würzen.\n",   # Geschmacksrichtung
            "static/images/umami-pilze.jpg": b"\xff\xd8\xff\x00binary",                   # Foto, kein Code
            "BERICHT-2026-10-10.md": "Umami Cloud wurde beanstandet. cloud.umami.is\n",   # datierter Bericht
            "docs/archiv/ALT.md": "UMAMI_API_TOKEN war gesetzt\n",                        # Archiv
            "data/audit/2026-09-15.jsonl": '{"step": "umami"}\n',                         # Ledger
            "data/blob.bin": b"UMAMI_API_TOKEN\x00\x01",                                  # binär
        })
        erwarte("sauberer Baum", befunde(td, nur_pfade=sorted(
            str(p.relative_to(td).as_posix()) for p in td.rglob("*") if p.is_file())), [])

    # 2) Jedes Anbindungs-Merkmal wird gefunden (F2) – jeweils einzeln sabotiert
    proben = {
        "Skript-Host": '<script defer src="https://cloud.umami.is/script.js"></script>',
        "Skriptname": '<script src="/umami.js"></script>',
        "Ereignis-Attribut": '<a data-umami-event="affiliate_click">x</a>',
        "Website-ID": '<script data-website-id="abc"></script>',
        "Selbst gehostetes Snippet": '<script async src="https://stats.example.org/s.js" data-website-id="1b2c"></script>',
        "JS-Objekt": "window.umami && umami.track('x')",
        "JS-API": "umami.track('klick')",
        "Secret": "env:\n  UMAMI_API_TOKEN: ${{ secrets.UMAMI_API_TOKEN }}",
        "API-Kopf": "headers = {'x-umami-api-key': k}",
        "Betriebsschalter": "umami_api_import_enabled: false",
        "Hugo-Konfig": "[params.umami]\nwebsiteId = \"\"",
        "Template-Zugriff": "{{ if site.Params.umami.websiteId }}",
        "YAML-Provider": "provider: umami-only",
        "YAML-Analytics": "analytics: umami",
        "Datenstand-Name": "data/umami_clicks.json",
        "Gate-Kennung": "python3 scripts/governance_gate.py --emit umami-views",
    }
    for name, zeile in proben.items():
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, {"scripts/x.py": f"# {zeile}\n"})
            erwarte(f"Merkmal „{name}“ bleibt unentdeckt", befunde(td, nur_pfade=["scripts/x.py"]),
                    ["F2-ANBINDUNG"])
    # … und dasselbe Merkmal in redaktionellen Zonen (content/, data/) – dort gilt nur F2
    for zone in ("content/posts/x/index.md", "data/x.yaml"):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, {zone: '<script src="https://cloud.umami.is/script.js"></script>\n'})
            erwarte(f"Anbindung in {zone} bleibt unentdeckt", befunde(td, nur_pfade=[zone]), ["F2-ANBINDUNG"])

    # 3) F3: das Wort in lebenden technischen Dateien – aber nicht als Redaktion
    for rel in ("docs/ANLEITUNG-X.md", ".github/workflows/x.yml", "layouts/_partials/x.html",
                "static/premium/x.js", "scripts/tool.py", "package.json", "README.md"):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, {rel: "# Hinweis: Umami wird bei uns gemessen\n"})
            erwarte(f"Erwähnung in {rel}", befunde(td, nur_pfade=[rel]), ["F3-ERWAEHNUNG"])
    for rel in ("content/posts/x/index.md", "data/themen.yaml", "data/research/brief.md"):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, {rel: "Umami als fünfte Grundgeschmacksrichtung.\n"})
            erwarte(f"redaktionelles Wort in {rel} wird fälschlich gemeldet", befunde(td, nur_pfade=[rel]), [])

    # 4) F1: Dateiname (Code/Daten/Doku ja, Foto nein)
    for rel, soll in (("scripts/umami_clicks.py", ["F1-DATEI"]), ("data/umami_views.meta.json", ["F1-DATEI"]),
                      ("docs/ANLEITUNG-UMAMI-ANALYTICS.md", ["F1-DATEI"]), ("data/umami/x.json", ["F1-DATEI"]),
                      ("static/images/umami-pilze.webp", []), ("scripts/umamiser.py", [])):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, {rel: "# leer\n" if rel.endswith((".py", ".md")) else "{}\n"})
            erwarte(f"Dateiname {rel}", befunde(td, nur_pfade=[rel]), soll)

    # 5) HISTORISCH wird nicht gescannt – aber ein ähnlich benannter LEBENDER Pfad schon
    for rel, soll in (("AUDIT-2026-10-10.md", []), ("docs/archiv/X.md", []), ("docs/X-2026-09-26.md", []),
                      ("docs/awin-entfernung-workflows.patch", []), ("data/audit/2026-10-19.jsonl", []),
                      ("AUDIT.md", ["F3-ERWAEHNUNG"]), ("docs/X.md", ["F3-ERWAEHNUNG"]),
                      ("data/x.json", ["F2-ANBINDUNG"])):
        with tempfile.TemporaryDirectory() as t:
            td = Path(t)
            _baum(td, {rel: ("Umami" if soll != ["F2-ANBINDUNG"] else "UMAMI_API_TOKEN") + " steht hier\n"})
            erwarte(f"Zone {rel}", befunde(td, nur_pfade=[rel]), soll)

    # 5b) GENERIERT: Momentaufnahmen des letzten Laufs werden nicht gescannt
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        _baum(td, {"COCKPIT.md": "Umami-Daten noch nicht importiert\n",
                   "data/governance_status.json": '{"report": "data/umami_clicks.meta.json"}\n',
                   "data/cockpit_status.json": "UMAMI_API_TOKEN\n",
                   "docs/COCKPIT.md": "Umami\n"})                       # anderer Pfad: gescannt
        erwarte("generierte Momentaufnahmen", befunde(td, nur_pfade=sorted(
            str(p.relative_to(td).as_posix()) for p in td.rglob("*") if p.is_file())), ["F3-ERWAEHNUNG"])

    # 6) Ausnahmen: gedeckter Fund still, veraltete/unbegründete/fehlende laut (F5)
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        _baum(td, {"a.py": "# Umami bleibt hier erwähnt\n", "b.py": "# sauber\n", "c.py": "# Umami\n"})
        ok = befunde(td, ausnahmen={"a.py": "Absenz-Test", "b.py": "alt", "c.py": ""}, nur_pfade=None)
        erwarte("veraltet/unbegründet", [f for f in ok if f.pfad in ("b.py", "c.py")], ["F5-AUSNAHME"])
        if sum(1 for f in ok if f.pfad == "b.py" and "veraltet" in f.stelle) != 1:
            fehler.append("eine Ausnahme ohne Fund (b.py) wird nicht als veraltet gemeldet")
        if any(f.pfad == "a.py" for f in ok):
            fehler.append("eine gedeckte Ausnahme (a.py) wird trotzdem gemeldet")
        if not any(f.pfad == "c.py" and f.klasse == "F5-AUSNAHME" for f in ok):
            fehler.append("eine Ausnahme ohne Begründung (c.py) bleibt unbeanstandet")
        weg = befunde(td, ausnahmen={"gibt-es-nicht.py": "Grund"}, nur_pfade=None)
        if not any(f.klasse == "F5-AUSNAHME" and f.pfad == "gibt-es-nicht.py" for f in weg):
            fehler.append("Ausnahme für eine fehlende Datei bleibt unbeanstandet")
        # eine Ausnahme deckt NICHT eine zweite, fremde Datei
        if not any(f.pfad == "c.py" and f.klasse == "F3-ERWAEHNUNG" for f in
                   befunde(td, ausnahmen={"a.py": "Grund"}, nur_pfade=None)):
            fehler.append("Ausnahme für a.py deckt fälschlich auch c.py")

    # 7) Gebauter Baum (F4): Anbindung überall, das Wort nur in Skript/Stil
    with tempfile.TemporaryDirectory() as t:
        td = Path(t)
        _baum(td, {
            "index.html": "<p>Umami ist eine Geschmacksrichtung.</p>\n",
            "posts/x/index.html": "<p>Mehr zu Umami im Essen.</p>\n",
            "feed.xml": "<item><title>Umami</title></item>\n",
            "premium/ok.js": "console.log('ok');\n",
            "bild.avif": b"\x00\x01UMAMI_API_TOKEN",
        })
        erwarte("gebauter Baum, redaktionelles Wort", befunde_gebaut(td), [])
        _baum(td, {"premium/leck.js": "/* kein Umami (Kommentar landet im Browser) */\n"})
        erwarte("Name in ausgeliefertem Skript", befunde_gebaut(td), ["F4-GEBAUT"])
        (td / "premium/leck.js").unlink()
        _baum(td, {"premium/stil.css": "/* Umami */ a{color:red}\n"})
        erwarte("Name in ausgeliefertem Stil", befunde_gebaut(td), ["F4-GEBAUT"])
        (td / "premium/stil.css").unlink()
        _baum(td, {"x/index.html": '<script defer src="https://cloud.umami.is/script.js"></script>\n'})
        erwarte("Loader im gebauten HTML", befunde_gebaut(td), ["F4-GEBAUT"])
        (td / "x/index.html").unlink()
        _baum(td, {"y/index.html": '<a data-umami-event="affiliate_click" href="/go/x/">x</a>\n'})
        erwarte("Ereignis-Attribut im gebauten HTML", befunde_gebaut(td), ["F4-GEBAUT"])
        erwarte("fehlender Baum", befunde_gebaut(td / "gibt-es-nicht"), ["F4-GEBAUT"])

    # 8) Die Ausnahmen selbst: alle begründet, keine Wildcards, keine historischen Pfade
    for rel, grund in ERLAUBT.items():
        if len(str(grund).strip()) < 20:
            fehler.append(f"ERLAUBT[{rel}] hat keinen tragfähigen Grund")
        if any(c in rel for c in "*?[]"):
            fehler.append(f"ERLAUBT[{rel}]: Wildcards sind verboten (jede Ausnahme einzeln)")
        if _historisch(rel):
            fehler.append(f"ERLAUBT[{rel}]: historische Pfade werden ohnehin nicht gescannt")
    for rel, grund in GENERIERT.items():
        if len(str(grund).strip()) < 20:
            fehler.append(f"GENERIERT[{rel}] hat keinen tragfähigen Grund")
        if any(c in rel for c in "*?[]") or rel in ERLAUBT or _historisch(rel):
            fehler.append(f"GENERIERT[{rel}]: Wildcard, Doppelung oder historischer Pfad")
    # 9) Das Selbstbild: die eigene Wache steht in ERLAUBT (sonst fände sie sich selbst)
    if "scripts/fremdmessung_sperre.py" not in ERLAUBT:
        fehler.append("die Sperre nimmt sich nicht selbst aus und fände sich selbst")

    if fehler:
        print("❌ FREMDMESSUNG-SPERRE-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print("   -", f)
        return 2
    print(f"✅ FREMDMESSUNG-SPERRE-SELBSTTEST bestanden ({len(proben)} Anbindungs-Merkmale einzeln, "
          "redaktionelles Wort erlaubt, Dateinamen, Historie, Ausnahmen begründet+alternd, gebauter Baum).")
    return 0


# ---------------------------------------------------------------- main

def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    public = None
    if "--public" in argv:
        i = argv.index("--public")
        if i + 1 >= len(argv) or argv[i + 1].startswith("-"):
            print("🛑 --public erwartet ein Verzeichnis, z. B. --public public/")
            return 2
        public = Path(argv[i + 1])
    funde = befunde(ROOT, public=public)
    if "--json" in argv:
        print(json.dumps([f._asdict() for f in funde], ensure_ascii=False, indent=2))
    else:
        _drucke(funde)
    return 1 if funde else 0


if __name__ == "__main__":
    sys.exit(main())
