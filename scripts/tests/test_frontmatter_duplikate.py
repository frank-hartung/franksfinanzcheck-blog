"""Frontmatter-Vertrag: keine doppelten YAML-Schlüssel im Bestand.

Anlass (26.10.2026): Zwei parallel gemergte PRs schrieben je eine
`description`-Zeile in denselben Artikel. PyYAML liest das still (letzter
gewinnt), Hugo bricht ab (`mapping key "description" already defined`) – und
zwar erst in der CI, mitten im Deploy. `main` lieferte für rund eine Stunde
keinen Build mehr aus.

Diese Prüfung ist absichtlich strenger als `yaml.safe_load`: Sie lehnt
doppelte Schlüssel ab, statt sie zu überschreiben. Zusätzlich gilt der Vertrag
für die Schreibseite: `sprachkern.setze_description` darf nie eine zweite
Zeile erzeugen – auch nicht auf bereits kaputtem Frontmatter.
"""
from __future__ import annotations

import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import sprachkern  # noqa: E402

FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*(?:\n|$)", re.S)


class EindeutigeSchluessel(yaml.SafeLoader):
    """SafeLoader, der doppelte Schlüssel als Fehler behandelt."""


def _keine_doppelten(loader, node, deep=False):
    gesehen = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in gesehen:
            raise yaml.YAMLError(f"doppelter Schlüssel: {key}")
        gesehen[key] = loader.construct_object(value_node, deep=deep)
    return gesehen


EindeutigeSchluessel.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _keine_doppelten)


def _dateien():
    for pfad in sorted((ROOT / "content").rglob("*.md")):
        m = FRONTMATTER.match(pfad.read_text(encoding="utf-8"))
        if m:
            yield pfad, m.group(1)


class BestandVertrag(unittest.TestCase):
    def test_keine_doppelten_frontmatter_schluessel(self):
        kaputt = []
        for pfad, fm in _dateien():
            try:
                yaml.load(fm, Loader=EindeutigeSchluessel)
            except yaml.YAMLError as exc:
                kaputt.append(f"{pfad.relative_to(ROOT)}: {str(exc).splitlines()[0]}")
        self.assertEqual(kaputt, [], "Doppelte Frontmatter-Schlüssel:\n" + "\n".join(kaputt))


class SchreibVertrag(unittest.TestCase):
    def test_setzen_entfernt_duplikate_und_bleibt_idempotent(self):
        fm = ('title: "A: B"\ndescription: "Alt: x"\n'
              'description: "Zweit: y"\n\ndate: 2026-01-01\n')
        neu = sprachkern.setze_description(fm, "Neu: z")
        self.assertEqual(neu.count("description:"), 1)
        self.assertIn('description: "Neu: z"', neu)
        self.assertEqual(sprachkern.setze_description(neu, "Neu: z"), neu)

    def test_setzen_haengt_direkt_hinter_den_titel(self):
        neu = sprachkern.setze_description('title: "T"\ndate: 2026-01-01\n', "D")
        self.assertEqual(neu.splitlines()[:2], ['title: "T"', 'description: "D"'])

    def test_rebuild_bricht_statt_zu_duplizieren(self):
        artikel = {"fm": 'title: "T"\ndescription: "A"\ndescription: "B"\n',
                   "prefix": "", "path": "x"}
        text = sprachkern.rebuild(artikel, "Body\n", "Neu")
        self.assertEqual(text.count("description:"), 1)

    def test_anfuehrungszeichen_und_zeilenumbrueche_bleiben_kontrolliert(self):
        neu = sprachkern.setze_description('title: "T"\n', 'Er sagt "Hallo"\nZweite Zeile')
        self.assertNotIn('"Hallo"', neu.split("description:")[1].splitlines()[0])
        self.assertEqual(len(neu.splitlines()), 2)


if __name__ == "__main__":
    unittest.main()
