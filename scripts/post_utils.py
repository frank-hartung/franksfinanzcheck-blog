"""Zentrale Post-Utilities für FranksFinanzcheck-Skripte.

Unterstützt PAGE-BUNDLES (content/posts/<slug>/index.md) und Legacy
(content/posts/<slug>.md). Alle Skripte nutzen list_post_paths() bzw.
post_path(), damit neue Artikel automatisch als Bundles angelegt werden
und alte Pfade weiter funktionieren.
"""
import os
import glob

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
