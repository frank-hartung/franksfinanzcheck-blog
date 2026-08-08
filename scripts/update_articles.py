#!/usr/bin/env python3
"""
VOLLAUTOMATISCHE ARTIKEL-UPDATE-ROUTINE (Quartalsweise, Profi-Niveau)

Aktualisiert alle 3 Monate die wichtigsten Artikel (neue Zahlen, aktuelle
Formulierungen, "Stand:"-Angaben) – als Frische-Signal an Google.

WIE ES FUNKTIONIERT:
  1. PRIORISIERUNG (Top-Artikel):
     score = SEO-Qualität (Titel/Desc-Längen) 
           + Alter seit Publikation (je älter, desto eher)
           + Interne-Links-Autorität (wie oft wird der Artikel verlinkt)
           + Tarif-Themen-Bonus (Strom/Gas/DSL/Versicherung = hohe Frische-Relevanz)
  2. ROTATION: Artikel, die im letzten Quartal schon aktualisiert wurden,
     werden übersprungen (Tracking in .article_updates.json) → über die
     Zeit kommt jeder Artikel dran.
  3. KI-ÜBERARBEITUNG (Gemini/Groq):
     - Einleitung & Formulierungen auffrischen
     - "Stand: <Monat Jahr>"-Angabe aktualisieren
     - Veraltete Preiszahlen durch aktuelle, plausible Spannen ersetzen
       (mit "ca." – keine erfundenen Fakten)
     - Struktur, Überschriften, FAQ-Schema, Affiliate-Links BLEIBEN erhalten
  4. VERIFIKATION: Frontmatter intakt, Affiliate-Links vorhanden, keine
     kaputten Markdown-Blöcke → sonst Update verwerfen.
  5. lastmod im Frontmatter setzen → Hugo rendert article:modified_time
     + sitemap-lastmod (Frische-Signal für Google).

Nutzung:
    python3 scripts/update_articles.py --dry-run      # Top-10 anzeigen
    python3 scripts/update_articles.py --apply        # Top-10 aktualisieren
    python3 scripts/update_articles.py --apply --max 3
"""
import os
import re
import sys
import json
import datetime
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import list_post_paths
TRACKING_FILE = os.path.join(BLOG_DIR, ".article_updates.json")
REPORT_FILE = os.path.join(BLOG_DIR, "ARTIKEL-UPDATE-REPORT.md")
CACHE_FILE = os.path.join(BLOG_DIR, ".update_cache.json")

TODAY = datetime.date.today()
QUARTER = f"{TODAY.year}-Q{(TODAY.month - 1) // 3 + 1}"

# Themen mit hoher Frische-Relevanz (Tarife/Preise ändern sich)
FRESH_TOPICS = [
    "strom", "gas", "dsl", "internet", "handy", "tarif", "versicherung",
    "kfz", "mietwagen", "tagesgeld", "kredit", "girokonto", "kreditkarte",
    "flug", "reise", "urlaub", "wlan", "waermepumpe", "heizung",
]

# Keywords für "Stand:"-Formulierungen im Text
STAND_PATTERNS = [
    r"[Ss]tand:?\s*(?:Januar|Februar|März|April|Mai|Juni|Juli|August|September|Oktober|November|Dezember)?\s*\d{4}",
    r"[Ss]tand:?\s*(?:0?[1-9]|1[0-2])/\d{4}",
    r"\(Stand [A-Za-zäöü]+ \d{4}\)",
    r"Stand:?\s+[A-Za-zäöü]+\s+\d{4}",
]


def load_articles():
    """Lädt alle Artikel mit Frontmatter + Body + Metadaten."""
    arts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm_raw, body = parts[1], parts[2]
        if "draft: true" in fm_raw:
            continue

        def get(key):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm_raw, re.M)
            return m.group(1).strip() if m else ""

        arts.append({
            "file": fn,
            "slug": fn[:-3],
            "title": get("title"),
            "description": get("description"),
            "date": get("date"),
            "lastmod": get("lastmod"),
            "path": path,
            "content": content,
            "fm": fm_raw,
            "body": body,
        })
    return arts


def count_internal_links(pages):
    """Zählt, wie oft jeder Artikel von anderen verlinkt wird (Autorität)."""
    links = {a["slug"]: 0 for a in pages}
    for a in pages:
        for other in pages:
            if other["slug"] != a["slug"]:
                if a["slug"].replace("-", "") in other["body"].replace("-", ""):
                    # Nur echte Links zählen
                    if f"/posts/{a['slug']}/" in other["body"] or f"({a['slug']}" in other["body"]:
                        links[a["slug"]] += 1
    return links


def meta_quality(a):
    """SEO-Qualität aus Titel/Desc-Längen (0-100)."""
    score = 100
    tl = len(a["title"])
    dl = len(a["description"])
    if not (30 <= tl <= 60):
        score -= 20
    if not (70 <= dl <= 160):
        score -= 20
    if not a["lastmod"]:
        score -= 5  # nie aktualisiert → Bonus-Interesse
    return max(0, score)


def fresh_bonus(a):
    """Bonus, wenn das Thema preis-/tarifabhängig ist."""
    text = (a["title"] + " " + a["description"]).lower()
    return 25 if any(k in text for k in FRESH_TOPICS) else 0


def priority_score(a, links, tracking):
    """Gesamtscore für die Top-Auswahl."""
    # Alter in Tagen seit Publikation
    try:
        pub = datetime.date.fromisoformat(a["date"][:10])
        age_days = (TODAY - pub).days
    except Exception:
        age_days = 0
    age_bonus = min(age_days // 30, 30)  # bis 30 Punkte für Alter

    # Rotation: zuletzt aktualisiert in den letzten ~100 Tagen → Skip-Gewicht
    last_update = tracking.get(a["slug"])
    rot_penalty = 0
    if last_update:
        try:
            lu = datetime.date.fromisoformat(last_update[:10])
            days_since = (TODAY - lu).days
            if days_since < 100:
                rot_penalty = 1000  # hart ausschließen (gerade erst aktualisiert)
            else:
                rot_penalty = max(0, 40 - days_since // 10)
        except Exception:
            pass

    score = meta_quality(a) + age_bonus + fresh_bonus(a) + min(links.get(a["slug"], 0) * 5, 20)
    return score - rot_penalty


def ai_update_article(a):
    """Lässt die KI den Artikel auffrischen. Liefert neuen Body oder None."""
    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not (gemini_key or groq_key):
        print("  ⚠️ Keine API-Keys – Überspringe KI-Update.")
        return None

    month_names = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                   "Juli", "August", "September", "Oktober", "November", "Dezember"]
    stand = f"Stand: {month_names[TODAY.month - 1]} {TODAY.year}"

    prompt = f"""Du bist ein deutscher Finanz-Redakteur. Frische den folgenden Blog-Artikel für einen
Tarif-Vergleichs-Blog auf (Frische-Signal für Google). Der heutige Stand ist {stand}.

REGELN – STRENG EINHALTEN:
1. Überarbeite die Einleitung und 2-3 Absätze sprachlich so, dass sie aktuell wirken.
2. Füge die Angabe "{stand}" an passender Stelle ein (z. B. in der Einleitung oder bei Preisen).
3. Ersetze veraltete konkrete Preiszahlen durch aktuelle, PLAUSIBLE Spannen mit "ca." 
   (z. B. "ca. 30–40 € pro Monat"). ERFINDE KEINE konkreten Anbieter-Fakten – verwende
   vorsichtige Formulierungen wie "in der Regel", "je nach Anbieter".
4. Behalte ALLE Überschriften (##, ###) exakt bei – ändere ihre Formulierung nur minimal.
5. Behalte alle FAQ-Fragen (### ... mit ?) bei, frisch nur die Antworten leicht auf.
6. Behalte ALLE Links exakt bei – insbesondere Affiliate-Links zu a.check24.net und
   a.partner-versicherung.de. Lösche KEINEN Link und ändere keine URL.
7. Behalte Listen, Tabellen und deren Struktur bei.
8. Mindestlänge: der neue Text muss mindestens 85% der ursprünglichen Länge haben.
9. Kein Markdown-Code, keine Anführungszeichen um den Text, keine Einleitung wie "Hier ist...".

ARTIKEL-TITEL: {a['title']}
KEYWORDS: {a['description'][:100]}

ARTIKEL-TEXT:
{a['body']}

Liefere NUR den vollständigen aktualisierten Artikeltext (Markdown), ohne Frontmatter."""

    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

    # 1) Gemini versuchen
    if gemini_key:
        try:
            body = {"contents": [{"parts": [{"text": prompt}]}]}
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-3-flash-preview:generateContent?key=" + gemini_key,
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
            text = resp["candidates"][0]["content"]["parts"][0]["text"].strip()
            if text:
                return text
        except Exception as e:
            print(f"  ⚠️ Gemini-Fehler: {e}")

    # 2) Groq-Fallback
    if groq_key:
        try:
            body = {"model": "llama-3.3-70b-versatile",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4000}
            req = urllib.request.Request(
                "https://api.groq.com/openai/v1/chat/completions",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json",
                         "Authorization": f"Bearer {groq_key}", "User-Agent": ua})
            resp = json.loads(urllib.request.urlopen(req, timeout=120).read())
            text = resp["choices"][0]["message"]["content"].strip()
            if text:
                return text
        except Exception as e:
            print(f"  ⚠️ Groq-Fehler: {e}")
    return None


def verify_update(a, new_body):
    """Prüft, ob das KI-Update sicher ist (Links, Struktur, Länge)."""
    problems = []
    old_links = set(re.findall(r"https?://[^\s)\"']+", a["body"]))
    new_links = set(re.findall(r"https?://[^\s)\"']+", new_body))

    # Affiliate-Links müssen erhalten bleiben
    old_aff = {l for l in old_links if "check24" in l or "partner-versicherung" in l}
    new_aff = {l for l in new_links if "check24" in l or "partner-versicherung" in l}
    missing = old_aff - new_aff
    if missing:
        problems.append(f"Affiliate-Links verloren: {len(missing)}")

    # Überschriften-Struktur
    old_h = re.findall(r"^#{1,3} ", a["body"], re.M)
    new_h = re.findall(r"^#{1,3} ", new_body, re.M)
    if abs(len(old_h) - len(new_h)) > 2:
        problems.append(f"Überschriften-Anzahl stark verändert ({len(old_h)}→{len(new_h)})")

    # Länge
    if len(new_body) < len(a["body"]) * 0.8:
        problems.append(f"Text zu stark gekürzt ({len(new_body)}/{len(a['body'])} Zeichen)")

    # Code-Blöcke nicht zerstört
    if a["body"].count("```") % 2 == 0 and new_body.count("```") % 2 != 0:
        problems.append("Code-Blöcke kaputt")

    return problems


def set_lastmod(a, new_body):
    """Setzt lastmod + schreibt den neuen Body ins Frontmatter."""
    content = a["content"]
    today_iso = TODAY.isoformat()

    # lastmod setzen (oder ersetzen)
    if re.search(r"^lastmod:.*$", a["fm"], re.M):
        content = re.sub(r"^lastmod:.*$", f"lastmod: {today_iso}", content, count=1, flags=re.M)
    else:
        # Nach date: einfügen
        content = re.sub(r"^(date:.*)$", rf"\1\nlastmod: {today_iso}", content, count=1, flags=re.M)

    # Body ersetzen (nach dem zweiten ---)
    parts = content.split("---", 2)
    if len(parts) == 3:
        content = parts[0] + "---" + parts[1] + "---" + new_body

    open(a["path"], "w", encoding="utf-8").write(content)
    return today_iso


def main():
    dry = "--dry-run" in sys.argv
    apply = "--apply" in sys.argv
    max_n = 10
    if "--max" in sys.argv:
        try:
            max_n = int(sys.argv[sys.argv.index("--max") + 1])
        except (ValueError, IndexError):
            pass

    pages = load_articles()
    links = count_internal_links(pages)

    # Tracking laden
    tracking = {}
    if os.path.exists(TRACKING_FILE):
        try:
            tracking = json.load(open(TRACKING_FILE, encoding="utf-8"))
        except Exception:
            tracking = {}

    # Priorisieren
    scored = []
    for a in pages:
        s = priority_score(a, links, tracking)
        scored.append((s, a))
    scored.sort(key=lambda x: -x[0])

    selected = scored[:max_n]
    print(f"Artikel-Update-Routine ({QUARTER})")
    print(f"Priorisiert: {len(pages)} Artikel → Top {len(selected)} ausgewählt\n")
    print("Rangliste:")
    for i, (s, a) in enumerate(selected, 1):
        last = tracking.get(a["slug"], "nie")
        print(f"  {i:2d}. [{s:3d}] {a['title'][:55]:55s} (zuletzt: {last[:10]})")

    if dry:
        print(f"\nDRY-RUN: {len(selected)} Artikel würden aktualisiert. "
              f"(--apply zum Ausführen)")
        sys.exit(0)

    # KI-Update pro Artikel
    updated = []
    failed = []
    for i, (s, a) in enumerate(selected, 1):
        print(f"\n[{i}/{len(selected)}] {a['title'][:50]}…")
        new_body = ai_update_article(a)
        if not new_body:
            failed.append(a["slug"])
            continue
        problems = verify_update(a, new_body)
        if problems:
            print(f"  ❌ Verworfen: {'; '.join(problems)}")
            failed.append(a["slug"])
            continue
        lastmod = set_lastmod(a, new_body)
        tracking[a["slug"]] = TODAY.isoformat()
        updated.append({"slug": a["slug"], "title": a["title"], "date": lastmod})
        print(f"  ✅ Aktualisiert (lastmod {lastmod})")

    # Tracking + Report speichern
    json.dump(tracking, open(TRACKING_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

    month_names = ["Januar", "Februar", "März", "April", "Mai", "Juni",
                   "Juli", "August", "September", "Oktober", "November", "Dezember"]
    lines = [
        f"# 🔄 Artikel-Update-Report – {TODAY.strftime('%d.%m.%Y')} ({QUARTER})",
        "",
        f"> **Vollautomatisch** – {len(updated)} Artikel aktualisiert, {len(failed)} fehlgeschlagen.",
        "",
        "## Aktualisierte Artikel",
        "",
        "| # | Artikel | Datum |",
        "|---|---|---|",
    ]
    for i, u in enumerate(updated, 1):
        lines.append(f"| {i} | {u['title']} | {u['date']} |")
    if failed:
        lines += ["", "## Fehlgeschlagen", ""]
        for f in failed:
            lines.append(f"- {f}")
    lines += ["", "---", f"*Automatisch erzeugt am {TODAY} vom Artikel-Update-Bot.*"]
    open(REPORT_FILE, "w", encoding="utf-8").write("\n".join(lines))

    print(f"\nFertig: {len(updated)} Artikel aktualisiert, {len(failed)} fehlgeschlagen.")
    print(f"Report: {REPORT_FILE}")


if __name__ == "__main__":
    main()
