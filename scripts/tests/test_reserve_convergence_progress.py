"""#614: Teilfortschritt weiterführen, ohne Erfolg oder Zeitbudget zu erfinden."""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reserve_converge as rc
import reserve_readiness as rr
import satz_heiler as sh


def state(flesch=58.0, digest="alt", ready=2):
    return {"target": 6, "ready": ready, "pool_size": 12, "exists": True,
            "candidates": [{"slug": "kandidat", "ready": False,
                            "sha256": digest, "flesch": flesch}]}


class ProgressTests(unittest.TestCase):
    def test_flesch_zwischenstufe_erlaubt_zweite_runde_bis_zum_ziel(self):
        states = iter([state(), state(58.3, "neu"), state(58.3, "neu"),
                       state(60.1, "fertig", ready=6)])
        calls = []
        result = rc.converge(state_reader=lambda: next(states),
                             runner=lambda *a, **k: calls.append(a) or 0,
                             log=lambda *_: None)
        self.assertTrue(result["ok"])
        self.assertEqual(result["runden"], 2)
        self.assertEqual(len(calls), 6)
        self.assertEqual(result["verlauf"][0]["ready"], 2)
        self.assertEqual(result["verlauf"][0]["teilfortschritt"],
                         [{"slug": "kandidat", "vor": 58.0, "nach": 58.3}])

    def test_teilfortschritt_ist_kein_erfolg_und_rundendeckel_bleibt(self):
        states = iter([state(), state(59.0, "neu"), state(59.0, "neu")])
        result = rc.converge(state_reader=lambda: next(states), max_runden=1,
                             runner=lambda *a, **k: 0, log=lambda *_: None)
        self.assertFalse(result["ok"])
        self.assertEqual(result["abbruch"], "runden-erschöpft")

    def test_nur_hashwechsel_oder_schlechtere_werte_sind_keine_wirkung(self):
        for value in (58.0, 58.2, 57.0, None, "59", True, float("nan"), float("inf")):
            with self.subTest(value=value):
                self.assertEqual([], rc.partial_progress(state(), state(value, "neu")))
        self.assertEqual([], rc.partial_progress(state(), state(59, "alt")))
        self.assertEqual([], rc.partial_progress(state(), state(59, "")))
        self.assertEqual([], rc.partial_progress(state(61), state(62, "neu")))
        other = state(59, "neu")
        other["candidates"][0]["slug"] = "anderes-thema"
        self.assertEqual([], rc.partial_progress(state(), other))

    def test_alte_zertifikate_bleiben_lesbar_ohne_erfundene_messung(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cert.json"
            path.write_text(json.dumps({"candidates": [{"ready": True}]}))
            result = rc.cert_state(path)
            self.assertEqual(result["ready"], 1)
            self.assertEqual([], rc.partial_progress(result, state(59, "neu")))
            for candidates in ("defekt", [None, "defekt"]):
                path.write_text(json.dumps({"candidates": candidates}))
                self.assertEqual(rc.cert_state(path)["ready"], 0)

    def test_zertifikat_misst_original_bytes_und_stellt_entwurf_wieder_her(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "index.md"
            raw = sh._fixture()
            path.write_text(raw)
            with patch.object(rr, "score_diagnosis", return_value=None), \
                    patch.object(rr, "capture_gate", return_value=(False, "")):
                row = rr.certify_one(path)
            self.assertFalse(row["ready"])
            self.assertEqual(row["flesch"], sh.lh.flesch(raw, path.parent.name))
            self.assertIsInstance(row["flesch"], float)
            self.assertEqual(row["sha256"], hashlib.sha256(raw.encode()).hexdigest())
            self.assertEqual(path.read_text(), raw)

    def test_summary_unterscheidet_teilfortschritt_und_ready(self):
        states = iter([state(), state(59, "neu"), state(59, "neu")])
        result = rc.converge(state_reader=lambda: next(states), max_runden=1,
                             runner=lambda *a, **k: 0, log=lambda *_: None)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "summary.md"
            rc.write_summary(result, str(path))
            self.assertIn("kein READY", path.read_text())
            self.assertIn("Engpass", path.read_text())


class DeadlineTests(unittest.TestCase):
    def run_budget(self, durations, budget=900, codes=None):
        clock, calls = [0], []
        durations = iter(durations)
        codes = iter(codes or [0, 0, 1])

        def run(cmd, env=None, timeout=0):
            calls.append((Path(cmd[1]).name, timeout))
            clock[0] += next(durations)
            return next(codes)

        result = rc.converge(runner=run, state_reader=state,
                             max_sekunden=budget, now=lambda: clock[0],
                             log=lambda *_: None)
        return result, calls

    def test_restbudget_wird_vor_jedem_schritt_neu_berechnet(self):
        result, calls = self.run_budget([400, 400, 50])
        self.assertEqual([t for _, t in calls], [900, 500, 100])
        self.assertFalse(result["ok"])

    def test_keine_kuenstlichen_300_sekunden_nach_fast_verbrauchtem_budget(self):
        result, calls = self.run_budget([895, 5])
        self.assertEqual([t for _, t in calls], [900, 5])
        self.assertEqual(result["abbruch"], "zeit-budget")
        self.assertFalse(result["ok"])

    def test_nullbudget_startet_keine_kinder(self):
        result, calls = self.run_budget([], budget=0)
        self.assertEqual(calls, [])
        self.assertEqual(result["abbruch"], "zeit-budget")

    def test_timeout_beendet_runde_statt_danach_zu_zertifizieren(self):
        result, calls = self.run_budget([10], codes=[124])
        self.assertEqual(len(calls), 1)
        self.assertEqual(result["abbruch"], "schritt-timeout")
        self.assertFalse(result["ok"])

    def test_zertifizierungsabsturz_ist_kein_erfolg_mit_altem_zertifikat(self):
        states = iter([state(), state(60, "alt", ready=6)])
        codes = iter([0, 0, 2])
        result = rc.converge(state_reader=lambda: next(states),
                             runner=lambda *a, **k: next(codes), log=lambda *_: None)
        self.assertFalse(result["ok"])
        self.assertEqual(result["abbruch"], "zertifizierung-fehlgeschlagen")

    @unittest.skipUnless(sys.platform == "linux", "Prozessgruppen auf CI-Linux")
    def test_echter_timeout_stoppt_auch_schreibendes_enkelkind(self):
        with tempfile.TemporaryDirectory() as tmp:
            # Das Kind schreibt seine PID als Startnachweis, schläft dann und
            # würde nach dem Eltern-Timeout eine Datei schreiben. Es ignoriert
            # SIGTERM absichtlich; die abschließende Gruppen-KILL muss greifen.
            marker = Path(tmp) / "unerlaubter-schreibzugriff"
            pidfile = Path(tmp) / "pid"
            child = ("import os,signal,time,pathlib; "
                     "signal.signal(signal.SIGTERM, signal.SIG_IGN); "
                     f"pathlib.Path({str(pidfile)!r}).write_text(str(os.getpid())); "
                     "time.sleep(1); "
                     f"pathlib.Path({str(marker)!r}).write_text('verwaist')")
            parent = ("import subprocess,sys,time; "
                      f"subprocess.Popen([sys.executable,'-c',{child!r}]); "
                      "time.sleep(30)")
            try:
                code = rc._run([sys.executable, "-c", parent], timeout=0.5)
                self.assertEqual(code, 124)
                self.assertTrue(pidfile.exists(), "Kind muss wirklich gestartet sein")
                pid = int(pidfile.read_text())
                # Warten durch einen unabhängigen, begrenzten Prozess.
                subprocess.run([sys.executable, "-c", "import time; time.sleep(1)"],
                               check=True, timeout=5)
                stat = Path(f"/proc/{pid}/stat")
                if stat.exists():
                    self.assertEqual(stat.read_text().split()[2], "Z")
                self.assertFalse(marker.exists())
            finally:
                if pidfile.exists():
                    try:
                        os.kill(int(pidfile.read_text()), signal.SIGKILL)
                    except ProcessLookupError:
                        pass


class SentenceWhitespaceTests(unittest.TestCase):
    def test_eingerueckte_saetze_haben_exakte_dateikoordinaten(self):
        sentence = next(iter(sh.LEICHT))
        for indent in (" ", "  ", "\t"):
            with self.subTest(indent=repr(indent)):
                raw = "---\ntitle: Probe\ndraft: true\n---\n" + indent + sentence
                rows = sh.saetze_finden(sh._teile(raw)[2], base_offset=sh._body_offset(raw))
                self.assertEqual(len(rows), 1)
                start = rows[0]["start"]
                self.assertEqual(raw[start:start + len(sentence)], sentence)
                self.assertEqual(sh._finde_satz(raw, sentence), start)
                replacement = sh.LEICHT[sentence]
                changed = raw[:start] + replacement + raw[start + len(sentence):]
                self.assertEqual([], sh.unversehrte_saetze(raw, changed, [(sentence, replacement)]))


if __name__ == "__main__":
    unittest.main()
