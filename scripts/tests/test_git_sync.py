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
  9. Eine Ruleset-/Branch-Schutz-Ablehnung (Vorfall 19.09.2026, Issue #320)
     ist Klasse `schutz`: sofortiger Abbruch OHNE Backoff-Runden, Meldung mit
     Reparatur-Anleitung – während Netzwerk-Transient und Non-Fast-Forward
     retrybar bleiben. Eine Regel wartet sich nicht weg.

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
if [ "${1:-}" = "push" ] && [ -n "${SABOTAGE_DIR:-}" ]; then
  v=$(( $(cat "$SABOTAGE_DIR/push_versuche" 2>/dev/null || echo 0) + 1 ))
  echo "$v" > "$SABOTAGE_DIR/push_versuche"
  if [ -f "$SABOTAGE_DIR/push_fehler" ]; then
    cat "$SABOTAGE_DIR/push_fehler" >&2
    exit 1
  fi
fi
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

    def test_reserve_zertifikat_konflikt_heilt_frischer_lauf_gewinnt(self):
        """Issue #295: Das Reserve-Zertifikat ist ein maschinengeneriertes
        Artefakt und wird von JEDEM Lauf komplett neu geschrieben. Ein
        Rebase-Konflikt darauf darf den nächtlichen Reserve-Lauf nicht mehr
        rot machen (Run 34949097389: Deploy-Lauf committete dieselbe Datei
        um 10:50:30, während der Reserve-Lauf pushte)."""
        cert = "data/reserve-readiness.json"
        self._commit(self.bot_a, cert, '{"target": 6, "ready": 6}\n',
                     "A: zertifikat (deploy)")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)
        # Der frische Reserve-Lauf hat SEIN (ehrlicheres) Zertifikat dabei.
        self._commit(self.bot_b, cert, '{"target": 6, "ready": 3}\n',
                     "B: zertifikat (reserve)")
        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Bot-Artefakt-Konflikte automatisch gelöst", res.stdout)
        self.assertEqual(self.origin_read(cert), '{"target": 6, "ready": 3}\n')

    def test_cover_manifest_konflikt_heilt_frischer_lauf_gewinnt(self):
        """Dasselbe für das Cover-Manifest (Fingerprints, rein generiert)."""
        manifest = "data/covers_manifest.json"
        self._commit(self.bot_a, manifest, '{"a": {"title": "alt"}}\n',
                     "A: manifest")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)
        self._commit(self.bot_b, manifest, '{"a": {"title": "neu"}}\n',
                     "B: manifest")
        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("neu", self.origin_read(manifest))

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


class ReserveKandidatKonfliktTests(GitSyncTestBase):
    """#295: Reserve-Kandidaten sind maschinenverwaltet (draft+reserve) –
    ein Konflikt darauf heilt (frischer Lauf gewinnt), LIVE-Content bleibt
    ein harter Stopp."""

    SLUG = "content/posts/2026-09-15-gasrechnung-senken-probe/index.md"

    @staticmethod
    def _draft(body, reserve=True, draft=True):
        kopf = ("---\ntitle: Probe\ndate: 2026-09-15T06:00:00Z\n"
                f"draft: {'true' if draft else 'false'}\n")
        if reserve:
            kopf += "reserve: true\n"
        return kopf + "---\n" + body + "\n"

    def test_beide_seiten_reserve_entwurf_heilt(self):
        self._commit(self.bot_a, self.SLUG, self._draft("A: stale Fassung"),
                     "A: stale Veredelung")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)
        self._commit(self.bot_b, self.SLUG, self._draft("B: frische Veredelung"),
                     "B: frische Veredelung")
        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Bot-Artefakt-Konflikte automatisch gelöst", res.stdout)
        self.assertIn("B: frische Veredelung", self.origin_read(self.SLUG))

    def test_live_artikel_bleibt_harter_stopp(self):
        self._commit(self.bot_a, self.SLUG, self._draft("A: live", reserve=False,
                                                        draft=False),
                     "A: live")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)
        self._commit(self.bot_b, self.SLUG, self._draft("B: reserve"),
                     "B: reserve")
        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 1,
                         "Live-Content darf NIE automatisch gemergt werden")
        self.assertIn("Kein Push", res.stdout + res.stderr)

    def test_hand_entwurf_ohne_reserve_marker_bleibt_harter_stopp(self):
        self._commit(self.bot_a, self.SLUG, self._draft("A: Handentwurf",
                                                        reserve=False),
                     "A: Handentwurf")
        self.assertEqual(self.run_sync(["--push-only"], repo=self.bot_a).returncode, 0)
        self._commit(self.bot_b, self.SLUG, self._draft("B: reserve"),
                     "B: reserve")
        res = self.run_sync(["--push-only"])
        self.assertEqual(res.returncode, 1,
                         "Hand-Entwürfe ohne reserve-Marker sind tabu")


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


# --------------------------------------------------------------------------- #
#  Vorfall 20./21.09.2026 (Issue #329): Tag-Push-Trigger + gelöschtes Ref
# --------------------------------------------------------------------------- #
#  Ein kurzlebiger Probe-TAG (_arena-perm-probe) triggerte den
#  Willkommenstext-Refresh (Tag-Pushes unterliegen keinem paths-Filter) und
#  wurde Sekunden später gelöscht. Der Lauf (detached HEAD, Remote-Ref weg)
#  starb mit Exit 128: "You must fully qualify the ref" – der ALTE Push
#  benutzte den KURZEN Refnamen `HEAD:<name>`, den git bei detached HEAD
#  ohne Remote-Ref nicht auflösen kann. Dieselbe Exit-128-Klasse traf am
#  28.08./31.08.2026 gelöschte Feature-Branches (Runs 33131763016 /
#  33408869777).
class TagTriggerUndGeloeschtesRefTests(GitSyncTestBase):
    def _delete_remote_main(self):
        # Das bare Test-Remote verweigert standardmäßig das Löschen seiner
        # HEAD-Branch – das erlauben wir, damit der gelöschte Probe-Ref
        # (CI-Situation) simuliert werden kann.
        subprocess.run(["git", "--git-dir", str(self.origin), "config",
                        "receive.denyDeleteCurrent", "ignore"], check=True)
        subprocess.run(["git", "-C", str(self.bot_b), "push", "-q", "origin", ":main"],
                       check=True)

    def _remote_refs(self):
        out = subprocess.run(
            ["git", "ls-remote", "--heads", "--tags", str(self.origin)],
            capture_output=True, text=True, check=True,
        ).stdout
        return {line.split("\t")[1] for line in out.splitlines() if line}

    def test_tag_trigger_publish_nicht_kein_muell_ref(self):
        # #329-Kern: Tag-Trigger (Probe-Tag, Sekunden später gelöscht)
        # PUBLIZIERT NICHT – grüner Exit, kein Ref im Remote.
        self._commit(self.bot_b, "data/status.jsonl", '{"run": 1}\n', "B: status")
        res = self.run_sync(
            ["--push-only"],
            env_extra={"BRANCH": "", "GITHUB_REF_TYPE": "tag",
                       "GITHUB_REF_NAME": "probe-tag"},
        )
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 0, log)
        self.assertIn("TAG ausgelöst", log)
        self.assertIn("KEIN Push", log)
        # Nichts ist im Remote angelegt worden (weder Branch noch Tag).
        refs = self._remote_refs()
        self.assertNotIn("refs/heads/probe-tag", refs)
        self.assertNotIn("refs/tags/probe-tag", refs)
        self.assertNotIn("B: status", self.origin_log())
        # B behält seinen Commit lokal (nichts verloren, kein Halbzustand).
        local = subprocess.run(
            ["git", "-C", str(self.bot_b), "log", "--format=%s", "-1"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        self.assertEqual(local, "B: status")

    def test_tag_trigger_mit_explicit_branch_override_push_trotzdem(self):
        # Bewusste Ausnahme: BRANCH explizit gesetzt = der Workflow will
        # auf eine echte Branch syncen – der Schutz greift NICHT.
        self._commit(self.bot_b, "data/status.jsonl", '{"run": 2}\n', "B: status")
        res = self.run_sync(
            ["--push-only"],
            env_extra={"BRANCH": "main", "GITHUB_REF_TYPE": "tag",
                       "GITHUB_REF_NAME": "probe-tag"},
        )
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Push erfolgreich", res.stdout)
        self.assertIn("B: status", self.origin_log())

    def test_geloeschtes_ref_detached_head_heilt_per_vollqualifiziertem_push(self):
        # #329 exakt (Branch-Variante): CI-Checkout = detached HEAD,
        # Ziel-Ref zwischenzeitlich gelöscht. Der ALTE Code starb hier mit
        # Exit 128 („You must fully qualify the ref"); jetzt legt der
        # vollqualifizierte Rettungsanker den Ref neu an.
        self._commit(self.bot_b, "data/status.jsonl", '{"run": 3}\n', "B: status")
        # CI-Zustand simulieren: detached HEAD …
        subprocess.run(["git", "-C", str(self.bot_b), "checkout", "-q", "--detach"],
                       check=True)
        # … und das Ziel-Ref remote weg (Probe-Ref, der sofort gelöscht wurde).
        self._delete_remote_main()

        res = self.run_sync(["--push-only"])
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 0, log)
        self.assertIn("Rettungsanker", log)
        self.assertNotIn("fully qualify", log)          # der #329-Todespfad ist weg
        # main ist im Remote neu angelegt und trägt B's Commit.
        self.assertIn("refs/heads/main", self._remote_refs())
        self.assertIn("B: status", self.origin_log())

    def test_fehlendes_remote_ref_keine_retry_runden(self):
        # Ein gelöschtes Ref ist kein Netzwerk-Transient: keine Backoff-
        # Runden, genau EIN Push-Versuch (der das Ref neu anlegt).
        self._commit(self.bot_b, "data/status.jsonl", '{"run": 4}\n', "B: status")
        subprocess.run(["git", "-C", str(self.bot_b), "checkout", "-q", "--detach"],
                       check=True)
        self._delete_remote_main()

        res = self.run_sync(["--push-only"], env_extra={"GIT_SYNC_TRIES": "3"})
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 0, log)
        self.assertIn("existiert remote NICHT", log)
        self.assertNotIn("erneuter Versuch", log,
                         "fehlendes Ref darf nicht als Transient retryen")
        zaehler = self.sabotage / "push_versuche"
        self.assertEqual(int(zaehler.read_text(encoding="utf-8")), 1,
                         "genau EIN Push-Versuch erwartet")


if __name__ == "__main__":
    unittest.main()


# --------------------------------------------------------------------------- #
#  Vorfall 19.09.2026 (Issue #320): Ruleset-Ablehnung ≠ Wackelkontakt
# --------------------------------------------------------------------------- #
GH014_PFLICHT_CHECK = """remote: error: GH014: Push cannot be completed as the required status check "Integritäts-Siegel" has not passed.
To https://github.com/frank-hartung/franksfinanzcheck-blog.git
 ! [remote rejected] main -> main (update-ref failed)
error: failed to push some refs to 'https://github.com/frank-hartung/franksfinanzcheck-blog.git'
"""

GH006_PR_ZWANG = """remote: error: GH006: Protected branch update failed for 'refs/heads/main'.
remote: error: Changes must be made through a pull request.
To https://github.com/frank-hartung/franksfinanzcheck-blog.git
 ! [remote rejected] main -> main (protected branch hook declined)
error: failed to push some refs
"""

SIGNATURPFLICHT = """remote: error: GH006: Protected branch update failed for 'refs/heads/main'.
remote: error: Commits must be signed.
 ! [remote rejected] main -> main (must be signed)
error: failed to push some refs
"""

NETZWERK_TRANSIENT = """fatal: unable to access 'https://github.com/frank-hartung/franksfinanzcheck-blog.git/': Failed to connect to github.com port 443 after 120035 ms: Couldn't connect to server
"""

NON_FAST_FORWARD = """To https://github.com/frank-hartung/franksfinanzcheck-blog.git
 ! [rejected]        main -> main (fetch first)
error: failed to push some refs
hint: Updates were rejected because the remote contains work that you do not have locally.
"""


class SchutzKlasseTests(GitSyncTestBase):
    """Eine Regel, die den Push ablehnt, darf nicht als Netzwerkfehler durchgehen.

    Am 19.09.2026 verlangte Ruleset #23695872 den Pflicht-Check
    `Integritäts-Siegel` auf `main`, ohne Bypass-Akteur. Der Check entsteht nur
    in Pull Requests, Pflicht-Checks gelten aber für jeden Push – jeder Bot-Push
    wurde abgelehnt, `git_sync.sh` meldete „zuletzt: netzwerk" und verbrannte
    drei Runden Backoff. Deploy #998 starb, „Deploy auf gh-pages" wurde
    übersprungen, die Website blieb vier Stunden alt.
    """

    def _push_versuche(self):
        zaehler = self.sabotage / "push_versuche"
        return int(zaehler.read_text(encoding="utf-8").strip()) if zaehler.exists() else 0

    def _mit_push_fehler(self, fehler_text, args=("--push-only",), sabotage_fetch=None):
        (self.sabotage / "push_fehler").write_text(fehler_text, encoding="utf-8")
        self._commit(self.bot_b, "data/status.jsonl", '{"run": 1}\n', "B: status")
        return self.run_sync(list(args), sabotage_fetch=sabotage_fetch)

    # --- Schutz: sofortiger Abbruch, klare Meldung, KEINE Runden ------------- #
    def test_pflicht_check_ohne_bypass_ist_schutz(self):
        res = self._mit_push_fehler(GH014_PFLICHT_CHECK)
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 1, log)
        self.assertIn("::error::", log)
        self.assertIn("schutz", log)                       # Klasse steht im Log
        self.assertIn("Branch-Schutz/Ruleset", log)
        self.assertIn("PFLICHT-CHECK-RUNBOOK.md", log)     # Reparatur, nicht nur Rot
        self.assertNotIn("3 Runden", log)                  # kein Backoff gegen eine Regel
        self.assertEqual(self._push_versuche(), 1, "genau EIN Push-Versuch erwartet")
        self.assertNotIn("B: status", self.origin_log())   # nichts ist durchgerutscht

    def test_pr_zwang_ist_schutz(self):
        res = self._mit_push_fehler(GH006_PR_ZWANG)
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 1, log)
        self.assertIn("Branch-Schutz/Ruleset", log)
        self.assertNotIn("Auth/Berechtigung", log)         # nicht als auth fehlgedeutet
        self.assertEqual(self._push_versuche(), 1)

    def test_signaturpflicht_ist_schutz(self):
        res = self._mit_push_fehler(SIGNATURPFLICHT)
        self.assertEqual(res.returncode, 1, res.stdout + res.stderr)
        self.assertIn("Branch-Schutz/Ruleset", res.stdout + res.stderr)
        self.assertEqual(self._push_versuche(), 1)

    def test_schutz_auch_im_vollmodus(self):
        # Vollmodus = committen UND pushen (so laufen die Bots im Deploy).
        (self.sabotage / "push_fehler").write_text(GH014_PFLICHT_CHECK, encoding="utf-8")
        (self.bot_b / "FOO.md").write_text("# Foo\n", encoding="utf-8")
        res = self.run_sync(["chore: Testreport", "FOO.md"])
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 1, log)
        self.assertIn("Branch-Schutz/Ruleset", log)
        self.assertIn("Ursache: schutz", log)
        self.assertEqual(self._push_versuche(), 1)
        self.assertNotIn("chore: Testreport", self.origin_log())

    def test_rettungsanker_umgeht_schutz_nicht(self):
        # Selbst wenn der fetch ausfällt (Rettungsanker-Pfad): eine Regel bleibt
        # eine Regel – der direkte Push-Versuch darf sie nicht „ausprobieren".
        res = self._mit_push_fehler(GH014_PFLICHT_CHECK, sabotage_fetch=3)
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 1, log)
        self.assertIn("Branch-Schutz/Ruleset", log)

    # --- Die Gegenseite: Transientes muss retrybar bleiben ------------------ #
    def test_netzwerk_transient_bleibt_retrybar(self):
        res = self._mit_push_fehler(NETZWERK_TRANSIENT)
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 1, log)
        self.assertIn("3 Runden", log)                     # Backoff wie gehabt
        self.assertNotIn("Branch-Schutz/Ruleset", log)     # keine falsche Diagnose
        self.assertEqual(self._push_versuche(), 3, "drei Versuche bei Transient")

    def test_non_fast_forward_bleibt_retrybar(self):
        res = self._mit_push_fehler(NON_FAST_FORWARD)
        log = res.stdout + res.stderr
        self.assertEqual(res.returncode, 1, log)
        self.assertNotIn("Branch-Schutz/Ruleset", log)
        self.assertEqual(self._push_versuche(), 3, "drei Versuche bei Race")
