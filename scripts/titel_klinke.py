#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""TITEL-KLINKE – Titel-Befunde an bereits veröffentlichten Artikeln
dürfen nicht unsichtbar bleiben (#1304).

WARUM ES DIESE WACHE GIBT (#1304, 22.11.2026)
=============================================
Am 20.11.2026 landete ein Titel mit 64 Zeichen im Bestand
(`Kfz-Versicherung vergleichen: Was ändert sich außer dem Beitrag?`,
Artikel vom 26.08.2026). Er blieb tagelang unbemerkt, obwohl ZWEI Wachen
ihn sehen:

  · `metadaten_wache.py` M1 (Titel 1–60 Zeichen) – Exit 1, aber C34:
    ein Befund stoppt die Auslieferung NICHT. Der Meldebestand wächst,
    niemand muss ihn je schließen.
  · `check_titles.py` R1 (Titel > 45 Zeichen ohne Doppelpunkt) – prüft
    den Bestand, meldet aber nur; die Redaktion liest es oder nicht.

Beide Wachen sind richtig gebaut. Was fehlte, war die KLINKE: ein Zustand,
der nicht schlechter werden kann. Eine Meldung, die jeden Tag erneut
erscheint, wird nach einer Woche weggeklickt – das ist keine Wache, das
ist Rauschen.

DIE KLINKE (Haus-Muster, wie `scripts/struktur_guard.py`)
========================================================
`data/titel_baseline.json` hält je Artikel den akzeptierten Titel-Stand.
Die Wache lässt ihn NUR BESSER WERDEN:

  · Ein NEUER Befund (Artikel war grün, ist jetzt rot) → Exit 1.
  · Ein Befund, der in der Baseline steht, bleibt Meldung (Exit 0) –
    er ist bekannt, die Redaktion hat ihn auf dem Zettel.
  · Ein geheilter Befund rastet ein: die Baseline zieht nach, und ein
    Rückfall (Titel wieder zu lang) ist ab dann ein NEUER Befund.
  · Ein Titel, der sich ändert, wird neu bewertet: wird er dabei
    schlechter als der eingefrorene Stand, ist das ein Fund.

Damit ist der Bestand ab heute eingefroren, ohne dass ein einziger
bestehender Befund die Auslieferung blockiert (C34 bleibt gewahrt).

WAS GEPRÜFT WIRD (nur, was eine Zahl oder eine harte Regel hat)
--------------------------------------------------------------
  T1  Titel > TITLE_MAX (60) Zeichen            – SERP kürzt
  T2  Titel fehlt oder ist leer
  T3  Titel > 45 Zeichen OHNE Doppelpunkt        – Cover-Umbruch kaputt
      (Blog-Konvention „Hauptkeyword: Untertitel“, check_titles.py R1)
  T4  Titel-Änderung gegenüber der Baseline, die einen bekannten
      Befund NICHT behebt und den Titel nicht verbessert

Bewusst NICHT hier: Stilurteile, Keyword-Dichte, „klickstark“. Eine
Klinke braucht eine Schwelle, die man messen kann – nicht eine Meinung.

NUTZUNG
-------
  python3 scripts/titel_klinke.py               # prüfen (Exit 0/1/2)
  python3 scripts/titel_klinke.py --json        # maschinenlesbar
  python3 scripts/titel_klinke.py --md          # Markdown (Job-Summary)
  python3 scripts/titel_klinke.py --seed        # Baseline einfrieren
  python3 scripts/titel_klinke.py --dry-run     # nichts schreiben
  python3 scripts/titel_klinke.py --selftest    # Sabotage-Proben

EXIT: 0 = keine NEUEN Befunde · 1 = neuer/verschlechterter Befund ·
      2 = Selbsttest oder Setup defekt (fail-closed, es wird nichts
      geschrieben)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
BASELINE = ROOT / "data" / "titel_baseline.json"
HISTORY = ROOT / "data" / "titel_history.jsonl"

sys.path.insert(0, str(SCRIPTS))

# Grenzen kommen aus den vorhandenen Wachen, nicht aus einer dritten Zahl.
# (Hausregel: eine Wahrheit. TITLE_MAX steht in metadaten_wache.py, die
# Doppelpunkt-Konvention in check_titles.py – hier wird nur gelesen.)
TITLE_MAX = 60               # M1 in metadaten_wache.py
TITLE_NO_COLON_MAX = 45      # R1 in check_titles.py

CONTENT_GLOBS = (
    "content/posts/*.md",
    "content/posts/*/index.md",
    "content/pillar/*/index.md",
)
SKIP_BASENAMES = {"_index.md"}

RE_FM = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.S)
RE_TITLE = re.compile(r"^title:\s*(?P<wert>.*?)\s*$", re.M)


# ======================================================================
#  Frontmatter (stdlib – die Klinke muss auch ohne PyYAML laufen)
# ======================================================================
def _unquote(wert: str) -> str:
    """YAML-Skalar grob entpacken – nur für `title:` gebraucht.

    Bewusst kein Parser: `title:` ist im Bestand ein einzeiliger Skalar
    (einfach, doppelt oder gar nicht zitiert). Wer hier einen Parser
    braucht, hat ein anderes Problem – und die Frontmatter-Wache meldet es.
    """
    wert = wert.strip()
    if len(wert) >= 2 and wert[0] == wert[-1] and wert[0] in ("'", '"'):
        inner = wert[1:-1]
        if wert[0] == "'":
            return inner.replace("''", "'")
        return (inner.replace('\\"', '"').replace("\\\\", "\\")
                .replace("\\n", "\n"))
    # Ein Kommentar hinter einem Plain-Skalar ist kein Titeltext.
    if " #" in wert:
        wert = wert.split(" #", 1)[0]
    return wert.strip()


def frontmatter_und_titel(text: str) -> tuple[str, bool]:
    """(Titel, hat_frontmatter) – Titel leer, wenn keiner dasteht."""
    m = RE_FM.match(text)
    if not m:
        return "", False
    treffer = RE_TITLE.search(m.group(1))
    if not treffer:
        return "", True
    return _unquote(treffer.group("wert")), True


def _norm_titel(titel: str) -> str:
    return re.sub(r"\s+", " ", titel.replace("\u00a0", " ")).strip()


def _draft(text: str) -> bool:
    m = RE_FM.match(text)
    if not m:
        return False
    d = re.search(r"^draft:\s*(true|false)\s*$", m.group(1), re.M)
    return bool(d and d.group(1) == "true")


# ======================================================================
#  Bewertung: nur messbare Regeln
# ======================================================================
def bewerte(titel: str, *, hat_frontmatter: bool = True) -> list[dict]:
    """Befunde eines Titels als [{"regel", "text", "wert"}]."""
    titel = _norm_titel(titel)
    befunde: list[dict] = []
    if not hat_frontmatter:
        befunde.append({"regel": "T2", "wert": 0,
                        "text": "Kein Frontmatter – Titel nicht prüfbar "
                                "(Hugo baut die Datei dann ohne Titel)."})
        return befunde
    if not titel:
        befunde.append({"regel": "T2", "wert": 0, "text": "Titel fehlt."})
        return befunde
    if len(titel) > TITLE_MAX:
        befunde.append({
            "regel": "T1", "wert": len(titel),
            "text": f"Titel {len(titel)} Zeichen (max. {TITLE_MAX}): "
                    f"{titel!r} – die SERP kürzt ihn ab."})
    if len(titel) > TITLE_NO_COLON_MAX and ":" not in titel:
        befunde.append({
            "regel": "T3", "wert": len(titel),
            "text": f"Titel {len(titel)} Zeichen ohne Doppelpunkt "
                    f"(Konvention „Hauptkeyword: Untertitel\") – der "
                    f"Cover-Umbruch bricht semantisch."})
    return befunde


def _schwere(befunde: list[dict]) -> int:
    """Eine Zahl je Artikel, damit „besser/schlechter“ vergleichbar ist.

    Absicht: T1 (SERP-Abschnitt) wiegt schwerer als T3 (Cover-Umbruch),
    weil T1 messbar Text abschneidet. Die Zahl ist nur für den Vergleich
    mit der Baseline da – sie taucht in keiner Meldung auf.
    """
    gewicht = {"T1": 2, "T2": 3, "T3": 1}
    return sum(gewicht.get(b["regel"], 1) for b in befunde)


# ======================================================================
#  Bestand einsammeln
# ======================================================================
def sammle_dateien(root: Path = ROOT) -> list[Path]:
    dateien: list[Path] = []
    for muster in CONTENT_GLOBS:
        dateien.extend(sorted(root.glob(muster)))
    return [p for p in sorted(set(dateien))
            if p.name not in SKIP_BASENAMES and p.is_file()]


def _schluessel(pfad: Path, root: Path = ROOT) -> str:
    return pfad.relative_to(root).as_posix()


def erhebe(root: Path = ROOT) -> tuple[dict, int]:
    """Aktuellen Stand erheben: {schlüssel: {titel, schwere, befund}}."""
    stand: dict = {}
    dateien = sammle_dateien(root)
    for pfad in dateien:
        try:
            text = pfad.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        titel, hat_fm = frontmatter_und_titel(text)
        befunde = bewerte(titel, hat_frontmatter=hat_fm)
        stand[_schluessel(pfad, root)] = {
            "titel": _norm_titel(titel),
            "draft": _draft(text),
            "schwere": _schwere(befunde),
            "befunde": [{"regel": b["regel"], "text": b["text"]} for b in befunde],
        }
    return stand, len(dateien)


# ======================================================================
#  Baseline lesen/schreiben
# ======================================================================
def lade_baseline() -> dict:
    if not BASELINE.exists():
        return {}
    try:
        daten = json.loads(BASELINE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return daten.get("artikel") or {}


def _schreibe_baseline(stand: dict, dry_run: bool = False) -> None:
    if dry_run:
        return
    BASELINE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE.write_text(json.dumps({
        "stand": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "hinweis": "Sperrklinke: nur abwärts. Erzeugt von "
                   "scripts/titel_klinke.py --seed.",
        "schwellen": {"T1_max_zeichen": TITLE_MAX,
                      "T3_max_zeichen_ohne_doppelpunkt": TITLE_NO_COLON_MAX},
        "artikel": dict(sorted(stand.items())),
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _schreibe_history(neu: int, bekannt: int, dateien: int, dry_run: bool) -> None:
    if dry_run:
        return
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    zeile = {
        "ts": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "module": "titel_klinke", "action": "check",
        "input": {"dateien": dateien},
        "output": {"neue_befunde": neu, "bekannte_befunde": bekannt},
        "status": "issues" if neu else "ok", "critical": False, "commit": None,
    }
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(zeile, ensure_ascii=False) + "\n")


# ======================================================================
#  Bewertung gegen die Baseline (die Klinke)
# ======================================================================
def vergleiche(stand: dict, baseline: dict) -> dict:
    """Teilt den Bestand in neu / bekannt / geheilt / verschlechtert.

    `verschlechtert` ist der interessante Fall: Der Titel wurde geändert
    (Redaktion war dran), der Befund ist aber geblieben oder schlimmer
    geworden. Genau das ist am 21.11.2026 passiert – Frank hat den Titel
    umformuliert, 64 Zeichen blieben 64 Zeichen. Ohne diese Klasse wäre
    eine Änderung ohne Wirkung als „neu“ gemeldet und dann stillgelegt
    worden.
    """
    neu, bekannt, verschlechtert, geheilt = [], [], [], []
    for schluessel, ist in sorted(stand.items()):
        alt = baseline.get(schluessel)
        if not ist["befunde"]:
            if alt and alt.get("schwere", 0) > 0:
                geheilt.append(schluessel)
            continue
        if alt is None:
            # Neuer Artikel: Ein Titel zu lang ist ein Befund, aber ein
            # frisch geborener Artikel ist redaktionelle Arbeit – er zählt
            # als NEU, wenn er veröffentlicht ist (Entwürfe nicht).
            (bekannt if ist["draft"] else neu).append(schluessel)
            continue
        if alt.get("schwere", 0) == 0:
            neu.append(schluessel)          # war grün, ist rot
        elif ist["schwere"] > alt.get("schwere", 0):
            verschlechtert.append(schluessel)
        elif ist["titel"] != alt.get("titel") and ist["schwere"] == alt.get("schwere"):
            # Titel geändert, Befund unverändert: Meldung, aber kein
            # neuer Fund – die Redaktion war dran, es hat nicht gereicht.
            verschlechtert.append(schluessel)
        else:
            bekannt.append(schluessel)
    return {"neu": neu, "bekannt": bekannt,
            "verschlechtert": verschlechtert, "geheilt": geheilt}


def klinke_einrasten(stand: dict, baseline: dict) -> dict:
    """Neue Baseline: je Artikel der BESSERE Stand (nie schlechter).

    Ein geheilter Befund rastet ein (`schwere` sinkt). Ein neuer Befund
    wird NICHT eingefroren, solange er offen ist – sonst wäre die Klinke
    ein Wegwischer: Der Fund wäre ab dem nächsten Lauf „bekannt“ und
    niemand müsste ihn je beheben.
    """
    neu = {}
    for schluessel, ist in sorted(stand.items()):
        alt = baseline.get(schluessel)
        if alt is None:
            neu[schluessel] = {"titel": ist["titel"],
                               "schwere": ist["schwere"]}
            continue
        if ist["schwere"] <= alt.get("schwere", 0):
            neu[schluessel] = {"titel": ist["titel"], "schwere": ist["schwere"]}
        else:
            # Verschlechterung nicht einfrieren: die Klinke hält den
            # besseren Stand fest, der Fund bleibt offen.
            neu[schluessel] = {"titel": alt.get("titel", ist["titel"]),
                               "schwere": alt.get("schwere", 0)}
    return neu


# ======================================================================
#  Ausgabe
# ======================================================================
def bericht_md(stand: dict, ergebnis: dict, baseline: dict, dateien: int) -> str:
    offen = sum(1 for s in stand.values() if s["befunde"])
    zeilen = ["### 🏷️ Titel-Klinke (Bestand, #1304)", ""]
    zeilen.append(
        f"**{dateien} Dateien** · **{offen} offene Titel-Befunde** · "
        f"**{len(ergebnis['neu'])} neu** · "
        f"**{len(ergebnis['verschlechtert'])} verschlechtert** · "
        f"**{len(ergebnis['geheilt'])} geheilt** · "
        f"Grenzen: T1 ≤ {TITLE_MAX}, T3 ≤ {TITLE_NO_COLON_MAX} ohne Doppelpunkt")
    if ergebnis["neu"] or ergebnis["verschlechtert"]:
        zeilen += ["", "| Artikel | Klasse | Befund |", "|---|---|---|"]
        for schluessel in ergebnis["neu"]:
            for b in stand[schluessel]["befunde"]:
                zeilen.append(f"| `{schluessel}` | **NEU** {b['regel']} | "
                              f"{b['text'].replace('|', chr(92) + '|')} |")
        for schluessel in ergebnis["verschlechtert"]:
            alt = baseline.get(schluessel) or {}
            zeilen.append(
                f"| `{schluessel}` | **SCHLECHTER** | Titel geändert, Befund "
                f"unverändert/schlimmer (vorher `{alt.get('titel', '?')}`) |")
    if ergebnis["bekannt"]:
        zeilen += ["", f"<details><summary>{len(ergebnis['bekannt'])} bekannte "
                       f"Befunde (in der Baseline, Redaktionssache)</summary>", ""]
        for schluessel in ergebnis["bekannt"]:
            for b in stand[schluessel]["befunde"]:
                zeilen.append(f"- `{schluessel}` ({b['regel']}): {b['text']}")
        zeilen += ["", "</details>"]
    if ergebnis["geheilt"]:
        zeilen += ["", "✅ Eingerastet (geheilt): "
                       + ", ".join(f"`{s}`" for s in ergebnis["geheilt"])]
    return "\n".join(zeilen) + "\n"


def _drucke(stand: dict, ergebnis: dict, baseline: dict, dateien: int,
            als_json: bool, als_md: bool) -> None:
    if als_json:
        print(json.dumps({
            "dateien": dateien,
            "offene_befunde": sum(1 for s in stand.values() if s["befunde"]),
            "neu": ergebnis["neu"],
            "verschlechtert": ergebnis["verschlechtert"],
            "bekannt": ergebnis["bekannt"],
            "geheilt": ergebnis["geheilt"],
            "befunde": {k: v["befunde"] for k, v in stand.items() if v["befunde"]},
        }, ensure_ascii=False, indent=2))
        return
    if als_md:
        print(bericht_md(stand, ergebnis, baseline, dateien))
        return
    offen = sum(1 for s in stand.values() if s["befunde"])
    print(f"Titel-Klinke: {dateien} Dateien | offen: {offen} | "
          f"neu: {len(ergebnis['neu'])} | "
          f"verschlechtert: {len(ergebnis['verschlechtert'])} | "
          f"bekannt: {len(ergebnis['bekannt'])} | "
          f"geheilt: {len(ergebnis['geheilt'])}")
    for schluessel in ergebnis["neu"]:
        for b in stand[schluessel]["befunde"]:
            print(f"  ❌ NEU {schluessel}: {b['text']}")
    for schluessel in ergebnis["verschlechtert"]:
        print(f"  ⚠ SCHLECHTER {schluessel}: Titel geändert, Befund "
              f"unverändert/schlimmer")
    for schluessel in ergebnis["bekannt"]:
        for b in stand[schluessel]["befunde"]:
            print(f"  · bekannt {schluessel}: {b['text']}")
    if ergebnis["geheilt"]:
        print(f"  ✅ eingerastet: {len(ergebnis['geheilt'])}")


# ======================================================================
#  Selbsttest: Sabotage-Proben
# ======================================================================
_GRUEN = "Frischer Titel mit Doppelpunkt: kurz genug"          # 42 Zeichen
_ROT_T1 = ("Kfz-Versicherung vergleichen: Was ändert sich außer "  # 64
           "dem Beitrag?")
_ROT_T3 = "Wie viel Bandbreite brauchst du fürs Streaming?"    # 47, kein :


def run_selftest(*, ausgabe=sys.stdout) -> int:
    """Sabotage-Proben. `ausgabe` ist umlenkbar, damit `--json`/`--md`
    einen SAUBEREN Datenstrom behalten (Hausregel: wer Maschinenformat
    anbietet, darf keine Grußzeile davor schreiben – sonst bricht jeder
    Parser, und der Vertrag ist nur Papier)."""
    fehler: list[str] = []

    def pruefe(name: str, ist: list[dict], soll: list[str]) -> None:
        if sorted(b["regel"] for b in ist) != sorted(soll):
            fehler.append(f"{name}: erwartet {soll}, bekommen "
                          f"{[b['regel'] for b in ist]}")

    def aus_datei(titelzeile: str) -> list[dict]:
        """Genau der Weg der Produktion: über das Frontmatter lesen.

        Wichtig, weil `bewerte()` den ENTQUOTETEN Titel bekommt – ein Test,
        der `bewerte('"Titel" # Kommentar')` aufruft, prüft die falsche
        Schnittstelle (und zählt den Kommentar als Titeltext).
        """
        text = f"---\ntitle: {titelzeile}\ndate: 2026-01-01\n---\n\nText.\n"
        titel, hat_fm = frontmatter_und_titel(text)
        return bewerte(titel, hat_frontmatter=hat_fm)

    # 1) Der echte Fall vom 20.11.2026: 64 Zeichen → T1 (T3 greift nicht,
    #    weil der Titel einen Doppelpunkt hat).
    pruefe("64 Zeichen mit Doppelpunkt", bewerte(_ROT_T1), ["T1"])
    # 2) Genau an der Grenze: 60 Zeichen ist erlaubt, 61 nicht.
    #    (`A`*56 + ": bb" = 60 Zeichen, `A`*57 + ": bb" = 61.)
    pruefe("60 Zeichen ist grün", bewerte("A" * 56 + ": bb"), [])
    pruefe("61 Zeichen ist rot", bewerte("A" * 57 + ": bb"), ["T1"])
    # 3) R1-Konvention: 47 Zeichen ohne Doppelpunkt → T3, nicht T1.
    pruefe("lang ohne Doppelpunkt", bewerte(_ROT_T3), ["T3"])
    # 4) Kurz ohne Doppelpunkt ist in Ordnung (Cover bricht nicht).
    pruefe("kurz ohne Doppelpunkt", bewerte("Strom sparen im Alltag"), [])
    # 5) Leerer/fehlender Titel → T2, und zwar NUR T2 (kein Folgefehler).
    pruefe("leerer Titel", bewerte(""), ["T2"])
    pruefe("kein Frontmatter", bewerte("", hat_frontmatter=False), ["T2"])
    if len(_GRUEN) > TITLE_MAX:      # Selbstschutz: Testdaten müssen passen
        fehler.append(f"_GRUEN ist {len(_GRUEN)} Zeichen – Testaufbau kaputt")
    # 6) Zitate und Kommentare dürfen die Länge nicht verfälschen – und
    #    zwar auf dem Weg, den die Produktion geht (Frontmatter-Zeile).
    pruefe("zitiert", aus_datei(f"'{_ROT_T1}'"), ["T1"])
    # Ein Kommentar hinter einem PLAIN-Skalar ist kein Titeltext; hinter
    # einem Zitat ohnehin nicht (dort ist `#` Text).
    pruefe("Kommentar hinter Zitat",
           aus_datei(f'"{_GRUEN}"  # Kürzer wäre: ' + "x" * 40), [])
    pruefe("Kommentar hinter Plain-Skalar",
           aus_datei(_GRUEN + "  # zu lang wäre: " + "x" * 40), [])
    # 7) Das echte Frontmatter-Paar (der Vorfall) wird aus Text gelesen.
    text = f"---\ntitle: '{_ROT_T1}'\ndate: 2026-08-26\n---\n\nText.\n"
    titel, hat_fm = frontmatter_und_titel(text)
    if titel != _ROT_T1:
        fehler.append(f"Frontmatter-Leser: {titel!r} statt {_ROT_T1!r}")
    if not hat_fm:
        fehler.append("Frontmatter-Leser: Frontmatter nicht erkannt")
    # 8) Die Klinke: gleicher Stand ist kein neuer Fund …
    stand = {"a": {"titel": _ROT_T1, "draft": False, "schwere": 2,
                   "befunde": bewerte(_ROT_T1)}}
    basis = {"a": {"titel": _ROT_T1, "schwere": 2}}
    e = vergleiche(stand, basis)
    if e["neu"] or e["verschlechtert"]:
        fehler.append(f"Klinke: bekannter Befund als neu gemeldet: {e}")
    # … 9) war grün, ist rot → NEU (das ist der Daseinszweck) …
    basis_gruen = {"a": {"titel": _GRUEN, "schwere": 0}}
    e = vergleiche(stand, basis_gruen)
    if e["neu"] != ["a"]:
        fehler.append(f"Klinke: grün→rot nicht als NEU gemeldet: {e}")
    # … 10) geheilt → eingerastet, und die Baseline zieht nach …
    stand_gruen = {"a": {"titel": _GRUEN, "draft": False, "schwere": 0,
                         "befunde": []}}
    e = vergleiche(stand_gruen, basis)
    if e["geheilt"] != ["a"]:
        fehler.append(f"Klinke: Heilung nicht erkannt: {e}")
    neu_basis = klinke_einrasten(stand_gruen, basis)
    if neu_basis["a"]["schwere"] != 0:
        fehler.append("Klinke: Heilung rastet nicht ein")
    # … 11) und ein Rückfall ist danach NEU, nicht „bekannt“.
    e = vergleiche(stand, neu_basis)
    if e["neu"] != ["a"]:
        fehler.append(f"Klinke: Rückfall nach Heilung nicht NEU: {e}")
    # … 12) Verschlechterung wird NICHT eingefroren (Klinke ist kein
    #    Wegwischer) – der offene Fund bleibt offen.
    neu_basis2 = klinke_einrasten(stand, basis_gruen)
    if neu_basis2["a"]["schwere"] != 0:
        fehler.append("Klinke: Verschlechterung wurde eingefroren (Wegwischer)")
    # 13) Titel geändert, Befund gleich → gemeldet, aber nicht „neu“.
    geaendert = {"a": {"titel": _ROT_T1 + "!", "draft": False, "schwere": 2,
                       "befunde": bewerte(_ROT_T1 + "!")}}
    e = vergleiche(geaendert, basis)
    if e["verschlechtert"] != ["a"]:
        fehler.append(f"Klinke: wirkungslose Änderung nicht gemeldet: {e}")
    # 14) Entwurf mit Befund ist kein NEU (redaktionelle Arbeit).
    entwurf = {"a": {"titel": _ROT_T1, "draft": True, "schwere": 2,
                     "befunde": bewerte(_ROT_T1)}}
    e = vergleiche(entwurf, {})
    if e["neu"]:
        fehler.append(f"Klinke: Entwurf als NEU gemeldet: {e}")

    if fehler:
        print("🛑 Titel-Klinke Selbsttest FEHLGESCHLAGEN:", file=ausgabe)
        for f in fehler:
            print("   -", f, file=ausgabe)
        return 2
    print("✅ Titel-Klinke Selbsttest: 20 Proben bestanden – die Klinke "
          "rastet ein und lässt nichts durch.", file=ausgabe)
    return 0


# ======================================================================
#  main
# ======================================================================
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Titel-Klinke: Titel-Befunde im Bestand (#1304)")
    ap.add_argument("--json", action="store_true", help="maschinenlesbar")
    ap.add_argument("--md", action="store_true", help="Markdown")
    ap.add_argument("--seed", action="store_true",
                    help="aktuellen Stand als Baseline einfrieren")
    ap.add_argument("--dry-run", action="store_true", help="nichts schreiben")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args(argv)

    # Hausregel: erst der Detektor, dann der Prüfling. Ein Selbsttest, der
    # rot ist, darf nichts schreiben – sonst friert eine kaputte Wache
    # einen falschen Stand ein.
    maschinenformat = args.json or args.md
    if run_selftest(ausgabe=sys.stderr if maschinenformat else sys.stdout) != 0:
        return 2
    if args.selftest:
        return 0

    stand, dateien = erhebe()
    baseline = lade_baseline()
    ergebnis = vergleiche(stand, baseline)

    if args.seed:
        klinke_einrasten_stand = {k: {"titel": v["titel"],
                                     "schwere": v["schwere"]}
                                  for k, v in stand.items()}
        _schreibe_baseline(klinke_einrasten_stand, args.dry_run)
        print(f"🔒 Baseline eingefroren: {len(klinke_einrasten_stand)} Artikel → "
              f"{BASELINE.relative_to(ROOT)}"
              + (" (dry-run, nichts geschrieben)" if args.dry_run else ""))
        return 0

    # Klinke zieht bei Heilungen nach; offene NEUE Befunde werden nicht
    # eingefroren.
    if baseline:
        _schreibe_baseline(klinke_einrasten(stand, baseline), args.dry_run)
    else:
        # Ohne Baseline wäre jeder Befund „neu“ – das ist beim ersten Lauf
        # richtig (der Bestand ist tatsächlich ungeprüft), aber es darf
        # nicht schreiben, was es nicht weiß. Deshalb: einfrieren nur auf
        # --seed, hier nur melden.
        pass

    _schreibe_history(len(ergebnis["neu"]) + len(ergebnis["verschlechtert"]),
                       len(ergebnis["bekannt"]), dateien, args.dry_run)
    _drucke(stand, ergebnis, baseline, dateien, args.json, args.md)

    return 1 if (ergebnis["neu"] or ergebnis["verschlechtert"]) else 0


if __name__ == "__main__":
    sys.exit(main())
