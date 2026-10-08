"""Regressionstests für die Manifest-Wache (WF-7B6B / #654, 08.10.2026).

Warum diese Tests existieren
----------------------------
Am 08.10.2026 stand ein Merge-Rest in package.json: ungültiges JSON. `npm ci`
brach in Sekunde 1 ab, der E2E-Lauf und danach der Produktions-Deploy wurden
rot, und die Meldung riet zu API-Keys. Diese Tests halten fünf Zusagen fest:

1) **Die Wache misst richtig** – ihr eingebauter Sabotage-Selbsttest läuft grün.
2) **Der Vorfall wird erkannt** – ein echter Git-Commit mit dem kaputten
   Abhängigkeitsblock muss J1 in genau der Zeile melden, an der npm bricht.
3) **Der Bestand ist sauber** – das ausgelieferte Repo besteht die Wache.
4) **Die Verdrahtung bleibt** – jeder Workflow, der `npm ci` ausführt, ruft die
   Wache vorher auf (sonst läuft der Install ungeprüft).
5) **Die Regel ist eingetragen** – Governance-Vertrag (C6) und npm-Skripte kennen
   die Wache, und der Alarm nennt bei Install-Fehlern die Manifest-Ursache.

Alle Tests laufen ohne Netz, ohne Hugo, ohne Browser und ohne Wanduhr.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - CI installiert pyyaml
    yaml = None

ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"

sys.path.insert(0, str(ROOT / "scripts"))
import manifest_guard as mg  # noqa: E402


def _codes(befunde, schwere=None):
    return {b.code for b in befunde if schwere is None or b.schwere == schwere}


class SelbsttestTests(unittest.TestCase):
    def test_selbsttest_ist_gruen(self):
        self.assertEqual(mg.selftest(), [], "Die Wache hat ihre eigenen Sabotageproben nicht gefangen.")

    def test_gegenprobe_bleibt_gruen(self):
        befunde = mg.pruefe_manifeste({mg.MANIFEST: mg.GUT_MANIFEST, mg.LOCK: mg.GUT_LOCK})
        self.assertEqual(befunde, [])

    def test_cli_selftest_exit_null(self):
        self.assertEqual(mg.main(["--selftest"]), 0)


class VorfallTests(unittest.TestCase):
    """Der Vorfall #654: fehlendes Komma + doppelter Schlüssel im Abhängigkeitsblock."""

    def test_fehlendes_komma_wird_in_der_kernzeile_gemeldet(self):
        befunde = mg.pruefe_manifeste({mg.MANIFEST: mg.VORFALL_MANIFEST, mg.LOCK: mg.GUT_LOCK})
        j1 = [b for b in befunde if b.code == "J1"]
        self.assertEqual(len(j1), 1)
        self.assertEqual(j1[0].datei, mg.MANIFEST)
        self.assertEqual(j1[0].zeile, mg._zeile_des_befunds())
        self.assertIn("Komma", j1[0].hinweis)

    def test_vorfall_als_echter_git_commit(self):
        """Der kaputte Stand wird über `--ref` nachgespielt – wie im echten Vorfall."""
        if shutil.which("git") is None:
            self.skipTest("git nicht verfügbar")
        gut = (ROOT / mg.MANIFEST).read_text(encoding="utf-8")
        kaputt_block = (
            '"dependencies": {\n'
            '    "pagefind": "1.5.2"\n'
            '    "lighthouse": "13.5.0",\n'
            '    "pagefind": "^1.5.2"\n'
            '  }')
        assert '"dependencies": {\n    "pagefind": "1.5.2"\n  }' in gut, \
            "Anker im aktuellen package.json fehlt – Testfixture anpassen"
        kaputt = gut.replace('"dependencies": {\n    "pagefind": "1.5.2"\n  }', kaputt_block, 1)
        erwartete_zeile = kaputt.splitlines().index('    "lighthouse": "13.5.0",') + 1

        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid",
                       GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@example.invalid")

            def git(*args):
                return subprocess.run(["git", "-C", str(repo), *args], check=True,
                                      capture_output=True, text=True, env=env).stdout.strip()

            git("init", "-q")
            lock = (ROOT / mg.LOCK).read_text(encoding="utf-8")
            (repo / mg.MANIFEST).write_text(gut, encoding="utf-8")
            (repo / mg.LOCK).write_text(lock, encoding="utf-8")
            git("add", "-A")
            git("commit", "-q", "-m", "gut")
            gut_sha = git("rev-parse", "HEAD")
            (repo / mg.MANIFEST).write_text(kaputt, encoding="utf-8")
            git("add", "-A")
            git("commit", "-q", "-m", "merge-rest")
            kaputt_sha = git("rev-parse", "HEAD")

            dateien_kaputt = mg.dateien_aus_ref(repo, kaputt_sha)
            befunde_kaputt = mg.pruefe_manifeste(dateien_kaputt)
            j1 = [b for b in befunde_kaputt if b.code == "J1" and b.schwere == mg.FEHLER]
            self.assertEqual(len(j1), 1, befunde_kaputt)
            self.assertEqual(j1[0].datei, mg.MANIFEST)
            self.assertEqual(j1[0].zeile, erwartete_zeile)

            befunde_gut = mg.pruefe_manifeste(mg.dateien_aus_ref(repo, gut_sha))
            self.assertTrue(mg.gruen(befunde_gut), befunde_gut)


class DauerbeweisTests(unittest.TestCase):
    """Das ausgelieferte Repo besteht die Wache – jede künftige Manifest-Sünde fällt hier auf."""

    def test_repo_manifeste_sind_gruen(self):
        dateien = mg.dateien_aus_baum(ROOT)
        self.assertIn(mg.MANIFEST, {Path(p).name for p in dateien})
        befunde = mg.pruefe_manifeste(dateien)
        self.assertEqual([b for b in befunde if b.schwere == mg.FEHLER], [],
                         "Ein Manifest im Repo ist kaputt – npm ci würde abbrechen.")

    def test_lockfile_paare_sind_vollstaendig(self):
        dateien = mg.dateien_aus_baum(ROOT)
        locks = [p for p in dateien if Path(p).name == mg.LOCK]
        for lock in locks:
            manifest = str(Path(lock).with_name(mg.MANIFEST).as_posix())
            self.assertIn(manifest, dateien, f"{lock} ohne Manifest")


class WiderstandTests(unittest.TestCase):
    """Eingaben, die die Wache nicht zum Absturz bringen dürfen."""

    def test_keine_utf8_datei_ist_befund_nicht_absturz(self):
        befunde = mg.pruefe_manifeste({mg.MANIFEST: b"\xff\xfe\x00bytes"})
        self.assertIn("J1", _codes(befunde, mg.FEHLER))

    def test_konfliktmarker_schlaegt_vor_json(self):
        text = mg.GUT_MANIFEST.replace('"pagefind": "1.5.2"', "<<<<<<< HEAD\n=======\n>>>>>>> main")
        befunde = mg.pruefe_manifeste({mg.MANIFEST: text, mg.LOCK: mg.GUT_LOCK})
        self.assertEqual(_codes(befunde, mg.FEHLER), {"K1"})

    def test_unbekanntes_ref_ist_werkzeugfehler(self):
        self.assertEqual(mg.main(["--ref", "gibt-es-nicht-0000"]), 2)

    def test_ausnahme_ohne_lock_ist_eng(self):
        self.assertIn("newsletter-worker/package.json", mg.OHNE_LOCKFILE_ERLAUBT)
        befunde = mg.pruefe_manifeste({"tools/x/" + mg.MANIFEST: mg.GUT_MANIFEST})
        self.assertIn("P1", _codes(befunde, mg.WARNUNG))


@unittest.skipUnless(yaml, "PyYAML fehlt")
class VerdrahtungTests(unittest.TestCase):
    """Jeder Workflow, der `npm ci`/`npm install` für das Repo ausführt, prüft vorher."""

    @staticmethod
    def _ist_repo_install(run: str) -> bool:
        for zeile in run.splitlines():
            z = zeile.strip()
            if not z or z.startswith("#"):
                continue
            if re.search(r"\bnpm\s+(ci|install|i)\b", z) and not re.search(r"(^|\s)(-g|--global)\b", z):
                return True
        return False

    def test_jeder_npm_install_ist_vorgeschaltet_geprueft(self):
        geprueft = 0
        for pfad in sorted(WORKFLOWS.glob("*.yml")):
            data = yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}
            for jid, job in (data.get("jobs") or {}).items():
                steps = (job or {}).get("steps") or []
                erster_install = next((i for i, s in enumerate(steps)
                                       if self._ist_repo_install(str((s or {}).get("run") or ""))), None)
                if erster_install is None:
                    continue
                geprueft += 1
                wache = next((i for i, s in enumerate(steps)
                              if "manifest_guard.py" in str((s or {}).get("run") or "")), None)
                self.assertIsNotNone(
                    wache, f"{pfad.name} · Job „{jid}“ führt npm ci/install aus, ohne Manifest-Wache.")
                self.assertLess(
                    wache, erster_install,
                    f"{pfad.name} · Job „{jid}“: Manifest-Wache steht NACH dem Install.")
        self.assertGreaterEqual(geprueft, 6, "Erwartet: mindestens sechs Install-Jobs im Repo.")

    def test_e2e_und_deploy_haben_den_schritt(self):
        for name in ("e2e.yml", "deploy.yml"):
            text = (WORKFLOWS / name).read_text(encoding="utf-8")
            self.assertIn("manifest_guard.py --selftest", text, f"{name}: Selbsttest der Wache fehlt")
            self.assertIn("python3 scripts/manifest_guard.py\n", text, f"{name}: Wache fehlt")


class EintragungTests(unittest.TestCase):
    def test_npm_skripte_sind_eingetragen(self):
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        skripte = pkg["scripts"]
        self.assertIn("manifest_guard.py", skripte["manifest:check"])
        self.assertIn("scripts.tests.test_manifest_guard", skripte["test:manifest"])

    def test_governance_kennt_die_wache(self):
        text = (ROOT / "scripts" / "governance_contract.py").read_text(encoding="utf-8")
        self.assertIn('"manifest_guard.py"', text, "C6: Wache fehlt in GUARDS")

    def test_alarm_nennt_bei_install_fehlern_die_manifest_ursache(self):
        text = (WORKFLOWS / "alert-on-failure.yml").read_text(encoding="utf-8")
        self.assertIn("installFailed", text)
        self.assertIn("Abhängigkeiten nicht installierbar", text)
        self.assertIn("python3 scripts/manifest_guard.py", text)
        # Die alte Ratschlagsliste bleibt der Fallback – sie wird nicht gelöscht.
        self.assertIn("API-Key abgelaufen", text)


if __name__ == "__main__":
    unittest.main()
