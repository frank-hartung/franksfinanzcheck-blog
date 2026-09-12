"""Regressionstests für das Schema-/SEO-Gate (Bau-Ursache 11.09.2026).

Zwei Ebenen, weil beide schon Fehler produziert haben:

1) Verhalten der Wache an einer Mini-Site – inkl. der Originalstörung: ein
   `{{ .Permalink | jsonify }}` in einem <script>-Block wird von Hugos
   kontextsensitivem Escaper NOCH EINMAL in Quotes gesetzt
   (`"@id": "\\"https://…\\""`). 31 Artikel trugen so unbrauchbares Article-
   Schema, der Build blieb grün, weil kein Prüfer in JSON-LD geschaut hat.
   Die Wache muss genau diese Klasse sehen – und GRÜN bleiben, wenn sie
   nicht gestört ist (sonst ist jede künftige Änderung „rot wie vorher").

2) Quelltext-Invarianten der Templates – die billigste Dauer-Sicherung gegen
   denselben Rückfall: JSON-LD darf in diesem Projekt nur als dict →
   `| jsonify | safeJS` gebaut werden, die Sitemap darf kein `.Lastmod`
   (Datei-Mtime = Deploy-Zeit) statt der Frontmatter lesen, und head.html muss
   die Preload-Bremse für Pager-/Archivseiten enthalten.

Beide Ebenen laufen ohne Hugo-Build und ohne Netzwerk.
"""
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

try:                                                     # Pillow für echte Maße
    from PIL import Image
    HAVE_PIL = True
except Exception:                                        # pragma: no cover
    Image = None
    HAVE_PIL = False


HUGO_COMMENT_RE = re.compile(r"{{-?\s*/\*.*?\*/\s*-?}}", re.S)

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import schema_seo_gate as gate  # noqa: E402


def good_ld(**over):
    ld = {
        "@context": "https://schema.org", "@type": "Article",
        "@id": "https://example.org/posts/a/",
        "headline": "Strom sparen im Herbst",
        "datePublished": "2026-08-10T10:00:00Z",
        "dateModified": "2026-09-01T00:00:00Z",
        "author": {"@type": "Person", "name": "Frank Hartung"},
        "publisher": {"@type": "Organization", "name": "Ex",
                      "@id": "https://example.org/#organization"},
        "image": {"@type": "ImageObject", "url": "https://example.org/i/cover.jpg",
                  "width": 1000, "height": 1500},
        "wordCount": 1200,
    }
    ld.update(over)
    return ld


FAQ = {"@type": "FAQPage", "mainEntity": [{
    "@type": "Question", "name": "Spart das wirklich etwas?",
    "acceptedAnswer": {"@type": "Answer", "text": (
        "Ja – der Ratgeber rechnet konkrete Euro-Beträge, Fristen und die "
        "drei häufigsten Fehler beim Wechsel durch.")}}]}


def article_page(ld=None, faq=FAQ, extra_head="", body_extra=""):
    head = (extra_head or '<meta name=robots content="index, follow">'
            '<meta property="og:title" content="T">'
            '<meta property="og:description" content="D">'
            '<meta property="og:image" content="https://example.org/i/cover.jpg">'
            '<meta property="og:image:width" content="1000">'
            '<meta property="og:image:height" content="1500">'
            '<meta property="og:image:alt" content="T">'
            '<meta name="twitter:card" content="summary_large_image">'
            '<link rel="canonical" href="https://example.org/posts/a/">')
    blocks = f'<script type=application/ld+json>{json.dumps(ld or good_ld())}</script>'
    if faq is not None:
        blocks += f'<script type=application/ld+json>{json.dumps(faq)}</script>'
    return (f"<html><head>{head}{blocks}</head>"
            f"<body><img src=/i/cover.jpg alt=x>{body_extra}</body></html>")


class GateFixture(unittest.TestCase):
    """Mini-Site als Fixture; jedes Tests sabotiert gezielt und prüft die Regel."""

    def setUp(self):
        if not HAVE_PIL:
            self.skipTest("Pillow fehlt – Bildmaße sind nicht prüfbar")
        self.root = tempfile.mkdtemp(prefix="schema-gate-test-")
        self.pub = os.path.join(self.root, "public")
        self.content = os.path.join(self.root, "content")
        os.makedirs(os.path.join(self.pub, "i"), exist_ok=True)
        # echtes JPEG, damit image_dims() die Maße wirklich liefert
        Image.new("RGB", (1000, 1500), (14, 90, 67)).save(
            os.path.join(self.pub, "i", "cover.jpg"), quality=80)
        os.makedirs(os.path.join(self.content, "posts", "a"), exist_ok=True)
        Path(self.content, "posts", "a", "index.md").write_text(
            '---\ntitle: "Strom sparen im Herbst"\n'
            'date: 2026-08-10T10:00:00Z\nlastmod: 2026-09-01\n---\nText\n',
            encoding="utf-8")
        Path(self.root, "hugo.toml").write_text(
            'baseURL = "https://example.org/"\n', encoding="utf-8")
        self.base = gate.site_base_url.__wrapped__ if False else "https://example.org"
        self._globals = (gate.PUBLIC, gate.CONTENT, gate.CONFIG)
        gate.PUBLIC, gate.CONTENT, gate.CONFIG = (
            self.pub, self.content, os.path.join(self.root, "hugo.toml"))
        assert gate.site_base_url() == self.base, "Fixture-Base muss zur Wache passen"
        self.write_clean()

    def tearDown(self):
        gate.PUBLIC, gate.CONTENT, gate.CONFIG = self._globals
        shutil.rmtree(self.root, ignore_errors=True)

    # ------------------------------------------------------------------ Helfer
    def write(self, rel, text):
        p = os.path.join(self.pub, rel.lstrip("/"))
        os.makedirs(os.path.dirname(p), exist_ok=True)
        Path(p).write_text(text, encoding="utf-8")
        return p

    def write_clean(self):
        self.write("posts/a/index.html", article_page())
        self.write("tags/eines/index.html",
                   '<html><head><meta name=robots content="noindex, follow">'
                   '<link rel=canonical href=https://example.org/tags/eines/>'
                   "</head><body></body></html>")
        self.write("sitemap.xml",
                   '<?xml version="1.0"?><urlset><url>'
                   "<loc>https://example.org/posts/a/</loc>"
                   "<lastmod>2026-09-01</lastmod></url></urlset>")
        self.write("robots.txt",
                   "User-agent: *\nAllow: /\nDisallow: /go/\n\n"
                   "User-agent: Pinterestbot\nAllow: /\n\n"
                   "User-agent: OAI-SearchBot\nAllow: /\n\n"
                   "Sitemap: https://example.org/sitemap.xml\n")

    def run_gate(self):
        F = gate.Findings()
        pages = [gate.check_page(p, self.base, F)
                 for p in gate.iter_pages()]
        gate.check_sitemap(pages, F)
        gate.check_robots(F)
        return ([f"{r} {m}" for r, _, m in F.hard],
                [f"{r} {m}" for r, _, m in F.soft])

    def rules(self, hard):
        return {h.split()[0] for h in hard}

    # ------------------------------------------------------------------ Tests
    def test_saubere_anlage_bleibt_gruen(self):
        hard, _ = self.run_gate()
        self.assertEqual([], hard, "grüne Anlage darf keine harten Funde melden")

    def test_doppeltes_json_escaping_wird_gesehen(self):
        """Der Original-Bug: Werte, die bereits Quotes enthalten."""
        ld = good_ld(**{"@id": '"https://example.org/posts/a/"'})
        self.write("posts/a/index.html", article_page(ld=ld))
        hard, _ = self.run_gate()
        self.assertIn("S2", self.rules(hard),
                      f"Doppel-Escape muss hart melden, kam: {hard}")

    def test_ungueltiges_json_bricht_hart(self):
        p = self.write("posts/a/index.html", article_page())
        txt = Path(p).read_text(encoding="utf-8").replace('"wordCount": 1200',
                                                          '"wordCount": 1200,,}')
        Path(p).write_text(txt, encoding="utf-8")
        hard, _ = self.run_gate()
        self.assertIn("S1", self.rules(hard))

    def test_build_datum_als_dateModified_bricht(self):
        """dateModified aus der Datei-Mtime wäre eine erfundene Frische."""
        today = gate.date.today().isoformat()
        ld = good_ld(**{"dateModified": f"{today}T23:59:59Z",
                        "datePublished": "2026-08-10T10:00:00Z"})
        self.write("posts/a/index.html", article_page(ld=ld))
        hard, _ = self.run_gate()
        self.assertTrue({"S3", "S4"} & self.rules(hard),
                        f"future/erfundene Änderung muss melden: {hard}")

    def test_og_image_masse_muessen_zur_datei_passen(self):
        txt = article_page().replace('og:image:width" content="1000"',
                                     'og:image:width" content="1200"')
        self.write("posts/a/index.html", txt)
        hard, _ = self.run_gate()
        self.assertIn("S5", self.rules(hard),
                      f"Maß-Widerspruch zur Bilddatei muss melden: {hard}")

    def test_preload_ohne_gerendertes_bild_bricht(self):
        txt = article_page(body_extra="").replace(
            "<body>", '<link rel=preload as=image imagesrcset="/i/ghost.avif 720w" '
                      'fetchpriority=high><body>')
        self.write("posts/a/index.html", txt)
        hard, _ = self.run_gate()
        self.assertIn("S9", self.rules(hard),
                      f"un-genutzter Preload muss melden: {hard}")

    def test_canonical_muttermal_wird_gesehen(self):
        txt = article_page().replace(
            '<link rel="canonical" href="https://example.org/posts/a/">',
            '<link rel="canonical" href="https://example.org/posts/a/">'
            '<link rel="canonical" href="https://example.org/anderes/">')
        self.write("posts/a/index.html", txt)
        hard, _ = self.run_gate()
        self.assertIn("S10", self.rules(hard))

    def test_archiv_seite_ohne_noindex_bricht(self):
        self.write("tags/eines/index.html",
                   '<html><head><link rel=canonical '
                   'href=https://example.org/tags/eines/></head><body></body></html>')
        hard, _ = self.run_gate()
        self.assertIn("S6", self.rules(hard),
                      f"Archiv ohne noindex muss melden: {hard}")

    def test_sitemap_muss_Money_Seite_enthalten_und_sauber_sein(self):
        """Nur eine Tag-URL statt der Money-Page: beide Funde müssen melden."""
        self.write("sitemap.xml",
                   '<?xml version="1.0"?><urlset><url>'
                   "<loc>https://example.org/tags/eines/</loc>"
                   "<lastmod>2026-09-01</lastmod></url></urlset>")
        hard, _ = self.run_gate()
        self.assertIn("S6", self.rules(hard),
                      f"Duplikat-URL + fehlende Money-Seite müssen melden: {hard}")
        self.assertTrue(any("Thin-Duplikat" in h for h in hard),
                        f"Archiv-URL in der Sitemap muss benannt werden: {hard}")
        self.assertTrue(any("fehlt in der Sitemap" in h for h in hard),
                        f"Money-Seite muss eingepflegt sein: {hard}")

    def test_buildZeitstempel_als_lastmod_bricht(self):
        """<lastmod> aus der Datei-Mtime wäre erfundene Frische bei jedem Deploy."""
        self.write("sitemap.xml",
                   '<?xml version="1.0"?><urlset><url>'
                   "<loc>https://example.org/posts/a/</loc>"
                   "<lastmod>2026-09-11T22:06:29+00:00</lastmod></url></urlset>")
        hard, _ = self.run_gate()
        self.assertIn("S7", self.rules(hard),
                      f"Build-Zeitstempel als lastmod muss melden: {hard}")

    def test_lastmod_muss_zum_Redaktionsdatum_passen(self):
        self.write("sitemap.xml",
                   '<?xml version="1.0"?><urlset><url>'
                   "<loc>https://example.org/posts/a/</loc>"
                   "<lastmod>2026-01-01</lastmod></url></urlset>")
        hard, _ = self.run_gate()
        self.assertTrue(any(h.startswith("S7") and "Redaktionsdatum" in h for h in hard),
                        f"abweichendes <lastmod> muss melden: {hard}")

    def test_robots_disallow_gegen_pinterest_bricht(self):
        self.write("robots.txt",
                   "User-agent: *\nAllow: /\n\n"
                   "User-agent: Pinterestbot\nDisallow: /\n\n"
                   "Sitemap: https://example.org/sitemap.xml\n")
        hard, _ = self.run_gate()
        self.assertIn("S8", self.rules(hard),
                      f"Pin-Crawl-Sperre muss melden: {hard}")

    def test_pwa_manifest_wird_eingefordert(self):
        """Service Worker ohne Manifest = nie ein Install-Prompt."""
        self.write("index.html",
                   '<html><head><meta name=robots content="index, follow">'
                   '<meta property="og:title" content="T">'
                   '<meta property="og:description" content="D">'
                   '<meta property="og:image" content="https://example.org/i/cover.jpg">'
                   '<meta property="og:image:width" content="1000">'
                   '<meta property="og:image:height" content="1500">'
                   '<meta property="og:image:alt" content="T">'
                   '<link rel=canonical href=https://example.org/>'
                   "</head><body></body></html>")
        hard, _ = self.run_gate()
        self.assertIn("S11", self.rules(hard),
                      f"fehlendes Manifest muss melden: {hard}")
        self.write("manifest.json", json.dumps({
            "id": self.base + "/", "name": "Test", "short_name": "Test",
            "description": "Testseite", "start_url": self.base + "/",
            "scope": self.base + "/", "display": "standalone",
            "theme_color": "#0E5A43",
            "icons": [{"src": "/i/cover.jpg", "sizes": "1000x1500",
                       "type": "image/jpeg", "purpose": "any"},
                      {"src": "/i/cover.jpg", "sizes": "1000x1500",
                       "type": "image/jpeg", "purpose": "maskable"}]}))
        self.write("index.html",
                   Path(os.path.join(self.pub, "index.html")).read_text(
                       encoding="utf-8").replace("</head>",
                       '<link rel="manifest" href="/manifest.json"></head>'))
        hard, _ = self.run_gate()
        self.assertNotIn("S11", self.rules(hard),
                         f"nach dem Nachrüsten muss S11 schweigen: {hard}")


class TemplateInvarianten(unittest.TestCase):
    """Die billige Dauer-Sicherung direkt am Template-Quelltext."""

    def read(self, rel):
        src = (ROOT / rel).read_text(encoding="utf-8")
        # Die Templates dokumentieren die Alt-Bugs in ihren Kommentarblöcken –
        # `"@id": {{ .Permalink | jsonify }}` steht dort zitiert. Eine Invariante
        # darf nicht auf zitiertem Code anschlagen, sonst ist sie sofort tot.
        return HUGO_COMMENT_RE.sub("", src)

    def test_schema_partials_bauen_json_ld_als_dict_mit_safejs(self):
        for rel in ("layouts/_partials/schema_article.html", "layouts/pillar/list.html"):
            src = self.read(rel)
            self.assertIn("| jsonify | safeJS", src,
                          f"{rel}: JSON-LD muss als dict → jsonify → safeJS gebaut werden")
            bad = re.findall(r"\{\{[^}]*\| jsonify \}\}", src)
            self.assertEqual([], bad,
                             f"{rel}: nacktes `| jsonify` in Ausgabe-Kontext erzeugt "
                             "doppelt escaptes JSON-LD")

    def test_sitemap_und_schema_nutzen_nie_die_datei_mtime(self):
        for rel in ("layouts/sitemap.xml", "layouts/_partials/sitemap_lastmod.html",
                    "layouts/_partials/schema_article.html"):
            self.assertNotIn(".Lastmod", self.read(rel),
                             f"{rel}: .Lastmod ist die Datei-Mtime = Deploy-Zeit und "
                             "damit eine erfundene Frische")

    def test_head_hat_preload_bremse_fuer_pager_und_archive(self):
        src = self.read("layouts/_partials/head.html")
        self.assertIn("$noPreload", src)
        self.assertIn('eq .Kind "term"', src)
        self.assertIn("PageNumber", src,
                      "Pager-Erkennung über .Paginator.PageNumber muss bleiben – "
                      ".RelPermalink ist auf Pager-Seiten die Basis-URL")

    def test_robots_txt_ermoeglicht_antwortmaschinen_und_sperrt_nicht(self):
        src = self.read("layouts/robots.txt")
        for bot in ("OAI-SearchBot", "ChatGPT-User", "PerplexityBot",
                    "Perplexity-User", "DuckAssistBot", "Claude-User",
                    "meta-externalfetcher"):
            self.assertIn(bot, src, f"{bot} muss in der Robots-Politik stehen")
        self.assertNotIn("Content-Signal: search=no", src,
                         "AI-Training darf abgelehnt werden, Antwortbezug nicht")

    def test_pillar_seiten_tragen_cover_und_preload_optout(self):
        for d in sorted((ROOT / "content" / "pillar").iterdir()):
            if not d.is_dir():
                continue
            fm = (d / "index.md").read_text(encoding="utf-8").split("---")[1]
            self.assertIn("cover:", f"{d.name}: {fm}")
            self.assertIn("preload: false", fm,
                          f"{d.name}: Pillar-Template rendert kein Cover-Bild – "
                          "ein Preload wäre ungenutzt (Lighthouse-Fund)")
            self.assertTrue((ROOT / "static" / "images" / "covers" / f"{d.name}.jpg").exists()
                            or (ROOT / "static" / "images" / "covers" /
                                f"pillar-{d.name}.jpg").exists(),
                            f"{d.name}: Cover-Bild fehlt")

    def test_pwa_artefakte_sind_im_repository(self):
        for rel in ("static/manifest.json", "static/images/pwa/icon-192.png",
                    "static/images/pwa/icon-512.png",
                    "static/images/pwa/icon-maskable-512.png"):
            self.assertTrue((ROOT / rel).is_file(), f"{rel} fehlt")
        man = json.loads((ROOT / "static" / "manifest.json").read_text(encoding="utf-8"))
        for key in ("name", "short_name", "start_url", "scope", "display",
                    "theme_color", "icons"):
            self.assertIn(key, man, f"Manifest: „{key}“ fehlt")
        head = self.read("layouts/_partials/extend_head.html")
        self.assertIn('rel="manifest"', head, "Manifest muss im Kopf verlinkt sein")


if __name__ == "__main__":
    unittest.main(verbosity=2)
