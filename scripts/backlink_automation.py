#!/usr/bin/env python3
"""
Backlink-Automation für FranksFinanzcheck – SCOUT-MODUS.

Was dieses Skript automatisiert (und was nicht):
  ✅ Automatisch: Opportunities prüfen (Erreichbarkeit), priorisieren,
     personalisierte Outreach-Texte generieren (mit passendem eigenen
     Artikel als 'Hingucker'), Report als Markdown erzeugen, Status
     in data/backlink_prospects.yaml aktualisieren.
  ❌ NICHT automatisch: Das Absenden/Einreichen – das bleibt bewusst
     manuell (Qualitäts-Gate). Automatisches Posten wäre Spam und
     riskiert Google-Abstrafungen. Der Report gibt dir Copy-Paste-Texte.

Nutzung:
    python3 scripts/backlink_automation.py            # Scout + Report
    python3 scripts/backlink_automation.py --no-net   # ohne HTTP-Checks

Workflow: backlink-weekly.yml (Mo 08:00) → committet Report + Status.
"""
import os
import sys
import re
import datetime
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_FILE = os.path.join(BLOG_DIR, "data", "backlink_prospects.yaml")
REPORT_FILE = os.path.join(BLOG_DIR, "BACKLINK-REPORT.md")
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import list_post_paths, slug_of

try:
    import yaml
except ImportError:
    sys.exit("FEHLER: pyyaml nicht installiert – pip install pyyaml")


def http_check(url, timeout=8):
    """Prüft Erreichbarkeit einer URL (HEAD, Fallback GET)."""
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (Backlink-Scout)"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except Exception:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (Backlink-Scout)"})
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.status
        except Exception:
            return None


def load_articles():
    """Lädt Artikel-Titel + Themen für die Outreach-Personalisierung."""
    arts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        title = (m.group(1) if m else slug_of(path)).strip()
        m2 = re.search(r'^categories:\s*\[(.*?)\]', content, re.M)
        cats = [c.strip().strip('"\'') for c in (m2.group(1).split(",") if m2 else [])]
        arts.append({"title": title, "slug": fn[:-3], "categories": cats})
    return arts


def pick_best_article(articles, topic_keywords):
    """Wählt den passendsten eigenen Artikel für den Outreach-Text."""
    best, best_score = None, 0
    for a in articles:
        score = 0
        text = (a["title"] + " " + " ".join(a["categories"])).lower()
        for kw in topic_keywords:
            if kw.lower() in text:
                score += 2
        if score > best_score:
            best, best_score = a, score
    return best or (articles[0] if articles else None)


def build_outreach(prospect, articles):
    """Generiert einen personalisierten Outreach-Text."""
    topic = prospect.get("topic", "Finanzen")
    topic_kws = [t.strip() for t in topic.split(",")][:3]
    article = pick_best_article(articles, topic_kws)
    art_url = f"https://frank-hartung.github.io/franksfinanzcheck-blog/posts/{article['slug']}/" if article else ""
    art_title = article["title"] if article else "unseren Ratgeber"
    name = prospect.get("name", "die Plattform")
    return (
        f"**Betreff:** Gastbeitrag/Vorschlag: „{art_title}“\n\n"
        f"Hallo {name}-Team,\n\n"
        f"ich betreibe den Blog *FranksFinanzcheck* – unabhängige, praxisnahe "
        f"Ratgeber zu Geld sparen, Versicherungen und Tarifvergleichen.\n\n"
        f"Ich würde mich freuen, {name} mit einem Beitrag zu unterstützen. "
        f"Als Beispiel: **{art_title}** – {prospect.get('approach', '')[:120]}\n\n"
        f"Der Artikel ist faktenbasiert, mit konkreten Zahlen und ohne Werbeversprechen. "
        f"Gerne liefere ich auch einen exklusiven Beitrag nur für euch.\n\n"
        f"Mein Blog: {art_url}\n\n"
        f"Beste Grüße\nFrank Hartung\nFranksFinanzcheck\n"
        f"https://frank-hartung.github.io/franksfinanzcheck-blog/"
    )


def main():
    no_net = "--no-net" in sys.argv
    data = yaml.safe_load(open(DATA_FILE, encoding="utf-8"))
    prospects = data.get("prospects", [])
    articles = load_articles()

    print(f"Backlink-Scout: {len(prospects)} Opportunities, {len(articles)} Artikel\n")

    today = datetime.date.today().isoformat()
    lines = [
        f"# 🔗 Backlink-Report – {today}",
        "",
        "> **Hinweis:** Automatisches Einreichen wäre Spam und riskiert Google-Strafen.",
        "> Dieser Report liefert dir priorisierte Opportunities + Copy-Paste-Outreach-Texte.",
        "> Das Absenden bleibt dein Qualitäts-Gate (10–20 Min/Woche).",
        "",
        "## Priorisierung (Passung × Erreichbarkeit)",
        "",
        "| # | Quelle | Typ | Passung | Status | Erreichbar |",
        "|---|--------|-----|---------|--------|------------|",
    ]

    checked = []
    for i, p in enumerate(prospects, 1):
        status = p.get("status", "neu")
        reachable = "–"
        if not no_net and p.get("url") and status in ("neu", "vorbereitet"):
            code = http_check(p["url"])
            reachable = f"HTTP {code}" if code else "⚠️ nicht erreichbar"
            p["last_checked"] = today
        fit = p.get("fit", 3)
        lines.append(
            f"| {i} | [{p.get('name','?')}]({p.get('url','')}) | {p.get('type','?')} "
            f"| {'⭐'*fit}{'☆'*(5-fit)} | {status} | {reachable} |"
        )
        checked.append((fit, p))

    lines += ["", "## Outreach-Texte (Copy-Paste)", ""]
    for i, p in enumerate(prospects, 1):
        if p.get("status") in ("gewonnen", "abgelehnt"):
            continue
        lines.append(f"### {i}. {p.get('name','?')} ({p.get('type','?')})")
        lines.append(f"**Vorgehen:** {p.get('approach','')}")
        lines.append("")
        lines.append(build_outreach(p, articles))
        lines.append("")

    with open(REPORT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    # Status-Tracking zurückschreiben
    yaml.safe_dump(data, open(DATA_FILE, "w", encoding="utf-8"), allow_unicode=True, sort_keys=False)

    print(f"Report erzeugt: {REPORT_FILE}")
    gewonnen = sum(1 for p in prospects if p.get("status") == "gewonnen")
    print(f"Status: {gewonnen} gewonnen, {len(prospects) - gewonnen} offen")


if __name__ == "__main__":
    main()
