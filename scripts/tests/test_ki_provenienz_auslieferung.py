#!/usr/bin/env python3
"""Gegenproben für #1028: Endstand, Identität und tatsächliche Signalwerte.

Alle Tests sind offline und benutzen kleine isolierte Bauprodukte. Ein grüner
Lauf beweist weder KI-Herkunft noch die technische Markierung des Anbieters.
"""
from __future__ import annotations

import copy
import json
import os
import re
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import patch

from scripts import ki_provenienz as kp
from scripts import ki_provenienz_gate as gate
from scripts import ki_kennzeichnung_gate as kennzeichnung

ROOT = kp.ROOT
ATOM = "http://www.w3.org/2005/Atom"
MEDIA = "http://search.yahoo.com/mrss/"
FFKI = kp.NAMESPACE
BASE = "https://example.test/base/"
PAGE = BASE + "posts/ziel/"
HINWEIS = BASE + "impressum/#ki-hinweis"
COVER = BASE + "images/covers/probe.jpg"
ART = "trainedAlgorithmicMedia"


def q(namespace: str, name: str) -> str:
    return f"{{{namespace}}}{name}"


class BauproduktFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.bau = self.root / "public"
        self.post = self.root / "content/posts/quelle/index.md"
        self.post.parent.mkdir(parents=True)
        (self.root / "hugo.toml").write_text(f'baseURL = "{BASE}"\n', encoding="utf-8")
        self.page = self.bau / "posts/ziel/index.html"
        self.page.parent.mkdir(parents=True)
        self.quelle()
        self.html()
        self.rss = ET.Element("rss", {"version": "2.0"})
        self.kanal = ET.SubElement(self.rss, "channel")
        ET.SubElement(self.kanal, q(ATOM, "link"), {"rel": "describedby", "href": HINWEIS})
        self.item = ET.SubElement(self.kanal, "item")
        ET.SubElement(self.item, "guid").text = PAGE
        ET.SubElement(self.item, "link").text = PAGE + "?utm_source=pinterest"
        ET.SubElement(self.item, "description").text = kp.social_hinweis("Beispiel", ki_text=True)
        ET.SubElement(self.item, q(ATOM, "link"), {"rel": "describedby", "href": HINWEIS})
        ET.SubElement(self.item, q(FFKI, "ai-generated")).text = "true"
        ET.SubElement(self.item, q(FFKI, "ai-generated-scope")).text = "text,audio"
        self.feed()

    def quelle(self, *, text: bool = True, bild: bool = False, extra: str = ""):
        cover = ("cover:\n  image: images/covers/probe.jpg\n  ai_generated: true\n"
                 f"  ki_pruefung:\n    digital_source_type: {ART}\n") if bild else ""
        self.post.write_text("---\ntitle: Probe\nslug: ziel\n"
                             f"ai_generated: {'true' if text else 'false'}\n"
                             f"{cover}{extra}---\nInhalt\n", encoding="utf-8")

    def html(self, *, text: bool = True, bild: bool = False):
        bereiche = (["text"] if text else []) + (["image"] if bild else []) + ["audio"]
        meta = '<meta name="ai-generated" content="true">' if text else ""
        scope = ','.join(bereiche)
        credit = ("Mit KI erstellt oder bearbeitet. " if text else "")
        credit += ("Cover mit KI erstellt oder bearbeitet. " if bild else "")
        credit += "Tonspur maschinell erzeugt."
        schema = json.dumps({"@type": "Article", "creditText": credit}, ensure_ascii=False)
        label = '<strong data-ff-ki-label>Mit KI erstellt oder bearbeitet</strong>' if text else ""
        image = (f'<img src="{COVER}?v=123" data-ai-generated="true" '
                 f'data-digital-source-type="{ART}">'
                 '<span data-ff-ki-image-label>Bild mit KI erstellt oder bearbeitet</span>') if bild else ""
        html = (f'<html><head>{meta}<meta name="ai-generated-scope" content="{scope}">'
                f'<link rel="describedby" href="{HINWEIS}">'
                f'<script type="application/ld+json">{schema}</script></head><body>'
                f'{label}{image}<div class="ff-voice-slot">'
                '<span data-ff-ki-voice-label aria-hidden="true">KI-Stimme</span>'
                '</div></body></html>')
        self.page.write_text(html, encoding="utf-8")

    def feed(self, root=None):
        ET.ElementTree(root if root is not None else self.rss).write(
            self.bau / "index.xml", encoding="utf-8", xml_declaration=True)

    def m5(self):
        return gate.regel_m5(self.bau, self.root)

    def m14(self):
        return gate.regel_m1_m4(self.bau, self.root)[0]

    def bild_ergaenzen(self):
        self.quelle(bild=True)
        self.html(bild=True)
        self.item.find(q(FFKI, "ai-generated-scope")).text = "text,image,audio"
        self.item.find("description").text = kp.social_hinweis("Beispiel", ki_text=True, ki_bild=True)
        medium = ET.SubElement(self.item, q(MEDIA, "content"), {"url": COVER})
        credit = ET.SubElement(medium, q(MEDIA, "credit"), {
            "role": "digitalsourcetype", "scheme": kp.IPTC_VOKABULAR})
        credit.text = ART
        self.feed()


class FeedIdentitaetTests(BauproduktFixture):
    def test_gesunder_feed_nutzt_slug_und_utm_der_gebauten_seite(self):
        self.assertEqual(kp.seiten(self.root)[0].basis, "posts/ziel")
        self.assertEqual(self.m5(), ([], 1, []))
        self.assertEqual(self.m14(), [])

    def test_unbekanntes_unmarkiertes_item_ist_fund_statt_nur_kennzahl(self):
        fremd = copy.deepcopy(self.item)
        fremd.find("guid").text = BASE + "posts/neu/"
        fremd.find("link").text = BASE + "posts/neu/"
        for e in list(fremd):
            if e.tag.startswith("{" + FFKI + "}"):
                fremd.remove(e)
        self.kanal.append(fremd)
        self.feed()
        funde, anzahl, unbekannt = self.m5()
        self.assertEqual(anzahl, 1)
        self.assertEqual(len(unbekannt), 1)
        self.assertTrue(any("neu" in f["text"] and f["regel"] == "M5" for f in funde))
        self.assertEqual(gate.main_exit_werkzeug(funde), 1)

    def test_gleicher_slug_ersetzt_nie_host_und_vollstaendigen_pfad(self):
        falsch = ["https://fremd.test/base/posts/ziel/",
                  "https://example.test/andere-sektion/ziel/",
                  "https://example.test/base/fremd/ziel/",
                  "https://example.test.evil.test/base/posts/ziel/",
                  "https://user@example.test/base/posts/ziel/",
                  "https://example.test/base/posts/%2e%2e/ziel/"]
        for url in falsch:
            with self.subTest(url=url):
                root = copy.deepcopy(self.rss)
                item = root.find("./channel/item")
                item.find("guid").text = url
                item.find("link").text = url
                self.feed(root)
                funde, anzahl, unbekannt = self.m5()
                self.assertEqual(anzahl, 0)
                self.assertTrue(unbekannt)
                self.assertTrue(any(f["regel"] == "M5" for f in funde))

    def test_guid_link_und_doppelte_items_muessen_eindeutig_sein(self):
        for fall in ("anderer-link", "fehlender-link", "doppelte-guid", "guid-query", "duplikat"):
            with self.subTest(fall=fall):
                root = copy.deepcopy(self.rss)
                kanal = root.find("channel")
                item = kanal.find("item")
                if fall == "anderer-link":
                    item.find("link").text = BASE + "posts/andere/"
                elif fall == "fehlender-link":
                    item.remove(item.find("link"))
                elif fall == "doppelte-guid":
                    ET.SubElement(item, "guid").text = PAGE
                elif fall == "guid-query":
                    item.find("guid").text = PAGE + "?tracking=1"
                else:
                    kanal.append(copy.deepcopy(item))
                self.feed(root)
                self.assertTrue(self.m5()[0])
                self.assertTrue(self.m5()[2])

    def test_ungueltiger_oder_leerer_feed_ist_nicht_gruen(self):
        for inhalt in (b"<rss/>", b"<rss><channel/><channel/></rss>", b"<rss>"):
            with self.subTest(inhalt=inhalt):
                (self.bau / "index.xml").write_bytes(inhalt)
                self.assertTrue(any(f["regel"] == "M5" for f in self.m5()[0]))
        self.kanal.remove(self.item)
        self.feed()
        self.assertTrue(any("leer" in f["text"] for f in self.m5()[0]))
        self.quelle(extra="hiddenInRss: true\n")
        self.assertEqual(self.m5()[0], [])

    def test_fehlerhafte_basiskonfiguration_ist_werkzeugfehler(self):
        (self.root / "hugo.toml").unlink()
        funde, _, _ = self.m5()
        self.assertEqual(gate.main_exit_werkzeug(funde), 2)
        self.assertEqual(funde[0]["regel"], "W0")


class FeedWerteTests(BauproduktFixture):
    def test_false_leer_fehlend_und_doppelt_sind_keine_true_angabe(self):
        for wert in ("false", "", "fehlt", "doppelt"):
            with self.subTest(wert=wert):
                root = copy.deepcopy(self.rss)
                item = root.find("./channel/item")
                element = item.find(q(FFKI, "ai-generated"))
                if wert == "fehlt":
                    item.remove(element)
                elif wert == "doppelt":
                    ET.SubElement(item, q(FFKI, "ai-generated")).text = "true"
                else:
                    element.text = wert
                self.feed(root)
                self.assertTrue(any("ffki:ai-generated " in f["text"] for f in self.m5()[0]))

    def test_false_oder_true_ohne_text_ist_keine_neutrale_angabe(self):
        self.quelle(text=False)
        self.html(text=False)
        self.item.remove(self.item.find(q(FFKI, "ai-generated")))
        self.item.find("description").text = "Beispiel"
        self.item.find(q(FFKI, "ai-generated-scope")).text = "audio"
        self.feed()
        self.assertEqual(self.m5()[0], [])
        for wert in ("false", "true"):
            with self.subTest(wert=wert):
                root = copy.deepcopy(self.rss)
                ET.SubElement(root.find("./channel/item"), q(FFKI, "ai-generated")).text = wert
                self.feed(root)
                self.assertTrue(any("ffki:ai-generated " in f["text"] for f in self.m5()[0]))

    def test_scope_und_verweise_muessen_genau_stimmen(self):
        for fall in ("unbekannter-scope", "doppelter-scope", "falsches-item-ziel",
                     "falsches-kanal-ziel", "doppeltes-ziel"):
            with self.subTest(fall=fall):
                root = copy.deepcopy(self.rss)
                kanal = root.find("channel")
                item = kanal.find("item")
                if fall == "unbekannter-scope":
                    item.find(q(FFKI, "ai-generated-scope")).text = "text,audio,video"
                elif fall == "doppelter-scope":
                    ET.SubElement(item, q(FFKI, "ai-generated-scope")).text = "text,audio"
                elif fall == "falsches-item-ziel":
                    item.find(q(ATOM, "link")).set("href", "https://example.test/falsch")
                elif fall == "falsches-kanal-ziel":
                    kanal.find(q(ATOM, "link")).set("href", "https://example.test/falsch")
                else:
                    ET.SubElement(item, q(ATOM, "link"), {"rel": "describedby", "href": HINWEIS})
                self.feed(root)
                self.assertTrue(self.m5()[0])

    def test_iptc_credit_muss_im_richtigen_medium_mit_wert_stehen(self):
        self.bild_ergaenzen()
        self.assertEqual(self.m5()[0], [], "das echte Template verschachtelt media:credit")
        self.assertTrue(kp.feed_items(self.bau / "index.xml")[0]["media_credit"])
        for fall in ("wert", "rolle", "schema", "bild", "direkt", "doppelt"):
            with self.subTest(fall=fall):
                root = copy.deepcopy(self.rss)
                item = root.find("./channel/item")
                medium = item.find(q(MEDIA, "content"))
                credit = medium.find(q(MEDIA, "credit"))
                if fall == "wert":
                    credit.text = "algorithmicMedia"
                elif fall == "rolle":
                    credit.set("role", "credit")
                elif fall == "schema":
                    credit.set("scheme", "https://falsch.test/")
                elif fall == "bild":
                    medium.set("url", BASE + "images/anderes.jpg")
                elif fall == "direkt":
                    medium.remove(credit)
                    item.append(credit)
                else:
                    medium.append(copy.deepcopy(credit))
                self.feed(root)
                self.assertTrue(any("media:credit" in f["text"] for f in self.m5()[0]))

    def test_nach_erster_pruefung_geaenderter_feed_faellt_bei_endpruefung_auf(self):
        self.assertEqual(self.m5()[0], [])
        self.item.find(q(FFKI, "ai-generated")).text = "false"
        self.feed()
        self.assertEqual(gate.main_exit_werkzeug(self.m5()[0]), 1)

    def test_description_fallback_muss_vorne_eindeutig_und_inhaltlich_passend_sein(self):
        self.bild_ergaenzen()
        self.assertEqual(self.m5()[0], [])
        for fall in ("fehlt", "doppelt", "ohne-text", "ohne-bild", "hint-am-ende",
                     "zu-lang", "hinweis-doppelt"):
            with self.subTest(fall=fall):
                root = copy.deepcopy(self.rss)
                item = root.find("./channel/item")
                desc = item.find("description")
                if fall == "fehlt":
                    item.remove(desc)
                elif fall == "doppelt":
                    ET.SubElement(item, "description").text = desc.text
                elif fall == "ohne-text":
                    desc.text = kp.social_hinweis("Beispiel", ki_bild=True)
                elif fall == "ohne-bild":
                    desc.text = kp.social_hinweis("Beispiel", ki_text=True)
                elif fall == "zu-lang":
                    desc.text = kp.social_hinweis("X" * 501, ki_text=True, ki_bild=True)
                elif fall == "hinweis-doppelt":
                    desc.text = kp.social_hinweis("Beispiel " + kp.SOCIAL_TEXT,
                                                   ki_text=True, ki_bild=True)
                else:
                    desc.text = "Beispiel " + kp.social_hinweis("", ki_text=True, ki_bild=True)
                self.feed(root)
                self.assertTrue(any("description" in f["text"] for f in self.m5()[0]))

    def test_unbelegte_positive_beschreibung_ist_widerspruch(self):
        self.quelle(text=False)
        self.html(text=False)
        self.item.remove(self.item.find(q(FFKI, "ai-generated")))
        self.item.find(q(FFKI, "ai-generated-scope")).text = "audio"
        self.feed()
        self.assertTrue(any("nicht deklarierte" in f["text"] for f in self.m5()[0]))


class DokumentTests(BauproduktFixture):
    def test_meta_und_describedby_pruefen_werte_und_wirkliches_ziel(self):
        original = self.page.read_text(encoding="utf-8")
        proben = [
            original.replace('content="true"', 'content="false"', 1),
            original.replace('</head>', '<meta name="ai-generated" content="true"></head>'),
            original.replace('content="text,audio"', 'content="text,audio,video"'),
            original.replace(HINWEIS, BASE + 'falsch/#ki-hinweis'),
            original.replace(HINWEIS, 'impressum/#ki-hinweis'),
        ]
        for text in proben:
            with self.subTest(text=text[:130]):
                self.page.write_text(text, encoding="utf-8")
                self.assertTrue(any(f["regel"] == "M1" for f in self.m14()))

    def test_falscher_oder_versteckter_marker_ist_keine_sichtbare_angabe(self):
        original = self.page.read_text(encoding="utf-8")
        label = '<strong data-ff-ki-label>Mit KI erstellt oder bearbeitet</strong>'
        ersatz = [f'<!-- {label} -->', '<strong data-ff-ki-label></strong>',
                  '<strong data-ff-ki-label>anderer Text</strong>',
                  '<strong data-ff-ki-label hidden>Mit KI erstellt oder bearbeitet</strong>',
                  '<div style="display: none">' + label + '</div>',
                  '<div class="sr-only">' + label + '</div>']
        for fake in ersatz:
            with self.subTest(fake=fake):
                self.page.write_text(original.replace(label, fake), encoding="utf-8")
                self.assertTrue(any(f["regel"] == "M4" and "text" in f["text"]
                                    for f in self.m14()))

    def test_entferntes_oder_korruptes_article_schema_ist_nicht_mehr_gruen(self):
        original = self.page.read_text(encoding="utf-8")
        schema = re.search(r'<script type="application/ld\+json">.*?</script>', original).group(0)
        for ersatz in ("", '<script type="application/ld+json">{broken}</script>',
                       '<!-- ' + schema + ' -->',
                       schema.replace('Mit KI erstellt oder bearbeitet.', 'Ohne Textangabe.')):
            with self.subTest(ersatz=ersatz[:40]):
                self.page.write_text(original.replace(schema, ersatz), encoding="utf-8")
                self.assertTrue(any(f["regel"] == "M1" and "Schema" in f["text"]
                                    or f["regel"] == "M1" and "Article-JSON-LD" in f["text"]
                                    for f in self.m14()))

    def test_cover_attribute_muessen_am_originalbild_mit_richtigem_wert_stehen(self):
        self.bild_ergaenzen()
        self.assertEqual(self.m14(), [])
        original = self.page.read_text(encoding="utf-8")
        for text in (original.replace('data-ai-generated="true"', 'data-ai-generated="false"'),
                     original.replace(ART, 'algorithmicMedia'),
                     original.replace(COVER, BASE + 'images/falsch.jpg'),
                     original.replace('data-ai-generated="true"', 'srcset="anders.jpg 1x" data-ai-generated="true"')):
            with self.subTest(text=text[:100]):
                self.page.write_text(text, encoding="utf-8")
                self.assertTrue(any(f["regel"] == "M1" and "KI-Cover" in f["text"]
                                    for f in self.m14()))


class SocialVariantenGateTests(BauproduktFixture):
    def test_alte_social_variante_wird_gemeldet_aber_nicht_blind_geloescht(self):
        self.quelle(bild=True)
        variante = self.root / "static/images/social/quelle-4x5.jpg"
        variante.parent.mkdir(parents=True)
        variante.write_bytes(b"unbekannte alte datei")
        funde = gate.regel_m6(self.root)
        self.assertTrue(any(f["regel"] == "M6" and "Social-Variante" in f["text"]
                            for f in funde))
        kp.heilen(self.root)
        self.assertEqual(variante.read_bytes(), b"unbekannte alte datei")
        self.assertTrue(any("Social-Variante" in f["text"] for f in gate.regel_m6(self.root)))


class WachenZustandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / "data").mkdir()
        self.register = self.root / "data/ki_kennzeichnung.yaml"
        self.register.write_text("maschinell:\n  - bot\nmenschlich:\n  - alt\n", encoding="utf-8")
        (self.root / "data/recht-fristen.yaml").write_text(
            f'fristen:\n  - id: {gate.FRIST_ID}\n    faellig_am: "2026-12-02"\n', encoding="utf-8")
        self.state = self.root / kp.STATE
        self.state.write_text(json.dumps({"frist": "2026-12-02", "funde": 0,
                                         "ungeklaert_erstmals": {"alt": "2026-11-07"}}),
                              encoding="utf-8")
        self.heilung = {"eingriffe": [], "eskalation": [], "funde_nachher": [],
                        "revision": "probe", "kennzahlen": {}}

    def wache(self):
        with patch.object(gate, "heilen", return_value=copy.deepcopy(self.heilung)), \
             patch.object(gate, "_datum_heute", return_value="2026-11-12"):
            return gate.wache(self.root, nur_quelle=True)

    def test_aus_register_entfernter_altfall_bleibt_bis_bewusster_klaerung_offen(self):
        # Löschen oder Umklassifizieren allein ist kein Nachweis der Klärung.
        for raw in ("maschinell:\n  - bot\nmenschlich:\n",
                    "maschinell:\n  - bot\n  - alt\nmenschlich:\n"):
            with self.subTest(raw=raw):
                self.register.write_text(raw, encoding="utf-8")
                lauf = self.wache()
                self.assertEqual(lauf["lage"]["ungeklaert"], 1)
                self.assertEqual(lauf["lage"]["aeltester_alter_tage"], 5)
                self.assertTrue(any(e["grund"] == "register-entfernt" for e in lauf["eskalation"]))
                self.assertEqual(json.loads(self.state.read_text())["ungeklaert_erstmals"],
                                 {"alt": "2026-11-07"})
                self.assertFalse(self.wache()["state_geaendert"])

    def test_fehlt_der_versionierte_zustand_ist_die_wache_nicht_messbar(self):
        self.state.unlink()
        lauf = self.wache()
        self.assertEqual(gate.main_exit_werkzeug(lauf["funde_nachher"]), 2)
        self.assertFalse(lauf["state_geaendert"])
        self.assertFalse(self.state.exists())

    def test_defektes_register_loescht_keine_offenen_altfaelle(self):
        for roh in (None, "maschinell:\n  - bot\nmenschlich: [alt]\n",
                    "maschinell:\n  - bot\nmenshlich:\n  - alt\n",
                    "maschinell:\n  - bot\nmenschlich:\n  - bot\n"):
            with self.subTest(roh=roh):
                if roh is None:
                    self.register.unlink(missing_ok=True)
                else:
                    self.register.write_text(roh, encoding="utf-8")
                with self.assertRaises(kp.WerkzeugFehler):
                    kp.ungeklaert(self.root)
                vorher = self.state.read_bytes()
                lauf = self.wache()
                self.assertIsNone(lauf["lage"]["ungeklaert"])
                self.assertFalse(lauf["state_geaendert"])
                self.assertEqual(self.state.read_bytes(), vorher)

    def test_frist_fehlt_ist_nicht_messbar(self):
        (self.root / "data/recht-fristen.yaml").unlink()
        vorher = self.state.read_bytes()
        lauf = self.wache()
        self.assertTrue(any(f["regel"] == "W0" for f in lauf["funde_nachher"]))
        self.assertEqual(gate.main_exit_werkzeug(lauf["funde_nachher"]), 2)
        self.assertEqual(lauf["lage"]["frist"], "2026-12-02")
        self.assertEqual(lauf["lage"]["tage_bis_frist"], 20)
        self.assertTrue(any(e["grund"] == "register" for e in lauf["eskalation"]))
        self.assertFalse(lauf["state_geaendert"])
        self.assertEqual(self.state.read_bytes(), vorher)

    def test_verschobene_frist_beruhigt_die_wache_nicht_und_ueberschreibt_keinen_state(self):
        (self.root / "data/recht-fristen.yaml").write_text(
            f'fristen:\n  - id: {gate.FRIST_ID}\n    faellig_am: "2027-12-02"\n', encoding="utf-8")
        vorher = self.state.read_bytes()
        lauf = self.wache()
        self.assertEqual(gate.main_exit_werkzeug(lauf["funde_nachher"]), 2)
        self.assertEqual(lauf["lage"]["frist"], "2026-12-02")
        self.assertEqual(lauf["lage"]["tage_bis_frist"], 20)
        self.assertTrue(any(e["grund"] == "register" for e in lauf["eskalation"]))
        self.assertFalse(lauf["state_geaendert"])
        self.assertEqual(self.state.read_bytes(), vorher)

    def test_datumswechsel_erfindet_keine_zustandsaenderung(self):
        zustand = json.loads(self.state.read_text())
        zustand.update(zuletzt_geaendert="2026-11-07", revision="belegter-stand")
        self.state.write_text(json.dumps(zustand), encoding="utf-8")
        vorher = self.state.read_bytes()
        with patch.object(gate, "heilen", return_value=copy.deepcopy(self.heilung)):
            lauf = gate.wache(self.root, nur_quelle=True, heute="2026-11-13")
        self.assertEqual(lauf["lage"]["tage_bis_frist"], 19)
        self.assertEqual(lauf["lage"]["aeltester_alter_tage"], 6)
        self.assertEqual(lauf["lage"]["zuletzt_geaendert"], "2026-11-07")
        self.assertFalse(lauf["state_geaendert"])
        self.assertEqual(self.state.read_bytes(), vorher)

    def test_defekter_zustand_wird_nicht_als_neue_wache_ueberschrieben(self):
        for raw in ('{broken', '[]', '{}', '{"ungeklaert_erstmals": []}',
                    '{"ungeklaert_erstmals": {"alt": "kein-datum"}}',
                    '{"ungeklaert_erstmals": {}, "ungeklaert_erstmals": {"alt":"2026-11-07"}}',
                    '{"ungeklaert_erstmals": {"alt":"2026-11-07", "alt":"2026-11-08"}}'):
            with self.subTest(raw=raw):
                self.state.write_text(raw, encoding="utf-8")
                vorher = self.state.read_bytes()
                lauf = self.wache()
                self.assertEqual(gate.main_exit_werkzeug(lauf["funde_nachher"]), 2)
                self.assertFalse(lauf["state_geaendert"])
                self.assertEqual(self.state.read_bytes(), vorher)

    def test_doppelte_oder_invalid_formatierte_frist_ist_nicht_messbar(self):
        pfad = self.root / "data/recht-fristen.yaml"
        for raw in (f'- id: {gate.FRIST_ID}\n  faellig_am: "2026-12-02"\n'
                    f'- id: {gate.FRIST_ID}\n  faellig_am: "2026-12-03"\n',
                    f'- id: {gate.FRIST_ID}\n  faellig_am: "2026-99-33"\n'):
            with self.subTest(raw=raw):
                pfad.write_text(raw, encoding="utf-8")
                self.assertEqual(gate.main_exit_werkzeug(self.wache()["funde_nachher"]), 2)

    def test_offene_fristeskalation_ergibt_cli_exit_1_werkzeug_hat_vorrang(self):
        lauf = self.wache()
        self.assertTrue(any(e["grund"] == "register" for e in lauf["eskalation"]))
        with patch.object(gate, "wache", return_value=lauf), patch("builtins.print"):
            self.assertEqual(gate.main(["--wache"]), 1)
            lauf["funde_nachher"] = [{"regel": "W0", "text": "Probe"}]
            with patch.object(kp, "werkzeugbefund_melden"):
                self.assertEqual(gate.main(["--wache"]), 2)


class KennzeichnungRegisterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.posts = self.root / "content/posts"
        self.posts.mkdir(parents=True)
        self.register = self.root / "data/ki_kennzeichnung.yaml"
        self.register.parent.mkdir()
        self.register.write_text("maschinell:\n  - bot\nmenschlich:\n", encoding="utf-8")
        self.bot = self.posts / "bot.md"
        self.unbekannt = self.posts / "unbekannt.md"
        self.bot.write_text("---\ntitle: Bot\nai_generated: false\n---\nText\n", encoding="utf-8")
        self.unbekannt.write_text("---\ntitle: Unbekannt\nai_generated: false\n---\nText\n", encoding="utf-8")

    def cli(self, *args):
        with patch.object(kennzeichnung, "ROOT", self.root), \
             patch.object(kennzeichnung, "POSTS", self.posts), \
             patch.object(kennzeichnung, "REGISTER", self.register), \
             patch.object(kp, "werkzeugbefund_melden"), patch("builtins.print"):
            return kennzeichnung.main(list(args))

    def test_nur_positiv_im_register_stehende_herkunft_wird_automatisch_gesetzt(self):
        unbekannt_vorher = self.unbekannt.read_bytes()
        self.assertEqual(self.cli("--fix"), 1)
        self.assertIn("ai_generated: true", self.bot.read_text(encoding="utf-8"))
        self.assertEqual(self.unbekannt.read_bytes(), unbekannt_vorher)
        self.assertEqual(self.cli("--gate"), 1)

    def test_nicht_lesbares_oder_widerspruechliches_register_verhindert_jeden_eingriff(self):
        for raw in (None, "maschinell:\n  - bot\nmenshlich:\n",
                    "maschinell:\n  - bot\nmenschlich:\n  - bot\n",
                    "maschinell:\n  - bot\n  - bot\nmenschlich:\n"):
            with self.subTest(raw=raw):
                if raw is None:
                    self.register.unlink(missing_ok=True)
                else:
                    self.register.write_text(raw, encoding="utf-8")
                vorher = (self.bot.read_bytes(), self.unbekannt.read_bytes())
                self.assertEqual(self.cli("--fix"), 2)
                self.assertEqual((self.bot.read_bytes(), self.unbekannt.read_bytes()), vorher)


class DeployVerdrahtungTests(unittest.TestCase):
    def test_letztes_gate_prueft_nach_rebuild_und_vor_beiden_veroeffentlichungen(self):
        import yaml
        workflow = yaml.safe_load((ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8"))
        schritte = workflow["jobs"]["deploy"]["steps"]
        namen = [s.get("name", "") for s in schritte]
        ziel = "KI-Provenienz – finales Veröffentlichungs-Gate"
        self.assertEqual(namen.count(ziel), 1)
        index = namen.index(ziel)
        for vorher in ("KI-Provenienz – maschinenlesbare Kennzeichnung im Build",
                       "KI-Kennzeichnung – Register durchsetzen (selbstheilend)",
                       "Rebuild nach Heilungen (nur wenn sich Content geändert hat)",
                       "Suchindex bauen (Pagefind)"):
            self.assertLess(namen.index(vorher), index, vorher)
        for nachher in ("Deploy auf gh-pages", "Artefakt für offizielles Pages-Deployment hochladen"):
            self.assertLess(index, namen.index(nachher), nachher)
        schritt = schritte[index]
        self.assertEqual(schritt.get("run"), "python3 scripts/ki_provenienz_gate.py --gate")
        self.assertNotIn("if", schritt)
        self.assertFalse(schritt.get("continue-on-error", False))
        self.assertEqual(namen[index + 1:namen.index("Deploy auf gh-pages")],
                         ["Werkzeugbefunde einsammeln (Material für das Siegel)"])

        # Den echten run-Block wie Actions mit bash -e ausführen, nicht nur
        # Text suchen: Erfolg, Inhaltsfund und Werkzeugfehler bleiben erhalten.
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            (basis / "scripts").mkdir()
            for code in (0, 1, 2):
                (basis / "scripts/ki_provenienz_gate.py").write_text(
                    f"import sys\nassert sys.argv[1:] == ['--gate']\nsys.exit({code})\n", encoding="utf-8")
                ergebnis = subprocess.run(["bash", "-e", "-c", schritt["run"]], cwd=basis,
                                          env=dict(os.environ), capture_output=True, text=True)
                self.assertEqual(ergebnis.returncode, code)


if __name__ == "__main__":
    unittest.main()
