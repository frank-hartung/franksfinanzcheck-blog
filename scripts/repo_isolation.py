#!/usr/bin/env python3
"""repo_isolation.py – Ein Testlauf fabriziert keine Beweise (Governance C27).

WARUM DIESES MODUL EXISTIERT (Nebenbefund zu #610, 07.10.2026)
--------------------------------------------------------------
`data/audit/*.jsonl` ist versioniert und wird von `history_guard.py` als
append-only bewacht (H6). Jede Zeile darin ist eine Behauptung über den
Betrieb: „Dieser Artikel wurde am Gate verworfen", „Dieses Secret hat sich
im Lauf X bewährt". Drei Unit-Tests schrieben echte Zeilen hinein:

  · test_affiliate_intent_guard.test_bestand_gate_checks_intent_dimension
      → bestand_gate.run_gate() → publish_gate.affiliate_profi_failures()
      → Subprozess `affiliate_profi_check.py --json` → log_event(...)
  · test_clear_text_logging_security
      .test_secrets_age_guard_record_success_and_list_are_clean
      → secrets_age_guard._record_success("GROQ_API_KEY") → log_event(...)
        (der Test patchte `_mutate_state`, vergaß aber den Audit-Zweig)
  · test_publication_reliability.test_publish_gate_heilt_r5_vor_der_harten_pruefung
      → pg.main() mit DRY_RUN=False → log_event(module="publish_gate", ...)
        mit dem Fixture-Slug `2026-09-07-r5-live`

Die dritte Variante ist die teure: Sie legte einen gate-Entscheid für einen
Artikel ins Buch, den es nie gab. Am 03.10.2026 stand genau diese Zeile
bereits im versionierten Ledger.

WARUM EINE UMGEBUNGSVARIABLE UND KEIN MONKEYPATCH
-------------------------------------------------
Die erste Leckstelle läuft über einen SUBPROZESS. `mock.patch.object` im
Testprozess erreicht ein Kind nicht – die Umgebung erbt sich dagegen in
jedes Kind. Deshalb ist der Vertrag in `audit_log.py` an `FFC_AUDIT_DIR`
gebunden, und dieses Modul setzt genau diese Variable.

VERTRAG FÜR TESTS
-----------------
Jeder Test, der eine Wache oder ein Gate aufruft, die `log_event()` erreichen
kann, läuft in der Sandbox – und beweist danach, dass das echte Ledger
Byte für Byte unverändert blieb:

    from repo_isolation import beweis_ledger_unangetastet

    def test_gate_prueft_intent(self):
        with beweis_ledger_unangetastet("bestand_gate"):
            findings, errors = bg.run_gate()
        self.assertIn("intent", findings)

Der Block bricht mit AssertionError ab, sobald auch nur eine Zeile im echten
`data/audit/` landet. Zusätzlich überwacht `publication-reliability-tests.yml`
das Verzeichnis nach dem Suite-Lauf – ein Leak wird damit zum Build-Fehler,
auch wenn ein künftiger Test die Sandbox vergisst.

Selbsttest:  python3 scripts/repo_isolation.py --selftest
"""
from __future__ import annotations

import contextlib
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parent.parent
SCRIPTS = BLOG_DIR / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import audit_log  # noqa: E402

#: Das ECHTE, versionierte Beweis-Ledger. Bewusst eine Konstante: Die
#: Umlenkung lebt in `audit_verzeichnis()`, damit „wo ist das Buch" und
#: „wohin schreibt dieser Prozess" zwei verschiedene Fragen bleiben.
LEDGER = BLOG_DIR / "data" / "audit"


# --------------------------------------------------------------------- #
# Fingerabdruck
# --------------------------------------------------------------------- #
def fingerabdruck(verzeichnis: str | os.PathLike | None = None) -> dict:
    """{Dateiname: sha256} aller JSONL-Dateien eines Verzeichnisses.

    Inhalt statt Zeitstempel: Ein Anhängen, ein Umschreiben und ein Löschen
    fallen alle auf, während ein bloßes `touch` (mtime) kein Befund ist.
    """
    pfad = Path(verzeichnis) if verzeichnis is not None else LEDGER
    abdruck = {}
    if not pfad.is_dir():
        return abdruck
    for datei in sorted(pfad.glob("*.jsonl")):
        try:
            abdruck[datei.name] = hashlib.sha256(datei.read_bytes()).hexdigest()
        except OSError:
            abdruck[datei.name] = "unlesbar"
    return abdruck


def ledger_abweichung(vorher: dict, verzeichnis: str | os.PathLike | None = None) -> list:
    """Unterschiede zwischen einem Fingerabdruck und dem jetzigen Zustand.

    Liefert menschenlesbare Zeilen (leer = das Ledger ist unberührt).
    """
    jetzt = fingerabdruck(verzeichnis)
    funde = []
    for name in sorted(set(vorher) | set(jetzt)):
        alt, neu = vorher.get(name), jetzt.get(name)
        if alt is None:
            funde.append(f"{name}: NEU angelegt (Testlauf schrieb ins Ledger)")
        elif neu is None:
            funde.append(f"{name}: GELÖSCHT (Testlauf entfernte Beweise)")
        elif alt != neu:
            funde.append(f"{name}: UMGESCHRIEBEN/erweitert "
                         f"({alt[:8]}… → {neu[:8]}…)")
    return funde


def lese_zeilen(pfad: str | os.PathLike) -> list:
    """Alle JSON-Zeilen einer Datei (leere Liste, wenn sie nicht existiert)."""
    datei = Path(pfad)
    if not datei.is_file():
        return []
    zeilen = []
    for roh in datei.read_text(encoding="utf-8").splitlines():
        roh = roh.strip()
        if roh:
            try:
                zeilen.append(json.loads(roh))
            except json.JSONDecodeError:
                pass
    return zeilen


def sandbox_zeilen(sandbox: str | os.PathLike) -> list:
    """Alle Zeilen einer Sandbox, über alle Tagesdateien hinweg."""
    zeilen = []
    for datei in sorted(Path(sandbox).glob("*.jsonl")):
        zeilen += lese_zeilen(datei)
    return zeilen


# --------------------------------------------------------------------- #
# Sandbox
# --------------------------------------------------------------------- #
@contextlib.contextmanager
def ledger_sandbox(name: str = "testlauf"):
    """Lenkt jede Audit-Zeile dieses Blocks in ein Temp-Verzeichnis um.

    Wirkt für den eigenen Prozess UND für alle Kindprozesse, weil der Vertrag
    über `FFC_AUDIT_DIR` in der Umgebung steht. Liefert den Pfad der Sandbox,
    damit ein Test die umgelenkten Zeilen lesen und damit beweisen kann, dass
    die Protokollierung selbst weiter funktioniert (nur eben nicht ins Buch).
    """
    sandbox = Path(tempfile.mkdtemp(prefix=f"ffc-ledger-{name}-"))
    vorher = os.environ.get(audit_log.AUDIT_DIR_ENV)
    os.environ[audit_log.AUDIT_DIR_ENV] = str(sandbox)
    try:
        yield sandbox
    finally:
        if vorher is None:
            os.environ.pop(audit_log.AUDIT_DIR_ENV, None)
        else:
            os.environ[audit_log.AUDIT_DIR_ENV] = vorher
        shutil.rmtree(sandbox, ignore_errors=True)


@contextlib.contextmanager
def beweis_ledger_unangetastet(name: str = "testlauf"):
    """Sandbox PLUS Schlussbeweis – der Baustein für Tests.

    Bricht mit AssertionError ab, sobald im echten `data/audit/` eine Zeile
    entsteht, wächst oder verschwindet. Ein Test, der diesen Block benutzt,
    kann das Ledger nicht stillschweigend verschmutzen: Der Beweis läuft
    nach dem Block, also auch dann, wenn die Prüfung selbst wirft.
    """
    vorher = fingerabdruck()
    try:
        with ledger_sandbox(name) as sandbox:
            yield sandbox
    finally:
        funde = ledger_abweichung(vorher)
        if funde:
            raise AssertionError(
                "🛑 Beweis-Ledger angetastet (Governance C27): Dieser Testlauf "
                "hat echte Zeilen in data/audit/ geschrieben – das Ledger ist "
                "append-only bewacht (history_guard H6) und ein Testeintrag "
                "ist ein fabrizierter Beweis.\n  " + "\n  ".join(funde) +
                "\nHeilung: Den Aufruf in `with beweis_ledger_unangetastet(...)` "
                "fassen (scripts/repo_isolation.py)."
            )


def selftest() -> list:
    """Beweist die Isolation in beide Richtungen (C6/C27).

    Fehler UND Schein-Sicherheit: Die Sandbox muss umlenken (sonst ist sie
    wirkungslos) und das echte Ledger muss unberührt bleiben (sonst lügt sie).
    """
    fehler = []
    echt_vorher = fingerabdruck()
    alt = os.environ.get(audit_log.AUDIT_DIR_ENV)

    # 1) Ohne Sandbox zeigt der Vertrag auf das echte Ledger.
    #    Vergleich über Path, nicht über den String: `os.path.abspath` (audit_log)
    #    und `Path.resolve()` (dieses Modul) unterscheiden sich unter Symlinks.
    os.environ.pop(audit_log.AUDIT_DIR_ENV, None)
    if Path(audit_log.audit_verzeichnis()) != Path(audit_log.AUDIT_DIR):
        fehler.append(f"audit_verzeichnis() zeigt ohne Umlenkung nicht auf {LEDGER}")

    # 2) Die Sandbox lenkt um und ist lesbar.
    with ledger_sandbox("selftest") as sandbox:
        if audit_log.audit_verzeichnis() != str(sandbox):
            fehler.append("ledger_sandbox() setzt FFC_AUDIT_DIR nicht")
        pfad = audit_log.log_event(module="repo_isolation_selftest",
                                   action="probe", status="ok")
        if not pfad or Path(pfad).parent != sandbox:
            fehler.append(f"log_event() schrieb außerhalb der Sandbox: {pfad}")
        zeilen = sandbox_zeilen(sandbox)
        if [z.get("module") for z in zeilen] != ["repo_isolation_selftest"]:
            fehler.append(f"sandbox_zeilen() liefert Unerwartetes: {zeilen}")
    if sandbox.exists():
        fehler.append("ledger_sandbox() räumt die Sandbox nicht auf")

    # 3) Die Umgebung ist danach wiederhergestellt.
    if alt is None and audit_log.AUDIT_DIR_ENV in os.environ:
        fehler.append("ledger_sandbox() lässt FFC_AUDIT_DIR zurück")

    # 4) Der Fingerabdruck merkt eine angehängte Zeile (Schein-Sicherheits-Probe).
    with tempfile.TemporaryDirectory(prefix="ffc-abdruck-") as tmp:
        t = Path(tmp)
        (t / "2026-01-01.jsonl").write_text('{"ts": "x"}\n', encoding="utf-8")
        davor = fingerabdruck(t)
        with open(t / "2026-01-01.jsonl", "a", encoding="utf-8") as fh:
            fh.write('{"ts": "y"}\n')
        if not ledger_abweichung(davor, t):
            fehler.append("ledger_abweichung() merkt eine angehängte Zeile nicht")
        (t / "2026-01-02.jsonl").write_text('{"ts": "z"}\n', encoding="utf-8")
        if not any("NEU" in f for f in ledger_abweichung(davor, t)):
            fehler.append("ledger_abweichung() merkt eine neue Datei nicht")

    # 5) Schlussbeweis: Der Selbsttest hat das echte Ledger nicht angetastet.
    funde = ledger_abweichung(echt_vorher)
    if funde:
        fehler.append("repo_isolation-Selbsttest schrieb ins echte Ledger: "
                      + "; ".join(funde))
    if alt is not None:
        os.environ[audit_log.AUDIT_DIR_ENV] = alt
    return fehler


def main() -> int:
    if "--selftest" in sys.argv:
        fehler = selftest()
        if fehler:
            print("🛑 REPO-ISOLATION-SELBSTTEST FEHLGESCHLAGEN – Ledger-Schutz defekt.")
            for f in fehler:
                print(f"   {f}")
            return 2
        print("✅ Repo-Isolation-Selbsttest ok: Sandbox lenkt um (auch für "
              "Kindprozesse), data/audit/ bleibt unberührt, Abweichungen fallen auf.")
        return 0
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
