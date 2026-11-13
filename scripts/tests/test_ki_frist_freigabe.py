#!/usr/bin/env python3
"""#1028: Abschluss nur mit Belegen, echtem Workflow und sicherem Readback.

Alle Belege und GitHub-Antworten sind isolierte Fiktionen. Kein Test beweist
Herkunft, rechtliche Konformität, eine tatsächliche Freigabe oder Live-Ausgabe.
"""
from __future__ import annotations

import base64
import contextlib
import copy
import datetime as dt
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import fristen_check as fristen
from scripts import ki_frist_freigabe as gate

ROOT = Path(__file__).resolve().parents[2]
REPO = gate.REPOSITORY
FID = gate.FRIST_ID
TODAY = dt.date(2026, 11, 12)
NOW = dt.datetime(2026, 11, 12, 12, tzinfo=dt.timezone.utc)
DEPLOY_SHA = "a" * 40
WORKFLOW_SHA = "b" * 40
MAIN_SHA = "c" * 40
RUN_ID = 1234
DEPLOY_RUN = 8765
DEPLOY_ID = 3456
PAGE_JOB = 5678
TITLE = "KI-VO: maschinenlesbare KI-Kennzeichnung für Bestandssysteme (Frist 02.12.2026)"


def step(name, number, conclusion="success"):
    return {"name": name, "number": number, "conclusion": conclusion}


def job(name, steps, number=123):
    return {"name": name, "id": number, "status": "completed", "run_attempt": 1,
            "conclusion": "success", "steps": steps}


class IssuesFake:
    def __init__(self, aktiv=True):
        self.aktiv = aktiv
        self.repo = REPO
        self.closed = []
        self.reopened = []
        self.comments = []
        self.labels = []
        self.created = []
        self.title = f"⏰ Frist: {TITLE}"
        self.state = "OPEN"
        self.close_ok = True
        self.reopen_ok = True

    def offene_issues(self):
        return [{"number": 1028, "title": self.title}] if self.state == "OPEN" else []

    def _run(self, *args):
        if args[:2] == ("issue", "view"):
            return json.dumps({"number": 1028, "title": self.title, "state": self.state})
        raise AssertionError(f"unerwarteter gh-Aufruf {args}")

    def schliessen(self, number, comment):
        self.closed.append((number, comment))
        if self.close_ok:
            self.state = "CLOSED"
        return self.close_ok

    def wieder_oeffnen(self, number, comment):
        self.reopened.append((number, comment))
        if self.reopen_ok:
            self.state = "OPEN"
        return self.reopen_ok

    def kommentieren(self, number, comment):
        self.comments.append((number, comment))

    def label_setzen(self, number, label):
        self.labels.append((number, label))

    def erstellen(self, title, body, labels):
        self.created.append((title, body, labels))
        return 9000


class FreigabeFixture(unittest.TestCase):
    def setUp(self):
        # Negative Fixtures drucken absichtlich ::error; sie dürfen in Actions
        # keine echten Fehler-Annotationen für einen grünen Testlauf erzeugen.
        self.capture = contextlib.redirect_stdout(io.StringIO())
        self.capture.__enter__()
        self.addCleanup(self.capture.__exit__, None, None, None)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / gate.BELEG_ORDNER).mkdir(parents=True)
        (self.root / "data").mkdir(parents=True)
        for rel in (*gate.ABSCHLUSS_CODE, "data/recht-fristen.yaml"):
            ziel = self.root / rel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / rel, ziel)
        (self.root / "data/ki_kennzeichnung.yaml").write_text(
            "maschinell:\n  - bot\nmenschlich: []\n", encoding="utf-8")
        self.watch = {"frist": "2026-12-02", "funde": 0, "ungeklaert_erstmals": {}}
        self.write_watch()
        self.proof = self.doc("anbieter.md", "Schriftlicher Anbieterbeleg und Systemversion für Testzwecke.")
        self.image = self.doc("bilder.md", "Bildinventar und Prüfung der Herkunft für Testzwecke.")
        self.register = self.doc("register.md", "Einzelfallprüfung und redaktionelle Verantwortung, Testdaten.")
        self.live = self.doc("live.md", "Browser-, Feed-, Ton-, Bild- und Plattformprüfung, Testdaten.")
        self.manifest = {
            "frist_id": FID,
            "systeme": [{"name": "System A", "version": "1.2", "anbieter": "Anbieter A",
                         "rolle": "betreiber", "inverkehrgebracht_am": "2026-01-01",
                         "nachweis": self.proof}],
            "bildinventar": self.image,
            "registerpruefung": self.register,
            "deploy": {"run_id": DEPLOY_RUN, "deployment_id": DEPLOY_ID, "head_sha": DEPLOY_SHA},
            "live_abnahme": {"zeitpunkt": "2026-11-11T11:00:00Z", "pruefer": "Prüferin",
                             "url": "https://franksfinanzcheck.de/posts/beispiel/",
                             "kanaele": ["seite", "feed", "tonspur", "bild", "pinterest"],
                             "nachweis": self.live},
            "betreiberfreigabe": {"zeitpunkt": "2026-11-11T12:00:00Z", "name": "Betreiber",
                                   "github_login": "frank-hartung"},
        }
        self.sign_and_save()
        self.event_path = self.root / "event.json"
        self.event_path.write_text(json.dumps({"inputs": {"erledigt": FID}}), encoding="utf-8")
        self.env = {
            "GITHUB_ACTIONS": "true", "GITHUB_EVENT_NAME": "workflow_dispatch",
            "GITHUB_REF": "refs/heads/main", "GITHUB_JOB": "fristen",
            "GITHUB_WORKFLOW_REF": f"{REPO}/.github/workflows/fristen-check.yml@refs/heads/main",
            "GITHUB_REPOSITORY": REPO, "GITHUB_ACTOR": "frank-hartung",
            "GITHUB_TRIGGERING_ACTOR": "frank-hartung", "GITHUB_RUN_ID": str(RUN_ID),
            "GITHUB_RUN_ATTEMPT": "1", "GITHUB_SHA": WORKFLOW_SHA, "GITHUB_EVENT_PATH": str(self.event_path),
        }
        self.deploy_run = {"id": DEPLOY_RUN, "path": ".github/workflows/deploy.yml",
                           "head_branch": "main", "head_sha": DEPLOY_SHA, "event": "push", "run_attempt": 1,
                           "status": "completed", "conclusion": "success", "updated_at": "2026-11-11T10:30:00Z"}
        self.deploy_jobs = {"total_count": 2, "jobs": [
            job("deploy", [step("KI-Cover – finale Provenienzprüfung", 10),
                           step("KI-Provenienz – finales Veröffentlichungs-Gate", 11),
                           step("Artefakt für offizielles Pages-Deployment hochladen", 12)]),
            job("An GitHub Pages ausliefern (Environment github-pages)",
                [step("Deployment auslösen", 1)], PAGE_JOB),
        ]}
        self.deployment = {"id": DEPLOY_ID, "environment": "github-pages",
                           "ref": "main", "sha": DEPLOY_SHA}
        self.statuses = [{"state": "success", "created_at": "2026-11-11T10:20:00Z",
                          "log_url": f"https://github.com/{REPO}/actions/runs/{DEPLOY_RUN}/job/{PAGE_JOB}"}]
        self.deployments = [copy.deepcopy(self.deployment)]
        self.run = {"id": RUN_ID, "path": ".github/workflows/fristen-check.yml", "run_attempt": 1,
                    "event": "workflow_dispatch", "head_branch": "main", "head_sha": WORKFLOW_SHA,
                    "status": "completed", "conclusion": "success", "created_at": "2026-11-11T12:01:00Z",
                    "actor": {"login": "frank-hartung"}, "triggering_actor": {"login": "frank-hartung"}}
        self.workflow_jobs = {"total_count": 3, "jobs": [
            job("fristen", [step("Fristen prüfen + Issues eskalieren", 2),
                            step("Report & State committen", 3)]),
            job("KI-Abschluss-Gegenproben", [step(gate.TEST_SCHRITT, 3)]),
            job("KI-Freigabe nach State und Tests", [
                step("KI-Freigabe nach Tests vorbereiten", 2),
                step("KI-Abschluss-State committen", 3), step(gate.FINAL_SCHRITT, 4)]),
        ]}
        self.remote_state = {}
        self.remote_overrides = {}
        self.remote_ref_overrides = {}
        self.api_calls = []
        self.ref = {"object": {"sha": MAIN_SHA}}
        self.active_deploys = {status: {"total_count": 0, "workflow_runs": []}
                               for status in ("queued", "in_progress", "waiting", "requested", "pending")}
        self.active_emergency_deploys = copy.deepcopy(self.active_deploys)
        self.comparison = {"status": "ahead", "behind_by": 0, "total_commits": 2,
                           "merge_base_commit": {"sha": DEPLOY_SHA},
                           "files": [{"filename": gate.BELEG, "status": "added"},
                                     {"filename": "data/fristen_state.json", "status": "modified"}]}
        self.issue_frist = {"id": FID, "titel": TITLE, "faellig_am": "2026-12-02",
                            "einmalig": True, "erinnerung_ab_tage": 30}
        self.fstate = {"issue": 1028, "erledigt_am": TODAY.isoformat(), "last_done": TODAY.isoformat(),
                       "ki_abschluss": gate.quittung_erstellen(self.root, self.env, api=self.api_in_progress, heute=TODAY)}
        self.remote_state[FID] = copy.deepcopy(self.fstate)

    def write_watch(self):
        (self.root / "data/ki_provenienz_state.json").write_text(json.dumps(self.watch), encoding="utf-8")

    def doc(self, name, content):
        rel = gate.BELEG_ORDNER + "/" + name
        data = content.encode("utf-8")
        (self.root / rel).write_bytes(data)
        return {"datei": rel, "sha256": gate._sha(data)}

    def sign_and_save(self):
        f = self.manifest.get("betreiberfreigabe")
        if isinstance(f, dict):
            digest = gate.buendel_sha256(self.manifest)
            f["buendel_sha256"] = digest
            f["nachweis"] = self.doc("freigabe.md", f"Bewusste Betreiberfreigabe für Testdaten.\n"
                                     f"{f.get('github_login', '')}\n{f.get('zeitpunkt', '')}\n{digest}\n")
        self.save()

    def save(self):
        (self.root / gate.BELEG).write_text(json.dumps(self.manifest, ensure_ascii=False), encoding="utf-8")

    def api(self, endpoint):
        self.api_calls.append(endpoint)
        prefix = f"repos/{REPO}/"
        if not endpoint.startswith(prefix):
            raise gate.FreigabeFehler(f"unerwartetes Repository: {endpoint}")
        key = endpoint[len(prefix):]
        mapping = {
            f"actions/runs/{DEPLOY_RUN}": self.deploy_run,
            f"actions/runs/{DEPLOY_RUN}/jobs?filter=latest&per_page=100": self.deploy_jobs,
            f"deployments/{DEPLOY_ID}": self.deployment,
            f"deployments/{DEPLOY_ID}/statuses?per_page=100": self.statuses,
            f"deployments/{DEPLOY_ID}/statuses?per_page=1": self.statuses[:1],
            "deployments?environment=github-pages&per_page=100": self.deployments,
            f"actions/runs/{RUN_ID}": self.run,
            f"actions/runs/{RUN_ID}/jobs?filter=latest&per_page=100": self.workflow_jobs,
            "git/ref/heads/main": self.ref,
            f"compare/{DEPLOY_SHA}...{MAIN_SHA}?per_page=100": self.comparison,
        }
        if key in mapping:
            return copy.deepcopy(mapping[key])
        for workflow, active in (("deploy.yml", self.active_deploys),
                                 ("notfall-deploy.yml", self.active_emergency_deploys)):
            for status, response in active.items():
                if key == f"actions/workflows/{workflow}/runs?status={status}&per_page=1":
                    return copy.deepcopy(response)
        if key.startswith("contents/") and "?ref=" in key:
            rel, ref = key[len("contents/"):].split("?ref=")
            if ref not in (MAIN_SHA, WORKFLOW_SHA):
                raise gate.FreigabeFehler("unbekannter Ref")
            if (ref, rel) in self.remote_ref_overrides:
                data = self.remote_ref_overrides[(ref, rel)]
            elif rel in self.remote_overrides:
                data = self.remote_overrides[rel]
            elif rel == "data/fristen_state.json":
                data = json.dumps(self.remote_state).encode()
            else:
                data = (self.root / rel).read_bytes()
            return {"encoding": "base64", "content": base64.b64encode(data).decode()}
        raise gate.FreigabeFehler(f"unerwarteter API-Aufruf: {key}")

    def api_in_progress(self, endpoint):
        result = self.api(endpoint)
        if endpoint == f"repos/{REPO}/actions/runs/{RUN_ID}":
            result["status"] = "in_progress"
            result["conclusion"] = None
        return result

    def check(self, *, aktuell=True):
        return gate.pruefen(self.root, REPO, TODAY, api=self.api, jetzt=NOW, aktuell=aktuell)

    def test_vollstaendige_fiktive_belege_und_echter_ablauf_formal_positiv(self):
        self.assertEqual(self.check(), [])
        gate.dispatcher_pruefen(self.root, self.env, api=self.api_in_progress)
        self.assertEqual(gate.quittung_pruefen(self.root, REPO, TODAY, self.fstate,
                                               api=self.api, env={}, jetzt=NOW), [])
        gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)

    def test_fehlende_und_inhaltlich_unvollstaendige_bloecke_sperren(self):
        faelle = [
            lambda m: m.pop("systeme"),
            lambda m: m["systeme"][0].pop("version"),
            lambda m: m["systeme"][0].update(rolle="unbekannt"),
            lambda m: m["systeme"][0].update(inverkehrgebracht_am="2027-01-01"),
            lambda m: m["systeme"][0].pop("nachweis"),
            lambda m: m.pop("bildinventar"),
            lambda m: m.pop("registerpruefung"),
            lambda m: m.pop("live_abnahme"),
            lambda m: m["live_abnahme"].update(kanaele=["seite", "feed"]),
            lambda m: m["live_abnahme"].update(url="https://franksfinanzcheck.de.evil.test/"),
            lambda m: m["live_abnahme"].update(zeitpunkt="2026-11-11T10:29:59Z"),
            lambda m: m.pop("betreiberfreigabe"),
            lambda m: m["betreiberfreigabe"].update(github_login="irgendwer"),
            lambda m: m["betreiberfreigabe"].update(zeitpunkt="2026-11-11T10:00:00Z"),
            lambda m: m.pop("deploy"),
        ]
        original = copy.deepcopy(self.manifest)
        for mutate in faelle:
            with self.subTest(mutate=mutate):
                self.manifest = copy.deepcopy(original)
                mutate(self.manifest)
                self.sign_and_save()
                self.assertTrue(self.check())

    def test_hash_aenderung_leerdatei_und_pfadflucht_sperren(self):
        (self.root / self.proof["datei"]).write_text("Manipuliert", encoding="utf-8")
        self.assertTrue(self.check())
        (self.root / self.proof["datei"]).write_text("", encoding="utf-8")
        self.assertTrue(self.check())
        self.manifest["systeme"][0]["nachweis"]["datei"] = "docs/ki-vo-abschluss/../../etc/passwd"
        self.sign_and_save()
        self.assertTrue(self.check())

    def test_fehlende_beschaedigte_und_doppelte_manifest_datei_sperrt(self):
        p = self.root / gate.BELEG
        for content in (b"{", b'{}', b'{"frist_id":"x","frist_id":"y"}'):
            with self.subTest(content=content):
                p.write_bytes(content)
                self.assertTrue(self.check())
        p.unlink()
        self.assertTrue(self.check())

    def test_freigabe_ist_an_buendel_zeitpunkt_und_akteur_gebunden(self):
        self.manifest["live_abnahme"]["pruefer"] = "Nachträglich geändert"
        self.save()
        self.assertTrue(self.check())
        self.sign_and_save()
        self.assertEqual(self.check(), [])
        p = self.root / self.manifest["betreiberfreigabe"]["nachweis"]["datei"]
        p.write_text("Freigabe ohne Bündelbindung", encoding="utf-8")
        self.manifest["betreiberfreigabe"]["nachweis"]["sha256"] = gate._sha(p.read_bytes())
        self.save()
        self.assertTrue(self.check())

    def test_register_und_wachzustand_koennen_nicht_durch_loeschen_scheinbar_heilen(self):
        (self.root / "data/ki_kennzeichnung.yaml").write_text(
            "maschinell:\n  - bot\nmenschlich:\n  - ungeprueft\n", encoding="utf-8")
        self.assertTrue(self.check())
        (self.root / "data/ki_kennzeichnung.yaml").write_text("maschinell: []\nmenschlich: []\n", encoding="utf-8")
        for watch in ({"frist": "2026-12-02", "funde": 0, "ungeklaert_erstmals": {"alt": "2026-11-01"}},
                      {"frist": "2026-12-02", "funde": False, "ungeklaert_erstmals": {}},
                      {"frist": "falsch", "funde": 0, "ungeklaert_erstmals": {}},
                      {"frist": "2026-12-02", "funde": 1, "ungeklaert_erstmals": {}}, {}):
            self.watch = watch
            self.write_watch()
            with self.subTest(watch=watch):
                self.assertTrue(self.check())
        (self.root / "data/ki_provenienz_state.json").unlink()
        self.assertTrue(self.check())

    def test_vollstaendiger_zweiter_deploy_versuch_ist_formal_zulaessig(self):
        self.deploy_run["run_attempt"] = 2
        for job_eintrag in self.deploy_jobs["jobs"]:
            job_eintrag["run_attempt"] = 2
        self.assertEqual(self.check(), [])

    def test_deploy_run_pages_job_gates_reihenfolge_und_status_sperren(self):
        cases = [
            (self.deploy_run, "head_branch", "arena/test"),
            (self.deploy_run, "conclusion", "failure"),
            (self.deploy_run, "path", ".github/workflows/falsch.yml"),
            (self.deploy_run, "updated_at", "2026-11-11T11:01:00Z"),
            (self.deploy_run, "run_attempt", 2),
            (self.deploy_jobs, "total_count", 3),
            (self.deploy_jobs["jobs"][0], "run_attempt", 2),
            (self.deploy_jobs["jobs"][1], "run_attempt", 2),
            (self.deploy_jobs["jobs"][0]["steps"][1], "conclusion", "skipped"),
            (self.deploy_jobs["jobs"][0]["steps"][1], "number", 13),
            (self.deploy_jobs["jobs"][1], "conclusion", "failure"),
            (self.deployment, "sha", "b" * 40),
            (self.statuses[0], "state", "failure"),
            (self.statuses[0], "log_url", f"https://github.com/{REPO}/actions/runs/{DEPLOY_RUN}/job/999"),
            (self.statuses[0], "created_at", "2026-11-11T11:01:00Z"),
        ]
        for obj, key, value in cases:
            with self.subTest(key=key, value=value):
                old = obj[key]
                obj[key] = value
                self.assertTrue(self.check())
                obj[key] = old
        self.deployments.insert(0, {"id": 999, "ref": "anderer-branch"})
        self.assertTrue(self.check())
        # Ein späteres Deployment entwertet den historischen Abschluss nicht;
        # beim ersten Abschluss MUSS aber der neue Live-Stand geprüft werden.
        self.statuses.insert(0, {"state": "inactive"})
        self.assertEqual(self.check(aktuell=False), [])

    def test_api_ausfall_und_fremdes_repository_sind_nicht_gruen(self):
        def broken(_):
            raise gate.FreigabeFehler("GitHub nicht erreichbar")
        self.assertTrue(gate.pruefen(self.root, REPO, TODAY, api=broken, jetzt=NOW))
        self.assertTrue(gate.pruefen(self.root, "fremd/repo", TODAY, api=self.api, jetzt=NOW))

    def test_dispatch_muss_explizit_vom_inhaber_auf_main_sein(self):
        variants = {"GITHUB_ACTOR": "anderer", "GITHUB_TRIGGERING_ACTOR": "anderer",
                    "GITHUB_EVENT_NAME": "schedule", "GITHUB_REF": "refs/heads/feature",
                    "GITHUB_JOB": "fremd", "GITHUB_WORKFLOW_REF": "anderer-workflow",
                    "GITHUB_REPOSITORY": "fremd/repo", "GITHUB_RUN_ID": "0",
                    "GITHUB_RUN_ATTEMPT": "2", "GITHUB_SHA": "d" * 40}
        for key, value in variants.items():
            with self.subTest(key=key):
                env = dict(self.env, **{key: value})
                with self.assertRaises(gate.FreigabeFehler):
                    gate.dispatcher_pruefen(self.root, env, api=self.api_in_progress)
        # Ein bereits beendeter oder vor der Freigabe gestarteter Lauf ist
        # keine lebende, bewusste Betreiberanforderung.
        with self.assertRaises(gate.FreigabeFehler):
            gate.dispatcher_pruefen(self.root, self.env, api=self.api)
        self.run["created_at"] = "2026-11-11T11:59:59Z"
        with self.assertRaises(gate.FreigabeFehler):
            gate.dispatcher_pruefen(self.root, self.env, api=self.api_in_progress)
        self.run["created_at"] = "2026-11-11T12:01:00Z"
        self.event_path.write_text(json.dumps({"inputs": {"erledigt": "andere-frist"}}))
        with self.assertRaises(gate.FreigabeFehler):
            gate.dispatcher_pruefen(self.root, self.env, api=self.api_in_progress)

    def test_altflag_allein_und_manipulierte_quittung_sperren(self):
        for state in ({"erledigt_am": "2026-11-12", "last_done": "2026-11-12"},
                      dict(self.fstate, ki_abschluss={}),
                      dict(self.fstate, last_done="2026-11-11")):
            with self.subTest(state=state):
                self.assertTrue(gate.quittung_pruefen(self.root, REPO, TODAY, state,
                                                       api=self.api, env={}, jetzt=NOW))
        self.manifest["systeme"][0]["version"] = "2"
        self.sign_and_save()
        self.assertTrue(gate.quittung_pruefen(self.root, REPO, TODAY, self.fstate,
                                               api=self.api, env={}, jetzt=NOW))

    def test_quittung_verlangt_erfolgreichen_manuellen_workflow_und_alle_jobs(self):
        checks = [
            (self.run, "event", "schedule"), (self.run, "conclusion", "failure"),
            (self.run, "actor", {"login": "anderer"}),
            (self.run, "head_sha", "d" * 40), (self.run, "run_attempt", 2),
            (self.workflow_jobs, "total_count", 4),
            (self.workflow_jobs["jobs"][0], "run_attempt", 2),
            (self.workflow_jobs["jobs"][1], "conclusion", "failure"),
            (self.workflow_jobs["jobs"][1]["steps"][0], "conclusion", "skipped"),
            (self.workflow_jobs["jobs"][2], "run_attempt", 2),
            (self.workflow_jobs["jobs"][2]["steps"][0], "conclusion", "skipped"),
        ]
        for obj, key, value in checks:
            with self.subTest(key=key, value=value):
                old = obj[key]
                obj[key] = value
                self.assertTrue(gate.quittung_pruefen(self.root, REPO, TODAY, self.fstate,
                                                       api=self.api, env={}, jetzt=NOW))
                obj[key] = old
        self.remote_overrides[gate.BELEG] = b"anderer Beleg im Workflow-Commit"
        self.assertTrue(gate.quittung_pruefen(self.root, REPO, TODAY, self.fstate,
                                               api=self.api, env={}, jetzt=NOW))

    def test_laufender_abschluss_verlangt_gruene_vorjobs_desselben_versuchs(self):
        env = dict(self.env, GITHUB_JOB="ki-freigabe")
        for obj, key, value in (
            (self.workflow_jobs["jobs"][0], "conclusion", "failure"),
            (self.workflow_jobs["jobs"][1], "run_attempt", 2),
            (self.workflow_jobs["jobs"][1]["steps"][0], "conclusion", "skipped"),
            (self.workflow_jobs, "total_count", 4),
        ):
            with self.subTest(key=key, value=value):
                old = obj[key]
                obj[key] = value
                self.assertTrue(gate.quittung_pruefen(self.root, REPO, TODAY, self.fstate,
                                                       api=self.api_in_progress, env=env, jetzt=NOW))
                obj[key] = old
        self.assertEqual(gate.quittung_pruefen(self.root, REPO, TODAY, self.fstate,
                                               api=self.api_in_progress, env=env, jetzt=NOW), [])
        self.assertTrue(gate.quittung_pruefen(self.root, REPO, TODAY, self.fstate,
                                               api=self.api_in_progress, env=self.env, jetzt=NOW))

    def test_readback_bindet_ausgefuehrten_code_und_eingaben_an_dispatch_und_main(self):
        for rel in gate.ABSCHLUSS_CODE + gate.ABSCHLUSS_EINGABEN:
            for ref in (WORKFLOW_SHA, MAIN_SHA):
                with self.subTest(ref=ref, rel=rel):
                    self.remote_ref_overrides[(ref, rel)] = b"ungetestete oder ueberholte Fassung"
                    with self.assertRaises(gate.FreigabeFehler):
                        gate.remote_state_pruefen(self.root, REPO, self.fstate,
                                                  api=self.api, heute=TODAY, jetzt=NOW)
                    self.remote_ref_overrides.clear()
        self.remote_ref_overrides[(WORKFLOW_SHA, self.live["datei"])] = b"beim Dispatch fehlender Beleg"
        with self.assertRaises(gate.FreigabeFehler):
            gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)

    def test_readback_muss_state_und_jede_belegdatei_in_main_enthalten(self):
        self.remote_state[FID]["ki_abschluss"]["beleg_sha256"] = "d" * 64
        with self.assertRaises(gate.FreigabeFehler):
            gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)
        self.remote_state[FID] = copy.deepcopy(self.fstate)
        self.remote_overrides[self.live["datei"]] = b"auf main anders"
        with self.assertRaises(gate.FreigabeFehler):
            gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)
        for rel in ("data/ki_kennzeichnung.yaml", "data/ki_provenienz_state.json"):
            self.remote_overrides = {rel: b"auf main anders"}
            with self.subTest(rel=rel), self.assertRaises(gate.FreigabeFehler):
                gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)

    def test_readback_sperrt_unveroeffentlichten_site_und_ki_drift(self):
        for pfad in ("content/posts/neu/index.md", "layouts/rss.xml", "scripts/ki_provenienz.py",
                     "scripts/social_channels/pinterest.py", ".github/workflows/deploy.yml",
                     ".github/workflows/notfall-deploy.yml"):
            with self.subTest(pfad=pfad):
                self.comparison["files"].append({"filename": pfad, "status": "modified"})
                with self.assertRaises(gate.FreigabeFehler):
                    gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)
                self.comparison["files"].pop()
        self.comparison["files"].append({"filename": "docs/neu.md", "status": "renamed",
                                          "previous_filename": "content/posts/alt.md"})
        with self.assertRaises(gate.FreigabeFehler):
            gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)
        self.comparison["files"] = [{"filename": "docs/test.md", "status": "modified"}] * 300
        with self.assertRaises(gate.FreigabeFehler):
            gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)
        self.comparison["files"] = []
        self.comparison["status"] = "diverged"
        with self.assertRaises(gate.FreigabeFehler):
            gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)

    def test_readback_stoppt_wenn_ein_deploy_aussteht_oder_nicht_messbar_ist(self):
        for workflow, active in (("deploy", self.active_deploys),
                                 ("notfall", self.active_emergency_deploys)):
            for status in active:
                with self.subTest(workflow=workflow, status=status):
                    active[status] = {"total_count": 1, "workflow_runs": [{"id": 99}]}
                    with self.assertRaises(gate.FreigabeFehler):
                        gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)
                    active[status] = {"total_count": 0, "workflow_runs": []}
            active["queued"] = {}
            with self.subTest(workflow=workflow, status="blind"), self.assertRaises(gate.FreigabeFehler):
                gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)
            active["queued"] = {"total_count": 0, "workflow_runs": []}

    def test_readback_sperrt_neuestes_deployment_mit_anderem_ref_oder_defekten_daten(self):
        for neuer_eintrag in ({"id": 999, "ref": "anderer-branch"}, {}, None):
            with self.subTest(deployment=neuer_eintrag):
                self.deployments.insert(0, neuer_eintrag)
                with self.assertRaises(gate.FreigabeFehler):
                    gate.remote_state_pruefen(self.root, REPO, self.fstate, api=self.api, heute=TODAY, jetzt=NOW)
                self.deployments.pop(0)

    def test_readback_stoppt_wenn_main_parallel_veraendert_wird(self):
        count = 0
        def wechsel(endpoint):
            nonlocal count
            if endpoint.endswith("git/ref/heads/main"):
                count += 1
                if count == 2:
                    return {"object": {"sha": "d" * 40}}
            return self.api(endpoint)
        with self.assertRaises(gate.FreigabeFehler):
            gate.remote_state_pruefen(self.root, REPO, self.fstate, api=wechsel, heute=TODAY, jetzt=NOW)

    def test_erledigt_ohne_belege_blockiert_nur_ki_und_beruehrt_issue_nicht(self):
        other = {"id": "andere", "titel": "Andere", "faellig_am": "2026-11-29", "intervall_tage": 90}
        state = {FID: {"issue": 1028}, "andere": {"issue": 77}}
        issues = IssuesFake()
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "pruefen", return_value=["Beleg fehlt"]), \
                patch.object(gate, "quittung_erstellen", side_effect=gate.FreigabeFehler("keine Freigabe")):
            denied = fristen.markiere_erledigt([FID, "andere"], [self.issue_frist, other], state, TODAY, issues)
        self.assertTrue(denied)
        self.assertEqual(state[FID], {"issue": 1028})
        self.assertEqual(state["andere"]["last_done"], TODAY.isoformat())
        self.assertEqual([n for n, _ in issues.closed], [77])

    def test_ki_erledigt_mit_freigabe_schliesst_vor_push_nicht(self):
        state = {FID: {"issue": 1028}}
        issues = IssuesFake()
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "pruefen", return_value=[]), \
                patch.object(gate, "quittung_erstellen", return_value=self.fstate["ki_abschluss"]):
            denied = fristen.markiere_erledigt([FID], [self.issue_frist], state, TODAY, issues)
        self.assertFalse(denied)
        self.assertNotIn("erledigt_am", state[FID])
        self.assertNotIn("last_done", state[FID])
        self.assertEqual(state[FID]["ki_abschluss_vorgemerkt"]["datum"], TODAY.isoformat())
        self.assertEqual(state[FID]["issue"], 1028)
        self.assertEqual(issues.closed, [])

    def test_vormerkung_wird_erst_im_ki_job_nach_readback_zum_abschluss(self):
        pending = {"issue": 1028, "ki_abschluss_vorgemerkt": {
            "datum": TODAY.isoformat(), "quittung": self.fstate["ki_abschluss"]}}
        self.remote_state[FID] = copy.deepcopy(pending)
        state = {FID: pending}
        issues = IssuesFake()
        env = dict(self.env, GITHUB_JOB="ki-freigabe")
        with patch.object(fristen, "REPO", self.root), \
                patch.object(fristen, "STATE_PATH", self.root / "data/fristen_state.json"), \
                patch.object(gate, "_api", side_effect=self.api_in_progress), patch.dict(os.environ, env, clear=True):
            self.assertEqual(fristen.bereite_ki_frist_vor(state, issues, TODAY), 0)
        self.assertEqual(state[FID]["erledigt_am"], TODAY.isoformat())
        self.assertNotIn("ki_abschluss_vorgemerkt", state[FID])
        self.assertEqual(issues.closed, [])
        self.assertEqual(json.loads((self.root / "data/fristen_state.json").read_text())[FID], state[FID])

    def test_vorbereitung_ohne_readback_oder_im_falschen_job_schreibt_nichts(self):
        pending = {"issue": 1028, "ki_abschluss_vorgemerkt": {
            "datum": TODAY.isoformat(), "quittung": self.fstate["ki_abschluss"]}}
        for fall in ("readback", "job"):
            with self.subTest(fall=fall):
                state = {FID: copy.deepcopy(pending)}
                self.remote_state[FID] = copy.deepcopy(pending)
                self.remote_overrides = {self.live["datei"]: b"falsch"} if fall == "readback" else {}
                env = dict(self.env, GITHUB_JOB="ki-freigabe" if fall == "readback" else "fristen")
                with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api_in_progress), \
                        patch.object(fristen, "schreibe_state") as write, patch.dict(os.environ, env, clear=True):
                    self.assertEqual(fristen.bereite_ki_frist_vor(state, IssuesFake(), TODAY), 2)
                self.assertNotIn("erledigt_am", state[FID])
                write.assert_not_called()

    def test_vorbereitung_stoppt_vor_zweitem_push_bei_falschem_issue_oder_altem_versuch(self):
        pending = {"issue": 1028, "ki_abschluss_vorgemerkt": {
            "datum": TODAY.isoformat(), "quittung": self.fstate["ki_abschluss"]}}
        for fall in ("nummer", "titel", "versuch"):
            with self.subTest(fall=fall):
                state = {FID: copy.deepcopy(pending)}
                self.remote_state[FID] = copy.deepcopy(pending)
                issues = IssuesFake()
                env = dict(self.env, GITHUB_JOB="ki-freigabe")
                if fall == "nummer":
                    state[FID]["issue"] = 77
                elif fall == "titel":
                    issues.title = "Fremde Frist"
                else:
                    state[FID]["ki_abschluss_vorgemerkt"]["quittung"]["workflow_attempt"] = 99
                with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api_in_progress), \
                        patch.object(fristen, "schreibe_state") as write, patch.dict(os.environ, env, clear=True):
                    self.assertEqual(fristen.bereite_ki_frist_vor(state, issues, TODAY), 2)
                write.assert_not_called()
                self.assertEqual(issues.closed, [])

    def test_altstatus_ohne_quittung_ist_offen_und_loest_keinen_close_aus(self):
        issues = IssuesFake()
        state = {FID: {"issue": 1028, "erledigt_am": "2026-11-01", "last_done": "2026-11-01"}}
        with patch.object(fristen, "REPO", self.root):
            ergebnisse = fristen.bewerte_fristen([self.issue_frist], state, TODAY, issues, dry_run=False)
        self.assertEqual(ergebnisse[0]["status"], "Erinnerung")
        self.assertNotIn("erledigt_am", state[FID])
        self.assertEqual(state[FID]["ki_abschluss_unbestaetigt"]["erledigt_am"], "2026-11-01")
        self.assertEqual(issues.closed, [])

    def test_abbruch_nach_zweitem_push_wird_quarantaenisiert_und_vollstaendig_neu_geprueft(self):
        issues = IssuesFake()
        state = {FID: copy.deepcopy(self.fstate)}
        self.run["conclusion"] = "failure"  # z. B. Close fehlgeschlagen nach State-Push
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api), \
                patch.dict(os.environ, {}, clear=True):
            result = fristen.bewerte_fristen([self.issue_frist], state, TODAY, issues, False)
        self.assertEqual(result[0]["status"], "Erinnerung")
        self.assertIn("ki_schutz_fehler", result[0])
        self.assertNotIn("erledigt_am", state[FID])
        self.assertIn("ki_abschluss_unbestaetigt", state[FID])
        self.assertEqual(issues.closed, [])

        # Neuer vollständiger Versuch: frischer Antrag, alle Jobs erneut grün,
        # Remote-Pushes simuliert. Mitternacht zwischen Antrag und Freigabe ist
        # erlaubt; der Antragstag bleibt in der Quittung unverändert.
        self.run["run_attempt"] = 2
        env = dict(self.env, GITHUB_RUN_ATTEMPT="2")
        for job_eintrag in self.workflow_jobs["jobs"]:
            job_eintrag["run_attempt"] = 2
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api_in_progress), \
                patch.dict(os.environ, env, clear=True):
            self.assertFalse(fristen.markiere_erledigt([FID], [self.issue_frist], state, TODAY, issues))
        self.assertNotIn("erledigt_am", state[FID])
        self.assertEqual(state[FID]["ki_abschluss_vorgemerkt"]["quittung"]["workflow_attempt"], 2)
        self.remote_state[FID] = copy.deepcopy(state[FID])
        morgen = TODAY + dt.timedelta(days=1)
        with patch.object(fristen, "REPO", self.root), \
                patch.object(fristen, "STATE_PATH", self.root / "data/fristen_state.json"), \
                patch.object(gate, "_api", side_effect=self.api_in_progress), \
                patch.dict(os.environ, dict(env, GITHUB_JOB="ki-freigabe"), clear=True):
            self.assertEqual(fristen.bereite_ki_frist_vor(state, issues, morgen), 0)
            self.assertEqual(state[FID]["erledigt_am"], TODAY.isoformat())
            self.remote_state[FID] = copy.deepcopy(state[FID])
            self.assertEqual(fristen.schliesse_ki_frist([self.issue_frist], state, issues, morgen), 0)
        self.assertEqual([n for n, _ in issues.closed], [1028])
        self.run["conclusion"] = "success"
        self.assertEqual(gate.quittung_pruefen(self.root, REPO, morgen, state[FID],
                                               api=self.api, env={}, jetzt=NOW), [])

    def test_api_ausfall_quarantaene_und_sicherer_readback_stellen_status_wieder_her(self):
        issues = IssuesFake()
        issues.state = "CLOSED"  # Ein bestätigter Abschluss bleibt auch tatsächlich geschlossen.
        state = {FID: copy.deepcopy(self.fstate)}
        with patch.object(fristen, "REPO", self.root), \
                patch.object(gate, "_api", side_effect=gate.FreigabeFehler("API nicht erreichbar")), \
                patch.dict(os.environ, {}, clear=True):
            result = fristen.bewerte_fristen([self.issue_frist], state, TODAY, issues, False)
        self.assertEqual(result[0]["status"], "Erinnerung")
        self.assertNotIn("erledigt_am", state[FID])
        self.assertEqual(state[FID]["ki_abschluss_unbestaetigt"]["ki_abschluss"], self.fstate["ki_abschluss"])
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api), \
                patch.dict(os.environ, {}, clear=True):
            result = fristen.bewerte_fristen([self.issue_frist], state, TODAY, issues, False)
        self.assertEqual(result[0]["status"], "abgeschlossen")
        self.assertEqual(state[FID], self.fstate)
        self.assertEqual(issues.closed, [])

    def test_wieder_geoeffnetes_abgeschlossenes_issue_ist_nicht_mehr_gruen(self):
        issues = IssuesFake()  # auch nach gültiger Quittung steht #1028 nun wieder OPEN
        state = {FID: copy.deepcopy(self.fstate)}
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api), \
                patch.dict(os.environ, {}, clear=True):
            for _ in range(2):  # Quarantäne darf sich bei offenem Issue nicht selbst wiederherstellen.
                result = fristen.bewerte_fristen([self.issue_frist], state, TODAY, issues, False)
                self.assertEqual(result[0]["status"], "Erinnerung")
                self.assertIn("ki_schutz_fehler", result[0])
                self.assertNotIn("erledigt_am", state[FID])
                self.assertEqual(state[FID]["ki_abschluss_unbestaetigt"]["ki_abschluss"],
                                 self.fstate["ki_abschluss"])
        self.assertEqual(issues.closed, [])
        self.assertEqual(issues.reopened, [])
        self.assertEqual(issues.state, "OPEN")

    def test_issue_readback_fehler_quarantaenisiert_eine_gueltige_quittung(self):
        for fall in ("titel", "nummer", "netz"):
            with self.subTest(fall=fall):
                issues = IssuesFake()
                issues.state = "CLOSED"
                state = {FID: copy.deepcopy(self.fstate)}
                if fall == "titel":
                    issues.title = "Fremdes Issue"
                elif fall == "nummer":
                    state[FID]["issue"] = 999
                read = patch.object(issues, "_run", return_value=None) if fall == "netz" else contextlib.nullcontext()
                with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api), \
                        patch.dict(os.environ, {}, clear=True), read:
                    result = fristen.bewerte_fristen([self.issue_frist], state, TODAY, issues, False)
                self.assertEqual(result[0]["status"], "Erinnerung")
                self.assertIn("ki_schutz_fehler", result[0])
                self.assertNotIn("erledigt_am", state[FID])
                self.assertIn("ki_abschluss_unbestaetigt", state[FID])
                self.assertEqual(issues.closed, [])
                self.assertEqual(issues.reopened, [])

    def test_vorzeitig_geschlossenes_unbelegtes_issue_wird_gezielt_wieder_geoeffnet(self):
        issues = IssuesFake()
        issues.state = "CLOSED"
        state = {FID: {"issue": 1028}}
        result = fristen.bewerte_fristen([self.issue_frist], state, TODAY, issues, False)
        self.assertEqual(result[0]["status"], "Erinnerung")
        self.assertNotIn("ki_schutz_fehler", result[0])
        self.assertEqual([n for n, _ in issues.reopened], [1028])
        self.assertEqual(issues.state, "OPEN")
        self.assertEqual(issues.closed, [])

    def test_issue_identitaet_oder_unsicherer_close_fuehren_nie_zu_blinder_wiedereroeffnung(self):
        for fall in ("falsche_nummer", "falscher_titel", "lesefehler", "unsichere_quittung", "reopen-fehler"):
            with self.subTest(fall=fall):
                issues = IssuesFake()
                issues.state = "CLOSED"
                state = {FID: {"issue": 1028}}
                if fall == "falsche_nummer":
                    state[FID]["issue"] = 999
                elif fall == "falscher_titel":
                    issues.title = "Andere Frist"
                elif fall == "unsichere_quittung":
                    state[FID]["ki_abschluss_unbestaetigt"] = {"erledigt_am": "2026-11-12"}
                elif fall == "reopen-fehler":
                    issues.reopen_ok = False
                read = patch.object(issues, "_run", return_value=None) if fall == "lesefehler" else contextlib.nullcontext()
                with read:
                    result = fristen.bewerte_fristen([self.issue_frist], state, TODAY, issues, False)
                self.assertIn("ki_schutz_fehler", result[0])
                self.assertEqual(issues.closed, [])
                if fall != "reopen-fehler":
                    self.assertEqual(issues.reopened, [])
                self.assertEqual(issues.state, "CLOSED")

    def test_fremde_frist_kann_issue_1028_auch_ueber_alias_nicht_schliessen(self):
        other = {"id": "andere", "titel": "Andere", "faellig_am": "2026-11-29", "intervall_tage": 90}
        for nummer in (1028, "1028", "001028", "https://github.com/frank-hartung/franksfinanzcheck-blog/issues/1028", 0, True):
            with self.subTest(nummer=nummer):
                issues = IssuesFake()
                state = {"andere": {"issue": nummer}}
                self.assertTrue(fristen.markiere_erledigt(["andere"], [other], state, TODAY, issues))
                self.assertEqual(state["andere"]["last_done"], TODAY.isoformat())
                self.assertEqual(state["andere"]["issue"], nummer)
                self.assertEqual(issues.closed, [])

    def test_fremde_frist_darf_issue_1028_weder_automatisch_schliessen_noch_eskalieren(self):
        for modus in ("einmalig", "eskalation", "titel-map", "erstellt"):
            with self.subTest(modus=modus):
                issues = IssuesFake()
                other = {"id": "andere", "titel": "Andere", "faellig_am": "2026-11-11"}
                state = {"andere": {"issue": 1028}}
                if modus in ("einmalig", "titel-map"):
                    other["einmalig"] = True
                    state["andere"]["erledigt_am"] = "2026-11-10"
                if modus == "titel-map":
                    state["andere"].pop("issue")
                    issues.offene_issues = Mock(return_value=[{"title": "⏰ Frist: Andere", "number": 1028}])
                elif modus == "erstellt":
                    state["andere"].pop("issue")
                    issues.erstellen = Mock(return_value=1028)
                result = fristen.bewerte_fristen([other], state, TODAY, issues, False)
                self.assertIn("ki_schutz_fehler", result[0])
                self.assertEqual(issues.closed, [])
                self.assertEqual(issues.comments, [])
                self.assertEqual(issues.labels, [])

    def test_fremde_frist_mit_geschuetztem_issue_bleibt_sichtbar_und_sichert_state(self):
        issues = IssuesFake()
        other = {"id": "andere", "titel": "Andere", "faellig_am": "2026-11-29", "intervall_tage": 90}
        state = {FID: {"issue": 1028}, "andere": {"issue": 1028}}
        with patch.object(fristen, "lade_fristen", return_value=[self.issue_frist, other]), \
                patch.object(fristen, "lade_state", return_value=state), \
                patch.object(fristen, "Issues", return_value=issues), \
                patch.object(fristen, "veraltungs_scan", return_value=[]), \
                patch.object(fristen, "STAND_DATEIEN", []), \
                patch.object(fristen, "schreibe_report"), \
                patch.object(fristen, "schreibe_state") as write, \
                patch.object(sys, "argv", ["fristen_check.py", "--now", TODAY.isoformat(), "--done", "andere"]):
            self.assertEqual(fristen.main(), 3)
        write.assert_called_once()
        self.assertEqual(state["andere"]["last_done"], TODAY.isoformat())
        self.assertEqual(state["andere"]["issue"], 1028)
        self.assertEqual(issues.closed, [])

    def test_issue_ueberwachungsfehler_ist_rot_aber_state_andere_fristen_wird_gesichert(self):
        issues = IssuesFake()
        issues.title = "Anderes Issue"
        other = {"id": "andere", "titel": "Andere", "faellig_am": "2027-01-01", "intervall_tage": 90}
        state = {FID: {"issue": 1028}, "andere": {}}
        with patch.object(fristen, "lade_fristen", return_value=[self.issue_frist, other]), \
                patch.object(fristen, "lade_state", return_value=state), \
                patch.object(fristen, "Issues", return_value=issues), \
                patch.object(fristen, "veraltungs_scan", return_value=[]), \
                patch.object(fristen, "STAND_DATEIEN", []), \
                patch.object(fristen, "schreibe_report") as report, \
                patch.object(fristen, "schreibe_state") as write, \
                patch.object(sys, "argv", ["fristen_check.py", "--now", TODAY.isoformat(), "--done", "andere"]):
            self.assertEqual(fristen.main(), 3)
        report.assert_called_once()
        write.assert_called_once()
        self.assertEqual(state["andere"]["last_done"], TODAY.isoformat())
        self.assertEqual(issues.closed, [])
        self.assertEqual(issues.reopened, [])

    def test_geloeschte_ki_frist_bleibt_sichtbar_und_nicht_abschliessbar(self):
        calendar = self.root / "data/recht-fristen.yaml"
        calendar.write_text("fristen:\n  - id: andere\n    titel: Andere\n    faellig_am: '2026-11-29'\n", encoding="utf-8")
        with patch.object(fristen, "YAML_PATH", calendar):
            geladen = fristen.lade_fristen()
        self.assertEqual({f["id"] for f in geladen}, {"andere", FID})
        ki = next(f for f in geladen if f["id"] == FID)
        self.assertFalse(fristen.ki_frist_konform(ki))
        issues = IssuesFake()
        result = fristen.bewerte_fristen(geladen, {FID: {"issue": 1028}}, TODAY, issues, True)
        self.assertEqual(next(e for e in result if e["frist"]["id"] == FID)["due"], dt.date(2026, 12, 2))
        self.assertEqual(issues.closed, [])
        # Der Ersatzkalender soll nicht nur im Report stehen: Ein eindeutig
        # unbelegt geschlossenes Issue wird trotz Konfigurationsfehler geöffnet.
        issues.state = "CLOSED"
        result = fristen.bewerte_fristen([ki], {FID: {"issue": 1028}}, TODAY, issues, False)
        self.assertEqual(result[0]["due"], dt.date(2026, 12, 2))
        self.assertIn("ki_schutz_fehler", result[0])
        self.assertEqual([nummer for nummer, _ in issues.reopened], [1028])
        self.assertEqual(issues.state, "OPEN")

    def test_defekte_fristkonfiguration_verschiebt_oder_schliesst_nicht(self):
        for aenderung in ({"faellig_am": "2027-01-01"}, {"einmalig": False}, {"intervall_tage": 100},
                          {"titel": "fremdes Issue"}, {"erinnerung_ab_tage": 1},
                          {"erinnerung_ab_tage": "kaputt"}, {"eskalation_nach_tagen": [14, 30]}):
            with self.subTest(aenderung=aenderung):
                frist = dict(self.issue_frist, **aenderung)
                issues = IssuesFake()
                state = {FID: copy.deepcopy(self.fstate)}
                with patch.object(fristen, "REPO", self.root), \
                        patch.object(gate, "pruefen", return_value=[]), \
                        patch.object(gate, "quittung_erstellen", return_value=self.fstate["ki_abschluss"]):
                    result = fristen.bewerte_fristen([frist], state, TODAY, issues, False)
                    self.assertTrue(fristen.markiere_erledigt([FID], [frist], state, TODAY, issues))
                self.assertEqual(result[0]["status"], "Erinnerung")
                self.assertEqual(result[0]["due"], dt.date(2026, 12, 2))
                self.assertEqual(issues.closed, [])

    def test_gueltige_alte_quittung_darf_status_zeigen_aber_nie_issue_schliessen(self):
        issues = IssuesFake()
        issues.state = "CLOSED"
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api), \
                patch.dict(os.environ, {}, clear=True):
            result = fristen.bewerte_fristen([self.issue_frist], {FID: self.fstate}, TODAY, issues, False)
        self.assertEqual(result[0]["status"], "abgeschlossen")
        self.assertEqual(issues.closed, [])

    def test_trockenlauf_mit_done_schreibt_und_schliesst_nichts(self):
        other = {"id": "andere", "titel": "Andere", "faellig_am": "2026-11-29", "intervall_tage": 90}
        state = {FID: {"issue": 1028}, "andere": {"issue": 77}}
        issues = IssuesFake()
        with patch.object(gate, "pruefen", return_value=[]), patch.object(gate, "quittung_erstellen") as receipt:
            denied = fristen.markiere_erledigt([FID, "andere"], [self.issue_frist, other], state,
                                               TODAY, issues, dry_run=True)
        self.assertFalse(denied)
        self.assertEqual(state[FID], {"issue": 1028})
        self.assertEqual(issues.closed, [])
        receipt.assert_not_called()
        with patch.object(fristen, "lade_fristen", return_value=[self.issue_frist, other]), \
                patch.object(fristen, "lade_state", return_value=state), \
                patch.object(fristen, "Issues", return_value=IssuesFake(aktiv=False)), \
                patch.object(fristen, "veraltungs_scan", return_value=[]), \
                patch.object(fristen, "STAND_DATEIEN", []), \
                patch.object(fristen, "schreibe_report") as report, \
                patch.object(fristen, "schreibe_state") as write, \
                patch.object(gate, "pruefen", return_value=[]), \
                patch.object(sys, "argv", ["fristen_check.py", "--dry-run", "--done", f"{FID},andere"]):
            self.assertEqual(fristen.main(), 0)
        report.assert_not_called()
        write.assert_not_called()

    def test_trockenlauf_gibt_frist_in_erinnerung_nicht_gruen_aus(self):
        output = io.StringIO()
        with patch.object(fristen, "lade_fristen", return_value=[self.issue_frist]), \
                patch.object(fristen, "lade_state", return_value={FID: {"issue": 1028}}), \
                patch.object(fristen, "Issues", return_value=IssuesFake(aktiv=False)), \
                patch.object(fristen, "veraltungs_scan", return_value=[]), \
                patch.object(fristen, "STAND_DATEIEN", []), \
                patch.object(fristen, "schreibe_report") as report, \
                patch.object(fristen, "schreibe_state") as write, \
                patch.object(sys, "argv", ["fristen_check.py", "--now", TODAY.isoformat(), "--dry-run"]), \
                contextlib.redirect_stdout(output):
            self.assertEqual(fristen.main(), 0)
        self.assertIn("🟡 Frist in Erinnerung", output.getvalue())
        self.assertNotIn("🟢 Alles im grünen Bereich", output.getvalue())
        report.assert_not_called()
        write.assert_not_called()

    def test_finalisierung_nur_nach_readback_und_mit_exaktem_issue(self):
        issues = IssuesFake()
        env = dict(self.env, GITHUB_JOB="ki-freigabe")
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api_in_progress), \
                patch.dict(os.environ, env, clear=True):
            self.assertEqual(fristen.schliesse_ki_frist([self.issue_frist], {FID: self.fstate}, issues, TODAY), 0)
        self.assertEqual([n for n, _ in issues.closed], [1028])

    def test_finalisierung_bei_fehlendem_main_readback_oder_falschem_issue_keine_wirkung(self):
        for fall in ("readback", "issue", "actor", "close-error"):
            with self.subTest(fall=fall):
                issues = IssuesFake()
                env = dict(self.env, GITHUB_JOB="ki-freigabe")
                self.remote_overrides = {}
                if fall == "readback":
                    self.remote_overrides[self.live["datei"]] = b"nicht aktuell"
                elif fall == "issue":
                    issues.title = "Anderes Issue"
                elif fall == "actor":
                    env["GITHUB_TRIGGERING_ACTOR"] = "anderer"
                else:
                    issues.close_ok = False
                with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api_in_progress), \
                        patch.dict(os.environ, env, clear=True):
                    self.assertEqual(fristen.schliesse_ki_frist([self.issue_frist], {FID: self.fstate}, issues, TODAY), 2)
                if fall != "close-error":
                    self.assertEqual(issues.closed, [])

    def test_bereits_geschlossenes_issue_ist_idempotent_aber_nur_nach_aller_pruefung(self):
        issues = IssuesFake()
        issues.state = "CLOSED"
        env = dict(self.env, GITHUB_JOB="ki-freigabe")
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api_in_progress), \
                patch.dict(os.environ, env, clear=True):
            self.assertEqual(fristen.schliesse_ki_frist([self.issue_frist], {FID: self.fstate}, issues, TODAY), 0)
        self.assertEqual(issues.closed, [])
        self.assertEqual(issues.reopened, [])
        self.remote_overrides[self.live["datei"]] = b"widerspruechlich"
        with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api_in_progress), \
                patch.dict(os.environ, env, clear=True):
            self.assertEqual(fristen.schliesse_ki_frist([self.issue_frist], {FID: self.fstate}, issues, TODAY), 2)
        self.assertEqual(issues.closed, [])

    def test_aenderung_nach_issue_read_oder_unbestaetigter_close_stoppt_finalisierung(self):
        for fall in ("main", "deploy", "close-readback"):
            with self.subTest(fall=fall):
                issues = IssuesFake()
                env = dict(self.env, GITHUB_JOB="ki-freigabe")
                self.ref = {"object": {"sha": MAIN_SHA}}
                self.active_deploys["queued"] = {"total_count": 0, "workflow_runs": []}
                original = issues._run

                def issue_read(*args):
                    result = original(*args)
                    if fall == "main":
                        self.ref = {"object": {"sha": "d" * 40}}
                    elif fall == "deploy":
                        self.active_deploys["queued"] = {"total_count": 1, "workflow_runs": [{"id": 99}]}
                    return result

                with patch.object(fristen, "REPO", self.root), patch.object(gate, "_api", side_effect=self.api_in_progress), \
                        patch.object(issues, "_run", side_effect=issue_read), patch.dict(os.environ, env, clear=True):
                    if fall == "close-readback":
                        with patch.object(issues, "schliessen", return_value=True):  # API bleibt OPEN
                            self.assertEqual(fristen.schliesse_ki_frist([self.issue_frist], {FID: self.fstate}, issues, TODAY), 2)
                    else:
                        self.assertEqual(fristen.schliesse_ki_frist([self.issue_frist], {FID: self.fstate}, issues, TODAY), 2)
                self.assertEqual(issues.closed, [])
                self.assertEqual(issues.state, "OPEN")

    def test_workflow_verankert_tests_readback_und_unabhaengige_fristen(self):
        import yaml
        workflow = yaml.safe_load((ROOT / ".github/workflows/fristen-check.yml").read_text())
        jobs = workflow["jobs"]
        self.assertNotIn("needs", jobs["fristen"])
        self.assertEqual(set(jobs["ki-freigabe"]["needs"]), {"fristen", "abschluss-tests"})
        names = [s.get("name") for s in jobs["fristen"]["steps"]]
        self.assertLess(names.index("Fristen prüfen + Issues eskalieren"), names.index("Report & State committen"))
        final = jobs["ki-freigabe"]["steps"][-1]
        self.assertEqual(final["name"], gate.FINAL_SCHRITT)
        self.assertIn("--finalize-ki", final["run"])
        self.assertEqual(workflow["permissions"]["actions"], "read")
        self.assertEqual(workflow["permissions"]["deployments"], "read")
        self.assertIn('"${args[@]}"', jobs["fristen"]["steps"][2]["run"])


if __name__ == "__main__":
    unittest.main()
