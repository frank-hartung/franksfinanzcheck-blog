#!/usr/bin/env python3
"""push_diagnose.py – warum ein Commit/Push scheiterte, belegt statt geraten.

AUFTRAG (Frank, 21.11.2026)
===========================
„Fehlermeldungen der Commit-/Push-Schritte vergleichen: Berechtigung,
Branch-Schutz, Konflikt oder anderer Fehler? … Der generische Hinweis
‚API-Key abgelaufen' in den Issues ist keine Diagnose."

DER BEFUND, DER DIESES WERKZEUG AUSGELÖST HAT
=============================================
Vier rote Läufe vom 16./17.11.2026, ausnahmslos im Commit-/Push-Schritt:

    #1254  blog-health-daily    „Run git config user.name …“        → konflikt
    #1246  frankautoops-report  „Audit-Log-Stand committen“          → netzwerk
    #1245  hemingway-check      „Änderungen committen & pushen“      → netzwerk
    #1244  zeit-rechtschreibung „Änderungen committen & pushen“      → netzwerk

DREI VERSCHIEDENE URSACHEN, EIN RAT
-----------------------------------
Die Meldungen rieten zu abgelaufenen API-Schlüsseln, GitHub-Ausfall und
Neustart. Belegt war:

  * KEIN Schlüssel: Alle vier Schritte sind reines `git`. Kein GROQ, kein
    GEMINI, kein Netz-Dienst – der Rat konnte gar nicht zutreffen.
  * KEIN Branch-Schutz: `git_sync.sh` klassifiziert GH006/GH013/… als
    `schutz` und bricht sofort ab. In keinem der vier Läufe stand das.
  * „netzwerk“ war eine RESTKATEGORIE, keine Ursache: Sie bedeutet nur
    „nicht als Konflikt/Auth/Schutz erkannt“ – ein Non-Fast-Forward-Rennen
    wurde darunter einsortiert. Genau das war es: 14:02 `ab677efe`,
    14:05 `32976dca`, 14:12 `551f12a9` auf `main` – drei Bot-Commits in zehn
    Minuten, dazu `hemingway` und `zeit-rechtschreibung`, die `fetch-depth: 0`
    ohne erneutes Angleichen auschecken. Beide committen sieben Minuten nach
    demselben Sekundenstand `88c3e658`; wer zuerst pusht, gewinnt.
  * Ein ECHTER Konflikt (#1254): Parallel-Heilung derselben `index.md`
    (Tagesgeld/Zinsen) durch zwei Heil-Läufe.

WAS HIER PASSIERT
=================
Dieses Werkzeug liest die Fehlschläge der jüngsten Läufe (Jobs + Schritt-
Annotationen über die GitHub-API), ordnet jeden Schritt EINER Klasse zu und
gibt je Klasse den nächsten wirksamen Schritt an. Es ändert nichts, es
schreibt nichts – reine Diagnose.

    python3 scripts/push_diagnose.py                # letzte 50 Läufe
    python3 scripts/push_diagnose.py --tage 7       # Zeitfenster
    python3 scripts/push_diagnose.py --json         # maschinenlesbar
    python3 scripts/push_diagnose.py --selftest     # Klassifikation beweisen

EXIT  0 = kein Commit-/Push-Fehlschlag im Fenster
      1 = mindestens einer (die Ausgabe nennt Klasse + Handlung)
      2 = Diagnose nicht möglich (kein `gh`, keine API) – nie „grün“ raten
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone

# ======================================================================
#  KLASSEN – eine Wahrheit für Werkzeug, Log und Issue
# ======================================================================
#  Reihenfolge ist Rangfolge: Die erste passende Klasse gewinnt. Sie ist so
#  gewählt, dass die AUSSAGEKRÄFTIGSTE Erklärung vor der allgemeinen steht
#  (ein Branch-Schutz ist eine Ursache, „netzwerk“ ist eine Restmenge).
KLASSEN: tuple[tuple[str, str, str], ...] = (
    ("schutz", "Branch-Schutz / Ruleset",
     "Ein Regelwerk hat den Push abgelehnt. Reparatur NICHT über Lockerung: "
     "docs/PFLICHT-CHECK-RUNBOOK.md, Abschnitt „Direkte Pushes“ – Pflicht-"
     "Checks gelten auch für direkte Pushes und brauchen einen Bypass-Akteur "
     "im Ruleset oder einen PR-Pfad."),
    # DROSSELUNG GEHOERT VOR "auth" – in KLASSEN, weil DIESE Reihenfolge die
    # Rangfolge ist (`RANG`). GitHub drosselt mit HTTP 403 und dem Text
    # "secondary rate limit"; das Auth-Muster liest "403". Stuende diese
    # Klasse dahinter, waere eine Drosselung ein angebliches Token-Problem –
    # genau die Verwechslung, die dieses Werkzeug behebt.
    ("rate_limit", "GitHub-Drosselung (Rate-Limit)",
     "GitHub hat die Anfrage absichtlich abgelehnt (429 oder „secondary "
     "rate limit“, oft als 403 getarnt). ERNEUT VERSUCHEN MACHT ES "
     "SCHLIMMER: Jede weitere Runde zählt auf dasselbe, erschöpfte "
     "Kontingent. Deshalb steht diese Klasse vor „auth“ und vor „netzwerk“: "
     "Ein 429 ist kein Wackelkontakt, sondern eine Antwort. Reparatur: "
     "Läufe serialisieren (concurrency-Gruppe), Schreibfrequenz senken, bei "
     "„secondary rate limit“ mindestens eine Minute Abstand. „Re-run“ ist "
     "hier die falsche Antwort."),
    ("auth", "Berechtigung / Token",
     "Der Push wurde nicht autorisiert. Prüfen: `permissions: contents: write` "
     "im Workflow, Gültigkeit des Tokens, ob der Workflow aus einem "
     "Fork-Kontext läuft. Ein Retry hilft hier nie."),
    ("konflikt", "Echter Inhalts-Konflikt beim Rebase",
     "Zwei Läufe haben dieselben Zeilen geändert. Bei Bestands-Artikeln ist "
     "das ein harter Stopp (richtig). Heilung: heilende Läufe serialisieren "
     "(concurrency-Gruppe) oder den Pfad per "
     "GIT_SYNC_BESTAND_POLICY=bestand-gewinnt abgeben (WF-A535 #590)."),
    ("push_rennen", "Push-Rennen (parallele Bot-Commits)",
     "Ein anderer Lauf war schneller. Das ist kein Fehler in der Sache, "
     "sondern eine Frage der Serialisierung: gemeinsame concurrency-Gruppe "
     "für Schreiber auf `main`, oder `git_sync.sh --push-only` mit mehr "
     "Runden (GIT_SYNC_TRIES). Das Werkzeug zählt die Mitbewerber unten auf."),
    ("netzwerk", "Netzwerk-/GitHub-Transient (Restmenge)",
     "Nicht als Konflikt, Auth oder Schutz erkennbar. Erst wenn die Klassen "
     "oben ausgeschlossen sind, ist „erneut versuchen“ die richtige Antwort – "
     "und dann bitte mit Beleg aus dieser Ausgabe, nicht als Vermutung."),
    ("unbekannt", "Unbekannt (kein Git-Fehler erkannt)",
     "Der rote Schritt hat keine Git-Meldung hinterlassen. Dann ist der "
     "Schritt selbst kaputt (z. B. ein Werkzeug im `run:`-Block), nicht der "
     "Push. Die Annotation des Schritts nennt den Exit-Code."),
)

# Schritte, die einen Commit oder Push machen. Nur sie werden bewertet:
# Ein roter Test ist kein Push-Befund (und darf hier nicht als solcher
# auftauchen – sonst wiederholt das Werkzeug genau den Fehler, den es behebt).
COMMIT_SCHRITT = re.compile(
    r"commit|committen|pushen|git config user\.name|git_sync|push-only|"
    r"Audit-Log-Stand|Gate-Heilungen",
    re.IGNORECASE)

# Textmuster – dieselben, die `git_sync.sh` in seinen Klassen benutzt, plus
# die Git-Meldungen, die dort NICHT vorkommen (weil sie vor der
# Klassifikation abgefangen werden).
MUSTER: tuple[tuple[str, str], ...] = (
    ("rate_limit", r"\b429\b|rate limit|rate-limit|secondary rate|"
                   r"abuse detection|too many requests|"
                   r"API rate limit exceeded|You have exceeded a secondary"),
    ("schutz", r"GH00[1367]|GH01[34]|push protection|protected branch|"
               r"repository rule|rule violation|required status check|"
               r"changes must be made through a pull request|hook declined|"
               r"push declined|must be signed"),
    ("auth", r"could not read [Uu]sername|[Aa]uthentication failed|"
             r"[Aa]uthorization failed|[Pp]ermission denied|[Aa]ccess denied|"
             r"HTTP 40[13]|403 [Ff]orbidden|remote: Permission to|"
             r"supported authentication|Invalid username or password|"
             r"could not read Password|bad credentials"),
    ("konflikt", r"Rebase-Konflikt|CONFLICT \(|could not apply|"
                r"needs merge|unmerged files|Fix conflicts"),
    ("push_rennen", r"non-fast-forward|fetch first|cannot lock ref|stale info|"
                    r"\[rejected\]|failed to push some refs|"
                    r"Updates were rejected"),
    ("netzwerk", r"RPC failed|HTTP/2 stream|Empty reply|early EOF|"
                 r"Connection reset|Could not resolve host|"
                 r"the remote end hung up|SSL|timed out|timeout|503|502|500|"
                 r"Service Unavailable|Bad Gateway"),
)

# Reihenfolge, in der die Muster geprüft werden: von der Ursache zur Restmenge.
RANG = [name for name, _text, _handlung in KLASSEN]


# `git_sync.sh` klassifiziert seine Fehlschläge selbst und schreibt das
# Ergebnis in die Meldung („… fehlgeschlagen (zuletzt: netzwerk)“ bzw.
# „(Ursache: schutz)“). Das ist die wertvollste Angabe im Log – sie stammt
# vom Ort des Geschehens. Sie wird hier GELESEN und gegen die Rohmeldung
# geprüft, nicht blind übernommen: `netzwerk` ist ausdrücklich die
# RESTMENGE („nicht als Konflikt/Auth/Schutz erkannt“), und genau darunter
# wurden am 16.11.2026 drei Non-Fast-Forward-Rennen einsortiert.
SELBST_KLASSE = re.compile(
    r"\(zuletzt:\s*(?P<klasse>schutz|auth|push_rennen|netzwerk|konflikt|"
    r"rebase|autostash|ref_fehlt)\)|\(Ursache:\s*(?P<ursache>schutz|auth)\)",
    re.IGNORECASE)

# git_sync-Vokabular → Klasse dieses Werkzeugs. Ohne diese Abbildung stünde
# „(zuletzt: netzwerk)“ als unbekannt da, obwohl der Lauf eine Aussage traf.
SELBST_ZUORDNUNG = {
    "schutz": "schutz", "auth": "auth", "push_rennen": "push_rennen",
    "netzwerk": "netzwerk", "konflikt": "konflikt", "rebase": "konflikt",
    "autostash": "konflikt", "ref_fehlt": "push_rennen",
}


def _roh(text: str) -> str:
    """Klasse aus den ROH-Meldungen (Git/curl), ohne git_sync-Vokabular."""
    for name in RANG:
        for muster_name, muster in MUSTER:
            if muster_name == name and re.search(muster, text, re.IGNORECASE):
                return name
    return "unbekannt"


def selbst_klasse(text: str) -> str:
    """Die Selbsteinordnung eines Laufs, sofern er eine hinterlassen hat."""
    treffer = SELBST_KLASSE.search(text or "")
    if not treffer:
        return ""
    wort = (treffer.group("klasse") or treffer.group("ursache") or "").lower()
    return SELBST_ZUORDNUNG.get(wort, "")


def klassifiziere(text: str) -> str:
    """Ordnet eine Fehlermeldung einer Klasse zu – belegbar, ohne Netz.

    Zwei Quellen, eine Regel:
      1. ROHMELDUNG (Git/curl) gewinnt, wenn sie eine Ursache NENNT. Ein Text,
         der sowohl „rejected“ als auch „protected branch“ trägt, ist ein
         Schutzfall – Git schreibt beides, wenn ein Ruleset den Push abwehrt.
      2. Ist die Rohmeldung stumm, gilt die Selbsteinordnung von
         `git_sync.sh` („zuletzt: …“).
      3. Sagt der Lauf „netzwerk“ (Restmenge), die Rohmeldung aber etwas
         Konkreteres, gewinnt die konkretere Angabe.
    """
    if not text:
        return "unbekannt"
    roh = _roh(text)
    selbst = selbst_klasse(text)
    if roh == "unbekannt":
        return selbst or "unbekannt"
    if roh == "netzwerk" and selbst in ("schutz", "auth", "push_rennen",
                                        "konflikt"):
        return selbst
    return roh


def quelle(text: str) -> str:
    """Woher die Einordnung stammt – für den Bericht (Nachvollziehbarkeit)."""
    if _roh(text) != "unbekannt":
        return "Git-Meldung"
    if selbst_klasse(text):
        return "Selbsteinordnung git_sync.sh"
    return "keine Belege"


def handlung(klasse: str) -> str:
    for name, _titel, text in KLASSEN:
        if name == klasse:
            return text
    return KLASSEN[-1][2]


def titel(klasse: str) -> str:
    for name, text, _h in KLASSEN:
        if name == klasse:
            return text
    return KLASSEN[-1][1]


# ======================================================================
#  GitHub-Lesen (nur lesend)
# ======================================================================
def _gh(args: list[str]) -> str:
    erg = subprocess.run(["gh", *args], capture_output=True, text=True)
    if erg.returncode != 0:
        raise RuntimeError((erg.stderr or erg.stdout or "gh-Fehler").strip())
    return erg.stdout


def repo() -> str:
    env = os.environ.get("GITHUB_REPOSITORY", "")
    if env:
        return env
    try:
        return _gh(["repo", "view", "--json", "nameWithOwner",
                    "--jq", ".nameWithOwner"]).strip()
    except (RuntimeError, OSError) as fehler:
        raise RuntimeError(f"Repository nicht bestimmbar: {fehler}") from fehler


class Budget:
    """Deckel für API-Aufrufe – ein Diagnosewerkzeug darf nie hängen."""

    def __init__(self, aufrufe: int = 30) -> None:
        self.rest = aufrufe

    def nehmen(self) -> bool:
        if self.rest <= 0:
            return False
        self.rest -= 1
        return True


def fehlschlaege(tage: int = 3, grenze: int = 60,
                 budget: "Budget | None" = None) -> list[dict]:
    """Rote Läufe im Zeitfenster, je Lauf die roten Schritte und Annotationen.

    Über die REST-API, nicht über `gh run list --status`: Die Option gibt es
    nicht in jeder `gh`-Version, und ein Werkzeug, das auf dem Runner an
    einer fremden CLI-Version scheitert, ist keine Diagnose (der Selbsttest
    hätte es nicht gesehen).
    """
    seit = datetime.now(timezone.utc) - timedelta(days=tage)
    # KEIN --paginate: Die API liefert die jüngsten Läufe zuerst, und ein
    # Zeitfenster von Tagen braucht keine hundert Seiten. Ohne Grenze hing
    # das Werkzeug im Sandbox-Test (300 s) an der reinen Abfrage.
    roh = _gh(["api",
               f"repos/{repo()}/actions/runs?per_page={max(1, min(grenze, 100))}",
               "--jq",
               '.workflow_runs[] | select(.conclusion == "failure") | '
               '{id: .id, name: .name, created: .created_at, '
               'branch: .head_branch, event: .event, url: .html_url}'])
    laeufe = []
    for zeile in (roh or "").splitlines():
        zeile = zeile.strip()
        if not zeile:
            continue
        try:
            lauf = json.loads(zeile)
        except ValueError:
            continue
        try:
            if datetime.fromisoformat(
                    str(lauf.get("created", "")).replace("Z", "+00:00")) < seit:
                continue
        except ValueError:
            continue
        laeufe.append(lauf)
    ergebnis: list[dict] = []
    for lauf in laeufe:
        eintrag = {"id": lauf.get("id"),
                   "workflow": lauf.get("name"),
                   "created": lauf.get("created"),
                   "branch": lauf.get("branch"),
                   "event": lauf.get("event"),
                   "url": lauf.get("url"),
                   "schritte": [], "klasse": "unbekannt", "meldung": "",
                   "quelle": "", "selbst": ""}
        try:
            jobs = json.loads(_gh([
                "api", f"repos/{repo()}/actions/runs/{lauf['id']}/jobs"
                       "?filter=latest&per_page=100",
                "--jq", ".jobs"]) or "[]")
        except (RuntimeError, ValueError, KeyError):
            jobs = []
        for job in jobs:
            rote = [str(s.get("name") or "") for s in (job.get("steps") or [])
                    if s.get("conclusion") in ("failure", "timed_out")]
            relevante = [n for n in rote if COMMIT_SCHRITT.search(n)]
            if not relevante:
                continue
            # Annotationen hängen an der CHECK-RUN (= Job), nicht am Schritt:
            # Die Step-Objekte der Job-API tragen keine eigene `id`. Genau
            # daran lief die erste Fassung blind an den Meldungen vorbei –
            # alle Läufe galten als „unbekannt“, obwohl `git_sync.sh` seine
            # Ursache in die Annotation geschrieben hatte.
            texts = _annotationen(job.get("id"), budget)
            for name in relevante:
                eintrag["schritte"].append({"name": name, "texte": texts})
            if not eintrag["meldung"]:
                eintrag["meldung"] = _aussage(texts)
        if eintrag["schritte"]:
            text = "\n".join(t for s in eintrag["schritte"] for t in s["texte"])
            eintrag["klasse"] = klassifiziere(text)
            eintrag["quelle"] = quelle(text)
            eintrag["selbst"] = selbst_klasse(text)
            ergebnis.append(eintrag)
    return ergebnis


def _annotationen(check_run_id: object,
                  budget: "Budget | None" = None) -> list[str]:
    """Annotationen einer Check-Run (= eines Jobs) – der Text des Runners."""
    if not isinstance(check_run_id, int):
        return []
    if budget is not None and not budget.nehmen():
        return []
    try:
        roh = _gh(["api",
                   f"repos/{repo()}/check-runs/{check_run_id}/annotations",
                   "--jq", '.[] | "\(.annotation_level) \(.message)"'])
    except (RuntimeError, OSError):
        return []
    return [z.strip() for z in (roh or "").splitlines() if z.strip()]


def _aussage(texts: list[str]) -> str:
    """Die aussagekräftigste Zeile: die erste, die eine Klasse trifft."""
    for text in texts:
        if klassifiziere(text) != "unbekannt":
            return text[:400]
    return (texts[0][:400] if texts else "keine Annotation hinterlassen")


# ======================================================================
#  Bericht
# ======================================================================
def bericht(laeufe: list[dict]) -> dict:
    je_klasse: dict[str, list[dict]] = {}
    for lauf in laeufe:
        je_klasse.setdefault(lauf["klasse"], []).append(lauf)
    return {
        "stand": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "anzahl": len(laeufe),
        "klassen": [
            {"klasse": name, "titel": titel(name), "anzahl": len(gruppe),
             "handlung": handlung(name),
             "laeufe": [{"workflow": l["workflow"], "created": l["created"],
                         "url": l["url"], "schritt": (l["schritte"][0]["name"]
                                                      if l["schritte"] else ""),
                         "meldung": l["meldung"],
                         "quelle": l.get("quelle", ""),
                         "selbst": l.get("selbst", "")} for l in gruppe]}
            for name in RANG if (gruppe := je_klasse.get(name))
        ],
    }


def text_bericht(d: dict) -> str:
    if not d["anzahl"]:
        return ("✅ push_diagnose: kein Commit-/Push-Fehlschlag im Zeitfenster.\n"
                "   (Rote Tests und Builds sind keine Push-Befunde und werden "
                "hier bewusst nicht gezählt.)")
    zeilen = [f"🛑 push_diagnose: {d['anzahl']} Lauf/Läufe im Commit-/Push-"
              f"Schritt gescheitert (Stand {d['stand']})"]
    for gruppe in d["klassen"]:
        zeilen.append("")
        zeilen.append(f"## {gruppe['titel']} – {gruppe['anzahl']} Lauf/Läufe "
                      f"[klasse: {gruppe['klasse']}]")
        for lauf in gruppe["laeufe"]:
            zeilen.append(f"  · {lauf['workflow']} · {lauf['created'][:16]} · "
                          f"{lauf['schritt']}")
            if lauf["meldung"]:
                zeilen.append(f"    „{lauf['meldung'][:200]}“")
            if lauf.get("selbst") and lauf.get("selbst") != gruppe["klasse"]:
                zeilen.append(f"    · Selbsteinordnung des Laufs: "
                              f"{lauf['selbst']} – siehe Rohmeldung oben")
        zeilen.append(f"  → {gruppe['handlung']}")
    zeilen.append("")
    zeilen.append("Belegquelle: Job-Schritte + Schritt-Annotationen der "
                  "genannten Läufe. Kein Schlüssel, kein Neustart ohne "
                  "begründende Klasse.")
    return "\n".join(zeilen)


# ======================================================================
#  Selbsttest – die Klassifikation selbst beweisen
# ======================================================================
PROBEN: tuple[tuple[str, str, str], ...] = (
    # (Fall, Text, erwartete Klasse)
    ("#1254 echter Rebase-Konflikt",
     "git_sync.sh: Rebase-Konflikt gegen origin/main (ein paralleler Workflow "
     "hat dieselben Zeilen geändert). Betroffen: content/posts/2026-11-13-"
     "tagesgeld-und-zinsen-so-parkst-du-dein-geld-sicher/index.md.",
     "konflikt"),
    ("#1246 Restmenge ohne Git-Meldung",
     "git_sync.sh: Synchronisation nach 3 Runden fehlgeschlagen (zuletzt: "
     "netzwerk). Mögliche Ursachen: GitHub-Transient, fehlende "
     "'contents: write'-Berechtigung, Branch-Schutz …",
     "netzwerk"),
    ("paralleler Bot: non-fast-forward",
     "! [rejected]        HEAD -> main (non-fast-forward)\nerror: failed to "
     "push some refs to 'https://github.com/x/y'",
     "push_rennen"),
    ("Ruleset lehnt ab (auch mit 'rejected' im Text)",
     "remote: error: GH013: Repository rule violations found for refs/heads/"
     "main.\n! [remote rejected] HEAD -> main (push declined due to "
     "repository rule violations)",
     "schutz"),
    ("Pflicht-Check ohne Bypass",
     "remote: error: required status check 'Qualitäts-Gate' is expected",
     "schutz"),
    ("Token ohne contents: write",
     "remote: Permission to frank-hartung/blog.git denied to github-actions"
     "[bot].\nfatal: unable to access: The requested URL returned error: 403",
     "auth"),
    ("HTTP/2-Transient",
     "error: RPC failed; curl 92 HTTP/2 stream 5 was not closed cleanly",
     "netzwerk"),
    ("Unbekannt bleibt unbekannt",
     "Process completed with exit code 1.",
     "unbekannt"),
)


def selftest() -> int:
    fehler: list[str] = []
    for name, text, soll in PROBEN:
        ist = klassifiziere(text)
        if ist != soll:
            fehler.append(f"{name}: erwartet {soll}, bekommen {ist}")
    # Jede Klasse muss einen Titel und eine Handlung haben – sonst steht im
    # Issue eine leere Empfehlung (genau der Fehler, den das Werkzeug behebt).
    for wert in {soll for _n, _t, soll in PROBEN}:
        if not titel(wert).strip() or not handlung(wert).strip():
            fehler.append(f"{wert}: Titel oder Handlung fehlt")
    # Gegenprobe: Ein roter TEST ist kein Push-Befund.
    if COMMIT_SCHRITT.search("Selbsttests HART"):
        fehler.append("Ein Selbsttest würde als Push-Schritt gezählt – "
                      "das Werkzeug wiederholte den Fehler, den es behebt")
    if fehler:
        print("🛑 push_diagnose SELFTEST – Befunde:")
        for f in fehler:
            print(f"   ✗ {f}")
        return 1
    print(f"✅ push_diagnose SELFTEST: {len(PROBEN)} Klassenproben grün "
          "(Konflikt, Rennen, Schutz, Auth, Transient, Restmenge).")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Commit-/Push-Fehlschläge klassifizieren – Berechtigung, "
                    "Branch-Schutz, Konflikt oder anderes?")
    p.add_argument("--tage", type=int, default=3,
                   help="Zeitfenster in Tagen (Default 3)")
    p.add_argument("--grenze", type=int, default=60,
                   help="wie viele rote Läufe höchstens gelesen werden")
    p.add_argument("--json", action="store_true", help="Bericht als JSON")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return selftest()
    try:
        laeufe = fehlschlaege(args.tage, args.grenze, Budget())
    except (RuntimeError, OSError) as fehler:
        print(f"::error title=push_diagnose::Diagnose nicht möglich: {fehler}",
              file=sys.stderr)
        return 2
    d = bericht(laeufe)
    print(json.dumps(d, ensure_ascii=False, indent=2) if args.json
          else text_bericht(d))
    return 0 if not d["anzahl"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
