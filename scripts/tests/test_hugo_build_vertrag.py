"""Vertragstests für die gemeinsame Hugo-Build-Action (H1–H8).

Diese Tests prüfen zwei Dinge getrennt voneinander:

1. Die REGELN (H1–H8) erkennen Defekte und melden saubere Zustände nicht.
2. Die ACTION verhält sich, wie die Regeln behaupten – geprüft am echten
   Shell-Rumpf gegen ein Hugo-Attrappen-Programm.

Der zweite Punkt ist der wichtigere. Eine Wache, die nur nach dem Wort
``pipefail`` im YAML sucht, lässt sich mit einem Kommentar betrügen.
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import hugo_build_vertrag as hbv  # noqa: E402


class VertragIstGruen(unittest.TestCase):
    """Der echte Zustand des Repos erfüllt den Vertrag."""

    def test_alle_regeln_gruen(self):
        erg = hbv.pruefen()
        offen = {k: v["befunde"] for k, v in erg.items() if v["befunde"]}
        self.assertEqual(offen, {}, f"Befunde: {offen}")

    def test_selbsttest_gruen(self):
        self.assertEqual(hbv.main(["--selftest"]), 0)

    def test_bericht_nennt_jede_regel(self):
        text = hbv.bericht(hbv.pruefen())
        for kennung in hbv.REGELN:
            self.assertIn(kennung, text)


class RegelnErkennenDefekte(unittest.TestCase):
    """Jede Regel muss rot werden können – sonst ist sie Dekoration."""

    def _wf(self, inhalt: str, tmp: str) -> Path:
        wf = Path(tmp)
        for name in hbv.AUSNAHMEN:
            (wf / name).write_text(
                "jobs:\n  x:\n    steps:\n      - run: hugo --minify\n",
                encoding="utf-8")
        (wf / "probe.yml").write_text(inhalt, encoding="utf-8")
        return wf

    def test_h6_sieht_direkten_aufruf(self):
        with tempfile.TemporaryDirectory() as tmp:
            wf = self._wf("jobs:\n  x:\n    steps:\n      - run: hugo --minify\n", tmp)
            befunde = hbv.h6_alle_bauten_nutzen_die_action(wf)
        self.assertTrue(any("probe.yml" in b for b in befunde))

    def test_h6_akzeptiert_die_action(self):
        with tempfile.TemporaryDirectory() as tmp:
            wf = self._wf(
                "jobs:\n  x:\n    steps:\n      - uses: ./.github/actions/hugo-build\n",
                tmp)
            self.assertEqual(hbv.h6_alle_bauten_nutzen_die_action(wf), [])

    def test_h6_wertet_schrittnamen_nicht_als_bau(self):
        """`- name: "… hugo --minify …"` ist ein Name, kein Aufruf."""
        with tempfile.TemporaryDirectory() as tmp:
            wf = self._wf(
                'jobs:\n  x:\n    steps:\n'
                '      - name: "Website bauen (identisch zur Produktion: hugo --minify)"\n'
                "        uses: ./.github/actions/hugo-build\n", tmp)
            self.assertEqual(hbv.h6_alle_bauten_nutzen_die_action(wf), [])

    def test_h6_meldet_tote_ausnahme(self):
        with tempfile.TemporaryDirectory() as tmp:
            wf = Path(tmp)
            namen = list(hbv.AUSNAHMEN)
            (wf / namen[0]).write_text(
                "jobs:\n  x:\n    steps:\n      - run: echo nix\n", encoding="utf-8")
            for weitere in namen[1:]:
                (wf / weitere).write_text(
                    "jobs:\n  x:\n    steps:\n      - run: hugo --minify\n",
                    encoding="utf-8")
            befunde = hbv.h6_alle_bauten_nutzen_die_action(wf)
        self.assertTrue(any("toter Eintrag" in b for b in befunde))

    def test_jede_ausnahme_hat_eine_begruendung(self):
        for datei, grund in hbv.AUSNAHMEN.items():
            self.assertTrue(grund.strip(), f"{datei} ohne Begründung")
            self.assertGreater(len(grund), 60,
                               f"{datei}: Begründung ist zu dünn, um eine zu sein")

    def test_h7_sieht_jeden_beweisvernichter(self):
        for zeile in ("hugo --minify > /dev/null 2>&1",
                      "hugo --minify || true",
                      "hugo --minify --quiet"):
            with self.subTest(zeile=zeile), tempfile.TemporaryDirectory() as tmp:
                wf = self._wf(
                    f"jobs:\n  x:\n    steps:\n      - run: {zeile}\n", tmp)
                self.assertTrue(hbv.h7_keine_beweisvernichtung(wf),
                                f"H7 übersieht: {zeile}")

    def test_h7_meldet_sauberen_aufruf_nicht(self):
        with tempfile.TemporaryDirectory() as tmp:
            wf = self._wf("jobs:\n  x:\n    steps:\n      - run: hugo --minify\n", tmp)
            self.assertEqual(hbv.h7_keine_beweisvernichtung(wf), [])


class ActionVerhaeltSichWirklichSo(unittest.TestCase):
    """Der echte Shell-Rumpf gegen eine Hugo-Attrappe."""

    @classmethod
    def setUpClass(cls):
        cls.rumpf = hbv._bau_rumpf()
        if not cls.rumpf:
            raise unittest.SkipTest("Bau-Rumpf nicht lesbar (PyYAML fehlt?)")

    def test_gruener_bau_meldet_null_und_seitenzahl(self):
        v = hbv._rumpf_ausfuehren(self.rumpf, 0, " Pages            \u2502   42 ")
        self.assertEqual(v["rc"], 0)
        self.assertIn("rc=0", v["outputs"])
        self.assertIn("seiten=42", v["outputs"])

    def test_roter_bau_meldet_rot(self):
        """Das Kernversprechen: der Exit-Code überlebt die Pipe."""
        v = hbv._rumpf_ausfuehren(self.rumpf, 1, "ERROR template kaputt")
        self.assertNotEqual(v["rc"], 0)
        self.assertIn("::error title=Hugo-Build:", v["stdout"])
        self.assertIn("template kaputt", v["stdout"])
        self.assertIn("❌", v["summary"])

    def test_pipefail_und_pipestatus_tragen_je_allein(self):
        """Zwei Netze, jedes einzeln belastet.

        Wer beide zusammen prüft, merkt nicht, wenn eins reißt.
        """
        ohne_pipefail = self.rumpf.replace("set -uo pipefail", "set -u")
        self.assertNotEqual(ohne_pipefail, self.rumpf)
        # PIPESTATUS allein, ganz ohne pipefail:
        v = hbv._rumpf_ausfuehren(ohne_pipefail, 1, "ERROR x", flaggen=("-e",))
        self.assertNotEqual(v["rc"], 0, "PIPESTATUS trägt nicht allein")
        # pipefail allein, ohne PIPESTATUS:
        v = hbv._rumpf_ausfuehren(
            self.rumpf.replace("${PIPESTATUS[0]}", "$?"), 1, "ERROR x")
        self.assertNotEqual(v["rc"], 0, "pipefail trägt nicht allein")
        # Gegenprobe: ohne beides MUSS es grün werden – sonst messen die
        # beiden Proben oben nichts.
        v = hbv._rumpf_ausfuehren(
            ohne_pipefail.replace("${PIPESTATUS[0]}", "$?"), 1, "ERROR x",
            flaggen=("-e",))
        self.assertEqual(v["rc"], 0, "Die Proben oben sind blind")

    def test_leeres_verzeichnis_wird_benannt(self):
        v = hbv._rumpf_ausfuehren(self.rumpf, 1, "ERROR x",
                                  leeres_verzeichnis=True)
        self.assertIn("content/drafts", v["summary"])

    def test_kein_fehlalarm_ohne_leeres_verzeichnis(self):
        v = hbv._rumpf_ausfuehren(self.rumpf, 1, "ERROR x",
                                  leeres_verzeichnis=False)
        self.assertNotIn("Leere Verzeichnisse gefunden", v["summary"])

    def test_toleriert_heisst_sichtbar_nicht_unbemerkt(self):
        v = hbv._rumpf_ausfuehren(self.rumpf, 1, "ERROR x", weiter="true")
        self.assertEqual(v["rc"], 0, "Job wurde trotz Toleranz gestoppt")
        self.assertIn("::error title=", v["stdout"], "toleriert = unsichtbar")
        self.assertIn("rc=1", v["outputs"])

    def test_quiet_wird_abgelehnt(self):
        vor = hbv._vorpruef_rumpf()
        self.assertTrue(vor, "Vorprüf-Schritt nicht lesbar")
        v = hbv._rumpf_ausfuehren(vor, 0, "", args="--minify --quiet")
        self.assertNotEqual(v["rc"], 0)
        self.assertIn("--quiet", v["stdout"])
        v = hbv._rumpf_ausfuehren(vor, 0, "", args="--minify")
        self.assertEqual(v["rc"], 0, "Fehlalarm bei sauberen Argumenten")


class WorkflowsSindUmgestellt(unittest.TestCase):
    """Die Action darf kein Regalstück sein – sie muss benutzt werden."""

    def test_die_frueher_blinden_stellen_nutzen_die_action(self):
        # Genau die fünf Dateien, die am 02.10.2026 die Fehlermeldung
        # vernichtet haben.
        for datei in ("seo-weekly.yml", "bot-watchdog.yml", "e2e.yml",
                      "layout-ai.yml", "visual-data-gate.yml"):
            with self.subTest(datei=datei):
                text = (ROOT / ".github" / "workflows" / datei).read_text(
                    encoding="utf-8")
                self.assertIn(hbv.ACTION_REF, text)

    def test_gate_und_produktion_nutzen_die_action(self):
        for datei in ("link-check.yml", "deploy.yml"):
            with self.subTest(datei=datei):
                text = (ROOT / ".github" / "workflows" / datei).read_text(
                    encoding="utf-8")
                self.assertIn(hbv.ACTION_REF, text)

    def test_vertrag_laeuft_im_qualitaetsgate(self):
        text = (ROOT / ".github" / "workflows" / "link-check.yml").read_text(
            encoding="utf-8")
        self.assertIn("hugo_build_vertrag.py", text)


if __name__ == "__main__":
    unittest.main()
