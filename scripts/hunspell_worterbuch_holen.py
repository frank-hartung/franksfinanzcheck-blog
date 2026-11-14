#!/usr/bin/env python3
"""Deutsches Hunspell-Wörterbuch bereitstellen (Befund 15.11.2026).

WARUM DIESE DATEI EXISTIERT
---------------------------
`hunspell_ersatz.py` braucht ein deutsches Wörterbuch (`de_DE.aff`/`.dic`).
Es wird NICHT ins Repo eingecheckt, sondern hier reproduzierbar beschafft:
4,2 MB Binärdatei mit fremder Lizenz gehören nicht in die Versionskontrolle,
wenn sie sich in 15 Sekunden herstellen lässt.

Quelle
------
LibreOffice `dictionaries` (das Standardpaket, aus dem auch
`hunspell-de-de` in Debian/Ubuntu gebaut wird):
Björn Jacke, de_DE-frami, **GPLv2 / GPLv3** (siehe data/hunspell/README.md).

Damit die Lizenz eingehalten ist, kopiert das Skript die Copyleft-Texte
mit. Wer das Wörterbuch weitergibt, gibt sie mit weiter.

NUTZUNG
-------
    python3 scripts/hunspell_worterbuch_holen.py            # holen, wenn nötig
    python3 scripts/hunspell_worterbuch_holen.py --check    # nur prüfen
    python3 scripts/hunspell_worterbuch_holen.py --force    # neu holen

Rückgabewerte:
    0  Wörterbuch vorhanden (schon da oder erfolgreich geholt)
    1  konnte nicht geholt werden (kein Netzzugang?) – mit Anweisung
    2  Aufruffehler
"""
import argparse
import io
import shutil
import sys
import tarfile
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ZIEL = ROOT / "data" / "hunspell"
QUELLE = ("https://codeload.github.com/LibreOffice/dictionaries/"
          "tar.gz/refs/heads/master")
MITGLIEDER = {
    "dictionaries-master/de/de_DE_frami.aff": "de_DE.aff",
    "dictionaries-master/de/de_DE_frami.dic": "de_DE.dic",
    # Lizenztexte gehören zur Weitergabe dazu.
    "dictionaries-master/de/COPYING_GPLv2": "COPYING_GPLv2",
    "dictionaries-master/de/COPYING_GPLv3": "COPYING_GPLv3",
}
README = """# Deutsches Hunspell-Wörterbuch (de_DE)

**Herkunft:** LibreOffice `dictionaries`, Datei `de_DE_frami`
**Autor:** Björn Jacke <bjoern@j3e.de>
**Lizenz:** GPLv2 oder GPLv3 (beide Texte liegen in diesem Verzeichnis)
**Größe:** ca. 4,2 MB, 258.220 Wörter

Diese Dateien sind **nicht** versioniert (siehe `.gitignore`). Sie werden
mit `scripts/hunspell_worterbuch_holen.py` hergestellt und von
`scripts/hunspell_ersatz.py` gelesen.

## Warum hier und nicht als Systempaket?

Die CI installiert `hunspell hunspell-de-de` per apt. Auf Rechnern ohne
root ist das nicht möglich; ohne Wörterbuch ist die Rechtschreibkette tot,
und `quality_score` wertet sie als `spelling = 0.5` („unbekannt") – das
drückt gesunde Artikel rechnerisch unter die Schwelle. Dieselbe Ursache
verhinderte die Reserve-Nachzertifizierung über Wochen.

## Weitergabe

Bei Weitergabe des Wörterbuchs sind `COPYING_GPLv2`/`COPYING_GPLv3`
mitzugeben (Copyleft). Das holt das Skript automatisch mit.
"""


def vorhanden() -> bool:
    return (ZIEL / "de_DE.aff").is_file() and (ZIEL / "de_DE.dic").is_file()


def holen(force: bool = False) -> int:
    if vorhanden() and not force:
        print(f"✅ Wörterbuch liegt bereits: {ZIEL}/de_DE.{{aff,dic}}")
        return 0
    print(f"→ hole {QUELLE}")
    try:
        with urllib.request.urlopen(QUELLE, timeout=300) as r:
            rohdaten = r.read()
    except Exception as exc:
        print(f"🛑 Download fehlgeschlagen: {exc.__class__.__name__}: {exc}")
        print("   Ohne Netzzugang: das Wörterbuch muss aus einem "
              "`hunspell-de-de`-Paket kopiert werden:")
        print(f"   data/hunspell/de_DE.aff und data/hunspell/de_DE.dic")
        return 1

    print(f"   {len(rohdaten) / 1e6:.0f} MB geladen, entpacke …")
    ZIEL.mkdir(parents=True, exist_ok=True)
    gefunden = 0
    with tarfile.open(fileobj=io.BytesIO(rohdaten), mode="r:gz") as tar:
        for mitglied, name in MITGLIEDER.items():
            try:
                datei = tar.extractfile(mitglied)
            except KeyError:
                print(f"   ⚠ fehlt im Archiv: {mitglied}")
                continue
            if datei is None:
                continue
            ziel = ZIEL / name
            tmp = ziel.with_suffix(ziel.suffix + ".tmp")
            tmp.write_bytes(datei.read())
            tmp.replace(ziel)
            gefunden += 1
            print(f"   ✓ {name} ({ziel.stat().st_size / 1e3:.0f} kB)")
    (ZIEL / "README.md").write_text(README, encoding="utf-8")

    if not vorhanden():
        print("🛑 Wörterbuch unvollständig – bitte Ausgabe oben prüfen.")
        return 1
    print(f"✅ Wörterbuch bereit: {ZIEL}")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(
        prog="hunspell_worterbuch_holen.py",
        description="Deutsches Hunspell-Wörterbuch nach data/hunspell/ holen.")
    p.add_argument("--check", action="store_true",
                   help="nur prüfen, nichts holen")
    p.add_argument("--force", action="store_true", help="neu holen")
    args = p.parse_args(argv)

    if args.check:
        if vorhanden():
            print(f"✅ Wörterbuch vorhanden: {ZIEL}/de_DE.{{aff,dic}}")
            return 0
        print(f"🛑 Wörterbuch fehlt: {ZIEL}/de_DE.{{aff,dic}}")
        print("   Abhilfe: python3 scripts/hunspell_worterbuch_holen.py")
        return 1
    return holen(force=args.force)


if __name__ == "__main__":
    sys.exit(main())
