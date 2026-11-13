#!/usr/bin/env python3
"""#1028: Feed und direkte Pinterest-Payloads offline und ohne Token prüfen.

Die Tests belegen den eigenen Ausgang, NICHT, dass Pinterest den Inhalt
übernimmt, anzeigt oder Anbieter-Wasserzeichen erhält.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import types
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import ki_provenienz as kp  # noqa: E402
import ki_bild_markierung as markierung  # noqa: E402
import pinterest_hashtags as ph  # noqa: E402
import generate_pins as generator  # noqa: E402

# Ein Import des Engines darf in einem Offline-Test keinen Token prüfen.
with patch.dict(sys.modules, {"pinterest_token": types.SimpleNamespace(get_token=lambda: "")}):
    import pinterest_engine as engine  # noqa: E402
import social_studio as studio  # noqa: E402
import social_gate  # noqa: E402
from social_channels import pinterest as adapter_module  # noqa: E402

HUGO = os.environ.get("HUGO_BIN", "hugo")


def ki_cover_fixture(root: Path) -> str:
    """Kleines JPEG mit Test-Markierung und fassungsgebundenem Testbeleg."""
    image = root / "static/cover.jpg"
    image.parent.mkdir(parents=True, exist_ok=True)
    image.write_bytes(b"\xff\xd8\xff\xd9")
    typ = "trainedAlgorithmicMedia"
    markierung.schreiben(image, markierung.paket_bauen(typ, datum="2026-01-01T00:00:00Z"))
    sha = hashlib.sha256(image.read_bytes()).hexdigest()
    return ("cover:\n  image: /cover.jpg\n  ai_generated: true\n  ki_pruefung:\n"
            f'    sha256: "{sha}"\n    quelle: "Testbeleg"\n'
            f"    geprueft_am: 2026-01-01\n    deepfake: false\n    digital_source_type: {typ}\n")


class AngabenTests(unittest.TestCase):
    def test_nur_explizite_booleans_und_bildpruefung(self):
        self.assertEqual(kp.social_erklaerungen("title: x\nai_generated: true # ja\n"),
                         (True, False))
        self.assertEqual(kp.social_erklaerungen("title: x\nai_generated: false\n"),
                         (False, False))
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            beleg = ki_cover_fixture(root)
            self.assertEqual(kp.social_erklaerungen("title: x\nai_generated: true\n" + beleg, root),
                             (True, True))
            (root / "static/cover.jpg").write_bytes(b"ausgetauscht")
            with self.assertRaises(kp.WerkzeugFehler):
                kp.social_erklaerungen("title: x\n" + beleg, root)
        for kopf in ("", "[kein, objekt]", "ai_generated: [true\n",
                     'ai_generated: "true"\n', "ai_generated: yes\n",
                     "ai_generated: true\nai_generated: false\n",
                     "AI_GENERATED: true\nai_generated: false\n",
                     "cover: {ai_generated: true}\n",
                     "cover: {ai_generated: true, ki_pruefung: {deepfake: false}}\n",
                     "cover: {ai_generated: true, ki_pruefung: {deepfake: true}}\n",
                     "cover: {ai_generated: true, ki_pruefung: {deepfake: 'false'}}\n",
                     "default: &x {ai_generated: true}\n<<: *x\n"):
            with self.subTest(kopf=kopf), self.assertRaises(kp.WerkzeugFehler):
                kp.social_erklaerungen(kopf)

    def test_cover_nachweis_braucht_hash_quelle_datum_und_iptc_ohne_doppelte_felder(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            beleg = ki_cover_fixture(root)
            for fehlerhaft in (
                beleg.replace('quelle: "Testbeleg"', 'quelle: ""'),
                beleg.replace('geprueft_am: 2026-01-01', 'geprueft_am: 2999-01-01'),
                beleg.replace('digital_source_type: trainedAlgorithmicMedia', 'digital_source_type: algorithmicMedia'),
                beleg.replace('deepfake: false', 'deepfake: false\n    deepfake: true'),
                beleg.replace('sha256:', 'sha256: falscher-wert\n    sha256:'),
            ):
                with self.subTest(beleg=fehlerhaft), self.assertRaises(kp.WerkzeugFehler):
                    kp.social_erklaerungen(fehlerhaft, root)
            bild = root / "static/cover.jpg"
            alt = hashlib.sha256(bild.read_bytes()).hexdigest()
            bild.write_bytes(b"\xff\xd8\xff\xd9")  # neuer Hash, aber keine IPTC-Markierung
            neuer_hash = hashlib.sha256(bild.read_bytes()).hexdigest()
            with self.assertRaises(kp.WerkzeugFehler):
                kp.social_erklaerungen(beleg.replace(alt, neuer_hash), root)

    def test_hinweis_ist_idempotent_und_werbung_bleibt_vorn(self):
        text = "*Werbung | Spartipps & Verträge #geldsparen"
        fertig = kp.social_hinweis(text, ki_text=True, ki_bild=True)
        self.assertTrue(fertig.startswith("*Werbung | " + kp.SOCIAL_TEXT + " " + kp.SOCIAL_BILD))
        self.assertEqual(fertig, kp.social_hinweis(fertig, ki_text=True, ki_bild=True))
        self.assertEqual(kp.social_hinweis(text), text)
        self.assertNotIn(kp.SOCIAL_PIN, fertig)


class DirektePublisherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "content/posts/quelle/index.md"
        self.path.parent.mkdir(parents=True)
        self.ki_cover = ki_cover_fixture(self.root)
        for p in (patch.object(kp, "ROOT", self.root),
                  patch.object(generator, "BASE_URL", "https://example.test"),
                  patch.object(engine, "BASE_URL", "https://example.test")):
            p.start()
            self.addCleanup(p.stop)

    def post_schreiben(self, flags: str):
        self.path.write_text(
            '---\ntitle: "Artikel"\ndescription: "Spartipps"\n'
            'pin_description: "*Werbung | ' + ('Langer Satz. ' * 55) +
            '#geldsparen #spartipps #internet"\n' + flags + '\n---\nInhalt\n',
            encoding="utf-8")

    def test_beide_writer_lesen_flags_aus_der_quelle_und_senden_sie(self):
        self.post_schreiben("ai_generated: true\n" + self.ki_cover)
        with patch.object(generator, "list_post_paths", return_value=[str(self.path)]), \
             patch.object(engine, "list_post_paths", return_value=[str(self.path)]):
            p1 = generator.load_posts()[0]
            p2 = engine.load_posts()[0]
        self.assertEqual((p1["ki_text"], p1["ki_bild"]), (True, True))
        self.assertEqual((p2["ki_text"], p2["ki_bild"]), (True, True))
        texts = (generator.build_api_description(p1), engine.pin_text(p2))
        for text in texts:
            with self.subTest(beschreibung=text[:100]):
                self.assertTrue(text.startswith("*Werbung | " + kp.SOCIAL_TEXT + " " + kp.SOCIAL_BILD))
                self.assertNotIn(kp.SOCIAL_PIN, text)
                self.assertLessEqual(len(text), 500)
                self.assertEqual(ph.befunde(text), [])
                self.assertEqual(ph.tags_normalisiert(text), ["geldsparen", "spartipps", "internet"])
        self.assertEqual(p2["cover"], "/cover.jpg")

        payloads = []
        class Antwort:
            def __enter__(self): return self
            def __exit__(self, *_): return False
            def read(self): return b'{"id": "offline"}'
        def urlopen(req, **_):
            payloads.append(json.loads(req.data.decode()))
            return Antwort()
        with patch("urllib.request.urlopen", side_effect=urlopen):
            generator.create_pin("offline", "board", p1,
                                 "https://example.test/posts/quelle/", "https://example.test/cover.jpg")
            engine.api_post_pin("offline", "board", p2)
        self.assertEqual([p["description"] for p in payloads], list(texts))

    def test_api_grenzen_blockieren_falsche_flags_ziel_bild_und_alten_snapshot(self):
        self.post_schreiben("ai_generated: true\n" + self.ki_cover
                            + "pin_image: /anderes-pin-bild.jpg\n")
        with patch.object(generator, "list_post_paths", return_value=[str(self.path)]), \
             patch.object(engine, "list_post_paths", return_value=[str(self.path)]):
            p1, p2 = generator.load_posts()[0], engine.load_posts()[0]
        link = "https://example.test/posts/quelle/"
        bild = "https://example.test/cover.jpg"
        with patch("urllib.request.urlopen") as api:
            for falsch in ({**p1, "ki_text": False}, {**p1, "slug": "andere"},
                            {"title": "frei erfunden", "slug": "quelle"}):
                with self.subTest(falsch=falsch), self.assertRaises(kp.WerkzeugFehler):
                    generator.create_pin("offline", "board", falsch, link, bild)
            with self.assertRaises(kp.WerkzeugFehler):
                generator.create_pin("offline", "board", p1, "https://example.test/posts/fremd/", bild)
            with self.assertRaises(kp.WerkzeugFehler):
                generator.create_pin("offline", "board", p1, link, "https://example.test/anders.jpg")
            with self.assertRaises(kp.WerkzeugFehler):
                engine.api_post_pin("offline", "board", p2)  # separates pin_image
            self.path.write_text(p1["content"] + "geändert", encoding="utf-8")
            with self.assertRaises(kp.WerkzeugFehler):
                generator.create_pin("offline", "board", p1, link, bild)
            api.assert_not_called()

    def test_bilddatei_nach_dem_laden_ausgetauscht_blockiert_vor_post(self):
        self.post_schreiben("ai_generated: true\n" + self.ki_cover)
        with patch.object(engine, "list_post_paths", return_value=[str(self.path)]):
            p = engine.load_posts()[0]
        (self.root / "static/cover.jpg").write_bytes(b"anders")
        with patch("urllib.request.urlopen") as api, self.assertRaises(kp.WerkzeugFehler):
            engine.api_post_pin("offline", "board", p)
        api.assert_not_called()

    def test_unbekannte_herkunft_wird_nicht_positiv_behauptet(self):
        self.post_schreiben("ai_generated: false\ncover:\n  image: /cover.jpg")
        with patch.object(generator, "list_post_paths", return_value=[str(self.path)]), \
             patch.object(engine, "list_post_paths", return_value=[str(self.path)]):
            texts = (generator.build_api_description(generator.load_posts()[0]),
                     engine.pin_text(engine.load_posts()[0]))
        for text in texts:
            self.assertNotIn(kp.SOCIAL_TEXT, text)
            self.assertNotIn(kp.SOCIAL_BILD, text)

    def test_ungueltige_oder_deepfake_herkunft_bremst_beide_writer(self):
        for flags in ("ai_generated: true\nai_generated: false",
                      "ai_generated: true\ncover: {ai_generated: true}",
                      "ai_generated: true\ncover: {ai_generated: true, "
                      "ki_pruefung: {deepfake: true}}"):
            with self.subTest(flags=flags):
                self.post_schreiben(flags)
                for mod in (generator, engine):
                    with patch.object(mod, "list_post_paths", return_value=[str(self.path)]):
                        with self.assertRaises(kp.WerkzeugFehler):
                            mod.load_posts()


class SocialAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.path = self.root / "content/posts/x/index.md"
        self.path.parent.mkdir(parents=True)
        self.path.write_text("---\ntitle: x\nai_generated: true\n---\nText\n", encoding="utf-8")
        root_patch = patch.object(kp, "ROOT", self.root)
        root_patch.start()
        self.addCleanup(root_patch.stop)
        article = studio.copy.load_article(str(self.path), "https://example.test")
        self.ch = {"text": {"max_chars": 500, "title_max_chars": 100}}
        self.adapter = adapter_module.PinterestAdapter(self.ch, {}, "pinterest")
        self.item = {"channel": "pinterest", "slug": "x", "headline": "Artikel", "text": "Ein Text #geldsparen",
                     "url": "https://example.test/posts/x/", "media_url": "https://example.test/x.jpg",
                     "article": article}

    def senden(self, item):
        with patch.object(self.adapter, "configured", return_value=(True, "")), \
             patch.object(self.adapter, "resolve_board", return_value="board"), \
             patch.object(adapter_module, "http_json", return_value=(201, {"id": "offline"}, None)) as api:
            res = self.adapter.publish(item)
        return res, api

    def test_studio_und_adapter_pruefen_denselben_unveraenderten_payload(self):
        self.item["ai_polished"] = True
        studio.pinterest_kennzeichnung(self.item, "pinterest", self.ch)
        self.assertTrue(self.item["text"].startswith("*Werbung | " + kp.SOCIAL_TEXT + " " + kp.SOCIAL_PIN))
        result, api = self.senden(self.item)
        self.assertTrue(result.ok)
        payload = json.loads(api.call_args.kwargs["data"].decode())
        self.assertEqual(payload["description"], self.item["text"])

    def test_letzte_api_grenze_blockiert_fehlenden_hinweis_und_defektes_frontmatter(self):
        result, api = self.senden(self.item)  # ohne Studio-Vorbereitung
        self.assertFalse(result.ok)
        api.assert_not_called()
        self.item["article"]["raw_fm"] = "ai_generated: true\nai_generated: false\n"
        studio.pinterest_kennzeichnung(self.item, "pinterest", self.ch)
        self.assertIn("ki_kennzeichnung_fehler", self.item)
        _, violations, _ = social_gate.check(self.item, self.ch, {})
        self.assertTrue(any("KI-Provenienz" in v for v in violations))
        result, api = self.senden(self.item)
        self.assertFalse(result.ok)
        api.assert_not_called()

    def test_zu_langer_text_wird_nicht_still_in_den_hinweis_geschnitten(self):
        self.item["text"] = "Wort " * 100
        studio.pinterest_kennzeichnung(self.item, "pinterest", self.ch)
        self.assertIn("ki_kennzeichnung_fehler", self.item)
        result, api = self.senden(self.item)
        self.assertFalse(result.ok)
        api.assert_not_called()

    def test_adapter_verweigert_altfassung_oder_fremdes_ziel(self):
        studio.pinterest_kennzeichnung(self.item, "pinterest", self.ch)
        self.item["url"] = "https://example.test/posts/fremd/"
        result, api = self.senden(self.item)
        self.assertFalse(result.ok)
        api.assert_not_called()
        self.item["url"] = "https://example.test/posts/x/"
        self.path.write_text(self.path.read_text(encoding="utf-8") + "nach Planung geändert", encoding="utf-8")
        result, api = self.senden(self.item)
        self.assertFalse(result.ok)
        api.assert_not_called()

    def test_ki_cover_wird_nicht_umkodiert_und_nur_original_darf_gesendet_werden(self):
        beleg = ki_cover_fixture(self.root)
        self.path.write_text("---\ntitle: x\nai_generated: true\n" + beleg + "---\nText\n", encoding="utf-8")
        self.item["article"] = studio.copy.load_article(str(self.path), "https://example.test")
        with patch.object(studio, "BLOG_DIR", str(self.root)), \
             patch.object(studio.images, "STATIC_DIR", str(self.root / "static")), \
             patch.object(studio.images, "ensure_variant") as encode:
            path, url = studio.resolve_media(self.item["article"],
                                              {"media": {"variant": "4:5"}},
                                              {"base_url": "https://example.test"})
            self.assertEqual(Path(path), self.root / "static/cover.jpg")
            self.assertEqual(url, "https://example.test/cover.jpg")
            encode.assert_not_called()
        studio.pinterest_kennzeichnung(self.item, "pinterest", self.ch)
        self.item["media_url"] = "https://example.test/images/social/x-4x5.jpg"
        result, api = self.senden(self.item)
        self.assertFalse(result.ok)
        api.assert_not_called()
        self.item["media_url"] = url
        result, api = self.senden(self.item)
        self.assertTrue(result.ok)
        api.assert_called_once()

    def test_unknown_polituraussage_und_widerspruechlicher_hinweis_blockieren(self):
        for value in ("true", None):
            self.item["ai_polished"] = value
            studio.pinterest_kennzeichnung(self.item, "pinterest", self.ch)
            self.assertIn("ki_kennzeichnung_fehler", self.item)
        self.item.pop("ki_kennzeichnung_fehler")
        self.item["ai_polished"] = False
        self.item["text"] = kp.SOCIAL_BILD + " Ein Text #geldsparen"
        studio.pinterest_kennzeichnung(self.item, "pinterest", self.ch)
        self.assertIn("ki_kennzeichnung_fehler", self.item)
        result, api = self.senden(self.item)
        self.assertFalse(result.ok)
        api.assert_not_called()


class SocialBudgetTests(unittest.TestCase):
    def test_unmoegliches_budget_schneidet_weder_link_noch_hashtags_ab(self):
        link = "https://example.test/posts/" + "a" * 80 + "/"
        tags = "#geldsparen #spartipps #internet"
        result = studio.copy._hard_fit("Langer Text " * 60 + link + " " + tags,
                                       40, [link, tags])
        self.assertIn(link, result)
        self.assertIn(tags, result)
        self.assertGreater(len(result), 40)  # Social-Gate muss ablehnen
        ok, violations, _ = social_gate.check(
            {"channel": "pinterest", "text": result, "url": link, "article": {}},
            {"text": {"max_chars": 40}}, {})
        self.assertFalse(ok)
        self.assertTrue(any("L1 zu lang" in v for v in violations))


class SocialBildVariantenTests(unittest.TestCase):
    def test_bekannte_ki_originale_und_alias_werden_nicht_neu_kodiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            beleg = ki_cover_fixture(root)
            post = root / "content/posts/x/index.md"
            post.parent.mkdir(parents=True)
            post.write_text("---\ntitle: x\n" + beleg + "---\nText\n", encoding="utf-8")
            bild = root / "static/cover.jpg"
            alias = root / "static/alias.jpg"
            alias.symlink_to(bild)
            with patch.object(studio.images, "BLOG_DIR", str(root)), \
                 patch.object(studio.images, "OUT_DIR", str(root / "static/images/social")):
                for quelle in (bild, alias):
                    vorher = quelle.read_bytes()
                    ergebnis = studio.images.ensure_variant(str(quelle), "x", "4:5", force=True)
                    self.assertEqual(ergebnis, str(quelle))
                    self.assertEqual(quelle.read_bytes(), vorher)
                self.assertFalse((root / "static/images/social/x-4x5.jpg").exists())

    def test_ungemessener_inventarschutz_kodiert_nicht_neu(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            bild = root / "static/cover.jpg"
            bild.parent.mkdir(parents=True)
            bild.write_bytes(b"original")
            with patch.object(studio.images, "BLOG_DIR", str(root)), \
                 patch("ki_cover_provenienz.protected_paths", side_effect=ValueError("kaputt")):
                self.assertEqual(studio.images.ensure_variant(str(bild), "x", "4:5"), str(bild))
                self.assertEqual(bild.read_bytes(), b"original")


@unittest.skipUnless(shutil.which(HUGO), "Hugo nicht installiert")
class EchterRssRenderTests(unittest.TestCase):
    def test_beide_rss_vorlagen_rendern_modalitaeten_und_escapen_einmal(self):
        self.assertEqual((ROOT / "layouts/rss.xml").read_bytes(),
                         (ROOT / "layouts/_default/rss.xml").read_bytes())
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            def write(path, value):
                p = root / path
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(value, encoding="utf-8")
            write("hugo.toml", 'baseURL = "https://example.test/"\ntitle = "Test"\n')
            for rel in ("layouts/rss.xml", "layouts/_default/rss.xml",
                        "layouts/_partials/_funcs/ki_modalitaeten.html"):
                write(rel, (ROOT / rel).read_text(encoding="utf-8"))
            write("layouts/_default/single.html", "<html><body>Probe</body></html>")
            write("layouts/index.html", "<html><body>Home</body></html>")
            beide = "ai_generated: true\ncover:\n  image: /bild.jpg\n  ai_generated: true\n"
            samples = {"text": "ai_generated: true\n",
                       "neutral": "ai_generated: false\n",
                       "bild": "ai_generated: false\ncover:\n  image: /bild.jpg\n  ai_generated: true\n",
                       "beide": beide, "lang": beide, "unicode": beide,
                       "geschuetzt": beide, "ohne-tags": "ai_generated: true\n"}
            standard = "*Werbung | Sonne & Wind #geldsparen"
            beschreibungen = {"lang": "*Werbung | " + ("Langer Satz. " * 80)
                                       + "#geldsparen #spartipps #internet",
                              "unicode": "*Werbung | " + ("Über Geld & Öl 💡 nachdenken. " * 80)
                                          + "#geldsparen #spartipps",
                              "geschuetzt": "*Werbung | " + " ".join("#tag" + str(i) * 22 for i in range(30)),
                              "ohne-tags": "Lange Beschreibung " * 80}
            for slug, flags in samples.items():
                desc = beschreibungen.get(slug, standard)
                write(f"content/posts/{slug}/index.md",
                      f'---\ntitle: {slug}\ndate: 2026-01-01\n'
                      f'pin_description: {json.dumps(desc, ensure_ascii=False)}\n{flags}---\nText\n')
            subprocess.run([HUGO, "--minify", "--quiet"], cwd=root, check=True,
                           capture_output=True, text=True)
            items = ET.parse(root / "public/index.xml").findall("./channel/item")
            self.assertEqual(len(items), len(samples))
            by_title = {item.findtext("title"): item.findtext("description") for item in items}
            for slug in ("text", "neutral", "bild", "beide"):
                with self.subTest(slug=slug):
                    text = by_title[slug]
                    self.assertEqual(text, kp.social_hinweis(standard,
                                     ki_text=slug in ("text", "beide"),
                                     ki_bild=slug in ("bild", "beide")))
                    self.assertNotIn("&amp;", text)  # XML-Parser hat genau einmal dekodiert
            for slug in ("lang", "unicode", "ohne-tags"):
                with self.subTest(slug=slug):
                    text = by_title[slug]
                    self.assertLessEqual(len(text), 500)
                    self.assertNotIn("&amp;", text)  # auch nach Kürzung kein Double-Escaping
                    self.assertEqual(text.count(kp.SOCIAL_TEXT), 1)
                    if slug != "ohne-tags":
                        self.assertTrue(text.startswith("*Werbung | " + kp.SOCIAL_TEXT + " " + kp.SOCIAL_BILD))
                        self.assertTrue(text.endswith("#" + beschreibungen[slug].split(" #", 1)[1]))
                    else:
                        self.assertTrue(text.startswith(kp.SOCIAL_TEXT))
            # Selbst ein unvernünftiger, >500 Zeichen langer geschützter
            # Hashtagblock darf den Herkunftshinweis nicht anschneiden; M5
            # meldet diesen Überlauf und blockiert dann die Veröffentlichung.
            text = by_title["geschuetzt"]
            self.assertGreater(len(text), 500)
            self.assertTrue(text.startswith("*Werbung | " + kp.SOCIAL_TEXT + " " + kp.SOCIAL_BILD))
            self.assertTrue(text.endswith(beschreibungen["geschuetzt"].split(" | ", 1)[1]))


if __name__ == "__main__":
    unittest.main()
