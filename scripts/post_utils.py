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
    return sorted(set(paths))


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
