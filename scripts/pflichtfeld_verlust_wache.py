#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
pflichtfeld_verlust_wache.py – kein Automatik-Commit verliert ein Pflichtfeld
===========================================================================

BEFUND 06.11.2026 (#1110, Content-Bot `0b55fca`)
----------------------------------------------
Der Ökostrom-Artikel ging ohne `kurzantwort` live (Metadaten-Wache M4). Die
Ursache war KEIN fehlender Texter, sondern ein Verlust beim Schreiben: Der
Gate-Heilungs-Commit des Deploy-Laufs (`fix(gate): Kadenz-/Titel-/Cover-
Heilungen vor Veröffentlichung`, Content-Bot) schrieb den Frontmatter-Block
neu und ließ ein Pflichtfeld fallen, das im letztenCommit noch stand.

Die Nachlauf-Wache (`veroeffentlichungs_wache.py`) MELDET diese Klasse nach
der Veröffentlichung – aber sie heilt nicht, und sie steht nicht im Deploy-
Pfad. Zwischen dem Schreibverlust und der Meldung liegt die Auslieferung:
Der Artikel ist live, das Feld fehlt, und kein Schritt im selben Lauf hält
den Verlust auf. Genau das ist die Lücke, die #1110 dauerhaft schließt.

DIE DREI SÄTZE DIESES GATES
---------------------------
1. **Verlust ist messbar, nicht geraten.** Ein Pflichtfeld gilt als verloren,
   wenn es im letzten Commit (`HEAD`) stand und im Arbeitsbaum jetzt fehlt –
   und die Metadaten-Wache (M4, importiert, nicht kopiert) den Verlust als
   Befund bestätigt. Welche Felder Pflicht sind, beweist der Selbsttest gegen
   M4; das Gate erfindet keine zweite Liste.
2. **Heilen heißt zitieren, nicht erfinden.** Verlorene Felder werden
   **bytegenau aus `HEAD` zurückgeholt** – der zuletzt redaktionell committed
   Stand. Der Artikeltext (Body) bleibt dabei bytegleich; nur das fehlende
   Feld wird vor die schließende Frontmatter-Grenze gesetzt. Stand `HEAD`
   das Feld auch nicht, wird NICHTS erfunden: der Befund bleibt gemeldet und
   gehört der Redaktion (bzw. dem Texter `generate_kurzantworten.py`).
3. **Kein Befund nimmt einen Artikel offline (C34).** Das Gate heilt vor dem
   Commit und meldet den Rest; es blockiert die Auslieferung nicht. Es steht
   im Deploy-Pfad VOR „Gate-Heilungen committen“, damit der Content-Bot den
   Verlust gar nicht erst festschreibt.

Damit ist die Fehlerklasse an der Quelle geschlossen – gleichgültig, welcher
Schreiber (Titel-, Cover-, Keyword-, Meta-KI oder ein künftiger Merge) das
Feld fallen lässt: Was `HEAD` an Pflichtfeldern trug, überlebt den Lauf.

NUTZUNG
    python3 scripts/pflichtfeld_verlust_wache.py                 # prüfen (lesend)
    python3 scripts/pflichtfeld_verlust_wache.py --fix           # aus HEAD zurückholen
    python3 scripts/pflichtfeld_verlust_wache.py --json
    python3 scripts/pflichtfeld_verlust_wache.py --pfad content/posts/x/index.md
    python3 scripts/pflichtfeld_verlust_wache.py --selftest

EXIT: 0 = kein offener Verlust (oder geheilt) · 1 = offener Verlust (HEAD trug
      das Feld nicht – Redaktion/Texter) · 2 = Selbsttest rot oder Grundlage
      (Git/Metadaten-Wache) nicht verfügbar – fail-closed, nie „grün aus Unwissen“.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

# Die beiden Quellen der Wahrheit, die dieses Gate NICHT nachbaut:
#   * metadaten_wache.py  – was ein Pflichtfeld ist (M4), Frontmatter lesen
#   * post_utils.py       – die kanonische Naht (split_article / doppel_freies_feld)
# Fällt eine aus, ist das Gate rot (Exit 2), nicht grün (#661: „ungeprüft“ darf
# nie wie „heil“ aussehen).
SSOT_FEHLER = ""
try:
    import metadaten_wache as mw            # noqa: E402
    import post_utils as pu                 # noqa: E402
except Exception as exc:                     # pragma: no cover – Ausfallpfad
    mw = None                                # type: ignore[assignment]
    pu = None                                # type: ignore[assignment]
    SSOT_FEHLER = f"{exc.__class__.__name__}: {exc}"


# Pflichtfelder je Seitenart. Der Selbsttest pinnt diese Liste gegen M4:
# jedes Feld hier MUSS einen M4-Befund auslösen, wenn es fehlt (sonst wäre die
# Liste eine zweite Wahrheit). `cover` steht für `cover.image`/`cover.alt`.
PFLICHT_POSTS = ("kurzantwort", "quellen", "faktencheck", "cover")
PFLICHT_PILLAR = ("quellen",)

SCHLUENZE = ("kurzantwort", "quellen", "faktencheck", "cover")


def _grundlage(root: str) -> tuple[bool, str]:
    """Die Messgrundlage muss WIRKLICH tragen – sonst Exit 2, nie Grün.

    Zwei stille Ausfälle würden sonst wie „alles heil“ aussehen (C2/C33):
      * PyYAML fehlt: `metadaten_wache` importiert trotzdem (yaml = None) und
        sein Leser gibt nur noch None zurück – jede Datei sähe verlustfrei aus.
      * Git fehlt / kein HEAD: jede Datei sähe wie eine NEUE Datei aus (keine
        Basis), also ebenfalls verlustfrei.
    Darum wird die Grundlage geprüft, nicht vorausgesetzt – inklusive einer
    Wirksamkeitsprobe am Leser statt eines bloßen Import-Urteils.
    """
    if mw is None or pu is None:
        return False, SSOT_FEHLER or "SSOT-Import ausgefallen"
    if getattr(mw, "yaml", None) is None:
        return False, "PyYAML fehlt – Frontmatter ist nicht lesbar (C2/C33)"
    probe_fm, _ = mw.split_frontmatter('---\nkurzantwort: "x"\n---\n\nText\n')
    if not isinstance(probe_fm, dict) or probe_fm.get("kurzantwort") != "x":
        return False, "Frontmatter-Leser liest nicht (SSOT-Wirksamkeitsprobe rot)"
    try:
        kopf = subprocess.run(["git", "rev-parse", "--verify", "HEAD"], cwd=root,
                              capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return False, f"Git nicht ausführbar ({exc.__class__.__name__}) – keine Basis"
    if kopf.returncode != 0 or not kopf.stdout.strip():
        return False, "kein Git-HEAD – ohne Basis ist kein Verlust messbar"
    return True, ""


def _git_head_text(root: str, rel: str) -> str | None:
    """Der committed Stand (`HEAD`) einer Datei – oder None (neue Datei).

    None heißt: es gibt nichts zurückzuholen. Das Gate erfindet dann nichts,
    sondern meldet den Befund der Redaktion/dem Texter.
    """
    try:
        proc = subprocess.run(
            ["git", "show", f"HEAD:{rel}"], cwd=root,
            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode != 0:
        return None
    return proc.stdout


def _fm_span(lines: list[str]) -> tuple[int, int] | None:
    """(start, end) des Frontmatter-Bereichs in Zeilen – end = Index der
    schließenden `---`-Grenze. Wie post_utils/park_state: die erste Grenze
    nach der Öffnung beendet das Frontmatter (Hugo-Sicht)."""
    if not lines or lines[0].strip() != "---":
        return None
    for i in range(1, len(lines)):
        if lines[i].startswith("---"):
            return (1, i)
    return None


def _block_grenzen(lines: list[str], key: str) -> tuple[int, int] | None:
    """EINE Blockgrenzen-Wahrheit: [start, ende) eines Top-Level-Feldes.

    Zum Feld gehören die Schlüsselzeile und jede eingerückte Fortsetzung
    (Blockliste, nested map). Leerzeilen zählen nur mit, wenn danach noch
    eingerückter Inhalt folgt; abschließende Leerzeilen gehören nicht dazu.
    Genutzt von Lesen (`_feld_block`) UND Ersetzen – zwei Scanner würden
    genau den Fall auseinanderlaufen lassen, den #1110 gezeigt hat.
    """
    start = None
    muster = re.compile(rf"^{re.escape(key)}:")
    for i, zeile in enumerate(lines):
        if muster.match(zeile):
            start = i
            break
    if start is None:
        return None
    ende = start + 1
    while ende < len(lines):
        zeile = lines[ende]
        if zeile.strip() == "":
            nxt = ende + 1
            if (nxt < len(lines) and lines[nxt][:1] in (" ", "\t")
                    and lines[nxt].strip()):
                ende += 1
                continue
            break
        if zeile[:1] in (" ", "\t"):
            ende += 1
            continue
        break
    while ende > start + 1 and lines[ende - 1].strip() == "":
        ende -= 1
    return start, ende


def _feld_block(fm_text: str, key: str) -> list[str] | None:
    """Die ROHEN Zeilen eines Top-Level-Feldes aus einem Frontmatter-Block.

    Erhalt der exakten Schreibweise (Quotes, Einzug, Blockliste) – darum wird
    aus dem Text zitiert, nicht aus einem yaml.dump (das würde die Formatierung
    und damit ggf. das Prüf-Siegel verändern). None, wenn das Feld nicht steht.
    """
    lines = fm_text.split("\n")
    grenzen = _block_grenzen(lines, key)
    if grenzen is None:
        return None
    start, ende = grenzen
    return lines[start:ende]


def _ersetze_feld(fm_lines: list[str], key: str,
                  block: list[str]) -> list[str]:
    """Setzt das Feld AN SEINE STELLE – ersetzt statt anzuhängen.

    Wichtig für den Fall „Schlüssel steht noch, ist aber leer geleert“:
    `doppel_freies_feld` behält die ERSTE Zeile, ein bloßes Anhängen würde
    also genau die leere Fassung überleben lassen. Darum wird der vorhandene
    Block entfernt und der HEAD-Block an dieselbe Position gesetzt.
    """
    grenzen = _block_grenzen(fm_lines, key)
    if grenzen is None:
        # Feld fehlt ganz: ans Ende des Frontmatter-Blocks, vor die Grenze.
        ende = len(fm_lines)
        while ende > 0 and fm_lines[ende - 1].strip() == "":
            ende -= 1
        return fm_lines[:ende] + block + fm_lines[ende:]
    start, ende = grenzen
    return fm_lines[:start] + block + fm_lines[ende:]


def _feld_steht(fm: dict | None, key: str) -> bool:
    """Trägt das Frontmatter ein nicht-leeres Pflichtfeld? (M4-Semantik)."""
    if not isinstance(fm, dict):
        return False
    wert = fm.get(key)
    if key == "cover":
        return bool(isinstance(wert, dict) and (wert.get("image") or "").strip())
    if key == "quellen":
        return bool(wert)
    if isinstance(wert, str):
        return bool(wert.strip())
    return wert is not None and wert != ""


def _pflichtfelder(rel: str) -> tuple[str, ...]:
    if "/posts/" in rel.replace(os.sep, "/"):
        return PFLICHT_POSTS
    if "/pillar/" in rel.replace(os.sep, "/"):
        return PFLICHT_PILLAR
    return ()


def _m4_befunde(rel: str, text: str) -> set[str]:
    """M4-Befundmeldungen der importierten Wache (SSOT). None bei Ausfall."""
    if mw is None:
        return set()
    return {f["msg"] for f in mw.check_document(rel, text) if f.get("rule") == "M4"}


def verluste(rel: str, head_text: str | None, work_text: str) -> list[dict]:
    """Reine Verlust-Erkennung (ohne Schreiben) – testbar ohne Dateisystem.

    Ein Verlust liegt vor, wenn HEAD das Pflichtfeld trug, der Arbeitsbaum es
    nicht mehr trägt UND M4 den Verlust bestätigt. `rueckholbar` sagt, ob HEAD
    den Roh-Block liefert (dann heilt --fix bytegenau; sonst Redaktion).
    """
    if mw is None or pu is None or head_text is None:
        return []
    pflicht = _pflichtfelder(rel)
    if not pflicht:
        return []
    work_fm, _ = mw.split_frontmatter(work_text)
    head_fm, _ = mw.split_frontmatter(head_text)
    if work_fm is None or head_fm is None:
        return []
    # Nur veröffentlichte Inhalte: ein Entwurf ist kein Live-Verlust.
    if not mw._is_published(work_fm):
        return []
    work_m4 = _m4_befunde(rel, work_text)
    out = []
    for key in pflicht:
        if _feld_steht(head_fm, key) and not _feld_steht(work_fm, key):
            block = _feld_block(_fm_roh(head_text), key)
            # M4 muss den Verlust bestätigen (zweite Wahrheit ausgeschlossen):
            # fehlt das Feld, meldet M4 es. Bestätigt M4 nicht, ist es kein
            # M4-Pflichtverlust und wird hier nicht angefasst.
            bestaetigt = bool(work_m4)
            out.append({
                "datei": rel, "feld": key,
                "rueckholbar": block is not None,
                "m4": sorted(work_m4),
                "bestaetigt": bestaetigt,
            })
    return out


def _fm_roh(text: str) -> str:
    """Der Frontmatter-Rohblock (ohne die beiden Grenzen) über die Naht-SSOT."""
    _prefix, fm, _body = pu.split_article(text)
    return fm


def heile_datei(rel: str, head_text: str | None, work_text: str) -> tuple[str, list[dict]]:
    """Holt verlorene, rückholbare Pflichtfelder bytegenau aus HEAD zurück.

    Beweis vor dem Schreiben (alles oder nichts je Feld):
      * der Body bleibt bytegleich (nur das Feld wird ergänzt),
      * das Feld steht danach nicht-leer,
      * M4 bestätigt den Verlust nicht mehr,
      * es entsteht kein doppelter Schlüssel (doppel_freies_feld).
    """
    funde = verluste(rel, head_text, work_text)
    if not funde or head_text is None:
        return work_text, []
    head_fm_roh = _fm_roh(head_text)
    text = work_text
    geheilt = []
    for fund in funde:
        if not fund["rueckholbar"] or not fund["bestaetigt"]:
            continue
        key = fund["feld"]
        block = _feld_block(head_fm_roh, key)
        if not block:
            continue
        lines = text.split("\n")
        span = _fm_span(lines)
        if span is None:
            continue
        fm_start, fm_ende = span
        # Nur der Frontmatter-Block wird angefasst; alles ab der schließenden
        # Grenze (der Body) bleibt Zeile für Zeile stehen. Ersetzt statt
        # angehängt, damit eine leer geräumte Fassung nicht überlebt.
        fm_lines = _ersetze_feld(lines[fm_start:fm_ende], key, block)
        kandidat = "\n".join(lines[:fm_start] + fm_lines + lines[fm_ende:])
        # Sicherheit gegen einen doch vorhandenen Restschlüssel: genau EIN
        # Top-Level-Feld (Naht-SSOT), Body unverändert.
        prefix, fm_neu, body = pu.split_article(kandidat)
        fm_neu = pu.doppel_freies_feld(fm_neu, key)
        kandidat = pu.join_article(fm_neu, body, prefix)
        # Beweis 1: Body bytegleich (Naht-SSOT normalisiert identisch).
        if pu.split_article(kandidat)[2] != pu.split_article(text)[2]:
            continue
        # Beweis 2: Feld steht jetzt nicht-leer.
        neu_fm, _ = mw.split_frontmatter(kandidat)
        if not _feld_steht(neu_fm, key):
            continue
        # Beweis 3: echte Verbesserung – die M4-Befundmenge schrumpft strikt.
        # Kein Fortschritt → nicht schreiben (das Feld bleibt gemeldet).
        if not (_m4_befunde(rel, kandidat) < _m4_befunde(rel, text)):
            continue
        text = kandidat
        geheilt.append({"datei": rel, "feld": key, "quelle": "HEAD"})
    return text, geheilt


def sammle_dateien(root: str, pfade: list[str] | None = None) -> list[str]:
    """Content-Dateien (posts + pillar) als repo-relative Pfade."""
    import glob
    if pfade:
        return [os.path.relpath(p, root) if os.path.isabs(p) else p for p in pfade]
    rels = []
    for pattern in ("content/posts/*/index.md", "content/posts/*.md",
                    "content/pillar/*/index.md"):
        for path in glob.glob(os.path.join(root, pattern)):
            if os.path.basename(path) == "_index.md":
                continue
            rels.append(os.path.relpath(path, root))
    return sorted(set(rels))


def lauf(root: str = ROOT, fix: bool = False,
         pfade: list[str] | None = None) -> dict:
    """Prüft (und heilt optional) den Bestand. Reine Berichtsfunktion."""
    tragfaehig, grund = _grundlage(root)
    if not tragfaehig:
        return {"grundlage": False, "fehler": grund,
                "verluste": [], "geheilt": [], "offen": []}
    verlust_funde: list[dict] = []
    geheilt: list[dict] = []
    offen: list[dict] = []
    for rel in sammle_dateien(root, pfade):
        pfad = os.path.join(root, rel)
        try:
            with open(pfad, encoding="utf-8") as fh:
                work_text = fh.read()
        except OSError:
            continue
        head_text = _git_head_text(root, rel)
        funde = verluste(rel, head_text, work_text)
        if not funde:
            continue
        if fix:
            neu, heals = heile_datei(rel, head_text, work_text)
            if heals:
                with open(pfad, "w", encoding="utf-8") as fh:
                    fh.write(neu)
                geheilt += heals
            # Rest nach der Heilung neu bewerten
            rest = verluste(rel, head_text, neu)
        else:
            rest = funde
        for f in rest:
            verlust_funde.append(f)
            if not f["rueckholbar"]:
                offen.append(f)
    return {
        "grundlage": True,
        "verluste": verlust_funde,
        "geheilt": geheilt,
        "offen": offen,
        "geprueft": len(sammle_dateien(root, pfade)),
    }


def bericht_text(bericht: dict) -> str:
    if not bericht.get("grundlage"):
        return (f"🛑 Pflichtfeld-Verlust-Wache: Grundlage fehlt "
                f"({bericht.get('fehler')}) – fail-closed.")
    zeilen = []
    if bericht["geheilt"]:
        zeilen.append(f"✅ {len(bericht['geheilt'])} Pflichtfeld(er) aus HEAD zurückgeholt:")
        for g in bericht["geheilt"]:
            zeilen.append(f"   · {g['feld']} → {g['datei']}")
    if bericht["offen"]:
        zeilen.append(f"🛑 {len(bericht['offen'])} offener Verlust (HEAD trug das Feld "
                      "nicht – Redaktion/Texter, kein Erfinden):")
        for o in bericht["offen"]:
            zeilen.append(f"   · {o['feld']} fehlt in {o['datei']}")
    if not zeilen:
        zeilen.append(f"✅ Pflichtfeld-Verlust-Wache grün: {bericht.get('geprueft', 0)} "
                      "Dateien, kein Pflichtfeld gegenüber HEAD verloren.")
    return "\n".join(zeilen)


# ---------------------------------------------------------------------------
#  Selbsttest: Sabotage-Proben gegen einen synthetischen Git-Bestand.
# ---------------------------------------------------------------------------
def _run_selftest() -> int:
    import tempfile
    if mw is None or pu is None:
        print(f"🛑 Selbsttest: Grundlage fehlt ({SSOT_FEHLER}).")
        return 2
    fehler: list[str] = []

    def fest(name, bedingung):
        if not bedingung:
            fehler.append(name)

    # M4 pinnt die Pflichtliste: jedes Feld löst einen M4-Befund aus, wenn es fehlt.
    gut = (
        '---\n'
        'title: "Ökostrom wechseln: sicher und grün"\n'
        'description: "So wechselst du den Ökostrom-Anbieter sicher, grün und '
        'bezahlbar – mit geprüften Siegeln und einem klaren Ablauf."\n'
        'date: 2026-10-28T06:00:00Z\n'
        'draft: false\n'
        'kurzantwort: "Ein Wechsel ist jederzeit möglich; echte Ökotarife '
        'erkennst du an Siegeln wie Grüner Strom oder ok-power."\n'
        'quellen:\n'
        '  - id: "Q1"\n'
        '    titel: "Bundesnetzagentur"\n'
        '    url: "https://www.bundesnetzagentur.de/x"\n'
        'cover:\n'
        '  image: "images/covers/probe.jpg"\n'
        '  alt: "Ökostrom wechseln"\n'
        'faktencheck: 2026-10-28\n'
        '---\n\n'
        'Ein echter Artikeltext mit genug Substanz für die Prüfung.\n'
    )
    rel = "content/posts/2026-10-28-probe/index.md"
    fest("S0 gut hat kein M4", not _m4_befunde(rel, gut))
    for key in PFLICHT_POSTS:
        block = _feld_block(_fm_roh(gut), key)
        fest(f"S1 Pflichtfeld {key} extrahierbar", bool(block))
        # Feld aus dem Gut-Text entfernen → M4 muss es melden
        ohne = gut.replace("\n".join(block) + "\n", "", 1)
        fest(f"S2 M4 pinnt {key}", bool(_m4_befunde(rel, ohne)))
        # Verlusterkennung: HEAD=gut, work=ohne → genau dieses Feld verloren
        v = verluste(rel, gut, ohne)
        fest(f"S3 Verlust erkannt {key}",
             any(x["feld"] == key and x["rueckholbar"] for x in v))
        # Heilung holt es bytegenau zurück, Body bleibt gleich
        neu, heals = heile_datei(rel, gut, ohne)
        fest(f"S4 Heilung {key}", any(h["feld"] == key for h in heals))
        fest(f"S5 Feld wieder da {key}", _feld_steht(mw.split_frontmatter(neu)[0], key))
        fest(f"S6 Body bytegleich {key}",
             pu.split_article(neu)[2] == pu.split_article(ohne)[2])
        fest(f"S7 M4 geheilt {key}", not _m4_befunde(rel, neu))
        fest(f"S8 kein Doppelschlüssel {key}",
             len(re.findall(rf"(?m)^{re.escape(key)}:", _fm_roh(neu))) == 1)

    # Idempotenz: zweimal heilen ändert nichts mehr
    ohne_kz = gut.replace("\n".join(_feld_block(_fm_roh(gut), "kurzantwort")) + "\n", "", 1)
    einmal, _ = heile_datei(rel, gut, ohne_kz)
    zweimal, heals2 = heile_datei(rel, gut, einmal)
    fest("S9 idempotent", einmal == zweimal and not heals2)

    # Kein Erfinden: HEAD trägt das Feld selbst nicht → nicht rückholbar, offen
    head_ohne = ohne_kz
    v = verluste(rel, head_ohne, ohne_kz)
    fest("S10 kein Verlust wenn HEAD auch fehlt", not v)

    # Entwurf ist kein Live-Verlust
    entwurf = ohne_kz.replace("draft: false", "draft: true", 1)
    fest("S11 Entwurf verschont", not verluste(rel, gut, entwurf))

    # Andere Felder bleiben erhalten (Title-Heilung darf nicht zurückgedreht werden)
    work = ohne_kz.replace('title: "Ökostrom wechseln: sicher und grün"',
                           'title: "Ökostrom wechseln: sicher, grün, bezahlbar"', 1)
    neu, _ = heile_datei(rel, gut, work)
    fest("S12 fremde Änderung bleibt",
         'title: "Ökostrom wechseln: sicher, grün, bezahlbar"' in neu)

    # Leer geräumtes Feld: ERSETZEN statt anhängen. `doppel_freies_feld`
    # behält die ERSTE Zeile – ein bloßer Anhänger ließe die leere Fassung
    # überleben und der Verlust bliebe unsichtbar geheilt.
    geleert = ohne_kz.replace("quellen:\n", 'kurzantwort: ""\nquellen:\n', 1)
    neu_g, heals_g = heile_datei(rel, gut, geleert)
    fest("S16 leeres Feld ersetzt",
         any(h["feld"] == "kurzantwort" for h in heals_g))
    fest("S17 genau ein Schlüssel nach Ersetzen",
         len(re.findall(r"(?m)^kurzantwort:", _fm_roh(neu_g))) == 1)
    fest("S18 M4 nach Ersetzen grün", not _m4_befunde(rel, neu_g))

    # Git-Integration: echter HEAD-Restore in einem Wegwerf-Repo
    with tempfile.TemporaryDirectory() as tmp:
        def git(*args):
            return subprocess.run(["git", *args], cwd=tmp, capture_output=True, text=True)
        git("init", "-q")
        git("config", "user.email", "test@example.org")
        git("config", "user.name", "Test")
        os.makedirs(os.path.join(tmp, "content", "posts", "2026-10-28-probe"))
        pfad = os.path.join(tmp, rel)
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(gut)
        git("add", "-A")
        git("commit", "-qm", "stand mit kurzantwort")
        # Automatik lässt kurzantwort fallen
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(ohne_kz)
        bericht = lauf(root=tmp, fix=True, pfade=[rel])
        fest("S13 Git-Restore geheilt", any(g["feld"] == "kurzantwort" for g in bericht["geheilt"]))
        with open(pfad, encoding="utf-8") as fh:
            geheilt_text = fh.read()
        fest("S14 Git-Restore bytegenau",
             _feld_block(_fm_roh(geheilt_text), "kurzantwort")
             == _feld_block(_fm_roh(gut), "kurzantwort"))
        fest("S15 Git-Restore M4 grün", not _m4_befunde(rel, geheilt_text))

    # Fail-closed: ohne lesbare Grundlage ist „kein Fund“ kein Grün (C2/C33).
    # PyYAML-Ausfall – mw importiert weiter, sein Leser gibt nur noch None.
    echter_parser = mw.yaml
    try:
        mw.yaml = None
        ok, grund = _grundlage(ROOT)
        fest("S19 PyYAML-Ausfall ist nicht grün", not ok and "PyYAML" in grund)
        fest("S20 PyYAML-Ausfall meldet keine Heilung",
             lauf(root=ROOT, fix=False, pfade=[rel])["grundlage"] is False)
    finally:
        mw.yaml = echter_parser
    # Kein Git/HEAD – sonst sähe jede Datei wie eine neue (basislose) Datei aus.
    with tempfile.TemporaryDirectory() as kein_git:
        ok, grund = _grundlage(kein_git)
        fest("S21 fehlender Git-HEAD ist nicht grün", not ok and "HEAD" in grund)
        fest("S22 fehlender Git-HEAD läuft fail-closed",
             lauf(root=kein_git, fix=True, pfade=[rel])["grundlage"] is False)
    fest("S23 echte Grundlage ist grün", _grundlage(ROOT)[0])

    if fehler:
        print("🛑 PFLICHTFELD-VERLUST-WACHE SELBSTTEST – Befunde:")
        for f in fehler:
            print(f"   ✗ {f}")
        return 1
    print("✅ PFLICHTFELD-VERLUST-WACHE SELBSTTEST: 23 Gruppen grün "
          "(M4-Pflicht gepinnt, Verlust erkannt, bytegenau aus HEAD geheilt, "
          "Body gleich, idempotent, kein Erfinden, Entwurf verschont, "
          "leeres Feld ersetzt, Git-Restore, fail-closed ohne PyYAML/HEAD).")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Pflichtfeld-Verlust-Wache: holt verlorene M4-Pflichtfelder "
                    "bytegenau aus HEAD zurück, bevor die Automatik committed.")
    p.add_argument("--fix", action="store_true", help="aus HEAD zurückholen (sonst nur prüfen)")
    p.add_argument("--json", action="store_true", help="Bericht als JSON")
    p.add_argument("--pfad", action="append", default=None, help="nur diese Datei(en)")
    p.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return _run_selftest()

    bericht = lauf(root=args.root, fix=args.fix, pfade=args.pfad)
    if args.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(bericht_text(bericht))
    if not bericht.get("grundlage"):
        return 2
    return 1 if bericht["offen"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
