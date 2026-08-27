#!/usr/bin/env python3
"""weekly_digest.py – WOCHEN-DIGEST DER BLOG-AUTOMATIK (Agentur-Stufe-2, 27.08.)

Schließt die Lücke „Systemzustand ohne Datei-Jagd": Einmal pro Woche
(Workflow patches/…stage-2) kompiliert dieses Skript ALLE Kanäle zu
einem Markdown-Digest und veröffentlicht ihn als GitHub-Issue
(Label `digest`, Titel „📊 Wochen-Digest KW<n>/<Jahr>“). Der Digest der
Vorwoche wird automatisch geschlossen – es existiert maximal EIN
offener Digest. Ohne GITHUB_TOKEN: reine Markdown-Ausgabe (lokal testbar).

Quellen (alles offline, kein API-Zwang):
  · content/posts/*/index.md  → veröffentlichte Artikel der Woche
  · data/spam_history.jsonl   → Spam-Funde/Heilungen
  · data/audit/*.jsonl        → Audit-Events (Fehler/kritisch)
  · data/social_log.jsonl     → Mastodon-Posts
  · data/pin_history.jsonl    → Pinterest-Pins (Registry)
  · ENGINE-STATUS.md/BOT-STATUS.md → letzter Engine-Zustand
  · data/topics.yaml          → freie Themen (via generate_drafts)
  · GitHub API (optional, wenn GITHUB_TOKEN gesetzt): fehlgeschlagene
    Workflow-Läufe der Woche

AUFRUF: python3 scripts/weekly_digest.py [--weeks-back n]
"""
import datetime
import glob
import json
import os
import re
import sys
import urllib.request

WEEKS_BACK = 0
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)

DIGEST_LABEL = "digest"


def week_window(weeks_back=0):
    """Montag–Sonntag der Kalenderwoche vor `weeks_back` Wochen (ab heute)."""
    today = datetime.date.today()
    monday = today - datetime.timedelta(days=today.weekday(), weeks=weeks_back)
    return monday, monday + datetime.timedelta(days=6)


def iso_kw(monday):
    return monday.isocalendar()[1], monday.isocalendar()[0]


def load_jsonl(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]
    except (OSError, json.JSONDecodeError):
        return []


def published_articles(monday, sunday):
    out = []
    date_re = re.compile(r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", re.M)
    draft_re = re.compile(r"^draft:\s*true\b", re.M)
    title_re = re.compile(r"^title:\s*[\"']?(.+?)[\"']?\s*$", re.M)
    for f in sorted(glob.glob("content/posts/*/index.md")):
        head = open(f, encoding="utf-8", errors="ignore").read(2500)
        m = date_re.search(head)
        if not m:
            continue
        d = datetime.date.fromisoformat(m.group(1))
        if monday <= d <= sunday and not draft_re.search(head):
            t = title_re.search(head)
            out.append((d.isoformat(), f.split(os.sep)[-2],
                        t.group(1).strip() if t else "?"))
    return out


def count_week(rows, date_keys=("ts", "date"), monday=None, sunday=None):
    n = 0
    for row in rows:
        for key in date_keys:
            v = row.get(key, "")
            if not v:
                continue
            try:
                d = datetime.date.fromisoformat(str(v)[:10])
            except ValueError:
                continue
            if monday <= d <= sunday:
                n += 1
                break
    return n


def engine_status():
    for path, marker in (("ENGINE-STATUS.md", "**Status:**"),
                         ("BOT-STATUS.md", "**Status:**")):
        try:
            for line in open(path, encoding="utf-8"):
                if marker in line:
                    return line.strip().lstrip("* ").strip()
        except OSError:
            continue
    return "unbekannt"


def free_topics():
    try:
        sys.path.insert(0, "scripts")
        import generate_drafts as g
        topics = g.load_topics()
        used = g.existing_titles()
        free = [t for t in topics if not g.topic_already_covered(t["title"], used)]
        return len(topics), len(free)
    except Exception:
        return None, None


def failed_workflow_runs(monday, sunday):
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        return None
    url = (f"https://api.github.com/repos/{repo}/actions/runs"
           f"?created={monday.isoformat()}..{sunday.isoformat()}&per_page=100")
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "weekly-digest",
    })
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            runs = json.load(resp).get("workflow_runs", [])
        return sum(1 for r in runs if r.get("conclusion") == "failure")
    except Exception:
        return None


def build_markdown():
    for wb in range(WEEKS_BACK + 1):
        monday, sunday = week_window(wb)
        kw, year = iso_kw(monday)
        articles = published_articles(monday, sunday)
        spam = load_jsonl("data/spam_history.jsonl")
        spam_n = count_week(spam, monday=monday, sunday=sunday)
        audit_rows = []
        for f in glob.glob("data/audit/*.jsonl"):
            audit_rows += load_jsonl(f)
        audit_n = count_week(audit_rows, ("ts", "datetime", "date"), monday, sunday)
        social = load_jsonl("data/social_log.jsonl")
        social_n = count_week([s for s in social if s.get("ok")],
                              ("date",), monday, sunday)
        pins_n = count_week(load_jsonl("data/pin_history.jsonl"),
                            ("ts", "created", "date"), monday, sunday)
        total_topics, free_t = free_topics()
        failed = failed_workflow_runs(monday, sunday)

        lines = [f"## 📊 Wochen-Digest KW{kw}/{year} "
                 f"({monday.strftime('%d.%m.')}–{sunday.strftime('%d.%m.%Y')})", "",
                 "| Kanal | Wert |", "|---|---|",
                 f"| Veröffentlichte Artikel | {len(articles)} |",
                 f"| Mastodon-Posts | {social_n} |",
                 f"| Pinterest-Pins (Registry) | {pins_n} |",
                 f"| Spam-Wachen-Funde/-Heilungen | {spam_n} |",
                 f"| Audit-Events | {audit_n} |",
                 f"| Fehlgeschlagene Workflow-Läufe | "
                 f"{failed if failed is not None else 'n/a (kein Token)'} |",
                 f"| Themenpool frei / gesamt | "
                 f"{free_t if free_t is not None else '?'} / "
                 f"{total_topics if total_topics is not None else '?'} |",
                 f"| Engine-Status (zuletzt) | {engine_status()} |", ""]
        if articles:
            lines.append("### Neue Artikel")
            lines += [f"- {d} · [{t}](https://franksfinanzcheck.de/posts/{slug}/)"
                      for d, slug, t in articles]
            lines.append("")
        lines.append("---")
        lines.append("_Erzeugt von scripts/weekly_digest.py · Agentur-Stufe-2, 27.08.2026_")
        return "\n".join(lines), kw, year
    return "", None, None


def publish_issue(md, kw, year):
    token = os.environ.get("GITHUB_TOKEN")
    repo = os.environ.get("GITHUB_REPOSITORY", "")
    if not token or not repo:
        print("(Kein GITHUB_TOKEN – Digest nur als Markdown ausgegeben.)")
        return
    api = f"https://api.github.com/repos/{repo}"
    headers = {"Authorization": f"Bearer {token}",
               "Accept": "application/vnd.github+json",
               "User-Agent": "weekly-digest"}
    title = f"📊 Wochen-Digest KW{kw}/{year}"

    def call(url, data=None, method="GET"):
        req = urllib.request.Request(url, headers=headers,
                                     data=json.dumps(data).encode() if data else None)
        if method != "GET":
            req.get_method = lambda: method
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}

    # Vorwochen-Digests schließen (max. 1 offener Digest)
    try:
        issues = call(f"{api}/issues?labels={DIGEST_LABEL}&state=open")
        for i in issues:
            call(f"{api}/issues/{i['number']}", {"state": "closed"}, "PATCH")
    except Exception as exc:  # noqa: BLE001
        print(f"⚠ Digest-Close: {exc}")
    # Label sicherstellen + Issue erstellen
    try:
        call(f"{api}/labels", {"name": DIGEST_LABEL, "color": "1d76db"},
             "POST")
    except Exception:
        pass  # existiert schon
    issue = call(f"{api}/issues", {"title": title, "body": md,
                                   "labels": [DIGEST_LABEL]}, "POST")
    print(f"✅ Digest-Issue #{issue.get('number')} erstellt.")


def main():
    if "--weeks-back" in sys.argv:
        globals()["WEEKS_BACK"] = int(sys.argv[sys.argv.index("--weeks-back") + 1])
    md, kw, year = build_markdown()
    print(md)
    if kw:
        publish_issue(md, kw, year)
    return 0


if __name__ == "__main__":
    sys.exit(main())
