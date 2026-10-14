#!/usr/bin/env python3
"""Vertragstests für die Messkette (Dauerheilung #740, C38).

GEPRÜFTER VERTRAG
-----------------
Der Ausfall vom 14.10.2026 hatte eine banale Ursache: `hunspell` war in
sechs Workflows installiert – im `deploy`-Job nie. Der Mess-Schritt
„Quote-Nachfüllung" stürzte an einem fehlenden Wörterbuch ab und nahm die
öffentliche Auslieferung mit (zehn rote Läufe, Live-Stand eingefroren).

Die Heilung hat drei Ebenen, und alle drei werden hier festgehalten:

  1. EINE Quelle der Wahrheit statt Copy-Paste pro Workflow
     (`measurement_chain.py` kennt Binary, Wörterbuch, Installationszeile).
  2. Ein früher, benannter Abbruch statt eines Tracebacks nach dem Build
     (`require()` im Vorflug der Quote-Nachfüllung → Exit 3 mit Heilungsweg).
  3. Eine statische Vollständigkeitsprüfung: Wer misst, installiert vorher
     (`audit_workflows()` über ALLE Workflows, nicht nur über deploy.yml).

Besonders wichtig ist Punkt 3 – er hat beim Schreiben dieser Heilung einen
zweiten, bis dahin unsichtbaren Fall gefunden: `frankautoops-report.yml`
maß die Qualitätskennzahl des gesamten Bestands jeden Tag ohne hunspell.
"""

from __future__ import annotations

import datetime as dt
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))

import measurement_chain as mk  # noqa: E402
import publication_release as pr  # noqa: E402
import selftest_clock as uhr_zwang  # noqa: E402

# Mittwoch – nur an Publikationstagen füllt der Release nach (cadence_guard).
_POSTTAG = dt.datetime(2026, 11, 4, 12, 0, tzinfo=dt.timezone.utc)


class EchteWorkflowsSindVollstaendig(unittest.TestCase):
    """Der Vertrag am echten Bestand – das ist der Regressionstest zu #740."""

    def test_kein_messlauf_ohne_werkzeug(self):
        befunde = mk.audit_workflows()
        self.assertEqual(befunde, [],
                         "Messkette unvollständig:\n  - "
                         + "\n  - ".join(befunde))

    def test_deploy_installiert_vor_der_quote_nachfuellung(self):
        """Der konkrete Fall: #740, Schritt für Schritt nachgewiesen."""
        import yaml

        deploy = yaml.safe_load(
            (ROOT / ".github" / "workflows" / "deploy.yml")
            .read_text(encoding="utf-8"))
        steps = deploy["jobs"]["deploy"]["steps"]
        kette = messer = None
        for i, step in enumerate(steps):
            text = str(step.get("run") or "")
            if kette is None and mk.BINARY in text and "apt-get" in text:
                kette = i
            if messer is None and "publication_release.py" in \
                    mk.messaufrufe_im_schritt(text):
                messer = i
        self.assertIsNotNone(kette, "deploy.yml installiert hunspell nicht – "
                                    "exakt der Zustand vom 14.10.2026")
        self.assertIsNotNone(messer, "Die Quote-Nachfüllung fehlt im Deploy")
        self.assertLess(kette, messer,
                        "Die Messkette wird erst NACH dem Mess-Schritt "
                        "installiert – sie nützt dann nichts")

    def test_alle_installationen_nennen_dieselben_pakete(self):
        """Kein Workflow installiert eine andere Teilmenge der Kette."""
        for datei in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
            text = datei.read_text(encoding="utf-8")
            for zeile in text.splitlines():
                if "apt-get install" not in zeile or mk.BINARY not in zeile:
                    continue
                for paket in mk.APT_PAKETE:
                    self.assertIn(
                        paket, zeile,
                        f"{datei.name}: installiert hunspell ohne `{paket}` – "
                        f"ein Binary ohne Wörterbuch misst nichts "
                        f"({zeile.strip()})")


class LaufzeitAuskunft(unittest.TestCase):
    def test_status_hat_immer_eine_form(self):
        lage = mk.status()
        for schluessel in ("vollstaendig", "fehlend", "installationszeile"):
            self.assertIn(schluessel, lage)
        self.assertIsInstance(lage["fehlend"], list)
        if lage["vollstaendig"]:
            self.assertEqual(lage["fehlend"], [])

    def test_fehlertext_nennt_heilung_und_vertrag(self):
        text = mk.fehlertext("Testlauf", {"fehlend": ["hunspell"],
                                          "installationszeile": mk.INSTALLATIONSZEILE})
        self.assertIn(mk.INSTALLATIONSZEILE, text)
        self.assertIn("C33", text, "Die Regel ‚kein Grün ohne Messung‘ fehlt")
        self.assertIn("#740", text)

    @unittest.skipIf(shutil.which(mk.BINARY) is None,
                     "hunspell nicht installiert – positive Probe entfällt")
    def test_require_laesst_durch_wenn_alles_da_ist(self):
        self.assertTrue(mk.require("Testlauf")["vollstaendig"])

    def test_require_meldet_fehlende_kette(self):
        with patch.object(mk, "status", lambda: {
                "vollstaendig": False, "fehlend": ["hunspell (Programm fehlt)"],
                "installationszeile": mk.INSTALLATIONSZEILE}):
            with self.assertRaises(mk.MesskettenFehler) as ctx:
                mk.require("Quote-Nachfüllung")
            self.assertIn("Quote-Nachfüllung", str(ctx.exception))
            self.assertIn(mk.INSTALLATIONSZEILE, str(ctx.exception))

    def test_abschalter_wirkt_nur_mit_exaktem_wert(self):
        alt = os.environ.get("MESSKETTE_VORFLUG")
        try:
            with patch.object(mk, "status", lambda: {
                    "vollstaendig": False, "fehlend": ["hunspell"],
                    "installationszeile": mk.INSTALLATIONSZEILE}):
                os.environ["MESSKETTE_VORFLUG"] = "aus"
                self.assertTrue(mk.require("Test").get("uebersprungen"))
                os.environ["MESSKETTE_VORFLUG"] = "an"
                with self.assertRaises(mk.MesskettenFehler):
                    mk.require("Test")
        finally:
            os.environ.pop("MESSKETTE_VORFLUG", None)
            if alt is not None:
                os.environ["MESSKETTE_VORFLUG"] = alt


class AufrufErkennung(unittest.TestCase):
    """Ein Selbsttest ist kein Messlauf – aber ein Messlauf dahinter schon."""

    def test_messlauf_wird_erkannt(self):
        self.assertEqual(
            mk.messaufrufe_im_schritt(
                "python3 scripts/publication_release.py --refill-only"),
            ["publication_release.py"])

    def test_selbsttest_zaehlt_nicht(self):
        self.assertEqual(
            mk.messaufrufe_im_schritt("python3 scripts/reserve_pool.py --selftest"),
            [])

    def test_selbsttest_verdeckt_den_messlauf_nicht(self):
        """`a --selftest && a --refill-only` ist ein Messlauf."""
        self.assertEqual(
            mk.messaufrufe_im_schritt(
                "python3 scripts/publication_release.py --selftest && "
                "python3 scripts/publication_release.py --refill-only"),
            ["publication_release.py"])

    def test_kommentare_zaehlen_nicht(self):
        self.assertEqual(
            mk.messaufrufe_im_schritt("# python3 scripts/ops_report.py"), [])


class SabotageProben(unittest.TestCase):
    """Eine Wache, die nur grün kann, ist keine Wache."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.wurzel = Path(self._tmp.name)
        (self.wurzel / "scripts").mkdir()
        (self.wurzel / ".github" / "workflows").mkdir(parents=True)
        for name in mk.MESSENDE_SKRIPTE:
            (self.wurzel / "scripts" / name).write_text("# Attrappe\n",
                                                        encoding="utf-8")

    def tearDown(self):
        self._tmp.cleanup()

    def _audit(self, inhalt: str) -> list[str]:
        (self.wurzel / ".github" / "workflows" / "probe.yml").write_text(
            textwrap.dedent(inhalt), encoding="utf-8")
        return [b for b in mk.audit_workflows(root=self.wurzel)
                if "probe.yml" in b]

    def test_messen_ohne_kette_faellt_auf(self):
        befunde = self._audit("""
            name: Probe
            jobs:
              bau:
                steps:
                  - name: Quote-Nachfüllung
                    run: python3 scripts/publication_release.py --refill-only
            """)
        self.assertTrue(befunde, "Der Befund aus #740 bliebe unentdeckt")
        self.assertIn("#740", befunde[0])
        self.assertIn(mk.INSTALLATIONSZEILE, befunde[0],
                      "Ein Befund ohne Heilungsweg erzieht zum Wegsehen")

    def test_kette_davor_ist_in_ordnung(self):
        self.assertEqual(self._audit("""
            name: Probe
            jobs:
              bau:
                steps:
                  - name: Abhängigkeiten
                    run: sudo apt-get install -y -qq hunspell hunspell-de-de
                  - name: Quote-Nachfüllung
                    run: python3 scripts/publication_release.py --refill-only
            """), [])

    def test_kette_danach_ist_ein_befund(self):
        self.assertTrue(self._audit("""
            name: Probe
            jobs:
              bau:
                steps:
                  - name: Quote-Nachfüllung
                    run: python3 scripts/publication_release.py --refill-only
                  - name: Abhängigkeiten
                    run: sudo apt-get install -y -qq hunspell hunspell-de-de
            """), "Reihenfolge wird nicht geprüft")

    def test_kette_in_fremdem_job_zaehlt_nicht(self):
        self.assertTrue(self._audit("""
            name: Probe
            jobs:
              vorbereiten:
                steps:
                  - name: Abhängigkeiten
                    run: sudo apt-get install -y -qq hunspell hunspell-de-de
              bau:
                steps:
                  - name: Quote-Nachfüllung
                    run: python3 scripts/publication_release.py --refill-only
            """), "Jobs teilen sich keinen Runner – das muss auffallen")

    def test_workflow_darf_den_vorflug_nicht_abschalten(self):
        """Der Abschalter gehört auf lokale Rechner, nicht in CI."""
        befunde = self._audit("""
            name: Probe
            jobs:
              bau:
                env:
                  MESSKETTE_VORFLUG: aus
                steps:
                  - name: Abhängigkeiten
                    run: sudo apt-get install -y -qq hunspell hunspell-de-de
                  - name: Messen
                    run: python3 scripts/publication_release.py --refill-only
            """)
        self.assertTrue(befunde, "Ein stiller Bypass bleibt unentdeckt")
        self.assertIn("MESSKETTE_VORFLUG", befunde[0])

    def test_neues_messendes_skript_faellt_auf(self):
        (self.wurzel / "scripts" / "neuer_messer.py").write_text(
            "import quality_score as qs\n", encoding="utf-8")
        befunde = [b for b in mk.audit_workflows(root=self.wurzel)
                   if "neuer_messer" in b]
        self.assertTrue(befunde, "Die Registry kann still verrotten")

    def test_registrierte_datei_muss_existieren(self):
        (self.wurzel / "scripts" / "ops_report.py").unlink()
        befunde = [b for b in mk.audit_workflows(root=self.wurzel)
                   if "ops_report.py" in b]
        self.assertTrue(befunde, "Eine tote Registry-Zeile fällt nicht auf")


class VorflugImRelease(unittest.TestCase):
    """Der Befund kommt VOR dem ersten Kandidaten – und heißt beim Namen."""

    def test_refill_bricht_ohne_kette_sauber_ab(self):
        gemessen = []

        def nie(*a, **kw):  # pragma: no cover - darf nicht laufen
            gemessen.append(a)
            return True

        with tempfile.TemporaryDirectory() as tmp:
            posts = Path(tmp) / "content" / "posts"
            posts.mkdir(parents=True)
            artikel = posts / "kandidat" / "index.md"
            artikel.parent.mkdir()
            artikel.write_text(
                "---\ntitle: Kandidat\ndate: 2026-11-04T12:00:00Z\n"
                "draft: true\nreserve: true\n---\nText\n", encoding="utf-8")
            with uhr_zwang.uhr(_POSTTAG, uhr_zwang.MODUS_VERSCHOBEN,
                               module=[pr]), \
                 patch.object(mk, "status", lambda: {
                     "vollstaendig": False, "fehlend": ["hunspell"],
                     "installationszeile": mk.INSTALLATIONSZEILE}), \
                 patch.object(pr, "accept_candidate", nie), \
                 patch("builtins.print"):
                with self.assertRaises(pr.ReleaseBuildCrash) as ctx:
                    pr.refill_to_min(posts_dir=posts, finalize=False)
            self.assertIn("hunspell", str(ctx.exception))
            self.assertIn(mk.INSTALLATIONSZEILE, str(ctx.exception))
            self.assertEqual(gemessen, [],
                             "Es wurde trotz toter Messkette gemessen")
            self.assertIn("draft: true", artikel.read_text(encoding="utf-8"),
                          "Der Abbruch hat trotzdem Inhalte angefasst")

    def test_crash_wird_exit_3_mit_ursache(self):
        """Der Vorflug landet im bestehenden Exit-Vertrag (0/1/3)."""
        import audit_log

        def crash(*a, **kw):
            raise pr.ReleaseBuildCrash(
                mk.fehlertext("Quote-Nachfüllung",
                              {"fehlend": ["hunspell"],
                               "installationszeile": mk.INSTALLATIONSZEILE}))

        with patch.object(pr, "heal_shortcode_damage", lambda *a, **kw: True), \
             patch.object(pr, "_dispatch", crash), \
             patch.object(audit_log, "log_event", lambda **kw: "/dev/null"), \
             patch("builtins.print") as fake_print:
            rc = pr.main(["--refill-only"])
        self.assertEqual(rc, pr.EXIT_CRASH)
        ausgabe = "\n".join(str(c) for c in fake_print.call_args_list)
        self.assertIn("hunspell", ausgabe)
        self.assertIn("apt-get", ausgabe,
                      "Der rote Schritt nennt den Heilungsweg nicht")

    def test_selbsttest_braucht_die_kette_nicht(self):
        """Selbsttests laufen mit Attrappen (Haus-Regel, vgl. KI-Probe #138)."""
        lauf = subprocess.run(
            [sys.executable, str(SCRIPTS / "publication_release.py"),
             "--selftest"], capture_output=True, text=True, timeout=300,
            cwd=str(ROOT))
        self.assertEqual(lauf.returncode, 0,
                         f"Selbsttest ohne hunspell rot:\n{lauf.stdout[-2000:]}")


class WachenSelbsttest(unittest.TestCase):
    def test_selftest_gruen(self):
        lauf = subprocess.run(
            [sys.executable, str(SCRIPTS / "measurement_chain.py"), "--selftest"],
            capture_output=True, text=True, timeout=300)
        self.assertEqual(lauf.returncode, 0,
                         f"Selbsttest rot:\n{lauf.stdout}\n{lauf.stderr}")

    def test_audit_cli_gruen(self):
        lauf = subprocess.run(
            [sys.executable, str(SCRIPTS / "measurement_chain.py"),
             "--audit-workflows"], capture_output=True, text=True, timeout=300)
        self.assertEqual(lauf.returncode, 0,
                         f"--audit-workflows rot:\n{lauf.stdout}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
