#!/usr/bin/env python3
"""test_whisper_engine.py — Unit-Tests für die lokale Whisper-Engine.

Enthält seit dem 04.10.2026 die Regressionswache für Meldung #559
(Code-Scanning-Alert 60 „Uncontrolled command line“): Externe Audio-Pfade,
Modell- und Sprachwerte dürfen eine Prozesszeile niemals ungeprüft erreichen.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import whisper_engine


class TestWhisperEngine(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="test_whisper_")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_clean_transcript_text(self) -> None:
        raw = "Äh, wir haben also quasi 300 Euro gespart, weißt du?"
        cleaned = whisper_engine.clean_transcript_text(raw)
        self.assertNotIn("äh", cleaned.lower())
        self.assertNotIn("quasi", cleaned.lower())
        self.assertNotIn("weißt du", cleaned.lower())
        self.assertIn("300 Euro", cleaned)

    def test_mock_backend_transcription(self) -> None:
        engine = whisper_engine.WhisperEngine(backend="mock")
        res = engine.transcribe("sample.mp3")
        self.assertIn("text", res)
        self.assertIn("cleaned_text", res)
        self.assertEqual(res["backend_used"], "mock")
        self.assertGreater(len(res["segments"]), 0)

    def test_transform_voice_to_article(self) -> None:
        sample_transcript = {
            "text": "In dieser Folge prüfen wir die besten Stromtarife für den Winter.",
            "cleaned_text": "In dieser Folge prüfen wir die besten Stromtarife für den Winter.",
        }
        art = whisper_engine.transform_voice_to_article(
            sample_transcript,
            kategorie="strom-gas",
            custom_title="Stromtarife im Winter prüfen",
            audio_filename="aufnahme1.mp3",
        )
        self.assertEqual(art["title"], "Stromtarife im Winter prüfen")
        self.assertEqual(art["kategorie"], "strom-gas")
        self.assertIn("4K-Prüfpfad", art["markdown"])
        self.assertIn("whisper_audio_source: \"aufnahme1.mp3\"", art["markdown"])
        self.assertGreaterEqual(art["reading_time"], 1)

    def test_vtt_and_srt_export(self) -> None:
        engine = whisper_engine.WhisperEngine(backend="mock")
        res = engine.transcribe("sample.mp3")

        vtt_file = os.path.join(self.tmp_dir, "test.vtt")
        srt_file = os.path.join(self.tmp_dir, "test.srt")

        whisper_engine.export_vtt(res, vtt_file)
        whisper_engine.export_srt(res, srt_file)

        self.assertTrue(os.path.exists(vtt_file))
        self.assertTrue(os.path.exists(srt_file))

        with open(vtt_file, encoding="utf-8") as fh:
            vtt_content = fh.read()
        self.assertTrue(vtt_content.startswith("WEBVTT"))

    def test_audio_parity_qa(self) -> None:
        engine = whisper_engine.WhisperEngine(backend="mock")
        art_path = os.path.join(self.tmp_dir, "article.md")
        with open(art_path, "w", encoding="utf-8") as fh:
            fh.write(
                "---\ntitle: 'Strompreise 2026'\n---\n"
                "Hallo und herzlich willkommen zu Franks Finanzcheck. "
                "In dieser Aufnahme sprechen wir über die Strompreisentwicklung 2026 "
                "und wie Privathaushalte mit dem 4K-Prüfpfad sofort 350 Euro im Jahr sparen können. "
                "Erstens Kosten sehen, zweitens Konditionen rechnen, drittens Kündigungsfenster sichern "
                "und viertens Kurs halten. Vergleicht immer die Grundgebühr und den Arbeitspreis."
            )

        qa = whisper_engine.verify_audio_parity("sample.mp3", art_path, engine=engine, min_similarity=0.65)
        self.assertTrue(qa["passed"])
        self.assertGreaterEqual(qa["similarity_score"], 0.65)


class TestSprachNormalisierung(unittest.TestCase):
    """Whitelist-Abbildung der Sprachwerte (Meldung #559)."""

    def test_whitelist_und_aliasse(self) -> None:
        fälle = {
            "de": "de", " DE ": "de", "deutsch": "de", "german": "de",
            "en": "en", "englisch": "en", "auto": "auto", "fr": "fr",
            "de-DE": "de", "en-US": "en", "zh": "zh", "yue": "yue",
        }
        for roh, erwartet in fälle.items():
            self.assertEqual(whisper_engine._normalize_language(roh), erwartet, roh)

    def test_unbekannte_sprache_faellt_auf_auto(self) -> None:
        self.assertEqual(whisper_engine._normalize_language("klingonisch"), "auto")
        self.assertEqual(whisper_engine._normalize_language(None), "auto")
        self.assertEqual(whisper_engine._normalize_language(""), "auto")


class TestEingangsWacht(unittest.TestCase):
    """Pfadkanonisierung und -prüfung vor jeder Backend-Weitergabe (Meldung #559)."""

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="test_whisper_wache_")
        self.memo = os.path.join(self.tmp_dir, "memo.mp3")
        with open(self.memo, "wb") as fh:
            fh.write(b"RIFF")
        self.mock_engine = whisper_engine.WhisperEngine(backend="mock")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_pfad_wird_zu_absolutem_kanon_aufgeloest(self) -> None:
        verschleiert = os.path.join(self.tmp_dir, "unter", "..", "memo.mp3")
        self.assertEqual(
            self.mock_engine._safe_audio_path(verschleiert),
            os.path.realpath(self.memo),
        )

    def test_fuehrender_bindestrich_wird_abgelehnt(self) -> None:
        angreifer = os.path.join(self.tmp_dir, "-angriff.mp3")
        with open(angreifer, "wb") as fh:
            fh.write(b"RIFF")
        with self.assertRaises(ValueError):
            self.mock_engine._safe_audio_path(angreifer)

    def test_nul_zeichen_und_leere_pfade_werden_abgelehnt(self) -> None:
        for feindselig in ("memo.mp3\x00.txt", "", "   "):
            with self.assertRaises(ValueError):
                self.mock_engine._safe_audio_path(feindselig)

    def test_fehlende_datei_nur_fuer_echte_backends_fatal(self) -> None:
        cpp_engine = whisper_engine.WhisperEngine(backend="whisper.cpp")
        with self.assertRaises(FileNotFoundError):
            cpp_engine._safe_audio_path("gibt_es_nicht.mp3")
        # Mock-Basis bleibt für hermetische Tests offen:
        self.assertTrue(os.path.isabs(self.mock_engine._safe_audio_path("gibt_es_nicht.mp3")))

    def test_transcribe_reicht_nur_den_kanon_weiter(self) -> None:
        res = self.mock_engine.transcribe(self.memo)
        self.assertEqual(res["file_path"], os.path.realpath(self.memo))


class TestWhisperCppProzessvertrag(unittest.TestCase):
    """Prozesszeilen-Vertrag des whisper.cpp-Backends (Meldung #559).

    Die Audiodatei wird ausschließlich als geöffneter Datei-Deskriptor
    übergeben; Modell- und Sprachwerte stammen aus Whitelists; fehlende
    Binary, Modell oder JSON-Antwort führen zum fail-closed Abbruch.
    """

    def setUp(self) -> None:
        self.tmp_dir = tempfile.mkdtemp(prefix="test_whisper_cpp_")
        self.audio = os.path.join(self.tmp_dir, "memo.mp3")
        with open(self.audio, "wb") as fh:
            fh.write(b"RIFF")
        self.engine = whisper_engine.WhisperEngine(backend="whisper.cpp", model="base", language="de")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def _fake_blog_dir(self) -> str:
        fake_blog = tempfile.mkdtemp(prefix="test_whisper_cpp_blog_")
        os.makedirs(os.path.join(fake_blog, "models"), exist_ok=True)
        with open(os.path.join(fake_blog, "models", "ggml-base.bin"), "wb") as fh:
            fh.write(b"")
        return fake_blog

    def _fake_run_erfolg(self, argv, **kwargs):
        out_base = argv[argv.index("-of") + 1]
        with open(f"{out_base}.json", "w", encoding="utf-8") as fh:
            json_daten = {
                "result": "Hallo Franks Finanzcheck",
                "transcription": [{"text": "Hallo"}, {"text": "Franks Finanzcheck"}],
            }
            json.dump(json_daten, fh)
        return subprocess.CompletedProcess(argv, 0, "", "")

    def test_fehlendes_binary_fail_closed(self) -> None:
        with mock.patch.object(whisper_engine.shutil, "which", return_value=None), \
             mock.patch.object(whisper_engine.subprocess, "run") as runner:
            with self.assertRaises(RuntimeError):
                self.engine._transcribe_whisper_cpp(self.audio, "de")
        runner.assert_not_called()

    def test_modellname_muss_auf_der_whitelist_stehen(self) -> None:
        for feindselig in ("../angriff", "base; rm -rf /", "base-x", "-oj"):
            engine = whisper_engine.WhisperEngine(backend="whisper.cpp", model=feindselig)
            with mock.patch.object(whisper_engine.shutil, "which", return_value="/usr/bin/whisper-cpp"), \
                 mock.patch.object(whisper_engine.subprocess, "run") as runner:
                with self.assertRaises(ValueError):
                    engine._transcribe_whisper_cpp(self.audio, "de")
            runner.assert_not_called()

    def test_prozesszeile_enthaelt_nur_gepruefte_werte(self) -> None:
        fake_blog = self._fake_blog_dir()
        try:
            with mock.patch.object(whisper_engine.shutil, "which", return_value="/usr/bin/whisper-cpp"), \
                 mock.patch.object(whisper_engine.subprocess, "run", side_effect=self._fake_run_erfolg) as runner, \
                 mock.patch.object(whisper_engine, "BLOG_DIR", fake_blog):
                res = self.engine.transcribe(self.audio)
        finally:
            shutil.rmtree(fake_blog, ignore_errors=True)

        argv = runner.call_args.args[0]
        kwargs = runner.call_args.kwargs
        self.assertEqual(argv[0], "/usr/bin/whisper-cpp")
        self.assertEqual(argv[argv.index("-m") + 1], os.path.join(fake_blog, "models", "ggml-base.bin"))
        datei_arg = argv[argv.index("-f") + 1]
        self.assertRegex(datei_arg, r"^/(proc/self|dev)/fd/\d+$")
        self.assertNotIn(self.audio, argv)
        self.assertNotIn(os.path.realpath(self.audio), argv)
        self.assertEqual(argv[argv.index("-l") + 1], "de")
        self.assertIn("-oj", argv)
        # „--“ versteht der whisper.cpp-Parser nicht und würde ihn abbrechen:
        self.assertNotIn("--", argv)
        # Deskriptor-Übergabe statt Pfad-Übergabe:
        self.assertIs(kwargs.get("shell", False), False)
        pass_fds = kwargs.get("pass_fds", ())
        self.assertEqual(len(pass_fds), 1)
        self.assertIsInstance(pass_fds[0], int)
        # Segmenttexte werden vollständig verbunden:
        self.assertEqual(res["text"], "Hallo Franks Finanzcheck")
        self.assertEqual(res["language"], "de")
        self.assertEqual(res["file_path"], os.path.realpath(self.audio))

    def test_fehlercode_fail_closed(self) -> None:
        fake_blog = self._fake_blog_dir()
        try:
            with mock.patch.object(whisper_engine.shutil, "which", return_value="/usr/bin/whisper-cpp"), \
                 mock.patch.object(whisper_engine, "BLOG_DIR", fake_blog), \
                 mock.patch.object(whisper_engine.subprocess, "run",
                                   return_value=subprocess.CompletedProcess([], 1, "", "boom")):
                with self.assertRaisesRegex(RuntimeError, "Fehlercode 1"):
                    self.engine._transcribe_whisper_cpp(self.audio, "de")
        finally:
            shutil.rmtree(fake_blog, ignore_errors=True)

    def test_fehlendes_json_fail_closed(self) -> None:
        def _leerer_lauf(argv, **kwargs):
            return subprocess.CompletedProcess(argv, 0, "", "")
        fake_blog = self._fake_blog_dir()
        try:
            with mock.patch.object(whisper_engine.shutil, "which", return_value="/usr/bin/whisper-cpp"), \
                 mock.patch.object(whisper_engine, "BLOG_DIR", fake_blog), \
                 mock.patch.object(whisper_engine.subprocess, "run", side_effect=_leerer_lauf):
                with self.assertRaisesRegex(RuntimeError, "kein JSON-Transkript"):
                    self.engine._transcribe_whisper_cpp(self.audio, "de")
        finally:
            shutil.rmtree(fake_blog, ignore_errors=True)

    def test_feindselige_eingaben_starten_keinen_prozess(self) -> None:
        with mock.patch.object(whisper_engine.subprocess, "run") as runner:
            for feindselig in ("-angriff.mp3", "memo.mp3\x00", "gibt_es_nicht.mp3"):
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.engine.transcribe(feindselig)
        runner.assert_not_called()


class TestInboxFehlerisolation(unittest.TestCase):
    """Eine abgelehnte Aufnahme darf die Inbox-Verarbeitung nicht blockieren."""

    def test_feindselige_datei_wird_uebersprungen(self) -> None:
        inbox = tempfile.mkdtemp(prefix="test_whisper_inbox_")
        ziel = tempfile.mkdtemp(prefix="test_whisper_drafts_")
        try:
            for name in ("gut.mp3", "-boese.mp3"):
                with open(os.path.join(inbox, name), "wb") as fh:
                    fh.write(b"RIFF")
            engine = whisper_engine.WhisperEngine(backend="mock")
            results = whisper_engine.process_inbox_directory(inbox_dir=inbox, target_dir=ziel, engine=engine)

            self.assertEqual(len(results), 1)
            self.assertEqual(results[0]["source_audio"], "gut.mp3")
            self.assertTrue(os.path.exists(os.path.join(inbox, "archive", "gut.mp3")))
            # Die abgelehnte Aufnahme bleibt zur manuellen Prüfung liegen:
            self.assertTrue(os.path.exists(os.path.join(inbox, "-boese.mp3")))
        finally:
            shutil.rmtree(inbox, ignore_errors=True)
            shutil.rmtree(ziel, ignore_errors=True)


class TestQuelldateiHaertung(unittest.TestCase):
    """Externe Dateinamen dürfen Frontmatter und Markdown nicht brechen."""

    def test_dateiname_wird_vor_dem_frontmatter_gehaertet(self) -> None:
        transcript = {
            "text": "Strompreise prüfen und vergleichen.",
            "cleaned_text": "Strompreise prüfen und vergleichen.",
        }
        art = whisper_engine.transform_voice_to_article(
            transcript,
            kategorie="strom-gas",
            audio_filename='boese" name\nx.mp3',
        )
        quelle = re.search(r'^whisper_audio_source: "(.*)"$', art["markdown"], re.MULTILINE)
        self.assertIsNotNone(quelle)
        self.assertRegex(quelle.group(1), r"^[A-Za-z0-9._ -]*$")
        self.assertNotIn('"', quelle.group(1))
        self.assertNotIn("\n", quelle.group(1))


if __name__ == "__main__":
    unittest.main()
