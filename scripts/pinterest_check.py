#!/usr/bin/env python3
"""PINTEREST-CHECK – Profi-Audit mit Selbstheilung + Sabotage-Schutz
für FranksFinanzcheck (Affiliate-Blog, Pinterest-Marketing).

Prüft ALLE Pinterest-Signale, die Pinterest beim „Pin it“-Button und
beim Rich-Pin-Scraping bewertet – und heilt gefundene Fehler
automatisch (deterministisch, mit Sabotage-Schutz).

  P1  ROBOTS.TXT        existiert + erlaubt Pinterest-Crawler
  P2  DOMAIN-VERIFY     p:domain_verify-Meta vorhanden
  P3  PIN-BUTTON        jeder echte Artikel hat den Pin-Button
  P4  DESCRIPTION       einzigartig pro Artikel, <= 500 Zeichen,
                        keine rohen '&', keine Schablonen-Muster
  P4b PIN_TITLE         einzigartig pro Artikel, <=100 Zeichen (Premium)
  P5  MEDIA             Bild existiert, >= 10 KB, <= 5 MB
  P6  RICH-PIN-META     og:type/title/description/image/url vorhanden
  P7  RICH-PIN-MASSE    og:image:width + og:image:height (1000x1500)
  P8  HASHTAGS          nur [a-z0-9], keine Umlaute, max. 3,
                        Hashtags als Block am Ende der Beschreibung –
                        gemessen an der QUELLE (pin_description) und am
                        Build; Regel + Heiler: scripts/pinterest_hashtags.py
  P9  PROFIL-LINK       Pinterest-Profil im Footer/Startseite verlinkt
  P10 ARTIKEL-REDIRECT  LIVE-Artikel-URLs liefern Inhalt. Eine geparkte URL
                        (draft: true) darf weiterleiten – aber nur, wenn
                        data/weiterleitungen.yaml das erklärt (#822)
  P11 AFFILIATE-DICHTE  max. 5 Affiliate-Links pro Artikel
  P12 LINK-ATTRIBUTE   /go/-Links tragen sponsored/nofollow
  P13 GATEWAY-NOINDEX  /go/-Ziele sind noindex
  P14 PIN-ZIEL          kein Pin zeigt auf Weiterleitung/Entwurf/fehlendes
                        Ziel – Regel + Heiler: scripts/pinterest_ziele.py
                        (Retarget nur auf erklärten Live-Nachfolger, sonst
                        parken; Queue-Einträge werden entfernt)

SELBSTHEILUNG (--fix):
  - P1: robots.txt anlegen/reparieren
  - P3: fehlende Pin-Buttons melden (Ursache meist Template – Hinweis)
  - P4: Description-Fehler heilen: Duplikate werden durch einzigartige
        Premium-Texte ersetzt (deterministisch, aus Titel/Description/
        Keywords des Artikels), & und Länge werden sanitized.
  - P4b: Pin-Titel-Duplikate werden ebenfalls geheilt
  - P7: og:image-Maße im opengraph-Partial ergänzen (einmalig)
  - P10: Überdeckt eine Weiterleitung einen LIVE-Artikel, wird der ungültige
        SSOT-Eintrag entfernt und die erzeugte Alias-Seite gelöscht (der
        Live-Artikel gewinnt). Eine verwaiste Alias-Seite ohne SSOT-Eintrag
        wird entfernt. Fail-closed, wenn der Eintrag kein eindeutiger
        Einzeiler ist – dann bleibt der Befund stehen (#822).
  - P14: Pin-Ziele werden gegen die Live-SSOT gemessen. Heilung ohne
        Erfindung: Weiterleitungen der Regeln A/B (gleichwertiger, geprüfter
        Live-Nachfolger) werden umgeschrieben; alles andere wird nach
        data/pinterest_plan_parked.yaml geparkt (kein Content-Verlust),
        Queue-Einträge entfernt (#822).
  - P8: Hashtag-Fehler werden an der QUELLE geheilt (pin_description im
        Frontmatter): normalisieren (Umlaut-Faltung, Kleinschreibung),
        auf max. 3 kappen, als Block ans Ende stellen – idempotent.
        Bis #729 (13.10.2026) meldete diese Prüfung die Klasse nur; der
        Watchdog eröffnete damit ein Issue, das kein Heiler je schließen
        konnte (ein Befund ohne Schließpfad).

SABOTAGE-SCHUTZ: SELFTEST läuft VOR jeder Fix-Aktion – schlägt er
fehl, wird NICHTS verändert (Exit 2, wie workspace_guard).

Nutzung:
  python3 scripts/pinterest_check.py            # nur prüfen (Exit 0/1)
  python3 scripts/pinterest_check.py --fix      # heilen
  python3 scripts/pinterest_check.py --json     # JSON-Report

Ausgabe: PINTEREST-REPORT.md · Audit-Log (data/audit/*.jsonl)
"""
import datetime
import glob
import hashlib
import json
import os
import re
import sys
import unicodedata

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import join_article, doppel_freies_feld  # noqa: E402 – Naht-SSOT (FM-Grenze)
import pinterest_hashtags as ph  # noqa: E402 – Hashtag-SSOT (#729)
import pinterest_ziele as pz  # noqa: E402 – Ziel-SSOT (#822)
PUBLIC = os.path.join(BLOG_DIR, "public")
REPORT = os.path.join(BLOG_DIR, "PINTEREST-REPORT.md")
DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv

DESC_MAX = 500
MEDIA_MIN = 10 * 1024
MEDIA_MAX = 5 * 1024 * 1024
MAX_AFFILIATE_LINKS = 5
SITE = "https://franksfinanzcheck.de"
PROFILE_URL = "https://www.pinterest.de/franksfinanzcheck/"

PROBLEMS = []   # (code, artikel, msg)
FIXED = []

# P8 (#729): Was die Quelltext-Prüfung in DIESEM Lauf gesehen und geheilt hat.
# Der Build ist zu diesem Zeitpunkt älter als die Heilung (der Watchdog baut
# vor dem Check) – ein Hashtag-Befund im HTML wäre danach kein Befund mehr,
# sondern der Beleg für eine Heilung, die der nächste Build ausliefert.
SOURCE_FINDINGS = {}   # slug -> [Befunde der Quelle]
SOURCE_HEALED = {}     # slug -> [Änderungen der Heilung]
# P10 (#822): geparkte URLs mit ERKLÄRTER Weiterleitung sind Betriebszustand,
# kein Befund. Sie werden gezählt und im Report genannt – „kein Befund" heißt
# nicht „nicht gemessen" (C2).
ERKLAERT = []          # (slug, ziel, regel)

# Der Report ist ein versioniertes Betriebsartefakt. Ein bloßes Zeitstempel-
# Datum reicht nicht: Ein anderer Bot kann einen alten Report in einen neuen
# Commit mitnehmen (genau die Ursache der Phantom-Meldung #390). Der
# Fingerabdruck umfasst deshalb alle Quellen, die die lokalen Pinterest-Checks
# beeinflussen. Er enthält bewusst keine flüchtige `public/`-Ausgabe; die wird
# im Watchdog-Lauf direkt vor dem Check frisch gebaut.
#
# PREMIUM-FIX 30.09.2026 (#462) – der Fingerabdruck war ZU BREIT:
# Er hashte die kompletten Bytes von `content/posts`. Jeder Prosa-Eingriff
# (Stilpolitur, Rechtschreibung, Faktenfrische, Fazit-Schmiede) und jeder neue
# Artikel machte den Report damit „veraltet", obwohl KEINE einzige Pinterest-
# Prüfung ein anderes Ergebnis geliefert hätte. Weil der Pinterest-Watchdog um
# 04:30 UTC läuft und der Morgen-Artikel um 08:10 erscheint, war der Report
# beim Bot-Watchdog um 08:30 per KONSTRUKTION stale – ein Dauer-Alarm ohne
# Erkenntnisgewinn (dieselbe Fehlklasse wie #393).
# Der Fingerabdruck deckt jetzt den PIN-RELEVANTEN Quellenstand ab: pro
# Artikel das Frontmatter (Titel, Description, pin_title, pin_description,
# Keywords, Cover …) plus die Affiliate-Gateway-Links aus dem Fließtext
# (Grundlage von P11/P12) – also exakt das, was die Prüfungen lesen.
# Schema 3, weil alte Reports mit Schema-2-Abdruck nicht vergleichbar sind.
# Schema 4 (13.10.2026, #729): Die Hashtag-Regel (P8) liegt jetzt in
# `scripts/pinterest_hashtags.py` – die Datei beeinflusst die Prüfung, also
# gehört sie in den Fingerabdruck. Ein Schema-3-Report ist damit nicht mehr
# vergleichbar (er bezeugt einen Quellenstand ohne diese Regel).
# Schema 5 (24.10.2026, #822): P10 misst jetzt die pin-relevante Menge
# (Live-Artikel vs. geparkte URL mit erklärter Weiterleitung), und P14 misst
# die Pin-Ziele von Masterplan und Queue gegen dieselbe Live-SSOT. Der
# Fingerabdruck kennt deshalb `data/weiterleitungen.yaml`, die Zieldaten und
# `scripts/pinterest_ziele.py`; ein Schema-4-Report bezeugt einen
# Quellenstand, der diese beiden Prüfungen nicht enthielt.
REPORT_SCHEMA_VERSION = 5
_REPORT_SOURCE_DIRS = ("layouts",)
_REPORT_SOURCE_POSTS = "content/posts"
_REPORT_SOURCE_FILES = (
    "hugo.toml",
    ".github/workflows/pinterest-watchdog.yml",
    "scripts/pinterest_check.py",
    "scripts/pinterest_ziele.py",
    "scripts/weiterleitungen.py",
    "scripts/pinterest_duplicate_guard.py",
    "scripts/pinterest_hashtags.py",
    "scripts/pinterest_pin_text_sync.py",
    "scripts/pinterest_seo_healer.py",
    # P10/P14 (#822): Urteil hängt an der Weiterleitungs-SSOT und den Zieldaten.
    "data/weiterleitungen.yaml",
    "data/url_entfallen.yaml",
    "data/pinterest_plan.yaml",
    "data/pinterest_plan_parked.yaml",
    "data/pin_queue.yaml",
)
_REPORT_SOURCE_ASSETS = ("static/images/pins",)


def pin_projection(article_text: str) -> bytes:
    """Der pin-relevante Anteil EINES Artikels (Frontmatter + Gateway-Links).

    Warum nicht die ganze Datei? Weil die Pinterest-Prüfungen genau diese
    beiden Dinge lesen: das Frontmatter (P4/P4b/P5/P8 – pin_title,
    pin_description, Hashtags, Cover) und die Affiliate-Gateways im Text
    (P11/P12). Eine Komma-Korrektur im dritten Absatz ändert an keinem
    einzigen Pinterest-Signal etwas und darf den Nachweis nicht entwerten
    (#462).
    """
    text = article_text or ""
    fm = ""
    if text.startswith("---"):
        ende = text.find("\n---", 3)
        if ende != -1:
            fm = text[:ende + 4]
    gateways = sorted(set(re.findall(r"\]\((/go/[\w-]+/)\)", text)))
    direct = sorted(set(re.findall(
        r"\]\((https://a\.(?:check24|partner-versicherung)[^)]*)\)", text)))
    return ("\n".join([fm, *gateways, *direct])).encode("utf-8")


def source_fingerprint() -> str:
    """Erzeugt einen stabilen Fingerabdruck des geprüften Quellenstands.

    Pfad und Bytes werden gemeinsam gehasht, damit auch Umbenennungen,
    Löschungen und identische Dateien an unterschiedlichen Stellen sichtbar
    bleiben. Die Funktion ist absichtlich ohne Git-Abhängigkeit lauffähig und
    lässt sich so auch in Tests mit einem temporären `BLOG_DIR` verwenden.
    """
    paths = []
    root = os.path.abspath(BLOG_DIR)
    for rel in (*_REPORT_SOURCE_DIRS, *_REPORT_SOURCE_ASSETS):
        directory = os.path.join(root, rel)
        if not os.path.isdir(directory):
            continue
        for current, _dirs, files in os.walk(directory):
            for name in files:
                path = os.path.join(current, name)
                if os.path.isfile(path):
                    paths.append(path)
    for rel in _REPORT_SOURCE_FILES:
        path = os.path.join(root, rel)
        if os.path.isfile(path):
            paths.append(path)

    digest = hashlib.sha256()
    for path in sorted(set(paths)):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\\0")
        with open(path, "rb") as fh:
            digest.update(fh.read())
        digest.update(b"\\0")

    # Artikel gehen NUR mit ihrer pin-relevanten Projektion ein (#462).
    posts_dir = os.path.join(root, _REPORT_SOURCE_POSTS)
    artikel = []
    if os.path.isdir(posts_dir):
        for current, _dirs, files in os.walk(posts_dir):
            for name in files:
                if name.endswith(".md"):
                    artikel.append(os.path.join(current, name))
    for path in sorted(set(artikel)):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        digest.update(rel.encode("utf-8"))
        digest.update(b"\\0")
        try:
            with open(path, encoding="utf-8") as fh:
                digest.update(pin_projection(fh.read()))
        except OSError:
            digest.update(b"<unlesbar>")
        digest.update(b"\\0")
    return digest.hexdigest()


def report_source_fingerprint(report_text: str) -> str | None:
    """Liest den Quellfingerabdruck aus einem Pinterest-Report.

    `None` bedeutet bewusst „nicht nachweisbar“ (altes Reportformat oder
    beschädigte Zeile) und darf nie als aktueller Report gewertet werden.
    """
    match = re.search(r"Quellfingerabdruck:\*{0,2}\s*`([0-9a-f]{64})`", report_text or "")
    return match.group(1) if match else None


# ------------------------------------------------------------ Helfer

def _post_slugs(root=None):
    """Echte Artikel-Slugs aus `content/posts` (auch Entwürfe – die Auswahl
    trifft jede Prüfung selbst; P10 und P14 brauchen den Unterschied)."""
    root = root or BLOG_DIR
    return sorted(os.path.basename(os.path.dirname(f))
                  for f in glob.glob(os.path.join(root, "content", "posts", "*", "index.md")))


def _is_redirect_html(path):
    try:
        t = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return False
    return 'http-equiv="refresh"' in t or "http-equiv=refresh" in t


def _check_robots():
    """P1: robots.txt (layouts/robots.txt = Hugo-Template, gewinnt über static)
    existiert, erlaubt Pinterest und blockt /go/ (Affiliate-Gateway)."""
    p = os.path.join(BLOG_DIR, "layouts", "robots.txt")
    if not os.path.exists(p):
        PROBLEMS.append(("P1", "-", "layouts/robots.txt fehlt – Pinterest-Crawler nicht explizit erlaubt"))
        if DO_FIX:
            robots = (
                "User-agent: *\n"
                "Allow: /\n"
                "Disallow: /go/\n"
                "\n"
                "# Pinterest-Crawler explizit erlauben (Rich Pins / Pin-Scraping)\n"
                "User-agent: Pinterest\n"
                "Allow: /\n"
                "\n"
                "Sitemap: {{ \"sitemap.xml\" | absURL }}\n"
            )
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(robots)
            FIXED.append(("P1", "-", "layouts/robots.txt erstellt (Pinterest erlaubt, /go/ blockt)"))
        return
    t = open(p, encoding="utf-8").read()
    if "Pinterest" not in t:
        PROBLEMS.append(("P1", "-", "layouts/robots.txt erwähnt Pinterest nicht"))
        if DO_FIX:
            with open(p, "a", encoding="utf-8") as f:
                f.write("\n# Pinterest-Crawler explizit erlauben\n"
                        "User-agent: Pinterest\nAllow: /\n")
            FIXED.append(("P1", "-", "layouts/robots.txt um Pinterest-Regel ergänzt"))
    if "Disallow: /go/" not in t:
        PROBLEMS.append(("P1", "-", "layouts/robots.txt blockt /go/ nicht (Affiliate-Gateway-Hygiene)"))
        if DO_FIX:
            t2 = t.replace("Allow: /", "Allow: /\nDisallow: /go/", 1)
            with open(p, "w", encoding="utf-8") as f:
                f.write(t2)
            FIXED.append(("P1", "-", "/go/-Disallow ergänzt"))


def _check_domain_verify():
    """P2: p:domain_verify vorhanden."""
    t = open(os.path.join(BLOG_DIR, "hugo.toml"), encoding="utf-8").read()
    m = re.search(r'pinterestVerify\s*=\s*"([^"]+)"', t)
    if m and m.group(1):
        return
    PROBLEMS.append(("P2", "-", "pinterestVerify fehlt in hugo.toml"))


def _is_draft(slug, root=None):
    """PREM-AUDIT 26.08.2026: Draft-Erkennung – Drafts werden mit
    buildDrafts=false NICHT gebaut (bewusst!). Sie dürfen in KEINEM
    HTML-Check als 'Seite nicht gebaut' auffallen (Falschalarm; die
    Kadenz-Wache re-queued sie, sie gehen später wieder live)."""
    p = os.path.join(root or BLOG_DIR, "content", "posts", slug, "index.md")
    try:
        head = open(p, encoding="utf-8").read(4000)
    except OSError:
        return False
    return bool(re.search(r"^draft:\s*true\s*$", head, re.M))


# ---------------------- Premium: Frontmatter-Helfer für Selbstheilung

def _read_post_file(slug):
    path = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
    try:
        return open(path, encoding="utf-8").read(), path
    except OSError:
        return "", path

def _fm_get(content, key):
    m = re.search(rf'^{re.escape(key)}:\s*"(.*)"\s*$', content, re.M)
    if m:
        return m.group(1)
    m = re.search(rf"^{re.escape(key)}:\s*'(.*)'\s*$", content, re.M)
    if m:
        return m.group(1)
    m = re.search(rf"^{re.escape(key)}:\s*(.+?)\s*$", content, re.M)
    return m.group(1).strip() if m else ""

def _fm_get_list(content, key):
    m = re.search(rf"^{re.escape(key)}:\s*\[(.*?)\]", content, re.M)
    if m:
        return [k.strip().strip("\"'") for k in m.group(1).split(",") if k.strip()]
    raw = _fm_get(content, key)
    if not raw:
        return []
    return [k.strip().strip("\"'") for k in raw.split(",") if k.strip()]

def _fm_set(content, key, value):
    """Setzt/ersetzt ein Frontmatter-Feld (quoted, YAML-sicher).

    Zwei Härtungen gegenüber der ersten Fassung:
    * Das Ersetzen läuft über eine Funktion, nicht über den String direkt –
      ein Backslash im Wert (z. B. in einer Marke) wurde von `re.sub` sonst
      als Escape gelesen und veränderte den Text.
    * Nach dem Schreiben greift die Haus-Regel `doppel_freies_feld` (F7/C32):
      existiert der Schlüssel genau einmal? Ein doppelter Mapping-Schlüssel
      lässt Hugo den Build abbrechen, während PyYAML ihn still liest.
    """
    v = str(value).replace('"', '\\"')
    line = f'{key}: "{v}"'
    if re.search(rf"^{re.escape(key)}:\s*", content, re.M):
        new_content = re.sub(rf"^{re.escape(key)}:\s*.*$", lambda _m: line,
                             content, count=1, flags=re.M)
    else:
        if "---" in content:
            parts = content.split("---", 2)
            if len(parts) >= 3:
                fm = parts[1]
                body = parts[2]
                fm2 = fm.rstrip("\n") + "\n" + line + "\n"
                new_content = join_article(fm2, body)
            else:
                new_content = content
        else:
            new_content = content
    if new_content != content and "---" in new_content:
        parts = new_content.split("---", 2)
        if len(parts) >= 3:
            new_content = join_article(doppel_freies_feld(parts[1], key), parts[2])
    return new_content

def _build_unique_pin_description(slug, title, description, keywords, existing_descs, attempt=0):
    """Erzeugt eine einzigartige, Premium-konforme Pin-Beschreibung."""
    base_desc = (description or title or slug).strip()
    base_desc = re.sub(r"\s+", " ", base_desc).replace("&", "und")
    ctas = [
        "Jetzt Anleitung sichern!",
        "Jetzt checken und sparen!",
        "Jetzt Tipps entdecken!",
        "Jetzt lesen und bis zu 300 € sparen!",
        "Jetzt Guide sichern!",
        "Jetzt Überblick sichern!",
        "Jetzt Vergleich starten!",
    ]
    cta_idx = (sum(ord(c) for c in slug) + attempt) % len(ctas)
    cta = ctas[cta_idx]

    # Eine Regel für alle Pinterest-Schreiber: scripts/pinterest_hashtags.py
    hashtags = ph.tags_bauen(keywords, slug)
    ht_str = ph.als_text(hashtags)

    if attempt > 0:
        extras = [
            f" Inkl. Rechenbeispiel für {100+attempt*20} € Ersparnis.",
            f" Mit Schritt-für-Schritt-Checkliste.",
            f" Für {2026+attempt} aktualisiert.",
            f" Inkl. 5-Minuten-Check.",
            f" Mit Praxis-Beispiel aus dem Alltag.",
        ]
        extra = extras[attempt % len(extras)]
        base_desc = base_desc.rstrip(".") + extra

    text = f"*Werbung | {base_desc} {cta}"
    if ht_str:
        text = f"{text} {ht_str}"
    if len(text) > DESC_MAX:
        budget = DESC_MAX - len(f"*Werbung |  {cta} {ht_str}") - 4
        budget = max(60, budget)
        truncated = base_desc[:budget]
        sp = truncated.rfind(" ")
        if sp > 30:
            truncated = truncated[:sp]
        text = f"*Werbung | {truncated}… {cta}"
        if ht_str:
            text += f" {ht_str}"
    # Schlusskontrolle über die SSOT: ein Block, höchstens drei Tags, ≤500 –
    # ein erzeugter Text darf die Regel nicht erst nach dem Schreiben brechen.
    text, _ = ph.heile(text)
    text = text[:DESC_MAX]

    if text in existing_descs and attempt < 10:
        return _build_unique_pin_description(slug, title, description, keywords, existing_descs, attempt+1)
    return text

def _build_unique_pin_title(slug, title, existing_titles, attempt=0):
    """Erzeugt einen einzigartigen Pin-Titel ≤100 Zeichen."""
    base = (title or slug).strip()
    base = re.sub(r"\s+", " ", base)
    if attempt > 0:
        suffixes = [
            " – Praxis-Guide",
            " – So sparst du",
            " – Schritt für Schritt",
            " – Jetzt vergleichen",
            " – Tipps für 2026",
            f" – Teil {attempt+1}",
        ]
        suffix = suffixes[attempt % len(suffixes)]
        if len(base) + len(suffix) <= 100:
            base = base + suffix
        else:
            base = base[: 100 - len(suffix) - 1] + "…" + suffix
            base = base[:100]
    base = base[:100]
    if base in existing_titles and attempt < 10:
        return _build_unique_pin_title(slug, title, existing_titles, attempt+1)
    return base

def _check_frontmatter_duplicates():
    """Premium-Guard: Prüft ALLE Artikel (inkl. Drafts) auf doppelte
    pin_description und pin_title – und heilt sie bei --fix."""
    posts = []
    for slug in _post_slugs():
        content, path = _read_post_file(slug)
        if not content:
            continue
        title = _fm_get(content, "title") or slug
        desc = _fm_get(content, "description") or ""
        pin_title = _fm_get(content, "pin_title")
        pin_desc = _fm_get(content, "pin_description")
        keywords = _fm_get_list(content, "keywords") or _fm_get_list(content, "tags")
        posts.append({
            "slug": slug,
            "path": path,
            "content": content,
            "title": title,
            "description": desc,
            "pin_title": pin_title,
            "pin_description": pin_desc,
            "keywords": keywords,
        })

    desc_map = {}
    title_map = {}
    for p in posts:
        if p["pin_description"]:
            desc_map.setdefault(p["pin_description"], []).append(p)
        if p["pin_title"]:
            title_map.setdefault(p["pin_title"], []).append(p)

    for d, group in desc_map.items():
        if len(group) > 1:
            slugs = ", ".join(g["slug"] for g in group)
            PROBLEMS.append(("P4", slugs, "DUPLIKAT-Description (Spam-Risiko)"))
            if DO_FIX:
                existing = set(desc_map.keys())
                for g in group[1:]:
                    new_desc = _build_unique_pin_description(
                        g["slug"], g["title"], g["description"], g["keywords"], existing
                    )
                    new_content = _fm_set(g["content"], "pin_description", new_desc)
                    try:
                        open(g["path"], "w", encoding="utf-8").write(new_content)
                        FIXED.append(("P4", g["slug"], f"pin_description ent-dupliziert → {new_desc[:80]}…"))
                        existing.add(new_desc)
                        g["content"] = new_content
                        g["pin_description"] = new_desc
                    except OSError as e:
                        PROBLEMS.append(("P4", g["slug"], f"Fix fehlgeschlagen: {e}"))

    for t, group in title_map.items():
        if len(group) > 1:
            slugs = ", ".join(g["slug"] for g in group)
            PROBLEMS.append(("P4b", slugs, "DUPLIKAT-pin_title (Spam-Risiko)"))
            if DO_FIX:
                existing_titles = set(title_map.keys())
                for g in group[1:]:
                    new_title = _build_unique_pin_title(g["slug"], g["title"], existing_titles)
                    new_content = _fm_set(g["content"], "pin_title", new_title)
                    try:
                        open(g["path"], "w", encoding="utf-8").write(new_content)
                        FIXED.append(("P4b", g["slug"], f"pin_title ent-dupliziert → {new_title}"))
                        existing_titles.add(new_title)
                        g["content"] = new_content
                        g["pin_title"] = new_title
                    except OSError as e:
                        PROBLEMS.append(("P4b", g["slug"], f"Fix fehlgeschlagen: {e}"))


def _check_pin_descriptions():
    """P8 (Quelle): Hashtag-Hygiene der `pin_description` – prüfen UND heilen.

    Warum an der Quelle? Die `pin_description` speist drei Auslieferungen:
    den Pin-It-Button (Layout), die RSS-Beschreibung (index.xml, Quelle des
    Pinterest-Auto-Publish) und den API-Pin (`pinterest_engine.pin_text`).
    Ein Fehler hier ist also nicht „nur Frontmatter".

    Warum mit Heiler? #729: Der Watchdog meldete fünf Hashtags täglich neu –
    P8 heilte nichts (P1/P4/P4b/P7 sanieren andere Klassen), der Befund blieb
    in jedem Lauf stehen, und der Watchdog schließt sein Issue nur bei Exit 0. Die Heilung ist deterministisch: normalisieren, auf drei
    kappen, Block ans Ende, idempotent. Sie erfindet kein Thema (die
    Reihenfolge im Text entscheidet, gekappt wird hinten) und sie schreibt
    nur das eine Feld.
    """
    for slug in _post_slugs():
        content, path = _read_post_file(slug)
        if not content:
            continue
        pin_desc = _fm_get(content, "pin_description")
        if not pin_desc:
            continue  # „fehlt" ist P4/H6 – hier geht es nur um Hashtag-Hygiene
        funde = ph.befunde(pin_desc)
        if not funde:
            continue
        SOURCE_FINDINGS[slug] = funde
        if not DO_FIX:
            for f in funde:
                PROBLEMS.append(("P8", slug, f))
            continue
        neu, aenderungen = ph.heile(pin_desc)
        if neu == pin_desc:
            # Heilung hat nichts verändert → der Befund bleibt stehen (fail-closed)
            for f in funde:
                PROBLEMS.append(("P8", slug, f))
            continue
        new_content = _fm_set(content, "pin_description", neu)
        try:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new_content)
        except OSError as e:
            PROBLEMS.append(("P8", slug, f"Heilung nicht schreibbar: {e}"))
            continue
        SOURCE_HEALED[slug] = list(aenderungen)
        FIXED.append(("P8", slug, "; ".join(aenderungen)
                      + f" → {neu[-60:] if len(neu) > 60 else neu}"))


def _check_pin_buttons():
    """P3 + P4 + P5 + P8: Pin-Button, Description, Media, Hashtags pro Artikel."""
    import urllib.parse
    descs = {}
    for slug in _post_slugs():
        if _is_draft(slug):
            continue
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            PROBLEMS.append(("P3", slug, "Seite nicht gebaut (public fehlt?)"))
            continue
        if _is_redirect_html(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        m = re.search(r'pin/create/button/\?([^"\'"]+)', h)
        if not m:
            PROBLEMS.append(("P3", slug, "KEIN Pin-Button im Artikel"))
            continue
        q = urllib.parse.parse_qs(m.group(1).replace("&amp;", "&"))
        desc = urllib.parse.unquote(q.get("description", [""])[0])
        media = q.get("media", [""])[0]
        if len(desc) > DESC_MAX:
            PROBLEMS.append(("P4", slug, f"Description {len(desc)} Zeichen > {DESC_MAX}"))
        if "&" in desc:
            PROBLEMS.append(("P4", slug, "rohes & in Description"))
        if re.search(r"– via FranksFinanzcheck|via FranksFinanzcheck$", desc):
            PROBLEMS.append(("P4", slug, "Schablonen-Description (via FranksFinanzcheck)"))
        descs.setdefault(desc, []).append(slug)
        path = media.replace(SITE, "")
        local = os.path.join(BLOG_DIR, "static", path.lstrip("/"))
        if not os.path.exists(local):
            PROBLEMS.append(("P5", slug, f"Media fehlt: {path}"))
        else:
            size = os.path.getsize(local)
            if size < MEDIA_MIN:
                PROBLEMS.append(("P5", slug, f"Media zu klein ({size//1024} KB)"))
            if size > MEDIA_MAX:
                PROBLEMS.append(("P5", slug, f"Media zu groß ({size//1024//1024} MB)"))
        # P8 am Build: dieselbe Regel wie an der Quelle (scripts/pinterest_hashtags.py).
        # Die alte Zählung `#([a-z0-9]+)` war für Umlaute und Großbuchstaben
        # blind – `#zählerstand` galt als '#z', `#ersteWohnung` als '#erste',
        # und die Umlaut-Prüfung dahinter konnte nie feuern (toter Code).
        tags_problems = ph.befunde(desc)
        if tags_problems:
            if slug in SOURCE_HEALED:
                # Die Quelle wurde in DIESEM Lauf geheilt; dieser Build stammt
                # von davor. Kein offener Befund – der nächste Build liefert
                # den geheilter Stand aus (und der ist im selben Lauf belegt).
                FIXED.append(("P8", slug, "Build trägt den Stand von vor der "
                                          "Heilung – nächster Build liefert den "
                                          "geheilten Stand aus"))
            elif slug in SOURCE_FINDINGS:
                pass  # derselbe Text, schon quellseitig als P8 gemeldet
            else:
                PROBLEMS.append(("P8", slug, "Build weicht von der Quelle ab: "
                                             + "; ".join(tags_problems)))
    for d, slugs in descs.items():
        if len(slugs) > 1:
            already = any(slugs[0] in p[1] for p in PROBLEMS if p[0] == "P4")
            if not already:
                PROBLEMS.append(("P4", ", ".join(slugs), "DUPLIKAT-Description (Spam-Risiko)"))


def _alias_art(pfad):
    """'generiert' (weiterleitungen.py), 'fremd' (Handarbeit) oder 'fehlt'."""
    if not os.path.exists(pfad):
        return "fehlt"
    with open(pfad, encoding="utf-8", errors="ignore") as fh:
        return "generiert" if "ff-weiterleitung" in fh.read(1500) else "fremd"


def _entferne_alias(verzeichnis, slug):
    """Entfernt eine erzeugte Alias-Seite (static/ und public/ getrennt)."""
    pfad = os.path.join(verzeichnis, "posts", slug, "index.html")
    art = _alias_art(pfad)
    if art != "generiert":
        return art == "fehlt", f"Seite {art} – nicht gelöscht"
    os.remove(pfad)
    try:
        os.rmdir(os.path.dirname(pfad))  # leeres Verzeichnis aufräumen
    except OSError:
        pass
    return True, "erzeugte Alias-Seite gelöscht"


def _p10_pruefen(root=None, public=None, fix=False):
    """P10: Pin-relevante URLs liefern Inhalt, geparkte URLs eine erklärte Weiterleitung.

    Die Regel in Zahlen (#822): `content/posts/<slug>` mit `draft: true` ist
    GEPARKT – Hugo baut es nicht, eine erklärte Weiterleitung in
    `data/weiterleitungen.yaml` ist dann die gewollte Auslieferung. Ein
    LIVE-Artikel dagegen darf niemals von einer Weiterleitung überdeckt
    werden: Dann ist die Seite für Besucher, für Pinterest und für Google
    kein Artikel mehr, obwohl das Frontmatter „live“ sagt. Genau diesen
    Unterschied hat P10 bis zum 24.10.2026 nicht gemacht – es meldete den
    geparkten Bestand täglich als Defekt, ohne Heiler und ohne Schließpfad.
    """
    root, public = root or BLOG_DIR, public or PUBLIC
    probleme, heilungen, erklaert = [], [], []
    try:
        weiter = pz.lade_weiterleitungen(root)
    except pz.QuellenFehler as exc:
        return ([("P10", "-", f"Weiterleitungs-Quelle nicht lesbar ({exc}) – "
                             "Alias-Herkunft nicht nachweisbar")], [], [])
    for slug in _post_slugs(root):
        html_path = os.path.join(public, "posts", slug, "index.html")
        if not os.path.exists(html_path) or not _is_redirect_html(html_path):
            continue
        pfad = f"/posts/{slug}/"
        eintrag = weiter.get(pfad)
        geparkt = _is_draft(slug, root)
        if geparkt and eintrag:
            # Betriebszustand: geparkt + erklärte Weiterleitung = Absicht.
            erklaert.append((slug, eintrag.get("nach") or "?", eintrag.get("regel") or "?"))
            continue
        if geparkt:
            befund = ("geparkte URL liefert eine verwaiste Weiterleitung ohne Eintrag "
                      "in data/weiterleitungen.yaml")
        else:
            befund = ("LIVE-Artikel wird von einer Weiterleitung überdeckt – die URL "
                      "ist kein Artikel mehr (data/weiterleitungen.yaml)")
        quelle = os.path.join(root, "static")
        if _alias_art(os.path.join(quelle, "posts", slug, "index.html")) == "fremd":
            probleme.append(("P10", slug, f"{befund}; die Seite ist Handarbeit "
                                          "(kein Generator-Marker) – Handentscheidung"))
            continue
        if not fix:
            probleme.append(("P10", slug, befund))
            continue
        if eintrag:
            ok, meldung = pz.entferne_weiterleitung(root, pfad, fix=True)
            if not ok:
                probleme.append(("P10", slug, f"{befund} – {meldung} (fail-closed)"))
                continue
        ok_q, _ = _entferne_alias(quelle, slug)
        _entferne_alias(public, slug)
        if not ok_q:
            probleme.append(("P10", slug, f"{befund} – Alias-Seite in static/ nicht "
                                          "entfernbar (fail-closed)"))
            continue
        heilungen.append(("P10", slug, ("LIVE-Artikel gewinnt: SSOT-Eintrag und "
                                        "Alias-Seite entfernt" if not geparkt else
                                        "verwaiste Alias-Seite entfernt "
                                        "(Herkunft nicht in der SSOT)")))
    return probleme, heilungen, erklaert


def _check_no_redirect_on_article():
    """P10 über den echten Baum (public/ + static/) – Befunde und Heilungen."""
    probleme, heilungen, erklaert = _p10_pruefen(BLOG_DIR, PUBLIC, DO_FIX)
    PROBLEMS.extend(probleme)
    FIXED.extend(heilungen)
    ERKLAERT.extend(erklaert)


def _check_pin_ziele():
    """P14: Kein Pin zeigt auf eine Weiterleitung, einen Entwurf oder ins Leere.

    Die Ziel-Auflösung ist SSOT (`scripts/pinterest_ziele.py`): live heißt
    live nach `weiterleitungen.live_urls()`. Geheilt wird ohne Erfindung –
    Retarget nur bei erklärten Regeln A/B, sonst parken.
    """
    try:
        offen, geheilt = pz.heile(BLOG_DIR, fix=DO_FIX)
    except (pz.QuellenFehler, OSError) as exc:
        PROBLEMS.append(("P14", "-", f"Pin-Ziele nicht messbar ({exc}) – fail-closed"))
        return
    for h in geheilt:
        ziel = f"Tag {h['tag']}"
        if h["aktion"] == "retarget":
            FIXED.append(("P14", ziel, f"{h['von']} → {h['nach']} (Regel {h['regel']}: "
                                       "gleichwertiger Live-Beitrag)"))
        elif h["aktion"] == "queue":
            FIXED.append(("P14", ziel, f"Queue-Ziel {h['von']} war {h['status']} – "
                                       "Eintrag entfernt"))
        else:
            FIXED.append(("P14", ziel, f"{h['von']} war {h['status']} – Pin geparkt "
                                       "(data/pinterest_plan_parked.yaml, kein Verlust)"))
    for o in offen:
        PROBLEMS.append(("P14", f"Tag {o['tag']}",
                         f"{o['pfad'] or 'ohne Ziel'} ist {o['status']} – kein Pin-Ziel"))


def _check_affiliate_density():
    """P11: Affiliate-Link-Dichte pro Artikel; redaktionelle Korrektur bleibt manuell."""
    for slug in _post_slugs():
        p = os.path.join(BLOG_DIR, "content", "posts", slug, "index.md")
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8") as fh:
            c = fh.read()
        total = _affiliate_link_count(c)
        if total > MAX_AFFILIATE_LINKS:
            PROBLEMS.append((
                "P11", slug,
                f"{total} Affiliate-Links (> {MAX_AFFILIATE_LINKS} – Profi-Limit)"
            ))


def _affiliate_link_count(content):
    """Zählt interne Affiliate-Gateways und unterstützte direkte Partner-Links."""
    go = len(re.findall(r"\]\(/go/[\w-]+/\)", content))
    direct = len(re.findall(
        r"\]\(https://a\.(?:check24|partner-versicherung)[^)]*\)", content
    ))
    return go + direct


def _check_go_links_rel():
    """P12: /go/-Links im HTML tragen rel='sponsored nofollow'"""
    for slug in _post_slugs():
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        for m in re.finditer(r'<a[^>]*href="/go/[^"]*"[^>]*>', h):
            a = m.group(0)
            if "rel=" not in a or ("nofollow" not in a and "sponsored" not in a):
                PROBLEMS.append(("P12", slug, "/go/-Link ohne nofollow/sponsored"))
                break


def _check_go_noindex():
    """P13: /go/-Gateway-Seiten sind noindex,nofollow"""
    go_dir = os.path.join(BLOG_DIR, "static", "go")
    if not os.path.isdir(go_dir):
        return
    for d in sorted(os.listdir(go_dir)):
        p = os.path.join(go_dir, d, "index.html")
        if not os.path.exists(p):
            PROBLEMS.append(("P13", d, "/go/<key>/index.html fehlt"))
            continue
        h = open(p, encoding="utf-8").read()
        if "noindex" not in h:
            PROBLEMS.append(("P13", d, "/go/ ohne noindex"))


def _check_rich_pins():
    """P6 + P7: Rich-Pin-Meta + Bildmaße."""
    required = ["og:type", "og:title", "og:description", "og:image", "og:url"]
    for slug in _post_slugs():
        html_path = os.path.join(PUBLIC, "posts", slug, "index.html")
        if not os.path.exists(html_path):
            continue
        if _is_redirect_html(html_path):
            continue
        h = open(html_path, encoding="utf-8", errors="ignore").read()
        for prop in required:
            if f'property="{prop}"' not in h and f"property={prop}" not in h:
                PROBLEMS.append(("P6", slug, f"{prop} fehlt"))
        if "og:image:width" not in h:
            PROBLEMS.append(("P7", slug, "og:image:width fehlt (Rich-Pin-Maße)"))
        if "og:image:height" not in h:
            PROBLEMS.append(("P7", slug, "og:image:height fehlt (Rich-Pin-Maße)"))


def _check_profile_link():
    """P9: Pinterest-Profil im Footer verlinkt."""
    t = open(os.path.join(BLOG_DIR, "hugo.toml"), encoding="utf-8").read()
    if "pinterest" not in t.lower() or "franksfinanzcheck" not in t.lower():
        PROBLEMS.append(("P9", "-", "Pinterest-Profil-Link fehlt in hugo.toml"))


# ------------------------------------------------- Sabotage-Schutz

def _selftest():
    """Prüft die Kern-Logik VOR jeder Fix-Aktion (Sabotage-Schutz)."""
    fehler = []
    if DESC_MAX != 500:
        fehler.append("DESC_MAX verändert")
    if MEDIA_MIN != 10 * 1024 or MEDIA_MAX != 5 * 1024 * 1024:
        fehler.append("MEDIA-Grenzen verändert")
    if not re.search(r"– via FranksFinanzcheck", "X – via FranksFinanzcheck"):
        fehler.append("Schablonen-Regex defekt")
    if re.search(r"– via FranksFinanzcheck", "sauberer Text"):
        fehler.append("Schablonen-Regex zu aggressiv")
    if not re.search(r"[äöüß]", "#vögel"):
        fehler.append("Umlaut-Regex defekt")
    # P8 (#729): die Hashtag-Regel liegt in scripts/pinterest_hashtags.py.
    # Der Selbsttest friert die Kopplung ein – zwei Wahrheiten über dieselbe
    # Regel waren die Ursache (der Check zählte [a-z0-9], der Heiler prüfte
    # nur Länge und '&', und die Umlaut-Prüfung konnte nie feuern).
    if DESC_MAX != ph.BESCHREIBUNG_MAX:
        fehler.append("DESC_MAX ≠ pinterest_hashtags.BESCHREIBUNG_MAX (zwei Wahrheiten)")
    if ph.HASHTAG_MAX != 3:
        fehler.append("Hashtag-Maximum ≠ 3 (P8)")
    # Vier Fälle: kappen (H1), Umlaut (H2), Großbuchstabe (H2), konform (still).
    for text, muss_enthalten, muss_still_sein in (
        ("*Werbung | Text. #umzug #internet #rufnummer #dsl #wechsel",
         "5 Hashtags (max. 3)", False),
        ("*Werbung | Text. #zählerstand #gas", "Umlaut-Hashtag", False),
        ("*Werbung | Text. #ersteWohnung #fixkosten", "Großbuchstaben", False),
        ("*Werbung | Text. #umzug #internet #rufnummer", None, True),
    ):
        funde = ph.befunde(text)
        if muss_still_sein and funde:
            fehler.append(f"P8: konformer Text beanstandet: {funde}")
        if muss_enthalten and not any(muss_enthalten in f for f in funde):
            fehler.append(f"P8: '{muss_enthalten}' nicht erkannt (toter Code?)")
    geheilt = ph.heile("*Werbung | Text. #umzug #internet #rufnummer #dsl #wechsel")[0]
    if not ph.ist_konform(geheilt) or ph.heile(geheilt)[0] != geheilt:
        fehler.append("P8: Heilung nicht idempotent/konform")
    if SITE != "https://franksfinanzcheck.de":
        fehler.append("SITE verändert")
    if PROFILE_URL != "https://www.pinterest.de/franksfinanzcheck/":
        fehler.append("PROFILE_URL verändert")
    if _affiliate_link_count(
        "[Strom](/go/strom/) [Tarif](https://a.check24.net/click) "
        "[Versicherung](https://a.partner-versicherung.de/click)"
    ) != 3:
        fehler.append("P11-Affiliate-Link-Zähler defekt")
    if MAX_AFFILIATE_LINKS != 5:
        fehler.append("P11-Profi-Limit verändert")
    test_existing = {"*Werbung | Test"}
    gen = _build_unique_pin_description("test-slug", "Test Titel", "Test Beschreibung", ["kw"], test_existing)
    if gen in test_existing or len(gen) > DESC_MAX or "&" in gen:
        fehler.append("Unique-Generator defekt")
    gen_t = _build_unique_pin_title("test-slug", "Test Titel", {"Test Titel"})
    if gen_t == "Test Titel" or len(gen_t) > 100:
        fehler.append("Title-Unique-Generator defekt")
    # P14 (#822): Die Ziel-Regel hat EINE Quelle – ihr Selbsttest läuft hier mit.
    for e in pz._selftest():
        fehler.append(f"P14-Ziel-SSOT: {e}")
    fehler.extend(_p10_selftest())
    return fehler


def _p10_selftest():
    """P10 (#822): geparkt+erklärt ist kein Befund, live+Alias ist einer.

    Eingefroren wird beides – die Erkennung UND die Heilung –, weil der
    Unterschied zwischen „Betriebszustand“ und „Defekt“ genau der Fehler war,
    der #822 fünf Tage lang täglich gemeldet hat.
    """
    import tempfile as _tf
    f = []
    with _tf.TemporaryDirectory() as tmp:
        def baue(slug, draft, ssot, alias=True):
            d = os.path.join(tmp, "content", "posts", slug)
            os.makedirs(d, exist_ok=True)
            with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
                fh.write("---\ntitle: X\n" + ("draft: true\n" if draft else "") + "---\n")
            if alias:
                for basis in (os.path.join(tmp, "static"), os.path.join(tmp, "public")):
                    p = os.path.join(basis, "posts", slug, "index.html")
                    os.makedirs(os.path.dirname(p), exist_ok=True)
                    with open(p, "w", encoding="utf-8") as fh:
                        fh.write('<meta name="ff-weiterleitung" content="regel-C">'
                                 '<meta http-equiv="refresh" content="0; url=/x/">')
            return f"/posts/{slug}/"

        os.makedirs(os.path.join(tmp, "data"))
        with open(os.path.join(tmp, "data", "url_entfallen.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("eintraege: []\n")
        eintraege = ["/posts/geparkt/", "/posts/live/"]
        with open(os.path.join(tmp, "data", "weiterleitungen.yaml"), "w",
                  encoding="utf-8") as fh:
            fh.write("eintraege:\n" + "".join(
                f'  - {{von: "{e}", nach: "/pillar/x/", regel: "C", grund: "Test"}}\n'
                for e in eintraege))
        baue("geparkt", True, True)
        baue("live", False, True)
        baue("ohne", True, False)
        pub = os.path.join(tmp, "public")
        probleme, heilungen, erklaert = _p10_pruefen(tmp, pub, fix=False)
        gemeldet = {s for _c, s, _m in probleme}
        if "geparkt" in gemeldet:
            f.append("P10: geparkte URL mit erklärter Weiterleitung gilt als Befund "
                     "(genau #822)")
        if not {"live", "ohne"} <= gemeldet:
            f.append(f"P10: echte Defekte nicht erkannt ({gemeldet})")
        if [e[0] for e in erklaert] != ["geparkt"]:
            f.append("P10: erklärte Weiterleitung nicht als Betriebszustand belegt")
        probleme, heilungen, _ = _p10_pruefen(tmp, pub, fix=True)
        if probleme:
            f.append(f"P10: Heilung ließ Befunde stehen ({probleme})")
        if len(heilungen) != 2:
            f.append(f"P10: {len(heilungen)} Heilungen, erwartet 2")
        for basis in (os.path.join(tmp, "static"), pub):
            for slug in ("live", "ohne"):
                if os.path.exists(os.path.join(basis, "posts", slug, "index.html")):
                    f.append(f"P10: Alias-Seite {basis}/{slug} nicht entfernt")
        with open(os.path.join(tmp, "data", "weiterleitungen.yaml"),
                  encoding="utf-8") as fh:
            ssot = fh.read()
        if "/posts/live/" in ssot:
            f.append("P10: SSOT-Eintrag des LIVE-Artikels nicht entfernt")
        if "/posts/geparkt/" not in ssot:
            f.append("P10: geparkte, erklärte Weiterleitung wurde angefasst")
        probleme, _, erklaert = _p10_pruefen(tmp, pub, fix=True)
        if probleme:
            f.append(f"P10: Heilung ist nicht idempotent ({probleme})")
    return f


# ------------------------------------------------------------ main

def main():
    st = _selftest()
    if st:
        print("🛑 PINTEREST-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert, keine Änderung.")
        for e in st:
            print(f"   {e}")
        sys.exit(2)
    print(f"✅ Pinterest-Selbsttest ok (Modus: {'FIX' if DO_FIX else 'CHECK'})")

    public_ready = os.path.isdir(PUBLIC)
    nicht_gemessen = [] if public_ready else ["P3", "P6", "P7", "P10", "P12"]
    if not public_ready:
        print("ℹ️  public/ fehlt (kein Hugo-Build) – HTML-Checks P3/P6/P7/P10/P12 übersprungen.")
        print("   C2: Eine nicht ausgeführte Messung ist kein Grün – der Report nennt sie.")

    if DO_FIX:
        _check_robots()
    _check_domain_verify()
    _check_frontmatter_duplicates()
    # P8 zuerst an der QUELLE (heilt vor dem HTML-Vergleich), danach am Build.
    _check_pin_descriptions()
    if public_ready:
        _check_pin_buttons()
    _check_affiliate_density()
    # P14 (#822): Pin-Ziele gegen die Live-SSOT – Quelle ist der Masterplan,
    # kein Build nötig. Läuft VOR P10, damit die geheilten Ziele schon stehen.
    _check_pin_ziele()
    _check_go_noindex()
    if public_ready:
        _check_no_redirect_on_article()
        _check_go_links_rel()
        _check_rich_pins()
    _check_profile_link()
    if not DO_FIX:
        _check_robots()

    lines = _report_zeilen(nicht_gemessen)
    REPORT_PATH = os.path.join(BLOG_DIR, REPORT) if not os.path.isabs(REPORT) else REPORT
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    for code, slug, msg in PROBLEMS:
        print(f"  ❌ [{code}] {slug}: {msg}")
    for code, slug, msg in FIXED:
        print(f"  ✅ [FIX {code}] {slug}: {msg}")

    if FIXED or PROBLEMS:
        try:
            sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
            from audit_log import log_event
            log_event(module="pinterest_check", action="fix" if DO_FIX else "check",
                      input={}, output={"problems": len(PROBLEMS), "fixed": len(FIXED)},
                      status="ok" if not PROBLEMS else "issues")
        except Exception:
            pass

    if AS_JSON:
        print(json.dumps({"problems": PROBLEMS, "fixed": FIXED}, ensure_ascii=False))
    return 1 if PROBLEMS else 0


def _report_zeilen(nicht_gemessen=()):
    """Der Report-Text – auch als reine Funktion, damit er prüfbar ist.

    Eine nicht ausgeführte Messung ist kein Grün (C2): Fehlt `public/`,
    nennt der Report die übersprungenen HTML-Prüfungen ausdrücklich und
    behauptet nicht „alle Signale im Profi-Bereich".
    """
    alle = _post_slugs()
    live = len([s for s in alle if not _is_draft(s)])
    lines = ["# 📌 PINTEREST-REPORT", "",
             f"**Stand:** {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC · "
             f"Modus: {'FIX' if DO_FIX else 'CHECK'}", "",
             f"**Report-Schema:** {REPORT_SCHEMA_VERSION} · **Geprüfte Artikel:** {len(alle)} "
             f"(live: {live} · geparkt: {len(alle) - live})",
             f"**Quellfingerabdruck:** `{source_fingerprint()}`", "",
             f"Probleme: {len(PROBLEMS)} · Geheilt: {len(FIXED)}", ""]
    if ERKLAERT:
        lines += [f"**Geparkte URLs mit erklärter Weiterleitung:** {len(ERKLAERT)} "
                  f"(`data/weiterleitungen.yaml`, bewusst kein Pin-Ziel – kein "
                  f"Befund):", ""]
        for slug, ziel, regel in ERKLAERT:
            lines.append(f"- `{slug}` → `{ziel}` (Regel {regel}, geparkt)")
        lines.append("")
    if nicht_gemessen:
        lines += [f"**Nicht gemessen (kein Hugo-Build in `public/`):** "
                  f"{', '.join(nicht_gemessen)} – dieser Report ist dort "
                  f"unbekannt, nicht grün (C2).", ""]
    if PROBLEMS:
        lines.append("| Code | Artikel | Problem |")
        lines.append("|---|---|---|")
        for code, slug, msg in PROBLEMS:
            lines.append(f"| {code} | {slug} | {msg} |")
    elif nicht_gemessen:
        lines.append("✅ Keine Befunde in den gemessenen Prüfungen "
                     "(P1/P2/P4/P4b/P5/P8/P9/P11/P13) – die HTML-Checks fehlen "
                     "in diesem Lauf (s. o.).")
    else:
        lines.append("✅ Alle Pinterest-Signale im Profi-Bereich.")
    if FIXED:
        lines += ["", "**Selbstheilung (diese Runde):**"]
        for code, slug, msg in FIXED:
            lines.append(f"- [{code}] {slug}: {msg}")
    return lines


if __name__ == "__main__":
    sys.exit(main())
