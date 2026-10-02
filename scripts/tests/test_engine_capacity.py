#!/usr/bin/env python3
"""Unit-Tests für engine_capacity.py – die ehrliche Kapazitäts-Rechnung.

ISSUE #521 (Tagesdefizit 02.10.2026, 0/2 LIVE)
===============================================
Am 02.10.2026 meldete der Pre-Flight „187 Themen, 157 frei“ und ließ den
Lauf grün starten. Der Disponent, der das Thema tatsächlich zieht, fand
zur selben Zeit **drei**. Die Engine produzierte vier Artikel – zwei davon
zu YMYL-Themen, die per Vertrag nie ohne menschliche Freigabe live gehen –
und veröffentlichte null.

Zwei Maße für dieselbe Frage sind kein Messfehler, sondern ein
Konstruktionsfehler: Eine grüne Lampe, die an einem anderen Kabel hängt
als die Maschine, ist schlimmer als gar keine Lampe.

Dieses Modul prüft die drei Zusagen der Reparatur:

  1. BAHN-TRENNUNG   YMYL-Themen landen nie in der Automatik-Bahn, aber
                     sie verschwinden auch nicht – die Fachbahn erreicht
                     sie weiterhin.
  2. EIN MASS        `lage()` zählt frei disponierbare Themen ausschließlich
                     über `reserve_topics.disponieren` – es gibt keine
                     zweite Zählregel, die wieder auseinanderlaufen könnte.
  3. NEBENWIRKUNGS-  Die Messung ruft kein LLM und schreibt keine Datei.
     FREIHEIT        Eine Diagnose, die den Zustand verändert, den sie
                     misst, ist keine Diagnose.
"""
from __future__ import annotations

import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import engine_capacity as ec  # noqa: E402
import reserve_topics as rt  # noqa: E402


FM_HOCH = """---
title: "Reisekrankenversicherung: Das musst du wissen"
pillar: "versicherungen"
draft: true
redaktionelle_pruefung:
  risikoklasse: "hoch"
  status: "ausstehend"
---

Text.
"""

FM_FREI = """---
title: "Hausratversicherung optimieren"
pillar: "versicherungen"
draft: false
redaktionelle_pruefung:
  risikoklasse: "hoch"
  status: "freigegeben"
---

Text.
"""

FM_STANDARD = """---
title: "Stromanbieter wechseln und sparen"
pillar: "energie"
draft: true
---

Text.
"""


def _posts(tmp: Path, **dateien: str) -> Path:
    posts = tmp / "posts"
    posts.mkdir(parents=True, exist_ok=True)
    for name, inhalt in dateien.items():
        d = posts / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.md").write_text(inhalt, encoding="utf-8")
    return posts


class BahnTrennungTests(unittest.TestCase):
    """Zusage 1: Risiko entscheidet über die Bahn, nicht über das Dasein."""

    def test_ymyl_thema_kommt_in_die_fachbahn(self):
        for titel in ("Reisekrankenversicherung: Das musst du wissen",
                      "Berufsunfähigkeitsversicherung vergleichen",
                      "Riester-Rente: Lohnt sie sich 2026 noch?"):
            with self.subTest(titel=titel):
                self.assertEqual(ec.bahn_fuer_thema({"title": titel}),
                                 ec.BAHN_FACHFREIGABE)

    def test_alltagsthema_bleibt_in_der_automatik(self):
        for titel in ("Stromanbieter wechseln und bis zu 300 Euro sparen",
                      "Haushaltsbuch führen: App, Excel oder Papier?",
                      "Black Friday DSL-Deals: Diese Angebote lohnen sich"):
            with self.subTest(titel=titel):
                self.assertEqual(ec.bahn_fuer_thema({"title": titel}),
                                 ec.BAHN_AUTO)

    def test_kein_thema_geht_verloren(self):
        """Die Bahnen sind eine Partition, keine Auswahl."""
        topics = [{"title": t} for t in (
            "Reisekrankenversicherung: Das musst du wissen",
            "Stromanbieter wechseln und sparen",
            "Riester-Rente: Lohnt sie sich 2026 noch?",
            "Haushaltsbuch führen: App, Excel oder Papier?")]
        verteilt = ec.nach_bahn(topics)
        self.assertEqual(
            sum(len(v) for v in verteilt.values()), len(topics),
            "Summe der Bahnen muss den Pool ergeben – sonst verschwinden "
            "Themen lautlos")
        self.assertEqual(set(verteilt), set(ec.BAHNEN))

    def test_klassifikation_stammt_vom_redaktions_gate(self):
        """Keine zweite Kopie der Risiko-Muster (SSOT-Vertrag)."""
        quelle = (Path(__file__).resolve().parents[1]
                  / "engine_capacity.py").read_text(encoding="utf-8")
        self.assertIn("editorial_review_gate", quelle)
        self.assertNotIn("HIGH_PATTERNS = ", quelle,
                         "die Risiko-Muster wohnen genau einmal – im "
                         "editorial_review_gate")


class EinMassTests(unittest.TestCase):
    """Zusage 2: Pre-Flight und Disponent zählen mit derselben Regel."""

    def test_freie_themen_kommen_von_disponieren(self):
        quelle = (Path(__file__).resolve().parents[1]
                  / "engine_capacity.py").read_text(encoding="utf-8")
        self.assertIn("disponieren(", quelle,
                      "lage() muss mit dem Maß des Disponenten messen – "
                      "genau diese Lücke war Issue #521")

    def test_gesperrtes_thema_zaehlt_nicht_als_frei(self):
        topics = [{"title": "Stromanbieter wechseln und sparen"},
                  {"title": "Haushaltsbuch führen: App, Excel oder Papier?"}]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            ledger = tmp / "ledger.json"
            posts = _posts(tmp)
            vorher = ec.lage(topics, posts_dir=posts, ledger=ledger)
            rt.merke("Stromanbieter wechseln und sparen", True,
                     "produziert: irgendwas", pfad=ledger)
            nachher = ec.lage(topics, posts_dir=posts, ledger=ledger)
        self.assertEqual(vorher["frei_auto"], 2)
        self.assertEqual(nachher["frei_auto"], 1,
                         "ein 180 Tage gesperrtes Thema ist nicht frei")

    def test_ymyl_thema_zaehlt_nie_zur_automatik_kapazitaet(self):
        topics = [{"title": "Reisekrankenversicherung: Das musst du wissen"},
                  {"title": "Riester-Rente: Lohnt sie sich 2026 noch?"},
                  {"title": "Haushaltsbuch führen: App, Excel oder Papier?"}]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            daten = ec.lage(topics, posts_dir=_posts(tmp),
                            ledger=tmp / "l.json")
        self.assertEqual(daten["themen_gesamt"], 3)
        self.assertEqual(daten["frei_auto"], 1,
                         "nur das Alltagsthema darf die Automatik-Kapazität "
                         "erhöhen")
        self.assertEqual(daten["themen_fachfreigabe"], 2)

    def test_verdikt_folgt_dem_tagesziel(self):
        viele = [{"title": f"Stromtarif {i} wechseln und sparen"}
                 for i in range(40)]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            posts, ledger = _posts(tmp), tmp / "l.json"
            self.assertEqual(
                ec.lage(viele, posts_dir=posts, ledger=ledger)["verdikt"], "ok")
            self.assertEqual(
                ec.lage([], posts_dir=posts, ledger=ledger)["verdikt"],
                "erschoepft")
            knapp = ec.lage(viele[:3], posts_dir=posts, ledger=ledger)
            self.assertEqual(knapp["verdikt"], "knapp",
                             "drei freie Themen bei Tagesziel 2 decken den "
                             "Tag, aber keinen Ausfall – genau die Lage vom "
                             "02.10.2026")


class FachfreigabeBahnTests(unittest.TestCase):
    """Die menschliche Bahn hat eine endliche Kapazität – und sagt das."""

    def test_bahn_schliesst_bei_vollem_pruefstapel(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = _posts(Path(tmp), **{
                f"2026-10-0{i}-hoch-{i}": FM_HOCH for i in range(1, 6)})
            bahn = ec.fachfreigabe_bahn(posts, limit=3)
        self.assertFalse(bahn["geoeffnet"])
        self.assertEqual(bahn["offen"], 5)
        self.assertIn("3", bahn["grund"])

    def test_bahn_ist_offen_wenn_platz_ist(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = _posts(Path(tmp), **{"2026-10-01-hoch-1": FM_HOCH})
            bahn = ec.fachfreigabe_bahn(posts, limit=3)
        self.assertTrue(bahn["geoeffnet"])
        self.assertEqual(bahn["offen"], 1)

    def test_alltagsartikel_belegt_die_fachbahn_nicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            posts = _posts(Path(tmp), **{
                "2026-10-02-standard": FM_STANDARD,
                "2026-10-03-standard-b": FM_STANDARD})
            bahn = ec.fachfreigabe_bahn(posts, limit=3)
        self.assertEqual(bahn["offen"], 0,
                         "nur Hochrisiko-Artikel belegen die menschliche Bahn")
        self.assertTrue(bahn["geoeffnet"])

    def test_behauptete_freigabe_ohne_siegel_belegt_die_bahn_weiter(self):
        """Fail-closed: `status: freigegeben` allein ist keine Freigabe.

        Ohne gültigen Inhalts-Hash (E17) gilt der Artikel als offen. Sonst
        könnte sich die Bahn selbst leerschreiben, indem irgendwo ein
        Status-Feld gesetzt wird – und der WIP-Deckel wäre wertlos.
        """
        with tempfile.TemporaryDirectory() as tmp:
            posts = _posts(Path(tmp), **{"2026-10-01-behauptet": FM_FREI})
            bahn = ec.fachfreigabe_bahn(posts, limit=3)
        self.assertEqual(bahn["offen"], 1)
        self.assertIn("E17", bahn["stapel"][0]["codes"],
                      "fehlendes Freigabe-Siegel muss der Grund sein")


class NebenwirkungsfreiheitTests(unittest.TestCase):
    """Zusage 3: Messen verändert nichts."""

    def test_lage_schreibt_keine_datei(self):
        topics = [{"title": "Stromanbieter wechseln und sparen"}]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            posts = _posts(tmp)
            ledger = tmp / "ledger.json"
            vorher = sorted(p.relative_to(tmp) for p in tmp.rglob("*"))
            ec.lage(topics, posts_dir=posts, ledger=ledger)
            ec.lage(topics, posts_dir=posts, ledger=ledger)
            nachher = sorted(p.relative_to(tmp) for p in tmp.rglob("*"))
        self.assertEqual(vorher, nachher,
                         "die Kapazitäts-Messung darf den Zustand nicht "
                         "verändern, den sie misst")

    def test_kein_netzaufruf_im_modul(self):
        quelle = (Path(__file__).resolve().parents[1]
                  / "engine_capacity.py").read_text(encoding="utf-8")
        for verboten in ("urllib", "requests", "GROQ_API_KEY",
                         "GEMINI_API_KEY", "http://", "https://api"):
            self.assertNotIn(verboten, quelle,
                             f"„{verboten}“ gehört nicht in eine Diagnose – "
                             "sie muss offline und kostenlos laufen")

    def test_messung_ist_wiederholbar(self):
        topics = [{"title": "Stromanbieter wechseln und sparen"},
                  {"title": "Reisekrankenversicherung: Das musst du wissen"}]
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            posts, ledger = _posts(tmp), tmp / "l.json"
            a = ec.lage(topics, posts_dir=posts, ledger=ledger)
            b = ec.lage(topics, posts_dir=posts, ledger=ledger)
        self.assertEqual(a, b)


class SchnittstellenTests(unittest.TestCase):
    """Verträge, auf die sich Pre-Flight, Engine und Issue verlassen."""

    def test_lage_liefert_alle_erwarteten_schluessel(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            daten = ec.lage([{"title": "Stromtarif wechseln und sparen"}],
                            posts_dir=_posts(tmp), ledger=tmp / "l.json")
        for key in ("verdikt", "befund", "themen_gesamt", "themen_auto",
                    "themen_fachfreigabe", "frei_auto", "frei_fachfreigabe",
                    "min_artikel_pro_tag", "puffer_bedarf", "fachfreigabe",
                    "warnungen", "naechste_auto"):
            self.assertIn(key, daten, f"„{key}“ ist ein Vertrag mit "
                                      "bot_preflight/engine_issue")
        self.assertIn(daten["verdikt"], ("ok", "knapp", "erschoepft"))

    def test_preflight_bricht_bei_engpass_nicht_ab(self):
        """Ein leerer Pool heilt nicht dadurch, dass die Engine stillsteht."""
        quelle = (Path(__file__).resolve().parents[1]
                  / "bot_preflight.py").read_text(encoding="utf-8")
        self.assertIn("check_capacity", quelle)
        block = quelle[quelle.index("def check_capacity"):]
        block = block[:block.index("\ndef ") if "\ndef " in block else len(block)]
        self.assertNotIn("sys.exit", block)
        self.assertNotIn("return False", block,
                         "Kapazität darf den Lauf nie scheitern lassen – "
                         "Re-Queue und Reserve bleiben sinnvolle Arbeit")

    def test_preflight_nutzt_das_ehrliche_mass(self):
        quelle = (Path(__file__).resolve().parents[1]
                  / "bot_preflight.py").read_text(encoding="utf-8")
        self.assertIn("engine_capacity", quelle,
                      "der Pre-Flight muss mit dem Maß des Disponenten "
                      "messen – sonst wiederholt sich Issue #521")
        self.assertIn("abgleich", quelle,
                      "Phantom-Sperren müssen VOR der Messung fallen")

    def test_engine_waehlt_nur_aus_der_auto_bahn(self):
        quelle = (Path(__file__).resolve().parents[1]
                  / "engine_generate.py").read_text(encoding="utf-8")
        self.assertIn("nur_auto", quelle,
                      "publish_one_article darf keinen LIVE-Slot an ein "
                      "Thema geben, das nur ein Mensch freigeben kann")

    def test_selftest_laeuft_und_ist_gruen(self):
        puffer = io.StringIO()
        with redirect_stdout(puffer):
            rc = ec.run_selftest()
        self.assertEqual(rc, 0, puffer.getvalue())
        self.assertIn("grün", puffer.getvalue())


if __name__ == "__main__":
    unittest.main(verbosity=2)
