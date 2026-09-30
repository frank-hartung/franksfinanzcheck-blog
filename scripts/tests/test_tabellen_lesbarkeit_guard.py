"""Regressionstests für die Tabellen-Lesbarkeits-Wache (30.09.2026).

Warum diese Tests existieren
----------------------------
Der Schaden, den die Wache verhindert, ist lautlos: Markup und CSS
sind einzeln fehlerfrei, sie treffen sich nur nicht. Die Spar-Matrix
auf ``/pillar/`` lag außerhalb von ``.post-content`` – und genau
dorthin war das komplette Premium-Tabellen-System gescopt. Im Browser
blieb der PaperMod-Reset übrig: fünf Spalten ohne Zellpolster.

Diese Tests halten vier Zusagen fest:

1) **Die Wache misst richtig** – der eingebaute Sabotage-Selbsttest
   (L1–L5) läuft grün, sonst ist jede Aussage wertlos.
2) **Der Bestand ist versorgt** – das ausgelieferte Repository selbst
   erfüllt den Vertrag (0 Funde).
3) **Der Originalschaden wird erkannt** – ein nachgestelltes Repo im
   Zustand „CSS nur unter .post-content" muss L2 auslösen.
4) **Der Markup-Vertrag bleibt** – Spaltenzahl, ``scope`` und
   ``data-label`` der echten Template-Datei stimmen.

Alle Tests laufen ohne Netz, ohne Hugo und ohne Browser.
"""
import importlib.util
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
GUARD = ROOT / "scripts" / "tabellen_lesbarkeit_guard.py"


def _modul():
    spec = importlib.util.spec_from_file_location("tabellen_lesbarkeit_guard", GUARD)
    mod = importlib.util.module_from_spec(spec)
    # Vor dem Ausfuehren registrieren: @dataclass schlaegt sonst nach
    # sich selbst in sys.modules und findet nichts.
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


class TestWache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.mod = _modul()

    def test_selbsttest_gruen(self):
        """Die Sabotage-Proben L1–L5 feuern punktgenau."""
        self.assertEqual(self.mod.selftest(), [])

    def test_bestand_erfuellt_den_vertrag(self):
        """Das ausgelieferte Repo hat keine unversorgte Tabelle."""
        erg = self.mod.pruefe(ROOT)
        self.assertEqual(
            [f"{b.regel}: {b.text}" for b in erg.funde], [],
            "Tabellen-Lesbarkeit: offener Befund im Bestand",
        )

    def test_scope_falle_wird_erkannt(self):
        """Der Originalschaden (CSS nur unter .post-content) löst L2 aus."""
        with tempfile.TemporaryDirectory() as tmp:
            basis = self.mod._mini_repo(
                Path(tmp), self.mod.GUT_TEMPLATE,
                self.mod._nur_im_artikel(self.mod.GUT_CSS),
            )
            regeln = {b.regel for b in self.mod.pruefe(basis).funde}
        self.assertIn("L2", regeln)

    def test_cli_exit_codes(self):
        """--selftest endet mit 0, der Bestandslauf ebenfalls."""
        for args in (["--selftest"], ["--json"]):
            with self.subTest(args=args):
                p = subprocess.run([sys.executable, str(GUARD), *args],
                                   capture_output=True, text=True, cwd=ROOT)
                self.assertEqual(p.returncode, 0, p.stdout + p.stderr)


class TestMarkupVertrag(unittest.TestCase):
    """Die Spar-Matrix im echten Template (ohne Hugo-Build lesbar)."""

    @classmethod
    def setUpClass(cls):
        cls.tpl = (ROOT / "layouts" / "pillar" / "list.html").read_text(encoding="utf-8")

    def test_fuenf_spalten_konsistent(self):
        block = self.tpl[self.tpl.find("<table class=\"ff-tbl ff-spar-matrix-table\""):]
        block = block[:block.find("</table>")]
        self.assertEqual(len(re.findall(r"<col\b", block)), 5)
        self.assertEqual(len(re.findall(r'<th[^>]*scope="col"', block)), 5)

    def test_datenzellen_tragen_feldnamen(self):
        zellen = re.findall(r"<td\b[^>]*>", self.tpl)
        matrix = [z for z in zellen if "data-label=" in z]
        self.assertGreaterEqual(len(matrix), 4,
                                "mobile Kartenansicht braucht data-label je Datenzelle")

    def test_affiliate_knoepfe_bleiben_einmalig(self):
        """Keine zweite Markup-Kopie für Mobil – sonst zählt die
        Werbe-Offenlegung jeden Partnerlink doppelt."""
        self.assertEqual(self.tpl.count('"placement" "spar-matrix"'), 1)


if __name__ == "__main__":
    unittest.main()
