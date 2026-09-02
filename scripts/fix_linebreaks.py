#!/usr/bin/env python3
"""fix_linebreaks.py – VOLLAUTOMATISCHER ZEILENUMBRUCH-GENERATOR (PROFI-LEVEL, KI-ENTSCHEIDER)

Der Generator entscheidet SELBST per KI, ob ein Zeilenumbruch sinnvoll ist –
OHNE Wortlisten-Heuristiken („alle bisherigen Sonderregelungen entfernt").

WIE ER ARBEITET:
  1) KANDIDATEN SAMMELN: Alle „ – "-Stellen im Fließtext (auch bereits
     umgebrochene Zeilen werden als Kandidaten mit „aktuell umgebrochen"
     markiert) – die KI entscheidet über jeden einzelnen.
  2) KI-ENTSCHEIDUNG (Groq/Gemini, Batch pro Datei): Jeder Kandidat wird
     mit Kontext (Satz vor/nach dem Gedankenstrich) präsentiert. Die KI
     antwortet pro Kandidat mit „ja" (Umbruch sinnvoll) oder „nein".
  3) ANWENDEN: „ja" → Hard-Break (2 Spaces + Newline) setzen bzw. behalten;
     „nein" → zurückbauen (Zeilen zusammenführen).
  4) SELBSTHEILUNG (deterministisch, ohne KI): Umbrüche in technisch
     unpassenden Kontexten werden IMMER zurückgebaut – FAQ-Antworten
     (FAQPage-JSON-LD!), Listenelemente, Tabellen, Inline-Code,
     Blockquotes. Diese Kontexte sind keine „Geschmacks-Sonderregeln",
     sondern technisch zwingend (sonst bricht das Schema/HTML).
  5) FALLBACK OHNE KI (kein API-Key/Fehler): Keine neuen Umbrüche, aber
     die Selbstheilung in Schutzkontexten läuft weiter – der Blog bleibt
     immer konsistent.

Aufruf:  python3 scripts/fix_linebreaks.py             (alle Dateien)
         python3 scripts/fix_linebreaks.py --dry-run   (nur anzeigen)
         python3 scripts/fix_linebreaks.py --file X    (eine Datei)
"""
import glob
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import groq_config

RE_FAQ_START = re.compile(
    r"^#{1,2}\s*(Häufige Fragen|Häufig gestellte Fragen|Häufige Fragen \(FAQ\)|FAQ)\s*$",
    re.I)
RE_BROKEN_END = re.compile(r"[ \u00a0]{2,}$")       # Zeile endet mit Hard-Break-Spuren
RE_DASH = re.compile(r"\u2013")                      # Gedankenstrich


# ---------------------------------------------------------------------------
# Kontext-Erkennung (nur technisch zwingende Schutzbereiche)
# ---------------------------------------------------------------------------

def _is_protected(line: str) -> bool:
    """Zeilen, in denen NIE umgebrochen werden darf (technisch zwingend)."""
    if "|" in line or "`" in line:
        return True
    if line.lstrip().startswith((">", "```")):
        return True
    if re.match(r"^\s*(?:[-*]|\d+\.)\s+", line):     # Listenelement
        return True
    if line.lstrip().startswith("#"):                 # Überschrift
        return True
    return False


# Definitions-Listen-Muster: Zeile beginnt mit "**Fett-Titel:**" (mit oder ohne
# Listen-Marker davor). Das ist ein Aufzählungs-/Tipp-Stil, bei dem der ganze
# Absatz als EINHEIT gehört – ein Umbruch nach dem Gedankenstrich zerreisst
# die Definition. Wird deterministisch geschuetzt und zurueckgebaut.
RE_LEAD = re.compile(r"^\s*(?:[-*]\s+)?\*\*[^*]+:\*\*")


def _is_lead_definition(line: str) -> bool:
    return bool(RE_LEAD.match(line))


def _find_candidates(body: str) -> list[dict]:
    """Sammelt alle Kandidaten im Fließtext (außerhalb Schutzkontexte)."""
    lines = body.split("\n")
    candidates = []
    in_faq = False
    for i, line in enumerate(lines):
        if re.match(r"^#{1,6}\s+", line):
            if RE_FAQ_START.match(line):
                in_faq = True
            elif re.match(r"^#{1,2}\s+", line):
                in_faq = False
        if in_faq or _is_protected(line) or _is_lead_definition(line):
            continue
        is_broken = bool(RE_BROKEN_END.search(line))
        has_dash = bool(RE_DASH.search(line))
        if not (is_broken or has_dash):
            continue
        # Nächste Zeile = Fortsetzung (bei umgebrochener Zeile)
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        candidates.append({
            "idx": i,
            "line": line.rstrip(),
            "broken": is_broken,
            "next": nxt,
        })
    return candidates


# ---------------------------------------------------------------------------
# KI-Entscheidung
# ---------------------------------------------------------------------------

def _llm_call(prompt: str, provider: str) -> str | None:
    """Ruft Groq oder Gemini an. Liefert Antwort-Text oder None."""
    try:
        if provider == "GROQ":
            out = groq_config.chat(prompt, temperature=0.1, max_tokens=2000, timeout=60)
            if out:
                time.sleep(4)  # Rate-Limit-Schutz (Gratis-Key)
            return out
        else:
            key = os.environ.get("GEMINI_API_KEY", "")
            url = ("https://generativelanguage.googleapis.com/v1beta/models/"
                   + os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
                   + ":generateContent?key=" + key)
            data = json.dumps({
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 2000},
            }).encode()
            req = urllib.request.Request(url, data=data, headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (Finanzblog-Automation)"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.loads(r.read().decode())["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:  # noqa: BLE001
        print(f"    ⚠ {provider}-Fehler: {e}")
        return None


def _ai_decide(candidates: list[dict]) -> list[bool]:
    """Fragt die KI, ob pro Kandidat ein Umbruch sinnvoll ist.
    Liefert Liste von bool (True = Umbruch). Bei KI-Fehler: konservativ False."""
    if not candidates:
        return []
    prompt_lines = [
        "Du bist ein Typografie-Experte für einen deutschen Finanzblog.",
        "Für jede Stelle mit Gedankenstrich entscheidest du, ob ein Zeilenumbruch "
        "nach dem Gedankenstrich sinnvoll ist (der Nachsatz beginnt auf einer neuen "
        "Zeile) oder ob der Satz zusammenbleiben soll.",
        "UMBRUCH sinnvoll (ja), wenn: der Nachsatz ein eigenständiger, erläuternder "
        "Gedanke ist (z. B. '…Reisedauern –  die 10-Tage-Variante ist besser').",
        "KEIN Umbruch (nein), wenn: der Nachsatz eng zur Zahl/Aussage davor gehört "
        "(z. B. '2.653 Euro – mehr als 650 Euro zusätzlich'), eine kurze Ergänzung "
        "ist, oder der Satz ohne Umbruch besser liest.",
        "Antworte NUR im Format: Nummer|ja oder Nummer|nein – eine Zeile pro Nummer.",
        "",
    ]
    for k, c in enumerate(candidates, 1):
        vor = c["line"][-70:] if len(c["line"]) > 70 else c["line"]
        nach = c["next"][:70]
        status = " (aktuell umgebrochen)" if c["broken"] else ""
        prompt_lines.append(f"{k}. …{vor} – {nach}…{status}")
    prompt = "\n".join(prompt_lines)

    # Provider-Rotation
    for provider in ("GROQ", "GEMINI"):
        if not os.environ.get(f"{provider}_API_KEY"):
            continue
        answer = _llm_call(prompt, provider)
        if answer:
            decisions = {}
            for line in answer.strip().splitlines():
                m = re.match(r"^\s*(\d+)\s*[|:]\s*(ja|nein)\b", line, re.I)
                if m:
                    decisions[int(m.group(1))] = m.group(2).lower() == "ja"
            if decisions:
                return [decisions.get(k + 1, False) for k in range(len(candidates))]
    print("    ⚠ Keine KI-Antwort – konservativ: keine neuen Umbrüche.")
    return [c["broken"] for c in candidates]  # Bestand halten, nichts Neues


# ---------------------------------------------------------------------------
# Anwenden
# ---------------------------------------------------------------------------

def apply_decisions(body: str, candidates: list[dict], decisions: list[bool]) -> tuple[str, int]:
    """Setzt/baut Umbrüche gemäß KI-Entscheidung. Liefert (neuer_body, anzahl)."""
    lines = body.split("\n")
    # Rückwärts arbeiten, damit Indizes stabil bleiben
    changed = 0
    for c, want_break in zip(reversed(candidates), reversed(decisions)):
        i = c["idx"]
        line = lines[i]
        nxt = lines[i + 1] if i + 1 < len(lines) else ""
        if want_break:
            if c["broken"]:
                continue  # schon umgebrochen – ok
            if nxt and not _is_protected(nxt) and not RE_BROKEN_END.search(nxt):
                lines[i] = line.rstrip() + "  "
                changed += 1
        else:
            if c["broken"] and nxt:
                lines[i] = line.rstrip() + " " + nxt.strip()
                del lines[i + 1]
                changed += 1
    return "\n".join(lines), changed


def self_heal(body: str) -> tuple[str, int]:
    """Deterministische Selbstheilung: Umbrüche in Schutzkontexten zurückbauen."""
    lines = body.split("\n")
    out: list[str] = []
    changed = 0
    in_faq = False
    i = 0
    n = len(lines)
    while i < n:
        line = lines[i]
        if re.match(r"^#{1,6}\s+", line):
            if RE_FAQ_START.match(line):
                in_faq = True
            elif re.match(r"^#{1,2}\s+", line):
                in_faq = False
        if (in_faq or _is_protected(line) or _is_lead_definition(line)) \
                and RE_BROKEN_END.search(line) and i + 1 < n:
            nxt = lines[i + 1].strip()
            if nxt and not RE_BROKEN_END.search(nxt) and not re.match(r"^#{1,6}\s+", nxt):
                out.append(line.rstrip() + " " + nxt)
                changed += 1
                i += 2
                continue
        out.append(line)
        i += 1
    return "\n".join(out), changed


def _apply_heading_breaks(body: str) -> tuple[str, int]:
    """DAUERHAFT DEAKTIVIERT (02.09.2026, Wöchentliche SEO-Optimierung #20).

    Die alte Design-Vorgabe „H2/H3 mit Doppelpunkt bekommen :<br>“ ist seit
    27.08.2026 außer Kraft – Haus-Regel: KEIN <br> in Überschriften, weil es
    TOC-Texte zerstört („Fazit:\\ Ein …“) und die Anker-Logik gefährdet
    (heading_guard.py heilt seither anker-stabil, blog_health_gate ruft es
    täglich). Beide Bots stritten täglich: heading_guard entfernte nachts,
    fix_linebreaks setzte per Engine/SEO-Weekly wieder `<br>` – Beweis am
    02.09.: 05:51 Uhr 118 Überschriften geheilt, 06:43 Uhr von Engine
    Phase 2 (dieser Aufruf) komplett zurückgesetzt, 121 Geister-Funde live.
    AB JETZT ändert diese Funktion Überschriften NIE wieder; Altlasten werden
    nur gezählt (die anker-stabile Heilung bleibt Hoheit von heading_guard)."""
    relikt = sum(1 for line in body.split("\n")
                 if re.match(r"^#{1,6}\s+", line) and "<br" in line.lower())
    if relikt:
        print(f"    ℹ {relikt} Überschrift(en) tragen Altlast-<br> – Heilung "
              f"(anker-stabil) gehört heading_guard.py, nicht mehr dieser Funktion.")
    return body, 0


def fix_body(body: str) -> tuple[str, int]:
    """Hauptfunktion: Überschriften → Selbstheilung → KI-Entscheidung."""
    # 1) Überschriften-Doppelpunkt (Design-Vorgabe)
    body, n0 = _apply_heading_breaks(body)
    # 2) Selbstheilung (Schutzkontexte deterministisch bereinigen)
    body, n1 = self_heal(body)
    # 2) Kandidaten sammeln (nach Selbstheilung neu)
    candidates = _find_candidates(body)
    if not candidates:
        return body, n1
    # 3) KI entscheiden
    decisions = _ai_decide(candidates)
    # 4) Anwenden
    body, n2 = apply_decisions(body, candidates, decisions)
    return body, n0 + n1 + n2


def main() -> int:
    dry = "--dry-run" in sys.argv
    only = None
    if "--file" in sys.argv:
        only = sys.argv[sys.argv.index("--file") + 1]
    files = (sorted(glob.glob(f"{BLOG_DIR}/content/posts/*/index.md"))
             + sorted(glob.glob(f"{BLOG_DIR}/content/pillar/*/index.md")))
    if only:
        files = [f for f in files if only in f]
    total = 0
    for f in files:
        content = open(f, encoding="utf-8").read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        new_body, n = fix_body(parts[2])
        if n:
            total += n
            print(f"  {f.split('/')[-2]}: {n} Änderung(en)")
            if not dry:
                open(f, "w", encoding="utf-8").write(parts[0] + "---" + parts[1] + "---" + new_body)
    print(f"\n{'DRY-RUN: ' if dry else ''}Zeilenumbruch-Generator (KI): {total} Änderungen.")
    if not dry:
        try:
            from audit_log import log_event
            log_event(module="fix_linebreaks", action="apply",
                      input={"files": len(files)}, output={"changes": total},
                      status="ok")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
