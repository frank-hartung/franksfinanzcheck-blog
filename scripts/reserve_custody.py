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

import reserve_artifacts as artifacts  # noqa: E402
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
# Reparatur 07.10.2026 (#614): `\s*$` läuft mit (?m) über Zeilenenden
# hinweg – steht `draft: true` als LETZTE Frontmatter-Zeile, landete die
# Fahne dadurch am Ende des Kopfes (statt dahinter) oder die Suche griff
# ins Leere. [ \t] statt \s hält den Treffer auf seiner Zeile.
RE_DRAFT_ZEILE = re.compile(r"(?m)^draft:[ \t]*\S+[ \t]*$")
RE_RESERVE = re.compile(r"(?m)^reserve:\s*(?:true|yes|1)\s*$")
RE_PUBLISHED = re.compile(r"(?m)^reserve_published:")
RE_BLOCKED = re.compile(r"(?m)^reserve_blocked:")
RE_BLOCKED_GRUND = re.compile(r'(?m)^reserve_blocked:\s*"?(?P<grund>.*?)"?\s*$')
RE_BLOCKED_AT = re.compile(r"(?m)^reserve_blocked_at:.*$\n?")
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
        return artifacts.read_object(pfad)
    except FileNotFoundError:
        return {}


def ledger_speichern(data: dict, pfad: Path | None = None) -> None:
    pfad = ledger_pfad(pfad)
    artifacts.write_object(pfad, data, sort_keys=True)


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


# ---------------------------------------------------------------------------
#  RÜCKHOLUNG MIT BEWEIS (Reparatur 07.10.2026, BOT-WATCHDOG #614)
# ---------------------------------------------------------------------------
#  Bis hierher war die Ausmusterung eine EINBAHNSTRASSE. `reserve_quarantine`
#  nimmt einem Kandidaten die Fahne, sobald derselbe Befund in zwei Läufen
#  steht; dieser Wächter setzt das Gedächtnis auf „ausgemustert“ – und kein
#  Pfad führte je zurück. Am 07.10.2026 (Run 37645894042) nahm ein einziger
#  Lauf ZEHN Fahnen (Pool 12 -> 2); der halbe Vorrat war danach für die
#  Automatik unerreichbar, obwohl sechs der Befunde eine Klasse waren, die der
#  Politur-Heiler bzw. der Satz-Heiler inzwischen heilt. Ein Wächter, der
#  Material endgültig aussperrt, während die Heiler besser werden, macht den
#  Vorrat genau dann kleiner, wenn er gebraucht wird – „Automatisierung
#  braucht Eingriff“ (#614) in Reinform.
#
#  Deshalb gilt jetzt die Gegenregel, in derselben Bauart wie „Löschen braucht
#  einen Beweis“ (WF-B594) und „Nichts wird gelöscht“ (#295):
#
#      RÜCKHOLUNG BRAUCHT EINEN WIRKUNGS-NACHWEIS.
#
#  Ein ausgemusterter Entwurf kehrt in den Pool zurück, wenn ALLE drei gelten:
#    1. Sein Befund gehört einer Klasse an, die `reserve_blocker_klassen` als
#       HEILBAR führt (SSOT – geraten wird nichts),
#    2. mindestens einer der dort genannten Heiler läuft in der echten Kette
#       (`reserve_finisher.HEALER_CHAIN`), UND
#    3. genau dieser Heiler besitzt einen grünen Wirkungsnachweis
#       (`reserve_healer_coverage.WIRKUNGS_PROBEN`, Vertrag C25).
#  Fehlt einer der drei Belege, bleibt der Kandidat ausgemustert und wird mit
#  Grund gemeldet („unheilbar“, „kein Wirkungsnachweis“) – die Lücke ist der
#  Bericht, nicht der stille Verlust.
def rueckholbar(grund: str) -> tuple[bool, dict]:
    """Darf dieser ausgemusterte Befund den Vorrat zurückbekommen?"""
    grund = (grund or "").strip()
    try:
        import reserve_blocker_klassen as bk
    except Exception as exc:  # noqa: BLE001 – fail-closed: nichts zurückholen
        return False, {"klasse": "unbekannt", "beweis": [],
                       "warum": f"Klassen-SSOT nicht ladbar: {exc}"}
    bewertung = bk.gate_befund_klasse(grund)
    if bewertung["klasse"] != bk.HEILBAR:
        return False, {"klasse": bewertung["klasse"], "beweis": [],
                       "warum": bewertung["grund"]}
    try:
        import reserve_finisher as fin
        import reserve_healer_coverage as rhc
        kette = {e[0] for e in fin.HEALER_CHAIN}
        proben = set(rhc.WIRKUNGS_PROBEN)
    except Exception as exc:  # noqa: BLE001 – ohne prüfbare Kette kein Beweis
        return False, {"klasse": bewertung["klasse"], "beweis": [],
                       "warum": f"Kette/Nachweise nicht prüfbar: {exc}"}
    beweis = sorted(set(bewertung["heiler"]) & kette & proben)
    if not beweis:
        return False, {"klasse": bewertung["klasse"], "beweis": [],
                       "warum": ("Klasse ist heilbar, aber kein Heiler der "
                                 "Klasse hat einen grünen Wirkungsnachweis in "
                                 "der Kette")}
    return True, {"klasse": bewertung["klasse"], "beweis": beweis,
                  "warum": bewertung["grund"]}


def reaktivieren(text: str, hinweis: str) -> str | None:
    """Fahne zurück + Belegzeile – oder None, wenn es kein Entwurf ist.

    Der Entwurf wird NIE inhaltlich angefasst: Es fallen nur die beiden
    Ausmusterungs-Zeilen, `reserve: true` kommt hinter `draft: true` (wie in
    `fahne_setzen`) und die Rückholung wird mit Datum, Klasse und Beweis
    begründet – der nächste Leser soll nicht raten müssen, warum ein
    ehemals ausgemusterter Text wieder im Pool steht.
    """
    if not RE_DRAFT_TRUE.search(frontmatter(text)):
        return None
    teile = text.split("---", 2)
    if len(teile) != 3 or teile[0] != "":
        return None
    fm_neu = RE_BLOCKED_AT.sub("", teile[1])
    fm_neu = RE_BLOCKED_GRUND.sub("", fm_neu)
    fm_neu = re.sub(r"\n{3,}", "\n\n", fm_neu)
    neu = fahne_setzen("---" + fm_neu + "---" + teile[2])
    if neu is None:
        return None
    zeile = "reserve_reaktiviert: " + json.dumps(hinweis, ensure_ascii=False)
    # Belegzeile direkt hinter die Fahne. Muster bewusst mit [ \t] statt \s:
    # `\s*$` läuft mit (?m) über Zeilenenden hinweg und frisst den Text –
    # genau dieser Fehler wurde beim Bau gegen die Fixture gefunden.
    return re.sub(r"(?m)^(reserve:[ \t]*true[ \t]*)$",
                  lambda m: m.group(1) + "\n" + zeile, neu, count=1)


def _quarantaene_zuruecksetzen(slug: str) -> None:
    """Zähler eines zurückgeholten Kandidaten löschen (er beginnt bei null)."""
    try:
        import reserve_quarantine as rq
        state = rq.load_state(rq.STATE)
        if state.pop(slug, None) is not None:
            rq.save_state(state, rq.STATE)
    except Exception:  # noqa: BLE001 – Bestands-Wächter ist keine Blockade
        pass


def rueckholen(lage: dict, posts_dir: Path = POSTS, *, dry_run: bool = False,
               jetzt: dt.date | None = None) -> list[dict]:
    """Heilbare Ausgemusterte zurück in den Vorrat holen (mit Beweis).

    Rückgabe: die zurückgeholten Einträge. `lage` wird mitgeführt –
    Zurückgeholte wandern von `blockiert` nach `pool`, damit das Gedächtnis
    (und der Bericht) denselben Stand liest wie die Dateien.
    """
    reaktiviert: list[dict] = []
    abgelehnt: list[dict] = []
    for eintrag in list(lage.get("blockiert") or []):
        index = Path(eintrag.get("pfad") or "")
        try:
            text = index.read_text(encoding="utf-8")
        except OSError:
            continue
        m = RE_BLOCKED_GRUND.search(frontmatter(text))
        grund = (m.group("grund") if m else "") or ""
        ok, info = rueckholbar(grund)
        if not ok:
            abgelehnt.append({**eintrag, "klasse": info["klasse"],
                              "warum": info["warum"]})
            continue
        hinweis = (f"{heute(jetzt)} – Rückholung (#614): Befund der Klasse "
                   f"\u201e{info['klasse']}\u201c ist heilbar, "
                   f"Wirkungsnachweis {', '.join(info['beweis'])}")
        neu = reaktivieren(text, hinweis)
        if neu is None:
            abgelehnt.append({**eintrag, "klasse": info["klasse"],
                              "warum": "nicht reaktivierbar (kein Entwurf)"})
            continue
        if not dry_run:
            index.write_text(neu, encoding="utf-8")
            _quarantaene_zuruecksetzen(eintrag["slug"])
        reaktiviert.append({**eintrag, "klasse": info["klasse"],
                            "beweis": info["beweis"], "hinweis": hinweis})
        lage["blockiert"].remove(eintrag)
        lage["pool"].append(eintrag)
    lage["reaktiviert"] = reaktiviert
    lage["nicht_reaktiviert"] = abgelehnt
    return reaktiviert


def bestandsaufnahme(posts_dir: Path = POSTS, *, pfad: Path | None = None) -> dict:
    """Aktueller Zustand aller je bekannten Kandidaten + Befunde.

    IDENTITÄTS-REGEL (Reparatur WF-B594, 05.10.2026, Issue #594):
    Der Ledger-Schlüssel ist datumslos (`schluessel()`), damit die
    Veredelungs-Stufe Ordner umdatieren darf. Zwei Artikel können denselben
    Stamm tragen – im Bestand etwa `2026-09-22-konto-karten-update-…` und
    `2026-09-29-konto-karten-update-…`. Vor dieser Reparatur heilte
    `--heal` die Fahne am FALSCHEN der beiden: Der Nachtlauf zog einen nie
    übernommenen Entwurf still in den Pool, überschrieb im Ledger den
    gemerkten Slug und umging damit das Übernahmeprotokoll
    (`data/reserve-intake.json`). Genau diese Sorte stiller Pool-Mutation
    produziert die Watchdog-Befunde, die dann Handarbeit verlangen.

    Deshalb gilt: Hat das Ledger einen konkreten `slug` gemerkt, heilt nur
    dieser eine Pfad. Namensgleiche Geschwister landen in `namensgleich`
    und werden berichtet, nicht angefasst. Alt-Einträge ohne `slug` bleiben
    wie bisher über den Stamm heilbar.
    """
    pfad = ledger_pfad(pfad)
    ledger = ledger_laden(pfad)
    (pool, verloren, ruecklaeufer, blockiert, zurueckgezogen,
     ohne_nachweis) = [], [], [], [], [], []
    namensgleich: list[dict] = []
    gesehen = set()
    # Rückläufer-VERDACHT (reserve_published + draft) wird erst mit einem
    # LIVE-Zwilling zum Rückläufer; ohne Nachweis: `ruecklaeufer_ohne_nachweis`
    # → Material, das der Janitor zurückschont und in den Vorrat zurückholt.

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
                # WF-54C4 #610 (07.10.2026): `reserve_published` + `draft: true`
                # ist ein VERDACHT, kein Beweis. Erst ein LIVE-Artikel mit
                # demselben Thema (Titel oder Slug-Rumpf) belegt, dass „der
                # Inhalt live weiterlebt“. Ohne Zwilling kehrt der Entwurf als
                # Material zurück (reserve_pool.zurueck_in_den_pool) und wird
                # niemals als Rückläufer gelöscht – genau diese Verwechslung
                # vernichtete am 05.10.2026 den einzigen Nachschub des Tages.
                try:
                    import reserve_pool as _rp
                    eintrag["live_zwilling"] = _rp.live_zwilling(slug, posts_dir)
                except Exception:  # noqa: BLE001 – fail-closed: ohne Beweis kein Löschen
                    eintrag["live_zwilling"] = None
                if eintrag["live_zwilling"]:
                    ruecklaeufer.append(eintrag)
                else:
                    ohne_nachweis.append(eintrag)
            elif zu == ZUSTAND_VERLOREN and ledger.get(
                    schluessel(slug), {}).get("zustand") == ZUSTAND_POOL:
                merk = ledger[schluessel(slug)]
                gemerkter_slug = merk.get("slug")
                if gemerkter_slug and gemerkter_slug != slug:
                    # NAMENSGLEICH, aber nicht derselbe Artikel (WF-B594).
                    namensgleich.append({**eintrag,
                                         "gemerkter_slug": gemerkter_slug})
                    continue
                # Der Kern-Befund: war im Pool, ist Entwurf, Fahne fehlt.
                eintrag["seit"] = merk.get("seit")
                eintrag["herkunft"] = merk.get("herkunft", "")
                verloren.append(eintrag)
    # Kandidaten, die das Ledger kennt, die es aber nicht mehr gibt.
    verwaist = [kennung for kennung, e in ledger.items()
                if kennung not in gesehen
                and e.get("zustand") == ZUSTAND_POOL]
    return {"pool": pool, "verloren": verloren, "ruecklaeufer": ruecklaeufer,
            "blockiert": blockiert, "zurueckgezogen": zurueckgezogen,
            "ruecklaeufer_ohne_nachweis": ohne_nachweis,
            "verwaist": sorted(verwaist), "namensgleich": namensgleich}


def heilen(posts_dir: Path = POSTS, *, pfad: Path | None = None,
           dry_run: bool = False, jetzt: dt.date | None = None) -> dict:
    """Verlorene Fahnen wiederherstellen und das Ledger fortschreiben."""
    pfad = ledger_pfad(pfad)
    lage = bestandsaufnahme(posts_dir, pfad=pfad)
    ledger = ledger_laden(pfad)
    # Rückholung VOR dem Gedächtnis-Schreiben: Ein zurückgeholter Kandidat ist
    # wieder Pool und darf unten nicht als „ausgemustert“ vermerkt werden.
    reaktiviert = rueckholen(lage, posts_dir, dry_run=dry_run, jetzt=jetzt)
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

    if reaktiviert and not dry_run:
        # Der Beweis reist mit: Wer einen Kandidaten zurückholt, hinterlässt
        # die Zählung im Gedächtnis (nachvollziehbar, nicht nur gedruckt).
        for eintrag in reaktiviert:
            kennung = schluessel(eintrag["slug"])
            e = dict(ledger.get(kennung) or {})
            e["reaktiviert"] = int(e.get("reaktiviert") or 0) + 1
            e["zuletzt_reaktiviert"] = heute(jetzt)
            e["reaktiviert_mit"] = list(eintrag.get("beweis") or [])
            ledger[kennung] = e

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
    if lage.get("reaktiviert"):
        zeilen.append(f"- **Rückholung mit Beweis (#614):** "
                      f"{len(lage['reaktiviert'])} – ausgemustert war eine "
                      "Sackgasse; die Befund-Klasse ist heilbar und hat einen "
                      "grünen Wirkungsnachweis")
        for e in lage["reaktiviert"]:
            zeilen.append(f"  - `{e['slug']}` ← "
                          f"{', '.join(e.get('beweis') or []) or '?'}")
    if lage.get("nicht_reaktiviert"):
        zeilen.append(f"- **Weiter ausgemustert:** "
                      f"{len(lage['nicht_reaktiviert'])} (unheilbar oder ohne "
                      "Wirkungsnachweis – der Befund ist der Bericht)")
    if lage.get("ruecklaeufer"):
        zeilen.append(f"- **Rückläufer (Mensch entscheidet):** "
                      f"{len(lage['ruecklaeufer'])} – veröffentlicht und "
                      "danach wieder auf `draft` gesetzt")
        for e in lage["ruecklaeufer"]:
            zeilen.append(f"  - `{e['slug']}`")
    if lage.get("ruecklaeufer_ohne_nachweis"):
        zeilen.append("- **Ohne LIVE-Nachweis (Material, kein Rückläufer):** "
                      f"{len(lage['ruecklaeufer_ohne_nachweis'])} – "
                      "`reserve_published` + `draft`, aber kein LIVE-Artikel "
                      "mit gleichem Thema; wird nicht gelöscht (#610)")
        for e in lage["ruecklaeufer_ohne_nachweis"]:
            zeilen.append(f"  - `{e['slug']}`")
    if lage.get("namensgleich"):
        zeilen.append(f"- **Namensgleich, nicht angefasst:** "
                      f"{len(lage['namensgleich'])} – gleicher Slug-Stamm wie "
                      "ein Pool-Kandidat, aber ein anderer Artikel "
                      "(Übernahme nur über `reserve_intake.py`)")
        for e in lage["namensgleich"]:
            zeilen.append(f"  - `{e['slug']}` (Gedächtnis kennt "
                          f"`{e['gemerkter_slug']}`)")
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
    for e in lage.get("namensgleich", []):
        print(f"ℹ Namensgleicher Entwurf geschont: {e['slug']} – das "
              f"Gedächtnis meint `{e['gemerkter_slug']}`. Keine Fahne "
              "gesetzt; Übernahme läuft nur über reserve_intake.py.")
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
        # WF-54C4 #610: Der LIVE-Nachweis macht den Verdacht zum Rückläufer.
        _schreibe(posts, "2026-09-20-ruecklaeufer-live",
                  'title: "Rückläufer"\ndate: 2026-09-20\ndraft: false')
        # Ohne diesen Nachweis ist es KEIN Rückläufer, sondern nicht
        # ausgelieferter Nachschub – Material, das zurück in den Vorrat muss.
        ohne_nachweis = _schreibe(posts, "2026-09-21-ohne-nachweis",
                                  'title: "Ohne Nachweis"\ndate: 2026-09-21\n'
                                  'draft: true\nreserve_published: 2026-09-21')
        fremd = _schreibe(posts, "2026-09-22-fremd",
                          'title: "Fremder Entwurf"\ndate: 2026-09-22\n'
                          'draft: true')
        retired = _schreibe(posts, "2026-09-23-zurueckgezogen",
                            'title: "Zurückgezogen"\ndate: 2026-09-23\n'
                            'draft: true\nreserve_retired: true')
        blockiert = _schreibe(posts, "2026-09-19-blockiert",
                              'title: "Ausgemustert"\ndate: 2026-09-19\n'
                              'draft: true\nreserve_blocked: R5')
        # REPARATUR 07.10.2026 (#614): Ein ausgemusterter Kandidat, dessen
        # Befund eine heilbare Klasse MIT grünem Wirkungsnachweis ist, kehrt
        # zurück. Der Befund ist wörtlich der des Vorfalls (Flesch 58.0).
        heilbar_blockiert = _schreibe(
            posts, "2026-09-18-heilbar-blockiert",
            'title: "Ausgemustert, aber heilbar"\ndate: 2026-09-18\n'
            'draft: true\n'
            'reserve_blocked: "Lesbarkeits-Gate nicht bestanden: Flesch 58.0 '
            '(Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den '
            'Bestands-Durchschnitt nach unten (#585)"\n'
            'reserve_blocked_at: 2026-09-18T06:00:00Z')

        # Gedächtnis: „verloren", „retired" und „blockiert" waren im Pool.
        ledger_speichern({
            "verloren": {"zustand": "pool", "seit": "2026-09-24",
                         "herkunft": "Zertifikat 2026-09-25"},
            "zurueckgezogen": {"zustand": "pool", "seit": "2026-09-23"},
            "blockiert": {"zustand": "pool", "seit": "2026-09-19"},
            "heilbar-blockiert": {"zustand": "pool", "seit": "2026-09-18"},
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
        if lage["ruecklaeufer"] and lage["ruecklaeufer"][0].get(
                "live_zwilling") != "2026-09-20-ruecklaeufer-live":
            fehler.append("LIVE-Nachweis des Rückläufers fehlt: "
                          f"{lage['ruecklaeufer'][0]}")
        if [e["slug"] for e in lage["ruecklaeufer_ohne_nachweis"]] != \
                ["2026-09-21-ohne-nachweis"]:
            fehler.append("Nachschub ohne Nachweis nicht als eigener Zustand "
                          f"gemeldet: {lage['ruecklaeufer_ohne_nachweis']}")
        if "reserve: true" in ohne_nachweis.read_text(encoding="utf-8"):
            fehler.append("Nachweis-loser Nachschub wurde in den Pool gezogen "
                          "(nur der Janitor holt ihn zurück, #610)")

        # 2b. RÜCKHOLUNG MIT BEWEIS (#614): Der heilbar Ausgemusterte ist
        #     wieder Pool – mit Belegzeile, ohne Ausmusterungs-Zeilen, und der
        #     Inhalt ist unangetastet. Der unklassifizierte "R5"-Fall bleibt
        #     dagegen ausgemustert (fail-closed).
        reaktiviert = [e["slug"] for e in lage.get("reaktiviert", [])]
        if reaktiviert != ["2026-09-18-heilbar-blockiert"]:
            fehler.append(f"Rückholung traf die falschen Dateien: {reaktiviert}")
        text_hb = heilbar_blockiert.read_text(encoding="utf-8")
        if "reserve: true" not in text_hb:
            fehler.append("Rückholung hat die Fahne nicht gesetzt")
        if "reserve_blocked:" in text_hb or "reserve_blocked_at:" in text_hb:
            fehler.append("Rückholung ließ die Ausmusterungs-Zeilen stehen")
        if "reserve_reaktiviert:" not in text_hb:
            fehler.append("Rückholung ohne Belegzeile (nicht nachvollziehbar)")
        if "Wirkungsnachweis" not in text_hb:
            fehler.append("Belegzeile nennt den Wirkungsnachweis nicht")
        if "Text." not in text_hb:
            fehler.append("Rückholung hat den Artikelinhalt verändert")
        haerte = [e["slug"] for e in lage.get("nicht_reaktiviert", [])]
        if haerte != ["2026-09-19-blockiert"]:
            fehler.append(f"Fail-closed-Liste falsch: {haerte}")

        # 3. Idempotenz: zweiter Lauf heilt nichts mehr.
        vorher = verloren.read_text(encoding="utf-8")
        lage2 = heilen(posts, pfad=pfad, jetzt=dt.date(2026, 9, 26))
        if lage2["geheilt"]:
            fehler.append("Heilung ist nicht idempotent")
        if lage2.get("reaktiviert"):
            fehler.append("Rückholung ist nicht idempotent")
        if verloren.read_text(encoding="utf-8") != vorher:
            fehler.append("Zweiter Lauf hat die Datei erneut verändert")

        # 4. Gedächtnis wächst mit: Der frische Pool-Kandidat ist erfasst.
        ledger = ledger_laden(pfad)
        if ledger.get("pool", {}).get("zustand") != ZUSTAND_POOL:
            fehler.append("Pool-Kandidat landet nicht im Gedächtnis")
        if ledger.get("blockiert", {}).get("zustand") != ZUSTAND_BLOCKIERT:
            fehler.append("Zustandswechsel (ausgemustert) nicht vermerkt")
        if ledger.get("heilbar-blockiert", {}).get("zustand") != ZUSTAND_POOL:
            fehler.append("Rückgeholter Kandidat nicht als Pool vermerkt")
        if int(ledger.get("heilbar-blockiert", {}).get("reaktiviert") or 0) != 1:
            fehler.append("Rückholung nicht im Gedächtnis gezählt")

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
    print("✅ Bestands-Wächter-Selbsttest grün (Rückholung mit Beweis #614, "
          "Fahne zurück, Inhalt "
          "unberührt, Live/Rückläufer/Fremd/zurückgezogen/ausgemustert "
          "unangetastet, Rückläufer nur MIT LIVE-Nachweis, Nachschub ohne "
          "Nachweis als eigener Zustand (#610), idempotent, Trockenlauf "
          "schreibfrei, Gedächtnis).")
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
              f"{len(lage.get('ruecklaeufer_ohne_nachweis', []))} ohne "
              f"LIVE-Nachweis · "
              f"{len(lage['blockiert'])} ausgemustert · "
              f"{len(lage['zurueckgezogen'])} von Hand zurückgezogen")
        for e in lage["geheilt"]:
            print(f"   🧾 Fahne wiederhergestellt: {e['slug']}")
        for e in lage.get("reaktiviert", []):
            print(f"   ♻️  Rückgeholt (Klassen-Beweis): {e['slug']} ← "
                  f"{', '.join(e.get('beweis') or [])}")
        for e in lage.get("nicht_reaktiviert", []):
            print(f"   🧱 bleibt ausgemustert: {e['slug']} "
                  f"[{e.get('klasse') or '?'}] – {e.get('warum', '')[:90]}")
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
