#!/usr/bin/env python3
"""engine_issue.py – Tagesdefizit der Content-Engine als GitHub-Issue.

Aufruf: python3 scripts/engine_issue.py --deficit

Öffnet (oder kommentiert) ein Issue, wenn an einem Publikationstag
weniger LIVE-Artikel als MIN_ARTIKEL_PRO_TAG entstanden sind.
Schließt das Issue, sobald das Ziel erreicht ist.

Benötigt GH_TOKEN (github.token im Workflow). Ohne Token: Exit 0 + Hinweis.
"""
from __future__ import annotations

import datetime
import os
import subprocess
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import cadence_guard as cg  # noqa: E402

MARKER = "<!-- engine-deficit-id: tagesdefizit -->"
LABEL = "engine-deficit"


def _gh(*args: str) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    return subprocess.run(
        ["gh", *args],
        cwd=BLOG_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def _ensure_label() -> None:
    listed = _gh("label", "list", "--json", "name", "--jq", ".[].name")
    if LABEL not in (listed.stdout or "").splitlines():
        _gh("label", "create", LABEL, "--color", "d93f0b",
            "--description", "Content-Engine: LIVE unter Tagesmindestziel")


def _open_issue_number() -> str:
    proc = _gh("issue", "list", "--label", LABEL, "--state", "open",
               "--json", "number,body",
               "--jq",
               f'[.[] | select(.body // "" | contains("{MARKER}")) | .number] | first // ""')
    return (proc.stdout or "").strip()


def _diagnose() -> str:
    """Warum war heute zu wenig LIVE? – Ursachen statt Symptom.

    ISSUE #521 (02.10.2026): Das alte Defizit-Issue meldete „0/2 LIVE“ und
    verwies auf das Runbook. Es stand damit genau so ratlos da wie der
    Leser: Dass vier Themen produziert, aber von Gates gestoppt wurden,
    dass 47 Themen durch Phantom-Erfolge gesperrt waren und dass der
    Prüfstapel der Fachfreigabe mit 11 Artikeln dicht war, musste man sich
    aus drei Reports zusammensuchen. Ein Alarm ohne Diagnose erzeugt
    Arbeit statt sie zu ersparen – deshalb trägt das Issue die Lage jetzt
    bei sich.

    Fail-open: Eine kaputte Diagnose darf den Alarm nie verschlucken.
    """
    zeilen = []
    try:
        sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
        import engine_capacity as ec
        lage = ec.lage()
        symbol = {"ok": "✅", "knapp": "⚠️", "erschoepft": "🛑"}[lage["verdikt"]]
        zeilen.append("### Lage der Engine\n")
        zeilen.append(f"{symbol} {lage['befund']}\n")
        zeilen.append(
            f"| Bahn | Themen | frei disponierbar |\n"
            f"|---|---:|---:|\n"
            f"| AUTO (darf live gehen) | {lage['themen_auto']} "
            f"| **{lage['frei_auto']}** |\n"
            f"| FACHFREIGABE (YMYL, braucht Mensch) "
            f"| {lage['themen_fachfreigabe']} "
            f"| {lage['frei_fachfreigabe']} |\n")
        fach = lage["fachfreigabe"]
        if not fach["geoeffnet"]:
            zeilen.append(
                f"\n**Fachfreigabe-Bahn ist geschlossen:** {fach['grund']}. "
                f"Hochrisiko-Themen können heute also nicht ausweichen – "
                f"sie warten, statt einen LIVE-Slot zu verbrennen.\n")
        for w in lage["warnungen"]:
            zeilen.append(f"\n- ⚠️ {w}")
        if lage["naechste_auto"]:
            zeilen.append(
                f"\n\n**Nächste freie AUTO-Themen:** "
                f"{' · '.join(lage['naechste_auto'][:3])}\n")
    except Exception as e:  # noqa: BLE001 – Alarm geht IMMER raus
        zeilen.append(f"\n_(Kapazitäts-Diagnose nicht verfügbar: {e})_\n")

    # Entwürfe, die fertig sind, aber auf einen Menschen warten.
    try:
        import json as _json
        q = os.path.join(BLOG_DIR, "data", "editorial_review_queue.json")
        if os.path.exists(q):
            with open(q, encoding="utf-8") as fh:
                daten = _json.load(fh)
            # open_live/open_drafts sind Zähler, keine Listen.
            offen_live = int(daten.get("open_live") or 0)
            offen_entw = int(daten.get("open_drafts") or 0)
            if offen_live or offen_entw:
                zeilen.append(
                    f"\n### Wartet auf fachliche Freigabe\n\n"
                    f"{offen_entw} Entwürfe und {offen_live} Live-Artikel "
                    f"liegen in der YMYL-Prüfqueue. Diese Arbeit ist "
                    f"**nicht automatisierbar** – sie läuft über "
                    f"„Redaktionelle YMYL-Prüfqueue“.\n")
    except Exception:  # noqa: BLE001
        pass

    zeilen.append(
        "\n### Erste Schritte\n\n"
        "```bash\n"
        "python3 scripts/engine_capacity.py   # Lage in einem Blick\n"
        "python3 scripts/reserve_topics.py --abgleich  # Phantom-Sperren lösen\n"
        "python3 scripts/reserve_topics.py --bericht   # Themen-Gedächtnis\n"
        "```\n\n"
        "Hintergrund: `CONTENT-ENGINE-KAPAZITAET-PREMIUM-2026-10-02.md`\n")
    return "".join(zeilen)


def main() -> int:
    if "--deficit" not in sys.argv:
        print("Nutzung: python3 scripts/engine_issue.py --deficit")
        return 0

    today = datetime.date.today()
    if today.weekday() not in cg.PUBLICATION_DAYS:
        print("Kein Publikationstag – Defizit-Wache übersprungen.")
        return 0

    min_n = int(os.environ.get("MIN_ARTIKEL_PRO_TAG") or "2")
    if min_n < 2:
        min_n = 2
    posts = cg.load_posts()
    live = [p for p in posts if not p["draft"] and p["date"] == today]
    n = len(live)
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    if not token:
        print("Kein GH_TOKEN – Defizit nur geloggt, kein Issue.")
        print(f"Heute LIVE: {n}/{min_n}")
        return 0

    _ensure_label()
    num = _open_issue_number()

    if n >= min_n:
        if num:
            _gh("issue", "close", num, "--comment",
                f"✅ {today.isoformat()}: LIVE {n}/{min_n} – Tagesziel erfüllt.")
            print(f"Issue #{num} geschlossen (Ziel erfüllt).")
        else:
            print(f"Kein Defizit ({n}/{min_n} LIVE).")
        return 0

    body = (
        f"## Content-Engine: LIVE unter Mindestziel\n\n"
        f"- **Tag:** {today.isoformat()}\n"
        f"- **LIVE heute:** {n} (Ziel ≥ {min_n})\n"
        f"- **Slugs:** {', '.join(p['slug'] for p in live) or '–'}\n\n"
        f"{_diagnose()}\n"
        f"Runbook: Actions → Content-Engine v2 → Phase 1.\n\n"
        f"{MARKER}\n"
    )
    title = f"Content-Engine: Tagesdefizit {today.isoformat()} ({n}/{min_n} LIVE)"
    if not num:
        created = _gh("issue", "create", "--title", title, "--label", LABEL, "--body", body)
        print(created.stdout or created.stderr)
    else:
        _gh("issue", "comment", num, "--body",
            f"**{datetime.datetime.now(datetime.timezone.utc):%Y-%m-%d %H:%M} UTC** – weiterhin {n}/{min_n} LIVE.\n\n{body}")
        print(f"Issue #{num} kommentiert.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
