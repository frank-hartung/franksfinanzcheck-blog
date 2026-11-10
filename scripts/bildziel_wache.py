#!/usr/bin/env python3
"""bildziel_wache.py – Bildziele und Bildzeilen im Bestand prüfen und heilen.

WARUM (Befund 10.11.2026, F4-Runde #1072)
-----------------------------------------
Im Bestand standen 20 Beiträge mit **40 kaputten Bildzielen**:

    ![Merkkarte: …](abbildung-merkkarte. svg)     ← Leerzeichen im Dateinamen
    ![Gliederung: …](abbildung-ablauf. svg)

Die Dateien `abbildung-merkkarte.svg` und `abbildung-ablauf.svg` liegen
daneben und sind gültig. Weil der kaputte Pfad nicht mehr dem Muster des
Ableiters (`abbildungen_ableiten.py`) entsprach, hielt der nächste Lauf die
Abbildung für „fehlt" und **fügte sie erneut ein**: zwei Bildzeilen pro
Abbildung, eine kaputt, eine gültig. Auf der Seite erschien der Alt-Text als
Fließtext, das Bild fehlte – ein sichtbarer Qualitätsfehler auf 20 Live-Seiten.

Ursache war nicht der Ableiter, sondern `fix_spaces.py`: Regel D ergänzt nach
einem Punkt ein Leerzeichen („Satz.Neuer" → „Satz. Neuer") und maskierte
bisher nur `http(s)`-URLs. Markdown-Ziele wie `abbildung-merkkarte.svg` sind
aber keine URL mit Schema – der Punkt vor `svg` wurde als Satzende gelesen.
Deshalb gilt jetzt an zwei Stellen dasselbe:

  * `fix_spaces.py` maskiert **jedes** Markdown-Ziel (Bild, Link, relativ oder
    absolut), bevor die Leerzeichen-Regeln laufen – dort kann kein Leerzeichen
    mehr entstehen.
  * diese Wache macht den Rest sichtbar und heilt ihn deterministisch.

HEILREGEL (konservativ, beweisgestützt)
---------------------------------------
1. Ein Ziel mit Leerzeichen wird **nur** repariert, wenn die Datei ohne die
   Leerzeichen im selben Beitragsordner existiert. Sonst: Befund, keine
   Vermutung.
2. Existiert dieselbe Bildzeile (gleicher Alt-Text) bereits mit gültigem Ziel,
   wird der kaputte **Doppelblock** entfernt (Bildzeile + zugehörige
   `*Abbildung:`-Zeile) – die gültige Zeile ist die neuere Fassung des
   Ableiters. Das ist die einzige Löschung: eine Zeile, die auf ein nicht
   existierendes Bild zeigt und deren Inhalt bereits existiert.
3. Alles andere (fehlende Datei, unbekannter Alt-Text) wird nur gemeldet.

NUTZUNG
  python3 scripts/bildziel_wache.py            # Report (Exit 1 bei Befund)
  python3 scripts/bildziel_wache.py --check    # dasselbe, für CI/Nachlauf
  python3 scripts/bildziel_wache.py --heilen   # reparieren (Exit 0)
  python3 scripts/bildziel_wache.py --selftest # Regelbeweis, schreibt nie
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content"

BILD_RE = re.compile(r"^\s*!\[([^\]]*)\]\(([^)]*)\)\s*$")
ABBILDUNG_RE = re.compile(r"^\s*\*Abbildung:")
# Endungen, bei denen ein Leerzeichen vor dem Punkt ein Maschinenfehler ist.
# Bewusst eng: nur Dateiendungen, die im Bestand als Markdown-Ziel vorkommen.
ENDUNGEN = (".svg", ".png", ".jpg", ".jpeg", ".webp", ".gif", ".pdf")


def beitragsdateien(root: Path = CONTENT) -> list[Path]:
    return sorted(p for p in root.rglob("index.md") if p.is_file())


def zerlegt(text: str) -> tuple[str, str, str]:
    """Frontmatter/Body trennen – ohne den Body je neu zu serialisieren."""
    teile = text.split("---", 2)
    if len(teile) < 3:
        return "", "", text
    return teile[0], teile[1], teile[2]


def ziel_heilbar(ziel: str, ordner: Path) -> str | None:
    """Ziel ohne Leerzeichen, wenn die Datei daneben wirklich existiert."""
    if " " not in ziel:
        return None
    kandidat = ziel.replace(" ", "")
    if not kandidat.endswith(ENDUNGEN):
        return None
    if (ordner / kandidat).is_file():
        return kandidat
    return None


def befund_einer_datei(pfad: Path) -> dict:
    """Bildzeilen, Doppelblöcke und tote Ziele einer Beitragsdatei."""
    text = pfad.read_text(encoding="utf-8")
    _, _, body = zerlegt(text)
    zeilen = body.split("\n")
    ordner = pfad.parent
    bilder = []
    for nr, zeile in enumerate(zeilen):
        m = BILD_RE.match(zeile)
        if m:
            bilder.append({"nr": nr, "alt": m.group(1).strip(),
                           "ziel": m.group(2).strip(), "zeile": zeile})
    heilbar, doppelt, tot = {}, [], []
    gueltige_ziele = {b["ziel"] for b in bilder
                      if (ordner / b["ziel"]).is_file()}
    for b in bilder:
        neu = ziel_heilbar(b["ziel"], ordner)
        if neu:
            heilbar[b["nr"]] = neu
    for b in bilder:
        if b["nr"] in heilbar and any(
                o["alt"] == b["alt"] for o in bilder
                if o["nr"] != b["nr"] and o["ziel"] in gueltige_ziele):
            doppelt.append(b["nr"])
    for b in bilder:
        if b["ziel"].startswith(("http://", "https://")):
            continue
        if not (ordner / b["ziel"]).is_file() and b["nr"] not in heilbar:
            tot.append(b)
    return {"pfad": pfad, "zeilen": zeilen, "bilder": bilder,
            "heilbar": heilbar, "doppelt": doppelt, "tot": tot}


def heilen(pfad: Path, *, schreiben: bool = True) -> dict:
    """Doppelblöcke entfernen, heilbare Ziele reparieren. Idempotent."""
    stand = befund_einer_datei(pfad)
    if not stand["heilbar"]:
        return {"pfad": pfad, "entfernt": 0, "repariert": 0, "tot": stand["tot"]}
    zeilen = list(stand["zeilen"])
    entfernen = set()
    for nr in stand["doppelt"]:
        entfernen.add(nr)
        folge = nr + 1
        while folge < len(zeilen) and not zeilen[folge].strip():
            folge += 1
        if folge < len(zeilen) and ABBILDUNG_RE.match(zeilen[folge]):
            entfernen.add(folge)
        # die Leerzeile direkt davor/danach mitnehmen, damit kein Loch bleibt
        if nr > 0 and not zeilen[nr - 1].strip():
            entfernen.add(nr - 1)
        elif nr + 1 < len(zeilen) and not zeilen[nr + 1].strip():
            entfernen.add(nr + 1)
    repariert = 0
    neu = []
    for nr, zeile in enumerate(zeilen):
        if nr in entfernen:
            continue
        ziel = stand["heilbar"].get(nr)
        if ziel:
            zeile = BILD_RE.sub(
                lambda m: f"![{m.group(1)}]({ziel})", zeile)
            repariert += 1
        neu.append(zeile)
    if schreiben and (entfernen or repariert):
        kopf, fm, _ = zerlegt(pfad.read_text(encoding="utf-8"))
        pfad.write_text(f"{kopf}---{fm}---" + "\n".join(neu), encoding="utf-8")
    return {"pfad": pfad, "entfernt": len(entfernen), "repariert": repariert,
            "tot": stand["tot"]}


def pruefen(root: Path = CONTENT) -> dict:
    befunde, tot = [], []
    for pfad in beitragsdateien(root):
        stand = befund_einer_datei(pfad)
        if stand["heilbar"] or stand["tot"]:
            befunde.append(stand)
        tot.extend({"pfad": str(b["nr"]), "ziel": b["ziel"],
                    "datei": str(pfad.relative_to(ROOT))} for b in stand["tot"])
    return {"betroffen": befunde, "tote_ziele": tot,
            "kaputt": sum(len(b["heilbar"]) for b in befunde),
            "doppelt": sum(len(b["doppelt"]) for b in befunde)}


# ----------------------------------------------------------------------
# Selbsttest: die Regel muss beweisen, was sie heilt UND was sie stehen lässt
# ----------------------------------------------------------------------
def selftest() -> int:
    import tempfile
    fehler = []

    def fall(name, inhalt, erwartet_entfernt, erwartet_repariert, muss_bleiben):
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp) / "2026-01-01-test"
            ordner.mkdir()
            (ordner / "abbildung-merkkarte.svg").write_text("<svg/>",
                                                            encoding="utf-8")
            pfad = ordner / "index.md"
            pfad.write_text(inhalt, encoding="utf-8")
            ergebnis = heilen(pfad)
            text = pfad.read_text(encoding="utf-8")
            if (ergebnis["entfernt"], ergebnis["repariert"]) != (
                    erwartet_entfernt, erwartet_repariert):
                fehler.append(f"{name}: entfernt/repariert = "
                              f"{ergebnis['entfernt']}/{ergebnis['repariert']}, "
                              f"erwartet {erwartet_entfernt}/{erwartet_repariert}")
            for merkmal in muss_bleiben:
                if merkmal not in text:
                    fehler.append(f"{name}: „{merkmal}“ fehlt nach der Heilung")
            # Idempotenz: ein zweiter Lauf darf nichts mehr ändern.
            zweite = heilen(pfad)
            if zweite["entfernt"] or zweite["repariert"]:
                fehler.append(f"{name}: nicht idempotent")

    # 1) Doppelblock: kaputte Zeile + gültige Zeile -> kaputter Block fällt weg.
    fall("doppelblock",
         "---\ntitle: T\n---\n\nText.\n\n"
         "![Merkkarte](abbildung-merkkarte. svg)\n\n"
         "*Abbildung: Merkkarte zu „[T](../../posts/x/).“ (eigene Darstellung).*\n\n"
         "![Merkkarte](abbildung-merkkarte.svg)\n\n"
         "*Abbildung: Merkkarte zu „T“ (eigene Darstellung).*\n\nEnde.\n",
         3, 0, ["Text.", "Ende.", "![Merkkarte](abbildung-merkkarte.svg)"])
    # 2) Einzelne kaputte Zeile ohne Doppel -> Pfad reparieren, Zeile bleibt.
    fall("einzelziel",
         "---\ntitle: T\n---\n\nText.\n\n"
         "![Merkkarte](abbildung-merkkarte. svg)\n\nEnde.\n",
         0, 1, ["![Merkkarte](abbildung-merkkarte.svg)", "Ende."])
    # 3) Totes Ziel ohne Datei -> nichts anfassen (keine Vermutung).
    fall("totes-ziel",
         "---\ntitle: T\n---\n\nText.\n\n"
         "![Merkkarte](abbildung-gibtsnicht. svg)\n\nEnde.\n",
         0, 0, ["![Merkkarte](abbildung-gibtsnicht. svg)"])
    if fehler:
        print("🛑 BILDZIEL-SELBSTTEST FEHLGESCHLAGEN")
        print("\n".join(f"  {f}" for f in fehler))
        return 2
    print("✅ Bildziel-Selbsttest: 3 Fälle grün (Doppelblock, Einzelziel, "
          "totes Ziel) + Idempotenz.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if "--selftest" in argv:
        return selftest()
    if "--heilen" in argv:
        gesamt = {"entfernt": 0, "repariert": 0}
        for pfad in beitragsdateien():
            ergebnis = heilen(pfad)
            if ergebnis["entfernt"] or ergebnis["repariert"]:
                print(f"  {pfad.parent.name}: {ergebnis['repariert']} Ziel(e) "
                      f"repariert, {ergebnis['entfernt']} Zeile(n) entfernt")
            gesamt["entfernt"] += ergebnis["entfernt"]
            gesamt["repariert"] += ergebnis["repariert"]
        stand = pruefen()
        print(f"[HEILUNG] {gesamt['repariert']} Bildziel(e) repariert, "
              f"{gesamt['entfernt']} Zeile(n) eines Doppelblocks entfernt.")
        if stand["tote_ziele"]:
            print(f"⚠ {len(stand['tote_ziele'])} tote(s) Bildziel(e) ohne "
                  "Datei – gemeldet, nicht geraten:")
            for t in stand["tote_ziele"]:
                print(f"   - {t['datei']}: {t['ziel']}")
        return 0
    stand = pruefen()
    if not stand["betroffen"] and not stand["tote_ziele"]:
        print("✅ Bildziele sauber: jedes lokale Bildziel existiert, keine "
              "Leerzeichen im Dateinamen, keine Doppelzeile.")
        return 0
    print(f"❌ {stand['kaputt']} heilbares Bildziel(e) mit Leerzeichen, "
          f"{stand['doppelt']} Doppelblock/-blöcke, "
          f"{len(stand['tote_ziele'])} tote(s) Ziel(e).")
    for b in stand["betroffen"]:
        print(f"   - {b['pfad'].relative_to(ROOT)}: "
              f"{len(b['heilbar'])} heilbar, {len(b['doppelt'])} doppelt")
    for t in stand["tote_ziele"][:20]:
        print(f"   - tot: {t['datei']}: {t['ziel']}")
    print("   Heilung: python3 scripts/bildziel_wache.py --heilen")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
