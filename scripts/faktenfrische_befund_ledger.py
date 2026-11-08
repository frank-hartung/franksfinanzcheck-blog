#!/usr/bin/env python3
"""Dauerhafte Fachbefunde der Faktenfrische (#912, #984, #912-Nachlauf).

Ein erfolgreicher Faktencheck darf ein Alter zurücksetzen, aber keinen
inhaltlichen Befund löschen. Befunde bleiben bis zu einer dokumentierten
menschlichen Entscheidung offen.

WARUM ES ZWEI HASHES GIBT (Nachtrag 03.11.2026, #912)
----------------------------------------------------
Bis zum 02.11.2026 band eine Entscheidung an `pruef_hash` – den Hash über
Titel, Beschreibung, Kurzantwort, QUELLEN und Text. Das hatte zwei Folgen,
die zusammen jeden Bestand dauerhaft rot halten:

  1. Der Lauf selbst schreibt `quellen` (die Belegkette). Jede automatische
     Quellenpflege änderte damit die „Fassung“ – und machte jede bereits
     dokumentierte Entscheidung ungültig. Die Maschine löschte also durch
     ihre eigene Arbeit den Schließpfad.
  2. Wurde ein Text zur Heilung eines Befunds geändert (genau der Zweck des
     Befunds!), passte der alte Hash nicht mehr. Eine Entscheidung über den
     neuen Text konnte den alten Befund nie mehr schließen: 8 von 13 Seiten
     trugen am 03.11.2026 solche unschließbaren Befunde, zwei weitere nur
     den Platzhalter `legacy-unbekannt`.

Deshalb gilt jetzt: **Befund und Entscheidung hängen am TEXT**
(`text_hash`: Titel, Beschreibung, Kurzantwort, Text – ohne Quellen), die
KI-Fachprüfung weiterhin an der vollständigen Prüffassung (`pruef_hash`,
inklusive Quellen; sie belegt, dass die Quellen mitgeprüft wurden).

Eine Entscheidung nennt beide Seiten:
  * `befund_fassung`  – welcher Ledger-Eintrag gemeint ist (Beweis der Zuordnung)
  * `geprueft_fassung` – welcher Text tatsächlich gelesen wurde (Beweis der Prüfung)

Sie schließt genau diesen Befund an genau diesem Text. Ändert sich der Text
später, öffnet der Befund erneut – der Mensch muss die neue Aussage erneut
anschauen. Das bleibt die Regel: **die Maschine entscheidet nie fachlich.**

FOLGEENTSCHEIDUNG (06.11.2026, Dauerheilung)
--------------------------------------------
Genau dieser Fall – Entscheidung, dann legitime redaktionelle Textänderung
(Heilung eines Befunds, Umformulierung wegen Dublette #1027) – war früher
unauflösbar: Der Befund öffnete sich erneut, aber `--entscheiden` weigerte
sich mit „Für diesen Befund existiert bereits eine Entscheidung“, und der
Loader warf bei einem zweiten Eintrag „Doppelte Entscheidung“. Eine
Heilung hätte den Bestand also dauerhaft rot gehalten, und zwar ohne
jede fachliche Ursache.

Jetzt gilt: Die Datei ist ein Anfügeprotokoll. Eine weitere Entscheidung
zum selben Befund ist zulässig und heißt FOLGEENTSCHEIDUNG – sie bindet an
den HEUTIGEN Text und referenziert ihre Vorgänger-Fassung
(`vorgaenger_geprueft_fassung`). Eine Entscheidung, die den heutigen Text
noch abdeckt, wird weiterhin abgelehnt (Idempotenz: nichts doppelt
schreiben). Die Maschine entscheidet auch hier nie – es prüft wieder ein
Mensch, nur eben die aktuelle Aussage.

NACHLESE (#984): Ein Lauf schreibt das Dossier vor seiner Bilanz. Bricht er
danach ab, liegen seine Befunde nur im Dossier. `--nachlese` liest die
Dossiers und ergänzt ausschließlich, was im Ledger fehlt – idempotent, ohne
eine Fassung zu erfinden und ohne je einen Befund zu schließen.

NUTZUNG
  python3 scripts/faktenfrische_befund_ledger.py                 # offene Befunde
  python3 scripts/faktenfrische_befund_ledger.py --fassung <datei>
  python3 scripts/faktenfrische_befund_ledger.py --text-hash <datei>
  python3 scripts/faktenfrische_befund_ledger.py --entscheiden <befund-id> \\
      --von "Name" --begruendung "was geprüft/geändert wurde" [--beleg URL]
  python3 scripts/faktenfrische_befund_ledger.py --nachlese [--apply]
  python3 scripts/faktenfrische_befund_ledger.py --wache         # entscheidbar?
  python3 scripts/faktenfrische_befund_ledger.py --selftest

EXIT: 0 ok · 1 nicht entscheidbarer/strukturfehlerhafter Befundstand
      2 Selbsttest rot oder Werkzeugfehler
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import tempfile
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "faktenfrische_queue.json"
ENTSCHEIDUNGEN = ROOT / "data" / "faktenfrische_entscheidungen.yaml"
DOSSIERS = ROOT / "data" / "research" / "artikel"
AKTE = ROOT / "BEFUND-AKTE.md"

LEGACY = "legacy-unbekannt"
HASH_RE = re.compile(r"[0-9a-f]{64}")
# Betriebsflächen (07.11.2026, #1072-Nachlauf): Zeilen, die NICHT die
# Redaktion schreibt, sondern der Betrieb – und die deshalb keine
# fachliche Entscheidung öffnen dürfen.
#
# WARUM SO ENG (zweite Fassung, 07.11.2026): Eine Zeilenregel nach Stichwort
# genügt nicht. Der Bestand enthält redaktionelle Doppelgänger, die wie
# Betriebsflächen aussehen, aber Aussagen tragen:
#   * `* **Transparenz:** Intelligente Steckdosen entlarven Standby-Sünder.`
#     – ein Bullet in „Das Wichtigste in Kürze“, keine Offenlegung.
#   * `> 💡 **Schnell-Tipp von FranksFinanzcheck:** … 24 Monate … 0,80 € …`
#     – der Werbe-Baustein nennt echte Zahlen und Fristen.
# Eine breite Stichwort-Ausnahme hätte diese Sätze für immer vor dem Ledger
# versteckt. Deshalb gilt: Jede Betriebsfläche wird über ihre STRUKTUR erkannt,
# und freigestellt wird nur, was nachweislich keine Aussage tragen kann –
# jede Zeile mit freistehender Zahl bleibt gebunden (fail-closed).
BETRIEBS_FLAECHEN = (
    # Kuratierte „Weiterlesen“-Zeile: nur Linktitel und Trenner, nie Prosa.
    # (Im Bestand gibt es 5 Prosavarianten; sie tragen verbundene Sätze und
    # werden von `_ist_weiterlesen_zeile` NICHT freigestellt.)
    re.compile(r"^\s*\*\*Weiterlesen:\*\*.*$"),
    re.compile(r"^\s*\*\*Lesetipp:\*\*.*$"),
    # Der Offenlegungssatz des Text-Gates – in allen vier Schreibweisen des
    # Bestands (`**Transparenz:**`, `> **Transparenz:**`, `* **Transparenz:**`
    # und Blockquote). Erkannt wird der SATZ, nicht das Wort.
    re.compile(r"^\s*(?:>\s*)?\*{0,2}Transparenz:\*{0,2}\s*"
               r"(?:Dieser (?:Artikel|Blog|Beitrag) enthält Affiliate)"),
    # Abbildungszeilen des Ableiters: Bild-Syntax allein, Bildzeile mit
    # Gliederungstext. Beide sind abgeleitet, keine Redaktion.
    re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$"),
    re.compile(r"^\s*\*Abbildung:"),
    # Der Affiliate-Disclaimer, den `ki_shared`/`endredaktion` einsetzt –
    # im Bestand auch als `_(…)`, `> (…)` und `*(…)` geklammert.
    re.compile(r"^\s*(?:>\s*)?[\*_]{0,2}\(?Dieser Artikel enthält Affiliate-Links"),
)
# Eine freistehende Zahl (nicht in einem Link, nicht in der Bild-Syntax) macht
# aus jeder Betriebsfläche eine Aussage. Fail-closed: Im Zweifel bleibt die
# Zeile gebunden.
_NUR_LINK = re.compile(r"!?\[[^\]]*\]\([^)]*\)")
_ZAHL = re.compile(r"\d")

# Der Werbebaustein „Schnell-Tipp“ ist die einzige Fläche, die der Betrieb
# nicht nur anfügt, sondern UMSCHREIBT: `affiliate_marketer.py` tauscht die
# `/go/<route>/`-Route gegen die thematisch bessere (RETARGET, Abschnitt
# „Sabotage-schutz“) – in 69 Zeilen des Bestands. Genau das ist der Fall, den
# `betriebsflaeche()` nicht öffnen darf.
#
# Warum er trotzdem NICHT pauschal freigestellt wird: Der Baustein nennt
# echte Fristen und Werte („Effektivpreis über 24 Monate“, „Wi-Fi 6“). Diese
# sind Teil des Werbetexts und keine Marktbehauptung – ein PROZENTWERT
# dagegen wäre eine („3,5 % Zinsen“) und bleibt deshalb gebunden.
SCHNELL_TIPP = re.compile(r"^\s*(?:>\s*)?💡\s*\*\*Schnell[-‑‐–—]Tipp")

# Die CTA-Bausteine des Marketers. Sie bestehen nur aus Anreißer + `/go/`-Link;
# `affiliate_marketer.py` tauscht die Route, `fix_cta_hygiene.py` den Anreißer.
# Beide schreiben – die Redaktion entscheidet über den Satz davor, nicht über
# den Werbeblock.
# Reine Werbezeilen: Nach dem Entfernen von Links, Hervorhebungen, Emoji und
# Satzzeichen bleibt NICHTS übrig. Das ist die belastbare Definition einer
# CTA-Zeile – unabhängig davon, wie der Marketer den Anreißer gerade formuliert.
_SCHMUCK = re.compile(r"!?\[[^\]]*\]\([^)]*\)")          # Links/Bilder
_DEKOR = re.compile(r"[\s*_~`:·•\-–—>|\u2192\u2190\u21d2\u00bb"
                    r"\U0001F300-\U0001FAFF\u2600-\u27BF\uFE0F]+")
_GO_LINK = re.compile(r"\]\(/go/[^)]*\)")


def _nur_werbung(zeile: str) -> bool:
    """Reine Werbezeile: Anreißer-Überschrift + /go/-Link, sonst kein Satz.

    Erlaubt ist ein kurzer Anreißer in Fettschrift, der auf einen Doppelpunkt
    endet („👉 **Jetzt vergleichen und sparen:** [**→ …**](/go/x/)"). Er ist
    eine Überschrift des Werbeblocks, kein Satz: kein Verb am Ende, kein
    Punkt. Sobald danach echter Fließtext steht, bleibt die Zeile gebunden.
    """
    if not _GO_LINK.search(zeile):
        return False                                  # ohne /go/-Link: keine CTA
    rest = _SCHMUCK.sub("", zeile)
    # Anreißer-Überschrift am Zeilenanfang entfernen (endet auf Doppelpunkt).
    rest = re.sub(r"^\s*(?:>\s*)?(?:👉\s*)?\*\*[^*]{1,60}:\*\*", "", rest)
    rest = _DEKOR.sub("", rest)
    return not rest.strip(" :.,;!?()[]{}'\"")
SPAR_TIPP = re.compile(r"^\s*(?:>\s*)?💶\s*\*\*Spar[-‑‐–—]Tipp")

# Vom Ableiter erzeugte Bildzeilen (`abbildungen_ableiten.py`). Sie tragen die
# Gliederung des Artikels als Zahlen („5 Stationen“) – abgeleitet, nicht
# behauptet. Deshalb steht diese Stufe VOR der Zahl-Sperre.
# ABGELEITET wird über die HERKUNFT erkannt, nicht über das Wort „Abbildung"
# (08.11.2026, Rückfall-Schutz aus #1072; Test `…bildzeile_bleibt_aussage`):
# Der Ableiter schreibt seine Herkunft selbst in die Zeile
# („(eigene Darstellung …)"). Fehlt dieser Vermerk, ist die Zeile Redaktion –
# und eine Zahl darin bleibt eine Behauptung, die geprüft werden muss.
# Zuvor galt JEDE `*Abbildung:`-Zeile als abgeleitet; damit wäre eine
# handgeschriebene Bildunterschrift („… 30 Prozent Abweichung") still aus dem
# Aussage-Hash gefallen und hätte eine dokumentierte Entscheidung blind
# gehalten. Die 40 Bildzeilen des Bestands tragen den Vermerk ausnahmslos –
# der Hash ändert sich dadurch für keinen Artikel.
ABGELEITET = re.compile(
    r"^\s*(?:!\[[^\]]*\]\([^)]*\)\s*$"
    # Aktueller Ableiter: Herkunftsvermerk in der Zeile.
    r"|\*Abbildung:[^\n]*\(eigene Darstellung[^\n]*\)\.?\*\s*$"
    # Altformat desselben Ableiters (vor dem Herkunftsvermerk):
    # „Gliederung zu „…“ – N Stationen von „…“ bis „…“*". Nur diese exakte
    # Form – eine beliebige Bildzeile bleibt Redaktion und damit Aussage.
    r"|\*Abbildung: Gliederung zu „[^“”]+“ – \d+ Stationen von "
    r"„[^“”]+“ bis „[^“”]+“\*\s*$)")
WEITERLESEN_PROSA = re.compile(
    r"^\s*\*\*Weiterlesen:\*\*\s*(?:Der|Die|Das|Im|In|Wer|Was|Hier)\b")


def _ist_weiterlesen_zeile(zeile: str) -> bool:
    """Linkliste ja, Fließtext nein.

    Die Weiterlesen-Zeile ist der Ort, an den `gsc_abdeckung.py` schreibt
    (#1097). Sie besteht dann aus Linktiteln und `·` – keine Aussage. Beginnt
    der Text nach dem Marker jedoch mit einem Satz, ist es Redaktion, die
    gelesen und geprüft werden muss.
    """
    if WEITERLESEN_PROSA.match(zeile):
        return False
    return True


def betriebsflaeche(zeile: str) -> bool:
    """Ist diese Zeile Betriebsfläche – und darf sie die Aussage nicht öffnen?

    Drei Stufen, weil die Flächen unterschiedlich viel tragen können:
      1. ABGELEITET (`*Abbildung:`, Bild-Syntax): Der Ableiter erzeugt die
         Zeile samt Gliederungszahlen aus dem Artikel – sie ist nie eine
         eigenständige Behauptung. Immer Betriebsfläche.
      2. WERBETEXT (`Schnell-Tipp`): wird umgeschrieben (RETARGET), trägt
         aber teils Werte. Nur ohne Prozentwert Betriebsfläche.
      3. VERWEIS (Weiterlesen, Lesetipp, Offenlegungssatz, Disclaimer):
         Nur als Linkliste/Formelsatz Betriebsfläche; jede freistehende
         Zahl hält die Zeile gebunden (fail-closed).
    """
    if ABGELEITET.match(zeile):
        return True
    if SCHNELL_TIPP.match(zeile) or SPAR_TIPP.match(zeile):
        # Prozentwerte sind Marktbehauptungen, alles andere ist Werbetext.
        return "%" not in zeile
    if _nur_werbung(zeile):
        return True   # reiner /go/-Link, kein Satz
    if _ZAHL.search(_NUR_LINK.sub("", zeile)):
        return False  # eine Zahl ist immer Aussage, egal wer die Zeile schrieb
    if any(muster.match(zeile) for muster in BETRIEBS_FLAECHEN):
        return _ist_weiterlesen_zeile(zeile)
    return False


# EINGEFROREN (07.11.2026): Die erste Fassung der Betriebsflächen-Regel, wie
# sie an diesem Tag um 09:00 UTC im Ledger stand. Sie wird NIE mehr geändert –
# sie ist der Beweis dafür, dass eine frühere Projektion nicht entwertet
# wird, wenn die Erkennung genauer wird. `PROJEKTIONEN` nennt sie `betrieb-v1`.
BETRIEBS_FLAECHEN_V1 = (
    re.compile(r"^\s*\*\*Weiterlesen:\*\*.*$"),
    re.compile(r"^\s*\*\*Lesetipp:\*\*.*$"),
    re.compile(r"^\s*\*\*Transparenz:\*\*.*$"),
    re.compile(r"^\s*!\[[^\]]*\]\([^)]*\)\s*$"),
    re.compile(r"^\s*\*Abbildung:.*\*\s*$"),
    re.compile(r"^\s*\*?\(?Dieser Artikel enthält Affiliate-Links.*$"),
)


def _betriebsflaeche_v1(zeile: str) -> bool:
    """Die Vorgänger-Regel, eingefroren – nur für die Rückwärtsbindung."""
    return any(muster.match(zeile) for muster in BETRIEBS_FLAECHEN_V1)

# Eine Begründung, die nur „ok“ sagt, ist keine Entscheidung. Die Grenze ist
# bewusst klein (kein Aufsatz), aber groß genug, um die Prüfung zu benennen.
BEGRUENDUNG_MIN = 20


class LedgerFehler(ValueError):
    """Ungültiger Beweisstand; niemals als leere Befundliste behandeln."""


# ----------------------------------------------------------------------
# Struktur der Schließakte: lesen, prüfen, heilen (08.11.2026, #1098)
# ----------------------------------------------------------------------
class StrengerLoader(yaml.SafeLoader):
    """YAML-Leser, der einen DOPPELTEN Schlüssel NICHT still überschreibt.

    WARUM (08.11.2026, #1098)
    -------------------------
    `data/faktenfrische_entscheidungen.yaml` ist seit dem 06.11.2026 ein
    Anfügeprotokoll: mehrere Entscheidungen zu demselben Befund stehen
    untereinander als eigene Listenpunkte. Am 08.11.2026 lagen 20 davon
    NICHT als eigener Listenpunkt, sondern als zweiter Schlüsselblock
    INNERHALB eines fremden Eintrags (Writer-Fehler beim Anfügen).

    `yaml.safe_load` nimmt dann still den LETZTEN Wert. Folge: Der Eintrag
    trug eine `geprueft_fassung` und einen `vorgaenger_geprueft_fassung` aus
    zwei VERSCHIEDENEN Ketten. Die Wache meldete „Ungültige Folgeentscheidung
    – Vorgänger fehlt oder stimmt nicht", obwohl der Befund ordentlich
    entschieden war, und die Scorecard fiel als Werkzeugfehler aus (#1098).
    Die überschriebenen Felder waren für keinen Leser mehr sichtbar – also
    auch nicht prüfbar.

    Deshalb gilt ab jetzt: Ein doppelter Schlüssel ist ein STRUKTURFEHLER,
    kein Datenwert. Er scheitert laut (`LedgerFehler`) und wird mit
    `--reparieren` geheilt; er darf nie wieder als „nichts gesehen" gelten.
    """

    def construct_mapping(self, node, deep=False):
        gesehen: set = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in gesehen:
                zeile = getattr(key_node.start_mark, "line", -1) + 1
                raise LedgerFehler(
                    f"Doppelter Schlüssel `{key}` (Zeile {zeile}) – der "
                    "Eintrag würde still überschrieben. Heilung: "
                    "`python3 scripts/faktenfrische_befund_ledger.py "
                    "--reparieren --apply`.")
            gesehen.add(key)
        return super().construct_mapping(node, deep=deep)


def _laden_streng(path: Path) -> dict:
    """YAML mit Duplikat-Schutz laden; jeder Strukturfehler bleibt sichtbar."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise LedgerFehler(f"{path.name} nicht lesbar: {exc}") from exc
    try:
        daten = yaml.load(text, Loader=StrengerLoader) or {}
    except LedgerFehler:
        raise
    except yaml.YAMLError as exc:
        raise LedgerFehler(f"{path.name} ist kein gültiges YAML: {exc}") from exc
    if not isinstance(daten, dict):
        raise LedgerFehler(f"{path.name} muss ein Mapping sein")
    return daten


def _laden_tolerant(path: Path) -> dict:
    """Altverhalten (letzter Schlüssel gewinnt) – nur für Vorher/Nachher-Beweis.

    Diese Lesart ist NICHT die Wahrheit, sondern das, was die Werkzeuge bis
    zum 08.11.2026 sahen. Der Heiler vergleicht damit, dass er ausschließlich
    die Struktur ändert und keinen dokumentierten Inhalt verschiebt.
    """
    try:
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return {}


def _yaml_wert(node):
    """YAML-Knoten in Python-Werte übersetzen (Reihenfolge bleibt erhalten).

    Skalare werden über ihren TAG typisiert – `folgeentscheidung: true` muss
    ein Wahrheitswert bleiben. Ein `"true"` als Zeichenkette hätte die
    Kettenprüfung („ist es wirklich `is True`?") stillschweigend ausgehebelt.
    Datumsangaben bleiben Zeichenketten: Die Akte schreibt `2026-11-07`,
    ein `datetime.date` würde beim erneuten Serialisieren das Format ändern.
    """
    if isinstance(node, yaml.ScalarNode):
        if node.tag == "tag:yaml.org,2002:bool":
            return node.value.strip().lower() in ("true", "yes", "on")
        if node.tag == "tag:yaml.org,2002:null":
            return None
        if node.tag == "tag:yaml.org,2002:int":
            return int(node.value)
        if node.tag == "tag:yaml.org,2002:float":
            return float(node.value)
        return node.value
    if isinstance(node, yaml.MappingNode):
        return {k.value: _yaml_wert(v) for k, v in node.value}
    if isinstance(node, yaml.SequenceNode):
        return [_yaml_wert(v) for v in node.value]
    return None  # pragma: no cover - Alias-/Sonderfälle


def _entscheidungs_segmente(path: Path) -> list[tuple[int, list[dict]]]:
    """Listeneinträge in ihre logischen Entscheidungen zerlegen.

    Ein Eintrag mit doppelten Schlüsseln ist in Wahrheit MEHRERE
    Entscheidungen: Jeder erneute Schlüssel beginnt einen neuen Block.
    Genau so ist der Fehler entstanden – hier wird er wieder lesbar.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []
    except OSError as exc:
        raise LedgerFehler(f"{path.name} nicht lesbar: {exc}") from exc
    try:
        wurzel = yaml.compose(text)
    except yaml.YAMLError as exc:
        raise LedgerFehler(f"{path.name} ist kein gültiges YAML: {exc}") from exc
    if wurzel is None:
        return []
    if not isinstance(wurzel, yaml.MappingNode):
        raise LedgerFehler(f"{path.name} muss ein Mapping sein")
    folge = None
    for schluessel, wert in wurzel.value:
        if schluessel.value == "entscheidungen":
            folge = wert
    if folge is None:
        return []
    if not isinstance(folge, yaml.SequenceNode):
        raise LedgerFehler("Entscheidungen müssen eine Liste sein")
    ergebnis = []
    for eintrag in folge.value:
        if not isinstance(eintrag, yaml.MappingNode):
            raise LedgerFehler("Entscheidung muss ein Mapping sein")
        segmente: list[dict] = []
        aktuell: dict = {}
        for schluessel, wert in eintrag.value:
            name = schluessel.value
            if name in aktuell and aktuell:
                segmente.append(aktuell)
                aktuell = {}
            aktuell[name] = _yaml_wert(wert)
        segmente.append(aktuell)
        ergebnis.append((eintrag.start_mark.line + 1, segmente))
    return ergebnis


def struktur_pruefen(path: Path = ENTSCHEIDUNGEN) -> dict:
    """Befund zur DATEI-STRUKTUR (nicht zur Fachlichkeit)."""
    segmente = _entscheidungs_segmente(path)
    funde = []
    for zeile, segs in segmente:
        if len(segs) > 1:
            doppelt = sorted({k for s in segs[1:] for k in s})
            funde.append({
                "zeile": zeile,
                "segmente": len(segs),
                "schluessel": doppelt,
                "befund": (f"Zeile {zeile}: {len(segs)} Entscheidungen in einem "
                           f"Listeneintrag untereinander (doppelte Schlüssel: "
                           f"{', '.join(doppelt)})"),
            })
    return {"datei": str(path), "eintraege": len(segmente),
            "strukturfehler": len(funde), "funde": funde, "ok": not funde}


def _befund_index(queue_path: Path) -> dict[str, list[dict]]:
    """Beanstandungstext → Ledger-Einträge (Slug, ID, Befundfassung)."""
    try:
        roh = json.loads(queue_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    index: dict[str, list[dict]] = {}
    for eintrag in eintraege_aus_queue(roh if isinstance(roh, dict) else {}):
        text = re.sub(r"\s+", " ", str(eintrag.get("text") or "")).strip()
        if text:
            index.setdefault(text, []).append(eintrag)
    return index


def _befund_zu_text(beanstandung: str | None,
                    index: dict[str, list[dict]]) -> dict | None:
    """Ordnet einen verlorenen Block über seine Beanstandung eindeutig zu.

    Ein Block, der aus einem fremden Eintrag herausgerissen wurde, hat keinen
    Slug und keine Befund-ID. Die Beanstandung ist der einzige belastbare
    Zeuge – sie muss GENAU EINEN Ledger-Eintrag treffen, sonst wird nicht
    geraten (fail-closed, der Heiler meldet dann einen Handbefund).
    """
    text = re.sub(r"\s+", " ", str(beanstandung or "")).strip()
    if len(text) < 20:
        return None
    treffer = index.get(text, [])
    if len(treffer) == 1:
        return treffer[0]
    # Der Ledger kürzt Beanstandungen auf 400 Zeichen – Präfixvergleich.
    kandidaten: list[dict] = []
    for k, treffer in index.items():
        if k.startswith(text[:80]) or text.startswith(k[:80]):
            for eintrag in treffer:
                if eintrag not in kandidaten:
                    kandidaten.append(eintrag)
    return kandidaten[0] if len(kandidaten) == 1 else None


def struktur_reparieren(path: Path = ENTSCHEIDUNGEN, *,
                        queue_path: Path = QUEUE,
                        apply: bool = False) -> dict:
    """Zerlegte Einträge wieder zu eigenständigen Entscheidungen machen.

    Der Heiler ist bewusst konservativ:

      * Er ändert NUR die Struktur (jeder Block wird ein eigener
        Listenpunkt) und ergänzt ausschließlich Felder, die dem Block beim
        Anfügen verloren gegangen sind (Slug, Befund-ID, Fassungsbindung).
      * Er erfindet keinen Inhalt: Beanstandung/Beleg/Begründung bleiben
        zeichengenau; eine Zuordnung ohne eindeutigen Zeugen wird gemeldet,
        nicht geraten.
      * Er beweist nach dem Schreiben zwei Dinge: Jeder Block ist
        feldgleich zu seinem Vorher-Stand (nichts verschoben, nichts
        verloren), und die Akte ist streng lesbar samt gültiger Ketten.
        Schlägt eines fehl, werden die ORIGINAL-Bytes zurückgeschrieben.
      * Ein Fragment ohne Person und Begründung ist keine Entscheidung. Es
        wird ausgewiesen und verworfen – aber nie, wenn es der jüngste Beleg
        seines Befunds ist (dann Handprüfung statt Datenverlust).
    """
    try:
        original = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise LedgerFehler(f"{path.name} nicht lesbar: {exc}") from exc
    segmente = _entscheidungs_segmente(path)
    index = _befund_index(queue_path)
    vorher_bloecke = [dict(block) for _z, segs in segmente for block in segs]
    neu: list[dict] = []
    ergaenzt: list[dict] = []
    offen: list[dict] = []
    verworfen: list[dict] = []
    paare: list[tuple[dict, dict]] = []
    letzte: dict[tuple, dict] = {}
    for _zeile, segs in segmente:
        vorheriger: dict | None = None
        for nummer, roh_block in enumerate(segs):
            block = dict(roh_block)
            if nummer > 0:
                ziel = _befund_zu_text(block.get("beanstandung"), index)
                if ziel:
                    block.setdefault("slug", ziel["slug"])
                    block.setdefault("befund_id", ziel["id"])
                    block.setdefault("befund_ursprung_slug",
                                     ziel.get("ursprungs_slug", ziel["slug"]))
                    block.setdefault("typ", ziel.get("typ"))
                    block.setdefault("beanstandung", ziel.get("text"))
                    block.setdefault("befund_fassung", ziel.get("fassung_sha256"))
                elif vorheriger:
                    for feld in ("slug", "befund_id", "befund_ursprung_slug",
                                 "typ", "beanstandung", "befund_fassung"):
                        if not block.get(feld) and vorheriger.get(feld):
                            block[feld] = vorheriger[feld]
                    block["uebernommen_aus"] = "vorheriger-block"
                else:  # pragma: no cover - erster Block hat immer slug/id
                    offen.append({"zeile": _zeile, "grund": "Block ohne Zuordnung"})
                if not block.get("geprueft_fassung") and vorheriger:
                    block["geprueft_fassung"] = vorheriger.get("geprueft_fassung")
            if vorheriger:
                fehlend = [f for f in ("slug", "befund_id", "geprueft_fassung")
                           if not block.get(f)]
                if fehlend:
                    offen.append({"zeile": _zeile, "grund":
                                  f"Block ohne {', '.join(fehlend)}"})
                    continue
            # Ein Block OHNE Person und Begründung ist keine Entscheidung,
            # sondern ein Schreibartefakt (das Schema verlangt beides). Er
            # wird nicht mit erfundenem Inhalt aufgefüllt, sondern
            # ausgewiesen und verworfen – der belegte Folgeblock bleibt.
            if not (str(block.get("entschieden_von") or "").strip()
                    and str(block.get("begruendung") or "").strip()):
                verworfen.append({
                    "zeile": _zeile,
                    "slug": block.get("slug"),
                    "befund_id": block.get("befund_id"),
                    "geprueft_fassung": (block.get("geprueft_fassung") or "")[:12],
                    "grund": "Fragment ohne Person/Begründung (kein Entscheid)",
                })
                continue
            # Kette reparieren: Der Anfüge-Vorgang hat bei einigen Blöcken den
            # Vorgänger verschluckt (er landete im Folgeblock). Belegt ist der
            # Vorgänger durch die Reihenfolge der Akte – die letzte
            # Entscheidung desselben Befunds. Nur wenn dort keine steht,
            # bleibt der Block ohne Vorgänger (erster Entscheid).
            schluessel = (block.get("slug"), block.get("befund_id"))
            vorher_im_ledger = letzte.get(schluessel)
            if (vorher_im_ledger and not block.get("vorgaenger_geprueft_fassung")
                    and vorher_im_ledger.get("geprueft_fassung")):
                block["vorgaenger_geprueft_fassung"] = \
                    vorher_im_ledger["geprueft_fassung"]
                block["folgeentscheidung"] = True
                block["kette_ergaenzt"] = True
            elif vorheriger and not block.get("vorgaenger_geprueft_fassung"):
                block["vorgaenger_geprueft_fassung"] = \
                    vorheriger.get("geprueft_fassung")
                block["folgeentscheidung"] = True
                block["kette_ergaenzt"] = True
            if nummer > 0:
                # Reihenfolge der Beweisfelder vereinheitlichen (Kette zuerst).
                kopf = {k: block.pop(k) for k in
                        ("slug", "befund_ursprung_slug", "befund_id") if k in block}
                block = {**kopf, **block}
                ergaenzt.append({
                    "zeile": _zeile,
                    "befund_id": block.get("befund_id"),
                    "slug": block.get("slug"),
                    "geprueft_fassung": (block.get("geprueft_fassung") or "")[:12],
                })
            neu.append(block)
            paare.append((roh_block, block))
            letzte[schluessel] = block
            vorheriger = block
    bericht = {"datei": str(path), "segmente": len(neu),
               "strukturfehler": sum(1 for _, s in segmente if len(s) > 1),
               "getrennt": len(ergaenzt), "ergaenzt": ergaenzt,
               "unzuordenbar": offen, "verworfen": verworfen,
               "geschrieben": False}
    if offen:
        bericht["fehler"] = ("Blöcke ohne eindeutigen Zeugen – nicht "
                             "geschrieben (fail-closed)")
        return bericht
    # Ein verworfener Fragmentblock darf NIE der letzte Beleg seines Befunds
    # sein: Dann trüge er den gültigen Entscheid, und Verwerfen würde eine
    # dokumentierte Prüfung löschen. Fail-closed statt Datenverlust.
    letzter_block: dict[tuple, int] = {}
    for nummer, block in enumerate(vorher_bloecke):
        letzter_block[(block.get("slug"), block.get("befund_id"))] = nummer
    for eintrag in verworfen:
        stelle = letzter_block.get((eintrag.get("slug"), eintrag.get("befund_id")))
        if stelle is not None and vorher_bloecke[stelle] is not None:
            if (vorher_bloecke[stelle].get("geprueft_fassung") ==
                    eintrag.get("geprueft_fassung") and
                    not vorher_bloecke[stelle].get("entschieden_von")):
                bericht["fehler"] = (
                    f"Zeile {eintrag['zeile']}: Fragment ist der jüngste Beleg "
                    "seines Befunds – nicht verworfen (Handprüfung nötig)")
                return bericht
    if not apply:
        return bericht
    if not bericht["strukturfehler"]:
        return bericht
    def _zurueck(fehler: str) -> dict:
        path.write_text(original, encoding="utf-8")
        bericht["fehler"] = f"{fehler} – zurückgerollt"
        return bericht

    _yaml_schreiben(path, {"entscheidungen": neu})
    # BEWEIS 1: Kein dokumentierter Block ist verloren oder verändert.
    # Verglichen wird Block für Block gegen die Zerlegung VOR dem Schreiben –
    # nicht gegen die tolerante Lesart (die war ja gerade der Defekt).
    nachher_bloecke = [dict(block) for _z, segs in _entscheidungs_segmente(path)
                       for block in segs]
    if len(nachher_bloecke) != len(neu):
        return _zurueck(f"Blockzahl hätte sich geändert "
                        f"({len(nachher_bloecke)} statt {len(neu)})")
    for alt, neu_block in paare:
        for feld, wert in alt.items():
            if neu_block.get(feld) != wert:
                return _zurueck(f"Blockinhalt `{feld}` hätte sich geändert")
    if len(paare) != sum(len(segs) for _z, segs in segmente) - len(verworfen):
        return _zurueck("Abrechnung der Blöcke stimmt nicht")
    # BEWEIS 2: Die Datei ist ab jetzt streng lesbar und die Ketten stimmen.
    try:
        entscheidungen_laden(path)
    except LedgerFehler as exc:  # pragma: no cover - Schutznetz
        return _zurueck(f"Reparatur ergab ungültige Akte: {exc}")
    bericht["geschrieben"] = True
    return bericht


# ----------------------------------------------------------------------
# Hashes: eine Prüffassung, ein Text
# ----------------------------------------------------------------------
def body_hash(body: str) -> str:
    return hashlib.sha256(body.encode("utf-8")).hexdigest()


def _frontmatter(art: dict) -> dict:
    fm = yaml.safe_load(art.get("fm", "")) or {}
    if not isinstance(fm, dict):
        raise LedgerFehler("Frontmatter ist kein Mapping")
    return fm


# HINWEIS (07.11.2026, #1072): Hier stand eine ZWEITE, ältere `pruef_hash`-
# Definition ohne `pin_title`/`pin_description`. Sie war seit #996 toter Code
# – Python nimmt die spätere –, aber ein Bearbeiter hätte sie „reparieren“
# können und damit die Werbeflächen aus der Prüffassung verloren (genau der
# Rückfall, den #996 geschlossen hat). Der Vertrag C46 verlangt zwei Hashes,
# nicht drei Definitionen. Entfernt; der Selftest prüft die Bindung.


# ----------------------------------------------------------------------
# Die Projektionen der Aussage (07.11.2026, #1072)
# ----------------------------------------------------------------------
# EINE LEBENSREGEL FÜR DIESEN LEDGER:
#   Eine Regeländerung darf keine Redaktionsarbeit löschen – und ein
#   Textbefund darf keine Betriebsarbeit öffnen.
#
# Beides ist derselbe Fehler von zwei Seiten: Eine Entscheidung wurde an
# einen HASH gebunden, ohne zu sagen, WELCHE Projektion des Textes dieser
# Hash abbildet. Ändert man die Projektion (neue Betriebsfläche, neuer
# Filter, feinerer Anker), passen alte Hashes nicht mehr – nicht weil sich
# der Text geändert hat, sondern weil das Messgerät sich geändert hat.
#
# Deshalb steht hier jede Fassung, die je geschrieben wurde, mit ihrer
# eigenen Projektion. `PROJEKTIONEN[0]` ist die Vorgabe für NEUE
# Entscheidungen; alle weiteren sind reine Rückwärtsbindung. Kommt eine
# neue Fläche dazu, wird EINE Projektion ergänzt – nicht eine Regel
# verschärft, die bestehende Entscheidungen entwertet.
#
# Der Bestand zeigt, dass das nötig ist: Bei Camping/Gas/Frugalismus sind
# die Aussageflächen am Entscheidungstag und heute nachweislich identisch,
# trotzdem öffnete jede Projektionsänderung die Entscheidungen erneut.
# Jede Projektion ist ein Paar (Betriebsflächen-Regel, Rand-Behandlung).
# Der Rand ist der zweite, leicht übersehene Teil des Problems: Der frühere
# `text_hash` rechnete über den ROHEN Body, der heutige strippt die
# Randleerzeilen. Ein Artikel, der auf "\n" endete, bekam dadurch einen
# anderen Hash, obwohl der Satz derselbe war – dieselbe Klasse von Fehler
# wie die Betriebsflächen, nur unsichtbar.
PROJEKTIONEN = ("betrieb-v2", "betrieb-v2-rand", "betrieb-v1",
                "betrieb-v1-rand", "roh-rand")
_BETRIEBSREGEL = {"betrieb-v2": "betrieb-v2", "betrieb-v2-rand": "betrieb-v2",
                  "betrieb-v1": "betrieb-v1", "betrieb-v1-rand": "betrieb-v1",
                  "roh-rand": "keine"}
# "nackt" = ohne Rand-Leerzeilen (neue + randneutrale Anker)
# "ein"   = mit genau einer Schlusszeile (Beweisform der gespeicherten Anker)
_RAND_ART = {"betrieb-v2": "nackt", "betrieb-v1": "nackt", "roh-rand": "nackt",
             "betrieb-v2-rand": "ein", "betrieb-v1-rand": "ein"}


def aussage_body(body: str, projektion: str = PROJEKTIONEN[0]) -> str:
    """Der Body ohne die Flächen, die der BETRIEB schreibt – nicht der Mensch.

    WARUM (Vorgang #1072-Nachlauf, 07.11.2026)
    ------------------------------------------
    `text_hash` band eine Entscheidung an den vollständigen Body. Damit
    öffnete jede Maschinen-Schreibe eine menschliche Entscheidung neu, obwohl
    sich kein Satz der Aussage geändert hatte:

      * `**Weiterlesen:** …` – `gsc_abdeckung.py --verlinkung --heilen`
        hängt dort einen Link an (Selbstheilung #1097, seit 06.11. live).
      * `![…](…)` und `*Abbildung: …*` – der Abbildungs-Lauf schreibt die
        abgeleiteten Bildzeilen nach.
      * `**Transparenz:** …` und der Affiliate-Disclaimer – beide werden vom
        Text-Gate eingesetzt.
      * der Anhang `## Weiterrechnen und vertiefen` – Werkzeug-Links, keine
        Redaktion.

    Am 07.11.2026 standen deshalb **8 von 11** bereits dokumentierten
    Entscheidungen wieder offen (Gas 08-12, Gas 08-24, Camping), obwohl die
    Aussageflächen am Entscheidungstag nachweislich identisch waren. Das ist
    derselbe Fehler wie bei den Quellen (#912): Die Maschine löschte durch
    ihre eigene Arbeit den Schließweg – und die Scorecard zeigte „F4
    blockiert“ für Sätze, die niemand angefasst hatte.

    Die UMFANGREICHE Fläche bleibt die sichere: Was die Redaktion selbst
    schreibt (Überschriften, Tabellen, Beispiele, FAQ, Affiliate-Sätze im
    Fließtext), wird weiter geprüft. Entfernt werden ausschließlich die
    erkennbar betrieblichen Zeilen – und wer eine solche Zeile ändert,
    entscheidet sie ohnehin nicht fachlich. Eine echte Textänderung öffnet
    die Entscheidung weiterhin (Beweis: `--selftest` Fall (k)).

    PROJEKTIONEN (07.11.2026, siehe `PROJEKTIONEN`):
      * `betrieb-v2` – die enge Fassung: Ein Betriebsflächen-Stichwort befreit
        nur ohne freistehende Zahl, `**Weiterlesen:**` nur als Linkliste
        (5 Prosavarianten im Bestand bleiben gebunden), `Transparenz:` nur
        als Offenlegungssatz (das redaktionelle Bullet in „Das Wichtigste in
        Kürze“ bleibt gebunden).
      * `betrieb-v1` – die erste, breitere Fassung (nur Stichwort). Sie wird
        nie für neue Entscheidungen geschrieben, hält aber die am 07.11.2026
        getroffenen Entscheidungen gültig. Ohne sie hätte die Verschärfung
        13 dokumentierte Entscheidungen wieder geöffnet – genau der Fehler,
        den diese Datei verhindern soll.
    """
    if projektion not in PROJEKTIONEN:
        raise LedgerFehler(f"Unbekannte Projektion `{projektion}` – "
                           f"erlaubt: {', '.join(PROJEKTIONEN)}")
    zeilen = str(body or "").split("\n")
    ergebnis: list[str] = []
    im_werkzeug_anhang = False
    for zeile in zeilen:
        if not im_werkzeug_anhang and \
                re.match(r"^##\s+Weiterrechnen und vertiefen\s*$", zeile, re.I):
            im_werkzeug_anhang = True
            continue
        if im_werkzeug_anhang:
            if re.match(r"^##\s+", zeile):
                im_werkzeug_anhang = False
            else:
                continue
        regel = _BETRIEBSREGEL[projektion]
        if (betriebsflaeche(zeile) if regel == "betrieb-v2"
                else _betriebsflaeche_v1(zeile)):
            continue
        ergebnis.append(zeile)
    text = "\n".join(ergebnis)
    text = re.sub(r"<!--.*?-->", "", text, flags=re.S)
    # RAND (nachgemessen am 07.11.2026): Der frühere `text_hash` rechnete
    # über den ROHEN Body; ein Artikel, der auf "\n" endete, hatte dort einen
    # anderen Hash als derselbe Text ohne die letzte Leerzeile. Beim Anhängen
    # einer Betriebsfläche entstehen genau solche Zeilen. Beide Varianten
    # stehen deshalb als eigene Projektion zur Verfügung:
    #   "nackt" – ohne Rand-Leerzeilen (Vorgabe für NEUE Entscheidungen),
    #   "ein"   – mit genau einer schließenden Zeile (die Form, in der
    #             Artikel gespeichert werden und in der der Alt-Hash rechnete).
    if _RAND_ART[projektion] == "ein":
        return text.rstrip("\n") + "\n"
    return text.strip("\n")


def text_hash(art: dict, projektion: str = PROJEKTIONEN[0]) -> str:
    """Hash der Aussageflächen – OHNE Quellen und ohne Betriebsflächen.

    Quellen schreibt der Lauf selbst. Ein Befund über eine Aussage darf
    nicht dadurch unschließbar werden, dass die Belegkette aufgefrischt
    wird; eine Aussageänderung dagegen muss jede Entscheidung öffnen.
    Seit dem 07.11.2026 gilt dasselbe für die Flächen, die fremde Werkzeuge
    schreiben (Weiterlesen-Zeile, Abbildungen, Transparenz, Disclaimer,
    Werkzeug-Anhang) – Begründung und Beweis: `aussage_body()`.
    """
    fm = _frontmatter(art)
    material = {
        "title": fm.get("title", ""),
        "description": fm.get("description", ""),
        "kurzantwort": fm.get("kurzantwort", ""),
        "body": aussage_body(art.get("body", ""), projektion),
    }
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def text_hash_volltext(art: dict) -> str:
    """Hash des VOLLSTÄNDIGEN Texts – Betriebsflächen inklusive.

    Das ist der Alt-Anker von `text_hash` (bis 07.11.2026, 09:00 UTC) und
    heute die Gegenprobe: Eine abgeleitete Bildzeile darf die Aussage NICHT
    ändern, den Volltext-Hash aber sehr wohl (sie ist Text, nur keine
    Behauptung). Wer hier und in `text_hash` denselben Wert sieht, hat eine
    Betriebsfläche versehentlich als Aussage gebunden – oder umgekehrt.
    """
    return _text_hash_roh(art, "roh")


def pruef_hash(art: dict) -> str:
    """Fassungs-Hash über Text UND die mitgeprüften Aussageflächen.

    Seit #996 (03.11.2026) gehören auch `pin_title` und `pin_description`
    zum Hash: Die Werbeflächen hatten Superlative und Sparversprechen
    zurückgebracht, ohne dass sich die Fassung änderte – eine
    fassungsgebundene Entscheidung hätte den Rückfall nicht gesehen.
    Ältere Dossier- und Queue-Hashes bleiben gespeicherte Historie; der
    nächste Lauf bindet die Fassung mit dem erweiterten Material neu.
    """
    fm = yaml.safe_load(art.get("fm", "")) or {}
    if not isinstance(fm, dict):
        raise LedgerFehler("Frontmatter ist kein Mapping")
    material = {}
    material["title"] = fm.get("title", "")
    material["description"] = fm.get("description", "")
    material["kurzantwort"] = fm.get("kurzantwort", "")
    material["pin_title"] = fm.get("pin_title", "")
    material["pin_description"] = fm.get("pin_description", "")
    material["quellen"] = fm.get("quellen") or []
    material["body"] = art.get("body", "")
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def befund_id(slug: str, befund: dict) -> str:
    text = "\x1f".join((slug, str(befund.get("typ", "befund")),
                        str(befund.get("text", "")).strip()))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def canonical_slug(slug: str, aliases: dict[str, str]) -> str:
    """Aktuellen Slug einer Alias-Kette liefern – fail-closed bei Schleifen.

    Ein Datums-Lift ändert den Ordner, aber nicht die Identität eines bereits
    erhobenen Befunds. Die Kette bleibt absichtlich klein und explizit: Jeder
    Sprung stammt aus `faktenfrische_aliases` am aktuellen Artikel. Fehlerhafte
    Metadaten werden nie als „Seite gelöscht, alles erledigt“ gelesen.
    """
    aktuell = str(slug)
    gesehen: set[str] = set()
    while aktuell in aliases:
        if aktuell in gesehen:
            raise LedgerFehler(f"Schleife in faktenfrische_aliases bei `{slug}`")
        gesehen.add(aktuell)
        ziel = aliases[aktuell]
        if not isinstance(ziel, str) or not ziel.strip() or ziel != ziel.strip():
            raise LedgerFehler(f"Ungültiges Slug-Alias-Ziel bei `{aktuell}`")
        if ziel == aktuell:
            raise LedgerFehler(f"Selbstreferenz in faktenfrische_aliases bei `{aktuell}`")
        aktuell = ziel
    return aktuell


def _alle_artikel_fuer_identitaet() -> list[dict]:
    """Bestand genau einmal lesen (Importfehler bleibt Werkzeugfehler)."""
    try:
        import faktenfrische as ff  # noqa: PLC0415 – Zyklus: ff importiert uns
        return ff.alle_artikel("alle")
    except Exception as exc:  # noqa: BLE001 – fail-closed
        raise LedgerFehler(f"Bestand nicht lesbar: {exc}") from exc


def bestand_identitaeten() -> tuple[dict[str, dict], dict[str, str]]:
    """(Fassungen, Alias-Karte) aus demselben Bestands-Schnappschuss.

    `faktenfrische_aliases` ist interne Herkunftsmetadaten, keine öffentliche
    Weiterleitung. Sie steht am aktuellen Artikel und überlebt dadurch auch ein
    Rollback des Reserve-Finishers. Kollisionen mit einem anderen lebenden Slug
    sind ein Werkzeugfehler: Eine Mehrdeutigkeit darf niemals einen Fachbefund
    auf den falschen Artikel projizieren.
    """
    seiten = _alle_artikel_fuer_identitaet()
    fassungen: dict[str, dict] = {}
    aliases: dict[str, str] = {}
    canonische_slugs = {str(a["slug"]) for a in seiten if a.get("slug")}
    for art in seiten:
        if not art.get("slug"):
            continue
        slug = str(art["slug"])
        # DREI LESARTEN EINER ENTSCHEIDUNG (07.11.2026, #1072):
        #   `text`      – Aussage-Hash der heutigen Regel (Vorgabe für NEUE
        #                 Entscheidungen, ohne Quellen und Betriebsflächen),
        #   `pruef`     – volle Prüffassung (Quellen, pin_*, alles),
        #   `text_alt`  – der nackte Body-Hash (Regel bis 09:00 UTC),
        #   `text_v1`   – Aussage-Hash der ersten Betriebsflächen-Regel
        #                 (`betrieb-v1`, 09:00–14:00 UTC).
        # Ohne die Vorläufer hätte die Verschärfung von `betrieb-v1` auf
        # `betrieb-v2` 13 am selben Tag getroffene Entscheidungen wieder
        # geöffnet – eine Regeländerung darf keine Redaktionsarbeit löschen.
        # Keiner der Vorläufer ist Vorgabe; sie zählen nur, solange sie zu
        # einer dokumentierten Entscheidung passen.
        fassungen[slug] = {
            "text": text_hash(art),                            # Vorgabe, neu
            "pruef": pruef_hash(art),                          # volle Prüffassung
            # Vorläufer (nie für neue Entscheidungen geschrieben):
            # Der Alt-Anker ist der UNVERÄNDERTE Body – in drei Rand-Formen,
            # weil je nach Speicherstand die Schlusszeile mitgezählt wurde.
            "text_alt": _text_hash_roh(art, "roh"),
            "text_alt_nackt": _text_hash_roh(art, "nackt"),
            "text_alt_ein": _text_hash_roh(art, "ein"),
            # Blindverfahren: der Alt-Anker mit NEUTRALISIERTEN Betriebs-
            # flächen. Nur so überlebt eine Entscheidung, wenn der Betrieb
            # später eine Route tauscht oder eine Bildzeile nachschreibt –
            # der Fall, der am 07.11.2026 acht Entscheidungen öffnete.
            "text_alt_blind": _text_hash_roh(art, "roh", blind=True),
            "text_alt_blind_nackt": _text_hash_roh(art, "nackt", blind=True),
            # Die erste Betriebsflächen-Regel vom 07.11.2026 (09–14 Uhr).
            "text_v1": _text_hash_nackt(art, "betrieb-v1"),
            "text_v1_rand": _text_hash_nackt(art, "betrieb-v1-rand"),
        }
        roh = _frontmatter(art).get("faktenfrische_aliases") or []
        if not isinstance(roh, list):
            raise LedgerFehler(f"{slug}: faktenfrische_aliases muss eine Liste sein")
        for alias in roh:
            if not isinstance(alias, str) or not alias.strip() or alias != alias.strip():
                raise LedgerFehler(f"{slug}: ungültiger Eintrag in faktenfrische_aliases")
            if alias == slug:
                raise LedgerFehler(f"{slug}: Selbstreferenz in faktenfrische_aliases")
            if alias in canonische_slugs:
                raise LedgerFehler(
                    f"{slug}: Alias `{alias}` kollidiert mit einem aktuellen Artikel")
            bisher = aliases.get(alias)
            if bisher is not None and bisher != slug:
                raise LedgerFehler(
                    f"Alias `{alias}` zeigt auf zwei Artikel (`{bisher}`, `{slug}`)")
            aliases[alias] = slug
    # Alle Ketten einmal validieren, auch wenn gerade kein offener Befund auf
    # ihnen liegt. So bleibt ein beschädigter Herkunftspfad nicht unsichtbar.
    for alias in aliases:
        canonical_slug(alias, aliases)
    return fassungen, aliases


def fassungen_aus_bestand() -> dict[str, dict]:
    """slug → {"text": Text-Hash, "pruef": Prüffassungs-Hash} für JEDE Seite."""
    return bestand_identitaeten()[0]


def slug_aliases_aus_bestand() -> dict[str, str]:
    """Alter Befund-Slug → aktueller Artikel-Slug (Herkunft, kein Redirect)."""
    return bestand_identitaeten()[1]


# Betriebsflächen im ROLLEN-BLINDVERFAHREN: Jede Zeile, die als Betriebsfläche
# erkannt wird, wird durch einen festen Platzhalter ersetzt (eine Zeile bleibt
# eine Zeile). Damit bleibt die STRUKTUR der Entscheidungsgrundlage erhalten,
# aber Inhalt und Anzahl der Links/CTAs sind austauschbar – genau das, was der
# Betrieb ändert (Route tauschen, Bildzeile neu, Disclaimer ergänzen).
BETRIEB_PLATZHALTER = "\x00betrieb\x00"


def _body_mit_blindtext(body: str, regel: str = "betrieb-v2") -> str:
    zeilen = []
    for zeile in str(body or "").split("\n"):
        ist = (betriebsflaeche(zeile) if regel == "betrieb-v2"
               else _betriebsflaeche_v1(zeile))
        zeilen.append(BETRIEB_PLATZHALTER if ist else zeile)
    return "\n".join(zeilen)


def _text_hash_roh(art: dict, rand: str = "roh", blind: bool = False) -> str:
    """Der Hash des UNVERÄNDERTEN Body (Alt-Anker) mit drei Rand-Formen.

    Das ist die Projektion von `text_hash` bis zum 07.11.2026, 09:00 UTC:
    dieselben vier Felder, derselbe Body – keine Betriebsflächen-Entfernung,
    keine Leerzeilen-Normalisierung. Sie ist der bewiesene Anker von 104
    Entscheidungen (07.11.2026: 131 von 131 lesbaren Entscheidungen
    reproduziert, wenn man den Rand mitzählt).

    `rand`:
      "roh"  – zeichengenau, wie gespeichert,
      "nackt"– ohne führende/schließende Leerzeilen,
      "ein"  – mit genau einer schließenden Zeile.

    Nur "nackt"/"ein" sind rand-tolerant; sie unterscheiden sich von "roh"
    ausschließlich in Leerzeilen. Genau deshalb darf eine angehängte
    Betriebsfläche (die am Dateiende Zeilen erzeugt) keine Entscheidung
    öffnen, und genau deshalb darf eine ECHTE Satzänderung sie öffnen.
    """
    fm = _frontmatter(art)
    body = (str(art.get("body", "")) if not blind
            else _body_mit_blindtext(art.get("body", "")))
    if rand == "nackt":
        body = body.strip("\n")
    elif rand == "ein":
        body = body.rstrip("\n") + "\n"
    elif rand != "roh":
        raise LedgerFehler(f"Unbekannte Rand-Form `{rand}`")
    material = {"title": fm.get("title", ""),
                "description": fm.get("description", ""),
                "kurzantwort": fm.get("kurzantwort", ""),
                "body": body}
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _text_hash_nackt(art: dict, projektion: str = "0") -> str:
    """Der Hash der früheren Regeln – reine Rückwärtsbindung, nie geschrieben.

    Vorläufer-Projektionen, nie für neue Entscheidungen geschrieben:
      * `"0"` (Vorgabe) – der ROHE Body, zeichengenau. Das war `text_hash`
        bis zum 07.11.2026, 09:00 UTC, und er reproduziert 131 von 131
        noch lesbaren Entscheidungen exakt (am 07.11.2026 nachgemessen).
        Er ist damit der bewiesene Alt-Anker – keine Schätzung.
      * `"roh-rand"` – derselbe Body mit normalisiertem Rand. Für den Fall,
        dass eine Betriebsfläche am Dateiende angehängt wurde und dadurch
        Randzeilen entstanden sind.
      * `"betrieb-v1"` – Aussageflächen ohne die erste, breite
        Betriebsflächen-Liste. An sie sind die 24 Entscheidungen gebunden,
        die am 07.11.2026 zwischen 09:00 und 14:00 UTC entstanden.
      * `"betrieb-v1-rand"`, `"betrieb-v2-rand"` – dieselben Regeln mit
        schließender Zeile, für die Beweisführung."""
    fm = _frontmatter(art)
    material = {
        "title": fm.get("title", ""),
        "description": fm.get("description", ""),
        "kurzantwort": fm.get("kurzantwort", ""),
        "body": (art.get("body", "") if projektion == "0"
                 else aussage_body(art.get("body", ""), projektion)),
    }
    payload = json.dumps(material, ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _normalisiere_fassungen(fassungen) -> dict[str, dict]:
    """Akzeptiert {slug: hash} (Tests) und {slug: {"text","pruef"}}."""
    if not fassungen:
        return {}
    ergebnis = {}
    for slug, wert in dict(fassungen).items():
        if isinstance(wert, str):
            # Ein einzelner Hash deckt alle Lesarten ab (Tests, Altaufrufer).
            ergebnis[str(slug)] = {"text": wert, "pruef": wert,
                                   "text_alt": wert, "text_alt_nackt": wert,
                                   "text_alt_ein": wert, "text_v1": wert,
                                   "text_v1_rand": wert}
        elif isinstance(wert, dict):
            ergebnis[str(slug)] = {"text": wert.get("text") or "",
                                   "pruef": wert.get("pruef") or "",
                                   "text_alt": (wert.get("text_alt")
                                                or wert.get("text") or ""),
                                   "text_v1": (wert.get("text_v1")
                                               or wert.get("text") or ""),
                                   "text_v1_rand": (wert.get("text_v1_rand")
                                                    or wert.get("text") or ""),
                                   "text_alt_nackt": (wert.get("text_alt_nackt")
                                                      or wert.get("text") or ""),
                                   "text_alt_ein": (wert.get("text_alt_ein")
                                                    or wert.get("text") or ""),
                                   "text_alt_blind": (wert.get("text_alt_blind")
                                                      or wert.get("text") or ""),
                                   "text_alt_blind_nackt": (
                                       wert.get("text_alt_blind_nackt")
                                       or wert.get("text") or "")}
    return ergebnis


# ----------------------------------------------------------------------
# Lesen
# ----------------------------------------------------------------------
def _json_object(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerFehler(f"{path.name} nicht lesbar: {exc}") from exc
    if not isinstance(data, dict):
        raise LedgerFehler(f"{path.name}: Objekt erwartet")
    return data


def eintraege_aus_queue(data: dict) -> list[dict]:
    """Neues Ledger plus einmalige Migration der bisherigen Lauf-Befunde."""
    result = []
    entries = data.get("fachbefunde", [])
    if not isinstance(entries, list):
        raise LedgerFehler("fachbefunde ist keine Liste")
    for entry in entries:
        if not isinstance(entry, dict) or not all(
                isinstance(entry.get(k), str) and entry[k].strip()
                for k in ("id", "slug", "fassung_sha256", "typ", "text")):
            raise LedgerFehler("Unvollständiger Ledger-Eintrag")
        result.append(dict(entry))
    runs = data.get("laeufe", [])
    if not isinstance(runs, list):
        raise LedgerFehler("laeufe ist keine Liste")
    for run in runs:
        if not isinstance(run, dict) or not isinstance(run.get("slug"), str):
            raise LedgerFehler("Unvollständiger Lauf")
        findings = run.get("befunde", [])
        if not isinstance(findings, list):
            raise LedgerFehler("Lauf-Befunde sind keine Liste")
        for finding in findings:
            if not isinstance(finding, dict) or not isinstance(finding.get("text"), str):
                raise LedgerFehler("Unvollständiger Fachbefund")
            slug = run["slug"]
            result.append({"id": befund_id(slug, finding), "slug": slug,
                           "fassung_sha256": run.get("fassung_sha256", LEGACY),
                           "typ": str(finding.get("typ", "befund")),
                           "text": finding["text"], "beleg": finding.get("beleg", ""),
                           "zuletzt_gesehen": data.get("erzeugt", "")})
    return result


def zusammenfuehren(alt: dict, neu: list[dict]) -> list[dict]:
    """Deduplizieren, niemals still schließen; neuester Belegstand gewinnt."""
    merged: dict[tuple[str, str], dict] = {}
    for entry in eintraege_aus_queue(alt) + list(neu):
        key = (entry["slug"], entry["id"])
        previous = merged.get(key, {})
        candidate = {**previous, **entry}
        for feld in ("fassung_sha256", "text_sha256"):
            alt_wert = previous.get(feld, "")
            neu_wert = entry.get(feld, "")
            if HASH_RE.fullmatch(str(alt_wert)) and not HASH_RE.fullmatch(str(neu_wert)):
                candidate[feld] = alt_wert
        merged[key] = candidate
    return [merged[key] for key in sorted(merged)]


def entscheidungen_laden(path: Path = ENTSCHEIDUNGEN) -> dict[tuple[str, str], dict]:
    """Menschliche Schließakte – Schema v1 und v2.

    v1 (bis 02.11.2026): `fassung_sha256` – bindet an die Prüffassung.
    v2 (ab 03.11.2026): `befund_fassung` + `geprueft_fassung` – bindet an den
    Ledger-Eintrag UND an den tatsächlich gelesenen Text.

    Folgeentscheidung (06.11.2026): Steht zu einem Schlüssel mehr als ein
    Eintrag da, gewinnt der ZULETZT geschriebene (Anfügeprotokoll). Eine
    frühere Entscheidung bleibt in der Datei lesbar und ist über
    `vorgaenger_geprueft_fassung` verkettet.
    """
    if not path.exists():
        return {}
    data = _laden_streng(path)
    entries = data.get("entscheidungen", []) if isinstance(data, dict) else None
    if not isinstance(entries, list):
        raise LedgerFehler("Entscheidungen müssen eine Liste sein")
    result = {}
    ketten: dict[tuple[str, str], list[dict]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not all(
                isinstance(entry.get(k), str) and entry[k].strip()
                for k in ("slug", "befund_id", "entschieden_von", "begruendung")):
            raise LedgerFehler("Entscheidung braucht Slug, Befund, Person und Begründung")
        if len(entry["begruendung"].strip()) < BEGRUENDUNG_MIN:
            raise LedgerFehler(
                f"Entscheidung für {entry.get('befund_id')} braucht eine "
                f"Begründung (≥ {BEGRUENDUNG_MIN} Zeichen) – 'ok' ist keine Prüfung")
        if "befund_fassung" in entry or "geprueft_fassung" in entry:
            if not all(isinstance(entry.get(k), str) and entry[k].strip()
                       for k in ("befund_fassung", "geprueft_fassung")):
                raise LedgerFehler("Entscheidung braucht `befund_fassung` UND "
                                   "`geprueft_fassung`")
            if not HASH_RE.fullmatch(entry["geprueft_fassung"]):
                raise LedgerFehler("`geprueft_fassung` muss ein echter SHA-256 sein")
            befund_fassung = entry["befund_fassung"]
        else:
            if not isinstance(entry.get("fassung_sha256"), str) or \
                    not HASH_RE.fullmatch(entry["fassung_sha256"]):
                raise LedgerFehler("Entscheidung braucht einen echten SHA-256 der "
                                   "geprüften Fassung")
            befund_fassung = entry["fassung_sha256"]
            entry = dict(entry, geprueft_fassung=entry["fassung_sha256"])
        key = (entry["slug"], entry["befund_id"])
        # Folgeentscheidung (06.11.2026): dieselbe Datei ist ein
        # Anfügeprotokoll. Steht ein Schlüssel mehrfach da, gewinnt der
        # ZULETZT geschriebene Eintrag (die gültige Entscheidung am heutigen
        # Text); die Vorgänger bleiben in der Datei als Kette lesbar.
        vorher = result.get(key)
        if vorher:
            # Kettenregel (08.11.2026, #1098): Die Vorgängerfassung muss eine
            # Fassung sein, die für DIESEN Befund schon einmal geprüft wurde.
            # Nicht verlangt wird, dass es der unmittelbar vorherige Eintrag
            # ist: Das Anfügeprotokoll ist in der Praxis nicht streng
            # chronologisch (zwei Personen bestätigen denselben Text, ein
            # Lauf zieht eine ältere Dokumentation nach). Die strengere
            # Nachbarschaftsregel erzeugte am 08.11.2026 einen Werkzeugfehler,
            # obwohl jede Entscheidung belegt und keine verloren war.
            # Was NICHT nachsichtig wird: ein Vorgänger, den es in der Kette
            # dieses Befunds nie gab – das bleibt ein Strukturfehler.
            vorgaenger = entry.get("vorgaenger_geprueft_fassung")
            dokumentiert = {d.get("geprueft_fassung") for d in ketten[key]}
            dokumentiert |= {d.get("vorgaenger_geprueft_fassung")
                             for d in ketten[key]}
            dokumentiert.discard(None)
            if (entry.get("folgeentscheidung") is not True or
                    vorgaenger not in dokumentiert):
                raise LedgerFehler(
                    f"Ungültige Folgeentscheidung für {key}: Vorgänger "
                    f"`{vorgaenger}` fehlt in der Kette "
                    f"({len(ketten[key])} frühere Entscheidung(en)) – "
                    "Struktur mit `--reparieren` prüfen.")
        elif entry.get("folgeentscheidung") or entry.get("vorgaenger_geprueft_fassung"):
            raise LedgerFehler(f"Folgeentscheidung ohne Vorgänger: {key}")
        result[key] = dict(entry, befund_fassung=befund_fassung)
        ketten.setdefault(key, []).append(entry)
    return result


def _entscheidung_schliesst(decision: dict | None, entry: dict,
                            fassungen: dict) -> bool:
    """Schließt diese Entscheidung GENAU diesen Eintrag an GENAU diesem Text?"""
    if not decision:
        return False
    # 1) Der Mensch muss den richtigen Ledger-Eintrag adressiert haben.
    ziele = {str(entry.get("fassung_sha256") or ""),
             str(entry.get("text_sha256") or "")}
    if str(decision.get("befund_fassung") or "") not in ziele:
        return False
    geprueft = str(decision.get("geprueft_fassung") or "")
    # 2) Der Text, den der Mensch gelesen hat, muss der aktuelle sein –
    #    IMMER, nicht nur bei einer Folgeentscheidung.
    #
    #    WARUM DAS GEÄNDERT WURDE (07.11.2026, #1072)
    #    ---------------------------------------------
    #    Hier stand `if befund_fassung != geprueft_fassung and aktuell:`.
    #    Damit wurde die Textprüfung genau dann übersprungen, wenn am
    #    UNVERÄNDERTEN Text entschieden wurde – dem häufigsten Fall. Folge:
    #    Die Entscheidung war für immer blind. Wurde der Satz danach wieder
    #    geändert (oder eine Zahl nachgeschoben), blieb der Befund
    #    geschlossen, und die Scorecard meldete F4 grün für einen Text, den
    #    niemand geprüft hatte. Der Zweig sollte nur die Quellenpflege
    #    abfedern – das leistet bereits `text` (ohne Quellen) bzw. `pruef`.
    #
    #    Ist die Seite nicht mehr lesbar, bleibt die dokumentierte
    #    Entscheidung gültig – sie betrifft eine Aussage, die es nicht mehr
    #    gibt (so bei der gelöschten Heizöl-Seite vom 05.11.2026).
    aktuell = fassungen.get(str(entry.get("slug")))
    if aktuell:
        # Drei Lesarten, eine Aussage (07.11.2026): `text` (neue Regel, ohne
        # Betriebsflächen), `text_alt` (dieselbe Aussage MIT den vom Betrieb
        # geschriebenen Zeilen – die Fassung, an die bis zum 07.11.2026
        # entschieden wurde) und `pruef` (volle Prüffassung).
        #
        # `text_alt` wird HEUTE aus der heutigen Datei gerechnet. Passt er zum
        # gelesenen Hash, ist bewiesen: Der Text ist seit der Entscheidung
        # unverändert – er trägt nur zusätzlich Betriebsflächen. Damit bleibt
        # eine dokumentierte Entscheidung gültig, ohne dass eine Regeländerung
        # Redaktionsarbeit löscht. Neue Entscheidungen binden immer an `text`
        # (siehe `entscheidung_anfuegen`), dieser Weg ist also reine
        # Rückwärtsbindung und kann sich nicht ausweiten.
        # Ein gespeicherter Hash kann mit oder ohne Schlusszeile gerechnet
        # worden sein – je nachdem, ob der Artikel damals auf "\n" endete und
        # welche Projektion der Lauf benutzte. Beides ist DIESELBE Aussage
        # (Markdown rendert `A\n` und `A` gleich, und ein angehängter
        # Betriebsblock erzeugt genau solche Schlusszeilen). Deshalb wird
        # jede Lesart in beiden Rand-Formen verglichen: byte-genau zuerst,
        # dann randneutral. Eine ECHTE Textänderung ändert den Hash in beiden
        # Formen – die Toleranz betrifft ausschließlich Leerzeilen am Rand.
        moeglich = set()
        for wert in (aktuell.get("text"), aktuell.get("pruef"),
                     aktuell.get("text_alt"), aktuell.get("text_alt_nackt"),
                     aktuell.get("text_alt_ein"),
                     aktuell.get("text_alt_blind"),
                     aktuell.get("text_alt_blind_nackt"),
                     aktuell.get("text_v1"), aktuell.get("text_v1_rand")):
            if not wert:
                continue
            moeglich.add(wert)
            # Randtoleranz: `A`, `A\n` und `A\n\n` sind dieselbe Aussage.
            for form in (wert, wert.rstrip("\n"), wert.rstrip("\n") + "\n"):
                moeglich.add(form)
        if geprueft not in moeglich:
            return False
    return bool(geprueft)


def offene_eintraege(entries: list[dict], decisions: dict,
                     fassungen: dict | None = None,
                     aliases: dict[str, str] | None = None) -> list[dict]:
    if fassungen is None:
        fassungen, geladene_aliases = bestand_identitaeten()
        if aliases is None:
            aliases = geladene_aliases
    fassungen = _normalisiere_fassungen(fassungen)
    aliases = aliases or {}
    result = []
    for roh in entries:
        ursprung = roh["slug"]
        aktuell = canonical_slug(ursprung, aliases)
        entry = (dict(roh) if aktuell == ursprung else
                 dict(roh, slug=aktuell, ursprungs_slug=ursprung))
        # Historische Entscheidungen bleiben unter ihrem alten Slug lesbar.
        # Neue Entscheidungen stehen am aktuellen Artikel. Die Befund-ID und
        # beide Fassungs-Hashes bleiben unverändert – ein Re-Dating ist weder
        # ein neuer Befund noch ein automatischer Abschluss.
        kandidaten = [decisions.get((ursprung, entry["id"]))]
        if aktuell != ursprung:
            kandidaten.append(decisions.get((aktuell, entry["id"])))
        if any(_entscheidung_schliesst(d, entry, fassungen)
               for d in kandidaten if d):
            continue
        result.append(entry)
    return result


def offene_befunde(queue_path: Path = QUEUE,
                   decisions_path: Path = ENTSCHEIDUNGEN,
                   fassungen: dict | None = None,
                   aliases: dict[str, str] | None = None) -> list[dict]:
    return offene_eintraege(zusammenfuehren(_json_object(queue_path), []),
                            entscheidungen_laden(decisions_path), fassungen,
                            aliases)


# ----------------------------------------------------------------------
# Zustand eines Befunds – entscheidbar oder nicht?
# ----------------------------------------------------------------------
def _datum(wert: str) -> dt.date | None:
    try:
        return dt.date.fromisoformat(str(wert)[:10])
    except (TypeError, ValueError):
        return None


def fassung_status(entry: dict, fassungen: dict, stichtag: dt.date) -> dict:
    """Wo steht dieser Befund gegenüber dem heutigen Text?"""
    stored = {str(entry.get("fassung_sha256") or ""),
              str(entry.get("text_sha256") or "")}
    aktuell = fassungen.get(str(entry.get("slug")))
    if not aktuell:
        return {"status": "seite-fehlt",
                "hinweis": "Seite ist im Bestand nicht lesbar – Entscheidung "
                           "würde eine gelöschte Seite bestätigen."}
    # Auch ein Alt-Befund ohne Hash braucht eine reale Seite als Schließweg.
    # Sonst ließe sich ein unlösbarer Fund durch Löschen des Fassungsankers
    # als angebliche Legacy-Erledigung verschwinden lassen.
    if not any(HASH_RE.fullmatch(w) for w in stored):
        return {"status": "ohne-fassung",
                "hinweis": "Kein gültiger Fassungs-Hash (Altbestand) – die "
                           "Entscheidung bindet an den heutigen Text."}
    if aktuell.get("text") in stored or aktuell.get("pruef") in stored:
        return {"status": "aktuell",
                "hinweis": "Der Text ist seit dem Befund unverändert."}
    alt = next((w for w in stored if HASH_RE.fullmatch(w)), "")
    return {"status": "ueberholt",
            "hinweis": "Der Text wurde nach dem Befund geändert "
                       f"(`{alt[:12]}…` → `{(aktuell.get('text') or '')[:12]}…`). "
                       "Bitte den HEUTIGEN Text prüfen und entscheiden.",
            "alte_fassung": alt,
            "heutige_fassung": aktuell.get("text") or ""}


def befunde_mit_status(queue_path: Path = QUEUE,
                       decisions_path: Path = ENTSCHEIDUNGEN,
                       fassungen: dict | None = None,
                       stichtag: dt.date | None = None,
                       aliases: dict[str, str] | None = None) -> list[dict]:
    """Offene Befunde, angereichert um Fassungsstand, Alter und Entscheidbarkeit."""
    stichtag = stichtag or dt.date.today()
    if fassungen is None:
        fassungen, geladene_aliases = bestand_identitaeten()
        if aliases is None:
            aliases = geladene_aliases
    fassungen = _normalisiere_fassungen(fassungen)
    result = []
    for entry in offene_befunde(queue_path, decisions_path, fassungen, aliases):
        stand = fassung_status(entry, fassungen, stichtag)
        gesehen = _datum(entry.get("zuletzt_gesehen", ""))
        alter = (stichtag - gesehen).days if gesehen else None
        result.append({
            **entry,
            "fassung_status": stand["status"],
            "fassung_hinweis": stand["hinweis"],
            "heutige_fassung": stand.get("heutige_fassung", ""),
            "alter_tage": alter,
            # Alle offenen Befunde sind entscheidbar – der Weg ist
            # `--entscheiden`, nicht das Editieren einer YAML-Datei.
            "entscheidbar": stand["status"] != "seite-fehlt",
            "nicht_entscheidbar_grund": (
                "" if stand["status"] != "seite-fehlt" else stand["hinweis"]),
        })
    result.sort(key=lambda e: (
        0 if e["fassung_status"] == "ueberholt" else 1,
        0 if e["fassung_status"] == "ohne-fassung" else 1,
        -(e["alter_tage"] if e["alter_tage"] is not None else -1),
        e["slug"], e["id"]))
    return result


# ----------------------------------------------------------------------
# Nachlese: Was im Dossier belegt ist, darf nicht außerhalb des Ledgers enden
# ----------------------------------------------------------------------
#  WARUM (Vorgang WF-8F6F / #984, 31.10.2026)
#  Ein Lauf schreibt das Dossier VOR seiner Bilanz. Brach er danach ab, lagen
#  die Befunde nur noch in `data/research/artikel/<slug>.json` – für die
#  Redaktion unsichtbar, für Publish-Gate und Scorecard (F4) nicht messbar,
#  für die Maschine „nichts gefunden“. Genau das passierte bei „Kostenloses
#  Girokonto ohne Gebühren finden“: fünf belegte Lücken, kein Ledger-Eintrag.
#
#  Die Nachlese schließt diese Lücke strukturell: Sie liest die Dossiers und
#  ergänzt ausschließlich, was fehlt. Sie schließt NIE einen Befund, erfindet
#  keine Fassung (ohne echten SHA-256 wird der Befund nicht übernommen) und
#  ist idempotent – zweimal ausgeführt ändert sie nichts.

def dossier_eintraege(dossier_dir: Path = DOSSIERS) -> tuple[list[dict], list[str]]:
    """(Ledger-Einträge, übersprungene Dateien/Gründe) aus den Dossiers."""
    eintraege: list[dict] = []
    hinweise: list[str] = []
    if not Path(dossier_dir).is_dir():
        return eintraege, [f"{dossier_dir} fehlt"]
    for pfad in sorted(Path(dossier_dir).glob("*.json")):
        try:
            data = json.loads(pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            hinweise.append(f"{pfad.name}: nicht lesbar ({exc})")
            continue
        if not isinstance(data, dict):
            hinweise.append(f"{pfad.name}: kein Objekt")
            continue
        findings = data.get("befunde") or []
        if not isinstance(findings, list) or not findings:
            continue
        fassung = data.get("fassung_sha256")
        slug = data.get("slug") or pfad.stem
        if not isinstance(fassung, str) or not HASH_RE.fullmatch(fassung):
            # Ohne echte Fassung wäre eine spätere Entscheidung nicht bindbar.
            hinweise.append(f"{pfad.name}: kein gültiger Fassungs-Hash – "
                            f"{len(findings)} Befund(e) nicht übernommen")
            continue
        for finding in findings:
            if not isinstance(finding, dict) or not isinstance(finding.get("text"), str) \
                    or not finding["text"].strip():
                hinweise.append(f"{pfad.name}: unvollständiger Befund")
                continue
            eintraege.append({
                "id": befund_id(str(slug), finding),
                "slug": str(slug),
                "fassung_sha256": fassung,
                # Der Text-Hash macht den Befund auch nach einer Korrektur
                # entscheidbar (#912); fehlt er im Alt-Dossier, bleibt die
                # Prüffassung die Zuordnung.
                "text_sha256": (data.get("text_sha256")
                                if isinstance(data.get("text_sha256"), str)
                                and HASH_RE.fullmatch(data["text_sha256"]) else ""),
                "typ": str(finding.get("typ") or "befund")[:20],
                "text": finding["text"].strip()[:400],
                "beleg": str(finding.get("beleg") or ""),
                "zuletzt_gesehen": str(data.get("erzeugt") or ""),
                "herkunft": "dossier-nachlese",
            })
    return eintraege, hinweise


def nachlese(dossier_dir: Path = DOSSIERS,
             queue_path: Path = QUEUE) -> dict:
    """Welche belegten Dossier-Befunde fehlen im Ledger? (rein lesend)"""
    vorhanden = {(e["slug"], e["id"]) for e in zusammenfuehren(
        _json_object(queue_path), [])}
    alle, hinweise = dossier_eintraege(dossier_dir)
    fehlend = [e for e in alle if (e["slug"], e["id"]) not in vorhanden]
    return {"dossiers": len(list(Path(dossier_dir).glob("*.json")))
            if Path(dossier_dir).is_dir() else 0,
            "befunde_im_dossier": len(alle),
            "fehlend": fehlend,
            "hinweise": hinweise}


def nachlese_anwenden(dossier_dir: Path = DOSSIERS,
                      queue_path: Path = QUEUE) -> dict:
    """Ergänzt fehlende Dossier-Befunde im Ledger – idempotent, nur ergänzend."""
    ergebnis = nachlese(dossier_dir, queue_path)
    if not ergebnis["fehlend"]:
        return ergebnis
    queue = _json_object(queue_path)
    queue["fachbefunde"] = zusammenfuehren(queue, ergebnis["fehlend"])
    queue["nachlese"] = {"zeit": _jetzt(), "ergaenzt": len(ergebnis["fehlend"]),
                         "quelle": "data/research/artikel"}
    tmp = Path(str(queue_path) + ".tmp")
    try:
        tmp.write_text(json.dumps(queue, ensure_ascii=False, indent=2),
                       encoding="utf-8")
        tmp.replace(queue_path)
    except OSError as exc:
        raise LedgerFehler(f"{Path(queue_path).name} nicht schreibbar: {exc}") from exc
    ergebnis["ergaenzt"] = len(ergebnis["fehlend"])
    return ergebnis


# ----------------------------------------------------------------------
# Entscheiden – der Schließpfad (statt Handarbeit an einer YAML-Datei)
# ----------------------------------------------------------------------
def _jetzt() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def _yaml_kopf(path: Path) -> str:
    """Kommentarkopf der Schließakte erhalten (menschlich kuratiert)."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return ("# Menschliche Schließakte zur Faktenfrische (#912).\n"
                "# Eine Entscheidung schließt nur genau diesen Befund an genau "
                "diesem Text.\n# Nie automatisch ergänzen. Nach einer Textänderung "
                "muss neu entschieden werden.\n")
    treffer = re.search(r"^entscheidungen:\s*$", text, re.MULTILINE)
    return text[:treffer.start()] if treffer else ""


def _yaml_schreiben(path: Path, daten: dict) -> None:
    kopf = _yaml_kopf(path)
    rumpf = yaml.safe_dump(daten, allow_unicode=True, sort_keys=False,
                           default_flow_style=False)
    tmp = Path(str(path) + ".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(kopf + rumpf, encoding="utf-8")
        tmp.replace(path)
    except OSError as exc:
        raise LedgerFehler(f"{path.name} nicht schreibbar: {exc}") from exc


def bindung_auf_feine_projektion(*, decisions_path: Path = ENTSCHEIDUNGEN,
                                 fassungen: dict | None = None,
                                 probe: bool = False) -> dict:
    """Einmalige Umbindung der Altentscheidungen auf die feine Projektion.

    WARUM (07.11.2026, #1072)
    -------------------------
    Bis zum 07.11.2026 band `text_hash` an den ROHEN Body – Betriebsflächen
    inklusive. Am 07.11.2026 nachgemessen: **104 von 104** noch lesbaren
    Entscheidungen trafen genau diesen Anker (`_text_hash_roh(art, "roh")`).
    Die Folge war der Defekt, der diesen Vorgang ausgelöst hat: Jede
    Maschinen-Schreibe (Link an der Weiterlesen-Zeile, Abbildungszeile,
    Disclaimer, CTA-Route) änderte den Hash und riss die Entscheidung auf –
    ohne dass sich ein Satz der Aussage geändert hatte.

    Diese Funktion schreibt die Bindung EINMAL um: von „roher Body" auf
    „Aussage ohne Betriebsflächen in der Fassung, die am Entscheidungstag
    galt" (`text_v1`). Sie ist beweisgestützt, nicht pauschal:

      * Sie bindet nur um, wenn der HEUTIGE Text den damals gelesenen
        zeichengenau reproduziert (`text_alt`-Familie). Hat sich seit der
        Entscheidung ein Satz geändert, bleibt der Befund offen und die
        Redaktion entscheidet neu – die Umbindung erfindet keine Prüfung.
      * Sie ändert `geprueft_fassung` NICHT. Der historische Beweis bleibt
        erhalten (`ursprungs_geprueft_fassung`), die neue Lesart steht
        daneben. Nichts wird überschrieben, nichts gelöscht.
      * Sie schließt nie einen Befund, den die Wache nicht schon als
        geschlossen führt: Nach der Umbindung muss die offene Menge
        unverändert sein, sonst bricht sie ab und schreibt nichts.
      * Sie ist idempotent: Ein zweiter Lauf findet nichts mehr zu tun.

    Ohne diese Umbindung stünde die Wahl zwischen zwei Übeln: entweder die
    feine Projektion aufgeben (dann öffnet jede Betriebsarbeit weiter
    Entscheidungen) oder 104 dokumentierte Entscheidungen entwerten (dann
    löscht eine Regeländerung Redaktionsarbeit). Beides ist ausgeschlossen.
    """
    if fassungen is None:
        fassungen, _ = bestand_identitaeten()
    fassungen = _normalisiere_fassungen(fassungen)
    daten = yaml.safe_load(decisions_path.read_text(encoding="utf-8")) \
        if decisions_path.exists() else {}
    eintraege = (daten or {}).get("entscheidungen") or []
    if not isinstance(eintraege, list):
        raise LedgerFehler("Entscheidungen müssen eine Liste sein")
    vorher_offen = {e["id"] for e in befunde_mit_status(
        decisions_path=decisions_path, fassungen=fassungen)}
    umgebunden, unveraendert, ohne_seite, unklar = [], 0, [], []
    for i, d in enumerate(eintraege):
        if not isinstance(d, dict) or not d.get("slug"):
            continue
        if d.get("projektion"):          # bereits umgebunden (idempotent)
            unveraendert += 1
            continue
        f = fassungen.get(str(d["slug"]))
        if not f:
            ohne_seite.append(str(d["slug"]))
            continue
        gelesen = str(d.get("geprueft_fassung") or "")
        # Nur umbinden, wenn der heutige Text den damals gelesenen exakt deckt.
        # Zwei Anker sind beweisbar:
        #   * `text_alt`-Familie – der rohe Body (Entscheidungen vor 09:00),
        #   * `text_v1`         – die erste Betriebsflächen-Regel (09–14 Uhr).
        # In beiden Fällen ist bewiesen: Der Satz ist unverändert, nur die
        # Messung hat sich geändert.
        # ZIEL IST IMMER DIE HEUTIGE, FEINE PROJEKTION (`text`). Die
        # Zwischenfassungen `text_v1`/`text_v1_rand` sind nur der BEWEIS, dass
        # der Text seit der Entscheidung unverändert ist – nicht das Ziel.
        # Wer auf `text_v1` stehen bliebe, hätte die breite Regel
        # zementiert: Am 07.11.2026 öffnete genau das 34 Befunde, sobald der
        # Marketer eine `/go/`-Route tauschte (CTA-Zeile noch als Aussage).
        if gelesen in {f.get("text_alt"), f.get("text_alt_nackt"),
                       f.get("text_alt_ein"), f.get("text_v1"),
                       f.get("text_v1_rand")}:
            ziel = f.get("text")
        else:
            unklar.append((str(d["slug"]), d.get("befund_id", ""), gelesen[:12]))
            continue
        if not ziel or ziel == gelesen:
            unveraendert += 1
            continue
        eintraege[i] = dict(d, geprueft_fassung=ziel,
                            ursprungs_geprueft_fassung=gelesen,
                            projektion="betrieb-v2",
                            umgebunden_am=dt.date.today().isoformat())
        umgebunden.append((str(d["slug"]), d.get("befund_id", "")))
    ergebnis = {"umgebunden": umgebunden, "unveraendert": unveraendert,
                "ohne_seite": ohne_seite, "unklar": unklar}
    if probe:
        ergebnis["probe"] = True
        return ergebnis
    if umgebunden:
        _yaml_schreiben(decisions_path, {"entscheidungen": eintraege})
        # Selbstkontrolle: Die Umbindung darf KEINEN Befund öffnen oder
        # schließen. Sie verschiebt nur die Projektion eines Beweises.
        nachher_offen = {e["id"] for e in befunde_mit_status(
            decisions_path=decisions_path, fassungen=fassungen)}
        if nachher_offen != vorher_offen:
            raise LedgerFehler(
                "Umbindung verändert die offene Menge – zurückgerollt "
                f"(vorher {len(vorher_offen)}, nachher {len(nachher_offen)})")
    return ergebnis


def entscheidung_anfuegen(befund_id_: str, von: str, begruendung: str,
                          beleg: str = "", *,
                          queue_path: Path = QUEUE,
                          decisions_path: Path = ENTSCHEIDUNGEN,
                          fassungen: dict | None = None,
                          heute: dt.date | None = None,
                          aliases: dict[str, str] | None = None) -> dict:
    """Eine menschliche Entscheidung dokumentieren, fassungsgebunden.

    Es gibt hier keinen Automatik-Pfad: Ohne Namen und Begründung schreibt
    diese Funktion nichts. Sie prüft die Zuordnung, bindet an den heutigen
    Text und macht den Befund damit schließbar – auch wenn der Text seit dem
    Befund korrigiert wurde (genau das ist der Normalfall einer Heilung).
    """
    von = (von or "").strip()
    begruendung = (begruendung or "").strip()
    if not von:
        raise LedgerFehler("`--von` fehlt – eine Entscheidung braucht eine Person")
    if len(begruendung) < BEGRUENDUNG_MIN:
        raise LedgerFehler(f"`--begruendung` braucht mindestens {BEGRUENDUNG_MIN} "
                           "Zeichen (was wurde geprüft, geändert oder verworfen?)")
    heute = heute or dt.date.today()
    if fassungen is None:
        fassungen, geladene_aliases = bestand_identitaeten()
        if aliases is None:
            aliases = geladene_aliases
    fassungen = _normalisiere_fassungen(fassungen)
    offen = offene_befunde(queue_path, decisions_path, fassungen, aliases)
    treffer = [e for e in offen if e["id"] == befund_id_]
    if not treffer:
        raise LedgerFehler(f"Kein offener Befund mit der ID `{befund_id_}` "
                           "(bereits entschieden, Tippfehler oder nicht im Ledger)")
    if len(treffer) > 1:
        raise LedgerFehler(f"Befund-ID `{befund_id_}` ist nicht eindeutig "
                           f"({len(treffer)} Seiten) – Ledger prüfen")
    entry = treffer[0]
    stand = fassung_status(entry, fassungen, heute)
    if stand["status"] == "seite-fehlt":
        raise LedgerFehler(f"{entry['slug']}: {stand['hinweis']}")
    aktuell = fassungen[entry["slug"]]["text"]
    decisions = entscheidungen_laden(decisions_path)
    alt = decisions.get((entry["slug"], befund_id_))
    if alt:
        if _entscheidung_schliesst(alt, entry, fassungen):
            # Idempotenz: die vorhandene Entscheidung deckt den heutigen
            # Text bereits ab – nichts doppelt zu schreiben.
            raise LedgerFehler("Für diesen Befund existiert bereits eine "
                               "Entscheidung (gebunden an den heutigen Text) – "
                               "nichts zu tun")
        # Folgeentscheidung: Der Text wurde nach der Entscheidung geändert –
        # genau der dokumentierte Heilungspfad. Die neue Entscheidung bindet
        # an den HEUTIGEN Text und verweist auf ihre Vorgänger.
        vorgaenger = alt.get("geprueft_fassung") or ""
    else:
        vorgaenger = ""
    decision = {
        "slug": entry["slug"],
        "befund_ursprung_slug": entry.get("ursprungs_slug", entry["slug"]),
        "befund_id": befund_id_,
        "befund_fassung": entry.get("fassung_sha256") or LEGACY,
        "geprueft_fassung": aktuell,
        "typ": entry.get("typ", ""),
        "beanstandung": entry.get("text", "")[:400],
        "beleg": beleg.strip(),
        "entschieden_von": von,
        "entschieden_am": heute.isoformat(),
        "fassung_wechsel": stand["status"] != "aktuell",
        "begruendung": begruendung,
    }
    if vorgaenger:
        # Folgeentscheidung: Kette statt Überschreiben – die Vorgänger-
        # Entscheidung bleibt in der Datei stehen und ist hier referenziert.
        decision["vorgaenger_geprueft_fassung"] = vorgaenger
        decision["folgeentscheidung"] = True
    daten = {"entscheidungen": []}
    if decisions_path.exists():
        roh = _laden_streng(decisions_path)
        if isinstance(roh, dict) and isinstance(roh.get("entscheidungen"), list):
            daten["entscheidungen"] = roh["entscheidungen"]
    daten["entscheidungen"].append(decision)
    _yaml_schreiben(decisions_path, daten)
    # Selbstkontrolle: Was wir geschrieben haben, muss den Befund schließen.
    if any(e["id"] == befund_id_ for e in
           offene_befunde(queue_path, decisions_path, fassungen, aliases)):
        raise LedgerFehler("Entscheidung geschrieben, aber der Befund bleibt "
                           "offen – Fassungsbindung prüfen")
    return decision


# ----------------------------------------------------------------------
# Wache: jeder offene Befund ist entscheidbar
# ----------------------------------------------------------------------
def wache(*, queue_path: Path = QUEUE, decisions_path: Path = ENTSCHEIDUNGEN,
          fassungen: dict | None = None, stichtag: dt.date | None = None,
          aliases: dict[str, str] | None = None) -> dict:
    """Strukturprüfung: kein Befund darf ohne Schließweg im Ledger liegen."""
    stichtag = stichtag or dt.date.today()
    befunde = befunde_mit_status(queue_path, decisions_path, fassungen, stichtag,
                                 aliases)
    nicht_entscheidbar = [e for e in befunde if not e["entscheidbar"]]
    ohne_begruendung = [e for e in befunde if not str(e.get("text") or "").strip()]
    return {
        "offen": len(befunde),
        "nicht_entscheidbar": len(nicht_entscheidbar),
        "ohne_beanstandung": len(ohne_begruendung),
        "seiten": len({e["slug"] for e in befunde}),
        "ueberholt": sum(1 for e in befunde if e["fassung_status"] == "ueberholt"),
        "ohne_fassung": sum(1 for e in befunde if e["fassung_status"] == "ohne-fassung"),
        "gruen": not nicht_entscheidbar and not ohne_begruendung,
        "funde": [f"{e['slug']} · {e['id']}: {e['nicht_entscheidbar_grund']}"
                  for e in nicht_entscheidbar],
    }


# ----------------------------------------------------------------------
# Selbsttest
# ----------------------------------------------------------------------
def selftest() -> int:
    finding = {"typ": "praezision", "text": "Unbelegte Preisangabe"}
    entry = {"id": befund_id("a", finding), "slug": "a",
             "fassung_sha256": body_hash("Fassung A"), **finding, "beleg": ""}
    assert zusammenfuehren({"fachbefunde": [entry]}, [entry]) == [entry]
    assert zusammenfuehren({"fachbefunde": [entry]}, []) == [entry]
    changed = dict(entry, fassung_sha256=body_hash("Fassung B"))
    assert zusammenfuehren({"fachbefunde": [entry]}, [changed]) == [changed]
    try:
        eintraege_aus_queue({"fachbefunde": [{}]})
    except LedgerFehler:
        pass
    else:
        raise AssertionError("Ungültiges Ledger wurde akzeptiert")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        queue_path = tmp / "queue.json"
        decisions = tmp / "decisions.yaml"
        fassung_a = body_hash("Text A")
        fassung_b = body_hash("Text B")
        eintrag = {"id": befund_id("seite", finding), "slug": "seite",
                   "fassung_sha256": fassung_a, "text_sha256": fassung_a,
                   **finding, "beleg": "", "zuletzt_gesehen": "2026-10-30 11:01 UTC"}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}), encoding="utf-8")
        fassungen = {"seite": {"text": fassung_a, "pruef": fassung_a}}

        # (a) Ohne Entscheidung offen, und zwar entscheidbar.
        offen = befunde_mit_status(queue_path, decisions, fassungen,
                                   dt.date(2026, 11, 3))
        assert len(offen) == 1 and offen[0]["entscheidbar"], offen
        assert offen[0]["alter_tage"] == 4, offen

        # (b) Ein geänderter TEXT macht den Befund nicht unschließbar (#912).
        fassungen_neu = {"seite": {"text": fassung_b, "pruef": fassung_b}}
        offen = befunde_mit_status(queue_path, decisions, fassungen_neu,
                                   dt.date(2026, 11, 3))
        assert offen[0]["fassung_status"] == "ueberholt", offen
        entscheidung_anfuegen(eintrag["id"], "Redaktion",
                              "Preisangabe im aktuellen Text entfernt und geprüft",
                              queue_path=queue_path, decisions_path=decisions,
                              fassungen=fassungen_neu, heute=dt.date(2026, 11, 3))
        assert offene_befunde(queue_path, decisions, fassungen_neu) == []
        text = decisions.read_text(encoding="utf-8")
        assert "befund_fassung" in text and "geprueft_fassung" in text
        assert fassung_b in text and fassung_a in text
        # (c) Maschinen-Quellenpflege (pruef ändert sich, Text nicht) öffnet NICHT.
        assert offene_befunde(queue_path, decisions,
                              {"seite": {"text": fassung_b, "pruef": "f" * 64}}) == []
        # (d) Eine spätere Textänderung öffnet die Entscheidung erneut.
        spaeter = {"seite": {"text": body_hash("Text C"), "pruef": body_hash("Text C")}}
        assert len(offene_befunde(queue_path, decisions, spaeter)) == 1

        # (e) Eine Entscheidung ohne Person/Begründung ist keine Entscheidung.
        for kwargs in ({"von": "", "begruendung": "x" * 40},
                       {"von": "Redaktion", "begruendung": "ok"}):
            try:
                entscheidung_anfuegen(eintrag["id"], queue_path=queue_path,
                                      decisions_path=tmp / "leer.yaml",
                                      fassungen=fassungen, **kwargs)
            except LedgerFehler:
                pass
            else:
                raise AssertionError("Leere Entscheidung wurde akzeptiert")
        assert not (tmp / "leer.yaml").exists(), "Datei trotz Fehler geschrieben"

        # (f) `legacy-unbekannt` ist entscheidbar (Altbestand ohne Hash).
        legacy = dict(eintrag, id=befund_id("alt", finding), slug="alt",
                      fassung_sha256=LEGACY, text_sha256="")
        queue_path.write_text(json.dumps({"fachbefunde": [legacy]}), encoding="utf-8")
        fassungen_alt = {"alt": {"text": fassung_a, "pruef": fassung_a}}
        assert befunde_mit_status(queue_path, tmp / "neu.yaml", fassungen_alt,
                                  dt.date(2026, 11, 3))[0]["fassung_status"] == "ohne-fassung"
        entscheidung_anfuegen(legacy["id"], "Redaktion",
                              "Altbefund am heutigen Text geprüft und erledigt",
                              queue_path=queue_path, decisions_path=tmp / "alt.yaml",
                              fassungen=fassungen_alt, heute=dt.date(2026, 11, 3))
        assert offene_befunde(queue_path, tmp / "alt.yaml", fassungen_alt) == []

        # (g) Fehlt die Seite, bleibt der Befund offen und heißt so.
        assert wache(queue_path=queue_path, decisions_path=tmp / "alt.yaml",
                     fassungen=fassungen_alt,
                     stichtag=dt.date(2026, 11, 3))["gruen"]
        einsam = {"andere-seite": {"text": fassung_a, "pruef": fassung_a}}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}), encoding="utf-8")
        stand = befunde_mit_status(queue_path, tmp / "ohne.yaml", einsam,
                                   dt.date(2026, 11, 3))
        assert stand and stand[0]["fassung_status"] == "seite-fehlt"
        assert not wache(queue_path=queue_path, decisions_path=tmp / "alt.yaml",
                         fassungen=einsam, stichtag=dt.date(2026, 11, 3))["gruen"]

        # (h) Nachlese: Dossier-Befunde erreichen das Ledger, ohne zu schließen.
        dossier_dir = tmp / "artikel"
        dossier_dir.mkdir()
        (dossier_dir / "seite.json").write_text(json.dumps({
            "slug": "seite", "erzeugt": "2026-10-31 10:34 UTC",
            "fassung_sha256": fassung_a, "befunde": [finding]}), encoding="utf-8")
        (dossier_dir / "ohne_hash.json").write_text(json.dumps({
            "slug": "alt", "befunde": [finding]}), encoding="utf-8")
        leer = tmp / "queue2.json"
        leer.write_text("{}", encoding="utf-8")
        ergebnis = nachlese_anwenden(dossier_dir, leer)
        assert ergebnis["ergaenzt"] == 1, ergebnis
        assert any("ohne_hash.json" in h for h in ergebnis["hinweise"]), ergebnis
        assert len(zusammenfuehren(_json_object(leer), [])) == 1
        assert nachlese_anwenden(dossier_dir, leer)["fehlend"] == []

    # WF-8F6F / #1073: Re-Dating ist keine Löschung und keine Entscheidung.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        queue_path = tmp / "queue.json"
        decisions = tmp / "decisions.yaml"
        alt_hash = body_hash("alter Befundtext")
        eintrag = {"id": befund_id("alt", finding), "slug": "alt",
                   "fassung_sha256": alt_hash, "text_sha256": alt_hash,
                   **finding, "beleg": "", "zuletzt_gesehen": "2026-11-03 12:18 UTC"}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}), encoding="utf-8")
        fassungen = {"neu": {"text": alt_hash, "pruef": alt_hash}}
        assert canonical_slug("alt", {"alt": "neu"}) == "neu"
        offen = befunde_mit_status(queue_path, decisions, fassungen,
                                   dt.date(2026, 11, 5), aliases={"alt": "neu"})
        assert len(offen) == 1 and offen[0]["slug"] == "neu"
        assert offen[0]["ursprungs_slug"] == "alt" and offen[0]["entscheidbar"]
        assert wache(queue_path=queue_path, decisions_path=decisions,
                     fassungen=fassungen, aliases={"alt": "neu"})["gruen"]
        assert offene_befunde(queue_path, decisions, {})[0]["slug"] == "alt"
        assert fassung_status(eintrag, {}, dt.date(2026, 11, 5))["status"] == "seite-fehlt"
        try:
            canonical_slug("alt", {"alt": "mitte", "mitte": "alt"})
        except LedgerFehler:
            pass
        else:
            raise AssertionError("Alias-Schleife wurde nicht fail-closed erkannt")

    # (i) Folgeentscheidung: Nach einer Entscheidung am geheilten Text bleibt
    #     der Befund an die GELESENE Aussage gebunden (v2-Regel) – ändert sich
    #     der Text erneut, öffnet sich der Befund, und die Folgeentscheidung
    #     schließt ihn wieder. Die Datei hält die Kette; die zuletzt
    #     geschriebene Entscheidung gewinnt.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        queue_path = tmp / "queue.json"
        decisions = tmp / "decisions.yaml"
        fassung_a = body_hash("Text A (Befundfassung)")
        fassung_b = body_hash("Text B (Heilung)")
        fassung_c = body_hash("Text C (erneute Änderung)")
        eintrag = {"id": befund_id("seite", finding), "slug": "seite",
                   "fassung_sha256": fassung_a, "text_sha256": fassung_a,
                   **finding, "beleg": "",
                   "zuletzt_gesehen": "2026-11-03 12:18 UTC"}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}),
                              encoding="utf-8")
        fassungen_b = {"seite": {"text": fassung_b, "pruef": fassung_b}}
        fassungen_c = {"seite": {"text": fassung_c, "pruef": fassung_c}}
        # Heilungs-Pfad: Der Text hatte sich seit dem Befund geändert – die
        # Entscheidung bindet an den tatsächlich gelesenen Text B.
        entscheidung_anfuegen(eintrag["id"], "Redaktion",
                              "Am geheilten Text B geprüft, erledigt",
                              queue_path=queue_path, decisions_path=decisions,
                              fassungen=fassungen_b, heute=dt.date(2026, 11, 3))
        assert offene_befunde(queue_path, decisions, fassungen_b) == []
        # Idempotenz: Solange die Entscheidung den gelesenen Text abdeckt,
        # wird nichts doppelt geschrieben.
        try:
            entscheidung_anfuegen(eintrag["id"], "Redaktion",
                                  "Doppelte Entscheidung darf nicht gehen",
                                  queue_path=queue_path, decisions_path=decisions,
                                  fassungen=fassungen_b, heute=dt.date(2026, 11, 4))
        except LedgerFehler:
            pass
        else:
            raise AssertionError("Doppelte Entscheidung am selben gelesenen Text akzeptiert")
        # Erneute Textänderung → Befund öffnet → Folgeentscheidung zulässig.
        assert len(offene_befunde(queue_path, decisions, fassungen_c)) == 1
        entscheidung_anfuegen(eintrag["id"], "Redaktion",
                              "Am Text C erneut geprüft, erledigt",
                              queue_path=queue_path, decisions_path=decisions,
                              fassungen=fassungen_c, heute=dt.date(2026, 11, 6))
        assert offene_befunde(queue_path, decisions, fassungen_c) == []
        daten = yaml.safe_load(decisions.read_text(encoding="utf-8"))
        eintraege = daten["entscheidungen"]
        assert len(eintraege) == 2, eintraege
        assert eintraege[1].get("folgeentscheidung") is True
        assert eintraege[1].get("vorgaenger_geprueft_fassung") == fassung_b
        # Die Kette bleibt vollständig lesbar – nichts wird überschrieben.
        assert {e["geprueft_fassung"] for e in eintraege} == {fassung_b, fassung_c}

    # (j) KEINE MASCHINE MACHT EINE ENTSCHEIDUNG BLIND (07.11.2026, #1072).
    #     Die frühere Fassung dieses Falls hieß „Stabiler Pfad“ und pinnte das
    #     Gegenteil fest: Wer am unveränderten Text entschied, dessen
    #     Entscheidung blieb danach bei JEDER Textänderung geschlossen –
    #     weil die Textprüfung nur bei `befund_fassung != geprueft_fassung`
    #     lief. Das war die Lücke, durch die die zurückgekehrte Heizöl-Seite
    #     am 07.11.2026 mit fünf F4-Befunden wieder live ging, ohne dass die
    #     Scorecard etwas merkte.
    #
    #     Was richtig ist: Quellen- und Betriebspflege schließen dir nicht
    #     den Befund, aber sie nehmen dir auch nicht das Schließen ab. Eine
    #     Aussageänderung öffnet SOFORT – und wird am geänderten Text neu
    #     entschieden (Folgeentscheidung), nicht ignoriert.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        queue_path = tmp / "queue.json"
        decisions = tmp / "decisions.yaml"
        fassung_a = body_hash("Text A (stabil)")
        eintrag = {"id": befund_id("stabil", finding), "slug": "stabil",
                   "fassung_sha256": fassung_a, "text_sha256": fassung_a,
                   **finding, "beleg": "",
                   "zuletzt_gesehen": "2026-11-03 12:18 UTC"}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}),
                              encoding="utf-8")
        fassungen_a = {"stabil": {"text": fassung_a, "pruef": fassung_a}}
        # Nur die QUELLEN ändern sich (pruef neu) – der Aussage-Hash bleibt.
        fassungen_quellen = {"stabil": {"text": fassung_a, "pruef": body_hash("Q neu")}}
        # Die AUSSAGE ändert sich (ein Zeichen genügt).
        fassungen_mut = {"stabil": {"text": body_hash("Text A\n"),
                                    "pruef": body_hash("Text A\n")}}
        entscheidung_anfuegen(eintrag["id"], "Redaktion",
                              "Am unveränderten Text A geprüft, erledigt",
                              queue_path=queue_path, decisions_path=decisions,
                              fassungen=fassungen_a, heute=dt.date(2026, 11, 3))
        # Quellenpflege des Laufs öffnet nichts: Sie ändert keine Aussage.
        assert offene_befunde(queue_path, decisions, fassungen_quellen) == [], \
            "Quellenpflege hat eine dokumentierte Entscheidung geöffnet"
        # Eine geänderte Aussage öffnet sie sehr wohl – auch wenn am
        # unveränderten Text entschieden wurde (das alte Loch).
        assert len(offene_befunde(queue_path, decisions, fassungen_mut)) == 1, \
            "Aussageänderung nach Gleichstands-Entscheidung blieb unsichtbar"
        # Und der geänderte Text ist entscheidbar: Folgeentscheidung statt
        # Dauerblinde. Danach ist wieder Ruhe.
        entscheidung_anfuegen(eintrag["id"], "Redaktion",
                              "Am geänderten Text A erneut geprüft, erledigt",
                              queue_path=queue_path, decisions_path=decisions,
                              fassungen=fassungen_mut, heute=dt.date(2026, 11, 6))
        assert offene_befunde(queue_path, decisions, fassungen_mut) == []
        # Die letzte Entscheidung bindet an den GEÄNDERTEN Text – kehrt der
        # Text auf die alte Fassung zurück, ist der Befund zu Recht wieder
        # offen (eine Entscheidung deckt genau die Aussage, die gelesen wurde).
        assert len(offene_befunde(queue_path, decisions, fassungen_quellen)) == 1

    # (l) DER BETRIEB SCHREIBT, DIE ENTSCHEIDUNG HÄLT (07.11.2026, #1072).
    #     Der Defekt, der den Vorgang ausgelöst hat: Jede Maschinen-Schreibe
    #     riss eine dokumentierte Entscheidung auf, obwohl kein Satz sich
    #     geändert hatte. Hier wird jede Schreibart einzeln geprüft – und die
    #     Gegenprobe, dass ein echter Satz sie sofort wieder öffnet.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        queue_path = tmp / "queue.json"
        decisions = tmp / "decisions.yaml"
        fm = 'title: "T"\ndescription: "D"\nkurzantwort: "K"\n'
        satz = "# H\n\nDer Abschlag bleibt eine Vorauszahlung.\n"
        betrieb = {
            "weiterlesen": "\n**Weiterlesen:** [A](../../posts/a/) · [B](../../posts/b/)\n",
            "abbildung": ("\n![Merkkarte](abbildung-merkkarte.svg)\n"
                          # Ableiter-Format (Herkunftsvermerk in der Zeile,
                          # seit 08.11.2026 das Erkennungsmerkmal).
                          "\n*Abbildung: Merkkarte zu \u201eT\u201c "
                          "(eigene Darstellung aus diesem Beitrag).*\n"),
            "transparenz": ("\n**Transparenz:** Dieser Artikel enthält "
                            "Affiliate-Links (Werbung).\n"),
            "disclaimer": ("\n*(Dieser Artikel enthält Affiliate-Links "
                           "(Werbung). Beim Abschluss über einen Link erhalten "
                           "wir eine Provision.)*\n"),
            "schnell_tipp": ("\n💡 **Schnell-Tipp von FranksFinanzcheck:** "
                             "Prüfe den Effektivpreis: "
                             "[**Tarife vergleichen**](/go/dsl/)\n"),
            "cta": ("\n👉 **Jetzt vergleichen und sparen:** "
                    "[**→ Internet & DSL vergleichen**](/go/dsl/)\n"),
            "spar_tipp": ("\n> 💶 **Spar-Tipp zwischendurch:** Faire Konditionen "
                          "gibt es online: [**Tagesgeld ansehen**](/go/tagesgeld/)\n"),
            "anhang": ("\n## Weiterrechnen und vertiefen\n\n"
                       "- **Rechner:** [Haushaltsbudget](/werkzeuge/haushaltsbudget/)\n"),
        }
        finding = {"typ": "luecke", "text": "Zahl ohne Beleg"}
        eintrag = {"id": befund_id("seite", finding), "slug": "seite",
                   "fassung_sha256": body_hash("Fassung A"),
                   "text_sha256": body_hash("Fassung A"), **finding,
                   "beleg": "", "zuletzt_gesehen": "2026-11-07 09:00 UTC"}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}),
                              encoding="utf-8")

        def fassung(body):
            artikel = {"fm": fm, "body": body}
            return {"text": text_hash(artikel), "pruef": pruef_hash(artikel),
                    "text_alt": _text_hash_roh(artikel, "roh"),
                    "text_alt_nackt": _text_hash_roh(artikel, "nackt"),
                    "text_alt_ein": _text_hash_roh(artikel, "ein"),
                    "text_v1": _text_hash_nackt(artikel, "betrieb-v1"),
                    "text_v1_rand": _text_hash_nackt(artikel, "betrieb-v1-rand")}

        basis = fassung(satz)
        entscheidung_anfuegen(eintrag["id"], "Redaktion",
                              "Abschlag-Satz am heutigen Text geprüft, erledigt",
                              queue_path=queue_path, decisions_path=decisions,
                              fassungen={"seite": basis},
                              heute=dt.date(2026, 11, 7))
        assert offene_befunde(queue_path, decisions, {"seite": basis}) == []
        for name, block in betrieb.items():
            nachher = fassung(satz + block)
            assert offene_befunde(queue_path, decisions,
                                  {"seite": nachher}) == [], \
                f"Betriebsfläche `{name}` hat die Entscheidung geöffnet"
        # ALLE Betriebsflächen zusammen – der Normalfall im Bestand.
        alle = fassung(satz + "".join(betrieb.values()))
        assert offene_befunde(queue_path, decisions, {"seite": alle}) == [], \
            "Gesamter Betriebsblock hat die Entscheidung geöffnet"
        # GEGENPROBE: ein echter Satz öffnet – sofort und unabhängig davon,
        # wie viel Betrieb daneben steht.
        echt = fassung(satz.replace("Vorauszahlung", "Abschlagszahlung")
                       + "".join(betrieb.values()))
        assert len(offene_befunde(queue_path, decisions, {"seite": echt})) == 1, \
            "Echter Satz hat die Entscheidung NICHT geöffnet"

        # (m) UMBIENDUNG: Altentscheidungen überleben die Projektionsänderung.
        #     Am 07.11.2026 banden 104 Entscheidungen an den ROHEN Body (mit
        #     Betriebsflächen). Ohne Umbindung hätte die feine Projektion sie
        #     entweder entwertet oder der Betrieb hätte sie weiter aufgerissen.
        alt_datei = tmp / "alt.yaml"
        alt_datei.write_text(yaml.safe_dump({"entscheidungen": [{
            "slug": "seite", "befund_id": eintrag["id"],
            "befund_fassung": eintrag["fassung_sha256"],
            "geprueft_fassung": basis["text_alt"],
            "entschieden_von": "Redaktion",
            "begruendung": "Am unveränderten Text entschieden (Altbindung)",
        }]}), encoding="utf-8")
        assert offene_befunde(queue_path, alt_datei, {"seite": basis}) == []
        # Der Betrieb schreibt – mit Altbindung reißt es auf. Genommen wird
        # der CTA-Block: Er steht NICHT in der ersten Betriebsflächen-Liste
        # (`betrieb-v1`) und ändert deshalb auch bei Altbindung den Hash.
        nachher = fassung(satz + betrieb["cta"])
        assert len(offene_befunde(queue_path, alt_datei,
                                  {"seite": nachher})) == 1, \
            "Altbindung war schon vor der Umbindung stabil – Testaufbau falsch"
        # … die Umbindung beweist: gleicher Text, neue Projektion.
        bericht = bindung_auf_feine_projektion(decisions_path=alt_datei,
                                               fassungen={"seite": basis})
        assert len(bericht["umgebunden"]) == 1, bericht
        assert offene_befunde(queue_path, alt_datei, {"seite": basis}) == []
        # Und der Betrieb schreibt jetzt, ohne zu öffnen.
        assert offene_befunde(queue_path, alt_datei, {"seite": nachher}) == [], \
            "Umbindung hat die Betriebstoleranz nicht hergestellt"
        # Der historische Beweis bleibt lesbar; nichts wurde überschrieben.
        d_neu = entscheidungen_laden(alt_datei)[("seite", eintrag["id"])]
        assert d_neu["ursprungs_geprueft_fassung"] == basis["text_alt"]
        assert d_neu["geprueft_fassung"] == basis["text"]
        assert d_neu["projektion"] == "betrieb-v2"
        # Idempotent: zweiter Lauf ändert nichts mehr.
        assert bindung_auf_feine_projektion(
            decisions_path=alt_datei, fassungen={"seite": basis})["umgebunden"] == []
        # Eine echte Änderung öffnet auch nach der Umbindung.
        assert len(offene_befunde(queue_path, alt_datei, {"seite": echt})) == 1

    # (k) BETRIEBSFLÄCHEN ÖFFNEN KEINE ENTSCHEIDUNG (07.11.2026, #1072).
    #     Der genaue Defekt: `gsc_abdeckung.py --verlinkung --heilen` hängt
    #     einen Link an die Weiterlesen-Zeile; seither standen 8 dokumentierte
    #     Entscheidungen wieder offen, ohne dass sich ein Satz geändert hatte.
    #     Hier wird beides geprüft: Betriebsfläche öffnet NICHT, echter Satz
    #     öffnet SOFORT – und eine bereits dokumentierte Entscheidung bleibt
    #     gültig (Rückwärtsbindung), sonst löschte die Regeländerung Arbeit.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        queue_path = tmp / "queue.json"
        decisions = tmp / "decisions.yaml"
        fm = 'title: "T"\ndescription: "D"\nkurzantwort: "K"\n'
        satz = "Der Abschlag bleibt eine Vorauszahlung.\n"
        betrieb = ("\n![Merkkarte](abbildung-merkkarte.svg)\n"
                   "\n*Abbildung: Merkkarte zu \u201eT\u201c "
                   "(eigene Darstellung aus diesem Beitrag).*\n"
                   "\n**Transparenz:** Dieser Artikel enthält Affiliate-Links "
                   "(Werbung).\n"
                   "\n**Weiterlesen:** [A](../../posts/a/) · [B](../../posts/b/)\n")
        anhang = ("\n## Weiterrechnen und vertiefen\n\n"
                  "- **Rechner:** [Haushaltsbudget](/werkzeuge/haushaltsbudget/)\n")
        vorher_art = {"fm": fm, "body": "# H\n\n" + satz}
        betrieb_art = {"fm": fm, "body": "# H\n\n" + satz + betrieb + anhang}
        # Die Aussage ist dieselbe – die Betriebsflächen ändern den Hash nicht.
        assert text_hash(vorher_art) == text_hash(betrieb_art), \
            "Betriebsfläche verändert den Aussage-Hash"
        # Eine echte Satzänderung ändert ihn sehr wohl.
        echt_art = {"fm": fm, "body": "# H\n\nDer Abschlag ist gesetzlich "
                                        "festgelegt.\n" + betrieb}
        assert text_hash(vorher_art) != text_hash(echt_art), \
            "Echter Satz öffnet die Entscheidung nicht"
        # Der Alt-Anker (`text_alt`) ist der Hash MIT Betriebsflächen – er
        # ändert sich also mit ihnen. Genau deshalb zählt er nur als
        # Rückwärtsbindung zu einer bereits dokumentierten Entscheidung und
        # wird nie für neue Entscheidungen geschrieben.
        assert _text_hash_nackt(vorher_art) != _text_hash_nackt(betrieb_art), \
            "text_alt ist der alte Anker und muss Betriebsflächen mitlesen"

        eintrag = {"id": befund_id("betrieb", finding), "slug": "betrieb",
                   "fassung_sha256": body_hash("Fassung A"),
                   "text_sha256": body_hash("Fassung A"), **finding,
                   "beleg": "", "zuletzt_gesehen": "2026-11-07 09:00 UTC"}
        queue_path.write_text(json.dumps({"fachbefunde": [eintrag]}),
                              encoding="utf-8")
        fassungen_vorher = {"betrieb": {"text": text_hash(vorher_art),
                                        "pruef": text_hash(vorher_art),
                                        "text_alt": _text_hash_nackt(vorher_art)}}
        entscheidung_anfuegen(eintrag["id"], "Redaktion",
                              "Abschlag-Satz am heutigen Text geprüft, erledigt",
                              queue_path=queue_path, decisions_path=decisions,
                              fassungen=fassungen_vorher, heute=dt.date(2026, 11, 7))
        assert offene_befunde(queue_path, decisions, fassungen_vorher) == []
        # Der Verlinkungs-Heiler schreibt seine Zeile …
        fassungen_betrieb = {"betrieb": {"text": text_hash(betrieb_art),
                                         "pruef": text_hash(betrieb_art),
                                         "text_alt": _text_hash_nackt(betrieb_art)}}
        assert offene_befunde(queue_path, decisions, fassungen_betrieb) == [], \
            "Betriebsfläche hat eine dokumentierte Entscheidung geöffnet"
        # … und selbst der alte Anker bleibt gültig (Rückwärtsbindung).
        fassungen_alt = {"betrieb": {"text": text_hash(betrieb_art),
                                     "pruef": text_hash(betrieb_art),
                                     "text_alt": text_hash(betrieb_art)}}
        assert offene_befunde(queue_path, decisions, fassungen_alt) == [], \
            "Betriebsfläche hat eine dokumentierte Entscheidung geöffnet (alt)"
        # Ein echter Satz öffnet sie – unabhängig von jeder Anker-Fassung.
        fassungen_echt = {"betrieb": {"text": text_hash(echt_art),
                                      "pruef": text_hash(echt_art),
                                      "text_alt": _text_hash_nackt(echt_art)}}
        assert len(offene_befunde(queue_path, decisions, fassungen_echt)) == 1, \
            "Echter Satz hat die Entscheidung nicht geöffnet"

    # (n) STRUKTUR: EIN EINTRAG, EINE ENTSCHEIDUNG (08.11.2026, #1098).
    #     Der Defekt: Ein Writer hängte Folgeentscheidungen IN einen fremden
    #     Listeneintrag. `safe_load` überschreibt dann still – die Akte sah
    #     aus wie ein Widerspruch („Vorgänger fehlt oder stimmt nicht"),
    #     obwohl jede Entscheidung belegt war. Drei Eigenschaften müssen
    #     dauerhaft gelten: laut scheitern, beweisbar heilen, nichts verlieren.
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        queue_path = tmp / "queue.json"
        decisions = tmp / "decisions.yaml"
        hash_a = body_hash("Text A")
        hash_b = body_hash("Text B")
        finding = {"typ": "luecke", "text": "Marktzahl ohne Beleg im Text"}
        queue_path.write_text(json.dumps({"fachbefunde": [{
            "id": befund_id("seite", finding), "slug": "seite",
            "fassung_sha256": hash_a, **finding, "beleg": "",
            "zuletzt_gesehen": "2026-11-08 09:00 UTC"}]}), encoding="utf-8")
        b_id = befund_id("seite", finding)
        # Ein strukturell kaputter Eintrag: der zweite Block hat keinen Slug,
        # keine ID – er wurde beim Anfügen aus einem Eintrag herausgerissen.
        kaputt = (
            "# Kopfkommentar bleibt erhalten.\n"
            "entscheidungen:\n"
            "- slug: seite\n"
            "  befund_id: %s\n"
            "  befund_fassung: %s\n"
            "  geprueft_fassung: %s\n"
            "  typ: luecke\n"
            "  beanstandung: Marktzahl ohne Beleg im Text\n"
            "  entschieden_von: Redaktion\n"
            "  entschieden_am: '2026-11-07'\n"
            "  begruendung: Erste Pruefung am unveraenderten Text\n"
            "  geprueft_fassung: %s\n"
            "  typ: luecke\n"
            "  beanstandung: Marktzahl ohne Beleg im Text\n"
            "  entschieden_von: Redaktion\n"
            "  entschieden_am: '2026-11-08'\n"
            "  begruendung: Zweite Pruefung nach redaktioneller Umformulierung\n"
            "  vorgaenger_geprueft_fassung: %s\n"
            "  folgeentscheidung: true\n"
        ) % (b_id, hash_a, hash_a, hash_b, hash_a)
        decisions.write_text(kaputt, encoding="utf-8")
        # 1) Die Wache scheitert LAUT – kein stiller Letzter-gewinnt-Leser.
        try:
            entscheidungen_laden(decisions)
        except LedgerFehler as exc:
            assert "Doppelter Schlüssel" in str(exc), exc
        else:  # pragma: no cover
            raise AssertionError("Doppelter Schlüssel wurde still überschrieben")
        assert not struktur_pruefen(decisions)["ok"]
        # 2) Der Heiler trennt die Blöcke und behält beide Entscheidungen.
        bericht = struktur_reparieren(decisions, queue_path=queue_path, apply=True)
        assert bericht["geschrieben"] and not bericht.get("fehler"), bericht
        assert bericht["getrennt"] == 1, bericht
        geladen = entscheidungen_laden(decisions)
        assert geladen[("seite", b_id)]["geprueft_fassung"] == hash_b
        assert geladen[("seite", b_id)]["vorgaenger_geprueft_fassung"] == hash_a
        strict_text = decisions.read_text(encoding="utf-8")
        assert "Kopfkommentar bleibt erhalten." in strict_text
        assert struktur_pruefen(decisions)["ok"]
        # 3) Idempotent: ein zweiter Lauf ändert nichts und schreibt nichts.
        assert struktur_reparieren(decisions, queue_path=queue_path,
                                   apply=True)["strukturfehler"] == 0
        # 4) Ein Block OHNE Person/Begründung ist kein Entscheid: Er wird
        #    ausgewiesen und verworfen – aber niemals stillschweigend.
        decisions.write_text(
            "entscheidungen:\n"
            "- slug: seite\n"
            "  befund_id: %s\n"
            "  befund_fassung: %s\n"
            "  geprueft_fassung: %s\n"
            "  typ: luecke\n"
            "  beanstandung: Marktzahl ohne Beleg im Text\n"
            "  entschieden_von: Redaktion\n"
            "  entschieden_am: '2026-11-07'\n"
            "  begruendung: Erste Pruefung am unveraenderten Text\n"
            "  geprueft_fassung: %s\n"
            "  typ: luecke\n"
            "  beanstandung: Marktzahl ohne Beleg im Text\n"
            % (b_id, hash_a, hash_a, hash_b), encoding="utf-8")
        bericht = struktur_reparieren(decisions, queue_path=queue_path, apply=True)
        assert bericht["geschrieben"], bericht
        assert len(bericht["verworfen"]) == 1, bericht
        assert bericht["verworfen"][0]["befund_id"] == b_id, bericht
        assert entscheidungen_laden(decisions)[("seite", b_id)][
            "geprueft_fassung"] == hash_a

    print("✅ Faktenfrische-Befundledger: zwei Hashes, fassungsgebundene "
          "Entscheidung, Textänderung bleibt schließbar, Folgeentscheidung "
          "mit Kette (#912), Quellenpflege öffnet "
          "nicht, Altbestand entscheidbar, Re-Dating-Aliasse (#1073), Nachlese, "
          "Betriebsflächen öffnen nicht (Weiterlesen/Abbildung/Transparenz/"
          "Werkzeug-Anhang, #1072), doppelte Schlüssel scheitern laut und "
          "sind beweisbar heilbar (#1098), fail-closed.")
    return 0


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selftest", action="store_true")
    parser.add_argument("--fassung", help="SHA-256 der Prüffassung einer Artikel-Datei")
    parser.add_argument("--text-hash", help="SHA-256 der Aussageflächen (ohne Quellen)")
    parser.add_argument("--entscheiden", metavar="BEFUND_ID",
                        help="menschliche Entscheidung zu genau diesem Befund")
    parser.add_argument("--von", help="wer entscheidet (Pflicht bei --entscheiden)")
    parser.add_argument("--begruendung",
                        help="was geprüft/geändert/verworfen wurde (Pflicht)")
    parser.add_argument("--beleg", default="", help="fakultativer Beleg (URL)")
    parser.add_argument("--nachlese", action="store_true",
                        help="Dossier-Befunde finden, die im Ledger fehlen")
    parser.add_argument("--apply", action="store_true",
                        help="mit --nachlese: fehlende Befunde ins Ledger ergänzen")
    parser.add_argument("--wache", action="store_true",
                        help="Exit 1, wenn ein offener Befund keinen Schließweg hat")
    parser.add_argument("--struktur-pruefen", action="store_true",
                        help="Exit 1, wenn die Akte doppelte Schlüssel trägt "
                             "(mehrere Entscheidungen in einem Listeneintrag)")
    parser.add_argument("--reparieren", action="store_true",
                        help="strukturzerlegte Einträge wieder zu eigenen "
                             "Entscheidungen machen (Selbstheilung der Akte)")
    parser.add_argument("--json", action="store_true", help="maschinenlesbar")
    args = parser.parse_args()
    try:
        if args.selftest:
            raise SystemExit(selftest())
        if args.nachlese:
            if args.apply:
                ergebnis = nachlese_anwenden()
                print(f"Nachlese: {ergebnis.get('ergaenzt', 0)} Befund(e) ergänzt "
                      f"aus {ergebnis['dossiers']} Dossier(s).")
            else:
                ergebnis = nachlese()
                print(f"Nachlese (Trockenlauf): {len(ergebnis['fehlend'])} von "
                      f"{ergebnis['befunde_im_dossier']} Dossier-Befund(en) fehlen "
                      "im Ledger.")
                for eintrag in ergebnis["fehlend"]:
                    print(f"  - {eintrag['slug']} · {eintrag['typ']}: "
                          f"{eintrag['text'][:110]}")
            for hinweis in ergebnis["hinweise"]:
                print(f"  Hinweis: {hinweis}")
            raise SystemExit(0)
        if args.fassung:
            import faktenfrische as ff
            article = ff.lade_artikel(args.fassung)
            if article is None:
                parser.error("Artikel nicht lesbar")
            print(pruef_hash(article))
            raise SystemExit(0)
        if args.text_hash:
            import faktenfrische as ff
            article = ff.lade_artikel(args.text_hash)
            if article is None:
                parser.error("Artikel nicht lesbar")
            print(text_hash(article))
            raise SystemExit(0)
        if args.entscheiden:
            if not args.von or not args.begruendung:
                parser.error("--entscheiden braucht --von und --begruendung")
            decision = entscheidung_anfuegen(args.entscheiden, args.von,
                                             args.begruendung, args.beleg)
            print(f"✅ {decision['slug']} · {decision['befund_id']} entschieden "
                  f"von {decision['entschieden_von']} "
                  f"({'Fassung hatte sich geändert' if decision['fassung_wechsel'] else 'Text unverändert'}).")
            raise SystemExit(0)
        if args.struktur_pruefen:
            stand = struktur_pruefen()
            if args.json:
                print(json.dumps(stand, ensure_ascii=False, indent=2))
            elif stand["ok"]:
                print(f"✅ Schließakte strukturell sauber "
                      f"({stand['eintraege']} Listeneinträge, keine doppelten "
                      "Schlüssel).")
            else:
                print(f"❌ {stand['strukturfehler']} Listeneintrag/-einträge "
                      "tragen mehrere Entscheidungen untereinander:")
                for fund in stand["funde"]:
                    print(f"   - {fund['befund']}")
                print("   Heilung: python3 scripts/faktenfrische_befund_ledger.py "
                      "--reparieren --apply")
            raise SystemExit(0 if stand["ok"] else 1)
        if args.reparieren:
            bericht = struktur_reparieren(apply=args.apply)
            if args.json:
                print(json.dumps(bericht, ensure_ascii=False, indent=2))
            else:
                if bericht.get("fehler"):
                    print(f"❌ {bericht['fehler']}")
                elif not bericht["strukturfehler"]:
                    print("✅ Schließakte strukturell sauber – nichts zu heilen.")
                elif bericht["geschrieben"]:
                    print(f"✅ {bericht['getrennt']} verlorene Folgeentscheidung(en) "
                          f"wieder als eigener Listeneintrag geführt "
                          f"({bericht['segmente']} Entscheidungen gesamt).")
                else:
                    print(f"Trockenlauf: {bericht['getrennt']} Block/Blöcke "
                          f"würden getrennt ({bericht['strukturfehler']} "
                          "betroffene Listeneinträge). Mit `--apply` schreiben.")
                    for eintrag in bericht["ergaenzt"]:
                        print(f"   - Zeile {eintrag['zeile']}: "
                              f"{eintrag['slug']} · {eintrag['befund_id']}")
            raise SystemExit(2 if bericht.get("fehler") else 0)
        if args.wache:
            stand = wache()
            if args.json:
                print(json.dumps(stand, ensure_ascii=False, indent=2))
            else:
                print(f"Offene Fachbefunde: {stand['offen']} auf {stand['seiten']} "
                      f"Seiten · überholte Fassung: {stand['ueberholt']} · "
                      f"ohne Fassung: {stand['ohne_fassung']}")
                if stand["gruen"]:
                    print("✅ Jeder offene Befund hat einen Schließweg "
                          "(eine menschliche Entscheidung am heutigen Text).")
                else:
                    print(f"❌ {stand['nicht_entscheidbar']} Befund(e) ohne "
                          "Schließweg:")
                    for fund in stand["funde"]:
                        print(f"   - {fund}")
            raise SystemExit(0 if stand["gruen"] else 1)
        if args.json:
            print(json.dumps(befunde_mit_status(), ensure_ascii=False, indent=2))
        else:
            for eintrag in befunde_mit_status():
                print(json.dumps(eintrag, ensure_ascii=False, indent=2))
    except LedgerFehler as exc:
        print(f"❌ {exc}", file=__import__("sys").stderr)
        raise SystemExit(2)
