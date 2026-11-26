"""#900: Bytegebundene Reserve-Entwürfe sind für Hygiene-Heiler schreibgeschützt.

Der Vorfall: `data/reserve-readiness.json` belegte drei Reserve-Entwürfe mit
ihrer SHA-256. Danach heilte der Pinterest-Watchdog dieselben Dateien
(Transparenz-Zeile via `spam_guard`, gekürzte `keywords` via Pin-Heiler) und
committete sie – der Nachweis zeigte auf Bytes, die es nicht mehr gab. Beide
Vorgänge waren für sich „grün“; der Widerspruch fiel erst im nächsten Gate auf.

Diese Tests halten die Regel fest, die den Fehler an der Wurzel schließt:

  · `draft: true` **und** `reserve: true` = bytegebunden → Heiler schreiben nicht.
  · die Heiler verschweigen den Fund nicht, sie melden ihn.
  · ohne die zweite Marke bleibt der Heiler scharf (kein stiller Ausfall der
    Heilung – ein Schutz, der zu viel sperrt, wäre derselbe Fehler andersherum).
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import reserve_schreibschutz as schutz  # noqa: E402
import spam_guard as sg  # noqa: E402
import pinterest_duplicate_guard as pdg  # noqa: E402
import pinterest_seo_healer as seo  # noqa: E402

RESERVE_ENTWURF = """---
title: "Testartikel"
draft: true
reserve: true
pin_description: "Alter Pin-Text"
keywords: ["A", "B"]
---

Erster Absatz mit Inhalt.
"""

NORMALER_ENTWURF = RESERVE_ENTWURF.replace("reserve: true\n", "")
LIVE_ARTIKEL = RESERVE_ENTWURF.replace("draft: true\n", "")


class RegelTest(unittest.TestCase):
    """Die Marke selbst: zwei Zeilen, beide nötig, Reihenfolge egal."""

    def test_beide_marken_ergeben_bytebindung(self):
        self.assertTrue(schutz.ist_bytegebunden(RESERVE_ENTWURF))

    def test_nur_draft_ist_kein_reserve_entwurf(self):
        self.assertFalse(schutz.ist_bytegebunden(NORMALER_ENTWURF))

    def test_nur_reserve_ist_kein_entwurf(self):
        self.assertFalse(schutz.ist_bytegebunden(LIVE_ARTIKEL))

    def test_ohne_frontmatter_kein_schutz(self):
        self.assertFalse(schutz.ist_bytegebunden(""))
        self.assertFalse(schutz.ist_bytegebunden("# Nur Markdown\n\nText.\n"))

    def test_windows_zeilenenden_brechen_die_marke_nicht(self):
        self.assertTrue(schutz.ist_bytegebunden(
            RESERVE_ENTWURF.replace("\n", "\r\n")))

    def test_marken_ausserhalb_des_frontmatters_zaehlen_nicht(self):
        text = ("---\ntitle: \"X\"\ndraft: true\n---\n\nreserve: true\n")
        self.assertFalse(schutz.ist_bytegebunden(text))

    def test_geschuetzte_slugs_findet_nur_reserve_entwuerfe(self):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            for slug, inhalt in (("reserve", RESERVE_ENTWURF),
                                 ("entwurf", NORMALER_ENTWURF),
                                 ("live", LIVE_ARTIKEL)):
                (wurzel / slug).mkdir()
                (wurzel / slug / "index.md").write_text(inhalt, encoding="utf-8")
            self.assertEqual({"reserve"}, schutz.geschuetzte_slugs(wurzel))


class SpamGuardTest(unittest.TestCase):
    """B3/B8: Der Heiler, der die Transparenz-Zeile in den Entwurf schrieb."""

    def _fix(self, inhalt, regel="B3"):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "index.md"
            pfad.write_text(inhalt, encoding="utf-8")
            post = {"slug": "kandidat", "path": str(pfad), "content": inhalt}
            with patch.object(sg, "DRY_RUN", False), \
                    patch.object(sg, "audit", lambda *_a, **_k: None):
                geheilt = sg.fix_blog({"kandidat": (post, [(regel, "hard", "Test")])})
            return pfad.read_bytes(), inhalt.encode("utf-8"), geheilt

    def test_reserve_entwurf_bleibt_bytegleich(self):
        danach, vorher, geheilt = self._fix(RESERVE_ENTWURF)
        self.assertEqual(vorher, danach, "bytegebundener Entwurf wurde geschrieben")
        self.assertTrue(any("unangetastet" in zeile for zeile in geheilt),
                        geheilt)

    def test_normaler_entwurf_wird_weiterhin_geheilt(self):
        danach, vorher, _geheilt = self._fix(NORMALER_ENTWURF)
        self.assertNotEqual(vorher, danach, "Heilung ist ausgefallen")
        self.assertIn("Transparenz", danach.decode("utf-8"))


class DuplicateGuardTest(unittest.TestCase):
    """Der Heiler, der die `keywords` der zertifizierten Entwürfe kürzte."""

    def _run(self, inhalt_reserve):
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            posts = wurzel / "content" / "posts"
            for slug, inhalt in (("erst", RESERVE_ENTWURF.replace(
                                      "Alter Pin-Text", "Gleicher Text")),
                                 ("zweit", inhalt_reserve)):
                (posts / slug).mkdir(parents=True)
                (posts / slug / "index.md").write_text(inhalt, encoding="utf-8")
            with patch.object(pdg, "BLOG_DIR", str(wurzel)), \
                    patch.object(pdg, "DO_FIX", True):
                pdg.main()
            return (posts / "zweit" / "index.md").read_text(encoding="utf-8")

    def test_reserve_entwurf_behaelt_seinen_pin_text(self):
        vorher = RESERVE_ENTWURF.replace("Alter Pin-Text", "Gleicher Text")
        self.assertEqual(vorher, self._run(vorher))

    def test_normaler_entwurf_wird_weiterhin_eindeutig(self):
        nachher = self._run(NORMALER_ENTWURF.replace("Alter Pin-Text",
                                                     "Gleicher Text"))
        self.assertNotIn('"Gleicher Text"', nachher,
                         "Der Guard hat den normalen Entwurf nicht mehr geheilt")

    def _run_in_reihenfolge(self, umgekehrt, slugs=("erst", "zweit")):
        """Reserve-Entwurf und normaler Entwurf mit gleichem Pin-Text.

        `umgekehrt` dreht die Reihenfolge, in der das Dateisystem die Ordner
        liefert. Genau daran hing der Test bis zum 14.11.2026: Lokal kam
        `erst` zuerst, in CI `zweit` – dort blieb die Dublette stehen und die
        Prüfung `regression` war rot, ohne dass jemand Code angefasst hatte.
        """
        reserve_slug, normal_slug = slugs
        gleich = "Gleicher Text"
        reserve = RESERVE_ENTWURF.replace("Alter Pin-Text", gleich)
        normal = NORMALER_ENTWURF.replace("Alter Pin-Text", gleich)
        echtes_glob = pdg.glob.glob

        def glob_in_reihenfolge(muster, *a, **kw):
            treffer = sorted(echtes_glob(muster, *a, **kw))
            return treffer[::-1] if umgekehrt else treffer

        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            posts = wurzel / "content" / "posts"
            for slug, inhalt in ((reserve_slug, reserve), (normal_slug, normal)):
                (posts / slug).mkdir(parents=True)
                (posts / slug / "index.md").write_text(inhalt, encoding="utf-8")
            with patch.object(pdg, "BLOG_DIR", str(wurzel)), \
                    patch.object(pdg, "DO_FIX", True), \
                    patch.object(pdg.glob, "glob", glob_in_reihenfolge):
                pdg.main()
            return ((posts / reserve_slug / "index.md").read_text(encoding="utf-8"),
                    (posts / normal_slug / "index.md").read_text(encoding="utf-8"),
                    reserve)

    def test_ergebnis_haengt_nicht_an_der_reihenfolge_des_dateisystems(self):
        for umgekehrt in (False, True):
            with self.subTest(umgekehrt=umgekehrt):
                reserve_nachher, normal_nachher, reserve_vorher = \
                    self._run_in_reihenfolge(umgekehrt)
                self.assertEqual(reserve_vorher, reserve_nachher,
                                 "bytegebundener Entwurf wurde geschrieben")
                self.assertNotIn('"Gleicher Text"', normal_nachher,
                                 "Die Dublette blieb stehen")

    def test_reserve_entwurf_haelt_den_text_auch_wenn_er_spaeter_sortiert(self):
        # Der normale Entwurf steht nach Slug VOR dem Reserve-Entwurf. Früher
        # behielt dann er den Text, der Reserve-Entwurf wurde übersprungen –
        # und beide trugen weiter denselben Pin-Text.
        for umgekehrt in (False, True):
            with self.subTest(umgekehrt=umgekehrt):
                reserve_nachher, normal_nachher, reserve_vorher = \
                    self._run_in_reihenfolge(umgekehrt, slugs=("z-reserve", "a-normal"))
                self.assertEqual(reserve_vorher, reserve_nachher)
                self.assertNotIn('"Gleicher Text"', normal_nachher)

    def test_zwei_normale_entwuerfe_der_erste_nach_slug_behaelt_den_text(self):
        gleich = NORMALER_ENTWURF.replace("Alter Pin-Text", "Gleicher Text")
        for umgekehrt in (False, True):
            with self.subTest(umgekehrt=umgekehrt), tempfile.TemporaryDirectory() as tmp:
                wurzel = Path(tmp)
                posts = wurzel / "content" / "posts"
                for slug in ("a-frueh", "b-spaet"):
                    (posts / slug).mkdir(parents=True)
                    (posts / slug / "index.md").write_text(gleich, encoding="utf-8")
                echtes_glob = pdg.glob.glob

                def glob_in_reihenfolge(muster, *a, _u=umgekehrt, **kw):
                    treffer = sorted(echtes_glob(muster, *a, **kw))
                    return treffer[::-1] if _u else treffer

                with patch.object(pdg, "BLOG_DIR", str(wurzel)), \
                        patch.object(pdg, "DO_FIX", True), \
                        patch.object(pdg.glob, "glob", glob_in_reihenfolge):
                    pdg.main()
                self.assertEqual(gleich, (posts / "a-frueh" / "index.md")
                                 .read_text(encoding="utf-8"))
                self.assertNotIn('"Gleicher Text"', (posts / "b-spaet" / "index.md")
                                 .read_text(encoding="utf-8"))


class HeilbarkeitsTest(unittest.TestCase):
    """Der Schließweg: heilbar heißt zählbar, unheilbar heißt gemeldet.

    Befund vom 17.11.2026 (Vorgang #1227): Der Guard beendete sich mit
    `fixed >= len(problems)`. Eine Gruppe aus zwei bytegebundenen
    Reserve-Entwürfen ist konstruktiv nicht heilbar – der Zähler konnte sie
    nie erreichen, der Lauf blieb für immer rot. Ein Befund ohne Schließweg
    ist kein Befund, sondern eine Sackgasse.

    Die zweite Hälfte ist die Gegenprobe zur Gegenprobe: Ein Umbau, der
    „nur die heilbaren zählt“, darf nicht heilen, was er nicht darf. Genau
    das täte die Fassung aus #1227 (sie heilt nur den ERSTEN nicht
    geschützten Eintrag): Steht ein bytegebundener Entwurf neben zwei
    normalen, bliebe die Dublette zwischen ihm und dem zweiten normalen
    Entwurf stehen – bei Rückgabe 0.
    """

    GLEICH = "Gleicher Text"

    def _projekt(self, inhalt_map):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        wurzel = Path(tmp.name)
        posts = wurzel / "content" / "posts"
        for slug, inhalt in inhalt_map.items():
            (posts / slug).mkdir(parents=True)
            (posts / slug / "index.md").write_text(inhalt, encoding="utf-8")
        return wurzel, posts

    def _fix(self, inhalt_map):
        wurzel, posts = self._projekt(inhalt_map)
        with patch.object(pdg, "BLOG_DIR", str(wurzel)), \
                patch.object(pdg, "DO_FIX", True):
            code = pdg.main()
        return code, {slug: (posts / slug / "index.md").read_text(encoding="utf-8")
                      for slug in inhalt_map}

    def test_geschuetzter_entwurf_und_zwei_normale_werden_alle_eindeutig(self):
        reserve = RESERVE_ENTWURF.replace("Alter Pin-Text", self.GLEICH)
        normal = NORMALER_ENTWURF.replace("Alter Pin-Text", self.GLEICH)
        code, nachher = self._fix({"a-reserve": reserve, "b-normal": normal,
                                   "c-normal": normal})
        self.assertEqual(code, 0)
        self.assertEqual(nachher["a-reserve"], reserve,
                         "bytegebundener Entwurf wurde geschrieben")
        for slug in ("b-normal", "c-normal"):
            self.assertNotIn(f'"{self.GLEICH}"', nachher[slug],
                             f"{slug}: Dublette blieb neben dem geschützten "
                             f"Entwurf stehen")

    def test_zwei_geschuetzte_entwuerfe_melden_statt_zu_scheitern(self):
        reserve = RESERVE_ENTWURF.replace("Alter Pin-Text", self.GLEICH)
        code, nachher = self._fix({"a-reserve": reserve, "b-reserve": reserve})
        self.assertEqual(code, 1, "Unheilbare Gruppe muss rot bleiben")
        for slug in ("a-reserve", "b-reserve"):
            self.assertEqual(nachher[slug], reserve,
                             "Ein bytegebundener Entwurf wurde geschrieben")

    def test_reine_normale_gruppe_bleibt_gruen(self):
        normal = NORMALER_ENTWURF.replace("Alter Pin-Text", self.GLEICH)
        code, nachher = self._fix({"a-normal": normal, "b-normal": normal})
        self.assertEqual(code, 0)
        self.assertNotIn(f'"{self.GLEICH}"', nachher["b-normal"])


class SeoHealerTest(unittest.TestCase):
    def test_heal_article_verweigert_reserve_entwurf(self):
        artikel = {"slug": "kandidat", "reserve": True, "content": RESERVE_ENTWURF,
                   "path": "/tmp/nie-geschrieben.md", "title": "Testartikel"}
        geaendert, aktionen = seo.heal_article(artikel)
        self.assertFalse(geaendert)
        self.assertTrue(any("unangetastet" in a for a in aktionen), aktionen)

    def test_load_articles_setzt_die_marke_aus_dem_frontmatter(self):
        quelle = (SCRIPTS / "pinterest_seo_healer.py").read_text(encoding="utf-8")
        self.assertIn('"reserve": schutz.ist_bytegebunden(content)', quelle)


class VertragTest(unittest.TestCase):
    """Strukturvertrag: keine der drei Dateien darf den Haken wieder verlieren."""

    DATEIEN = ("spam_guard.py", "pinterest_duplicate_guard.py",
               "pinterest_seo_healer.py")

    def test_jeder_heiler_fragt_den_schutz(self):
        for name in self.DATEIEN:
            with self.subTest(datei=name):
                quelle = (SCRIPTS / name).read_text(encoding="utf-8")
                self.assertIn("reserve_schreibschutz", quelle)
                self.assertIn("ist_bytegebunden", quelle)

    def test_faktenfrische_schuetzt_korpus_und_erlaubt_nur_reserve_kette(self):
        """#1230: Korpus-Lauf lässt bytegebundene Entwürfe unangetastet;
        nur `reserve_finisher.py` mit `--file --erlaube-reserve` darf die
        Erstrecherche vor der Neuzertifizierung ausführen."""
        import faktenfrische as ff

        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "index.md"
            pfad.write_text(RESERVE_ENTWURF, encoding="utf-8")
            art = {
                "slug": "2026-11-25-probe",
                "titel": "Probe",
                "pfad": str(pfad),
                "bereich": "posts",
                "_faellig": {"faellig": True, "grund": "Erstrecherche", "frist": None},
                "_geo": {"prozent": 50, "offen": []},
            }
            # 1) Default (Korpus-Lauf): bytegebunden bleibt unangetastet (#900).
            eintrag, offen = ff.verarbeite_seite(art, {}, trocken=True, schreiben=False)
            self.assertFalse(offen)
            self.assertIn("übersprungen", eintrag["fachpruefung"])

            # 2) Reserve-Kette (`erlaube_reserve=True`): Recherche wird ausgeführt.
            with patch.object(ff, "recherchiere", return_value={"treffer": [], "fehler": []}) as r_mock, \
                 patch.object(ff, "claude_fachpruefung", return_value=([], [], "offline")), \
                 patch.object(ff, "dossier_schreiben"):
                eintrag2, _ = ff.verarbeite_seite(
                    art, {}, trocken=True, schreiben=False, erlaube_reserve=True
                )
            r_mock.assert_called_once()
            self.assertNotIn("übersprungen", eintrag2["fachpruefung"])

            # 3) CLI: `--erlaube-reserve` ohne `--file` ist unzulässig (fail-closed).
            with patch.object(ff.sys, "argv", ["faktenfrische.py", "--erlaube-reserve"]):
                with self.assertRaises(SystemExit) as cm:
                    ff.main()
            self.assertEqual(cm.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
