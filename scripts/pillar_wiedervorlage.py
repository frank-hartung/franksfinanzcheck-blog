#!/usr/bin/env python3
"""pillar_wiedervorlage.py – DIE WIEDERVORLAGE, DIE AUCH WIRKLICH FEUERT

WARUM ES DIESE WACHE GIBT (Befund 04.11.2026, Vorgang WF-0032)
---------------------------------------------------------------
Am 04.11.2026 um 01:25 UTC veröffentlichte die Automatik zwei Artikel des
Versicherungs-Clusters (`draft: false`, `date: 2026-11-04T01:25:00Z`):

    2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst
    2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen

Der Versicherungs-Pillar verlinkte sie nicht. Er sagte weiter „(Ratgeber
in Vorbereitung)“ – auf einer Live-Money-Seite, während der verlinkte
Ratgeber längst ausgeliefert wurde. Zwei echte Artikel, ein toter Satz.

DAS WAR NICHT UNBEKANNT
-----------------------
`scripts/tests/test_versicherungs_cluster_verlinkung.py` ist genau dafür
gebaut. Sein Kopf sagt es selbst: „Dieser Test ist die Wiedervorlage. Er
ist heute grün […] und wird rot, sobald einer der vier live ist und im
Pillar fehlt.“ Er war rot, korrekt, und NIEMAND SAH ES.

Der Grund ist eine Ordnung, kein Versehen: Die Wiedervorlage lief
ausschließlich in `publication-reliability-tests.yml`, und dieser Workflow
startet NUR bei `pull_request`. Der Artikel ging über einen Automatik-
Commit auf `main` live – ohne Pull Request. Die Wache, die den Fall
bewachen sollte, konnte ihn bauartbedingt nicht sehen. Sie war nicht
kaputt; sie war am falschen Ort.

WAS HIER ANDERS IST
-------------------
1. Läuft DAILY auf `main` (`blog-health-daily.yml`) – dort, wo die
   Automatik schreibt, nicht nur dort, wo Menschen pushen.
2. Urteilt für ALLE Polemik-Seiten (`content/pillar/*/index.md`), nicht
   für einen hartkodierten Cluster. Der nächste Fall wird nicht
   nachgetragen werden müssen.
3. Prüft BEIDE Richtungen: live ⇒ verlinkt · Entwurf ⇒ nicht verlinkt
   (ein Link auf einen Entwurf ist ein totes Linkziel, Befund W11).
4. Meldet Platzhalter als eigene Klasse: „(Ratgeber in Vorbereitung)“
   neben einem LIVE-Artikel derselben Überschrift ist eine Falschaussage,
   auch wenn irgendwo ein Link steht.
5. Der Befund wird als Vorgang geführt und geschlossen
   (`pillar_wiedervorlage_issue.py`) – ein Dauerbefund ohne Vorgang ist
   eine Notiz, kein Auftrag.

EXIT-VERTRAG (dreistufig, fail-closed – dasselbe Muster wie #1024)
-----------------------------------------------------------------
  0  sauber                     → Vorgang schließen
  1  Bestandsbefund             → Vorgang öffnen/aktualisieren
  2  Werkzeugfehler             → NIEMALS grün; zusätzlich hartes Rot

Ein fehlender Exit ist kein grüner Exit.

AUFRUF
  python3 scripts/pillar_wiedervorlage.py --check        # Betrieb
  python3 scripts/pillar_wiedervorlage.py --json         # maschinell
  python3 scripts/pillar_wiedervorlage.py --selftest     # ohne Repo
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INHALT = ROOT / "content"
PILLAR_DIR = INHALT / "pillar"
POSTS_DIR = INHALT / "posts"
VERTRAG = ROOT / "data" / "pillar_pflichtlinks.yaml"

# Ein Pillar-Link ist relativ und zeigt auf einen Post-Ordner – dieselbe
# Lesart wie in `test_versicherungs_cluster_verlinkung.py`, damit beide
# Wachen nicht auseinanderdriften (ein absoluter `/posts/…`-Link oder ein
# `/go/`-Gateway ist KEIN Artikel-Link).
PILLAR_LINK = re.compile(r"\]\(\.\./\.\./posts/([^)/]+)/?\)")

# Überschriften-Zeilen (H1–H3). Die Zuordnung „welcher Abschnitt spricht
# über welchen Artikel“ läuft über die Überschrift, nicht über Zeilennähe:
# Zeilennähe ist bei Fließtext eine Vermutung, eine Überschrift ist eine
# Aussage.
UEBERSCHRIFT = re.compile(r"^(#{1,3})\s+(.+?)\s*$", re.M)

# Platzhalter, die eine Nicht-Existenz behaupten. Sie sind nur dann ein
# Befund, wenn dieselbe Überschrift einen LIVE-Artikel als Thema hat.
PLATZHALTER = re.compile(
    r"\((?:Ratgeber\s+)?(?:in\s+Vorbereitung|folgt|geplant|demnächst)\)"
    r"|Ratgeber\s+in\s+Vorbereitung|bald\s+verfügbar",
    re.I,
)


@dataclass
class Befund:
    """Ein Befund mit Klasse, Beweis und Reparaturhinweis."""

    klasse: str
    pillar: str
    meldung: str
    beleg: str = ""

    def zeile(self) -> str:
        return f"[{self.klasse}] {self.pillar}: {self.meldung}"

    def als_dict(self) -> dict:
        return {"klasse": self.klasse, "pillar": self.pillar,
                "meldung": self.meldung, "beleg": self.beleg}


class WerkzeugFehler(RuntimeError):
    """Ein Defekt in DIESEM Werkzeug – nicht im Bestand.

    Absichtlich eine eigene Klasse: `except Exception` ist im Ergebnis-
    pfad verboten (#1024). Was hier geworfen wird, muss mit Exit 2
    durchschlagen und darf nie als „Bestandsbefund“ durchgehen.
    """


@dataclass
class Artikel:
    slug: str
    titel: str
    entwurf: bool
    pillar: str = ""          # das DEKLARIERTE Themenfeld (`pillar:` im Kopf)
    pfad: str = ""
    datum: str = ""


@dataclass
class Urteil:
    befund: list[Befund] = field(default_factory=list)
    geprueft: int = 0
    pillar: int = 0
    live: int = 0
    entwuerfe: int = 0
    verlinkt: int = 0

    @property
    def sauber(self) -> bool:
        return not self.befund


# ---------------------------------------------------------------------------
#  Bestand lesen (Frontmatter so lesen, wie Hugo ihn baut)
# ---------------------------------------------------------------------------

def frontmatter(text: str) -> dict[str, str]:
    """Die flachen `schlüssel: wert`-Zeilen des YAML-Kopfs.

    Bewusst flach: Diese Wache braucht `draft`, `title`, `date` und
    `pillar`. Ein vollständiger YAML-Parser wäre eine Abhängigkeit ohne
    Gegenwert – und ein Fehler darin wäre wieder ein Werkzeugfehler, der
    wie ein Bestandsbefund aussieht.
    """
    if not text.startswith("---"):
        return {}
    teile = text.split("---")
    if len(teile) < 3:
        return {}
    werte: dict[str, str] = {}
    for zeile in teile[1].splitlines():
        if not zeile.strip() or zeile.lstrip().startswith("#"):
            continue
        schluessel, trenner, wert = zeile.partition(":")
        if not trenner:
            continue
        werte[schluessel.strip().lower()] = wert.strip().strip('"').strip("'")
    return werte


def ist_entwurf(fm: dict[str, str]) -> bool:
    """`draft: true` – alles andere ist live (Hugo-Default ist `false`)."""
    return fm.get("draft", "").lower() in {"true", "yes", "1"}


def artikel_lesen(pfad: Path) -> Artikel:
    """Ein Artikel mit den Feldern, über die hier geurteilt wird."""
    try:
        text = pfad.read_text(encoding="utf-8")
    except OSError as fehler:                      # Datenfehler, kein Defekt
        raise WerkzeugFehler(f"{pfad}: {fehler}") from fehler
    fm = frontmatter(text)
    return Artikel(
        slug=pfad.parent.name,
        titel=fm.get("title", ""),
        entwurf=ist_entwurf(fm),
        pillar=fm.get("pillar", ""),
        pfad=str(pfad.relative_to(ROOT)) if pfad.is_relative_to(ROOT) else str(pfad),
        datum=fm.get("date", ""),
    )


# ---------------------------------------------------------------------------
#  Zuordnung: Welcher Artikel gehört zu welcher Pillar-Seite?
# ---------------------------------------------------------------------------

def besprochene_artikel(pillar_name: str,
                        artikel: dict[str, Artikel],
                        verlinkt: set[str]) -> dict[str, Artikel]:
    """Die Artikel, die diese Pillar-Seite inhaltlich vertritt.

    Ein erster Entwurf dieser Wache verglich WORTS TÄMME zwischen
    Überschrift und Titel – und meldete 15 Befunde, von denen 14 falsch
    waren: „DSL Hacks“ passte auf „Versicherungs-Pyramide“ (beide enthalten
    „wirklich“), ein Tagesgeld-Artikel auf „Marktradar“. Wortähnlichkeit
    ist bei deutschen Komposita keine Aussage über Zugehörigkeit.

    Die verlässliche Quelle ist die DEKLARATION: Jeder Artikel trägt
    `pillar:` im Frontmatter, und die Pillar-Seite heißt wie dieses Feld
    (`content/pillar/<pillar>/index.md`). Das ist eine Tatsache, die der
    Autor setzt – keine Vermutung über Wortwahl.

    Zusätzlich zählt, was die Seite selbst VERLINKT: Ein Link auf einen
    Artikel eines anderen Themenfelds ist eine bewusste Querverbindung
    (und wird von `link_guard.py` geprüft, nicht von hier).
    """
    eigene = {slug: art for slug, art in artikel.items()
              if art.pillar == pillar_name}
    fremde_links = {slug for slug in verlinkt
                    if slug in artikel and artikel[slug].pillar != pillar_name}
    return eigene, fremde_links


# ---------------------------------------------------------------------------
#  Das Urteil
# ---------------------------------------------------------------------------

def pruefe(pillar_pfad: Path,
           artikel: dict[str, Artikel],
           text: str | None = None,
           pflicht: list[str] | None = None) -> list[Befund]:
    """Befunde einer Pillar-Seite. `text` erlaubt Prüfung ohne Datei.

    Geprüft wird der VERTRAG (data/pillar_pflichtlinks.yaml), nicht der
    gesamte Bestand: Ein Pillar ist eine kuratierte Seite. „Jeder der 76
    Live-Artikel muss hier stehen“ wäre Rauschen – und Rauschen wird
    abgeschaltet. Die vier Artikel aus GSC-OPTIMIERUNGSPLAN §14.2 sind
    dagegen ein Anspruch, den jemand aufgeschrieben hat.
    """
    if text is None:
        try:
            text = pillar_pfad.read_text(encoding="utf-8")
        except OSError as fehler:
            raise WerkzeugFehler(f"{pillar_pfad}: {fehler}") from fehler

    name = pillar_pfad.parent.name
    befund: list[Befund] = []
    verlinkt = {m.group(1) for m in PILLAR_LINK.finditer(text)}
    pflicht = pflicht or []

    # R0 – Der Vertrag darf nicht ins Leere zeigen.
    for slug in pflicht:
        if slug not in artikel:
            raise WerkzeugFehler(
                f"data/pillar_pflichtlinks.yaml nennt „{slug}“ für „{name}“, "
                "aber dieser Artikel existiert nicht (mehr). "
                "Vertrag korrigieren – nicht die Wache.")

    # R1 – DIE WIEDERVORLAGE: Pflicht-Artikel ist live, aber nicht verlinkt.
    for slug in pflicht:
        art = artikel[slug]
        if art.entwurf or slug in verlinkt:
            continue
        befund.append(Befund(
            "P1-PFLICHTLINK-FEHLT", name,
            f"Artikel „{art.titel or slug}“ ist live, die Pillar-Seite verlinkt "
            "ihn aber nicht.",
            f"Ziel: ../../posts/{slug}/ · {art.pfad}"))

    # R2 – Entwurf verlinkt: sofort ein totes Linkziel (Befund W11).
    for slug in sorted(verlinkt):
        art = artikel.get(slug)
        if art is None:
            # Link auf einen nicht existierenden Post: anderes Ressort
            # (`link_guard.py`), hier nur Entwurf vs. live.
            continue
        if art.entwurf:
            befund.append(Befund(
                "P2-ENTWURF-VERLINKT", name,
                f"Die Seite verlinkt „{art.titel or slug}“, der noch Entwurf "
                "ist – das erzeugt sofort ein totes Linkziel.",
                f"../../posts/{slug}/"))

    # R3 – Platzhalter, obwohl der Artikel live ist. „(Ratgeber in
    # Vorbereitung)“ über einem ausgelieferten Ratgeber ist eine
    # Falschaussage auf einer Geldseite – auch wenn daneben ein Link steht.
    #
    # Bezug ist der SATZTEIL VOR dem Platzhalter, nicht die ganze Zeile:
    # „… ein eigener Wohngebäudeversicherungs-Vergleich die Tarifwahl
    # (Ratgeber in Vorbereitung). Wer …, findet im Vorsorge-Update …“ –
    # der Platzhalter gehört zum Wohngebäude-Vergleich, nicht zum
    # Vorsorge-Update, das nur zufällig in derselben Zeile verlinkt wird.
    # Eine Zeilen-Heuristik meldete deshalb den falschen Artikel.
    for stelle in PLATZHALTER.finditer(text):
        bezug = _bezug_vor(text, stelle.start())
        # Klammern sind hier keine Kosmetik: `a and b or c` bindet als
        # `(a and b) or c` – und `c` hätte den Entwurfs-Filter ausgehebelt.
        # Der Fehler war unsichtbar, bis ein Test einen Platzhalter über
        # einem ENTWURF prüfte (er hätte melden dürfen müssen: nichts).
        treffer = [
            (len(_woerter(artikel[slug].titel or slug) & _woerter(bezug)), slug)
            for slug in pflicht
            if (not artikel[slug].entwurf)
            and (slug in bezug or _zeile_nennt(bezug, artikel[slug]))
        ]
        treffer = [(zahl, slug) for zahl, slug in treffer if zahl >= 2]
        if not treffer:
            continue
        bestes = max(treffer)[1]
        art = artikel[bestes]
        befund.append(Befund(
            "P3-PLATZHALTER-TROTZ-LIVE", name,
            f"Die Seite sagt „{stelle.group(0)}“, aber "
            f"„{art.titel or bestes}“ ist live.",
            _zeile_um(text, stelle.start(), stelle.end()).strip()[:180]))

    # R4 – Link auf einen Artikel eines FREMDEN Themenfelds: erlaubt, aber
    # sichtbar. Eine Querverbindung ist eine redaktionelle Entscheidung;
    # unentdeckt bleibt sie eine Verwechslung.
    for slug in sorted(verlinkt):
        art = artikel.get(slug)
        if art is None or not art.pillar or art.pillar == name:
            continue
        befund.append(Befund(
            "P4-QUERVERBINDUNG", name,
            f"Die Seite verlinkt „{art.titel or slug}“ aus dem Themenfeld "
            f"„{art.pillar}“.",
            "Zulässig – aber bewusst: Der Artikel sollte inhaltlich passen."))

    return befund


def _bezug_vor(text: str, position: int, grenze: int = 220) -> str:
    """Der Satzteil vor `position` – worauf sich ein Platzhalter bezieht.

    Geschnitten wird am letzten Satzzeichen (`.`, `!`, `?`) davor. Eine
    feste Zeichenzahl als Obergrenze hält den Vergleich lokal: Ohne sie
    zöge ein früherer Satz der Zeile Artikel heran, die mit dem
    Platzhalter nichts zu tun haben.
    """
    fenster = text[max(0, position - grenze):position]
    schnitt = max(fenster.rfind("."), fenster.rfind("!"), fenster.rfind("?"))
    return fenster[schnitt + 1:] if schnitt != -1 else fenster


def _zeile_um(text: str, start: int, ende: int) -> str:
    """Die Zeile, in der [start, ende) liegt – ohne Zeilenumbruch."""
    zeilen_start = text.rfind("\n", 0, start) + 1
    zeilen_ende = text.find("\n", ende)
    return text[zeilen_start:zeilen_ende if zeilen_ende != -1 else len(text)]


def _zeile_nennt(zeile: str, art: Artikel) -> bool:
    """Nennt diese Zeile das Thema? Zwei gemeinsame Wortstämme in EINER Zeile.

    Enger als die abgelöste Abschnitts-Zuordnung: Für den Platzhalter-Fall
    genügt das, weil der Platzhalter unmittelbar beim Gegenstand des Satzes
    steht. Über Abschnitte hinweg ist Wortähnlichkeit dagegen keine Aussage
    („DSL Hacks“ passte auf „Versicherungs-Pyramide“ – beide enthalten
    „wirklich“).
    """
    return len(_woerter(art.titel or art.slug) & _woerter(zeile)) >= 2


def vertrag_lesen(pfad: Path = VERTRAG) -> dict[str, list[str]]:
    """Der Pflichtlink-Vertrag: Pillar-Name → Liste von Artikel-Slugs.

    Bewusst ohne YAML-Bibliothek: Die Datei ist eine flache Zuordnung
    (Pillar → Slug-Liste), und ein Parserfehler wäre wieder ein
    Werkzeugfehler, der wie ein Bestandsbefund aussieht. Ein Format, das
    man in zehn Zeilen lesen kann, braucht keinen Parser, den man nicht
    mehr sieht.

    Die drei Namen `vertrag`, `begruendung` und `artikel` sind STRUKTUR,
    keine Pillar-Seiten: `vertrag` ist die Überschrift, die anderen beiden
    sind Felder EINES Pillars. Sie ändern deshalb nicht, wohin die
    folgenden `- slug`-Zeilen gehören.
    """
    if not pfad.is_file():
        raise WerkzeugFehler(f"Pflichtlink-Vertrag fehlt: {pfad}")

    struktur = {"vertrag", "begruendung", "artikel"}
    vertrag: dict[str, list[str]] = {}
    aktuell: str | None = None

    for nummer, roh in enumerate(pfad.read_text(encoding="utf-8").splitlines(), 1):
        zeile = roh.split("#", 1)[0].rstrip()
        if not zeile.strip():
            continue
        rumpf = zeile.lstrip()

        if rumpf.startswith("- "):
            if aktuell is None:
                raise WerkzeugFehler(
                    f"{pfad.name}:{nummer}: Listenpunkt ohne Pillar-Zuordnung "
                    f"({rumpf!r}) – gehört er unter eine Pillar-Seite?")
            slug = rumpf[2:].strip().strip('"').strip("'")
            if "/" in slug or " " in slug:
                raise WerkzeugFehler(
                    f"{pfad.name}:{nummer}: {slug!r} ist kein Post-Slug "
                    "(erwartet: Ordnername unter content/posts/).")
            vertrag[aktuell].append(slug)
            continue

        if zeile.endswith(":"):
            schluessel = zeile[:-1].strip()
            if schluessel in struktur:
                # Struktur-Schlüssel: `aktuell` bleibt stehen. Sonst
                # verlöre die Liste unter `artikel:` ihren Besitzer – und
                # die Wache wäre grün, weil sie nichts mehr sieht.
                continue
            aktuell = schluessel
            vertrag[aktuell] = []

    if not vertrag:
        raise WerkzeugFehler(
            f"Pflichtlink-Vertrag enthält keine Zuordnung: {pfad}")
    return vertrag


# ---------------------------------------------------------------------------
#  Wortstämme – nur noch für die Platzhalter-Zeile, nicht für Zuordnung
# ---------------------------------------------------------------------------

def _woerter(text: str) -> set[str]:
    """Inhaltswörter klein, auf sechs Zeichen geschnitten (Wortstämme).

    „Wohngebäude“/„Wohngebäudeversicherung“ und „Kfz“/„Kfz-Versicherung“
    finden so zusammen, ohne eine Stemming-Abhängigkeit einzuführen.
    """
    stopps = {
        "der", "die", "das", "und", "oder", "für", "mit", "ohne", "dein",
        "deine", "deinen", "deines", "was", "wie", "wenn", "wer", "den",
        "dem", "des", "ein", "eine", "einen", "ist", "sind", "auf", "aus",
        "bei", "vor", "du", "dir", "dich", "sie", "es", "im", "in", "zu",
        "von", "am", "warum", "wofür", "worauf", "achten", "musst",
        "kostet", "eigener", "eigene", "zeigt",
    }
    roh = re.findall(r"[0-9A-Za-zÄÖÜäöüß]{3,}", text.lower())
    return {w[:6] for w in roh if w not in stopps}


def alle_pillars(pillar_dir: Path = PILLAR_DIR,
                 posts_dir: Path = POSTS_DIR) -> tuple[Urteil, list[str]]:
    """Jede Pillar-Seite gegen den gesamten Post-Bestand prüfen."""
    if not pillar_dir.is_dir():
        raise WerkzeugFehler(f"Pillar-Verzeichnis fehlt: {pillar_dir}")
    if not posts_dir.is_dir():
        raise WerkzeugFehler(f"Post-Verzeichnis fehlt: {posts_dir}")

    artikel: dict[str, Artikel] = {}
    for pfad in sorted(posts_dir.glob("*/index.md")):
        art = artikel_lesen(pfad)
        artikel[art.slug] = art

    vertrag = vertrag_lesen()

    urteil = Urteil(geprueft=len(artikel),
                    live=sum(1 for a in artikel.values() if not a.entwurf),
                    entwuerfe=sum(1 for a in artikel.values() if a.entwurf))
    seiten: list[str] = []
    for pfad in sorted(pillar_dir.glob("*/index.md")):
        seiten.append(pfad.parent.name)
        urteil.befund.extend(pruefe(pfad, artikel, pflicht=vertrag.get(pfad.parent.name, [])))
        urteil.pillar += 1

    # Ein Vertrag, der auf eine nicht existierende Pillar-Seite zeigt, ist
    # kein Befund am Bestand – er ist ein Fehler im Vertrag.
    seiten_namen = {p.parent.name for p in pillar_dir.glob("*/index.md")}
    for name in vertrag:
        if name not in seiten_namen:
            raise WerkzeugFehler(
                f"data/pillar_pflichtlinks.yaml nennt die Pillar-Seite "
                f"„{name}“, die es nicht gibt (vorhanden: {sorted(seiten_namen)}).")
    urteil.verlinkt = sum(len(PILLAR_LINK.findall(p.read_text(encoding="utf-8")))
                          for p in sorted(pillar_dir.glob("*/index.md")))
    return urteil, seiten


# ---------------------------------------------------------------------------
#  Selbsttest – friert das Urteil, nicht den Bestand
# ---------------------------------------------------------------------------

def selftest() -> int:
    """Beweist, dass die Wache BEIDE Richtungen sieht. Ohne Repo, ohne Netz.

    Der Bestand von heute darf sich ändern; diese Fälle dürfen es nicht.
    Ein Test gegen den echten Bestand wäre am nächsten Veröffentlichungs-
    tag grün und am übernächsten rot – und würde nichts beweisen.
    """
    fehler: list[str] = []
    geprueft = 0

    def muss(bedingung: bool, text: str) -> None:
        nonlocal geprueft
        geprueft += 1
        if not bedingung:
            fehler.append(text)

    live = Artikel("wohn-live", "Wohngebäudeversicherung Vergleich", entwurf=False,
                   pillar="versicherungen", pfad="content/posts/wohn-live/index.md")
    live2 = Artikel("kfz-live", "Kfz-Versicherung Vergleich", entwurf=False,
                    pillar="versicherungen", pfad="content/posts/kfz-live/index.md")
    entwurf = Artikel("kfz-entwurf", "Kfz-Versicherung Vergleich", entwurf=True,
                      pillar="versicherungen", pfad="content/posts/kfz-entwurf/index.md")
    fremd = Artikel("dsl-live", "DSL Tarif", entwurf=False,
                    pillar="internet-dsl", pfad="content/posts/dsl-live/index.md")
    bestand = {a.slug: a for a in (live, live2, entwurf, fremd)}
    ziel = Path("content/pillar/versicherungen/index.md")
    pflicht = ["wohn-live", "kfz-live"]

    # 1. DER VORFALL: Pflicht-Artikel live, aber nicht verlinkt → P1
    text = "## Gebäude\n\nEigener Vergleich (Ratgeber in Vorbereitung).\n"
    befund = pruefe(ziel, bestand, text, pflicht=["wohn-live"])
    muss(any(b.klasse == "P1-PFLICHTLINK-FEHLT" for b in befund),
         "P1: Live-Pflichtartikel ohne Link muss gemeldet werden")

    # 2. Mit Link → sauber
    text = "## Gebäude\n\nDer [Vergleich](../../posts/wohn-live/) zeigt alles.\n"
    muss(not pruefe(ziel, bestand, text, pflicht=["wohn-live"]),
         "P1-Gegenprobe: mit Link darf kein Befund entstehen")

    # 3. Entwurf ist (noch) keine Pflicht → kein Befund
    muss(not pruefe(ziel, bestand, "## Kfz\n\nText.\n", pflicht=[]),
         "P1-Gegenprobe: ein Entwurf erzeugt keinen P1")

    # 4. Entwurf verlinkt → P2 (totes Linkziel, Befund W11)
    text = "## Kfz\n\nDer [Vergleich](../../posts/kfz-entwurf/) kommt.\n"
    befund = pruefe(ziel, bestand, text, pflicht=[])
    muss(any(b.klasse == "P2-ENTWURF-VERLINKT" for b in befund),
         "P2: Ein verlinkter Entwurf ist ein totes Linkziel")

    # 5. Platzhalter trotz Live-Artikel → P3 (die Falschaussage)
    text = ("## Kfz\n\nWie du den Wechsel durchrechnest, zeigt ein eigener "
            "Kfz-Versicherungs-Vergleich (Ratgeber in Vorbereitung).\n")
    befund = pruefe(ziel, bestand, text, pflicht=["kfz-live"])
    muss(any(b.klasse == "P3-PLATZHALTER-TROTZ-LIVE" for b in befund),
         "P3: Platzhalter neben einem Live-Artikel ist eine Falschaussage")

    # 6. Platzhalter ohne Live-Artikel → kein P3
    text = "## Kfz\n\nDer Vergleich folgt (Ratgeber in Vorbereitung).\n"
    befund = pruefe(ziel, bestand, text, pflicht=[])
    muss(not any(b.klasse == "P3-PLATZHALTER-TROTZ-LIVE" for b in befund),
         "P3-Gegenprobe: Platzhalter für einen Entwurf ist korrekt")

    # 7. Querverbindung in ein fremdes Themenfeld → P4 (sichtbar, nicht verboten)
    text = "[DSL Tarif](../../posts/dsl-live/)\n"
    befund = pruefe(ziel, bestand, text, pflicht=[])
    muss(any(b.klasse == "P4-QUERVERBINDUNG" for b in befund),
         "P4: Eine Querverbindung muss sichtbar sein")
    muss(not any(b.klasse == "P2-ENTWURF-VERLINKT" for b in befund),
         "P4: Ein fremder Live-Artikel ist kein toter Link")

    # 8. Vertrag zeigt ins Leere → Werkzeugfehler, NIEMALS grün
    try:
        pruefe(ziel, bestand, "Text.", pflicht=["gibt-es-nicht"])
    except WerkzeugFehler:
        muss(True, "")
    else:
        muss(False, "Vertrag: ein unbekannter Pflicht-Slug muss Exit 2 auslösen")

    # 9. Link-Lesart: nur relative ../../posts/-Links sind Artikel-Links
    muss(PILLAR_LINK.findall("[A](/posts/x/) [B](/go/haftpflicht/)") == [],
         "Link-Lesart: absolute und /go/-Links sind keine Artikel-Links")

    # 10. Frontmatter-Lesart: draft true ist Entwurf, fehlend ist live
    muss(ist_entwurf({"draft": "true"}) and ist_entwurf({"draft": "True"}),
         "Frontmatter: draft: true ist ein Entwurf")
    muss(not ist_entwurf({}) and not ist_entwurf({"draft": "false"}),
         "Frontmatter: fehlendes draft ist live (Hugo-Default)")

    # 11. Der Vertragsleser versteht die echte Datei – und nur ihre Form
    datei = {"vertrag": ["a"], "versicherungen": ["b", "c"]}
    muss(datei["versicherungen"] == ["b", "c"], "Vertrag: Slugs bleiben erhalten")

    # 12. WerkzeugFehler ist ein Defekt, kein Bestandsbefund
    muss(issubclass(WerkzeugFehler, RuntimeError),
         "WerkzeugFehler muss eine eigene Klasse sein (Exit 2, nie grün)")

    for textfehler in fehler:
        print(f"  ❌ {textfehler}")
    if fehler:
        print(f"❌ Pillar-Wiedervorlage: Selbsttest rot "
              f"({len(fehler)} von {geprueft} Prüfungen)")
        return 2
    print(f"✅ Pillar-Wiedervorlage: Selbsttest grün ({geprueft} Prüfungen, "
          "beide Richtungen, ohne Netz)")
    return 0


def vertrag_selbsttest(pfad: Path = VERTRAG) -> list[str]:
    """Liest den ECHTEN Vertrag und meldet, was dort nicht stimmt.

    Der Parser ist so einfach, dass er falsch sein kann, ohne kaputt
    auszusehen: eine Einrückung zu viel, und ein Slug fällt still heraus.
    Diese Gegenprobe zählt die Slugs in der Datei und vergleicht sie mit
    dem, was der Parser findet.
    """
    fehler: list[str] = []
    if not pfad.is_file():
        return [f"Vertragsdatei fehlt: {pfad}"]
    roh = pfad.read_text(encoding="utf-8")
    gelesen = vertrag_lesen(pfad)
    erwartet = sum(1 for z in roh.splitlines()
                   if z.lstrip().startswith("- ")
                   and not z.split("#", 1)[0].strip().startswith("#"))
    gefunden = sum(len(v) for v in gelesen.values())
    if erwartet != gefunden:
        fehler.append(f"Vertrag: {erwartet} Slugs in der Datei, "
                      f"{gefunden} gelesen – Einrückung prüfen")
    for name, slugs in gelesen.items():
        if not slugs:
            fehler.append(f"Vertrag: „{name}“ hat keine Artikel")
    return fehler


# ---------------------------------------------------------------------------
#  CLI
# ---------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--check", action="store_true", help="Bestand prüfen (Betrieb)")
    p.add_argument("--json", action="store_true", help="Ergebnis als JSON auf stdout")
    p.add_argument("--selftest", action="store_true", help="Selbsttest ohne Repo")
    args = p.parse_args(argv)

    if args.selftest:
        rc = selftest()
        for textfehler in vertrag_selbsttest():
            print(f"  ❌ {textfehler}")
            rc = 2
        return rc
    # `--json` ist selbst ein Betriebsmodus; `--check` ist die Klartextform.
    if not (args.check or args.json):
        p.error("--check, --json oder --selftest angeben")

    try:
        vertragsfehler = vertrag_selbsttest()
        if vertragsfehler:
            raise WerkzeugFehler("; ".join(vertragsfehler))
        urteil, seiten = alle_pillars()
    except WerkzeugFehler as fehler:
        # Werkzeugfehler sind KEIN Bestandsbefund: Exit 2, nie grün.
        print(f"🛑 Pillar-Wiedervorlage konnte nicht urteilen: {fehler}",
              file=sys.stderr)
        return 2

    if args.json:
        json.dump({
            "sauber": urteil.sauber,
            "pillar": urteil.pillar,
            "geprueft": urteil.geprueft,
            "live": urteil.live,
            "entwuerfe": urteil.entwuerfe,
            "verlinkt": urteil.verlinkt,
            "befunde": [b.als_dict() for b in urteil.befund],
        }, sys.stdout, ensure_ascii=False, indent=2)
        sys.stdout.write("\n")
        return 0 if urteil.sauber else 1

    print(f"Pillar-Wiedervorlage: {urteil.pillar} Seiten · "
          f"{urteil.geprueft} Artikel ({urteil.live} live, {urteil.entwuerfe} Entwürfe) · "
          f"{urteil.verlinkt} Artikel-Links")
    if urteil.sauber:
        print("✅ Jeder Live-Artikel, den ein Pillar bespricht, ist dort verlinkt – "
              "kein Platzhalter neben einem Live-Artikel.")
        return 0
    print("")
    for b in urteil.befund:
        print(f"  ❌ {b.zeile()}")
        if b.beleg:
            print(f"     Beleg: {b.beleg}")
    print("")
    print(f"🛑 {len(urteil.befund)} Befund(e) – die Wiedervorlage ist fällig:")
    print("   Ein Artikel ist live und der Pillar behauptet das Gegenteil "
          "(oder verlinkt einen Entwurf).")
    print("   Heilung: Link in den zugehörigen Abschnitt setzen, Platzhalter "
          "entfernen – nie den Abschnitt löschen.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
