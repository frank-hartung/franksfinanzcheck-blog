#!/usr/bin/env python3
"""Vertragstest: „Auslieferung vor Siegel" in deploy.yml (Dauerheilung #676).

Befund 09./10.10.2026 (Ticket #676, „Bot-Watchdog: Automatisierung braucht
Eingriff"):

  * Der `deploy`-Job von deploy.yml scheiterte vom 09.10.2026 02:12 bis
    17:43 UTC 20× in Folge (plus ein verdrängter Lauf) – immer am Schritt „Release-Scorecard
    (Produktionswahrheit versiegeln, fail-closed)".
  * Die Scorecard steht VOR der Auslieferung. Ihr Fehlschlag ließ die
    Schritte 50–60 springen, darunter „Artefakt für offizielles
    Pages-Deployment hochladen"; der Job `pages-deployment` wurde gar nicht
    erst gestartet.
  * Öffentlich ging vom 08.10. 22:35 bis zum 09.10. 18:13 UTC nichts raus
    (19 h 38 min). Der um 14:02 UTC veröffentlichte Artikel
    `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust`
    lieferte 4 h 11 min HTTP 404 – genau der Befund, den der Bot-Watchdog
    meldete.

Die Scorecard ist ein BEWEISLAUF. Ihr Exit-Vertrag unterscheidet zwei
grundverschiedene Zustände: Exit 1 = heutige Kandidaten fachlich blockiert
(echter Inhaltsbefund, die Auslieferung MUSS stehen bleiben) und Exit 2 =
Werkzeugfehler (die Messung selbst ist kaputt). Nur Ersteres darf die
Veröffentlichung stoppen.

Diese Tests frieren die Reihenfolge ein, damit kein künftiger Mess-,
Report- oder Siegel-Schritt die öffentliche Auslieferung erneut als Geisel
nehmen kann:

  1. Der Scorecard-Schritt wertet den Exit-Code aus, statt ihn
     durchzureichen: Exit 1 bricht hart ab, ein Werkzeugfehler nicht.
  2. Nach dem Upload des Pages-Artefakts darf im `deploy`-Job NICHTS mehr
     folgen, was den Job rot machen kann – der Upload ist der letzte Schritt.
  3. Der deploy-Job gibt Auslieferungs-Beleg und Scorecard-Ergebnis als
     Job-Outputs heraus.
  4. Ein eigener Job `release-seal` läuft NACH der Veröffentlichung mit
     `if: always()` und macht den Lauf rot, wenn das Siegel fehlt oder die
     Auslieferung ausblieb. Fail-closed bleibt erhalten – nur die
     Reihenfolge stimmt: erst liefern, dann siegeln.
"""
from __future__ import annotations

import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEPLOY_YML = REPO / ".github" / "workflows" / "deploy.yml"

SCORECARD_ID = "scorecard"
ARTEFAKT_ID = "artefakt"
ARTEFAKT_SCHRITT = "Artefakt für offizielles Pages-Deployment hochladen"
SEAL_JOB = "release-seal"


def _workflow() -> dict:
    try:
        import yaml
    except ImportError:  # pragma: no cover - CI hat PyYAML; lokal sauber skippen
        raise unittest.SkipTest("PyYAML lokal nicht installiert")
    return yaml.safe_load(DEPLOY_YML.read_text(encoding="utf-8")) or {}


def _deploy_job() -> dict:
    return (_workflow().get("jobs") or {}).get("deploy") or {}


def _steps() -> list:
    return _deploy_job().get("steps") or []


def _step_by_id(step_id: str) -> dict:
    for step in _steps():
        if isinstance(step, dict) and step.get("id") == step_id:
            return step
    raise AssertionError(f"Schritt mit id '{step_id}' fehlt im deploy-Job")


def _step_index(step_id: str) -> int:
    for index, step in enumerate(_steps()):
        if isinstance(step, dict) and step.get("id") == step_id:
            return index
    raise AssertionError(f"Schritt mit id '{step_id}' fehlt im deploy-Job")


class ScorecardExitVertragTestCase(unittest.TestCase):
    """Der Scorecard-Schritt muss den Exit-Code auswerten, nicht durchreichen."""

    def setUp(self) -> None:
        self.step = _step_by_id(SCORECARD_ID)
        self.run = self.step.get("run") or ""

    def test_schritt_hat_stabile_id(self) -> None:
        self.assertEqual(self.step.get("id"), SCORECARD_ID)
        self.assertIn("release_scorecard.py", self.run)

    def test_exit_code_wird_ausgewertet(self) -> None:
        """Ohne Auswertung ist jeder Scorecard-Fehler ein Auslieferungs-Stopp."""
        self.assertIn('echo "exit_code=$code" >> "$GITHUB_OUTPUT"', self.run)
        self.assertIn('case "$code" in', self.run)

    def test_inhaltsbefund_blockiert_die_auslieferung_weiter(self) -> None:
        """Exit 1 (Kandidaten blockiert) muss den deploy-Job hart stoppen."""
        zweig = self._zweig("1)")
        self.assertIn("exit 1", zweig,
                      "Ein Inhaltsbefund der Scorecard darf nicht live gehen")
        self.assertIn('werkzeugfehler=false', zweig)

    def test_werkzeugfehler_blockiert_die_auslieferung_nicht(self) -> None:
        """Exit 2 (Werkzeugfehler) darf die Veröffentlichung nicht stoppen."""
        zweig = self._zweig("*)")
        self.assertNotIn("exit 1", zweig,
                         "Ein kaputtes Messwerkzeug nahm die Live-Site 19,6 h als "
                         "Geisel (#676) – das darf nicht zurückkommen")
        self.assertIn('werkzeugfehler=true', zweig)
        self.assertIn("::error::", zweig,
                      "Der Werkzeugfehler muss laut bleiben (kein stilles Grün)")

    def test_erfolgszweig_setzt_keinen_fehler(self) -> None:
        zweig = self._zweig("0)")
        self.assertIn('werkzeugfehler=false', zweig)
        self.assertNotIn("exit 1", zweig)

    def _zweig(self, marker: str) -> str:
        self.assertIn(marker, self.run, f"Exit-Zweig '{marker}' fehlt")
        start = self.run.index(marker)
        ende = self.run.index(";;", start)
        return self.run[start:ende]


class AuslieferungsReihenfolgeTestCase(unittest.TestCase):
    """Nach dem Artefakt-Upload darf nichts mehr die Veröffentlichung kippen."""

    def test_siegel_laeuft_vor_der_auslieferung(self) -> None:
        """Die Scorecard muss den Bestand VOR dem Upload messen können.

        Nur so kann ein echter Inhaltsbefund (Exit 1) die Veröffentlichung
        stoppen – das ist die gewollte Fail-closed-Richtung.
        """
        self.assertLess(_step_index(SCORECARD_ID), _step_index(ARTEFAKT_ID))

    def test_upload_schritt_existiert_weiter(self) -> None:
        namen = [str(s.get("name") or "") for s in _steps() if isinstance(s, dict)]
        self.assertIn(ARTEFAKT_SCHRITT, namen)

    def test_artefakt_beleg_kommt_nach_dem_upload(self) -> None:
        namen = [str(s.get("name") or "") for s in _steps() if isinstance(s, dict)]
        self.assertLess(namen.index(ARTEFAKT_SCHRITT), _step_index(ARTEFAKT_ID))

    def test_nach_dem_upload_darf_nichts_mehr_den_job_roeten(self) -> None:
        """Der Auslieferungs-Beleg ist der LETZTE Schritt des deploy-Jobs.

        Jeder spätere Schritt wäre ein neuer Kandidat für die #676-Klasse:
        rot nach der inhaltlichen Arbeit, aber vor/ohne die öffentliche
        Auslieferung. Meldeschritte gehören in `release-seal`.
        """
        self.assertEqual(_step_index(ARTEFAKT_ID), len(_steps()) - 1,
                         "Nach dem Auslieferungs-Beleg darf kein weiterer Schritt "
                         "folgen (Dauerheilung #676)")

    def test_deploy_job_veroeffentlicht_beweis_als_outputs(self) -> None:
        outputs = _deploy_job().get("outputs") or {}
        for schluessel in ("artefakt_ok", "scorecard_exit", "scorecard_werkzeugfehler"):
            self.assertIn(schluessel, outputs, f"Job-Output '{schluessel}' fehlt")
        self.assertIn("steps.artefakt.outputs.artefakt_ok", outputs["artefakt_ok"])
        self.assertIn("steps.scorecard.outputs.werkzeugfehler",
                      outputs["scorecard_werkzeugfehler"])


class ReleaseSealTestCase(unittest.TestCase):
    """Das Siegel wird NACH der Veröffentlichung gelegt – und bleibt laut."""

    def setUp(self) -> None:
        self.job = (_workflow().get("jobs") or {}).get(SEAL_JOB)
        if not self.job:
            raise AssertionError(f"Job '{SEAL_JOB}' fehlt in deploy.yml")

    def test_laeuft_auch_nach_roten_vorlaeufern(self) -> None:
        self.assertIn("always()", str(self.job.get("if") or ""),
                      "Ohne always() fällt das Siegel genau dann aus, wenn es "
                      "gebraucht wird")

    def test_haengt_an_auslieferung_und_gate(self) -> None:
        needs = self.job.get("needs") or []
        for erwartet in ("deploy-gate", "deploy", "pages-deployment"):
            self.assertIn(erwartet, needs)

    def test_nur_bei_verlangtem_deploy(self) -> None:
        self.assertIn("needs.deploy-gate.outputs.deploy == 'true'",
                      str(self.job.get("if") or ""),
                      "Ein übersprungener Deploy darf kein Siegel-Befund sein")

    def _run(self) -> str:
        schritte = self.job.get("steps") or []
        self.assertTrue(schritte, "release-seal hat keine Schritte")
        return schritte[0].get("run") or ""

    def test_ausgebliebene_auslieferung_wird_rot(self) -> None:
        run = self._run()
        self.assertIn('ARTEFAKT_OK" != "true"', run)
        self.assertIn("Auslieferung ausgeblieben", run)

    def test_abbruch_vor_auslieferung_wird_benannt(self) -> None:
        run = self._run()
        self.assertIn("VOR der Auslieferung abgebrochen", run)

    def test_werkzeugfehler_des_siegels_wird_rot(self) -> None:
        run = self._run()
        self.assertIn('SCORECARD_WERKZEUGFEHLER" = "true"', run)

    def test_verdraengter_lauf_ist_kein_befund(self) -> None:
        """`cancelled` ist gewolltes Verdrängen (#218), kein Ausfall."""
        run = self._run()
        self.assertIn('"cancelled"', run)
        self.assertIn("exit 0", run)

    def test_schlusszeile_unterscheidet_belegt_und_nicht_belegt(self) -> None:
        """„bereits raus" darf nur bei belegter Auslieferung stehen.

        Ein Siegel, das in jeder Lage dieselbe Beruhigung druckt, verschleiert
        genau den Zustand, den es melden soll.
        """
        run = self._run()
        self.assertIn("öffentlich raus", run)
        self.assertIn("NICHT belegt", run)

    def test_befund_beendet_den_schritt_mit_fehler(self) -> None:
        run = self._run()
        self.assertIn("exit 1", run,
                      "Ohne roten Exit meldet alert-on-failure den Befund nicht")
        self.assertIn("::error::", run)


class PagesDeploymentUnveraendertTestCase(unittest.TestCase):
    """Die #537-Reparatur darf durch die Umstellung nicht verloren gehen."""

    def test_pages_job_liefert_weiter_offiziell_aus(self) -> None:
        job = (_workflow().get("jobs") or {}).get("pages-deployment") or {}
        schritte = job.get("steps") or []
        uses = [str(s.get("uses") or "") for s in schritte if isinstance(s, dict)]
        self.assertTrue(any(u.startswith("actions/deploy-pages@") for u in uses),
                        "Das offizielle Pages-Deployment fehlt (Issue-#537-Klasse)")

    def test_siegel_blockiert_die_auslieferung_nicht(self) -> None:
        """`release-seal` darf kein `needs`-Vorlauf von `pages-deployment` sein."""
        job = (_workflow().get("jobs") or {}).get("pages-deployment") or {}
        needs = job.get("needs") or []
        self.assertNotIn(SEAL_JOB, needs,
                         "Das Siegel läuft NACH der Auslieferung – sonst blockiert "
                         "es sie wieder (#676)")


if __name__ == "__main__":
    unittest.main()
