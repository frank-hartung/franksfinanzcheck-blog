"""Regressionen für den temporären Ausschluss des Google-Verification-HTMLs."""
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase

from scripts.pagefind_build import build


class PagefindBuildTests(TestCase):
    def test_verifikationsdatei_bleibt_bytegleich_und_wird_nicht_indexiert(self):
        with TemporaryDirectory() as folder:
            site = Path(folder)
            verification = site / "google-verify.html"
            payload = b"google-site-verification: google-verify.html\n"
            verification.write_bytes(payload)
            (site / "index.html").write_text("<html>site</html>", encoding="utf-8")
            observed = []

            def fake_run(command, check):
                observed.append((command, verification.exists()))
                return SimpleNamespace(returncode=0)

            self.assertEqual(0, build(site, "pagefind-test-double", fake_run))
            self.assertFalse(observed[0][1])
            self.assertEqual(payload, verification.read_bytes())

    def test_verifikationsdatei_wird_auch_bei_pagefind_fehler_wiederhergestellt(self):
        with TemporaryDirectory() as folder:
            site = Path(folder)
            verification = site / "google-token.html"
            payload = b"google-site-verification: google-token.html\n"
            verification.write_bytes(payload)

            def failed_run(command, check):
                self.assertFalse(verification.exists())
                return SimpleNamespace(returncode=7)

            self.assertEqual(7, build(site, "pagefind-test-double", failed_run))
            self.assertEqual(payload, verification.read_bytes())
