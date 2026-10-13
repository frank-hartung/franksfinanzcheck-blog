#!/usr/bin/env python3
# ============================================================
#  KI-REDAKTION – gemeinsame Helfer (Stufe 0)
#  ------------------------------------------------------------
#  Gemeinsame Bausteine für die drei Rollen der Blog-Automatik
#  nach dem Schema Claude/ChatGPT/Jasper:
#
#    claude_writer.py  → Rolle „Claude":    lange Premium-Artikel
#    news_writer.py    → Rolle „ChatGPT":   schnelle News-Kompakt
#    jasper_seo.py     → Rolle „Jasper":    SEO-Pass (deterministisch)
#
#  KOSTEN-REGEL (Dauervorgabe Frank, 08.09.2026): Diese Automatik
#  darf NUR Gratis-Zugänge nutzen. Paid-APIs (Anthropic/OpenAI)
#  werden NIE automatisch verwendet; sie lassen sich nur manuell per
#  Env-Key zuschalten.
#
#  SEIT 03.10.2026: Die Rolle „ChatGPT" läuft auf OpenAIs eigenem
#  offenen Modell `openai/gpt-oss-120b` – kostenlos über drei
#  unabhängige Hoster (Groq → NVIDIA NIM → Cloudflare Workers AI),
#  Gemini als Gegenprobe aus einem anderen Modellhaus. Die Ketten
#  stehen in data/ki_transportweg.yaml, das Gate ist
#  scripts/ki_transportweg.py. Warum kein echtes ChatGPT-Konto:
#  CHATGPT-GRATIS-TRANSPORTWEG-PREMIUM-2026-10-03.md.
#
#  SEIT 13.10.2026 (Dauerheilung #734): Jeder Writer, der hier sein
#  Frontmatter baut, unterliegt dem Fachfreigabe-Vertrag der Engine
#  (zwei Bahnen, Issue #521) – siehe Abschnitt FACHFREIGABE-VERTRAG.
# ============================================================
from __future__ import annotations

import datetime
import json
import os
import re
import sys
from pathlib import Path

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import yaml  # noqa: E402

import editorial_review_gate as erg  # noqa: E402  – Risiko-SSOT + Prüfgerüst
import engine_capacity as ec  # noqa: E402  – Bahn-SSOT (AUTO/FACHFREIGABE)
import post_utils  # noqa: E402
from generate_drafts import slugify, yaml_str  # noqa: E402

CONFIG_FILE = os.path.join(BLOG_DIR, "data", "ki_redaktion.yaml")
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")
AKTUELLE_FILE = os.path.join(BLOG_DIR, "data", "aktuelle_entwicklungen.yaml")
REPORT_FILE = os.path.join(BLOG_DIR, "KI-REDAKTION-REPORT.md")
AUTHOR = os.environ.get("BLOG_AUTHOR") or "Frank Hartung"
AFFILIATE_URL = (os.environ.get("AFFILIATE_URL")
                 or "https://a.check24.net/misc/click.php?pid=80968&aid=18")

DISCLOSURE = (
    "**Transparenz:** Dieser Artikel enthält Affiliate-Links (Werbung). "
    "Beim Abschluss über einen Link erhalten wir eine Provision – für dich "
    "entstehen keine Mehrkosten."
)

DISCLAIMER = (
    "_Wichtiger Hinweis: Dieser Artikel dient ausschließlich der "
    "allgemeinen Information und stellt keine Anlage-, Rechts- oder "
    "Steuerberatung dar. Prüfe Konditionen und Bedingungen immer beim "
    "jeweiligen Anbieter._"
)

DEFAULT_CONFIG = {
    # Gratis-Provider zuerst (Kosten-Regel). Paid-Anbieter nur, wenn
    # jemand bewusst einen Key hinterlegt UND hier freischaltet.
    # Drei Hoster desselben OpenAI-Modells + ein fremdes Modellhaus:
    # fällt einer aus oder ist sein Tageskontingent leer, rückt der
    # nächste nach, statt die Produktion anzuhalten.
    "anbieter_kette_lang": ["groq", "nvidia", "cloudflare", "gemini"],
    "anbieter_kette_news": ["groq", "nvidia", "cloudflare", "gemini"],
    "zeichenvorgabe_lang": {"min": 11000, "ziel": 14000, "max": 18000},
    "zeichenvorgabe_news": {"min": 10500, "ziel": 12000, "max": 15000},
    "auto_veroeffentlichen": False,   # Dauervorgabe: NIE automatisch live
    "max_artikel_pro_lauf": 1,
}


def load_config() -> dict:
    """Konfiguration laden (mit sicheren Defaults, nie crashen)."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, encoding="utf-8") as fh:
                cfg.update(yaml.safe_load(fh) or {})
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ ki_redaktion.yaml nicht lesbar ({e}) – Defaults aktiv.")
    return cfg


def _load_yaml(path):
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001
        return None


# ============================================================
#  FACHFREIGABE-VERTRAG DER KI-REDAKTION (Dauerheilung #734)
#  ------------------------------------------------------------
#  Die Content-Engine kennt seit 02.10.2026 zwei Bahnen (Issue #521):
#  AUTO-Themen darf die Automatik bis zum Entwurf und weiter tragen;
#  YMYL-Hochrisiko (Versicherung, Kredit, Baufinanzierung, Altersvorsorge)
#  gehört in die FACHFREIGABE-Bahn – ohne namentliche Prüfung, Belegkette,
#  Zahlenprotokoll und Siegel geht dort nichts live.
#
#  Die KI-Redaktion kannte diesen Vertrag bis 13.10.2026 nicht. Der
#  News-Writer zog den nächsten freien Aufhänger – Kategorie
#  „versicherung“ – und schrieb einen Hochrisiko-Entwurf ohne jedes
#  Prüfgerüst. Das Redaktions-Gate tat seine Pflicht (E03), die
#  werktägliche Prüfqueue öffnete Issue #734. Derselbe Writer hatte am
#  17.09. den titelgleichen Schwesterentwurf erzeugt, der erst in #586
#  nachträglich geprüft und versiegelt werden musste. Die Maschine
#  produzierte Arbeit, die sie selbst nie ausliefern darf – exakt die
#  Klasse von #521, nur an einer zweiten Produktionslinie.
#
#  Seitdem gilt an EINER Stelle für jeden Writer, der hier sein
#  Frontmatter baut (claude_writer, news_writer, poppy_repurpose):
#
#    AUTO          → schreibt wie bisher; das Frontmatter trägt wie bei
#                    der Engine das Risikoklassen-Gerüst (status
#                    „ausstehend“).
#    FACHFREIGABE  → nur auf ausdrückliche menschliche Beauftragung
#                    (`--fachfreigabe`) UND nur bei offenem WIP-Limit der
#                    Bahn (`engine_capacity.fachfreigabe_bahn`). Der
#                    Entwurf trägt dann `redaktionelle_pruefung` mit
#                    risikoklasse „hoch“ und status „ausstehend“ – nie
#                    „freigegeben“. Die Freigabe bleibt beim Menschen.
#
#  Die Einstufung wird NICHT nachgebaut: `bahn_fuer()` fragt
#  `engine_capacity.bahn_fuer_thema()`, das seinerseits
#  `editorial_review_gate.classify_text()` mit demselben Material aufruft,
#  das das Gate später am fertigen Artikel benutzt (Titel + die ersten
#  zwei Keywords + Pillar). Unbekannt ist nicht AUTO: Scheitert die
#  Einstufung, entsteht kein Entwurf (fail-closed).
# ============================================================
BAHN_AUTO = ec.BAHN_AUTO
BAHN_FACHFREIGABE = ec.BAHN_FACHFREIGABE
FACHFREIGABE_FLAG = "--fachfreigabe"

# Arbeitsauftrag für das Modell, wenn ein Mensch einen YMYL-Entwurf
# bewusst beauftragt hat. Inhaltlich dieselben Leitplanken wie der
# Hochrisiko-Block der Engine (generate_drafts, „ARBEITSENTWURF, KEINE
# FREIGABE“) – ein Modell darf keine fertige Fachprüfung simulieren.
YMYL_ARBEITSAUFTRAG = (
    "\n\nYMYL-RISIKOKLASSE HOCH – ARBEITSENTWURF, KEINE FREIGABE:\n"
    "- Behaupte weder fachliche Prüfung noch Beratung, eigene Kundenfälle "
    "oder eigene Tests.\n"
    "- Nenne keine Beträge, Prozentwerte, Fristen, Paragraphen oder "
    "Marktmechanismen, die nicht im Brief mit konkreter Quelle stehen. Fehlt "
    "der Beleg, lass die Aussage weg, statt zu raten.\n"
    "- Keine Pauschalaussagen zu Versicherungsschutz, Bonität, Zinsen oder "
    "Anbieterverhalten; nenne Bedingungen und Gegenfälle.\n"
    "- Eine Modellrechnung nur mit frei gewählten, als solche markierten "
    "Annahmen; zeige jeden Rechenschritt.\n"
    "- Kein Kaufaufruf im Fachtext: Kriterien, Risiken und Alternativen "
    "zuerst vollständig erklären.\n"
)


class FachfreigabeErforderlich(RuntimeError):
    """Dieses Material darf ohne (gültige) Beauftragung nicht geschrieben werden.

    Bewusst eine eigene Klasse: Fallback-Pfade der Writer (z. B. das
    Ersatz-Frontmatter der Poppy-Werkbank) dürfen sie NIE als „irgendein
    Fehler“ schlucken – sonst wäre der Vertrag mit einem `except Exception`
    umgehbar.
    """


def _einstufen(frage, title, keywords, pillar) -> str:
    """Eine `engine_capacity`-Frage zum Thema stellen – fail-closed."""
    thema = {"title": title or "", "keywords": list(keywords or []),
             "pillar": pillar or ""}
    try:
        return frage(thema)
    except Exception as exc:  # noqa: BLE001 – unbekannt ist nicht AUTO
        raise FachfreigabeErforderlich(
            f"Risikoklasse für „{title}“ nicht bestimmbar "
            f"({exc.__class__.__name__}: {exc}) – fail-closed, kein Entwurf."
        ) from exc


def risikoklasse(title, keywords=None, pillar=None) -> str:
    """standard/erhoeht/hoch – über `engine_capacity` aus der Gate-SSOT."""
    return _einstufen(ec.risikoklasse_fuer_thema, title, keywords, pillar)


def bahn_fuer(title, keywords=None, pillar=None) -> str:
    """AUTO oder FACHFREIGABE – wörtlich `engine_capacity.bahn_fuer_thema`."""
    return _einstufen(ec.bahn_fuer_thema, title, keywords, pillar)


def pruefgeruest(title, keywords=None, pillar=None) -> str:
    """Frontmatter-Block `redaktionelle_pruefung` wie bei der Engine.

    Risikoklasse aus der Gate-SSOT, status „ausstehend“ – nie Prüfer, nie
    „freigegeben“ (`editorial_review_gate.review_scaffold_yaml`).
    """
    return erg.review_scaffold_yaml(risikoklasse(title, keywords, pillar))


def fachfreigabe_lage() -> dict:
    """WIP-Lage der Fachfreigabe-Bahn über den Bestand der Writer.

    Gemessen wird mit `engine_capacity.fachfreigabe_bahn` – dieselbe Zahl,
    die `engine_capacity.lage()` im Kapazitätsbericht ausweist. Eigene
    Funktion, damit Tests die Lage festnageln können, ohne den echten
    Bestand zu lesen.
    """
    return ec.fachfreigabe_bahn(Path(post_utils.POSTS_DIR))


def fachfreigabe_pruefen(*, title, keywords=None, pillar=None,
                         beauftragt: bool = False,
                         lage: dict | None = None) -> str:
    """Darf dieser KI-Entwurf entstehen? Liefert die Bahn oder wirft.

    AUTO          → immer erlaubt.
    FACHFREIGABE  → nur mit bewusster Beauftragung (`beauftragt=True`,
                    CLI `--fachfreigabe`) UND offenem WIP-Limit.

    Writer rufen das VOR der Generierung auf (kein verbranntes Kontingent,
    kein verbrauchter Aufhänger); `build_frontmatter` ruft es an der
    letzten Schreibgrenze ein zweites Mal (Defense in Depth).
    """
    bahn = bahn_fuer(title, keywords, pillar)
    if bahn != BAHN_FACHFREIGABE:
        return bahn
    if not beauftragt:
        raise FachfreigabeErforderlich(
            f"„{title}“ ist YMYL-Hochrisiko (Bahn FACHFREIGABE). Die "
            "Automatik schreibt solche Entwürfe nicht: Ohne namentliche "
            "Fachprüfung wären sie nie veröffentlichbar und landeten nur in "
            "der YMYL-Prüfqueue (Issue #734). Bewusst beauftragen mit "
            f"{FACHFREIGABE_FLAG}.")
    lage = fachfreigabe_lage() if lage is None else lage
    if not lage.get("geoeffnet"):
        raise FachfreigabeErforderlich(
            f"„{title}“ ist beauftragt, aber die Fachfreigabe-Bahn ist "
            f"geschlossen: {lage.get('grund') or 'WIP-Limit erreicht'}. "
            "Erst den Prüfstapel abarbeiten "
            "(python3 scripts/editorial_review_gate.py --all).")
    return bahn


def existing_titles() -> set:
    """Alle bereits verwendeten Titel (Kleinschreibung), Duplikat-Schutz."""
    titles = set()
    for path in post_utils.list_post_paths():
        try:
            with open(path, encoding="utf-8") as fh:
                head = fh.read(4000)
        except OSError:
            continue
        m = re.search(r'(?m)^title:\s*"?(.+?)"?\s*$', head)
        if m:
            titles.add(m.group(1).strip().lower())
    return titles


def bestands_slugs() -> set:
    """Alle Artikel-Slugs, normalisiert wie das Themen-Gedächtnis der Engine.

    Bewusst über `reserve_topics._bestands_slugs` (CLAUDE.md: „Immer über
    `_bestands_slugs()` normalisieren“) – Datumspräfix und Dubletten-Zähler
    fallen weg, keine zweite Normalisierungsregel.
    """
    import reserve_topics
    return reserve_topics._bestands_slugs(Path(post_utils.POSTS_DIR))


def titel_vergeben(title: str, *, titel: set | None = None,
                   slugs: set | None = None) -> bool:
    """Gibt es diesen Artikel schon – als Titel ODER als Slug? (#734)

    Der exakte Titel allein reicht nicht: SEO-Werkzeuge verlängern Titel
    nachträglich („… für den Alltag: Geld sparen“), der Slug bleibt. So
    entstanden die Entwürfe vom 23.09. und 09.10. als Dubletten bereits
    veröffentlichter Artikel, und am 13.10. schrieb der News-Writer – ganz
    ohne Prüfung – den Titel des Entwurfs vom 17.09. ein zweites Mal.
    """
    titel = existing_titles() if titel is None else titel
    if (title or "").strip().lower() in titel:
        return True
    slugs = bestands_slugs() if slugs is None else slugs
    return slugify(title or "") in slugs


def pick_topic(pillar: str | None = None, *,
               fachfreigabe: bool = False) -> dict | None:
    """Nächstes freies Thema aus dem kuratierten Pool (data/topics.yaml).

    Deterministisch: erstes Thema des (optional gefilterten) Pools, das
    noch keinen bestehenden Post-Titel belegt. Kein Halluzinations-
    risiko – Themen sind ausschließlich kuratiert.

    Ohne Beauftragung nur aus der AUTO-Bahn – mit genau dem Filter, den
    die Engine für ihre Tagesquote benutzt (`engine_capacity.nur_auto`,
    Issue #521). Bis 13.10.2026 stand hier kein Filter – an diesem Tag
    waren 55 von 202 Pool-Themen YMYL-Hochrisiko (#734).
    """
    data = _load_yaml(TOPICS_FILE) or {}
    topics = data.get("topics") or []
    if not fachfreigabe:
        topics = ec.nur_auto(topics)
    used, slugs = existing_titles(), bestands_slugs()
    for t in topics:
        if pillar and t.get("pillar") != pillar:
            continue
        title = (t.get("title") or "").strip()
        if title and not titel_vergeben(title, titel=used, slugs=slugs):
            return t
    return None


def news_hook_kandidaten(kategorie: str | None = None, *,
                         heute: datetime.date | None = None) -> list[dict]:
    """Alle gültigen, unverbrauchten Aufhänger aus data/aktuelle_entwicklungen.yaml.

    Der Pool ist von Menschen kuratiert (Anti-Halluzinations-Regel des
    Repos). Einträge außerhalb ihres Gültigkeitsfensters (ab/bis) oder
    bereits verarbeitete (ki_news_used) fallen heraus.

    Bewusst eine LISTE statt „der nächste“ (bis 13.10.2026:
    `pick_news_hook`): Welcher Aufhänger geschrieben werden DARF, entscheidet
    erst der Writer mit Bahn- und Dublettenprüfung. Ein übersprungener
    YMYL-Aufhänger bleibt unverbraucht im Pool – er wartet auf eine
    menschliche Beauftragung, statt still verheizt zu werden.
    """
    entries = _load_yaml(AKTUELLE_FILE)
    if not isinstance(entries, list):
        return []
    today = (heute or datetime.date.today()).isoformat()
    out: list[dict] = []
    for e in entries:
        if not isinstance(e, dict) or not e.get("hook"):
            continue
        if kategorie and e.get("kategorie") != kategorie:
            continue
        if e.get("ab") and str(e["ab"]) > today:
            continue
        if e.get("bis") and str(e["bis"]) < today:
            continue
        if e.get("ki_news_used"):
            continue
        out.append(e)
    return out


def mark_news_hook_used(hook_id: str) -> None:
    """Verarbeiteten Aufhänger im Pool markieren (idempotent)."""
    if not os.path.exists(AKTUELLE_FILE) or not hook_id:
        return
    try:
        with open(AKTUELLE_FILE, encoding="utf-8") as fh:
            text = fh.read()
        pattern = (r'(- id: ' + re.escape(hook_id)
                   + r'\b(?:(?!^- id:|\Z).)*?)(?=\n- id: |\Z)')

        def add_flag(m):
            block = m.group(1)
            if "ki_news_used" in block:
                return block
            return block.rstrip("\n") + "\n  ki_news_used: true\n"

        new = re.sub(pattern, add_flag, text, count=1, flags=re.S | re.M)
        if new != text:
            with open(AKTUELLE_FILE, "w", encoding="utf-8") as fh:
                fh.write(new)
    except Exception as e:  # noqa: BLE001
        print(f"  ⚠ Aufhänger konnte nicht markiert werden: {e}")


def unique_bundle_slug(title: str) -> str:
    """Slug mit Datumspräfix; hängt Zähler an, falls schon vorhanden."""
    date = datetime.date.today().isoformat()
    base = f"{date}-{slugify(title)}"
    if not os.path.exists(os.path.join(post_utils.POSTS_DIR, base)):
        return base
    i = 2
    while os.path.exists(os.path.join(post_utils.POSTS_DIR, f"{base}-{i}")):
        i += 1
    return f"{base}-{i}"


def _kanonische_frontmatter_tags(tags, *, pillar=None, title="") -> list[str]:
    """Zentrale, fail-closed Tag-Grenze für alle KI-Writer.

    `tags` ist aus historischen Gründen der Parametername, darf aber niemals
    ungeprüfte Keywords in das Frontmatter durchreichen.  Das Register ist
    die einzige Quelle; ein fehlendes Register oder ein nicht zuordenbares
    Thema stoppt den Draft statt neue URL-Terme zu erfinden.
    """
    from tag_governance import kanonische_tags
    return kanonische_tags(tags or [], pillar=pillar or "", titel=title or "")


def build_frontmatter(*, title, description, tags, pillar=None,
                      keywords=None, rolle="claude", kurzantwort=None,
                      news=False, kategorie=None,
                      fachfreigabe: bool = False) -> str:
    """Hugo-Frontmatter nach Repo-Konvention – IMMER draft: true.

    Kein cadence_wait: Damit bleiben die Entwürfe für die Kadenz-
    Automatik unsichtbar (cadence_guard fasst sie nie an). Veröffent-
    licht wird ausschließlich bewusst über ki_redaktion.py --promote.
    Die Tags werden an dieser letzten Writer-Grenze noch einmal gegen das
    Register geprüft (Defense-in-Depth gegen neue Crawl-URLs).

    Fachfreigabe-Vertrag (#734): Vor allem anderen wird die Bahn bestimmt –
    mit exakt dem Material, das das Redaktions-Gate später liest (Titel +
    die ersten zwei Keywords + Pillar). YMYL-Hochrisiko ohne Beauftragung
    wirft `FachfreigabeErforderlich`; jeder Entwurf trägt wie bei der
    Engine das Gerüst `redaktionelle_pruefung` (status „ausstehend“).
    """
    keywords = [k for k in (keywords or []) if k][:8]
    fachfreigabe_pruefen(title=title, keywords=keywords, pillar=pillar,
                         beauftragt=fachfreigabe)
    review_block = pruefgeruest(title, keywords, pillar)
    date = datetime.datetime.now(datetime.timezone.utc)
    date_str = date.strftime("%Y-%m-%dT%H:%M:%SZ")
    tags = _kanonische_frontmatter_tags(tags, pillar=pillar, title=title)
    tags = [t for t in tags if t][:5]
    fm = (
        "---\n"
        f"title: {yaml_str(title)}\n"
        f"description: {yaml_str(description)}\n"
        f"date: {date_str}\n"
        "draft: true\n"
        f"tags: {json.dumps(tags, ensure_ascii=False)}\n"
        + ('categories: ["News"]\n' if news else 'categories: ["Ratgeber"]\n')
        + (f'pillar: "{pillar}"\n' if pillar else "")
        + (f'keywords: {json.dumps(keywords, ensure_ascii=False)}\n'
           if keywords else "")
        + f"author: {yaml_str(AUTHOR)}\n"
        "ai_generated: true\n"
        f'ki_redaktion: "{rolle}"\n'
        'ki_redaktion_status: "review"\n'
        + (f'news_kategorie: "{kategorie}"\n' if news and kategorie else "")
    )
    if kurzantwort:
        fm += f"kurzantwort: {yaml_str(kurzantwort)}\n"
    fm += review_block
    fm += "---\n\n"
    return fm


def clip_text(text: str, max_len: int = 158) -> str:
    """Schneidet Text an einer Wortgrenze ab (nie mitten im Wort)."""
    text = text.strip()
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,;:-–") + " …"


def cta_block(affiliate_url: str | None = None, route: str = "",
              slug: str = "") -> str:
    """Affiliate-CTA + Werbekennzeichnung (Hausstil der Engine).

    REPARATUR 02.10.2026 (WF-D4E0, Issue #513): Diese Funktion schrieb
    bis heute die ROHE Partner-URL mit dem generischen Anker „Jetzt
    Angebote vergleichen“ – Link-Integrität (kein /go/-Redirect), IW8
    (Anker nennt kein Angebot) und IW3 („Vergleich“ vor Einzelangebot)
    verwarfen so jeden erzeugten Reserve-Kandidaten bei der Zertifizie-
    rung. Delegiert ab jetzt an scripts/cta_builder.py: Satz und Anker
    aus affiliate_intent_contract (eine Wahrheit mit der Intent-Wache),
    Ziel immer die /go/-Übergabeseite.
    """
    import cta_builder
    return cta_builder.cta_end_block(
        affiliate_url=affiliate_url, route=route, slug=slug)


def write_report(lines: list) -> None:
    """Statusreport ins Repo-Root schreiben (Konvention: *-REPORT.md)."""
    stamp = datetime.datetime.now(datetime.timezone.utc)
    head = [
        "# KI-REDAKTION-REPORT",
        "",
        f"_Stand: {stamp.strftime('%d.%m.%Y %H:%M UTC')} – automatisch "
        "durch scripts/ki_redaktion.py erzeugt._",
        "",
    ]
    with open(REPORT_FILE, "w", encoding="utf-8") as fh:
        fh.write("\n".join(head + lines).rstrip() + "\n")
