#!/usr/bin/env python3
"""engine_issue.py – Erstellt GitHub-Issues für Content-Engine-v2-Störungen.

Zwei Modi (Dedupe je Titel-Präfix, jeweils nur ein offenes Issue):

  (1) Default (Draft-Rettung):
      Die Engine hat einen Artikel nur als ENTWURF sichern können.
      → Issue "⚠ Content-Engine: Entwurf wartet auf Freigabe"

  (2) --deficit (Tagesziel unter Mindestwert, 26.08.2026):
      Am Ende des TAGESLÄUFS ist die live gegangene Stückzahl für heute
      unter MIN_ARTIKEL_PRO_TAG (Dauervorgabe CADENCE-REPORT.md Regel 2:
      2–3 Artikel pro Publikationstag). Kein Verstoß (Maximum), aber
      das Minimum wurde nicht erreicht – z. B. weil Slots an API-Limits
      scheiterten oder Artikel am Publish-Gate gescheitert sind.
      → Issue "⚠ Content-Engine: Tagesziel unter Mindestwert" mit der
        exakten Lage (live heute / Min / Max / Vorschlag: Folge-Slot
        oder manueller Top-up). Bei Wiederherstellung (live >= Min)
        wird das offene Issue automatisch geschlossen.

Aufruf (im GitHub-Actions-Kontext):
  python3 scripts/engine_issue.py
  python3 scripts/engine_issue.py --deficit
"""
import json
import os
import re
import sys
import urllib.request

DRAFT_PREFIX = "⚠ Content-Engine"          # "Entwurf wartet auf Freigabe"
DEFICIT_PREFIX = "⚠ Content-Engine: Tagesziel unter Mindestwert"


def _api():
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("Kein GITHUB_TOKEN/GITHUB_REPOSITORY – übersprungen.")
        return None
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github+json"}
    return f"https://api.github.com/repos/{repo}", headers


def _open_issues(api, headers):
    req = urllib.request.Request(f"{api}/issues?state=open&per_page=100",
                                 headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return [i for i in json.loads(resp.read().decode())
                    if not i.get("pull_request")]
    except Exception as e:  # noqa: BLE001
        print(f"List-Fehler (nicht kritisch): {e}")
        return None


def _create_issue(api, headers, title, body):
    data = json.dumps({"title": title, "body": body}).encode()
    req = urllib.request.Request(api, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=20) as resp:
        created = json.loads(resp.read().decode())
        print(f"Issue erstellt: #{created.get('number')}")
        return created.get("number")


def _close_issue(api, headers, number):
    req = urllib.request.Request(f"{api}/issues/{number}",
                                 data=json.dumps({"state": "closed"}).encode(),
                                 headers={**headers,
                                          "Content-Type": "application/json"},
                                 method="PATCH")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            print(f"Issue #{number} geschlossen (Ziel wieder erfüllt).")
    except Exception as e:  # noqa: BLE001
        print(f"Close-Fehler (nicht kritisch): {e}")


def main():
    if "--deficit" in sys.argv[1:]:
        return main_deficit()
    return main_draft()


def main_draft():
    endpoint = _api()
    if not endpoint:
        return 0
    api, headers = endpoint
    existing = _open_issues(api, headers)
    if existing is None:
        return 1
    for issue in existing:
        if issue.get("title", "").startswith(DRAFT_PREFIX) and \
           not issue.get("title", "").startswith(DEFICIT_PREFIX):
            print(f"Issue existiert bereits: #{issue['number']}")
            return 0

    body = (
        "Die Content-Engine v2 hat einen Artikel nur als **ENTWURF** sichern können, "
        "weil die automatische Qualitätsprüfung (oder die KI-APIs) die Profi-Schwelle "
        "nicht erreicht hat.\n\n"
        "**Bitte prüfen:**\n"
        "1. `ENGINE-STATUS.md` ansehen (Ebene, Fehler)\n"
        "2. Den Entwurf unter `content/posts/` suchen (`draft: true`)\n"
        "3. Artikel fertigstellen und `draft: false` setzen – der nächste Deploy "
        "veröffentlicht ihn.\n\n"
        "_Automatisch erstellt von der Content-Engine v2._"
    )
    try:
        _create_issue(api, headers,
                      "⚠ Content-Engine: Entwurf wartet auf Freigabe", body)
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"Issue-Fehler (nicht kritisch): {e}")
        return 1


def main_deficit():
    """Endkontrolle des Tageslaufs: live-gezählte Artikel HEUTE vs. Min/Max.

    Zählt nach dem FRONTMATTER-Datum (Single Source of Truth, s.
    cadence_guard) – nicht nach dem Ordner-Präfix (bleibt bei Re-Queue
    alt)."""
    import sys as _sys
    _sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cadence_guard as cg
    import datetime

    today = datetime.date.today()
    min_n = int(os.environ.get("MIN_ARTIKEL_PRO_TAG", str(cg.MIN_ARTIKEL_PRO_TAG)))
    max_n = int(os.environ.get("MAX_ARTIKEL_PRO_TAG", str(cg.MAX_ARTIKEL_PRO_TAG)))

    posts = cg.load_posts()
    live = len(cg.published_on(posts, today))
    drafts = sum(1 for p in posts
                 if p["date"] == today and p["draft"])
    today_iso = today.isoformat()

    if not cg.is_publication_day(today):
        print(f"Deficit-Check: heute ({today_iso}) ist kein Publikationstag – übersprungen.")
        return 0
    if live >= min_n:
        print(f"Deficit-Check: {live} live heute ≥ Minimum {min_n} – Ziel erfüllt.")
    else:
        print(f"⚠ Deficit: nur {live} live heute, Minimum {min_n} "
              f"(Max {max_n}, {drafts} Entwürfe warten).")

    endpoint = _api()
    if not endpoint:
        return 0
    api, headers = endpoint
    existing = _open_issues(api, headers)
    if existing is None:
        return 1
    open_deficit = [i for i in existing
                    if i.get("title", "").startswith(DEFICIT_PREFIX)]

    if live >= min_n:
        for issue in open_deficit:
            _close_issue(api, headers, issue["number"])
        return 0
    if open_deficit:
        print(f"Deficit-Issue existiert bereits: #{open_deficit[0]['number']}")
        return 0

    body = (
        f"Der Tageslauf der Content-Engine v2 endet mit **{live} live** "
        f"veröffentlichten Artikeln für heute ({today}), "
        f"**Minimum laut Dauervorgabe ist {min_n}** "
        f"(Maximum {max_n}, {drafts} Entwürfe warten unter `content/posts/`).\n\n"
        "**Mögliche Ursachen:**\n"
        "- KI-API-Limits/Timeouts in einem der 3 Slots\n"
        "- Artikel scheiterten am Publish-Gate (siehe `CADENCE-GATE-REPORT.md` "
          "und Publish-Gate-Log)\n"
        "- Cadenz-Re-Queue hielt Slots für Bestand reserviert\n\n"
        "**Empfehlung:**\n"
        "1. `ENGINE-STATUS.md` und das Action-Log des Tageslaufs prüfen\n"
        "2. Warten, bis der nächste Publikationstag den Rückstand mit auffüllt "
        "(Selbstheilung: 2–3 Artikel/Tag), ODER\n"
        "3. Manuell einen Slot nachlaufen "
        "(`workflow_dispatch` der Content-Engine v2) bzw. Entwürfe freigeben.\n\n"
        "_Automatisch erstellt am Ende des Tageslaufs (Selbstheilung: "
        "Sichtbarkeit bei unerreichtem Minimum). Schließt sich automatisch, "
        "sobald wieder ≥ " + str(min_n) + " Artikel live sind._"
    )
    try:
        _create_issue(api, headers, DEFICIT_PREFIX, body)
        return 0
    except Exception as e:  # noqa: BLE001
        print(f"Issue-Fehler (nicht kritisch): {e}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
