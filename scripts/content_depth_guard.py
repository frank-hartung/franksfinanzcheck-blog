#!/usr/bin/env python3
# ============================================================
#  CONTENT-DEPTH-GUARD – Themenautorität statt Oberfläche
#  (14.08.2026, Frank: "Content sollte in die Tiefe gehen und nicht nur
#  die offensichtliche Frage, sondern auch die Folgefragen beantworten
#  und ebenso Sonderfälle und Ausnahmen behandeln.")
#
#  GRUNDLAGE (recherchiert 14.08.2026, siehe SEO-STANDARDS-2026.md):
#  "Topical Authority" ist 2026 der etablierte Fachbegriff dafür – Google
#  UND KI-Suchsysteme (AI Overviews/AI Mode) bewerten, ob eine Seite ein
#  Thema vollständig behandelt statt nur ein Keyword zu bedienen: Folge-
#  fragen beantworten, Teilaspekte über H2/H3 abdecken, Sonderfälle
#  benennen. Das ist zugleich die wichtigste Verteidigung gegen Googles
#  "Scaled Content Abuse"-Regel (verschärft seit dem März-2026-Core-
#  Update): das Risiko für eine KI-Content-Seite ist nicht die
#  KI-Erstellung selbst, sondern viele Seiten OHNE echten Mehrwert/Tiefe.
#
#  PRÜFUNGEN:
#    D1  FOLGEFRAGEN-TIEFE: < 4 FAQ-Einträge (### in "Häufige Fragen")
#        gilt als oberflächlich für ein YMYL-Finanzthema.
#    D2  SONDERFÄLLE/AUSNAHMEN: kein Signalwort (Ausnahme, Sonderfall,
#        Achtung, "was gilt, wenn", "es sei denn" …) im Artikeltext
#        gefunden → Artikel behandelt vermutlich nur den Normalfall.
#    D3  TEILASPEKT-BREITE: < 3 echte H2-Abschnitte (ohne FAQ/Fazit)
#        deuten auf Keyword- statt Themen-Abdeckung hin.
#
#  SELBSTHEILUNG (13.08.2026-Prinzip: nur mit echtem KI-Call, sonst
#  Report): fehlt D1 oder D2, wird über die bestehende Content-Engine-
#  Infrastruktur (generate_drafts.call_groq/call_gemini, SELBE
#  SYSTEM_PROMPT-Stimme wie neue Artikel) GENAU EIN zusätzlicher
#  FAQ-Eintrag erzeugt, der einen im Artikel noch nicht behandelten
#  Sonderfall/eine Ausnahme abdeckt, und sicher in den bestehenden
#  "Häufige Fragen"-Abschnitt eingefügt. Nach der Heilung läuft
#  check_length.py + g.profi_quality_ok() erneut – bricht die Heilung
#  irgendetwas (Länge, Qualitäts-Gate), wird die Datei automatisch
#  zurückgesetzt (kein Datenverlust, kein kaputter Artikel live).
#  Ohne API-Key: sauberer Report, kein Fehler (wie social_poster.py).
#
#  Aufruf:
#    python3 scripts/content_depth_guard.py             # prüfen + heilen
#    python3 scripts/content_depth_guard.py --dry-run   # nur prüfen
#    python3 scripts/content_depth_guard.py --json
# ============================================================

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
POSTS_DIR = ROOT / "content" / "posts"
REPORT = ROOT / "CONTENT-DEPTH-REPORT.md"

DRY_RUN = "--dry-run" in sys.argv
AS_JSON = "--json" in sys.argv

MIN_FAQ = 4
MIN_H2 = 3

EDGE_CASE_MARKERS = [
    "ausnahme", "sonderfall", "sonderfälle", "achtung:", "wichtig zu wissen",
    "was passiert, wenn", "was gilt, wenn", "es sei denn", "gilt nicht",
    "aber:", "einschränkung", "sonderregel", "nicht in jedem fall",
]

sys.path.insert(0, str(SCRIPTS))


def load_live_articles():
    arts = []
    for slug_dir in sorted(POSTS_DIR.iterdir()):
        index_md = slug_dir / "index.md"
        if not index_md.is_file():
            continue
        text = index_md.read_text(encoding="utf-8")
        if not text.startswith("---") or text.count("---") < 2:
            continue
        parts = text.split("---", 2)
        fm, body = parts[1], parts[2]
        if re.search(r"^draft:\s*true\s*$", fm, re.MULTILINE):
            continue
        title_m = re.search(r'^title:\s*"?(.+?)"?\s*$', fm, re.MULTILINE)
        arts.append({
            "slug": slug_dir.name, "path": index_md, "content": text,
            "fm": fm, "body": body, "title": title_m.group(1) if title_m else slug_dir.name,
        })
    return arts


def analyze(body: str) -> dict:
    faq_count = len(re.findall(r"^###\s+.+\?\s*$", body, re.MULTILINE))
    h2_headings = [h.strip() for h in re.findall(r"^##\s+(.+)$", body, re.MULTILINE)]
    substantive_h2 = [h for h in h2_headings if "häufige fragen" not in h.lower() and "fazit" not in h.lower()]
    low = body.lower()
    has_edge_case = any(marker in low for marker in EDGE_CASE_MARKERS)
    return {
        "faq_count": faq_count,
        "h2_count": len(substantive_h2),
        "has_edge_case": has_edge_case,
    }


def build_prompt(article: dict) -> str:
    return (
        f"Hier ist ein bestehender Ratgeber-Artikel mit dem Titel \"{article['title']}\".\n\n"
        f"AUSZUG (gekürzt):\n{article['body'][:2500]}\n\n"
        "AUFGABE: Formuliere GENAU EINE zusätzliche FAQ-Frage mit Antwort, die einen "
        "SONDERFALL oder eine AUSNAHME zu diesem Thema behandelt, der/die im obigen Text noch "
        "NICHT vorkommt (z. B. ein Grenzfall, eine Ausnahme von der Regel, eine besondere "
        "Personengruppe/Situation). Antworte NUR mit exakt diesem Format, sonst nichts:\n\n"
        "### <Frage>?\n<Antwort in 2-4 Sätzen, konkret und praxisnah>\n"
    )


def parse_ai_faq(raw: str):
    if not raw:
        return None
    m = re.search(r"^###\s+(.+\?)\s*\n(.+?)(?:\n###|\Z)", raw.strip(), re.MULTILINE | re.DOTALL)
    if not m:
        return None
    question, answer = m.group(1).strip(), m.group(2).strip()
    if len(question) < 8 or len(answer) < 20:
        return None
    return question, answer


def insert_faq(content: str, question: str, answer: str) -> str | None:
    """Fügt die neue Frage sicher ans Ende des 'Häufige Fragen'-Abschnitts
    ein (vor dem nächsten '## '-Abschnitt oder dem CTA-Trennstrich)."""
    m = re.search(r"^##\s+Häufige Fragen\s*$", content, re.MULTILINE)
    if not m:
        return None
    section_start = m.end()
    next_section = re.search(r"\n##\s+|\n---\s*\n", content[section_start:])
    insert_at = section_start + next_section.start() if next_section else len(content)
    new_block = f"\n\n### {question}\n{answer}\n"
    return content[:insert_at] + new_block + content[insert_at:]


def heal_article(article: dict) -> tuple[bool, str]:
    import generate_drafts as g
    provider_used = None
    raw = None
    for provider, fn in (("Groq", g.call_groq), ("Gemini", g.call_gemini)):
        try:
            raw = fn(build_prompt(article))
        except Exception:  # noqa: BLE001
            raw = None
        if raw:
            provider_used = provider
            break
    if not raw:
        return False, "kein API-Key/keine Antwort verfügbar"

    parsed = parse_ai_faq(raw)
    if not parsed:
        return False, "KI-Antwort hatte nicht das erwartete Format"
    question, answer = parsed

    new_content = insert_faq(article["content"], question, answer)
    if not new_content:
        return False, "kein 'Häufige Fragen'-Abschnitt gefunden, Einfügen nicht sicher möglich"

    original_content = article["content"]
    article["path"].write_text(new_content, encoding="utf-8")

    # Sicherheitsnetz: nach der Heilung müssen Länge + Profi-Qualitäts-Gate
    # weiterhin bestehen, sonst sofortiger Rollback (kein kaputter Artikel).
    ok, reason = verify_after_heal(article["path"])
    if not ok:
        article["path"].write_text(original_content, encoding="utf-8")
        return False, f"Heilung zurückgerollt ({reason})"

    return True, f"neue FAQ ergänzt (Provider: {provider_used}): „{question}“"


def verify_after_heal(path: Path) -> tuple[bool, str]:
    import generate_drafts as g
    text = path.read_text(encoding="utf-8")
    body = text.split("---", 2)[2] if text.count("---") >= 2 else text
    word_count = len(re.findall(r"\S+", body))
    if word_count > 1800:
        return False, f"Länge nach Heilung {word_count} Wörter (> 1800)"
    try:
        ok, problems = g.profi_quality_ok(body, [])
    except Exception:  # noqa: BLE001
        return True, ""  # Gate selbst nicht verfügbar -> nicht blockieren
    if not ok:
        return False, "; ".join(problems[:2])
    return True, ""


def main():
    articles = load_live_articles()
    findings = []
    healed = []

    for a in articles:
        analysis = analyze(a["body"])
        problems = []
        if analysis["faq_count"] < MIN_FAQ:
            problems.append(f"nur {analysis['faq_count']} FAQ-Einträge (< {MIN_FAQ})")
        if not analysis["has_edge_case"]:
            problems.append("keine erkennbare Sonderfall-/Ausnahme-Behandlung")
        if analysis["h2_count"] < MIN_H2:
            problems.append(f"nur {analysis['h2_count']} inhaltliche H2-Abschnitte (< {MIN_H2})")

        if not problems:
            continue

        heal_result = None
        if not DRY_RUN and (analysis["faq_count"] < MIN_FAQ or not analysis["has_edge_case"]):
            try:
                ok, detail = heal_article(a)
            except Exception as exc:  # noqa: BLE001
                # Sicherheitsnetz: ein unerwarteter Fehler (z. B. fehlende
                # Abhängigkeit, API-Ausfall) darf NIE den ganzen Lauf/Report
                # verhindern (14.08.2026, im Live-Test gefunden: ein
                # ungefangener ModuleNotFoundError ließ den Report für ALLE
                # Artikel ausfallen, nicht nur für den betroffenen).
                ok, detail = False, f"unerwarteter Fehler: {exc}"
            heal_result = detail
            if ok:
                healed.append(a["slug"])
                # nach Heilung neu analysieren für den Report
                a["content"] = a["path"].read_text(encoding="utf-8")
                a["body"] = a["content"].split("---", 2)[2]
                analysis = analyze(a["body"])
                problems = []
                if analysis["faq_count"] < MIN_FAQ:
                    problems.append(f"weiterhin nur {analysis['faq_count']} FAQ-Einträge")
                if not analysis["has_edge_case"]:
                    problems.append("weiterhin keine Sonderfall-Behandlung erkennbar")
                if analysis["h2_count"] < MIN_H2:
                    problems.append(f"nur {analysis['h2_count']} inhaltliche H2-Abschnitte (< {MIN_H2}, nicht automatisch heilbar)")

        findings.append({
            "slug": a["slug"], "title": a["title"], "analysis": analysis,
            "problems": problems, "heal_attempt": heal_result,
        })

    if AS_JSON:
        print(json.dumps({"checked": len(articles), "findings": findings, "healed": healed},
                          ensure_ascii=False, indent=2))
        return 1 if any(f["problems"] for f in findings) else 0

    lines = [
        "# 🧠 CONTENT-DEPTH-REPORT (content_depth_guard.py)",
        "",
        f"**Geprüfte Live-Artikel:** {len(articles)} · **Automatisch geheilt:** {len(healed)} "
        f"({', '.join(healed) if healed else '–'})",
        "",
    ]
    remaining = [f for f in findings if f["problems"]]
    if not remaining:
        lines.append("🎉 Alle Artikel erfüllen die Tiefe-Kriterien (Folgefragen, Sonderfälle, Themenbreite) "
                      "– oder wurden automatisch nachgebessert.")
    else:
        for f in remaining:
            lines.append(f"### {f['slug']}")
            lines.append(f"„{f['title']}“")
            for p in f["problems"]:
                lines.append(f"- ⚠️ {p}")
            if f["heal_attempt"]:
                lines.append(f"- ℹ️ Heilungsversuch: {f['heal_attempt']}")
            lines.append("")
        lines.append(
            "---\n_H2-Breite (Themenabdeckung) ist nicht automatisch heilbar – eine neue Sektion braucht "
            "redaktionelle Einordnung, wo sie inhaltlich sinnvoll hinpasst. FAQ-Tiefe und Sonderfälle werden "
            "per KI automatisch ergänzt (Provider: Groq/Gemini, dieselbe Stimme wie neue Artikel), inklusive "
            "automatischem Rollback, falls die Ergänzung Länge oder Qualitäts-Gate verletzt._"
        )

    report_text = "\n".join(lines)
    print(report_text)
    REPORT.write_text(report_text + "\n", encoding="utf-8")
    return 1 if remaining else 0


if __name__ == "__main__":
    sys.exit(main())
