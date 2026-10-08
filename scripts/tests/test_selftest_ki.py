"""Regressionstests – Dauerheilung Content-Engine v2 #138 (KI-Probe).

Run 37694986440 (07.10.2026, 22:15 UTC) starb in Phase 0.5 mit Exit 2:
`requeue_quality_holds.py --selftest` fragte mit echten Schlüsseln das
Live-Modell, und eine GUTE Modellantwort färbte den Selbsttest rot. Diese
Datei hält fest:

  · Nachstellung des Ernstfalls: Schlüssel gesetzt, der ECHTE Transport
    liefert eine gelungene Antwort → die Selbsttests bleiben grün und der
    echte Transport wird nie erreicht (requeue, poppy).
  · Die Probe selbst ist scharf (ihr Selbsttest) und entdeckt den Auslöser.
  · Die Engine benennt einen Frühabbruch ehrlich statt „ohne Exit-Code“.
  · Die PR-Pipeline fährt die Probe über alle Workflow-Selbsttests.

Läuft offline, ohne Netz und ohne Schlüssel.
"""
from __future__ import annotations

import io
import os
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import selftest_ki  # noqa: E402

# Die gelungene Fassung, die das Live-Modell im Ernstfall sinngemäß lieferte.
GELUNGEN = ("Die Kasse hebt den Beitrag an. Das kostet die Kunden jeden Monat "
            "mehr Geld. Die Beratung der Verbraucherzentrale rät dir: Lies den "
            "Vertrag noch einmal genau durch. So siehst du, was sich für dich "
            "ändert und was gleich bleibt.")


class ErnstfallNachstellung(unittest.TestCase):
    """Schlüssel vorhanden + Modell antwortet gut = Selbsttest bleibt grün."""

    def setUp(self):
        self._env = mock.patch.dict(os.environ, {"GEMINI_API_KEY": "echt-wirkend",
                                                 "GROQ_API_KEY": "echt-wirkend"})
        self._env.start()

    def tearDown(self):
        self._env.stop()

    def test_requeue_selbsttest_haengt_nicht_am_modell(self):
        import lesbarkeit_heiler as lh
        import requeue_quality_holds as rq

        echter_transport = mock.Mock(return_value=GELUNGEN)
        with mock.patch.object(lh, "_ki_chat", echter_transport), \
                mock.patch.object(lh, "KI_CALL", None):
            fehler = rq.run_selftest()
        self.assertEqual(fehler, [], "Selbsttest lässt sich vom Modell umstimmen (#138)")
        echter_transport.assert_not_called()

    def test_requeue_selbsttest_stellt_ki_call_wieder_her(self):
        import lesbarkeit_heiler as lh
        import requeue_quality_holds as rq

        vorher = object()
        with mock.patch.object(lh, "KI_CALL", vorher), \
                mock.patch.object(lh, "_ki_chat", mock.Mock(return_value=None)):
            rq.run_selftest()
            self.assertIs(lh.KI_CALL, vorher, "Attrappe bleibt nach dem Selbsttest hängen")

    def test_requeue_selbsttest_beweist_die_heilwirkung(self):
        """Sabotage: Heiler wird ignoriert → der Selbsttest MUSS rot werden."""
        import requeue_quality_holds as rq

        with mock.patch.object(rq, "lesbarkeit_reif",
                               lambda text, rel="x": (False, "sabotiert", text)):
            fehler = rq.run_selftest()
        self.assertTrue(any(f.startswith("L3") for f in fehler), fehler)

    def test_poppy_selbsttest_haengt_nicht_am_modell(self):
        import llm_client
        import poppy_lib

        antwort = ('{"insights": ["x"], "pillar": "versicherungen", "winkel": "w", '
                   '"schlagworte": [], "artikel_titel": "t"}')
        echter_transport = mock.Mock(return_value=antwort)
        with mock.patch.object(llm_client, "chat", echter_transport), \
                redirect_stdout(io.StringIO()):
            rc = poppy_lib.selbsttest()
        self.assertEqual(rc, 0, "Poppy-Selbsttest lässt sich vom Modell umstimmen")
        echter_transport.assert_not_called()

    def test_schaltwerk_selbsttest_bleibt_offline(self):
        import schaltwerk
        import schaltwerk_triggers as trg

        echte = dict(trg.PROVIDER)
        with selftest_ki.ki_sperre() as versuche, redirect_stdout(io.StringIO()):
            rc = schaltwerk.selftest()
        self.assertEqual(rc, 0)
        self.assertEqual(versuche, [], f"Schaltwerk-Selbsttest geht ins Netz: {versuche}")
        self.assertEqual(trg.PROVIDER, echte, "Netz-Trigger nach ST7 nicht wiederhergestellt")


class ProbeIstScharf(unittest.TestCase):
    def test_probe_selbsttest(self):
        with redirect_stdout(io.StringIO()) as aus:
            rc = selftest_ki._selftest()
        self.assertEqual(rc, 0, aus.getvalue())

    def test_alter_requeue_selbsttest_waere_gefangen_worden(self):
        """Die Probe erkennt genau die Bauart, die #138 ausgelöst hat."""
        import tempfile

        code = (
            "import sys, os\n"
            f"sys.path.insert(0, {str(SCRIPTS)!r})\n"
            "import lesbarkeit_heiler as lh\n"
            "if '--selftest' in sys.argv:\n"
            "    t = '---\\ntitle: T\\ndraft: true\\n---\\n\\nDie Beitragsanpassung der "
            "Versicherungsgesellschaft erhöht die monatliche Belastung der Kunden.\\n'\n"
            "    lh.heile_text('fixture', t, ki=True)   # ohne Attrappe – wie vor #138\n"
            "    sys.exit(0)\n")
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "alter_selbsttest.py"
            pfad.write_text(code, encoding="utf-8")
            erg = selftest_ki.trap(str(pfad), timeout=120)
        self.assertEqual(erg["befund"], "NETZ", erg["ausgabe"][-800:])
        self.assertTrue(any("llm_client.py" in v["ort"]
                            for v in erg["versuche"]), erg["versuche"])

    def test_entdeckung_kennt_phase_05(self):
        liste = {e["script"]: e for e in selftest_ki.entdecke()}
        for script in ("scripts/requeue_quality_holds.py", "scripts/cadence_guard.py",
                       "scripts/draft_link_healer.py"):
            self.assertIn(script, liste)
        self.assertTrue(liste["scripts/requeue_quality_holds.py"]["schluessel"])
        self.assertGreaterEqual(len(liste), 90, "Entdeckung verliert Workflow-Selbsttests")


class WorkflowVertrag(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        wf = ROOT / ".github" / "workflows"
        cls.engine = (wf / "content-engine-v2.yml").read_text(encoding="utf-8")
        cls.pr = (wf / "publication-reliability-tests.yml").read_text(encoding="utf-8")

    def test_pr_pipeline_faehrt_die_ki_probe(self):
        self.assertIn("python3 scripts/selftest_ki.py --selftest", self.pr)
        self.assertIn("python3 scripts/selftest_ki.py --trap-workflows", self.pr)

    def test_engine_benennt_fruehabbruch(self):
        self.assertIn("FRÜHABBRUCH", self.engine)
        self.assertIn("steps.final_release.outcome }}\" = 'skipped'", self.engine)
        for sid in ("lock", "preflight", "kadenz", "generate", "taxonomie",
                    "phase1_commit", "hugo", "shortcode"):
            self.assertIn(f"        id: {sid}\n", self.engine, f"Schritt-id {sid} fehlt")
            self.assertIn(f"steps.{sid}.outcome", self.engine, f"{sid} wird nicht ausgewertet")

    def test_fruehabbruch_vor_der_exit_code_auswertung(self):
        frueh = self.engine.find("FRÜHABBRUCH (#138)")
        rc = self.engine.find("case \"$RC\" in")
        self.assertGreater(frueh, 0)
        self.assertLess(frueh, rc, "Frühabbruch muss VOR der Exit-Code-Auswertung stehen")

    def test_phase_05_nennt_den_befehl(self):
        start = self.engine.find("id: kadenz")
        ende = self.engine.find("id: generate")
        block = self.engine[start:ende]
        self.assertIn("trap '", block)
        self.assertIn("$BASH_COMMAND", block)
        # Die Selbsttests bleiben wörtlich auffindbar (Entdeckung der Probe).
        self.assertIn("python3 scripts/requeue_quality_holds.py --selftest", block)


if __name__ == "__main__":
    unittest.main()
