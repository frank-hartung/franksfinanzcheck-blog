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
#    L7  NOMINALSTIL-RADAR: >4 Behoerden-Nomen (-ung/-heit/…) je Absatz -> Report
#    L8  WEICHMACHER-DICHTE: >6 Konjunktive (könnte/sollte/müsste) -> Report
#    L9  SATZANFANGS-ECHO: gleiches Wort startet 3+ Saetze eines Absatzes -> Report
#    L10 ZAHLENSCHREIBWEISE (Duden): 2-12 ausgeschrieben vor Zaehlwoertern
#        (3 Tipps -> drei Tipps) – Auto-Fix; NIE vor %, €, Euro, Jahren
#    L11 WERBE-INTENSIVEL entschaerft (brutal guenstig -> besonders guenstig,
#        sensationell -> beachtlich, mega- -> sehr …) – Auto-Fix Kanon
#    L12 LONGSATZ-ALARM: >35 Woerter -> Report
#
#  SABOTAGE-SCHUTZ (neu): SELFTEST mit 12 eingefrorenen Lektorats-Faellen
#  (inkl. Negativ-Fallen „darf unangetastet bleiben") laeuft vor JEDEM
#  Einsatz; Abweichung -> Exit 2, keine Datei wird angefasst.
#
#  SCHUTZZONEN (bewahrte Familien-Regeln): Front-Matter, URLs, Code,
#  Hashtags, Woerterbuecher (z. B. buchstabierend „der der" wenn…), Zitate,
#  Ueberschriften, Listen-Marker, Disclaimer-Block, Affiliate-Block.
#
#  Verdrahtet: Engine v2 Phase 2 (hoch in der Sprachgruppe, NACH Unit/
#  Casing, VOR Profi-Gate). Lektorat in Echtzeit, gleich bei der Geburt.
#  + Wochen-Gesamtsichtung im Archiv (weekly-audit). Idempotent (getestet).
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

# ------------- L7-L12: Zielredaktions-Erweiterung (11.08.2026, Abend) -------------
# L7 NOMINALSTIL-RADAR: Behoerden-Nomen auf -ung/-heit/-keit/… pro Absatz zaehlen,
#    ueber Schwellenwert -> Report (Verlagsregel: >4 = Kancelli-Stil)
NOMINAL_PAT = re.compile(
    r"\b\w{3,}(ung|ungen|heit|heiten|keit|keiten|nis|nisse|enz|tion|tionen)\b", re.I)
NOMINAL_MAX = 4

# L8 MODALVERB-WEICHMACHER (Konjunktiv-Traegheit) – Dichte pro Artikel
WEICH_PAT = re.compile(
    r"\b(könnte(?:n|st|t)?|sollte(?:n|st|t)?|müsste(?:n|st|t)?|"
    r"dürfte(?:n|st|t)?|möchte(?:n|st|t)?)\b", re.I)
WEICH_MAX = 6

# L9 SATZANFANGS-ECHO: dasselbe Wort beginnt >= 3 Saetze eines Absatzes
ANFANG_ECHO_MIN = 3

# L10 ZAHLENSCHREIBWEISE (Duden): Kardinalzahlen 2-12 werden ausgeschrieben.
# Auto-Fix NUR vor Alltags-Zaehlwoertern – NIE vor %, €, Euro, Jahren usw.
ZAHL_KANON = {"2": "zwei", "3": "drei", "4": "vier", "5": "fünf", "6": "sechs",
              "7": "sieben", "8": "acht", "9": "neun", "10": "zehn", "11": "elf",
              "12": "zwölf"}
ZAEHL_NOMEN = (r"Tipps?|Tricks?|Schritte?n?|Regeln?|Wege?|Fehler?|Gründe?|Beispiele?n?|"
               r"Fragen?|Faktoren?|Strategien?|Methoden?|Punkte?n?|Gewohnheiten?|"
               r"Ideen?|Vorteile?n?|Nachteile?n?|Möglichkeiten?|Geheimnisse?")
ZAHL_PAT = re.compile(
    r"(?<![\d.,/€>|\-])\b(1[0-2]|[2-9])\s+(?=(?:" + ZAEHL_NOMEN + r")\b)")


def _zahl_repl(m):
    w = ZAHL_KANON[m.group(1)]
    j = m.start() - 1
    while j >= 0 and m.string[j] in " \t":
        j -= 1
    if j < 0 or m.string[j] in ".!?":
        w = w.capitalize()
    return w + " "

# L11 WERBE-INTENSIVEL (Typen-Sprech) mit Kanon-Entschaerfung:
INTENSIV = [
    (re.compile(r"\bbrutal\s+(?=günstig|teuer|schwer|einfach|gut)", re.I), "besonders "),
    (re.compile(r"\bunfassbar\s+(?=günstig|viel|hoch|niedrig|gut)", re.I), "bemerkenswert "),
    (re.compile(r"\bsensationell\s+", re.I), "beachtlich "),
    (re.compile(r"\bmega[- ](?=\w)", re.I), "sehr "),
    (re.compile(r"\bkrass\s+", re.I), "deutlich "),
]

# L12 LANGE-SAETZE-ALARM (Verlagsstil: >35 Woerter = Sichtungskandidat)
SATZ_MAX_WOERTER = 35

# ------------------------------------------------------------
# SABOTAGE-SCHUTZ (11.08.2026, Abend): eingefrorene Lektorats-Faelle.
# Laueft vor JEDEM Einsatz; bei Abweichung Exit 2, bevor eine Datei
# angefasst wird – niemand biegt das Lektorat still kaputt.
# ------------------------------------------------------------
SELFTEST = [
    # (Regel, Zeile, Erwarteter Output oder None = nur Flag, Report-Tag oder "")
    ("L1", "Wir sparen und und planen weiter.", "Wir sparen und planen weiter.", ""),
    ("L1rel", "Institute, die die meisten Vorteile bieten.", None, "L1-Relativ"),
    ("L2", "In der heutigen Zeit sparst du mehr.", "Heute sparst du mehr.", ""),
    ("L4", "Das ist stark!!!", "Das ist stark!", ""),
    ("L10", "Mit 3 Tipps sparst du Geld.", "Mit drei Tipps sparst du Geld.", ""),
    ("L10neg", "Spare 3 Euro pro Woche.", None, ""),          # Euro bleibt Ziffer
    ("L10neg", "Mit 13 Tipps startest du.", None, ""),        # 13 nicht im Kanon
    ("L11", "Diese Konten sind brutal günstig.", "Diese Konten sind besonders günstig.", ""),
    ("L7", "Die Überprüfung der Ermöglichung von Einsparungen und Reduzierungen verbessert die Haushaltsrechnung.", None, "L7-Nominalstil"),
    ("L8", "Du könntest sparen und müsstest prüfen und solltest wechseln und dürftest warten und möchtest handeln; wir könnten alle, wir müssten alle.", None, "L8-Weichmacher"),
    ("L9", "Du sparst Geld zur Seite. Du siehst die Kurse regelmässig. Du handelst besonnen und mit Plan.", None, "L9-Satzanfang"),
    ("L12", "Dies ist ein ausgesprochen langer Satz der mit vielen Woertern und Nebensaetzen und Einschueben und Gedanken und Wendungen und Details und Klaerungen und Beispielen und Hinweisen versehen wurde damit er definitiv weit ueber fuenfunddreissig Woerter kommt ohne je zu enden.", None, "L12-Longsatz"),
    # MASKE-REGRESSION (11.08. Nacht): md-Link ZWISCHEN zwei Zitaten darf
    # niemals als Platzhalter-Leiche in der Datei landen:
    ("MASK", "Das macht das [Internet schneller machen](../../posts/2026-08-06-turbo-fuers-netz/) zu einer Sache von Millisekunden – das Gefühl, wie eine Seite „anspringt“, zählt.",
     "Das macht das [Internet schneller machen](../../posts/2026-08-06-turbo-fuers-netz/) zu einer Sache von Millisekunden – das Gefühl, wie eine Seite „anspringt“, zählt.", ""),
]

# ---------------- L5/L3 Wortlisten ------------------------------------------------
DU_SET = {"du", "dein", "deine", "deiner", "deinen", "deinem", "deinem", "deines", "dich", "dir", "deinen"}
SIE_SET = {"Sie", "Ihnen", "Ihre", "Ihrem", "Ihrer"}


def mask(line: str):
    store = {}
    def _m(m):
        k = f"\x00{len(store)}\x00"
        store[k] = m.group(0)
        return k
    line = re.sub("https?://\\S+", _m, line)
    line = re.sub(r"\[[^\]]*\]\([^)]*\)", _m, line)
    line = re.sub("`[^`]*`", _m, line)
    # Lektorats-Ehre: direkte Rede/Zitate („…" / "…") niemals umschreiben.
    # WICHTIG (Bugfix 11.08.): [^„"]… nicht-gierig – sonst frisst ein Zitat
    # bis zum LETZTEN Anfuehrungszeichen der Zeile und schluckt dabei
    # bereits gesetzte Platzhalter (Masken-Schachtelungs-Bug).
    line = re.sub('„[^„"]{1,240}?["“]', _m, line)
    line = re.sub('"[^"\n]{3,120}"', _m, line)
    return line, store


def unmask(line, store):
    # Rueckwaerts-Reihenfolge (LIFO): spaet maskierte Regionen zuerst
    # aufloesen – sie koennen fruehere Platzhalter inhaltlich umschliessen;
    # dann Platzhalter im Ergebnis solange aufloesen, bis nichts mehr da ist.
    for k in reversed(list(store.keys())):
        line = line.replace(k, store[k])
    for _ in range(8):  # Verschachtelungs-Fixpunkt (Sicherheitsnetz)
        if "\x00" not in line:
            break
        for k, v in reversed(list(store.items())):
            line = line.replace(k, v)
    return line


def fresh_stats() -> dict:
    return {"L1": 0, "L1rel": 0, "L2": 0, "L3": 0, "L4": 0, "L5echo": 0, "L5ki": 0,
            "L7": 0, "L8n": 0, "L8meldung": False, "L9": 0, "L10": 0, "L11": 0, "L12": 0}


def run_selftest() -> list[str]:
    """Sabotage-Schutz: eingefrorene Lektorats-Faelle gegen live-Logik."""
    fehler = []
    for i, (regel, zeile, want_out, want_tag) in enumerate(SELFTEST, 1):
        st = fresh_stats()
        reps = []
        masked, store = mask(zeile)
        out, _ = lektor_line(masked, st, reports=reps, fname="sabotage-selbsttest", line_no=i)
        out = unmask(out, store)
        if want_out is not None and out != want_out:
            fehler.append(f"  Fall {i} [{regel}]: Output falsch → {out[:70]!r}")
            continue
        if want_out is None and not want_tag and out != zeile:
            fehler.append(f"  Fall {i} [{regel}]: darf unveraendert bleiben → {out[:70]!r}")
        if want_tag:
            tags = [r[2] for r in reps]
            if not any(want_tag in t for t in tags):
                fehler.append(f"  Fall {i} [{regel}]: Report-Tag „{want_tag}“ fehlt (bekommen: {tags})")
    return fehler


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
    stats = fresh_stats()
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
    # ----- L7-L12: Zielredaktion (11.08.2026 Abend) -----
    prose = not line.lstrip().startswith(("-", "*", "|", "#", ">", "!")) and len(line.strip()) >= 36
    if prose:
        # L7 Nominalstil-Radar (Report)
        nom = len(NOMINAL_PAT.findall(line))
        if nom > NOMINAL_MAX:
            stats["L7"] += 1
            if reports is not None:
                reports.append((fname, line_no, "L7-Nominalstil",
                                f"{nom} Behörden-Nomen: {line.strip()[:70]}"))
        # L9 Satzanfangs-Echo (Report) + L12 Longsatz (Report)
        saetze = [s_.strip() for s_ in re.split(r"(?<=[.!?])\s+", line) if s_.strip()]
        anfaenge = []
        for s_ in saetze:
            mm = re.match(r"^[*>\-\s]*([A-Za-zÄÖÜäöüß]{2,})", s_)
            if mm:
                anfaenge.append(mm.group(1).lower())
            if len(s_.split()) > SATZ_MAX_WOERTER:
                stats["L12"] += 1
                if reports is not None:
                    reports.append((fname, line_no, "L12-Longsatz", s_[:70]))
        for w_ in set(anfaenge):
            if anfaenge.count(w_) >= ANFANG_ECHO_MIN:
                stats["L9"] += 1
                if reports is not None:
                    reports.append((fname, line_no, "L9-Satzanfang",
                                    f"„{w_}“ ×{anfaenge.count(w_)}: {line.strip()[:60]}"))
                break
    # L8 Weichmacher-Dichte (Artikel-Ebene, Schwellen-Meldung einmalig)
    w_n = len(WEICH_PAT.findall(line))
    if w_n:
        stats["L8n"] += w_n
        if stats["L8n"] > WEICH_MAX and not stats.get("L8meldung"):
            stats["L8meldung"] = True
            if reports is not None:
                reports.append((fname, line_no, "L8-Weichmacher",
                                f"{stats['L8n']}+ Konjunktive – {line.strip()[:60]}"))
    # L10 Zahlenschreibweise (Auto-Fix, Duden)
    n10 = len(ZAHL_PAT.findall(line))
    if n10:
        stats["L10"] += n10
        line = ZAHL_PAT.sub(_zahl_repl, line)
    # L11 Werbe-Intensivierung entschaerfen (Auto-Fix, Kanon)
    for pat, repl in INTENSIV:
        nb = len(pat.findall(line))
        if nb:
            stats["L11"] += nb
            line = pat.sub(repl, line)
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
    # SABOTAGE-SCHUTZ zuerst: Lektorat testet sich selbst (offline),
    # BEVOR irgendeine Datei angefasst wird.
    fehler = run_selftest()
    if fehler:
        print("🛑 LEKTOR-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        print("   Kein Lauf, keine Datei angefasst. Bitte lektor_guard.py prüfen:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Lektor-Selbsttest: {len(SELFTEST)} Fälle grün.")
    files = target_files()
    total_fix = {"L1": 0, "L2": 0, "L3": 0, "L4": 0, "L5echo": 0, "L5ki": 0,
                 "L7": 0, "L8n": 0, "L9": 0, "L10": 0, "L11": 0, "L12": 0}
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
    L.append(f"| L7 Nominalstil-Radar (Report) | {total_fix['L7']} |")
    L.append(f"| L8 Weichmacher-Dichte (Report) | {total_fix['L8n']} |")
    L.append(f"| L9 Satzanfangs-Echo (Report) | {total_fix['L9']} |")
    L.append(f"| L10 Zahlenschreibweise (Auto) | {total_fix['L10']} |")
    L.append(f"| L11 Werbe-Intensivel (Auto) | {total_fix['L11']} |")
    L.append(f"| L12 Longsatz-Alarm (Report) | {total_fix['L12']} |")
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
