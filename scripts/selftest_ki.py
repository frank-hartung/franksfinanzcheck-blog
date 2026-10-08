#!/usr/bin/env python3
"""selftest_ki.py – KI-Probe: Kein Selbsttest darf am Modell oder am Netz hängen.

WARUM (Content-Engine v2 #138, Run 37694986440, 07.10.2026 22:15 UTC)
-----------------------------------------------------------------------
Phase 0.5 der Engine starb mit Exit 2 – noch VOR Phase 1, also ohne einen
einzigen Artikel, ohne Endabnahme, ohne Reserve-Refill. Ursache war kein
kaputter Code, sondern ein Selbsttest, der das LIVE-MODELL fragte:
`requeue_quality_holds.py --selftest` rief den Lesbarkeits-Heiler mit
`ki=True` ohne Attrappe auf. Im PR-CI und lokal fehlen die Schlüssel – Stufe B
fiel still aus, der Test war grün. In Phase 0.5 stehen seit WACHE-609 echte
GROQ/GEMINI-Schlüssel. Sobald das Modell den „schlechten“ Fixture-Text gut
genug umschrieb (Flesch 2.9 → 86), urteilte der Test „Hold unter der Schwelle
wird freigegeben“ – rot, ohne dass sich eine Zeile Code geändert hatte. Die
Läufe #136/#137 am selben Tag waren grün, weil die Antwort des Modells zufällig
verworfen wurde. Ein Münzwurf im kritischen Pfad der Produktion.

Dieselbe Klasse hat `selftest_clock.py` für die Wanduhr geschlossen. Dieses
Modul schließt sie für KI und Netz:

  `ki_sperre()`   Kontextmanager. Setzt für jeden bekannten KI-Schlüssel eine
                  ATTRAPPE in die Umgebung (der Selbsttest sieht dieselbe Lage
                  wie die Produktion: „Schlüssel vorhanden“) und sperrt jede
                  Netzverbindung außer Loopback. Jeder Versuch wird
                  PROTOKOLLIERT, auch wenn der Aufrufer die Ausnahme schluckt
                  (genau das tut `lesbarkeit_heiler._ki_chat` – deshalb fiel
                  der Fehler nie auf).

  `trap(script)`  Fährt den `--selftest` eines Skripts in einem eigenen
                  Prozess unter der Sperre. Befund, wenn
                    · der Selbsttest das Netz/Modell berühren wollte (NETZ), oder
                    · der Selbsttest unter der Sperre rot ist (ROT) – das ist die
                      Lage eines Tages mit Modell-Ausfall in der Produktion.

  `entdecke()`    Liest alle Workflows und liefert jeden `scripts/*.py
                  --selftest`-Aufruf. Bewusst ALLE, nicht nur die Schritte, die
                  heute Schlüssel tragen: #138 entstand genau dadurch, dass ein
                  Schritt am 07.10. Schlüssel BEKAM.

Nutzung:
    python3 scripts/selftest_ki.py --selftest
    python3 scripts/selftest_ki.py --trap scripts/requeue_quality_holds.py
    python3 scripts/selftest_ki.py --trap-workflows            # alle Workflow-Selbsttests
    python3 scripts/selftest_ki.py --trap-workflows --nur-schluessel
    python3 scripts/selftest_ki.py --liste                     # nur entdecken

Exit: 0 = grün · 1 = Befund (Selbsttest hängt an KI/Netz oder ist unter Sperre rot)
      · 2 = Werkzeugfehler
"""
from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import socket
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"

# Jede Umgebungsvariable, über die ein Skript ein Modell erreicht. Die Probe
# setzt ALLE auf eine Attrappe – ein Selbsttest, der „Schlüssel vorhanden“ als
# Freibrief für einen echten Aufruf nimmt, läuft dann in die Netzsperre statt
# still in die Produktion. Quelle ist die SSOT `data/ki_transportweg.yaml`
# (Feld `schluessel` je Anbieter); die Grundliste unten gilt, falls die SSOT
# nicht lesbar ist. Kostenpflichtige Wege existieren im Repo nicht (Vertrag
# T1, test_ki_transportweg) – und die Netzsperre fängt ohnehin JEDEN Versuch,
# unabhängig davon, welcher Schlüssel ihn auslöste.
_GRUNDSCHLUESSEL = (
    "GEMINI_API_KEY", "GROQ_API_KEY", "NVIDIA_API_KEY",
    "CLOUDFLARE_API_TOKEN", "CLOUDFLARE_ACCOUNT_ID",
)
SSOT = ROOT / "data" / "ki_transportweg.yaml"


def ki_schluessel() -> tuple[str, ...]:
    gefunden = list(_GRUNDSCHLUESSEL)
    try:
        import yaml
        daten = yaml.safe_load(SSOT.read_text(encoding="utf-8")) or {}
    except Exception:  # noqa: BLE001 – SSOT fehlt/kaputt: Grundliste genügt
        return tuple(gefunden)

    def sammle(knoten) -> None:
        if isinstance(knoten, dict):
            for k, v in knoten.items():
                if k == "schluessel" and isinstance(v, list):
                    gefunden.extend(str(x) for x in v if x)
                else:
                    sammle(v)
        elif isinstance(knoten, list):
            for v in knoten:
                sammle(v)

    sammle(daten)
    return tuple(dict.fromkeys(gefunden))


KI_SCHLUESSEL = ki_schluessel()
ATTRAPPE = "ffc-ki-probe-attrappe"
PROTOKOLL_ENV = "FFC_KI_PROBE_PROTOKOLL"

_LOOPBACK_NAMEN = {"localhost", "localhost.localdomain", "ip6-localhost",
                   "ip6-loopback", ""}

_AUFRUF = re.compile(
    r"python3?\s+(scripts/[\w./-]+\.py)\b([^\n|&;#]*?)--selftest\b")


class NetzGesperrt(OSError):
    """Ein Selbsttest wollte das Netz erreichen (KI-Probe)."""


# ===========================================================================
#  1) DIE SPERRE
# ===========================================================================
def _ist_loopback(host) -> bool:
    if host is None:
        return True
    if isinstance(host, bytes):
        host = host.decode("ascii", "replace")
    host = str(host).strip("[]").lower()
    if host in _LOOPBACK_NAMEN:
        return True
    if host.startswith("127.") or host in ("::1", "0:0:0:0:0:0:0:1", "0.0.0.0"):
        return True
    return host.startswith("::ffff:127.")


def _host_port(adresse):
    if isinstance(adresse, tuple) and adresse:
        return adresse[0], (adresse[1] if len(adresse) > 1 else None)
    return adresse, None          # AF_UNIX: Pfad – lokal, kein Netz


def _bibliothekspfade() -> tuple[str, ...]:
    import sysconfig
    pfade = {sysconfig.get_paths().get(k) for k in ("stdlib", "platstdlib", "purelib", "platlib")}
    return tuple(str(Path(p).resolve()) for p in pfade if p)


def _aufrufort() -> str:
    """Innerste Zeile des geprüften Codes, die den Versuch auslöste.

    Bevorzugt Repo-Dateien (`scripts/lesbarkeit_heiler.py:525 (_ki_chat)`),
    sonst die innerste echte Datei außerhalb von stdlib/site-packages.
    Pseudo-Rahmen (`<frozen runpy>`, `<string>`) und diese Datei zählen nie.
    """
    eigene = Path(__file__).resolve()
    bib = _bibliothekspfade()
    fremd = None
    for rahmen in reversed(traceback.extract_stack()[:-3]):
        if not rahmen.filename or rahmen.filename.startswith("<"):
            continue
        try:
            pfad = Path(rahmen.filename).resolve()
        except (OSError, ValueError):
            continue
        if pfad == eigene or str(pfad).startswith(bib):
            continue
        try:
            rel = pfad.relative_to(ROOT)
        except ValueError:
            fremd = fremd or f"{pfad}:{rahmen.lineno} ({rahmen.name})"
            continue
        return f"{rel}:{rahmen.lineno} ({rahmen.name})"
    return fremd or "unbekannt (außerhalb des Repos)"


@contextlib.contextmanager
def ki_sperre(protokoll: list | None = None, protokoll_datei: str | None = None):
    """Attrappen-Schlüssel setzen, Netz außer Loopback sperren, Versuche zählen.

    `protokoll` (Liste) und/oder `protokoll_datei` (JSON-Zeilen) nehmen jeden
    Versuch auf – unabhängig davon, ob der Aufrufer die Ausnahme schluckt.
    Nach dem Block ist alles wie vorher (Umgebung UND socket-Modul).
    """
    versuche = protokoll if protokoll is not None else []
    env_vorher = {k: os.environ.get(k) for k in KI_SCHLUESSEL}
    echt = {
        "connect": socket.socket.connect,
        "connect_ex": socket.socket.connect_ex,
        "create_connection": socket.create_connection,
        "getaddrinfo": socket.getaddrinfo,
    }

    def _melde(art: str, host, port) -> None:
        eintrag = {"art": art, "host": str(host), "port": port, "ort": _aufrufort()}
        versuche.append(eintrag)
        if protokoll_datei:
            try:
                with open(protokoll_datei, "a", encoding="utf-8") as fh:
                    fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
            except OSError:
                pass
        raise NetzGesperrt(f"KI-Probe: Netz im Selbsttest gesperrt ({art} → {host}:{port})")

    def connect(self, adresse):
        host, port = _host_port(adresse)
        if self.family in (socket.AF_INET, socket.AF_INET6) and not _ist_loopback(host):
            _melde("connect", host, port)
        return echt["connect"](self, adresse)

    def connect_ex(self, adresse):
        host, port = _host_port(adresse)
        if self.family in (socket.AF_INET, socket.AF_INET6) and not _ist_loopback(host):
            _melde("connect_ex", host, port)
        return echt["connect_ex"](self, adresse)

    def create_connection(adresse, *args, **kwargs):
        host, port = _host_port(adresse)
        if not _ist_loopback(host):
            _melde("create_connection", host, port)
        return echt["create_connection"](adresse, *args, **kwargs)

    def getaddrinfo(host, port, *args, **kwargs):
        if not _ist_loopback(host):
            _melde("getaddrinfo", host, port)
        return echt["getaddrinfo"](host, port, *args, **kwargs)

    try:
        for k in KI_SCHLUESSEL:
            os.environ[k] = ATTRAPPE
        socket.socket.connect = connect
        socket.socket.connect_ex = connect_ex
        socket.create_connection = create_connection
        socket.getaddrinfo = getaddrinfo
        yield versuche
    finally:
        socket.socket.connect = echt["connect"]
        socket.socket.connect_ex = echt["connect_ex"]
        socket.create_connection = echt["create_connection"]
        socket.getaddrinfo = echt["getaddrinfo"]
        for k, v in env_vorher.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


# ===========================================================================
#  2) DIE PROBE UM EINEN SELBSTTEST
# ===========================================================================
def _kind(script: str, args: list[str]) -> int:
    """Läuft IM Kindprozess: Sperre an, Skript als __main__ ausführen."""
    import runpy

    datei = os.environ.get(PROTOKOLL_ENV) or None
    pfad = str((ROOT / script).resolve()) if not os.path.isabs(script) else script
    sys.path.insert(0, os.path.dirname(pfad))
    sys.argv = [pfad, *args]
    with ki_sperre(protokoll_datei=datei):
        try:
            runpy.run_path(pfad, run_name="__main__")
        except SystemExit as exc:
            code = exc.code
            if code is None:
                return 0
            return code if isinstance(code, int) else 1
    return 0


def trap(script: str, args: tuple[str, ...] = ("--selftest",),
         timeout: int = 600) -> dict:
    """Selbsttest eines Skripts unter KI-Sperre in eigenem Prozess fahren.

    Rückgabe: {script, rc, versuche, dauer, befund, ausgabe}
    befund: None (grün) · "NETZ" · "ROT" · "ZEIT" (Timeout)
    """
    with tempfile.NamedTemporaryFile("w+", suffix=".jsonl", delete=False) as fh:
        protokoll = fh.name
    env = dict(os.environ)
    env[PROTOKOLL_ENV] = protokoll
    env.setdefault("PYTHONIOENCODING", "utf-8")
    start = time.monotonic()
    try:
        proc = subprocess.run(
            [sys.executable, str(Path(__file__).resolve()), "--_kind", script,
             "--", *args],
            cwd=str(ROOT), env=env, capture_output=True, text=True,
            timeout=timeout, check=False)
        rc, ausgabe = proc.returncode, (proc.stdout or "") + (proc.stderr or "")
    except subprocess.TimeoutExpired as exc:
        rc = None
        ausgabe = ((exc.stdout or b"").decode("utf-8", "replace")
                   if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
    dauer = time.monotonic() - start
    versuche = []
    try:
        with open(protokoll, encoding="utf-8") as fh:
            versuche = [json.loads(z) for z in fh if z.strip()]
    except (OSError, ValueError):
        pass
    finally:
        with contextlib.suppress(OSError):
            os.unlink(protokoll)
    if versuche:
        befund = "NETZ"
    elif rc is None:
        befund = "ZEIT"
    elif rc != 0:
        befund = "ROT"
    else:
        befund = None
    return {"script": script, "rc": rc, "versuche": versuche,
            "dauer": dauer, "befund": befund, "ausgabe": ausgabe}


# ===========================================================================
#  3) ENTDECKUNG – jeder Selbsttest, den ein Workflow aufruft
# ===========================================================================
def entdecke(workflows: Path = WORKFLOWS) -> list[dict]:
    """Alle `python3 scripts/X.py … --selftest`-Aufrufe aus den Workflows.

    Rückgabe (nach Skript sortiert, je Skript ein Eintrag):
      {script, args, orte: ["datei.yml › Schritt"], schluessel: bool}
    `schluessel` = mindestens ein Aufruf läuft in einem Schritt/Job, dessen
    Umgebung einen KI-Schlüssel trägt (heute schon produktionsrelevant).
    """
    import yaml  # PyYAML – im CI vorhanden, hier erst bei Bedarf geladen

    gefunden: dict[str, dict] = {}
    for wf in sorted(workflows.glob("*.y*ml")):
        try:
            daten = yaml.safe_load(wf.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError:
            continue
        wf_env = daten.get("env") or {}
        for _jname, job in (daten.get("jobs") or {}).items():
            if not isinstance(job, dict):
                continue
            job_env = {**wf_env, **(job.get("env") or {})}
            for schritt in job.get("steps") or []:
                lauf = schritt.get("run") or ""
                if "--selftest" not in lauf:
                    continue
                env = {**job_env, **(schritt.get("env") or {})}
                mit_key = any(k in env for k in KI_SCHLUESSEL)
                for m in _AUFRUF.finditer(lauf):
                    script = m.group(1)
                    extra = m.group(2).split()
                    e = gefunden.setdefault(script, {
                        "script": script, "args": [*extra, "--selftest"],
                        "orte": [], "schluessel": False})
                    e["orte"].append(f"{wf.name} › {schritt.get('name') or '(ohne Name)'}")
                    e["schluessel"] = e["schluessel"] or mit_key
    return [gefunden[k] for k in sorted(gefunden)]


# ===========================================================================
#  4) BERICHT
# ===========================================================================
def _bericht(ergebnisse: list[dict], ausfuehrlich: bool = False) -> int:
    befunde = [e for e in ergebnisse if e["befund"]]
    for e in ergebnisse:
        zeichen = {"NETZ": "🛑", "ROT": "❌", "ZEIT": "⏱", None: "✅"}[e["befund"]]
        print(f"{zeichen} {e['script']} ({e['dauer']:.1f}s)"
              + (f" – {e['befund']}" if e["befund"] else ""))
        for v in e["versuche"][:5]:
            print(f"     ↳ {v['art']} → {v['host']}:{v['port']} aus {v['ort']}")
        if e["befund"] and (ausfuehrlich or e["befund"] != "NETZ"):
            for zeile in e["ausgabe"].strip().splitlines()[-12:]:
                print(f"     │ {zeile}")
    print()
    if not befunde:
        print(f"✅ KI-Probe grün: {len(ergebnisse)} Selbsttest(s) urteilen ohne Modell "
              "und ohne Netz – dasselbe Ergebnis mit und ohne Schlüssel.")
        return 0
    print(f"🛑 KI-Probe: {len(befunde)} von {len(ergebnisse)} Selbsttest(s) hängen an "
          "KI/Netz oder sind unter der Sperre rot.")
    print("   Heilung: Den KI-Weg im Selbsttest über die vorhandene Attrappe führen")
    print("   (z. B. `lesbarkeit_heiler.KI_CALL`, `satz_heiler.KI_CALL`) und den")
    print("   echten Transport nie erreichen. Muster: requeue_quality_holds._KiAttrappe.")
    print("   Hintergrund: CONTENT-ENGINE-138-DAUERHEILUNG-PREMIUM-2026-10-08.md")
    return 1


# ===========================================================================
#  5) SELBSTTEST DER PROBE – Sabotage-Proben
# ===========================================================================
_PROBE_NETZ_GESCHLUCKT = '''
import sys, urllib.request
if "--selftest" in sys.argv:
    try:  # schluckt wie lesbarkeit_heiler._ki_chat jede Ausnahme
        urllib.request.urlopen("https://generativelanguage.googleapis.com/", timeout=2)
    except Exception:
        pass
    print("selbsttest grün (scheinbar)")
    sys.exit(0)
'''
_PROBE_SCHLUESSEL_SICHTBAR = '''
import os, sys
ok = all(os.environ.get(k) == "%s" for k in ("GEMINI_API_KEY", "GROQ_API_KEY"))
sys.exit(0 if ok else 5)
''' % ATTRAPPE
_PROBE_LOOPBACK = '''
import socket, sys
s = socket.socket()
try:
    s.settimeout(1)
    s.connect(("127.0.0.1", 9))   # Port zu – egal; Loopback ist erlaubt
except OSError:
    pass
finally:
    s.close()
sys.exit(0)
'''
_PROBE_ROT = 'import sys\nsys.exit(2)\n'
_PROBE_GRUEN = 'print("hermetisch")\n'


def _selftest() -> int:
    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        def probe(name: str, code: str) -> str:
            p = Path(tmp) / f"{name}.py"
            p.write_text(code, encoding="utf-8")
            return str(p)

        e = trap(probe("geschluckt", _PROBE_NETZ_GESCHLUCKT))
        if e["befund"] != "NETZ" or e["rc"] != 0:
            fehler.append(f"P1: geschluckter Netzversuch nicht erkannt ({e['befund']}, rc={e['rc']})")
        elif not any("googleapis" in v["host"] for v in e["versuche"]):
            fehler.append(f"P1: Protokoll nennt das Ziel nicht: {e['versuche']}")
        elif not any("geschluckt.py:" in v["ort"] for v in e["versuche"]):
            fehler.append(f"P1: Protokoll nennt keinen Aufrufort: {e['versuche']}")

        e = trap(probe("schluessel", _PROBE_SCHLUESSEL_SICHTBAR), args=())
        if e["befund"] is not None:
            fehler.append(f"P2: Attrappen-Schlüssel im Selbsttest nicht sichtbar (rc={e['rc']})")

        e = trap(probe("loopback", _PROBE_LOOPBACK), args=())
        if e["befund"] is not None:
            fehler.append(f"P3: Loopback fälschlich gesperrt: {e['versuche'] or e['rc']}")

        e = trap(probe("rot", _PROBE_ROT), args=())
        if e["befund"] != "ROT":
            fehler.append(f"P4: roter Selbsttest unter Sperre nicht gemeldet ({e['befund']})")

        e = trap(probe("gruen", _PROBE_GRUEN), args=())
        if e["befund"] is not None:
            fehler.append(f"P5: hermetischer Selbsttest fälschlich rot ({e['befund']})")

    # P6: Die Sperre räumt hinter sich auf (Umgebung + socket).
    vorher_connect = socket.socket.connect
    vorher_env = os.environ.get("GEMINI_API_KEY")
    with ki_sperre() as v:
        try:
            socket.getaddrinfo("example.org", 443)
        except NetzGesperrt:
            pass
    if socket.socket.connect is not vorher_connect or os.environ.get("GEMINI_API_KEY") != vorher_env:
        fehler.append("P6: ki_sperre stellt socket/Umgebung nicht wieder her")
    if not v or v[0]["host"] != "example.org":
        fehler.append(f"P6: In-Prozess-Sperre protokolliert nicht: {v}")

    # P7: Entdeckung trägt den Auslöser von #138 (sonst ist die Probe blind).
    try:
        liste = {e["script"]: e for e in entdecke()}
    except Exception as exc:  # noqa: BLE001
        fehler.append(f"P7: Entdeckung wirft: {exc}")
    else:
        rq = liste.get("scripts/requeue_quality_holds.py")
        if not rq:
            fehler.append("P7: requeue_quality_holds --selftest wird nicht entdeckt")
        elif not rq["schluessel"]:
            fehler.append("P7: Phase-0.5-Schlüssel (content-engine-v2) nicht erkannt")

    if fehler:
        print("🛑 KI-PROBE-SELBSTTEST FEHLGESCHLAGEN – die Probe ist blind:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ KI-Probe-Selbsttest grün (geschluckter Netzversuch erkannt, Attrappen-"
          "Schlüssel sichtbar, Loopback frei, Rot gemeldet, Aufräumen, Entdeckung).")
    return 0


# ===========================================================================
#  CLI
# ===========================================================================
def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["--_kind"]:
        script = argv[1]
        rest = argv[3:] if len(argv) > 2 and argv[2] == "--" else argv[2:]
        return _kind(script, rest)

    ap = argparse.ArgumentParser(description="KI-Probe für Selbsttests (#138)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--trap", metavar="SCRIPT", action="append",
                    help="Selbsttest eines Skripts unter KI-Sperre (mehrfach möglich)")
    ap.add_argument("--trap-workflows", action="store_true",
                    help="alle in Workflows aufgerufenen Selbsttests probieren")
    ap.add_argument("--nur-schluessel", action="store_true",
                    help="nur Selbsttests aus Schritten mit KI-Schlüsseln")
    ap.add_argument("--liste", action="store_true", help="nur entdecken und auflisten")
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--ausfuehrlich", action="store_true")
    a = ap.parse_args(argv)

    try:
        if a.selftest:
            return _selftest()
        if a.liste or a.trap_workflows:
            liste = entdecke()
            if a.nur_schluessel:
                liste = [e for e in liste if e["schluessel"]]
            if a.liste:
                for e in liste:
                    print(f"{'🔑' if e['schluessel'] else '  '} {e['script']} "
                          f"{' '.join(e['args'])}  ← {e['orte'][0]}"
                          + (f" (+{len(e['orte']) - 1})" if len(e["orte"]) > 1 else ""))
                print(f"\n{len(liste)} Selbsttest(s); 🔑 = läuft schon heute mit KI-Schlüssel.")
                return 0
            ergebnisse = [trap(e["script"], tuple(e["args"]), a.timeout) for e in liste]
            return _bericht(ergebnisse, a.ausfuehrlich)
        if a.trap:
            return _bericht([trap(s, ("--selftest",), a.timeout) for s in a.trap],
                            a.ausfuehrlich)
    except Exception as exc:  # noqa: BLE001 – Werkzeugfehler ist Exit 2, kein Befund
        print(f"🛑 KI-Probe: Werkzeugfehler: {exc}")
        traceback.print_exc()
        return 2
    ap.print_help()
    return 2


if __name__ == "__main__":
    sys.exit(main())
