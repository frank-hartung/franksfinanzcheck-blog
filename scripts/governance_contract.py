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
GUARDS = ["editorial_scorecard.py", "cwv_guard.py", "secrets_age_guard.py",
          "decay_radar.py", "governance_gate.py", "umami_clicks.py",
          "click_attribution.py", "awin_provisions.py", "pinterest_perf_feedback.py"]

# Reihenfolge-Vertrag: diese Schritte sind Messungen, die vor der Sicht liegen müssen
MEASURE_STEPS = ("decay", "cwv", "secrets", "pinperf", "clicks", "awin")
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
    "cwv":       (r"--emit\s+cwv\b", r"cwv_guard\.py"),
    "secrets":   (r"--emit\s+secrets\b", r"secrets_age_guard\.py"),
    "pinperf":   (r"--emit\s+pinperf\b", r"pinterest_perf_feedback\.py"),
    "clicks":    (r"--emit\s+clicks\b", r"click_attribution\.py"),
    "awin":      (r"--emit\s+awin\b", r"awin_provisions\.py"),
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
}

LABEL = {"C1": "Reihenfolge", "C2": "Bau-Grundlage", "C3": "Messkette",
         "C4": "Issue-Policy", "C5": "Nachweis-Provenienz", "C6": "Selbsttests",
         "C7": "Datenkonsistenz", "C8": "Commit-Hygiene", "C9": "Secret-Leak-Schutz"}


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
    for code, label in sorted(LABEL.items()):
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
    # --- LABEL/Regeltext-Deckung: jede Regel ist erklärt (Doku gehört zum Vertrag)
    for code in LABEL:
        if code not in RULE_TEXT or len(RULE_TEXT[code]) < 40:
            failures.append(f"{code} ohne richtigen Regeltext")
    if "C1" not in LABEL or "C9" not in LABEL:
        failures.append("Regel-Codes nicht vollständig gelabelt")
    if failures:
        print("❌ KONTRAKT-SELFTEST FEHLGESCHLAGEN:")
        for f in failures:
            print("   -", f)
        return 2
    print("✅ KONTRAKT-SELFTEST bestanden (C1–C9 mit Kunstbefunden: Fehler erkannt, "
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
        print("🔒 GOVERNANCE-VERTRAG erfüllt – alle neun Regeln prüfen in beide Richtungen "
              "(Fehler UND Schein-Sicherheit).")
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
