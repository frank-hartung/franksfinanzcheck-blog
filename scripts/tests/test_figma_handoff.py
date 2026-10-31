"""Regressionstests für den Figma-Handoff und die Qualitäts-Gate (31.10.2026).

Warum diese Tests existieren
---------------------------
Der Handoff ist eine Übergabeschicht: Er behauptet, die Produktion zu
beschreiben. Genau darin liegt die Gefahr. Ein Inventar mit erfundenen
Klassen, eine Semantik mit fehlenden Dunkel-Rollen oder ein Plugin, das
still die Hälfte nicht baut, sieht von außen vollständig aus.

Die Tests halten die fünf Zusagen fest, auf denen der Handoff steht:

1) **Nichts wird erfunden.** Jeder `code`-Vertrag existiert im CSS.
2) **Kein Modus ist halb.** Hell und Dunkel tragen dieselben Rollen.
3) **Kontrast wird gerechnet.** Die Matrix ist WCAG-Mathematik, keine Prosa.
4) **Das Plugin baut, es beschreibt nicht.** Variablen, Stile, Varianten.
5) **Das Gate fängt echte Lücken.** Jede Sabotage erzeugt einen Befund.

Alle Tests laufen ohne Netz, ohne Hugo, ohne Browser und ohne Figma.
"""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import design_handoff as handoff  # noqa: E402
import figma_quality_gate as gate  # noqa: E402


def ssot():
    return handoff.load_yaml(handoff.SOURCE)


def rules():
    return handoff.load_yaml(handoff.RULES)


class ErfindungsVerbot(unittest.TestCase):
    """Zusage 1: Der Handoff beschreibt den Bestand, er dichtet nichts hinzu."""

    def test_jede_komponente_existiert_im_css(self):
        fehler = handoff.pruefe_css_vertrag(ssot(), handoff.css_bestand())
        self.assertEqual(fehler, [], "Inventar und CSS sind auseinandergelaufen")

    def test_erfundene_klasse_wird_erkannt(self):
        data = ssot()
        data["components"].append({
            "id": "geist", "figma": "Geist/X", "code": ".gibt-es-nicht",
            "states": ["default", "dark"], "accessibility": "-", "variablen": [],
        })
        fehler = handoff.pruefe_css_vertrag(data, handoff.css_bestand())
        self.assertTrue(any("gibt-es-nicht" in f for f in fehler), fehler)

    def test_komponente_ohne_code_vertrag_faellt_auf(self):
        data = ssot()
        data["components"].append({"id": "ohne", "figma": "X/Y", "code": "",
                                   "states": ["default", "dark"], "accessibility": "-"})
        fehler = handoff.pruefe_css_vertrag(data, handoff.css_bestand())
        self.assertTrue(any("keinen code-Vertrag" in f for f in fehler), fehler)


class BeideModi(unittest.TestCase):
    """Zusage 2: Ein Modus ohne die Rollen des anderen ist unfertig."""

    def test_rollen_sind_in_beiden_modi_gleich(self):
        figma = ssot()["figma"]
        self.assertEqual(set(figma["semantic"]["light"]), set(figma["semantic"]["dark"]))

    def test_fehlende_dunkel_rolle_wird_erkannt(self):
        data = ssot()
        data["figma"]["semantic"]["dark"].pop("focus")
        with self.assertRaises(ValueError) as ctx:
            handoff.validate(data, rules())
        self.assertIn("Semantik-Rollen", str(ctx.exception))

    def test_rolle_zeigt_nie_auf_erfundene_farbe(self):
        data = ssot()
        data["figma"]["semantic"]["light"]["text"] = "nichtvorhanden"
        with self.assertRaises(ValueError) as ctx:
            handoff.validate(data, rules())
        self.assertIn("nichtvorhanden", str(ctx.exception))


class KontrastMathematik(unittest.TestCase):
    """Zusage 3: Kontrast ist rechnerisch, nicht redaktionell."""

    def test_definition(self):
        self.assertAlmostEqual(handoff.kontrast("#FFFFFF", "#000000"), 21.0, places=2)
        self.assertAlmostEqual(handoff.kontrast("#777777", "#777777"), 1.0, places=2)
        # Reihenfolge darf keine Rolle spielen.
        self.assertEqual(handoff.kontrast("#0E5A43", "#FFFFFF"),
                         handoff.kontrast("#FFFFFF", "#0E5A43"))

    def test_alle_paarungen_halten_aa(self):
        for mode, label, _vg, _hg, _a, _b, wert in handoff.kontrast_matrix(ssot()):
            with self.subTest(modus=mode, paarung=label):
                self.assertGreaterEqual(wert, 4.5)

    def test_matrix_steht_im_export(self):
        data, rw = ssot(), rules()
        text = handoff.annotationen(data, rw)
        self.assertIn("Kontrast-Matrix", text)
        self.assertGreaterEqual(text.count(":1 | 4,5:1 |"), 20)


class TypografieSkala(unittest.TestCase):
    """Die Skala muss auf dem Abnahme-Viewport zusammenhalten."""

    def test_display_darf_schrumpfen_text_nicht(self):
        data = ssot()
        data["figma"]["typography"]["body"]["mobile_px"] = 12  # 18 → 12 = 67 %
        with self.assertRaises(ValueError) as ctx:
            handoff.validate(data, rules())
        self.assertIn("Skala zerfällt", str(ctx.exception))

    def test_mobil_nie_groesser_als_desktop(self):
        data = ssot()
        data["figma"]["typography"]["h2"]["mobile_px"] = 40
        with self.assertRaises(ValueError) as ctx:
            handoff.validate(data, rules())
        self.assertIn("größer als size_px", str(ctx.exception))

    def test_zeilenhoehe_bleibt_im_lesbaren_band(self):
        data = ssot()
        data["figma"]["typography"]["body"]["line_height"] = 0.8
        with self.assertRaises(ValueError) as ctx:
            handoff.validate(data, rules())
        self.assertIn("line_height", str(ctx.exception))


class PluginVertrag(unittest.TestCase):
    """Zusage 4: Das Plugin baut die Datei, es beschreibt sie nicht."""

    def test_code_ist_erzeugt_und_syntaktisch_gueltig(self):
        code = handoff.plugin_code(ssot())
        self.assertNotIn("DATA_MARKE", code)
        lauf = subprocess.run(["node", "--check", "-"], input=code,
                              capture_output=True, text=True)
        self.assertEqual(lauf.returncode, 0, lauf.stderr)
        self.assertEqual(code, (handoff.PLUGIN_OUT / "code.js").read_text(encoding="utf-8"))

    def test_plugin_bleibt_ohne_netz(self):
        manifest = json.loads((handoff.PLUGIN_OUT / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["networkAccess"]["allowedDomains"], ["none"])

    def test_datenblock_traegt_die_ssot(self):
        daten = handoff.plugin_daten(ssot())
        self.assertEqual(daten["pages"], ssot()["figma"]["page_order"])
        self.assertEqual(len(daten["components"]), len(ssot()["components"]))
        # Zustand und Modus sind zwei Achsen: „Dunkel“ ist kein Zustand.
        self.assertIn("Standard", daten["state_labels"].values())
        self.assertNotIn("Dunkel", daten["state_labels"].values())
        self.assertEqual(handoff.MODES["dark"], "Dunkel")

    def test_dark_ist_modus_und_kein_zustand(self):
        code = handoff.plugin_code(ssot())
        self.assertIn("if (s === 'dark') continue", code)
        self.assertIn("Zustand=", code)
        self.assertIn("Modus=", code)

    def test_kein_platzhalter_kein_auskommentieren(self):
        # Der Platzhalter lebt in einer Zeile – auch ein Kommentar damit
        # würde nach dem Ersetzen als Rest auffallen.
        quelle = handoff.PLUGIN_SOURCE.read_text(encoding="utf-8")
        self.assertEqual(quelle.count("DATA_MARKE"), 1)


class PluginLaeuftWirklich(unittest.TestCase):
    """Das Plugin wird gegen eine nachgebildete Figma-API ausgeführt."""

    def test_simulation_besteht(self):
        import json as _json
        import shutil
        if not shutil.which("node"):
            self.skipTest("node fehlt")
        lauf = subprocess.run(
            ["node", str(ROOT / "scripts/tests/figma_plugin_sim.mjs"), "--json"],
            capture_output=True, text=True, cwd=ROOT)
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
        daten = _json.loads(lauf.stdout)
        self.assertEqual(daten["befund"], [])
        self.assertEqual(daten["ersterLauf"]["seiten"], 7)
        self.assertEqual(daten["ersterLauf"]["sammlungen"], 4)
        self.assertGreaterEqual(daten["ersterLauf"]["variablen"], 50)
        self.assertEqual(daten["ersterLauf"]["effektstile"], 4)
        self.assertEqual(daten["zweiterLauf"]["neu"], 0)

    def test_plugin_nutzt_kein_netz_und_kein_require(self):
        quelle = (handoff.PLUGIN_OUT / "code.js").read_text(encoding="utf-8")
        for verboten in ("fetch(", "XMLHttpRequest", "require("):
            self.assertNotIn(verboten, quelle)


class GateFaengtLuecken(unittest.TestCase):
    """Zusage 5: Das Gate ist eine Prüfung, keine Zusammenfassung."""

    def test_alle_kriterien_sind_erfuellt(self):
        bericht = gate.lauf()
        offen = [b for b in bericht if not b["ok"] and b["schwere"] == "fehler"]
        self.assertEqual(offen, [], f"{len(offen)} Kriterien offen: "
                                    f"{[b['id'] for b in offen]}")

    def test_kriterien_haben_eindeutige_ids(self):
        ids = [b["id"] for b in gate.lauf()]
        self.assertEqual(len(ids), len(set(ids)))

    def test_es_gibt_mindestens_34_kriterien(self):
        self.assertGreaterEqual(len(gate.lauf()), 34)

    def test_sabotage_am_manifest_wird_erkannt(self):
        original = (handoff.PLUGIN_OUT / "manifest.json").read_text(encoding="utf-8")
        try:
            kaputt = json.loads(original)
            kaputt["networkAccess"]["allowedDomains"] = ["https://example.com"]
            (handoff.PLUGIN_OUT / "manifest.json").write_text(
                json.dumps(kaputt), encoding="utf-8")
            befund = gate.p1()
            self.assertIsNotNone(befund)
            self.assertIn("none", befund)
        finally:
            (handoff.PLUGIN_OUT / "manifest.json").write_text(original, encoding="utf-8")

    def test_sabotage_an_einer_kontrastzeile_wird_erkannt(self):
        text = (handoff.OUT / "ANNOTATIONEN.md").read_text(encoding="utf-8")
        try:
            (handoff.OUT / "ANNOTATIONEN.md").write_text(
                text.replace("✅ 13.51:1", "❌ 2.10:1", 1), encoding="utf-8")
            befund = gate.e3()
            self.assertIsNotNone(befund)
        finally:
            (handoff.OUT / "ANNOTATIONEN.md").write_text(text, encoding="utf-8")


class SkillsGepinnt(unittest.TestCase):
    """Die beiden Design-Skills sind vollständig und hashgleich gepinnt."""

    def test_lockfile_kennt_beide_mit_commit(self):
        lock = json.loads((ROOT / "skills-lock.json").read_text(encoding="utf-8"))
        for name in ("impeccable", "design-taste-frontend"):
            with self.subTest(skill=name):
                eintrag = lock["skills"][name]
                self.assertRegex(eintrag["commit"], r"^[0-9a-f]{40}$")
                self.assertEqual(len(eintrag["computedHash"]), 64)

    def test_hashes_stimmen(self):
        import hashlib
        lock = json.loads((ROOT / "skills-lock.json").read_text(encoding="utf-8"))
        for name in ("impeccable", "design-taste-frontend"):
            with self.subTest(skill=name):
                pfad = ROOT / ".claude/skills" / name / "SKILL.md"
                ist = hashlib.sha256(pfad.read_bytes()).hexdigest()
                self.assertEqual(ist, lock["skills"][name]["computedHash"])

    def test_kein_referenzpfad_zeigt_ins_leere(self):
        self.assertIsNone(gate.k4())


if __name__ == "__main__":
    unittest.main()
