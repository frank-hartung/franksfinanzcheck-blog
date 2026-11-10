#!/usr/bin/env python3
"""F4-Entscheidungsvorlage (#1098) – das Dossier für die MENSCHLICHE Entscheidung.

F4 (`data/release_scorecard.yaml`: `entscheidung: human`) ist die einzige
Prüfung, die keine Maschine schließen darf. Damit der Herausgeber sie in einem
Durchgang schließen kann, braucht er je Befund:

  * den Wortlaut der Beanstandung und die Quelle,
  * die **frühere** Entscheidung (wer, wann, mit welcher Begründung),
  * die **heutige** Textlage: stehen die beanstandeten Werte noch im Artikel –
    und sind sie dort gekennzeichnet,
  * den fertigen Schließweg (`faktenfrische_befund_ledger.py --entscheiden`).

WARUM DIESES SKRIPT EXISTIERT
  In #1098 wurde genau dieses Dossier von Hand gebaut. Es war nach dem nächsten
  Automatik-Commit unvollständig (5 neue Befunde auf einem Artikel, den die
  Tageswache erst danach geprüft hatte) – ein Dossier, das der Wirklichkeit
  hinterherläuft, ist derselbe Fehler wie ein veraltetes Register. Deshalb ist
  die Vorlage jetzt eine Projektion mit `--check` und einem Test
  (`scripts/tests/test_1098_produktionswahrheit.py`), der beweist, dass jeder
  offene Live-Befund im Dokument steht.

DAS DOKUMENT ENTSCHEIDET NICHTS
  Es schreibt in keinen Ledger und schließt keinen Befund. Es macht nur
  sichtbar, was zu entscheiden ist.

Nutzung:
  python3 scripts/f4_entscheidungsvorlage.py             # schreiben
  python3 scripts/f4_entscheidungsvorlage.py --check     # Exit 1 = veraltet
  python3 scripts/f4_entscheidungsvorlage.py --stdout    # nur ausgeben
  python3 scripts/f4_entscheidungsvorlage.py --stichtag 2026-11-10

Exit: 0 = geschrieben/aktuell · 1 = veraltet (--check) · 2 = Werkzeugfehler
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

ZIEL = ROOT / "F4-ENTSCHEIDUNGSVORLAGE.md"
POSTS = ROOT / "content" / "posts"
ENTSCHEIDUNGEN = ROOT / "data" / "faktenfrische_entscheidungen.yaml"

# Werte mit Einheit – bewusst MIT Einheit: „2026“ ist kein Betrag
# (Lehre aus der ersten Handfassung, in der die Zahl „2026“ als Wert galt).
ZAHL = re.compile(
    r"(?<![\w.,])(\d{1,3}(?:\.\d{3})*(?:,\d+)?|\d+(?:,\d+)?)"
    r"\s*(€|Euro|Prozent|%|Cent|ct|kWh|kW|Stunden|Stunde|Tage|Jahre|Monate|Grad)"
)
KENNZEICHNUNG = ("modellwert", "modellrechnung", "beispielwert", "rechenannahme",
                 "als beispiel", "beispielrechnung", "schätzwert", "annahme",
                 "gekennzeichnet", "orientierungswert")


def prosa(text: str) -> str:
    """Artikelkörper ohne Frontmatter (für den Werteabgleich)."""
    teile = text.split("---", 2)
    return teile[2] if len(teile) >= 3 else text


def datei_hash(pfad: Path) -> str:
    return hashlib.sha256(pfad.read_bytes()).hexdigest()


def entscheidungen() -> dict[tuple[str, str], list[dict]]:
    """(slug, befund_id) → Entscheidungen in zeitlicher Reihenfolge."""
    import yaml
    try:
        daten = yaml.safe_load(ENTSCHEIDUNGEN.read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001 – fail-closed: ohne Entscheidungen kein Dossier
        raise SystemExit(f"🛑 Entscheidungen nicht lesbar: {exc.__class__.__name__}: {exc}")
    liste = daten.get("entscheidungen") if isinstance(daten, dict) else None
    register: dict[tuple[str, str], list[dict]] = {}
    for eintrag in liste or []:
        if not isinstance(eintrag, dict):
            continue
        schluessel = (str(eintrag.get("slug") or ""), str(eintrag.get("befund_id") or ""))
        register.setdefault(schluessel, []).append(eintrag)
    for treffer in register.values():
        treffer.sort(key=lambda e: str(e.get("entschieden_am") or ""))
    return register


def werte(beanstandung: str) -> list[tuple[str, str]]:
    """(Zahl, Einheit) aus der Beanstandung – in Textreihenfolge, ohne Dubletten."""
    gesehen, ergebnis = set(), []
    for treffer in ZAHL.finditer(beanstandung):
        paar = (treffer.group(1), treffer.group(2))
        if paar not in gesehen:
            gesehen.add(paar)
            ergebnis.append(paar)
    return ergebnis


def _zahl_muster(wert: str) -> re.Pattern:
    """1.100 € findet auch 1100 € – Trenner bleiben trennbar."""
    teile = [re.escape(t) for t in re.split(r"[.,]", wert) if t]
    return re.compile(r"[.,]?".join(teile))


def lage(text: str, beanstandung: str) -> tuple[str, str]:
    """Heutige Textlage zu den beanstandeten Werten.

    Rückgabe: (Kurzfassung für die Tabelle, Langfassung für den Befund-Block).
    """
    werte_liste = werte(beanstandung)
    if not werte_liste:
        return ("kein Wert genannt (Aussage/Präzision)",
                "Kein Zahlenwert – die Beanstandung betrifft Aussage/Präzision.")
    zeilen = text.splitlines()
    fehlend, gefunden = [], []
    for wert, einheit in werte_liste:
        muster = _zahl_muster(wert)
        treffer = [i for i, zeile in enumerate(zeilen, 1) if muster.search(zeile)]
        if not treffer:
            fehlend.append(f"{wert} {einheit}")
            continue
        zeile = zeilen[treffer[0] - 1].lower()
        kennung = next((k for k in KENNZEICHNUNG if k in zeile), None)
        gefunden.append((f"{wert} {einheit}", treffer[0], kennung))
    kurz = []
    if fehlend:
        kurz.append("nicht mehr im Text: " + ", ".join(fehlend))
    for wert, nummer, kennung in gefunden:
        kurz.append(f"{wert} in Zeile {nummer} "
                    + ("gekennzeichnet" if kennung else "ohne Kennzeichnung"))
    lang = []
    if fehlend:
        lang.append("Im heutigen Text nicht mehr vorhanden: " + ", ".join(fehlend))
    for wert, nummer, kennung in gefunden:
        lang.append(f"Heute in Zeile {nummer}: {wert} – "
                    + (f"gekennzeichnet („{kennung}“)" if kennung else "**ohne** Kennzeichnung"))
    if not kurz:
        kurz.append("Werte im Text nicht gefunden")
    return (" · ".join(kurz), "\n".join(f"- {z}" for z in lang))


def baue(stichtag: dt.date) -> str:
    import faktenfrische_befund_akte as akte
    import faktenfrische_befund_ledger as ledger

    befunde = ledger.befunde_mit_status(stichtag=stichtag)
    live = akte.live_seiten()
    entschieden = entscheidungen()

    offen = [b for b in befunde if b["slug"] in live]
    neu = [b for b in offen if (b["slug"], b["id"]) not in entschieden]
    alt = [b for b in offen if (b["slug"], b["id"]) in entschieden]
    seiten = sorted({b["slug"] for b in offen})

    z: list[str] = []
    z.append(f"# F4-Entscheidungsvorlage — Stand {stichtag.isoformat()} (Vorschlag)")
    z.append("")
    z.append("**Status: VORSCHLAG – nichts entschieden.** Die Artikel bleiben in der")
    z.append("Scorecard blockiert, bis der Herausgeber die heutigen Fassungen bestätigt.")
    z.append("Dieses Dokument schreibt nichts in den Ledger und erzeugt keine Entscheidung.")
    z.append("")
    z.append(f"**{len(offen)} offene Live-Befunde auf {len(seiten)} Artikeln.** Davon sind "
             f"**{len(alt)}** bereits früher entschieden und durch eine spätere Textänderung")
    z.append(f"wieder geöffnet worden (fassungsgebundene Bindung, kein Rückfall). "
             f"**{len(neu)}** Befunde sind neu.")
    z.append("")
    z.append(f"Erzeugt von `scripts/f4_entscheidungsvorlage.py` aus "
             f"`data/faktenfrische_befunde_state.json`,")
    z.append("`data/faktenfrische_entscheidungen.yaml`, dem Scorecard-Siegel und den "
             "heutigen Artikeln.")
    z.append("Regel: F4 ist per SSOT **menschlich** – die Maschine schließt hier nichts.")
    z.append("")

    z.append("## Neu ohne frühere Entscheidung")
    z.append("")
    if neu:
        for b in sorted(neu, key=lambda x: (x["slug"], x["id"])):
            z.append(f"- `{b['id']}` · `{b['slug']}` · {b.get('text') or ''}")
    else:
        z.append("_Keine – jeder offene Live-Befund hat eine frühere Entscheidung._")
    z.append("")

    for slug in seiten:
        pfad = POSTS / slug / "index.md"
        eintraege = sorted([b for b in offen if b["slug"] == slug],
                           key=lambda b: b["id"])
        z.append(f"## `{slug}`")
        z.append("")
        if pfad.exists():
            z.append(f"- Datei-SHA256 (heute): `{datei_hash(pfad)}`")
            body = prosa(pfad.read_text(encoding="utf-8"))
        else:
            z.append("- Datei-SHA256 (heute): **Datei fehlt**")
            body = ""
        z.append(f"- Offene Live-Befunde: **{len(eintraege)}**")
        z.append("")
        z.append("| Befund | Typ | Frühere Entscheidung | Betroffene Werte heute | Befund |")
        z.append("|---|---|---|---|---|")
        for b in eintraege:
            frueher = entschieden.get((slug, b["id"]), [])
            if frueher:
                letzte = frueher[-1]
                kennung = (f"{letzte.get('entschieden_am') or '–'} · "
                           f"{len(frueher)}. Entscheidung")
            else:
                kennung = "**neu**"
            kurz, _ = lage(body, b.get("text") or "")
            text = str(b.get("text") or "").replace("|", "\\|")
            if len(text) > 120:
                text = text[:117].rstrip() + "…"
            z.append(f"| `{b['id']}` | {b.get('typ') or '–'} | {kennung} | {kurz} | {text} |")
        z.append("")

        for b in eintraege:
            frueher = entschieden.get((slug, b["id"]), [])
            z.append(f"### `{b['id']}`")
            z.append("")
            z.append(f"**Befund:** {b.get('text') or ''}")
            z.append("")
            if frueher:
                letzte = frueher[-1]
                z.append(f"**Frühere Entscheidung ({letzte.get('entschieden_am') or '–'}):** "
                         f"{letzte.get('entschieden_von') or '–'}")
                z.append("")
                begruendung = str(letzte.get("begruendung") or "").strip()
                if begruendung:
                    z.append("> " + begruendung.replace("\n", "\n> "))
                    z.append("")
            else:
                z.append("**Frühere Entscheidung:** keine – dieser Befund ist neu.")
                z.append("")
            _, lang = lage(body, b.get("text") or "")
            z.append(lang)
            z.append("")

    z.append("---")
    z.append("")
    z.append("## Schließweg (eine Zeile je Befund)")
    z.append("")
    z.append("```bash")
    for b in sorted(offen, key=lambda x: (x["slug"], x["id"])):
        z.append(f'python3 scripts/faktenfrische_befund_ledger.py --entscheiden {b["id"]} '
                 f'--von "<Name>" --begruendung "<was am heutigen Text geprüft wurde>"')
    z.append("python3 scripts/faktenfrische_befund_akte.py --schreiben")
    z.append("python3 scripts/release_scorecard.py --live --streng")
    z.append("```")
    z.append("")
    z.append("_Jede Entscheidung ist fassungsgebunden: Sie gilt für den heute geprüften")
    z.append("Text (Projektion `betrieb-v3`). Ändert sich ein Satz, öffnet der Befund")
    z.append("erneut – das ist gewollt. Abgeleitete Blöcke und Leerzeilen öffnen nichts._")
    z.append("")
    return "\n".join(z)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F4-Entscheidungsvorlage erzeugen")
    parser.add_argument("--check", action="store_true",
                        help="nur prüfen: Exit 1, wenn die Vorlage veraltet ist")
    parser.add_argument("--stdout", action="store_true", help="auf die Ausgabe schreiben")
    parser.add_argument("--stichtag", default=None, help="JJJJ-MM-TT (Vorgabe: heute)")
    args = parser.parse_args(argv)

    try:
        stichtag = (dt.date.fromisoformat(args.stichtag) if args.stichtag
                    else dt.date.today())
    except ValueError:
        print("🛑 --stichtag muss JJJJ-MM-TT sein", file=sys.stderr)
        return 2

    try:
        text = baue(stichtag)
    except SystemExit as exc:
        print(str(exc), file=sys.stderr)
        return 2

    if args.stdout:
        print(text, end="")
        return 0

    if args.check:
        try:
            alt = ZIEL.read_text(encoding="utf-8")
        except OSError:
            print(f"🛑 {ZIEL.name} fehlt – python3 scripts/f4_entscheidungsvorlage.py")
            return 1
        if alt != text:
            print(f"🛑 {ZIEL.name} ist veraltet – "
                  f"python3 scripts/f4_entscheidungsvorlage.py")
            return 1
        print(f"✅ {ZIEL.name} ist aktuell")
        return 0

    ZIEL.write_text(text, encoding="utf-8")
    print(f"✅ {ZIEL.name} geschrieben ({len(text.splitlines())} Zeilen)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
