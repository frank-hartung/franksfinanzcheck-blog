"""Hermetische Tests der Social-Vorschau (scripts/social_limits.py,
scripts/social_vorschau.py).

Zwei Dinge müssen stimmen, sonst ist die Vorschau gefährlich: Die Bildmaße
dürfen NICHT geraten werden (ein grünes Licht ohne Deckung), und die
Erzeugung darf keinen Datensatz ungefiltert in die Seite schreiben
(Script-Abbruch). Beides wird hier geprüft; dazu Kanalgrenzen, die
Frontmatter-Quelle und der Build-Modus.
"""
import json
import os
import struct
import tempfile
import unittest

import scripts.social_limits as sl
import scripts.social_vorschau as sv

PNG_1200 = (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
            + struct.pack(">II", 1200, 630) + b"\x08\x02\x00\x00\x00")


def repo_anlegen(root: str, *, cover: bool = True, draft: bool = False) -> str:
    os.makedirs(os.path.join(root, "content", "posts", "artikel"), exist_ok=True)
    os.makedirs(os.path.join(root, "static", "images"), exist_ok=True)
    with open(os.path.join(root, "hugo.toml"), "w", encoding="utf-8") as fh:
        fh.write('baseURL = "https://franksfinanzcheck.de/"\n')
    if cover:
        with open(os.path.join(root, "static", "images", "cover.png"), "wb") as fh:
            fh.write(PNG_1200)
    cover_block = 'cover:\n  image: "images/cover.png"\n  alt: "Stromzähler"\n' if cover else ""
    with open(os.path.join(root, "content", "posts", "artikel", "index.md"),
              "w", encoding="utf-8") as fh:
        fh.write('---\ntitle: "Strom sparen im Haushalt"\n'
                 'description: "Strom sparen: Stromfresser finden, Tarife vergleichen."\n'
                 f'date: 2026-09-01\ndraft: {"true" if draft else "false"}\n'
                 f'{cover_block}---\n\nText.\n')
    return os.path.join(root, "content", "posts", "artikel", "index.md")


class GrenzenTests(unittest.TestCase):
    def test_kanal_lookup_und_eindeutige_ids(self):
        self.assertEqual(sl.kanal("x")["name"], "X (Twitter)")
        self.assertIsNone(sl.kanal("gibtsnicht"))
        ids = [k["id"] for k in sl.KANAELE]
        self.assertEqual(len(ids), len(set(ids)))

    def test_jede_grenze_hat_eine_quelle(self):
        for k in sl.KANAELE:
            self.assertTrue(k["quelle"], k["id"])
            self.assertLessEqual(k["titel_max"], k["beschreibung_max"])

    def test_kurzer_text_erzeugt_keinen_befund(self):
        self.assertEqual(sl.text_befunde("Strom sparen", "Stromfresser finden."), [])

    def test_fehlendes_bild_ist_p1(self):
        befunde = sl.bild_befunde(None, None)
        self.assertEqual([(b["code"], b["schwere"]) for b in befunde], [("social-bild", "P1")])

    def test_ideales_bild_ist_unauffaellig(self):
        self.assertEqual(sl.bild_befunde(1200, 630, groesse=400_000), [])

    def test_hochformat_ist_genau_ein_befund_mit_pinterest_hinweis(self):
        befunde = sl.bild_befunde(1000, 1500)
        self.assertEqual(len(befunde), 1)
        self.assertEqual(befunde[0]["code"], "social-bild-format")
        self.assertIn("Pinterest", befunde[0]["detail"])

    def test_zu_kleines_und_zu_grosses_bild(self):
        codes = {b["code"] for b in sl.bild_befunde(400, 400, groesse=20 * 1024 * 1024)}
        self.assertEqual(codes, {"social-bild-klein", "social-bild-format", "social-bild-groesse"})

    def test_zusammenfassung_zaehlt_aus_den_befunden(self):
        summ = sl.zusammenfassung([
            {"bild_breite": 1200, "befunde": [{"code": "social-titel", "schwere": "P3"}]},
            {"bild_breite": None, "befunde": [{"code": "social-bild", "schwere": "P1"}]},
        ])
        self.assertEqual((summ["seiten"], summ["ohne_bild"], summ["befunde"]), (2, 1, 2))


class BildmassTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def datei(self, name, inhalt):
        pfad = os.path.join(self.tmp.name, name)
        with open(pfad, "wb") as fh:
            fh.write(inhalt)
        return pfad

    def test_png(self):
        self.assertEqual(sv.bild_masse(self.datei("a.png", PNG_1200)), (1200, 630))

    def test_jpeg(self):
        jpeg = (b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                + b"\xff\xc0\x00\x11\x08" + struct.pack(">HH", 600, 800)
                + b"\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01")
        self.assertEqual(sv.bild_masse(self.datei("a.jpg", jpeg)), (800, 600))

    def test_gif(self):
        gif = b"GIF89a" + struct.pack("<HH", 400, 300) + b"\x00\x00\x00"
        self.assertEqual(sv.bild_masse(self.datei("a.gif", gif)), (400, 300))

    def test_webp(self):
        webp = (b"RIFF" + struct.pack("<I", 30) + b"WEBP" + b"VP8X" + b"\x0a\x00\x00\x00"
                + b"\x00" * 4 + (1200 - 1).to_bytes(3, "little") + (630 - 1).to_bytes(3, "little"))
        self.assertEqual(sv.bild_masse(self.datei("a.webp", webp)), (1200, 630))

    def test_unbekanntes_format_wird_nicht_geschaetzt(self):
        self.assertEqual(sv.bild_masse(self.datei("x.bin", b"kein bild" * 10)), (None, None))
        self.assertEqual(sv.bild_masse(os.path.join(self.tmp.name, "fehlt.png")), (None, None))


class OgTitelTests(unittest.TestCase):
    def test_regel_wie_seo_title_html(self):
        self.assertEqual(sv._og_titel("Kurz", None), "Kurz | FranksFinanzcheck")
        self.assertEqual(sv._og_titel("K" * 40, None), "K" * 40)
        self.assertEqual(sv._og_titel("Kurz", "Eigener SEO-Titel"), "Eigener SEO-Titel")


class VorschauTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = os.path.join(self.tmp.name, "repo")
        self.ausgabe = os.path.join(self.tmp.name, "out")

    def test_frontmatter_quelle_mit_cover(self):
        repo_anlegen(self.root)
        daten = sv.sammle(self.root, "frontmatter", self.ausgabe, heute="2026-10-28")
        seite = daten["pages"][0]
        self.assertEqual(daten["quelle"], "frontmatter")
        self.assertEqual((seite["bild_breite"], seite["bild_hoehe"]), (1200, 630))
        self.assertEqual(seite["befunde"], [])
        self.assertEqual(seite["url"], "https://franksfinanzcheck.de/posts/artikel/")
        self.assertTrue(seite["bild_datei"].endswith(os.path.join("static", "images", "cover.png")))

    def test_fehlendes_cover_ist_p1(self):
        repo_anlegen(self.root, cover=False)
        seite = sv.sammle(self.root, "frontmatter", self.ausgabe, heute="2026-10-28")["pages"][0]
        self.assertIn("social-bild", {b["code"] for b in seite["befunde"]})
        self.assertEqual(seite["schwere"], "P1")

    def test_draft_erscheint_nicht(self):
        repo_anlegen(self.root, draft=True)
        daten = sv.sammle(self.root, "frontmatter", self.ausgabe, heute="2026-10-28")
        self.assertEqual(daten["pages"], [])

    def test_build_modus_liest_gerenderte_meta_tags(self):
        repo_anlegen(self.root)
        public = os.path.join(self.root, "public")
        os.makedirs(os.path.join(public, "posts", "artikel"), exist_ok=True)
        with open(os.path.join(public, "index.html"), "w", encoding="utf-8") as fh:
            fh.write('<html lang="de"><head><title>Start</title></head><body></body></html>')
        with open(os.path.join(public, "posts", "artikel", "index.html"),
                  "w", encoding="utf-8") as fh:
            fh.write('<html lang="de"><head><title>Strom sparen</title>'
                     '<link rel="canonical" href="https://franksfinanzcheck.de/posts/artikel/">'
                     '<meta property="og:title" content="Strom sparen im Haushalt">'
                     '<meta property="og:description" content="Strom sparen: Stromfresser finden.">'
                     '<meta property="og:image" content="https://franksfinanzcheck.de/images/cover.png">'
                     '<meta property="og:image:alt" content="Stromzähler">'
                     '</head><body><h1>Strom sparen</h1></body></html>')
        daten = sv.sammle(self.root, "auto", self.ausgabe, heute="2026-10-28")
        self.assertEqual(daten["quelle"], "build")
        seiten = {p["slug"]: p for p in daten["pages"]}
        self.assertIn("artikel", seiten)
        self.assertEqual(seiten["artikel"]["bild_breite"], 1200)
        self.assertEqual(seiten["artikel"]["titel_og"], "Strom sparen im Haushalt")

    def test_build_quelle_ohne_build_ist_ein_fehler(self):
        repo_anlegen(self.root)
        with self.assertRaises(ValueError):
            sv.sammle(self.root, "build", self.ausgabe, heute="2026-10-28")

    def test_ausgabe_maskiert_den_datensatz(self):
        repo_anlegen(self.root)
        daten = sv.sammle(self.root, "frontmatter", self.ausgabe, heute="2026-10-28")
        daten["pages"][0]["titel_og"] = "</script><img src=x onerror=alert(1)>"
        pfade = sv.schreibe(daten, self.ausgabe)
        html = open(pfade["html"], encoding="utf-8").read()
        self.assertNotIn("</script><img", html)
        self.assertIn("\\u003c/script\\u003e", html)
        self.assertTrue(os.path.isfile(os.path.join(self.ausgabe, "app.js")))
        self.assertTrue(os.path.isfile(os.path.join(self.ausgabe, "vorschau.json")))
        json.load(open(pfade["json"], encoding="utf-8"))

    def test_csv_neutralisiert_formeln(self):
        repo_anlegen(self.root, cover=False)
        daten = sv.sammle(self.root, "frontmatter", self.ausgabe, heute="2026-10-28")
        daten["pages"][0]["slug"] = "=HYPERLINK(\"http://x\")"
        pfade = sv.schreibe(daten, self.ausgabe)
        with open(pfade["csv"], encoding="utf-8-sig") as fh:
            inhalt = fh.read()
        self.assertIn("'=HYPERLINK", inhalt)
        self.assertIn("Prüfung", inhalt)

    def test_selbsttest_ist_gruen(self):
        self.assertEqual(sv.selftest(), 0)


if __name__ == "__main__":
    unittest.main()


class ServerTests(unittest.TestCase):
    """Der lokale Vorschau-Server liefert nur, was auf der Positivliste steht.

    Anlass: CodeQL hat am 28.10.2026 `py/path-injection` und
    `py/http-response-splitting` an der früheren Fassung gemeldet. Der Server
    war ein lokales Werkzeug – „nur lokal" ist aber keine Eigenschaft, die
    einen Pfad aus einer Anfrage harmlos macht.
    """

    def setUp(self):
        import threading
        import urllib.request
        self._threading, self._request = threading, urllib.request
        self.tmp = tempfile.mkdtemp()
        with open(os.path.join(self.tmp, "index.html"), "w", encoding="utf-8") as fh:
            fh.write("<html><body>Bericht</body></html>")
        with open(os.path.join(self.tmp, "vorschau.json"), "w", encoding="utf-8") as fh:
            fh.write("{}")
        # Eine Datei, die NICHT auf der Positivliste steht (falsche Endung).
        with open(os.path.join(self.tmp, "geheim.txt"), "w", encoding="utf-8") as fh:
            fh.write("nicht ausliefern")
        self.server = sv.server(self.tmp, "127.0.0.1", 0)
        self.port = self.server.server_address[1]
        self.faden = self._threading.Thread(target=self.server.serve_forever, daemon=True)
        self.faden.start()

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.faden.join(timeout=5)
        for name in os.listdir(self.tmp):
            os.unlink(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)

    def hole(self, pfad: str):
        try:
            with self._request.urlopen(f"http://127.0.0.1:{self.port}{pfad}", timeout=5) as antwort:
                return antwort.status, antwort.headers.get("Content-Type", ""), antwort.read()
        except self._request.HTTPError as fehler:
            return fehler.code, fehler.headers.get("Content-Type", ""), b""
        except (self._request.URLError, ValueError) as fehler:
            # Der Client selbst kann eine Anfrage mit Steuerzeichen ablehnen
            # (http.client.InvalidURL, ab 3.12 strenger geprüft). Auch das ist
            # ein Beweis: Es geht kein präparierter Header auf die Reise.
            return 0, f"abgelehnt: {type(fehler).__name__}", b""

    def test_startseite_und_json_werden_ausgeliefert(self):
        status, typ, inhalt = self.hole("/")
        self.assertEqual(status, 200)
        self.assertTrue(typ.startswith("text/html"), typ)
        self.assertIn(b"Bericht", inhalt)
        status, typ, _ = self.hole("/vorschau.json")
        self.assertEqual(status, 200)
        self.assertTrue(typ.startswith("application/json"), typ)

    def test_nicht_gelistete_datei_und_ausbruch_ergeben_404(self):
        self.assertEqual(self.hole("/geheim.txt")[0], 404)
        self.assertEqual(self.hole("/nichtda.html")[0], 404)
        # Klassischer Ausbruch: darf die Positivliste nicht umgehen.
        self.assertEqual(self.hole("/../../etc/passwd")[0], 404)
        self.assertEqual(self.hole("/%2e%2e/%2e%2e/etc/passwd")[0], 404)

    def test_bilder_aus_static_werden_ausgeliefert(self):
        """Die Karten verlinken relativ (`../../static/images/…`); der Browser
        fragt `/static/images/…` – das muss die Positivliste enthalten."""
        kandidaten = [k for k in sv._auslieferbar(self.tmp) if k.startswith("/static/")]
        self.assertTrue(kandidaten, "keine Bilder aus static/ in der Positivliste")
        status, typ, _ = self.hole(kandidaten[0])
        self.assertEqual(status, 200, kandidaten[0])
        self.assertTrue(typ.startswith("image/"), typ)

    def test_content_type_kommt_aus_der_tabelle_nicht_aus_der_anfrage(self):
        """Ein CRLF im Dateinamen darf keinen zusätzlichen Header erzeugen."""
        status, typ, _ = self.hole("/index.html%0d%0aX-Boese:%20ja")
        self.assertIn(status, (0, 404), status)
        self.assertNotIn("X-Boese", typ)
