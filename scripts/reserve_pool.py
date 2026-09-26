#!/usr/bin/env python3
"""
reserve_pool.py – Redaktions-Reserve-Pool („Zwingend 2–3 LIVE an Mo/Mi/Fr“)

WARUM (Premium-Fix 03.09.2026, Auftrag „Mi 02.09.: nur 1 Artikel live“):
  Die Content-Engine produziert 2–3 Artikel pro Publikationstag aus
  KI-Generierung + Re-Queue-Recycling. Beide Quellen können an einem Tag
  versagen (Provider-Ausfall, wiederholte Gate-Stopps). Damit die
  Dauervorgabe „Mo/Mi/Fr 2–3 Artikel live“ NICHT mehr von der KI-Verfügbarkeit
  abhängt, hält die Redaktion einen kleinen POOL fertiger Premium-Evergreen-
  Artikel als Entwürfe vor (Frontmatter: `reserve: true`).

  Nur die Kadenz-Endkontrolle (kadenz-endkontrolle.yml, 21:05 UTC an
  Mo/Mi/Fr, NACH dem letzten Engine-Slot) bzw. die Engine selbst dürfen
  Reserve-Artikel VERÖFFENTLICHEN – und nur, wenn der Tag sonst unter dem
  LIVE-Mindestziel bliebe. Veröffentlichte Reserve-Artikel sind normale
  live-Posts (draft: false, Datum = heute) und durchlaufen danach exakt
  dieselben Deploy-Gates wie jeder andere Artikel.

  Tägliche Reserve-Produktion ergänzt den Engine-Top-up. Der Vorrat ist
  endlich; fehlende gate-geprüfte Reserve löst einen sichtbaren Fehler aus.

SICHERHEIT:
  * reserve:true-Entwürfe haben KEINE cadence_*-Felder → park_state liest
    sie als „manual“ (Frank-Schutz): keine andere Automatik fasst sie an.
  * Veröffentlicht wird NUR bis zum LIVE-Mindestziel und NUR an Mo/Mi/Fr
    (Guard identisch zu cadence_guard.PUBLICATION_DAYS).
  * Kein Reserve-Artikel wird je gelöscht oder überschrieben.

MODI:
  python3 scripts/reserve_pool.py --status          # Pool + heutige LIVE-Zahl
  python3 scripts/reserve_pool.py --publish-to-min  # Lücke bis Min füllen
  python3 scripts/reserve_pool.py --selftest        # Sabotage-Schutz
"""

import contextlib
import datetime
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"

sys.path.insert(0, str(ROOT / "scripts"))
import cadence_guard  # noqa: E402 – PUBLICATION_DAYS/load_posts (SSOT)


def now_utc_iso() -> str:
    return (datetime.datetime.now(datetime.timezone.utc)
            - datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")


def _frontmatter(text: str) -> str:
    parts = text.split("---", 2)
    return parts[1] if len(parts) == 3 and parts[0] == "" else ""


def is_reserve(text: str) -> bool:
    m = re.search(r"(?m)^reserve:\s*(true|yes|1)\s*$", _frontmatter(text))
    return bool(m)


def is_draft(text: str) -> bool:
    return bool(re.search(r"(?m)^draft:\s*true\s*$", _frontmatter(text)))


def reserve_drafts(posts_dir: Path = POSTS) -> list:
    """Alle Reserve-Entwürfe (draft: true + reserve: true), älteste zuerst.

    Premium-Fix 15.09.2026 (#287): Wenn data/reserve-readiness.json
    hash-gesicherte ready-Zertifikate trägt, kommen zertifizierte
    Kandidaten ZUERST – so greift die Quote-Nachfüllung bevorzugt zu
    Artikeln, die publish_gate STRICT bereits bestanden haben, statt
    blind den ältesten (ggf. abgelehnten) Entwurf zu versuchen.
    """
    out = []
    if not posts_dir.is_dir():
        return out
    for index in sorted(posts_dir.glob("*/index.md")):
        text = index.read_text(encoding="utf-8")
        if is_draft(text) and is_reserve(text):
            out.append(index)
    return _prefer_certified(out)


def _prefer_certified(drafts: list) -> list:
    """Stable: ready-zertifizierte zuerst, Rest in Originalreihenfolge."""
    import hashlib
    import json
    cert_path = ROOT / "data" / "reserve-readiness.json"
    if not cert_path.exists() or not drafts:
        return drafts
    try:
        data = json.loads(cert_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 – Zertifikat optional
        return drafts
    ready_ok = set()
    for row in data.get("candidates") or []:
        if not row.get("ready"):
            continue
        slug = row.get("slug")
        sha = row.get("sha256")
        if not slug:
            continue
        # Hash-Match: nur EXAKT dieser Inhalt gilt als zertifiziert.
        path = next((p for p in drafts if p.parent.name == slug), None)
        if path is None:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except OSError:
            continue
        if sha and hashlib.sha256(body.encode()).hexdigest() != sha:
            continue
        ready_ok.add(slug)
    if not ready_ok:
        return drafts
    head = [p for p in drafts if p.parent.name in ready_ok]
    tail = [p for p in drafts if p.parent.name not in ready_ok]
    return head + tail


# REPARATUR 26.09.2026 (#387) – Themen-Sperre in ZWEI Stufen.
#
# Befund: Am 20.09. gingen VIER Gasrechnungs-Varianten am selben Tag live;
# der Dubletten-Schutz stufte drei davon danach wieder zu Entwürfen zurück
# („Rückläufer") – fertiger Content ohne Zuhause, verbrannte Arbeit, und
# ein Pool, der sich selbst leerte.
#
# Warum nicht einfach 14 Tage hart sperren? Weil der Pool heute zu 4/5 aus
# Varianten EINES Themas besteht. Eine harte Sperre würde an einem
# Ausfalltag drei fertige Artikel blockieren und die Dauervorgabe „2–3 LIVE
# an Mo/Mi/Fr" reißen – die Reserve wäre genau dann wertlos, wofür sie da
# ist. Deshalb:
#
#   WEICH (14 Tage): Erste Wahl sind Kandidaten mit frischem Thema. Solange
#     das Tagesziel damit erreichbar ist, bleibt eine thematische
#     Wiederholung im Pool liegen.
#   HART (0 Tage = derselbe Tag): Was nachweislich Schaden anrichtet, wird
#     NIE veröffentlicht – zwei Artikel zum selben Thema am SELBEN Tag.
#     Genau diese Konstellation (vier Gasrechnungs-Varianten am 20.09.)
#     erzeugte die fünf Rückläufer; der Dubletten-Schutz stuft die
#     Zweitplatzierten verlässlich wieder zurück. Ein Thema am
#     übernächsten Publikationstag zu wiederholen ist dagegen normales
#     redaktionelles Arbeiten – das darf die Kadenz nicht kosten.
#
# Ergebnis: kein Kannibalismus, aber auch keine selbstverschuldete Lücke.
DUBLETTEN_SPERRE_TAGE = 14
DUBLETTEN_HARTSPERRE_TAGE = 0


def frische_live_titel(posts_dir: Path = POSTS,
                       tage: int = DUBLETTEN_SPERRE_TAGE,
                       heute: datetime.date | None = None) -> dict:
    """slug -> Titel der zuletzt veröffentlichten Artikel.

    Grundlage der Themen-Sperre. `cadence_guard.load_posts` ist die SSOT
    für Datum und Entwurfs-Status (Datums-FELD, nicht Ordnerpräfix); den
    Titel liest diese Funktion selbst aus dem Frontmatter.
    """
    heute = heute or datetime.date.today()
    grenze = heute - datetime.timedelta(days=tage)
    treffer = {}
    for post in cadence_guard.load_posts(str(posts_dir)):
        if post.get("draft"):
            continue
        datum = post.get("date")
        if isinstance(datum, str):
            try:
                datum = datetime.date.fromisoformat(datum[:10])
            except ValueError:
                datum = None
        if not datum or datum < grenze:
            continue
        try:
            titel = _titel(Path(post["path"]).read_text(encoding="utf-8"))
        except OSError:
            continue
        if titel:
            treffer[post.get("slug") or Path(post["path"]).parent.name] = titel
    return treffer


def sperr_treffer(titel: str, gesperrt: dict, rt=None):
    """Kollidiert `titel` thematisch mit einem kürzlich live gegangenen?

    Als eigene Funktion, damit die Entscheidung im Selbsttest ohne
    Kalender, Dateisystem und Wochentag geprüft werden kann.
    """
    if not titel or not gesperrt:
        return None
    if rt is None:
        try:
            import reserve_topics as rt  # noqa: PLC0415 – fail-open
        except Exception:  # noqa: BLE001
            return None
    try:
        return rt.thema_kollision(titel, gesperrt)
    except Exception:  # noqa: BLE001
        return None


def _titel(text: str) -> str:
    m = re.search(r'(?m)^title:\s*["\']?(.+?)["\']?\s*$', _frontmatter(text))
    return m.group(1).strip() if m else ""


def live_count_today(posts_dir: Path = POSTS) -> int:
    today = datetime.date.today()
    posts = cadence_guard.load_posts(posts_dir)
    return len(cadence_guard.published_on(posts, today))


def publish_one(index: Path, when=None) -> str:
    """Veröffentlicht EINEN Reserve-Artikel: draft:false, Datum = heute,
    reserve-Marke wird durch reserve_published ersetzt (Audit-Trail)."""
    text = index.read_text(encoding="utf-8")
    iso = when or now_utc_iso()
    text = re.sub(r"(?m)^date:\s*.*$", f"date: {iso}", text, count=1)
    text = re.sub(r"(?m)^draft:\s*true\s*$", "draft: false", text, count=1)
    text = re.sub(r"(?m)^reserve:\s*(true|yes|1)\s*$\n?",
                  f"reserve_published: {iso[:10]}\n", text, count=1)
    index.write_text(text, encoding="utf-8")
    return iso


def publish_to_min(min_per_day: int | None = None,
                   posts_dir: Path = POSTS, validator=None) -> list:
    """Füllt die heutige LIVE-Lücke bis zum Mindestziel aus dem Reserve-Pool.

    Nur an Publikationstagen (Mo/Mi/Fr). Rückgabe: Liste veröffentlichter
    Slugs. Ist der Pool leer, bleibt die Lücke – die Endkontrolle meldet
    das Defizit dann als Issue (engine_issue --deficit).

    ZWEI DURCHGÄNGE (26.09.2026, #387): Erst Kandidaten mit frischem Thema
    (Vielfalt), danach – nur falls das Tagesziel sonst nicht erreicht wird –
    auch thematische Wiederholungen. Was nachweislich zurückgestuft würde
    (gleiches Thema am SELBEN Tag), bleibt in beiden Durchgängen gesperrt.
    """
    today = datetime.date.today()
    if today.weekday() not in cadence_guard.PUBLICATION_DAYS:
        print(f"Kein Publikationstag ({cadence_guard.DAYS_DE[today.weekday()]}) "
              f"– Reserve-Pool bleibt unangetastet.")
        return []
    floor, ceiling = cadence_guard.effective_limits()
    min_per_day = max(floor, min(min_per_day or floor, ceiling))
    if validator is None:
        from publication_release import accept_candidate
        validator = accept_candidate

    # Fail-open: Lädt die Disposition nicht, publiziert der Pool wie früher.
    try:
        import reserve_topics as rt
        sperren = {
            1: frische_live_titel(posts_dir, heute=today),
            2: frische_live_titel(posts_dir, tage=DUBLETTEN_HARTSPERRE_TAGE,
                                  heute=today),
        }
    except Exception as exc:  # noqa: BLE001
        print(f"  ⚠ Themen-Sperre inaktiv ({exc}) – Reserve publiziert "
              f"ohne Vielfalts-Prüfung.")
        rt, sperren = None, {1: {}, 2: {}}

    published: list = []
    zurueckgestellt: list = []

    for durchgang in (1, 2):
        if live_count_today(posts_dir) >= min_per_day:
            break
        if durchgang == 2:
            if not zurueckgestellt:
                break
            print("  ↻ Tagesziel noch nicht erreicht – zweiter Durchgang "
                  "lässt thematische Wiederholungen zu (die Kadenz-Zusage "
                  "wiegt schwerer als die Vielfalt; zwei Artikel zum selben "
                  "Thema am selben Tag bleiben ausgeschlossen).")
        gesperrt = sperren[durchgang]
        for index in reserve_drafts(posts_dir):
            # Never carry a delayed slot across midnight into a
            # non-publication day.
            if datetime.date.today() != today:
                break
            if live_count_today(posts_dir) >= min_per_day:
                break
            if index.parent.name in published:
                continue
            original = index.read_text(encoding="utf-8")
            titel = _titel(original) if rt is not None else ""
            treffer = sperr_treffer(titel, gesperrt, rt) if titel else None
            if treffer:
                # NICHT verbrauchen: Der Kandidat bleibt im Pool und ist
                # nach Ablauf der Sperre wieder ein vollwertiger Notnagel.
                if index.parent.name not in zurueckgestellt:
                    zurueckgestellt.append(index.parent.name)
                    print(f"  ↩ Reserve zurückgestellt (Themen-Dublette zu "
                          f"„{treffer[0]}“, Leitbegriff „{treffer[1]}“): "
                          f"{index.parent.name}")
                continue
            accepted = False
            try:
                iso = now_utc_iso()
                if iso[:10] != today.isoformat():
                    break
                iso = publish_one(index, when=iso)
                accepted = validator(index)
            finally:
                if not accepted:
                    index.write_text(original, encoding="utf-8")
            if not accepted:
                print(f"  Reserve abgelehnt, bleibt Entwurf: "
                      f"{index.parent.name}")
                continue
            published.append(index.parent.name)
            if titel:
                # Innerhalb desselben Laufs zählt jede Veröffentlichung
                # sofort als belegtes Thema – in BEIDEN Sperrlisten.
                for liste in sperren.values():
                    liste[index.parent.name] = titel
            print(f"  🆘 RESERVE live geschaltet: {index.parent.name} "
                  f"(datiert {iso[:10]})")

    if published:
        print(f"Reserve-Pool: {len(published)} Artikel veröffentlicht – "
              f"jetzt {live_count_today(posts_dir)} live heute "
              f"(Ziel ≥ {min_per_day}).")
    else:
        live = live_count_today(posts_dir)
        pool = len(reserve_drafts(posts_dir))
        print(f"Reserve-Pool: keine Veröffentlichung nötig/möglich – "
              f"{live} live heute, Ziel ≥ {min_per_day}, Pool: {pool}.")
        if zurueckgestellt and live < min_per_day:
            print(f"  Hinweis: {len(zurueckgestellt)} Kandidat(en) blieben "
                  f"liegen, weil ihr Thema gerade erst live war. Eine echte "
                  f"Lücke ist ehrlicher als eine Dublette, die morgen wieder "
                  f"Entwurf ist – die Endkontrolle meldet sie als Defizit.")
    return published


@contextlib.contextmanager
def _als_publikationstag():
    """Selbsttest-Helfer: erklärt den HEUTIGEN Tag zum Publikationstag.

    Bewusst wird der Wochentags-Kanon geliehen und NICHT die Uhr verstellt:
    `publish_one` datiert auf die echte UTC-Zeit und vergleicht sie mit
    `today` – eine gefälschte Uhr ließe den Test still ins Leere laufen.
    So prüft er an jedem Kalendertag dieselbe Logik (Uhr-Zwang, C15).
    """
    original = cadence_guard.PUBLICATION_DAYS
    cadence_guard.PUBLICATION_DAYS = tuple(range(7))
    try:
        yield
    finally:
        cadence_guard.PUBLICATION_DAYS = original


def run_selftest() -> list:
    fehler = []
    # --- Vielfalts-Sperre (#387) --------------------------------------
    frisch = {"2026-09-20-gas": "Gasrechnung senken: Dein Strategieplan "
                                   "im Spätsommer"}
    if not sperr_treffer("Gasrechnung senken: Clevere Herbst-Vorbereitung "
                         "im Check", frisch):
        fehler.append("Themen-Dublette wird trotz frischer Veröffentlichung "
                      "publiziert (Rückläufer-Ursache #387)")
    if sperr_treffer("Reisekrankenversicherung: Worauf du 2026 achten musst",
                     frisch):
        fehler.append("Fremdes Thema wird fälschlich zurückgestellt")
    if sperr_treffer("", frisch) or sperr_treffer("Irgendwas", {}):
        fehler.append("Sperre urteilt ohne Datengrundlage")

    class _Kaputt:
        @staticmethod
        def thema_kollision(*_a, **_k):
            raise RuntimeError("Modul defekt")

    if sperr_treffer("Gasrechnung senken", frisch, _Kaputt) is not None:
        fehler.append("Sperre ist nicht fail-open (blockiert bei Defekt)")

    # --- Zwei Durchgänge: Vielfalt zuerst, Kadenz notfalls trotzdem ------
    #  Der reale Pool bestand am 26.09. zu 4/5 aus Varianten EINES Themas.
    #  Eine harte Sperre hätte an einem Ausfalltag drei fertige Artikel
    #  blockiert und die Zusage „2–3 LIVE an Mo/Mi/Fr" gerissen.
    with tempfile.TemporaryDirectory() as tmp:
        fx = Path(tmp) / "content" / "posts"
        fx.mkdir(parents=True)
        # Gestern live: Thema Stromfresser. Pool: zwei Stromfresser-Varianten.
        gestern = (datetime.date.today()
                   - datetime.timedelta(days=1)).isoformat()
        d = fx / "live-stromfresser"
        d.mkdir()
        (d / "index.md").write_text(
            f'---\ntitle: "Stromfresser finden: Die teuersten Energiediebe"\n'
            f"date: {gestern}T06:00:00Z\ndraft: false\n---\n\nBody.\n",
            encoding="utf-8")
        for name in ("pool-stromfresser-a", "pool-stromfresser-b"):
            d = fx / name
            d.mkdir()
            (d / "index.md").write_text(
                f'---\ntitle: "Stromfresser finden: So senkst du die '
                f'Stromrechnung ({name[-1]})"\n'
                f"date: {gestern}T06:00:00Z\ndraft: true\nreserve: true\n"
                f"---\n\nBody.\n", encoding="utf-8")

        veroeffentlicht = []

        def validator(index):
            veroeffentlicht.append(index.parent.name)
            return True

        with _als_publikationstag():
            raus = publish_to_min(2, posts_dir=fx, validator=validator)
        # Ein Pool aus EINEM Thema trägt genau einen Artikel pro Tag: Der
        # erste geht raus (sonst wäre der Tag leer, obwohl fertige Arbeit
        # bereitliegt), der zweite wäre die Dublette, die der
        # Dubletten-Schutz noch am selben Tag zurückstuft.
        if len(raus) != 1:
            fehler.append(f"Ein-Thema-Pool: {len(raus)} Artikel statt genau "
                          "1 – entweder verschenkte Kadenz oder Dublette")

        # Harte Sperre: dasselbe Thema HEUTE live -> nie ein zweiter Artikel.
        fx2 = Path(tmp) / "posts2"
        fx2.mkdir(parents=True)
        heute_iso = datetime.date.today().isoformat()
        d = fx2 / "live-heute"
        d.mkdir()
        (d / "index.md").write_text(
            f'---\ntitle: "Gasrechnung senken: Dein Strategieplan"\n'
            f"date: {heute_iso}T06:00:00Z\ndraft: false\n---\n\nBody.\n",
            encoding="utf-8")
        d = fx2 / "pool-gas"
        d.mkdir()
        (d / "index.md").write_text(
            f'---\ntitle: "Gasrechnung senken: Clevere Herbst-Vorbereitung"\n'
            f"date: {heute_iso}T06:00:00Z\ndraft: true\nreserve: true\n"
            f"---\n\nBody.\n", encoding="utf-8")
        with _als_publikationstag():
            raus2 = publish_to_min(2, posts_dir=fx2, validator=lambda i: True)
        if raus2:
            fehler.append("Dublette am SELBEN Tag wurde veröffentlicht – "
                          "genau das erzeugte die fünf Rückläufer (#387)")

    with tempfile.TemporaryDirectory() as tmp:
        fx = Path(tmp) / "content" / "posts"
        fx.mkdir(parents=True)
        for slug, datum, draft, titel in (
                ("2026-09-25-frisch", "2026-09-25", "false", "Frisch live"),
                ("2026-08-01-alt", "2026-08-01", "false", "Lange her"),
                ("2026-09-25-entwurf", "2026-09-25", "true", "Nur Entwurf")):
            d = fx / slug
            d.mkdir()
            (d / "index.md").write_text(
                f'---\ntitle: "{titel}"\ndate: {datum}T06:00:00Z\n'
                f"draft: {draft}\n---\n\nBody.\n", encoding="utf-8")
        titel = frische_live_titel(fx, heute=datetime.date(2026, 9, 26))
        if list(titel.values()) != ["Frisch live"]:
            fehler.append(f"Sperrliste falsch aufgebaut: {titel} "
                          "(erwartet: nur frische LIVE-Artikel)")

    with tempfile.TemporaryDirectory() as tmp:
        fx = Path(tmp) / "content" / "posts"
        fx.mkdir(parents=True)
        # Reserve-Entwurf
        d1 = fx / "2026-09-01-reserve-a"
        d1.mkdir()
        (d1 / "index.md").write_text(
            "---\ntitle: \"Reserve A\"\n"
            "date: 2026-09-01T06:00:00Z\ndraft: true\n"
            "reserve: true\n---\n\nBody.\n", encoding="utf-8")
        # normaler manueller Entwurf (ohne reserve) – darf NIE angefasst werden
        d2 = fx / "2026-09-01-manuell"
        d2.mkdir()
        (d2 / "index.md").write_text(
            "---\ntitle: \"Manuell\"\n"
            "date: 2026-09-01T06:00:00Z\ndraft: true\n"
            "---\n\nBody.\n", encoding="utf-8")
        pool = reserve_drafts(fx)
        if len(pool) != 1 or pool[0].parent.name != "2026-09-01-reserve-a":
            fehler.append(f"reserve_drafts filtert falsch: {[p.parent.name for p in pool]}")

        # publish_one: draft false, Datum heute, reserve-Marke ersetzt
        # (direkter Funktionsaufruf – unabhängig vom Wochentag testbar)
        published = pool[0]
        publish_one(published, when="2026-09-04T06:00:00Z")
        text = published.read_text(encoding="utf-8")
        if "draft: false" not in text or "reserve: true" in text:
            fehler.append("publish_one ließ draft/reserve-Marke falsch zurück")
        if "reserve_published: 2026-09-04" not in text:
            fehler.append("reserve_published-Audit-Zeile fehlt")
        if "date: 2026-09-04T06:00:00Z" not in text:
            fehler.append("Re-Dating auf heute fehlt")

        # manueller Entwurf bleibt unangetastet (Pool-Liste leer danach)
        if len(reserve_drafts(fx)) != 0:
            fehler.append("manueller Entwurf wurde in den Pool gezählt")
    return fehler


def main() -> int:
    args = sys.argv[1:]
    if "--selftest" in args:
        errs = run_selftest()
        if errs:
            print("🛑 RESERVE-POOL-SELFTEST FEHLGESCHLAGEN:")
            for e in errs:
                print(f"   - {e}")
            return 2
        print("✅ Reserve-Pool-Selbsttest grün (Filter, Publish, "
              "Draft-Schutz, Audit-Zeile, Themen-Sperre gegen Dubletten).")
        return 0

    if "--status" in args or not args:
        pool = reserve_drafts()
        live = live_count_today()
        min_d, max_d = cadence_guard.effective_limits()
        today = datetime.date.today()
        pub = today.weekday() in cadence_guard.PUBLICATION_DAYS
        print(f"Reserve-Pool: {len(pool)} Artikel (Ziel-Obergrenze siehe "
              f"Engine-Env RESERVE_TARGET)")
        for p in pool:
            print(f"  - {p.parent.name}")
        print(f"Heute ({cadence_guard.DAYS_DE[today.weekday()]}, "
              f"{today.isoformat()}): {live} live · Ziel {min_d}–{max_d} · "
              f"{'Publikationstag' if pub else 'kein Publikationstag'}.")
        return 0

    if "--publish-to-min" in args:
        publish_to_min()
        return 0

    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main())
