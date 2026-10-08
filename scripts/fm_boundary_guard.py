#!/usr/bin/env python3
"""fm_boundary_guard.py – FM-GRENZEN-WACHE (Front-Matter-Boundary-Gate, 11.09.2026)

BAUURSACHE (Fr 11.09.2026 – main rot in den Runs 34594479696, 34597633413,
34598288171; zuletzt grün in Run 34587113270 auf abfc359):
  Ein Content-Engine-Artikel schrieb die pin_description mit dem
  UWG-Prefix „*Werbung | …“ UNQUOTIERT ins Frontmatter. In YAML beginnt mit
  „*“ ein Alias → der Wert ist kein gültiges Skalar mehr. Hugo bricht ab mit
      ERROR error building site: assemble: failed to create page from
      pageMetaSource …: invalid header option: " Der Traumurlaub …"
  Der Deploy stirbt nach Sekunden im Schritt „Build (für Publish-Gate +
  Publish)“ (hugo --minify, Exit 1). ALLE nachgelagerten Stufen (Spam-Gate,
  Publish-Gate, Anker-Wache, Vorlesen, Publish, Catchup) laufen dann nicht
  mehr – der Blog bleibt auf dem Stand vor dem Fehler stehen, die
  Publish-Kette (RSS → Pinterest) trocknet aus.

GRUNDSÄTZLICH: Frontmatter ist die einzige Fehlerklasse, die den Build HART
beendet – und sie entsteht genau dort, wo Engine und Heiler Werte ZEILENWEISE
schreiben (engine_generate.yaml_quote, pin_text_sync.fm_set, spam_guard,
Meta-/Cover-Heiler). Jeder Wert mit YAML-Indikator am Anfang („*Werbung“,
„&…“, „!!tag“, „- …“) oder mit „: “ im unquotierten Text ist ein potenzieller
Build-Abbruch.

PRÜFPRINZIP (bewusst anders als die Text-Wachen):
  1) Der ganze Frontmatter-BLOCK wird geparst (Hugo-Sicht). Parsbar = RUHE.
     → keine False Positives gegen legale Konstrukte wie
       tags: ["Energie-Update: was sich ändert", …]  (Liste mit Doppelpunkt)
  2) Fehlt die Grenze oben (F1) oder unten (F2), ist der Block nicht parbar
     (F3) oder unvollständig quotiert (F4) → Zeile wird lokalisiert.
  3) GEHEILT wird nur, was nachweislich besser ist: Wert in doppelte
     YAML-Guillemets („\\“ und „"“ escaped), Block NOCHMAL geparst. Parsen
     fehlschlug und die Heilung nichts bringt → nichts wird geschrieben
     (kein Schema-Eingriff, kein Content-Verlust – eine Liste darf durch
     eine Heilung NIEMALS zu einem String werden).
  Ohne PyYAML arbeitet die Wache deterministisch nach Regelkanon (F5), heilt
  aber nur die eindeutig gefahrlosen Fälle.

DOPPELTE MAPPING-SCHLÜSSEL (F7 – die Klasse, die PyYAML nicht sieht, 08.10.2026):
  Am 08.10.2026 starb der Produktions-Build zweimal an derselben Zeile:
      ERROR error building site: assemble: failed to create page from
      pageMetaSource /posts/2026-10-07-campingurlaub-…:
      "…/index.md:9:1": [8:1] mapping key "tags" already defined at [7:1]
  Fünf Reserve-Entwürfe trugen ein zweites `tags:` (einer zusätzlich ein
  zweites `cover.image:`) – entstanden beim Zusammenführen zweier Fassungen,
  in denen beide Seiten ihre eigene Schlüsselzeile behielten.
  Die Tücke: **PyYAML parst doppelte Schlüssel still** (der letzte gewinnt),
  Hugo (go-yaml) bricht hart ab. Damit war die Grundannahme dieser Wache
  („Parsbar = RUHE“) für genau diese Klasse FALSCH: FM-Grenze, Taxonomie,
  Publish-Gate und Scorecard standen alle grün, während `hugo --minify` den
  kompletten Publish-Pfad mitnahm – ohne Report, ohne verwertbares Alert.
  F7 wird deshalb REGELBASIERT erkannt (Zeilenscan über die Mapping-Struktur,
  unabhängig von PyYAML) und deterministisch, verlustfrei geheilt:
    · Listen (Flow- wie Blockform) werden VEREINIGT – kein Element geht
      verloren, Dubletten fallen weg, Reihenfolge des ersten Vorkommens;
    · alles andere behält das LETZTE Vorkommen (YAML-Leseregel: genau der
      Wert, den jeder Leser bisher sah), das frühere wird entfernt und im
      Report namentlich belegt.
  Geschrieben wird nur, wenn danach (a) keine Doppelung mehr existiert und
  (b) der Block weiterhin parst – sonst bleibt die Datei unangetastet.

KLEBER (F6 – baukritisch seit 18.09.2026): Hugo schließt das Frontmatter an der
ERSTEN Zeile ab Index 1, die mit „---“ BEGINNT – auch wenn Text direkt
dahinterklebt („---Warum zahlen …“). Der geklebte Rest RENDERT als Body (im
Hugo-Labor gemessen: „---Text“ und „---\n\nText“ liefern identisches HTML; die
frühere Annahme „gehört nicht zum Body“ war falsch). Der Schaden liegt
woanders, und er ist belegt:

  · ZEILENWEISE lesende Wachen erkennen das FM-Ende an einer exakt
    alleinstehenden `---`-Zeile. Bleibt sie aus, gilt der ganze Artikel als
    Frontmatter und wird nie geprüft – grün, obwohl blind.
    Beweis: derselbe Verstoß („Preisgarantie Gas“) ergibt in `compound_guard`
    sauber 1 Fund, geklebt 0 Funde.
  · `park_state.set_field` liefert auf geklebten Dateien still `False`: die
    Re-Queue-Maschine kann einen maschinell geparkten Artikel nicht mehr
    markieren – er sieht danach wie ein menschlicher Entwurf aus und wird nie
    promotet. Genau daran hingen die vier Reserve-Entwürfe, die am 18.09. als
    „fm-grenze“-Blockierte feststeckten.
  · Produzenten waren real: `keyword_optimizer.py` (9 Dateien, Commit 6c772fd)
    und `redaktions_standard.py` (KI-Antwort samt Prompt-Gerüst, 7b51187).

Diese Wache heilt den Kleber jetzt selbst (Naht zerlegen, Prompt-Gerüst am
Anfang entfernen) – über `post_utils.heal_glued_close`, dieselbe Quelle, die
alle Schreiber über `post_utils.join_article` benutzen. Ohne `--fix` ist der
Kleber ein harter Befund (F6, Exit 1): Eine Klasse, die 13 Dateien befallen
und eine Live-Seite mit „TITEL:/ARTIKEL:“ versehen hat, darf nicht als
„Hinweis“ durchlaufen.

AUFRUF:
  python3 scripts/fm_boundary_guard.py --selftest   # Sabotage-Schutz, Exit 2
  python3 scripts/fm_boundary_guard.py --check      # melden, Exit 1 bei F1–F7
  python3 scripts/fm_boundary_guard.py --fix        # heilen (konvergent)
  python3 scripts/fm_boundary_guard.py --staged     # nur die GESTAGETEN
                                                    # Content-Blobs (Commit-Sperre)
  python3 scripts/fm_boundary_guard.py --wirkungsprobe  # Fixture-Beweis: F7
                                                    # erkannt, geheilt, konvergent
"""
import datetime
import os
import re
import subprocess
import sys
import tempfile

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# Die Naht-Logik ist EINE Wahrheit für Schreiber, Heiler und Prüfer
# (post_utils.join_article / split_article / heal_glued_close).
import post_utils  # noqa: E402

CONTENT_DIR = os.path.join(BLOG_DIR, "content")
REPORT = os.path.join(BLOG_DIR, "FM-GRENZEN-REPORT.md")

OPEN_RX = re.compile(r"^---[ \t]*$")
CLOSE_RX = re.compile(r"^---")            # Hugo: Schluss an „---…“ (Präfix)
TOP_KEY_RX = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*):[ \t]*(.*)$")
INDICATORS = ("*", "&", "!", "@", "`")

try:
    import yaml as _yaml                   # Gegenprüfung (im Deploy installiert)
except Exception:                          # pragma: no cover
    _yaml = None


# ------------------------------------------------------------------- Frontmatter
def content_files():
    """Alle Content-Quellen (posts, pillar, statische Seiten) – sortiert."""
    out = []
    for base, _dirs, names in os.walk(CONTENT_DIR):
        for name in names:
            if name.endswith((".md", ".markdown")):
                out.append(os.path.join(base, name))
    return sorted(out)


def split_fm(text):
    """(zeilen, beginn_idx, end_idx) des FM-Blocks – Hugo-Semantik.

    zeilen is None  → keine eigene ---Zeile am Dateianfang (F1)
    end_idx is None → Block nie geschlossen (F2)"""
    lines = text.split("\n")
    if not lines or not OPEN_RX.match(lines[0]):
        return None, None, None
    for i in range(1, len(lines)):
        if CLOSE_RX.match(lines[i]):
            return lines[1:i], 1, i
    return lines[1:], 1, None


def closing_glue(text):
    """Kleber-Rest der FM-Schlusszeile: '---Warum zahlen …' → 'Warum zahlen …'.

    Delegiert an die Naht-SSOT (`post_utils.glued_close`) – es gibt genau EINE
    Erkennung im Repo, damit Prüfer, Heiler und Schreiber nie auseinanderlaufen.
    """
    _i, rest = post_utils.glued_close(text)
    return rest.strip()


def parse_ok(block_text):
    """Block/Zeile als YAML: True/False, None = ohne PyYAML nicht prüfbar."""
    if _yaml is None:
        return None
    try:
        _yaml.safe_load(block_text)
        return True
    except Exception:
        return False


def heuristic_defects(fm_lines):
    """Regelkanon F5 (Fallback ohne PyYAML) – nur eindeutig gefährliche Form."""
    defects = []
    for idx, raw in enumerate(fm_lines):
        if not raw.strip() or raw[:1] in (" ", "\t", "#"):
            continue
        m = TOP_KEY_RX.match(raw)
        if not m:
            defects.append((idx, "F5",
                            f"Top-Level-Zeile ohne 'key:' – {raw[:60]!r}"))
            continue
        value = m.group(2).strip()
        if not value or value[0] in ("[", "{", "\"", "'", "|", ">"):
            continue                       # legal oder nur mit Parser beurteilbar
        if (value[0] in INDICATORS or value.startswith("- ")
                or ": " in value or value.endswith(":")):
            defects.append((idx, "F5",
                            "Wertform, die YAML nach Hausregeln nicht als "
                            "Plain-Scalar akzeptiert (Indikator/Sequenz/': ')"))
    return defects


def find_defects(fm_lines):
    """Baukritische Funde im Block. Liefert [(index, regel, nachricht)]."""
    if _yaml is None:
        return heuristic_defects(fm_lines)
    defects = []
    for idx, raw in enumerate(fm_lines):
        if not raw.strip() or raw[:1] in (" ", "\t", "#"):
            continue
        if not TOP_KEY_RX.match(raw):
            continue
        if parse_ok(raw + "\n") is False:
            defects.append((idx, "F3",
                            "Zeile ist kein gültiges Top-Level-YAML-Paar – "
                            "Hugo verliert hier das Frontmatter"))
    return defects


# ------------------------------------------------- F7: doppelte Mapping-Schlüssel
# Hugo (go-yaml) bricht hart ab, sobald ein Mapping-Schlüssel auf derselben
# Ebene zweimal steht:
#     [8:1] mapping key "tags" already defined at [7:1]
# PyYAML parst dieselbe Datei still (der letzte Wert gewinnt) – deshalb ist
# dieser Befund ein ZEILENSCAN und keine Parser-Frage. Er läuft MIT und OHNE
# PyYAML identisch (Regelkanon der Wache).
KEY_RX = re.compile(r"^([A-Za-z_][A-Za-z0-9_.\-]*)[ \t]*:(.*)$")
BLOCK_SKALAR_RX = re.compile(r"^[|>][0-9+\-]*[ \t]*$")
FLOW_LISTE_RX = re.compile(r"^\[(?P<inner>.*)\][ \t]*$")


def _einzug(zeile):
    """Spaltenzahl des ersten Nicht-Leerzeichens (Tabs zählen als Spalte)."""
    return len(zeile) - len(zeile.lstrip(" \t"))


def _schluessel_und_wert(text):
    m = KEY_RX.match(text.strip())
    return (m.group(1), m.group(2).strip()) if m else (None, "")


def _wert_zeile(zeile):
    """(schlüssel, wert) einer Mapping-Zeile – None, wenn sie keine ist."""
    m = KEY_RX.match(zeile.strip())
    return (m.group(1), m.group(2).strip()) if m else (None, "")


def doppelte_schluessel(fm_lines):
    """F7 – derselbe Mapping-Schlüssel zweimal auf DERSELBEN Ebene.

    Rückgabe: [(zeilen_idx, schlüssel, erstes_idx, einzug)] (aufsteigend).
    Erkennt Top-Level (`tags`, `cover: …`) UND verschachtelte Schlüssel
    (`cover.image`). Sequenz-Elemente (`- id: "Q1"`) sind EIGENE Container:
    dieselbe Kennung in zwei Einträgen ist korrekt (Quellenlisten!) – sie wird
    nur innerhalb EINES Eintrags gemeldet. Block-Skalare („|“ / „>“) werden
    übersprungen: ihr Text ist Inhalt, kein Schlüssel.
    """
    funde = []
    rahmen = []            # [{"indent": spalte, "keys": {schluessel: idx}}]
    skalar_einzug = None   # läuft ein Block-Skalar, gehören tiefere Zeilen dazu
    for idx, roh in enumerate(fm_lines):
        if skalar_einzug is not None:
            if not roh.strip() or _einzug(roh) > skalar_einzug:
                continue
            skalar_einzug = None
        if not roh.strip() or roh.lstrip().startswith("#"):
            continue
        einzug = _einzug(roh)
        rest = roh[einzug:]
        # --- Sequenz-Element: JEDER Strich eröffnet einen frischen Container
        if rest == "-" or rest.startswith(("- ", "-\t")):
            rahmen = [r for r in rahmen if r["indent"] < einzug]
            nach_strich = rest[1:]
            inhalt = nach_strich.lstrip(" \t")
            spalte = einzug + 1 + (len(nach_strich) - len(inhalt))
            rahmen.append({"indent": spalte, "keys": {}})
            if inhalt:
                schluessel, wert = _wert_zeile(inhalt)
                if schluessel:
                    _merke(rahmen, funde, schluessel, idx)
                    if BLOCK_SKALAR_RX.match(wert or ""):
                        skalar_einzug = spalte
            continue
        # --- Mapping-Zeile (Top-Level oder verschachtelt)
        if not KEY_RX.match(rest):
            continue
        while rahmen and rahmen[-1]["indent"] > einzug:
            rahmen.pop()          # tiefere Rahmen gehörten zur letzten Zuweisung
        if not rahmen or rahmen[-1]["indent"] < einzug:
            rahmen.append({"indent": einzug, "keys": {}})
        schluessel, wert = _wert_zeile(rest)
        _merke(rahmen, funde, schluessel, idx)
        if BLOCK_SKALAR_RX.match(wert or ""):
            skalar_einzug = einzug
    return funde


def _merke(rahmen, funde, schluessel, idx):
    keys = rahmen[-1]["keys"]
    if schluessel in keys:
        funde.append((idx, schluessel, keys[schluessel], rahmen[-1]["indent"]))
    else:
        keys[schluessel] = idx


def _block_ende(fm_lines, idx):
    """Erste Zeile nach dem Block, der zu Zeile idx gehört (tiefere Zeilen)."""
    einzug = _einzug(fm_lines[idx])
    ende = idx + 1
    while ende < len(fm_lines):
        roh = fm_lines[ende]
        if not roh.strip() or _einzug(roh) <= einzug:
            break
        ende += 1
    return ende


def _fluss_liste(wert):
    """`[a, b]` → Liste der Roh-Einträge; None, wenn keine Flow-Liste."""
    m = FLOW_LISTE_RX.match(wert or "")
    return _teile_fluss(m.group("inner")) if m else None


def _teile_fluss(inner):
    """Flow-Liste in ihre Elemente zerlegen (Klammern/Quotes bleiben unberührt)."""
    teile, puffer, tief, quote, escape = [], "", 0, None, False
    for ch in inner:
        if escape:
            puffer += ch
            escape = False
            continue
        if quote:
            puffer += ch
            if ch == "\\" and quote == "\"":
                escape = True
            elif ch == quote:
                quote = None
            continue
        if ch in "\"'":
            quote = ch
            puffer += ch
            continue
        if ch in "[{":
            tief += 1
        elif ch in "]}":
            tief -= 1
        if ch == "," and tief == 0:
            teile.append(puffer.strip())
            puffer = ""
        else:
            puffer += ch
    if puffer.strip():
        teile.append(puffer.strip())
    return teile


def _block_items(fm_lines, key_idx, ende):
    """Block-Liste unterhalb von `key:` → Roh-Einträge; None, wenn keine."""
    items = []
    for zeile in fm_lines[key_idx + 1:ende]:
        text = zeile.strip()
        if text == "-" or text.startswith(("- ", "-\t")):
            items.append(text[1:].strip())
        else:
            return None
    return items


def _normalisiert(roh):
    return roh.strip().strip("\"'").strip().lower()


def heile_doppelte(fm_lines, funde):
    """F7 heilen – Rückgabe (neue Zeilen, änderungen, notizen, ok).

    Reihenfolge: von hinten nach vorn, damit die Indizes stabil bleiben.
    Listen → Vereinigung (kein Element geht verloren) · alles andere →
    letztes Vorkommen bleibt (YAML-Leseregel), das frühere fällt weg.
    ok=False → die Heilung wäre keine Verbesserung; es wird NICHTS geschrieben.
    """
    zeilen = list(fm_lines)
    aenderungen, notizen = [], []
    for idx, schluessel, erst, _einzug_ in sorted(funde, key=lambda f: -f[0]):
        if not (0 <= erst < idx < len(zeilen)):
            return fm_lines, [], [], False
        vorher = zeilen[erst]
        einzug = vorher[:len(vorher) - len(vorher.lstrip(" \t"))]
        erst_ende = _block_ende(zeilen, erst)
        jetzt_ende = _block_ende(zeilen, idx)
        _k1, erst_wert = _wert_zeile(zeilen[erst])
        _k2, jetzt_wert = _wert_zeile(zeilen[idx])
        erst_flow, jetzt_flow = _fluss_liste(erst_wert), _fluss_liste(jetzt_wert)
        erst_block = (_block_items(zeilen, erst, erst_ende)
                      if erst_flow is None and not erst_wert else None)
        jetzt_block = (_block_items(zeilen, idx, jetzt_ende)
                       if jetzt_flow is None and not jetzt_wert else None)
        if erst_flow is not None and jetzt_flow is not None:
            vereint = _vereinige(erst_flow, jetzt_flow)
            zeilen[erst] = f"{einzug}{schluessel}: [{', '.join(vereint)}]"
            entfernt = jetzt_ende - idx
            del zeilen[idx:jetzt_ende]
            aenderungen.append((vorher, zeilen[erst]))
            notizen.append(f"'{schluessel}' vereinigt "
                           f"({len(erst_flow)} + {len(jetzt_flow)} → {len(vereint)} Elemente, "
                           f"{entfernt} Zeile(n) entfernt)")
            continue
        if erst_block is not None and jetzt_block is not None:
            vereint = _vereinige(erst_block, jetzt_block)
            neu_block = [f"{einzug}  - {item}" for item in vereint]
            zeilen[erst + 1:erst_ende] = neu_block
            verschiebung = len(neu_block) - (erst_ende - (erst + 1))
            idx += verschiebung
            jetzt_ende += verschiebung
            del zeilen[idx:jetzt_ende]
            aenderungen.append((vorher, f"{schluessel}: (vereinigte Blockliste)"))
            notizen.append(f"'{schluessel}' (Blockliste) vereinigt "
                           f"({len(erst_block)} + {len(jetzt_block)} → {len(vereint)} Elemente)")
            continue
        # Alles andere: YAML-Leseregel – der LETZTE Wert gilt.
        del zeilen[erst:erst_ende]
        notizen.append(f"'{schluessel}': erstes Vorkommen entfernt – YAML liest "
                       f"den letzten Wert ({jetzt_wert[:60]!r}); verworfen: "
                       f"{erst_wert[:60]!r}")
        aenderungen.append((vorher, None))
    return zeilen, aenderungen, notizen, True


def _vereinige(links, rechts):
    """Beide Listen in Reihenfolge vereinigen, Dubletten (normiert) fallen weg."""
    vereint, gesehen = [], set()
    for roh in list(links) + list(rechts):
        marke = _normalisiert(roh)
        if not marke or marke in gesehen:
            continue
        gesehen.add(marke)
        vereint.append(roh.strip())
    return vereint


def _setze_fm(text, fm_zeilen):
    """Text mit ersetztem Frontmatter-Block – Grenzen und Body bleiben stehen."""
    zeilen = text.split("\n")
    _fm, begin, ende = split_fm(text)
    if begin is None or ende is None:
        return text
    return "\n".join(zeilen[:begin] + list(fm_zeilen) + zeilen[ende:])


# YAML-Indikatoren am Wertanfang – ein Plain-Scalar darf mit keinem davon
# beginnen (Alias *, Anker &, Tag !, reserved @ `, Directive %, Block | >,
# Flow [ ] { }, Quote " ', Kommentar #, Block-Mapping -, Key-Grenz :).
START_INDICATORS = ("-", "?", ":", "*", "&", "!", "@", "`", "|", ">", "%",
                    "[", "]", "{", "}", '"', "'", "#", ",")


def needs_quote(value) -> bool:
    """True, wenn ein Frontmatter-Wert NICHT als Plain-Scalar sicher ist.

    Single Source of Truth für ALLE FM-Schreiber (engine_generate,
    Pin-/Meta-Heiler) – genau diese Lücke erzeugte den Build-Abbruch am
    11.09.2026: '*Werbung | …' begann mit '*' und wurde unquotiert
    geschrieben (alte Regel kannte nur ':', '#' und die Starts ' ', '-',
    '?', '!')."""
    v = "" if value is None else str(value)
    if not v or v != v.strip():
        return True
    if v[0] in START_INDICATORS:
        return True
    if ": " in v or v.endswith(":") or " #" in v or "\n" in v:
        return True
    return False


def yaml_quote(value):
    """Wert → nur falls nötig doppeltes YAML-Quote (verlustfrei).

    Das Frontmatter wird zeilenweise geschrieben – ein echter Umbruch im Wert
    würde die Folgezeilen zu YAML-Content machen. Darum wird \\n escapt."""
    if value is None:
        return '""'
    v = str(value)
    if not needs_quote(v):
        return v
    v = v.replace("\\", "\\\\").replace('"', '\\"')
    v = v.replace("\r", "").replace("\n", "\\n")
    return '"' + v + '"'


def heal_line(raw):
    """Schlüssel behalten, WERT quotieren – alles andere bleibt bytegleich."""
    m = TOP_KEY_RX.match(raw)
    if not m:
        return raw
    key, value = m.group(1), m.group(2).strip()
    if not value:
        return raw
    return f"{key}: {yaml_quote(value)}"


# ------------------------------------------------------------------- Prüfen/Heilen
def inspect_text(text):
    """(grenzregel, kleber, text, defects, doppel) eines Content-Textes.

    Wichtig seit 08.10.2026: Die Doppel-Schlüssel-Prüfung (F7) läuft VOR dem
    Parser-Kurzschluss. PyYAML hält doppelte Schlüssel für gültig (letzter
    gewinnt), Hugo nicht – „der Block parst“ darf hier also NICHT mehr
    „sauber“ heißen.
    """
    fm_lines, begin, end = split_fm(text)
    if fm_lines is None:
        return "F1", "", text, [], []
    if end is None:
        return "F2", "", text, [], []
    doppel = doppelte_schluessel(fm_lines)
    block = "\n".join(fm_lines) + "\n"
    if not doppel and _yaml is not None and parse_ok(block) is True:
        return None, closing_glue(text), text, [], []   # Hugo-Sicht: sauber
    return None, closing_glue(text), text, find_defects(fm_lines), doppel


def inspect(path):
    """Wie `inspect_text`, liest die Datei von der Platte."""
    with open(path, "r", encoding="utf-8") as fh:
        return inspect_text(fh.read())


def heal_values(text, defects):
    """Wert-Ebene heilen – Rückgabe (neuer Text, Änderungen, ok).

    Schreibt NICHTS: der Aufrufer entscheidet, ob und in welcher Reihenfolge
    er Wert-Quotes und Kleber-Heilung auf die Platte bringt (ein Schreibvorgang
    je Datei). ok=False → die Heilung wäre keine Verbesserung (unheilbar)."""
    fm_lines, begin, _end = split_fm(text)
    lines = text.split("\n")
    changes = []
    for idx, _regel, _msg in defects:
        real = begin + idx
        fixed = heal_line(lines[real])
        if fixed != lines[real]:
            changes.append((real, lines[real], fixed))
            lines[real] = fixed
    if not changes:
        return text, [], True
    new_text = "\n".join(lines)
    new_fm, _b, new_end = split_fm(new_text)
    if _yaml is not None and (new_end is None or parse_ok("\n".join(new_fm) + "\n") is not True):
        return text, [], False                          # Heilung hilft nicht
    return new_text, [(alt, neu) for _i, alt, neu in changes], True


def heal(path, text, defects):
    """Werte quotieren – und NUR schreiben, wenn der Block danach parst.

    Rückgabe: (changes, ok). ok=False → nichts geschrieben (unheilbar)."""
    new_text, changes, ok = heal_values(text, defects)
    if not changes:
        return [], ok
    if not ok:
        return [], False
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(new_text)
    return changes, True


def run(fix, quellen=None):
    """→ (hart, kleber, heilungen, unheilbar, residual, geprüfte, doppel).

    `kleber` = F6-Funde (Schlussgrenze zugeklebt). Mit `--fix` werden sie
    ZUSAMMEN mit der Wert-Ebene in einem Schreibvorgang geheilt; ohne `--fix`
    sind sie harte Befunde (Exit 1), damit die Klasse nicht wieder still
    durchläuft. Jeder Eintrag: (pfad, "F6", meldung, notizen).

    `doppel` = (funde, heilungen) der Klasse F7 (doppelte Mapping-Schlüssel,
    08.10.2026): `funde` = [(rel, schlüssel, meldung)] und `heilungen` =
    [(rel, alt, neu)] – Listen werden vereinigt, alles andere folgt der
    YAML-Leseregel (das letzte Vorkommen gilt, das frühere fällt weg und wird
    im Report belegt).

    `quellen` = None → Bestand von der PLATTE; nur dann wird geschrieben.
    `quellen` = [(rel, text)] → Prüflauf auf mitgegebenen Texten (z. B.
    `--staged`: genau die Blobs aus dem Index, nie der Arbeitsbaum) – heilt nie.
    """
    fix = bool(fix) and quellen is None
    if quellen is None:
        quellen = [(os.path.relpath(p, BLOG_DIR), None) for p in content_files()]
    hart, kleber, heilungen, unheilbar, geprüfte = [], [], [], [], 0
    doppel_funde, doppel_heilungen = [], []
    for rel, gegeben in quellen:
        geprüfte += 1
        path = os.path.join(BLOG_DIR, rel)
        if gegeben is None:
            grenze, glue, text, defects, dups = inspect(path)
        else:
            grenze, glue, text, defects, dups = inspect_text(gegeben)
        if grenze:
            note = ("keine eigene ---Zeile am Dateianfang" if grenze == "F1"
                    else "Frontmatter-Block nicht geschlossen – der Body wird "
                         "zum Frontmatter")
            hart.append((rel, grenze, note))
            continue
        notizen = []
        arbeits_text = text
        if glue:
            meldung = f"Schlussgrenze zugeklebt: '---{glue[:56]}'"
            if fix:
                arbeits_text, notizen = post_utils.heal_glued_close(text)
            else:
                hart.append((rel, "F6", meldung))     # ohne --fix baukritisch
            kleber.append((rel, "F6", meldung, notizen))
        for idx, schluessel, erst, _e in dups:
            meldung = (f"doppelter Schlüssel '{schluessel}': Zeile {idx + 1} "
                       f"wiederholt Zeile {erst + 1} – Hugo bricht hier ab "
                       f"(\u201emapping key already defined\u201c)")
            doppel_funde.append((rel, schluessel, meldung))
            if not fix:
                hart.append((rel, "F7", meldung))
        if fix and dups:
            fm_zeilen, _b, _e = split_fm(arbeits_text)
            neu_zeilen, aenderungen, f7_notizen, ok = heile_doppelte(fm_zeilen, dups)
            if not ok:
                unheilbar.append(rel)
                continue                                   # nichts anfassen
            arbeits_text = _setze_fm(arbeits_text, neu_zeilen)
            for alt, neu in aenderungen:
                doppel_heilungen.append((rel, alt, neu))
            for n in f7_notizen:
                doppel_heilungen.append((rel, "", n))
            for idx, schluessel, erst, _e in doppelte_schluessel(
                    split_fm(arbeits_text)[0]):
                hart.append((rel, "F7",
                             f"doppelter Schlüssel '{schluessel}' steht nach "
                             f"der Heilung erneut (Zeile {idx + 1} / {erst + 1})"))
        if fix:
            rest_defects = find_defects(split_fm(arbeits_text)[0])
            neu, changes, ok = heal_values(arbeits_text, rest_defects)
            if not ok:
                unheilbar.append(rel)
                continue
            if neu != text:
                with open(path, "w", encoding="utf-8") as fh:
                    fh.write(neu)
            for alt, ziel in changes:
                heilungen.append((rel, alt, ziel))
        else:
            for idx, regel, msg in defects:
                hart.append((rel, regel, msg))
    unheilbar = sorted(set(unheilbar))
    residual = []
    if fix:
        for rel, _gegeben in quellen:
            grenze, glue, _text, defects, dups = inspect(os.path.join(BLOG_DIR, rel))
            if grenze or glue or defects or dups:
                residual.append(rel)
    return (hart, kleber, heilungen, unheilbar, residual, geprüfte,
            (doppel_funde, doppel_heilungen))


def write_report(hart, kleber, heilungen, unheilbar, residual, geprüfte, modus,
                 doppel=((), ())):
    stand = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M")
    geheilt_f6 = [k for k in kleber if k[3]]
    doppel_funde, doppel_heilungen = doppel
    doppel_listen = [h for h in doppel_heilungen if h[1]]
    doppel_regel = [h for h in doppel_heilungen if not h[1]]
    zeilen = [
        "# 🧱 FM-GRENZEN-REPORT (fm_boundary_guard.py)",
        "",
        f"**Stand:** {stand} UTC · Modus: {modus.upper()}",
        f"**Geprüfte Dateien:** {geprüfte} · **baukritisch:** {len(hart)} · "
        f"**automatisch geheilt:** {len(heilungen)} · **unheilbar:** "
        f"{len(unheilbar)} · **offen nach Heilung:** {len(residual)} · "
        f"**Klebefugen (F6):** {len(kleber)}"
        + (f" (davon {len(geheilt_f6)} geheilt)" if geheilt_f6 else "")
        + f" · **doppelte Schlüssel (F7):** {len(doppel_funde)}"
        + (f" (davon {len(doppel_listen)} vereinigt, "
           f"{len(doppel_regel)} nach YAML-Leseregel)" if doppel_heilungen else ""),
        "",
        "**Regelkanon:** F1 Grenze oben · F2 Grenze unten · F3 Block/Zeile "
        "nicht YAML-parbar · F4 Quote/Flow nicht geschlossen · F5 "
        "Fallback-Regel ohne PyYAML · F6 Schlussgrenze zugeklebt (baukritisch, "
        "mit --fix selbstheilend) · F7 doppelter Mapping-Schlüssel "
        "(baukritisch, mit --fix verlustfrei selbstheilend)",
        "",
        f"**Gegenprüfung:** PyYAML "
        f"{'aktiv (Block-Parse vor und nach jeder Heilung)' if _yaml is not None else 'fehlt – nur deterministische Formregeln, Heilung auf eindeutig gefahrlose Fälle beschränkt'}",
        "",
    ]
    if not hart:
        zeilen.append("🎉 Alle Frontmatter-Blöcke sind baufest – Grenzen "
                      "stehen, Werte sind YAML-konform, kein Schlüssel steht "
                      "doppelt. `hugo --minify` kann am Frontmatter nicht mehr "
                      "scheitern.")
    else:
        zeilen += ["## ⚠️ Baukritische Funde", "",
                   "| Datei | Regel | Befund |", "|---|---|---|"]
        zeilen += [f"| `{f}` | {r} | {m} |" for f, r, m in hart[:60]]
        if len(hart) > 60:
            zeilen.append(f"| … | … | {len(hart) - 60} weitere |")
    if heilungen:
        zeilen += ["", "## Selbstheilung (nur Wert-Quote, Text bytegleich)", ""]
        zeilen += [f"- `{rel}`: `{alt[:70]}` → `{neu[:70]}`"
                   for rel, alt, neu in heilungen[:60]]
    if doppel_funde or doppel_heilungen:
        zeilen += ["", "## F7 – doppelte Mapping-Schlüssel (Hugo-Abbruch)", "",
                   "Hugo (go-yaml) bricht bei einem wiederholten Mapping-Schlüssel "
                   "hart ab (`mapping key \"…\" already defined`), während "
                   "PyYAML dieselbe Datei still parst (letzter Wert gewinnt). "
                   "Genau daran starb der Produktions-Build am 08.10.2026 – "
                   "alle PyYAML-Gates meldeten grün. Listen werden vereinigt "
                   "(kein Element geht verloren), alles andere folgt der "
                   "YAML-Leseregel: Das letzte Vorkommen gilt, das frühere wird "
                   "entfernt und hier belegt.", ""]
        for rel, schluessel, meldung in doppel_funde[:40]:
            ziel = [z for z in doppel_heilungen if z[0] == rel]
            zusatz = ""
            if ziel:
                zusatz = "; ".join(v for _r, _o, v in ziel if v) or "geheilt"
                zusatz = f" → {zusatz[:120]}"
            zeilen.append(f"- `{rel}` **{schluessel}**: {meldung}{zusatz}")
        if len(doppel_funde) > 40:
            zeilen.append(f"- … {len(doppel_funde) - 40} weitere")
    if kleber:
        zeilen += ["", "## F6 – zugeklebte FM-Schlussgrenze (`---Text`)", "",
                   "Hugo rendert den Rest der Grenzzeile als Body (gemessen: "
                   "HTML identisch zu `---\\n\\nText`). Der Schaden ist ein "
                   "anderer: **zeilenweise** lesende Wachen erkennen das "
                   "FM-Ende nur an einer alleinstehenden `---`-Zeile – bleibt "
                   "die aus, gilt der ganze Artikel als Frontmatter und wird "
                   "nie geprüft (grün, obwohl blind), und "
                   "`park_state.set_field` schreibt still gar nichts. "
                   "`--fix` trennt die Naht (bytegleich außer der Grenze) und "
                   "entfernt Prompt-Gerüst am Textanfang.", ""]
        for rel, _regel, msg, notizen in kleber[:30]:
            zusatz = f" → {'; '.join(notizen)}" if notizen else ""
            zeilen.append(f"- `{rel}` {msg}{zusatz}")
        if len(kleber) > 30:
            zeilen.append(f"- … {len(kleber) - 30} weitere")
    if unheilbar:
        zeilen += ["", "## ⚠️ Nicht automatisch heilbar (manuell)", ""]
        zeilen += [f"- `{rel}`" for rel in unheilbar[:40]]
    if residual:
        zeilen += ["", "## ⚠️ Nach Heilung weiterhin auffällig", ""]
        zeilen += [f"- `{rel}`" for rel in residual[:40]]
    zeilen += ["", "---",
               "_Hartes Gate VOR `hugo --minify` (deploy.yml): FM-Fehler sind "
               "die einzige Klasse, die den gesamten Deploy stoppt – ohne "
               "Gate-Report, ohne verwertbares Fehler-Alerting, nur ein toter "
               "Build._"]
    with open(REPORT, "w", encoding="utf-8") as fh:
        fh.write("\n".join(zeilen) + "\n")


# ------------------------------------------------------------------- Selbsttest
SELFTEST_CASES = [
    # (name, FM-Zeile, befund_mit_pyyaml, geheilte_zeile, befund_ohne_pyyaml)
    #  befund_ohne_pyyaml = None → gleiche Erwartung im Fallback-Modus
    ("Regression 11.09.2026: *Werbung-Prefix",
     "pin_description: *Werbung | Der Traumurlaub scheitert am Budget?",
     True, 'pin_description: "*Werbung | Der Traumurlaub scheitert am Budget?"',
     None),
    ("Alias ohne Ziel", "excerpt: *unbekannt", True, 'excerpt: "*unbekannt"', None),
    ("Unbekannter Tag", "inspiration: !!unbekannt Bild", True,
     'inspiration: "!!unbekannt Bild"', None),
    ("Bullethochladung", "excerpt: - nicht ok", True, 'excerpt: "- nicht ok"', None),
    ("Key-Konflikt im Wert", "title: Reisekasse: 7 Tipps", True,
     'title: "Reisekasse: 7 Tipps"', None),
    ("Wert endet auf Doppelpunkt", "pinwand: Günstig reisen:", True,
     'pinwand: "Günstig reisen:"', None),
    ("Quote nicht geschlossen", 'description: "halb offen', True,
     'description: "\\"halb offen"', False),
    ("Blockscalar mit Text", "description: | zu viel text", True,
     'description: "| zu viel text"', False),
    # Ruhe-Fälle – sie schützen den Bestand vor False Positives
    ("Ruhe: Double-Quote mit Doppelpunkt", 'title: "Reisekasse: 7 Tipps"',
     False, None, None),
    ("Ruhe: Flow-Sequence mit ': ' im Item",
     'tags: ["Energie-Update: was sich jetzt ändert", "Strom", "Gas"]',
     False, None, None),
    ("Ruhe: Plain-Scalar", "pillar: mietwagen", False, None, None),
    ("Ruhe: ISO-Datum", "date: 2026-09-11T11:17:28Z", False, None, None),
    ("Ruhe: Blockschlüssel", "cover:", False, None, None),
    ("Ruhe: verschachtelte Zeile", "  alt: !!str Bild", False, None, None),
    ("Ruhe: Pipe/Ampersand mittig", "pinwand: Günstig reisen | Budget & Auto",
     False, None, None),
    ("Ruhe: Boolesche Werte", "draft: false", False, None, None),
    ("Ruhe: legaler Anker (nur Parser urteilt)", "title: &titel Reisekasse",
     False, None, True),
    ("Ruhe: legaler Tag (nur Parser urteilt)", "inspiration: !!str Bild",
     False, None, True),
]

GRENZE_CASES = [
    ("geschlossener Block", "---\ntitle: x\n---\nBody\n", None),
    ("Kleber-Schluss (Hugo akzeptiert)", "---\ntitle: x\n---Warum zahlen…\n", None),
    ("ohne obere Grenze", "title: x\n---\nBody\n", "F1"),
    ("ohne untere Grenze", "---\ntitle: x\nBody\n", "F2"),
]


def selftest():
    fehler = []
    hinweise = []
    if _yaml is None:
        hinweise.append("PyYAML fehlt – es gilt der deterministische "
                        "Fallback-Regelkanon (Deploy installiert pyyaml vor "
                        "der Wache: 'Py-Abhängigkeiten für Gate-Chain')")
    for name, zeile, erwartet, ziel, fallback in SELFTEST_CASES:
        soll = erwartet if _yaml is not None else (
            erwartet if fallback is None else fallback)
        defects = find_defects(zeile.split("\n"))
        if bool(defects) != soll:
            fehler.append(f"{name}: Befund={bool(defects)} erwartet={soll}")
            continue
        got = heal_line(zeile)
        if soll and ziel is not None and got != ziel:
            fehler.append(f"{name}: Heilung {got!r} != {ziel!r}")
        if got != zeile:                        # Konvergenz + Schema-Ruhe
            if find_defects([got]):
                fehler.append(f"{name}: geheilte Zeile bleibt auffällig "
                              f"(nicht konvergent)")
            if parse_ok(got + "\n") is False:
                fehler.append(f"{name}: geheilte Zeile ist kein gültiges YAML")
    for name, text, erwartet in GRENZE_CASES:
        fm_lines, _b, end = split_fm(text)
        grenze = None if (fm_lines is not None and end is not None) else erwartet
        if grenze != erwartet:
            fehler.append(f"{name}: Grenze {grenze!r} != {erwartet!r}")
    if closing_glue("---\nt: x\n---Warum zahlen…\nBody\n") != "Warum zahlen…":
        fehler.append("Kleber-Erkennung defekt")
    if closing_glue("---\nt: x\n---\nBody\n") != "":
        fehler.append("Kleber-Erkennung meldet saubere Grenze")
    # Round-Trip-Eigenschaft: jeder Wert – so hässlich er für YAML ist –
    # muss durch yaml_quote so geschrieben werden, dass Hugo ihn exakt
    # zurückbekommt (Quote nur wo nötig, Escaping immer korrekt).
    NASTY = ['*Werbung | Der Traumurlaub: 500 €', ': führend', '- listig',
             'a: b', 'text # kommentar', 'sag "hi" \\back', 'mehr\nzeilig',
             "it's ok", '', '  lead', 'trail  ', '{} klammern', '[1, 2]',
             '&anker', '*alias', '%direktive', '@at', '`tick`', '>fold',
             '|literal', 'ganz normal']
    for v in NASTY:
        q = yaml_quote(v)
        if needs_quote(v) and not (q.startswith('"') and q.endswith('"')):
            fehler.append(f"Round-Trip {v!r}: Quote fehlt trotz Bedarf")
            continue
        if not needs_quote(v) and q != v:
            fehler.append(f"Round-Trip {v!r}: unnötig umgeschrieben")
            continue
        if _yaml is not None:
            try:
                back = _yaml.safe_load("key: " + q + "\n")
            except Exception as exc:
                fehler.append(f"Round-Trip {v!r}: {exc}")
                continue
            if not isinstance(back, dict) or back.get("key") != v:
                fehler.append(f"Round-Trip {v!r} → {q!r} → {back!r}")
    # Schema-Schutz: eine Liste darf durch eine Heilung nie zum String werden
    listenzeile = 'tags: ["Energie-Update: was sich jetzt ändert"]'
    if find_defects([listenzeile]):
        fehler.append("Schema-Risiko: legale Flow-Sequence würde umgeschrieben")
    # F6 – Klebefuge: erkennen, heilen, Naht-Treue, Prompt-Gerüst, Idempotenz.
    # Die Fälle sind die zwei REALEN Produzenten-Muster des Bestands
    # (keyword_optimizer: „Du willst x? …" bzw. „x im Check: …";
    #  redaktions_standard: KI-Antwort mit Prompt-Gerüst).
    kleber_fall = ("---\ntitle: x\n---Du willst gaspreis-probe? Zahlst du zu "
                   "viel?\n\nZweiter Absatz.\n")
    if closing_glue(kleber_fall) != "Du willst gaspreis-probe? Zahlst du zu viel?":
        fehler.append("F6: Klebefuge nicht erkannt")
    geheilt, notizen = post_utils.heal_glued_close(kleber_fall)
    soll = ("---\ntitle: x\n---\n\nDu willst gaspreis-probe? Zahlst du zu "
            "viel?\n\nZweiter Absatz.\n")
    if geheilt != soll:
        fehler.append(f"F6: Heilung falsch: {geheilt!r}")
    if geheilt.replace("---\n\n", "---", 1) != kleber_fall:
        fehler.append("F6: Heilung ist nicht bytegleich außer der Naht")
    if not notizen or "getrennt" not in notizen[0]:
        fehler.append("F6: Heilung ohne Nachweis-Notiz")
    if post_utils.heal_glued_close(geheilt)[0] != geheilt:
        fehler.append("F6: Heilung ist nicht idempotent")
    if post_utils.heal_glued_close("---\ntitle: x\n---\n\nBody.\n")[0] != \
            "---\ntitle: x\n---\n\nBody.\n":
        fehler.append("F6: saubere Datei wird angefasst")
    schablone = ("---\ntitle: x\n---TITEL: Digitaler Turbo\n\nARTIKEL:\n\n"
                 "Klickst du auf einen Link?\n")
    geruest_frei, g_notizen = post_utils.heal_glued_close(schablone)
    if geruest_frei != "---\ntitle: x\n---\n\nKlickst du auf einen Link?\n":
        fehler.append(f"F6: Prompt-Gerüst nicht entfernt: {geruest_frei!r}")
    if not any("Gerüst" in n for n in g_notizen):
        fehler.append("F6: Gerüst-Entfernung nicht belegt")
    nur_schablone = "TITEL: x\n\nARTIKEL:\n"
    if post_utils.strip_generator_scaffolding(nur_schablone)[0] != nur_schablone:
        fehler.append("F6: Schablone ohne Inhalt darf nicht geleert werden")
    # Naht-SSOT: kein Body-Fragment – gestrippt oder nicht – darf kleben.
    for fragment in ("Text.", "\nText.", "\n\n\nText.", "Text.\n"):
        z = post_utils.join_article("title: x", fragment)
        if post_utils.glued_close(z)[0] is not None:
            fehler.append(f"Naht-SSOT: join_article klebt bei {fragment!r}")
        if post_utils.split_article(z)[2].lstrip("\n") != fragment.lstrip("\n"):
            fehler.append(f"Naht-SSOT: join/split verliert Text bei {fragment!r}")
    # F7 – doppelte Mapping-Schlüssel (Bau-Ursache 08.10.2026, WF-54C4 #643).
    # PyYAML hält sie für gültig (der letzte Wert gewinnt), Hugo bricht ab.
    # Deshalb prüft und heilt die Wache hier REGELBASIERT, nicht über den Parser.
    f7_doppelt = ['tags: ["Campingurlaub", "Reisekosten"]',
                  'tags: ["Mietwagen und Wohnmobil"]',
                  'categories: ["Ratgeber"]']
    funde = doppelte_schluessel(f7_doppelt)
    if len(funde) != 1 or funde[0][1] != "tags" or funde[0][2] != 0:
        fehler.append(f"F7: doppeltes 'tags' nicht erkannt: {funde}")
    verschachtelt = ["cover:", "  image: alt.jpg", "  image: neu.jpg", "  alt: x"]
    funde_v = doppelte_schluessel(verschachtelt)
    if len(funde_v) != 1 or funde_v[0][1] != "image" or funde_v[0][2] != 1:
        fehler.append(f"F7: verschachteltes 'cover.image' nicht erkannt: {funde_v}")
    sequenz = ["quellen:", '  - id: "Q1"', "    titel: Eins",
               '  - id: "Q2"', "    titel: Zwei"]
    if doppelte_schluessel(sequenz):
        fehler.append("F7: Sequenz-Einträge (Quellenliste) fälschlich gemeldet")
    skalar = ["beschreibung: |", "  Zeile: mit Doppelpunkt", "  Zeile: noch eine",
              "titel: x"]
    if doppelte_schluessel(skalar):
        fehler.append("F7: Block-Skalar-Inhalt fälschlich als Schlüssel gelesen")
    neu, _aend, notizen, ok = heile_doppelte(f7_doppelt, funde)
    if not ok or doppelte_schluessel(neu) or len(neu) != 2:
        fehler.append(f"F7: Flow-Listen-Heilung nicht konvergent: {neu}")
    elif not any('"Campingurlaub"' in z and '"Mietwagen und Wohnmobil"' in z
                 for z in neu):
        fehler.append(f"F7: Vereinigung verlor ein Element: {neu}")
    if not any("vereinigt" in n for n in notizen):
        fehler.append("F7: Vereinigung wird nicht belegt (Report-Pflicht)")
    neu_v, _a2, _n2, ok_v = heile_doppelte(verschachtelt, funde_v)
    if not ok_v or doppelte_schluessel(neu_v):
        fehler.append(f"F7: Skalar-Heilung nicht konvergent: {neu_v}")
    elif "alt.jpg" in "".join(neu_v) or "neu.jpg" not in "".join(neu_v):
        fehler.append("F7: YAML-Leseregel verletzt – der letzte Wert muss gelten")
    blockliste = ["tags:", '  - "A"', '  - "B"', "tags:", '  - "C"']
    neu_b, _a3, _n3, ok_b = heile_doppelte(blockliste, doppelte_schluessel(blockliste))
    if not (ok_b and not doppelte_schluessel(neu_b)
            and '"A"' in "".join(neu_b) and '"C"' in "".join(neu_b)):
        fehler.append(f"F7: Blocklisten-Vereinigung fehlerhaft: {neu_b}")
    if heile_doppelte(neu, [])[0] != neu or heile_doppelte(neu, [])[3] is not True:
        fehler.append("F7: Heilung ohne Funde verändert die Datei (nicht idempotent)")
    if _yaml is not None and parse_ok("\n".join(neu) + "\n") is not True:
        fehler.append("F7: geheiltes Frontmatter parst nicht")
    for h in hinweise:
        print(f"ℹ FM-Grenzen-Selbsttest: {h}")
    if fehler:
        print("❌ FM-Grenzen-Selbsttest FEHLERHALFT – die Wache greift nicht "
              "ins Content-Regiment ein:")
        for f in fehler:
            print("  -", f)
        return 2
    print(f"✅ FM-Grenzen-Selbsttest: {len(SELFTEST_CASES)} Wert-Fälle + "
          f"{len(GRENZE_CASES)} Grenz-Fälle + F7-Doppelschlüssel (erkennen, "
          f"vereinigen, YAML-Leseregel, Sequenz-/Skalar-Schutz) + "
          f"Kleber/Quote/Schema-Schutz grün (inkl. Regression '*Werbung |').")
    return 0


def staged_content():
    """[(rel, text)] der GESTAGETEN Content-Blobs (für die Commit-Sperre).

    Gelesen wird der INDEX (`git show :<pfad>`), nicht der Arbeitsbaum – genau
    der Stand, den der Commit festschreiben würde (dieselbe Regel wie die
    Markenflächen-Sperre in `.githooks/pre-commit`). Rückgabe None, wenn
    git/Index nicht lesbar sind: dann entscheidet der Aufrufer fail-closed.
    """
    try:
        r = subprocess.run(["git", "diff", "--cached", "--name-only",
                            "--diff-filter=ACMR"], capture_output=True,
                           text=True, timeout=30, cwd=BLOG_DIR)
    except (OSError, subprocess.SubprocessError):
        return None
    if r.returncode != 0:
        return None
    treffer = []
    for pfad in r.stdout.splitlines():
        pfad = pfad.strip()
        if not pfad.startswith("content/") or not pfad.endswith((".md", ".markdown")):
            continue
        try:
            b = subprocess.run(["git", "show", f":{pfad}"], capture_output=True,
                               text=True, timeout=30, cwd=BLOG_DIR)
        except (OSError, subprocess.SubprocessError):
            return None
        if b.returncode != 0:
            return None
        treffer.append((pfad, b.stdout))
    return sorted(treffer)


# --------------------------------------------------------------- Wirkungsprobe
F7_FIXTURE = """---
title: "Campingurlaub planen: Budget für Platz, Fahrt und Ausrüstung"
date: 2026-10-07T17:47:29Z
draft: true
reserve: true
tags: ["Campingurlaub", "Reisekosten", "Urlaub planen"]
tags: ["Mietwagen und Wohnmobil", "Reisekosten sparen"]
categories: ["Ratgeber"]
cover:
  image: images/covers/2026-10-06-campingurlaub.jpg
  image: images/covers/2026-10-07-campingurlaub.jpg
  alt: "Campingurlaub planen"
quellen:
  - id: "Q1"
    titel: "Erste Quelle"
  - id: "Q2"
    titel: "Zweite Quelle"
---

Camping wirkt oft preiswert, solange du nur den Platz ansiehst.
"""

# Ruhe-Fixture: legale Block-Skalare und Sequenz-Einträge mit gleichen
# Schlüsseln (Quellenlisten) – hier darf NICHTS gefunden werden.
F7_RUHE = """---
title: "Ruhige Datei"
beschreibung: |
  Mehrzeilig: mit Doppelpunkt
  und einer zweiten Zeile.
quellen:
  - id: "Q1"
    titel: "Erste Quelle"
  - id: "Q2"
    titel: "Zweite Quelle"
---

Text.
"""


def wirkungsprobe():
    """Maschinenvertrag „Deckung heißt Wirkung“: beweist an echten Fixtures,
    dass die F7-Klasse erkannt, verlustfrei geheilt und konvergent ist.

    Rückgabe (ok, meldung). Geprüft wird der GANZE Weg über `run(fix=True)` mit
    umgelenktem Content-Verzeichnis – inklusive Report, Body-Treue und einem
    zweiten Lauf (Fixpunkt). Nie am Bestand: alles läuft in einer Wegwerf-Ablage.
    """
    with tempfile.TemporaryDirectory(prefix="fmwirkung-") as tmp:
        posts = os.path.join(tmp, "content", "posts")
        os.makedirs(os.path.join(posts, "camping"))
        os.makedirs(os.path.join(posts, "ruhig"))
        camping = os.path.join(posts, "camping", "index.md")
        ruhig = os.path.join(posts, "ruhig", "index.md")
        with open(camping, "w", encoding="utf-8") as fh:
            fh.write(F7_FIXTURE)
        with open(ruhig, "w", encoding="utf-8") as fh:
            fh.write(F7_RUHE)
        globe = globals()
        alt_files, alt_report = globe["content_files"], globe["REPORT"]
        globe["content_files"] = lambda: sorted(
            os.path.join(wurzel, name)
            for wurzel, _dirs, namen in os.walk(os.path.join(tmp, "content"))
            for name in namen if name.endswith(".md"))
        globe["REPORT"] = os.path.join(tmp, "FM-GRENZEN-REPORT.md")
        try:
            hart, _kleber, _heil, unheilbar, residual, geprueft, (funde, _dh) = run(True)
            if not funde or len(funde) != 2:
                return False, (f"Fixture lieferte {len(funde)} F7-Funde statt 2 "
                               "(tags + cover.image) – Detektor greift nicht")
            if unheilbar or residual or any(r == "F7" for _f, r, _m in hart):
                return False, f"Heilung nicht sauber (unheilbar/residual/hart): {hart}"
            mit = open(camping, encoding="utf-8").read()
            fm_neu, _b, _e = split_fm(mit)
            tags = [z for z in fm_neu if z.startswith("tags:")]
            if len(tags) != 1:
                return False, f"tags steht {len(tags)}× – nicht konvergent"
            for erwartet in ("\"Campingurlaub\"", "\"Reisekosten\"",
                             "\"Urlaub planen\"", "\"Mietwagen und Wohnmobil\"",
                             "\"Reisekosten sparen\""):
                if erwartet not in tags[0]:
                    return False, f"Vereinigung verlor {erwartet}: {tags[0]}"
            bilder = [z for z in fm_neu if z.strip().startswith("image:")]
            if len(bilder) != 1 or "2026-10-07" not in bilder[0]:
                return False, ("cover.image nicht nach YAML-Leseregel geheilt "
                               f"(letzter Wert muss gelten): {bilder}")
            if "Q2" not in "\n".join(fm_neu):
                return False, "Sequenz-Einträge (quellen Q1/Q2) wurden angetastet"
            if _yaml is not None and parse_ok("\n".join(fm_neu) + "\n") is not True:
                return False, "geheiltes Frontmatter parst nicht"
            if body(mit) != body(F7_FIXTURE):
                return False, "Body wurde verändert – Heilung muss texttreu sein"
            if open(ruhig, encoding="utf-8").read() != F7_RUHE:
                return False, "Ruhe-Fixture wurde angefasst (False Positive)"
            (hart2, kleber2, heil2, unheil2, residual2, geprueft2,
             doppel2) = run(True)
            if open(camping, encoding="utf-8").read() != mit:
                return False, "zweiter Lauf ändert erneut (nicht idempotent)"
            if residual2 or doppel2[0]:
                return False, f"zweiter Lauf meldet noch Befunde: {doppel2[0]}"
            write_report(hart2, kleber2, heil2, unheil2, residual2, geprueft2,
                         "fix", doppel2)
            if not os.path.exists(globe["REPORT"]):
                return False, "Report wurde nicht geschrieben"
        finally:
            globe["content_files"] = alt_files
            globe["REPORT"] = alt_report
    return True, (f"F7 erkannt (tags + cover.image), verlustfrei geheilt "
                  f"(5 Tags vereinigt, letztes Bild gilt), Body bytegleich, "
                  f"Sequenzlisten unberührt, zweiter Lauf ein Fixpunkt "
                  f"({geprueft} Dateien)")


def body(text):
    """Alles ab der FM-Schlussgrenze – für die Texttreue-Prüfung."""
    _zeilen, _begin, ende = split_fm(text)
    return "\n".join(text.split("\n")[ende:]) if ende else text


def main():
    if "--selftest" in sys.argv:
        return selftest()
    if "--wirkungsprobe" in sys.argv:
        ok, meldung = wirkungsprobe()
        print(("✅ " if ok else "❌ ") + "FM-Grenzen-Wirkungsprobe: " + meldung)
        return 0 if ok else 2
    if "--staged" in sys.argv:
        texte = staged_content()
        if texte is None:
            print("❌ FM-Grenzen (--staged): der Index ist nicht lesbar – es "
                  "wird nichts freigegeben (fail-closed).")
            return 2
        (hart, _kleber, _heil, _unh, _res, geprüfte,
         (doppel_funde, _dh)) = run(False, quellen=texte)
        for rel, schluessel, msg in doppel_funde:
            print(f"⚠ FM-Grenze F7: {rel} – {msg}")
        for rel, regel, msg in hart:
            if regel != "F7":
                print(f"⚠ FM-Grenze {regel}: {rel} – {msg}")
        if hart:
            print(f"❌ {len(hart)} baukritische(r) FM-Fund/Funde in den "
                  f"gestageten Dateien ({geprüfte} geprüft) – dieser Commit "
                  f"würde den Build töten. Heilung: "
                  f"python3 scripts/fm_boundary_guard.py --fix && git add content/")
            return 1
        print(f"✅ FM-Grenzen (--staged) sauber ({geprüfte} Content-Datei(en) im "
              f"Index): dieser Commit kann den Hugo-Build nicht am Frontmatter "
              f"töten.")
        return 0
    fix = "--fix" in sys.argv
    (hart, kleber, heilungen, unheilbar, residual, geprüfte,
     (doppel_funde, doppel_heilungen)) = run(fix)
    write_report(hart, kleber, heilungen, unheilbar, residual, geprüfte,
                 "fix" if fix else "check", (doppel_funde, doppel_heilungen))
    for rel, schluessel, msg in doppel_funde:
        if fix:
            print(f"🩹 FM-Doppelschlüssel geheilt: {rel} – {msg}")
        else:
            print(f"⚠ FM-Grenze F7: {rel} – {msg}")
    if fix:
        for rel, alt, neu in doppel_heilungen:
            print(f"   ↳ {rel}: {neu}")
    for rel, regel, msg in hart:
        if regel != "F7":
            print(f"⚠ FM-Grenze {regel}: {rel} – {msg}")
    for rel, alt, neu in heilungen:
        print(f"🩹 FM-Grenze geheilt: {rel}: {alt[:60]} → {neu[:60]}")
    if fix:
        for rel, _r, _m, notizen in kleber:
            if notizen:
                print(f"🩹 FM-Klebefuge geheilt: {rel}: {'; '.join(notizen)}")
    if unheilbar:
        for rel in unheilbar:
            print(f"❌ nicht automatisch heilbar: {rel}")
    if residual:
        print(f"❌ {len(residual)} Datei(en) bleiben nach Heilung auffällig – "
              f"Details: FM-GRENZEN-REPORT.md")
        return 1
    if unheilbar:
        print(f"❌ {len(unheilbar)} Datei(en) müssen manuell repariert werden – "
              f"Report: FM-GRENZEN-REPORT.md")
        return 1
    if heilungen or doppel_heilungen:
        print(f"✅ FM-Grenzen: {len(heilungen)} Wert(e) und "
              f"{len(doppel_heilungen)} Doppelschlüssel-Stelle(n) selbstgeheilt "
              f"({geprüfte} Dateien geprüft) – der Build ist wieder möglich.")
        return 0
    if hart:
        print(f"❌ {len(hart)} baukritische(r) FM-Fund/Funde (--fix heilt "
              f"deterministisch). Report: FM-GRENZEN-REPORT.md")
        return 1
    if kleber:
        print(f"✅ FM-Grenzen: {len(kleber)} Klebefuge(n) mit --fix getrennt "
              f"({geprüfte} Dateien geprüft) – die Wachen sehen jetzt denselben "
              f"Text wie Hugo.")
        return 0
    print(f"✅ FM-Grenzen sauber ({geprüfte} Dateien) – Grenzen stehen allein, "
          f"kein Schlüssel doppelt, Werte sind YAML-konform: die Wachen und "
          f"Hugo lesen denselben Text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
