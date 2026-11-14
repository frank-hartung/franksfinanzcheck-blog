#!/usr/bin/env python3
"""#1028 / Deploy-Siegel: `--check` und `--gate` sind derselbe Schalter.

Befund 14.11.2026 (Lauf 43618889770): `.github/workflows/deploy.yml` rief
`python3 scripts/ki_audio_markierung.py --check`. Das Werkzeug kannte nur
`--gate`; `argparse` beendet unbekannte Schalter mit Exit 2. Der Schritt
meldete „write=0 / check=2“, `werkzeugbefund.py` machte daraus einen Befund
(C38) – und das Auslieferungs-Siegel war an JEDEM Deploy rot, obwohl der
Gegenlauf am echten Bestand 44 von 44 Tonspuren markiert fand (0 Befunde).

Der Test hält beide Namen am echten CLI fest: gleicher Exit-Code, gleiche
Wirkung, kein Schreiben im Prüfmodus.
"""
from __future__ import annotations

import contextlib
import io
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import ki_audio_markierung as kim  # noqa: E402


def _mp3() -> bytes:
    return kim._mini_mp3()


def _markiert() -> bytes:
    """Eine Datei, die ihre Herkunft bereits trägt (MP3 + eigener ID3-Block)."""
    return kim.tag_bauen(kim.eigene_frames(kim.ERLAUBTE_TYPEN[0], system="edge")) + _mp3()


class SchalterAlias(unittest.TestCase):
    def _lauf(self, *argv: str) -> tuple[int, str]:
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            code = kim.main(list(argv))
        return code, puffer.getvalue()

    def test_check_und_gate_teilen_denselben_schalter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            (ordner / "a.mp3").write_bytes(_markiert())
            (ordner / "a.track.json").write_text('{"engine": "edge"}', encoding="utf-8")

            code_gate, text_gate = self._lauf("--gate", "--dir", tmp)
            code_check, text_check = self._lauf("--check", "--dir", tmp)

        self.assertEqual(code_gate, 0, text_gate)
        self.assertEqual(code_check, 0, text_check)
        self.assertEqual(code_gate, code_check)

    def test_unmarkierte_spur_ist_bei_beiden_namen_rot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            (ordner / "b.mp3").write_bytes(_mp3())
            (ordner / "b.track.json").write_text('{"engine": "edge"}', encoding="utf-8")

            code_gate, _ = self._lauf("--gate", "--dir", tmp)
            code_check, text_check = self._lauf("--check", "--dir", tmp)

        self.assertEqual(code_gate, 1)
        self.assertEqual(code_check, 1)
        self.assertIn("keine Markierung im Container", text_check)

    def test_pruefmodus_schreibt_nichts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            ordner = Path(tmp)
            datei = ordner / "c.mp3"
            roh = _mp3()
            datei.write_bytes(roh)
            (ordner / "c.track.json").write_text('{"engine": "edge"}', encoding="utf-8")

            self._lauf("--check", "--dir", tmp)
            self.assertEqual(datei.read_bytes(), roh,
                             "der Prüfmodus hat die Datei verändert (C15)")

            self._lauf("--write", "--dir", tmp)
            self.assertTrue(kim.markierung_lesen(datei.read_bytes())["markiert"])

    def test_unbekannter_schalter_bleibt_ein_fehler(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(SystemExit) as ctx:
                with contextlib.redirect_stderr(io.StringIO()):
                    kim.main(["--gibtesnicht", "--dir", tmp])
        self.assertEqual(ctx.exception.code, 2)


class WorkflowNenntDenSchalter(unittest.TestCase):
    """Der Deploy-Pfad und das Werkzeug müssen denselben Namen benutzen."""

    def test_deploy_ruft_einen_bekannten_schalter(self) -> None:
        text = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        zeilen = [z for z in text.splitlines()
                  if "ki_audio_markierung.py --write" in z
                  or "ki_audio_markierung.py --gate" in z
                  or "ki_audio_markierung.py --check" in z]
        self.assertGreaterEqual(len(zeilen), 2, "write/Prüf-Aufruf fehlt im Deploy")
        for zeile in zeilen:
            schalter = zeile.split("ki_audio_markierung.py", 1)[1].split()[0]
            self.assertIn(schalter, {"--write", "--gate", "--check"},
                          f"unbekannter Schalter im Deploy: {schalter}")


if __name__ == "__main__":
    unittest.main()
