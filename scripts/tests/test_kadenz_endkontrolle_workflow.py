"""Workflow-Verträge für die Kadenz-Endkontrolle (WF-1F8C #602).

Der Vorfall #602 war kein neuer Fachbefund, sondern ein Melde-Routing-Fehler:
Die Kadenz-Endkontrolle blieb bei 1/2 LIVE korrekt rot und hatte das
Tagesdefizit bereits über `engine_issue.py --deficit` in den Fachkanal
`engine-deficit` gelegt. Das zentrale Fehler-Alerting legte zusätzlich ein
markenneutrales, aber generisches Wartungs-Issue mit API-Key-/Transient-Runbook
an. Diese Tests frieren die neue Trennung ein:

* Die Endabnahme schreibt eine maschinenlesbare Klasse (`ok`, `tagesdefizit`,
  `release-crash`, `cover-crash`, `unknown`) in `GITHUB_OUTPUT`.
* Der Reconcile-Schritt gleicht Fach-Issue und Source-Quote ab, wird aber
  selbst nicht mehr der rote Sammelschritt.
* Tagesdefizit, Release-Crash und Gate-Crash haben eigene rote Schritt-Namen,
  damit das Alerting nur die Fachkanal-Klasse dedupliziert und echte Build-/
  Gate-Crashs weiterhin laut bleiben.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
YAML_PATH = REPO / ".github" / "workflows" / "kadenz-endkontrolle.yml"


def _workflow() -> dict:
    try:
        import yaml
    except ImportError:  # pragma: no cover - CI hat PyYAML; lokal sauber skippen
        raise unittest.SkipTest("PyYAML lokal nicht installiert")
    data = yaml.safe_load(YAML_PATH.read_text(encoding="utf-8")) or {}
    return data


def _steps() -> list[dict]:
    data = _workflow()
    jobs = data.get("jobs") or {}
    job = jobs.get("endkontrolle") or {}
    return job.get("steps") or []


def _step(name: str) -> dict:
    for step in _steps():
        if step.get("name") == name:
            return step
    raise AssertionError(f"Workflow-Schritt fehlt: {name}")


class KadenzEndkontrolleWorkflowTests(unittest.TestCase):
    def test_release_schreibt_klassifizierten_exitcode(self):
        step = _step("Final gates and validated reserve (no AI dependency)")
        self.assertEqual(step.get("id"), "release")
        self.assertTrue(step.get("continue-on-error"),
                        "Release muss weiterlaufen lassen, damit Fachmeldung/Deploy noch passieren")
        run = step.get("run") or ""
        self.assertIn("set +e", run)
        self.assertIn("publication_release.py", run)
        self.assertIn('echo "rc=$rc" >> "$GITHUB_OUTPUT"', run)
        self.assertIn('echo "class=$klasse" >> "$GITHUB_OUTPUT"', run)
        for klasse in ("ok", "tagesdefizit", "release-crash", "unknown"):
            self.assertIn(klasse, run)
        self.assertIn("cover-crash", run)

    def test_reconcile_ist_nicht_mehr_der_rotsammelschritt(self):
        step = _step("Reconcile final source quota and deficit issue")
        self.assertEqual(step.get("id"), "quota")
        run = step.get("run") or ""
        self.assertIn("engine_issue.py --deficit", run)
        self.assertIn("publication_check.py", run)
        self.assertIn('echo "check_rc=$check_rc" >> "$GITHUB_OUTPUT"', run)
        self.assertIn("exit 0", run,
                      "Reconcile soll klassifizieren; rot werden dedizierte Folgeschritte")
        self.assertNotIn("test '${{ steps.release.outcome }}' = success", run)

    def test_dedizierte_rote_schritte_trennen_defizit_und_crash(self):
        release_crash = _step("RELEASE-CRASH – Endabnahme blockiert")
        gate_crash = _step("KADENZ-GATE-CRASH – Vorprüfung oder Endabnahme unklassifiziert")
        deficit = _step("TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig")

        self.assertIn("release-crash", release_crash.get("if") or "")
        self.assertIn("KADENZ-GATE-CRASH", gate_crash.get("run") or "")
        self.assertIn("steps.release.outcome != 'success'", gate_crash.get("if") or "")
        self.assertIn("tagesdefizit", deficit.get("if") or "")
        self.assertIn("engine-deficit", deficit.get("run") or "")
        self.assertIn("exit 1", release_crash.get("run") or "")
        self.assertIn("exit 1", gate_crash.get("run") or "")
        self.assertIn("exit 1", deficit.get("run") or "")

    def test_crash_klassen_koennen_nicht_vom_defizit_silencer_verschluckt_werden(self):
        """Nur der TAGESDEFIZIT-Schritt trägt `engine-deficit` im Namen.

        Das zentrale Alerting dedupliziert genau diese Schrittidentität. Würde
        ein Crash-Schritt denselben Fachkanal-Namen tragen, könnte #602 erneut
        als falsch negative Meldung wiederkommen.
        """
        for name in ("RELEASE-CRASH – Endabnahme blockiert",
                     "KADENZ-GATE-CRASH – Vorprüfung oder Endabnahme unklassifiziert"):
            self.assertNotIn("engine-deficit", name)
            self.assertNotIn("TAGESDEFIZIT", name)
        self.assertIn("engine-deficit",
                      "TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig")


if __name__ == "__main__":
    unittest.main()
