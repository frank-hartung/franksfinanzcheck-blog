"""Regressionstests für den Fachfreigabe-Vertrag der KI-Redaktion (#734).

Warum diese Tests existieren
----------------------------
Am 13.10.2026 öffnete die werktägliche YMYL-Prüfqueue Issue #734: Der
News-Writer (Rolle „ChatGPT“) hatte aus dem nächsten freien Aufhänger –
Kategorie „versicherung“ – den Entwurf „Versicherung-Update: Was sich jetzt
für dich ändert“ geschrieben. Hochrisiko, kein Prüfgerüst, keine einzige
Quelle, dazu ein Titel, den es seit dem 17.09. schon gab (der Schwester-
entwurf aus #586). Das Redaktions-Gate tat seine Pflicht (E03).

Die Ursache saß nicht im Gate, sondern in der Produktion: Die Content-Engine
hält sich seit #521 an zwei Bahnen (AUTO vs. FACHFREIGABE, WIP-Limit), die
drei KI-Writer über `ki_shared` (claude_writer, news_writer, poppy_repurpose)
kannten diesen Vertrag nicht. Wer schreibt, muss die Regel kennen, nach der
später über ihn entschieden wird – dieselbe Fehlerklasse wie #521, nur an
einer zweiten Produktionslinie.

Diese Datei friert die Zusagen der Dauerheilung ein:

1) **SSOT** – die Bahn kommt aus `engine_capacity` (→ `classify_text` des
   Gates), keine kopierten Muster in `ki_shared`; unbekannt ist nicht AUTO.
2) **Schreibgrenze** – `build_frontmatter` verweigert YMYL ohne Beauftragung;
   beauftragt entsteht das Prüfgerüst (hoch/ausstehend, nie „freigegeben“),
   die Queue zeigt dann E05 statt E03. Geschlossenes WIP-Limit sperrt auch
   die Beauftragung.
3) **News-Writer** – der echte Aufhänger vom 13.10. wird übersprungen und
   NICHT verbraucht, ein AUTO-Aufhänger rückt nach; Dubletten werden über
   Titel ODER normalisierten Slug erkannt (SEO-verlängerte Titel täuschen
   nicht mehr); ein beauftragter Lauf landet mit Gerüst im Entwurf.
4) **Claude-Writer / Poppy** – der Pool liefert ohne Beauftragung nur AUTO;
   kein `except Exception` darf den Vertrag umgehen.
5) **Promote** – `ki_redaktion.py --promote` legt keinen Hochrisiko-Entwurf
   ohne gültige Freigabe in die Re-Queue.

Alle Tests laufen ohne Netz, ohne API-Keys, uhrfest (Bestand und WIP-Lage
werden festgenagelt) und schreiben nur in temporäre Verzeichnisse.
"""
from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import claude_writer as cw  # noqa: E402
import editorial_review_gate as erg  # noqa: E402
import engine_capacity as ec  # noqa: E402
import ki_redaktion as kr  # noqa: E402
import ki_shared as ks  # noqa: E402
import news_writer as nw  # noqa: E402
import poppy_lib as lib  # noqa: E402
import poppy_repurpose as rep  # noqa: E402
import post_utils  # noqa: E402

# Der Aufhänger, aus dem am 13.10.2026 der E03-Entwurf entstand – wörtlich
# aus data/aktuelle_entwicklungen.yaml, ohne die Verbrauchs-Markierung.
VORFALL_HOOK = {
    "id": "versicherung-vergleichsportale-nicht-vollstaendig",
    "kategorie": "versicherung",
    "ab": "2026-01-01",
    "bis": "",
    "hook": ("Vergleichsportale zeigen selten alle Anbieter am Markt – wer "
             "nur das erstbeste Ergebnis nimmt, lässt oft bares Geld liegen."),
}
VORFALL_TITEL = "Versicherung-Update: Was sich jetzt für dich ändert"
SAISON_HOOK = {
    "id": "saisonal-test-vertragscheck",
    "kategorie": "saisonal",
    "hook": "Ein jährlicher Vertrags-Check deckt mehr auf als spontane Wechsel.",
}
ENERGIE_HOOK = {
    "id": "energie-test-wechselfenster",
    "kategorie": "energie",
    "hook": "Rund um den Jahreswechsel kündigen viele Versorger Preise neu an.",
}
OFFEN = {"geoeffnet": True, "grund": "WIP frei (Test)"}
ZU = {"geoeffnet": False, "grund": "WIP-Limit erreicht (3/3, Test)"}


def FREI(_titel: str) -> bool:  # noqa: N802 – liest sich im Aufruf wie ein Wert
    """Bestand ohne Dubletten (die Auswahl-Tests prüfen nur die Bahn)."""
    return False


def news_args(**kw) -> argparse.Namespace:
    basis = dict(title=None, kategorie=None, keywords=None, offline=True,
                 provider=None, model=None, fachfreigabe=False)
    basis.update(kw)
    return argparse.Namespace(**basis)


def claude_args(**kw) -> argparse.Namespace:
    basis = dict(topic=None, pillar=None, keywords=None, offline=True,
                 provider=None, model=None, fachfreigabe=False)
    basis.update(kw)
    return argparse.Namespace(**basis)


def still(fn, *a, **kw):
    """Aufruf ohne Konsolenrauschen; liefert (Ergebnis, Ausgabe)."""
    puffer = io.StringIO()
    with contextlib.redirect_stdout(puffer):
        ergebnis = fn(*a, **kw)
    return ergebnis, puffer.getvalue()


def parse(text: str) -> tuple[dict, str]:
    """(Frontmatter-Mapping, Body) – mit dem Parser des Redaktions-Gates."""
    fm_text, body = erg.split_article(text)
    return yaml.safe_load(fm_text) or {}, body


def vorfall_frontmatter(**kw) -> str:
    return ks.build_frontmatter(
        title=VORFALL_TITEL, description="Test", tags=["Versicherungen vergleichen"],
        pillar="versicherungen", keywords=[VORFALL_TITEL], rolle="chatgpt",
        news=True, kategorie="versicherung", **kw)


class TempPosts(unittest.TestCase):
    """Posts-Ordner ins Temp-Verzeichnis, KI-Report stumm."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="ki-fachfreigabe-")
        self.posts = os.path.join(self.tmp, "posts")
        os.makedirs(self.posts)
        self._alt_posts = post_utils.POSTS_DIR
        post_utils.POSTS_DIR = self.posts
        report = mock.patch.object(ks, "write_report", lambda *a, **k: None)
        report.start()
        self.addCleanup(report.stop)

    def tearDown(self):
        post_utils.POSTS_DIR = self._alt_posts
        shutil.rmtree(self.tmp, ignore_errors=True)

    def entwuerfe(self) -> list[str]:
        return sorted(str(p) for p in Path(self.posts).glob("*/index.md"))


# ---------------------------------------------------------------------------
# 1) SSOT: Bahn aus engine_capacity, fail-closed
# ---------------------------------------------------------------------------
class BahnSsotTests(unittest.TestCase):
    def test_ki_shared_kopiert_keine_risikomuster(self):
        quelle = (SCRIPTS / "ki_shared.py").read_text(encoding="utf-8")
        self.assertNotIn("HIGH_PATTERNS =", quelle)
        self.assertNotIn("MEDIUM_PATTERNS =", quelle)
        self.assertIn("ec.risikoklasse_fuer_thema", quelle)
        self.assertIn("ec.bahn_fuer_thema", quelle)
        self.assertIn("ec.fachfreigabe_bahn(", quelle)
        self.assertIn("ec.nur_auto(", quelle)
        self.assertEqual(ks.BAHN_AUTO, ec.BAHN_AUTO)
        self.assertEqual(ks.BAHN_FACHFREIGABE, ec.BAHN_FACHFREIGABE)

    def test_dieselbe_antwort_wie_die_engine(self):
        faelle = [
            (VORFALL_TITEL, [VORFALL_TITEL], "versicherungen"),
            ("Riester-Rente: Lohnt sie sich 2026 noch?", [], ""),
            ("Ratenkredit umschulden: so gehst du vor", [], "konto-karten"),
            ("Stromfresser im Haushalt entlarven", [], "strom-sparen"),
            ("Saison-Update: Was sich jetzt für dich ändert", [], "frugalismus"),
        ]
        for titel, keywords, pillar in faelle:
            with self.subTest(titel=titel):
                self.assertEqual(
                    ks.bahn_fuer(titel, keywords, pillar),
                    ec.bahn_fuer_thema({"title": titel, "keywords": keywords,
                                        "pillar": pillar}))

    def test_vorfall_734_ist_fachfreigabe(self):
        self.assertEqual(
            ks.bahn_fuer(VORFALL_TITEL, [VORFALL_TITEL], "versicherungen"),
            ks.BAHN_FACHFREIGABE)

    def test_einstufung_defekt_ist_fail_closed(self):
        with mock.patch.object(ec, "risikoklasse_fuer_thema",
                               side_effect=ValueError("kaputt")):
            with self.assertRaises(ks.FachfreigabeErforderlich) as ctx:
                ks.bahn_fuer("Stromfresser im Haushalt entlarven", [],
                             "strom-sparen")
        self.assertIn("fail-closed", str(ctx.exception))

    def test_lage_kommt_aus_engine_capacity(self):
        with mock.patch.object(ec, "fachfreigabe_bahn",
                               return_value=dict(OFFEN)) as bahn:
            self.assertTrue(ks.fachfreigabe_lage()["geoeffnet"])
        self.assertEqual(bahn.call_args.args[0], Path(post_utils.POSTS_DIR))


# ---------------------------------------------------------------------------
# 2) Schreibgrenze build_frontmatter
# ---------------------------------------------------------------------------
class SchreibgrenzeTests(unittest.TestCase):
    def test_ohne_beauftragung_kein_ymyl_frontmatter(self):
        with self.assertRaises(ks.FachfreigabeErforderlich) as ctx:
            vorfall_frontmatter()
        self.assertIn(ks.FACHFREIGABE_FLAG, str(ctx.exception))
        self.assertIn("#734", str(ctx.exception))

    def test_beauftragt_traegt_pruefgeruest_e05_statt_e03(self):
        with mock.patch.object(ks, "fachfreigabe_lage", return_value=OFFEN):
            fm_text = vorfall_frontmatter(fachfreigabe=True)
        self.assertIn("redaktionelle_pruefung:", fm_text)
        self.assertIn('risikoklasse: "hoch"', fm_text)
        self.assertIn('status: "ausstehend"', fm_text)
        self.assertNotIn('status: "freigegeben"', fm_text)
        self.assertNotRegex(fm_text, r"pruefer:\s*\S")

        fm, body = parse(fm_text + "## Abschnitt\n\nText.\n")
        befund = erg.validate_article(fm, body)
        codes = {f["code"] for f in befund["findings"]}
        self.assertEqual(befund["risk"], erg.RISK_HIGH)
        self.assertNotIn("E03", codes)
        self.assertIn("E05", codes)
        self.assertFalse(befund["approved"])

    def test_geschlossene_bahn_sperrt_auch_die_beauftragung(self):
        with mock.patch.object(ks, "fachfreigabe_lage", return_value=ZU):
            with self.assertRaises(ks.FachfreigabeErforderlich) as ctx:
                vorfall_frontmatter(fachfreigabe=True)
        self.assertIn("geschlossen", str(ctx.exception))

    def test_auto_bekommt_risikogeruest_wie_die_engine(self):
        lage = mock.Mock(side_effect=AssertionError("AUTO braucht keine Lage"))
        with mock.patch.object(ks, "fachfreigabe_lage", lage):
            fm_text = ks.build_frontmatter(
                title="Stromfresser im Haushalt entlarven", description="Test",
                tags=["Stromkosten senken"], pillar="strom-sparen",
                keywords=["Stromfresser"], rolle="claude")
        self.assertIn("redaktionelle_pruefung:", fm_text)
        self.assertIn('status: "ausstehend"', fm_text)
        fm, _ = parse(fm_text + "Text.\n")
        self.assertEqual(fm["redaktionelle_pruefung"]["risikoklasse"],
                         erg.inferred_risk(fm))

    def test_ymyl_sperre_greift_vor_der_tag_kanonisierung(self):
        # Ein Thema ohne kanonischen Tag würde sonst mit einem Register-
        # Fehler scheitern und den eigentlichen Grund verdecken.
        with self.assertRaises(ks.FachfreigabeErforderlich):
            ks.build_frontmatter(
                title="Riester-Rente: Lohnt sie sich 2026 noch?",
                description="Test", tags=["Riester-Rente"], pillar=None,
                keywords=["Riester-Rente"], rolle="claude")


# ---------------------------------------------------------------------------
# 3) News-Writer: Auswahl, Dubletten, beauftragter Lauf
# ---------------------------------------------------------------------------
class NewsWriterAuswahlTests(unittest.TestCase):
    def test_vorfall_hook_wird_uebersprungen_auto_rueckt_nach(self):
        plan, gruende = nw.waehle_aufhaenger(
            news_args(), kandidaten=[VORFALL_HOOK, SAISON_HOOK], ist_vergeben=FREI)
        self.assertEqual(plan["hook"]["id"], SAISON_HOOK["id"])
        self.assertEqual(plan["bahn"], ks.BAHN_AUTO)
        self.assertEqual(len(gruende), 1)
        self.assertIn(VORFALL_HOOK["id"], gruende[0])
        self.assertIn(ks.FACHFREIGABE_FLAG, gruende[0])

    def test_titel_dublette_wird_verhindert(self):
        vergeben = {"energie-update: was sich jetzt für dich ändert"}
        plan, gruende = nw.waehle_aufhaenger(
            news_args(), kandidaten=[ENERGIE_HOOK],
            ist_vergeben=lambda t: t.lower() in vergeben)
        self.assertIsNone(plan)
        self.assertIn("Dublette", gruende[0])
        self.assertIn("titel:", gruende[0])

    def test_kuratierter_titel_im_pool_loest_die_dublette(self):
        hook = dict(ENERGIE_HOOK, titel="Strompreise zum Jahreswechsel: jetzt prüfen")
        vergeben = {"energie-update: was sich jetzt für dich ändert"}
        plan, gruende = nw.waehle_aufhaenger(
            news_args(), kandidaten=[hook],
            ist_vergeben=lambda t: t.lower() in vergeben)
        self.assertEqual(plan["title"], hook["titel"])
        self.assertEqual(gruende, [])

    def test_dublette_hat_vorrang_vor_der_bahn(self):
        # Der echte 13.10.: Titel vergeben UND YMYL – gemeldet wird die
        # Dublette, denn auch eine Beauftragung macht sie nicht schreibbar.
        plan, gruende = nw.waehle_aufhaenger(
            news_args(fachfreigabe=True), kandidaten=[VORFALL_HOOK],
            ist_vergeben=lambda t: True, lage=OFFEN)
        self.assertIsNone(plan)
        self.assertIn("Dublette", gruende[0])

    def test_beauftragt_und_offen_waehlt_den_ymyl_hook(self):
        plan, gruende = nw.waehle_aufhaenger(
            news_args(fachfreigabe=True), kandidaten=[VORFALL_HOOK],
            ist_vergeben=FREI, lage=OFFEN)
        self.assertEqual(plan["bahn"], ks.BAHN_FACHFREIGABE)
        self.assertEqual(plan["title"], VORFALL_TITEL)
        self.assertEqual(plan["fm_keywords"], [VORFALL_TITEL])
        self.assertEqual(gruende, [])

    def test_beauftragt_aber_wip_voll_ueberspringt(self):
        plan, gruende = nw.waehle_aufhaenger(
            news_args(fachfreigabe=True), kandidaten=[VORFALL_HOOK],
            ist_vergeben=FREI, lage=ZU)
        self.assertIsNone(plan)
        self.assertIn("geschlossen", gruende[0])

    def test_kein_aufrufer_nutzt_die_alte_einzelwahl(self):
        # `pick_news_hook` lieferte „den nächsten“ Aufhänger ohne Bahn- und
        # Dublettenprüfung – genau der Weg des 13.10. Er darf nicht zurück.
        self.assertFalse(hasattr(ks, "pick_news_hook"))
        for skript in SCRIPTS.glob("*.py"):
            with self.subTest(skript=skript.name):
                self.assertNotIn("pick_news_hook(",
                                 skript.read_text(encoding="utf-8"))

    def test_kandidaten_respektieren_fenster_und_verbrauch(self):
        import datetime
        pool = [
            dict(VORFALL_HOOK, ki_news_used=True),
            dict(SAISON_HOOK, ab="2026-11-01"),
            dict(ENERGIE_HOOK, bis="2026-10-01"),
            {"id": "ohne-hook", "kategorie": "energie"},
            {"id": "gueltig", "kategorie": "konto", "hook": "Ein Satz."},
        ]
        with mock.patch.object(ks, "_load_yaml", return_value=pool):
            ids = [h["id"] for h in ks.news_hook_kandidaten(
                heute=datetime.date(2026, 10, 13))]
        self.assertEqual(ids, ["gueltig"])


class NewsWriterLaufTests(TempPosts):
    def test_automatik_verbraucht_den_ymyl_hook_nicht(self):
        markiere = mock.Mock()
        with mock.patch.object(ks, "news_hook_kandidaten",
                               return_value=[dict(VORFALL_HOOK)]), \
                mock.patch.object(ks, "existing_titles", return_value=set()), \
                mock.patch.object(ks, "mark_news_hook_used", markiere):
            rc, ausgabe = still(nw.run, news_args())
        self.assertEqual(rc, 1)
        markiere.assert_not_called()
        self.assertEqual(self.entwuerfe(), [])
        self.assertIn("bleibt im Pool", ausgabe)
        self.assertIn(VORFALL_HOOK["id"], ausgabe)

    def test_beauftragter_lauf_schreibt_entwurf_mit_pruefgeruest(self):
        markiere = mock.Mock()
        with mock.patch.object(ks, "news_hook_kandidaten",
                               return_value=[dict(VORFALL_HOOK)]), \
                mock.patch.object(ks, "existing_titles", return_value=set()), \
                mock.patch.object(ks, "fachfreigabe_lage", return_value=OFFEN), \
                mock.patch.object(ks, "mark_news_hook_used", markiere):
            rc, ausgabe = still(nw.run, news_args(fachfreigabe=True))
        self.assertEqual(rc, 0, ausgabe)
        markiere.assert_called_once_with(VORFALL_HOOK["id"])
        [pfad] = self.entwuerfe()
        urteil = erg.evaluate_path(Path(pfad))
        codes = {f["code"] for f in urteil["findings"]}
        self.assertEqual(urteil["risk"], erg.RISK_HIGH)
        self.assertNotIn("E03", codes)
        self.assertIn("E05", codes)
        self.assertFalse(urteil["approved"])
        self.assertIn("YMYL beauftragt", ausgabe)

    def test_automatik_schreibt_den_auto_hook(self):
        with mock.patch.object(ks, "news_hook_kandidaten",
                               return_value=[dict(VORFALL_HOOK), dict(SAISON_HOOK)]), \
                mock.patch.object(ks, "existing_titles", return_value=set()), \
                mock.patch.object(ks, "mark_news_hook_used") as markiere:
            rc, _ = still(nw.run, news_args())
        self.assertEqual(rc, 0)
        markiere.assert_called_once_with(SAISON_HOOK["id"])
        [pfad] = self.entwuerfe()
        self.assertIn("saison-update", pfad)
        urteil = erg.evaluate_path(Path(pfad))
        self.assertNotEqual(urteil["risk"], erg.RISK_HIGH)
        self.assertNotIn("E03", {f["code"] for f in urteil["findings"]})


class DublettenIdentitaetTests(TempPosts):
    """Titel ODER normalisierter Slug – SEO-Verlängerungen täuschen nicht."""

    def lege_an(self, slug: str, titel: str) -> None:
        os.makedirs(os.path.join(self.posts, slug))
        with open(os.path.join(self.posts, slug, "index.md"), "w",
                  encoding="utf-8") as fh:
            fh.write(f'---\ntitle: "{titel}"\ndraft: false\n---\n\nText.\n')

    def test_seo_verlaengerter_titel_wird_ueber_den_slug_erkannt(self):
        # Realfall 23.09.: live war „… für den Alltag: Geld sparen“.
        self.lege_an("2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag",
                     "5 einfache Frugalismus-Tricks für den Alltag: Geld sparen")
        self.assertTrue(ks.titel_vergeben(
            "5 einfache Frugalismus-Tricks für den Alltag"))

    def test_dubletten_zaehler_im_slug_wird_normalisiert(self):
        self.lege_an("2026-10-13-energie-update-was-sich-jetzt-fuer-dich-aendert-2",
                     "Energie-Update kompakt")
        self.assertTrue(ks.titel_vergeben(
            "Energie-Update: Was sich jetzt für dich ändert"))

    def test_exakter_titel_und_neues_thema(self):
        self.lege_an("2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert",
                     VORFALL_TITEL)
        self.assertTrue(ks.titel_vergeben(VORFALL_TITEL.upper()))
        self.assertFalse(ks.titel_vergeben("Heizperiode vorbereiten im Spätsommer"))

    def test_normalisierung_kommt_aus_reserve_topics(self):
        quelle = (SCRIPTS / "ki_shared.py").read_text(encoding="utf-8")
        self.assertIn("reserve_topics._bestands_slugs(", quelle)


# ---------------------------------------------------------------------------
# 4) Claude-Writer und Poppy-Werkbank
# ---------------------------------------------------------------------------
POOL = {"topics": [
    {"title": "Kfz-Versicherung wechseln: Stichtag und Fallstricke",
     "pillar": "versicherungen", "keywords": ["Kfz-Versicherung wechseln"]},
    {"title": "Stromfresser im Haushalt entlarven", "pillar": "strom-sparen",
     "keywords": ["Stromfresser"]},
]}


class ClaudeWriterTests(TempPosts):
    def test_pool_liefert_ohne_beauftragung_nur_auto(self):
        with mock.patch.object(ks, "_load_yaml", return_value=POOL), \
                mock.patch.object(ks, "existing_titles", return_value=set()):
            self.assertEqual(ks.pick_topic()["pillar"], "strom-sparen")
            self.assertEqual(ks.pick_topic(fachfreigabe=True)["pillar"],
                             "versicherungen")
            self.assertIsNone(ks.pick_topic(pillar="versicherungen"))

    def test_explizites_ymyl_topic_braucht_die_beauftragung(self):
        with mock.patch.object(ks, "existing_titles", return_value=set()):
            rc, ausgabe = still(cw.run, claude_args(
                topic="Riester-Rente: Lohnt sie sich 2026 noch?"))
        self.assertEqual(rc, 1)
        self.assertIn(ks.FACHFREIGABE_FLAG, ausgabe)
        self.assertEqual(self.entwuerfe(), [])

    def test_writer_pruefen_vor_der_generierung(self):
        # Struktur-Pin: Die Prüfung steht VOR dem Modellaufruf bzw. dem
        # Offline-Gerüst – kein verbranntes Gratis-Kontingent, kein
        # verbrauchter Aufhänger, kein halber Entwurf.
        import inspect
        for funktion, pruefung, erzeugung in (
                (cw.run, "ks.fachfreigabe_pruefen(", "_generate(chain"),
                (nw.run, "waehle_aufhaenger(args)", "_generate(chain"),
                (rep.blog_entwurf_schreiben, "ks.fachfreigabe_pruefen(",
                 "if offline:")):
            with self.subTest(funktion=funktion.__module__):
                quelle = inspect.getsource(funktion)
                self.assertIn(pruefung, quelle)
                self.assertLess(quelle.index(pruefung), quelle.index(erzeugung))
                self.assertIn("fachfreigabe=", quelle)
        for skript in ("claude_writer.py", "news_writer.py", "poppy_repurpose.py"):
            with self.subTest(cli=skript):
                quelle = (SCRIPTS / skript).read_text(encoding="utf-8")
                self.assertIn("ks.FACHFREIGABE_FLAG", quelle)


class PoppyTests(TempPosts):
    def setUp(self):
        super().setUp()
        self._alt = (lib.CARD_DIR, lib.REPORT_FILE, lib.BOARD_OUTPUT)
        lib.CARD_DIR = os.path.join(self.tmp, "cards")
        lib.REPORT_FILE = os.path.join(self.tmp, "report.md")
        lib.BOARD_OUTPUT = os.path.join(self.tmp, "board")

    def tearDown(self):
        lib.CARD_DIR, lib.REPORT_FILE, lib.BOARD_OUTPUT = self._alt
        super().tearDown()

    def ymyl_karte(self) -> dict:
        karte = lib.neue_karte(
            "text", titel="Kfz-Versicherung wechseln – Notiz", url="",
            rohtext="Kfz-Versicherung: Wechsel bis 30. November möglich.")
        karte["insights"] = ["Viele Policen lassen sich zum Jahresende kündigen."]
        karte["pillar"] = "versicherungen"
        karte["artikel_titel"] = "Kfz-Versicherung wechseln"
        lib.speichere_karte(karte)
        return karte

    def test_ymyl_karte_bleibt_neu_und_ohne_entwurf(self):
        karte = self.ymyl_karte()
        ok, ausgabe = still(rep.karte_verwerten, karte, offline=True)
        self.assertFalse(ok)
        self.assertEqual(karte["status"], lib.STATUS_NEU)
        self.assertFalse((karte.get("erzeugnisse") or {}).get("blog"))
        self.assertEqual(self.entwuerfe(), [])
        self.assertIn("#734", ausgabe)

    def test_ersatz_frontmatter_umgeht_den_vertrag_nicht(self):
        # Selbst wenn die Frühprüfung durchrutschte: Die Schreibgrenze wirft,
        # und der Fallback-Zweig (`except Exception`) darf das nicht schlucken.
        karte = self.ymyl_karte()
        with mock.patch.object(ks, "fachfreigabe_pruefen",
                               return_value=ks.BAHN_AUTO), \
                mock.patch.object(ks, "build_frontmatter",
                                  side_effect=ks.FachfreigabeErforderlich("x")):
            with self.assertRaises(ks.FachfreigabeErforderlich):
                still(rep.blog_entwurf_schreiben, karte, True)
        self.assertEqual(self.entwuerfe(), [])

    def test_ersatz_frontmatter_traegt_ebenfalls_das_pruefgeruest(self):
        # Beauftragt, aber das Tag-Register streikt: Das Ersatz-Frontmatter
        # darf keinen E03-Entwurf erzeugen (genau der Befund von #734).
        karte = self.ymyl_karte()
        with mock.patch.object(ks, "fachfreigabe_lage", return_value=OFFEN), \
                mock.patch.object(ks, "_kanonische_frontmatter_tags",
                                  side_effect=RuntimeError("Register kaputt")):
            (slug, _, _), ausgabe = still(rep.blog_entwurf_schreiben, karte,
                                          True, fachfreigabe=True)
        self.assertIn("Fallback-Frontmatter", ausgabe)
        urteil = erg.evaluate_path(Path(self.posts) / slug / "index.md")
        codes = {f["code"] for f in urteil["findings"]}
        self.assertEqual(urteil["risk"], erg.RISK_HIGH)
        self.assertNotIn("E03", codes)
        self.assertNotIn("E02", codes)
        self.assertIn("E05", codes)

    def test_beauftragte_ymyl_karte_traegt_pruefgeruest(self):
        karte = self.ymyl_karte()
        with mock.patch.object(ks, "fachfreigabe_lage", return_value=OFFEN):
            (slug, _, _), _ = still(rep.blog_entwurf_schreiben, karte, True,
                                    fachfreigabe=True)
        pfad = Path(self.posts) / slug / "index.md"
        urteil = erg.evaluate_path(pfad)
        codes = {f["code"] for f in urteil["findings"]}
        self.assertEqual(urteil["risk"], erg.RISK_HIGH)
        self.assertNotIn("E03", codes)
        self.assertFalse(urteil["approved"])


# ---------------------------------------------------------------------------
# 5) Promote-Sperre
# ---------------------------------------------------------------------------
def ki_entwurf(*, pillar: str, titel: str) -> str:
    absatz = ("Dieser Absatz beschreibt sachlich, worauf es ankommt, und "
              "nennt Bedingungen statt Versprechen. ") * 6
    body = "\n\n".join(f"## Abschnitt {i}\n\n{absatz}" for i in range(1, 9))
    return (
        "---\n"
        f'title: "{titel}"\n'
        'description: "Test"\n'
        "date: 2026-10-13T08:00:00Z\n"
        "draft: true\n"
        f'pillar: "{pillar}"\n'
        f'keywords: ["{titel}"]\n'
        'author: "Frank Hartung"\n'
        'ki_redaktion: "chatgpt"\n'
        'ki_redaktion_status: "review"\n'
        "---\n\n" + body + "\n")


class PromoteSperreTests(TempPosts):
    def lege_an(self, slug: str, text: str) -> str:
        os.makedirs(os.path.join(self.posts, slug))
        pfad = os.path.join(self.posts, slug, "index.md")
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(text)
        return pfad

    def test_hochrisiko_ohne_freigabe_kommt_nicht_in_die_requeue(self):
        slug = "2026-10-13-versicherung-update-was-sich-jetzt-fuer-dich-aendert"
        pfad = self.lege_an(slug, ki_entwurf(pillar="versicherungen",
                                             titel=VORFALL_TITEL))
        vorher = Path(pfad).read_bytes()
        import park_state
        with mock.patch.object(park_state, "rearm") as rearm:
            rc, ausgabe = still(kr.cmd_promote, argparse.Namespace(promote=slug))
        self.assertEqual(rc, 1)
        rearm.assert_not_called()
        self.assertEqual(Path(pfad).read_bytes(), vorher)
        self.assertIn("E03", ausgabe)
        self.assertIn("--seal", ausgabe)

    def test_gate_defekt_ist_fail_closed(self):
        with mock.patch.object(erg, "evaluate_path",
                               side_effect=RuntimeError("kaputt")):
            grund = kr._fachfreigabe_fehlt("egal.md")
        self.assertIn("fail-closed", grund)

    def test_unlesbarer_entwurf_ist_fail_closed(self):
        slug = "2026-10-13-kaputtes-frontmatter"
        pfad = self.lege_an(slug, "kein Frontmatter\n")
        grund = kr._fachfreigabe_fehlt(pfad)
        self.assertIn("nicht lesen", grund)
        self.assertIn("fail-closed", grund)

    def test_auto_entwurf_passiert_die_sperre(self):
        slug = "2026-10-13-stromfresser-im-haushalt-entlarven"
        pfad = self.lege_an(slug, ki_entwurf(pillar="strom-sparen",
                                             titel="Stromfresser im Haushalt entlarven"))
        self.assertEqual(kr._fachfreigabe_fehlt(pfad), "")

    def test_freigegebener_hochrisiko_entwurf_passiert_die_sperre(self):
        with mock.patch.object(erg, "evaluate_path", return_value={
                "risk": erg.RISK_HIGH, "approved": True, "findings": []}):
            self.assertEqual(kr._fachfreigabe_fehlt("egal.md"), "")


# ---------------------------------------------------------------------------
# Selbsttest der KI-Redaktion trägt die Vertragsprobe
# ---------------------------------------------------------------------------
class SelbsttestTests(unittest.TestCase):
    def test_selbsttest_prueft_den_vertrag(self):
        ok, ausgabe = still(kr._selbsttest_fachfreigabe)
        self.assertTrue(ok, ausgabe)
        self.assertIn("Fachfreigabe-Vertrag (#734)", ausgabe)

    def test_selbsttest_erkennt_einen_ausgehebelten_vertrag(self):
        with mock.patch.object(ks, "fachfreigabe_pruefen",
                               return_value=ks.BAHN_AUTO):
            ok, ausgabe = still(kr._selbsttest_fachfreigabe)
        self.assertFalse(ok)
        self.assertIn("ohne Beauftragung", ausgabe)


if __name__ == "__main__":
    unittest.main()
