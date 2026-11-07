"""Regression #1110: Kein Automatik-Commit verliert ein M4-Pflichtfeld.

Befund 06.11.2026: Der Gate-Heilungs-Commit des Deploy-Laufs (Content-Bot,
`0b55fca`) schrieb den Frontmatter-Block des Ökostrom-Artikels neu und ließ die
`kurzantwort` fallen – der Artikel ging ohne Kurzantwort live (M4).

Diese Tests frieren die Dauerheilung ein: die Verlust-Wache erkennt die Klasse,
holt bytegenau aus HEAD zurück (Body bleibt gleich, nichts wird erfunden), und
sie steht im Deploy-Pfad VOR dem Content-Bot-Commit. Der Vorfall selbst wird
gegen den ECHTEN Artikel nachgespielt – nicht gegen eine erfundene Fixture.
"""
import os
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import metadaten_wache as mw          # noqa: E402
import pflichtfeld_verlust_wache as wache  # noqa: E402
import post_utils as pu               # noqa: E402

VORFALL = ("content/posts/2026-10-28-oekostrom-anbieter-wechseln-"
           "sicher-gruen-und-bezahlbar/index.md")

GUT = (
    '---\n'
    'title: "Ökostrom wechseln: sicher und grün"\n'
    'description: "So wechselst du den Ökostrom-Anbieter sicher, grün und '
    'bezahlbar – mit geprüften Siegeln und einem klaren Ablauf."\n'
    'date: 2026-10-28T06:00:00Z\n'
    'draft: false\n'
    'kurzantwort: "Ein Wechsel ist jederzeit möglich; echte Ökotarife '
    'erkennst du an Siegeln wie Grüner Strom oder ok-power."\n'
    'quellen:\n'
    '  - id: "Q1"\n'
    '    titel: "Bundesnetzagentur"\n'
    '    url: "https://www.bundesnetzagentur.de/x"\n'
    'cover:\n'
    '  image: "images/covers/probe.jpg"\n'
    '  alt: "Ökostrom wechseln"\n'
    'faktencheck: 2026-10-28\n'
    '---\n\n'
    'Ein echter Artikeltext mit genug Substanz für die Prüfung.\n'
)
REL = "content/posts/2026-10-28-probe/index.md"


def _ohne(text, key):
    """Entfernt genau den Roh-Block eines Pflichtfeldes – wie ein Re-Writer."""
    block = wache._feld_block(pu.split_article(text)[1], key)
    assert block, key
    return text.replace("\n".join(block) + "\n", "", 1)


class PflichtlisteIstM4Tests(unittest.TestCase):
    """Die Pflichtliste ist keine zweite Wahrheit: M4 bleibt die Instanz."""

    def test_grundlage_da(self):
        self.assertTrue(wache.mw is not None and wache.pu is not None,
                        "SSOT-Import ausgefallen – die Wache wäre ungeprüft")

    def test_jedes_pflichtfeld_loest_m4_aus(self):
        for key in wache.PFLICHT_POSTS:
            with self.subTest(key=key):
                self.assertTrue(wache._m4_befunde(REL, _ohne(GUT, key)),
                                f"{key} fehlt, aber M4 schweigt – Liste driftet")

    def test_guter_text_hat_kein_m4(self):
        self.assertFalse(wache._m4_befunde(REL, GUT))


class VerlustUndHeilungTests(unittest.TestCase):
    def test_verlust_wird_erkannt_und_aus_head_geheilt(self):
        for key in wache.PFLICHT_POSTS:
            with self.subTest(key=key):
                beschaedigt = _ohne(GUT, key)
                funde = wache.verluste(REL, GUT, beschaedigt)
                self.assertIn(key, [f["feld"] for f in funde])
                neu, heals = wache.heile_datei(REL, GUT, beschaedigt)
                self.assertIn(key, [h["feld"] for h in heals])
                # M4 ist geheilt …
                self.assertFalse(wache._m4_befunde(REL, neu))
                # … der Body bytegleich …
                self.assertEqual(pu.split_article(neu)[2],
                                 pu.split_article(beschaedigt)[2])
                # … das Feld wortgleich aus HEAD (zitieren, nicht erfinden) …
                self.assertEqual(
                    wache._feld_block(pu.split_article(neu)[1], key),
                    wache._feld_block(pu.split_article(GUT)[1], key))
                # … und genau EIN Schlüssel (C32 bleibt gewahrt).
                self.assertEqual(
                    len(re.findall(rf"(?m)^{re.escape(key)}:",
                                   pu.split_article(neu)[1])), 1)

    def test_mehrere_verlorene_felder_in_einem_lauf(self):
        beschaedigt = _ohne(_ohne(GUT, "kurzantwort"), "quellen")
        neu, heals = wache.heile_datei(REL, GUT, beschaedigt)
        self.assertEqual({h["feld"] for h in heals}, {"kurzantwort", "quellen"})
        self.assertFalse(wache._m4_befunde(REL, neu))

    def test_idempotent(self):
        einmal, _ = wache.heile_datei(REL, GUT, _ohne(GUT, "kurzantwort"))
        zweimal, heals = wache.heile_datei(REL, GUT, einmal)
        self.assertEqual(einmal, zweimal)
        self.assertFalse(heals)

    def test_nichts_erfinden_wenn_head_auch_fehlt(self):
        ohne = _ohne(GUT, "kurzantwort")
        self.assertFalse(wache.verluste(REL, ohne, ohne))
        neu, heals = wache.heile_datei(REL, ohne, ohne)
        self.assertEqual(neu, ohne)
        self.assertFalse(heals)

    def test_neue_datei_ohne_head_wird_nicht_angefasst(self):
        ohne = _ohne(GUT, "kurzantwort")
        neu, heals = wache.heile_datei(REL, None, ohne)
        self.assertEqual(neu, ohne)
        self.assertFalse(heals)

    def test_entwurf_ist_kein_live_verlust(self):
        entwurf = _ohne(GUT, "kurzantwort").replace("draft: false", "draft: true")
        self.assertFalse(wache.verluste(REL, GUT, entwurf))

    def test_fremde_heilung_wird_nicht_zurueckgedreht(self):
        """Die Wache ist kein Reset: andere Felder bleiben wie geschrieben."""
        work = _ohne(GUT, "kurzantwort").replace(
            'title: "Ökostrom wechseln: sicher und grün"',
            'title: "Ökostrom wechseln: sicher, grün, bezahlbar"')
        neu, _ = wache.heile_datei(REL, GUT, work)
        self.assertIn('title: "Ökostrom wechseln: sicher, grün, bezahlbar"', neu)
        self.assertFalse(wache._m4_befunde(REL, neu))

    def test_wertaenderung_ist_kein_verlust(self):
        """Ein REDAKTIONELL geänderter Wert wird nicht auf HEAD zurückgesetzt."""
        geaendert = GUT.replace("Ein Wechsel ist jederzeit möglich;",
                                "Ein Wechsel ist fast immer möglich;")
        self.assertFalse(wache.verluste(REL, GUT, geaendert))
        neu, heals = wache.heile_datei(REL, GUT, geaendert)
        self.assertEqual(neu, geaendert)
        self.assertFalse(heals)

    def test_leeres_feld_gilt_als_verlust_und_wird_ersetzt_nicht_verdoppelt(self):
        geleert = _ohne(GUT, "kurzantwort").replace(
            "quellen:\n", 'kurzantwort: ""\nquellen:\n', 1)
        neu, heals = wache.heile_datei(REL, GUT, geleert)
        self.assertIn("kurzantwort", [h["feld"] for h in heals])
        self.assertFalse(wache._m4_befunde(REL, neu))
        self.assertEqual(
            len(re.findall(r"(?m)^kurzantwort:", pu.split_article(neu)[1])), 1)


class GitWirkungsprobeTests(unittest.TestCase):
    """Der Beweis am echten Git: HEAD ist die Quelle, nicht das Gedächtnis."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        self.pfad = Path(self.root) / REL
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        self.git("init", "-q")
        self.git("config", "user.email", "test@example.org")
        self.git("config", "user.name", "Test")
        self.pfad.write_text(GUT, encoding="utf-8")
        self.git("add", "-A")
        self.git("commit", "-qm", "Stand mit Kurzantwort")

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root,
                              capture_output=True, text=True, timeout=120)

    def test_automatik_verliert_feld_lauf_holt_es_zurueck(self):
        self.pfad.write_text(_ohne(GUT, "kurzantwort"), encoding="utf-8")
        bericht = wache.lauf(root=self.root, fix=True, pfade=[REL])
        self.assertTrue(bericht["grundlage"])
        self.assertIn("kurzantwort", [g["feld"] for g in bericht["geheilt"]])
        self.assertFalse(bericht["offen"])
        geheilt = self.pfad.read_text(encoding="utf-8")
        self.assertFalse(wache._m4_befunde(REL, geheilt))
        self.assertEqual(
            wache._feld_block(pu.split_article(geheilt)[1], "kurzantwort"),
            wache._feld_block(pu.split_article(GUT)[1], "kurzantwort"))

    def test_prueflauf_schreibt_nicht(self):
        beschaedigt = _ohne(GUT, "kurzantwort")
        self.pfad.write_text(beschaedigt, encoding="utf-8")
        bericht = wache.lauf(root=self.root, fix=False, pfade=[REL])
        self.assertIn("kurzantwort", [f["feld"] for f in bericht["verluste"]])
        self.assertFalse(bericht["geheilt"])
        self.assertEqual(self.pfad.read_text(encoding="utf-8"), beschaedigt)

    def test_zweiter_lauf_ist_gruen_und_schreibt_nichts(self):
        self.pfad.write_text(_ohne(GUT, "kurzantwort"), encoding="utf-8")
        wache.lauf(root=self.root, fix=True, pfade=[REL])
        stand = self.pfad.read_text(encoding="utf-8")
        bericht = wache.lauf(root=self.root, fix=True, pfade=[REL])
        self.assertFalse(bericht["verluste"])
        self.assertFalse(bericht["geheilt"])
        self.assertEqual(self.pfad.read_text(encoding="utf-8"), stand)


class FailClosedTests(unittest.TestCase):
    """Ein Messausfall ist kein Grün (C2/C33) – die zwei stillen Ausfälle."""

    def test_ohne_pyyaml_kein_gruen(self):
        echter = mw.yaml
        try:
            mw.yaml = None
            ok, grund = wache._grundlage(str(ROOT))
            self.assertFalse(ok)
            self.assertIn("PyYAML", grund)
            bericht = wache.lauf(root=str(ROOT), fix=False, pfade=[VORFALL])
            self.assertFalse(bericht["grundlage"])
            self.assertFalse(bericht["geheilt"])
        finally:
            mw.yaml = echter

    def test_ohne_git_head_kein_gruen(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok, grund = wache._grundlage(tmp)
            self.assertFalse(ok)
            self.assertIn("HEAD", grund)
            self.assertFalse(wache.lauf(root=tmp, fix=True)["grundlage"])

    def test_echte_grundlage_traegt(self):
        ok, grund = wache._grundlage(str(ROOT))
        self.assertTrue(ok, grund)

    def test_exit_2_bei_ausfall(self):
        """Die CLI trennt Werkzeugausfall (2) von Inhaltsbefund (1)."""
        with tempfile.TemporaryDirectory() as tmp:
            rc = wache.main(["--root", tmp, "--json"])
            self.assertEqual(rc, 2)


class Vorfall1110Tests(unittest.TestCase):
    """Der echte Vorfall, nachgespielt am echten Artikel (#1110)."""

    def setUp(self):
        self.pfad = ROOT / VORFALL
        if not self.pfad.exists():
            self.skipTest("Vorfall-Artikel nicht im Bestand")
        self.text = self.pfad.read_text(encoding="utf-8")

    def test_artikel_traegt_die_kurzantwort(self):
        """Der Live-Stand ist geheilt – M4 meldet keine fehlende Kurzantwort."""
        self.assertNotIn("Kurzantwort fehlt", wache._m4_befunde(VORFALL, self.text))

    def test_0b55fca_klasse_wird_erkannt_und_geheilt(self):
        """Lässt ein Schreiber die Kurzantwort fallen, holt die Wache sie zurück."""
        beschaedigt = _ohne(self.text, "kurzantwort")
        self.assertIn("Kurzantwort fehlt", wache._m4_befunde(VORFALL, beschaedigt))
        funde = wache.verluste(VORFALL, self.text, beschaedigt)
        self.assertIn("kurzantwort", [f["feld"] for f in funde])
        neu, heals = wache.heile_datei(VORFALL, self.text, beschaedigt)
        self.assertIn("kurzantwort", [h["feld"] for h in heals])
        self.assertNotIn("Kurzantwort fehlt", wache._m4_befunde(VORFALL, neu))
        self.assertEqual(pu.split_article(neu)[2], pu.split_article(beschaedigt)[2])
        self.assertEqual(
            wache._feld_block(pu.split_article(neu)[1], "kurzantwort"),
            wache._feld_block(pu.split_article(self.text)[1], "kurzantwort"))


class VerdrahtungTests(unittest.TestCase):
    """Die Wache steht im Weg – sonst ist sie Prosa (C49)."""

    @classmethod
    def setUpClass(cls):
        cls.deploy = (ROOT / ".github" / "workflows" / "deploy.yml").read_text(
            encoding="utf-8")

    def _schritt(self, name):
        m = re.search(r"(?m)^\s*-\s+name:\s*[\"']?" + re.escape(name), self.deploy)
        self.assertIsNotNone(m, f"Schritt fehlt: {name}")
        return m.start()

    def test_heilung_vor_diff_tor_und_bot_commit(self):
        fix = self.deploy.find("scripts/pflichtfeld_verlust_wache.py --fix")
        self.assertNotEqual(fix, -1, "deploy.yml ruft die Heilung nicht auf")
        self.assertLess(fix, self._schritt("Gate-Heilungsdiff merken"))
        self.assertLess(fix, self._schritt("Gate-Heilungen committen"))

    def test_heilung_nach_dem_letzten_inhaltsschreiber(self):
        fix = self.deploy.find("scripts/pflichtfeld_verlust_wache.py --fix")
        lcp = self.deploy.find("scripts/lcp_image_optimizer.py --fix")
        self.assertNotEqual(lcp, -1)
        self.assertGreater(fix, lcp, "Wache ist nicht der letzte Schreiber")

    def test_selbsttest_steht_im_deploy(self):
        self.assertIn("scripts/pflichtfeld_verlust_wache.py --selftest", self.deploy)

    def test_restbefund_geht_ans_siegel_nicht_in_die_auslieferung(self):
        """C34: der Restbefund wird gemeldet, blockiert aber nicht (#676/#740)."""
        self.assertIn('--melden "pflichtfeld-verlust-wache"', self.deploy)

    def test_blustradius_erklaert_beide_schritte(self):
        register = (ROOT / "data" / "blustradius-deploy.yml").read_text(
            encoding="utf-8")
        self.assertIn("Pflichtfeld-Verlust – Selbsttest (Wache muss lauffähig sein)",
                      register)
        self.assertIn("Pflichtfeld-Verlust-Wache – Quelle (aus HEAD, C34-toleriert)",
                      register)

    def test_wache_steht_im_vertraglichen_minimum(self):
        import governance_contract as gc
        self.assertIn("pflichtfeld_verlust_wache.py", gc.GUARDS)
        self.assertIn("C49", gc.LABEL)
        self.assertIn("C49", gc.RULE_TEXT)
        self.assertGreaterEqual(len(gc.RULE_TEXT["C49"]), 40)


if __name__ == "__main__":
    unittest.main()
