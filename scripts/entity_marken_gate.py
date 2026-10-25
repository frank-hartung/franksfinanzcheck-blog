#!/usr/bin/env python3
"""Entity-/Marken-Wache für FranksFinanzcheck (offline, deterministisch).

Hintergrund (SERP-Live-Prüfung 25.10.2026, §3): Google korrigiert die
Markensuche „FranksFinanzcheck" auf „Frank Finanzcheck" und schlägt
FINANZCHECK.de vor – die Marke ist keine eindeutige Entität. Der Vertrag
dagegen steht in data/entity.yaml: EIN wortgleicher Identitätssatz und
EINE wortgleiche Abgrenzung auf jeder Fläche, die Suchmaschinen,
KI-Antwortmaschinen und Journalisten zur Einordnung lesen (Startseite,
Schema.org, /ueber/, /impressum/, /presse/, llms.txt), dazu eine einzige
Profil-Liste (hugo.toml [[params.socialIcons]]) für sameAs und rel=me.

Regeln (jede Regel hat eine Sabotage-Probe im Selbsttest):
  E1  Register      – data/entity.yaml lädt; Pflichtfelder da; Definition
                      nennt Marke + Domain, Abgrenzung nennt FINANZCHECK.de
  E2  Build-Quelle  – hugo.toml entityDefinition/entityAbgrenzung sind
                      wortgleich mit dem Register
  E3  Wortlaut      – Definition/Abgrenzung stehen wortgleich auf /ueber/,
                      /impressum/, /presse/, im llms.txt-Generator und in
                      static/llms.txt; Startseiten-Description beginnt mit
                      dem Entity-Satz
  E4  Profile       – [[params.socialIcons]] == profile_aktiv (Menge);
                      kein geplantes Profil (LinkedIn/Xing) vorab im Build;
                      keine Platzhalter-URL (nur Domain ohne Profilpfad);
                      jedes Profil hat ein Theme-Icon
  E5  Templates     – Person/ProfilePage/Organization lesen sameAs aus der
                      einen Liste ($entityProfiles/$profiles), kein
                      hartkodiertes Einzel-Profil; Footer verlinkt
                      social_icons (rel=me); Entity-Box liest Params statt
                      Literale und ist auf der Startseite eingebunden
  E6  Namensflächen – Newsletter-Absender trägt die exakte Marke und die
                      eigene Domain; alle Newsletter-Seiten nennen die
                      Marke in der Description; DOI-Text des Workers nennt
                      sie; keine Falschschreibung („Franks Finanzcheck" …)
                      in content/, layouts/ oder hugo.toml
  E7  Register-Reife– repo-kontrollierte Publisher-Voraussetzungen stehen:
                      Logo (SVG + Raster ≥ 512 px), RSS-Feed aktiv,
                      Presse-Seite + Studien-Asset vorhanden; ein externer
                      Register-Status darf nur mit Beleg „aktiv" sein
  E8  Build (public)– Startseite: Organization.description == Definition,
                      Person- und Organization-sameAs == Profil-Liste,
                      WebSite.name == Marke, Definition + Abgrenzung im
                      sichtbaren Text; /ueber/ und /impressum/ tragen die
                      Abgrenzung gerendert; Footer-rel=me je Profil
  E9  Snippet-Marke – og:site_name == Marke auf jeder indexierbaren Seite
                      (hart); Marken-Anteil in <title> als ehrliche
                      Messung (weich – das 60-Zeichen-Fenster lässt ein
                      Marken-Suffix bei den meisten Artikeln nicht zu;
                      Markenträger ist der Site-Name aus dem WebSite-
                      Schema, siehe MARKEN-ENTITY-HIGHEND-2026-10-25.md)

Nutzung:
  python3 scripts/entity_marken_gate.py                # Quellen-Prüfung
  python3 scripts/entity_marken_gate.py --source-only  # dasselbe, explizit
  python3 scripts/entity_marken_gate.py --public public
  python3 scripts/entity_marken_gate.py --selftest     # Sabotage-Proben

Exit: 0 = grün (Warnungen möglich) · 1 = harte Befunde · 2 = Setup-Fehler
Vertrag: data/entity.yaml · Runbook: docs/ANLEITUNG-MARKEN-ENTITY.md
"""
import html as _html
import json
import os
import re
import struct
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

try:
    import yaml
except ImportError:  # fail-closed: ohne PyYAML keine Aussage
    yaml = None

BLOG_DIR = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

FALSCHSCHREIBUNGEN = (
    "Franks Finanzcheck",
    "FrankFinanzcheck",
    "Franks-Finanzcheck",
    "franksFinanzcheck",
)
STATUS_ERLAUBT = {"offen", "nicht angestrebt", "aktiv", "abgelehnt", "in Prüfung"}


class Findings:
    def __init__(self) -> None:
        self.hart: list[tuple[str, str, str]] = []
        self.weich: list[tuple[str, str, str]] = []

    def add(self, regel: str, wo: str, text: str, soft: bool = False) -> None:
        (self.weich if soft else self.hart).append((regel, wo, text))

    def regeln(self) -> set[str]:
        return {r for r, _, _ in self.hart}

    def berichten(self, titel: str) -> int:
        print(f"== Entity-/Marken-Wache – {titel} ==")
        for regel, wo, text in self.hart:
            print(f"  FEHLER [{regel}] {wo}: {text}")
        for regel, wo, text in self.weich:
            print(f"  WARNUNG [{regel}] {wo}: {text}")
        print(f"  Ergebnis: {len(self.hart)} Fehler, {len(self.weich)} Warnungen")
        return 1 if self.hart else 0


# ---------------------------------------------------------------- Helfer

def _lies(root: Path, rel: str) -> str | None:
    p = root / rel
    try:
        return p.read_text(encoding="utf-8")
    except OSError:
        return None


class _TextExtraktor(HTMLParser):
    """Sichtbarer Text ohne Script-/Style-Inhalte.

    Bewusst ein Parser statt Regex-Tag-Filter (CodeQL py/bad-tag-filter):
    Regex-Filter sind prinzipiell umgehbar (Schreibweise, Leerzeichen in
    End-Tags wie </script >) – und hier auch unnötig, denn gebraucht wird
    nur der sichtbare Text für Wortlaut-Proben auf der eigenen Site.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.teile: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs) -> None:
        if tag in ("script", "style"):
            self._skip += 1
        self.teile.append(" ")

    def handle_endtag(self, tag) -> None:
        if tag in ("script", "style") and self._skip:
            self._skip -= 1
        self.teile.append(" ")

    def handle_data(self, data) -> None:
        if not self._skip:
            self.teile.append(data)


def _norm(s: str) -> str:
    """HTML → vergleichbarer Text (nur für Sicht-Text-Proben im Build)."""
    extraktor = _TextExtraktor()
    try:
        extraktor.feed(s)
        extraktor.close()
    except Exception:  # noqa: BLE001 – Parser ist tolerant; Teilergebnis genügt der Probe
        pass
    text = "".join(extraktor.teile).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _toml_wert(text: str, key: str) -> str | None:
    m = re.search(rf'^[ \t]*{re.escape(key)}\s*=\s*"(.*)"\s*$', text, re.M)
    return m.group(1) if m else None


def _social_icons(toml: str) -> list[tuple[str, str]]:
    out: list[tuple[str, str]] = []
    for block in toml.split("[[params.socialIcons]]")[1:]:
        block = block.split("[[", 1)[0].split("\n[", 1)[0]
        name = _toml_wert(block, "name")
        url = _toml_wert(block, "url")
        if name and url:
            out.append((name.strip(), url.strip()))
    return out


def _png_masse(pfad: Path) -> tuple[int, int] | None:
    try:
        with open(pfad, "rb") as f:
            kopf = f.read(24)
    except OSError:
        return None
    if len(kopf) < 24 or kopf[:8] != b"\x89PNG\r\n\x1a\n":
        return None
    return struct.unpack(">II", kopf[16:24])


def _jsonld(html_text: str) -> list[dict]:
    bloecke: list[dict] = []
    for m in re.finditer(
            r'<script[^>]*type="?application/ld\+json"?[^>]*>([\s\S]*?)</script>',
            html_text):
        try:
            daten = json.loads(m.group(1))
        except (ValueError, TypeError):
            continue  # Parse-Gültigkeit ist S1 der schema_seo-Wache
        if isinstance(daten, dict):
            bloecke.append(daten)
            for knoten in daten.get("@graph") or []:
                if isinstance(knoten, dict):
                    bloecke.append(knoten)
    return bloecke


def _knoten(bloecke: list[dict], typ: str) -> dict | None:
    for b in bloecke:
        if b.get("@type") == typ:
            return b
    return None


# ------------------------------------------------------------- E1 Register

def _entity_laden(root: Path, F: Findings) -> dict | None:
    rel = "data/entity.yaml"
    roh = _lies(root, rel)
    if roh is None:
        F.add("E1", rel, "Entity-Register fehlt – Vertrag in data/entity.yaml anlegen")
        return None
    if yaml is None:  # pragma: no cover – main() fängt das vorher ab
        F.add("E1", rel, "PyYAML fehlt (fail-closed)")
        return None
    try:
        daten = yaml.safe_load(roh)
    except yaml.YAMLError as exc:
        F.add("E1", rel, f"YAML nicht lesbar: {exc}")
        return None
    if not isinstance(daten, dict):
        F.add("E1", rel, "Register ist kein Mapping")
        return None
    marke = daten.get("marke") or {}
    name = str(marke.get("name") or "")
    domain = str(marke.get("domain") or "")
    definition = str(daten.get("definition") or "")
    abgrenzung = str(daten.get("abgrenzung") or "")
    if not name or not domain:
        F.add("E1", rel, "marke.name / marke.domain fehlen")
    if name and name not in definition:
        F.add("E1", rel, "definition nennt die Marke nicht")
    if domain and domain not in definition:
        F.add("E1", rel, "definition nennt die Domain nicht (Entity-Anker fehlt)")
    if "FINANZCHECK.de" not in abgrenzung:
        F.add("E1", rel, "abgrenzung nennt FINANZCHECK.de nicht – Disambiguation wirkungslos")
    if definition and definition == abgrenzung:
        F.add("E1", rel, "definition und abgrenzung sind identisch")
    if not daten.get("profile_aktiv"):
        F.add("E1", rel, "profile_aktiv ist leer – sameAs hätte keine Quelle")
    return daten


def _profile(entity: dict) -> tuple[list[tuple[str, str]], list[str]]:
    aktiv = [(str(p.get("name") or ""), str(p.get("url") or ""))
             for p in entity.get("profile_aktiv") or [] if isinstance(p, dict)]
    geplant = [str(p.get("name") or "")
               for p in entity.get("profile_geplant") or [] if isinstance(p, dict)]
    return aktiv, geplant


# ----------------------------------------------------------- Quellen E2–E7

def check_source(root: Path, F: Findings) -> dict | None:
    entity = _entity_laden(root, F)
    if entity is None:
        return None
    marke = str((entity.get("marke") or {}).get("name") or "")
    definition = str(entity.get("definition") or "")
    abgrenzung = str(entity.get("abgrenzung") or "")
    aktiv, geplant = _profile(entity)
    aktiv_urls = {u for _, u in aktiv if u}

    # ---- E2: hugo.toml trägt denselben Wortlaut
    toml = _lies(root, "hugo.toml") or ""
    if not toml:
        F.add("E2", "hugo.toml", "Datei fehlt")
        return entity
    if _toml_wert(toml, "entityDefinition") != definition:
        F.add("E2", "hugo.toml",
              "entityDefinition weicht von data/entity.yaml `definition` ab "
              "(Wortlaut nur an einer Stelle ändern und überall nachziehen)")
    if _toml_wert(toml, "entityAbgrenzung") != abgrenzung:
        F.add("E2", "hugo.toml",
              "entityAbgrenzung weicht von data/entity.yaml `abgrenzung` ab")

    # ---- E3: Wortlaut auf allen Lese-Flächen
    flaechen = [
        ("content/ueber/index.md", definition, "Definition"),
        ("content/ueber/index.md", abgrenzung, "Abgrenzung"),
        ("content/impressum/index.md", abgrenzung, "Abgrenzung"),
        ("content/presse/index.md", definition, "Definition (Boilerplate)"),
        ("scripts/generate_llms_txt.py", definition, "Definition"),
        ("scripts/generate_llms_txt.py", abgrenzung, "Abgrenzung"),
        ("static/llms.txt", definition, "Definition"),
        ("static/llms.txt", abgrenzung, "Abgrenzung"),
    ]
    cache: dict[str, str | None] = {}
    for rel, satz, was in flaechen:
        if rel not in cache:
            cache[rel] = _lies(root, rel)
        text = cache[rel]
        if text is None:
            F.add("E3", rel, "Datei fehlt")
        elif satz and satz not in text:
            hinweis = (" – Generator laufen lassen: python3 scripts/generate_llms_txt.py"
                       if rel == "static/llms.txt" else "")
            F.add("E3", rel, f"{was} steht nicht wortgleich in der Datei{hinweis}")
    impressum = cache.get("content/impressum/index.md") or ""
    if impressum and f"({marke}, " not in impressum:
        F.add("E3", "content/impressum/index.md",
              "Betreiberzeile nennt die Marke nicht (erwartet: „(FranksFinanzcheck, …)“)")
    home = _lies(root, "content/_index.md") or ""
    m = re.search(r'^description:\s*"(.*?)"\s*$', home, re.M)
    if not m or not m.group(1).startswith(f"{marke} ist das Fixkosten-Cockpit"):
        F.add("E3", "content/_index.md",
              "Startseiten-Description beginnt nicht mit dem Entity-Satz "
              f"„{marke} ist das Fixkosten-Cockpit …“")

    # ---- E4: Profil-Parität (eine Liste für sameAs + rel=me)
    icons = _social_icons(toml)
    icon_urls = {u for _, u in icons}
    if icon_urls != aktiv_urls:
        F.add("E4", "hugo.toml",
              f"[[params.socialIcons]] {sorted(icon_urls)} != profile_aktiv "
              f"{sorted(aktiv_urls)} (data/entity.yaml) – Schema und Register laufen auseinander")
    svg = (_lies(root, "layouts/_partials/svg.html")
           or _lies(root, "themes/PaperMod/layouts/_partials/svg.html") or "")
    for name, url in icons:
        if name in geplant:
            F.add("E4", "hugo.toml",
                  f"Profil „{name}“ steht im Build, ist im Register aber nur geplant – "
                  "erst anlegen/verlinken, dann in profile_aktiv heben")
        if not re.match(r"^https://[^/]+/\S{2,}", url or ""):
            F.add("E4", "hugo.toml",
                  f"Profil „{name}“ hat keine echte Profil-URL ({url!r}) – "
                  "Platzhalter sind falsche sameAs-Signale")
        if svg and f'"{name}"' not in svg:
            F.add("E4", "themes/PaperMod/layouts/_partials/svg.html",
                  f"kein Icon für Profil „{name}“ – Footer-Link bliebe ohne Symbol")

    # ---- E5: Template-Verträge
    head = _lies(root, "layouts/_partials/extend_head.html") or ""
    if '(slice "https://www.pinterest' in head or "(slice \"https://mastodon" in head:
        F.add("E5", "layouts/_partials/extend_head.html",
              "hartkodierte Einzel-Profil-Liste statt $entityProfiles – "
              "genau so fehlte Mastodon im Person-Knoten")
    if head.count('"sameAs" $entityProfiles') < 3:
        F.add("E5", "layouts/_partials/extend_head.html",
              "Person, ProfilePage und Organization müssen sameAs alle aus "
              "$entityProfiles lesen (3 Fundstellen erwartet)")
    if "site.Params.entityDefinition" not in head:
        F.add("E5", "layouts/_partials/extend_head.html",
              "Organization.description liest entityDefinition nicht aus hugo.toml")
    artikel = _lies(root, "layouts/_partials/schema_article.html") or ""
    if '"sameAs" $profiles' not in artikel or "site.Params.entityDefinition" not in artikel:
        F.add("E5", "layouts/_partials/schema_article.html",
              "Article-Publisher braucht sameAs aus $profiles und die "
              "entityDefinition als description (Parität zur Startseite)")
    footer = _lies(root, "layouts/_partials/footer.html") or ""
    if 'partial "social_icons.html"' not in footer:
        F.add("E5", "layouts/_partials/footer.html",
              "Social-Profile sind nicht sichtbar verlinkt (rel=me fehlt siteweit)")
    box = _lies(root, "layouts/_partials/entity_box.html")
    if box is None:
        F.add("E5", "layouts/_partials/entity_box.html", "Entity-Box der Startseite fehlt")
    else:
        if "site.Params.entityDefinition" not in box or "site.Params.entityAbgrenzung" not in box:
            F.add("E5", "layouts/_partials/entity_box.html",
                  "Box muss beide Sätze aus hugo.toml lesen, nicht als Literal führen")
        if definition and definition in box:
            F.add("E5", "layouts/_partials/entity_box.html",
                  "Definitions-Literal in der Box gefunden – Drift-Quelle, Param nutzen")
    liste = _lies(root, "layouts/_default/list.html") or ""
    if 'partial "entity_box.html"' not in liste:
        F.add("E5", "layouts/_default/list.html",
              "Entity-Box ist auf der Startseite nicht eingebunden")

    # ---- E6: Namensflächen + Schreibweise
    studio = _lies(root, "data/newsletter_studio.json")
    try:
        absender = (json.loads(studio or "{}").get("email") or {}).get("absender") or {}
    except ValueError:
        absender = {}
        F.add("E6", "data/newsletter_studio.json", "JSON nicht lesbar")
    if marke and marke not in str(absender.get("name") or ""):
        F.add("E6", "data/newsletter_studio.json",
              f"Newsletter-Absendername {absender.get('name')!r} trägt die exakte Marke nicht")
    if not str(absender.get("email") or "").endswith("@franksfinanzcheck.de"):
        F.add("E6", "data/newsletter_studio.json",
              "Newsletter-Absenderadresse liegt nicht auf der eigenen Domain")
    for pfad in sorted((root / "content").glob("newsletter*/index.md")):
        text = pfad.read_text(encoding="utf-8")
        m = re.search(r'^description:\s*"(.*?)"\s*$', text, re.M)
        if not m or marke not in m.group(1):
            F.add("E6", str(pfad.relative_to(root)),
                  "Newsletter-Seite nennt die Marke in der Description nicht")
    worker = _lies(root, "newsletter-worker/src/index.js") or ""
    if worker and f"von {marke}" not in worker:
        F.add("E6", "newsletter-worker/src/index.js",
              "Double-Opt-In-Text nennt die Marke nicht („… von FranksFinanzcheck“)")
    suchraeume = [root / "content", root / "layouts"]
    dateien = [p for r in suchraeume if r.exists()
               for p in r.rglob("*") if p.is_file() and p.suffix in (".md", ".html")]
    dateien.append(root / "hugo.toml")
    for pfad in dateien:
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError:
            continue
        for falsch in FALSCHSCHREIBUNGEN:
            if falsch in text:
                F.add("E6", str(pfad.relative_to(root)),
                      f"Falschschreibung der Marke: „{falsch}“ statt „{marke}“")

    # ---- E7: Register-Reife (nur, was das Repo kontrolliert)
    if _lies(root, "static/images/brand/logo.svg") is None:
        F.add("E7", "static/images/brand/logo.svg", "Marken-Logo (SVG) fehlt")
    masse = _png_masse(root / "static/images/pwa/icon-512.png")
    if not masse or min(masse) < 512:
        F.add("E7", "static/images/pwa/icon-512.png",
              "kein Raster-Logo ≥ 512 px (Publisher Center braucht ein "
              "quadratisches Raster-Logo; SVG allein genügt dort nicht)")
    if _lies(root, "layouts/rss.xml") is None or '"RSS"' not in toml:
        F.add("E7", "layouts/rss.xml",
              "RSS-Feed nicht aktiv (Publisher Center liest /index.xml)")
    if _lies(root, "content/presse/index.md") is None:
        F.add("E7", "content/presse/index.md", "Presse-Seite fehlt (Entity-Anlaufstelle)")
    if not (root / "content/studien/fixkosten-index-2026-q4").exists() \
            or _lies(root, "static/downloads/fixkosten-index-2026-q4.csv") is None:
        F.add("E7", "content/studien/",
              "zitierfähiges Studien-Asset (Fixkosten-Index + CSV) fehlt – "
              "ohne belegbare Erwähnungen keine Wikipedia-/Wikidata-Grundlage")
    for name, eintrag in (entity.get("externe_register") or {}).items():
        if not isinstance(eintrag, dict):
            continue
        status = str(eintrag.get("status") or "")
        if status not in STATUS_ERLAUBT:
            F.add("E7", "data/entity.yaml",
                  f"externe_register.{name}: unbekannter Status {status!r}")
        elif status == "aktiv" and not str(eintrag.get("beleg") or "").strip():
            F.add("E7", "data/entity.yaml",
                  f"externe_register.{name} ist „aktiv“ ohne Beleg – "
                  "kein externer Status ohne Nachweis (Ehrlichkeits-Regel)")
    return entity


# ------------------------------------------------------------- Public E8/E9

def check_public(root: Path, public: Path, F: Findings) -> None:
    entity = _entity_laden(root, F)
    if entity is None:
        return
    marke = str((entity.get("marke") or {}).get("name") or "")
    definition = str(entity.get("definition") or "")
    abgrenzung = str(entity.get("abgrenzung") or "")
    aktiv, _ = _profile(entity)
    aktiv_urls = {u for _, u in aktiv if u}

    def seite(rel: str) -> str | None:
        p = public / rel
        try:
            return p.read_text(encoding="utf-8")
        except OSError:
            F.add("E8", rel, "Seite fehlt im Build")
            return None

    home = seite("index.html")
    if home:
        bloecke = _jsonld(home)
        webseite = _knoten(bloecke, "WebSite") or {}
        if webseite.get("name") != marke:
            F.add("E8", "index.html",
                  f"WebSite.name ist {webseite.get('name')!r} statt „{marke}“ "
                  "(Quelle des Google-Site-Namens im Snippet)")
        publisher = webseite.get("publisher") or {}
        if publisher.get("description") != definition:
            F.add("E8", "index.html",
                  "Organization.description ist nicht der kanonische Identitätssatz")
        if set(publisher.get("sameAs") or []) != aktiv_urls:
            F.add("E8", "index.html",
                  f"Organization.sameAs {sorted(publisher.get('sameAs') or [])} "
                  f"!= Profil-Liste {sorted(aktiv_urls)}")
        person = _knoten(bloecke, "Person") or {}
        if set(person.get("sameAs") or []) != aktiv_urls:
            F.add("E8", "index.html",
                  f"Person.sameAs {sorted(person.get('sameAs') or [])} != Profil-Liste "
                  f"{sorted(aktiv_urls)} (Befund 25.10.2026: Mastodon fehlte hier)")
        sichtbar = _norm(home)
        if _norm(definition) not in sichtbar:
            F.add("E8", "index.html", "Identitätssatz steht nicht im sichtbaren Startseiten-Text")
        if _norm(abgrenzung) not in sichtbar:
            F.add("E8", "index.html", "Abgrenzung steht nicht im sichtbaren Startseiten-Text")
        for url in aktiv_urls:
            if not re.search(rf'href="?{re.escape(url)}"?[^>]*rel="[^"]*\bme\b', home) \
                    and not re.search(rf'rel="[^"]*\bme\b[^"]*"[^>]*href="?{re.escape(url)}', home):
                F.add("E8", "index.html", f"kein rel=me-Link auf das offizielle Profil {url}")
    ueber = seite("ueber/index.html")
    if ueber:
        sichtbar = _norm(ueber)
        if _norm(definition) not in sichtbar or _norm(abgrenzung) not in sichtbar:
            F.add("E8", "ueber/index.html",
                  "Definition oder Abgrenzung fehlt im gerenderten Text von /ueber/")
        profil = _knoten(_jsonld(ueber), "ProfilePage") or {}
        haupt = profil.get("mainEntity") or {}
        if set(haupt.get("sameAs") or []) != aktiv_urls:
            F.add("E8", "ueber/index.html",
                  "ProfilePage.mainEntity.sameAs weicht von der Profil-Liste ab")
    impressum = seite("impressum/index.html")
    if impressum and _norm(abgrenzung) not in _norm(impressum):
        F.add("E8", "impressum/index.html", "Abgrenzung fehlt im gerenderten Impressum")

    # ---- E9: Snippet-Marke (og:site_name hart, <title> als Messung)
    seiten = 0
    titel_mit_marke = 0
    for pfad in sorted(public.rglob("*.html")):
        rel = pfad.relative_to(public).as_posix()
        if rel.startswith("go/"):
            continue  # Affiliate-Gateways: noindex, kein Snippet-Anspruch
        text = pfad.read_text(encoding="utf-8", errors="ignore")
        robots = re.search(r'<meta[^>]+name="?robots"?[^>]+content="?([^"\s>]+)', text)
        if not robots or "noindex" in robots.group(1):
            continue
        if "og:title" not in text:
            continue  # Verifikations-/Sonderdateien ohne Head-Vertrag
        seiten += 1
        if not re.search(rf'og:site_name"?[^>]+content="?{re.escape(marke)}"?', text):
            F.add("E9", rel, "og:site_name trägt die Marke nicht")
        titel = re.search(r"<title>([\s\S]*?)</title>", text)
        if titel and marke in _html.unescape(titel.group(1)):
            titel_mit_marke += 1
    if seiten:
        F.add("E9", "public/",
              f"Messung: <title> trägt die Marke auf {titel_mit_marke}/{seiten} "
              "indexierbaren Seiten. Rest: Marken-Suffix passt nicht ins "
              "60-Zeichen-Fenster (M1) – Markenträger ist dort der Site-Name "
              "(WebSite-Schema + og:site_name, hart geprüft). Kein Fehler, "
              "aber ehrlich ausgewiesen statt grün gerechnet.",
              soft=True)


# ---------------------------------------------------------------- Selbsttest

_DEF = ("FranksFinanzcheck (franksfinanzcheck.de) ist das unabhängige "
        "Fixkosten-Cockpit für deutsche Haushalte: Test-Definition.")
_ABG = ("FranksFinanzcheck steht in keiner geschäftlichen Verbindung zum "
        "Kreditvergleichsportal FINANZCHECK.de. Test-Abgrenzung.")


def _schreibe(root: Path, rel: str, inhalt: str | bytes) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(inhalt, bytes):
        p.write_bytes(inhalt)
    else:
        p.write_text(inhalt, encoding="utf-8")


def _png_fixture(mass: int) -> bytes:
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR"
            + struct.pack(">II", mass, mass) + b"\x08\x06\x00\x00\x00" + b"\x00" * 4)


def _fixture(root: Path) -> None:
    _schreibe(root, "data/entity.yaml", f"""version: 1
marke:
  name: "FranksFinanzcheck"
  domain: "franksfinanzcheck.de"
definition: "{_DEF}"
abgrenzung: "{_ABG}"
profile_aktiv:
  - name: "pinterest"
    url: "https://www.pinterest.de/franksfinanzcheck/"
  - name: "mastodon"
    url: "https://mastodon.social/@FranksFinanzcheck"
profile_geplant:
  - name: "linkedin"
    status: "nicht aktiv"
  - name: "xing"
    status: "nicht aktiv"
externe_register:
  wikidata:
    status: "offen"
    beleg: ""
""")
    _schreibe(root, "hugo.toml", f"""title = "FranksFinanzcheck"
[outputs]
  home = ["HTML", "RSS", "SWJS"]
[params]
  entityDefinition = "{_DEF}"
  entityAbgrenzung = "{_ABG}"
  [[params.socialIcons]]
    name = "pinterest"
    url = "https://www.pinterest.de/franksfinanzcheck/"
    title = "Pinterest"
  [[params.socialIcons]]
    name = "mastodon"
    url = "https://mastodon.social/@FranksFinanzcheck"
    title = "Mastodon"
""")
    _schreibe(root, "content/_index.md",
              '---\ndescription: "FranksFinanzcheck ist das Fixkosten-Cockpit für Tests"\n---\n')
    _schreibe(root, "content/ueber/index.md", f"# Über\n\n{_DEF}\n\n{_ABG}\n")
    _schreibe(root, "content/impressum/index.md",
              f"# Impressum\n\nBetreiber (FranksFinanzcheck, franksfinanzcheck.de):\n\n{_ABG}\n")
    _schreibe(root, "content/presse/index.md", f"# Presse\n\n> {_DEF}\n")
    _schreibe(root, "content/newsletter/index.md",
              '---\ndescription: "Newsletter von FranksFinanzcheck"\n---\n')
    _schreibe(root, "content/newsletter-abmelden/index.md",
              '---\ndescription: "Abmeldung von FranksFinanzcheck"\n---\n')
    _schreibe(root, "content/studien/fixkosten-index-2026-q4/index.md", "# Studie\n")
    _schreibe(root, "scripts/generate_llms_txt.py", f'KOPF = """{_DEF}\n{_ABG}"""\n')
    _schreibe(root, "static/llms.txt", f"{_DEF}\n\n{_ABG}\n")
    _schreibe(root, "static/images/brand/logo.svg", "<svg/>\n")
    _schreibe(root, "static/images/pwa/icon-512.png", _png_fixture(512))
    _schreibe(root, "static/downloads/fixkosten-index-2026-q4.csv", "a;b\n")
    _schreibe(root, "layouts/rss.xml", "<rss/>\n")
    _schreibe(root, "layouts/_partials/extend_head.html",
              '"sameAs" $entityProfiles\n"sameAs" $entityProfiles\n'
              '"sameAs" $entityProfiles\nsite.Params.entityDefinition\n')
    _schreibe(root, "layouts/_partials/schema_article.html",
              '"sameAs" $profiles\nsite.Params.entityDefinition\n')
    _schreibe(root, "layouts/_partials/footer.html", '{{- partial "social_icons.html" . }}\n')
    _schreibe(root, "layouts/_partials/entity_box.html",
              "{{ site.Params.entityDefinition }} {{ site.Params.entityAbgrenzung }}\n")
    _schreibe(root, "layouts/_default/list.html", '{{- partial "entity_box.html" . }}\n')
    _schreibe(root, "themes/PaperMod/layouts/_partials/svg.html",
              'eq $icon_name "pinterest" eq $icon_name "mastodon" '
              'eq $icon_name "linkedin" eq $icon_name "xing"\n')
    _schreibe(root, "data/newsletter_studio.json", json.dumps(
        {"email": {"absender": {"name": "Frank von FranksFinanzcheck",
                                "email": "news@franksfinanzcheck.de"}}}))
    _schreibe(root, "newsletter-worker/src/index.js",
              "const T = 'Spar-Newsletter von FranksFinanzcheck';\n")


def _public_fixture(root: Path, public: Path, person_sameas: list[str]) -> None:
    urls = ["https://www.pinterest.de/franksfinanzcheck/",
            "https://mastodon.social/@FranksFinanzcheck"]
    person = {"@context": "https://schema.org", "@type": "Person",
              "name": "Frank Hartung", "sameAs": person_sameas}
    webseite = {"@context": "https://schema.org", "@type": "WebSite",
                "name": "FranksFinanzcheck",
                "publisher": {"@type": "Organization", "name": "FranksFinanzcheck",
                              "description": _DEF, "sameAs": urls}}
    profil = {"@context": "https://schema.org", "@type": "ProfilePage",
              "mainEntity": {"@type": "Person", "name": "Frank Hartung", "sameAs": urls}}

    def ld(obj: dict) -> str:
        return ('<script type="application/ld+json">'
                + json.dumps(obj, ensure_ascii=False) + "</script>")

    me_links = "".join(
        f'<a href="{u}" target="_blank" rel="noopener noreferrer me">x</a>' for u in urls)
    kopf = ('<meta name="robots" content="index, follow">'
            '<meta property="og:title" content="T">'
            '<meta property="og:site_name" content="FranksFinanzcheck">')
    _schreibe(public, "index.html",
              f"<html><head><title>Start</title>{kopf}{ld(person)}{ld(webseite)}</head>"
              f"<body><p>{_DEF}</p><p>{_ABG}</p>{me_links}</body></html>")
    _schreibe(public, "ueber/index.html",
              f"<html><head><title>Über</title>{kopf}{ld(profil)}</head>"
              f"<body><p>{_DEF}</p><p>{_ABG}</p></body></html>")
    _schreibe(public, "impressum/index.html",
              f"<html><head><title>Impressum</title>{kopf}</head>"
              f"<body><p>{_ABG}</p></body></html>")


def selftest() -> int:
    faelle: list[tuple[str, str, str | None]] = []  # (Name, Soll-Regel, Datei-Ersatz)

    def lauf(sabotage=None) -> Findings:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            _fixture(root)
            if sabotage:
                sabotage(root)
            F = Findings()
            check_source(root, F)
            return F

    def ersetze(rel: str, alt: str, neu: str):
        def _t(root: Path) -> None:
            p = root / rel
            p.write_text(p.read_text(encoding="utf-8").replace(alt, neu), encoding="utf-8")
        return _t

    gut = lauf()
    ok = True
    if gut.hart:
        ok = False
        print("SELBSTTEST FEHLER: Gutes Fixture erzeugt Befunde:")
        for r, w, t in gut.hart:
            print(f"  [{r}] {w}: {t}")
    else:
        print("SELBSTTEST ok: gutes Fixture ohne Befunde")

    proben = [
        ("E2 greift bei Wortlaut-Drift in hugo.toml", "E2",
         ersetze("hugo.toml", "Test-Definition.", "Abweichende Definition.")),
        ("E3 greift bei gekürzter Abgrenzung im Impressum", "E3",
         ersetze("content/impressum/index.md", "Test-Abgrenzung.", "Gekürzt.")),
        ("E4 greift bei fehlendem Mastodon-Profil", "E4",
         ersetze("hugo.toml", "https://mastodon.social/@FranksFinanzcheck",
                 "https://mastodon.social/@AnderesProfil")),
        ("E4 greift bei LinkedIn-Platzhalter im Build", "E4",
         ersetze("hugo.toml", 'title = "Mastodon"',
                 'title = "Mastodon"\n  [[params.socialIcons]]\n'
                 '    name = "linkedin"\n    url = "https://www.linkedin.com/"\n'
                 '    title = "LinkedIn"')),
        ("E5 greift bei hartkodierter Pinterest-Liste", "E5",
         ersetze("layouts/_partials/extend_head.html", '"sameAs" $entityProfiles\n',
                 '"sameAs" (slice "https://www.pinterest.de/franksfinanzcheck/")\n', )),
        ("E6 greift bei Absender ohne Marke", "E6",
         ersetze("data/newsletter_studio.json", "Frank von FranksFinanzcheck", "Sparpost")),
        ("E6 greift bei Falschschreibung im Content", "E6",
         ersetze("content/ueber/index.md", "# Über", "# Über Franks Finanzcheck")),
        ("E7 greift bei „aktiv“ ohne Beleg", "E7",
         ersetze("data/entity.yaml", 'status: "offen"', 'status: "aktiv"')),
    ]
    for name, regel, sabotage in proben:
        F = lauf(sabotage)
        if regel in F.regeln():
            print(f"SELBSTTEST ok: {name}")
        else:
            ok = False
            print(f"SELBSTTEST FEHLER: {name} – Regel {regel} schlug nicht an "
                  f"(gefunden: {sorted(F.regeln()) or 'nichts'})")

    # Public-Proben (E8): gutes Build-Fixture sauber, Person-Lücke schlägt an
    urls = ["https://www.pinterest.de/franksfinanzcheck/",
            "https://mastodon.social/@FranksFinanzcheck"]
    for name, sameas, soll in [
            ("E8 gutes Build-Fixture ohne Befunde", urls, None),
            ("E8 greift bei Person.sameAs nur mit Pinterest", urls[:1], "E8")]:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "repo"
            public = Path(td) / "public"
            _fixture(root)
            _public_fixture(root, public, sameas)
            F = Findings()
            check_public(root, public, F)
            if soll is None and not F.hart:
                print(f"SELBSTTEST ok: {name}")
            elif soll and soll in F.regeln():
                print(f"SELBSTTEST ok: {name}")
            else:
                ok = False
                print(f"SELBSTTEST FEHLER: {name} – gefunden: "
                      f"{[(r, w) for r, w, _ in F.hart] or 'nichts'}")
    print("SELBSTTEST " + ("BESTANDEN" if ok else "NICHT BESTANDEN"))
    return 0 if ok else 2


# -------------------------------------------------------------------- main

def main(argv: list[str]) -> int:
    if yaml is None:
        print("FEHLER: PyYAML fehlt – Wache kann das Register nicht lesen (fail-closed).")
        return 2
    if "--selftest" in argv:
        return selftest()
    F = Findings()
    if "--public" in argv:
        i = argv.index("--public")
        public = Path(argv[i + 1]) if i + 1 < len(argv) else BLOG_DIR / "public"
        if not public.is_absolute():
            public = BLOG_DIR / public
        if not public.exists():
            print(f"FEHLER: Build-Verzeichnis {public} fehlt – erst hugo bauen.")
            return 2
        check_public(BLOG_DIR, public, F)
        return F.berichten(f"Public-Prüfung gegen {public}")
    check_source(BLOG_DIR, F)
    return F.berichten("Quellen-Prüfung")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
