"""CLI-Vertrag von `generate_covers.py` (Befund 15.11.2026).

WARUM DIESER TEST EXISTIERT
--------------------------
Bis zum 15.11.2026 las das Skript seine Schalter per `"--flag" in sys.argv`.
Damit fiel jeder nicht erkannte Aufruf in den VOLLLAUF:

  * `--help` erzeugte keinen Hilfetext, sondern renderte Cover und schrieb
    `data/lcp_images.json` und `data/fcp_images.json` neu.
  * ein Tippfehler (`--frce`) tat dasselbe, statt zu meckern.
  * `--slug` ohne Wert wurde stillschweigend zu „alle Artikel".

Das ist die unangenehmste Sorte Fehler: Ein Aufruf, der nichts tun sollte,
verändert den Bestand – und niemand sieht es, weil das Skript „Fertig"
meldet. Ein Probelauf, der die Hälfte schreibt, ist schlimmer als keiner.

Dieser Test hält die vier Zusicherungen fest, die daraus folgen:
  1. `--help` schreibt nichts und endet mit 0.
  2. Ein unbekannter Schalter ist ein Fehler (2), kein Volllauf.
  3. `--slug` ohne Wert ist ein Fehler, kein Volllauf.
  4. `--dry-run` schreibt NICHTS – geprüft an den echten Manifesten.
"""
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts" / "generate_covers.py"

# Die Dateien, die ein Volllauf anfasst (Bilder ausgenommen: die liegen unter
# static/ und werden hier nicht gebraucht – die Manifeste genügen als Beweis,
# weil sie am ENDE jedes Laufs geschrieben werden).
MANIFESTE = (
    ROOT / "data" / "lcp_images.json",
    ROOT / "data" / "fcp_images.json",
    ROOT / "data" / "covers_manifest.json",
)


def lauf(*argumente):
    return subprocess.run([sys.executable, str(SKRIPT), *argumente],
                          capture_output=True, text=True, timeout=600,
                          cwd=str(ROOT))


def staende():
    """(Pfad, Bytes) der Manifeste – None, wenn die Datei fehlt."""
    out = []
    for p in MANIFESTE:
        out.append((p.name, p.read_bytes() if p.exists() else None))
    return out


class CliVertragTests(unittest.TestCase):
    def test_hilfe_schreibt_nichts_und_endet_null(self):
        """`--help` ist eine Auskunft, keine Aktion."""
        vorher = staende()
        r = lauf("--help")
        self.assertEqual(r.returncode, 0,
                         f"--help muss 0 liefern, war {r.returncode}: {r.stderr[:200]}")
        self.assertIn("--dry-run", r.stdout,
                      "Der Hilfetext nennt die Schalter nicht")
        self.assertEqual(vorher, staende(),
                         "--help hat den Bestand verändert")

    def test_unbekannter_schalter_ist_ein_fehler(self):
        """Ein Tippfehler darf nie als „kein Schalter" durchgehen."""
        vorher = staende()
        r = lauf("--frce")           # bewusst falsch geschrieben
        self.assertEqual(r.returncode, 2,
                         f"unbekannter Schalter muss Exit 2 sein, war {r.returncode}")
        self.assertIn("unrecognized", r.stderr.lower())
        self.assertEqual(vorher, staende(),
                         "Der abgelehnte Aufruf hat trotzdem geschrieben")

    def test_slug_ohne_wert_ist_ein_fehler(self):
        """`--slug` ohne Wert lief früher stillschweigend über ALLE Artikel."""
        vorher = staende()
        r = lauf("--slug")
        self.assertEqual(r.returncode, 2,
                         f"--slug ohne Wert muss Exit 2 sein, war {r.returncode}")
        self.assertIn("expected one argument", r.stderr.lower())
        self.assertEqual(vorher, staende(),
                         "Der abgelehnte Aufruf hat trotzdem geschrieben")

    def test_probelauf_schreibt_nichts(self):
        """Die eigentliche Zusicherung: `--dry-run` ist wirkungsfrei."""
        vorher = staende()
        r = lauf("--dry-run", "--slug", "2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpunkt")
        self.assertEqual(r.returncode, 0, f"Probelauf scheiterte: {r.stderr[:300]}")
        self.assertIn("PROBELAUF", r.stdout)
        self.assertIn("Es wurde NICHTS geändert", r.stdout,
                      "Der Probelauf behauptet keine Wirkungsfreiheit")
        self.assertEqual(vorher, staende(),
                         "Der Probelauf hat Manifeste verändert")

    def test_probelauf_meldet_keine_erstellten_cover(self):
        """Ein Probelauf darf nicht „133 Cover erstellt" ins Log schreiben."""
        r = lauf("--dry-run", "--slug", "2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpunkt")
        self.assertEqual(r.returncode, 0)
        self.assertNotIn("Cover erstellt", r.stdout,
                         "Probelauf meldet erstellte Cover, obwohl nichts geschrieben wurde")


if __name__ == "__main__":
    unittest.main()
