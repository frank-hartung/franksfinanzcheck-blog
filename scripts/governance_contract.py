#!/usr/bin/env python3
"""
GOVERNANCE-KONTRAKT – die Checks, damit #206 nie wiederkehrt.

Ein Governance-Report, der jede Woche dasselbe „Problem" meldet, das keines ist,
ist kein Messinstrument, sondern Lärm. Und Lärm ist im Betrieb teurer als der
Fehler selbst: echte rote Befunde gehen in der Gewohnheit unter (Alarm-Müdigkeit).
Deshalb werden die Regeln, die den Dauer-Alarm erzeugt haben, jetzt als
**materieller Vertrag** im Repo gespeichert und vor jedem Merge geprüft.

Geprüft werden ausschließlich Im-Repo-Artefakte (Workflows, Reports, Manifeste) –
ohne Netzwerk, ohne API, determinisch. Läuft lokal, im Premium-Governance-Lauf
(Preflight) und im Qualitäts-Gate (bei jedem Push/PR auf main).

  C1  Reihenfolge       – Scorecard (Sicht) MUSS nach den Messschritten laufen
  C2  Bau-Grundlage     – Hugo-Build darf kein `|| true` schlucken; Scheingrün
                          ohne gemessenen Build ist verboten
  C3  Messkette komplett– jeder Gate-Schritt wird aus dem Workflow gefüttert
  C4  Issue-Policy       – kein Issue ohne Gate-Entscheidung, kein Duplikat
                          (update statt create), schließen bei Grün
  C5  Nachweis-Provenienz– `--record-success` nur mit `--proof-by`, nie im
                          Governance-Lauf selbst (kein Selbst-Waschen), nur für
                          registrierte Secrets
  C6  Selbsttests grün   – alle Governance-Wachen haben `--selftest` und bestehen
  C7  Datenkonsistenz    – Manifest ↔ Report ↔ Scorecard müssen dieselbe Ampel
                          zeigen (oder die Scorecard kennzeichnet STALE/nicht
                          gemessen ausdrücklich)
  C8  Commit-Hygiene     – `git add` im Workflow darf nur versionierbare Pfade
                          nennen (Sonst: harter Abbruch, vgl. #205)
  C9  Secret-Leak-Schutz – Report-Dateien dürfen kein Token-Material enthalten
  C10 Token-Broker      – jedes Pinterest-Skript holt seinen Token beim zentralen
                          Broker; kein Skript baut sich eine eigene Reihenfolge
                          (sonst prüft die Wache einen anderen Token als der Bot
                          benutzt – Kernbefund #206)
  C11 Token-Lebenszyklus– es gibt einen täglichen Erneuerungslauf, der den
                          rotierten Refresh-Token sichert und sich selbst heilt
                          (ein 30-Tage-Secret von Hand ist kein Betrieb)
  C13 Nachweis-Echtheit – ein Pinterest-Nachweis läuft immer mit Live-Probe
                          (`--verify`), nur die Token-Wache rotiert proaktiv
                          (PINTEREST_TOKEN_WACHE=1), und die Autorisierung
                          fordert die echten v5-Scopes (#219)
  C12 Label-Garantie    – jeder Workflow, der ein Issue mit Label erzeugt, legt
                          das Label vorher an; sonst scheitert der Melder am
                          Melden (Ursache des roten Laufs in #209)

Exit-Codes: 0 = Vertrag erfüllt · 1 = Verletzung(en) · 2 = Selbsttest/Fehler

Nutzung:
  python3 scripts/governance_contract.py            # prüfen
  python3 scripts/governance_contract.py --md docs/GOVERNANCE-KONTRAKT.md
  python3 scripts/governance_contract.py --quick    # ohne Selbsttest-Läufe (schnell)
  python3 scripts/governance_contract.py --python .venv/bin/python   # lokale Abweichung
  python3 scripts/governance_contract.py --selftest
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

GOV_WORKFLOW = os.path.join(BLOG_DIR, ".github", "workflows", "premium-governance.yml")
WORKFLOWS_DIR = os.path.join(BLOG_DIR, ".github", "workflows")
# Mindestmenge der Wachen, die der Vertrag prüft (C6: jede mit `--selftest`).
# schema_seo_gate.py + generate_pwa_icons.py sind der 11.09.2026 dazugekommen:
# das doppelte `| jsonify` in schema_article.html hatte die Article-Schema aller
# Live-Artikel unbrauchbar gemacht, und die Site registrierte einen Service
# Worker ohne Manifest. Beide Fehler waren im Build unsichtbar – jede Korrektur
# ohne Wache hier wäre eine Leihgabe.
GUARDS = ["editorial_scorecard.py", "cwv_guard.py", "secrets_age_guard.py",
          "decay_radar.py", "governance_gate.py", "readability_check.py",
          "umami_clicks.py", "click_attribution.py", "awin_provisions.py",
          "pinterest_perf_feedback.py", "pinterest_token.py", "pinterest_auth.py",
          "schema_seo_gate.py", "generate_pwa_icons.py", "report_hygiene.py",
          "live_policy_guard.py", "draft_triage.py", "check_uniqueness.py",
          "audio_coverage_check.py", "newsletter_digest.py"]

# Skripte, die mit der Pinterest-API sprechen, müssen ihren Token vom Broker
# holen. Ausnahmen: der Broker selbst und die Krypto-/OAuth-Schicht darunter.
TOKEN_BROKER = "pinterest_token"
TOKEN_BROKER_EXEMPT = {"pinterest_token.py", "pinterest_auth.py"}
TOKEN_WORKFLOW = "pinterest-token.yml"

# Reihenfolge-Vertrag: diese Schritte sind Messungen, die vor der Sicht liegen müssen
MEASURE_STEPS = ("decay", "cwv", "secrets", "lesbarkeit", "pinperf", "clicks", "awin",
                 "live-policy")
VIEW_STEP = "scorecard"


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


# --------------------------------------------------------------- Schritt-Modell

def step_blocks(workflow_text):
    """YAML grob in `name:`-Schritte zerlegen (der Workflow ist bot-geschrieben,
    deshalb bewusst einfach gehalten – ein voller YAML-Parser wäre hier fragiler)."""
    blocks = []
    cur_name, cur = None, []
    for line in workflow_text.splitlines():
        m = re.match(r"^\s*-\s+name:\s*(.+?)\s*$", line)
        if m:
            if cur_name is not None:
                blocks.append((cur_name, "\n".join(cur)))
            cur_name, cur = m.group(1).strip().strip("'\""), []
            continue
        if cur_name is not None:
            cur.append(line)
    if cur_name is not None:
        blocks.append((cur_name, "\n".join(cur)))
    return blocks


STEP_SIGNATURES = {
    "decay":     (r"--emit\s+decay\b", r"decay_radar\.py"),
    "lesbarkeit": (r"--emit\s+lesbarkeit\b", r"readability_check\.py"),
    "cwv":       (r"--emit\s+cwv\b", r"cwv_guard\.py"),
    "secrets":   (r"--emit\s+secrets\b", r"secrets_age_guard\.py"),
    "pinperf":   (r"--emit\s+pinperf\b", r"pinterest_perf_feedback\.py"),
    "clicks":    (r"--emit\s+clicks\b", r"click_attribution\.py"),
    "awin":      (r"--emit\s+awin\b", r"awin_provisions\.py"),
    "live-policy": (r"--emit\s+live-policy\b", r"live_policy_guard\.py"),
    "scorecard": (r"--emit\s+scorecard\b", r"editorial_scorecard\.py"),
}


def step_index(workflow_text, only=None):
    """Position (Index) der Schritte, die eine Kennzahl messen bzw. bündeln."""
    pos = {}
    for i, (_name, body) in enumerate(step_blocks(workflow_text)):
        if "--selftest" in body:
            continue          # Preflight-Selbsttests sind keine Messläufe
        for step, pats in STEP_SIGNATURES.items():
            if only and step not in only:
                continue
            if any(re.search(pat, body) for pat in pats):
                pos.setdefault(step, i)
    return pos


def c1_ordering(workflow_text):
    """C1: Die Sicht (Scorecard) darf nie vor ihren Messungen laufen."""
    out = []
    idx = step_index(workflow_text)
    if VIEW_STEP not in idx:
        out.append(("C1", "Kein Scorecard-Schritt (scripts/editorial_scorecard.py) im "
                          "Governance-Workflow gefunden."))
        return out
    for step in MEASURE_STEPS:
        if step in idx and idx[step] > idx[VIEW_STEP]:
            out.append(("C1", f"`{step}` (Messung, Schritt {idx[step]}) läuft NACH der "
                              f"Scorecard (Schritt {idx[VIEW_STEP]}) – die Scorecard "
                              "zeigt damit Werte des Vorlaufs. Genau der #206-Fehler: "
                              "AMBER in der Sicht, GREEN im Wächter, -7 Punkte Grund "
                              "in einem Lauf, das nichts mit Performance zu tun hat."))
    return out


def c2_build_not_swallowed(workflow_text):
    out = []
    for name, body in step_blocks(workflow_text):
        if "hugo" not in (name + body).lower():
            continue
        if re.search(r"hugo[^\n]*\|\|\s*true", body):
            out.append(("C2", f"Bau-Schritt „{name}“ verschluckt Hugo-Fehler mit `|| true` "
                              "– ein fehlgeschlagener Build wäre unsichtbar und die "
                              "Performance-Messung würde auf einem leeren/alten Baum grün."))
        if "governance_gate.py --emit build" not in body and "--require-green" not in body:
            if "hugo --minify" in body:
                out.append(("C2", "Hugo-Build meldet sein Ergebnis nicht an das "
                                  "Governance-Gate (`--emit build --require-green`)."))
    return out


def c3_measure_chain_complete(workflow_text, gate_text):
    out = []
    steps = re.findall(r'^\s{4}"([a-z_]+)":\s*\{', gate_text, re.M)
    if not steps:
        steps = re.findall(r'^\s+"([a-z_]+)":\s*\{"', gate_text, re.M)
    for step in steps:
        if step in ("scorecard",):
            continue
        if not re.search(rf"--emit\s+{step}\b", workflow_text):
            out.append(("C3", f"Gate-Kennung `{step}` wird im Governance-Workflow nie "
                              "übermittelt – dieser Befund taucht in keiner Entscheidung auf."))
    return out


def c4_issue_policy(workflow_text):
    out = []
    low = workflow_text
    if "governance_gate.py --decide" not in low:
        out.append(("C4", "Der Workflow entscheidet nicht über `governance_gate.py --decide` "
                          "– damit hängt das Issue an rohen Exit-Codes (Ursache des "
                          "Wochen-Duplikat-Issues #206)."))
    if re.search(r"issues\.create\(", low) and "--decide" not in low:
        out.append(("C4", "Issue-Erzeugung ohne Gate-Entscheidung (creates Duplikate)."))
    if "issues.create(" in low.replace(" ", "") and "gh issue list" not in low \
            and "issues.listForRepo" not in low:
        out.append(("C4", "Issue-Erzeugung ohne Duplikat-Prüfung (listForRepo / gh issue list)."))
    if "governance" in low and "close" not in low.lower():
        out.append(("C4", "Kein Selbstheilungs-Pfad: ein Governance-Issue wird nie "
                          "geschlossen, wenn alles grün ist (action=close fehlt)."))
    return out


def c5_record_provenance(workflow_texts, secrets_text):
    """Nachweis-Provenienz: workflow_texts = dict pfad -> Text."""
    out = []
    known = set(re.findall(r'^\s{4}"([A-Z0-9_]+)":\s*\{', secrets_text, re.M))
    for path, raw_text in workflow_texts.items():
        rel = os.path.basename(path)
        # Shell-Zeilenfortsetzung ( \ + Umbruch ) zusammenziehen, sonst übersieht
        # die Regel ein --proof-by in der Folgezeile.
        text = re.sub(r"\\\s*\n\s*", " ", raw_text)
        for m in re.finditer(r"--record-success\s+([A-Z0-9_]+)([^\n]*)", text):
            var, rest = m.group(1), m.group(2)
            if known and var not in known:
                out.append(("C5", f"{rel}: `--record-success {var}` – Secret nicht in "
                                  "`secrets_age_guard.SECRETS` registriert."))
            if "--proof-by" not in rest:
                out.append(("C5", f"{rel}: Nachweis für `{var}` ohne `--proof-by` – "
                                  "ohne Herkunft ist der Eintrag nicht beweisbar und "
                                  "kann nicht auf Plausibilität geprüft werden."))
        if rel == "premium-governance.yml" and "--record-success" in text:
            out.append(("C5", "premium-governance.yml vermerkt Secret-Erfolg, obwohl der "
                              "Lauf die Secrets nicht benutzt (Selbst-Waschen). "
                              "Stattdessen: `secrets_age_guard.py --verify`."))
        if rel == "premium-governance.yml" and "secrets_age_guard.py" in text \
                and "--verify" not in text:
            out.append(("C5", "premium-governance.yml prüft Secrets ohne Live-Probe "
                              "(`--verify`) – vorhanden ist nicht gleich funktioniert."))
    return out


def c6_selftests(python_bin="python3", quick=False):
    out = []
    if quick:
        for name in GUARDS:
            src = _read(os.path.join(BLOG_DIR, "scripts", name))
            if "--selftest" not in src:
                out.append(("C6", f"scripts/{name} hat keinen `--selftest`."))
        return out
    for name in GUARDS:
        path = os.path.join(BLOG_DIR, "scripts", name)
        if not os.path.exists(path):
            out.append(("C6", f"scripts/{name} fehlt."))
            continue
        try:
            r = subprocess.run([python_bin, path, "--selftest"], cwd=BLOG_DIR,
                               capture_output=True, text=True, timeout=600)
            if r.returncode != 0:
                tail = (r.stdout or r.stderr or "").strip().splitlines()
                last = tail[-1][:160] if tail else "kein Output"
                out.append(("C6", f"scripts/{name} --selftest Exit {r.returncode}: {last}"))
        except (OSError, subprocess.TimeoutExpired) as exc:
            out.append(("C6", f"scripts/{name} --selftest nicht ausführbar: {exc.__class__.__name__}"))
    return out


def c7_data_consistency(report_texts, manifest):
    out = []
    cwv_report = report_texts.get("CWV-REPORT.md", "")
    verdict_report = None
    m = re.search(r"Gesamt-Ampel:\s*\*\*(GREEN|AMBER|RED)\*\*", cwv_report)
    if m:
        verdict_report = m.group(1)
    verdict_manifest = manifest.get("verdict")
    if verdict_report and verdict_manifest and verdict_report != verdict_manifest:
        out.append(("C7", f"CWV-Report sagt {verdict_report}, Manifest {verdict_manifest} – "
                          "zwei Wahrheiten an einem Tag."))
    date_report = None
    m = re.search(r"\*\*Stand:\*\*\s*(\d{4}-\d{2}-\d{2})", cwv_report)
    if m:
        date_report = m.group(1)
    if date_report and manifest.get("generated") and date_report != manifest["generated"]:
        out.append(("C7", f"CWV-Report (Stand {date_report}) und Manifest "
                          f"({manifest.get('generated')}) sind nicht derselbe Lauf – "
                          "die Scorecard liest einen gemischten Stand."))
    scorecard = report_texts.get("EDITORIAL-SCORECARD.md", "")
    if scorecard and verdict_manifest:
        m = re.search(r"Core-Web-Vitals\s*\|\s*([^|]+?)\s*\|", scorecard)
        if m:
            cell = m.group(1)
            allowed = [verdict_manifest] if manifest.get("build_measured", True) else []
            allowed += ["STALE", "nicht gemessen", "nur static/", "UNKNOWN"]
            if not any(a.split(" (")[0] in cell for a in allowed if a):
                out.append(("C7", f"Scorecard-Zeile „Core-Web-Vitals = {cell}"
                                  f"“ passt nicht zum Manifest ({verdict_manifest}, "
                                  "build_measured="
                                  f"{manifest.get('build_measured')}) – die Sicht zeigt "
                                  "einen Stand, den niemand gemessen hat."))
    return out


def add_tokens(workflow_text):
    """Alle Pfade, die ein Workflow mit `git add` staged (für die Hygiene-Regel)."""
    toks = []
    for line in workflow_text.splitlines():
        m = re.match(r"^\s*git add\s+(?!--)(.+)$", line)
        if not m:
            continue
        for raw in re.split(r"[;|]{1,2}", m.group(1)):
            for tok in raw.split():
                tok = re.sub(r"(\s*2>?/?dev/null.*|\s*>\s*/dev/null.*)$", "", tok).strip("'\"")
                if not tok or tok.startswith("-") or "$" in tok or "*" in tok:
                    continue
                toks.append(tok)
    return sorted(set(toks))


def c8_commit_hygiene(workflow_text, ignored_untracked):
    """C8: `git add` auf eine ignorierte, unversionierte Datei bricht den Lauf unter
    `set -e` hart ab – genau die Ursache von #205. Versionierte Dateien (Reports)
    dürfen das, sie sind .gitignore-technisch frei."""
    out = []
    for tok in add_tokens(workflow_text):
        if tok in ignored_untracked:
            out.append(("C8", f"`git add {tok}` – Datei ist .gitignore-ignoriert UND nicht "
                              "versioniert: der Add bricht den Lauf hart ab (vgl. #205). "
                              "Als CI-Artefakt sichern statt committen."))
    return out


SECRET_PATTERNS = [
    (r"\bpina_[A-Za-z0-9]{20,}", "Pinterest Access-Token im Klartext"),
    (r"\bpinr_[A-Za-z0-9]{20,}", "Pinterest Refresh-Token im Klartext"),
    (r"\bAIza[0-9A-Za-z_\-]{30,}", "Google/Gemini-API-Key im Klartext"),
    (r"\bgsk_[A-Za-z0-9]{20,}", "Groq-API-Key im Klartext"),
    (r"\bghp_[A-Za-z0-9]{30,}", "GitHub-PAT im Klartext"),
    (r"eyJ[A-Za-z0-9_\-]{20,}\.eyJ", "JWT (Mastodon/OAuth) im Klartext"),
]


def c10_token_broker(script_texts):
    """C10: EINE Token-Wahrheit für den ganzen Pinterest-Betrieb.

    Der teuerste Teil von #206 war nicht der abgelaufene Token, sondern dass
    sechs Skripte sechs verschiedene Reihenfolgen benutzten: Die Wache prüfte
    das Env-Secret, der Bot arbeitete mit dem Auto-Refresh-Speicher. Ein grüner
    Report konnte einen toten Kanal bedeuten – und ein roter einen gesunden.
    """
    out = []
    for name, text in sorted(script_texts.items()):
        if name in TOKEN_BROKER_EXEMPT:
            continue
        if "api.pinterest.com" not in text and "PINTEREST_ACCESS_TOKEN" not in text:
            continue
        uses_broker = TOKEN_BROKER in text
        # Direktzugriff auf das Env-Secret als TOKEN-QUELLE (nicht bloß erwähnt)
        direct = re.search(r"os\.environ(?:\.get\(\s*)?\[?[\"']PINTEREST_ACCESS_TOKEN", text)
        if not uses_broker and direct:
            out.append(("C10", f"scripts/{name}: holt den Pinterest-Token direkt aus dem "
                               "Env statt über `pinterest_token.get_token()` – damit prüft "
                               "die Wache einen anderen Token als der Bot benutzt (#206)."))
        if not uses_broker and "api.pinterest.com" in text and not direct:
            out.append(("C10", f"scripts/{name}: spricht mit der Pinterest-API, kennt aber "
                               "den Token-Broker `pinterest_token` nicht – Failover und "
                               "Auto-Erneuerung greifen dort nicht."))
    return out


def c11_token_lifecycle(workflow_texts, root=None):
    """C11: Der Zugang muss sich selbst erneuern – täglich, nachweisbar."""
    out = []
    path = next((p for p in workflow_texts if os.path.basename(p) == TOKEN_WORKFLOW), None)
    if not path:
        out.append(("C11", f"Kein Erneuerungslauf `.github/workflows/{TOKEN_WORKFLOW}` – "
                           "ein Pinterest-Token von Hand stirbt planmäßig nach 30 Tagen "
                           "(genau der Dauerbefund aus #206)."))
        return out
    text = workflow_texts[path]
    if "schedule:" not in text or "cron:" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: kein Zeitplan – eine Erneuerung, die nur "
                           "von Hand läuft, ist keine Erneuerung."))
    if "pinterest_token.py --refresh" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: erneuert den Zugang nicht über "
                           "`pinterest_token.py --refresh`."))
    if "data/pinterest_tokens.enc" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: sichert den rotierten Refresh-Token nicht "
                           "(`data/pinterest_tokens.enc`) – nach 60 Tagen ist der Kanal "
                           "trotz Automatik tot."))
    if "issue close" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: kein Selbstheilungs-Pfad – ein erledigter "
                           "Befund muss sein Issue selbst schließen."))
    if "--selftest" not in text:
        out.append(("C11", f"{TOKEN_WORKFLOW}: fasst Tokens ohne vorherigen Selbsttest an "
                           "(Sabotage-Schutz fehlt)."))
    return out


def c12_label_guarantee(workflow_texts):
    """C12: Ein Melder, der am Melden scheitert, ist schlimmer als kein Melder.

    `gh issue create --label X` schlägt mit HTTP 422 fehl, wenn X im Repository
    nicht existiert. Genau das hat den Pinterest-Watchdog am 07.09.2026 rot
    laufen lassen (#209) – und das Fehler-Alerting öffnete daraufhin ein Issue
    über das Issue, das nicht geschrieben werden konnte.
    """
    out = []
    for path, raw in sorted(workflow_texts.items()):
        rel = os.path.basename(path)
        # Kommentarzeilen raus: In den Kommentaren stehen Beispielbefehle (auch
        # dieser Regel), die sonst als echte Issue-Erzeugung gezählt würden.
        raw = "\n".join(l for l in raw.splitlines()
                         if not l.lstrip().startswith("#"))
        text = re.sub(r"\\\s*\n\s*", " ", raw)          # Zeilenfortsetzungen
        labels = set()
        for m in re.finditer(r"gh issue create[^\n]*", text):
            labels |= {l.strip("\"'`,;") for l in re.findall(r"--label\s+(\S+)", m.group(0))}
        for m in re.finditer(r"labels:\s*\[([^\]]*)\]", text):
            labels |= {l.strip().strip("\"'") for l in m.group(1).split(",") if l.strip()}
        for label in sorted(l for l in labels if l):
            # `--label "$GOV_LABEL"` und `--label governance` sollen beide
            # zum passenden `gh label create` finden – deshalb der nackte Kern.
            var = label.strip('${} "\'')
            pattern = r'gh label create\s+["\']?\$?\{?' + re.escape(var)
            created = (re.search(pattern, text)
                       or re.search(r"issues\.createLabel", text))
            if not created:
                out.append(("C12", f"{rel}: erzeugt Issues mit Label `{label}`, legt es aber "
                                   "nie an (`gh label create … --force`). Fehlt das Label im "
                                   "Repo, scheitert die Meldung mit HTTP 422 (#209)."))
    return out


def c13_proof_integrity(workflow_texts, auth_text=""):
    """C13: Ein Nachweis ohne Probe ist eine Behauptung (#219, 08.09.2026).

    Drei Workflows riefen `secrets_age_guard.py --verify-only PINTEREST_ACCESS_TOKEN`
    OHNE `--verify` auf – es lief nie eine Live-Probe, und das Lagebild stand
    monatelang auf `unverified`. Dazu: Nur die Token-Wache darf den Refresh-
    Token proaktiv rotieren (sonst Kollision), und die Autorisierungs-URL muss
    die echten v5-Scopes anfordern (`read_ads` gibt es nicht; ohne
    `user_accounts:read` antwortet die Broker-Probe /v5/user_account mit 403).
    """
    out = []
    for path, raw in sorted(workflow_texts.items()):
        rel = os.path.basename(path)
        text = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))
        text = re.sub(r"\\\s*\n\s*", " ", text)
        for m in re.finditer(r"secrets_age_guard\.py([^\n]*)--verify-only\s+PINTEREST_ACCESS_TOKEN", text):
            if not re.search(r"(^|\s)--verify(\s|$)", m.group(1) + " "):
                out.append(("C13", f"{rel}: prüft den Pinterest-Nachweis mit `--verify-only`, "
                                   "aber ohne `--verify` – es läuft keine Live-Probe, die Wache "
                                   "bleibt `unverified` (#219)."))
        if rel == TOKEN_WORKFLOW and "PINTEREST_TOKEN_WACHE" not in text:
            out.append(("C13", f"{rel}: setzt `PINTEREST_TOKEN_WACHE` nicht – der Broker rotiert "
                               "dann nie proaktiv, der Access-Token stirbt am 30. Tag."))
        if rel != TOKEN_WORKFLOW and re.search(r"PINTEREST_TOKEN_WACHE:\s*[\"']?(1|true|yes|ja)", text):
            out.append(("C13", f"{rel}: gibt sich als Token-Wache aus – zwei Rotierer entwerten "
                               "sich gegenseitig den Refresh-Token."))
    if auth_text:
        m = re.search(r"^DEFAULT_SCOPES\s*=\s*[\"']([^\"']+)[\"']", auth_text, re.M)
        scopes = set(m.group(1).replace(" ", ",").split(",")) if m else set()
        if not m:
            out.append(("C13", "scripts/pinterest_auth.py: keine `DEFAULT_SCOPES` – die "
                               "Autorisierungs-URL ist nicht prüfbar."))
        else:
            bad = [sc for sc in scopes if not re.fullmatch(r"[a-z_]+:(read|write)(_secret)?", sc)]
            if bad:
                out.append(("C13", "scripts/pinterest_auth.py: ungültige v5-Scopes "
                                   f"{sorted(bad)} – Pinterest bricht die Autorisierung ab."))
            for need in ("pins:write", "boards:read", "user_accounts:read"):
                if need not in scopes:
                    out.append(("C13", f"scripts/pinterest_auth.py: Scope `{need}` fehlt – "
                                       + ("die Broker-Probe /v5/user_account liefert 403."
                                          if need == "user_accounts:read"
                                          else "ohne ihn kann der Bot nicht pinnen.")))
    return out


def c9_secret_leak(texts):
    out = []
    for name, text in texts.items():
        for pattern, label in SECRET_PATTERNS:
            if re.search(pattern, text):
                out.append(("C9", f"{name}: {label} – Report/Ausgabe dichtet etwas nicht ab."))
    return out


# ------------------------------------------------------------------ Ausführung

def run_all(python_bin="python3", quick=False, root=BLOG_DIR):
    gov = _read(os.path.join(root, ".github", "workflows", "premium-governance.yml"))
    gate = _read(os.path.join(root, "scripts", "governance_gate.py"))
    secrets = _read(os.path.join(root, "scripts", "secrets_age_guard.py"))
    wflows = {}
    for path in sorted(glob.glob(os.path.join(root, ".github", "workflows", "*.yml"))):
        wflows[path] = _read(path)
    manifest = {}
    mpath = os.path.join(root, "data", "cwv_manifest.json")
    try:
        with open(mpath, encoding="utf-8") as f:
            manifest = json.load(f)
    except (OSError, json.JSONDecodeError):
        manifest = {}
    report_texts = {}
    for name in ("CWV-REPORT.md", "EDITORIAL-SCORECARD.md", "SECRETS-REPORT.md"):
        report_texts[name] = _read(os.path.join(root, name))
    # Welche der gestagten Pfade sind ignoriert UND unversioniert? (die Kombination
    # ist das Problem – Versioniertes darf git add trotz Ignore-Muster.)
    candidates = sorted({t for text in wflows.values() for t in add_tokens(text)})
    ignored = set()
    if candidates:
        try:
            r = subprocess.run(["git", "check-ignore", "--stdin"], cwd=root,
                               input="\n".join(candidates), capture_output=True,
                               text=True, timeout=60)
            ignored = {l.strip() for l in r.stdout.splitlines() if l.strip()}
            if ignored:
                t = subprocess.run(["git", "ls-files", "--", *sorted(ignored)], cwd=root,
                                   capture_output=True, text=True, timeout=60)
                tracked = {l.strip() for l in t.stdout.splitlines() if l.strip()}
                ignored -= tracked
        except (OSError, subprocess.TimeoutExpired):
            ignored = set()
    checks = []
    checks += c1_ordering(gov)
    checks += c2_build_not_swallowed(gov)
    checks += c3_measure_chain_complete(gov, gate)
    checks += c4_issue_policy(gov)
    checks += c5_record_provenance(wflows, secrets)
    checks += c6_selftests(python_bin=python_bin, quick=quick)
    checks += c7_data_consistency(report_texts, manifest)
    checks += c8_commit_hygiene(gov, ignored)
    leak_texts = dict(report_texts)
    for path in glob.glob(os.path.join(root, "data", "*.json")):
        if os.path.getsize(path) < 400_000:
            leak_texts[os.path.relpath(path, root)] = _read(path)
    checks += c9_secret_leak(leak_texts)
    script_texts = {}
    for path in sorted(glob.glob(os.path.join(root, "scripts", "*.py"))):
        script_texts[os.path.basename(path)] = _read(path)
    checks += c10_token_broker(script_texts)
    checks += c11_token_lifecycle(wflows, root=root)
    checks += c12_label_guarantee(wflows)
    checks += c13_proof_integrity(wflows, auth_text=script_texts.get("pinterest_auth.py", ""))
    return checks


RULE_TEXT = {
    "C1": "Die Sicht (Chefredakteur-Scorecard) läuft nach allen Messungen – sonst "
          "zeigt sie Werte des Vorlaufs als aktuellen Befund (#206).",
    "C2": "Der Hugo-Build darf keinen Fehler mit `|| true` verschlucken und meldet sein "
          "Ergebnis an das Gate – eine nicht ausgeführte Messung ist kein Grün.",
    "C3": "Jede Gate-Kennung wird aus einem Workflow befüllt – ein Schritt, den "
          "niemals jemand meldet, kann auch niemand reparieren.",
    "C4": "Issues entstehen aus der Gate-Entscheidung (`--decide`), Duplikate sind "
          "verboten (aktualisieren statt neu öffnen), und eine meldungsfreie Lage "
          "schließt das Issue.",
    "C5": "Secret-Nachweise tragen ihre Herkunft (`--proof-by`) und kommen aus dem "
          "Workflow, der das Secret benutzt; die Governance prüft live (`--verify`) "
          "statt sich selbst zu beglaubigen.",
    "C6": "Jede Wache hat einen `--selftest`, und alle bestehen – eine kaputte Wache "
          "liefert falsche Sicherheit.",
    "C7": "Manifest, Report und Scorecard zeigen dieselbe Ampel (oder die Scorecard "
          "kennzeichnet STALE/nicht gemessen ausdrücklich).",
    "C8": "`git add` im Workflow nennt nur versionierbare Pfade – ignorierte, "
          "unversionierte Dateien brechen den Lauf hart ab (#205).",
    "C9": "Reports und `data/*.json` enthalten kein Secret-Material (Pinterest/Groq/"
          "Gemini/GitHub/JWT-Muster).",
    "C10": "Alle Pinterest-Skripte holen ihren Token über den Broker "
           "`scripts/pinterest_token.py` – eine Reihenfolge, ein Failover, und die "
           "Wache prüft denselben Token, mit dem der Bot arbeitet (#206).",
    "C11": "Es gibt einen täglichen Erneuerungslauf (`pinterest-token.yml`), der den "
           "rotierten Refresh-Token sichert, sich selbst testet und sein Issue bei "
           "Heilung schließt – ein Handbetriebs-Secret stirbt sonst alle 30 Tage.",
    "C12": "Jeder Workflow, der Issues mit Label erzeugt, legt das Label vorher an – "
           "sonst scheitert die Meldung mit HTTP 422 und der Melder wird selbst zum "
           "Zwischenfall (#209).",
    "C13": "Ein Pinterest-Nachweis läuft immer mit Live-Probe (`--verify`), nur die "
           "Token-Wache rotiert den Refresh-Token proaktiv, und die Autorisierung "
           "fordert die echten v5-Scopes – sonst steht `unverified` im Cockpit, während "
           "niemand gemessen hat (#219).",
}

LABEL = {"C1": "Reihenfolge", "C2": "Bau-Grundlage", "C3": "Messkette",
         "C4": "Issue-Policy", "C5": "Nachweis-Provenienz", "C6": "Selbsttests",
         "C7": "Datenkonsistenz", "C8": "Commit-Hygiene", "C9": "Secret-Leak-Schutz",
         "C10": "Token-Broker", "C11": "Token-Lebenszyklus", "C12": "Label-Garantie",
         "C13": "Nachweis-Echtheit"}


def render_md(checks, ok_notes=()):
    lines = [
        "# 🔒 Governance-Vertrag (automatisch geprüft)",
        "",
        f"**Stand:** {datetime.date.today().isoformat()} · erzeugt von "
        "`scripts/governance_contract.py` · geprüft in `link-check.yml` (Qualitäts-Gate) "
        "und als Preflight in `premium-governance.yml`.",
        "",
        "Dieser Vertrag hält die Regeln fest, die den Dauer-Alarm aus "
        "Governance-Report #206 ermöglicht haben. Jede Verletzung ist ein Build-Fehler.",
        "",
        "## Regeln",
        "",
    ]
    # Natürliche Reihenfolge: C2 vor C10 (lexikografisch wäre C1, C10, C11, C2 …)
    for code, label in sorted(LABEL.items(), key=lambda kv: int(kv[0][1:])):
        lines.append(f"- **{code} {label}** – {RULE_TEXT.get(code, '')}")
    lines += ["", "## Befund", ""]
    if not checks:
        lines.append("🟢 Alle Verträge erfüllt.")
    else:
        lines += ["| Regel | Befund |", "|---|---|"]
        for code, msg in checks:
            lines.append(f"| {code} {LABEL.get(code, '')} | {msg} |")
    if ok_notes:
        lines += ["", "## Geprüfte Nachweise", ""]
        lines += [f"- {n}" for n in ok_notes]
    return "\n".join(lines) + "\n"


def _selftest():
    """Die Prüf-Regeln selbst mit Kunst-Workflows – sonst prüft man Ins Blaue."""
    failures = []
    good = """
      - name: Core-Web-Vitals-Wächter
        run: |
          hugo --minify > /tmp/build.log 2>&1
          python3 scripts/governance_gate.py --emit build --require-green
      - name: CWV
        run: python3 scripts/cwv_guard.py --public public/ --strict-build
      - name: emit
        run: python3 scripts/governance_gate.py --emit cwv --report CWV-REPORT.md
      - name: emit decay
        run: python3 scripts/governance_gate.py --emit decay --report DECAY-REPORT.md
      - name: emit secrets
        run: python3 scripts/secrets_age_guard.py --verify && python3 scripts/governance_gate.py --emit secrets
      - name: emit pinperf
        run: python3 scripts/governance_gate.py --emit pinperf --report PINTEREST-PERF-REPORT.md
      - name: emit clicks
        run: python3 scripts/governance_gate.py --emit clicks --report CLICK-REPORT.md
      - name: emit awin
        run: python3 scripts/governance_gate.py --emit awin --report AWIN-REPORT.md
      - name: Chefredakteur-Scorecard
        run: python3 scripts/editorial_scorecard.py
      - name: decide
        run: python3 scripts/governance_gate.py --decide
      - name: issue
        run: |
          gh issue list --state open --label governance
          gh issue create --label governance
      - name: close
        run: gh issue close 1
      - name: commit
        run: |
          git add data/governance_status.json
          git add CWV-REPORT.md
"""
    if c1_ordering(good):
        failures.append(f"guter Workflow wird von C1 verworfen: {c1_ordering(good)}")
    if c2_build_not_swallowed(good):
        failures.append(f"guter Workflow wird von C2 verworfen: {c2_build_not_swallowed(good)}")
    if c4_issue_policy(good):
        failures.append(f"guter Workflow wird von C4 verworfen: {c4_issue_policy(good)}")
    if c8_commit_hygiene(good, {"ops-report.json"}):
        failures.append("guter Workflow wird von C8 verworfen")
    # --- C1: #206-Fall (Scorecard zuerst) muss gefunden werden
    bad_order = """
      - name: Chefredakteur-Scorecard
        run: python3 scripts/editorial_scorecard.py
      - name: emit cwv
        run: python3 scripts/governance_gate.py --emit cwv
"""
    if not c1_ordering(bad_order):
        failures.append("C1: Scorecard vor den Messungen wird nicht erkannt (#206-Fall)")
    # --- C2: `|| true` muss gefunden werden
    bad_build = '- name: Hugo-Build\n        run: hugo --minify > /dev/null 2>&1 || true\n'
    if not c2_build_not_swallowed(bad_build):
        failures.append("C2: verschluckter Build-Fehler bleibt unentdeckt")
    # --- C4: Issue ohne decide/close
    bad_issue = "- name: issue\n        run: github.rest.issues.create({ title: 'x' })\n"
    if len(c4_issue_policy(bad_issue)) < 2:
        failures.append("C4: Issue-Erzeugung ohne Gate/Dedupe/Close bleibt unentdeckt")
    # --- C5: Selbst-Waschen + fehlende Provenienz
    bad_rec = {"premium-governance.yml":
               "python3 scripts/secrets_age_guard.py --record-success GROQ_API_KEY || true\n"}
    res = c5_record_provenance(bad_rec, 'SECRETS = {\n    "GROQ_API_KEY": {"days": 60},\n}')
    if not any("Selbst-Waschen" in m for _, m in res):
        failures.append("C5: Selbst-Waschen im Governance-Lauf wird nicht gemeldet")
    if not any("--proof-by" in m for _, m in res):
        failures.append("C5: Nachweis ohne --proof-by wird nicht gemeldet")
    res_unknown = c5_record_provenance({"social-ai.yml":
                                        "--record-success NOPE_TOKEN --proof-by social-ai\n"},
                                        'SECRETS = {\n    "GROQ_API_KEY": {"days": 60},\n}')
    if not any("nicht in" in m for _, m in res_unknown):
        failures.append("C5: unregistriertes Secret wird nicht gemeldet")
    # --- C7: zwei Wahrheiten
    man = {"verdict": "GREEN", "generated": "2026-09-07", "build_measured": True}
    if c7_data_consistency({"CWV-REPORT.md": "## 🤖 Gesamt-Ampel: **GREEN**\n**Stand:** 2026-09-07"},
                           man):
        failures.append("C7: konsistenter Stand wird beanstandet")
    res = c7_data_consistency({"CWV-REPORT.md": "## 🤖 Gesamt-Ampel: **AMBER**\n**Stand:** 2026-09-07"},
                             man)
    if not res:
        failures.append("C7: Report ≠ Manifest bleibt unentdeckt")
    res = c7_data_consistency({"CWV-REPORT.md": "## 🤖 Gesamt-Ampel: **GREEN**\n**Stand:** 2026-09-07",
                               "EDITORIAL-SCORECARD.md": "| Core-Web-Vitals | AMBER | 🟡 |"}, man)
    if not res:
        failures.append("C7: Scorecard mit erfundener CWV-Ampel (#206) bleibt unentdeckt")
    res = c7_data_consistency({"CWV-REPORT.md": "## 🤖 Gesamt-Ampel: **GREEN**\n**Stand:** 2026-09-07",
                               "EDITORIAL-SCORECARD.md": "| Core-Web-Vitals | STALE (12d) | ⚪ |"},
                              {"verdict": "GREEN", "generated": "2026-09-07",
                               "build_measured": False})
    if res:
        failures.append(f"C7: ehrliche STALE-Kennzeichnung wird bestraft: {res}")
    # --- C8: git add auf ignorierte Datei
    res = c8_commit_hygiene("          git add ops-report.json\n", {"ops-report.json"})
    if not res:
        failures.append("C8: git add auf ignorierte Datei (#205) bleibt unentdeckt")
    if c8_commit_hygiene("          git add CWV-REPORT.md\n", set()):
        failures.append("C8: versionierter Report wird beanstandet (Ignore gilt für "
                        "getrackte Dateien nicht)")
    if c8_commit_hygiene("          git add data/x.json 2>/dev/null || true\n", set()):
        failures.append("C8: Shell-Reste werden als Pfad fehlinterpretiert")
    # --- C9: Leak-Erkennung
    res = c9_secret_leak({"X.md": "token: gsk_" + "A" * 32})
    if not res:
        failures.append("C9: Klartext-Secret im Report wird nicht erkannt")
    if c9_secret_leak({"X.md": "Pinterest-Status: ok, keine Daten"}):
        failures.append("C9: Fehlalarm bei normalem Text")
    # --- C3: fehlender Emit-Zweig
    res = c3_measure_chain_complete("- name: x\n        run: echo",
                                   'STEPS = {\n    "decay":   {"report": "x"},\n    "cwv":     {"report": "y"},\n}')
    if len(res) != 2:
        failures.append(f"C3: fehlende Emit-Zweige nur {len(res)}x gemeldet (erwartet 2)")
    # --- C10: eigene Token-Reihenfolge im Skript (der #206-Kern)
    bad_scripts = {"pinterest_dings.py":
                   'tok = os.environ.get("PINTEREST_ACCESS_TOKEN", "")\n'
                   'urllib.request.urlopen("https://api.pinterest.com/v5/boards")\n'}
    if not any(code == "C10" for code, _ in c10_token_broker(bad_scripts)):
        failures.append("C10: eigenmächtige Token-Quelle im Skript bleibt unentdeckt")
    good_scripts = {"pinterest_dings.py":
                    "import pinterest_token\n"
                    "tok = pinterest_token.get_token()\n"
                    'urllib.request.urlopen("https://api.pinterest.com/v5/boards")\n'}
    if c10_token_broker(good_scripts):
        failures.append("C10: sauberes Skript über den Broker wird beanstandet")
    if c10_token_broker({"pinterest_token.py": 'os.environ["PINTEREST_ACCESS_TOKEN"]'}):
        failures.append("C10: der Broker selbst darf nicht gegen seine eigene Regel laufen")
    # --- C11: fehlender/halber Erneuerungslauf
    if not c11_token_lifecycle({}):
        failures.append("C11: fehlender Token-Erneuerungslauf bleibt unentdeckt")
    halb = {".github/workflows/pinterest-token.yml":
            "on:\n  workflow_dispatch: {}\nsteps:\n  - run: python3 scripts/pinterest_token.py --status\n"}
    res = c11_token_lifecycle(halb)
    if len(res) < 4:
        failures.append(f"C11: unvollständiger Erneuerungslauf nur {len(res)}x gemeldet")
    voll = {".github/workflows/pinterest-token.yml":
            "on:\n  schedule:\n    - cron: \"40 2 * * *\"\n"
            "steps:\n  - run: python3 scripts/pinterest_token.py --selftest\n"
            "  - run: python3 scripts/pinterest_token.py --refresh\n"
            "  - run: git add data/pinterest_tokens.enc\n"
            "  - run: gh issue close 1\n"}
    if c11_token_lifecycle(voll):
        failures.append(f"C11: vollständiger Erneuerungslauf wird beanstandet: {c11_token_lifecycle(voll)}")
    # --- C12: Issue-Label ohne Anlegen (Ursache #209)
    bad_label = {"x.yml": 'run: gh issue create --title "T" --label pinterest --body "b"\n'}
    if not any(code == "C12" for code, _ in c12_label_guarantee(bad_label)):
        failures.append("C12: Issue-Label ohne `gh label create` bleibt unentdeckt (#209)")
    good_label = {"x.yml": 'run: |\n  gh label create pinterest --force\n'
                           '  gh issue create --title "T" --label pinterest --body "b"\n'}
    if c12_label_guarantee(good_label):
        failures.append("C12: abgesicherter Melder wird beanstandet")
    var_label = {"x.yml": 'env:\n  L: gov\nrun: |\n  gh label create "$L" --force\n'
                          '  gh issue create --label "$L" --body b\n'}
    if c12_label_guarantee(var_label):
        failures.append("C12: Label über Variable wird fälschlich beanstandet")
    js_label = {"x.yml": "issues.createLabel({name:'auto-report'})\n"
                         "issues.create({labels: ['auto-report']})\n"}
    if c12_label_guarantee(js_label):
        failures.append("C12: github-script mit createLabel wird beanstandet")
    kommentar = {"x.yml": "# Beispiel: gh issue create --label demo\njobs: {}\n"}
    if c12_label_guarantee(kommentar):
        failures.append("C12: Beispiel im Kommentar wird als echter Melder gezählt")
    # --- C13: Nachweis ohne Live-Probe (Ursache #219)
    no_probe = {".github/workflows/x.yml":
                "run: |\n  python3 scripts/secrets_age_guard.py --verify-only PINTEREST_ACCESS_TOKEN --quiet\n"}
    if not any(code == "C13" for code, _ in c13_proof_integrity(no_probe)):
        failures.append("C13: `--verify-only` ohne `--verify` bleibt unentdeckt (#219)")
    with_probe = {".github/workflows/x.yml":
                  "run: |\n  python3 scripts/secrets_age_guard.py --verify --verify-only PINTEREST_ACCESS_TOKEN \\\n    --quiet\n"}
    if c13_proof_integrity(with_probe):
        failures.append(f"C13: echter Nachweis wird beanstandet: {c13_proof_integrity(with_probe)}")
    fake_wache = {".github/workflows/pinterest-ai.yml": "env:\n  PINTEREST_TOKEN_WACHE: \"1\"\n"}
    if not c13_proof_integrity(fake_wache):
        failures.append("C13: zweiter Rotierer bleibt unentdeckt")
    no_flag = {f".github/workflows/{TOKEN_WORKFLOW}": "env:\n  X: y\n"}
    if not c13_proof_integrity(no_flag):
        failures.append("C13: Token-Wache ohne Wache-Flag bleibt unentdeckt")
    good_flag = {f".github/workflows/{TOKEN_WORKFLOW}": "env:\n  PINTEREST_TOKEN_WACHE: \"1\"\n"}
    if c13_proof_integrity(good_flag):
        failures.append("C13: korrekt markierte Token-Wache wird beanstandet")
    bad_scope = 'DEFAULT_SCOPES = "boards:read,pins:write,read_ads"\n'
    if not any("read_ads" in msg or "user_accounts" in msg
               for _, msg in c13_proof_integrity({}, auth_text=bad_scope)):
        failures.append("C13: ungültiger Scope `read_ads` / fehlender Profil-Scope bleibt unentdeckt")
    good_scope = 'DEFAULT_SCOPES = "boards:read,boards:write,pins:read,pins:write,user_accounts:read"\n'
    if c13_proof_integrity({}, auth_text=good_scope):
        failures.append("C13: korrekte v5-Scopes werden beanstandet")
    # --- LABEL/Regeltext-Deckung: jede Regel ist erklärt (Doku gehört zum Vertrag)
    for code in LABEL:
        if code not in RULE_TEXT or len(RULE_TEXT[code]) < 40:
            failures.append(f"{code} ohne richtigen Regeltext")
    if "C1" not in LABEL or "C13" not in LABEL:
        failures.append("Regel-Codes nicht vollständig gelabelt")
    if failures:
        print("❌ KONTRAKT-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ KONTRAKT-SELFTEST bestanden (C1–C13 mit Kunstbefunden: Fehler erkannt, "
          "gutes Setup bleibt still).")
    return 0


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return _selftest()
    quick = "--quick" in argv
    pybin = argv[argv.index("--python") + 1] if "--python" in argv else sys.executable or "python3"
    checks = run_all(python_bin=pybin, quick=quick)
    if checks:
        print("🔒 GOVERNANCE-VERTRAG: verletzt\n")
        annotate = bool(os.environ.get("GITHUB_ACTIONS"))
        for code, msg in checks:
            line = f"{code} {LABEL.get(code, '')}: {msg}"
            print(f"  ❌ {line}")
            if annotate:
                print(f"::error::{line}")
    else:
        print("🔒 GOVERNANCE-VERTRAG erfüllt – alle dreizehn Regeln prüfen in beide "
              "Richtungen (Fehler UND Schein-Sicherheit).")
    if "--md" in argv:
        target = argv[argv.index("--md") + 1]
        try:
            os.makedirs(os.path.dirname(os.path.join(BLOG_DIR, target)) or BLOG_DIR, exist_ok=True)
            with open(os.path.join(BLOG_DIR, target), "w", encoding="utf-8") as f:
                f.write(render_md(checks))
            print(f"→ geschrieben: {target}")
        except OSError as exc:
            print(f"⚠️  Markdown konnte nicht geschrieben werden: {exc}")
    return 1 if checks else 0


if __name__ == "__main__":
    sys.exit(main())
