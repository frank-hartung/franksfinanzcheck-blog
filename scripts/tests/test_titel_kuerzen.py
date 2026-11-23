#!/usr/bin/env python3
"""Der Titel ist eine Zusage an das Snippet – 60 Zeichen, nicht 64.

ANLASS (22.11.2026)
===================
Der Automationslauf um 08:45 schrieb diesen Artikel live und versiegelte ihn:

    title: 'Kfz-Versicherung vergleichen: Was ändert sich außer dem Beitrag?'

64 Zeichen. `metadaten_wache` (Regel M1, max. 60) meldet das zu Recht, der
Metadaten-Regressionstest der YMYL-Siegelwache fällt – auf `main`, für jeden
PR. Der Prompt bat um „max. 60 Zeichen“; die Description wurde im Parser
gekürzt (`desc[:155]`), der Titel nicht. Es gab also eine Zusage ohne Zähler.

WARUM DIE HEILUNG HIER UND NICHT AM ARTIKEL STEHT
=================================================
Der Titel ist Teil des YMYL-Fingerabdrucks (`content_fingerprint`). Ihn in
einem versiegelten Live-Artikel zu ändern, verlangt eine neue redaktionelle
Freigabe – das darf kein Automat. Diese Datei sichert deshalb die ENTSTEHUNG:
Kein neuer Titel über 60 Zeichen, egal aus welchem Pfad (TITLE-Zeile,
H1-Fallback oder Themenvorgabe). Der eine Altfall bleibt redaktionell.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def _load_generate_drafts():
    spec = importlib.util.spec_from_file_location(
        "_gd_titel", SCRIPTS / "generate_drafts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


import post_utils  # noqa: E402

TITEL_MAX = 60
titel_kuerzen = post_utils.titel_kuerzen
gd = _load_generate_drafts()

# Exakt der Titel aus dem Automationslauf vom 22.11.2026.
SCHADENSFALL = ("Kfz-Versicherung vergleichen: "
                "Was ändert sich außer dem Beitrag?")


class TitelObergrenzeTest(unittest.TestCase):
    def test_schadensfall_wird_gekuerzt(self):
        self.assertEqual(64, len(SCHADENSFALL), "Ausgangslage hat sich geändert")
        kurz = titel_kuerzen(SCHADENSFALL)
        self.assertLessEqual(len(kurz), TITEL_MAX)
        self.assertEqual("Kfz-Versicherung vergleichen", kurz,
                         "Der Hauptteil trägt die Aussage; der Untertitel fällt")

    def test_kurzer_titel_bleibt_unveraendert(self):
        for titel in ("Kurz und gut", "Strom sparen: Die besten Tipps",
                      "Genau sechzig Zeichen lang ist dieser Titel hier, ja!"):
            self.assertEqual(titel, titel_kuerzen(titel))

    def test_kuerzung_endet_nie_mitten_im_wort(self):
        lang = ("Ein sehr langer Titel ohne Trenner der einfach nicht "
                "aufhören will und weiterläuft")
        kurz = titel_kuerzen(lang)
        self.assertLessEqual(len(kurz), TITEL_MAX)
        self.assertTrue(lang.startswith(kurz), "Nur vorne abschneiden")
        self.assertTrue(kurz.endswith(("nicht", "einfach", "der", "ohne")),
                        f"Wortgrenze verletzt: {kurz!r}")

    def test_kein_haengendes_bindewort(self):
        lang = ("Kfz-Versicherung vergleichen und Tarife prüfen und "
                "Beiträge senken und Leistungen lesen")
        kurz = titel_kuerzen(lang)
        self.assertLessEqual(len(kurz), TITEL_MAX)
        self.assertNotIn(kurz.split()[-1].lower(), post_utils._TITEL_STOPP)

    def test_leerer_titel_bleibt_leer(self):
        self.assertEqual("", titel_kuerzen(""))

    def test_parse_article_haelt_die_grenze(self):
        roh = ("TITLE: " + SCHADENSFALL + "\n"
               "DESCRIPTION: Ein Vergleich mit gleicher Fahrleistung und "
               "Selbstbeteiligung, damit der Beitrag wirklich vergleichbar "
               "bleibt und nicht nur die Zahl auf dem Angebot zählt.\n\n"
               "Der Text beginnt hier und ist lang genug für einen Entwurf.\n")
        title, _desc, _body = gd.parse_article(roh, "kfz-versicherung", "Vergleich")
        self.assertLessEqual(len(title), TITEL_MAX,
                             "Der Parser ist die letzte Stelle vor dem Frontmatter")


class SiegelVerweigertUeberlangenTitelTest(unittest.TestCase):
    """Ein Befund, der nicht heilbar ist, darf nicht ins Siegel (#1069)."""

    def test_64_zeichen_ist_ein_befund(self):
        import editorial_review_gate as gate
        befund = gate.titel_befund({"title": SCHADENSFALL})
        self.assertIsNotNone(befund)
        self.assertIn("64 Zeichen", befund)

    def test_kurzer_titel_ist_kein_befund(self):
        import editorial_review_gate as gate
        self.assertIsNone(gate.titel_befund({"title": "Kfz-Versicherung vergleichen"}))
        self.assertIsNone(gate.titel_befund({}))


if __name__ == "__main__":
    unittest.main()
