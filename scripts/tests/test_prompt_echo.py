#!/usr/bin/env python3
"""Unit-Tests für R16-PROMPT-ECHO – der Generator spricht mit sich selbst.

ISSUE #521 (Tagesdefizit 02.10.2026)
=====================================
Die KI-Prompts der Engine verlangen das Ausgabeformat

    TITLE: <Überschrift>
    DESCRIPTION: <Beschreibung>
    <Artikeltext>

`generate_drafts.parse_article` erkannte diesen Kopf nur, wenn „TITLE:“
exakt auf Zeile 0 und „DESCRIPTION:“ exakt auf Zeile 1 stand. Die zweite
Bedingung war zugleich die EINZIGE Stelle, an der der Body überhaupt vom
Kopf getrennt wurde. Setzte das Modell eine Leerzeile dazwischen – am
02.10.2026 real geschehen –, entstand:

    description:     "TITLE: Preiswert surfen: So findest du den …"
    pin_description: "*Werbung | TITLE: Preiswert surfen: …"
    Fließtext ab Zeile 1: "TITLE: Preiswert surfen: …"

Also Google-Snippet, Pinterest-Pin UND Artikeltext. Gestoppt wurde der
Entwurf nur zufällig von der Zeichenlängen-Prüfung; keine Wache maß das
Muster. Die Reparatur hat zwei Ebenen:

  ENTSTEHUNG   `parse_article` ist positionsunabhängig und entfernt jeden
               Marker aus Titel, Beschreibung und Body.
  WACHE        `R16-PROMPT-ECHO` (Fließtext) und `R16-PROMPT-ECHO-META`
               (Frontmatter) blockieren hart – in beiden hard_rules-Sätzen.

Eine Ebene allein genügt nicht: Der Parser kann künftig erneut brechen,
und Artikel entstehen nicht nur über diesen einen Pfad.
"""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import sprachkern as sk  # noqa: E402
import textverstaendnis_guard as tg  # noqa: E402


def _load_generate_drafts():
    """generate_drafts hat Modul-Nebenwirkungen – isoliert laden."""
    spec = importlib.util.spec_from_file_location(
        "_gd_test", SCRIPTS / "generate_drafts.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


gd = _load_generate_drafts()

# Exakt die Form, die am 02.10.2026 im DSL-Entwurf stand.
SCHADENSFALL = (
    "TITLE: Preiswert surfen: So findest du den optimalen DSL-Anschluss\n"
    "\n"
    "DESCRIPTION: Entdecke, wie ein preiswerter Anschluss funktioniert.\n"
    "\n"
    "---\n"
    "\n"
    "Du hast das Gefühl, dein DSL-Anschluss kostet zu viel?\n")


class ParserTests(unittest.TestCase):
    """Ebene 1: Die Ruine darf gar nicht erst entstehen."""

    def test_schadensfall_02_10_2026(self):
        titel, desc, body = gd.parse_article(SCHADENSFALL, "Fallback", "rat")
        self.assertEqual(
            titel, "Preiswert surfen: So findest du den optimalen DSL-Anschluss")
        self.assertEqual(
            desc, "Entdecke, wie ein preiswerter Anschluss funktioniert.")
        self.assertTrue(body.startswith("Du hast das Gefühl"),
                        f"Body beginnt mit Prompt-Resten: {body[:60]!r}")

    def test_marker_landet_nie_in_beschreibung_oder_titel(self):
        for roh in (
            SCHADENSFALL,
            "TITLE: A\n\n\nDESCRIPTION: B\n\nText.",
            "DESCRIPTION: B\nTITLE: A\n\nText.",
            "```\nTITLE: A\n---\nDESCRIPTION: B\n\nText.",
            "TITLE: A\n\nText ohne Beschreibung.",
            "\n\nTITLE: A\nDESCRIPTION: B\n\nText.",
        ):
            with self.subTest(roh=roh[:28]):
                titel, desc, body = gd.parse_article(roh, "Fallback", "rat")
                self.assertEqual(sk.prompt_echo_im_feld(titel), "")
                self.assertEqual(sk.prompt_echo_im_feld(desc), "")
                self.assertEqual(sk.politur_ruine_funde(body), [])

    def test_marker_mitten_im_text_wird_entfernt(self):
        roh = ("TITLE: A\nDESCRIPTION: B\n\nErster Absatz.\n\n"
               "KEYWORDS: dsl, tarif\n\nZweiter Absatz.")
        _, _, body = gd.parse_article(roh, "Fallback", "rat")
        self.assertNotIn("KEYWORDS", body)
        self.assertIn("Erster Absatz.", body)
        self.assertIn("Zweiter Absatz.", body)

    def test_deutsche_prosa_bleibt_unangetastet(self):
        """Falsch-Positive wären teurer als der Fehler selbst."""
        prosa = ("Tipp: Vergleiche drei Angebote.\n\n"
                 "Beispiel: 2.500 € netto im Monat.\n\n"
                 "Faustregel: Alle drei Jahre prüfen.\n\n"
                 "Achtung: Die Frist endet am 31.12.\n\n"
                 "Fazit: Der Wechsel lohnt sich.")
        _, _, body = gd.parse_article(
            f"TITLE: A\nDESCRIPTION: B\n\n{prosa}", "Fallback", "rat")
        for satz in prosa.split("\n\n"):
            self.assertIn(satz, body)

    def test_trenner_nach_dem_kopf_verschwindet(self):
        _, _, body = gd.parse_article(
            "TITLE: A\nDESCRIPTION: B\n\n---\n\nText.", "Fallback", "rat")
        self.assertFalse(body.lstrip().startswith("---"),
                         "ein „---“ als erste Body-Zeile ist ein Rest des "
                         "Ausgabeformats, kein Gestaltungselement")

    def test_ohne_marker_funktioniert_der_h1_fallback_weiter(self):
        titel, desc, body = gd.parse_article(
            "# Strom sparen\n\nDer Text beginnt hier.", "Fallback", "rat")
        self.assertEqual(titel, "Strom sparen")
        self.assertEqual(desc, "Der Text beginnt hier.")
        self.assertEqual(body, "Der Text beginnt hier.")


class WacheTests(unittest.TestCase):
    """Ebene 2: Falls der Parser je wieder bricht, blockt die Wache."""

    def test_r16_erkennt_den_schadensfall_im_fliesstext(self):
        funde = {r for r, _ in sk.politur_ruine_funde(SCHADENSFALL)}
        self.assertIn("R16-PROMPT-ECHO", funde)

    def test_r16_erkennt_marker_im_frontmatter(self):
        roh = ('---\n'
               'title: "Preiswert surfen"\n'
               'description: "TITLE: Preiswert surfen: So findest du …"\n'
               'pin_description: "*Werbung | TITLE: Preiswert surfen"\n'
               '---\n\nSauberer Text.\n')
        funde = tg.check_meta_prompt_echo("x", roh)
        self.assertEqual(len(funde), 2, f"beide Felder melden: {funde}")
        self.assertTrue(all(f[1] == "R16-PROMPT-ECHO-META" for f in funde))

    def test_keine_falsch_positiven_im_bestand(self):
        """Die Regel wurde gegen den gesamten Content geprüft."""
        root = SCRIPTS.parent
        treffer = []
        for md in (root / "content").rglob("*.md"):
            txt = md.read_text(encoding="utf-8")
            body = txt.split("---", 2)[2] if txt.startswith("---") else txt
            if any(r == "R16-PROMPT-ECHO"
                   for r, _ in sk.politur_ruine_funde(body)):
                treffer.append(str(md.relative_to(root)))
            treffer += [f[0] for f in tg.check_meta_prompt_echo(
                str(md.relative_to(root)), txt)]
        self.assertEqual(treffer, [],
                         f"R16 schlägt im Bestand an: {treffer}")

    @staticmethod
    def _hard_rules_block(quelle: str) -> str:
        """Der Literal-Block hinter `hard_rules =`, über Klammer-Bilanz."""
        start = quelle.index("hard_rules =")
        auf = min((i for i in (quelle.find("(", start), quelle.find("{", start))
                   if i != -1))
        paare = {"(": ")", "{": "}"}
        zu, tiefe = paare[quelle[auf]], 0
        for i in range(auf, len(quelle)):
            if quelle[i] == quelle[auf]:
                tiefe += 1
            elif quelle[i] == zu:
                tiefe -= 1
                if tiefe == 0:
                    return quelle[auf:i + 1]
        raise AssertionError("hard_rules-Block nicht geschlossen")

    def test_r16_blockiert_hart_in_beiden_gates(self):
        """Eine Regel, die nur meldet, hätte den 02.10. nicht verhindert."""
        for datei in ("textverstaendnis_guard.py", "publish_gate.py"):
            block = self._hard_rules_block(
                (SCRIPTS / datei).read_text(encoding="utf-8"))
            for regel in ("R16-PROMPT-ECHO", "R16-PROMPT-ECHO-META"):
                with self.subTest(datei=datei, regel=regel):
                    self.assertIn(f'"{regel}"', block,
                                  f"{regel} fehlt in den harten Regeln von "
                                  f"{datei}")

    def test_beide_gates_teilen_denselben_harten_regelsatz(self):
        """Zwei Wachen mit verschiedenen Listen = Issue #521 in klein."""
        saetze = {}
        for datei in ("textverstaendnis_guard.py", "publish_gate.py"):
            block = self._hard_rules_block(
                (SCRIPTS / datei).read_text(encoding="utf-8"))
            saetze[datei] = {m for m in
                             __import__("re").findall(r'"(R\d+[A-Z\-]*)"', block)}
        nur_guard = saetze["textverstaendnis_guard.py"] - saetze["publish_gate.py"]
        nur_gate = saetze["publish_gate.py"] - saetze["textverstaendnis_guard.py"]
        self.assertEqual(
            (nur_guard, nur_gate), (set(), set()),
            "Guard und Publish-Gate müssen dieselben Regeln hart führen – "
            "sonst meldet die eine Wache, was die andere durchlässt")

    def test_muster_wohnen_genau_einmal(self):
        """SSOT: sprachkern besitzt die Marker, niemand kopiert sie."""
        quelle = (SCRIPTS / "textverstaendnis_guard.py").read_text(
            encoding="utf-8")
        self.assertIn("from sprachkern import", quelle)
        self.assertIn("prompt_echo_im_feld", quelle)
        self.assertNotIn("METADESCRIPTION|SLUG", quelle,
                         "die Marker-Liste gehört in sprachkern, nicht in "
                         "eine zweite Kopie")

    def test_feld_und_textregel_teilen_die_marker(self):
        self.assertIs(sk.PROMPT_ECHO_RX, sk.POLITUR_RUINEN[-1][1])
        for marker in ("TITLE", "DESCRIPTION", "KEYWORDS", "PILLAR"):
            with self.subTest(marker=marker):
                self.assertTrue(sk.prompt_echo_im_feld(f"{marker}: x"))
                self.assertTrue(sk.politur_ruine_funde(f"{marker}: x"))


class SelbsttestTests(unittest.TestCase):
    def test_guard_selbsttest_ist_gruen(self):
        self.assertEqual(tg.run_selftest(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
