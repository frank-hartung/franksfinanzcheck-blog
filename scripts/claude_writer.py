#!/usr/bin/env python3
# ============================================================
#  KI-REDAKTION – Rolle 1 „CLAUDE": lange Premium-Artikel
#  ------------------------------------------------------------
#  Bildet den Claude-Part des Schemas „Claude für lange Artikel"
#  mit gleichem Funktionsumfang ab: lange, tief recherchierte
#  Premium-Ratgeber (11.000–18.000 Zeichen) mit klarer Struktur,
#  Tabellen, Rechenbeispielen und FAQ.
#
#  KOSTEN-REGEL: Standardmäßig laufen NUR die Gratis-Zugänge des
#  Repos (Groq → Gemini, Kette aus data/ki_redaktion.yaml). Die
#  echte Anthropic-API wird nur verwendet, wenn ausdrücklich ein
#  ANTHROPIC_API_KEY gesetzt UND --provider claude übergeben wird
#  (kostenpflichtig – deshalb nie Default).
#
#  Ergebnis ist IMMER ein Entwurf (draft: true, kein cadence_wait):
#  Die Content-Engine v2 und ihre Gates bleiben der einzige Weg ins
#  Live-Blog. Anti-Halluzination: Thema + Faktenanker kommen nur aus
#  kuratierten Repo-Daten (topics.yaml, AGC-Recherche).
#
#  Nutzung:
#    python3 scripts/claude_writer.py                    # freies Thema
#    python3 scripts/claude_writer.py --topic "Titel" --pillar strom-sparen
#    python3 scripts/claude_writer.py --offline          # ohne KI-API
#    python3 scripts/claude_writer.py --provider claude  # paid, opt-in
# ============================================================
from __future__ import annotations

import argparse
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import ki_shared as ks  # noqa: E402
import llm_client  # noqa: E402

try:  # AGC-Kontext (Brand Brain + Recherche) – darf nie crashen
    import agc_context
except Exception:  # noqa: BLE001
    agc_context = None

try:
    import length_policy
except Exception:  # noqa: BLE001
    length_policy = None

ROLLE = "claude"

SYSTEM_PROMPT = """Du bist die Leitfigur der Redaktion von FranksFinanzcheck: \
ein erfahrener deutscher Finanzjournalist (Verlagsniveau: Capital/WiWo/Zeit). \
Deine Aufgabe ist ein LANGER Premium-Ratgeber.

HARTE REGELN (Verstoß = unbrauchbar):
1. Schreibe ausschließlich auf Deutsch, direkte Du-Ansprache, warm und konkret.
2. ERFINDE NIEMALS Fakten: keine Studien, keine Institute, keine Paragraphen, \
keine Prozentzahlen, keine Preise, keine Testergebnisse, keine Daten. \
Verwende NUR Faktenanker, die im Brief stehen, plus allgemeingültige, \
zeitlose Faustregeln (z. B. 50-30-20-Regel, Notgroschen 3-6 Monatsgehälter), \
die du als Faustregel kennzeichnest.
3. Zahlen in Rechenbeispielen müssen korrekt sein und mit sauber \
gerundeten, als Beispiel gekennzeichneten Annahmen arbeiten.
4. Keine Übertreibungen, keine Heilsversprechen, kein Clickbait. \
Keine Emojis im Fließtext (nur im CTA-Block).
5. Nenne keine konkreten Anbieter-Empfehlungen außer CHECK24 als \
Vergleichsportal.
6. Groß-/Kleinschreibung nach Duden (deutsche Satzschreibung, kein englisches \
Title-Case): In Überschriften und Sätzen wird NUR groß, was ein Nomen ist oder \
am Satzanfang steht – nicht jedes Wort. „So sparst du 300 €“, nicht \
„So Sparst Du 300 €“. Nach einem Doppelpunkt beginnt ein neuer Satz (dann groß), \
nach Komma, Präposition oder Artikel klein. Feste Wendungen klein: „bar bezahlen“, \
„pro Monat“, „im Alltag“. Marken exakt so: CHECK24, FRITZ!Box (ein Wort, Ausrufezeichen), \
congstar, otelo, idealo, Verivox, O2, PAYBACK, Pinterest, Excel, Vodafone. \
Fachkürzel groß: DSL, WLAN, DNS, kWh, AGB, FAQ. Keine GROSSBUCHSTABEN als \
Betonung („Das ist NICHT egal“ → „Das ist nicht egal“). \
Überschriften (Regel K.1–K.3): deutsche Satzschreibung, enden NIE mit einem Punkt, \
enthalten keinen zweiten Satz und keinen Call-to-action in der Titelzeile – \
„## Fazit: Heizkosten senken“, nie „## Fazit: Heizkosten senken: spar sofort schlau nutzen“. \
Kein **Fettdruck** in der Überschrift (sie ist bereits fett). \
Komposita zusammen- oder mit Bindestrich geschrieben: „Frugalismus-Tipps“, \
„Heizungswartung“, „DSL-Vergleich“ – nie „Frugalismus Tipps“.

STRUKTUR (exakt so, mit ## -Überschriften):
- Einstieg (1 Absatz Alltagssituation oder Leitfrage, ohne Überschrift)
- 4 bis 6 thematische Kapitel mit ## -Überschriften, darin mind. 1x eine \
Markdown-Tabelle und mind. 1 hervorgehobenes Rechenbeispiel (> **Rechenbeispiel:**)
- Kapitel „Häufige Fehler und wie du sie vermeidest"
- Kapitel „FAQ – die wichtigsten Fragen kurz beantwortet" mit 5 Fragen (### )
- Schlussabsatz mit konkretem nächsten Schritt (keine Überschrift)

ZIEL: {ziel} Zeichen Fließtext (Minimum {min_z} Zeichen, Maximum {max_z}). \
Schreibe den Artikel JETZT vollständig als Markdown OHNE Frontmatter, \
OHNE Titel-Zeile (# ...), OHNE Codeblöcken-Zaun um den ganzen Text."""


def _brief(topic: dict, keywords: list, extra: str = "") -> str:
    """Recherche-Brief für das Modell (Faktenanker aus kuratierten Daten)."""
    title = topic.get("title", "")
    pillar = topic.get("pillar", "")
    parts = [
        f"ARTIKEL-THEMA: {title}",
        f"SÄULE (PILLAR): {pillar}",
    ]
    if keywords:
        parts.append("SEO-KEYWORDS (natürlich einflechten, nicht stopfen): "
                     + ", ".join(keywords))
    if extra:
        parts.append(extra)
    if agc_context is not None:
        try:
            ctx = agc_context.build_context_block(title, pillar=pillar,
                                                  keywords=keywords)
            if ctx:
                parts.append(ctx)
        except Exception:  # noqa: BLE001
            pass
    parts.append(
        "REGEL ZUM BRIEF: Übernimm Faktenanker wörtlich/sinngemäß. Alles, "
        "was hier nicht steht, ist für konkrete Zahlen/Daten TABU.")
    return "\n\n".join(parts)


def _generate(provider_chain: list, system: str, prompt: str,
              model: str | None) -> tuple[str | None, str]:
    """Erster erreichbarer Gratis-Provider der Kette. Liefert (Text, Name)."""
    for prov in provider_chain:
        if prov == "claude" and not (os.environ.get("ANTHROPIC_API_KEY")
                                     and "--provider" in sys.argv):
            continue
        text = llm_client.chat(prov, prompt=prompt, system=system,
                               model=model, temperature=0.5,
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
    t = re.sub(r"(?m)^#\s+.+$", "", t, count=1)  # Titelzeile entfernen
    return t.strip()


def _measure(text: str) -> int:
    if length_policy is not None:
        try:
            return length_policy.measure(text)[1]
        except Exception:  # noqa: BLE001
            pass
    return len(re.sub(r"\s+", " ", text).strip())


def offline_skeleton(topic: dict) -> str:
    """Offline-Gerüst (ohne KI-API): komplette Struktur, Inhalt = Aufgabe."""
    t = topic.get("title", "Thema")
    return f"""<!-- OFFLINE-GERÜST der KI-Redaktion (Rolle Claude): Struktur steht,
Inhalt fehlt – API-Key nötig oder manuell fertigstellen. -->

Bedeutet **{t}** für dich vor allem eines: eine Entscheidung, die Geld kostet, wenn man sie aufschiebt? Genau hier setzt dieser Ratgeber an.

{ks.DISCLOSURE}

## {t}: Das Wichtigste im Überblick

<!-- TODO(KI-REDAKTION/claude): 2-3 Absätze Überblick mit Facts aus dem kuratierten Brief. -->

## So gehst du Schritt für Schritt vor

<!-- TODO(KI-REDAKTION/claude): 4-5 Schritte als Absätze, je 1 Zwischenüberschrift erwägen. -->

| Schritt | Was zu tun ist | Worauf achten |
|---|---|---|
| 1 | <!-- TODO --> | <!-- TODO --> |
| 2 | <!-- TODO --> | <!-- TODO --> |

> **Rechenbeispiel:** <!-- TODO(KI-REDAKTION/claude): Beispielrechnung mit klar gekennzeichneten Annahmen. -->

## Häufige Fehler und wie du sie vermeidest

<!-- TODO(KI-REDAKTION/claude): 3-5 Fehler mit Lösung. -->

## FAQ – die wichtigsten Fragen kurz beantwortet

### Was bringt {t} konkret?

<!-- TODO(KI-REDAKTION/claude): kurze, ehrliche Antwort. -->
"""


def run(args) -> int:
    cfg = ks.load_config()
    limits = cfg.get("zeichenvorgabe_lang", {})
    min_z = int(limits.get("min", 11000))
    ziel = int(limits.get("ziel", 14000))
    max_z = int(limits.get("max", 18000))

    # ---------- Thema bestimmen ----------
    if args.topic:
        topic = {"title": args.topic.strip(),
                 "pillar": args.pillar or "",
                 "affiliate_url": ks.AFFILIATE_URL}
    else:
        topic = ks.pick_topic(pillar=args.pillar)
        if not topic:
            print("❌ Kein freies Thema im Pool (data/topics.yaml) gefunden.")
            return 1
    title = topic["title"]
    if title.lower() in ks.existing_titles():
        print(f"❌ Thema bereits veröffentlicht: „{title}“ – übersprungen.")
        return 1

    keywords = ([k.strip() for k in args.keywords.split(",") if k.strip()]
                if args.keywords else topic.get("keywords") or [])

    # ---------- Text erzeugen ----------
    if args.offline:
        body, provider = offline_skeleton(topic), "offline"
    else:
        chain = list(cfg.get("anbieter_kette_lang") or ["groq", "gemini"])
        if args.provider:
            chain = [args.provider]
        system = SYSTEM_PROMPT.format(min_z=min_z, ziel=ziel, max_z=max_z)
        prompt = _brief(topic, keywords) + (
            f"\n\nSchreibe jetzt den vollständigen Artikel "
            f"(Ziel: ca. {ziel} Zeichen).")
        body, provider = _generate(chain, system, prompt, args.model)
        if not body:
            print("⚠ Kein Gratis-Provider erreichbar – Offline-Gerüst wird "
                  "als Entwurf gespeichert (Pipeline bleibt lauffähig).")
            body, provider = offline_skeleton(topic), "offline"
        else:
            body = _strip_fences(body)

    # ---------- Zusammensetzen + speichern ----------
    description = ks.clip_text(
        f"{title} – der große Ratgeber von FranksFinanzcheck: Schritt für "
        "Schritt erklärt, mit Rechenbeispielen, Checklisten und FAQ.")
    fm = ks.build_frontmatter(
        title=title, description=description,
        tags=(keywords or [title])[:4], pillar=topic.get("pillar"),
        keywords=keywords or [title], rolle=ROLLE)
    content = fm + body
    if provider != "offline":
        content += ("\n\n" + ks.cta_block(topic.get("affiliate_url"))
                    + "\n" + ks.DISCLAIMER + "\n")
    slug = ks.unique_bundle_slug(title)
    import post_utils  # noqa: E402
    path = post_utils.write_post(slug, content)

    chars = _measure(body)
    print(f"✅ Rolle Claude: Entwurf „{title}“")
    print(f"   Pfad: {os.path.relpath(path, BLOG_DIR)}")
    print(f"   Provider: {provider} | Fließtext: {chars:,} Zeichen "
          f"(Ziel {ziel:,})")
    if chars < min_z and provider != "offline":
        print(f"   ⚠ Unter Floor ({min_z:,}) – die Engine hebtelt den Text "
              "beim nächsten Lauf nach (check_length). Vor --promote prüfen!")
    ks.write_report([
        f"- **Letzter Lauf (Rolle Claude):** Entwurf „{title}“ "
        f"({provider}, {chars:,} Zeichen) – Status: Review erforderlich.",
        f"- Pfad: `{os.path.relpath(path, BLOG_DIR)}`",
        "- Veröffentlichung: NIE automatisch – Freigabe über "
        "`python3 scripts/ki_redaktion.py --promote <slug>`.",
    ])
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="KI-Redaktion, Rolle Claude: langer Premium-Artikel")
    ap.add_argument("--topic", help="Thema (sonst: nächstes freies Pool-Thema)")
    ap.add_argument("--pillar", help="Pillar-Filter (z. B. strom-sparen)")
    ap.add_argument("--keywords", help="SEO-Keywords, komma-getrennt")
    ap.add_argument("--offline", action="store_true",
                    help="ohne KI-API: nur Struktur-Gerüst erzeugen")
    ap.add_argument("--provider",
                    choices=["groq", "gemini", "claude", "openai"],
                    help="Provider erzwingen (claude/openai = kostenpflichtig, "
                         "nur mit gesetztem Key)")
    ap.add_argument("--model", help="Modell-ID überschreiben")
    args = ap.parse_args()
    if args.provider in ("claude", "openai") and not os.environ.get(
            "ANTHROPIC_API_KEY" if args.provider == "claude"
            else "OPENAI_API_KEY"):
        print(f"❌ --provider {args.provider} braucht einen (kostenpflichtigen) "
              "API-Key. Gratis-Regel: weglassen, dann laufen Groq/Gemini.")
        return 2
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
