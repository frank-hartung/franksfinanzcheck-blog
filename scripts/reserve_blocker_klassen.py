#!/usr/bin/env python3
"""
reserve_blocker_klassen.py – Welcher Reserve-Befund rechtfertigt das Löschen?

WARUM DIESE DATEI EXISTIERT (Reparatur 05.10.2026, Vorgang WF-B594,
Bot-Watchdog-Meldung #594, Run 37347512536)
---------------------------------------------------------------------------
Der Watchdog meldete „Content-Reserve niedrig – 0 gate-fertige Artikel,
6 Reserve-Entwürfe“. Der Reserve-Lauf derselben Stunde liefert die Erklärung,
und sie ist keine Produktionsschwäche:

    17:20 Zertifikat (Commit 601030e): 6 Kandidaten, 0 reif.
          Gründe ausschließlich: „Zeichenlänge (check_length.py) nicht
          bestanden" (3x) und „Faktenfrische – Erstrecherche" (3x).
    17:35 Commit c56382b „content: unabhängige Redaktionsreserve auffüllen":
          8 Entwürfe GELÖSCHT (1.815 Zeilen Artikeltext, 24 Cover-Dateien),
          1 neuer Entwurf angelegt.

Gelöscht hat `reserve_janitor.py`. Seine Löschliste kam aus `draft_triage`
(Zustand BLOCKIERT) – und zwei der dortigen Hindernisse treffen JEDEN frisch
erzeugten Maschinen-Entwurf per Konstruktion:

    * „laenge: <n> Zeichen < Soll 10000"  – der Rohtext ist immer kürzer als
      der Floor; gehoben wird er erst von der Heiler-Kette (check_length ->
      extend_articles). Ist der Gratis-Provider im Cooldown, bleibt der
      Entwurf kurz – ein ÄUSSERER Ausfall, kein Urteil über den Artikel.
    * „interne links: <n> (Soll >= 2)" – die Reserve-Kette fährt den
      Internal-Linker (bis zu dieser Reparatur) überhaupt nicht.

Damit war die Produktionslinie ein Kreislauf, der sich selbst auffrisst:
produzieren -> am Gate scheitern -> am nächsten Morgen VOR der Heiler-Kette
löschen -> Thema im Ledger verbrannt -> wieder bei null anfangen. Der Pool
konnte das Ziel strukturell nie erreichen, und das Watchdog-Ticket kam jeden
Tag zurück (#251, #272, #281, #393, #446, #462, #520, #594).

Die zweite Schieflage war die Beweislast. `reserve_quarantine.py` nimmt einem
Kandidaten nur die FAHNE (reversibel, Artikel bleibt liegen) – und verlangt
dafür zwei Läufe mit demselben Fund. Der Janitor LÖSCHT die Datei samt Cover
(unwiderruflich) – und verlangte dafür eine einzige Triage-Sichtung, auch bei
einem Entwurf, der zehn Minuten vorher entstanden war. Die schwächere Folge
hatte den stärkeren Beweis.

DIESE DATEI IST DIE EINE QUELLE der Antwort auf: „Ist dieser Befund heilbar?"

    HEILBAR    Ein Heiler der Reserve-Kette (reserve_finisher.HEALER_CHAIN)
               kann den Befund auflösen. Solche Entwürfe werden NIE gelöscht.
               Sie bleiben Material – auch über Provider-Ausfälle hinweg.
    UNHEILBAR  Kein Heiler kann das auflösen (Quelltext-Defekt, fehlender
               Titel, rückdatierter Entwurf). Hier darf der Janitor löschen –
               aber erst mit Beleg (mehrere Läufe) und nach Karenzzeit.

Die Tabelle wird von `reserve_healer_coverage.py` gegen die echte Heiler-Kette
geprüft: Ein als „heilbar" deklarierter Befund, dessen Heiler nicht in der
Kette läuft, ist eine Lücke und bricht den Lauf (fail-closed). Ein neuer
Triage-Blocker ohne Eintrag ebenfalls – niemand soll je wieder eine
Löschregel einführen, ohne die Heilung mitzuliefern.

MODI:
    python3 scripts/reserve_blocker_klassen.py            # Tabelle zeigen
    python3 scripts/reserve_blocker_klassen.py --json     # maschinenlesbar
    python3 scripts/reserve_blocker_klassen.py --selftest # Sabotage-Schutz

EXIT: 0 = ok · 2 = Selbsttest fehlgeschlagen
"""
from __future__ import annotations

import argparse
import json
import re
import sys

HEILBAR = "heilbar"          # ein Heiler der Kette löst das auf -> nie löschen
MENSCHLICH = "menschlich"    # nur ein Mensch darf das -> nie automatisch löschen
UNHEILBAR = "unheilbar"      # Torso/Quelldefekt -> löschbar, aber mit Beleg
TRANSIENT = "transient"      # Werkzeug-/Infrastrukturfehler -> kein Urteil

# ---------------------------------------------------------------------------
#  VERTRAG (eine Quelle): Triage-Hindernis -> Klasse + Begründung + Heiler.
#
#  `praefix` ist der Wortlaut, mit dem `draft_triage.classify()` den Blocker
#  schreibt. Die Zuordnung ist bewusst über den Präfix geführt (nicht über
#  einen Code): Die Triage ist die Wache, die diese Texte erzeugt, und ein
#  umbenannter Blocker fällt in der Deckungsprüfung sofort auf, statt still
#  in die falsche Klasse zu rutschen.
# ---------------------------------------------------------------------------
KLASSEN: tuple[dict, ...] = (
    # ---------------------------- heilbar ----------------------------------
    {
        "praefix": "laenge:",
        "klasse": HEILBAR,
        "heiler": ("check_length.py",),
        "grund": ("Der Längen-Floor wird von der Heiler-Kette gehoben "
                  "(check_length --fix -> extend_articles). Ein kurzer "
                  "Rohtext ist der NORMALFALL direkt nach der Produktion; "
                  "bleibt er kurz, fehlte der Gratis-Provider – das ist ein "
                  "äußerer Ausfall und kein Urteil über den Artikel."),
    },
    {
        "praefix": "struktur:",
        "klasse": HEILBAR,
        "heiler": ("check_length.py",),
        "grund": ("Zu wenige H2 heilt derselbe Verlängerer, der den Floor "
                  "hebt – er schreibt den Körper mit mindestens vier "
                  "Abschnitten neu."),
    },
    {
        "praefix": "interne links:",
        "klasse": HEILBAR,
        "heiler": ("internal_linker.py",),
        "grund": ("Interne Verlinkung ist maschinelle Fleißarbeit. Der "
                  "Internal-Linker setzt sie datei-bezirkelt "
                  "(--file, nur LIVE-Ziele)."),
    },
    {
        "praefix": "beschreibung:",
        "klasse": HEILBAR,
        "heiler": ("meta_optimizer.py",),
        "grund": "Die Meta-Beschreibung erzeugt der Meta-Optimierer.",
    },
    {
        "praefix": "lastmod:",
        "klasse": HEILBAR,
        "heiler": ("reserve_finisher.py",),
        "grund": ("Der Lift auf HEUTE zieht `lastmod` verlustfrei nach "
                  "(reserve_finisher.sync_lastmod_to_date)."),
    },
    {
        "praefix": "cover:",
        "klasse": HEILBAR,
        "heiler": ("generate_covers.py", "check_covers.py"),
        "grund": ("Fehlendes oder totes Cover erzeugt/repariert die "
                  "Cover-Pipeline der Kette (slug-bezirkelt)."),
    },
    {
        "praefix": "werbekennzeichnung:",
        "klasse": HEILBAR,
        "heiler": ("affiliate_profi_check.py", "affiliate_integrity_gate.py"),
        "grund": ("Die Kennzeichnungszeile gehört zum kanonischen CTA-Block "
                  "und wird deterministisch nachgesetzt."),
    },
    {
        "praefix": "go-route:",
        "klasse": HEILBAR,
        "heiler": ("affiliate_intent_guard.py", "affiliate_link_check.py"),
        "grund": ("Eine nicht registrierte /go/-Route schreibt der "
                  "Intent-Wächter auf eine echte Route um."),
    },
    # --------------------------- unheilbar ---------------------------------
    {
        "praefix": "fm-",
        "klasse": UNHEILBAR,
        "heiler": (),
        "dominant": True,
        "grund": ("Defekte Frontmatter-Grenze/YAML: Build und Wachen lesen "
                  "verschiedene Texte. Raten wäre Datenverlust – das gehört "
                  "einem Menschen oder in die Tonne. QUELLDEFEKT: Alle "
                  "weiteren Befunde eines solchen Entwurfs (Länge, "
                  "Struktur, Links) sind Folgefehler der gescheiterten "
                  "Zerlegung und zählen deshalb nicht als Heilungschance."),
    },
    {
        "praefix": "titel:",
        "klasse": UNHEILBAR,
        "heiler": (),
        "grund": ("Ein Titel ist eine redaktionelle Aussage. Die Kette "
                  "repariert abgeschnittene Titel (check_titles), erfindet "
                  "aber keinen – ein titelloser Entwurf ist ein Torso."),
    },
    {
        "praefix": "datum:",
        "klasse": UNHEILBAR,
        "heiler": (),
        "grund": ("Unlesbares oder rückdatiertes Datum kippt die Chronologie "
                  "des Archivs. Die Reserve datiert nur VORWÄRTS (Lift auf "
                  "heute); alles andere ist ein Eingriff in die Historie."),
    },
)

_INDEX = {e["praefix"]: e for e in KLASSEN}


# ---------------------------------------------------------------------------
#  Zweite Tabelle: GATE-Befunde (die Sprache der Zertifizierung).
#
#  Sie entscheidet über ausgemusterte Kandidaten (`reserve_blocked`, gesetzt
#  von reserve_quarantine nach zwei Läufen mit demselben Fund). Auch hier gilt:
#  Die Quarantäne nimmt die Fahne – löschen darf der Janitor nur, wenn der
#  Fund weder heilbar noch Menschensache ist. Ein Kandidat, der nur auf den
#  Gratis-Provider wartet („Zeichenlänge"), ist Material, kein Müll.
#  Gesucht wird case-insensitiv als Teilzeichenkette im Fund-Text.
# ---------------------------------------------------------------------------
GATE_BEFUNDE: tuple[dict, ...] = (
    {"muster": "gate-ausnahme", "klasse": TRANSIENT,
     "grund": "Werkzeug-/Infrastrukturfehler ist kein Urteil über den Text."},
    {"muster": "timeout", "klasse": TRANSIENT,
     "grund": "Zeitüberschreitung der Werkzeugkette, kein Content-Befund."},
    {"muster": "freigabe", "klasse": MENSCHLICH,
     "grund": ("YMYL-Freigaben sind Redaktionsakte. Ein Hochrisiko-Entwurf "
               "wartet auf einen Menschen – löschen hieße, die Arbeit der "
               "Fachprüfung wegzuwerfen.")},
    {"muster": "redaktionelle", "klasse": MENSCHLICH,
     "grund": "Offene redaktionelle Prüfung gehört einem Menschen."},
    {"muster": "ymyl", "klasse": MENSCHLICH,
     "grund": "YMYL-Risikoklasse: nur mit menschlicher Freigabe."},
    {"muster": "zeichenlänge", "klasse": HEILBAR, "heiler": ("check_length.py",),
     "grund": ("Der Längen-Floor wird von der Kette gehoben; ein kurzer "
               "Entwurf heißt meist nur: Der Gratis-Provider war im "
               "Cooldown (Realfall #594).")},
    {"muster": "faktenfrische", "klasse": HEILBAR, "heiler": ("faktenfrische.py",),
     "grund": "Erst-/Folgerecherche zieht der echte Rechercheweg nach."},
    {"muster": "lesbarkeit", "klasse": HEILBAR, "heiler": ("profi_polish.py",),
     "grund": "Satzbau/Absätze hebt das Polish der Kette."},
    {"muster": "quality-score", "klasse": HEILBAR,
     "heiler": ("profi_polish.py", "spellcheck.py", "check_length.py"),
     "grund": ("Der Score ist die Summe heilbarer Teile (Rechtschreibung, "
               "Struktur, Lesbarkeit) – die Kette arbeitet genau daran.")},
    {"muster": "keyword", "klasse": HEILBAR, "heiler": ("keyword_optimizer.py",),
     "grund": "Keyword-Verteilung heilt der Optimierer."},
    {"muster": "affiliate", "klasse": HEILBAR,
     "heiler": ("affiliate_intent_guard.py", "affiliate_integrity_gate.py"),
     "grund": "CTA/Anker/Route heilen die beiden Affiliate-Wachen."},
    {"muster": "intent", "klasse": HEILBAR, "heiler": ("affiliate_intent_guard.py",),
     "grund": "IW0–IW9 heilt der Intent-Wächter datei-bezirkelt."},
    {"muster": "titel", "klasse": HEILBAR, "heiler": ("check_titles.py",),
     "grund": "Abgeschnittene Titel repariert die Titel-Wache."},
    {"muster": "dublette", "klasse": UNHEILBAR,
     "grund": ("Der Inhalt existiert bereits – ein zweites Exemplar ist "
               "kein Vorrat, sondern Kannibalismus.")},
    {"muster": "duplikat", "klasse": UNHEILBAR,
     "grund": "Doppelter Inhalt: das Original bleibt, die Kopie geht."},
    {"muster": "frontmatter", "klasse": UNHEILBAR,
     "grund": ("Defekter Quelltext-Kopf: Build und Wachen lesen "
               "verschiedene Texte – raten wäre Datenverlust.")},
)


def gate_befund_klasse(grund: str) -> dict:
    """Ordnet EINEN Zertifizierungs-Fund seiner Klasse zu (fail-closed).

    Unbekannt heißt: NICHT löschbar. Der Janitor meldet den Entwurf dann als
    verschont mit Begründung – ein unbekannter Fund ist ein Grund, genauer
    hinzusehen, nie einer, Text zu vernichten.
    """
    text = (grund or "").strip()
    niedrig = text.lower()
    for eintrag in GATE_BEFUNDE:
        if eintrag["muster"] in niedrig:
            return {"grund_text": text, "muster": eintrag["muster"],
                    "klasse": eintrag["klasse"],
                    "heiler": list(eintrag.get("heiler") or ()),
                    "grund": eintrag["grund"], "bekannt": True}
    return {"grund_text": text, "muster": None, "klasse": "unbekannt",
            "heiler": [], "bekannt": False,
            "grund": ("Unbekannter Gate-Fund – ohne Eintrag in "
                      "reserve_blocker_klassen.GATE_BEFUNDE wird nicht "
                      "gelöscht.")}


def gate_befund_loeschbar(grund: str) -> tuple[bool, dict]:
    """Rechtfertigt dieser ausgemusterte Gate-Fund eine Löschung?"""
    bewertung = gate_befund_klasse(grund)
    return bewertung["klasse"] == UNHEILBAR, bewertung


def alle() -> tuple[dict, ...]:
    """Die Tabelle (Kopie-sicher für Aufrufer)."""
    return KLASSEN


def klassifiziere(blocker: str) -> dict:
    """Ordnet EINEN Triage-Blocker-Text seiner Klasse zu.

    Unbekannt heißt fail-closed `unheilbar=False`: Ein Befund, den diese
    Tabelle nicht kennt, darf NIE zum Löschen führen. Die Deckungswache
    meldet ihn separat als Lücke – stilles Löschen auf Verdacht ist genau
    der Schaden, der #594 erzeugt hat.
    """
    text = (blocker or "").strip()
    niedrig = text.lower()
    for eintrag in KLASSEN:
        if niedrig.startswith(eintrag["praefix"]):
            return {"blocker": text, "praefix": eintrag["praefix"],
                    "klasse": eintrag["klasse"],
                    "heiler": list(eintrag["heiler"]),
                    "dominant": bool(eintrag.get("dominant")),
                    "grund": eintrag["grund"], "bekannt": True}
    return {"blocker": text, "praefix": None, "klasse": "unbekannt",
            "heiler": [], "bekannt": False, "dominant": False,
            "grund": ("Unbekannter Triage-Blocker – ohne Eintrag in "
                      "reserve_blocker_klassen.py wird nicht gelöscht.")}


def loeschbar(blocker_liste) -> tuple[bool, list[dict]]:
    """Darf ein Entwurf allein wegen dieser Hindernisse gelöscht werden?

    JA nur, wenn mindestens ein Hindernis vorliegt UND jedes einzelne als
    `unheilbar` deklariert ist. Ein einziger heilbarer (oder unbekannter)
    Befund genügt, um den Entwurf zu verschonen: Er ist dann Material, das
    die Heiler-Kette im nächsten Lauf anfassen kann.

    Eine Ausnahme kennt die Regel: einen QUELLDEFEKT (`dominant`, heute nur
    die `fm-`-Familie). Wenn die Zerlegung des Entwurfs scheitert, sind alle
    weiteren Befunde Messfehler an einem unlesbaren Text – „laenge: 80
    Zeichen" sagt dann nichts über den Artikel, sondern nur über den
    kaputten Kopf. Solche Entwürfe bleiben löschbar, sonst entstünde eine
    unräumbare Halde aus Dateien, die kein Werkzeug je anfassen kann.
    """
    bewertet = [klassifiziere(b) for b in (blocker_liste or [])]
    if not bewertet:
        return False, bewertet
    if any(e["klasse"] == MENSCHLICH for e in bewertet):
        return False, bewertet
    if any(e.get("dominant") and e["klasse"] == UNHEILBAR for e in bewertet):
        return True, bewertet
    return all(e["klasse"] == UNHEILBAR for e in bewertet), bewertet


def heilbare_heiler() -> set[str]:
    """Alle Skripte, die laut Tabelle einen Befund heilen sollen."""
    out: set[str] = set()
    for e in KLASSEN:
        if e["klasse"] == HEILBAR:
            out.update(e["heiler"])
    return out


def triage_blocker_praefixe(quelle: str | None = None) -> list[str]:
    """Liest die Blocker-Präfixe aus `draft_triage.py` – abgetippt wird nichts.

    Gesucht werden die Literale, mit denen die Triage ihre Hindernisse
    schreibt (`stand["blocker"].append("laenge: …")`, auch als f-String).
    Dadurch fällt ein NEUER Blocker in der Deckungsprüfung auf, statt still
    in die Löschliste zu rutschen.
    """
    if quelle is None:
        from pathlib import Path
        quelle = (Path(__file__).resolve().parent / "draft_triage.py"
                  ).read_text(encoding="utf-8")
    treffer: set[str] = set()
    # Nur `…blocker…].append(` / `return …, ["fm-…"]` zählen – Hinweise ohne
    # Sperrwirkung (`hinweise`) gehören ausdrücklich NICHT dazu, sie führen
    # nie zu einer Löschung.
    muster = re.compile(r"""blocker["']?\]?\.append\(""")
    literal = re.compile(r"""f?["']([^"']{2,80})["']""")
    for m in muster.finditer(quelle):
        rest = quelle[m.end():m.end() + 200]
        lit = literal.search(rest)
        if not lit:
            continue
        treffer.add(_praefix_von(lit.group(1)))
    # Quell-Defekte meldet `fm_and_body` als Rückgabewert, nicht per append.
    for m in re.finditer(r"""\[["'](fm-[a-zä-ü]+)[: ]""", quelle):
        treffer.add(m.group(1).lower() + ":")
    return sorted(t for t in treffer if t)


def _praefix_von(literal_text: str) -> str:
    """„laenge: 500 Zeichen …" -> „laenge:" · „fm-grenze: …" -> „fm-grenze:"."""
    kopf = literal_text.split(":", 1)[0].strip().lower()
    if not kopf or " " in kopf.strip() and len(kopf.split()) > 3:
        return ""
    return kopf + ":"


def bericht_text() -> str:
    zeilen = ["# 🧯 Löschklassen der Reserve (Blocker → heilbar/unheilbar)", ""]
    for e in KLASSEN:
        zeichen = "🩹" if e["klasse"] == HEILBAR else "🧱"
        heiler = ", ".join(f"`{h}`" for h in e["heiler"]) or "–"
        zeilen.append(f"- {zeichen} `{e['praefix']}` · **{e['klasse']}** · "
                      f"Heiler: {heiler}")
        zeilen.append(f"  <br>{e['grund']}")
    zeilen += ["", "Unbekannte Blocker sind nie löschbar (fail-closed)."]
    return "\n".join(zeilen)


def run_selftest() -> int:
    fehler: list[str] = []

    # 1) Die beiden Befunde aus #594 sind heilbar – und damit nie Löschgrund.
    ok, _ = loeschbar(["laenge: 6073 Zeichen < Soll 10000 (Wache: "
                       "length_guard.py)"])
    if ok:
        fehler.append("Längen-Befund darf nie zum Löschen führen (#594)")
    ok, _ = loeschbar(["interne links: 1 (Soll ≥ 2) – link_density_guard.py "
                       "zählt den Artikel als unterversorgt"])
    if ok:
        fehler.append("Link-Befund darf nie zum Löschen führen (#594)")

    # 2) Der reale Löschfall vom 05.10.: BEIDE Befunde zusammen -> verschont.
    ok, bewertet = loeschbar([
        "laenge: 6073 Zeichen < Soll 10000 (Wache: length_guard.py)",
        "interne links: 1 (Soll ≥ 2) – link_density_guard.py zählt den "
        "Artikel als unterversorgt"])
    if ok or len(bewertet) != 2:
        fehler.append("der reale #594-Entwurf wäre erneut gelöscht worden")

    # 3) Ein echter Quelltext-Defekt bleibt löschbar (sonst wird der Vorrat
    #    zur Müllhalde).
    ok, _ = loeschbar(["fm-grenze: keine schließende `---`-Zeile gefunden",
                       "titel: leer – ohne Titel kein Pin, kein OG-Tag"])
    if not ok:
        fehler.append("unheilbare Quell-Defekte müssen löschbar bleiben")

    # 4) Mischung: ein heilbarer Befund verschont den ganzen Entwurf.
    ok, _ = loeschbar(["titel: leer", "laenge: 500 Zeichen < Soll 10000"])
    if ok:
        fehler.append("ein heilbarer Befund muss den Entwurf verschonen")

    # 4b) Quelldefekt schlägt die Mischung: Bei kaputtem Frontmatter sind
    #     „laenge"/„struktur" Messfehler an einem unlesbaren Text, keine
    #     Heilungschance. Sonst wäre kein Torso je räumbar.
    ok, _ = loeschbar(["fm-grenze: keine schließende `---`-Zeile gefunden",
                       "laenge: 80 Zeichen < Soll 10000",
                       "interne links: 0 (Soll >= 2)"])
    if not ok:
        fehler.append("Quelldefekt (fm-) muss trotz Folgefehlern löschbar sein")

    # 5) Unbekannter Befund = nie löschen (fail-closed).
    ok, bewertet = loeschbar(["irgendwas-neues: hier stimmt was nicht"])
    if ok or bewertet[0]["bekannt"]:
        fehler.append("unbekannte Blocker dürfen nicht löschbar sein")

    # 6) Keine Hindernisse = kein Löschgrund.
    if loeschbar([])[0]:
        fehler.append("ohne Hindernis darf nichts gelöscht werden")

    # 7) Groß-/Kleinschreibung darf die Klasse nicht kippen.
    if klassifiziere("Laenge: 10 Zeichen")["klasse"] != HEILBAR:
        fehler.append("Klassifikation ist nicht schreibweisen-fest")

    # 7b) Gate-Befunde: die beiden realen Funde aus #594 sind heilbar, ein
    #     Werkzeugfehler ist gar kein Urteil, eine offene Freigabe gehört
    #     einem Menschen – und nichts davon rechtfertigt eine Löschung.
    for fund in ("Zeichenlänge (check_length.py) nicht bestanden",
                 "Faktenfrische nicht bestanden: Erstrecherche – noch nie "
                 "faktengeprüft",
                 "Gate-Ausnahme: hugo timeout",
                 "editorial_review: Freigabe fehlt (Risikoklasse hoch)",
                 "völlig neuer Fund ohne Eintrag"):
        loeschen, bewertung = gate_befund_loeschbar(fund)
        if loeschen:
            fehler.append(f"Gate-Fund darf nicht löschbar sein: {fund!r} "
                          f"-> {bewertung['klasse']}")
    if gate_befund_klasse("Zeichenlänge …")["klasse"] != HEILBAR:
        fehler.append("Zeichenlängen-Fund muss heilbar sein (#594)")
    if gate_befund_klasse("Gate-Ausnahme: x")["klasse"] != TRANSIENT:
        fehler.append("Werkzeugfehler muss transient sein")
    if gate_befund_klasse("Freigabe fehlt")["klasse"] != MENSCHLICH:
        fehler.append("offene Freigabe gehört einem Menschen")
    if not gate_befund_loeschbar("Dublette zu 2026-09-11-x")[0]:
        fehler.append("eine echte Dublette muss löschbar bleiben")

    # 8) Die Tabelle muss die ECHTEN Präfixe der Triage decken.
    try:
        fehlend = [p for p in triage_blocker_praefixe()
                   if not any(p.startswith(e["praefix"]) or
                              e["praefix"].startswith(p) for e in KLASSEN)]
        if fehlend:
            fehler.append(f"Triage-Blocker ohne Klasse: {fehlend}")
    except OSError as exc:
        fehler.append(f"draft_triage.py nicht lesbar: {exc}")

    if fehler:
        print("🛑 SELBSTTEST reserve_blocker_klassen FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   ✗ {f}")
        return 2
    print("✅ Selbsttest reserve_blocker_klassen: heilbar/unheilbar, "
          "Mischfall, unbekannt (fail-closed), Präfix-Deckung der Triage.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Löschklassen der Content-Reserve (Blocker → Heilung)")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    if args.json:
        print(json.dumps([{**e, "heiler": list(e["heiler"])}
                          for e in KLASSEN], ensure_ascii=False, indent=2))
        return 0
    print(bericht_text())
    return 0


if __name__ == "__main__":
    sys.exit(main())
