#!/usr/bin/env python3
# ============================================================
#  KI-REDAKTION – Rolle 2 „CHATGPT": schnelle News
#  ------------------------------------------------------------
#  Bildet den ChatGPT-Part des Schemas „ChatGPT Plus für schnelle
#  News" mit gleichem Funktionsumfang ab: zügig produzierte,
#  kompakte News-Artikel zu aktuellen Anlässen.
#
#  KOSTEN-REGEL: Standardmäßig laufen NUR die Gratis-Zugänge des
#  Repos (Groq → Gemini). Die echte OpenAI-API wird nur verwendet,
#  wenn ausdrücklich ein OPENAI_API_KEY gesetzt UND --provider
#  openai übergeben wird (kostenpflichtig – deshalb nie Default).
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
#  Nutzung:
#    python3 scripts/news_writer.py                 # nächster Aufhänger
#    python3 scripts/news_writer.py --offline       # ohne KI-API
#    python3 scripts/news_writer.py --kategorie energie
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

try:
    import length_policy
except Exception:  # noqa: BLE001
    length_policy = None

ROLLE = "chatgpt"

SYSTEM_PROMPT = """Du bist der News-Desk von FranksFinanzcheck: schnell, \
präzise, verlässlich – wie eine seriöse deutsche Wirtschaftsredaktion. \
Du schreibst einen News-Kompakt-Artikel.

HARTE REGELN (Verstoß = unbrauchbar):
1. Deutsch, direkte Du-Ansprache, newsiger Ton (kurze Sätze, aktiv).
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
        if prov == "openai" and "--provider" not in sys.argv:
            continue
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
    return t.strip()


def _measure(text: str) -> int:
    if length_policy is not None:
        try:
            return length_policy.measure(text)[1]
        except Exception:  # noqa: BLE001
            pass
    return len(re.sub(r"\s+", " ", text).strip())


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


def run(args) -> int:
    cfg = ks.load_config()
    limits = cfg.get("zeichenvorgabe_news", {})
    min_z = int(limits.get("min", 10500))
    ziel = int(limits.get("ziel", 12000))
    max_z = int(limits.get("max", 15000))

    hook = ks.pick_news_hook(kategorie=args.kategorie)
    if not hook:
        print("❌ Kein gültiger, unverbrauchter News-Aufhänger in "
              "data/aktuelle_entwicklungen.yaml – bitte Pool nachpflegen "
              "(Anti-Halluzinations-Regel: nichts Erfundenes).")
        return 1

    kategorie = hook.get("kategorie", "saisonal")
    today = datetime.date.today().strftime("%d.%m.%Y")
    title = (args.title or f"{_kategorie_wort(kategorie)}-Update: "
             f"Was sich jetzt für dich ändert").strip()

    keywords = ([k.strip() for k in args.keywords.split(",") if k.strip()]
                if args.keywords else [])

    if args.offline:
        body, provider = offline_skeleton(hook), "offline"
    else:
        chain = list(cfg.get("anbieter_kette_news") or ["groq", "gemini"])
        if args.provider:
            chain = [args.provider]
        system = SYSTEM_PROMPT.format(min_z=min_z, ziel=ziel, max_z=max_z)
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
        tags=(keywords or [title, _kategorie_wort(kategorie)])[:4],
        keywords=keywords or [title], rolle=ROLLE, news=True,
        kategorie=kategorie)
    stand = (f"**Stand: {today}.** Dieser News-Kompakt-Artikel ordnet eine "
             "aktuelle Entwicklung ein. Konditionen und Regeln können sich "
             "ändern – prüfe Details immer beim jeweiligen Anbieter.\n\n")
    content = fm + stand + body
    if provider != "offline":
        content += ("\n\n" + ks.cta_block() + "\n" + ks.DISCLAIMER + "\n")

    slug = ks.unique_bundle_slug(title)
    import post_utils  # noqa: E402
    path = post_utils.write_post(slug, content)
    ks.mark_news_hook_used(hook.get("id", ""))

    chars = _measure(stand + body)
    print(f"✅ Rolle ChatGPT (News): Entwurf „{title}“")
    print(f"   Pfad: {os.path.relpath(path, BLOG_DIR)}")
    print(f"   Provider: {provider} | Fließtext: {chars:,} Zeichen "
          f"(Ziel {ziel:,}) | Aufhänger: {hook.get('id')}")
    if chars < min_z and provider != "offline":
        print(f"   ⚠ Unter Floor ({min_z:,}) – vor --promote prüfen!")
    ks.write_report([
        f"- **Letzter Lauf (Rolle ChatGPT/News):** Entwurf „{title}“ "
        f"({provider}, {chars:,} Zeichen, Aufhänger `{hook.get('id')}`) "
        "– Status: Review erforderlich.",
        f"- Pfad: `{os.path.relpath(path, BLOG_DIR)}`",
        "- Veröffentlichung: NIE automatisch – Freigabe über "
        "`python3 scripts/ki_redaktion.py --promote <slug>`.",
    ])
    return 0


def _kategorie_wort(kategorie: str) -> str:
    return {"energie": "Energie", "versicherung": "Versicherung",
            "konto": "Konto & Karten", "internet": "Internet & DSL",
            "saisonal": "Saison", "seo_qualitaet": "Markt"}.get(
                kategorie, "Markt")


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
                    choices=["groq", "gemini", "claude", "openai"],
                    help="Provider erzwingen (claude/openai = kostenpflichtig, "
                         "nur mit gesetztem Key)")
    ap.add_argument("--model", help="Modell-ID überschreiben")
    args = ap.parse_args()
    if args.provider == "openai" and not os.environ.get("OPENAI_API_KEY"):
        print("❌ --provider openai braucht einen (kostenpflichtigen) "
              "API-Key. Gratis-Regel: weglassen, dann laufen Groq/Gemini.")
        return 2
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
