#!/usr/bin/env python3
# ============================================================
#  VERGLEICHS-WACHE – Bewertungsraster, dauerhaft beweisbar
#  (Rollout 03.10.2026, Audit-Befund 8: „Monetarisierung und
#  Vertrauen müssen sauberer austariert werden – eine öffentliche
#  Seite ‚So entstehen unsere Vergleiche‘ mit konkretem
#  Bewertungsraster wäre deutlich stärker als ein allgemeiner
#  Unabhängigkeitshinweis. Dauerhaft auf Highend-Level.")
#
#  „DAUERHAFT" IST – wie bei der Offenlegungs-Wache – DER
#  EIGENTLICHE AUFTRAG. Eine Grundsatz-Seite, die niemand gegen
#  die Realität prüft, veraltet in die Unwahrheit: Eine neue
#  /go/-Route fehlt im Register, ein Einzelanbieter-Ziel steht
#  als „Marktvergleich" da, oder jemand „präzisiert" die
#  Provisions-Antwort. Deshalb prüft diese Wache das GEBAUTE
#  HTML gegen die drei Quellen des Rasters:
#    * data/vergleichsgrundsaetze.yaml        (kuratierte Antworten)
#    * data/affiliate_ziele.yaml              (Routen-Register, gebacken)
#    * data/beweise/vergleichsmethodik.yaml   (K.-o./Rangfolge, versioniert)
#
#  GEPRÜFTE VERTRÄGE
#    V1 SIEBEN ANTWORTEN  Die Seite existiert und trägt jede der
#                         sieben Audit-Fragen (data-ff-vg-frage
#                         v1…v7) genau einmal, plus Raster-Kopf.
#    V2 REGISTER-SYNC     Jede Route aus data/affiliate_ziele.yaml
#                         steht genau einmal im Routen-Register der
#                         Seite – und keine Route, die es im
#                         Zielregister nicht gibt (beide Richtungen).
#    V3 ZIELTYP-EHRLICHKEIT Routen mit Abweichung (einzelanbieter/
#                         portal/buendelung) tragen sichtbar den
#                         ehrlichen Zieltyp samt Erklärtext; ein
#                         Einzelangebot darf nie als „Marktvergleich"
#                         gerendert werden.
#    V4 PROVISION = NEIN  Die kuratierte Antwort MUSS wörtlich
#                         „nein" sein, sichtbar als „Nein." auf der
#                         Seite, mit mindestens drei benannten
#                         Durchsetzungs-Mechanismen. Jede Abweichung
#                         ist ein Befund – wer das ändern will, muss
#                         zuerst diese Wache ändern, öffentlich.
#    V5 METHODIK-SYNC     Jeder Themenbereich der versionierten
#                         Vergleichsmethodik erscheint im Raster
#                         zweimal (Rangfolge-Block UND Mindest-
#                         kriterien-Block) mit der korrekten
#                         Versionsnummer.
#    V6 DEAKTIVIERUNG     Mindestens vier konkrete Auslöser-/
#                         Reaktions-Paare kuratiert UND vollzählig
#                         gerendert – „Links werden geprüft" ohne
#                         Auslöser wäre wieder nur ein Satz.
#    V7 WEGWEISER         Footer (jede Seite), /transparenz/ und
#                         /methodik/ verlinken auf das Raster; das
#                         Raster verlinkt zurück auf beide.
#    V8 KURATIERUNG       SemVer-Version, ISO-Stand (nicht in der
#                         Zukunft), Changelog vorhanden, Ausschlüsse
#                         (>=3, je mit Grund) und Lücken-Regeln (>=3).
#
#  LEHRE AUS AI4 („stille Blindheit", 01./02.09.2026), identisch
#  zur Offenlegungs-Wache übernommen:
#    1. ATTRIBUT-TOLERANT: html.parser statt Regex – minifiziert
#       oder nicht, Attributreihenfolge egal.
#    2. DETEKTOR-FRISCHE: Vor jeder Prüfung wird der Fingerabdruck
#       (data-ff-vg) im LIVE-Shortcode-Template verlangt. Fehlt er,
#       ist das ein WERKZEUGFEHLER (Exit 2) – nicht „alles grün".
#    3. FAIL-CLOSED: Kein public/, keine Seite, kein Register →
#       Exit 2. Unbewiesen ist nicht bewiesen.
#
#  NUTZUNG
#    python3 scripts/vergleichsgrundsaetze_gate.py               # public/ prüfen
#    python3 scripts/vergleichsgrundsaetze_gate.py --public out  # anderes Build-Verzeichnis
#    python3 scripts/vergleichsgrundsaetze_gate.py --source-only # nur Quellen (ohne Build)
#    python3 scripts/vergleichsgrundsaetze_gate.py --selftest    # Sabotage-Proben (offline)
#    python3 scripts/vergleichsgrundsaetze_gate.py --history     # + Journalzeile
#
#  SSOT-Regel: Diese Wache LIEST die kuratierten Dateien und das
#  gebaute HTML, schreibt aber NIE an beiden.
# ============================================================
from __future__ import annotations

import argparse
import copy
import datetime as _dt
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover
    print("FEHLER: PyYAML fehlt (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

REPO = Path(__file__).resolve().parent.parent
GRUNDSAETZE = REPO / "data" / "vergleichsgrundsaetze.yaml"
ZIELREGISTER = REPO / "data" / "affiliate_ziele.yaml"
METHODIK = REPO / "data" / "beweise" / "vergleichsmethodik.yaml"
SHORTCODE = REPO / "layouts" / "shortcodes" / "vergleichsgrundsaetze.html"
HISTORY = REPO / "data" / "vergleichsgrundsaetze_history.jsonl"

SEITE_PFAD = "so-entstehen-unsere-vergleiche"
FRAGEN = ("v1", "v2", "v3", "v4", "v5", "v6", "v7")
ZIELTYP_LABELS = {
    "": "marktvergleich",
    "portal": "portal",
    "einzelanbieter": "einzelanbieter",
    "buendelung": "buendelung",
}
MIN_AUSSCHLUESSE = 3
MIN_TRIGGER = 4
MIN_DURCHSETZUNG = 3
MIN_LUECKEN = 3
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")


def _lade_yaml(pfad: Path):
    with pfad.open(encoding="utf-8") as fh:
        return yaml.safe_load(fh)


class _Werkzeugfehler(RuntimeError):
    """Fail-closed: Die Prüfung selbst ist nicht beweisfähig."""


# ------------------------------------------------------------
# HTML-Analyse: attribut-tolerant (html.parser, kein Regex)
# ------------------------------------------------------------
class _RasterParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.fragen: dict[str, int] = {}
        self.kopf = 0
        self.routen: list[tuple[str, str]] = []       # (route, zieltyp)
        self.bereiche: list[str] = []
        self.trigger = 0
        self.ausschluesse = 0
        self.provision_attr: str | None = None
        self.mversionen: list[str] = []
        self.links: set[str] = set()
        self._in_frage: list[str] = []                # Stack: offene Fragen-Container
        self._frage_tiefe: list[int] = []
        self._tiefe = 0
        self.fragen_text: dict[str, list[str]] = {f: [] for f in FRAGEN}
        self._in_mversion = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        self._tiefe += 1
        if "data-ff-vg" in a and a.get("data-ff-vg") == "kopf":
            self.kopf += 1
        frage = a.get("data-ff-vg-frage")
        if frage:
            self.fragen[frage] = self.fragen.get(frage, 0) + 1
            self._in_frage.append(frage)
            self._frage_tiefe.append(self._tiefe)
        if "data-ff-vg-route" in a:
            self.routen.append((a.get("data-ff-vg-route") or "",
                                a.get("data-ff-vg-zieltyp") or ""))
        if "data-ff-vg-bereich" in a:
            self.bereiche.append(a.get("data-ff-vg-bereich") or "")
        if "data-ff-vg-trigger" in a:
            self.trigger += 1
        if "data-ff-vg-ausschluss" in a:
            self.ausschluesse += 1
        if "data-ff-vg-provision" in a:
            self.provision_attr = (a.get("data-ff-vg-provision") or "").strip().lower()
        klasse = a.get("class") or ""
        if "ff-vg__mversion" in klasse.split():
            self._in_mversion = self._tiefe
        if tag == "a" and a.get("href"):
            self.links.add(a["href"])
        # Leere Elemente (void) schließen sofort wieder:
        if tag in ("br", "img", "hr", "meta", "link", "input", "source"):
            self._tiefe -= 1

    def handle_endtag(self, tag):
        if self._frage_tiefe and self._tiefe == self._frage_tiefe[-1]:
            self._frage_tiefe.pop()
            self._in_frage.pop()
        if self._in_mversion and self._tiefe == self._in_mversion:
            self._in_mversion = 0
        self._tiefe = max(0, self._tiefe - 1)

    def handle_data(self, data):
        if self._in_frage and data.strip():
            self.fragen_text[self._in_frage[-1]].append(data.strip())
        if self._in_mversion and data.strip():
            self.mversionen.append(data.strip())


def _parse(html: str) -> _RasterParser:
    p = _RasterParser()
    p.feed(html)
    return p


# ------------------------------------------------------------
# Quellen-Prüfung (V4-Daten, V6-Daten, V8) – kein Build nötig
# ------------------------------------------------------------
def pruefe_quellen(g: dict, fehler: list[str]) -> None:
    meta = (g or {}).get("meta") or {}
    if not SEMVER.match(str(meta.get("version") or "")):
        fehler.append(f"V8 meta.version {meta.get('version')!r} ist kein SemVer")
    stand = str(meta.get("stand") or "")[:10]
    try:
        d = _dt.date.fromisoformat(stand)
        if d > _dt.date.today():
            fehler.append(f"V8 meta.stand {stand} liegt in der Zukunft")
    except ValueError:
        fehler.append(f"V8 meta.stand {meta.get('stand')!r} ist kein ISO-Datum")
    if not (g.get("changelog") or []):
        fehler.append("V8 changelog fehlt oder ist leer")

    antwort = str(((g.get("provision") or {}).get("antwort") or "")).strip().lower()
    if antwort != "nein":
        fehler.append(f"V4 provision.antwort MUSS wörtlich 'nein' sein, ist {antwort!r} "
                      "– diese Zusage ist der Kern des Rasters")
    durchsetzung = (g.get("provision") or {}).get("durchsetzung") or []
    if len(durchsetzung) < MIN_DURCHSETZUNG:
        fehler.append(f"V4 provision.durchsetzung braucht >= {MIN_DURCHSETZUNG} Mechanismen "
                      f"(gefunden: {len(durchsetzung)})")

    ausschluesse = g.get("ausschluesse") or []
    if len(ausschluesse) < MIN_AUSSCHLUESSE:
        fehler.append(f"V8 ausschluesse braucht >= {MIN_AUSSCHLUESSE} Einträge "
                      f"(gefunden: {len(ausschluesse)})")
    for i, a in enumerate(ausschluesse):
        if not (a or {}).get("name") or not (a or {}).get("grund"):
            fehler.append(f"V8 ausschluesse[{i}]: 'name' und 'grund' sind Pflicht – "
                          "ein Ausschluss ohne Begründung ist keiner")

    ausloeser = (g.get("deaktivierung") or {}).get("ausloeser") or []
    if len(ausloeser) < MIN_TRIGGER:
        fehler.append(f"V6 deaktivierung.ausloeser braucht >= {MIN_TRIGGER} Paare "
                      f"(gefunden: {len(ausloeser)})")
    for i, t in enumerate(ausloeser):
        if not (t or {}).get("ausloeser") or not (t or {}).get("reaktion"):
            fehler.append(f"V6 deaktivierung.ausloeser[{i}]: 'ausloeser' und 'reaktion' sind Pflicht")

    if len(g.get("luecken") or []) < MIN_LUECKEN:
        fehler.append(f"V8 luecken braucht >= {MIN_LUECKEN} Regeln "
                      f"(gefunden: {len(g.get('luecken') or [])})")

    aufnahme = g.get("aufnahme") or {}
    if not aufnahme.get("modell") or len(aufnahme.get("kriterien") or []) < 3:
        fehler.append("V8 aufnahme braucht 'modell' und >= 3 'kriterien'")
    reihenfolge = g.get("reihenfolge") or {}
    if not reihenfolge.get("grundsatz") or not reihenfolge.get("portal_hinweis"):
        fehler.append("V8 reihenfolge braucht 'grundsatz' UND den ehrlichen 'portal_hinweis' "
                      "(Portal-Sortierung liegt nicht in unserer Hand)")


# ------------------------------------------------------------
# HTML-Prüfung (V1–V6 am gebauten Raster)
# ------------------------------------------------------------
def pruefe_raster_html(html: str, g: dict, ziele: dict, methodik: dict,
                       fehler: list[str]) -> None:
    p = _parse(html)

    # V1: sieben Antworten + Kopf
    if p.kopf != 1:
        fehler.append(f"V1 Raster-Kopf (data-ff-vg=\"kopf\") {p.kopf}x statt 1x")
    for f in FRAGEN:
        n = p.fragen.get(f, 0)
        if n != 1:
            fehler.append(f"V1 Antwort-Abschnitt {f} {n}x statt genau 1x auf der Seite")

    # V2: Routen-Register in beide Richtungen
    register = set((ziele or {}).keys())
    gerendert = [r for r, _ in p.routen]
    fehlend = sorted(register - set(gerendert))
    fremd = sorted(set(gerendert) - register)
    for r in fehlend:
        fehler.append(f"V2 Route '{r}' steht im Zielregister, fehlt aber im Raster – "
                      "eine Partnerroute ohne öffentliche Nennung ist eine stille Lücke")
    for r in fremd:
        fehler.append(f"V2 Raster nennt Route '{r}', die es im Zielregister nicht gibt")
    doppelt = {r for r in gerendert if gerendert.count(r) > 1}
    for r in sorted(doppelt):
        fehler.append(f"V2 Route '{r}' mehrfach im Raster")

    # V3: Zieltyp-Ehrlichkeit
    zieltyp_je_route = dict(p.routen)
    for key, z in (ziele or {}).items():
        erwartet = ZIELTYP_LABELS.get((z or {}).get("abweichung") or "", "marktvergleich")
        ist = zieltyp_je_route.get(key)
        if ist is not None and ist != erwartet:
            fehler.append(f"V3 Route '{key}': Zieltyp '{ist}' gerendert, Register sagt "
                          f"'{erwartet}' – ein Einzelangebot darf nie als Marktvergleich erscheinen")
        abweichung_ziel = (z or {}).get("abweichung_ziel") or ""
        if abweichung_ziel and abweichung_ziel not in html:
            fehler.append(f"V3 Route '{key}': der Erklärtext zur Abweichung "
                          f"({abweichung_ziel[:40]}…) fehlt im Raster")

    # V4: Provision sichtbar „Nein"
    if p.provision_attr != "nein":
        fehler.append(f"V4 data-ff-vg-provision ist {p.provision_attr!r} statt 'nein'")
    v4_text = " ".join(p.fragen_text.get("v4") or [])
    if "Nein." not in v4_text:
        fehler.append("V4 Die sichtbare Antwort 'Nein.' fehlt im Provisions-Abschnitt")
    if "Provision" not in v4_text:
        fehler.append("V4 Der Provisions-Abschnitt nennt das Wort 'Provision' nicht")

    # V5: Methodik-Sync (jeder Bereich 2x: Rangfolge + Mindestkriterien)
    bereiche = [(b or {}).get("id") for b in (methodik or {}).get("bereiche") or []]
    for b in bereiche:
        n = p.bereiche.count(b)
        if n != 2:
            fehler.append(f"V5 Themenbereich '{b}' {n}x im Raster statt 2x "
                          "(Rangfolge-Block + Mindestkriterien-Block)")
    for b in set(p.bereiche) - set(bereiche):
        fehler.append(f"V5 Raster nennt Themenbereich '{b}', den die Methodik nicht kennt")
    for b in (methodik or {}).get("bereiche") or []:
        label = f"Methodik v{b.get('version')}"
        if label not in p.mversionen:
            fehler.append(f"V5 Versionsnummer '{label}' für Bereich '{b.get('id')}' "
                          "fehlt im Raster – Versionssprünge müssen hier sichtbar werden")

    # V6: Deaktivierungs-Auslöser vollzählig gerendert
    soll = len((g.get("deaktivierung") or {}).get("ausloeser") or [])
    if p.trigger != soll:
        fehler.append(f"V6 {p.trigger} Auslöser gerendert, {soll} kuratiert")
    if p.ausschluesse != len(g.get("ausschluesse") or []):
        fehler.append(f"V2 {p.ausschluesse} Ausschlüsse gerendert, "
                      f"{len(g.get('ausschluesse') or [])} kuratiert")


def pruefe_wegweiser(raster_html: str, transparenz_html: str, methodik_html: str,
                     irgendeine_seite_html: str, fehler: list[str]) -> None:
    """V7: Hin- und Rückwege zwischen Raster, Transparenz, Methodik, Footer."""
    ziel = f"/{SEITE_PFAD}/"

    def _verlinkt(html: str) -> bool:
        return ziel in {h if h.startswith("/") else "/" + h.split("://", 1)[-1].split("/", 1)[-1]
                        for h in _parse(html).links} or ziel in html

    if not _verlinkt(transparenz_html):
        fehler.append("V7 /transparenz/ verlinkt nicht auf das Bewertungsraster")
    if not _verlinkt(methodik_html):
        fehler.append("V7 /methodik/ verlinkt nicht auf das Bewertungsraster")
    if not _verlinkt(irgendeine_seite_html):
        fehler.append("V7 Footer-Link auf das Bewertungsraster fehlt (Stichprobe Startseite)")
    raster_links = _parse(raster_html).links
    for rueckweg in ("/transparenz/", "/methodik/"):
        if not any(rueckweg in h for h in raster_links):
            fehler.append(f"V7 Raster verlinkt nicht zurück auf {rueckweg}")


# ------------------------------------------------------------
# Detektor-Frische + Lauf
# ------------------------------------------------------------
def pruefe_detektor_frische() -> None:
    if not SHORTCODE.exists():
        raise _Werkzeugfehler(f"Shortcode fehlt: {SHORTCODE}")
    quelle = SHORTCODE.read_text(encoding="utf-8")
    for anker in ("data-ff-vg-frage", "data-ff-vg-route", "data-ff-vg-zieltyp",
                  "data-ff-vg-bereich", "data-ff-vg-trigger", "data-ff-vg-provision"):
        if anker not in quelle:
            raise _Werkzeugfehler(
                f"Detektor-Fingerabdruck '{anker}' fehlt im Live-Template "
                f"{SHORTCODE.name} – die Wache wäre blind (AI4-Lektion). "
                "Template und Wache nur gemeinsam ändern.")


def lauf(public: Path, source_only: bool, history: bool) -> int:
    pruefe_detektor_frische()
    for pfad in (GRUNDSAETZE, ZIELREGISTER, METHODIK):
        if not pfad.exists():
            raise _Werkzeugfehler(f"Quelle fehlt: {pfad}")
    g = _lade_yaml(GRUNDSAETZE)
    ziele = (_lade_yaml(ZIELREGISTER) or {}).get("ziele") or {}
    methodik = _lade_yaml(METHODIK)
    if not ziele:
        raise _Werkzeugfehler("Zielregister ist leer – unbewiesen ist nicht bewiesen")

    fehler: list[str] = []
    pruefe_quellen(g, fehler)

    if not source_only:
        seite = public / SEITE_PFAD / "index.html"
        if not seite.exists():
            raise _Werkzeugfehler(
                f"Gebaute Raster-Seite fehlt: {seite} – vorher `hugo` laufen lassen "
                "oder --source-only verwenden")
        raster_html = seite.read_text(encoding="utf-8")
        pruefe_raster_html(raster_html, g, ziele, methodik, fehler)

        pfade = {
            "transparenz": public / "transparenz" / "index.html",
            "methodik": public / "methodik" / "index.html",
            "startseite": public / "index.html",
        }
        for name, pf in pfade.items():
            if not pf.exists():
                raise _Werkzeugfehler(f"Gebaute Seite fehlt: {pf} ({name})")
        pruefe_wegweiser(raster_html,
                         pfade["transparenz"].read_text(encoding="utf-8"),
                         pfade["methodik"].read_text(encoding="utf-8"),
                         pfade["startseite"].read_text(encoding="utf-8"),
                         fehler)

    print("VERGLEICHS-WACHE – Bewertungsraster (V1–V8)")
    print(f"  Raster v{(g.get('meta') or {}).get('version')} · "
          f"{len(ziele)} Routen · "
          f"{len((methodik or {}).get('bereiche') or [])} Methodik-Bereiche · "
          f"{len(g.get('ausschluesse') or [])} Ausschlüsse · "
          f"{len((g.get('deaktivierung') or {}).get('ausloeser') or [])} Deaktivierungs-Auslöser")
    if source_only:
        print("  (nur Quellen geprüft – HTML-Beweise V1–V3/V5–V7 brauchen ein Build)")
    for f in fehler:
        print(f"  FEHLER  {f}")
    print(f"  => {len(fehler)} Fehler")

    if history:
        zeile = {
            "zeit": _dt.datetime.now(_dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
            "raster_version": str((g.get("meta") or {}).get("version")),
            "routen": len(ziele),
            "source_only": source_only,
            "fehler": len(fehler),
        }
        with HISTORY.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(zeile, ensure_ascii=False) + "\n")

    return 1 if fehler else 0


# ------------------------------------------------------------
# Selbsttest: Sabotage-Proben (offline, ohne public/)
# ------------------------------------------------------------
def _fixture_html(g: dict, ziele: dict, methodik: dict) -> str:
    """Minimal-HTML mit allen Fingerabdrücken – wie der Shortcode sie setzt."""
    teile = ['<div data-ff-vg="kopf"></div>']
    # v1 + Routen
    zeilen = []
    for key, z in ziele.items():
        ab = (z or {}).get("abweichung") or ""
        typ = ZIELTYP_LABELS.get(ab, "marktvergleich")
        erklaer = (z or {}).get("abweichung_ziel") or ""
        zeilen.append(f'<tr data-ff-vg-route="{key}" data-ff-vg-zieltyp="{typ}">'
                      f'<td>{erklaer}</td></tr>')
    teile.append(f'<div data-ff-vg-frage="v1"><table>{"".join(zeilen)}</table></div>')
    # v2 Ausschlüsse
    aus = "".join(f'<div data-ff-vg-ausschluss><dt>{a["name"]}</dt></div>'
                  for a in g.get("ausschluesse") or [])
    teile.append(f'<div data-ff-vg-frage="v2">{aus}</div>')
    # v3 + v5 Bereiche
    bereiche = "".join(
        f'<section data-ff-vg-bereich="{b["id"]}">'
        f'<span class="ff-vg__mversion">Methodik v{b["version"]}</span></section>'
        for b in (methodik or {}).get("bereiche") or [])
    teile.append(f'<div data-ff-vg-frage="v3">{bereiche}</div>')
    antwort = str((g.get("provision") or {}).get("antwort") or "")
    sichtbar = "Nein." if antwort.lower() == "nein" else antwort
    teile.append(f'<div data-ff-vg-frage="v4"><p data-ff-vg-provision="{antwort.lower()}">'
                 f'<b>{sichtbar}</b> Provision ist kein Parameter.</p></div>')
    teile.append(f'<div data-ff-vg-frage="v5">{bereiche}</div>')
    trig = "".join('<tr data-ff-vg-trigger><td>x</td></tr>'
                   for _ in (g.get("deaktivierung") or {}).get("ausloeser") or [])
    teile.append(f'<div data-ff-vg-frage="v6"><table>{trig}</table></div>')
    teile.append('<div data-ff-vg-frage="v7"><ul><li>x</li></ul></div>')
    teile.append('<a href="/transparenz/">T</a><a href="/methodik/">M</a>')
    return "<html><body>" + "".join(teile) + "</body></html>"


def selftest() -> int:
    pruefe_detektor_frische()
    g = _lade_yaml(GRUNDSAETZE)
    ziele = (_lade_yaml(ZIELREGISTER) or {}).get("ziele") or {}
    methodik = _lade_yaml(METHODIK)
    basis_html = _fixture_html(g, ziele, methodik)
    footer = f'<footer><a href="https://example.org/{SEITE_PFAD}/">Raster</a></footer>'
    proben: list[tuple[str, bool]] = []

    # 1: Basis ist sauber (Quellen + HTML + Wegweiser).
    fehler: list[str] = []
    pruefe_quellen(copy.deepcopy(g), fehler)
    pruefe_raster_html(basis_html, g, ziele, methodik, fehler)
    pruefe_wegweiser(basis_html, footer, footer, footer, fehler)
    proben.append(("Basis (Quellen + Raster + Wegweiser) sauber", not fehler))

    # 2: provision.antwort "ja" fällt durch.
    sab = copy.deepcopy(g)
    sab["provision"]["antwort"] = "ja"
    fehler = []
    pruefe_quellen(sab, fehler)
    proben.append(("provision.antwort != 'nein' fällt durch",
                   any("MUSS wörtlich 'nein'" in f for f in fehler)))

    # 3: Fehlende Route im Raster fällt durch.
    opfer = next(iter(ziele))
    sab_html = re.sub(rf'<tr data-ff-vg-route="{re.escape(opfer)}".*?</tr>', "",
                      basis_html, count=1, flags=re.S)
    fehler = []
    pruefe_raster_html(sab_html, g, ziele, methodik, fehler)
    proben.append(("Route fehlt im Raster → V2 schlägt an",
                   any(f"V2 Route '{opfer}'" in f for f in fehler)))

    # 4: Einzelanbieter als „Marktvergleich" getarnt fällt durch.
    einzel = next((k for k, z in ziele.items()
                   if (z or {}).get("abweichung") == "einzelanbieter"), None)
    if einzel:
        sab_html = basis_html.replace(
            f'data-ff-vg-route="{einzel}" data-ff-vg-zieltyp="einzelanbieter"',
            f'data-ff-vg-route="{einzel}" data-ff-vg-zieltyp="marktvergleich"')
        fehler = []
        pruefe_raster_html(sab_html, g, ziele, methodik, fehler)
        proben.append(("Einzelangebot als Marktvergleich getarnt → V3 schlägt an",
                       any(f"V3 Route '{einzel}'" in f for f in fehler)))

    # 5: Entfernte Antwort-Sektion fällt durch.
    sab_html = basis_html.replace('<div data-ff-vg-frage="v6">', '<div>', 1)
    fehler = []
    pruefe_raster_html(sab_html, g, ziele, methodik, fehler)
    proben.append(("Fehlende Antwort-Sektion → V1 schlägt an",
                   any("Antwort-Abschnitt v6" in f for f in fehler)))

    # 6: Fehlender Footer-Link fällt durch.
    fehler = []
    pruefe_wegweiser(basis_html, footer, footer, "<footer>ohne Link</footer>", fehler)
    proben.append(("Fehlender Footer-Link → V7 schlägt an",
                   any("Footer-Link" in f for f in fehler)))

    # 7: Verlorene Deaktivierungs-Zeilen fallen durch.
    sab_html = basis_html.replace('<tr data-ff-vg-trigger><td>x</td></tr>', "", 2)
    fehler = []
    pruefe_raster_html(sab_html, g, ziele, methodik, fehler)
    proben.append(("Verlorene Auslöser-Zeilen → V6 schlägt an",
                   any(f.startswith("V6 ") for f in fehler)))

    # 8: Fremde Route im Raster fällt durch.
    sab_html = basis_html.replace(
        '</table></div>',
        '<tr data-ff-vg-route="erfundene-route" data-ff-vg-zieltyp="marktvergleich"></tr>'
        '</table></div>', 1)
    fehler = []
    pruefe_raster_html(sab_html, g, ziele, methodik, fehler)
    proben.append(("Erfundene Route → V2 schlägt an",
                   any("'erfundene-route'" in f for f in fehler)))

    # 9: Fehlender Methodik-Bereich fällt durch.
    opfer_b = ((methodik or {}).get("bereiche") or [{}])[0].get("id")
    sab_html = basis_html.replace(f'data-ff-vg-bereich="{opfer_b}"', 'data-ff-vg-bereich-weg=""', 1)
    fehler = []
    pruefe_raster_html(sab_html, g, ziele, methodik, fehler)
    proben.append(("Fehlender Methodik-Bereich → V5 schlägt an",
                   any(f"V5 Themenbereich '{opfer_b}'" in f for f in fehler)))

    # 10: Ausschluss ohne Grund fällt durch.
    sab = copy.deepcopy(g)
    sab["ausschluesse"][0].pop("grund", None)
    fehler = []
    pruefe_quellen(sab, fehler)
    proben.append(("Ausschluss ohne Begründung fällt durch",
                   any("ohne Begründung ist keiner" in f for f in fehler)))

    alle_ok = True
    print("VERGLEICHS-WACHE – Selbsttest (Sabotage-Proben)")
    for name, ok in proben:
        print(f"  {'OK  ' if ok else 'FAIL'} {name}")
        alle_ok &= ok
    return 0 if alle_ok else 2


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vergleichs-Wache: Bewertungsraster 'So entstehen unsere Vergleiche' (V1–V8)")
    parser.add_argument("--public", default="public",
                        help="Build-Verzeichnis (Default: public)")
    parser.add_argument("--source-only", action="store_true",
                        help="nur kuratierte Quellen prüfen (kein Build nötig)")
    parser.add_argument("--selftest", action="store_true",
                        help="Sabotage-Proben gegen die eigene Prüflogik (offline)")
    parser.add_argument("--history", action="store_true",
                        help="Journalzeile nach data/vergleichsgrundsaetze_history.jsonl")
    args = parser.parse_args()
    try:
        if args.selftest:
            return selftest()
        return lauf(REPO / args.public if not Path(args.public).is_absolute()
                    else Path(args.public), args.source_only, args.history)
    except _Werkzeugfehler as exc:
        print(f"WERKZEUGFEHLER (fail-closed): {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
