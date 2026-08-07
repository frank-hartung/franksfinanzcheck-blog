#!/usr/bin/env python3
"""
PROFI-TEXT-QUALITÄTS-GATE für FranksFinanzcheck.

Prüft Artikel auf Profi-Text-Niveau – die Kriterien, die einen
Blog-Artikel von KI-Brei unterscheiden:

  ✅ Wortanzahl      ≥ 400 Wörter (Profi-Artikel sind substanziell)
  ✅ Struktur        ≥ 4 H2-Abschnitte (klare Gliederung)
  ✅ FAQ-Bereich     ≥ 2 Fragen (Featured-Snippets + Nutzerwert)
  ✅ KEINE KI-Floskeln (Blacklist: "In der heutigen…", "Es ist wichtig…")
  ✅ Aktive Sprache  Anteil Passiv-/Füllformulierungen klein
  ✅ Lesbarkeit      Ø Satzlänge ≤ 22 Wörter (verständlich)
  ✅ Keywords        Haupt-Keyword im Text enthalten
  ✅ Beispiele       Mindestens 1 Liste ODER Tabelle (Mehrwert)
  ✅ Rechtschreibung Stichprobe: Sätze beginnen groß (deutsche Orthografie)

Liefert einen Score 0–100 pro Artikel und Exit-Code:
  Exit 0 = alle Artikel ≥ THRESHOLD (Profi-Niveau)
  Exit 1 = mindestens ein Artikel unter Schwelle (→ Regenerierung)

Nutzung:
    python3 scripts/profi_text_check.py                 # alle Artikel
    python3 scripts/profi_text_check.py --file X.md     # einzelner Artikel
    python3 scripts/profi_text_check.py --json          # maschinenlesbar
"""
import os
import re
import sys
import json

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
THRESHOLD = 80

# Typische KI-Floskeln – disqualifizieren einzelne Punkte (je -8)
KI_FLOSKELN = [
    "in der heutigen schnelllebigen welt",
    "in der heutigen zeit",
    "es ist wichtig zu beachten",
    "es ist wichtig, zu beachten",
    "zusammenfassend lässt sich sagen",
    "zusammenfassend kann man sagen",
    "des weiteren",
    "in diesem artikel werden wir",
    "in diesem artikel erfahren sie",
    "in diesem beitrag",
    "fazit: es bleibt",  # nur als Abschluss-Floskel, nicht "mein Fazit:
    "zusammenfassung:",
    "es gibt viele möglichkeiten",
    "es gibt zahlreiche",
    "wenn es darum geht",
    "in der regel gilt",
    "es lohnt sich,",
    "ein wichtiger aspekt",
    "von großer bedeutung",
    "nicht zu unterschätzen",
    "die welt der",
    "in einer welt, in der",
    "tauchen wir ein",
    "lassen sie uns",
    "sie fragen sich vielleicht",
    "genau das wollen wir",
    "heutzutage",
    "heutzutage ist",
    "in der modernen welt",
    "das a und o",
    "der schlüssel zum erfolg",
    "ein muss für jeden",
    "unverzichtbar für",
    "top-tipp",
    "geheimtipp",
]

# Passiv-/Füll-Formulierungen (je -3)
FUELLER = [
    "man kann", "man sollte", "man muss", "es gibt", "es ist",
    "wird gemacht", "kann gemacht werden", "sollte beachtet werden",
    "ist zu empfehlen", "kann empfohlen werden",
]


def parse_keywords(raw):
    """Parst Keywords (YAML-Liste oder Komma-String) sauber."""
    if not raw:
        return []
    raw = raw.strip()
    if raw.startswith("["):
        return [k.strip().strip('"\'') for k in raw[1:-1].split(",") if k.strip()]
    return [k.strip().strip('"\'') for k in raw.split(",") if k.strip()]


def load_article(path):
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    fm, body = (parts[1], parts[2]) if len(parts) == 3 else ("", content)
    if "draft: true" in fm:
        return None

    def get(key):
        m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
        return m.group(1).strip() if m else ""

    return {"path": path, "title": get("title"), "keywords": get("keywords"),
            "body": body, "date": get("date")}


def keyword_in_text(keyword, text):
    """Prüft, ob ein Keyword (mit Bindestrichen/Mehrwort) im Text vorkommt.
    Bindestriche werden wie Leerzeichen behandelt; zwischen den Wörtern
    sind bis zu 2 weitere Wörter erlaubt (Einschübe wie "(500–1.000 €)")."""
    kw_norm = re.sub(r"[\-–—]", " ", keyword).strip()
    kw_words = [w for w in re.findall(r"\w+", kw_norm) if w]
    if not kw_words:
        return True
    text_words = re.findall(r"\w+", text)
    # Fenster-Suche mit Toleranz
    for i in range(len(text_words) - len(kw_words) + 1):
        j = i
        matched = 0
        for kw in kw_words:
            # Suche das nächste Keyword-Wort innerhalb von 3 Positionen
            found = False
            for k in range(j, min(j + 4, len(text_words))):
                if text_words[k] == kw:
                    j = k + 1
                    matched += 1
                    found = True
                    break
            if not found:
                break
        if matched == len(kw_words):
            return True
    return False


def clean_body(body):
    """Entfernt Markdown-Syntax für Textanalyse."""
    text = re.sub(r"```.*?```", " ", body, flags=re.S)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"[#>*_`|~-]", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def score_article(a):
    """Berechnet den Profi-Text-Score (0-100)."""
    score = 100
    issues = []
    body = a["body"]
    text_orig = clean_body(body)          # Original (für Großschreibungs-Check)
    text = text_orig.lower()              # lowercase (für Floskeln/Keywords)

    # 1. Wortanzahl
    words = len(re.findall(r"\w+", text))
    if words < 300:
        score -= 30
        issues.append(f"nur {words} Wörter (Profi: 400+)")
    elif words < 400:
        score -= 15
        issues.append(f"nur {words} Wörter (Profi: 400+)")

    # 2. H2-Struktur
    h2 = len(re.findall(r"^##\s", body, re.M))
    if h2 < 4:
        score -= 15
        issues.append(f"nur {h2} H2-Abschnitte (Profi: 4+)")

    # 3. FAQ
    faq_q = len(re.findall(r"^###\s.*\?", body, re.M))
    if faq_q < 2:
        score -= 10
        issues.append(f"nur {faq_q} FAQ-Fragen (Profi: 2+)")

    # 4. KI-Floskeln
    floskeln = [f for f in KI_FLOSKELN if f in text]
    if floskeln:
        score -= min(30, len(floskeln) * 8)
        issues.append(f"KI-Floskeln: {', '.join(floskeln[:3])}")

    # 5. Füller/Passiv
    fueller = [f for f in FUELLER if f in text]
    if len(fueller) >= 4:
        score -= min(15, len(fueller) * 3)
        issues.append(f"viele Füllformulierungen ({len(fueller)})")

    # 6. Lesbarkeit (Ø Satzlänge)
    sentences = re.split(r"[.!?]\s", text)
    sentences = [s for s in sentences if len(s.split()) > 1]
    if sentences:
        avg = sum(len(s.split()) for s in sentences) / len(sentences)
        if avg > 24:
            score -= 10
            issues.append(f"Ø Satzlänge {avg:.0f} Wörter (Profi: ≤22)")
        elif avg > 20:
            score -= 4

    # 7. Haupt-Keyword im Text (robust: Bindestriche normalisiert,
    #    zwischen den Wörtern dürfen bis zu 2 Wörter stehen – z. B.
    #    "Notgroschen (500–1.000 €) aufbauen" oder "Stromfresser zu finden")
    kws = [k.lower() for k in parse_keywords(a["keywords"])]
    if kws and not keyword_in_text(kws[0], text):
        score -= 10
        issues.append(f"Haupt-Keyword „{kws[0]}“ fehlt im Text")

    # 8. Liste oder Tabelle
    if not re.search(r"(^|\n)[-*]\s", body, re.M) and "|" not in body:
        score -= 10
        issues.append("keine Liste/Tabelle (Mehrwert fehlt)")

    # 8b. Nackte URLs als Linktext ([https://x](https://x)) – SEO/UX-Problem
    bare_links = re.findall(r"\[https?://[^\]]+\]\(https?://[^)]*\)", body)
    if bare_links:
        score -= 10
        issues.append(f"{len(bare_links)} nackte URL(s) als Linktext (Ankertext verwenden!)")

    # 9. Rechtschreib-Stichprobe: Sätze beginnen mit Kleinbuchstaben?
    #    Nur ECHTE Fälle zählen: nach einem Wort-Endpunkt (. ! ?) direkt
    #    gefolgt von Leerzeichen + Kleinbuchstabe. Nummern-Listen ("1. strom")
    #    und Abkürzungen werden ausgeschlossen (Vorgänger kein Buchstabe).
    samples = re.findall(r"([a-zäöüßöA-ZÄÖÜ])[.!?]\s+([a-zäöüß])", text_orig)
    real_low = [b for a, b in samples if a.isalpha()]
    if len(real_low) > 3:
        score -= 8
        issues.append(f"{len(real_low)} Sätze beginnen mit Kleinbuchstaben")

    # 10. Persönliche/Erfahrungs-Elemente (E-E-A-T)
    eeat = any(w in text for w in ["ich habe", "ich habe es", "meine erfahrung",
                                   "ich selbst", "aus eigener erfahrung",
                                   "in der praxis", "ich empfehle"])
    if eeat:
        score += 5  # Bonus

    return max(0, min(100, score)), issues


def main():
    import datetime
    today = datetime.date.today().isoformat()
    new_only = "--new-only" in sys.argv
    files = []
    if "--file" in sys.argv:
        files = [sys.argv[sys.argv.index("--file") + 1]]
    else:
        files = [os.path.join(POSTS_DIR, f) for f in sorted(os.listdir(POSTS_DIR))
                 if f.endswith(".md")]
    as_json = "--json" in sys.argv

    results = []
    for path in files:
        a = load_article(path)
        if not a:
            continue
        # --new-only: nur Artikel, die heute (oder später) publiziert wurden
        if new_only and not a["date"].startswith(today):
            continue
        score, issues = score_article(a)
        results.append({"file": os.path.basename(path), "title": a["title"],
                        "score": score, "issues": issues,
                        "ok": score >= THRESHOLD})

    below = [r for r in results if not r["ok"]]
    avg = sum(r["score"] for r in results) / len(results) if results else 0

    if as_json:
        print(json.dumps({"articles": len(results), "avg_score": round(avg, 1),
                          "threshold": THRESHOLD, "below": below},
                         ensure_ascii=False, indent=2))
    else:
        print(f"Profi-Text-Gate: {len(results)} Artikel | Ø Score {avg:.0f}/100 "
              f"(Schwelle {THRESHOLD})")
        for r in sorted(results, key=lambda x: x["score"]):
            status = "✅" if r["ok"] else "❌"
            print(f"  {status} [{r['score']:3d}] {r['title'][:50]}")
            for i in r["issues"]:
                print(f"       • {i}")

    sys.exit(1 if below else 0)


if __name__ == "__main__":
    main()
