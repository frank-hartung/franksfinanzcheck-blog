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
import re
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

# Eingefrorener Bestand NACH Schritt 1 + B5-Heilung (01.11.2026).
# Vorher: 42 Befunde (41 × B1, 1 × B4) und 107 Hinweise; nach Schritt 1 noch
# 40 Hinweise (2 × B3, 38 × B5). Die 38 Lifts sind inzwischen Fläche für
# Fläche geheilt und die zwei `transition: all` ausgeschrieben – deshalb 0/0.
# Die Zahl darf nur fallen. Steigt sie, hat jemand Bewegung ohne Skala
# eingebaut und niemand hat es gemerkt, bis dieser Test lief.
BESTAND_BEFUNDE = 0
BESTAND_HINWEISE = 0          # B3/B5 = 0 seit dem B5-Nachtrag


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
        """Der Bestandslauf ist grün – sonst darf die Wache nicht ins Gate."""
        lauf = wache("--json")
        self.assertEqual(lauf.returncode, 0, lauf.stdout[-400:] + lauf.stderr)

    def test_kein_befund_mehr_im_bestand(self):
        """Schritt 1 ist vollzogen: keine Dauer außerhalb der Skala, keine
        undokumentierte Layout-Animation. Fällt hier etwas auf, hat jemand
        Bewegung ohne Skala eingebaut."""
        daten = json.loads(wache("--json").stdout)
        self.assertEqual([f["klasse"] for f in daten["befunde"]], [],
                         "Bewegung außerhalb der Skala – erst §6.1/Regelwerk "
                         "entscheiden, dann eintragen (nie umgekehrt).")


class SkalaSynchron(unittest.TestCase):
    """DESIGN.md §6.1 (Prosa) und regelwerk.yaml (Maschine) müssen dasselbe
    sagen. Zwei Wahrheitsorte ohne Abgleich sind der Fehler, den dieses Repo
    an `serp_limits.py` schon einmal beschrieben hat – und der Grund, warum
    die Dauer-Liste am 01.11.2026 überhaupt auffiel."""

    def test_jede_dauer_in_6_1_steht_im_regelwerk(self):
        text = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
        abschnitt = text[text.index("### 6.1"):text.index("### 6.2")]
        aus_prosa = {round(float(w.replace(",", ".")), 4)
                     for w in re.findall(r"\|\s*(?:\*\*)?\w+(?:\+)?(?:\*\*)?\s*\|\s*([0-9],[0-9]+) s", abschnitt)}
        dauern, _ = bw.skala(REGELWERK)
        self.assertEqual(aus_prosa - dauern, set(),
                         "Dauer in §6.1, aber nicht im Regelwerk – das Gate "
                         "würde sie als Verstoß melden.")
        self.assertEqual(dauern - aus_prosa, set(),
                         "Dauer im Regelwerk, aber nicht in §6.1 – dann steht "
                         "eine Zahl ohne Aufgabe in der Skala.")

    def test_ease_ist_ausdruecklich_erlaubt(self):
        """67 ausgelieferte Deklarationen nutzen `ease`. Ein Verbot im
        Regelwerk hätte sie alle zu Befunden gemacht, ohne dass sich am
        Verhalten etwas ändert."""
        _, kurven = bw.skala(REGELWERK)
        self.assertIn("ease", kurven)
        daten = json.loads(wache("--json").stdout)
        self.assertEqual([f for f in daten["hinweise"] if f["klasse"] == "B2"], [])

    def test_layout_ausnahmen_stehen_in_prosa_und_maschine(self):
        texte = (ROOT / "DESIGN.md").read_text(encoding="utf-8")
        abschnitt = texte[texte.index("### 6.1"):texte.index("### 6.2")]
        for eintrag in bw.layout_ausnahmen(REGELWERK):
            selektor = eintrag["selektor"]
            self.assertIn(selektor, abschnitt,
                          f"{selektor} steht im Regelwerk, aber nicht in §6.1")
            self.assertTrue(str(eintrag.get("grund") or "").strip(),
                            f"{selektor}: Ausnahme ohne Grund")

    def test_layout_ausnahme_braucht_einen_grund(self):
        for eintrag in bw.layout_ausnahmen(REGELWERK):
            self.assertIn("grund", eintrag)


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

    def test_wache_steht_im_vertraglichen_minimum(self):
        """Seit der Heilung (0 Befunde) gehört sie zu GUARDS. Eine Wache, die
        niemand verlangt, führt irgendwann niemand aus – und dann wächst die
        Skala wieder unbemerkt."""
        import governance_contract as gc
        self.assertIn("bewegungs_wache.py", gc.GUARDS,
                      "ohne Platz in GUARDS läuft ihr Selbsttest im Qualitäts-"
                      "Gate nie")

    def test_skill_nennt_die_wache(self):
        skill = ROOT / ".claude/skills/ff-oberflaeche/SKILL.md"
        self.assertIn("bewegungs_wache.py", skill.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
