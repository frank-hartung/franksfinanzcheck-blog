#!/usr/bin/env python3
# ============================================================
#  CAMPAIGN-MANAGER – Kampagnen + Redaktionskalender (AGC-Parität, Stufe 3)
#  ------------------------------------------------------------
#  AGC Studio bietet ein "Campaign Management System":
#    - Promo-Kampagnen      (Angebot, Zeitraum, kampagnen-eigener CTA)
#    - Researched-Kampagnen (Thema → Research → Content-Serie)
#    - eigener Kampagnen-Kalender, kampagnen-spezifische CTAs.
#
#  Dieses Skript bildet das für den Hugo-Blog ab:
#    - data/campaigns.yaml        – Kampagnen-Definitionen (Single Source)
#    - cta_for()                  – löst den effektiven CTA je Artikel auf
#                                   (Kampagnen-CTA hat Vorrang vor default_cta)
#    - generate_calendar()        – plant die nächsten Publikations-Slots
#                                   (Mo/Mi/Fr, Dauervorgabe) in
#                                   data/editorial_calendar.yaml
#
#  KADENZ-SCHUTZ: Der Kalender plant AUSSCHLIESSLICH innerhalb der
#  DAUERVORGABE (Mo/Mi/Fr) – er ist ein PLAN, kein Veröffentlicher.
#  Die harten Gates (cadence_guard, publish_gate) bleiben unberührt.
#
#  Aufruf:
#    python3 scripts/campaign_manager.py --calendar [--weeks 4] [--dry-run]
#    python3 scripts/campaign_manager.py --status
#    python3 scripts/campaign_manager.py --selftest
# ============================================================
import datetime
import hashlib
import os
import random
import re
import sys

import yaml

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import brand_brain as bb          # noqa: E402
import research_engine as re_     # noqa: E402

CAMPAIGNS_FILE = os.path.join(BLOG_DIR, "data", "campaigns.yaml")
CALENDAR_FILE = os.path.join(BLOG_DIR, "data", "editorial_calendar.yaml")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")

# Kadenz-Single-Source-of-Truth (Mo/Mi/Fr), NICHT hier duplizieren.
try:
    import cadence_guard  # noqa: E402
    PUBLICATION_DAYS = cadence_guard.PUBLICATION_DAYS
except Exception:  # pragma: no cover – Fallback, falls cadence_guard fehlt
    PUBLICATION_DAYS = {0, 2, 4}


# ---------------------------------------------------------------- Laden
def load_campaigns():
    if not os.path.exists(CAMPAIGNS_FILE):
        return []
    try:
        with open(CAMPAIGNS_FILE, encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
    except Exception:
        return []
    camps = data.get("campaigns", []) if isinstance(data, dict) else []
    return [c for c in camps if isinstance(c, dict)]


def active_campaigns(day=None):
    day = day or datetime.date.today()
    today = day.isoformat()
    active = []
    for c in load_campaigns():
        if c.get("status") != "active":
            continue
        start, end = c.get("start"), c.get("end")
        if start and today < str(start):
            continue
        if end and today > str(end):
            continue
        active.append(c)
    return active


def campaign_for(campaigns, pillar):
    """Wählt die passende aktive Kampagne für einen Pillar (erste Priorität)."""
    for c in campaigns:
        if pillar in (c.get("pillars") or []):
            return c
    return None


def cta_for(pillar=None, day=None, campaigns=None):
    """Effektiver CTA: Kampagnen-CTA > default_cta (Brand Brain)."""
    campaigns = active_campaigns(day) if campaigns is None else campaigns
    brain = bb.load_brand_brain()
    camp = campaign_for(campaigns, pillar) if pillar else None
    if camp and camp.get("cta"):
        return camp["cta"], camp.get("id")
    return brain.get("default_cta", "Jetzt vergleichen"), None


# ---------------------------------------------------------------- Bestand
def covered_titles():
    """Titel aller vorhandenen Posts (für die Lücken-Erkennung)."""
    titles = set()
    if not os.path.isdir(POSTS_DIR):
        return titles
    for slug in sorted(os.listdir(POSTS_DIR)):
        idx = os.path.join(POSTS_DIR, slug, "index.md")
        if not os.path.isfile(idx):
            continue
        try:
            head = open(idx, encoding="utf-8").read(4000)
        except OSError:
            continue
        m = re.search(r"^title:\s*[\"']?(.+?)[\"']?\s*$", head, re.M)
        if m:
            titles.add(m.group(1).strip().lower())
    return titles


def load_topics():
    data = re_._load_yaml(TOPICS_FILE)
    topics = data.get("topics", []) if isinstance(data, dict) else []
    return [t for t in topics if isinstance(t, dict)]


def uncovered_topics(day=None):
    """Themen, die noch keinen Artikel haben (Lücken-Feed für den Kalender)."""
    covered = covered_titles()
    out = []
    for t in load_topics():
        title = (t.get("title") or "").strip()
        if not title:
            continue
        if title.lower() in covered:
            continue
        out.append(t)
    rng = random.Random(f"uncovered:{ (day or datetime.date.today()).isoformat() }")
    rng.shuffle(out)
    return out


# ---------------------------------------------------------------- Kalender
def next_slots(weeks=4, day=None):
    """Erzeugt die nächsten Publikations-Slots (Mo/Mi/Fr) ab morgen."""
    day = day or datetime.date.today()
    slots = []
    cursor = day + datetime.timedelta(days=1)
    end = day + datetime.timedelta(weeks=weeks)
    while cursor <= end:
        if cursor.weekday() in PUBLICATION_DAYS:
            slots.append(cursor)
        cursor += datetime.timedelta(days=1)
    return slots


def generate_calendar(weeks=4, day=None, report=None):
    """Baut den Redaktionskalender: Slots → Thema/Pillar/Kampagne/CTA/Winkel."""
    day = day or datetime.date.today()
    report = report or re_._load_yaml(re_.LATEST_FILE)
    active = active_campaigns(day)
    free = uncovered_topics(day)
    slots = next_slots(weeks, day)
    # Recherche-Brief nur mit echten Keywords (Hint-Themen ohne Keywords
    # bekommen einen ehrlichen leeren Brief statt erfundener Suchbegriffe).
    plan = []
    # BLOGAUTOMATIK-OPTIMIERUNG 28.09.2026: Abgedeckte Titel (bestehende
    # Artikel) einmal laden und pro Lauf mitführen – Kampagnen-Hints, die
    # bereits einen Artikel haben, werden übersprungen statt doppelt geplant.
    covered = covered_titles()
    planned = set()
    for i, slot in enumerate(slots):
        topic_entry, source = _pick_topic(active, free, i, slot,
                                          covered=covered, planned=planned)
        topic = (topic_entry or {}).get("title", "").strip() or "—"
        pillar = (topic_entry or {}).get("pillar")
        camp = campaign_for(active, pillar)
        cta, camp_id = cta_for(pillar, day=day, campaigns=active)
        brief = ""
        if report and "teams" in report:
            brief = re_.build_brief(report, topic, pillar=pillar,
                                    keywords=(topic_entry or {}).get("keywords"))
        plan.append({
            "date": slot.isoformat(),
            "weekday": slot.strftime("%a"),
            "slot": i + 1,
            "topic": topic,
            "pillar": pillar,
            "source": source,
            "campaign": camp_id,
            "cta": cta,
            "research_brief": brief or "",
        })
    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc)
                        .strftime("%Y-%m-%dT%H:%M:%SZ"),
        "start_date": (day + datetime.timedelta(days=1)).isoformat(),
        "cadence": "Mo/Mi/Fr · 2–3 Artikel/Tag (DAUERVORGABE)",
        "slots": plan,
    }


def _pick_topic(active, free, idx, slot, covered=None, planned=None):
    """Themenwahl: Kampagnen-Hint > freie Themen > leeres Slot (nie doppelt).

    BLOGAUTOMATIK-OPTIMIERUNG 28.09.2026: Vorher lief die Hint-Schleife als
    `for h, c in hints: return …` – JEDER Slot bekam denselben ersten Hint,
    eine aktive Kampagne hätte also den kompletten Kalender mit ein und
    demselben Thema gefüllt (Duplikat-Risiko für die Engine). Jetzt:
      1. Hints der Reihe nach, jeder höchstens EINMAL pro Kalenderlauf
         (`planned`) und nur, wenn dafür noch kein Artikel existiert
         (`covered` – Titel-Abgleich wie bei freien Themen).
      2. Freie Themen (Lücken) – deterministisch, ebenfalls ohne Wieder-
         holung innerhalb des Laufs.
      3. Fallback: irgendein Thema aus dem Pool (verhindert leeres Slot).
    """
    covered = covered if covered is not None else set()
    planned = planned if planned is not None else set()

    def _norm(t):
        return (t or "").strip().lower()

    # 1) Aktive Kampagne mit expliziten Themen-Hints (zyklisch, nie doppelt)
    hints = []
    for c in active:
        for h in (c.get("topics_hint") or []):
            hints.append((h, c))
    for h, c in hints:
        if _norm(h) in covered:
            continue
        if _norm(h) in planned:
            continue
        entry = {"title": h, "pillar": (c.get("pillars") or [None])[0],
                 "keywords": []}
        planned.add(_norm(h))
        return entry, f"campaign:{c.get('id')}"
    # 2) Freie Themen (Lücken) – der Reihe nach, ohne Wiederholung im Lauf
    if free:
        for t in free:
            if _norm(t.get("title")) in planned:
                continue
            planned.add(_norm(t.get("title")))
            return t, "topics"
    # 3) Fallback: irgendein Thema aus dem Pool (verhindert leeres Slot)
    all_topics = load_topics()
    if all_topics:
        rng = random.Random(f"fallback:{slot.isoformat()}")
        return rng.choice(all_topics), "topics:fallback"
    return None, "leer"


def save_calendar(plan, dry_run=False):
    if dry_run:
        return
    with open(CALENDAR_FILE, "w", encoding="utf-8") as fh:
        yaml.safe_dump(plan, fh, allow_unicode=True, sort_keys=False)


# ---------------------------------------------------------------- CLI
def run_selftest():
    errs = []
    plan = generate_calendar(weeks=2)
    if not plan.get("slots"):
        errs.append("Kalender erzeugt keine Slots")
    for s in plan["slots"]:
        wd = datetime.date.fromisoformat(s["date"]).weekday()
        if wd not in PUBLICATION_DAYS:
            errs.append(f"Slot {s['date']} liegt NICHT an Mo/Mi/Fr")
    if not errs:
        # CTA-Auflösung prüfen
        cta, _ = cta_for("strom-sparen")
        if not cta:
            errs.append("cta_for lieferte keinen CTA")

    # BLOGAUTOMATIK-OPTIMIERUNG 28.09.2026: Eine aktive Kampagne darf den
    # Kalender NIE mit ein und demselben Thema fluten (der alte Code gab
    # jedem Slot den ersten Hint). Drei Verträge:
    #   a) Hints werden zyklisch und nur einmal pro Lauf verplant
    #   b) bereits abgedeckte Hints (Artikel existiert) werden übersprungen
    #   c) im erzeugten Kalender wiederholt sich kein Thema
    fake = [{"id": "selftest-kampagne", "status": "active",
             "pillars": ["strom-sparen"],
             "topics_hint": ["Hint Alpha", "Hint Beta"]}]
    # Ein shared planned-Set pro Kalenderlauf – exakt die Semantik von
    # generate_calendar. Der alte Code hätte hier 4× „Hint Alpha" geliefert.
    planned = set()
    seen = []
    for i in range(4):
        entry, _src = _pick_topic(fake, [], i, datetime.date.today(),
                                  planned=planned)
        seen.append((entry or {}).get("title"))
    if seen[0] != "Hint Alpha" or seen[1] != "Hint Beta":
        errs.append(f"_pick_topic verplant Kampagnen-Hints falsch: {seen}")
    if any(t in ("Hint Alpha", "Hint Beta") for t in seen[2:]):
        errs.append(f"_pick_topic wiederholt einen Hint: {seen}")
    entry, _src = _pick_topic(fake, [], 0, datetime.date.today(),
                              covered={"hint alpha"})
    if entry and entry.get("title") == "Hint Alpha":
        errs.append("_pick_topic plant einen bereits abgedeckten Hint")
    titel = [s.get("topic", "").strip().lower() for s in plan.get("slots", [])]
    if titel and len(set(titel)) < len(titel):
        dup = sorted({t for t in titel if titel.count(t) > 1})
        errs.append(f"Kalender plant Themen doppelt: {dup[:3]}")
    return errs


def main():
    if "--selftest" in sys.argv:
        errs = run_selftest()
        if errs:
            print("🛑 CAMPAIGN-MANAGER-SELFTEST FEHLGESCHLAGEN:")
            for e in errs:
                print(f"   - {e}")
            return 2
        print("✅ CAMPAIGN-MANAGER-SELFTEST bestanden (Kalender + CTA).")
        return 0

    if "--calendar" in sys.argv:
        weeks = 4
        if "--weeks" in sys.argv:
            w = sys.argv.index("--weeks")
            if len(sys.argv) > w + 1:
                weeks = int(sys.argv[w + 1])
        dry = "--dry-run" in sys.argv
        plan = generate_calendar(weeks=weeks)
        save_calendar(plan, dry_run=dry)
        print(f"🗓️ Redaktionskalender: {len(plan['slots'])} Slots "
              f"(Mo/Mi/Fr, {weeks} Wochen) {'(dry-run)' if dry else 'gespeichert'}")
        for s in plan["slots"]:
            print(f"   {s['date']} ({s['weekday']}) · {s['pillar'] or '–'} · "
                  f"{s['topic'][:60]}")
        return 0

    # Default: Status
    day = datetime.date.today()
    active = active_campaigns(day)
    print(f"Kampagnen aktiv am {day.isoformat()}: {len(active)}")
    for c in load_campaigns():
        mark = "● aktiv" if c in active else "○ " + c.get("status", "?")
        print(f"  {mark:10s} {c.get('id')} ({c.get('type')}) "
              f"{c.get('start')} → {c.get('end')}")
    cta, _ = cta_for("strom-sparen", day=day)
    print(f"Default-CTA Strom: {cta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
