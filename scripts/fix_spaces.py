#!/usr/bin/env python3
"""fix_spaces.py – VOLLAUTOMATISCHER LEERZEICHEN-GENERATOR (PROFI-LEVEL)

Entscheidet SELBST, ob ein Leerzeichen sinnvoll ist – und ist
SELBSTHEILEND (idempotent, schützt bewusste Formatierung).

WAS ER KANN:
  A) DOPPELTE LEERZEICHEN im Fließtext → 1 Leerzeichen. Bewusste
     Markdown-Hard-Breaks (2+ Spaces am ZEILENENDE, z. B. nach „ – ")
     bleiben UNANGETASTET – sie sind vom Zeilenumbruch-Generator gesetzt.
  B) LISTEN-MARKER normalisieren: „*   Text" / „-   Text" / „1.   Text"
     (3+ Spaces nach dem Marker) → 1 Space.
  C) LEERZEICHEN VOR SATZZEICHEN entfernen („Hallo ," → „Hallo,") –
     selbstheilend, falls welche auftauchen.
  D) FEHLENDES LEERZEICHEN NACH .!? ergänzen („Satz.Neuer" → „Satz.
     Neuer") – mit Schutz für Abkürzungen (z. B., d. h., usw., ca., …),
     URLs, Markdown-Links und E-Mail-Adressen.
  E) FEHLENDES LEERZEICHEN NACH KOMMA ergänzen („Hallo,Welt" →
     „Hallo, Welt") – mit Link-/Zahlen-Schutz („3,5", „1,2").
  H) ZERRISSENE DOMAINS joins: „www. google. de" → „www.google.de",
     „@Anbieter. de" → „@Anbieter.de". Entsteht, wenn fruehere Regeln
     Punkt+Leerzeichen eingefuegt haben. Nur mit Hostname-Pruefung
     (Label-Laengen, TLD-Liste, www/@/Hyphen-/Zahlen-Beleg) – deshalb kein
     Risiko fuer Fliesstext wie „die Stadt. de".  (Regel D kann das nicht:
     sie fuegt Leerzeichen erst ein.)
  F) GESCHÜTZTES LEERZEICHEN (U+00A0) zwischen Zahl und %/€
     sicherstellen (kein Umbruch zwischen Zahl und Einheit).

NICHT ANGE FASTET: Tabellenzeilen (|), Inline-Code (`), Blockquotes (>),
Überschriften-Markup, Link-URLs, bereits gesetzte NBSP.

Aufruf:  python3 scripts/fix_spaces.py            (alle Dateien)
         python3 scripts/fix_spaces.py --dry-run  (nur anzeigen)
"""
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

NBSP = "\u00a0"

# Abkürzungen, nach denen KEIN Satzende folgt (Schutz für Regel D)
ABKUERZUNGEN = (
    "z\\.\\s?B\\.", "d\\.\\s?h\\.", "u\\.\\s?a\\.", "u\\.\\s?ä\\.", "v\\.\\s?a\\.",
    "usw\\.", "etc\\.", "bzw\\.", "ca\\.", "inkl\\.", "exkl\\.", "Nr\\.",
    "Dr\\.", "Prof\\.", "z\\.\\s?T\\.", "s\\.\\s?o\\.", "s\\.\\s?u\\.", "u\\.\\s?U\\.",
    "Abs\\.", "Art\\.", "Bd\\.", "Bsp\\.", "ggf\\.", "evtl\\.", "i\\.\\s?d\\.\\s?R\\.",
    "Tel\\.", "Mo\\.", "Di\\.", "Mi\\.", "Do\\.", "Fr\\.", "Sa\\.", "So\\.",
    "Jan\\.", "Feb\\.", "Mär\\.", "Apr\\.", "Jun\\.", "Jul\\.", "Aug\\.", "Sep\\.",
    "Okt\\.", "Nov\\.", "Dez\\.", "b\\.\\s?w\\.",
)
ABK_RE = re.compile(r"(?:" + "|".join(ABKUERZUNGEN) + r")(?=\s+[A-Za-zäöüß])")

# Muster: Buchstabe/Zahl + Satzzeichen + direkt Buchstabe (fehlendes Leerzeichen)
RE_MISSING_AFTER_PUNCT = re.compile(r"([a-zäöüßA-ZÄÖÜ0-9\)])([.!?])([a-zäöüßA-ZÄÖÜ])")
RE_MISSING_AFTER_COMMA = re.compile(r"([a-zäöüßA-ZÄÖÜ0-9\)]),([a-zäöüßA-ZÄÖÜ])")
# Achtung: „3,5" / „1,2" (Dezimalzahlen) sind keine Komma-Fehler – geschützt
RE_COMMA_NUMBER = re.compile(r"\d,\d")
RE_SPACE_BEFORE_PUNCT = re.compile(r" +([,.;:!?])")
# Regel-D-Schutz: Ausrufezeichen/Zwischenruf *zwischen* Wortteilen ist kein
# Satzende (FRITZ!Box, Adobe!-Schreibweisen, „24!-Aktion“).
RE_INWORD_BANG = re.compile(r"(?<=[A-Za-z0-9\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df])[!](?=[A-Za-z0-9\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df])")
# --- Regel H: zerrissene Domains -------------------------------------------------
TLD = ("de", "com", "net", "org", "io", "eu", "app", "info", "shop", "online",
       "site", "cloud", "box", "one", "dev", "at", "ch", "uk")
# Namen, die im Blog als Domain vorkommen (Markenkanon + Provider). Wachst
# automatisch mit dem Casing-Lexikon mit (tag_casing.BRANDS).
DOMAIN_HINTS = {"www", "mail", "ftp", "m", "web", "gmx", "posteo", "t-online",
                "google", "cloudflare", "quad9", "check24", "verivox",
                "tarifcheck", "congstar", "otelo", "vodafone", "telekom",
                "o2", "pyur", "franksfinanzcheck", "idealo", "ebay", "paypal"}
try:
    import sys as _sys
    _sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
    import tag_casing as _tc
    DOMAIN_HINTS |= {re.sub(r"[^a-z0-9.-]", "", v.lower()) for v in _tc.BRANDS.values()}
except Exception:                                     # pragma: no cover
    pass
RE_DOMAIN_FRAGMENT = re.compile(
    r"(?<![\w./-])((?:[A-Za-z0-9.\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df-]{1,41}\. [A-Za-z0-9.\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df-]{0,41})*"
    r"[A-Za-z0-9.\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df-]{1,41}\. ?(?:de|com|net|org|io|eu|app|info|shop|online|site|cloud|box|one|dev|at|ch|uk))"
    r"(?![A-Za-z0-9-])")


def _labels_of(raw: str) -> list:
    return [x.strip(" \u00a0.") for x in raw.split(".") if x.strip(" \u00a0.")]


def _domain_fix(line: str, m) -> str:
    """Join-Entscheidung fuer eine moegliche zerrissene Domain.

    Drei harte Belege, einer muss vorliegen, sonst ist es Fliesstext:
      A) direkt vor dem Treffer steht ein @  ->  "@Anbieter. de"
      B) erstes Label ist ein Hostpraefix    ->  "www. google. de"
      C) erstes Label ist ein bekannter
         Marken-/Providername (DOMAIN_HINTS)  ->  "google. de"
    Zusaetzlich: gueltige Label-Form, echte TLD, kein Doppel punkt,
    kein Ein-Zeichen-Label („z. B. de" bleibt Prosa).
    """
    raw = m.group(1)
    labels = _labels_of(raw)
    if len(labels) < 2:
        return m.group(0)
    if any(not re.fullmatch(r"[A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df0-9-]{1,63}", x)
           for x in labels):
        return m.group(0)
    if labels[-1].lower() not in TLD:
        return m.group(0)
    if not all(re.search(r"[A-Za-z\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df]", x) for x in labels[:-1]):
        return m.group(0)                      # „1. de", „2. de" sind keine Domains
    first = labels[0].lower()
    if len(first) < 2:
        return m.group(0)                      # „z. B. de" -> Abkuerzung, keine Domain
    cue = (line[:m.start()].endswith("@") or first in {"www", "mail", "ftp", "m"}
           or first in DOMAIN_HINTS)
    if not cue:
        return m.group(0)
    return ".".join(labels)


def _fix_domains(line: str) -> tuple:
    """Zerrissene Domains wieder zusammenziehen (Regel H).

    Zaehlt nur echte Textaenderung – sonst blaeht sich die Korrekturzahl der
   Report auf und der Generator verliert sein Idempotenz-Versprechen.
    """
    out = RE_DOMAIN_FRAGMENT.sub(lambda m: _domain_fix(line, m), line)
    return out, (1 if out != line else 0)


RE_DBL_SPACE = re.compile(r"([^ \t])  +([^ \t])")
RE_LIST_MARKER = re.compile(r"^(\s*(?:[-*]|\d+\.))[ \u00a0]{2,}(\S)")


# --- Markenschutz gegen Regel D -------------------------------------------------
# Regel D ergaenzt ein Leerzeichen nach .!?  – das zerlegt AVMs Schreibweise
# „FRITZ!Box" zu „FRITZ! Box". Zwei Wachen, die sich gegenseitig rueckgaengig
# machen, sind teurer als jede Regel: die Marke wird daher VOR allen Regeln
# tokenisiert. Die Liste kommt aus dem gemeinsamen Casing-Lexikon
# (tag_casing.BRANDS) – neue Marken mit Sonderzeichen sind automatisch drin.
def _bang_brands() -> list:
    try:
        vals = {v for v in _tc.BRANDS.values() if "!" in v}
    except Exception:                          # pragma: no cover
        vals = set()
    vals |= {"FRITZ!Box", "FRITZ!Fon", "FRITZ!OS", "FRITZ!DECT",
             "FRITZ!Repeater", "FRITZ!Powerline", "Yahoo!"}
    return sorted(vals, key=len, reverse=True)


BANG_BRANDS = _bang_brands()
BANG_RE = re.compile("|".join(
    re.escape(b).replace("\\!", r"\s*!\s*") for b in BANG_BRANDS), re.I) \
    if BANG_BRANDS else None


def _mask_bang(line: str) -> tuple[str, list]:
    """Marken mit Ausrufezeichen aus dem Regel-Text herausnehmen."""
    if not BANG_RE or "!" not in line:
        return line, []
    held = []

    def put(m):
        held.append(m.group(0))
        return f"§BANG{len(held) - 1}§"
    return BANG_RE.sub(put, line), held


def _unmask_bang(line: str, held: list) -> str:
    for i, val in enumerate(held):
        line = line.replace(f"§BANG{i}§", val)
    return line


# Ganze Hostnamen muessen vor Regel D sicher sein: Regel D ergaenzt nach jedem
# Punkt ein Leerzeichen („Satz.Neuer“ -> „Satz. Neuer“) und zerstoert damit genau
# das, was Regel H eben zusammengesetzt hat („www.google.de“ -> „www. google. de“).
# Ohne diese Maske heilen sich die zwei Regeln gegenseitig auf – der Fehler, der
# im Bestand sechs mal sichtbar war.
RE_DOMAIN_SAFE = re.compile(
    r"(?<![\w./-])(?:[A-Za-z0-9\u00c4\u00d6\u00dc\u00e4\u00f6\u00fc\u00df-]{1,63}\.){1,4}"
    r"(?:" + "|".join(TLD) + r")(?![A-Za-z0-9-])")


def _mask_domains(line: str) -> tuple[str, list]:
    held = []

    def put(m):
        held.append(m.group(0))
        return f"§DOM{len(held) - 1}§"
    return RE_DOMAIN_SAFE.sub(put, line), held


def _unmask_domains(line: str, held: list) -> str:
    for i, val in enumerate(held):
        line = line.replace(f"§DOM{i}§", val)
    return line


def _is_protected(line: str) -> bool:
    """Zeilen, die nie angefasst werden: Tabelle, Code, Zitat, URL-only."""
    return "|" in line or "`" in line or line.lstrip().startswith((">", "```"))


# URL-Maske: matcht http(s)-URLs (auch mit internen Leerzeichen durch
# fruehere Fehllauefe) – wird vor den Leerzeichen-Regeln maskiert, damit
# NIE wieder Leerzeichen in URLs eingefuegt/veraendert werden.
RE_URL = re.compile(r"https?://[^\s)\]\}]+(?:\s+[^\s)\]\}]+)*")


def _mask_urls(line: str) -> tuple[str, list[tuple[str, str]]]:
    """Ersetzt URLs durch eindeutige Token (§URL0§, §URL1§, …).
    Die Token enthalten keine Leerzeichen/Punkte → werden von keiner
    Leerzeichen-Regel veraendert und koennen danach sicher zurueck-
    ersetzt werden (positionsunabhaengig)."""
    urls = []
    def _repl(m):
        tok = f"§URL{len(urls)}§"
        urls.append((tok, m.group(0)))
        return tok
    return RE_URL.sub(_repl, line), urls


def fix_line(line: str) -> tuple[str, int]:
    """Wendet alle Leerzeichen-Regeln auf EINE Zeile an."""
    if _is_protected(line):
        return line, 0
    changed = 0
    orig = line
    line, bang = _mask_bang(line)

    # H) Zerrissene Domains zuerst: fuellt „www. google. de" zurueck auf
    #    „www.google.de" und entzieht damit Regel D die Grundlage.
    line, n = _fix_domains(line)
    changed += n
    line, doms = _mask_domains(line)

    # G) „z.B.“ → „z. B.“ (Abkürzung sauber schreiben) – VOR Regel D,
    #    damit die Abkürzungs-Maskierung die neue Form korrekt schützt.
    line, n = re.subn(r"([zZ])\.B\.", r"\1. B.", line)
    changed += n

    # B) Listen-Marker normalisieren (3+ Spaces nach Marker → 1)
    line, n = RE_LIST_MARKER.subn(lambda m: m.group(1) + " " + m.group(2), line)
    changed += n

    # C) Leerzeichen vor Satzzeichen entfernen
    line, n = RE_SPACE_BEFORE_PUNCT.subn(lambda m: m.group(1), line)
    changed += n

    # A) Doppelte Leerzeichen mittendrin → 1 (Zeilenende = Hard-Break bleibt!)
    def _dbl(m):
        return m.group(1) + " " + m.group(2)
    line, n = RE_DBL_SPACE.subn(_dbl, line)
    changed += n

    # E) Fehlendes Leerzeichen nach Komma (nicht bei Dezimalzahlen)
    def _comma(m):
        return m.group(1) + ", " + m.group(2)
    # Dezimalzahlen temporär maskieren
    masked = RE_COMMA_NUMBER.sub(lambda m: m.group(0).replace(",", "§§"), line)
    line2, n = RE_MISSING_AFTER_COMMA.subn(_comma, masked)
    if n:
        line = line2.replace("§§", ",")
        changed += n

    # D) Fehlendes Leerzeichen nach .!? (Abkürzungen schützen)
    def _punct(m):
        return m.group(1) + m.group(2) + " " + m.group(3)
    # Abkürzungen temporär maskieren (Punkt durch Platzhalter ersetzen)
    def _mask_abk(m):
        return m.group(0).replace(".", "§")
    masked2 = ABK_RE.sub(_mask_abk, line)
    masked2 = RE_INWORD_BANG.sub("§EX§", masked2)     # FRITZ!Box-Angriffsschutz
    line3, n = RE_MISSING_AFTER_PUNCT.subn(_punct, masked2)
    if n:
        line = line3.replace("§EX§", "!").replace("§", ".")
        changed += n

    # F) Geschütztes Leerzeichen zwischen Zahl und %/€ sicherstellen
    line, n = re.subn(r"(\d)[ \u00a0]+([%€])", lambda m: m.group(1) + NBSP + m.group(2), line)
    changed += n

    line = _unmask_domains(line, doms)
    line = _unmask_bang(line, bang)
    # URLs unveraendert wiederherstellen (Platzhalter zurueck)
    # (fix_line arbeitet auf maskierter Zeile – wir maskieren hier erneut,
    # damit die Regeln URLs nie anfassen koennen.)
    return line, changed


def fix_line_safe(line: str) -> tuple[str, int]:
    """fix_line mit URL-Maskierung (URLs werden nie veraendert)."""
    masked, urls = _mask_urls(line)
    out, n = fix_line(masked)
    for tok, u in urls:
        out = out.replace(tok, u)
    return out, n


def fix_body(body: str) -> tuple[str, int]:
    """Wendet die Leerzeichen-Regeln auf den Body an."""
    lines = body.split("\n")
    out: list[str] = []
    changed = 0
    for line in lines:
        if "|" in line:
            # TABELLENZEILEN: Nur die sicheren Regeln anwenden – nbsp
            # zwischen Zahl und %/€ sowie „z.B.“ → „z. B.“. Alle anderen
            # Regeln (Leerzeichen-Kollaps etc.) würden Tabellen-Spacing
            # zerstören. URLs bleiben maskiert.
            masked, urls = _mask_urls(line)
            new = re.sub(r"(\d)[ \u00a0]+([%€])",
                         lambda m: m.group(1) + NBSP + m.group(2), masked)
            new = re.sub(r"([zZ])\.B\.", r"\1. B.", new)
            for tok, u in urls:
                new = new.replace(tok, u)
            if new != line:
                changed += 1
            out.append(new)
            continue
        new_line, n = fix_line_safe(line)
        out.append(new_line)
        changed += n
    return "\n".join(out), changed


def main() -> int:
    dry = "--dry-run" in sys.argv
    files = (sorted(glob.glob(f"{BLOG_DIR}/content/posts/*/index.md"))
             + sorted(glob.glob(f"{BLOG_DIR}/content/pillar/*/index.md")))
    total = 0
    for f in files:
        content = open(f, encoding="utf-8").read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        new_body, n = fix_body(parts[2])
        if n:
            total += n
            print(f"  {f.split('/')[-2]}: {n} Korrektur(en)")
            if not dry:
                open(f, "w", encoding="utf-8").write(parts[0] + "---" + parts[1] + "---" + new_body)
    print(f"\n{'DRY-RUN: ' if dry else ''}Leerzeichen-Generator: {total} Korrekturen in {len(files)} Dateien.")
    if not dry:
        try:
            from audit_log import log_event
            log_event(module="fix_spaces", action="apply",
                      input={"files": len(files)}, output={"fixes": total},
                      status="ok" if total >= 0 else "error")
        except Exception:
            pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
