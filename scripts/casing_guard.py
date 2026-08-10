#!/usr/bin/env python3
# ============================================================
#  CASING-GUARD – Akronym-Orthografie (selbst entscheidend)
#
#  AUFTRAG (10.08.2026, Fund: „Ein dsl Wechselbonus"):
#  Deutsche Regeln für Akronyme (Duden): DSL, WLAN, ETF, 5G … werden
#  a) immer in der kanonischen Schreibweise geschrieben
#     (nie „dsl"; Satzanfang: „DSL", nicht „Dsl")
#  b) in Zusammensetzungen DURCHGEKOPPELT:
#     „DSL Wechselbonus" -> „DSL-Wechselbonus" („5G Home" -> „5G-Home").
#
#  REGELN:
#    C1  Akronym komplett klein/falsch gemischt -> kanonische Form
#        („etf" -> „ETF", „wlans" -> „WLANs", Binnenmajuskel-Schutz)
#    C2  Akronym + Nomen (Liste) ohne Bindestrich -> Durchkopplung
#        („5G Netz" -> „5G-Netz"); Genus/Plural-Endungen tolerant.
#
#  GESCHÜTZT (niemals anfassen):
#    - Front-Matter KOMPLETT (keywords = SEO-Suchanfragen, bleiben klein!)
#    - URLs & Markdown-Linkziele, Slugs, Code-Fences, Inline-Code
#    - Eigennamen-Whitelist, Hashtags (#5g ok – wirkt im Social-Kontext)
#
#  STATUS-STUFEN: Fund -> Auto-Fix (--fix) -> CASING-REPORT.md.
#  KI braucht es hier nicht: Diese Regeln sind Dudenentscheidungen,
#  deterministisch exakt (Profi-Level = kein Zufall durch Modelle).
#
#  Aufruf:
#    python3 scripts/casing_guard.py             # Report
#    python3 scripts/casing_guard.py --fix       # korrigieren
#    python3 scripts/casing_guard.py --new-only  # Engine-Modus
# ============================================================

import re
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "CASING-REPORT.md"

DO_FIX = "--fix" in sys.argv
DRY_RUN = "--dry-run" in sys.argv
NEW_ONLY = "--new-only" in sys.argv

# Kanonische Groß-/Kleinschreibung (Binnenmajuskeln beachten!):
ACRONYMS = {
    "dsl": "DSL", "wlan": "WLAN", "etf": "ETF", "etfs": "ETFs",
    "kfz": "Kfz", "sim": "SIM", "sms": "SMS", "pin": "PIN", "tan": "TAN",
    "sepa": "SEPA", "nfc": "NFC", "usb": "USB", "lte": "LTE",
    "5g": "5G", "4g": "4G", "hdmi": "HDMI", "usb-c": "USB-C",
    # Anglizismen-Nomen (kein Akronym, aber Nomen-Regel): Cashback groß
    "cashback": "Cashback",
}
# Nomen, die bei Akronym-Direktkontakt durchkoppelt werden (Dudenkoalition):
COUPLE_NOUNS = ("Tarif", "Tarife", "Tarifen", "Wechselbonus", "Anbieter", "Angebote",
                "Vergleich", "Vergleiche", "Netz", "Netze", "Vertrag", "Verträge",
                "Router", "Empfang", "Signal", "Zugang", "Flat", "Flatrate",
                "Geschwindigkeit", "Internet", "Karte", "Sparplan", "Depot",
                "Kosten", "Gebühren", "Preise", "Home", "Top", "Tipps", "Kabel",
                "Anschluss", "Option", "Optionen", "Paket", "Pakete", "Modem")
ACRO_FOR_COUPLE = ("DSL", "WLAN", "LTE", "4G", "5G", "NFC", "SIM", "ETF", "ETFs",
                   "PIN", "TAN", "USB", "HDMI", "SEPA", "Kfz", "SMS")

C1_RE = re.compile(r"\b(" + "|".join(ACRONYMS) + r")\b", re.IGNORECASE)
C2_RE = re.compile(r"\b(" + "|".join(ACRO_FOR_COUPLE) + r") ("
                   + "|".join(COUPLE_NOUNS) + r")(?:e[nrms]?|s)?\b")

WHITELIST = re.compile(r"^\s*(#|//|\{%)")        # Zeilen, die nie angefasst werden
SITZWEST = {"pin"}, {"pin": "PIN"}                 # Sicherheitswortliste


def mask(line: str):
    store = {}
    def _m(m):
        k = f"\x00{len(store)}\x00"
        store[k] = m.group(0)
        return k
    line = re.sub(r"https?://\S+", _m, line)
    line = re.sub(r"\[[^\]]*\]\([^)]*\)", _m, line)
    line = re.sub(r"`[^`]*`", _m, line)
    line = re.sub(r"#[A-Za-z0-9äöüÄÖÜ_-]+", _m, line)   # Hashtags schonen
    return line, store


def unmask(line, store):
    for k, v in store.items():
        line = line.replace(k, v)
    return line


def fix_line(body: str) -> tuple[str, int]:
    hits = 0
    def _c1(m):
        nonlocal hits
        w = m.group(1)
        canon = ACRONYMS[w.lower()]
        if w != canon:
            hits += 1
            return canon
        return w
    body = C1_RE.sub(_c1, body)
    def _c2(m):
        nonlocal hits
        hits += 1
        return f"{m.group(1)}-{m.group(2)}{m.group(3) or ''}"
    # Gruppenerweiterung: Flexionsendung beibehalten („DSL Tarifen" -> „DSL-Tarifen")
    # Gruppen: 1=Akronym, 2=gesamtes Segment, 3=Nomen, 4=Flexionsendung
    def _c2b(m):
        nonlocal hits
        noun, tail = m.group(3), m.group(4) or ""
        hits += 1
        return f"{m.group(1)}-{noun}{tail}"
    body = re.sub(r"\b(" + "|".join(ACRO_FOR_COUPLE) + r") (("
                  + "|".join(COUPLE_NOUNS) + r")(e[nrms]?|s)?)\b", _c2b, body)
    return body, hits


def process(path: Path):
    rel = str(path.relative_to(ROOT))
    lines = path.read_text(encoding="utf-8").split("\n")
    in_code, fm_seen_close, i = False, False, -1
    out, changes = [], 0
    for raw in lines:
        i += 1
        s = raw.strip()
        if s.startswith("```"):
            in_code = not in_code
            out.append(raw); continue
        if i == 0 and s == "---":
            out.append(raw); continue
        if not fm_seen_close:                       # Front-Matter = SEO-Safe-Zone
            if i > 0 and raw.startswith("---"):
                fm_seen_close = True
                rest = raw[3:]
                if rest.strip() == "":
                    out.append(raw); continue
                # GEKLEBTER Fence („---Zahlst du …"): Rest ist schon Body!
                masked, store = mask(rest)
                fixed, n = fix_line(masked)
                fixed = unmask(fixed, store)
                if fixed != rest:
                    changes += n
                out.append("---" + fixed)
                continue
            out.append(raw); continue
        if in_code or WHITELIST.match(raw) or s == "---":
            out.append(raw); continue
        prefix = ""
        body = raw
        m = re.match(r"^(\s*[-*>#]+\s+)(.*)$", raw)  # Listen-/Zitat-Marker schützen
        if m:
            prefix, body = m.group(1), m.group(2)
        masked, store = mask(body)
        fixed, n = fix_line(masked)
        fixed = unmask(fixed, store)
        if fixed != body:
            changes += n
        out.append(prefix + fixed)
    return changes, "\n".join(out)


def target_files():
    files = []
    for d in ("posts", "pillar", "ueber", "datenschutz", "impressum"):
        dd = ROOT / "content" / d
        if dd.is_dir():
            files += sorted(dd.rglob("*.md"))
    if files and NEW_ONLY:
        try:
            out = subprocess.run(["git", "diff", "--name-only", "HEAD~2", "HEAD", "--", "content/"],
                                 capture_output=True, text=True, cwd=ROOT, timeout=30).stdout
            changed = {ROOT / l.strip() for l in out.splitlines() if l.strip()}
        except Exception:
            changed = set()
        today = date.today().isoformat()
        changed |= {f for f in (ROOT / "content").rglob("index.md") if f.parent.name.startswith(today)}
        files = [f for f in files if f in changed]
    return files


def main() -> None:
    files = target_files()
    touched = []
    for p in files:
        n, new_text = process(p)
        if n and DO_FIX and not DRY_RUN and new_text != p.read_text(encoding="utf-8"):
            p.write_text(new_text, encoding="utf-8")
            touched.append((str(p.relative_to(ROOT)), n))
        elif n:
            touched.append((str(p.relative_to(ROOT)), n))

    mode = "DRY-RUN" if DRY_RUN else ("FIX" if DO_FIX else "REPORT")
    L = ["# 🔠 CASING-REPORT (casing_guard.py)", "",
         f"**Stand:** {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · Modus: {mode}", ""]
    if touched:
        L += [f"## {'✅ Korrigiert' if DO_FIX else '🔍 Befunde'} ({len(touched)} Dateien)", ""]
        L += [f"- `{f}`: {n} Korrektur(en)" for f, n in touched[:30]]
    else:
        L.append("🎉 Akronym-Orthografie sauber (C1 + C2, Duden).")
    L += ["", "---", "_C1 kanonische Akronym-Schreibweise (dsl→DSL) · C2 Durchkopplung "
          "(DSL Tarif→DSL-Tarif). Front-Matter = SEO-Safe-Zone (Keywords bleiben klein)._"]
    REPORT.write_text("\n".join(L) + "\n", encoding="utf-8")
    print("\n".join(L[:25]))


if __name__ == "__main__":
    main()
