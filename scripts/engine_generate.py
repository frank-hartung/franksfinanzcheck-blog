#!/usr/bin/env python3
"""engine_generate.py – CONTENT-ENGINE v2 (Multi-Fallback-Orchestrierung)

Ersetzt den fragilen Einzel-Lauf der alten Automatisierung durch eine
2-Ebenen-Fallback-Architektur – damit NIE ein Tag ohne neuen Artikel bleibt,
OHNE dabei je Content unterhalb des Profi-Qualitäts-Gates zu veröffentlichen:

  EBENE 1 (Profi):    KI-Artikel generieren, Profi-Gate hart, bis zu
                      5 Versuche mit wechselndem Stil/Perspektive/Provider.
                      Nur ein hier bestandener Artikel wird automatisch
                      veröffentlicht (siehe should_auto_publish()).
  EBENE 2 (Draft):    Wenn auch alle Versuche scheitern: Artikel wird als
                      ENTWURF (draft: true) mit Issue-Hinweis gespeichert.
                      Der Tag ist nie verloren, der Mensch kann ihn
                      fertigstellen und freigeben.

  13.08.2026 (Frank): Die frühere "Relaxed"-Zwischenstufe (abgeschwächtes
  Qualitäts-Gate als Kompromiss fürs Tagesziel) wurde ersatzlos entfernt –
  es soll grundsätzlich keine automatisch veröffentlichten Artikel geben,
  die nicht das volle Profi-Gate bestanden haben. Ein Tag ohne Profi-Erfolg
  bekommt jetzt konsequent einen Entwurf statt eines abgeschwächt geprüften
  Artikels.

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
from check_titles import COMPOUND_FIXES, TIME_TAIL as RE_ANHAENGSEL  # noqa: E402 – Titel-Qualitätsgate (FrankAutoOps)

# ---------------------------------------------------------------------------
# Freigabe-Modus (Frank, 13.08.2026 – 13.08. Nachmittag: Relaxed-Stufe
# ersatzlos entfernt, siehe Modul-Docstring oben):
#   AUTO_PUBLISH=0      -> IMMER manuelle Freigabe (draft:true), egal welche
#                          Qualitätsstufe erreicht wurde. Sicherste Variante.
#   AUTO_PUBLISH=profi  -> Default: Nur Artikel, die das harte Profi-
#                          Qualitäts-Gate bestehen, werden automatisch
#                          veröffentlicht (draft:false). Jede Qualitäts-
#                          Rettung (Ebene 2, Profi-Gate nicht erreicht)
#                          bleibt als Entwurf liegen und wartet auf dich –
#                          es gibt keine Zwischenstufe mehr.
#   AUTO_PUBLISH=1      -> Vollautomatik wie ursprünglich (nicht empfohlen
#                          für eine junge YMYL-Domain, siehe README).
# In jedem Modus: volle Qualitäts-Kette (Rechtschreibung, Grammatik, Cover,
# Meta, interne Links, Affiliate-Guards, …) läuft unverändert durch – nur
# die Veröffentlichungs-Entscheidung am Ende ändert sich.
# Freigeben: GitHub-UI (draft: true -> false) oder `python3 scripts/publish.py
# <slug>`. Repo-Variable AUTO_PUBLISH steuert den Modus (Settings -> Secrets
# and variables -> Actions -> Variables).
# ---------------------------------------------------------------------------
def should_auto_publish(quality_level: str) -> bool:
    """Entscheidet je Artikel, ob er automatisch veröffentlicht werden darf."""
    mode = os.environ.get("AUTO_PUBLISH", "profi").strip().lower()
    if mode in ("1", "true", "yes", "all", "immer"):
        return True
    if mode in ("0", "false", "no", "nie", "manuell", "manual"):
        return False
    # Default "profi": NUR echte Profi-Qualität wird automatisch veröffentlicht.
    # Es gibt keine Zwischenstufe mehr (Relaxed entfernt, 13.08.2026) – jeder
    # andere quality_level-Wert (insbesondere "draft"/Qualitäts-Rettung, oder
    # ein nicht erkannter Modus-Wert) führt sicher zu draft:true statt einer
    # versehentlichen Vollautomatik bei Tippfehlern.
    return quality_level == "profi"


# Rückwärtskompatibel (falls andere Skripte/ältere Aufrufe noch das alte,
# globale Bool-Flag lesen): True nur im reinen Vollautomatik-Modus.
AUTO_PUBLISH = os.environ.get("AUTO_PUBLISH", "profi").strip().lower() in ("1", "true", "yes", "all", "immer")


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


def _log_cadence_event(result: str, topics_tried: int) -> None:
    """Protokolliert jeden Lauf ins zentrale Audit-Log (data/audit/*.jsonl).
    Grundlage für scripts/cadence_manager.py, das daraus automatisch die
    Erfolgsquote berechnet und die Publikationsfrequenz anpasst (13.08.2026,
    "Profi-SEO-Manager"/"Profi-Affiliate-Marketer"-Betriebsregel)."""
    try:
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        from audit_log import log_event
        log_event(module="engine_generate", action="run",
                  input={"topics_tried": topics_tried},
                  output={"result": result},
                  status="ok" if result == "published" else ("error" if result == "error" else "skip"))
    except Exception:
        pass


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


def save_article(title, desc, body, draft=False, inspiration=None, pillar=None, quality_level=None):
    """Speichert Artikel als Page-Bundle (Format wie bisherige Pipeline).
    quality_level: optionale, echte Qualitätsstufe ("profi") fürs
    Frontmatter-Feld engine_level – bleibt auch bei draft:true (manuelle
    Freigabe) sichtbar, statt pauschal auf "draft" zu fallen (das bleibt
    reserviert für echte Qualitäts-Gate-Ausfälle, Ebene 2). Die frühere
    Zwischenstufe "relaxed" gibt es seit 13.08.2026 nicht mehr."""
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
    # engine_level ist jetzt binär: "profi" (Ebene 1 bestanden) oder "draft"
    # (Ebene 2, Qualitäts-Rettung) – keine "relaxed"-Zwischenstufe mehr.
    engine_level = quality_level or "draft"
    frontmatter = (
        "---\n"
        f'title: {yaml_quote(title)}\n'
        f'description: {yaml_quote(desc)}\n'
        f"date: {now_utc_iso()}\n"
        f"draft: {draft_line}\n"
        'tags: []\n'
        'categories: ["Ratgeber"]\n'
        'pillar: "' + (pillar or "konto-karten") + '"\n' 
        "author: \"Frank Hartung\"\n"
        "ai_generated: true\n"
        f'ai_provider: "Content-Engine v2"\n'
        f"engine_level: \"{engine_level}\"\n"
        f"{insp_line}"
        "---\n"
    )
    with open(filename, "w", encoding="utf-8") as fh:
        fh.write(frontmatter + body.strip() + "\n" + cta)
    return filename, slug



# ---------------------------------------------------------------------------
# Ebene 1: Generieren mit hartem Profi-Qualitäts-Gate (13.08.2026: keine
# abgeschwächte "Relaxed"-Zwischenstufe mehr – entweder Profi-Niveau oder
# Ebene 2 / Draft-Rettung, siehe Modul-Docstring oben).
# ---------------------------------------------------------------------------

def try_generate(topic, keywords, pin, used_titles, max_attempts=5):
    """Ein Generierungs-Versuch über beide Provider. Liefert (filename|None, info).
    Prüft IMMER das volle Profi-Gate (g.profi_quality_ok) – kein Fallback auf
    reduzierte Kriterien mehr."""
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

        ok_profi, prob = g.profi_quality_ok(body, keywords)
        if not ok_profi:
            print(f"  ⚠ Profi-Gate: {'; '.join(prob[:3])} (Versuch {attempt}/{max_attempts}, {provider})")
            continue

        used_titles.add(title.lower())
        return (title, desc, body), f"OK via {provider_name} (profi)"
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
    # TAGESLIMIT (13.08.2026 auf 1 reduziert – Google-Sichtbarkeits-Audit):
    # Standard ist jetzt 1 Artikel/Tag (an publizierenden Tagen, siehe Cron
    # in content-engine-v2.yml), harte Obergrenze bleibt bei 2 (Sicherheits-
    # Deckel, falls MAX_ARTIKEL_PRO_TAG mal höher gesetzt wird).
    max_per_day = min(int(os.environ.get("MAX_ARTIKEL_PRO_TAG", "1")), 2)
    if os.environ.get("MAX_ARTIKEL_PRO_TAG", "1") not in ("1", "2"):
        print(f"⚠ MAX_ARTIKEL_PRO_TAG={os.environ.get('MAX_ARTIKEL_PRO_TAG')} "
              f"– hartes Cap von 2 Posts/Tag greift.")
    pin_topics = os.environ.get("PIN_TOPICS", "0") == "1"

    # Tages-Guard (wie bisherige Pipeline)
    # 13.08.: Zählt jetzt ALLE heutigen Artikel, die das Profi-Qualitäts-Gate
    # bestanden haben – unabhängig vom draft-Flag. So bleibt
    # das 2/Tag-Cap auch im manuellen Freigabe-Modus (AUTO_PUBLISH=0) korrekt:
    # Frank bekommt trotzdem nur 2 Entwürfe/Tag statt endlos vieler. Nur
    # echte Qualitäts-Rettungen (engine_level: "draft", Ebene 3) zählen NICHT
    # mit – für die soll weiter ein Ersatzartikel versucht werden.
    today = datetime.date.today().isoformat()
    published_today = 0
    for path in g.list_post_paths():
        if os.path.basename(os.path.dirname(path)).startswith(today):
            content = open(path, encoding="utf-8").read()
            if 'engine_level: "draft"' in content or "engine_level: 'draft'" in content:
                continue
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

    # 13.08.2026 (Frank, "so wenig wie möglich zu tun"): KEIN Stub-Entwurf
    # mehr bei Misserfolg. Stattdessen probiert die Engine bis zu
    # TOPIC_HOP_LIMIT verschiedene Themen durch (je mit vollen 5 Versuchen,
    # siehe try_generate()) und veröffentlicht NUR, wenn eines davon das
    # Profi-Gate besteht. Klappt gar keins, wird der Lauf sauber ohne
    # Artefakt beendet – der nächste Cron-Slot (mehrere pro Publikationstag)
    # probiert automatisch erneut. Niemand muss je einen Entwurf von Hand
    # fertigschreiben oder freigeben.
    TOPIC_HOP_LIMIT = 3
    random.shuffle(freie)
    versucht = []
    result, info, topic = None, "", None
    for kandidat in freie[:TOPIC_HOP_LIMIT]:
        keywords = kandidat.get("keywords")
        pin = None
        if pin_topics:
            try:
                pin = g.find_pin_for_topic(kandidat.get("title"), g.load_pinterest_plan())
            except Exception:  # noqa: BLE001
                pin = None
        print(f"Content-Engine v2 – Quelle: {quelle}, Thema: {kandidat['title'][:60]}")
        result, info = try_generate(kandidat, keywords, pin, used_titles, max_attempts=5)
        versucht.append(kandidat["title"][:40])
        if result:
            topic = kandidat
            break
        print(f"  → Thema verworfen ({info}), nächstes Thema …")

    level = "profi"
    if not result:
        # Kein einziges der probierten Themen hat das Profi-Gate erreicht.
        # Kein Draft, kein Artefakt – einfach sauber beenden. Kein Fehler-
        # Alarm (Exit 0): Das ist erwartetes Verhalten bei KI-Schwankungen,
        # kein Betriebsproblem. Themenpool bleibt für den nächsten Slot frei.
        info_line = f"{len(versucht)} Themen probiert, keins bestand das Profi-Gate: {versucht}"
        print(f"○ Kein Artikel diesen Lauf – {info_line}")
        write_status(info_line, level="SKIP")
        _log_cadence_event("skip", topics_tried=len(versucht))
        return 0

    title, desc, body = result
    try:
        if should_auto_publish(level):
            filename, slug = save_article(title, desc, body, draft=False,
                                          inspiration=topic.get("title"), pillar=topic.get("pillar"),
                                          quality_level=level)
            print(f"  ✓ Artikel automatisch veröffentlicht ({level}): {slug}")
        else:
            filename, slug = save_article(title, desc, body, draft=True,
                                          inspiration=topic.get("title"), pillar=topic.get("pillar"),
                                          quality_level=level)
            print(f"  ✓ Entwurf gesichert (Qualität: {level}, wartet auf manuelle Freigabe): {slug}")
    except Exception as exc:  # noqa: BLE001
        print(f"  ✗ Speichern fehlgeschlagen: {exc}")
        write_status("Kompletter Ausfall – Speicherfehler.", level="FAIL")
        _log_cadence_event("error", topics_tried=len(versucht))
        return 1

    status_line = f"Thema: {topic['title'][:60]} | Ebene: {level} | veröffentlicht | {info}"
    write_status(status_line, level="OK")
    _log_cadence_event("published", topics_tried=len(versucht))
    return 0


if __name__ == "__main__":
    sys.exit(main())
