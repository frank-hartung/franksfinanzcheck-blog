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

    # 3) Themenpool
    parse_ok, freie, msg = check_topics()
    if not parse_ok:
        ok = False
        print(f"❌ Themenpool: {msg}")
    else:
        print(f"✅ Themenpool: {msg}")
        if freie < 8:
            print("   ℹ️ Wenig freie Themen – KI-Nachschub wird beim Lauf aktiviert.")

    print("-" * 60)
    if ok:
        print("✅ PRE-FLIGHT BESTANDEN – Bot kann starten.")
        return 0
    print("❌ PRE-FLIGHT FEHLGESCHLAGEN – Workflow wird abgebrochen.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
