"""Maschinenlesbare Bildmarkierung: IPTC DigitalSourceType in der Datei (#1028).

Geprüft wird am echten Rundlauf (JPEG erzeugen → markieren → auslesen) und am
Bestandsgate mit einer künstlichen Inhaltsdatei. Die Bilddaten müssen
byteweise erhalten bleiben: Ein neu kodiertes Bild wäre ein anderes Bild –
und ein verdeckt geänderter Hash bricht ki_cover_provenienz.py.
"""
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

try:
    from PIL import Image
except ImportError:  # CI liefert Pillow über requirements-ci.txt
    Image = None

from scripts import ki_bild_markierung as markierung


def jpeg(pfad: Path, farbe=(12, 90, 160), groesse=(40, 30)) -> bytes:
    puffer = io.BytesIO()
    Image.new("RGB", groesse, farbe).save(puffer, format="JPEG", quality=90)
    daten = puffer.getvalue()
    pfad.write_bytes(daten)
    return daten


@unittest.skipIf(Image is None, "Pillow nicht installiert")
class BilddateiTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bild = self.root / "cover.jpg"
        self.original = jpeg(self.bild)
        self.paket = markierung.paket_bauen(
            "trainedAlgorithmicMedia", werkzeug="Beispiel-Generator",
            hinweis="Mit KI erstellt oder bearbeitet", datum="2026-11-05T00:00:00Z")

    def test_markierung_ist_lesbar_und_beruehrt_die_pixel_nicht(self):
        self.assertEqual(markierung.schreiben(self.bild, self.paket), "ergaenzt")
        stand = markierung.lesen(self.bild)
        self.assertEqual(stand["digital_source_type"], "trainedAlgorithmicMedia")
        self.assertEqual(stand["ai_system"], "Beispiel-Generator")
        self.assertTrue(stand["xmp"])

        neu = self.bild.read_bytes()
        self.assertTrue(neu.startswith(markierung.SOI))
        self.assertTrue(neu.endswith(self.original[2:]), "Bilddaten verändert")
        self.assertEqual(hashlib.sha256(Image.open(self.bild).tobytes()).hexdigest(),
                         hashlib.sha256(Image.open(io.BytesIO(self.original)).tobytes()).hexdigest())

    def test_segmentkette_bleibt_valide(self):
        markierung.schreiben(self.bild, self.paket)
        daten = self.bild.read_bytes()
        enden = [offset + laenge + 2 for offset, laenge in markierung.segmente(daten)]
        self.assertTrue(enden, "keine Segmente gefunden")
        self.assertEqual(daten[max(enden):max(enden) + 2], b"\xff\xda",
                         "Segmentlänge führt nicht auf den Start of Scan")

    def test_idempotenz_und_schutz_fremder_metadaten(self):
        self.assertEqual(markierung.schreiben(self.bild, self.paket), "ergaenzt")
        self.assertEqual(markierung.schreiben(self.bild, self.paket), "unveraendert")
        anderes = markierung.paket_bauen("compositeWithTrainedAlgorithmicMedia")
        self.assertEqual(markierung.schreiben(self.bild, anderes), "blockiert")
        self.assertEqual(markierung.lesen(self.bild)["digital_source_type"],
                         "trainedAlgorithmicMedia", "fremdes XMP wurde still überschrieben")
        self.assertEqual(markierung.schreiben(self.bild, anderes, force=True), "ersetzt")
        self.assertEqual(markierung.lesen(self.bild)["digital_source_type"],
                         "compositeWithTrainedAlgorithmicMedia")

    def test_manifest_verweis_wird_geschrieben(self):
        paket = markierung.paket_bauen("trainedAlgorithmicMedia",
                                       manifest_url="https://example.org/c2pa/1.json")
        markierung.schreiben(self.bild, paket)
        self.assertEqual(markierung.lesen(self.bild)["provenienz_url"],
                         "https://example.org/c2pa/1.json")

    def test_andere_formate_werden_abgelehnt(self):
        png = self.root / "cover.png"
        Image.new("RGB", (8, 8)).save(png, format="PNG")
        with self.assertRaises(ValueError):
            markierung.schreiben(png, self.paket)
        self.assertEqual(markierung.lesen(png)["format"], "png")
        self.assertFalse(markierung.lesen(png)["xmp"])


@unittest.skipIf(Image is None, "Pillow nicht installiert")
class BestandsGateTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bild = self.root / "static/images/covers/ki.jpg"
        self.bild.parent.mkdir(parents=True)
        jpeg(self.bild)
        self.post = self.root / "content/posts/ki-artikel/index.md"
        self.post.parent.mkdir(parents=True)
        self.sha = hashlib.sha256(self.bild.read_bytes()).hexdigest()

    def deklarieren(self, typ: str | None):
        zeilen = ["cover:", "  image: /images/covers/ki.jpg", "  ai_generated: true",
                  "  ki_pruefung:", f"    sha256: {self.sha}", '    quelle: "Auftrag 17"',
                  "    geprueft_am: 2026-01-01", "    deepfake: false"]
        if typ:
            zeilen.append(f"    digital_source_type: {typ}")
        self.post.write_text("---\ntitle: KI\n" + "\n".join(zeilen) + "\n---\nText\n",
                             encoding="utf-8")

    def test_ohne_markierung_ist_es_ein_fund(self):
        self.deklarieren("trainedAlgorithmicMedia")
        _, fehler = markierung.pruefen(self.root)
        self.assertTrue(any("maschinenlesbare Markierung" in f for f in fehler), fehler)

    def test_ohne_belegte_art_wird_nichts_erfunden(self):
        self.deklarieren(None)
        _, fehler = markierung.pruefen(self.root)
        self.assertTrue(any("digital_source_type fehlt" in f for f in fehler), fehler)
        erledigt, _ = markierung.heilen(self.root)
        self.assertEqual(erledigt, [])
        self.assertFalse(markierung.lesen(self.bild)["xmp"])

    def test_falscher_wert_ist_ein_fund(self):
        self.deklarieren("digitalCapture")
        _, fehler = markierung.pruefen(self.root)
        self.assertTrue(any("kein erlaubter IPTC-Wert" in f for f in fehler), fehler)

    def test_heilung_macht_den_bestand_gruen(self):
        self.deklarieren("trainedAlgorithmicMedia")
        erledigt, fehler = markierung.heilen(self.root)
        self.assertEqual(len(erledigt), 1)
        self.assertEqual(fehler, [])
        _, fehler = markierung.pruefen(self.root)
        self.assertEqual(fehler, [])
        # Die Markierung ändert die Datei – der deklarierte Hash muss danach
        # neu belegt werden, sonst meldet ki_cover_provenienz.py zu Recht.
        self.assertNotEqual(hashlib.sha256(self.bild.read_bytes()).hexdigest(), self.sha)


if __name__ == "__main__":
    unittest.main()
