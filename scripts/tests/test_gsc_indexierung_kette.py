#!/usr/bin/env python3
"""Regressionstests der Search-Console-Kette (12.10.2026).

Hermetisch: kein Netz, kein Hugo, keine Google-Konten. Alle HTTP-Pfade sind
injiziert, alle Zeitstempel fest. Geprüft wird die KLASSE, nicht der Einzelfall:
jede Regel bekommt eine Sabotage-Probe (muss anschlagen) und, wo es eine
gültige Variante gibt, eine Gegenprobe (muss still bleiben).
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import gsc_indexierung as gi  # noqa: E402
import gsc_verifikations_guard as gv  # noqa: E402
import indexierbare_seiten as is_  # noqa: E402
import submit_indexnow as inow  # noqa: E402

BASE = "https://franksfinanzcheck.de/"
TOKEN_DATEI = "google0123456789abcdef.html"
FEST = dt.datetime(2026, 10, 12, 6, 0, tzinfo=dt.timezone.utc)


# ---------------------------------------------------------------- Fixtures
def baue_projekt(tmp: str, *, verifikation: bool = True, sitemap: str | None = None,
                 env: str = "production") -> tuple[str, str]:
    """Mini-Projekt mit root/ und public/; gibt (root, public) zurück."""
    root = os.path.join(tmp, "repo")
    pub = os.path.join(root, "public")
    for pfad in ("static", "content/suche", "content/posts/neu"):
        os.makedirs(os.path.join(root, pfad), exist_ok=True)
    os.makedirs(os.path.join(pub, "posts", "neu"), exist_ok=True)
    os.makedirs(os.path.join(pub, "werkzeuge", "scanner"), exist_ok=True)

    open(os.path.join(root, "hugo.toml"), "w", encoding="utf-8").write(
        f'baseURL = "{BASE}"\n[params]\n  env = "{env}"\n')
    open(os.path.join(root, "content", "suche", "index.md"), "w", encoding="utf-8").write(
        "---\ntitle: Suche\nrobotsNoIndex: true\nurl: /suche/\n---\n")

    home_jsonld = ('<script type="application/ld+json">{"@context":"https://schema.org",'
                   '"@type":"WebSite","name":"FF","url":"https://franksfinanzcheck.de/",'
                   '"inLanguage":"de-DE","publisher":{"@type":"Organization","name":"FF"}}'
                   "</script>")

    def seite(rel: str, url: str, robots: str = "index, follow", extra: str = "") -> None:
        ziel = os.path.join(pub, rel)
        os.makedirs(os.path.dirname(ziel), exist_ok=True)
        open(ziel, "w", encoding="utf-8").write(
            f'<!doctype html><html><head><meta name=robots content="{robots}">'
            f'<link rel=canonical href="{url}">{extra}</head>'
            f'<body><a href="/posts/neu/">Neu</a><a href="/werkzeuge/scanner/">Rechner</a>'
            "</body></html>")

    seite("index.html", BASE, extra=home_jsonld)
    seite("posts/neu/index.html", BASE + "posts/neu/")
    seite("werkzeuge/scanner/index.html", BASE + "werkzeuge/scanner/")
    seite("suche/index.html", BASE + "suche/", robots="noindex, follow")

    if verifikation:
        for pfad in (os.path.join(root, "static", TOKEN_DATEI),
                     os.path.join(pub, TOKEN_DATEI)):
            open(pfad, "w", encoding="utf-8").write(
                f"google-site-verification: {TOKEN_DATEI}\n")
    open(os.path.join(pub, "robots.txt"), "w", encoding="utf-8").write(
        "User-agent: *\nAllow: /\nDisallow: /go/\n\n"
        f"Sitemap: {BASE}sitemap.xml\n")
    open(os.path.join(pub, "sitemap.xml"), "w", encoding="utf-8").write(sitemap or (
        '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{BASE}</loc><lastmod>2026-10-12</lastmod>'
        '<changefreq>daily</changefreq><priority>1.0</priority></url>'
        f'<url><loc>{BASE}posts/neu/</loc><lastmod>2026-10-11</lastmod>'
        '<changefreq>weekly</changefreq><priority>0.8</priority></url>'
        f'<url><loc>{BASE}werkzeuge/scanner/</loc><lastmod>2026-10-02</lastmod>'
        '<changefreq>monthly</changefreq><priority>0.7</priority></url>'
        "</urlset>"))
    return root, pub


SA = {"client_email": "gsc@x.iam.gserviceaccount.com", "private_key": "PEM"}
ENV = {"GSC_SITE_URL": "sc-domain:franksfinanzcheck.de",
       "GSC_SERVICE_ACCOUNT_JSON": json.dumps(SA)}


def sitemap_xml() -> str:
    """Zwei Seiten mit redaktioneller Gewichtung – absichtlich falsch herum.

    Die Startseite trägt `priority` 1.0, steht aber ZULETZT in der Datei. Wer
    die Sitemap bloß in Dokumentreihenfolge abarbeitet, bekommt die
    Reihenfolge-Assertion in den Transport-Tests nicht erfüllt: `reihenfolge()`
    muss sortieren, nicht durchreichen.
    """
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>{BASE}posts/neu/</loc><lastmod>2026-10-11</lastmod>'
            '<changefreq>weekly</changefreq><priority>0.8</priority></url>'
            f'<url><loc>{BASE}</loc><lastmod>2026-10-12</lastmod>'
            '<changefreq>daily</changefreq><priority>1.0</priority></url>'
            '</urlset>')


def fake_api(stufe: str = "siteOwner", abdeckung: str = "Submitted and indexed",
             status: int = 200, mitzaehlen: list | None = None):
    """Fake-HTTP für Token, Property-Liste und urlInspection."""
    def http(method, url, headers, body):
        if url == gi.TOKEN_URL:
            return 200, {"access_token": "t-schreibend"}
        if url.endswith("/sites"):
            return 200, {"siteEntry": [{"siteUrl": ENV["GSC_SITE_URL"],
                                        "permissionLevel": stufe}]}
        if "urlInspection" in url:
            if mitzaehlen is not None:
                mitzaehlen.append(json.loads(body)["inspectionUrl"])
            return status, ({"inspectionResult": {"indexStatusResult": {
                "verdict": "PASS", "coverageState": abdeckung,
                "indexingState": "INDEXING_ALLOWED",
                "lastCrawlTime": "2026-10-11T10:00:00Z",
                "pageFetchState": "Successful", "robotsTxtState": "ALLOWED",
                "crawledAs": "Googlebot"}}} if status == 200
                else {"error": {"message": "abgelehnt"}})
        return 404, {}
    return http


# ---------------------------------------------------------------- Module
class IndexierbareSeitenTest(unittest.TestCase):
    """Eine Quelle für „welche Seiten sollen in den Index?"."""

    def test_selbsttest(self):
        self.assertEqual(is_._selftest(), 0)

    def test_queue_ist_abgeleitet_nicht_aufgeschrieben(self):
        """Ein neuer Seitentyp landet ohne Code-Änderung in der Queue."""
        with tempfile.TemporaryDirectory() as tmp:
            root, pub = baue_projekt(tmp)
            seiten, befunde = is_.hole_seiten(basis=pub)
            self.assertEqual(len(seiten), 3)
            self.assertEqual(befunde, [])
            pfade = [s.pfad for s in is_.reihenfolge(seiten)]
            self.assertIn("/werkzeuge/scanner/", pfade)   # früher: Namensliste
            self.assertEqual(pfade[0], "/")               # Wichtigkeit zuerst

    def test_bild_sitemap_wird_gezaehlt(self):
        xml = ('<?xml version="1.0"?><urlset '
               'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" '
               'xmlns:image="http://www.google.com/schemas/sitemap-image/1.1">'
               f'<url><loc>{BASE}posts/a/</loc><image:image>'
               f'<image:loc>{BASE}c.jpg</image:loc></image:image></url></urlset>')
        seiten = is_.parse_sitemap(xml)
        self.assertEqual(seiten[0].bilder, 1)

    def test_leere_sitemap_ist_fehler_nicht_leerlauf(self):
        xml = ('<?xml version="1.0"?><urlset '
               'xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"></urlset>')
        with self.assertRaises(is_.SitemapFehler):
            is_.hole_seiten(sitemap_url=BASE + "sitemap.xml",
                            http=lambda url, timeout=30: (200, xml))


class GscIndexierungTest(unittest.TestCase):
    """Die aktive Indexierungs-Anfrage (URL Inspection API)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.state = Path(self.tmp.name) / "state.json"
        self.urls = [BASE, BASE + "posts/neu/", BASE + "werkzeuge/scanner/"]

    def lauf(self, **kwargs):
        # Der Zähler muss VOR dem Bau des Fake-HTTP existieren: die Closure
        # hält die Liste, nicht ihren Namen.
        self.anfragen = []
        kwargs.setdefault("http", fake_api(mitzaehlen=self.anfragen))
        kwargs.setdefault("env", ENV)
        kwargs.setdefault("jetzt", FEST)
        kwargs.setdefault("sign", lambda m, k: b"x")
        kwargs.setdefault("state_pfad", self.state)
        kwargs.setdefault("urls", self.urls)
        kwargs.setdefault("warten", False)
        return gi.lauf(**kwargs)

    def test_selbsttest(self):
        self.assertEqual(gi._selftest(), 0)

    def test_sitemap_transport_ist_injizierbar(self):
        """KI-Probe #138: Das Injektions-Versprechen von `lauf()` gilt auch für die Sitemap.

        Regression gegen die erste Fassung: Sie ersetzte nur den API-Transport
        (`http`), die Sitemap ging weiter über `indexierbare_seiten._hole_http`
        ins Netz. Die KI-Probe meldete `create_connection → x:443`. Ein
        Selbsttest, der am Netz hängt, ist nicht reproduzierbar und bricht den
        Vertrag aus CONTENT-ENGINE-138.
        """
        erreicht = []

        def verbotener_transport(url, timeout=30):
            erreicht.append(url)
            self.fail("der echte Sitemap-Transport wurde erreicht")

        aufrufe = []

        def fake_sitemap(url):
            aufrufe.append(url)
            return 200, sitemap_xml()

        with patch.object(is_, "_hole_http", verbotener_transport):
            b = self.lauf(urls=None, sitemap_url="https://x/sitemap.xml",
                          sitemap_http=fake_sitemap)
        self.assertEqual(b["status"], "ok")
        self.assertEqual(aufrufe, ["https://x/sitemap.xml"],
                         "die Sitemap kam nicht über den injizierten Transport")
        self.assertEqual(erreicht, [], "der echte Transport wurde benutzt")
        self.assertEqual(b["seiten_indexierbar"], 2)
        self.assertEqual([a["url"] for a in b["angefragt"]], [BASE, BASE + "posts/neu/"])

    def test_ohne_injektion_bleibt_der_echte_transport_zustaendig(self):
        """Gegenprobe zur Injektion: Der Produktionsweg geht weiter durch `_hole_http`.

        Ohne diese Probe ließe sich die Naht auch „heilen", indem die Sitemap
        grundsätzlich über einen Attrappen-Transport läuft. Der Tageslauf mit
        `--live` sähe dann nie die ausgelieferte Sitemap und würde still einen
        erfundenen Bestand anfragen – grünes Gate, falsche Wirklichkeit.
        """
        aufrufe = []

        def transport(url, timeout=30):
            aufrufe.append(url)
            return 200, sitemap_xml()

        with patch.object(is_, "_hole_http", transport):
            b = self.lauf(urls=None, live=True)
        self.assertEqual(b["status"], "ok")
        self.assertEqual(aufrufe, [is_.live_sitemap_url()],
                         "--live läuft nicht über die ausgelieferte Sitemap")
        self.assertEqual([a["url"] for a in b["angefragt"]], [BASE, BASE + "posts/neu/"])

    def test_alle_drei_seiten_werden_angefragt(self):
        b = self.lauf()
        self.assertEqual(b["status"], "ok")
        self.assertEqual(len(b["angefragt"]), 3)
        self.assertEqual(self.anfragen[0], BASE)          # Wichtigkeit zuerst

    def test_kein_doppeltes_einreichen(self):
        self.lauf()
        b2 = self.lauf()
        self.assertEqual(b2["status"], "nichts_zu_tun")
        self.assertEqual(self.anfragen, [])

    def test_tageskontingent_wird_nicht_ueberschritten(self):
        b = self.lauf(nur_plan=True)
        self.assertLessEqual(len(b["queue"]), gi.TAGESKONTINGENT - gi.SICHERHEITSABSTAND)

    def test_verbrauchtes_kontingent_blockiert_die_queue(self):
        state = gi.lade_state(self.state)
        for i in range(gi.TAGESKONTINGENT):
            state["urls"][f"{BASE}p{i}/"] = {"zuletzt": FEST.strftime("%Y-%m-%dT%H:%M:%SZ")}
        gi.schreibe_state(state, self.state)
        b = self.lauf(nur_plan=True)
        self.assertEqual(b["queue"], [])
        self.assertTrue(any(s["grund"] == "Tageskontingent ausgeschöpft"
                            for s in b["uebersprungen"]))

    def test_eingeschraenkte_berechtigung_wird_erkannt(self):
        """„Eingeschränkt" reicht für den Lese-Import, nicht für eine Anfrage."""
        self.anfragen = []
        b = gi.lauf(http=fake_api(stufe="siteRestrictedUser", mitzaehlen=self.anfragen),
                    env=ENV, jetzt=FEST, sign=lambda m, k: b"x",
                    state_pfad=self.state, urls=self.urls, warten=False)
        self.assertEqual(b["status"], "keine_berechtigung")
        self.assertIn("Vollständig", b["grund"])
        self.assertEqual(self.anfragen, [])

    def test_quota_429_bricht_ab_statt_weiter_zu_traktieren(self):
        self.anfragen = []
        b = gi.lauf(http=fake_api(status=429, mitzaehlen=self.anfragen), env=ENV,
                    jetzt=FEST, sign=lambda m, k: b"x", state_pfad=self.state,
                    urls=self.urls, warten=False)
        self.assertEqual(b["status"], "kontingent_erschoepft")
        self.assertEqual(len(self.anfragen), 1)

    def test_nicht_indexierte_seiten_werden_gezaehlt(self):
        self.anfragen = []
        b = gi.lauf(http=fake_api(abdeckung="Crawled - currently not indexed",
                                  mitzaehlen=self.anfragen), env=ENV, jetzt=FEST,
                    sign=lambda m, k: b"x", state_pfad=self.state,
                    urls=self.urls, warten=False)
        self.assertEqual(b["nicht_indexiert"], 3)
        self.assertEqual(b["indexiert"], 0)

    def test_zustand_enthaelt_kein_geheimnis(self):
        self.lauf()
        roh = self.state.read_text(encoding="utf-8")
        self.assertNotIn("t-schreibend", roh)
        self.assertNotIn("PEM", roh)
        self.assertIn("coverageState", roh)

    def test_inhaltsaenderung_bricht_die_wiedervorlage(self):
        self.lauf()
        state = gi.lade_state(self.state)
        state["urls"][BASE + "posts/neu/"]["lastmod_angefragt"] = "2026-01-01"
        gi.schreibe_state(state, self.state)
        b = self.lauf(jetzt=FEST + dt.timedelta(days=2))
        self.assertEqual(self.anfragen, [BASE + "posts/neu/"])

    def test_ohne_zugang_nicht_konfiguriert(self):
        b = self.lauf(env={}, http=fake_api())
        self.assertEqual(b["status"], "nicht_konfiguriert")

    def test_kaputter_zustand_ist_fail_closed(self):
        self.state.write_text("{ kaputt", encoding="utf-8")
        with self.assertRaises(gi.IndexierungsFehler):
            gi.lade_state(self.state)

    def test_dauerhaft_abgelehnte_url_stoppt_die_automatik(self):
        e = {"zuletzt": FEST.strftime("%Y-%m-%dT%H:%M:%SZ"), "lastmod_angefragt": "",
             "lastmod": "", "fehler_zaehler": 3}
        faellig, _grund = gi.ist_fällig(e, FEST.date() + dt.timedelta(days=400))
        self.assertFalse(faellig)


class VerifikationsGuardTest(unittest.TestCase):
    """V1–V13: Zugangsschicht zur Search Console."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root, self.pub = baue_projekt(self.tmp.name)

    def regeln(self) -> set:
        f, _ = gv.pruefe(self.pub, self.root)
        return {r for r, _w, _t in f.hart}

    def test_selbsttest(self):
        self.assertEqual(gv._selftest(), 0)

    def test_gesunder_stand_ist_gruen(self):
        f, bericht = gv.pruefe(self.pub, self.root)
        self.assertEqual(f.hart, [])
        self.assertEqual(bericht["sitemap_eintraege"], 3)
        self.assertEqual(bericht["verifikations_dateien"], [TOKEN_DATEI])

    def test_besitznachweis_muss_da_und_richtig_sein(self):
        os.remove(os.path.join(self.pub, TOKEN_DATEI))
        self.assertIn("V1", self.regeln())

        baue_projekt(self.tmp.name, verifikation=False)
        self.assertIn("V1", self.regeln())

    def test_falscher_inhalt_im_besitznachweis(self):
        open(os.path.join(self.pub, TOKEN_DATEI), "w", encoding="utf-8").write(
            "google-site-verification: googleXXXXXXXXXXXXXXXX.html\n")
        self.assertIn("V1", self.regeln())

    def test_googlebot_sperre_ist_hart(self):
        open(os.path.join(self.pub, "robots.txt"), "w", encoding="utf-8").write(
            f"User-agent: *\nDisallow: /\nSitemap: {BASE}sitemap.xml\n")
        self.assertIn("V2", self.regeln())

    def test_trainingsbot_sperre_ist_erlaubt(self):
        """Google-Extended (Training) darf zu bleiben – Antwort-Bots nicht."""
        open(os.path.join(self.pub, "robots.txt"), "w", encoding="utf-8").write(
            "User-agent: Google-Extended\nDisallow: /\n\nUser-agent: *\nAllow: /\n"
            f"Sitemap: {BASE}sitemap.xml\n")
        self.assertNotIn("V2", self.regeln())

    def test_sitemap_hinweis_muss_stimmen(self):
        open(os.path.join(self.pub, "robots.txt"), "w", encoding="utf-8").write(
            "User-agent: *\nAllow: /\n")
        self.assertIn("V3", self.regeln())

    def test_fremder_host_in_der_sitemap(self):
        offen = open(os.path.join(self.pub, "sitemap.xml"), encoding="utf-8").read()
        open(os.path.join(self.pub, "sitemap.xml"), "w", encoding="utf-8").write(
            offen.replace(BASE + "posts/neu/", "https://example.com/posts/neu/"))
        self.assertIn("V4", self.regeln())

    def test_noindex_seite_in_der_sitemap(self):
        open(os.path.join(self.pub, "sitemap.xml"), "w", encoding="utf-8").write(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>{BASE}suche/</loc></url></urlset>')
        self.assertIn("V5", self.regeln())

    def test_canonical_muss_selbstreferenziell_sein(self):
        ziel = os.path.join(self.pub, "posts", "neu", "index.html")
        text = open(ziel, encoding="utf-8").read()
        open(ziel, "w", encoding="utf-8").write(
            text.replace(BASE + "posts/neu/", BASE + "alt/"))
        self.assertIn("V6", self.regeln())

    def test_verifikationsdatei_ist_kein_inhalt(self):
        open(os.path.join(self.pub, "sitemap.xml"), "w", encoding="utf-8").write(
            '<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f'<url><loc>{BASE}{TOKEN_DATEI}</loc></url></urlset>')
        self.assertIn("V7", self.regeln())

    def test_entity_nachweis_auf_der_startseite(self):
        open(os.path.join(self.pub, "index.html"), "w", encoding="utf-8").write(
            '<!doctype html><html><head><meta name=robots content="index, follow">'
            f'<link rel=canonical href="{BASE}"></head><body></body></html>')
        self.assertIn("V8", self.regeln())

    def test_noindex_braucht_einen_erklaerten_grund(self):
        os.makedirs(os.path.join(self.pub, "transparenz"), exist_ok=True)
        open(os.path.join(self.pub, "transparenz", "index.html"), "w",
             encoding="utf-8").write(
            '<!doctype html><html><head><meta name=robots content="noindex, follow">'
            f'<link rel=canonical href="{BASE}transparenz/"></head><body></body></html>')
        self.assertIn("V9", self.regeln())

    def test_erklaertes_noindex_bleibt_still(self):
        """`robotsNoIndex: true` im Frontmatter ist die redaktionelle Antwort."""
        os.makedirs(os.path.join(self.pub, "suche"), exist_ok=True)
        self.assertNotIn("V9", self.regeln())

    def test_funktionsflaeche_aus_static_ist_kein_inhalt(self):
        """Kalender/OAuth liegen in static/ und tragen ihr noindex selbst."""
        os.makedirs(os.path.join(self.root, "static", "kalender"), exist_ok=True)
        inhalt = ('<!doctype html><html><head><meta name=robots content="noindex, follow">'
                  f'<link rel=canonical href="{BASE}kalender/"></head><body></body></html>')
        open(os.path.join(self.root, "static", "kalender", "index.html"), "w",
             encoding="utf-8").write(inhalt)
        os.makedirs(os.path.join(self.pub, "kalender"), exist_ok=True)
        open(os.path.join(self.pub, "kalender", "index.html"), "w",
             encoding="utf-8").write(inhalt)
        self.assertNotIn("V9", self.regeln())

    def test_nicht_produktions_build_ist_nicht_indexierbar(self):
        """Ein Vorschau-Build darf kein V9-Feuerwerk auslösen."""
        _root, _pub = baue_projekt(self.tmp.name, env="development")
        f, bericht = gv.pruefe(self.pub, self.root)
        self.assertEqual(bericht["noindex_ohne_grund"], 0)
        self.assertNotIn("V9", {r for r, _w, _t in f.hart})


class VerifikationsLiveTest(unittest.TestCase):
    """V13: die ausgelieferte Wahrheit, mit injiziertem HTTP (kein Netz)."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root, self.pub = baue_projekt(self.tmp.name)
        self.antworten = {
            BASE + TOKEN_DATEI: (200, f"google-site-verification: {TOKEN_DATEI}\n", {}),
            BASE + "robots.txt": (200, open(os.path.join(self.pub, "robots.txt"),
                                            encoding="utf-8").read(), {}),
            BASE + "sitemap.xml": (200, open(os.path.join(self.pub, "sitemap.xml"),
                                             encoding="utf-8").read(), {}),
            BASE: (200, open(os.path.join(self.pub, "index.html"), encoding="utf-8").read(), {}),
            BASE + "posts/neu/": (200, open(os.path.join(self.pub, "posts", "neu", "index.html"),
                                            encoding="utf-8").read(), {}),
            BASE + "werkzeuge/scanner/": (200, open(
                os.path.join(self.pub, "werkzeuge", "scanner", "index.html"),
                encoding="utf-8").read(), {}),
        }

    def pruefe(self, antworten=None):
        a = antworten or self.antworten
        return gv.pruefe_live(self.pub, self.root,
                              http=lambda url, timeout=30: a.get(url, (404, "", {})))

    def test_live_gruen(self):
        f, live = self.pruefe()
        self.assertEqual(f.hart, [])
        self.assertGreaterEqual(len(live["geprueft"]), 5)

    def test_verifikationsdatei_live_404(self):
        a = dict(self.antworten)
        a[BASE + TOKEN_DATEI] = (404, "", {})
        f, _ = self.pruefe(a)
        self.assertTrue(any(r == "V13" and "Besitznachweis" in t for r, _w, t in f.hart))

    def test_weitergeleitete_sitemap_wird_abgelehnt(self):
        a = dict(self.antworten)
        a[BASE + "sitemap.xml"] = (301, "", {"Location": BASE + "sitemap-index.xml"})
        f, _ = self.pruefe(a)
        self.assertTrue(any("weitergeleitete Sitemaps" in t for _r, _w, t in f.hart))

    def test_noindex_live_ist_widerspruch(self):
        a = dict(self.antworten)
        text = open(os.path.join(self.pub, "posts", "neu", "index.html"),
                    encoding="utf-8").read()
        a[BASE + "posts/neu/"] = (200, text.replace("index, follow", "noindex, follow"), {})
        f, _ = self.pruefe(a)
        self.assertTrue(any("noindex" in t for _r, _w, t in f.hart))

    def test_canonical_drift_live(self):
        a = dict(self.antworten)
        text = open(os.path.join(self.pub, "posts", "neu", "index.html"),
                    encoding="utf-8").read()
        a[BASE + "posts/neu/"] = (200, text.replace(BASE + "posts/neu/", BASE + "alt/"), {})
        f, _ = self.pruefe(a)
        self.assertTrue(any("Canonical" in t for _r, _w, t in f.hart))


class IndexNowTest(unittest.TestCase):
    """IndexNow: dieselbe Quelle, anderer Suchmaschinen-Kreis."""

    def test_selbsttest(self):
        self.assertEqual(inow._selftest(), 0)

    def test_schluessel_und_datei_stimmen_ueberein(self):
        key = inow.get_key()
        self.assertEqual(inow.pruefe_schluesseldatei(key), [])

    def test_queue_kommt_aus_der_sitemap(self):
        xml = ('<?xml version="1.0"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
               f'<url><loc>{BASE}werkzeuge/scanner/</loc><priority>0.7</priority></url>'
               f'<url><loc>{BASE}</loc><priority>1.0</priority></url></urlset>')
        urls, befunde = inow.queue_bauen(
            sitemap_url=BASE + "sitemap.xml",
            http=lambda url, timeout=30: (200, xml))
        self.assertEqual(befunde, [])
        self.assertEqual(urls, [BASE, BASE + "werkzeuge/scanner/"])

    def test_github_io_altlast_wird_entsorgt(self):
        state = {"https://frank-hartung.github.io/projekt/posts/a/",
                 BASE + "posts/a/"}
        behalten, fremd = inow.bereinige_zustand(state, "franksfinanzcheck.de")
        self.assertEqual(fremd, 1)
        self.assertEqual(behalten, {BASE + "posts/a/"})

    def test_batch_grenze(self):
        urls = [f"{BASE}p{i}/" for i in range(inow.MAX_URLS_PRO_ANFRAGE + 3)]
        teile = inow.batches(urls)
        self.assertEqual([len(t) for t in teile], [inow.MAX_URLS_PRO_ANFRAGE, 3])


class DrahtungTest(unittest.TestCase):
    """Die Kette muss verdrahtet sein, nicht nur vorhanden."""

    def test_guard_steht_im_governance_vertrag(self):
        import governance_contract as gc
        for wache in ("indexierbare_seiten.py", "gsc_verifikations_guard.py",
                      "gsc_indexierung.py", "submit_indexnow.py"):
            self.assertIn(wache, gc.GUARDS,
                          f"{wache} fehlt in GUARDS – ihr Selbsttest liefe in "
                          "keinem Qualitäts-Gate mit (C6)")

    def test_tageslauf_ist_eingerichtet(self):
        wf = (ROOT / ".github" / "workflows" / "gsc-import.yml").read_text(encoding="utf-8")
        self.assertIn("scripts/gsc_import.py", wf)
        self.assertIn("scripts/gsc_indexierung.py", wf)
        self.assertIn("scripts/gsc_verifikations_guard.py --nur-live", wf)
        self.assertIn("scripts/submit_indexnow.py", wf)
        self.assertIn("schedule:", wf)

    def test_deploy_prueft_verifikation_vor_der_auslieferung(self):
        deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        self.assertIn("gsc_verifikations_guard.py", deploy)
        # Die Wache muss VOR dem Pages-Deployment stehen, sonst ist sie Deko.
        self.assertLess(deploy.index("gsc_verifikations_guard.py"),
                        deploy.index("Deploy auf gh-pages"))

    def test_gsc_zustand_loest_keinen_livegang_aus(self):
        """Ein tägliches Lebenszeichen darf die Deploy-Queue nicht verstopfen."""
        import re
        deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(encoding="utf-8")
        muster = re.search(r"STATE_ONLY='([^']+)'", deploy).group(1)
        self.assertTrue(re.match(muster, "data/gsc_indexierung_state.json"))
        self.assertTrue(re.match(muster, "data/gsc/tagesdaten.jsonl"))
        # Gegenprobe: echter Inhalt bleibt deploy-relevant
        self.assertFalse(re.match(muster, "content/posts/x/index.md"))


if __name__ == "__main__":
    unittest.main()
