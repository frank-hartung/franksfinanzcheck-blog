#!/usr/bin/env python3
"""TAGESZIEL-GUARD – sichert an Publikationstagen mindestens 1 veröffentlichten
Post (Profi-Level, Selbstheilung) für FranksFinanzcheck.

Betriebsregel (User, 13.08.2026 – reduziert von 2/Tag auf 1 Artikel an 4
Tagen/Woche): Dieser Guard prüft bei jedem Lauf, wie viele Posts mit
Veröffentlichungsdatum HEUTE (Qualitäts-Gate bestanden, unabhängig vom
draft-Flag) im Content liegen, und generiert fehlende Artikel direkt über
die Content-Engine (try_generate: Profi → Draft-Rettung, keine Relaxed-
Zwischenstufe mehr seit 13.08.2026 Nachmittag) – mit den gleichen
Qualitäts-Gates wie die Engine selbst.

SELBSTHEILUNG:
  - 3 Cron-Slots je Publikationstag (Mo/Mi/Fr/Sa): scheitert ein Lauf
    (z. B. API-Rate-Limit), versucht der nächste Slot automatisch erneut.
  - Fehlgeschlagene Generation → Exit 1 (Workflow-Alarm via
    alert-on-failure) + Audit-Log; nichts bleibt still.
  - MAX_ARTIKEL_PRO_TAG-Cap (Default 1, hart max. 2) der Engine wird
    respektiert.

Nutzung:
  python3 scripts/daily_post_guard.py          # nur zählen (Exit 0/3)
  python3 scripts/daily_post_guard.py --fill   # fehlende generieren
  python3 scripts/daily_post_guard.py --json   # JSON-Status

Exit: 0 = Ziel erreicht · 3 = Ziel nicht erreicht (Workflow: Aktion nötig)
     1 = Fehler (Generation fehlgeschlagen)
"""
import datetime
import glob
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TAGESZIEL = 1  # Betriebsregel (13.08.2026): 1 Post an Publikationstagen (Mo/Mi/Fr/Sa)

DO_FILL = "--fill" in sys.argv
AS_JSON = "--json" in sys.argv


def published_today():
    """Anzahl heute erstellter, qualitätsgeprüfter Artikel (unabhängig vom
    draft-Flag – siehe engine_generate.should_auto_publish). Zählt über das
    date-Feld (Hugo-Richtigkeit), Ordnername als Fallback. Echte
    Qualitäts-Rettungen (engine_level: "draft", Ebene 3) zählen NICHT mit,
    damit für sie weiter ein Ersatzartikel versucht wird."""
    today = datetime.date.today().isoformat()
    n = 0
    for f in glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md")):
        c = open(f, encoding="utf-8").read()
        if 'engine_level: "draft"' in c or "engine_level: 'draft'" in c:
            continue
        m = re.search(r"^date:\s*[\"']?([^\"'\n]+)", c, re.M)
        d = m.group(1).strip()[:10] if m else ""
        if d == today:
            n += 1
            continue
        # Fallback: Ordnername mit Datums-Präfix (Engine-Konvention)
        slug = os.path.basename(os.path.dirname(f))
        if d == "" and slug.startswith(today):
            n += 1
    return n


def fill_missing():
    """Generiert fehlende Artikel (bis TAGESZIEL erreicht).
    Rückgabe: (erstellt, fehlgeschlagen, info, draft_pending).
    draft_pending=True, sobald in diesem Lauf mindestens 1 Artikel als
    Entwurf (draft:true) statt automatisch veröffentlicht gespeichert wurde
    – steuert, ob ein Freigabe-Issue wirklich nötig ist (zweistufige
    Freigabe, siehe engine_generate.should_auto_publish)."""
    created, failed = 0, []
    draft_pending = False
    missing = max(0, TAGESZIEL - published_today())
    if missing == 0:
        return 0, [], "Ziel bereits erreicht", False

    sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
    import engine_generate as eg
    import generate_drafts as g

    used_titles = g.existing_titles()
    topics = g.load_topics()
    freie = [t for t in topics if not g.topic_already_covered(t["title"], used_titles)]
    if not freie:
        try:
            g.refill_topics(topics, used_titles)
        except Exception as exc:  # noqa: BLE001
            print(f"  ⚠ Themen-Nachschub fehlgeschlagen: {exc}")
        topics = g.load_topics()
        freie = [t for t in topics if not g.topic_already_covered(t["title"], used_titles)]
    if not freie:
        return 0, ["Themenpool erschöpft"], "keine freien Themen", False

    import random
    # 13.08.2026 ("so wenig wie möglich zu tun"): kein Stub-Entwurf mehr bei
    # Misserfolg. Stattdessen Themen-Hopping (bis zu 3 Themen je fehlendem
    # Artikel, je mit vollen 5 Versuchen) – klappt gar keins, bleibt der
    # Tag ohne neuen Artikel, OHNE Artefakt. Der nächste Cron-Slot (3/Tag)
    # probiert automatisch erneut. draft_pending bleibt False in diesem Fall
    # bewusst (kein Freigabe-Issue nötig – es gibt nichts freizugeben).
    TOPIC_HOP_LIMIT = 3
    for i in range(missing):
        if published_today() >= TAGESZIEL:
            break
        kandidaten = random.sample(freie, min(TOPIC_HOP_LIMIT, len(freie)))
        result, info, topic = None, "", None
        for cand in kandidaten:
            keywords = cand.get("keywords")
            pin = None
            try:
                pin = g.find_pin_for_topic(cand.get("title"), g.load_pinterest_plan())
            except Exception:  # noqa: BLE001
                pin = None
            result, info = eg.try_generate(cand, keywords, pin, used_titles, max_attempts=5)
            if result:
                topic = cand
                break
            print(f"  → Thema verworfen ({info}): {cand['title'][:50]}")

        if not result:
            failed.append(f"{len(kandidaten)} Themen probiert, keins bestand das Profi-Gate")
            print(f"  ○ Kein Artikel diesen Slot – {len(kandidaten)} Themen ohne Erfolg probiert.")
            continue

        title, desc, body = result
        try:
            # Freigabe (siehe engine_generate.should_auto_publish): nur echte
            # "profi"-Qualität wird automatisch veröffentlicht. Zählt als
            # "erstellt" (Profi-Gate bestanden), damit das Tages-Cap nicht
            # dauerhaft "offen" bleibt und immer weiter nachgeneriert.
            auto_publish_now = eg.should_auto_publish("profi")
            filename, slug = eg.save_article(title, desc, body, draft=not auto_publish_now,
                                             inspiration=topic.get("title"),
                                             pillar=topic.get("pillar"),
                                             quality_level="profi", keywords=topic.get("keywords"))
            created += 1
            used_titles.add(title.lower())
            if auto_publish_now:
                print(f"  ✅ Artikel automatisch veröffentlicht (profi): {slug} ({topic['title'][:50]})")
            else:
                draft_pending = True
                print(f"  ✅ Entwurf erstellt (profi, wartet auf Freigabe): {slug} ({topic['title'][:50]})")

        except Exception as exc:  # noqa: BLE001
            failed.append(str(exc))
            print(f"  ✗ Speichern fehlgeschlagen: {exc}")
    return created, failed, f"{created} erstellt, {len(failed)} fehlgeschlagen", draft_pending


def main():
    n = published_today()
    status = {"today": datetime.date.today().isoformat(),
              "published": n, "target": TAGESZIEL,
              "missing": max(0, TAGESZIEL - n), "draft_pending": False}

    if DO_FILL and status["missing"] > 0:
        created, failed, info, draft_pending = fill_missing()
        status["created"] = created
        status["failed"] = failed
        status["info"] = info
        status["draft_pending"] = draft_pending
        n = published_today()
        status["published"] = n
        status["missing"] = max(0, TAGESZIEL - n)
        # Audit-Log
        try:
            sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
            from audit_log import log_event
            log_event(module="daily_post_guard", action="fill",
                      input={"target": TAGESZIEL},
                      output={"published": n, "created": created,
                              "failed": failed},
                      status="ok" if status["missing"] == 0 else "partial")
        except Exception:
            pass

    print(f"Tagesziel-Guard: {status['published']}/{TAGESZIEL} Posts heute "
          f"({datetime.date.today().isoformat()})"
          + (f" – {status.get('info', '')}" if DO_FILL else ""))
    # Maschinenlesbare Zeile fürs Workflow (steuert, ob ein Freigabe-Issue
    # nötig ist – nur wenn tatsächlich ein Entwurf liegen geblieben ist,
    # nicht pauschal je nach AUTO_PUBLISH-Modus).
    print(f"DRAFT_PENDING={'true' if status['draft_pending'] else 'false'}")
    if AS_JSON:
        print(json.dumps(status, ensure_ascii=False))

    if status["missing"] > 0:
        return 1 if DO_FILL else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
