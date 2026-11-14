"""Reproduzierbare Cover und verlustfreie Varianten (#1211 / #1208)."""
from __future__ import annotations

import contextlib
import hashlib
import io
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from PIL import Image, ImageChops, ImageDraw, ImageFont, features

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cover_render_check as render  # noqa: E402
import generate_covers as covers  # noqa: E402
import image_optimizer as optimizer  # noqa: E402


class FontLayoutVertrag(unittest.TestCase):
    def test_generator_waehlt_basic_ausdruecklich(self):
        with mock.patch.object(covers.ImageFont, "truetype", wraps=ImageFont.truetype) as laden:
            font = covers.load_font(56)
        self.assertEqual(font.layout_engine, ImageFont.Layout.BASIC)
        self.assertEqual(laden.call_args.kwargs["layout_engine"], ImageFont.Layout.BASIC)
        self.assertTrue(hasattr(laden.call_args.args[0], "read"),
                        "Pillow darf bei Fehler nicht in System-Fontordner ausweichen")

    def test_raqm_und_basic_koennen_andere_pixel_erzeugen(self):
        if not features.check_feature("raqm"):
            self.skipTest("RAQM nicht installiert – BASIC-Vertrag wird separat geprüft")
        schrift = ROOT / "static/fonts/Inter-Bold.ttf"
        automatisch = ImageFont.truetype(str(schrift), 56)
        self.assertEqual(automatisch.layout_engine, ImageFont.Layout.RAQM)
        basic = covers.load_font(56)
        bilder = [Image.new("RGB", (800, 120), "white") for _ in range(2)]
        for bild, font in zip(bilder, (automatisch, basic)):
            ImageDraw.Draw(bild).text((10, 10), "Geld sparen für 2026", font=font, fill="black")
        self.assertIsNotNone(ImageChops.difference(*bilder).getbbox(),
                             "Diese Probe muss den früheren Runner-Drift sichtbar machen")

    def test_fehlt_repo_schrift_dann_keine_gleichnamige_systemschrift(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            system = root / "user-share/fonts"
            system.mkdir(parents=True)
            shutil.copy2(ROOT / "static/fonts/Inter-Bold.ttf", system / "Inter-Bold.ttf")
            with mock.patch.object(covers, "BLOG_DIR", str(root / "repo")), \
                 mock.patch.dict(os.environ, {"XDG_DATA_HOME": str(system.parent)}), \
                 contextlib.redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as fehler:
                    covers.load_font(40)
            self.assertEqual(fehler.exception.code, 2)

    def test_echtes_pillar_cover_bleibt_pixelidentisch(self):
        datei = ROOT / "content/pillar/strom-sparen/index.md"
        slug, titel, badge, spar = render.expected_inputs(
            covers, str(datei), datei.read_text(encoding="utf-8"))
        original = ROOT / "static/images/covers" / f"{slug}.jpg"
        with tempfile.TemporaryDirectory() as tmp:
            ziel = Path(tmp) / "probe.jpg"
            with contextlib.redirect_stdout(io.StringIO()):
                render.render_to(covers, titel, badge, spar, str(ziel))
            self.assertTrue(render.same_pixels(original, ziel),
                            "Reproduktion muss die gespeicherten Pixel treffen")


class BildVariantenVertrag(unittest.TestCase):
    def test_native_avif_unabhaengig_vom_optionalen_plugin(self):
        code = (
            "import sys; sys.modules['pillow_avif'] = None; "
            "from PIL import features; import scripts.image_optimizer as opt; "
            "print(int(features.check('avif')), int(opt.AVIF_OK))"
        )
        proc = subprocess.run([sys.executable, "-c", code], cwd=ROOT,
                              capture_output=True, text=True, check=True, timeout=30)
        native, erkannt = map(int, proc.stdout.strip().splitlines()[-1].split())
        if not native:
            self.skipTest("Pillow ohne nativen AVIF-Encoder")
        self.assertEqual(erkannt, 1, "Der Encoder darf nicht am Plugin-Import hängen")

    def test_aus_original_nachziehen_ist_idempotent_und_vollstaendig(self):
        if not optimizer.AVIF_OK or "WEBP" not in Image.SAVE:
            self.skipTest("AVIF-/WebP-Encoder in dieser Umgebung nicht verfügbar")
        # 720 ist sowohl eine responsive Breite als auch die Root-Breite.
        # Früher wurde dadurch avif/720 und webp/720 nie geschrieben.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "static/images/covers/probe.jpg"
            original.parent.mkdir(parents=True)
            Image.new("RGB", (720, 1080), (40, 80, 120)).save(original, quality=90)
            vorher = hashlib.sha256(original.read_bytes()).digest()
            with mock.patch.object(optimizer, "BLOG_DIR", root), \
                 mock.patch.object(optimizer, "ist_ki_original", return_value=False):
                erstellt = optimizer.optimize_cover_image(original)
                self.assertEqual(len(erstellt), 14)
                self.assertEqual(optimizer.check_sources([original]), [])
                self.assertEqual(optimizer.optimize_cover_image(original), [])
            self.assertEqual(hashlib.sha256(original.read_bytes()).digest(), vorher)
            for fmt in ("avif", "webp"):
                for pfad in (original.parent / fmt / f"probe.{fmt}",
                             original.parent / fmt / "720" / f"probe.{fmt}"):
                    self.assertTrue(pfad.is_file(), str(pfad))
                    with Image.open(pfad) as bild:
                        self.assertEqual(bild.size, (720, 1080))

    def test_ki_original_wird_nicht_abgeleitet(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            original = root / "probe.jpg"
            Image.new("RGB", (720, 1080), "white").save(original)
            vorher = original.read_bytes()
            with mock.patch.object(optimizer, "BLOG_DIR", root), \
                 mock.patch.object(optimizer, "KI_ORIGINAL_UEBERSPRUNGEN", []), \
                 mock.patch.object(optimizer, "ist_ki_original", return_value=True):
                self.assertEqual(optimizer.optimize_cover_image(original, force=True), [])
            self.assertEqual(original.read_bytes(), vorher)
            self.assertEqual([p.name for p in root.iterdir()], ["probe.jpg"])


if __name__ == "__main__":
    unittest.main()
