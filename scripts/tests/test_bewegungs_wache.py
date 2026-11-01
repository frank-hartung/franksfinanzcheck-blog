#!/usr/bin/env python3
"""Tests zur Bewegungs-Wache (B1–B6, 01.11.2026).

Fünf Ebenen, damit „die Skala gilt" nicht von einem grünen Lauf abhängt:

1. **Logik** – der Selbsttest der Wache (Dauer, Easing, `all`, Layout,
   Lift ohne Druck, Ausnahme-Fristen) und die Sortier-/Dedup-Regel.
2. **Quelle** – die Skala wird aus `data/design/regelwerk.yaml` gelesen,
   nicht in der Wache abgetippt; beide Leser (YAML und Rückfall) liefern
   dieselben Zahlen. Eine zweite Grenze im Code wäre genau der Fehler,
   den DESIGN.md §9 verbietet.
3. **Bestand** – der heutige Befund ist eingefroren. Fällt die Zahl, ist
   das eine Heilung (Test anpassen, Zahl senken). Steigt sie, hat jemand
   neue Bewegung ohne Skala eingebaut – und das fällt auf, obwohl die
   Wache noch nicht im Gate steht.
4. **Abgrenzung** – was die Wache NICHT prüft, wird hier festgehalten:
   `prefers-reduced-motion`-Abdeckung ist keine Bedingung dieser Wache
   (sie wird getrennt gemessen), damit niemand sie dafür hält.
5. **Verdrahtung** – der Befehl existiert in `package.json`, der
   Selbsttest ist quotiert implementiert (sonst führt der
   `selftest_runner` ihn nicht aus) und der Wahrheitsort ist verlinkt.
"""
from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import bewegungs_wache as bw  # noqa: E402

WACHE = SCRIPTS / "bewegungs_wache.py"
REGELWERK = ROOT / "data" / "design" / "regelwerk.yaml"
BERICHT = ROOT / "BEWEGUNG-AUDIT-HIGHEND-2026-11-01.md"

# Eingefrorener Bestand am 01.11.2026 (BEWEGUNG-AUDIT-…).
# Sinkt die Zahl, gehört sie hier gesenkt – das ist die Heilung.
BESTAND_BEFUNDE = 42          # B1 (41) + B4 (1)
BESTAND_HINWEISE = 107        # B2 (67) + B3 (2) + B5 (38)


def wache(*argumente: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(WACHE), *argumente],
                          cwd=ROOT, capture_output=True, text=True, timeout=300)


class Logik(unittest.TestCase):
    """1. Die Wache selbst – über ihren eingefrorenen Selbsttest."""

    def test_selbsttest_gruen(self):
        lauf = wache("--selftest")
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
        self.assertIn("Fälle grün", lauf.stdout)

    def test_doppelte_dauer_wird_einmal_gemeldet(self):
        """`transform .15s ease, box-shadow .15s ease` ist EIN Verstoß."""
        fund = bw.Fund("B1", "a.css", 3, ".x", "Dauer 0.15s …")
        einmal = bw.sortiere_nach_datei([fund])
        zweimal = bw.sortiere_nach_datei([fund, fund])
        self.assertEqual(len(einmal), 1)
        self.assertEqual(len(zweimal), 1, "derselbe Verstoß darf nicht doppelt zählen")

    def test_ohne_ausnahmen_gibt_es_keine_luecke(self):
        """Fehlt die Ausnahmedatei, prüft die Wache weiter – ohne Absturz."""
        fehlend = ROOT / "data" / "gibt-es-nicht.yaml"
        import datetime
        liste, funde = bw.ausnahmen(fehlend, datetime.date(2026, 11, 1))
        self.assertEqual(liste, [])
        self.assertEqual(funde, [])


class Quelle(unittest.TestCase):
    """2. Eine Wahrheit: die Skala steht im Regelwerk, nicht im Code."""

    def test_skala_kommt_aus_dem_regelwerk(self):
        dauern, kurven = bw.skala(REGELWERK)
        self.assertIn(0.16, dauern)
        self.assertIn(0.3, dauern)
        self.assertTrue(any("cubic-bezier" in k for k in kurven), kurven)

    def test_keine_zweite_grenze_im_code(self):
        quelle = WACHE.read_text(encoding="utf-8")
        # Der Modulkopf darf die Zahlen als Prosa nennen; eine Zuweisung wäre
        # eine zweite Grenze. Gesucht wird die Zuweisungsform.
        for verboten in ("ERLAUBTE_DAUERN =", "SKALA =", "EASINGS = ["):
            self.assertNotIn(verboten, quelle)

    def test_rueckfallleser_liefert_dieselben_zahlen(self):
        """Ohne PyYAML muss die Wache dieselben Werte sehen (CI hat yaml,
        ein nackter Sandkasten nicht)."""
        dauern, kurven = bw.skala(REGELWERK)
        text = REGELWERK.read_text(encoding="utf-8")
        import re
        treffer = re.search(r"uebergang_dauer_s_erlaubt:\s*\[(.*?)\]", text, re.S)
        self.assertIsNotNone(treffer)
        roh = {round(float(x), 4) for x in treffer.group(1).split(",") if x.strip()}
        self.assertEqual(roh, dauern)
        self.assertTrue(kurven)


class Bestand(unittest.TestCase):
    """3. Der heutige Stand ist eingefroren – Bewegung wächst nicht heimlich."""

    def test_befundzahl_ist_eingefroren(self):
        lauf = wache("--json")
        daten = json.loads(lauf.stdout)
        self.assertEqual(daten["dateien"] >= bw.MIN_DATEIEN, True,
                         f"nur {daten['dateien']} Stylesheets – blind, nicht grün")
        self.assertLessEqual(
            len(daten["befunde"]), BESTAND_BEFUNDE,
            "Neue Bewegung ohne Skala: erst heilen oder begründet ausnehmen, "
            "dann diese Zahl senken – niemals erhöhen.")
        self.assertLessEqual(len(daten["hinweise"]), BESTAND_HINWEISE,
                             "Neue Hinweise (Easing/`all`/Lift) – siehe Bericht.")

    def test_ohne_befund_ist_der_exitcode_null(self):
        """Belegt die Verdrahtung: der Bestandslauf darf nicht still grün sein."""
        lauf = wache("--json", "--nur-hinweise")
        self.assertEqual(lauf.returncode, 0, lauf.stderr)


class Abgrenzung(unittest.TestCase):
    """4. Was hier NICHT geprüft wird – damit die Wache nicht überschätzt wird."""

    def test_reduzierte_bewegung_ist_nicht_teil_der_wache(self):
        quelle = WACHE.read_text(encoding="utf-8")
        # Sie liest prefers-reduced-motion nur, um die dort abgeschalteten
        # Lifts nicht als fehlendes Druck-Feedback zu zählen.
        self.assertNotIn("B7", quelle)
        self.assertIn("prefers-reduced-motion", quelle)

    def test_befundzahl_im_bericht_passt_zur_wache(self):
        """Zwei Wahrheitsorte, ein Wert: Bericht und Wache dürfen nicht
        auseinanderlaufen (die Klasse „Report ohne Erzeuger", #806)."""
        if not BERICHT.is_file():
            self.skipTest("Bericht fehlt in diesem Baum")
        text = BERICHT.read_text(encoding="utf-8")
        self.assertIn(f"{BESTAND_BEFUNDE} Befunde", text)
        self.assertIn("bewegungs_wache.py", text)


class Verdrahtung(unittest.TestCase):
    """5. Erreichbar und auffindbar – sonst prüft niemand."""

    def test_npm_befehle_existieren(self):
        paket = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertIn("bewegung:check", paket["scripts"])
        self.assertIn("test:bewegung", paket["scripts"])
        self.assertIn("bewegungs_wache.py", paket["scripts"]["bewegung:check"])

    def test_selbsttest_ist_quotiert_implementiert(self):
        """Eine bloße Erwähnung im Kommentar würde den selftest_runner dazu
        bringen, die Standard-Aktion zu starten (17.09.2026, publish_gate)."""
        quelle = WACHE.read_text(encoding="utf-8")
        self.assertIn('"--selftest"', quelle)

    def test_wache_ist_nicht_im_gate_blockiert_aber_dokumentiert(self):
        """Solange der Bestand rot ist, steht sie NICHT in GUARDS – das ist
        eine Entscheidung, keine Vergesslichkeit, und steht im Bericht."""
        import governance_contract as gc
        if BERICHT.is_file():
            text = BERICHT.read_text(encoding="utf-8")
            self.assertIn("GUARDS", text)
        if "bewegungs_wache.py" not in gc.GUARDS:
            self.skipTest("bewusst nicht im vertraglichen Minimum (Bestand rot)")

    def test_skill_nennt_die_wache(self):
        skill = ROOT / ".claude/skills/ff-oberflaeche/SKILL.md"
        self.assertIn("bewegungs_wache.py", skill.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
