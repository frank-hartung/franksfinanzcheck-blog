#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
reserve_frontmatter_gate.py – eine Content-Zeile darf den Vorrat nicht töten
===========================================================================

WARUM ES DIESES GATE GIBT (30.10.2026, WF-D4E0 / #947)
-----------------------------------------------------
Der Reserve-Lauf 40856100639 (29.10.2026, Commit `76efccb4`) endete mit zwei
roten Schritten, und das Ticket nannte nur den letzten:

    Job „reserve“ – „Artefakt-Wächter (Maschinen-Artefakte strukturell heil)“
                  → „Stock shortage must not look successful“

Der erste rote Schritt war kein Vorratsproblem. Er war **eine Zeile Content**:

    content/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-…/index.md:5
    reserve_reaktiviert: "… Befund der Klasse „heilbar" ist heilbar, …"

Ein deutsches Schlusszeichen als **ASCII**-Zeichen (`„heilbar"` statt
`„heilbar“`) beendet den YAML-Wert beim ersten `"`. Alles danach ist Text, der
Parser bricht ab („expected <block end>, but found '<scalar>'“) – Hugo kann
die Seite nicht bauen.

Die Herkunft ist belegt (Git-Historie, nicht Vermutung):

| Commit     | Zeit (UTC) | Was                                    |
|------------|------------|----------------------------------------|
| `47fee362` | 27.10. 17:44 | Zeile steht korrekt (`„heilbar“`)    |
| `3d050ea1` | 29.10. 10:11 | **#941 (WF-D0C9) schreibt sie kaputt** – Frontmatter von 9 Live-Artikeln neu getippt |
| `76efccb4` | 29.10. 10:11 | Reserve-Lauf checkt genau diesen Stand aus |
| `40856100639` | 29.10. 11:15 | Lauf rot: Artefakt-Wächter (A6) + End-Gate |
| `d396dd3e` | 29.10. 10:41 | #942 baut `frontmatter_wache.py` und heilt die Zeile |

Der Fund war also **echt** – und er war an der falschen Stelle teuer:
Der Artefakt-Wächter der Reserve kennt die Klasse (A6), kann sie aber nicht
heilen („A6 wird NICHT geheilt: Inhalt zu rekonstruieren hieße, Inhalt zu
erfinden“ – richtig, aber hier wird nichts erfunden, es wird **zitiert**).
Also stand die Nacht still, ohne dass ein Mensch aus dem Ticket ablesen
konnte, welche Datei, welche Zeile, welche Ursache und welcher Befehl.

DIE DREI SÄTZE DIESES GATES
---------------------------
1. **Keine zweite Wahrheit.** Das Gate parst kein Frontmatter. Es fragt
   `frontmatter_wache.py` – die Wache, die aus diesem Vorfall entstanden ist
   (F1–F6, `--fix`). Fällt sie aus, ist das Gate rot (fail-closed), nicht grün.
2. **Besitz statt Reichweite.** Geheilt wird nur, was dem Reserve-Lauf gehört
   (`reserve: true` im Pool, `reserve_blocked:` in der Quarantäne) – dieselbe
   Besitzregel wie `reserve_stage_guard.py`, importiert, nicht kopiert.
   **Live-Content gehört der Engine-/Deploy-Kette**: Er wird gemeldet, benannt
   und mit Reparaturbefehl übergeben – nie still verändert.
3. **Heilung nur mit Beweis.** Geschrieben wird ausschließlich, wenn
   *die Wache den Fund als heilbar führt* (`heilbar=True`),
   *der Artikeltext **bytegleich** bleibt* (nur das Frontmatter darf sich
     ändern),
   *nach der Heilung **kein neuer** Blocker entsteht und mindestens einer
     verschwindet.
   Fehlt ein Beweis, bleiben die Originalbytes stehen und der Fund wird offen
   gemeldet.

Damit ist die Fehlerklasse strukturell geschlossen:
* Ein heilbarer Frontmatter-Defekt im **eigenen** Vorrat kann die Nacht nicht
  mehr töten – er wird geheilt **und** belegt.
* Ein Defekt im **fremden** Bestand wird beim Namen genannt (Datei, Zeile,
  Spalte, Ursache, Befehl) statt als „Stock shortage“.
* Eine Heilung, die den Artikel umschreiben würde, ist unerzeugbar.

NUTZUNG
    python3 scripts/reserve_frontmatter_gate.py              # prüfen (lesend)
    python3 scripts/reserve_frontmatter_gate.py --fix        # eigenes heilen
    python3 scripts/reserve_frontmatter_gate.py --md         # Lauf-Summary
    python3 scripts/reserve_frontmatter_gate.py --json
    python3 scripts/reserve_frontmatter_gate.py --kurzbefund # eine Zeile
    python3 scripts/reserve_frontmatter_gate.py --pfad content/posts/x/index.md
    python3 scripts/reserve_frontmatter_gate.py --wirkungsprobe
    python3 scripts/reserve_frontmatter_gate.py --selftest

EXIT: 0 = kein offener Blocker · 1 = offener Blocker (eigener unheilbar oder
      fremder Bestand) · 2 = Selbsttest rot oder Frontmatter-Wache (SSOT)
      nicht lauffähig – fail-closed, nie „grün aus Unwissen“.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

# Die beiden Quellen der Wahrheit, die dieses Gate NICHT nachbaut:
#   * frontmatter_wache.py  – was ist ein Blocker, was ist heilbar, wie heilt man
#   * reserve_stage_guard.py – wem gehört eine Content-Datei
# Beide werden importiert. Ist einer nicht verfügbar, ist das ein Ausfall des
# Gates (Exit 2) – „ungeprüft“ darf niemals wie „heil“ aussehen (#661).
SSOT_FEHLER = ""
try:
    import frontmatter_wache as fw          # noqa: E402
    import reserve_stage_guard as rsg       # noqa: E402
except Exception as exc:                     # pragma: no cover – Ausfallpfad
    fw = None                                # type: ignore[assignment]
    rsg = None                               # type: ignore[assignment]
    SSOT_FEHLER = f"{exc.__class__.__name__}: {exc}"

BESITZ_RESERVE = "reserve"
BESITZ_FREMD = "fremd"

# Nur Inhaltsdateien – dieselbe Endungsliste wie die Frontmatter-Wache.
INHALT_ENDUNGEN = (".md", ".markdown")

REPARATUR = ("python3 scripts/frontmatter_wache.py --fix --pfad "
             "{pfad}")


# ---------------------------------------------------------------------------
#  Sammlung / Hilfen
# ---------------------------------------------------------------------------
def _rel(pfad: Path, wurzel: Path) -> str:
    try:
        return str(pfad.relative_to(wurzel))
    except ValueError:
        return str(pfad)


def sammle_dateien(wurzel: Path | None = None,
                   pfade: list[str] | None = None) -> list[tuple[Path, str]]:
    wurzel = Path(wurzel or ROOT)
    if pfade:
        out: list[tuple[Path, str]] = []
        for eintrag in pfade:
            ziel = Path(eintrag)
            if not ziel.is_absolute():
                ziel = wurzel / ziel
            if ziel.is_file():
                out.append((ziel, _rel(ziel, wurzel)))
                continue
            for treffer in sorted(ziel.rglob("*")):
                if treffer.is_file() and treffer.suffix.lower() in INHALT_ENDUNGEN:
                    out.append((treffer, _rel(treffer, wurzel)))
        return out
    return [(p, _rel(p, wurzel)) for p in sorted(wurzel.glob("content/**/*.md"))
            + sorted(wurzel.glob("content/**/*.markdown"))]


def koerper(text: str) -> str:
    """Alles nach dem schließenden Frontmatter-Trenner (oder "" wenn keins).

    Der Beweis „Heilung fasst nur das Frontmatter an“ ist ein Bytevergleich
    dieser Zeichenkette: Was hier steht, ist der Artikel – und der darf sich
    durch eine Heilung **nie** ändern.
    """
    if not text.startswith("---"):
        return ""
    teile = text.split("---", 2)
    return teile[2] if len(teile) == 3 else ""


def _schreibe(pfad: Path, text: str) -> None:
    tmp = pfad.with_suffix(pfad.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, pfad)


def _befund_dict(b: dict, besitz: str) -> dict:
    return {"regel": b.get("regel", "?"), "schwere": b.get("schwere", ""),
            "pfad": b.get("pfad", ""), "zeile": b.get("zeile", 0),
            "spalte": b.get("spalte", 0), "meldung": b.get("meldung", ""),
            "heilbar": bool(b.get("heilbar")), "besitz": besitz}


def _kurz(eintrag: dict) -> str:
    ort = f"{eintrag['pfad']}:{eintrag['zeile']}"
    if eintrag.get("spalte"):
        ort += f":{eintrag['spalte']}"
    return f"[{eintrag['regel']}] {ort} – {eintrag['meldung']}"


# ---------------------------------------------------------------------------
#  Der Beweis der Heilung
# ---------------------------------------------------------------------------
def heilung_beweisen(pfad: Path, alt: str, neu: str, belege: list,
                     vorher: list[dict], *,
                     anzeige: str | None = None) -> tuple[bool, str, list[dict]]:
    """Darf `neu` geschrieben werden? (ok, Grund, Blocker nachher)

    Vier Bedingungen, jede einzeln nachweisbar. Fehlt eine, bleibt die Datei
    bytegenau, wie sie war:

      B1 Die Wache hat überhaupt eine Änderung erzeugt UND sie begründet
         (`belege`) – eine Änderung ohne Beleg ist eine Behauptung.
      B2 Der Artikeltext ist **bytegleich**. Ein Heiler, der Prosa anfasst,
         ist kein Frontmatter-Heiler (Lehre aus der Generalprobe 29.10.2026).
      B3 Es entsteht **kein neuer Blocker** (gleiche Regel+Meldung wie vorher
         oder gar keiner) – Heilung darf keine neue Baustelle öffnen.
      B4 Es verschwindet mindestens ein Blocker.
    """
    if fw is None:                                   # pragma: no cover
        return False, "Frontmatter-Wache (SSOT) nicht verfügbar", vorher
    if neu == alt:
        return False, "keine Änderung – nichts zu heilen", vorher
    if not belege:
        return False, "Änderung ohne Beleg der Wache (B1)", vorher
    if koerper(alt) != koerper(neu):
        return False, ("Heilung würde den Artikeltext verändern (B2) – "
                       "Originalbytes bleiben stehen"), vorher
    nachher, _ = fw.pruefe_datei(pfad, neu,
                                 anzeige=anzeige or _rel(pfad, ROOT))
    nachher_blocker = [b for b in nachher if b.get("schwere") == fw.BLOCKER]
    vorher_signaturen = {(b.get("regel"), b.get("meldung")) for b in vorher}
    neue = [b for b in nachher_blocker
            if (b.get("regel"), b.get("meldung")) not in vorher_signaturen]
    if neue:
        return False, ("Heilung würde einen NEUEN Blocker erzeugen (B3): "
                       + "; ".join(str(b.get("meldung", ""))[:80] for b in neue[:2])
                       ), vorher
    if len(nachher_blocker) >= len(vorher):
        return False, ("Heilung beseitigt keinen Blocker (B4) – "
                       f"{len(vorher)} vorher, {len(nachher_blocker)} nachher"), vorher
    return True, "", nachher_blocker


# ---------------------------------------------------------------------------
#  Prüfung
# ---------------------------------------------------------------------------
def pruefe(wurzel: Path | None = None, *, fix: bool = False,
           pfade: list[str] | None = None) -> dict:
    """Prüft/heilt den Content-Bestand. Gibt den Bericht als dict zurück."""
    wurzel = Path(wurzel or ROOT)
    bericht: dict = {"dateien": 0, "geheilt": [], "offen": [],
                     "verworfen": [], "tiefenpruefung": False,
                     "reserve_dateien": 0, "fremd_dateien": 0,
                     "klasse": "ok"}
    if fw is None or rsg is None:                    # pragma: no cover
        bericht["klasse"] = "ssot"
        bericht["fehler"] = SSOT_FEHLER
        return bericht

    for pfad, rel in sammle_dateien(wurzel, pfade):
        try:
            text = pfad.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            bericht["offen"].append({
                "regel": "F1", "schwere": fw.BLOCKER, "pfad": rel,
                "zeile": 0, "spalte": 0, "heilbar": False,
                "besitz": BESITZ_RESERVE,
                "meldung": f"Datei nicht als UTF-8 lesbar: {exc.__class__.__name__}"})
            continue
        bericht["dateien"] += 1
        befunde, tief = fw.pruefe_datei(pfad, text, anzeige=rel)
        bericht["tiefenpruefung"] = bericht["tiefenpruefung"] or tief
        blocker = [b for b in befunde if b.get("schwere") == fw.BLOCKER]
        if not blocker:
            continue
        besitz = (BESITZ_RESERVE if rsg.is_reserve_owned(pfad)
                  else BESITZ_FREMD)
        bericht["reserve_dateien" if besitz == BESITZ_RESERVE
                else "fremd_dateien"] += 1

        if (besitz == BESITZ_RESERVE and fix
                and any(b.get("heilbar") for b in blocker)):
            # Ein werfender Heiler ist ein Ausfall, kein Freibrief: Die Datei
            # bleibt stehen, der Grund wird gemeldet (fail-closed).
            try:
                neu, belege = fw.heile_datei(pfad, text)
            except Exception as exc:                 # noqa: BLE001
                bericht["verworfen"].append({
                    "pfad": rel,
                    "grund": (f"Heiler der SSOT ist gescheitert "
                              f"({exc.__class__.__name__}: {exc}) – "
                              "Originalbytes bleiben stehen"),
                    "befunde": [_befund_dict(b, besitz) for b in blocker]})
                for b in blocker:
                    bericht["offen"].append(_befund_dict(b, besitz))
                continue
            ok, grund, nachher = heilung_beweisen(pfad, text, neu, belege,
                                                  blocker, anzeige=rel)
            if ok:
                _schreibe(pfad, neu)
                bericht["geheilt"].append({
                    "pfad": rel, "vorher": len(blocker),
                    "nachher": len(nachher),
                    "belege": [str(b.get("meldung", "")) for b in belege],
                    "befunde": [_befund_dict(b, besitz) for b in blocker]})
                if nachher:
                    for b in nachher:
                        bericht["offen"].append(_befund_dict(b, besitz))
                continue
            bericht["verworfen"].append({
                "pfad": rel, "grund": grund,
                "befunde": [_befund_dict(b, besitz) for b in blocker]})

        for b in blocker:
            bericht["offen"].append(_befund_dict(b, besitz))

    if bericht["offen"]:
        bericht["klasse"] = ("fremd" if any(e["besitz"] == BESITZ_FREMD
                                            for e in bericht["offen"])
                             else "reserve")
    return bericht


# ---------------------------------------------------------------------------
#  Ausgabe
# ---------------------------------------------------------------------------
def bericht_text(bericht: dict) -> str:
    zeilen: list[str] = []
    if bericht["klasse"] == "ssot":
        return ("🛑 FRONTMATTER-GATE: Die Frontmatter-Wache (SSOT) ist nicht "
                f"lauffähig – {bericht.get('fehler', 'unbekannt')}. Es wurde "
                "NICHTS geprüft; das ist ein Ausfall, kein grünes Ergebnis.")
    geheilt = bericht["geheilt"]
    offen = bericht["offen"]
    fremd = [e for e in offen if e["besitz"] == BESITZ_FREMD]
    eigen = [e for e in offen if e["besitz"] == BESITZ_RESERVE]
    kopf = (f"Frontmatter-Gate: {bericht['dateien']} Dateien | "
            f"geheilt: {len(geheilt)} | offen: {len(offen)} "
            f"({len(eigen)} Reserve, {len(fremd)} fremd) | "
            f"Tiefenprüfung: "
            f"{'YAML-Parser' if bericht['tiefenpruefung'] else 'Scanner'}")
    if not geheilt and not offen:
        zeilen.append("✅ " + kopf)
        zeilen.append("   Kein Blocker: Der Content, den der Vorrat anfasst, "
                      "ist baubar.")
        return "\n".join(zeilen)
    zeilen.append(("🛑 " if offen else "🔧 ") + kopf)
    for eintrag in geheilt:
        erste = eintrag["befunde"][0] if eintrag["befunde"] else {}
        zeilen.append(f"   🔧 GEHEILT (Reserve-Eigentum): {eintrag['pfad']} – "
                      f"{eintrag['vorher']} Blocker → {eintrag['nachher']}")
        if erste:
            zeilen.append(f"        vorher: {_kurz(erste)}")
        for beleg in eintrag["belege"][:4]:
            zeilen.append(f"        Beleg: {beleg}")
        zeilen.append("        Artikeltext unverändert (Bytevergleich).")
    for eintrag in bericht["verworfen"]:
        zeilen.append(f"   ⊘ HEILUNG VERWORFEN: {eintrag['pfad']} – "
                      f"{eintrag['grund']}")
    for eintrag in eigen:
        zeilen.append(f"   ✗ OFFEN (Reserve, nicht beweisbar heilbar): "
                      f"{_kurz(eintrag)}")
        zeilen.append("        " + REPARATUR.format(pfad=eintrag["pfad"]))
    for eintrag in fremd:
        zeilen.append(f"   ✗ OFFEN (Live-Bestand – gehört der Engine-/Deploy-"
                      f"Kette, wird NICHT angefasst): {_kurz(eintrag)}")
        zeilen.append("        " + REPARATUR.format(pfad=eintrag["pfad"]))
    if offen:
        zeilen.append("")
        zeilen.append("   Eine Seite, die YAML nicht lesen kann, baut nicht. "
                      "Das ist ein Build-Befund, kein Vorratsproblem: Der "
                      "Vorrat heilt, was ihm gehört, und nennt den Rest beim "
                      "Namen.")
    return "\n".join(zeilen)


def bericht_md(bericht: dict) -> str:
    if bericht["klasse"] == "ssot":
        return ("### 🛑 Frontmatter-Gate\n\nDie Frontmatter-Wache (SSOT) ist "
                f"nicht lauffähig: `{bericht.get('fehler', '')}`. Es wurde "
                "nichts geprüft.\n")
    zeilen = ["### Frontmatter-Gate (eine Content-Zeile darf den Vorrat "
              "nicht töten)", "",
              "| Kennzahl | Wert |", "|---|---|",
              f"| geprüfte Dateien | {bericht['dateien']} |",
              f"| geheilt (Reserve-Eigentum) | {len(bericht['geheilt'])} |",
              f"| offen | {len(bericht['offen'])} |",
              f"| Tiefenprüfung | "
              f"{'YAML-Parser' if bericht['tiefenpruefung'] else 'Scanner'} |",
              ""]
    for eintrag in bericht["geheilt"]:
        zeilen.append(f"- 🔧 `{eintrag['pfad']}` – {eintrag['vorher']} Blocker "
                      f"→ {eintrag['nachher']} (Artikeltext bytegleich)")
    for eintrag in bericht["offen"]:
        wo = ("Reserve-Eigentum" if eintrag["besitz"] == BESITZ_RESERVE
              else "Live-Bestand")
        zeilen.append(f"- ✗ `{eintrag['pfad']}:{eintrag['zeile']}` "
                      f"({wo}) – {eintrag['meldung']}")
        zeilen.append(f"  - Reparatur: `{REPARATUR.format(pfad=eintrag['pfad'])}`")
    if bericht["offen"]:
        zeilen += ["", "**Ein Frontmatter-Blocker ist ein Build-Befund, kein "
                   "Vorratsproblem.** Der Lauf nennt Datei, Zeile und Befehl – "
                   "er heilt nur, was ihm gehört."]
    return "\n".join(zeilen)


# ---------------------------------------------------------------------------
#  Selbsttest – Sabotageschutz des Gates selbst
# ---------------------------------------------------------------------------
_KAPUTT_FM = (
    '---\n'
    'title: "Dein Weg zu geringeren Monatskosten: Schritt für Schritt"\n'
    'date: 2026-10-19T01:20:46Z\n'
    'draft: true\n'
    'reserve: true\n'
    'reserve_reaktiviert: "2026-10-07 – Rückholung (#614): Befund der Klasse '
    '„heilbar" ist heilbar, Wirkungsnachweis lesbarkeit_heiler.py"\n'
    '---\n'
    '\n'
    'Der Artikeltext bleibt unangetastet.\n'
)

_LIVE_FM = _KAPUTT_FM.replace("draft: true\nreserve: true\n",
                              "draft: false\nreserve_published: 2026-10-19\n")
_GUT_FM = (
    '---\n'
    'title: "Sauber"\n'
    'date: 2026-10-19T01:20:46Z\n'
    'draft: true\n'
    'reserve: true\n'
    '---\n'
    '\n'
    'Annahme: Die Anlage kostet 500 Euro.\n'
)


def _schreib(wurzel: Path, rel: str, text: str) -> Path:
    ziel = wurzel / rel
    ziel.parent.mkdir(parents=True, exist_ok=True)
    ziel.write_text(text, encoding="utf-8")
    return ziel


def run_selftest() -> int:
    fehler: list[str] = []
    if fw is None or rsg is None:                    # pragma: no cover
        print("🛑 FRONTMATTER-GATE SELBSTTEST ROT: SSOT nicht importierbar "
              f"({SSOT_FEHLER}).")
        return 2
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        kaputt = _schreib(wurzel, "content/posts/pool/index.md", _KAPUTT_FM)
        live = _schreib(wurzel, "content/posts/live/index.md", _LIVE_FM)
        gut = _schreib(wurzel, "content/posts/gut/index.md", _GUT_FM)

        # 1) Der #947-Fall wird erkannt – als Blocker, nicht als Hinweis.
        befunde, _ = fw.pruefe_datei(kaputt, kaputt.read_text(encoding="utf-8"),
                                     anzeige="content/posts/pool/index.md")
        if not [b for b in befunde if b["schwere"] == fw.BLOCKER]:
            fehler.append("1) Der Vorfall-Blocker (#947) wurde nicht erkannt")

        # 2) Lesemodus schreibt nicht (C15): Dateien bleiben bytegleich.
        vorher = {p: p.read_bytes() for p in (kaputt, live, gut)}
        bericht = pruefe(wurzel)
        if [p for p in vorher if p.read_bytes() != vorher[p]]:
            fehler.append("2) Prüf-Aufruf ohne --fix hat Dateien verändert")
        gemeldet = {e["pfad"] for e in bericht["offen"]}
        if gemeldet != {"content/posts/pool/index.md",
                        "content/posts/live/index.md"} or bericht["geheilt"]:
            fehler.append(f"2) Lesemodus meldet nicht genau die zwei kaputten "
                          f"Dateien (gemeldet: {sorted(gemeldet)})")

        # 3) Besitz: Pool wird geheilt, Live-Content NICHT angefasst.
        bericht = pruefe(wurzel, fix=True)
        if len(bericht["geheilt"]) != 1:
            fehler.append("3) Pool-Datei wurde nicht geheilt")
        if fw.pruefe_datei(kaputt, kaputt.read_text(encoding="utf-8"),
                           anzeige="x")[0]:
            fehler.append("3) Pool-Datei ist nach der Heilung nicht grün")
        if live.read_bytes() != vorher[live]:
            fehler.append("3) Live-Content (fremder Besitz) wurde angefasst")
        if gut.read_bytes() != vorher[gut]:
            fehler.append("3) saubere Datei wurde angefasst")
        if [e for e in bericht["offen"] if e["besitz"] != BESITZ_FREMD]:
            fehler.append("3) fremder Fund wurde nicht als fremd gemeldet")
        if not [e for e in bericht["offen"] if e["besitz"] == BESITZ_FREMD]:
            fehler.append("3) fremder Fund fehlt im Bericht")

        # 4) Der Beweis B2: Eine „Heilung“, die Prosa ändert, wird verworfen.
        echt = fw.heile_datei

        def pfuscher(pfad, text):
            neu, belege = echt(pfad, text)
            return neu + "\nNachsatz des Heilers.\n", belege

        fw.heile_datei = pfuscher
        try:
            ziel = _schreib(wurzel, "content/posts/pool2/index.md", _KAPUTT_FM)
            bericht = pruefe(wurzel, fix=True)
            if not any(e["pfad"].endswith("pool2/index.md")
                       for e in bericht["verworfen"]):
                fehler.append("4) Heilung mit geändertem Artikeltext wurde "
                              "nicht verworfen (B2)")
            if ziel.read_text(encoding="utf-8") != _KAPUTT_FM:
                fehler.append("4) verworfene Heilung hat trotzdem geschrieben")
        finally:
            fw.heile_datei = echt

        # 5) Der Beweis B1: Änderung ohne Beleg wird verworfen.
        def stumm(pfad, text):
            neu, _ = echt(pfad, text)
            return neu, []

        fw.heile_datei = stumm
        try:
            ziel = _schreib(wurzel, "content/posts/pool3/index.md", _KAPUTT_FM)
            bericht = pruefe(wurzel, fix=True)
            if not any(e["pfad"].endswith("pool3/index.md")
                       for e in bericht["verworfen"]):
                fehler.append("5) Heilung ohne Beleg wurde nicht verworfen (B1)")
            if ziel.read_text(encoding="utf-8") != _KAPUTT_FM:
                fehler.append("5) beleglose Heilung hat geschrieben")
        finally:
            fw.heile_datei = echt

        # 6) Fail-closed: ohne SSOT kein grünes Urteil (Exit 2, nicht 0).
        #    (Der Ausfall wird über globals() gestellt – der Selbsttest läuft
        #    in-process und darf das Modul nicht dauerhaft verbiegen.)
        echt_fw = fw
        try:
            globals()["fw"] = None
            bericht = pruefe(wurzel)
            if bericht["klasse"] != "ssot":
                fehler.append("6) ohne SSOT wurde nicht fail-closed geurteilt")
            if "NICHTS geprüft" not in bericht_text(bericht):
                fehler.append("6) Ausfall wird nicht als Ausfall ausgesprochen")
        finally:
            globals()["fw"] = echt_fw

        # 7) Idempotenz: zweimal heilen ändert beim zweiten Mal nichts.
        _schreib(wurzel, "content/posts/pool4/index.md", _KAPUTT_FM)
        pruefe(wurzel, fix=True)
        stand = (wurzel / "content/posts/pool4/index.md").read_bytes()
        zweiter = pruefe(wurzel, fix=True)
        if (wurzel / "content/posts/pool4/index.md").read_bytes() != stand:
            fehler.append("7) Heilung ist nicht idempotent")
        if [e for e in zweiter["geheilt"]
                if e["pfad"].endswith("pool4/index.md")]:
            fehler.append("7) zweiter Lauf meldet erneut eine Heilung")

    if fehler:
        print("🛑 FRONTMATTER-GATE SELBSTTEST ROT:")
        for eintrag in fehler:
            print("   - " + eintrag)
        return 2
    print("✅ Frontmatter-Gate-Selbsttest grün (Erkennung, Lesemodus "
          "schreibfrei, Besitz-Grenze, Beweise B1/B2, Fail-closed, "
          "Idempotenz).")
    return 0


def run_wirkungsprobe() -> int:
    """Vorfall → heilen → grün, fremder Besitz unberührt (Maschinenvertrag)."""
    fehler: list[str] = []
    if fw is None or rsg is None:                    # pragma: no cover
        print(f"🛑 WIRKUNGSPROBE ROT: SSOT nicht importierbar ({SSOT_FEHLER}).")
        return 1
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        pool = _schreib(wurzel, "content/posts/2026-10-12-vorfall/index.md",
                        _KAPUTT_FM)
        live = _schreib(wurzel, "content/posts/2026-10-12-live/index.md",
                        _LIVE_FM)
        live_alt = live.read_bytes()
        bericht = pruefe(wurzel, fix=True)
        if len(bericht["geheilt"]) != 1:
            fehler.append("Vorfall im Pool wurde nicht geheilt")
        geheilt = pool.read_text(encoding="utf-8")
        if '„heilbar“' not in geheilt:
            fehler.append("deutsches Schlusszeichen wurde nicht ersetzt")
        if koerper(geheilt) != koerper(_KAPUTT_FM):
            fehler.append("Artikeltext wurde verändert")
        if live.read_bytes() != live_alt:
            fehler.append("Live-Content wurde angefasst")
        if fw.pruefe_datei(pool, geheilt, anzeige="x")[0]:
            fehler.append("geheilte Datei ist nicht grün")
    if fehler:
        print("🛑 WIRKUNGSPROBE ROT:")
        for eintrag in fehler:
            print("   - " + eintrag)
        return 1
    print("✅ Wirkungsprobe grün: #947-Zeile erkannt, im Reserve-Eigentum "
          "bytegenau geheilt (Text unverändert), Live-Content nicht "
          "angefasst, danach grün.")
    return 0


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Frontmatter-Gate der Content-Reserve: heilt beweisbar, "
                    "was dem Vorrat gehört – und benennt den Rest.")
    ap.add_argument("--fix", action="store_true",
                    help="heilbare Blocker im Reserve-Eigentum heilen")
    ap.add_argument("--pfad", action="append", default=None,
                    help="nur diese Datei/dieses Verzeichnis (mehrfach)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--kurzbefund", action="store_true",
                    help="erste offene Zeile (für Lauf-Annotationen)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--wirkungsprobe", action="store_true")
    ap.add_argument("--root", default=None, help="Wurzel (Tests/Sondierung)")
    args = ap.parse_args(argv)

    if args.selftest:
        return run_selftest()
    if args.wirkungsprobe:
        return run_wirkungsprobe()

    wurzel = Path(args.root).resolve() if args.root else ROOT
    bericht = pruefe(wurzel, fix=args.fix, pfade=args.pfad)

    ssot_ausfall = bericht["klasse"] == "ssot"
    if args.kurzbefund:
        offen = bericht["offen"]
        if ssot_ausfall:
            print("Frontmatter-Gate: Frontmatter-Wache (SSOT) nicht "
                  f"lauffähig – {bericht.get('fehler', 'unbekannt')}")
            return 2
        print(_kurz(offen[0]) if offen else "")
        return 1 if offen else 0
    if args.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2))
        return 2 if ssot_ausfall else (1 if bericht["offen"] else 0)
    if args.md:
        print(bericht_md(bericht))
        return 2 if ssot_ausfall else (1 if bericht["offen"] else 0)

    print(bericht_text(bericht))
    if bericht["klasse"] == "ssot":
        return 2
    return 1 if bericht["offen"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
