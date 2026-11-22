#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Regressionstests der Titel-Klinke (scripts/titel_klinke.py).

Anlass (#1304, 22.11.2026): Ein Titel mit 64 Zeichen stand seit dem
20.11.2026 im Bestand. Zwei Wachen sahen ihn (`metadaten_wache.py` M1,
`check_titles.py` R1) – keine konnte ihn schließen, weil beide nur melden
(C34: ein Befund stoppt die Auslieferung nicht) und der Befund damit jeden
Tag erneut erschien. Eine Meldung, die nie zur Entscheidung zwingt, ist
Rauschen.

Diese Tests halten die Klinke fest: Bekanntes bleibt still, Neues wird
rot, Geheiltes rastet ein, und eine Änderung ohne Wirkung ist ein Fund
(genau der Fall vom 21.11.2026: Titel umformuliert, weiter 64 Zeichen).
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

import titel_klinke as k  # noqa: E402

GRUEN = "Frischer Titel mit Doppelpunkt: kurz genug"          # 42 Zeichen
ROT_T1 = ("Kfz-Versicherung vergleichen: Was ändert sich außer "
          "dem Beitrag?")                                      # 64 Zeichen
ROT_T3 = "Wie viel Bandbreite brauchst du fürs Streaming?"     # 47, kein :


def datei(titelzeile: str, draft: bool = False) -> str:
    return (f"---\ntitle: {titelzeile}\ndate: 2026-01-01\n"
            f"draft: {'true' if draft else 'false'}\n---\n\nText.\n")


def aus_text(text: str) -> list[dict]:
    titel, hat_fm = k.frontmatter_und_titel(text)
    return k.bewerte(titel, hat_frontmatter=hat_fm)


class RegelTest(unittest.TestCase):
    """T1–T3: nur messbare Schwellen, dieselben Zahlen wie die Wachen."""

    def test_der_vorfall_64_zeichen_ist_ein_befund(self) -> None:
        befunde = k.bewerte(ROT_T1)
        self.assertEqual(["T1"], [b["regel"] for b in befunde])
        # Die Zahl in der Meldung ist die gemessene, nicht die geschätzte.
        self.assertIn("64 Zeichen", befunde[0]["text"])

    def test_grenzen_stimmen_mit_den_wachen_ueberein(self) -> None:
        """Keine dritte Wahrheit: 60 und 45 sind die Zahlen der Wachen."""
        self.assertEqual(60, k.TITLE_MAX)
        self.assertEqual(45, k.TITLE_NO_COLON_MAX)

    def test_grenze_60_ist_gruen_61_ist_rot(self) -> None:
        self.assertEqual([], k.bewerte("A" * 56 + ": bb"))      # 60
        self.assertEqual(["T1"], [b["regel"] for b in
                                  k.bewerte("A" * 57 + ": bb")])  # 61

    def test_lang_ohne_doppelpunkt_ist_t3_nicht_t1(self) -> None:
        befunde = k.bewerte(ROT_T3)
        self.assertEqual(["T3"], [b["regel"] for b in befunde])

    def test_kurzer_titel_ohne_doppelpunkt_ist_in_ordnung(self) -> None:
        self.assertEqual([], k.bewerte("Strom sparen im Alltag"))

    def test_fehlender_titel_ist_t2_und_nur_t2(self) -> None:
        self.assertEqual(["T2"], [b["regel"] for b in k.bewerte("")])
        self.assertEqual(["T2"], [b["regel"] for b in
                                  k.bewerte("", hat_frontmatter=False)])

    def test_leser_entquotet_und_ignoriert_kommentar(self) -> None:
        self.assertEqual(["T1"], [b["regel"] for b in
                                  aus_text(datei(f"'{ROT_T1}'"))])
        self.assertEqual([], aus_text(datei(f'"{GRUEN}"  # ' + "x" * 40)))
        self.assertEqual([], aus_text(datei(GRUEN + "  # " + "x" * 40)))

    def test_datei_ohne_frontmatter(self) -> None:
        self.assertEqual(["T2"], [b["regel"] for b in aus_text("# nur Text\n")])


class KlinkeTest(unittest.TestCase):
    """Die Sperrklinke: nur abwärts, und kein Wegwischer."""

    def _stand(self, titel: str, draft: bool = False) -> dict:
        return {"a": {"titel": titel, "draft": draft,
                      "schwere": k._schwere(k.bewerte(titel)),
                      "befunde": k.bewerte(titel)}}

    def test_bekannter_befund_ist_kein_neuer_fund(self) -> None:
        basis = {"a": {"titel": ROT_T1, "schwere": 2}}
        e = k.vergleiche(self._stand(ROT_T1), basis)
        self.assertEqual([], e["neu"])
        self.assertEqual(["a"], e["bekannt"])

    def test_war_gruen_ist_rot_wird_neu_gemeldet(self) -> None:
        basis = {"a": {"titel": GRUEN, "schwere": 0}}
        e = k.vergleiche(self._stand(ROT_T1), basis)
        self.assertEqual(["a"], e["neu"])

    def test_heilung_rastet_ein(self) -> None:
        basis = {"a": {"titel": ROT_T1, "schwere": 2}}
        jetzt = self._stand(GRUEN)
        e = k.vergleiche(jetzt, basis)
        self.assertEqual(["a"], e["geheilt"])
        neu = k.klinke_einrasten(jetzt, basis)
        self.assertEqual(0, neu["a"]["schwere"])
        # … und ein Rückfall ist danach NEU, kein Altbestand.
        self.assertEqual(["a"], k.vergleiche(self._stand(ROT_T1), neu)["neu"])

    def test_verschlechterung_wird_nicht_eingefroren(self) -> None:
        """Sonst wäre die Klinke ein Wegwischer: Fund → „bekannt“ → nie weg."""
        basis = {"a": {"titel": GRUEN, "schwere": 0}}
        neu = k.klinke_einrasten(self._stand(ROT_T1), basis)
        self.assertEqual(0, neu["a"]["schwere"],
                         "ein offener Fund darf nicht in die Baseline")

    def test_aenderung_ohne_wirkung_ist_ein_fund(self) -> None:
        """Der Vorfall vom 21.11.2026: neu formuliert, weiter 64 Zeichen."""
        basis = {"a": {"titel": ROT_T1[:-1], "schwere": 2}}
        umformuliert = ROT_T1 + "!"
        e = k.vergleiche(self._stand(umformuliert), basis)
        self.assertEqual(["a"], e["verschlechtert"])

    def test_entwurf_ist_kein_neuer_fund(self) -> None:
        e = k.vergleiche(self._stand(ROT_T1, draft=True), {})
        self.assertEqual([], e["neu"])
        self.assertEqual(["a"], e["bekannt"])

    def test_neuer_veroeffentlichter_artikel_ist_neu(self) -> None:
        e = k.vergleiche(self._stand(ROT_T1), {})
        self.assertEqual(["a"], e["neu"])


class EchtdatenTest(unittest.TestCase):
    """Gegenprobe am echten Bestand – die Wache muss die zwei Fälle sehen."""

    def test_bestand_hat_keine_unbekannten_befunde(self) -> None:
        stand, dateien = k.erhebe()
        self.assertGreater(dateien, 100, "zu wenige Inhaltsdateien")
        ergebnis = k.vergleiche(stand, k.lade_baseline())
        self.assertEqual([], ergebnis["neu"],
                         f"neue Titel-Befunde ohne Baseline-Eintrag: "
                         f"{ergebnis['neu']}")
        self.assertEqual([], ergebnis["verschlechtert"])

    def test_der_vorfall_ist_geheilt_und_bleibt_geheilt(self) -> None:
        """#1304 ist am 22.11.2026 an der QUELLE geheilt worden.

        Frank hat den Kfz-Titel von 64 auf 59 Zeichen gekürzt („Was ändert
        sich beim Beitrag?“ – derselbe Sinn, kein neuer Versprechens-Ton),
        der Streaming-Titel bekam seinen Doppelpunkt. Die Klinke kann das
        nur bestätigen, wenn die Baseline den Zustand NACH der Heilung
        kennt. Sie friert deshalb `schwere: 0` ein – und die Sperre ist,
        dass eine Rückkehr des Befunds als NEU gemeldet wird.

        Ein Test, der hier noch einen roten Befund erwartet, würde die
        Heilung als Regression brandmarken. Genau das war der Anlass für
        diesen Test: Er prüft den Ist-Zustand, nicht die Erinnerung.
        """
        baseline = k.lade_baseline()
        for teil, grenze in (("2026-08-26-kfz-versicherung", 60),
                             ("2026-11-12-wie-viel-streaming-bandbreite", 60)):
            treffer = [x for x in baseline if teil in x]
            self.assertTrue(treffer, f"{teil} fehlt in der Baseline")
            eintrag = baseline[treffer[0]]
            self.assertEqual(0, eintrag["schwere"],
                             f"{teil} ist in der Baseline noch rot – die "
                             f"Heilung wurde nicht eingefroren")
            self.assertLessEqual(len(eintrag["titel"]), grenze,
                                 f"{teil}: Titel ist wieder über {grenze} Zeichen")

    def test_rueckkehr_des_befunds_wird_als_neu_gemeldet(self) -> None:
        """Die Sperre: Was geheilt ist, darf nicht still zurückkommen.

        Der Befund wird über `bewerte` erzeugt, nicht von Hand gesetzt –
        sonst prüft der Test eine Zustandsform, die `erhebe` nie liefert
        (genau daran ist die erste Fassung dieses Tests gescheitert).
        """
        baseline = k.lade_baseline()
        schluessel = next(x for x in baseline if "2026-08-26-kfz" in x)
        titel = "Kfz-Versicherung vergleichen: " + "x" * 40
        befunde = k.bewerte(titel, hat_frontmatter=True)
        self.assertTrue(befunde, "Testaufbau: der lange Titel muss anschlagen")
        stand = {schluessel: {
            "titel": k._norm_titel(titel), "draft": False,
            "schwere": k._schwere(befunde),
            "befunde": [{"regel": b["regel"], "text": b["text"]} for b in befunde]}}
        ergebnis = k.vergleiche(stand, baseline)
        self.assertEqual([schluessel], ergebnis["neu"],
                         "ein zurückgekehrter Titelbefund bliebe still")



class CliTest(unittest.TestCase):
    """Exit-Codes sind der Vertrag mit der CI."""

    def _lauf(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "titel_klinke.py"), *args],
            capture_output=True, text=True, cwd=ROOT)

    def test_selftest_gruen(self) -> None:
        lauf = self._lauf("--selftest")
        self.assertEqual(0, lauf.returncode, lauf.stdout + lauf.stderr)

    def test_selbsttest_fehler_bricht_ab_bevor_geschrieben_wird(self) -> None:
        """Hausregel: erst der Detektor, dann der Prüfling (fail-closed)."""
        quelle = (ROOT / "scripts" / "titel_klinke.py").read_text(encoding="utf-8")
        # Der Aufruf steht VOR jedem Schreibzugriff in main().
        main_rumpf = quelle.split("def main(argv")[1]
        self.assertLess(main_rumpf.index("run_selftest("),
                        main_rumpf.index("_schreibe_baseline("),
                        "der Selbsttest läuft nicht vor dem Schreiben")
        self.assertLess(main_rumpf.index("run_selftest("),
                        main_rumpf.index("_schreibe_history("),
                        "die History wird vor dem Selbsttest geschrieben")

    def test_dry_run_schreibt_nichts(self) -> None:
        before = (ROOT / "data" / "titel_history.jsonl").read_text(
            encoding="utf-8") if (ROOT / "data" / "titel_history.jsonl").exists() else ""
        lauf = self._lauf("--dry-run")
        after = (ROOT / "data" / "titel_history.jsonl").read_text(
            encoding="utf-8") if (ROOT / "data" / "titel_history.jsonl").exists() else ""
        self.assertEqual(before, after, "--dry-run hat die History verändert")
        self.assertEqual(0, lauf.returncode, lauf.stdout + lauf.stderr)

    def test_json_ist_maschinenlesbar(self) -> None:
        lauf = self._lauf("--json")
        self.assertEqual(0, lauf.returncode, lauf.stderr)
        daten = json.loads(lauf.stdout)
        for feld in ("dateien", "offene_befunde", "neu", "bekannt",
                     "verschlechtert", "geheilt"):
            self.assertIn(feld, daten)

    def test_isolierter_lauf_in_tmp(self) -> None:
        """Ein kaputter Titel in einem tmp-Baum wird als NEU gemeldet."""
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            (wurzel / "content/posts/x").mkdir(parents=True)
            (wurzel / "content/posts/x/index.md").write_text(
                datei(ROT_T1), encoding="utf-8")
            stand, dateien = k.erhebe(wurzel)
            self.assertEqual(1, dateien)
            ergebnis = k.vergleiche(stand, {})
            self.assertEqual(["content/posts/x/index.md"], ergebnis["neu"])


if __name__ == "__main__":
    unittest.main()
