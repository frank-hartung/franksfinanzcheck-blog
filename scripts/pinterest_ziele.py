#!/usr/bin/env python3
"""PINTEREST-ZIELE – die Wahrheit über ein Pin-Ziel (SSOT, #822, 24.10.2026).

WARUM DIESES MODUL EXISTIERT
Der Pinterest-Check #822 meldete am 20.–24.10.2026 jeden Tag denselben Befund:

    [P10] 2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026
          Artikel-Seite ist ein Meta-Refresh-Alias – nicht direkt pinnen

Der Artikel war am 19.10.2026 nach dem Redaktions-Standard (RS1–RS3) geparkt
(`draft: true`) und seine ehemalige URL in `data/weiterleitungen.yaml` als
Regel C auf die Versicherungs-Pillar-Seite erklärt. Die Meta-Refresh-Seite
unter `static/posts/<slug>/index.html` war damit **die gewollte Auslieferung**,
kein Defekt. Der Check maß nur die falsche Menge: `_post_slugs()` kennt
Entwürfe, P10 unterschied aber nicht zwischen „Live-Artikel, dessen Seite von
einer Weiterleitung überdeckt wird“ (echter Defekt) und „geparkter Artikel,
dessen URL absichtlich weiterleitet“ (Betriebszustand).

Beim Nachmessen kam die eigentliche Pinterest-Schwäche ans Licht: Im
Masterplan `data/pinterest_plan.yaml` standen **sieben Pins** (von 46), deren
Ziel gar keine Artikel-Seite mehr ist – vier geparkte Entwürfe, drei URLs
ohne Inhalt. Ein Pin auf eine Meta-Refresh-Seite ist für Pinterest ein
schwaches Ziel (Scraping ohne Rich-Pin-Basis, Weiterleitung nach dem Klick).
Genau davor warnt P10 seit jeher – nur hatte der Masterplan keine Wache, die
das Ziel gegen den Parkstand prüft.

DIE REGEL (eine Quelle, keine zweite Liste)
  Ein Pin-Ziel ist genau dann zulässig, wenn es nach demselben Maßstab live
  ist, den `scripts/weiterleitungen.py` und `scripts/url_wache.py` benutzen:
  `weiterleitungen.live_urls()` – Frontmatter `draft: true` zählt nicht.

  Status eines Ziels:
    artikel        live (draft: false)                  → zulässig
    pillar         live                                 → zulässig
    weiterleitung  in data/weiterleitungen.yaml erklärt  → KEIN Pin-Ziel
    geparkt        Inhalt existiert, ist aber Entwurf    → KEIN Pin-Ziel
    fehlt          kein Inhalt, keine Erklärung          → KEIN Pin-Ziel
    fremd          nicht franksfinanzcheck.de            → nicht unsere Klasse

  Heilung (deterministisch, ohne Erfindung):
    A/B  Die SSOT erklärt einen gleichwertigen Live-Nachfolger (Regel A:
         Ordner umbenannt, Regel B: gleiche Suchabsicht, geprüft) → der Pin
         wird auf dieses Ziel umgeschrieben (`url` + `blog_url`, UTM bleibt).
    C    Kein gleichwertiger Live-Beitrag (Ziel ist eine Pillar-Seite) → der
         Pin wird nach `data/pinterest_plan_parked.yaml` geparkt. Er bleibt
         vollständig erhalten und wartet auf seinen eigenen Artikel – so
         arbeitet bereits der Repeat-Pin-Schutz (pinterest_plan_guard P6/P7).
    geparkt/fehlt  ohne Live-Nachfolger → parken (kein Ziel erfinden).
    queue  Ein Ziel in `data/pin_queue.yaml` wird NICHT geparkt (die Queue
         leert die Engine nach dem Posting): der Eintrag wird entfernt. Ein
         gepinnter Alias ist teurer als ein nicht gesendeter Pin.

  Warum nicht einfach löschen? Weil ein Pin ein Redaktions-Artefakt ist.
  Parken ist umkehrbar, Löschen nicht (docs/SPAM-SCHUTZ.md, P6/P7).

FAIL-CLOSED
Ist `data/weiterleitungen.yaml` nicht lesbar oder leer, wird **nichts**
verändert: Ein Heiler ohne Quelle würde Ziele raten (Lehre aus C37/#729).
Die chirurgische Kürzung wird vor dem Schreiben nachgeparst – stimmt die
Restmenge nicht, bleibt die Datei unangetastet.

Nutzung:
    python3 scripts/pinterest_ziele.py --check     Befunde zeigen (Exit 0/1)
    python3 scripts/pinterest_ziele.py --fix       heilen (Retarget/Park/Queue)
    python3 scripts/pinterest_ziele.py --selftest  Sabotage-Schutz (Exit 2)
"""
from __future__ import annotations

import io
import os
import re
import sys
import tempfile

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

SITE = "https://franksfinanzcheck.de"
#: Identisch zu pinterest_engine.py / pinterest_link_guard.py – ein UTM-Satz.
PIN_UTM = "?utm_source=pinterest&utm_medium=social&utm_campaign=pins"
#: Quelle der Pin-Ziele (Masterplan), Parkbecken und Engine-Queue.
PLAN_REL = os.path.join("data", "pinterest_plan.yaml")
PARK_REL = os.path.join("data", "pinterest_plan_parked.yaml")
QUEUE_REL = os.path.join("data", "pin_queue.yaml")
#: Die Weiterleitungs-SSOT (Parser: scripts/weiterleitungen.py).
SSOT_REL = os.path.join("data", "weiterleitungen.yaml")
ENTFALLEN_REL = os.path.join("data", "url_entfallen.yaml")
PARK_HINWEIS = ("Von P6/P7 (Repeat-Pin-Schutz) und der Zielwache (#822) geparkte "
                "Pins. Kein Content-Verlust: Diese Pins brauchen ein EIGENES Ziel "
                "(neuer Artikel), dann koennen sie zurueck in den Plan.")

#: Statuswerte – bewusst Konstanten, damit Prüfer und Heiler nicht zwei
#: Vokabulare sprechen (Lehre #729: Prüfer und Heiler widersprachen sich).
ARTIKEL = "artikel"
PILLAR = "pillar"
WEITERLEITUNG = "weiterleitung"
GEPARKT = "geparkt"
FEHLT = "fehlt"
FREMD = "fremd"
LEER = "leer"
ZULAESSIG = (ARTIKEL, PILLAR)
#: Regeln, deren Ziel ein gleichwertiger Live-Beitrag ist (Weiterleitungen A/B).
RETARGET_REGELN = ("A", "B")


class QuellenFehler(RuntimeError):
    """Die SSOT ist nicht lesbar – dann wird nichts verändert (fail-closed)."""


# --------------------------------------------------------------- SSOT lesen

def _weiterleitungs_modul():
    """`scripts/weiterleitungen.py` – der EINE Parser der Weiterleitungs-SSOT."""
    try:
        import weiterleitungen as wl  # noqa: PLC0415 – lazy: ohne PyYAML fail-closed
    except ImportError as exc:  # pragma: no cover – Umgebung ohne PyYAML
        raise QuellenFehler(f"scripts/weiterleitungen.py nicht importierbar: {exc}")
    return wl


def lade_weiterleitungen(root: str = BLOG_DIR) -> dict[str, dict]:
    """`/posts/<slug>/` → {"nach": …, "regel": …, "grund": …} aus der SSOT.

    Eine **leere** Liste ist ein gültiger Zustand (kein einziger Alias in der
    Auslieferung). Fehlt dagegen die Datei oder der Schlüssel `eintraege`,
    ist die Quelle nicht lesbar – dann wird nichts geheilt (fail-closed).
    Ein leerer Zustand darf nie als Dauerbefund enden (C37-Lehre).
    """
    if not os.path.isfile(os.path.join(root, SSOT_REL)):
        raise QuellenFehler(f"{SSOT_REL} fehlt")
    wl = _weiterleitungs_modul()
    if not os.path.isfile(os.path.join(root, ENTFALLEN_REL)):
        # lade_quelle erwartet beide Dateien; eine leere Ersatzquelle wäre eine
        # stille Zweitwahrheit – also lieber fail-closed.
        raise QuellenFehler(f"{ENTFALLEN_REL} fehlt")
    try:
        import yaml  # noqa: PLC0415
        with open(os.path.join(root, SSOT_REL), encoding="utf-8") as fh:
            roh = yaml.safe_load(fh) or {}
        if not isinstance(roh, dict) or "eintraege" not in roh:
            raise QuellenFehler(f"{SSOT_REL} ohne Schlüssel `eintraege`")
        eintraege, _entfallen = wl.lade_quelle(root)
    except QuellenFehler:
        raise
    except Exception as exc:  # noqa: BLE001 – jeder Lesefehler ist ein Quellenfehler
        raise QuellenFehler(f"{SSOT_REL} nicht lesbar: {exc}")
    return {e.get("von"): {"nach": e.get("nach"), "regel": e.get("regel"),
                           "grund": e.get("grund")}
            for e in eintraege if e.get("von")}


def live_urls(root: str = BLOG_DIR) -> set[str]:
    """Live-URLs (Hugo-Logik, `draft: true` ausgenommen) – die Live-SSOT."""
    if not os.path.isfile(os.path.join(root, SSOT_REL)):
        raise QuellenFehler(f"{SSOT_REL} fehlt")
    try:
        return _weiterleitungs_modul().live_urls(root)
    except QuellenFehler:
        raise
    except Exception as exc:  # noqa: BLE001
        raise QuellenFehler(f"Live-Menge nicht lesbar: {exc}")


def _inhalt_pfade(root: str = BLOG_DIR) -> set[str]:
    """Alle URLs mit Inhalt (auch Entwürfe) – die Menge „geparkt“."""
    out: set[str] = set()
    for rel in ("posts", "pillar"):
        base = os.path.join(root, "content", rel)
        if not os.path.isdir(base):
            continue
        for name in os.listdir(base):
            unter = os.path.join(base, name)
            if os.path.isfile(os.path.join(unter, "index.md")):
                out.add(f"/{rel}/{name}/")
    return out


def url_pfad(url: str) -> str:
    """Pin-URL → Pfad der Zielseite: Query weg, Trailing-Slash erzwungen."""
    roh = re.sub(r"\?.*$", "", (url or "").strip())
    roh = re.sub(r"^https?://[^/]+", "", roh).strip()
    if not roh:
        return ""
    return "/" + roh.strip("/") + "/"


def ziel_status(root: str, pfad: str) -> tuple[str, str | None]:
    """(Status, Live-Ziel) für einen Zielpfad – die eine Entscheidung.

    Nimmt Pfade (`/posts/<slug>/`) und volle URLs; beides wird über
    `url_pfad` auf dieselbe Form gebracht, damit kein Aufrufer eine zweite
    Normalisierung erfindet.
    """
    if pfad and "://" in pfad:
        pfad = url_pfad(pfad)
    if not pfad:
        return LEER, None
    if not (pfad.startswith("/posts/") or pfad.startswith("/pillar/")):
        return FREMD, None
    if pfad in live_urls(root):
        return (PILLAR if pfad.startswith("/pillar/") else ARTIKEL), pfad
    weiter = lade_weiterleitungen(root)
    if pfad in weiter:
        return WEITERLEITUNG, (weiter[pfad].get("nach") or None)
    if pfad in _inhalt_pfade(root):
        return GEPARKT, None
    return FEHLT, None


# ------------------------------------------------------------- Plan/Queue IO

def _lade_yaml(pfad: str):
    import yaml  # noqa: PLC0415
    if not os.path.isfile(pfad):
        return None
    with open(pfad, encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def _pins(daten) -> list[dict]:
    if isinstance(daten, dict):
        return [p for p in (daten.get("pins") or []) if isinstance(p, dict)]
    if isinstance(daten, list):
        return [p for p in daten if isinstance(p, dict)]
    return []


def _pin_url(pin: dict) -> str:
    for key in ("url", "link", "blog_url"):
        wert = str(pin.get(key) or "").strip()
        if wert:
            return wert
    return ""


def _zeilen_und_bloecke(text: str) -> tuple[list[str], list[tuple[int, int]]]:
    """Zeilen plus die Bereiche der Pin-Blöcke einer `pins:`-Liste.

    Deckungsgleich mit dem YAML-Parser wird das VOR jedem Schreiben geprüft –
    ein Textheiler, der anders zählt als der Parser, ist die halbe Fassung
    aus C39.
    """
    zeilen = text.splitlines(keepends=True)
    bloecke: list[tuple[int, int]] = []
    start = None
    in_pins = False
    for i, zeile in enumerate(zeilen):
        if re.match(r"^pins:\s*$", zeile):
            in_pins = True
            continue
        if not in_pins:
            continue
        if re.match(r"^- ", zeile):
            if start is not None:
                bloecke.append((start, i))
            start = i
        elif start is not None and zeile.strip() and not zeile[:1].isspace():
            bloecke.append((start, i))
            start = None
            in_pins = False
    if start is not None:
        bloecke.append((start, len(zeilen)))
    return zeilen, bloecke


def _setze_feld(block: list[str], feld: str, wert: str) -> list[str]:
    muster = re.compile(rf"^(\s*){re.escape(feld)}:\s*.*$")
    neu, getroffen = [], False
    for zeile in block:
        m = muster.match(zeile)
        if m:
            neu.append(f"{m.group(1)}{feld}: {wert}\n")
            getroffen = True
        else:
            neu.append(zeile)
    if not getroffen:  # Feld fehlte: hinter `titel:` (bzw. Zeile 1) einfügen
        neu.insert(1, f"  {feld}: {wert}\n")
    return neu


def _parke(root: str, pins: list[dict]) -> int:
    """Hängt Pins an das Parkbecken (dedupliziert) – gibt die Zahl der Neuen."""
    import yaml  # noqa: PLC0415
    pfad = os.path.join(root, PARK_REL)
    daten = _lade_yaml(pfad) or {}
    if not isinstance(daten, dict):
        daten = {"pins": _pins(daten)}
    vorhanden = _pins(daten)
    schluessel = {(_titel(p), _pin_url(p)) for p in vorhanden}
    neu = [p for p in pins if (_titel(p), _pin_url(p)) not in schluessel]
    if not neu:
        return 0
    daten.setdefault("hinweis", PARK_HINWEIS)
    daten["pins"] = vorhanden + neu
    with open(pfad, "w", encoding="utf-8") as fh:
        yaml.safe_dump(daten, fh, allow_unicode=True, sort_keys=False, width=1000)
    return len(neu)


def _titel(pin: dict) -> str:
    return str(pin.get("titel") or pin.get("title") or "").strip()


def _entscheidung(root: str, pfad: str) -> tuple[str, str | None, str | None]:
    """(Status, Live-Ziel, Regel) – eine Stelle für Prüfer und Heiler."""
    status, ziel = ziel_status(root, pfad)
    regel = None
    if status == WEITERLEITUNG:
        regel = lade_weiterleitungen(root).get(pfad, {}).get("regel")
    return status, ziel, regel


# ---------------------------------------------------------------- Befunde

def _pruefe_plan(root: str) -> None:
    """Der Masterplan ist Pflicht: fehlt er, ist P14 nicht messbar (C2)."""
    if not os.path.isfile(os.path.join(root, PLAN_REL)):
        raise QuellenFehler(f"{PLAN_REL} fehlt – Pin-Ziele nicht messbar")


def befunde(root: str = BLOG_DIR) -> list[dict]:
    """Jedes Pin-Ziel aus Masterplan und Queue, das KEINE Live-Seite ist."""
    _pruefe_plan(root)
    out: list[dict] = []
    for rel in (PLAN_REL, QUEUE_REL):
        daten = _lade_yaml(os.path.join(root, rel))
        for pin in _pins(daten):
            url = _pin_url(pin)
            pfad = url_pfad(url)
            status, _ziel, regel = _entscheidung(root, pfad)
            if status in ZULAESSIG:
                continue
            out.append({"quelle": rel, "tag": pin.get("tag"), "titel": _titel(pin),
                        "pfad": pfad, "status": status, "regel": regel, "url": url})
    return out


def _kurve(root: str, rel: str, zu_entfernen: set[int],
           ersatz: dict[int, list[str]]) -> str | None:
    """Chirurgische Kürzung einer `pins:`-Liste – mit Beweis vor dem Schreiben."""
    pfad = os.path.join(root, rel)
    if not os.path.isfile(pfad):
        return None
    with open(pfad, encoding="utf-8") as fh:
        text = fh.read()
    zeilen, bloecke = _zeilen_und_bloecke(text)
    pins = _pins(_lade_yaml(pfad))
    if len(bloecke) != len(pins):
        raise QuellenFehler(f"{rel}: {len(bloecke)} Textblöcke ≠ {len(pins)} Pins "
                            "– fail-closed, nichts geschrieben")
    if not zu_entfernen and not ersatz:
        return None
    ausgabe: list[str] = []
    pos = 0
    for i, (a, b) in enumerate(bloecke):
        ausgabe.extend(zeilen[pos:a])
        pos = b
        if i in zu_entfernen:
            continue
        ausgabe.extend(ersatz.get(i, zeilen[a:b]))
    ausgabe.extend(zeilen[pos:])
    neu_text = "".join(ausgabe)

    import yaml  # noqa: PLC0415
    neu_pins = _pins(yaml.safe_load(io.StringIO(neu_text)))
    erwartet = len(pins) - len(zu_entfernen)
    if len(neu_pins) != erwartet:
        raise QuellenFehler(f"{rel}: Kürzung {len(pins)} → {len(neu_pins)}, "
                            f"erwartet {erwartet} – nichts geschrieben")
    # Retargets müssen im Ergebnis angekommen sein.
    for i, block in ersatz.items():
        neu_url = next((z.split("url: ", 1)[1].strip() for z in block
                        if z.strip().startswith("url: ")), None)
        if neu_url and neu_url not in neu_text:
            raise QuellenFehler(f"{rel}: Retarget nicht geschrieben – fail-closed")
    return neu_text


def heile(root: str = BLOG_DIR, fix: bool = False) -> tuple[list[dict], list[dict]]:
    """Prüft und (mit `fix=True`) heilt Masterplan und Queue.

    Rückgabe: (offene Befunde NACH der Heilung, Liste der Heilungen).
    """
    if not fix:
        return befunde(root), []

    _pruefe_plan(root)
    heilungen: list[dict] = []
    for rel in (PLAN_REL, QUEUE_REL):
        pfad_datei = os.path.join(root, rel)
        if not os.path.isfile(pfad_datei):
            continue
        pins = _pins(_lade_yaml(pfad_datei))
        with open(pfad_datei, encoding="utf-8") as fh:
            text = fh.read()
        zeilen, bloecke = _zeilen_und_bloecke(text)
        if len(bloecke) != len(pins):
            raise QuellenFehler(f"{rel}: {len(bloecke)} Textblöcke ≠ {len(pins)} "
                                "Pins – fail-closed, nichts verändert")
        zu_entfernen: set[int] = set()
        ersatz: dict[int, list[str]] = {}
        parken: list[dict] = []
        for i, pin in enumerate(pins):
            ziel_pfad = url_pfad(_pin_url(pin))
            status, ziel, regel = _entscheidung(root, ziel_pfad)
            if status in ZULAESSIG:
                continue
            if (rel == PLAN_REL and status == WEITERLEITUNG
                    and regel in RETARGET_REGELN and ziel
                    and ziel_status(root, ziel)[0] in ZULAESSIG):
                neu_url = SITE + ziel + PIN_UTM
                a, b = bloecke[i]
                block = _setze_feld(zeilen[a:b], "url", neu_url)
                block = _setze_feld(block, "blog_url", neu_url)
                ersatz[i] = block
                heilungen.append({"aktion": "retarget", "tag": pin.get("tag"),
                                  "titel": _titel(pin), "von": ziel_pfad,
                                  "nach": ziel, "regel": regel, "quelle": rel})
                continue
            zu_entfernen.add(i)
            if rel == PLAN_REL:
                parken.append(pin)
            heilungen.append({"aktion": "parken" if rel == PLAN_REL else "queue",
                              "tag": pin.get("tag"), "titel": _titel(pin),
                              "von": ziel_pfad, "status": status, "regel": regel,
                              "quelle": rel})
        if not zu_entfernen and not ersatz:
            continue
        neu_text = _kurve(root, rel, zu_entfernen, ersatz)
        if neu_text is None:
            continue
        if parken and _parke(root, parken) != len(parken):
            raise QuellenFehler(f"{PARK_REL}: Parken unvollständig – {rel} unverändert")
        with open(pfad_datei, "w", encoding="utf-8") as fh:
            fh.write(neu_text)
    return befunde(root), heilungen


def entferne_weiterleitung(root: str = BLOG_DIR, pfad: str = "",
                           fix: bool = False) -> tuple[bool, str]:
    """Entfernt einen ungültigen SSOT-Eintrag (Live-Seite würde überdeckt).

    Fail-closed: nur ein einzeiliger `- {von: …}`-Eintrag wird chirurgisch
    entfernt, und erst nach dem Beweis, dass die Datei danach parst und der
    Eintrag wirklich fehlt.
    """
    datei = os.path.join(root, SSOT_REL)
    if not os.path.isfile(datei):
        return False, f"{SSOT_REL} fehlt"
    with open(datei, encoding="utf-8") as fh:
        zeilen = fh.read().splitlines(keepends=True)
    treffer = [i for i, z in enumerate(zeilen)
               if z.lstrip().startswith("- {") and f'von: "{pfad}"' in z]
    if len(treffer) != 1:
        return False, (f"{pfad}: {len(treffer)} SSOT-Zeile(n) gefunden – kein "
                       "eindeutiger Einzeiler, Handentscheidung nötig")
    if not fix:
        return True, f"{pfad}: SSOT-Eintrag würde entfernt"
    neu = "".join(z for i, z in enumerate(zeilen) if i not in set(treffer))
    try:
        import yaml  # noqa: PLC0415
        eintraege = (yaml.safe_load(neu) or {}).get("eintraege") or []
    except Exception as exc:  # noqa: BLE001
        return False, f"{pfad}: Datei nach Kürzung nicht lesbar ({exc}) – nicht geschrieben"
    if any(e.get("von") == pfad for e in eintraege):
        return False, f"{pfad}: Eintrag wäre noch vorhanden – nicht geschrieben"
    with open(datei, "w", encoding="utf-8") as fh:
        fh.write(neu)
    return True, f"{pfad}: ungültigen SSOT-Eintrag entfernt (Live-Artikel gewinnt)"


# ------------------------------------------------------------- Selbsttest

def _selftest() -> list[str]:
    """Eingefrorene Fälle – Regel und Heilung, ohne Netz und ohne Hugo."""
    f: list[str] = []
    if SITE != "https://franksfinanzcheck.de":
        f.append("SITE verändert")
    if PIN_UTM != "?utm_source=pinterest&utm_medium=social&utm_campaign=pins":
        f.append("PIN_UTM verändert")
    if ZULAESSIG != (ARTIKEL, PILLAR):
        f.append("zulässige Status verändert")
    if RETARGET_REGELN != ("A", "B"):
        f.append("Retarget-Regeln verändert (C ist eine Pillar-Seite, kein Beitrag)")
    for roh, muss in (
        ("https://franksfinanzcheck.de/posts/x/?utm_source=pinterest", "/posts/x/"),
        ("https://www.franksfinanzcheck.de/posts/x", "/posts/x/"),
        ("/posts/x/", "/posts/x/"),
        ("https://franksfinanzcheck.de/pillar/strom-sparen", "/pillar/strom-sparen/"),
        ("", ""),
    ):
        if url_pfad(roh) != muss:
            f.append(f"url_pfad({roh!r}) = {url_pfad(roh)!r}, erwartet {muss!r}")

    with tempfile.TemporaryDirectory() as tmp:
        root = tmp
        for slug, draft in (("live", False), ("geparkt", True)):
            d = os.path.join(root, "content", "posts", slug)
            os.makedirs(d)
            with open(os.path.join(d, "index.md"), "w", encoding="utf-8") as fh:
                fh.write("---\ntitle: X\n" + ("draft: true\n" if draft else "") + "---\n")
        os.makedirs(os.path.join(root, "content", "pillar", "versicherungen"))
        with open(os.path.join(root, "content", "pillar", "versicherungen", "index.md"),
                  "w", encoding="utf-8") as fh:
            fh.write("---\ntitle: P\n---\n")
        os.makedirs(os.path.join(root, "data"))
        ssot = ('eintraege:\n'
                '  - {von: "/posts/alt/", nach: "/posts/live/", regel: "B", '
                'grund: "gleiche Suchabsicht"}\n'
                '  - {von: "/posts/geparkt/", nach: "/pillar/versicherungen/", '
                'regel: "C", grund: "kein gleichwertiger Beitrag"}\n')
        with open(os.path.join(root, SSOT_REL), "w", encoding="utf-8") as fh:
            fh.write(ssot)
        with open(os.path.join(root, ENTFALLEN_REL), "w", encoding="utf-8") as fh:
            fh.write("eintraege: []\n")
        with open(os.path.join(root, PLAN_REL), "w", encoding="utf-8") as fh:
            fh.write("pins:\n"
                     "- tag: 1\n  titel: Live\n  url: https://franksfinanzcheck.de/posts/live/\n"
                     "  blog_url: https://franksfinanzcheck.de/posts/live/\n"
                     "- tag: 2\n  titel: Alt\n  url: https://franksfinanzcheck.de/posts/alt/\n"
                     "  blog_url: https://franksfinanzcheck.de/posts/alt/\n"
                     "- tag: 3\n  titel: Geparkt\n"
                     "  url: https://franksfinanzcheck.de/posts/geparkt/\n"
                     "  blog_url: https://franksfinanzcheck.de/posts/geparkt/\n"
                     "- tag: 4\n  titel: Fehlt\n"
                     "  url: https://franksfinanzcheck.de/posts/fehlt/\n"
                     "  blog_url: https://franksfinanzcheck.de/posts/fehlt/\n")

        if ziel_status(root, "/posts/live/")[0] != ARTIKEL:
            f.append("Live-Artikel nicht als artikel erkannt")
        if ziel_status(root, "/posts/geparkt/")[0] != WEITERLEITUNG:
            f.append("erklärte Weiterleitung nicht erkannt")
        if ziel_status(root, "/posts/fehlt/")[0] != FEHLT:
            f.append("fehlendes Ziel nicht erkannt")
        if ziel_status(root, "/posts/geparkt-nur-draft/")[0] != FEHLT:
            f.append("unbekanntes Ziel nicht als fehlt erkannt")

        # Quellenausfall: nichts wird verändert.
        vorher = open(os.path.join(root, PLAN_REL), encoding="utf-8").read()
        os.rename(os.path.join(root, SSOT_REL), os.path.join(root, "ssot.bak"))
        try:
            heile(root, fix=True)
            f.append("fehlende SSOT wird nicht fail-closed erkannt")
        except QuellenFehler:
            pass
        if open(os.path.join(root, PLAN_REL), encoding="utf-8").read() != vorher:
            f.append("ohne SSOT wurde der Plan verändert")
        os.rename(os.path.join(root, "ssot.bak"), os.path.join(root, SSOT_REL))

        offen, geheilt = heile(root, fix=False)
        if len(offen) != 3:
            f.append(f"Prüfung ohne Fix: {len(offen)} Befunde, erwartet 3")
        if geheilt:
            f.append("Prüfung ohne Fix hat geheilt")
        offen, geheilt = heile(root, fix=True)
        aktionen = sorted(h["aktion"] for h in geheilt)
        if aktionen != ["parken", "parken", "retarget"]:
            f.append(f"Heilaktionen {aktionen}, erwartet parken/parken/retarget")
        if offen:
            f.append(f"nach der Heilung offen: {offen}")
        plan = open(os.path.join(root, PLAN_REL), encoding="utf-8").read()
        park = open(os.path.join(root, PARK_REL), encoding="utf-8").read()
        if "/posts/alt/" in plan or plan.count("- tag:") != 2:
            f.append(f"Plan nach Heilung falsch ({plan.count('- tag:')} Pins)")
        if PIN_UTM not in plan or "/posts/live/" not in plan:
            f.append("Retarget hat Ziel oder UTM-Satz verloren")
        if park.count("- tag:") != 2:
            f.append(f"Parkbecken hat {park.count('- tag:')} Pins, erwartet 2")
        if "hinweis" not in park:
            f.append("Parkbecken ohne Hinweis (Content-Verlust nicht erklärt)")
        # Idempotenz
        offen, geheilt = heile(root, fix=True)
        if (open(os.path.join(root, PLAN_REL), encoding="utf-8").read() != plan
                or open(os.path.join(root, PARK_REL), encoding="utf-8").read() != park
                or offen or geheilt):
            f.append("Heilung ist nicht idempotent")

        # Live-Artikel mit SSOT-Eintrag: Eintrag wird entfernt, Artikel gewinnt.
        with open(os.path.join(root, SSOT_REL), "w", encoding="utf-8") as fh:
            fh.write(ssot + '  - {von: "/posts/live/", nach: "/pillar/versicherungen/", '
                            'regel: "C", grund: "Sabotage-Test"}\n')
        ok, meldung = entferne_weiterleitung(root, "/posts/live/", fix=True)
        import yaml  # noqa: PLC0415
        nachher = (yaml.safe_load(open(os.path.join(root, SSOT_REL),
                                       encoding="utf-8")) or {}).get("eintraege") or []
        if not ok or any(e.get("von") == "/posts/live/" for e in nachher):
            f.append(f"SSOT-Eintrag eines Live-Artikels nicht entfernt ({meldung})")
        if len(nachher) != 2:
            f.append(f"SSOT nach Kürzung hat {len(nachher)} Einträge, erwartet 2")
        ok, _ = entferne_weiterleitung(root, "/posts/live/", fix=False)
        if ok:
            f.append("Prüfung ohne Fix hat die SSOT verändert")
    return f


def main() -> int:
    st = _selftest()
    if st:
        print("🛑 PINTEREST-ZIELE-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        for e in st:
            print(f"   {e}")
        return 2
    if "--selftest" in sys.argv:
        print("✅ Pinterest-Zielwache-Selbsttest ok")
        return 0
    fix = "--fix" in sys.argv
    try:
        offen, geheilt = heile(BLOG_DIR, fix=fix)
    except QuellenFehler as exc:
        print(f"🛑 fail-closed: {exc} – nichts verändert.")
        return 2
    for h in geheilt:
        if h["aktion"] == "retarget":
            print(f"  ✅ [ZIEL] Tag {h['tag']}: {h['von']} → {h['nach']} "
                  f"(Regel {h['regel']}, gleichwertiger Live-Beitrag)")
        elif h["aktion"] == "queue":
            print(f"  ✅ [QUEUE] Tag {h['tag']}: {h['von']} ist {h['status']} – "
                  "Eintrag entfernt")
        else:
            print(f"  ✅ [PARK] Tag {h['tag']}: {h['von']} ist {h['status']} – "
                  "Pin geparkt (bleibt erhalten)")
    for o in offen:
        print(f"  ❌ [ZIEL] Tag {o['tag']} ({o['titel'][:40]}): "
              f"{o['pfad'] or 'kein Ziel'} ist {o['status']}")
    print(f"Zielwache: {len(offen)} offen, {len(geheilt)} geheilt "
          f"({'FIX' if fix else 'CHECK'})")
    return 1 if offen else 0


if __name__ == "__main__":
    sys.exit(main())
