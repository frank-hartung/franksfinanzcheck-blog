"""Regressionstests zur Pflicht-Check-Frist-Wache (20.11.2026, C18-Nachtrag zu #316).

Der Befund: Der dokumentierte Dauerzustand (`PFLICHT_CHECK_DAUERZUSTAND`) trägt eine
Prüffrist (`pruefung_bis` 2026-12-31). Bis zum 01.01.2027 meldet der weiche Pfad der
PR-Wache "noch X Tage" im Log – aber niemand dutzte diesen Zähler, bevor er umschlug
(jede PR = Exit 1). Diese Tests nageln fest, dass die Wochen-Wache den Ablauf
rechtzeitig und mit der richtigen Handlung benennt, und dass sie dabei kein Urteil
des PR-Gates anfasst:

  1. FRIST_BEFUND   Restlaufzeit > 35 Tage → INFO · ≤ 35 Tage → AMBER (handlungs-
                    bedürftig, Menschen-Entscheidung) · abgelaufen → RED · ohne
                    Erklärung → INFO `dauerzustand_weg` · Frist unbrauchbar → RED.
  2. GOVERNANCE     Die Befundtabelle wird vom Gate als `pflichtcheck`-Schritt
                    gelesen: INFO →grün (Hinweis), AMBER → amber/actionable,
                    RED → red/actionable (beide: Issue), C3 (Gate-Kennung ist
                    verdrahtet) und die Reihenfolge im Workflow bleiben prüfbar.
  3. CLI            `--frist-report PFAD` schreibt die Datei, beendet sich mit 0
                    (kein Handlungsbedarf) bzw. 1 (AMBER/RED) – unter jeder Uhr
                    reproduzierbar (heutiges Datum wird injiziert, nie gelesen).

Ausführung wie Bestands-Tests:  python3 -m unittest scripts.tests.test_pflichtcheck_frist -v
"""
import datetime as dt
import contextlib
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import governance_contract as gc  # noqa: E402
import governance_gate as gate  # noqa: E402
import pflichtcheck_guard as pg  # noqa: E402

FRIST = dt.date(2026, 12, 31)  # die im Vertrag hinterlegte Prüffrist
TAG = lambda tage_vorher: FRIST - dt.timedelta(days=tage_vorher)  # noqa: E731


def _zustand(**anderungen):
    z = {"zweck": "Pflicht-Check wird von main nicht verlangt (C15)",
         "check": gc.PFLICHT_CHECK_NAME, "branch": "main",
         "urteil_erwartet": "UNGESCHUETZT",
         "festgestellt": "2026-09-19", "dokumentiert": "2026-09-20",
         "pruefung_bis": FRIST.isoformat(),
         "belege": {"kein-merge-blocker": "PR #327 bei FAILURE gemergt (4b91938)"},
         "runbook": "docs/PFLICHT-CHECK-RUNBOOK.md",
         "runbook_abschnitt": "Dauerzustand – dokumentiert statt Dauer-Alarm (20.09.2026, Option B)"}
    z.update(anderungen)
    return z


class FristBefund(unittest.TestCase):
    """Die reine Grenze – keine Uhr wird gelesen, jeder Fall ist übergeben."""

    def test_langfristige_frist_ist_info(self):
        b = pg.frist_befund(TAG(41), _zustand())
        self.assertEqual(("info", "dauerzustand_frist"), (b["level"], b["code"]))
        self.assertIn("41 Tage", b["message"])

    def test_letzter_info_tag_ist_36(self):
        b = pg.frist_befund(TAG(36), _zustand())
        self.assertEqual("info", b["level"])

    def test_exakt_35_tage_ist_amber(self):
        b = pg.frist_befund(TAG(pg.FRIST_WARN_TAGE), _zustand())
        self.assertEqual(("amber", "dauerzustand_frist"), (b["level"], b["code"]))
        self.assertIn(str(pg.FRIST_WARN_TAGE), b["message"])
        self.assertIn("Menschen", b["message"], "die Meldung muss benennen, WER entscheidet")

    def test_stichtag_ist_noch_amber(self):
        # „bis einschließlich 31.12.2026" – der Stichtag selbst zählt noch.
        b = pg.frist_befund(FRIST, _zustand())
        self.assertEqual("amber", b["level"])

    def test_tag_danach_ist_red(self):
        b = pg.frist_befund(FRIST + dt.timedelta(days=1), _zustand())
        self.assertEqual(("red", "dauerzustand_frist"), (b["level"], b["code"]))
        self.assertIn("abgelaufen", b["message"])

    def test_ohne_erklaerung_ist_info_dauerzustand_weg(self):
        # Hinweis: None ist bewusst NICHT dabei – das ist der Default und liest
        # bewusst den echten Vertrag. Leer heißt: kein Inhalt hinterlegt.
        for leer in ({}, [], "UNGESCHUETZT", 0):
            b = pg.frist_befund(TAG(41), zustand=leer)
            self.assertEqual(("info", "dauerzustand_weg"), (b["level"], b["code"]), leer)

    def test_unbrauchbare_frist_ist_red(self):
        # 20261231 ist bewusst NICHT dabei: ISO-8601 erlaubt das Basisformat
        # (date.fromisoformat liest es) – das ist ein gültiges Datum, kein Befund.
        for kaputt in ("31.12.2026", "", "2026-13-01", "morgen", None, ["2026-12-31"]):
            b = pg.frist_befund(TAG(41), _zustand(pruefung_bis=kaputt))
            self.assertEqual("red", b["level"], kaputt)
            self.assertEqual("dauerzustand_frist", b["code"], kaputt)

    def test_konstante_ist_die_gemeldete_grenze(self):
        # Runbook und Gate-Meldung nennen 35 – die Konstante muss das halten.
        self.assertEqual(35, pg.FRIST_WARN_TAGE)

    def test_echter_vertrag_ist_lesbar_und_behauptet(self):
        # Der echte Vertrag trägt eine gültige Frist – die Wache liest ihn nie falsch.
        b = pg.frist_befund(dt.date(2026, 11, 20), None)
        self.assertIn(b["level"], ("info", "amber"))
        self.assertEqual("dauerzustand_frist", b["code"])


class GovernanceVerdrahtung(unittest.TestCase):
    """Das Gate liest die Befundtabelle – und C3 bleibt erfüllt."""

    def _classify(self, befund, exit_code):
        heute = dt.date(2026, 11, 20)
        report = pg.frist_report(befund, heute)
        return gate.classify("pflichtcheck", report, "", exit_code, "pflichtcheck_guard")

    def test_info_ist_nicht_behandlungsbeduerftig(self):
        b = pg.frist_befund(TAG(41), _zustand())
        c = self._classify(b, 0)
        self.assertFalse(c["actionable"], c)
        self.assertEqual("green", c["level"])

    def test_amber_ist_actionable_und_loest_issue_aus(self):
        b = pg.frist_befund(TAG(20), _zustand())
        c = self._classify(b, 1)
        self.assertEqual("amber", c["level"])
        self.assertTrue(c["actionable"])
        self.assertEqual("dauerzustand_frist", c["code"])
        _verdict, aktion, _counts = gate.decide_policy({"pflichtcheck": c})
        self.assertEqual("report", aktion, "AMBER muss ins gebündelte Governance-Issue münden")

    def test_red_ist_actionable_und_laesst_den_lauf_rot(self):
        b = pg.frist_befund(FRIST + dt.timedelta(days=1), _zustand())
        c = self._classify(b, 1)
        self.assertEqual("red", c["level"])
        self.assertTrue(c["actionable"])
        verdict, aktion, _counts = gate.decide_policy({"pflichtcheck": c})
        self.assertEqual(("RED", "report"), (verdict, aktion))

    def test_amber_ist_im_gate_als_handlungsbeduerftig_registriert(self):
        self.assertIn("dauerzustand_frist", gate.ACTIONABLE_AMBER)
        self.assertIn("pflichtcheck", gate.STEPS)
        self.assertEqual("Pflicht-Check-Frist (Dauerzustand)", gate.STEPS["pflichtcheck"]["label"])

    def test_report_enthaelt_tabelle_und_keine_pipe_im_meldungstext(self):
        b = pg.frist_befund(TAG(10), _zustand())
        report = pg.frist_report(b, dt.date(2026, 11, 20))
        zeile = next(l for l in report.splitlines() if l.startswith("| AMBER "))
        zellen = zeile.split("|")
        self.assertEqual(5, len(zellen), f"Pipe außerhalb der Tabelle: {zeile}")
        self.assertIn("dauerzustand_frist", zeile)

    def test_c3_messkette_ist_erfuellt(self):
        # Jede Gate-Kennung braucht einen Emit im Workflow (C3).
        text = (ROOT / ".github" / "workflows" / "premium-governance.yml").read_text(encoding="utf-8")
        self.assertIn("--emit pflichtcheck", text)
        self.assertIn("--frist-report /tmp/pflichtcheck-frist-report.md", text)

    def test_workflow_reihenfolge_und_gate_wiring(self):
        text = (ROOT / ".github" / "workflows" / "premium-governance.yml").read_text(encoding="utf-8")
        frist_at = text.index("pflichtcheck_guard.py --frist-report")
        automation_at = text.index("pflichtcheck_guard.py --automation")
        decide_at = text.index("governance_gate.py --decide --fail-on red")
        emit_at = text.index("--emit pflichtcheck")
        self.assertLess(automation_at, frist_at, "Frist-Schritt gehört neben die Automations-Wache")
        self.assertLess(frist_at, decide_at, "--decide darf nie vor der Frist-Wache laufen")
        self.assertLess(frist_at, emit_at)
        self.assertIn('--exit "$rc"', text[frist_at:emit_at + 200])
        # Offline-Vertrag: kein Token, kein Netz – der Befund kommt aus dem Vertrag.
        schritt = text[text.rindex("- name:", 0, frist_at):text.index("\n      - name:", frist_at)]
        self.assertNotIn("GH_TOKEN", schritt)
        self.assertNotIn("secrets.", schritt)

    def test_gate_selbstheilung_steps_heuristik_bleibt_erfuellt(self):
        # C3 findet Kennungen mit genau dieser Regex im Gate-Quelltext.
        import re
        gate_text = (ROOT / "scripts" / "governance_gate.py").read_text(encoding="utf-8")
        schritte = re.findall(r'^\s{4}"([a-z_]+)":\s*\{', gate_text, re.M)
        self.assertIn("pflichtcheck", schritte)


class CliVerhalten(unittest.TestCase):
    """`--frist-report` schreibt die Datei und exitet ehrlich – ohne Netz."""

    def _lauf(self, heute, zustand):
        with tempfile.TemporaryDirectory() as td:
            pfad = os.path.join(td, "frist-report.md")
            with mock.patch.object(gc, "PFLICHT_CHECK_DAUERZUSTAND", zustand), \
                    contextlib.redirect_stdout(io.StringIO()):
                rc = pg.frist_probe(report=pfad, heute=heute)
            self.assertTrue(os.path.exists(pfad), "Befunddatei fehlt")
            return rc, Path(pfad).read_text(encoding="utf-8")

    def test_info_exit_0(self):
        rc, inhalt = self._lauf(TAG(41), _zustand())
        self.assertEqual(0, rc)
        self.assertIn("INFO", inhalt)

    def test_amber_exit_1(self):
        rc, inhalt = self._lauf(TAG(20), _zustand())
        self.assertEqual(1, rc)
        self.assertIn("AMBER", inhalt)

    def test_red_exit_1(self):
        rc, inhalt = self._lauf(FRIST + dt.timedelta(days=3), _zustand())
        self.assertEqual(1, rc)
        self.assertIn("RED", inhalt)

    def test_weg_exit_0(self):
        rc, inhalt = self._lauf(TAG(41), {})
        self.assertEqual(0, rc)
        self.assertIn("dauerzustand_weg", inhalt)

    def test_report_format_passt_zum_gate_parser(self):
        rc, inhalt = self._lauf(TAG(20), _zustand())
        gefunden = gate._findings_from_report(inhalt)
        self.assertEqual(1, len(gefunden), gefunden)
        self.assertEqual(("amber", "dauerzustand_frist"), (gefunden[0][0], gefunden[0][1]))

    def test_aufruf_ueber_cli(self):
        with tempfile.TemporaryDirectory() as td:
            pfad = os.path.join(td, "x.md")
            import subprocess
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pflichtcheck_guard.py"),
                                "--frist-report", pfad],
                               capture_output=True, text=True, cwd=ROOT, timeout=60,
                               env={"PATH": os.environ.get("PATH", "")})
            self.assertIn(r.returncode, (0, 1))
            self.assertTrue(Path(pfad).exists())
            self.assertIn("dauerzustand_", Path(pfad).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
