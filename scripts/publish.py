#!/usr/bin/env python3
"""
Veröffentlichungs-Helfer: Setzt 'draft: true' auf 'draft: false'.

NUTZUNG:
    python3 scripts/publish.py posts/2026-08-04-mein-artikel.md   # ein Artikel
    python3 scripts/publish.py --all                              # alle Entwürfe
    python3 scripts/publish.py --all --force-cadence              # NOTFALL

KADENZ-HARD-GATE (Dauervorgabe, 26.08.2026 geschärft):
    Manuelles Veröffentlichen unterliegt der GLEICHEN Routine wie die
    Automatik (CADENCE-REPORT.md Regel 2):
      • NUR montags, mittwochs, freitags
      • höchstens MAX_ARTIKEL_PRO_TAG (Default 3) Artikel pro Tag
        (zählt alle heute veröffentlichten Posts – auch Automatik-Posts)
    Verstoß = Abbruch (Exit 1) mit klarer Meldung. Der Live-Blog darf
    nie durch einen manuellen Klick die Routine brechen.

    NOTFALL (bewusst, wird im Commit-Log sichtbar):
      FORCE_PUBLISH_ANY_DAY=1  oder  --force-cadence
      NUR für Frank, z. B. für geprüfte Nachhol-Publikationen.
"""
import datetime
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import list_post_paths, slug_of, frontmatter_date  # noqa: E402
import cadence_guard  # noqa: E402 – Single Source of Truth für die Kadenz


def published_count_today():
    """Alle heute veröffentlichten Posts (live) – Datum-Feld-basiert."""
    today = datetime.date.today().isoformat()
    return sum(1 for p in cadence_guard.load_posts()
               if not p["draft"] and p["date"].isoformat() == today)


def publish(path):
    with open(path, encoding="utf-8") as f:
        content = f.read()
    if "draft: true" not in content:
        print(f"  – übersprungen (kein Entwurf): {slug_of(path)}")
        return 0
    content = content.replace("draft: true", "draft: false", 1)
    # Entwurfs-Datum durch heutiges Datum ersetzen (wird beim Veröffentlichen neu datiert)
    content = re.sub(r"^date: \d{4}-\d{2}-\d{2}$", f"date: {__import__('datetime').date.today().isoformat()}", content, count=1, flags=re.M)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"  ✓ veröffentlicht: {slug_of(path)}")
    return 1


def main():
    args = sys.argv[1:]
    force = ("--force-cadence" in args
             or os.environ.get("FORCE_PUBLISH_ANY_DAY") == "1")
    args = [a for a in args if a != "--force-cadence"]

    if not args:
        print(__doc__)
        sys.exit(1)

    # ------- KADENZ-HARD-GATE (vor JEDEM Schreibzugriff) -------
    today = datetime.date.today()
    min_d, max_d = cadence_guard.effective_limits()
    today_n = published_count_today()

    if args == ["--all"]:
        files = [f for f in list_post_paths()
                 if "draft: true" in open(f, encoding="utf-8").read()]
    else:
        files = []
        for arg in args:
            path = arg if os.path.isabs(arg) else os.path.join(BLOG_DIR, arg)
            if os.path.exists(path):
                files.append(path)
            else:
                print(f"  ✗ Datei nicht gefunden: {path}")
        if not files:
            sys.exit(1)

    n_drafts = len(files)
    if not force:
        day_name = cadence_guard.DAYS_DE[today.weekday()]
        if not cadence_guard.is_publication_day(today):
            print(f"🛑 KADENZ-GATE: Heute ist {day_name} – Publikation nur "
                  f"Mo/Mi/Fr (Dauervorgabe, CADENCE-REPORT.md Regel 2).")
            print(f"   Notfall: FORCE_PUBLISH_ANY_DAY=1 python3 scripts/publish.py … "
                  f"(bewusster Override, bleibt im Commit-Log).")
            sys.exit(1)
        if today_n + n_drafts > max_d:
            room = max_d - today_n
            if room <= 0:
                print(f"🛑 KADENZ-GATE: Tageslimit ({max_d} Artikel) ist heute "
                      f"erreicht ({today_n} live).")
            else:
                print(f"🛑 KADENZ-GATE: Nur noch {room} von {max_d} Plätzen frei "
                      f"heute – {n_drafts} Veröffentlichungen angefordert.")
            print(f"   Notfall: --force-cadence (bewusster Override).")
            sys.exit(1)
        if today_n + n_drafts < min_d:
            print(f"   ℹ️  Hinweis: Damit sind heute {today_n + n_drafts} von "
                  f"{min_d}–{max_d} Artikeln erreicht – die Engine füllt "
                  f"in den Fallback-Slots auf.")

    # ------- Veröffentlichen -------
    if args == ["--all"]:
        print(f"Veröffentliche {n_drafts} Artikel in {POSTS_DIR}:")
        count = sum(publish(f) for f in files)
    else:
        count = 0
        for f in files:
            count += publish(f)
    if force:
        print("⚠ Mit CADENCE-OVERRIDE durchgeführt (FORCE_PUBLISH_ANY_DAY/--force-cadence).")
    print(f"\nFertig: {count} Artikel veröffentlicht. Jetzt committen & pushen, "
          f"dann baut GitHub Pages automatisch neu "
          f"(Deploy-Gate in deploy.yml prüft die Kadenz ein zweites Mal).")


if __name__ == "__main__":
    main()
