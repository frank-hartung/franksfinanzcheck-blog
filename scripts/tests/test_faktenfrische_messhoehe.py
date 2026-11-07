"""Vertrag: Offene BEFUNDE werden dort gemessen, wo sie stehen (#763/#823/#911).

Stand 07.11.2026 – Lehre aus einem Fehlalarm, der jeden Pull-Request blockiert hat.

`data/faktenfrische_queue.json` trägt zwei Dinge, die sich ähnlich anfühlen und
nichts miteinander zu tun haben:

  * `arbeitsvorrat` (Alias `offen`) – Seiten, die noch nicht dran waren, MIT
    FRIST. Eine Seite steht dort turnusgemäß, sobald ihre Faktenprüfung älter
    als das Intervall ist. Das ist normal und kein Fehler.
  * `fachbefunde` – offene fachliche Befunde, mit `id`, `typ`, `text` und
    `fassung_sha256`.

Drei Rückfall-Tests lasen bis heute `queue['offen']` und nannten das „offene
Befunde“. Das war in BEIDE Richtungen falsch:

  * Fehlalarm (07.11.2026): Die Heizperiode rutschte turnusgemäß wieder in den
    Vorrat („frisch geprüft vor 23 Tagen“) → CI-Job „Code-Regression“ rot, an
    drei Testmodulen, ohne einen einzigen Sachfehler. Der PR war blockiert.
  * Schein-Sicherheit: Ein echter zurückgekehrter Befund steht in
    `fachbefunde`; über `offen` gemessen wäre er unsichtbar geblieben.

Dieser Vertrag prüft die Messhöhe selbst – und zwar in beide Richtungen:
Er lässt den Fehlalarm nicht zurückkehren UND er lässt die Schein-Sicherheit
nicht zurückkehren. Ein Vertrag, der nur eines von beidem prüft, wäre die
halbe Heilung.
"""
from pathlib import Path
import ast
import json
import re
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import faktenfrische  # noqa: E402
import faktenfrische_befund_ledger as ledger  # noqa: E402

QUEUE = ROOT / "data" / "faktenfrische_queue.json"
TESTS = ROOT / "scripts" / "tests"

# Die drei Module, in denen die falsche Messhöhe stand.
BETROFFENE = ("test_faktenfrische_763.py", "test_faktenfrische_823.py",
              "test_faktenfrische_911.py")


class MesshoeheVertrag(unittest.TestCase):
    """Die Queue hat zwei Felder – und beide werden richtig gelesen."""

    def test_vorrat_und_befunde_sind_getrennte_felder(self):
        """Der ERZEUGER schreibt beide Namen – das ist der scharfe Teil.

        Das Artefakt auf der Platte ist bewusst nicht der Zeuge: Es wurde am
        06.11. geschrieben, also vor der Heilung, und wird erst vom nächsten
        Lauf nachgezogen. Ein Test, der ein Datenartefakt zur Wahrheit macht,
        wäre am Tag nach der Heilung rot – genau der Fehler, den dieser
        Vertrag verhindert.
        """
        qd = faktenfrische.queue_daten_bauen(
            uebersicht={}, fachbefunde=[], kapazitaet={}, abbrueche=[],
            arbeitsvorrat=[{"slug": "x", "frist": "2026-11-14"}], laeufe=[],
            erzeugt="2026-11-07 13:00 UTC")
        self.assertIn("arbeitsvorrat", qd, "Arbeitsvorrat muss einen eigenen Namen haben")
        self.assertIn("fachbefunde", qd, "Befundliste muss vorhanden sein")
        self.assertEqual(qd["offen"], qd["arbeitsvorrat"])

    def test_artefakt_bleibt_widerspruchsfrei(self):
        """Trägt die Datei den neuen Namen, muss der Alias gleich sein."""
        q = json.loads(QUEUE.read_text(encoding="utf-8"))
        if "arbeitsvorrat" in q:
            self.assertEqual(q["offen"], q["arbeitsvorrat"],
                             "Zwei Feldnamen mit verschiedenem Inhalt – zwei Wahrheiten.")

    def test_vorrat_traegt_keine_befund_merkmale(self):
        q = json.loads(QUEUE.read_text(encoding="utf-8"))
        vorrat = q.get("arbeitsvorrat", q["offen"])
        for eintrag in vorrat:
            self.assertIn("frist", eintrag,
                          f"Vorrats-Eintrag ohne Frist: {eintrag}")
            self.assertNotIn("id", eintrag,
                             "Der Arbeitsvorrat ist keine Befundliste – "
                             "ein Befund gehört nach `fachbefunde`.")
            self.assertNotIn("text", eintrag)

    def test_echter_befund_ist_ueber_das_ledger_sichtbar(self):
        """Gegenprobe zur Schein-Sicherheit: Ein Befund MUSS gefunden werden."""
        q = json.loads(QUEUE.read_text(encoding="utf-8"))
        slug = "2026-10-14-heizperiode-vorbereiten-im-spaetsommer"
        q["fachbefunde"].append({
            "typ": "luecke", "text": " Quelle fehlt", "beleg": "",
            "id": "f" * 20, "slug": slug, "fassung_sha256": "a" * 64,
            "zuletzt_gesehen": "2026-11-07 13:00 UTC"})
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "queue.json"
            pfad.write_text(json.dumps(q), encoding="utf-8")
            treffer = [e for e in ledger.offene_befunde(pfad) if e["slug"] == slug]
        self.assertTrue(treffer, "Ein echter Befund muss über das Ledger auffindbar sein")

    def test_faelligkeit_allein_erzeugt_keinen_befund(self):
        """Gegenprobe zum Fehlalarm: turnusgemäße Wiederaufnahme ist kein Befund."""
        q = json.loads(QUEUE.read_text(encoding="utf-8"))
        slug = "2026-10-14-heizperiode-vorbereiten-im-spaetsommer"
        q["arbeitsvorrat"] = list(q.get("arbeitsvorrat", q["offen"])) + [{
            "slug": slug, "titel": "turnusgemäß", "grund": "frisch geprüft vor 23 Tagen",
            "faellig": False, "frist": "2026-11-14", "geo": 100}]
        q["offen"] = q["arbeitsvorrat"]
        q["fachbefunde"] = [b for b in q["fachbefunde"] if b["slug"] != slug]
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "queue.json"
            pfad.write_text(json.dumps(q), encoding="utf-8")
            treffer = [e for e in ledger.offene_befunde(pfad) if e["slug"] == slug]
        self.assertFalse(treffer,
                         "Fälligkeit ist kein Befund – hier entstand der Fehlalarm vom 07.11.")

    def test_bauende_funktion_ist_rein(self):
        """Ein Datensatz, zwei Namen – ohne Datei, ohne Uhr, ohne Netz."""
        vorrat = [{"slug": "x", "titel": "X", "grund": "g", "faellig": False,
                   "frist": "2026-11-14", "geo": 100}]
        befund = [{"id": "a" * 20, "slug": "x", "typ": "luecke", "text": "t",
                   "fassung_sha256": "b" * 64}]
        qd = faktenfrische.queue_daten_bauen(
            uebersicht={}, fachbefunde=befund, kapazitaet={}, abbrueche=[],
            arbeitsvorrat=vorrat, laeufe=[], erzeugt="2026-11-07 13:00 UTC")
        self.assertEqual(qd["offen"], qd["arbeitsvorrat"])
        self.assertIs(qd["fachbefunde"], befund)
        self.assertEqual(set(qd), {"erzeugt", "uebersicht", "fachbefunde",
                                   "kapazitaet", "abbrueche", "arbeitsvorrat",
                                   "offen", "laeufe"})


class KeinRueckfallInsFalscheFeld(unittest.TestCase):
    """Die drei reparierten Tests dürfen nicht wieder `['offen']` messen."""

    def test_kein_test_liest_befunde_aus_dem_vorrat(self):
        befund, geprueft = [], 0
        for name in BETROFFENE:
            pfad = TESTS / name
            self.assertTrue(pfad.exists(), name)
            quelle = pfad.read_text(encoding="utf-8")
            baum = ast.parse(quelle)
            # Die drei Rückfall-Tests müssen überhaupt noch existieren.
            geprueft += sum(1 for k in ast.walk(baum)
                            if isinstance(k, ast.FunctionDef) and "befunde" in k.name)
            for knoten in ast.walk(baum):
                # NUR Zugriffe auf die QUEUE zählen. `geo["offen"]` ist die
                # Liste offener GEO-Kriterien – ein anderes Feld mit gleichem
                # Namen; eine Prüfung, die das mitzählt, wäre selbst falsch.
                ziel = None
                if isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Attribute) \
                        and knoten.func.attr == "get" and knoten.args \
                        and isinstance(knoten.args[0], ast.Constant) \
                        and knoten.args[0].value == "offen":
                    ziel = knoten.func.value
                elif isinstance(knoten, ast.Subscript) and isinstance(knoten.slice, ast.Constant) \
                        and knoten.slice.value == "offen":
                    ziel = knoten.value
                if ziel is None:
                    continue
                name_ziel = ziel.id if isinstance(ziel, ast.Name) else (
                    ziel.attr if isinstance(ziel, ast.Attribute) else "")
                if "queue" in name_ziel.lower():
                    befund.append(f"{name}:{knoten.lineno} liest {name_ziel}['offen']")
        self.assertEqual(befund, [],
                         "Offene Befunde werden aus dem Arbeitsvorrat gelesen – "
                         "das erzeugt Fehlalarme und verbirgt echte Rückfälle.")
        self.assertGreaterEqual(geprueft, 3, "Die drei Rückfall-Tests müssen existieren")

    def test_die_drei_tests_fragen_das_ledger(self):
        for name in BETROFFENE:
            quelle = (TESTS / name).read_text(encoding="utf-8")
            self.assertIn("ledger.offene_befunde", quelle,
                          f"{name} muss offene Befunde über das Ledger lesen")


class FeldnameBleibtEhrlich(unittest.TestCase):
    """Der Name `arbeitsvorrat` darf nicht wieder verschwinden."""

    def test_schreibpfad_nutzt_die_reine_funktion(self):
        quelle = (ROOT / "scripts" / "faktenfrische.py").read_text(encoding="utf-8")
        self.assertIn("queue_daten_bauen(", quelle)
        # Der Datensatz darf nicht mehr inline zusammengebaut werden.
        self.assertNotIn('"offen": [{"slug"', quelle,
                         "Der Datensatz wird wieder inline gebaut – dann können "
                         "die beiden Feldnamen auseinanderlaufen.")

    def test_selbsttest_deckt_die_messhoehe_ab(self):
        quelle = (ROOT / "scripts" / "faktenfrische.py").read_text(encoding="utf-8")
        for fall in ("ST9a", "ST9b", "ST9c", "ST9d", "ST9e", "ST9f"):
            self.assertIn(f'pruefe("{fall}"', quelle,
                          f"{fall} fehlt: der Selbsttest prüft die Messhöhe nicht mehr")

    def test_selbsttest_haengt_nicht_am_netz(self):
        """Ein Selbsttest, der main() ruft, hing am Recherche-Netz (#138)."""
        quelle = (ROOT / "scripts" / "faktenfrische.py").read_text(encoding="utf-8")
        baum = ast.parse(quelle)
        rufender = None
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.FunctionDef) and knoten.name == "selftest":
                rufender = knoten
                break
        self.assertIsNotNone(rufender, "selftest() fehlt")
        # ECHTER Aufruf, nicht das Wort im Kommentar: main() innerhalb von
        # selftest() zog die ganze Recherche (Netz, Uhr, Dateien) nach.
        aufrufe = [k.func.id for k in ast.walk(rufender)
                   if isinstance(k, ast.Call) and isinstance(k.func, ast.Name)]
        self.assertNotIn("main", aufrufe,
                         "Der Selbsttest darf main() nicht aufrufen – das hing "
                         "am Netz und wurde von der KI-Probe zu Recht erschlagen.")


if __name__ == "__main__":
    unittest.main()
