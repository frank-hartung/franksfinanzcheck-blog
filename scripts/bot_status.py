"""Bot-Status-Dashboard – erzeugt/aktualisiert BOT-STATUS.md im Repo.

Damit du den Zustand der Automatisierung AUF EINEN BLICK im Repo siehst
(ohne die Actions-Seite zu öffnen). Der Workflow ruft dieses Skript am
Ende jedes Laufs auf; die Datei wird nur committet, wenn sich der Inhalt
ändert (kein Commit-Spam).
"""
import os
import re
import sys
import glob
import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATUS_FILE = os.path.join(BLOG_DIR, "BOT-STATUS.md")
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")


def main():
    now = datetime.datetime.now()
    today = now.date().isoformat()

    # 1) Heute veröffentlichte Artikel
    published_today = []
    for path in sorted(glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))):
        slug = os.path.basename(os.path.dirname(path))
        if slug.startswith(today):
            content = open(path, encoding="utf-8").read()
            if "draft: false" in content:
                title = "?"
                m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
                if m:
                    title = m.group(1).strip()[:60]
                published_today.append(f"- {slug} – {title}")

    # 2) Themenpool
    sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
    pool_msg = "?"
    free = -1
    try:
        import generate_drafts as g
        topics = g.load_topics()
        used = g.existing_titles()
        freie = [t for t in topics if not g.topic_already_covered(t["title"], used)]
        free = len(freie)
        pool_msg = f"{len(topics)} Themen, **{free} frei**"
        if free < 8:
            pool_msg += " ⚠️ (KI-Nachschub aktiv)"
    except Exception as e:
        pool_msg = f"Fehler: {e}"

    # 3) Letzter Publikationstag (AUDIT-FIX 27.08.2026: content-basiert statt
    #    `git log --grep='^content:'` – Commit-Messages verschwinden bei
    #    History-Konsolidierungen, der Artikelbestand nicht.)
    last_content = "?"
    try:
        import publish_day_check as pdc
        expected = pdc.last_publish_day()
        live, drafts = pdc.articles_on(expected)
        last_content = (
            f"{expected.isoformat()} "
            f"({['Mo','Di','Mi','Do','Fr','Sa','So'][expected.weekday()]}.): "
            f"{len(live)} live, {len(drafts)} Entwurf(e)"
        )
    except Exception:
        pass

    # 4) Tageslimit (aus Env, wenn gesetzt) – DAUERVORGABE: 2-3 Artikel
    #    pro Publikationstag (Mo/Mi/Fr), Defaults + Floor wie in engine_generate.py
    try:
        limit = max(int(os.environ.get("MAX_ARTIKEL_PRO_TAG") or "3"), 2)
        min_limit = max(int(os.environ.get("MIN_ARTIKEL_PRO_TAG") or "2"), 2)
        if min_limit > limit:
            min_limit = limit
    except ValueError:
        limit, min_limit = 3, 2

    lines = [
        "# 🤖 Bot-Status",
        "",
        f"> Automatisch aktualisiert: {now.strftime('%d.%m.%Y %H:%M')} Uhr (MESZ)",
        "",
        "## Heutiger Stand",
        "",
        f"- **Veröffentlicht heute:** {len(published_today)}/{limit} Artikel",
        *published_today,
        "",
        "## System",
        "",
        f"- **Themenpool:** {pool_msg}",
        f"- **Letzter Content-Commit:** {last_content}",
        f"- **Tageslimit:** {min_limit}–{limit} Artikel pro Publikationstag (Mo/Mi/Fr; steuerbar per Variablen MIN_ARTIKEL_PRO_TAG / MAX_ARTIKEL_PRO_TAG)",
        "",
        "## Bei Problemen",
        "",
        "- Offene Issues prüfen (Fehler-Alerting erstellt automatisch eins)",
        "- API-Keys: Settings → Secrets and variables → Actions",
        "- Workflow manuell starten: Actions → „Content-Engine v2“ → Run workflow",
        "",
        "---",
        "*Erzeugt von scripts/bot_status.py am Ende jedes Bot-Laufs.*",
    ]
    content = "\n".join(lines) + "\n"

    # Nur schreiben, wenn sich Inhalt geändert hat (kein Commit-Spam)
    if os.path.exists(STATUS_FILE):
        old = open(STATUS_FILE, encoding="utf-8").read()
        if old == content:
            print("BOT-STATUS.md unverändert – kein Update nötig.")
            return 0
    open(STATUS_FILE, "w", encoding="utf-8").write(content)
    print(f"BOT-STATUS.md aktualisiert ({len(published_today)} Artikel heute).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
