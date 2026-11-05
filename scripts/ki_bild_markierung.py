#!/usr/bin/env python3
"""KI-Bild-Markierung – maschinenlesbare Herkunft IN der Bilddatei (#1028).

Was das leistet
---------------
Sichtbare Bildunterschriften und `data-`-Attribute im HTML sind Angaben für
Menschen und für den eigenen DOM. Was ein Dritter (Plattform, Detektor,
Aufsicht) aus der *Datei* lesen kann, steht in deren Metadaten. Der
Verhaltenskodex der Kommission vom 10.06.2026 nennt dafür signierte Metadaten
(C2PA-Familie) plus Wasserzeichen; das unverschlüsselte, aber breit gelesene
Feld ist IPTC `DigitalSourceType` (XMP `Iptc4xmpExt:DigitalSourceType`), das
C2PA in `c2pa.actions` übernimmt und das u. a. Meta, Apple, Google und
Pinterest auswerten.

Dieses Werkzeug schreibt genau dieses Feld in ausdrücklich als KI deklarierte
Cover – als XMP-Paket im JPEG-APP1-Segment, **ohne die Bilddaten neu zu
kodieren**. Pixel und bestehende EXIF-/ICC-Daten bleiben byteweise erhalten;
es kommt nur ein Segment hinzu (oder das vorhandene XMP-Segment wird
ersetzt, wenn `--force` das ausdrücklich erlaubt).

Rechtliche Grenze
-----------------
Art. 50 Abs. 2 KI-VO ist eine Pflicht des ANBIETERS des generativen Systems.
Ein selbst gesetztes XMP-Feld ist eine Angabe des Betreibers: nicht signiert,
leicht entfernbar und kein Herkunftsbeweis. Es ersetzt weder die Anbieter-
Markierung noch ein Wasserzeichen – es macht die eigene Erklärung aber in der
Datei auffindbar, statt sie nur im HTML zu haben.

Aufruf
------
    python3 scripts/ki_bild_markierung.py             # Befund (Report)
    python3 scripts/ki_bild_markierung.py --gate      # Exit 1 bei Lücke
    python3 scripts/ki_bild_markierung.py --write     # XMP-Feld ergänzen
    python3 scripts/ki_bild_markierung.py --json
    python3 scripts/ki_bild_markierung.py --selftest

Exit: 0 = alles markiert · 1 = Lücke (--gate) · 2 = Fehler
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from xml.sax.saxutils import escape

sys.path.insert(0, str(Path(__file__).resolve().parent))

# ki_cover_provenienz bringt PyYAML mit. Der Selbsttest braucht das Register
# nicht und darf deshalb nicht an einer fehlenden Abhängigkeit scheitern –
# der Import erfolgt erst dort, wo der Bestand gelesen wird.
_provenienz = None


def provenienz():
    global _provenienz
    if _provenienz is None:
        import ki_cover_provenienz  # noqa: PLC0415  (bewusst verzögert)
        _provenienz = ki_cover_provenienz
    return _provenienz

ROOT = Path(__file__).resolve().parents[1]

XMP_NS_HEADER = b"http://ns.adobe.com/xap/1.0/\x00"
XMP_BEGIN = "<?xpacket begin"
VOKABULAR = "http://cv.iptc.org/newscodes/digitalsourcetype/"
# IPTC Digital Source Type – nur die beiden Werte, die eine KI-Beteiligung
# aussagen. `algorithmicMedia` (reiner Algorithmus ohne Trainingsdaten) gehört
# nicht hierher: Die Cover-Pipeline erzeugt damit zwar Grafiken, aber keine
# KI-Inhalte, und sie wird bewusst nicht pauschal markiert.
ERLAUBTE_TYPEN = ("trainedAlgorithmicMedia", "compositeWithTrainedAlgorithmicMedia")
SOI = b"\xff\xd8"
APP1 = b"\xff\xe1"


def typ_aus(cover: dict) -> str | None:
    """Belegte Erzeugungsart aus dem Frontmatter, sonst None."""
    pruefung = cover.get("ki_pruefung")
    if not isinstance(pruefung, dict):
        return None
    wert = pruefung.get("digital_source_type")
    return wert.strip() if isinstance(wert, str) and wert.strip() else None


def paket_bauen(typ: str, werkzeug: str | None = None, hinweis: str | None = None,
                manifest_url: str | None = None, datum: str | None = None) -> str:
    """XMP-Paket mit IPTC-DigitalSourceType (UTF-8, ohne BOM-Zeichen im Text)."""
    zeit = datum or dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    felder = [
        f'      <Iptc4xmpExt:DigitalSourceType>{VOKABULAR}{typ}</Iptc4xmpExt:DigitalSourceType>',
    ]
    if werkzeug:
        felder.append(f"      <Iptc4xmpExt:AISystemUsed>{escape(werkzeug)}</Iptc4xmpExt:AISystemUsed>")
    if manifest_url:
        # C2PA erlaubt ein externes Manifest, das per dcterms:provenance
        # referenziert wird (Link-Relation `c2pa-manifest` ist bei IANA
        # registriert). Signiert wird außerhalb dieses Werkzeugs.
        url = escape(str(manifest_url), {'"': "&quot;", "'": "&apos;"})
        felder.append(f'      <dcterms:provenance rdf:resource="{url}"/>')
    if hinweis:
        felder.append(
            "      <dc:description><rdf:Alt>"
            f'<rdf:li xml:lang="de">{escape(hinweis)}</rdf:li>'
            "</rdf:Alt></dc:description>"
        )
    felder.append(f"      <xmp:MetadataDate>{zeit}</xmp:MetadataDate>")
    return (
        '<?xpacket begin="\ufeff" id="W5M0MpCehiHzreSzNTczkc9d"?>\n'
        '<x:xmpmeta xmlns:x="adobe:ns:meta/" x:xmptk="franksfinanzcheck-blog">\n'
        '  <rdf:RDF xmlns:rdf="http://www.w3.org/1999-02-22-rdf-syntax-ns#">\n'
        '    <rdf:Description rdf:about=""\n'
        '      xmlns:dc="http://purl.org/dc/elements/1.1/"\n'
        '      xmlns:dcterms="http://purl.org/dc/terms/"\n'
        '      xmlns:Iptc4xmpExt="http://iptc.org/std/Iptc4xmpExt/2008-02-29/"\n'
        '      xmlns:xmp="http://ns.adobe.com/xap/1.0/">\n'
        + "\n".join(felder) + "\n"
        "    </rdf:Description>\n"
        "  </rdf:RDF>\n"
        "</x:xmpmeta>\n"
        '<?xpacket end="w"?>'
    )


def segmente(daten: bytes):
    """Liefert (Offset, Länge) aller JPEG-Segmente nach SOI."""
    if not daten.startswith(SOI):
        raise ValueError("kein JPEG (SOI fehlt)")
    pos = 2
    while pos + 4 <= len(daten):
        if daten[pos] != 0xFF:
            return
        marker = daten[pos + 1]
        if marker == 0xD8 or marker == 0xFF:  # Füllbyte
            pos += 1
            continue
        if marker == 0xDA:  # Start of Scan: dahinter liegen die Bilddaten
            return
        if marker in (0xD9,) or 0xD0 <= marker <= 0xD7:
            pos += 2
            continue
        laenge = int.from_bytes(daten[pos + 2:pos + 4], "big")
        if laenge < 2 or pos + 2 + laenge > len(daten):
            return
        yield pos, laenge
        pos += 2 + laenge


def xmp_bereich(daten: bytes) -> tuple[int, int] | None:
    """(Start, Ende) des XMP-APP1-Segments, falls vorhanden."""
    for offset, laenge in segmente(daten):
        if not daten.startswith(APP1, offset):
            continue
        inhalt = daten[offset + 4:offset + 2 + laenge]
        if inhalt.startswith(XMP_NS_HEADER):
            return offset, offset + 2 + laenge
    return None


def lesen(pfad: Path) -> dict:
    """Maschinenlesbare KI-Angaben einer Datei auslesen (ohne Bild-Decoder)."""
    daten = pfad.read_bytes()
    ergebnis = {"datei": pfad.name, "format": None, "xmp": False,
                "digital_source_type": None, "ai_system": None,
                "provenienz_url": None}
    if daten.startswith(SOI):
        ergebnis["format"] = "jpeg"
    elif daten.startswith(b"\x89PNG\r\n\x1a\n"):
        ergebnis["format"] = "png"
    elif daten[:4] == b"RIFF" and daten[8:12] == b"WEBP":
        ergebnis["format"] = "webp"
    elif daten[4:8] == b"ftyp":
        ergebnis["format"] = "avif"
    text = daten.decode("utf-8", errors="ignore")
    if XMP_BEGIN in text:
        ergebnis["xmp"] = True
        m = re.search(re.escape(VOKABULAR) + r"([A-Za-z]+)", text)
        if m:
            ergebnis["digital_source_type"] = m.group(1)
        m = re.search(r"<Iptc4xmpExt:AISystemUsed>([^<]*)</Iptc4xmpExt:AISystemUsed>", text)
        if m:
            ergebnis["ai_system"] = m.group(1)
        m = re.search(r'<dcterms:provenance rdf:resource="([^"]+)"', text)
        if m:
            ergebnis["provenienz_url"] = m.group(1)
    return ergebnis


def schreiben(pfad: Path, paket: str, force: bool = False) -> str:
    """XMP-Paket einsetzen, ohne Bilddaten zu berühren.

    Rückgabe: "ergaenzt" · "unveraendert" · "ersetzt" · "blockiert".
    """
    daten = pfad.read_bytes()
    if not daten.startswith(SOI):
        raise ValueError(
            f"{pfad.name}: nur JPEG kann dieses Werkzeug ohne Neukodierung "
            "markieren (PNG/WebP/AVIF brauchen eigene Container-Schreiber)"
        )
    kodiert = paket.encode("utf-8")
    payload = XMP_NS_HEADER + kodiert
    # JPEG-Segmentlänge = Nutzlast + die zwei Längenbytes selbst (ohne Marker).
    # Ein um 2 zu kurzes Längenfeld lässt strikte Leser mitten im Paket
    # aufsetzen – die Datei wäre für jeden Metadaten-Parser unbrauchbar.
    if len(payload) + 2 > 0xFFFF:
        raise ValueError("XMP-Paket zu groß für ein APP1-Segment")
    segment = APP1 + (len(payload) + 2).to_bytes(2, "big") + payload
    alt = xmp_bereich(daten)
    if alt:
        vorhanden = daten[alt[0]:alt[1]]
        if vorhanden == segment:
            return "unveraendert"
        if not force:
            return "blockiert"
        neu = daten[:alt[0]] + segment + daten[alt[1]:]
        pfad.write_bytes(neu)
        return "ersetzt"
    pfad.write_bytes(daten[:2] + segment + daten[2:])
    return "ergaenzt"


def zielliste(root: Path = ROOT):
    """Alle ausdrücklich als KI deklarierten Cover mit ihrer Beleglage."""
    quelle = provenienz()
    ziele, fehler = [], []
    for pfad, fm, cover in quelle.collect(root):
        if cover.get("ai_generated") is not True:
            continue
        rel = pfad.relative_to(root).as_posix()
        pruefung = cover.get("ki_pruefung") if isinstance(cover.get("ki_pruefung"), dict) else {}
        try:
            datei = quelle.local_cover(root, cover.get("image"))
        except ValueError as exc:
            fehler.append(f"{rel}: {exc}")
            continue
        ziele.append({
            "content": rel,
            "datei": datei,
            "typ": typ_aus(cover),
            "werkzeug": pruefung.get("werkzeug"),
            "manifest_url": pruefung.get("c2pa_manifest_url"),
            "hinweis": "Mit KI erstellt oder bearbeitet – FranksFinanzcheck",
        })
    return ziele, fehler


def pruefen(root: Path = ROOT):
    """Befund je deklariertem KI-Cover. Nie raten: fehlende Belege sind Fehler."""
    ziele, fehler = zielliste(root)
    befunde = []
    for ziel in ziele:
        rel = ziel["content"]
        if not ziel["datei"].is_file():
            fehler.append(f"{rel}: Originaldatei fehlt – Markierung nicht prüfbar")
            continue
        stand = lesen(ziel["datei"])
        stand["content"] = rel
        stand["datei"] = ziel["datei"].relative_to(root).as_posix()
        stand["erwartet"] = ziel["typ"]
        befunde.append(stand)
        if stand["format"] != "jpeg":
            fehler.append(
                f"{rel}: {stand['datei']} ist {stand['format'] or 'unbekannt'} – "
                "für dieses Format ist kein Markierungsweg hinterlegt; "
                "Datei nicht als KI-Cover ausspielen oder Format wechseln"
            )
            continue
        if not ziel["typ"]:
            fehler.append(
                f"{rel}: cover.ki_pruefung.digital_source_type fehlt "
                f"({'/'.join(ERLAUBTE_TYPEN)}) – ohne belegte Erzeugungsart "
                "wird nichts markiert"
            )
            continue
        if ziel["typ"] not in ERLAUBTE_TYPEN:
            fehler.append(f"{rel}: digital_source_type „{ziel['typ']}“ ist kein erlaubter IPTC-Wert")
            continue
        if stand["digital_source_type"] != ziel["typ"]:
            fehler.append(
                f"{rel}: {stand['datei']} trägt "
                f"{'keine' if not stand['digital_source_type'] else 'eine abweichende'} "
                f"maschinenlesbare Markierung (erwartet {ziel['typ']}) – "
                "scripts/ki_bild_markierung.py --write"
            )
    return befunde, fehler


def heilen(root: Path = ROOT, force: bool = False):
    ziele, fehler = zielliste(root)
    getan = []
    for ziel in ziele:
        rel = ziel["content"]
        if not ziel["typ"] or ziel["typ"] not in ERLAUBTE_TYPEN:
            fehler.append(f"{rel}: keine belegte Erzeugungsart – nichts geschrieben")
            continue
        if not ziel["datei"].is_file():
            fehler.append(f"{rel}: Originaldatei fehlt – nichts geschrieben")
            continue
        paket = paket_bauen(
            ziel["typ"],
            werkzeug=ziel["werkzeug"],
            hinweis=ziel["hinweis"],
            manifest_url=ziel["manifest_url"],
        )
        try:
            ergebnis = schreiben(ziel["datei"], paket, force=force)
        except (OSError, ValueError) as exc:
            fehler.append(f"{rel}: {exc}")
            continue
        if ergebnis == "blockiert":
            fehler.append(
                f"{rel}: {ziel['datei'].name} enthält bereits XMP-Metadaten, die "
                "von dieser Markierung abweichen. Fremde Herkunftsnachweise "
                "werden nicht still überschrieben – Einzelfall klären und "
                "bei bewusster Entscheidung --force nutzen"
            )
            continue
        getan.append({"content": rel, "datei": ziel["datei"].name, "ergebnis": ergebnis})
    return getan, fehler


def selbsttest() -> int:
    """Echter Rundlauf: JPEG erzeugen, markieren, wieder auslesen."""
    import hashlib
    import io
    import tempfile

    fehler = []
    try:
        from PIL import Image
    except ImportError:
        print("⚠️  Pillow fehlt – Selbsttest der Bilddatei übersprungen "
              "(pip install -r requirements-ci.txt).")
        Image = None

    with tempfile.TemporaryDirectory() as tmp:
        basis = Path(tmp)
        if Image is not None:
            bild = Image.new("RGB", (40, 30), (12, 90, 160))
            puffer = io.BytesIO()
            bild.save(puffer, format="JPEG", quality=90)
            original = puffer.getvalue()
            datei = basis / "cover.jpg"
            datei.write_bytes(original)

            vor_pixel = hashlib.sha256(Image.open(datei).tobytes()).hexdigest()
            paket = paket_bauen("trainedAlgorithmicMedia", werkzeug="Beispiel-Generator",
                                hinweis="Testhinweis", datum="2026-11-05T00:00:00Z")
            if schreiben(datei, paket) != "ergaenzt":
                fehler.append("erste Markierung nicht ergänzt")
            stand = lesen(datei)
            if stand["digital_source_type"] != "trainedAlgorithmicMedia":
                fehler.append(f"DigitalSourceType nicht lesbar: {stand}")
            if stand["ai_system"] != "Beispiel-Generator":
                fehler.append("AISystemUsed nicht lesbar")
            if stand["format"] != "jpeg" or not stand["xmp"]:
                fehler.append("Format/XMP nicht erkannt")
            neu = datei.read_bytes()
            if neu[:2] != SOI or not neu.endswith(original[2:]):
                fehler.append("Bilddaten wurden verändert statt ergänzt")
            # Gegenprobe auf die Segmentlänge: Ein strikter Leser muss vom
            # SOI über das neue XMP-Segment bis zum Start of Scan kommen.
            if b"\xff\xda" not in neu[2:]:
                fehler.append("Scan-Daten hinter dem XMP-Segment nicht erreichbar")
            ende = None
            for offset, laenge in segmente(neu):
                ende = offset + 2 + laenge
            if ende is None or neu[ende:ende + 2] != b"\xff\xda":
                fehler.append("Segmentkette führt nicht auf den Start of Scan")
            nach_pixel = hashlib.sha256(Image.open(datei).tobytes()).hexdigest()
            if vor_pixel != nach_pixel:
                fehler.append("Pixel nach Markierung verändert")
            if schreiben(datei, paket) != "unveraendert":
                fehler.append("Markierung nicht idempotent")
            if schreiben(datei, paket_bauen("compositeWithTrainedAlgorithmicMedia")) != "blockiert":
                fehler.append("abweichendes XMP wurde ohne --force überschrieben")
            if schreiben(datei, paket_bauen("compositeWithTrainedAlgorithmicMedia"), force=True) != "ersetzt":
                fehler.append("--force ersetzt abweichendes XMP nicht")
            if lesen(datei)["digital_source_type"] != "compositeWithTrainedAlgorithmicMedia":
                fehler.append("ersetzter Wert nicht lesbar")

            png = basis / "cover.png"
            Image.new("RGB", (8, 8)).save(png, format="PNG")
            try:
                schreiben(png, paket)
            except ValueError:
                pass
            else:
                fehler.append("PNG wurde statt Ablehnung geschrieben")

        # Vokabular und Paketform ohne Bilddatei prüfen
        if "cv.iptc.org" not in paket_bauen("trainedAlgorithmicMedia"):
            fehler.append("IPTC-Vokabular-URI fehlt im Paket")
        if "&" in paket_bauen("trainedAlgorithmicMedia", hinweis="A & B") and "&amp;" not in paket_bauen("trainedAlgorithmicMedia", hinweis="A & B"):
            fehler.append("Hinweistext nicht XML-escapt")
        if typ_aus({"ki_pruefung": {"digital_source_type": "trainedAlgorithmicMedia"}}) != "trainedAlgorithmicMedia":
            fehler.append("typ_aus liest belegten Wert nicht")
        if typ_aus({"ki_pruefung": {}}) is not None or typ_aus({}) is not None:
            fehler.append("typ_aus erfindet einen Wert")

    for f in fehler:
        print(f"❌ {f}")
    if fehler:
        return 2
    print("✅ KI-Bild-Markierung: IPTC-DigitalSourceType lesbar, Pixel unverändert, "
          "idempotent, fremdes XMP geschützt.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    gruppe = parser.add_mutually_exclusive_group()
    gruppe.add_argument("--gate", action="store_true")
    gruppe.add_argument("--write", action="store_true")
    gruppe.add_argument("--selftest", action="store_true")
    parser.add_argument("--force", action="store_true",
                        help="abweichendes fremdes XMP bewusst ersetzen")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selbsttest()
    try:
        if args.write:
            getan, fehler = heilen(force=args.force)
            befunde, _ = pruefen()
        else:
            getan, befunde, fehler = [], *pruefen()
    except (OSError, ValueError) as exc:
        print(f"KI-Bild-Markierung nicht ausführbar: {exc}")
        return 2

    if args.json:
        print(json.dumps({"markiert": getan, "bestand": befunde, "fehler": fehler},
                         ensure_ascii=False, indent=2))
    else:
        deklariert = len(befunde)
        markiert = sum(b["digital_source_type"] in ERLAUBTE_TYPEN for b in befunde)
        print(f"KI-Bild-Markierung: {deklariert} als KI deklarierte Cover, "
              f"{markiert} maschinenlesbar markiert, {len(fehler)} Befund(e).")
        for eintrag in getan:
            print(f"::notice title=KI-Bild markiert::{eintrag['datei']}: {eintrag['ergebnis']}")
        for f in fehler:
            print(f"::error title=KI-Bild-Markierung::{f}")
        if deklariert == 0:
            print("Hinweis: kein Cover ist als KI deklariert (cover.ai_generated: true). "
                  "Die Markierung greift erst, wenn eine Bildherkunft belegt ist – "
                  "pauschal wird nichts gesetzt.")
    if args.gate and fehler:
        return 1
    if args.write and fehler:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
