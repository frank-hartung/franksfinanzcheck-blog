"""Pre-Flight-Check für den Content-Bot (widerstandsfähige Automatisierung).

Prüft VOR der Generierung, dass alle Voraussetzungen erfüllt sind:
  1) Alle Python-Skripte sind syntaktisch valide (py_compile) – verhindert,
     dass ein kaputtes Skript (wie der topic.get-Bug) erst mitten im Lauf crasht.
  2) Mindestens ein API-Key (GROQ/GEMINI) ist gesetzt.
  3) topics.yaml ist parsebar und enthält Themen.
  4) Themenpool hat noch freie Themen (oder KI-Nachschub kann greifen).

Exit-Codes:
  0 = alles bereit
  1 = kritischer Fehler (Workflow sollte abbrechen → Alerting)
"""
import os
import sys
import glob
import py_compile

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS = sorted(glob.glob(os.path.join(BLOG_DIR, "scripts", "*.py")))
TOPICS_FILE = os.path.join(BLOG_DIR, "data", "topics.yaml")


def check_syntax():
    bad = []
    for path in SCRIPTS:
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            bad.append(f"{os.path.basename(path)}: {e}")
    return bad


def check_api_keys():
    groq = os.environ.get("GROQ_API_KEY")
    gemini = os.environ.get("GEMINI_API_KEY")
    return bool(groq or gemini), bool(groq), bool(gemini)


def check_topics():
    if not os.path.exists(TOPICS_FILE):
        return False, 0, "topics.yaml fehlt"
    # Parse-Check über generate_drafts.load_topics (nutzt den echten Parser)
    sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
    try:
        import generate_drafts as g
        topics = g.load_topics()
        used = g.existing_titles()
        freie = [t for t in topics if not g.topic_already_covered(t["title"], used)]
        return True, len(freie), f"{len(topics)} Themen, {len(freie)} frei"
    except Exception as e:
        return False, 0, f"topics.yaml unlesbar: {e}"


def check_capacity():
    """Die Zahl, die am Morgen eines Publikationstages wirklich zählt.

    PREMIUM-FIX 02.10.2026 (Issue #521). `check_topics()` zählt mit der
    laxen 60-%-Token-Regel aus `generate_drafts.topic_already_covered` und
    meldete am 02.10.2026 **157 freie Themen**. Der Disponent, der das Thema
    tatsächlich auswählt (`reserve_topics.disponieren`: Leitbegriff-Kollision
    + Cooldown-Gedächtnis + Publikations-Bahn), fand zur selben Zeit **3**.

    Ein Pre-Flight, der mit einem anderen Maß misst als der Disponent, ist
    kein Pre-Flight – er ist eine grüne Lampe am falschen Kabel. Der Lauf
    startete grün, produzierte vier Artikel und endete bei 0/2 LIVE.

    Diese Prüfung misst deshalb mit genau dem Maß des Disponenten und heilt
    vorher die nachweislich falschen Sperren (`--abgleich`): Eine
    Erfolgsmeldung „produziert: <slug>“ zu einem Artikel, den es nicht
    gibt, sperrt das Thema 180 Tage für nichts. Am 02.10. betraf das 47 von
    63 Einträgen.

    Sie bricht den Lauf NIE ab: Auch bei leerem Themenpool bleiben
    Re-Queue-Beförderung und Reserve-Veröffentlichung sinnvoll. Ein Engpass
    ist ein lautes Signal, kein Grund, die Produktion zuzusperren.
    """
    sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))
    try:
        import reserve_topics as rt
        import engine_capacity as ec
    except Exception as e:  # noqa: BLE001 – Pre-Flight darf nie hart fallen
        return None, [f"Kapazitäts-Rechnung nicht ladbar: {e}"]
    hinweise = []
    try:
        korrekturen = rt.abgleich()
        if korrekturen:
            hinweise.append(
                f"{len(korrekturen)} Erfolgsmeldung(en) ohne Artikel "
                f"zurückgenommen – so viele Themen waren grundlos gesperrt "
                f"(erste: „{korrekturen[0]['titel']}“).")
    except Exception as e:  # noqa: BLE001
        hinweise.append(f"Themen-Abgleich übersprungen: {e}")
    try:
        return ec.lage(), hinweise
    except Exception as e:  # noqa: BLE001
        return None, hinweise + [f"Kapazitäts-Lage nicht ermittelbar: {e}"]


def main():
    print("=" * 60)
    print("PRE-FLIGHT-CHECK Content-Bot")
    print("=" * 60)
    ok = True

    # 1) Syntax
    bad = check_syntax()
    if bad:
        ok = False
        print(f"❌ SYNTAX-FEHLER ({len(bad)}):")
        for b in bad:
            print(f"   {b}")
    else:
        print(f"✅ Syntax: {len(SCRIPTS)} Skripte valide")

    # 2) API-Keys
    has_key, groq, gemini = check_api_keys()
    if not has_key:
        ok = False
        print("❌ KEIN API-KEY gesetzt (GROQ_API_KEY / GEMINI_API_KEY fehlen beide)")
    else:
        print(f"✅ API-Keys: Groq={'ja' if groq else 'nein'} | Gemini={'ja' if gemini else 'nein'}")

    # 3) Themenpool (Parsebarkeit – nicht die Kapazität!)
    parse_ok, freie, msg = check_topics()
    if not parse_ok:
        ok = False
        print(f"❌ Themenpool: {msg}")
    else:
        print(f"✅ Themenpool lesbar: {msg} (grobe Zählung)")

    # 4) KAPAZITÄT – mit dem Maß des Disponenten (Issue #521)
    lage, hinweise = check_capacity()
    for hinweis in hinweise:
        print(f"   ℹ️ {hinweis}")
    if lage is None:
        print("⚠️ Kapazität: nicht messbar – Lauf startet trotzdem.")
    else:
        symbol = {"ok": "✅", "knapp": "⚠️", "erschoepft": "🛑"}[lage["verdikt"]]
        print(f"{symbol} Kapazität: {lage['befund']}")
        print(f"   AUTO-Bahn frei: {lage['frei_auto']} · "
              f"FACHFREIGABE-Bahn frei: {lage['frei_fachfreigabe']} "
              f"(von {lage['themen_auto']} + {lage['themen_fachfreigabe']} "
              f"Themen)")
        fach = lage["fachfreigabe"]
        if not fach["geoeffnet"]:
            print(f"   ℹ️ Fachfreigabe-Bahn geschlossen: {fach['grund']}.")
        for warnung in lage["warnungen"]:
            print(f"   ⚠️ {warnung}")
        # Sichtbar im Actions-Log, ohne den Lauf abzubrechen: Ein Engpass
        # heilt nicht dadurch, dass die Engine gar nicht erst anläuft –
        # Re-Queue und Reserve bleiben auch dann die richtige Arbeit.
        if lage["verdikt"] != "ok":
            print(f"::warning title=Content-Engine-Kapazität::"
                  f"{lage['befund']} "
                  f"(AUTO frei: {lage['frei_auto']}, Ziel/Tag: "
                  f"{lage['min_artikel_pro_tag']})")

    print("-" * 60)
    if ok:
        print("✅ PRE-FLIGHT BESTANDEN – Bot kann starten.")
        return 0
    print("❌ PRE-FLIGHT FEHLGESCHLAGEN – Workflow wird abgebrochen.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
