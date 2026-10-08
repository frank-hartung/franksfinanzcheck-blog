#!/usr/bin/env python3
"""KI-Vorschläge für Cover-Alt-Texte – nur Vorschläge, nie eigenständige Änderung.

Befund (08.10.2026): Alle Artikel mit Titelbild haben einen `cover.alt`. Bei
rund zwei Dritteln ist er aber nur eine Kopie des Seitentitels. Das hilft
Screenreader-Nutzern nicht. Dieses Skript schlägt beschreibende Alt-Texte vor.

Ablauf (Mensch bleibt in der Schleife):
  1. --report        Kandidaten zählen (fehlt / leer / Titel-Kopie)
  2. --vorschlagen   Gemini (Gratis-Tier) beschreibt das Titelbild; Eintrag in
                     data/alt_texte/vorschlaege.yaml mit freigegeben: false
  3. Mensch prüft   Text ändern oder übernehmen; freigegeben: true und
                     freigegeben_von: "<Name>" setzen
  4. --anwenden      schreibt NUR freigegebene Einträge in den cover-Block der
                     Seite (--trocken zeigt vorher, was passieren würde)

Regeln:
  - Kein Automatismus: der Befehl läuft nie in einem Workflow.
  - Ein Vorschlag wird nur angewendet, wenn der aktuelle Alt-Text noch dem
    Stand des Vorschlags entspricht (kein Überschreiben fremder Änderungen).
  - Bestehende Einträge werden nie neu erzeugt oder überschrieben.
  - Nur das Titelbild wird geschickt, keine personenbezogenen Daten.
  - Ohne GEMINI_API_KEY: exit 0, „übersprungen“, nichts wird geschrieben.

Aufruf:
  python3 scripts/alt_text_vorschlaege.py --report
  GEMINI_API_KEY=… python3 scripts/alt_text_vorschlaege.py --vorschlagen --max 10
  python3 scripts/alt_text_vorschlaege.py --anwenden --trocken
  python3 scripts/alt_text_vorschlaege.py --anwenden
  python3 scripts/alt_text_vorschlaege.py --selftest

Runbook: docs/ANLEITUNG-ALT-TEXTE.md
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import json
import os
import re
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

try:
    import yaml
except ImportError:  # CI installiert PyYAML; lokal: pip install pyyaml
    yaml = None

ROOT = Path(__file__).resolve().parents[1]
DATEI = ROOT / "data" / "alt_texte" / "vorschlaege.yaml"
MODELL = "gemini-3-flash-preview"  # wie in data/ki_transportweg.yaml (Gratis-Tier)
ENDPUNKT = "https://generativelanguage.googleapis.com/v1beta/models/{modell}:generateContent"
MAX_BYTES = 4 * 1024 * 1024
MIME = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png", ".webp": "image/webp"}
ALT_MAX = 125
KANDIDAT_GRUENDE = ("alt-fehlt", "alt-leer", "titel-kopie")
FM_RE = re.compile(r"^---\n(.*?)\n---\n", re.S)
PROMPT = (
    "Schreibe einen Alternativtext (alt-Text) für das Titelbild eines deutschen Finanzratgebers. "
    "Beschreibe nur, was auf dem Bild sichtbar ist. Höchstens 120 Zeichen, ein Satz, ohne "
    "„Bild von“ oder „Foto von“, ohne Preise, Zahlen oder Versprechen, die nicht im Bild stehen. "
    "Den Seitentitel nicht wörtlich wiederholen. Gib nur den Alternativtext zurück. "
    "Seitentitel als Kontext: {titel}"
)


# ---------------------------------------------------------------- Lesen
def lese_seite(pfad: Path):
    """(text, front_matter) – oder (None, None), wenn kein Front Matter da ist."""
    text = pfad.read_text(encoding="utf-8")
    m = FM_RE.match(text)
    if not m:
        return None, None
    return text, (yaml.safe_load(m.group(1)) or {})


def einordnen(fm: dict) -> str:
    cov = fm.get("cover")
    if not isinstance(cov, dict) or not cov.get("image"):
        return "ohne-cover"
    if cov.get("alt") is None:
        return "alt-fehlt"
    alt = str(cov.get("alt")).strip()
    if not alt:
        return "alt-leer"
    if alt.casefold() == str(fm.get("title", "")).strip().casefold():
        return "titel-kopie"
    return "eigenstaendig"


def seiten(root: Path):
    """Alle Seiten mit Titelbild: (relativer Pfad, front_matter, Grund)."""
    out = []
    for pfad in sorted((root / "content").rglob("*.md")):
        text, fm = lese_seite(pfad)
        if fm is None:
            continue
        grund = einordnen(fm)
        if grund == "ohne-cover":
            continue
        out.append((pfad.relative_to(root).as_posix(), fm, grund))
    return out


def lade_store(root: Path) -> dict:
    datei = root / "data" / "alt_texte" / "vorschlaege.yaml"
    if not datei.exists():
        return {"version": 1, "vorschlaege": []}
    daten = yaml.safe_load(datei.read_text(encoding="utf-8")) or {}
    daten.setdefault("version", 1)
    daten.setdefault("vorschlaege", [])
    return daten


def speichere_store(root: Path, store: dict) -> None:
    datei = root / "data" / "alt_texte" / "vorschlaege.yaml"
    datei.parent.mkdir(parents=True, exist_ok=True)
    kopf = (
        "# KI-Vorschläge für Cover-Alt-Texte (Gemini-Gratis-Tier).\n"
        "# Nur Vorschläge: angewendet wird ausschließlich mit freigegeben: true\n"
        "# und freigegeben_von (Name). Runbook: docs/ANLEITUNG-ALT-TEXTE.md\n"
    )
    inhalt = kopf + yaml.safe_dump(store, allow_unicode=True, sort_keys=False, width=100)
    tmp = datei.with_name(datei.name + ".tmp")
    tmp.write_text(inhalt, encoding="utf-8")
    tmp.replace(datei)


# ---------------------------------------------------------------- Prüfen
def bereinige(text: str) -> str:
    t = " ".join(str(text or "").split())
    t = t.strip().strip("\"'„“”«»`").strip()
    return t


def pruefe_alt(text: str, titel: str) -> list[str]:
    p: list[str] = []
    if not text:
        p.append("leer")
    if len(text) > ALT_MAX:
        p.append(f"zu lang ({len(text)} > {ALT_MAX} Zeichen)")
    if re.match(r"^(bild|foto|grafik|abbildung)\b", text, re.I):
        p.append("beginnt mit Bild-/Foto-Einleitung")
    if titel and text.casefold() == titel.strip().casefold():
        p.append("wiederholt den Titel")
    return p


# ---------------------------------------------------------------- Schreiben
def setze_cover_alt(text: str, neuer_alt: str) -> str:
    """Ändert nur die `alt:`-Zeile im cover-Block. Alles andere bleibt byte-gleich."""
    m = FM_RE.match(text)
    if not m:
        raise ValueError("kein Front Matter")
    zeilen = m.group(1).split("\n")
    start = next((i for i, z in enumerate(zeilen) if z.rstrip() == "cover:"), None)
    if start is None:
        raise ValueError("kein cover-Block")
    ende = start + 1
    while ende < len(zeilen) and zeilen[ende].startswith(" "):
        ende += 1
    neu = f"  alt: {json.dumps(neuer_alt, ensure_ascii=False)}"
    for i in range(start + 1, ende):
        if re.match(r"^  alt:", zeilen[i]):
            zeilen[i] = neu
            break
    else:
        for i in range(start + 1, ende):
            if re.match(r"^  image:", zeilen[i]):
                zeilen.insert(i + 1, neu)
                break
        else:
            raise ValueError("cover ohne image-Zeile")
    return "---\n" + "\n".join(zeilen) + "\n---\n" + text[m.end():]


# ---------------------------------------------------------------- Anbieter
def gemini_anbieter(api_key: str, modell: str = MODELL, timeout: int = 60):
    url = ENDPUNKT.format(modell=modell)

    def anbieter(bild: bytes, mime: str, titel: str) -> str:
        body = {
            "contents": [{"role": "user", "parts": [
                {"text": PROMPT.format(titel=titel)},
                {"inline_data": {"mime_type": mime, "data": base64.b64encode(bild).decode("ascii")}},
            ]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 300},
        }
        req = urllib.request.Request(
            url, data=json.dumps(body).encode("utf-8"), method="POST",
            headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                daten = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:  # Schlüssel nie ausgeben
            raise RuntimeError(f"Gemini HTTP {e.code}") from None
        kandidaten = daten.get("candidates") or [{}]
        teile = (kandidaten[0].get("content") or {}).get("parts") or []
        return "".join(t.get("text", "") for t in teile)

    return anbieter


# ---------------------------------------------------------------- Modi
def vorschlagen(root: Path, anbieter, max_n: int, pause: float = 4.0, heute: dt.date | None = None):
    heute = heute or dt.date.today()
    store = lade_store(root)
    bekannt = {e.get("seite") for e in store["vorschlaege"]}
    neu, verworfen = 0, []
    for seite, fm, grund in seiten(root):
        if neu >= max_n:
            break
        if grund not in KANDIDAT_GRUENDE or seite in bekannt:
            continue
        cov = fm["cover"]
        bild_rel = str(cov["image"])
        bild = root / "static" / bild_rel.lstrip("/")
        mime = MIME.get(bild.suffix.lower())
        if not bild.exists():
            verworfen.append((seite, "Bilddatei nicht gefunden"))
            continue
        if not mime:
            verworfen.append((seite, f"Bildformat {bild.suffix} nicht unterstützt"))
            continue
        if bild.stat().st_size > MAX_BYTES:
            verworfen.append((seite, "Bild größer als 4 MB"))
            continue
        titel = str(fm.get("title", ""))
        if neu:
            time.sleep(pause)  # Gratis-Tier: langsam bleiben
        try:
            roh = anbieter(bild.read_bytes(), mime, titel)
        except Exception as e:  # noqa: BLE001 – Fehler je Seite protokollieren, Lauf fortsetzen
            verworfen.append((seite, str(e)))
            continue
        text = bereinige(roh)
        probleme = pruefe_alt(text, titel)
        if probleme:
            verworfen.append((seite, "Antwort verworfen: " + ", ".join(probleme)))
            continue
        store["vorschlaege"].append({
            "seite": seite,
            "bild": bild_rel,
            "alt_aktuell": str(cov.get("alt") or ""),
            "vorschlag": text,
            "modell": MODELL,
            "erzeugt": heute.isoformat(),
            "freigegeben": False,
            "freigegeben_von": "",
        })
        bekannt.add(seite)
        neu += 1
        speichere_store(root, store)  # nach jedem Treffer sichern
    return neu, verworfen


def anwenden(root: Path, trocken: bool = False, heute: dt.date | None = None):
    heute = heute or dt.date.today()
    store = lade_store(root)
    ergebnisse: list[tuple[str, str]] = []
    geaendert = False
    for e in store["vorschlaege"]:
        seite = e.get("seite", "")
        if e.get("angewendet"):
            continue
        if e.get("freigegeben") is not True:
            continue
        if not str(e.get("freigegeben_von") or "").strip():
            ergebnisse.append((seite, "übersprungen: freigegeben_von fehlt"))
            continue
        pfad = root / seite
        if not pfad.exists():
            ergebnisse.append((seite, "übersprungen: Seite nicht gefunden"))
            continue
        text, fm = lese_seite(pfad)
        if fm is None or einordnen(fm) == "ohne-cover":
            ergebnisse.append((seite, "übersprungen: kein Titelbild mehr"))
            continue
        aktuell = str((fm.get("cover") or {}).get("alt") or "")
        if aktuell != str(e.get("alt_aktuell") or ""):
            ergebnisse.append((seite, "übersprungen: veraltet – der Alt-Text wurde seit dem Vorschlag geändert"))
            continue
        vorschlag = str(e.get("vorschlag") or "")
        probleme = pruefe_alt(vorschlag, str(fm.get("title", "")))
        if probleme:
            ergebnisse.append((seite, "übersprungen: " + ", ".join(probleme)))
            continue
        if trocken:
            ergebnisse.append((seite, f"würde gesetzt: {vorschlag}"))
            continue
        pfad.write_text(setze_cover_alt(text, vorschlag), encoding="utf-8")
        e["angewendet"] = heute.isoformat()
        geaendert = True
        ergebnisse.append((seite, f"angewendet: {vorschlag}"))
    if geaendert:
        speichere_store(root, store)
    return ergebnisse


def drucke_report(root: Path) -> None:
    alle = seiten(root)
    zaehler: dict[str, int] = {}
    for _, _, grund in alle:
        zaehler[grund] = zaehler.get(grund, 0) + 1
    store = lade_store(root)
    stand = {}
    for e in store["vorschlaege"]:
        status = "angewendet" if e.get("angewendet") else ("freigegeben" if e.get("freigegeben") is True else "offen")
        stand[status] = stand.get(status, 0) + 1
    print(f"## Cover-Alt-Texte: {len(alle)} Seiten mit Titelbild")
    for grund in ("eigenstaendig", "titel-kopie", "alt-fehlt", "alt-leer"):
        print(f"  {grund}: {zaehler.get(grund, 0)}")
    kandidaten = [s for s, _, g in alle if g in KANDIDAT_GRUENDE]
    print(f"Kandidaten für Vorschläge: {len(kandidaten)}")
    print("Vorschläge: " + (", ".join(f"{k} {v}" for k, v in sorted(stand.items())) or "keine"))


# ---------------------------------------------------------------- Selbsttest
def selbsttest() -> list[str]:
    fehler: list[str] = []
    titel = "Test-Ratgeber"
    faelle = {
        "fehlt": ("---\ntitle: \"Test-Ratgeber\"\ncover:\n  image: \"images/covers/a.jpg\"\n---\n", "alt-fehlt"),
        "leer": ("---\ntitle: \"Test-Ratgeber\"\ncover:\n  image: \"images/covers/a.jpg\"\n  alt: \"\"\n---\n", "alt-leer"),
        "kopie": ("---\ntitle: \"Test-Ratgeber\"\ncover:\n  image: \"images/covers/a.jpg\"\n  alt: \"test-ratgeber\"\n---\n", "titel-kopie"),
        "eigen": ("---\ntitle: \"Test-Ratgeber\"\ncover:\n  image: \"images/covers/a.jpg\"\n  alt: \"Sparschwein auf Münzstapel\"\n---\n", "eigenstaendig"),
        "ohne": ("---\ntitle: \"Test-Ratgeber\"\n---\n", "ohne-cover"),
    }
    for name, (text, erwartet) in faelle.items():
        _, fm = lese_seite_text(text)
        if einordnen(fm) != erwartet:
            fehler.append(f"Einordnung {name}: erwartet {erwartet}, bekommen {einordnen(fm)}")

    for text, erwartet, name in (
        ("Bild von einem Sparschwein", True, "Bild-Einleitung"),
        ("x" * (ALT_MAX + 1), True, "zu lang"),
        ("Test-Ratgeber", True, "Titel-Wiederholung"),
        ("", True, "leer"),
        ("Sparschwein mit Münzen auf hellem Grund", False, "gut"),
    ):
        if bool(pruefe_alt(text, titel)) != erwartet:
            fehler.append(f"pruefe_alt {name}: falsches Ergebnis")

    quelle = ("---\ntitle: \"T\"\ndate: 2026-01-01\ncover:\n  image: \"images/covers/a.jpg\"\n"
              "  alt: \"Alt alt\"\n  caption: \"Unterschrift\"\n---\n\nKörper mit alt: Zeile\n")
    neu = setze_cover_alt(quelle, "Neuer „Text“ mit \"Anführung\"")
    if neu.replace("  alt: \"Neuer „Text“ mit \\\"Anführung\\\"\"", "  alt: \"Alt alt\"") != quelle:
        fehler.append("setze_cover_alt: andere Zeilen wurden verändert")
    if "Körper mit alt: Zeile" not in neu:
        fehler.append("setze_cover_alt: Fließtext beschädigt")
    fm_neu = yaml.safe_load(FM_RE.match(neu).group(1))
    if fm_neu["cover"]["alt"] != "Neuer „Text“ mit \"Anführung\"":
        fehler.append("setze_cover_alt: YAML-Escape falsch")
    ohne_alt = "---\ntitle: \"T\"\ncover:\n  image: \"images/covers/a.jpg\"\n  caption: \"U\"\n---\nK\n"
    if yaml.safe_load(FM_RE.match(setze_cover_alt(ohne_alt, "Neu")).group(1))["cover"].get("alt") != "Neu":
        fehler.append("setze_cover_alt: fehlende alt-Zeile wurde nicht eingefügt")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "content" / "posts" / "a").mkdir(parents=True)
        (root / "static" / "images" / "covers").mkdir(parents=True)
        (root / "static" / "images" / "covers" / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0test")
        seite = root / "content" / "posts" / "a" / "index.md"
        seite.write_text("---\ntitle: \"Test-Ratgeber\"\ncover:\n  image: \"images/covers/a.jpg\"\n"
                         "  alt: \"test-ratgeber\"\n---\nKörper\n", encoding="utf-8")
        anbieter_fake = lambda bild, mime, titel: "Sparschwein auf Münzstapel vor hellem Hintergrund"  # noqa: E731
        neu_n, verworfen = vorschlagen(root, anbieter_fake, 5, pause=0)
        if neu_n != 1 or verworfen:
            fehler.append(f"vorschlagen: erwartet 1 neu ohne Verwurf, bekommen {neu_n} / {verworfen}")
        store = lade_store(root)
        if not store["vorschlaege"] or store["vorschlaege"][0]["freigegeben"] is not False:
            fehler.append("vorschlagen: Eintrag muss freigegeben: false sein")
        neu_n2, _ = vorschlagen(root, anbieter_fake, 5, pause=0)
        if neu_n2 != 0:
            fehler.append("vorschlagen: bestehender Eintrag wurde ein zweites Mal erzeugt")
        anwenden(root)
        if seite.read_text(encoding="utf-8").count("Sparschwein") != 0:
            fehler.append("anwenden: ohne Freigabe wurde geschrieben")
        store = lade_store(root)
        store["vorschlaege"][0]["freigegeben"] = True  # ohne freigegeben_von
        speichere_store(root, store)
        ergebnis = anwenden(root)
        if not any("freigegeben_von fehlt" in m for _, m in ergebnis):
            fehler.append("anwenden: Freigabe ohne Namen wurde nicht abgewiesen")
        if "Sparschwein" in seite.read_text(encoding="utf-8"):
            fehler.append("anwenden: Freigabe ohne Namen hat geschrieben")
        store = lade_store(root)
        store["vorschlaege"][0]["freigegeben"] = True
        speichere_store(root, store)
        anwenden(root, trocken=True)
        if "Sparschwein" in seite.read_text(encoding="utf-8"):
            fehler.append("anwenden --trocken: hat geschrieben")
        store = lade_store(root)
        store["vorschlaege"][0]["freigegeben_von"] = "Testprüfer"
        speichere_store(root, store)
        anwenden(root, trocken=False)
        if "Sparschwein auf Münzstapel" not in seite.read_text(encoding="utf-8"):
            fehler.append("anwenden: freigegebener Vorschlag wurde nicht geschrieben")
        # Veraltet: Alt-Text wurde inzwischen anders gesetzt – nicht überschreiben
        seite.write_text(seite.read_text(encoding="utf-8").replace("Sparschwein auf", "Anders auf"), encoding="utf-8")
        store = lade_store(root)
        store["vorschlaege"][0].pop("angewendet", None)
        store["vorschlaege"][0]["alt_aktuell"] = "test-ratgeber"
        speichere_store(root, store)
        ergebnis = anwenden(root)
        if not any("veraltet" in meldung for _, meldung in ergebnis):
            fehler.append("anwenden: veralteter Vorschlag wurde nicht abgewiesen")
        if "Anders auf" not in seite.read_text(encoding="utf-8"):
            fehler.append("anwenden: fremde Änderung wurde überschrieben")
        # Ohne Schlüssel: übersprungen, nichts schreiben
        datei_vor = (root / "data" / "alt_texte" / "vorschlaege.yaml").read_text(encoding="utf-8")
        import contextlib, io
        with contextlib.redirect_stdout(io.StringIO()) as puffer:
            code = main(["--vorschlagen"], root=root, env={})
        if code != 0 or "übersprungen" not in puffer.getvalue():
            fehler.append("ohne GEMINI_API_KEY muss exit 0 mit „übersprungen“ kommen")
        if (root / "data" / "alt_texte" / "vorschlaege.yaml").read_text(encoding="utf-8") != datei_vor:
            fehler.append("ohne GEMINI_API_KEY wurde geschrieben")
    return fehler


def lese_seite_text(text: str):
    m = FM_RE.match(text)
    return text, (yaml.safe_load(m.group(1)) or {})


# ---------------------------------------------------------------- CLI
def main(argv: list[str] | None = None, root: Path = ROOT, env: dict | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--vorschlagen", action="store_true")
    parser.add_argument("--anwenden", action="store_true")
    parser.add_argument("--trocken", action="store_true", help="mit --anwenden: nichts schreiben")
    parser.add_argument("--max", type=int, default=10, help="höchstens so viele neue Vorschläge pro Lauf")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)
    env = os.environ if env is None else env

    if args.selftest:
        if yaml is None:
            print("PyYAML fehlt: pip install pyyaml")
            return 2
        fehler = selbsttest()
        if fehler:
            print("Selbsttest ROT:")
            for f in fehler:
                print(f"  - {f}")
            return 2
        print("Selbsttest grün.")
        return 0

    if yaml is None:
        print("PyYAML fehlt: pip install pyyaml")
        return 2

    if args.vorschlagen:
        schluessel = (env.get("GEMINI_API_KEY") or "").strip()
        if not schluessel:
            print("Alt-Texte: übersprungen – GEMINI_API_KEY ist nicht gesetzt. Es wurde nichts geschrieben.")
            return 0
        neu, verworfen = vorschlagen(root, gemini_anbieter(schluessel), args.max)
        print(f"Neue Vorschläge: {neu} (offen zur Prüfung in data/alt_texte/vorschlaege.yaml)")
        for seite, grund in verworfen:
            print(f"  verworfen {seite}: {grund}")
        return 0

    if args.anwenden:
        ergebnisse = anwenden(root, trocken=args.trocken)
        if not ergebnisse:
            print("Keine freigegebenen Vorschläge offen.")
        for seite, meldung in ergebnisse:
            print(f"  {seite}: {meldung}")
        return 0

    drucke_report(root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
