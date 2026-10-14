#!/usr/bin/env python3
"""Messketten-Wache – kein Messlauf ohne sein Werkzeug (C38, #740).

DER BEFUND (14.10.2026, Ticket #740)
------------------------------------
Zehn Deploy-Läufe in Folge rot, kein Artikel live. Die Ursache war kein
Inhalt und kein Fehler in der Logik, sondern ein **fehlendes Wörterbuch**:
``quality_score.score_article()`` misst Rechtschreibung über ``hunspell``.
Sechs Workflows installieren das Paket, ``deploy.yml`` hat es nie getan.
Sichtbar wurde das erst an dem einen Tag, an dem der Deploy zum ersten Mal
wirklich einen Kandidaten messen musste.

Das Muster dahinter ist älter als der Befund: Die Messkette wird in jedem
Workflow **per Copy-Paste** deklariert. Wer einen Mess-Schritt in einen
Workflow stellt, muss daran denken, die apt-Zeile mitzubringen – sonst
misst der Lauf mit einem toten Werkzeug. Und eine tote Messung ist
gefährlicher als gar keine: Sie liefert eine Zahl.

DIESE WACHE SCHLIESST DIE KLASSE AUF DREI EBENEN
------------------------------------------------
1. EINE Quelle der Wahrheit  – welche Werkzeuge die Messkette braucht,
   wie man sie installiert, und ob sie JETZT vollständig ist
   (:func:`status`, :func:`require`).
2. Früher, benannter Abbruch – ``publication_release.py`` fragt VOR dem
   ersten Kandidaten; der Befund heißt dann „hunspell fehlt, Installation:
   …" statt eines Tracebacks nach dem Hugo-Build.
3. Statische Vollständigkeit – :func:`audit_workflows` liest alle
   Workflows und meldet jeden Job, der ein Messwerkzeug AUFRUFT, ohne die
   Kette vorher zu installieren. Ausnahmen müssen erklärt werden
   (``AUSNAHMEN``); eine stillschweigende Lücke gibt es nicht mehr.

WARUM ``--selftest`` NICHT ZÄHLT
--------------------------------
Selbsttests laufen im Haus grundsätzlich mit Attrappen und ohne äußere
Abhängigkeiten – dieselbe Regel, die die KI-Probe (#138) für Modelle und
Netz durchsetzt. Ein Selbsttest, der die Messkette braucht, urteilt nach
der Tagesform der Umgebung statt nach dem Code. Aufrufe mit ``--selftest``
gelten deshalb nicht als Messlauf.

Nutzung
-------
    python3 scripts/measurement_chain.py --check             # ist die Kette hier vollständig?
    python3 scripts/measurement_chain.py --audit-workflows   # wer misst ohne Werkzeug?
    python3 scripts/measurement_chain.py --installationszeile
    python3 scripts/measurement_chain.py --selftest

Exit-Codes: 0 = in Ordnung · 1 = Befund · 2 = Werkzeugfehler/Selbsttest rot
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = BLOG_DIR / ".github" / "workflows"

# --- Die Kette ------------------------------------------------------------
# EIN Ort, der weiß, womit im Haus Rechtschreibung gemessen wird.
BINARY = "hunspell"
WOERTERBUCH = "de_DE"
APT_PAKETE = ("hunspell", "hunspell-de-de")
INSTALLATIONSZEILE = f"sudo apt-get install -y -qq {' '.join(APT_PAKETE)}"

# --- Wer misst? -----------------------------------------------------------
# Einstiegspunkte, die in einem normalen Lauf die Messkette benutzen. Die
# Liste wird von `_registry_drift()` gegengelesen: Jedes Skript, das
# `spellcheck`/`quality_score` direkt importiert oder deren Messfunktionen
# aufruft, MUSS hier stehen. Damit kann die Liste nicht still verrotten.
MESSENDE_SKRIPTE: dict[str, str] = {
    "spellcheck.py": "ruft hunspell direkt auf (Rechtschreibung, Groß-/Kleinschreibung)",
    "quality_score.py": "misst `spelling` über spellcheck → hunspell",
    "publication_release.py": "accept_candidate misst jeden Kandidaten (Befund #740)",
    "requeue_quality_holds.py": "misst wartende Holds über quality_score",
    "reserve_finisher.py": "misst Reserve-Entwürfe über quality_score",
    "reserve_readiness.py": "misst Reservereife über quality_score",
    "reserve_recert.py": "zertifiziert Entwürfe mit spellcheck nach",
    "absorb_whitelist.py": "arbeitet direkt auf dem spellcheck-Wortschatz",
    "ops_report.py": "berechnet die Qualitätskennzahl des Bestands über quality_score",
    "reserve_pool.py": "löst `accept_candidate` auf und misst darüber (Pfad aus #740)",
}

# Messfunktionen, deren Aufruf ein Skript zum Messmodul macht.
MESSAUFRUFE = ("score_article(", "accept_candidate(", "analyze_article(",
               "batch_hunspell(")

# Erklärte Ausnahmen: Aufruf ohne Messkette, mit Grund. Schlüssel ist
# "<workflow>::<skript>". Eine Ausnahme ohne Grund gibt es nicht.
AUSNAHMEN: dict[str, str] = {}


class MesskettenFehler(RuntimeError):
    """Die Messkette fehlt – Werkzeugbefund, kein Inhaltsbefund (C33)."""


# ---------------------------------------------------------------------------
# Laufzeit
# ---------------------------------------------------------------------------
def status() -> dict:
    """Ist die Messkette in DIESER Umgebung vollständig?"""
    fehlend: list[str] = []
    pfad = shutil.which(BINARY)
    if not pfad:
        fehlend.append(f"{BINARY} (Programm nicht im PATH)")
        return {"vollstaendig": False, "fehlend": fehlend, "binary": None,
                "woerterbuch": WOERTERBUCH,
                "installationszeile": INSTALLATIONSZEILE}
    try:
        lauf = subprocess.run([BINARY, "-D"], input="", capture_output=True,
                              text=True, timeout=20)
        gesehen = f"{lauf.stdout}\n{lauf.stderr}"
    except (OSError, subprocess.SubprocessError) as exc:
        return {"vollstaendig": False,
                "fehlend": [f"{BINARY} startet nicht ({exc})"], "binary": pfad,
                "woerterbuch": WOERTERBUCH,
                "installationszeile": INSTALLATIONSZEILE}
    if WOERTERBUCH not in gesehen:
        fehlend.append(f"Wörterbuch {WOERTERBUCH} (hunspell kennt es nicht)")
    return {"vollstaendig": not fehlend, "fehlend": fehlend, "binary": pfad,
            "woerterbuch": WOERTERBUCH,
            "installationszeile": INSTALLATIONSZEILE}


def fehlertext(kontext: str, lage: dict | None = None) -> str:
    """Ein Satz, der sagt, was fehlt – und wie man es behebt."""
    lage = lage or status()
    fehlt = "; ".join(lage.get("fehlend") or ["unbekannt"])
    return (f"Messkette unvollständig für {kontext}: {fehlt}. "
            f"Eine ausgefallene Messung ist kein Grün (C33) – es wird nichts "
            f"angenommen. Heilung im Workflow, VOR dem Mess-Schritt: "
            f"`{lage.get('installationszeile', INSTALLATIONSZEILE)}` "
            f"(Vertrag C38, Dauerheilung #740).")


def require(kontext: str) -> dict:
    """Vorflug-Prüfung: ohne vollständige Kette wird gar nicht erst gemessen.

    Wirft :class:`MesskettenFehler`. Aufrufer übersetzen das in ihren
    Werkzeugfehler-Exit – im Haus ist das Exit 3 (Release-Crash) bzw. der
    Werkzeugzweig des Workflow-Schritts.
    """
    if os.environ.get("MESSKETTE_VORFLUG") == "aus":
        # Ausdrücklich abschaltbar für Umgebungen, die bewusst ohne Kette
        # laufen (lokale Teilprüfungen). Nie in CI gesetzt.
        return {"vollstaendig": True, "fehlend": [], "uebersprungen": True,
                "installationszeile": INSTALLATIONSZEILE}
    lage = status()
    if not lage["vollstaendig"]:
        raise MesskettenFehler(fehlertext(kontext, lage))
    return lage


# ---------------------------------------------------------------------------
# Statische Prüfung
# ---------------------------------------------------------------------------
def _registry_drift(root: Path) -> list[str]:
    """Jedes messende Skript muss in MESSENDE_SKRIPTE stehen."""
    befunde: list[str] = []
    ordner = root / "scripts"
    if not ordner.is_dir():
        return [f"{ordner} fehlt – die Messkette ist nicht prüfbar."]
    for datei in sorted(ordner.glob("*.py")):
        name = datei.name
        if name == Path(__file__).name:
            # Die Wache selbst NENNT die Messaufrufe (MESSAUFRUFE), sie führt
            # sie nicht aus. Ohne diese Zeile meldete sie sich selbst – und
            # ein Melder, der über sich selbst klagt, erzieht zum Wegsehen.
            continue
        try:
            text = datei.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        importiert = bool(re.search(
            r"^\s*(?:import|from)\s+(spellcheck|quality_score)\b", text, re.M))
        ruft = any(aufruf in text for aufruf in MESSAUFRUFE)
        # Definitionen zählen nicht als Aufruf (sonst meldet sich jedes Modul,
        # das die Funktion selbst bereitstellt).
        if ruft and not importiert:
            eigene = all(
                re.search(rf"def\s+{re.escape(aufruf[:-1])}\s*\(", text)
                for aufruf in MESSAUFRUFE if aufruf in text)
            ruft = not eigene
        if (importiert or ruft) and name not in MESSENDE_SKRIPTE:
            befunde.append(
                f"scripts/{name} misst (Import oder Messaufruf), steht aber "
                f"nicht in MESSENDE_SKRIPTE – damit prüft die Wache seine "
                f"Workflows nicht. Eintragen mit Begründung.")
    for name in MESSENDE_SKRIPTE:
        if not (ordner / name).is_file():
            befunde.append(f"MESSENDE_SKRIPTE nennt scripts/{name} – die Datei "
                           f"gibt es nicht (mehr). Eintrag nachziehen.")
    return befunde


def _workflow_jobs(text: str) -> dict:
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover - CI hat PyYAML
        raise MesskettenFehler(f"PyYAML fehlt: {exc}") from exc
    daten = yaml.safe_load(text) or {}
    return (daten.get("jobs") or {}) if isinstance(daten, dict) else {}


def _schritt_text(step: dict) -> str:
    teile = [str(step.get("run") or "")]
    mit = step.get("with")
    if isinstance(mit, dict):
        teile.extend(str(v) for v in mit.values())
    return "\n".join(teile)


def _einzelbefehle(zeile: str) -> list[str]:
    """Eine Shell-Zeile in ihre Einzelbefehle zerlegen.

    Ohne diese Zerlegung liest die Wache
    ``python3 x.py --selftest && python3 x.py --refill-only`` als einen
    einzigen Selbsttest – und übersieht den Messlauf dahinter. Genau diese
    Zeile steht im Deploy (#740).
    """
    return [t.strip() for t in re.split(r"&&|\|\||\||;", zeile) if t.strip()]


def messaufrufe_im_schritt(text: str) -> list[str]:
    """Welche messenden Skripte ruft dieser Schritt an – ohne --selftest?"""
    treffer: list[str] = []
    for zeile in text.splitlines():
        nackt = zeile.strip()
        if not nackt or nackt.startswith("#"):
            continue
        for befehl in _einzelbefehle(nackt):
            for name in MESSENDE_SKRIPTE:
                if f"scripts/{name}" not in befehl:
                    continue
                # Selbsttests laufen mit Attrappen (siehe Modul-Dokumentation).
                if "--selftest" in befehl.split(f"scripts/{name}", 1)[1]:
                    continue
                treffer.append(name)
    return treffer


def audit_workflows(root: Path | None = None) -> list[str]:
    """Jeder Job, der misst, muss die Messkette vorher installieren."""
    basis = Path(root) if root else BLOG_DIR
    befunde = _registry_drift(basis)
    ordner = basis / ".github" / "workflows"
    if not ordner.is_dir():
        return befunde + [f"{ordner} fehlt – keine Workflows prüfbar."]
    for datei in sorted(ordner.glob("*.yml")):
        text = datei.read_text(encoding="utf-8", errors="replace")
        try:
            jobs = _workflow_jobs(text)
        except Exception as exc:  # noqa: BLE001 – unlesbarer Workflow ist Befund
            befunde.append(f"{datei.name}: nicht lesbar ({exc})")
            continue
        # Der Abschalter ist für lokale Teilprüfungen gedacht. Steht er in
        # einem Workflow, ist die Wache dort abgeschaltet – und niemand sieht
        # es. Das wäre ein stiller Bypass (C2: kein Scheingrün).
        if "MESSKETTE_VORFLUG" in text:
            befunde.append(
                f"{datei.name}: setzt MESSKETTE_VORFLUG – der Vorflug der "
                f"Messkette wäre in CI abgeschaltet. Der Abschalter gehört "
                f"auf lokale Rechner, nicht in einen Lauf, der veröffentlicht "
                f"(#740).")
        for jobname, job in (jobs or {}).items():
            if not isinstance(job, dict):
                continue
            steps = [s for s in (job.get("steps") or []) if isinstance(s, dict)]
            kette_ab = None
            for index, step in enumerate(steps):
                blob = _schritt_text(step)
                if kette_ab is None and BINARY in blob and (
                        "apt-get" in blob or "apt " in blob):
                    kette_ab = index
                for skript in dict.fromkeys(messaufrufe_im_schritt(blob)):
                    schluessel = f"{datei.name}::{skript}"
                    if schluessel in AUSNAHMEN:
                        continue
                    if kette_ab is not None and kette_ab <= index:
                        continue
                    name = step.get("name") or step.get("uses") or f"Schritt {index + 1}"
                    befunde.append(
                        f"{datei.name} · Job `{jobname}` · „{name}“ ruft "
                        f"scripts/{skript} auf ({MESSENDE_SKRIPTE[skript]}), "
                        f"aber in diesem Job wird die Messkette vorher nicht "
                        f"installiert. Genau das war Befund #740: Die Messung "
                        f"läuft, das Werkzeug fehlt – das Ergebnis ist keine "
                        f"Zahl, sondern ein Ausfall. Heilung: `"
                        f"{INSTALLATIONSZEILE}` in einen früheren Schritt "
                        f"desselben Jobs (oder Ausnahme in "
                        f"scripts/measurement_chain.py:AUSNAHMEN begründen).")
    return befunde


# ---------------------------------------------------------------------------
# Selbsttest
# ---------------------------------------------------------------------------
def _selftest() -> int:
    import tempfile
    import textwrap

    fehler: list[str] = []

    # 1) Der echte Stand: kein Workflow misst ohne Kette.
    echte = audit_workflows()
    if echte:
        fehler.append(f"Workflow-Audit rot ({len(echte)} Befunde) – "
                      f"erster: {echte[0][:200]}")

    # 2) status() urteilt ohne Absturz, egal ob das Werkzeug da ist.
    lage = status()
    for schluessel in ("vollstaendig", "fehlend", "installationszeile"):
        if schluessel not in lage:
            fehler.append(f"status() ohne Schlüssel `{schluessel}`")
    if lage["vollstaendig"] and lage["fehlend"]:
        fehler.append("status() meldet vollständig UND fehlende Teile")

    # 3) require() wirft genau dann, wenn etwas fehlt – mit Heilungsweg.
    echt_binary = shutil.which(BINARY)
    if echt_binary is None:
        try:
            require("Selbsttest")
            fehler.append("require() wirft nicht, obwohl hunspell fehlt")
        except MesskettenFehler as exc:
            if INSTALLATIONSZEILE not in str(exc):
                fehler.append("require()-Meldung nennt die Installationszeile nicht")
            if "C33" not in str(exc):
                fehler.append("require()-Meldung nennt den Vertrag nicht")
    else:
        try:
            require("Selbsttest")
        except MesskettenFehler as exc:
            fehler.append(f"require() wirft trotz vollständiger Kette: {exc}")

    # 4) Abschalter wirkt (und nur er).
    alt = os.environ.get("MESSKETTE_VORFLUG")
    os.environ["MESSKETTE_VORFLUG"] = "aus"
    try:
        if not require("Selbsttest").get("uebersprungen"):
            fehler.append("MESSKETTE_VORFLUG=aus wird ignoriert")
    except MesskettenFehler:
        fehler.append("MESSKETTE_VORFLUG=aus hebt den Vorflug nicht auf")
    finally:
        os.environ.pop("MESSKETTE_VORFLUG", None)
        if alt is not None:
            os.environ["MESSKETTE_VORFLUG"] = alt

    # 5) Aufruf-Erkennung: Messlauf ja, Selbsttest nein.
    proben = [
        ("python3 scripts/publication_release.py --refill-only", ["publication_release.py"]),
        ("python3 scripts/publication_release.py --selftest", []),
        ("python3 scripts/publication_release.py --selftest && "
         "python3 scripts/publication_release.py --refill-only",
         ["publication_release.py"]),
        ("# python3 scripts/ops_report.py", []),
        ("python3 scripts/ops_report.py > ops-report.json", ["ops_report.py"]),
    ]
    for zeile, erwartet in proben:
        ist = messaufrufe_im_schritt(zeile)
        if ist != erwartet:
            fehler.append(f"Aufruf-Erkennung falsch bei {zeile!r}: "
                          f"{ist} statt {erwartet}")

    # 6) Sabotageproben gegen eine Attrappen-Werkbank.
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        (wurzel / "scripts").mkdir()
        (wurzel / ".github" / "workflows").mkdir(parents=True)
        for name in MESSENDE_SKRIPTE:
            (wurzel / "scripts" / name).write_text("# Attrappe\n", encoding="utf-8")

        def schreibe(inhalt: str) -> list[str]:
            (wurzel / ".github" / "workflows" / "probe.yml").write_text(
                textwrap.dedent(inhalt), encoding="utf-8")
            return [b for b in audit_workflows(root=wurzel)
                    if "probe.yml" in b]

        ohne_kette = schreibe("""
            name: Probe
            jobs:
              bau:
                steps:
                  - name: Messen
                    run: python3 scripts/publication_release.py --refill-only
            """)
        if not ohne_kette:
            fehler.append("Sabotage „Messlauf ohne Kette“ blieb unentdeckt – "
                          "genau der Befund aus #740.")

        mit_kette = schreibe("""
            name: Probe
            jobs:
              bau:
                steps:
                  - name: Abhängigkeiten
                    run: sudo apt-get install -y -qq hunspell hunspell-de-de
                  - name: Messen
                    run: python3 scripts/publication_release.py --refill-only
            """)
        if mit_kette:
            fehler.append(f"Falschalarm trotz installierter Kette: {mit_kette}")

        falsche_reihenfolge = schreibe("""
            name: Probe
            jobs:
              bau:
                steps:
                  - name: Messen
                    run: python3 scripts/publication_release.py --refill-only
                  - name: Abhängigkeiten
                    run: sudo apt-get install -y -qq hunspell hunspell-de-de
            """)
        if not falsche_reihenfolge:
            fehler.append("Kette NACH dem Messlauf gilt als in Ordnung – "
                          "die Reihenfolge wird nicht geprüft.")

        fremder_job = schreibe("""
            name: Probe
            jobs:
              vorbereiten:
                steps:
                  - name: Abhängigkeiten
                    run: sudo apt-get install -y -qq hunspell hunspell-de-de
              bau:
                steps:
                  - name: Messen
                    run: python3 scripts/publication_release.py --refill-only
            """)
        if not fremder_job:
            fehler.append("Kette in einem ANDEREN Job gilt als installiert – "
                          "Jobs teilen sich keine Runner.")

        abschalter = schreibe("""
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
        if not abschalter:
            fehler.append("Ein Workflow darf den Vorflug nicht abschalten – "
                          "der stille Bypass bleibt unentdeckt.")

        nur_selftest = schreibe("""
            name: Probe
            jobs:
              bau:
                steps:
                  - name: Probe
                    run: python3 scripts/reserve_pool.py --selftest
            """)
        if nur_selftest:
            fehler.append(f"Selbsttest wird als Messlauf gewertet: {nur_selftest}")

        # Registry-Drift: ein neues messendes Skript muss auffallen.
        (wurzel / "scripts" / "neuer_messer.py").write_text(
            "import quality_score as qs\n", encoding="utf-8")
        drift = [b for b in audit_workflows(root=wurzel) if "neuer_messer" in b]
        if not drift:
            fehler.append("Neues messendes Skript fällt nicht auf – die "
                          "Registry kann still verrotten.")

    if fehler:
        print("🛑 MESSKETTEN-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Messketten-Selbsttest grün (Laufzeit-Status, Vorflug, "
          "Aufruf-Erkennung, 7 Sabotageproben, Registry-Drift).")
    return 0


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        return _selftest()
    if "--installationszeile" in args:
        print(INSTALLATIONSZEILE)
        return 0
    if "--audit-workflows" in args:
        befunde = audit_workflows()
        if befunde:
            print(f"🛑 MESSKETTE UNVOLLSTÄNDIG ({len(befunde)} Befund(e)) – "
                  f"C38, Dauerheilung #740:")
            for b in befunde:
                print(f"   - {b}")
            return 1
        print(f"✅ Messkette vollständig verdrahtet: Jeder Job, der eines von "
              f"{len(MESSENDE_SKRIPTE)} Mess-Skripten aufruft, installiert sie "
              f"vorher.")
        return 0
    lage = status()
    if lage["vollstaendig"]:
        print(f"✅ Messkette vollständig: {BINARY} ({lage['binary']}) "
              f"inkl. Wörterbuch {WOERTERBUCH}.")
        return 0
    print(f"🛠 {fehlertext('diese Umgebung', lage)}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
