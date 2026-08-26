#!/usr/bin/env python3
# ============================================================
#  LENGTH-GUARD – Artikel-Längen-Wächter mit Selbstheilung
#  (überwacht · hält ein · heilt selbst)
#
#  POLITIK (Fundament: Audit 2026-08-10, Bestand 74 Artikel, Median
#  744 Wörter; Zielgrößen für Affiliate-Ratgeber mit Check24/Tarifcheck):
#
#    Typ „posts"  : Ziel 1.200–2.200 Wörter | Warnung < 1.000 |
#                   HEILUNG < 900 | „zu lang"-Hinweis ab 2.800
#    Typ „pillar" : Ziel 2.500–4.000 Wörter | Warnung < 1.800 |
#                   HEILUNG < 1.800  (Pillar = Silo-Anker, MUSS dick sein)
#
#  WARUM DAS WICHTIG IST (Affiliate-Kontext):
#    Check24-/Tarifcheck-Artikel konkurrieren mit Vergleichsportalen
#    selbst – unter ~1.000 Wörtern droht Googles Thin-/Affiliate-
#    Filter; die Pillar-Seiten tragen dein Silo (interne Links),
#    400–560 Wörter sind dafür strukturell zu dünn.
#
#  SELBSTHEILUNG (mit --ai + Groq/Gemini, Keys liegen als Secrets vor):
#    KI ergänzt MEHRWERT-Module (kein Fülltext!): Rechenbeispiel mit
#    echten Zahlen, „Typische Fehler"-Liste, Mini-Tabelle, +2 FAQ.
#    Einfügung VOR „## Fazit" (bzw. vor dem Disclaimer).
#    Verifikations-Gate (sonst VERWORFEN): Mindest-Zuwachs erreicht,
#    keine Links verloren, Überschriften-Balance, Disclaimer intakt.
#    Setzt lastmod (Frische-Signal) und protokolliert in die History.
#
#  RÜCKSTANDS-ABBAU: --backlog N heilt die N kürzesten Alt-Artikel
#  (Pillars zuerst!) – gedacht für den Wochen-Workflow (3/Woche),
#  NICHT für die Engine (dort nur --new-only). Ruhiger, planbarer Marsch.
#
#  Aufruf:
#    python3 scripts/length_guard.py                        # Report (alle)
#    python3 scripts/length_guard.py --fix --ai --new-only  # Engine-Modus
#    python3 scripts/length_guard.py --fix --ai --backlog 3 # Wochen-Modus
#    python3 scripts/length_guard.py --dry-run
#
#  Ausgabe: LENGTH-REPORT.md (Buckets, Kürzeste, Geheilte) +
#           data/length_history.jsonl · idempotent · Exit 0 = OK.
# ============================================================

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "LENGTH-REPORT.md"
HISTORY = ROOT / "data" / "length_history.jsonl"

import groq_config

GROQ_KEY = groq_config.api_key()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

DO_FIX = "--fix" in sys.argv
USE_AI = "--ai" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv
# Hoheits-Aufteilung (11.08.2026 mit Betreiber abgesprochen):
#   posts  -> check_length.py (Generierungs-eigen)
#   pillar -> length_guard.py (hier, 2.500+ Wörter)
# Aufruf in der Engine nur mit --scope pillar; Skript allein -> all.
SCOPE = "all"
if "--scope" in sys.argv:
    _i = sys.argv.index("--scope")
    if _i + 1 < len(sys.argv):
        SCOPE = sys.argv[_i + 1].lower()
        if SCOPE not in ("pillar", "posts", "all"):
            sys.exit("FEHLER: --scope muss pillar|posts|all sein")
BACKLOG = int(sys.argv[sys.argv.index("--backlog") + 1]) if "--backlog" in sys.argv else 0

POLICY = {
    "posts":  {"target_min": 1200, "target_max": 2200, "warn": 1000, "heal": 900,  "fat": 2800},
    "pillar": {"target_min": 2500, "target_max": 4000, "warn": 1800, "heal": 1800, "fat": 5000},
}


def classify(path: Path) -> str:
    return "pillar" if "pillar" in path.parts else "posts"


def measure(text: str) -> tuple[int, int]:
    """Wörter & Zeichen des eigentlichen Artikels (ohne Front-Matter/Code/Tabellen-Sep)."""
    t = re.sub(r"^---.*?^---", "", text, flags=re.S | re.M)
    t = re.sub(r"```.*?```", "", t, flags=re.S)
    t = re.sub(r"^\|[-| :]*\|$", "", t, flags=re.M)
    chars = len(re.sub(r"\s+", " ", t).strip())
    words = len(re.sub(r"[|#*>\[\]()]", " ", t).split())
    return words, chars


def fm_field(text: str, name: str) -> str:
    m = re.search(rf'^{name}:\s*["\']?(.*?)["\']?\s*$', text[:2500], re.M)
    return m.group(1).strip() if m else ""


# ------------------------------------------------------------ KI-Heilung

def ai(system: str, prompt: str, max_tokens: int = 3500) -> str | None:
    for provider, key in (("groq", GROQ_KEY), ("gemini", GEMINI_KEY)):
        if not key:
            continue
        try:
            if provider == "groq":
                return groq_config.chat(
                    prompt, system=system, temperature=0.3,
                    max_tokens=max_tokens, timeout=120, raise_on_error=True,
                )
            else:
                req = urllib.request.Request(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                    data=json.dumps({"systemInstruction": {"parts": [{"text": system}]},
                                     "contents": [{"parts": [{"text": prompt}]}],
                                     "generationConfig": {"temperature": 0.3,
                                                          "maxOutputTokens": max_tokens}}).encode(),
                    headers={"x-goog-api-key": key}, method="POST")
                with urllib.request.urlopen(req, timeout=120) as r:
                    return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
        except Exception as e:
            print(f"    ⚠ {provider}: {str(e)[:90]}")
    return None


def heal(text: str, typ: str, words: int) -> tuple[str | None, int]:
    """KI-Erweiterung. Gibt (neuer_text, zusätzliche_wörter) zurück – oder (None, 0)."""
    target = POLICY[typ]["target_min"]
    need = max(350, target - words)
    title = fm_field(text, "title")
    kw = fm_field(text, "kurzantwort")
    system = (
        "Du erweiterst deutsche Finanz-Ratgeber (Blog „Franks Finanzcheck\", Du-Form, "
        "locker-sachlich, ehrlich – keine Werbung, keine Übertreibung). Du lieferst "
        "NUR neue Markdown-Abschnitte, nie Fülltext. Zahlen mit Stand-Jahr versehen.")
    prompt = f"""Der Artikel „{title}" hat nur {words} Wörter – Zielkorridor: {target}–{POLICY[typ]['target_max']}.
Er braucht ca. {need}-{need + 250} Wörter an zusätzlichem MEHRWERT.

Kurzantwort/Kern des Artikels: {kw[:300]}

Erstelle 2–3 dieser Module (passend wählen):
## Rechenbeispiel – konkrete, nachvollziehbare Zahlen (mit Jahr, z. B. Stand {date.today().year})
## Typische Fehler – 3–5 Punkte zum Thema
## Schritt-für-Schritt – pragmatische Anleitung
## Zwei weitere FAQ als „### Frage?"-Blöcke mit ehrlichen Antworten

Regeln: Keine Überschrift # (H1); beginne direkt mit „## "; keine Affiliate-/Kauf-Empfehlung
eines konkreten Anbieters; keine Wiederholung vorhandener Inhalte; Ton: hilfsbereit,
Einsteiger-tauglich. Gib NUR Markdown aus."""

    addition = (ai(system, prompt) or "").strip()
    if not addition or len(addition.split()) < need * 0.5:
        return None, 0

    # Einfügepunkt: vor „## Fazit", sonst vor endständigem Disclaimer/---, sonst ans Ende
    anchor = None
    for pat in (r"\n## Fazit", r"\n## .*Fazit.*", r"\n---\s*\n> \*\*Hinweis", r"\n---\s*$"):
        m = re.search(pat, text)
        if m:
            anchor = m.start()
            break
    new_text = (text[:anchor].rstrip() + "\n\n" + addition + "\n" + text[anchor:]
                if anchor is not None else text.rstrip() + "\n\n" + addition + "\n")

    # ---------- Verifikations-Gate ----------
    links_old = re.findall(r"https?://\S+|\]\([^)]+\)", text)
    links_new = re.findall(r"https?://\S+|\]\([^)]+\)", new_text)
    if len(links_new) < len(links_old):                 # kein Link darf verloren gehen
        return None, 0
    if "Hinweis" in text and "Hinweis" not in new_text:  # Disclaimer intakt?
        return None, 0
    new_words, _ = measure(new_text)
    if new_words <= words or new_words > POLICY[typ]["fat"]:
        return None, 0
    # lastmod-Frische-Signal setzen
    today = date.today().isoformat()
    if re.search(r"^lastmod:", new_text, re.M):
        new_text = re.sub(r'^lastmod:.*$', f"lastmod: {today}", new_text, count=1, flags=re.M)
    else:
        new_text = re.sub(r"^(---\n.*?^date:.*$)",
                          r"\1\nlastmod: " + today, new_text, count=1,
                          flags=re.S | re.M)
    return new_text, new_words - words


# ------------------------------------------------------------ Datei-Scan

def target_files() -> list[Path]:
    files = []
    for d in ("posts", "pillar"):
        dd = ROOT / "content" / d
        if dd.is_dir():
            files += sorted(dd.rglob("index.md"))
    if SCOPE != "all":
        files = [f for f in files if classify(f) == SCOPE]
    if NEW_ONLY:
        changed = set()
        try:
            out = subprocess.run(["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                                 capture_output=True, text=True, cwd=ROOT, timeout=30).stdout
            changed = {ROOT / l.strip() for l in out.splitlines() if l.strip()}
        except Exception:
            pass
        today = date.today().isoformat()
        changed |= {f for f in (ROOT / "content").rglob("index.md")
                    if f.parent.name.startswith(today)}
        files = [f for f in files if f in changed]
    return files


def main() -> None:
    files = target_files()
    rows, heal_candidates = [], []
    for p in files:
        text = p.read_text(encoding="utf-8")
        if "draft: true" in text[:2500] or "no_lengthen: true" in text[:2500]:
            continue
        w, c = measure(text)
        typ = classify(p)
        pol = POLICY[typ]
        status = ("🔴 heilen" if w < pol["heal"] else
                  "🟡 kurz" if w < pol["warn"] else
                  "🟢 ok" if w <= pol["fat"] else "🟠 lang")
        row = {"file": str(p.relative_to(ROOT)), "typ": typ, "w": w, "c": c, "status": status}
        rows.append(row)
        if status == "🔴 heilen":
            heal_candidates.append((p, text, w, typ))

    # Heil-Reihenfolge: Pillars zuerst, dann kürzeste zuerst
    heal_candidates.sort(key=lambda x: (x[3] != "pillar", x[2]))
    if BACKLOG:
        heal_candidates = heal_candidates[:BACKLOG]

    healed, failed = [], []
    if DO_FIX and USE_AI and not DRY_RUN and (GROQ_KEY or GEMINI_KEY):
        for p, text, w, typ in heal_candidates:
            print(f"  🩹 Heile ({w} Wörter, {typ}): {p.parent.name}")
            new_text, plus = heal(text, typ, w)
            if new_text and new_text != text:
                p.write_text(new_text, encoding="utf-8")
                healed.append((p.parent.name, w, w + plus))
                print(f"    ✅ +{plus} Wörter → {w + plus}")
            else:
                failed.append(p.parent.name)
                print("    ⚠ verworfen (Gate oder KI ohne brauchbare Antwort)")

    # Report
    buckets = {"🔴": 0, "🟡": 0, "🟢": 0, "🟠": 0}
    for r in rows:
        buckets[r["status"][0] + r["status"][1]] if False else None
        buckets[r["status"].split()[0]] += 1
    mode = "DRY-RUN" if DRY_RUN else ("FIX+KI" + f" backlog={BACKLOG}" if BACKLOG else "FIX+KI" if DO_FIX and USE_AI else "FIX" if DO_FIX else "REPORT")
    L = ["# 📏📝 LENGTH-REPORT (length_guard.py)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}", "",
         f"**Geprüft:** {len(rows)} Seiten | 🔴 {buckets['🔴']} · 🟡 {buckets['🟡']} · 🟢 {buckets['🟢']} · 🟠 {buckets['🟠']}",
         "",
         "**Korridor (Affiliate-Profi):** Posts 1.200–2.200 Wörter (heil < 900) · "
         "Pillar 2.500–4.000 (heil < 1.800)", ""]
    if healed:
        L += ["## ✅ Geheilt (Selbstheilung, KI-Erweiterung mit Gate)", ""]
        L += [f"- `{n}`: {a} → {b} Wörter" for n, a, b in healed]
        L.append("")
    if failed:
        L += ["## ⚠ Heilung verworfen (Gate) – manueller Blick empfohlen", ""]
        L += [f"- `{n}`" for n in failed]; L.append("")
    short = sorted((r for r in rows if r["status"] != "🟢 ok"), key=lambda r: r["w"])[:20]
    if short:
        L += ["## Kürzeste Seiten außerhalb des Korridors", ""]
        L += [f"- {r['status']} `{r['file']}`: **{r['w']} Wörter** ({r['c']:,} Zeichen, {r['typ']})".replace(",", ".")
              for r in short]
    L += ["", "---", "_Selbstheilung: ⚠ Modul-Erweiterung durch KI, verifiziert (Links/Disclaimer/Länge). "
          "Nur --ai heilt; ohne Keys bleibt es ein Report._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:22]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "mode": mode,
                             "healed": len(healed), "red": buckets["🔴"],
                             "yellow": buckets["🟡"]}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
