#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Tests des Bestands-Einzigartigkeits-Diff-Tors (#1060 / #1027).

Der Vorfall, eingefroren (02.–03.11.2026): Derselbe BNetzA-Absatz landete
per Git-Commit (#1017, „69f08c40“) per Handänderung in drei LIVE Gas-
Artikeln. Das Tagesaudit meldete am 03.11. zwei kritische Paare
(16 und 5 geteilte 7-Wort-Phrasen, #1027).

Dieser Snapshot trägt die Historie nicht mehr (flacher Checkout mit
genau einem Objekt); dort existieren weder 69f08c40 noch de4d485f2.
Der Vorfall wird darum aus den zwei WIRKLICH geheilten Artikeln
rekonstruiert: die Heilung entfernte die Passage nicht aus unserem
Korpus-Git, sie entfernte sie aus den Dateien – den Fixture-Korpus
bauen wir deshalb aus genau den dokumentierten Passagen selbst.

Jede Fixture ist git-basiert (`git init` in einem tmpdir), weil das Tor
den Diff gegen die Basis misst; Vergleiche gegen den Arbeitsbaum wären
kein Beweis.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

WURZEL = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(WURZEL, "scripts"))

import check_uniqueness as cu  # noqa: E402
import bestand_einzigartigkeit_gate as beg  # noqa: E402

# Der geteilte BNetzA-Absatz (die in #1027 dokumentierten Sequenzen).
BNETZA = ("Bei einer einseitigen Preisaenderung koennen Verbraucher "
          "grundsaetzlich ohne Frist zum Zeitpunkt der Aenderung kuendigen; "
          "der Vertrag endet am Vortag der Aenderung. Ausnahmen gelten nur mit "
          "Bestaetigung des Wechsels in Textform durch den Versorger.")
BNETZA_U = ("Bei einer einseitigen Preisaenderung koennen Verbraucher "
            "grundsaetzlich ohne Frist zum Zeitpunkt der Aenderung kuendigen; "
            "der Vertrag endet am Vortag der Aenderung.")
# Die fünf geteilten Phrasen zwischen 08-10 und 08-12 kamen aus einem
# KÜRZEREN Kernsatz (die Audit-Ausgabe #1027 nennt ihn „bei weiterem
# Verbrauch je nach Fall Grund oder Ersatzversorgung…“).
KERN = ("Bei weiterem Verbrauch je nach Fall Grund oder Ersatzversorgung "
        "in Betracht ziehen; die Weiterversorgung laeuft bis dahin weiter.")
EIGEN_A = ("Der Testtext ueber Heizlast, Absenkung und Ventilatoren teilt "
           "keine einzige Phrase mit anderen Artikeln und steht am Anfang.")
EIGEN_B = ("Ein zweiter unabhaengiger Text ueber Katzen, Hypotheken und "
           "den Herbst teilt ebenfalls nichts und steht am Ende.")
EIGEN_C = ("Der dritte Text redigiert Trockner, Kombi und Speicherplatz "
           "von Grund auf neu und ist absichtlich eigenstaendig.")

GAS_10 = "2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas"
GAS_12 = "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026"
GAS_24 = "2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen"


def _doc(slug: str, body: str, draft: bool = False) -> str:
    marker = "true" if draft else "false"
    datum = "2026-08-10T08:00:00Z"
    return (f"---\ntitle: \"{slug}\"\ndate: {datum}\ndraft: {marker}\n---\n\n"
            f"{body}\n")


def _korpus(teil_in_12: bool, bnetza_in_24: bool, gas10_extra: str = "") -> dict[str, str]:
    return {
        GAS_12: _doc(GAS_12, (KERN + "\n\n" if teil_in_12 else "") + EIGEN_B),
        GAS_24: _doc(GAS_24, (BNETZA + "\n\n" if bnetza_in_24 else "") + EIGEN_C),
        GAS_10: _doc(GAS_10, EIGEN_A + ("\n\n" + gas10_extra if gas10_extra else "")),
    }


def _bestand(korpus: dict[str, str]) -> dict[str, dict]:
    return {
        f"/tmp/{slug}/index.md": {
            "slug": slug,
            "title": slug,
            "body": cu.clean_body(text),
            "live": "draft: true" not in text,
            "grund": "" if "draft: true" not in text else "draft:true",
            "date": "2026-08-10T08:00:00Z",
        }
        for slug, text in korpus.items()
    }


class GitFixture(unittest.TestCase):
    """Temporäres echtes Git-Repo mit dem Vorfall; je Test frisch."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="uniq-diff-")
        self.root = self.tmp
        self.posterdir = os.path.join(self.root, "content", "posts")
        os.makedirs(self.posterdir)
        self._git("init", "-q")
        self._git("config", "user.email", "test@example.invalid")
        self._git("config", "user.name", "uniq-test")
        self.korpus = _korpus(teil_in_12=True, bnetza_in_24=True)
        self._schreibe(self.korpus)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _git(self, *args):
        return subprocess.run(["git", "-C", self.root, *args],
                              capture_output=True, text=True, check=True)

    def _schreibe(self, korpus: dict[str, str]):
        for slug, text in korpus.items():
            folder = os.path.join(self.posterdir, slug)
            os.makedirs(folder, exist_ok=True)
            with open(os.path.join(folder, "index.md"), "w", encoding="utf-8") as fh:
                fh.write(text)

    def _commit_basis(self):
        self._git("add", "-A")
        self._git("commit", "-q", "-m", "basis (Ende des geheilten Stands)")
        return self._git("rev-parse", "HEAD").stdout.strip()

    def _bestand(self):
        return _bestand(self.korpus)

    def _aendere(self, korpus: dict[str, str]):
        self._schreibe(korpus)


class DirektMessungTests(GitFixture):
    """Die V4-Messung des Tores – ohne Git-Roundtrip (außer Basis)."""

    def test_keine_aenderungen_ist_still(self):
        basis = self._commit_basis()
        funde = beg.befunde([], basis, bestand=self._bestand(), root=self.root)
        self.assertEqual([], funde)

    def test_erzeugung_wird_gemeldet(self):
        """Wider den Vorfall: 08-10 bekommt die Passage → 2 Paare aus #1027."""
        basis = self._commit_basis()
        neu = _korpus(teil_in_12=True, bnetza_in_24=True,
                      gas10_extra=KERN + "\n\n" + BNETZA)
        self._aendere(neu)                       # 08-10 als Live-Artikel geändert
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md"], basis,
                            bestand=_bestand(neu), root=self.root)
        paare = {" ↔ ".join(sorted((f["slug"], f["anderer"]))) for f in funde}
        self.assertIn(f"{GAS_10} ↔ {GAS_12}", paare)
        self.assertIn(f"{GAS_10} ↔ {GAS_24}", paare)
        self.assertEqual(2, len(paare), paare)
        for f in funde:
            self.assertGreaterEqual(f["neu_n"], beg.KRITISCH_AB)

    def test_heilungszustand_bleibt_still(self):
        """Nach der Heilung (Arbeitbaum = Basis): keine Meldung – Beweis."""
        basis = self._commit_basis()
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md"], basis,
                            bestand=self._bestand(), root=self.root)
        self.assertEqual([], funde)

    def test_altlast_wird_nicht_angelastet(self):
        """Bestand MIT geteilter Passage, Diff OHNE Inhalt→Still."""
        korpus = _korpus(teil_in_12=True, bnetza_in_24=True,
                         gas10_extra=KERN + "\n\n" + BNETZA)
        self._schreibe(korpus)
        basis = self._commit_basis()
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md"], basis,
                            bestand=_bestand(korpus), root=self.root)
        self.assertEqual([], funde)

    def test_verstaerkung_wird_gemeldet(self):
        """Alt enthält KERN (Teil), neu enthält KERN+BNETZA → Verstärkt."""
        korpus_teil = _korpus(teil_in_12=True, bnetza_in_24=False,
                              gas10_extra=KERN)
        korpus_teil[GAS_24] = _doc(GAS_24, BNETZA + "\n\n" + EIGEN_C)
        self._schreibe(korpus_teil)   # Basis = 08-10(EIGEN+KERN), 08-24(BNETZA+EIGEN)
        basis = self._commit_basis()
        neu = dict(korpus_teil)
        neu[GAS_10] = _doc(GAS_10, EIGEN_A + "\n\n" + KERN + "\n\n" + BNETZA)
        self._aendere(neu)
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md"], basis,
                            bestand=_bestand(neu), root=self.root)
        verstaerkt = [f for f in funde if f["slug"] == GAS_10]
        self.assertTrue(any(f["anderer"] == GAS_24 for f in verstaerkt), funde)

    def test_abschwaechung_ist_kein_befund(self):
        """Gegenprobe Verstärkung: neu NUR der Teilabsatz → kein Fund."""
        korpus_voll = _korpus(teil_in_12=True, bnetza_in_24=True,
                              gas10_extra=BNETZA)
        self._schreibe(korpus_voll)
        basis = self._commit_basis()
        neu = dict(korpus_voll)
        neu[GAS_10] = _doc(GAS_10, EIGEN_A + "\n\n" + BNETZA_U)
        self._aendere(neu)
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md"], basis,
                            bestand=_bestand(neu), root=self.root)
        self.assertEqual([], funde)

    def test_kanonische_paarung_nur_einmal(self):
        """Beide Seiten geändert → ein Paar, nicht zwei."""
        korpus_voll = _korpus(teil_in_12=True, bnetza_in_24=True,
                              gas10_extra=BNETZA)
        self._schreibe(korpus_voll)
        basis = self._commit_basis()
        neu = dict(korpus_voll)
        # beide Seiten gegeneinander um denselben Block erweitern
        neu[GAS_10] = _doc(GAS_10, EIGEN_A + "\n\n" + BNETZA)
        neu[GAS_24] = _doc(GAS_24, EIGEN_C + "\n\n" + BNETZA)
        self._aendere(neu)
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md", f"content/posts/{GAS_24}/index.md"],
                            basis, bestand=_bestand(neu), root=self.root)
        paare = {tuple(sorted((f["slug"], f["anderer"]))) for f in funde}
        for pair in paare:
            self.assertEqual(
                sum(1 for f in funde if tuple(sorted((f["slug"], f["anderer"]))) == pair),
                1)

    def test_eigener_slug_nie_gegner(self):
        basis = self._commit_basis()
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md"], basis,
                            bestand=self._bestand(), root=self.root)
        for f in funde:
            self.assertNotEqual(f["slug"], f["anderer"])

    def test_leerer_bestand_ist_fail_closed(self):
        basis = self._commit_basis()
        with self.assertRaises(beg.GateFehler):
            beg.befunde([f"content/posts/{GAS_10}/index.md"], basis, bestand={}, root=self.root)

    def test_entwurf_gegner_zaehlt_wie_live(self):
        """Die Vorabaufgabe: Entwurf-gegen-live erzeugt einen Befund."""
        korpus_draft = _korpus(teil_in_12=False, bnetza_in_24=False)
        korpus_draft[GAS_12] = _doc(GAS_12, KERN + "\n\n" + EIGEN_B, draft=True)
        korpus_draft[GAS_10] = _doc(GAS_10, EIGEN_A)
        self._schreibe(korpus_draft)
        basis = self._commit_basis()
        neu = dict(korpus_draft)
        neu[GAS_10] = _doc(GAS_10, EIGEN_A + "\n\n" + KERN)
        self._aendere(neu)
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md"], basis,
                            bestand=_bestand(neu), root=self.root)
        self.assertTrue(any(f["anderer"] == GAS_12 for f in funde), funde)

    def test_echter_vorfall_die_zwei_paare(self):
        """Der Vorfall 69f08c40, rekonstruiert: exakt die zwei #1027-Paare."""
        # Basis trägt NUR die vorgelagerte Belegung (vor dem Commit 69f08c40):
        korpus_vorfall = _korpus(teil_in_12=True, bnetza_in_24=True)
        self._schreibe(korpus_vorfall)
        basis = self._commit_basis()
        # Der Vorfall: 08-10 bekommt BEIDE Bausteine – wie am 02.11.2026.
        neu = _korpus(teil_in_12=True, bnetza_in_24=True,
                      gas10_extra=KERN + "\n\n" + BNETZA)
        self._aendere(neu)                       # worktree = nach dem Commit
        funde = beg.befunde([f"content/posts/{GAS_10}/index.md"], basis,
                            bestand=_bestand(neu), root=self.root)
        paare = {tuple(sorted((f["slug"], f["anderer"]))) for f in funde}
        self.assertEqual(
            {tuple(sorted((GAS_10, GAS_12))), tuple(sorted((GAS_10, GAS_24)))},
            paare, f"die zwei dokumentierten Paare fehlen: {paare}")
        unter = len(cu.ngrams(KERN, cu.PHRASE_LEN))
        voll = len(cu.ngrams(BNETZA, cu.PHRASE_LEN))
        self.assertGreaterEqual(unter, 5)
        self.assertGreaterEqual(voll, 10)

    def test_selftest_laeuft_gruen(self):
        self.assertEqual(0, beg.main(["--selftest"]))


class GitIntegrationTests(GitFixture):
    """Ende-zu-Ende über echte Git-Aufrufe (cat-file/show/diff/ls-files)."""

    def test_git_diff_tor_meldet_und_steht_bei_infrastrukturfehler(self):
        basis = self._commit_basis()
        neu = _korpus(teil_in_12=True, bnetza_in_24=True,
                      gas10_extra=KERN + "\n\n" + BNETZA)
        self._aendere(neu)
        exit_code = beg.main(["--basis", basis, "--root", self.root])
        self.assertEqual(1, exit_code)

    def test_unerreichbare_basis_ist_werkzeugfehler(self):
        with self.assertRaises(beg.GateFehler):
            beg.changed_post_paths("refs/heads/no-such-ref-zulu", root=self.root)


if __name__ == "__main__":
    unittest.main()
