#!/usr/bin/env python3
"""Blustradius-Register der Auslieferung – Wache zum Vertrag C38 (#740).

DER BEFUND, DER DIESE WACHE ERZWUNGEN HAT
-----------------------------------------
09.10.2026 (#676): Die Release-Scorecard starb an einem Mess-Befund und fror
die öffentliche Auslieferung 19 h 38 min ein. Heilung: EIN Schritt wertet
seinen Exit-Code aus.

14.10.2026 (#740): Die Quote-Nachfüllung starb daran, dass im deploy-Job
``hunspell`` fehlte – zehn rote Läufe, kein Artikel live. Heilung: EIN
Schritt wertet seinen Exit-Code aus.

Zweimal dieselbe Klasse, zweimal eine Einzelfallheilung. Der deploy-Job hat
63 Schritte; 61 davon stehen VOR dem Upload des Pages-Artefakts. Jeder von
ihnen kann die Live-Site einfrieren, und für 59 davon hatte nie jemand
aufgeschrieben, ob er das DARF.

Diese Wache dreht die Beweislast um (fail-closed):

  * ``data/blustradius-deploy.yml`` erklärt für JEDEN Schritt, was sein
    rotes Ergebnis bedeutet – ``infra``, ``inhalt``, ``gate-selbsttest``
    oder ``werkzeug``.
  * Ein neuer Schritt ohne Eintrag macht diese Wache rot. Wer einen Schritt
    in den Auslieferungsweg stellt, trifft die Blustradius-Entscheidung
    bewusst.
  * Ein ``werkzeug``-Schritt, der hart abbrechen kann, macht sie ebenfalls
    rot – samt Dateizeile und Heilungsweg.
  * Ein Inhalts-Gate mit eigenem Werkzeug-Exit (``werkzeugzweig``) muss
    diesen Zweig auswerten, statt ihn durchzureichen.

Der Bot-Watchdog liest dasselbe Register: Meldet er „Auslieferung
blockiert", nennt er die KLASSE des blockierenden Schritts – Inhalts-Gate
(fachlich gemeint) oder Werkzeug-Blockade (darf nicht blockieren, Heilung
hier). Vorher stand im Ticket eine Frage, jetzt steht dort ein Urteil.

Nutzung
-------
    python3 scripts/blustradius_register.py --check      # Vertrag prüfen
    python3 scripts/blustradius_register.py --tabelle    # Register als Tabelle
    python3 scripts/blustradius_register.py --klasse "<Schrittname>"
    python3 scripts/blustradius_register.py --selftest   # Positiv + Sabotage

Exit-Codes: 0 = Vertrag erfüllt · 1 = Befund · 2 = Selbsttest/Werkzeugfehler
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

BLOG_DIR = Path(__file__).resolve().parents[1]
REGISTER = BLOG_DIR / "data" / "blustradius-deploy.yml"

KLASSEN = ("infra", "inhalt", "gate-selbsttest", "werkzeug")
# Klassen, die die öffentliche Auslieferung anhalten dürfen. `werkzeug` fehlt
# hier bewusst – das IST der Vertrag (C34/C38).
DARF_BLOCKIEREN = ("infra", "inhalt", "gate-selbsttest")

# Aufrufe, die in einem Shell-Block scheitern und damit den Schritt töten
# können. Bewusst eng: Es geht um Werkzeuge, nicht um `echo`.
WERKZEUG_AUFRUF = re.compile(
    r"^\s*(?:sudo\s+)?(python3?|npm|npx|hugo|pagefind|apt-get|git\s+push|"
    r"curl|wget|node)\b")
HARTER_EXIT = re.compile(r'^\s*exit\s+(?!0\s*$)(\d+|"?\$[\w{}]+"?)')


class RegisterFehler(RuntimeError):
    """Das Register selbst ist unlesbar – Werkzeugfehler, kein Inhaltsbefund."""


# ---------------------------------------------------------------------------
# Laden
# ---------------------------------------------------------------------------
def _yaml():
    try:
        import yaml  # noqa: PLC0415 – optional, damit der Import nie tötet
    except ImportError as exc:  # pragma: no cover - CI hat PyYAML
        raise RegisterFehler(f"PyYAML fehlt: {exc}") from exc
    return yaml


def lade_register(pfad: Path | None = None) -> dict:
    """Register-Datei lesen (ohne Bewertung)."""
    ziel = Path(pfad) if pfad else REGISTER
    if not ziel.is_file():
        raise RegisterFehler(f"{ziel} fehlt – ohne Register ist der "
                             f"Blustradius-Vertrag nicht prüfbar.")
    daten = _yaml().safe_load(ziel.read_text(encoding="utf-8")) or {}
    if not isinstance(daten, dict) or not isinstance(daten.get("schritte"), list):
        raise RegisterFehler(f"{ziel}: kein gültiges Register "
                             f"(Schlüssel `schritte:` fehlt oder ist keine Liste).")
    return daten


def lade_workflow(root: Path | None = None, register: dict | None = None):
    """(Workflow-Daten, Rohtext) des im Register benannten Workflows."""
    basis = Path(root) if root else BLOG_DIR
    reg = register if register is not None else lade_register()
    rel = reg.get("workflow") or ".github/workflows/deploy.yml"
    pfad = basis / rel
    if not pfad.is_file():
        raise RegisterFehler(f"{rel} fehlt – der Auslieferungsweg ist nicht prüfbar.")
    text = pfad.read_text(encoding="utf-8")
    daten = _yaml().safe_load(text) or {}
    return daten, text


def schritte_des_jobs(workflow: dict, job: str) -> list[dict]:
    jobs = (workflow or {}).get("jobs") or {}
    return [s for s in ((jobs.get(job) or {}).get("steps") or [])
            if isinstance(s, dict)]


def schrittname(step: dict) -> str:
    """Wirksamer Name – genau das, was GitHub (und die Jobs-API) anzeigt."""
    return str(step.get("name") or step.get("uses") or "").strip()


# ---------------------------------------------------------------------------
# Klassifizierung (API für den Bot-Watchdog)
# ---------------------------------------------------------------------------
def klassifiziere(name: str, register: dict | None = None) -> dict:
    """Klasse eines Schrittnamens – die Auskunft, die im Ticket landet.

    Rückgabe: ``{"name", "klasse", "grund", "darf_blockieren", "bekannt"}``.
    Ein unbekannter Name ist NIE ein stilles „alles gut": `bekannt=False`
    heißt, dass der Watchdog weiter die neutrale Formulierung nutzt.
    """
    leer = {"name": name, "klasse": "unbekannt", "grund": "",
            "darf_blockieren": None, "bekannt": False}
    if not name:
        return leer
    try:
        reg = register if register is not None else lade_register()
    except RegisterFehler:
        return leer
    gesucht = str(name).strip()
    for eintrag in reg.get("schritte") or []:
        if not isinstance(eintrag, dict):
            continue
        if str(eintrag.get("name") or "").strip() != gesucht:
            continue
        klasse = str(eintrag.get("klasse") or "unbekannt")
        return {"name": gesucht,
                "klasse": klasse,
                "grund": " ".join(str(eintrag.get("grund") or "").split()),
                "darf_blockieren": klasse in DARF_BLOCKIEREN,
                "bekannt": True}
    return leer


def urteil(name: str, register: dict | None = None) -> str:
    """Ein Satz für Ticket und Log – was die Klasse praktisch bedeutet."""
    info = klassifiziere(name, register)
    if not info["bekannt"]:
        return ("Dieser Schritt steht in keinem Blustradius-Register "
                "(data/blustradius-deploy.yml) – Klasse unbekannt. Prüfen, ob "
                "er ein Inhalts-Gate (fachlich gemeint) oder ein Mess-Schritt "
                "ist; Mess-Schritte dürfen die Auslieferung nie blockieren "
                "(C34/C38).")
    if info["klasse"] == "werkzeug":
        return ("WERKZEUG-BLOCKADE: Dieser Schritt ist ein Mess-/Melde-Schritt "
                "ohne Inhaltsentscheid – er DARF die Auslieferung nicht "
                "blockieren (Verträge C34/C38). Dass er es tut, ist der Befund: "
                "Exit-Code im Schritt auswerten, Befund über "
                "`scripts/werkzeugbefund.py --melden` an `release-seal` geben. "
                f"Registereintrag: {info['grund']}")
    if info["klasse"] == "gate-selbsttest":
        return ("GATE-SELBSTTEST: Ein Inhalts-Gate ist nicht lauffähig. "
                "Fail-closed ist hier gewollt (ungeprüfter Bestand geht nicht "
                "live, C2/C33) – die Heilung ist das Werkzeug, nicht die "
                f"Auslieferung. Registereintrag: {info['grund']}")
    if info["klasse"] == "inhalt":
        return ("INHALTS-GATE: Der Befund ist fachlich gemeint – die "
                "Auslieferung steht zu Recht. Heilung über den Fachkanal des "
                f"Gates, nicht über den Deploy. Registereintrag: {info['grund']}")
    return ("INFRASTRUKTUR: Ohne diesen Schritt gibt es keinen "
            f"Auslieferungsstand. Registereintrag: {info['grund']}")


# ---------------------------------------------------------------------------
# Shell-Analyse: Kann dieser Schritt den Job röten?
# ---------------------------------------------------------------------------
def _logische_zeilen(run: str) -> list[str]:
    """Fortsetzungszeilen (`\\`) zusammenziehen – sonst liest die Wache
    `python3 foo \\` ohne das `|| echo` der Folgezeile."""
    zeilen: list[str] = []
    puffer = ""
    for roh in (run or "").splitlines():
        teil = roh.rstrip()
        if puffer:
            puffer += " " + teil.strip()
        else:
            puffer = teil
        if puffer.endswith("\\"):
            puffer = puffer[:-1].rstrip()
            continue
        zeilen.append(puffer)
        puffer = ""
    if puffer:
        zeilen.append(puffer)
    return zeilen


def harte_stellen(step: dict) -> list[str]:
    """Stellen, an denen dieser Schritt den Job rot machen kann.

    Bewusst konservativ: Was die Wache nicht beweisen kann, gilt als hart.
    Ein falsch-positiver Befund kostet eine Zeile Erklärung – ein
    falsch-negativer kostet die Live-Site (#676/#740).
    """
    if step.get("continue-on-error") in (True, "true"):
        return []
    run = step.get("run")
    if not run:
        # `uses:`-Schritte sind Fremdcode – sie können immer röten.
        return [f"uses: {step.get('uses')}"] if step.get("uses") else []
    befunde: list[str] = []
    fehler_toleranz = False  # innerhalb von `set +e`
    for zeile in _logische_zeilen(run):
        nackt = zeile.strip()
        if not nackt or nackt.startswith("#"):
            continue
        if re.match(r"^set\s+[-+][a-zA-Z]*e", nackt):
            fehler_toleranz = nackt.startswith("set +")
            continue
        if HARTER_EXIT.match(nackt):
            befunde.append(nackt)
            continue
        if fehler_toleranz:
            continue
        if not WERKZEUG_AUFRUF.match(nackt):
            continue
        # Toleranzmuster: `|| …`, `&& …` in einer if-Bedingung, `if ! cmd`
        if "||" in nackt or nackt.startswith("if ") or nackt.startswith("elif "):
            continue
        if re.search(r"\$\(\s*", nackt) and not nackt.startswith("$("):
            # Kommandosubstitution in einer Zuweisung bricht ohne -e nicht ab,
            # mit -e aber schon – daher trotzdem melden.
            pass
        befunde.append(nackt)
    return befunde


def wertet_exitcode_aus(step: dict) -> bool:
    """Fängt der Schritt den Exit-Code seines Werkzeugs überhaupt ein?"""
    run = step.get("run") or ""
    return "$?" in run or "PIPESTATUS" in run


def meldet_werkzeugbefund(step: dict, helfer: str) -> bool:
    run = step.get("run") or ""
    return (helfer in run) or ("werkzeugfehler=true" in run)


# ---------------------------------------------------------------------------
# Prüfung
# ---------------------------------------------------------------------------
def pruefe(root: Path | None = None, register_pfad: Path | None = None) -> list[str]:
    """Alle Befunde des Blustradius-Vertrags (leer = grün)."""
    basis = Path(root) if root else BLOG_DIR
    reg = lade_register(register_pfad or (basis / "data" / "blustradius-deploy.yml"))
    workflow, roh = lade_workflow(basis, reg)
    job = str(reg.get("job") or "deploy")
    helfer = str(reg.get("befund_helfer") or "scripts/werkzeugbefund.py")
    steps = schritte_des_jobs(workflow, job)
    befunde: list[str] = []

    if not steps:
        return [f"{reg.get('workflow')}: Job `{job}` hat keine Schritte – "
                f"der Auslieferungsweg ist nicht prüfbar."]

    eintraege: dict[str, dict] = {}
    for eintrag in reg.get("schritte") or []:
        if not isinstance(eintrag, dict):
            befunde.append(f"Register: Eintrag ist kein Abschnitt: {eintrag!r}")
            continue
        name = str(eintrag.get("name") or "").strip()
        if not name:
            befunde.append("Register: Eintrag ohne `name:` – nicht zuordenbar.")
            continue
        if name in eintraege:
            befunde.append(f"Register: `{name}` ist doppelt eingetragen – "
                           f"welcher Eintrag gilt?")
        eintraege[name] = eintrag

    namen_workflow = [schrittname(s) for s in steps]

    # (1) Vollständigkeit: jeder Schritt erklärt seinen Blustradius ----------
    for index, step in enumerate(steps, 1):
        name = namen_workflow[index - 1]
        if name not in eintraege:
            befunde.append(
                f"Schritt {index} „{name}“ steht in keinem Blustradius-Register. "
                f"Fail-closed (C38): Wer einen Schritt in den Auslieferungsweg "
                f"stellt, erklärt in data/blustradius-deploy.yml, was sein rotes "
                f"Ergebnis bedeutet – `infra`, `inhalt`, `gate-selbsttest` oder "
                f"`werkzeug`.")

    # (2) Kein toter Eintrag (Register verrottet sonst still) ---------------
    for name in eintraege:
        if name not in namen_workflow:
            befunde.append(
                f"Register nennt „{name}“ – im Job `{job}` gibt es diesen "
                f"Schritt nicht (mehr). Umbenannt oder entfernt? Eintrag "
                f"nachziehen, sonst erklärt das Register einen Phantom-Schritt.")

    # (3) Klassen-Regeln ----------------------------------------------------
    for index, step in enumerate(steps, 1):
        name = namen_workflow[index - 1]
        eintrag = eintraege.get(name)
        if not eintrag:
            continue
        klasse = str(eintrag.get("klasse") or "").strip()
        grund = " ".join(str(eintrag.get("grund") or "").split())
        if klasse not in KLASSEN:
            befunde.append(f"Schritt {index} „{name}“: Klasse `{klasse or '—'}` "
                           f"ist unbekannt (erlaubt: {', '.join(KLASSEN)}).")
            continue
        if len(grund) < 25:
            befunde.append(f"Schritt {index} „{name}“: `grund:` fehlt oder ist "
                           f"zu dünn. Eine Klasse ohne Begründung ist eine "
                           f"Behauptung, kein Vertrag.")
        if klasse == "gate-selbsttest" and not str(eintrag.get("schuetzt") or "").strip():
            befunde.append(f"Schritt {index} „{name}“: `schuetzt:` fehlt – ein "
                           f"Selbsttest ohne benanntes Gate ist nicht prüfbar.")
        if klasse == "gate-selbsttest":
            geschuetzt = str(eintrag.get("schuetzt") or "").strip()
            if geschuetzt and geschuetzt not in namen_workflow:
                befunde.append(f"Schritt {index} „{name}“: schützt „{geschuetzt}“ "
                               f"– diesen Schritt gibt es im Job nicht.")

        erklaerte_id = str(eintrag.get("id") or "").strip()
        if erklaerte_id and str(step.get("id") or "").strip() != erklaerte_id:
            befunde.append(f"Schritt {index} „{name}“: Register erwartet "
                           f"`id: {erklaerte_id}`, der Workflow hat "
                           f"`{step.get('id') or '—'}`.")

        if klasse == "werkzeug":
            hart = harte_stellen(step)
            if hart:
                befunde.append(
                    f"GEISELHAFTUNG – Schritt {index} „{name}“ ist als "
                    f"`werkzeug` erklärt, kann den deploy-Job aber hart rot "
                    f"machen: {hart[0]!r}. Genau diese Bauweise fror die "
                    f"Live-Site am 09.10. (#676) und am 14.10.2026 (#740) ein. "
                    f"Heilung: Exit-Code mit `set +e`/`$?` einfangen, Befund "
                    f"über `{helfer} --melden` an `release-seal` geben, Schritt "
                    f"mit 0 beenden.")
            if eintrag.get("meldet") is not False and not meldet_werkzeugbefund(step, helfer):
                befunde.append(
                    f"Schritt {index} „{name}“ ist `werkzeug`, meldet seinen "
                    f"Befund aber nirgendwohin. Ein Werkzeugfehler, der nicht "
                    f"ans Siegel geht, ist ein stiller Messverzicht (C2/C33): "
                    f"`{helfer} --melden` aufrufen oder `meldet: false` mit "
                    f"Begründung eintragen.")

        zweig = eintrag.get("werkzeugzweig")
        if zweig is not None:
            run = step.get("run") or ""
            if not wertet_exitcode_aus(step):
                befunde.append(
                    f"Schritt {index} „{name}“: `werkzeugzweig: {zweig}` "
                    f"erklärt einen Werkzeug-Exit, der Schritt fängt seinen "
                    f"Exit-Code aber nicht ein (`$?`).")
            if re.search(r'^\s*exit\s+"?\$', run, re.M):
                befunde.append(
                    f"GEISELHAFTUNG – Schritt {index} „{name}“ reicht seinen "
                    f"Exit-Code unevaluiert durch (`exit \"$…\"`). Damit "
                    f"blockiert auch Exit {zweig} (Werkzeugfehler) die "
                    f"Auslieferung – Klasse #676/#740. Heilung: nur den "
                    f"Inhaltsbefund hart beenden, den Werkzeugzweig melden.")
            if not meldet_werkzeugbefund(step, helfer):
                befunde.append(
                    f"Schritt {index} „{name}“: der Werkzeugzweig (Exit "
                    f"{zweig}) meldet nichts an das Siegel – `{helfer} "
                    f"--melden` fehlt.")
            if "exit 1" not in run:
                befunde.append(
                    f"Schritt {index} „{name}“: der INHALTSZWEIG beendet den "
                    f"Schritt nicht mehr hart (`exit 1`). Ein Inhaltsbefund "
                    f"MUSS die Auslieferung stoppen – sonst ginge Ungeprüftes "
                    f"live (C33).")

    # (4) Reihenfolge: nach dem Upload darf nichts mehr röten ---------------
    artefakt = str(reg.get("artefakt_schritt") or "").strip()
    beleg = str(reg.get("beleg_schritt") or "").strip()
    if artefakt and artefakt not in namen_workflow:
        befunde.append(f"Der Upload-Schritt „{artefakt}“ fehlt im Job `{job}` – "
                       f"ohne ihn gibt es keine öffentliche Auslieferung.")
    elif artefakt:
        pos_artefakt = namen_workflow.index(artefakt)
        for index, step in enumerate(steps[pos_artefakt + 1:], pos_artefakt + 2):
            name = namen_workflow[index - 1]
            if name == beleg:
                continue
            befunde.append(
                f"Schritt {index} „{name}“ läuft NACH dem Artefakt-Upload. "
                f"Jeder spätere Schritt kann die bereits unterwegs befindliche "
                f"Veröffentlichung wieder rot machen (C34, #676).")
        if beleg and beleg in namen_workflow and \
                namen_workflow.index(beleg) < pos_artefakt:
            befunde.append(f"Der Auslieferungs-Beleg „{beleg}“ steht VOR dem "
                           f"Upload – er belegt dann nichts.")

    # (5) Sammler + Siegel: der Befund muss ankommen ------------------------
    sammler = str(reg.get("befund_sammler") or "").strip()
    output = str(reg.get("befund_output") or "werkzeugbefunde").strip()
    if sammler and sammler not in namen_workflow:
        befunde.append(f"Der Sammler-Schritt „{sammler}“ fehlt im Job `{job}` – "
                       f"gemeldete Werkzeugbefunde erreichen das Siegel nie.")
    elif sammler and artefakt in namen_workflow and \
            namen_workflow.index(sammler) > namen_workflow.index(artefakt):
        befunde.append(f"Der Sammler „{sammler}“ steht nach dem Artefakt-Upload "
                       f"– er darf dort nicht stehen (C34).")
    if not (BLOG_DIR / helfer).is_file() and not (basis / helfer).is_file():
        befunde.append(f"{helfer} fehlt – ohne Melder gibt es keinen "
                       f"einheitlichen Weg vom Werkzeugfehler zum Siegel.")
    job_outputs = ((workflow.get("jobs") or {}).get(job) or {}).get("outputs") or {}
    if output not in job_outputs:
        befunde.append(f"Job `{job}` gibt `{output}` nicht als Output heraus – "
                       f"das Siegel kann die Werkzeugbefunde nicht lesen.")
    siegel_job = str(reg.get("siegel_job") or "release-seal")
    siegel_steps = schritte_des_jobs(workflow, siegel_job)
    if not siegel_steps:
        befunde.append(f"Job `{siegel_job}` fehlt – ein Werkzeugbefund bliebe "
                       f"ohne roten Lauf (C34).")
    else:
        siegel_text = "\n".join(str(s.get("run") or "") for s in siegel_steps)
        siegel_env = " ".join(str((s.get("env") or {})) for s in siegel_steps)
        if output not in siegel_env:
            befunde.append(f"Job `{siegel_job}` bekommt `{output}` nicht in die "
                           f"Umgebung – der Befund erreicht das Siegel nicht.")
        if "WERKZEUGBEFUNDE" not in siegel_text.upper():
            befunde.append(f"Job `{siegel_job}` wertet die Werkzeugbefunde nicht "
                           f"aus – gemeldet, aber nie beurteilt.")
        if "exit 1" not in siegel_text:
            befunde.append(f"Job `{siegel_job}` beendet den Lauf nicht rot – "
                           f"ein Werkzeugbefund bliebe folgenlos.")

    # (6) Der Watchdog muss das Register kennen -----------------------------
    wache = basis / "scripts" / "bot_watchdog.py"
    if wache.is_file():
        text = wache.read_text(encoding="utf-8")
        if "blustradius_register" not in text:
            befunde.append(
                "bot_watchdog.py liest das Blustradius-Register nicht – dann "
                "steht im Ticket wieder die Frage „Inhalts-Gate oder "
                "Mess-Schritt?“ statt der Antwort (#740).")
    return befunde


# ---------------------------------------------------------------------------
# Darstellung
# ---------------------------------------------------------------------------
def tabelle(register: dict | None = None) -> str:
    reg = register if register is not None else lade_register()
    zeilen = ["| # | Schritt | Klasse | Darf die Auslieferung anhalten? |",
              "|---|---|---|---|"]
    for nr, eintrag in enumerate(reg.get("schritte") or [], 1):
        if not isinstance(eintrag, dict):
            continue
        klasse = str(eintrag.get("klasse") or "—")
        darf = "ja" if klasse in DARF_BLOCKIEREN else "**nein**"
        if eintrag.get("werkzeugzweig") is not None:
            darf += f" (außer Exit {eintrag['werkzeugzweig']}: Werkzeug)"
        name = str(eintrag.get("name") or "—").replace("|", "\\|")
        zeilen.append(f"| {nr} | {name} | `{klasse}` | {darf} |")
    return "\n".join(zeilen)


# ---------------------------------------------------------------------------
# Selbsttest – Positivprobe UND Sabotage
# ---------------------------------------------------------------------------
def _selftest() -> int:
    import copy
    import tempfile

    fehler: list[str] = []

    # 1) Positivprobe: Der echte Stand muss grün sein.
    try:
        echte = pruefe()
    except RegisterFehler as exc:
        print(f"🛑 Register nicht lesbar: {exc}")
        return 2
    if echte:
        fehler.append(f"Positivprobe rot ({len(echte)} Befunde) – "
                      f"erster: {echte[0][:160]}")

    reg = lade_register()
    workflow, _ = lade_workflow()
    steps = schritte_des_jobs(workflow, str(reg.get("job") or "deploy"))
    namen = [schrittname(s) for s in steps]

    # 2) Klassifizierung liefert Urteile statt Fragen.
    quote = klassifiziere("Quote-Nachfüllung nach Gate-Verlust (Re-Queue + Reserve → Min)", reg)
    if quote["klasse"] != "werkzeug" or quote["darf_blockieren"] is not False:
        fehler.append("Die Quote-Nachfüllung ist nicht als `werkzeug` erklärt – "
                      "genau der Schritt aus #740.")
    gate = klassifiziere("Publish-Gate (harte Qualitäts-, Affiliate-, Fakten- und YMYL-Freigaben)", reg)
    if gate["klasse"] != "inhalt" or gate["darf_blockieren"] is not True:
        fehler.append("Das Publish-Gate ist nicht als blockierendes Inhalts-Gate erklärt.")
    if klassifiziere("Schritt, den es nie gab", reg)["bekannt"]:
        fehler.append("Unbekannte Schritte gelten als bekannt – das Register lügt.")
    if "WERKZEUG-BLOCKADE" not in urteil(quote["name"], reg):
        fehler.append("Das Urteil zur Quote-Nachfüllung nennt die Werkzeug-Blockade nicht.")
    if "INHALTS-GATE" not in urteil(gate["name"], reg):
        fehler.append("Das Urteil zum Publish-Gate nennt den Inhaltsbefund nicht.")

    # 3) Shell-Analyse: harte Stellen müssen erkannt werden.
    proben = [
        ({"run": 'python3 scripts/x.py\n'}, True, "nackter Aufruf"),
        ({"run": 'python3 scripts/x.py || echo "⚠"\n'}, False, "toleranter Aufruf"),
        ({"run": 'set +e\npython3 scripts/x.py\ncode=$?\nset -e\n'}, False, "set +e"),
        ({"run": 'set +e\npython3 x.py\ncode=$?\nset -e\nexit "$code"\n'}, True, "durchgereicht"),
        ({"run": 'set +e\npython3 x.py\ncode=$?\nset -e\nexit 2\n'}, True, "harter exit 2"),
        ({"run": 'set +e\npython3 x.py\ncode=$?\nset -e\nexit 0\n'}, False, "exit 0"),
        ({"run": 'python3 a.py \\\n  --flag \\\n  || echo "⚠"\n'}, False, "Fortsetzungszeilen"),
        ({"run": 'if ! python3 x.py --selftest; then\n  echo hi\nfi\n'}, False, "if-Bedingung"),
        ({"uses": "actions/checkout@v7"}, True, "uses-Schritt"),
        ({"run": "python3 x.py", "continue-on-error": True}, False, "continue-on-error"),
    ]
    for step, erwartet_hart, titel in proben:
        ist_hart = bool(harte_stellen(step))
        if ist_hart != erwartet_hart:
            fehler.append(f"Shell-Analyse falsch bei „{titel}“: "
                          f"hart={ist_hart}, erwartet={erwartet_hart}")

    # 4) Sabotageproben gegen eine Kopie des Registers/Workflows.
    with tempfile.TemporaryDirectory() as tmp:
        wurzel = Path(tmp)
        (wurzel / "data").mkdir()
        (wurzel / "scripts").mkdir()
        (wurzel / ".github" / "workflows").mkdir(parents=True)
        yaml = _yaml()

        helfer = str(reg.get("befund_helfer") or "scripts/werkzeugbefund.py")
        (wurzel / helfer).write_text("# Attrappe\n", encoding="utf-8")
        (wurzel / "scripts" / "bot_watchdog.py").write_text(
            "# blustradius_register\n", encoding="utf-8")

        def schreibe(register_daten, workflow_daten) -> list[str]:
            (wurzel / "data" / "blustradius-deploy.yml").write_text(
                yaml.safe_dump(register_daten, allow_unicode=True, sort_keys=False),
                encoding="utf-8")
            (wurzel / ".github" / "workflows" / "deploy.yml").write_text(
                yaml.safe_dump(workflow_daten, allow_unicode=True, sort_keys=False),
                encoding="utf-8")
            return pruefe(root=wurzel)

        basis_register = {
            "workflow": ".github/workflows/deploy.yml",
            "job": "deploy",
            "artefakt_schritt": "Upload",
            "beleg_schritt": "Beleg",
            "siegel_job": "release-seal",
            "befund_helfer": helfer,
            "befund_sammler": "Sammler",
            "befund_output": "werkzeugbefunde",
            "schritte": [
                {"name": "Gate", "klasse": "inhalt",
                 "grund": "Inhaltsbefund ist fachlich gemeint und stoppt zu Recht."},
                {"name": "Messung", "klasse": "werkzeug",
                 "grund": "Reine Messung ohne Inhaltsentscheid, darf nie blockieren."},
                {"name": "Sammler", "klasse": "werkzeug", "meldet": False,
                 "grund": "Sammelstelle aller Werkzeugbefunde dieses Laufs."},
                {"name": "Upload", "klasse": "infra",
                 "grund": "Der Upload ist die öffentliche Auslieferung selbst."},
                {"name": "Beleg", "klasse": "infra",
                 "grund": "Reiner Beleg für das Siegel, kann nicht fehlschlagen."},
            ],
        }
        basis_workflow = {
            "jobs": {
                "deploy": {
                    "outputs": {"werkzeugbefunde": "${{ steps.s.outputs.werkzeugbefunde }}"},
                    "steps": [
                        {"name": "Gate", "run": "python3 scripts/gate.py\n"},
                        {"name": "Messung",
                         "run": ("set +e\npython3 scripts/m.py\ncode=$?\nset -e\n"
                                 f"if [ \"$code\" -ne 0 ]; then python3 {helfer} "
                                 "--melden messung \"kaputt\"; fi\n")},
                        {"name": "Sammler", "run": f"python3 {helfer} --sammeln || true\n"},
                        {"name": "Upload", "uses": "actions/upload-pages-artifact@v5"},
                        {"name": "Beleg", "run": "echo ok\n"},
                    ],
                },
                "release-seal": {
                    "steps": [{
                        "name": "Siegel",
                        "env": {"WERKZEUGBEFUNDE": "${{ needs.deploy.outputs.werkzeugbefunde }}"},
                        "run": ('if [ -n "$WERKZEUGBEFUNDE" ]; then echo "::error::"; '
                                'exit 1; fi\n'),
                    }],
                },
            },
        }

        grund = schreibe(basis_register, basis_workflow)
        if grund:
            fehler.append(f"Attrappe ist nicht grün – die Sabotageproben messen "
                          f"dann nichts: {grund[0][:160]}")

        def sabotage(titel, mutator, erwartet):
            r = copy.deepcopy(basis_register)
            w = copy.deepcopy(basis_workflow)
            mutator(r, w)
            treffer = schreibe(r, w)
            if not any(erwartet.lower() in t.lower() for t in treffer):
                fehler.append(f"Sabotage „{titel}“ blieb unentdeckt "
                              f"(Befunde: {treffer or 'keine'})")

        def _neuer_schritt(r, w):
            w["jobs"]["deploy"]["steps"].insert(
                1, {"name": "Frisch dazugebaut", "run": "python3 neu.py\n"})
        sabotage("neuer Schritt ohne Register-Eintrag", _neuer_schritt,
                 "steht in keinem Blustradius-Register")

        def _werkzeug_hart(r, w):
            w["jobs"]["deploy"]["steps"][1]["run"] = "python3 scripts/m.py\n"
        sabotage("werkzeug-Schritt bricht hart ab", _werkzeug_hart, "GEISELHAFTUNG")

        def _werkzeug_durchgereicht(r, w):
            w["jobs"]["deploy"]["steps"][1]["run"] = (
                "set +e\npython3 scripts/m.py\ncode=$?\nset -e\nexit \"$code\"\n")
        sabotage("werkzeug reicht Exit durch", _werkzeug_durchgereicht, "GEISELHAFTUNG")

        def _stiller_werkzeugfehler(r, w):
            w["jobs"]["deploy"]["steps"][1]["run"] = (
                "set +e\npython3 scripts/m.py\ncode=$?\nset -e\necho \"$code\"\n")
        sabotage("werkzeug meldet nichts", _stiller_werkzeugfehler,
                 "meldet seinen Befund aber nirgendwohin")

        def _umbenannt(r, w):
            w["jobs"]["deploy"]["steps"][0]["name"] = "Gate (umbenannt)"
        sabotage("Schritt umbenannt", _umbenannt, "Phantom-Schritt")

        def _klasse_weg(r, w):
            r["schritte"][0]["klasse"] = "egal"
        sabotage("unbekannte Klasse", _klasse_weg, "ist unbekannt")

        def _grund_weg(r, w):
            r["schritte"][0]["grund"] = "weil"
        sabotage("Begründung zu dünn", _grund_weg, "ist eine Behauptung")

        def _nach_upload(r, w):
            w["jobs"]["deploy"]["steps"].append(
                {"name": "Noch ein Bericht", "run": "python3 report.py\n"})
            r["schritte"].append({"name": "Noch ein Bericht", "klasse": "werkzeug",
                                  "meldet": False,
                                  "grund": "Bericht nach der Auslieferung, rein informativ."})
        sabotage("Schritt nach dem Upload", _nach_upload, "läuft NACH dem Artefakt-Upload")

        def _sammler_weg(r, w):
            w["jobs"]["deploy"]["steps"].pop(2)
            r["schritte"].pop(2)
        sabotage("Sammler entfernt", _sammler_weg, "fehlt im Job")

        def _siegel_blind(r, w):
            w["jobs"]["release-seal"]["steps"][0]["run"] = "echo nix\n"
        sabotage("Siegel wertet nicht aus", _siegel_blind, "wertet die Werkzeugbefunde nicht aus")

        def _output_weg(r, w):
            w["jobs"]["deploy"]["outputs"] = {}
        sabotage("Job-Output fehlt", _output_weg, "nicht als Output heraus")

        def _selbsttest_ohne_gate(r, w):
            r["schritte"][0]["klasse"] = "gate-selbsttest"
        sabotage("Selbsttest ohne `schuetzt:`", _selbsttest_ohne_gate, "`schuetzt:` fehlt")

        def _watchdog_blind(r, w):
            (wurzel / "scripts" / "bot_watchdog.py").write_text("# nichts\n",
                                                                encoding="utf-8")
        sabotage("Watchdog kennt das Register nicht", _watchdog_blind,
                 "liest das Blustradius-Register nicht")
        (wurzel / "scripts" / "bot_watchdog.py").write_text(
            "# blustradius_register\n", encoding="utf-8")

        def _werkzeugzweig_durchgereicht(r, w):
            r["schritte"][0]["werkzeugzweig"] = 2
            w["jobs"]["deploy"]["steps"][0]["run"] = (
                "set -uo pipefail\npython3 scripts/gate.py\niso=$?\n"
                "exit \"$iso\"\n")
        sabotage("Inhalts-Gate reicht Werkzeug-Exit durch",
                 _werkzeugzweig_durchgereicht, "unevaluiert durch")

    if fehler:
        print("🛑 BLUSTRADIUS-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ Blustradius-Selbsttest grün (Positivprobe, Klassifizierung, "
          "Shell-Analyse, 13 Sabotageproben).")
    return 0


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in args:
        return _selftest()
    try:
        if "--tabelle" in args:
            print(tabelle())
            return 0
        if "--klasse" in args:
            rest = args[args.index("--klasse") + 1:]
            name = rest[0] if rest else ""
            info = klassifiziere(name)
            print(f"{info['klasse']}: {urteil(name)}")
            return 0 if info["bekannt"] else 1
        befunde = pruefe()
    except RegisterFehler as exc:
        print(f"🛑 Blustradius-Register nicht prüfbar: {exc}")
        return 2
    if befunde:
        print(f"🛑 BLUSTRADIUS-VERTRAG VERLETZT ({len(befunde)} Befund(e)) – "
              f"C38, Dauerheilung #740:")
        for b in befunde:
            print(f"   - {b}")
        print()
        print("   Register: data/blustradius-deploy.yml")
        print("   Grundsatz: Ein kaputtes Messwerkzeug nimmt die öffentliche "
              "Auslieferung nie als Geisel (C34).")
        return 1
    anzahl = len(lade_register().get("schritte") or [])
    print(f"✅ Blustradius-Vertrag erfüllt: {anzahl} Schritte des "
          f"Auslieferungswegs erklären ihren Blustradius.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
