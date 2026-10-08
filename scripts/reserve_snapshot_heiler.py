#!/usr/bin/env python3
"""
reserve_snapshot_heiler.py – defekter Reserve-Nachweis wird wieder ein Beweis
============================================================================

WARUM ES DIESE DATEI GIBT (Issue #661, 08.10.2026)
--------------------------------------------------
Der Bot-Watchdog meldete:

    P2 · Content-Reserve niedrig (Maschine) – Reife-Zertifikat nicht
    verfügbar (Expecting property name enclosed in double quotes: line 28
    column 5 (char 738)); 15 Reserve-Entwürfe, Nachweis fehlt

Fünfzehn Entwürfe lagen im Repo, sechs davon waren wenige Stunden vorher
mit dem echten Produktions-Gate zertifiziert worden. Der Vorrat war also
gesund – unlesbar war allein der NACHWEIS darüber. Und genau für diesen
Zustand gab es drei Lücken, die sich gegenseitig verdeckten:

1. KEINE EIGENE KLASSE. `bot_watchdog.check_content_reserve()` fing den
   Parse-Fehler ab und meldete „Content-Reserve niedrig“. Der nächste
   Schritt im Ticket lautete deshalb „mindestens 4 zertifizierte
   Kandidaten herstellen“ – eine Heilung, die an einem defekten JSON
   nichts ändern kann. Ein Ticket, dessen nächster Schritt die Ursache
   verfehlt, wird nie abgearbeitet (dieselbe Historie wie #272, #393).
2. KEINE MASCHINELLE HEILUNG. Den Snapshot neu zu ziehen ist eine Sache
   von Sekunden; niemand tat es. Der Befund blieb, bis ein Mensch oder
   ein lokaler Reparaturlauf das Zertifikat neu schrieb.
3. KEIN WÄCHTER ÜBER DEN GANZEN SNAPSHOT. `reserve_artifacts.py` kann
   `--check`, aber es gab kein Werkzeug, das einen gefundenen Schaden
   auch BEHEBT – die Automatisierung konnte den Zustand nur melden.

WIE HIER GEHEILT WIRD (Fail-closed, nichts wird erfunden)
---------------------------------------------------------
Der Heiler arbeitet an genau drei Dateien, die als GANZE SNAPSHOTS
gelten (`reserve_artifacts.STATE_FILES`):

  * `data/reserve-readiness.json`
      Neu aufgebaut AUS DEN ENTWÜRFEN. Jede Zeile bekommt den echten
      SHA-256 der tatsächlichen Datei-Bytes und `ready: false` mit
      begründetem Grund. Nie wird ein READY behauptet, das nicht gemessen
      wurde – die echte Nachmessung macht danach `reserve_readiness.py`
      bzw. `reserve_recert.py --fix`. Damit ist der Nachweis wieder
      lesbar, ohne auch nur eine Qualitätsaussage zu fälschen.
  * `data/reserve-custody.json`
      Buchhaltung über Pool-Kandidaten und damit VOLLSTÄNDIG aus dem
      Bestand ableitbar: `reserve_custody.bestandsaufnahme()` liefert
      Zustand, Titel und Pfad je Entwurf. Der Neuaufbau ist deterministisch
      und veränderte keinen Artikel.
  * `data/reserve-quarantine.json`
      Das ist BEWEISMATERIAL („dieser Kandidat fiel mit demselben Fund
      zum zweiten Mal durch“) und lässt sich nicht ableiten. Deshalb wird
      hier nichts rekonstruiert, sondern der Schaden BELEGT: SHA-256,
      Größe und ein kurzer Fingerabdruck der defekten Bytes wandern in
      `data/reserve-history.jsonl` (append-only, unveränderbar), danach
      beginnt die Quarantäne nachvollziehbar bei null. Ein Kandidat, der
      wirklich reparierresistent ist, fällt innerhalb von zwei Läufen
      erneut auf – die Leitplanke wird nicht gelockert, nur beweisbar
      zurückgesetzt.

Gemeinsam für alle drei: geschrieben wird ausschließlich über
`reserve_artifacts.write_object()` (atomar, fsync, Rückleseprobe). Nach
der Heilung wird der Snapshot GEGENGELESEN; bleibt er ungültig, endet der
Lauf rot (Exit 1) statt einen halben Beweis zu hinterlassen.

MODI
    python3 scripts/reserve_snapshot_heiler.py --check      # nur prüfen
    python3 scripts/reserve_snapshot_heiler.py --fix        # prüfen + heilen
    python3 scripts/reserve_snapshot_heiler.py --selftest   # Sabotageproben

EXIT: 0 = Snapshot vollständig (auch nach Heilung) · 1 = offener Befund
      · 2 = Selbsttest fehlgeschlagen
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))

import reserve_artifacts as artifacts  # noqa: E402

DATA = "data"
HISTORY = "reserve-history.jsonl"
GRUND_ZERTIFIKAT = "Zertifikat beschädigt – Nachmessung nötig (#661)"
HERKUNFT = "snapshot-heiler #661"


# --------------------------------------------------------------------------
#  Prüfen
# --------------------------------------------------------------------------
def datei_befund(path: Path) -> str | None:
    """Ein Befund je defekter Snapshot-Datei, sonst None."""
    try:
        artifacts.read_object(path)
    except FileNotFoundError:
        return None          # fehlend ist erlaubt (Bootstrap), defekt nie
    except (OSError, ValueError) as exc:
        return f"{path.name}: {exc}"
    return None


def zertifikat_befund(path: Path) -> str | None:
    """Das Zertifikat trägt zusätzlich eine Inhaltsvertragspflicht."""
    try:
        artifacts.read_certificate(path)
    except FileNotFoundError:
        return None
    except (OSError, ValueError) as exc:
        return f"{path.name}: {exc}"
    return None


def pruefe(root: Path = ROOT) -> list[str]:
    """Alle Befunde am Reserve-Snapshot. Leere Liste = vollständig."""
    daten = root / DATA
    befunde: list[str] = []
    for name in artifacts.STATE_FILES:
        path = daten / name
        fund = (zertifikat_befund(path) if name == "reserve-readiness.json"
                else datei_befund(path))
        if fund:
            befunde.append(fund)
    return befunde


# --------------------------------------------------------------------------
#  Heilen
# --------------------------------------------------------------------------
def _entwuerfe(root: Path) -> list[Path]:
    """Alle Reserve-Entwürfe, sortiert – die Quelle jeder Rekonstruktion."""
    posts = root / "content" / "posts"
    if not posts.is_dir():
        return []
    treffer = []
    for index in sorted(posts.glob("*/index.md")):
        try:
            text = index.read_text(encoding="utf-8")
        except OSError:
            continue
        teile = text.split("---", 2)
        if len(teile) != 3 or teile[0] != "":
            continue
        fm = teile[1]
        if "reserve:" not in fm:
            continue
        treffer.append(index)
    return treffer


def zertifikat_neu(root: Path) -> dict:
    """Ehrliches Zertifikat aus dem Bestand: echte Hashes, kein READY.

    Das Ziel kommt aus `reserve_economy.ziel()` und NIE aus der beschädigten
    Datei – sonst setzte der kaputte Beweis seine eigene Messlatte (#393).
    """
    import reserve_economy

    ziel = reserve_economy.ziel()
    zeilen = []
    for index in _entwuerfe(root):
        roh = index.read_bytes()
        zeilen.append({
            "slug": index.parent.name,
            "ready": False,
            "sha256": hashlib.sha256(roh).hexdigest(),
            "reason": GRUND_ZERTIFIKAT,
            "details": [GRUND_ZERTIFIKAT],
        })
    return {
        "target": ziel,
        "ready": 0,
        "pool_size": len(zeilen),
        "generated_at": dt.datetime.now(dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "repariert_am": dt.datetime.now(dt.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"),
        "repariert_grund": "Snapshot-Heiler #661: defekter Nachweis, "
                           "Nachmessung durch reserve_readiness.py nötig",
        "candidates": zeilen,
    }


def custody_neu(root: Path) -> dict:
    """Buchhaltung neu aus dem Bestand – deterministisch, ohne Datenerfindung.

    Der Aufrufer hat die defekten Bytes vorher belegt und die Datei entfernt:
    `bestandsaufnahme()` liest das Gedächtnis zwingend mit (nur so erkennt
    sie einen Kandidaten mit verlorener Fahne) und bricht an ungültigem JSON
    ab – ein liegen gelassener Schaden würde die Heilung blockieren.
    """
    import reserve_custody as custody

    pfad = root / DATA / "reserve-custody.json"
    lage = custody.bestandsaufnahme(root / "content" / "posts", pfad=pfad)
    heute = custody.heute()
    ledger: dict[str, dict] = {}
    for zustand, liste in (("pool", lage.get("pool") or []),
                           ("ausgemustert", lage.get("blockiert") or []),
                           ("zurueckgezogen", lage.get("zurueckgezogen") or []),
                           ("ruecklaeufer", lage.get("ruecklaeufer") or [])):
        for eintrag in liste:
            slug = eintrag.get("slug") or ""
            if not slug:
                continue
            ledger[custody.schluessel(slug)] = {
                "slug": slug,
                "titel": eintrag.get("titel") or slug,
                "zustand": zustand,
                "seit": heute,
                "herkunft": HERKUNFT,
            }
    return ledger


def _beleg_schreiben(root: Path, path: Path, roh: str, grund: str) -> None:
    """Defekte Bytes belegen, bevor sie ersetzt werden (append-only)."""
    history = root / DATA / HISTORY
    beleg = {
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "ereignis": "snapshot_reparatur",
        "datei": path.name,
        "grund": grund[:300],
        "sha256": hashlib.sha256(roh.encode("utf-8", "replace")).hexdigest(),
        "bytes": len(roh.encode("utf-8", "replace")),
        "fingerabdruck": roh[:120],
    }
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(beleg, ensure_ascii=False, sort_keys=True) + "\n")


def quarantaine_zuruecksetzen(root: Path, path: Path, grund: str) -> None:
    """Quarantäne ist Beweis: erst belegen, dann nachvollziehbar bei null."""
    try:
        roh = path.read_text(encoding="utf-8")
    except OSError:
        roh = ""
    if roh:
        _beleg_schreiben(root, path, roh, grund)
    artifacts.write_object(path, {}, sort_keys=True)


def repariere(root: Path = ROOT) -> dict:
    """Heilt jeden defekten Snapshot. Rückgabe: Protokoll."""
    daten = root / DATA
    protokoll = {"geheilt": [], "belege": [], "fehler": []}

    for name in artifacts.STATE_FILES:
        path = daten / name
        if not path.exists():
            continue
        try:
            if name == "reserve-readiness.json":
                artifacts.read_certificate(path)
            else:
                artifacts.read_object(path)
            continue                                   # intakt – nichts tun
        except (OSError, ValueError) as exc:
            grund = f"{exc}"

        try:
            if name == "reserve-readiness.json":
                _beleg_schreiben(root, path, path.read_text(encoding="utf-8"),
                                 grund)
                artifacts.write_object(path, zertifikat_neu(root))
            elif name == "reserve-custody.json":
                _beleg_schreiben(root, path, path.read_text(encoding="utf-8"),
                                 grund)
                # Erst belegen, dann weg damit: die Bestandsaufnahme liest das
                # Gedächtnis mit und bricht an defektem JSON ab.
                path.unlink()
                artifacts.write_object(path, custody_neu(root), sort_keys=True)
            else:
                quarantaine_zuruecksetzen(root, path, grund)
        except (OSError, ValueError) as fehler:
            protokoll["fehler"].append(f"{name}: {fehler}")
            continue
        protokoll["geheilt"].append({"datei": name, "grund": grund[:300]})

    # Gegenprobe: erst der Beweis zählt, nicht der gute Wille.
    rest = pruefe(root)
    protokoll["restbefunde"] = rest
    if rest:
        protokoll["fehler"].extend(rest)
    return protokoll


# --------------------------------------------------------------------------
#  Selbsttest (Sabotageproben)
# --------------------------------------------------------------------------
def _schreibe_post(root: Path, slug: str, titel: str) -> None:
    index = root / "content" / "posts" / slug / "index.md"
    index.parent.mkdir(parents=True, exist_ok=True)
    index.write_text(
        f'---\ntitle: "{titel}"\ndate: 2026-10-08T10:00:00Z\n'
        f"draft: true\nreserve: true\n---\n\nText von {titel}.\n",
        encoding="utf-8")


def run_selftest() -> int:
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / DATA).mkdir(parents=True)
        for slug, titel in (("2026-10-08-alpha", "Alpha"),
                            ("2026-10-08-beta", "Beta")):
            _schreibe_post(root, slug, titel)

        # 1) Sauberer Start ist kein Befund.
        if pruefe(root):
            print("  ✗ leerer Snapshot meldet Befunde")
            return 2

        # 2) Abgeschnittenes JSON – genau die Klasse aus #661.
        kaputt = (root / DATA / "reserve-readiness.json")
        kaputt.write_text('{\n  "target": 6,\n  "candidates": [\n    {\n'
                          '      "slug": "2026-10-08-alpha",\n    },\n',
                          encoding="utf-8")
        if not pruefe(root):
            print("  ✗ defektes Zertifikat bleibt unbemerkt")
            return 2

        protokoll = repariere(root)
        if protokoll["fehler"]:
            print(f"  ✗ Heilung scheiterte: {protokoll['fehler']}")
            return 2
        if not protokoll["geheilt"]:
            print("  ✗ Heilung zählt keinen reparierten Snapshot")
            return 2

        # 3) Die Rekonstruktion ist ehrlich: zwei Zeilen, beide KEIN ready.
        neu = artifacts.read_certificate(kaputt)
        zeilen = neu["candidates"]
        if len(zeilen) != 2 or any(z["ready"] for z in zeilen):
            print("  ✗ rekonstruiertes Zertifikat behauptet Reife")
            return 2
        echt = {z["slug"]: hashlib.sha256(
            (root / "content" / "posts" / z["slug"] / "index.md").read_bytes()
        ).hexdigest() for z in zeilen}
        if any(z["sha256"] != echt[z["slug"]] for z in zeilen):
            print("  ✗ rekonstruierte Hashes stimmen nicht mit den Dateien")
            return 2
        if neu.get("ready") != 0 or neu.get("pool_size") != 2:
            print("  ✗ Summenfelder weichen von der Kandidatenliste ab")
            return 2

        # 4) Gedächtnis: Buchhaltung wird aus dem Bestand neu gebaut.
        ledger_pfad = root / DATA / "reserve-custody.json"
        ledger_pfad.write_text('{"alpha": {"zustand": "pool",',
                               encoding="utf-8")
        if not pruefe(root):
            print("  ✗ defektes Bestands-Gedächtnis bleibt unbemerkt")
            return 2
        if repariere(root)["fehler"]:
            print("  ✗ Bestands-Gedächtnis wurde nicht geheilt")
            return 2
        ledger = artifacts.read_object(ledger_pfad)
        if "alpha" not in ledger or "beta" not in ledger:
            print(f"  ✗ Ledger unvollständig: {sorted(ledger)}")
            return 2

        # 5) Quarantäne: Beweis wird belegt, nicht erfunden.
        quarantaene = root / DATA / "reserve-quarantine.json"
        schadtext = '{"2026-10-08-alpha": {"hits": 2, "signatur": "x"'
        quarantaene.write_text(schadtext, encoding="utf-8")
        if not pruefe(root):
            print("  ✗ defekte Quarantäne bleibt unbemerkt")
            return 2
        if repariere(root)["fehler"]:
            print("  ✗ Quarantäne wurde nicht geheilt")
            return 2
        if artifacts.read_object(quarantaene) != {}:
            print("  ✗ Quarantäne wurde mit erfundenen Akten gefüllt")
            return 2
        history = (root / DATA / HISTORY).read_text(encoding="utf-8").strip()
        belege = [json.loads(z) for z in history.splitlines() if z.strip()]
        schaden = [b for b in belege
                   if b.get("datei") == "reserve-quarantine.json"]
        if not schaden:
            print("  ✗ der Schaden ist nicht belegt (Spur fehlt)")
            return 2
        erwartet = hashlib.sha256(schadtext.encode("utf-8")).hexdigest()
        if schaden[-1]["sha256"] != erwartet:
            print("  ✗ Beleg zeigt nicht die defekten Bytes")
            return 2

        # 6) Ein intakter Snapshot wird NICHT angefasst (Idempotenz).
        vorher = {n: (root / DATA / n).read_text(encoding="utf-8")
                  for n in artifacts.STATE_FILES}
        nochmal = repariere(root)
        if nochmal["geheilt"] or nochmal["fehler"]:
            print("  ✗ zweite Heilung schreibt erneut")
            return 2
        if any((root / DATA / n).read_text(encoding="utf-8") != text
               for n, text in vorher.items()):
            print("  ✗ Idempotenz verletzt: Datei verändert")
            return 2

        # 7) Heilung ohne jeden Entwurf bleibt gültig (leerer Pool).
        leer = Path(tmp) / "leer"
        (leer / DATA).mkdir(parents=True)
        artifacts.write_object(leer / DATA / "reserve-readiness.json",
                               zertifikat_neu(leer))
        if pruefe(leer):
            print("  ✗ leeres, gültiges Zertifikat meldet Befunde")
            return 2

    print("  ✅ Snapshot-Heiler: 7 Sabotageproben bestanden")
    return 0


# --------------------------------------------------------------------------
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="nur prüfen (Exit 1 bei Befund)")
    parser.add_argument("--fix", action="store_true",
                        help="prüfen, heilen und gegenlesen")
    parser.add_argument("--json", action="store_true",
                        help="Ergebnis maschinenlesbar")
    parser.add_argument("--selftest", action="store_true",
                        help="Sabotageproben (offline)")
    parser.add_argument("--root", default=str(ROOT),
                        help="Repository-Wurzel (Tests)")
    args = parser.parse_args()

    if args.selftest:
        print("🔍 reserve_snapshot_heiler.py – Sabotageproben")
        return run_selftest()

    root = Path(args.root).resolve()
    befunde = pruefe(root)
    protokoll: dict = {"befunde": befunde, "geheilt": []}

    if befunde and args.fix:
        protokoll = repariere(root)
        protokoll["befunde_vorher"] = befunde

    if args.json:
        print(json.dumps(protokoll, ensure_ascii=False, indent=2))
    elif befunde and not args.fix:
        # Ohne --fix ist der Befund das Ergebnis – nicht die (leere) Heilung.
        print("🛑 Reserve-Snapshot beschädigt:")
        for fund in befunde:
            print(f"   - {fund}")
        print("   Heilung: `python3 scripts/reserve_snapshot_heiler.py --fix` "
              "(baut den Nachweis aus dem Bestand neu).")
        return 1

    if args.json:
        return 1 if protokoll.get("fehler") or protokoll.get("restbefunde") else 0

    if protokoll.get("geheilt"):
        print(f"🩺 Reserve-Snapshot geheilt: "
              f"{len(protokoll['geheilt'])} Datei(en) neu aus dem Bestand gezogen.")
        for eintrag in protokoll["geheilt"]:
            print(f"   - {eintrag['datei']}: {eintrag['grund']}")
        print("   Die echte Nachmessung macht `reserve_readiness.py` "
              "(Stufe 3) bzw. `reserve_recert.py --fix`.")
    if protokoll.get("fehler") or protokoll.get("restbefunde"):
        print("🛑 Reserve-Snapshot beschädigt:")
        for fund in (protokoll.get("restbefunde") or protokoll.get("fehler")):
            print(f"   - {fund}")
        return 1
    print("✅ Reserve-Snapshot vollständig: eindeutiges JSON in allen "
          "drei Zustandsdateien.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
