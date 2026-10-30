#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regression: Kein grünes Ergebnis ohne Messung (Meldung #900).

DER VORFALL (26.10.2026)
------------------------
Der Lauf 40336062251 meldete „Statisches Audit: Exit 1 · Browser-Audit: Exit 1"
und im Browser-Teil:

    404 http://127.0.0.1:8099/ · kein <title> · kein <h1>

Das sah nach kaputtem Layout aus, war aber ein abgebrochener Bau: In
`public/` lagen nur Bruchstücke. Zwei Prüfungen hatten dafür keinen Begriff:

1. `layout_audit.py` lief über 0 Seiten und meldete „0 Links kaputt, alle OK"
   – ein **grünes** Ergebnis ohne Messung (`main()` prüfte nur, ob das
   VERZEICHNIS existiert).
2. `layout_browser_check.js` lud die 404-Seite und zählte „kein <title>,
   kein <h1>" als Layout-Befund – obwohl der Fehler im Bau lag. Ein leerer Bau
   und ein fehlender Browser teilten sich außerdem denselben Exit-Code 2
   („weich übersprungen", im Workflow grün).

Diese Tests halten die Reparatur fest – am Verhalten, nicht an Worten:

* `pruefe_baubasis()` und `main()`: leerer, abgebrochener und fehlender Bau
  sind ROT, mit Klartext-Grund und Zahlen; ein vollständiger Bau ist messbar.
* Der Browser-Audit ist ohne messbaren Bau ein **Werkzeugfehler (Exit 3)**,
  kein Befund (1) und keine weiche Überspringung (2).
* Der Alt-Text-Parser liest den MINIFIZIERTEN Bau: `alt=""` kommt dort als
  bloßes `alt` an. Das ist ein leerer Alt-Text (dekorativ erlaubt), kein
  fehlender – der Fehlalarm über 77 Kartenbilder war genau dieser Unterschied.
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import layout_audit as la  # noqa: E402

PAGE = ('<!DOCTYPE html><html lang="de"><head><meta charset="utf-8">'
        '<title>Seite</title>'
        '<link rel="canonical" href="https://example.org/x/">'
        '<link rel="alternate" hreflang="de" href="https://example.org/x/">'
        '</head><body><article><h1>Seite</h1><p>ok</p></article></body></html>')


class _Basis(unittest.TestCase):
    """Gemeinsames Gerüst: eigener Bau-Baum, eigener Report-Pfad."""

    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.base = self.tmp / "public"
        self.base.mkdir(parents=True)
        self._alt = (la.BASE, la.ROOT, la.REPORT)
        la.BASE = str(self.base)
        la.ROOT = str(self.tmp)
        la.REPORT = str(self.tmp / "LAYOUT-REPORT.md")
        self.addCleanup(self._restore)
        for bucket in (la.CRITICAL, la.WARN, la.OK):
            bucket.clear()

    def _restore(self) -> None:
        la.BASE, la.ROOT, la.REPORT = self._alt
        # Kein Befund darf in einen anderen Test durchbluten.
        for bucket in (la.CRITICAL, la.WARN, la.OK):
            bucket.clear()

    def seite(self, rel: str, text: str = PAGE) -> None:
        pfad = self.base / rel
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(text, encoding="utf-8")

    def vollbau(self) -> None:
        """Ein Bau, der die Mindestgrenzen erfüllt (ohne echte Inhalte)."""
        self.seite("index.html")
        for i in range(la.MIN_SEITEN):
            self.seite(f"seite-{i:02d}/index.html")
        self.seite("posts/artikel/index.html")


class BaubasisTests(_Basis):
    def test_leerer_bau_ist_nicht_messbar(self) -> None:
        probleme, seiten, artikel = la.pruefe_baubasis()
        self.assertTrue(probleme, "Ein leerer Bau muss Befunde liefern")
        self.assertEqual((seiten, artikel), (0, 0))
        text = " ".join(probleme)
        self.assertIn("index.html", text)
        self.assertIn(f"Mindestumfang für eine Messung: {la.MIN_SEITEN}", text)

    def test_teilbau_unter_mindestumfang_ist_rot(self) -> None:
        # Der Zustand vom 26.10.: ein paar Seiten, aber kein vollständiger Bau.
        self.seite("index.html")
        for i in range(3):
            self.seite(f"posts/kaputt-{i}/index.html")
        probleme, seiten, artikel = la.pruefe_baubasis()
        self.assertEqual(4, seiten)
        self.assertEqual(3, artikel)
        self.assertTrue(any("HTML-Seiten" in p for p in probleme), probleme)

    def test_vollbau_ist_messbar(self) -> None:
        self.vollbau()
        probleme, seiten, artikel = la.pruefe_baubasis()
        self.assertEqual([], probleme)
        self.assertGreaterEqual(seiten, la.MIN_SEITEN)
        self.assertGreaterEqual(artikel, la.MIN_ARTIKEL)

    def test_leerer_bau_macht_den_lauf_rot_und_schreibt_einen_report(self) -> None:
        # Vor der Reparatur: Exit 0 mit „alles OK" über 0 Seiten.
        self.assertEqual(1, la.main())
        report = Path(la.REPORT).read_text(encoding="utf-8")
        self.assertIn("Messbarkeit", report)
        self.assertIn("NICHTS belastbar geprüft", report)
        self.assertIn("kein grünes Ergebnis", report)
        self.assertFalse(any(line.startswith("Interne Links")
                             for line in la.OK),
                         "Ohne Bau darf keine Einzelprüfung OK melden")

    def test_fehlendes_verzeichnis_ist_rot_und_wird_berichtet(self) -> None:
        shutil.rmtree(self.base)
        self.assertEqual(1, la.main())
        report = Path(la.REPORT).read_text(encoding="utf-8")
        self.assertIn("existiert nicht", report)

    def test_report_nennt_die_gefundenen_zahlen(self) -> None:
        self.seite("index.html")
        la.main()
        report = Path(la.REPORT).read_text(encoding="utf-8")
        self.assertIn("1 HTML-Seiten und 0 Artikel", report)


class MinifizierteAttributeTests(_Basis):
    """Hugo --minify schreibt `alt=""` als `alt` – der Parser muss das lesen."""

    def test_tag_attributes_unterscheidet_leer_von_fehlt(self) -> None:
        attrs = la.tag_attributes(
            '<img loading=lazy src=/x.jpg alt aria-hidden=true>')
        self.assertIn("alt", attrs, "Ein namenloses Attribut ist NICHT fehlend")
        self.assertIsNone(attrs["alt"], "… sondern hat den leeren Wert")
        self.assertEqual("lazy", attrs["loading"])
        self.assertEqual("/x.jpg", attrs["src"])
        self.assertEqual("true", attrs["aria-hidden"])
        self.assertNotIn("data-ff-fcp-image", attrs)

        ohne = la.tag_attributes('<img src=/x.jpg class=deko>')
        self.assertNotIn("alt", ohne)

    def test_minifiziertes_leeres_alt_ist_dekorativ(self) -> None:
        # Exakt der gerenderte Stand aus _partials/extend_post_content.html.
        self.seite("posts/a/index.html", PAGE.replace(
            "<p>ok</p>",
            '<p>ok</p><img loading=lazy decoding=async '
            'data-ff-fcp-image=deferred src=/images/covers/360/x.jpg '
            'alt aria-hidden=true width=360 height=540 class=ff-related-card__img>'))
        la.check_alts()
        self.assertEqual([], la.WARN, f"Fehlalarm aus #900 ist zurück: {la.WARN}")
        self.assertTrue(any("0 ohne Alt-Text" in line for line in la.OK))

    def test_leeres_alt_mit_role_presentation_ist_dekorativ(self) -> None:
        self.seite("posts/a/index.html", PAGE.replace(
            "<p>ok</p>", '<p>ok</p><img src=/x.png alt role=presentation>'))
        la.check_alts()
        self.assertEqual([], la.WARN)

    def test_leeres_alt_ohne_dekorativ_marker_bleibt_befund(self) -> None:
        self.seite("posts/a/index.html", PAGE.replace(
            "<p>ok</p>", '<p>ok</p><img src=/x.png alt>'))
        la.check_alts()
        self.assertTrue(any("leeres alt" in line for line in la.WARN), la.WARN)

    def test_fehlendes_alt_bleibt_harter_hinweis(self) -> None:
        self.seite("posts/a/index.html", PAGE.replace(
            "<p>ok</p>", '<p>ok</p><img src=/x.png>'))
        la.check_alts()
        self.assertTrue(any("ohne alt-Attribut" in line for line in la.WARN), la.WARN)

    def test_generischer_alt_text_wird_weiter_erkannt(self) -> None:
        self.seite("posts/a/index.html", PAGE.replace(
            "<p>ok</p>", '<p>ok</p><img src=/images/covers/hero.jpg alt="hero-1200">'))
        la.check_alts()
        self.assertTrue(any("generischer Alt-Text" in line for line in la.WARN))


@unittest.skipUnless(shutil.which("node"), "node fehlt – Browser-Vertrag nicht prüfbar")
class BrowserVorpruefungTests(_Basis):
    """Der Browser-Audit unterscheidet drei Zustände – ausgeführt, nicht gelesen."""

    SCRIPT = ROOT / "scripts" / "layout_browser_check.js"

    def _lauf(self, base: Path) -> subprocess.CompletedProcess:
        env = {"PATH": "/usr/bin:/bin:/usr/local/bin",
               "LAYOUT_BASE": str(base),
               # Bewusst KEIN CHROME_PATH: ohne messbaren Bau darf der Audit
               # die fehlende Browser-Umgebung gar nicht erst als Ausrede
               # benutzen.
               "HOME": str(self.tmp)}
        return subprocess.run([shutil.which("node"), str(self.SCRIPT)],
                              capture_output=True, text=True, env=env)

    def test_leerer_bau_ist_werkzeugfehler_exit_3(self) -> None:
        lauf = self._lauf(self.base)
        self.assertEqual(3, lauf.returncode,
                         f"leerer Bau darf kein Befund (1) und keine weiche "
                         f"Überspringung (2) sein:\n{lauf.stderr}")
        self.assertIn("NICHTS gemessen", lauf.stderr)
        self.assertIn("fail-closed", lauf.stderr)

    def test_teilbau_ist_werkzeugfehler(self) -> None:
        # Startseite und ein Artikel sind da, aber kein vollständiger Bau –
        # genau der Zustand vom 26.10.2026.
        self.seite("index.html")
        self.seite("posts/artikel/index.html")
        lauf = self._lauf(self.base)
        self.assertEqual(3, lauf.returncode)
        self.assertIn("Mindestumfang", lauf.stderr)

    def test_messbarer_bau_ohne_chrome_ist_weich_uebersprungen(self) -> None:
        self.vollbau()
        lauf = self._lauf(self.base)
        self.assertEqual(2, lauf.returncode, lauf.stderr)
        self.assertIn("übersprungen", lauf.stderr)

    def test_selftest_bleibt_ohne_browser_lauffaehig(self) -> None:
        lauf = subprocess.run([shutil.which("node"), str(self.SCRIPT), "--selftest"],
                              capture_output=True, text=True)
        self.assertEqual(0, lauf.returncode, lauf.stderr)
        self.assertIn('"selftest":"ok"', lauf.stdout)


if __name__ == "__main__":
    unittest.main()
