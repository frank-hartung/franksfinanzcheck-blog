#!/usr/bin/env python3
# ============================================================
#  BEWEIS-WACHE – ausführbarer Vertrag des Beweissystems
#  (Rollout 01.10.2026, Auftrag Frank: „Zu wenig originäre
#  Beweise – dauerhaft auf Highend-Level beheben“)
#
#  Der menschenlesbare Vertrag steht in data/beweise/schema.yaml.
#  Diese Wache prüft ihn maschinell bei jeder Änderung (CI:
#  .github/workflows/beweis-gate.yml) und schützt damit die
#  Glaubwürdigkeit des Systems gegen Drift:
#
#   B1  Beweis-Register: Pflichtfelder je Typ und Status,
#       eindeutige IDs, gültige Belegklassen/Status, https-Quellen,
#       Changelog bei beweisbaren Einträgen, Fälligkeit im Backlog.
#   B2  Dataset-Querverweise: register.dataset → data/datasets/*.yaml
#   B3  Vergleichsmethodik: bereich-id = Pillar-Slug, Pflichtfelder,
#       Version im SemVer-Format, Changelog vorhanden.
#   B4  Änderungsprotokoll: Pflichtfelder, erlaubte Typen,
#       Belegklasse, erreichbare interne Seitenpfade, Sortierung
#       (neueste zuerst).
#   B5  Shortcode-Querverweise im Content:
#       * beleg kennzahl="…"  → Kennzahl existiert im Register
#       * beleg (frei)        → url+name gesetzt, klasse gültig
#       * beweis id="…"       → ID existiert UND status ist
#         öffentlich beweisfähig (verifiziert/modellfall) –
#         unfertige Belege dürfen nie als Beweis erscheinen.
#   B6  Ehrlichkeits-Inventar (WARNUNG, kein Blocker): listet
#       Erfahrungs-Behauptungen („praxisgetestet“, „selbst
#       geprüft“ …) in Artikeln ohne Beweis-/Beleg-Verweis.
#       Der Bestand wird sichtbar gemacht statt still geduldet.
#
#  Aufrufe:
#    python3 scripts/beweis_gate.py            # Prüfung (CI)
#    python3 scripts/beweis_gate.py --history  # + Journalzeile
#    python3 scripts/beweis_gate.py --selftest # Sabotage-Proben
#
#  SSOT-Regel: Diese Wache LIEST die kuratierten YAML-Dateien,
#  schreibt sie aber NIE (vgl. data/kennzahlen_register.yaml).
# ============================================================
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("FEHLER: PyYAML fehlt (pip install pyyaml)", file=sys.stderr)
    sys.exit(1)

REPO = Path(__file__).resolve().parent.parent
BEWEISE_DIR = REPO / "data" / "beweise"
CONTENT_DIR = REPO / "content"
DATASETS_DIR = REPO / "data" / "datasets"
HISTORY_PATH = REPO / "data" / "beweis_history.jsonl"

BELEGKLASSEN = ("amtlich", "markt", "erfahrung")
STATUS_WERTE = ("geplant", "in-erhebung", "modellfall", "verifiziert")
OEFFENTLICH_ALS_BEWEIS = ("verifiziert", "modellfall")
TYPEN = ("fallstudie", "wechselprotokoll", "messreihe", "modellrechnung")
KORREKTUR_TYPEN = ("korrektur", "quellen-update", "aktualisierung", "system")

PFLICHT_ALLE = ("id", "typ", "titel", "themenbereich", "belegklasse", "status", "angelegt", "kurzfazit")
PFLICHT_BEWEISBAR = ("stand", "quellen", "grenzen", "changelog")
PFLICHT_BACKLOG = ("dokumentationsplan", "faellig")
PFLICHT_JE_TYP = {
    "fallstudie": ("ausgangslage", "entscheidung", "ergebnis", "zeitraum", "anonymisierung"),
    "wechselprotokoll": ("pflichtfelder",),
    "messreihe": ("messaufbau",),
    "modellrechnung": ("rechenweg", "annahmen"),
}

# Erfahrungs-Behauptungen, die ohne Register-Beleg nur Einordnung sind:
CLAIM_MUSTER = re.compile(
    r"praxisgetestet|selbst getestet|selbst geprüft|selbst durchgeführt"
    r"|eigene Messung|ich habe (?:getestet|gemessen|nachgemessen)"
    r"|hunderte[nr]? Tarifvergleiche",
    re.IGNORECASE,
)
RE_BELEG_SC = re.compile(r"\{\{<\s*beleg\s+([^>]*?)>\}\}")
RE_BEWEIS_SC = re.compile(r"\{\{<\s*beweis\s+([^>]*?)>\}\}")
RE_PARAM = re.compile(r"([\w-]+)\s*=\s*\"([^\"]*)\"")


def _lade_yaml(pfad: Path):
    with pfad.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _datum_ok(wert) -> bool:
    text = str(wert)[:10]
    try:
        _dt.date.fromisoformat(text)
        return True
    except ValueError:
        return False


def pruefe_register(register: dict, fehler: list[str]) -> dict:
    """B1 + B2. Liefert {id: eintrag} für die Querverweis-Prüfung."""
    eintraege = (register or {}).get("eintraege") or []
    index: dict[str, dict] = {}
    for e in eintraege:
        eid = str(e.get("id") or "<ohne id>")
        ort = f"register.yaml[{eid}]"
        for feld in PFLICHT_ALLE:
            if not e.get(feld):
                fehler.append(f"B1 {ort}: Pflichtfeld '{feld}' fehlt")
        if eid in index:
            fehler.append(f"B1 {ort}: ID doppelt vergeben")
        index[eid] = e
        if e.get("typ") not in TYPEN:
            fehler.append(f"B1 {ort}: unbekannter typ {e.get('typ')!r}")
        if e.get("belegklasse") not in BELEGKLASSEN:
            fehler.append(f"B1 {ort}: unbekannte belegklasse {e.get('belegklasse')!r}")
        status = e.get("status")
        if status not in STATUS_WERTE:
            fehler.append(f"B1 {ort}: unbekannter status {status!r}")
        if e.get("angelegt") and not _datum_ok(e["angelegt"]):
            fehler.append(f"B1 {ort}: 'angelegt' ist kein Datum")

        if status in OEFFENTLICH_ALS_BEWEIS:
            for feld in PFLICHT_BEWEISBAR:
                if not e.get(feld):
                    fehler.append(f"B1 {ort}: status {status} verlangt '{feld}'")
            for feld in PFLICHT_JE_TYP.get(e.get("typ"), ()):
                if not e.get(feld):
                    fehler.append(f"B1 {ort}: typ {e.get('typ')} verlangt '{feld}'")
            for q in e.get("quellen") or []:
                if not q.get("name") or not q.get("url"):
                    fehler.append(f"B1 {ort}: Quelle ohne name/url")
                elif not str(q["url"]).startswith("https://"):
                    fehler.append(f"B1 {ort}: Quelle nicht https: {q['url']}")
            for c in e.get("changelog") or []:
                if not c.get("datum") or not c.get("notiz") or not _datum_ok(c.get("datum")):
                    fehler.append(f"B1 {ort}: Changelog-Eintrag unvollständig")
        else:
            for feld in PFLICHT_BACKLOG:
                if not e.get(feld):
                    fehler.append(f"B1 {ort}: status {status} verlangt '{feld}' (ehrlicher Backlog)")
            if e.get("faellig") and not _datum_ok(e["faellig"]):
                fehler.append(f"B1 {ort}: 'faellig' ist kein Datum")

        dataset = e.get("dataset")
        if dataset and not (DATASETS_DIR / f"{dataset}.yaml").exists():
            fehler.append(f"B2 {ort}: dataset {dataset!r} fehlt unter data/datasets/")
    return index


def pruefe_methodik(methodik: dict, fehler: list[str]) -> None:
    """B3."""
    for b in (methodik or {}).get("bereiche") or []:
        bid = str(b.get("id") or "<ohne id>")
        ort = f"vergleichsmethodik.yaml[{bid}]"
        if not (CONTENT_DIR / "pillar" / bid).is_dir():
            fehler.append(f"B3 {ort}: kein Pillar-Ordner content/pillar/{bid}/")
        for feld in ("name", "version", "stand", "leitfrage", "rechenweg", "pruefregeln", "datenbasis", "changelog"):
            if not b.get(feld):
                fehler.append(f"B3 {ort}: Pflichtfeld '{feld}' fehlt")
        if b.get("version") and not re.fullmatch(r"\d+\.\d+\.\d+", str(b["version"])):
            fehler.append(f"B3 {ort}: version {b['version']!r} ist kein SemVer")
        for d in b.get("datenbasis") or []:
            if d.get("klasse") not in BELEGKLASSEN:
                fehler.append(f"B3 {ort}: Datenbasis mit unbekannter klasse {d.get('klasse')!r}")


def _interner_pfad_existiert(pfad: str) -> bool:
    teile = [t for t in pfad.split("/") if t]
    if not teile:
        return False
    kandidat = CONTENT_DIR.joinpath(*teile)
    return kandidat.is_dir() or kandidat.with_suffix(".md").exists()


def pruefe_korrekturen(korrekturen: dict, fehler: list[str]) -> int:
    """B4. Liefert Anzahl Einträge."""
    eintraege = (korrekturen or {}).get("eintraege") or []
    letztes = None
    for i, e in enumerate(eintraege):
        ort = f"korrekturen.yaml[#{i + 1}]"
        for feld in ("datum", "typ", "titel", "was", "warum", "quelle", "belegklasse"):
            if not e.get(feld):
                fehler.append(f"B4 {ort}: Pflichtfeld '{feld}' fehlt")
        if e.get("typ") and e["typ"] not in KORREKTUR_TYPEN:
            fehler.append(f"B4 {ort}: unbekannter typ {e['typ']!r}")
        if e.get("belegklasse") not in BELEGKLASSEN:
            fehler.append(f"B4 {ort}: unbekannte belegklasse {e.get('belegklasse')!r}")
        if e.get("datum"):
            if not _datum_ok(e["datum"]):
                fehler.append(f"B4 {ort}: 'datum' ist kein Datum")
            else:
                aktuell = _dt.date.fromisoformat(str(e["datum"])[:10])
                if letztes is not None and aktuell > letztes:
                    fehler.append(f"B4 {ort}: Sortierung verletzt (neueste Einträge gehören nach oben)")
                letztes = aktuell
        quelle = e.get("quelle") or {}
        if not quelle.get("name") or not quelle.get("url"):
            fehler.append(f"B4 {ort}: Quelle braucht name und url")
        elif not str(quelle["url"]).startswith("https://"):
            fehler.append(f"B4 {ort}: Quelle nicht https: {quelle['url']}")
        for s in e.get("seiten") or []:
            if not s.get("pfad") or not s.get("name"):
                fehler.append(f"B4 {ort}: Seiten-Eintrag braucht pfad und name")
            elif not _interner_pfad_existiert(s["pfad"]):
                fehler.append(f"B4 {ort}: Seite {s['pfad']!r} existiert nicht im Content")
    return len(eintraege)


def pruefe_content(register_index: dict, kennzahl_ids: set[str], fehler: list[str], warnungen: list[str]) -> dict:
    """B5 + B6 über alle Markdown-Dateien im Content."""
    statistik = {"beleg_refs": 0, "beweis_refs": 0, "claims_ohne_beweis": 0}
    for md in sorted(CONTENT_DIR.rglob("*.md")):
        try:
            rel = md.relative_to(REPO)
        except ValueError:  # Selbsttest nutzt ein Temp-Verzeichnis
            rel = md
        text = md.read_text(encoding="utf-8")

        for roh in RE_BELEG_SC.findall(text):
            statistik["beleg_refs"] += 1
            params = dict(RE_PARAM.findall(roh))
            if "kennzahl" in params:
                if params["kennzahl"] not in kennzahl_ids:
                    fehler.append(f"B5 {rel}: beleg verweist auf unbekannte Kennzahl {params['kennzahl']!r}")
            else:
                if not params.get("url") or not params.get("name"):
                    fehler.append(f"B5 {rel}: freier beleg braucht url und name")
                if params.get("klasse") and params["klasse"] not in BELEGKLASSEN:
                    fehler.append(f"B5 {rel}: beleg mit unbekannter klasse {params['klasse']!r}")

        for roh in RE_BEWEIS_SC.findall(text):
            statistik["beweis_refs"] += 1
            params = dict(RE_PARAM.findall(roh))
            bid = params.get("id")
            if not bid:
                fehler.append(f"B5 {rel}: beweis ohne id")
                continue
            eintrag = register_index.get(bid)
            if eintrag is None:
                fehler.append(f"B5 {rel}: beweis verweist auf unbekannte ID {bid!r}")
            elif eintrag.get("status") not in OEFFENTLICH_ALS_BEWEIS:
                fehler.append(
                    f"B5 {rel}: beweis {bid!r} hat status {eintrag.get('status')!r} – "
                    "unfertige Belege dürfen nicht als Beweis eingebettet werden"
                )

        if md.parts and "posts" in md.parts:
            treffer = sorted({m.group(0).lower() for m in CLAIM_MUSTER.finditer(text)})
            if treffer and not RE_BEWEIS_SC.search(text) and not RE_BELEG_SC.search(text):
                statistik["claims_ohne_beweis"] += 1
                warnungen.append(
                    f"B6 {rel}: Erfahrungs-Behauptung ohne Beweis-/Beleg-Verweis ({', '.join(treffer)})"
                )
    return statistik


def lauf(history: bool) -> int:
    fehler: list[str] = []
    warnungen: list[str] = []

    register = _lade_yaml(BEWEISE_DIR / "register.yaml")
    methodik = _lade_yaml(BEWEISE_DIR / "vergleichsmethodik.yaml")
    korrekturen = _lade_yaml(BEWEISE_DIR / "korrekturen.yaml")
    kennzahlen = _lade_yaml(REPO / "data" / "kennzahlen_register.yaml")
    kennzahl_ids = {k["id"] for k in (kennzahlen or {}).get("kennzahlen", []) if k.get("id")}

    register_index = pruefe_register(register, fehler)
    pruefe_methodik(methodik, fehler)
    anzahl_korrekturen = pruefe_korrekturen(korrekturen, fehler)
    statistik = pruefe_content(register_index, kennzahl_ids, fehler, warnungen)

    belegt = sum(1 for e in register_index.values() if e.get("status") in OEFFENTLICH_ALS_BEWEIS)
    print("BEWEIS-WACHE – Ergebnis")
    print(f"  Register-Einträge: {len(register_index)} (davon beweisbar: {belegt})")
    print(f"  Methodik-Bereiche: {len((methodik or {}).get('bereiche') or [])}")
    print(f"  Änderungsprotokoll: {anzahl_korrekturen} Einträge")
    print(f"  Content-Verweise: {statistik['beleg_refs']} beleg / {statistik['beweis_refs']} beweis")
    for w in warnungen:
        print(f"  WARNUNG {w}")
    for f in fehler:
        print(f"  FEHLER  {f}")
    print(f"  => {len(fehler)} Fehler, {len(warnungen)} Warnungen")

    if history:
        zeile = {
            "zeit": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "eintraege": len(register_index),
            "beweisbar": belegt,
            "korrekturen": anzahl_korrekturen,
            "beleg_refs": statistik["beleg_refs"],
            "beweis_refs": statistik["beweis_refs"],
            "claims_ohne_beweis": statistik["claims_ohne_beweis"],
            "fehler": len(fehler),
            "warnungen": len(warnungen),
        }
        with HISTORY_PATH.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    return 1 if fehler else 0


def selftest() -> int:
    """Sabotage-Proben: Jede Manipulation MUSS als Fehler auffallen."""
    basis = _lade_yaml(BEWEISE_DIR / "register.yaml")
    proben: list[tuple[str, bool]] = []

    # Probe 1: Basis-Register ist formal sauber.
    fehler: list[str] = []
    pruefe_register(copy.deepcopy(basis), fehler)
    proben.append(("Basis-Register sauber", not fehler))

    # Probe 2: verifizierter Eintrag ohne Quellen muss durchfallen.
    sab = copy.deepcopy(basis)
    for e in sab["eintraege"]:
        if e["status"] == "verifiziert":
            e.pop("quellen", None)
            break
    fehler = []
    pruefe_register(sab, fehler)
    proben.append(("verifiziert ohne quellen fällt durch", any("verlangt 'quellen'" in f for f in fehler)))

    # Probe 3: Backlog-Eintrag ohne Fälligkeit muss durchfallen.
    sab = copy.deepcopy(basis)
    for e in sab["eintraege"]:
        if e["status"] in ("in-erhebung", "geplant"):
            e.pop("faellig", None)
            break
    fehler = []
    pruefe_register(sab, fehler)
    proben.append(("Backlog ohne faellig fällt durch", any("verlangt 'faellig'" in f for f in fehler)))

    # Probe 4: beweis-Verweis auf unfertigen Eintrag muss durchfallen.
    index = {e["id"]: e for e in basis["eintraege"]}
    backlog_id = next(e["id"] for e in basis["eintraege"] if e["status"] not in OEFFENTLICH_ALS_BEWEIS)
    fehler, warnungen = [], []
    import tempfile

    global CONTENT_DIR
    echt_content = CONTENT_DIR
    with tempfile.TemporaryDirectory() as tmp:
        posts = Path(tmp) / "posts" / "sabotage"
        posts.mkdir(parents=True)
        (posts / "index.md").write_text(
            f'Text {{{{< beweis id="{backlog_id}" >}}}} und {{{{< beleg kennzahl="gibt-es-nicht" >}}}}',
            encoding="utf-8",
        )
        CONTENT_DIR = Path(tmp)
        try:
            pruefe_content(index, set(), fehler, warnungen)
        finally:
            CONTENT_DIR = echt_content
    proben.append(("Beweis-Einbettung eines Backlog-Eintrags fällt durch", any("unfertige Belege" in f for f in fehler)))
    proben.append(("Unbekannte Kennzahl fällt durch", any("unbekannte Kennzahl" in f for f in fehler)))

    # Probe 5: Korrektur-Eintrag ohne Quelle muss durchfallen.
    korr = _lade_yaml(BEWEISE_DIR / "korrekturen.yaml")
    sab = copy.deepcopy(korr)
    sab["eintraege"][0].pop("quelle", None)
    fehler = []
    pruefe_korrekturen(sab, fehler)
    proben.append(("Korrektur ohne Quelle fällt durch", any("'quelle' fehlt" in f for f in fehler)))

    alle_ok = True
    print("BEWEIS-WACHE – Selbsttest")
    for name, ok in proben:
        print(f"  {'OK  ' if ok else 'FAIL'} {name}")
        alle_ok &= ok
    return 0 if alle_ok else 2


def main() -> int:
    parser = argparse.ArgumentParser(description="Beweis-Wache: ausführbarer Vertrag des Beweissystems")
    parser.add_argument("--history", action="store_true", help="Journalzeile nach data/beweis_history.jsonl schreiben")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Proben gegen die eigene Prüflogik")
    args = parser.parse_args()
    if args.selftest:
        return selftest()
    return lauf(history=args.history)


if __name__ == "__main__":
    sys.exit(main())
