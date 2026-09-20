"""Regression: CWV-Refresh in EINEM Lauf (Report ↔ Manifest, Governance-Regel C7).

Anlass (20.09.2026): `CWV-REPORT.md` ist gitignoreiert (`/*-REPORT.md` im Root),
`data/cwv_manifest.json` ist versioniert. Wer beides in getrennten Läufen
erzeugt, committet ein Manifest, dessen `Stand:` der (unsichtbare) Report nicht
bestätigt – C7 meldet dann „zwei Wahrheiten an einem Tag". Diese Tests frieren
den Vertrag ein:

  1. `--build` misst erst NACH einem erfolgreichen Bau (ein Lauf, ein Datum).
  2. Ein Bau-Fehler schreibt KEIN Artefakt (kein Scheingrün mit frischem Datum).
  3. C7 akzeptiert denselben Lauf und beanstandet einen gemischten Stand.
  4. Das Bau-Kommando entspricht dem Premium-Governance-Workflow.

Kein Netz, kein Hugo-Aufruf, kein Schreibzugriff auf den Bestand: REPORT,
MANIFEST und HISTORY werden auf ein Wegwerfverzeichnis umgebogen.
"""
import contextlib
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import cwv_guard as cwv
import governance_contract as gc


def report_text(verdict="GREEN", stand="2026-09-20"):
    return (f"# ⚡ Core-Web-Vitals-Wächter\n**Stand:** {stand} · **Messmethode:** x\n\n"
            f"## 🤖 Gesamt-Ampel: **{verdict}**\n")


class EinLaufEinStand(unittest.TestCase):
    """`--build` erzeugt Report und Manifest aus demselben Prozess."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.report = base / "CWV-REPORT.md"
        self.manifest = base / "data" / "cwv_manifest.json"
        self.history = base / "data" / "cwv_history.jsonl"
        self.public = base / "public"
        self.public.mkdir(parents=True)
        patches = [
            patch.object(cwv, "REPORT", str(self.report)),
            patch.object(cwv, "MANIFEST", str(self.manifest)),
            patch.object(cwv, "HISTORY", str(self.history)),
            patch.object(cwv, "PUBLIC_DEFAULT", str(self.public)),
            patch.object(cwv, "_scan_static", return_value=({"count_img": 12, "count_covers": 8,
                                                            "total_img_bytes": 1024,
                                                            "worst_cover_bytes": 512}, [])),
            patch.object(cwv, "_scan_public", return_value=(
                {"html_files": 40, "js_files": 1, "css_files": 0, "js_bytes": 10,
                 "css_bytes": 0, "html_bytes": 100, "inline_styles": 0, "blocking_js": 0,
                 "inline_js": 4, "structured_data_scripts": 2, "inline_scripts_plain": 0,
                 "img_nosize": 0}, [])),
        ]
        for p in patches:
            p.start()
            self.addCleanup(p.stop)

    def run_guard(self, *args, build=(True, "Total in 1 s")):
        with patch.object(cwv, "_run_build", return_value=build) as bau, \
                patch.object(sys, "argv", ["cwv_guard.py", *args]), \
                contextlib.redirect_stdout(io.StringIO()):
            rc = cwv.main()
        return rc, bau

    def test_build_laeuft_vor_der_messung_und_schreibt_beides(self):
        rc, bau = self.run_guard("--build", "--strict-build")
        self.assertEqual(0, rc)
        bau.assert_called_once()
        self.assertTrue(self.report.exists(), "Report fehlt")
        self.assertTrue(self.manifest.exists(), "Manifest fehlt")
        manifest = json.loads(self.manifest.read_text())
        stand = re.search(r"\*\*Stand:\*\*\s*(\d{4}-\d{2}-\d{2})", self.report.read_text())
        self.assertIsNotNone(stand, "Report ohne Stand-Zeile – C7 kann nicht prüfen")
        self.assertEqual(manifest["generated"], stand.group(1),
                         "Report und Manifest stammen nicht aus demselben Lauf")
        ampel = re.search(r"Gesamt-Ampel:\s*\*\*(\w+)\*\*", self.report.read_text())
        self.assertEqual(manifest["verdict"], ampel.group(1))
        self.assertTrue(manifest["build_measured"])
        self.assertTrue(manifest["strict_build"])

    def test_baufehler_schreibt_kein_artefakt(self):
        rc, _ = self.run_guard("--build", "--strict-build",
                               build=(False, "hugo: command not found"))
        self.assertEqual(2, rc, "Bau-Fehler muss hart abbrechen (kein Scheingrün)")
        self.assertFalse(self.report.exists(), "Report trotz Bau-Fehler geschrieben")
        self.assertFalse(self.manifest.exists(), "Manifest trotz Bau-Fehler geschrieben")
        self.assertFalse(self.history.exists(), "Verlauf trotz Bau-Fehler geschrieben")

    def test_bau_zielt_auf_das_gemessene_verzeichnis(self):
        _, bau = self.run_guard("--build", "--public", str(self.public))
        cmd = bau.call_args.args[0]
        self.assertEqual(("hugo", "--minify", "--destination"), cmd[:3])
        # Das Ziel steht relativ zum Repo (wie im Workflow) – entscheidend ist,
        # dass Bau und Messung DENSELBEN Baum meinen.
        gebaut = Path(os.path.join(cwv.BLOG_DIR, cmd[3])).resolve()
        self.assertEqual(self.public.resolve(), gebaut,
                         "Bau-Ziel und Mess-Ziel müssen identisch sein")

    def test_ohne_build_flag_wird_nicht_gebaut(self):
        _, bau = self.run_guard("--public", str(self.public), "--strict-build")
        bau.assert_not_called()

    def test_verlauf_traegt_denselben_stand(self):
        self.run_guard("--build", "--strict-build")
        rows = [json.loads(l) for l in self.history.read_text().splitlines() if l.strip()]
        self.assertEqual(1, len(rows))
        self.assertEqual(cwv.TODAY.isoformat(), rows[0]["generated"])


class BauFailClosed(unittest.TestCase):
    """`_run_build` selbst: fehlend, kaputt, Hänger – nie „ok"."""

    def test_fehlendes_kommando(self):
        ok, msg = cwv._run_build(("definitiv-kein-hugo-xyz",))
        self.assertFalse(ok)
        self.assertIn("nicht installiert", msg)

    def test_exit_ungleich_null(self):
        ok, _ = cwv._run_build(("false",))
        self.assertFalse(ok)

    def test_erfolg(self):
        ok, _ = cwv._run_build(("true",))
        self.assertTrue(ok)

    def test_haenger_laeuft_ins_limit(self):
        ok, msg = cwv._run_build(("sleep", "5"), timeout=1)
        self.assertFalse(ok)
        self.assertIn("länger als", msg)

    def test_kommando_identisch_zum_workflow(self):
        self.assertEqual(("hugo", "--minify", "--destination", "public"), cwv.HUGO_BUILD_CMD)
        workflow = (ROOT / ".github/workflows/premium-governance.yml").read_text()
        self.assertIn("hugo --minify", workflow,
                      "Workflow baut anders als `--build` – zwei Bau-Wahrheiten")


class C7Vertrag(unittest.TestCase):
    """C7 ist der Grund, warum beides in einem Lauf entstehen muss."""

    def test_gleicher_stand_ist_konsistent(self):
        stand = dt.date.today().isoformat()
        manifest = {"verdict": "GREEN", "generated": stand, "build_measured": True}
        self.assertEqual([], gc.c7_data_consistency(
            {"CWV-REPORT.md": report_text("GREEN", stand)}, manifest))

    def test_gemischter_stand_wird_beanstandet(self):
        manifest = {"verdict": "GREEN", "generated": "2026-09-15", "build_measured": True}
        funde = gc.c7_data_consistency(
            {"CWV-REPORT.md": report_text("GREEN", "2026-09-20")}, manifest)
        self.assertEqual(["C7"], [f[0] for f in funde])
        self.assertIn("nicht derselbe Lauf", funde[0][1])

    def test_zwei_ampeln_an_einem_tag(self):
        stand = dt.date.today().isoformat()
        manifest = {"verdict": "AMBER", "generated": stand, "build_measured": True}
        funde = gc.c7_data_consistency(
            {"CWV-REPORT.md": report_text("GREEN", stand)}, manifest)
        self.assertEqual(["C7"], [f[0] for f in funde])
        self.assertIn("zwei Wahrheiten", funde[0][1])


class Sichtbarkeit(unittest.TestCase):
    """Warum ein getrennter Lauf gefährlich ist: der Report ist unsichtbar."""

    def test_root_reports_sind_ignoriert_manifest_nicht(self):
        gitignore = (ROOT / ".gitignore").read_text()
        self.assertIn("/*-REPORT.md", gitignore,
                      "CWV-REPORT.md muss ignoriert sein – sonst wäre die "
                      "Lauf-Kopplung egal")
        self.assertTrue(re.search(r"^/\*-REPORT\.md$", gitignore, re.M))
        self.assertNotIn("cwv_manifest", gitignore,
                         "das Manifest muss versioniert bleiben (Scorecard/C7)")
        self.assertTrue((ROOT / "data" / "cwv_manifest.json").exists())


if __name__ == "__main__":
    unittest.main()
