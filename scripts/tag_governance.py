#!/usr/bin/env python3
"""tag_governance.py – Wache und Reparatur für die Taxonomie (Tags/Kategorien).

WARUM DIESE WACHE EXISTIERT (Befund 29.09.2026)
Die Google Search Console meldete 237 nicht indexierte Seiten. Die Ursache lag
nicht im Content, sondern in der Taxonomie-Automatik: engine_generate.py hat die
Tags eines Artikels aus seinen SEO-Keywords abgeleitet (`tags = kws[:4]`).
Keywords sind long-tail und pro Artikel einmalig – jeder Artikel hat damit vier
brandneue Tags erzeugt. Nach 63 Artikeln:

    217 Roh-Tags  →  147 Tag-Archive  →  193 Tags mit genau EINEM Artikel
    + 147 zusätzliche /page/1/-Alias-Weiterleitungen

Also ~294 URLs ohne eigenen Suchwert. Google crawlt sie, meldet sie als „nicht
indexiert" und zieht das Budget von den 58 echten Money-Pages ab. Der Defekt
wuchs mit jedem Artikel weiter – eine URL-Leckage, kein einmaliger Fehler.

Diese Wache schließt das Leck an der Quelle: Tags kommen ab jetzt aus dem
kuratierten Register data/seo/tag_register.yaml. Was dort nicht steht, ist kein
Tag – es ist ein Keyword und gehört ins `keywords`-Feld.

WOZU TAGS NOCH DIENEN (Entscheidung 29.09.2026)
Die Tag-Taxonomie ist in hugo.toml abgeschaltet – es gibt KEINE /tags/-Archive
mehr. Das `tags`-Frontmatter-Feld bleibt aber bestehen und wichtig:
  * Hugos Related-Matching ([related] in hugo.toml, Gewicht 80) baut daraus die
    „Das könnte dich auch interessieren"-Karten unter jedem Artikel.
  * Das Article-Schema nutzt es als Keyword-Rückfall (schema_article.html).
Ein Tag ist damit kein URL-Erzeuger mehr, sondern ein Ähnlichkeits-Signal.
Genau deshalb bleibt die Kuratierung nötig: ein Tag, den nur EIN Artikel trägt,
kann per Definition nie zwei Artikel verbinden – er ist für das Related-Matching
totes Gewicht (Regel T4). Ein wucherndes Vokabular verwässert die Treffer.

REGELWERK (harte Funde => Exit 1):
  T1  Register     – Register ist ladbar, Namen eindeutig, kein Synonym doppelt
                     vergeben, kein Synonym gleich einem anderen Tag-Namen
  T2  Unbekannt    – jeder Tag im Frontmatter steht als Name oder Synonym im
                     Register (unbekannte Tags = neue Thin-Archive)
  T3  Kanonisch    – kein Artikel trägt ein Synonym statt des kanonischen Namens
                     (sonst entstehen zwei Archive für dasselbe Thema)
  T4  Wirksamkeit  – jeder benutzte Tag erreicht politik.min_artikel_pro_tag
                     (darunter verbindet er keine zwei Artikel → nutzlos fürs
                      Related-Matching)
  T5  Menge        – kein Artikel über politik.max_tags_pro_artikel Tags,
                     kein Artikel ganz ohne Tag (Waisenkind ohne Crawl-Pfad)
  T6  Form         – Tag-Länge <= max_tag_laenge, keine verbotenen Zeichen
                     (U+202F/U+00A0 erzeugen kaputte Prozent-Slugs in der URL)
  T7  Kategorie    – genau eine Kategorie je Artikel, aus erlaubte_kategorien
  T8  Leichen      – kein Register-Tag ohne Artikel (tote Registerzeile)

SELBSTHEILUNG: --apply schreibt das Frontmatter um (Synonyme → kanonischer
Name, Zeichen-Normalisierung, Dedupe, Kappung auf max_tags_pro_artikel,
Kategorie-Korrektur). Unbekannte Tags werden NICHT geraten: sie werden entfernt
und gemeldet, damit die Redaktion entscheidet, ob daraus ein Registereintrag
oder ein Keyword wird. Reine Register-Defekte (T1) repariert --apply nie.

Nutzung:
    python3 scripts/tag_governance.py --report     Bestand + Bilanz
    python3 scripts/tag_governance.py --check      Wache (CI)
    python3 scripts/tag_governance.py --apply      Frontmatter normalisieren
    python3 scripts/tag_governance.py --json       Maschinen-Ausgabe
    python3 scripts/tag_governance.py --selftest   9 Fälle (Sabotage-Schutz)

Exit: 0 = grün · 1 = harte Funde · 2 = Fehler/Selbsttest fehlgeschlagen
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import sys
import unicodedata

try:
    import yaml
except ImportError:  # pragma: no cover
    print("FEHLER: pyyaml fehlt (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REGISTER = os.environ.get(
    "TAG_REGISTER", os.path.join(BLOG_DIR, "data", "seo", "tag_register.yaml"))
CONTENT = os.environ.get("TAG_CONTENT", os.path.join(BLOG_DIR, "content"))

# Unicode-Leerzeichen, die optisch wie ein Leerzeichen aussehen, aber in der
# URL als %E2%80%AF / %C2%A0 landen. Quelle: die Typografie-Sicherung
# (nbsp_sicherung) schreibt schmale geschützte Leerzeichen in Fließtext –
# im Frontmatter haben sie nichts verloren.
UNSICHTBARE_LEERZEICHEN = "\u00a0\u2007\u2009\u202f\u2060\ufeff"

STANDARD_POLITIK = {
    "max_tags_pro_artikel": 4,
    "min_artikel_pro_tag": 2,
    "max_tag_laenge": 32,
    "verbotene_zeichen": [":", "–", "—", "!", "?", "\u202f", "\u00a0", "\u2009"],
    "erlaubte_kategorien": ["Ratgeber", "News"],
}


# ---------------------------------------------------------------------------
#  Befund-Sammler
# ---------------------------------------------------------------------------
class Funde:
    def __init__(self) -> None:
        self.hart: list[tuple[str, str, str]] = []
        self.weich: list[tuple[str, str, str]] = []

    def add(self, regel: str, wo: str, text: str) -> None:
        self.hart.append((regel, wo, text))

    def warn(self, regel: str, wo: str, text: str) -> None:
        self.weich.append((regel, wo, text))

    def __bool__(self) -> bool:
        return bool(self.hart)


# ---------------------------------------------------------------------------
#  Normalisierung
# ---------------------------------------------------------------------------
def normalisiere(text: str) -> str:
    """Unsichtbare Leerzeichen raus, NFC, Mehrfach-Leerzeichen zusammenziehen."""
    if not isinstance(text, str):
        text = str(text)
    for ch in UNSICHTBARE_LEERZEICHEN:
        text = text.replace(ch, " ")
    text = unicodedata.normalize("NFC", text)
    return re.sub(r"\s+", " ", text).strip()


def vergleichsform(text: str) -> str:
    """Schlüssel für den Register-Abgleich: normalisiert, klein, ohne Bindestrich."""
    t = normalisiere(text).casefold()
    return re.sub(r"[\s\-_/]+", " ", t).strip()


# ---------------------------------------------------------------------------
#  Register
# ---------------------------------------------------------------------------
class Register:
    def __init__(self, daten: dict) -> None:
        self.politik = dict(STANDARD_POLITIK)
        self.politik.update(daten.get("politik") or {})
        self.eintraege = daten.get("tags") or []
        self.namen: list[str] = []
        self.pillar: dict[str, str] = {}
        self._map: dict[str, str] = {}      # vergleichsform -> kanonischer Name
        self.register_funde: list[str] = []
        self._bauen()

    def _bauen(self) -> None:
        gesehen_namen: dict[str, str] = {}
        for e in self.eintraege:
            if not isinstance(e, dict) or not e.get("name"):
                self.register_funde.append(f"Registereintrag ohne 'name': {e!r}")
                continue
            name = normalisiere(e["name"])
            key = vergleichsform(name)
            if key in gesehen_namen:
                self.register_funde.append(
                    f"Tag-Name doppelt im Register: {name!r} (schon als "
                    f"{gesehen_namen[key]!r})")
                continue
            gesehen_namen[key] = name
            self.namen.append(name)
            self.pillar[name] = e.get("pillar") or ""
            self._map[key] = name
        # Synonyme erst nach allen Namen – ein Name gewinnt immer gegen ein Synonym.
        for e in self.eintraege:
            if not isinstance(e, dict) or not e.get("name"):
                continue
            name = normalisiere(e["name"])
            for syn in (e.get("synonyme") or []):
                s = normalisiere(syn)
                key = vergleichsform(s)
                if key in gesehen_namen and gesehen_namen[key] != name:
                    self.register_funde.append(
                        f"Synonym {s!r} (bei {name!r}) ist zugleich Tag-Name "
                        f"{gesehen_namen[key]!r}")
                    continue
                vorher = self._map.get(key)
                if vorher and vorher != name:
                    self.register_funde.append(
                        f"Synonym {s!r} doppelt vergeben: {vorher!r} und {name!r}")
                    continue
                self._map[key] = name

    def kanonisch(self, tag: str) -> str | None:
        return self._map.get(vergleichsform(tag))


def lade_register(pfad: str = REGISTER) -> Register:
    with open(pfad, encoding="utf-8") as fh:
        return Register(yaml.safe_load(fh) or {})


def tags_fuer(keywords, pillar: str = "", titel: str = "",
              register: Register | None = None) -> list[str]:
    """Kanonische Tags für einen NEUEN Artikel bestimmen.

    Das ist die Schnittstelle für die Content-Engine (engine_generate.py,
    generate_drafts.py). Vorher galt dort `tags = keywords[:4]` – und weil
    Keywords long-tail und pro Artikel einmalig sind, entstand mit jedem
    Artikel ein neues Thin-Archiv (Ursache der 237 GSC-Meldungen).

    Ablauf:
      1. Jedes Keyword gegen das Register spiegeln (Name oder Synonym).
      2. Reicht das nicht, den Titel gegen Namen/Synonyme prüfen.
      3. Bleibt es leer, die Tags des Pillars als Auffangnetz nehmen –
         ein Artikel ohne Tag fällt aus Hugos Related-Matching und bekommt
         keine „Das könnte dich auch interessieren"-Karten.
    Es wird NIE ein neuer Tag erfunden. Passt nichts, entscheidet die
    Redaktion über einen Registereintrag.
    """
    reg = register or lade_register()
    max_tags = int(reg.politik.get("max_tags_pro_artikel", 4))
    treffer: list[str] = []

    def nimm(name: str | None) -> None:
        if name and name not in treffer:
            treffer.append(name)

    for kw in (keywords or []):
        nimm(reg.kanonisch(kw))
        if len(treffer) >= max_tags:
            return treffer[:max_tags]

    if titel:
        t_cmp = vergleichsform(titel)
        for e in reg.eintraege:
            if not isinstance(e, dict) or not e.get("name"):
                continue
            name = normalisiere(e["name"])
            kandidaten = [name] + [normalisiere(s) for s in (e.get("synonyme") or [])]
            if any(vergleichsform(k) in t_cmp for k in kandidaten):
                nimm(name)
                if len(treffer) >= max_tags:
                    return treffer[:max_tags]

    # Auffangnetz: ein Artikel ohne Tag fällt aus dem Related-Matching und
    # bekommt keine Verwandten-Karten mehr.
    if not treffer and pillar:
        for e in reg.eintraege:
            if isinstance(e, dict) and e.get("pillar") == pillar and e.get("name"):
                nimm(normalisiere(e["name"]))
                if len(treffer) >= max_tags:
                    break

    return treffer[:max_tags]


# ---------------------------------------------------------------------------
#  Frontmatter lesen/schreiben (zeilenbasiert – erhält Formatierung und Reihenfolge)
# ---------------------------------------------------------------------------
def artikel_dateien(content: str = CONTENT) -> list[str]:
    """Nur echte Artikel. Section-Indizes (_index.md) sind Listenseiten ohne
    eigene Taxonomie – sie tragen keine Tags und dürfen auch keine bekommen."""
    treffer = (glob.glob(os.path.join(content, "posts", "*", "index.md"))
               + glob.glob(os.path.join(content, "posts", "*.md")))
    return sorted(p for p in treffer
                  if os.path.basename(p) not in ("_index.md", "_index.de.md"))


def lese_frontmatter(pfad: str) -> tuple[dict, str]:
    text = open(pfad, encoding="utf-8").read()
    if not text.startswith("---"):
        return {}, text
    teile = text.split("---", 2)
    if len(teile) < 3:
        return {}, text
    try:
        fm = yaml.safe_load(teile[1]) or {}
    except Exception:
        fm = {}
    return fm, text


def _yaml_liste(werte: list[str]) -> str:
    return "[" + ", ".join('"' + w.replace('"', '\\"') + '"' for w in werte) + "]"


def schreibe_feld(text: str, feld: str, werte: list[str]) -> str:
    """Ersetzt `feld: [...]` (inline oder Blockliste) im Frontmatter."""
    kopf_ende = text.index("---", 3)
    kopf, rest = text[:kopf_ende], text[kopf_ende:]
    neu = f"{feld}: {_yaml_liste(werte)}"
    inline = re.compile(rf"^{re.escape(feld)}:[ \t]*\[.*?\][ \t]*$", re.M)
    if inline.search(kopf):
        return inline.sub(lambda _m: neu, kopf, count=1) + rest
    block = re.compile(rf"^{re.escape(feld)}:[ \t]*\n(?:[ \t]*-[ \t]*.+\n)+", re.M)
    if block.search(kopf):
        return block.sub(lambda _m: neu + "\n", kopf, count=1) + rest
    skalar = re.compile(rf"^{re.escape(feld)}:[ \t]*\S.*$", re.M)
    if skalar.search(kopf):
        return skalar.sub(lambda _m: neu, kopf, count=1) + rest
    return kopf.rstrip("\n") + "\n" + neu + "\n" + rest


# ---------------------------------------------------------------------------
#  Prüfung
# ---------------------------------------------------------------------------
def pruefe(reg: Register, dateien: list[str], anwenden: bool = False) -> tuple[Funde, dict]:
    F = Funde()
    pol = reg.politik
    verboten = [c for c in (pol.get("verbotene_zeichen") or [])]
    max_tags = int(pol.get("max_tags_pro_artikel", 4))
    min_art = int(pol.get("min_artikel_pro_tag", 2))
    max_len = int(pol.get("max_tag_laenge", 32))
    erlaubte_kat = [normalisiere(k) for k in (pol.get("erlaubte_kategorien") or [])]

    # ---- T1: Register selbst ----
    for f in reg.register_funde:
        F.add("T1", "data/seo/tag_register.yaml", f)

    # ---- T6: Form der Registernamen (der Generator kopiert sie 1:1) ----
    for name in reg.namen:
        if len(name) > max_len:
            F.add("T6", "tag_register.yaml",
                  f"Tag-Name zu lang ({len(name)} > {max_len}): {name!r}")
        for ch in verboten:
            if ch in name:
                F.add("T6", "tag_register.yaml",
                      f"verbotenes Zeichen {ch!r} in Tag-Name {name!r}")

    nutzung: dict[str, int] = {n: 0 for n in reg.namen}
    unbekannt: dict[str, list[str]] = {}
    geaendert: list[str] = []
    stats = {"artikel": 0, "roh_tags": set(), "tags_vorher": 0}

    for pfad in dateien:
        rel = os.path.relpath(pfad, BLOG_DIR)
        fm, text = lese_frontmatter(pfad)
        if not fm:
            F.warn("T0", rel, "kein lesbares Frontmatter – übersprungen")
            continue
        stats["artikel"] += 1
        roh = fm.get("tags") or []
        if isinstance(roh, str):
            roh = [roh]
        stats["tags_vorher"] += len(roh)

        kanon: list[str] = []
        for t in roh:
            t_norm = normalisiere(t)
            stats["roh_tags"].add(t_norm)
            # T6 – Form des Roh-Tags
            if t_norm != str(t):
                F.warn("T6", rel,
                       f"Tag mit unsichtbarem/mehrfachem Leerzeichen: {t!r} → {t_norm!r}")
            k = reg.kanonisch(t_norm)
            if k is None:
                unbekannt.setdefault(t_norm, []).append(rel)
                F.add("T2", rel,
                      f"Tag {t_norm!r} steht nicht im Register "
                      f"(neues Thin-Archiv – als Keyword führen oder eintragen)")
                continue
            if normalisiere(t) != k:
                F.add("T3", rel, f"Synonym {t_norm!r} statt kanonisch {k!r}")
            if k not in kanon:
                kanon.append(k)

        # T5 – Menge
        if len(kanon) > max_tags:
            F.add("T5", rel,
                  f"{len(kanon)} Tags (erlaubt: {max_tags}) – "
                  f"überzählig: {kanon[max_tags:]}")
        if not kanon:
            F.add("T5", rel, "Artikel ohne gültigen Tag – fällt aus dem "
                             "Related-Matching und verliert seine Verwandten-Karten")
        for k in kanon[:max_tags]:
            nutzung[k] = nutzung.get(k, 0) + 1

        # T7 – Kategorie
        kats = fm.get("categories") or []
        if isinstance(kats, str):
            kats = [kats]
        kats_n = [normalisiere(k) for k in kats]
        kat_neu = [k for k in kats_n if k in erlaubte_kat][:1] or ["Ratgeber"]
        if len(kats_n) != 1 or kats_n[0] not in erlaubte_kat:
            F.add("T7", rel,
                  f"Kategorie {kats_n or '—'} unzulässig "
                  f"(erlaubt: genau eine aus {erlaubte_kat})")

        # ---- Selbstheilung ----
        if anwenden:
            neu_tags = kanon[:max_tags]
            neuer_text = text
            if neu_tags != [normalisiere(t) for t in roh]:
                neuer_text = schreibe_feld(neuer_text, "tags", neu_tags)
            if kats_n != kat_neu:
                neuer_text = schreibe_feld(neuer_text, "categories", kat_neu)
            if neuer_text != text:
                with open(pfad, "w", encoding="utf-8") as fh:
                    fh.write(neuer_text)
                geaendert.append(rel)

    # ---- T4 / T8 ----
    for name, n in sorted(nutzung.items()):
        if n == 0:
            F.add("T8", "tag_register.yaml",
                  f"Register-Tag {name!r} wird von keinem Artikel benutzt (tote Zeile)")
        elif n < min_art:
            F.add("T4", "tag_register.yaml",
                  f"Tag {name!r} hat nur {n} Artikel (mind. {min_art}) – "
                  f"verbindet keine zwei Artikel, also wirkungslos fürs "
                  f"Related-Matching; in einen breiteren Tag überführen")

    bericht = {
        "artikel": stats["artikel"],
        "roh_tags_gefunden": len(stats["roh_tags"]),
        "tags_im_register": len(reg.namen),
        "tags_benutzt": sum(1 for v in nutzung.values() if v),
        "tag_zuweisungen_vorher": stats["tags_vorher"],
        "nutzung": nutzung,
        "unbekannt": {k: sorted(set(v)) for k, v in sorted(unbekannt.items())},
        "geaendert": geaendert,
        "politik": pol,
    }
    return F, bericht


# ---------------------------------------------------------------------------
#  Ausgabe
# ---------------------------------------------------------------------------
def drucke_report(reg: Register, b: dict) -> None:
    print("=" * 66)
    print(" TAG-REGISTER – Bestand")
    print("=" * 66)
    print(f" Artikel geprüft ............ {b['artikel']}")
    print(f" Tags im Register ........... {b['tags_im_register']}")
    print(f" davon benutzt .............. {b['tags_benutzt']}")
    print(f" Roh-Tags im Frontmatter .... {b['roh_tags_gefunden']}")
    print(f" Tag-Zuweisungen ............ {b['tag_zuweisungen_vorher']}")
    print()
    nach_pillar: dict[str, list[tuple[str, int]]] = {}
    for name, n in b["nutzung"].items():
        nach_pillar.setdefault(reg.pillar.get(name, ""), []).append((name, n))
    for pil in sorted(nach_pillar):
        print(f"  ── {pil or '(ohne Pillar)'}")
        for name, n in sorted(nach_pillar[pil], key=lambda x: (-x[1], x[0])):
            marke = "  " if n >= int(b["politik"]["min_artikel_pro_tag"]) else " ⚠"
            print(f"    {n:3d} Artikel {marke} {name}")
    if b["unbekannt"]:
        print(f"\n  ── Nicht im Register ({len(b['unbekannt'])})")
        for t, wo in b["unbekannt"].items():
            print(f"    {t!r}  ({len(wo)}×)")
    archive = b["tags_benutzt"]
    print(f"\n  Crawl-Fläche Tag-Archive: {archive} statt {b['roh_tags_gefunden']} "
          f"Roh-Tags")


def drucke_funde(F: Funde) -> None:
    if F.weich:
        print(f"\n  Hinweise ({len(F.weich)}):")
        for r, wo, t in F.weich[:40]:
            print(f"    [{r}] {wo}: {t}")
        if len(F.weich) > 40:
            print(f"    … {len(F.weich) - 40} weitere")
    if F.hart:
        print(f"\n  HARTE FUNDE ({len(F.hart)}):")
        for r, wo, t in F.hart[:80]:
            print(f"    [{r}] {wo}: {t}")
        if len(F.hart) > 80:
            print(f"    … {len(F.hart) - 80} weitere")


# ---------------------------------------------------------------------------
#  Selbsttest
# ---------------------------------------------------------------------------
def selftest() -> int:
    import tempfile
    ok, fehl = 0, []

    def check(name: str, bedingung: bool) -> None:
        nonlocal ok
        if bedingung:
            ok += 1
        else:
            fehl.append(name)

    # 1 Normalisierung entfernt schmales geschütztes Leerzeichen
    check("normalisiere U+202F", normalisiere("Interrail\u202f+\u202fBahncard")
          == "Interrail + Bahncard")
    # 2 Vergleichsform ignoriert Bindestrich/Groß-Klein
    check("vergleichsform", vergleichsform("Mesh-WLAN") == vergleichsform("mesh wlan"))

    basis = {
        "politik": {"max_tags_pro_artikel": 2, "min_artikel_pro_tag": 2,
                    "max_tag_laenge": 20, "verbotene_zeichen": [":"],
                    "erlaubte_kategorien": ["Ratgeber"]},
        "tags": [
            {"name": "Strom sparen", "pillar": "p", "synonyme": ["Stromkosten"]},
            {"name": "Gas sparen", "pillar": "p", "synonyme": ["Gaskosten"]},
        ],
    }
    reg = Register(json.loads(json.dumps(basis)))
    # 3 Register baut sauber
    check("T1 sauberes Register", reg.register_funde == [])
    # 4 Synonym wird aufgelöst
    check("Synonym-Auflösung", reg.kanonisch("Stromkosten") == "Strom sparen")

    # 5 doppeltes Synonym wird erkannt
    kaputt = json.loads(json.dumps(basis))
    kaputt["tags"][1]["synonyme"].append("Stromkosten")
    check("T1 doppeltes Synonym", bool(Register(kaputt).register_funde))

    def baue(tmp: str, fm: str) -> str:
        d = os.path.join(tmp, "posts", "a")
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, "index.md")
        open(p, "w", encoding="utf-8").write(fm + "\nText\n")
        return p

    with tempfile.TemporaryDirectory() as tmp:
        p = baue(tmp, '---\ntitle: "T"\ntags: ["Fremdtag"]\ncategories: ["Ratgeber"]\n---')
        F, _ = pruefe(reg, [p])
        # 6 unbekannter Tag = harter Fund T2
        check("T2 unbekannter Tag", any(r == "T2" for r, _, _ in F.hart))

    with tempfile.TemporaryDirectory() as tmp:
        p = baue(tmp, '---\ntitle: "T"\ntags: ["Stromkosten"]\ncategories: ["Ratgeber"]\n---')
        F, _ = pruefe(reg, [p])
        # 7 Synonym im Artikel = harter Fund T3
        check("T3 Synonym im Artikel", any(r == "T3" for r, _, _ in F.hart))

    with tempfile.TemporaryDirectory() as tmp:
        p = baue(tmp, '---\ntitle: "T"\ntags: ["Stromkosten"]\ncategories: ["Quatsch"]\n---')
        pruefe(reg, [p], anwenden=True)
        fm, _ = lese_frontmatter(p)
        # 8 --apply normalisiert Synonym UND Kategorie
        check("--apply heilt", fm.get("tags") == ["Strom sparen"]
              and fm.get("categories") == ["Ratgeber"])

    with tempfile.TemporaryDirectory() as tmp:
        p = baue(tmp, '---\ntitle: "T"\ntags:\n  - "Gaskosten"\n  - "Stromkosten"\n'
                      'categories: ["Ratgeber"]\n---')
        pruefe(reg, [p], anwenden=True)
        fm, _ = lese_frontmatter(p)
        # 9 Blocklisten-Syntax wird ebenfalls umgeschrieben
        check("--apply Blockliste", sorted(fm.get("tags") or [])
              == ["Gas sparen", "Strom sparen"])

    # ---- tags_fuer(): die Schnittstelle der Content-Engine ----
    # 10 Unbekannte Keywords erfinden NIE einen Tag (das war die Ursache
    #    der Tag-Explosion – hier wird sie dauerhaft ausgeschlossen).
    check("tags_fuer erfindet nichts",
          tags_fuer(["voellig unbekanntes long-tail keyword"], "", "", reg) == [])
    # 11 Synonym im Keyword wird zum kanonischen Namen
    check("tags_fuer löst Synonym auf",
          tags_fuer(["Stromkosten"], "", "", reg) == ["Strom sparen"])
    # 12 Kappung auf max_tags_pro_artikel (hier 2)
    check("tags_fuer kappt",
          len(tags_fuer(["Stromkosten", "Gaskosten", "Strom sparen"], "", "", reg)) <= 2)
    # 13 Pillar-Auffangnetz: nie ein Artikel ohne Crawl-Pfad
    check("tags_fuer Pillar-Fallback",
          tags_fuer(["nichts passendes"], "p", "", reg) != [])
    # 14 Titel-Treffer, wenn die Keywords nichts hergeben
    check("tags_fuer Titel-Treffer",
          tags_fuer(["nichts"], "", "Wie du Gas sparen kannst", reg) == ["Gas sparen"])

    print(f"Selbsttest: {ok} bestanden, {len(fehl)} fehlgeschlagen")
    for f in fehl:
        print(f"  ✗ {f}")
    return 0 if not fehl else 2


# ---------------------------------------------------------------------------
def main() -> int:
    ap = argparse.ArgumentParser(description="Wache und Reparatur für die Taxonomie")
    ap.add_argument("--check", action="store_true", help="Wache (Exit 1 bei Funden)")
    ap.add_argument("--apply", action="store_true", help="Frontmatter normalisieren")
    ap.add_argument("--report", action="store_true", help="Bestand ausgeben")
    ap.add_argument("--json", action="store_true", help="Maschinen-Ausgabe")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()

    try:
        reg = lade_register()
    except FileNotFoundError:
        print(f"FEHLER: Register fehlt: {REGISTER}", file=sys.stderr)
        return 2

    dateien = artikel_dateien()
    F, bericht = pruefe(reg, dateien, anwenden=a.apply)

    if a.json:
        print(json.dumps({
            "hart": [{"regel": r, "wo": w, "text": t} for r, w, t in F.hart],
            "weich": [{"regel": r, "wo": w, "text": t} for r, w, t in F.weich],
            "bericht": {k: v for k, v in bericht.items() if k != "politik"},
        }, ensure_ascii=False, indent=2))
        return 1 if F.hart else 0

    if a.report or not (a.check or a.apply):
        drucke_report(reg, bericht)

    if a.apply:
        if bericht["geaendert"]:
            print(f"\n  {len(bericht['geaendert'])} Datei(en) normalisiert:")
            for r in bericht["geaendert"]:
                print(f"    ✓ {r}")
        else:
            print("\n  Nichts zu ändern – Frontmatter ist bereits kanonisch.")
        # Nach --apply erneut messen: was jetzt noch steht, muss die Redaktion lösen.
        F, bericht = pruefe(reg, dateien, anwenden=False)

    drucke_funde(F)
    if F.hart:
        print(f"\n✗ {len(F.hart)} harte Funde – Taxonomie nicht sauber.")
        return 1
    print("\n✓ Taxonomie sauber: jeder Tag kuratiert und wirksam.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
