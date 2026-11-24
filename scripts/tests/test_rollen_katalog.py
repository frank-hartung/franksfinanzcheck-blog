#!/usr/bin/env python3
"""Der Rollenkatalog ist ein Gate, kein Dokument (#1365-Nachbar, 24.11.2026).

WARUM DIESE DATEI
=================
Am 23.11.2026 wurde entschieden, die 54 Beiträge ohne Rolle in drei Wellen bis
15.12. zu kuratieren. Am 24.11. lag der Katalog (`data/rollen_katalog.yaml`)
fertig vor und wurde mit einem Befehl eingespielt – 16 Cluster, keine Ausnahmen,
alle sechs Pillars vollständig. Damit ist die *Frist* erledigt, aber die Arbeit
beginnt erst: Ein Katalog, den niemand prüft, verrottet wie jede Liste.

Diese Tests halten drei Zusagen:

  1. Der Katalog ist vollständig und widerspruchsfrei (`rollen_katalog.pruefen`):
     keine Lücke, keine doppelte Rolle, keine Kollision in den ersten 40 Zeichen
     des Titels (R4), kein Entwurf im Katalog (R3).
  2. Die Map trägt den Katalog: Einspielen ist idempotent, die Ausnahmen sind
     abgeschafft, und die Rollenpflicht gilt für alle sechs Pillars.
  3. Ein neuer Beitrag ohne Rolle fällt auf. Das ist der eigentliche Zweck –
     nicht die Zahl 54, sondern dass 55 nicht still passiert.
"""
from __future__ import annotations

import hashlib
import sys
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))

import rollen_katalog  # noqa: E402
import yaml  # noqa: E402

MAP = SCRIPTS.parent / "data" / "kannibalisierung_map.yaml"
KATALOG = SCRIPTS.parent / "data" / "rollen_katalog.yaml"


class KatalogTest(unittest.TestCase):
    def test_katalog_ist_widerspruchsfrei(self):
        befunde = rollen_katalog.pruefen(rollen_katalog.katalog_laden())
        self.assertEqual(befunde, [], f"Katalog nicht sauber: {befunde[:5]}")

    def test_jeder_oeffentliche_beitrag_hat_eine_rolle(self):
        posts = rollen_katalog.bestand()
        rollen = rollen_katalog.rollen_in_map()
        ohne = sorted(s for s, p in posts.items() if not p["entwurf"] and s not in rollen)
        self.assertEqual(ohne, [], f"Ohne Rolle: {ohne[:5]}")

    def test_katalog_und_map_stimmen_ueberein(self):
        katalog = rollen_katalog.katalog_laden()
        im_katalog = {b["slug"] for c in katalog["cluster"] for b in c["beitraege"]}
        in_map = rollen_katalog.rollen_in_map()
        self.assertEqual(sorted(im_katalog - in_map), [],
                         "Katalog nennt Beiträge, die die Map nicht kennt")
        posts = rollen_katalog.bestand()
        self.assertEqual(sorted(s for s in im_katalog if posts[s]["entwurf"]), [],
                         "Entwürfe im Katalog verletzen R3")


class MapAbdeckungTest(unittest.TestCase):
    @staticmethod
    def _map():
        return yaml.safe_load(MAP.read_text(encoding="utf-8")) or {}

    def test_keine_ausnahmen_mehr(self):
        self.assertEqual(self._map()["abdeckung"]["ausnahmen"], [],
                         "Die Ausnahmen vom 23.11. sollten am 24.11. entfallen sein")

    def test_alle_pillars_sind_vollstaendig(self):
        pillars = {p["pillar"] for p in self._map()["abdeckung"]["vollstaendige_pillars"]}
        erwartet = {"internet-dsl", "strom-sparen", "frugalismus",
                    "konto-karten", "mietwagen", "versicherungen"}
        self.assertEqual(pillars, erwartet)

    def test_gas_cluster_gehoeren_zur_strom_abdeckung(self):
        """K1/K2 bedienen `strom-sparen`, obwohl der Katalog sie nicht nennt.

        Wer die Abdeckung nur aus dem Katalog ableitet, macht neun
        Gas-/Heizungsbeiträge sofort rot – beim ersten Einspielen passiert.
        """
        zuordnung = {p["pillar"]: p["cluster"]
                     for p in self._map()["abdeckung"]["vollstaendige_pillars"]}
        self.assertIn("K1-gas-preisgarantie", zuordnung["strom-sparen"])
        self.assertIn("K2-gasrechnung-heizkosten", zuordnung["strom-sparen"])

    def test_einspielen_ist_idempotent(self):
        vorher = hashlib.sha256(MAP.read_bytes()).hexdigest()
        rollen_katalog.uebernehmen(rollen_katalog.katalog_laden())
        nachher = hashlib.sha256(MAP.read_bytes()).hexdigest()
        self.assertEqual(vorher, nachher,
                         "`--uebernehmen` hat die Map verändert, obwohl nichts fehlte")


if __name__ == "__main__":
    unittest.main()
