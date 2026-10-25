#!/usr/bin/env python3
"""Tests der Sicherheits-Header-Wache (scripts/blog_header_gate.py).

Hintergrund: Vorgang WF-E813, 15.10.2026. Der erste planmäßige Live-Lauf der
Sicherheits-Wache wurde rot. Zwei Fehler steckten in derselben Zeile:

  1. **Die Wache log.** Jede Netzstörung landete in der Liste der fehlenden
     Pflicht-Header. Ein TLS-Abbruch wurde zu „❌ Pflicht-Header fehlen oder
     sind falsch" umgedeutet – obwohl im Satz daneben stand, dass ohne
     Messung der Stand *ungeprüft* gilt. Ungeprüft ist nicht fehlend.
  2. **Der Melder riet.** Die automatische Meldung bot als „häufigste
     Ursachen" einen abgelaufenen API-Schlüssel an. Diese Wache misst
     Kopfzeilen und kennt keinen Schlüssel.

Diese Datei ist die Wache, dass weder das eine noch das andere zurückkommt:
Die vier Klassen (OK · TEILWEISE · BEFUND · STOERUNG) sind festgenagelt, die
Selbstheilung gegen transiente Netzfehler ist belegt, und die Verdrahtung im
Workflow (Auswertung statt Durchreichen, Vertrag C34) wird mitgeprüft – ein
Mess-Schritt, der seinen Exit-Code wieder durchreicht, macht jede
Klassifikation wertlos.

Läuft deterministisch ohne Netz
(`python3 -m unittest scripts.tests.test_blog_header_gate`).
"""
from __future__ import annotations

import os
import json
import subprocess
import tempfile
import textwrap
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import blog_header_gate as gate  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
WORKFLOW = REPO / ".github" / "workflows" / "sicherheits-wache.yml"

GUT = dict(gate.GUTE_KOPFZEILEN)
PROXY = dict(gate.PROXY_KENNUNG)
ABBRUCH = OSError("TLS/SSL connection has been closed (EOF)")


def _attrappe(ablauf):
    """Baut eine `holen`-Funktion, die die Ablaufliste abspielt und mitzählt."""
    probe = gate._Probe(ablauf)
    return probe.holen, probe


def _messen(ablauf, *, pausen=(), ziele=None):
    holen, probe = _attrappe(ablauf)
    return gate.netz_pruefen(holen=holen, pausen=pausen, schlaf=lambda _: None,
                             ziele=ziele), probe


class StoerungIstKeinBefund(unittest.TestCase):
    """Kernregression WF-E813: Eine Nicht-Messung ist kein Sicherheitsbefund."""

    def test_unerreichbare_seite_wird_als_stoerung_klassifiziert(self):
        (code, bericht, daten), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_STOERUNG)
        self.assertEqual(daten["klasse"], gate.KLASSE_STOERUNG)
        self.assertEqual(daten["gemessen"], 0)
        self.assertEqual(daten["nicht_gemessen"], [gate.ZIELE[0]])

    def test_netzstoerung_wandert_nie_in_die_liste_fehlender_header(self):
        """Genau das war der Fehler: `fehlend_gesamt.append(... nicht erreichbar ...)`."""
        (_, _, daten), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
        self.assertEqual(daten["fehlend"], [],
                         "Eine Netzstörung darf nie als fehlender Header erscheinen")
        self.assertTrue(daten["stoerung"], "Die Störung muss eigenständig benannt werden")

    def test_der_bericht_behauptet_keine_fehlenden_header(self):
        (_, bericht, _), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
        self.assertNotIn("fehlen oder sind falsch", bericht)
        self.assertIn("kein Header-Befund", bericht)
        self.assertIn("ungeprüft", bericht)

    def test_stoerung_und_befund_haben_unterschiedliche_exit_codes(self):
        # Der Auswerte-Schritt im Workflow trennt anhand dieser Codes. Wären
        # sie gleich, wäre die ganze Klassifikation wirkungslos.
        self.assertNotEqual(gate.EXIT_BEFUND, gate.EXIT_STOERUNG)
        self.assertNotEqual(gate.EXIT_OK, gate.EXIT_STOERUNG)
        self.assertEqual(gate.EXIT_BEFUND, 1)   # Bestandsvertrag: rot bleibt 1
        self.assertEqual(gate.EXIT_STOERUNG, 2)

    def test_stoerung_nennt_einen_naechsten_schritt_ohne_cloudflare_eingriff(self):
        (_, _, daten), _ = _messen([ABBRUCH], ziele=[gate.ZIELE[0]])
        schritt = daten["naechster_schritt"]
        self.assertTrue(schritt, "Eine Störung ohne nächsten Schritt ist Ratlosigkeit")
        self.assertIn("curl -sI", schritt)
        self.assertNotIn("Proxied", schritt)

    def test_versuche_werden_protokolliert(self):
        (_, bericht, daten), _ = _messen([ABBRUCH], pausen=(0.0, 0.0),
                                         ziele=[gate.ZIELE[0]])
        self.assertEqual(daten["ziele"][0]["versuche"], 3)
        self.assertIn("Versuch 3", bericht)


class Selbstheilung(unittest.TestCase):
    """Transiente Netzfehler heilt die Wache selbst, statt zu alarmieren."""

    def test_ein_abgebrochener_versuch_wird_wiederholt(self):
        (code, _, daten), probe = _messen(
            [ABBRUCH, ABBRUCH, (200, {**PROXY, **GUT})],
            pausen=(0.0,), ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK)
        self.assertEqual(daten["klasse"], gate.KLASSE_OK)
        self.assertEqual(probe.wege, ["HEAD", "GET", "HEAD"])

    def test_head_mit_fehlerstatus_löst_get_nachfrage_aus(self):
        def holen(url, weg):
            if weg == "HEAD":
                return (405, {"server": "cloudflare"})
            return (200, {**PROXY, **GUT})
        code, _, daten = gate.netz_pruefen(holen=holen, pausen=(),
                                           schlaf=lambda _: None, ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK, "Ein HEAD-Verbot darf kein Befund sein")
        self.assertEqual(daten["ziele"][0]["weg"], "GET")

    def test_pausen_sind_aufsteigend_und_endlich(self):
        # Sonst wäre „Wiederholung" entweder wirkungslos (0 s) oder eine
        # Endlosschleife im täglichen Lauf.
        self.assertTrue(gate.PAUSEN)
        self.assertEqual(list(gate.PAUSEN), sorted(gate.PAUSEN))
        self.assertLess(sum(gate.PAUSEN), 120.0,
                        "Die Selbstheilung muss in den 15-Minuten-Job passen")


class HTTPFehlerSindKeineSeitenmessung(unittest.TestCase):
    def test_fehler_und_challenge_seiten_bleiben_stoerung(self):
        for status in (301, 403, 404, 408, 429, 500, 502, 503, 504):
            with self.subTest(status=status):
                (code, _, daten), probe = _messen(
                    [(status, {**PROXY, **GUT})], pausen=(0,), ziele=[gate.ZIELE[0]])
                self.assertEqual(code, gate.EXIT_STOERUNG)
                self.assertEqual(daten["gemessen"], 0)
                self.assertEqual(daten["fehlend"], [])
                self.assertEqual(probe.anzahl, 4)

    def test_get_5xx_wird_wiederholt_bis_die_seite_wieder_da_ist(self):
        (code, _, daten), probe = _messen(
            [(503, {}), (503, {}), (200, {**PROXY, **GUT})],
            pausen=(0,), ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK)
        self.assertEqual(probe.wege, ["HEAD", "GET", "HEAD"])
        self.assertEqual(daten["ziele"][0]["versuche"], 2)

    def test_programmfehler_wird_nicht_als_netzstoerung_kaschiert(self):
        with self.assertRaises(NameError):
            _messen([NameError("Code kaputt")], ziele=[gate.ZIELE[0]])

    def test_rohe_cookies_werden_nicht_in_json_artefakte_kopiert(self):
        (code, bericht, daten), _ = _messen(
            [(200, {**PROXY, **GUT, "set-cookie": "GIFT_COOKIE", "x-debug": "GIFT_DEBUG"})],
            ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK)
        self.assertNotIn("GIFT_COOKIE", json.dumps(daten) + bericht)
        self.assertNotIn("GIFT_DEBUG", json.dumps(daten) + bericht)


class TeilweiseGemessen(unittest.TestCase):
    """Ein Ziel sauber, ein Ziel tot: kein Alarm, aber kein Freibrief."""

    def test_sauberer_host_alarmiert_nicht(self):
        def holen(url, weg):
            if url == gate.ZIELE[0]:
                return (200, {**PROXY, **GUT})
            raise OSError("Name or service not known")
        code, bericht, daten = gate.netz_pruefen(holen=holen, pausen=(),
                                                 schlaf=lambda _: None)
        self.assertEqual(code, gate.EXIT_OK)
        self.assertEqual(daten["klasse"], gate.KLASSE_TEILWEISE)
        self.assertEqual(daten["nicht_gemessen"], [gate.ZIELE[1]])

    def test_das_nicht_gemessene_ziel_wird_benannt(self):
        def holen(url, weg):
            if url == gate.ZIELE[0]:
                return (200, {**PROXY, **GUT})
            raise OSError("Name or service not known")
        _, bericht, _ = gate.netz_pruefen(holen=holen, pausen=(),
                                          schlaf=lambda _: None)
        self.assertIn(gate.ZIELE[1], bericht)

    def test_ein_gemessener_befund_sticht_die_stoerung(self):
        def holen(url, weg):
            if url == gate.ZIELE[0]:
                return (200, {**PROXY, "x-content-type-options": "nosniff"})
            raise OSError("Connection reset by peer")
        code, _, daten = gate.netz_pruefen(holen=holen, pausen=(),
                                           schlaf=lambda _: None)
        self.assertEqual(code, gate.EXIT_BEFUND)
        self.assertEqual(daten["klasse"], gate.KLASSE_BEFUND)
        self.assertEqual(daten["gemessen"], 1)
        self.assertTrue(any(gate.ZIELE[0] in f for f in daten["fehlend"]))


class ProxyDiagnose(unittest.TestCase):
    """Der Bericht nennt die Ursache, nicht nur das Symptom."""

    def test_proxy_erkennung(self):
        self.assertEqual(gate.proxy_lage({"cf-ray": "abc-FRA"}), gate.PROXY_AKTIV)
        self.assertEqual(gate.proxy_lage({"server": "cloudflare"}), gate.PROXY_AKTIV)
        self.assertEqual(gate.proxy_lage({"server": "GitHub.com"}), gate.PROXY_FEHLT)
        self.assertEqual(gate.proxy_lage({}), gate.PROXY_UNBEKANNT)

    def test_proxy_fehlt_zeigt_auf_den_dashboard_schritt(self):
        (code, bericht, daten), _ = _messen([(200, {"server": "GitHub.com"})],
                                            ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_BEFUND)
        self.assertEqual(daten["proxy"], gate.PROXY_FEHLT)
        self.assertIn("A1 Schritt 1", daten["naechster_schritt"])
        self.assertIn("gar nicht wirken", bericht)

    def test_proxy_aktiv_zeigt_auf_die_regel_nicht_auf_den_proxy(self):
        (code, _, daten), _ = _messen(
            [(200, {**PROXY, "content-security-policy": "default-src 'self'",
                    "x-content-type-options": "nosniff", "x-frame-options": "DENY",
                    "referrer-policy": "strict-origin-when-cross-origin",
                    "strict-transport-security": "max-age=300"})],
            ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_BEFUND)
        self.assertEqual(daten["proxy"], gate.PROXY_AKTIV)
        self.assertIn("FF Sicherheits-Header", daten["naechster_schritt"])
        self.assertNotIn("Proxied", daten["naechster_schritt"])

    def test_815_proxy_aktiv_erinnert_an_offenen_datenschutz_b7(self):
        (code, bericht, daten), _ = _messen(
            [(200, {**PROXY, **GUT})], ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK)
        self.assertTrue(any("Datenschutz-Folge B7 offen" in w for w in daten["warnungen"]))
        self.assertTrue(any("Datenschutz-Folge B7 offen" in b for b in daten["abschluss_blocker"]))
        self.assertIn("edge:b7:apply", bericht)

    def test_815_fehlende_datenschutzdatei_ist_ebenfalls_abschlussblocker(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp, patch.object(gate, "WURZEL", Path(tmp)):
            (code, bericht, daten), _ = _messen(
                [(200, {**PROXY, **GUT})], ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK)
        self.assertIn("nicht prüfbar", bericht)
        self.assertTrue(any("fehlt" in b for b in daten["abschluss_blocker"]))

    def test_815_alte_empfaengertabelle_allein_blockiert_den_abschluss(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            wurzel = Path(tmp)
            datei = wurzel / "content" / "datenschutz" / "index.md"
            datei.parent.mkdir(parents=True)
            datei.write_text("| GitHub (Hosting); Cloudflare (DNS) |", encoding="utf-8")
            with patch.object(gate, "WURZEL", wurzel):
                (code, _, daten), _ = _messen(
                    [(200, {**PROXY, **GUT})], ziele=[gate.ZIELE[0]])
        self.assertEqual(code, gate.EXIT_OK)
        self.assertTrue(any("Empfängertabelle" in b for b in daten["abschluss_blocker"]))


class WorkflowVerdrahtung(unittest.TestCase):
    """Vertrag C34: Der Workflow wertet aus, er reicht nicht durch.

    Ohne diese Verdrahtung wäre die gesamte Klassifikation nur Kosmetik:
    GitHub kennt am Schritt nur rot oder grün, und der Melder müßte wieder
    raten, was rot bedeutet.
    """

    def setUp(self):
        if not WORKFLOW.exists():
            self.skipTest("sicherheits-wache.yml fehlt")
        self.text = WORKFLOW.read_text(encoding="utf-8")

    def test_mess_schritt_reicht_seinen_exit_nicht_durch(self):
        self.assertNotRegex(
            self.text, r"run: python3 scripts/blog_header_gate\.py\s*\n",
            "Der Mess-Schritt darf kein nackter Durchreicher sein (Vertrag C34)")

    def test_exit_code_wird_festgehalten(self):
        self.assertIn("code=$?", self.text)
        self.assertIn("steps.header.outputs.code", self.text)

    def test_auswerte_schritt_unterscheidet_befund_und_stoerung(self):
        self.assertIn("F-01 BEFUND", self.text)
        self.assertIn("F-01 STOERUNG", self.text)
        self.assertIn("F-01 WACHE-FEHLER", self.text)

    def test_bericht_geht_in_die_zusammenfassung(self):
        # Lehre aus INCIDENT-2026-09-19: Die Wahrheit steht in der
        # Zusammenfassung, nicht versteckt im Log.
        self.assertIn("sicherheits_nachweis.py --auswerten", self.text)
        auswertung = (REPO / "scripts" / "sicherheits_nachweis.py").read_text()
        self.assertIn("GITHUB_STEP_SUMMARY", auswertung)

    def test_auswerte_schritt_bleibt_vom_alarm_routing_findbar(self):
        # Das Fehler-Alerting ordnet die Sicherheits-Wache über die Zeichen-
        # kette „Sicherheits-Header" im Schrittnamen zu (WF-E813). Würde der
        # Schritt umbenannt, fiele die Meldung still auf den Schlüssel-Rat
        # zurück – deshalb ist die Kopplung hier festgenagelt.
        self.assertIn("Sicherheits-Header auswerten", self.text)

    def test_worker_messung_wird_von_rotem_f01_nicht_verdeckt(self):
        worker = self.text.split("- name: Worker-Zustand messen", 1)[1].split("        run:", 1)[0]
        self.assertIn("!cancelled()", worker)
        self.assertNotIn("steps.header", worker)


class WorkflowShellRegression(unittest.TestCase):
    """Echte run-Blöcke mit Runner-Bash -e; nur die HTTP-Messung ist ersetzt."""

    @staticmethod
    def block(marker):
        text = WORKFLOW.read_text(encoding="utf-8")
        step = text.split(marker, 1)[1]
        lines = step.split("        run: |\n", 1)[1].splitlines()
        body = []
        for line in lines:
            if line and not line.startswith("          "):
                break
            body.append(line)
        return textwrap.dedent("\n".join(body))

    def run_block(self, block, root, env):
        if not (root / "scripts").exists():
            (root / "scripts").symlink_to(REPO / "scripts", target_is_directory=True)
        return subprocess.run(
            ["bash", "--noprofile", "--norc", "-e", "-o", "pipefail", "-c", block],
            cwd=root, env={**os.environ, **env}, capture_output=True, text=True,
            timeout=10)

    @staticmethod
    def fake_measure(code, prefix):
        daten = {"exit": code, "klasse": {0: "OK", 1: "BEFUND", 2: "STOERUNG"}.get(code, "UNBEKANNT"),
                 "gemessen": 0 if code == 2 else 1, "fehlend": ["Testbefund"] if code == 1 else [],
                 "warnungen": [], "stoerung": ["NICHT geprüft"] if code == 2 else [],
                 "bericht": "Messbericht", "naechster_schritt": "Runbook prüfen"}
        # Der run-Block entfernt alte Berichte vor dem Messaufruf. Daher
        # erzeugt die Attrappe sie im Aufruf, wie das echte --report.
        payload = json.dumps(daten)
        return (f"python3() {{ printf '%s' '{payload}'; "
                f"printf '%s' 'Messbericht' > {prefix}.md; return {code}; }}\n")

    def test_header_capture_and_evaluation_under_errexit(self):
        measure = self.block("id: header")
        evaluate = self.block("- name: Sicherheits-Header auswerten")
        for code, expected in ((0, "grün"), (1, "BEFUND"), (2, "STOERUNG"),
                               (3, "WACHE-FEHLER"), (127, "WACHE-FEHLER")):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                env = {"GITHUB_OUTPUT": str(root / "output"),
                       "GITHUB_STEP_SUMMARY": str(root / "summary"), "MESS_CODE": str(code)}
                result = self.run_block(self.fake_measure(code, "f01-live") + measure, root, env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / "output").read_text(), f"code={code}\n")
                result = self.run_block(evaluate, root, env)
                self.assertEqual(result.returncode, 0 if code == 0 else 1, result.stderr)
                self.assertIn(expected, result.stdout)
                summary = (root / "summary").read_text()
                self.assertIn("Messbericht" if code in (0, 1, 2) else "WACHE-FEHLER", summary)

    def test_missing_header_report_is_not_green(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_block(self.block("- name: Sicherheits-Header auswerten"), root,
                                    {"GITHUB_STEP_SUMMARY": str(root / "summary"), "MESS_CODE": "0"})
            self.assertEqual(result.returncode, 1)
            self.assertIn("WACHE-FEHLER", result.stdout)

    def test_output_write_failure_is_not_swallowed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            result = self.run_block("python3() { return 0; }\n" + self.block("id: header"),
                                    root, {"GITHUB_OUTPUT": str(root / "missing" / "output")})
            self.assertNotEqual(result.returncode, 0)

    def test_worker_keeps_exit_and_summary(self):
        measure = self.block("id: worker")
        evaluate = self.block("- name: Worker-Zustand auswerten")
        for code, expected in ((0, "grün"), (1, "BEFUND"),
                               (2, "STOERUNG"), (3, "WACHE-FEHLER")):
            with self.subTest(code=code), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                env = {"GITHUB_OUTPUT": str(root / "output"),
                       "GITHUB_STEP_SUMMARY": str(root / "summary"), "MESS_CODE": str(code)}
                result = self.run_block(self.fake_measure(code, "worker-live") + measure, root, env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual((root / "output").read_text(), f"code={code}\n")
                result = self.run_block(evaluate, root, env)
                self.assertEqual(result.returncode, 0 if code == 0 else 1, result.stderr)
                self.assertIn(expected, result.stdout)
                self.assertIn("Messbericht" if code in (0, 1, 2) else "WACHE-FEHLER",
                              (root / "summary").read_text())

    def test_alte_berichte_werden_vor_jeder_messung_entfernt(self):
        for marker, prefix in (("id: header", "f01-live"), ("id: worker", "worker-live")):
            with self.subTest(marker=marker), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                (root / f"{prefix}.md").write_text("alter Bericht")
                (root / f"{prefix}.json").write_text('{"klasse":"OK"}')
                env = {"GITHUB_OUTPUT": str(root / "output")}
                result = self.run_block("python3() { return 127; }\n" + self.block(marker), root, env)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertFalse((root / f"{prefix}.md").exists())
                self.assertEqual((root / f"{prefix}.json").read_text(), "")
                self.assertEqual((root / "output").read_text(), "code=127\n")

    def test_missing_worker_key_is_explicitly_unchecked_and_red(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            env = {"GITHUB_OUTPUT": str(root / "output"),
                   "GITHUB_STEP_SUMMARY": str(root / "summary"), "MESS_CODE": "2",
                   "NEWSLETTER_WORKER_BASE": "https://abos.franksfinanzcheck.de",
                   "NEWSLETTER_WORKER_EXPORT_KEY": ""}
            result = self.run_block(self.block("id: worker"), root, env)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual((root / "output").read_text(), "code=2\n")
            result = self.run_block(self.block("- name: Worker-Zustand auswerten"), root, env)
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn("Worker STOERUNG", result.stdout)
            self.assertIn("NICHT geprüft", (root / "summary").read_text())


class AlarmRouting(unittest.TestCase):
    """Die Meldung darf nicht auf einen Schlüssel raten (WF-E813, zweiter Fehler)."""

    def setUp(self):
        self.pfad = REPO / ".github" / "workflows" / "alert-on-failure.yml"
        if not self.pfad.exists():
            self.skipTest("alert-on-failure.yml fehlt")
        self.text = self.pfad.read_text(encoding="utf-8")

    def test_sicherheits_wache_hat_eigene_triage(self):
        self.assertIn("istSicherheitsWache", self.text)
        self.assertIn("headerGateFailed", self.text)
        self.assertIn("Bei WACHE-FEHLER", self.text)
        self.assertIn("wfName === 'Sicherheits-Wache'", self.text)

    def test_die_triage_haengt_an_der_runbook_klasse(self):
        # WF-9E5A / #761 (15.10.2026): Der Rat in einer offenen Meldung wird
        # nur nachgeführt, wenn die Klasse einen EIGENEN Namen hat. Hängt die
        # Sicherheits-Wache an der allgemeinen Klasse, bleibt in offenen
        # Meldungen der alte Rat stehen – genau der befundete Schaden.
        self.assertIn("runbookKlasse === 'sicherheit-header'", self.text)
        self.assertIn("runbookKlasse === 'sicherheit-wache'", self.text)
        self.assertIn("headerGateFailed ? 'sicherheit-header'", self.text)
        self.assertIn("istSicherheitsWache ? 'sicherheit-wache'", self.text)

    def test_die_triage_verweist_auf_die_beiden_runsbooks(self):
        self.assertIn("docs/SICHERHEIT-BETRIEB-RUNBOOK.md", self.text)
        self.assertIn("cloudflare/edge-schutz.md", self.text)


if __name__ == "__main__":
    unittest.main()
