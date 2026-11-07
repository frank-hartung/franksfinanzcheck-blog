#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ============================================================
#  EINZIGARTIGKEITS-STRUKTUR-HEILER (#1099, 07.11.2026)
# ------------------------------------------------------------
#  WARUM ES DIESEN HEILER GIBT
#
#  Das Tagesaudit (#1099) fand erneut ein Paar über der Schwelle –
#  und wie bei #766 war ein Teil des Befunds kein kopierter Text,
#  sondern GENERATOR-STRUKTUR: `claude_writer` und `poppy_repurpose`
#  schrieben jedem Artikel dasselbe Kapitelgerüst vor:
#
#      ## Häufige Fehler und wie du sie vermeidest
#      | Fehler | Warum er teuer wird | Wie du ihn vermeidest |
#
#  Stehen Überschrift und Tabellenkopf in zwei Artikeln direkt
#  hintereinander, ergeben sie allein 5 gleiche 7-Wort-Phrasen –
#  exakt `KRITISCH_AB`. Der Generator erzeugte den Befund, den das
#  Audit danach als „Duplicate Content" meldete.
#
#  WAS DIESER HEILER TUT (und was nicht)
#
#    * Er heilt NUR Struktur-Befunde: Ein Paar gilt als heilbar,
#      wenn die Überlappung nach Entfernen der registrierten
#      Strukturzeilen (generische Fehler-Überschrift + generischer
#      Fehler-Tabellenkopf) aus BEIDEN Texten unter `KRITISCH_AB`
#      fällt. Bleibt echte Prosa-Dopplung übrig, meldet er sie nur –
#      umformuliert wird NICHTS (kein Auto-Rewriting, #1027-Vertrag).
#    * Ersetzt wird deterministisch aus einem Pool themenneutraler,
#      paarweise audit-sicherer Varianten (Muster von #766:
#      `redaktions_standard.FAUSTREGEL_POOL`). Gewählt wird die erste
#      Variante, die gegen den GESAMTEN Bestand unter der Schwelle
#      bleibt – der Heiler kann den Befund nicht selbst neu erzeugen.
#    * Geheilt wird der jüngere/nicht-live Artikel eines Paares.
#      Live-Artikel nur mit `--auch-live`. Versiegelte Artikel
#      (`inhalt_sha256` im Frontmatter) werden NIE angefasst.
#    * Jede Heilung wird in `data/einzigartigkeit_struktur_history.jsonl`
#      protokolliert und per Nachmessung bewiesen, bevor geschrieben
#      wird (in-memory simuliert; schlägt die Nachmessung fehl,
#      bleibt die Datei unverändert).
#
#  EINE MESSUNG, KEINE ZWEITE WAHRHEIT
#    `clean_body`, `ngrams`, `KRITISCH_AB`, `lade_bestand` kommen aus
#    `check_uniqueness`. Dieses Modul definiert keine Schwelle.
#
#  NUTZUNG
#    python3 scripts/einzigartigkeit_struktur_heiler.py            # nur Befund
#    python3 scripts/einzigartigkeit_struktur_heiler.py --fix      # heilen
#    python3 scripts/einzigartigkeit_struktur_heiler.py --fix --auch-live
#    python3 scripts/einzigartigkeit_struktur_heiler.py --selftest
#
#  Exit: 0 = kein (heilbarer oder echter) Struktur-Befund offen
#        1 = offener Befund (echt oder ohne --fix/--auch-live blockiert)
#        2 = Werkzeugfehler / Selbsttest rot
# ============================================================
import argparse
import datetime
import hashlib
import json
import os
import re
import sys
from itertools import combinations

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BLOG_DIR, "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import check_uniqueness as cu  # noqa: E402  DIE eine Messung

KRITISCH_AB = cu.KRITISCH_AB
PHRASE_LEN = cu.PHRASE_LEN
HISTORY = os.path.join(BLOG_DIR, "data", "einzigartigkeit_struktur_history.jsonl")

# --- Registrierte Strukturzeilen (Generator-Gerüst, kein Inhalt) --------
UEBERSCHRIFT_RE = re.compile(
    r"^(?P<hash>#{2,3})[ \t]*Häufige Fehler und wie du sie vermeidest[ \t]*$", re.M)
TABELLENKOPF_RE = re.compile(
    r"^\|[ \t]*Fehler[ \t]*\|[ \t]*Warum er teuer wird[ \t]*\|[ \t]*Wie du ihn vermeidest[ \t]*\|[ \t]*$", re.M)
STRUKTUR_RES = (UEBERSCHRIFT_RE, TABELLENKOPF_RE)

# --- Varianten-Pool: (Überschrift, Tabellenkopf) -------------------------
# Paarweise und gegen das Original audit-sicher: Keine Variante teilt mit
# einer anderen oder mit dem Original eine 7-Wort-Phrase (Selbsttest Fall 2).
POOL = [
    ("## Diese Fehler kosten dich unnötig Geld – so vermeidest du sie",
     "| Stolperfalle | Was sie dich kostet | So gehst du ihr aus dem Weg |"),
    ("## Typische Stolperfallen – und wie du sie umgehst",
     "| Stolperfalle | Warum sie ins Geld geht | Deine Gegenmaßnahme |"),
    ("## Wo andere Leser Geld verlieren – und du nicht",
     "| Denkfehler | Was er dich kostet | So machst du es besser |"),
    ("## Die teuersten Denkfehler im Überblick",
     "| Irrtum | Warum er teuer endet | Die bessere Entscheidung |"),
    ("## Fehler, die fast jeder macht – und ihre Lösung",
     "| Fehlerquelle | Der Preis dafür | So stellst du es ab |"),
    ("## Achtung, Kostenfalle: Diese Fehler solltest du kennen",
     "| Kostenfalle | Wie sie entsteht | Wie du sie entschärfst |"),
    ("## Was schiefgehen kann – und wie du es verhinderst",
     "| Risiko | Was dann passiert | Deine Vorsorge dagegen |"),
    ("## Aus Fehlern anderer lernen: Das solltest du anders machen",
     "| Klassischer Fehler | Die Folge für dein Budget | Was stattdessen hilft |"),
]


def hat_struktur(text: str) -> bool:
    """True fuer Markdown-Rohtext UND clean_body-Text (dort ohne ## / |)."""
    if any(rx.search(text) for rx in STRUKTUR_RES):
        return True
    ziel = {cu.norm("Häufige Fehler und wie du sie vermeidest"),
            cu.norm("Fehler Warum er teuer wird Wie du ihn vermeidest")}
    return any(cu.norm(z) in ziel for z in text.splitlines())


def ohne_struktur(body: str) -> str:
    """clean_body-Text ohne die registrierten Strukturzeilen (Diagnose).

    clean_body hat Markdown laengst entfernt (## und | sind weg) - die
    Diagnose muss deshalb auf dem normalisierten Zeilentext arbeiten,
    nicht auf der Markdown-Quellform.
    """
    ziel = {cu.norm("Häufige Fehler und wie du sie vermeidest"),
            cu.norm("Fehler Warum er teuer wird Wie du ihn vermeidest")}
    return "\n".join(z for z in body.splitlines() if cu.norm(z) not in ziel)


def ueberlappung(body_a: str, body_b: str) -> int:
    return len(cu.ngrams(body_a, PHRASE_LEN) & cu.ngrams(body_b, PHRASE_LEN))


def ist_versiegelt(raw: str) -> bool:
    kopf = raw.split("---", 2)[1] if raw.startswith("---") and raw.count("---") >= 2 else ""
    return "inhalt_sha256" in kopf


def befunde(bestand: dict) -> list[dict]:
    """Paare über der Schwelle, klassifiziert: 'struktur' (heilbar) / 'echt'."""
    treffer = []
    for pfad_a, pfad_b in combinations(sorted(bestand), 2):
        a, b = bestand[pfad_a], bestand[pfad_b]
        n = ueberlappung(a["body"], b["body"])
        if n < KRITISCH_AB:
            continue
        rest = ueberlappung(ohne_struktur(a["body"]), ohne_struktur(b["body"]))
        treffer.append({
            "a": a, "b": b, "n": n, "rest": rest,
            "art": "struktur" if rest < KRITISCH_AB else "echt",
        })
    return treffer


def ziel_eintrag(treffer: dict) -> dict:
    """Heil-Ziel: nicht-live vor live, dann der jüngere Artikel."""
    a, b = treffer["a"], treffer["b"]
    return sorted([a, b], key=lambda e: (e["live"], str(e["date"] or "")))[-1]


def ersetze_struktur(raw: str, variante: tuple[str, str]) -> str:
    """Ersetzt NUR die registrierten Strukturzeilen durch die Pool-Variante."""
    ueberschrift, kopf = variante
    raw = UEBERSCHRIFT_RE.sub(lambda m: m.group("hash") + " " + ueberschrift.lstrip("# ").strip(), raw)
    raw = TABELLENKOPF_RE.sub(lambda m: kopf, raw)
    return raw


def heilen(bestand, auch_live=False, schreibe=True, history_pfad=HISTORY, jetzt=None):
    """Heilt Struktur-Befunde. Gibt (geheilt, offen) zurueck."""
    geheilt, offen = [], []
    bodies = {p: e["body"] for p, e in bestand.items()}
    pfade = {e["slug"]: p for p, e in bestand.items()}
    for treffer in befunde(bestand):
        if treffer["art"] == "echt":
            offen.append({**treffer, "grund": "echte Prosa-Ueberlappung - keine Auto-Heilung"})
            continue
        ziel = ziel_eintrag(treffer)
        partner = treffer["b"] if ziel is treffer["a"] else treffer["a"]
        pfad = pfade[ziel["slug"]]
        if not hat_struktur(bodies[pfad]):
            ziel, partner = partner, ziel
            pfad = pfade[ziel["slug"]]
        if not hat_struktur(bodies[pfad]):
            offen.append({**treffer, "grund": "kein heilbares Struktur-Ziel im Paar"})
            continue
        if ziel["live"] and not auch_live:
            offen.append({**treffer, "grund": f"Heil-Ziel {ziel['slug']} ist live (nur mit --auch-live)"})
            continue
        raw = bestand[pfad].get("_roh") or open(pfad, encoding="utf-8").read()
        if ist_versiegelt(raw):
            offen.append({**treffer, "grund": f"{ziel['slug']} ist versiegelt (inhalt_sha256)"})
            continue
        gewaehlt = None
        for variante in POOL:
            kandidat_raw = ersetze_struktur(raw, variante)
            if kandidat_raw == raw:
                continue
            kandidat_body = cu.clean_body(kandidat_raw)
            if all(ueberlappung(kandidat_body, b) < KRITISCH_AB
                   for p2, b in bodies.items() if p2 != pfad):
                gewaehlt = (variante, kandidat_raw, kandidat_body)
                break
        if gewaehlt is None:
            offen.append({**treffer, "grund": "keine Pool-Variante bleibt unter der Schwelle"})
            continue
        variante, kandidat_raw, kandidat_body = gewaehlt
        if schreibe:
            with open(pfad, "w", encoding="utf-8") as fh:
                fh.write(kandidat_raw)
            eintrag = {"datum": jetzt or datetime.datetime.now(datetime.timezone.utc).isoformat(),
                       "slug": ziel["slug"], "live": bool(ziel["live"]), "partner": partner["slug"],
                       "vorher": treffer["n"], "variante": variante[0], "issue": 1099}
            os.makedirs(os.path.dirname(history_pfad), exist_ok=True)
            with open(history_pfad, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        bodies[pfad] = kandidat_body
        geheilt.append({**treffer, "ziel": ziel["slug"], "variante": variante[0],
                        "nachher": ueberlappung(kandidat_body, bodies[pfade[partner["slug"]]])})
    return geheilt, offen


def _artikel(slug, live, date, intro):
    roh = ("## Häufige Fehler und wie du sie vermeidest\n\n" + intro + "\n\n"
           "| Fehler | Warum er teuer wird | Wie du ihn vermeidest |\n"
           "|---|---|---|\n| a | b | c |\n")
    return {"slug": slug, "title": slug, "body": cu.clean_body("---\ntitle: x\n---\n" + roh),
            "live": live, "grund": "", "date": date, "_roh": roh}


def selftest() -> list[str]:
    fehler = []
    eigen_a = "Stromkosten senken beginnt beim Zaehlerstand und endet beim Tarifvergleich."
    eigen_b = "Urlaubskasse fuellen gelingt mit Wochenzielen und kleinen festen Betraegen."
    # Fall 1: Reiner Struktur-Befund wird erkannt und klassifiziert.
    paar = {"a/index.md": _artikel("a", False, "2026-01-01", eigen_a),
            "b/index.md": _artikel("b", False, "2026-01-02", eigen_b)}
    bf = befunde(paar)
    if len(bf) != 1 or bf[0]["art"] != "struktur":
        fehler.append(f"Fall 1: Struktur-Befund nicht erkannt: {[(x['n'], x['art']) for x in bf]}")
    # Fall 2: Pool ist in sich und gegen das Original audit-sicher.
    originale = paar["a/index.md"]["body"]
    for i, v in enumerate(POOL):
        geheilt_body = cu.clean_body("---\ntitle: x\n---\n" + ersetze_struktur(paar["b/index.md"]["_roh"], v))
        if ueberlappung(geheilt_body, originale) >= KRITISCH_AB:
            fehler.append(f"Fall 2: Pool-Variante {i} kollidiert mit dem Original")
        for j, w in enumerate(POOL):
            if j <= i:
                continue
            andere = cu.clean_body("---\ntitle: x\n---\n" + ersetze_struktur(paar["a/index.md"]["_roh"], w))
            if ueberlappung(geheilt_body, andere) >= KRITISCH_AB:
                fehler.append(f"Fall 2: Pool-Varianten {i}/{j} kollidieren miteinander")
    # Fall 3 (Freibrief-Schutz): Echte Prosa-Dopplung wird NICHT geheilt.
    prosa = " ".join(f"wort{i}" for i in range(30))
    echt = {"a/index.md": _artikel("a", False, "2026-01-01", prosa),
            "b/index.md": _artikel("b", False, "2026-01-02", prosa)}
    bf = befunde(echt)
    if not bf or bf[0]["art"] != "echt":
        fehler.append("Fall 3: echte Prosa-Dopplung nicht als 'echt' klassifiziert")
    # Fall 4: Heilung senkt das Paar unter die Schwelle, Ziel = juengerer Entwurf.
    g, o = heilen(paar, schreibe=False)
    if len(g) != 1 or g[0]["ziel"] != "b" or g[0]["nachher"] >= KRITISCH_AB:
        fehler.append(f"Fall 4: Heilung wirkungslos/falsches Ziel: {g} / {o}")
    # Fall 5: Live-Ziel ohne --auch-live bleibt unangetastet.
    live_paar = {"a/index.md": _artikel("a", True, "2026-01-01", eigen_a),
                 "b/index.md": _artikel("b", True, "2026-01-02", eigen_b)}
    g, o = heilen(live_paar, schreibe=False)
    if g or not o:
        fehler.append("Fall 5: Live-Artikel ohne --auch-live geheilt")
    # Fall 6: Ersetzung ist zielgenau - Fliesstext bleibt, Struktur verschwindet.
    neu = ersetze_struktur(paar["a/index.md"]["_roh"], POOL[0])
    if hat_struktur(neu) or "Stromkosten senken beginnt" not in neu:
        fehler.append("Fall 6: Ersetzung trifft Struktur nicht oder frisst Fliesstext")
    # Fall 8: Die Ersetzung frisst keine Leerzeile nach der Ueberschrift
    # (\s*$ im Muster wuerde sie sonst mitkonsumieren).
    if "so vermeidest du sie\n\nStromkosten" not in neu and "aus dem Weg |\n" not in neu:
        fehler.append("Fall 8: Leerzeile nach der Ueberschrift wurde mitkonsumiert")
    # Fall 7: Siegel-Erkennung.
    if not ist_versiegelt("---\ninhalt_sha256: abc\n---\nText") or ist_versiegelt("---\ntitle: x\n---\ninhalt_sha256 im Text"):
        fehler.append("Fall 7: ist_versiegelt falsch")
    return fehler


def main() -> int:
    ap = argparse.ArgumentParser(description="Einzigartigkeits-Struktur-Heiler (#1099)")
    ap.add_argument("--fix", action="store_true", help="Struktur-Befunde deterministisch heilen")
    ap.add_argument("--auch-live", action="store_true", help="auch live Artikel heilen (nur mit --fix)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    if args.selftest:
        fehler = selftest()
        if fehler:
            print("SELBSTTEST ROT:")
            [print(" -", f) for f in fehler]
            return 2
        print(f"✅ Selbsttest: 8 eingefrorene Fälle (Struktur-Erkennung, Pool-Sicherheit, Freibrief-Schutz, Live-/Siegel-Schutz) stimmen.")
        return 0
    bestand = cu.lade_bestand()
    if not bestand:
        print("🛑 Leerer Bestand – Werkzeugfehler, kein leeres Grün.")
        return 2
    if args.fix:
        geheilt, offen = heilen(bestand, auch_live=args.auch_live, schreibe=True)
        for g in geheilt:
            print(f"🩹 GEHEILT {g['a']['slug']} ↔ {g['b']['slug']}: Ziel {g['ziel']} → „{g['variante'][3:]}\" (nachher: {g['nachher']} Phrasen)")
    else:
        treffer = befunde(bestand)
        geheilt = []
        offen = [{**t, "grund": "ohne --fix nur Befund"} if t["art"] == "struktur"
                 else {**t, "grund": "echte Prosa-Überlappung – keine Auto-Heilung"} for t in treffer]
        for t in treffer:
            print(f"{'🧱' if t['art'] == 'struktur' else '🚨'} {t['art'].upper()} {t['a']['slug']} ↔ {t['b']['slug']}: {t['n']} Phrasen (Rest ohne Struktur: {t['rest']})")
    for o_ in offen:
        print(f"⚠️ OFFEN {o_['a']['slug']} ↔ {o_['b']['slug']}: {o_['grund']}")
    print(f"Ergebnis: geheilt: {len(geheilt)} | offen: {len(offen)}")
    return 1 if offen else 0


if __name__ == "__main__":
    sys.exit(main())
