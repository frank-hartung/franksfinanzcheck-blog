#!/usr/bin/env python3
"""spam_guard.py – SPAM-WACHE (Google + Pinterest, Premium 26.08.2026)

Dauerauftrag (Frank): Der Blog, der RSS-Feed, der CSV-Upload und die
Pinterest-API dürfen NIEMALS Spam-Signale aussenden, die Pinterest zum
Sperren oder Google zur Abwertung (Scaled Content Abuse, Unoriginal
Content, Keyword Stuffing) geben.

KANÄLE (eigene Regelgruppe je Kanal):
  blog  B1–B7  – Spam-Profil JEDES Frontmatter+Text: Keyword-Stuffing,
                 Misleading Claims, Werbekennzeichnung, Affiliate-Dichte,
                 Originalitäts-Quote, Klon-Profil, Datums-/Hidden-Text
  feed  F1–F6  – RSS /index.xml = QUELLE des Pinterest-Auto-Publish:
                 Struktur, Item-Komplettheit, Kadenz-Konformität,
                 Cover im Build, Cross-Item-Dedup, Staleness
  csv   C1–C8  – Pinterest-Bulk-CSV: Batch-Limits (200), Pflichtfelder,
                 Title/Description-Regeln (100/500), Media + Live-Links,
                 History-Dedup (30-Tage-Rotation), Scheduling (≤30 Tage)
  api   A1–A4  – API-Pfad: Rate-Limits (10/h, 40/Tag), Pre-Create-Check
                 pro Pin, Response-Guard mit Eskalations-Pause (1h→24h→7d)

SELBSTHEILUNG (--fix, niemals Content-Verlust):
  blog: B2/B4/B5/B6/B7 hart → Artikel auf draft (Text erhalten) ·
        B3 (fehlende Kennzeichnung) → Disclosure-Zeile einfügen
  feed: führt die Spezial-Heiler aus (cadence_guard --fix, check_titles
        --fix, generate_covers) und re-verifiziert
  csv:  Datei wird neu geschrieben (Kürzung an Wortgrenze, *Werbung-
        Prefix, defekte Zeilen raus + Report im SPAM-REPORT.md)
  api:  Pause-Reset nur explizit (--reset-pause), nie automatisch

STATE/DASHBOARD (kommitiert):
  SPAM-REPORT.md               – letzter Lauf, Funde, Heilungen, API-Zustand
  data/spam_state.json         – Rate-Counter, Pausen
  data/pin_history.jsonl       – append-only Pin-Registry (Cross-Channel-
                                 Dedup: RSS-Autopublish, API, CSV, Sync)
  data/spam_history.jsonl      – Audit-Log (jeder Fund/Heilung)

SABOTAGE-SCHUTZ: --selftest mit eingefrorenen Fällen läuft VOR jeder
--fix-Aktion; Fehlschlag → Exit 2, nichts wird verändert.

AUFRUF:
  python3 scripts/spam_guard.py                      # blog feed csv api
  python3 scripts/spam_guard.py --check blog feed
  python3 scripts/spam_guard.py --fix                # + Selbstheilung
  python3 scripts/spam_guard.py --check csv --file data/pins_upload.csv
  python3 scripts/spam_guard.py --gen-csv --max 50   # kanonischer CSV
  python3 scripts/spam_guard.py --api-preflight      # (bibliothekfähig)
  python3 scripts/spam_guard.py --api-postrun
  python3 scripts/spam_guard.py --sync-pins          # Live-Pins → History
  python3 scripts/spam_guard.py --selftest
  python3 scripts/spam_guard.py --json
"""
import csv
import datetime
import json
import os
import re
import sys
import tempfile
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from collections import Counter
from email.utils import parsedate_to_datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

from post_utils import list_post_paths, slug_of          # noqa: E402
from check_titles import check_title                      # noqa: E402
import plagiat_guard as plag                               # noqa: E402
import cadence_guard as cad                                # noqa: E402

REPORT = os.path.join(BLOG_DIR, "SPAM-REPORT.md")
STATE_FILE = os.path.join(BLOG_DIR, "data", "spam_state.json")
HISTORY_FILE = os.path.join(BLOG_DIR, "data", "pin_history.jsonl")
AUDIT_FILE = os.path.join(BLOG_DIR, "data", "spam_history.jsonl")
FEED_LOCAL = os.path.join(BLOG_DIR, "public", "index.xml")
BASE_URL = os.environ.get("BLOG_BASE_URL", "https://franksfinanzcheck.de")
DOMAINS = ("franksfinanzcheck.de", "www.franksfinanzcheck.de")

DO_FIX = "--fix" in sys.argv
AS_JSON = "--json" in sys.argv
DRY_RUN = "--dry-run" in sys.argv

# ---------------- Schwellwerte (env-übersteuerbar, dokumentiert) -------------
MAX_STUFF_TITLE = 3            # B1: gleiches Wort (len≥4) 3× im Pin-/Blog-Titel
MAX_STUFF_DESC = 4             # B1: Hauptwort 4× in der Description
MAX_KEYWORD_DENSITY = 0.035    # B1: Haupt-Keyword-Anteil am Fließtext
MAX_AFF_PER_K = 4.0            # B4: /go/-Links pro 1000 Zeichen (hart)
WARN_AFF_PER_K = 2.5           # B4: Warnschwelle
MIN_UNIQUE_RATIO = 0.35        # B5: darunter = hart (Template-Masche)
WARN_UNIQUE_RATIO = 0.45       # B5: Warnschwelle
JACCARD_WARN = 0.35            # B6: Klon-Verdacht
JACCARD_HARD = 0.55            # B6: Klon (Parität zu plagiat_guard)
FEED_ITEMS_MAX = 50            # F1: Hugo limit + Pinterest-RSS-Bereich
FEED_STALE_DAYS = 4            # F6: Feed älter → Pipeline-Prüfung
CSV_ROWS_MAX = 200             # C1: Pinterest-Batch-Limit (Bulk create)
CSV_ROWS_WARN = 50             # C1: empfohlene Batch-Größe
CSV_SCHEDULE_DAYS_AHEAD = 30   # C1: Pinterest-Scheduling-Horizont
ROTATION_DAYS = 30             # C7/A2: gleicher Link < 30 Tage = Repeat-Pin
MAX_PER_HOUR = int(os.environ.get("PINTEREST_MAX_PINS_PER_HOUR", "10"))  # A1
MAX_PER_DAY = int(os.environ.get("PINTEREST_MAX_PINS_PER_DAY", "40"))    # A1
PAUSE_ESCALATION_H = (1, 24, 168)   # A3: 1. Fehler 1h, 2. 24h, 3.+ 7 Tage

# HART = konkrete Garantie-/Versprechen (UWG-kritisch, Pinterest "Misleading
# Claims"): "100 % sicherer Gewinn", "Zinsen garantiert", "ohne Risiko" in
# Versprechenskontext (Test/Kauf/Einstieg). Allgemeine Floskeln wie "sicher
# und ohne Risiko sparen" → WARN (Abschwächung empfohlen, kein Demote).
CLAIMS_HARD = [
    r"100\s*%\s*(sicher|garantiert|ohne\s+risiko|profitabel)",
    r"ohne\s+risiko\s+(?:testen|kaufen|einsteigen|sparen\s+müssen|verlieren)",
    r"risikolos",
    r"garantiert\w*\s+(?:gewinn|ertrag|erträge|zins|zinsen|spar)",
    r"(?:zinsen|erträge)\s+garantiert", r"sofort\s+reich",
    r"geld\s+(?:verdienen|verdienst)\s+garantiert",
    r"bester\s+(?:zins|anbieter|markt)\b", r"sicherer\s+gewinn",
    r"einmalig(?:e)?\s+chance", r"keine\s+verlust\s*garantie",
]
CLAIMS_WARN = [
    r"ohne\s+risiko",
    r"\bbest(?:e|er|es)\b", r"\bgünstigst(?:e|er|es)\b",
    r"\bhöchst(?:e|er|es)\b",
    r"\bsofort\s+(?:sparen|auszahlung)\b",
]

# B3: Disclosure-Marker (UWG-konform)
DISCLOSURE_RX = re.compile(r"(wering|affiliate-?links|sponsored)", re.I)
DISCLOSURE_TEXT = (
    "**Transparenz:** Dieser Artikel enthält Affiliate-Links (Werbung). "
    "Beim Abschluss über einen Link erhalten wir eine Provision – für dich "
    "entstehen keine Mehrkosten.\n"
)

STOPWORDS = set("""der die das und oder mit für aus bei von im in zu dem den des
ein eine einen einem einer euer eure wir du dein deine mir mich ich wie was
wenn dann auch nur sehr mehr am an als bis nach über unter vor um auf ist
sind war warum welcher welche welches können kann muss dürfen sollen will wird
werden sein hast haben hat euch ihr euch jetzt hier dort so einfach gerade mal
uns unsere sie sich selbst neu neue nicht schon noch wieder bis pro ca etc
sowie statt trotz wegen seit gegen durch beim beim ihre ihren ihre""".split())

SHORTENERS = ("bit.ly", "tinyurl.com", "t.co", "is.gd", "goo.gl", "cutt.ly",
              "shorturl.at", "buff.ly", "rb.gy", "rebrand.ly")

# CSV-Format = Pinterest "Bulk create Pins" (nativ): exakt diese Spalten.
CSV_COLUMNS = ["Title", "Media URL", "Pinterest board", "Description",
               "Link", "Publish date", "Keywords"]


# ------------------------------------------------------------------ Utilities
def now_utc():
    return datetime.datetime.now(datetime.timezone.utc)


def now_iso():
    return now_utc().strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(state):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=1)


def audit(event):
    try:
        os.makedirs(os.path.dirname(AUDIT_FILE), exist_ok=True)
        with open(AUDIT_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps({"ts": now_iso(), **event},
                               ensure_ascii=False) + "\n")
    except Exception:
        pass


def history_load():
    """Pin-Registry → dict {(link, image_key): record}."""
    reg = {}
    try:
        with open(HISTORY_FILE, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                reg[(r.get("link", ""), r.get("image_key", ""))] = r
    except FileNotFoundError:
        pass
    return reg


def history_append(record):
    reg = history_load()
    key = (record.get("link", ""), record.get("image_key", ""))
    if key in reg:
        return False
    os.makedirs(os.path.dirname(HISTORY_FILE), exist_ok=True)
    with open(HISTORY_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps({"ts": now_iso(), **record}, ensure_ascii=False)
                + "\n")
    return True


def history_links_recent(days=ROTATION_DAYS):
    """Links, die in den letzten `days` Tagen gepinnt wurden (Dedup-Schlüssel)."""
    now = now_utc()
    out = set()
    for r in history_load().values():
        ts = r.get("ts", "")
        try:
            if (now - datetime.datetime.fromisoformat(
                    ts.replace("Z", "+00:00"))) < datetime.timedelta(days=days):
                out.add(r.get("link", ""))
        except ValueError:
            pass
    return out


def head_ok(url, timeout=8):
    """HTTP-Status (nach Redirects) oder None bei Netz-/Sonstigen-Fehlern."""
    req = urllib.request.Request(
        url, method="HEAD", headers={"User-Agent": "Mozilla/5.0 (SpamGuard)"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def norm_link(url):
    """Link normalisieren (Query/Fragment/Fahrtstrich raus) für Dedup."""
    u = (url or "").strip()
    u = re.sub(r"[?#].*$", "", u)
    return u.rstrip("/").lower()


def wordset(text):
    return [w for w in re.findall(r"[a-zäöüß0-9]{3,}", (text or "").lower())
            if w not in STOPWORDS]


def ascii_de(text):
    """Umlaut → ASCII (Pinterest-Keywords müssen ISO-8859-sicher sein)."""
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(a, b)
    return text


def safe_word_cut(s, max_len):
    """Kürzung an der letzten Wortgrenze unter max_len (nie mitten im Wort)."""
    if len(s) <= max_len:
        return s
    cut = s[:max_len]
    sp = cut.rfind(" ")
    if sp <= 0:
        return cut.rstrip()
    return cut[:sp].rstrip(" –—-:,;")


def clean_body(content):
    """Fließtext ohne Frontmatter + Template-Bausteine (Parität zu
    check_uniqueness/brand_guard)."""
    parts = content.split("---", 2)
    body = parts[2] if len(parts) == 3 else content
    body = re.sub(
        r"\*?_?Dieser Artikel enthält Affiliate-Links.*?keine Mehrkosten\.\)?\*?",
        " ", body, flags=re.S)
    body = re.sub(r"💡\s*\*\*Schnell-Tipp.*?(?:\n\n|\Z)", " ", body, flags=re.S)
    body = re.sub(r">\s*💶\s*\*\*Spar-Tipp.*?(?:\n\n|\Z)", " ", body, flags=re.S)
    body = re.sub(r"\*\*Weiterlesen:\*\*.*?(?:\n\n|\Z)", " ", body, flags=re.S)
    body = re.sub(r"## Fazit:.*?(?=\n##|\Z)", " ", body, flags=re.S)
    body = re.sub(r"!\[.*?\]\(.*?\)", " ", body)
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    body = re.sub(r"\n{3,}", "\n\n", body)
    return body


def fm_get(content, key):
    m = re.search(r"^" + key + r":\s*[\"']?([^\"'\n]+)", content, re.M)
    return m.group(1).strip() if m else ""


_ARTIKEL_CACHE = None


def artikel_corpus():
    """Korpus (slug, date, 8-Wort-Shingles) – pro Lauf 1× berechnet."""
    global _ARTIKEL_CACHE
    if _ARTIKEL_CACHE is None:
        _ARTIKEL_CACHE = [
            {"slug": a["slug"], "date": a["date"],
             "shingles": plag.shingles(a["norm"])}
            for a in plag.artikel_daten()
        ]
    return _ARTIKEL_CACHE


# ------------------------------------------------------------------ B: BLOG
def read_post_all(path):
    content = open(path, encoding="utf-8").read()
    c = re.search(r"^date:\s*[\"']?([0-9T:\-Z]+)", content, re.M)
    aff_links = len(re.findall(r"\]\(/go/", content))
    return {
        "path": path, "slug": slug_of(path),
        "title": fm_get(content, "title"),
        "desc": fm_get(content, "description"),
        "draft": bool(re.search(r"^draft:\s*true\s*$", content, re.M)),
        "date_raw": c.group(1) if c else "",
        "pillar": fm_get(content, "pillar"),
        "pinwand": fm_get(content, "pinwand"),
        "pin_title": fm_get(content, "pin_title"),
        "pin_desc": fm_get(content, "pin_description"),
        "ai_generated": bool(re.search(r"^ai_generated:\s*true\s*$",
                                       content, re.M)),
        "aff_links": aff_links, "content": content,
        "body_raw": content.split("---", 2)[2]
        if len(content.split("---", 2)) == 3 else content,
        "body": clean_body(content),
    }


def check_blog_post(post):
    """B1–B7 → [(rule, severity, msg)]."""
    f = []
    title, desc, body = post["title"], post["desc"], post["body"]
    text_len = max(len(body), 1)

    # B1 Keyword-Stuffing (Titel, Description, Fließtext)
    stuff = []
    tw = re.findall(r"[a-zäöüß]{4,}", title.lower())
    for w in set(tw):
        if tw.count(w) >= MAX_STUFF_TITLE:
            stuff.append(f"Titel: '{w}' ×{tw.count(w)}")
    dw = wordset(desc)
    if dw:
        top, n = Counter(dw).most_common(1)[0]
        if n >= MAX_STUFF_DESC:
            stuff.append(f"Description: '{top}' ×{n}")
    bw = wordset(body)
    if len(bw) > 40:
        top, n = Counter(bw).most_common(1)[0]
        if n / len(bw) > MAX_KEYWORD_DENSITY:
            stuff.append(f"Text: '{top}' ×{n} "
                         f"({100.0 * n / len(bw):.1f} % Dichte)")
    if len(stuff) >= 2:
        f.append(("B1", "hard", "Keyword-Stuffing: " + "; ".join(stuff)))
    elif stuff:
        f.append(("B1", "warn", "Keyword-Stuffing (ein Signal): " + stuff[0]))

    # B2 Misleading Claims (Finanz)
    hard_hits = [p for p in CLAIMS_HARD if re.search(p, body, re.I)]
    if hard_hits:
        f.append(("B2", "hard",
                  "Garantie-/Versprechen-Claims (UWG/Pinterest): "
                  + ", ".join(hard_hits[:3])))
    elif [p for p in CLAIMS_WARN if re.search(p, body, re.I)]:
        warn_hits = [p for p in CLAIMS_WARN if re.search(p, body, re.I)]
        f.append(("B2", "warn", "Superlativ ohne Einschränkung ("
                                + ", ".join(warn_hits[:3]) + ")"))

    # B3 Werbekennzeichnung bei Affiliate-Links (Suche IM RAW-BODY: die
    # Boilerplate-Entfernung für B5/B6 würde die Kennzeichnung selbst
    # löschen → Falschalarm)
    intro = (post.get("body_raw") or body)[:3000]
    if post["aff_links"] > 0 and not DISCLOSURE_RX.search(intro):
        f.append(("B3", "hard",
                  "Affiliate-Links ohne Werbekennzeichnung im Intro "
                  "(UWG + Pinterest-Ad-Policy)"))

    # B4 Affiliate-Dichte
    dens = post["aff_links"] * 1000.0 / text_len
    if dens > MAX_AFF_PER_K:
        f.append(("B4", "hard",
                  f"Affiliate-Dichte {dens:.1f}/1000 Z. "
                  f"(Limit {MAX_AFF_PER_K:.0f}) – Link-Spam-Signal"))
    elif dens > WARN_AFF_PER_K:
        f.append(("B4", "warn",
                  f"Affiliate-Dichte {dens:.1f}/1000 Z. "
                  f"(Warnschwelle {WARN_AFF_PER_K})"))

    # B5 Originalitäts-Quote (Template-Masche / Scaled Content)
    words = re.findall(r"[a-zäöüß0-9]{3,}", body.lower())
    if len(words) > 150:
        ratio = len(set(words)) / len(words)
        if ratio < MIN_UNIQUE_RATIO:
            f.append(("B5", "hard",
                      f"Originalitäts-Quote {100 * ratio:.0f} % "
                      f"(< {100 * MIN_UNIQUE_RATIO:.0f} %) – "
                      f"starkes Template-/Duplikatmuster"))
        elif ratio < WARN_UNIQUE_RATIO:
            f.append(("B5", "warn",
                      f"Originalitäts-Quote {100 * ratio:.0f} % "
                      f"(< {100 * WARN_UNIQUE_RATIO:.0f} %)"))

    # B6 Klon-Profil (8-Wort-Shingle-Jaccard; jüngerer Artikel trägt Last)
    if len(words) > 100:
        sh = plag.shingles(plag.normalize(body))
        own_date = (post["date_raw"] or "0000")[:10]
        for other in artikel_corpus():
            if other["slug"] == post["slug"]:
                continue
            o_date = (other["date"] or "0000")[:10]
            if own_date < o_date:
                continue
            if own_date == o_date and other["slug"] > post["slug"]:
                continue
            jac = plag.jaccard(sh, other["shingles"])
            if jac >= JACCARD_HARD:
                f.append(("B6", "hard",
                          f"Klon-Niveau Jaccard {jac:.2f} mit "
                          f"'{other['slug']}' (≥ {JACCARD_HARD})"))
                break
            if jac >= JACCARD_WARN:
                f.append(("B6", "warn",
                          f"Klon-Verdacht Jaccard {jac:.2f} mit "
                          f"'{other['slug']}'"))
                break

    # B7 Datum-/Hidden-Text-Fehler
    today = datetime.date.today().isoformat()
    d_iso = (post["date_raw"] or "")[:10]
    if d_iso and d_iso > today:
        f.append(("B7", "hard", f"Future-Datum {d_iso}"))
    if (re.search(r"display\s*:\s*none[^}]{0,80}>[^<]{15,}", body, re.I)
            or re.search(r"font-size\s*:\s*(0|1)px[^}]{0,80}>[^<]{15,}",
                         body, re.I)):
        f.append(("B7", "hard", "Versteckter Text im Markup (Spam-Indiz)"))

    # B8 Pin-Text ohne Werbekennzeichnung (Pinterest-Ad-Policy: kommerzielle
    # Pins mit Affiliate-Ziel müssen als Werbung erkennbar sein)
    pin_desc = post.get("pin_desc") or ""
    if post["aff_links"] > 0:
        if pin_desc and "Werbung" not in pin_desc:
            f.append(("B8", "hard",
                      "Pin-Description ist Werbeeinblendung (Affiliate-Links "
                      "im Artikel) ohne 'Werbung'-Kennzeichnung"))
        elif not pin_desc:
            f.append(("B8", "warn",
                      "Keine pin_description (Engine-Fallback trägt keine "
                      "'Werbung'-Kennzeichnung)"))

    return f


def check_blog(new_only=False):
    """Alle (oder nur heute geborene) Posts → {slug: (post, findings)}."""
    findings = {}
    today = datetime.date.today().isoformat()
    for path in sorted(list_post_paths()):
        post = read_post_all(path)
        if new_only and (post["date_raw"] or "")[:10] != today:
            continue
        f = check_blog_post(post)
        if f:
            findings[post["slug"]] = (post, f)
    return findings


def fix_blog(findings):
    """Harte Blog-Funde heilen (Content wird NIEMALS gelöscht).
    B3/B8 = deterministische In-place-Heilung (keine Demotion),
    B2/B4/B5/B6/B7 = Demotion auf draft (manuelle Prüfung)."""
    healed = []
    for slug, (post, f) in sorted(findings.items()):
        # WICHTIG: Demotionsentscheid NUR über HARTe Funde – ein B2-warn
        # (Superlativ) darf einen Artikel niemals demoten!
        hard_rules = {r for r, s, _m in f if s == "hard"}
        if not hard_rules & {"B2", "B4", "B5", "B6", "B7"} and \
                hard_rules & {"B3", "B8"}:
            post_heals = []
            if "B3" in hard_rules:
                if not DRY_RUN:
                    parts = post["content"].split("---", 2)
                    body = parts[2]
                    lines = body.split("\n\n")
                    insert_at = 0
                    for i, para in enumerate(lines):
                        if para.strip() and not para.lstrip().startswith(
                                ("#", ">", "!", "|", "-")):
                            insert_at = i + 1
                            break
                    lines.insert(insert_at, DISCLOSURE_TEXT.rstrip("\n"))
                    parts[2] = "\n\n".join(lines)
                    open(post["path"], "w", encoding="utf-8").write(
                        "---\n".join(parts))
                post_heals.append("B3-Disclosure eingefügt")
            if "B8" in hard_rules:
                if not DRY_RUN:
                    content = post["content"]
                    m = re.search(
                        r"^pin_description:\s*[\"']?([^\"'\n]*)[\"']?\s*$",
                        content, re.M)
                    if m:
                        cur = m.group(1)
                        new = cur if "Werbung" in cur else \
                            safe_word_cut("*Werbung | " + cur, 500)
                        content = content.replace(
                            m.group(0),
                            'pin_description: "' + new.replace('"', "'")
                            + '"', 1)
                        open(post["path"], "w", encoding="utf-8").write(content)
                post_heals.append("B8-'Werbung'-Prefix ergänzt")
            healed.append(f"{slug}: " + " + ".join(post_heals)
                          + (" (dry-run)" if DRY_RUN else ""))
        elif hard_rules:
            if DRY_RUN:
                healed.append(f"{slug}: draft (dry-run) "
                              f"{sorted(hard_rules)}")
                continue
            content = post["content"]
            if not re.search(r"^draft:\s*true\s*$", content, re.M):
                content = re.sub(r"^draft:\s*false\s*$", "draft: true",
                                 content, count=1, flags=re.M)
            open(post["path"], "w", encoding="utf-8").write(content)
            healed.append(f"{slug}: draft gesetzt (hart: "
                          + ", ".join(sorted(hard_rules)) + ")")
        audit({"module": "spam_guard", "action": "blog-fix", "slug": slug,
               "rules": sorted({r for r, _s, _m in f})})
    return healed


def blog_ai_stats():
    """(ai_generated, gesamt-live) – Transparenz für Google Scaled Content."""
    ai = live = 0
    for path in list_post_paths():
        p = read_post_all(path)
        if p["draft"]:
            continue
        live += 1
        if p["ai_generated"]:
            ai += 1
    return ai, live# ------------------------------------------------------------------ F: FEED
def g_of(el, tag):
    c = el.find(tag)
    return (c.text or "").strip() if c is not None and c.text else ""


def parse_feed():
    if not os.path.exists(FEED_LOCAL):
        return None
    root = ET.parse(FEED_LOCAL).getroot()
    items = []
    for it in root.iter("item"):
        def g(tag):
            el = it.find(tag)
            return (el.text or "").strip() if el is not None and el.text else ""
        enc = it.find("enclosure")
        media = it.find("{http://search.yahoo.com/mrss/}content")
        items.append({
            "title": g("title"), "link": g("link"), "desc": g("description"),
            "guid": g("guid"), "pubDate": g("pubDate"),
            "image": (enc.get("url") if enc is not None
                      else (media.get("url") if media is not None else "")),
        })
    return {"tag": root.tag, "items": items}


def check_feed():
    """F1–F6 → (findings, feed|None)."""
    feed = parse_feed()
    if feed is None:
        return [("F0", "info",
                 "public/index.xml fehlt (noch kein Build) – Feed-Check "
                 "übersprungen")], None
    findings = []
    items = feed["items"]

    # F1 Struktur
    if not feed["tag"].endswith("rss"):
        findings.append(("F1", "hard", f"Feed-Root nicht RSS: {feed['tag']}"))
    if not 1 <= len(items) <= FEED_ITEMS_MAX:
        findings.append(("F1", "hard",
                         f"{len(items)} Items (Limit {FEED_ITEMS_MAX})"))
    guids = [i["guid"] or i["link"] for i in items]
    if len(guids) != len(set(guids)):
        findings.append(("F1", "hard", "Doppelte <guid> im Feed"))

    # F2 Item-Komplettheit
    for i, it in enumerate(items):
        errs = []
        t = it["title"]
        if not 15 <= len(t) <= 120:
            errs.append(f"Titel-Länge {len(t)}")
        for rule, _m in check_title(t):
            if rule == "R5":
                errs.append("Titel unvollständig (R5)")
        if not 60 <= len(it["desc"]) <= 500:
            errs.append(f"Description-Länge {len(it['desc'])}")
        if (not it["link"].startswith("https://")
                or not any(d in it["link"] for d in DOMAINS)):
            errs.append(f"Link außerhalb der Domain: {it['link'][:50]}")
        try:
            if parsedate_to_datetime(it["pubDate"]) > now_utc():
                errs.append(f"Future-pubDate {it['pubDate']}")
        except Exception:
            errs.append(f"ungültiges pubDate '{it['pubDate'][:25]}'")
        if errs:
            findings.append(("F2", "hard",
                             f"Item {i + 1} ({t[:40]}): " + "; ".join(errs)))

    # F3 Kadenz-Konformität IM FEED (die Auto-Publish-Quelle!)
    _min, max_per_day = cad.effective_limits()
    by_day = {}
    for it in items:
        try:
            by_day.setdefault(parsedate_to_datetime(it["pubDate"]).date(),
                              []).append(it)
        except Exception:
            pass
    for day, day_items in sorted(by_day.items()):
        if not cad.is_publication_day(day):
            findings.append(("F3", "hard",
                             f"{day} (kein Publikationstag): {len(day_items)} "
                             f"Items im Feed"))
        elif len(day_items) > max_per_day:
            findings.append(("F3", "hard",
                             f"{day}: {len(day_items)} Items im Feed "
                             f"(Max {max_per_day})"))

    # F4 Cover (muss im Build sein – sonst Pin ohne Bild)
    for i, it in enumerate(items):
        img = it["image"]
        if not img:
            findings.append(("F4", "hard",
                             f"Item {i + 1} ({it['title'][:35]}): kein Cover "
                             f"(Auto-Pin ohne Bild)"))
            continue
        if not img.startswith("https://"):
            findings.append(("F4", "warn",
                             f"Item {i + 1}: Bild-URL nicht https"))
        elif img.startswith(BASE_URL + "/") and \
                os.path.isdir(os.path.join(BLOG_DIR, "public")):
            rel = img[len(BASE_URL) + 1:]
            if not os.path.exists(os.path.join(BLOG_DIR, "public", rel)):
                findings.append(("F4", "hard",
                                 f"Item {i + 1}: Cover fehlt im Build ({rel})"))

    # F5 Cross-Item-Dedup (Titel/Description/Bild)
    for label, getter in (
            ("Titel", lambda it: plag.normalize(it["title"])),
            ("Description", lambda it: plag.normalize(it["desc"])[:60]),
            ("Bild", lambda it: it["image"].rstrip("/"))):
        seen = {}
        for i, it in enumerate(items):
            k = getter(it)
            if k:
                seen.setdefault(k, []).append(i)
        for _k, idxs in seen.items():
            if len(idxs) > 1:
                findings.append(("F5", "hard",
                                 f"Doppelte {label} in Items "
                                 f"{[i + 1 for i in idxs]}"))
                break

    # F6 Staleness
    latest = None
    for it in items:
        try:
            pd = parsedate_to_datetime(it["pubDate"])
            latest = pd if latest is None else max(latest, pd)
        except Exception:
            pass
    if latest and (now_utc() - latest).days > FEED_STALE_DAYS:
        findings.append(("F6", "warn",
                         f"Neuestes Feed-Item {FEED_STALE_DAYS}+ Tage alt "
                         f"(Pipeline prüfen)"))
    return (findings or [("F-OK", "info",
                          f"Feed sauber: {len(items)} Items, "
                          f"Kadenz-konform, Cover vorhanden, keine Duplikate")
                         ]), feed


def fix_feed(findings):
    """Feed-Heilung = Heilung der QUELLE (Spezial-Guards), dann Re-Check."""
    if DRY_RUN:
        return ["Feed-Heilung übersprungen (dry-run)"]
    healed = []
    rules = {r for r, _s, _m in findings if r not in ("F0", "F-OK")}
    base = os.path.join(BLOG_DIR, "scripts")
    if "F3" in rules:
        r = os.system(f"{sys.executable} {os.path.join(base, 'cadence_guard.py')} "
                      f"--fix >/dev/null 2>&1")
        healed.append(f"cadence_guard --fix (Exit {r})")
    if "F2" in rules:
        r = os.system(f"{sys.executable} {os.path.join(base, 'check_titles.py')} "
                      f"--fix >/dev/null 2>&1")
        healed.append(f"check_titles --fix (Exit {r})")
    if "F4" in rules:
        r = os.system(f"{sys.executable} {os.path.join(base, 'generate_covers.py')} "
                      f" >/dev/null 2>&1")
        healed.append(f"generate_covers (Exit {r})")
    if rules:
        audit({"module": "spam_guard", "action": "feed-fix",
               "rules": sorted(rules)})
    return healed


# ------------------------------------------------------------------ C: CSV
def csv_read(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            return None, []
        return reader.fieldnames, [dict(r) for r in reader]


def check_csv(path, check_network=True):
    """C1–C8 → (findings, kept_rows).
    check_network=False: nur lokale Regeln (schnell, ohne HEAD-Requests)."""
    findings = []
    fields, rows = csv_read(path)
    if fields is None:
        return [("C0", "hard", f"CSV leer: {path}")], []
    missing = [c for c in ("Title", "Media URL", "Pinterest board")
               if c not in fields]
    if missing:
        return [("C0", "hard", "Pflichtspalten fehlen: " + ", ".join(missing))], []

    # C1 Batch-Limit
    if not 1 <= len(rows) <= CSV_ROWS_MAX:
        findings.append(("C1", "hard",
                         f"{len(rows)} Zeilen (Pinterest-Limit "
                         f"{CSV_ROWS_MAX})"))
    elif len(rows) > CSV_ROWS_WARN:
        findings.append(("C1", "warn",
                         f"{len(rows)} Zeilen (> {CSV_ROWS_WARN} empfohlen)"))

    recent = history_links_recent()
    kept, seen_links, seen_media, seen_pin = [], set(), set(), {}
    net_fail = 0
    for n, row in enumerate(rows, start=2):  # Zeile 2 = erste Datenzeile
        title = (row.get("Title") or "").strip()
        media = (row.get("Media URL") or "").strip()
        board = (row.get("Pinterest board") or "").strip()
        desc = (row.get("Description") or "").strip()
        link = (row.get("Link") or "").strip()
        pdate = (row.get("Publish date") or "").strip()
        kw = (row.get("Keywords") or "").strip()
        errs, heals = [], []

        # C2 Pflichtfelder
        if not title:
            errs.append("C2: Title leer")
        if not media:
            errs.append("C2: Media URL leer")
        if not board:
            errs.append("C2: Board leer")
        if not link:
            errs.append("C2: Link fehlt (Pin ohne Ziel = wertlos)")

        # C3 Title-Regeln
        if len(title) > 100:
            row["Title"] = safe_word_cut(title, 100)
            heals.append("Title auf 100 Z. gekürzt")
            title = row["Title"]
        tw = re.findall(r"[a-zäöüß]{4,}", title.lower())
        if tw and max(Counter(tw).values()) >= MAX_STUFF_TITLE:
            errs.append("C3: Title-Keyword-Stuffing")
        if [p for p in CLAIMS_HARD if re.search(p, title + " " + desc, re.I)]:
            errs.append("C3: Garantie-Claim im Pin-Text (Misleading)")

        # C4 Description-Regeln (Disclosure VOR der Kürzung → ≤ 500 gesamt)
        if link and "Werbung" not in desc:
            desc = "*Werbung | " + desc
            heals.append("*Werbung-Disclosure ergänzt")
        if len(desc) > 500:
            row["Description"] = safe_word_cut(desc, 500)
            heals.append("Description auf 500 Z. gekürzt")
            desc = row["Description"]
        else:
            row["Description"] = desc
        pin_sig = plag.normalize(title + " " + desc)
        for j, sig in seen_pin.items():
            if plag.jaccard(plag.shingles(pin_sig), sig) > 0.85:
                errs.append(f"C4: Pin-Text-Klon (Zeile {j})")
                break

        # C5 Media
        if media:
            if (not media.startswith("https://")
                    or not media.lower().endswith((".jpg", ".jpeg", ".png",
                                                    ".mp4"))):
                errs.append("C5: Media-URL ungültig (https + jpg/png/mp4)")
            elif media.rstrip("/") in seen_media:
                errs.append("C5: Klon-Bild (gleiche Media-URL 2×)")
            elif check_network:
                st = head_ok(media)
                if st is None:
                    net_fail += 1
                    if net_fail >= 5:
                        errs.append("C5: zu viele Netzfehler – Prüfung gestoppt")
                    else:
                        errs.append("C5: Media nicht erreichbar")
                elif st != 200:
                    errs.append(f"C5: Media HTTP {st}")

        # C6 Link
        if link:
            if any(s in link.lower() for s in SHORTENERS):
                errs.append("C6: URL-Kürzer verboten (Pinterest)")
            elif (not link.startswith("https://")
                    or not any(d in link for d in DOMAINS)):
                errs.append(f"C6: Link außerhalb der Domain: {link[:50]}")
            else:
                nl = norm_link(link)
                if nl in seen_links:
                    errs.append("C6: Duplikat-Link (gleicher Artikel 2×)")
                elif nl in recent:
                    errs.append(f"C7: bereits gepinnt (< {ROTATION_DAYS} Tage)"
                                " – Repeat-Pin")
                elif check_network:
                    st = head_ok(link)
                    if st is None:
                        net_fail += 1
                        if net_fail >= 5:
                            errs.append("C6: zu viele Netzfehler – gestoppt")
                    elif st == 404:
                        errs.append("C6: Link tot (404)")

        # C1b Scheduling
        if pdate:
            try:
                pd = datetime.date.fromisoformat(pdate[:10])
                if pd > datetime.date.today() + \
                        datetime.timedelta(days=CSV_SCHEDULE_DAYS_AHEAD):
                    errs.append(f"C1: Scheduling > "
                                f"{CSV_SCHEDULE_DAYS_AHEAD} Tage")
                elif pd < datetime.date.today():
                    errs.append(f"C1: Scheduling in der Vergangenheit")
            except ValueError:
                errs.append(f"C1: Publish date ungültig: {pdate}")

        # C8 Keywords
        if kw:
            kws = [k.strip() for k in kw.split(",") if k.strip()]
            kws = kws[:10]
            kws = [ascii_de(k)[:25] for k in kws]
            row["Keywords"] = ", ".join(kws)
            if len([k for k in kw.split(",") if k.strip()]) > 10:
                heals.append("Keywords auf 10 begrenzt")

        if errs:
            code = errs[0].split(":")[0]
            findings.append((code, "hard",
                             f"Zeile {n}: " + "; ".join(errs)))
        else:
            if link:
                seen_links.add(norm_link(link))
            if media:
                seen_media.add(media.rstrip("/"))
            seen_pin[n] = plag.shingles(pin_sig)
            kept.append(row)
    return findings, kept


def gen_csv(max_n=None, out_path=None):
    """Kanonischer Pinterest-Bulk-CSV aus dem Blog-Bestand.
    Zeilen: Live-Artikel, die < ROTATION_DAYS Tage nicht (neu) gepinnt
    wurden und nicht pinned:true sind. Scheduling: nächste Publikationstage,
    max. cad.effective_limits()[1] pro Tag, maximal CSV_SCHEDULE_DAYS_AHEAD
    Tage voraus."""
    max_n = max_n or int(os.environ.get("SPAM_CSV_MAX", "50"))
    out_path = out_path or os.path.join(BLOG_DIR, "data", "pins_upload.csv")
    recent = history_links_recent()
    posts = []
    for path in sorted(list_post_paths()):
        p = read_post_all(path)
        if p["draft"] or re.search(r"^pinned:\s*true", p["content"], re.M):
            continue
        if (p["date_raw"] or "")[:10] > datetime.date.today().isoformat():
            continue
        link = norm_link(f"{BASE_URL}/posts/{p['slug']}/")
        if link in recent:
            continue
        p["link"] = link
        posts.append(p)
    posts.sort(key=lambda p: p["date_raw"] or "9999")
    _min, max_per_day = cad.effective_limits()
    schedule, d = [], datetime.date.today()
    while len(schedule) < min(max_n, len(posts)) and \
            len(schedule) < len(posts):
        if cad.is_publication_day(d):
            schedule += [d.isoformat()] * max_per_day
        d += datetime.timedelta(days=1)
        if (d - datetime.date.today()).days > CSV_SCHEDULE_DAYS_AHEAD:
            break
    posts = posts[:len(schedule)]
    # Board-Mapping (Konfiguration der Pinterest-Engine wiederverwenden;
    # Fallback-Board, wenn die Konfiguration leer fehlt/fällt)
    import warnings
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            import io
            from contextlib import redirect_stdout
            with redirect_stdout(io.StringIO()):
                import pinterest_engine as pe
                board_cfg = pe.load_board_config()
    except Exception:
        pe, board_cfg = None, None
    if not board_cfg or not board_cfg[0]:
        board_cfg = None
    rows = []
    for p, day in zip(posts, schedule):
        m = re.search(r"cover:\s*\n\s*image:\s*[\"']?([^\"'\n]+)",
                      p["content"])
        media = (BASE_URL + "/" + m.group(1).lstrip("/")) if m else ""
        title = safe_word_cut(p["pin_title"] or p["title"] or p["slug"], 100)
        desc = (p["pin_desc"] or p["desc"] or p["title"]).strip()
        if "Werbung" not in desc:
            desc = "*Werbung | " + desc
        desc = safe_word_cut(desc, 500)
        kws = []
        km = re.search(r"keywords:\s*\[(.*?)\]", p["content"], re.S)
        if km:
            kws = [re.sub(r"[\"']", "", k).strip()
                   for k in km.group(1).split(",") if k.strip()][:8]
        kws = [ascii_de(k)[:25] for k in kws]
        board = "Geld sparen im Alltag | Frugalismus-Tipps"
        if board_cfg is not None:
            try:
                board = pe.board_name_for(p, board_cfg) or board
            except Exception:
                pass
        rows.append({"Title": title, "Media URL": media,
                     "Pinterest board": board, "Description": desc,
                     "Link": p["link"], "Publish date": day,
                     "Keywords": ", ".join(kws)})
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    audit({"module": "spam_guard", "action": "csv-gen", "rows": len(rows),
           "file": os.path.basename(out_path)})
    return out_path, len(rows)


def fix_csv(path, findings, kept):
    if DRY_RUN:
        return [f"CSV-Heilung übersprungen (dry-run): {len(kept)} Zeilen "
                f"sauber"]
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, extrasaction="ignore")
        w.writeheader()
        w.writerows(kept)
    audit({"module": "spam_guard", "action": "csv-fix", "file": path,
           "kept": len(kept)})
    return [f"CSV neu geschrieben: {len(kept)} Zeilen behalten"]→ Nächste Nachricht: spam_guard.py Teil 3/3 (API-Kanal A1–A4 + Selftest + Report + CLI).
