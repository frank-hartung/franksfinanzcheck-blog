#!/usr/bin/env python3
"""engine_issue.py – Erstellt ein GitHub-Issue, wenn die Content-Engine v2
einen Artikel nur als ENTWURF sichern konnte (Draft-Rettung aktiv).

Dedupe: Es wird nur ein offenes Issue gleichzeitig erstellt.

Aufruf (im GitHub-Actions-Kontext):
  python3 scripts/engine_issue.py
"""
import json
import os
import urllib.request

def main():
    token = os.environ.get("GITHUB_TOKEN", "")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("Kein GITHUB_TOKEN/GITHUB_REPOSITORY – übersprungen.")
        return 0

    api = f"https://api.github.com/repos/{repo}/issues"
    headers = {"Authorization": f"token {token}",
               "Accept": "application/vnd.github+json"}

    # Dedupe: existiert bereits ein offenes Issue mit dem Titel?
    req = urllib.request.Request(f"{api}?state=open&per_page=50", headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            existing = json.loads(resp.read().decode())
    except Exception as e:  # noqa: BLE001
        print(f"List-Fehler (nicht kritisch): {e}")
        return 1
    for issue in existing:
        title = issue.get("title", "")
        if (title.startswith("⚠ Content-Engine") or title.startswith("📝 Content-Engine")) and not issue.get("pull_request"):

            print(f"Issue existiert bereits: #{issue['number']}")
            return 0

    body = (
        "Es liegt mindestens 1 neuer Artikel als **ENTWURF** (`draft: true`) bereit.\n\n"
        "Das kann zwei Gründe haben:\n"
        "1. **Normalfall (seit 13.08.):** Manuelle Freigabe ist aktiv "
        "(`AUTO_PUBLISH` ist nicht auf `1` gesetzt) – der Artikel hat die "
        "Qualitätsprüfung bestanden und wartet nur auf dein OK.\n"
        "2. **Ausnahme:** Die automatische Qualitätsprüfung (oder die KI-APIs) "
        "hat die Profi-Schwelle nicht erreicht (`engine_level: \"draft\"` im "
        "Frontmatter) – dann bitte kurz gegenlesen/nachbessern.\n\n"
        "**Bitte prüfen:**\n"
        "1. `ENGINE-STATUS.md` ansehen (Ebene, Fehler)\n"
        "2. Den Entwurf unter `content/posts/` suchen (`draft: true`)\n"
        "3. Freigeben: `draft: false` setzen (oder `python3 scripts/publish.py <slug>`) "
        "– der nächste Deploy veröffentlicht ihn.\n\n"
        "_Automatisch erstellt von der Content-Engine v2._"
    )
    data = json.dumps({"title": "📝 Content-Engine: Entwurf wartet auf Freigabe",
                       "body": body}).encode()

    req = urllib.request.Request(api, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            created = json.loads(resp.read().decode())
            print(f"Issue erstellt: #{created.get('number')}")
            return 0
    except Exception as e:  # noqa: BLE001
        print(f"Issue-Fehler (nicht kritisch): {e}")
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
