#!/usr/bin/env python3
"""publish_gate.py – Harte Vor-Publish-Kontrolle (13.08.2026)

Betriebsregel (Frank, 13.08.2026, erweitert 14.08.2026): Zukünftige Artikel
werden nur dann tatsächlich live geschaltet, wenn sie SIEBEN automatische
Prüfungen bestehen:

  1. check_length.py          – Zeichenlänge Premium (Floor 10.000, Optimum 12.000–18.000)
  2. seo_audit.py              – Title/Description-Länge, Wortzahl, Alt-Texte,
                                  Sitemap-Konsistenz
  3. affiliate_profi_check.py  – A1-A8: Offenlegung, E-E-A-T-Feld, interne
                                  Links, Schema.org, Affiliate-Dichte,
                                  Trust-Box, Autor, CTA-Vorhandensein
  4. affiliate_integrity_gate.py – AI1-AI4: strukturell vollständige CTA-
                                  Markdown-Links, nur registrierte /go/-
                                  Redirects (keine rohen Partner-URLs),
                                  Text-Plausibilität an der CTA, UND Render-
                                  Beweis (Link erscheint tatsächlich im
                                  gebauten HTML unter public/, nicht nur im
                                  Markdown-Quelltext). Grund: Vorfall
                                  14.08.2026, bei dem 8 Live-Artikel
                                  beschädigte CTA-Boxen hatten, die von den
                                  ersten drei Prüfungen NICHT erkannt wurden
                                  (siehe Kopfkommentar in
                                  affiliate_integrity_gate.py).

Läuft NACH der bestehenden Qualitäts-/Selbstheilungs-Kette (Rechtschreibung,
Meta-Optimierung, interne Verlinkung, affiliate_profi_check --fix, …) und
NACH quality_score.py (das bereits Rechtschreibung/Struktur/Einzigartigkeit
etc. bewertet) – aber VOR dem Deploy-Trigger. Ein Artikel muss also sowohl
den aggregierten Qualitäts-Score als auch dieses harte Gate bestehen, um
wirklich live zu gehen.

WICHTIG: Damit seo_audit.py und affiliate_profi_check.py echte Ergebnisse
liefern (sie lesen z. T. aus public/), MUSS vor diesem Skript ein
`hugo --minify` gelaufen sein.

Wirkung bei Nicht-Bestehen (13.08.2026, "so wenig wie möglich zu tun"-
Betriebsregel): Der betroffene Artikel wird NICHT mehr auf `draft: true`
zurückgestuft (das hätte einen Entwurf hinterlassen, den jemand von Hand
fertigstellen müsste), sondern komplett VERWORFEN – Content-Datei und
generierte Cover-Bilder werden gelöscht. Es entsteht kein Artefakt, das
Aufmerksamkeit braucht. Der nächste Cron-Lauf (mehrere pro Publikationstag)
versucht automatisch ein neues Thema.

Geprüft werden nur Artikel, die HEUTE erzeugt wurden (Ordner-Datumspräfix)
und aktuell auf draft:false stehen – also genau die Kandidaten, die dieser
Lauf gerade live schalten würde.

Exit-Code: immer 0 (das Gate degradiert nie den ganzen Workflow – es
verwirft nur einzelne Artikel). Mit --strict: Exit 1, falls mindestens
1 Artikel verworfen wurde (nützlich für CI-Sichtbarkeit/Statistik).

Nutzung:
  python3 scripts/publish_gate.py             # anwenden (Default)
  python3 scripts/publish_gate.py --dry-run   # nur anzeigen, nichts ändern
  python3 scripts/publish_gate.py --strict    # Exit 1 bei Zurückstufung
"""
import datetime
import glob
import json
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")

DRY_RUN = "--dry-run" in sys.argv
STRICT = "--strict" in sys.argv


def todays_live_candidates():
    """Slugs, die dieser Lauf gerade live schalten würde:
      (1) NEUE Artikel: Ordner-Präfix = heute, aktuell draft:false
      (2) Re-Queue-Promotions (26.08.2026): Frontmatter-Datum = heute,
          Ordner-Präfix bleibt alt (stabile URLs/Covers) – die zählen
          ebenfalls als "heute live geschaltet" und müssen das Gate
          ebenso bestehen."""
    today = datetime.date.today().isoformat()
    candidates = []
    for path in glob.glob(os.path.join(POSTS_DIR, "*", "index.md")):
        slug = os.path.basename(os.path.dirname(path))
        content = open(path, encoding="utf-8").read()
        if re.search(r"^draft:\s*true", content, re.M):
            continue
        if slug.startswith(today):
            candidates.append(slug)
            continue
        m = re.search(r"(?m)^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", content)
        if m and m.group(1) == today:
            candidates.append(slug)
    return candidates


def title_integrity_failures(candidates):
    """Cover-Text-Komplettheit (26.08.2026): Titel mit R5-Verstoß
    (vermutlich unvollständig/abgebrochen) dürfen nicht live gehen –
    der Cover-Text würde unvollständig abgebildet.

    Rückgabe: Set der Slugs mit R5-Verstoß. Die Haupt-Schleife entscheidet
    anhand des Ordner-Präfixes, was passiert:
      NEUE Artikel (Präfix = heute) → Verwurf (Betriebsregel 13.08.2026),
      Re-Queue-Posts (alter Ordner) → draft (Content bleibt erhalten)."""
    from check_titles import check_title
    failed = set()
    for slug in candidates:
        path = os.path.join(POSTS_DIR, slug, "index.md")
        if not os.path.exists(path):
            continue
        content = open(path, encoding="utf-8").read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        if not m:
            continue
        issues = check_title(m.group(1))
        if any(rule == "R5" for rule, _ in issues):
            failed.add(slug)
    return failed


def _run_json(cmd):
    """Führt ein Prüfskript aus und extrahiert den JSON-Block aus stdout.

    Die Skripte drucken unterschiedlich viel Klartext vor dem JSON (manche
    gar keinen, manche mehrere Zeilen) und formatieren das JSON teils
    einzeilig, teils mit indent=2 über mehrere Zeilen (z. B. seo_audit.py,
    das dabei auch verschachtelte '{'-Zeilen enthält). Robuste Lösung: von
    vorne die erste Zeile suchen, ab der der REST von stdout komplett als
    JSON geparst werden kann.
    """
    proc = subprocess.run(
        [sys.executable] + cmd, cwd=BLOG_DIR,
        capture_output=True, text=True, check=False,
    )
    lines = proc.stdout.splitlines()
    for i, line in enumerate(lines):
        if not line.strip().startswith("{"):
            continue
        blob = "\n".join(lines[i:])
        try:
            return json.loads(blob)
        except json.JSONDecodeError:
            continue
    return None


def check_length_failures():
    """Slugs mit 'zu-kurz'/'zu-lang' (hartes Kriterium; 'unter/ueber-optimum'
    ist nur ein Hinweis, kein Ausschlussgrund)."""
    data = _run_json(["scripts/check_length.py", "--json"])
    if not data:
        return set(), "check_length.py: keine Auswertung möglich"
    failed = {
        item["slug"] for item in data.get("items", [])
        if item.get("status") in ("zu-kurz", "zu-lang")
    }
    return failed, None


def seo_audit_failures():
    """Slugs mit score_issues > 0 (harte SEO-Mängel; 'tips' sind nur
    Empfehlungen und blockieren nicht)."""
    data = _run_json(["scripts/seo_audit.py", "--json"])
    if not data:
        return set(), "seo_audit.py: keine Auswertung möglich (public/ gebaut?)"
    failed = {
        d["file"] for d in data.get("details", [])
        if d.get("score_issues", 0) > 0
    }
    sitemap_issues = [s for s in data.get("sitemap_issues", []) if s]
    return failed, ("; ".join(sitemap_issues) if sitemap_issues else None)


def affiliate_profi_failures():
    """Slugs mit verbleibenden A1-A8-Problemen nach der --fix-Kette."""
    data = _run_json(["scripts/affiliate_profi_check.py", "--json"])
    if not data:
        return {}, "affiliate_profi_check.py: keine Auswertung möglich (public/ gebaut?)"
    per_slug = {}
    for code, slug, msg in data.get("problems", []):
        per_slug.setdefault(slug, []).append(f"{code}: {msg}")
    return per_slug, None


def affiliate_integrity_failures():
    """Slugs mit strukturell defekten/nicht gerenderten CTA-Boxen (14.08.2026,
    4. hartes Kriterium – siehe scripts/affiliate_integrity_gate.py).
    Läuft im --dry-run-Modus, da hier NUR geprüft wird: Heilung für
    Bestandsdaten passiert separat in bestand_gate.py; ein druckfrischer
    Kandidat, der hier durchfällt, wird stattdessen verworfen (Ebene 2:
    neues Thema statt kaputte Links live zu schalten)."""
    data = _run_json(["scripts/affiliate_integrity_gate.py", "--dry-run", "--json"])
    if not data:
        return {}, "affiliate_integrity_gate.py: keine Auswertung möglich (public/ gebaut?)"
    per_slug = {}
    for slug, info in data.get("findings", {}).items():
        per_slug[slug] = info.get("problems", [])
    for slug, msg in data.get("render_problems", {}).items():
        per_slug.setdefault(slug, []).append(msg)
    return per_slug, None



def readability_failures(candidates):
    """Live-Kandidaten mit Lesbarkeits-Score unter Top-Level (75) finden.

    Der Publish-Pfad bewertet bewusst pro Kandidat. Fällt der Prüfer selbst
    aus, gilt fail-closed: kein neuer Artikel darf ungeprüft live gehen.
    """
    try:
        from readability_check import load_article, analyze
    except Exception as exc:
        reason = f"Lesbarkeitsprüfung nicht verfügbar: {exc}"
        return {slug: [reason] for slug in candidates}, None

    failed = {}
    for slug in candidates:
        path = os.path.join(POSTS_DIR, slug, "index.md")
        error = "Lesbarkeitsprüfung lieferte kein Ergebnis"
        try:
            article = load_article(path)
            result = analyze(article) if article else None
        except Exception as exc:
            result = None
            error = f"Lesbarkeitsprüfung nicht auswertbar: {exc}"
        if not result:
            failed[slug] = [error]
            continue
        if result.get("score", 0) < 75:
            detail = "; ".join(result.get("issues", [])) or "Score unter 75"
            failed[slug] = [
                f"Lesbarkeits-Score {result.get('score', 0)}/100 (Mindestwert 75): {detail}"
            ]
    return failed, None


def textverstaendnis_failures(candidates):
    """Harte R2/R3/R5/R7/R8-URL-Verstöße pro Kandidat finden.

    R4 und R8-Anker bleiben bewusst Review-Hinweise; die deterministisch
    harten Regeln blockieren dagegen jede neue Veröffentlichung.
    """
    try:
        from textverstaendnis_guard import (
            split_body, load_terminologie, check_article,
        )
        hard_rules = {
            "R2-KEYWORD-DUMP", "R3-TERMINOLOGIE",
            "R5-ABSATZ-HART", "R7-INTRO-FORMEL",
            "R8-URL-LEERZEICHEN",
        }
        term = load_terminologie()
        failed = {}
        for slug in candidates:
            path = os.path.join(POSTS_DIR, slug, "index.md")
            body = split_body(open(path, encoding="utf-8").read())
            finds = [f for f in check_article(
                os.path.join("content", "posts", slug, "index.md"),
                body, term
            ) if f[1] in hard_rules]
            if finds:
                failed[slug] = [f"{rule}: {detail}" for _, rule, detail, _ in finds[:5]]
        return failed, None
    except Exception as exc:
        reason = f"Textverständnisprüfung nicht verfügbar: {exc}"
        return {slug: [reason] for slug in candidates}, None

def discard_article(slug):
    """Löscht einen durchgefallenen Artikel vollständig: Content-Bundle +
    generierte Cover-Bilder (alle Größen/Formate). Kein Artefakt bleibt
    zurück, das jemand von Hand anfassen müsste."""
    import shutil
    import glob as _glob
    bundle_dir = os.path.join(POSTS_DIR, slug)
    if os.path.isdir(bundle_dir):
        shutil.rmtree(bundle_dir)
    # Cover-Varianten: static/images/covers/<slug>.*, .../620/<slug>.*,
    # .../720/<slug>.*, .../webp/<slug>.*, .../avif/<slug>.*
    cover_root = os.path.join(BLOG_DIR, "static", "images", "covers")
    for path in _glob.glob(os.path.join(cover_root, "**", f"{slug}.*"), recursive=True):
        try:
            os.remove(path)
        except OSError:
            pass


def main():
    candidates = todays_live_candidates()
    if not candidates:
        print("Publish-Gate: keine heutigen Live-Kandidaten – nichts zu prüfen.")
        return 0

    print(f"Publish-Gate: {len(candidates)} Kandidat(en) für heute → {candidates}")

    today = datetime.date.today().isoformat()
    len_fail, len_warn = check_length_failures()
    seo_fail, seo_warn = seo_audit_failures()
    aff_fail, aff_warn = affiliate_profi_failures()
    integ_fail, integ_warn = affiliate_integrity_failures()
    r5_fail = title_integrity_failures(candidates)
    readability_fail, readability_warn = readability_failures(candidates)
    understanding_fail, understanding_warn = textverstaendnis_failures(candidates)
    for w in (len_warn, seo_warn):
        if w:
            print(f"⚠ {w}")
    if aff_warn:
        print(f"⚠ {aff_warn}")
    if integ_warn:
        print(f"⚠ {integ_warn}")
    if readability_warn:
        print(f"⚠ {readability_warn}")
    if understanding_warn:
        print(f"⚠ {understanding_warn}")

    gated = []
    demoted = []
    for slug in candidates:
        reasons = []
        if slug in len_fail:
            reasons.append("Zeichenlänge (check_length.py) nicht bestanden")
        if slug in seo_fail:
            reasons.append("SEO-Audit (seo_audit.py) nicht bestanden")
        if slug in aff_fail:
            reasons.append("Profi-Affiliate-Check nicht bestanden: " + "; ".join(aff_fail[slug]))
        if slug in integ_fail:
            reasons.append("Affiliate-Link-Integrität nicht bestanden (defekte/nicht gerenderte CTA): "
                            + "; ".join(integ_fail[slug]))
        if slug in r5_fail:
            reasons.append("Cover-Text-Komplettheit (check_titles R5) nicht bestanden – "
                           "Titel vermutlich unvollständig")
        if slug in readability_fail:
            reasons.append("Lesbarkeits-Gate nicht bestanden: " + "; ".join(readability_fail[slug]))
        if slug in understanding_fail:
            reasons.append("Textverständnis-Gate nicht bestanden: " + "; ".join(understanding_fail[slug]))

        if reasons:
            if slug.startswith(today):
                # NEUER Artikel: Verwurf (Betriebsregel 13.08.2026:
                # kein Artefakt – der nächste Slot erzeugt frischen Content)
                gated.append((slug, reasons))
                print(f"  🛑 {slug}: WIRD VERWORFEN (kein Artefakt, nächster Lauf versucht neues Thema)")
                for r in reasons:
                    print(f"     - {r}")
                if not DRY_RUN:
                    discard_article(slug)
            else:
                # Re-Dated/Re-Queue-Post (alter Ordner): Content war
                # bereits akzeptiert – NIE löschen. Auf draft zurück-
                # stufen + Re-Queue-Flag entfernen (sonst würde der
                # nächste Slot denselben Post erneut promoten).
                # Frank korrigiert (z. B. den Titel) und gibt frei.
                gated.append((slug, reasons))
                demoted.append(slug)
                print(f"  🛑 {slug}: PRÜFUNG NICHT BESTANDEN (Re-Queue-Post) → draft, Content erhalten")
                for r in reasons:
                    print(f"     - {r}")
                if not DRY_RUN:
                    # park_state.hold() statt Hand-Regex: draft: true,
                    # cadence_wait bewusst WEG – und der Grund bleibt
                    # dokumentiert stehen. Genau das fehlte bisher: ohne
                    # Grund-Feld war "draft ohne cadence_wait" mehrdeutig
                    # (manueller Entwurf? Gate-Hemmung? verlorenes Flag?)
                    # und die Kadenz-Wache konnte die Hemmung nicht von einem
                    # Bug unterscheiden. Jetzt: cadence_guard queue_integrity()
                    # hält diesen Post korrekt zurück und meldet ihn im Report.
                    path = os.path.join(POSTS_DIR, slug, "index.md")
                    try:
                        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
                        import park_state
                        grund = "publish-gate: " + "; ".join(reasons)
                        if len(grund) > 180:      # Grund bleibt lesbar
                            grund = grund[:177] + "…"
                        park_state.hold(path, grund)
                    except Exception as exc:      # nie am Gate scheitern
                        print(f"  ⚠ {slug}: park_state nicht nutzbar "
                              f"({exc}) – nur draft gesetzt")
                        content = open(path, encoding="utf-8").read()
                        content = re.sub(r"(?m)^draft:\s*false\s*$",
                                         "draft: true", content, count=1)
                        open(path, "w", encoding="utf-8").write(content)

    if gated:
        try:
            sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
            from audit_log import log_event
            log_event(module="publish_gate", action="gate",
                      input={"candidates": candidates},
                      output={"gated": [g[0] for g in gated],
                              "demoted": demoted},
                      status="gated")
        except Exception:
            pass

    print(f"\nErgebnis: {len(gated)}/{len(candidates)} Artikel am Gate scheitern "
          f"({len(gated) - len(demoted)} verworfen, {len(demoted)} → draft).")
    if STRICT and gated:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
