# -*- coding: utf-8 -*-
"""Tests für `scripts/push_diagnose.py` – Ursache statt Rateschluss.

ANLASS (21.11.2026, Vorgänge #1254/#1246/#1245/#1244):
Vier rote Läufe, alle im Commit-/Push-Schritt, alle mit demselben Rat im
Issue („API-Key abgelaufen", „GitHub-Ausfall", „neu starten"). Belegt war
das Gegenteil: kein Schlüssel im Spiel, kein Branch-Schutz, und dreimal
nicht einmal ein echter Git-Fehler – nur die Restmenge „netzwerk", die ein
Non-Fast-Forward-Rennen verschluckte.

Diese Tests nageln zwei Dinge fest:
  1. Die ECHTEN Annotationstexte dieser vier Vorgänge werden richtig
     eingeordnet (kein Rückfall in „unbekannt").
  2. Rote Tests und Builds zählen NICHT als Push-Befund – sonst würde das
     Werkzeug genau den Fehler wiederholen, den es behebt.
"""
from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import push_diagnose as pd  # noqa: E402

# Unveränderte Zitate aus den Schritt-Annotationen der Läufe
# 44108239933 (#1254), 43873009604 (#1246), 43873227943 (#1245),
# 43872362876 (#1244) – so, wie der Runner sie hinterlassen hat.
ECHTER_FALL_1254 = (
    "git_sync.sh: Rebase-Konflikt gegen origin/main  (ein paralleler Workflow "
    "hat dieselben Zeilen geändert).  Betroffen: content/posts/2026-11-13-"
    "tagesgeld-und-zinsen-so-parkst-du-dein-geld-sicher/index.md .  Kein Push "
    "– Arbeitsstand bleibt lokal sauber.")
ECHTER_FALL_1246 = (
    "git_sync.sh: Synchronisation nach 3 Runden  fehlgeschlagen (zuletzt: "
    "netzwerk). Mögliche Ursachen:  GitHub-Transient, fehlende 'contents: "
    "write'-Berechtigung,  Branch-Schutz (Ruleset mit Pflicht-Check ohne "
    "Bypass-Akteur –  docs/PFLICHT-CHECK-RUNBOOK.md), ein zwischenzeitlich "
    "gelöschtes  Ziel-Ref (ref_fehlt) oder ein anderer Workflow schreibt "
    "gleichzeitig.")


class EchteVorgaengeTest(unittest.TestCase):
    """Die vier Vorgänge, die den Auftrag ausgelöst haben."""

    def test_1254_ist_ein_echter_konflikt(self):
        self.assertEqual("konflikt", pd.klassifiziere(ECHTER_FALL_1254))
        self.assertEqual("Git-Meldung", pd.quelle(ECHTER_FALL_1254))

    def test_1244_bis_1246_sind_restmenge_der_selbsteinordnung(self):
        for text in (ECHTER_FALL_1246,
                     "git_sync.sh: Synchronisation nach 3 Runden  "
                     "fehlgeschlagen (zuletzt: netzwerk)."):
            with self.subTest(text=text[:40]):
                self.assertEqual("netzwerk", pd.klassifiziere(text))
                self.assertEqual("Selbsteinordnung git_sync.sh",
                                 pd.quelle(text),
                                 "die Selbsteinordnung des Laufs muss als "
                                 "Belegquelle sichtbar sein, nicht als Vermutung")

    def test_kein_rateschluss_bei_schutzsprache_im_resttext(self):
        """#1246 NENNT Branch-Schutz als MÖGLICHE Ursache – ohne Beleg.

        Die Selbsteinordnung des Laufs ist „netzwerk“; die Aufzählung
        danach ist eine Liste von Möglichkeiten, kein Befund. Würde das
        Werkzeug auf „Branch-Schutz“ springen, hätte es den Fehler der
        alten Issues (Raten) nur in neuer Form wiederholt.
        """
        self.assertEqual("netzwerk", pd.klassifiziere(ECHTER_FALL_1246))
        self.assertNotEqual("schutz", pd.klassifiziere(ECHTER_FALL_1246))

    def test_rohmeldung_gewinnt_gegen_restmenge(self):
        text = (ECHTER_FALL_1246 +
                "\n! [rejected]        HEAD -> main (non-fast-forward)")
        self.assertEqual("push_rennen", pd.klassifiziere(text),
                         "ein belegtes Rennen darf nicht als Restmenge "
                         "durchgehen")


class KlassenTest(unittest.TestCase):
    def test_alle_klassen_haben_titel_und_handlung(self):
        for name, titel, handlung in pd.KLASSEN:
            with self.subTest(klasse=name):
                self.assertTrue(titel.strip())
                self.assertTrue(handlung.strip())

    def test_schutz_schlaegt_rejected(self):
        text = ("remote: error: GH013: Repository rule violations found for "
                "refs/heads/main.\n! [remote rejected] HEAD -> main (push "
                "declined due to repository rule violations)")
        self.assertEqual("schutz", pd.klassifiziere(text))

    def test_auth(self):
        self.assertEqual("auth", pd.klassifiziere(
            "remote: Permission to x/y.git denied to github-actions[bot]."))
        self.assertEqual("auth", pd.klassifiziere(
            "fatal: could not read Username for 'https://github.com'"))

    def test_transient(self):
        self.assertEqual("netzwerk", pd.klassifiziere(
            "error: RPC failed; curl 92 HTTP/2 stream 5 was not closed cleanly"))

    def test_unbekannt_bleibt_unbekannt(self):
        self.assertEqual("unbekannt", pd.klassifiziere(
            "Process completed with exit code 1."))
        self.assertEqual("unbekannt", pd.klassifiziere(""))


class KeinFehlalarmTest(unittest.TestCase):
    """Ein roter Test ist kein Push-Befund."""

    def test_tests_und_builds_zaehlen_nicht(self):
        for schritt in ("Selbsttests HART", "Seite bauen",
                        "Governance-Selbsttests (alle Wachen)",
                        "Live-Messung (täglich und auf Zuruf)",
                        "Siegel auswerten (Auslieferung ist zu diesem Punkt "
                        "bereits gelaufen)"):
            with self.subTest(schritt=schritt):
                self.assertIsNone(pd.COMMIT_SCHRITT.search(schritt))

    def test_commitschritte_werden_erkannt(self):
        for schritt in ("Gate-Heilungen committen (konvergent)",
                        "Änderungen committen & pushen (Redaktions-Bot)",
                        "Audit-Log-Stand committen (data/audit)",
                        'Run git config user.name "Agent (Arena.ai)"',
                        "Belege & Dossiers committen"):
            with self.subTest(schritt=schritt):
                self.assertIsNotNone(pd.COMMIT_SCHRITT.search(schritt))


class CliTest(unittest.TestCase):
    def test_selftest_gruen(self):
        erg = subprocess.run([sys.executable,
                              str(ROOT / "scripts" / "push_diagnose.py"),
                              "--selftest"],
                             capture_output=True, text=True, check=False)
        self.assertEqual(0, erg.returncode, erg.stdout + erg.stderr)

    def test_bericht_ohne_laeufe_ist_gruen_und_ehrlich(self):
        d = pd.bericht([])
        self.assertEqual(0, d["anzahl"])
        self.assertIn("kein Commit-/Push-Fehlschlag", pd.text_bericht(d))

    def test_bericht_gruppiert_und_nennt_die_handlung(self):
        laeufe = [
            {"workflow": "A", "created": "2026-11-16T14:08:56Z",
             "url": "u1", "klasse": "netzwerk", "meldung": "zuletzt: netzwerk",
             "quelle": "Selbsteinordnung git_sync.sh", "selbst": "netzwerk",
             "schritte": [{"name": "Audit-Log-Stand committen"}]},
            {"workflow": "B", "created": "2026-11-17T15:54:21Z",
             "url": "u2", "klasse": "konflikt",
             "meldung": "Rebase-Konflikt", "quelle": "Git-Meldung",
             "selbst": "", "schritte": [{"name": "Commit"}]},
        ]
        d = pd.bericht(laeufe)
        self.assertEqual(2, d["anzahl"])
        klassen = [g["klasse"] for g in d["klassen"]]
        # Rangfolge: die Ursache (Konflikt) steht vor der Restmenge.
        self.assertEqual(["konflikt", "netzwerk"], klassen)
        text = pd.text_bericht(d)
        self.assertIn("Echter Inhalts-Konflikt", text)
        self.assertIn("Restmenge", text)


class DrosselungIstKeinTokenProblemTest(unittest.TestCase):
    """#1244–#1246: Der Rat „API-Key/Token prüfen" war der Dauerschaden.

    GitHub drosselt mit HTTP 429 UND mit „secondary rate limit" – und tarnt
    beides oft als 403. Das Auth-Muster liest „403". Steht `rate_limit` nicht
    VOR `auth` in KLASSEN (= Rangfolge `RANG`), wird aus einer Drosselung ein
    angebliches Token-Problem, und der Lauf wiederholt sich, bis das
    Kontingent noch tiefer im Keller ist. Diese Klasse hält beides fest:
    die richtige Einordnung UND die Gegenprobe, dass echtes Auth rot bleibt.
    """

    def test_429_ist_eine_drosselung(self):
        self.assertEqual("rate_limit", pd.klassifiziere("HTTP 429: Too Many Requests"))

    def test_als_403_getarnte_drosselung_ist_kein_auth_fehler(self):
        text = ("remote: You have exceeded a secondary rate limit. "
                "Please wait a few minutes before you try again. (HTTP 403)")
        self.assertEqual("rate_limit", pd.klassifiziere(text))

    def test_api_rate_limit_mit_403(self):
        self.assertEqual("rate_limit",
                         pd.klassifiziere("error: 403 Forbidden – API rate limit exceeded"))

    def test_echtes_auth_bleibt_auth(self):
        """Gegenprobe: Die Drosselungs-Regel darf Auth nicht verschlucken."""
        for text in (
            "fatal: Authentication failed for 'https://github.com/x/y.git/'",
            "remote: Invalid username or password.",
            "fatal: could not read Username for 'https://github.com': No such device",
        ):
            with self.subTest(text=text):
                self.assertEqual("auth", pd.klassifiziere(text))

    def test_drosselung_steht_vor_auth_und_netzwerk(self):
        rang = pd.RANG
        self.assertLess(rang.index("rate_limit"), rang.index("auth"))
        self.assertLess(rang.index("rate_limit"), rang.index("netzwerk"))

    def test_der_rat_widerspricht_dem_neustart(self):
        """Der Rat muss den Neustart AUSDRÜCKLICH verneinen, nicht nur meiden.

        Erste Fassung dieses Tests prüfte „enthält nicht die Wörter erneut
        versuchen" – und war damit falsch: Der Rat sagt „ERNEUT VERSUCHEN
        MACHT ES SCHLIMMER". Ein Test, der eine Verneinung mit einem
        WortverboT verwechselt, hätte den Satz gelöscht statt geprüft.
        """
        handlung = pd.handlung("rate_limit")
        self.assertIn("SCHLIMMER", handlung)
        self.assertIn("Re-run", handlung)
        self.assertIn("falsche Antwort", handlung)

    def test_gewOEhnlicher_netzwerkfehler_bleibt_netzwerk(self):
        """Gegenprobe: Die neue Klasse darf die Restmenge nicht schlucken."""
        self.assertEqual("netzwerk",
                         pd.klassifiziere("fatal: RPC failed; the remote end hung up"))


if __name__ == "__main__":
    unittest.main()
