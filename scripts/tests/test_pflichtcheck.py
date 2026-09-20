"""Regressionstests zum Pflicht-Check-Vertrag (C18, 19.09.2026 – Nachtrag zu #316).

Der Befund: Das PR-Gate `integrity-lock.yml` meldete sich bei GitHub als Check
`lock` (Job-ID, kein Anzeigename) und wurde unter diesem Namen als Pflicht-Check
in ein Ruleset eingetragen, das keinen Ziel-Zweig hatte – die effektiven Regeln
für `main` waren leer. Ein Häkchen, das nichts schützte.

Diese Tests nageln fest, dass der Vertrag zwischen Workflow-Datei und
Branch-Schutz an DREI Stellen gehalten wird und keine davon still versagen kann:

  1. KONSTANTE = WORKFLOW   `governance_contract.PFLICHT_CHECK_NAME` ist der
     Anzeigename des Gate-Jobs im echten Workflow; jede Abweichung (Umbenennung,
     Anzeigename entfernt, Pfadfilter, `if:` am Job, `continue-on-error`,
     Schreibrechte, fehlende Live-Wache) ist ein C18-Befund.
  2. WORKFLOW = RULESET     `pflichtcheck_guard.py` beurteilt die Regeln des
     Ziel-Zweigs: verlangt (grün), alter Name / falsche Quelle / kein Schutz
     (rot mit Diagnose und Reparatur), unbrauchbare Antwort (kein Urteil).
  3. VERDRAHTUNG            die Wache läuft im Gate-Workflow selbst und im
     Qualitäts-Gate (GUARDS + Selbsttest-Runner) – bewiesen über den
     Mechanismus, nicht über eine Namens-Suche.

Ausführung wie Bestands-Tests:  python3 -m unittest discover -s scripts/tests -v
"""
import contextlib
import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import governance_contract as gc  # noqa: E402
import pflichtcheck_guard as pg  # noqa: E402
import selftest_runner as sr  # noqa: E402

WF_PFAD = ROOT / ".github" / "workflows" / gc.PFLICHT_CHECK_WORKFLOW
WF_KEY = f".github/workflows/{gc.PFLICHT_CHECK_WORKFLOW}"


def _c18(text):
    return [msg for _code, msg in gc.c18_pflicht_check({WF_KEY: text})]


class VertragAmEchtenWorkflow(unittest.TestCase):
    """Die Konstante und die Datei, die GitHub liest, sind EINE Wahrheit."""

    def setUp(self):
        self.text = WF_PFAD.read_text(encoding="utf-8")

    def test_echter_workflow_erfuellt_c18(self):
        self.assertEqual([], _c18(self.text))

    def test_anzeigename_ist_die_vertragskonstante(self):
        self.assertEqual(gc.PFLICHT_CHECK_NAME, gc.pflichtcheck_name_aus_workflow(self.text))
        self.assertEqual("Integritäts-Siegel", gc.PFLICHT_CHECK_NAME,
                         "Der Name ist der Vertrag mit dem Ruleset – Umbenennen nur nach Runbook.")

    def test_profil_liest_die_vertragsrelevanten_teile(self):
        p = gc.pflichtcheck_profil(self.text)
        self.assertTrue(p["pr_trigger"])
        self.assertIn(gc.PFLICHT_CHECK_BRANCH, p["pr_branches"])
        self.assertFalse(p["pr_pfadfilter"])
        self.assertEqual([], p["schreibrechte"])
        [job] = p["jobs"]
        self.assertEqual(("lock", gc.PFLICHT_CHECK_NAME, False), (job["id"], job["name"], job["if"]))
        schritte = "\n".join(b for _n, b in job["steps"])
        self.assertIn("integrity_guard.py --gate", schritte)
        self.assertIn("pflichtcheck_guard.py", schritte)

    def test_die_live_wache_ist_der_letzte_schritt_und_liest_nur(self):
        # Reihenfolge: erst das Siegel (fail-closed), dann der Wächter des Wächters.
        namen = [n for n, _b in gc.step_blocks(self.text)]
        self.assertTrue(namen[-1].startswith("Pflicht-Check-Vertrag prüfen"), namen)
        self.assertLess(namen.index("Integritäts-Siegel prüfen (HARD STOP – Sabotage-Schutz)"),
                        len(namen) - 1)
        # nur das Lese-Token des Laufs, keine Secrets
        self.assertIn("GH_TOKEN: ${{ github.token }}", self.text)
        self.assertNotIn("secrets.", self.text)

    def test_umbenennung_ohne_vertrag_wird_rot(self):
        # Genau der Ausgangsbefund: kein Anzeigename → Check heißt „lock“
        ohne = self.text.replace(f"    name: {gc.PFLICHT_CHECK_NAME}\n", "")
        self.assertEqual("lock", gc.pflichtcheck_name_aus_workflow(ohne))
        fund = _c18(ohne)
        self.assertEqual(1, len(fund), fund)
        self.assertIn("`lock`", fund[0])
        self.assertIn("Ruleset im selben Atemzug", fund[0])
        anders = self.text.replace(gc.PFLICHT_CHECK_NAME, "Siegel-Check")
        self.assertTrue(any("Siegel-Check" in f for f in _c18(anders)))

    def test_die_wache_liest_denselben_namen_wie_der_vertrag(self):
        # Die Live-Wache nimmt den Namen aus der Datei, die GitHub liest – und
        # der stimmt heute mit der Konstante überein (sonst warnt sie und C18 ist rot).
        name, job_id, warnung = pg.erwarteter_check()
        self.assertEqual((gc.PFLICHT_CHECK_NAME, "lock", ""), (name, job_id, warnung))

    def test_pfadfilter_if_und_verschlucken_werden_rot(self):
        mit_pfaden = self.text.replace("    branches: [main]\n",
                                       "    branches: [main]\n    paths-ignore:\n      - 'docs/**'\n")
        self.assertTrue(any("paths" in f for f in _c18(mit_pfaden)), _c18(mit_pfaden))
        mit_if = self.text.replace("    runs-on: ubuntu-latest\n",
                                   "    if: github.event.pull_request.draft == false\n"
                                   "    runs-on: ubuntu-latest\n")
        self.assertTrue(any("`if:`" in f for f in _c18(mit_if)), _c18(mit_if))
        verschluckt = self.text.replace(
            "      - name: Integritäts-Siegel prüfen (HARD STOP – Sabotage-Schutz)\n",
            "      - name: Integritäts-Siegel prüfen (HARD STOP – Sabotage-Schutz)\n"
            "        continue-on-error: true\n")
        self.assertTrue(any("continue-on-error" in f for f in _c18(verschluckt)), _c18(verschluckt))
        schreibend = self.text.replace("  contents: read\n", "  contents: write\n")
        self.assertTrue(any("Schreibrechte" in f for f in _c18(schreibend)), _c18(schreibend))
        ohne_wache = self.text.replace("run: python3 scripts/pflichtcheck_guard.py",
                                       "run: echo übersprungen")
        self.assertTrue(any("pflichtcheck_guard.py" in f for f in _c18(ohne_wache)), _c18(ohne_wache))
        anderer_zweig = self.text.replace("branches: [main]", "branches: [release]")
        self.assertTrue(any("`main`" in f for f in _c18(anderer_zweig)), _c18(anderer_zweig))

    def test_c18_laeuft_im_vertrag_und_der_vertrag_ist_erklaert(self):
        self.assertIn("C18", gc.LABEL)
        self.assertIn("C18", gc.RULE_TEXT)
        self.assertIn(gc.PFLICHT_CHECK_NAME, gc.RULE_TEXT["C18"])
        # run_all bindet C18 ein – der echte Baum muss den Vertrag erfüllen
        befunde = [b for b in gc.run_all(quick=True) if b[0] == "C18"]
        self.assertEqual([], befunde)


class UrteilDerLiveWache(unittest.TestCase):
    """`pflichtcheck_guard.beurteilen` – reine Logik, an den vier Fehlerbildern."""

    NAME = gc.PFLICHT_CHECK_NAME

    def regel(self, *checks, ruleset_id=23695872):
        return {"type": "required_status_checks", "ruleset_id": ruleset_id,
                "ruleset_source": "frank-hartung/franksfinanzcheck-blog",
                "parameters": {"strict_required_status_checks_policy": False,
                               "required_status_checks": [
                                   {"context": c, "integration_id": i} for c, i in checks]}}

    def test_verlangt(self):
        u = pg.beurteilen([self.regel((self.NAME, pg.GITHUB_ACTIONS_APP_ID))], self.NAME)
        self.assertEqual(pg.VERLANGT, u["urteil"])
        u = pg.beurteilen([self.regel((self.NAME, None))], self.NAME)
        self.assertEqual(pg.VERLANGT, u["urteil"], "ohne Quellbindung erfüllt jeder Melder den Check")

    def test_alter_name_im_ruleset_ist_fehlt_mit_job_id_hinweis(self):
        u = pg.beurteilen([self.regel(("lock", 15368))], self.NAME, job_id="lock")
        self.assertEqual(pg.FEHLT, u["urteil"])
        self.assertIn("`lock`", u["grund"])
        self.assertIn("Job-ID", u["grund"])

    def test_ruleset_ohne_zielzweig_ist_ungeschuetzt(self):
        # Genau der Befund vom 19.09.2026: /rules/branches/main → []
        u = pg.beurteilen([], self.NAME)
        self.assertEqual(pg.UNGESCHUETZT, u["urteil"])
        self.assertIn("Deko", u["grund"])
        u = pg.beurteilen([{"type": "deletion"}, {"type": "non_fast_forward"}], self.NAME)
        self.assertEqual(pg.UNGESCHUETZT, u["urteil"])

    def test_falsche_quelle(self):
        u = pg.beurteilen([self.regel((self.NAME, 99))], self.NAME)
        self.assertEqual(pg.FALSCHE_QUELLE, u["urteil"])

    def test_unbrauchbare_antwort_ist_kein_urteil(self):
        for kaputt in ({"message": "Not Found"}, "[]", [{"type": "required_status_checks"}]):
            self.assertEqual(pg.NICHT_PRUEFBAR, pg.beurteilen(kaputt, self.NAME)["urteil"], kaputt)

    def test_diagnose_und_reparatur_nennen_ziel_und_tausch(self):
        diag = pg.ruleset_diagnose([{"id": 23695872, "name": "Integritäts-Lock (PR-Gate)",
                                     "enforcement": "active",
                                     "conditions": {"ref_name": {"include": [], "exclude": []}},
                                     "rules": [self.regel(("lock", 15368))]}])
        self.assertEqual(1, len(diag))
        self.assertIn("KEINEN Zweig", diag[0])
        self.assertIn("`lock`", diag[0])
        rep = "\n".join(pg.reparatur(self.NAME, [{"context": "lock", "integration_id": 15368,
                                                  "ruleset_id": 1, "ruleset_source": "x"}],
                                     "Integritäts-Lock (PR-Gate)"))
        self.assertIn("`lock` entfernen", rep)
        self.assertIn(f"`{self.NAME}` hinzufügen", rep)
        self.assertIn("Include default branch", rep)
        self.assertIn(pg.RUNBOOK, rep)
        self.assertTrue((ROOT / pg.RUNBOOK).exists(), "Das Runbook, auf das die Wache zeigt, muss existieren.")


class ProbeOffline(unittest.TestCase):
    """Die Probe über `--rules-file`: Exit-Codes, Annotationen, Step-Summary – ohne Netz."""

    def lauf(self, regeln, env_extra=None, extras=()):
        with tempfile.TemporaryDirectory() as td:
            rules = os.path.join(td, "rules.json")
            summary = os.path.join(td, "summary.md")
            Path(rules).write_text(json.dumps(regeln), encoding="utf-8")
            env = {**os.environ, "GITHUB_ACTIONS": "1", "GITHUB_STEP_SUMMARY": summary,
                   "GITHUB_REPOSITORY": "frank-hartung/franksfinanzcheck-blog",
                   "GITHUB_BASE_REF": "main", **(env_extra or {})}
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pflichtcheck_guard.py"),
                                "--rules-file", rules, *extras], cwd=ROOT, capture_output=True,
                               text=True, env=env, timeout=120)
            zusammenfassung = Path(summary).read_text(encoding="utf-8") if os.path.exists(summary) else ""
            return r.returncode, r.stdout + r.stderr, zusammenfassung

    def lauf_intern(self, regeln, zustand=(), umgebung=None, strict=False):
        """Dieselbe Probe im Prozess – nur so lässt sich die hinterlegte Erklärung
        austauschen. Ein Subprozess wüsste von einer austauschten Kopie nichts."""
        with tempfile.TemporaryDirectory() as td:
            rules = os.path.join(td, "rules.json")
            Path(rules).write_text(json.dumps(regeln), encoding="utf-8")
            puffer = io.StringIO()
            env = {"GITHUB_ACTIONS": "1", "GITHUB_STEP_SUMMARY": "",
                   "PFLICHTCHECK_STRICT": "", **(umgebung or {})}
            with contextlib.ExitStack() as st:
                st.enter_context(mock.patch.dict(os.environ, env, clear=False))
                if zustand != ():
                    st.enter_context(mock.patch.object(gc, "PFLICHT_CHECK_DAUERZUSTAND", dict(zustand)))
                st.enter_context(contextlib.redirect_stdout(puffer))
                rc = pg.probe(branch="main", repo="frank-hartung/franksfinanzcheck-blog",
                              rules_file=rules, strict=strict)
            return rc, puffer.getvalue()

    def test_gruen_wenn_der_zielzweig_das_siegel_verlangt(self):
        rc, out, summary = self.lauf([{"type": "required_status_checks", "ruleset_id": 1,
                                       "parameters": {"required_status_checks": [
                                           {"context": gc.PFLICHT_CHECK_NAME, "integration_id": 15368}]}},
                                      {"type": "pull_request", "parameters": {"required_approving_review_count": 0}}])
        self.assertEqual(0, rc, out)
        self.assertIn("Vertrag erfüllt", out)
        self.assertNotIn("::error::", out)
        self.assertIn("✅", summary)

    def test_rot_mit_annotation_wenn_nur_der_alte_name_verlangt_wird(self):
        rc, out, summary = self.lauf([{"type": "required_status_checks", "ruleset_id": 1,
                                       "parameters": {"required_status_checks": [
                                           {"context": "lock", "integration_id": 15368}]}}])
        self.assertEqual(1, rc, out)
        self.assertIn("::error::", out)
        self.assertIn("`lock` entfernen", out)
        self.assertIn("NICHT verlangt", summary)

    def test_dauerzustand_ungeschuetzt_warnt_statt_rot(self):
        # Der Befund bleibt sichtbar und rot im Text – nur die Folge ist eine Warnung.
        rc, out, summary = self.lauf([], {"GITHUB_BASE_REF": "main"})
        self.assertEqual(0, rc, out)
        self.assertIn("Branch-Schutz für `main`", out)
        self.assertIn("Deko", out)
        self.assertIn("🛑", out)
        self.assertIn("BEKANNT", out)
        self.assertIn("::warning::", out)
        self.assertNotIn("::error::", out)
        self.assertIn("BEKANNT (dokumentierter Dauerzustand)", summary)
        self.assertIn("kein Vorfall", out)

    def test_strict_meldet_denselben_befund_wieder_als_vorfall(self):
        rc, out, _s = self.lauf([], {"GITHUB_BASE_REF": "main"}, extras=["--strict"])
        self.assertEqual(1, rc, out)
        self.assertIn("::error::", out)
        self.assertIn("strenge Meldung", out)
        rc_env, out_env, _s = self.lauf([], {"GITHUB_BASE_REF": "main", "PFLICHTCHECK_STRICT": "1"})
        self.assertEqual(1, rc_env, out_env)
        self.assertIn("::error::", out_env)

    def test_fremder_zweig_fallt_nicht_unter_den_dauerzustand(self):
        # Die Erklärung gilt für `main`. Ein anderer Ziel-Zweig ist kein Freispruch.
        rc, out, _s = self.lauf([], {"GITHUB_BASE_REF": "release"})
        self.assertEqual(1, rc, out)
        self.assertIn("Gilt nicht als dokumentierter Dauerzustand", out)
        self.assertIn("::error::", out)

    def test_abgelaufene_frist_ist_wieder_vorfall(self):
        alt = dict(gc.PFLICHT_CHECK_DAUERZUSTAND, pruefung_bis="2020-01-01")
        rc, out = self.lauf_intern([], alt)
        self.assertEqual(1, rc, out)
        self.assertIn("abgelaufen", out)
        self.assertIn("::error::", out)
        self.assertNotIn("· kein Vorfall", out)

    def test_frist_heute_ist_noch_weich(self):
        # Der Stichtag selbst zählt noch – „bis einschließlich", nicht „bis vor".
        rc, out = self.lauf_intern([], dict(gc.PFLICHT_CHECK_DAUERZUSTAND,
                                            pruefung_bis=pg.dt.date.today().isoformat()))
        self.assertEqual(0, rc, out)
        self.assertIn("BEKANNT", out)

    def test_erklaerung_loeschen_meldet_hart_wie_frueher(self):
        rc, out = self.lauf_intern([], {})
        self.assertEqual(1, rc, out)
        self.assertIn("Fix (Admin)", out)          # Reparatur bleibt das, was dem Zustand fehlt
        self.assertIn("::error::", out)
        self.assertNotIn("BEKANNT", out)
        # Ohne Erklärung gibt es nichts abzuhaken – also kein „passt nicht“-Vermerk.
        self.assertNotIn("Gilt nicht als dokumentierter Dauerzustand", out)
        rc2, out2 = self.lauf_intern([], dict(gc.PFLICHT_CHECK_DAUERZUSTAND, urteil_erwartet="FEHLT"))
        self.assertEqual(1, rc2, out2)
        self.assertIn("Gilt nicht als dokumentierter Dauerzustand", out2)
        self.assertIn("Fix (Admin)", out2)

    def test_neues_ruleset_ohne_bypass_bleibt_vorfall(self):
        # Ein Ruleset, das direkte Pushes blockt, ist der Vorfall vom 19.09. – die
        # Dauerzustand-Erklärung darf ihn nicht einschließen.
        detail = {"id": 123, "name": "Zusatz-Ruleset", "target": "branch", "enforcement": "active",
                  "bypass_actors": [], "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"],
                                                                    "exclude": []}},
                  "rules": [{"type": "pull_request"}]}
        def fake_api(pfad, token="", timeout=20):
            if pfad.endswith("/rules/branches/main"):
                return [], ""                     # kein Status-Check verlangt → UNGESCHUETZT
            if pfad.endswith("/rulesets"):
                return [{"id": 123, "name": "Zusatz-Ruleset", "target": "branch"}], ""
            if "/rulesets/" in pfad:
                return detail, ""
            return None, f"unerwarteter Pfad: {pfad}"
        puffer = io.StringIO()
        with mock.patch.object(pg, "api_get", side_effect=fake_api), \
                mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "1", "PFLICHTCHECK_STRICT": ""},
                                clear=False), \
                contextlib.redirect_stdout(puffer):
            rc = pg.probe(branch="main", repo="o/r")
        out = puffer.getvalue()
        self.assertEqual(1, rc, out)
        self.assertIn("Zusatz-Ruleset", out)
        self.assertIn("blockiert direkte Pushes", out)
        self.assertNotIn("· kein Vorfall", out)

    def test_gruen_mit_liegender_erklaerung_meldet_ueberholt(self):
        regeln = [{"type": "required_status_checks", "ruleset_id": 1,
                   "parameters": {"required_status_checks": [
                       {"context": gc.PFLICHT_CHECK_NAME, "integration_id": 15368}]}},
                  {"type": "pull_request", "parameters": {"required_approving_review_count": 0}}]
        rc, out = self.lauf_intern(regeln)
        self.assertEqual(0, rc, out)
        self.assertIn("Vertrag erfüllt", out)
        self.assertIn("überholt", out)
        self.assertIn("PFLICHT_CHECK_DAUERZUSTAND", out)

    def test_unbrauchbare_datei_ist_warnung_nicht_rot(self):
        with tempfile.TemporaryDirectory() as td:
            kaputt = os.path.join(td, "rules.json")
            Path(kaputt).write_text("{nicht json", encoding="utf-8")
            r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pflichtcheck_guard.py"),
                                "--rules-file", kaputt], cwd=ROOT, capture_output=True, text=True,
                               env={**os.environ, "GITHUB_ACTIONS": "1"}, timeout=120)
        self.assertEqual(0, r.returncode, r.stdout)
        self.assertIn("::warning::", r.stdout)
        self.assertIn("nicht prüfbar", r.stdout)


class DauerzustandDokumentation(unittest.TestCase):
    """Der dokumentierte Dauerzustand (Option B, 20.09.2026) ist eine Wahrheit an
    drei Orten: Vertrag (Erklärung), Wache (Abgleich) und Runbook (Anleitung).

    Geprüft wird die Kohärenz – nicht, dass der Zustand gut ist. Er ist es nicht:
    `main` verlangt keinen Pflicht-Check, und kein Lauf dieses Repos darf das
    ändern. Was geprüft wird, ist, dass die Wache den Befund nur für GENAU diesen
    Stand weich zeichnet, das Runbook den Beleg nennt und das PR-Gate nicht
    versehentlich auf starr geschaltet wird.
    """

    def setUp(self):
        self.zustand = gc.PFLICHT_CHECK_DAUERZUSTAND
        self.wache = (ROOT / "scripts" / gc.PFLICHT_CHECK_WACHE).read_text(encoding="utf-8")
        self.runbuch = (ROOT / self.zustand["runbook"]).read_text(encoding="utf-8")

    def test_erklaerung_erfuellt_c18_gegen_wache_und_runbook(self):
        self.assertEqual([], gc.c18_dauerzustand(self.zustand, self.wache, self.runbuch))

    def test_erklaerung_entspricht_dem_vertrag(self):
        self.assertEqual(gc.PFLICHT_CHECK_NAME, self.zustand["check"])
        self.assertEqual(gc.PFLICHT_CHECK_BRANCH, self.zustand["branch"])
        self.assertEqual(pg.UNGESCHUETZT, self.zustand["urteil_erwartet"])
        self.assertIn(self.zustand["runbook_abschnitt"], self.runbuch)

    def test_belege_nennen_die_evidenz_statt_einer_meinung(self):
        belege = " ".join(self.zustand["belege"].values())
        for muss in ("rules/branches/main", "#327", "4b91938", "administration:write",
                     "integrity_guard.py --gate", "required_status_checks"):
            self.assertIn(muss, belege, f"Beleg fehlt: {muss}")

    def test_runbook_traegt_decision_und_rueckbau(self):
        for muss in ("Dauerzustand – dokumentiert statt Dauer-Alarm", "PR #327", "--strict",
                     "31.12.2026", "kein Grün", "Scheingrün"):
            self.assertIn(muss, self.runbuch, f"Runbook-Aussage fehlt: {muss}")
        self.assertIn("Rückbau in drei Schritten", self.runbuch)

    def test_pr_gate_bleibt_weich_und_der_harte_stopp_davor(self):
        text = WF_PFAD.read_text(encoding="utf-8")
        schritt = [b for n, b in gc.step_blocks(text) if n.startswith("Pflicht-Check-Vertrag prüfen")]
        self.assertEqual(1, len(schritt), schritt)
        # Kein --strict im PR-Gate: sonst wäre jeder PR wieder dauerhaft rot.
        self.assertIn("pflichtcheck_guard.py", schritt[0])
        self.assertNotIn("--strict", schritt[0])
        self.assertNotIn("continue-on-error", schritt[0])
        # Reihenfolge, nicht Textsuche: Der harte Stopp prüft vor der Vertragswache.
        namen = [n for n, _b in gc.step_blocks(text)]
        self.assertTrue(namen[-1].startswith("Pflicht-Check-Vertrag prüfen"), namen)
        self.assertLess(namen.index("Integritäts-Siegel prüfen (HARD STOP – Sabotage-Schutz)"),
                        len(namen) - 1)


class Verdrahtung(unittest.TestCase):
    """Die Wache läuft wirklich – im Gate-Workflow und im Qualitäts-Gate."""

    def test_selbsttest_gruen_und_schreibt_nichts(self):
        vorher = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                capture_output=True, text=True).stdout
        r = subprocess.run([sys.executable, str(ROOT / "scripts" / "pflichtcheck_guard.py"),
                            "--selftest"], cwd=ROOT, capture_output=True, text=True, timeout=120)
        self.assertEqual(0, r.returncode, r.stdout + r.stderr)
        nachher = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                                 capture_output=True, text=True).stdout
        self.assertEqual(vorher, nachher, "Der Selbsttest hat den Arbeitsbaum verändert (C15).")

    def test_im_regelwerk_und_im_qualitaets_gate(self):
        self.assertIn("pflichtcheck_guard.py", gc.GUARDS)
        # Mechanismus statt Namens-Suche: Regelwerk → Gate ruft den Runner →
        # Runner entdeckt die quotierte Kennung → keine Ausnahme.
        self.assertEqual([], sr.verdrahtet("pflichtcheck_guard.py"),
                         "pflichtcheck_guard läuft nicht im Qualitäts-Gate")

    def test_kontrakt_selbsttest_kennt_c18(self):
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = gc._selftest()
        self.assertEqual(0, rc, puffer.getvalue())
        self.assertIn("C1–C18", puffer.getvalue())


class BypassWarnung(unittest.TestCase):
    """Grün UND blind war der Vorfall vom 19.09.2026 (Issue #320).

    Das Ruleset #23695872 verlangte `Integritäts-Siegel` auf `main` ohne
    Bypass-Akteur; der Check entsteht nur in Pull Requests, Pflicht-Checks gelten
    aber für jeden Push. Jeder Bot-Push wurde abgelehnt, Deploy #998 starb,
    „Deploy auf gh-pages" wurde übersprungen – und diese Wache meldete
    „✅ Vertrag erfüllt". Der Vertrag war erfüllt; die Automation stand trotzdem.

    Diese Tests frieren die Nachprüfung ein: grün bleibt grün (Exit 0, der
    Melder darf nicht selbst zum Vorfall werden), aber die Lücke wird genannt.
    """

    NAME = gc.PFLICHT_CHECK_NAME
    REGELN = [{"type": "required_status_checks", "ruleset_id": 23695872,
               "ruleset_source_type": "Repository", "ruleset_source": "o/r",
               "parameters": {"strict_required_status_checks_policy": False,
                              "required_status_checks": [
                                  {"context": NAME, "integration_id": 15368}]}},
              {"type": "pull_request", "parameters": {"required_approving_review_count": 0}}]
    WORKFLOWS = {
        "integrity-lock.yml": "on:\n  pull_request:\n    branches: [main]\n"
                              "  workflow_dispatch: {}\njobs:\n  lock:\n",
        "deploy.yml": "permissions:\n  contents: write\njobs:\n  d:\n    steps:\n"
                      "      - run: bash scripts/git_sync.sh --push-only\n",
        "integrity-lock-nur-lesen.yml": "permissions:\n  contents: read\n",
    }

    def detail(self, bypass=None, enforcement="active", include=("~DEFAULT_BRANCH",),
               mit_check=True):
        regeln = ([{"type": "deletion"}, {"type": "non_fast_forward"}]
                  + ([{"type": "required_status_checks",
                       "parameters": {"strict_required_status_checks_policy": False,
                                      "required_status_checks": [
                                          {"context": self.NAME, "integration_id": 15368}]}}]
                     if mit_check else []))
        return {"id": 23695872, "name": "Integritäts-Lock (PR-Gate)", "target": "branch",
                "enforcement": enforcement, "bypass_actors": bypass,
                "conditions": {"ref_name": {"include": list(include), "exclude": []}},
                "rules": regeln}

    def probe(self, detail, workflows=None, regeln=None, api_fehler=False):
        regeln = self.REGELN if regeln is None else regeln
        workflows = self.WORKFLOWS if workflows is None else workflows

        def fake_api(pfad, token="", timeout=20):
            if api_fehler:
                return None, "HTTP 500: simulierter Ausfall"
            if pfad.endswith("/rules/branches/main"):
                return regeln, ""
            if pfad.endswith("/rulesets"):
                return [{"id": 23695872, "name": "Integritäts-Lock (PR-Gate)",
                         "target": "branch"}], ""
            if "/rulesets/" in pfad:
                return detail, ""
            return None, f"unerwarteter Pfad: {pfad}"

        puffer = io.StringIO()
        # GITHUB_ACTIONS=1, weil annotate() nur im Lauf ::warning:: schreibt –
        # genau dieser Weg ist der Beweis im PR-Gate (Annotation am Job).
        # Die Dauerzustand-Erklärung wird abgeschaltet: Diese Klasse prüft die
        # Bypass-Nachprüfung, nicht den überholt-Hinweis für einen grünen Lauf
        # (der eigene Fall: ProbeOffline.test_gruen_mit_liegender_erklaerung…).
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "1"}, clear=False), \
                mock.patch.object(pg, "api_get", side_effect=fake_api), \
                mock.patch.object(pg, "workflows_laden", return_value=workflows), \
                mock.patch.object(gc, "PFLICHT_CHECK_DAUERZUSTAND", {}), \
                mock.patch.object(pg, "erwarteter_check",
                                  return_value=(self.NAME, "lock", "")), \
                contextlib.redirect_stdout(puffer):
            rc = pg.probe(branch="main", repo="o/r")
        return rc, puffer.getvalue()

    # --- Die Lücke muss gemeldet werden – ohne das Urteil zu kippen --------- #
    def test_pflicht_check_ohne_bypass_warnt_und_bleibt_gruen(self):
        rc, out = self.probe(self.detail(bypass=None))
        self.assertEqual(0, rc, out)                     # Vertrag erfüllt → grün
        self.assertIn("Vertrag erfüllt", out)
        self.assertIn("::warning::", out)                # aber nicht blind
        self.assertIn("Schein-Sicherheit", out)
        self.assertIn("23695872", out)
        self.assertIn("KEINEN Bypass-Akteur", out)
        self.assertIn("nur in Pull Requests", out)       # Trigger-Lage erkannt
        self.assertIn("deploy.yml", out)                 # der Betroffene wird genannt
        self.assertIn("1 Workflows", out)                # nur der echte Direkt-Pusher
        self.assertIn("schutz", out)                     # die neue git_sync-Klasse
        self.assertIn(pg.RUNBOOK, out)
        self.assertNotIn("::error::", out)

    def test_leere_bypass_list_zaehlt_wie_null(self):
        _rc, out = self.probe(self.detail(bypass=[]))
        self.assertIn("Schein-Sicherheit", out)

    # --- Und sie muss schweigen, wenn sie nicht gilt ------------------------ #
    def test_mit_bypass_akteur_keine_warnung(self):
        rc, out = self.probe(self.detail(bypass=[{"actor_id": 15368,
                                                  "actor_type": "Integration",
                                                  "bypass_mode": "always"}]))
        self.assertEqual(0, rc, out)
        self.assertIn("Vertrag erfüllt", out)
        self.assertNotIn("Schein-Sicherheit", out)
        self.assertNotIn("::warning::", out)

    def test_ohne_direkt_pusher_keine_warnung(self):
        # Niemand committet selbst auf main → der Check bindet nur PRs: gewollt.
        rc, out = self.probe(self.detail(bypass=None),
                             workflows={"gate.yml": "permissions:\n  contents: read\n"})
        self.assertEqual(0, rc, out)
        self.assertNotIn("Schein-Sicherheit", out)

    def test_deaktiviertes_ruleset_warnt_nicht(self):
        _rc, out = self.probe(self.detail(bypass=None, enforcement="disabled"),
                              regeln=[])
        self.assertNotIn("Schein-Sicherheit", out)

    def test_api_ausfall_ist_best_effort_nicht_rot(self):
        rc, out = self.probe(self.detail(bypass=None), api_fehler=True)
        self.assertEqual(0, rc, out)                     # kein Netz → kein Urteil
        self.assertIn("nicht prüfbar", out)
        self.assertNotIn("Schein-Sicherheit", out)

if __name__ == "__main__":
    unittest.main()
