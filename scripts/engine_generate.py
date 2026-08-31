#!/usr/bin/env python3
"""engine_generate.py – CONTENT-ENGINE v2 (Multi-Fallback-Orchestrierung)

Ersetzt den fragilen Einzel-Lauf der alten Automatisierung durch eine
3-Ebenen-Fallback-Architektur – damit NIE ein Tag ohne neuen Artikel bleibt:

  EBENE 1 (Normal):   KI-Artikel generieren, Profi-Gate hart (wie bisher),
                      max. 3 Versuche mit wechselndem Stil/Perspektive.
  EBENE 2 (Relaxed):  Wenn Ebene 1 scheitert: 2 weitere Versuche mit
                      reduzierter Schwelle (nur HARTE Kriterien: >= 550 Wörter,
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

Kadenz (DAUERVORGABE, Frank, 19.08.2026):
  - Publikation NUR montags, mittwochs, freitags (harter Wochentags-Guard,
    gilt auch für workflow_dispatch; Notfall: FORCE_PUBLISH_ANY_DAY=1).
  - 2-3 Artikel pro Publikationstag: MIN_ARTIKEL_PRO_TAG (Default 2) bis
    MAX_ARTIKEL_PRO_TAG (Default 3) – die Schleife füllt das Tageslimit auf,
    Entwürfe zählen mit. Dauervorgabe-Floor: Werte unter 2 werden auf 2
    angehoben (Workflow-Legacy-Fallback „1" kann die Kadenz nicht drücken).

Aufruf (wie bisherige Bot-Umgebung):
  GROQ_API_KEY=... GEMINI_API_KEY=... AFFILIATE_URL=... MAX_ARTIKEL_PRO_TAG=3 \
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
from check_titles import COMPOUND_FIXES, TIME_TAIL as RE_ANHAENGSEL  # noqa: E402 – Titel-Qualitätsgate (FrankAutoOps)
from post_utils import safe_title_cut  # noqa: E402 – Wortgrenzen-Kürzung (nie Wortbruch)
import cadence_guard  # noqa: E402 – Single Source of Truth für die Kadenz


def normalize_title(title: str) -> str:
    """Deterministische Titel-Normalisierung (FrankAutoOps-Gate R2):
    behebt bekannte Komposita-Schreibfehler ('Riester Rente' -> 'Riester-Rente')
    per Regex (Wortgrenzen), damit fehlerhafte Titel gar nicht erst entstehen."""
    import re as _re
    for pat, repl in COMPOUND_FIXES:
        title = _re.sub(pat, repl, title)
    return title

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


def now_utc_iso() -> str:
    """Aktuelle UTC-Zeit als ISO-String (1 Minute zurück – NIE ein
    Future-Post, der von Hugo nicht gebaut würde)."""
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def save_article(title, desc, body, draft=False, inspiration=None, pillar=None,
                 keywords=None, pinwand=None, pin_title=None, pin_description=None,
                 level="profi"):
    """Speichert Artikel als Page-Bundle (Format wie bisherige Pipeline).

    Schreibt von Anfang an Pinterest-/Google-SEO-Felder (keywords, pin_*),
    damit der Healer und die Pin-Engine sofort greifen.

    Premium (25.08.2026): Bei Plan-Themen übernimmt die Funktion die
    kuratierten Masterplan-Texte (pin_title/pin_description) und die
    pinwand für das Multi-Board-Routing – gültige Premium-Texte haben
    Vorrang vor dem deterministischen Build.
    """
    date = datetime.date.today().isoformat()
    # Titel-Gate vor Speichern (Doppelpunkt-Konvention für Cover)
    try:
        from pinterest_seo_healer import (
            ensure_colon_title, strip_ellipsis, keywords_from_title,
            build_pin_title, build_pin_description, extend_description,
        )
        title = ensure_colon_title(strip_ellipsis(normalize_title(title)))
        # SERP-Kappung NUR an Wortgrenzen (safe_title_cut) – harte
        # [:60]-Slices haben Titel mitten im Wort kaputtgeschnitten
        # ("…Tarife – Gastari") und damit die Cover-Texte unvollständig
        # gemacht (Befund 26.08.2026).
        if len(title) > 60:
            title = safe_title_cut(title, 60)
        kws = keywords_from_title(title, keywords or [])
        desc = extend_description(desc or "", kws, title)
        pin_t = build_pin_title(title)
        pin_d = build_pin_description(title, desc, kws, g.slugify(title))
        # Premium-Pin-Texte aus dem Masterplan (wenn gültig) VOR den Build
        # (Titel: & erlaubt – nur Beschreibungen werden &-frei saniert)
        if pin_title and len(pin_title) <= 100:
            pin_t = pin_title.strip()
        if pin_description:
            d = re.sub(r"\s+", " ", str(pin_description).strip()).replace("&", "und")
            if not d.startswith("*Werbung"):
                d = f"*Werbung | {d}"
            if 40 <= len(d) <= 500:
                pin_d = d[:500]
    except Exception as _seo_err:
        print(f"  ⚠ SEO-Preflight übersprungen: {_seo_err}")
        kws = list(keywords or [])[:5] or [title.split(":")[0].strip() or "Geld sparen"]
        while len(kws) < 3:
            kws.append("Geld sparen")
        pin_t = title[:100]
        pin_d = f"*Werbung | {(desc or title)[:350]} Mehr Spartipps auf FranksFinanzcheck!"

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
    kw_yaml = "[" + ", ".join(f'"{k}"' for k in kws[:8]) + "]"
    tag_yaml = "[" + ", ".join(f'"{k}"' for k in kws[:4]) + "]"
    pinwand_line = f"pinwand: {yaml_quote(pinwand)}\n" if pinwand else ""
    frontmatter = (
        "---\n"
        f'title: {yaml_quote(title)}\n'
        f'description: {yaml_quote(desc)}\n'
        f"date: {now_utc_iso()}\n"
        f"draft: {draft_line}\n"
        f"tags: {tag_yaml}\n"
        'categories: ["Ratgeber"]\n'
        'pillar: "' + (pillar or "konto-karten") + '"\n'
        "author: \"Frank Hartung\"\n"
        f"keywords: {kw_yaml}\n"
        f"{pinwand_line}"
        f'pin_title: {yaml_quote(pin_t)}\n'
        f'pin_description: {yaml_quote(pin_d)}\n'
        "ai_generated: true\n"
        f'ai_provider: "Content-Engine v2"\n'
        f"engine_level: \"{'draft' if draft else level}\"\n"
        f"{insp_line}"
        "---\n"
    )
    body = re.sub(r"^\s*# [^\n]+\n+", "", body.strip(), count=1)
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
        title = normalize_title(title)  # FrankAutoOps R3: Komposita-Fixes
        if title.lower() in used_titles:
            print(f"  ✗ Titel existiert bereits: {title[:50]}…")
            continue
        # FrankAutoOps R2: lose Anhängsel ("… dieses Jahr") ohne Doppelpunkt
        # sind harte Titel-Verstöße -> Versuch verwerfen, neu generieren
        if ":" not in title and RE_ANHAENGSEL.search(title):
            print(f"  ✗ Titel-Gate R2: Anhängsel-Muster ohne ':' – Versuch {attempt} verworfen: {title[:60]}")
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
            if words < 1400 or h2 < 5 or floskeln:
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

# DAUERVORGABE (Frank, 19.08.2026): Der Blog veröffentlicht AUSSCHLIESSLICH
# montags, mittwochs und freitags (Mo=0, Mi=2, Fr=4) – 2 bis 3 Artikel pro
# Publikationstag. Dieser Wochentags-Guard gilt auch für manuelle
# workflow_dispatch-Läufe. Notfall-Override (z. B. Nachhol-Bedarf):
#   FORCE_PUBLISH_ANY_DAY=1
# Tagesziel: MIN_ARTIKEL_PRO_TAG (Default 2) bis MAX_ARTIKEL_PRO_TAG
# (Default 3) – steuerbar über die gleichnamigen Env-Variablen /
# GitHub-Actions-Variablen.
#
# WICHTIG (26.08.2026): PUBLICATION_DAYS kommt aus cadence_guard.py –
# der EINEN Kadenz-Definition für Engine, Guards und Deploy-Gate.
# (Die frühere lokale Kopie hier konnte sich davon driften.)
PUBLICATION_DAYS = cadence_guard.PUBLICATION_DAYS


def count_articles_today():
    """Zaehlt alle HEUTE VERÖFFENTLICHTE Artikel (live UND Entwurf) –
    Entwuerfe zaehlen mit, sonst wuerde die Schleife bei schwacher KI
    beliebig viele Drafts ablegen.

    Gezählt wird über das Frontmatter-`date:`-Feld (Single Source of
    Truth, s. cadence_guard) – nicht über den Ordner-Datumspräfix, der
    bei Re-Queue/Re-Dating (heilende Wachen) bewusst alt bleibt."""
    today = datetime.date.today().isoformat()
    n = 0
    for p in cadence_guard.load_posts():
        if p["date"].isoformat() == today:
            n += 1
    return n


# ---------------------------------------------------------------------------
#  RECYCLING ZÄHLT NICHT ALS NEUPRODUKTION  (Fix 29.08.2026)
#  ---------------------------------------------------------------------------
#  DEADLOCK-BEFUND (Issue #97): requeue_to_capacity() durfte die komplette
#  Tageskapazität mit umdatierten Alt-Posts (cadence_wait) füllen. Der
#  Tages-Guard zählte diese anschließend als Produktion -> der Erzeugungs-
#  Loop lief nie an -> 0 neue Artikel, an JEDEM Publikationstag.
#  Sichtbar wurde das nur indirekt: ENGINE-STATUS.md meldete
#  "Tageslimit erreicht (2/2)", während nichts Neues mehr entstand.
#
#  Gegenmaßnahme, zweistufig:
#    1. RESERVE: MIN_NEUE_PRO_TAG Slot(s) bleiben für echte neue Artikel
#       frei – die Re-Queue darf sie nicht auffüllen.
#    2. TRENNUNG: Die Tagesbilanz unterscheidet "neu" und "recycelt".
#       Nur "neu" erfüllt das Produktionsziel. Ein Tag mit 0 neuen
#       Artikeln wird als DEADLOCK gemeldet, nicht als Erfolg.
# ---------------------------------------------------------------------------
MIN_NEUE_PRO_TAG = int(os.environ.get("MIN_NEUE_PRO_TAG") or "1")


def ist_recycelt(post, promoted_slugs):
    """Ein heute datierter Post gilt als RECYCLING, wenn

      a) er in DIESEM Lauf von requeue_to_capacity() aus der
         Warteschlange promotet wurde, ODER
      b) sein Ordner-Datumspräfix nicht zum `date:`-Feld passt.

    (b) ist der eigentlich wichtige Fall: Pro Publikationstag laufen
    DREI Engine-Slots (06:10 / 14:10 / 17:40 UTC). Was Slot 06:10
    recycelt hat, muss Slot 14:10 ebenfalls als Recycling erkennen –
    sonst zählt der zweite Slot die Wiederverwertung des ersten als
    Neuproduktion und stoppt (derselbe Deadlock, nur eine Slot-Ebene
    später).

    Hintergrund zu (b): Bei Re-Queue/Re-Dating bleibt der Ordnerpräfix
    bewusst alt (stabile URLs, Covers, interne Links) – nur das
    `date:`-Feld wird auf heute gesetzt. Genau diese Divergenz ist das
    verlässliche, dauerhafte Erkennungsmerkmal.

    Fehlklassifikation ist bewusst FAIL-SAFE: ein fälschlich als
    „recycelt" geltender neuer Artikel führt zu MEHR Produktion
    (nach oben durch das Tageslimit gedeckelt) – nicht zum Stillstand.
    """
    if post["slug"] in promoted_slugs:
        return True
    m = re.match(r"(\d{4}-\d{2}-\d{2})", post["slug"])
    if not m:
        return False          # kein Präfix -> nicht bewertbar -> zählt als neu
    try:
        return datetime.date.fromisoformat(m.group(1)) != post["date"]
    except ValueError:
        return False


def tages_bilanz(posts, promoted_slugs, max_per_day, min_per_day):
    """Trennt ECHTE Neuproduktion von recycelten Re-Queue-Posts.

    Bewusst rein (keine Seiteneffekte) -> regressionstestbar.
    """
    today = datetime.date.today().isoformat()
    heute = [p for p in posts if p["date"].isoformat() == today]
    recycelt = [p for p in heute if ist_recycelt(p, promoted_slugs)]
    neu = [p for p in heute if not ist_recycelt(p, promoted_slugs)]
    return {
        "total": len(heute),
        "neu": len(neu),
        "recycelt": len(recycelt),
        "recycle_kapazitaet": max(0, max_per_day - MIN_NEUE_PRO_TAG),
        "ziel_neu": min_per_day,
        "slots_frei": max(0, max_per_day - len(heute)),
        "neu_noetig": max(0, min_per_day - len(neu)),
    }


def produktions_entscheidung(bilanz, max_per_day, min_per_day):
    """Entscheidet, ob (noch) ein neuer Artikel erzeugt werden muss.

    Liefert (entscheidung, meldung); entscheidung ist
    'WEITER' | 'STOP' | 'DEADLOCK'.
    """
    if bilanz["neu"] == 0 and bilanz["total"] >= max_per_day:
        return ("DEADLOCK",
                f"RECYCLE-DEADLOCK: {bilanz['total']}/{max_per_day} Posts heute sind "
                f"ausschließlich Re-Queue-Recycling – 0 neue Artikel. "
                f"Warteschlange (cadence_wait) prüfen bzw. MIN_NEUE_PRO_TAG erhöhen.")
    if bilanz["total"] >= max_per_day:
        return ("STOP",
                f"Tageslimit erreicht ({bilanz['total']}/{max_per_day} · "
                f"{bilanz['neu']} neu, {bilanz['recycelt']} recycelt).")
    if bilanz["neu"] >= min_per_day:
        return ("STOP",
                f"Neuproduktion erfüllt ({bilanz['neu']}/{min_per_day} neu, "
                f"{bilanz['recycelt']} recycelt, {bilanz['total']}/{max_per_day} gesamt).")
    return ("WEITER",
            f"{bilanz['slots_frei']} Slot(s) frei, "
            f"{bilanz['neu_noetig']} neue Artikel nötig.")


def publish_one_article(topics, quelle, pin_topics, used_titles, used_topics):
    """Erzeugt EINEN Artikel (Profi -> Relaxed -> Draft-Rettung).
    Liefert (level, draft_saved) oder None bei fatalem Fehler."""
    freie = [t for t in topics
             if not g.topic_already_covered(t["title"], used_titles)
             and id(t) not in used_topics]
    if not freie:
        print("Themenpool erschöpft – KI-Nachschub startet …")
        try:
            g.refill_topics(g.load_topics(), used_titles)
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ refill fehlgeschlagen: {exc}")
        topics = g.load_topics()
        freie = [t for t in topics
                 if not g.topic_already_covered(t["title"], used_titles)
                 and id(t) not in used_topics]
    if not freie:
        print("✗ Keine freien Themen – Abbruch.")
        return None

    topic = random.choice(freie)
    used_topics.add(id(topic))
    keywords = topic.get("keywords")
    pin = None
    if pin_topics:
        try:
            pin = g.find_pin_for_topic(topic.get("title"), g.load_pinterest_plan())
        except Exception:  # noqa: BLE001
            pin = None

    print(f"Content-Engine v2 – Quelle: {quelle}, Thema: {topic['title'][:60]}")

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
            filename, slug = save_article(
                title, desc, body, draft=True,
                inspiration=topic.get("title"), pillar=topic.get("pillar"),
                keywords=keywords,
                pinwand=topic.get("pinwand"),
                pin_title=topic.get("pin_titel"),
                pin_description=topic.get("pin_beschreibung"),
                level="draft",
            )
            used_titles.add(title.lower())  # Draft-Thema nicht doppelt ziehen
            draft_saved = True
            print(f"  ✓ Entwurf gesichert: {slug} (draft: true)")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Draft konnte nicht gespeichert werden: {exc}")
            write_status("Kompletter Ausfall – kein Artikel, kein Draft.", level="FAIL")
            return None

    if result and not draft_saved:
        title, desc, body = result
        try:
            filename, slug = save_article(
                title, desc, body, draft=False,
                inspiration=topic.get("title"), pillar=topic.get("pillar"),
                keywords=keywords,
                pinwand=topic.get("pinwand"),
                pin_title=topic.get("pin_titel"),
                pin_description=topic.get("pin_beschreibung"),
                level=level,
            )
            print(f"  ✓ Artikel veröffentlicht ({level}): {slug}")
        except Exception as exc:  # noqa: BLE001
            print(f"  ✗ Speichern fehlgeschlagen: {exc}")
            write_status("Kompletter Ausfall – Speicherfehler.", level="FAIL")
            return None

    status_line = (f"Thema: {topic['title'][:60]} | Ebene: {level} | "
                   f"{'Entwurf gesichert' if draft_saved else 'veröffentlicht'} | {info}")
    print(f"  → {status_line}")
    return level, draft_saved, status_line


def main():
    max_per_day = int(os.environ.get("MAX_ARTIKEL_PRO_TAG") or "3")
    min_per_day = int(os.environ.get("MIN_ARTIKEL_PRO_TAG") or "2")
    # DAUERVORGABE-Floor: An Publikationstagen (Mo/Mi/Fr) erscheinen MINDESTENS
    # 2 Artikel. Der Workflow-Legacy-Fallback „1“ (vars.MAX_ARTIKEL_PRO_TAG
    # leer) darf die Kadenz nicht unter das Mindestziel drücken; wer weniger
    # will, ändert zuerst die Dauervorgabe (CADENCE-REPORT.md). Die Variablen
    # im Repo (Settings → Actions → Variables) können das Ziel nur ANHEBEN:
    # empfohlen MAX_ARTIKEL_PRO_TAG=3 und MIN_ARTIKEL_PRO_TAG=2.
    if max_per_day < 2:
        max_per_day = 2
    if min_per_day < 2:
        min_per_day = 2
    if min_per_day > max_per_day:
        min_per_day = max_per_day
    pin_topics = os.environ.get("PIN_TOPICS", "0") == "1"

    # Wochentags-Guard (DAUERVORGABE: nur Mo/Mi/Fr publizieren)
    weekday = datetime.date.today().weekday()
    if weekday not in PUBLICATION_DAYS and os.environ.get("FORCE_PUBLISH_ANY_DAY") != "1":
        day = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"][weekday]
        print(f"Kein Publikationstag ({day}) – Mo/Mi/Fr-Vorgabe: nichts zu tun.")
        write_status(f"Kein Publikationstag ({day}) – Publikation nur Mo/Mi/Fr (2-3 Artikel).")
        return 0

    # KADENZ-Selbstheilung (26.08.2026): Posts aus der Re-Queue
    # (cadence_wait: true) bis zum Tageslimit promoten. Das ist die
    # Content-Seite des Heil-Kreises: Artikel, die cadence_guard --fix
    # wegen eines Kadenz-Verstoßes offline genommen hat (Deploy-Gate,
    # Blog-Health, Engine-Preflight), gehen hier am nächsten
    # Publikationstag wieder live – IMMER innerhalb des Tageslimits
    # (2–3), mit neuem Veröffentlichungsdatum. Der Loop unten füllt
    # den Rest des Tages mit neuen Artikeln auf.
    promoted_slugs = set()
    try:
        # RESERVE (Fix 29.08.2026): mindestens MIN_NEUE_PRO_TAG Slot(s)
        # bleiben für echte Neuproduktion frei – sonst erstickt die
        # Re-Queue die Engine (Deadlock, s. tages_bilanz).
        recycle_kap = max(0, max_per_day - MIN_NEUE_PRO_TAG)
        promoted = cadence_guard.requeue_to_capacity(
            cadence_guard.load_posts(), recycle_kap)
        promoted_slugs = {p["slug"] for p in promoted}
        if promoted:
            print(f"♻️ Cadence-Re-Queue: {len(promoted)} Post(s) wieder live "
                  f"(Recycle-Kapazität {recycle_kap} · "
                  f"Reserve für neue Artikel: {MIN_NEUE_PRO_TAG}).")
    except Exception as exc:  # noqa: BLE001 – Heilung darfs nicht bremsen
        print(f"⚠ Cadence-Re-Queue fehlgeschlagen (nicht kritisch): {exc}")

    # Tages-Guard (NEU 29.08.2026: trennt echte Produktion von Recycling)
    bilanz = tages_bilanz(cadence_guard.load_posts(), promoted_slugs,
                          max_per_day, min_per_day)
    entscheidung, meldung = produktions_entscheidung(bilanz, max_per_day, min_per_day)
    if entscheidung != "WEITER":
        print(meldung)
        write_status(meldung,
                     level=("WARN" if entscheidung == "DEADLOCK" else "OK"))
        return 0

    used_titles = g.existing_titles()
    used_topics = set()
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

    # 2-3 Artikel pro Publikationstag: bis zum Tageslimit auffüllen –
    # aber NUR so lange, wie das NEU-Ziel noch nicht erreicht ist
    # (Recycling erfüllt das Ziel nicht, s. tages_bilanz).
    results = []
    while True:
        out = publish_one_article(topics, quelle, pin_topics, used_titles, used_topics)
        if out is None:
            break
        level, draft_saved, status_line = out
        results.append(status_line)
        bilanz = tages_bilanz(cadence_guard.load_posts(), promoted_slugs,
                              max_per_day, min_per_day)
        entscheidung, meldung = produktions_entscheidung(bilanz, max_per_day, min_per_day)
        if entscheidung != "WEITER":
            break

    total = bilanz["total"]
    if total == 0:
        write_status("Kompletter Ausfall – kein Artikel, kein Draft.", level="FAIL")
        return 1
    levels = ", ".join(r.split("|")[1].strip() for r in results)
    live = total - sum(1 for r in results if "Entwurf gesichert" in r)
    note = (f"{total} Artikel heute ({'live: ' + str(live) if live else 'nur Entwürfe'})"
            f" · {bilanz['neu']} NEU · {bilanz['recycelt']} recycelt | "
            f"Ziel: {min_per_day}-{max_per_day} an Mo/Mi/Fr")
    if bilanz["neu"] == 0:
        note += " | ⚠ KEINE Neuproduktion – Recycling zählt nicht als Produktion"
    if total < min_per_day:
        note += " | ⚠ unter Mindestziel"
    write_status(note, level="OK")
    print(f"✅ {note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
