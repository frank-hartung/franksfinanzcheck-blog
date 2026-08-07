#!/usr/bin/env python3
"""
Meta-Qualitäts-Gate für FranksFinanzcheck – VOLLAUTOMATISCH.

Prüft nach der Meta-Optimierung (meta_optimizer.py --fix --ai) ALLE
Artikel erneut, erzeugt einen kompakten Report (META-REPORT.md) und
liefert den Exit-Code für den Workflow:

    Exit 0 = alle Meta-Daten auf Profi-Niveau (kein Handlungsbedarf)
    Exit 1 = kritische Probleme verbleiben → der Workflow erstellt
             automatisch ein GitHub-Issue (keine manuelle Sichtung nötig)

Der Report wird vom Workflow automatisch committet – du siehst ihn
jederzeit im Repo, musst ihn aber nie aktiv prüfen: Es gibt nur zwei
Zustände – "alles grün" (Report) oder "Issue erstellt" (GitHub-Meldung).

Nutzung:
    python3 scripts/meta_report.py            # Audit + Report + Exit-Code
"""
import os
import re
import sys
import json
import datetime

# Importiere die Audit-Logik aus meta_optimizer (läuft dort im __main__-Guard)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import meta_optimizer as mo

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORT_FILE = os.path.join(BLOG_DIR, "META-REPORT.md")
JSON_FILE = os.path.join(BLOG_DIR, ".meta_report.json")


def score_article(r):
    """Berechnet einen 0-100-Qualitätsscore für einen Artikel."""
    score = 100
    score -= len(r["issues"]) * 15          # jede Issue -15
    # Längen-Bonus/Malus für CTR-Optimalität (Titel 50-60, Desc 120-155)
    if not (50 <= r["tl"] <= 60):
        score -= 5
    if not (120 <= r["dl"] <= 160):
        score -= 5
    return max(0, min(100, score))


def main():
    articles = mo.load_articles()
    results = [mo.audit(a) for a in articles]
    for r in results:
        r["score"] = score_article(r)

    critical = [r for r in results if r["issues"]]
    avg_tl = sum(r["tl"] for r in results) / len(results) if results else 0
    avg_dl = sum(r["dl"] for r in results) / len(results) if results else 0
    avg_score = sum(r["score"] for r in results) / len(results) if results else 0
    today = datetime.date.today().isoformat()

    # ---- Markdown-Report ----
    lines = [
        f"# 📋 Meta-Daten-Report – {today}",
        "",
        f"> **Vollautomatisch** erzeugt vom wöchentlichen SEO-Workflow. "
        f"Keine manuelle Sichtung nötig: Bei verbleibenden Problemen "
        f"erstellt der Workflow automatisch ein GitHub-Issue.",
        "",
        "## Zusammenfassung",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Artikel geprüft | {len(results)} |",
        f"| Ø Qualitätsscore | **{avg_score:.0f}/100** |",
        f"| Ø Titel-Länge | {avg_tl:.0f} Zeichen (optimal 50–60) |",
        f"| Ø Description-Länge | {avg_dl:.0f} Zeichen (optimal 120–160) |",
        f"| Artikel mit Problemen | **{len(critical)}** |",
        "",
        "## Status",
        "",
    ]
    if critical:
        lines.append(f"### ⚠️ {len(critical)} Artikel brauchen Aufmerksamkeit")
        lines.append("")
        lines.append("> Ein GitHub-Issue wurde automatisch erstellt – Details siehe dort.")
        lines.append("")
    else:
        lines.append("### ✅ Alle Meta-Daten auf Profi-Niveau")
        lines.append("")
        lines.append("Alle Titel, Descriptions und Keywords sind im optimalen Bereich.")
        lines.append("")

    # ---- Detail-Tabelle ----
    lines += ["## Detail-Übersicht", "", "| Score | Artikel | Titel | Desc | Keywords | Status |",
              "|---|---|---|---|---|---|"]
    for r in sorted(results, key=lambda x: x["score"]):
        status = "✅" if not r["issues"] else f"⚠️ ({len(r['issues'])})"
        issues = "; ".join(r["issues"]) if r["issues"] else "–"
        lines.append(
            f"| {r['score']} | {r['title']} | {r['tl']} | {r['dl']} | {r['kw']} | {status} |"
        )
        if r["issues"]:
            lines.append(f"| | | | | | `{issues}` |")

    lines += ["", "---", f"*Erzeugt am {today} um {datetime.datetime.now().strftime('%H:%M')} Uhr "
                        "vom SEO-Bot – Änderungen an diesem Report werden automatisch überschrieben.*"]

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # ---- JSON für den Workflow (Issue-Details) ----
    with open(JSON_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "date": today,
            "articles": len(results),
            "avg_score": round(avg_score, 1),
            "avg_title_len": round(avg_tl, 1),
            "avg_desc_len": round(avg_dl, 1),
            "critical": [{"title": r["title"], "issues": r["issues"]} for r in critical],
        }, f, ensure_ascii=False, indent=2)

    # ---- Konsolen-Ausgabe (Workflow-Log) ----
    print(f"Meta-Qualitäts-Gate: {len(results)} Artikel | Ø Score {avg_score:.0f}/100 | "
          f"Ø Titel {avg_tl:.0f} | Ø Desc {avg_dl:.0f} | Probleme: {len(critical)}")
    for r in sorted(critical, key=lambda x: x["score"]):
        print(f"  ⚠️ {r['title']} [{r['score']}]: {'; '.join(r['issues'])}")
    print(f"Report: {REPORT_FILE}")

    sys.exit(1 if critical else 0)


if __name__ == "__main__":
    main()
