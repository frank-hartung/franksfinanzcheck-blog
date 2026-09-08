#!/usr/bin/env python3
# ============================================================
#  KI-REDAKTION – gemeinsame Helfer (Stufe 0)
#  ------------------------------------------------------------
#  Gemeinsame Bausteine für die drei Rollen der Blog-Automatik
#  nach dem Schema Claude/ChatGPT/Jasper:
#
#    claude_writer.py  → Rolle „Claude":    lange Premium-Artikel
#    news_writer.py    → Rolle „ChatGPT":   schnelle News-Kompakt
#    jasper_seo.py     → Rolle „Jasper":    SEO-Pass (deterministisch)
#
#  KOSTEN-REGEL (Dauervorgabe Frank, 08.09.2026): Diese Automatik
#  darf NUR Gratis-Zugänge nutzen (Groq/Gemini – bereits im Repo
#  etabliert). Paid-APIs (Anthropic/OpenAI) werden NIE automatisch
#  verwendet; sie lassen sich nur manuell per Env-Key zuschalten.
# ============================================================
from __future__ import annotations

import datetime
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402

import post_utils  # noqa: E402
from generate_drafts import slugify, yaml_str  # noqa: E402

CONFIG_FILE = os.path.join(BLOG_DIR, "data", "ki_redaktion.yaml")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")
AKTUELLE_FILE = os.path.join(BLOG_DIR, "data", "aktuelle_entwicklungen.yaml")
REPORT_FILE = os.path.join(BLOG_DIR, "KI-REDAKTION-REPORT.md")
AUTHOR = os.environ.get("BLOG_AUTHOR") or "Frank Hartung"
AFFILIATE_URL = (os.environ.get("AFFILIATE_URL")
                 or "https://a.check24.net/misc/click.php?pid=80968&aid=18")

DISCLOSURE = (
    "**Transparenz:** Dieser Artikel enthält Affiliate-Links (Werbung). "
    "Beim Abschluss über einen Link erhalten wir eine Provision – für dich "
    "entstehen keine Mehrkosten."
)

DISCLAIMER = (
    "_Wichtiger Hinweis: Dieser Artikel dient ausschließlich der "
    "allgemeinen Information und stellt keine Anlage-, Rechts- oder "
    "Steuerberatung dar. Prüfe Konditionen und Bedingungen immer beim "
    "jeweiligen Anbieter._"
)

DEFAULT_CONFIG = {
    # Gratis-Provider zuerst (Kosten-Regel). Paid-Anbieter nur, wenn
    # jemand bewusst einen Key hinterlegt UND hier freischaltet.
    "anbieter_kette_lang": ["groq", "gemini"],
    "anbieter_kette_news": ["groq", "gemini"],
    "zeichenvorgabe_lang": {"min": 11000, "ziel": 14000, "max": 18000},
    "zeichenvorgabe_news": {"min": 10500, "ziel": 12000, "max": 15000},
    "auto_veroeffentlichen": False,   # Dauervorgabe: NIE automatisch live
    "max_artikel_pro_lauf": 1,
}


def load_config() -> dict:
    """Konfiguration laden (mit sicheren Defaults, nie crashen)."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as fh:
                cfg.update(yaml.safe_load(fh) or {})
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ ki_redaktion.yaml nicht lesbar ({e}) – Defaults aktiv.")
    return cfg


def _load_yaml(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001
        return None


def existing_titles() -> set:
    """Alle bereits verwendeten Titel (Kleinschreibung), Duplikat-Schutz."""
    titles = set()
    for path in post_utils.list_post_paths():
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(4000)
        except OSError:
            continue
        m = re.search(r'(?m)^title:\s*"?(.+?)"?\s*$', head)
        if m:
            titles.add(m.group(1).strip().lower())
    return titles


def pick_topic(pillar: str | None = None) -> dict | None:
    """Nächstes freies Thema aus dem kuratierten Pool (data/topics.yaml).

    Deterministisch: erstes Thema des (optional gefilterten) Pools, das
    noch keinen bestehenden Post-Titel belegt. Kein Halluzinations-
    risiko – Themen sind ausschließlich kuratiert.
    """
    data = _load_yaml(TOPICS_FILE) or {}
    topics = data.get("topics") or []
    used = existing_titles()
    for t in topics:
        if pillar and t.get("pillar") != pillar:
            continue
        title = (t.get("title") or "").strip()
        if title and title.lower() not in used:
            return t
    return None


def pick_news_hook(kategorie: str | None = None) -> dict | None:
    """Nächster gültiger News-Aufhänger aus data/aktuelle_entwicklungen.yaml.

    Der Pool ist von Menschen kuratiiert (Anti-Halluzinations-Regel des
    Repos). Einträge außerhalb ihres Gültigkeitsfensters (ab/bis) oder
    bereits verarbeitete (ki_news_used) werden übersprungen.
    """
    entries = _load_yaml(AKTUELLE_FILE)
    if not isinstance(entries, list):
        return None
    today = datetime.date.today().isoformat()
    for e in entries:
        if not isinstance(e, dict) or not e.get("hook"):
            continue
        if kategorie and e.get("kategorie") != kategorie:
            continue
        if e.get("ab") and str(e["ab"]) > today:
            continue
        if e.get("bis") and str(e["bis"]) < today:
            continue
        if e.get("ki_news_used"):
            continue
        return e
    return None


def mark_news_hook_used(hook_id: str) -> None:
    """Verarbeiteten Aufhänger im Pool markieren (idempotent)."""
    if not os.path.exists(AKTUELLE_FILE) or not hook_id:
        return
    try:
        with open(AKTUELLE_FILE, encoding="utf-8") as fh:
            text = fh.read()
        pattern = (r'(- id: ' + re.escape(hook_id)
                   + r'\b(?:(?!^- id:|\Z).)*?)(?=\n- id: |\Z)')

        def add_flag(m):
            block = m.group(1)
            if "ki_news_used" in block:
                return block
            return block.rstrip("\n") + "\n  ki_news_used: true\n"

        new = re.sub(pattern, add_flag, text, count=1, flags=re.S | re.M)
        if new != text:
            with open(AKTUELLE_FILE, "w", encoding="utf-8") as fh:
                fh.write(new)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ Aufhänger konnte nicht markiert werden: {e}")


def unique_bundle_slug(title: str) -> str:
    """Slug mit Datumspräfix; hängt Zähler an, falls schon vorhanden."""
    date = datetime.date.today().isoformat()
    base = f"{date}-{slugify(title)}"
    if not os.path.exists(os.path.join(post_utils.POSTS_DIR, base)):
        return base
    i = 2
    while os.path.exists(os.path.join(post_utils.POSTS_DIR, f"{base}-{i}")):
        i += 1
    return f"{base}-{i}"


def build_frontmatter(*, title, description, tags, pillar=None,
                      keywords=None, rolle="claude", kurzantwort=None,
                      news=False, kategorie=None) -> str:
    """Hugo-Frontmatter nach Repo-Konvention – IMMER draft: true.

    Kein cadence_wait: Damit bleiben die Entwürfe für die Kadenz-
    Automatik unsichtbar (cadence_guard fasst sie nie an). Veröffent-
    licht wird ausschließlich bewusst über ki_redaktion.py --promote.
    """
    date = datetime.datetime.now(datetime.timezone.utc)
    date_str = date.strftime("%Y-%m-%dT%H:%M:%SZ")
    tags = [t for t in (tags or []) if t][:5]
    keywords = [k for k in (keywords or []) if k][:8]
    fm = (
        "---\n"
        f"title: {yaml_str(title)}\n"
        f"description: {yaml_str(description)}\n"
        f"date: {date_str}\n"
        "draft: true\n"
        f"tags: {json.dumps(tags, ensure_ascii=False)}\n"
        + ('categories: ["News"]\n' if news else 'categories: ["Ratgeber"]\n')
        + (f'pillar: "{pillar}"\n' if pillar else "")
        + (f'keywords: {json.dumps(keywords, ensure_ascii=False)}\n'
           if keywords else "")
        + f"author: {yaml_str(AUTHOR)}\n"
        "ai_generated: true\n"
        f'ki_redaktion: "{rolle}"\n'
        'ki_redaktion_status: "review"\n'
        + (f'news_kategorie: "{kategorie}"\n' if news and kategorie else "")
    )
    if kurzantwort:
        fm += f"kurzantwort: {yaml_str(kurzantwort)}\n"
    fm += "---\n\n"
    return fm


def clip_text(text: str, max_len: int = 158) -> str:
    """Schneidet Text an einer Wortgrenze ab (nie mitten im Wort)."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-–") + " …"


def cta_block(affiliate_url: str | None = None) -> str:
    """Affiliate-CTA + Werbekennzeichnung (Hausstil der Engine)."""
    url = affiliate_url or AFFILIATE_URL
    return (
        "\n---\n\n"
        f"👉 **Jetzt vergleichen und sparen:** "
        f"[**→ Jetzt Angebote vergleichen**]({url})\n\n"
        f"*{DISCLOSURE}*\n"
    )


def write_report(lines: list) -> None:
    """Statusreport ins Repo-Root schreiben (Konvention: *-REPORT.md)."""
    stamp = datetime.datetime.now(datetime.timezone.utc)
    head = [
        "# KI-REDAKTION-REPORT",
        "",
        f"_Stand: {stamp.strftime('%d.%m.%Y %H:%M UTC')} – automatisch "
        "durch scripts/ki_redaktion.py erzeugt._",
        "",
    ]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(head + lines).rstrip() + "\n")
