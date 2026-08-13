#!/usr/bin/env python3
# ============================================================
#  PILLAR-GUARD – erkennt tote Klartext-Artikelverweise auf Pillar-Seiten
#
#  Auftrag (13.08.2026, Frank): "veraltete Klartext-Artikelverweise auf
#  den Pillar-Seiten" beheben und dauerhaft automatisch überwachen.
#
#  HINTERGRUND: content/pillar/*/index.md verweist in Fließtext oft auf
#  "meinen Ratgeber XY" – meist als echter Markdown-Link (```[Text](../../
#  posts/<slug>/)```), den scripts/link_guard.py bereits auf Totstellen
#  prüft. Es gibt aber eine zweite, bisher UNGEPRÜFTE Variante: reiner
#  Klartext ohne Link, z. B. "erkläre ich in Kreditkarte ohne
#  Jahresgebühr: Die besten kostenlosen Karten." Wird der referenzierte
#  Artikel gelöscht/umbenannt (wie bei der Bereinigung der 9 Alt-Artikel
#  vor Domain-Gültigkeit am 13.08.2026), bleibt so ein Verweis als
#  unsichtbarer "toter Link" stehen – kein 404, aber ein falsches
#  Versprechen an Leser UND ein Vertrauens-/E-E-A-T-Problem.
#
#  METHODE: sucht nach bekannten Einleitungsfloskeln ("erkläre ich in",
#  "steht in", "zeige ich in", "findest du in" ...) gefolgt von einer
#  Phrase in Groß-/Kleinschreibung, die wie ein Artikeltitel aussieht.
#  Bereits als echter Markdown-Link gesetzte Stellen werden vorher
#  ausmaskiert (die prüft link_guard.py bereits separat). Die gefundene
#  Phrase wird per Fuzzy-Match gegen alle ECHTEN (draft:false) Artikel-
#  und Pillar-Titel abgeglichen. Kein hinreichend ähnlicher Titel
#  gefunden -> Verdacht auf Phantom-Verweis.
#
#  BEWUSST NUR REPORT (kein --fix): das Umschreiben von Fließtext ist
#  eine redaktionelle Entscheidung (welcher echte Artikel passt am besten,
#  oder soll die Stelle allgemein formuliert werden?), keine mechanische
#  Reparatur wie bei den anderen Guards. Ergebnis fließt in
#  PILLAR-REPORT.md und (bei Fund) in den Exit-Code für CI-Alarmierung.
#
#  Aufruf:
#    python3 scripts/pillar_guard.py            # Report
#    python3 scripts/pillar_guard.py --json     # JSON für Bots
# ============================================================

import difflib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "content" / "posts"
PILLAR_DIR = ROOT / "content" / "pillar"
REPORT = ROOT / "PILLAR-REPORT.md"

AS_JSON = "--json" in sys.argv

# Einleitungsfloskeln, nach denen üblicherweise ein Artikeltitel folgt
# (aus den echten Pillar-Seiten und dem Content-Engine-Prompt-Stil
# destilliert).
TRIGGERS = [
    "erkläre ich in", "erkläre ich dir in", "steht in", "steht im",
    "zeige ich in", "zeige ich dir in", "findest du in", "findest du im",
    "beschreibe ich in", "beschreibe ich dir in", "aufgeschlüsselt in",
    "in meinem Ratgeber", "im Ratgeber",
]
TRIGGER_RE = re.compile(
    r"(?:" + "|".join(re.escape(t) for t in TRIGGERS) + r")\s+([A-ZÄÖÜ][^.!?\n]{8,90})[.!?]",
)

SIMILARITY_THRESHOLD = 0.6


def _frontmatter_split(text: str):
    if not text.startswith("---"):
        return "", text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return "", text
    return parts[1], parts[2]


def real_titles() -> list[str]:
    titles = []
    for base in (POSTS_DIR, PILLAR_DIR):
        if not base.is_dir():
            continue
        for slug in sorted(os.listdir(base)):
            index_path = base / slug / "index.md"
            if not index_path.is_file():
                continue
            text = index_path.read_text(encoding="utf-8")
            fm, _ = _frontmatter_split(text)
            if re.search(r"^draft:\s*true\s*$", fm, re.MULTILINE):
                continue
            m = re.search(r'^title:\s*"?(.+?)"?\s*$', fm, re.MULTILINE)
            if m:
                titles.append(m.group(1).strip())
    return titles


def mask_real_links(body: str) -> str:
    """Ersetzt echte Markdown-Links durch Platzhalter gleicher Länge, damit
    ihr Linktext den Klartext-Scan nicht doppelt/falsch triggert (die
    Linkziele selbst prüft link_guard.py)."""
    return re.sub(r"\[([^\]]+)\]\(([^)]+)\)", lambda m: "\u0000" * len(m.group(0)), body)


def best_match(candidate: str, titles: list[str]) -> tuple[str, float]:
    cand_norm = candidate.strip().lower()
    best_title, best_ratio = "", 0.0
    for title in titles:
        ratio = difflib.SequenceMatcher(None, cand_norm, title.lower()).ratio()
        if ratio > best_ratio:
            best_title, best_ratio = title, ratio
    return best_title, best_ratio


def check_pillar_file(path: Path, titles: list[str]) -> list[dict]:
    text = path.read_text(encoding="utf-8")
    _, body = _frontmatter_split(text)
    masked = mask_real_links(body)
    findings = []
    for m in TRIGGER_RE.finditer(masked):
        candidate = m.group(1).strip()
        # Platzhalter-Reste (aus maskierten Links) ignorieren
        if "\u0000" in candidate:
            continue
        # Legitime Selbstverweise auf einen Abschnitt WEITER OBEN AUF DERSELBEN
        # Seite ("... im Depot-Ratgeber oben.") sind kein Phantom-Verweis auf
        # einen fehlenden Artikel, sondern beziehen sich aufs eigene Layout.
        if re.search(r"\boben\b\.?$", candidate, re.IGNORECASE):
            continue
        best_title, ratio = best_match(candidate, titles)
        if ratio < SIMILARITY_THRESHOLD:
            findings.append({
                "phrase": candidate,
                "best_match": best_title or None,
                "similarity": round(ratio, 2),
            })
    return findings


def main():
    if not PILLAR_DIR.is_dir():
        print("Keine Pillar-Seiten gefunden.")
        return 0

    titles = real_titles()
    all_findings = {}
    for slug in sorted(os.listdir(PILLAR_DIR)):
        index_path = PILLAR_DIR / slug / "index.md"
        if not index_path.is_file():
            continue
        text = index_path.read_text(encoding="utf-8")
        fm, _ = _frontmatter_split(text)
        if re.search(r"^draft:\s*true\s*$", fm, re.MULTILINE):
            continue  # inaktive Pillar-Seiten (z. B. frugalismus, mietwagen) nicht prüfen
        findings = check_pillar_file(index_path, titles)
        if findings:
            all_findings[slug] = findings

    if AS_JSON:
        print(json.dumps(all_findings, ensure_ascii=False, indent=2))
        return 1 if all_findings else 0

    lines = ["# 🧭 PILLAR-REPORT (pillar_guard.py)", ""]
    if not all_findings:
        lines.append("🎉 Keine Klartext-Verweise auf nicht mehr existierende Artikel gefunden.")
        print("\n".join(lines))
        REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return 0

    lines.append(f"⚠️ {sum(len(v) for v in all_findings.values())} möglicher Phantom-Verweis(e) in "
                 f"{len(all_findings)} Pillar-Seite(n):\n")
    for slug, findings in all_findings.items():
        lines.append(f"### {slug}")
        for f in findings:
            hinweis = (f"ähnlichster echter Titel: „{f['best_match']}“ ({f['similarity']:.0%})"
                       if f["best_match"] else "kein ähnlicher echter Titel gefunden")
            lines.append(f"- „{f['phrase']}“ – {hinweis}")
        lines.append("")
    lines.append(
        "---\n_Kein --fix: Fließtext-Korrektur ist eine redaktionelle Entscheidung. "
        "Bitte manuell prüfen und auf einen echten Artikel verlinken oder allgemein umformulieren._"
    )
    report_text = "\n".join(lines)
    print(report_text)
    REPORT.write_text(report_text + "\n", encoding="utf-8")
    return 1


if __name__ == "__main__":
    sys.exit(main())
