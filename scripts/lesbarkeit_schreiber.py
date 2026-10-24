#!/usr/bin/env python3
"""
SCHREIBER-GARANTIE – Jeder Weg, der einen Artikel schreibt, misst die
Publish-Schwelle VOR dem Schreiben (Governance-Report #806, 24.10.2026).

ANLASS (Issue #806, Premium-Governance vom 19.10.2026)
-----------------------------------------------------
Der Governance-Report #806 nannte als einzigen handlungsbedürftigen Befund
zwei Entwürfe unter der Publish-Schwelle 60:

  2026-10-19-urlaubskasse-clever-aufbessern          Flesch 54,2
  2026-10-16-dns-server-aendern-fuer-schnelleres-internet  Flesch 54,9

Beide tragen `ki_redaktion: "claude"` – sie stammen aus der Rolle „Claude“
(`scripts/claude_writer.py`), dem Hauptproduzenten der langen Premium-Artikel.
Die Lehre aus #712 („Wer schreibt, muss messen, was über ihn entscheidet“)
war damals nur EINER Rolle gegeben worden: `news_writer.py` (Rolle
„ChatGPT/News“) bekam `lesbarkeit_sichern()`. Die Rolle „Claude“ und die
Werkbank-Recycling-Bahn (`poppy_repurpose.py`) schrieben weiter, ohne zu
messen. Der Ausschuss entstand also im Generator – und wurde Wochen später
von drei Wachen eingesammelt (Publish-Gate, Endredaktion, Lesbarkeits-Wache),
bis der wöchentliche Governance-Report die Klasse namentlich meldete. Genau
das ist der Dauerläufer, den das Repo nicht duldet: „Ein Befund ohne Heiler
ist ein Dauerläufer“ (C37) – hier war es ein Befund ohne *Produzenten-Schutz*.

DIE GARANTIE (eine Implementierung, eine Schwelle, ein Tor)
-------------------------------------------------------------
  1. MESSEN über die SSOT: `readability_check` (Flesch-Amstad, deutsch).
     Die Schwelle kommt importiert aus `readability_check.NEW_FLESCH_MIN`
     (60.0) – im Haus gibt es KEINE zweite Flesch-Zahl (Lehre #585).
  2. HEILEN deterministisch über die Stufe A des Lesbarkeits-Heilers – als
     BIBLIOTHEK, nicht als zweite Satz-Zerlegung. Der Heiler ist der
     zertifizierte Ort (Tor T1–T4, Wirkungsprobe C25).
  3. PRÜFEN über das Tor (`verifiziere`): Frontmatter, Links, `/go/`-Anker,
     Überschriften, Shortcodes, Tabellenzeilen, Zahlen und Länge müssen
     unverändert bleiben. Was das Tor nicht freigibt, wird NICHT geschrieben.
  4. EHRLICH bleiben: reicht die deterministische Stufe nicht, steht die Zahl
     im Status – mit dem Weg zur redaktionellen Nachsorge. Ein stiller
     Ausschuss ist die einzige verbotene Sorte.

Die Messung und die Heilung kennen den Werbeblock (CTA/Disclaimer) NICHT:
er wird erst NACH der Sicherung angehängt. Sonst misst der Schreiber eine
Länge, die er nur mit Werbung erreicht.

WER nutzt das?
  * `scripts/news_writer.py`   – Rolle „ChatGPT/News“ (seit #712)
  * `scripts/claude_writer.py`  – Rolle „Claude“, lange Premium-Artikel (neu)
  * `scripts/poppy_repurpose.py`– Werkbank-Recycling (neu)
  Der Vertrag **C41** prüft, dass KEIN Schreiber ohne diese Sicherung
  schreibt – und dass die Sicherung vor dem Schreiben sitzt.

Bedienung:
  python3 scripts/lesbarkeit_schreiber.py --selftest
"""
from __future__ import annotations

import os
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BLOG_DIR not in sys.path:
    sys.path.insert(0, BLOG_DIR)
if os.path.join(BLOG_DIR, "scripts") not in sys.path:
    sys.path.insert(0, os.path.join(BLOG_DIR, "scripts"))

try:  # Die Mess-SSOT – ohne sie ist keine Messung möglich.
    import readability_check as rc  # noqa: E402
except Exception:  # noqa: BLE001 – fehlende SSOT ist ein Befund, kein Grund zu raten
    rc = None

try:  # Der zertifizierte Heiler (Tor T1–T4, Wirkungsprobe C25).
    import lesbarkeit_heiler  # noqa: E402
except Exception:  # noqa: BLE001
    lesbarkeit_heiler = None

#: Kennzeichnet „nicht übergeben“ – sonst wäre ein absichtliches `None`
#: (Modul fehlt) nicht von einem Default unterscheidbar.
_STD = object()


def messen(content: str, slug: str, rc_mod=None) -> float | None:
    """Flesch-Amstad über die Mess-SSOT. None = nicht messbar.

    „Nicht messbar“ ist niemals „freigegeben“ (V3, Vorfall WF-54C4/#607).
    """
    if rc_mod is None:
        rc_mod = rc
    if rc_mod is None:
        return None
    try:
        satz = rc_mod.parse_article(content, f"{slug}/index.md")
        return rc_mod.analyze(satz)["flesch"] if satz else None
    except Exception:  # noqa: BLE001 – ohne Messung bleibt der Lauf ehrlich
        return None


def sichern(content: str, slug: str, *, rc_mod=_STD, heiler=_STD) -> tuple[str, float | None, str]:
    """Misst die Lesbarkeit VOR dem Schreiben und heilt deterministisch nach.

    Rückgabe: `(content – ggf. geheilt, Flesch, Statusmeldung)`.

    Warum hier und nicht nur in der Nachsorge: Ein Generator, der seine
    Schwelle nicht kennt, produziert Ausschuss, den drei Wachen später
    einsammeln müssen (Publish-Gate, Endredaktion, Lesbarkeits-Wache). Der
    Heiler läuft als BIBLIOTHEK mit seinem Tor T1–T4 – er schreibt nur, was
    die importierte Schwelle wirklich erreicht; ohne API, ohne Netz.

    Die Nachsorge bleibt zuständig, wenn die deterministische Stufe nicht
    reicht (Flesch < 60 nach dem Lauf): Dann steht die Zahl ehrlich im Log,
    und `endredaktion.py` bzw. `lesbarkeit_heiler.py --entwuerfe` heilen
    redaktionell nach. Ein stiller Ausschuss ist die einzige verbotene Sorte.
    """
    r = rc if rc_mod is _STD else rc_mod
    h = lesbarkeit_heiler if heiler is _STD else heiler
    if r is None or h is None:
        return content, None, "Lesbarkeits-Messung nicht verfügbar (Modul fehlt)"
    vorher = messen(content, slug, r)
    if vorher is None:
        return content, None, "Lesbarkeit nicht messbar (fail-open im Schreiber)"
    if vorher >= r.NEW_FLESCH_MIN:
        return content, vorher, (f"Flesch {vorher:.1f} ≥ {r.NEW_FLESCH_MIN:g} "
                                 "– Publish-Schwelle erfüllt")
    try:
        neu, protokoll = h.stufe_a(content)
    except Exception as exc:  # noqa: BLE001
        return content, vorher, (f"Flesch {vorher:.1f} < {r.NEW_FLESCH_MIN:g}, "
                                 f"Heiler nicht ausführbar ({exc.__class__.__name__})")
    if neu != content:
        gruende = h.verifiziere(slug, content, neu)
        if not gruende:
            content = neu
            nachher = messen(content, slug, r)
            return content, nachher, (
                f"Flesch {vorher:.1f} → {nachher if nachher is not None else float('nan'):.1f} "
                f"(Stufe A: Lexikon {protokoll.get('lexikon', 0)}, "
                f"Satzschnitte {protokoll.get('saetze', 0)})")
        # Das Tor hat nicht freigegeben – der Grund wird genannt, nicht
        # geraten. Ohne ihn waere die Meldung falsch: Die Stufe A hat
        # geheilt, aber das Tor verweigert (z. B. fehlendes PyYAML in der
        # Schreibpruefung – fail-closed). Das ist ein Werkzeugbefund, kein
        # Lesbarkeits-Befund, und so wird es auch gemeldet.
        tor = "; ".join(str(g) for g in list(gruende)[:2])
        return content, vorher, (f"Flesch {vorher:.1f} < {r.NEW_FLESCH_MIN:g} – "
                                 f"Stufe A heilte, das Tor gab nicht frei "
                                 f"({tor}) – redaktionelle Nachsorge nötig "
                                 f"(`endredaktion.py --slug " + slug + "`)")
    return content, vorher, (f"Flesch {vorher:.1f} < {r.NEW_FLESCH_MIN:g} – "
                             "deterministische Stufe reicht nicht, "
                             "redaktionelle Nachsorge nötig "
                             "(`endredaktion.py --slug " + slug + "`)")


# --------------------------------------------------------------------------
# Selbsttest (Sabotage-Schutz): die Zusage muss WIRKEN, nicht nur behauptet
# sein. Ohne Netz, ohne API-Keys, ohne Schreiben in den Bestand.
# --------------------------------------------------------------------------
def _probe_dicht() -> str:
    """Dichter Text mit Frontmatter – Start unter der Schwelle.

    Dieselbe Fixture-Bauart wie die Wirkungsprobe des Heilers (WACHE-609):
    Flesch ~51–59 vor der Heilung, deutlich über 60 danach. So prüft der
    Selbsttest dieselbe Stufe A, die auch im Betrieb läuft.
    """
    teile = lesbarkeit_heiler.PROBE_FIXTURE.split("---", 2)
    body = teile[2] + "\nMehr im [Vergleich](/go/konto/).\n"
    return teile[0] + "---" + teile[1] + "---\n\n" + body


def selftest() -> int:
    """Die Garantie muss messen, heilen, prüfen und ehrlich bleiben."""
    fails = []
    if rc is None:
        print("❌ Mess-SSOT (readability_check) nicht importierbar")
        return 1
    if lesbarkeit_heiler is None:
        print("❌ Lesbarkeits-Heiler nicht importierbar")
        return 1

    # 1) Die Schwelle kommt aus der SSOT – keine eigene Zahl im Haus.
    if rc.NEW_FLESCH_MIN < 60:
        fails.append(f"Schwelle zu lax: {rc.NEW_FLESCH_MIN}")

    # 2) Ein klarer Text bleibt byte-identisch.
    klar = ("---\ntitle: \"Klar\"\ndate: 2026-10-24\ndraft: true\n---\n\n"
            "Die Kasse hebt den Beitrag an. Du zahlst im Monat mehr. "
            "Ein Blick auf die Abrechnung hilft dir sofort. Wer handelt, "
            "sparst Geld.\n")
    inhalt, flesch, status = sichern(klar, "probe-klar")
    if inhalt != klar:
        fails.append("Ein klarer Text wurde verändert – die Garantie heilt ohne Not")
    if flesch is None or flesch < rc.NEW_FLESCH_MIN:
        fails.append(f"Klarer Text unter Schwelle gemessen: {flesch}")
    if "Schwelle erfüllt" not in status:
        fails.append(f"Status unehrlich: {status}")

    # 3) Ein dichter Text wird gehoben – und das Tor gibt ihn frei.
    dicht = _probe_dicht()
    vorher = messen(dicht, "probe-dicht")
    geheilt, nachher, status2 = sichern(dicht, "probe-dicht")
    if vorher is None or vorher >= rc.NEW_FLESCH_MIN:
        fails.append(f"Die Probe ist nicht dicht genug (Flesch {vorher})")
    if geheilt == dicht:
        fails.append("Der dichte Text wurde nicht uebernommen – die Stufe A "
                     "wirkte nicht oder das Tor verweigerte (siehe Tor-Grund)")
    # Das Tor SEPARAT prüfen und seinen Grund nennen: Sonst stuende ein
    # Werkzeugbefund (fehlendes PyYAML → Schreibpruefung fail-closed) als
    # Lesbarkeits-Befund da – eine falsche Diagnose mit richtigem Ergebnis.
    heil_text, _protokoll = lesbarkeit_heiler.stufe_a(dicht)
    tor_gruende = lesbarkeit_heiler.verifiziere("probe-dicht", dicht, heil_text)
    if tor_gruende:
        fails.append("Das Tor hat den geheilten Text nicht freigegeben: "
                     + "; ".join(str(g) for g in list(tor_gruende)[:3]))
    if geheilt != dicht and (nachher is None or nachher < rc.NEW_FLESCH_MIN):
        fails.append(f"Der geheilte Text liegt unter der Schwelle: {nachher}")
    if "→" not in status2:
        fails.append(f"Der Wirkungsnachweis fehlt im Status: {status2}")

    # 4) Ohne Mess-SSOT bleibt es ehrlich (fail-open im Schreiber).
    ohne, f_wert, s_wert = sichern(dicht, "probe-ohne", rc_mod=None, heiler=None)
    if ohne != dicht or f_wert is not None or "nicht verfügbar" not in s_wert:
        fails.append("Ohne Mess-SSOT wurde nicht ehrlich gemeldet")

    if fails:
        for f in fails:
            print("❌ " + f)
        return 1
    print("✅ lesbarkeit_schreiber --selftest OK (SSOT-Schwelle · Stufe A + Tor T1–T4 "
          "· ehrliche Restlücke)")
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--selftest" in argv:
        return selftest()
    print(__doc__)
    return 0


if __name__ == "__main__":
    sys.exit(main())
