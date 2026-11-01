#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vertragstests der Abhängigkeits-Wache.

WARUM DIESE TESTS EXISTIEREN (24.10.2026)
-----------------------------------------
Die Wache entstand aus einem Widerspruch: GitHub meldete 58 offene
Schwachstellen, der ausgelieferte Bestand war nach vollständiger Prüfung
sauber. Ein Werkzeug, das diesen Widerspruch auflösen soll, darf nicht
nur „grün" können. Diese Tests halten deshalb drei Zusagen fest:

1. JEDE REGEL FEUERT. Für A1–A6 gibt es einen vergifteten Baum, in dem
   genau die zuständige Regel anschlägt.
2. KEINE REGEL FEUERT OHNE ANLASS. Ein sauberer Baum bleibt grün, eine
   leere Advisory-Quelle erzeugt keinen Treffer.
3. DER BESTAND BLEIBT SAUBER. Der echte Repo-Baum wird bei jedem Lauf
   geprüft. Fällt jemand auf einen Versions-Range zurück, wird dieser
   Test rot – nicht erst der Alert in der Security-Tab.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts import abhaengigkeits_wache as wache

ROOT = Path(__file__).resolve().parents[2]


class ParserRequirementsTest(unittest.TestCase):
    def test_pin_mit_hash_und_fortsetzung(self) -> None:
        text = (
            "Pillow==13.0.0 \\\n"
            "    --hash=sha256:aaaa \\\n"
            "    --hash=sha256:bbbb\n"
        )
        (anforderung,) = wache.parse_requirements(text)
        self.assertEqual(anforderung.name, "Pillow")
        self.assertEqual(anforderung.version, "13.0.0")
        self.assertEqual(anforderung.herkunft, "pin")
        self.assertEqual(anforderung.zeile, 1)

    def test_bereich_und_ungepinnt(self) -> None:
        anforderungen = {a.name: a for a in wache.parse_requirements("a>=1.2\nb\n")}
        self.assertEqual(anforderungen["a"].herkunft, "range")
        self.assertEqual(anforderungen["a"].version, "1.2")
        self.assertEqual(anforderungen["b"].herkunft, "range")
        self.assertEqual(anforderungen["b"].version, "")

    def test_extras_marker_und_kommentar(self) -> None:
        (anforderung,) = wache.parse_requirements(
            'requests[security,socks]==2.34.2 ; python_version >= "3.10"  # fest\n'
        )
        self.assertEqual(anforderung.name, "requests")
        self.assertEqual(anforderung.version, "2.34.2")

    def test_url_und_include_werden_ignoriert(self) -> None:
        text = "-r other.txt\nhttps://example.org/x-1.0.tar.gz\ngit+https://example.org/x.git\n"
        self.assertEqual(wache.parse_requirements(text), [])

    def test_wildcard_pin_ist_ein_bereich(self) -> None:
        (anforderung,) = wache.parse_requirements("pyyaml==6.0.*\n")
        self.assertEqual(anforderung.herkunft, "range")


class ParserLockfileTest(unittest.TestCase):
    def test_pakete_und_scopes(self) -> None:
        lock = {
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "x", "version": "1.0.0"},
                "node_modules/a": {"version": "2.0.0"},
                "node_modules/@scope/b": {"name": "@scope/b", "version": "3.1.4"},
                "node_modules/link": {"link": True},
                "node_modules/ohne-version": {"resolved": "file:x"},
            },
        }
        gefunden = {a.name: a.version for a in wache.parse_lockfile(json.dumps(lock))}
        self.assertEqual(gefunden, {"a": "2.0.0", "@scope/b": "3.1.4"})

    def test_kaputtes_json_ist_stoerung(self) -> None:
        with self.assertRaises(wache.Stoerung):
            wache.parse_lockfile("{", "package-lock.json")


class ParserWorkflowTest(unittest.TestCase):
    def test_sha_mit_versionskommentar(self) -> None:
        text = "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n"
        (anforderung,) = wache.parse_workflow(text)
        self.assertEqual(anforderung.oekosystem, "actions")
        self.assertEqual(anforderung.name, "actions/checkout")
        self.assertEqual(anforderung.version, "7.0.1")
        self.assertEqual(anforderung.herkunft, "action")

    def test_lokale_action_und_docker_werden_ignoriert(self) -> None:
        text = "      - uses: ./.github/actions/hugo-build\n      - uses: docker://alpine:3.20\n"
        self.assertEqual(wache.parse_workflow(text), [])

    def test_tag_referenz_ist_kein_pin(self) -> None:
        (anforderung,) = wache.parse_workflow("      - uses: owner/action@v3 # v3.1.0\n")
        self.assertEqual(anforderung.herkunft, "range")


class StrukturRegelnTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def schreibe(self, pfad: str, inhalt: str) -> None:
        ziel = self.root / pfad
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")

    def regeln(self) -> list[str]:
        return [b.regel for b in wache.pruefe_struktur(self.root)]

    def test_sauberer_baum_ist_gruen(self) -> None:
        self.schreibe("requirements-ci.in", "pillow==13.0.0\n")
        self.schreibe("requirements-ci.txt", "pillow==13.0.0 \\\n    --hash=sha256:aa\n")
        self.schreibe("requirements-werkbank.txt", "crawl4ai==0.9.5\n")
        self.schreibe("package.json", json.dumps({"devDependencies": {"x": "1.0.0"}}))
        self.schreibe(
            "package-lock.json",
            json.dumps({"lockfileVersion": 3, "packages": {"": {}, "node_modules/x": {"version": "1.0.0"}}}),
        )
        self.schreibe(
            ".github/workflows/w.yml",
            "      - uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1\n",
        )
        self.schreibe("tools/n8n/docker-compose.yml", "    image: n8nio/n8n:2.43.5\n")
        self.assertEqual(wache.pruefe_struktur(self.root), [])

    def test_a1_ungepinnte_anforderung(self) -> None:
        self.schreibe("requirements-werkbank.txt", "crawl4ai>=0.9.4\ncomposio\n")
        befunde = wache.pruefe_struktur(self.root)
        self.assertEqual([b.regel for b in befunde], [wache.REGEL_PIN, wache.REGEL_PIN])
        self.assertTrue(all(b.schwere == wache.SCHWERE_FEHLER for b in befunde))

    def test_a2_ssot_drift(self) -> None:
        self.schreibe("requirements-ci.in", "pillow==13.0.0\n")
        self.schreibe("requirements-ci.txt", "pillow==12.3.0 \\\n    --hash=sha256:aa\n")
        befunde = wache.pruefe_struktur(self.root)
        self.assertEqual([b.regel for b in befunde], [wache.REGEL_SSOT])

    def test_a2_fehlende_zeile_im_lock(self) -> None:
        self.schreibe("requirements-ci.in", "pillow==13.0.0\n")
        self.schreibe("requirements-ci.txt", "pypdf==6.21.2 \\\n    --hash=sha256:aa\n")
        befunde = wache.pruefe_struktur(self.root)
        self.assertIn(wache.REGEL_SSOT, [b.regel for b in befunde])

    def test_a3_manifest_ohne_lock(self) -> None:
        self.schreibe("cloudflare/x/package.json", json.dumps({"devDependencies": {"wrangler": "4.0.0"}}))
        befunde = wache.pruefe_struktur(self.root)
        self.assertEqual([b.regel for b in befunde], [wache.REGEL_LOCK])
        self.assertEqual(befunde[0].schwere, wache.SCHWERE_WARNUNG)

    def test_a4_action_ohne_sha_und_ohne_kommentar(self) -> None:
        self.schreibe(".github/workflows/w.yml", "      - uses: owner/action@v3\n")
        befunde = wache.pruefe_struktur(self.root)
        self.assertEqual({b.regel for b in befunde}, {wache.REGEL_AKTION})
        # beides: bewegliche Referenz (Fehler) und fehlender Kommentar (Warnung)
        self.assertEqual({b.schwere for b in befunde}, {wache.SCHWERE_FEHLER, wache.SCHWERE_WARNUNG})

    def test_a5_bewegliches_image(self) -> None:
        self.schreibe("tools/n8n/docker-compose.yml", "    image: n8nio/n8n\n")
        befunde = wache.pruefe_struktur(self.root)
        self.assertEqual([b.regel for b in befunde], [wache.REGEL_DOCKER])

    def test_a6_doppelte_version(self) -> None:
        self.schreibe("requirements-hugo.txt", "hugo==0.164.0\nhugo==0.168.0\n")
        befunde = wache.pruefe_struktur(self.root)
        self.assertEqual([b.regel for b in befunde], [wache.REGEL_MEHRFACH])


class AdHocInstallationTest(unittest.TestCase):
    """Regeln A7/A8 (WF-E813 / #972, 01.11.2026).

    Der Vorfall: `poppy-werkbank.yml`, `deploy.yml` und `social-video.yml`
    installierten neun Pakete AD HOC. Sie standen in keinem Manifest, wurden
    vom Advisory-Audit nie geprüft und von Dependabot nie aktualisiert –
    und `pypdf==6.21.2` (7× HIGH) lebte genau in so einer Installation
    weiter, während der Struktur-Lauf „0 Fehler“ meldete.
    """

    def regeln(self, text: str, regel: str) -> list[str]:
        return [b.regel for b in wache.pruefe_pip_ad_hoc(text, "w.yml", regel)]

    def test_ungepinntes_install_ist_a7(self) -> None:
        self.assertEqual(self.regeln("      - run: pip install pyyaml pypdf\n", wache.REGEL_LAUFZEIT),
                         [wache.REGEL_LAUFZEIT, wache.REGEL_LAUFZEIT])

    def test_exakter_pin_ist_zufrieden(self) -> None:
        self.assertEqual(self.regeln("      - run: pip install pyyaml==6.0.3 pypdf==6.21.4\n",
                                     wache.REGEL_LAUFZEIT), [])

    def test_bereich_und_wildcard_sind_offen(self) -> None:
        self.assertEqual(len(self.regeln("pip install 'pyyaml>=6' pillow==13.*\n", wache.REGEL_LAUFZEIT)), 2)

    def test_requirements_datei_ist_zufrieden(self) -> None:
        # A1/A2 prüfen die Pins DORT – hier darf nichts doppelt feuern.
        self.assertEqual(self.regeln("python3 -m pip install --require-hashes -r requirements-ci.txt\n",
                                     wache.REGEL_LAUFZEIT), [])

    def test_schalter_und_werkzeug_sind_keine_pakete(self) -> None:
        self.assertEqual(self.regeln(
            "pip install --upgrade pip\n"
            "pip install --index-url https://x.invalid/simple --break-system-packages pyyaml==6.0.3\n",
            wache.REGEL_LAUFZEIT), [])

    def test_prosa_und_kommentar_loesen_nicht_aus(self) -> None:
        # Ein Rat, der den Befehl ZITIERT, ist kein Aufruf. Ohne diese
        # Gegenprobe wäre die eigene Meldung des Kanals ein Struktur-Fehler.
        self.assertEqual(self.regeln(
            "  # nach pip install wieder entfernt\n"
            "                        '4. Jedes `pip install X` ohne `-r` ist ungepinnt.',\n",
            wache.REGEL_LAUFZEIT), [])

    def test_kette_mit_shell_trenner_ist_sichtbar(self) -> None:
        # Whisper-Image: `apt-get … && pip install …`. Der erste Parser
        # schnitt VOR dem Befehl ab und sah die Installation nie.
        treffer = wache.pruefe_pip_ad_hoc(
            "RUN apt-get update && pip install --no-cache-dir fastapi==1 uvicorn\n",
            "Dockerfile.x", wache.REGEL_IMAGE_PIP)
        self.assertEqual([b.regel for b in treffer], [wache.REGEL_IMAGE_PIP])
        self.assertIn("uvicorn", treffer[0].text)

    def test_mehrzeiliger_befehl_wird_zusammengefuehrt(self) -> None:
        treffer = wache.pruefe_pip_ad_hoc(
            "RUN pip install \\\n    fastapi==1 \\\n    uvicorn\n", "Dockerfile.x", wache.REGEL_IMAGE_PIP)
        self.assertEqual(len(treffer), 1)

    def test_repo_bestand_ist_gepinnt(self) -> None:
        """DAUERVERTRAG: Kein Workflow und kein Image installiert ad hoc."""
        befunde = [b for b in wache.pruefe_laufzeit_installationen(ROOT)
                   if b.schwere == wache.SCHWERE_FEHLER]
        self.assertEqual(befunde, [], f"Ad-hoc-Installationen: {[b.als_dict() for b in befunde]}")

    def test_dependabot_pflegt_die_neuen_manifeste(self) -> None:
        """Ein Pin ohne Update-Weg veraltet still."""
        text = (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
        for paket in ("pypdf", "edge-tts", "piper-tts", "trafilatura"):
            self.assertIn(f'dependency-name: "{paket}"', text)
        for datei in ("requirements-poppy.txt", "requirements-tts.txt"):
            self.assertTrue((ROOT / datei).is_file(), f"{datei} fehlt")


class AuditTest(unittest.TestCase):
    def quelle(self, daten: dict) -> wache.DateiAdvisoryQuelle:
        return wache.DateiAdvisoryQuelle(daten)

    def test_treffer_mit_fix(self) -> None:
        dep = wache.Anforderung("npm", "lodash", "4.17.15", "package-lock.json", 0, "lock")
        daten = {"npm:lodash@4.17.15": [{"ghsa": "GHSA-x", "severity": "high", "summary": "Test", "fixed": "4.17.21"}]}
        bilanz = wache.auditiere([dep], self.quelle(daten))
        self.assertEqual(len(bilanz.treffer), 1)
        treffer = bilanz.treffer[0]
        self.assertEqual((treffer.name, treffer.version, treffer.ghsa, treffer.fix), ("lodash", "4.17.15", "GHSA-x", "4.17.21"))
        self.assertEqual(treffer.quellen, ("package-lock.json",))

    def test_leere_quelle_ist_sauber(self) -> None:
        dep = wache.Anforderung("npm", "lodash", "4.17.15", "package-lock.json", 0, "lock")
        bilanz = wache.auditiere([dep], self.quelle({}))
        self.assertEqual((bilanz.geprueft, bilanz.treffer), (1, []))

    def test_bereich_wird_nicht_auditiert(self) -> None:
        dep = wache.Anforderung("pip", "crawl4ai", "0.9.4", "requirements.txt", 1, "range")
        bilanz = wache.auditiere([dep], self.quelle({}))
        self.assertEqual(bilanz.geprueft, 0)

    def test_dedupe_mehrerer_quellen(self) -> None:
        a = wache.Anforderung("npm", "ws", "7.5.13", "package-lock.json", 0, "lock")
        b = wache.Anforderung("npm", "ws", "7.5.13", "tools/x/package-lock.json", 0, "lock")
        daten = {"npm:ws@7.5.13": [{"ghsa": "GHSA-y", "severity": "high", "summary": "Test"}]}
        bilanz = wache.auditiere([a, b], self.quelle(daten))
        self.assertEqual(bilanz.geprueft, 1)
        self.assertEqual(set(bilanz.treffer[0].quellen), {"package-lock.json", "tools/x/package-lock.json"})

    def test_budget_ist_stoerung(self) -> None:
        a = wache.Anforderung("npm", "a", "1.0.0", "x", 0, "lock")
        b = wache.Anforderung("npm", "b", "1.0.0", "x", 0, "lock")
        with self.assertRaises(wache.Stoerung):
            wache.auditiere([a, b], self.quelle({}), max_abfragen=1)

    def test_api_dialekt_wird_normalisiert(self) -> None:
        roh = {
            "ghsa_id": "GHSA-z",
            "severity": "critical",
            "summary": "Test",
            "vulnerabilities": [
                {"package": {"name": "x"}, "first_patched_version": {"identifier": "2.0.0"}}
            ],
        }
        normal = wache._normalisiere(roh)
        self.assertEqual(normal, {"ghsa": "GHSA-z", "severity": "critical", "summary": "Test", "fixed": "2.0.0"})

    def test_ohne_fix_bleibt_der_befund_stehen(self) -> None:
        roh = {"ghsa_id": "GHSA-n", "severity": "medium", "summary": "kein fix", "vulnerabilities": []}
        self.assertEqual(wache._normalisiere(roh)["fixed"], "")


class HauptprogrammTest(unittest.TestCase):
    def test_selftest_gruen(self) -> None:
        self.assertEqual(wache.main(["--selftest"]), 0)

    def test_check_auf_repo_ist_gruen(self) -> None:
        """DAUERVERTRAG: Der ausgelieferte Bestand hat keine Struktur-Fehler."""
        befunde = wache.pruefe_struktur(ROOT)
        fehler = [b for b in befunde if b.schwere == wache.SCHWERE_FEHLER]
        self.assertEqual(fehler, [], f"Struktur-Fehler: {[b.als_dict() for b in fehler]}")

    def test_check_auf_vergiftetem_baum_exit_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "requirements-x.txt").write_text("pyyaml>=6.0\n", encoding="utf-8")
            self.assertEqual(wache.main(["--check", "--root", tmp]), 1)

    def test_audit_mit_dateiquelle_exit_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package-lock.json").write_text(
                json.dumps({"lockfileVersion": 3, "packages": {"node_modules/x": {"version": "1.0.0"}}}),
                encoding="utf-8",
            )
            quelle = root / "advisories.json"
            quelle.write_text(
                json.dumps({"npm:x@1.0.0": [{"ghsa": "GHSA-q", "severity": "high", "summary": "Test"}]}),
                encoding="utf-8",
            )
            self.assertEqual(
                wache.main(["--audit", "--root", tmp, "--advisory-datei", str(quelle)]), 1
            )

    def test_audit_ohne_treffer_exit_0(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package-lock.json").write_text(
                json.dumps({"lockfileVersion": 3, "packages": {"node_modules/x": {"version": "1.0.1"}}}),
                encoding="utf-8",
            )
            quelle = root / "advisories.json"
            quelle.write_text(json.dumps({}), encoding="utf-8")
            self.assertEqual(
                wache.main(["--audit", "--root", tmp, "--advisory-datei", str(quelle)]), 0
            )

    def test_audit_ohne_quelle_exit_2(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "package-lock.json").write_text(
                json.dumps({"lockfileVersion": 3, "packages": {"node_modules/x": {"version": "1.0.0"}}}),
                encoding="utf-8",
            )
            import os

            alte = {k: os.environ.pop(k, None) for k in ("GITHUB_TOKEN", "GH_TOKEN")}
            try:
                self.assertEqual(wache.main(["--audit", "--root", tmp]), 2)
            finally:
                for k, v in alte.items():
                    if v is not None:
                        os.environ[k] = v


class WorkflowVertragTest(unittest.TestCase):
    """Die Wache ist nur eine Wache, wenn sie läuft."""

    def test_sicherheits_wache_ruft_die_wache_auf(self) -> None:
        text = (ROOT / ".github/workflows/sicherheits-wache.yml").read_text(encoding="utf-8")
        self.assertIn("scripts/abhaengigkeits_wache.py --selftest", text)
        self.assertIn("scripts/abhaengigkeits_wache.py --check", text)
        self.assertIn("scripts/abhaengigkeits_wache.py --audit", text)

    def test_paket_skripte_existieren(self) -> None:
        paket = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        for name in ("deps:check", "deps:audit", "test:deps"):
            self.assertIn(name, paket["scripts"])


if __name__ == "__main__":  # pragma: no cover
    unittest.main(verbosity=2)
