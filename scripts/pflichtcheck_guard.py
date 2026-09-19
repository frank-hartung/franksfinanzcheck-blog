#!/usr/bin/env python3
"""
PFLICHT-CHECK-WACHE – verlangt der Branch-Schutz den Check, der hier gerade läuft?
=================================================================================

WARUM ES DIESE DATEI GIBT (19.09.2026, Nachtrag zu Issue #316 / PR #317)
------------------------------------------------------------------------
Das PR-Gate `integrity-lock.yml` prüft seit PR #317 bei jedem Pull Request, ob
der signierte Kern zum Baum passt. Ein Gate ist aber nur so viel wert wie das
Häkchen, das GitHub davor setzt: Erst als **Pflicht-Check** (required status
check) im Branch-Schutz hält es einen Merge auch wirklich auf.

Der Job trug keinen Anzeigenamen und meldete sich deshalb unter seiner Job-ID
`lock`. Unter genau diesem Namen wurde er als Pflicht-Check in ein Ruleset
eingetragen – und das Ruleset zielte auf keinen Zweig (`include: []`). Die
effektiven Regeln für `main` waren leer: ein aktives Häkchen, das nichts
schützte. Genau die Fehlerklasse, gegen die dieses Haus antritt – still,
grün, folgenlos.

Ein Pflicht-Check ist ein VERTRAG zwischen zwei Orten, die einander nicht
sehen: der Workflow-Datei (was der Job heißt) und der Repository-Einstellung
(was das Ruleset verlangt). Keine Seite kann ihn allein einhalten:

  · Job umbenannt, Ruleset nicht → jeder PR wartet auf einen Check, der nie
    berichtet („Expected“). `main` ist eingefroren.
  · Ruleset ohne Ziel-Zweig, deaktiviert, gelöscht oder mit altem Namen →
    das Gate läuft, entscheidet aber nichts. Deko.

Diese Wache schließt die Lücke von der einzigen Stelle aus, die beide Seiten
sieht: dem Gate-Lauf selbst. Sie liest den Check-Namen aus der Workflow-Datei
(nicht aus einer Kopie) und fragt GitHub, welche Checks der Ziel-Zweig
verlangt (`GET /repos/{repo}/rules/branches/{branch}` – nur aktive Rulesets,
Ziel-Bedingungen bereits aufgelöst). Stimmt beides überein: grün. Sonst rot –
mit Diagnose (welches Ruleset, welcher Name, welches Ziel) und der Reparatur
in Klicks, nicht nur einem roten Kreuz.

Regeln:
  · read-only: eine GET-Anfrage, keine Secrets außer dem Lese-Token des Laufs,
    kein Schreibzugriff (C15).
  · fail-closed für den VERTRAG (Name fehlt / falsche Quelle / kein Schutz →
    Exit 1), aber nicht für das NETZ: Ist die API nicht erreichbar, meldet die
    Wache „nicht prüfbar“ als ::warning:: und bleibt grün – ein Melder, der
    bei jedem API-Schluckauf den Merge sperrt, wird selbst zum Vorfall
    (Alarm-Routing-Grundsatz, #272).
  · eine Quelle: der erwartete Name kommt aus der Workflow-Datei; der
    Governance-Vertrag (C18) friert ihn als `PFLICHT_CHECK_NAME` ein und meldet
    im Qualitäts-Gate, wenn Datei und Konstante auseinanderlaufen.

Nutzung:
    python3 scripts/pflichtcheck_guard.py                  # Live-Probe (Schritt im PR-Gate)
    python3 scripts/pflichtcheck_guard.py --branch main    # Ziel-Zweig ausdrücklich
    python3 scripts/pflichtcheck_guard.py --rules-file r.json   # Regeln aus Datei (offline)
    python3 scripts/pflichtcheck_guard.py --selftest       # Logik-Beweis: kein Netz, schreibt nie

Umgebung (im Gate gesetzt): GH_TOKEN/GITHUB_TOKEN (Lesen), GITHUB_REPOSITORY,
GITHUB_BASE_REF (Ziel-Zweig des PR), GITHUB_STEP_SUMMARY (Kurzbericht).

Exit-Codes: 0 = Vertrag erfüllt (oder nicht prüfbar, dann ::warning::)
            1 = Vertrag verletzt · 2 = Selbsttest defekt / Aufruffehler
Runbook: docs/PFLICHT-CHECK-RUNBOOK.md
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
import governance_contract as gc  # noqa: E402  (stdlib-only, keine Nebenwirkungen)

# App-ID von GitHub Actions: Ein Pflicht-Check mit dieser `integration_id` wird
# nur von Actions-Läufen erfüllt. `None` = Quelle egal (jede App / Commit-Status).
GITHUB_ACTIONS_APP_ID = 15368
API = "https://api.github.com"
RUNBOOK = "docs/PFLICHT-CHECK-RUNBOOK.md"
WORKFLOW_PFAD = os.path.join(".github", "workflows", gc.PFLICHT_CHECK_WORKFLOW)

# Urteile – die Reihenfolge ist die der Schwere.
VERLANGT = "VERLANGT"                # Ziel-Zweig verlangt genau diesen Check
FEHLT = "FEHLT"                      # es gibt Pflicht-Checks, aber nicht diesen
FALSCHE_QUELLE = "FALSCHE_QUELLE"    # Name stimmt, aber andere App verlangt
UNGESCHUETZT = "UNGESCHUETZT"        # kein Pflicht-Check auf dem Ziel-Zweig
NICHT_PRUEFBAR = "NICHT_PRUEFBAR"    # API/Antwort unbrauchbar – kein Urteil


# --------------------------------------------------------------------------- #
#  Reine Logik (vom Selbsttest bewiesen)
# --------------------------------------------------------------------------- #
def verlangte_checks(regeln) -> list[dict] | None:
    """[{context, integration_id, ruleset_id, ruleset_source}] aus der Antwort von
    `GET /rules/branches/{branch}`. None = Antwort hat nicht die erwartete Form."""
    if not isinstance(regeln, list):
        return None
    out = []
    for regel in regeln:
        if not isinstance(regel, dict):
            return None
        if regel.get("type") != "required_status_checks":
            continue
        params = regel.get("parameters") or {}
        checks = params.get("required_status_checks")
        if not isinstance(checks, list):
            return None
        for c in checks:
            if not isinstance(c, dict) or not isinstance(c.get("context"), str):
                return None
            out.append({"context": c["context"],
                        "integration_id": c.get("integration_id"),
                        "ruleset_id": regel.get("ruleset_id"),
                        "ruleset_source": regel.get("ruleset_source")})
    return out


def beurteilen(regeln, erwartet: str, job_id: str = "",
               app_id: int = GITHUB_ACTIONS_APP_ID) -> dict:
    """Urteil über die Regeln eines Zweigs: verlangt er den Check `erwartet`?

    `job_id` ist der Name, unter dem sich der Job OHNE Anzeigenamen melden
    würde – taucht er im Ruleset auf, ist die Diagnose eindeutig (Ausgangsbefund
    vom 19.09.2026) und die Reparatur ein einziger Namenstausch.
    """
    checks = verlangte_checks(regeln)
    if checks is None:
        return {"urteil": NICHT_PRUEFBAR, "checks": [],
                "grund": "Antwort der Regel-API hat nicht die erwartete Form."}
    treffer = [c for c in checks if c["context"] == erwartet]
    if any(c["integration_id"] in (None, app_id) for c in treffer):
        return {"urteil": VERLANGT, "checks": checks, "grund": ""}
    if treffer:
        quellen = ", ".join(str(c["integration_id"]) for c in treffer)
        return {"urteil": FALSCHE_QUELLE, "checks": checks,
                "grund": f"`{erwartet}` wird verlangt, aber von App-ID {quellen} statt "
                         f"GitHub Actions ({app_id}) – der Lauf dieses Workflows erfüllt "
                         f"den Check nie."}
    if not checks:
        return {"urteil": UNGESCHUETZT, "checks": checks,
                "grund": f"Kein aktives Ruleset verlangt einen Status-Check auf dem "
                         f"Ziel-Zweig – `{erwartet}` entscheidet nichts, das Siegel ist Deko."}
    namen = ", ".join(f"`{c['context']}`" for c in checks)
    hinweis = ""
    if job_id and any(c["context"] == job_id for c in checks):
        hinweis = (f" `{job_id}` ist die Job-ID: So hieß der Check, bevor der Job seinen "
                   f"Anzeigenamen bekam – das Ruleset trägt noch den alten Namen.")
    return {"urteil": FEHLT, "checks": checks,
            "grund": f"Der Ziel-Zweig verlangt {namen}, nicht `{erwartet}` – dieser Lauf "
                     f"erfüllt keinen der verlangten Checks, und auf `{erwartet}` wartet "
                     f"niemand.{hinweis}"}


def ruleset_diagnose(rulesets: list[dict]) -> list[str]:
    """Lesbare Zeilen je Ruleset (Name, Zustand, Ziel-Zweige, verlangte Checks) –
    für den Fall, dass der Ziel-Zweig nichts verlangt: Meist existiert das
    Häkchen, es zeigt nur ins Leere (kein Ziel, deaktiviert, alter Name)."""
    zeilen = []
    for rs in rulesets or []:
        if not isinstance(rs, dict):
            continue
        ziele = (((rs.get("conditions") or {}).get("ref_name") or {}).get("include")) or []
        checks = verlangte_checks(rs.get("rules") or []) or []
        namen = ", ".join(f"`{c['context']}`" for c in checks) or "keinen Status-Check"
        ziel = ", ".join(f"`{z}`" for z in ziele) if ziele else "KEINEN Zweig (include: [])"
        zeilen.append(f"Ruleset „{rs.get('name', '?')}“ (#{rs.get('id', '?')}, "
                      f"{rs.get('enforcement', '?')}): verlangt {namen}, zielt auf {ziel}.")
    return zeilen


def reparatur(erwartet: str, checks: list[dict], ruleset_name: str = "") -> list[str]:
    """Die Reparatur in Klicks – für einen Admin, nicht für einen Parser."""
    rs = f"„{ruleset_name}“" if ruleset_name else "das Ruleset für den Ziel-Zweig"
    alt = sorted({c["context"] for c in checks if c["context"] != erwartet})
    tausch = (f"`{'`, `'.join(alt)}` entfernen, " if alt else "")
    return [
        f"Fix (Admin, drei Klicks): Settings → Rules → Rulesets → {rs}",
        "  · Target branches → Add target → „Include default branch“",
        f"  · Require status checks to pass → {tausch}`{erwartet}` hinzufügen "
        f"(Quelle: GitHub Actions)",
        "  · Save changes → diesen Job erneut ausführen (Re-run) → grün.",
        f"Runbook mit API-Einzeiler und Reihenfolge beim Umbenennen: {RUNBOOK}",
    ]


# --------------------------------------------------------------------------- #
#  GitHub-API (nur GET) und Umgebung
# --------------------------------------------------------------------------- #
def api_get(pfad: str, token: str = "", timeout: int = 20):
    """GET gegen die REST-API. Liefert (json, fehlertext) – wirft nie."""
    req = urllib.request.Request(API + pfad, headers={
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "franksfinanzcheck-pflichtcheck-guard",
        **({"Authorization": f"Bearer {token}"} if token else {}),
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as antwort:
            return json.loads(antwort.read().decode("utf-8")), ""
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code} für {pfad}"
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        return None, f"{type(exc).__name__}: {exc} ({pfad})"


def repo_aus_umgebung() -> str:
    repo = os.environ.get("GITHUB_REPOSITORY", "").strip()
    if repo:
        return repo
    try:
        url = subprocess.run(("git", "-C", BLOG_DIR, "remote", "get-url", "origin"),
                             capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
    url = url.removesuffix(".git")
    for marker in ("github.com/", "github.com:"):
        if marker in url:
            return url.split(marker, 1)[1].strip("/")
    return ""


def erwarteter_check() -> tuple[str, str, str]:
    """(Check-Name laut Workflow-Datei, Job-ID, Warnung). Der Name kommt aus
    der Datei, die GitHub für diesen Lauf gelesen hat – nicht aus einer Kopie."""
    try:
        with open(os.path.join(BLOG_DIR, WORKFLOW_PFAD), encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return gc.PFLICHT_CHECK_NAME, "", f"{WORKFLOW_PFAD} nicht lesbar – Vertragskonstante genutzt."
    name = gc.pflichtcheck_name_aus_workflow(text)
    job_id = ""
    for job in gc.pflichtcheck_profil(text)["jobs"]:
        if (job["name"] or job["id"]) == name:
            job_id = job["id"]
    if not name:
        return gc.PFLICHT_CHECK_NAME, "", (f"{WORKFLOW_PFAD}: kein Job mit `integrity_guard.py "
                                           f"--gate` – Vertragskonstante genutzt (C18 meldet das).")
    warnung = ""
    if name != gc.PFLICHT_CHECK_NAME:
        warnung = (f"Workflow meldet `{name}`, Vertrag erwartet `{gc.PFLICHT_CHECK_NAME}` – "
                   f"C18 im Qualitäts-Gate ist rot; geprüft wird der echte Name.")
    return name, job_id, warnung


def step_summary(zeilen: list[str]) -> None:
    pfad = os.environ.get("GITHUB_STEP_SUMMARY")
    if not pfad:
        return
    try:
        with open(pfad, "a", encoding="utf-8") as fh:
            fh.write("\n".join(zeilen) + "\n")
    except OSError:
        pass


def annotate(art: str, text: str) -> None:
    if os.environ.get("GITHUB_ACTIONS"):
        print(f"::{art}::{text}")


# --------------------------------------------------------------------------- #
#  Live-Probe
# --------------------------------------------------------------------------- #
def probe(branch: str = "", repo: str = "", rules_file: str = "") -> int:
    erwartet, job_id, warnung = erwarteter_check()
    branch = (branch or os.environ.get("GITHUB_BASE_REF", "").strip()
              or os.environ.get("PFLICHTCHECK_BRANCH", "").strip() or gc.PFLICHT_CHECK_BRANCH)
    repo = repo or repo_aus_umgebung()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    print(f"🔒 Pflicht-Check-Wache: Branch-Schutz für `{branch}`"
          + (f" ({repo})" if repo else ""))
    print(f"   erwarteter Check: `{erwartet}` (aus {WORKFLOW_PFAD}"
          + (f", Job-ID `{job_id}`" if job_id else "") + ")")
    if warnung:
        print(f"   ⚠️  {warnung}")
        annotate("warning", warnung)

    fehler = ""
    if rules_file:
        try:
            with open(rules_file, encoding="utf-8") as fh:
                regeln = json.load(fh)
        except (OSError, ValueError) as exc:
            regeln, fehler = None, f"{rules_file}: {exc}"
    elif not repo:
        regeln, fehler = None, "Repository unbekannt (GITHUB_REPOSITORY/origin fehlen)."
    else:
        regeln, fehler = api_get(f"/repos/{repo}/rules/branches/{branch}", token)

    if fehler:
        text = (f"Pflicht-Check-Wache: Branch-Schutz nicht prüfbar ({fehler}) – kein Urteil. "
                f"Bitte von Hand: gh api repos/{repo or 'OWNER/REPO'}/rules/branches/{branch}")
        print(f"⚠️  {text}")
        annotate("warning", text)
        step_summary([f"### ⚠️ Pflicht-Check `{erwartet}`: nicht prüfbar", "", fehler])
        return 0

    urteil = beurteilen(regeln, erwartet, job_id=job_id)
    verlangt = ", ".join(f"`{c['context']}`" for c in urteil["checks"]) or "– (kein Status-Check)"
    print(f"   verlangt auf `{branch}`: {verlangt}")
    if urteil["urteil"] == NICHT_PRUEFBAR:
        text = f"Pflicht-Check-Wache: {urteil['grund']} – kein Urteil."
        print(f"⚠️  {text}")
        annotate("warning", text)
        step_summary([f"### ⚠️ Pflicht-Check `{erwartet}`: nicht prüfbar", "", urteil["grund"]])
        return 0
    if urteil["urteil"] == VERLANGT:
        ids = sorted({str(c["ruleset_id"]) for c in urteil["checks"]
                      if c["context"] == erwartet and c["ruleset_id"] is not None})
        print(f"✅ Vertrag erfüllt: `{branch}` verlangt `{erwartet}`"
              + (f" (Ruleset #{', #'.join(ids)})" if ids else "") + " – das Siegel entscheidet.")
        step_summary([f"### ✅ Pflicht-Check `{erwartet}` wird auf `{branch}` verlangt", "",
                      f"Ruleset: {', '.join('#' + i for i in ids) or '–'}"])
        return 0

    # Rot – mit Diagnose (best effort, ändert das Urteil nicht) und Reparatur.
    # Die Diagnose liest die Rulesets des Repositories: Meist existiert das
    # Häkchen, es zeigt nur ins Leere (kein Ziel-Zweig, deaktiviert, alter Name).
    print(f"🛑 PFLICHT-CHECK-VERTRAG VERLETZT – {urteil['grund']}")
    ruleset_name, alte_namen = "", list(urteil["checks"])
    if repo and not rules_file:
        liste, _f = api_get(f"/repos/{repo}/rulesets", token)
        details = []
        for rs in (liste if isinstance(liste, list) else [])[:10]:
            if isinstance(rs, dict) and rs.get("target", "branch") == "branch" and "id" in rs:
                d, _f2 = api_get(f"/repos/{repo}/rulesets/{rs['id']}", token)
                if isinstance(d, dict):
                    details.append(d)
                    im_ruleset = verlangte_checks(d.get("rules") or []) or []
                    alte_namen += im_ruleset
                    if not ruleset_name and any(c["context"] in (erwartet, job_id)
                                                for c in im_ruleset):
                        ruleset_name = d.get("name", "")
        for zeile in ruleset_diagnose(details):
            print(f"   Diagnose: {zeile}")
        if liste == []:
            print("   Diagnose: Das Repository hat kein Ruleset – der Pflicht-Check wurde nie eingetragen.")
    rep = reparatur(erwartet, alte_namen, ruleset_name)
    for zeile in rep:
        print(f"   {zeile}")
    annotate("error", f"Pflicht-Check-Vertrag verletzt: {urteil['grund']} Reparatur im Log / {RUNBOOK}")
    step_summary([f"### 🛑 Pflicht-Check `{erwartet}` wird auf `{branch}` NICHT verlangt", "",
                  urteil["grund"], "", *[f"- {z.strip().removeprefix('· ')}" for z in rep]])
    return 1


# --------------------------------------------------------------------------- #
#  Selbsttest – reine Logik, kein Netz, schreibt nie (C15)
# --------------------------------------------------------------------------- #
def _regel(*checks, ruleset_id=42):
    return {"type": "required_status_checks", "ruleset_source_type": "Repository",
            "ruleset_source": "o/r", "ruleset_id": ruleset_id,
            "parameters": {"strict_required_status_checks_policy": False,
                           "required_status_checks": [
                               {"context": c, "integration_id": i} for c, i in checks]}}


def selftest() -> int:
    f = []
    name, alt = gc.PFLICHT_CHECK_NAME, "lock"
    # 1) verlangt – von Actions oder quellenfrei
    if beurteilen([_regel((name, GITHUB_ACTIONS_APP_ID))], name)["urteil"] != VERLANGT:
        f.append("Fall1: verlangter Check (Actions) wird nicht als VERLANGT erkannt.")
    if beurteilen([_regel((name, None))], name)["urteil"] != VERLANGT:
        f.append("Fall1b: verlangter Check ohne Quellbindung wird nicht als VERLANGT erkannt.")
    if beurteilen([{"type": "deletion"}, _regel((alt, 15368), (name, 15368))], name)["urteil"] != VERLANGT:
        f.append("Fall1c: Check neben anderen Regeln/Checks wird nicht erkannt.")
    # 2) der Ausgangsbefund: Ruleset trägt die Job-ID, der Job heißt inzwischen anders
    u = beurteilen([_regel((alt, GITHUB_ACTIONS_APP_ID))], name, job_id=alt)
    if u["urteil"] != FEHLT or f"`{alt}`" not in u["grund"] or "Job-ID" not in u["grund"]:
        f.append(f"Fall2: alter Name im Ruleset wird nicht als FEHLT mit Job-ID-Hinweis erkannt: {u}")
    u = beurteilen([_regel(("Playwright", 15368))], name, job_id=alt)
    if u["urteil"] != FEHLT or "Job-ID" in u["grund"]:
        f.append("Fall2b: fremder Pflicht-Check darf keinen Job-ID-Hinweis erzeugen.")
    # 3) kein Schutz: leere Regeln (include: [] – der Befund vom 19.09.2026) / nur andere Regeln
    if beurteilen([], name)["urteil"] != UNGESCHUETZT:
        f.append("Fall3: leere Regelliste (Ruleset ohne Ziel-Zweig) wird nicht als UNGESCHUETZT erkannt.")
    if beurteilen([{"type": "deletion"}, {"type": "non_fast_forward"}], name)["urteil"] != UNGESCHUETZT:
        f.append("Fall3b: Regeln ohne Status-Check werden nicht als UNGESCHUETZT erkannt.")
    # 4) falsche Quelle: gleicher Name, andere App
    if beurteilen([_regel((name, 99))], name)["urteil"] != FALSCHE_QUELLE:
        f.append("Fall4: gleichnamiger Check einer anderen App wird nicht als FALSCHE_QUELLE erkannt.")
    # 5) unbrauchbare Antwort → kein Urteil (nie ein falsches Grün, nie ein falsches Rot)
    for kaputt in ({"message": "Not Found"}, [{"type": "required_status_checks"}],
                   [{"type": "required_status_checks", "parameters": {"required_status_checks": [{}]}}]):
        if beurteilen(kaputt, name)["urteil"] != NICHT_PRUEFBAR:
            f.append(f"Fall5: unbrauchbare Antwort wird beurteilt statt als NICHT_PRUEFBAR gemeldet: {kaputt}")
    # 6) Diagnose nennt das Ziel-Problem beim Namen
    diag = ruleset_diagnose([{"id": 1, "name": "Integritäts-Lock (PR-Gate)", "enforcement": "active",
                              "conditions": {"ref_name": {"include": [], "exclude": []}},
                              "rules": [_regel((alt, 15368))]}])
    if len(diag) != 1 or "KEINEN Zweig" not in diag[0] or f"`{alt}`" not in diag[0]:
        f.append(f"Fall6: Diagnose nennt Ziel-Lücke/alten Namen nicht: {diag}")
    diag = ruleset_diagnose([{"id": 2, "name": "x", "enforcement": "active",
                              "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"]}},
                              "rules": []}])
    if "`~DEFAULT_BRANCH`" not in diag[0] or "keinen Status-Check" not in diag[0]:
        f.append(f"Fall6b: Diagnose mit Ziel, aber ohne Check, ist unvollständig: {diag}")
    # 7) Reparatur nennt Tausch (alt raus, neu rein), Ziel und Runbook
    rep = "\n".join(reparatur(name, [{"context": alt, "integration_id": 15368,
                                      "ruleset_id": 1, "ruleset_source": "o/r"}], "R"))
    for muss in (f"`{alt}` entfernen", f"`{name}` hinzufügen", "Include default branch", RUNBOOK, "„R“"):
        if muss not in rep:
            f.append(f"Fall7: Reparatur ohne „{muss}“.")
    # 8) der Name kommt aus der Workflow-Datei – Anzeigename, sonst Job-ID
    wf = ("on:\n  pull_request:\n    branches: [main]\njobs:\n  lock:\n    name: Siegel-X\n"
          "    steps:\n      - name: g\n        run: python3 scripts/integrity_guard.py --gate\n")
    if gc.pflichtcheck_name_aus_workflow(wf) != "Siegel-X":
        f.append("Fall8: Anzeigename wird nicht aus der Workflow-Datei gelesen.")
    if gc.pflichtcheck_name_aus_workflow(wf.replace("    name: Siegel-X\n", "")) != "lock":
        f.append("Fall8b: ohne Anzeigename muss die Job-ID gelten.")
    if gc.pflichtcheck_name_aus_workflow(wf.replace("--gate", "--selftest")) != "":
        f.append("Fall8c: ohne Gate-Schritt darf kein Name geraten werden.")
    # 9) der echte Workflow und die Vertragskonstante sind eine Wahrheit
    try:
        with open(os.path.join(BLOG_DIR, WORKFLOW_PFAD), encoding="utf-8") as fh:
            echt = gc.pflichtcheck_name_aus_workflow(fh.read())
    except OSError:
        echt = None
    if echt is not None and echt != gc.PFLICHT_CHECK_NAME:
        f.append(f"Fall9: {WORKFLOW_PFAD} meldet `{echt}`, Vertrag erwartet `{gc.PFLICHT_CHECK_NAME}` – "
                 f"Umbenennung ohne Vertrag (Ruleset im selben Atemzug!).")
    if f:
        print("❌ PFLICHTCHECK-SELBSTTEST FEHLGESCHLAGEN:")
        for z in f:
            print("   -", z)
        return 2
    print(f"✅ Pflichtcheck-Selbsttest bestanden (9 Fälle: Urteile, Diagnose, Reparatur, "
          f"Namensquelle – erwartet `{gc.PFLICHT_CHECK_NAME}`).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verlangt der Branch-Schutz den Check, der hier läuft?")
    ap.add_argument("--selftest", action="store_true", help="Logik-Beweis ohne Netz (schreibt nie)")
    ap.add_argument("--branch", default="", help="Ziel-Zweig (Standard: GITHUB_BASE_REF, sonst main)")
    ap.add_argument("--repo", default="", help="owner/repo (Standard: GITHUB_REPOSITORY, sonst origin)")
    ap.add_argument("--rules-file", default="", help="Regel-JSON statt API (offline/Diagnose)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    return probe(branch=args.branch, repo=args.repo, rules_file=args.rules_file)


if __name__ == "__main__":
    sys.exit(main())
