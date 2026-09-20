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
  · read-only: nur GET-Anfragen, keine Secrets außer dem Lese-Token des Laufs,
    kein Schreibzugriff (C15).
  · fail-closed für den VERTRAG (Name fehlt / falsche Quelle / kein Schutz →
    Exit 1), aber nicht für das NETZ: Ist die API nicht erreichbar, meldet die
    Wache „nicht prüfbar“ als ::warning:: und bleibt grün – ein Melder, der
    bei jedem API-Schluckauf den Merge sperrt, wird selbst zum Vorfall
    (Alarm-Routing-Grundsatz, #272). Dritte Ausnahme, gleicher Grund: ein als
    Dauerzustand dokumentierter Befund meldet ::warning:: statt Exit 1 –
    ausschließlich bei exakter Übereinstimmung und nur bis zur Prüffrist
    (Nachtrag 20.09.2026).
  · eine Quelle: der erwartete Name kommt aus der Workflow-Datei; der
    Governance-Vertrag (C18) friert ihn als `PFLICHT_CHECK_NAME` ein und meldet
    im Qualitäts-Gate, wenn Datei und Konstante auseinanderlaufen.

Nutzung:
    python3 scripts/pflichtcheck_guard.py                  # Live-Probe (Schritt im PR-Gate)
    python3 scripts/pflichtcheck_guard.py --branch main    # Ziel-Zweig ausdrücklich
    python3 scripts/pflichtcheck_guard.py --strict         # Dauerzustand wieder hart (Admin/Audit)
    python3 scripts/pflichtcheck_guard.py --rules-file r.json   # Regeln aus Datei (offline)
    python3 scripts/pflichtcheck_guard.py --selftest       # Logik-Beweis: kein Netz, schreibt nie

Umgebung (im Gate gesetzt): GH_TOKEN/GITHUB_TOKEN (Lesen), GITHUB_REPOSITORY,
GITHUB_BASE_REF (Ziel-Zweig des PR), GITHUB_STEP_SUMMARY (Kurzbericht).
Zusätzlich: PFLICHTCHECK_STRICT=1 entspricht `--strict` (für Läufe, in denen die
Kommandozeile nicht erreichbar ist), PFLICHTCHECK_BRANCH als Ziel-Zweig-Ausnahme.

Exit-Codes: 0 = Vertrag erfüllt · dokumentierter Dauerzustand (weicher Modus) ·
              nicht prüfbar (dann ::warning::)
            1 = Vertrag verletzt und NICHT der dokumentierte Dauerzustand – oder
                doch, aber `--strict` · 2 = Selbsttest defekt / Aufruffehler
NACHTRAG 19.09.2026 (zweiter Vorfall – Deploy-Ausfall, Issue #320)
-------------------------------------------------------------------
Dieselbe Wache meldete „✅ Vertrag erfüllt“, während `main` seit Stunden keinen
einzigen Commit der Automation mehr annahm: Das Ruleset verlangte den Pflicht-
Check `Integritäts-Siegel`, hatte aber KEINEN Bypass-Akteur. Pflicht-Checks
gelten für jeden Push – dieser Check entsteht jedoch nur in Pull Requests.
Deploy #998 scheiterte im Schritt „Gate-Heilungen committen“, „Deploy auf
gh-pages“ wurde übersprungen, die Seite blieb vier Stunden alt.

Der Vertrag war also erfüllt, nur um den Preis der direkten Pushes. Deshalb
prüft die Wache im GRÜNEN Fall zusätzlich nach (best effort, ändert nie das
Urteil): Verlangt ein aktives Ruleset einen Pflicht-Check auf dem Ziel-Zweig,
ohne Actions-Integration 15368 im Modus always, UND committen Workflows selbst auf diesen
Zweig? Dann ::warning:: mit Reparatur-Anleitung statt stiller Schein-Sicherheit.
Ein Admin-Eingriff bleibt Menschen vorbehalten (C15/Runbook) – die Wache meldet,
sie repariert nicht.

Betriebswache: --automation misst unabhängig vom PR-Vertrag auf main den letzten
Bot-Commit gegen abgeschlossene Cron-Läufe schreibender Workflows. >24 h Stille
mit Cron-Evidenz wird als ROT-Finding ans Governance-Gate geliefert. API-Lücken
sind INFO, keine erfundene Blockade. --report schreibt nur bei explizitem Auftrag.

NACHTRAG 20.09.2026 (Dritter Fall – der Vertrag ist hier nicht erfüllbar)
--------------------------------------------------------------------------
Seit 19.09. 23:09 UTC meldet diese Wache in JEDEM Pull Request rot: `main`
verlangt den Check nicht (kein `required_status_checks` in einem aktiven Ruleset).
Die Reparatur ist eine Admin-Änderung an einem Ruleset – und die ist nach C15 wie
nach Rechtelage nichts, was ein Lauf dieses Repos tun darf (der Bot-Zugang hat
kein `administration:write`). Der Vertrag ist auf diesem Repo also nicht
erfüllbar, sondern ein Dauerzustand. Und das rote Kreuz, das ihn meldet, hat
nichts in der Hand: PR #327 wurde am 20.09.2026 um 15:43 UTC gemergt, während
`Integritäts-Siegel` auf `FAILURE` stand (Run 35520108131, Merge-Commit 4b91938).

Ein Rot, das niemand beantworten kann und das nichts aufhält, ist kein Mess-
instrument, sondern Lärm – die Lehre aus #206/#272. Also: dokumentieren statt
alarmieren (Option B), ausdrücklich nicht „grün waschen“: Die Wache prüft
jeden Schritt genauso wie vorher, der Befund steht unverändert da – nur
eingeordnet:

  · `gc.PFLICHT_CHECK_DAUERZUSTAND` beschreibt den festgestellten Zustand (Zweig,
    Check, Urteil, Evidenz, Prüffrist). Diese Wache vergleicht den LIVE-Befund
    damit; nur die Übereinstimmung ist weich.
  · weicher Fall → Exit 0, `::warning::`, 🛑 bleibt in Log und Step-Summary
  · jeder andere Fall → wie bisher Exit 1 und `::error::`: anderer Befund
    (`FEHLT`, `FALSCHE_QUELLE`, `PR_SCOPING_FEHLT`), neues Ruleset ohne
    Actions-Bypass (der Stillstand vom 19.09.), abgelaufene oder unbrauchbare
    Frist, fehlende Erklärung
  · `--strict` (oder PFLICHTCHECK_STRICT=1) meldet auch den bekannten Zustand als
    Vorfall – für Admin-Sitzungen und Nachprüfungen; die Frist setzt dem
    Weichzeichnen ohnehin ein Datum
  · wird der Check doch verlangt, meldet der grüne Lauf die Erklärung als
    überholt; sie muss im selben PR aus dem Vertrag

Der harte Stopp selbst ist von all dem nicht berührt: `integrity_guard.py --gate`
läuft im selben Job vorher, prüft fail-closed und stoppt die Produktion bei Drift.
Er hält nur keinen Merge auf, weil kein Pflicht-Check verlangt ist – das ist die
Lücke, nicht dieses Urteil.

Runbook: docs/PFLICHT-CHECK-RUNBOOK.md
"""
from __future__ import annotations

import argparse
import datetime as dt
import fnmatch
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
import urllib.parse

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
PR_SCOPING_FEHLT = "PR_SCOPING_FEHLT"  # PR-Pflicht mit 0 Approvals fehlt
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
               app_id: int = GITHUB_ACTIONS_APP_ID, pr_pflicht: bool = False) -> dict:
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
        if pr_pflicht and not any(r.get("type") == "pull_request" and
                                  (r.get("parameters") or {}).get("required_approving_review_count") == 0
                                  for r in regeln):
            return {"urteil": PR_SCOPING_FEHLT, "checks": checks,
                    "grund": "PR-Scoping fehlt: pull_request-Regel mit 0 Approvals erforderlich. "
                             "Der Actions-Bypass muss Integration 15368 / always sein (Runbook)."}
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


def zielt_auf(rs: dict, branch: str, default_branch: str = "main") -> bool:
    """Trifft das Ruleset den Zweig? Treffer sind `~DEFAULT_BRANCH`/`~ALL`,
    `refs/heads/<branch>`, `<branch>` und Platzhalter-Muster; `exclude` sticht.
    `~DEFAULT_BRANCH` trifft nur den tatsächlichen Default-Zweig."""
    bed = (rs.get("conditions") or {}).get("ref_name") or {}
    inc, exc = bed.get("include") or [], bed.get("exclude") or []

    def trifft(muster) -> bool:
        m = str(muster or "")
        if not m:
            return False
        if m == "~DEFAULT_BRANCH":
            return branch == default_branch
        if m in ("~ALL", branch, f"refs/heads/{branch}"):
            return True
        return fnmatch.fnmatch(branch, m.removeprefix("refs/heads/"))

    return any(trifft(m) for m in inc) and not any(trifft(m) for m in exc)


def actions_bypass(rs: dict) -> bool:
    """Nur die Actions-Integration mit Always erlaubt direkte GITHUB_TOKEN-Pushes.

    Eine menschliche Rolle, fremde App oder pull_request-Bypass genügt NICHT.
    Der Bypass gilt für das ganze Ruleset, nicht nur für dessen PR-Regel.
    """
    return any(isinstance(a, dict) and a.get("actor_id") == GITHUB_ACTIONS_APP_ID
               and a.get("actor_type") == "Integration" and a.get("bypass_mode") == "always"
               for a in rs.get("bypass_actors") or [])


def blockiert_direkte_pushes(details: list[dict], branch: str = "main") -> list[dict]:
    """PR-/Check-Regeln auf dem Ziel ohne wirksamen Actions-Bypass.

    PR-Scoping bedeutet PR-Pflicht für Menschen, NICHT dass Status-Checks nur
    bei PRs gelten. Jede zusätzliche aktive Regel muss separat passiert werden.
    """
    treffer = []
    for rs in details or []:
        if (not isinstance(rs, dict) or rs.get("enforcement") != "active"
                or rs.get("target", "branch") != "branch"):
            continue
        # GitHub kann bypass_actors bei fehlender Ruleset-Sichtbarkeit weglassen.
        # Fehlendes Feld ist unbekannt, nicht dasselbe wie explizit null/[]!
        if "bypass_actors" not in rs:
            continue
        checks = verlangte_checks(rs.get("rules") or []) or []
        pr = any(r.get("type") == "pull_request" for r in rs.get("rules") or [])
        if not (checks or pr) or not zielt_auf(rs, branch) or actions_bypass(rs):
            continue
        treffer.append({"id": rs.get("id"), "name": rs.get("name", "?"),
                        "checks": [c["context"] for c in checks], "pull_request": pr})
    return treffer


def direkt_pusher(workflows: dict[str, str]) -> list[str]:
    """Workflows, die selbst committen/pushen: `contents: write` UND ein Push-
    Aufruf (`git_sync.sh` / `git push`). Sie sind die Kunden eines Bypass-Akteurs;
    gibt es keine, ist ein Ruleset ohne Bypass harmlos (dann nur PRs betroffen)."""
    treffer = []
    for datei, text in (workflows or {}).items():
        t = str(text or "")
        if re.search(r"contents:\s*write", t) and re.search(r"git_sync\.sh|git\s+push\b", t):
            treffer.append(str(datei))
    return sorted(treffer)


def workflow_nur_pull_request(text: str) -> bool:
    """True, wenn der Workflow einen `pull_request`-, aber keinen `push:`-Trigger
    hat: Sein Check kann auf einem direkten Push nie entstehen – der Pflicht-Check
    ist dann eine Sackgasse, kein Sicherheitsgewinn."""
    kopf = re.split(r"^jobs:", str(text or ""), maxsplit=1, flags=re.M)[0]
    return bool(re.search(r"^\s*pull_request\s*:", kopf, re.M)) \
        and not re.search(r"^\s*push\s*:", kopf, re.M)


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
        f"Fix (Admin): Settings → Rules → Rulesets → {rs}",
        "  · Target branches → Add target → „Include default branch“",
        f"  · Require status checks to pass → {tausch}`{erwartet}` hinzufügen "
        f"(Quelle: GitHub Actions)",
        "  · Require a pull request before merging → 0 Approvals; Bypass: GitHub Actions "
        "(Integration 15368), Always allow – keine menschlichen Rollen.",
        "  · Enforcement Active → Save changes → diesen Job erneut ausführen (Re-run).",
        f"Runbook mit Admin-Request und Reihenfolge beim Umbenennen: {RUNBOOK}",
    ]


# --------------------------------------------------------------------------- #
#  Dauerzustand: dokumentiert statt Dauer-Alarm (Option B, 20.09.2026)
# --------------------------------------------------------------------------- #
def _isodatum(wert):
    try:
        return dt.date.fromisoformat(str(wert or "").strip())
    except ValueError:
        return None


def dauerzustand_pruefen(zustand, urteil: str, branch: str, erwartet: str,
                         now: dt.date, blockierer=None) -> dict:
    """Gilt die dokumentierte Dauerzustand-Erklärung für GENAU DIESEN Befund?

    Die Erklärung ist keine Ausrede auf Dauer, sondern ein Abgleich: Sie gilt nur,
    wenn gemessenes Urteil, Zweig und Checkname exakt dem Festgestellten
    entsprechen, die Prüffrist läuft und das Ruleset-Ensemble keinen neuen Zustand
    zeigt. Alles andere ist Drift und bleibt ein Vorfall – Exit 1 mit ::error:::

      · anderer Befund (`FEHLT`, `FALSCHE_QUELLE`, `PR_SCOPING_FEHLT`) → der
        Branch-Schutz verlangt *etwas*, nur nicht dieses Siegel; das ist neu und
        reparierbar
      · neues Ruleset ohne Actions-Bypass → die Automation steht still (Vorfall vom
        19.09.2026); das ist ein zweiter, dringender Fehler
      · Frist abgelaufen oder unbrauchbar → der Zustand wurde zu lange nicht gesehen
      · keine Erklärung hinterlegt → melden wie bisher

    `blockierer=None` heißt „nicht prüfbar" (Offline-Modus mit `--rules-file`): die
    Freigabe gilt dann, aber der Lauf sagt offen, dass er diese eine Seite nicht
    gesehen hat.
    """
    def abgelehnt(grund, hinweise=()):
        return {"gilt": False, "grund": grund, "hinweise": list(hinweise), "frist": "", "tage": None}
    if not isinstance(zustand, dict) or not zustand:
        return abgelehnt("keine Dauerzustand-Erklärung hinterlegt")
    for feld, gemessen in (("urteil_erwartet", urteil), ("check", erwartet), ("branch", branch)):
        dokumentiert = str(zustand.get(feld) or "")
        if dokumentiert != gemessen:
            return abgelehnt(f"dokumentiert ist `{dokumentiert or '–'}`, gemessen `{gemessen}` "
                             f"(Feld `{feld}`) – das ist nicht der freigegebene Zustand")
    frist = _isodatum(zustand.get("pruefung_bis"))
    if frist is None:
        return abgelehnt(f"Prüffrist `{zustand.get('pruefung_bis')}` ist kein ISO-Datum – "
                         f"eine Erklärung ohne belastbare Frist gilt nicht")
    if now > frist:
        return abgelehnt(f"Prüffrist am {frist.isoformat()} abgelaufen ({(now - frist).days} Tage her) "
                         f"– der Zustand muss neu geprüft werden; Verlängern ist eine "
                         f"Menschen-Entscheidung, kein Schalter")
    hinweise = []
    if blockierer is None:
        hinweise.append("Ruleset-Details offline nicht prüfbar (`--rules-file`): ob ein neues "
                        "Ruleset direkte Pushes blockiert, ist in diesem Lauf nicht bewiesen.")
    elif blockierer:
        namen = ", ".join(f"„{b.get('name')}“ (#{b.get('id')})" for b in blockierer)
        return abgelehnt(f"ein aktives Ruleset blockiert direkte Pushes auf `{branch}`: {namen} – "
                         f"das ist der Vorfall vom 19.09.2026, nicht der dokumentierte Zustand")
    return {"gilt": True, "grund": "Befund entspricht exakt der hinterlegten Erklärung",
            "hinweise": hinweise, "frist": frist.isoformat(), "tage": (frist - now).days}


def dauerzustand_meldung(zustand: dict, urteil: dict, erwartet: str, branch: str,
                         pruefung: dict, strict: bool = False) -> list[str]:
    """Der Text zum bekannten Dauerzustand: rotes Kreuz ja, Vorfall nein.

    Bewusst kein ✅ und kein „alles in Ordnung": Die Wache beschreibt denselben
    Befund wie im harten Modus – nur mit Einordnung, Evidenz und Verfallsdatum.
    """
    zeilen = [("🛑 PFLICHT-CHECK-VERTRAG VERLETZT – BEKANNT: dokumentierter Dauerzustand"
               + (" · strenge Meldung wegen `--strict`" if strict else " · kein Vorfall"))]
    zeilen.append(f"   Befund: {urteil.get('grund', '')}")
    zeilen.append(f"   festgestellt {zustand.get('festgestellt', '?')} · dokumentiert "
                  f"{zustand.get('dokumentiert', '?')} · zu prüfen bis "
                  f"{pruefung.get('frist') or '?'}"
                  + (f" (noch {pruefung['tage']} Tage)" if pruefung.get("tage") is not None else ""))
    zeilen.append(f"   Warum der Vertrag hier nicht erfüllbar ist: {zustand.get('zweck', '')}")
    for titel, beleg in (zustand.get("belege") or {}).items():
        zeilen.append(f"     · {titel}: {beleg}")
    zeilen.append("   Was unverändert schützt: diese Prüfung läuft vollständig weiter und meldet "
                  "jede Abweichung von diesem Stand als Vorfall – anderer Befund, neues Ruleset, "
                  "abgelaufene Frist. Der harte Stopp (`integrity_guard.py --gate`) läuft vor ihr "
                  "und stoppt bei Drift in den Kerndateien weiterhin die Produktion.")
    if strict:
        zeilen.append("   Verhalten: `--strict` – dieser Lauf meldet Exit 1 und ::error::, als wäre "
                      "es ein Vorfall. Ohne den Schalter folgt derselbe Befund als Exit 0 mit "
                      "::warning::; das 🛑 steht in beiden Modi im Log.")
    else:
        zeilen.append("   Verhalten: Exit 0 und ::warning:: im PR-Gate; das 🛑 bleibt in Log und "
                      "Step-Summary stehen. Kein `continue-on-error`, kein Überspringen – die Folge "
                      "ist weicher, die Prüfung nicht.")
        zeilen.append("   Hart schalten: `--strict` (oder PFLICHTCHECK_STRICT=1) meldet genau diesen "
                      "Befund wieder als Vorfall – für Admin-Sitzungen und Nachprüfungen.")
    zeilen.append(f"   Reparatur bleibt möglich und unverändert dokumentiert: "
                  f"{zustand.get('runbook', RUNBOOK)} → Abschnitt „{zustand.get('runbook_abschnitt', '')}“.")
    for hinweis in pruefung.get("hinweise") or []:
        zeilen.append(f"   ⚠️  {hinweis}")
    return zeilen


def dauerzustand_ueberholt(zustand, urteil: str, erwartet: str, branch: str) -> list[str]:
    """Grün, aber die Erklärung liegt noch im Vertrag: sie ist überholt und muss weg."""
    if not isinstance(zustand, dict) or not zustand or urteil != VERLANGT:
        return []
    return [f"ℹ️  Der dokumentierte Dauerzustand ist überholt: `{branch}` verlangt `{erwartet}` "
            f"wieder – der Vertrag ist erfüllt. "
            f"`governance_contract.PFLICHT_CHECK_DAUERZUSTAND` im selben PR löschen (und Frist "
            f"sowie Belege mit), sonst erklärt der Vertrag einen Zustand, den es nicht mehr gibt. "
            f"Ablauf: {zustand.get('runbook', RUNBOOK)}"]


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


def workflows_laden() -> dict[str, str]:
    """Alle Workflow-Dateien des Hauses (Name → Text). read-only, kein Netz."""
    verzeichnis = os.path.join(BLOG_DIR, ".github", "workflows")
    texte: dict[str, str] = {}
    try:
        namen = sorted(os.listdir(verzeichnis))
    except OSError:
        return texte
    for name in namen:
        if not name.endswith((".yml", ".yaml")):
            continue
        try:
            with open(os.path.join(verzeichnis, name), encoding="utf-8") as fh:
                texte[name] = fh.read()
        except OSError:
            continue
    return texte


def bypass_pruefung(repo: str, token: str, branch: str, rules_file: str = "") -> list[str]:
    """Nachprüfung im GRÜNEN Fall: Der Vertrag ist erfüllt – kommt die Automation
    trotzdem noch durch? Liefert Meldungszeilen (leer = nichts zu melden) und
    ändert nie das Urteil (best effort: kein Netz/kein Repo → keine Meldung)."""
    if not repo or rules_file:
        return []
    liste, fehler = api_get(f"/repos/{repo}/rulesets", token)
    if fehler or not isinstance(liste, list):
        return []
    details = []
    for rs in liste[:10]:
        if isinstance(rs, dict) and rs.get("target", "branch") == "branch" and "id" in rs:
            d, f2 = api_get(f"/repos/{repo}/rulesets/{rs['id']}", token)
            if isinstance(d, dict) and not f2:
                details.append(d)
    blocker = blockiert_direkte_pushes(details, branch)
    unbekannt = [f"⚠️  Actions-Bypass für Ruleset #{rs.get('id', '?')} nicht prüfbar: "
                 "API liefert bypass_actors nicht; Frank muss die Admin-Ansicht prüfen."
                 for rs in details if rs.get("enforcement") == "active"
                 and zielt_auf(rs, branch) and "bypass_actors" not in rs
                 and any(r.get("type") in ("required_status_checks", "pull_request")
                         for r in rs.get("rules") or [])]
    if not blocker:
        return unbekannt
    workflows = workflows_laden()
    pusher = direkt_pusher(workflows)
    if not pusher:
        return unbekannt   # niemand pusht direkt – dann bindet der Check nur PRs (gewollt)
    zeilen = list(unbekannt)
    for b in blocker:
        pfad = gc.PFLICHT_CHECK_WORKFLOW
        nur_pr = workflow_nur_pull_request(workflows.get(os.path.basename(pfad), ""))
        checks = ", ".join(f"`{c}`" for c in b["checks"]) or "Pull Request"
        zeilen.append(f"⚠️  Schein-Sicherheit: Ruleset „{b['name']}“ (#{b['id']}) verlangt "
                      f"{checks} auf `{branch}`, hat aber KEINEN Bypass-Akteur für GitHub Actions (Integration 15368, always).")
        zeilen.append("Pflicht-Checks gelten auch für DIREKTE Pushes"
                      + (f" – {checks} entsteht jedoch nur in Pull Requests "
                         f"(Trigger in {pfad}: pull_request, kein push)." if nur_pr
                         else " – jeder Push ohne bestandenen Check wird abgelehnt."))
        gezeigt = ", ".join(pusher[:6]) + (f" … und {len(pusher) - 6} weitere"
                                           if len(pusher) > 6 else "")
        zeilen.append(f"Betroffene Automation ({len(pusher)} Workflows committen selbst auf "
                      f"`{branch}`): {gezeigt}.")
        zeilen.append("Folge: Push abgelehnt → git_sync.sh bricht sofort mit Klasse „schutz“ ab "
                      "→ State wird nicht persistiert; Deploy veröffentlicht trotzdem nach seinen Inhalts-Gates.")
        zeilen.append("Reparatur (Admin, Menschen vorbehalten): Bypass-Akteur für die Automation "
                      "ODER Ruleset-Schichtung – Lösch-/Force-Push-Schutz ohne Bypass, "
                      "PR-/Pflicht-Check mit Bypass (Integration 15368, Modus „always“).")
        zeilen.append(f"Anleitung + Admin-Request: {RUNBOOK}, Abschnitt "
                      "„Direkte Pushes und Automation“.")
    return zeilen


# --------------------------------------------------------------------------- #
#  Automation: Betriebssignal, getrennt vom PR-Merge-Vertrag
# --------------------------------------------------------------------------- #
def zeitpunkt(value: str) -> dt.datetime:
    stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    if stamp.tzinfo is None:
        raise ValueError("Zeitstempel ohne Zeitzone")
    return stamp


def bot_emails(workflows: dict[str, str]) -> set[str]:
    """Explizite lokale Automation-Identitäten, keine Heuristik auf 'bot' im Namen."""
    emails = {"41898282+github-actions[bot]@users.noreply.github.com",
              "github-actions[bot]@users.noreply.github.com"}
    for name in direkt_pusher(workflows):
        emails.update(re.findall(r'git config user\.email [\'\"]([^\'\"\s$]+)[\'\"]', workflows[name]))
    return emails


def bot_zeitpunkte(commits: list[dict], emails: set[str]) -> list[dt.datetime]:
    result = []
    for c in commits:
        # commit.committer.date misst den Stand auf dem Branch, nicht das u.U.
        # Wochen alte Autorendatum. API-Identität ODER explizite Workflow-Mail.
        details = c["commit"]
        bot = any((c.get(role) or {}).get("type") == "Bot"
                  or (c.get(role) or {}).get("login") == "github-actions[bot]"
                  or (details.get(role) or {}).get("email") in emails
                  for role in ("author", "committer"))
        if bot:
            result.append(zeitpunkt(details["committer"]["date"]))
    return result


def automation_befund(last_bot: dt.datetime | None, runs: list[dict],
                       pusher: list[str], now: dt.datetime) -> dict:
    """ROT genau bei >24h Bot-Stille und abgeschlossenem Writer-Cron in 24h.

    Kein kausaler Beweis: auch No-op-Läufe können keine Commits erzeugen.
    Deshalb nennt die Meldung die Evidenz und fordert die Push-Logs zur Prüfung.
    Keine/kaputte Messung wird INFO, niemals ein erfundenes Grün oder Rot.
    """
    def info(msg):
        return {"level": "info", "code": "probe_skipped", "message": msg}
    if last_bot is None:
        return info("Kein letzter Bot-Commit nachweisbar – Automation nicht prüfbar.")
    age = (now - last_bot).total_seconds() / 3600
    if age < 0:
        return info("Bot-Commit liegt in der Zukunft – Automation nicht prüfbar.")
    cron = []
    for r in runs:
        if (r.get("event") != "schedule" or r.get("head_branch") != "main"
                or r.get("status") != "completed"
                or r.get("path", "").removeprefix(".github/workflows/") not in pusher):
            continue
        started = zeitpunkt(r.get("run_started_at") or r["created_at"])
        if now - dt.timedelta(hours=24) <= started <= now and started > last_bot:
            cron.append(r)
    if age > 24 and cron:
        return {"level": "red", "code": "automation_blocked",
                "message": "Automation durch Branch-Schutz blockiert: "
                           f"letzter Bot-Commit auf main {last_bot.isoformat()} ({age:.1f} h); "
                           f"{len(cron)} abgeschlossene Writer-Cron-Läufe in 24 h "
                           f"(z. B. Run {cron[0]['id']}). "
                           "Verdacht: Push-Logs/Bypass prüfen, auch No-op möglich. " + RUNBOOK}
    if age > 24:
        return info(f"Bot-Commit {age:.1f} h alt, aber kein abgeschlossener Writer-Cron "
                    "in den letzten 24 h nachgewiesen – kein Blockade-Befund.")
    return {"level": "green", "code": "ok",
            "message": f"Letzter Bot-Commit auf main {age:.1f} h alt (höchstens 24 h)."}


def automation_messen(repo: str, token: str, now: dt.datetime | None = None) -> dict:
    """Nur GET, main fest (nie PR-Head). Pagination begrenzt; Lücken sind INFO."""
    now = now or dt.datetime.now(dt.timezone.utc)
    try:
        if not repo:
            raise ValueError("Repository unbekannt")
        workflows = workflows_laden()
        pusher, emails = direkt_pusher(workflows), bot_emails(workflows)
        last_bot = None
        for page in range(1, 11):
            commits, err = api_get(f"/repos/{repo}/commits?sha=main&per_page=100&page={page}", token)
            if err or not isinstance(commits, list):
                raise ValueError(err or "unbrauchbare Commit-Antwort")
            times = bot_zeitpunkte(commits, emails)
            if times:
                last_bot = max(times)
                break
            if len(commits) < 100:
                break
        if last_bot is None:
            return automation_befund(None, [], pusher, now)
        if now - last_bot <= dt.timedelta(hours=24):
            return automation_befund(last_bot, [], pusher, now)
        # GitHub begrenzt gefilterte Run-Abfragen auf 1000 Treffer. Falls diese
        # Grenze erreicht wird, urteilen wir nur bei tatsächlich belegtem Cron.
        since = (now - dt.timedelta(hours=24)).isoformat(timespec="seconds")
        query = urllib.parse.urlencode({"event": "schedule", "branch": "main",
                                        "created": ">=" + since, "per_page": 100})
        for page in range(1, 11):
            payload, err = api_get(f"/repos/{repo}/actions/runs?{query}&page={page}", token)
            if err or not isinstance(payload, dict) or not isinstance(payload.get("workflow_runs"), list):
                raise ValueError(err or "unbrauchbare Run-Antwort")
            runs = payload["workflow_runs"]
            verdict = automation_befund(last_bot, runs, pusher, now)
            if verdict["level"] == "red" or len(runs) < 100:
                return verdict
        return {"level": "info", "code": "probe_skipped",
                "message": "Run-Pagination ausgeschöpft – Automation nicht vollständig prüfbar."}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {"level": "info", "code": "probe_skipped",
                "message": f"Automation nicht prüfbar: {exc}"}


def automation_report(befund: dict) -> str:
    # Bestehendes Governance-Befundformat, INFO als nicht-handlungsbedürftiges
    # AMBER/probe_skipped. Exit-Code allein erzeugt ausdrücklich keinen Alarm.
    level = {"red": "RED", "info": "AMBER", "green": "GREEN"}[befund["level"]]
    msg = befund["message"].replace("|", "/").replace("\n", " ")
    return (f"# Automations-Wache (main)\n\nAmpel: **{level}**\n\n"
            "| Level | Code | Meldung |\n|---|---|---|\n"
            f"| {level} | {befund['code']} | {msg} |\n")


def automation_probe(repo: str = "", report: str = "") -> int:
    befund = automation_messen(repo or repo_aus_umgebung(),
                              os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or "")
    text = automation_report(befund)
    print(text)
    if report:
        with open(report, "w", encoding="utf-8") as fh:
            fh.write(text)
    step_summary([text])
    if befund["level"] != "green":
        annotate("error" if befund["level"] == "red" else "warning", befund["message"])
    return 1 if befund["level"] == "red" else 0


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
def probe(branch: str = "", repo: str = "", rules_file: str = "", strict: bool = False) -> int:
    erwartet, job_id, warnung = erwarteter_check()
    strict = bool(strict) or os.environ.get("PFLICHTCHECK_STRICT", "").strip().lower() in \
        ("1", "true", "ja", "yes")
    branch = (branch or os.environ.get("GITHUB_BASE_REF", "").strip()
              or os.environ.get("PFLICHTCHECK_BRANCH", "").strip() or gc.PFLICHT_CHECK_BRANCH)
    repo = repo or repo_aus_umgebung()
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN") or ""
    print(f"🔒 Pflicht-Check-Wache: Branch-Schutz für `{branch}`"
          + (f" ({repo})" if repo else ""))
    print(f"   erwarteter Check: `{erwartet}` (aus {WORKFLOW_PFAD}"
          + (f", Job-ID `{job_id}`" if job_id else "") + ")")
    if strict:
        print("   Modus: `--strict` – der dokumentierte Dauerzustand wird wie ein Vorfall "
              "gemeldet (Exit 1, ::error::).")
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

    urteil = beurteilen(regeln, erwartet, job_id=job_id, pr_pflicht=True)
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
        # Grün heißt nicht „alles gut“: Kommt die Automation noch durch?
        # Best effort, nur GET, ändert das Urteil nie (Vorfall 19.09.2026).
        zusatz = bypass_pruefung(repo, token, branch, rules_file)
        # Und: gilt die Dauerzustand-Erklärung noch? Ein überholter Freispruch im
        # Vertrag wäre eine zweite Wahrheit über einen Zustand, den es nicht mehr gibt.
        ueberh = dauerzustand_ueberholt(getattr(gc, "PFLICHT_CHECK_DAUERZUSTAND", None),
                                        urteil["urteil"], erwartet, branch)
        for z in zusatz + ueberh:
            print(z if z.startswith(("⚠️", "ℹ️")) else f"   {z}")
        if zusatz:
            annotate("warning", f"Actions-Bypass-Nachprüfung für `{branch}`: "
                                f"{zusatz[0]} Diagnose/Reparatur: {RUNBOOK}")
        if ueberh:
            annotate("warning", "Dauerzustand-Erklärung ist überholt – "
                                f"{ueberh[0].removeprefix('ℹ️  ')}")
        step_summary([f"### ✅ Pflicht-Check `{erwartet}` wird auf `{branch}` verlangt", "",
                      f"Ruleset: {', '.join('#' + i for i in ids) or '–'}"]
                     + (["", *[z.strip() for z in zusatz + ueberh]] if zusatz or ueberh else []))
        return 0

    # ---------------------------------------------------------------------- #
    #  Rot. Erst ansehen, was der Fall ist (Diagnose), dann entscheiden, WIE er
    #  gemeldet wird: als Vorfall – oder als das, was er auf diesem Repo ist,
    #  solange niemand im Repo das Ruleset ändern darf: ein dokumentierter,
    #  befristeter DAUERZUSTAND (Option B, 20.09.2026). Der Befund bleibt sichtbar
    #  und rot; nur die Folge (Exit, Annotation, Alarm) weicht aus. Alles, was
    #  nicht exakt dem Festgestellten entspricht, bleibt hart.
    # ---------------------------------------------------------------------- #
    ruleset_name, alte_namen, details, liste = "", list(urteil["checks"]), [], None
    if repo and not rules_file:
        liste, _f = api_get(f"/repos/{repo}/rulesets", token)
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
    dauer = getattr(gc, "PFLICHT_CHECK_DAUERZUSTAND", None)
    dauer_pfad = dauerzustand_pruefen(dauer, urteil["urteil"], branch, erwartet,
                                      dt.datetime.now(dt.timezone.utc).date(),
                                      blockierer=None if rules_file
                                      else blockiert_direkte_pushes(details, branch))
    if dauer_pfad["gilt"] and isinstance(dauer, dict):
        for zeile in dauerzustand_meldung(dauer, urteil, erwartet, branch, dauer_pfad, strict):
            print(zeile)
        for zeile in ruleset_diagnose(details):
            print(f"   Diagnose: {zeile}")
        if liste == []:
            print("   Diagnose: Das Repository hat kein Ruleset – der Pflicht-Check wurde nie eingetragen.")
        kurz = [f"- festgestellt {dauer.get('festgestellt', '?')} · dokumentiert "
                f"{dauer.get('dokumentiert', '?')} · zu prüfen bis {dauer_pfad['frist'] or '?'}",
                f"- {dauer.get('zweck', '')}"]
        kurz += [f"- Beleg `{titel}`: {text}" for titel, text in (dauer.get("belege") or {}).items()]
        kurz.append("- " + ("Exit 1 (strenge Meldung, `--strict`): der Befund bleibt ein Vorfall."
                            if strict else
                            "Exit 0: kein Vorfall, kein Alarm. Eine Merge-Blockade gab es nie "
                            "(Beleg `kein-merge-blocker`); die Prüfung selbst läuft unverändert."))
        annotate("error" if strict else "warning",
                  f"Pflicht-Check `{erwartet}` auf `{branch}` nicht verlangt – BEKANNT: "
                  f"dokumentierter Dauerzustand ({dauer_pfad['grund']}"
                  + (f", zu prüfen bis {dauer_pfad['frist']}" if dauer_pfad["frist"] else "")
                  + ("). Strenge Meldung wegen --strict, bleibt Vorfall." if strict else
                     "). Hält keinen Merge auf (Beleg: PFLICHT_CHECK_DAUERZUSTAND.belege) und "
                     "lässt den harten Stopp unverändert laufen; Reparatur und Frist: "
                     f"{dauer.get('runbook', RUNBOOK)}"))
        step_summary([f"### 🛑 Pflicht-Check `{erwartet}` auf `{branch}` NICHT verlangt – "
                      "BEKANNT (dokumentierter Dauerzustand)", "", urteil["grund"], "", *kurz,
                      "", f"Reparatur bleibt Admin-Aufgabe, unverändert dokumentiert: "
                      f"{dauer.get('runbook', RUNBOOK)} → Abschnitt „{dauer.get('runbook_abschnitt', '')}“"])
        return 1 if strict else 0

    # Harter Fall – mit Diagnose (best effort, ändert das Urteil nicht) und Reparatur.
    # Die Diagnose liest die Rulesets des Repositories: Meist existiert das
    # Häkchen, es zeigt nur ins Leere (kein Ziel-Zweig, deaktiviert, alter Name).
    print(f"🛑 PFLICHT-CHECK-VERTRAG VERLETZT – {urteil['grund']}")
    if isinstance(dauer, dict) and dauer:
        print(f"   Gilt nicht als dokumentierter Dauerzustand: {dauer_pfad['grund']}")
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
    # 10) Ziel-Treffer: Default-Zweig, refs/heads/…, Glob – und `exclude` sticht
    def _rs(inc, exc=(), rules=None, bypass=None, enf="active"):
        return {"id": 7, "name": "R", "enforcement": enf,
                "conditions": {"ref_name": {"include": list(inc), "exclude": list(exc)}},
                "rules": [_regel((name, GITHUB_ACTIONS_APP_ID))] if rules is None else rules,
                "bypass_actors": bypass}
    for muster in ("~DEFAULT_BRANCH", "~ALL", "main", "refs/heads/main", "refs/heads/*", "*"):
        if not zielt_auf(_rs([muster]), "main"):
            f.append(f"Fall10: Muster `{muster}` trifft `main` nicht.")
    for muster in ("develop", "refs/heads/develop", "release-*"):
        if zielt_auf(_rs([muster]), "main"):
            f.append(f"Fall10b: Muster `{muster}` trifft `main` fälschlich.")
    if zielt_auf(_rs([]), "main"):
        f.append("Fall10c: leere include-Liste darf keinen Zweig treffen (Befund #316).")
    if zielt_auf(_rs(["~DEFAULT_BRANCH"], ["main"]), "main"):
        f.append("Fall10d: `exclude` muss den Treffer aufheben.")

    # 11) Bypass-Lücke: Pflicht-Check ohne Bypass-Akteur blockiert direkte Pushes
    if len(blockiert_direkte_pushes([_rs(["~DEFAULT_BRANCH"], bypass=None)], "main")) != 1:
        f.append("Fall11: Ruleset mit Pflicht-Check und bypass_actors=null wird nicht erkannt.")
    if len(blockiert_direkte_pushes([_rs(["~DEFAULT_BRANCH"], bypass=[])], "main")) != 1:
        f.append("Fall11b: leere Bypass-Liste muss wie „niemand darf vorbei“ gelten.")
    if blockiert_direkte_pushes([_rs(["~DEFAULT_BRANCH"],
                                     bypass=[{"actor_id": 15368, "actor_type": "Integration",
                                              "bypass_mode": "always"}])], "main"):
        f.append("Fall11c: Ruleset MIT Bypass-Akteur darf nicht gemeldet werden.")
    if blockiert_direkte_pushes([_rs(["~DEFAULT_BRANCH"], enf="disabled")], "main"):
        f.append("Fall11d: deaktiviertes Ruleset darf nicht gemeldet werden.")
    if blockiert_direkte_pushes([_rs(["~DEFAULT_BRANCH"],
                                     rules=[{"type": "deletion"}, {"type": "non_fast_forward"}])],
                                "main"):
        f.append("Fall11e: Ruleset ohne Status-Check darf nicht gemeldet werden.")
    if blockiert_direkte_pushes([_rs(["develop"])], "main"):
        f.append("Fall11f: Ruleset auf anderem Zweig darf nicht gemeldet werden.")

    # 12) Direkt-Pusher: nur Workflows mit contents:write UND Push-Aufruf
    pusher = direkt_pusher({
        "deploy.yml": "permissions:\n  contents: write\njobs:\n  a:\n    steps:\n"
                      "      - run: bash scripts/git_sync.sh --push-only\n",
        "nur-push.yml": "permissions:\n  contents: read\n      - run: git push origin main\n",
        "nur-write.yml": "permissions:\n  contents: write\n      - run: hugo\n",
        "gate.yml": "permissions:\n  contents: read\n"})
    if pusher != ["deploy.yml"]:
        f.append(f"Fall12: Direkt-Pusher falsch bestimmt: {pusher}")

    # 13) Trigger-Lage des Gate-Workflows: ohne `push:` entsteht der Check nie direkt
    if not workflow_nur_pull_request("on:\n  pull_request:\n    branches: [main]\njobs:\n  x:\n"):
        f.append("Fall13: pull_request-only Workflow wird nicht als solcher erkannt.")
    if workflow_nur_pull_request("on:\n  push:\n  pull_request:\njobs:\n  x:\n"):
        f.append("Fall13b: Workflow mit push-Trigger darf nicht als PR-only gelten.")
    if workflow_nur_pull_request("on:\n  workflow_dispatch:\njobs:\n  x:\n"):
        f.append("Fall13c: Workflow ohne pull_request darf nicht als PR-only gelten.")

    if beurteilen([_regel((name, 15368))], name, pr_pflicht=True)["urteil"] != PR_SCOPING_FEHLT:
        f.append("Fall14: Check allein ist kein PR-Scoping.")
    scoped = [_regel((name, 15368)), {"type": "pull_request", "parameters": {"required_approving_review_count": 0}}]
    if beurteilen(scoped, name, pr_pflicht=True)["urteil"] != VERLANGT:
        f.append("Fall14: PR-Pflicht mit 0 Approvals wird nicht erkannt.")
    # 14) PR-Scoping: nur Actions/always reicht; PR-Pflicht ist selbst ein Blocker.
    for actor in ({"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"},
                  {"actor_id": 15368, "actor_type": "Integration", "bypass_mode": "pull_request"},
                  {"actor_id": 99, "actor_type": "Integration", "bypass_mode": "always"}):
        if not blockiert_direkte_pushes([_rs(["main"], bypass=[actor], rules=[{"type": "pull_request"}])]):
            f.append("Fall14: PR-Regel ohne Actions/always muss direkte Pushes blockieren.")
    if zielt_auf(_rs(["~DEFAULT_BRANCH"]), "feature"):
        f.append("Fall14b: Default-Branch-Regel trifft fälschlich einen PR-Head.")
    # 15) Uhrfester Betriebsnachweis, kein Netz/keine Dateiänderung.
    now = dt.datetime(2026, 9, 19, 12, tzinfo=dt.timezone.utc)
    run = {"id": 7, "event": "schedule", "head_branch": "main", "status": "completed",
           "path": ".github/workflows/engine.yml", "created_at": "2026-09-19T11:00:00Z"}
    for age, runs, expected in ((25, [run], "red"), (24, [run], "green"),
                                (23, [run], "green"), (25, [], "info")):
        got = automation_befund(now - dt.timedelta(hours=age), runs, ["engine.yml"], now)
        if got["level"] != expected:
            f.append(f"Fall15: Bot-Stille {age}h/{len(runs)} Cron: {got}")
    import governance_gate as gate
    red = automation_befund(now - dt.timedelta(hours=25), [run], ["engine.yml"], now)
    classified = gate.classify("automation", automation_report(red))
    if gate.decide_policy({"automation": classified})[:2] != ("RED", "report"):
        f.append("Fall15b: Automations-Stillstand wird im Governance-Gate nicht ROT.")

    # 16) Dauerzustand: weich NUR für den exakt dokumentierten Befund.
    heute = dt.date(2026, 10, 1)

    def _dz(**anderungen):
        z = {"zweck": "Rulesets ändern ist Admin-Aufgabe (C15), kein Token hier hat das Recht",
             "check": name, "branch": "main", "urteil_erwartet": UNGESCHUETZT,
             "festgestellt": "2026-09-19", "dokumentiert": "2026-09-20",
             "pruefung_bis": "2026-12-31",
             "belege": {"kein-merge-blocker": "PR #327 ist bei FAILURE gemergt (4b91938)"},
             "runbook": RUNBOOK, "runbook_abschnitt": "Dauerzustand"}
        z.update(anderungen)
        return z
    if dauerzustand_pruefen(_dz(), UNGESCHUETZT, "main", name, heute)["gilt"] is not True:
        f.append("Fall16: der dokumentierte Befund wird nicht als Dauerzustand angenommen.")
    for code in (FEHLT, FALSCHE_QUELLE, PR_SCOPING_FEHLT, VERLANGT, NICHT_PRUEFBAR):
        if dauerzustand_pruefen(_dz(), code, "main", name, heute)["gilt"]:
            f.append(f"Fall16b: `{code}` läuft unter der Dauerzustand-Erklärung durch.")
    for feld, wert in (("check", "Anderes-Siegel"), ("branch", "develop"),
                       ("urteil_erwartet", FEHLT), ("pruefung_bis", "31.12.2026"),
                       ("pruefung_bis", "")):
        if dauerzustand_pruefen(_dz(**{feld: wert}), UNGESCHUETZT, "main", name, heute)["gilt"]:
            f.append(f"Fall16c: Abweichung im Feld `{feld}` ({wert!r}) wird freigesprochen.")
    for kaputt in (None, {}, [], "UNGESCHUETZT"):
        if dauerzustand_pruefen(kaputt, UNGESCHUETZT, "main", name, heute)["gilt"]:
            f.append(f"Fall16d: unbrauchbare Erklärung {kaputt!r} erteilt einen Freispruch.")

    # 17) Frist: am Stichtag noch weich, am Tag danach wieder Vorfall.
    if dauerzustand_pruefen(_dz(), UNGESCHUETZT, "main", name, dt.date(2026, 12, 31))["gilt"] is not True:
        f.append("Fall17: der letzte Tag der Prüffrist muss noch gelten.")
    spat = dauerzustand_pruefen(_dz(), UNGESCHUETZT, "main", name, dt.date(2027, 1, 1))
    if spat["gilt"] or "abgelaufen" not in spat["grund"] or "1 Tage" not in spat["grund"]:
        f.append(f"Fall17b: abgelaufene Frist meldet nicht als Vorfall: {spat}")

    # 18) Blocker und Blindheit: neues Ruleset ohne Bypass ist ein anderer Vorfall,
    #     die Offline-Lücke ein Hinweis – nie ein stiller Freispruch.
    blockiert = [{"id": 99, "name": "Zusatz-Ruleset", "checks": [name], "pull_request": True}]
    zu = dauerzustand_pruefen(_dz(), UNGESCHUETZT, "main", name, heute, blockierer=blockiert)
    if zu["gilt"] or "Zusatz-Ruleset" not in zu["grund"]:
        f.append(f"Fall18: Ruleset ohne Bypass wird unter dem Dauerzustand versteckt: {zu}")
    blind = dauerzustand_pruefen(_dz(), UNGESCHUETZT, "main", name, heute, blockierer=None)
    if not blind["gilt"] or not blind["hinweise"]:
        f.append(f"Fall18b: offline muss die Freigabe ihre Blindheit nennen: {blind}")
    if dauerzustand_pruefen(_dz(), UNGESCHUETZT, "main", name, heute, blockierer=[])["hinweise"]:
        f.append("Fall18c: geprüfte Ruleset-Liste ohne Blocker erzeugt einen unnötigen Hinweis.")

    # 19) Der weiche Text wäscht nichts grün: Kreuz, Frist, Evidenz, Ausweg bleiben stehen.
    ur = {"grund": "Kein aktives Ruleset verlangt einen Status-Check – Deko."}
    mel = "\n".join(dauerzustand_meldung(_dz(), ur, name, "main",
                                        dauerzustand_pruefen(_dz(), UNGESCHUETZT, "main", name, heute)))
    for muss in ("🛑", "BEKANNT", "kein Vorfall", "zu prüfen bis 2026-12-31", "PR #327",
                 "integrity_guard.py --gate", "--strict", RUNBOOK, "Exit 0"):
        if muss not in mel:
            f.append(f"Fall19: weicher Befundtext ohne „{muss}“ – es fehlt die Einordnung.")
    if "Exit 1" in mel:
        f.append("Fall19b: der weiche Modus kündigt Exit 1 an.")
    hart = "\n".join(dauerzustand_meldung(_dz(), ur, name, "main",
                                         dauerzustand_pruefen(_dz(), UNGESCHUETZT, "main", name, heute),
                                         strict=True))
    if "Exit 1" not in hart or "kein Vorfall" in hart:
        f.append("Fall19c: --strict meldet den bekannten Zustand nicht als Vorfall.")
    ueb = dauerzustand_ueberholt(_dz(), VERLANGT, name, "main")
    if not ueb or "überholt" not in ueb[0] or "PFLICHT_CHECK_DAUERZUSTAND" not in ueb[0]:
        f.append(f"Fall19d: grüner Lauf mit liegender Erklärung meldet nicht: {ueb}")
    for urteil in (UNGESCHUETZT, FEHLT, NICHT_PRUEFBAR):
        if dauerzustand_ueberholt(_dz(), urteil, name, "main"):
            f.append(f"Fall19e: Überholt-Hinweis bei `{urteil}` ist fehl am Platz.")
    if dauerzustand_ueberholt(None, VERLANGT, name, "main"):
        f.append("Fall19f: Überholt-Hinweis ohne hinterlegte Erklärung.")

    # 20) Die echte Erklärung im Vertrag ist eine Wahrheit mit Wurzeln.
    echt = getattr(gc, "PFLICHT_CHECK_DAUERZUSTAND", None)
    if not isinstance(echt, dict) or not echt:
        f.append("Fall20: gc.PFLICHT_CHECK_DAUERZUSTAND fehlt – jeder Lauf meldet den "
                 "Dauerzustand weiter als Vorfall (das ist korrekt, aber hier nicht gemeint).")
    else:
        for feld, soll in (("check", name), ("branch", gc.PFLICHT_CHECK_BRANCH),
                           ("urteil_erwartet", UNGESCHUETZT)):
            if str(echt.get(feld)) != soll:
                f.append(f"Fall20: Erklärung sagt {echt.get(feld)!r} für `{feld}`, Vertrag `{soll}`.")
        for feld in ("festgestellt", "dokumentiert", "pruefung_bis"):
            if _isodatum(echt.get(feld)) is None:
                f.append(f"Fall20: Erklärung.{feld} ist kein ISO-Datum ({echt.get(feld)!r}).")
        if not (echt.get("belege") or {}):
            f.append("Fall20: Erklärung ohne Belege ist eine Behauptung.")
        try:
            with open(os.path.join(BLOG_DIR, echt.get("runbook") or RUNBOOK), encoding="utf-8") as fh:
                runbuch = fh.read()
        except OSError:
            runbuch = ""
        if runbuch and str(echt.get("runbook_abschnitt")) not in runbuch:
            f.append(f"Fall20: {echt.get('runbook')} führt den Abschnitt "
                     f"„{echt.get('runbook_abschnitt')}“ nicht – die Wache verweist ins Leere.")
    if f:
        print("❌ PFLICHTCHECK-SELBSTTEST FEHLGESCHLAGEN:")
        for z in f:
            print("   -", z)
        return 2
    print(f"✅ Pflichtcheck-Selbsttest bestanden (20 Fallgruppen: Urteile, Diagnose, Reparatur, "
          f"Namensquelle, Ziel-Treffer, Bypass-Lücke, Direkt-Pusher, Trigger-Lage, "
          f"Dauerzustand-Freigabe – erwartet `{gc.PFLICHT_CHECK_NAME}`).")
    return 0


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Verlangt der Branch-Schutz den Check, der hier läuft?")
    ap.add_argument("--automation", action="store_true", help="Bot-Stille auf main gegen Writer-Crons prüfen")
    ap.add_argument("--report", default="", help="Automation: Governance-Befunddatei schreiben")
    ap.add_argument("--selftest", action="store_true", help="Logik-Beweis ohne Netz (schreibt nie)")
    ap.add_argument("--branch", default="", help="Ziel-Zweig (Standard: GITHUB_BASE_REF, sonst main)")
    ap.add_argument("--repo", default="", help="owner/repo (Standard: GITHUB_REPOSITORY, sonst origin)")
    ap.add_argument("--rules-file", default="", help="Regel-JSON statt API (offline/Diagnose)")
    ap.add_argument("--strict", action="store_true",
                    help="dokumentierten Dauerzustand wieder als Vorfall melden (Exit 1, ::error::)")
    args = ap.parse_args(argv)
    if args.selftest:
        return selftest()
    if args.automation:
        if args.rules_file or args.branch not in ("", "main"):
            ap.error("--automation misst nur main live (kein --rules-file)")
        if args.strict:
            ap.error("--strict betrifft den PR-Vertrag, nicht die Automations-Wache "
                     "(deren Urteil ist unabhängig von der Dauerzustand-Erklärung)")
        return automation_probe(repo=args.repo, report=args.report)
    if args.report:
        ap.error("--report verlangt --automation")
    return probe(branch=args.branch, repo=args.repo, rules_file=args.rules_file,
                 strict=args.strict)


if __name__ == "__main__":
    sys.exit(main())
