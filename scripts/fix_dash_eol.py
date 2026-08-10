#!/usr/bin/env python3
"""Gedankenstrich-am-Zeilenende-Korrektur (deterministisch, selbstheilend)
für FranksFinanzcheck.

Hintergrund (User-Meldung Flug-Artikel):
    „…In der Flugsuche „flexible Daten" oder „±3 Tage" wählen –  [Umbruch]
     viele Portale zeigen dir die günstigsten Tage im Monatskalender."
Der Gedankenstrich am ZEILENENDE (mit/ohne trailing spaces → <br>) vor einem
NEUEN Hauptsatz ist ein Stilfehler: Nach einem Punkt gehört ein neuer Satz,
der Gedankenstrich ist dort redundant. Deterministische Regeln:

  MODUS A – Definitions-Listen (Lead-Definition) zurückbauen:
      Zeile (oder Vorgängerzeile) beginnt mit „**Titel:**" (RE_LEAD) und
      endet mit Gedankenstrich → Folgezeile wird angehängt, KEIN Punkt
      (die Definition ist eine Einheit – siehe Commit 63f809c).
      Beispiel: „**Wochenend-Ski-Trips:** … mieten –\n der Wochenend-Tarif…"
                → „**Wochenend-Ski-Trips:** … mieten – der Wochenend-Tarif…"

  MODUS B – Neuer Hauptsatz nach Zeilenende-Gedankenstrich:
      Zeile endet mit „–"/„—" (+ trailing spaces) und die FOLGEZEILE beginnt
      mit einem Wort, das einen NEUEN Hauptsatz einleitet → Gedankenstrich
      wird zum Punkt, erstes Wort der Folgezeile großgeschrieben, Zeilen
      zusammengefügt.
      Beispiel: „…wählen –\n viele Portale…" → „…wählen. Viele Portale…"

  SICHERHEIT (konservativ):
    - Relativ-/Nebensatz-Einleiter (wer, was, wenn, weil, wobei, …) und
      Präpositionen/Konjunktionen → KEIN Fix (Nachtrag/Apposition bleibt).
    - „der/die/das" + finites Verb an Position 2 → KEIN Fix (Relativ-Verdacht,
      z. B. „…Garantie – die entscheidet, wie viel Ökostrom…").
    - „der/die/das/den/dem" + Subjekt an Position 2 + finites Verb → Fix
      (Hauptsatz: „der Unterschied ist…", „die Zinsen werden…").
    - Ellipsen ohne finites Verb („die Umsetzung entscheidend.",
      „eine gebührenpflichtige aber nicht.") → KEIN Fix.
    - Schutzkontexte: Code, Listen, Tabellen, Blockquotes, Überschriften,
      FAQ, unbalancierte Klammern.

Nutzung:
  python3 scripts/fix_dash_eol.py            # nur melden (Exit 0/1)
  python3 scripts/fix_dash_eol.py --fix      # korrigieren
  python3 scripts/fix_dash_eol.py --json     # JSON-Output

Exit: 0 = ok · 1 = offene Funde
"""
import os
import re
import sys
import json
import glob

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

DASH = "[\u2013\u2014]"
RE_EOL_DASH = re.compile(r"[ \t]*" + DASH + r"[ \t]*$")

# Definitions-Listen-Muster (identisch zu fix_linebreaks.py)
RE_LEAD = re.compile(r"^\s*(?:[-*]\s+)?\*\*[^*]+:\*\*")

# --- Wörter, die IMMER einen neuen Hauptsatz einleiten können ------------
SAFE_STARTERS = {
    "viele", "manche", "einige", "zahlreiche", "mehrere", "alle", "beide",
    "es", "so", "dann", "dort", "hier",
    "mein", "meine", "meinen", "dein", "deine", "deinen",
    "sein", "seine", "seinen", "ihr", "ihre", "ihren", "unser", "unsere",
    "euer", "eure", "man", "niemand", "jemand", "jeder", "jede", "jedes",
    "alles", "etwas", "nichts", "oft", "meist", "meistens", "häufig",
    "selten", "manchmal", "heute", "morgen", "gestern", "bald", "immer",
    "regelmäßig", "automatisch", "übrigens", "endlich", "wirklich",
    "tatsächlich", "offenbar", "anscheinend", "leider", "hoffentlich",
    "sicherlich", "vermutlich", "wahrscheinlich", "völlig", "einfach",
    "genauso", "ebenso", "deshalb", "deswegen", "trotzdem", "dennoch",
    "allerdings", "jedoch", "zudem", "außerdem", "dazu", "dafür", "damit",
    "danach", "vorher", "nachher", "inzwischen", "mittlerweile",
    "mittendrin", "unterdessen", "gleichzeitig", "parallel", "zusätzlich",
}

# Konzessiv-/Konsekutiv-Einleitung am Zeilenanfang: „So sehr ich den Kauf
# empfehle – es gibt Situationen…" → der Gedankenstrich verbindet einen
# unvollständigen Vordersatz mit dem Hauptsatz; hier NUR den Umbruch
# zusammenfügen (KEIN Punkt). Muster: „So sehr/viel/gut/wenig/oft/…"
RE_KONZESSIV = re.compile(
    r"^So\s+(?:sehr|viel|gut|wenig|oft|schnell|gern|gerne|lange|spät|"
    r"spaet|früh|frueh)\b", re.IGNORECASE)

# Relativ-/Nebensatz-/Nachtrags-Einleiter → NIE anfassen
RELATIV_EINLEITER = {
    "wer", "was", "wen", "wem", "wessen", "wobei", "wodurch", "worin",
    "wovon", "womit", "worüber", "wozu", "wofür", "wogegen", "woher",
    "wohin", "wann", "wie", "als", "ob", "wenn", "weil", "dass", "damit",
    "um", "ohne", "statt", "außer", "sofern", "falls", "indem", "nachdem",
    "während", "seitdem", "sobald", "solange", "weder", "noch", "entweder",
    "je", "desto", "umso", "zwar", "hingegen", "dagegen", "stattdessen",
    "einerseits", "andererseits", "überdies", "folglich", "nämlich",
    "in", "mit", "von", "für", "auf", "an", "bei", "nach", "aus", "zu",
    "über", "unter", "vor", "hinter", "neben", "zwischen", "gegen", "seit",
    "bis", "ab", "dank", "trotz", "laut", "wegen", "zwecks", "inklusive",
    "exklusive", "pro", "plus", "minus", "genau", "gerade", "nur", "auch",
    "sogar", "erst", "noch", "schon", "bereits", "kaum", "fast", "beinahe",
    "mehr", "weniger", "weiter", "weiterhin", "wieder", "zurück",
}

# Artikel/Demonstrativa mit Sonderbehandlung (Verb-Positions-Heuristik)
ARTIKEL_DEM = {"der", "die", "das", "den", "dem", "dessen", "deren",
               "ein", "eine", "einer", "einem", "einen"}

# Häufige finite Verbformen (für Hauptsatz-/Ellipsen-Heuristik)
FINITE_VERBEN = {
    "ist", "sind", "war", "waren", "wird", "werden", "wurde", "wurden",
    "hat", "haben", "hatte", "hatten", "kann", "können", "konnte", "konnten",
    "muss", "müssen", "musste", "mussten", "will", "wollen", "wollte",
    "wollten", "soll", "sollen", "sollte", "sollten", "darf", "dürfen",
    "durfte", "durften", "mag", "möchte", "möchten", "liegt", "liegen",
    "lag", "lagen", "steht", "stehen", "stand", "standen", "gibt", "gab",
    "geht", "gehen", "ging", "gingen", "kommt", "kommen", "kam", "kamen",
    "kostet", "kosten", "kostete", "kosteten", "spart", "sparen", "sparst",
    "zeigt", "zeigen", "zeigte", "zeigten", "lohnt", "lohnen", "lohnte",
    "zahlt", "zahlen", "zahlst", "zahlte", "zahlten", "braucht", "brauchen",
    "brauchte", "brauchten", "fällt", "fallen", "fiel", "fielen", "bleibt",
    "bleiben", "blieb", "blieben", "macht", "machen", "machte", "machten",
    "tut", "tun", "tat", "taten", "weiß", "wissen", "wusste", "wussten",
    "sieht", "sehen", "sah", "sahen", "heißt", "heißen", "hieß", "rechnet",
    "rechnen", "rechnete", "rechneten", "entscheidet", "entscheiden",
    "entschied", "entschieden", "beginnt", "beginnen", "begann", "begannen",
    "endet", "enden", "endete", "endeten", "läuft", "laufen", "lief",
    "liefen", "fährt", "fahren", "fuhr", "fuhren", "fliegt", "fliegen",
    "flog", "flogen", "übernimmt", "übernehmen", "übernahm", "übernahmen",
    "setzt", "setzen", "setzte", "setzten", "ansetzt", "ansetzen",
    "holt", "holen", "holte", "holten", "schützt", "schützen", "schützte",
    "wohnt", "wohnen", "wohnte", "wohnten", "kennt", "kennen", "kannte",
    "kannten", "vergisst", "vergessen", "vergaß", "hilft", "helfen",
    "half", "halfen", "entfällt", "entfallen", "entfiel", "entfielen",
    "reicht", "reichen", "reichte", "reichten", "startet", "starten",
    "startete", "starteten", "arbeitet", "arbeiten", "arbeitete",
    "arbeiteten", "zahlt", "verdient", "verdienen", "verdiente",
    "verdienten", "steigt", "steigen", "stieg", "stiegen", "sinkt",
    "sinken", "sank", "sanken", "bleibt", "spart", "lohnt", "gilt",
    "gelten", "galt", "galten", "bedeutet", "bedeuten", "bedeutete",
    "bedeuteten", "scheint", "scheinen", "schien", "schienen", "dürfte",
    "könnte", "würde", "würden", "hätte", "hätten", "wäre", "wären",
    "fehlt", "fehlen", "fehlte", "fehlten", "reicht", "reichen",
    "bepreisen", "bepreist", "bündelt", "bündeln", "weisen", "weist",
    "funktioniert", "funktionieren", "funktionierte", "funktionierten",
    "bringt", "bringen", "brachte", "brachten", "nimmt", "nehmen", "nahm",
    "nahmen", "gibt", "handelt", "handeln", "handelte", "handelten",
    "rechnet", "lohnt", "rentiert", "rentieren", "spart", "kostet",
    "unterscheidet", "unterscheiden", "unterschied", "unterschieden",
    "erklärt", "erklären", "erklärte", "erklärten", "gilt", "gilt",
    "bildet", "bilden", "bildete", "bildeten", "folgt", "folgen", "folgte",
    "folgten", "zählt", "zählen", "zählte", "zählten", "spielt", "spielen",
    "spielte", "spielten", "wirkt", "wirken", "wirkte", "wirkten",
    "verschwindet", "verschwinden", "verschwand", "verschwunden",
    "ändert", "ändern", "änderte", "änderten", "wartet", "warten",
    "wartete", "warteten", "wartet", "erwartet", "erwarten", "erwartete",
}


def _is_protected(line: str) -> bool:
    """Technisch geschützte Zeilen (nie anfassen)."""
    if "|" in line or "`" in line:
        return True
    if line.lstrip().startswith((">", "```")):
        return True
    if re.match(r"^\s*(?:[-*]|\d+\.)\s+", line):
        return True
    if line.lstrip().startswith("#"):
        return True
    return False


def _unbalanced_paren(line: str) -> bool:
    """True, wenn die Zeile unbalancierte Klammern enthält (Schutz)."""
    return line.count("(") != line.count(")")


def _has_finite_verb(text: str) -> bool:
    words = re.findall(r"[A-Za-zÄÖÜäöüß-]+", text.lower())
    return any(w in FINITE_VERBEN for w in words)


def _norm_word(w: str) -> str:
    """Normalisiert ein Wort für Listenvergleiche (Interpunktion abtrennen)."""
    return w.strip("„“”\"'(),.;:!?…-–—").lower()


def _is_article_dem_hauptsatz(first_word: str, rest_words: list[str]) -> bool:
    """Sonderregel für der/die/das/den/dem/ein/eine/…:
    Hauptsatz, wenn Position 2 ein Subjekt (kein Verb, nicht 'sich') ist und
    ein finites Verb in den ersten ~6 Wörtern folgt. Ist Position 2 selbst
    ein Verb, gilt: Relativ-Verdacht nur, wenn direkt danach ein Komma mit
    Nebensatz-Einleiter folgt („die entscheidet, wie…"); sonst Demonstrativ
    → Hauptsatz („das ist normal…", „das übernimmt der Anbieter…")."""
    if not rest_words:
        return False
    w2 = _norm_word(rest_words[0])
    if w2 == "sich":
        return False  # Relativ („der sich … rechnet")
    if w2 in FINITE_VERBEN:
        rest_text = " ".join(rest_words[0:6])
        if re.match(
            r"^[^,]*,\s*(?:wie|was|wer|wen|wem|wann|wo|wohin|woher|ob|dass|"
            r"weil|wenn|als|wobei|wodurch|worin|wovon|womit|wozu)\b",
            rest_text,
        ):
            return False  # Relativsatz („…, die entscheidet, wie viel…")
        return True  # Demonstrativ → neuer Hauptsatz
    probe = " ".join(_norm_word(w) for w in rest_words[:6])
    return _has_finite_verb(probe)


def classify_followup(first_word: str, follow_line: str) -> bool:
    """Entscheidet, ob die Folgezeile einen NEUEN Hauptsatz beginnt
    (True = Fix mit Punkt + Großschreibung)."""
    w = first_word.lower()
    if w in SAFE_STARTERS:
        return True
    if w in RELATIV_EINLEITER or w in ARTIKEL_DEM:
        if w in ARTIKEL_DEM:
            rest = re.findall(r"[^\s]+", follow_line)[1:]
            return _is_article_dem_hauptsatz(w, rest)
        return False
    return False  # unbekannt → konservativ kein Fix


def scan_file(path: str, fix: bool = False) -> dict:
    """Scannt eine Datei; bei fix=True wird die Datei neu geschrieben.

    Die Ausgabe wird Zeile für Zeile aufgebaut (Rebuild). Bei einem Fix
    wird die zusammengeführte Zeile angehängt und die Folgezeile per
    Index-Sprung übersprungen – kein del auf einer Kopie, dadurch bleiben
    die Zeilen-Zuordnungen bei mehreren Fixes pro Datei korrekt.
    """
    with open(path, encoding="utf-8") as f:
        content = f.read()
    lines = content.split("\n")
    findings = []
    in_code = False
    in_faq = False
    out = []
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            out.append(line)
            i += 1
            continue
        if in_code:
            out.append(line)
            i += 1
            continue
        if re.match(r"^#{1,6}\s+", line):
            if re.match(r"^#{1,2}\s+(?:FAQ|Häufige Fragen|Fragen)", line):
                in_faq = True
            elif re.match(r"^#{1,2}\s+", line):
                in_faq = False
            out.append(line)
            i += 1
            continue
        if in_faq or _is_protected(line):
            out.append(line)
            i += 1
            continue
        if not RE_EOL_DASH.search(line):
            out.append(line)
            i += 1
            continue
        if _unbalanced_paren(line) or _unbalanced_paren(lines[i + 1] if i + 1 < len(lines) else ""):
            out.append(line)
            i += 1
            continue  # Klammer-Kontext → schützen
        nxt = lines[i + 1].strip() if i + 1 < len(lines) else ""
        if not nxt or nxt.startswith(("#", ">", "|", "-", "*", "`", "```")):
            out.append(line)
            i += 1
            continue
        # Definitions-Liste (Modus A): Zeile oder die Zeilen-KETTE davor
        # (ohne Leerzeilen-Unterbrechung = gleicher Absatz) beginnt mit
        # „**Titel:**". Eine Leerzeile dazwischen bedeutet: neuer Absatz,
        # die **-Zeile gehört zu einem ANDEREN Absatz → kein Modus A.
        lead_in_chain = RE_LEAD.match(line)
        if not lead_in_chain:
            j = i - 1
            while j >= 0 and lines[j].strip():
                if RE_LEAD.match(lines[j]):
                    lead_in_chain = True
                    break
                j -= 1
        if lead_in_chain:
            if fix:
                out.append(line.rstrip() + " " + nxt)
                i += 2  # Folgezeile ist in der zusammengeführten Zeile
            else:
                out.append(line)
                i += 1
            findings.append({"rule": "A", "mode": "lead-definition",
                             "line": line.strip()[:80]})
            continue
        # Modus B: neuer Hauptsatz?
        m = re.match(r"^([^\s]+)", nxt)
        if not m:
            out.append(line)
            i += 1
            continue
        first_word = m.group(1)
        is_hauptsatz = classify_followup(first_word, nxt)
        if not is_hauptsatz:
            out.append(line)
            i += 1
            continue
        # Modus C: Konzessiv-Vordersatz („So sehr ich den Kauf empfehle – …")
        # → nur Umbruch zusammenfügen, Gedankenstrich behalten (kein Punkt)
        if RE_KONZESSIV.match(line):
            if fix:
                out.append(line.rstrip() + " " + nxt)
                i += 2
            else:
                out.append(line)
                i += 1
            findings.append({"rule": "C", "mode": "konzessiv",
                             "line": line.strip()[:80]})
            continue
        if fix:
            # Gedankenstrich (inkl. Leerzeichen davor) → Punkt, erstes Wort
            # großschreiben, zusammenfügen
            base = re.sub(r"[ \t]*" + DASH + r"[ \t]*$", ".", line.rstrip())
            new_word = first_word[0].upper() + first_word[1:]
            rest = nxt[len(first_word):].lstrip()
            out.append(base + " " + new_word + (" " + rest if rest else ""))
            i += 2
        else:
            out.append(line)
            i += 1
        findings.append({"rule": "B", "mode": "hauptsatz",
                         "line": line.strip()[:80]})
    new_content = "\n".join(out)
    changed = new_content != content
    if fix and changed:
        with open(path, "w", encoding="utf-8") as f:
            f.write(new_content)
    return {"file": path, "findings": findings, "changed": changed}


def main():
    fix = "--fix" in sys.argv
    as_json = "--json" in sys.argv
    total = 0
    results = []
    for pattern in ("content/posts/*/index.md", "content/posts/*.md",
                    "content/pillar/*/index.md"):
        for path in sorted(glob.glob(os.path.join(BLOG_DIR, pattern))):
            r = scan_file(path, fix=fix)
            if r["findings"]:
                total += len(r["findings"])
                results.append(r)
                for f in r["findings"]:
                    slug = os.path.basename(os.path.dirname(path))
                    print(f"  {'✅' if fix else '❌'} [{f['rule']}] {slug}: "
                          f"{f['line']}")
    print(f"Gedankenstrich-EOL-Check: {total} Funde "
          f"(A: Definitions-Listen zurückgebaut, B: Hauptsatz→Punkt)")
    if fix and total:
        try:
            from audit_log import log_event
            log_event(module="fix_dash_eol", action="apply",
                      input={"files": len(results)}, output={"changes": total},
                      status="ok")
        except Exception:
            pass
    if as_json:
        print(json.dumps({"total": total, "fixed": fix, "items": results},
                         ensure_ascii=False))
    return 1 if (total and not fix) else 0


if __name__ == "__main__":
    sys.exit(main())
