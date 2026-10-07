"""Regressionstests für den Lesbarkeits-Heiler (WACHE-609).

Warum diese Tests existieren
----------------------------
Die Produktions-Wache meldete am 06.10.2026 für den letzten Publikationstag
„Content-Engine liefert nicht" (P2): 1/2 Artikel. Die Ursache stand im
selben Body: `data/reserve-readiness.json` meldete „Ziel 6, bereit 2" – und
sieben Kandidaten waren allein am harten Lesbarkeits-Gate (Flesch ≥ 60)
geparkt, während die Heiler-Deckung die Regel formal als „gedeckt" führte.
**Eine Deckung ohne Wirkung ist Papier.**

Diese Datei friert die Zusagen des Heilers ein:

1) **Wirkung** – die Wirkungsprobe bewegt ein Fixture nachweislich über die
   importierte Schwelle (`readability_check.NEW_FLESCH_MIN`), ohne Netz und
   ohne API-Kontingent. Dieselbe Probe verlangt der Governance-Vertrag C25.
2) **Fail-closed** – das Tor T1–T4 schreibt nichts, was die Schwelle nicht
   erreicht oder den Vertrag verletzt: entfernter Link, veränderte Zahl,
   anderes Frontmatter, neuer harter Textverständnis-Fund, zu starke Kürzung.
3) **Scope** – Entwürfe dürfen geheilt werden, Nicht-Entwürfe nie (der
   Live-Bestand gehört der Deploy-/Kadenz-Kette).
4) **Stufe B** – der KI-Pfad nimmt eine gute Fassung an (Attrappe) und
   verwirft eine schlechte, ohne eine Datei anzufassen.
5) **Verdrahtung** – Reserve-Kette und Deckung kennen den Heiler; die
   Zertifizierung bekommt damit eine echte Heilchance statt eines Namens.

Alle Tests laufen ohne Netz, ohne Hugo, ohne API-Keys und ohne Schreiben in
den Bestand (Fixtures liegen in temporären Verzeichnissen).
"""
import io
import contextlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import lesbarkeit_heiler as lh  # noqa: E402
import readability_check as rc  # noqa: E402


def _fixture(koerper: str, draft: bool = True, titel: str = "Probe") -> str:
    return (f"---\ntitle: \"{titel}\"\ndate: 2026-10-07\ndraft: "
            f"{'true' if draft else 'false'}\n---\n\n{koerper}\n")


SCHLECHT = _fixture(
    "Die Beitragsanpassung der Versicherungsgesellschaft erhöht die "
    "monatliche Belastung der Kunden. Die Verbraucherzentrale empfiehlt "
    "eine Überprüfung der Vertragsbedingungen, und die Tarifberatung "
    "dokumentiert die Vereinbarung der Zahlungsmodalitäten für die "
    "Folgejahre.")
GUT = _fixture(
    "Die Kasse hebt den Beitrag jedes Jahr an. Die Kunden merken das oft "
    "erst bei der Abrechnung. Wer die alten Briefe prüft, sieht den neuen "
    "Preis sofort. Die Beratung notiert, was sie mit dir ausgemacht hat, "
    "und was im nächsten Jahr gilt. So behältst du den Überblick und "
    "kannst rechtzeitig widersprechen, wenn dir etwas zu teuer wird.")


class WirkungsprobeTests(unittest.TestCase):
    """Die Wirkung ist die halbe Miete – ohne sie ist Deckung Papier (#609)."""

    def test_wirkungsprobe_bewegt_die_schwelle(self):
        ok, vor, nach, meldung = lh.wirkungsprobe()
        self.assertTrue(ok, meldung)
        self.assertLess(vor, lh.MINDEST_FLESCH)
        self.assertGreaterEqual(nach, lh.MINDEST_FLESCH)

    def test_schwelle_ist_importierte_ssot(self):
        """Keine zweite Zahl: die Schwelle kommt aus readability_check (#585)."""
        self.assertEqual(lh.MINDEST_FLESCH, rc.NEW_FLESCH_MIN)

    def test_cli_wirkungsprobe_als_maschinenvertrag(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "lesbarkeit_heiler.py"),
                            "--wirkungsprobe", "--json"],
                           cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        daten = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertTrue(daten["ok"])
        self.assertEqual(daten["schwelle"], lh.MINDEST_FLESCH)

    def test_selftest_des_heilers_gruen(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "lesbarkeit_heiler.py"),
                            "--selftest"], cwd=ROOT, capture_output=True,
                           text=True, timeout=180)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)


class TorTests(unittest.TestCase):
    """T1–T4: Was der Heiler nicht beweisen kann, schreibt er nicht."""

    def test_stufe_a_hebt_das_fixture_ueber_die_schwelle(self):
        neu, log = lh.stufe_a(lh.PROBE_FIXTURE)
        self.assertGreaterEqual(lh.flesch(neu, "p"), lh.MINDEST_FLESCH)
        self.assertEqual([], lh.verifiziere("p", lh.PROBE_FIXTURE, neu))
        self.assertGreater(log["saetze"], 0)

    def test_entfernter_link_wird_verworfen(self):
        mit_link = GUT.replace("Die Kunden merken das",
                               "Mehr im [Vergleich](/go/kasse/). Die Kunden merken das")
        ohne_link = mit_link.replace("[Vergleich](/go/kasse/)", "Vergleich")
        gruende = lh.verifiziere("p", mit_link, ohne_link)
        self.assertTrue(any("Linkziele" in g for g in gruende), gruende)
        self.assertTrue(any("/go/-Anker" in g for g in gruende), gruende)

    def test_veraenderte_zahl_wird_verworfen(self):
        mit_zahl = GUT.replace("Beitrag jedes Jahr", "Beitrag von 5 Euro")
        neu = mit_zahl.replace("5 Euro", "9 Euro")
        self.assertTrue(any("Zahlen" in g
                            for g in lh.verifiziere("p", mit_zahl, neu)))

    def test_frontmatter_ist_tabu(self):
        neu = GUT.replace('title: "Probe"', 'title: "Anders"')
        self.assertTrue(any("Frontmatter" in g
                            for g in lh.verifiziere("p", GUT, neu)))

    def test_neuer_harter_fund_wird_verworfen(self):
        neu = GUT + "\nIn diesem Beitrag erfährst du alles.\n"
        self.assertTrue(any(g.startswith("T2") for g in
                            lh.verifiziere("p", GUT, neu)))

    def test_zu_starke_kuerzung_wird_verworfen(self):
        gruende = lh.verifiziere("p", GUT, _fixture("Kurz."))
        self.assertTrue(any("90 %" in g or "Länge" in g for g in gruende),
                        gruende)

    def test_wirkungsloser_vorschlag_wird_verworfen(self):
        gruende = lh.verifiziere("p", GUT, GUT)
        self.assertTrue(any("keine Verbesserung" in g for g in gruende), gruende)

    def test_zweiter_lauf_ist_idempotent(self):
        einmal, _ = lh.stufe_a(lh.PROBE_FIXTURE)
        zweimal, _ = lh.stufe_a(einmal)
        self.assertEqual(einmal, zweimal)

    def test_abkuerzungen_ueberleben_den_schnitt(self):
        text = _fixture("Der Anbieter prüft z. B. die Frist, und er prüft "
                        "d. h. den Vertrag, und danach sendet er die "
                        "Bestätigung an dich.")
        neu, _ = lh.stufe_a(text)
        self.assertIn("z. B.", neu)
        self.assertIn("d. h.", neu)


class StufeBTests(unittest.TestCase):
    """Der KI-Pfad wird mit einer Attrappe bewiesen – kostenlos und scharf."""

    def setUp(self):
        self._alt = lh.KI_CALL

    def tearDown(self):
        lh.KI_CALL = self._alt

    def test_gute_ki_fassung_wird_angenommen(self):
        lh.KI_CALL = lambda _p: GUT.split("---", 2)[2].lstrip("\n")
        ergebnis = lh.heile_text("p", SCHLECHT, ki=True)
        self.assertTrue(ergebnis["ok"], ergebnis["gruende"])
        self.assertEqual(ergebnis["stufe"], "B")
        self.assertGreaterEqual(ergebnis["nach"], lh.MINDEST_FLESCH)

    def test_ki_fassung_mit_link_verlust_wird_verworfen(self):
        mit_link = SCHLECHT.replace("Die Verbraucherzentrale",
                                    "Mehr im [Vergleich](/go/kasse/). Die Verbraucherzentrale")
        lh.KI_CALL = lambda _p: GUT.split("---", 2)[2].lstrip("\n")
        ergebnis = lh.heile_text("p", mit_link, ki=True)
        self.assertFalse(ergebnis["ok"])
        self.assertEqual(ergebnis["neu_raw"], mit_link)
        self.assertTrue(any("verworfen" in g for g in ergebnis["gruende"]))

    def test_ki_fassung_unter_der_schwelle_wird_verworfen(self):
        lh.KI_CALL = lambda _p: SCHLECHT.split("---", 2)[2].lstrip("\n")
        ergebnis = lh.heile_text("p", SCHLECHT, ki=True)
        self.assertFalse(ergebnis["ok"])
        self.assertEqual(ergebnis["neu_raw"], SCHLECHT)

    def test_ohne_ki_wird_nie_geschrieben_wenn_die_schwelle_fehlt(self):
        ergebnis = lh.heile_text("p", SCHLECHT, ki=False)
        self.assertFalse(ergebnis["ok"])
        self.assertEqual(ergebnis["neu_raw"], SCHLECHT)
        self.assertIn("fail-closed", ergebnis["befund"])


class ScopeTests(unittest.TestCase):
    """Entwürfe ja, Live-Bestand nein – und kein Schreiben ohne --fix."""

    def _temp_datei(self, inhalt: str) -> str:
        tmp = tempfile.mkdtemp(prefix="lesbarkeit-heiler-test-")
        pfad = os.path.join(tmp, "index.md")
        Path(pfad).write_text(inhalt, encoding="utf-8")
        return pfad

    def test_klarer_text_bleibt_byte_identisch(self):
        pfad = self._temp_datei(GUT)
        vorher = Path(pfad).read_bytes()
        berichte, befund = lh._verarbeite([pfad], fix=True, ki=False, max_n=None)
        self.assertEqual(befund, 0)
        self.assertEqual(Path(pfad).read_bytes(), vorher)
        self.assertEqual(berichte[0]["stufe"], "bereits")

    def test_nicht_entwurf_wird_ohne_flagge_uebersprungen(self):
        pfad = self._temp_datei(SCHLECHT.replace("draft: true", "draft: false"))
        vorher = Path(pfad).read_bytes()
        berichte, befund = lh._verarbeite([pfad], fix=True, ki=False, max_n=None)
        self.assertEqual(befund, 0)
        self.assertEqual(berichte[0]["stufe"], "übersprungen")
        self.assertEqual(Path(pfad).read_bytes(), vorher)

    def test_unter_der_schwelle_wird_nichts_geschrieben(self):
        pfad = self._temp_datei(SCHLECHT)
        vorher = Path(pfad).read_bytes()
        _, befund = lh._verarbeite([pfad], fix=True, ki=False, max_n=None)
        self.assertEqual(befund, 1)
        self.assertEqual(Path(pfad).read_bytes(), vorher)

    def test_trockenlauf_schreibt_auch_bei_erfolg_nicht(self):
        pfad = self._temp_datei(lh.PROBE_FIXTURE)
        vorher = Path(pfad).read_bytes()
        berichte, _ = lh._verarbeite([pfad], fix=False, ki=False, max_n=None)
        self.assertEqual(Path(pfad).read_bytes(), vorher)
        self.assertFalse(berichte[0].get("geschrieben", False))


class KandidatenTests(unittest.TestCase):
    """Die Quellen: Holds, Reserve-Zertifikat, Artikel des Tages."""

    def test_hold_erkennung(self):
        self.assertTrue(lh.ist_lesbarkeits_hold(
            "publish-gate: Lesbarkeits-Gate nicht bestanden: Flesch 57.9"))
        self.assertTrue(lh.ist_lesbarkeits_hold(
            "publish-gate: Lesbarkeits-Score 70/100 (Mindestwert 75)"))
        self.assertFalse(lh.ist_lesbarkeits_hold(
            "publish-gate: Textverständnis-Gate nicht bestanden"))
        self.assertFalse(lh.ist_lesbarkeits_hold(None))

    def test_blockierte_kandidaten_sind_entwuerfe(self):
        for pfad in lh.hole_blocked():
            text = Path(pfad).read_text(encoding="utf-8")
            self.assertTrue(lh._ist_entwurf(text),
                            f"{pfad} ist kein Entwurf – Scope-Verletzung")

    def test_artikel_des_tages_tragen_heute_im_frontmatter(self):
        import datetime
        heute = datetime.date.today().isoformat()
        for pfad in lh.hole_neue():
            self.assertIn(heute, Path(pfad).read_text(encoding="utf-8")[:400])


class VerdrahtungTests(unittest.TestCase):
    """Deckung heißt Wirkung: Kette, Deckung und Vertrag kennen den Heiler."""

    def test_reserve_kette_faehrt_den_heiler(self):
        sys.path.insert(0, str(SCRIPTS))
        import reserve_finisher as rf
        namen = [e[0] for e in rf.HEALER_CHAIN]
        self.assertIn("lesbarkeit_heiler.py", namen)
        eintrag = [e for e in rf.HEALER_CHAIN if e[0] == "lesbarkeit_heiler.py"][0]
        self.assertIn("--fix", eintrag[1])
        self.assertEqual(eintrag[2], "file")

    def test_deckung_nennt_den_heiler_und_beweist_ihn(self):
        import reserve_healer_coverage as rhc
        b = rhc.volldeckung()
        gedeckt = {e["regel"]: e["heiler"] for e in b["gedeckt"]}
        self.assertIn("lesbarkeit_heiler.py",
                      gedeckt.get("readability_failures", []))
        self.assertEqual([], b["wirkung"]["luecken"])
        self.assertTrue(b["wirkung"]["nachgewiesen"])

    def test_governance_vertrag_prueft_die_wirkung(self):
        import governance_contract as gc
        self.assertIn("lesbarkeit_heiler.py", gc.GUARDS)
        texte = {name: (SCRIPTS / name).read_text(encoding="utf-8")
                 for name in ("reserve_healer_coverage.py",
                              "reserve_finisher.py", "lesbarkeit_heiler.py")}
        self.assertEqual([], gc.c25_deckung_wirkung(texte))

    def test_engine_workflow_heilt_die_artikel_des_tages(self):
        workflow = (ROOT / ".github" / "workflows" /
                    "content-engine-v2.yml").read_text(encoding="utf-8")
        self.assertIn("lesbarkeit_heiler.py --new-only --fix", workflow)


class ReportTests(unittest.TestCase):
    """Der Report ist die Menschen-Sicht auf dieselben Fakten."""

    def test_report_schreibt_und_nennt_die_schwelle(self):
        with tempfile.TemporaryDirectory() as tmp:
            pfad = os.path.join(tmp, "index.md")
            Path(pfad).write_text(SCHLECHT, encoding="utf-8")
            r = subprocess.run(
                [sys.executable, str(SCRIPTS / "lesbarkeit_heiler.py"),
                 "--file", pfad, "--keine-ki", "--json"],
                cwd=ROOT, capture_output=True, text=True, timeout=120)
            self.assertEqual(r.returncode, 1)
            daten = json.loads(r.stdout)
            self.assertEqual(daten["befund"], 1)
            bericht = daten["berichte"][0]
            self.assertEqual(bericht["vor"], bericht["nach"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
