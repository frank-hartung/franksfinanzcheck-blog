#!/usr/bin/env python3
"""End-to-End-Vertragstests für WF-0032 (#1026): Web-Vitals-Feldmessung (wöchentlich).

Sichert dauerhaft alle Schichten des Vorfalls #1026 ab:
  1. Paketfreie Isolationsprobe: `scripts/lighthouse_live.mjs --selftest` und
     `scripts/tests/lighthouse_live.test.mjs` werden in einem nackten Temp-Baum
     OHNE `node_modules` ausgeführt – selbst dann, wenn lokal `npm ci` lief.
  2. Workflow-Aufbau & Auto-Close-Vertrag: exakter Workflow- und Job-Name für
     `alert_issue_identity.py` (WF-0032) und `alert_resolve_gate.py` (#1026),
     Node-Setup vor Node-Selbsttest, Feldmessung isoliert vor dem Laborpfad,
     Labor-Selbsttest vor `npm ci` mit `test ! -d node_modules`, kein
     `continue-on-error` auf Messschritten.
  3. Echte `bash -eo pipefail`-Ausführung der extrahierten Workflow-Schritte
     (`feld`, `labor`, Urteils-Schritte) für Exit 0, Exit 1 (CrUX SCHLECHT),
     Exit 2 (`keine_crux_daten` vs. `abruf_fehlgeschlagen`) und leeren Exit.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import alert_issue_identity  # noqa: E402
import alert_resolve_gate  # noqa: E402

WORKFLOW_PFAD = ROOT / ".github" / "workflows" / "web-vitals-woche.yml"
ISSUE_1026_BODY = (
    "<!-- alert-workflow-id: WF-0032 -->\n"
    "<!-- alert-runbook: selbsttest -->\n"
    '<!-- alert-jobs: ["Felddaten (CrUX) + Labor (Lighthouse)"] -->\n'
)


def _lade_workflow() -> tuple[str, list[dict], str, str]:
    roh = WORKFLOW_PFAD.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-not-found]
    except ImportError:
        # Reiner Stdlib-Fallback, falls PyYAML nicht installiert ist.
        wf_name = ""
        job_name = ""
        steps: list[dict] = []
        aktuell: dict | None = None
        im_run = False
        run_zeilen: list[str] = []
        for zeile in roh.splitlines():
            if zeile.startswith("name: "):
                wf_name = zeile.split("name: ", 1)[1].strip()
            elif zeile.startswith("    name: ") and not job_name:
                job_name = zeile.split("name: ", 1)[1].strip()
            elif zeile.startswith("      - name: "):
                if aktuell is not None:
                    if im_run:
                        aktuell["run"] = textwrap.dedent("\n".join(run_zeilen))
                    steps.append(aktuell)
                aktuell = {"name": zeile.split("- name: ", 1)[1].strip()}
                im_run = False
                run_zeilen = []
            elif aktuell is not None:
                if im_run:
                    if not zeile.strip() or zeile.startswith("          "):
                        run_zeilen.append(zeile)
                        continue
                    aktuell["run"] = textwrap.dedent("\n".join(run_zeilen))
                    im_run = False
                    run_zeilen = []
                stripped = zeile.strip()
                if stripped.startswith("id: "):
                    aktuell["id"] = stripped.split("id: ", 1)[1].strip()
                elif stripped.startswith("continue-on-error: "):
                    aktuell["continue-on-error"] = stripped.split(": ", 1)[1].strip() == "true"
                elif stripped == "run: |":
                    im_run = True
                    run_zeilen = []
                elif stripped.startswith("run: "):
                    aktuell["run"] = stripped.split("run: ", 1)[1].strip()
        if aktuell is not None:
            if im_run:
                aktuell["run"] = textwrap.dedent("\n".join(run_zeilen))
            steps.append(aktuell)
        return roh, steps, wf_name, job_name

    daten = yaml.safe_load(roh)
    wf_name = str(daten["name"])
    job = daten["jobs"]["feld"]
    job_name = str(job["name"])
    return roh, list(job["steps"]), wf_name, job_name


class PaketfreieIsolationsTests(unittest.TestCase):
    def test_lighthouse_selftest_und_suite_laufen_ohne_node_modules(self):
        node = shutil.which("node")
        if node is None:
            self.skipTest("node nicht verfügbar")
        with tempfile.TemporaryDirectory() as tmp:
            basis = Path(tmp)
            for rel in (
                "scripts/lighthouse_live.mjs",
                "scripts/tests/lighthouse_live.test.mjs",
                "lighthouse/assertions.json",
                "data/cwv/feld_ziele.json",
            ):
                ziel = basis / rel
                ziel.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(ROOT / rel, ziel)
            self.assertFalse((basis / "node_modules").exists())
            env = {k: v for k, v in os.environ.items() if k != "NODE_PATH"}
            env["NODE_PATH"] = ""

            p_self = subprocess.run(
                [node, str(basis / "scripts/lighthouse_live.mjs"), "--selftest"],
                cwd=basis, env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(p_self.returncode, 0, p_self.stdout + p_self.stderr)
            self.assertIn("Selbsttest grün", p_self.stdout)

            p_test = subprocess.run(
                [node, "--test", str(basis / "scripts/tests/lighthouse_live.test.mjs")],
                cwd=basis, env=env, capture_output=True, text=True, timeout=30,
            )
            self.assertEqual(p_test.returncode, 0, p_test.stdout + p_test.stderr)


class WorkflowStrukturUndAutoCloseTests(unittest.TestCase):
    def test_identitaet_und_auto_close_vertrag_fuer_issue_1026(self):
        _, steps, wf_name, job_name = _lade_workflow()
        self.assertEqual(wf_name, "Web-Vitals-Feldmessung (wöchentlich)")
        ident = alert_issue_identity.identitaet(wf_name)
        self.assertEqual(ident["code"], "WF-0032")
        self.assertEqual(job_name, "Felddaten (CrUX) + Labor (Lighthouse)")

        ok = alert_resolve_gate.entscheiden(
            ISSUE_1026_BODY, [{"name": job_name, "conclusion": "success"}]
        )
        self.assertTrue(ok["schliessen"], ok)

        offen = alert_resolve_gate.entscheiden(
            ISSUE_1026_BODY, [{"name": job_name, "conclusion": "skipped"}]
        )
        self.assertFalse(offen["schliessen"], offen)
        self.assertTrue(steps)

    def test_schritt_reihenfolge_und_kein_continue_on_error(self):
        _, steps, _, _ = _lade_workflow()
        namen = [str(s.get("name") or "") for s in steps]

        def pos(teil: str) -> int:
            for idx, name in enumerate(namen):
                if teil in name:
                    return idx
            self.fail(f"Schritt mit '{teil}' fehlt in {namen}")

        idx_node = pos("Node einrichten")
        idx_manifest = pos("Manifest-Wache vor npm ci")
        idx_self_feld = pos("Selbsttest der Feldmessung")
        idx_feld = pos("Felddaten messen")
        idx_self_labor = pos("Selbsttest der Labormessung")
        idx_npm_ci = pos("Abhängigkeiten installieren")
        idx_labor = pos("Laborwerte messen")
        idx_urteil_labor = pos("Urteil Labor")
        idx_urteil_befund = pos("Urteil Felddaten – Befund")
        idx_urteil_stoerung = pos("Urteil Felddaten – Störung")

        self.assertLess(idx_node, idx_self_labor, "Node 22 muss vor dem Node-Selbsttest stehen")
        self.assertLess(idx_manifest, idx_npm_ci, "Manifest-Wache muss vor npm ci stehen")
        self.assertLess(idx_self_feld, idx_feld)
        self.assertLess(idx_feld, idx_self_labor,
                        "Verbindliche Feldmessung muss vor dem Laborpfad laufen")
        self.assertLess(idx_self_labor, idx_npm_ci,
                        "Labor-Selbsttest muss vor npm ci ohne node_modules laufen")
        self.assertLess(idx_npm_ci, idx_labor)
        self.assertLess(idx_labor, idx_urteil_labor)
        self.assertLess(idx_urteil_labor, idx_urteil_befund)
        self.assertLess(idx_urteil_befund, idx_urteil_stoerung)

        self_labor_run = str(steps[idx_self_labor].get("run") or "")
        self.assertIn("test ! -d node_modules", self_labor_run)
        self.assertIn("lighthouse_live.mjs --selftest", self_labor_run)

        for s in steps:
            self.assertFalse(
                bool(s.get("continue-on-error")),
                f"continue-on-error darf nicht gesetzt sein: {s.get('name')}",
            )


class WorkflowShellAusfuehrungsTests(unittest.TestCase):
    """Führt die echten `run:`-Blöcke unter `bash -eo pipefail` aus."""

    def _schritt_run(self, teil: str) -> str:
        _, steps, _, _ = _lade_workflow()
        for s in steps:
            if teil in str(s.get("name") or ""):
                return str(s["run"])
        raise AssertionError(f"Schritt {teil!r} fehlt")

    def test_feld_schritt_ueberlebt_exit_1_und_2_unter_bash_e(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash fehlt")
        feld_run = self._schritt_run("Felddaten messen")

        for erwarteter_rc, grund in ((0, ""), (1, ""), (2, "keine_crux_daten"), (2, "abruf_fehlgeschlagen")):
            with tempfile.TemporaryDirectory() as tmp:
                basis = Path(tmp)
                (basis / "scripts").mkdir(parents=True)
                (basis / "scripts" / "cwv_feld_wache.py").write_text(
                    textwrap.dedent(f"""\
                        import json, pathlib, sys
                        ziel = pathlib.Path("data/cwv/feld/befund.json")
                        ziel.parent.mkdir(parents=True, exist_ok=True)
                        ziel.write_text(json.dumps({{"stoerung_grund": {grund!r}}}), encoding="utf-8")
                        print("# Bericht rc={erwarteter_rc}")
                        print("Diagnose rc={erwarteter_rc}", file=sys.stderr)
                        sys.exit({erwarteter_rc})
                    """),
                    encoding="utf-8",
                )
                gh_out = basis / "gh_output.txt"
                gh_out.write_text("", encoding="utf-8")
                env = dict(os.environ, GITHUB_OUTPUT=str(gh_out), FELD_STRATEGIE="mobile")
                proc = subprocess.run(
                    [bash, "-eo", "pipefail", "-c", feld_run],
                    cwd=basis, env=env, capture_output=True, text=True, timeout=15,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                ausgabe = gh_out.read_text(encoding="utf-8")
                self.assertIn(f"exit={erwarteter_rc}\n", ausgabe)
                self.assertIn(f"grund={grund}\n", ausgabe)
                self.assertIn(f"# Bericht rc={erwarteter_rc}", proc.stdout)
                self.assertIn(f"Diagnose rc={erwarteter_rc}", proc.stderr)

    def test_labor_schritt_ueberlebt_exit_2_unter_bash_e(self):
        bash = shutil.which("bash")
        if bash is None or shutil.which("node") is None:
            self.skipTest("bash oder node fehlt")
        labor_run = self._schritt_run("Laborwerte messen")
        for erwarteter_rc in (0, 2):
            with tempfile.TemporaryDirectory() as tmp:
                basis = Path(tmp)
                (basis / "scripts").mkdir(parents=True)
                (basis / "scripts" / "lighthouse_live.mjs").write_text(
                    f"console.log('Labor rc={erwarteter_rc}'); process.exit({erwarteter_rc});\n",
                    encoding="utf-8",
                )
                gh_out = basis / "gh_output.txt"
                gh_out.write_text("", encoding="utf-8")
                proc = subprocess.run(
                    [bash, "-eo", "pipefail", "-c", labor_run],
                    cwd=basis,
                    env=dict(os.environ, GITHUB_OUTPUT=str(gh_out)),
                    capture_output=True, text=True, timeout=15,
                )
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                self.assertIn(f"exit={erwarteter_rc}\n", gh_out.read_text(encoding="utf-8"))
                self.assertIn(f"Labor rc={erwarteter_rc}", proc.stdout)

    def test_urteils_schritte_trennen_diagnose_befund_und_stoerung(self):
        bash = shutil.which("bash")
        if bash is None:
            self.skipTest("bash fehlt")
        urteil_labor = self._schritt_run("Urteil Labor")
        urteil_befund = self._schritt_run("Urteil Felddaten – Befund")
        urteil_stoerung = self._schritt_run("Urteil Felddaten – Störung")

        with tempfile.TemporaryDirectory() as tmp:
            # 1. Labor Exit 2 macht den Lauf NICHT rot, sendet nur ::warning::
            p_lab = subprocess.run(
                [bash, "-eo", "pipefail", "-c", urteil_labor],
                cwd=tmp,
                env=dict(os.environ, SCHRITT_LABOR_EXIT="2", SCHRITT_FELD_EXIT="0"),
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(p_lab.returncode, 0)
            self.assertIn("::warning::", p_lab.stdout)
            self.assertNotIn("::error::", p_lab.stdout)
            self.assertIn("Felddaten ohne Befund (Exit 0).", p_lab.stdout)

            # 2. Feld Befund (Exit 1) endet rot mit CrUX-Befund-Annotation
            p_bef = subprocess.run(
                [bash, "-eo", "pipefail", "-c", urteil_befund],
                cwd=tmp, env=dict(os.environ), capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(p_bef.returncode, 1)
            self.assertIn("::error::Felddaten schlecht (CrUX)", p_bef.stdout)

            # 3. Feld Störung unterscheidet keine_crux_daten vs. Abrufstörung vs. leer (fail-closed)
            p_crux = subprocess.run(
                [bash, "-eo", "pipefail", "-c", urteil_stoerung],
                cwd=tmp,
                env=dict(os.environ, SCHRITT_FELD_EXIT="2", SCHRITT_FELD_GRUND="keine_crux_daten"),
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(p_crux.returncode, 1)
            self.assertIn("keine_crux_daten", p_crux.stdout)

            p_api = subprocess.run(
                [bash, "-eo", "pipefail", "-c", urteil_stoerung],
                cwd=tmp,
                env=dict(os.environ, SCHRITT_FELD_EXIT="2", SCHRITT_FELD_GRUND="abruf_fehlgeschlagen"),
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(p_api.returncode, 1)
            self.assertIn("abruf_fehlgeschlagen", p_api.stdout)

            p_leer = subprocess.run(
                [bash, "-eo", "pipefail", "-c", urteil_stoerung],
                cwd=tmp,
                env=dict(os.environ, SCHRITT_FELD_EXIT="", SCHRITT_FELD_GRUND=""),
                capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(p_leer.returncode, 1)
            self.assertIn("kein Urteil abgegeben", p_leer.stdout)


if __name__ == "__main__":
    unittest.main()
