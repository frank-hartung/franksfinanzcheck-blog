#!/usr/bin/env python3
# ============================================================
#  TESTS: SOCIAL-CLAIMS – unzulässige Versprechen heilen statt ablehnen
#  ------------------------------------------------------------
#  Befund 06.11.2026 (#716-Klasse, eine Ebene tiefer): `social_gate` L3
#  sperrte „garantiert", der Texter hatte den Satz aber vorher aus dem
#  Artikel übernommen. Ergebnis: Der Ökostrom-Artikel war in JEDEM Winkel
#  unsendbar, der Kanal fiel still aus. Diese Tests halten fest, dass die
#  Heilung greift, dass Gate und Texter DIESELBE Sperrliste lesen und dass
#  aus einem belasteten Artikel trotzdem sendbare Beiträge entstehen.
# ============================================================
from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import social_claims as claims          # noqa: E402
import social_channels as sch           # noqa: E402
import social_copywriter as copy        # noqa: E402
import social_gate as gate              # noqa: E402

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
YAML = os.path.join(BLOG_DIR, "data", "social", "channels.yaml")


def _meta() -> dict:
    return {"gate": {"blocked_terms": ["garantiert", "risikofrei", "ohne Risiko"],
                     "forbidden_phrases": ["In der heutigen schnelllebigen Welt"],
                     "min_chars": 60},
            "base_url": "https://franksfinanzcheck.de"}


def _belastet() -> dict:
    """Artikel, dessen Copy-Quelle in jedem Baustein ein Versprechen trägt."""
    return {
        "slug": "probe-versprechen",
        "title": "Solaranlage finanzieren: Schritt für Schritt",
        "description": "So planst du die Finanzierung.",
        "kurzantwort": "Die Förderung ist garantiert, die Anlage risikofrei.",
        "hook": "Die Rendite ist garantiert.",
        "hook_sentences": ["Die Rendite ist garantiert.",
                           "Die Bank gibt die Zusage garantiert."],
        "takeaways": ["Der Zuschuss kommt garantiert.",
                      "Fördertöpfe vorher prüfen und Fristen notieren."],
        "numbers": ["350 € im Jahr"],
        "faq_question": "Was ist zu beachten?",
        "faq_answer": "In der heutigen schnelllebigen Welt zählt jeder Euro.",
        "keywords": ["Solar", "Finanzierung"],
        "tags": ["Solar", "Finanzierung"],
        "pillar": "strom-sparen",
        "url": "https://franksfinanzcheck.de/posts/probe-versprechen/",
        "cover": "", "cover_alt": "",
        "pin_title": "Solaranlage finanzieren",
        "published": "2026-11-01", "draft": False, "path": "", "raw_fm": "",
    }


class Sperrquelle(unittest.TestCase):
    """Eine Sperrliste – gelesen aus der YAML des Hauses."""

    def test_hausliste_wird_gelesen(self) -> None:
        cfg = sch.load_config(YAML)
        sperren = claims.sperrlisten(sch.meta_of(cfg))
        self.assertIn("garantiert", [w.lower() for w in sperren.begriffe])
        self.assertTrue(sperren.phrasen, "die Haus-Sperrliste darf nicht leer sein")

    def test_kanal_erweitert_nie_ab(self) -> None:
        basis = claims.sperrlisten(_meta())
        erweitert = claims.sperrlisten(_meta(), {"gate": {"blocked_terms": ["abzocke"]}})
        self.assertIn("abzocke", erweitert.begriffe)
        for wort in basis.begriffe:
            self.assertIn(wort, erweitert.begriffe,
                          "ein Kanal darf die Haus-Sperre nicht abschalten")

    def test_gate_und_texter_lesen_dieselbe_liste(self) -> None:
        """Der eigentliche Punkt: keine zweite Liste, die driftet."""
        meta = _meta()
        cfg = sch.load_config(YAML)
        haus = claims.sperrlisten(sch.meta_of(cfg))
        # Was das Gate als Verstoß meldet, kennt auch die Heilung.
        pkg = {"text": "Das ist garantiert.", "url": "https://x/posts/a/", "article": {}}
        ok, verstoesse, _ = gate.check(pkg, {"gate": {}}, meta, history=[])
        self.assertFalse(ok)
        self.assertTrue(any("L3" in v for v in verstoesse))
        self.assertIn("garantiert", [w.lower() for w in haus.begriffe])
        # Jede Kanal-Konfiguration erbt die Haus-Sperre vollständig.
        for cid, ch in sch.channel_map(cfg).items():
            with self.subTest(kanal=cid):
                wirksam = claims.sperrlisten(sch.meta_of(cfg), ch)
                for wort in haus.begriffe:
                    self.assertIn(wort, wirksam.begriffe)


class Heilung(unittest.TestCase):
    """Heilung auf Satz-Ebene, Glättung nur im Notfall."""

    def setUp(self) -> None:
        self.sperren = claims.sperrlisten(_meta())

    def test_satz_faellt_struktur_bleibt(self) -> None:
        text = ("Ein Wechsel dauert Minuten.\n\n* Siegel helfen.\n"
                "* Die Versorgung ist garantiert.\n* Preise prüfen.")
        sauber, weg = claims.saeubern(text, self.sperren)
        self.assertNotIn("garantiert", sauber)
        self.assertEqual(len(weg), 1)
        self.assertIn("* Siegel helfen.", sauber)
        self.assertIn("* Preise prüfen.", sauber)

    def test_glättung_bleibt_grammatisch(self) -> None:
        for eingabe, erwartet in (
            ("gesetzlich garantiert", "gesetzlich gesichert"),
            ("garantierte Rendite", "gesicherte Rendite"),
            ("risikofreie Anlage", "risikoarme Anlage"),
        ):
            with self.subTest(eingabe=eingabe):
                out, _ = claims.glaetten(eingabe, self.sperren)
                self.assertEqual(out, erwartet)
                self.assertTrue(self.sperren.sauber(out))

    def test_fail_closed_ohne_ausweg(self) -> None:
        eigen = claims.Sperren(("unmöglich",), ())
        leer, _ = claims.haerten("Das ist unmöglich.", eigen)
        self.assertEqual(leer, "",
                         "lieber kein Satz als ein unzulässiges Versprechen")

    def test_material_wird_vor_dem_bauen_gereinigt(self) -> None:
        artikel, weg = claims.material_saeubern(_belastet(), self.sperren)
        self.assertTrue(weg)
        for feld in ("kurzantwort", "hook", "faq_answer", "description"):
            self.assertTrue(self.sperren.sauber(artikel[feld]),
                            f"{feld} ist noch belastet: {artikel[feld]!r}")


class BeitraegeBleibenSendbar(unittest.TestCase):
    """Der Kanal darf nicht stillfallen – das ist die Lehre aus #716."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.cfg = sch.load_config(YAML)
        cls.meta = sch.meta_of(cls.cfg)
        cls.channels = sch.channel_map(cls.cfg)

    def test_kein_beitrag_traegt_ein_versprechen(self) -> None:
        sperren = claims.sperrlisten(self.meta)
        artikel = _belastet()
        geprueft = 0
        for cid, ch in self.channels.items():
            for angle in (ch.get("angles") or ["nutzen"]):
                pkg = copy.compose(dict(artikel), cid, ch, angle, self.meta, use_llm=False)
                rest = sperren.treffer(" ".join(
                    [pkg.get("text") or "", pkg.get("comment") or "",
                     *(pkg.get("thread") or [])]))
                self.assertEqual(rest, [], f"{cid}/{angle}: {rest}")
                geprueft += 1
        self.assertGreater(geprueft, 20, "zu wenige Kanäle/Winkel geprüft")

    def test_gate_laesst_die_geheilte_fassung_durch(self) -> None:
        """Heilung + Gate zusammen: kein L3 mehr (die anderen Regeln hängen
        vom Einzelfall ab und werden hier nicht beansprucht)."""
        artikel = _belastet()
        for cid, ch in self.channels.items():
            for angle in (ch.get("angles") or ["nutzen"]):
                pkg = copy.compose(dict(artikel), cid, ch, angle, self.meta, use_llm=False)
                _ok, verstoesse, _ = gate.check(pkg, ch, self.meta, history=[])
                l3 = [v for v in verstoesse if v.startswith("L3")]
                self.assertEqual(l3, [], f"{cid}/{angle}: {l3}")

    def test_heilung_ist_sichtbar(self) -> None:
        pkg = copy.compose(_belastet(), "mastodon",
                           self.channels["mastodon"], "nutzen", self.meta, use_llm=False)
        self.assertTrue(pkg.get("heilungen"),
                        "was geheilt wurde, muss im Paket belegt sein")
        self.assertGreaterEqual(len(pkg.get("text") or ""),
                                int((self.meta.get("gate") or {}).get("min_chars") or 0))

    def test_bestand_bleibt_sendbar(self) -> None:
        """Der echte Bestand: kein Artikel verliert durch die Heilung alles."""
        pool = copy.article_pool(base_url=str(self.meta.get("base_url")))
        self.assertTrue(pool)
        sperren = claims.sperrlisten(self.meta)
        for art in pool[:12]:
            pkg = copy.compose(dict(art), "mastodon", self.channels["mastodon"],
                               "nutzen", self.meta, use_llm=False)
            self.assertTrue((pkg.get("text") or "").strip(), f"{art['slug']}: leer")
            self.assertEqual(sperren.treffer(pkg["text"]), [], f"{art['slug']}: belastet")


class SelbsttestLaeuft(unittest.TestCase):
    def test_selftest_gruen(self) -> None:
        self.assertEqual(claims.selbsttest(), 0)


if __name__ == "__main__":
    unittest.main()
