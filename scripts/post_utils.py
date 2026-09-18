"""Zentrale Post-Utilities für FranksFinanzcheck-Skripte.

Unterstützt PAGE-BUNDLES (content/posts/<slug>/index.md) und Legacy
(content/posts/<slug>.md). Alle Skripte nutzen list_post_paths() bzw.
post_path(), damit neue Artikel automatisch als Bundles angelegt werden
und alte Pfade weiter funktionieren.
"""
import os
import glob
import re

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")


def list_post_paths():
    """Alle Post-Dateien (Bundles + Legacy), sortiert, dedupliziert."""
    paths = glob.glob(os.path.join(POSTS_DIR, "*.md"))
    paths += glob.glob(os.path.join(POSTS_DIR, "*", "index.md"))
    return sorted(set(p for p in paths if not p.endswith("_index.md")))


def slug_of(path):
    """Slug aus einem Post-Pfad (Bundle- oder Legacy-Format)."""
    if os.path.basename(path) == "index.md":
        return os.path.basename(os.path.dirname(path))
    return os.path.basename(path)[:-3]


def post_path(slug):
    """Pfad eines Posts (Bundle, falls vorhanden, sonst Legacy)."""
    bundle = os.path.join(POSTS_DIR, slug, "index.md")
    if os.path.exists(bundle):
        return bundle
    legacy = os.path.join(POSTS_DIR, slug + ".md")
    if os.path.exists(legacy):
        return legacy
    return bundle  # neu: Bundles sind der Standard


def write_post(slug, content):
    """Schreibt einen Post als Page-Bundle (content/posts/<slug>/index.md)."""
    d = os.path.join(POSTS_DIR, slug)
    os.makedirs(d, exist_ok=True)
    path = os.path.join(d, "index.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def read_post(slug):
    """Liest den Inhalt eines Posts."""
    with open(post_path(slug), encoding="utf-8") as f:
        return f.read()


# ---------------------------------------------------------------------------
# Titel-Kürzung (PREMIUM, 26.08.2026) – Single Source of Truth
#
# Hintergrund: Mehrere Skripte (engine_generate.save_article,
# meta_optimizer.fix_meta) kürzten lange Titel mit harten `title[:60]`-
# Slices – und schnitten dadurch WÖRTER INNENHERAUS ("…Tarife – Gastari",
# "…Fallen – Vollkas", "…für die goldene"). Der Cover-Renderer (und der
# H1, die RSS/Pinterest-Feed-Titel) zeigten seither unvollständige
# Cover-Texte. ALLE Kürzungen laufen seither durch safe_title_cut():
#   - bricht NUR an Wortgrenzen (nie mitten im Wort)
#   - bricht bei "Hauptkeyword: Untertitel"-Titeln am liebsten das
#     Untertitel-Ende, nie den Keyword-Kopf
#   - hinterlässt keine hängenden Gedankenstriche/Bindestriche/Punktation
#   - fällt auf den (kompletten) Kopf zurück, wenn der Rest zu kurz würde
# ---------------------------------------------------------------------------

# Zeichen, die nie am Titel-Ende stehen dürfen (hängende Konnektoren)
_DANGLING_END = "–—-–,;: \t\"'“”„«»"


def _clean_tail(s):
    """Strippt hängende Konnektoren/Punktation am Zeilenende."""
    return s.rstrip(_DANGLING_END).rstrip()


def _cut_at_word(s, max_len):
    """Kürzt `s` auf max_len Zeichen an der letzten Wortgrenze.
    Rückgabe: gekürzter String (evtl. kürzer als max_len) oder "" wenn
    sich kein sinnvoller Schnitt ergibt (z. B. ein einziges Wort)."""
    if len(s) <= max_len:
        return s
    cut = s[:max_len]
    sp = cut.rfind(" ")
    if sp <= 0:
        return ""  # ein einziges Wort – kein Wortgrenzen-Schnitt möglich
    return _clean_tail(cut[:sp])


def safe_title_cut(title, max_len=60):
    """Sichere Titel-Kürzung (Wortgrenze, nie mitten im Wort).

    Strategie für die Blog-Konvention "Hauptkeyword: Untertitel":
      1) Passt der Titel → unverändert (Whitespace normalisiert).
      2) Mit Doppelpunkt: erst das Untertitel-Ende kürzen. Reicht das
         Budget für den Untertitel nicht (Rest < 12 Zeichen), fällt die
         Kürzung auf den KOMPLETTEN Kopf zurück – ein kompletter
         Keyword-Titel ist immer besser als ein halber.
      3) Ohne Doppelpunkt: Wortgrenzen-Schnitt am Ende. Scheitert der
         Wortgrenzen-Schnitt (Ein-Wort-Übergröße), wird auf max_len
         gekürzt und als letztes Mittel wird das letzte Wort entfernt –
         NIE ein Wortbruch.

    Rückgabe: String ≤ max_len, endet an Wortgrenze, ohne hängende
    Konnektoren. Eingaben mit leerem Ergebnis (pathologisch) liefern den
    originalen Titel unverändert (lieber zu lang als kaputt – die
    Cover-/Titel-Gates melden es dann).
    """
    import re as _re
    t = _re.sub(r"\s+", " ", (title or "").strip())
    if not t or len(t) <= max_len:
        return t

    if ":" in t:
        head, tail = t.split(":", 1)
        head = head.strip()
        tail = tail.strip()
        # Untertitel kürzen (Budget inkl. ": " Trennung)
        budget = max_len - len(head) - 2
        if budget > 12:
            cut_tail = _cut_at_word(tail, budget)
            if len(cut_tail) >= 12:
                return f"{head}: {cut_tail}"
        # Rest-Untertitel zu kurz → kompletter Kopf (Keyword bleibt intakt)
        if len(head) + 1 <= max_len:
            return head
        # Kopf selbst über Budget → Wortgrenzen-Schnitt am Kopf
        cut_head = _cut_at_word(head, max_len)
        return cut_head if len(cut_head) >= 12 else head[:max_len]

    cut = _cut_at_word(t, max_len)
    if cut:
        return cut
    # Ein einzelnes riesiges Wort: letztes Wort opfern, nie Wortbruch
    words = t.split()
    if len(words) > 1:
        return _clean_tail(" ".join(words[:-1]))[:max_len]
    return t[:max_len]


def frontmatter_date(content):
    """Liest das `date:`-Feld aus Frontmatter als ISO-String (YYYY-MM-DD)
    zurück – robust gegen Vollzeitstempel ("2026-08-26T06:10:00Z") und
    Quotes. Rückgabe: None, wenn kein Datum erkennbar ist.

    DAS Datum-Feld ist die Single Source of Truth für den
    Veröffentlichungstag (nicht der Ordner-Datumspräfix – der bleibt bei
    Re-Queue/Re-Dating alt, s. cadence_guard)."""
    import re as _re
    m = _re.search(r"^date:\s*[\"']?(\d{4}-\d{2}-\d{2})", content, _re.M)
    return m.group(1) if m else None


# ---------------------------------------------------------------------------
# Build-Zustand eines Posts – exakt nach den Hugo-Gates (Issue #129)
#
# hugo.toml setzt drei harte Publikations-Gates:
#   buildDrafts=false · buildFuture=false · buildExpired=false
# Eine Seite erscheint also NUR dann im Build (und nur dann funktioniert
# ihre URL live), wenn sie weder Entwurf ist, noch in der Zukunft liegt,
# noch abgelaufen ist.
#
# WARUM EIGENE FUNKTION: Die Link-Skripte verglichen "Zukunfts-Post" bisher
# nur auf TAG-Genauigkeit (date[:10] > today). Ein Post, der am selben Tag
# um 18:00 UTC terminiert ist, galt als "live" – der Build um 03:15 UTC hat
# ihn aber nicht erzeugt (Hugo vergleicht den KOMPLETTEN Zeitstempel).
# Ergebnis: fröhlich verlinkte Nicht-Build-Seiten, rotes Qualitäts-Gate,
# Issue #129. build_state() spiegelt deshalb Hugos Semantik 1:1.
# ---------------------------------------------------------------------------

def parse_hugo_time(raw):
    """Frontmatter-Zeitwert → aware datetime (UTC). None bei unparsebar.
    Akzeptiert: 2026-08-26 · 2026-08-26T06:10:00Z · 2026-08-26T06:10:00+02:00
    · 2026-08-26 06:10:00 +0200 · Quotes drumherum. Naive Werte gelten – wie
    bei Hugo ohne --timezone – als UTC, reine Datumswerte als Mitternacht UTC."""
    import datetime as _dt
    import re as _re
    if raw is None:
        return None
    s = str(raw).strip().strip("\"'").strip()
    if not s:
        return None
    s = s.replace("Z", "+00:00")                        # ...T06:10:00Z
    s = _re.sub(r"([+-]\d{2})(\d{2})$", r"\1:\2", s)    # +0200 → +02:00
    s = _re.sub(r"\s+([+-]\d{2}:\d{2})$", r"\1", s)     # " … +02:00" anhängen
    s = _re.sub(r"^(\d{4}-\d{2}-\d{2})[ T]", r"\1T", s)  # Leerzeichen → T
    try:
        t = _dt.datetime.fromisoformat(s)
    except ValueError:
        m = _re.match(r"^(\d{4})-(\d{2})-(\d{2})", s)   # nur Datum (00:00 UTC)
        if not m:
            return None
        try:
            return _dt.datetime(*(int(x) for x in m.groups()),
                                tzinfo=_dt.timezone.utc)
        except ValueError:
            return None
    if t.tzinfo is None:
        t = t.replace(tzinfo=_dt.timezone.utc)
    return t.astimezone(_dt.timezone.utc)


def _fm_value(content, key):
    """Rohen Frontmatter-Wert eines Schlüssels lesen (erste Trefferzeile)."""
    import re as _re
    m = _re.search(rf"^{_re.escape(key)}:\s*(.+?)\s*$", content, _re.M)
    return m.group(1).strip("\"'") if m else ""


def _fm_bool(value):
    """Frontmatter-Boolean → True/False, None wenn Schlüssel fehlt/leer."""
    if not value:
        return None
    v = str(value).strip().lower()
    if v in ("true", "yes", "1"):
        return True
    if v in ("false", "no", "0"):
        return False
    return None


def build_state(content, now=None):
    """Ist diese Content-Datei im aktuellen Hugo-Build sichtbar?

    Rückgabe: (sichtbar: bool, grund: str). `grund` beschreibt den Grund nur
    bei sichtbar=False ("Draft …", "Zukunfts-Post (…)", "abgelaufen (…)").
    `now` ist injizierbar (deterministische Selbsttests)."""
    import datetime as _dt
    now = now or _dt.datetime.now(_dt.timezone.utc)
    if _fm_bool(_fm_value(content, "draft")) is True:
        return False, "Draft (Kadenz-Re-Queue)"
    date = parse_hugo_time(_fm_value(content, "date"))
    if date is not None and date > now:
        return False, f"Zukunfts-Post ({date.strftime('%Y-%m-%d %H:%M UTC')})"
    exp_raw = _fm_value(content, "expiryDate") or _fm_value(content, "expireDate")
    exp = parse_hugo_time(exp_raw)
    if exp is not None and exp <= now:
        return False, f"abgelaufen ({exp_raw})"
    return True, "live"


# ---------------------------------------------------------------------------
# FM-NAHT – die eine Wahrheit für die Frontmatter-Grenze (18.09.2026)
#
# WARUM (Folge-Befund 5 des Gate-Vorfalls vom 18.09.2026):
# Mindestens achtzehn Schreiber im Repo bauten eine Content-Datei aus
# `content.split("---", 2)` wieder zusammen – per String-Konkatenation:
#     "---" + fm + "---" + body
# Das ist nur so lange gut, wie `body` mit einem Zeilenumbruch beginnt. Sobald
# ein Heiler den Body anfasst und dabei den führenden Umbruch verliert, klebt
# die Schlussgrenze am Text:  ---DSL wechseln im Check: Zahlst du …
# Zwei Produzenten sind belegt (Git-Blame auf die Klebezeile, HEAD vor der
# Heilung): `keyword_optimizer.heal_first_paragraph` – es ersetzt den ersten
# Absatz; der leere Rest vor dem Absatz fiel unter den Tisch (Commit 6c772fd,
# 17.09.2026, 9 Dateien) – und der KI-Heilpfad in `redaktions_standard.py`,
# dessen Modellantwort gestrippt in parts[2] landete (Commits 7b51187,
# 37c1b3d, a261d64, 4 Dateien; in `2026-09-04-digitaler-turbo-…` stand sogar
# das Prompt-Gerüst „TITEL: … / ARTIKEL:" im Live-Text).
# Gesamt: 13 Dateien, davon 9 live.
#
# WAS DER KLEBER WIRKLICH KOSTET (gemessen, nicht behauptet):
#   · Hugo (Auslieferung) rendert genauso wie bei sauberer Naht; die
#     Zeilenumbruch-Prüfung liegt im Selbsttest der Wache (fm_boundary_guard.py,
#     Fall F6: „---Text" → „---\n\nText", bytegleich bis auf die Naht).
#     Damit ist belegt: Der geklebte Rest steht als Absatz in der Auslieferung
#     (Live-Beleg: die Gerüstzeilen „TITEL: …/ARTIKEL:" waren im HTML sichtbar).
#     Verifiziert außerdem: 13/13 Bestandsdateien sind bytegleich bis auf die
#     Naht geheilt (Regression: scripts/tests/test_fm_boundaries.py,
#     KleberFugeTests.test_fix_trennt_die_naht_und_erhaelt_den_text).
#   · Zeilenweise lesende Wachen werden dagegen BLIND: Sie erkennen das
#     Frontmatter-Ende nur an einer exakt alleinstehenden `---`-Zeile. Bleibt
#     die aus, gilt der ganze Artikel als Frontmatter und wird nicht geprüft
#     (`compound_guard`: 1 Fund sauber, 0 Funde geklebt; `umbruch_guard`,
#     `math_guard`, `park_state._fm_span` mit demselben Muster).
#   · Die PARK-MASCHINE kann nicht mehr schreiben: `park_state.set_field`
#     liefert auf einer geklebten Datei still `False` – ein maschinell
#     geparkter Artikel sieht danach wie ein menschlicher Entwurf aus und wird
#     nie wieder promotet. Genau so sind die vier Reserve-Entwürfe hängen
#     geblieben.
#
# DESHALB: EINE Funktion schreibt die Naht (`join_article`), EINE liest sie
# Hugo-konform (`split_article`), EINE heilt sie (`heal_glued_close`). Wer
# künftig eine Content-Datei zusammensetzt, benutzt join_article – damit kann
# kein Schreiber mehr kleben, egal wie das Body-Fragment aussieht.
# ---------------------------------------------------------------------------

FM_FENCE = "---"

# Generator-Schablonen: Zeilen, die eine KI-Antwort aus dem Prompt spiegelt
# („TITEL: …", „ARTIKEL:", „DESCRIPTION: …"). Sie sind kein Inhalt – der Titel
# steht im Frontmatter, die Kennzeichnung war nur die Frage an das Modell.
SCHABLONE_ZEILE = re.compile(
    r"^(?:TITEL|TITLE|DESCRIPTION|BESCHREIBUNG|ARTIKEL|ARTICLE|PROMPT|OUTPUT)\s*:",
    re.IGNORECASE)
SCHABLONE_MARKER = re.compile(
    r"^(?:TITEL|TITLE|DESCRIPTION|BESCHREIBUNG|ARTIKEL|ARTICLE|PROMPT|OUTPUT)\s*:?\s*$",
    re.IGNORECASE)


def split_article(text):
    """(prefix, fm, body) mit den Grenzen, die HUGO sieht.

    `prefix` ist alles vor dem Frontmatter (normalerweise leer), `fm` der Block
    OHNE die beiden `---`-Zeilen, `body` alles danach. Ein geklebter Rest
    („---Text") zählt – wie bei Hugo – zum Body, damit kein Leser Text verliert.

    Kein Frontmatter (oder keine schließende Grenze): ("", "", text) – der
    Aufrufer schreibt dann besser gar nichts um, statt Inhalt zu riskieren.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != FM_FENCE:
        return "", "", text
    for i in range(1, len(lines)):
        if lines[i].startswith(FM_FENCE):
            fm = "\n".join(lines[1:i])
            rest = lines[i][len(FM_FENCE):]           # Kleber zählt zum Body
            body = "\n".join(([rest] if rest else []) + lines[i + 1:])
            return "", fm, body
    return "", "", text


def join_article(fm, body, prefix=""):
    """Setzt eine Content-Datei mit KANONISCHER Naht zusammen.

    Rückgabe: `prefix + "---\n" + fm + "\n---\n\n" + body` – unabhängig
    davon, ob `body` führende Umbrüche hat oder ein Heiler sie verloren hat.
    `fm` und `body` dürfen ihre Grenz-Umbrüche noch tragen (die Splitter der
    Schreiber liefern unterschiedliche Konventionen); sie werden normiert.
    Auf einer schon kanonischen Datei ist das Ergebnis bytegleich; sonst
    normalisiert der Aufruf nur die Naht bzw. überschüssige Leerzeilen.
    Auf einer geklebten Datei entsteht die korrekte Grenze (Heilung durch
    Weglassen des Fehlers, nicht durch Sonderfall-Code im Schreiber).
    """
    fm_clean = (fm or "").strip("\n")
    if not fm_clean:
        return (prefix or "") + (body or "").lstrip("\n")
    return (f"{prefix or ''}{FM_FENCE}\n{fm_clean}\n{FM_FENCE}\n\n"
            f"{(body or '').lstrip(chr(10))}")


def glued_close(text):
    """(Zeilenindex, Kleberest) der Frontmatter-Schlussgrenze.

    (None, "") = die Grenze steht allein (sauber) oder es gibt keine.
    Genau EINE Grenze wird geprüft: die erste `---`-Zeile nach der Öffnung –
    das ist die Stelle, an der Hugo das Frontmatter beendet.
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != FM_FENCE:
        return None, ""
    for i in range(1, len(lines)):
        if lines[i].startswith(FM_FENCE):
            rest = lines[i][len(FM_FENCE):]
            if rest.strip():
                return i, rest
            return None, ""
    return None, ""


def strip_generator_scaffolding(text):
    """Entfernt Prompt-Gerüst am Textanfang. Rückgabe: (text, entfernte Zeilen).

    Nur am ANFANG und nur, solange echte Inhaltszeilen folgen: Ein Artikel, der
    nur aus Schablonenzeilen besteht, wird nicht geleert (dann bleibt alles –
    ein leerer Artikel wäre der größere Schaden). Markerzeilen („ARTIKEL:")
    dürfen auch allein stehen, Titelzeilen nur mit Inhalt dahinter.
    """
    lines = text.split("\n")
    entfernt = []
    i = 0
    while i < len(lines):
        raw = lines[i]
        s = raw.strip()
        if not s:
            if entfernt:
                entfernt.append("")
                i += 1
                continue
            break
        if SCHABLONE_MARKER.match(s) or SCHABLONE_ZEILE.match(s):
            entfernt.append(raw)
            i += 1
            continue
        break
    if not entfernt:
        return text, []
    rest = lines[i:]
    if not any(z.strip() for z in rest):          # nichts Echtes dahinter
        return text, []
    return "\n".join(rest), entfernt


def heal_glued_close(text):
    """Zerlegt eine geklebte Frontmatter-Grenze. Rückgabe: (text, Notizen).

    „---Text"  →  „---\\n\\nText"   (bytegleich bis auf die Naht)
    „---TITEL: …\\n\\nARTIKEL:\\n\\nText"  →  Grenze sauber, Gerüst entfernt.

    Idempotent: auf einer sauberen Datei kommt der Text unverändert zurück.
    """
    i, kleber = glued_close(text)
    if i is None:
        return text, []
    lines = text.split("\n")
    kopf_sauber, weg = strip_generator_scaffolding(
        "\n".join([kleber] + lines[i + 1:]))
    notizen = ["Klebefuge getrennt (---Text → ---\\n\\nText)"]
    if weg:
        notizen.append(f"Prompt-Gerüst entfernt ({len(weg)} Zeile(n): "
                       f"{weg[0].strip()[:48]!r} …)")
    neu = lines[:i] + [FM_FENCE, ""] + kopf_sauber.split("\n")
    return "\n".join(neu), notizen
