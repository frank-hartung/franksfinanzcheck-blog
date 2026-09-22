"""Regressionstests für die dauerhafte Reparatur zu Issue #316 (19.09.2026).

Der Vorfall: PR #315 (Commit ff6232e3) heilte sechs gesperrte Skripte und
signierte den Integritäts-Lock nicht mit. Zwei Läufe der Content-Engine
starben danach im ERSTEN Schritt (HARD STOP in `integrity_guard.py`), VOR
jeder Artikelarbeit – kein Artikel, kein Slot, Defizit-Alarm. Der HARD STOP
tat also genau, was er soll, und traf den falschen: die Produktion statt den
Merge.

Diese Tests nageln die drei Antworten darauf fest, jeweils an einem echten
Mini-Repo (keine Attrappen – eine Attrappe wäre die zweite Wahrheit):

  1. KLASSIFIKATION  „committet" und „zur Laufzeit verändert" sind
     unterscheidbar. Nur Ersteres ist signierbar; Letzteres ist genau die
     Klasse, die ein Siegel fangen muss.
  2. SIGNATUR-REGEL  `--heal` signiert ausschließlich versionierten,
     bytegleich committeten Drift der Klasse FEST. KRITISCH und
     Laufzeit-Mutationen bleiben HARD STOP (Exit 3) – Sabotage bleibt eine
     menschliche Entscheidung.
  3. KONVERGENZ & SPUR  Heilung ist idempotent, hinterlässt eine Akte im
     Lock (Herkunft: Commits, Klasse) und eine schema-konforme Zeile in
     `data/integrity_history.jsonl` (deren Pflichtfelder `history_guard.py`
     festhält). Und: Beweis-Läufe schreiben nichts (C15).

Nachtrag 21.09.2026 (Layout-Automatisierung, #338/#344) – zwei Lücken, die
die Mechanik oben nicht fangen konnte, weil sie nur Attrappen prüfte:

  4. BETREIBER-WEG  `--set-current` ist die Signatur, die das Gate selbst
     empfiehlt – sie schrieb die Herkunft aber nicht mit (im Gegensatz zu
     `--heal`). Die stille Neuzeichnung war damit der bequemste Weg. Jetzt
     nennt sie Klasse, Urteil und belegende Commits und hinterlässt eine
     Zeile in der Historie (`SetCurrentTests`).
  5. AUSLIEFERUNG  Der Baum DIESES Repos wird gegen sein Siegel geprüft
     (`RepoSealTests`). Am 21.09. war die Mechanik vollständig grün, während
     `main` aus dem Siegel lief: #344 hatte `head.html` (KRITISCH) geheilt
     und den Lock nicht mit-signiert. Der PR-Lauf zeigte es, der Branch-Schutz
     verlangt den Check aber nicht – der Merge ging durch, und der nächste
     Content-Engine-Lauf wäre im ersten Schritt hart gestoppt (kein Artikel,
     kein Slot, Defizit-Alarm). Der Testlauf ist der Weg, den CLAUDE.md vor
     dem Push nennt: hier steht der Befund jetzt nicht mehr stumm daneben.
"""
import contextlib
import datetime
import io
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import integrity_guard as ig  # noqa: E402

FEST_REL = "scripts/blog_doctor.py"      # Mitglied der FEST-Klasse
CRIT_REL = "hugo.toml"                   # Mitglied der KRITISCH-Klasse


def _git(root, *args):
    return subprocess.run(("git",) + args, cwd=str(root), capture_output=True, text=True)


def _commit(root, msg):
    _git(root, "add", "-A")
    return _git(root, "-c", "user.email=t@example.org", "-c", "user.name=Test",
                "commit", "-q", "-m", msg)


class Fixture(unittest.TestCase):
    """Mini-Repo mit je einer Datei der beiden Lock-Klassen."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ffc-test-integrity-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir(parents=True)
        (self.root / "layouts" / "_partials").mkdir(parents=True)
        (self.root / CRIT_REL).write_text("baseURL = '/'\n", encoding="utf-8")
        (self.root / FEST_REL).write_text("print('visite')\n", encoding="utf-8")
        _git(self.root, "init", "-q")
        self.assertEqual(_commit(self.root, "fixture").returncode, 0)
        self.lock_pfad = self.root / "data" / "integrity_lock.json"
        self.history_pfad = self.root / "data" / "integrity_history.jsonl"
        self.lock_pfad.parent.mkdir(parents=True, exist_ok=True)

    # ---- Hilfen -------------------------------------------------
    def signieren(self):
        with contextlib.redirect_stdout(io.StringIO()):
            ig.signieren(self.root, grund="test")

    def driften(self):
        lock = ig.load_lock(self.lock_pfad)
        return ig.verify_files(self.root, lock.get("files", {}))

    def schreibe(self, rel, inhalt):
        (self.root / rel).write_text(inhalt, encoding="utf-8")


class VerifyTests(Fixture):
    def test_sauberer_baum_hat_keinen_drift(self):
        self.signieren()
        self.assertEqual(self.driften(), ([], []))

    def test_fest_und_kritisch_werden_unterschieden(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('neu')\n")
        self.schreibe(CRIT_REL, "baseURL = '/neu/'\n")
        crit, fest = self.driften()
        self.assertEqual(crit, [CRIT_REL])
        self.assertEqual(fest, [FEST_REL])

    def test_neue_kritische_datei_ohne_signatur_ist_ein_fund(self):
        (self.root / "layouts" / "robots.txt").write_text("User-agent: *\n",
                                                          encoding="utf-8")
        self.signieren()
        # Signatur kennt die Datei jetzt – ohne Signatur wäre sie ein Fund.
        lock = ig.load_lock(self.lock_pfad)
        del lock["files"]["layouts/robots.txt"]
        crit, _ = ig.verify_files(self.root, lock["files"])
        self.assertIn("layouts/robots.txt (neu ohne Signatur)", crit)


class KlassifikationTests(Fixture):
    def test_committete_aenderung_ist_versiegelbar(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('geheilt')\n")
        self.assertEqual(_commit(self.root, "fix: belegte Änderung").returncode, 0)
        crit, fest = self.driften()
        audit = ig.klassifizieren(self.root, crit, fest,
                                  ig.load_lock(self.lock_pfad).get("head", ""))
        eintrag = next(e for e in audit if e["pfad"] == FEST_REL)
        self.assertEqual(eintrag["urteil"], "VERSIEGELBAR")
        self.assertEqual(eintrag["commits_art"], "seit-signatur")
        self.assertTrue(any(c["sha"] for c in eintrag["commits"]))
        self.assertTrue(ig.heilverdict(audit)[0])

    def test_laufzeitmutation_ist_nicht_versiegelbar(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('laufzeit')\n")   # NICHT committet
        crit, fest = self.driften()
        audit = ig.klassifizieren(self.root, crit, fest, "")
        eintrag = next(e for e in audit if e["pfad"] == FEST_REL)
        self.assertEqual(eintrag["urteil"], "UNERKLÄRT")
        self.assertFalse(eintrag["stand_gleich_head"])
        heilbar, blockiert = ig.heilverdict(audit)
        self.assertFalse(heilbar)
        self.assertTrue(blockiert)

    def test_rebase_hash_faellt_auf_letzte_commits_zurueck(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('neu')\n")
        _commit(self.root, "fix: danach")
        crit, fest = self.driften()
        audit = ig.klassifizieren(self.root, crit, fest, "0000000")
        eintrag = next(e for e in audit if e["pfad"] == FEST_REL)
        self.assertEqual(eintrag["commits_art"], "letzte-commits")
        self.assertTrue(eintrag["commits"])


class HeilungTests(Fixture):
    def test_heilen_signiert_belegten_fest_drift(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('geheilt')\n")
        _commit(self.root, "fix: belegte Änderung")
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ig.heilen(self.root), 0)
        self.assertEqual(self.driften(), ([], []))
        lock = ig.load_lock(self.lock_pfad)
        akte = lock["audit"][-1]
        self.assertEqual(akte["art"], "heal")
        self.assertEqual(akte["geaendert"], [FEST_REL])
        herkunft = akte["herkunft"][0]
        self.assertEqual(herkunft["pfad"], FEST_REL)
        self.assertEqual(herkunft["klasse"], "fest")
        self.assertEqual(herkunft["commits_art"], "seit-signatur")

    def test_heilung_ist_konvergent(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('geheilt')\n")
        _commit(self.root, "fix: belegte Änderung")
        with contextlib.redirect_stdout(io.StringIO()):
            ig.heilen(self.root)
            vorher = ig.sha256_file(self.lock_pfad)
            self.assertEqual(ig.heilen(self.root), 0)
        self.assertEqual(ig.sha256_file(self.lock_pfad), vorher,
                         "zweite Heilung darf nichts mehr ändern")

    def test_heilen_stoppt_bei_kritischem_drift(self):
        self.signieren()
        self.schreibe(CRIT_REL, "baseURL = '/neu/'\n")
        _commit(self.root, "feat: kritischer Kern")
        vorher = ig.sha256_file(self.lock_pfad)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ig.heilen(self.root), 3)
        self.assertEqual(ig.sha256_file(self.lock_pfad), vorher,
                         "HARD STOP darf nicht signieren")

    def test_heilen_stoppt_bei_laufzeitmutation(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('laufzeit')\n")
        vorher = ig.sha256_file(self.lock_pfad)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ig.heilen(self.root), 3)
        self.assertEqual(ig.sha256_file(self.lock_pfad), vorher)

    def test_dry_run_schreibt_nichts(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('geheilt')\n")
        _commit(self.root, "fix: belegte Änderung")
        vorher = ig.sha256_file(self.lock_pfad)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ig.heilen(self.root, dry_run=True), 0)
        self.assertEqual(ig.sha256_file(self.lock_pfad), vorher)

    def test_heilung_laesst_schema_konforme_historie(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('geheilt')\n")
        _commit(self.root, "fix: belegte Änderung")
        with contextlib.redirect_stdout(io.StringIO()):
            ig.heilen(self.root)
        zeilen = [json.loads(z) for z in
                  self.history_pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
        self.assertEqual(len(zeilen), 1)
        self.assertIsInstance(zeilen[0]["date"], str)
        self.assertIsInstance(zeilen[0]["kritisch"], int)
        self.assertIsInstance(zeilen[0]["fest"], int)
        self.assertEqual(zeilen[0]["modus"], "heal")
        self.assertEqual(zeilen[0]["geheilt"], [FEST_REL])


class GateTests(Fixture):
    def test_gate_ist_fail_closed(self):
        self.signieren()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ig.gate(self.root), 0)
            self.schreibe(FEST_REL, "print('neu')\n")
            self.assertEqual(ig.gate(self.root), 3,
                             "auch FEST-Drift muss im PR-Gate rot sein")
            self.schreibe(CRIT_REL, "baseURL = '/neu/'\n")
            self.assertEqual(ig.gate(self.root), 3)

    def test_gate_nennt_die_reparaturzeile(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('neu')\n")
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            ig.gate(self.root)
        text = puffer.getvalue()
        self.assertIn("--set-current", text)
        self.assertIn("data/integrity_lock.json", text)

    def test_drift_audit_ist_read_only(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('neu')\n")
        vorher = {p: ig.sha256_file(p) for p in
                  (self.lock_pfad, self.history_pfad,
                   self.root / "INTEGRITY-REPORT.md")}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ig.drift_audit(self.root), 1)
            self.assertEqual(ig.gate(self.root), 3)
        for pfad, sha in vorher.items():
            self.assertEqual(ig.sha256_file(pfad), sha,
                             f"{pfad.name} wurde von einem Lese-Modus angefasst")

    def test_exit_urteil(self):
        self.assertEqual(ig.exit_fuer([], []), 0)
        self.assertEqual(ig.exit_fuer([], ["a"]), 1)
        self.assertEqual(ig.exit_fuer(["a"], []), 3)


class BeweisTests(Fixture):
    def test_selftest_schreibt_nicht_in_den_baum(self):
        """C15: Der Kern-Beweis baut sein eigenes Repo – und rührt dieses nicht an."""
        vorher = {p: ig.sha256_file(p) for p in (ig.LOCK, ig.REPORT, ig.HISTORY)}
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ig.selftest(), 0)
        for pfad, sha in vorher.items():
            self.assertEqual(ig.sha256_file(pfad), sha,
                             f"Selbsttest hat {pfad.name} verändert")

    def test_signieren_schreibt_sortierte_akte(self):
        self.signieren()
        lock = ig.load_lock(self.lock_pfad)
        self.assertEqual(list(lock["files"]), sorted(lock["files"]))
        self.assertTrue(all(lock["files"].values()), "leere Hashes sind kein Siegel")
        self.assertEqual(lock["audit"][-1]["art"], "test")


class SetCurrentTests(Fixture):
    """Der Weg, den das Gate empfiehlt, muss dieselbe Spur legen wie --heal."""

    def test_set_current_nennt_die_herkunft(self):
        self.signieren()
        self.schreibe(CRIT_REL, "baseURL = '/neu/'\n")
        _commit(self.root, "feat: kritischer Kern bewusst geändert")
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            self.assertEqual(ig.set_current(self.root), 0)
        akte = ig.load_lock(self.lock_pfad)["audit"][-1]
        self.assertEqual(akte["art"], "set-current")
        self.assertEqual(akte["geaendert"], [CRIT_REL])
        herkunft = akte["herkunft"][0]
        self.assertEqual(herkunft["pfad"], CRIT_REL)
        self.assertEqual(herkunft["klasse"], "kritisch")
        self.assertEqual(herkunft["urteil"], "VERSIEGELBAR")
        self.assertTrue(herkunft["commits"], "Herkunft ohne Commit ist keine")
        self.assertIn("Herkunft:", puffer.getvalue(),
                      "die Signatur muss im Log sagen, was sie zeichnet")
        self.assertEqual(self.driften(), ([], []))

    def test_set_current_ohne_drift_traegt_keine_herkunft(self):
        self.signieren()
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(ig.set_current(self.root), 0)
        akte = ig.load_lock(self.lock_pfad)["audit"][-1]
        self.assertEqual(akte["geaendert"], [])
        self.assertNotIn("herkunft", akte,
                         "ohne Drift gibt es keine Herkunft zu erfinden")
        self.assertEqual(self.driften(), ([], []))

    def test_set_current_hinterlaesst_eine_zeile_in_der_historie(self):
        self.signieren()
        self.schreibe(FEST_REL, "print('neu')\n")
        _commit(self.root, "fix: bewusst neu signiert")
        with contextlib.redirect_stdout(io.StringIO()):
            ig.set_current(self.root)
        zeilen = [json.loads(z) for z in
                  self.history_pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
        self.assertEqual(zeilen[-1]["modus"], "set-current")
        self.assertEqual(zeilen[-1]["fest"], 1)
        self.assertEqual(zeilen[-1]["geaendert"], [FEST_REL])
        self.assertEqual(zeilen[-1]["date"], datetime.date.today().isoformat())


class ConflictResilienceTests(Fixture):
    """Widerstandsfähigkeit gegen Merge-Konflikte und Syntax-Fehler in data/integrity_lock.json.

    Anlass 21./22.09.2026: PR #342 überschnitt sich mit main in data/integrity_lock.json.
    Beim Merge wurden durch unsaubere Konfliktlösung Metadaten gelöscht und ungültiges
    JSON hinterlassen.
    """

    def test_load_lock_erkennt_git_konfliktmarker(self):
        self.lock_pfad.write_text("<<<<<<< HEAD\n{\"signed_at\": \"alt\"}\n=======\n{\"signed_at\": \"neu\"}\n>>>>>>> branch\n", encoding="utf-8")
        lock = ig.load_lock(self.lock_pfad)
        self.assertEqual(lock.get("_status"), "konflikt")

    def test_load_lock_erkennt_syntaxfehler(self):
        self.lock_pfad.write_text("{\n  \"signed_at\": \"alt\",\n  \"files\": {\n", encoding="utf-8")
        lock = ig.load_lock(self.lock_pfad)
        self.assertEqual(lock.get("_status"), "beschaedigt")

    def test_gate_meldet_konfliktmarker_eindeutig(self):
        self.signieren()
        self.lock_pfad.write_text("<<<<<<< HEAD\n{\"signed_at\": \"alt\"}\n=======\n{\"signed_at\": \"neu\"}\n>>>>>>> branch\n", encoding="utf-8")
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = ig.gate(self.root)
        self.assertEqual(rc, 3)
        self.assertIn("Git-Merge-Konfliktmarker", puffer.getvalue())
        self.assertIn("--set-current", puffer.getvalue())

    def test_gate_meldet_syntaxfehler_eindeutig(self):
        self.signieren()
        self.lock_pfad.write_text("{ \"art\": \"set-current\", ] }", encoding="utf-8")
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = ig.gate(self.root)
        self.assertEqual(rc, 3)
        self.assertIn("ungültiges JSON", puffer.getvalue())
        self.assertIn("--set-current", puffer.getvalue())

    def test_set_current_heilt_merge_konflikt_mit_git_baseline(self):
        self.signieren()
        self.assertEqual(_commit(self.root, "chore: lock committet").returncode, 0)
        # Jetzt simuliere einen Merge-Konflikt auf Arbeitsbaum-Ebene
        self.lock_pfad.write_text("<<<<<<< HEAD\n{\"signed_at\": \"alt\"}\n=======\n{\"signed_at\": \"neu\"}\n>>>>>>> branch\n", encoding="utf-8")
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = ig.set_current(self.root)
        self.assertEqual(rc, 0)
        self.assertIn("Git-Konfliktmarker", puffer.getvalue())
        lock = ig.load_lock(self.lock_pfad)
        self.assertEqual(lock.get("_status"), "ok")
        self.assertEqual(self.driften(), ([], []))

    def test_selftest_erkennt_beschaedigten_lock(self):
        self.signieren()
        self.lock_pfad.write_text("<<<<<<< HEAD\n{\"signed_at\": \"alt\"}\n=======\n{\"signed_at\": \"neu\"}\n>>>>>>> branch\n", encoding="utf-8")
        orig_lock = ig.LOCK
        try:
            ig.LOCK = self.lock_pfad
            fehler = ig._selftest()
            self.assertTrue(any("beschädigt oder enthält Git-Konfliktmarker" in f for f in fehler))
        finally:
            ig.LOCK = orig_lock


class RepoSealTests(unittest.TestCase):
    """Nicht die Attrappe: Passt der ausgelieferte Baum zu seinem Siegel?"""

    def test_ausgelieferter_baum_passt_zum_siegel(self):
        lock = ig.load_lock(ig.LOCK)
        crit_bad, fest_bad = ig.verify_files(ig.ROOT, lock.get("files", {}))
        self.assertEqual(
            (crit_bad, fest_bad), ([], []),
            "Der gesperrte Kern läuft aus dem Siegel. Reparatur – die Herkunft "
            "landet dabei in der Akte: python3 scripts/integrity_guard.py "
            "--set-current, dann data/integrity_lock.json im SELBEN Commit "
            f"mitnehmen. Abweichungen: kritisch={crit_bad}, fest={fest_bad}")

    def test_siegel_kennt_jeden_kritischen_knoten(self):
        lock = ig.load_lock(ig.LOCK)
        unsigniert = sorted(p for p in ig.KRITISCH
                            if (ig.ROOT / p).exists() and p not in lock.get("files", {}))
        self.assertEqual(unsigniert, [], "kritische Knoten ohne Signatur")

    def test_akte_bleibt_gebunden_und_bennbar(self):
        lock = ig.load_lock(ig.LOCK)
        akte = lock["audit"]
        self.assertTrue(akte, "das Siegel ohne Akte ist eine Zahl ohne Grund")
        self.assertLessEqual(len(akte), ig.AUDIT_MAX, "AUDIT_MAX ist die Lesbarkeitsgrenze")
        letzte = akte[-1]
        for feld in ("date", "art", "head", "geaendert"):
            self.assertIn(feld, letzte)
        if letzte["geaendert"]:
            herkunft = {e["pfad"] for e in letzte.get("herkunft", [])}
            self.assertEqual(herkunft, set(letzte["geaendert"]),
                             "wer zeichnet, nennt die Herkunft JEDER gezeichneten Datei")


if __name__ == "__main__":
    unittest.main()
