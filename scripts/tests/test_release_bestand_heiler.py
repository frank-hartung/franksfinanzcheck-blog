#!/usr/bin/env python3
"""Regressionstests für die transaktionale Bestands-Selbstheilung (#1098)."""
from __future__ import annotations
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import release_bestand_heiler as h
import politur_heiler as ph
import publish_gate as pg
import repo_isolation as iso


def artikel(checks=("T6-textverstaendnis",), urteil="blockiert", extra=()):
    return {"pfad": "content/posts/a.md", "urteil": urteil,
            "befunde": [{"check": c, "wirkung": "blockiert"} for c in (*checks, *extra)]}


class AuswahlTest(unittest.TestCase):
    register = {c: {"entscheidung": "auto"} for c in h.UNTERSTUETZT}
    register.update({"F4-fachbefund": {"entscheidung": "human"}, "RD2-einzigartigkeit": {"entscheidung": "human"}})

    def messen(self, daten):
        return {"tool_fehler": {}, "artikel": {s: {"slug": s, **a} for s, a in daten.items()}}

    def test_nur_blockierte_unterstuetzte_checks(self):
        ergebnis = self.messen({"a": artikel(), "b": artikel(urteil="warnung"),
                "c": artikel(("T5-lesbarkeit",), urteil="warnung"), "d": artikel(("F4-fachbefund",))})
        register = self.register
        with mock.patch.object(h, "_modul", return_value=mock.Mock(automatic_write_protected=lambda p: None)):
            ziele, rest = h.auswahl(ergebnis, register, max_artikel=8)
        self.assertEqual([z["slug"] for z in ziele], ["a"])
        self.assertEqual(len(rest), 1)  # Warnungen sind keine Blocker und erzeugen keine Übergabe

    def test_gemischter_menschlicher_blocker_sperrt_ganzen_artikel(self):
        ergebnis = self.messen({"a": artikel(extra=("F4-fachbefund",))})
        register = self.register
        with mock.patch.object(h, "_modul", return_value=mock.Mock(automatic_write_protected=lambda p: None)):
            ziele, rest = h.auswahl(ergebnis, register, max_artikel=8)
        self.assertEqual(ziele, [])
        self.assertIn("menschlicher", rest[0]["grund"])

    def test_ymyl_wird_nicht_automatisch_geschrieben(self):
        ergebnis = self.messen({"a": artikel()}); register = self.register
        with mock.patch.object(h, "_modul", return_value=mock.Mock(automatic_write_protected=lambda p: "High-Risk")):
            ziele, rest = h.auswahl(ergebnis, register, max_artikel=8)
        self.assertEqual(ziele, [])
        self.assertIn("YMYL", rest[0]["grund"])

    def test_budget_ist_hart(self):
        daten = {str(i): artikel() for i in range(20)}
        e = self.messen(daten); register = self.register
        with mock.patch.object(h, "_modul", return_value=mock.Mock(automatic_write_protected=lambda p: None)):
            ziele, _ = h.auswahl(e, register, max_artikel=3)
        self.assertEqual(len(ziele), 3)
        with self.assertRaises(h.HeilFehler):
            h.auswahl(e, register, max_artikel=0)

    def test_werkzeugfehler_schliesst_auswahl_aus(self):
        e = self.messen({"a": artikel()}); e["tool_fehler"] = {"x": "kaputt"}
        register = self.register
        with self.assertRaises(h.HeilFehler): h.auswahl(e, register, max_artikel=8)


class VorschlagTest(unittest.TestCase):
    def test_echter_t6_fixture_wird_geheilt_und_formbewahrt(self):
        alt = ph.PROBE_FIXTURE.replace("draft: true", "draft: false")
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "probe"; d.mkdir(); (d / "index.md").write_text(alt)
            with mock.patch.object(pg, "POSTS_DIR", tmp):
                before, _ = pg.textverstaendnis_failures(["probe"])
        self.assertTrue(before)
        neu, checks = h.vorschlag("probe", alt, {"T6-textverstaendnis"})
        self.assertEqual(checks, ["politur_heiler"])
        self.assertNotEqual(neu, alt)
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "probe"; d.mkdir(); (d / "index.md").write_text(neu)
            with mock.patch.object(pg, "POSTS_DIR", tmp):
                after, _ = pg.textverstaendnis_failures(["probe"])
        self.assertEqual(after, {})
        self.assertEqual(ph.bewahre_form(alt, neu), [])

    def test_f4_ist_kein_auto_check(self):
        with self.assertRaises(h.HeilFehler):
            h.vorschlag("a", "x", {"F4-fachbefund"})

    def test_rd2_wird_nicht_automatisch_umgeschrieben(self):
        with self.assertRaises(h.HeilFehler):
            h.vorschlag("a", "x", {"RD2-einzigartigkeit"})


class BlockerTest(unittest.TestCase):
    def test_live_und_siegel_form_werden_gleich_gelesen(self):
        live = {"a": artikel(("T6-textverstaendnis",))}
        seal = {"a": {"urteil": "blockiert", "checks": [{"check": "T6-textverstaendnis", "wirkung": "blockiert"}]}}
        self.assertEqual(h.blocker(live), h.blocker(seal))

    def test_detailtext_aendert_identitaet_nicht(self):
        a = artikel(); b = artikel(); b["befunde"][0]["details"] = "andere Zahl"
        self.assertEqual(h.blocker({"a": a}), h.blocker({"a": b}))

    def test_ausnahme_und_warnung_sind_keine_blocker(self):
        a = artikel(); a["befunde"][0]["ausnahme"] = "bewusst"
        a["befunde"].append({"check": "T1", "wirkung": "warnung"})
        self.assertEqual(h.blocker({"a": a}), set())


class TransaktionTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.root = Path(self.tmp.name)
        self.p = self.root / "a.md"; self.p.write_bytes(b"original")
        self.patches = [mock.patch.object(h, "ROOT", self.root),
                        mock.patch.object(h, "STATE", self.root / "journal.json"),
                        mock.patch.object(h, "REPORT", self.root / "report.md")]
        for p in self.patches: p.start()
        self.z = {"version": 1, "basis_commit": "abc", "generated_at": h.jetzt(),
                  "baseline_hashes": {"a": h.sha(b"geheilt")}, "artikel": [
            {"pfad": "a.md", "slug": "a", "vorher_sha256": h.sha(b"original"),
             "nachher_sha256": h.sha(b"geheilt"), "checks": ["T6-textverstaendnis"]}],
            "baseline_blocker": [["a", "T6-textverstaendnis"]]}

    def tearDown(self):
        for p in reversed(self.patches): p.stop()
        self.tmp.cleanup()

    def test_atomic_replace_keine_temp_leiche(self):
        h.atomar_schreiben(self.p, b"neu")
        self.assertEqual(self.p.read_bytes(), b"neu")
        self.assertEqual(list(self.root.glob(".a.md.*")), [])

    def test_rollback_stellt_exakte_bytes_wieder_her(self):
        self.p.write_bytes(b"geheilt")
        proc = mock.Mock(returncode=0, stdout=b"original")
        with mock.patch.object(h.subprocess, "run", return_value=proc), iso.ledger_sandbox("test"):
            h.zurueckrollen(self.z, "Test")
        self.assertEqual(self.p.read_bytes(), b"original")
        self.assertEqual(h._journal()["status"], "zurueckgerollt")

    def test_fremde_aenderung_wird_niemals_ueberschrieben(self):
        self.p.write_bytes(b"redaktion")
        with mock.patch.object(h.subprocess, "run") as run, iso.ledger_sandbox("test"), \
             self.assertRaises(h.HeilFehler):
            h.zurueckrollen(self.z, "Test")
        run.assert_not_called(); self.assertEqual(self.p.read_bytes(), b"redaktion")

    def test_unbeweisbarer_git_blob_schreibt_nichts(self):
        self.p.write_bytes(b"geheilt")
        with mock.patch.object(h.subprocess, "run", return_value=mock.Mock(returncode=1, stdout=b"")), \
             self.assertRaises(h.HeilFehler):
            h.zurueckrollen(self.z, "Test")
        self.assertEqual(self.p.read_bytes(), b"geheilt")

    def _nachmessung(self, checks=(), tool_fehler=None, sha_wert=None):
        state = {"modus": "live", "commit": "abc", "generated_at": "9999-01-01T00:00:00Z", "tool_fehler": tool_fehler or {},
                 "artikel": {"a": {"urteil": "freigabe-reif" if not checks else "blockiert",
                                   "sha256": sha_wert or h.sha(b"geheilt"),
                                   "checks": [{"check": c, "wirkung": "blockiert"} for c in checks]}}}
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data/release_scorecard_state.json").write_text(json.dumps(state))
        h.zustand_schreiben({**self.z, "status": "geschrieben"})
        self.p.write_bytes(b"geheilt")

    def test_bestaetigung_ohne_neuen_blocker(self):
        self._nachmessung()
        with mock.patch.object(h.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=b"original")), iso.ledger_sandbox("test"):
            self.assertEqual(h.bestaetigen(), 0)
        self.assertEqual(h._journal()["status"], "bestaetigt")

    def test_neuer_blocker_rolls_back(self):
        self._nachmessung(("RD1-duplikate",))
        with mock.patch.object(h.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=b"original")), iso.ledger_sandbox("test"):
            self.assertEqual(h.bestaetigen(), 1)
        self.assertEqual(self.p.read_bytes(), b"original")

    def test_werkzeugfehler_rolls_back(self):
        self._nachmessung(tool_fehler={"sammlung": "kaputt"})
        with mock.patch.object(h.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=b"original")), iso.ledger_sandbox("test"):
            self.assertEqual(h.bestaetigen(), 1)
        self.assertEqual(self.p.read_bytes(), b"original")

    def test_falsche_bytes_im_siegel_rolls_back(self):
        self._nachmessung(sha_wert="fremd")
        with mock.patch.object(h.subprocess, "run", return_value=mock.Mock(returncode=0, stdout=b"original")), iso.ledger_sandbox("test"):
            self.assertEqual(h.bestaetigen(), 1)
        self.assertEqual(self.p.read_bytes(), b"original")


class WorkflowTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import yaml
        cls.wf = yaml.safe_load((ROOT / ".github/workflows/release-scorecard.yml").read_text())
        cls.steps = cls.wf["jobs"]["scorecard"]["steps"]

    def idx(self, step_id):
        return next(i for i, s in enumerate(self.steps) if s.get("id") == step_id)

    def test_heilung_nach_build_vor_messung(self):
        builds = [i for i, s in enumerate(self.steps) if s.get("uses") == "./.github/actions/hugo-build"]
        self.assertLess(builds[0], self.idx("heilung"))
        self.assertLess(self.idx("heilung"), builds[1])
        self.assertLess(builds[1], self.idx("scorecard"))
        self.assertLess(self.idx("scorecard"), self.idx("bestaetigung"))

    def test_content_commit_nur_nach_bestaetigung(self):
        commit = next(s["run"] for s in self.steps if s.get("name", "").startswith("Scorecard-Artefakte"))
        self.assertIn('if [ "${BESTAETIGT:-}" = "success" ] && [ "${HEILUNG:-}" = "success" ] && [ "${ROLLBACK:-}" != "failure" ]; then', commit)
        self.assertIn("git add -- content/posts", commit)
        self.assertEqual(next(s for s in self.steps if s.get("name", "").startswith("Scorecard-Artefakte"))["env"]["BESTAETIGT"],
                         "${{ steps.bestaetigung.outcome }}")

    def test_rollback_hat_eigenen_build_und_neue_messung(self):
        self.assertLess(self.idx("rollback"), self.idx("scorecard_rollback"))
        self.assertIn("rollback.outputs.zurueckgerollt", self.steps[self.idx("scorecard_rollback")]["if"])

    def test_scorecard_bleibt_getrennter_beweislauf(self):
        engine = (ROOT / "scripts/release_scorecard.py").read_text()
        self.assertNotIn("release_bestand_heiler", engine)
        self.assertIn("DRY_RUN = True", engine)

    def test_ticket_kopf_wird_aktualisiert(self):
        ticket = next(s["run"] for s in self.steps if s.get("name", "").startswith("Scorecard-Ticket"))
        self.assertIn('gh issue edit "$NUM" --body', ticket)

    def test_bestaetigte_heilung_wird_nicht_als_cleanup_diff_verworfen(self):
        step = self.steps[self.idx("rollback")]
        self.assertIn('--journal-status', step["run"])
        self.assertIn('[ "$STATUS" = "schreiben" ] || [ "$STATUS" = "geschrieben" ]', step["run"])
        self.assertIn('echo "zurueckgerollt=false"', step["run"])

    def test_ticket_bindet_siegel_an_lauf_und_vermeidet_kommentarlaerm(self):
        step = self.steps[self.idx("ticket")]
        self.assertIn('--erwarteter-commit "$BASIS_COMMIT"', step["run"])
        self.assertIn('--frisch-ab "$LAUFBEGINN"', step["run"])
        self.assertIn('grep -Fq "release-scorecard-ursache: $URSACHE"', step["run"])
        self.assertTrue(step.get("continue-on-error"))

    def test_pushverlust_ist_rot_nicht_warnung(self):
        step = self.steps[self.idx("commit")]
        self.assertIn('scripts/git_sync.sh --push-only', step["run"])
        self.assertNotIn('Push fehlgeschlagen', step["run"])
        self.assertTrue(step.get("continue-on-error"))
        final = self.steps[-1]
        self.assertIn('steps.commit.outcome ==', final["if"])
        self.assertIn('steps.ticket.outcome ==', final["if"])

    def test_nachmessung_ist_an_basis_commit_gebunden(self):
        runs = [s.get("run", "") for s in self.steps if s.get("id") in ("scorecard", "scorecard_rollback")]
        self.assertEqual(len(runs), 2)
        for run in runs:
            self.assertIn('--commit-sha "$(git rev-parse HEAD)"', run)


if __name__ == "__main__":
    unittest.main(verbosity=2)
