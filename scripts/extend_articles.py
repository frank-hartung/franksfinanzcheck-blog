#!/usr/bin/env python3
"""KI-Verlängerung zu kurzer Artikel (Selbstheilung, Profi-Format)
für FranksFinanzcheck.

Findet alle Artikel unter einer Mindest-Wortzahl (Default 700) und lässt
sie per KI (Groq/Gemini, 2 Versuche, Provider-Rotation) auf Ziel-Länge
bringen. Der Artikel-Body wird durch die KI-Erweiterung ersetzt; das
Frontmatter (Titel, Description, Keywords, Cover …) bleibt unangetastet.

QUALITÄTS-GATES nach der Generierung (deterministisch):
  - neue Wortzahl >= max(MIN_WORDS, alte + 50)
  - mindestens 4 H2-Abschnitte
  - keine KI-Floskeln (PROFI_FLOSKELN)
  - kein Frontmatter-Rest („TITLE:", „DESCRIPTION:") im Body

KONSERVATIV: Artikel werden NUR erweitert, wenn sie unter der Schwelle
liegen und die KI-Antwort alle Gates besteht – sonst bleibt der
Originaltext unverändert (kein Qualitätsverlust möglich).

Nutzung:
  python3 scripts/extend_articles.py                # alle < 700 Wörter
  python3 scripts/extend_articles.py --min 600      # eigene Schwelle
  python3 scripts/extend_articles.py --dry          # nur anzeigen
  python3 scripts/extend_articles.py --slug X       # nur ein Artikel

Exit: 0 = alle behandelten Artikel jetzt ok · 1 = offene (oder trotz
KI nicht erreichbare) Artikel.
"""
import os
import re
import sys
import json
import time
import glob
import random
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import groq_config
import length_policy as lp
MIN_CHARS = int(os.environ.get("LENGTH_MIN_CHARS") or lp.POSTS["target_min_chars"])
MIN_WORDS = int(os.environ.get("LENGTH_MIN_WORDS") or max(1400, MIN_CHARS // 7))
# Zielzone relativ zum Floor: nie unter der Schwelle landen, sonst Heilungs-Loop.
TARGET_MIN = None
TARGET_MAX = None 

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0 Safari/537.36")

PROFI_FLOSKELN = {
    "in der heutigen schnelllebigen welt", "in der heutigen zeit",
    "in einer welt", "es ist wichtig zu beachten", "es ist ratsam",
    "zusammenfassend lässt sich sagen", "fazit: zusammenfassend",
    "tauchen sie ein", "entdecken sie die welt", "in diesem artikel werden wir",
    "dieser artikel beleuchtet", "in der heutigen gesellschaft",
    "die welt verändert sich", "immer mehr menschen", "ein beliebtes thema",
    "in den letzten jahren hat sich", "nicht zuletzt",
}


def http_json(url, data=None, headers=None, timeout=90):
    hdrs = {"User-Agent": UA}
    if headers:
        hdrs.update(headers)
    req = urllib.request.Request(url, data=data, headers=hdrs)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _retry(fn, attempts=3, base_delay=4.0):
    last_err = None
    for i in range(attempts):
        try:
            return fn()
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 429:
                time.sleep(base_delay * (i + 1))
                continue
            if e.code in (401, 403):
                break
            time.sleep(base_delay * (i + 1))
        except (TimeoutError, urllib.error.URLError, ConnectionError) as e:
            last_err = str(e)
            time.sleep(base_delay * (i + 1))
    raise RuntimeError(last_err or "API nicht erreichbar")


def call_groq(prompt):
    return groq_config.chat(
        prompt, temperature=0.4, max_tokens=6000, raise_on_error=True,
    )


def call_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        return None
    model = os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
    body = {"contents": [{"parts": [{"text": prompt}]}]}
    data = json.dumps(body).encode("utf-8")

    def _call():
        resp = http_json(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}"
            f":generateContent?key={key}",
            data=data,
            headers={"Content-Type": "application/json"},
        )
        return resp["candidates"][0]["content"]["parts"][0]["text"]

    return _retry(_call)


def clean_words(text):
    t = re.sub(r"[#*_>`|~\[\]()-]", " ", text)
    return len(re.findall(r"\w+", t))


def article_words(path):
    c = open(path, encoding="utf-8").read()
    parts = c.split("---", 2)
    body = parts[2] if len(parts) >= 3 else c
    return clean_words(body), body


def article_chars(path):
    c = open(path, encoding="utf-8").read()
    _w, chars = lp.measure(c)
    return chars


def build_prompt(title, keywords, body, target_min, target_max):
    kw = ", ".join(keywords[:5]) if keywords else ""
    return (
        "Du bist ein erfahrener deutscher Finanz-Ratgeber-Redakteur. "
        "Erweitere den folgenden Blog-Artikel um ECHTEN Mehrwert, damit er "
        f"die Profi-Länge von {target_min}-{target_max} Wörtern erreicht "
        f"(aktuell kürzer).\n\n"
        "REGLEN:\n"
        "- Behalte Titel, Struktur, Stil (Du-Form, direkte Ansprache) und "
        "alle vorhandenen Inhalte/Abschnitte bei.\n"
        "- Ergänze Tiefe, KEINE Füllwörter: zusätzliche konkrete Tipps, "
        "Zahlen und Beispiele, Vor-/Nachteile, ggf. eine Vergleichstabelle, "
        "1-2 zusätzliche FAQ-Fragen mit ehrlichen Antworten.\n"
        "- Baue die Keywords natürlich ein (kein Stuffing).\n"
        "- Keine KI-Floskeln wie ›In der heutigen Welt‹, ›Zusammenfassend "
        "lässt sich sagen‹, ›Es ist wichtig zu beachten‹.\n"
        "- Markdown-Format wie im Original (##-Überschriften, Listen, "
        "Tabellen, **fett**).\n"
        "- Gib NUR den vollständigen neuen Artikel-Body zurück – OHNE "
        "Frontmatter, OHNE Titel-Zeile, OHNE Erklärungen oder Einleitung.\n\n"
        f"TITEL: {title}\n"
        f"KEYWORDS: {kw}\n\n"
        f"ARTIKEL-BODY:\n{body}"
    )


def extend_article(path, min_words, dry=False, min_chars=None):
    """Versucht, einen Artikel zu verlängern. Rückgabe (ok, info)."""
    content = open(path, encoding="utf-8").read()
    parts = content.split("---", 2)
    if len(parts) < 3:
        return False, "kein Frontmatter"
    front = parts[1]
    body = parts[2]
    words, _ = article_words(path)
    chars = article_chars(path)
    floor_chars = min_chars if min_chars is not None else MIN_CHARS
    if words >= min_words and chars >= floor_chars:
        return True, f"bereits {words} Wörter / {chars} Zeichen"

    m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', front, re.M)
    title = m.group(1).strip() if m else ""
    kws = re.search(r'^keywords:\s*\[(.*?)\]', front, re.M | re.S)
    keywords = []
    if kws:
        keywords = [k.strip().strip("\"'") for k in kws.group(1).split(",")]
    keywords = [k for k in keywords if k]

    providers = [("gemini", call_gemini), ("groq", call_groq)]
    random.shuffle(providers)
    prompt = build_prompt(title, keywords, body, TARGET_MIN, TARGET_MAX)

    for name, fn in providers:
        try:
            raw = fn(prompt)
        except Exception as exc:  # noqa: BLE001
            print(f"    ✗ {name}: {exc}")
            continue
        if not raw:
            continue
        new_body = raw.strip()
        # Frontmatter-Reste entfernen/ablehnen
        if re.search(r"^(TITLE|DESCRIPTION|KEYWORDS|FRONTMATTER)\s*:", new_body, re.M | re.I):
            print(f"    ✗ {name}: Antwort enthielt Frontmatter-Reste")
            continue
        # Eventuell eingerahmten Markdown-Codeblock entfernen
        new_body = re.sub(r"^```(?:markdown)?\s*|\s*```$", "", new_body)
        nw = clean_words(new_body)
        nh2 = len(re.findall(r"^##\s", new_body, re.M))
        low = new_body.lower()
        floskeln = [f for f in PROFI_FLOSKELN if f in low]
        new_chars = len(re.sub(r"\s+", " ", new_body).strip())
        if nw < max(min_words, words + 50) or new_chars < floor_chars:
            print(f"    ✗ {name}: nur {nw} Wörter / {new_chars} Zeichen "
                  f"(Ziel ≥ {max(min_words, words + 50)} Wörter und ≥ {floor_chars} Zeichen)")
            continue
        if nh2 < 4:
            print(f"    ✗ {name}: nur {nh2} H2-Abschnitte")
            continue
        if floskeln:
            print(f"    ✗ {name}: KI-Floskeln {floskeln[:2]}")
            continue
        if dry:
            return True, f"DRY-RUN ok: {nw} Wörter / {nh2} H2 (via {name})"
        with open(path, "w", encoding="utf-8") as f:
            f.write("---" + front + "---" + new_body.strip() + "\n")
        print(f"    ✅ {name}: {words} → {nw} Wörter ({nh2} H2)")
        time.sleep(4)  # Rate-Limit-Schonung
        return True, f"verlängert {words} → {nw} Wörter via {name}"
    return False, f"KI lieferte kein gültiges Ergebnis (war {words} Wörter)"


def main():
    global TARGET_MIN, TARGET_MAX
    min_words = MIN_WORDS
    min_chars = MIN_CHARS
    TARGET_MIN = min_words + 150
    TARGET_MAX = min_words + 800
    if "--min" in sys.argv:
        min_words = int(sys.argv[sys.argv.index("--min") + 1])
    if "--min-chars" in sys.argv:
        min_chars = int(sys.argv[sys.argv.index("--min-chars") + 1])
        min_words = max(min_words, min_chars // 7)
        TARGET_MIN = min_words + 150
        TARGET_MAX = min_words + 800
    dry = "--dry" in sys.argv
    only = None
    if "--slug" in sys.argv:
        only = sys.argv[sys.argv.index("--slug") + 1]

    heal_per_run = int(os.environ.get("LENGTH_HEAL_PER_RUN") or "8")
    files = sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md")))
    targets = []
    for f in files:
        slug = os.path.basename(os.path.dirname(f))
        if only and slug != only:
            continue
        w, _ = article_words(f)
        c = article_chars(f)
        if w < min_words or c < min_chars:
            targets.append((f, slug, w))
    if not targets:
        print(f"Keine Artikel unter {min_words} Wörtern / {min_chars} Zeichen – alles im Rahmen.")
        return 0

    if len(targets) > heal_per_run:
        print(f"    (Ration: {heal_per_run} von {len(targets)}, Rest in folgenden Läufen)")
    print(f"{'DRY-RUN: ' if dry else ''}Verlängerung von {min(len(targets), heal_per_run)} von {len(targets)} Artikeln "
          f"unter {min_words} Wörtern (Ziel {TARGET_MIN}-{TARGET_MAX}) …")
    ok_count = 0
    failed = []
    for f, slug, w in targets[:heal_per_run]:
        print(f"  ▶ {slug} ({w} Wörter)")
        ok, info = extend_article(f, min_words, dry=dry, min_chars=min_chars)
        if ok:
            ok_count += 1
        else:
            failed.append((slug, info))
    print(f"\nFertig: {ok_count}/{len(targets)} erfolgreich"
          + ("" if dry else "") + ".")
    for slug, info in failed:
        print(f"  ⚠ {slug}: {info}")

    if ok_count and not dry and not only:
        try:
            from audit_log import log_event
            log_event(module="extend_articles", action="apply",
                      input={"min_words": min_words,
                             "targets": len(targets)},
                      output={"ok": ok_count, "failed": len(failed)},
                      status="ok" if not failed else "partial")
        except Exception:
            pass
    return 1 if failed and not dry else 0


if __name__ == "__main__":
    sys.exit(main())
