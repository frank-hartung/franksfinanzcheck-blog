#!/usr/bin/env python3
"""Bildherkunft der Cover: belegen statt offen lassen (#1028, Frist 02.12.2026).

DIE FRAGE, DIE HIER BEANTWORTET WIRD
------------------------------------
Am 13.11.2026 stand in der Akte: „Bildherkunft je Datei: 0 Cover als KI
deklariert; aus dem Repo allein ist Vollständigkeit nicht belegbar." Das war
richtig – solange man Herkunft für eine Behauptung hält.

Für die Cover dieses Blogs ist sie keine Behauptung, sondern nachrechenbar:
`scripts/generate_covers.py` zeichnet jede Datei aus einem Verlauf, einem
Badge, dem Titeltext und einem Markenband. Kein Bildmodell, kein Training,
keine Zufallsquelle. Derselbe Input ergibt dieselbe Datei. Am 13.11.2026
nachgemessen: **132 von 132 Covern** sind pixelidentisch zu einem frischen
Render (`cover_render_check.py`, 0 Befunde), und ein Lauf ohne `--force`
rendert nichts.

WAS DAS RECHTLICH BEDEUTET – UND WAS NICHT
------------------------------------------
Ein so erzeugtes Bild ist `algorithmicMedia` im Sinne des IPTC-Vokabulars:
von einem Algorithmus erzeugt, aber **nicht** mit Trainingsdaten eines
generativen Modells. Art. 50 Abs. 2 KI-VO spricht von Inhalten, die ein
KI-System erzeugt hat; eine deterministische Zeichenroutine ist kein solches
System. Die Covers sind deshalb **nicht** kennzeichnungspflichtig – und
genau das ist der Punkt: Ohne Beleg wäre „nicht deklariert" von „nicht
geprüft" nicht zu unterscheiden. Mit Beleg ist es eine Aussage.

Ausdrücklich **nicht** behauptet wird:
  · dass die Covers keine Rechte Dritter berühren (Schrift, Farben, Marke),
  · dass ein Leser die Herkunft nachprüfen kann, ohne dieses Repo zu haben,
  · dass ein späterer Lauf mit einem Bildmodell dieselbe Aussage trägt –
    dagegen steht die Reproduktionswache (`--pruefen`).

DREI BELEGE, EIN WERKZEUG
-------------------------
1. `--attestieren` schreibt je Cover `cover.ki_pruefung` ins Frontmatter:
   `digital_source_type: algorithmicMedia`, `variante: renderer-v3`,
   `sha256` der Datei, `verfahren` (Generator + Version) und `geprueft_am`.
   Das ist derselbe Ort, an dem ein KI-Cover seine Erzeugungsart belegt –
   ein Wahrheitsort, zwei mögliche Werte.
2. `--markieren` schreibt `DigitalSourceType=algorithmicMedia` als
   IPTC-XMP **in die Bilddatei** (ohne Neukodierung, APP1-Segment vor den
   Bilddaten). Damit trägt die Datei ihre Herkunft selbst – dieselbe
   Anforderung, die für Ton am 13.11.2026 umgesetzt wurde.
3. `--pruefen` ist die Wache: Es rendert jedes Cover erneut (ohne
   Schreibzugriff) und verlangt Pixelgleichheit. Weicht eines ab, ist die
   Attestation falsch geworden – dann ist das ein Befund, kein Rauschen.
   Zusätzlich: Steht `trainedAlgorithmicMedia` im Frontmatter, gehört die
   Datei dem KI-Weg (`ki_bild_markierung.py`), nicht diesem.

Aufruf:
  python3 scripts/ki_cover_herkunft.py --attestieren [--trocken]
  python3 scripts/ki_cover_herkunft.py --markieren [--trocken] [--force]
  python3 scripts/ki_cover_herkunft.py --pruefen        # Exit 0/1/2
  python3 scripts/ki_cover_herkunft.py --selftest

Exit-Codes: 0 sauber · 1 Inhaltsbefund · 2 Werkzeugfehler (C33/C38).
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

# IPTC-Wert für „von einem Algorithmus erzeugt, ohne Trainingsdaten".
# Bewusst NICHT `trainedAlgorithmicMedia`: Das behauptete ein trainiertes
# Modell, das hier nicht im Spiel ist (siehe Modul-Dokumentation).
TYP = "algorithmicMedia"
VARIANTE = "renderer-v3"
VERFAHREN = "generate_covers.py (Pillow, deterministisch)"
FRONTMATTER_FELD = "ki_pruefung"

# Felder, die ein KI-Cover belegen. Steht eines davon im Frontmatter, ist die
# Datei Sache des KI-Wegs – dieses Werkzeug fasst sie nicht an.
KI_FELDER = ("trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia")


class WerkzeugFehler(RuntimeError):
    """Messung nicht möglich – nie als Inhaltsbefund ausgeben."""


def _kern():
    try:
        import ki_cover_provenienz as kp
        import generate_covers as gc
    except ImportError as exc:  # pragma: no cover – Umgebung, nicht Inhalt
        raise WerkzeugFehler(f"Cover-Kern nicht ladbar: {exc}") from exc
    return kp, gc


def _ruhig_rendern(gc):
    """Varianten beim Test-Rendern abschalten.

    `make_cover` schreibt sonst responsive Ableitungen neben die Datei – im
    Selbsttest in ein temporäres Verzeichnis, das `image_optimizer` nicht
    kennt (`relative_to(BLOG_DIR)` wirft). Die Wache selbst rendert über
    `cover_render_check.render_to`, der genau das schon tut.
    """
    gc.save_modern_variants = lambda *a, **k: []
    return gc


def _sha256(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def _frontmatter_bereich(text: str) -> tuple[int, int]:
    """(Start, Ende) des YAML-Blocks zwischen den `---`-Zäunen."""
    if not text.startswith("---"):
        raise ValueError("kein YAML-Frontmatter")
    ende = text.find("\n---", 3)
    if ende < 0:
        raise ValueError("Frontmatter nicht abgeschlossen")
    return 3, ende


def _cover_block(text: str) -> tuple[int, int, int]:
    """(Start, Ende, Einrückung) des `cover:`-Blocks im Frontmatter.

    Ohne diesen Block kann kein Cover-Beleg eingetragen werden – und eine
    Attestation an der falschen Stelle wäre schlimmer als keine.
    """
    a, e = _frontmatter_bereich(text)
    fm = text[a:e]
    m = re.search(r"(?m)^cover:[ \t]*\r?\n", fm)
    if not m:
        raise ValueError("kein `cover:`-Block")
    start = a + m.end()
    rest = fm[m.end():]
    # Der Block endet an der ersten Zeile, die nicht eingerückt ist.
    versatz = 0
    for zeile in rest.splitlines(keepends=True):
        if zeile.strip() and not zeile.startswith((" ", "\t")):
            break
        versatz += len(zeile)
    return start, a + m.end() + versatz, len(re.match(r"[ \t]*", fm[m.end():]).group(0))


def beleg_vorhanden(cover: dict) -> bool:
    pruefung = cover.get(FRONTMATTER_FELD)
    return isinstance(pruefung, dict) and pruefung.get("digital_source_type") == TYP


def _beleg_zeilen(slug: str, sha: str, datum: str | None = None) -> list[str]:
    tag = datum or dt.date.today().isoformat()
    return [
        f"  {FRONTMATTER_FELD}:",
        f"    digital_source_type: {TYP}",
        f"    variante: {VARIANTE}",
        f'    verfahren: "{VERFAHREN}"',
        f"    sha256: {sha}",
        f"    geprueft_am: {tag}",
    ]


def im_renderbereich(pfad: Path) -> bool:
    """Gehört diese Seite zum Prüfbereich des Cover-Renderers?

    WARUM DIE FRAGE NÖTIG IST (Befund 13.11.2026)
    `cover_render_check.py` prüft Artikel (`content/posts`) und
    Ratgeber-Säulen (`content/pillar`) – das sind 132 der 134 Cover-
    Referenzen. Die übrigen zeigen das Markenbild
    (`brand-franksfinanzcheck.jpg`) auf statischen Seiten wie /newsletter/.
    Für die wäre „nicht reproduzierbar" kein Befund, sondern eine falsche
    Erwartung: Sie haben keinen eigenen Renderer-Lauf.

    Ein Beleg, der auch falsche Fälle prüft, ist kein Beleg. Deshalb wird
    der Bereich benannt und die Zahl der ausgeschlossenen Referenzen
    berichtet – nicht verschwiegen.
    """
    teile = pfad.resolve().parts
    return "posts" in teile or "pillar" in teile


def _ohne_beleg(block: str, einzug: int) -> str:
    """Entfernt einen bereits vorhandenen `ki_pruefung:`-Block aus `cover:`.

    Der Block gehört zu `cover:` und steht auf dessen Einrückungsebene
    (zwei Leerzeichen im Regelfall). Alles, was tiefer eingerückt ist,
    gehört zum Beleg und fällt mit weg.
    """
    zeilen = block.splitlines(keepends=True)
    behalten, ueberspringen = [], False
    for zeile in zeilen:
        if re.match(r"^" + re.escape(" " * einzug) + FRONTMATTER_FELD + r":", zeile):
            ueberspringen = True
            continue
        if ueberspringen:
            if zeile.strip() and not zeile.startswith(" " * (einzug + 1)):
                ueberspringen = False
            else:
                continue
        behalten.append(zeile)
    return "".join(behalten)


def attestieren(root: Path = ROOT, trocken: bool = False, nur: str | None = None):
    """Beleg je Cover ins Frontmatter. Rückgabe: (geschrieben, übersprungen, Fehler)."""
    kp, _ = _kern()
    geschrieben, uebersprungen, fehler = 0, 0, []
    for pfad, _fm, cover in kp.collect(root):
        slug = pfad.parent.name
        if nur and slug != nur:
            continue
        if not im_renderbereich(pfad):
            uebersprungen += 1
            continue
        datei = cover.get("image")
        if not datei:
            continue
        try:
            ziel = kp.local_cover(root, datei)
        except ValueError as exc:
            fehler.append(f"{slug}: {exc}")
            continue
        if not ziel.is_file():
            fehler.append(f"{slug}: Bilddatei fehlt ({datei})")
            continue
        # Fremde Belege nicht überschreiben: Ein KI-Cover gehört dem
        # KI-Weg, ein bereits attestiertes bleibt, wie es ist.
        vorhanden = cover.get(FRONTMATTER_FELD)
        if isinstance(vorhanden, dict) and vorhanden.get("digital_source_type") in KI_FELDER:
            uebersprungen += 1
            continue
        if beleg_vorhanden(cover):
            # Attestation vorhanden: nur die sha256 nachziehen, wenn die
            # Datei sich legitim geändert hat (sonst wäre der Beleg falsch).
            if vorhanden.get("sha256") == _sha256(ziel):
                uebersprungen += 1
                continue
        text = pfad.read_text(encoding="utf-8")
        try:
            start, ende, einzug = _cover_block(text)
        except ValueError as exc:
            fehler.append(f"{slug}: {exc}")
            continue
        block = text[start:ende]
        # Bestehenden Beleg-Block entfernen (idempotent neu setzen).
        # Vorhandenen Beleg entfernen – ohne Regex mit Rückverweisen
        # (der erste Entwurf hatte eine Gruppe, die es nicht gab, und warf
        # `invalid group reference`). Zeilenweise ist es außerdem lesbarer.
        block = _ohne_beleg(block, einzug)
        if not block.endswith("\n"):
            block += "\n"
        # Einrückung: `_beleg_zeilen` liefert bereits den Block-Einzug (zwei
        # Leerzeichen) und die Unterebene (vier). Vorher wurde der Einzug des
        # `cover:`-Blocks zusätzlich davorgesetzt – der Beleg rutschte damit
        # unter `alt:` statt unter `cover:` und das YAML war kaputt.
        neue_zeilen = "\n".join(_beleg_zeilen(slug, _sha256(ziel)))
        # Zwischen Block und Beleg darf keine Leerzeile entstehen: YAML liest
        # eine Leerzeile innerhalb eines Mappings als Trenner.
        neu_text = text[:start] + block.rstrip("\n") + "\n" + neue_zeilen + "\n" + text[ende:]
        if not trocken:
            pfad.write_text(neu_text, encoding="utf-8")
        geschrieben += 1
    return geschrieben, uebersprungen, fehler


def markieren(root: Path = ROOT, trocken: bool = False, force: bool = False):
    """IPTC `algorithmicMedia` in die Bilddatei schreiben (ohne Neukodierung)."""
    kp, _ = _kern()
    import ki_bild_markierung as km
    geschrieben, uebersprungen, fehler = 0, 0, []
    for pfad, _fm, cover in kp.collect(root):
        slug = pfad.parent.name
        if not im_renderbereich(pfad):
            uebersprungen += 1
            continue
        datei = cover.get("image")
        if not datei:
            continue
        try:
            ziel = kp.local_cover(root, datei)
        except ValueError as exc:
            fehler.append(f"{slug}: {exc}")
            continue
        if not ziel.is_file():
            fehler.append(f"{slug}: Bilddatei fehlt")
            continue
        if ziel.suffix.lower() != ".jpg":
            uebersprungen += 1  # PNG/WebP: eigener Container-Schreiber nötig
            continue
        stand = km.lesen(ziel)
        ist = stand.get("digital_source_type")
        if ist in KI_FELDER:
            uebersprungen += 1  # KI-Beleg — nicht überschreiben
            continue
        if ist == TYP:
            uebersprungen += 1
            continue
        if ist and not force:
            fehler.append(f"{slug}: fremde Erzeugungsart `{ist}` in der Datei "
                          "– nicht überschrieben (--force entscheidet)")
            continue
        paket = km.paket_bauen(TYP, werkzeug=VERFAHREN,
                               hinweis="Cover von FranksFinanzcheck – "
                                       "deterministisch gezeichnet, kein KI-Bildmodell")
        if trocken:
            geschrieben += 1
            continue
        km.schreiben(ziel, paket, force=True)
        geschrieben += 1
    return geschrieben, uebersprungen, fehler


def pruefen(root: Path = ROOT):
    """Reproduktionswache: Rendert jedes Cover neu und verlangt Pixelgleichheit.

    Das ist der eigentliche Beweis. Eine Attestation im Frontmatter ist eine
    Erklärung; die Pixelgleichheit ist eine Messung. Wer die Renderer-Version
    ändert, ohne neu zu rendern, bekommt hier einen Befund – nicht in einem
    halben Jahr bei einer Aufsicht.
    """
    kp, gc = _kern()
    try:
        import cover_render_check as crc
    except ImportError as exc:
        raise WerkzeugFehler(f"Render-Wache nicht ladbar: {exc}") from exc
    befunde, geprueft, ausserhalb = [], 0, 0
    with tempfile.TemporaryDirectory(prefix="cover-herkunft-") as tmp:
        for pfad, _fm, cover in kp.collect(root):
            slug = pfad.parent.name
            if not cover.get("image"):
                continue
            if not im_renderbereich(pfad):
                # Kein Renderer-Lauf für diese Seite (Markenbild auf einer
                # statischen Seite). Gezählt, nicht bewertet.
                ausserhalb += 1
                continue
            try:
                ziel = kp.local_cover(root, cover.get("image"))
            except ValueError:
                continue
            if not ziel.is_file():
                befunde.append(f"{slug}: Bilddatei fehlt")
                continue
            try:
                inhalt = pfad.read_text(encoding="utf-8")
                _slug, titel, badge, savings = crc.expected_inputs(gc, str(pfad), inhalt)
            except Exception as exc:  # pragma: no cover
                befunde.append(f"{slug}: Erwartung nicht ableitbar ({exc})")
                continue
            neu = os.path.join(tmp, f"{slug}.jpg")
            try:
                crc.render_to(gc, titel, badge, savings, neu)
            except Exception as exc:
                raise WerkzeugFehler(f"{slug}: Render nicht möglich ({exc})") from exc
            geprueft += 1
            if not crc.same_pixels(str(ziel), neu):
                befunde.append(f"{slug}: Bild weicht vom Renderer ab – die "
                               "Herkunftsangabe ist damit nicht mehr belegt "
                               "(Cover neu rendern, dann Beleg nachziehen)")
                continue
            if not beleg_vorhanden(cover):
                befunde.append(f"{slug}: reproduzierbar, aber ohne Beleg im "
                               "Frontmatter (--attestieren schreibt ihn)")
    return befunde, geprueft, ausserhalb


def selbsttest() -> int:
    """Sabotage-Proben an einer echten, aber künstlichen Cover-Lage."""
    import shutil
    fehler = []
    with tempfile.TemporaryDirectory(prefix="cover-herkunft-test-") as tmp:
        root = Path(tmp)
        for unter in ("content/posts", "static/images/covers", "scripts",
                      "layouts", "data"):
            (root / unter).mkdir(parents=True, exist_ok=True)
        # Ein Artikel mit echtem, vom Generator gezeichneten Cover.
        try:
            kp, gc = _kern()
        except WerkzeugFehler as exc:
            print(f"❌ Selbsttest nicht möglich: {exc}")
            return 2
        slug = "test-artikel"
        _ruhig_rendern(gc)
        cover = root / "static" / "images" / "covers" / f"{slug}.jpg"
        gc.make_cover("Strom sparen: Ratgeber", slug, str(cover), force=True,
                      badge="STROM & GAS SPAREN", savings=None)
        artikel = root / "content" / "posts" / slug / "index.md"
        artikel.parent.mkdir(parents=True, exist_ok=True)
        artikel.write_text(
            "---\ntitle: \"Strom sparen: Ratgeber\"\ndescription: Test\n"
            f"ai_generated: true\ncover:\n  image: \"images/covers/{slug}.jpg\"\n"
            "  alt: \"Test\"\n---\nText\n", encoding="utf-8")
        # 1) Ohne Beleg muss die Wache den fehlenden Beleg nennen.
        befunde, geprueft, ausserhalb = pruefen(root)
        if geprueft != 1:
            fehler.append(f"Wache prüfte {geprueft} statt 1 Cover")
        if not any("ohne Beleg" in b for b in befunde):
            fehler.append("Wache merkt einen fehlenden Beleg nicht")
        # 2) Attestation schreiben, dann muss Ruhe sein.
        geschrieben, _, _ = attestieren(root)
        if geschrieben != 1:
            fehler.append(f"attestieren schrieb {geschrieben} statt 1")
        befunde, _, _ = pruefen(root)
        if befunde:
            fehler.append(f"nach der Attestation noch Befunde: {befunde}")
        # 3) Bild manipulieren → die Attestation ist nicht mehr belegt.
        # Gemessen wird das an den PIXELN (die Wache vergleicht Bilder, nicht
        # Bytes). Ein angehängtes Nullbyte änderte kein Pixel – die Probe
        # wäre blind gewesen. Ein Pixel im Titelbereich zu schwärzen ist
        # genau die Manipulation, die auffallen muss.
        from PIL import Image
        bild = Image.open(cover).convert("RGB")
        bild.putpixel((500, 600), (0, 0, 0))
        bild.save(cover, "JPEG", quality=88)
        befunde, _, _ = pruefen(root)
        if not any("weicht vom Renderer ab" in b for b in befunde):
            fehler.append("Wache merkt ein manipuliertes Bild nicht")
        # 4) Fremder KI-Beleg wird nicht überschrieben.
        # 4) Fremder KI-Beleg wird nicht überschrieben. Der Beleg steht nach
        # Schritt 2 bereits im Frontmatter – hier wird nur sein WERT auf den
        # KI-Wert umgestellt (eine Attestation, die den KI-Beleg ersetzt,
        # wäre ein Datenverlust).
        text = artikel.read_text(encoding="utf-8")
        text = text.replace("digital_source_type: algorithmicMedia",
                            "digital_source_type: trainedAlgorithmicMedia")
        artikel.write_text(text, encoding="utf-8")
        _, uebersprungen, _ = attestieren(root)
        if uebersprungen < 1:
            fehler.append("attestieren überschreibt einen KI-Beleg")
        # 5) Datei-Markierung: make_cover markiert beim Rendern, und
        #    markieren() schreibt nach, falls eine Datei unmarkiert ist.
        gc.make_cover("Strom sparen: Ratgeber", slug, str(cover), force=True,
                      badge="STROM & GAS SPAREN", savings=None)
        import ki_bild_markierung as km
        stand = km.lesen(cover)
        if stand.get("digital_source_type") != TYP:
            fehler.append(f"make_cover markiert nicht "
                          f"(gelesen {stand.get('digital_source_type')})")
        # Markierung entfernen (Neusave streift APP1/XMP), dann muss
        # markieren() sie wiederherstellen.
        from PIL import Image
        Image.open(cover).convert("RGB").save(cover, "JPEG", quality=88)
        markiert, _, _ = markieren(root, force=True)
        stand = km.lesen(cover)
        if markiert != 1 or stand.get("digital_source_type") != TYP:
            fehler.append(f"markieren schreibt nicht nach "
                          f"(geschrieben {markiert}, gelesen {stand.get('digital_source_type')})")
    if fehler:
        print("❌ Cover-Herkunft-Selbsttest FEHLGESCHLAGEN:")
        for f in fehler:
            print("   -", f)
        return 2
    print("✅ Cover-Herkunft: Beleg erkannt, Attestation wirksam, Manipulation "
          "erkannt, KI-Beleg geschützt, IPTC in der Datei lesbar.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--attestieren", action="store_true",
                        help="Beleg (variante + sha256) ins Cover-Frontmatter")
    parser.add_argument("--markieren", action="store_true",
                        help="IPTC algorithmicMedia in die Bilddatei schreiben")
    parser.add_argument("--pruefen", action="store_true",
                        help="Reproduktionswache: Cover nachrendern und vergleichen")
    parser.add_argument("--selftest", action="store_true", help="Sabotage-Proben")
    parser.add_argument("--trocken", action="store_true", help="nur zeigen, nichts schreiben")
    parser.add_argument("--force", action="store_true", help="fremde Angabe ersetzen")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selbsttest()
    try:
        if args.pruefen:
            befunde, geprueft, ausserhalb = pruefen()
            if args.json:
                print(json.dumps({"geprueft": geprueft, "ausserhalb": ausserhalb,
                                  "befunde": befunde}, ensure_ascii=False, indent=2))
            else:
                for b in befunde:
                    print(f"::error title=Cover-Herkunft::{b}")
                print(f"Cover-Herkunft: {geprueft} Cover reproduziert, "
                      f"{ausserhalb} außerhalb des Renderbereichs "
                      f"(Marken-/statische Seiten), {len(befunde)} Befund(e).")
            return 1 if befunde else 0
        if args.attestieren:
            geschrieben, uebersprungen, fehler = attestieren(trocken=args.trocken)
            print(f"Cover-Herkunft: {geschrieben} Beleg(e) "
                  f"{'geplant' if args.trocken else 'geschrieben'}, "
                  f"{uebersprungen} bereits belegt, {len(fehler)} Fehler.")
            for f in fehler:
                print(f"::error title=Cover-Herkunft::{f}")
            return 1 if fehler else 0
        if args.markieren:
            geschrieben, uebersprungen, fehler = markieren(
                trocken=args.trocken, force=args.force)
            print(f"Cover-Herkunft: {geschrieben} Bilddatei(en) "
                  f"{'geplant' if args.trocken else 'markiert'}, "
                  f"{uebersprungen} unverändert, {len(fehler)} Fehler.")
            for f in fehler:
                print(f"::error title=Cover-Herkunft::{f}")
            return 1 if fehler else 0
        parser.print_help()
        return 0
    except WerkzeugFehler as exc:
        # Messung ausgefallen ≠ Inhalt falsch (C33/C38).
        print(f"::error title=Cover-Herkunft (Werkzeug)::{exc}")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
