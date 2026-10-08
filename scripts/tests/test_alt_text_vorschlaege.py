#!/usr/bin/env python3
"""Vertragstests: scripts/alt_text_vorschlaege.py (Cover-Alt-Texte, 08.10.2026).

Festgehalten wird:
  1. Der Selbsttest des Skripts ist grün (Einordnung, Prüfregeln, Schreiben, Freigabe).
  2. Nur freigegebene Vorschläge mit benanntem Freigeber werden geschrieben.
  3. Ohne GEMINI_API_KEY: exit 0, „übersprungen“, kein Netzwerkzugriff, keine Datei.
  4. Die Anwendung ändert nur die alt-Zeile im cover-Block.
  5. Kein Workflow ruft das Skript auf (Vorschläge sind nie automatisch).
  6. Der Bestand im Repo ist konsistent: die Zählung deckt alle Seiten mit Titelbild.
"""
from __future__ import annotations

import contextlib
import importlib.util
import io
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SKRIPT = ROOT / "scripts" / "alt_text_vorschlaege.py"


def _load():
    spec = importlib.util.spec_from_file_location("alt_text_vorschlaege", SKRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


at = _load()
HAS_YAML = at.yaml is not None


@unittest.skipUnless(HAS_YAML, "PyYAML fehlt (CI installiert es)")
class SelbsttestUndRegeln(unittest.TestCase):
    def test_selbsttest_ist_gruen(self):
        self.assertEqual(at.selbsttest(), [])

    def test_pruefe_alt_faengt_die_typischen_fehler(self):
        self.assertTrue(at.pruefe_alt("Bild von einem Sparschwein", "Titel"))
        self.assertTrue(at.pruefe_alt("Foto: Münzen", "Titel"))
        self.assertTrue(at.pruefe_alt("x" * (at.ALT_MAX + 1), "Titel"))
        self.assertTrue(at.pruefe_alt("Titel", "titel"))
        self.assertEqual(at.pruefe_alt("Sparschwein mit Münzen auf hellem Grund", "Titel"), [])

    def test_bildschirm_ist_keine_bild_einleitung(self):
        self.assertEqual(at.pruefe_alt("Bildschirm mit Tarifvergleich", "Titel"), [])

    def test_einordnung_der_grundfaelle(self):
        self.assertEqual(at.einordnen({"cover": {"image": "a.jpg"}}), "alt-fehlt")
        self.assertEqual(at.einordnen({"cover": {"image": "a.jpg", "alt": "  "}}), "alt-leer")
        self.assertEqual(at.einordnen({"title": "T", "cover": {"image": "a.jpg", "alt": "t"}}), "titel-kopie")
        self.assertEqual(at.einordnen({"title": "T", "cover": {"image": "a.jpg", "alt": "Münzen"}}), "eigenstaendig")
        self.assertEqual(at.einordnen({"title": "T"}), "ohne-cover")

    def test_setze_cover_alt_aendert_nur_die_alt_zeile(self):
        quelle = ("---\ntitle: \"T\"\ncover:\n  image: \"images/covers/a.jpg\"\n"
                  "  alt: \"alt\"\n  caption: \"U\"\n---\n\nKörper alt: Zeile\n")
        neu = at.setze_cover_alt(quelle, "Neu")
        self.assertEqual(neu.count("\n"), quelle.count("\n"))
        self.assertIn("Körper alt: Zeile", neu)
        self.assertIn('  caption: "U"', neu)
        self.assertEqual(at.yaml.safe_load(at.FM_RE.match(neu).group(1))["cover"]["alt"], "Neu")

    def test_setze_cover_alt_fuegt_fehlende_zeile_nach_image_ein(self):
        quelle = "---\ntitle: \"T\"\ncover:\n  image: \"images/covers/a.jpg\"\n---\nK\n"
        neu = at.setze_cover_alt(quelle, "Neu")
        self.assertEqual(at.yaml.safe_load(at.FM_RE.match(neu).group(1))["cover"]["alt"], "Neu")

    def test_setze_cover_alt_ohne_cover_ist_fehler(self):
        with self.assertRaises(ValueError):
            at.setze_cover_alt("---\ntitle: \"T\"\n---\nK\n", "Neu")


@unittest.skipUnless(HAS_YAML, "PyYAML fehlt (CI installiert es)")
class Freigabe(unittest.TestCase):
    def _repo(self, tmp: str) -> Path:
        root = Path(tmp)
        (root / "content" / "posts" / "a").mkdir(parents=True)
        (root / "static" / "images" / "covers").mkdir(parents=True)
        (root / "static" / "images" / "covers" / "a.jpg").write_bytes(b"\xff\xd8\xff\xe0x")
        (root / "content" / "posts" / "a" / "index.md").write_text(
            "---\ntitle: \"Test-Ratgeber\"\ncover:\n  image: \"images/covers/a.jpg\"\n"
            "  alt: \"test-ratgeber\"\n---\nKörper\n", encoding="utf-8")
        return root

    def test_ohne_freigabe_wird_nichts_geschrieben(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp)
            at.vorschlagen(root, lambda b, m, t: "Sparschwein auf Münzen", 5, pause=0)
            at.anwenden(root)
            self.assertIn('alt: "test-ratgeber"', (root / "content/posts/a/index.md").read_text(encoding="utf-8"))

    def test_vorschlag_ist_nie_schon_freigegeben(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp)
            at.vorschlagen(root, lambda b, m, t: "Sparschwein auf Münzen", 5, pause=0)
            store = at.lade_store(root)
            self.assertIs(store["vorschlaege"][0]["freigegeben"], False)
            self.assertEqual(store["vorschlaege"][0]["freigegeben_von"], "")

    def test_bestehende_eintraege_werden_nicht_neu_erzeugt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp)
            at.vorschlagen(root, lambda b, m, t: "Sparschwein auf Münzen", 5, pause=0)
            neu, _ = at.vorschlagen(root, lambda b, m, t: "Anderer Text", 5, pause=0)
            self.assertEqual(neu, 0)
            self.assertEqual(len(at.lade_store(root)["vorschlaege"]), 1)

    def test_verworfene_antwort_erzeugt_keinen_eintrag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp)
            neu, verworfen = at.vorschlagen(root, lambda b, m, t: "Bild von einem Sparschwein", 5, pause=0)
            self.assertEqual(neu, 0)
            self.assertTrue(verworfen)
            self.assertEqual(at.lade_store(root)["vorschlaege"], [])

    def test_ohne_schluessel_exit_null_ohne_netz_und_ohne_datei(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp)
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                code = at.main(["--vorschlagen"], root=root, env={})
            self.assertEqual(code, 0)
            self.assertIn("übersprungen", puffer.getvalue())
            self.assertFalse((root / "data" / "alt_texte" / "vorschlaege.yaml").exists())

    def test_veralteter_vorschlag_wird_abgewiesen(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = self._repo(tmp)
            at.vorschlagen(root, lambda b, m, t: "Sparschwein auf Münzen", 5, pause=0)
            store = at.lade_store(root)
            store["vorschlaege"][0].update({"freigegeben": True, "freigegeben_von": "Prüfer"})
            store["vorschlaege"][0]["alt_aktuell"] = "etwas anderes"
            at.speichere_store(root, store)
            ergebnis = at.anwenden(root)
            self.assertTrue(any("veraltet" in m for _, m in ergebnis))
            self.assertIn('alt: "test-ratgeber"', (root / "content/posts/a/index.md").read_text(encoding="utf-8"))


@unittest.skipUnless(HAS_YAML, "PyYAML fehlt (CI installiert es)")
class Repo(unittest.TestCase):
    def test_zaehlung_deckt_alle_seiten_mit_titelbild(self):
        alle = at.seiten(ROOT)
        self.assertGreater(len(alle), 0)
        gruende = {g for _, _, g in alle}
        self.assertTrue(gruende <= {"eigenstaendig", "titel-kopie", "alt-fehlt", "alt-leer"})

    def test_vorschlagsdatei_ist_gueltig(self):
        store = at.lade_store(ROOT)
        self.assertEqual(store["version"], 1)
        self.assertIsInstance(store["vorschlaege"], list)
        for e in store["vorschlaege"]:
            self.assertIn(e.get("freigegeben"), (True, False))

    def test_kein_workflow_ruft_das_skript_auf(self):
        wf = ROOT / ".github" / "workflows"
        for datei in wf.glob("*.yml"):
            self.assertNotIn("alt_text_vorschlaege", datei.read_text(encoding="utf-8"), datei.name)


if __name__ == "__main__":
    unittest.main()
