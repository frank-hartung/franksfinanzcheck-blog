#!/usr/bin/env python3
"""Regressionstests für die Ledger-Isolation (C27, Nebenbefund zu #610).

DER VORFALL (07.10.2026)
------------------------
Drei Unit-Tests schrieben echte Zeilen in `data/audit/*.jsonl` – ein
versioniertes, append-only bewachtes Beweis-Ledger (history_guard H6).
Am teuersten war der gate-Entscheid für den Fixture-Artikel
`2026-09-07-r5-live`, committet am 03.10.2026: Das Buch behauptete einen
am Gate verworfenen Live-Artikel, den es nie gab.

DIE DREI PFADE
--------------
1. test_affiliate_intent_guard.test_bestand_gate_checks_intent_dimension
     → bestand_gate.run_gate() → publish_gate.affiliate_profi_failures()
     → SUBPROZESS `affiliate_profi_check.py --json` → log_event()
2. test_clear_text_logging_security
     .test_secrets_age_guard_record_success_and_list_are_clean
     → secrets_age_guard._record_success() → log_event()
3. test_publication_reliability.test_publish_gate_heilt_r5_vor_der_harten_pruefung
     → publish_gate.main() mit DRY_RUN=False → log_event(action="gate")

Warum diese Datei nötig ist, obwohl die drei Tests geheilt sind: Drei
geheilte Stellen sind eine Absichtserklärung. Bewacht ist sie erst, wenn
(a) der Vertrag des Engpasses selbst geprüft ist – auch über Prozessgrenzen,
(b) die bekannte Leckstelle nachweislich eingesperrt bleibt und
(c) ein künftiger Test, der dieselben Einstiege ohne Sandbox aufruft,
    ROT wird, statt stillschweigend weiter zu fabrizieren.

Laufbar über die Repo-Konvention (kein pytest nötig):
    python3 -m unittest discover -s scripts/tests
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[2]
SCRIPTS = ROOT / "scripts"
TESTS = SCRIPTS / "tests"
sys.path.insert(0, str(SCRIPTS))

import audit_log  # noqa: E402
import repo_isolation as iso  # noqa: E402

LEDGER = ROOT / "data" / "audit"
#: Name aus dem Modul, nicht abgeschrieben – ein Umbenennen im Engpass
#: schlägt sonst hier nicht durch.
OFF_ENV = audit_log.AUDIT_OFF_ENV

#: Einstiege, die `log_event()` erreichen und deshalb in Tests nur in der
#: Sandbox aufgerufen werden dürfen – als (Modul, Funktion), NICHT als bloßer
#: Funktionsname. Bewusst eine ausdrücklich gepflegte Liste (Vorbild:
#: HEILER_NACKT/KETTEN_LEITER in governance_contract C15); sie ist Ergebnis
#: einer empirischen Erhebung vom 07.10.2026, bei der jeder Audit-Eintrag
#: eines Suite-Laufs seinem Test zugeordnet wurde.
#:
#: Der Modul-Bezug ist Pflicht: `pg` heißt in test_publication_reliability.py
#: `publish_gate`, in test_ruleset_restoration.py aber `pflichtcheck_guard`.
#: Eine Regel über Alias-Namen meldete Letzteres fälschlich als Leck.
LEDGER_EINSTIEGE = {
    ("bestand_gate", "run_gate"),          # → publish_gate → Subprozess
    ("secrets_age_guard", "_record_success"),
    ("audit_log", "log_event"),
    ("publish_gate", "main"),
}

#: Als isoliert gilt ein Test, der die Sandbox nutzt …
ISOLATIONS_BAUSTEINE = {"beweis_ledger_unangetastet", "ledger_sandbox"}
#: … oder `log_event` patcht. Das ist das ältere Muster im Haus
#: (test_editorial_review_gate, test_publication_release_wache,
#: publication_release.selftest) und bleibt gültig.
PATCH_ZIEL = "log_event"


# --------------------------------------------------------------------- #
# 1) Der Vertrag des Engpasses
# --------------------------------------------------------------------- #
class VertragDesEngpasses(unittest.TestCase):
    """`audit_log` muss die Isolation tragen – auch über Prozessgrenzen.

    Der entscheidende Punkt: Leckstelle 1 entsteht in einem KINDPROZESS.
    Ein Monkeypatch im Testprozess erreicht das Kind nicht, eine
    Umgebungsvariable erbt sich hinein. Genau das wird hier bewiesen.
    """

    def setUp(self):
        self.alt = {name: os.environ.get(name)
                    for name in (audit_log.AUDIT_DIR_ENV, OFF_ENV)}
        self.tmp = tempfile.TemporaryDirectory(prefix="c27-vertrag-")
        self.addCleanup(self.tmp.cleanup)

    def tearDown(self):
        for name, wert in self.alt.items():
            if wert is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = wert

    def test_normalfall_zeigt_auf_das_echte_ledger(self):
        """Schein-Sicherheits-Probe: Ohne Schalter MUSS das Ledger scharf sein.

        Eine Isolation, die das Protokollieren im Betrieb abschaltet, wäre
        schlimmer als der ursprüngliche Fehler – sie würde Beweise vernichten
        statt zu fabrizieren. Deshalb wird die Gegenrichtung geprüft, ohne
        selbst zu schreiben.
        """
        os.environ.pop(audit_log.AUDIT_DIR_ENV, None)
        os.environ.pop(OFF_ENV, None)
        self.assertEqual(Path(audit_log.AUDIT_DIR), LEDGER,
                         "audit_log.AUDIT_DIR zeigt nicht auf data/audit")
        self.assertEqual(Path(audit_log.audit_verzeichnis()),
                         Path(audit_log.AUDIT_DIR))
        self.assertFalse(audit_log.audit_abgeschaltet())

    def test_umlenkung_gilt_im_eigenen_prozess(self):
        os.environ[audit_log.AUDIT_DIR_ENV] = self.tmp.name
        pfad = audit_log.log_event(module="c27_probe", action="im_prozess")
        self.assertIsNotNone(pfad)
        self.assertEqual(Path(pfad).parent, Path(self.tmp.name))
        self.assertEqual([z["module"] for z in iso.lese_zeilen(pfad)], ["c27_probe"])

    def test_umlenkung_erbt_sich_in_den_subprozess(self):
        """Kern der Heilung: Das Kind schreibt in die Sandbox, nicht ins Buch."""
        vorher = iso.fingerabdruck()
        os.environ[audit_log.AUDIT_DIR_ENV] = self.tmp.name
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "audit_log.py"), "--event",
             json.dumps({"module": "c27_kind", "action": "subprozess"})],
            capture_output=True, text=True, cwd=ROOT, timeout=120)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn(self.tmp.name, proc.stdout,
                      "der Kindprozess schrieb nicht in die umgelenkte Sandbox")
        self.assertEqual([], iso.ledger_abweichung(vorher),
                         "der Kindprozess hat das echte data/audit/ angetastet")
        self.assertEqual([z["module"] for z in iso.sandbox_zeilen(self.tmp.name)],
                         ["c27_kind"])

    def test_stummschaltung_ist_harter_no_op(self):
        vorher = iso.fingerabdruck()
        os.environ[audit_log.AUDIT_DIR_ENV] = self.tmp.name
        os.environ[OFF_ENV] = "1"
        self.assertTrue(audit_log.audit_abgeschaltet())
        self.assertIsNone(audit_log.log_event(module="c27_probe", action="stumm"))
        self.assertEqual([], list(Path(self.tmp.name).glob("*.jsonl")),
                         f"{OFF_ENV} legte trotzdem eine Datei an")
        self.assertEqual([], iso.ledger_abweichung(vorher))

    def test_stummschaltung_erbt_sich_in_den_subprozess(self):
        vorher = iso.fingerabdruck()
        os.environ[OFF_ENV] = "1"
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS / "audit_log.py"), "--event",
             json.dumps({"module": "c27_kind", "action": "stumm"})],
            capture_output=True, text=True, cwd=ROOT, timeout=120)
        self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)
        self.assertIn("stumm", proc.stdout,
                      "der Kindprozess meldet die Stummschaltung nicht")
        self.assertEqual([], iso.ledger_abweichung(vorher))

    def test_leser_folgen_der_umlenkung(self):
        """Ein umgelenkter Lauf darf nicht das echte Buch lesen."""
        os.environ[audit_log.AUDIT_DIR_ENV] = self.tmp.name
        audit_log.log_event(module="c27_leser", action="probe")
        self.assertEqual({z.get("module") for z in audit_log.load_events()},
                         {"c27_leser"},
                         "load_events() liest trotz Umlenkung das echte Ledger")
        self.assertEqual(1, audit_log.report()["total"])

    def test_selbsttests_der_beiden_bausteine(self):
        self.assertEqual([], audit_log.selftest())
        self.assertEqual([], iso.selftest())

    def test_selbsttests_als_skript(self):
        for skript in ("audit_log.py", "repo_isolation.py"):
            with self.subTest(skript=skript):
                proc = subprocess.run(
                    [sys.executable, str(SCRIPTS / skript), "--selftest"],
                    capture_output=True, text=True, cwd=ROOT, timeout=300)
                self.assertEqual(0, proc.returncode, proc.stdout + proc.stderr)


# --------------------------------------------------------------------- #
# 2) Die bekannten Leckpfade bleiben eingesperrt
# --------------------------------------------------------------------- #
class BekannteLeckpfade(unittest.TestCase):
    """Beweis am echten Pfad, nicht am Modell."""

    def test_profi_check_subprozess_bleibt_im_sandkasten(self):
        """Leckstelle 1, auf ihre Mechanik reduziert: publish_gate ruft
        `affiliate_profi_check.py --json` als Kindprozess, und dessen main()
        schreibt bei jedem Fund eine Zeile."""
        with iso.beweis_ledger_unangetastet("profi_check") as sandbox:
            proc = subprocess.run(
                [sys.executable, str(SCRIPTS / "affiliate_profi_check.py"), "--json"],
                capture_output=True, text=True, cwd=ROOT, timeout=600)
            # INNEN lesen: Beim Verlassen des Blocks räumt die Sandbox sich
            # selbst auf. Eine Assertion danach wäre falsch grün (leere Menge
            # erfüllt jede `<=`-Probe) – genau die Schein-Sicherheit, vor der
            # diese Datei warnen soll.
            gefunden = {z.get("module") for z in iso.sandbox_zeilen(sandbox)}
            gefunden_aktionen = [(z.get("module"), z.get("action"))
                                 for z in iso.sandbox_zeilen(sandbox)]
        self.assertGreaterEqual(
            proc.returncode, 0,
            f"affiliate_profi_check ist abgestürzt: {proc.stdout[-300:]}")
        self.assertTrue(gefunden <= {"affiliate_profi_check"},
                        f"unerwartete Module im Sandkasten: {gefunden}")
        # Gegenprobe zur Schein-Sicherheit: main() liefert genau dann Exit 1,
        # wenn es Befunde gibt – und schreibt genau dann eine Zeile. Die Zeile
        # muss im Sandkasten liegen: umgelenkt, nicht abgeschaltet. Ohne
        # gebauten public/-Baum (CI) darf der Check auch leer ausgehen; geprüft
        # wird hier die Einsperrung, nicht das Affiliate-Ergebnis.
        if proc.returncode == 1:
            self.assertIn(("affiliate_profi_check", "check"), gefunden_aktionen,
                          "der Kindprozess protokollierte nicht in die Sandbox – "
                          "die Umlenkung wäre wirkungslos")

    def test_bestand_gate_run_gate_schreibt_kein_buch(self):
        """End-to-End über den echten Aufrufpfad des geheilten Tests."""
        import bestand_gate as bg
        with iso.beweis_ledger_unangetastet("bestand_gate_e2e"):
            funde, _fehler = bg.run_gate()
        self.assertIn("intent", funde)

    def test_record_success_schreibt_kein_buch(self):
        """Leckstelle 2: `_record_success` hat zwei Schreibzweige – Zustand und
        Audit. Der Test von 2026-09 patchte nur den ersten."""
        import secrets_age_guard as sag
        with iso.beweis_ledger_unangetastet("secrets_age") as sandbox, \
                mock.patch.object(sag, "_mutate_state"):
            rc = sag._record_success("GROQ_API_KEY", proof_by="content-engine-v2")
            # INNEN lesen – die Sandbox räumt sich beim Verlassen selbst auf.
            zeilen = [(z["module"], z["action"]) for z in iso.sandbox_zeilen(sandbox)]
        self.assertEqual(0, rc)
        self.assertEqual(
            zeilen, [("secrets_age_guard", "record-success")],
            "die Zeile fehlt im Sandkasten – die Protokollierung wäre still "
            "abgeschaltet statt umgelenkt")


# --------------------------------------------------------------------- #
# 3) Wache gegen neue Leckstellen
# --------------------------------------------------------------------- #
class WacheGegenNeueLeckstellen(unittest.TestCase):
    """Ein künftiger Test, der einen Ledger-Einstieg ohne Sandbox aufruft,
    muss ROT werden – nicht erst im Betrieb auffallen.

    Statische Prüfung über eine ausdrücklich gepflegte Einstiegsliste. Sie
    ersetzt den Laufzeit-Beweis aus Abschnitt 2 nicht, sondern verlängert ihn
    in die Zukunft.
    """

    @staticmethod
    def _import_aufloesung(quelltext: str) -> dict:
        """{lokaler Name: 'modul'} für Aliase, {'name': 'modul.funktion'} für
        From-Imports. Ohne diese Auflösung ist ein Alias wie `pg` mehrdeutig."""
        aufloesung = {}
        for knoten in ast.walk(ast.parse(quelltext)):
            if isinstance(knoten, ast.Import):
                for alias in knoten.names:
                    lokal = alias.asname or alias.name.split(".")[0]
                    aufloesung[lokal] = alias.name
            elif isinstance(knoten, ast.ImportFrom):
                for alias in knoten.names:
                    lokal = alias.asname or alias.name
                    aufloesung[lokal] = f"{knoten.module or ''}.{alias.name}"
        return aufloesung

    @classmethod
    def _ledger_einstiege(cls, methoden_quelltext: str, datei_quelltext: str):
        """Sortierte Liste der Ledger-Einstiege, die diese Methode aufruft."""
        aufloesung = cls._import_aufloesung(datei_quelltext)
        # Importe können auch INNERHALB der Methode stehen (Repo-Stil).
        aufloesung.update(cls._import_aufloesung(methoden_quelltext))
        funde = []
        for knoten in ast.walk(ast.parse(methoden_quelltext)):
            if not isinstance(knoten, ast.Call):
                continue
            ziel = knoten.func
            if isinstance(ziel, ast.Attribute) and isinstance(ziel.value, ast.Name):
                # `self.run_gate()` ist eine eigene Hilfsmethode, kein Einstieg
                # (test_schema_seo_gate.py definiert genau so eine).
                if ziel.value.id == "self":
                    continue
                modul = aufloesung.get(ziel.value.id, ziel.value.id)
                kandidat = (modul, ziel.attr)
            elif isinstance(ziel, ast.Name):
                # `from audit_log import log_event` → nackter Aufruf
                aufgeloest = aufloesung.get(ziel.id, "")
                kandidat = tuple(aufgeloest.rsplit(".", 1)) \
                    if "." in aufgeloest else ("", ziel.id)
            else:
                continue
            if kandidat in LEDGER_EINSTIEGE:
                funde.append(f"{kandidat[0]}.{kandidat[1]}()")
        return sorted(set(funde))

    @staticmethod
    def _patcht_log_event(quelltext: str) -> bool:
        """Erkennt `patch.object(audit_log, "log_event", …)` – das ältere
        Isolationsmuster im Haus."""
        for knoten in ast.walk(ast.parse(quelltext)):
            if not isinstance(knoten, ast.Call):
                continue
            if not (isinstance(knoten.func, ast.Attribute)
                    and knoten.func.attr == "object"):
                continue
            for arg in knoten.args:
                if isinstance(arg, ast.Attribute) and arg.attr == PATCH_ZIEL:
                    return True
                if isinstance(arg, ast.Constant) and arg.value == PATCH_ZIEL:
                    return True
        return False

    @staticmethod
    def _nutzt_sandbox(methoden_quelltext: str) -> bool:
        for knoten in ast.walk(ast.parse(methoden_quelltext)):
            if isinstance(knoten, ast.Call):
                ziel = knoten.func
                name = ziel.attr if isinstance(ziel, ast.Attribute) else (
                    ziel.id if isinstance(ziel, ast.Name) else "")
                if name in ISOLATIONS_BAUSTEINE:
                    return True
        return False

    def _testmethoden(self):
        """(dateiname, zeile, name, methoden-quelltext, datei-quelltext)."""
        for datei in sorted(TESTS.glob("test_*.py")):
            if datei.name == Path(__file__).name:
                continue        # diese Wache darf ihre eigenen Proben aufrufen
            datei_quelltext = datei.read_text(encoding="utf-8")
            baum = ast.parse(datei_quelltext, filename=str(datei))
            for knoten in ast.walk(baum):
                if isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)) \
                        and knoten.name.startswith("test"):
                    ausschnitt = ast.get_source_segment(datei_quelltext, knoten) or ""
                    yield (datei.name, knoten.lineno, knoten.name,
                           ausschnitt, datei_quelltext)

    def test_jeder_ledger_einstieg_in_tests_ist_isoliert(self):
        funde = []
        for datei, zeile, name, quelltext, datei_quelltext in self._testmethoden():
            kritisch = self._ledger_einstiege(quelltext, datei_quelltext)
            if not kritisch:
                continue
            if self._nutzt_sandbox(quelltext) or self._patcht_log_event(quelltext):
                continue
            funde.append(
                f"{datei}:{zeile} {name}() ruft {', '.join(kritisch)} ohne "
                f"Sandbox auf – der Test schreibt echte Zeilen ins "
                f"Beweis-Ledger data/audit/ (C27). Heilung: `with "
                f"beweis_ledger_unangetastet(…)` aus scripts/repo_isolation.py.")
        self.assertEqual([], funde, "\n".join(funde))

    def test_die_wache_erkennt_einen_neuen_lecker(self):
        """Schein-Sicherheits-Probe: ohne Zähne ist die Wache ein grünes
        Häkchen."""
        datei = textwrap.dedent("""\
            import bestand_gate as bg
            import secrets_age_guard as sag
            from audit_log import log_event
            class Kunst(unittest.TestCase):
                pass
            """)
        kunst = textwrap.dedent("""\
            def test_leckt(self):
                bg.run_gate()
                sag._record_success('GROQ_API_KEY')
                log_event(module='x', action='y')
            """)
        self.assertEqual(
            ["audit_log.log_event()", "bestand_gate.run_gate()",
             "secrets_age_guard._record_success()"],
            self._ledger_einstiege(kunst, datei))
        self.assertFalse(self._nutzt_sandbox(kunst))
        self.assertFalse(self._patcht_log_event(kunst))

    def test_die_wache_laesst_beide_isolationsmuster_durch(self):
        """Gegenrichtung: korrekt isolierte Tests dürfen kein Befund sein."""
        sandbox = textwrap.dedent("""\
            def test_a(self):
                from repo_isolation import beweis_ledger_unangetastet
                with beweis_ledger_unangetastet('x'):
                    bg.run_gate()
            """)
        self.assertTrue(self._nutzt_sandbox(sandbox))

        gepatcht = textwrap.dedent("""\
            def test_b(self):
                with patch.object(audit_log, 'log_event'):
                    publish_gate.main()
            """)
        self.assertTrue(self._patcht_log_event(gepatcht))

    def test_die_wache_verwechselt_gleichnamige_module_nicht(self):
        """Zwei Falschbefunde, die diese Wache selbst fast gebaut hätte:

        · `pg` ist in test_ruleset_restoration.py `pflichtcheck_guard`, nicht
          `publish_gate` – ein Alias allein trägt keine Bedeutung.
        · `self.run_gate()` ist eine eigene Hilfsmethode.
        """
        pflicht = textwrap.dedent("""\
            import pflichtcheck_guard as pg
            class Kunst(unittest.TestCase):
                def run_gate(self):
                    return [], []
            """)
        methode = textwrap.dedent("""\
            def test_report_cli(self):
                pg.main(['--automation'])
                hard, _ = self.run_gate()
            """)
        self.assertEqual([], self._ledger_einstiege(methode, pflicht),
                         "die Wache hält pflichtcheck_guard.main() für das "
                         "Publish-Gate oder eine Hilfsmethode für einen Einstieg")

        echt = textwrap.dedent("""\
            import publish_gate as pg
            """)
        self.assertEqual(["publish_gate.main()"],
                         self._ledger_einstiege(methode, echt))


# --------------------------------------------------------------------- #
# 4) Das Buch selbst: frei von Einträgen, die kein Betrieb erzeugen konnte
# --------------------------------------------------------------------- #
#: Fixture-Slugs der Test-Suite. Sie dürfen niemals in einem Betriebsbeweis
#: stehen – es sind Etiketten, keine Artikel.
FIXTURE_SLUGS = (
    "2026-09-07-r5-live",
    "2026-09-07-r5-hold",
    "2026-09-07-r5-reserve",
)


def record_success_aufrufe() -> set:
    """(VAR, proof_by)-Paare, die ein Workflow tatsächlich erzeugen kann.

    Selbstlernend statt abgeschrieben: Gelesen wird, welche Workflows
    `--record-success` überhaupt aufrufen und mit welchem `--proof-by`. Ein
    Paar, das kein Workflow erzeugen kann, ist kein Betriebsbeweis – so war
    der Nachweis für die vier GROQ-Zeilen vom 05.10.2026 geführt: Das Register
    ERLAUBT `content-engine-v2` für GROQ_API_KEY, aber kein Workflow ruft es
    auf. Erlaubt heißt nicht erfolgt.
    """
    paare = set()
    for pfad in sorted((ROOT / ".github" / "workflows").glob("*.yml")):
        text = pfad.read_text(encoding="utf-8")
        # Backslash-Fortführung auflösen, wie die Shell sie sieht.
        glatt = re.sub(r"\\\s*\n\s*", " ", text)
        for m in re.finditer(
                r"--record-success\s+(\S+)\s+--proof-by\s+([A-Za-z0-9_.-]+)", glatt):
            paare.add((m.group(1), m.group(2)))
    return paare


def ledger_zeilen_mit_fund(finde):
    """Alle Ledger-Zeilen, auf die `finde(entry, raw)` zutrifft."""
    funde = []
    for datei in sorted(LEDGER.glob("*.jsonl")):
        for nummer, roh in enumerate(
                datei.read_text(encoding="utf-8").splitlines(), 1):
            roh = roh.strip()
            if not roh:
                continue
            try:
                eintrag = json.loads(roh)
            except json.JSONDecodeError:
                continue
            grund = finde(eintrag, roh)
            if grund:
                funde.append(f"{datei.name}:{nummer} {grund}")
    return funde


class FabrizierteEintraege(unittest.TestCase):
    """Bewacht den IST-Zustand des Buches, nicht nur den Schreibpfad.

    Die Isolation oben verhindert neue fabrizierte Beweise. Diese Klasse
    stellt sicher, dass die bereits aufgefundenen nicht zurückkehren – und
    dass ein künftiger Eintrag derselben Art sofort auffällt.

    Abgrenzung, empirisch erhoben am 07.10.2026: Ein gate-Entscheid für einen
    Slug, der nicht in der Content-Historie steht, ist KEIN Beleg für eine
    Fälschung. `publish_gate.discard_article()` löscht einen verworfenen neuen
    Artikel (`shutil.rmtree`), bevor er je committet wird – 161 solcher Zeilen
    sind echt. Entscheidend ist deshalb, ob der Slug eine Test-Fixture ist und
    ob ein Workflow den Eintrag überhaupt erzeugen konnte.
    """

    def test_kein_fixture_slug_im_buch(self):
        def finde(_eintrag, roh):
            for slug in FIXTURE_SLUGS:
                if slug in roh:
                    return (f"nennt die Test-Fixture `{slug}` – ein Etikett aus "
                            f"scripts/tests/, kein Artikel")
            return ""

        funde = ledger_zeilen_mit_fund(finde)
        self.assertEqual([], funde, "\n".join(funde))

    def test_record_success_nur_aus_echtem_workflow(self):
        """Jede Erfolgsbescheinigung muss ein Workflow erzeugen können.

        `secrets_age_guard` selbst wertet eine fremde Erfolgsmeldung als
        `declared_foreign` ab; `social-autopilot.yml` hält fest: „Probe und
        nicht `--record-success`: eine fremde Erfolgsmeldung gilt nicht."
        Im Buch stand sie trotzdem – mit `quality: declared`, also aufgewertet.
        """
        erlaubt = record_success_aufrufe()
        # Blindheits-Probe: Ohne erkennbaren Workflow-Aufruf wäre jede Zeile ein
        # Fund und die Regel unbrauchbar – dann lieber laut scheitern.
        self.assertTrue(erlaubt,
                        "kein Workflow ruft --record-success auf – die Probe "
                        "wäre blind (Parser prüfen)")

        def finde(eintrag, _roh):
            if eintrag.get("module") != "secrets_age_guard":
                return ""
            if eintrag.get("action") != "record-success":
                return ""
            eingabe = eintrag.get("input") or {}
            paar = (eingabe.get("var"), eingabe.get("proof_by"))
            if paar in erlaubt:
                return ""
            return (f"bescheinigt {paar[0]} einen Erfolg via `{paar[1]}` – kein "
                    f"Workflow ruft `--record-success` dafür auf (erzeugbar: "
                    f"{sorted(erlaubt)})")

        funde = ledger_zeilen_mit_fund(finde)
        self.assertEqual([], funde, "\n".join(funde))

    def test_die_buchwache_ist_nicht_blind(self):
        """Schein-Sicherheits-Probe: Die Wache muss anschlagen, sonst ist das
        saubere Buch oben nur eine leere Menge."""
        kunst = ('{"ts": "2026-10-03T18:26:51Z", "module": "publish_gate", '
                 '"action": "gate", "input": {"candidates": '
                 '["2026-09-07-r5-live"]}}')
        self.assertTrue(any(slug in kunst for slug in FIXTURE_SLUGS))

        erfunden = {"module": "secrets_age_guard", "action": "record-success",
                    "input": {"var": "GROQ_API_KEY",
                              "proof_by": "content-engine-v2"}}
        erlaubt = record_success_aufrufe()
        self.assertNotIn(("GROQ_API_KEY", "content-engine-v2"), erlaubt,
                         "ein Workflow ruft das Paar inzwischen selbst auf – "
                         "die Regel muss dann neu gelesen werden")

    def test_echter_gate_entscheid_ist_kein_fund(self):
        """Gegenrichtung: Ein gate-Entscheid für einen echten Artikel bleibt
        stehen – auch wenn der Slug nicht in der Content-Historie steht, weil
        `discard_article()` ihn nach dem Verwurf gelöscht hat."""
        echt = {"module": "publish_gate", "action": "gate",
                "input": {"candidates": [
                    "2026-10-03-stromanbieter-pleite-so-sicherst-du-deine-"
                    "stromversorgung"]}}
        roh = json.dumps(echt, ensure_ascii=False)
        self.assertFalse(any(slug in roh for slug in FIXTURE_SLUGS),
                         "ein echter Artikel-Slug wird als Fixture behandelt")


if __name__ == "__main__":
    unittest.main()
