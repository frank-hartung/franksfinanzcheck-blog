#!/usr/bin/env python3
# ============================================================
#  POPPY-WERKBANK – Verwerten (Karte → Blog-Entwurf + Social-Texte)
#  ------------------------------------------------------------
#  Das Poppy-Kernfeature im eigenen Repo: Eine Insight-Karte wird
#  in Franks Marken-Stimme verwertet zu
#
#    • Blog-ENTWURF  (content/posts/<slug>/index.md, draft: true,
#                     Frontmatter über ki_shared.build_frontmatter,
#                     Rolle „poppy“ – Freigabe wie immer über
#                     python3 scripts/ki_redaktion.py --promote <slug>)
#    • Newsletter-Blurb (Betreff + 2–3 Sätze)
#    • Mastodon-Post (≤ 480 Zeichen, mit Artikel-Link)
#    • Pinterest-Pin (Titel 40–100, Beschreibung 220–500 Zeichen,
#                     Grenzen aus scripts/length_policy.py)
#
#  KOSTEN-REGEL: nur Gratis-Kette Groq → Gemini (llm_client).
#  Ohne Key: strukturiertes Offline-Gerüst mit TODO-Markern –
#  bewusst NICHT promotefähig (gleiche Wache wie KI-Redaktion).
#
#  Anti-Halluzination: Faktenanker NUR aus der Quellkarte plus
#  gekennzeichnete Faustregeln. Zahlen aus der Quelle werden als
#  solche benannt („laut <Quelle> …“).
#
#  Nutzung:
#    python3 scripts/poppy_repurpose.py --auto            # alle neuen Karten
#    python3 scripts/poppy_repurpose.py --karte <id>       # eine Karte
#    python3 scripts/poppy_repurpose.py --neueste 2        # die 2 neuesten
#    python3 scripts/poppy_repurpose.py --auto --nur-sozial  # ohne Blogartikel
#    python3 scripts/poppy_repurpose.py --karte <id> --offline
# ============================================================
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

import poppy_lib as lib  # noqa: E402

import ki_shared as ks  # noqa: E402
import post_utils  # noqa: E402

try:
    import length_policy  # noqa: E402
except Exception:  # noqa: BLE001
    length_policy = None

ROLLE = "poppy"

# Zeichenvorgabe (Floor der length_policy für Posts einhalten, damit
# ki_redaktion.py --promote nicht an der Mindestlänge scheitert).
ZIEL_ZEICHEN = 12500
MIN_ZEICHEN = 10000
MAX_ZEICHEN = 16000

SYSTEM_PROMPT = """Du bist die Leitfigur der Redaktion von FranksFinanzcheck: \
ein erfahrener deutscher Finanzjournalist (Verlagsniveau: Capital/WiWo/Zeit). \
Du schreibst aus EINER recherchierten Quelle einen eigenständigen Ratgeber.

HARTE REGELN (Verstoß = unbrauchbar):
1. Schreibe ausschließlich auf Deutsch, direkte Du-Ansprache, warm und konkret.
2. ERFINDE NIEMALS Fakten: keine Studien, Institute, Paragraphen, Prozentzahlen, \
Preise oder Daten. Zahlen NUR aus dem QUELLENTTEXT – und dann benannt als \
„laut <Quelle> …“ oder „für das Jahr 2026 heißt das im Beispiel …“. Allgemeingültige \
Faustregeln (50-30-20-Regel, Notgroschen 3–6 Monatsgehälter) sind erlaubt und als \
Faustregel zu kennzeichnen.
3. Rechenbeispiele mit sauber gerundeten, ausdrücklich als Rechenbeispiel \
gekennzeichneten Annahmen – Rechnung muss stimmen.
4. Keine Übertreibungen, keine Heilsversprechen, kein Clickbait, keine Emojis \
im Fließtext.
5. Keine konkreten Anbieter-Empfehlungen außer CHECK24 als Vergleichsportal.
6. Deutsche Satzschreibung (kein Title-Case): „So sparst du 300 €“ – nicht \
„So Sparst Du 300 €“. Nach Doppelpunkt groß, nach Komma/Präposition/Artikel klein. \
Marken exakt: CHECK24, FRITZ!Box, congstar, otelo, idealo, Verivox, O2, PAYBACK, \
Pinterest, Excel, Vodafone. Fachkürzel groß: DSL, WLAN, DNS, kWh, AGB, FAQ. \
Keine GROSSBUCHSTABEN als Betonung. Überschriften enden nie mit Punkt, enthalten \
keinen zweiten Satz, keinen Call-to-action, keinen **Fettdruck**. Komposita \
zusammen oder mit Bindestrich: „DSL-Vergleich“, nie „DSL Vergleich“.
7. LESBARKEIT (Wache readability_check.py): Flesch-Amstadt ≥ 60, im Schnitt \
11–14 Wörter pro Satz, höchstens ein Nebensatz je Satz, Aktiv statt Passiv, \
kein Nominalstil, keine Kanzleiwörter („obligatorisch“, „im Rahmen von“), \
höchstens vier Sätze pro Absatz.

STRUKTUR (exakt so, mit ## -Überschriften):
- Einstieg (1 Absatz: konkrete Alltagssituation oder Leitfrage, ohne Überschrift)
- 4 bis 6 thematische Kapitel mit ## -Überschriften, darin mind. 1 Markdown-Tabelle \
und mind. 1 hervorgehobenes Rechenbeispiel (> **Rechenbeispiel:** …)
- Kapitel „Häufige Fehler und wie du sie vermeidest“
- Kapitel „FAQ – die wichtigsten Fragen kurz beantwortet“ mit 5 Fragen (### )
- Schlussabsatz mit konkretem nächsten Schritt (keine Überschrift)

ZIEL: {ziel} Zeichen Fließtext (Minimum {min_z}, Maximum {max_z}). \
Schreibe den Artikel JETZT vollständig als Markdown – OHNE Frontmatter, \
OHNE Titel-Zeile (# …), OHNE Codezaun um den Text."""


SOZIAL_SYSTEM = """Du bist Social-Editor von FranksFinanzcheck (deutscher \
Finanzblog, ehrlicher Alltags-Praktiker, kein Verkaufsdruck). Du bekommst \
einen fertigen Artikel-Entwurf plus Insights und schreibst Begleittexte. \
Antworte AUSSCHLIESSLICH mit validem JSON, ohne Vorrede:

{
  "kurzantwort": "Ein Satz (max. 140 Zeichen), der die Kernfrage des \
Artikels direkt beantwortet",
  "newsletter": {"betreff": "max. 70 Zeichen, neugierig aber ehrlich",
                 "text": "2–3 Sätze (max. 500 Zeichen), im Du-Ton, mit \
klarem Nutzen – ohne erfundene Zahlen"},
  "mastodon": "max. 470 Zeichen, Du-Ton, 1–2 passende Hashtags am Ende, \
OHNE Link (wird automatisch angehängt)",
  "pinterest": {"titel": "40–100 Zeichen, deutsch, konkret",
                "beschreibung": "220–500 Zeichen, Nutzen zuerst, \
ohne Hashtag-Stau (max. 3)"}
}

Regeln: Nur Aussagen, die im Artikel/Insights stehen. Kein Clickbait, \
keine Emojis außer höchstens einem. Deutsche Satzschreibung."""


def _strip_fences(text: str) -> str:
    text = (text or "").strip()
    text = re.sub(r"^```(?:markdown|md)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def offline_geruest(karte: dict) -> str:
    """Struktur-Gerüst ohne API – mit TODO(KI-REDAKTION)-Markern.

    Die Marker blockieren ki_redaktion.py --promote bewusst (gleiche
    Wache wie bei den anderen Rollen): Offline-Gerüste gehen nie live.
    """
    quelle = karte.get("quelle", {})
    insights = karte.get("insights") or []
    punkte = "\n".join(f"- TODO(KI-REDAKTION: Insight ausformulieren) {i}"
                       for i in insights) or \
        "- TODO(KI-REDAKTION: Kernpunkte aus der Quelle ergänzen)"
    return f"""Der Start gehört hierher: TODO(KI-REDAKTION: Einstieg mit \
konkreter Alltagssituation zur Quelle „{quelle.get('titel', '')}“ schreiben.)

## Was die Quelle besagt

{punkte}

## So prüfst du das für deinen Haushalt

TODO(KI-REDAKTION: Schritt-für-Schritt-Anleitung aus den Insights ableiten.)

**Rechenbeispiel:** TODO(KI-REDAKTION: Rechnung mit gerundeten, als Rechenbeispiel \
gekennzeichneten Annahmen.)

| Schritt | Was zu tun ist | Worauf zu achten ist |
|---|---|---|
| TODO | TODO | TODO |

## Häufige Fehler und wie du sie vermeidest

TODO(KI-REDAKTION: drei typische Fehler aus der Quelle ableiten.)

## FAQ – die wichtigsten Fragen kurz beantwortet

### TODO Frage 1?
TODO(KI-REDAKTION: Antwort.)

### TODO Frage 2?
TODO(KI-REDAKTION: Antwort.)

### TODO Frage 3?
TODO(KI-REDAKTION: Antwort.)

### TODO Frage 4?
TODO(KI-REDAKTION: Antwort.)

### TODO Frage 5?
TODO(KI-REDAKTION: Antwort.)

TODO(KI-REDAKTION: Schlussabsatz mit konkretem nächsten Schritt.)
"""


def _brief(karte: dict) -> str:
    """Schreib-Brief aus der Karte (Faktenanker = Quelle)."""
    quelle = karte.get("quelle", {})
    einst = lib.lade_einstellungen()
    auszug, _ = lib.kuerze(karte.get("inhalt", {}).get("rohtext") or "",
                           int(einst["quelle_max_zeichen"]))
    insights = karte.get("insights") or []
    teile = [
        f"ARTIKEL-THEMA: {karte.get('artikel_titel') or quelle.get('titel', '')}",
        f"SÄULE (PILLAR): {karte.get('pillar') or 'allgemein'}",
        f"QUELLE ({quelle.get('typ')}): „{quelle.get('titel', '')}“"
        + (f" von {quelle.get('autor')}" if quelle.get("autor") else ""),
        f"QUELL-URL (nur für die Namensnennung, nicht als Link einbauen): "
        f"{quelle.get('url') or '-'}",
    ]
    if karte.get("schlagworte"):
        teile.append("SEO-KEYWORDS (natürlich einflechten): "
                     + ", ".join(karte["schlagworte"]))
    teile.append("INSIGHTS AUS DER QUELLE (Faktenanker):\n- "
                 + "\n- ".join(insights))
    if auszug:
        teile.append("QUELLENTEXT (Auszug):\n" + auszug)
    else:
        teile.append("QUELLENTEXT: kein Fließtext vorhanden – "
                     "ausschließlich die Insights verwenden.")
    teile.append("WINKEL: " + (karte.get("winkel")
                                or "Eigenständiger Ratgeber aus der Quelle."))
    if lib.agc_context is not None:
        try:
            block = lib.agc_context.build_context_block(
                karte.get("artikel_titel") or quelle.get("titel", ""),
                pillar=karte.get("pillar"))
            if block:
                teile.append("MARKEN-KONTEXT:\n" + block)
        except Exception:  # noqa: BLE001 – Marken-Kontext darf nie brechen
            pass
    teile.append(
        f"Schreibe jetzt den vollständigen Artikel (Ziel: ca. {ZIEL_ZEICHEN:,} "
        "Zeichen Fließtext).")
    return "\n\n".join(t for t in teile if t)


def blog_entwurf_schreiben(karte: dict, offline: bool) -> tuple[str, str, str]:
    """(slug, provider, zeichen) – schreibt den Entwurf, gibt Slug zurück."""
    quelle = karte.get("quelle", {})
    titel = (karte.get("artikel_titel")
             or karte.get("winkel")
             or quelle.get("titel") or "Quelle verwerten").strip()
    titel = post_utils.safe_title_cut(titel, 60)
    if titel.lower() in ks.existing_titles():
        titel = post_utils.safe_title_cut(
            f"{titel} – was das für dich bedeutet", 60)

    if offline:
        body, provider = offline_geruest(karte), "offline"
    else:
        system = SYSTEM_PROMPT.format(ziel=f"{ZIEL_ZEICHEN:,}",
                                      min_z=f"{MIN_ZEICHEN:,}",
                                      max_z=f"{MAX_ZEICHEN:,}")
        text, provider = lib.chat(system, _brief(karte),
                                  temperature=0.85, max_tokens=8000)
        if not text:
            print("  ⚠ Kein Gratis-Provider erreichbar – Offline-Gerüst "
                  "wird gespeichert (Pipeline bleibt lauffähig).")
            body, provider = offline_geruest(karte), "offline"
        else:
            body = _strip_fences(text)

    description = ks.clip_text(
        f"{titel} – so gehst du Schritt für Schritt vor, mit Rechenbeispiel "
        "und FAQ. Ehrlich, Zahlen statt Werbeversprechen.")
    try:
        fm = ks.build_frontmatter(
            title=titel, description=description,
            tags=karte.get("schlagworte") or [titel],
            pillar=karte.get("pillar") or None,
            keywords=karte.get("schlagworte") or [titel],
            rolle=ROLLE)
    except Exception as e:  # noqa: BLE001 – Register-Grenze darf den Lauf bremsen,
        # aber nie die Karte zerstören: minimales, sicheres Frontmatter.
        print(f"  ⚠ Kanonisches Frontmatter nicht möglich ({e}) – "
              "Fallback-Frontmatter mit draft: true.")
        fm = (
            "---\n"
            f"title: {json.dumps(titel, ensure_ascii=False)}\n"
            f"description: {json.dumps(description, ensure_ascii=False)}\n"
            f"date: {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')}\n"
            "draft: true\n"
            "categories: [\"Ratgeber\"]\n"
            f"author: \"{ks.AUTHOR}\"\n"
            "ai_generated: true\n"
            f'ki_redaktion: "{ROLLE}"\n'
            'ki_redaktion_status: "review"\n'
            "---\n\n")

    content = fm + body
    if provider != "offline":
        content += ("\n\n" + ks.cta_block(karte.get("affiliate_url"))
                    + "\n" + ks.DISCLAIMER + "\n")

    slug = ks.unique_bundle_slug(titel)
    pfad = post_utils.write_post(slug, content)
    zeichen = len(re.sub(r"\s+", " ", body))
    print(f"  ✅ Blog-Entwurf „{titel}“")
    print(f"     Pfad: {os.path.relpath(pfad, BLOG_DIR)}")
    print(f"     Provider: {provider} | Fließtext: {zeichen:,} Zeichen")
    if zeichen < MIN_ZEICHEN and provider != "offline":
        print(f"     ⚠ Unter Floor ({MIN_ZEICHEN:,}) – die Content-Engine "
              "hebelt beim nächsten Lauf nach. Vor --promote prüfen!")
    return slug, provider, zeichen


def sozial_texte_generieren(karte: dict, slug: str, offline: bool) -> dict:
    """Newsletter/Mastodon/Pinterest – mit Offline-Fallback aus Insights."""
    quelle = karte.get("quelle", {})
    fallback_titel = (karte.get("artikel_titel")
                      or quelle.get("titel") or "Neuer Ratgeber")
    artikel_url = f"https://franksfinanzcheck.de/posts/{slug}/"
    if not offline:
        prompt = (
            f"ARTIKEL-TITEL: {karte.get('artikel_titel') or quelle.get('titel')}\n"
            f"PILLAR: {karte.get('pillar') or 'allgemein'}\n"
            f"INSIGHTS:\n- " + "\n- ".join(karte.get("insights") or [])
            + f"\n\nARTIKEL-ENTWURF (Auszug):\n"
            + lib.kuerze(_brief(karte), 6000)[0]
            + "\n\nSchreibe jetzt die Begleittexte als JSON.")
        text, provider = lib.chat(SOZIAL_SYSTEM, prompt, temperature=0.5,
                                  max_tokens=1200)
        erg = lib.extrahiere_json(text) if text else None
        if erg and erg.get("mastodon") and erg.get("newsletter"):
            erg["provider"] = provider
        else:
            erg = None
    else:
        erg = None
    if not erg:
        # Offline-Fallback: nur Bausteine, die nachweislich aus der Quelle stammen
        provider = "offline-vorlage"
        titel = fallback_titel
        insight = (karte.get("insights") or ["Konkrete Zahlen und Schritte"])[0]
        erg = {
            "kurzantwort": lib.kuerze(karte.get("winkel")
                                      or "So gehst du Schritt für Schritt vor.", 140)[0],
            "newsletter": {
                "betreff": lib.kuerze(titel, 68)[0],
                "text": (f"Neu im Blog: {lib.kuerze(titel, 70)[0]}. "
                         f"Darin: {lib.kuerze(insight, 160)[0]} "
                         "Geschrieben wie immer ehrlich und ohne Verkaufsdruck."),
            },
            "mastodon": (f"Neuer Ratgeber: {lib.kuerze(titel, 80)[0]}. "
                         f"Kern: {lib.kuerze(insight, 200)[0]} "
                         "#Finanzen #Sparen"),
            "pinterest": {
                "titel": lib.kuerze(titel, 90)[0],
                "beschreibung": lib.kuerze(
                    f"{lib.kuerze(insight, 220)[0]} So prüfst du das Schritt "
                    "für Schritt für deinen Haushalt – mit Rechenbeispiel und "
                    "FAQ, ehrlich und ohne Verkaufsdruck.", 480)[0],
            },
        }
    # Hart klemmen: Mastodon-Länge, Pinterest-Grenzen (length_policy)
    erg["mastodon"] = lib.kuerze(erg.get("mastodon") or "", 470)[0]
    if erg.get("pinterest"):
        erg["pinterest"]["titel"] = lib.kuerze(
            erg["pinterest"].get("titel", "") or fallback_titel, 100)[0]
        erg["pinterest"]["beschreibung"] = lib.kuerze(
            erg["pinterest"].get("beschreibung") or "", 490)[0]
    erg["artikel_url"] = artikel_url
    erg.setdefault("provider", provider)
    return erg


def karte_verwerten(karte: dict, *, nur_sozial: bool = False,
                    offline: bool = False, dry_run: bool = False) -> bool:
    """Eine Karte verwerten → Entwurf + Social-Texte + Karte aktualisieren."""
    print(f"\n▶ Verwerte Karte {karte['id']}: "
          f"{lib.kuerze(karte.get('quelle', {}).get('titel', ''), 70)[0]}")
    if not (karte.get("insights") or karte.get("inhalt", {}).get("rohtext")):
        print("  ⚠ Karte ohne Insights und Quellentext – übersprungen.")
        return False

    erzeugnisse = karte.get("erzeugnisse") or {}
    neu = False

    if not nur_sozial and not erzeugnisse.get("blog"):
        if dry_run:
            print("  [Dry-Run] Blog-Entwurf würde jetzt geschrieben.")
            slug, provider, zeichen = "", "dry-run", 0
        else:
            slug, provider, zeichen = blog_entwurf_schreiben(karte, offline)
        erzeugnisse["blog"] = {
            "slug": slug, "provider": provider, "zeichen": zeichen,
            "erstellt": lib.now_utc_iso(),
            "freigabe": ("python3 scripts/ki_redaktion.py --promote " + slug
                         if slug else ""),
        }
        neu = True

    if dry_run:
        print("  [Dry-Run] Social-Texte würden jetzt generiert.")
    else:
        sozial = sozial_texte_generieren(
            karte, erzeugnisse.get("blog", {}).get("slug", ""), offline)
        erzeugnisse.update({
            "kurzantwort": sozial.get("kurzantwort", ""),
            "newsletter": sozial.get("newsletter", {}),
            "mastodon": sozial.get("mastodon", ""),
            "pinterest": sozial.get("pinterest", {}),
            "artikel_url": sozial.get("artikel_url", ""),
            "sozial_provider": sozial.get("provider", ""),
        })
        neu = True

    if dry_run:
        return True
    karte["erzeugnisse"] = erzeugnisse
    karte["status"] = lib.STATUS_VERWERTET
    lib.protokolliere(karte, "Karte verwertet (Blog-Entwurf"
                       + ("" if nur_sozial else " + Social-Texte") + ")")
    lib.speichere_karte(karte)
    print(f"  ✅ Karte aktualisiert (Status: verwertet).")
    return True


def _selbsttest() -> int:
    print("Poppy-Verwerter – Selbsttest (offline)")
    fehler = []
    if "ERFINDE NIEMALS" not in SYSTEM_PROMPT or "FAQ" not in SYSTEM_PROMPT:
        fehler.append("SYSTEM_PROMPT unvollständig")
    if "TODO(KI-REDAKTION" not in offline_geruest(
            lib.neue_karte("text", titel="t", url="", rohtext="x")):
        fehler.append("Offline-Gerüst ohne TODO-Marker (Promote-Wache blind)")
    probe = {"insights": ["Strompreis sinkt um 12 Prozent"],
             "quelle": {"titel": "Test", "typ": "artikel", "url": "u",
                        "autor": "A"},
             "artikel_titel": "Stromkosten senken 2026",
             "schlagworte": ["Strom sparen"], "winkel": "w", "pillar": ""}
    if not _brief(probe).startswith("ARTIKEL-THEMA: Stromkosten senken 2026"):
        fehler.append("Brief baut nicht mit Thema auf")
    if fehler:
        print("  ✗ " + "\n  ✗ ".join(fehler))
        return 2
    print("  ✓ Prompts, Offline-Gerüst (mit Promote-Sperre) und Brief: in Ordnung.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Poppy-Werkbank: Karten zu Entwürfen + Social-Texten verwerten")
    ap.add_argument("--karte", action="append", default=[],
                    help="Karten-ID (mehrfach möglich)")
    ap.add_argument("--neueste", type=int, default=0,
                    help="Die N neuesten neuen Karten verwerten")
    ap.add_argument("--auto", action="store_true",
                    help="Alle Karten mit Status „neu“ (max. aus quellen.yaml)")
    ap.add_argument("--nur-sozial", action="store_true",
                    help="Keinen Blog-Entwurf schreiben, nur Begleittexte")
    ap.add_argument("--offline", action="store_true",
                    help="Ohne KI-API: Gerüst/Vorlagen statt generierter Texte")
    ap.add_argument("--dry-run", action="store_true",
                    help="Nur anzeigen, nichts schreiben")
    ap.add_argument("--selftest", action="store_true",
                    help="Fail-closed-Selbsttest (Exit 2 bei Defekt)")
    args = ap.parse_args()

    if args.selftest:
        return _selbsttest()

    karten = lib.lade_karten()
    if not karten:
        print("ℹ Board leer – zuerst einsammeln: "
              "python3 scripts/poppy_ingest.py --quelle …")
        return 0

    if args.karte:
        gewaehlt = [k for k in karten if k["id"] in args.karte]
        fehlend = set(args.karte) - {k["id"] for k in gewaehlt}
        if fehlend:
            print(f"⚠ Karten nicht gefunden: {', '.join(sorted(fehlend))}")
    elif args.neueste:
        gewaehlt = [k for k in karten if k["status"] == lib.STATUS_NEU][:args.neueste]
    else:  # --auto (Default, wenn nichts gewählt)
        einst = lib.lade_einstellungen()
        gewaehlt = [k for k in karten if k["status"] == lib.STATUS_NEU][
            :int(einst["max_verwertung_pro_lauf"])]

    if not gewaehlt:
        print("ℹ Keine Karten mit Status „neu“ – alles verwertet. "
              "Board: python3 scripts/poppy_board.py")
        return 0

    print(f"Poppy-Werkbank – verwerte {len(gewaehlt)} Karte(n) …")
    erledigt = 0
    for karte in gewaehlt:
        if karte_verwerten(karte, nur_sozial=args.nur_sozial,
                           offline=args.offline, dry_run=args.dry_run):
            erledigt += 1

    if not args.dry_run:
        lib.schreibe_report([
            f"- **Verwerten ({lib.heute_iso()}):** {erledigt} Karte(n) zu "
            "Entwürfen + Begleittexten verwertet (Rolle „poppy“, alles "
            "draft: true).",
            "- Freigabe wie immer: `python3 scripts/ki_redaktion.py "
            "--promote <slug>` (cadence_guard, Mo/Mi/Fr).",
        ])
        try:  # Board gleich frisch bauen
            import poppy_board
            poppy_board.board_bauen()
        except Exception:  # noqa: BLE001 – Board ist Komfort, kein Muss
            pass
    print(f"\n✅ Poppy-Werkbank: {erledigt} Karte(n) verwertet.")
    return 0 if erledigt else 1


if __name__ == "__main__":
    raise SystemExit(main())
