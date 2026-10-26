"""Jeder Download-Link im Inhalt muss eine echte Datei sein.

Anlass (26.10.2026): Die Studienseite versprach seit dem 02.10.2026 ein
PDF unter `/downloads/…`, die Datei existierte nie. Gefunden hat das erst das
Layout-Audit – nach Wochen, in denen der Link ein 404 war. Ein Link im
Fließtext ist kein Artefakt; dieser Test zieht die Grenze vor dem Push.

Geprüft werden ausschließlich ZIELE unter `/downloads/`; externe Links und
Seiten-URLs sind nicht Gegenstand dieses Vertrags.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DOWNLOAD_LINK = re.compile(r"\]\((/downloads/[^)#?\s]+)")


def _content_dateien():
    return sorted((ROOT / "content").rglob("*.md"))


class DownloadLinkVertrag(unittest.TestCase):
    def test_jeder_download_link_hat_eine_datei(self):
        fehlend = []
        for pfad in _content_dateien():
            text = pfad.read_text(encoding="utf-8")
            for ziel in DOWNLOAD_LINK.findall(text):
                datei = ROOT / "static" / ziel.lstrip("/")
                if not datei.is_file():
                    fehlend.append(f"{pfad.relative_to(ROOT)} → {ziel}")
        self.assertEqual(fehlend, [], "Download-Link ohne Datei:\n" + "\n".join(fehlend))

    def test_studie_verlinkt_ihr_pdf_und_der_bauer_existiert(self):
        seite = (ROOT / "content/studien/fixkosten-index-2026-q4/index.md").read_text(encoding="utf-8")
        self.assertIn("/downloads/fixkosten-index-2026-q4.pdf", seite)
        self.assertIn("studie_pdf.py", seite,
                      "Die Seite muss ihren Erzeuger nennen – sonst ist die Datei nicht reproduzierbar")
        pdf = ROOT / "static/downloads/fixkosten-index-2026-q4.pdf"
        self.assertTrue(pdf.is_file())
        self.assertEqual(b"%PDF", pdf.read_bytes()[:4], "Datei ist kein PDF")
        self.assertGreater(pdf.stat().st_size, 1000, "PDF ist leer/kaputt")


if __name__ == "__main__":
    unittest.main()
