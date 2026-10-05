"""Regressions-Tests: scripts/nachheilung.py – Heilung nach Fremdänderung.

Vorgang WF-A535, Meldung #590 (05.10.2026): Die Content-Engine verlor einen
kompletten Tagesertrag, weil ein parallel bearbeiteter Bestands-Artikel den
Rebase blockierte. Seitdem gibt `git_sync.sh` solche Artikel an den Bestand ab
(die fremde, neuere Fassung gewinnt) und protokolliert sie – und dieses
Werkzeug zieht die maschinelle Heilung auf dem neuen Textstand nach.

Geprüft werden die Versprechen, von denen die Dauerheilung abhängt:

  1. Ohne Protokoll passiert nichts (und das ist kein Fehler).
  2. Das Protokoll ist eine Notiz, keine Befehlsliste: nur echte Artikel
     unter content/posts/<slug>/index.md werden geheilt, alles andere
     (Pfad-Ausbruch, Skripte, gelöschte Artikel) wird verworfen.
  3. Doppelte Einträge heilen einmal.
  4. Der Plan startet nichts; --fix startet exakt den Plan.
  5. Zielgenaue Werkzeuge bekommen jede Datei einzeln, bestandsweite laufen
     genau einmal.
  6. Scheitert ein Werkzeug, bleibt das Protokoll stehen (Exit 1) – der
     nächste Lauf wiederholt den Auftrag.
  7. Nach vollständigem Erfolg ist das Protokoll geschlossen (Exit 0).
  8. Kein Befehl läuft über eine Shell, keiner zieht eine Geldfläche
     (KI/Online/Premium-Engine) nach sich.

Ausführung:  python3 -m unittest scripts.tests.test_nachheilung -v
"""

import contextlib
import io
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PFAD = REPO_ROOT / "scripts" / "nachheilung.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))
import nachheilung  # noqa: E402  (Pfad muss vorher stehen)


class _Proc:
    def __init__(self, rc=0, stdout=""):
        self.returncode = rc
        self.stdout = stdout
        self.stderr = ""


class NachheilungBasis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.wurzel = Path(self.tmp.name)
        self.artikel = "content/posts/2026-10-05-probe/index.md"
        ziel = self.wurzel / self.artikel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text("---\ntitle: Probe\ndraft: false\n---\nText\n",
                        encoding="utf-8")
        self.protokoll = self.wurzel / nachheilung.STANDARD_PROTOKOLL

    def schreibe(self, inhalt):
        self.protokoll.write_text(inhalt, encoding="utf-8")

    def lage(self):
        return nachheilung.lies_lage(self.protokoll, self.wurzel)


class EinlesenTests(NachheilungBasis):
    def test_ohne_protokoll_keine_arbeit(self):
        lage = self.lage()
        self.assertFalse(lage.hat_arbeit)
        self.assertEqual(nachheilung.plane(lage.artikel), [])

    def test_nur_echte_artikel_werden_geheilt(self):
        self.schreibe(
            f"{self.artikel}\n"
            "../../etc/passwd\n"
            "scripts/git_sync.sh\n"
            "content/posts/gibt-es-nicht/index.md\n"
            "RELEASE-SCORECARD.md\n"
        )
        lage = self.lage()
        self.assertEqual(lage.artikel, [self.artikel])
        self.assertEqual(len(lage.verworfen), 4)

    def test_doppelte_eintraege_heilen_einmal(self):
        self.schreibe(f"{self.artikel}\n{self.artikel}\n{self.artikel}\n")
        self.assertEqual(self.lage().artikel, [self.artikel])

    def test_kommentare_und_leerzeilen_stoeren_nicht(self):
        self.schreibe(f"# Protokoll\n\n{self.artikel}\n\n")
        self.assertEqual(self.lage().artikel, [self.artikel])


class PlanUndAusfuehrungTests(NachheilungBasis):
    def test_plan_startet_nichts(self):
        self.schreibe(f"{self.artikel}\n")
        aufrufe = []

        def runner(befehl, **_kw):
            aufrufe.append(befehl)
            return _Proc()

        befehle = nachheilung.plane(self.lage().artikel)
        self.assertEqual(aufrufe, [], "Planen darf kein Werkzeug starten")
        self.assertTrue(befehle)
        self.assertIs(runner, runner)  # Runner bleibt ungenutzt – das ist der Punkt.

    def test_zielgenau_je_datei_bestandsweit_genau_einmal(self):
        zweiter = "content/posts/2026-10-05-zweite-probe/index.md"
        (self.wurzel / zweiter).parent.mkdir(parents=True, exist_ok=True)
        (self.wurzel / zweiter).write_text("---\ntitle: Zwei\n---\n", encoding="utf-8")
        self.schreibe(f"{self.artikel}\n{zweiter}\n")

        befehle = nachheilung.plane(self.lage().artikel)
        zielgenau = [w for w in nachheilung.KETTE if w.zielgenau]
        bestandsweit = [w for w in nachheilung.KETTE if not w.zielgenau]
        self.assertEqual(len(befehle), len(zielgenau) * 2 + len(bestandsweit))

        for wz in bestandsweit:
            treffer = [b for b in befehle if b[1].endswith(wz.skript)]
            self.assertEqual(len(treffer), 1,
                             f"{wz.skript} darf genau einmal laufen")
        for wz in zielgenau:
            treffer = [b for b in befehle if b[1].endswith(wz.skript)]
            self.assertEqual(len(treffer), 2, f"{wz.skript} fehlt eine Datei")
            self.assertTrue(all(wz.flagge in b for b in treffer))

    def test_kein_shellaufruf_und_keine_geldflaeche(self):
        self.schreibe(f"{self.artikel}\n")
        for befehl in nachheilung.plane(self.lage().artikel):
            self.assertIsInstance(befehl, list)
            self.assertEqual(befehl[0], sys.executable)
            zeile = " ".join(befehl)
            for meta in (";", "&&", "||", "|", "`", "$("):
                self.assertNotIn(meta, zeile)
        for wz in nachheilung.KETTE:
            self.assertNotIn("--ai", wz.argumente)
            self.assertNotIn("--oeffentlich", wz.argumente)
            self.assertTrue((REPO_ROOT / "scripts" / wz.skript).is_file(),
                            f"Werkzeug fehlt: {wz.skript}")


class ProtokollLebenszyklusTests(NachheilungBasis):
    def _main(self, argv, runner_rc=0):
        """main() mit injiziertem Runner und temporärer Wurzel."""
        echt_run = subprocess.run
        aufrufe = []

        def runner(befehl, **_kw):
            aufrufe.append(befehl)
            return _Proc(rc=runner_rc, stdout="Fund" if runner_rc else "")

        alt_root, alt_scripts = nachheilung.ROOT, nachheilung.SCRIPTS
        nachheilung.ROOT = self.wurzel
        nachheilung.SCRIPTS = REPO_ROOT / "scripts"
        subprocess.run = runner
        try:
            with contextlib.redirect_stdout(io.StringIO()) as puffer:
                rc = nachheilung.main(argv)
        finally:
            subprocess.run = echt_run
            nachheilung.ROOT, nachheilung.SCRIPTS = alt_root, alt_scripts
        return rc, aufrufe, puffer.getvalue()

    def test_hat_arbeit_meldet_bedarf_per_exitcode(self):
        rc, _, _ = self._main(["--hat-arbeit"])
        self.assertEqual(rc, 1, "ohne Protokoll liegt keine Arbeit an")
        self.schreibe(f"{self.artikel}\n")
        rc, _, _ = self._main(["--hat-arbeit"])
        self.assertEqual(rc, 0, "mit Protokoll liegt Arbeit an")

    def test_erfolg_schliesst_das_protokoll(self):
        self.schreibe(f"{self.artikel}\n")
        rc, aufrufe, _ = self._main(["--fix"])
        self.assertEqual(rc, 0)
        self.assertTrue(aufrufe)
        self.assertFalse(self.protokoll.exists(),
                         "nach erfolgreicher Heilung ist der Auftrag erledigt")

    def test_fehlschlag_laesst_den_auftrag_stehen(self):
        self.schreibe(f"{self.artikel}\n")
        rc, _, ausgabe = self._main(["--fix"], runner_rc=1)
        self.assertEqual(rc, 1)
        self.assertTrue(self.protokoll.exists(),
                        "ein unerledigter Auftrag darf nicht verschwinden")
        self.assertIn("Protokoll bleibt erhalten", ausgabe)

    def test_plan_laesst_protokoll_unberuehrt(self):
        self.schreibe(f"{self.artikel}\n")
        rc, aufrufe, _ = self._main([])
        self.assertEqual(rc, 0)
        self.assertEqual(aufrufe, [], "Plan ruft keine Werkzeuge auf")
        self.assertTrue(self.protokoll.exists())

    def test_protokoll_nur_mit_unsinn_ist_ein_befund(self):
        self.schreibe("../../etc/passwd\nscripts/git_sync.sh\n")
        rc, aufrufe, _ = self._main(["--fix"])
        self.assertEqual(rc, 3, "unbrauchbares Protokoll muss auffallen")
        self.assertEqual(aufrufe, [])


class SelbsttestTests(unittest.TestCase):
    def test_selbsttest_ist_gruen_und_leise(self):
        res = subprocess.run([sys.executable, str(MODULE_PFAD), "--selftest"],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
        self.assertIn("Selbsttest grün", res.stdout)
        self.assertNotIn("✅ zeit_rechtschreibung", res.stdout,
                         "ein Selbsttest darf nicht wie ein echter Lauf aussehen")


if __name__ == "__main__":
    unittest.main()
