"""Workflow-Verträge für den öffentlichen Nachweis (WF-7C1F #611).

Der Vorfall #611 war kein API-Key-Problem und kein transienter Fehler: Am
05./06.10.2026 lief „Publication Delivery (öffentlicher Nachweis)" zweimal rot,
weil die QUELLE den gemessenen Montag (05.10.) nur mit 1/2 LIVE trug. Der Beleg
sagte das selbst (`source: 1`, `delivered: 1`, `errors: []`) – die Auslieferung
war vollständig. Weil der rote Sammel-Schritt „Missing public delivery is a
failed run" die Ursache nicht benannte, legte das zentrale Fehler-Alerting das
generische Wartungs-Issue #611 mit API-Key-Runbook an, obwohl der Fachkanal
`engine-deficit` (WF-1F8C #602/#608) für genau diesen Zustand existiert.

Diese Tests frieren die neue Trennung ein:

* Der Beleg trägt eine Klasse (`publication_check.py --klasse`).
* Der Workflow antwortet der Klasse mit einem eigenen, ehrlichen roten Schritt
  (`quelle_unter`, `quelle_ueber`, `auslieferung`/`unbekannt`).
* Der Schritt `quelle_unter` belegt den Fachkanal VOR dem roten Exit und trägt
  im Namen die beiden Kennwörter, an denen das zentrale Fehler-Alerting die
  Fachkanal-Stummschaltung festmacht („TAGESDEFIZIT" + „engine-deficit").
* Ein unbekannter/fehlender Beleg ist fail-closed laut, nie still.
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "publication-delivery.yml"
ALERTING = REPO / ".github" / "workflows" / "alert-on-failure.yml"


def _yaml(path: Path):
    try:
        import yaml
    except ImportError:  # pragma: no cover - CI hat PyYAML; lokal sauber skippen
        raise unittest.SkipTest("PyYAML lokal nicht installiert")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def _steps() -> list[dict]:
    return ((_yaml(WORKFLOW).get("jobs") or {}).get("verify") or {}).get("steps") or []


def _step(name: str) -> dict:
    for step in _steps():
        if step.get("name") == name:
            return step
    raise AssertionError(f"Workflow-Schritt fehlt: {name}")


class AuslieferungsKlassenWorkflowTests(unittest.TestCase):
    def test_klassenschritt_liest_den_gueltigen_beleg(self):
        step = _step("Auslieferungsklasse des gültigen Belegs")
        self.assertEqual(step.get("id"), "klasse")
        run = step.get("run") or ""
        self.assertIn("publication_check.py --klasse", run)
        # Immer der gültige Beleg: die Datei trägt nach der Wiederherstellung
        # den zweiten Nachweis (der erste bleibt als Tagesartefakt erhalten).
        self.assertIn("tmp/publication-receipt.json", run)
        self.assertIn('echo "klasse=$KLASSE" >> "$GITHUB_OUTPUT"', run)
        self.assertIn("unbekannt", run,
                      "Ohne lesbaren Beleg muss die Klasse fail-closed laut sein")

    def test_klasse_kommt_vor_jedem_verdikt(self):
        namen = [s.get("name") for s in _steps()]
        self.assertLess(namen.index("Auslieferungsklasse des gültigen Belegs"),
                        namen.index("AUSLIEFERUNGS-DEFIZIT – öffentlicher Nachweis fehlt"))

    def test_fachkanal_schritt_traegt_die_alerting_zuordnung(self):
        """Der Schrittname ist der Zuordnungsvertrag des Fehler-Alertings."""
        step = _step("TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig "
                     "(Auslieferungs-SLO)")
        name = step["name"]
        self.assertIn("TAGESDEFIZIT", name)
        self.assertIn("engine-deficit", name)
        self.assertIn("quelle_unter", step.get("if") or "",
                      "Der Fachkanal gilt nur für das Bestandsdefizit")
        run = step.get("run") or ""
        # Frischebeweis VOR dem roten Exit: nur ein offener UND für diesen Lauf
        # frisch belegter Kanal schaltet das generische Issue stumm (#602).
        self.assertIn("engine_issue.py --deficit", run)
        self.assertLess(run.index("engine_issue.py --deficit"), run.index("exit 1"))
        self.assertIn("exit 1", run, "Ehrlich rot – kein grüner Fremdtag")

    def test_alerting_regel_passt_zum_schrittnamen(self):
        alerting = ALERTING.read_text(encoding="utf-8")
        self.assertIn('"Publication Delivery (öffentlicher Nachweis)"', alerting,
                      "Der Workflow muss in der Wacht-Liste des Alertings stehen")
        m = re.search(r"const routedToEngineDeficit[^;]*;", alerting, re.S)
        self.assertIsNotNone(m, "Die Fachkanal-Regel des Alertings fehlt")
        regel = m.group(0)
        self.assertIn("'TAGESDEFIZIT'", regel)
        self.assertIn("'engine-deficit'", regel)
        name = _step("TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig "
                     "(Auslieferungs-SLO)")["name"]
        self.assertIn("TAGESDEFIZIT", name)
        self.assertIn("engine-deficit", name)

    def test_uebrige_klassen_bleiben_laut_und_ehrlich(self):
        ueber = _step("KADENZ-ÜBERSCHUSS – Bestand über dem Tagesmaximum")
        self.assertIn("quelle_ueber", ueber.get("if") or "")
        self.assertIn("exit 1", ueber.get("run") or "")
        self.assertNotIn("engine-deficit", ueber["name"],
                         "Ein Überschuss ist kein Defizit-Kanal-Fall")
        ausl = _step("AUSLIEFERUNGS-DEFIZIT – öffentlicher Nachweis fehlt")
        bedingung = ausl.get("if") or ""
        self.assertIn("auslieferung", bedingung)
        self.assertIn("unbekannt", bedingung,
                      "Kein Beleg = fail-closed laut, niemals still")
        self.assertIn("exit 1", ausl.get("run") or "")
        for step in (ueber, ausl):
            self.assertNotIn("TAGESDEFIZIT", step["name"],
                             "Nur das Bestandsdefizit ruft den Defizit-Fachkanal")

    def test_sammel_boolean_ist_ersetzt(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("Missing public delivery is a failed run", text,
                         "Der Sammel-Schritt ohne Ursache ist der Befund #611")
        self.assertNotIn("test '${{ steps.recovered_receipt.outcome }}' = success", text)
        # Die Belegkette selbst bleibt: Erstnachweis, Artefakt, Wiederherstellung,
        # zweiter Nachweis, tagesgebundener Abschluss (#610).
        for name in ("Verify sitemap AND article HTML; retry CDN propagation",
                     "Run bounded recovery and wait for its deploy",
                     "Re-check public receipt after recovery",
                     "Close incident when the recovered receipt is public"):
            self.assertTrue(_step(name), f"Belegkette beschädigt: {name} fehlt")
        self.assertIn("tmp/publication-receipt*.json", text,
                      "Der tagesgenaue Beleg muss als Artefakt erhalten bleiben")


if __name__ == "__main__":
    unittest.main()
