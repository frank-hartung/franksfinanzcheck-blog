#!/usr/bin/env python3
"""
fix_url_hygiene.py – Deterministische Link-URL-Hygiene (R8-URL-LEERZEICHEN)

WARUM (Befund 02.09.2026, Issue „Mi 02.09.: nur 1 statt 2–3 Artikel“):
  Fertige Premium-Artikel wurden am Publish-Gate mit dem HARTEN Fehler
  R8-URL-LEERZEICHEN gestoppt (z. B. Ziel „…-zuhause/“ als „…-zu Hause/“
  geschrieben – Leerzeichen in der Markdown-URL). Die Folge war fatal für
  die Kadenz: Der Kandidat wurde in den Zustand „hold“ zurückgestuft
  („Korrektur nötig, NIEMALS automatisch“), obwohl der Fehler rein
  DETERMINISTISCH heilbar ist. Der Tag blieb mit 1 Artikel unter dem
  Mindestziel, und kein Heiler (fix_r8_anker, draft_link_healer) hat
  diese Fehlerklasse behandelt.

LÖSUNG – drei Modi, alle deterministisch (kein KI-Rewriting):
  1) --fix     : Jede interne Markdown-URL mit Leerzeichen (oder %20) wird
                 gegen die ECHTEN Post-Slugs aufgelöst (Normalisierung:
                 Kleinbuchstaben, Umlaute → ae/oe/ue/ss, alles außer
                 [a-z0-9] entfernt). EINDEUTIGER Treffer → URL wird auf den
                 korrekten Slug korrigiert; mehrdeutig/kein Treffer → Fund
                 wird gemeldet, aber NIE geraten.
  2) --heal-holds : Gehaltene Posts (park_state „hold“), deren einziger
                 harter Grund R8-URL-LEERZEICHEN ist, werden nachweislich
                 geheilt und in die Re-Queue (cadence_wait) gelegt – die
                 Promotion entscheidet weiterhin allein cadence_guard am
                 nächsten Publikationstag. Das hebt die „NIEMALS
                 automatisch“-Blockade NUR für die deterministisch heilbare
                 URL-Leerzeichen-Klasse auf; alle anderen hold-Gründe
                 bleiben unangetastet.
  3) --selftest : Sabotage-Schutz (Exit 2, wenn der Heiler selbst bricht).

Die Sicherheitsregel des Heilers: Ein interner Link wird NUR ersetzt,
wenn der normalisierte Ziel-Fragment EXAKT einem vorhandenen Post-Slug
entspricht. Alles andere bleibt stehen und wird im Report sichtbar.

Aufruf:
  python3 scripts/fix_url_hygiene.py                # Report (keine Änderung)
  python3 scripts/fix_url_hygiene.py --fix          # URLs heilen
  python3 scripts/fix_url_hygiene.py --heal-holds   # heilbare holds → Re-Queue
  python3 scripts/fix_url_hygiene.py --selftest
"""

import datetime
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
POSTS = ROOT / "content" / "posts"

# Alle Markdown-Dateien unter content/ (Posts, Pillar, statische Seiten).
def content_files(root: Path = CONTENT) -> list:
    files = []
    for p in sorted(root.rglob("*.md")):
        if p.name == "_index.md":
            continue
        files.append(p)
    return files


def normalize_umlauts(text: str) -> str:
    """ä→ae, ö→oe, ü→ue, ß→ss (identisch zum Textverständnis-Guard)."""
    return (text.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue")
                .replace("Ä", "Ae").replace("Ö", "Oe").replace("Ü", "Ue")
                .replace("ß", "ss"))


def norm_key(text: str) -> str:
    """Normalisiert einen Slug/URL-Fragment für den Vergleich:
    nur [a-z0-9] zählt – Leerzeichen, Bindestriche, Punkte etc. fallen weg.
    Genau dadurch wird „…-zu Hause“ == „…-zuhause“ erkennbar (der eigentliche
    Kernbefund vom 02.09.2026)."""
    return re.sub(r"[^a-z0-9]", "", normalize_umlauts(text.lower()))


def collect_slugs(posts_dir: Path = POSTS) -> list:
    """Alle Post-Slugs (Verzeichnisnamen) unter content/posts."""
    if not posts_dir.is_dir():
        return []
    return sorted(d.name for d in posts_dir.iterdir() if d.is_dir())


def resolve_fragment(fragment: str, slugs: list) -> str | None:
    """Löst einen fehlerhaften URL-Fragment gegen die echten Slugs auf.

    Liefert den eindeutigen korrekten Slug oder None (kein/mehrdeutiger
    Treffer → niemals raten)."""
    key = norm_key(fragment)
    if not key:
        return None
    hits = [s for s in slugs if norm_key(s) == key]
    if len(hits) == 1:
        return hits[0]
    return None


def heal_url(url: str, slugs: list) -> str | None:
    """Korrigiert EINE Markdown-URL, wenn sie ein heilbares Leerzeichen/
    %20-Problem hat und eindeutig auflösbar ist. None = keine Änderung."""
    if not url or url.startswith(("http://", "https://", "mailto:", "#")):
        return None
    if url.startswith("/go/"):
        return None
    if '"' in url:
        # Markdown-Titel-Attribut (… "title") – nicht anfassen
        return None
    if " " not in url and "%20" not in url:
        return None
    url = url.replace("%20", " ")  # %20 ist kodiertes Leerzeichen
    segs = [s for s in url.split("/") if s != ""]
    if not segs:
        return None
    resolved = resolve_fragment(segs[-1], slugs)
    if not resolved:
        return None
    segs[-1] = resolved
    new = "/".join(segs)
    if url.startswith("/"):
        new = "/" + new
    if url.endswith("/") and not new.endswith("/"):
        new += "/"
    return new


_LINK_RE = re.compile(r"(\[[^\]]*\])\(([^)]*)\)")


def heal_text(text: str, slugs: list) -> tuple:
    """Heilt alle URLs in einem Markdown-Text.

    Rückgabe: (neuer_text, anzahl_fixes, [beschreibungen])."""
    out = []
    new_count = 0

    def _sub(m: re.Match) -> str:
        nonlocal new_count
        head, url = m.group(1), m.group(2)
        fixed = heal_url(url, slugs)
        if fixed is None or fixed == url:
            return m.group(0)
        new_count += 1
        out.append(f"  „{url[:80]}“ → „{fixed[:80]}“")
        return f"{head}({fixed})"

    new_text = _LINK_RE.sub(_sub, text)
    return new_text, new_count, out


def scan_url_leerzeichen(text: str) -> list:
    """Findet R8-URL-LEERZEICHEN-Funde (Spiegel der Guard-Logik)."""
    finds = []
    for m in _LINK_RE.finditer(text):
        url = m.group(2)
        if url.startswith(("http", "mailto:", "#")) or url.startswith("/go/"):
            continue
        if " " in url or "%20" in url:
            finds.append((m.group(1)[:40], url))
    return finds


def run_fix(root: Path = CONTENT, posts_dir: Path = POSTS,
            do_write: bool = True) -> dict:
    """Heilt alle Content-Dateien. Rückgabe: {files, fixes, unreviewed}."""
    slugs = collect_slugs(posts_dir)
    stats = {"files": 0, "fixes": 0, "unreviewed": []}
    for path in content_files(root):
        text = path.read_text(encoding="utf-8")
        new_text, count, _ = heal_text(text, slugs)
        if count and do_write:
            path.write_text(new_text, encoding="utf-8")
        if count:
            stats["files"] += 1
            stats["fixes"] += count
            print(f"  {count} URL-Fix(es): {path.relative_to(ROOT)}")
        # Restfunde (nicht eindeutig auflösbar) immer sichtbar machen
        final_text = new_text if count else text
        rest = scan_url_leerzeichen(final_text)
        if rest:
            stats["unreviewed"].append((str(path.relative_to(ROOT)),
                                        [u for _, u in rest]))
    if stats["unreviewed"]:
        print("\n⚠ Nicht eindeutig auflösbare URLs (manuell prüfen):")
        for rel, urls in stats["unreviewed"]:
            for u in urls:
                print(f"   - {rel}: „{u}“")
    return stats


# ---------------------------------------------------------------------------
# --heal-holds: deterministisch heilbare R8-URL-LEERZEICHEN-Holds entblocken
# ---------------------------------------------------------------------------

HOLD_MARKER_RX = re.compile(r"(R[0-9]+-[A-Z0-9_-]+)")
# Nur diese harte Fehlerklasse ist deterministisch heilbar und darf die
# „NIEMALS automatisch“-Blockade automatisch auflösen.
HEALABLE_CODES = {"R8-URL-LEERZEICHEN"}


def hold_is_healable(grund: str) -> bool:
    """True nur, wenn der hold-Grund ausschließlich R8-URL-LEERZEICHEN ist
    (bzw. die Klartext-Form „URL mit Leerzeichen“). Jede weitere harte
    Fehlerklasse im Grund → False (Mensch entscheidet)."""
    if not grund:
        return False
    codes = set(HOLD_MARKER_RX.findall(grund))
    if codes:
        return codes <= HEALABLE_CODES
    return "URL mit Leerzeichen" in grund or "URL-Leerzeichen" in grund


def requeue_healed_holds(posts_dir: Path = POSTS,
                         root: Path = CONTENT,
                         extra_slugs: list | None = None) -> list:
    """Heilt gehaltene Posts mit ausschließlich heilbarem R8-URL-LEERZEICHEN-
    Grund und legt sie nachweislich in die Re-Queue (cadence_wait).

    Rückgabe: Liste der re-queueten Slugs (nur bei tatsächlicher Heilung).
    Ablauf: (1) URL-Hygiene auf die Datei, (2) Verifikation per Guard-Logik
    (kein R8-URL-LEERZEICHEN mehr), (3) park_state.park → queue.
    Schritt 3 ist KEINE Veröffentlichung: cadence_guard entscheidet am
    nächsten Publikationstag über die Promotion."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import park_state

    slugs = collect_slugs(posts_dir) + (extra_slugs or [])
    requeued = []
    for index in sorted((posts_dir).glob("*/index.md")):
        text = index.read_text(encoding="utf-8")
        try:
            st = park_state.read(text)
        except Exception:
            continue
        if st["state"] != "hold" or not hold_is_healable(st["grund"] or ""):
            continue
        healed, count, _ = heal_text(text, slugs)
        if not count:
            continue
        # Verifikation: nach der Heilung darf kein R8-URL-LEERZEICHEN bleiben
        if scan_url_leerzeichen(healed):
            continue
        # Inhalt schreiben, dann in die Re-Queue legen (draft bleibt draft!)
        index.write_text(healed, encoding="utf-8")
        try:
            from park_state import now_utc_iso
        except ImportError:
            now_utc_iso = (datetime.datetime.now(datetime.timezone.utc)
                           - datetime.timedelta(minutes=1)
                           ).strftime("%Y-%m-%dT%H:%M:%SZ")
        park_state.park(
            index,
            "kadenz: R8-URL-Leerzeichen deterministisch geheilt – "
            "Re-Queue (nächster Publikationstag entscheidet)",
            now_utc_iso(),
            do_fix=True,
        )
        requeued.append(index.parent.name)
        print(f"  ♻️  hold geheilt + Re-Queue: {index.parent.name}")
    return requeued


# ---------------------------------------------------------------------------
# Selbsttest (Sabotage-Schutz)
# ---------------------------------------------------------------------------

def run_selftest() -> list:
    fehler = []
    slugs = ["2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause",
             "2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet"]

    # 1) Leerzeichen-URL wird eindeutig aufgelöst (Kernfall 02.09.2026)
    url = "../../posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zu Hause/"
    fixed = heal_url(url, slugs)
    if fixed != "../../posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause/":
        fehler.append(f"Leerzeichen-URL nicht korrekt aufgelöst: {fixed!r}")

    # 2) %20-Variante
    url2 = "../../posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zu%20Hause/"
    fixed2 = heal_url(url2, slugs)
    if fixed2 != "../../posts/2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause/":
        fehler.append(f"%20-URL nicht korrekt aufgelöst: {fixed2!r}")

    # 3) Mehrdeutig/kein Treffer → NIE raten
    if heal_url("../../posts/2026-08-20-gibts-nicht/", slugs) is not None:
        fehler.append("Nicht existierender Slug wurde geändert (Rate-Verbot verletzt)")
    if heal_url("../../posts/2026-08-26-dns-server-wechseln/", slugs) is not None:
        fehler.append("Teil-Slug ohne Eindeutigkeit wurde geändert (Rate-Verbot verletzt)")

    # 4) Externe/System-URLs bleiben unangetastet
    for ext in ("https://example.com/a b/", "mailto:a@b.de",
                "/go/dsl/", "#anker mit leerzeichen"):
        if heal_url(ext, slugs) is not None:
            fehler.append(f"Externe/System-URL verändert: {ext}")

    # 5) heal_text über ganzen Body
    body = ("TEXT\n\n[Ratgeber zum DSL-Tarif](../../posts/2026-08-20-so-findest-du-"
            "den-richtigen-dsl-tarif-fuer-dein-zu Hause/) und mehr.")
    new_body, count, _ = heal_text(body, slugs)
    if count != 1 or "zuhause/" not in new_body or "zu Hause/" in new_body:
        fehler.append(f"heal_text fehlerhaft: {count} Fixes, {new_body[-90:]!r}")

    # 6) Selftest der hold-Entscheidung
    if not hold_is_healable("publish-gate: Textverständnis-Gate nicht "
                            "bestanden: R8-URL-LEERZEICHEN: URL mit Leerzeichen"):
        fehler.append("R8-URL-LEERZEICHEN-hold nicht als heilbar erkannt")
    if hold_is_healable("publish-gate: Textverständnis-Gate nicht bestanden: "
                        "R8-URL-LEERZEICHEN: …; R5-ABSATZ-HART: …"):
        fehler.append("Hold mit zusätzlicher harter Klasse fälschlich heilbar")
    if hold_is_healable("publish-gate: Lesbarkeits-Gate nicht bestanden: Score 60"):
        fehler.append("Nicht-heilbarer hold fälschlich als heilbar erkannt")

    # 7) End-to-End: --heal-holds auf Fixture (Temp-Posts)
    with tempfile.TemporaryDirectory() as tmp:
        fx_root = Path(tmp)
        fx_posts = fx_root / "content" / "posts"
        fx_posts.mkdir(parents=True)
        fx_slugs = collect_slugs(fx_posts) + slugs  # Auflösung gegen echte Welt
        slug = "2026-08-26-fixture-hold-test"       # Ordner-Slug ist sauber
        p = fx_posts / slug
        p.mkdir()
        fm = (
            "---\n"
            "title: \"Test\"\n"
            "date: 2026-08-26T06:00:00Z\n"
            "draft: true\n"
            "cadence_demoted: 2026-09-02T13:07:26Z\n"
            'cadence_grund: "publish-gate: Textverständnis-Gate nicht '
            'bestanden: R8-URL-LEERZEICHEN: URL mit Leerzeichen"\n'
            "---\n\n"
            "[Ratgeber zum DSL-Tarif](../../posts/2026-08-20-so-findest-du-"
            "den-richtigen-dsl-tarif-fuer-dein-zu Hause/)\n"
        )
        (p / "index.md").write_text(fm, encoding="utf-8")
        try:
            requeued = requeue_healed_holds(posts_dir=fx_posts, root=fx_root,
                                            extra_slugs=slugs)
        except SystemExit:
            requeued = []
        after = (p / "index.md").read_text(encoding="utf-8")
        if "2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zu Hause/" in after:
            fehler.append("Fixture-URL wurde nicht geheilt")
        if "cadence_wait: true" not in after:
            fehler.append("Geheilter hold wurde nicht in die Re-Queue gelegt")
        if requeued != [slug]:
            fehler.append(f"requeue_healed_holds lieferte {requeued!r}")
    return fehler


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        errs = run_selftest()
        if errs:
            print("🛑 URL-HYGIENE-SELFTEST FEHLGESCHLAGEN – der Heiler ist defekt:")
            for e in errs:
                print(f"   - {e}")
            return 2
        print("✅ URL-Hygiene-Selbsttest grün (Leerzeichen-URLs, %20, "
              "Rate-Verbot, hold-Heilung).")
        return 0

    if "--heal-holds" in args:
        requeued = requeue_healed_holds()
        if requeued:
            print(f"URL-Hygiene: {len(requeued)} gehaltene(r) Post(s) geheilt "
                  f"und in die Re-Queue gelegt → {requeued}")
        else:
            print("URL-Hygiene: keine heilbaren R8-URL-LEERZEICHEN-Holds.")
        return 0

    stats = run_fix(do_write="--fix" in args)
    verb = "geheilt" if "--fix" in args else "zu heilen"
    if stats["fixes"]:
        print(f"\nURL-Hygiene: {stats['fixes']} URL(s) in "
              f"{stats['files']} Datei(en) {verb}.")
    else:
        print("URL-Hygiene: keine Leerzeichen-URLs im Bestand – alle Links sauber.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
