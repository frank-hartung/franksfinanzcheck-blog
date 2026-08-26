#!/usr/bin/env python3
# ============================================================
#  DASH-GUARD – Profi-Strich-Typografie (selbst entscheidend)
#
#  Entscheidet auf Profi-/Duden-Niveau, welcher Strich wo hingehört,
#  und korrigiert selbstständig. Zwei Ebenen:
#
#  EBENE 1 – DETERMINISTISCHE AUTO-FIXES (immer sicher):
#    R1  " - "  (Bindestrich-Minus als Gedankenstrich)  -> " – "
#    R3  "—"    (Geviertstrich, US-Stil)                -> " – "
#    R4  "--" / "---" im Fließtext                      -> "–"
#    R5  Zahlenbereiche: "10 - 20 Euro" / "10-20 Euro"  -> "10–20 Euro"
#        (Halbgeviert OHNE Leerzeichen; ISO-Daten & URLs geschützt)
#    R6  Asymmetrische Leerzeichen am Gedankenstrich    -> " – "
#
#  EBENE 2 – STIL-SCHIEDSRICHTER (KI, nur mit --ai + API-Key):
#    S1  Satz mit >2 Gedankenstrichen (verklausulierter Doppelschub)
#    S3  Gedankenstrich, wo Komma/Doppelpunkt sauberer wäre
#    Die KI (Groq, Fallback Gemini) entscheidet je Fall: behalten oder
#    sauber umformulieren. Verifikation: URLs/Links/Länge/Dash-Zahl
#    werden gegengeprüft – Änderung wird sonst VERWORFEN.
#
#  NIE ANFASSEN (geschützt): Front-Matter (---...---), Code-Fences,
#  Markdown-Aufzählungsmarker ("- " Zeilenanfang – aber Fehler IM
#  Listentext werden korrigiert), Tabellen-Separatoren (|---|),
#  Überschriften (nur Report, kein Auto-Fix – Titel-Semantik!),
#  URLs/Aliase, HTML-Kommentare, ISO-Datumsangaben (2026-08-10),
#  Wort-Bindestriche (Riester-Rente, 10-jährig) und der Disclaimer.
#
#  Aufruf:
#    python3 scripts/dash_guard.py              # Report über alle Artikel
#    python3 scripts/dash_guard.py --fix        # deterministisch fixen
#    python3 scripts/dash_guard.py --fix --ai   # + KI-Schiedsrichter
#    python3 scripts/dash_guard.py --fix --new-only   # nur neue Artikel
#    python3 scripts/dash_guard.py --dry-run    # zeigen, nichts ändern
#
#  Ausgabe: DASH-REPORT.md (wie SEO-/GRAMMATIK-Report) + Konsole.
#  Idempotent: zweiter Lauf ohne Funde. Exit 0 = OK/Funde behandelt.
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
POSTS_DIRS = [ROOT / "content" / "posts", ROOT / "content" / "pillar"]
REPORT = ROOT / "DASH-REPORT.md"
HISTORY = ROOT / "data" / "dash_guard_history.jsonl"

import groq_config

GROQ_KEY = groq_config.api_key()
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "").strip()

DO_FIX = "--fix" in sys.argv
USE_AI = "--ai" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv


# --------------------------------------------------------- Datei-Auswahl

def target_files() -> list[Path]:
    files = []
    for d in POSTS_DIRS:
        if d.is_dir():
            files += sorted(d.rglob("index.md"))
    if NEW_ONLY:
        changed: set[Path] = set()
        try:
            out = subprocess.run(
                ["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                capture_output=True, text=True, cwd=ROOT, timeout=30,
            ).stdout
            changed = {ROOT / line.strip() for line in out.splitlines() if line.strip()}
        except Exception:
            pass
        # Fallback & Ergänzung (GitHub-Actions-Checkout ist u. U. flach/shallow!):
        today = date.today().isoformat()
        changed |= {f for f in (ROOT / "content").rglob("index.md")
                    if f.parent.name.startswith(today)}
        files = [f for f in files if f in changed]
    return files


# -------------------------------------------------- Schutz-Zonen & Masken

def mask_protected(line: str) -> tuple[str, dict]:
    """Ersetzt URLs/Markdown-Links & Inline-Code durch Platzhalter."""
    store = {}
    def _m(m):
        key = f"\x00{len(store)}\x00"
        store[key] = m.group(0)
        return key
    line = re.sub(r"https?://\S+", _m, line)          # URLs
    line = re.sub(r"\[[^\]]*\]\([^)]*\)", _m, line)    # Markdown-Links
    line = re.sub(r"`[^`]*`", _m, line)                # Inline-Code
    line = re.sub(r"\d{4}-\d{2}-\d{2}", _m, line)      # ISO-Datum
    return line, store


def unmask(line, store):
    # LIFO + Fixpunkt (11.08. Nacht, aus dem lektor-Masken-Bug gelernt):
    # zuletzt maskierte Regionen zuerst loesen, dann bis zur Platzhalter-
    # Freiheit rotieren – Verschachtelung kann so nie mehr lecken.
    for k in reversed(list(store.keys())):
        line = line.replace(k, store[k])
    for _ in range(6):
        if "\x00" not in line:
            break
        for k, v in reversed(list(store.items())):
            line = line.replace(k, v)
    return line


def in_front_matter(idx: int, lines: list[str]) -> bool:
    """Zeile idx innerhalb des Front-Matters? Fence-Erkennung mit
    startswith('---'), damit auch geklebte Fences („---Text") gelten."""
    if lines and lines[0].strip() == "---":
        for j in range(1, min(len(lines), 60)):
            if lines[j].startswith("---"):
                return idx <= j          # 0..j = Front-Matter inkl. Schluss-Fence
    return False


# ------------------------------------------------------- Regelwerk (Ebene 1)

def fix_r153(line: str) -> tuple[str, list[str]]:
    """R1/R3/R4: falsche Gedankenstrich-Typen -> Halbgeviert mit Leerzeichen."""
    notes = []
    # Leerzeichen-symmetrisch normalisieren (R6): " –x" / "x– "->" – "
    new = re.sub(r"\s–(\S)", r" – \1", line)
    new = re.sub(r"(\S)–\s", r"\1 – ", new)
    # R3: Geviertstrich normalisieren ("—"/" — ")
    new = re.sub(r"\s*—\s*", " – ", new)
    # R4: doppelte/dreifache Minus zwischen Wörtern im Fließtext.
    # Anker \w (statt \S): Wortgrenzen links+rechts – SCHÜTZT Zeilenanfänge wie
    # „---Fence"/Markdown-HR/Listensequenzen (Bug-Fix 2026-08-10: R4 hatte
    # geklebte Front-Matter-Fences „---Text" zu „- – Text" deformiert).
    new = re.sub(r"(\w)\s*-{2,3}\s*(\w)", r"\1 – \2", new)
    # R1: gesetztes Minus als Gedankenstrich (" Wort - wort")
    new = re.sub(r"(\w) - ", r"\1 – ", new)
    new = re.sub(r" - (\w)", r" – \1", new)
    if new != line:
        notes.append("Gedankenstrich-Typ")
    return new, notes


# R7: Gedankenstrich direkt NACH Satzende-Punkt (Stil-Orphan, Fund 2026-08-10:
# „…Vertrag. – Ließ …"). Entscheidung nach Folgezeichen:
#   Großbuchstabe danach → neuer Satz, Strich weg:   „. – Deshalb" → „. Deshalb"
#   Kleinbuchstabe danach → Apposition gehört in den Satz: „. – und" → „ – und"
R7_UPPER = re.compile(r"([.!?]) – (?=[A-ZÄÖÜ0-9])")

# R8 (Mikro-Tabelle): Imperativ-Schreibweise am Satzanfang (Fund im selben Satz:
# „Ließ" = Präteritum, richtig ist „Lies"). Eng gefasst – trifft nie ein
# legitimes „Dann ließ er …" (dort klein/mittendrin).
R8_IMPERATIV = re.compile(r"(?<=[.!?] )Ließ (das|dein|deine|deinen|mein|meine|hier|bitte)")


# R9: Geklebte Front-Matter-SCHLUSS-Fence normalisieren.
# „---Text" wird zu „---\n\nText" – NUR an genau einer Stelle: der ersten
# Fence-Zeile nach dem oeffnenden Front-Matter. Verhindert YAML-Parse-Fehler
# in Editoren (GitHub Web-UI!) ohne jedes Layout-Risiko (Hugo aendert nichts).
def normalize_glued_fence(text: str) -> tuple[str, bool]:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text, False
    for j in range(1, min(len(lines), 80)):
        if lines[j].startswith("---"):
            rest = lines[j][3:]
            if rest.strip():                       # geklebt: ---Text
                lines[j] = "---\n" + rest if False else "---\n\n" + rest
                return "\n".join(lines), True
            return text, False                     # sauber: nichts zu tun
    return text, False


def fix_r7_r8(line: str) -> tuple[str, list[str]]:
    new = R7_UPPER.sub(r"\1 ", line)                              # Groß: Strich weg
    new = re.sub(r"([.!?]) – (?=[a-zäöü])", r" – ", new)          # klein: Punkt weg
    new = R8_IMPERATIV.sub(lambda m: "Lies " + m.group(1), new)   # Ließ→Lies
    return new, (["Satzende-/Imperativ-Regel (R7/R8)"] if new != line else [])
BIS_PAT = re.compile(
    r"(?<!\d)(\d+(?:[.,]\d+)?)\s?[-–]\s?"              # Zahl + Strich (verbraucht)
    r"(?=(\d+(?:[.,]\d+)?)(?:\s?(?:Euro|%|Jahr|Monat|Tage|Prozent|€|km|kg|\b)))")
    # zweite Zahl nur per Lookahead -> bleibt im Text stehen. Damit werden auch
    # Ketten überlappend geflickt: 50-30-20 -> 50–30–20 (ohne Verschlucken der Mitte).


def fix_r5(line: str) -> tuple[str, list[str]]:
    """R5: Zahlenbereiche -> Halbgeviert ohne Leerzeichen (10–20 Euro).
    Bereits korrekte Bereiche werden übersprungen; iterativ bis stabil.
    Schützt „10-jährig" (Buchstaben) per Zahlen-Anker und ISO-Daten via Maske."""
    new = line
    while True:
        def _rep(m):
            canonical = f"{m.group(1)}–"
            return m.group(0) if m.group(0) == canonical else canonical
        n2 = BIS_PAT.sub(_rep, new)
        if n2 == new:
            break
        new = n2
    return new, (["Bis-Strich (Zahlenbereich)"] if new != line else [])


STYLE_FINDINGS = []  # (datei, zeile, typ, satz)

def style_check(text: str, fname: str, base_offset: int = 0) -> None:
    """Ebene-2-Erkennung: S1 (>2 Gedankenstriche/Satz), S3 (Strich statt Komma).
    base_offset = Zeilennummer (Aufruf erfolgt zeilenweise)."""
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for s in sentences:
        dashes = s.count("–")
        if dashes >= 3:
            STYLE_FINDINGS.append((fname, base_offset, "S1-Doppelschub", s.strip()))
        elif dashes == 1 and re.search(r"[a-zäöüß] – (und|oder|aber|denn)\s", s):
            # Gedankenstrich vor einfacher Konjunktion -> Komma wäre sauberer
            STYLE_FINDINGS.append((fname, base_offset, "S3-Konjunktion", s.strip()))


# ------------------------------------------------------------- KI-Schiedsamt

def ai_call(prompt: str) -> str | None:
    msgs = [{"role": "user", "content": prompt}]
    try:
        if GROQ_KEY:
            return groq_config.chat(
                messages=[
                    {"role": "system", "content": "Du bist ein deutscher Profi-Lektor (Duden, Webtypografie). Antworte NUR mit JSON."},
                    *msgs,
                ],
                temperature=0.1,
                max_tokens=900,
                timeout=60,
                raise_on_error=True,
            )
    except Exception as e:
        print(f"  ⚠ Groq: {e}")
    try:
        if GEMINI_KEY:
            req = urllib.request.Request(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                params={}, data=json.dumps({
                    "systemInstruction": {"parts": [{"text": "Du bist ein deutscher Profi-Lektor (Duden, Webtypografie). Antworte NUR mit JSON."}]},
                    "contents": [{"parts": [{"text": prompt}]}],
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 900},
                }).encode(),
                headers={"x-goog-api-key": GEMINI_KEY, "Content-Type": "application/json"},
                method="POST")
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read())["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        print(f"  ⚠ Gemini: {e}")
    return None


def ai_arbitrate(satz: str) -> tuple[bool, str]:
    """KI entscheidet: behalten (True, satz) oder ersetzen (False, neu)."""
    prompt = f"""Bewerte diesen deutschen Satz als Lektor – NUR hinsichtlich Gedankenstrichen („–"):

SATZ: {satz}

Regeln des Hauses: Gedankenstrich immer als „ – " (Halbgeviert + Leerzeichen); max. 1 Einschub pro Satz; einfache Anschlüsse mit und/oder/aber bekommen KEINEN Gedankenstrich, sondern Komma oder gar nichts.

Antworte als reines JSON: {{"keep": true}} oder {{"keep": false, "fixed": "..."}}
Bei keep=false: formuliere NUR die Strich-/Satzglied-Probleme um, Inhalt/Wörter/Ton unverändert. Markdown (z. B. **fett**) muss identisch bleiben."""
    out = ai_call(prompt)
    if not out:
        return True, satz
    m = re.search(r"\{.*\}", out, re.DOTALL)
    if not m:
        return True, satz
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return True, satz
    if d.get("keep") or not d.get("fixed"):
        return True, satz
    fixed = d["fixed"].strip()
    # VERIFIKATION (Profi-Gate): Vertrauen ist gut, Kontrolle ist Pflicht.
    if re.findall(r"https?://\S+", satz) != re.findall(r"https?://\S+", fixed):
        return True, satz
    if not (0.6 <= len(fixed) / max(1, len(satz)) <= 1.5):
        return True, satz
    if fixed.count("**") != satz.count("**"):
        return True, satz
    if fixed.count("–") > satz.count("–"):
        return True, satz
    return False, fixed


# ------------------------------------------------------------ Hauptverarbeitung

def process_file(path: Path) -> dict:
    rel = path.relative_to(ROOT)
    text = path.read_text(encoding="utf-8")
    # R9: geklebte Schluss-Fence zuerst heilen (Datei-Ebene, sonst YAML-Bruch
    # in Editoren & Guards!)
    text, _glued_fixed = normalize_glued_fence(text)
    if _glued_fixed:
        pass  # Zaehlung unten im Schreibpfad (gleiche Bedingung wie Zeilenregeln)
    lines = text.split("\n")
    out, stats = [], {"R": 0, "KI": 0}
    in_code = False
    global STYLE_FINDINGS
    STYLE_FINDINGS = []

    for i, line in enumerate(lines):
        stripped = line.strip()
        # Schutzzonen
        if stripped.startswith("```"):
            in_code = not in_code
            out.append(line); continue
        # GEKLEBTER FENCE („---Zahlst du …"): Prefix "---" immer schützen,
        # angeschlossener Text IST Body und wird geregelt. Muss VOR der
        # Front-Matter-Schutz-Abfrage stehen (die den Fence sonst ganz auslässt)!
        fence_prefix = ""
        if line.startswith("---") and len(line) > 3:
            fence_prefix, line = "---", line[3:]
            stripped = line.strip()
        if in_code or (in_front_matter(i, lines) and not fence_prefix):
            out.append(fence_prefix + line); continue
        if (re.fullmatch(r"\s*[-|–:\s]*", stripped or "|")      # Tabellen-Separator
                or stripped == "---"                            # Trennlinie
                or stripped.startswith("<!--")):                # HTML-Kommentar
            out.append(fence_prefix + line); continue

        is_heading = stripped.startswith("#")
        prefix = ""
        body = line
        m = re.match(r"^(\s*[-*]\s+)(.*)$", line)   # Listenmarker schützen,
        if m:                                        # Fehler IM Punkt fixen
            prefix, body = m.group(1), m.group(2)

        masked, store = mask_protected(body)
        fixed, notes = fix_r153(masked)
        fixed, n5 = fix_r5(fixed)
        notes += n5
        fixed, n78 = fix_r7_r8(fixed)
        notes += n78
        fixed = unmask(fixed, store)

        if is_heading:
            fixed = body  # Überschriften: NIE auto-fixen, nur Report
            if (body != masked) or notes:
                notes = [f"Überschrift prüfen ({'; '.join(notes)})"]
        if fixed != body and not is_heading and DO_FIX and not DRY_RUN:
            stats["R"] += len(notes)
        style_check(fixed, str(rel), i)
        out.append(fence_prefix + prefix + (fixed if (not is_heading) else body))

    # Ebene 2: KI-Schiedsrichter über Stil-Funde (nur mit --ai und Keys)
    ki_changes = []
    if USE_AI and (GROQ_KEY or GEMINI_KEY) and STYLE_FINDINGS:
        full = "\n".join(out)
        for fname, pos, typ, satz in STYLE_FINDINGS[:5]:   # Kostenbremse: max 5/Artikel
            drop, new_satz = ai_arbitrate(satz)
            if not drop and new_satz != satz and satz in full and not DRY_RUN:
                full = full.replace(satz, new_satz, 1)
                ki_changes.append(typ)
                stats["KI"] += 1
        if ki_changes:
            return {"file": str(rel), "stats": stats, "text": full}

    if stats["R"] or (DO_FIX and not DRY_RUN):
        if _glued_fixed:
            stats["R"] += 1
        return {"file": str(rel), "stats": stats, "text": "\n".join(out),
                "styles": list(STYLE_FINDINGS)}
    return {"file": str(rel), "stats": stats, "text": None, "styles": list(STYLE_FINDINGS)}


def main() -> None:
    files = target_files()
    if not files:
        print("Keine Zieldateien (ggf. --new-only ohne Änderungen).")
        REPORT.write_text(f"# 📏 DASH-REPORT\n\n**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC\n\nNichts zu prüfen.\n", encoding="utf-8")
        return

    touched, findings, styles_all = [], [], []
    for p in files:
        res = process_file(p)
        styles_all += res.get("styles", [])
        r = res["stats"]["R"] + res["stats"]["KI"]
        if res["text"] is not None and r > 0 and DO_FIX:
            path = p
            if res["text"] != path.read_text(encoding="utf-8"):
                path.write_text(res["text"], encoding="utf-8")
                if not DRY_RUN:
                    touched.append((res["file"], res["stats"]))
        elif r > 0:
            findings.append((res["file"], res["stats"]))

    mode = "DRY-RUN" if DRY_RUN else ("FIX" + ("+KI" if (USE_AI) else "") if DO_FIX else "REPORT")
    lines = [f"# 📏 DASH-REPORT (dash_guard.py)", "",
             f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}", ""]
    if touched:
        lines += [f"## ✅ Automatisch korrigiert ({len(touched)} Dateien)", ""]
        lines += [f"- `{f}`: Regel-Fixes {s['R']}, KI-Umformulierungen {s['KI']}" for f, s in touched]
    if findings and not DO_FIX:
        lines += [f"## 🔍 Befunde ohne Fix ({len(findings)} Dateien) – Aufruf mit --fix", ""]
        lines += [f"- `{f}`: {s['R']} Regel-Funde" for f, s in findings[:40]]
    if not touched and not findings:
        lines.append("🎉 Alle geprüften Artikel sind strich-typografisch sauber (Duden-Level).")
    # Stil-Funde (Ebene 2) transparent machen – KI-Schiedsrichter bearbeitet sie
    # nur mit --ai; im REPORT bleiben sie als Hinweis sichtbar:
    if styles_all:
        lines += ["", "## 🎓 Stil-Hinweise (Ebene 2, nur Info bzw. mit --ai aktiv)", ""]
        lines += [f"- `{fn}` Zeile {ln}: {typ}" for fn, ln, typ, _ in styles_all[:15]]
    lines += ["", "---", "_Deterministisch: Gedankenstrich-Typ, Bis-Striche, Doppelminus · "
              "KI-Schiedsrichter (S1/S3) nur mit --ai. Geschützt: Front-Matter, Listen, "
              "Tabellen, Überschriften, URLs, Code._"]
    REPORT.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("\n".join(lines[:30]))
    if HISTORY.parent.exists() or True:
        HISTORY.parent.mkdir(exist_ok=True)
        with HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"date": date.today().isoformat(), "mode": mode,
                                 "fixed": len(touched), "found": len(findings)}) + "\n")


if __name__ == "__main__":
    main()
