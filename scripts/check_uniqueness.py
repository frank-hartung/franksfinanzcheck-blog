#!/usr/bin/env python3
"""
Einzigartigkeits-Audit für alle Blog-Artikel.

Prüft:
  1) Jeden Artikel gegen die Pinterest-Pin-Texte (Quelle: data/pinterest_plan.yaml)
  2) Jeden Artikel gegen alle anderen Artikel (interne Duplikate)
  3) SAME-DAY-TWINS: Titel-/Themen-Aehnlichkeit innerhalb desselben
     Kalendertags (Keyword-Kannibalisierung verhindern, 11.08.2026 –
     Anlass: Gas-Zwilling). --fix heilt: juengerer Zweitling → draft:true.

WICHTIG: Template-Bausteine (Werbekennzeichnung, Affiliate-CTA, FAQ-Rahmen)
werden VOR dem Vergleich entfernt – nur der echte Fließtext zählt.

  4) KANDIDATEN-COLLECTOR (Issue #714, 12.10.2026): `kandidaten_befunde()`
     ist DIESELBE Messung für das Publish-Gate (uniqueness_failures, U1/U2)
     und die Release-Scorecard (RD2-einzigartigkeit). Ein Bestandsbefund
     kann damit nie erst NACH einem grünen Gate auftauchen.

SABOTAGE-SCHUTZ: SELFTEST_SAMEDAY (8 eingefrorene Faelle inkl. echtem
Fall) + Collector-Korpus laufen vor jedem Audit; Abweichung → Exit 2.

Nutzung:
    python3 scripts/check_uniqueness.py            # alle Artikel prüfen
    python3 scripts/check_uniqueness.py --strict   # strengere Schwelle (5-Wort-Phrasen)
    python3 scripts/check_uniqueness.py --sameday --fix  # Geburts-Modus (Engine)
    python3 scripts/check_uniqueness.py --selftest       # nur Sabotage-Schutz (Selbsttest-Runner)
"""
import datetime
import os
import re
import sys
from itertools import combinations

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
from post_utils import build_state, list_post_paths
import template_boilerplate  # SSOT für deterministische Fazit-/FAQ-Bausteine (#251)
PINTEREST_PLAN = os.path.join(BLOG_DIR, "data", "pinterest_plan.yaml")

PHRASE_LEN = int(os.environ.get("PHRASE_LEN", "7"))
MAX_SIMILAR = int(os.environ.get("MAX_SIMILAR", "1"))


def norm(s):
    s = s.lower()
    s = re.sub(r"[äàáâ]", "ae", s)
    s = re.sub(r"[öòóô]", "oe", s)
    s = re.sub(r"[üùúû]", "ue", s)
    s = re.sub(r"ß", "ss", s)
    return re.sub(r"[^a-z0-9]+", " ", s).strip()


def clean_body(content):
    """Entfernt Frontmatter und alle Template-Bausteine → nur Fließtext."""
    parts = content.split("---", 2)
    body = parts[2] if len(parts) == 3 else content
    # Deterministische Fazit-/FAQ-Blöcke der Fazit-Schmiede ZENTRAL entfernen
    # (Issue #251): Template-Repetition ≠ Text-Dopplung – sonst kollidiert
    # jeder Artikel über den geteilten „Hebel“-Satz + Vergleichs-CTA mit 10+
    # unverwandten Artikeln und wird fälschlich als Duplikat geparkt.
    body = template_boilerplate.strip_generated_conclusions(body)
    # Marketing-/Affiliate-Bausteine aus DERSELBEN Quelle wie quality_score
    # (keine Drift mehr): Werbekennzeichnung, Schnell-/Spar-Tipp, CTA-Zeilen.
    body = template_boilerplate.strip_marketing_boilerplate(body)
    # Werbekennzeichnung in umbrochenen Varianten (mehrzeilig, Altbestand)
    body = re.sub(r"\*?_?Dieser Artikel enthält Affiliate-Links.*?(?:Mehrkosten|Mehrkosten\.)_?\*?", " ", body, flags=re.S)
    body = re.sub(r"\(Dieser Artikel enthält Affiliate-Links.*?\)", " ", body, flags=re.S)
    # UI-Callout-Blöcke & CTAs (Schnell-Tipp, Spar-Tipp, Weiterlesen, Conversion-Buttons)
    body = re.sub(r"💡\s*\*\*Schnell-Tipp.*?(?:\n\n|\Z)", " ", body, flags=re.S)
    body = re.sub(r">\s*💶\s*\*\*Spar-Tipp.*?(?:\n\n|\Z)", " ", body, flags=re.S)
    body = re.sub(r"👉.*?\)", " ", body, flags=re.S)
    body = re.sub(r"\*\*Weiterlesen:\*\*.*?(?:\n\n|\Z)", " ", body, flags=re.S)
    # Interne Verweise (internal_linker.py) sind NAVIGATION, kein Fließtext:
    # ihr Ankertext ist der Titel des Zielartikels. Zwei Ratgeber, die
    # denselben Pillar verlinken, teilen ihn sonst als „Duplikat“ – Issue #490.
    # Reihenfolge wichtig: VOR dem generischen Markdown-Link-Strip, der nur
    # den Ankertext behalten würde.
    body = template_boilerplate.strip_internal_link_anchors(body)
    # ROBUST: ALLE URLs entfernen (unabhängig vom CTA-Format)
    body = re.sub(r"https?://[^\s)\"']+", " ", body)
    body = re.sub(r"www\.[^\s)\"']+", " ", body)
    # Markdown-Links (ab hier: externe): nur den Ankertext behalten
    body = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", body)
    # FAQ-Intro-Standardsätze
    body = re.sub(r"## Häufige Fragen", " ", body)
    # Übrige Markdown-Syntax & HTML-Tags (<br>)
    body = re.sub(r"<[^>]+>", " ", body)
    body = re.sub(r"[*_#>`|~-]{1,}", " ", body)
    return body


def ngrams(text, n):
    words = re.findall(r"\w+", norm(text))
    return set(" ".join(words[i:i + n]) for i in range(len(words) - n + 1))


def audit_publication_state(content: str, now=None) -> tuple[bool, str]:
    """Spiegelt für die Befundklasse exakt, ob Hugo die Seite ausliefert.

    Diese kleine Naht ist absichtlich testbar: Ein `draft:`-Regex übersieht
    Zukunfts- und Ablaufdaten; `post_utils.build_state` ist die gemeinsame
    Hugo-Semantik der übrigen Publikationswachen.
    """
    return build_state(content, now=now)


def _slug(path):
    """Lesbarer Artikelname statt abgeschnittener Pfad.

    Der Report druckte `path[:32]` – bei absoluten Pfaden zeigte damit JEDES
    Paar „/home/user/franksfinanzcheck-blo" und der Fund war unbrauchbar: man
    sah, DASS etwas doppelt ist, aber nicht WELCHE Artikel. Bei einer Wache,
    deren Ausgabe der Redakteur abarbeitet, ist das der Unterschied zwischen
    Werkzeug und Attrappe.
    """
    base = os.path.splitext(os.path.basename(path))[0]
    return base if base and base != "index" else os.path.basename(os.path.dirname(path))


def load_pinterest_plan():
    pins = []
    if not os.path.exists(PINTEREST_PLAN):
        return pins
    current = None
    with open(PINTEREST_PLAN, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("- tag:"):
                current = {"tag": line.split(":", 1)[1].strip()}
                pins.append(current)
            elif current and ":" in line:
                key, val = line.split(":", 1)
                current[key.strip()] = val.strip().strip("\"'")
    return pins


def find_pin_for_topic(topic_title, pins):
    t = norm(topic_title)
    best, best_score = None, 0
    for p in pins:
        ref = norm((p.get("titel") or "") + " " + (p.get("pinwand") or ""))
        score = 0
        t_tokens = t.split()
        ref_tokens = ref.split()
        for i in range(min(len(t_tokens), 6)):
            if i < len(ref_tokens) and t_tokens[i] == ref_tokens[i]:
                score += 1
        if score > best_score:
            best, best_score = p, score
    return best if best_score >= 2 else None


# ============================================================
#  3) SAME-DAY-TWIN-RADAR (11.08.2026, Frank-Auftrag)
#  Anlass: Zwei Lebendiges zum selben Gas-Thema am selben Tag
#  (Keyword-Kannibalisierung!). Faengt Titel-/Themen-Aehnlichkeit
#  innerhalb desselben Kalendertags. --fix heilt selbst: der
#  juengere Zweitling wird draft:true gesetzt (Alias bewahrt sein
#  URL-Kapital), der aeltere ist kanonisch. Sabotage-Schutz via
#  SELFTEST unten (Exit 2 vor jeder Schreibaktion).
# ============================================================
STOP = set("""der die das ein eine einem einer einem einen so du dich dein deine
sich vor gegen mit und oder aber ist sind als zum zur im in am an auf aus wie
was wer wann warum sicherst schuetzt einfach erklaert leicht gemacht ab
vergleich vergleichen vergleichs vergleichstabelle
richtig pruefen pruefst prueft wirklich lohnt jetzt tipps tricks schritt
worauf ankommt achten clever""".split())
# Die zweite Zeile (12.10.2026, Issue #714) sind REDAKTIONSVOKABELN, keine
# Themenwörter: „richtig prüfen“, „worauf es ankommt“, „Schritt für Schritt“
# stehen in jeder dritten Ratgeber-Überschrift. Am 12.10. machten allein
# „kosten richtig pruefen“ aus einem DSL- und einem Handyvertrags-Artikel
# einen Titel-Zwilling (Jaccard 0,30) – obwohl beide verschiedene Suchanfragen
# bedienen. Der Zwillings-Radar soll Themen vergleichen, nicht Schablonen.
SAMEDAY_JACCARD = 0.25  # fuzzy-Jaccard (Komposita werden aufgesplittet)


def title_sig(title: str) -> set:
    # Generische Vergleichs-Vokabeln + Jahreszahlen (überall gleich) zählen nicht.
    return {t for t in norm(title).split()
            if t not in STOP and len(t) >= 3 and not re.fullmatch(r"20\d\d", t)}


def _tok_match(a: str, b: str) -> bool:
    """Gleich ODER Kompositum-Teildach: gaspreisgarantie ~ preisgarantie."""
    if a == b:
        return True
    return len(a) >= 6 and len(b) >= 6 and (a in b or b in a)


def same_day_twin(t_a: str, t_b: str) -> bool:
    a, b = title_sig(t_a), title_sig(t_b)
    if not a or not b:
        return False
    inter = max(sum(1 for x in a if any(_tok_match(x, y) for y in b)),
                sum(1 for y in b if any(_tok_match(x, y) for x in a)))
    return inter / (len(a) + len(b) - inter) >= SAMEDAY_JACCARD


# ============================================================
#  BEFUND-KLASSEN (Issue #490, 01.10.2026)
#  Ein Befund ist nur dann „kritisch", wenn er auch WIRKEN kann:
#  Duplicate Content und Keyword-Kannibalisierung entstehen zwischen
#  VERÖFFENTLICHTEN Seiten. Ein nicht auslieferbarer Artikel – Entwurf
#  (draft: true), Zukunfts-Post (buildFuture=false) oder abgelaufene Seite
#  (buildExpired=false) – steht in keinem aktuellen Index, hat keine
#  öffentliche URL und kann nichts kannibalisieren. Er ist eine
#  REDAKTIONELLE Aufgabe vor der Veröffentlichung, kein Bestandsschaden.
#  Beides in einen Topf zu werfen hatte zwei Folgen:
#    · Der Quartals-Report meldete 10 „kritische" Funde, von denen 3 nur
#      Entwürfe betrafen – der Bestand war nie so beschädigt, wie das
#      Ticket aussah (Alarm-Inflation, niemand arbeitet sie ab).
#    · Umgekehrt verschwand die Vorab-Dopplung in derselben Liste, statt als
#      eigene, VOR der Veröffentlichung fällige Aufgabe sichtbar zu sein.
#  Deshalb: eigene Klasse, eigener Abschnitt, eigene Zählung – und nur
#  live↔live bestimmt den Exit-Code des Bestands-Audits.
# ============================================================
KRITISCH_AB = 5          # ab so vielen geteilten Phrasen ist es Dopplung


def paar_klasse(overlap: int, a_draft: bool, b_draft: bool,
                max_sim: int = 1) -> str:
    """Klasse eines Artikelpaars: ok | unkritisch | entwurf | kritisch.

    overlap   Anzahl geteilter n-Gramme
    a/b_draft ob der jeweilige Artikel derzeit nicht auslieferbar ist
              (Entwurf, Zukunfts-Post oder abgelaufen)
    max_sim   Toleranz für Standard-Formulierungen
    """
    if overlap <= max_sim:
        return "ok"
    if overlap < KRITISCH_AB:
        return "unkritisch"
    return "entwurf" if (a_draft or b_draft) else "kritisch"


SELFTEST_SAMEDAY = [
    # DER echte Zwillings-Fall vom 11.08.2026:
    ("Gaspreisgarantie: So sicherst du dich gegen Preissprünge ab",
     "Preisgarantie Gas: So schützt du dich vor Preiserhöhungen", True),
    ("DSL-Wechselbonus sichern: So holst du dir das Extra",
     "DSL-Wechselbonus – das Extra ist größer als gedacht", True),
    ("Mietwagen buchen – die besten Tricks", "Mietwagen buchen im Urlaub", True),
    ("Tagesgeld-Zinsen 2026 im Vergleich", "Handytarife vergleichen 2026", False),
    ("50-30-20-Regel einfach erklärt", "Haushaltsbuch führen leicht gemacht", False),
    ("Kfz-Versicherung wechseln", "Handyvertrag kündigen", False),
    # Issue #714 (12.10.2026): dieselbe Titel-SCHABLONE ist kein Zwilling –
    # DSL und Mobilfunk bedienen verschiedene Suchanfragen.
    ("DSL-Anbieter wechseln: Kosten und Fristen richtig prüfen",
     "Handyvertrag kündigen: Frist und Kosten richtig prüfen", False),
    # … aber dasselbe THEMA bleibt einer, auch wenn die Schablone drumherum
    # steht (Gegenprobe: die Redaktionsvokabeln dürfen nichts verstecken).
    ("Stromfresser im Haushalt richtig prüfen",
     "Stromfresser finden: So prüfst du deinen Haushalt", True),
]


def run_selftest() -> list:
    fehler = []
    for i, (a, b, want) in enumerate(SELFTEST_SAMEDAY, 1):
        got = same_day_twin(a, b)
        if got != want:
            fehler.append(f"  Fall {i}: erwartet „{want}“, bekam „{got}“  ← {a[:40]!r} ↔ {b[:40]!r}")
    # Der Report-Teil: Slugs lesbar + geteilte Phrasen realmente bestimmbar.
    # Beides ist der Grund, warum der Report überhaupt abarbeitbar ist; ohne diese
    # zwei Fälle könnte die Wache wieder „/home/user/franksfinanzcheck-blo …“ als
    # Fund ausgeben und der Satz „1 Überlappung“ bliebe unbenannt.
    for pfad, erwartet in (("/repo/content/posts/2026-08-17-gasvergleich/index.md",
                             "2026-08-17-gasvergleich"),
                            ("/repo/content/posts/2026-08-17-gasvergleich.md",
                             "2026-08-17-gasvergleich"),
                            ("content/posts/2026-09-11-stromfresser/index.md",
                             "2026-09-11-stromfresser")):
        if _slug(pfad) != erwartet:
            fehler.append(f"  _slug({pfad!r}) = {_slug(pfad)!r}, erwartet {erwartet!r}")
    # Befund-Klassen (Issue #490): nur live↔live ist ein Bestandsschaden,
    # Entwürfe sind eine redaktionelle Aufgabe VOR der Veröffentlichung –
    # und echte Dopplung darf in keiner Konstellation verschwinden.
    for overlap, a_d, b_d, want in (
            (1, False, False, "ok"),          # Toleranz für Standardsätze
            (3, False, False, "unkritisch"),
            (5, False, False, "kritisch"),    # Schwelle ist inklusiv
            (26, False, False, "kritisch"),
            (9, True, False, "entwurf"),      # Entwurf gegen Live-Artikel
            (9, False, True, "entwurf"),
            (9, True, True, "entwurf"),
            (3, True, False, "unkritisch"),   # unter der Schwelle bleibt es
    ):
        got = paar_klasse(overlap, a_d, b_d)
        if got != want:
            fehler.append(f"  paar_klasse({overlap}, {a_d}, {b_d}) = {got!r}, "
                          f"erwartet {want!r}")
    # Interne Link-Ankertexte sind Navigation, kein Fließtext – sonst gilt
    # korrekte interne Verlinkung als Duplikat (3 von 10 Funden in #490).
    anker = ("Mehr dazu: [So findest du den richtigen DSL-Tarif für dein "
             "Zuhause](../../posts/2026-08-20-dsl-tarif/). Eigener Satz hier.")
    if "richtigen dsl tarif fuer dein zuhause" in norm(clean_body(anker)):
        fehler.append("  interner Link-Ankertext zählt noch als Fließtext "
                      "– zwei Artikel, die denselben Ratgeber verlinken, "
                      "werden fälschlich als Duplikat gemeldet")
    if "eigener satz hier" not in norm(clean_body(anker)):
        fehler.append("  Fließtext um einen internen Link wurde mitentfernt")

    a = "Heizung laufen lassen und Strom sparen jeden Monat mit diesen Tipps"
    b = "So Heizung laufen lassen und Strom sparen jeden Monat ohne Folgeschäden"
    gem = ngrams(a, PHRASE_LEN) & ngrams(b, PHRASE_LEN)
    if "heizung laufen lassen und strom sparen jeden" not in gem:
        fehler.append("  geteilte Sieben-Wort-Phrase wird nicht gefunden – der "
                      "Report könnte ‚Überlappung‘ wieder ohne Beleg drucken")
    fremd = ngrams("völlig andere Formulierung ohne Bezug", PHRASE_LEN) & ngrams(a, PHRASE_LEN)
    if fremd:
        fehler.append(f"  fremde Texte werden als überlappend gemeldet: {sorted(fremd)[:1]}")
    # Twin-Schutz (25.09.2026): etablierte/geteilte Zweitlinge nie auto-draften.
    heute = datetime.date.today().isoformat()
    schutz_faelle = [
        # (pfad, datum, geteilt, heilung_erlaubt?)
        ("content/posts/2026-09-25-neu/index.md", heute + "T08:00:00Z",
         set(), True),
        ("content/posts/2026-09-20-alt/index.md", "2026-09-20T08:00:00Z",
         set(), False),
        ("content/posts/2026-09-25-neu/index.md", heute + "T08:00:00Z",
         {"2026-09-25-neu"}, False),
        ("content/posts/2026-09-20-ohne-datum/index.md", "", set(), False),
    ]
    for pfad, dat, get, erlaubt in schutz_faelle:
        grund = twin_schutz_grund(pfad, dat, geteilt=get)
        if bool(grund) == erlaubt:
            fehler.append(f"  Twin-Schutz {pfad} [{dat[:10] or '?'}]: erwartet "
                          f"erlaubt={erlaubt}, Grund={grund!r}")
    # Kandidaten-Collector (#714): dieselbe Messung, die das Publish-Gate
    # liest – wenn sie hier nicht findet, darf kein Gate ihr vertrauen.
    fehler.extend(_collector_selftest())
    return fehler


def _geteilte_slugs():
    """Slugs, deren URL bereits Leser erreicht hat (Newsletter/Pinterest).

    Quellen (alle lesend, best-effort):
      data/newsletter_state.json  pending + versandene_artikel (direkte Slugs)
      data/pinterest_plan.yaml    /posts/<slug>/-URLs in url/blog_url
      data/pins_upload.csv        /posts/<slug>/-URLs in der Link-Spalte
    Lesefehler liefern eine leere Menge (Warnung im Log): Die Geburts-Tags-
    Regel in twin_schutz_grund() schützt unabhängig davon; diese Liste ist
    die zweite Hürde für Grenzfälle am Geburts-Tag selbst.
    """
    gefunden = set()
    try:
        import json
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        st = os.path.join(root, "data", "newsletter_state.json")
        if os.path.exists(st):
            d = json.load(open(st, encoding="utf-8"))
            for k in ("pending", "versandene_artikel"):
                gefunden.update(str(x) for x in (d.get(k) or []))
        for datei in ("data/pinterest_plan.yaml", "data/pins_upload.csv"):
            pfad = os.path.join(root, datei)
            if os.path.exists(pfad):
                txt = open(pfad, encoding="utf-8-sig").read()
                gefunden.update(
                    re.findall(r"/posts/([A-Za-z0-9][A-Za-z0-9\-]*)/", txt))
    except Exception as exc:  # noqa: BLE001 – best-effort, nie blockieren
        print(f"  ⚠ geteilte Slugs nicht lesbar ({exc}) – nur Geburts-Tags-Regel aktiv")
    return gefunden


def twin_schutz_grund(path: str, datum: str, geteilt=None) -> str:
    """Schutz vor Auto-Draft: "" = Heilung erlaubt, sonst der Grund.

    WARUM (Premium-Fix „404 nach Twin-Heilung“, 25.09.2026): Die Geburts-Wache
    draftete jeden jüngeren Zweitling – auch etablierte Live-Artikel, deren URL
    längst geteilt war (Newsletter, Pinterest, Google-Index). Jeder Auto-Draft
    eines etablierten Artikels ist ein 404 für echte Leser – schlimmer als der
    Twin selbst. Regeln:
      1. Geteilte URL (Newsletter/Pinterest) → NIEMALS Auto-Draft.
      2. Zweitling älter als heute (etabliert) → NIEMALS Auto-Draft.
    Erlaubt bleibt der Geburts-Fall: Zweitling mit Frontmatter-Datum = heute
    und (noch) nicht geteilt – dort ist die URL frisch und unverlinkt.
    Etablierte/geteilte Twins werden nur GEMELDET (Report, Exit 1 bei
    --sameday); die Zusammenführung ist redaktionell (Canonical/Redirect),
    kein Automatismus. `geteilt` ersetzt nur im Selbsttest die Dateisuche.
    """
    slug = os.path.basename(os.path.dirname(path))
    menge = _geteilte_slugs() if geteilt is None else set(geteilt)
    if slug in menge:
        return ("URL bereits geteilt (Newsletter/Pinterest) – redaktionell "
                "zusammenführen statt auto-draften")
    tag = (datum or "")[:10]
    if tag != datetime.date.today().isoformat():
        return (f"etabliert (Frontmatter-Datum {tag or 'unbekannt'}) – "
                "kein Auto-Draft nach dem Geburts-Tag")
    return ""


def heal_twin(path_younger: str) -> bool:
    """Setzt den juengeren Zweitling auf draft:true (stopft Publication) und
    markiert die Zurückhaltung als BEWUSST (park_state.hold).

    Warum das Markieren nötig ist: ohne Grund-Feld sähe der Post für die
    Kadenz-Wache aus wie ein verlegendes Re-Queue-Flag und würde beim nächsten
    Slot wieder promotingiert – das Qualitäts-Gate würde ihn erneut halten:
    Ping-Pong statt Zustand. Mit `cadence_grund` ist die Hemmung explizit und
    sichtbar (CADENCE-GATE-REPORT.md, Abschnitt Re-Queue-Integrität)."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import park_state
    except Exception:                      # Fallback: nur draft (altes Bild)
        with open(path_younger, encoding="utf-8") as f:
            src = f.read()
        m = re.search(r"(?m)^draft:\s*false\s*$", src)
        if not m:
            return False
        with open(path_younger, "w", encoding="utf-8") as f:
            f.write(src[:m.start()] + "draft: true" + src[m.end():])
        return True
    return park_state.hold(path_younger,
                           "duplikat (same-day-twin: älterer Titel ist "
                           "kanonisch, Zusammenführung nötig)")


# ============================================================
#  KANDIDATEN-COLLECTOR FÜR DAS PUBLISH-GATE (Issue #714, 12.10.2026)
#  ------------------------------------------------------------
#  Befund vom 12.10.2026: Zwei Reserve-Artikel (DSL-Anbieterwechsel und
#  Handyvertrag kündigen) gingen um 06:02 Uhr live, beide durch quality_score
#  und publish_gate STRICT – und das Tagesaudit um 13:35 Uhr meldete sie als
#  KRITISCH: 14 gleiche Sieben-Wort-Phrasen aus demselben § 56-TKG-Absatz.
#
#  Warum das Gate blind war: Es kannte diese Messung nicht. `duplikat_guard`
#  (D3/D4) misst GANZE Absätze mit difflib-Ratio ≥ 0,85 – zwei Absätze, die
#  „DSL-Vertrag“ gegen „Handyvertrag“ tauschen und einen Satz anhängen,
#  liegen darunter. `quality_score` wertet eine kritische Überlappung mit
#  −0,01 Gesamtpunkten (Gewicht 0,1 × 0,1). Beides zusammen heißt: Die
#  Bestandswache und das Veröffentlichungs-Gate hatten ZWEI Wahrheiten, und
#  die strengere kam erst nach dem Deploy zu Wort. Genau diese Bauart hat
#  dieses Repo schon in #583 (Faktenfrische) und #674 (Duplikate) gekostet:
#  grüner Publish-Pfad, roter Nachlauf, offenes Ticket, niemand zuständig.
#
#  Dieser Collector ist DIESELBE Messung (clean_body + ngrams + KRITISCH_AB +
#  same_day_twin), nur auf Kandidaten zugeschnitten:
#    U1-PHRASEN   Kandidat teilt ≥ KRITISCH_AB Sieben-Wort-Phrasen mit einem
#                 auslieferbaren Artikel oder einem Mit-Kandidaten.
#    U2-ZWILLING  Kandidat ist Titel-Zwilling eines auslieferbaren Artikels
#                 desselben Kalendertags (Slug-Datum). Zwischen zwei
#                 Kandidaten trägt nur der jüngere den Befund – wie bei der
#                 Heilung im Tagesaudit ist der ältere kanonisch.
#  Ein Fund hier ist damit NIE erst nach einem grünen Gate möglich: Das
#  Publish-Gate (uniqueness_failures), die Release-Scorecard
#  (RD2-einzigartigkeit) und dieses Tagesaudit lesen dieselbe Funktion.
# ============================================================
def lade_bestand(paths=None, now=None) -> dict:
    """{pfad: {slug, title, body, live, grund, date}} – eine Leseregel.

    `paths` ersetzt nur im Test die Dateisuche (synthetischer Korpus); `now`
    ist die Hugo-Uhr für Zukunfts-/Ablaufdaten (post_utils.build_state).
    """
    bestand = {}
    for path in (paths if paths is not None else list_post_paths()):
        try:
            with open(path, encoding="utf-8") as fh:
                content = fh.read()
        except OSError:
            continue
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        dm = re.search(r'(?m)^date:\s*["\']?([0-9T:\-]+)', content)
        visible, reason = audit_publication_state(content, now=now)
        bestand[path] = {
            "slug": _slug(path),
            "title": m.group(1) if m else _slug(path),
            "body": clean_body(content),
            "live": visible,
            "grund": "" if visible else reason,
            "date": dm.group(1) if dm else "",
        }
    return bestand


def _slug_tag(slug: str) -> str:
    m = re.match(r"(20\d\d-\d\d-\d\d)", slug or "")
    return m.group(1) if m else ""


def kandidaten_befunde(candidates, bestand=None, n: int = None,
                       max_sim: int = None) -> dict:
    """U1/U2-Befunde je Kandidaten-Slug: {slug: [detail, …]} (leer = sauber).

    candidates  Slugs (Ordnernamen), die ein Lauf gerade live schalten würde.
                Sie gelten als auslieferbar – unabhängig von ihrem aktuellen
                `draft`-Stand (das Gate misst die Fassung, die gleich live ist).
    bestand     Ergebnis von lade_bestand(); None = aus content/posts lesen.
    Gegenseite  nur auslieferbare Artikel und Mit-Kandidaten. Ein Entwurf im
                Vorrat kann nichts kannibalisieren – er wird hier NICHT gegen
                den Kandidaten gerechnet (sonst würde die Reserve sich selbst
                blockieren; der zweite Zwilling fällt, sobald der erste live
                ist – fail-closed am richtigen Zeitpunkt).
    """
    n = PHRASE_LEN if n is None else n
    max_sim = MAX_SIMILAR if max_sim is None else max_sim
    wanted = {str(s).strip() for s in candidates if str(s).strip()}
    if not wanted:
        return {}
    bestand = lade_bestand() if bestand is None else bestand
    by_slug = {info["slug"]: info for info in bestand.values()}
    gegenseite = {s: i for s, i in by_slug.items() if i["live"] or s in wanted}
    grams = {s: ngrams(i["body"], n) for s, i in gegenseite.items()}
    funde: dict[str, list[str]] = {}

    def merke(slug, text):
        if slug in wanted and text not in funde.setdefault(slug, []):
            funde[slug].append(text)

    for cand in sorted(wanted & set(by_slug)):
        for other, info in sorted(gegenseite.items()):
            if other == cand or (other in wanted and other < cand):
                continue  # jedes Paar genau einmal
            gemeinsam = grams[cand] & grams[other]
            klasse = paar_klasse(len(gemeinsam), False, False, max_sim)
            if klasse == "kritisch":
                beispiel = sorted(gemeinsam)[0]
                text = (f"U1-PHRASEN: {len(gemeinsam)} gleiche {n}-Wort-Phrasen "
                        f"mit {{anderer}} (z. B. „{beispiel}“) – ab {KRITISCH_AB} "
                        f"ist es Dopplung, Passage umschreiben")
                # Beide Seiten benannt – aber nur Kandidaten erhalten einen
                # Eintrag (merke() filtert; ein Live-Artikel ist hier Zeuge,
                # nicht Angeklagter – seine Prüfung ist das Tagesaudit).
                merke(cand, text.format(anderer=other))
                merke(other, text.format(anderer=cand))
            tag = _slug_tag(cand)
            if tag and tag == _slug_tag(other) and same_day_twin(
                    by_slug[cand]["title"], info["title"]):
                a, b = by_slug[cand], info
                text = (f"U2-ZWILLING: Titel-Zwilling am {tag} mit {{anderer}} "
                        f"(„{a['title'][:40]}“ ↔ „{b['title'][:40]}“) – "
                        "Thema zusammenführen oder Titel schärfen")
                if other in wanted:
                    # Zwei Kandidaten: der jüngere weicht, der ältere ist
                    # kanonisch (dieselbe Regel wie heal_twin im Tagesaudit).
                    juenger = max(cand, other,
                                  key=lambda s: (by_slug[s]["date"], s))
                    aelter = other if juenger == cand else cand
                    merke(juenger, text.format(anderer=aelter))
                else:
                    merke(cand, text.format(anderer=other))
    return funde


def _collector_selftest() -> list:
    """Eingefrorener Mini-Korpus: der Collector findet, was er finden muss,
    und schweigt, wo nichts ist. Läuft in run_selftest() – ein Gate, das
    diese Funktion liest, misst damit nachweislich (Sabotage-Schutz)."""
    fehler = []
    passage = ("Lies die Laufzeit in deinem Vertrag bevor du ein neues Angebot "
               "annimmst denn die erste feste Laufzeit darf höchstens vierundzwanzig "
               "Monate dauern und danach kannst du jederzeit mit einer Frist von "
               "einem Monat kündigen wenn der Vertrag still weiterläuft.")
    eigen = ("Ein Router steht selten am besten Platz; wer ihn vom Boden auf das "
             "Regal hebt, gewinnt oft mehr als ein neuer Tarif verspricht. Miss das "
             "WLAN in jedem Zimmer, bevor du den Vertrag anfasst.")
    frei = ("Der Notgroschen ist kein Sparziel, sondern ein Puffer gegen den "
            "Dienstag, an dem die Waschmaschine stirbt. Drei Nettogehälter sind "
            "eine Faustregel, kein Gesetz.")
    mobil = ("Eine offene Gerätezahlung läuft oft weiter, wenn der Mobilfunkdienst "
             "endet; wer die Raten nicht getrennt aufgelistet bekommt, zahlt am "
             "Ende für ein Telefon, das längst in der Schublade liegt.")

    def doc(slug, title, body, draft="false", date="2026-10-07T08:00:00Z"):
        return (f"---\ntitle: \"{title}\"\ndate: {date}\ndraft: {draft}\n---\n\n"
                f"{body}\n")

    korpus = {
        "/k/posts/2026-10-07-dsl/index.md":
            doc("2026-10-07-dsl", "DSL-Anbieter wechseln: was der Vertrag kostet",
                passage + "\n\n" + eigen),
        "/k/posts/2026-10-07-handy/index.md":
            doc("2026-10-07-handy", "Handyvertrag kündigen: Enddatum und Nachweis",
                passage + "\n\n" + mobil, date="2026-10-07T09:00:00Z"),
        "/k/posts/2026-10-07-notgroschen/index.md":
            doc("2026-10-07-notgroschen", "Notgroschen: wie viel Puffer reicht",
                frei + " Und ein zweiter, ganz eigener Gedanke steht hier."),
        "/k/posts/2026-10-07-notgroschen-zwilling/index.md":
            doc("2026-10-07-notgroschen-zwilling", "Notgroschen aufbauen: wie viel reicht",
                eigen, date="2026-10-07T10:00:00Z"),
        "/k/posts/2026-09-01-entwurf/index.md":
            doc("2026-09-01-entwurf", "Alter Entwurf", passage, draft="true"),
    }
    import tempfile
    with tempfile.TemporaryDirectory() as tmp:
        pfade = {}
        for virt, inhalt in korpus.items():
            p = os.path.join(tmp, *virt.strip("/").split("/")[1:])
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8") as fh:
                fh.write(inhalt)
            pfade[virt] = p
        bestand = lade_bestand(paths=list(pfade.values()),
                               now=datetime.datetime(2026, 10, 12,
                                                     tzinfo=datetime.timezone.utc))
    # Fall 1: Kandidat teilt die Passage mit einem Live-Artikel → U1, beide
    # Richtungen benannt, der Live-Artikel selbst bekommt keinen Eintrag.
    f1 = kandidaten_befunde(["2026-10-07-handy"], bestand)
    if not any(d.startswith("U1-PHRASEN") and "2026-10-07-dsl" in d
               for d in f1.get("2026-10-07-handy", [])):
        fehler.append("  Collector: geteilte § 56-Passage (live↔Kandidat) wird "
                      "nicht als U1 gemeldet")
    if "2026-10-07-dsl" in f1:
        fehler.append("  Collector: Nicht-Kandidat erhält einen Befund")
    # Fall 2: zwei Mit-Kandidaten teilen die Passage → beide tragen U1.
    f2 = kandidaten_befunde(["2026-10-07-dsl", "2026-10-07-handy"], bestand)
    if not all(any(d.startswith("U1-PHRASEN") for d in f2.get(s, []))
               for s in ("2026-10-07-dsl", "2026-10-07-handy")):
        fehler.append("  Collector: Kandidat↔Kandidat-Dopplung wird nicht beiden "
                      "zugeordnet")
    # Fall 3: Entwürfe im Vorrat zählen nicht als Gegenseite.
    f3 = kandidaten_befunde(["2026-10-07-notgroschen"], bestand)
    if any("2026-09-01-entwurf" in d for d in f3.get("2026-10-07-notgroschen", [])):
        fehler.append("  Collector: Entwurf (draft: true) wird als Gegenseite "
                      "gerechnet – die Reserve würde sich selbst blockieren")
    # Fall 4: Titel-Zwilling gegen Live-Artikel desselben Slug-Tags → U2 …
    f4 = kandidaten_befunde(["2026-10-07-notgroschen-zwilling"], bestand)
    if not any(d.startswith("U2-ZWILLING") and "2026-10-07-notgroschen" in d
               for d in f4.get("2026-10-07-notgroschen-zwilling", [])):
        fehler.append("  Collector: Same-Day-Titel-Zwilling gegen Live-Artikel "
                      "wird nicht als U2 gemeldet")
    # … und zwischen zwei Kandidaten trägt nur der jüngere den Befund.
    f5 = kandidaten_befunde(["2026-10-07-notgroschen",
                             "2026-10-07-notgroschen-zwilling"], bestand)
    if any(d.startswith("U2-ZWILLING") for d in f5.get("2026-10-07-notgroschen", [])):
        fehler.append("  Collector: der ÄLTERE Zwilling trägt den U2-Befund – "
                      "kanonisch ist der ältere, weichen muss der jüngere")
    if not any(d.startswith("U2-ZWILLING")
               for d in f5.get("2026-10-07-notgroschen-zwilling", [])):
        fehler.append("  Collector: der jüngere Kandidaten-Zwilling bleibt ohne U2")
    # Fall 5: eigenständiger Text bleibt ohne Phrasen-Befund (kein Scheinrot) –
    # der Notgroschen-Artikel teilt mit niemandem eine Passage.
    u1 = [d for d in f3.get("2026-10-07-notgroschen", []) if d.startswith("U1-")]
    if u1:
        fehler.append(f"  Collector: eigenständiger Text erhält U1-Befund: {u1[:1]}")
    f6 = kandidaten_befunde(["2026-10-07-dsl"], bestand)
    if any("mit 2026-10-07-notgroschen (" in d for d in f6.get("2026-10-07-dsl", [])):
        fehler.append("  Collector: unverwandte Artikel werden als Paar gemeldet")
    return fehler


def main():
    # SABOTAGE-SCHUTZ zuerst: Same-Day-Twin-Radar prueft sich selbst,
    # bevor irgendetwas gemeldet oder geheilt wird.
    fehler = run_selftest()
    if fehler:
        print("🛑 UNIQUENESS-SELBSTTEST FEHLGESCHLAGEN – Sabotage verhindert.")
        print("   Kein Audit, keine Heilung. Bitte same_day_twin() prüfen:")
        print("\n".join(fehler))
        sys.exit(2)
    print(f"✅ Selbsttest: {len(SELFTEST_SAMEDAY)} Twin-Faelle + Slug-/Gram-Report-Pinne stimmen.")
    # --selftest ist der Eintrittspunkt des Selbsttest-Runners
    # (scripts/selftest_runner.py, läuft im Qualitäts-Gate link-check.yml) und von
    # governance_contract C6: hier ends the run – der Selbsttest prüft die Logik,
    # nicht den Bestand. Sonst hinge ein grüner Selbsttest davon ab, ob gerade
    # jemand zwei Artikel ähnlich geschrieben hat (und ein roter von einem Fund,
    # für den es ein eigenes Gate gibt).
    if "--selftest" in sys.argv:
        return

    strict = "--strict" in sys.argv
    do_fix = "--fix" in sys.argv
    only_sameday = "--sameday" in sys.argv
    n = 5 if strict else PHRASE_LEN
    max_sim = 1 if strict else MAX_SIMILAR

    articles = {}
    titles = {}
    # Hugo liefert nicht nur `draft: true` nicht aus: Auch Zukunfts- und
    # abgelaufene Seiten haben unter buildDrafts/buildFuture/buildExpired=false
    # keine öffentliche URL. Für einen Bestandsbefund zählt deshalb exakt die
    # gemeinsame Hugo-Semantik aus post_utils.build_state(), nicht ein einzelner
    # Regex auf `draft:`. Solche Vorab-Fälle bleiben sichtbar, aber sie färben
    # den Live-Bestand nicht rot.
    not_live = {}
    dates = {}
    for path in list_post_paths():
        content = open(path, encoding="utf-8").read()
        m = re.search(r'^title:\s*["\']?(.+?)["\']?\s*$', content, re.M)
        titles[path] = m.group(1) if m else path
        articles[path] = clean_body(content)
        visible, reason = audit_publication_state(content)
        if not visible:
            not_live[path] = reason
        dm = re.search(r'(?m)^date:\s*["\']?([0-9T:\-]+)', content)
        dates[path] = dm.group(1) if dm else ""

    # 3) Same-Day-Twin-Radar (laeuft immer zuerst; bei --sameday: NUR dieser)
    print("=== 3) Same-Day-Zwillinge (Titel-/Themen-Aehnlichkeit, gleicher Tag) ===")
    same_crit = 0
    healed = []
    by_day = {}
    for fn in articles:
        base = os.path.basename(os.path.dirname(fn))
        dm = re.match(r"(20\d\d-\d\d-\d\d)", base)
        if dm and fn not in not_live:
            by_day.setdefault(dm.group(1), []).append(fn)
    for day, fns in sorted(by_day.items()):
        for a, b in combinations(sorted(fns), 2):
            if same_day_twin(titles[a], titles[b]):
                same_crit += 1
                print(f"  🚨 TWIN am {day}: {os.path.basename(os.path.dirname(a))}")
                print(f"               ↔ {os.path.basename(os.path.dirname(b))}")
                print(f"               ({titles[a][:44]!r} ↔ {titles[b][:44]!r})")
                if do_fix:
                    loser = max(a, b, key=lambda p: (dates.get(p, ""), p))
                    schutz = twin_schutz_grund(loser, dates.get(loser, ""))
                    if schutz:
                        print(f"               ⏸️ kein Auto-Draft für "
                              f"{os.path.basename(os.path.dirname(loser))}: {schutz}")
                    elif heal_twin(loser):
                        # Das Dokument ist gerade zu draft:true geworden und
                        # darf im anschließenden Bestandsvergleich nicht mehr
                        # als auslieferbar gelten.
                        not_live[loser] = "Draft (Same-Day-Twin-Heilung)"
                        healed.append(os.path.basename(os.path.dirname(loser)))
                        print(f"               🛠️ geheilt: Zweitling {os.path.basename(os.path.dirname(loser))} → draft:true")
    if not same_crit:
        print("  ✅ Keine Same-Day-Zwillinge")
    if only_sameday:
        if same_crit:
            print(f"\nErgebnis: {same_crit} Same-Day-Zwilling(e)" + (f", geheilt: {len(healed)}" if healed else ""))
            sys.exit(0 if healed else 1)
        print("\n✅ Geburtstag sauber – kein Zwilling.")
        sys.exit(0)

    print(f"Prüfe {len(articles)} Artikel (Phrasenlänge: {n}, max. ähnlich: {max_sim})\n")

    # 1) Gegen Pinterest-Pins
    pins = load_pinterest_plan()
    print("=== 1) Vergleich mit Pinterest-Pins ===")
    pin_problems = 0
    for fn in sorted(articles):
        pin = find_pin_for_topic(titles[fn], pins)
        if not pin:
            continue
        ref = norm((pin.get("titel") or "") + " " + (pin.get("beschreibung") or "") + " " + (pin.get("keywords") or ""))
        ref_words = ref.split()
        if len(ref_words) < n:
            continue
        ref_grams = set(" ".join(ref_words[i:i + n]) for i in range(len(ref_words) - n + 1))
        my_grams = ngrams(articles[fn], n)
        hits = len(my_grams & ref_grams)
        if hits > max_sim:
            pin_problems += 1
            print(f"  ⚠️ {_slug(fn)}: {hits} gleiche Phrasen mit Pin "
                  f"(Tag {pin.get('tag')})")
    if not pin_problems:
        print("  ✅ Alle Artikel einzigartig gegenüber den Pin-Texten")

    # 2) Interne Duplikate
    print("\n=== 2) Interne Duplikate (Artikel untereinander) ===")
    names = sorted(articles.keys())
    grams = {fn: ngrams(articles[fn], n) for fn in names}
    internal = 0
    critical = 0
    entwuerfe = []
    for a, b in combinations(names, 2):
        overlap = len(grams[a] & grams[b])
        klasse = paar_klasse(overlap, a in not_live, b in not_live, max_sim)
        if klasse == "ok":
            continue
        internal += 1
        if klasse == "kritisch":
            critical += 1
            print(f"  🚨 KRITISCH {_slug(a)} ↔ {_slug(b)}: {overlap} gleiche "
                  f"{n}-Wort-Phrasen")
            # Die betroffenen Passagen gleich mit ausgeben: „irgendwas ist
            # doppelt" wird in der Redaktion umformuliert, indem man rät –
            # mit den konkreten Ketten ist der Fix 10 Minuten Arbeit.
            for gram in sorted(grams[a] & grams[b])[:8]:
                print(f"       · {gram}")
        elif klasse == "entwurf":
            entwuerfe.append((a, b, overlap))
        else:
            print(f"  ℹ️ unkritisch {_slug(a)} ↔ {_slug(b)}: {overlap} Phrasen "
                  f"(Standard-Formulierungen)")
    if not internal:
        print("  ✅ Keine internen Duplikate")
    else:
        print(f"  (davon kritisch: {critical} – unter {KRITISCH_AB} Phrasen ist "
              f"normal und kein Duplicate Content)")

    # Nicht auslieferbare Seiten: eigene Liste, eigene Verantwortung (owner:
    # human). Entwürfe, Zukunfts- und abgelaufene Seiten stehen in keinem
    # aktuellen Index – der Bestand ist davon nicht beschädigt –, dürfen aber
    # nicht unverändert live gehen. Deshalb benannt, nicht stillgeschwiegen.
    print("\n=== 2b) Nicht veröffentlichte Artikel mit Überlappung ===")
    if not entwuerfe:
        print("  ✅ Kein nicht veröffentlichter Artikel überlappt kritisch mit dem Bestand")
    else:
        def mark(path):
            return _slug(path) + (f" [{not_live[path]}]" if path in not_live else " [live]")
        for a, b, overlap in entwuerfe:
            print(f"  📝 {mark(a)} ↔ {mark(b)}: {overlap} gleiche "
                  f"{n}-Wort-Phrasen")
            for gram in sorted(grams[a] & grams[b])[:5]:
                print(f"       · {gram}")
        print(f"  ({len(entwuerfe)} Nicht-Live-Paar(e) – vor der Veröffentlichung "
              f"umschreiben oder zusammenführen; blockiert den Bestand nicht)")

    same_open = same_crit - len(healed)
    print(f"\nErgebnis: Pin-Konflikte: {pin_problems} | Interne Überlappungen: "
          f"{internal} | Kritisch (live↔live): {critical} | Nicht-Live-Paare: "
          f"{len(entwuerfe)} | Same-Day-Twins: {same_crit} (geheilt: {len(healed)})")

    # Exit-Code für CI/Automatisierung:
    #   0 = alles ok (keine kritischen Probleme)
    #   1 = kritische Duplikate gefunden → Workflow bricht ab, nichts wird veröffentlicht
    #   2 = SELBSTTEST fehlgeschlagen (Sabotage-Schutz)
    if pin_problems > 0 or critical > 0 or same_open > 0:
        print("\n⚠️ KRITISCHE DUPLIKATE GEFUNDEN – Bitte Artikel überarbeiten, bevor veröffentlicht wird.")
        print("  Tipp: Betroffene Passagen umformulieren und Audit erneut ausführen.")
        sys.exit(1)
    else:
        print("\n✅ Audit bestanden – alle Artikel sind einzigartig.")


if __name__ == "__main__":
    main()
