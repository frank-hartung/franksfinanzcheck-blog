#!/usr/bin/env python3
# ============================================================
#  MASTODON-MANUAL-POST
#
#  Postet EIN bestehendes (bereits veröffentlichtes) Blogartikel-Bundle
#  gezielt manuell auf Mastodon – unabhängig vom automatischen
#  scripts/social_poster.py, der jeden Artikel nur EINMAL postet
#  (Dedupe über "social_posted: true" im Frontmatter).
#
#  Einsatzzweck: An Tagen ohne neuen Blogartikel (Publikationscadence
#  ist Mo/Mi/Fr, siehe scripts/cadence_manager.py) trotzdem gezielt
#  einen bestehenden, thematisch passenden Artikel erneut sichtbar
#  machen ("Spotlight-Post") – MIT eigenem Intro-Text, damit es nicht
#  wie eine wortgleiche Dopplung des Erst-Posts wirkt.
#
#  Rührt "social_posted" NICHT an und beeinflusst daher die normale
#  Automatik nicht.
#
#  Benötigt Secret MASTODON_ACCESS_TOKEN (Scope 'write:statuses'+
#  'write:media' reicht, 'write:accounts' wird hier nicht gebraucht).
#
#  Nutzung:
#    python3 scripts/mastodon_manual_post.py --slug <slug> [--intro "..."] [--dry-run]
# ============================================================

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import social_poster as sp  # noqa: E402  (wiederverwendet Frontmatter-/Post-/API-Helfer)

DEFAULT_INTRO = "🔁 Nochmal ans Herz gelegt:"


def main():
    ap = argparse.ArgumentParser(description="Postet einen bestehenden Artikel manuell auf Mastodon (oder bearbeitet einen vorhandenen Post).")
    ap.add_argument("--slug", required=True, help="Ordnername unter content/posts/, z. B. 2026-08-12-preisgarantie-gas-...")
    ap.add_argument("--intro", default=None, help="Individueller Einleitungssatz (Standard: Spotlight-Hinweis; leerer String = kein Intro)")
    ap.add_argument("--edit-status-id", default=None, help="Bearbeitet einen VORHANDENEN Status (PUT) statt einen neuen zu posten (POST) – z. B. um Hashtags nachträglich zu korrigieren, ohne Duplikat-Post.")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.slug in ("__seo_heal__", "seo-heal", "__seo_dedupe__", "seo-dedupe"):
        import mastodon_seo
        extra = []
        if args.dry_run and "--dry-run" not in sys.argv:
            extra.append("--dry-run")
        if args.slug in ("__seo_dedupe__", "seo-dedupe"):
            extra.append("--delete-dupes")
        for a in extra:
            if a not in sys.argv:
                sys.argv.append(a)
        mastodon_seo.DRY_RUN = "--dry-run" in sys.argv
        mastodon_seo.DELETE_DUPES = "--delete-dupes" in sys.argv
        mastodon_seo.main()
        return

    slug_dir = sp.POSTS_DIR / args.slug
    index_md = slug_dir / "index.md"
    if not index_md.is_file():
        sys.exit(f"FEHLER: Artikel-Bundle '{args.slug}' nicht gefunden ({index_md}).")

    fm = sp.read_frontmatter(index_md)
    if fm.get("broken"):
        sys.exit(f"FEHLER: Frontmatter von '{args.slug}' konnte nicht gelesen werden.")
    if fm.get("draft"):
        sys.exit(f"FEHLER: Artikel '{args.slug}' ist noch draft:true – wird nicht gepostet.")

    url = f"{sp.BASE_URL}/posts/{args.slug}/"
    title = fm.get("title") or args.slug.replace("-", " ").title()
    hook = fm.get("kurzantwort") or fm.get("description") or ""
    if len(hook) > 200:
        hook = hook[:200].rsplit(" ", 1)[0] + " …"
    tags = sp.hashtags(fm.get("tags", []))

    # --intro nicht gesetzt -> Standard-Spotlight-Hinweis (neuer Post).
    # --intro "" (explizit leer) -> KEIN Intro, entspricht 1:1 dem Format
    # von scripts/social_poster.py::build_post() – wichtig beim Bearbeiten
    # eines automatisch erzeugten Posts, damit nur die Hashtags korrigiert
    # werden und der Rest des Textes unverändert bleibt.
    intro = DEFAULT_INTRO if args.intro is None else args.intro
    parts = [p for p in (intro, f"📌 {title}", hook, f"🔗 {url}", tags) if p]
    text = "\n\n".join(parts)
    text = text[:497] + "…" if len(text) > 500 else text

    image = sp.cover_path(slug_dir, fm)

    print("Post-Text:")
    print(text)
    print(f"Bild: {image if image else '(kein Cover gefunden)'}")
    if args.edit_status_id:
        print(f"Modus: BEARBEITEN von Status {args.edit_status_id}")

    if args.dry_run:
        print("[DRY-RUN] Es wurde nichts gesendet.")
        return

    if not sp.MASTODON_TOKEN:
        sys.exit("FEHLER: Kein MASTODON_ACCESS_TOKEN gesetzt – siehe ANLEITUNG-SOCIAL-MEDIA.md.")

    if args.edit_status_id:
        # Leeres Intro = Original-Format des Auto-Posters beibehalten
        # (Cover nachziehen, ohne Spotlight-Satz).
        if not intro:
            text = sp.build_post(fm, args.slug)
        ok, ref = sp.edit_mastodon(args.edit_status_id, text, image)
        sp.append_log(args.slug, "mastodon-manual-edit", ok, ref)
    else:
        ok, ref = sp.post_mastodon(text, image)
        sp.append_log(args.slug, "mastodon-manual", ok, ref)

    if not ok:
        sys.exit(f"FEHLER: Mastodon-Post fehlgeschlagen: {ref}")
    print(f"✅ {'Bearbeitet' if args.edit_status_id else 'Gepostet'}: {ref}")


if __name__ == "__main__":
    main()

