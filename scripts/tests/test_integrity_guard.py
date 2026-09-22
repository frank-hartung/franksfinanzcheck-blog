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
import os
import shutil
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


class SiegelZustandTests(Fixture):
    """Issue #346 – das SIEGEL selbst ist prüfbar geworden.

    Der Vorfall: Ein Merge hat zwei Lock-Fassungen zusammengesetzt. Das
    Ergebnis war syntaktisch kaputt (Byte 7.171), `load_lock()` verschluckte
    es zu „0 Dateien gelockt", und gemeldet wurde das Symptom („6 kritische
    Knoten ohne Signatur") statt der Ursache. Diese Tests halten fest, dass
    ein beschädigtes Siegel ein EIGENER, benannter Befund ist – und dass auch
    ein syntaktisch GÜLTIGER Zusammenschnitt auffällt (Kette + Map-Prüfsumme).
    """

    def bestes_siegel(self):
        self.signieren()
        return json.loads(self.lock_pfad.read_text(encoding="utf-8"))

    def test_gesundes_siegel_ist_verkettet_und_verankert(self):
        dokument = self.bestes_siegel()
        self.assertEqual(ig.lock_zustand(self.lock_pfad)["zustand"], ig.ZUSTAND_OK)
        self.assertEqual(dokument["schema"], ig.SCHEMA)
        self.assertEqual(dokument["files_sha256"], ig.files_sha(dokument["files"]))
        letzte = dokument["audit"][-1]
        self.assertEqual(letzte["files_sha256"], ig.files_sha(dokument["files"]))
        # Kette: jeder Verweis trifft die Prüfsumme seines Vorgängers.
        for vor, jetzt in zip(dokument["audit"], dokument["audit"][1:]):
            self.assertEqual(jetzt["prev_sha256"], ig._eintrag_sha(vor))

    def test_zerstoertes_siegel_nennt_bruchstelle_und_muster(self):
        """Der echte Vorfall als Form: vorne vollständig, hinten fremder Rest."""
        self.signieren()
        gut = self.lock_pfad.read_text(encoding="utf-8")
        self.lock_pfad.write_text(
            gut[: int(len(gut) * 0.7)] + "\n      ]\n    }\n  ]\n}\n",
            encoding="utf-8")
        befund = ig.lock_zustand(self.lock_pfad)
        self.assertEqual(befund["zustand"], ig.ZUSTAND_BESCHAEDIGT)
        self.assertIsInstance(befund["offset"], int)
        self.assertEqual(befund["verdacht"], "zusammenschnitt",
                         "ein fremder Rest hinter der Bruchstelle ist ein "
                         "Zusammenschnitt, kein Schreibabbruch")
        self.assertEqual(befund["groesse"], len(self.lock_pfad.read_bytes()))
        self.assertIn("zusammengesetzt", " ".join(befund["detail"]))
        self.assertNotIn("zusammen-gesetzt", " ".join(befund["detail"]),
                         "kein Trennstrich-Artefakt im Klartext")

    def test_abbruch_wird_als_abbruch_erkannt(self):
        self.signieren()
        gut = self.lock_pfad.read_text(encoding="utf-8")
        self.lock_pfad.write_text(gut[: int(len(gut) * 0.7)], encoding="utf-8")
        befund = ig.lock_zustand(self.lock_pfad)
        self.assertEqual(befund["zustand"], ig.ZUSTAND_BESCHAEDIGT)
        self.assertEqual(befund["verdacht"], "abbruch",
                         "eine Datei, die AN der Bruchstelle endet, ist ein "
                         "abgebrochener Schreibvorgang")

    def test_zusammenschnitt_mit_gueltigem_json_ist_eine_chimaere(self):
        """Der gefährliche Fall: es PARST – und ist trotzdem aus zwei Ständen."""
        alt = self.bestes_siegel()
        self.schreibe(FEST_REL, "print('zweite generation')\n")
        _commit(self.root, "fix: Änderung vor der zweiten Signatur")
        self.signieren()
        zweite = json.loads(self.lock_pfad.read_text(encoding="utf-8"))
        gemischt = dict(alt)
        gemischt["audit"] = list(alt["audit"][:-1]) + [zweite["audit"][-1]]
        self.lock_pfad.write_text(json.dumps(gemischt, indent=2) + "\n",
                                  encoding="utf-8")
        json.loads(self.lock_pfad.read_text(encoding="utf-8"))   # parst!
        befund = ig.lock_zustand(self.lock_pfad)
        self.assertEqual(befund["zustand"], ig.ZUSTAND_CHIMAERE)
        self.assertTrue(any("ANDEREN" in d or "Map" in d for d in befund["detail"]))

    def test_gebrochene_kette_ist_eine_chimaere(self):
        dokument = self.bestes_siegel()
        dokument["audit"][0]["head"] = "0000000"
        self.lock_pfad.write_text(json.dumps(dokument, indent=2) + "\n",
                                  encoding="utf-8")
        self.assertEqual(ig.lock_zustand(self.lock_pfad)["zustand"],
                         ig.ZUSTAND_CHIMAERE)

    def test_getrimmte_akte_bleibt_gesund(self):
        """AUDIT_MAX kappt die Akte – die Kette muss das aushalten."""
        for i in range(ig.AUDIT_MAX + 4):
            self.schreibe(FEST_REL, f"print({i})\n")
            _commit(self.root, f"fix: Änderung {i}")
            self.signieren()
        dokument = json.loads(self.lock_pfad.read_text(encoding="utf-8"))
        self.assertEqual(len(dokument["audit"]), ig.AUDIT_MAX)
        self.assertEqual(ig.lock_zustand(self.lock_pfad)["zustand"], ig.ZUSTAND_OK)
        self.assertIsNone(dokument["audit"][0]["prev_sha256"],
                          "der älteste erhaltene Eintrag beginnt die Kette")

    def test_legacy_siegel_bleibt_gueltig(self):
        """Vor dem 22.09.2026 signierte Fassungen bleiben benutzbar."""
        self.signieren()
        dokument = json.loads(self.lock_pfad.read_text(encoding="utf-8"))
        dokument.pop("schema")
        dokument.pop("files_sha256")
        dokument.pop("audit_start_sha256")
        for eintrag in dokument["audit"]:
            eintrag.pop("prev_sha256", None)
            eintrag.pop("files_sha256", None)
        self.lock_pfad.write_text(json.dumps(dokument, indent=2) + "\n",
                                  encoding="utf-8")
        self.assertEqual(ig.lock_zustand(self.lock_pfad)["zustand"],
                         ig.ZUSTAND_LEGACY)
        self.assertEqual(self.driften(), ([], []),
                         "ein Legacy-Siegel muss weiter tragen")

    def test_load_lock_verschluckt_den_schaden_nicht(self):
        self.signieren()
        self.lock_pfad.write_text('{"files": ', encoding="utf-8")
        lock = ig.load_lock(self.lock_pfad)
        self.assertEqual(lock.get("files"), {})
        self.assertEqual(lock["_zustand"]["zustand"], ig.ZUSTAND_BESCHAEDIGT,
                         "die Diagnose reist mit – kein stilles „leeres Siegel\"")


class ReparaturTests(Fixture):
    """Ein beschädigtes Siegel wird BELEGT geheilt – oder gar nicht.

    Der Unterschied zum Signieren ist der Nachweis: Quelle ist der committete
    Stand, die lokale Historie oder die Bergung aus dem Artefakt – und bei
    der Bergung muss die geborgene Datei-Map den Baum exakt und vollständig
    decken. Sonst bleibt es HARD STOP (Mensch).
    """

    def vorfall_bauen(self):
        """Gültiges Siegel committen, dann exakt wie am 21.09. verlieren."""
        self.signieren()
        _commit(self.root, "chore(integrity): gültiges Siegel committet")
        gut = self.lock_pfad.read_text(encoding="utf-8")
        self.lock_pfad.write_text(
            gut[: int(len(gut) * 0.7)] + "\n      ]\n    }\n  ]\n}\n",
            encoding="utf-8")
        _commit(self.root, "chore: Siegel zusammengesetzt (Vorfall)")
        return gut

    def test_reparieren_nennt_die_quelle_und_zeichnet_nichts_neu(self):
        gut = self.vorfall_bauen()
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            self.assertEqual(ig.lock_reparatur(self.root), 0)
        text = puffer.getvalue()
        self.assertIn("Quelle:", text)
        self.assertEqual(ig.lock_zustand(self.lock_pfad)["zustand"], ig.ZUSTAND_OK)
        self.assertEqual(self.driften(), ([], []))
        akte = ig.load_lock(self.lock_pfad)["audit"][-1]
        self.assertEqual(akte["art"], "repair")
        self.assertEqual(akte["geaendert"], [],
                         "eine Reparatur zeichnet KEINE Datei neu")
        self.assertIn(akte["quelle"]["art"], ("git-head", "git-historie", "bergung"))
        self.assertEqual(akte["beschaedigung"]["verdacht"], "zusammenschnitt")
        self.assertEqual(json.loads(gut)["files"], ig.load_lock(self.lock_pfad)["files"],
                         "die reparierte Map ist die belegte Map")

    def test_reparieren_hinterlaesst_historie_und_ist_konvergent(self):
        self.vorfall_bauen()
        with contextlib.redirect_stdout(io.StringIO()):
            ig.lock_reparatur(self.root)
            vorher = ig.sha256_file(self.lock_pfad)
            self.assertEqual(ig.lock_reparatur(self.root), 0)
        zeilen = [json.loads(z) for z in
                  self.history_pfad.read_text(encoding="utf-8").splitlines() if z.strip()]
        self.assertEqual(zeilen[-1]["modus"], "repair")
        self.assertIsInstance(zeilen[-1]["kritisch"], int)
        self.assertIsInstance(zeilen[-1]["fest"], int)
        self.assertEqual(ig.sha256_file(self.lock_pfad), vorher,
                         "zweite Reparatur darf nichts mehr ändern")

    def test_bergung_deckt_den_baum_nicht_und_lehnt_ab(self):
        """Ohne belegte Quelle und mit echtem Drift: kein Automatik-Segen."""
        self.signieren()
        self.schreibe(FEST_REL, "print('ohne Signatur')\n")
        _commit(self.root, "fix: Änderung VOR dem Siegelverlust")
        _commit(self.root, "chore: nichts")
        gut = self.lock_pfad.read_text(encoding="utf-8")
        self.lock_pfad.write_text(gut[: int(len(gut) * 0.7)] + "\n]\n}", encoding="utf-8")
        _commit(self.root, "chore: Siegel zerstört (und Baum steht im Drift)")
        # Eine Historie-Quelle gibt es hier sehr wohl – nur hilft sie nicht
        # gegen echten Drift: Sie stellt den belegten Stand her, die
        # Abweichung BLEIBT und wird gemeldet, statt sie zu überzeichnen.
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = ig.lock_reparatur(self.root)
        self.assertEqual(rc, 1, "FEST-Drift nach der Reparatur = Sichtung (1)")
        kritisch, fest = self.driften()
        self.assertEqual((kritisch, fest), ([], [FEST_REL]))
        self.assertTrue(any(w in puffer.getvalue() for w in
                            ("bleibt Drift", "HARD STOP")),
                        "kein stiller Automatik-Lauf bei Drift")

    def test_bergung_im_flachen_klon_prueft_gegen_den_baum(self):
        """Der echte Produktionsfall: flacher Klon (fetch-depth 1), keine
        gültige Fassung in der Historie, nur das beschädigte Artefakt. Dann
        entscheidet der BAUM, ob geborgen werden darf – deckt ihn die
        geborgene Map nicht exakt, gibt es keine Automatik."""
        from pathlib import Path as _P
        self.signieren()
        gut = self.lock_pfad.read_text(encoding="utf-8")
        self.lock_pfad.write_text(
            gut[: int(len(gut) * 0.7)] + "\n      ]\n    }\n  ]\n}\n",
            encoding="utf-8")
        _commit(self.root, "chore: Siegel zusammengesetzt (Vorfall)")
        with tempfile.TemporaryDirectory(prefix="ffc-flach-") as td:
            flach = _P(td) / "repo"
            klon = _git(self.root, "clone", "-q", "--depth", "1",
                        "file://" + str(self.root), str(flach))
            self.assertEqual(klon.returncode, 0, klon.stderr)
            _git(flach, "config", "user.email", "t@example.org")
            _git(flach, "config", "user.name", "Test")
            self.assertEqual(_git(flach, "rev-parse",
                                  "--is-shallow-repository").stdout.strip(), "true")
            fassungen = _git(flach, "log", "--format=%H", "--",
                             "data/integrity_lock.json").stdout.split()
            self.assertEqual(len(fassungen), 1,
                             "der flache Klon kennt nur die beschädigte Fassung")
            ziel = flach / "data" / "integrity_lock.json"
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                self.assertEqual(ig.lock_reparatur(flach), 0)
            self.assertIn("bergung", puffer.getvalue())
            self.assertEqual(ig.lock_zustand(ziel)["zustand"], ig.ZUSTAND_OK)
            self.assertEqual(ig.verify_files(flach, ig.load_lock(ziel)["files"]),
                             ([], []), "geborgenes Siegel deckt den Baum")
            akte = ig.load_lock(ziel)["audit"][-1]
            self.assertEqual(akte["quelle"]["art"], "bergung")
            self.assertEqual(akte["geaendert"], [])

    def test_konfliktmarker_im_siegel_erkannt_und_repariert(self):
        """Git-Merge-Konfliktmarker im Siegel werden erkannt und belegt repariert."""
        self.signieren()
        _commit(self.root, "chore: gültiges Siegel")
        self.lock_pfad.write_text("<<<<<<< HEAD\n{\"schema\": 2}\n=======\n{\"schema\": 2}\n>>>>>>> branch\n",
                                 encoding="utf-8")
        befund = ig.lock_zustand(self.lock_pfad)
        self.assertEqual(befund["zustand"], ig.ZUSTAND_BESCHAEDIGT)
        self.assertEqual(befund.get("verdacht"), "konfliktmarker")
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rc = ig.lock_reparatur(self.root)
        self.assertEqual(rc, 0)
        self.assertIn("SIEGEL REPARIERT", puffer.getvalue())

    def test_keine_quelle_ist_ein_hartes_stoppen(self):
        """Kaputtes Siegel ohne jede belegte Quelle: Exit 3, nichts geschrieben."""
        (self.root / "data").mkdir(exist_ok=True)
        self.lock_pfad.write_text('{"files": ', encoding="utf-8")
        _commit(self.root, "chore: kaputtes Siegel ohne Vorgeschichte")
        vorher = ig.sha256_file(self.lock_pfad)
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            self.assertEqual(ig.lock_reparatur(self.root), 3)
        self.assertIn("KEINE BELEGTE QUELLE", puffer.getvalue())
        self.assertIn("--set-current", puffer.getvalue(),
                      "ein Mensch braucht den Weg, nicht nur das Verbot")
        self.assertEqual(ig.sha256_file(self.lock_pfad), vorher)

    def test_laufzeitmutation_des_siegels_wird_aus_head_geheilt(self):
        """Sind nur die Bytes IM BAUM zerstört, ist die Quelle der committete
        Stand – die Trümmer im Arbeitsbaum werden niemals Quelle."""
        self.signieren()
        _commit(self.root, "chore(integrity): gültiges Siegel committet")
        gutes_siegel = self.lock_pfad.read_bytes()
        self.lock_pfad.write_bytes(b'{"files": ')          # nur im Arbeitsbaum
        self.assertFalse(ig.stand_gleich_head(self.root, "data/integrity_lock.json"))
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            self.assertEqual(ig.lock_reparatur(self.root), 0)
        self.assertIn("git-head", puffer.getvalue())
        wiederhergestellt = json.loads(self.lock_pfad.read_text(encoding="utf-8"))
        self.assertEqual(wiederhergestellt["files"],
                         json.loads(gutes_siegel)["files"],
                         "die belegte Datei-Map ist wieder da")
        self.assertEqual(wiederhergestellt["audit"][-1]["art"], "repair")
        self.assertEqual(wiederhergestellt["audit"][-1]["geaendert"], [],
                         "eine Reparatur zeichnet keine Datei neu")
        self.assertEqual(self.driften(), ([], []))

    def test_ohne_committete_quelle_bleibt_es_hart(self):
        """Ist AUCH der committete und historische Stand kaputt und nichts zu
        bergen, gibt es keinen Automatik-Segen – nur den menschlichen Weg."""
        (self.root / "data").mkdir(exist_ok=True)
        self.lock_pfad.write_text('{"files": ', encoding="utf-8")
        _commit(self.root, "chore: kaputtes Siegel ohne Vorgeschichte")
        vorher = ig.sha256_file(self.lock_pfad)
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            self.assertEqual(ig.lock_reparatur(self.root), 3)
        self.assertIn("KEINE BELEGTE QUELLE", puffer.getvalue())
        self.assertEqual(ig.sha256_file(self.lock_pfad), vorher)

    def test_heilen_repariert_das_siegel_und_faehrt_weiter(self):
        """Genau der Vorfall vom 21.09.2026: Der erste Engine-Schritt heilt
        das Siegel selbst, statt die Produktion zu stoppen."""
        self.vorfall_bauen()
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            self.assertEqual(ig.heilen(self.root), 0)
        self.assertEqual(ig.lock_zustand(self.lock_pfad)["zustand"], ig.ZUSTAND_OK)
        self.assertEqual(self.driften(), ([], []))
        self.assertIn("SIEGEL REPARIERT", puffer.getvalue())

    def test_gate_ist_read_only_und_nennt_den_weg(self):
        self.vorfall_bauen()
        vorher = {p: ig.sha256_file(p) for p in (self.lock_pfad, self.history_pfad)}
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            self.assertEqual(ig.gate(self.root), 3)
        text = puffer.getvalue()
        self.assertIn("Siegel", text)
        self.assertIn("--repair-lock", text)
        self.assertIn("Byte", text, "die Bruchstelle gehört in die Meldung")
        for pfad, sha in vorher.items():
            self.assertEqual(ig.sha256_file(pfad), sha,
                             "das Gate bleibt read-only")


class SchreibsicherheitTests(Fixture):
    """Ein abgebrochener Lauf darf NIE ein halbes Siegel hinterlassen.

    Das alte `Path.write_text()` kürzte die Zieldatei zuerst; ein Kill oder
    Runner-Timeout mitten im Vorgang hinterließ genau die Trümmer, die am
    21.09.2026 die Produktion gestoppt haben. Jetzt: daneben schreiben,
    umbenennen, zurücklesen – oder den alten Stand behalten.
    """

    def test_abbruch_laesst_den_alten_stand_stehen(self):
        self.signieren()
        vorher = self.lock_pfad.read_bytes()
        dokument = json.loads(self.lock_pfad.read_text(encoding="utf-8"))
        neuer_eintrag = {"date": datetime.date.today().isoformat(),
                         "art": "abriss", "head": ig.git_head(self.root),
                         "geaendert": []}
        echt = os.replace
        os.replace = lambda *_a, **_k: (_ for _ in ()).throw(OSError("Kill simuliert"))
        try:
            ok, meldung = ig.lock_schreiben(self.root, ig._lock_dokument(
                self.root, dokument["files"], dokument["audit"], neuer_eintrag))
        finally:
            os.replace = echt
        self.assertFalse(ok, "ein abgebrochener Schreibvorgang ist kein Erfolg")
        self.assertIn("alter Stand bleibt", meldung)
        self.assertEqual(self.lock_pfad.read_bytes(), vorher,
                         "das Siegel muss Byte für Byte unverändert sein")
        self.assertFalse((self.root / "data" / "integrity_lock.json.tmp").exists(),
                         "kein Temp-Rest nach dem Abbruch")

    def test_ungesundes_siegel_wird_nicht_geschrieben(self):
        self.signieren()
        vorher = self.lock_pfad.read_bytes()
        dokument = json.loads(self.lock_pfad.read_text(encoding="utf-8"))
        dokument["files_sha256"] = "0" * 64          # Map-Prüfsumme verbogen
        ok, meldung = ig.lock_schreiben(self.root, dokument)
        self.assertFalse(ok)
        self.assertIn("verworfen", meldung)
        self.assertEqual(self.lock_pfad.read_bytes(), vorher)

    def test_rueckleseprobe_prueft_die_platte(self):
        self.signieren()
        vorher = self.lock_pfad.read_bytes()
        echt = ig._lock_text
        # Ein Text, der zwar schreibt, aber als Siegel ungesund zurückkommt.
        ig._lock_text = lambda daten: '{"files": {}, "audit": []}\n'
        try:
            ok, meldung = ig.lock_schreiben(self.root, {"files": {"a": "b" * 32},
                                                        "audit": []})
        finally:
            ig._lock_text = echt
        self.assertFalse(ok, "was nicht gesund zurückkommt, wird nicht signiert")
        self.assertEqual(self.lock_pfad.read_bytes(), vorher)

    def test_signieren_scheitert_laut_statt_still(self):
        """Eine Unterschrift, die nicht auf der Platte steht, ist keine."""
        self.signieren()
        dokument = json.loads(self.lock_pfad.read_text(encoding="utf-8"))
        echt = ig._lock_text
        ig._lock_text = lambda daten: "{ kaputt"
        try:
            with self.assertRaises(ig.LockSchreibfehler):
                ig.signieren(self.root, grund="test")
        finally:
            ig._lock_text = echt
        self.assertEqual(json.loads(self.lock_pfad.read_text(encoding="utf-8"))["files"],
                         dokument["files"])


class CliTests(unittest.TestCase):
    """Der Aufrufvertrag, den die Workflows nutzen: Flag → Exit-Code → Meldung.

    Die übrigen Tests rufen Funktionen direkt auf. Genau das wäre die zweite
    Wahrheit: In der CI startet ein Subprozess mit Flags. Hier läuft die
    KOPIE des Guards in einem fremden Mini-Repo (`ROOT` folgt der Datei),
    also exakt so, wie die Engine sie startet.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix="ffc-cli-")
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        (self.root / "scripts").mkdir(parents=True)
        shutil.copy(ROOT / "scripts" / "integrity_guard.py",
                    self.root / "scripts" / "integrity_guard.py")
        (self.root / "hugo.toml").write_text("baseURL = '/'\n", encoding="utf-8")
        (self.root / "scripts" / "blog_doctor.py").write_text(
            "print('visite')\n", encoding="utf-8")
        _git(self.root, "init", "-q")
        self.assertEqual(_commit(self.root, "fixture").returncode, 0)
        self.lock_pfad = self.root / "data" / "integrity_lock.json"

    def lauf(self, *args):
        return subprocess.run([sys.executable, "scripts/integrity_guard.py", *args],
                              cwd=str(self.root), capture_output=True, text=True)

    def test_selftest_flag_ist_gruen_und_schreibt_nichts(self):
        # Ohne Siegel meldet der Beweis-Modus das Fehlen des Siegels (Exit 2,
        # Hausentscheidung). Erst signieren, dann beweisen – und dann darf
        # NICHTS mehr geschrieben werden.
        self.assertEqual(self.lauf("--set-current").returncode, 0)
        vorher = self.lock_pfad.read_bytes()
        ergebnis = self.lauf("--selftest")
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("Kern-Beweis", ergebnis.stdout)
        self.assertEqual(self.lock_pfad.read_bytes(), vorher,
                         "Beweisläufe schreiben nichts")
        self.assertFalse(
            (self.root / "data" / "integrity_probe_tmp.json").exists(),
            "der Beweis-Modus darf den Baum nicht einmal probehalber anfassen")

    def test_set_current_und_gate(self):
        self.assertEqual(self.lauf("--set-current").returncode, 0)
        self.assertEqual(self.lauf("--gate").returncode, 0)
        (self.root / "hugo.toml").write_text("baseURL = '/neu/'\n", encoding="utf-8")
        _commit(self.root, "feat: kritischer Kern ohne Signatur")
        rot = self.lauf("--gate")
        self.assertEqual(rot.returncode, 3)
        self.assertIn("--set-current", rot.stdout)
        self.assertEqual(self.lauf("--drift-audit").returncode, 3)
        self.assertEqual(self.lauf("--heal").returncode, 3,
                         "KRITISCH bleibt Handarbeit")

    def test_repair_lock_flag_heilt_den_vorfall(self):
        self.assertEqual(self.lauf("--set-current").returncode, 0)
        _commit(self.root, "chore(integrity): gültiges Siegel committet")
        gut = self.lock_pfad.read_text(encoding="utf-8")
        self.lock_pfad.write_text(
            gut[: int(len(gut) * 0.7)] + "\n      ]\n    }\n  ]\n}\n",
            encoding="utf-8")
        _commit(self.root, "chore: Siegel zusammengesetzt (Vorfall)")
        ergebnis = self.lauf("--repair-lock")
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stdout + ergebnis.stderr)
        self.assertIn("SIEGEL REPARIERT", ergebnis.stdout)
        self.assertIn("Bruchstelle", ergebnis.stdout)
        self.assertEqual(self.lauf("--gate").returncode, 0)

    def test_repair_lock_dry_run_schreibt_nichts(self):
        self.assertEqual(self.lauf("--set-current").returncode, 0)
        _commit(self.root, "chore(integrity): gültiges Siegel committet")
        gut = self.lock_pfad.read_text(encoding="utf-8")
        self.lock_pfad.write_text(gut[: int(len(gut) * 0.7)] + "\n]\n}", encoding="utf-8")
        vorher = self.lock_pfad.read_bytes()
        ergebnis = self.lauf("--repair-lock", "--dry-run")
        self.assertEqual(ergebnis.returncode, 0)
        self.assertIn("dry-run", ergebnis.stdout)
        self.assertEqual(self.lock_pfad.read_bytes(), vorher)


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

    def test_ausgeliefertes_siegel_ist_verkettet_und_gesund(self):
        """Issue #346: Ein Siegel, das nicht selbst prüfbar ist, ist kein Siegel."""
        befund = ig.lock_zustand(ig.LOCK)
        self.assertIn(befund["zustand"], (ig.ZUSTAND_OK, ig.ZUSTAND_LEGACY),
                      "das ausgelieferte Siegel ist nicht gesund: "
                      f"{befund['zustand']} – {befund.get('detail')}. "
                      "Reparatur: python3 scripts/integrity_guard.py --repair-lock")
        if befund["zustand"] == ig.ZUSTAND_OK:
            daten = json.loads(ig.LOCK.read_text(encoding="utf-8"))
            self.assertEqual(daten.get("schema"), ig.SCHEMA)
            self.assertEqual(daten["files_sha256"], ig.files_sha(daten["files"]))
            self.assertEqual(daten["audit"][-1].get("files_sha256"),
                             ig.files_sha(daten["files"]))

    def test_ausgeliefertes_siegel_ist_committet(self):
        """Die Reparatur gehört in den SELBEN Commit wie das Siegel."""
        self.assertTrue(ig.stand_gleich_head(ig.ROOT, "data/integrity_lock.json"),
                        "data/integrity_lock.json weicht von HEAD ab – das "
                        "Siegel muss mit seinem Beleg committet werden")

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
