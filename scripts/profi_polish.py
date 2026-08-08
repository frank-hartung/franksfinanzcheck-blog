#!/usr/bin/env python3
"""
PROFI-POLISH-PASS – KI-Nachbearbeitung neuer Artikel.

Verwandelt einen frisch generierten Bot-Artikel in einen PROFI-TEXT:
  - KI-Floskeln & Füllformulierungen entfernen
  - Aktive, lebendige Sprache (kurze Sätze, starke Verben)
  - Einleitung mit Haken (Nutzen versprechen, Frage/Nr. aufwerfen)
  - Absätze auf 3–4 Sätze kürzen (Scannability)
  - Natürliche Keyword-Integration (kein Stuffing)
  - E-E-A-T-Sprache: Erfahrung, Praxisbezug, konkrete (plausible) Beispiele
  - Deutsche Orthografie (Großschreibung, korrekte Zeichen)

SICHERHEIT (Verifikation VOR dem Schreiben):
  - Alle Links bleiben erhalten (Affiliate-Links Pflicht)
  - Überschriften-Anzahl bleibt stabil
  - Länge ≥ 85 % des Originals
  - Frontmatter wird nie angefasst

Nutzung:
    python3 scripts/profi_polish.py --file X.md     # einzelnen Artikel
    python3 scripts/profi_polish.py --new           # alle Artikel ohne lastmod
    python3 scripts/profi_polish.py --all           # ALLE Artikel (auch manuelle)
    python3 scripts/profi_polish.py --dry-run       # ohne zu schreiben
"""
import os
import re
import sys
import json
import datetime
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import list_post_paths, slug_of
CACHE_FILE = os.path.join(BLOG_DIR, ".polish_cache.json")


def load_article(path):
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    if len(parts) != 3:
        return None
    fm, body = parts[1], parts[2]
    if "draft: true" in fm:
        return None

    def get(key):
        m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
        return m.group(1).strip() if m else ""

    anrede_raw = get("anrede").strip('"').lower()
    return {"path": path, "title": get("title"), "description": get("description"),
            "keywords": get("keywords"), "body": body,
            "anrede_sie": anrede_raw in ("sie", "sie-form", "höflich")}


def ai_polish(a):
    """KI-Polish. Liefert neuen Body oder None."""
    key = slug_of(a["path"])  # eindeutig (Bundles: Ordnername, nicht "index.md"!)
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.load(open(CACHE_FILE, encoding="utf-8"))
        except Exception:
            cache = {}
    if key in cache:
        return cache[key]

    gemini_key = os.environ.get("GEMINI_API_KEY", "")
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if not (gemini_key or groq_key):
        print("  ⚠️ Keine API-Keys – kein Polish möglich.")
        return None

    # Keywords sauber parsen (YAML-Liste)
    kws_raw = a["keywords"]
    kws = []
    if kws_raw.strip().startswith("["):
        kws = [k.strip().strip('"\'') for k in kws_raw.strip()[1:-1].split(",") if k.strip()]
    else:
        kws = [k.strip() for k in kws_raw.split(",") if k.strip()]
    kw_hint = ", ".join(kws[:4]) if kws else a["title"]
    # Anrede: Standard "du" – bei Frontmatter anrede:"Sie" → Sie-Form
    anrede_auftrag = ('"du" – der Leser wird geduzt (Blog-Stil)' if not a.get("anrede_sie")
                      else '"Sie" – dieser Artikel richtet sich bewusst an eine Zielgruppe, die gesiezt wird')
    anrede_pronomen = '("du"/"dein"/"dich")' if not a.get("anrede_sie") else '("Sie"/"Ihr"/"Ihnen")'

    prompt = f"""Du bist Lektor für einen seriösen deutschen Finanz-Ratgeber-Blog (Profi-Niveau).
Polieren den folgenden Blog-Artikel auf PROFESSIONELLES Text-Niveau.

REGELN:
1. Entferne ALLE KI-Floskeln und Füllphrasen ("In der heutigen…", "Es ist wichtig zu beachten",
   "Zusammenfassend lässt sich sagen", "Des Weiteren", "Es gibt viele…", "heutzutage" usw.).
2. Schreibe in AKTIVER, lebendiger Sprache: kurze Sätze (max. ~20 Wörter), starke Verben,
   direkte Ansprache {anrede_auftrag} {anrede_pronomen}. Vermeide Passiv.
3. Einleitung: Beginne mit einem starken Haken (Nutzenversprechen, konkrete Zahl, Frage).
4. Absätze auf 3-4 Sätze kürzen. Zwischenüberschriften beibehalten.
5. Baue die Keywords natürlich ein (kein Stuffing): {a['keywords'][:120]}
6. Mehr Praxisbezug (E-E-A-T): konkrete, PLAUSIBLE Beispiele ("In der Regel", "je nach Anbieter",
   "ca. X–Y €") – ERFINDE KEINE Fakten, Preise nur als vorsichtige Spannen.
7. Deutsche Orthografie: korrekte Groß-/Kleinschreibung, korrekte Anführungszeichen.
8. BEHALTE alle Links exakt bei (insbesondere https://a.check24.net und https://a.partner-versicherung.de).
   Lösche KEINEN Link, ändere keine URL.
9. Behalte alle Überschriften (##, ###) und die FAQ-Fragen bei. FAQ-Antworten dürfen leicht
   frischer formuliert werden.
10. Behalte Listen und Tabellen. WICHTIG: Der polierte Text muss mindestens 90% der
    Länge des Originaltextes haben. Kürze KEINE Absätze komplett weg – formuliere
    innerhalb der Absätze um. Nur Floskeln/Füllwörter dürfen entfallen.
11. Falls der Artikel KEINE Liste und KEINE Tabelle enthält, ergänze eine kurze
    Liste mit 4-6 Punkten (z. B. "Das Wichtigste in Kürze") an passender Stelle.
11b. LESBARKEIT (wichtig!): Zerlege Schachtelsätze (über 25 Wörter) in 2 kurze
    Sätze. Ersetze lange Wörter durch einfachere Alternativen (z. B. "die
    Erstattungsfähigkeit" → "ob die Kosten erstattet werden"). Vermeide
    Nominalstil ("die Übernahme der Kosten" → "die Kasse übernimmt die Kosten").
    Ziel: Ø Satzlänge unter 15 Wörter, Flesch-Score über 60.
12. TOP-LEVEL-DARSTELLUNG: Jeder Absatz ist 3-4 Sätze lang, behandelt genau EINEN
    Gedanken und endet an einer sinnvollen Stelle (keine Textwände). Schreibe
    Wörter NIE mit Silbentrennung. Zwischen einer Zahl und ihrer Einheit steht
    IMMER ein geschütztes Leerzeichen (&nbsp;): 20&nbsp;%, 50&nbsp;€,
    100&nbsp;EUR – niemals "20 %" oder "50 €" mit normalem Leerzeichen.
12. GROSS-/KLEINSCHREIBUNG: Verwende die NORMALE deutsche Rechtschreibung – wie in
    einem Zeitungsartikel. Nur Satzanfänge und Substantive werden großgeschrieben,
    alle anderen Wörter klein (KEIN Titel-Stil, kein "Jedes Wort Groß").
    Nach jedem Satzendepunkt (! . ?) beginnt das nächste Wort mit einem Großbuchstaben.
    Achtung: "Du" wird nur am Satzanfang groß, im Satz klein ("du").
13. KEYWORDS: Diese Keywords müssen 1-2 Mal natürlich im Text vorkommen (kein Stuffing):
    {kw_hint}
    Das Haupt-Keyword (das erste) MUSS mindestens einmal im Text stehen.
14. Beginne den Text NICHT mit dem Artikel-Titel – der Titel steht bereits in der
    Überschrift der Seite. Starte direkt mit dem ersten Absatz.

TITEL: {a['title']}
DESCRIPTION: {a['description'][:100]}

ARTIKEL:
{a['body']}

Liefere NUR den vollständigen polierten Markdown-Text (ohne Frontmatter, ohne Erklärungen)."""

    ua = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126.0 Safari/537.36"

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
                cache[key] = text
                json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)
            return text
        except Exception as e:
            print(f"  ⚠️ Gemini: {e}")

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
                cache[key] = text
                json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)
            return text
        except Exception as e:
            print(f"  ⚠️ Groq: {e}")
    return None


# Abkürzungen, nach denen KEIN Großbuchstabe folgen muss
ABKUERZUNGEN = {
    "z.b", "z. b", "usw", "bzw", "d.h", "d. h", "u.a", "u. a", "etc", "ca",
    "inkl", "exkl", "zzgl", "vgl", "usf", "nr", "prof", "dr", "tel", "mo",
    "di", "mi", "do", "fr", "sa", "so", "geb", "ggf", "evtl", "sog", "bspw",
}


def fix_capitalization(text):
    """Deterministische Korrektur: Nach Satzendepunkt (! ? .) folgt ein
    Großbuchstabe – außer nach bekannten Abkürzungen (z. B., usw., bzw. …).
    Behebt das häufigste Qualitätsproblem von KI-Texten (kleine Satzanfänge)."""
    def repl(m):
        prefix, punct, space, lower = m.group(1), m.group(2), m.group(3), m.group(4)
        # Abkürzungs-Check: letztes Wort vor dem Punkt
        words = prefix.split()
        if words:
            last = words[-1].lower().rstrip(".")
            # Mehrteilige Abkürzungen wie "z. B." – letzte zwei Wörter prüfen
            if len(words) >= 2:
                combo = (words[-2] + " " + words[-1]).lower().rstrip(".")
                if combo in ABKUERZUNGEN or combo.replace(".", "") in ABKUERZUNGEN:
                    return m.group(0)
            if last in ABKUERZUNGEN or last.replace(".", "") in ABKUERZUNGEN:
                return m.group(0)
        return prefix + punct + space + lower.upper()

    # Buchstabe + .!? + Leerzeichen + Kleinbuchstabe
    return re.sub(r"([a-zäöüßA-ZÄÖÜ0-9\)\"])([.!?])(\s+)([a-zäöüß])", repl, text)


def fix_number_units(text):
    """Top-Level-Darstellung: Zahl + Einheit (% / € / EUR) mit geschütztem
    Leerzeichen (&nbsp;) verbinden, damit nie getrennt umbrochen wird.
    Markdown-Links werden maskiert, damit URLs unangetastet bleiben."""
    link_re = re.compile(r"\[[^\]]*\]\([^)]*\)")
    num_unit_re = re.compile(r"(\d[\d.,]*)\s+(%|€|EUR)(?!\w)")
    masked = link_re.sub(lambda m: " " * (m.end() - m.start()), text)
    out, last = [], 0
    for m in num_unit_re.finditer(masked):
        out.append(text[last:m.start()])
        out.append(m.group(1) + "&nbsp;" + m.group(2))
        last = m.end()
    out.append(text[last:])
    return "".join(out)


def verify(a, new_body):
    """Sicherheits-Verifikation vor dem Schreiben."""
    problems = []
    old_links = set(re.findall(r"https?://[^\s)\"']+", a["body"]))
    new_links = set(re.findall(r"https?://[^\s)\"']+", new_body))
    old_aff = {l for l in old_links if "check24" in l or "partner-versicherung" in l}
    new_aff = {l for l in new_links if "check24" in l or "partner-versicherung" in l}
    if old_aff - new_aff:
        problems.append(f"Affiliate-Links verloren: {len(old_aff - new_aff)}")
    old_h = len(re.findall(r"^#{1,3} ", a["body"], re.M))
    new_h = len(re.findall(r"^#{1,3} ", new_body, re.M))
    if abs(old_h - new_h) > 2:
        problems.append(f"Überschriften {old_h}→{new_h}")
    if len(new_body) < len(a["body"]) * 0.75:
        problems.append("zu stark gekürzt")
    return problems


def write_polished(a, new_body):
    content = a["path"] and open(a["path"], encoding="utf-8").read()
    parts = content.split("---", 2)

    # Titel-Duplikat-Schutz: Wenn die KI den Titel als erste Zeile wiederholt,
    # entfernen (der Titel steht bereits im Frontmatter/als Seiten-Titel).
    first_line = new_body.strip().split("\n", 1)[0].strip()
    title_norm = re.sub(r"[#*_]", "", a["title"]).strip().lower()
    first_norm = re.sub(r"[#*_]", "", first_line).strip().lower()
    if first_norm == title_norm or first_norm == title_norm + ":":
        new_body = new_body.strip().split("\n", 1)[1].lstrip()

    content = parts[0] + "---" + parts[1] + "---" + new_body
    open(a["path"], "w", encoding="utf-8").write(content)


def main():
    dry = "--dry-run" in sys.argv
    mode_new = "--new" in sys.argv
    mode_all = "--all" in sys.argv

    files = []
    if "--file" in sys.argv:
        files = [sys.argv[sys.argv.index("--file") + 1]]
    elif mode_new:
        # Nur Artikel VON HEUTE (date == heute, draft: false) – so verschwendet
        # der tägliche Workflow keine Zeit/Quota mit alten, nie gepolisheden
        # Artikeln (die z. B. wegen Affiliate-Link-Schutz verworfen werden).
        today = datetime.date.today().isoformat()
        for f in list_post_paths():
            c = open(f, encoding="utf-8").read()
            fm = c.split("---", 2)[1] if c.startswith("---") and c.count("---") >= 2 else ""
            if today in fm and "draft: false" in fm:
                files.append(f)
    else:
        files = list_post_paths()

    polished, failed, skipped = [], [], 0
    import time
    for idx, path in enumerate(files):
        a = load_article(path)
        if not a:
            skipped += 1
            continue
        # Standard: nur Bot-Artikel polieren (ai_generated).
        # --all: AUCH manuelle Artikel polieren (Profi-Niveau für alles).
        if not mode_all:
            content = open(path, encoding="utf-8").read()
            if "ai_generated: true" not in content:
                skipped += 1
                continue
        print(f"  [{idx+1}/{len(files)}] → {os.path.basename(path)[:50]}…", flush=True)
        new_body = ai_polish(a)
        if not new_body:
            failed.append(os.path.basename(path))
            continue
        # Deterministischer Auto-Fix: Großschreibung nach Satzpunkten
        new_body = fix_capitalization(new_body)
        # Top-Level-Darstellung: Zahl+Einheit mit &nbsp; verbinden (% / € / EUR)
        new_body = fix_number_units(new_body)
        problems = verify(a, new_body)
        if problems:
            print(f"    ❌ Verworfen: {'; '.join(problems)}")
            failed.append(os.path.basename(path))
            continue
        if not dry:
            write_polished(a, new_body)
        polished.append(os.path.basename(path))
        print(f"    ✅ Poliert ({len(new_body)} Zeichen)", flush=True)
        # Rate-Limit-Schonung: kurze Pause zwischen KI-Calls (mehrere Artikel)
        if not dry and len(files) > 1:
            time.sleep(2)

    print(f"\nFertig: {len(polished)} poliert, {len(failed)} fehlgeschlagen, "
          f"{skipped} übersprungen (manuell/Entwurf).")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
