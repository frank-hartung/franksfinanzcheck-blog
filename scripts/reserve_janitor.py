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

REPARATUR 05.10.2026 (Vorgang WF-B594, Bot-Watchdog #594, Run 37347512536)
---------------------------------------------------------------------------
Dieses Skript war die Ursache des Dauer-Tickets „Content-Reserve niedrig".
Am 05.10. löschte es in EINEM Lauf acht vollständige Entwürfe (1.815 Zeilen
Artikeltext, 24 Cover-Dateien, Commit c56382b) – darunter sechs Kandidaten,
die das Zertifikat 15 Minuten zuvor mit ausschließlich HEILBAREN Funden
abgelehnt hatte („Zeichenlänge", „Faktenfrische – Erstrecherche"). Drei
Konstruktionsfehler wirkten zusammen:

  1. LÖSCHEN VOR HEILEN. Der Janitor läuft als Stufe 0a, die Heiler-Kette
     erst als Stufe 2. Was die Triage morgens als BLOCKIERT sah, war abends
     verschwunden – bevor irgendein Heiler es anfassen konnte.
  2. JEDER MASCHINEN-ENTWURF IST PER KONSTRUKTION BLOCKIERT. „laenge: < Soll"
     trifft jeden Rohtext vor der Verlängerung, „interne links: < 2" jeden
     Kandidaten, weil die Reserve-Kette den Internal-Linker nicht fuhr. Die
     Löschliste war damit praktisch die Produktionsliste der Nacht.
  3. DIE SCHWÄCHERE FOLGE HATTE DEN STÄRKEREN BEWEIS. `reserve_quarantine`
     nimmt nur die FAHNE (reversibel) – und verlangt zwei Läufe mit
     demselben Fund. Der Janitor LÖSCHT (unwiderruflich) – und verlangte
     eine einzige Sichtung, auch bei einem Entwurf von vor zehn Minuten.

Seither gilt der Vertrag „Löschen braucht einen Beweis":

  * KLASSE    Nur Hindernisse, die laut `reserve_blocker_klassen.py`
              unheilbar sind, rechtfertigen eine Löschung. Ein einziger
              heilbarer, menschlicher oder unbekannter Befund verschont den
              Entwurf (fail-closed).
  * BELEG     Derselbe Befund muss in RESERVE_JANITOR_HITS (Default 2)
              VERSCHIEDENEN Läufen aufgetreten sein – gezählt in
              data/reserve-janitor-state.json, Lauf-Identität wie bei der
              Quarantäne (GITHUB_RUN_ID).
  * KARENZ    Kein Entwurf wird in seinen ersten RESERVE_JANITOR_KARENZ_TAGE
              (Default 2) Tagen gelöscht. Produktion und Veredelung müssen
              mindestens einen vollen Zyklus Zeit gehabt haben.
  * ALTERUNG  Ausgemusterte Entwürfe (`reserve_blocked`) sind kein Müll,
              sondern Material: Sie verschwinden erst nach
              RESERVE_JANITOR_AUSMUSTERUNG_TAGE (Default 30) Tagen – und nie,
              wenn ihr Fund einem Menschen gehört (offene YMYL-Freigabe).
  * BERICHT   Jeder verschonte Entwurf steht mit Grund im Bericht. Wer
              verschont, muss sagen warum – sonst wächst der Vorrat
              unbemerkt zur Halde.

Rückläufer (einmal veröffentlicht, danach wieder Entwurf) bleiben wie bisher
Sofort-Löschfälle: Ihr Inhalt lebt live weiter, der Entwurf ist eine Kopie.

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
    python3 scripts/reserve_janitor.py --geschont  # wer wurde warum verschont?
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
import reserve_blocker_klassen as bk  # noqa: E402 – SSOT der Löschklassen
import reserve_pool as rp  # noqa: E402 – Nachweis/Rückholung (#610)
#     Absichtlich auf Modulebene: Im Selbsttest ist die Kalender-Uhr ersetzt
#     (Uhr-Zwang). Ein späterer Import würde `datetime` aus dem Shim binden –
#     und die Rückholung läse danach dauerhaft eine fremde Uhr.

# Beweislast des Löschens (WF-B594). Alle drei Schwellen sind per Umgebung
# verstellbar, aber nie abschaltbar: `hits_limit()` bleibt >= 1.
JANITOR_STATE = Path("data") / "reserve-janitor-state.json"
HITS_DEFAULT = 2          # verschiedene Läufe mit demselben unheilbaren Fund
KARENZ_DEFAULT = 2        # Tage Schonfrist für junge Entwürfe
AUSMUSTERUNG_DEFAULT = 30  # Tage, die ausgemusterter Text als Material bleibt

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


def hits_limit() -> int:
    """Wie viele VERSCHIEDENE Läufe denselben Befund belegen müssen."""
    try:
        return max(1, int(os.environ.get("RESERVE_JANITOR_HITS")
                          or HITS_DEFAULT))
    except ValueError:
        return HITS_DEFAULT


def karenz_tage() -> int:
    """Schonfrist für junge Entwürfe (in Tagen)."""
    try:
        return max(0, int(os.environ.get("RESERVE_JANITOR_KARENZ_TAGE")
                          or KARENZ_DEFAULT))
    except ValueError:
        return KARENZ_DEFAULT


def ausmusterung_tage() -> int:
    """Wie lange ein ausgemusterter Entwurf als Material liegen bleibt."""
    try:
        return max(0, int(os.environ.get("RESERVE_JANITOR_AUSMUSTERUNG_TAGE")
                          or AUSMUSTERUNG_DEFAULT))
    except ValueError:
        return AUSMUSTERUNG_DEFAULT


def _lauf_kennung() -> str:
    """Lauf-Identität – dieselbe Quelle wie die Quarantäne (#349)."""
    try:
        import reserve_quarantine as rq
        return rq.lauf_kennung()
    except Exception:  # noqa: BLE001 – Zähler darf nie am Import scheitern
        run_id = (os.environ.get("GITHUB_RUN_ID") or "").strip()
        return (f"run:{run_id}" if run_id
                else "lokal:" + dt.date.today().isoformat())


def _signatur(text: str) -> str:
    """Stabile Fund-Signatur – dieselbe Quelle wie die Quarantäne."""
    try:
        import reserve_quarantine as rq
        return rq.signatur(text)
    except Exception:  # noqa: BLE001
        return re.sub(r"\d+", "<n>", (text or "").lower())[:200]


def lade_zaehler(root: Path) -> dict:
    try:
        data = json.loads((root / JANITOR_STATE).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def schreibe_zaehler(root: Path, state: dict) -> None:
    pfad = root / JANITOR_STATE
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(state, ensure_ascii=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")


def _zaehle(state: dict, slug: str, signatur: str, grund: str,
            run_key: str, jetzt: "dt.datetime | None" = None) -> int:
    """Zählt denselben Befund je LAUF genau einmal (Vertrag wie #349).

    `jetzt` kommt vom Aufrufer und ist im Zweifel aus dem Urteils-Tag
    abgeleitet (Mittag UTC), nicht aus der Wanduhr. Grund: Der eigene
    `--selftest` läuft unter einer STRIKTEN Uhr (scripts/selftest_clock.py) –
    ein echter Uhr-Lesezugriff hier wäre ein Uhr-Verstoß, und der Zählerstand
    wäre für denselben Tag nicht reproduzierbar (07.10.2026: als die
    Uhr-Probe lernte, Alias-Importe umzubiegen, flog genau das auf).
    """
    stamp = (jetzt or dt.datetime.now(dt.timezone.utc)).strftime("%Y-%m-%dT%H:%M:%SZ")
    eintrag = state.get(slug)
    if not isinstance(eintrag, dict) or eintrag.get("signatur") != signatur:
        eintrag = {"signatur": signatur, "hits": 0, "first": stamp}
    if eintrag.get("lauf") != run_key:
        eintrag["hits"] = int(eintrag.get("hits", 0)) + 1
        eintrag["lauf"] = run_key
        laeufe = [l for l in (eintrag.get("laeufe") or []) if l != run_key]
        laeufe.append(run_key)
        eintrag["laeufe"] = laeufe[-5:]
    eintrag["last"] = stamp
    eintrag["grund"] = grund[:220]
    state[slug] = eintrag
    return int(eintrag["hits"])


def _blocked_grund(text: str) -> str:
    m = re.search(r'(?m)^reserve_blocked:\s*"?(.*?)"?\s*$', text)
    return (m.group(1).strip() if m else "").strip()


def _blocked_alter(text: str, today: dt.date) -> int | None:
    m = re.search(r"(?m)^reserve_blocked_at:\s*\"?(\d{4}-\d{2}-\d{2})", text)
    if not m:
        return None
    try:
        return (today - dt.date.fromisoformat(m.group(1))).days
    except ValueError:
        return None


def find_targets(root: Path, *, today: dt.date | None = None,
                 stale_days: int = 21, run_key: str | None = None,
                 zaehler_schreiben: bool = True
                 ) -> tuple[dict[str, dict], list[dict], list[dict]]:
    """Zielslugs, übersprungene Handentwürfe und VERSCHONTE mit Begründung.

    Seit WF-B594 ist das die Stelle, an der entschieden wird, ob Text
    vernichtet werden darf. Die Entscheidung ist dreifach abgesichert
    (Klasse → Beleg → Karenz) und in jedem Fall begründet.
    """
    today = today or dt.date.today()
    posts_dir = root / "content" / "posts"
    keys = ledger_keys(root)
    targets: dict[str, dict] = {}
    skipped: list[dict] = []
    geschont: list[dict] = []
    run_key = run_key or _lauf_kennung()
    state = lade_zaehler(root)
    gesehen: set[str] = set()
    limit = hits_limit()
    karenz = karenz_tage()

    try:
        lage = custody_lage(root)
    except Exception:  # noqa: BLE001 – Triage allein reicht als Fallback
        lage = {"ruecklaeufer": [], "blockiert": []}

    # 1) Rückläufer: Der Inhalt lebt live weiter, der Entwurf ist die Kopie.
    #    Sofort-Löschung (unverändert seit #24) – ABER nur mit NACHWEIS
    #    (WF-54C4 #610, 07.10.2026): `reserve_published` + `draft: true` allein
    #    belegt gar nichts. Am 05.10.2026 wurde der nachgeschobene Reserve-
    #    Artikel um 22:41 vom Gate zurückgestuft – nie ausgeliefert – und in
    #    der Nacht als „Rückläufer“ vernichtet. Deshalb: ein LIVE-Artikel mit
    #    demselben Thema (Titel oder Slug-Rumpf) muss die Veröffentlichung
    #    belegen; fehlt er, ist der Entwurf Material und wird zurückgeholt.
    for e in lage.get("ruecklaeufer", []):
        slug = e.get("slug")
        if slug:
            targets.setdefault(slug, {"slug": slug, "gruende": []}
                               )["gruende"].append(
                f"Rückläufer (belegt durch {e.get('live_zwilling')})")

    # 1b) Rückläufer-VERDACHT ohne Nachweis (#610): kein Löschziel.
    #     Fail-closed zugunsten des Textes: Wer nicht beweisen kann, dass der
    #     Inhalt öffentlich lebt, darf ihn nicht vernichten. Diese Entwürfe
    #     kehren in den Vorrat zurück (`zurueck_in_den_pool`, in `purge`)
    #     und stehen mit Grund im Bericht.
    for e in lage.get("ruecklaeufer_ohne_nachweis", []):
        slug = e.get("slug")
        if not slug:
            continue
        geschont.append({
            "slug": slug, "quelle": "ruecklaeufer",
            "klasse": "ohne-nachweis",
            "grund": ("kein LIVE-Zwilling für die Veröffentlichung nachweisbar – "
                      "kein Löschgrund, Material kehrt in den Vorrat zurück "
                      "(#610)"),
            "befund": "reserve_published + draft: true, aber kein LIVE-Artikel "
                      "mit gleichem Thema"})

    # 2) Ausgemusterte (`reserve_blocked`, gesetzt von reserve_quarantine):
    #    Material auf Zeit. Gelöscht wird erst nach der Alterungsfrist – und
    #    nie, wenn der Fund heilbar ist oder einem Menschen gehört.
    for e in lage.get("blockiert", []):
        slug = e.get("slug")
        if not slug:
            continue
        p = post_index(posts_dir, slug)
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        grund = _blocked_grund(text) or "ohne Begründung ausgemustert"
        loeschbar, bewertung = bk.gate_befund_loeschbar(grund)
        alter = _blocked_alter(text, today)
        if not loeschbar and (alter is None or alter < ausmusterung_tage()):
            geschont.append({
                "slug": slug, "quelle": "quarantäne",
                "klasse": bewertung["klasse"],
                "grund": (f"ausgemustert seit {alter if alter is not None else '?'} "
                          f"Tag(en) – {bewertung['grund']}"),
                "befund": grund[:160]})
            continue
        if bewertung["klasse"] == bk.MENSCHLICH:
            geschont.append({
                "slug": slug, "quelle": "quarantäne",
                "klasse": bewertung["klasse"],
                "grund": bewertung["grund"], "befund": grund[:160]})
            continue
        targets.setdefault(slug, {"slug": slug, "gruende": []}
                           )["gruende"].append(f"Quarantäne-Blocker: {grund[:160]}")

    # 3) Triage-BLOCKIERT – der Pfad, der #594 erzeugt hat.
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
            skipped.append({"slug": slug,
                            "grund": "Handentwurf ohne Reserve-/Kadenz-Marker"})
            continue
        blocker = list(row.get("blocker") or [])
        loeschbar, bewertet = bk.loeschbar(blocker)
        if not loeschbar:
            schoner = next((e for e in bewertet
                            if e["klasse"] != bk.UNHEILBAR), None)
            geschont.append({
                "slug": slug, "quelle": "triage",
                "klasse": (schoner or {}).get("klasse", "ohne Hindernis"),
                "grund": (schoner or {}).get(
                    "grund", "kein Hindernis – nichts zu löschen"),
                "befund": "; ".join(blocker)[:200]})
            continue
        # Ab hier: ausschließlich unheilbare Befunde. Jetzt erst Beleg + Karenz.
        signatur = _signatur("; ".join(sorted(blocker)))
        gesehen.add(slug)
        hits = _zaehle(state, slug, signatur,
                       "; ".join(blocker), run_key,
                       jetzt=dt.datetime.combine(today, dt.time(12, 0),
                                                 tzinfo=dt.timezone.utc))
        alter = row.get("tage_seit_letzte_aenderung")
        if isinstance(alter, int) and alter < karenz:
            geschont.append({
                "slug": slug, "quelle": "triage", "klasse": "karenz",
                "grund": (f"erst {alter} Tag(e) alt – Karenz {karenz} Tage: "
                          "Produktion und Veredelung brauchen mindestens "
                          "einen vollen Zyklus"),
                "befund": "; ".join(blocker)[:200]})
            continue
        if hits < limit:
            geschont.append({
                "slug": slug, "quelle": "triage", "klasse": "beleg",
                "grund": (f"unheilbarer Befund, aber erst {hits}/{limit} "
                          "Läufe belegt – Löschen ist unwiderruflich"),
                "befund": "; ".join(blocker)[:200]})
            continue
        eintrag = targets.setdefault(slug, {"slug": slug, "gruende": []})
        eintrag["gruende"].append(
            f"BLOCKIERT ({hits}/{limit} Läufe, unheilbar): "
            + "; ".join(blocker)[:200])

    # Zähler aufräumen: Wer nicht mehr unheilbar blockiert ist, verliert ihn.
    for slug in [s for s in state if s not in gesehen]:
        state.pop(slug, None)
    if zaehler_schreiben:
        schreibe_zaehler(root, state)

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
    return targets, skipped, geschont


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
    # Nichts entfernt = nichts schreiben (WF-B594): Ein reiner Nicht-Lösch-
    # Lauf hat am 05.10. allein durch das Zurückschreiben von
    # covers_manifest.json einen Diff erzeugt (Zeilenende). Stiller Churn auf
    # maschinellen Manifesten kostet Rebase-Konflikte im Nachtlauf.
    if not removed:
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
          today: dt.date | None = None, stale_days: int = 21,
          run_key: str | None = None) -> dict:
    root = Path(root)
    # Der Trockenlauf darf den Beleg-Zähler nicht hochdrehen – sonst würde
    # ein Bericht die spätere Löschung herbeirechnen (WF-B594).
    targets, skipped, geschont = find_targets(
        root, today=today, stale_days=stale_days, run_key=run_key,
        zaehler_schreiben=not dry_run)
    slugs = set(targets)
    post_files = {post_index(root / "content" / "posts", s).resolve() for s in slugs}
    all_bases = {b for t in targets.values() for b in t.get("cover_bases", [])}
    still_ref = referenced_cover_bases(root, post_files)
    cover_files = matching_cover_files(root, all_bases, still_ref)
    audio_files = matching_audio_files(root, slugs)
    links_removed = unlink_content_references(root, slugs, dry_run=dry_run)
    llms_removed = prune_llms_txt(root, slugs, dry_run=dry_run)

    # WF-54C4 #610: Nicht ausgelieferten Nachschub zurück in den Vorrat holen.
    # Die Rettung ist die *Umkehrung* der Löschung: Sie braucht keinen Beweis
    # gegen den Text, sondern stellt die Kandidaten-Fahne wieder her. Nur im
    # Echtlauf; der Trockenlauf meldet die Rettung nur.
    wiederhergestellt: list[str] = []
    stamp_tag = today or dt.date.today()
    for e in (geschont or []):
        if e.get("klasse") != "ohne-nachweis" or e.get("quelle") != "ruecklaeufer":
            continue
        slug = str(e.get("slug") or "")
        if not slug or dry_run:
            continue
        try:
            index = post_index(root / "content" / "posts", slug)
            stamp = f"{stamp_tag.isoformat()}T12:00:00Z"
            ok, meldung = rp.zurueck_in_den_pool(
                index, "Reserve-Janitor #610: kein LIVE-Nachweis – Material erhalten",
                posts_dir=root / "content" / "posts", when=stamp,
                history_path=root / "data" / "reserve-history.jsonl")
        except Exception as exc:  # noqa: BLE001 – Rettung darf den Lauf nie kippen
            ok, meldung = False, f"Rettung nicht ausführbar: {exc}"
        print(("  ♻️  " if ok else "  ⚠ ") + meldung)
        if ok:
            wiederhergestellt.append(slug)

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
        "geschont": sorted(geschont, key=lambda e: str(e.get("slug"))),
        "wiederhergestellt": sorted(wiederhergestellt),
        "regeln": {"hits": hits_limit(), "karenz_tage": karenz_tage(),
                   "ausmusterung_tage": ausmusterung_tage()},
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
    wieder = report.get("wiederhergestellt") or []
    if wieder:
        lines += ["", f"### ♻️ Zurück in den Vorrat (#610, {len(wieder)})", "",
                  "Kein LIVE-Nachweis für die Veröffentlichung – Material bleibt "
                  "erhalten statt als „Rückläufer“ vernichtet zu werden.", ""]
        for slug in wieder:
            lines.append(f"- `{slug}` – reserve_published entfernt, Fahne gesetzt")
    geschont = report.get("geschont") or []
    regeln = report.get("regeln") or {}
    if geschont:
        lines += ["", f"### 🛟 Geschont (Material, {len(geschont)})", "",
                  ("Löschen braucht einen Beweis: unheilbare Klasse, "
                   f"{regeln.get('hits', HITS_DEFAULT)} Läufe Beleg und "
                   f"{regeln.get('karenz_tage', KARENZ_DEFAULT)} Tage Karenz "
                   "(WF-B594)."), ""]
        for s in geschont:
            befund = (s.get("befund") or "").strip()
            zusatz = f" · Befund: {befund}" if befund else ""
            lines.append(f"- `{s.get('slug')}` – **{s.get('klasse')}**: "
                         f"{s.get('grund')}{zusatz}")
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


try:  # Determinismus-Garantie (scripts/selftest_clock.py)
    from selftest_clock import (MITTAG as _MITTAG,  # type: ignore
                                MODUS_STRIKT as _UHR_STRIKT,
                                stempel as _stempel, uhr as _uhr)
except Exception:  # noqa: BLE001
    _MITTAG = _UHR_STRIKT = _stempel = _uhr = None


# Sechs Probetage statt „heute" – Schalttag, Jahreswechsel, Monatsenden.
PROBETAGE = (dt.date(2026, 3, 1), dt.date(2024, 2, 29), dt.date(2026, 12, 24),
             dt.date(2027, 1, 1), dt.date(2026, 6, 30), dt.date(2025, 10, 5))


def _szenario(heute: dt.date) -> list[str]:
    """Ein vollständiger Lösch-Durchlauf gegen ein VORGEGEBENES Testdatum.

    DETERMINISMUS-VERTRAG (Nachzug 05.10.2026, WF-B594): Die erste Fassung
    las `dt.date.today()` und ließ die Fixtures mit der echten Wanduhr
    altern. Unter der CI-Probe mit vorgestellter Uhr war der frisch
    geschriebene Entwurf plötzlich 97 Tage alt, die Karenz griff nicht mehr
    und der Prüffall „Karenz schont junges Material" fiel durch – eine
    Zeitbombe in genau der Wache, die vor unwiderruflichem Löschen schützt.
    Jedes Dateialter wird deshalb ABSOLUT auf das Testdatum gestempelt.
    """
    errors: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        posts = root / "content" / "posts"
        covers = root / "static" / "images" / "covers"
        (root / "data" / "audio").mkdir(parents=True)
        covers.mkdir(parents=True)
        for sub in ("", "360", "webp", "avif/360"):
            (covers / sub).mkdir(parents=True, exist_ok=True)

        # Fixture-Datum RELATIV zum Testdatum (nie "2026-09-01"): ein
        # Artikel, der aus Sicht des Testtages in der Zukunft liegt, ist für
        # die Triage nicht fällig – dann prüft der Selbsttest nichts mehr.
        d0 = (heute - dt.timedelta(days=5)).isoformat()
        body_ok = ("[A](../../posts/live-a/) und [B](../../posts/live-b/)\n" +
                   "\n".join(f"## Abschnitt {i}\nNutzwert mit Zahlen und Beispielen." for i in range(6)) * 90)
        _write_post(posts, "live-a", f'title: "Live A"\ndate: {d0}\ndraft: false', body_ok)
        _write_post(posts, "live-b", f'title: "Live B"\ndate: {d0}\ndraft: false', body_ok)
        _write_post(posts, "rueck", f'title: "Rück"\ndate: {d0}\ndraft: true\nreserve_published: {d0}\ncover:\n  image: "images/covers/rueck.jpg"', body_ok)
        # „blocked" = echter Torso: vollständiger Körper, aber OHNE Titel.
        # Unheilbar (die Kette erfindet keine redaktionelle Aussage), also
        # löschbar – aber erst mit Beleg aus zwei Läufen (WF-B594).
        _write_post(posts, "blocked",
                    f'title: ""\ndate: {d0}\nlastmod: {d0}\n'
                    'description: "Eine ordentliche Beschreibung mit genug '
                    'Zeichen fuer das Meta-Gate der Reserve dieses Blogs."\n'
                    'draft: true\nreserve: true\ncover:\n'
                    '  image: "images/covers/blocked.jpg"', body_ok)
        # „heilbar-kurz" = der Realfall aus #594: Maschinen-Entwurf, dem nur
        # Länge, Struktur und interne Links fehlen. Muss ÜBERLEBEN.
        _write_post(posts, "heilbar-kurz", f'title: "Kurz aber heilbar"\ndate: {d0}\nlastmod: {d0}\ndescription: "Eine ordentliche Beschreibung mit genug Zeichen fuer das Meta-Gate der Reserve."\ndraft: true\nreserve: true\ncover:\n  image: "images/covers/heilbar-kurz.jpg"', "## Nur ein Anfang\nNoch zu kurz, aber heilbar.")
        _write_post(posts, "manual", f'title: "Hand"\ndate: {d0}\ndraft: true', "zu kurz")
        _write_post(posts, "live-old-reserve", f'title: "Alt"\ndate: {d0}\ndraft: false\nreserve_published: {d0}', body_ok)
        _write_post(posts, "ref", f'title: "Ref"\ndate: {d0}\ndraft: false',
                    "Siehe [Rück](../../posts/rueck/) und [Block](../../posts/blocked/).")
        _write_post(posts, "shared", f'title: "Shared"\ndate: {d0}\ndraft: false\ncover:\n  image: "images/covers/shared.jpg"', body_ok)
        _write_post(posts, "doomed-shared", f'title: "Doomed Shared"\ndate: {d0}\ndraft: true\nreserve_published: {d0}\ncover:\n  image: "images/covers/shared.jpg"', body_ok)
        # WF-54C4 #610: Der LIVE-NACHWEIS für einen Rückläufer. Ohne ihn wird
        # nicht gelöscht, sondern zurückgeholt (nächste Fixture).
        _write_post(posts, "live-rueck", f'title: "Rück"\ndate: {d0}\ndraft: false', body_ok)
        _write_post(posts, "live-doomed", f'title: "Doomed Shared"\ndate: {d0}\ndraft: false', body_ok)
        # Der reale #610-Fall: nachgeschobener Reserve-Artikel, vom späten Gate
        # zurückgestuft, NIE ausgeliefert. reserve_published + draft: true ist
        # hier ein VERDACHT ohne Beweis – er muss überleben und in den Vorrat
        # zurückkehren. Frühere Fassung des Janitors hätte ihn vernichtet.
        _write_post(posts, "rueck-ohne-nachweis", f'title: "Ohne Nachweis"\ndate: {d0}\ndraft: true\nreserve_published: {d0}\ncadence_grund: "publish-gate: Lesbarkeits-Gate"', body_ok)

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

        # Alter ABSOLUT stempeln: Die Entwürfe sind am Testtag entstanden –
        # unabhängig davon, welcher Kalendertag beim Lauf gerade herrscht.
        for index in posts.glob("*/index.md"):
            _stempel(str(index), heute)

        umwelt = {k: os.environ.get(k) for k in
                  ("RESERVE_JANITOR_HITS", "RESERVE_JANITOR_KARENZ_TAGE",
                   "RESERVE_JANITOR_AUSMUSTERUNG_TAGE")}
        os.environ["RESERVE_JANITOR_HITS"] = "2"
        os.environ["RESERVE_JANITOR_KARENZ_TAGE"] = "2"
        try:
            # (1) KARENZ: Die Entwürfe sind heute entstanden. Ein unheilbarer
            #     Quelldefekt allein reicht nicht – erst nach der Schonfrist.
            jung = purge(root, dry_run=True, today=heute, run_key="run:0")
            if "blocked" in jung["deleted_slugs"]:
                errors.append("Karenz verletzt: junger Entwurf wurde zum Ziel")
            if not any(g["slug"] == "blocked" and g["klasse"] == "karenz"
                       for g in jung["geschont"]):
                errors.append(f"Karenz nicht begründet gemeldet: {jung['geschont']}")

            os.environ["RESERVE_JANITOR_KARENZ_TAGE"] = "0"

            # (2) TROCKENLAUF zählt nicht. Zwei Berichte dürfen keine
            #     Löschung herbeirechnen – sonst wäre der Bericht gefährlich.
            for lauf in ("run:dry-1", "run:dry-2"):
                dry = purge(root, dry_run=True, today=heute, run_key=lauf)
                if "blocked" in dry["deleted_slugs"]:
                    errors.append("Trockenlauf hat den Beleg-Zähler erhöht")
            if (root / JANITOR_STATE).exists():
                errors.append("Trockenlauf hat den Zähler geschrieben")
            if set(dry["deleted_slugs"]) != {"rueck", "doomed-shared"}:
                errors.append(f"Trockenlauf-Ziele falsch: {dry['deleted_slugs']}")
            if "rueck-ohne-nachweis" in dry["deleted_slugs"]:
                errors.append("Rückläufer-Verdacht ohne LIVE-Nachweis wurde "
                              "zum Löschziel (#610)")
            if not any(g["slug"] == "rueck-ohne-nachweis"
                       and g["klasse"] == "ohne-nachweis"
                       for g in dry["geschont"]):
                errors.append(f"Nachweis-loser Nachschub nicht begründet "
                              f"gemeldet: {dry['geschont']}")
            if not (posts / "rueck" / "index.md").exists():
                errors.append("Trockenlauf hat gelöscht")

            # (3) ERSTER echter Lauf: Rückläufer gehen sofort, der Quelldefekt
            #     wartet auf den zweiten Beleg.
            erst = purge(root, dry_run=False, today=heute, run_key="run:1")
            if "blocked" in erst["deleted_slugs"]:
                errors.append("Quelldefekt ohne zweiten Beleg gelöscht")
            if not (posts / "blocked" / "index.md").exists():
                errors.append("Quelldefekt beim ersten Beleg vernichtet")
            if not any(g["slug"] == "blocked" and g["klasse"] == "beleg"
                       for g in erst["geschont"]):
                errors.append(f"Beleg-Regel nicht begründet: {erst['geschont']}")
            zaehler = json.loads((root / JANITOR_STATE).read_text(encoding="utf-8"))
            if zaehler.get("blocked", {}).get("hits") != 1:
                errors.append(f"Beleg-Zähler falsch: {zaehler}")

            # (3b) #610: Der Nachschub ohne LIVE-Nachweis kehrt in den Vorrat
            #      zurück – Fahne gesetzt, Rückläufer-Signatur weg, Inhalt
            #      byte-identisch. Genau das rettet den Text, den der Tag
            #      vorher verlor.
            if "rueck-ohne-nachweis" not in erst["wiederhergestellt"]:
                errors.append(f"Nachschub ohne Nachweis nicht zurückgeholt: "
                              f"{erst['wiederhergestellt']}")
            ohne = (posts / "rueck-ohne-nachweis" / "index.md")
            if not ohne.exists():
                errors.append("Nachschub ohne Nachweis wurde gelöscht (#610)")
            else:
                ohne_text = ohne.read_text(encoding="utf-8")
                if "reserve: true" not in ohne_text:
                    errors.append("Fahne des zurückgeholten Nachschubs fehlt")
                if "reserve_published" in ohne_text:
                    errors.append("Rückläufer-Signatur nicht entfernt")
                if "draft: false" in ohne_text:
                    errors.append("Rückgeholter Nachschub ist live geschaltet")
                if "Nutzwert" not in ohne_text:
                    errors.append("Rückholung hat den Inhalt verändert")
            #      Zweiter Lauf: idempotent, keine zweite Rettung.
            zweit = purge(root, dry_run=True, today=heute, run_key="run:1b")
            if "rueck-ohne-nachweis" in zweit["deleted_slugs"]:
                errors.append("Zurückgeholter Nachschub ist erneut Löschziel")
            if "rueck-ohne-nachweis" in [
                    e.get("slug") for e in zweit.get("geschont", [])
                    if e.get("klasse") == "ohne-nachweis"]:
                errors.append("Zurückgeholter Nachschub wird erneut als "
                              "Nachweis-loser Rückläufer gemeldet "
                              "(Rettung nicht idempotent)")

            # (4) Der #594-Realfall überlebt JEDEN Lauf: nur heilbare Mängel.
            if not (posts / "heilbar-kurz" / "index.md").exists():
                errors.append("heilbarer Kurz-Entwurf wurde gelöscht (#594)")
            if not any(g["slug"] == "heilbar-kurz" and g["klasse"] == bk.HEILBAR
                       for g in erst["geschont"]):
                errors.append(f"heilbarer Entwurf nicht als Material gemeldet: "
                              f"{erst['geschont']}")

            # (5) ZWEITER Lauf mit demselben Fund: jetzt ist die Löschung belegt.
            rep = purge(root, dry_run=False, today=heute, run_key="run:2")
        finally:
            for k, v in umwelt.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v
        for slug in ("rueck", "blocked", "doomed-shared"):
            if (posts / slug).exists():
                errors.append(f"{slug} wurde nicht gelöscht")
        for slug in ("manual", "live-old-reserve", "shared", "heilbar-kurz",
                     "rueck-ohne-nachweis"):
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

    return errors


def run_selftest() -> int:
    if _stempel is None or _uhr is None or _MITTAG is None:
        print("🛑 reserve_janitor-Selbsttest FEHLGESCHLAGEN:\n"
              "  - scripts/selftest_clock.py fehlt oder ist nicht importierbar –\n"
              "    eine Lösch-Wache ohne Uhr-Zwang ist eine Verabredung mit\n"
              "    dem Kalender.")
        return 2
    errors: list[str] = []
    for tag in PROBETAGE:
        with _uhr(dt.datetime.combine(tag, _MITTAG, tzinfo=dt.timezone.utc),
                  _UHR_STRIKT, module=[sys.modules[__name__]]):
            errors += [f"[Testdatum {tag.isoformat()}] {e}"
                       for e in _szenario(tag)]
    if errors:
        print("🛑 reserve_janitor-Selbsttest FEHLGESCHLAGEN:")
        for e in errors:
            print(f"   - {e}")
        return 2
    print(f"✅ reserve_janitor-Selbsttest grün ({len(PROBETAGE)} Probetage, "
          "Uhr-Zwang): Rückläufer nur MIT LIVE-Nachweis sofort gelöscht, "
          "Nachschub ohne Nachweis zurück in den Vorrat geholt (#610), Torso "
          "erst mit 2 Läufen Beleg, heilbarer Kurz-Entwurf verschont (#594), "
          "Karenz greift, Trockenlauf zählt nicht, Handentwurf/Live "
          "geschützt, Links, llms.txt, Cover, Audio und Gedächtnisse "
          "bereinigt.")
    return 0


def loesch_wache() -> int:
    """STARTSPERRE (WF-B594): Darf dieser Lauf überhaupt löschen?

    Der Janitor entscheidet über unwiderrufliche Vernichtung. Seine
    Entscheidungsgrundlage ist die Klassen-Tabelle – und die ist nur so viel
    wert wie ihre Verdrahtung: Nennt sie einen Blocker „heilbar", ohne dass
    der Heiler in `reserve_finisher.HEALER_CHAIN` läuft, bleibt der Entwurf
    ewig blockiert und landet Nacht für Nacht wieder auf der Löschliste.
    Genau so verlor die Reserve am 05.10.2026 acht Artikel. Darum: Lücke in
    der Lösch-Deckung = dieser Lauf löscht NICHTS. Der Aufrufer macht daraus
    einen Trockenlauf (rc=0 für den Workflow-Step, aber `::error::` als
    Annotation) – die Produktion danach darf nicht an der Sperre sterben.
    """
    try:
        import reserve_healer_coverage as rhc
        b = rhc.loeschdeckung()
    except Exception as exc:  # noqa: BLE001 – fail-closed
        print(f"🛑 Lösch-Deckung nicht auswertbar: {exc}")
        print("::error::Reserve-Janitor gesperrt: Die Lösch-Deckung ist "
              "nicht auswertbar – ohne belastbare Klassen wird nicht "
              "gelöscht (Issue #594).")
        return 1
    if not (b["luecken"] or b["tote_eintraege"]):
        return 0
    print("🛑 LÖSCH-DECKUNG LÜCKENHAFT – der Janitor löscht in diesem Lauf "
          "nichts:")
    for e in b["luecken"]:
        print(f"   - {e['blocker']}: {e['art']}"
              + (f" ({', '.join(e.get('heiler', []))})"
                 if e.get("heiler") else ""))
    for e in b["tote_eintraege"]:
        print(f"   - {e['blocker']}: {e['art']} (deckt nichts mehr)")
    print("   Diagnose: python3 scripts/reserve_healer_coverage.py")
    print("::error::Reserve-Janitor gesperrt: Ein Triage-Blocker hat keinen "
          "Heiler in der Reserve-Kette oder keine Klasse – Löschen wäre "
          "wieder der Fehler aus #594.")
    return 1


def main() -> int:
    ap = argparse.ArgumentParser(description="Rückläufer und blockierte Reserve-Entwürfe löschen")
    ap.add_argument("--purge", action="store_true", help="wirklich löschen")
    ap.add_argument("--dry-run", action="store_true", help="nur berichten")
    ap.add_argument("--md", action="store_true", help="Markdown-Bericht")
    ap.add_argument("--json", action="store_true", help="JSON-Bericht")
    ap.add_argument("--geschont", action="store_true",
                    help="nur zeigen, wer warum verschont wurde (schreibt nichts)")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--stale-days", type=int, default=21)
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    if args.geschont:
        _, _, geschont = find_targets(ROOT, stale_days=args.stale_days,
                                      zaehler_schreiben=False)
        print(f"Reserve-Janitor: {len(geschont)} Entwurf/Entwürfe geschont "
              f"(Regeln: {hits_limit()} Läufe Beleg, {karenz_tage()} Tage "
              f"Karenz, {ausmusterung_tage()} Tage Ausmusterung).")
        for s in geschont:
            print(f"   - {s['slug']} [{s['klasse']}] {s['grund']}")
        return 0
    dry = args.dry_run or not args.purge
    if not dry and loesch_wache() != 0:
        # Kein Abbruch des Nachtlaufs: Der Janitor ist Stufe 0a, nach ihm
        # kommt die Produktion. Eine ungedeckte Klassen-Tabelle ist ein Grund,
        # NICHT zu löschen – kein Grund, den Nachschub zu verhindern. Die
        # Annotation oben macht den Strukturbruch trotzdem rot sichtbar, und
        # der Bericht zeigt als Trockenlauf, was der Lauf unterlassen hat.
        print("   → Dieser Lauf berichtet nur (Trockenlauf), löscht aber "
              "nichts.")
        dry = True
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
        for s in rep.get("geschont") or []:
            print(f"   ~ geschont: {s['slug']} [{s['klasse']}] {s['grund']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
