#!/usr/bin/env python3
"""
reserve_janitor.py – entfernt Rückläufer und blockierte Reserve-Entwürfe.

WARUM (26.09.2026, Content-Reserve #24)
----------------------------------------
Der tägliche Vorrat darf kein Friedhof aus zwei Klassen werden:

  * RÜCKLÄUFER: Ein Artikel war bereits veröffentlicht (`reserve_published`),
    steht danach aber wieder auf `draft: true`. Das ist fast immer ein
    Dubletten-/Kadenz-Rückbau. Im Bestand verwirrt er die Redaktion, in
    llms.txt/Queues kann er als 404-Leiche weiterleben.
  * BLOCKIERT: Die Reserve-Triage meldet harte Hindernisse (z. B. defektes
    Frontmatter, zu wenige interne Links, ungültiges lastmod) oder die
    Quarantäne hat `reserve_blocked:` gesetzt. Solche Artikel sollen den
    Vorrat nicht mehr belegen.

Frühere Reparaturen musterten Dauer-Blocker nur aus und legten Rückläufer der
Redaktion vor. Der Auftrag hier ist explizit stärker: vollständig löschen.
Dieses Skript macht das kontrolliert und idempotent:

  - Es löscht NUR Entwürfe (`draft: true`) und NUR maschinenverwaltete Artikel
    (Reserve-/Kadenz-Marker oder Eintrag im Reserve-Gedächtnis). Handentwürfe
    werden gemeldet, aber nicht angefasst.
  - Es entfernt Markdown-Links auf gelöschte Artikel aus verbleibenden
    Content-Dateien (Linktext bleibt), damit keine 404-Kette entsteht.
  - Es löscht zugehörige Cover-Varianten und Audio-Chunk-Artefakte, sofern sie
    von keinem verbleibenden Content mehr referenziert werden.
  - Es bereinigt die aktiven Reserve-Gedächtnisse/Zertifikate, damit der
    nächste Lauf nicht gelöschte Slugs wieder als Phantom zählt.

Nutzung:
    python3 scripts/reserve_janitor.py --dry-run   # Bericht, keine Änderung
    python3 scripts/reserve_janitor.py --purge     # löschen + Gedächtnisse putzen
    python3 scripts/reserve_janitor.py --md        # Markdown-Bericht
    python3 scripts/reserve_janitor.py --selftest  # Sabotageschutz

Exit: 0 = ok · 2 = Selbsttest fehlgeschlagen
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
STATIC = ROOT / "static"
DATA = ROOT / "data"

sys.path.insert(0, str(ROOT / "scripts"))

RE_DRAFT_TRUE = re.compile(r"(?m)^draft:\s*(?:true|yes|1)\s*$")
RE_MACHINE = re.compile(
    r"(?m)^(?:reserve:\s*(?:true|yes|1)|reserve_published:|"
    r"reserve_blocked:|cadence_wait:\s*(?:true|yes|1)|cadence_demoted:)"
)
RE_COVER_LINE = re.compile(r"(?m)^\s*image:\s*[\"']?([^\"'\n#]+)[\"']?")
RE_MD_IMAGE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
RE_MD_LINK = re.compile(r"(?<!!)\[([^\]]+)\]\(([^)]+)\)")
RE_DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")
COVER_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".avif")
TEXT_SCAN_EXTS = (".md", ".html", ".txt", ".toml", ".yaml", ".yml", ".json")


def slug_key(slug: str) -> str:
    return RE_DATE_PREFIX.sub("", slug or "")


def split_frontmatter(text: str) -> tuple[str, str]:
    parts = text.split("---", 2)
    if len(parts) == 3 and parts[0] == "":
        return parts[1], parts[2]
    return "", text


def is_draft(text: str) -> bool:
    fm, _ = split_frontmatter(text)
    return bool(RE_DRAFT_TRUE.search(fm))


def is_machine_owned(text: str, slug: str, ledger_keys: set[str]) -> bool:
    fm, _ = split_frontmatter(text)
    return bool(RE_MACHINE.search(fm)) or slug_key(slug) in ledger_keys


def post_index(posts_dir: Path, slug: str) -> Path:
    return posts_dir / slug / "index.md"


def content_paths(root: Path) -> list[Path]:
    content = root / "content"
    if not content.exists():
        return []
    return sorted(p for p in content.rglob("*.md") if p.is_file())


def frontmatter_image_refs(text: str) -> set[str]:
    fm, body = split_frontmatter(text)
    refs: set[str] = set()
    for m in RE_COVER_LINE.finditer(fm):
        refs.add(m.group(1).strip())
    for m in RE_MD_IMAGE.finditer(body):
        refs.add(m.group(1).strip())
    return {normalisiere_static_ref(r) for r in refs if normalisiere_static_ref(r)}


def normalisiere_static_ref(ref: str) -> str:
    ref = (ref or "").split("?", 1)[0].split("#", 1)[0].strip()
    if not ref:
        return ""
    ref = ref.replace("\\", "/")
    if ref.startswith("/"):
        ref = ref[1:]
    if ref.startswith("static/"):
        ref = ref[len("static/"):]
    return ref


def cover_bases_for(slug: str, text: str) -> set[str]:
    bases = {slug}
    for ref in frontmatter_image_refs(text):
        if ref.startswith("images/covers/"):
            bases.add(Path(ref).stem)
    return {b for b in bases if b}


def referenced_cover_bases(root: Path, excluded: set[Path]) -> set[str]:
    bases: set[str] = set()
    for p in content_paths(root):
        try:
            if p.resolve() in excluded:
                continue
        except OSError:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        for ref in frontmatter_image_refs(text):
            if ref.startswith("images/covers/"):
                bases.add(Path(ref).stem)
    return bases


def matching_cover_files(root: Path, bases: set[str], still_referenced: set[str]) -> list[Path]:
    if not bases:
        return []
    out: list[Path] = []
    covers = root / "static" / "images" / "covers"
    if not covers.exists():
        return []
    doomed = {b for b in bases if b not in still_referenced}
    if not doomed:
        return []
    for p in covers.rglob("*"):
        if p.is_file() and p.suffix.lower() in COVER_EXTS and p.stem in doomed:
            out.append(p)
    return sorted(out)


def matching_audio_files(root: Path, slugs: set[str]) -> list[Path]:
    out: list[Path] = []
    for base in (root / "data" / "audio", root / "static" / "audio"):
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.is_file() and any(p.name.startswith(slug) for slug in slugs):
                out.append(p)
    return sorted(out)


def ledger_keys(root: Path) -> set[str]:
    pfad = root / "data" / "reserve-custody.json"
    try:
        data = json.loads(pfad.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()
    if not isinstance(data, dict):
        return set()
    keys = set(data)
    for k, v in data.items():
        if isinstance(v, dict) and v.get("slug"):
            keys.add(slug_key(str(v["slug"])))
        keys.add(slug_key(k))
    return keys


def triage_rows(root: Path, today: dt.date | None = None, stale_days: int = 21) -> list[dict]:
    import draft_triage as triage  # lokal importierbar, keine PyYAML-Pflicht
    return triage.collect(str(root), today or dt.date.today(), stale_days)


def custody_lage(root: Path) -> dict:
    import reserve_custody as custody
    return custody.bestandsaufnahme(root / "content" / "posts",
                                    pfad=root / "data" / "reserve-custody.json")


def find_targets(root: Path, *, today: dt.date | None = None,
                 stale_days: int = 21) -> tuple[dict[str, dict], list[dict]]:
    """Zielslugs und übersprungene Handentwürfe."""
    posts_dir = root / "content" / "posts"
    keys = ledger_keys(root)
    targets: dict[str, dict] = {}
    skipped: list[dict] = []

    try:
        lage = custody_lage(root)
    except Exception:  # noqa: BLE001 – Triage allein reicht als Fallback
        lage = {"ruecklaeufer": [], "blockiert": []}
    for quelle, grund in (("ruecklaeufer", "Rückläufer"),
                          ("blockiert", "Quarantäne-Blocker")):
        for e in lage.get(quelle, []):
            slug = e.get("slug")
            if slug:
                targets.setdefault(slug, {"slug": slug, "gruende": []})["gruende"].append(grund)

    for row in triage_rows(root, today=today, stale_days=stale_days):
        if row.get("zustand") != "BLOCKIERT":
            continue
        slug = str(row.get("slug") or "")
        if not slug:
            continue
        pfad = root / str(row.get("pfad") or f"content/posts/{slug}/index.md")
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError:
            continue
        if not is_draft(text):
            skipped.append({"slug": slug, "grund": "nicht draft:true"})
            continue
        if not is_machine_owned(text, slug, keys):
            skipped.append({"slug": slug, "grund": "Handentwurf ohne Reserve-/Kadenz-Marker"})
            continue
        eintrag = targets.setdefault(slug, {"slug": slug, "gruende": []})
        blocker = "; ".join(row.get("blocker") or []) or "Triage BLOCKIERT"
        eintrag["gruende"].append("BLOCKIERT: " + blocker[:220])

    # Letzte Sicherung: Nur existierende draft:true-Artikel löschen.
    for slug in list(targets):
        p = post_index(posts_dir, slug)
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            targets.pop(slug, None)
            continue
        if not is_draft(text):
            skipped.append({"slug": slug, "grund": "nicht draft:true"})
            targets.pop(slug, None)
            continue
        if not is_machine_owned(text, slug, keys):
            skipped.append({"slug": slug, "grund": "Handentwurf ohne Reserve-/Kadenz-Marker"})
            targets.pop(slug, None)
            continue
        targets[slug]["pfad"] = str(p.relative_to(root))
        targets[slug]["cover_bases"] = sorted(cover_bases_for(slug, text))
    return targets, skipped


def prune_llms_txt(root: Path, slugs: set[str], *, dry_run: bool) -> int:
    """Stale Einträge aus static/llms.txt entfernen.

    Die Datei wird normalerweise generiert, kann aber nach einer Rückstufung
    eines vormals live gewesenen Artikels noch auf einen Draft zeigen. Wenn der
    Janitor den Artikel löscht, muss diese öffentliche KI-Lesedatei im selben
    Commit sauber werden.
    """
    pfad = root / "static" / "llms.txt"
    if not slugs or not pfad.exists():
        return 0
    try:
        lines = pfad.read_text(encoding="utf-8").splitlines()
    except OSError:
        return 0
    def doomed(line: str) -> bool:
        return any(f"/posts/{slug}/" in line for slug in slugs)
    removed = sum(1 for line in lines if doomed(line))
    if removed and not dry_run:
        kept = [line for line in lines if not doomed(line)]
        pfad.write_text("\n".join(kept).rstrip() + "\n", encoding="utf-8")
    return removed


def unlink_content_references(root: Path, slugs: set[str], *, dry_run: bool) -> int:
    if not slugs:
        return 0
    slug_alt = "|".join(re.escape(s) for s in sorted(slugs, key=len, reverse=True))
    # ../../posts/slug/, /posts/slug/, https://domain/posts/slug/ – Query bleibt egal.
    target_rx = re.compile(r"(?:https?://[^)\s]+)?(?:\.\./\.\./|/)?posts/(?:" +
                           slug_alt + r")/?(?:[?#][^)]*)?$")
    changed = 0
    for p in content_paths(root):
        if any(str(p).endswith(f"content/posts/{s}/index.md") for s in slugs):
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        def repl(m: re.Match) -> str:
            nonlocal changed
            url = m.group(2).strip()
            if target_rx.search(url):
                changed += 1
                return m.group(1)
            return m.group(0)
        neu = RE_MD_LINK.sub(repl, text)
        if neu != text and not dry_run:
            p.write_text(neu, encoding="utf-8")
    return changed


def prune_json_file(path: Path, predicate) -> int:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return 0
    removed = 0
    if isinstance(data, dict):
        for k in list(data.keys()):
            if predicate(k, data[k]):
                del data[k]
                removed += 1
        # Spezialfall reserve-readiness.json
        if path.name == "reserve-readiness.json" and isinstance(data.get("candidates"), list):
            alt = len(data["candidates"])
            data["candidates"] = [r for r in data["candidates"] if not predicate(r.get("slug"), r)]
            removed += alt - len(data["candidates"])
            data["ready"] = sum(1 for r in data["candidates"] if r.get("ready") is True)
            data["pool_size"] = len(data["candidates"])
    else:
        return 0
    # Reihenfolge und Dateistil erhalten: Manifeste sind maschinell, aber ein
    # reiner Löschlauf darf nicht tausend Zeilen Diff durch alphabetisches
    # Umsortieren oder andere Einrückung erzeugen.
    indent = 1 if path.name == "covers_manifest.json" else 2
    path.write_text(json.dumps(data, ensure_ascii=False, indent=indent) + "\n",
                    encoding="utf-8")
    return removed


def prune_state(root: Path, slugs: set[str], cover_bases_deleted: set[str], *, dry_run: bool) -> dict:
    if dry_run:
        return {"custody": 0, "quarantine": 0, "readiness": 0, "covers_manifest": 0}
    keys = {slug_key(s) for s in slugs}

    def by_slug(k, v) -> bool:
        vals = {str(k), slug_key(str(k))}
        if isinstance(v, dict) and v.get("slug"):
            vals.add(str(v["slug"]))
            vals.add(slug_key(str(v["slug"])))
        return bool(vals & (slugs | keys))

    out = {
        "custody": prune_json_file(root / "data" / "reserve-custody.json", by_slug),
        "quarantine": prune_json_file(root / "data" / "reserve-quarantine.json", by_slug),
        "readiness": prune_json_file(root / "data" / "reserve-readiness.json", by_slug),
        "covers_manifest": 0,
    }

    def by_cover(k, v) -> bool:
        return str(k) in cover_bases_deleted or str(k) in slugs

    out["covers_manifest"] = prune_json_file(root / "data" / "covers_manifest.json", by_cover)
    return out


def purge(root: Path = ROOT, *, dry_run: bool = False,
          today: dt.date | None = None, stale_days: int = 21) -> dict:
    root = Path(root)
    targets, skipped = find_targets(root, today=today, stale_days=stale_days)
    slugs = set(targets)
    post_files = {post_index(root / "content" / "posts", s).resolve() for s in slugs}
    all_bases = {b for t in targets.values() for b in t.get("cover_bases", [])}
    still_ref = referenced_cover_bases(root, post_files)
    cover_files = matching_cover_files(root, all_bases, still_ref)
    audio_files = matching_audio_files(root, slugs)
    links_removed = unlink_content_references(root, slugs, dry_run=dry_run)
    llms_removed = prune_llms_txt(root, slugs, dry_run=dry_run)

    if not dry_run:
        for slug in sorted(slugs):
            d = root / "content" / "posts" / slug
            if d.exists():
                shutil.rmtree(d)
        for p in cover_files + audio_files:
            try:
                p.unlink()
            except FileNotFoundError:
                pass
        state = prune_state(root, slugs, {p.stem for p in cover_files}, dry_run=False)
    else:
        state = prune_state(root, slugs, {p.stem for p in cover_files}, dry_run=True)

    return {
        "deleted_slugs": sorted(slugs),
        "targets": [targets[s] for s in sorted(slugs)],
        "skipped": skipped,
        "cover_files": [str(p.relative_to(root)) for p in cover_files],
        "audio_files": [str(p.relative_to(root)) for p in audio_files],
        "links_removed": links_removed,
        "llms_removed": llms_removed,
        "state_pruned": state,
        "dry_run": dry_run,
    }


def markdown(report: dict) -> str:
    mode = "Trockenlauf" if report.get("dry_run") else "Bereinigung"
    lines = ["", f"## 🧹 Content-Reserve-Janitor – {mode}", "",
             f"- **Gelöschte Artikel:** {len(report['deleted_slugs'])}",
             f"- **Cover-Dateien:** {len(report['cover_files'])}",
             f"- **Audio-Artefakte:** {len(report['audio_files'])}",
             f"- **Markdown-Links entlinkt:** {report['links_removed']}",
             f"- **llms.txt-Einträge entfernt:** {report.get('llms_removed', 0)}"]
    if report["deleted_slugs"]:
        lines += ["", "### Entfernt"]
        for t in report["targets"]:
            grund = "; ".join(dict.fromkeys(t.get("gruende") or []))
            lines.append(f"- `{t['slug']}` – {grund}")
    if report.get("skipped"):
        lines += ["", "### Bewusst übersprungen"]
        for s in report["skipped"]:
            lines.append(f"- `{s.get('slug')}` – {s.get('grund')}")
    pruned = report.get("state_pruned") or {}
    if any(pruned.values()):
        lines += ["", "### Gedächtnisse bereinigt"]
        for k, v in sorted(pruned.items()):
            if v:
                lines.append(f"- `{k}`: {v}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Selbsttest
# ---------------------------------------------------------------------------
def _write_post(posts: Path, slug: str, fm: str, body: str = "Text") -> Path:
    d = posts / slug
    d.mkdir(parents=True, exist_ok=True)
    p = d / "index.md"
    p.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")
    return p


def run_selftest() -> int:
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        posts = root / "content" / "posts"
        covers = root / "static" / "images" / "covers"
        (root / "data" / "audio").mkdir(parents=True)
        covers.mkdir(parents=True)
        for sub in ("", "360", "webp", "avif/360"):
            (covers / sub).mkdir(parents=True, exist_ok=True)

        body_ok = ("[A](../../posts/live-a/) und [B](../../posts/live-b/)\n" +
                   "\n".join(f"## Abschnitt {i}\nNutzwert mit Zahlen und Beispielen." for i in range(6)) * 90)
        _write_post(posts, "live-a", 'title: "Live A"\ndate: 2026-09-01\ndraft: false', body_ok)
        _write_post(posts, "live-b", 'title: "Live B"\ndate: 2026-09-01\ndraft: false', body_ok)
        _write_post(posts, "rueck", 'title: "Rück"\ndate: 2026-09-01\ndraft: true\nreserve_published: 2026-09-01\ncover:\n  image: "images/covers/rueck.jpg"', body_ok)
        _write_post(posts, "blocked", 'title: "Block"\ndate: 2026-09-01\ndraft: true\nreserve: true\ncover:\n  image: "images/covers/blocked.jpg"', "zu kurz")
        _write_post(posts, "manual", 'title: "Hand"\ndate: 2026-09-01\ndraft: true', "zu kurz")
        _write_post(posts, "live-old-reserve", 'title: "Alt"\ndate: 2026-09-01\ndraft: false\nreserve_published: 2026-09-01', body_ok)
        _write_post(posts, "ref", 'title: "Ref"\ndate: 2026-09-01\ndraft: false',
                    "Siehe [Rück](../../posts/rueck/) und [Block](../../posts/blocked/).")
        _write_post(posts, "shared", 'title: "Shared"\ndate: 2026-09-01\ndraft: false\ncover:\n  image: "images/covers/shared.jpg"', body_ok)
        _write_post(posts, "doomed-shared", 'title: "Doomed Shared"\ndate: 2026-09-01\ndraft: true\nreserve_published: 2026-09-01\ncover:\n  image: "images/covers/shared.jpg"', body_ok)

        for base in ("rueck", "blocked", "shared"):
            for p in (covers / f"{base}.jpg", covers / "360" / f"{base}.jpg",
                      covers / "webp" / f"{base}.webp", covers / "avif" / "360" / f"{base}.avif"):
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text("img", encoding="utf-8")
        (root / "data" / "audio" / "rueck.chunks.json").write_text("{}\n", encoding="utf-8")
        (root / "data" / "reserve-custody.json").write_text(json.dumps({
            "rueck": {"slug": "rueck", "zustand": "ruecklaeufer"},
            "blocked": {"slug": "blocked", "zustand": "pool"},
            "doomed-shared": {"slug": "doomed-shared", "zustand": "ruecklaeufer"},
        }), encoding="utf-8")
        (root / "data" / "reserve-quarantine.json").write_text(json.dumps({
            "blocked": {"hits": 2}, "other": {"hits": 1}
        }), encoding="utf-8")
        (root / "data" / "reserve-readiness.json").write_text(json.dumps({
            "target": 2, "ready": 2, "pool_size": 2,
            "candidates": [{"slug": "blocked", "ready": True},
                           {"slug": "keep", "ready": True}],
        }), encoding="utf-8")
        (root / "data" / "covers_manifest.json").write_text(json.dumps({
            "rueck": {}, "blocked": {}, "shared": {}, "keep": {}
        }), encoding="utf-8")
        (root / "static").mkdir(exist_ok=True)
        (root / "static" / "llms.txt").write_text(
            "- [Rück](https://example.org/posts/rueck/): alt\n"
            "- [Keep](https://example.org/posts/keep/): bleibt\n",
            encoding="utf-8")

        dry = purge(root, dry_run=True, today=dt.date(2026, 9, 26))
        if set(dry["deleted_slugs"]) != {"rueck", "blocked", "doomed-shared"}:
            errors.append(f"Trockenlauf-Ziele falsch: {dry['deleted_slugs']}")
        if not (posts / "rueck" / "index.md").exists():
            errors.append("Trockenlauf hat gelöscht")

        rep = purge(root, dry_run=False, today=dt.date(2026, 9, 26))
        for slug in ("rueck", "blocked", "doomed-shared"):
            if (posts / slug).exists():
                errors.append(f"{slug} wurde nicht gelöscht")
        for slug in ("manual", "live-old-reserve", "shared"):
            if not (posts / slug / "index.md").exists():
                errors.append(f"{slug} wurde fälschlich gelöscht")
        ref = (posts / "ref" / "index.md").read_text(encoding="utf-8")
        if "../../posts/rueck/" in ref or "../../posts/blocked/" in ref:
            errors.append("Links auf gelöschte Slugs wurden nicht entlinkt")
        if "[Rück]" in ref or "[Block]" in ref:
            errors.append("Link-Markdown blieb halb stehen")
        if (covers / "rueck.jpg").exists() or (covers / "360" / "blocked.jpg").exists():
            errors.append("unreferenzierte Cover-Varianten wurden nicht gelöscht")
        if not (covers / "shared.jpg").exists():
            errors.append("referenziertes Shared-Cover wurde gelöscht")
        if (root / "data" / "audio" / "rueck.chunks.json").exists():
            errors.append("Audio-Artefakt wurde nicht gelöscht")
        llms = (root / "static" / "llms.txt").read_text(encoding="utf-8")
        if "/posts/rueck/" in llms or "/posts/keep/" not in llms:
            errors.append(f"llms.txt wurde nicht gezielt bereinigt: {llms!r}")
        custody = json.loads((root / "data" / "reserve-custody.json").read_text(encoding="utf-8"))
        if any(k in custody for k in ("rueck", "blocked", "doomed-shared")):
            errors.append(f"Custody-Ledger nicht bereinigt: {custody}")
        readiness = json.loads((root / "data" / "reserve-readiness.json").read_text(encoding="utf-8"))
        if any(r.get("slug") == "blocked" for r in readiness.get("candidates", [])):
            errors.append("Readiness-Zertifikat enthält gelöschten Kandidaten")
        if readiness.get("ready") != 1 or readiness.get("pool_size") != 1:
            errors.append(f"Readiness-Zähler nicht neu berechnet: {readiness}")
        manifest = json.loads((root / "data" / "covers_manifest.json").read_text(encoding="utf-8"))
        if "rueck" in manifest or "blocked" in manifest:
            errors.append(f"Cover-Manifest nicht bereinigt: {manifest}")
        if "shared" not in manifest:
            errors.append("Shared-Cover wurde aus Manifest entfernt")
        if rep["state_pruned"].get("quarantine") != 1:
            errors.append(f"Quarantäne-Zähler nicht bereinigt: {rep['state_pruned']}")

    if errors:
        print("🛑 reserve_janitor-Selbsttest FEHLGESCHLAGEN:")
        for e in errors:
            print(f"   - {e}")
        return 2
    print("✅ reserve_janitor-Selbsttest grün (Rückläufer/Blocker gelöscht, Handentwurf/Live geschützt, Links, llms.txt, Cover, Audio und Gedächtnisse bereinigt).")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Rückläufer und blockierte Reserve-Entwürfe löschen")
    ap.add_argument("--purge", action="store_true", help="wirklich löschen")
    ap.add_argument("--dry-run", action="store_true", help="nur berichten")
    ap.add_argument("--md", action="store_true", help="Markdown-Bericht")
    ap.add_argument("--json", action="store_true", help="JSON-Bericht")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--stale-days", type=int, default=21)
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    dry = args.dry_run or not args.purge
    rep = purge(ROOT, dry_run=dry, stale_days=args.stale_days)
    if args.json:
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    elif args.md:
        print(markdown(rep))
    else:
        verb = "würde löschen" if dry else "gelöscht"
        print(f"Reserve-Janitor: {len(rep['deleted_slugs'])} Artikel {verb}, "
              f"{len(rep['cover_files'])} Cover, {len(rep['audio_files'])} Audio, "
              f"{rep['links_removed']} Links entlinkt, "
              f"{rep.get('llms_removed', 0)} llms.txt-Zeilen entfernt.")
        for slug in rep["deleted_slugs"]:
            print(f"   - {slug}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
