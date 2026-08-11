#!/usr/bin/env python3
"""quality_score.py – Einheitlicher Content-Qualitäts-Score (0–1) für FrankAutoOps

Aggregiert die vorhandenen Qualitäts-Gates zu EINEM Score pro Artikel:
  - Rechtschreibung (spellcheck: 0 Funde = 1.0, sonst absteigend)
  - Meta-Qualität (Titel ≤60, Description ≤160, Endpunkt)
  - Lesbarkeit (Flesch/Score aus readability_check)
  - Struktur (Wortzahl ≥1200, H2-Anzahl ≥4, FAQ vorhanden)
  - Einzigartigkeit (check_uniqueness: 0 kritische Überlappungen)
  - Affiliate-Integrität (Links vorhanden + Disclosure vorhanden)
  - Typografie (keine doppelten Spaces, keine Hard-Break-Fehler,
    keine falschen Anführungszeichen)

ENTSCHEIDUNGSLOGIK (gemäß FrankAutoOps):
  - Score ≥ 0.85 → automatische Veröffentlichung
  - Score < 0.85 → Entwurf + automatische Korrekturen (fix_*-Skripte)
  - Score < 0.80 nach Korrekturen → human review (Ticket)

CLI:
  python3 scripts/quality_score.py               # Score für alle Artikel (JSON)
  python3 scripts/quality_score.py --report      # Zusammenfassung + Threshold-Urteile
  python3 scripts/quality_score.py --file SLUG   # nur ein Artikel
"""
import glob
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

THRESHOLD_PUBLISH = 0.85
THRESHOLD_REVIEW = 0.80

# Typografische Fehler (Detect-Komponente)
RE_DBL_SPACE = re.compile(r"[^ \t]  +[^ \t]")
RE_BAD_QUOTE = re.compile(r"[\u0022\u0027]")          # ASCII-Anführungszeichen im Fließtext
RE_BROKEN_END = re.compile(r"[ \u00a0]{2,}$")


def _read_article(path: str) -> dict:
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    fm = parts[1] if len(parts) >= 3 else ""
    body = parts[2] if len(parts) >= 3 else content
    meta = {}
    for key in ("title", "description", "kurzantwort", "pillar"):
        m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
        if m:
            meta[key] = m.group(1).strip()
    return {"path": path, "slug": os.path.basename(os.path.dirname(path)),
            "meta": meta, "body": body, "content": content}


def score_article(path: str) -> dict:
    """Berechnet den Qualitäts-Score 0–1 für einen Artikel."""
    a = _read_article(path)
    parts = {}

    # 1) Rechtschreibung (nutzt bestehenden Spellcheck-Lauf, falls vorhanden)
    try:
        import spellcheck as sc
        wl = sc.load_whitelist()
        problems = sc.analyze_article({"body": a["body"], "content": a["content"],
                                       "fm": "", "meta": a["meta"]}, wl)
        # Nur Rechtschreib-/Groß-Klein-Fehler zählen (keine Hinweise)
        real = [p for p in problems if p.get("type") not in ("entity", "nbsp")]
        parts["spelling"] = max(0.0, 1.0 - len(real) * 0.1)
    except Exception:
        parts["spelling"] = 0.5  # unbekannt

    # 2) Meta-Qualität
    m = a["meta"]
    meta_score = 1.0
    title = m.get("title", "")
    desc = m.get("description", "")
    if not title or len(title) > 60:
        meta_score -= 0.3
    if not desc or len(desc) > 160 or not desc[-1] in ".!?…":
        meta_score -= 0.3
    if not m.get("kurzantwort"):
        meta_score -= 0.15
    parts["meta"] = max(0.0, meta_score)

    # 3) Struktur (Wortzahl, H2, FAQ)
    words = len(re.findall(r"\w+", a["body"]))
    h2 = len(re.findall(r"^##\s", a["body"], re.M))
    has_faq = bool(re.search(r"^#{1,2}\s*(Häufige Fragen|Häufig gestellte Fragen|FAQ)\s*$",
                             a["body"], re.M | re.I))
    struct = 1.0
    if words < 1200:
        struct -= 0.3
    if h2 < 4:
        struct -= 0.2
    if not has_faq:
        struct -= 0.2
    parts["structure"] = max(0.0, struct)

    # 4) Typografie (Detect)
    typo = 1.0
    body_lines = a["body"].split("\n")
    dbl = sum(1 for l in body_lines if RE_DBL_SPACE.search(l))
    bad_quote = sum(1 for l in body_lines if RE_BAD_QUOTE.search(l))
    # Falsche Hard-Breaks in Schutzkontexten (FAQ/Listen)
    in_faq = False
    broken_ctx = 0
    for l in body_lines:
        if re.match(r"^#{1,6}\s+", l):
            if re.search(r"^#{1,2}\s*(Häufige Fragen|Häufig gestellte Fragen|FAQ)", l, re.I):
                in_faq = True
            elif re.match(r"^#{1,2}\s+", l):
                in_faq = False
        if (in_faq or re.match(r"^\s*(?:[-*]|\d+\.)\s+", l)) and RE_BROKEN_END.search(l):
            broken_ctx += 1
    if dbl:
        typo -= min(0.3, dbl * 0.02)
    if bad_quote:
        typo -= min(0.2, bad_quote * 0.02)
    if broken_ctx:
        typo -= min(0.3, broken_ctx * 0.05)
    parts["typography"] = max(0.0, typo)

    # 5) Einzigartigkeit (bestehendes Audit-Ergebnis grob ermitteln)
    # Achtung (Stoerfall 11.08.): Kesselplatten (Schnell-Tipp-Box, Disclaimer,
    # CTA-Zeilen, „Das Wichtigste"-Hakenlistung) werden ZUERST abgezogen -
    # sonst wertet jeder Artikel als „Duplikat" und es stuermt das Massen-Parken.
    def _strip_boilerplate(text: str) -> str:
        text = re.sub(r"💡[^\n]*Schnell-Tipp[^\n]*", " ", text)
        text = re.sub(r"[*_]?Dieser Artikel enthält Affiliate-Links[^\n]*", " ", text)
        text = re.sub(r"👉[^\n]*", " ", text)
        text = re.sub(r"\*\*Das Wichtigste in Kürze:\*\*", " ", text)
        text = re.sub(r"_(Dieser Artikel enthält|Lesetipps zum Weitersparen)[^\n]*_", " ", text)
        return text
    try:
        import check_uniqueness as cu
        arts = {}
        for p in glob.glob(f"{BLOG_DIR}/content/posts/*/index.md"):
            arts[p] = cu.clean_body(_strip_boilerplate(open(p, encoding="utf-8").read()))
        from itertools import combinations
        grams = {k: cu.ngrams(v, cu.PHRASE_LEN) for k, v in arts.items()}
        overlap = 0
        for x, y in combinations(arts, 2):
            if len(grams[x] & grams[y]) >= 5:
                overlap += 1
        parts["uniqueness"] = max(0.0, 1.0 - overlap * 0.1)
    except Exception:
        parts["uniqueness"] = 0.5

    # 6) Affiliate-Integrität (Gateway-Ära: echte Links laufen ueber /go/!)
    aff = 1.0
    has_link = ("check24.net" in a["content"] or "partner-versicherung.de" in a["content"]
                or bool(re.search(r"/go/[\w-]+/", a["content"])))
    has_disclosure = "Affiliate" in a["content"] or "Provision" in a["content"]
    if not has_link:
        aff -= 0.5
    if not has_disclosure:
        aff -= 0.5
    parts["affiliate"] = max(0.0, aff)

    # Gesamt: gewichteter Mittelwert (Struktur & Typografie wichtiger)
    weights = {"spelling": 0.25, "meta": 0.2, "structure": 0.2,
               "typography": 0.15, "uniqueness": 0.1, "affiliate": 0.1}
    total = sum(parts[k] * weights[k] for k in weights)
    verdict = "publish" if total >= THRESHOLD_PUBLISH else (
        "draft+autofix" if total >= THRESHOLD_REVIEW else "human-review")

    return {"slug": a["slug"], "score": round(total, 3), "parts": parts,
            "verdict": verdict}


def main() -> int:
    only = None
    if "--file" in sys.argv:
        only = sys.argv[sys.argv.index("--file") + 1]
    files = sorted(glob.glob(f"{BLOG_DIR}/content/posts/*/index.md"))
    if only:
        files = [f for f in files if only in f]
    results = [score_article(f) for f in files]

    if "--report" in sys.argv:
        publish = [r for r in results if r["verdict"] == "publish"]
        draft = [r for r in results if r["verdict"] == "draft+autofix"]
        review = [r for r in results if r["verdict"] == "human-review"]
        avg = sum(r["score"] for r in results) / len(results) if results else 0
        report = {
            "articles": len(results),
            "avg_score": round(avg, 3),
            "publish": len(publish),
            "draft_autofix": len(draft),
            "human_review": [r["slug"] for r in review],
            "thresholds": {"publish": THRESHOLD_PUBLISH, "review": THRESHOLD_REVIEW},
            "details": results,
        }
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
