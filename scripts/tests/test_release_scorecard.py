#!/usr/bin/env python3
"""Unit-Tests für die Release-Scorecard (Produktionswahrheit).

Verträge, die hier eingefroren werden:
  * SSOT-Form: acht Dimensionen, valide Checks, Publish-Gate-Deckung (C19)
  * Ausnahmen-Protokoll: Pflichtfelder, Ablauf, nicht ausnehmbar
  * Check-Matrix: gelaufen+sauber = bestanden, nicht gemessen = nie bestanden
  * Siegel-Bindung: Fingerprint ändert sich mit dem Inhalt, Drift wird erkannt
  * Terminrechnung: Intervall-SSOT faktenfrische, Review-Termin für „hoch“
  * Quellvertrag: die Scorecard misst über die Publish-Gate-Collectoren –
    fehlt ein Collector, ist die Sicht blind (Lektion: keine zweite Messregel).

Lauf: python3 -m unittest scripts.tests.test_release_scorecard
"""
import datetime as dt
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import release_scorecard as rs  # noqa: E402


class SSOTVertragTests(unittest.TestCase):
    """Die deklarative Wahrheit muss vollständig und deckungsgleich sein."""

    def setUp(self):
        self.ssot = rs.ssot_laden()
        self.register = rs.check_register(self.ssot)

    def test_acht_dimensionen_vorhanden(self):
        for dim in rs.DIMENSIONS_FOLGE:
            self.assertIn(dim, self.ssot["dimensionen"], f"Dimension {dim} fehlt")
            self.assertTrue(self.ssot["dimensionen"][dim].get("titel"))

    def test_check_ids_eindeutig_und_valide(self):
        gesehen = set()
        for check in self.ssot["checks"]:
            cid = check["id"]
            self.assertNotIn(cid, gesehen, f"Check-ID {cid} doppelt")
            gesehen.add(cid)
            self.assertIn(check["dimension"], rs.DIMENSIONS_FOLGE)
            self.assertIn(check["wirkung"], ("blockiert", "warnung"))
            self.assertIn(check["entscheidung"], ("auto", "human"))
            self.assertTrue(str(check.get("quelle") or "").strip())

    def test_publish_gate_deckung_c19(self):
        """Jede harte Publish-Gate-Familie ist blockierend deklariert."""
        for cid, quellemuster in rs.PUBLISH_GATE_HART_FAMILIEN.items():
            check = self.register.get(cid)
            self.assertIsNotNone(check, f"{cid} fehlt in der SSOT")
            self.assertEqual(check["wirkung"], "blockiert",
                             f"{cid} muss blockierend sein")
            self.assertIn(quellemuster, check["quelle"],
                          f"{cid}-quelle nennt {quellemuster} nicht")

    def test_warnungen_und_blocker_getrennt(self):
        """Frage 1 und 2 brauchen eine eindeutige, nicht-leere Antwort."""
        blocker = [c for c in self.ssot["checks"] if c["wirkung"] == "blockiert"]
        warnungen = [c for c in self.ssot["checks"] if c["wirkung"] == "warnung"]
        self.assertGreater(len(blocker), 10)
        self.assertGreaterEqual(len(warnungen), 1)

    def test_eskalation_und_falschpositive_dokumentiert(self):
        for block in ("eskalation", "falschpositive", "freigabeprozess", "siegel"):
            self.assertIn(block, self.ssot, f"SSOT-Block {block} fehlt")
        self.assertIn("fachlicher_konflikt", self.ssot["eskalation"])

    def test_nicht_ausnehmbare_checks_existieren(self):
        for cid in rs.NICHT_AUSNEHMBAR:
            self.assertIn(cid, self.register)


class EditorialMappingTests(unittest.TestCase):
    """E00–E19 vollständig gemappt – ein neuer Code ist ein Fehler, nie Still."""

    def test_alle_codes_gemappt(self):
        erwartet = {f"E{i:02d}" for i in range(20)}
        self.assertEqual(set(rs.ERG_CODE_ZU_CHECK), erwartet)

    def test_mapping_ziele_sind_deklarierte_checks(self):
        ssot = rs.ssot_laden()
        register = rs.check_register(ssot)
        for code, cid in rs.ERG_CODE_ZU_CHECK.items():
            self.assertIn(cid, register, f"{code} → {cid} ist nicht deklariert")

    def test_quellen_und_freigabe_und_Revision_getrennt(self):
        self.assertEqual(rs.ERG_CODE_ZU_CHECK["E12"], "Q1-belegkette")
        self.assertEqual(rs.ERG_CODE_ZU_CHECK["E17"], "M2-siegel-bindung")
        self.assertEqual(rs.ERG_CODE_ZU_CHECK["E10"], "N1-naechste-pruefung")
        self.assertEqual(rs.ERG_CODE_ZU_CHECK["E16"], "F2-stand-kennzeichnung")


class AusnahmenProtokollTests(unittest.TestCase):
    """Falsch-Alarme werden befristet, begründet und unterschrieben – nie
    durch Schwächung des Gates."""

    GUT = {"slug": "2026-01-01-beispiel", "check": "T1-zeichenlaenge",
           "begruendung": "Messartefakt aus dem Cover-Rendering",
           "gueltig_bis": "2030-01-01", "entschieden_von": "Frank Hartung"}

    def test_vollstaendig_ist_gueltig(self):
        self.assertEqual(rs.ausnahme_fehler(dict(self.GUT)), [])

    def test_plichtfelder_erzwungen(self):
        for feld in rs.AUSNAHME_PFLICHTFELDER:
            kaputt = dict(self.GUT)
            kaputt[feld] = ""
            self.assertTrue(rs.ausnahme_fehler(kaputt), f"{feld} fehlt")

    def test_kurze_begruendung_abgelehnt(self):
        kaputt = dict(self.GUT, begruendung="passt schon")
        self.assertTrue(rs.ausnahme_fehler(kaputt))

    def test_kein_iso_datum_abgelehnt(self):
        self.assertTrue(rs.ausnahme_fehler(dict(self.GUT, gueltig_bis="bald")))

    def test_siegel_und_render_nicht_ausnehmbar(self):
        for cid in ("M2-siegel-bindung", "T7-render-beweis"):
            self.assertTrue(rs.ausnahme_fehler(dict(self.GUT, check=cid)))

    def test_abgelaufene_wirkt_nicht(self):
        ssot = {"ausnahmen": [dict(self.GUT, gueltig_bis="2020-01-01")]}
        aktive, abgelaufene = rs.ausnahmen_aufbereiten(ssot, dt.date(2026, 10, 3))
        self.assertEqual(len(aktive), 0)
        self.assertEqual(len(abgelaufene), 1)

    def test_unzulaessige_ausnahme_stoppt_den_lauf(self):
        ssot = {"ausnahmen": [dict(self.GUT, check="M2-siegel-bindung")]}
        with self.assertRaises(rs.KonfigurationsFehler):
            rs.ausnahmen_aufbereiten(ssot, dt.date(2026, 10, 3))


class CheckMatrixTests(unittest.TestCase):
    """check_ergebnis: die vollständige Matrix ohne Scheingrün."""

    def setUp(self):
        self.ssot = rs.ssot_laden()
        self.register = rs.check_register(self.ssot)

    def _check(self, cid):
        return self.register[cid]

    def test_gelaufen_und_sauber_ist_bestanden(self):
        ergebnis = rs.check_ergebnis("s", self._check("T1-zeichenlaenge"),
                                     {}, {}, {}, "standard")
        self.assertEqual(ergebnis["status"], "bestanden")

    def test_fund_blockiert(self):
        befunde = {"T1-zeichenlaenge": ["zu-kurz"]}
        ergebnis = rs.check_ergebnis("s", self._check("T1-zeichenlaenge"),
                                     befunde, {}, {}, "standard")
        self.assertEqual(ergebnis["status"], "blockiert")

    def test_warnungs_fund_warnt_nur(self):
        befunde = {"T1w-zeichenlaenge-optimum": ["unter-optimum"]}
        ergebnis = rs.check_ergebnis("s", self._check("T1w-zeichenlaenge-optimum"),
                                     befunde, {}, {}, "standard")
        self.assertEqual(ergebnis["status"], "warnung")

    def test_ausnahme_stuft_auf_warnung_zurueck(self):
        befunde = {"T1-zeichenlaenge": ["zu-kurz"]}
        ausnahmen = {("s", "T1-zeichenlaenge"): dict(
            slug="s", check="T1-zeichenlaenge", begruendung="x" * 20,
            gueltig_bis="2030-01-01", entschieden_von="Frank Hartung")}
        ergebnis = rs.check_ergebnis("s", self._check("T1-zeichenlaenge"),
                                     befunde, {}, ausnahmen, "standard")
        self.assertEqual(ergebnis["status"], "warnung")
        self.assertTrue(ergebnis["ausnahme"])

    def test_werkzeugfehler_ist_nie_bestanden(self):
        tools = {"A1-link-integritaet": "kein public/"}
        ergebnis = rs.check_ergebnis("s", self._check("A1-link-integritaet"),
                                     {}, tools, {}, "standard")
        self.assertEqual(ergebnis["status"], "nicht beweisbar")

    def test_geltung_hoch_nur_fuer_hoch(self):
        ergebnis = rs.check_ergebnis("s", self._check("M1-fachliche-freigabe"),
                                     {}, {}, {}, "standard")
        self.assertEqual(ergebnis["status"], "nicht erforderlich")
        ergebnis = rs.check_ergebnis("s", self._check("M1-fachliche-freigabe"),
                                     {}, {}, {}, "hoch")
        self.assertEqual(ergebnis["status"], "bestanden")

    def test_geltung_standard_nur_fuer_nicht_hoch(self):
        ergebnis = rs.check_ergebnis("s", self._check("Q2-quellen-vorhanden"),
                                     {}, {}, {}, "hoch")
        self.assertEqual(ergebnis["status"], "nicht erforderlich")
        ergebnis = rs.check_ergebnis("s", self._check("Q2-quellen-vorhanden"),
                                     {}, {}, {}, "standard")
        self.assertEqual(ergebnis["status"], "bestanden")

    def test_dimension_ohne_messung_nicht_beweisbar(self):
        self.assertEqual(rs.dimension_status([]), "nicht beweisbar")

    def test_dimension_nur_nicht_erforderlich(self):
        self.assertEqual(rs.dimension_status(
            [{"status": "nicht erforderlich"}]), "nicht erforderlich")

    def test_dimension_worst_of(self):
        self.assertEqual(rs.dimension_status(
            [{"status": "bestanden"}, {"status": "warnung"}]), "warnung")
        self.assertEqual(rs.dimension_status(
            [{"status": "bestanden"}, {"status": "nicht beweisbar"}]),
            "nicht beweisbar")
        self.assertEqual(rs.dimension_status(
            [{"status": "warnung"}, {"status": "blockiert"}]), "blockiert")


class SiegelBindungTests(unittest.TestCase):
    """Frage 6: Das Siegel bindet die geprüfte Version nachweisbar."""

    def test_fingerprint_stabil_und_inhaltsgebunden(self):
        with tempfile.TemporaryDirectory() as tmp:
            datei = Path(tmp) / "index.md"
            datei.write_text("---\ntitle: A\n---\n\nText\n", encoding="utf-8")
            fp1 = rs.file_fingerprint(datei)
            self.assertEqual(fp1, rs.file_fingerprint(datei))
            datei.write_text("---\ntitle: A\n---\n\nAnderer Text\n", encoding="utf-8")
            self.assertNotEqual(fp1, rs.file_fingerprint(datei))

    def test_crlf_normalisiert(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.md"
            b = Path(tmp) / "b.md"
            a.write_text("---\ntitle: A\n---\n\nText\n", encoding="utf-8")
            b.write_bytes(a.read_text(encoding="utf-8").replace("\n", "\r\n")
                          .encode("utf-8"))
            self.assertEqual(rs.file_fingerprint(a), rs.file_fingerprint(b))

    def test_drift_erkennung(self):
        alt = {"artikel": {"x": {"sha256": "aaa"}, "y": {"sha256": "bbb"}}}
        self.assertEqual(rs.siegel_drift(alt, "x", "aaa"), "unverändert")
        self.assertEqual(rs.siegel_drift(alt, "x", "zzz"), "geändert – neu geprüft")
        self.assertEqual(rs.siegel_drift(alt, "neu", "zzz"), "neu versiegelt")


class TerminrechnungTests(unittest.TestCase):
    """nächste Überprüfung: eine Regel, keine zweite (SSOT faktenfrische)."""

    HEUTE = dt.date(2026, 10, 3)

    def test_standard_intervall_90_tage(self):
        fakten = {"faellig": {"intervall": 90},
                  "art": {"faktencheck": dt.date(2026, 9, 1)}}
        termin, ueberfaellig = rs.naechste_pruefung(
            "x", {"risk": "standard"}, fakten, self.HEUTE)
        self.assertEqual(termin, "2026-11-30")
        self.assertFalse(ueberfaellig)

    def test_ueberfaellig(self):
        fakten = {"faellig": {"intervall": 30},
                  "art": {"faktencheck": dt.date(2026, 6, 1)}}
        termin, ueberfaellig = rs.naechste_pruefung(
            "x", {"risk": "saisonal"}, fakten, self.HEUTE)
        self.assertTrue(ueberfaellig)

    def test_hoch_nimmt_review_termin(self):
        termin, ueberfaellig = rs.naechste_pruefung(
            "x", {"risk": "hoch", "_review": {"naechste_pruefung": "2026-11-15"}},
            None, self.HEUTE)
        self.assertEqual(termin, "2026-11-15")
        self.assertFalse(ueberfaellig)

    def test_hoch_ohne_termin_ist_ueberfaellig(self):
        termin, ueberfaellig = rs.naechste_pruefung(
            "x", {"risk": "hoch", "_review": {}}, None, self.HEUTE)
        self.assertEqual(termin, "unbekannt")
        self.assertTrue(ueberfaellig)

    def test_ohne_faktencheck_ist_ueberfaellig(self):
        termin, ueberfaellig = rs.naechste_pruefung(
            "x", {"risk": "standard"},
            {"faellig": {"intervall": 90}, "art": {"faktencheck": None}},
            self.HEUTE)
        self.assertTrue(ueberfaellig)


class ExitVertragTests(unittest.TestCase):
    """0 = freigabe-reif · 1 = blockierend im Scope · 2 = Werkzeugfehler."""

    def test_blockiert_im_scope(self):
        ergebnis = {"tool_fehler": {}, "artikel": {
            "a": {"urteil": "freigabe-reif"}, "b": {"urteil": "blockiert"}}}
        self.assertEqual(rs.exit_code(ergebnis, ["b"]), rs.EXIT_BLOCKIERT)

    def test_blockiert_ausserhalb_des_scopes(self):
        ergebnis = {"tool_fehler": {}, "artikel": {
            "a": {"urteil": "freigabe-reif"}, "b": {"urteil": "blockiert"}}}
        self.assertEqual(rs.exit_code(ergebnis, ["a"]), rs.EXIT_OK)

    def test_nicht_beweisbar_zaehlt_als_blockierend(self):
        ergebnis = {"tool_fehler": {}, "artikel": {
            "a": {"urteil": "nicht beweisbar"}}}
        self.assertEqual(rs.exit_code(ergebnis, ["a"]), rs.EXIT_BLOCKIERT)

    def test_werkzeugfehler_immer_fail_closed(self):
        ergebnis = {"tool_fehler": {"T2-seo-audit": "kein public/"},
                    "artikel": {"a": {"urteil": "freigabe-reif"}}}
        self.assertEqual(rs.exit_code(ergebnis, ["a"]), rs.EXIT_WERKZEUGFEHLER)


class QuellvertragTests(unittest.TestCase):
    """Die Scorecard misst über die Publish-Gate-Collectoren – das ist
    eingefroren (keine zweite Messregel, Scheingrün-Schutz 1)."""

    def test_collectoren_vorhanden(self):
        import publish_gate as pg
        for name in ("check_length_failures", "seo_audit_failures",
                     "faktenfrische_failures", "affiliate_profi_failures", "affiliate_integrity_failures",
                     "affiliate_intent_failures", "offenlegung_failures",
                     "editorial_review_failures", "title_integrity_failures",
                     "keyword_failures", "readability_failures",
                     "textverstaendnis_failures", "duplicate_failures",
                     "todays_live_candidates"):
            self.assertTrue(hasattr(pg, name), f"publish_gate.{name} fehlt")

    def test_beweislauf_schreibt_nicht(self):
        """C15: Der Scorecard-Lauf erzwingt DRY_RUN am Publish-Gate."""
        import inspect
        quelle = inspect.getsource(rs.sammle)
        self.assertIn("DRY_RUN = True", quelle,
                      "sammle() muss publish_gate.DRY_RUN=True setzen "
                      "(Intent-Wache heilt dann nicht)")

    def test_redundanz_hat_keine_zweite_scorecard_messung(self):
        """WF-54C4/#674: D1–D6 kommen aus dem Publish-Gate-Collector."""
        import inspect
        quelle = inspect.getsource(rs.sammle)
        self.assertIn("publish_gate.duplicate_failures", quelle)
        self.assertNotIn('_importiere_gate_module("duplikat_guard")', quelle)

    def test_selbsttest_gruen(self):
        self.assertEqual(rs.selftest(), [])


if __name__ == "__main__":
    unittest.main()
