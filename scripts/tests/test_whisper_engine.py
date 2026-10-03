#!/usr/bin/env python3
"""test_whisper_engine.py — Unit-Tests für die lokale Whisper-Engine."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
import unittest

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


if __name__ == "__main__":
    unittest.main()
