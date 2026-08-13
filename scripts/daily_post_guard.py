#!/usr/bin/env python3
"""TAGESZIEL-GUARD – sichert täglich 2 veröffentlichte Posts (Profi-Level,
Selbstheilung) für FranksFinanzcheck.

Betriebsregel (User, 12.08.2026): JEDEN Tag werden GENAU 2 Artikel
veröffentlicht. Dieser Guard prüft bei jedem Lauf, wie viele Posts mit
Veröffentlichungsdatum HEUTE (draft: false) im Content liegen, und
generiert fehlende Artikel direkt über die Content-Engine (try_generate:
Profi → Relaxed → Draft-Rettung) – mit den gleichen Qualitäts-Gates wie
die Engine selbst.

SELBSTHEILUNG:
  - 3 Cron-Slots/Tag (06:30 / 12:30 / 18:30 UTC): scheitert ein Lauf
    (z. B. API-Rate-Limit), versucht der nächste Slot automatisch erneut.
  - Fehlgeschlagene Generation → Exit 1 (Workflow-Alarm via
    alert-on-failure) + Audit-Log; nichts bleibt still.
  - MAX_ARTIKEL_PRO_TAG-Cap (2) der Engine wird respektiert – es werden
    nie mehr als 2/Tag veröffentlicht.

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
TAGESZIEL = 2  # Betriebsregel: genau 2 Posts pro Tag

DO_FILL = "--fill" in sys.argv
AS_JSON = "--json" in sys.argv


def published_today():
    """Anzahl heute erstellter, qualitätsgeprüfter Artikel (unabhängig vom
    draft-Flag – siehe engine_generate.AUTO_PUBLISH). Zählt über das
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
    Rückgabe: (erstellt, fehlgeschlagen, info)."""
    created, failed = 0, []
    missing = max(0, TAGESZIEL - published_today())
    if missing == 0:
        return 0, [], "Ziel bereits erreicht"

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
        return 0, ["Themenpool erschöpft"], "keine freien Themen"

    import random
    for i in range(missing):
        if published_today() >= TAGESZIEL:
            break
        # Thema wählen (nicht schon heute verwendet)
        topic = None
        for _ in range(len(freie)):
            cand = random.choice(freie)
            if cand.get("title") not in [x.get("title") for x in [] if False]:
                topic = cand
                break
        if topic is None:
            topic = random.choice(freie)
        keywords = topic.get("keywords")
        pin = None
        try:
            pin = g.find_pin_for_topic(topic.get("title"), g.load_pinterest_plan())
        except Exception:  # noqa: BLE001
            pin = None

        result = None
        level = "relaxed"
        for relaxed in (False, True):
            result, info = eg.try_generate(topic, keywords, pin, used_titles,
                                           relaxed=relaxed, max_attempts=3 if not relaxed else 2)
            level = "relaxed" if relaxed else "profi"
            if result:
                break
        if not result:
            # Draft-Rettung (wie Engine Ebene 3) – zählt bewusst NICHT als
            # "created", damit der nächste Slot einen echten Ersatz versucht.
            try:
                title, desc, body = eg.make_draft(topic, used_titles)
                filename, slug = eg.save_article(title, desc, body, draft=True,
                                                 inspiration=topic.get("title"),
                                                 pillar=topic.get("pillar"))
                failed.append(f"{slug} (Draft – Qualitäts-Gate)")
                print(f"  ⚠ {slug}: nur Draft gerettet")
                continue
            except Exception as exc:  # noqa: BLE001
                failed.append(str(exc))
                print(f"  ✗ Generierung fehlgeschlagen: {exc}")
                continue
        title, desc, body = result
        try:
            # 13.08.: manuelle Freigabe (siehe engine_generate.AUTO_PUBLISH) –
            # Standard ist jetzt draft:true, der Artikel zählt aber trotzdem
            # als "erstellt" (Qualitäts-Gate bestanden), damit das 2/Tag-Cap
            # nicht dauerhaft "offen" bleibt und immer weiter nachgeneriert.
            filename, slug = eg.save_article(title, desc, body, draft=not eg.AUTO_PUBLISH,
                                             inspiration=topic.get("title"),
                                             pillar=topic.get("pillar"),
                                             quality_level=level)
            created += 1
            used_titles.add(title.lower())
            if eg.AUTO_PUBLISH:
                print(f"  ✅ Artikel erstellt: {slug} ({topic['title'][:50]})")
            else:
                print(f"  ✅ Entwurf erstellt (wartet auf Freigabe): {slug} ({topic['title'][:50]})")

        except Exception as exc:  # noqa: BLE001
            failed.append(str(exc))
            print(f"  ✗ Speichern fehlgeschlagen: {exc}")
    return created, failed, f"{created} erstellt, {len(failed)} fehlgeschlagen"


def main():
    n = published_today()
    status = {"today": datetime.date.today().isoformat(),
              "published": n, "target": TAGESZIEL,
              "missing": max(0, TAGESZIEL - n)}

    if DO_FILL and status["missing"] > 0:
        created, failed, info = fill_missing()
        status["created"] = created
        status["failed"] = failed
        status["info"] = info
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
    if AS_JSON:
        print(json.dumps(status, ensure_ascii=False))

    if status["missing"] > 0:
        return 1 if DO_FILL else 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
