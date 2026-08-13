#!/usr/bin/env python3
# ============================================================
#  BESTAND-GATE – wendet die AKTUELLE Publish-Gate-Prüfung auch auf
#  BESTANDSDATEN (bereits veröffentlichte, ältere Artikel) an.
#
#  Auftrag (13.08.2026, Frank): "Sorge dafür, dass die jetzige Artikel-
#  Veröffentlichungsroutine auch für die bestehenden Artikel gilt, und
#  dass jede Änderung am Blog auch für die Bestandsdaten gilt."
#
#  HINTERGRUND: scripts/publish_gate.py prüft die 3 harten Kriterien
#  (check_length.py, seo_audit.py, affiliate_profi_check.py) NUR für
#  Artikel, die HEUTE neu erzeugt wurden (todays_live_candidates()) –
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
#       heutigen) mit denselben drei Funktionen aus publish_gate.py –
#       echte Wiederverwendung, kein Parallel-Code. Jede künftige
#       Verschärfung/Änderung der Gate-Logik gilt dadurch automatisch
#       auch hier, ohne dass dieses Skript angefasst werden muss.
#    2. Für jeden Fund wird die passende bestehende Selbstheilung
#       versucht (meta_optimizer.py --fix für SEO-Mängel,
#       affiliate_profi_check.py --fix für A1-A8), danach erneut
#       geprüft.
#    3. Was danach IMMER NOCH nicht besteht, wird NIEMALS gelöscht,
#       sondern klar für redaktionelle Prüfung gemeldet
#       (BESTAND-REPORT.md, Exit 1 -> löst das bestehende
#       Fehler-Alerting aus). Längen-Probleme sind grundsätzlich nicht
#       automatisch heilbar (brauchen echte Textarbeit).
#
#  Aufruf:
#    python3 scripts/bestand_gate.py             # prüfen + heilen
#    python3 scripts/bestand_gate.py --dry-run   # nur prüfen, nicht heilen
#    python3 scripts/bestand_gate.py --json
#
#  Workflow: .github/workflows/seo-weekly.yml (nach den bestehenden
#  Fix-Schritten, als abschließende Konformitäts-Prüfung).
# ============================================================

import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "content" / "posts"
REPORT = ROOT / "BESTAND-REPORT.md"

DRY_RUN = "--dry-run" in sys.argv
AS_JSON = "--json" in sys.argv

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


def run_gate():
    """Importiert publish_gate.py und ruft dieselben drei Prüf-Funktionen
    auf, die auch für druckfrische Artikel gelten – echte Wiederverwendung,
    kein Parallel-Code. Setzt daher voraus, dass vorher `hugo --minify`
    gelaufen ist (wie publish_gate.py selbst dokumentiert)."""
    if "publish_gate" in sys.modules:
        del sys.modules["publish_gate"]
    pg = __import__("publish_gate")

    length_failed, length_err = pg.check_length_failures()
    seo_failed, seo_err = pg.seo_audit_failures()
    affiliate_failed, affiliate_err = pg.affiliate_profi_failures()

    return {
        "length": length_failed,
        "seo": seo_failed,
        "affiliate": affiliate_failed,
    }, [e for e in (length_err, seo_err, affiliate_err) if e]


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
    # "length" (zu kurz/zu lang) ist nicht automatisch heilbar – braucht
    # echte Textarbeit, wird nur gemeldet.


def main():
    all_slugs = set(live_slugs())
    findings, errors = run_gate()

    affected = {s for s in (findings["length"] | findings["seo"] | set(findings["affiliate"].keys()))
                if s in all_slugs}

    healed_dims = []
    if affected and not DRY_RUN:
        if affected & findings["seo"]:
            heal("seo")
            healed_dims.append("seo")
        if affected & set(findings["affiliate"].keys()):
            heal("affiliate")
            healed_dims.append("affiliate")
        if healed_dims and rebuild_hugo():
            findings, errors = run_gate()  # erneut prüfen nach Heilungsversuch

    still_affected = {
        s: {
            "length": s in findings["length"],
            "seo": s in findings["seo"],
            "affiliate": findings["affiliate"].get(s, []),
        }
        for s in all_slugs
        if s in findings["length"] or s in findings["seo"] or s in findings["affiliate"]
    }

    if AS_JSON:
        result = {
            "checked": len(all_slugs),
            "healing_attempted": healed_dims,
            "still_failing": still_affected,
            "errors": errors,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 1 if still_affected else 0

    lines = [
        "# 📋 BESTAND-REPORT (bestand_gate.py)",
        "",
        f"**Geprüfte Live-Artikel:** {len(all_slugs)} · **Heilung versucht:** "
        f"{', '.join(healed_dims) or '–'} · **Weiterhin auffällig:** {len(still_affected)}",
        "",
    ]
    if errors:
        lines.append("⚠️ Auswertungsfehler: " + "; ".join(errors))
        lines.append("")

    if not still_affected:
        lines.append(
            "🎉 Alle bestehenden Artikel erfüllen die aktuelle Publish-Gate-Prüfung "
            "(check_length.py + seo_audit.py + affiliate_profi_check.py) – "
            "keine Reparatur nötig, oder erfolgreich automatisch geheilt."
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
            lines.append("")
        lines.append(
            "---\n_Bestandsartikel werden NIE automatisch gelöscht (anders als druckfrische Kandidaten in "
            "publish_gate.py) – nur geheilt oder gemeldet, da sie bereits veröffentlicht/indexiert sein können._"
        )

    report_text = "\n".join(lines)
    print(report_text)
    REPORT.write_text(report_text + "\n", encoding="utf-8")
    return 1 if still_affected else 0


if __name__ == "__main__":
    sys.exit(main())
