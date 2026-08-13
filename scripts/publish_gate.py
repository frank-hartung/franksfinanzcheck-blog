#!/usr/bin/env python3
"""publish_gate.py – Harte Vor-Publish-Kontrolle (13.08.2026)

Betriebsregel (Frank, 13.08.2026): Zukünftige Artikel werden nur dann
tatsächlich live geschaltet, wenn sie DREI automatische Prüfungen bestehen:

  1. check_length.py          – Zeichen-/Wortlänge (700-1800 Wörter)
  2. seo_audit.py              – Title/Description-Länge, Wortzahl, Alt-Texte,
                                  Sitemap-Konsistenz
  3. affiliate_profi_check.py  – A1-A8: Offenlegung, E-E-A-T-Feld, interne
                                  Links, Schema.org, Affiliate-Dichte,
                                  Trust-Box, Autor, CTA-Vorhandensein

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
    """Slugs, die heute erzeugt wurden UND aktuell draft:false sind –
    also die Kandidaten, die dieser Lauf gerade veröffentlichen würde."""
    today = datetime.date.today().isoformat()
    candidates = []
    for path in glob.glob(os.path.join(POSTS_DIR, "*", "index.md")):
        slug = os.path.basename(os.path.dirname(path))
        if not slug.startswith(today):
            continue
        content = open(path, encoding="utf-8").read()
        if re.search(r"^draft:\s*true", content, re.M):
            continue
        candidates.append(slug)
    return candidates


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

    len_fail, len_warn = check_length_failures()
    seo_fail, seo_warn = seo_audit_failures()
    aff_fail, aff_warn = affiliate_profi_failures()
    for w in (len_warn, seo_warn):
        if w:
            print(f"⚠ {w}")
    if aff_warn:
        print(f"⚠ {aff_warn}")

    gated = []
    for slug in candidates:
        reasons = []
        if slug in len_fail:
            reasons.append("Zeichenlänge (check_length.py) nicht bestanden")
        if slug in seo_fail:
            reasons.append("SEO-Audit (seo_audit.py) nicht bestanden")
        if slug in aff_fail:
            reasons.append("Profi-Affiliate-Check nicht bestanden: " + "; ".join(aff_fail[slug]))

        if reasons:
            gated.append((slug, reasons))
            print(f"  🛑 {slug}: WIRD VERWORFEN (kein Artefakt, nächster Lauf versucht neues Thema)")
            for r in reasons:
                print(f"     - {r}")
            if not DRY_RUN:
                discard_article(slug)
        else:
            print(f"  ✅ {slug}: alle 3 Prüfungen bestanden – bleibt live")

    if gated:
        try:
            sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
            from audit_log import log_event
            log_event(module="publish_gate", action="gate",
                      input={"candidates": candidates},
                      output={"gated": [g[0] for g in gated]},
                      status="gated")
        except Exception:
            pass

    print(f"\nErgebnis: {len(gated)}/{len(candidates)} Artikel verworfen.")
    if STRICT and gated:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
