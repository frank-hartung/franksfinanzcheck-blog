#!/usr/bin/env python3
"""KI-Provenienz-Gate – die maschinenlesbare Kennzeichnung bleibt dran (#1028).

Frist `ki-vo-kennzeichnung-bestand` · fällig 02.12.2026 · Issue #1028.

BEFUND, DER DIESEN STAND NÖTIG MACHT (Nachmessung 07.11.2026)
--------------------------------------------------------------
Die Kennzeichnung lag seit dem 05.11.2026 auf vier Kanälen, und das Gate war
grün. Grün war es, weil es nicht überall hinsah. Gemessen am gebauten Bestand
(406 Seiten, Hugo 0.168.0):

  · DECKUNG  Das Gate zählte `content/posts` – 78 Seiten. Der Bau enthält
    109 reguläre Seiten ohne Entwurf. Sechs Ratgeber-Seiten unter
    `content/pillar/` deklarierten `ai-generated-scope: audio`, ohne dass
    eine Regel hinsah.
  · KANALTREUE  Regel M4 verglich das Meta-Signal gegen EINEN Anker:
    `data-ff-ki-label`, den Text-Hinweis. 84 Seiten spielten eine
    synthetische Stimme aus; 18 davon trugen überhaupt keinen sichtbaren
    Hinweis, und die übrigen 66 einen, der vom Text handelt – nicht von der
    Stimme. Maschinenlesbar deklariert, menschenlesbar unsichtbar.
  · VERBREITUNG  Der RSS-Feed – Quelle des Pinterest-Auto-Publish – verteilte
    50 Artikel, davon 45 mit `ai_generated: true`, ohne eine einzige
    Herkunftsangabe. Was die Seite kennzeichnet, ging auf dem
    Verbreitungsweg verloren.
  · ROBUSTHEIT  Ohne PyYAML starb das Gate mit `ModuleNotFoundError` und
    Exit 1. Exit 1 heißt im Deploy „Inhalts-Fund". Ein Abhängigkeitsausfall
    ist ein Werkzeugfehler und gehört über den einen Meldeweg
    (scripts/werkzeugbefund.py, C38), nicht als Traceback in den Schritt.
  · BILD  scripts/image_optimizer.py kannte `cover.ai_generated` nicht und
    hätte zu einem deklarierten KI-Original unmarkierte AVIF/WebP/JPEG-
    Geschwister erzeugt – öffentlich erreichbar, Markierung weg.

REGELN
------
M1  Auslieferung  Jede gebaute Seite trägt genau die Signale, die ihr
    Frontmatter und ihre Ausspielung hergeben: `ai-generated`,
    `ai-generated-scope`, `rel="describedby"`, Bildattribute, `creditText`.
    Geprüft wird der GEBAUTE Baum, alle Abschnitte – nicht nur posts/.
M2  Vertrag       Die Kanäle bleiben eingebunden (Vorlagen, CSS, Engine,
    Feed, Bild-Optimizer).
M3  Bilddatei     Jedes deklarierte KI-Cover trägt IPTC `DigitalSourceType`
    in der Datei (scripts/ki_bild_markierung.py).
M4  Kanaltreue    Jede deklarierte Modalität hat einen sichtbaren Anker –
    text → `data-ff-ki-label`, image → `data-ff-ki-image-label`,
    audio → `data-ff-ki-voice-label`. Und umgekehrt: kein sichtbarer Anker
    ohne Deklaration. Leser und Maschine sehen dieselbe Wahrheit.
M5  Feed          Jedes Item trägt dieselbe Angabe wie seine Seite
    (`ffki:`-Namensraum + IANA-Relation `describedby`), der Kanal selbst die
    Relation auf den Hinweis.
M6  Bild-Ableitung  Ein deklariertes KI-Original hat keine unmarkierten
    Ableitungen, und der Optimizer kennt die Ausnahme.
M7  Spiegelung    layouts/rss.xml und layouts/_default/rss.xml sind bytgleich
    (Hugo zieht je Version die eine oder andere – driftet eine, ist die
    Kennzeichnung versionsabhängig).

SELBSTHEILUNG
-------------
`--heilen` repariert, was deterministisch reparierbar ist (Impressum-Anker,
RSS-Spiegelung, unmarkierte Bild-Ableitungen), schreibt jede Zeile in das
append-only-Ledger `data/ki_provenienz_history.jsonl` und meldet alles
Übrige als Eskalation. Eine Heilung, die eine Entscheidung erfindet, ist
schlimmer als keine: Anbieter-Auskünfte, Bildherkunft und die Belege der
`menschlich`-Einträge bleiben Menschen vorbehalten.

`--wache` heilt, misst nach, führt das Alter der ungeklärten Register-
Einträge in `data/ki_provenienz_state.json` und sagt, was offen ist.

Aufruf
------
    python3 scripts/ki_provenienz_gate.py                 # Befund
    python3 scripts/ki_provenienz_gate.py --gate          # Exit 1 bei Fund
    python3 scripts/ki_provenienz_gate.py --heilen        # reparieren + Beleg
    python3 scripts/ki_provenienz_gate.py --wache         # heilen, nachmessen, Altern
    python3 scripts/ki_provenienz_gate.py --selftest
    python3 scripts/ki_provenienz_gate.py --json

Exit: 0 = sauber · 1 = Fund (--gate/--wache) · 2 = Werkzeugfehler
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# EIN Modulobjekt, egal wer ruft. Läuft diese Datei als Skript, liegt
# `scripts/` auf dem Pfad und der Kern heißt `ki_provenienz`; unter
# `python3 -m unittest scripts.tests.…` heißt er `scripts.ki_provenienz`.
# Zwei Namen für dieselbe Datei sind zwei Modulobjekte mit je eigenem
# Vokabular und je eigenem Cache – ein Test, der das eine patcht, prüft
# dann eine Kopie des anderen (gemessen am 07.11.2026: `kp is gate.kp`
# war False). Deshalb wird der Kern über das Paket geladen, das in beiden
# Einstiegswegen dasselbe Objekt liefert.
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
# Geschwister-Module (ki_bild_markierung, werkzeugbefund) werden top-level
# importiert und brauchen `scripts/` auf dem Pfad – unabhängig davon, wie
# DIESER Kern geladen wurde. Fehlt die Zeile, wird M3 blind und sieht aus wie
# ein Inhaltsbefund (gefunden am 07.11.2026 durch die Unit-Tests).
if str(ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(ROOT / "scripts"))
try:
    from scripts import ki_provenienz as kp  # noqa: E402
except ImportError:  # pragma: no cover – ohne Namespace-Paket direkt laden
    import ki_provenienz as kp  # noqa: E402  (ein Wahrheitsort für Vokabular
    #                                           und Heilung)

BAU = kp.BAU
ARTIKEL_MUSTER = '"@type":"Article"'
CREDIT_TEXT_MUSTER = re.compile(r'"creditText"\s*:\s*"([^"]{0,400})"')
FRIST_ID = "ki-vo-kennzeichnung-bestand"


# --------------------------------------------------------------------------
#  Meldeweg
# --------------------------------------------------------------------------

def _melden(ebene: str, text: str, *, datei: str | None = None, titel: str | None = None) -> None:
    """Ein Befund, ein Kommando – über den einen Meldeweg des Hauses.

    Vorher druckte dieses Gate `::error title=…::` selbst. Damit fehlten der
    Fluchtschutz gegen CR/LF/`::` in Fundtexten (die Slugs stammen aus dem
    Baum, also aus PR-Inhalt) und die Teststille: Ein Unit-Test, der `main()`
    aufruft, färbte den eigenen Lauf rot (WF-E813/#815).
    """
    try:
        import github_kommando  # noqa: PLC0415
    except ImportError:  # pragma: no cover – ohne Melder trotzdem lesbar
        print(f"[{ebene}] {titel + ': ' if titel else ''}{text}")
        return
    github_kommando.annotation(ebene, text, datei=datei, titel=titel)


def _datum_heute() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _frist(root: Path = ROOT) -> str | None:
    """Fälligkeitsdatum der Frist aus data/recht-fristen.yaml.

    Zeilenweise gelesen, ohne PyYAML: Die Frist muss auch dann sichtbar
    bleiben, wenn das YAML-Werkzeug fehlt – sonst eskaliert die Wache im
    falschen Moment nicht.
    """
    pfad = root / "data" / "recht-fristen.yaml"
    if not pfad.is_file():
        return None
    im_block = False
    for zeile in pfad.read_text(encoding="utf-8", errors="ignore").splitlines():
        if re.match(r"^\s*-\s+id:\s*", zeile):
            im_block = FRIST_ID in zeile
            continue
        if im_block:
            m = re.match(r"^\s+faellig_am:\s*[\"']?(\d{4}-\d{2}-\d{2})", zeile)
            if m:
                return m.group(1)
    return None


# --------------------------------------------------------------------------
#  Regeln M1–M7
# --------------------------------------------------------------------------

def _fund(regel: str, text: str, datei: str = "") -> dict:
    return {"regel": regel, "text": text, "datei": datei}


def regel_m1_m4(bau: Path, root: Path):
    """Auslieferung und Kanaltreue – über den GANZEN gebauten Baum.

    Beide Regeln teilen denselben Durchlauf, weil sie dieselbe Datei lesen:
    M1 vergleicht Frontmatter/Ausspielung mit den Maschinensignalen, M4
    dieselben Signale mit den sichtbaren Ankern. Getrennte Durchläufe wären
    zweimal dieselbe I/O und zwei Gelegenheiten, unterschiedlich zu zählen.
    """
    funde: list[dict] = []
    if not bau.is_dir():
        return [_fund("M1", f"kein Bauprodukt unter {bau}/ – Auslieferung nicht "
                            "geprüft (nach `hugo` erneut laufen lassen)")], 0, 0

    geprueft = 0
    live = 0
    for seite in kp.seiten(root):
        if seite.entwurf:
            continue
        live += 1
        datei = bau / seite.basis / "index.html" if seite.basis else bau / "index.html"
        if not datei.is_file():
            funde.append(_fund("M1", f"{seite.basis or '/'}: kein Bauprodukt unter "
                                     f"{datei.relative_to(bau.parent)} – Auslieferung "
                                     "nicht prüfbar", str(datei)))
            continue
        try:
            html = datei.read_text(encoding="utf-8", errors="ignore")
        except OSError as exc:
            funde.append(_fund("M1", f"{seite.basis}: Bauprodukt nicht lesbar: {exc}",
                               str(datei)))
            continue
        geprueft += 1
        sig = kp.signale(html)
        erwartet = kp.erwartet(seite, sig)
        ort = str(datei)
        kennung = seite.basis or "/"

        # --- M1: Primärsignal -------------------------------------------
        if seite.ki_text and not sig["meta"]:
            funde.append(_fund("M1", f"{kennung}: ai_generated: true, aber das gebaute "
                                     'HTML trägt kein <meta name="ai-generated" '
                                     'content="true">', ort))
        elif not seite.ki_text and sig["meta"]:
            funde.append(_fund("M1", f"{kennung}: ohne ai_generated: true wird eine "
                                     "KI-Erzeugung ausgewiesen – Signal entfernen oder "
                                     "Herkunft klären", ort))

        # --- M1: Modalitäten --------------------------------------------
        if set(sig["bereiche"]) != set(erwartet):
            funde.append(_fund("M1", f"{kennung}: ai-generated-scope lautet "
                                     f"„{','.join(sig['bereiche']) or '–'}“, erwartet "
                                     f"„{','.join(erwartet) or '–'}“", ort))

        # --- M1: IANA-Relation ------------------------------------------
        if erwartet and not sig["describedby"]:
            funde.append(_fund("M1", f"{kennung}: deklarierte Modalitäten ohne "
                                     'rel="describedby" auf den Hinweis', ort))
        elif not erwartet and sig["describedby"]:
            funde.append(_fund("M1", f"{kennung}: rel=\"describedby\" auf den KI-Hinweis "
                                     "ohne deklarierte Modalität", ort))

        # --- M1: Bildkanal im DOM ---------------------------------------
        if seite.ki_bild:
            if "data-ai-generated" not in html:
                funde.append(_fund("M1", f"{kennung}: cover.ai_generated: true, aber das "
                                         "gebaute <img> trägt kein data-ai-generated", ort))
            if seite.quellentyp and "data-digital-source-type" not in html:
                funde.append(_fund("M1", f"{kennung}: digital_source_type belegt, aber "
                                         "nicht als data-digital-source-type ausgeliefert",
                                   ort))

        # --- M1: schema.org creditText ----------------------------------
        if ARTIKEL_MUSTER in html:
            m = CREDIT_TEXT_MUSTER.search(html)
            credit = m.group(1) if m else ""
            if "text" in erwartet and "Mit KI erstellt" not in credit:
                funde.append(_fund("M1", f"{kennung}: Article-Schema ohne creditText zur "
                                         "Text-Herkunft", ort))
            if "image" in erwartet and "Cover mit KI erstellt" not in credit:
                funde.append(_fund("M1", f"{kennung}: Article-Schema ohne creditText zur "
                                         "Bild-Herkunft", ort))
            if "audio" in erwartet and "Tonspur maschinell erzeugt" not in credit:
                funde.append(_fund("M1", f"{kennung}: Article-Schema ohne creditText zur "
                                         "Tonspur", ort))

        # --- M4: Kanaltreue je Modalität --------------------------------
        for modalitaet in erwartet:
            if not sig["anker"][modalitaet]:
                funde.append(_fund("M4", f"{kennung}: Modalität „{modalitaet}“ ist "
                                         "maschinenlesbar deklariert, hat aber keinen "
                                         f"sichtbaren Anker ({kp.ANKER[modalitaet]})", ort))
        for modalitaet, anker in kp.ANKER.items():
            if sig["anker"][modalitaet] and modalitaet not in erwartet:
                funde.append(_fund("M4", f"{kennung}: sichtbarer Anker {anker} ohne "
                                         f"deklarierte Modalität „{modalitaet}“", ort))
    return funde, geprueft, live


def regel_m2(root: Path):
    """Vertrag der Vorlagen: die Kanäle müssen eingebunden bleiben."""
    funde = []
    for v in kp.kanal_vertrag(root):
        if v.regel != "M2":
            continue
        datei = root / v.datei
        if not datei.is_file():
            funde.append(_fund("M2", f"{v.datei} fehlt", v.datei))
        elif v.nadel not in datei.read_text(encoding="utf-8", errors="ignore"):
            funde.append(_fund("M2", f"{v.datei}: {v.meldung}", v.datei))
    return funde


def regel_m3(root: Path, *, werkzeug_blind: bool = False):
    """Maschinenlesbare Markierung IN den deklarierten KI-Bilddateien."""
    try:
        import ki_bild_markierung  # noqa: PLC0415
    except ImportError as exc:
        if werkzeug_blind:
            # W0 trägt die Meldung bereits – und zwar mit der richtigen
            # Bedeutung (Exit 2, Werkzeugfehler). Ein zweiter Fund unter M3
            # hieße „Inhaltsbefund" und würde die Ursache verwischen (C33).
            return [], True
        return [_fund("M3", f"ki_bild_markierung.py nicht ladbar – IPTC-Feld in der "
                            f"Bilddatei nicht prüfbar: {exc}")], True
    try:
        _, fehler = ki_bild_markierung.pruefen(root)
    except (OSError, ValueError) as exc:
        return [_fund("M3", f"Bildbestand nicht lesbar: {exc}")], True
    except Exception as exc:  # pragma: no cover – blind melden, nie still grün
        return [_fund("M3", f"Bildbestand nicht prüfbar ({type(exc).__name__}: {exc})")], True
    return [_fund("M3", f) for f in fehler], False


def regel_m5(bau: Path, root: Path):
    """Feed: dieselbe Angabe wie auf der Seite – kein Verlust beim Verteilen."""
    funde = []
    pfad = Path(bau) / "index.xml"
    if not pfad.is_file():
        if bau.is_dir():
            funde.append(_fund("M5", f"kein Feed unter {pfad} – Verbreitungsweg nicht "
                                     "prüfbar"))
        return funde, 0, []
    try:
        items = kp.feed_items(pfad)
    except kp.WerkzeugFehler as exc:
        return [_fund("M5", str(exc))], 0, []

    if items and not kp.feed_kanal_angabe(pfad):
        funde.append(_fund("M5", "der Feed trägt auf Kanal-Ebene kein "
                                 'atom:link rel="describedby" auf den Hinweis'))

    seiten_by_slug = {s.slug: s for s in kp.seiten(root) if not s.entwurf}
    geprueft = 0
    ohne_seite: list[str] = []
    for item in items:
        seite = seiten_by_slug.get(item["slug"])
        if seite is None:
            # Kein stilles Überspringen: Ein Feed-Item, das keine Seite im
            # Bestand hat, ist eine Lücke in der Messung (M5 wäre für dieses
            # Item blind). Es wird GEZÄHLT und benannt, nicht verschluckt –
            # Befund vom 08.11.2026: In CI waren 49 von 50 Items gemappt, und
            # niemand konnte sehen, welches fehlte.
            # Mit Beleg: Slug UND die Quelle, aus der er stammt. Ein Befund,
            # der nur den Slug nennt, ist bei abweichender URL nicht zu
            # bestätigen (Befund 08.11.2026: 49/50, Item unbekannt).
            ohne_seite.append(f"{item['slug']} ← {item['guid'] or 'ohne guid'}")
            continue
        geprueft += 1
        gebaut = bau / seite.basis / "index.html" if seite.basis else bau / "index.html"
        erwartet: tuple[str, ...] = ()
        if gebaut.is_file():
            html = gebaut.read_text(encoding="utf-8", errors="ignore")
            erwartet = kp.erwartet(seite, kp.signale(html))
        if not erwartet:
            if item["scope"] or item["describedby"]:
                funde.append(_fund("M5", f"{item['slug']}: Feed-Item trägt eine "
                                         "Herkunftsangabe, die Seite deklariert keine"))
            continue
        if not item["describedby"]:
            funde.append(_fund("M5", f"{item['slug']}: Feed-Item ohne "
                                     'atom:link rel="describedby"'))
        if set(filter(None, item["scope"].split(","))) != set(erwartet):
            funde.append(_fund("M5", f"{item['slug']}: ffki:ai-generated-scope lautet "
                                     f"„{item['scope'] or '–'}“, die Seite deklariert "
                                     f"„{','.join(erwartet)}“"))
        if "text" in erwartet and not item["ai_generated"]:
            funde.append(_fund("M5", f"{item['slug']}: ai_generated: true, aber das "
                                     "Feed-Item trägt kein ffki:ai-generated"))
        if seite.quellentyp and not item["media_credit"]:
            funde.append(_fund("M5", f"{item['slug']}: IPTC-Erzeugungsart belegt, aber "
                                     "das Feed-Item trägt kein media:credit"))
    return funde, geprueft, ohne_seite


def regel_m6(root: Path):
    """Keine unmarkierte Kopie eines deklarierten KI-Originals."""
    funde = []
    for v in kp.kanal_vertrag(root):
        if v.regel != "M6":
            continue
        datei = root / v.datei
        if not datei.is_file():
            funde.append(_fund("M6", f"{v.datei} fehlt", v.datei))
        elif v.nadel not in datei.read_text(encoding="utf-8", errors="ignore"):
            # Die Nadel steht im Vertrag (ki_provenienz.kanal_vertrag) und wird
            # hier gelesen, nicht ein zweites Mal abgetippt: Zwei Abschriften
            # derselben Bedingung sind genau der Drift, den M2 verhindern soll.
            funde.append(_fund("M6", f"{v.datei}: {v.meldung}", v.datei))
    for seite, rel in kp.unmarkierte_ableitungen(root):
        funde.append(_fund("M6", f"{seite.slug}: static/{rel} ist eine öffentlich "
                                 "erreichbare Ableitung eines deklarierten KI-Originals "
                                 "und trägt dessen IPTC-Markierung nicht", f"static/{rel}"))
    return funde


def regel_m7(root: Path):
    """Beide RSS-Vorlagen bytgleich – sonst hängt die Kennzeichnung an Hugo."""
    abweichung = kp.rss_spiegel_abweichung(root)
    if not abweichung:
        return []
    if abweichung == "beide":
        return [_fund("M7", f"{kp.RSS_QUELLE} und {kp.RSS_SPIEGEL} unterscheiden sich "
                            "und tragen beide den Herkunfts-Kanal – welche Fassung gilt, "
                            "ist eine Entscheidung (kein Heilauftrag)", kp.RSS_SPIEGEL)]
    quelle, spiegel = ((kp.RSS_QUELLE, kp.RSS_SPIEGEL) if abweichung == "quelle"
                       else (kp.RSS_SPIEGEL, kp.RSS_QUELLE))
    return [_fund("M7", f"{spiegel} weicht von {quelle} ab – die Kennzeichnung im Feed "
                        "hängt damit an der Hugo-Version (`--heilen` gleicht an)",
                  spiegel)]


# --------------------------------------------------------------------------
#  Gesamtdurchlauf
# --------------------------------------------------------------------------

def main_exit_werkzeug(funde: list[dict]) -> int:
    """Exit-Code für einen Befundssatz: 2 bei ausgefallener Messung, sonst 1/0.

    Ein Werkzeugfehler ist KEIN Inhaltsbefund (C33/C38). Wer das verwechselt,
    jagt einen kaputten Messlauf wie einen roten Artikel.
    """
    if any(f["regel"] == "W0" for f in funde):
        return 2
    return 1 if funde else 0


def pruefen(root: Path = ROOT, bau: Path | None = None, *, nur_quelle: bool = False):
    """(funde, gepruefte_seiten, kennzahlen) – niemals ein Traceback.

    `nur_quelle` prüft ausschließlich, was keinen Build braucht (M2 Vertrag,
    M3 Bilddatei, M6 Ableitungen, M7 Spiegelung). Das ist der Modus für den
    Selbstheilungs-Schritt VOR dem Build im Deploy: Ein Heillauf, der mangels
    Bauprodukt „kein Bauprodukt" als Fund meldet, würde jeden Deploy stoppen –
    Vorbild ist `fixkosten_kompass_guard.py --source-only`.
    """
    bau = bau or (root / BAU if root == ROOT else root / BAU)
    funde: list[dict] = []
    kennzahlen: dict[str, object] = {}

    fehlende = kp.abhaengigkeiten(root)
    if fehlende:
        # Blind ist nicht grün: Ohne PyYAML/Pillow sind Bild-Register und
        # IPTC-Feld nicht messbar. Das ist ein Werkzeugfehler (Exit 2), kein
        # Inhalts-Fund – und gehört über den einen Meldeweg (C38).
        funde.append(_fund("W0", "Messwerkzeug fehlt: " + "; ".join(fehlende) +
                           " – Regeln M3/M6 sind blind. Installation: "
                           "pip install -r requirements-ci.txt"))
        kennzahlen["werkzeug_blind"] = fehlende

    geprueft = 0
    feed_items = 0
    live = sum(1 for s in kp.seiten(root) if not s.entwurf)
    if not nur_quelle:
        m14, geprueft, live = regel_m1_m4(bau, root)
        funde += m14
    funde += regel_m2(root)
    m3, m3_blind = regel_m3(root, werkzeug_blind=bool(fehlende))
    funde += m3
    feed_ohne_seite: list[str] = []
    if not nur_quelle:
        m5, feed_items, feed_ohne_seite = regel_m5(bau, root)
        funde += m5
    funde += regel_m6(root)
    funde += regel_m7(root)

    kennzahlen.update({
        "nur_quelle": nur_quelle,
        "seiten_live": live,
        "seiten_geprueft": geprueft,
        "feed_items_geprueft": feed_items,
        "feed_items_ohne_seite": feed_ohne_seite,
        "abschnitte": sorted({s.abschnitt for s in kp.seiten(root)}),
        "ki_originale": len(kp.ki_originale(root)),
        "ungeklaert": len(kp.ungeklaert(root)),
        "m3_blind": m3_blind,
    })
    return funde, geprueft, kennzahlen


# --------------------------------------------------------------------------
#  Selbstheilung und Wache
# --------------------------------------------------------------------------

def heilen(root: Path = ROOT, *, trocken: bool = False, bau: Path | None = None,
           nur_quelle: bool = False) -> dict:
    """Erst reparieren, dann nachmessen – und beides sagen."""
    ergebnis = kp.heilen(root, trocken=trocken)
    funde, geprueft, kennzahlen = pruefen(root, bau, nur_quelle=nur_quelle)
    ergebnis.update({"funde_nachher": funde, "geprueft": geprueft,
                     "kennzahlen": kennzahlen})
    return ergebnis


def wache(root: Path = ROOT, *, trocken: bool = False, bau: Path | None = None,
          nur_quelle: bool = False) -> dict:
    """Dauerlauf: heilen, nachmessen, Alter der offenen Punkte führen.

    Das Alter ist der Teil, der aus einer Warteschlange eine Wache macht:
    Ein ungeklärter Register-Eintrag, der 30 Tage vor der Frist noch offen
    ist, wird benannt – statt täglich grün durchzugehen.
    """
    ergebnis = heilen(root, trocken=trocken, bau=bau, nur_quelle=nur_quelle)
    heute = _datum_heute()
    state = kp.state_lesen(root)
    erstmals: dict[str, str] = state.get("ungeklaert_erstmals") or {}
    ungeklaert = kp.ungeklaert(root)
    for slug in ungeklaert:
        erstmals.setdefault(slug, heute)
    for slug in list(erstmals):
        if slug not in ungeklaert:
            erstmals.pop(slug)               # geklärt – Alter läuft nicht weiter

    # Ältester Eintrag = kleinestes Erst-Datum. Nicht „größtes Alter > 0":
    # Am ersten Tag ist jedes Alter 0, und dann bliebe der Eintrag namenlos –
    # die Eskalation könnte nichts benennen.
    aeltester = ""
    alter_tage = 0
    if erstmals:
        aeltester = min(erstmals, key=lambda s: erstmals[s])
        try:
            alter_tage = (date.fromisoformat(heute)
                          - date.fromisoformat(erstmals[aeltester])).days
        except ValueError:
            alter_tage = 0

    frist = _frist(root)
    tage_bis_frist = None
    if frist:
        try:
            tage_bis_frist = (date.fromisoformat(frist) - date.fromisoformat(heute)).days
        except ValueError:
            tage_bis_frist = None

    eskalation = list(ergebnis.get("eskalation") or [])
    if ungeklaert and tage_bis_frist is not None and tage_bis_frist <= 30:
        eskalation.append({
            "grund": "register",
            "datei": "data/ki_kennzeichnung.yaml",
            "text": f"{len(ungeklaert)} `menschlich`-Einträge sind {tage_bis_frist} Tage "
                    f"vor der Frist ({frist}) ungeklärt – ältester seit {alter_tage} "
                    f"Tagen ({aeltester}). Ob ein Mensch die redaktionelle "
                    "Verantwortung übernommen hat, weiß nur der Betreiber."})

    neu = {
        "frist": frist,
        "ungeklaert_erstmals": erstmals,
        "funde": len(ergebnis["funde_nachher"]),
    }
    # NUR Dauerzustand wird verglichen und geschrieben. Abgeleitete Zahlen
    # (Alter in Tagen, Tage bis zur Frist) ändern sich täglich, ohne dass sich
    # am Bestand etwas geändert hätte – stünden sie im Vergleich, würde die
    # Wache jeden Tag committen und damit genau die Betriebsblindheit
    # trainieren, gegen die dieses Gate existiert (Lehre aus der Befundakte,
    # 06.11.2026: „sonst committete der Bot die Uhr statt des Befunds").
    # Sie werden zur Laufzeit gerechnet und nur berichtet, nie gespeichert.
    alt = {k: state.get(k) for k in neu}
    geaendert = alt != neu
    state.update(neu)
    state["zuletzt_geaendert"] = heute
    state["revision"] = ergebnis.get("revision", "")
    if not trocken and geaendert:
        kp.state_schreiben(root, state)
    if not trocken and ergebnis["eingriffe"]:
        # Belegzeilen nur für echte Eingriffe – ein Lauf ohne Eingriff hat
        # nichts zu belegen und soll das Ledger nicht blähen.
        kp.ledger(root, {"schritt": "wache", "revision": state["revision"],
                         "eingriffe": len(ergebnis["eingriffe"]),
                         "eskalationen": len(eskalation),
                         "funde": len(ergebnis["funde_nachher"]),
                         "ungeklaert": len(ungeklaert)})
    ergebnis["eskalation"] = eskalation
    ergebnis["state"] = state
    ergebnis["state_geaendert"] = geaendert
    #: Berichtslage – zur Laufzeit gerechnet, nie gespeichert.
    ergebnis["lage"] = {
        "frist": frist,
        "tage_bis_frist": tage_bis_frist,
        "ungeklaert": len(ungeklaert),
        "aeltester_eintrag": aeltester,
        "aeltester_alter_tage": alter_tage,
        "zuletzt_geaendert": heute,
        "revision": state["revision"],
    }
    return ergebnis


# --------------------------------------------------------------------------
#  Ausgabe
# --------------------------------------------------------------------------

def bericht(funde, kennzahlen, *, json_format: bool = False) -> str:
    if json_format:
        return json.dumps({"kennzahlen": kennzahlen, "funde": funde},
                          ensure_ascii=False, indent=2, default=str)
    if kennzahlen.get("nur_quelle"):
        zeilen = [f"KI-Provenienz (Quelle, ohne Build): "
                  f"{len(kennzahlen.get('abschnitte', []))} Abschnitte, "
                  f"{kennzahlen.get('ki_originale', 0)} deklarierte KI-Cover, "
                  f"{len(funde)} Fund(e)."]
    else:
        zeilen = [
            f"KI-Provenienz: {kennzahlen.get('seiten_geprueft', 0)} von "
            f"{kennzahlen.get('seiten_live', 0)} gebauten Seiten geprüft "
            f"({len(kennzahlen.get('abschnitte', []))} Abschnitte), "
            f"{kennzahlen.get('feed_items_geprueft', 0)} Feed-Items, "
            f"{len(funde)} Fund(e).",
        ]
    for f in funde:
        _melden("error", f["text"], datei=f.get("datei") or None,
                titel=f"KI-Provenienz {f['regel']}")
    if not funde and kennzahlen.get("nur_quelle"):
        # Nicht „alle Kanäle" behaupten, wenn der Build gar nicht geprüft wurde.
        zeilen.append("✅ Quellen sauber: Vorlagenvertrag, Impressum-Anker, "
                      "RSS-Spiegelung und Bild-Ableitungen stimmen. "
                      "Die ausgelieferten Seiten prüft M1/M4/M5 nach dem Build.")
    elif not funde:
        zeilen.append("✅ Maschinenlesbare Kennzeichnung liegt auf allen Kanälen: "
                      "Meta + scope + describedby im Kopf, creditText im Schema, "
                      "Bildattribut und IPTC-Feld, Herkunftsangabe im Feed – und jede "
                      "Modalität hat einen sichtbaren Anker.")
    return "\n".join(zeilen)


def wachenbericht(ergebnis: dict) -> str:
    lage = ergebnis.get("lage") or {}
    zeilen = ["## KI-Provenienz – Wache (#1028)", ""]
    eingriffe = ergebnis.get("eingriffe") or []
    eskalation = ergebnis.get("eskalation") or []
    zeilen.append(f"- Selbstheilung: **{len(eingriffe)} Eingriff(e)**, "
                  f"{len(eskalation)} Eskalation(en)")
    for e in eingriffe:
        zeilen.append(f"  - geheilt `{e.get('datei')}`: {e.get('text')}")
    for e in eskalation:
        zeilen.append(f"  - ⚠️ braucht Menschen ({e.get('grund')}) `{e.get('datei')}`: "
                      f"{e.get('text')}")
    zeilen.append(f"- Funde nach der Heilung: **{len(ergebnis.get('funde_nachher') or [])}**")
    if lage:
        zeilen.append(f"- Frist: {lage.get('frist') or 'unbekannt'} "
                      f"({lage.get('tage_bis_frist')} Tage)")
        zeilen.append(f"- Ungeklärte `menschlich`-Einträge: {lage.get('ungeklaert')} "
                      f"(ältester {lage.get('aeltester_alter_tage')} Tage, "
                      f"{lage.get('aeltester_eintrag') or '–'})")
        zeilen.append(f"- Zustand geändert (Commit nötig): "
                      f"{'ja' if ergebnis.get('state_geaendert') else 'nein'}")
    kenn = ergebnis.get("kennzahlen") or {}
    zeilen.append(f"- Deckung: {kenn.get('seiten_geprueft')}/{kenn.get('seiten_live')} "
                  f"Seiten, {kenn.get('feed_items_geprueft')} Feed-Items, "
                  f"{kenn.get('ki_originale')} deklarierte KI-Cover")
    for f in ergebnis.get("funde_nachher") or []:
        zeilen.append(f"- 🛑 {f['regel']}: {f['text']}")
    return "\n".join(zeilen)


# --------------------------------------------------------------------------
#  Selbsttest
# --------------------------------------------------------------------------

def selbsttest() -> int:
    """Prüft jede Regel an einer künstlichen, aber echten Dateilage.

    Der Selbsttest baut bewusst Fehlstände ein und verlangt die passende
    Regel – sonst ist ein grünes Gate eine Behauptung, keine Messung.
    """
    import shutil
    import tempfile

    fehler: list[str] = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        inhalt = root / "content"
        for slug, ki in (("ki-artikel", True), ("mensch-artikel", False)):
            (inhalt / "posts" / slug).mkdir(parents=True)
            (inhalt / "posts" / slug / "index.md").write_text(
                f"---\ntitle: {slug}\nai_generated: {'true' if ki else 'false'}\n---\nText\n",
                encoding="utf-8")
        (inhalt / "posts" / "entwurf").mkdir(parents=True)
        (inhalt / "posts" / "entwurf" / "index.md").write_text(
            "---\ntitle: Entwurf\nai_generated: true\ndraft: true\n---\nText\n",
            encoding="utf-8")
        # Ratgeber-Seite außerhalb von posts/ – der Blindfleck bis 07.11.2026
        (inhalt / "pillar" / "thema").mkdir(parents=True)
        (inhalt / "pillar" / "thema" / "index.md").write_text(
            "---\ntitle: Thema\nai_generated: false\n---\nText\n", encoding="utf-8")

        for rel in ("layouts/_partials/head.html", "layouts/_partials/schema_article.html",
                    "layouts/_partials/cover.html", "layouts/_partials/ff_voice_toolbar.html",
                    "layouts/_partials/ki_provenienz.html",
                    "layouts/_partials/_funcs/ki_modalitaeten.html",
                    "assets/css/extended/ff-voice.css", "static/premium/ff-voice.js",
                    "layouts/rss.xml", "layouts/_default/rss.xml",
                    "content/impressum/index.md", "scripts/image_optimizer.py"):
            ziel = root / rel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, ziel)
        for script in ("ki_bild_markierung.py", "ki_cover_provenienz.py", "ki_provenienz.py",
                       "github_kommando.py"):
            shutil.copy(ROOT / "scripts" / script, root / "scripts" / script)

        # 1) ohne Bauprodukt: M1 meldet den Hinweis, sonst grün
        funde, _, _ = pruefen(root)
        regeln = {f["regel"] for f in funde}
        if regeln != {"M1"}:
            fehler.append(f"ohne Bauprodukt: {sorted(regeln)} statt nur M1 "
                          f"({[f['text'][:70] for f in funde]})")

        # 2) korrekter Stand: keine Funde, alle Abschnitte gedeckt
        bau = root / BAU
        for basis, meta, scope, label, ton, toolbar in (
                ("posts/ki-artikel", True, "text,audio", True, True, True),
                ("posts/mensch-artikel", False, "audio", False, True, True),
                ("pillar/thema", False, "audio", False, True, True)):
            datei = bau / basis / "index.html"
            datei.parent.mkdir(parents=True, exist_ok=True)
            kopf = '<meta name="ai-generated" content="true">' if meta else ""
            sig = ('<meta name="ai-generated-scope" content="' + scope + '">'
                   '<link rel="describedby" href="/impressum/#ki-hinweis">')
            sichtbar = '<span data-ff-ki-label>Mit KI erstellt</span>' if label else ""
            siegel = '<span data-ff-ki-voice-label>KI-Stimme</span>' if ton else ""
            leiste = '<div class="ff-voice-slot"></div>' if toolbar else ""
            datei.write_text(f"<html><head>{kopf}{sig}</head><body>{leiste}{sichtbar}"
                             f"{siegel}</body></html>", encoding="utf-8")
        # Das Impressum ist eine reguläre Seite ohne Lesehilfe und ohne
        # KI-Angabe – es muss gebaut sein, sonst meldet M1 zu Recht.
        (bau / "impressum").mkdir(parents=True, exist_ok=True)
        (bau / "impressum" / "index.html").write_text(
            "<html><head></head><body>Impressum</body></html>", encoding="utf-8")

        def feed(items: list[tuple[str, str, bool]], *, kanal: bool = True) -> None:
            """Feed-Fixture: (slug, scope, ai_generated) je Item."""
            kopf = ('<atom:link rel="describedby" '
                    'href="https://x/impressum/#ki-hinweis"/>' if kanal else "")
            körper = "".join(
                f"<item><guid>https://x/posts/{slug}/</guid>"
                '<atom:link rel="describedby" href="https://x/impressum/#ki-hinweis"/>'
                + ("<ffki:ai-generated>true</ffki:ai-generated>" if ki else "")
                + (f'<ffki:ai-generated-scope>{scope}</ffki:ai-generated-scope>'
                   if scope else "")
                + "</item>"
                for slug, scope, ki in items)
            (bau / "index.xml").write_text(
                '<?xml version="1.0"?><rss version="2.0" '
                'xmlns:atom="http://www.w3.org/2005/Atom" '
                f'xmlns:ffki="{kp.NAMESPACE}"><channel>{kopf}{körper}'
                "</channel></rss>", encoding="utf-8")

        feed([("ki-artikel", "text,audio", True), ("mensch-artikel", "audio", False)])
        funde, geprueft, kenn = pruefen(root)
        if funde:
            fehler.append(f"korrekter Stand meldet {[f['text'][:80] for f in funde]}")
        if geprueft != 4:
            fehler.append(f"{geprueft} Seiten geprüft statt 4 (Entwurf überspringen)")
        if len(kenn["abschnitte"]) < 2:
            fehler.append("nur ein Abschnitt gedeckt – pillar/ wäre wieder blind")
        if kenn["feed_items_geprueft"] != 2:
            fehler.append(f"{kenn['feed_items_geprueft']} Feed-Items geprüft statt 2")
        if kenn["feed_items_ohne_seite"]:
            fehler.append(f"Feed-Items ohne Seite: {kenn['feed_items_ohne_seite']}")

        # 3) Deckung: pillar-Seite mit falschem scope fällt auf
        datei = bau / "pillar" / "thema" / "index.html"
        datei.write_text('<html><head><meta name="ai-generated-scope" content="text">'
                         '</head><body><div class="ff-voice-slot"></div></body></html>',
                         encoding="utf-8")
        regeln = {f["regel"] for f in pruefen(root)[0]}
        if "M1" not in regeln:
            fehler.append(f"falscher scope auf pillar/: {sorted(regeln)} ohne M1")

        # 4) Kanaltreue: Tonspur deklariert, Siegel fehlt → M4
        datei.write_text('<html><head><meta name="ai-generated-scope" content="audio">'
                         '<link rel="describedby" href="/impressum/#ki-hinweis"></head>'
                         '<body><div class="ff-voice-slot"></div>'
                         '<span data-ff-ki-label>x</span></body></html>', encoding="utf-8")
        funde = pruefen(root)[0]
        if not any(f["regel"] == "M4" and "audio" in f["text"] for f in funde):
            fehler.append("M4 merkt eine deklarierte Tonspur ohne sichtbares Siegel nicht")
        if not any(f["regel"] == "M4" and "text" in f["text"] for f in funde):
            fehler.append("M4 merkt einen sichtbaren Text-Anker ohne Deklaration nicht")

        # 5) M2: Einbindung entfernt → Fund
        kopf = root / "layouts/_partials/head.html"
        kopf.write_text(kopf.read_text(encoding="utf-8").replace("ki_provenienz.html",
                                                                 "weg.html"),
                        encoding="utf-8")
        if not any(f["regel"] == "M2" for f in pruefen(root)[0]):
            fehler.append("M2 merkt die entfernte Einbindung nicht")
        shutil.copy(ROOT / "layouts/_partials/head.html", kopf)

        # 6) M2: KI-Siegel der Lesehilfe entfernt → Fund
        leiste = root / "layouts/_partials/ff_voice_toolbar.html"
        original = leiste.read_text(encoding="utf-8")
        leiste.write_text(original.replace("data-ff-ki-voice-label", "data-egal"),
                          encoding="utf-8")
        if not any(f["regel"] == "M2" and "Lesehilfe" in f["text"]
                   for f in pruefen(root)[0]):
            fehler.append("M2 merkt das entfernte KI-Siegel der Lesehilfe nicht")
        leiste.write_text(original, encoding="utf-8")

        # 7) M5: Feed ohne Herkunftsangabe → Fund; mit Angabe → grün
        feed([("ki-artikel", "", False), ("mensch-artikel", "", False)], kanal=False)
        funde = pruefen(root)[0]
        if not any(f["regel"] == "M5" and "Kanal-Ebene" in f["text"] for f in funde):
            fehler.append("M5 merkt die fehlende Herkunftsangabe auf Kanal-Ebene nicht")
        if not any(f["regel"] == "M5" and "ki-artikel" in f["text"] for f in funde):
            fehler.append("M5 merkt ein Feed-Item ohne Herkunftsangabe nicht")
        feed([("ki-artikel", "audio", False), ("mensch-artikel", "audio", False)])
        funde = pruefen(root)[0]
        if not any(f["regel"] == "M5" and "ffki:ai-generated" in f["text"] for f in funde):
            fehler.append("M5 merkt ein fehlendes ffki:ai-generated nicht")
        if not any(f["regel"] == "M5" and "text,audio" in f["text"] for f in funde):
            fehler.append("M5 merkt einen falschen scope im Feed nicht")
        feed([("ki-artikel", "text,audio", True), ("mensch-artikel", "audio", False)])
        m5 = [f for f in pruefen(root)[0] if f["regel"] == "M5"]
        if m5:
            fehler.append(f"M5 meldet trotz vollständiger Angabe: {[f['text'] for f in m5]}")

        # 8) M7: Spiegel driftet → Fund, und --heilen gleicht an
        spiegel = root / kp.RSS_SPIEGEL
        spiegel.write_text(spiegel.read_text(encoding="utf-8").replace(
            "ffki:ai-generated-scope", "weg"), encoding="utf-8")
        if not any(f["regel"] == "M7" for f in pruefen(root)[0]):
            fehler.append("M7 merkt die drifted RSS-Spiegelung nicht")
        ergebnis = heilen(root)
        if not any(e["art"] == "spiegel" for e in ergebnis["eingriffe"]):
            fehler.append("heilen() gleicht die RSS-Spiegelung nicht an")
        if kp.rss_spiegel_abweichung(root):
            fehler.append("nach der Heilung sind die RSS-Vorlagen noch immer ungleich")
        if any(f["regel"] == "M7" for f in ergebnis["funde_nachher"]):
            fehler.append("M7 bleibt nach der Heilung rot")

        # 9) Heilung des Impressum-Ankers + Belegzeile
        imp = root / kp.IMPRESSUM
        imp.write_text("## Hinweis zu KI-gestützten Inhalten\n\nText\n", encoding="utf-8")
        if not any(f["regel"] == "M2" for f in pruefen(root)[0]):
            fehler.append("M2 merkt den fehlenden Impressum-Anker nicht")
        ergebnis = heilen(root)
        if kp.IMPRESSUM_ANKER not in imp.read_text(encoding="utf-8"):
            fehler.append("heilen() stellt den Impressum-Anker nicht wieder her")
        if not any(e["art"] == "anker" for e in ergebnis["eingriffe"]):
            fehler.append("die Anker-Heilung fehlt im Ergebnis")
        ledger = root / kp.LEDGER
        if not ledger.is_file() or "anker" not in ledger.read_text(encoding="utf-8"):
            fehler.append("die Heilung hinterlässt keine Belegzeile im Ledger")
        if heilen(root)["eingriffe"]:
            fehler.append("heilen() ist nicht idempotent")

        # 10) M6: unmarkierte Ableitung eines deklarierten KI-Originals
        (inhalt / "posts" / "ki-artikel" / "index.md").write_text(
            "---\ntitle: ki\nai_generated: true\ncover:\n  image: images/covers/x.jpg\n"
            "  ai_generated: true\n  ki_pruefung:\n    digital_source_type: "
            "trainedAlgorithmicMedia\n---\nText\n", encoding="utf-8")
        (root / "static" / "images" / "covers" / "webp").mkdir(parents=True)
        (root / "static" / "images" / "covers" / "webp" / "x.webp").write_bytes(b"x")
        if not any(f["regel"] == "M6" and "x.webp" in f["text"]
                   for f in pruefen(root)[0]):
            fehler.append("M6 merkt eine unmarkierte Ableitung nicht")
        ergebnis = heilen(root)
        if (root / "static" / "images" / "covers" / "webp" / "x.webp").exists():
            fehler.append("heilen() entfernt die unmarkierte Ableitung nicht")
        if not any(e["art"] == "bilder" for e in ergebnis["eingriffe"]):
            fehler.append("die Bild-Heilung fehlt im Ergebnis")

        # 11) Wache führt Alter und Frist
        (root / "data").mkdir(exist_ok=True)
        (root / "data" / "ki_kennzeichnung.yaml").write_text(
            "maschinell:\n  - ki-artikel\nmenschlich:\n  - alt-eintrag\n", encoding="utf-8")
        (root / "data" / "recht-fristen.yaml").write_text(
            f"fristen:\n  - id: {FRIST_ID}\n    faellig_am: \"{_datum_heute()}\"\n",
            encoding="utf-8")
        lauf = wache(root)
        lage = lauf["lage"]
        if lage["ungeklaert"] != 1 or lage["aeltester_eintrag"] != "alt-eintrag":
            fehler.append(f"Wache führt das Register nicht: {lage}")
        if lauf["state"].get("ungeklaert_erstmals") != {"alt-eintrag": _datum_heute()}:
            fehler.append(f"Dauerzustand führt das Erst-Datum nicht: {lauf['state']}")
        if not lauf["state_geaendert"]:
            fehler.append("erster Lauf meldet keine Zustandsänderung")
        if not any(e.get("grund") == "register" for e in lauf["eskalation"]):
            fehler.append("Wache eskaliert ungeklärte Einträge kurz vor der Frist nicht")
        zweiter = wache(root)
        if zweiter["lage"]["aeltester_alter_tage"] != 0:
            fehler.append("das Alter wird beim zweiten Lauf nicht gehalten")
        if zweiter["lage"]["aeltester_eintrag"] != "alt-eintrag":
            fehler.append("der zweite Lauf verliert den ältesten Eintrag")
        if zweiter["state_geaendert"]:
            fehler.append("zweiter Lauf meldet eine Änderung – die Wache würde "
                          "täglich die Uhr committen")

        # 12) Blindheit ist kein Grün: fehlendes Werkzeug → W0 und Exit 2.
        # Gepatcht wird `kp` – DIE Referenz, mit der pruefen() arbeitet. Ein
        # zweiter `import ki_provenienz` hier drin hätte neben
        # `scripts.ki_provenienz` ein zweites Modulobjekt erzeugt: Der Test
        # patchte dann eine Kopie und die Prüfung lief blind weiter, ohne es
        # zu merken (gefunden am 07.11.2026 durch genau diesen Selbsttest).
        real = kp.abhaengigkeiten
        kp.abhaengigkeiten = lambda root=None: ["pillow (Probe)"]
        try:
            funde, _, kenn = pruefen(root)
            if not any(f["regel"] == "W0" for f in funde):
                fehler.append("fehlendes Werkzeug wird nicht als W0 gemeldet")
            if kenn.get("werkzeug_blind") != ["pillow (Probe)"]:
                fehler.append("die Blindstelle steht nicht in den Kennzahlen")
            if main_exit_werkzeug(funde) != 2:
                fehler.append("Blindheit liefert nicht Exit 2 (C33/C38)")
        finally:
            kp.abhaengigkeiten = real

    for f in fehler:
        print(f"❌ {f}")
    if fehler:
        return 2
    print("✅ KI-Provenienz-Gate: M1 Auslieferung (ganzer Baum), M2 Vorlagenvertrag, "
          "M3 Bilddatei, M4 Kanaltreue je Modalität, M5 Feed, M6 Bild-Ableitungen, "
          "M7 RSS-Spiegelung – plus Selbstheilung mit Beleg und Wache mit Alter.")
    return 0


# --------------------------------------------------------------------------
#  CLI
# --------------------------------------------------------------------------

def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    gruppe = parser.add_mutually_exclusive_group()
    gruppe.add_argument("--gate", action="store_true", help="Exit 1 bei Fund")
    gruppe.add_argument("--selftest", action="store_true")
    gruppe.add_argument("--heilen", action="store_true",
                        help="reparieren, was deterministisch reparierbar ist")
    gruppe.add_argument("--wache", action="store_true",
                        help="heilen, nachmessen, Alter der offenen Punkte führen")
    parser.add_argument("--trocken", action="store_true",
                        help="mit --heilen/--wache: nichts schreiben")
    parser.add_argument("--source-only", action="store_true",
                        help="nur Regeln ohne Bauprodukt (M2/M3/M6/M7) – für den "
                             "Selbstheilungs-Schritt VOR dem Build")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--public", default=None,
                        help="Ort des Bauprodukts (Voreinstellung public/)")
    args = parser.parse_args(argv)

    if args.selftest:
        return selbsttest()

    bau = Path(args.public) if args.public else ROOT / BAU

    try:
        if args.wache:
            ergebnis = wache(ROOT, trocken=args.trocken, bau=bau,
                             nur_quelle=args.source_only)
            if args.json:
                print(json.dumps(ergebnis, ensure_ascii=False, indent=2, default=str))
            else:
                print(wachenbericht(ergebnis))
            funde = ergebnis["funde_nachher"]
            code = main_exit_werkzeug(funde)
            if code == 2:
                kp.werkzeugbefund_melden("ki_provenienz",
                                         "KI-Provenienz-Wache blind: "
                                         + "; ".join(f["text"] for f in funde
                                                     if f["regel"] == "W0"))
            return code

        if args.heilen:
            ergebnis = heilen(ROOT, trocken=args.trocken, bau=bau,
                              nur_quelle=args.source_only)
            if args.json:
                print(json.dumps(ergebnis, ensure_ascii=False, indent=2, default=str))
            else:
                for e in ergebnis["eingriffe"]:
                    print(f"🔧 geheilt {e.get('datei')}: {e.get('text')}")
                for e in ergebnis["eskalation"]:
                    print(f"⚠️  braucht Menschen ({e.get('grund')}) {e.get('datei')}: "
                          f"{e.get('text')}")
                print(bericht(ergebnis["funde_nachher"], ergebnis["kennzahlen"]))
            funde = ergebnis["funde_nachher"]
            code = main_exit_werkzeug(funde)
            if code == 2:
                kp.werkzeugbefund_melden("ki_provenienz",
                                         "KI-Provenienz-Heilung blind: "
                                         + "; ".join(f["text"] for f in funde
                                                     if f["regel"] == "W0"))
            return code

        funde, geprueft, kennzahlen = pruefen(ROOT, bau, nur_quelle=args.source_only)
    except (OSError, ValueError) as exc:
        print(f"KI-Provenienz-Gate nicht ausführbar: {exc}")
        return 2

    if args.json:
        print(bericht(funde, kennzahlen, json_format=True))
    else:
        print(bericht(funde, kennzahlen))

    # Blind ≠ grün: Werkzeugfehler ist Exit 2, nicht „Inhalts-Fund" (Exit 1).
    code = main_exit_werkzeug(funde)
    if code == 2:
        kp.werkzeugbefund_melden("ki_provenienz",
                                 next(f["text"] for f in funde if f["regel"] == "W0"))
        return 2
    return code if args.gate else 0


if __name__ == "__main__":
    raise SystemExit(main())
