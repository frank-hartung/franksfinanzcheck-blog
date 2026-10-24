"""Regressionstests der Pinterest-Zielwache (#822, 24.10.2026).

Der Befund: P10 meldete fünf Tage lang einen geparkten Artikel als Defekt,
und der Masterplan trug sieben Pins auf Ziele, die keine Artikel-Seite mehr
sind. Beides hat dieselbe Wurzel: Es gab keine Stelle, die „ist dieses Ziel
noch ein Artikel?“ beantwortet. `scripts/pinterest_ziele.py` ist diese Stelle.

Diese Datei friert die Regel ein (Status), ihre Heilung (Retarget/Park/Queue)
und die zwei Grenzen, an denen ein Heiler gefährlich wird: eine nicht lesbare
Quelle (fail-closed) und eine Datei, deren Text nicht zum Parser passt.
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pinterest_ziele as pz  # noqa: E402

SSOT = """eintraege:
  - {von: "/posts/alt/", nach: "/posts/live/", regel: "B", grund: "gleiche Suchabsicht"}
  - {von: "/posts/umzug/", nach: "/posts/live/", regel: "A", grund: "Ordner umbenannt"}
  - {von: "/posts/geparkt/", nach: "/pillar/versicherungen/", regel: "C", grund: "kein Beitrag"}
"""

PLAN = """pins:
- tag: 1
  typ: EP
  titel: 'Live: bleibt'
  url: https://franksfinanzcheck.de/posts/live/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
  beschreibung: '*Werbung | Bleibt.'
  blog_url: https://franksfinanzcheck.de/posts/live/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
- tag: 2
  typ: EP
  titel: 'Alt: Nachfolger vorhanden'
  url: https://franksfinanzcheck.de/posts/alt/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
  beschreibung: '*Werbung | Wird umgeschrieben.'
  blog_url: https://franksfinanzcheck.de/posts/alt/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
- tag: 3
  typ: EP
  titel: 'Geparkt: kein gleichwertiger Beitrag'
  url: https://franksfinanzcheck.de/posts/geparkt/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
  beschreibung: '*Werbung | Wird geparkt.'
  blog_url: https://franksfinanzcheck.de/posts/geparkt/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
- tag: 4
  typ: EP
  titel: 'Entwurf: Inhalt existiert als Draft'
  url: https://franksfinanzcheck.de/posts/entwurf/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
  beschreibung: '*Werbung | Wird geparkt.'
  blog_url: https://franksfinanzcheck.de/posts/entwurf/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
- tag: 5
  typ: EP
  titel: 'Fehlt: gar kein Inhalt'
  url: https://franksfinanzcheck.de/posts/fehlt/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
  beschreibung: '*Werbung | Wird geparkt.'
  blog_url: https://franksfinanzcheck.de/posts/fehlt/?utm_source=pinterest&utm_medium=social&utm_campaign=pins
"""


def baue_repo(root: Path, plan: str = PLAN, ssot: str = SSOT) -> Path:
    """Minimaler Blog: zwei Live-Ziele, ein Draft, eine Pillar, eine SSOT."""
    for slug, draft in (("live", False), ("entwurf", True)):
        d = root / "content" / "posts" / slug
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.md").write_text(
            "---\ntitle: X\n" + ("draft: true\n" if draft else "") + "---\nText\n",
            encoding="utf-8")
    d = root / "content" / "pillar" / "versicherungen"
    d.mkdir(parents=True, exist_ok=True)
    (d / "index.md").write_text("---\ntitle: P\n---\n", encoding="utf-8")
    (root / "data").mkdir(parents=True, exist_ok=True)
    (root / pz.SSOT_REL).write_text(ssot, encoding="utf-8")
    (root / pz.ENTFALLEN_REL).write_text("eintraege: []\n", encoding="utf-8")
    (root / pz.PLAN_REL).write_text(plan, encoding="utf-8")
    return root


class ZielStatusTests(unittest.TestCase):
    def test_url_pfad_normalisiert_query_www_und_slash(self):
        self.assertEqual(
            pz.url_pfad("https://www.franksfinanzcheck.de/posts/x?utm_source=pinterest"),
            "/posts/x/")
        self.assertEqual(pz.url_pfad(""), "")
        self.assertEqual(pz.url_pfad("https://franksfinanzcheck.de/pillar/strom-sparen"),
                         "/pillar/strom-sparen/")

    def test_status_der_fuenf_faelle(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            self.assertEqual(pz.ziel_status(root, "/posts/live/"), (pz.ARTIKEL, "/posts/live/"))
            self.assertEqual(pz.ziel_status(root, "/pillar/versicherungen/"),
                             (pz.PILLAR, "/pillar/versicherungen/"))
            self.assertEqual(pz.ziel_status(root, "/posts/alt/"),
                             (pz.WEITERLEITUNG, "/posts/live/"))
            self.assertEqual(pz.ziel_status(root, "/posts/entwurf/"), (pz.GEPARKT, None))
            self.assertEqual(pz.ziel_status(root, "/posts/fehlt/"), (pz.FEHLT, None))
            self.assertEqual(pz.ziel_status(root, "")[0], pz.LEER)
            self.assertEqual(pz.ziel_status(root, "https://fremd.example/x/")[0], pz.FREMD)
            self.assertEqual(pz.ziel_status(root, "/go/strom/")[0], pz.FREMD)

    def test_draft_ist_nicht_live_obwohl_die_datei_existiert(self):
        """Die Live-Wahrheit kommt aus derselben Funktion wie bei url_wache."""
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            self.assertNotIn("/posts/entwurf/", pz.live_urls(root))
            self.assertIn("/posts/live/", pz.live_urls(root))

    def test_fehlende_quelle_ist_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            (root / pz.SSOT_REL).unlink()
            with self.assertRaises(pz.QuellenFehler):
                pz.ziel_status(root, "/posts/live/")

    def test_quelle_ohne_schluessel_ist_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp), ssot='stand: "2026-10-24"\n')
            with self.assertRaises(pz.QuellenFehler):
                pz.lade_weiterleitungen(root)

    def test_leere_quelle_ist_ein_gueltiger_zustand(self):
        """Kein einziger Alias ist erlaubt – ein leerer Zustand darf nie
        als Dauerbefund enden (sonst wäre der Heiler selbst der Dauerläufer)."""
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp), ssot="eintraege: []\n")
            self.assertEqual(pz.lade_weiterleitungen(root), {})
            self.assertEqual(pz.ziel_status(root, "/posts/live/")[0], pz.ARTIKEL)


class HeilungTests(unittest.TestCase):
    def test_pruefung_ohne_fix_schreibt_nichts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            vorher = (root / pz.PLAN_REL).read_text(encoding="utf-8")
            offen, geheilt = pz.heile(root, fix=False)
            self.assertEqual(len(offen), 4)
            self.assertEqual(geheilt, [])
            self.assertEqual((root / pz.PLAN_REL).read_text(encoding="utf-8"), vorher)
            self.assertFalse((root / pz.PARK_REL).exists())

    def test_retarget_nur_auf_erklaerte_live_nachfolger(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            offen, geheilt = pz.heile(root, fix=True)
            self.assertEqual(offen, [])
            plan = (root / pz.PLAN_REL).read_text(encoding="utf-8")
            self.assertNotIn("/posts/alt/", plan)
            self.assertIn("https://franksfinanzcheck.de/posts/live/" + pz.PIN_UTM, plan)
            # Der Pin-Text bleibt unangetastet – nur das Ziel wird ersetzt.
            self.assertIn("'*Werbung | Wird umgeschrieben.'", plan)
            self.assertIn("'Live: bleibt'", plan)

    def test_regel_c_und_fehlende_ziele_werden_geparkt_nicht_geloescht(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            _offen, geheilt = pz.heile(root, fix=True)
            aktionen = sorted(h["aktion"] for h in geheilt)
            self.assertEqual(aktionen, ["parken", "parken", "parken", "retarget"])
            park = (root / pz.PARK_REL).read_text(encoding="utf-8")
            for titel in ("Geparkt: kein gleichwertiger Beitrag",
                          "Entwurf: Inhalt existiert als Draft",
                          "Fehlt: gar kein Inhalt"):
                self.assertIn(titel, park)
            self.assertIn("hinweis", park)  # Content-Verlust wird erklärt
            plan = (root / pz.PLAN_REL).read_text(encoding="utf-8")
            self.assertEqual(plan.count("- tag:"), 2)

    def test_heilung_ist_idempotent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            pz.heile(root, fix=True)
            plan = (root / pz.PLAN_REL).read_text(encoding="utf-8")
            park = (root / pz.PARK_REL).read_text(encoding="utf-8")
            offen, geheilt = pz.heile(root, fix=True)
            self.assertEqual((offen, geheilt), ([], []))
            self.assertEqual((root / pz.PLAN_REL).read_text(encoding="utf-8"), plan)
            self.assertEqual((root / pz.PARK_REL).read_text(encoding="utf-8"), park)

    def test_queue_eintraege_werden_entfernt_nicht_geparkt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            (root / pz.QUEUE_REL).write_text(
                "pins:\n"
                "- tag: 9\n  titel: 'Queue geparkt'\n"
                "  url: https://franksfinanzcheck.de/posts/geparkt/\n",
                encoding="utf-8")
            offen, geheilt = pz.heile(root, fix=True)
            self.assertEqual(offen, [])
            self.assertIn("queue", [h["aktion"] for h in geheilt])
            self.assertNotIn("Queue geparkt",
                             (root / pz.PARK_REL).read_text(encoding="utf-8"))
            self.assertNotIn("Queue geparkt",
                             (root / pz.QUEUE_REL).read_text(encoding="utf-8"))

    def test_quelle_verschwindet_bleibt_alles_unveraendert(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            plan = (root / pz.PLAN_REL).read_text(encoding="utf-8")
            (root / pz.SSOT_REL).unlink()
            with self.assertRaises(pz.QuellenFehler):
                pz.heile(root, fix=True)
            self.assertEqual((root / pz.PLAN_REL).read_text(encoding="utf-8"), plan)
            self.assertFalse((root / pz.PARK_REL).exists())

    def test_text_und_parser_uneinig_ist_fail_closed(self):
        """Eingerückte Blöcke: YAML liest 1 Pin, der Textheiler 0 – fail-closed."""
        inline = ("pins:\n"
                  "  - tag: 1\n"
                  "    titel: 'Eingerückt'\n"
                  "    url: https://franksfinanzcheck.de/posts/fehlt/\n")
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp), plan=inline)
            with self.assertRaises(pz.QuellenFehler):
                pz.heile(root, fix=True)
            self.assertEqual((root / pz.PLAN_REL).read_text(encoding="utf-8"), inline)


class PlanPflichtTests(unittest.TestCase):
    def test_fehlender_masterplan_ist_fail_closed(self):
        """C2: Ohne Plan ist P14 nicht gemessen – das ist kein Grün."""
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            (root / pz.PLAN_REL).unlink()
            with self.assertRaises(pz.QuellenFehler):
                pz.befunde(root)
            with self.assertRaises(pz.QuellenFehler):
                pz.heile(root, fix=True)


class WeiterleitungsEintragTests(unittest.TestCase):
    def test_live_artikel_entfernt_nur_seinen_eintrag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp))
            mit_live = SSOT + ('  - {von: "/posts/live/", nach: "/pillar/versicherungen/", '
                               'regel: "C", grund: "überdeckt Live-Artikel"}\n')
            (root / pz.SSOT_REL).write_text(mit_live, encoding="utf-8")
            ok, meldung = pz.entferne_weiterleitung(root, "/posts/live/", fix=True)
            self.assertTrue(ok, meldung)
            text = (root / pz.SSOT_REL).read_text(encoding="utf-8")
            self.assertNotIn('von: "/posts/live/"', text)
            self.assertIn('von: "/posts/alt/"', text)  # andere Einträge bleiben
            self.assertIn("eintraege:", text)

    def test_mehrzeiliger_eintrag_wird_nicht_angefasst(self):
        mehrzeilig = ('eintraege:\n'
                      '  - von: "/posts/live/"\n'
                      '    nach: "/pillar/versicherungen/"\n'
                      '    regel: "C"\n'
                      '    grund: "mehrzeilig"\n')
        with tempfile.TemporaryDirectory() as tmp:
            root = baue_repo(Path(tmp), ssot=mehrzeilig)
            ok, meldung = pz.entferne_weiterleitung(root, "/posts/live/", fix=True)
            self.assertFalse(ok)
            self.assertIn("Handentscheidung", meldung)
            self.assertEqual((root / pz.SSOT_REL).read_text(encoding="utf-8"), mehrzeilig)


class SelbsttestTests(unittest.TestCase):
    def test_sabotage_schutz_ist_gruen(self):
        self.assertEqual(pz._selftest(), [])


if __name__ == "__main__":
    unittest.main()
