#!/usr/bin/env python3
"""Regressionen des Artefakt-Wächters (Dauerheilung #653, WF-D4E0, 08.10.2026).

Warum diese Tests existieren: Sechs Nächte hintereinander meldete der harte
End-Gate der Content-Reserve „🛑 RESERVE-ENGPAß: nur 0/6 Kandidaten
gate-fertig“ – und in keiner dieser Nächte war der Vorrat leer.
`data/reserve-readiness.json` lag nach einem Merge als strukturell kaputtes
JSON in `main`, `data/reserve-quarantine.json` gleich mit. Der End-Gate fing
den Parse-Fehler und zählte „0 bereit“: **Ein Artefakt-Defekt sah aus wie ein
leerer Lagerbestand.** Die Reparatur lief sechs Nächte in die falsche
Richtung, weil niemand die Artefakte gegenlas.

Diese Fälle frieren drei Dinge ein:
  1. Jede der sechs Klassen wird erkannt – und keine erfindet Funde.
     (Eine Wache mit Fehlalarmen wird abgeschaltet; eine blinde ist Deko.)
  2. `--heal` verändert die AUSSAGE einer Datei nicht (letzter Eintrag
     gewinnt == `json.loads`-Semantik) und ist idempotent.
  3. Ein unlesbares Artefakt wird NICHT rekonstruiert (fail-closed):
     Wer Inhalt erfindet, macht aus einem Defekt eine Lüge.
"""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import artefakt_waechter as aw  # noqa: E402

SKRIPT = ROOT / "scripts" / "artefakt_waechter.py"


def _baum(faelle: dict[str, str]) -> Path:
    """Legt einen Mini-Korpus an: {relativer Pfad: Inhalt}."""
    tmp = Path(tempfile.mkdtemp(prefix="aw-test-"))
    for rel, inhalt in faelle.items():
        ziel = tmp / rel
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")
    return tmp


class ErkennungTests(unittest.TestCase):
    """A1–A6: erkannt wird, was kein Leser der Kette mehr lesen kann."""

    def test_a1_kaputtes_json_wird_erkannt(self):
        # Exakt die Form, die am 08.10.2026 in main stand: der zweite
        # Zertifikatsstand wurde mitten in einen offenen Block geklebt.
        tmp = _baum({"data/reserve-readiness.json":
                     '{\n  "target": 6,\n  "ready": 2,\n'
                     '  "candidates": [\n'
                     '    {"slug": "a", "ready": true, '
                     '"parts": {"spelling": 0.5},\n'
                     '    {"slug": "b", "ready": true}\n  ]\n}\n'})
        funde = aw.pruefe_alle(tmp)
        self.assertTrue([f for f in funde if f.klasse.startswith("A1")], funde)
        self.assertFalse(any(f.heilbar for f in funde if f.klasse.startswith("A1")),
                         "A1 darf nie automatisch geheilt werden")

    def test_a2_doppelter_schluessel_wird_erkannt_und_ist_heilbar(self):
        tmp = _baum({"data/x.json": '{\n  "a": 1,\n  "a": 2\n}\n'})
        funde = aw.pruefe_alle(tmp)
        a2 = [f for f in funde if f.klasse.startswith("A2")]
        self.assertEqual(len(a2), 1, funde)
        self.assertTrue(a2[0].heilbar)
        self.assertIn("a", a2[0].ort, a2[0].meldung)

    def test_a2_gleicher_schluessel_auf_verschiedenen_ebenen_ist_kein_fund(self):
        # Negativprobe: ein Schlüssel ist nur Innerhalb SEINER Ebene doppelt.
        tmp = _baum({"data/x.json": '{"a": {"k": 1}, "b": {"k": 2}}\n'})
        self.assertFalse([f for f in aw.pruefe_alle(tmp) if f.klasse.startswith("A2")])

    def test_a2_gleicher_schluessel_in_listeneintraegen_ist_kein_fund(self):
        tmp = _baum({"data/x.json": '{"l": [{"k": 1}, {"k": 2}]}\n'})
        self.assertFalse([f for f in aw.pruefe_alle(tmp) if f.klasse.startswith("A2")])

    def test_a3_kaputte_jsonl_zeile_wird_mit_nummer_erkannt(self):
        tmp = _baum({"data/tagebuch.jsonl":
                     '{"a": 1}\nkein json\n{"b": 2}\n'})
        funde = [f for f in aw.pruefe_alle(tmp) if f.klasse.startswith("A3")]
        self.assertEqual(len(funde), 1, funde)
        self.assertIn("Zeile 2", funde[0].ort)

    def test_a4_konfliktmarker_werden_erkannt(self):
        tmp = _baum({"data/x.json":
                     '{\n<<<<<<< HEAD\n  "a": 1\n=======\n'
                     '  "a": 2\n>>>>>>> other\n}\n'})
        funde = [f for f in aw.pruefe_alle(tmp) if f.klasse.startswith("A4")]
        self.assertTrue(funde, "Konfliktmarker müssen auffallen")

    def test_a5_yaml_doppelter_schluessel_wird_erkannt(self):
        tmp = _baum({"data/x.yaml": "a: 1\na: 2\n"})
        funde = [f for f in aw.pruefe_alle(tmp) if f.klasse.startswith("A5")]
        self.assertTrue(funde, "doppelter YAML-Schlüssel muss auffallen")

    def test_a5_yaml_doppelter_schluessel_in_liste_ist_kein_fund(self):
        tmp = _baum({"data/x.yaml": "items:\n  - k: 1\n  - k: 2\n"})
        self.assertFalse([f for f in aw.pruefe_alle(tmp) if f.klasse.startswith("A5")])

    def test_a6_frontmatter_doppelter_schluessel_wird_erkannt(self):
        # Hugo stirbt daran beim Bauen mit „mapping key … already defined“.
        tmp = _baum({"content/p/index.md":
                     "---\ntitle: \"A\"\ntitle: \"B\"\n---\n\nText\n"})
        funde = [f for f in aw.pruefe_alle(tmp) if f.klasse.startswith("A6")]
        self.assertTrue(funde)

    def test_a6_ohne_frontmatter_ist_kein_fund(self):
        tmp = _baum({"content/p/index.md": "## Nur Text\n\nNichts davor.\n"})
        self.assertFalse([f for f in aw.pruefe_alle(tmp) if f.klasse.startswith("A6")])

    def test_heiler_korpus_bleibt_still(self):
        """Kein Fehlalarm: ein sauberer Korpus liefert null Funde."""
        tmp = _baum({
            "data/gut.json": '{"a": 1, "b": {"c": [1, 2]}}\n',
            "data/gut.jsonl": '{"a": 1}\n{"b": 2}\n',
            "data/gut.yaml": "a: 1\nb:\n  - 1\n  - 2\n",
            "content/gut/index.md": "---\ntitle: \"A\"\ndate: 2026-10-08\n---\n\nText\n",
        })
        self.assertEqual(aw.pruefe_alle(tmp), [])

    def test_leere_und_unlesbare_dateien_zerstoeren_die_wache_nicht(self):
        tmp = _baum({"data/leer.json": "", "data/leer.yaml": ""})
        self.assertIsInstance(aw.pruefe_alle(tmp), list)

    def test_ohne_yaml_werkzeug_gibt_es_keinen_freispruch(self):
        """#661: Fehlt das Werkzeug, ist das ein Befund – nie Stille.

        Vier Stunden lang war der Integritäts-Lock rot, weil das CI kein
        PyYAML hatte (`actions/setup-python` bringt es nicht mit) und die
        Wache daraufhin „nichts gefunden“ meldete, wo sie „nichts gemessen“
        hätte sagen müssen. Ein Hart-Gate ohne Messwerkzeug darf nicht grün
        werden – es muss sagen, dass es blind ist.
        """
        sauber = _baum({"data/x.yaml": "a: 1\nb: 2\n"})
        blind = aw.pruefe_yaml(sauber / "data" / "x.yaml", "data/x.yaml",
                               mit_werkzeug=False)
        self.assertTrue(any("NICHT geprüft" in f.meldung for f in blind),
                        "ohne Werkzeug darf die Wache nicht schweigen")

        kaputt = _baum({"data/x.yaml": "a: 1\na: 2\n"})
        funde = aw.pruefe_yaml(kaputt / "data" / "x.yaml", "data/x.yaml",
                               mit_werkzeug=False)
        self.assertTrue(any("doppelte" in f.meldung for f in funde),
                        "doppelte Schlüssel finden der eigene Scanner auch "
                        "ohne Drittwerkzeug")

    def test_ohne_yaml_werkzeug_bleibt_auch_frontmatter_laut(self):
        tmp = _baum({"content/p/index.md":
                     "---\ntitle: \"A\"\ndraft: true\n---\n\nText\n"})
        blind = aw.pruefe_frontmatter(tmp / "content" / "p" / "index.md",
                                      "content/p/index.md",
                                      mit_werkzeug=False)
        self.assertTrue(any("NICHT geprüft" in f.meldung for f in blind))

    def test_yaml_werkzeug_da_heisst_vollstaendig_pruefen(self):
        """Mit Werkzeug ist „nicht geprüft“ nie zu sehen (kein Dauer-Alarm)."""
        if aw._yaml_modul() is None:  # pragma: no cover – Umgebung ohne PyYAML
            self.skipTest("PyYAML nicht installiert")
        sauber = _baum({"data/x.yaml": "a: 1\nb: 2\n",
                        "content/p/index.md":
                        "---\ntitle: \"A\"\n---\n\nText\n"})
        self.assertEqual(aw.pruefe_yaml(sauber / "data" / "x.yaml"), [])
        self.assertEqual(
            aw.pruefe_frontmatter(sauber / "content" / "p" / "index.md"), [])


class HeilungsTests(unittest.TestCase):
    """`--heal` darf die Aussage nie verändern – und nie Inhalt erfinden."""

    def test_heilung_laesst_die_aussage_unveraendert(self):
        alt = '{\n  "a": 1,\n  "a": 2,\n  "b": {"k": 9}\n}\n'
        tmp = _baum({"data/x.json": alt})
        ziel = tmp / "data" / "x.json"
        neu = ziel.read_text(encoding="utf-8")
        self.assertEqual(json.loads(neu), json.loads(alt),
                         "vor der Heilung muss die Lesart identisch sein")
        geheilt, meldung = aw.heile_json_doppelt(ziel)
        self.assertTrue(geheilt, meldung)
        self.assertEqual(json.loads(ziel.read_text(encoding="utf-8")),
                         json.loads(alt),
                         "nach der Heilung muss dieselbe Aussage stehen")
        self.assertNotIn('"a": 1', ziel.read_text(encoding="utf-8"),
                         "der verworfene Eintrag darf nicht zurückkehren")

    def test_heilung_ist_idempotent(self):
        tmp = _baum({"data/x.json": '{"a": 1, "a": 2}\n'})
        ziel = tmp / "data" / "x.json"
        self.assertTrue(aw.heile_json_doppelt(ziel)[0])
        stand = ziel.read_text(encoding="utf-8")
        self.assertFalse(aw.heile_json_doppelt(ziel)[0],
                         "ein zweiter Lauf darf nichts mehr zu tun haben")
        self.assertEqual(ziel.read_text(encoding="utf-8"), stand)

    def test_heilung_erhaelt_den_einzug_des_bestands(self):
        """Ein Diff-Schock ist Merge-Material – die Heilung schreibt um,
        wie der Bestand schon schreibt (#653)."""
        for stufe in (2, 4):
            with self.subTest(einzug=stufe):
                # Von Hand gebaut: ein Python-Dict würde den doppelten
                # Schlüssel beim Erzeugen schon selbst verwerfen.
                s = " " * stufe
                alt = ("{\n"
                       f'{s}"a": 1,\n'
                       f'{s}"a": 2,\n'
                       f'{s}"b": {{\n'
                       f'{s * 2}"k": 9\n'
                       f'{s}}}\n'
                       "}\n")
                tmp = _baum({"data/x.json": alt})
                ziel = tmp / "data" / "x.json"
                self.assertTrue(aw.heile_json_doppelt(ziel)[0])
                neu = ziel.read_text(encoding="utf-8")
                self.assertEqual(json.loads(neu), json.loads(alt))
                zeilen = [z for z in neu.splitlines() if z.strip() == '"b": {']
                self.assertTrue(zeilen, neu)
                self.assertEqual(len(zeilen[0]) - len(zeilen[0].lstrip()), stufe,
                                 f"Einzug {stufe} wurde nicht erhalten:\n{neu}")

    def test_heilung_rekonstruiert_kein_unlesbares_artefakt(self):
        """FAIL-CLOSED: A1 bleibt Fund. Rekonstruktion wäre Erfindung."""
        kaputt = '{"a": 1,\n  "b": {\n'
        tmp = _baum({"data/x.json": kaputt})
        ziel = tmp / "data" / "x.json"
        geheilt, meldung = aw.heile_json_doppelt(ziel)
        self.assertFalse(geheilt)
        self.assertEqual(ziel.read_text(encoding="utf-8"), kaputt,
                         "die Wache darf ein kaputtes Artefakt nicht anfassen")
        self.assertTrue(meldung)

    def test_heile_bearbeitet_nur_a2(self):
        tmp = _baum({"data/kaputt.json": '{"a": 1,\n',
                     "data/doppelt.json": '{"k": 1, "k": 2}\n'})
        funde_vorher = aw.pruefe_alle(tmp)
        self.assertTrue([f for f in funde_vorher if f.klasse.startswith("A1")])
        protokoll = aw.heile(funde_vorher, tmp)
        self.assertTrue(protokoll)
        reste = aw.pruefe_alle(tmp)
        self.assertTrue([f for f in reste if f.klasse.startswith("A1")],
                        "A1 muss als Fund stehen bleiben")
        self.assertFalse([f for f in reste if f.klasse.startswith("A2")],
                         "A2 muss geheilt sein")


class CliTests(unittest.TestCase):
    """Der Vertrag am CLI: Exit-Codes, Maschinenformat, C15 (schreibfrei)."""

    def test_selftest_ist_gruen(self):
        proc = subprocess.run([sys.executable, str(SKRIPT), "--selftest"],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0,
                         f"Selbsttest rot:\n{proc.stdout}\n{proc.stderr}")

    def test_wirkungsprobe_ist_gruen(self):
        proc = subprocess.run(
            [sys.executable, str(SKRIPT), "--wirkungsprobe"],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0,
                         f"Wirkungsprobe rot:\n{proc.stdout}\n{proc.stderr}")

    def test_fund_bringt_exit_1_und_fund_im_json(self):
        tmp = _baum({"data/x.json": '{"a": 1, "a": 2}\n'})
        proc = subprocess.run(
            [sys.executable, str(SKRIPT), "--json", "--root", str(tmp)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1, proc.stdout)
        daten = json.loads(proc.stdout)
        self.assertEqual(daten["geprueft"], 1)
        self.assertEqual(len(daten["funde"]), 1)
        self.assertTrue(daten["funde"][0]["klasse"].startswith("A2"))
        self.assertTrue(daten["funde"][0]["heilbar"])

    def test_gruener_korpus_bringt_exit_0(self):
        tmp = _baum({"data/gut.json": '{"a": 1}\n'})
        proc = subprocess.run(
            [sys.executable, str(SKRIPT), "--root", str(tmp)],
            capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, proc.stdout)

    def test_pruefen_schreibt_nicht(self):
        """C15: Ein Prüf-Aufruf heilt nicht – auch nicht am echten Repo."""
        tmp = _baum({"data/x.json": '{"a": 1, "a": 2}\n'})
        ziel = tmp / "data" / "x.json"
        vorher = ziel.read_text(encoding="utf-8")
        subprocess.run([sys.executable, str(SKRIPT), "--root", str(tmp)],
                       capture_output=True, text=True)
        self.assertEqual(ziel.read_text(encoding="utf-8"), vorher)

    def test_markdown_bericht_traegt_alle_klassen(self):
        tmp = _baum({"data/x.json": '{"a": 1, "a": 2}\n'})
        proc = subprocess.run(
            [sys.executable, str(SKRIPT), "--md", "--root", str(tmp)],
            capture_output=True, text=True)
        self.assertIn("A2", proc.stdout)
        self.assertIn("data/x.json", proc.stdout)


class KettenTests(unittest.TestCase):
    """Verdrahtung: die Wache ist Pflicht, nicht Empfehlung (C33)."""

    def test_in_governance_guards_eingetragen(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import governance_contract as gc  # noqa: E402
        self.assertIn("artefakt_waechter.py", gc.GUARDS,
                      "ohne C6-Zwang zum Selbsttest verstummt die Wache")

    def test_unter_integritaetssiegel(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import integrity_guard as ig  # noqa: E402
        self.assertIn("scripts/artefakt_waechter.py", ig.FEST,
                      "eine Wache, die man still ändern kann, ist keine")

    def test_in_beiden_workflows_verdrahtet(self):
        for name in ("integrity-lock.yml", "content-reserve.yml"):
            text = (ROOT / ".github" / "workflows" / name).read_text(
                encoding="utf-8")
            self.assertIn("scripts/artefakt_waechter.py", text,
                          f"{name} ruft den Artefakt-Wächter nicht")

    def test_reserve_laeuft_nach_der_heilenden_stufe(self):
        text = (ROOT / ".github" / "workflows" / "content-reserve.yml"
                ).read_text(encoding="utf-8")
        self.assertLess(text.find("scripts/reserve_readiness.py"),
                        text.rindex("scripts/artefakt_waechter.py"),
                        "erst heilen (Stufe 3), dann urteilen (Wächter)")


class GateKlassenTests(unittest.TestCase):
    """#653: „nicht gemessen“ darf nicht als „zu wenig Vorrat“ aussehen."""

    def test_kaputtes_zertifikat_ist_klasse_artefakt(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import reserve_gate as rg  # noqa: E402
        tmp = Path(tempfile.mkdtemp(prefix="rg-test-"))
        zert = tmp / "reserve-readiness.json"
        zert.write_text('{"target": 6, "ready": 2, "candidates": [\n'
                        '  {"slug": "a", "ready": true},\n', encoding="utf-8")
        klasse, meldung = rg.zertifikat_lage(zert)
        self.assertEqual(klasse, rg.KLASSE_ARTEFAKT, meldung)
        self.assertIn("STRUKTURELL KAPUTT", meldung)
        # … und die Zählung bleibt trotzdem fail-closed:
        self.assertEqual(rg.evaluate(zert)[0], 0)

    def test_fehlendes_zertifikat_ist_klasse_artefakt(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import reserve_gate as rg  # noqa: E402
        klasse, meldung = rg.zertifikat_lage(
            Path(tempfile.mkdtemp(prefix="rg-test-")) / "nicht-da.json")
        self.assertEqual(klasse, rg.KLASSE_ARTEFAKT)
        self.assertIn("fehlt", meldung)

    def test_gueltiges_zertifikat_ist_klasse_ok(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import reserve_gate as rg  # noqa: E402
        tmp = Path(tempfile.mkdtemp(prefix="rg-test-"))
        zert = tmp / "reserve-readiness.json"
        zert.write_text(json.dumps(
            {"target": 6, "ready": 6,
             "candidates": [{"slug": f"k{i}", "ready": True} for i in range(6)]}),
            encoding="utf-8")
        self.assertEqual(rg.zertifikat_lage(zert)[0], rg.KLASSE_OK)

    def test_uebersprungene_kette_wird_gemeldet(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import os
        import reserve_gate as rg  # noqa: E402
        alt = os.environ.get("RESERVE_STUFE3_STATUS")
        try:
            os.environ["RESERVE_STUFE3_STATUS"] = "skipped"
            zeilen = rg.ketten_lage()
            self.assertTrue(any("Stufe 3" in z for z in zeilen), zeilen)
            self.assertTrue(any("nicht neu geschrieben" in z for z in zeilen))
        finally:
            if alt is None:
                os.environ.pop("RESERVE_STUFE3_STATUS", None)
            else:
                os.environ["RESERVE_STUFE3_STATUS"] = alt

    def test_wachen_klasse_ist_ein_eigener_befund(self):
        """Roter Wachen-Selbsttest ≠ übersprungene Kette (#653).

        Bei Klasse `wachen` ist die Messung AKTUELL – der Nachschub steht.
        Wer beides „Kette“ nennt, weist die Reparatur in die Reihenfolge
        statt in die Wache.
        """
        sys.path.insert(0, str(ROOT / "scripts"))
        import io
        import os
        import contextlib
        import reserve_gate as rg  # noqa: E402
        alt = os.environ.get("RESERVE_WACHEN_ROT")
        try:
            for wert, erwartet in (("1", True), ("true", True),
                                   ("0", False), ("", False)):
                os.environ["RESERVE_WACHEN_ROT"] = wert
                self.assertIs(rg.wachen_rot(), erwartet, wert)
            os.environ.pop("RESERVE_WACHEN_ROT", None)
            self.assertIs(rg.wachen_rot(), False)
            os.environ["RESERVE_WACHEN_ROT"] = "1"
            puffer = io.StringIO()
            with contextlib.redirect_stdout(puffer):
                rg.report(6, 6, [{"slug": f"k{i}", "ready": True}
                                 for i in range(6)],
                          klasse=rg.KLASSE_WACHEN, meldung="",
                          ketten=["WACHEN: Selbsttest rot"])
            text = puffer.getvalue()
            self.assertIn("AKTUELL gemessen", text)
            self.assertNotIn("nicht aus diesem Lauf", text,
                             "bei Klasse wachen ist die Messung nicht alt")
            self.assertNotIn("ENGPA", text)
        finally:
            if alt is None:
                os.environ.pop("RESERVE_WACHEN_ROT", None)
            else:
                os.environ["RESERVE_WACHEN_ROT"] = alt

    def test_keine_erfundene_engpass_diagnose_ohne_messung(self):
        """#653: Aus einer fehlgeschlagenen Messung darf keine Ursache werden.

        Sechs Nächte lang nannte der Bericht „PRODUKTION: 6 Kandidaten
        fehlen im Pool“ – bei vollem Vorrat. Die Zahl war eine Null aus
        einer kaputten Datei, die Ursachenliste eine Erfindung daraus.
        """
        sys.path.insert(0, str(ROOT / "scripts"))
        import io
        import contextlib
        import reserve_gate as rg  # noqa: E402
        puffer = io.StringIO()
        with contextlib.redirect_stdout(puffer):
            rg.report(0, 6, [], klasse=rg.KLASSE_ARTEFAKT,
                      meldung="Test: Zertifikat strukturell kaputt", ketten=[])
        text = puffer.getvalue()
        self.assertIn("RESERVE-MESSUNG FEHLGESCHLAGEN", text)
        self.assertNotIn("ENGPA", text, text)
        self.assertNotIn("URSACHEN DIESES ENGPASSES", text, text)

    def test_erfolgreiche_stufen_sind_still(self):
        sys.path.insert(0, str(ROOT / "scripts"))
        import os
        import reserve_gate as rg  # noqa: E402
        alt = {k: os.environ.get(k) for k in
               ("RESERVE_STUFE1_STATUS", "RESERVE_STUFE2_STATUS",
                "RESERVE_STUFE3_STATUS", "RESERVE_WACHEN_ROT")}
        try:
            for k in alt:
                os.environ.pop(k, None)
            os.environ["RESERVE_STUFE1_STATUS"] = "success"
            os.environ["RESERVE_STUFE2_STATUS"] = "success"
            os.environ["RESERVE_STUFE3_STATUS"] = "success"
            self.assertEqual(rg.ketten_lage(), [])
        finally:
            for k, v in alt.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


if __name__ == "__main__":
    unittest.main(verbosity=2)
