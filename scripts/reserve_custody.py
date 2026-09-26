#!/usr/bin/env python3
"""
reserve_custody.py – Bestands-Wächter der Content-Reserve (Premium #387)

WARUM DIESE DATEI EXISTIERT (Root-Cause 26.09.2026)
---------------------------------------------------
Der Reserve-Pool ist nur eine FAHNE im Frontmatter (`reserve: true`). Wer
immer einen Entwurf umschreibt – ein KI-Redaktionslauf, ein Heiler, ein
Agent im Auftrag der Redaktion –, kann diese Fahne mitentfernen, ohne es zu
merken. Dann ist der Artikel nicht weg, aber der VORRAT ist es:

  * 25.09.2026, 14:39 – Zertifikat: 8 Kandidaten, davon 7 gate-fertig.
  * 25.09.2026, 22:16 – Commit b025322 („Rebase audit cleanup branch onto
    main") schreibt zwei dieser Kandidaten neu und ersetzt dabei das ganze
    Frontmatter. `reserve: true` fehlt danach:
        2026-09-24-stromfresser-finden-so-stoppst-du-teure
        2026-09-25-stromfresser-finden-so-stoppst-du-teure-energiediebe
  * 26.09.2026, 08:49 – Zertifikat: 3 Kandidaten, 2 gate-fertig.
    Der harte End-Gate wird rot („Stock shortage must not look successful"),
    und niemand kann sagen warum: Die Entwürfe liegen ja noch im Repo.

Zwei gute Artikel verschwinden also lautlos aus dem Vorrat – und der Lauf
produziert Ersatz, den er gar nicht bräuchte. Diese Wache schließt die Lücke:

  GEDÄCHTNIS  `data/reserve-custody.json` führt Buch über jeden Kandidaten,
              der je im Pool war (Slug, Titel, seit wann, letzter Zustand).
  HEILUNG     Verliert ein Entwurf seine Fahne, ohne veröffentlicht,
              ausgemustert oder von einem Menschen zurückgezogen worden zu
              sein, wird sie WIEDERHERGESTELLT – belegt, mit Datum und
              Begründung im Ledger.
  MELDUNG     „Rückläufer" (einmal veröffentlicht, danach wieder `draft:
              true`) werden NICHT automatisch zurückgeholt: Das sind meist
              Dubletten, die ein Gate zu Recht zurückgestuft hat. Sie
              gehören einem Menschen und stehen im Bericht.
  GRENZE      Ein Mensch kann einen Kandidaten dauerhaft aus dem Pool
              nehmen: `reserve_retired: true` im Frontmatter. Diese Marke
              respektiert die Heilung ausnahmslos.

Nichts wird gelöscht, nichts veröffentlicht, kein `draft:`-Zustand geändert.

MODI:
  python3 scripts/reserve_custody.py --status     # Bericht (Mensch)
  python3 scripts/reserve_custody.py --json       # Maschine
  python3 scripts/reserve_custody.py --heal       # Fahnen wiederherstellen
  python3 scripts/reserve_custody.py --md         # Markdown (Step-Summary)
  python3 scripts/reserve_custody.py --selftest   # Sabotage-Schutz

EXIT: 0 = ok (auch nach Heilung) · 1 = offener Befund für einen Menschen
      · 2 = Selbsttest fehlgeschlagen
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
LEDGER = ROOT / "data" / "reserve-custody.json"


def ledger_pfad(pfad: Path | None = None) -> Path:
    """Wo das Bestands-Gedächtnis liegt – zur LAUFZEIT aufgelöst
    (RESERVE_CUSTODY_LEDGER lenkt es um, damit Test- und Trockenläufe nicht
    ins echte Gedächtnis schreiben)."""
    if pfad is not None:
        return Path(pfad)
    ziel = (os.environ.get("RESERVE_CUSTODY_LEDGER") or "").strip()
    return Path(ziel) if ziel else LEDGER

RE_DRAFT_TRUE = re.compile(r"(?m)^draft:\s*true\s*$")
RE_DRAFT_ZEILE = re.compile(r"(?m)^draft:\s*\S+\s*$")
RE_RESERVE = re.compile(r"(?m)^reserve:\s*(?:true|yes|1)\s*$")
RE_PUBLISHED = re.compile(r"(?m)^reserve_published:")
RE_BLOCKED = re.compile(r"(?m)^reserve_blocked:")
RE_RETIRED = re.compile(r"(?m)^reserve_retired:\s*(?:true|yes|1)\s*$")
RE_TITEL = re.compile(r'(?m)^title:\s*["\']?(.+?)["\']?\s*$')
RE_DATUMSPRAEFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")

ZUSTAND_POOL = "pool"
ZUSTAND_LIVE = "veroeffentlicht"
ZUSTAND_BLOCKIERT = "ausgemustert"
ZUSTAND_RUECKLAEUFER = "ruecklaeufer"
ZUSTAND_ZURUECKGEZOGEN = "zurueckgezogen"
ZUSTAND_VERLOREN = "fahne-verloren"


def schluessel(slug: str) -> str:
    """Stabile Kennung eines Kandidaten – OHNE Datumspräfix.

    Die Veredelungs-Stufe hebt jeden offenen Kandidaten auf HEUTE und
    benennt dazu den Ordner um (2026-09-25-x -> 2026-09-26-x). Ein
    Gedächtnis, das den Slug als Schlüssel nähme, verlöre bei jeder Nacht
    seine Einträge und meldete lauter Phantome. Der Datumspräfix gehört
    deshalb nicht zur Identität.
    """
    return RE_DATUMSPRAEFIX.sub("", slug or "")


def frontmatter(text: str) -> str:
    teile = (text or "").split("---", 2)
    return teile[1] if len(teile) == 3 and teile[0] == "" else ""


def heute(jetzt: dt.date | None = None) -> str:
    return (jetzt or dt.date.today()).isoformat()


def ledger_laden(pfad: Path | None = None) -> dict:
    pfad = ledger_pfad(pfad)
    try:
        data = json.loads(pfad.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def ledger_speichern(data: dict, pfad: Path | None = None) -> None:
    pfad = ledger_pfad(pfad)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(data, ensure_ascii=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")


def zustand(text: str) -> str:
    """Zustand eines Artikels aus seinem Frontmatter – eine Quelle."""
    fm = frontmatter(text)
    draft = bool(RE_DRAFT_TRUE.search(fm))
    if RE_RETIRED.search(fm):
        return ZUSTAND_ZURUECKGEZOGEN
    if RE_BLOCKED.search(fm):
        return ZUSTAND_BLOCKIERT
    if RE_RESERVE.search(fm) and draft:
        return ZUSTAND_POOL
    if RE_PUBLISHED.search(fm):
        return ZUSTAND_RUECKLAEUFER if draft else ZUSTAND_LIVE
    return ZUSTAND_VERLOREN if draft else ZUSTAND_LIVE


def fahne_setzen(text: str) -> str | None:
    """Fügt `reserve: true` direkt hinter die draft-Zeile ein (oder None)."""
    m = RE_DRAFT_ZEILE.search(frontmatter(text))
    if not m:
        return None
    # Position im Gesamttext bestimmen (Frontmatter beginnt nach dem ersten ---)
    offset = text.index("---") + 3
    ende = offset + m.end()
    return text[:ende] + "\nreserve: true" + text[ende:]


def bestandsaufnahme(posts_dir: Path = POSTS, *, pfad: Path | None = None) -> dict:
    """Aktueller Zustand aller je bekannten Kandidaten + Befunde."""
    pfad = ledger_pfad(pfad)
    ledger = ledger_laden(pfad)
    pool, verloren, ruecklaeufer, blockiert, zurueckgezogen = [], [], [], [], []
    gesehen = set()
    if posts_dir.is_dir():
        for index in sorted(posts_dir.glob("*/index.md")):
            slug = index.parent.name
            try:
                text = index.read_text(encoding="utf-8")
            except OSError:
                continue
            gesehen.add(schluessel(slug))
            zu = zustand(text)
            titel_m = RE_TITEL.search(text)
            titel = titel_m.group(1).strip() if titel_m else slug
            eintrag = {"slug": slug, "titel": titel, "pfad": str(index)}
            if zu == ZUSTAND_POOL:
                pool.append(eintrag)
            elif zu == ZUSTAND_BLOCKIERT:
                blockiert.append(eintrag)
            elif zu == ZUSTAND_ZURUECKGEZOGEN:
                zurueckgezogen.append(eintrag)
            elif zu == ZUSTAND_RUECKLAEUFER:
                ruecklaeufer.append(eintrag)
            elif zu == ZUSTAND_VERLOREN and ledger.get(
                    schluessel(slug), {}).get("zustand") == ZUSTAND_POOL:
                # Der Kern-Befund: war im Pool, ist Entwurf, Fahne fehlt.
                eintrag["seit"] = ledger[schluessel(slug)].get("seit")
                eintrag["herkunft"] = ledger[schluessel(slug)].get("herkunft", "")
                verloren.append(eintrag)
    # Kandidaten, die das Ledger kennt, die es aber nicht mehr gibt.
    verwaist = [kennung for kennung, e in ledger.items()
                if kennung not in gesehen
                and e.get("zustand") == ZUSTAND_POOL]
    return {"pool": pool, "verloren": verloren, "ruecklaeufer": ruecklaeufer,
            "blockiert": blockiert, "zurueckgezogen": zurueckgezogen,
            "verwaist": sorted(verwaist)}


def heilen(posts_dir: Path = POSTS, *, pfad: Path | None = None,
           dry_run: bool = False, jetzt: dt.date | None = None) -> dict:
    """Verlorene Fahnen wiederherstellen und das Ledger fortschreiben."""
    pfad = ledger_pfad(pfad)
    lage = bestandsaufnahme(posts_dir, pfad=pfad)
    ledger = ledger_laden(pfad)
    geheilt = []
    for eintrag in lage["verloren"]:
        index = Path(eintrag["pfad"])
        try:
            text = index.read_text(encoding="utf-8")
        except OSError:
            continue
        neu = fahne_setzen(text)
        if neu is None:
            continue
        if not dry_run:
            index.write_text(neu, encoding="utf-8")
            kennung = schluessel(eintrag["slug"])
            e = dict(ledger.get(kennung) or {})
            e["zustand"] = ZUSTAND_POOL
            e["titel"] = eintrag["titel"]
            e["slug"] = eintrag["slug"]
            e["zuletzt_im_pool"] = heute(jetzt)
            e.setdefault("seit", heute(jetzt))
            e["geheilt"] = int(e.get("geheilt") or 0) + 1
            e["zuletzt_geheilt"] = heute(jetzt)
            ledger[kennung] = e
        geheilt.append(eintrag)

    if not dry_run:
        # Fortschreiben: aktueller Pool + Zustandswechsel dokumentieren.
        for eintrag in lage["pool"]:
            kennung = schluessel(eintrag["slug"])
            e = dict(ledger.get(kennung) or {})
            e["zustand"] = ZUSTAND_POOL
            e["titel"] = eintrag["titel"]
            e["slug"] = eintrag["slug"]
            e["zuletzt_im_pool"] = heute(jetzt)
            e.setdefault("seit", heute(jetzt))
            ledger[kennung] = e
        for feld, zu in (("ruecklaeufer", ZUSTAND_RUECKLAEUFER),
                         ("blockiert", ZUSTAND_BLOCKIERT),
                         ("zurueckgezogen", ZUSTAND_ZURUECKGEZOGEN)):
            for eintrag in lage[feld]:
                kennung = schluessel(eintrag["slug"])
                if kennung not in ledger and zu != ZUSTAND_RUECKLAEUFER:
                    continue
                e = dict(ledger.get(kennung) or {})
                e["zustand"] = zu
                e["titel"] = eintrag["titel"]
                e["slug"] = eintrag["slug"]
                e.setdefault("seit", heute(jetzt))
                ledger[kennung] = e
        ledger_speichern(ledger, pfad)
    lage["geheilt"] = geheilt
    return lage


def markdown(lage: dict) -> str:
    zeilen = ["", "## 🧾 Content-Reserve – Bestands-Wächter", "",
              f"- **Pool:** {len(lage['pool'])} Kandidaten mit Fahne"]
    if lage.get("geheilt"):
        zeilen.append(f"- **Fahne wiederhergestellt:** {len(lage['geheilt'])} "
                      "(Kandidat war im Pool, Entwurf vorhanden, Fahne fehlte)")
        for e in lage["geheilt"]:
            zeilen.append(f"  - `{e['slug']}`")
    if lage.get("ruecklaeufer"):
        zeilen.append(f"- **Rückläufer (Mensch entscheidet):** "
                      f"{len(lage['ruecklaeufer'])} – veröffentlicht und "
                      "danach wieder auf `draft` gesetzt")
        for e in lage["ruecklaeufer"]:
            zeilen.append(f"  - `{e['slug']}`")
    if lage.get("verwaist"):
        zeilen.append(f"- **Verschwunden:** {len(lage['verwaist'])} "
                      "(im Gedächtnis, aber keine Datei mehr)")
    return "\n".join(zeilen) + "\n"


def heal_quiet(posts_dir: Path = POSTS, *, pfad: Path | None = None) -> int:
    """Best-effort-Heilung für Aufrufer in der Produktionslinie.

    Darf NIE eine Ausnahme nach oben geben: Der Bestands-Wächter ist eine
    Absicherung, kein Gate – ein Fehler hier darf den Reserve-Lauf nicht
    abbrechen (der harte End-Gate urteilt ohnehin über den Pool-Stand).
    """
    try:
        lage = heilen(posts_dir, pfad=pfad)
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Bestands-Wächter nicht ausführbar: {exc}")
        return 0
    for e in lage.get("geheilt", []):
        print(f"🧾 Reserve-Fahne wiederhergestellt: {e['slug']} "
              f"(war im Pool, Fahne fehlte – Entwurf unverändert)")
    if lage.get("ruecklaeufer"):
        print(f"ℹ Rückläufer im Bestand ({len(lage['ruecklaeufer'])}): "
              "veröffentlicht und wieder auf draft gesetzt – "
              "Redaktion entscheidet (draft_triage zeigt sie).")
    return len(lage.get("geheilt", []))


# ---------------------------------------------------------------------------
#  Sabotage-Schutz
# ---------------------------------------------------------------------------
def _schreibe(posts: Path, slug: str, frontmatter_zeilen: str) -> Path:
    ordner = posts / slug
    ordner.mkdir(parents=True, exist_ok=True)
    index = ordner / "index.md"
    index.write_text(f"---\n{frontmatter_zeilen}\n---\n\nText.\n",
                     encoding="utf-8")
    return index


def run_selftest() -> int:
    import tempfile
    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        posts = Path(tmp) / "posts"
        pfad = Path(tmp) / "custody.json"

        pool = _schreibe(posts, "2026-09-26-pool",
                         'title: "Pool"\ndate: 2026-09-26\ndraft: true\n'
                         'reserve: true')
        verloren = _schreibe(posts, "2026-09-24-verloren",
                             'title: "Verloren"\ndate: 2026-09-24\ndraft: true')
        live = _schreibe(posts, "2026-09-20-live",
                         'title: "Live"\ndate: 2026-09-20\ndraft: false\n'
                         'reserve_published: 2026-09-20')
        rueck = _schreibe(posts, "2026-09-21-ruecklaeufer",
                          'title: "Rückläufer"\ndate: 2026-09-21\ndraft: true\n'
                          'reserve_published: 2026-09-21')
        fremd = _schreibe(posts, "2026-09-22-fremd",
                          'title: "Fremder Entwurf"\ndate: 2026-09-22\n'
                          'draft: true')
        retired = _schreibe(posts, "2026-09-23-zurueckgezogen",
                            'title: "Zurückgezogen"\ndate: 2026-09-23\n'
                            'draft: true\nreserve_retired: true')
        blockiert = _schreibe(posts, "2026-09-19-blockiert",
                              'title: "Ausgemustert"\ndate: 2026-09-19\n'
                              'draft: true\nreserve_blocked: R5')

        # Gedächtnis: „verloren", „retired" und „blockiert" waren im Pool.
        ledger_speichern({
            "verloren": {"zustand": "pool", "seit": "2026-09-24",
                         "herkunft": "Zertifikat 2026-09-25"},
            "zurueckgezogen": {"zustand": "pool", "seit": "2026-09-23"},
            "blockiert": {"zustand": "pool", "seit": "2026-09-19"},
        }, pfad)

        lage = heilen(posts, pfad=pfad, jetzt=dt.date(2026, 9, 26))

        # 1. Der reale Befund: Fahne zurück, Inhalt unangetastet.
        if [e["slug"] for e in lage["geheilt"]] != ["2026-09-24-verloren"]:
            fehler.append(f"Heilung traf die falschen Dateien: "
                          f"{[e['slug'] for e in lage['geheilt']]}")
        text = verloren.read_text(encoding="utf-8")
        if "reserve: true" not in text or "draft: true" not in text:
            fehler.append("Fahne wurde nicht korrekt gesetzt")
        if text.index("draft: true") > text.index("reserve: true"):
            fehler.append("reserve-Fahne steht nicht hinter draft")
        if "Text." not in text:
            fehler.append("Heilung hat den Artikelinhalt verändert")

        # 2. Was NICHT angefasst werden darf.
        if "reserve: true" in live.read_text(encoding="utf-8"):
            fehler.append("Live-Artikel wurde in den Pool gezogen")
        if "reserve: true" in rueck.read_text(encoding="utf-8"):
            fehler.append("Rückläufer wurde automatisch zurückgeholt "
                          "(gehört einem Menschen)")
        if "reserve: true" in fremd.read_text(encoding="utf-8"):
            fehler.append("Fremder Entwurf wurde in den Pool gezogen")
        if "reserve: true" in retired.read_text(encoding="utf-8"):
            fehler.append("reserve_retired (Mensch) wurde übergangen")
        if "reserve: true" in blockiert.read_text(encoding="utf-8"):
            fehler.append("Ausgemusterter Entwurf wurde reaktiviert")
        if [e["slug"] for e in lage["ruecklaeufer"]] != \
                ["2026-09-21-ruecklaeufer"]:
            fehler.append(f"Rückläufer nicht gemeldet: {lage['ruecklaeufer']}")

        # 3. Idempotenz: zweiter Lauf heilt nichts mehr.
        vorher = verloren.read_text(encoding="utf-8")
        lage2 = heilen(posts, pfad=pfad, jetzt=dt.date(2026, 9, 26))
        if lage2["geheilt"]:
            fehler.append("Heilung ist nicht idempotent")
        if verloren.read_text(encoding="utf-8") != vorher:
            fehler.append("Zweiter Lauf hat die Datei erneut verändert")

        # 4. Gedächtnis wächst mit: Der frische Pool-Kandidat ist erfasst.
        ledger = ledger_laden(pfad)
        if ledger.get("pool", {}).get("zustand") != ZUSTAND_POOL:
            fehler.append("Pool-Kandidat landet nicht im Gedächtnis")
        if ledger.get("blockiert", {}).get("zustand") != ZUSTAND_BLOCKIERT:
            fehler.append("Zustandswechsel (ausgemustert) nicht vermerkt")

        # 4b. RE-DATING (die Veredelung hebt Kandidaten auf heute und
        #     benennt den Ordner um): Das Gedächtnis darf dabei nichts
        #     verlieren und kein Phantom melden.
        (posts / "2026-09-26-pool").rename(posts / "2026-09-27-pool")
        nach_umbenennung = bestandsaufnahme(posts, pfad=pfad)
        if nach_umbenennung["verwaist"]:
            fehler.append(f"Re-Dating erzeugt Phantome: "
                          f"{nach_umbenennung['verwaist']}")
        if "2026-09-27-pool" not in [e["slug"] for e in
                                     nach_umbenennung["pool"]]:
            fehler.append("Re-Dating verliert den Pool-Kandidaten")
        pool = posts / "2026-09-27-pool" / "index.md"

        # 5. Trockenlauf schreibt nichts.
        opfer = _schreibe(posts, "2026-09-25-verloren2",
                          'title: "Verloren 2"\ndate: 2026-09-25\ndraft: true')
        ledger = ledger_laden(pfad)
        ledger["verloren2"] = {"zustand": "pool", "seit": "2026-09-25"}
        ledger_speichern(ledger, pfad)
        stand = pfad.read_text(encoding="utf-8")
        trocken = heilen(posts, pfad=pfad, dry_run=True)
        if not trocken["geheilt"]:
            fehler.append("Trockenlauf erkennt den Befund nicht")
        if "reserve: true" in opfer.read_text(encoding="utf-8"):
            fehler.append("Trockenlauf hat geschrieben")
        if pfad.read_text(encoding="utf-8") != stand:
            fehler.append("Trockenlauf hat das Gedächtnis verändert")

        # 6. Verschwundene Datei wird gemeldet, nicht verschwiegen.
        ledger["weg"] = {"zustand": "pool", "seit": "2026-09-01"}
        ledger_speichern(ledger, pfad)
        if "weg" not in bestandsaufnahme(posts, pfad=pfad)["verwaist"]:
            fehler.append("Verschwundener Kandidat wird nicht gemeldet")

    if fehler:
        print("🛑 RESERVE-CUSTODY-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Bestands-Wächter-Selbsttest grün (Fahne zurück, Inhalt "
          "unberührt, Live/Rückläufer/Fremd/zurückgezogen/ausgemustert "
          "unangetastet, idempotent, Trockenlauf schreibfrei, Gedächtnis).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Bestands-Wächter der "
                                             "Content-Reserve")
    ap.add_argument("--heal", action="store_true",
                    help="verlorene reserve-Fahnen wiederherstellen")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--md", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()

    lage = (heilen() if args.heal
            else {**bestandsaufnahme(), "geheilt": []})
    if args.json:
        print(json.dumps({k: (v if k in ("verwaist",)
                              else [e["slug"] for e in v])
                          for k, v in lage.items()}, ensure_ascii=False))
    elif args.md:
        print(markdown(lage))
    else:
        print(f"Reserve-Bestand: {len(lage['pool'])} im Pool · "
              f"{len(lage['verloren'])} ohne Fahne · "
              f"{len(lage['ruecklaeufer'])} Rückläufer · "
              f"{len(lage['blockiert'])} ausgemustert · "
              f"{len(lage['zurueckgezogen'])} von Hand zurückgezogen")
        for e in lage["geheilt"]:
            print(f"   🧾 Fahne wiederhergestellt: {e['slug']}")
        geheilt = {e["slug"] for e in lage["geheilt"]}
        for e in lage["verloren"]:
            if e["slug"] in geheilt:
                continue  # in diesem Lauf bereits zurückgeholt
            print(f"   ⛔ Fahne fehlt (heilbar mit --heal): {e['slug']}")
        for e in lage["ruecklaeufer"]:
            print(f"   👤 Rückläufer, Redaktion entscheidet: {e['slug']}")
        for slug in lage["verwaist"]:
            print(f"   ❓ im Gedächtnis, aber keine Datei mehr: {slug}")
    offen = bool([e for e in lage["verloren"]
                  if e["slug"] not in {g["slug"] for g in lage["geheilt"]}])
    return 1 if offen else 0


if __name__ == "__main__":
    raise SystemExit(main())
