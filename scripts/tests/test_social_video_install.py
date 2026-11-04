#!/usr/bin/env python3
# ============================================================
#  SHORTS-SCHMIEDE (#1049): Kein pip-Aufruf darf hash-gesperrte
#  und hash-lose Manifeste mischen.
#  ------------------------------------------------------------
#  requirements-ci.txt trägt --hash-Zeilen; pip schaltet damit
#  den Hash-Modus für den gesamten Aufruf scharf und verweigert
#  jeden Pin ohne Hash (bewiesener Fehler: „Hashes are required
#  … missing from edge-tts==7.3.1“). Der Shorts-Lauf vom
#  03.11.2026 starb genau daran – die Installation konnte seit
#  der Manifest-Pinnung (WF-E813) nie gelingen. Dieser Test
#  liest alle Workflows und verbietet die Bauart generell:
#  getrennte Aufrufe je Manifest (Vorbild deploy.yml), und ein
#  Aufruf mit requirements-ci.txt trägt immer --require-hashes.
# ============================================================
import glob
import os
import re
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..", "..")


def _hat_hashes(manifest_pfad: str) -> bool:
    try:
        with open(manifest_pfad, encoding="utf-8") as fh:
            return "--hash=" in fh.read()
    except OSError:
        return False


def _pip_aufrufe(text: str):
    """Alle pip-install-Aufrufe eines Workflow-Texts (logische Zeilen)."""
    logisch = re.sub(r"\\\n\s*", " ", text)
    for zeile in logisch.splitlines():
        if "pip install" in zeile or "pip3 install" in zeile:
            yield zeile


class ManifestMischungTest(unittest.TestCase):
    def test_kein_aufruf_mischt_hash_und_hashlos(self):
        verstoss = []
        for pfad in sorted(glob.glob(os.path.join(
                ROOT, ".github", "workflows", "*.yml"))):
            with open(pfad, encoding="utf-8") as fh:
                text = fh.read()
            for zeile in _pip_aufrufe(text):
                manifeste = re.findall(r"-r\s+(\S*requirements[^\s\"']*\.txt)", zeile)
                if len(manifeste) < 2:
                    continue
                zustand = {_hat_hashes(os.path.join(ROOT, m)) for m in manifeste}
                if len(zustand) > 1:
                    verstoss.append(f"{os.path.basename(pfad)}: {zeile.strip()[:120]}")
        self.assertEqual([], verstoss,
                         "pip-Aufruf mischt hash-gesperrte und hash-lose "
                         "Manifeste – Hash-Modus frisst den Aufruf (#1049)")

    def test_ci_manifest_immer_mit_require_hashes(self):
        fehlend = []
        for pfad in sorted(glob.glob(os.path.join(
                ROOT, ".github", "workflows", "*.yml"))):
            with open(pfad, encoding="utf-8") as fh:
                text = fh.read()
            for zeile in _pip_aufrufe(text):
                if "requirements-ci.txt" in zeile and "--require-hashes" not in zeile:
                    # `|| true`-Legacy-Zeilen und Kommentar-Beispiele sind
                    # keine Installation dieses Manifests im Ernstpfad;
                    # gezählt wird nur ein Aufruf ohne Hash-Zwang.
                    fehlend.append(f"{os.path.basename(pfad)}: {zeile.strip()[:120]}")
        self.assertEqual([], fehlend,
                         "requirements-ci.txt ohne --require-hashes installiert")

    def test_shorts_installiert_getrennt(self):
        with open(os.path.join(ROOT, ".github", "workflows",
                               "social-video.yml"), encoding="utf-8") as fh:
            text = fh.read()
        self.assertIn("--require-hashes -r requirements-ci.txt", text)
        self.assertIn("-r requirements-tts.txt", text)
        self.assertNotIn("-r requirements-ci.txt -r requirements-tts.txt", text)


if __name__ == "__main__":
    unittest.main()
