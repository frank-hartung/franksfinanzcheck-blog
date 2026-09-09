"""Regressions-Tests: scripts/git_sync.sh – Sync-Kern aller Bots.

Reparatur Issue #233 (Wöchentliche SEO-Optimierung, 09.09.2026):
Der Lauf starb an einem EINMALIGEN transienten Netzwerkfehler beim
`git pull` (fetch) – der alte Kern hatte Retries nur für den PUSH, nicht
für den FETCH, und keine Rettungsanker-Logik. Schritte 18–35 der
Wochenkette (Affiliate-/Bestand-/Cover-Gates, IndexNow) liefen dadurch nie.

Diese Tests beweisen die gehärteten Verträge gegen synthetische Repos
(nie gegen das Live-Repo, nie gegen das Netz):

  1. Happy Path: --push-only und Vollmodus committen+pushen sauber.
  2. Nichts zu pushen ist Erfolg (Exit 0), kein Fake-Push.
  3. Push-Race gegen einen parallelen Bot heilt per Auto-Rebase.
  4. Rebase-Konflikt auf generierten Reports löst sich deterministisch
     (--theirs = der frische Bot-Lauf gewinnt).
  5. Rebase-Konflikt auf append-only JSONL-Historien wird als
     deduplizierter Union-Merge zusammengeführt.
  6. Echter Content-Konflikt bleibt ein HARTER Stopp: kein Push, kein
     Blind-Merge, der lokale Commit bleibt sauber erhalten.
  7. Transienter fetch-Fehler (#233-Ursache!) wird wiederholt und heilt
     sich, sobald GitHub wieder antwortet.
  8. Bleibt der fetch dauerhaft weg, rettet der direkte Push-Versuch den
     Lauf, falls origin nicht weitergelaufen ist (Fast-Forward).

Ausführung wie Bestands-Tests:  python3 -m unittest discover -s scripts/tests -v
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
GIT_SYNC = REPO_ROOT / "scripts" / "git_sync.sh"

# Fake-`git`: sabotiert NUR `fetch` (steuerbar über Zählerdateien) und
# delegiert alles andere an das echte git. Damit ist die #233-Klasse
# (transienter Fetch-Ausfall, Push aber möglich) deterministisch testbar.
# {REAL_GIT} wird beim Setup durch den absoluten Pfad des echten git ersetzt
# (kein PATH-Lookup – sonst würde der Fake sich selbst finden).
FAKE_GIT_TEMPLATE = r"""#!/usr/bin/env bash
real="{REAL_GIT}"
[ -x "$real" ] || exit 127
if [ "${1:-}" = "fetch" ] && [ -n "${SABOTAGE_DIR:-}" ]; then
  if [ -f "$SABOTAGE_DIR/fetch_fails" ]; then
    n=$(cat "$SABOTAGE_DIR/fetch_fails" 2>/dev/null || echo 0)
    if [ "$n" -gt 0 ]; then
      echo "$((n - 1))" > "$SABOTAGE_DIR/fetch_fails"
      echo "fatal: simulierter Transient: Empty reply from server (EOF)" >&2
      exit 128
    fi
  fi
fi
exec "$real" "$@"
"""


class GitSyncTestBase(unittest.TestCase):
    """Stellt ein synthetisches Remote + zwei Klone bereit."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)

        self.origin = base / "origin.git"
        subprocess.run(["git", "init", "-q", "-b", "main", "--bare", str(self.origin)],
                       check=True)

        # Seed-Commit direkt ins Remote, damit ALLE Klone einen gemeinsamen
        # Anker haben (leeres Remote ist ein eigener, anderer Fehlerfall).
        seed = base / "seed"
        subprocess.run(["git", "clone", "-q", str(self.origin), str(seed)],
                       check=True, stderr=subprocess.DEVNULL)
        self._cfg(seed)
        self._commit(seed, "README.md", "# Start\n", "init")
        subprocess.run(["git", "-C", str(seed), "push", "-q", "origin", "main"], check=True)

        # Klon A ("paralleler Bot") und Klon B ("der lange SEO-Lauf")
        self.bot_a = self._clone("a")
        self.bot_b = self._clone("b")

        # Fake-git für gezielte Fetch-Sabotage
        self.bin = base / "bin"
        self.bin.mkdir()
        real_git = shutil.which("git") or "/usr/bin/git"
        (self.bin / "git").write_text(
            FAKE_GIT_TEMPLATE.replace("{REAL_GIT}", real_git), encoding="utf-8")
        (self.bin / "git").chmod(0o755)
        self.sabotage = base / "sabotage"
        self.sabotage.mkdir()

    # ---------- Helfer ---------------------------------------------------
    def _clone(self, name):
        path = Path(self.tmp.name) / name
        subprocess.run(["git", "clone", "-q", str(self.origin), str(path)], check=True)
        self._cfg(path)
        return path

    @staticmethod
    def _cfg(repo):
        for key, val in (("user.name", "Test-Bot"),
                         ("user.email", "test-bot@example.com"),
                         ("commit.gpgsign", "false")):
            subprocess.run(["git", "-C", str(repo), "config", key, val], check=True)

    @staticmethod
    def _commit(repo, relpath, content, msg):
        target = repo / relpath
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
        subprocess.run(["git", "-C", str(repo), "commit", "-q", "-m", msg], check=True)

    def run_sync(self, args, repo=None, env_extra=None, sabotage_fetch=None):
        """Führt git_sync.sh aus (standardmäßig im Klon B)."""
        repo = repo or self.bot_b
        env = dict(os.environ)
        env.update({
            "BRANCH": "main",
            "GIT_USER": "Test-Bot",
            "GIT_MAIL": "test-bot@example.com",
            "GIT_SYNC_BACKOFF": "0",
            "GIT_SYNC_FETCH_TRIES": "3",
            "GIT_SYNC_TRIES": "3",
            "SABOTAGE_DIR": str(self.sabotage),
            # Pufferkanäle zu, damit die Assertion auf stdout stabil ist
            "GITHUB_ENV": "",
        })
        env["PATH"] = f"{self.bin}:{env.get('PATH', '')}"
        if env_extra:
            env.update(env_extra)
        if sabotage_fetch is not None:
            (self.sabotage / "fetch_fails").write_text(str(sabotage_fetch))
        return subprocess.run(
            ["bash", str(GIT_SYNC), *args],
            cwd=str(repo), env=env, capture_output=True, text=True, timeout=120,
        )

    def origin_files(self):
        """Liest Dateien aus dem Remote-HEAD (schlanker als ein Klon)."""
        out = subprocess.run(
            ["git", "--git-dir", str(self.origin), "ls-tree", "-r", "--name-only", "main"],
            capture_output=True, text=True, check=True,
        ).stdout.split()
        return out

    def origin_read(self, relpath):
        return subprocess.run(
            ["git", "--git-dir", str(self.origin), "show", f"main:{relpath}"],
            capture_output=True, text=True, check=True,
        ).stdout

    def origin_log(self):
        out = subprocess.run(
            ["git", "--git-dir", str(self.origin), "log", "--format=%s", "main"],
            capture_output=True, text=True, check=True,
        ).stdout.splitlines()
        return out


class HappyPathTests(GitSyncTestBase):
    def test_push_only_happy_path(self):
        self._commit(self.bot_b, "data/status.jsonl", '{"run": 1}\n', "B: status")
        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Push erfolgreich", res.stdout)
        self.assertIn("data/status.jsonl", self.origin_files())
        self.assertIn("B: status", self.origin_log())

    def test_vollmodus_commit_und_push(self):
        report = self.bot_b / "FOO-REPORT.md"
        report.write_text("# Report\n", encoding="utf-8")
        res = self.run_sync(["chore: Testreport", "FOO-REPORT.md"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("chore: Testreport", self.origin_log())
        self.assertIn("FOO-REPORT.md", self.origin_files())

    def test_nichts_zu_pushen_ist_erfolg(self):
        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("nichts zu pushen", res.stdout)

    def test_keine_aenderungen_vollmodus(self):
        res = self.run_sync(["chore: leer", "gibt-es-nicht.md"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("nichts zu committen", res.stdout)


class RaceUndKonfliktTests(GitSyncTestBase):
    def test_push_race_heilt_per_autorebase(self):
        # Paralleler Bot A pusht, während B auf altem Stand committet.
        self._commit(self.bot_a, "docs/a.md", "A\n", "A: docs")
        res_a = self.run_sync(["--push-only"], repo=self.bot_a)
        self.assertEqual(res_a.returncode, 0, res_a.stdout + res_a.stderr)

        self._commit(self.bot_b, "docs/b.md", "B\n", "B: docs")
        res_b = self.run_sync(["--push-only"])
        self.assertEqual(res_b.returncode, 0, res_b.stdout + res_b.stderr)

        # Beide Änderungen live, Historie linear (Rebase, kein Merge-Commit)
        self.assertIn("docs/a.md", self.origin_files())
        self.assertIn("docs/b.md", self.origin_files())
        merge_count = subprocess.run(
            ["git", "--git-dir", str(self.origin), "log", "--merges", "--format=%h", "main"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(merge_count, "", "Historie muss linear bleiben (Rebase, kein Merge)")

    def test_report_konflikt_wird_deterministisch_autogeloest(self):
        # A (alter Lauf) pusht seinen Report-Stand …
        self._commit(self.bot_a, "SEO-REPORT.md", "Stand aus Lauf A\n", "A: report")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)
        # … B (frischer Lauf) hat einen NEUEN Report committet.
        self._commit(self.bot_b, "SEO-REPORT.md", "Stand aus Lauf B\n", "B: report")
        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Bot-Artefakt-Konflikte automatisch gelöst", res.stdout)
        # Deterministisch: der FRISCHE Lauf (B) gewinnt.
        self.assertEqual(self.origin_read("SEO-REPORT.md"), "Stand aus Lauf B\n")

    def test_jsonl_konflikt_wird_union_gemerget(self):
        base_jsonl = 'data/history.jsonl'
        self._commit(self.bot_a, base_jsonl, '{"run": "basis"}\n', "init jsonl")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)

        # Beide Seiten hängen NUR an (append-only) – klassischer Parallel-Bot.
        self._commit(self.bot_a, base_jsonl,
                     '{"run": "basis"}\n{"run": "A"}\n', "A: append")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)
        self._commit(self.bot_b, base_jsonl,
                     '{"run": "basis"}\n{"run": "B"}\n', "B: append")

        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        merged = self.origin_read(base_jsonl)
        self.assertIn('"run": "A"', merged)
        self.assertIn('"run": "B"', merged)
        self.assertIn('"run": "basis"', merged)
        # Keine Duplikat-Zeilen (deduplizierter Union-Merge)
        lines = [ln for ln in merged.splitlines() if ln.strip()]
        self.assertEqual(len(lines), len(set(lines)), f"Duplikate im Merge: {lines}")

    def test_content_konflikt_bleibt_harter_stopp(self):
        # A ändert einen Artikel und pusht …
        self._commit(self.bot_a, "content/artikel.md", "Text neu von A\n", "A: artikel")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)
        # … B hat dieselben Zeilen redaktionell geändert -> echter Konflikt.
        self._commit(self.bot_b, "content/artikel.md", "Text neu von B\n", "B: artikel")

        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 1, "Content-Konflikt muss rot bleiben")
        self.assertIn("Kein Push", res.stdout + res.stderr)
        # Kein Blind-Merge: origin enthält NICHT B Stand …
        self.assertEqual(self.origin_read("content/artikel.md"), "Text neu von A\n")
        # … und B behält seinen Commit sauber lokal (nichts verloren).
        local = subprocess.run(
            ["git", "-C", str(self.bot_b), "log", "--format=%s", "-1"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(local, "B: artikel")


class NetzwerkHaertungTests(GitSyncTestBase):
    """Die eigentliche #233-Reparatur: transiente fetch-Fehler."""

    def _prepare_b_commit(self):
        # B hat einen Commit, origin ist auf gemeinsamem Stand (kein Race).
        self._commit(self.bot_b, "data/run.jsonl", '{"ok": true}\n', "B: lauf")

    def test_transienter_fetch_fehler_heilt_durch_retry(self):
        self._prepare_b_commit()
        # Fetch fällt 2x aus (GitHub-Transient), der 3. Versuch geht durch.
        res = self.run_sync(["--push-only"], sabotage_fetch=2)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("erneuter Versuch", res.stdout, "Retry-Meldung fehlt")
        self.assertIn("Push erfolgreich", res.stdout)
        self.assertIn("B: lauf", self.origin_log())

    def test_dauerhafter_fetch_ausfall_rettungsanker_push(self):
        self._prepare_b_commit()
        # Fetch bleibt tot (#233-Situation) – aber origin ist NICHT
        # weitergelaufen: der Rettungsanker-Push muss den Lauf retten.
        res = self.run_sync(["--push-only"], sabotage_fetch=99,
                            env_extra={"GIT_SYNC_TRIES": "1"})
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Rettungsanker erfolgreich", res.stdout)
        self.assertIn("B: lauf", self.origin_log())

    def test_dauerhafter_fetch_ausfall_mit_race_bleibt_rot_aber_sauber(self):
        self._prepare_b_commit()
        # A pusht parallel – Bs Rettungsanker-Push wird abgelehnt (non-FF)
        # und der fetch ist tot: dann muss LAUT und sauber rot geendet
        # werden, ohne B's Commit zu beschädigen.
        self._commit(self.bot_a, "docs/parallel.md", "A\n", "A: parallel")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)

        res = self.run_sync(["--push-only"], sabotage_fetch=99,
                            env_extra={"GIT_SYNC_TRIES": "1"})
        self.assertEqual(res.returncode, 1, "Ohne fetch und mit Race muss rot geendet werden")
        combined = res.stdout + res.stderr
        self.assertIn("Rettungsanker", combined)
        # B's Commit bleibt lokal unangetastet (kein Rebase-Halbzustand).
        local = subprocess.run(
            ["git", "-C", str(self.bot_b), "log", "--format=%s", "-1"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(local, "B: lauf")
        status = subprocess.run(["git", "-C", str(self.bot_b), "status", "--porcelain"],
                                capture_output=True, text=True, check=True).stdout
        self.assertEqual(status.strip(), "", "Arbeitsbaum von B muss sauber sein")


if __name__ == "__main__":
    unittest.main()
