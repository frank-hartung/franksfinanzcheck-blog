"""Vertrag: `offen` ist ARBEIT, `vorlauf` ist Termin – nie ein Befund (#1126).

Stand 10.11.2026 – Dauerheilung des Befunds, der `regression` repo-weit rot
hielt.

`data/faktenfrische_queue.json` trug bis heute drei Namen für zwei Dinge:

  * `offen` / `arbeitsvorrat` (Alias, gleicher Inhalt) – die Arbeitsliste der
    Seiten mit Frist, egal ob fällig oder erst im Vorlauf;
  * `fachbefunde` – offene fachliche Befunde mit `id`, `typ`, `text` und
    `fassung_sha256`.

Der Alias machte den Inhalt nicht ehrlich: Ein Eintrag konnte in `offen`
stehen und im selben Atemzug „frisch geprüft vor 23 Tagen (Intervall 30
Tage)“, `faellig: false`, Frist 14.11. sagen. Wer das las, musste wissen,
dass „offen“ nicht „offen“ bedeutet. Am 07.11. machte genau diese
Doppeldeutigkeit drei Aktentests rot (#763, #823, #911) und blockierte über
`regression` jeden Pull-Request; am 08.11. wurde der Befund als #1126
festgehalten.

SEIT SCHEMA 2 GILT EINE REGEL, AN DER ERZEUGER, MIGRATION UND WÄCHTER HÄNGEN
----------------------------------------------------------------------------
    offen          = ARBEIT: fällig, befundbehaftet oder abgebrochen
    vorlauf        = Termin: Frist rückt, aber (noch) keine Arbeit
    arbeitsvorrat  = Obermenge beider (Planung/Kapazität)
    fachbefunde    = Befunde, ausschließlich hier

Dieser Vertrag prüft die Messhöhe in beide Richtungen:

  * FEHLALARM: Eine turnusgemäß wieder aufgenommene Seite ist Vorlauf, keine
    Arbeit und kein Befund – sie darf keinen Aktentest rot machen.
  * SCHEIN-SICHERHEIT: Ein echter Befund steht in `fachbefunde` und MUSS über
    das Ledger auffindbar sein; `offen` führt ihn nicht mit.
  * STRUKTUR: Die Zerlegung ist vollständig und disjunkt. Ein Vorlauf-Eintrag
    in `offen` ist kein Grenzfall, sondern ein Fehler (#1126).
"""
from pathlib import Path
import ast
import json
import re
import subprocess
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

VORRAT = [
    {"slug": "vorlauf", "titel": "Vorlauf", "grund": "frisch geprüft vor 23 Tagen",
     "faellig": False, "frist": "2026-11-14", "geo": 100},
    {"slug": "faellig", "titel": "Fällig", "grund": "31 Tage seit Prüfung",
     "faellig": True, "frist": "2026-11-10", "geo": 83},
    {"slug": "befund", "titel": "Befund", "grund": "frisch geprüft vor 20 Tagen",
     "faellig": False, "frist": "2026-11-18", "geo": 100, "befund": True},
    {"slug": "abbruch", "titel": "Abbruch", "grund": "Lauf abgebrochen",
     "faellig": False, "frist": "2026-11-20", "geo": 67, "unvollstaendig": True},
]
FACHBEFUND = [{"id": "a" * 20, "slug": "befund", "typ": "luecke",
               "text": "Quelle fehlt", "fassung_sha256": "b" * 64}]


def bauen(vorrat=None, fachbefunde=None, erzeugt="2026-11-10 13:00 UTC"):
    return faktenfrische.queue_daten_bauen(
        uebersicht={}, fachbefunde=(FACHBEFUND if fachbefunde is None
                                    else fachbefunde),
        kapazitaet={}, abbrueche=[],
        arbeitsvorrat=(VORRAT if vorrat is None else vorrat),
        laeufe=[], erzeugt=erzeugt)


def artefakt():
    return json.loads(QUEUE.read_text(encoding="utf-8"))


class QueueSchemaVertrag(unittest.TestCase):
    """Drei Felder, eine Wahrheit – geprüft am Erzeuger und am Artefakt."""

    def test_erzeuger_zerlegt_in_arbeit_und_vorlauf(self):
        qd = bauen()
        self.assertEqual(qd["schema"], faktenfrische.QUEUE_SCHEMA)
        self.assertEqual([e["slug"] for e in qd["offen"]],
                         ["faellig", "befund", "abbruch"])
        self.assertEqual([e["slug"] for e in qd["vorlauf"]], ["vorlauf"])
        self.assertEqual([e["status"] for e in qd["arbeitsvorrat"]],
                         ["vorlauf", "faellig", "befund", "unvollstaendig"])
        # Die Zerlegung ist vollständig und überschneidungsfrei.
        self.assertEqual(
            {e["slug"] for e in qd["offen"]} | {e["slug"] for e in qd["vorlauf"]},
            {e["slug"] for e in qd["arbeitsvorrat"]})
        self.assertFalse({e["slug"] for e in qd["offen"]}
                         & {e["slug"] for e in qd["vorlauf"]})

    def test_frisch_gepruefte_seite_ist_vorlauf_nicht_offen(self):
        """Der gemeldete Befund selbst: „frisch geprüft“ darf nicht „offen“ sein."""
        qd = bauen()
        offen = {e["slug"]: e for e in qd["offen"]}
        self.assertNotIn("vorlauf", offen,
                         "Eine frisch geprüfte Seite steht als ARBEIT in `offen` (#1126)")
        eintrag = qd["vorlauf"][0]
        self.assertEqual(eintrag["status"], "vorlauf")
        self.assertIn("frisch geprüft", eintrag["grund"])

    def test_wache_erkennt_jeden_rueckfall(self):
        """Sabotageproben: Die Invariante ist scharf, nicht dekorativ."""
        qd = bauen()
        faelle = {}
        faelle["vorlauf in offen"] = {**qd, "offen": qd["offen"] + qd["vorlauf"]}
        faelle["arbeit fehlt"] = {**qd, "offen": qd["offen"][:-1]}
        faelle["fällig im vorlauf"] = {**qd, "vorlauf": qd["vorlauf"] + [qd["offen"][0]]}
        faelle["befunddaten im vorrat"] = {
            **qd, "offen": [dict(e, id="c" * 20) for e in qd["offen"]]}
        # Status von Hand verdreht: Die Zerlegung bleibt vollständig, aber der
        # Eintrag behauptet Arbeit, obwohl seine Fakten Vorlauf sind.
        faelle["status verdreht"] = {
            **qd, "offen": qd["offen"] + [dict(qd["vorlauf"][0], status="faellig")],
            "vorlauf": []}
        for name, kaputt in faelle.items():
            with self.subTest(sabotage=name):
                self.assertTrue(faktenfrische.queue_invariante(kaputt),
                                f"Die Wache übersieht: {name}")
        self.assertEqual(faktenfrische.queue_invariante(qd), [])

    def test_artefakt_ist_widerspruchsfrei(self):
        """Die committete Queue muss die Regel erfüllen – nicht erst der Lauf."""
        q = artefakt()
        self.assertEqual(q.get("schema"), faktenfrische.QUEUE_SCHEMA,
                         "Queue-Datei ist nicht auf Schema 2 migriert (#1126)")
        self.assertEqual(faktenfrische.queue_invariante(q), [],
                         "Queue widerspricht ihrem eigenen Vertrag")
        for eintrag in q["offen"]:
            self.assertNotEqual(eintrag.get("status"), "vorlauf")
            self.assertTrue(
                eintrag.get("faellig") or eintrag.get("befund")
                or eintrag.get("unvollstaendig"),
                f"`offen` ohne Arbeit: {eintrag.get('slug')} (#1126)")

    def test_vorrat_traegt_keine_befund_merkmale(self):
        q = artefakt()
        for eintrag in q["arbeitsvorrat"]:
            self.assertIn("frist", eintrag,
                          f"Vorrats-Eintrag ohne Frist: {eintrag}")
            self.assertIn("faellig", eintrag)
            self.assertNotIn("id", eintrag,
                             "Der Arbeitsvorrat ist keine Befundliste – "
                             "ein Befund gehört nach `fachbefunde`.")
            self.assertNotIn("text", eintrag)

    def test_echter_befund_ist_ueber_das_ledger_sichtbar(self):
        """Gegenprobe zur Schein-Sicherheit: Ein Befund MUSS gefunden werden."""
        q = artefakt()
        slug = "2026-10-14-heizperiode-vorbereiten-im-spaetsommer"
        q["fachbefunde"].append({
            "typ": "luecke", "text": " Quelle fehlt", "beleg": "",
            "id": "f" * 20, "slug": slug, "fassung_sha256": "a" * 64,
            "zuletzt_gesehen": "2026-11-10 13:00 UTC"})
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "queue.json"
            pfad.write_text(json.dumps(q), encoding="utf-8")
            treffer = [e for e in ledger.offene_befunde(pfad)
                       if e["slug"] == slug]
        self.assertTrue(treffer,
                        "Ein echter Befund muss über das Ledger auffindbar sein")

    def test_faelligkeit_allein_erzeugt_keinen_befund(self):
        """Gegenprobe zum Fehlalarm: turnusgemäße Wiederaufnahme ist kein Befund."""
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "queue.json"
            qd = bauen()
            pfad.write_text(json.dumps(qd), encoding="utf-8")
            treffer = [e for e in ledger.offene_befunde(pfad)
                       if e["slug"] == "vorlauf"]
        self.assertFalse(treffer,
                         "Fälligkeit ist kein Befund – hier entstand der "
                         "Fehlalarm vom 07.11.")

    def test_schreiber_verweigert_doppelten_slug(self):
        with self.assertRaises(ValueError):
            bauen(vorrat=VORRAT + [dict(VORRAT[0])])


class MigrationUndIdempotenz(unittest.TestCase):
    """Schema 1 → 2 ohne Datenverlust, ohne erfundene Fristen, idempotent."""

    def test_migration_hebt_alten_bestand_und_aendert_ihn_nicht(self):
        alt = artefakt()
        alt.pop("schema", None)
        alt.pop("vorlauf", None)
        # Schema-1-Form: `offen` ist die einzige Arbeitsliste.
        alt["arbeitsvorrat"] = [dict(e, status="vorlauf")
                                for e in alt.get("arbeitsvorrat", [])]
        alt["offen"] = alt["arbeitsvorrat"]
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "queue.json"
            pfad.write_text(json.dumps(alt, ensure_ascii=False), encoding="utf-8")
            bericht = faktenfrische.queue_normalisieren(apply=True, pfad=str(pfad))
            self.assertTrue(bericht["ok"], bericht)
            einmal = pfad.read_text(encoding="utf-8")
            neu = json.loads(einmal)
            self.assertEqual(neu["schema"], faktenfrische.QUEUE_SCHEMA)
            self.assertEqual(faktenfrische.queue_invariante(neu), [])
            # Kein Eintrag verloren, kein Termin erfunden.
            alt_slugs = {e["slug"] for e in alt["arbeitsvorrat"]}
            self.assertEqual({e["slug"] for e in neu["arbeitsvorrat"]}, alt_slugs)
            self.assertEqual(
                {e["slug"]: e["frist"] for e in alt["arbeitsvorrat"]},
                {e["slug"]: e["frist"] for e in neu["arbeitsvorrat"]})
            # Zweiter Lauf ändert nichts (Byte-Vergleich ohne Zeitstempel).
            faktenfrische.queue_normalisieren(apply=True, pfad=str(pfad))
            self.assertEqual(pfad.read_text(encoding="utf-8"), einmal)

    def test_cli_bietet_den_trockenlauf(self):
        ergebnis = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "faktenfrische.py"),
             "--queue-normalisieren"],
            capture_output=True, text=True, cwd=str(ROOT), timeout=300)
        self.assertEqual(ergebnis.returncode, 0, ergebnis.stderr)
        self.assertIn("Trockenlauf", ergebnis.stdout)
        self.assertNotIn("🛑", ergebnis.stdout + ergebnis.stderr)


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

    def test_die_drei_tests_fragen_das_ledger_und_den_vorlauf(self):
        for name in BETROFFENE:
            quelle = (TESTS / name).read_text(encoding="utf-8")
            self.assertIn("ledger.offene_befunde", quelle,
                          f"{name} muss offene Befunde über das Ledger lesen")
            self.assertIn("eintraege_in_offen", quelle,
                          f"{name} muss prüfen, dass die Seite nicht als ARBEIT "
                          f"in `offen` steht (#1126)")


class FeldnameBleibtEhrlich(unittest.TestCase):
    """Der Schreiber darf die Zerlegung nicht wieder selbst zusammensetzen."""

    def test_schreibpfad_nutzt_die_reine_funktion(self):
        quelle = (ROOT / "scripts" / "faktenfrische.py").read_text(encoding="utf-8")
        self.assertIn("queue_daten_bauen(", quelle)
        # Der Datensatz darf nicht mehr inline zusammengebaut werden.
        self.assertNotIn('"offen": [{"slug"', quelle,
                         "Der Datensatz wird wieder inline gebaut – dann können "
                         "die drei Feldnamen auseinanderlaufen.")
        self.assertNotIn('"offen": arbeitsvorrat', quelle,
                         "`offen` ist wieder ein Alias des Arbeitsvorrats – "
                         "genau die Doppeldeutigkeit aus #1126.")
        self.assertIn("queue_status_von(", quelle,
                      "Der Status muss aus den Fakten abgeleitet, nicht gesetzt werden")
        self.assertIn("queue_invariante(", quelle,
                      "Der Schreiber muss den Datensatz vor dem Schreiben prüfen")

    def test_selbsttest_deckt_die_messhoehe_ab(self):
        quelle = (ROOT / "scripts" / "faktenfrische.py").read_text(encoding="utf-8")
        for fall in ("ST9a", "ST9b", "ST9c", "ST9d", "ST9e", "ST9f",
                     "ST9g", "ST9h", "ST9i", "ST9j", "ST9k"):
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
