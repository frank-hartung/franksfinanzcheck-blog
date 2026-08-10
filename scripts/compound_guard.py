#!/usr/bin/env python3
# ============================================================
#  COMPOUND-GUARD – Deutsche Komposita-Prüfung (selbst entscheidend)
#
#  ERKENNT & KORRIGIERT SEO-/KI-typische Komposita-Fehler der Form
#  „Preisgarantie Gas" (grammatisch falsch: zwei Substantive ohne
#  Bindung) -> „Gaspreisgarantie".
#
#  DREI ENTSCHEIDUNGSEBENEN (Profi-Level):
#    1) REGELWERK (COMPOUND_RULES unten): dokumentierte Fälle aus dem
#       Blog -> sofort deterministisch korrigieren.
#    2) KANDIDATEN-ERKENNUNG: Kopf-Nomen (Preisgarantie, Tarif, Konto,
#       Sparplan, …) direkt vor Themen-Nomen (Gas, Strom, DSL, …) ->
#       neue Kombinationen landen im REPORT zur Prüfung.
#    3) KI-SCHIEDSRICHTER (optional, --ai, nutzt Groq/Gemini):
#       entscheidet bei Kandidaten selbst – mit Verifikations-Gate.
#
#  NIEMALS ANFASSEN (geschützt, wie Dash-Guard):
#    - URLs/Slugs (veröffentlichte URLs sind sakrosankt!)
#    - Front-Matter-Felder title, description, keywords
#      (SEO-Keywords dürfen in der gesuchten Wortfolge bleiben;
#      Google erkennt Komposita-Treffer auch aus der Keyword-Liste)
#    - Eigennamen & Marken (Whitelist: „Franks Finanzcheck" u. a.)
#    - Wochentage/Monate vor Nomen („Montag Abend"), Code, Listen-Marker
#
#  Aufruf:
#    python3 scripts/compound_guard.py             # Report
#    python3 scripts/compound_guard.py --fix       # Regelwerk anwenden
#    python3 scripts/compound_guard.py --fix --ai  # + KI bei Kandidaten
#    python3 scripts/compound_guard.py --new-only  # nur neue Artikel
#
#  Ausgabe: COMPOUND-REPORT.md · idempotent · Exit 0 = OK.
# ============================================================

import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT_DIRS = [ROOT / "content" / "posts", ROOT / "content" / "pillar"]
REPORT = ROOT / "COMPOUND-REPORT.md"

GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

DO_FIX = "--fix" in sys.argv
USE_AI = "--ai" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

# ---------------------------------------------------------------- Regelwerk
# Bekannte Fälle aus dem Blog. Format: (Regex, Ersatz, Kommentar)
# ANLEITUNG: Neue Fälle aus COMPOUND-REPORT.md hier eintragen (oder --ai
# entscheiden lassen und den Fund hier dokumentieren).
COMPOUND_RULES = [
    (r"\bPreisgarantie Gas\b",    "Gaspreisgarantie",    "Betriebseintrag 2026-08-10 (Riester-naher Gas-Artikel)"),
    (r"\bPreisgarantie Strom\b",  "Strompreisgarantie",  "vorbeugend – gleiche SEO-Keyword-Falle"),
    (r"\bPreisgarantie DSL\b",    "DSL-Preisgarantie",   "vorbeugend (Durchkopplung, Akronym vor Kompositum)"),
    (r"\bZinsen Tagesgeld\b",     "Tagesgeldzinsen",     "vorbeugend"),
    (r"\bZinsen Festgeld\b",      "Festgeldzinsen",      "vorbeugend"),
    (r"\bSparplan ETF\b",         "ETF-Sparplan",        "vorbeugend"),
    (r"\bTarif DSL\b",            "DSL-Tarif",           "vorbeugend"),
    (r"\bKonto Giro\b",           "Girokonto",           "vorbeugend"),
]

# Kopf-Nomen, die gerne falsch vor Themen-Nomen geraten (Kandidaten-Radar)
HEAD_NOUNS = ["Preisgarantie", "Garantie", "Zinsen", "Sparplan", "Tarif",
              "Konto", "Kredit", "Depot", "Rate", "Beitrag", "Kosten", "Preis"]
TOPIC_NOUNS = ["Gas", "Strom", "DSL", "Internet", "Handy", "ETF", "ETFs",
               "Rente", "Tagesgeld", "Festgeld", "Giro", "Kfz", "Auto"]

# Nie als Fehler werten:
WHITELIST = {"Franks Finanzcheck", "Google Suche", "Social Media"}

CANDIDATE_RE = re.compile(
    r"\b(" + "|".join(HEAD_NOUNS) + r")\s+(" + "|".join(TOPIC_NOUNS) + r")\b")

HEADER_PROTECTED_FM = {"title", "description", "keywords"}


# ------------------------------------------------------------- Hilfen

def mask(line: str):
    store = {}
    def _m(m):
        key = f"\x00{len(store)}\x00"
        store[key] = m.group(0)
        return key
    line = re.sub(r"https?://\S+", _m, line)
    line = re.sub(r"\[[^\]]*\]\([^)]*\)", _m, line)
    line = re.sub(r"`[^`]*`", _m, line)
    return line, store


def unmask(line, store):
    for k, v in store.items():
        line = line.replace(k, v)
    return line


def target_files():
    files = []
    for d in CONTENT_DIRS:
        if d.is_dir():
            files += sorted(d.rglob("index.md"))
    if NEW_ONLY:
        today = date.today().isoformat()
        changed = set()
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                capture_output=True, text=True, cwd=ROOT, timeout=30).stdout
            changed = {ROOT / l.strip() for l in out.splitlines() if l.strip()}
        except Exception:
            pass
        changed |= {f for f in (ROOT / "content").rglob("index.md")
                    if f.parent.name.startswith(today)}
        files = [f for f in files if f in changed]
    return files


# ---------------------------------------------------- KI-Schiedsrichter

def ai_call(system: str, prompt: str) -> str | None:
    for provider, key, url, payload in (
        ("groq", GROQ_KEY, "https://api.groq.com/openai/v1/chat/completions",
         {"model": "llama-3.3-70b-versatile", "temperature": 0.0, "max_tokens": 300,
          "messages": [{"role": "system", "content": system}, {"role": "user", "content": prompt}]}),
        ("gemini", GEMINI_KEY, "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
         {"systemInstruction": {"parts": [{"text": system}]},
          "contents": [{"parts": [{"text": prompt}]}],
          "generationConfig": {"temperature": 0.0, "maxOutputTokens": 300}}),
    ):
        if not key:
            continue
        try:
            headers = {"Content-Type": "application/json"}
            if provider == "groq":
                headers["Authorization"] = f"Bearer {key}"
            else:
                headers["x-goog-api-key"] = key
            req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                         headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read())
            return (data["choices"][0]["message"]["content"] if provider == "groq"
                    else data["candidates"][0]["content"]["parts"][0]["text"])
        except Exception as e:
            print(f"  ⚠ {provider}: {e}")
    return None


def ai_decide(phrase: str, context: str) -> str:
    """Liefert Korrektur-String oder '' (= behalten). Nur bei klarem Kompositum-Fehler."""
    out = ai_call(
        "Du bist deutscher Profi-Lektor. Antworte NUR als JSON.",
        f"""Im folgenden Satz steht die Wortfolge „{phrase}" (Kopf-Nomen + Themen-Nomen, z. B. „Preisgarantie Gas").

KONTEXT: {context[:280]}

Frage: Ist das ein grammatisch falsches Kompositum im Fließtext (korrekt wäre z. B. „Gaspreisgarantie")?
NEIN/antworte {{"keep": true}} bei: Eigennamen, bewussten SEO-Keyword-Platzierungen im Titel, Appositionen mit Komma-Gefühl, Bedeutung wie „Preis für die Garantie".

JSON-Antwort: {{"keep": true}} ODER {{"keep": false, "fixed": "…"}} – wobei „fixed" NUR die korrigierte Wortfolge „{phrase}" enthält (z. B. „Gaspreisgarantie"), nie den ganzen Satz.""")
    if not out:
        return ""
    m = re.search(r"\{.*\}", out, re.DOTALL)
    if not m:
        return ""
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return ""
    if d.get("keep"):
        return ""
    fixed = (d.get("fixed") or "").strip()
    # Verifikations-Gate: nur eine Wortfolge, Großbuchstaben, keine Satzzeichen
    if not fixed or len(fixed.split()) > 3 or re.search(r"[.!?;:]", fixed):
        return ""
    return fixed


# --------------------------------------------------------- Verarbeitung

def process(path: Path):
    rel = str(path.relative_to(ROOT))
    lines = path.read_text(encoding="utf-8").split("\n")
    fixes, candidates = [], []
    in_fm = lines and lines[0].strip() == "---"
    fm_end = None
    out = []
    in_code = False

    for i, line in enumerate(lines):
        if in_fm and i > 0 and line.rstrip() == "---" and fm_end is None:
            fm_end = i
            out.append(line); continue
        if stripped := line.strip().startswith("```"):
            in_code = not in_code
            out.append(line); continue
        if in_code:
            out.append(line); continue

        # Front-Matter: komplett schützen (SEO-Keywords/Titel bleiben)
        if fm_end is None and in_fm:
            out.append(line); continue

        if line.strip() == "---" or line.lstrip().startswith("<!--"):
            out.append(line); continue

        masked, store = mask(line)
        new = masked
        for pat, repl, _why in COMPOUND_RULES:
            new = re.sub(pat, repl, new)
        if new != masked:
            do = DO_FIX and not DRY_RUN
            fixes.append((rel, i + 1, masked.strip()[:70], new.strip()[:70], do))
        # Kandidaten-Radar (ohne Regel-Treffer doppelt zu melden)
        for m in CANDIDATE_RE.finditer(new):
            phrase = m.group(0)
            if phrase in WHITELIST:
                continue
            if any(re.fullmatch(pat, phrase) for pat, _, _ in COMPOUND_RULES):
                continue
            candidates.append((rel, i + 1, phrase, new.strip()[:70]))
        out.append(unmask(new, store))

    changed = fixes and DO_FIX and not DRY_RUN
    return {"file": rel, "text": "\n".join(out) if changed else None,
            "fixes": fixes, "candidates": candidates}


def main() -> None:
    files = target_files()
    if not files:
        print("Keine Zieldateien.")
        return
    touched, found, cands = 0, 0, []
    for p in files:
        res = process(p)
        if res["text"] is not None and res["text"] != p.read_text(encoding="utf-8"):
            p.write_text(res["text"], encoding="utf-8")
            touched += 1
        found += len(res["fixes"])
        cands += res["candidates"]

    # KI-Schiedsrichter über Kandidaten (max 6/Lauf, Kostenbremse)
    ai_fixes = []
    if USE_AI and (GROQ_KEY or GEMINI_KEY) and cands and DO_FIX and not DRY_RUN:
        by_file: dict[str, list] = {}
        for rel, ln, phrase, ctx in cands[:6]:
            verdict = ai_decide(phrase, ctx)
            if verdict:
                ai_fixes.append((rel, ln, phrase, verdict))
                by_file.setdefault(rel, []).append((phrase, verdict))
        for rel, pairs in by_file.items():
            p = ROOT / rel
            t = p.read_text(encoding="utf-8")
            for old, new in pairs:
                t = re.sub(r"\b" + re.escape(old) + r"\b", new, t)
            p.write_text(t, encoding="utf-8")

    mode = "DRY-RUN" if DRY_RUN else ("FIX" + ("+KI" if USE_AI else "") if DO_FIX else "REPORT")
    lines = ["# 🧩 COMPOUND-REPORT (compound_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}", ""]
    if found:
        lines += [f"## Regelwerk-Treffer: {found}" + (" ✅ korrigiert" if (DO_FIX and not DRY_RUN) else " (→ mit --fix anwenden)"), ""]
    if ai_fixes:
        lines += ["## 🤖 KI-Urteile (Komposita bestätigt & korrigiert)", ""]
        lines += [f'- `{f}` Z.{l}: „{o}" → „{n}"' for f, l, o, n in ai_fixes]
    open_cands = [c for c in cands] if not ai_fixes else []
    if open_cands:
        lines += ["", "## 🔭 Kandidaten-Radar (zur Prüfung – Regel ergänzen oder --ai entscheiden lassen)", ""]
        lines += [f'- `{f}` Z.{l}: „{ph}"' for f, l, ph, _ in open_cands[:20]]
    if not found and not open_cands and not ai_fixes:
        lines.append("🎉 Keine Komposita-Fehler gefunden (Profi-Level).")
    lines += ["", "---", "_Schützt: Front-Matter (Titel/Keywords = SEO-Freiraum), URLs, "
              "Code, Eigennamen. Hausform: Kompositum oder Durchkopplung._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines[:25]))


if __name__ == "__main__":
    main()
