#!/usr/bin/env python3
"""PINTEREST- + GOOGLE-SEO-HEALER (Profi-Agentur, Selbstheilung)

Zentrale Orchestrierung für Titel, Cover-Texte, Meta-Daten, Keywords,
Cover-Bilder und Pinterest-Pin-Texte – auf dem Stand 2026.

Was geheilt wird (deterministisch, idempotent):
  H1  Titel-Gate          Doppelpunkt-Konvention, Komposita, Ellipsis-Reste
  H2  Meta-Description    120–160 Zeichen, Keyword vorn, klickstark
  H3  Keywords            min. 3 aus Titel/Pillar (LSI-fähig)
  H4  Cover-Alt           natürlicher Titel statt „Spar-Tipp: 2026 …"
  H5  Cover-Bilder        1000×1500 (2:3), Brand-Band, Stale-Titel → neu
  H6  Pin-SEO-Felder      pin_title (≤100, optimal 40–60), pin_description
                          (≤500, Keyword + CTA + max. 3 ASCII-Hashtags)
  H7  Tags                aus Keywords (Pinterest-/Related-Matching)

Aufruf:
  python3 scripts/pinterest_seo_healer.py              # Audit
  python3 scripts/pinterest_seo_healer.py --fix        # Selbstheilung
  python3 scripts/pinterest_seo_healer.py --fix --force-covers
  python3 scripts/pinterest_seo_healer.py --json

Exit: 0 = ok · 1 = offene Probleme · 2 = Selbsttest/Sabotage
"""
from __future__ import annotations

import datetime as _dt
import json
import os
import re
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

from post_utils import list_post_paths, slug_of  # noqa: E402

REPORT = os.path.join(BLOG_DIR, "PINTEREST-SEO-HEALER-REPORT.md")
DO_FIX = "--fix" in sys.argv
FORCE_COVERS = "--force-covers" in sys.argv
AS_JSON = "--json" in sys.argv

# Google SERP + Pinterest 2026
TITLE_MIN, TITLE_MAX = 30, 60
TITLE_OPT_MIN, TITLE_OPT_MAX = 50, 60
DESC_MIN, DESC_MAX = 70, 160
DESC_OPT_MIN, DESC_OPT_MAX = 120, 160
PIN_TITLE_MAX = 100
PIN_TITLE_OPT = 60
PIN_DESC_MIN = 220
PIN_DESC_MAX = 500
KEYWORDS_MIN = 3
HASHTAG_MAX = 3

STOP = {
    "der", "die", "das", "den", "dem", "des", "ein", "eine", "einer", "eines",
    "und", "oder", "mit", "ohne", "für", "fuer", "von", "vom", "zum", "zur",
    "im", "in", "am", "an", "auf", "aus", "bei", "so", "du", "dich", "dir",
    "dein", "deine", "wie", "was", "wer", "warum", "welche", "welcher",
    "ist", "sind", "wird", "werden", "kann", "kannst", "findest", "sichern",
    "tipps", "tipp", "ratgeber", "guide", "2024", "2025", "2026", "2027",
}


# ---------------------------------------------------------------------------
# Sabotage-Schutz
# ---------------------------------------------------------------------------

def _selftest() -> list[str]:
    err = []
    if PIN_DESC_MAX != 500:
        err.append("PIN_DESC_MAX ≠ 500")
    if PIN_TITLE_MAX != 100:
        err.append("PIN_TITLE_MAX ≠ 100")
    if HASHTAG_MAX != 3:
        err.append("HASHTAG_MAX ≠ 3")
    # Doppelpunkt-Konvention
    sample = ensure_colon_title("Mehr Freiheit durch Verzicht Clevere Frugalismus Tipps")
    if ":" not in sample:
        err.append("ensure_colon_title erzeugt keinen Doppelpunkt")
    # Hashtags ASCII-only
    tags = pin_hashtags(["Frugalismus", "Geld sparen", "DSL-Tarif", "extra"])
    if any(re.search(r"[äöüßÄÖÜ]", t) for t in tags):
        err.append("Hashtags mit Umlaut")
    if len(tags) > HASHTAG_MAX:
        err.append("zu viele Hashtags")
    # Ellipsis-Strip
    if "…" in strip_ellipsis("Foo bar…"):
        err.append("strip_ellipsis defekt")
    return err


# ---------------------------------------------------------------------------
# Frontmatter-Helfer
# ---------------------------------------------------------------------------

def split_fm(content: str):
    if not content.startswith("---"):
        return "", content, content
    parts = content.split("---", 2)
    if len(parts) < 3:
        return "", content, content
    return parts[1], parts[2], content


def fm_get(fm: str, key: str) -> str:
    m = re.search(rf"^{re.escape(key)}:\s*[\"']?(.*?)[\"']?\s*$", fm, re.M)
    return (m.group(1).strip() if m else "")


def fm_get_list(fm: str, key: str) -> list[str]:
    m = re.search(rf"^{re.escape(key)}:\s*\[(.*?)\]", fm, re.M)
    if m:
        return [k.strip().strip("\"'") for k in m.group(1).split(",") if k.strip()]
    raw = fm_get(fm, key)
    if not raw:
        return []
    return [k.strip().strip("\"'") for k in raw.split(",") if k.strip()]


def fm_set(content: str, key: str, value: str, quote: bool = True) -> str:
    """Setzt/ersetzt eine Frontmatter-Zeile (einfacher Skalar)."""
    fm, body, _ = split_fm(content)
    if not fm and not content.startswith("---"):
        return content
    line = f'{key}: "{value}"' if quote else f"{key}: {value}"
    if re.search(rf"^{re.escape(key)}:", fm, re.M):
        fm2 = re.sub(rf"^{re.escape(key)}:.*$", line, fm, count=1, flags=re.M)
    else:
        fm2 = fm.rstrip("\n") + "\n" + line + "\n"
    return "---" + fm2 + "---" + body


def fm_set_list(content: str, key: str, items: list[str]) -> str:
    items = [i for i in items if i][:8]
    rendered = "[" + ", ".join(f'"{i}"' for i in items) + "]"
    fm, body, _ = split_fm(content)
    line = f"{key}: {rendered}"
    if re.search(rf"^{re.escape(key)}:", fm, re.M):
        fm2 = re.sub(rf"^{re.escape(key)}:.*$", line, fm, count=1, flags=re.M)
    else:
        fm2 = fm.rstrip("\n") + "\n" + line + "\n"
    return "---" + fm2 + "---" + body


def fm_set_cover_alt(content: str, alt: str) -> str:
    m = re.search(
        r"(^cover:\s*\n\s*image:.*?\n)(\s*alt:.*?)(\n\s*caption:)",
        content, re.M | re.S,
    )
    if not m:
        # Alt nach image-Zeile einfügen
        m2 = re.search(r"(^cover:\s*\n\s*image:.*?\n)", content, re.M)
        if not m2:
            return content
        return content[:m2.end()] + f'  alt: "{alt}"\n' + content[m2.end():]
    return content[:m.start(2)] + f'  alt: "{alt}"' + content[m.end(2):]


# ---------------------------------------------------------------------------
# Titel / Keywords / Pin-Text
# ---------------------------------------------------------------------------

def strip_ellipsis(title: str) -> str:
    t = title.strip()
    t = re.sub(r"[…\.…]{1,}$", "", t).rstrip()
    t = re.sub(r"\s+[…\.…]+\s*$", "", t).rstrip()
    # abgeschnittene Wortreste am Ende (z. B. "im Url")
    if re.search(r"\s(im|in|am|an|zu|zur|zum|der|die|das|den|dem|für|mit|ohne|und|oder)\s+\w{1,4}$", t, re.I):
        t = re.sub(r"\s+\S+$", "", t).rstrip(" –-:")
    return t.strip()


def ensure_colon_title(title: str) -> str:
    """Erzwingt Blog-Konvention 'Hauptkeyword: Untertitel' für Cover-Umbruch.

    Regeln:
      - Titel mit ':' bleibt (nach Komposita-Fix)
      - Titel > 45 ohne ':' → semantisch teilen
      - Fragezeichen-Titel: Keyword-Teil nach dem ? wird Kopf
    """
    t = strip_ellipsis(title)
    t = re.sub(r"\s{2,}", " ", t).strip()
    if ":" in t:
        return t
    # "X? Y" → "Y: X?" falls Y Keyword-artig
    if "?" in t:
        head, tail = t.split("?", 1)
        head, tail = head.strip(), tail.strip(" ?.-–")
        if tail and len(tail) >= 8:
            # "Clevere Frugalismus Tipps" → "Frugalismus-Tipps: Mehr Freiheit durch Verzicht?"
            # Bevorzuge Substantiv-Kompositum als Keyword-Kopf
            words = tail.split()
            # Finde Haupt-Nomen (längstes Inhaltswort)
            content_w = [w for w in words if w.lower() not in STOP and len(w) > 3]
            if content_w:
                # Kopf = Rest-Phrase, Untertitel = Frage
                kw = " ".join(words)
                # Frugalismus Tipps → Frugalismus-Tipps
                kw = re.sub(r"\b([A-ZÄÖÜ][a-zäöüß]+)\s+(Tipps|Tarif|Tarife|Vergleich|Konto|Versicherung)\b",
                            r"\1-\2", kw)
                new = f"{kw}: {head}?"
                if TITLE_MIN <= len(new) <= TITLE_MAX + 8:
                    return new[:TITLE_MAX] if len(new) > TITLE_MAX else new
        # Fallback: "Frage: Antwort-Stub"
        if len(head) >= 12:
            return f"{head}?" if len(head) <= TITLE_MAX else head[:TITLE_MAX - 1] + "?"
    # Semantische Teilung nach ~40 % der Wörter (Keyword-Kopf)
    words = t.split()
    if len(words) < 4:
        return t
    # Bevorzugt nach 2–4 Wörtern teilen, wenn erstes Segment Keyword-artig
    for cut in (2, 3, 4, 5):
        if cut >= len(words):
            break
        head = " ".join(words[:cut])
        tail = " ".join(words[cut:])
        if len(head) < 12 or len(tail) < 8:
            continue
        # Kopf nicht mit Stopwort enden
        if words[cut - 1].lower().strip(".,!?") in STOP:
            continue
        candidate = f"{head}: {tail}"
        if len(candidate) <= TITLE_MAX + 5:
            return candidate if len(candidate) <= TITLE_MAX else candidate[:TITLE_MAX].rstrip()
    # Notnagel: erste Hälfte
    mid = max(2, len(words) // 2)
    return f"{' '.join(words[:mid])}: {' '.join(words[mid:])}"[:TITLE_MAX]


def restore_known_titles(slug: str, title: str) -> str:
    """Bekannte, durch Meta-Ellipsis zerstörte Titel wiederherstellen/kürzen."""
    KNOWN = {
        "2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier":
            "Haushaltsbuch führen: App, Excel oder Stift im Vergleich",
        "2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub":
            "Mietwagen ohne Kautionsfallen: So sparst du im Urlaub",
        "2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps":
            "Frugalismus-Tipps: Mehr Freiheit durch klugen Verzicht",
        "2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026":
            "Preisgarantie Gas: So sicherst du günstige Tarife",
    }
    if slug in KNOWN:
        return KNOWN[slug]
    if "…" in title or title.rstrip().endswith("..."):
        return ensure_colon_title(strip_ellipsis(title))
    return title


def trim_hanging_prep(title: str) -> str:
    """Entfernt hängende Präpositionen am Titelende (Cover-Look)."""
    t = title.rstrip()
    hang = {
        "für", "fuer", "mit", "ohne", "und", "oder", "im", "in", "am", "an",
        "auf", "aus", "bei", "von", "vom", "zum", "zur", "der", "die", "das",
        "den", "dem", "des", "ein", "eine", "so", "du",
    }
    parts = t.split()
    while parts and parts[-1].lower().strip(".,;:!?–-") in hang:
        parts.pop()
    return " ".join(parts).rstrip(" :–-")


def compound_fix(title: str) -> str:
    try:
        from check_titles import COMPOUND_FIXES, fix_title
        t = fix_title(title)
        for pat, repl in COMPOUND_FIXES:
            t = re.sub(pat, repl, t)
        return t
    except Exception:
        return title


def keywords_from_title(title: str, existing: list[str] | None = None) -> list[str]:
    """Min. 3 Keywords: Hauptkeyword (vor :) + Inhaltswörter + bestehende."""
    out: list[str] = []
    seen = set()

    def add(k: str):
        k = k.strip().strip("\"'")
        if not k or len(k) < 3:
            return
        nk = k.lower()
        if nk in seen:
            return
        seen.add(nk)
        out.append(k)

    for k in (existing or []):
        add(k)

    head = title.split(":")[0].strip() if ":" in title else title
    head = re.sub(r"[?!.…]+$", "", head).strip()
    if head:
        add(head)
        # Bindestrich-Variante ohne Bindestrich als LSI
        if "-" in head:
            add(head.replace("-", " "))

    # Inhaltswörter aus Titel: nur echte Keyword-Kandidaten (Nomen/Komposita)
    VERBISH = {
        "schützt", "schuetzt", "sicherst", "findest", "sparst", "bringst",
        "kannst", "wichtig", "clevere", "klugen", "senken", "führen", "fuehren",
        "stoppen", "kostet", "vermeiden", "verbessern", "sichern", "schützen",
        "schuetzen", "günstigsten", "guenstigsten", "stabilen", "kostenloses",
        "sicher", "heizen",
    }
    plain = re.sub(r"[^\wÄÖÜäöüß\s-]", " ", title)
    for w in plain.split():
        wl = w.lower()
        if wl in STOP or wl in VERBISH or len(w) < 5:
            continue
        # Einzelwörter nur wenn Kompositum-artig (≥ 8 Zeichen oder Bindestrich-Rest)
        if " " not in w and "-" not in w and len(w) < 8:
            continue
        if w[0].isupper() or len(w) >= 8:
            add(w)

    # Generische Finanz-LSI je nach Signal
    low = title.lower()
    if any(x in low for x in ("gas", "heiz", "preisgarantie")):
        for k in ("Gaspreisgarantie", "Gastarif wechseln", "Heizkosten senken"):
            add(k)
    if any(x in low for x in ("dsl", "internet", "wlan")):
        for k in ("DSL-Vergleich", "Internetvertrag wechseln", "günstiges Internet"):
            add(k)
    if any(x in low for x in ("frugal", "verzicht", "sparen")):
        for k in ("Frugalismus", "Geld sparen", "minimalistisch leben"):
            add(k)
    if any(x in low for x in ("giro", "konto")):
        for k in ("Girokonto vergleichen", "Konto ohne Gebühren"):
            add(k)
    if "mietwagen" in low or "kaution" in low:
        for k in ("Mietwagen buchen", "Mietwagen Kaution", "Autovermietung Tipps"):
            add(k)
    if "haushaltsbuch" in low:
        for k in ("Haushaltsbuch führen", "Budget planen", "Ausgaben tracken"):
            add(k)

    while len(out) < KEYWORDS_MIN:
        add(f"Geld sparen {len(out)+1}".replace(" 1", "").strip())
        if len(out) >= KEYWORDS_MIN:
            break
    return out[:8]


def pin_hashtags(keywords: list[str], slug: str = "") -> list[str]:
    """Max. 3 ASCII-Hashtags (Pinterest-SEO: keine Umlaute)."""
    tags = []
    pool = list(keywords) + [slug.replace("-", " ")]
    for p in pool:
        words = re.findall(r"[a-z0-9]+", _ascii(p).lower())
        tag = "".join(words)
        if 3 <= len(tag) <= 24 and tag not in tags:
            tags.append(tag)
        if len(tags) >= HASHTAG_MAX:
            break
    return tags


def _ascii(s: str) -> str:
    s = s.lower()
    for a, b in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss"),
                 ("Ä", "Ae"), ("Ö", "Oe"), ("Ü", "Ue")):
        s = s.replace(a, b)
    return s


def build_pin_title(title: str) -> str:
    """Pinterest-Titel ≤100, optimal ≤60, Keyword vorn."""
    t = re.sub(r"<[^>]+>", "", title).strip()
    if len(t) <= PIN_TITLE_OPT:
        return t
    if len(t) <= PIN_TITLE_MAX:
        return t
    # am Wortende kürzen
    cut = t[: PIN_TITLE_MAX - 1]
    sp = cut.rfind(" ")
    if sp > 40:
        cut = cut[:sp]
    return cut.rstrip(" ,.;:–-") + "…"


def build_pin_description(title: str, description: str, keywords: list[str], slug: str) -> str:
    """Pin-Text: *Werbung | Meta + CTA + max. 3 Hashtags (≤500)."""
    desc = (description or title).strip()
    desc = re.sub(r"\s+", " ", desc)
    # Roh-& vermeiden (Pinterest-Check P4)
    desc = desc.replace("&", "und")
    tags = pin_hashtags(keywords, slug)
    ht = " ".join("#" + t for t in tags)
    cta = "Mehr Spartipps auf FranksFinanzcheck!"
    text = f"*Werbung | {desc} {cta} {ht}".strip()
    if len(text) > PIN_DESC_MAX:
        # Description kürzen, Hashtags behalten
        budget = PIN_DESC_MAX - len(f"*Werbung |  {cta} {ht}") - 1
        d2 = desc[: max(40, budget)]
        sp = d2.rfind(" ")
        if sp > 30:
            d2 = d2[:sp]
        text = f"*Werbung | {d2}… {cta} {ht}".strip()
    return text[:PIN_DESC_MAX]


def extend_description(desc: str, keywords: list[str], title: str) -> str:
    desc = (desc or "").strip()
    if not desc:
        kw = keywords[0] if keywords else title.split(":")[0]
        desc = f"{kw}: Praxis-Tipps zum Sparen – klar erklärt und sofort umsetzbar."
    # Keyword vorn
    if keywords:
        core = keywords[0]
        if core.lower() not in desc.lower() and len(core) < 40:
            desc = f"{core}: {desc}"
    addons = [
        " So sparst du jeden Monat bares Geld.",
        " Schritt für Schritt erklärt – ohne Fachchinesisch.",
        " Mit praktischen Tipps für den Alltag.",
        " Vergleiche jetzt und profitiere von fairen Konditionen.",
    ]
    for add in addons:
        if len(desc) >= DESC_OPT_MIN:
            break
        if add.strip().lower()[:18] in desc.lower():
            continue
        if len(desc) + len(add) <= DESC_OPT_MAX:
            desc += add
    if len(desc) > DESC_MAX:
        cut = desc[: DESC_MAX - 1]
        sp = cut.rfind(" ")
        if sp > DESC_MAX * 0.7:
            cut = cut[:sp]
        desc = cut.rstrip(" ,.;:") + "…"
    return desc


# ---------------------------------------------------------------------------
# Artikel laden / heilen
# ---------------------------------------------------------------------------

def load_articles():
    arts = []
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        fm, body, _ = split_fm(content)
        title = fm_get(fm, "title")
        desc = fm_get(fm, "description")
        kws = fm_get_list(fm, "keywords")
        tags = fm_get_list(fm, "tags")
        draft = "draft: true" in fm
        alt_m = re.search(r"^\s*alt:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
        alt = alt_m.group(1).strip() if alt_m else ""
        cover_m = re.search(r'image:\s*[\"\']?([^\"\'\n]+)', fm)
        cover = cover_m.group(1).strip() if cover_m else ""
        pin_title = fm_get(fm, "pin_title")
        pin_desc = fm_get(fm, "pin_description")
        arts.append({
            "path": path,
            "slug": slug_of(path),
            "title": title,
            "description": desc,
            "keywords": kws,
            "tags": tags,
            "draft": draft,
            "alt": alt,
            "cover": cover,
            "pin_title": pin_title,
            "pin_description": pin_desc,
            "content": content,
            "body": body,
            "fm": fm,
        })
    return arts


def audit_article(a: dict) -> list[str]:
    issues = []
    t = a["title"]
    tl = len(re.sub(r"<[^>]+>", "", t))
    dl = len(a["description"])
    if not t:
        issues.append("Titel leer")
    else:
        if tl < TITLE_MIN:
            issues.append(f"Titel zu kurz ({tl})")
        if tl > TITLE_MAX:
            issues.append(f"Titel zu lang ({tl} > {TITLE_MAX})")
        if "…" in t or t.rstrip().endswith("..."):
            issues.append("Titel mit Ellipsis (abgeschnitten)")
        if tl > 45 and ":" not in t:
            issues.append("Titel ohne Doppelpunkt (Cover-Umbruch/Pinterest)")
    if dl < DESC_MIN:
        issues.append(f"Description zu kurz ({dl})")
    elif dl > DESC_MAX:
        issues.append(f"Description zu lang ({dl})")
    if len(a["keywords"]) < KEYWORDS_MIN:
        issues.append(f"Nur {len(a['keywords'])} Keywords (min. {KEYWORDS_MIN})")
    if not a["cover"]:
        issues.append("Cover fehlt")
    else:
        cov_path = os.path.join(BLOG_DIR, "static", a["cover"])
        if not os.path.exists(cov_path):
            issues.append("Cover-Datei fehlt")
    alt = a["alt"]
    if not alt:
        issues.append("Cover-Alt fehlt")
    elif (
        alt.startswith("Spar-Tipp:")
        or alt == "Tipp von FranksFinanzcheck"
        or re.search(r"\b20\d{2}\s+0\d\s+\d{2}\b", alt)
        or "2026 08" in alt
        or len(alt) < 12
    ):
        issues.append("Cover-Alt generisch/slug-basiert")
    if not a["pin_title"]:
        issues.append("pin_title fehlt")
    elif len(a["pin_title"]) > PIN_TITLE_MAX:
        issues.append(f"pin_title zu lang ({len(a['pin_title'])})")
    if not a["pin_description"]:
        issues.append("pin_description fehlt")
    else:
        pd = a["pin_description"]
        if len(pd) > PIN_DESC_MAX:
            issues.append(f"pin_description zu lang ({len(pd)})")
        if "&" in pd:
            issues.append("pin_description enthält rohes &")
        tags = re.findall(r"#([A-Za-z0-9]+)", pd)
        if len(tags) > HASHTAG_MAX:
            issues.append(f"zu viele Hashtags ({len(tags)})")
        if any(re.search(r"[äöüß]", t) for t in tags):
            issues.append("Umlaut-Hashtag")
    return issues


def heal_article(a: dict) -> tuple[bool, list[str]]:
    """Heilt einen Artikel. Liefert (changed, actions)."""
    actions = []
    content = a["content"]
    title = a["title"]
    orig_title = title

    # H1 Titel
    title = restore_known_titles(a["slug"], title)
    title = compound_fix(title)
    title = strip_ellipsis(title)
    if len(title) > 45 and ":" not in title:
        title = ensure_colon_title(title)
    # Länge final
    if len(title) > TITLE_MAX:
        # am Doppelpunkt-Untertitel kürzen
        if ":" in title:
            head, tail = title.split(":", 1)
            budget = TITLE_MAX - len(head) - 2
            tail = tail.strip()
            if budget > 10:
                tcut = tail[:budget]
                sp = tcut.rfind(" ")
                if sp > 8:
                    tcut = tcut[:sp]
                title = f"{head.strip()}: {tcut.strip()}"
            else:
                title = head.strip()[:TITLE_MAX]
        else:
            title = title[: TITLE_MAX - 1].rstrip() + "…"
            title = ensure_colon_title(strip_ellipsis(title))
    title = trim_hanging_prep(title)
    if title != orig_title:
        content = fm_set(content, "title", title)
        actions.append(f"Titel → {title}")

    # H3 Keywords – fehlende ergänzen + schwache Einzelwort-Reste entfernen
    WEAK_SINGLE = {
        "mehr", "klugen", "sicherst", "schützt", "schuetzt", "sparst",
        "bringst", "kannst", "findest", "wichtig", "clevere", "tipps",
        "sicher", "heizen", "tarife", "günstige", "guenstige", "senken",
        "führen", "fuehren", "stoppen", "kostet", "vermeiden", "verbessern",
        "sichern", "schützen", "schuetzen", "günstigsten", "guenstigsten",
        "stabilen", "kostenloses", "fehler", "vergleich", "freiheit",
        "verzicht", "gebühren", "gebuehren", "girokonto", "mietwagen",
        "kautionsfallen", "stromfresser", "energiediebe", "haushaltsbuch",
        "internetvertrag", "internettarif", "gasrechnung", "spätsommer",
        "spaetsommer", "preisgarantie", "preissprüngen", "preisspruengen",
        "dsl-wechselbonus",
    }

    def _is_weak(k: str) -> bool:
        kl = k.lower().strip()
        # Phrasen mit Leerzeichen/Bindestrich behalten (echte Keywords)
        if " " in k or (("-" in k or "–" in k) and len(k) >= 8):
            # außer reine Stoppwort-Phrasen
            return False
        if kl in WEAK_SINGLE or len(k) < 5:
            return True
        # Kurze Einzelwörter ohne Keyword-Wert
        if len(k) < 10 and kl.isalpha():
            return True
        return False

    base_kws = [k for k in a["keywords"] if not _is_weak(k)]
    kws = keywords_from_title(title, base_kws)
    kws = [k for k in kws if not _is_weak(k)]
    # Dedup case-insensitive
    seen_k, clean = set(), []
    for k in kws:
        nk = k.lower()
        if nk in seen_k:
            continue
        seen_k.add(nk)
        clean.append(k)
    kws = clean
    while len(kws) < KEYWORDS_MIN:
        filler = title.split(":")[0].strip() if ":" in title else "Geld sparen"
        if filler.lower() not in seen_k:
            kws.append(filler)
            seen_k.add(filler.lower())
        else:
            kws.append("Geld sparen")
            break
    if kws != a["keywords"]:
        content = fm_set_list(content, "keywords", kws[:8])
        actions.append(f"Keywords → {kws[:4]}")

    # Tags aus Keywords (Related + Pinterest)
    tags = a["tags"]
    if len(tags) < 2:
        new_tags = kws[:4]
        content = fm_set_list(content, "tags", new_tags)
        actions.append(f"Tags → {new_tags}")
        tags = new_tags

    # H2 Description
    desc = a["description"]
    if len(desc) < DESC_OPT_MIN or len(desc) > DESC_MAX or not desc:
        new_desc = extend_description(desc, kws, title)
        if new_desc != desc:
            content = fm_set(content, "description", new_desc)
            actions.append(f"Description → {len(new_desc)} Z.")
            desc = new_desc

    # H4 Cover-Alt
    good_alt = title
    alt = a["alt"]
    # Generische/slug-basierte Alts heilen; szenische Profi-Alts behalten
    bad_alt = (
        not alt
        or alt.startswith("Spar-Tipp:")
        or alt == "Tipp von FranksFinanzcheck"
        or re.search(r"\b20\d{2}\s+0\d\s+\d{2}\b", alt)
        or "2026 08" in alt
        or len(alt) < 12
    )
    if bad_alt and good_alt:
        content = fm_set_cover_alt(content, good_alt)
        actions.append(f"Cover-Alt → {good_alt[:50]}")

    # H6 Pin-SEO (Premium 25.08.2026): Existierendes, GÜLTIGES Premium-Text-
    # material (aus pinterest_pin_text_sync.py / Masterplan) wird NICHT
    # überschrieben – nur fehlende oder ungültige Felder werden
    # deterministisch nachgeheilt.
    pin_title = build_pin_title(title)
    pin_desc = build_pin_description(title, desc, kws, a["slug"])
    # Titel: & ist erlaubt (nur Button-Beschreibungen müssen &-frei sein)
    pin_title_ok = (bool(a["pin_title"].strip())
                    and len(a["pin_title"]) <= PIN_TITLE_MAX)
    pin_desc_ok = (bool(a["pin_description"].strip())
                   and PIN_DESC_MIN <= len(a["pin_description"]) <= PIN_DESC_MAX
                   and "&" not in a["pin_description"])
    if not pin_title_ok:
        content = fm_set(content, "pin_title", pin_title)
        actions.append("pin_title gesetzt")
    else:
        pin_title = a["pin_title"].strip()  # Premium-Text behalten
    if not pin_desc_ok:
        content = fm_set(content, "pin_description", pin_desc)
        actions.append("pin_description gesetzt")
    else:
        pin_desc = a["pin_description"].strip()  # Premium-Text behalten

    # Cover-Pfad sicherstellen
    if not a["cover"]:
        image_path = f"images/covers/{a['slug']}.jpg"
        # cover-Block anlegen
        fm, body, _ = split_fm(content)
        if "cover:" not in fm:
            block = (
                f"cover:\n"
                f'  image: "{image_path}"\n'
                f'  alt: "{good_alt}"\n'
                f'  caption: "Tipp von FranksFinanzcheck"\n'
            )
            content = "---" + fm.rstrip("\n") + "\n" + block + "---" + body
            actions.append("Cover-Frontmatter angelegt")

    changed = content != a["content"]
    if changed:
        open(a["path"], "w", encoding="utf-8").write(content)
        a["content"] = content
        a["title"] = title
        a["description"] = desc
        a["keywords"] = kws
        a["pin_title"] = pin_title
        a["pin_description"] = pin_desc
        a["alt"] = good_alt if bad_alt else alt
    return changed, actions


def run_subprocess(args: list[str]) -> int:
    print(f"  → {' '.join(args)}")
    r = subprocess.run([sys.executable, *args], cwd=BLOG_DIR)
    return r.returncode


def regenerate_covers(slugs: list[str] | None = None, force_all: bool = False) -> None:
    gen = os.path.join(BLOG_DIR, "scripts", "generate_covers.py")
    if force_all:
        run_subprocess([gen, "--force"])
        return
    if slugs:
        for s in slugs:
            run_subprocess([gen, "--slug", s, "--force"])
    else:
        run_subprocess([gen])


def write_report(results: list[dict], fixed: int, cover_note: str) -> None:
    now = _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    open_issues = sum(len(r["issues"]) for r in results)
    lines = [
        "# 📌 PINTEREST- + GOOGLE-SEO-HEALER",
        "",
        f"**Stand:** {now} · **Modus:** {'FIX' if DO_FIX else 'CHECK'}",
        "",
        f"- Artikel: **{len(results)}**",
        f"- Geheilt: **{fixed}**",
        f"- Offene Issues: **{open_issues}**",
        f"- Covers: {cover_note}",
        "",
        "## Kriterien 2026 (Agentur-Standard)",
        "",
        "| Feld | Google | Pinterest |",
        "|---|---|---|",
        f"| Titel | {TITLE_MIN}–{TITLE_MAX} Z. (opt. {TITLE_OPT_MIN}–{TITLE_OPT_MAX}), "
        f"Keyword vorn, `Hauptkeyword: Untertitel` | Pin-Titel ≤{PIN_TITLE_MAX} "
        f"(Feed sichtbar ~40) |",
        f"| Description | {DESC_OPT_MIN}–{DESC_OPT_MAX} Z., Keyword + CTA | "
        f"Pin-Text ≤{PIN_DESC_MAX}, `*Werbung | …`, max. {HASHTAG_MAX} ASCII-Tags |",
        "| Cover | og:image 1000×1500, Alt = Titel | 2:3, Text-Overlay, Brand-Band |",
        "| Keywords | ≥3, in Titel/Desc/H2/Slug | Hashtags aus Keywords |",
        "",
        "## Artikel",
        "",
        "| Status | Artikel | Issues |",
        "|---|---|---|",
    ]
    for r in results:
        flag = "✅" if not r["issues"] else "⚠️"
        iss = "; ".join(r["issues"][:4]) if r["issues"] else "—"
        draft = " *(draft)*" if r.get("draft") else ""
        lines.append(f"| {flag} | `{r['slug']}`{draft} | {iss} |")
    if fixed and DO_FIX:
        lines += ["", "## Selbstheilung (diese Runde)", ""]
        for r in results:
            for a in r.get("actions", []):
                lines.append(f"- `{r['slug']}`: {a}")
    lines += [
        "",
        "---",
        "*Erzeugt von `scripts/pinterest_seo_healer.py` – Teil der FrankAutoOps-Selbstheilung.*",
        "",
    ]
    open(REPORT, "w", encoding="utf-8").write("\n".join(lines))


def main() -> int:
    st = _selftest()
    if st:
        print("🛑 SELBSTTEST FEHLGESCHLAGEN – keine Änderung.")
        for e in st:
            print(f"   {e}")
        return 2
    print(f"✅ Selbsttest ok · Modus: {'FIX' if DO_FIX else 'CHECK'}")

    arts = load_articles()
    results = []
    fixed = 0
    title_changed_slugs = []

    for a in arts:
        before_title = a["title"]
        actions = []
        if DO_FIX:
            ch, actions = heal_article(a)
            if ch:
                fixed += 1
            if a["title"] != before_title:
                title_changed_slugs.append(a["slug"])
        issues = audit_article(a)
        results.append({
            "slug": a["slug"],
            "draft": a["draft"],
            "issues": issues,
            "actions": actions,
            "title": a["title"],
            "tl": len(a["title"]),
            "dl": len(a["description"]),
            "kw": len(a["keywords"]),
        })

    cover_note = "nicht angefasst"
    if DO_FIX:
        # Cover-Pipeline
        print("== Cover-Pipeline ==")
        try:
            if FORCE_COVERS:
                regenerate_covers(force_all=True)
                cover_note = "alle neu (--force-covers)"
            elif title_changed_slugs:
                regenerate_covers(slugs=title_changed_slugs)
                # fehlende Covers nachziehen
                regenerate_covers()
                cover_note = f"{len(title_changed_slugs)} Titel-Stale + fehlende nachgezogen"
            else:
                regenerate_covers()
                cover_note = "fehlende nachgezogen"
            run_subprocess([os.path.join(BLOG_DIR, "scripts", "check_covers.py"), "--fix"])
        except Exception as exc:
            cover_note = f"Fehler: {exc}"
            print(f"  ⚠ Cover-Pipeline: {exc}")

        # Nach Cover-Lauf nur generische Alts final syncen
        print("== Cover-Alt Final-Sync ==")
        for a in load_articles():
            if not a["title"]:
                continue
            bad = (
                not a["alt"]
                or a["alt"].startswith("Spar-Tipp:")
                or a["alt"] == "Tipp von FranksFinanzcheck"
                or "2026 08" in a["alt"]
                or re.search(r"\b20\d{2}\s+0\d\s+\d{2}\b", a["alt"] or "")
                or len(a["alt"] or "") < 12
            )
            if bad:
                c = fm_set_cover_alt(a["content"], a["title"])
                if c != a["content"]:
                    open(a["path"], "w", encoding="utf-8").write(c)
                    print(f"  ✓ Alt-Sync {a['slug']}")

        # Re-Audit nach Fixes
        results = []
        for a in load_articles():
            results.append({
                "slug": a["slug"],
                "draft": a["draft"],
                "issues": audit_article(a),
                "actions": [],
                "title": a["title"],
                "tl": len(a["title"]),
                "dl": len(a["description"]),
                "kw": len(a["keywords"]),
            })

    write_report(results, fixed, cover_note)

    open_n = sum(len(r["issues"]) for r in results)
    print("=" * 60)
    print(f"Pinterest/Google-SEO-Healer: {len(results)} Artikel | "
          f"geheilt: {fixed} | offen: {open_n}")
    for r in results:
        if r["issues"]:
            print(f"  ⚠️ {r['slug']}: {', '.join(r['issues'][:3])}")
        else:
            print(f"  ✅ {r['slug']}  [T:{r['tl']} D:{r['dl']} K:{r['kw']}]")
    print(f"Report: {REPORT}")

    if AS_JSON:
        print(json.dumps({"articles": len(results), "fixed": fixed,
                          "open": open_n, "details": results},
                         ensure_ascii=False, indent=2))
    return 1 if open_n else 0


if __name__ == "__main__":
    sys.exit(main())
