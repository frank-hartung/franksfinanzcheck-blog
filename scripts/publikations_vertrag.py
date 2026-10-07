#!/usr/bin/env python3
# ============================================================
#  PUBLIKATIONS-VERTRAG – Textänderungen dürfen keine Blocker erzeugen
#  (Vorgang WF-54C4 / Meldung #607, 07.10.2026)
#
#  WARUM DIESE WACHE
#  -----------------
#  Am 05.10.2026 um 22:27 UTC starb der Deploy-Lauf 37379833880 im Schritt
#  „Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)“ mit
#  Exit 1 – wörtlich aus dem Lauf:
#
#      Release-Scorecard (kandidaten): 32/39 Live-Artikel freigabe-reif,
#                                      1 blockiert/unbeweisbar, 0 Werkzeugfehler.
#        ❌ 2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert (blockiert)
#             T5-lesbarkeit: Flesch 44.3 (Mindestwert 60) …
#             T6-textverstaendnis: R7-INTRO-FORMEL: „in diesem beitrag“ ×1 …
#      Exit 1 (blockierend im Scope).
#
#  Der Artikel war 20 Minuten zuvor konform: Flesch 68,7, kein R7-Fund.
#  Die KI-Redaktion (scripts/redaktions_standard.py --fix --ai) hatte ihn im
#  Rahmen des Capital/WiWo/ZEIT-Retrofits neu geschrieben und dabei unter die
#  Veröffentlichungsschwelle gedrückt. Ihre eigene Verifikation prüfte
#  Linkziele, H2-Anzahl, Länge und Trennlinien – also die STRUKTUR der
#  Änderung – aber nicht die Regeln, die über die Veröffentlichung
#  entscheiden. Der folgende Deploy-Lauf hat den frisch geänderten Artikel
#  korrekt blockiert; das Ergebnis war dennoch ein roter Produktionsalarm,
#  ein abgebrochener Deploy und ein Catch-up-Lauf.
#
#  „Eine Wache ohne zugehöriges Tor ist ein Protokoll“ (Lektion aus #585).
#  Hier gilt die Umkehrung: Ein Schreiber ohne zugehöriges Tor ist ein
#  Blocker-Produzent. Dieses Modul ist das fehlende Tor auf der SCHREIB-Seite.
#
#  DER VERTRAG (V1–V3)
#  -------------------
#  Gemessen wird eine GEPLANTE Änderung – alt gegen neu –, bevor sie
#  geschrieben wird. Beide Seiten werden über `readability_check.parse_article`
#  gelesen (kein Dateizugriff nötig; eine Messung, die erst nach dem Schreiben
#  möglich ist, verhindert nichts).
#
#    V1  Lesbarkeit      Eine Änderung darf einen Artikel nicht unter die
#                        Publish-Schwelle drücken und ihn dabei
#                        verschlechtern. Schwelle: importierte SSOT
#                        `readability_check.NEW_FLESCH_MIN` (60,0) –
#                        keine zweite Zahl, kein zweiter Maßstab.
#    V2  Textverständnis Eine Änderung darf keine HARTEN Verständnis-Funde
#                        einführen, die der Text vorher nicht hatte.
#                        Detektor: `textverstaendnis_guard.check_article`,
#                        Regelliste: importierte SSOT `publish_gate.HARTE_REGELN`
#                        – dieselbe Liste, mit der das Publish-Gate blockiert.
#                        Geprüft wird die DIFFERENZ: Altlasten werden nicht
#                        dem Schreiber angelastet, neue Ruinen schon.
#    V3  Messbarkeit     Lässt sich V1 oder V2 nicht ausführen, gilt der
#                        Vertrag als verletzt (fail-closed). „Nicht gemessen“
#                        ist niemals „freigegeben“.
#
#  BEWUSST NICHT GEPRÜFT
#  ---------------------
#  Eine Verschlechterung OBERHALB der Schwelle (z. B. 68 → 63) blockiert
#  nicht. Der Vertrag verhindert Blocker, er verbietet keine Redaktion – eine
#  Regel, die jede Verbesserung mit Sanktion belegt, wird umgangen statt
#  eingehalten. Ebenso unberührt: Rechtschreibung, Länge, Struktur (das
#  erledigen die vorhandenen Wachen des jeweiligen Schreibers).
#
#  BENUTZUNG
#  ---------
#    from publikations_vertrag import pruefe, raw_aus
#    gruende = pruefe(slug, raw_aus(fm, alt_body, prefix),
#                           raw_aus(fm, neu_body, prefix))
#    if gruende:  # → Änderung verwerfen, nichts schreiben
#        ...
#    python3 scripts/publikations_vertrag.py --selftest   # Sabotage-Proben
# ============================================================
from __future__ import annotations

import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import post_utils  # noqa: E402  (Pfad-Injektion muss davor stehen)
import readability_check  # noqa: E402
import publish_gate  # noqa: E402
import textverstaendnis_guard  # noqa: E402

SIM_DIR = os.path.join(BLOG_DIR, "scripts", "tests", "sim", "wf54c4")


def raw_aus(fm: str, body: str, prefix: str = "") -> str:
    """Baut den kanonischen Rohtext (Frontmatter + Body) für die Messung.

    Nutzt `post_utils.join_article` – dieselbe Naht wie jeder Schreiber.
    Damit misst der Vertrag exakt den Text, der auch geschrieben würde.
    """
    return post_utils.join_article(fm, body, prefix)


def _flesch(rohtext: str, slug: str) -> float | None:
    """Flesch-Amstad eines noch nicht geschriebenen Textes (oder None)."""
    datensatz = readability_check.parse_article(rohtext, f"{slug}/index.md")
    if not datensatz:
        return None
    return readability_check.analyze(datensatz).get("flesch")


def _harte_funde(rohtext: str, slug: str, term: dict) -> set[str]:
    """Namen der harten Verständnis-Regeln, die dieser Text auslöst."""
    body = textverstaendnis_guard.split_body(rohtext)
    funde = textverstaendnis_guard.check_article(
        f"{slug}/index.md", body, term,
        textverstaendnis_guard.frontmatter_keywords(rohtext))
    return {regel for _, regel, _, _ in funde if regel in publish_gate.HARTE_REGELN}


def pruefe(slug: str, alt_rohtext: str, neu_rohtext: str) -> list[str]:
    """Prüft eine geplante Textänderung gegen den Publikations-Vertrag.

    Rückgabe: Liste der Verstöße (leer = Vertrag erfüllt). Fail-closed:
    jeder Messfehler ist ein Verstoß, niemals ein Freispruch.
    """
    gruende: list[str] = []

    # ---------- V1: Lesbarkeit ----------
    try:
        alt_flesch = _flesch(alt_rohtext, slug)
        neu_flesch = _flesch(neu_rohtext, slug)
    except Exception as exc:  # noqa: BLE001 – ohne Mess KEIN grünes Urteil
        gruende.append(
            f"V3 Messbarkeit: Lesbarkeit nicht auswertbar ({exc.__class__.__name__}: "
            f"{exc}) – fail-closed, die Änderung wird verworfen")
        alt_flesch = neu_flesch = None

    if alt_flesch is None or neu_flesch is None:
        if not gruende:
            gruende.append(
                "V3 Messbarkeit: Text ist nicht messbar (Frontmatter/Grenzen "
                "unvollständig) – fail-closed, die Änderung wird verworfen")
    else:
        schwelle = readability_check.NEW_FLESCH_MIN
        if neu_flesch < schwelle and neu_flesch < alt_flesch:
            gruende.append(
                f"V1 Lesbarkeit: Flesch {neu_flesch:.1f} liegt unter der "
                f"Publish-Schwelle {schwelle:g} und verschlechtert den Text "
                f"({alt_flesch:.1f} → {neu_flesch:.1f}) – dieser Artikel würde "
                f"vom Publish-Gate blockiert (Belegart WF-54C4/#607)")

    # ---------- V2: Textverständnis (nur NEUE harte Funde) ----------
    try:
        term = textverstaendnis_guard.load_terminologie()
        alt_funde = _harte_funde(alt_rohtext, slug, term)
        neu_funde = _harte_funde(neu_rohtext, slug, term)
        for regel in sorted(neu_funde - alt_funde):
            gruende.append(
                f"V2 Textverständnis: die Änderung führt den harten Fund "
                f"{regel} ein, den der Text vorher nicht hatte – das "
                f"Publish-Gate würde den Artikel blockieren")
    except Exception as exc:  # noqa: BLE001 – ohne Mess KEIN grünes Urteil
        gruende.append(
            f"V3 Messbarkeit: Textverständnis nicht auswertbar "
            f"({exc.__class__.__name__}: {exc}) – fail-closed, die Änderung "
            f"wird verworfen")

    return gruende


def verstoesse_kurz(gruende: list[str], grenze: int = 160) -> str:
    """Einzeiler für Log/Historie (erster Verstoß, gekürzt)."""
    if not gruende:
        return ""
    text = gruende[0].replace("\n", " ")
    return text if len(text) <= grenze else text[:grenze - 1] + "…"


# ============================================================
#  SELFTEST – die Wache selbst ist beweispflichtig
# ============================================================
def _sim(name: str) -> str:
    with open(os.path.join(SIM_DIR, name), encoding="utf-8") as fh:
        return fh.read()


def selftest() -> int:
    """Sabotage-Proben: Fehler MÜSSEN erkannt werden, Gutes MUSS still bleiben."""
    fehler: list[str] = []

    gut_alt = ("---\ntitle: \"X\"\ndraft: false\n---\n\n"
               "Das ist ein kurzer Satz. Noch einer folgt hier. So bleibt der Text leicht.\n")
    gut_neu = ("---\ntitle: \"X\"\ndraft: false\n---\n\n"
               "Ein kurzer Satz steht hier. Der Text bleibt leicht lesbar. "
               "Kurze Sätze helfen jedem Leser.\n")
    schwer_neu = ("---\ntitle: \"X\"\ndraft: false\n---\n\n"
                  "Die vorgenommene Umstrukturierung der Tariflandschaft, die sich "
                  "insbesondere durch die Anpassung der Netzentgelte sowie der "
                  "CO₂-Bepreisung im Kontext der fortschreitenden Dekarbonisierung "
                  "der Energieversorgungssysteme ergibt, erfordert eine "
                  "grundlegende Neubewertung der individuellen Vertragskonstellationen, "
                  "wobei die Berücksichtigung der jeweiligen Verbrauchsprofile "
                  "unabdingbar erscheint.\n")
    r7_neu = gut_neu.replace("Ein kurzer Satz steht hier.",
                             "In diesem Beitrag erfährst du alles Wichtige.")

    # 1) Gute Änderung bleibt still.
    if pruefe("gut", gut_alt, gut_neu):
        fehler.append(f"gute Änderung wird verworfen: {pruefe('gut', gut_alt, gut_neu)[:1]}")

    # 2) Flesch-Absturz unter die Schwelle wird erkannt (Kernfall WF-54C4).
    gruende = pruefe("hart", gut_alt, schwer_neu)
    if not any(g.startswith("V1") for g in gruende):
        fehler.append("V1: Absinken unter die Publish-Schwelle wird nicht erkannt")
    elif "V1" in gruende[0] and "Flesch" not in gruende[0]:
        fehler.append("V1: Meldung nennt den Flesch-Wert nicht")

    # 3) Neue harte Verständnis-Regel wird erkannt (R7 „In diesem Beitrag“).
    gruende = pruefe("r7", gut_alt, r7_neu)
    if not any("R7-INTRO-FORMEL" in g for g in gruende):
        fehler.append("V2: neu eingeführte R7-Intro-Formel wird nicht erkannt")

    # 4) Altlasten werden nicht angelastet: Der Fund steht schon VORHER drin.
    if pruefe("altlast", r7_neu, r7_neu):
        fehler.append("V2: unveränderte Altlast wird fälschlich als neuer Fund gemeldet")

    # 5) Die Schwelle ist importiert, nicht kopiert: Wer sie anhebt, hebt sie
    #    auch hier – eine zweite Zahl im Modul würde das nicht mitmachen.
    echtes_min = readability_check.NEW_FLESCH_MIN
    try:
        readability_check.NEW_FLESCH_MIN = 99.0
        if not pruefe("schwelle", gut_alt, gut_neu):
            fehler.append("V1: Schwelle wird nicht aus readability_check importiert "
                          "(angehobene SSOT änderte das Urteil nicht)")
    finally:
        readability_check.NEW_FLESCH_MIN = echtes_min

    # 6) Fail-closed: nicht messbarer Text → Verstoß, niemals Freispruch.
    if not pruefe("kaputt", "kein Frontmatter", "auch keiner"):
        fehler.append("V3: nicht messbarer Text gilt als freigegeben (fail-open)")

    # 7) Der ECHTE Vorfall, eingefroren: Der Artikel vom 05.10.2026 war
    #    konform und wurde von der KI-Redaktion unter die Schwelle gedrückt.
    try:
        vorher, nachher = _sim("vorher.md"), _sim("nachher.md")
        echte_gruende = pruefe("2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert",
                               vorher, nachher)
        if not any(g.startswith("V1") for g in echte_gruende):
            fehler.append("Vorfall WF-54C4: der reale Auslöser wird nicht mehr erkannt "
                          "(Flesch-Absturz fehlt)")
        if not any("R7-INTRO-FORMEL" in g for g in echte_gruende):
            fehler.append("Vorfall WF-54C4: der reale R7-Fund wird nicht mehr erkannt")
        if pruefe("vorfall-ok", vorher, vorher):
            fehler.append("Vorfall WF-54C4: der unveränderte Ursprungstext gilt "
                          "fälschlich als Verstoß")
    except OSError as exc:
        fehler.append(f"Vorfall-Material (scripts/tests/sim/wf54c4) nicht lesbar: {exc}")

    if fehler:
        print("🛑 PUBLIKATIONS-VERTRAG – SELFTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print("✅ PUBLIKATIONS-VERTRAG-SELFTEST bestanden: V1 (Flesch-Absturz unter die "
          "importierte Schwelle), V2 (neue harte Verständnis-Funde, Altlasten "
          "verschont), V3 (fail-closed), reale Vorfallprobe WF-54C4.")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    print(__doc__.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
