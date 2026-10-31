"""Regressionstests für den Figma-/Relume-Handoff (31.10.2026).

Warum diese Tests existieren
---------------------------
Der Handoff ist eine zweite Darstellung des Designs. Zweite Darstellungen
veralten lautlos: Das CSS ändert sich, das Inventar behauptet weiter die
alte Klasse, und niemand merkt es, bis ein Kunde im Figma-Entwurf auf eine
Komponente zeigt, die es nicht gibt. Diese Tests halten fest, was der
Handoff zusagt – und was ausdrücklich NICHT:

1) **Die Quelle ist die Wahrheit.** Jedes Artefakt trägt einen Hash aus der
   SSOT. Weicht er ab, ist die Datei veraltet – nicht „ungefähr richtig“.
2) **Kein erfundenes CSS.** Jede dokumentierte Klasse muss im ausgelieferten
   CSS existieren; jede Komponente braucht einen Fokus- und einen
   Dark-Mode-Zustand.
3) **Figma ist optional.** `design-system.html` muss ohne Netz, ohne Server
   und ohne Anmeldung vollständig sein. Fehlt diese Zusage, ist der Handoff
   für alle ohne Figma wertlos.
4) **Das Plugin baut idempotent.** Zweiter Lauf: „Neu 0“. Fehlende Rechte:
   Abbruch vor dem Aufbau, nicht mittendrin.
5) **Kontrast wird gerechnet.** Die Matrix darf keine behaupteten Zahlen
   enthalten – WCAG 2.2, relative Luminanz, nachprüfbar.

Alle Tests laufen ohne Netz, ohne Figma, ohne Browser und ohne Hugo.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import design_handoff as handoff          # noqa: E402
import figma_quality_gate as gate         # noqa: E402

OUT = ROOT / "design/handoff"
PLUGIN = ROOT / "figma/design-system-builder"


def lade():
    return handoff.load_yaml(handoff.SOURCE), handoff.load_yaml(handoff.RULES)


class QuelleTest(unittest.TestCase):
    """Die SSOT selbst: vollständig, symmetrisch, markenkonform."""

    @classmethod
    def setUpClass(cls):
        cls.data, cls.rules = lade()
        cls.rendered = handoff.render(cls.data, cls.rules)

    def test_01_version_und_stand(self):
        self.assertEqual(self.data["version"], handoff.VERSION)
        self.assertRegex(str(self.data["stand"]), r"^\d{4}-\d{2}-\d{2}$")

    def test_02_projekt_kontext_vorhanden(self):
        for key in ("name", "sprache", "produkt", "ziel", "ton"):
            self.assertTrue(str(self.data["projekt"].get(key, "")).strip(), key)

    def test_03_farben_sind_markenkonform(self):
        erlaubt = {str(v).upper() for v in self.rules["marke"]["farben_erlaubt"]}
        for name, wert in self.data["figma"]["primitives"]["colors"].items():
            self.assertIn(wert.upper(), erlaubt, name)

    def test_04_radien_im_regelwerk(self):
        erlaubt = set(self.rules["marke"]["radien_px_erlaubt"])
        for name, wert in self.data["figma"]["primitives"]["radius_px"].items():
            self.assertIn(wert, erlaubt, name)

    def test_05_semantik_symmetrisch(self):
        sem = self.data["figma"]["semantic"]
        self.assertEqual(set(sem["light"]), set(sem["dark"]),
                         "Rollen müssen in beiden Modi existieren")
        # 15 Rollen: die 12 Grundrollen plus Rand, Fokus, Fehler und Marke.
        self.assertEqual(len(sem["light"]), 15)

    def test_06_aliase_zeigen_auf_primitives(self):
        farben = set(self.data["figma"]["primitives"]["colors"])
        for modus, rollen in self.data["figma"]["semantic"].items():
            for rolle, ziel in rollen.items():
                self.assertIn(ziel, farben, f"{modus}.{rolle}")

    def test_07_typografie_hat_mobilwerte(self):
        for name, stil in self.data["figma"]["typography"].items():
            self.assertIn("mobile_px", stil, name)
            self.assertGreaterEqual(stil["mobile_px"], 12, name)
            self.assertLessEqual(stil["mobile_px"], stil["size_px"], name)

    def test_08_schatten_sind_figma_faehig(self):
        muster = re.compile(r"^0 \d+px \d+px rgba\(\d+, ?\d+, ?\d+, ?[0-9.]+\)$")
        for name, wert in self.data["figma"]["primitives"]["elevation"].items():
            self.assertRegex(str(wert).strip(), muster, name)

    def test_09_komponenten_vollstaendig(self):
        self.assertEqual(len(self.data["components"]), 19)
        ids = [c["id"] for c in self.data["components"]]
        self.assertEqual(len(ids), len(set(ids)))
        for c in self.data["components"]:
            self.assertTrue(c["code"].startswith((".", "#")), c["id"])
            self.assertIn("dark", c["states"], c["id"])
            self.assertTrue(c["accessibility"].strip(), c["id"])

    def test_10_interaktive_komponenten_mit_fokus(self):
        fokus = {"focus", "focus-visible", "focus-within", "keyboard"}
        for c in self.data["components"]:
            if c["id"] in gate.INTERAKTIV:
                self.assertTrue(fokus & set(c["states"]), c["id"])

    def test_11_validation_ist_gruen(self):
        handoff.validate(self.data, self.rules)  # wirft bei Fehlern

    def test_12_validation_faengt_fehlende_rolle(self):
        kaputt = json.loads(json.dumps(self.data))
        kaputt["figma"]["semantic"]["dark"].pop("focus")
        with self.assertRaises(ValueError) as ctx:
            handoff.validate(kaputt, self.rules)
        self.assertIn("Semantik-Rollen", str(ctx.exception))

    def test_13_validation_faengt_erfundene_klasse(self):
        kaputt = json.loads(json.dumps(self.data))
        kaputt["components"].append({
            "id": "geist", "figma": "Geist/X", "code": ".gibt-es-nicht",
            "states": ["default", "dark"], "accessibility": "x"})
        with self.assertRaises(ValueError) as ctx:
            handoff.validate(kaputt, self.rules)
        self.assertIn("gibt-es-nicht", str(ctx.exception))

    def test_14_validation_faengt_typografie_zerfall(self):
        kaputt = json.loads(json.dumps(self.data))
        kaputt["figma"]["typography"]["body"]["mobile_px"] = 9
        with self.assertRaises(ValueError) as ctx:
            handoff.validate(kaputt, self.rules)
        self.assertIn("Skala", str(ctx.exception))

    def test_15_relume_seiten_haben_sections(self):
        ids = {c["id"] for c in self.data["components"]} | handoff.RELUME_BAUSTEINE
        for page in self.data["relume"]["pages"]:
            self.assertTrue(page["sections"], page["path"])
            for section in page["sections"]:
                self.assertIn(section["component"], ids,
                              f"{page['path']}/{section['id']}")


class RenderingTest(unittest.TestCase):
    """Der Generator: deterministisch, vollständig, ohne Netz."""

    @classmethod
    def setUpClass(cls):
        cls.data, cls.rules = lade()
        cls.rendered = handoff.render(cls.data, cls.rules)

    def test_16_deterministisch(self):
        self.assertEqual(self.rendered, handoff.render(self.data, self.rules))

    def test_17_alle_artefakte_entstehen(self):
        # Das Manifest entsteht NACH dem Rendern aus allen Artefakten –
        # eine Datei, die ihren eigenen Hash enthält, wäre ein Widerspruch.
        self.assertEqual(set(handoff.GENERATED) - set(self.rendered),
                         {"handoff-manifest.json"})
        for name in self.rendered:
            self.assertIn(name, handoff.GENERATED, name)

    def test_18_tokens_haben_zwei_themes(self):
        tokens = json.loads(self.rendered["figma-tokens.tokens.json"])
        self.assertEqual(len(tokens["$themes"]), 2)
        self.assertIn("Semantic/Dark", tokens)

    def test_19_tokens_halten_spacing_skala(self):
        tokens = json.loads(self.rendered["figma-tokens.tokens.json"])
        self.assertEqual(len(tokens["Primitives"]["spacing"]),
                         len(self.data["figma"]["primitives"]["spacing_px"]))

    def test_20_design_system_ist_netzfrei(self):
        html = self.rendered["design-system.html"]
        self.assertNotRegex(html, r'(?:src|href)="https?://')
        self.assertNotIn("@import", html)

    def test_21_design_system_zeigt_beide_modi(self):
        html = self.rendered["design-system.html"]
        self.assertIn('data-modus="light"', html)
        self.assertIn("setze('dark')", html)

    def test_22_design_system_zeigt_alle_komponenten(self):
        html = self.rendered["design-system.html"]
        for c in self.data["components"]:
            self.assertIn(f'data-probe="{c["id"]}"', html, c["id"])
        self.assertGreaterEqual(html.count('class="karte"'), 19)

    def test_23_design_system_ist_responsiv(self):
        html = self.rendered["design-system.html"]
        self.assertIn("@media", html)
        self.assertIn("viewport", html)

    def test_24_spezifikation_listet_komponenten(self):
        html = self.rendered["spezifikation.html"]
        for c in self.data["components"]:
            self.assertIn(f'data-komponente="{c["id"]}"', html, c["id"])

    def test_25_patterns_enthalten_verbote(self):
        text = self.rendered["patterns.md"]
        self.assertIn("Seitenrhythmus", text)
        self.assertIn("Was das System niemals tut", text)
        self.assertIn("Abnahme je Entwurf", text)

    def test_26_annotationen_enthalten_matrix(self):
        text = self.rendered["ANNOTATIONEN.md"]
        self.assertIn("Kontrast-Matrix", text)
        zeilen = re.findall(r"^\| (?:light|dark) \|.*$", text, re.MULTILINE)
        self.assertEqual(len(zeilen), 2 * len(handoff.KONTRAST_PAARE))
        for zeile in zeilen:
            self.assertRegex(zeile, r"\d+[.,]\d+:1", "Zeile ohne gerechneten Wert")

    def test_27_relume_brief_traegt_regeln(self):
        text = self.rendered["relume-project-brief.md"]
        for regel in self.data["relume"]["global_rules"]:
            self.assertIn(regel, text)

    def test_28_inventar_nennt_jede_klasse(self):
        text = self.rendered["component-inventory.md"]
        for c in self.data["components"]:
            self.assertIn(c["code"], text, c["id"])


class KontrastTest(unittest.TestCase):
    """Kontrast wird gerechnet, nicht behauptet."""

    @classmethod
    def setUpClass(cls):
        cls.data, _ = lade()

    def test_29_wcag_referenzwerte(self):
        self.assertAlmostEqual(handoff.kontrast("#FFFFFF", "#000000"), 21.0, places=1)
        self.assertAlmostEqual(handoff.kontrast("#FFB300", "#FFB300"), 1.0, places=2)
        # Reihenfolge darf keine Rolle spielen
        self.assertEqual(handoff.kontrast("#0E5A43", "#FFFFFF"),
                         handoff.kontrast("#FFFFFF", "#0E5A43"))

    def test_30_alle_paare_erreichen_aa(self):
        for modus, label, _vg, _hg, _a, _b, wert in handoff.kontrast_matrix(self.data):
            self.assertGreaterEqual(wert, 4.5, f"{modus}/{label}")

    def test_31_matrix_hat_24_zeilen(self):
        self.assertEqual(len(handoff.kontrast_matrix(self.data)),
                         2 * len(handoff.KONTRAST_PAARE))

    def test_32_signalgelb_traegt_anthrazit_nicht_weiss_text(self):
        farben = self.data["figma"]["primitives"]["colors"]
        self.assertGreater(handoff.kontrast(farben["anthracite"], farben["yellow"]), 4.5)
        # Weiß auf Gelb wäre der klassische Fehler – er muss durchfallen.
        self.assertLess(handoff.kontrast("#FFFFFF", farben["yellow"]), 3.0)


class PluginTest(unittest.TestCase):
    """Das Plugin: aus der Quelle erzeugt, offline, idempotent."""

    @classmethod
    def setUpClass(cls):
        cls.data, _ = lade()
        cls.code = handoff.plugin_code(cls.data)

    def test_33_datenmarke_wird_ersetzt(self):
        self.assertNotIn("DATA_MARKE", self.code)
        self.assertIn("const DATA = {", self.code)

    def test_34_plugin_kennt_die_komponenten(self):
        daten = handoff.plugin_daten(self.data)
        self.assertEqual(len(daten["components"]), 19)
        self.assertEqual(len(daten["colors"]), 22)
        self.assertEqual(daten["pages"], self.data["figma"]["page_order"])

    def test_35_plugin_ist_offline(self):
        for verboten in ("fetch(", "XMLHttpRequest", "require(", "import("):
            self.assertNotIn(verboten, self.code)

    def test_36_plugin_bricht_bei_fehlender_marke_ab(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            quelle = Path(tmp) / "source.js"
            quelle.write_text("// ohne Marke\n", encoding="utf-8")
            original = handoff.PLUGIN_SOURCE
            handoff.PLUGIN_SOURCE = quelle
            try:
                with self.assertRaises(ValueError) as ctx:
                    handoff.plugin_code(self.data)
                self.assertIn("DATA_MARKE", str(ctx.exception))
            finally:
                handoff.PLUGIN_SOURCE = original

    def test_37_manifest_ohne_id(self):
        manifest = json.loads((PLUGIN / "manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("id", manifest)
        self.assertEqual(manifest["main"], "code.js")
        self.assertEqual(manifest["ui"], "ui.html")
        self.assertEqual(manifest["networkAccess"]["allowedDomains"], ["none"])
        self.assertEqual(manifest["documentAccess"], "dynamic-page")

    def test_38_ui_ist_eigenstaendig(self):
        html = (PLUGIN / "ui.html").read_text(encoding="utf-8")
        self.assertNotRegex(html, r'(?:src|href)="https?://')
        for marker in ("aufbauen", "fertig", "pluginMessage", "<button"):
            self.assertIn(marker, html)

    def test_38b_ui_prueft_ursprung_und_quelle(self):
        """Ein message-Handler ohne Herkunftsprüfung ist eine offene Tür.

        CodeQL hat das am 31.10.2026 als js/missing-origin-check gemeldet.
        Der richtige Umgang ist Härtung, nicht Unterdrückung: Ursprung,
        Quelle und Format werden geprüft, bevor Daten die Oberfläche
        erreichen.
        """
        html = (PLUGIN / "ui.html").read_text(encoding="utf-8")
        self.assertIn("event.origin", html)
        self.assertIn("event.source", html)
        self.assertIn("window.parent", html)
        self.assertIn("ERLAUBTE_TYPEN", html)
        # Reihenfolge: die Prüfung steht VOR dem Zugriff auf pluginMessage.
        stelle_pruefung = html.index("event.origin")
        stelle_zugriff = html.index("daten.pluginMessage")
        self.assertLess(stelle_pruefung, stelle_zugriff)

    def test_39_code_js_ist_aktuell(self):
        self.assertEqual((PLUGIN / "code.js").read_text(encoding="utf-8"), self.code,
                         "code.js ist veraltet – python3 scripts/design_handoff.py")

    def test_40_simulation_laeuft_gruen(self):
        lauf = subprocess.run(["node", "scripts/tests/figma_plugin_sim.mjs"],
                              cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
        self.assertIn("Neu 0", lauf.stdout)

    def test_41_simulation_meldet_keine_befunde(self):
        lauf = subprocess.run(["node", "scripts/tests/figma_plugin_sim.mjs", "--json"],
                              cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        daten = json.loads(lauf.stdout)
        self.assertEqual(daten["befund"], [])
        self.assertEqual(daten["ersterLauf"]["seiten"], 7)
        self.assertEqual(daten["ersterLauf"]["komponenten"], 19)


class ArtefaktTest(unittest.TestCase):
    """Die committeten Dateien müssen zur Quelle passen – nicht „ungefähr“."""

    def test_42_check_ist_gruen(self):
        lauf = subprocess.run([sys.executable, "scripts/design_handoff.py", "--check"],
                              cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)

    def test_43_manifest_traegt_alle_artefakte(self):
        manifest = json.loads((OUT / "handoff-manifest.json").read_text(encoding="utf-8"))
        self.assertNotIn("handoff-manifest.json", manifest["artifacts"])
        for name in handoff.GENERATED:
            if name != "handoff-manifest.json":
                self.assertIn(name, manifest["artifacts"], name)
        self.assertIn("figma/design-system-builder/code.js", manifest["plugins"])

    def test_44_manifest_hashes_stimmen(self):
        manifest = json.loads((OUT / "handoff-manifest.json").read_text(encoding="utf-8"))
        for name, wert in manifest["artifacts"].items():
            self.assertEqual(handoff.sha256((OUT / name).read_text(encoding="utf-8")), wert, name)

    def test_45_quellen_sind_im_manifest(self):
        manifest = json.loads((OUT / "handoff-manifest.json").read_text(encoding="utf-8"))
        self.assertIn("data/design/handoff.yaml", manifest["sources"])
        self.assertIn("figma/design-system-builder/source.js", manifest["sources"])


class GateTest(unittest.TestCase):
    """Das Gate: 36 Kriterien, und es fängt Sabotage."""

    def test_46_katalog_hat_36_kriterien(self):
        self.assertEqual(len(gate.PRUEFUNGEN), 36)
        ids = [p.id for p in gate.PRUEFUNGEN]
        self.assertEqual(ids, [f"P{i}" for i in range(1, 37)])

    def test_47_katalog_ist_vollstaendig_dokumentiert(self):
        for p in gate.PRUEFUNGEN:
            self.assertTrue(p.name.strip(), p.id)
            self.assertTrue(p.frage.strip(), p.id)
            self.assertIn(p.schwere, {"P1", "P2", "P3"}, p.id)
            self.assertIn(p.besitzer, {"auto", "human"}, p.id)
            self.assertTrue(p.kanal, p.id)

    def test_48_gate_ist_gruen(self):
        befunde = gate.pruefe()
        blockiert = [b for b in befunde if b.schwere in ("P1", "P2")]
        self.assertEqual(blockiert, [], "\n".join(b.text for b in blockiert))

    def test_49_gate_selftest_faengt_sabotage(self):
        lauf = subprocess.run([sys.executable, "scripts/figma_quality_gate.py", "--selftest"],
                              cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        self.assertEqual(lauf.returncode, 0, lauf.stdout + lauf.stderr)
        self.assertIn("Sabotage-Proben", lauf.stdout)

    def test_50_selftest_laesst_arbeitsbaum_unveraendert(self):
        vorher = {p.name: p.read_bytes() for p in [OUT / "handoff-manifest.json",
                                                   OUT / "design-system.html",
                                                   PLUGIN / "manifest.json"]}
        subprocess.run([sys.executable, "scripts/figma_quality_gate.py", "--selftest"],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        for pfad in [OUT / "handoff-manifest.json", OUT / "design-system.html",
                     PLUGIN / "manifest.json"]:
            self.assertEqual(pfad.read_bytes(), vorher[pfad.name], pfad.name)

    def test_51_einzelkriterium_laeuft(self):
        self.assertEqual(gate.pruefe("P1"), [])
        lauf = subprocess.run([sys.executable, "scripts/figma_quality_gate.py", "--nur", "P1"],
                              cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        self.assertEqual(lauf.returncode, 0, lauf.stdout)

    def test_52_unbekanntes_kriterium_ist_ein_fehler(self):
        lauf = subprocess.run([sys.executable, "scripts/figma_quality_gate.py", "--nur", "P99"],
                              cwd=str(ROOT), capture_output=True, text=True, timeout=120)
        self.assertEqual(lauf.returncode, 2)

    def test_53_json_ausgabe_ist_maschinenlesbar(self):
        lauf = subprocess.run([sys.executable, "scripts/figma_quality_gate.py", "--json"],
                              cwd=str(ROOT), capture_output=True, text=True, timeout=180)
        daten = json.loads(lauf.stdout)
        self.assertEqual(daten["kriterien"], 36)
        self.assertTrue(daten["bestanden"])
        self.assertEqual(daten["befunde"], [])

    def test_54_gate_faengt_erfundene_klasse(self):
        data, rules = lade()
        kaputt = json.loads(json.dumps(data))
        kaputt["components"][0]["code"] = ".zauber-klasse"
        befunde = gate.p14(kaputt, rules)
        self.assertTrue(befunde)
        self.assertEqual(befunde[0].kriterium, "P14")

    def test_55_gate_faengt_asymmetrie(self):
        data, rules = lade()
        kaputt = json.loads(json.dumps(data))
        kaputt["figma"]["semantic"]["dark"].pop("surface-soft")
        self.assertTrue(gate.p6(kaputt, rules))

    def test_56_gate_faengt_fehlende_rolle_in_komponente(self):
        data, rules = lade()
        kaputt = json.loads(json.dumps(data))
        kaputt["components"][0]["variablen"] = ["gibt-es-nicht"]
        self.assertTrue(gate.p15(kaputt, rules))

    def test_57_gate_faengt_fehlerhaftes_manifest(self):
        original = (PLUGIN / "manifest.json").read_text(encoding="utf-8")
        try:
            manifest = json.loads(original)
            manifest["id"] = ""
            (PLUGIN / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
            data, rules = lade()
            self.assertTrue(gate.p31(data, rules))
        finally:
            (PLUGIN / "manifest.json").write_text(original, encoding="utf-8")

    def test_58_befunde_haben_besitzer_und_schwere(self):
        data, rules = lade()
        kaputt = json.loads(json.dumps(data))
        kaputt["figma"]["primitives"]["colors"]["emerald"] = "#123456"
        for befund in gate.p4(kaputt, rules):
            self.assertIn(befund.besitzer, {"auto", "human"})
            self.assertEqual(befund.schwere, "P1")
            self.assertTrue(befund.kanal)


class DokuTest(unittest.TestCase):
    """Der Figma-freie Weg muss begehbar dokumentiert sein."""

    def test_59_anleitung_existiert(self):
        self.assertTrue(gate.DOKU.exists())

    def test_60_anleitung_nennt_figma_freien_weg(self):
        text = gate.DOKU.read_text(encoding="utf-8")
        self.assertIn("ohne Figma", text)
        self.assertIn("design-system.html", text)

    def test_61_anleitung_erklaert_abbruch(self):
        text = gate.DOKU.read_text(encoding="utf-8")
        for marker in ("currentpage", "textreview", "dynamic-page", "⛔"):
            self.assertIn(marker, text)

    def test_62_anleitung_ist_im_workflow_verlinkt(self):
        workflow = gate.WORKFLOW.read_text(encoding="utf-8")
        for marker in ("figma_quality_gate.py", "figma_plugin_sim.mjs",
                       "test_figma_handoff.py", "design_handoff.py --check"):
            self.assertIn(marker, workflow)

    def test_63_bestehende_handoff_doku_bleibt_gueltig(self):
        text = (ROOT / "docs/ANLEITUNG-FIGMA-RELUME-HANDOFF.md").read_text(encoding="utf-8")
        self.assertIn("data/design/handoff.yaml", text)
        self.assertIn("design/handoff/handoff-manifest.json", text)


class BestandTest(unittest.TestCase):
    """Was der Handoff über den Blog behauptet, muss im Blog stimmen."""

    @classmethod
    def setUpClass(cls):
        cls.data, _ = lade()
        cls.css = handoff.css_bestand()

    def test_64_css_klassen_existieren(self):
        self.assertEqual(handoff.pruefe_css_vertrag(self.data, self.css), [])

    def test_65_jede_komponente_hat_zielrollen(self):
        rollen = set(self.data["figma"]["semantic"]["light"])
        for c in self.data["components"]:
            self.assertTrue(c.get("variablen"), c["id"])
            for rolle in c["variablen"]:
                self.assertIn(rolle, rollen, c["id"])

    def test_66_keine_unbenutzten_rollen(self):
        benutzt = {v for c in self.data["components"] for v in c["variablen"]}
        self.assertEqual(set(self.data["figma"]["semantic"]["light"]) - benutzt, set())

    def test_67_globaler_fokusring_ist_dokumentiert(self):
        self.assertRegex(self.css, r"(?:^|[\s,])a:focus-visible")
        self.assertRegex(self.css, r"(?:^|[\s,])summary:focus-visible")

    def test_68_abnahme_viewport_ist_390(self):
        self.assertEqual(self.data["figma"]["breakpoints"]["mobile"], 390)

    def test_69_raster_ist_das_dokumentierte(self):
        grid = self.data["figma"]["grid"]
        self.assertEqual(grid["basis_px"], 8)
        self.assertEqual(grid["feinstufen_px"], [14, 18, 22])
        self.assertEqual(grid["content_breite_px"], 720)

    def test_70_seitenreihenfolge_sieben(self):
        self.assertEqual(len(self.data["figma"]["page_order"]), 7)
        self.assertEqual(self.data["figma"]["page_order"][0], "00 Cover")

    def test_71_plugin_id_bleibt_maschinenspezifisch(self):
        # Die Figma-Plugin-ID gehört nicht ins Repository – ein leeres Feld
        # verhindert, dass eine fremde ID den Import blockiert.
        self.assertEqual(self.data["figma"]["plugin_id"], "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
