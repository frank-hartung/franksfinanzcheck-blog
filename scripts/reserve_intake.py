#!/usr/bin/env python3
"""
reserve_intake.py – Bestandsaufnahme: fertige Entwürfe finden, die niemandem
gehören, und sie dem Vorrat zuführen.

WARUM DIESE DATEI EXISTIERT (Vorgang WF-B594, Issue #594, 05.10.2026)
---------------------------------------------------------------------------
Befund F der Ursachenanalyse: Am 05.10.2026 meldete der Watchdog „Content-
Reserve niedrig – 0 gate-fertige Artikel". Im selben Repository lagen zur
selben Minute FÜNF Entwürfe, die am ECHTEN Gate 0,898–0,90 erreichten und
`ready: true` bekamen. Sie fehlten im Vorrat aus einem einzigen Grund: Ihnen
fehlte die Zeile `reserve: true`.

Der Pool ist nämlich fahnen-definiert (`reserve_pool.reserve_drafts()`:
`draft: true` UND `reserve: true`). Wer die Fahne nicht trägt, existiert für
Zählung, Zertifizierung und Watchdog nicht – egal wie fertig er ist. Die
Automatik meldete also Hunger, während der Vorratsschrank nebenan voll war.
Genau das ist „Automatisierung braucht Eingriff": Ein Mensch musste die
Verbindung herstellen, die keine Maschine je herstellte.

Diese Bestandsaufnahme schließt die Lücke – aber mit Eigentumsrecht, nicht
mit Gewalt. Ein Entwurf wird NUR übernommen, wenn alle sechs Prüfungen
zustimmen; jede Ablehnung steht mit Grund im Bericht:

  1. ENTWURF      `draft: true` – Live-Artikel werden nie angefasst.
  2. HERRENLOS    Keine fremde Fahne: `reserve*`, `cadence_*`, `park*`,
                  kein Eintrag im Custody-Ledger. Wer einem anderen
                  Fließband gehört, bleibt dort (Doppelbesitz erzeugt genau
                  die Geisterzustände, die #387 gekostet haben).
  3. MASCHINE     Erkennbar maschinell entstanden (`ai_generated: true` oder
                  `ki_redaktion:`). Ein reiner Handentwurf ist Privatsache
                  der Redaktion und wird nicht eingesammelt.
  4. REIF         `draft_triage` sagt REIF – kein einziges Hindernis. Die
                  Triage ist die SSOT dieser Aussage; eine zweite Meinung
                  hier wäre eine zweite Wahrheit.
  5. RISIKO       `editorial_review_gate.inferred_risk()` != hoch. YMYL
                  (Versicherung, Kredit, Altersvorsorge) braucht eine
                  menschliche Freigabe – die erzeugt keine Automatik.
  6. EINZIGARTIG  Kein Live-Artikel mit gleichem Titel oder gleichem
                  Slug-Rumpf. Eine zweite Ausgabe desselben Textes ist kein
                  Vorrat, sondern Kannibalisierung (realer Fall: der Entwurf
                  `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag`
                  dupliziert den LIVE-Artikel vom 11.09.).

ANGEBOTE STATT ÜBERGRIFF
    Entwürfe, die nur an Prüfung 2 scheitern, weil sie der KI-Redaktion
    gehören (`ki_redaktion_status: review` – ein Mensch soll sie freigeben),
    verschwinden nicht still. Sie stehen als ANGEBOT im Bericht, inklusive
    Kommando. Die Übernahme bleibt ein bewusster, protokollierter Akt:

        python3 scripts/reserve_intake.py --adopt <slug> --grund "..."

    Das ist der Unterschied zwischen „die Maschine räumt auf" und „die
    Maschine nimmt sich, was sie findet". Nur der erste Satz ist Premium.

PROTOKOLL
    Jede Übernahme schreibt `reserve: true` plus eine Herkunftszeile
    `reserve_intake: "<ISO-Datum> – <Grund>"` ins Frontmatter und einen
    Eintrag in `data/reserve-intake.json`. Rückgängig ist das mit einer
    Zeile; nachvollziehbar bleibt es für immer.

NUTZUNG
    python3 scripts/reserve_intake.py                # Bericht (nichts ändert sich)
    python3 scripts/reserve_intake.py --md           # Markdown für die Step-Summary
    python3 scripts/reserve_intake.py --apply        # herrenlose Reife übernehmen
    python3 scripts/reserve_intake.py --adopt <slug> # Angebot bewusst annehmen
    python3 scripts/reserve_intake.py --selftest     # Sabotageschutz

EXIT: 0 = Bericht/Übernahme in Ordnung · 2 = Werkzeugfehler/Selbsttest rot
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
sys.path.insert(0, str(SCRIPTS))
import reserve_artifacts as artifacts  # noqa: E402

LEDGER = Path("data") / "reserve-intake.json"

# Fremde Besitz-Marken: Wer eine davon trägt, gehört einem anderen Fließband.
FREMDE_FAHNEN = (
    re.compile(r"(?m)^reserve:\s*true\s*$"),
    re.compile(r"(?m)^reserve_published:"),
    re.compile(r"(?m)^reserve_blocked:"),
    re.compile(r"(?m)^cadence_[a-z_]+:"),
    re.compile(r"(?m)^park[a-z_]*:"),
    re.compile(r"(?m)^status:\s*\"?(geparkt|requeue)"),
)
RE_DRAFT = re.compile(r"(?m)^draft:\s*true\s*$")
RE_MASCHINE = (re.compile(r"(?m)^ai_generated:\s*true\s*$"),
               re.compile(r"(?m)^ki_redaktion:"))
RE_KI_REVIEW = re.compile(r"(?m)^ki_redaktion_status:\s*\"?review\"?\s*$")
RE_TITEL = re.compile(r'(?m)^title:\s*"?(.*?)"?\s*$')


def _fm(text: str) -> str:
    teile = text.split("---", 2)
    return teile[1] if text.startswith("---") and len(teile) >= 3 else ""


def titel_von(text: str) -> str:
    m = RE_TITEL.search(_fm(text))
    return (m.group(1) if m else "").strip()


def slug_rumpf(slug: str) -> str:
    """Slug ohne Datumspräfix – die eigentliche Themen-Identität."""
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", slug or "").strip("-")


def _norm(titel: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (titel or "").lower()).strip()


def live_identitaeten(root: Path) -> tuple[set[str], set[str]]:
    """Titel und Slug-Rümpfe aller LIVE-Artikel (Dubletten-Abwehr)."""
    titel: set[str] = set()
    ruempfe: set[str] = set()
    for index in sorted((root / "content" / "posts").glob("*/index.md")):
        try:
            text = index.read_text(encoding="utf-8")
        except OSError:
            continue
        if RE_DRAFT.search(text):
            continue
        titel.add(_norm(titel_von(text)))
        ruempfe.add(slug_rumpf(index.parent.name))
    return {t for t in titel if t}, {r for r in ruempfe if r}


def custody_slugs(root: Path) -> set[str]:
    try:
        data = artifacts.read_object(root / "data" / "reserve-custody.json")
    except FileNotFoundError:
        return set()
    # Beschädigtes Gedächtnis darf nie „herrenlos“ bedeuten (#634).
    out = set(data)
    for k, v in data.items():
        if isinstance(v, dict) and v.get("slug"):
            out.add(str(v["slug"]))
    return out


def risikoklasse(text: str) -> str:
    """Risikoklasse über die SSOT des Freigabe-Gates (nie nachgebaut)."""
    try:
        import editorial_review_gate as erg
        fm, _body = erg.split_article(text)
        daten = erg._yaml_module().safe_load(fm) or {}
        return erg.inferred_risk(daten if isinstance(daten, dict) else {})
    except Exception:  # noqa: BLE001 – fail-closed: im Zweifel Mensch
        return "hoch"


def triage_zustaende(root: Path, today: dt.date | None = None) -> dict:
    import draft_triage as triage
    return {r["slug"]: r for r in triage.collect(str(root),
                                                 today or dt.date.today(), 21)}


def pruefe(index: Path, *, root: Path, live_titel: set[str],
           live_ruempfe: set[str], custody: set[str],
           zeile: dict | None) -> dict:
    """Ein Urteil über EINEN Entwurf – mit Grund, immer."""
    slug = index.parent.name
    try:
        text = index.read_text(encoding="utf-8")
    except OSError as exc:
        return {"slug": slug, "zustand": "fehler", "grund": str(exc)}
    befund = {"slug": slug, "titel": titel_von(text),
              "pfad": str(index.relative_to(root))}

    if not RE_DRAFT.search(text):
        return {**befund, "zustand": "live", "grund": "kein Entwurf"}
    fremd = next((rx.pattern for rx in FREMDE_FAHNEN if rx.search(text)), None)
    if fremd or slug in custody:
        ki = bool(RE_KI_REVIEW.search(text))
        return {**befund, "zustand": "fremd",
                "angebot": ki,
                "grund": ("gehört dem Custody-Ledger" if slug in custody
                          else f"trägt bereits eine Besitz-Fahne ({fremd})")}
    if not any(rx.search(text) for rx in RE_MASCHINE):
        return {**befund, "zustand": "handarbeit",
                "grund": ("kein Maschinen-Merkmal (ai_generated/ki_redaktion)"
                          " – Handentwürfe gehören der Redaktion")}
    if zeile is None:
        return {**befund, "zustand": "unbekannt",
                "grund": "keine Triage-Zeile – ohne Urteil keine Übernahme"}
    if zeile.get("zustand") != "REIF":
        blocker = "; ".join(zeile.get("blocker") or [])[:200]
        return {**befund, "zustand": "unreif",
                "grund": f"Triage: {zeile.get('zustand')} – {blocker}"}
    risiko = risikoklasse(text)
    if risiko == "hoch":
        return {**befund, "zustand": "ymyl",
                "grund": ("Risikoklasse hoch – fachliche Freigabe ist ein "
                          "Redaktionsakt, keine Automatik")}
    if _norm(befund["titel"]) in live_titel:
        return {**befund, "zustand": "dublette",
                "grund": f"Titel existiert bereits live: {befund['titel']!r}"}
    if slug_rumpf(slug) in live_ruempfe:
        return {**befund, "zustand": "dublette",
                "grund": (f"Slug-Rumpf {slug_rumpf(slug)!r} existiert bereits "
                          "live – zweite Ausgabe desselben Themas")}
    if RE_KI_REVIEW.search(text):
        return {**befund, "zustand": "angebot", "angebot": True,
                "risiko": risiko,
                "grund": ("reif und dublettenfrei, aber die KI-Redaktion "
                          "wartet auf eine menschliche Freigabe "
                          "(ki_redaktion_status: review)")}
    return {**befund, "zustand": "uebernehmbar", "risiko": risiko,
            "grund": "herrenlos, maschinell, reif, standardrisiko, einzigartig"}


def bestandsaufnahme(root: Path = ROOT,
                     today: dt.date | None = None) -> dict:
    root = Path(root)
    live_titel, live_ruempfe = live_identitaeten(root)
    custody = custody_slugs(root)
    zeilen = triage_zustaende(root, today)
    befunde = []
    for index in sorted((root / "content" / "posts").glob("*/index.md")):
        text_draft = index.read_text(encoding="utf-8", errors="ignore")
        if not RE_DRAFT.search(text_draft):
            continue
        befunde.append(pruefe(index, root=root, live_titel=live_titel,
                              live_ruempfe=live_ruempfe, custody=custody,
                              zeile=zeilen.get(index.parent.name)))
    gruppen: dict[str, list] = {}
    for b in befunde:
        gruppen.setdefault(b["zustand"], []).append(b)
    return {"befunde": befunde, "gruppen": gruppen,
            "uebernehmbar": gruppen.get("uebernehmbar", []),
            "angebote": gruppen.get("angebot", [])
            + [b for b in gruppen.get("fremd", []) if b.get("angebot")]}


# ---------------------------------------------------------------------------
#  Übernahme (der einzige schreibende Teil)
# ---------------------------------------------------------------------------
def _ledger_schreiben(root: Path, eintrag: dict) -> None:
    pfad = root / LEDGER
    try:
        data = json.loads(pfad.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = {}
    except (OSError, ValueError):
        data = {}
    data.setdefault("uebernahmen", []).append(eintrag)
    pfad.parent.mkdir(parents=True, exist_ok=True)
    pfad.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


def uebernehmen(index: Path, grund: str, *, root: Path = ROOT,
                heute: dt.date | None = None) -> dict:
    """Setzt `reserve: true` + Herkunftszeile. Idempotent und protokolliert."""
    root = Path(root)
    text = index.read_text(encoding="utf-8")
    slug = index.parent.name
    if re.search(r"(?m)^reserve:\s*true\s*$", text):
        return {"slug": slug, "ok": True, "schon": True,
                "grund": "trug die Fahne bereits"}
    heute = heute or dt.date.today()
    herkunft = (f'reserve: true\n'
                f'reserve_intake: "{heute.isoformat()} – {grund}"\n')
    # Die Fahne gehört direkt hinter `draft: true`: dort stehen die
    # Zustands-Felder, und jeder Leser sieht Entwurf + Besitz auf einen Blick.
    neu, anzahl = re.subn(r"(?m)^(draft:\s*true\s*)$",
                          lambda m: m.group(1) + "\n" + herkunft.rstrip("\n"),
                          text, count=1)
    if not anzahl:
        return {"slug": slug, "ok": False,
                "grund": "keine Zeile `draft: true` gefunden"}
    index.write_text(neu, encoding="utf-8")
    _ledger_schreiben(root, {"slug": slug, "datum": heute.isoformat(),
                             "grund": grund})
    return {"slug": slug, "ok": True, "grund": grund}


def markdown(bericht: dict) -> str:
    g = bericht["gruppen"]
    zeilen = ["", "## 📥 Reserve-Bestandsaufnahme (herrenlose Reife)", "",
              f"- **Übernehmbar:** {len(bericht['uebernehmbar'])}",
              f"- **Angebote an die Redaktion:** {len(bericht['angebote'])}",
              f"- Entwürfe insgesamt geprüft: {len(bericht['befunde'])}"]
    if bericht["uebernehmbar"]:
        zeilen += ["", "### Übernommen bzw. übernehmbar"]
        for b in bericht["uebernehmbar"]:
            zeilen.append(f"- `{b['slug']}` – {b['grund']}")
    if bericht["angebote"]:
        zeilen += ["", "### Angebote (bewusste Freigabe nötig)", ""]
        for b in bericht["angebote"]:
            zeilen.append(f"- `{b['slug']}` – {b['grund']}  \n"
                          f"  `python3 scripts/reserve_intake.py --adopt "
                          f"{b['slug']} --grund \"...\"`")
    abgelehnt = [b for k, v in g.items() if k not in
                 ("uebernehmbar", "angebot") for b in v]
    if abgelehnt:
        zeilen += ["", "### Nicht übernommen (mit Grund)"]
        for b in sorted(abgelehnt, key=lambda x: x["slug"]):
            zeilen.append(f"- `{b['slug']}` – **{b['zustand']}**: {b['grund']}")
    return "\n".join(zeilen) + "\n"


# ---------------------------------------------------------------------------
#  Selbsttest – Sabotagefälle statt Schönwetter
# ---------------------------------------------------------------------------
try:  # Determinismus-Garantie (scripts/selftest_clock.py)
    from selftest_clock import (MITTAG as _MITTAG,  # type: ignore
                                MODUS_STRIKT as _UHR_STRIKT,
                                stempel as _stempel, uhr as _uhr)
except Exception:  # noqa: BLE001
    _MITTAG = _UHR_STRIKT = _stempel = _uhr = None


# Sechs Probetage statt „heute": Schalttag, Jahreswechsel, Monatsenden und
# der Tag, an dem audio_coverage_check kippte. Gleiche Eingabe, gleiches
# Ergebnis – an jedem Kalendertag.
PROBETAGE = (dt.date(2026, 3, 1), dt.date(2024, 2, 29), dt.date(2026, 12, 24),
             dt.date(2027, 1, 1), dt.date(2026, 6, 30), dt.date(2025, 10, 5))


def _post(posts: Path, slug: str, fm: str, body: str = "Text") -> Path:
    d = posts / slug
    d.mkdir(parents=True, exist_ok=True)
    p = d / "index.md"
    p.write_text(f"---\n{fm}\n---\n\n{body}\n", encoding="utf-8")
    return p


def _szenario(heute: dt.date) -> list[str]:
    """Ein vollständiger Durchlauf gegen ein VORGEGEBENES Testdatum.

    DETERMINISMUS-VERTRAG (Nachzug 05.10.2026, WF-B594):
    Die erste Fassung dieses Selbsttests las `dt.date.today()` und stempelte
    ihre Fixtures mit der echten Wanduhr – unter der CI-Probe mit um 97 bzw.
    1461 Tage vorgestellter Uhr fielen alle reifen Entwürfe auf „unreif",
    weil die Triage sie am Verfallsfenster altern sah. Genau die Bauart, vor
    der `scripts/selftest_clock.py` seit dem 18.09.2026 warnt. Jeder Fall ist
    deshalb RELATIV zum Testdatum beschrieben, jedes Dateialter wird ABSOLUT
    gestempelt, und der Prüfpfad läuft unter Uhr-Zwang.
    """
    import tempfile
    fehler: list[str] = []
    body = ("[A](../../posts/live-thema/) und [B](../../posts/live-zwei/)\n"
            + "\n".join(f"## Abschnitt {i}\nNutzwert mit Zahlen und Beispielen."
                        for i in range(6)) * 90)
    kopf = (f'lastmod: {heute.isoformat()}\ndate: {heute.isoformat()}\n'
            'description: "Eine ordentliche Beschreibung mit genug Zeichen '
            'fuer das Meta-Gate dieser Bestandsaufnahme im Test."\n')

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        posts = root / "content" / "posts"
        covers = root / "static" / "images" / "covers"
        covers.mkdir(parents=True)
        for name in ("frei", "fremd", "hand", "kurz", "ymyl", "dublette",
                     "angebot"):
            (covers / f"{name}.jpg").write_text("img", encoding="utf-8")
        (covers / "live-thema.jpg").write_text("img", encoding="utf-8")

        def fm(slug: str, titel: str, extra: str = "",
               ai: str = "ai_generated: true") -> str:
            return (f'title: "{titel}"\n{kopf}draft: true\n{ai}\n'
                    f'cover:\n  image: "images/covers/{slug}.jpg"\n{extra}')

        # Slug-Präfix RELATIV zum Testdatum (nie "2026-01-01"): ein Entwurf
        # mit Datum aus der Zukunft des Testtages ist für die Triage nicht
        # fällig und fiele als "unreif" durch.
        pfx = (heute - dt.timedelta(days=3)).isoformat()
        _post(posts, "live-thema", f'title: "Live Thema"\n{kopf}draft: false',
              body)
        _post(posts, "live-zwei", f'title: "Live Zwei"\n{kopf}draft: false',
              body)
        _post(posts, f"{pfx}-frei",
              fm("frei", "Strom sparen im Haushalt clever geplant"), body)
        _post(posts, f"{pfx}-fremd",
              fm("fremd", "Zweiter freier Entwurf mit Nutzwert",
                 extra="cadence_wait: true\n"), body)
        _post(posts, f"{pfx}-hand",
              fm("hand", "Handentwurf der Redaktion ohne Maschine",
                 ai="ai_generated: false"), body)
        _post(posts, f"{pfx}-kurz", fm("kurz", "Zu kurzer Rohtext"),
              "## Nur ein Anfang\nViel zu wenig Text.")
        _post(posts, f"{pfx}-ymyl",
              fm("ymyl", "Kfz-Versicherung vergleichen und sparen",
                 extra='pillar: "versicherungen"\n'), body)
        _post(posts, f"{pfx}-live-thema",
              fm("dublette", "Ganz anderer Titel, gleicher Slug-Rumpf"), body)
        _post(posts, f"{pfx}-angebot",
              fm("angebot", "Angebot der KI-Redaktion mit Nutzwert",
                 extra='ki_redaktion: "claude"\n'
                       'ki_redaktion_status: "review"\n'), body)

        # Alter ABSOLUT stempeln – nie „JETZT minus n Tage". Drei Tage alt:
        # sicher innerhalb des Triage-Fensters, egal welcher Kalendertag.
        for index in posts.glob("*/index.md"):
            _stempel(str(index), heute - dt.timedelta(days=3))

        b = bestandsaufnahme(root, heute)
        zustand = {x["slug"]: x["zustand"] for x in b["befunde"]}
        erwartet = {
            f"{pfx}-frei": "uebernehmbar",
            f"{pfx}-fremd": "fremd",
            f"{pfx}-hand": "handarbeit",
            f"{pfx}-kurz": "unreif",
            f"{pfx}-ymyl": "ymyl",
            f"{pfx}-live-thema": "dublette",
            f"{pfx}-angebot": "angebot",
        }
        for slug, soll in erwartet.items():
            if zustand.get(slug) != soll:
                fehler.append(f"{slug}: erwartet {soll}, erhalten "
                              f"{zustand.get(slug)}")
        if "live-thema" in zustand:
            fehler.append("Live-Artikel wurde als Entwurf gewertet")

        # Übernahme schreibt die Fahne genau einmal und protokolliert.
        index = posts / f"{pfx}-frei" / "index.md"
        r1 = uebernehmen(index, "Selbsttest", root=root, heute=heute)
        r2 = uebernehmen(index, "Selbsttest", root=root, heute=heute)
        text = index.read_text(encoding="utf-8")
        if not r1.get("ok") or not r2.get("schon"):
            fehler.append(f"Übernahme nicht idempotent: {r1} / {r2}")
        if len(re.findall(r"(?m)^reserve:\s*true\s*$", text)) != 1:
            fehler.append("Fahne nicht genau einmal gesetzt")
        if "reserve_intake:" not in text:
            fehler.append("Herkunftszeile fehlt")
        ledger = json.loads((root / LEDGER).read_text(encoding="utf-8"))
        if len(ledger.get("uebernahmen", [])) != 1:
            fehler.append(f"Ledger falsch: {ledger}")
        # Nach der Übernahme ist derselbe Entwurf nicht mehr herrenlos.
        b2 = bestandsaufnahme(root, heute)
        if any(x["slug"] == f"{pfx}-frei" and x["zustand"] == "uebernehmbar"
               for x in b2["befunde"]):
            fehler.append("übernommener Entwurf gilt weiter als herrenlos")

    return fehler


def run_selftest() -> int:
    if _stempel is None or _uhr is None or _MITTAG is None:
        print("🛑 SELBSTTEST reserve_intake FEHLGESCHLAGEN:\n"
              "  - scripts/selftest_clock.py fehlt oder ist nicht importierbar –\n"
              "    ohne Uhr-Zwang wäre dieser Selbsttest wieder eine\n"
              "    Verabredung mit dem Kalender.")
        return 2
    fehler: list[str] = []
    for tag in PROBETAGE:
        # Uhr-Zwang: Ein Lesezugriff auf die Wanduhr im Prüfpfad dieses
        # Moduls ist ein Fehler, keine Nebensache.
        with _uhr(dt.datetime.combine(tag, _MITTAG, tzinfo=dt.timezone.utc),
                  _UHR_STRIKT, module=[sys.modules[__name__]]):
            fehler += [f"[Testdatum {tag.isoformat()}] {e}"
                       for e in _szenario(tag)]
    if fehler:
        print("🛑 SELBSTTEST reserve_intake FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   ✗ {f}")
        return 2
    print(f"✅ Selbsttest reserve_intake ({len(PROBETAGE)} Probetage, Uhr-Zwang): "
          "herrenlose Reife erkannt; fremde Fahne, Handentwurf, unreif, YMYL "
          "und Dublette abgelehnt; KI-Review bleibt Angebot; Übernahme "
          "idempotent und protokolliert.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Fertige, herrenlose Entwürfe dem Reserve-Pool zuführen")
    ap.add_argument("--apply", action="store_true",
                    help="übernehmbare Entwürfe wirklich übernehmen")
    ap.add_argument("--adopt", metavar="SLUG",
                    help="ein Angebot bewusst annehmen")
    ap.add_argument("--grund", default="",
                    help="Begründung für --adopt (Pflicht)")
    ap.add_argument("--md", action="store_true", help="Markdown-Bericht")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()

    if args.adopt:
        if not args.grund.strip():
            print("❌ --adopt verlangt --grund: Eine Übernahme ohne "
                  "Begründung ist ein unprotokollierter Eingriff.")
            return 2
        index = ROOT / "content" / "posts" / args.adopt / "index.md"
        if not index.is_file():
            print(f"❌ Entwurf nicht gefunden: {args.adopt}")
            return 2
        r = uebernehmen(index, args.grund.strip())
        print(("✅ übernommen: " if r.get("ok") else "❌ nicht übernommen: ")
              + f"{r['slug']} – {r['grund']}")
        return 0 if r.get("ok") else 2

    bericht = bestandsaufnahme()
    if args.apply:
        for b in bericht["uebernehmbar"]:
            index = ROOT / "content" / "posts" / b["slug"] / "index.md"
            r = uebernehmen(index, "herrenlose Reife (automatische "
                                   "Bestandsaufnahme)")
            print(("✅ übernommen: " if r.get("ok") else "❌ "),
                  r["slug"], "–", r["grund"])
        bericht = bestandsaufnahme()
    if args.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=1))
    elif args.md:
        print(markdown(bericht))
    else:
        print(f"Reserve-Bestandsaufnahme: {len(bericht['uebernehmbar'])} "
              f"übernehmbar, {len(bericht['angebote'])} Angebot(e), "
              f"{len(bericht['befunde'])} Entwürfe geprüft.")
        for b in bericht["uebernehmbar"]:
            print(f"   + {b['slug']} – {b['grund']}")
        for b in bericht["angebote"]:
            print(f"   ? {b['slug']} – {b['grund']}")
        for b in sorted(bericht["befunde"], key=lambda x: x["slug"]):
            if b["zustand"] not in ("uebernehmbar", "angebot"):
                print(f"   - {b['slug']} [{b['zustand']}] {b['grund']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
