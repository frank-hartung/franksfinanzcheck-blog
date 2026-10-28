"""Hermetische Tests des CI-Einstiegs (scripts/seo_paritaet_ci.py).

Der Orchestrator ist die Stelle, an der aus vier Werkzeugen EIN Merge-Urteil
wird. Genau deshalb wird hier die POLICY geprüft, nicht die Fachlogik der
Werkzeuge (das tun deren eigene Suiten):

  · Was sperrt, was ist nur Hinweis – inklusive der Fälle, die NICHT sperren
    dürfen (P3, Cornerstone-Alter C4). Ein Gate, das zu viel sperrt, wird
    abgeschaltet; eines, das zu wenig sperrt, ist ein grüner Haken.
  · Der Exit-Vertrag 0/1/2. Er ist die einzige Sprache, die der Workflow
    versteht – 2 (Werkzeug defekt) darf niemals als 0 durchgehen.
  · Die Ehrlichkeit des Berichts: Zählung, Grenze der Aussage, kein
    stilles Grün bei fehlender Messung (Node fehlt → „nicht gemessen").
  · Ein Ende-zu-Ende-Lauf auf einem Mini-Repo: Befunde kommen an, Inhalte
    werden nicht angefasst, ein fehlender Build schlägt fail-closed fehl.

Kein Hugo, kein Netz, keine echten Inhalte.
"""
import contextlib
import io
import json
import os
import struct
import tempfile
import unittest
from unittest.mock import patch

import scripts.seo_paritaet_ci as ci

# 1200×630 – genau das Karten-Ideal. Als Kopfzeilen-PNG, weil die Prüfung die
# Maße aus dem Datei-Header liest und nicht raten darf.
PNG_IDEAL = (b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR"
             + struct.pack(">II", 1200, 630) + b"\x08\x02\x00\x00\x00")


def posten(werkzeug: str, regel: str, schwere: str) -> ci.Posten:
    return ci.Posten(werkzeug, regel, schwere, "content/posts/x/index.md", "Text", "Maßnahme")


def mini_repo(root: str, *, cover: bool = True, cornerstone: bool = True,
              hugo: bool = True) -> str:
    """Zwei Artikel: ein markierter Cornerstone und ein gewöhnlicher Post.

    Ohne `hugo.toml` fehlt der Social-Vorschau die baseURL – sie darf dann
    NICHT raten, sondern muss den Lauf mit Exit 2 beenden (fail-closed).
    """
    if hugo:
        with open(os.path.join(root, "hugo.toml"), "w", encoding="utf-8") as fh:
            fh.write('baseURL = "https://franksfinanzcheck.de/"\n')
    if cover:
        os.makedirs(os.path.join(root, "static", "images"), exist_ok=True)
        with open(os.path.join(root, "static", "images", "cover.png"), "wb") as fh:
            fh.write(PNG_IDEAL)
    bild = ('cover:\n  image: "images/cover.png"\n  alt: "Stromzähler"\n'
            if cover else "")
    for slug, titel, cs in (("cs", "Cornerstone", cornerstone), ("normal", "Normal", False)):
        ordner = os.path.join(root, "content", "posts", slug)
        os.makedirs(ordner, exist_ok=True)
        with open(os.path.join(ordner, "index.md"), "w", encoding="utf-8") as fh:
            fh.write('---\n'
                     f'title: "{titel}"\n'
                     'description: "Beschreibung zum Artikel."\n'
                     'date: 2026-10-01\n'
                     'lastmod: 2026-10-01\n'
                     'draft: false\n'
                     'pillar: "strom"\n'
                     f'{"cornerstone: true" if cs else ""}\n'
                     f'{bild}'
                     '---\n\nText.\n')
    return root


class PolicyTests(unittest.TestCase):
    """Was den Merge blockiert – und was ausdrücklich nicht."""

    def test_p1_sperrt_unabhaengig_vom_werkzeug(self):
        for werkzeug, regel in (("cornerstone", "C1"), ("fokus_keywords", "F3"),
                                ("social", "social-bild"), ("linkvorschlaege", "beliebig")):
            with self.subTest(werkzeug=werkzeug):
                self.assertTrue(ci.ist_sperre(posten(werkzeug, regel, "P1")))

    def test_fokus_p2_sperrt_und_die_jede_regel_f1_bis_f8(self):
        for nummer in range(1, 9):
            with self.subTest(regel=f"F{nummer}"):
                self.assertTrue(ci.ist_sperre(posten("fokus_keywords", f"F{nummer}", "P2")))

    def test_fokus_p3_sperrt_nicht(self):
        for regel in ("F7", "F9"):
            with self.subTest(regel=regel):
                self.assertFalse(ci.ist_sperre(posten("fokus_keywords", regel, "P3")))

    def test_cornerstone_markierungsbruch_sperrt(self):
        for regel in ("C1", "C2", "C3", "C5"):
            with self.subTest(regel=regel):
                self.assertTrue(ci.ist_sperre(posten("cornerstone", regel, "P2")))

    def test_cornerstone_alter_und_breite_sperren_nicht(self):
        # C4 zählt Tage: ein uhrzeitabhängiges Gate wird zur Zeitbombe
        # (Lehre vom 07.10.2026, scripts/selftest_clock.py).
        for regel in ("C4", "C6"):
            with self.subTest(regel=regel):
                self.assertFalse(ci.ist_sperre(posten("cornerstone", regel, "P2")))

    def test_social_p3_sperrt_nicht(self):
        self.assertFalse(ci.ist_sperre(posten("social", "social-beschreibung", "P2")))
        self.assertFalse(ci.ist_sperre(posten("social", "social-beschreibung", "P3")))

    def test_bewerte_teilt_und_streng_hebt_an(self):
        p3 = posten("social", "social-beschreibung", "P3")
        p1 = posten("social", "social-bild", "P1")
        sperren, hinweise = ci.bewerte([p3, p1])
        self.assertEqual([p.schwere for p in sperren], ["P1"])
        self.assertEqual([p.schwere for p in hinweise], ["P3"])
        sperren, hinweise = ci.bewerte([p3, p1], streng=True)
        self.assertEqual(len(sperren), 2)
        self.assertEqual(hinweise, [])

    def test_leere_lage_ist_gruen(self):
        self.assertEqual(ci.Befund().exit_code, 0)


class ExitVertragTests(unittest.TestCase):
    """0 = frei, 1 = Sperre, 2 = Werkzeug defekt. Nie 2 als 0."""

    def test_exit_codes(self):
        lage = ci.Befund()
        self.assertEqual(lage.exit_code, 0)
        lage.sperren = [posten("fokus_keywords", "F2", "P2")]
        self.assertEqual(lage.exit_code, 1)
        lage.fehler = ["Selbsttest social_limits: Exit 1"]
        self.assertEqual(lage.exit_code, 2)

    def test_nur_hinweise_ergeben_exit_0(self):
        lage = ci.Befund(warnungen=[posten("social", "social-titel", "P3")])
        self.assertEqual(lage.exit_code, 0)

    def test_ausfall_eines_werkzeugs_ist_nie_gruen(self):
        """Ein fehlgeschlagener Unterprozess landet in `fehler`, nicht in `ok`."""
        schritt = ci.fuehre_aus("Probe", ["/gibt/es/nicht"])
        self.assertFalse(schritt.ok)
        self.assertIn("nicht ausführbar", schritt.detail)

    def test_fehlender_node_ist_nicht_gemessen_und_nicht_gruen(self):
        with patch("shutil.which", return_value=None), \
                contextlib.redirect_stderr(io.StringIO()):
            schritte = ci.node_tests()
        self.assertEqual(len(schritte), 1)
        self.assertTrue(schritte[0].uebersprungen)
        self.assertFalse(schritte[0].ok)
        self.assertIn("nicht gemessen", schritte[0].detail)

    def test_uebersprungener_schritt_wirft_den_lauf_nicht_um(self):
        """„nicht gemessen" ist ehrlich, aber kein Werkzeugfehler (Exit 2)."""
        with patch.object(ci, "selbsttests", return_value=[]), \
                patch.object(ci, "unittests", return_value=[]), \
                patch.object(ci, "node_tests", return_value=[
                    ci.Schritt("DOM-Test", False, "Node fehlt", 0.0, uebersprungen=True)]):
            with tempfile.TemporaryDirectory() as tmp:
                mini_repo(tmp)
                lage = ci.lauf(tmp, mit_linkvorschlaegen=False)
        self.assertEqual(lage.fehler, [])
        self.assertNotEqual(lage.exit_code, 2)


class BerichtTests(unittest.TestCase):
    """Der Bericht muss zählen, begrenzen und die Grenze der Aussage nennen."""

    def test_summary_nennt_zaehlung_policy_und_ehrlichkeitsgrenze(self):
        lage = ci.Befund(sperren=[posten("fokus_keywords", "F2", "P2")],
                         warnungen=[posten("social", "social-titel", "P3")])
        md = ci.summary_md(lage, streng=False)
        self.assertIn("Sperren: 1", md)
        self.assertIn("Hinweise: 1", md)
        self.assertIn("P1 + Fokus P2 + Cornerstone C1/C2/C3/C5", md)
        self.assertIn("keine Aussage über Rankings", md)
        self.assertIn("Sperren (blockieren den Merge)", md)

    def test_summary_weist_strenge_policy_aus(self):
        self.assertIn("--streng", ci.summary_md(ci.Befund(), streng=True))

    def test_summary_kappt_die_liste_und_zaehlt_den_rest(self):
        lage = ci.Befund(warnungen=[posten("social", "social-titel", "P3")
                                    for _ in range(30)])
        md = ci.summary_md(lage, streng=False)
        self.assertEqual(md.count("social/social-titel"), 25)
        self.assertIn("und 5 weitere", md)

    def test_summary_maskiert_pipes_in_ortsangaben(self):
        """Ein `|` im Pfad darf die Markdown-Tabelle nicht zerlegen."""
        md = ci.summary_md(ci.Befund(schritte=[ci.Schritt("a|b", True, "d|e", 1.0)]),
                           streng=False)
        self.assertIn("a\\|b", md)
        self.assertIn("d\\|e", md)

    def test_json_ist_serialisierbar_und_traegt_die_policy(self):
        daten = ci.bericht_json(ci.Befund(sperren=[posten("cornerstone", "C3", "P2")]),
                                streng=False)
        self.assertEqual(json.loads(json.dumps(daten))["ergebnis"]["exit"], 1)
        self.assertFalse(daten["policy"]["streng"])
        self.assertIn("C4", daten["policy"]["bernstein"])
        self.assertEqual(daten["sperren"][0]["regel"], "C3")
        self.assertEqual(daten["version"], 1)

    def test_werkzeugfehler_stehen_im_bericht_nicht_als_null(self):
        lage = ci.Befund(fehler=["Befunde nicht erhebbar: baseURL fehlt"])
        md = ci.summary_md(lage, streng=False)
        self.assertIn("Werkzeugfehler", md)
        self.assertIn("baseURL", md)
        self.assertEqual(ci.bericht_json(lage, streng=False)["ergebnis"]["exit"], 2)


class EndeZuEndeTests(unittest.TestCase):
    """Ein Lauf auf einem Mini-Repo – inklusive dessen, was NICHT passieren darf."""

    def test_markierungsbruch_sperrt_fehlt_feld_ist_hinweis(self):
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp)
            lage = ci.lauf(tmp, ohne_tests=True, mit_linkvorschlaegen=False)
        sperren = {(p.werkzeug, p.regel) for p in lage.sperren}
        self.assertIn(("cornerstone", "C3"), sperren)
        self.assertIn(("cornerstone", "C5"), sperren)
        self.assertNotIn(("fokus_keywords", "F9"), sperren)
        self.assertTrue(any(p.regel == "F9" for p in lage.warnungen))
        self.assertEqual(lage.exit_code, 1)

    def test_streng_macht_die_hinweise_zur_sperre(self):
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp)
            lage = ci.lauf(tmp, ohne_tests=True, streng=True, mit_linkvorschlaegen=False)
        self.assertTrue(any(p.regel == "F9" for p in lage.sperren))
        self.assertEqual(lage.warnungen, [])

    def test_ohne_markierung_ist_das_repo_gruen(self):
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp, cornerstone=False)
            lage = ci.lauf(tmp, ohne_tests=True, mit_linkvorschlaegen=False)
        self.assertEqual(lage.sperren, [])
        self.assertEqual(lage.exit_code, 0)

    def test_kein_schreibzugriff_auf_inhalte(self):
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp)

            def stand() -> dict:
                return {os.path.join(dp, f): os.path.getmtime(os.path.join(dp, f))
                        for dp, _, fs in os.walk(os.path.join(tmp, "content")) for f in fs}

            vorher = stand()
            ci.lauf(tmp, ohne_tests=True, mit_linkvorschlaegen=False)
            self.assertEqual(vorher, stand())

    def test_fehlender_build_ist_fail_closed(self):
        """`--quelle build` ohne public/ darf nicht „0 Befunde" melden."""
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp)
            lage = ci.lauf(tmp, ohne_tests=True, mit_linkvorschlaegen=False,
                           quelle="build")
        self.assertEqual(lage.exit_code, 2)
        self.assertTrue(lage.fehler)
        self.assertIn("build", lage.fehler[0])

    def test_quelle_wird_durchgereicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp)
            _, kennzahlen = ci.sammle_posten(tmp, mit_linkvorschlaegen=False)
        self.assertEqual(kennzahlen["social"]["quelle"], "frontmatter")

    def test_kennzahlen_zaehlen_das_mini_repo(self):
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp)
            _, kennzahlen = ci.sammle_posten(tmp, mit_linkvorschlaegen=False)
        self.assertEqual(kennzahlen["cornerstone"]["seiten"], 2)
        self.assertEqual(kennzahlen["cornerstone"]["markiert"], 1)
        # Beide Artikel haben kein keywords_fokus → zwei Empfehlungen (F9).
        self.assertEqual(kennzahlen["fokus_keywords"]["ohne_feld"], 2)
        self.assertEqual(kennzahlen["social"]["seiten"], 2)

    def test_bildlose_seite_ist_p1_und_sperrt(self):
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp, cover=False)
            lage = ci.lauf(tmp, ohne_tests=True, mit_linkvorschlaegen=False)
        self.assertTrue(any(p.werkzeug == "social" and p.schwere == "P1"
                            for p in lage.sperren))


class CliTests(unittest.TestCase):
    """Der Einstiegspunkt selbst – der Selbsttest ist die Eintrittskarte."""

    def test_selftest_laeuft_ueber_die_cli(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ci.main(["--selftest"]), 0)

    def test_json_nach_stdout_bleibt_maschinenlesbar(self):
        """`--json -` schreibt NUR JSON auf stdout (Meldungen gehen nach stderr)."""
        with tempfile.TemporaryDirectory() as tmp:
            mini_repo(tmp, cornerstone=False)
            ausgabe = io.StringIO()
            with contextlib.redirect_stdout(ausgabe), \
                    contextlib.redirect_stderr(io.StringIO()):
                code = ci.main(["--root", tmp, "--ohne-tests", "--json", "-",
                                "--ohne-linkvorschlaege"])
        daten = json.loads(ausgabe.getvalue())
        self.assertEqual(code, daten["ergebnis"]["exit"])
        self.assertIn("policy", daten)


if __name__ == "__main__":
    unittest.main()
