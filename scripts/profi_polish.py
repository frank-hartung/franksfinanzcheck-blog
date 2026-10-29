#!/usr/bin/env python3
"""
PROFI-POLISH-PASS – KI-Nachbearbeitung neuer Artikel.

Verwandelt einen frisch generierten Bot-Artikel in einen PROFI-TEXT:
  - KI-Floskeln & Füllformulierungen entfernen
  - Aktive, lebendige Sprache (kurze Sätze, starke Verben)
  - Einleitung mit Haken (Nutzen versprechen, Frage/Nr. aufwerfen)
  - Absätze auf 3–4 Sätze kürzen (Scannability)
  - Natürliche Keyword-Integration (kein Stuffing)
  - E-E-A-T-Sprache: Erfahrung, Praxisbezug, konkrete (plausible) Beispiele
  - Deutsche Orthografie (Großschreibung, korrekte Zeichen)

SICHERHEIT (Verifikation VOR dem Schreiben):
  - Alle Links bleiben erhalten (Affiliate-Links Pflicht)
  - Überschriften-Anzahl bleibt stabil
  - Länge ≥ 85 % des Originals
  - Frontmatter wird nie angefasst

Nutzung:
    python3 scripts/profi_polish.py --file X.md     # einzelnen Artikel
    python3 scripts/profi_polish.py --file X.md --include-drafts
                                                  # auch Entwürfe polieren
    python3 scripts/profi_polish.py --new           # alle Artikel ohne lastmod
    python3 scripts/profi_polish.py --all           # ALLE Artikel (auch manuelle)
    python3 scripts/profi_polish.py --dry-run       # ohne zu schreiben
"""
import os
import re
import sys
import json
import datetime

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS_DIR = os.path.join(BLOG_DIR, "content", "posts")
if os.path.join(BLOG_DIR, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
from post_utils import (list_post_paths, slug_of,  # noqa: E402
                        join_article, strip_generator_scaffolding)
import llm_client
CACHE_FILE = os.path.join(BLOG_DIR, ".polish_cache.json")

try:
    from publikations_vertrag import (pruefe as _vertrag_pruefe,
                                      raw_aus as _vertrag_raw_aus,
                                      _flesch as _vertrag_flesch,
                                      _harte_funde as _vertrag_harte_funde,
                                      verstoesse_kurz)
    import readability_check as _rc_guard
    import textverstaendnis_guard as _tv_guard
    _VERTRAG_FEHLER = ""
except Exception as _exc:  # noqa: BLE001 – fail-closed: ohne Vertrag kein Schreiben
    _vertrag_pruefe = None
    _vertrag_raw_aus = None
    _vertrag_flesch = None
    _vertrag_harte_funde = None
    verstoesse_kurz = None
    _rc_guard = None
    _tv_guard = None
    _VERTRAG_FEHLER = f"{_exc.__class__.__name__}: {_exc}"

try:
    import redaktions_standard as _rs_guard
except Exception:  # noqa: BLE001
    _rs_guard = None


def _stamm(slug: str) -> str:
    return re.sub(r"^\d{4}-\d{2}-\d{2}-", "", (slug or "").strip())


def load_article(path, include_drafts=False):
    with open(path, encoding="utf-8") as fh:
        content = fh.read()
    parts = content.split("---", 2)
    if len(parts) != 3:
        return None
    fm, body = parts[1], parts[2]
    if not include_drafts and "draft: true" in fm:
        return None

    def get(key):
        m = re.search(rf"^{key}:\s*[\"']?(.+?)[\"']?\s*$", fm, re.M)
        return m.group(1).strip() if m else ""

    anrede_raw = get("anrede").strip('"').lower()
    return {"path": path, "slug": slug_of(path), "fm": fm,
            "title": get("title"), "description": get("description"),
            "keywords": get("keywords"), "body": body,
            "anrede_sie": anrede_raw in ("sie", "sie-form", "höflich")}


def build_polish_prompt(a: dict) -> str:
    """Baut den Lektorats-Prompt (reine Funktion, vertragstestbar)."""
    kws_raw = a.get("keywords", "")
    kws = []
    if kws_raw.strip().startswith("["):
        kws = [k.strip().strip('"\'') for k in kws_raw.strip()[1:-1].split(",") if k.strip()]
    else:
        kws = [k.strip() for k in kws_raw.split(",") if k.strip()]
    kw_hint = ", ".join(kws[:4]) if kws else a.get("title", "")
    anrede_auftrag = ('"du" – der Leser wird geduzt (Blog-Stil)' if not a.get("anrede_sie")
                      else '"Sie" – dieser Artikel richtet sich bewusst an eine Zielgruppe, die gesiezt wird')
    anrede_pronomen = '("du"/"dein"/"dich")' if not a.get("anrede_sie") else '("Sie"/"Ihr"/"Ihnen")'

    return f"""Du bist Lektor für einen seriösen deutschen Finanz-Ratgeber-Blog (Profi-Niveau).
Poliere den folgenden Blog-Artikel auf PROFESSIONELLES Text-Niveau.

REGELN:
1. Entferne ALLE KI-Floskeln und Füllphrasen ("In der heutigen…", "Es ist wichtig zu beachten",
   "Zusammenfassend lässt sich sagen", "Des Weiteren", "Es gibt viele…", "heutzutage" usw.).
2. Schreibe in AKTIVER, lebendiger Sprache: kurze Sätze (max. ~20 Wörter), starke Verben,
   direkte Ansprache {anrede_auftrag} {anrede_pronomen}. Vermeide Passiv.
3. Einleitung: Beginne mit einem starken Haken (Nutzenversprechen, Alltags-Szene oder konkrete Frage) –
   KEINE Zahl und kein Euro-/Prozentwert im Einstieg ohne bereits eingeführte Modellrechnung.
4. Absätze auf 3-4 Sätze kürzen. Zwischenüberschriften beibehalten.
5. Baue die Keywords natürlich ein (kein Stuffing): {a.get('keywords', '')[:120]}
6. ZAHLEN-VERTRAG (RS5, hart): Erfinde KEINE neuen Zahlen, Preise, Prozentwerte oder Spannen.
   Ein bloßes „ca.", „rund" oder „in der Regel" gilt am Gate NICHT als Beleg und führt zur Ablehnung!
   Jede Zahl mit Einheit (€, %, kWh, Monate, Jahre) muss im SELBEN Satz als Modell-/Beispielrechnung
   („Beispielrechnung", „Modellrechnung", „Annahme", „Rechenbeispiel") gekennzeichnet sein oder einen
   klickbaren Quellenlink im selben Satz tragen. Wo keine Modellrechnung vorliegt, formuliere ohne Zahl.
7. Deutsche Orthografie: korrekte Groß-/Kleinschreibung, korrekte Anführungszeichen.
8. BEHALTE alle Links exakt bei (insbesondere https://a.check24.net, https://a.partner-versicherung.de,
   interne /go/-Links und interne Artikel-Links). Lösche KEINEN Link, ändere keine URL.
9. Behalte alle Überschriften (##, ###) inklusive Frage-Überschriften mit „?" und die FAQ-Fragen bei.
   Bewahre vorhandene Pflicht-Module (**Das Wichtigste in Kürze**, **Faustregel:**, nummerierte
   Schrittfolgen 1./2./3. und Modellrechnungen) vollständig!
10. Behalte Listen und Tabellen. WICHTIG: Der polierte Text muss mindestens 90% der
    Länge des Originaltextes haben. Kürze KEINE Absätze komplett weg – formuliere
    innerhalb der Absätze um. Nur Floskeln/Füllwörter dürfen entfallen.
11. Falls der Artikel KEINE Liste und KEINE Tabelle enthält, ergänze eine kurze
    Liste mit 4-6 Punkten (z. B. "Das Wichtigste in Kürze") an passender Stelle.
11b. LESBARKEIT (wichtig!): Zerlege Schachtelsätze (über 25 Wörter) in 2 kurze
    Sätze. Ersetze lange Wörter durch einfachere Alternativen (z. B. "die
    Erstattungsfähigkeit" → "ob die Kosten erstattet werden"). Vermeide
    Nominalstil ("die Übernahme der Kosten" → "die Kasse übernimmt die Kosten").
    Ziel: Ø Satzlänge unter 15 Wörter, Flesch-Score über 60.
11c. TEXTVERSTÄNDNIS (Verlagsregel, 01.09.2026): Ersetze die Schablone
    "In diesem Ratgeber zeige/erfährst/erkläre ich dir …" durch eine individuelle
    Öffnung (Schritt-Versprechen, Alltags-Irrtum, Analogie, Warnung,
    Mini-Geschichte, Checkliste, Frage – ohne unbelegte Zahl im Einstieg). Zerlege Komma-Ketten über 15 Begriffe in
    Tabellen oder Listen mit Erklärungen. Vereinheitliche Synonyme auf EINEN
    Leitbegriff pro Konzept (Synonyme nur einmal als Erklärung bei Ersterwähnung).
12. TOP-LEVEL-DARSTELLUNG: Jeder Absatz ist 3-4 Sätze lang, behandelt genau EINEN
    Gedanken und endet an einer sinnvollen Stelle (keine Textwände). Schreibe
    Wörter NIE mit Silbentrennung. Zwischen einer Zahl und ihrer Einheit steht
    IMMER ein geschütztes Leerzeichen (&nbsp;): 20&nbsp;%, 50&nbsp;€,
    100&nbsp;EUR – niemals "20 %" oder "50 €" mit normalem Leerzeichen.
    Leitet ein Gedankenstrich einen erläuternden Nachsatz ein (Muster:
    'Satz – Nachsatz'), beginnt der Nachsatz auf einer NEUEN Zeile
    (Markdown-Hard-Break: zwei Leerzeichen am Zeilenende).
12. GROSS-/KLEINSCHREIBUNG: Verwende die NORMALE deutsche Rechtschreibung – wie in
    einem Zeitungsartikel. Nur Satzanfänge und Substantive werden großgeschrieben,
    alle anderen Wörter klein (KEIN Titel-Stil, kein "Jedes Wort Groß").
    Nach jedem Satzendepunkt (! . ?) beginnt das nächste Wort mit einem Großbuchstaben.
    Achtung: "Du" wird nur am Satzanfang groß, im Satz klein ("du").
13. KEYWORDS: Diese Keywords müssen 1-2 Mal natürlich im Text vorkommen (kein Stuffing):
    {kw_hint}
    Das Haupt-Keyword (das erste) MUSS mindestens einmal im Text stehen.
14. Beginne den Text NICHT mit dem Artikel-Titel – der Titel steht bereits in der
    Überschrift der Seite. Starte direkt mit dem ersten Absatz.

TITEL: {a.get('title', '')}
DESCRIPTION: {a.get('description', '')[:100]}

ARTIKEL:
{a.get('body', '')}

Liefere NUR den vollständigen polierten Markdown-Text (ohne Frontmatter, ohne Erklärungen)."""


def ai_polish(a):
    """KI-Polish. Liefert neuen Body oder None."""
    key = slug_of(a["path"])  # eindeutig (Bundles: Ordnername, nicht "index.md"!)
    stamm = _stamm(key)
    cache = {}
    if os.path.exists(CACHE_FILE):
        try:
            cache = json.load(open(CACHE_FILE, encoding="utf-8"))
        except Exception:
            cache = {}
    if key in cache:
        return cache[key]
    if stamm and stamm in cache:
        return cache[stamm]

    if not (llm_client.available("gemini") or llm_client.available("groq")):
        print("  ⚠️ Keine API-Keys – kein Polish möglich.")
        return None

    prompt = build_polish_prompt(a)

    for provider in ("gemini", "groq"):
        if not llm_client.available(provider):
            continue
        try:
            text = llm_client.chat(
                provider, prompt=prompt,
                model="gemini-3-flash-preview" if provider == "gemini" else None,
                max_tokens=8000 if provider == "gemini" else 4000,
                timeout=120, attempts=3,
            )
            if text:
                cache[key] = text
                if stamm:
                    cache[stamm] = text
                json.dump(cache, open(CACHE_FILE, "w", encoding="utf-8"), ensure_ascii=False)
                return text
        except Exception as exc:
            print(f"  ⚠️ {provider.capitalize()}: {exc}")
    return None


# Abkürzungen, nach denen KEIN Großbuchstabe folgen muss
ABKUERZUNGEN = {
    "z.b", "z. b", "usw", "bzw", "d.h", "d. h", "u.a", "u. a", "etc", "ca",
    "inkl", "exkl", "zzgl", "vgl", "usf", "nr", "prof", "dr", "tel", "mo",
    "di", "mi", "do", "fr", "sa", "so", "geb", "ggf", "evtl", "sog", "bspw",
}


def fix_capitalization(text):
    """Deterministische Korrektur: Nach Satzendepunkt (! ? .) folgt ein
    Großbuchstabe – außer nach bekannten Abkürzungen (z. B., usw., bzw. …).
    Behebt das häufigste Qualitätsproblem von KI-Texten (kleine Satzanfänge)."""
    def repl(m):
        prefix, punct, space, lower = m.group(1), m.group(2), m.group(3), m.group(4)
        # Abkürzungs-Check: letztes Wort vor dem Punkt
        words = prefix.split()
        if words:
            last = words[-1].lower().rstrip(".")
            # Mehrteilige Abkürzungen wie "z. B." – letzte zwei Wörter prüfen
            if len(words) >= 2:
                combo = (words[-2] + " " + words[-1]).lower().rstrip(".")
                if combo in ABKUERZUNGEN or combo.replace(".", "") in ABKUERZUNGEN:
                    return m.group(0)
            if last in ABKUERZUNGEN or last.replace(".", "") in ABKUERZUNGEN:
                return m.group(0)
        return prefix + punct + space + lower.upper()

    # Buchstabe + .!? + Leerzeichen + Kleinbuchstabe
    return re.sub(r"([a-zäöüßA-ZÄÖÜ0-9\)\"])([.!?])(\s+)([a-zäöüß])", repl, text)


def fix_number_units(text):
    """Top-Level-Darstellung: Zahl + Einheit (% / € / EUR) mit geschütztem
    Leerzeichen (U+00A0) verbinden, damit nie getrennt umbrochen wird.
    HTML-Entities (&nbsp;) werden dabei normalisiert. Markdown-Links werden
    maskiert, damit URLs unangetastet bleiben."""
    link_re = re.compile(r"\[[^\]]*\]\([^)]*\)")
    num_unit_re = re.compile(r"(\d[\d.,]*)\s+(%|€|EUR)(?!\w)")
    text = re.sub(r"&nbsp;", "\u00a0", text)
    masked = link_re.sub(lambda m: " " * (m.end() - m.start()), text)
    out, last = [], 0
    for m in num_unit_re.finditer(masked):
        out.append(text[last:m.start()])
        out.append(m.group(1) + "\u00a0" + m.group(2))
        last = m.end()
    out.append(text[last:])
    return "".join(out)


def verify(a, new_body):
    """Sicherheits-Verifikation vor dem Schreiben (inkl. Publikations- & RS-Vertrag)."""
    problems = []
    orig_body = a.get("body", "")
    old_links = set(re.findall(r"https?://[^\s)\"']+", orig_body))
    new_links = set(re.findall(r"https?://[^\s)\"']+", new_body))
    old_aff = {l for l in old_links if "check24" in l or "partner-versicherung" in l}
    new_aff = {l for l in new_links if "check24" in l or "partner-versicherung" in l}
    if old_aff - new_aff:
        problems.append(f"Affiliate-Links verloren: {len(old_aff - new_aff)}")
    old_go = set(re.findall(r"\]\(\s*(/go/[a-z0-9_\-/]+/?)\s*\)", orig_body, re.I))
    new_go = set(re.findall(r"\]\(\s*(/go/[a-z0-9_\-/]+/?)\s*\)", new_body, re.I))
    if old_go - new_go:
        problems.append(f"/go/-Links verloren: {sorted(old_go - new_go)}")
    old_h = len(re.findall(r"^#{1,3} ", orig_body, re.M))
    new_h = len(re.findall(r"^#{1,3} ", new_body, re.M))
    if abs(old_h - new_h) > 2:
        problems.append(f"Überschriften {old_h}→{new_h}")
    if len(new_body) < len(orig_body) * 0.75:
        problems.append("zu stark gekürzt")

    # Publikations-Vertrag (V1 Flesch >= 60, V2 keine neuen harten Textverständnis-Funde)
    fm = a.get("fm") or f'title: "{a.get("title", "Check")}"\n'
    slug = a.get("slug") or (slug_of(a["path"]) if a.get("path") else "profi-polish-check")
    if _vertrag_pruefe is None or _vertrag_raw_aus is None:
        problems.append(f"Publikations-Vertrag nicht prüfbar ({_VERTRAG_FEHLER})")
    else:
        alt_raw = _vertrag_raw_aus(fm, orig_body)
        neu_raw = _vertrag_raw_aus(fm, new_body)
        verstoesse = _vertrag_pruefe(slug, alt_raw, neu_raw)
        if verstoesse:
            kurz = verstoesse_kurz(verstoesse) if verstoesse_kurz else "; ".join(str(v) for v in verstoesse)
            problems.append(f"Publikations-Vertrag: {kurz}")

    # Redaktions-Standard-Schutz (WF-D4E0 #710): Lektorat darf weder Pflicht-Module
    # (RS1 Kurzfassung, RS2 Frage-H2, RS3 Faustregel, RS4 Schrittfolge) löschen noch
    # neue unbelegte Zahlenbehauptungen (RS5) oder Phantom-Quellen (RS6) einführen.
    if _rs_guard is not None:
        vorher_rs = _rs_guard.reserve_quality_findings(orig_body)
        nachher_rs = _rs_guard.reserve_quality_findings(new_body)
        vorher_klassen = {f.split(":", 1)[0].strip() for f in vorher_rs}
        nachher_klassen = {f.split(":", 1)[0].strip() for f in nachher_rs}
        neue_klassen = sorted(nachher_klassen - vorher_klassen)
        if neue_klassen:
            problems.append(f"Redaktions-Standard-Regression ({', '.join(neue_klassen)})")
        vorher_rs5 = len(_rs_guard._reserve_numeric_claim_findings(orig_body))
        nachher_rs5 = len(_rs_guard._reserve_numeric_claim_findings(new_body))
        if nachher_rs5 > vorher_rs5:
            problems.append(f"RS5-Zahlenbehauptungen erhöht ({vorher_rs5}→{nachher_rs5})")
    return problems


def _already_gate_clean(a: dict) -> bool:
    """True, wenn der Entwurf bereits Flesch >= 60, 0 harte Textverständnis-Funde
    und 0 Redaktions-Standard-Funde hat (Idempotenz in der Reserve-Heilerkette)."""
    if (_vertrag_raw_aus is None or _vertrag_flesch is None
            or _vertrag_harte_funde is None or _rs_guard is None
            or _rc_guard is None or _tv_guard is None):
        return False
    orig_body = a.get("body", "")
    fm = a.get("fm") or f'title: "{a.get("title", "Check")}"\n'
    slug = a.get("slug") or (slug_of(a["path"]) if a.get("path") else "profi-polish-check")
    raw = _vertrag_raw_aus(fm, orig_body)
    flesch = _vertrag_flesch(raw, slug)
    if flesch is None or flesch < _rc_guard.NEW_FLESCH_MIN:
        return False
    if _vertrag_harte_funde(raw, slug, _tv_guard.load_terminologie()):
        return False
    if _rs_guard.reserve_quality_findings(orig_body):
        return False
    return True


def run_selftest() -> int:
    errors = []
    sample = {
        "path": "",
        "slug": "2026-10-12-test-artikel",
        "fm": 'title: "Stromkosten senken: Kluge Tipps im Alltag"\nauthor: "Frank Hartung"\n',
        "title": "Stromkosten senken: Kluge Tipps im Alltag",
        "description": "So senkst du deine Stromkosten im Alltag.",
        "keywords": '["Stromkosten senken", "Haushalt"]',
        "body": (
            "Willst du im Alltag einfach Geld sparen? Kurze Wege helfen dir sofort. "
            "Du behältst dein Konto jeden Monat sicher im Griff.\n\n"
            "**Das Wichtigste in Kürze**\n"
            "- Erster klarer Punkt für dein Budget.\n"
            "- Zweiter klarer Punkt für deine Rechnung.\n"
            "- Dritter klarer Punkt für deinen Vertrag.\n\n"
            "## Warum steigen deine Kosten im Haushalt?\n\n"
            "Alte Geräte ziehen im Leerlauf ständig Strom. Ein Schalter stoppt diesen "
            "Verbrauch sofort. [Jetzt Strom vergleichen](/go/strom/)\n\n"
            "**Faustregel:** Trenne ungenutzte Geräte abends komplett vom Netz.\n\n"
            "## Wie gehst du Schritt für Schritt vor?\n\n"
            "1. Prüfe deine letzte Abrechnung in Ruhe.\n"
            "2. Miss große Geräte mit einem Stecker.\n"
            "3. Wechsle rechtzeitig in einen fairen Tarif.\n"
        ) * 6,
    }
    prompt = build_polish_prompt(sample)
    if "ca. X–Y €" in prompt or "konkrete Zahl" in prompt:
        errors.append("build_polish_prompt enthält noch alte RS5-widrige Zahlen-Anweisung")
    if "Beispielrechnung" not in prompt or "Faustregel" not in prompt:
        errors.append("build_polish_prompt nennt Beispielrechnung/Faustregel-Schutz nicht")
    if verify(sample, sample["body"]):
        errors.append(f"verify lehnt sauberen Ausgangstext ab: {verify(sample, sample['body'])}")
    # Regression 1: Faustregel gelöscht (RS3) + unbelegte Zahl eingeführt (RS5)
    kaputt_rs = sample["body"].replace("**Faustregel:**", "Hinweis:") + (
        "\n\nEin fehlender Ausweis kostet dich bis zu 15.000 € Bußgeld.\n"
    )
    prob_rs = verify(sample, kaputt_rs)
    if not any("Redaktions-Standard" in p or "RS5" in p for p in prob_rs):
        errors.append(f"verify erkennt RS3/RS5-Regression nicht: {prob_rs}")
    # Regression 2: /go/-Link verloren
    kaputt_go = sample["body"].replace("(/go/strom/)", "(/kontakt/)")
    prob_go = verify(sample, kaputt_go)
    if not any("/go/-Links" in p for p in prob_go):
        errors.append(f"verify erkennt verlorenen /go/-Link nicht: {prob_go}")
    if errors:
        print("profi_polish selftest FAILED:")
        for e in errors:
            print(f"  - {e}")
        return 1
    print("profi_polish selftest OK (Prompt-Vertrag, Publikations-Vertrag, RS3/RS5- & /go/-Schutz).")
    return 0


def write_polished(a, new_body):
    from editorial_review_gate import automatic_write_protected
    if automatic_write_protected(a["path"]):
        print("  YMYL: Politur verworfen – redaktionelle Prüfung erforderlich")
        return False
    content = a["path"] and open(a["path"], encoding="utf-8").read()
    parts = content.split("---", 2)

    # Prompt-Gerüst-Schutz (18.09.2026): Modelle spiegeln gern den Kopf des
    # Auftrags („TITEL: …\n\nARTIKEL:\n\n…"). Das ist kein Artikeltext – es
    # stand in einem Live-Artikel (7b51187) über der ersten Zeile.
    new_body, geruest = strip_generator_scaffolding(new_body)
    if geruest:
        print(f"  ⚠ Prompt-Gerüst der KI-Antwort entfernt "
              f"({len(geruest)} Zeile(n): {geruest[0].strip()[:40]!r})")

    # Titel-Duplikat-Schutz: Wenn die KI den Titel als erste Zeile wiederholt,
    # entfernen (der Titel steht bereits im Frontmatter/als Seiten-Titel).
    first_line = new_body.strip().split("\n", 1)[0].strip()
    title_norm = re.sub(r"[#*_]", "", a["title"]).strip().lower()
    first_norm = re.sub(r"[#*_]", "", first_line).strip().lower()
    if first_norm == title_norm or first_norm == title_norm + ":":
        new_body = new_body.strip().split("\n", 1)[1].lstrip()

    # Naht über die SSOT: Ein gestripptes Body-Fragment kann so keine
    # Klebefuge mehr erzeugen (genau daran sind am 17.09. neun Dateien
    # gescheitert – `"---" + fm + "---" + new_body` klebt ohne Umbruch).
    content = join_article(parts[1], new_body, parts[0])
    open(a["path"], "w", encoding="utf-8").write(content)


def main():
    if "--selftest" in sys.argv:
        sys.exit(run_selftest())
    dry = "--dry-run" in sys.argv
    mode_new = "--new" in sys.argv
    mode_all = "--all" in sys.argv
    include_drafts = "--include-drafts" in sys.argv

    files = []
    if "--file" in sys.argv:
        files = [sys.argv[sys.argv.index("--file") + 1]]
    elif mode_new:
        # Nur Artikel VON HEUTE (date == heute, draft: false) – so verschwendet
        # der tägliche Workflow keine Zeit/Quota mit alten, nie gepolisheden
        # Artikeln (die z. B. wegen Affiliate-Link-Schutz verworfen werden).
        today = datetime.date.today().isoformat()
        for f in list_post_paths():
            c = open(f, encoding="utf-8").read()
            fm = c.split("---", 2)[1] if c.startswith("---") and c.count("---") >= 2 else ""
            if today in fm and "draft: false" in fm:
                files.append(f)
    else:
        files = list_post_paths()

    polished, failed, skipped = [], [], 0
    import time
    for idx, path in enumerate(files):
        a = load_article(path, include_drafts=include_drafts)
        if not a:
            skipped += 1
            continue
        # Standard: nur Bot-Artikel polieren (ai_generated).
        # --all: AUCH manuelle Artikel polieren (Profi-Niveau für alles).
        if not mode_all:
            content = open(path, encoding="utf-8").read()
            if "ai_generated: true" not in content:
                skipped += 1
                continue
        if include_drafts and _already_gate_clean(a):
            print(f"  [{idx+1}/{len(files)}] ⏭ Bereits gate-konform (Flesch ≥ 60 & RS1–RS7 grün): {a['slug']}")
            skipped += 1
            continue
        print(f"  [{idx+1}/{len(files)}] → {os.path.basename(path)[:50]}…", flush=True)
        new_body = ai_polish(a)
        if not new_body:
            failed.append(os.path.basename(path))
            continue
        # Deterministischer Auto-Fix: Großschreibung nach Satzpunkten
        new_body = fix_capitalization(new_body)
        # Top-Level-Darstellung: Zahl+Einheit mit &nbsp; verbinden (% / € / EUR)
        new_body = fix_number_units(new_body)
        problems = verify(a, new_body)
        if problems:
            print(f"    ❌ Verworfen: {'; '.join(problems)}")
            failed.append(os.path.basename(path))
            continue
        if not dry:
            write_polished(a, new_body)
        polished.append(os.path.basename(path))
        print(f"    ✅ Poliert ({len(new_body)} Zeichen)", flush=True)
        # Rate-Limit-Schonung: kurze Pause zwischen KI-Calls (mehrere Artikel)
        if not dry and len(files) > 1:
            time.sleep(2)

    print(f"\nFertig: {len(polished)} poliert, {len(failed)} fehlgeschlagen, "
          f"{skipped} übersprungen (manuell/Entwurf).")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
