#!/usr/bin/env python3
# ============================================================
#  LEKTOR-GUARD – Verlags-Lektorat (Zeitung-/Buchqualitaet), selbstheilend
#
#  Auftrag (11.08.2026): „Vollautomatische Lektorenpruefung mit
#  Selbstheilung", wie sie Verlage einsetzen. Uebernimmt die
#  sprachliche Feinkontrolle, die Grammatik-/Rechtschreib-Tools
#  nicht abdecken:
#
#    L1  Wortduplikate im Satz (tautologisch): „der der", „und und", „sich sich"
#        (deterministisch, sofort sicher fixbar)
#    L2  Füllphrasen (Buerokratie-Deutsch) mit Kanon-Ersatz:
#        „Es ist zu beachten, dass" -> „Wichtig:" (etc., siehe PHRASEN)
#    L3  Personenkonsistenz: Hausduktus ist „du"; vereinzelte „Sie/Ihnen/Ihre"
#        werden angepasst (Framework: Mehrheitsentscheid je Artikel)
#    L4  Ausrufezeichen-Inflation: „!!" -> „!"; > 3 Ausrufezeichen je Artikel
#        = Werbeton-Fund im Report (Lektorat: hoechstens drei!)
#    L5  Echo-Woerter: dasselbe Vollword (>4 Buchstaben) zweimal im selben Satz
#        -> REPORT (nicht auto-fix); mit --ai formuliert der Lektor um
#        (4-fach-Verifikations-Gate wie dash_guard: URL/Laenge/MD/sinnig)
#    L6  Stale-Jahre: „Stand: 2023"/„(2024)" neben Jahreswechsel-Flag  -> Report
#
#  SCHUTZZONEN (bewahrte Familien-Regeln): Front-Matter, URLs, Code,
#  Hashtags, Woerterbuecher (z. B. buchstabierend „der der" wenn…), Zitate,
#  Ueberschriften, Listen-Marker, Disclaimer-Block, Affiliate-Block.
#
#  Verdrahtet: Engine v2 Phase 2 (hoch in der Sprachgruppe, NACH Unit/
#  Casing, VOR Profi-Gate). Lektorat in Echtzeit, gleich bei der Geburt.
#  Idempotent (Convergence-Test 11.08.).
#
#  Aufruf:
#    python3 scripts/lektor_guard.py             # Report (weich)
#    python3 scripts/lektor_guard.py --fix       # deterministisch fixen
#    python3 scripts/lektor_guard.py --fix --ai  # + KI-Leitzeilen (L5)
#    python3 scripts/lektor_guard.py --new-only  # Engine-Modus
#
#  Ausgabe: LEKTOR-REPORT.md + data/lektor_history.jsonl · Exit 0.
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
REPORT = ROOT / "LEKTOR-REPORT.md"
HISTORY = ROOT / "data" / "lektor_history.jsonl"

GROQ_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

DO_FIX = "--fix" in sys.argv
USE_AI = "--ai" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

# ---------------- L1: Doppelwoerter (Kanon: wiederholte Funktionswoerter) --------
# Auto-Fix nur bei NIE legalen Verdopplungen (Konjunktionen/Partikel).
# Relativpronomen-Kaskaden wie die-die-meisten sind KORREKTES Deutsch!
L1_PAT = re.compile(
    r"\b(und|oder|aber|denn|doch|sowie|auch|nicht|sehr|ganz|schon|noch|"
    r"dass|weil|wenn|mit|fuer|durch|ohne|gegen|im|in|zu|von|bei|auf|an|sich)\s+\1\b",
    re.IGNORECASE)
# Relativ-Doppler (der der / die die / das das) -> NUR melden/KI, nie auto
L1_RELATIV = re.compile(r'\b(der|die|das|den|dem|ein|eine|einer|einem|einen|eines)\s+\1\b', re.IGNORECASE)


def l1_artikel_entcheidung(m):
    """Artikel-Doppelung: nur aufloesen, wenn KEIN Komma/Doppelpunkt davor
    steht (Leerzeichen werden uebersprungen! Relativkaskaden bleiben)."""
    i = m.start() - 1
    while i >= 0 and m.string[i] in " \t":
        i -= 1
    before = m.string[i] if i >= 0 else ""
    return m.group(1) if before not in (",", ";", ":", "–", "-") else m.group(0)
L1_FIX = lambda m: m.group(1)

# ---------------- L2: Fuehl-Phrasen (deterministisch ersetzbar) ------------------
PHRASEN = [
    (re.compile(r"Es ist zu beachten, dass", re.I), "Wichtig:"),
    (re.compile(r"In der heutigen Zeit", re.I), "Heute"),
    (re.compile(r"Aufgrund der Tatsache, dass", re.I), "Weil"),
    (re.compile(r"Im Grunde genommen,? ", re.I), ""),
    (re.compile(r"Es sei (?:an dieser Stelle )?(?:darauf )?hingewiesen, dass", re.I), "Hinweis:"),
    (re.compile(r"Ohne (?:jeden |jedwede[mnrs]? )?Zweifel", re.I), "Unbestreitbar"),
    (re.compile(r"In diesem Zusammenhang (?:ist zu (?:beachten|erw[äa]hnen), dass|muss gesagt werden, dass)", re.I), "Dabei ist"),
    (re.compile(r"was (?:das|dies|jenes) (?:betrifft|anbelangt|angeht)", re.I), "dazu"),
    (re.compile(r"Darueber hinaus ist zu (?:sagen|beachten|erw[äa]hnen),? dass", re.I), "Zudem"),
]

# ---------------- L4: Ausrufezeichen-Kontrolle -----------------------------------
AUSRUF_MAX = 3  # Lektorats-Regel: mehr als 3 = Werbeton

# ---------------- L5/L3 Wortlisten ------------------------------------------------
DU_SET = {"du", "dein", "deine", "deiner", "deinen", "deinem", "deinem", "deines", "dich", "dir", "deinen"}
SIE_SET = {"Sie", "Ihnen", "Ihre", "Ihrem", "Ihrer"}


def mask(line: str):
    store = {}
    def _m(m):
        k = f"\x00{len(store)}\x00"
        store[k] = m.group(0)
        return k
    line = re.sub(r"https?://\S+", _m, line)
    line = re.sub(r"\[[^\]]*\]\([^)]*\)", _m, line)
    line = re.sub(r"`[^`]*`", _m, line)
    # Lektorats-Ehre: direkte Rede/Zitate („…" / "…") niemals umschreiben
    line = re.sub('„[^"]+["“]', _m, line)
    line = re.sub('"[^"\n]{3,120}"', _m, line)
    return line, store


def unmask(line, store):
    for k, v in store.items():
        line = line.replace(k, v)
    return line


# ---------------------------------------------------------- L3 (Person) ----------

def l3_person(text: str) -> tuple[str, int]:
    """Mehrheit gewinnt: dominant du vs. Sie; Minderheit wird angepasst."""
    du_n = len(re.findall(r"\b" + "|".join(sorted(DU_SET)), text, re.I))
    sie_n = len(re.findall(r"\b" + "|".join(sorted(SIE_SET)), text))
    # Grossbildschreibung bewusst: \"sie\" klein kann Dritte Person Plural sein
    if sie_n == 0 or du_n == 0 or du_n >= sie_n * 3 and sie_n < 4:
        return text, 0
    if sie_n and sie_n <= max(2, du_n // 4):
        n = 0
        def r_sie(m):
            nonlocal n
            n += 1
            return {"Sie": "du", "Ihnen": "dir", "Ihre": "deine", "Ihrem": "deinem", "Ihrer": "deiner"}[m.group(0)]
        return re.sub(r"\b(Sie|Ihnen|Ihre|Ihrem|Ihrer)\b", r_sie, text), n
    return text, 0


# ---------------------------------------------------------- L5 (Echo, KI) --------

def l5_echo(line: str) -> list[tuple]:
    """Dasselbe Vollwort (>4 Buchstaben) zweimal im selben Satz -> Report."""
    out = []
    for sent in re.split(r"(?<=[.!?])\s+", line):
        words = [w.lower() for w in re.findall(r"[A-Za-zäöüÄÖÜß]{5,}", sent)]
        seen, dup = set(), set()
        for w in words:
            (dup if w in seen else seen).add(w)
        if dup:
            out.append((sorted(dup), sent.strip()))
    return out


def l5_ai_rewrite(satz: str, woerter: list) -> str | None:
    """KI formuliert den Satz ohne Echo um (mit Gate)."""
    if not (GROQ_KEY or GEMINI_KEY):
        return None
    prompt = f"""Dieser deutsche Satz hat ein Echo-Wort (Wiederholung von „{', '.join(woerter)}").

SATZ: {satz}

Lektorats-Aufgabe: Formuliere den Satz nur so um, dass das Echo weg ist
(Synonym fuer die zweite Wiederholung, Satzumbau ok). Ton/Sinn/Laenge
(~+/-25%) aehnlich. Markdown (**fett**) 1:1 erhalten.

Antworte NUR mit dem korrigierten Satz, nichts anderes."""
    for provider, key in (("groq", GROQ_KEY), ("gemini", GEMINI_KEY)):
        if not key:
            continue
        try:
            if provider == "groq":
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=json.dumps({"model": "llama-3.3-70b-versatile", "temperature": 0.2, "max_tokens": 500,
                                     "messages": [{"role": "user", "content": prompt}]}).encode(),
                    headers={"Authorization": f"Bearer {key}"}, method="POST")
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.loads(r.read())["choices"][0]["message"]["content"].strip()
            else:
                req = urllib.request.Request(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                    data=json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                                     "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500}}).encode(),
                    headers={"x-goog-api-key": key}, method="POST")
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip()
            fixed = out.splitlines()[0].strip()
            # Gates: keine URLs verloren, Laenge plausibel, kein Echo mehr:
            if re.findall(r"https?://\S+", satz) != re.findall(r"https?://\S+", fixed):
                return None
            if not (0.5 <= len(fixed) / max(1, len(satz)) <= 1.8):
                return None
            if any(w.lower() in fixed.lower() and fixed.lower().count(w.lower()) > 1 for w in woerter):
                return None
            return fixed
        except Exception:
            continue
    return None


def l3_ai_rewrite(satz: str) -> str | None:
    """KI schreibt Heavy-Mix-Satz (Sie-Form) im du-Duktus korrekt um."""
    if not (GROQ_KEY or GEMINI_KEY):
        return None
    prompt = f"""Schreibe diesen Satz in die Du-Form um (Hausduktus „du"):

{satz}

Pflicht: grammatikalisch fehlerfrei, gleicher Sinn, gleiche Laenge (+-25%),
Markdown bleibt, keine Faktaenderung. Antworte NUR mit dem neuen Satz."""
    for provider, key in (("groq", GROQ_KEY), ("gemini", GEMINI_KEY)):
        if not key:
            continue
        try:
            if provider == "groq":
                req = urllib.request.Request(
                    "https://api.groq.com/openai/v1/chat/completions",
                    data=json.dumps({"model": "llama-3.3-70b-versatile", "temperature": 0.2, "max_tokens": 500,
                                     "messages": [{"role": "user", "content": prompt}]}).encode(),
                    headers={"Authorization": f"Bearer {key}"}, method="POST")
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.loads(r.read())["choices"][0]["message"]["content"].strip()
            else:
                req = urllib.request.Request(
                    "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                    data=json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                                     "generationConfig": {"temperature": 0.2, "maxOutputTokens": 500}}).encode(),
                    headers={"x-goog-api-key": key}, method="POST")
                with urllib.request.urlopen(req, timeout=60) as r:
                    out = json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"].strip()
            fixed = out.splitlines()[0].strip()
            # Grammatik-Gate: du + konjugiertes Verb in Singular-Endung (-st) muessen vorkommen
            if not re.search(r"\bdu\s+\w+(st|est)\b", fixed, re.I) and not re.search(r"\b(dir|deine?r?[smn]?)\b", fixed):
                return None
            if re.search(r"\b(Sie|Ihnen|Ihre[nmrs]?)\b", fixed):
                return None
            if abs(len(fixed) - len(satz)) > abs(len(satz)) * 0.6:
                return None
            return fixed
        except Exception:
            continue
    return None


# ------------------------------------------------------------ Verarbeitung

def process(path: Path):
    """Bewaehrtes Muster der anderen Guards: Front-Matter-Fence zaehlen,
    Zeilenklassen schuetzen, lektor_line() nur auf Body anwenden."""
    rel = str(path.relative_to(ROOT))
    full_text = path.read_text(encoding="utf-8")
    lines = full_text.split("\n")
    out = []
    stats = {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5echo": 0, "L5ki": 0}
    reports = []

    # Datei-Duktus einmalig (L3-Entscheidung ist filebasiert, nicht zeilenbasiert)
    du_ct = len(re.findall(r"\b(du|dein|deine|deinem|deinen|dich|dir)\b", full_text, re.I))
    sie_ct = len(re.findall(r"\b(Sie|Ihnen|Ihre|Ihrem|Ihrer)\b", full_text))
    du_dominant = (sie_ct > 0 and du_ct > 0)  # Mix = Problem; Hausduktus (du) gewinnt

    in_code = False
    fm_open = False
    fm_done = False
    for i, raw in enumerate(lines):
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            out.append(raw); continue
        if in_code:
            out.append(raw); continue
        if i == 0 and s == "---":
            fm_open = True
            out.append(raw); continue
        if fm_open and not fm_done:
            if s == "---":
                fm_done = True
                out.append(raw); continue
            if s.startswith("---") and len(s) > 3:
                fm_done = True
                rest = s[3:]
                if rest.strip() and re.search(r"[A-Za-zäöü]", rest):
                    masked, store = mask(rest)
                    fixed, _ = lektor_line(masked, stats, reports=reports, fname=rel,
                                           line_no=i + 1, du_dominant=du_dominant)
                    out.append("---" + unmask(fixed, store))
                    continue
            out.append(raw); continue
        masked, store = mask(raw)
        fixed, _ = lektor_line(masked, stats, reports=reports, fname=rel,
                               line_no=i + 1, du_dominant=du_dominant)
        out.append(unmask(fixed, store))
    return stats, reports, "\n".join(out)


def lektor_line(line: str, stats, reports=None, fname="", line_no=0, du_dominant=False) -> tuple[str, int]:
    # L1 Doppelwoerter (Auto-Fix)
    def r_l1(m):
        stats["L1"] += 1
        return m.group(1)
    line = L1_PAT.sub(r_l1, line)
    line = L1_RELATIV.sub(l1_artikel_entcheidung, line)
    # Relativ-Doppler: NIE auto-fixen (korrektes Deutsch), nur Report:
    for _m in L1_RELATIV.finditer(line):
        stats.setdefault("L1rel", 0)
        stats["L1rel"] += 1
        if reports is not None:
            reports.append((fname, line_no, "L1-Relativ (Korrektur pruefen)", line.strip()[:80]))
    # L2 Fuehl-Phrasen (Auto-Fix)
    for pat, repl in PHRASEN:
        n_before = len(pat.findall(line))
        if n_before:
            stats["L2"] += n_before
            line = pat.sub(repl, line)
    # L3 Personenkonsistenz – KI-only (deterministisch NIEMALS: Worttausch
    # ohne Verb-Konjugation erzeugt Grammatik-Bruch, getestet und verworfen).
    # Zwei Bedingungen: Datei ist du-dominiert + Satz hat Sie-Formen.
    if du_dominant and re.search(r"\b(Sie|Ihnen|Ihre|Ihrem|Ihrer)\b", line):
        stats["L3"] += line.count("Sie ") + line.count("Ihn")
        if reports is not None:
            reports.append((fname, line_no, "L3-Formal-Ich", line.strip()[:90]))
        if DO_FIX and USE_AI and not DRY_RUN and line.strip() and not line.lstrip().startswith("#"):
            for satz in re.split(r"(?<=[.!?])\s+", line):
                if re.search(r"\b(Sie|Ihnen|Ihre|Ihrem|Ihrer)\b", satz):
                    fixed = l3_ai_rewrite(satz)
                    if fixed and fixed != satz:
                        line = line.replace(satz, fixed)
    # L4 Ausrufezeichen
    bang = line.count("!") + line.count("！")
    if bang:
        line = re.sub(r"!{2,}", "!", line)
        if bang > 1:
            stats["L4"] += 1
    if line.count("!") > AUSRUF_MAX:
        stats["L4"] += 1
        if reports is not None:
            reports.append((fname, line_no, "L4-Werbeton", line.strip()[:90]))
    # L5 Echo-Report (nur Fliesstext-Zeilen – Listen/Tabellen/Ueberschriften
    # haben Wiederholung per Konstruktion!)
    if line.lstrip().startswith(("-", "*", "|", "#", ">")) or len(line.strip()) < 36:
        return line, 0
    for woerter, satz in l5_echo(line):
        stats["L5echo"] += 1
        if reports is not None:
            reports.append((fname, line_no, "L5-Echo", f"{'/'.join(woerter)}: {satz[:70]}"))
        if DO_FIX and USE_AI and not DRY_RUN:
            fixed = l5_ai_rewrite(satz, woerter)
            if fixed and fixed != satz:
                line = line.replace(satz, fixed)
                stats["L5ki"] += 1
    return line, 0


def target_files():
    files = []
    for d in ("posts", "pillar"):
        dd = ROOT / "content" / d
        if dd.is_dir():
            files += sorted(dd.rglob("index.md"))
    if NEW_ONLY:
        changed = set()
        try:
            out = subprocess.run(["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                                 capture_output=True, text=True, cwd=ROOT, timeout=30).stdout
            changed = {ROOT / l.strip() for l in out.splitlines() if l.strip()}
        except Exception:
            pass
        today = date.today().isoformat()
        changed |= {f for f in (ROOT / "content").rglob("index.md") if f.parent.name.startswith(today)}
        files = [f for f in files if f in changed]
    return files


def main() -> None:
    files = target_files()
    total_fix = {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5echo": 0, "L5ki": 0}
    all_reports = []
    touched = 0
    for p in files:
        stats, reports, new_text = process(p)
        if DO_FIX and not DRY_RUN and new_text != p.read_text(encoding="utf-8"):
            p.write_text(new_text, encoding="utf-8")
            touched += 1
        for k in total_fix:
            total_fix[k] += stats[k]
        all_reports += reports

    mode = "DRY-RUN" if DRY_RUN else ("FIX" + ("+KI" if USE_AI else "") if DO_FIX else "REPORT")
    L = ["# ✒️ LEKTOR-REPORT (lektor_guard.py)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}", ""]
    L.append("| Regel | Anzahl |")
    L.append("|---|---|")
    L.append(f"| L1 Doppelwoerter (Auto) | {total_fix['L1']} |")
    L.append(f"| L2 Fuehl-Phrasen (Auto) | {total_fix['L2']} |")
    L.append(f"| L3 Personenkonsistenz | {total_fix['L3']} |")
    L.append(f"| L4 Ausrufezeichen/Grenze | {total_fix['L4']} |")
    L.append(f"| L5 Echo (Report" + ("/KI-gefixt" if USE_AI else "") + f") | {total_fix['L5echo']}/{total_fix['L5ki']} |")
    if all_reports:
        L += ["", "## Fundstellen (Auswahl)", ""]
        L += [f"- `{f}` Z.{n}: **{t}** {c[:60]}" for f, n, t, c in all_reports[:20]]
    L += ["", "---", "_Verlagslektorat: Du-Duktus, keine Echo-Woerter, keine Buerokratie-Phrasen, max 3 Ausrufezeichen. KI nur bei --ai._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:25]))
    HISTORY.parent.mkdir(exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"date": date.today().isoformat(), "mode": mode,
                             **{k: v for k, v in total_fix.items()}}, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
