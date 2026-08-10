#!/usr/bin/env python3
"""engine_generate.py – CONTENT-ENGINE v2 (Multi-Fallback-Orchestrierung)

Ersetzt den fragilen Einzel-Lauf der alten Automatisierung durch eine
3-Ebenen-Fallback-Architektur – damit NIE ein Tag ohne neuen Artikel bleibt:

  EBENE 1 (Normal):   KI-Artikel generieren, Profi-Gate hart (wie bisher),
                      max. 3 Versuche mit wechselndem Stil/Perspektive.
  EBENE 2 (Relaxed):  Wenn Ebene 1 scheitert: 2 weitere Versuche mit
                      reduzierter Schwelle (nur HARTE Kriterien: >= 350 Wörter,
                      >= 3 H2, keine KI-Floskeln). Artikel wird trotzdem
                      veröffentlicht – Qualitäts-Gates (Phase 3) polieren nach.
  EBENE 3 (Draft):    Wenn auch das scheitert: Artikel wird als ENTWURF
                      (draft: true) mit Issue-Hinweis gespeichert. Der Tag ist
                      nie verloren, der Mensch kann ihn freigeben.

Zusätzlich:
  - Multi-Modell: Versuch wechselt automatisch zwischen Gemini und Groq
    (AI_PROVIDER wird je Versuch rotiert), falls ein Provider schwächelt.
  - ENGINE-STATUS.md: Zustands-Dashboard mit letztem Lauf, Ebene, Fehlern.
  - Exit-Codes: 0 = ok (auch Draft-Rettung), 1 = kompletter Ausfall (-> Alert).

Aufruf (wie bisherige Bot-Umgebung):
  GROQ_API_KEY=... GEMINI_API_KEY=... AFFILIATE_URL=... MAX_ARTIKEL_PRO_TAG=2 \
  PIN_TOPICS=1 python3 scripts/engine_generate.py
"""
import datetime
import os
import random
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import generate_drafts as g  # noqa: E402  (nutzt bestehende Generierungs-Logik)

STATUS_FILE = os.path.join(BLOG_DIR, "ENGINE-STATUS.md")

# ---------------------------------------------------------------------------
# Status-Dashboard
# ---------------------------------------------------------------------------

def write_status(line_extra=None, level="OK"):
    """Schreibt ENGINE-STATUS.md (kurz, menschenlesbar, commit-freundlich)."""
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    lines = [
        "# 🤖 ENGINE-STATUS (Content-Engine v2)",
        "",
        f"**Letzter Lauf:** {now}",
        f"**Status:** {level}",
    ]
    if line_extra:
        lines += ["", line_extra]
    lines += [
        "",
        "_Wird bei jedem Lauf der Content-Engine v2 aktualisiert._",
        "",
    ]
    with open(STATUS_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return STATUS_FILE


# ---------------------------------------------------------------------------
# Hilfsfunktionen: Frontmatter + Datei speichern
# ---------------------------------------------------------------------------

def yaml_quote(value: str) -> str:
    """Quoted einen Wert YAML-sicher (Doppelpunkte, Sonderzeichen).
    Verhindert Frontmatter-Build-Fehler wie 'inspiration: Text: Mehr'."""
    if value is None:
        return '""'
    v = str(value)
    if ":" in v or "#" in v or v.startswith((" ", "-", "?", "!")) or v != v.strip():
        return '"' + v.replace('"', '\\"') + '"'
    return v


def save_article(title, desc, body, draft=False, inspiration=None):
    """Speichert Artikel als Page-Bundle (Format wie bisherige Pipeline)."""
    date = datetime.date.today().isoformat()
    slug = g.slugify(title)
    bundle_dir = os.path.join(g.POSTS_DIR, f"{date}-{slug}")
    if os.path.exists(bundle_dir):
        i = 2
        while os.path.exists(f"{bundle_dir}-{i}"):
            i += 1
        bundle_dir = f"{bundle_dir}-{i}"
        slug = f"{slug}-{i}"
    os.makedirs(bundle_dir, exist_ok=True)
    filename = os.path.join(bundle_dir, "index.md")

    affiliate_url = g.AFFILIATE_URL
    cta = (
        "\n---\n\n"
        f"👉 **Jetzt vergleichen und sparen:** [**→ Jetzt Angebote vergleichen**]({affiliate_url})\n\n"
        "*Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link "
        "erhalten wir eine Provision – für dich entstehen keine Mehrkosten.*\n"
    )
    insp_line = ""
    if inspiration:
        insp_line = f"\ninspiration: {yaml_quote(inspiration)}\n"
    draft_line = "true" if draft else "false"
    frontmatter = (
        "---\n"
        f'title: {yaml_quote(title)}\n'
        f'description: {yaml_quote(desc)}\n'
        f"date: {date}T12:00:00Z\n"
        f"draft: {draft_line}\n"
        'tags: []\n'
        'categories: ["Ratgeber"]\n'
        'pillar: "konto-karten"\n'
        "author: \"Frank\"\n"
        "ai_generated: true\n"
        f'ai_provider: "Content-Engine v2"\n'
        f"engine_level: \"{'draft' if draft else 'relaxed'}\"\n"
        f"{insp_line}"
        "---\n"
    )
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(frontmatter + body.strip() + "\n" + cta)
    return filename, slug


# ---------------------------------------------------------------------------
# Ebene 1 + 2: Generieren mit Qualitäts-Schleife (hart / relaxed)
# ---------------------------------------------------------------------------

def try_generate(topic, keywords, pin, used_titles, relaxed=False, max_attempts=3):
    """Ein Generierungs-Versuch über beide Provider. Liefert (filename|None, info)."""
    providers = [p for p in ("GEMINI", "GROQ") if os.environ.get(f"{p}_API_KEY")]
    if not providers:
        return None, "kein API-Key"
    random.shuffle(providers)  # Modell-Rotation gegen Provider-Schwäche

    for attempt in range(1, max_attempts + 1):
        provider = providers[(attempt - 1) % len(providers)]
        os.environ["AI_PROVIDER"] = provider
        angle = random.choice(g.ANGLES)
        perspective = random.choice(g.PERSPECTIVES)
        try:
            raw, provider_name = g.generate_article_text(
                topic, angle, perspective=perspective, pin=pin,
                keywords=keywords,
            )
        except Exception as exc:  # noqa: BLE001 – kein Abbruch bei Provider-Fehler
            print(f"  ✗ Provider-Fehler ({provider}): {exc}")
            continue
        if not raw:
            continue
        title, desc, body = g.parse_article(raw, topic, angle[0])
        if not title or not body:
            continue
        if title.lower() in used_titles:
            print(f"  ✗ Titel existiert bereits: {title[:50]}…")
            continue

        if not relaxed:
            ok_profi, prob = g.profi_quality_ok(body, keywords)
            if not ok_profi:
                print(f"  ⚠ Profi-Gate: {'; '.join(prob[:3])} (Versuch {attempt}/{max_attempts}, {provider})")
                continue
        else:
            # Relaxed: nur HARTE Kriterien (Text darf trotzdem nicht mager sein)
            text = re.sub(r"[#*_>`|~\[\]()-]", " ", body)
            words = len(re.findall(r"\w+", text))
            h2 = len(re.findall(r"^##\s", body, re.M))
            floskeln = [f for f in g.PROFI_FLOSKELN if f in text.lower()]
            if words < 350 or h2 < 3 or floskeln:
                print(f"  ⚠ Relaxed-Gate: {words} Wörter / {h2} H2 / Floskeln {floskeln[:2]} (Versuch {attempt})")
                continue

        used_titles.add(title.lower())
        return (title, desc, body), f"OK via {provider_name} ({'relaxed' if relaxed else 'profi'})"
    return None, f"{max_attempts} Versuche ohne Erfolg"


# ---------------------------------------------------------------------------
# Ebene 3: Draft-Rettung (nie ein Tag ohne Content)
# ---------------------------------------------------------------------------

def make_draft(topic, used_titles):
    """Erzeugt aus dem Thema einen minimalen, ehrlichen Entwurf (draft: true)."""
    title = topic.get("title", "Finanz-Thema des Tages")
    if title.lower() in used_titles:
        title = f"{title} – Kurzfassung"
    date = datetime.date.today().isoformat()
    body = (
        f"## Worum geht es?\n\n"
        f"Dieser Beitrag behandelt: **{title}**. Die vollständige Ausarbeitung "
        f"wurde von der Content-Engine am {date} als Entwurf gesichert, weil die "
        f"automatische Qualitätsprüfung die Profi-Schwelle nicht erreicht hat.\n\n"
        f"## Erste Kernpunkte\n\n"
        f"- Relevanz für den Alltag prüfen\n"
        f"- Sparpotenzial konkret beziffern\n"
        f"- Schritt-für-Schritt-Anleitung ergänzen\n"
        f"- FAQ mit 3–5 Fragen vervollständigen\n\n"
        f"## Nächster Schritt\n\n"
        f"Der Artikel wird in der nächsten Qualitäts-Runde fertiggestellt und "
        f"veröffentlicht.\n"
    )
    return title, "", body


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    max_per_day = int(os.environ.get("MAX_ARTIKEL_PRO_TAG", "2"))
    pin_topics = os.environ.get("PIN_TOPICS", "0") == "1"

    # Tages-Guard (wie bisherige Pipeline)
    today = datetime.date.today().isoformat()
    published_today = 0
    for path in g.list_post_paths():
        if os.path.basename(os.path.dirname(path)).startswith(today):
            content = open(path, encoding="utf-8").read()
            if "draft: false" in content:
                published_today += 1
    if published_today >= max_per_day:
        print(f"Bereits {published_today}/{max_per_day} Artikel heute – nichts zu tun.")
        write_status(f"Tageslimit erreicht ({published_today}/{max_per_day}).")
        return 0

    used_titles = g.existing_titles()
    if pin_topics:
        topics = g.load_pin_topics()
        quelle = "Pinterest-Plan"
        freie = [t for t in topics if not g.topic_already_covered(t["title"], used_titles)]
        if not freie:
            topics = g.load_topics()
            quelle = "Themenpool"
    else:
        topics = g.load_topics()
        quelle = "Themenpool"
    freie = [t for t in topics if not g.topic_already_covered(t["title"], used_titles)]
    if not freie:
        print("Themenpool erschöpft – KI-Nachschub startet …")
        try:
            g.refill_topics(g.load_topics(), used_titles)
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ refill fehlgeschlagen: {exc}")
        topics = g.load_topics()
        freie = [t for t in topics if not g.topic_already_covered(t["title"], used_titles)]
    if not freie:
        print("✗ Keine freien Themen – Abbruch.")
        write_status("Keine freien Themen verfügbar.", level="FAIL")
        return 1

    topic = random.choice(freie)
    keywords = topic.get("keywords")
    pin = None
    if pin_topics:
        try:
            pin = g.find_pin_for_topic(topic.get("title"), g.load_pinterest_plan())
        except Exception:  # noqa: BLE001
            pin = None

    print(f"Content-Engine v2 gestartet – Quelle: {quelle}, Thema: {topic['title'][:60]}")

    # EBENE 1 – Profi
    result, info = try_generate(topic, keywords, pin, used_titles, relaxed=False, max_attempts=3)
    level = "profi"
    # EBENE 2 – Relaxed
    if not result:
        print("→ Ebene 2 (Relaxed) …")
        result, info = try_generate(topic, keywords, pin, used_titles, relaxed=True, max_attempts=2)
        level = "relaxed"
    # EBENE 3 – Draft-Rettung
    draft_saved = False
    if not result:
        print("→ Ebene 3 (Draft-Rettung) …")
        title, desc, body = make_draft(topic, used_titles)
        try:
            filename, slug = save_article(title, desc, body, draft=True,
                                          inspiration=topic.get("title"))
            draft_saved = True
            print(f"  ✓ Entwurf gesichert: {slug} (draft: true)")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Draft konnte nicht gespeichert werden: {exc}")
            write_status("Kompletter Ausfall – kein Artikel, kein Draft.", level="FAIL")
            return 1

    if result and not draft_saved:
        title, desc, body = result
        try:
            filename, slug = save_article(title, desc, body, draft=False,
                                          inspiration=topic.get("title"))
            print(f"  ✓ Artikel veröffentlicht ({level}): {slug}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Speichern fehlgeschlagen: {exc}")
            write_status("Kompletter Ausfall – Speicherfehler.", level="FAIL")
            return 1

    status_line = (f"Thema: {topic['title'][:60]} | Ebene: {level} | "
                   f"{'Entwurf gesichert' if draft_saved else 'veröffentlicht'} | {info}")
    write_status(status_line, level="OK" if not draft_saved else "DRAFT")
    return 0


if __name__ == "__main__":
    sys.exit(main())
