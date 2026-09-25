#!/usr/bin/env python3
"""Sprachkern – gemeinsame Offline-Basis der Sprach-Politur OHNE API.

Auftrag (Frank, 25.09.2026): „Sämtliche Blogartikel dauerhaft automatisch mit
DeepL Write oder LanguageTool glätten (KOSTENLOS, OHNE API nachbauen) und auf
Premium-Level einer Profi-Agentur beheben."

Dieser Kern ist der geteilte, netzfreie Teil der beiden Engines:
  - scripts/grammar_check.py  – LanguageTool-Nachbau (Korrektur-Ebene)
  - scripts/sprachglatt.py    – DeepL-Write-Nachbau (Glätt-Ebene)

Er liefert NUR Mechanik – Schutzzonen, Case-Erhalt, Regel-Executor,
Artikel-Lauf. Die REGELN liegen bewusst genau einmal, je in der Engine,
die sie besitzt (Qualitäts-Regelwerk: „Jede Lektorats-Regel genau einmal").

Sicherheitsverträge (gelten für BEIDE Engines):
  - Schutzzonen: Code-Blöcke, Inline-Code, Markdown-Links/-Bilder inkl.
    Linkziel, Shortcodes, URLs, HTML-Tags/Kommentare werden maskiert und
    NIE verändert (auch Link-TEXTE nicht – sie sind Marken-/Anker-Verträge).
  - Frontmatter: title wird nie geschrieben (Cover-Marken-Lock, check_covers),
    description wird nur über die sichere Regelschicht geheilt.
  - Verifikation vor dem Schreiben: Link-/Shortcode-/Überschriften-Zahl
    konstant, Wortzahl ≥ 90 % – sonst wird die Datei NICHT geschrieben.
  - Selbsttest vor JEDEM Schreibvorgang; Abweichung = Exit 2, kein Schreiben.
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from post_utils import list_post_paths, join_article  # noqa: E402

# ---------------------------------------------------------------- Schutzzonen
PROTECT_RX = re.compile(
    r"(```.*?```"                # Code-Block
    r"|`[^`\n]+`"                # Inline-Code
    r"|\{\{[<%].*?[>%]\}\}"      # Hugo-Shortcodes
    r"|!?\[[^\]]*\]\([^)]*\)"    # MD-Links & Bilder inkl. Ziel (Text = Anker-Vertrag!)
    r"|https?://\S+"             # URLs
    r"|<!--.*?-->"               # HTML-Kommentare
    r"|<[^>\n]+>"                # HTML-Tags
    r")", re.S)

_SENT_TRAP = re.compile(r"(?:\d{1,2}\.){1,3}\s*$")


def protect_zones(text: str):
    """Maskiert Schutzzonen durch Platzhalter. Rückgabe: (maskiert, Originale)."""
    origs = []

    def repl(m):
        origs.append(m.group(0))
        return f"\x00Z{len(origs) - 1}\x00"

    return PROTECT_RX.sub(repl, text), origs


def unprotect(text: str, origs: list) -> str:
    for i, o in enumerate(origs):
        text = text.replace(f"\x00Z{i}\x00", o)
    return text


def case_match(src: str, canon: str) -> str:
    """Übernimmt die Anfangsgroßschreibung des Fundwortes auf den Kanon."""
    if src[:1].isupper():
        return canon[:1].upper() + canon[1:]
    return canon


# ------------------------------------------------------------ Regel-Executor
# Regel = (ID, Regex, Fixer, Label)
#   Fixer: Callable[Match -> str]  = Auto-Fix (100 % sicher)
#          None                    = NUR Report (Vorschlagsschicht)

def scan_rules(text: str, rules) -> list:
    """Liefert Funde (dicts) ohne zu schreiben. Identity-Fixe (fix == found)
    sind Falsch-Alarme und werden verworfen (Sicherheitsnetz für alle Engines)."""
    body, _ = protect_zones(text)
    out = []
    for rid, rx, fixer, label in rules:
        for m in rx.finditer(body):
            fix = fixer(m) if fixer else None
            if fixer is not None and fix == m.group(0):
                continue
            ctx = body[max(0, m.start() - 36): m.end() + 36].replace("\n", " ").strip()
            out.append({
                "rule": rid, "found": m.group(0), "fix": fix,
                "label": label, "ctx": ctx,
            })
    return out


def apply_rules(text: str, rules):
    """Führt Auto-Fixes aus, bewahrt Schutzzonen. Rückgabe: (text, n_fixes, funde)."""
    body, origs = protect_zones(text)
    n = 0
    funde = []
    for rid, rx, fixer, label in rules:
        if fixer is None:
            continue
        def _safe_sub(m, _fixer=fixer):
            ersatz = _fixer(m)
            return m.group(0) if ersatz == m.group(0) else ersatz
        found = [m for m in rx.finditer(body) if fixer(m) != m.group(0)]
        if not found:
            continue
        for m in found:
            funde.append({
                "rule": rid, "found": m.group(0), "fix": fixer(m),
                "label": label,
                "ctx": body[max(0, m.start() - 36): m.end() + 36]
                       .replace("\n", " ").strip(),
            })
        body, _k = rx.subn(_safe_sub, body)
        n += len(found)
    return unprotect(body, origs), n, funde


# ------------------------------------------------------------ Artikel-Lauf
def load_articles(files=None, new_only=False, include_drafts=False):
    """Lädt Posts (Bundle + Legacy). new_only: Frontmatter-Datum ODER Slug = heute."""
    today = datetime.now(timezone.utc).date().isoformat()
    arts = []
    paths = files or list_post_paths()
    for path in paths:
        with open(path, encoding="utf-8") as fh:
            content = fh.read()
        parts = content.split("---", 2)
        if len(parts) < 3:
            continue
        fm, body = parts[1], parts[2]
        if not include_drafts and "draft: true" in fm:
            continue

        def get(key, _fm=fm):
            m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", _fm, re.M)
            return m.group(1).strip() if m else ""

        if new_only:
            in_slug = today in os.path.basename(os.path.dirname(path)) \
                or today in os.path.basename(path)
            if not (in_slug or get("date").startswith(today)):
                continue
        arts.append({
            "path": path,
            "slug": (os.path.basename(os.path.dirname(path))
                     if os.path.basename(path) == "index.md"
                     else os.path.basename(path)[:-3]),
            "title": get("title"), "description": get("description"),
            "fm": fm, "body": body, "content": content, "prefix": parts[0],
        })
    return arts


def link_count(text: str) -> int:
    return len(re.findall(r"\[[^\]]*\]\([^)]*\)", text))


def shortcode_count(text: str) -> int:
    return len(re.findall(r"\{\{[<%].*?[>%]\}\}", text))


def heading_count(text: str) -> int:
    return len(re.findall(r"(?m)^#{1,6}\s", text))


def words(text: str) -> int:
    return len(re.findall(r"\w+", text, re.UNICODE))


def write_verified(a: dict, new_content: str, engine: str) -> tuple[bool, str]:
    """Verifikation VOR dem Schreiben (Repo-Vertrag). Rückgabe: (geschrieben, Grund)."""
    old, new = a["content"], new_content
    if link_count(old) != link_count(new):
        return False, "Link-Zahl verändert"
    if shortcode_count(old) != shortcode_count(new):
        return False, "Shortcode-Zahl verändert"
    if heading_count(old) != heading_count(new):
        return False, "Überschriften-Zahl verändert"
    if words(new) < 0.90 * words(old):
        return False, "Wortzahl unter 90 % des Originals"
    with open(a["path"], "w", encoding="utf-8") as fh:
        fh.write(new)
    return True, "ok"


def rebuild(a: dict, new_body: str, new_description: str | None = None) -> str:
    """Setzt die Datei FM-sicher aus Teilen zusammen (Kanon-Naht via post_utils)."""
    fm = a["fm"]
    if new_description is not None:
        fm2 = re.sub(r"(?m)^description:\s*[\"']?.+?[\"']?\s*$",
                     'description: "' + new_description.replace('"', "'") + '"',
                     fm, count=1)
        if fm2 == fm and new_description:
            fm2 = fm.rstrip("\n") + '\ndescription: "' + new_description.replace('"', "'") + '"\n'
        fm = fm2
    return join_article(fm, new_body, a["prefix"])


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M")
