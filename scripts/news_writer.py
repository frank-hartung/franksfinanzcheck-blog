#!/usr/bin/env python3
# ============================================================
#  KI-REDAKTION – Rolle 2 „CHATGPT": schnelle News
#  ------------------------------------------------------------
#  Bildet den ChatGPT-Part des Schemas „ChatGPT Plus für schnelle
#  News" mit gleichem Funktionsumfang ab: zügig produzierte,
#  kompakte News-Artikel zu aktuellen Anlässen.
#
#  KOSTEN-REGEL: Es laufen AUSSCHLIESSLICH Gratis-Zugänge
#  (Groq → NVIDIA → Cloudflare → Gemini). Seit 03.10.2026 gibt es
#  keinen kostenpflichtigen Pfad mehr – das frühere Opt-in auf die
#  OpenAI-API ist ersatzlos entfernt. „Rolle ChatGPT" ist ein
#  REDAKTIONELLER Rollenname (schnelle News), kein Anbieter: Das
#  Modell dahinter ist openai/gpt-oss-120b, OpenAIs offenes Modell,
#  kostenlos bei drei Hostern.
#
#  ANTI-HALLUZINATION (YMYL-Finanzen, Haftungsschutz):
#  „Aktualität" kommt ausschließlich aus dem KURATIERTEN Pool
#  data/aktuelle_entwicklungen.yaml (von Menschen geprüft). Die KI
#  erfindet keine Meldungen, keine Zahlen, keine Zitate – sie
#  verarbeitet nur den kuratierten Aufhänger. Deshalb braucht die
#  Automatik auch kein teures Live-Web-Monitoring.
#
#  Länge: Auch News erfüllen den Repo-Floor von 10.000 Zeichen
#  (length_policy) – Format „News-Kompakt": Meldung + Einordnung +
#  Betroffenheit + Checkliste + FAQ + Ausblick.
#
#  Ergebnis ist IMMER ein Entwurf (draft: true, kein cadence_wait).
#
#  FACHFREIGABE-VERTRAG (seit 13.10.2026, Dauerheilung #734): Die
#  Automatik schreibt nur Aufhänger der AUTO-Bahn. Ein YMYL-Aufhänger
#  (z. B. Kategorie „versicherung“) wird übersprungen, NICHT verbraucht
#  und bleibt für eine bewusste Beauftragung im Pool. Ebenso übersprungen:
#  Aufhänger, deren Titel es im Bestand schon gibt (der Kategorie-Titel
#  „<Kategorie>-Update: Was sich jetzt für dich ändert“ ist pro Kategorie
#  nur einmal frei – ein eigener Titel kommt über das Feld `titel:` im
#  Pool).
#
#  Nutzung:
#    python3 scripts/news_writer.py                 # nächster Aufhänger
#    python3 scripts/news_writer.py --offline       # ohne KI-API
#    python3 scripts/news_writer.py --kategorie energie
#    python3 scripts/news_writer.py --kategorie versicherung --fachfreigabe
#                                   # YMYL bewusst beauftragen (WIP-Limit)
# ============================================================
from __future__ import annotations

import argparse
import datetime
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import ki_shared as ks  # noqa: E402
import llm_client  # noqa: E402
# SSOT für das Generator-Gerüst (Issue #490), identisch mit content_audit C7.
from content_audit import C7_SCAFFOLD_RE  # noqa: E402

try:
    import length_policy
except Exception:  # noqa: BLE001
    length_policy = None

# Lesbarkeits-SSOT + Heiler (Issue #712): Der Schreiber prüft, was über ihn
# entscheidet – dieselbe Lehre wie WF-D4E0/#612. Vorher schrieb diese Rolle
# News-Kompakt-Artikel in die Ablage, ohne die Publish-Schwelle überhaupt zu
# messen: Der Entwurf „Energie-Update“ vom 08.10.2026 landete mit Flesch 38,2
# im Vorrat, blockierte dort zwei Tage das Endredaktions-Gate und erzeugte den
# Governance-Befund #712. Was der Schreiber nicht misst, muss die Nachsorge
# aufräumen – messen ist billiger.
try:
    import readability_check as rc
    import lesbarkeit_heiler as lesbarkeit_heiler
except Exception:  # noqa: BLE001 – fehlende Messung darf den Lauf nicht töten
    rc = None
    lesbarkeit_heiler = None

# Die Schreiber-Garantie liegt seit #806 im eigenen Modul: eine Messung, eine
# Heilung, ein Tor – für ALLE Schreiberbahnen (Rolle „ChatGPT/News“, Rolle
# „Claude“, Werkbank-Recycling). Vorher hatte nur diese Rolle eine Sicherung;
# die beiden anderen schrieben ungemessen in den Vorrat (Issue #806).
try:
    import lesbarkeit_schreiber
except Exception:  # noqa: BLE001 – ohne Garantie meldet der Aufruf ehrlich
    lesbarkeit_schreiber = None

ROLLE = "chatgpt"

# ============================================================
#  HAUS-FORMEL DER NEWS-KOMPAKT-DATELINE (SSOT, Dauerheilung #676)
#  ------------------------------------------------------------
#  Diese Zeile schreibt die Engine ABSICHTLICH in jeden News-Kompakt-
#  Artikel – sie ist Format (Dateline + Einordnungsauftrag), kein
#  redaktioneller Inhalt. Bis zum 09.10.2026 stand sie als f-string
#  mitten in `main()`: Damit war sie für keine andere Wache als
#  Konstante greifbar, und duplikat_guard maß sie über Artikel hinweg
#  als D4-X-Fast-Duplikat (Ratio 0.98, `markt-update` ≈ `energie-update`,
#  Unterschied nur das Datum). RD1-duplikate ist in der Release-Scorecard
#  blockierend – derselbe Widerspruch wie beim Haus-CTA, dieselbe
#  eingefrorene Auslieferung (Issue #676).
#
#  Jetzt ist die Formel eine benannte Konstante und duplikat_guard leitet
#  ihr Vergleichsmuster DARAUS ab (`haus_formeln()`): Ein Platzhalter wird
#  zur Wildcard, alles andere bleibt literal. Eine neue Haus-Formel muss
#  also nur hier entstehen – die Duplikat-Messung kennt sie automatisch.
# ============================================================
STAND_INTRO = (
    "**Stand: {today}.** Dieser News-Kompakt-Artikel ordnet eine "
    "aktuelle Entwicklung ein. Konditionen und Regeln können sich "
    "ändern – prüfe Details immer beim jeweiligen Anbieter.\n\n"
)

SYSTEM_PROMPT = """Du bist der News-Desk von FranksFinanzcheck: schnell, \
präzise, verlässlich – wie eine seriöse deutsche Wirtschaftsredaktion. \
Du schreibst einen News-Kompakt-Artikel.

HARTE REGELN (Verstoß = unbrauchbar):
1. Deutsch, direkte Du-Ansprache, newsiger Ton (kurze Sätze, aktiv).
1a. LESBARKEIT IST EIN MESSWERT, keine Stimmung: Ziel ist Flesch-Amstad \
≥ 60 (deutsch). Die Formel lautet 180 − Ø Satzlänge − 58,5 · Silben je Wort. \
Das heißt praktisch: höchstens 14 Wörter pro Satz, ein Gedanke pro Satz, \
und KEINE langen Komposita, wo ein kurzes Alltagswort reicht \
(„Stromanbieterwechsel“ → „Wechsel“, „Verbrauchsmuster“ → „Verbrauch“, \
„Vertragsbedingungen“ → „Bedingungen“). Nominalstil in Verben auflösen \
(„die Übernahme der Kosten“ → „die Kasse zahlt“). Wer schachtelt, wird \
nachgemessen und verworfen.
2. ERFINDE NIEMALS Fakten: keine Daten, keine Prozentzahlen, keine \
Unternehmensmeldungen, keine Zitate, keine Paragraphen. Einziger \
Faktenanker ist der kuratierte AUFHÄNGER im Brief – paraphrasiere ihn \
natürlich, dichte nichts hinzu.
3. Wo Unklarheit herrscht, schreibe ehrlich „prüfe die Details bei \
deinem Anbieter" statt Zahlen zu erfinden.
4. Keine Panikmache, keine Übertreibung, kein Clickbait. Keine Emojis \
im Fließtext.

STRUKTUR (exakt so, mit ## -Überschriften):
- Teaser: 2-3 Sätze, die den Anlass auf den Punkt bringen (ohne Überschrift)
- ## Was ist passiert? (der kuratierte Aufhänger, sauber eingeordnet)
- ## Was bedeutet das für dich? (konkrete Alltags-Betroffenheit)
- ## Was du jetzt konkret tun kannst (nummerierte Liste, 4-6 Punkte)
- ## Hintergrund: So funktioniert der Markt dahinter (2-3 Absätze, \
zeitloses Wissen, als Faustregeln gekennzeichnet)
- ## FAQ – die wichtigsten Fragen zur Meldung (4 Fragen als ###)
- ## Ausblick: So geht es weiter (1 Absatz, vorsichtig formuliert)

ZIEL: {ziel} Zeichen Fließtext (Minimum {min_z} Zeichen, Maximum {max_z}). \
Schreibe den Artikel JETZT vollständig als Markdown OHNE Frontmatter, \
OHNE Titel-Zeile (# ...)."""


def _brief(hook: dict, keywords: list) -> str:
    return "\n\n".join([
        "AUFGÄNGER (kuratiert, einziger Faktenanker – nichts hinzuerfinden): "
        + hook.get("hook", ""),
        f"KATEGORIE: {hook.get('kategorie', '')}",
        ("SEO-KEYWORDS (natürlich einflechten): " + ", ".join(keywords))
        if keywords else "",
        "REGEL: Der Aufhänger beschreibt einen allgemeinen Marktmechanismus. "
        "Behandle ihn als Anlass, nicht als Eilmeldung mit konkretem Datum.",
    ])


def _generate(chain: list, system: str, prompt: str,
              model: str | None) -> tuple[str | None, str]:
    for prov in chain:
        text = llm_client.chat(prov, prompt=prompt, system=system,
                               model=model, temperature=0.45,
                               max_tokens=8192, timeout=240)
        if text and len(text) > 1500:
            return text, prov
        if text:
            print(f"  ⚠ Antwort von {prov} zu kurz ({len(text)} Z.) – "
                  "nächster Provider.")
    return None, ""


def _strip_fences(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```[a-z]*\s*", "", t)
        t = re.sub(r"\s*```$", "", t)
    t = re.sub(r"(?m)^#\s+.+$", "", t, count=1)
    # Prompt-Echo entfernen (Issue #490): Auch dieser Prompt übergibt eine
    # „ARTIKEL-TITEL:“-Zeile; echo-t das Modell sie, stünde sie als erste
    # sichtbare Zeile im Artikel. Gleiche Marke wie content_audit C7 –
    # ein Muster, eine Wahrheit.
    t = C7_SCAFFOLD_RE.sub("", t)
    return t.strip()


def _measure(text: str) -> int:
    if length_policy is not None:
        try:
            return length_policy.measure(text)[1]
        except Exception:  # noqa: BLE001
            pass
    return len(re.sub(r"\s+", " ", text).strip())


def _flesch_von(content: str, slug: str) -> float | None:
    """Flesch-Amstad über die Mess-SSOT (readability_check). None = nicht messbar."""
    if rc is None:
        return None
    try:
        satz = rc.parse_article(content, f"{slug}/index.md")
        return rc.analyze(satz)["flesch"] if satz else None
    except Exception:  # noqa: BLE001 – ohne Messung bleibt der Lauf ehrlich
        return None


def lesbarkeit_sichern(content: str, slug: str) -> tuple[str, float | None, str]:
    """Misst die Lesbarkeit VOR dem Schreiben und heilt deterministisch nach.

    Rückgabe: (content – ggf. geheilt, Flesch, Statusmeldung).

    Warum hier und nicht nur in der Nachsorge: Ein Generator, der seine
    Schwelle nicht kennt, produziert Ausschuss, den drei Wachen später
    einsammeln müssen (Publish-Gate, Endredaktion, Lesbarkeits-Wache). Der
    Heiler läuft als BIBLIOTHEK mit seinem Tor T1–T4 – er schreibt nur, was
    die importierte Schwelle wirklich erreicht; ohne API, ohne Netz.

    Die Nachsorge bleibt zuständig, wenn die deterministische Stufe nicht
    reicht (Flesch < 60 nach dem Lauf): Dann steht die Zahl ehrlich im Log,
    und `endredaktion.py` bzw. `lesbarkeit_heiler.py --entwuerfe` heilen
    redaktionell nach. Ein stiller Ausschuss ist die einzige verbotene Sorte.

    SEIT #806 liegt die Umsetzung in `scripts/lesbarkeit_schreiber.py` – dort
    liegt sie für ALLE Schreiberbahnen (Rolle „Claude“, Werkbank-Recycling).
    Diese Hülle reicht den Modulzustand durch, damit eine Sabotage im Test
    sichtbar bleibt; der Vertrag C41 prüft beide Seiten.
    """
    if lesbarkeit_schreiber is None:
        return content, None, "Lesbarkeits-Messung nicht verfügbar (Modul fehlt)"
    return lesbarkeit_schreiber.sichern(content, slug, rc_mod=rc,
                                       heiler=lesbarkeit_heiler)


def offline_skeleton(hook: dict) -> str:
    return f"""<!-- OFFLINE-GERÜST der KI-Redaktion (Rolle ChatGPT/News): Struktur steht,
Inhalt fehlt – API-Key nötig oder manuell fertigstellen. -->

{hook.get('hook', '')}

## Was ist passiert?

<!-- TODO(KI-REDAKTION/chatgpt): Aufhänger einordnen, keine erfundenen Fakten. -->

## Was bedeutet das für dich?

<!-- TODO(KI-REDAKTION/chatgpt): Alltags-Betroffenheit konkret beschreiben. -->

## Was du jetzt konkret tun kannst

1. <!-- TODO -->
2. <!-- TODO -->
3. <!-- TODO -->

## Hintergrund: So funktioniert der Markt dahinter

<!-- TODO(KI-REDAKTION/chatgpt): zeitloses Wissen als Faustregeln. -->

## FAQ – die wichtigsten Fragen zur Meldung

### Lohnt sich das Handeln sofort?

<!-- TODO(KI-REDAKTION/chatgpt): ehrliche, vorsichtige Antwort. -->

## Ausblick: So geht es weiter

<!-- TODO(KI-REDAKTION/chatgpt): vorsichtig formuliert, ohne Datums-Prognosen. -->
"""


def plane_artikel(hook: dict, args) -> dict:
    """Was würde aus diesem Aufhänger geschrieben? (ohne Generierung)

    Titel, Keywords und Pillar entstehen hier GENAU EINMAL – dieselben
    Werte prüft `waehle_aufhaenger` gegen Bahn und Bestand und bekommt
    später `build_frontmatter`. Zwei Rechenwege für dasselbe Material wären
    zwei Wahrheiten.
    """
    kategorie = hook.get("kategorie", "saisonal")
    title = (getattr(args, "title", None) or hook.get("titel")
             or f"{_kategorie_wort(kategorie)}-Update: "
                f"Was sich jetzt für dich ändert").strip()
    roh = getattr(args, "keywords", None)
    keywords = ([k.strip() for k in roh.split(",") if k.strip()]
                if roh else [])
    return {
        "hook": hook,
        "kategorie": kategorie,
        "title": title,
        "keywords": keywords,
        # Material des Redaktions-Gates: Titel + die ersten zwei Keywords
        # des Frontmatters – ohne eigene Keywords steht dort der Titel.
        "fm_keywords": keywords or [title],
        "pillar": _kategorie_pillar(kategorie),
    }


def waehle_aufhaenger(args, *, kandidaten: list | None = None,
                      ist_vergeben=None,
                      lage: dict | None = None) -> tuple[dict | None, list[str]]:
    """Erster Aufhänger, den diese Rolle schreiben DARF – plus Begründungen.

    Übersprungen (und NICHT verbraucht) werden:
      * Dubletten: Den Artikel gibt es im Bestand schon (Titel oder Slug,
        `ks.titel_vergeben`). Am 13.10.2026 entstand so ein zweites
        „Versicherung-Update: Was sich jetzt für dich ändert“ neben dem
        freigeprüften Entwurf vom 17.09.
      * FACHFREIGABE ohne Beauftragung bzw. bei geschlossenem WIP-Limit
        (`ks.fachfreigabe_pruefen`, Dauerheilung #734).
    """
    if kandidaten is None:
        kandidaten = ks.news_hook_kandidaten(kategorie=args.kategorie)
    if ist_vergeben is None:
        titel, slugs = ks.existing_titles(), ks.bestands_slugs()

        def ist_vergeben(t):
            return ks.titel_vergeben(t, titel=titel, slugs=slugs)
    beauftragt = bool(getattr(args, "fachfreigabe", False))
    gruende: list[str] = []
    for hook in kandidaten:
        plan = plane_artikel(hook, args)
        hid = hook.get("id") or "?"
        if ist_vergeben(plan["title"]):
            gruende.append(
                f"`{hid}`: Titel „{plan['title']}“ gibt es im Bestand schon – "
                "eine Dublette würde nur kannibalisieren. Eigenen Titel im "
                "Pool setzen (Feld `titel:`).")
            continue
        try:
            plan["bahn"] = ks.fachfreigabe_pruefen(
                title=plan["title"], keywords=plan["fm_keywords"],
                pillar=plan["pillar"], beauftragt=beauftragt, lage=lage)
        except ks.FachfreigabeErforderlich as exc:
            gruende.append(f"`{hid}`: {exc}")
            continue
        return plan, gruende
    return None, gruende


def run(args) -> int:
    cfg = ks.load_config()
    limits = cfg.get("zeichenvorgabe_news", {})
    min_z = int(limits.get("min", 10500))
    ziel = int(limits.get("ziel", 12000))
    max_z = int(limits.get("max", 15000))

    plan, uebersprungen = waehle_aufhaenger(args)
    for grund in uebersprungen:
        print(f"⏭ Aufhänger übersprungen (bleibt im Pool): {grund}")
    if not plan:
        if uebersprungen:
            print("❌ Kein Aufhänger, den die Automatik schreiben darf – "
                  "siehe Gründe oben. Nichts verbraucht, nichts geschrieben.")
        else:
            print("❌ Kein gültiger, unverbrauchter News-Aufhänger in "
                  "data/aktuelle_entwicklungen.yaml – bitte Pool nachpflegen "
                  "(Anti-Halluzinations-Regel: nichts Erfundenes).")
        return 1

    hook = plan["hook"]
    kategorie = plan["kategorie"]
    title = plan["title"]
    keywords = plan["keywords"]
    ymyl = plan["bahn"] == ks.BAHN_FACHFREIGABE
    today = datetime.date.today().strftime("%d.%m.%Y")

    if args.offline:
        body, provider = offline_skeleton(hook), "offline"
    else:
        chain = list(cfg.get("anbieter_kette_news") or ["groq", "gemini"])
        if args.provider:
            chain = [args.provider]
        system = SYSTEM_PROMPT.format(min_z=min_z, ziel=ziel, max_z=max_z)
        if ymyl:
            system += ks.YMYL_ARBEITSAUFTRAG
        prompt = _brief(hook, keywords) + (
            f"\n\nARTIKEL-TITEL: {title}\nSchreibe jetzt den vollständigen "
            f"News-Kompakt-Artikel (Ziel: ca. {ziel} Zeichen).")
        body, provider = _generate(chain, system, prompt, args.model)
        if not body:
            print("⚠ Kein Gratis-Provider erreichbar – Offline-Gerüst wird "
                  "als Entwurf gespeichert (Pipeline bleibt lauffähig).")
            body, provider = offline_skeleton(hook), "offline"
        else:
            body = _strip_fences(body)

    description = ks.clip_text(
        f"{title} – aktuelle Einordnung von FranksFinanzcheck: was "
        "passiert ist, was es für dich bedeutet und was du jetzt tun kannst.")
    fm = ks.build_frontmatter(
        title=title, description=description,
        # `build_frontmatter` übernimmt die Register-Kanonisierung; die
        # Keywords werden nicht direkt in URL-erzeugende Tags kopiert.
        tags=keywords or [title, _kategorie_wort(kategorie)],
        pillar=plan["pillar"],
        keywords=plan["fm_keywords"], rolle=ROLLE, news=True,
        kategorie=kategorie,
        # Zweite Prüfung an der Schreibgrenze (Defense in Depth, #734).
        fachfreigabe=bool(getattr(args, "fachfreigabe", False)))
    stand = STAND_INTRO.format(today=today)
    # Der Tail (CTA + Disclaimer) ist KEIN Fließtext: Er bleibt beim Messen
    # und Heilen draußen – sonst meldet der Schreiber eine Länge, die er nur
    # mit Werbeblock erreicht (dieselbe Ehrlichkeit wie `length_policy`).
    tail = ""
    if provider != "offline":
        tail = ("\n\n" + ks.cta_block() + "\n" + ks.DISCLAIMER + "\n")
    rumpf = fm + stand + body

    slug = ks.unique_bundle_slug(title)

    # LESBARKEITS-GATE VOR DEM SCHREIBEN (Issue #712): messen, deterministisch
    # heilen (Tor T1–T4 des Lesbarkeits-Heilers), dann erst schreiben. Der
    # Befund steht in jedem Fall im Log – auch die ehrliche Restlücke.
    if provider != "offline":
        rumpf, flesch, lesbarkeit_status = lesbarkeit_sichern(rumpf, slug)
    else:
        flesch, lesbarkeit_status = None, "Offline-Gerüst – keine Messung"
    content = rumpf + tail
    # Für die Meldung zählt derselbe Ausschnitt wie bisher (`stand + body`):
    # die Heilung kann Sätze geteilt haben, also den Body neu abgrenzen.
    kern = rumpf.split("---", 2)[2] if rumpf.startswith("---") else rumpf
    if kern.startswith(stand):
        kern = kern[len(stand):]

    import post_utils  # noqa: E402
    path = post_utils.write_post(slug, content)
    ks.mark_news_hook_used(hook.get("id", ""))

    chars = _measure(stand + kern)
    print(f"✅ Rolle ChatGPT (News): Entwurf „{title}“")
    print(f"   Pfad: {os.path.relpath(path, BLOG_DIR)}")
    print(f"   Provider: {provider} | Fließtext: {chars:,} Zeichen "
          f"(Ziel {ziel:,}) | Aufhänger: {hook.get('id')}")
    print(f"   Lesbarkeit: {lesbarkeit_status}")
    if ymyl:
        print("   ⚖ YMYL beauftragt: Prüfgerüst gesetzt (status „ausstehend“). "
              "Vor --promote: Prüfer, Belegkette, Zahlenprotokoll, --seal "
              "(docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md).")
    if chars < min_z and provider != "offline":
        print(f"   ⚠ Unter Floor ({min_z:,}) – vor --promote prüfen!")
    if (flesch is not None and rc is not None and flesch < rc.NEW_FLESCH_MIN
            and provider != "offline"):
        print("   ⚠ Unter der Publish-Schwelle – Nachsorge nötig "
              "(`python3 scripts/endredaktion.py --slug "
              f"{slug}` oder `python3 scripts/lesbarkeit_heiler.py "
              "--entwuerfe`)")
    ks.write_report([
        f"- **Letzter Lauf (Rolle ChatGPT/News):** Entwurf „{title}“ "
        f"({provider}, {chars:,} Zeichen, Aufhänger `{hook.get('id')}`) "
        "– Status: Review erforderlich.",
        f"- Pfad: `{os.path.relpath(path, BLOG_DIR)}`",
        f"- Lesbarkeit: {lesbarkeit_status}",
        "- Veröffentlichung: NIE automatisch – Freigabe über "
        "`python3 scripts/ki_redaktion.py --promote <slug>`.",
    ])
    return 0


def _kategorie_wort(kategorie: str) -> str:
    return {"energie": "Energie", "versicherung": "Versicherung",
            "konto": "Konto & Karten", "internet": "Internet & DSL",
            "saisonal": "Saison", "seo_qualitaet": "Markt"}.get(
                kategorie, "Markt")


def _kategorie_pillar(kategorie: str) -> str:
    """Ordnet News dem bestehenden Register-Silo zu, ohne einen Tag zu erfinden."""
    return {
        "energie": "strom-sparen",
        "versicherung": "versicherungen",
        "konto": "konto-karten",
        "internet": "internet-dsl",
        "saisonal": "frugalismus",
        "seo_qualitaet": "frugalismus",
    }.get(kategorie, "frugalismus")


def main() -> int:
    ap = argparse.ArgumentParser(
        description="KI-Redaktion, Rolle ChatGPT: schneller News-Kompakt-Artikel")
    ap.add_argument("--title", help="News-Titel (sonst: automatisch)")
    ap.add_argument("--kategorie",
                    choices=["energie", "versicherung", "konto",
                             "internet", "saisonal"],
                    help="Aufhänger-Kategorie filtern")
    ap.add_argument("--keywords", help="SEO-Keywords, komma-getrennt")
    ap.add_argument("--offline", action="store_true",
                    help="ohne KI-API: nur Struktur-Gerüst erzeugen")
    ap.add_argument("--provider",
                    choices=list(llm_client.PROVIDERS),
                    help="Provider erzwingen (alle kostenfrei)")
    ap.add_argument("--model", help="Modell-ID überschreiben")
    ap.add_argument(ks.FACHFREIGABE_FLAG, dest="fachfreigabe",
                    action="store_true",
                    help="YMYL-Aufhänger bewusst beauftragen (nur bei offenem "
                         "WIP-Limit der Fachfreigabe-Bahn; der Entwurf trägt "
                         "das Prüfgerüst, die Freigabe bleibt menschlich)")
    args = ap.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
