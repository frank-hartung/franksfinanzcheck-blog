"""Tonspur-Markierung: Herkunft IN der Datei, ohne Neukodierung (#1028).

Befund 13.11.2026: Der Blog liefert vorab erzeugte Vorlese-Tonspuren aus
(synthetische Stimme). Die Seite kennzeichnete das auf sieben Kanälen – die
DATEI enthielt keine einzige Angabe. Wer sie herunterlädt oder weiterreicht,
hielt synthetische Sprache ohne Herkunft in der Hand.

Diese Tests prüfen das, was ein Werkzeug behaupten darf und was nicht:

* Die Audiodaten bleiben byteweise gleich (kein Neukodieren, kein Pegel).
* Der Tag ist lesbar wie ein Fremdleser ihn liest – nicht wie wir ihn
  schreiben (Rundlauf über die eigene Lesefunktion UND über `mutagen`,
  wenn es installiert ist).
* Fremde Metadaten werden nicht überschrieben: Das `Lavf…` des Encoders,
  ein fremder `DigitalSourceType` und bestehende Frames bleiben.
* `--entfernen` stellt die Datei BYTEGLEICH wieder her – auch bei der
  ID3v2.4-Kopfzeile, die `ffmpeg` selbst schreibt.
* Ohne Erzeugerbeleg (Sidecar) wird NICHTS markiert.
"""
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts import ki_audio_markierung as markierung

ROOT = Path(__file__).resolve().parents[2]


def _ffmpeg() -> str | None:
    """Ein ffmpeg finden – System, `imageio-ffmpeg` oder `$FFMPEG_BIN`."""
    import os
    kandidat = os.environ.get("FFMPEG_BIN") or shutil.which("ffmpeg")
    if kandidat:
        return kandidat
    try:  # CI und Sandbox: wheel mitgeliefert, kein apt nötig
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return None


FFMPEG = _ffmpeg()


def _erzeuge(ziel: Path, format: str) -> bool:
    """Eine ECHTE Datei vom Encoder – kein selbstgebauter Kopf.

    Der Unterschied ist nicht akademisch: Genau an einer echten ffmpeg-Datei
    sind am 13.11.2026 drei Fehler aufgefallen, die ein selbstgebauter
    Frame nie gezeigt hätte (ID3v2.4 statt v2.3, Null-Padding im Tag,
    `ISFT` des Encoders im RIFF-INFO).
    """
    if not FFMPEG:
        return False
    cmd = [FFMPEG, "-y", "-v", "error", "-f", "lavfi", "-i",
           "sine=frequency=440:duration=1", "-ar", "24000", "-ac", "1"]
    cmd += ["-c:a", "libmp3lame", "-b:a", "64k", str(ziel)] if format == "mp3" else [str(ziel)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except (OSError, subprocess.CalledProcessError):
        return False
    return ziel.is_file() and ziel.stat().st_size > 0


def _audiodaten(daten: bytes) -> bytes:
    """Nur die Audiodaten – bei MP3 hinter dem ID3-Tag, bei WAV der data-Chunk."""
    art = markierung._format(daten)
    if art == "mp3":
        bereich = markierung.id3_bereich(daten)
        return daten[bereich[1]:] if bereich else daten
    for kennung, inhalt, _ in markierung._riff_chunks(daten):
        if kennung == b"data":
            return inhalt
    return daten


class RundlaufTest(unittest.TestCase):
    """Ohne Encoder: die Mathematik der Container (immer lauffähig)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ordner = Path(self.tmp.name)

    def test_mp3_waechst_und_bleibt_hoerbar(self):
        datei = self.ordner / "probe.mp3"
        datei.write_bytes(markierung._mini_mp3())
        vorher = datei.read_bytes()
        self.assertEqual(markierung.schreiben(datei, "trainedAlgorithmicMedia",
                                             system="edge"), "ergaenzt")
        nachher = datei.read_bytes()
        self.assertTrue(nachher.endswith(vorher), "Audiodaten wurden angefasst")
        stand = markierung.markierung_lesen(nachher)
        self.assertTrue(stand["markiert"])
        self.assertEqual(stand["system"], "edge")
        self.assertEqual(stand["digital_source_type"],
                         markierung.VOKABULAR + "trainedAlgorithmicMedia")

    def test_idempotent(self):
        datei = self.ordner / "probe.mp3"
        datei.write_bytes(markierung._mini_mp3())
        markierung.schreiben(datei, "trainedAlgorithmicMedia", system="edge")
        einmal = datei.read_bytes()
        self.assertEqual(markierung.schreiben(datei, "trainedAlgorithmicMedia",
                                             system="edge"), "unveraendert")
        self.assertEqual(datei.read_bytes(), einmal)

    def test_eigene_frames_werden_ersetzt_nicht_verdoppelt(self):
        """Ein zweiter Lauf darf keine zweite Wahrheit in die Datei legen.

        Ohne diese Probe blieb eine Sabotage unsichtbar: Wer beim Filtern der
        vorhandenen Frames die eigenen NICHT aussortiert, schreibt sie ein
        zweites Mal hinein. Das Tag „liest" sich dann noch richtig (die erste
        Fassung gewinnt), die Datei trägt aber zwei widersprechende
        Erzeugungsarten – und ein Fremdleser nimmt die letzte.
        """
        datei = self.ordner / "doppelt.mp3"
        datei.write_bytes(markierung._mini_mp3())
        markierung.schreiben(datei, "trainedAlgorithmicMedia", system="edge")
        # Eine ANDERE Erzeugungsart ist ein Widerspruch, keine Aktualisierung:
        # ohne `force` bleibt die Datei unangetastet (gleiche Regel wie beim
        # Bildkanal). Erst der bewusste Lauf ersetzt die Angabe.
        vorher = datei.read_bytes()
        self.assertEqual(markierung.schreiben(
            datei, "compositeWithTrainedAlgorithmicMedia", system="edge"), "blockiert")
        self.assertEqual(datei.read_bytes(), vorher)
        self.assertEqual(markierung.schreiben(
            datei, "compositeWithTrainedAlgorithmicMedia", system="edge", force=True),
            "ersetzt")
        roh = datei.read_bytes()
        # TXXX-Beschreibungen stehen UTF-16-kodiert im Frame (BOM + LE).
        # Wer hier `latin-1` zählt, zählt immer 0 – die Probe wäre blind
        # und würde die Sabotage durchwinken. Genau das passierte.
        def anzahl(name: str) -> int:
            return roh.count(name.encode("utf-16-le"))

        self.assertEqual(anzahl(markierung.FRAME_QUELLE), 1,
                         "DigitalSourceType steht mehrfach in der Datei")
        self.assertEqual(anzahl(markierung.FRAME_SYSTEM), 1,
                         "AISystemUsed steht mehrfach in der Datei")
        self.assertEqual(markierung.markierung_lesen(roh)["digital_source_type"],
                         markierung.VOKABULAR + "compositeWithTrainedAlgorithmicMedia")

    def test_fremde_herkunft_wird_nicht_ueberschrieben(self):
        """Dieselbe Regel wie beim Bild: erst prüfen, dann bewusst --force."""
        datei = self.ordner / "fremd.mp3"
        datei.write_bytes(markierung.tag_bauen(
            markierung._txxx(markierung.FRAME_QUELLE,
                             markierung.VOKABULAR + "compositeWithTrainedAlgorithmicMedia"))
            + markierung._mini_mp3())
        self.assertEqual(markierung.schreiben(datei, "trainedAlgorithmicMedia"), "blockiert")
        self.assertEqual(markierung.schreiben(datei, "trainedAlgorithmicMedia",
                                             force=True), "ersetzt")

    def test_entfernen_stellt_bytegleich_her(self):
        datei = self.ordner / "probe.mp3"
        original = markierung._mini_mp3()
        datei.write_bytes(original)
        markierung.schreiben(datei, "trainedAlgorithmicMedia", system="edge")
        self.assertEqual(markierung.entfernen(datei), "entfernt")
        self.assertEqual(datei.read_bytes(), original)

    def test_ohne_beleg_wird_nichts_behauptet(self):
        bestand = self.ordner / "articles"
        bestand.mkdir()
        (bestand / "spur.mp3").write_bytes(markierung._mini_mp3())
        getan, fehler = markierung.markieren(bestand)
        self.assertEqual(getan, [])
        self.assertTrue(any("kein Erzeugerbeleg" in f for f in fehler))
        # Die Datei ist unangetastet – eine Angabe ohne Beleg wäre erfunden.
        self.assertEqual((bestand / "spur.mp3").read_bytes(), markierung._mini_mp3())

    def test_belegte_spur_wird_markiert_und_gemeldet(self):
        bestand = self.ordner / "articles"
        bestand.mkdir()
        (bestand / "spur.mp3").write_bytes(markierung._mini_mp3())
        (bestand / "spur.track.json").write_text(
            json.dumps({"engine": "elevenlabs", "src": "/audio/articles/spur.mp3"}),
            encoding="utf-8")
        getan, fehler = markierung.markieren(bestand)
        self.assertEqual(fehler, [])
        self.assertEqual(len(getan), 1)
        befunde, funde = markierung.pruefen(bestand)
        self.assertEqual(funde, [])
        self.assertEqual(befunde[0]["system"], "elevenlabs")

    def test_widerspruechliche_engine_ist_ein_befund(self):
        bestand = self.ordner / "articles"
        bestand.mkdir()
        datei = bestand / "spur.mp3"
        datei.write_bytes(markierung._mini_mp3())
        markierung.schreiben(datei, "trainedAlgorithmicMedia", system="edge")
        (bestand / "spur.track.json").write_text(json.dumps({"engine": "elevenlabs"}),
                                                 encoding="utf-8")
        _, funde = markierung.pruefen(bestand)
        self.assertTrue(any("widersprüchlich" in f for f in funde), funde)

    def test_unsynchronisiertes_tag_wird_nicht_angefasst(self):
        datei = self.ordner / "unsync.mp3"
        datei.write_bytes(markierung.ID3_KOPF + b"\x03\x00"
                          + bytes([markierung.ID3_FLAG_UNSYNC])
                          + markierung._syncsafe(0) + markierung._mini_mp3())
        with self.assertRaises(markierung.WerkzeugFehler):
            markierung.schreiben(datei, "trainedAlgorithmicMedia")


@unittest.skipUnless(FFMPEG, "kein ffmpeg verfügbar – Encoder-Proben übersprungen")
class EncoderProbenTest(unittest.TestCase):
    """Was nur an einer ECHTEN Encoder-Datei auffällt."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ordner = Path(self.tmp.name)

    def _datei(self, format: str) -> tuple[Path, bytes]:
        datei = self.ordner / f"echt.{format}"
        self.assertTrue(_erzeuge(datei, format), "Encoder hat keine Datei erzeugt")
        return datei, datei.read_bytes()

    def test_mp3_tagt_ohne_die_audiodaten_zu_veraendern(self):
        datei, original = self._datei("mp3")
        markierung.schreiben(datei, "trainedAlgorithmicMedia", system="elevenlabs")
        neu = datei.read_bytes()
        self.assertEqual(_audiodaten(neu), _audiodaten(original))
        # Fremde Angabe des Encoders bleibt stehen (Befund: TSSE / Lavf).
        # Geprüft wird die NEUE Datei, nicht das Original: Ein `assertIn` über
        # beide wäre immer wahr und würde den Fehler genau dann übersehen,
        # wenn er passiert.
        self.assertIn(b"Lavf", neu, "Encoder-Kennung wurde beim Markieren geloescht")
        self.assertIn(b"TSSE", neu, "fremder Software-Frame wurde geloescht")
        self.assertTrue(markierung.markierung_lesen(neu)["markiert"])

    def test_ffmpeg_kopfzeile_bleibt_ihre_version(self):
        """ffmpeg schreibt ID3v2.4. Wer v2.3 daraus macht, kann nicht zurück."""
        datei, original = self._datei("mp3")
        version_vorher = markierung.id3_bereich(original)
        self.assertIsNotNone(version_vorher)
        markierung.schreiben(datei, "trainedAlgorithmicMedia", system="elevenlabs")
        self.assertEqual(markierung.id3_bereich(datei.read_bytes())[3], version_vorher[3])
        markierung.entfernen(datei)
        self.assertEqual(datei.read_bytes(), original, "nicht bytegleich zurück")

    def test_wav_haelt_chunk_reihenfolge_und_fremdes_info(self):
        datei, original = self._datei("wav")
        vorher = [k for k, _, _ in markierung._riff_chunks(original)]
        markierung.schreiben(datei, "trainedAlgorithmicMedia", system="elevenlabs")
        neu = datei.read_bytes()
        self.assertEqual(_audiodaten(neu), _audiodaten(original))
        # Die bestehenden Chunks bleiben in ihrer Reihenfolge; unser LIST hängt
        # hinten dran. Ein Umsortieren wäre eine Strukturänderung ohne Anlass.
        nachher = [k for k, _, _ in markierung._riff_chunks(neu)]
        self.assertEqual(nachher[:len(vorher)], vorher)
        self.assertIn(b"Lavf", neu, "Encoder-ISFT wurde geloescht")
        markierung.entfernen(datei)
        self.assertEqual(datei.read_bytes(), original)

    def test_mutagen_liest_dieselbe_angabe(self):
        """Der Beweis, dass nicht nur wir unsere eigene Schrift lesen."""
        try:
            import mutagen
        except ImportError:
            self.skipTest("mutagen nicht installiert")
        datei, _ = self._datei("mp3")
        markierung.schreiben(datei, "trainedAlgorithmicMedia", system="elevenlabs")
        tags = mutagen.File(str(datei)).tags
        self.assertEqual(str(tags["TXXX:" + markierung.FRAME_QUELLE].text[0]),
                         markierung.VOKABULAR + "trainedAlgorithmicMedia")
        self.assertEqual(str(tags["TXXX:" + markierung.FRAME_SYSTEM].text[0]), "elevenlabs")


class GateVertragTest(unittest.TestCase):
    """Der Kanal hängt am Gate – sonst ist er eine Absicht, keine Wache."""

    def test_provenienz_gate_prueft_den_tonkanal(self):
        quelle = (ROOT / "scripts" / "ki_provenienz_gate.py").read_text(encoding="utf-8")
        self.assertIn("ki_audio_markierung", quelle,
                      "M3 prüft die Tonspur nicht – der Kanal wäre ungesichert")
        self.assertIn('"audio" / "articles"', quelle,
                      "M3 misst nicht das ausgelieferte Bauprodukt")

    def test_generator_markiert_die_spur_selbst(self):
        """Die Markierung darf nicht von einem zweiten Befehl abhängen."""
        quelle = (ROOT / "scripts" / "ff_voice_audio.py").read_text(encoding="utf-8")
        self.assertIn("setze_tonmarkierung", quelle)
        self.assertIn("ki_audio_markierung", quelle)

    def test_das_register_der_erzeugungsart_bleibt_ein_wahrheitsort(self):
        """Ton und Bild teilen Vokabular und Werteliste-Konvention."""
        from scripts import ki_bild_markierung as bild
        self.assertEqual(markierung.VOKABULAR, bild.VOKABULAR)
        self.assertTrue(set(markierung.ERLAUBTE_TYPEN) <= set(bild.ERLAUBTE_TYPEN),
                        "Ton nutzt einen Wert, den der Bildkanal nicht kennt")


if __name__ == "__main__":
    unittest.main()
