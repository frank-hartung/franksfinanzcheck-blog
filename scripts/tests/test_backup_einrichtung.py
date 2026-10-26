"""Vertrag: Offsite-Backup – Einrichtungsprüfung, Workflow, Anleitung (WF-9E5A / #761).

WARUM: Der KV-Job des Offsite-Backups war ab seinem ersten Lauf rot, weil
seine Zugänge nie eingerichtet wurden. Das Rot war richtig (fail-closed), die
Lage drumherum nicht: falscher Rat im Alarm, eine Prüfung, die nur „gesetzt?“
fragte, ein Verweis auf ein nicht existierendes Runbook, kein Vorlauf vor dem
Ablauf eines Tokens und eine Rückspiel-Anleitung, die ohne `--remote` nur in
Wranglers lokale Simulation geschrieben hätte. Diese Tests halten fest:

  1. PRÜFER: `scripts/backup_einrichtung.py --selftest` ist grün; ohne Werte
     wird nichts live abgefragt; kein Secret-Wert erreicht eine Ausgabe.
  2. WORKFLOW: Beide Jobs laufen im Environment `backup`; die Prüfung steht
     vor Export und Ablage, ist nicht abschaltbar (kein continue-on-error)
     und behält ihren Schrittnamen (das Alerting erkennt daran die Klasse);
     die Fristwarnung ist der letzte Schritt und läuft nur nach Erfolg; die
     Ablage prüft Entwurf + Größe und räumt Teil-Releases ab; kein Artefakt.
  3. SCHNITTSTELLE: Die Umgebungsnamen, die der Prüfer liest, sind im Job
     genau auf die dokumentierten Secrets/Variablen verdrahtet.
  4. ANLEITUNG: Die Datei existiert, nennt jede Einstellung und zitiert die
     Abhilfe-Links des Prüfers wörtlich (eine Quelle der Wahrheit).
  5. RÜCKSPIELEN: Jede dokumentierte schreibende `wrangler kv`-Zeile trägt
     `--remote`.
  6. NAMEN: Kein Funktions- oder Modulname des Prüfers fällt unter die
     CodeQL-Heuristik für sensible Daten (Vertrag test_zugangs_namensvertrag).
"""
from __future__ import annotations

import ast
import datetime as dt
import importlib.util
import io
import re
import subprocess
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts"
sys.path.insert(0, str(SCRIPTS))

import backup_einrichtung as be  # noqa: E402

WORKFLOW = REPO / ".github" / "workflows" / "backup-offsite.yml"
ANLEITUNG = REPO / be.ANLEITUNG
JETZT = dt.datetime(2026, 10, 15, 12, 0, tzinfo=dt.timezone.utc)

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover – CI installiert PyYAML
    yaml = None


def _workflow() -> dict:
    if yaml is None:
        raise unittest.SkipTest("PyYAML lokal nicht installiert (CI installiert es)")
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def _frischwache_workflow() -> dict:
    if yaml is None:
        raise unittest.SkipTest("PyYAML lokal nicht installiert (CI installiert es)")
    wf = REPO / ".github" / "workflows" / "backup-frischwache.yml"
    return yaml.safe_load(wf.read_text(encoding="utf-8"))


class _OhneNetz:
    """HTTP-Ersatz, der jeden Aufruf protokolliert und eine Antwort-Funktion nutzt."""

    def __init__(self, antwort=None):
        self.aufrufe: list[str] = []
        self.antwort = antwort

    def __call__(self, methode, url, kopf=None):
        self.aufrufe.append(url)
        if self.antwort is None:
            raise AssertionError(f"unerwarteter Netzaufruf: {url}")
        return self.antwort(url, kopf or {})


class PrueferVerhalten(unittest.TestCase):
    def setUp(self):
        self._http = be.HTTP

    def tearDown(self):
        be.HTTP = self._http

    def test_selbsttest_ist_gruen(self):
        lauf = subprocess.run([sys.executable, str(SCRIPTS / "backup_einrichtung.py"), "--selftest"],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
        self.assertIn("✅ backup_einrichtung-Selbsttest", lauf.stdout)
        # Ein Selbsttest im CI-Lauf darf nie echte Workflow-Befehle ausgeben.
        self.assertNotIn("::error", lauf.stdout)
        self.assertNotIn("::warning", lauf.stdout)

    def test_lage_von_761_ohne_netzaufruf(self):
        be.HTTP = _OhneNetz()  # wirft bei jedem Aufruf
        ergebnis = be.pruefen({"CF_ACCOUNT_ID": "0123456789abcdef0123456789abcdef"}, JETZT)
        self.assertEqual([b.kennung for b in ergebnis.offen()], ["E1", "E2", "E3", "E5", "E6"])
        self.assertEqual(ergebnis.stufe_von("E4"), "ok")
        self.assertIn("NICHTS gesichert", be.schlusssatz(ergebnis))
        self.assertIn("Neustart ändert daran nichts", be.schlusssatz(ergebnis))

    def test_jeder_offene_punkt_hat_eine_abhilfe(self):
        be.HTTP = _OhneNetz()
        ergebnis = be.pruefen({}, JETZT)
        for befund in ergebnis.offen():
            with self.subTest(befund.kennung):
                self.assertTrue(befund.abhilfe, f"{befund.kennung} ohne Abhilfe")

    def test_kein_secret_wert_in_irgendeiner_ausgabe(self):
        gift = {"ZIEL_TOKEN": "github_pat_GIFT_A", "PASSWORT": "GIFT-B-mindestens-zwanzig-zeichen",
                "CF_API_TOKEN": "GIFT_C_cloudflare", "GH_TOKEN": "GIFT_D_lauf"}
        umgebung = {"ZIEL_REPO": "frank-hartung/franksfinanzcheck-backup", **gift,
                    "CF_ACCOUNT_ID": "a" * 32, "KV_NAMESPACE_ID": "b" * 32,
                    "GITHUB_REPOSITORY": "frank-hartung/franksfinanzcheck-blog"}

        def fehlerwelt(url, kopf):
            # Jede API lehnt ab: alle Fehlertexte werden erzeugt.
            return 401, {}, {"message": "Bad credentials", "success": False,
                             "errors": [{"code": 1000, "message": "Invalid API Token"}]}, ""

        be.HTTP = _OhneNetz(fehlerwelt)
        ergebnis = be.pruefen(umgebung, JETZT)
        texte = "\n".join([be.konsolen_bericht(ergebnis), be.zusammenfassung(ergebnis, "x/y"),
                           *be.annotationen(ergebnis)])
        for wert in gift.values():
            self.assertNotIn(wert, texte)
        self.assertTrue(ergebnis.offen(), "abgelehnte Zugänge müssen rot sein")

    def test_erst_absichern_dann_befuellen(self):
        # Lage nach dem Merge von #769: Environment „backup“ ohne Branch-Regel,
        # Zugänge fehlen. Wer die Prüfliste von oben abarbeitet, beginnt mit E8 –
        # aber nur, wenn ein fremder Branch wirklich an die Zugänge käme.
        nur_regeln = {"protected_branches": False, "custom_branch_policies": True}

        def welt(status, politik=None, branches=(), regeln=()):
            def antwort(url, kopf):
                if url.endswith("/deployment-branch-policies"):
                    return 200, {}, {"branch_policies": [{"name": n} for n in branches]}, ""
                self.assertTrue(url.endswith("/environments/backup"), url)
                return status, {}, {"protection_rules": [{"type": t} for t in regeln],
                                    "deployment_branch_policy": politik}, ""
            return antwort

        teil = {"GITHUB_REPOSITORY": "frank-hartung/franksfinanzcheck-blog", "CF_ACCOUNT_ID": "a" * 32}
        faelle = {
            "ohne Branch-Regel (Stand 15.10.)": (welt(200, None), True),
            "Environment fehlt": (welt(404), True),
            "fremder Branch erlaubt": (welt(200, nur_regeln, ("main", "arena/*")), True),
            "nur main": (welt(200, nur_regeln, ("main",)), False),
            "nur Pflicht-Freigabe": (welt(200, nur_regeln, ("main",), ("required_reviewers",)), False),
        }
        for name, (antwort, erwartet) in faelle.items():
            with self.subTest(name):
                be.HTTP = _OhneNetz(antwort)
                lage = be.pruefen(teil, JETZT)
                self.assertEqual(lage.environment_offen, erwartet)
                self.assertEqual(bool(be.reihenfolge_hinweis(lage)), erwartet)

        be.HTTP = _OhneNetz(welt(200, None))
        lage = be.pruefen(teil, JETZT)
        konsole, summary = be.konsolen_bericht(lage), be.zusammenfassung(lage, "x/y")
        self.assertLess(konsole.index("Zuerst E8"), konsole.index(" E1 "), "Hinweis gehört vor die Liste")
        self.assertLess(summary.index("Zuerst E8"), summary.index("| Punkt |"), "Hinweis gehört vor die Tabelle")

        # Fertig eingerichtet, Environment noch offen: kein Reihenfolge-Hinweis
        # mehr (es gibt nichts mehr einzutragen) – E8 steht im Schlusssatz.
        fertig = be.Ergebnis(environment_offen=True)
        fertig.neu("E8", "Environment-Schutz", "warnung", "jeder Branch darf das Environment nutzen")
        self.assertEqual(be.reihenfolge_hinweis(fertig), "")
        self.assertIn("E8", be.schlusssatz(fertig))
        self.assertNotIn("Zuerst E8", be.konsolen_bericht(fertig) + be.zusammenfassung(fertig))

    def test_fristen_grenzen(self):
        with redirect_stdout(io.StringIO()):
            self.assertEqual(be.befehl_fristen({"BACKUP_FRIST_TAGE": str(be.FRIST_ROT - 1)}), 1)
            self.assertEqual(be.befehl_fristen({"BACKUP_FRIST_TAGE": str(be.FRIST_ROT)}), 0)
            self.assertEqual(be.befehl_fristen({}), 0)
        self.assertEqual((be.FRIST_ROT, be.FRIST_GELB), (14, 30))


class WorkflowVertrag(unittest.TestCase):
    def setUp(self):
        self.wf = _workflow()
        self.kv = self.wf["jobs"]["kv-backup"]
        self.schritte = self.kv["steps"]
        self.namen = [s.get("name", "") for s in self.schritte]

    def _schritt(self, teil: str) -> dict:
        treffer = [s for s in self.schritte if teil in s.get("name", "")]
        self.assertEqual(len(treffer), 1, f"genau ein Schritt mit „{teil}“ erwartet: {self.namen}")
        return treffer[0]

    def test_beide_jobs_im_environment_backup(self):
        for name in ("backup", "kv-backup"):
            with self.subTest(name):
                umgebung = self.wf["jobs"][name].get("environment")
                if isinstance(umgebung, dict):
                    umgebung = umgebung.get("name")
                self.assertEqual(umgebung, "backup")

    def test_pruefung_ist_pflicht_und_steht_vorn(self):
        pruefung = self._schritt("Voraussetzungen prüfen")
        self.assertIn("scripts/backup_einrichtung.py --pruefen", pruefung.get("run", ""))
        self.assertNotIn("continue-on-error", pruefung)
        self.assertNotIn("if", pruefung)
        index = self.schritte.index(pruefung)
        for spaeter in ("Exportieren", "Im privaten Backup-Repo ablegen"):
            self.assertGreater(self.schritte.index(self._schritt(spaeter)), index,
                               f"„{spaeter}“ muss nach der Prüfung laufen")

    def test_schrittname_bleibt_alarmschluessel(self):
        # alert-on-failure.yml erkennt die Klasse „Einrichtung unvollständig“ am Namen.
        alarm = (REPO / ".github" / "workflows" / "alert-on-failure.yml").read_text(encoding="utf-8")
        self.assertIn("includes('Voraussetzungen prüfen')", alarm)
        self.assertIn("includes('Fristwarnung')", alarm)
        self._schritt("Voraussetzungen prüfen")
        self._schritt("Fristwarnung")

    def test_selbsttests_laufen_vorher(self):
        selbsttest = self._schritt("Selbsttest")
        self.assertIn("scripts/kv_backup.py --selftest", selbsttest["run"])
        self.assertIn("scripts/backup_einrichtung.py --selftest", selbsttest["run"])

    def test_fristwarnung_ist_letzter_schritt_nur_nach_erfolg(self):
        letzter = self.schritte[-1]
        self.assertIn("Fristwarnung", letzter.get("name", ""))
        self.assertIn("scripts/backup_einrichtung.py --fristen", letzter.get("run", ""))
        self.assertNotIn("if", letzter, "Fristwarnung darf nur nach erfolgreicher Sicherung laufen")

    def test_ablage_prueft_entwurf_und_raeumt_ab(self):
        ablage = self._schritt("Im privaten Backup-Repo ablegen")["run"]
        self.assertIn("--draft", ablage)
        self.assertIn("isDraft", ablage)
        self.assertIn('"$ENTWURF" != "true"', ablage)
        self.assertIn("aufraeumen", ablage)
        self.assertIn("--cleanup-tag", ablage)

    def test_kein_artefakt_im_kv_job(self):
        for schritt in self.schritte:
            self.assertNotIn("upload-artifact", str(schritt.get("uses", "")),
                             "KV-Daten nie als Artefakt (Audit M-11)")

    def test_rechte_nur_lesend(self):
        self.assertEqual(self.kv.get("permissions"), {"contents": "read", "actions": "read"})

    def test_umgebungsnamen_passen_zum_pruefer(self):
        erwartet = {
            "ZIEL_REPO": "${{ vars.BACKUP_REPO }}",
            "ZIEL_TOKEN": "${{ secrets.BACKUP_REPO_TOKEN }}",
            "PASSWORT": "${{ secrets.BACKUP_PASSPHRASE }}",
            "CF_API_TOKEN": "${{ secrets.CF_KV_BACKUP_TOKEN }}",
            "CF_ACCOUNT_ID": "${{ secrets.CLOUDFLARE_ACCOUNT_ID }}",
            "KV_NAMESPACE_ID": "${{ vars.KV_NAMESPACE_ID_ABO }}",
            "D1_DATABASE_ID": "${{ vars.D1_DATABASE_ID }}",
        }
        self.assertEqual({k: self.kv["env"].get(k) for k in erwartet}, erwartet)
        quelltext = (SCRIPTS / "backup_einrichtung.py").read_text(encoding="utf-8")
        for name in erwartet:
            self.assertIn(f'umgebung.get("{name}")', quelltext, f"Prüfer liest {name} nicht")

    def test_kein_verweis_auf_fehlendes_runbook(self):
        text = WORKFLOW.read_text(encoding="utf-8")
        self.assertNotIn("Umsetzungs-Runbook", text)
        self.assertIn(be.ANLEITUNG, text)


class AnleitungVertrag(unittest.TestCase):
    def setUp(self):
        self.assertTrue(ANLEITUNG.is_file(), f"{be.ANLEITUNG} fehlt")
        self.text = ANLEITUNG.read_text(encoding="utf-8")

    def _enthaelt(self, nadel: str) -> None:
        # Kurze Fehlermeldung statt der ganzen Anleitung im Testprotokoll.
        self.assertTrue(nadel in self.text, f"Anleitung nennt nicht: {nadel[:90]}")

    def test_nennt_jede_einstellung(self):
        for name in ("BACKUP_REPO", "BACKUP_REPO_TOKEN", "BACKUP_PASSPHRASE", "CF_KV_BACKUP_TOKEN",
                     "CLOUDFLARE_ACCOUNT_ID", "KV_NAMESPACE_ID_ABO", "D1_DATABASE_ID"):
            with self.subTest(name):
                self._enthaelt(f"`{name}`")

    def test_zitiert_die_links_des_pruefers_woertlich(self):
        quelle = "frank-hartung/franksfinanzcheck-blog"
        for link in (be.link_ziel_anlegen(), be.link_schreibzugang(),
                     be.link_cloudflare_lesezugang(False), be.link_cloudflare_lesezugang(True),
                     be.LINK_KV_NAMESPACES, be.link_einstellungen(quelle, "environments"),
                     be.link_einstellungen(quelle, "variables")):
            with self.subTest(link[:60]):
                self._enthaelt(link)

    def test_vorbelegung_ist_sicher(self):
        pat = be.link_schreibzugang()
        self.assertIn("expires_in=366", pat, "GitHub-Vorgabe wären 30 Tage")
        self.assertIn("contents=write", pat)
        self.assertNotRegex(pat, r"(administration|workflows|secrets)=", "nur Contents")
        self.assertIn("visibility=private", be.link_ziel_anlegen())
        self.assertIn("%22type%22%3A%22read%22", be.link_cloudflare_lesezugang(True))
        self.assertNotIn("edit", be.link_cloudflare_lesezugang(True), "Cloudflare-Zugang nur lesend")

    def test_kennt_alle_pruefpunkte_und_fallstricke(self):
        for kennung in ("E1", "E2", "E3", "E4", "E5", "E6", "E7", "E8"):
            self._enthaelt(f"| {kennung} |")
        for nadel in ("Only select repositories", "Required reviewers", "Zugänge erneuern",
                      "Fehlerbilder", "restore_drill.sh", "--remote"):
            self._enthaelt(nadel)

    def test_erst_absichern_dann_befuellen(self):
        # Wer der Anleitung folgt, beschränkt das Environment auf main, bevor
        # das erste Secret hineinkommt – sonst läge es offen für jeden Branch.
        schritte = re.findall(r"(?m)^### Schritt (\d) – (.+)$", self.text)
        self.assertEqual([n for n, _ in schritte], [str(i) for i in range(1, 8)], "Schritte 1–7 lückenlos")
        self.assertEqual(schritte[0][1], "Environment `backup` absichern (E8)")
        einrichtung = self.text.index("## Einrichtung Schritt für Schritt")
        erstes_secret = min(self.text.index(f"`{name}`", einrichtung)
                            for name in ("BACKUP_PASSPHRASE", "BACKUP_REPO_TOKEN", "CF_KV_BACKUP_TOKEN"))
        self.assertLess(self.text.index("### Schritt 1 – Environment"), erstes_secret)
        self.assertRegex(self.text, r"(?m)^\| 1 \| Environment `backup` absichern")
        self.assertRegex(self.text, r"(?m)^\| E8 \|.*\| Schritt 1 \|$")

    def test_leitfaden_und_npm_skript(self):
        # Der Leitfaden für Agenten nennt Prüfer und Grundsatz – sonst „heilt“
        # der nächste Agent das Rot mit continue-on-error.
        leitfaden = (REPO / "CLAUDE.md").read_text(encoding="utf-8")
        self.assertIn("scripts/backup_einrichtung.py", leitfaden)
        self.assertIn("Fail-closed bleibt", leitfaden)
        import json
        skripte = json.loads((REPO / "package.json").read_text(encoding="utf-8"))["scripts"]
        self.assertIn("backup_einrichtung.py --selftest", skripte.get("test:backup", ""))
        self.assertIn("scripts.tests.test_backup_einrichtung", skripte.get("test:backup", ""))


class RueckspielenVertrag(unittest.TestCase):
    """Wrangler 4 schreibt `kv … put` ohne `--remote` in die lokale Simulation
    und meldet Erfolg (isLocal, Vorgabe true; geprüft an 4.149.0)."""

    SCHREIBEND = re.compile(r"wrangler\s+kv[\s:]+(?:bulk|key)[\s:]+(?:put|delete)\b[^\n`]*")

    def test_jede_dokumentierte_kv_schreibzeile_traegt_remote(self):
        dateien = (list((REPO / "docs").glob("*.md")) + list(SCRIPTS.glob("*.py"))
                   + list(SCRIPTS.glob("*.sh")) + [REPO / "newsletter-worker" / "wrangler.toml"])
        treffer = 0
        for pfad in dateien:
            if not pfad.is_file():
                continue
            for zeile in self.SCHREIBEND.findall(pfad.read_text(encoding="utf-8", errors="replace")):
                treffer += 1
                with self.subTest(f"{pfad.relative_to(REPO)}: {zeile[:60]}"):
                    self.assertIn("--remote", zeile)
        self.assertGreaterEqual(treffer, 2, "Anleitung und kv_backup.py nennen das Rückspielen")

    def test_gepinntes_wrangler_ist_version_4(self):
        paket = (REPO / "tools" / "wrangler" / "package.json").read_text(encoding="utf-8")
        self.assertRegex(paket, r'"wrangler":\s*"4\.', "Neue Major-Version: --remote-Vorgabe neu prüfen")


class TransportVertrag(unittest.TestCase):
    """Ausgleich für die T6-Ausnahme in scripts/ki_transportweg.py: Der Prüfer
    spricht die Cloudflare-API an, aber nie ein Modell. Erlaubt sind genau die
    Verwaltungspfade der Einrichtungsprüfung."""

    def test_nur_verwaltungspfade_kein_modellaufruf(self):
        quelltext = (SCRIPTS / "backup_einrichtung.py").read_text(encoding="utf-8")
        self.assertIn('Path("scripts/backup_einrichtung.py")',
                      (SCRIPTS / "ki_transportweg.py").read_text(encoding="utf-8"))
        hosts = set(re.findall(r"https://([a-z0-9.-]+)", quelltext))
        self.assertLessEqual(hosts, {"api.github.com", "api.cloudflare.com", "github.com",
                                     "dash.cloudflare.com", "x.invalid"},
                             f"unerwartete Hosts: {hosts}")
        for verboten in ("/ai/run", "/ai/", "generativelanguage", "api.groq.com", "nvidia",
                         "pollinations", "llm_client", "/chat/completions"):
            self.assertFalse(verboten in quelltext, f"Modellbezug im Prüfer: {verboten}")
        cf_pfade = set(re.findall(r"\{CF_API\}(/[^\"'\s]*)", quelltext))
        erlaubt = {"/user/tokens/verify", "/accounts/{konto}/tokens/verify",
                   "/accounts/{konto}/storage/kv/namespaces/{ns}", "/accounts/{konto}/d1/database/{db}"}
        self.assertEqual(cf_pfade, erlaubt, f"Cloudflare-Pfade weichen ab: {cf_pfade ^ erlaubt}")


class FrischwacheVertrag(unittest.TestCase):
    """Operative RPO-Wache (Highend 24.10.2026): Der Konfigurations-Check
    (E1–E8) und die Fristwarnung dürfen nicht mit \"jüngst gelaufen\"
    verwechselt werden. Diese Wache schließt die operative Lücke – ein
    ausgesetzter nächtlicher Lauf ohne ablaufenden Token bliebe sonst still."""

    def test_workflow_existiert_und_laueft_taeglich(self):
        wf = REPO / ".github" / "workflows" / "backup-frischwache.yml"
        self.assertTrue(wf.is_file(), "backup-frischwache.yml fehlt – RPO wäre unbewacht")
        data = _frischwache_workflow()
        # PyYAML 1.1: `on` wird als bool True geparst – GitHub meint den Trigger.
        on = data.get("on", data.get(True, {}))
        self.assertIn("schedule", on, "Frischwache muss täglich laufen (schedule)")
        crons = [e.get("cron", "") for e in on["schedule"]]
        self.assertTrue(any("13" in c for c in crons), f"Frischwache soll nach dem 03:00-Backup laufen (13:00 UTC): {crons}")
        job = data["jobs"]["frischwache"]
        self.assertEqual(job.get("environment"), "backup", "Secrets liegen im Environment backup")
        schritte = {s.get("name", ""): s for s in job.get("steps", [])}
        self.assertIn("Selbsttest (Wache prueft sich selbst – fail-closed)", schritte)
        self.assertIn("Frische messen (beide Release-Familien, Entwuerfe eingeschlossen)", schritte)
        # Fail-closed: kein continue-on-error darf die RPO-Wache still grün halten.
        for s in job["steps"]:
            self.assertNotIn("continue-on-error", str(s), "RPO-Wache darf nicht mit continue-on-error still grün werden")

    def test_ueberwacht_beide_familien_mit_gelben_und_roten_grenzen(self):
        wf_text = (REPO / ".github" / "workflows" / "backup-frischwache.yml").read_text(encoding="utf-8")
        self.assertIn("backup_freshness_guard.py", wf_text)
        self.assertIn("BACKUP_REPO", wf_text)
        self.assertIn("GH_TOKEN", wf_text)
        guard = (SCRIPTS / "backup_freshness_guard.py").read_text(encoding="utf-8")
        # Grenzen müssen zu ANLEITUNG und SLAs passen (36/52), sonst ist die Anleitung falsch.
        self.assertIn("MAX_ALTER_GELB_H = 36", guard)
        self.assertIn("MAX_ALTER_ROT_H = 52", guard)
        anleitung = ANLEITUNG.read_text(encoding="utf-8")
        self.assertIn("52 h", anleitung)
        self.assertIn("36 h", anleitung)
        self.assertIn("backup-frischwache.yml", anleitung)

    def test_alerting_kennt_die_frischklasse(self):
        alert = (REPO / ".github" / "workflows" / "alert-on-failure.yml").read_text(encoding="utf-8")
        self.assertIn("Backup-Frischwache", alert)
        self.assertIn("backup-frisch", alert)
        self.assertIn("RPO", alert)


class WizardVertrag(unittest.TestCase):
    """Der Einrichtungs-Wizard ist der geprüfte Schnellweg durch die einzige
    verbliebene Inhaber-Aufgabe (#761). Er darf vom npm-Kurzbefehl und der
    Anleitung nicht abweichen und muss in CI (kein Mensch, kein TTY) hart
    ablehnen – Geheimnisse gehören nicht in automatisierte Läufe."""

    WIZARD = SCRIPTS / "backup_einrichten_wizard.sh"

    def setUp(self):
        self.assertTrue(self.WIZARD.is_file(), "backup_einrichten_wizard.sh fehlt")
        self.text = self.WIZARD.read_text(encoding="utf-8")

    def test_bash_syntax(self):
        proc = subprocess.run(["bash", "-n", str(self.WIZARD)],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, "Wizard-Syntaxfehler: " + proc.stderr)

    def test_lehnt_in_ci_ab(self):
        # Kein /dev/tty, GITHUB_ACTIONS gesetzt: Exit 1, kein Schreibversuch.
        proc = subprocess.run(["bash", str(self.WIZARD), "--check"],
                              capture_output=True, text=True,
                              env={**__import__("os").environ, "GITHUB_ACTIONS": "true"})
        self.assertEqual(proc.returncode, 1)
        self.assertIn("CI", proc.stderr + proc.stdout)

    def test_kennt_check_modus_und_alle_sieben_einstellungen(self):
        self.assertIn("--check", self.text)
        for name in ("BACKUP_REPO", "BACKUP_REPO_TOKEN", "BACKUP_PASSPHRASE",
                     "CF_KV_BACKUP_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
                     "KV_NAMESPACE_ID_ABO", "D1_DATABASE_ID"):
            with self.subTest(name):
                self.assertIn(name, self.text)
        # Reihenfolge der Anleitung: erst E8, dann die Secrets.
        self.assertLess(self.text.index("pruefe_e8"),
                        self.text.index('gh secret set BACKUP_PASSPHRASE'),
                        "Erst absichern (E8), dann das erste Secret befüllen")
        self.assertIn(be.ANLEITUNG, self.text)

    def test_npm_kurzbefehle_zeigen_auf_den_wizard(self):
        import json
        skripte = json.loads((REPO / "package.json").read_text(encoding="utf-8"))["scripts"]
        self.assertEqual(skripte.get("backup:einrichten"),
                         "bash scripts/backup_einrichten_wizard.sh")
        self.assertEqual(skripte.get("backup:status"),
                         "bash scripts/backup_einrichten_wizard.sh --check")
        # Die Anleitung muss dieselben Kurzbefehle nennen (eine Einstiegsstelle).
        anleitung = ANLEITUNG.read_text(encoding="utf-8")
        self.assertIn("npm run backup:einrichten", anleitung)
        self.assertIn("npm run backup:status", anleitung)


class NamensVertrag(unittest.TestCase):
    """Kein Name im Prüfer darf unter die CodeQL-Heuristik fallen (Alert-Klasse #78)."""

    def test_keine_sensiblen_namen(self):
        spec = importlib.util.spec_from_file_location(
            "_namensvertrag", SCRIPTS / "tests" / "test_zugangs_namensvertrag.py")
        modul = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(modul)
        baum = ast.parse((SCRIPTS / "backup_einrichtung.py").read_text(encoding="utf-8"))
        namen = set()
        for knoten in ast.walk(baum):
            if isinstance(knoten, (ast.FunctionDef, ast.ClassDef)):
                namen.add(knoten.name)
            elif isinstance(knoten, ast.Name) and isinstance(knoten.ctx, ast.Store):
                namen.add(knoten.id)
            elif isinstance(knoten, ast.arg):
                namen.add(knoten.arg)
            elif isinstance(knoten, ast.Attribute) and isinstance(knoten.ctx, ast.Store):
                namen.add(knoten.attr)
        sensibel = sorted(n for n in namen if modul.codeql_klassifikation(n))
        self.assertEqual(sensibel, [], f"CodeQL stuft diese Namen als sensibel ein: {sensibel}")
        self.assertGreater(len(namen), 50, "Namenssammlung blind")


if __name__ == "__main__":
    unittest.main()
