#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Vertragstests der Abhängigkeits-Selbstheilung (Dependabot-Alert #79, 10.11.2026).

Sichert alle fünf Schichten offline im temporären Verzeichnis (C15/C27 – kein
Schreibzugriff auf das echte Repository während der Testsuite):
  1. Schutz-Vertrag (`data/abhaengigkeits_schutz_vertrag.json`) inkl. A9-Boden
  2. Eichprobe (Exit 3 `MESSGERAET` bei blindem Prüfer)
  3. Monotone Heilung (`--ignore-scripts`, `overrides`, pip-Hash-Sync, Rollback)
  4. Verkettete SHA-256-Belegkette (`data/abhaengigkeits_schutz_belege.jsonl`)
  5. Verdrahtungs-Wache (`--wache`), PR-Audit-Bedarfsfilter und H-02-Grenze
"""
from __future__ import annotations

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from typing import Dict, List, Tuple

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))

import abhaengigkeits_selbstheilung as heiler  # noqa: E402
import abhaengigkeits_wache as wache  # noqa: E402


def _gueltiger_vertrag() -> Dict[str, object]:
    return {
        "schema": 1,
        "nur_verschaerfen": True,
        "ignore_scripts_pflicht": True,
        "erlaubte_npm_hosts": ["registry.npmjs.org"],
        "heil_branch_praefix": "automation/deps-heilung-",
        "ledger": heiler.LEDGER_PFAD,
        "mindestversionen": {
            "npm:minimatch": {
                "ab": "11.0.1",
                "ghsa": ["GHSA-g3hv-75wg-m249"],
                "seit": "2026-11-10",
                "grund": "Dependabot Alert #79 globparts DoS",
            },
            "npm:glob": {
                "ab": "14.0.2",
                "ghsa": ["GHSA-3g3m-2fjr-6pw4"],
                "seit": "2026-11-10",
                "grund": "Glob AbortSignal cancellation bypass",
            },
        },
        "begruendung": "Testvertrag für Vorfall #79 und GHSA-3g3m-2fjr-6pw4 mit Offline-Boden A9.",
    }


def _baue_baum(wurzel: Path, *, mit_vorboden: bool = False) -> None:
    (wurzel / "data").mkdir(parents=True, exist_ok=True)
    vertrag = _gueltiger_vertrag()
    if not mit_vorboden:
        vertrag["mindestversionen"] = {}
    heiler._schreibe_json_sauber(wurzel / heiler.VERTRAG_PFAD, vertrag)
    (wurzel / heiler.LEDGER_PFAD).write_text("", encoding="utf-8")
    heiler._schreibe_json_sauber(
        wurzel / "package.json",
        {"name": "probe", "version": "1.0.0", "devDependencies": {"lighthouse": "13.6.0"}},
    )
    heiler._schreibe_json_sauber(
        wurzel / "package-lock.json",
        {
            "lockfileVersion": 3,
            "packages": {
                "": {"name": "probe", "version": "1.0.0", "devDependencies": {"lighthouse": "13.6.0"}},
                "node_modules/lighthouse": {
                    "version": "13.6.0",
                    "resolved": "https://registry.npmjs.org/lighthouse/-/lighthouse-13.6.0.tgz",
                    "integrity": "sha512-lh",
                },
                "node_modules/glob": {
                    "version": "13.0.6",
                    "resolved": "https://registry.npmjs.org/glob/-/glob-13.0.6.tgz",
                    "integrity": "sha512-g13",
                },
                "node_modules/minimatch": {
                    "version": "10.2.6",
                    "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-10.2.6.tgz",
                    "integrity": "sha512-m10",
                },
            },
        },
    )


class VertragTest(unittest.TestCase):
    def test_echter_repo_vertrag_erfuellt_pflichtboden_79(self) -> None:
        vertrag = heiler.lade_vertrag(ROOT, mindest_pflicht=True)
        self.assertTrue(vertrag["nur_verschaerfen"])
        self.assertTrue(vertrag["ignore_scripts_pflicht"])
        mindest = vertrag["mindestversionen"]
        self.assertIsInstance(mindest, dict)
        self.assertIn("npm:minimatch", mindest)
        self.assertIn("npm:glob", mindest)

    def test_nur_verschaerfen_darf_nicht_abgeschaltet_werden(self) -> None:
        daten = _gueltiger_vertrag()
        daten["nur_verschaerfen"] = False
        self.assertTrue(any("nur_verschaerfen" in f for f in heiler.vertrag_fehler(daten)))

    def test_ignore_scripts_pflicht_darf_nicht_fehlen(self) -> None:
        daten = _gueltiger_vertrag()
        daten["ignore_scripts_pflicht"] = False
        self.assertTrue(any("ignore_scripts_pflicht" in f for f in heiler.vertrag_fehler(daten)))

    def test_unbekannter_schluessel_wird_abgelehnt(self) -> None:
        daten = _gueltiger_vertrag()
        daten["hintertuer"] = True
        self.assertTrue(any("Unbekannte Schlüssel" in f for f in heiler.vertrag_fehler(daten)))

    def test_pflichtboden_erkennt_fehlendes_minimatch_79(self) -> None:
        daten = _gueltiger_vertrag()
        daten["mindestversionen"] = {}
        fehler = heiler.vertrag_fehler(daten, mindest_pflicht=True)
        self.assertTrue(any("Alert #79" in f for f in fehler), fehler)

    def test_doppelter_json_schluessel_im_vertrag_ist_nicht_belegbar(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            (baum / "data").mkdir(parents=True)
            (baum / heiler.VERTRAG_PFAD).write_text(
                '{"schema": 1, "schema": 1}', encoding="utf-8"
            )
            with self.assertRaises(heiler.NichtBelegbar):
                heiler.lade_vertrag(baum)


class EichprobeTest(unittest.TestCase):
    def test_eichprobe_gruen(self) -> None:
        heiler.eichprobe()

    def test_kaputte_eichprobe_liefert_exit_3_ohne_schreibzugriff(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            _baue_baum(baum)
            vorher_lock = (baum / "package-lock.json").read_bytes()
            erg = heiler.ausfuehren(
                baum,
                heilen=True,
                advisory_quelle=wache.DateiAdvisoryQuelle({}),
                eichprobe_fn=lambda: (_ for _ in ()).throw(heiler.MessgeraetDefekt("blind")),
            )
            self.assertEqual(erg.code, 3)
            self.assertEqual(erg.klasse, heiler.KLASSE_MESSGERAET)
            self.assertEqual((baum / "package-lock.json").read_bytes(), vorher_lock)
            self.assertEqual((baum / heiler.LEDGER_PFAD).read_text(encoding="utf-8"), "")


class BelegketteTest(unittest.TestCase):
    def test_echte_belegkette_im_repo_ist_intakt_und_belegt_79(self) -> None:
        kette = heiler.pruefe_belegkette(ROOT / heiler.LEDGER_PFAD)
        self.assertGreaterEqual(len(kette), 1)
        erster = kette[0]
        self.assertEqual(erster["seq"], 1)
        self.assertEqual(erster["prev_sha256"], heiler.GENESIS)
        self.assertIn("GHSA-g3hv-75wg-m249", erster["geheilte_ghsa"])

    def test_verkettung_ueber_mehrere_eintraege_und_manipulationsschutz(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            pfad = Path(tmp) / "belege.jsonl"
            pfad.write_text("", encoding="utf-8")
            bild_v = heiler.Messbild(10, [], [], [])
            bild_n = heiler.Messbild(10, [], [], [])
            e1 = heiler.haenge_beleg_an(
                pfad,
                klasse="GEHEILT",
                befund_id="id1",
                vorher=bild_v,
                nachher=bild_n,
                geheilte_ghsa=["GHSA-g3hv-75wg-m249"],
                schritte=["Schritt 1"],
                install_skript_pakete=[],
                gruende=["Grund 1"],
            )
            e2 = heiler.haenge_beleg_an(
                pfad,
                klasse="GEHEILT",
                befund_id="id2",
                vorher=bild_v,
                nachher=bild_n,
                geheilte_ghsa=["GHSA-3g3m-2fjr-6pw4"],
                schritte=["Schritt 2"],
                install_skript_pakete=[],
                gruende=["Grund 2"],
            )
            self.assertEqual(e2["prev_sha256"], e1["sha256"])
            self.assertEqual(len(heiler.pruefe_belegkette(pfad)), 2)

            # Manipulation eines Zeichens bricht die Kette sofort.
            kaputt = pfad.read_text(encoding="utf-8").replace("Schritt 1", "Schritt X")
            pfad.write_text(kaputt, encoding="utf-8")
            with self.assertRaises(heiler.KetteKaputt):
                heiler.pruefe_belegkette(pfad)

    def test_token_und_fremdlinks_werden_vor_beleg_maskiert(self) -> None:
        roh = "Fehler bei https://evil.example/a mit Bearer ghp_1234567890abcdef"
        gesaeubert = heiler._saeubere_text(roh)
        self.assertNotIn("ghp_1234567890abcdef", gesaeubert)
        self.assertNotIn("https://evil.example", gesaeubert)


class HeilungTest(unittest.TestCase):
    def _quelle_79(self) -> wache.DateiAdvisoryQuelle:
        return wache.DateiAdvisoryQuelle(
            {
                "npm:minimatch@10.2.6": [
                    {
                        "ghsa": "GHSA-g3hv-75wg-m249",
                        "severity": "medium",
                        "summary": "minimatch globparts amplification DoS (#79)",
                        "fixed": "11.0.1",
                    }
                ],
                "npm:glob@13.0.6": [
                    {
                        "ghsa": "GHSA-3g3m-2fjr-6pw4",
                        "severity": "medium",
                        "summary": "Glob AbortSignal bypass",
                        "fixed": "14.0.2",
                    }
                ],
            }
        )

    def test_vollheilung_vorfall_79_und_idempotenz(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            _baue_baum(baum)

            def fake_npm(cwd: Path, args: List[str]) -> Tuple[int, str]:
                lock_p = cwd / "package-lock.json"
                daten = json.loads(lock_p.read_text(encoding="utf-8"))
                daten["packages"]["node_modules/glob"] = {
                    "version": "14.0.4",
                    "resolved": "https://registry.npmjs.org/glob/-/glob-14.0.4.tgz",
                    "integrity": "sha512-g14",
                }
                daten["packages"]["node_modules/minimatch"] = {
                    "version": "11.0.6",
                    "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-11.0.6.tgz",
                    "integrity": "sha512-m11",
                }
                heiler._schreibe_json_sauber(lock_p, daten)
                return 0, "ok"

            erg = heiler.ausfuehren(
                baum, heilen=True, advisory_quelle=self._quelle_79(), npm_runner=fake_npm
            )
            self.assertEqual((erg.klasse, erg.code), (heiler.KLASSE_GEHEILT, 0))
            self.assertEqual(
                erg.geheilte_ghsa, ["GHSA-3g3m-2fjr-6pw4", "GHSA-g3hv-75wg-m249"]
            )
            manifest = json.loads((baum / "package.json").read_text(encoding="utf-8"))
            self.assertEqual(
                manifest["overrides"], {"glob": ">=14.0.2", "minimatch": ">=11.0.1"}
            )
            vertrag = heiler.lade_vertrag(baum, mindest_pflicht=True)
            self.assertEqual(vertrag["mindestversionen"]["npm:minimatch"]["ab"], "11.0.1")  # type: ignore[index]

            # Zweiter Lauf ändert nichts und hängt keine Uhrzeit-Zeile an.
            erg2 = heiler.ausfuehren(
                baum, heilen=True, advisory_quelle=self._quelle_79(), npm_runner=fake_npm
            )
            self.assertEqual((erg2.klasse, erg2.code), (heiler.KLASSE_SICHER, 0))
            self.assertEqual(erg2.geaenderte_dateien, [])
            self.assertEqual(len(heiler.pruefe_belegkette(baum / heiler.LEDGER_PFAD)), 1)

    def test_blockierender_eltern_range_erzwingt_override_nachzug(self) -> None:
        """Auch bei einem Minor-Fix eskaliert der Heiler auf `overrides`, wenn `npm update` hängt."""
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            _baue_baum(baum)
            quelle = wache.DateiAdvisoryQuelle(
                {
                    "npm:minimatch@10.2.6": [
                        {
                            "ghsa": "GHSA-aaaa-bbbb-1111",
                            "severity": "medium",
                            "summary": "Minor-Fix-Blockade",
                            "fixed": "10.2.8",
                        }
                    ]
                }
            )
            aufrufe: List[List[str]] = []

            def sturer_npm(cwd: Path, args: List[str]) -> Tuple[int, str]:
                aufrufe.append(list(args))
                # Erst `npm install` (nach Override-Nachzug) hebt die Version an.
                if args and args[0] == "install":
                    lock_p = cwd / "package-lock.json"
                    daten = json.loads(lock_p.read_text(encoding="utf-8"))
                    daten["packages"]["node_modules/minimatch"] = {
                        "version": "10.2.8",
                        "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-10.2.8.tgz",
                        "integrity": "sha512-m1028",
                    }
                    heiler._schreibe_json_sauber(lock_p, daten)
                return 0, "ok"

            erg = heiler.ausfuehren(baum, heilen=True, advisory_quelle=quelle, npm_runner=sturer_npm)
            self.assertEqual((erg.klasse, erg.code), (heiler.KLASSE_GEHEILT, 0))
            self.assertEqual([a[0] for a in aufrufe], ["update", "install"])

    def test_fremder_registry_host_oder_fehlende_integrity_rollt_zurueck(self) -> None:
        for defekt in ("fremder_host", "keine_integrity"):
            with self.subTest(defekt=defekt), tempfile.TemporaryDirectory() as tmp:
                baum = Path(tmp)
                _baue_baum(baum)
                alt_lock = (baum / "package-lock.json").read_bytes()
                alt_pkg = (baum / "package.json").read_bytes()

                def manipulierter_npm(cwd: Path, args: List[str]) -> Tuple[int, str]:
                    lock_p = cwd / "package-lock.json"
                    daten = json.loads(lock_p.read_text(encoding="utf-8"))
                    eintrag = {
                        "version": "11.0.6",
                        "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-11.0.6.tgz",
                        "integrity": "sha512-ok",
                    }
                    if defekt == "fremder_host":
                        eintrag["resolved"] = "https://evil-npmjs.org/minimatch-11.0.6.tgz"
                    else:
                        eintrag["integrity"] = ""
                    daten["packages"]["node_modules/minimatch"] = eintrag
                    daten["packages"]["node_modules/glob"]["version"] = "14.0.4"
                    daten["packages"]["node_modules/glob"]["integrity"] = "sha512-ok"
                    heiler._schreibe_json_sauber(lock_p, daten)
                    return 0, "ok"

                erg = heiler.ausfuehren(
                    baum,
                    heilen=True,
                    advisory_quelle=self._quelle_79(),
                    npm_runner=manipulierter_npm,
                )
                self.assertEqual((erg.klasse, erg.code), (heiler.KLASSE_VERSCHLECHTERUNG, 2))
                self.assertEqual((baum / "package-lock.json").read_bytes(), alt_lock)
                self.assertEqual((baum / "package.json").read_bytes(), alt_pkg)

    def test_install_skript_wird_ausgewiesen_ohne_ausfuehrung(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            _baue_baum(baum)

            def skript_npm(cwd: Path, args: List[str]) -> Tuple[int, str]:
                lock_p = cwd / "package-lock.json"
                daten = json.loads(lock_p.read_text(encoding="utf-8"))
                daten["packages"]["node_modules/glob"] = {
                    "version": "14.0.4",
                    "resolved": "https://registry.npmjs.org/glob/-/glob-14.0.4.tgz",
                    "integrity": "sha512-g14",
                }
                daten["packages"]["node_modules/minimatch"] = {
                    "version": "11.0.6",
                    "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-11.0.6.tgz",
                    "integrity": "sha512-m11",
                    "hasInstallScript": True,
                }
                heiler._schreibe_json_sauber(lock_p, daten)
                return 0, "ok"

            erg = heiler.ausfuehren(
                baum, heilen=True, advisory_quelle=self._quelle_79(), npm_runner=skript_npm
            )
            self.assertEqual(erg.klasse, heiler.KLASSE_GEHEILT)
            self.assertEqual(erg.install_skript_pakete, ["minimatch@11.0.6"])
            self.assertIn("minimatch@11.0.6", heiler.bericht_markdown(erg))

    def test_neue_schwachstelle_in_nachmessung_loest_rollback_aus(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            _baue_baum(baum)
            alt_lock = (baum / "package-lock.json").read_bytes()
            quelle = wache.DateiAdvisoryQuelle(
                {
                    "npm:minimatch@10.2.6": [
                        {
                            "ghsa": "GHSA-g3hv-75wg-m249",
                            "severity": "medium",
                            "summary": "Alt",
                            "fixed": "11.0.1",
                        }
                    ],
                    "npm:minimatch@11.0.1": [
                        {
                            "ghsa": "GHSA-9999-8888-7777",
                            "severity": "high",
                            "summary": "Regressions-CVE",
                            "fixed": "11.0.2",
                        }
                    ],
                }
            )

            def regression_npm(cwd: Path, args: List[str]) -> Tuple[int, str]:
                lock_p = cwd / "package-lock.json"
                daten = json.loads(lock_p.read_text(encoding="utf-8"))
                daten["packages"]["node_modules/minimatch"] = {
                    "version": "11.0.1",
                    "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-11.0.1.tgz",
                    "integrity": "sha512-m1101",
                }
                heiler._schreibe_json_sauber(lock_p, daten)
                return 0, "ok"

            erg = heiler.ausfuehren(
                baum, heilen=True, advisory_quelle=quelle, npm_runner=regression_npm
            )
            self.assertEqual((erg.klasse, erg.code), (heiler.KLASSE_VERSCHLECHTERUNG, 2))
            self.assertEqual((baum / "package-lock.json").read_bytes(), alt_lock)

    def test_teilheilung_bleibt_ehrlich_offen_mit_exit_1(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            _baue_baum(baum)
            quelle = wache.DateiAdvisoryQuelle(
                {
                    "npm:minimatch@10.2.6": [
                        {
                            "ghsa": "GHSA-g3hv-75wg-m249",
                            "severity": "medium",
                            "summary": "Mit Fix",
                            "fixed": "11.0.1",
                        }
                    ],
                    "npm:glob@13.0.6": [
                        {
                            "ghsa": "GHSA-0000-0000-0001",
                            "severity": "high",
                            "summary": "Noch kein Upstream-Fix",
                        }
                    ],
                }
            )

            def teil_npm(cwd: Path, args: List[str]) -> Tuple[int, str]:
                lock_p = cwd / "package-lock.json"
                daten = json.loads(lock_p.read_text(encoding="utf-8"))
                daten["packages"]["node_modules/minimatch"] = {
                    "version": "11.0.6",
                    "resolved": "https://registry.npmjs.org/minimatch/-/minimatch-11.0.6.tgz",
                    "integrity": "sha512-m11",
                }
                heiler._schreibe_json_sauber(lock_p, daten)
                return 0, "ok"

            erg = heiler.ausfuehren(baum, heilen=True, advisory_quelle=quelle, npm_runner=teil_npm)
            # C33: Teilheilung wird persistiert, liefert aber NIEMALS Exit 0!
            self.assertEqual((erg.klasse, erg.code), (heiler.KLASSE_OFFEN, 1))
            self.assertEqual(erg.geheilte_ghsa, ["GHSA-g3hv-75wg-m249"])
            self.assertEqual(len(heiler.pruefe_belegkette(baum / heiler.LEDGER_PFAD)), 1)

    def test_downgrade_fix_wird_verweigert(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            _baue_baum(baum)
            quelle = wache.DateiAdvisoryQuelle(
                {
                    "npm:minimatch@10.2.6": [
                        {
                            "ghsa": "GHSA-1111-2222-3333",
                            "severity": "medium",
                            "summary": "Falscher Alt-Zweig",
                            "fixed": "3.1.3",
                        }
                    ]
                }
            )
            erg = heiler.ausfuehren(baum, heilen=True, advisory_quelle=quelle)
            self.assertEqual((erg.klasse, erg.code), (heiler.KLASSE_OFFEN, 1))

    def test_pip_heilung_haelt_quelle_und_hash_lock_synchron(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            _baue_baum(baum)
            (baum / "requirements-ci.in").write_text("Pillow==12.3.0\n", encoding="utf-8")
            (baum / "requirements-ci.txt").write_text(
                "Pillow==12.3.0 \\\n    --hash=sha256:alt1 \\\n    --hash=sha256:alt2\n",
                encoding="utf-8",
            )
            quelle = wache.DateiAdvisoryQuelle(
                {
                    "pip:pillow@12.3.0": [
                        {
                            "ghsa": "GHSA-2222-3333-4444",
                            "severity": "high",
                            "summary": "Pillow Fix",
                            "fixed": "13.0.0",
                        }
                    ]
                }
            )
            erg = heiler.ausfuehren(
                baum,
                heilen=True,
                advisory_quelle=quelle,
                pip_hash_aufloeser=lambda p, v: ["sha256:" + "c" * 64, "sha256:" + "d" * 64],
            )
            self.assertEqual((erg.klasse, erg.code), (heiler.KLASSE_GEHEILT, 0))
            self.assertIn("Pillow==13.0.0", (baum / "requirements-ci.in").read_text(encoding="utf-8"))
            self.assertIn("sha256:" + "c" * 64, (baum / "requirements-ci.txt").read_text(encoding="utf-8"))
            self.assertEqual(wache.pruefe_struktur(baum), [])


class VerdrahtungUndDiffTest(unittest.TestCase):
    def test_echte_verdrahtung_im_repo_ist_gruen(self) -> None:
        self.assertEqual(heiler.pruefe_verdrahtung(ROOT), [])

    def test_verdrahtung_erkennt_sabotage_an_gitattributes_und_h02(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            baum = Path(tmp)
            for rel in heiler.PFLICHT_PFADE:
                ziel = baum / rel
                ziel.parent.mkdir(parents=True, exist_ok=True)
                ziel.write_bytes((ROOT / rel).read_bytes())

            self.assertEqual(heiler.pruefe_verdrahtung(baum), [])

            # Sabotage 1: merge=binary entfernt
            (baum / heiler.GITATTRIBUTES_PFAD).write_text("*.jsonl merge=union\n", encoding="utf-8")
            self.assertTrue(
                any("merge=binary" in f for f in heiler.pruefe_verdrahtung(baum))
            )

            # Wiederherstellen + Sabotage 2: verbotenes `gh pr merge` (Audit H-02)
            (baum / heiler.GITATTRIBUTES_PFAD).write_bytes(
                (ROOT / heiler.GITATTRIBUTES_PFAD).read_bytes()
            )
            wf = (baum / heiler.ARBEITSFLUSS).read_text(encoding="utf-8") + "\n      - run: gh pr merge 1\n"
            (baum / heiler.ARBEITSFLUSS).write_text(wf, encoding="utf-8")
            self.assertTrue(
                any("Audit H-02" in f for f in heiler.pruefe_verdrahtung(baum))
            )

    def test_audit_bedarf_filtert_inhalts_commits_und_schuetzt_paket_prs(self) -> None:
        for pfad in (
            "package-lock.json",
            "tools/mcp/package.json",
            "requirements-ci.txt",
            "requirements-poppy.txt",
            ".github/dependabot.yml",
            ".github/workflows/deploy.yml",
            "data/abhaengigkeits_schutz_vertrag.json",
        ):
            with self.subTest(pfad=pfad):
                bedarf, _ = heiler.pruefe_audit_bedarf(
                    ROOT, event_name="pull_request", geaenderte_dateien=[pfad]
                )
                self.assertTrue(bedarf)

        bedarf_inhalt, _ = heiler.pruefe_audit_bedarf(
            ROOT,
            event_name="push",
            geaenderte_dateien=["content/posts/2026-11-10-test/index.md", "layouts/index.html"],
        )
        self.assertFalse(bedarf_inhalt)

    def test_cli_selftest_und_wache_liefern_exit_0(self) -> None:
        puffer = io.StringIO()
        with redirect_stdout(puffer), redirect_stderr(puffer):
            self.assertEqual(heiler.main(["--selftest"]), 0)
            self.assertEqual(heiler.main(["--wache"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
