#!/usr/bin/env python3
# ============================================================
#  BESTAND-GATE – wendet die AKTUELLE Publish-Gate-Prüfung auch auf
#  BESTANDSDATEN (bereits veröffentlichte, ältere Artikel) an.
#
#  Auftrag (13.08.2026, Frank): "Sorge dafür, dass die jetzige Artikel-
#  Veröffentlichungsroutine auch für die bestehenden Artikel gilt, und
#  dass jede Änderung am Blog auch für die Bestandsdaten gilt."
#
#  HINTERGRUND: scripts/publish_gate.py prüft die 4 harten Kriterien
#  (check_length.py, seo_audit.py, affiliate_profi_check.py,
#  affiliate_integrity_gate.py) NUR für Artikel, die HEUTE neu erzeugt
#  wurden (todays_live_candidates()) –
#  by design, weil es bei Nicht-Bestehen den Artikel komplett VERWIRFT
#  (discard_article() löscht Content + Cover). Das ist für druckfrische,
#  noch nirgends verlinkte/indexierte Kandidaten die richtige, radikale
#  Lösung. Für bereits veröffentlichte, potenziell längst von Google
#  indexierte und extern verlinkte Bestandsartikel wäre automatisches
#  Löschen dagegen ein Betriebsunfall (verlorene Rankings/Backlinks).
#  Deshalb wurden Bestandsartikel bisher NIE gegen das aktuelle Gate
#  geprüft, obwohl das Gate selbst (und alle anderen Qualitäts-Regeln)
#  sich laufend weiterentwickeln.
#
#  DIESES SKRIPT SCHLIESST DIE LÜCKE, aber NICHT-DESTRUKTIV:
#    1. Prüft ALLE aktuell live geschalteten Artikel (nicht nur die
#       heutigen) mit denselben vier Funktionen aus publish_gate.py –
#       echte Wiederverwendung, kein Parallel-Code. Jede künftige
#       Verschärfung/Änderung der Gate-Logik gilt dadurch automatisch
#       auch hier, ohne dass dieses Skript angefasst werden muss.
#    2. Für jeden Fund wird die passende bestehende Selbstheilung
#       versucht (meta_optimizer.py --fix für SEO-Mängel,
#       affiliate_profi_check.py --fix für A1-A8,
#       affiliate_integrity_gate.py [ohne --dry-run, heilt also
#       tatsächlich] für defekte/nicht gerenderte CTA-Boxen – 14.08.2026,
#       Frank: "sofortige Reparatur" für Bestandsschäden), danach erneut
#       geprüft.
#    3. Was danach IMMER NOCH nicht besteht, wird NIEMALS gelöscht,
#       sondern klar für redaktionelle Prüfung gemeldet
#       (BESTAND-REPORT.md, Exit 1 -> löst das bestehende
#       Fehler-Alerting aus). Längen-Probleme sind grundsätzlich nicht
#       automatisch heilbar (brauchen echte Textarbeit).
#
#  SEBSTSTÄNDIGE PREMIUM-VERSION (02.09.2026, Issue #149):
#    Alles passiert HIER – kein Workflow-Patch, kein manueller Schritt,
#    kein zusätzlicher Token nötig. .github/workflows/seo-weekly.yml
#    ruft das Skript wie bisher auf (hugo --minify + bestand_gate.py).
#
#    - Detektor-Selbsttest VOR der Bewertung: scripts/affiliate_integrity_gate.py
#      --selftest. Bei Detektor-Drift fail-closed (Exit 2, nichts geheilt).
#    - Eindeutige Exit-Codes:
#        0  grün – alle Bestandsartikel konform
#        1  Inhaltsschaden – nach Heilungsversuch bleibt etwas offen
#        2  Auswertungsfehler / Detektor-Drift – fail-closed, nichts geheilt
#    - Idempotente Issue-Pflege direkt über die GitHub-API (GITHUB_TOKEN,
#      reicht `issues: write`, das seo-weekly.yml bereits hat):
#        * EIN offenes Issue pro Schadenslage (Marker <!-- bestand-gate -->)
#        * Rot  -> vorhandenes Issue wird AKTUALISIERT, nie dupliziert
#        * Grün -> offene Bestand-Gate-Issues werden automatisch geschlossen
#          (auch Alt-Issues ohne Marker wie #149)
#        * Werkzeug- vs. Inhaltsschaden wird im Titel/Body getrennt gemeldet
#
#  Aufruf:
#    python3 scripts/bestand_gate.py             # prüfen + heilen + Issue-Pflege
#    python3 scripts/bestand_gate.py --dry-run   # nur prüfen (kein Heilen,
#                                                # keine API-Schreibzugriffe)
#    python3 scripts/bestand_gate.py --selftest  # nur Detektor-Selbsttest
#    python3 scripts/bestand_gate.py --json
# ============================================================

import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "content" / "posts"
REPORT = ROOT / "BESTAND-REPORT.md"
STATE = ROOT / ".bestand_gate_state.json"

DRY_RUN = "--dry-run" in sys.argv
AS_JSON = "--json" in sys.argv
SELFTEST_ONLY = "--selftest" in sys.argv

sys.path.insert(0, str(SCRIPTS))


def live_slugs() -> list[str]:
    """Alle aktuell live geschalteten (draft:false) Artikel-Slugs –
    unabhängig ermittelt, nicht über eine der geprüften Lade-Funktionen."""
    slugs = []
    if not POSTS_DIR.is_dir():
        return slugs
    for slug in sorted(os.listdir(POSTS_DIR)):
        index_path = POSTS_DIR / slug / "index.md"
        if not index_path.is_file():
            continue
        text = index_path.read_text(encoding="utf-8", errors="ignore")
        if not text.startswith("---") or text.count("---") < 2:
            continue
        fm = text.split("---", 2)[1]
        if re.search(r"^draft:\s*true\s*$", fm, re.MULTILINE):
            continue
        slugs.append(slug)
    return slugs


def detector_selftest() -> tuple[bool, str]:
    """Vorbeweis (Premium 02.09.2026, Issue #149): Die Wache muss erst SEHEN
    können, bevor sie urteilt. Läuft der Detektor-Selbsttest
    (affiliate_integrity_gate.py --selftest) nicht grün, gilt das als
    Detektor-Drift: fail-closed, nichts wird geheilt oder verworfen."""
    try:
        r = subprocess.run(
            [sys.executable, str(SCRIPTS / "affiliate_integrity_gate.py"), "--selftest"],
            cwd=ROOT, capture_output=True, text=True, timeout=180,
        )
    except Exception as exc:  # noqa: BLE001
        return False, f"Detektor-Selbsttest konnte nicht gestartet werden: {exc}"
    if r.returncode != 0:
        tail = ((r.stdout or "") + "\n" + (r.stderr or "")).strip()[-1200:]
        return False, (
            "Detektor-Drift: `scripts/affiliate_integrity_gate.py --selftest` "
            f"fehlgeschlagen (Exit {r.returncode}). NICHTS wurde geheilt oder "
            "verworfen. Anpassung des Detektors an den Render-Hook nötig "
            "(Drift-Wächter, siehe AFFILIATE-INTEGRITY-GATE-REPORT.md).\n"
            f"```\n{tail}\n```"
        )
    return True, "✅ Detektor-Selbsttest (affiliate_integrity_gate.py --selftest) grün."


def run_gate():
    """Importiert publish_gate.py und ruft dieselben vier Prüf-Funktionen
    auf, die auch für druckfrische Artikel gelten – echte Wiederverwendung,
    kein Parallel-Code. Setzt daher voraus, dass vorher `hugo --minify`
    gelaufen ist (wie publish_gate.py selbst dokumentiert)."""
    if "publish_gate" in sys.modules:
        del sys.modules["publish_gate"]
    pg = __import__("publish_gate")

    length_failed, length_err = pg.check_length_failures()
    seo_failed, seo_err = pg.seo_audit_failures()
    affiliate_failed, affiliate_err = pg.affiliate_profi_failures()
    # Bestand: bewusst OHNE Kandidaten-Filter (alles prüfen) – bestand_gate
    # ist die nicht-destruktive Bestands-Wache, die jeden Fund meldet
    #    und zu heilen versucht. Werkzeugfehler (exit_code 2) kommen als
    #    errors-Liste zurück und landen im Report + Exit 2 (fail-closed).
    integrity_failed, integrity_err, integrity_tool_error = \
        pg.affiliate_integrity_failures()

    errors = [e for e in (length_err, seo_err, affiliate_err, integrity_err) if e]
    if integrity_tool_error:
        # fail-closed sichtbar machen: kein Bestand darf als "sauber" gelten,
        # solange der Render-Beweis nicht geführt werden konnte.
        errors.append("Affiliate-Render-Beweis nicht möglich (Werkzeugfehler) – "
                      "Bestand gilt als NICHT geprüft")
    return {
        "length": length_failed,
        "seo": seo_failed,
        "affiliate": affiliate_failed,
        "integrity": integrity_failed,
    }, errors


def rebuild_hugo() -> bool:
    hugo_bin = shutil.which("hugo")
    if not hugo_bin and Path("/tmp/hugo").is_file():
        hugo_bin = "/tmp/hugo"  # Sandbox-Fallback; CI hat 'hugo' regulär im PATH
    if not hugo_bin:
        print("⚠️ Kein Hugo-Binary gefunden – Re-Check nach Heilung übersprungen.")
        return False
    try:
        r = subprocess.run([hugo_bin, "--minify"], cwd=ROOT, capture_output=True, text=True, timeout=180)
        return r.returncode == 0
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ Hugo-Rebuild fehlgeschlagen ({exc}) – Re-Check nutzt evtl. veraltetes public/.")
        return False


def heal(dimension: str) -> None:
    if dimension == "seo":
        subprocess.run([sys.executable, str(SCRIPTS / "meta_optimizer.py"), "--fix"],
                        cwd=ROOT, capture_output=True, text=True, timeout=180)
    elif dimension == "affiliate":
        subprocess.run([sys.executable, str(SCRIPTS / "affiliate_profi_check.py"), "--fix"],
                        cwd=ROOT, capture_output=True, text=True, timeout=180)
    elif dimension == "integrity":
        # OHNE --dry-run: heilt tatsächlich (regeneriert defekte CTA-Boxen
        # komplett neu über affiliate_marketer.py-Vorlagen) statt nur zu
        # melden – das ist die vom Nutzer geforderte "sofortige Reparatur"
        # für bereits veröffentlichte Bestandsartikel.
        subprocess.run([sys.executable, str(SCRIPTS / "affiliate_integrity_gate.py")],
                        cwd=ROOT, capture_output=True, text=True, timeout=180)
    # "length" (zu kurz/zu lang) ist nicht automatisch heilbar – braucht
    # echte Textarbeit, wird nur gemeldet.


# ------------------------------------------------------------------ #
#  Maschinenlesbarer Zustand (Premium 02.09.2026, Issue #149)
# ------------------------------------------------------------------ #
VOLATILE_STATE_KEYS = ("generated_at",)


def _state_fingerprint(payload: dict) -> str:
    """Fingerprint ohne fluechtige Felder – verhindert Commit-/Deploy-Churn
    an ruhigen Tagen (gleiches Prinzip wie affiliate_integrity_gate.py)."""
    return json.dumps({k: v for k, v in payload.items()
                       if k not in VOLATILE_STATE_KEYS},
                      ensure_ascii=False, sort_keys=True, default=list)


def write_state(payload: dict) -> None:
    """Schreibt .bestand_gate_state.json nur bei inhaltlicher Aenderung.

    Die Datei macht die Schadenslage eindeutig maschinenlesbar:
      * 0  = gruen (Bestand konform / erfolgreich geheilt)
      * 1  = Inhaltsschaden offen
      * 2  = Auswertungsfehler / Detektor-Drift (fail-closed)
    """
    try:
        previous = json.loads(STATE.read_text(encoding="utf-8")) if STATE.is_file() else {}
        if _state_fingerprint(previous) == _state_fingerprint(payload):
            return  # konvergent: kein Diff, kein Commit, kein Deploy-Trigger
        STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                         encoding="utf-8")
    except (OSError, json.JSONDecodeError) as exc:
        try:
            STATE.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n",
                             encoding="utf-8")
        except OSError as exc2:
            print(f"⚠️ Zustand konnte nicht geschrieben werden: {exc2} ({exc})")


# ------------------------------------------------------------------ #
#  Idempotente Issue-Pflege (Premium 02.09.2026, Issue #149) – DIREKT
#  im Skript, über die GitHub-API. Kein Workflow-Patch mehr nötig:
#  .github/workflows/seo-weekly.yml hat bereits `issues: write`.
# ------------------------------------------------------------------ #
ISSUE_MARKER = "<!-- bestand-gate -->"
LEGACY_TITLES = {"📋 Bestand-Gate: bestehende Artikel brauchen Aufmerksamkeit"}
DEFAULT_LEGACY_ISSUES = "149"


def _gh_token() -> str | None:
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or None


def _gh_repo() -> tuple[str, str] | None:
    repo = os.environ.get("GITHUB_REPOSITORY") or ""
    if "/" not in repo:
        return None
    owner, name = repo.split("/", 1)
    return owner, name


def _legacy_numbers() -> set[int]:
    """Alt-Issues ohne Marker (Standard: #149), die bei Grün mitgeschlossen
    werden – per Env BESTAND_GATE_LEGACY_ISSUES (Komma-Liste) anpassbar."""
    raw = os.environ.get("BESTAND_GATE_LEGACY_ISSUES", DEFAULT_LEGACY_ISSUES)
    return {int(p) for p in raw.split(",") if p.strip().isdigit()}


def gh_api(method: str, path: str, token: str, payload: dict | None = None):
    """Kleiner GitHub-REST-Client (stdlib, keine Extra-Dependency)."""
    url = "https://api.github.com" + path
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "bestand-gate")
    with urllib.request.urlopen(req, timeout=30) as resp:
        if resp.status == 204:
            return {}
        return json.loads(resp.read().decode("utf-8"))


def list_open_issues(token: str, owner: str, repo: str) -> list[dict]:
    """Alle offenen Issues (paginiert, ohne Pull Requests zu prüfen)."""
    issues: list[dict] = []
    for page in range(1, 11):
        batch = gh_api("GET", f"/repos/{owner}/{repo}/issues?state=open&per_page=100&page={page}",
                       token=token)
        if not isinstance(batch, list) or not batch:
            break
        issues.extend(batch)
        if len(batch) < 100:
            break
    return issues


def is_bestand_issue(issue: dict) -> bool:
    """Erkennt Bestand-Gate-Issues: neuer Marker im Body ODER exakter
    Legacy-Titel (Issues des alten Workflow-Schritts) ODER feste
    Legacy-Nummer (z. B. #149)."""
    if issue.get("pull_request"):
        return False
    body = issue.get("body") or ""
    if ISSUE_MARKER in body:
        return True
    if issue.get("title") in LEGACY_TITLES:
        return True
    if issue.get("number") in _legacy_numbers():
        return True
    return False


def manage_issues(exit_code: int, report_text: str, dry_run: bool = False) -> None:
    """Idempotente Issue-Pflege: EIN Issue pro Schadenslage.

    * exit_code 0 (grün)  -> alle offenen Bestand-Gate-Issues schließen
      (mit Erklärung, auch Alt-Issue #149).
    * exit_code 1 (Inhalt)-> vorhandenes Issue aktualisieren, Duplikate
      schließen, sonst EIN neues Issue anlegen.
    * exit_code 2 (Werkzeug/Drift) -> wie 1, aber mit Werkzeugfehler-Titel
      und Handlungsanleitung (fail-closed).

    Ohne GITHUB_TOKEN/GITHUB_REPOSITORY (z. B. lokaler Lauf) wird sauber
    übersprungen – der Gate-Exit-Code und der Report bleiben unverändert.
    """
    token = _gh_token()
    repo = _gh_repo()
    if not token or not repo:
        print("ℹ️ Issue-Pflege übersprungen – kein GITHUB_TOKEN/GITHUB_REPOSITORY in der Umgebung.")
        return
    owner, name = repo

    green = exit_code == 0
    tool_error = exit_code == 2
    title = ("📋 Bestand-Gate: Auswertung nicht möglich (Werkzeugfehler, fail-closed)"
             if tool_error
             else "📋 Bestand-Gate: bestehende Artikel brauchen Aufmerksamkeit")
    now = datetime.now(timezone.utc).isoformat()
    checked = re.search(r"Geprüfte Live-Artikel:\s*(\d+)", report_text)
    affected = re.search(r"Weiterhin auffällig:\s*(\d+)", report_text)
    body = "\n".join([
        ISSUE_MARKER,
        ("> 🟠 **Werkzeugfehler (fail-closed):** Der Detektor-Selbsttest bzw. der "
         "Render-Beweis konnte nicht geführt werden. Es wurde **nichts geheilt und "
         "nichts verworfen** – Bestand gilt als NICHT geprüft. Bitte den Drift-Wächter "
         "prüfen (`python3 scripts/affiliate_integrity_gate.py --selftest`); schlägt er "
         "weiter fehl, muss der Detektor an `layouts/_default/_markup/render-link.html` "
         "angepasst werden."
         if tool_error else
         "> 🔴 **Bestand auffällig:** Nach der automatischen Selbstheilung bleiben "
         "Bestandsartikel auffällig. Betroffene Artikel wurden NICHT gelöscht – es braucht "
         "echte Text-/Content-Arbeit."),
        "",
        f"**Lauf:** {now} · **Exit-Code:** {exit_code} · "
        f"**Geprüfte Artikel:** {checked.group(1) if checked else '?'} · "
        f"**Weiterhin auffällig:** {affected.group(1) if affected else '?'}",
        "",
        "---",
        "",
        report_text,
        "",
        "---",
        "_Automatisch gepflegt von `scripts/bestand_gate.py` (Wochenlauf). "
        "Pro Schadenslage gibt es genau EIN Issue; es wird bei Rot aktualisiert "
        "und bei Grün automatisch geschlossen._",
    ])

    try:
        existing = [i for i in list_open_issues(token, owner, name) if is_bestand_issue(i)]
    except Exception as exc:  # noqa: BLE001
        print(f"⚠️ Issue-Pflege: offene Issues nicht lesbar – {exc}")
        return

    if green:
        if not existing:
            print("✅ Bestand-Gate grün, kein offenes Bestand-Gate-Issue vorhanden.")
            return
        for issue in existing:
            num = issue.get("number")
            print(f"{'🕵 DRY-RUN:' if dry_run else '✅'} Issue #{num} → "
                  f"{'würde geschlossen' if dry_run else 'schließen'} "
                  f"(Bestand-Gate grün)")
            if dry_run:
                continue
            try:
                gh_api("POST", f"/repos/{owner}/{name}/issues/{num}/comments", token,
                       {"body": f"{ISSUE_MARKER}\n✅ **Bestand-Gate grün** ({now}): alle "
                                "bestehenden Artikel erfüllen die aktuelle Publish-Gate-Prüfung "
                                "(Länge, SEO, Affiliate-Profi, Affiliate-Integrität).\n\n"
                                "Issue wird automatisch geschlossen."})
                gh_api("PATCH", f"/repos/{owner}/{name}/issues/{num}", token,
                       {"state": "closed", "state_reason": "completed"})
                print(f"✅ Issue #{num} automatisch geschlossen (Bestand-Gate grün).")
            except Exception as exc:  # noqa: BLE001
                print(f"⚠️ Issue #{num} konnte nicht geschlossen werden – {exc}")
        return

    # Rot (1 = Inhalt, 2 = Werkzeug): EIN Issue, aktualisieren statt duplizieren.
    if not existing:
        print(f"{'🕵 DRY-RUN:' if dry_run else '✅'} Neues Issue "
              f"{'würde angelegt' if dry_run else 'angelegt'}: {title}")
        if dry_run:
            return
        try:
            created = gh_api("POST", f"/repos/{owner}/{name}/issues", token,
                             {"title": title, "body": body})
            print(f"✅ Issue #{created.get('number')} erstellt ({title}).")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Issue konnte nicht erstellt werden – {exc}")
        return

    first, dups = existing[0], existing[1:]
    num = first.get("number")
    print(f"{'🕵 DRY-RUN:' if dry_run else '🔁'} Issue #{num} → "
          f"{'würde aktualisiert' if dry_run else 'aktualisiert'} (kein Duplikat)")
    if not dry_run:
        try:
            gh_api("PATCH", f"/repos/{owner}/{name}/issues/{num}", token,
                   {"title": title, "body": body})
            gh_api("POST", f"/repos/{owner}/{name}/issues/{num}/comments", token,
                   {"body": f"{ISSUE_MARKER}\n🔁 Bestand-Gate lief erneut ({now}), "
                            f"Befund aktualisiert. Exit-Code {exit_code} – genau EIN "
                            "Issue pro Schadenslage."})
            print(f"🔁 Issue #{num} aktualisiert (kein Duplikat).")
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Issue #{num} konnte nicht aktualisiert werden – {exc}")
    for dup in dups:
        dnum = dup.get("number")
        print(f"{'🕵 DRY-RUN:' if dry_run else '🧹'} Duplikat #{dnum} → "
              f"{'würde geschlossen' if dry_run else 'geschlossen'}")
        if dry_run:
            continue
        try:
            gh_api("POST", f"/repos/{owner}/{name}/issues/{dnum}/comments", token,
                   {"body": f"{ISSUE_MARKER}\n🧹 Duplikat – geschlossen, "
                            f"weiter geht es in Issue #{num}."})
            gh_api("PATCH", f"/repos/{owner}/{name}/issues/{dnum}", token,
                   {"state": "closed", "state_reason": "not_planned"})
        except Exception as exc:  # noqa: BLE001
            print(f"⚠️ Duplikat #{dnum} konnte nicht geschlossen werden – {exc}")


# ------------------------------------------------------------------ #
#  Report
# ------------------------------------------------------------------ #
def render_report(all_slugs: set[str], still_affected: dict, errors: list[str],
                  healed_dims: list[str]) -> str:
    lines = [
        "# 📋 BESTAND-REPORT (bestand_gate.py)",
        "",
        f"**Geprüfte Live-Artikel:** {len(all_slugs)} · **Heilung versucht:** "
        f"{', '.join(healed_dims) or '–'} · **Weiterhin auffällig:** {len(still_affected)}"
        + (" · ⚠️ **Auswertungsfehler:** " + str(len(errors)) if errors else ""),
        "",
    ]
    if errors:
        lines.append("⚠️ Auswertungsfehler: " + "; ".join(errors))
        lines.append("")

    if errors and not still_affected:
        # FAIL-CLOSED (02.09.2026): Ohne vollständige Prüfung darf der Report
        # NICHT grün aussehen – sonst liest sich ein Werkzeugfehler als
        # "Bestand sauber" (genau die Irreführung, die Exit 2 abschafft).
        lines.append(
            "🟠 **Bestand gilt als NICHT geprüft** – mindestens eine Prüfung konnte "
            "nicht ausgewertet werden (siehe Auswertungsfehler oben). Es wurde "
            "nichts geheilt und nichts gelöscht. Diagnose: "
            "`python3 scripts/affiliate_integrity_gate.py --selftest` und "
            "`hugo --minify` (der Render-Beweis AI4/AI5 braucht `public/`)."
        )
    elif not still_affected:
        lines.append(
            "🎉 Alle bestehenden Artikel erfüllen die aktuelle Publish-Gate-Prüfung "
            "(check_length.py + seo_audit.py + affiliate_profi_check.py + "
            "affiliate_integrity_gate.py) – keine Reparatur nötig, oder erfolgreich "
            "automatisch geheilt."
        )
    else:
        lines.append("### Weiterhin auffällig (NICHT gelöscht – zur redaktionellen Prüfung):")
        lines.append("")
        for slug, detail in still_affected.items():
            lines.append(f"#### {slug}")
            if detail["length"]:
                lines.append("- ⚠️ Länge außerhalb 700-1800 Wörter (braucht echte Textarbeit, nicht automatisch heilbar)")
            if detail["seo"]:
                lines.append("- ⚠️ SEO-Mangel laut seo_audit.py besteht nach meta_optimizer.py --fix weiter")
            for msg in detail["affiliate"]:
                lines.append(f"- ⚠️ {msg}")
            for msg in detail["integrity"]:
                lines.append(f"- ⚠️ Affiliate-Link-Integrität (CTA defekt/nicht gerendert), Selbstheilung fehlgeschlagen: {msg}")
            lines.append("")
        lines.append(
            "---\n_Bestandsartikel werden NIE automatisch gelöscht (anders als druckfrische Kandidaten in "
            "publish_gate.py) – nur geheilt oder gemeldet, da sie bereits veröffentlicht/indexiert sein können._"
        )
    return "\n".join(lines)


def main():
    # --selftest: nur der Detektor-Vorbeweis (z. B. für lokale Diagnose/CI).
    if SELFTEST_ONLY:
        ok, msg = detector_selftest()
        print(msg)
        return 0 if ok else 2

    all_slugs = set(live_slugs())

    # 1) VORBEWEIS: Detektor muss erst sehen können, bevor er urteilt
    #    (Issue #149/#146). Bei Drift fail-closed: keine Bewertung, keine
    #    Heilung, kein Verwurf.
    selftest_ok, selftest_msg = detector_selftest()

    if not selftest_ok:
        errors = [selftest_msg]
        healed_dims: list[str] = []
        still_affected: dict = {}
        exit_code = 2
    else:
        # 2) Bewertung mit denselben publish_gate-Funktionen wie für
        #    druckfrische Artikel.
        findings, errors = run_gate()
        affected = {s for s in (findings["length"] | findings["seo"]
                                | set(findings["affiliate"].keys())
                                | set(findings["integrity"].keys()))
                    if s in all_slugs}

        healed_dims = []
        if affected and not DRY_RUN:
            if affected & findings["seo"]:
                heal("seo")
                healed_dims.append("seo")
            if affected & set(findings["affiliate"].keys()):
                heal("affiliate")
                healed_dims.append("affiliate")
            if affected & set(findings["integrity"].keys()):
                heal("integrity")
                healed_dims.append("integrity")
            if healed_dims and rebuild_hugo():
                findings, errors = run_gate()  # erneut prüfen nach Heilungsversuch

        still_affected = {
            s: {
                "length": s in findings["length"],
                "seo": s in findings["seo"],
                "affiliate": findings["affiliate"].get(s, []),
                "integrity": findings["integrity"].get(s, []),
            }
            for s in all_slugs
            if s in findings["length"] or s in findings["seo"] or s in findings["affiliate"]
            or s in findings["integrity"]
        }

        # EXIT-CODES (02.09.2026): 0 = grün, 1 = Inhaltsschaden, 2 = Auswertungsfehler.
        exit_code = 2 if errors else (0 if not still_affected else 1)

    state = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "exit_code": exit_code,
        "checked": len(all_slugs),
        "healing_attempted": healed_dims,
        "still_affected": sorted(still_affected.keys()),
        "errors": errors,
    }

    report_text = render_report(all_slugs, still_affected, errors, healed_dims)
    REPORT.write_text(report_text + "\n", encoding="utf-8")
    write_state(state)

    if AS_JSON:
        # --json ist eine reine Maschinen-Schnittstelle: NUR JSON auf stdout.
        print(json.dumps({
            "generated_at": state["generated_at"],
            "exit_code": exit_code,
            "checked": len(all_slugs),
            "healing_attempted": healed_dims,
            "still_failing": still_affected,
            "errors": errors,
            "selftest": "drift" if not selftest_ok else "ok",
        }, ensure_ascii=False, indent=2))
        return exit_code

    print(report_text)
    if not selftest_ok:
        print("🛡️ Detektor-Drift: Bewertung/Heilung übersprungen (fail-closed) – "
              "nichts geheilt, nichts verworfen.")
    # 3) Idempotente Issue-Pflege DIREKT im Skript (kein Workflow-Patch).
    manage_issues(exit_code, report_text, DRY_RUN)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
