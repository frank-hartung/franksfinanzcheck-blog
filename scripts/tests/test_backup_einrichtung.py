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

def leitfaden_text() -> str:
    """Der Leitfaden der Agenten ist seit dem Umbau vom 01.11.2026 Kern **plus**
    `ff-*`-Skills (Progressive Disclosure, `docs/ANLEITUNG-SKILLS.md`). Wer nur
    `CLAUDE.md` liest, prüft den alten Ablageort und meldet eine Regel als
    verschwunden, die lediglich umgezogen ist – derselbe Fehler, den K3 auf der
    Skill-Seite verbietet.
    """
    ordner = REPO / ".claude" / "skills"
    teile = [(REPO / "CLAUDE.md").read_text(encoding="utf-8")]
    for muster in ("ff-*/SKILL.md", "ff-*/references/*.md"):
        for pfad in sorted(ordner.glob(muster)):
            teile.append(pfad.read_text(encoding="utf-8"))
    return "\n".join(teile)

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
                if "/deployment-branch-policies" in url:
                    return 200, {}, {"branch_policies": [{"name": n, "type": "branch"} for n in branches]}, ""
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

    def test_e8_verwirft_zusaetzliche_regel_auf_folgeseite(self):
        basis = "https://api.github.com/repos/frank-hartung/franksfinanzcheck-blog/environments/backup"
        folgeseite = basis + "/deployment-branch-policies?per_page=100&page=2"
        environment = {"protection_rules": [], "deployment_branch_policy": {
            "protected_branches": False, "custom_branch_policies": True}}

        def antwort(url, _kopf):
            if url == basis:
                return 200, {}, environment, ""
            if url == folgeseite:
                return 200, {}, {"branch_policies": [{"name": "arena/*", "type": "branch"}]}, ""
            if "/deployment-branch-policies" in url:
                return 200, {"link": f'<{folgeseite}>; rel="next", <{folgeseite}>; rel="last"'}, {
                    "branch_policies": [{"name": "main", "type": "branch"}]}, ""
            self.fail(f"unerwarteter API-Aufruf: {url}")

        http = _OhneNetz(antwort)
        be.HTTP = http
        lage = be.pruefen({"GITHUB_REPOSITORY": "frank-hartung/franksfinanzcheck-blog",
                           "CF_ACCOUNT_ID": "a" * 32}, JETZT)
        self.assertTrue(lage.environment_offen)
        self.assertEqual(lage.stufe_von("E8"), "warnung")
        self.assertIn(folgeseite, http.aufrufe, "E8 muss jede Branch-Policy-Seite lesen")

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

    def test_secret_jobs_laufen_nur_auf_main(self):
        """E8 darf nicht die einzige Schranke für Environment-Secrets sein.

        `workflow_dispatch` lässt sich in GitHub auf einem beliebigen Ref
        starten. Ein Job-Level-if wird vor der Environment-Auswertung geprüft
        und verhindert deshalb, dass ein geänderter Workflow auf einem
        Feature-Branch überhaupt Geheimnisse erhält.
        """
        erwartet = "${{ github.ref == 'refs/heads/main' }}"
        for name in ("backup", "kv-backup"):
            with self.subTest(name):
                self.assertEqual(self.wf["jobs"][name].get("if"), erwartet)
        self.assertEqual(self.wf["jobs"]["backup"].get("permissions"), {"contents": "read"})

    def test_offsite_ziel_verlangt_dedizierten_token(self):
        backup_schritte = self.wf["jobs"]["backup"]["steps"]
        treffer = [s for s in backup_schritte if "Dauerhaftes Ziel" in s.get("name", "")]
        self.assertEqual(len(treffer), 1, "der Repo-Job braucht genau einen Offsite-Ziel-Schritt")
        ziel = treffer[0]["run"]
        self.assertIn('if [ -z "${ZIEL_TOKEN:-}" ]', ziel)
        self.assertIn('TOKEN="$ZIEL_TOKEN"', ziel)
        self.assertNotIn('TOKEN="${ZIEL_TOKEN:-$GH_TOKEN}"', ziel)
        self.assertNotIn("GH_TOKEN", self.wf["jobs"]["backup"].get("env", {}),
                         "der Repo-Job darf kein Quell-Token als Offsite-Fallback erhalten")

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
        # der nächste Agent das Rot mit continue-on-error. Gelesen wird der
        # ganze Leitfaden (Kern + `ff-*`-Skills), nicht nur der Kern: seit dem
        # Umbau vom 01.11.2026 liegt der Grundsatz in
        # `ff-ausliefern/references/bestand-backup-merge.md`.
        leitfaden = leitfaden_text()
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
        self.assertEqual(job.get("if"), "${{ github.ref == 'refs/heads/main' }}",
                         "workflow_dispatch darf die Frische-Secrets nur auf main erhalten")
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


class RueckwegVertrag(unittest.TestCase):
    """WF-9E5A / #923 (01.11.2026): Ein Drill, der nichts prüft, ist grün.

    Befund: `restore_drill.sh --nur-git --nur-kv` endete mit Exit 0 und dem
    Satz „RESTORE-DRILL BESTANDEN“, ohne eine einzige Datei angesehen zu haben.
    Genau diese Zeile wäre im Betrieb als Wiederherstellungs-Nachweis zitiert
    worden. Dazu kam die Frischwache-Kurzprüfung mit `if: always()`: Sie lief
    auch dann, wenn der Job davor schon rot war – der Rückweg-Nachweis hing am
    Ausgang einer anderen Messung.
    """

    DRILL = SCRIPTS / "restore_drill.sh"

    @staticmethod
    def _werkzeuge() -> bool:
        import shutil
        return all(shutil.which(w) for w in ("bash", "git", "openssl"))

    def test_ohne_gepruefte_familie_kein_bestanden(self):
        if not self._werkzeuge():
            self.skipTest("bash/git/openssl fehlen lokal (CI hat sie)")
        lauf = subprocess.run(["bash", str(self.DRILL), "--repo", "probe/kein-zugriff",
                               "--nur-git", "--nur-kv"],
                              capture_output=True, text=True, timeout=120)
        self.assertEqual(lauf.returncode, 2,
                         "ein Drill ohne geprüfte Familie darf NICHT bestanden melden:\n"
                         + lauf.stdout + lauf.stderr)
        self.assertNotIn("BESTANDEN", lauf.stdout)
        self.assertIn("NICHTS", lauf.stderr)

    def test_gesunde_sicherung_wird_mit_nachweis_bestanden(self):
        if not self._werkzeuge():
            self.skipTest("bash/git/openssl fehlen lokal (CI hat sie)")
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as ordner:
            q = Path(ordner)
            quelle = q / "quelle"
            for unter in ("content/posts", "content/impressum", "content/datenschutz"):
                (quelle / unter).mkdir(parents=True)
            for nummer in range(21):
                (quelle / "content" / "posts" / f"p{nummer}.md").write_text("x\n", encoding="utf-8")
            (quelle / "content" / "impressum" / "index.md").write_text("a\n", encoding="utf-8")
            (quelle / "content" / "datenschutz" / "index.md").write_text("b\n", encoding="utf-8")
            (quelle / "hugo.toml").write_text("x\n", encoding="utf-8")
            # HEAD muss auf einem Branch liegen: `git clone` eines Bundles mit
            # losem HEAD (detached) ergibt einen leeren Arbeitsbaum.
            for befehl in (["git", "init", "-q", "-b", "main"],
                           ["git", "-c", "user.email=t@example.invalid",
                            "-c", "user.name=Test", "add", "-A"],
                           ["git", "-c", "user.email=t@example.invalid",
                            "-c", "user.name=Test", "commit", "-qm", "i"]):
                subprocess.run(befehl, cwd=quelle, check=True, capture_output=True)
            subprocess.run(["git", "bundle", "create", str(q / "sicherung.bundle"), "main"],
                           cwd=quelle, check=True, capture_output=True)
            passphrase = "kein-echtes-geheimnis-nur-probe-1234"
            subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-salt",
                            "-in", str(q / "sicherung.bundle"), "-out", str(q / "sicherung.bundle.enc"),
                            "-pass", f"pass:{passphrase}"], check=True, capture_output=True)
            (q / "kv.json").write_text(json.dumps({
                "version": 1, "kv": {"namespace": "x" * 32, "anzahl": 1,
                                     "werte": {"abo:probe@example.invalid": json.dumps({"status": "active"})},
                                     "ablauf": {}}}), encoding="utf-8")
            subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "600000", "-salt",
                            "-in", str(q / "kv.json"), "-out", str(q / "kv.json.enc"),
                            "-pass", f"pass:{passphrase}"], check=True, capture_output=True)
            umgebung = {**__import__("os").environ, "BACKUP_PASSPHRASE": passphrase}
            lauf = subprocess.run(["bash", str(self.DRILL), "--bundle", str(q / "sicherung.bundle.enc"),
                                   "--kv", str(q / "kv.json.enc")],
                                  capture_output=True, text=True, timeout=180, env=umgebung)
            self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
            self.assertIn("RESTORE-DRILL BESTANDEN", lauf.stdout)
            # Der Abschluss nennt, WAS geprüft wurde – keine pauschale Zusage.
            self.assertIn("geprüft: Abonnenten (KV), Repository (Git-Bundle", lauf.stdout)

    def test_falsche_passphrase_bleibt_rot(self):
        if not self._werkzeuge():
            self.skipTest("bash/git/openssl fehlen lokal (CI hat sie)")
        import tempfile
        with tempfile.TemporaryDirectory() as ordner:
            datei = Path(ordner) / "x.bundle.enc"
            datei.write_bytes(b"kein gueltiger schluesseltext" * 10)
            lauf = subprocess.run(["bash", str(self.DRILL), "--bundle", str(datei), "--nur-git"],
                                  capture_output=True, text=True, timeout=120,
                                  env={**__import__("os").environ, "BACKUP_PASSPHRASE": "falsch-falsch-123"})
            self.assertEqual(lauf.returncode, 1, lauf.stdout + lauf.stderr)
            self.assertIn("nicht entschlüsselbar", lauf.stderr)
            self.assertNotIn("BESTANDEN", lauf.stdout)


class FrischwacheKommandozeile(unittest.TestCase):
    """#923: `--repo` OHNE Positionsargument wurde verworfen.

    Anleitung und `npm run backup:frische` rufen genau so auf. Ergebnis war
    „Kein gültiges Backup-Repo angegeben“ – ein Fehlalarm über eine Eingabe,
    die da war. Im Workflow fiel es nicht auf (dort greift `BACKUP_REPO`).
    """

    SKRIPT = SCRIPTS / "backup_freshness_guard.py"

    def _lauf(self, argumente: list[str]) -> subprocess.CompletedProcess:
        import os
        umgebung = {k: v for k, v in os.environ.items()
                    if k not in ("GH_TOKEN", "GITHUB_TOKEN", "BACKUP_REPO",
                                 "ZIEL_REPO", "BACKUP_REPO_TOKEN", "ZIEL_TOKEN")}
        return subprocess.run([sys.executable, str(self.SKRIPT), *argumente],
                              capture_output=True, text=True, timeout=120, env=umgebung)

    def test_repo_flag_ohne_positionsargument_kommt_an(self):
        lauf = self._lauf(["--repo", "frank-hartung/franksfinanzcheck-backup", "--json"])
        self.assertNotIn("Kein gültiges Backup-Repo angegeben", lauf.stdout,
                         "--repo wurde erneut verworfen (Fehlalarm #923)")
        # Ohne Token bleibt es fail-closed – aber aus dem richtigen Grund.
        self.assertEqual(lauf.returncode, 1)
        self.assertIn("Kein Token angegeben", lauf.stdout)
        import json
        daten = json.loads(lauf.stdout)
        self.assertEqual(daten["repo"], "frank-hartung/franksfinanzcheck-backup")

    def test_positionsargument_bleibt_erlaubt(self):
        lauf = self._lauf(["frank-hartung/franksfinanzcheck-backup", "--json"])
        self.assertNotIn("Kein gültiges Backup-Repo angegeben", lauf.stdout)

    def test_ohne_jede_angabe_bleibt_es_fail_closed(self):
        lauf = self._lauf(["--json"])
        self.assertEqual(lauf.returncode, 1)
        self.assertIn("Kein gültiges Backup-Repo angegeben", lauf.stdout)


class WizardVertrag(unittest.TestCase):
    """Der Einrichtungs-Wizard ist der geprüfte Schnellweg durch die einzige
    verbliebene Inhaber-Aufgabe (#761). Er darf vom npm-Kurzbefehl und der
    Anleitung nicht abweichen und muss in CI (kein Mensch, kein TTY) hart
    ablehnen – Geheimnisse gehören nicht in automatisierte Läufe."""

    WIZARD = SCRIPTS / "backup_einrichten_wizard.sh"

    def setUp(self):
        self.assertTrue(self.WIZARD.is_file(), "backup_einrichten_wizard.sh fehlt")
        self.text = self.WIZARD.read_text(encoding="utf-8")

    def _funktion(self, name: str) -> str:
        """Isoliert eine Top-Level-Bash-Funktion für Tests mit gemocktem `gh`."""
        start = re.search(rf"(?m)^{re.escape(name)}\(\) \{{[^\n]*\n", self.text)
        self.assertIsNotNone(start, f"Bash-Funktion {name} fehlt")
        ende = re.search(r"(?m)^\}", self.text[start.end():])
        self.assertIsNotNone(ende, f"Bash-Funktion {name} ist nicht geschlossen")
        return self.text[start.start():start.end() + ende.start() + 1]

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

    def _e8_lauf(self, environment: dict, policies: dict | None = None,
                  environment_fail: bool = False, policies_fail: bool = False) -> int:
        funktionen = "\n\n".join(self._funktion(name) for name in
                                     ("branch_regel_status", "branch_regel_namen", "pruefe_e8"))
        harness = r'''
set -o pipefail
QUELLE="frank-hartung/franksfinanzcheck-blog"
UMGEBUNG="backup"
EINSTELLUNGEN_UMGEBUNGEN="https://example.invalid/settings"
gh() {
  case "$*" in
    *"/deployment-branch-policies"*)
      [ "${WIZARD_POLICIES_FAIL:-0}" != "1" ] || return 1
      printf '%s' "$WIZARD_POLICIES_JSON" | python3 -c '
import json, sys
for p in json.load(sys.stdin).get("branch_policies", []):
    print("{}\t{}".format(p.get("name", ""), p.get("type", "unbekannt")))
'
      ;;
    *)
      [ "${WIZARD_ENV_FAIL:-0}" != "1" ] || return 1
      printf '%s' "$WIZARD_ENV_JSON"
      ;;
  esac
}
ok() { :; }
offen() { :; }
hinweis() { :; }
link() { :; }
''' + funktionen + "\npruefe_e8\n"
        umgebung = {
            **__import__("os").environ,
            "WIZARD_ENV_JSON": __import__("json").dumps(environment),
            "WIZARD_POLICIES_JSON": __import__("json").dumps(policies or {"branch_policies": []}),
            "WIZARD_ENV_FAIL": "1" if environment_fail else "0",
            "WIZARD_POLICIES_FAIL": "1" if policies_fail else "0",
        }
        proc = subprocess.run(["bash", "-c", harness], capture_output=True, text=True, env=umgebung)
        self.assertEqual(proc.stderr, "", proc.stderr)
        return proc.returncode

    def test_environment_policy_uses_supported_rest_endpoint(self):
        import json
        import os
        import tempfile

        funktion = self._funktion("umgebung_anlegen")
        with tempfile.TemporaryDirectory() as ordner:
            args_datei, body_datei = Path(ordner) / "args", Path(ordner) / "body"
            harness = '''set -euo pipefail
QUELLE="frank-hartung/franksfinanzcheck-blog"
UMGEBUNG="backup"
gh() { echo "$*" > "$GH_ARGS_FILE"; cat > "$GH_BODY_FILE"; }
''' + funktion + "\numgebung_anlegen\n"
            umgebung = {**os.environ, "GH_ARGS_FILE": str(args_datei), "GH_BODY_FILE": str(body_datei)}
            proc = subprocess.run(["bash", "-c", harness], capture_output=True, text=True, env=umgebung)
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            self.assertIn("-X PUT repos/frank-hartung/franksfinanzcheck-blog/environments/backup",
                          args_datei.read_text(encoding="utf-8"))
            self.assertEqual(json.loads(body_datei.read_text(encoding="utf-8")), {
                "deployment_branch_policy": {"protected_branches": False, "custom_branch_policies": True}
            })

    def test_branch_policy_replacement_uses_supported_rest_operations(self):
        import json
        import os
        import tempfile

        funktion = self._funktion("branch_regel_setzen")
        basis = "repos/frank-hartung/franksfinanzcheck-blog/environments/backup/deployment-branch-policies"
        cases = (
            ("create before cleanup", [
                {"id": 101, "name": "arena/*", "type": "branch"},
                {"id": 202, "name": "main", "type": "tag"},
            ], True),
            ("preserve main rule", [
                {"id": 111, "name": "main", "type": "branch"},
                {"id": 202, "name": "arena/*", "type": "branch"},
            ], False),
        )
        for name, policies, post_needed in cases:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as ordner:
                log_datei, body_datei = Path(ordner) / "calls", Path(ordner) / "body"
                harness = r'''
set -euo pipefail
QUELLE="frank-hartung/franksfinanzcheck-blog"
UMGEBUNG="backup"
gh() {
  echo "$*" >> "$GH_LOG_FILE"
  case "$*" in
    *--paginate*)
      printf '%s' "$GH_POLICY_JSON" | python3 -c '
import json, sys
for p in json.load(sys.stdin).get("branch_policies", []):
    print("{}\t{}\t{}".format(p.get("id", ""), p.get("name", ""), p.get("type", "")))
'
      ;;
    *--input*) cat > "$GH_BODY_FILE"; echo 303 ;;
    *"-X DELETE"*) ;;
    *) echo "unexpected gh operation" >&2; return 1 ;;
  esac
}
''' + funktion + "\nbranch_regel_setzen\n"
                umgebung = {
                    **os.environ,
                    "GH_LOG_FILE": str(log_datei),
                    "GH_BODY_FILE": str(body_datei),
                    "GH_POLICY_JSON": json.dumps({"branch_policies": policies}),
                }
                proc = subprocess.run(["bash", "-c", harness], capture_output=True, text=True, env=umgebung)
                self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
                calls = log_datei.read_text(encoding="utf-8").splitlines()
                self.assertIn("--paginate --jq .branch_policies[]?", calls[0])
                self.assertIn(basis + "?per_page=100", calls[0])
                if post_needed:
                    self.assertEqual(len(calls), 4, calls)
                    self.assertIn("-X POST " + basis, calls[1])
                    self.assertIn("-X DELETE " + basis + "/101", calls[2])
                    self.assertIn("-X DELETE " + basis + "/202", calls[3])
                    self.assertEqual(json.loads(body_datei.read_text(encoding="utf-8")),
                                     {"name": "main", "type": "branch"})
                else:
                    self.assertEqual(len(calls), 2, calls)
                    self.assertIn("-X DELETE " + basis + "/202", calls[1])
                    self.assertNotIn("-X DELETE " + basis + "/111", "\n".join(calls))
                    self.assertFalse(any("-X POST" in call for call in calls), calls)

    def test_branch_policy_api_failure_stops_safely(self):
        import os
        import tempfile

        funktion = self._funktion("branch_regel_setzen")
        for failure in ("list", "post", "delete"):
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as ordner:
                log_datei = Path(ordner) / "calls"
                harness = r'''
set -u
QUELLE="frank-hartung/franksfinanzcheck-blog"
UMGEBUNG="backup"
gh() {
  echo "$*" >> "$GH_LOG_FILE"
  case "$*" in
    *--paginate*)
      [ "$FAIL_AT" != "list" ] || return 1
      printf '{"branch_policies":[{"id":101,"name":"arena/*","type":"branch"}]}' | python3 -c '
import json, sys
for p in json.load(sys.stdin).get("branch_policies", []):
    print("{}\t{}\t{}".format(p.get("id", ""), p.get("name", ""), p.get("type", "")))
'
      ;;
    *"-X DELETE"*) [ "$FAIL_AT" != "delete" ] || return 1 ;;
    *--input*)
      [ "$FAIL_AT" != "post" ] || return 1
      cat >/dev/null
      echo 303
      ;;
    *) echo "unexpected gh operation" >&2; return 1 ;;
  esac
}
''' + funktion + "\nbranch_regel_setzen\n"
                umgebung = {**os.environ, "GH_LOG_FILE": str(log_datei), "FAIL_AT": failure}
                proc = subprocess.run(["bash", "-c", harness], capture_output=True, text=True, env=umgebung)
                self.assertEqual(proc.returncode, 1, proc.stdout + proc.stderr)
                calls = log_datei.read_text(encoding="utf-8").splitlines()
                posts = [i for i, call in enumerate(calls) if "-X POST" in call]
                deletes = [i for i, call in enumerate(calls) if "-X DELETE" in call]
                if failure == "list":
                    self.assertFalse(posts, calls)
                    self.assertFalse(deletes, calls)
                elif failure == "post":
                    self.assertEqual(len(posts), 1, calls)
                    self.assertFalse(deletes, calls)
                else:
                    self.assertEqual(len(posts), 1, calls)
                    self.assertEqual(len(deletes), 1, calls)
                    self.assertLess(posts[0], deletes[0], calls)

    def test_e8_gate_fails_closed_unless_exact_main_branch_is_live(self):
        readback = self._funktion("branch_regel_namen")
        self.assertIn("gh api --paginate --jq", readback,
                      "der E8-Nachweis muss auch nachgelagerte Seiten vollständig lesen")
        self.assertIn("?per_page=100", readback)
        policy_main = {"protected_branches": False, "custom_branch_policies": True}
        selected_main = {"branch_policies": [{"name": "main", "type": "branch"}]}
        environment = {"protection_rules": [], "deployment_branch_policy": policy_main}
        self.assertEqual(self._e8_lauf(environment, selected_main), 0)

        cases = (
            ("alle Branches", {"protection_rules": [], "deployment_branch_policy": None}, None, False, False),
            ("protected branches", {"protection_rules": [], "deployment_branch_policy":
                                    {"protected_branches": True, "custom_branch_policies": False}}, None, False, False),
            ("unvollständige Policy", {"protection_rules": [], "deployment_branch_policy":
                                       {"custom_branch_policies": True}}, selected_main, False, False),
            ("keine explizite Auswahl", {"protection_rules": [], "deployment_branch_policy":
                                         {"protected_branches": False, "custom_branch_policies": False}}, None, False, False),
            ("zusätzlicher Branch", environment, {"branch_policies": [
                {"name": "main", "type": "branch"}, {"name": "arena/*", "type": "branch"}]}, False, False),
            ("Tag statt Branch", environment, {"branch_policies": [{"name": "main", "type": "tag"}]}, False, False),
            ("Pflicht-Freigabe", {"protection_rules": [{"type": "required_reviewers"}],
                                  "deployment_branch_policy": policy_main}, selected_main, False, False),
            ("Protection Rules nicht lesbar", {"deployment_branch_policy": policy_main}, selected_main, False, False),
            ("Environment nicht lesbar", environment, selected_main, True, False),
            ("Branch-Liste nicht lesbar", environment, selected_main, False, True),
        )
        for name, env_daten, policy_daten, env_fail, policy_fail in cases:
            with self.subTest(name):
                self.assertEqual(self._e8_lauf(env_daten, policy_daten, env_fail, policy_fail), 1,
                                 f"E8 muss bei {name} vor Secrets stoppen")

    def test_setup_rechecks_e8_after_manual_claim_before_any_secret(self):
        abschnitt = self.text.split("# ---- Schritt 1 (E8): Environment absichern", 1)[1]
        abschnitt = abschnitt.split("# ---- Schritt 2 (E1): Privates Backup-Repository", 1)[0]
        pruefungen = [m.start() for m in re.finditer(r"if ! pruefe_e8; then", abschnitt)]
        self.assertEqual(len(pruefungen), 3,
                         "E8 muss vor Änderungen, nach automatischem Setup und nach manueller Bestätigung live geprüft werden")
        self.assertLess(pruefungen[0], abschnitt.index("umgebung_anlegen"))
        self.assertLess(abschnitt.index("branch_regel_setzen"), pruefungen[1])
        self.assertLess(pruefungen[1], abschnitt.index("Erledigt?"))
        self.assertLess(abschnitt.index("Erledigt?"), pruefungen[2])
        self.assertIn("reviewer|unlesbar", abschnitt,
                      "bei Required Reviewers oder unbekanntem Zustand nicht blind mutieren")
        self.assertIn("Erledigt?", abschnitt)
        self.assertIn("weiterhin nicht als main-only bestätigt", abschnitt)
        self.assertNotIn("gh secret set", abschnitt)

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
