#!/usr/bin/env python3
"""BEFUND-AKTE – die Arbeitsdatei der Redaktion für offene Fachbefunde (#912).

WARUM DIESE DATEI EXISTIERT
---------------------------
Die Release-Scorecard meldete seit dem 27.10.2026 „Bestand blockiert“ mit
der Dimension `faktenalter`. Am 02.11.2026 war die Kadenz längst geheilt
(0 überfällig, 146 % Deckung) – rot war der Bestand trotzdem, weil **F4**
(offener Fachbefund) zehn Live-Artikel blockierte. Das Ticket nannte aber
weiter „Kadenz, kein Inhaltsbefund“, und für die 57 offenen Befunde gab es
weder eine Arbeitsliste noch einen Befehl: Die Anleitung verlangte Handarbeit
an einer YAML-Datei samt SHA-256. Ein Befund, der nur von Hand schließbar ist,
ist in der Praxis nicht schließbar – und ein Alarm ohne Schließpfad ist ein
Dauerläufer (C14).

Diese Akte ist der Schließpfad, sichtbar im Repository:
  * JEDER offene Befund steht mit ID, Typ, Alter, Beanstandung und Beleg da.
  * JEDER Befund trägt den fertigen Entscheidungsbefehl (eine Zeile).
  * JEDER Befund sagt, ob der Text seit dem Befund geändert wurde –
    dann ist der HEUTIGE Text zu prüfen (die Falle, die 8 Seiten
    unschließbar machte, ist damit sichtbar statt unsichtbar).
  * Die Frist (`befunde.frist_tage`) macht aus „irgendwann“ einen Termin;
    überschrittene Befunde stehen oben und werden im Ticket eskaliert.

Die Akte entscheidet NICHTS. Sie ist eine Sicht auf eine Regel
(`faktenfrische_befund_ledger.py`) – wie die Scorecard auf das Publish-Gate.

NUTZUNG
  python3 scripts/faktenfrische_befund_akte.py --schreiben   # Akte + Zustand
  python3 scripts/faktenfrische_befund_akte.py --wache       # Exit 1 ohne Schließweg
  python3 scripts/faktenfrische_befund_akte.py --json        # Zustand auf stdout
  python3 scripts/faktenfrische_befund_akte.py --selftest
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import faktenfrische_befund_ledger as ledger  # noqa: E402

AKTE_PATH = ROOT / "BEFUND-AKTE.md"
STATE_PATH = ROOT / "data" / "faktenfrische_befunde_state.json"
QUEUE_PATH = ROOT / "data" / "faktenfrische_queue.json"
DECISIONS_PATH = ROOT / "data" / "faktenfrische_entscheidungen.yaml"
SCORECARD_STATE = ROOT / "data" / "release_scorecard_state.json"
CONFIG_PATH = ROOT / "data" / "agent_reach" / "faktenfrische.yaml"

STANDARD_FRIST = 14
STANDARD_ESKALATION = 21
ENTSCHEIDEN = ("python3 scripts/faktenfrische_befund_ledger.py --entscheiden {id} "
               "--von \"<Name>\" --art geaendert --stelle \"<wörtlicher Satz "
               "aus dem Artikel>\" --begruendung \"<was geprüft/geändert wurde>\"")
# ^ `--art`/`--stelle` sind seit 10.11.2026 Pflicht: Eine Entscheidung, die eine
#   Änderung behauptet, muss den Satz zitieren, der sie trägt (Heilungsbeleg).

STATUS_RANG = {"ueberholt": 0, "ohne-fassung": 1, "aktuell": 2, "seite-fehlt": 3}
STATUS_TEXT = {
    "ueberholt": "Text seit dem Befund geändert – bitte den HEUTIGEN Text prüfen",
    "ohne-fassung": "Altbestand ohne Fassungs-Hash – am heutigen Text prüfen",
    "aktuell": "Text unverändert seit dem Befund",
    "seite-fehlt": "Seite nicht lesbar – nicht entscheidbar",
}


def _config() -> dict:
    """Fristen aus der SSOT (menschlich kuratiert), mit sicheren Vorgaben."""
    try:
        import yaml
        with CONFIG_PATH.open(encoding="utf-8") as fh:
            daten = yaml.safe_load(fh) or {}
    except Exception:  # noqa: BLE001 – Vorgabe statt Absturz
        daten = {}
    block = daten.get("befunde") if isinstance(daten, dict) else None
    block = block if isinstance(block, dict) else {}
    return {
        "frist_tage": int(block.get("frist_tage") or STANDARD_FRIST),
        "eskalation_tage": int(block.get("eskalation_tage") or STANDARD_ESKALATION),
    }


def live_seiten() -> dict[str, dict]:
    """slug → {urteil, risikoklasse} aus dem Scorecard-Siegel (eine Quelle)."""
    try:
        data = json.loads(SCORECARD_STATE.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    artikel = data.get("artikel") if isinstance(data, dict) else None
    if not isinstance(artikel, dict):
        return {}
    return {str(slug): {"urteil": str(a.get("urteil") or ""),
                        "risikoklasse": str(a.get("risikoklasse") or "")}
            for slug, a in artikel.items() if isinstance(a, dict)}


def _de_zahl(wert) -> str:
    return "–" if wert is None else str(wert)


def zustand_bauen(befunde: list[dict], live: dict[str, dict], *,
                  frist_tage: int, eskalation_tage: int,
                  stichtag: dt.date) -> dict:
    """Reine Funktion: Befunde + Live-Sicht → Zustand (Siegel der Akte)."""
    def ist_live(b: dict) -> bool:
        return b["slug"] in live

    offen = len(befunde)
    live_befunde = [b for b in befunde if ist_live(b)]
    ueber_frist = [b for b in befunde
                   if b.get("alter_tage") is not None and b["alter_tage"] > frist_tage]
    eskalation = [b for b in befunde
                  if b.get("alter_tage") is not None
                  and b["alter_tage"] > eskalation_tage]
    aeltester = max((b.get("alter_tage") or 0) for b in befunde) if befunde else None
    return {
        "erzeugt": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "stichtag": stichtag.isoformat(),
        "offen": offen,
        "seiten": len({b["slug"] for b in befunde}),
        "live_seiten": len({b["slug"] for b in live_befunde}),
        "live_befunde": len(live_befunde),
        "ueberholt": sum(1 for b in befunde if b["fassung_status"] == "ueberholt"),
        "ohne_fassung": sum(1 for b in befunde if b["fassung_status"] == "ohne-fassung"),
        "seite_fehlt": sum(1 for b in befunde if b["fassung_status"] == "seite-fehlt"),
        "nicht_entscheidbar": sum(1 for b in befunde if not b.get("entscheidbar")),
        "aeltester_tage": aeltester,
        "frist_tage": frist_tage,
        "eskalation_tage": eskalation_tage,
        "ueber_frist": len(ueber_frist),
        "in_eskalation": len(eskalation),
        "je_seite": {slug: sum(1 for b in befunde if b["slug"] == slug)
                     for slug in sorted({b["slug"] for b in befunde})},
        "befunde": [{k: b.get(k) for k in
                     ("slug", "ursprungs_slug", "id", "typ", "text", "beleg",
                      "alter_tage", "fassung_status", "entscheidbar",
                      "nicht_entscheidbar_grund")
                     if k != "ursprungs_slug" or b.get(k)}
                    for b in befunde],
    }


def akte_bauen(befunde: list[dict], live: dict[str, dict], zustand: dict,
               belege: dict | None = None) -> str:
    """Reine Funktion: Befunde + Zustand → Markdown-Arbeitsdatei."""
    z: list[str] = []
    add = z.append
    add("# BEFUND-AKTE – offene Fachbefunde der Faktenfrische")
    add("")
    add(f"_Stand {zustand['stichtag']} · erzeugt von "
        "`scripts/faktenfrische_befund_akte.py` · Quelle: "
        "`data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml` "
        "(eine Regel, zwei Leser)._")
    add("")
    add(f"**{zustand['offen']} offene Befunde auf {zustand['seiten']} Seiten · "
        f"davon {zustand['live_seiten']} Live-Seiten mit "
        f"{zustand['live_befunde']} Befunden · ältester "
        f"{_de_zahl(zustand['aeltester_tage'])} Tage · Frist "
        f"{zustand['frist_tage']} Tage.**")
    add("")
    add("| Kennzahl | Wert |")
    add("|---|---|")
    add(f"| Offene Befunde | {zustand['offen']} |")
    add(f"| Seiten betroffen | {zustand['seiten']} "
        f"(davon live: {zustand['live_seiten']}) |")
    add(f"| Text seit dem Befund geändert | {zustand['ueberholt']} |")
    add(f"| Altbestand ohne Fassungs-Hash | {zustand['ohne_fassung']} |")
    add(f"| Nicht entscheidbar (Seite fehlt) | {zustand['seite_fehlt']} |")
    add(f"| Über der Frist ({zustand['frist_tage']} Tage) | "
        f"{zustand['ueber_frist']} |")
    add(f"| In Eskalation ({zustand['eskalation_tage']} Tage) | "
        f"{zustand['in_eskalation']} |")
    add("")
    if belege is not None:
        add("## Heilungsbelege (Beweislage der Schließakte)")
        add("")
        add(f"**{belege.get('geprueft', 0)} dokumentierte Heilung(en)** zitieren "
            f"einen Satz, der heute im Artikel steht · "
            f"{belege.get('ohne_stelle', 0)} Altentscheidung(en) ohne Belegstelle · "
            f"{belege.get('seite_fehlt', 0)} Seite(n) nicht im Bestand.")
        add("")
        if belege.get("funde"):
            add(f"> **{len(belege['funde'])} Belegstelle(n) stehen nicht mehr im "
                "Text.** Die Heilung ist damit nicht mehr belegt und muss neu "
                "entschieden werden (`--entscheiden … --art geaendert --stelle "
                "\"…\"`). Prüfen: `python3 scripts/faktenfrische_befund_ledger.py "
                "--pruefe-stellen`.")
            add("")
            for fund in belege["funde"][:20]:
                add(f"- `{fund['slug']}` · `{fund['befund_id']}` "
                    f"({fund.get('art', '')}, {fund.get('entschieden_am', '')}): "
                    f"„{str(fund.get('belegstelle', ''))[:120]}“")
            add("")
        else:
            add("Die Rückprobe (`--pruefe-stellen`) ist grün: Jede dokumentierte "
                "Belegstelle steht im heutigen Text.")
            add("")
    add("## So schließt du einen Befund")
    add("")
    add("1. **Text und Beleg prüfen.** Mangel korrigieren (Zahl belegen oder "
        "entfernen, Aussage präzisieren) oder den Befund fachlich begründet "
        "zurückweisen. Der Text ist redaktionell – die Maschine schreibt ihn nie.")
    add("2. **Entscheidung dokumentieren** (eine Zeile, bindet an den heutigen "
        "Text und an genau diesen Befund):")
    add("")
    add("   ```bash")
    add("   " + ENTSCHEIDEN.format(id="<BEFUND-ID>"))
    add("   ```")
    add("")
    add("3. **Akte und Messung nachziehen:**")
    add("")
    add("   ```bash")
    add("   python3 scripts/faktenfrische_befund_akte.py --schreiben")
    add("   python3 scripts/release_scorecard.py --live --streng")
    add("   ```")
    add("")
    add("Ein neues `faktencheck`-Datum schließt **keinen** Befund (F4 ≠ F1). "
        "Und: Ein Befund ist an den **Text** gebunden, nicht an die Quellen – "
        "eine automatische Quellenpflege öffnet keine erledigte Entscheidung, "
        "eine Textänderung dagegen schon.")
    add("")
    if zustand["ueberholt"] or zustand["ohne_fassung"]:
        add(f"> **Wichtig – betrifft {zustand['ueberholt'] + zustand['ohne_fassung']} "
            f"von {zustand['offen']} Befunden** (in der Tabelle als Fassung "
            "markiert): Der Text ist seit dem Befund bereits geändert worden "
            "(Heilung) oder stammt aus dem Altbestand. Die Entscheidung bezieht "
            "sich ausdrücklich auf den HEUTIGEN Text – bitte diesen lesen, "
            "nicht den alten Befund abnicken. Diese Prüfung kann dir die "
            "Maschine nicht abnehmen – "
        "sie darf sie aber auch nicht verhindern.")
        add("")
    if not befunde:
        add("## Keine offenen Befunde")
        add("")
        add("Alle fachlichen Befunde sind dokumentiert entschieden. "
            "F4 ist grün – sofern die Messung im selben Stand läuft.")
        add("")
        return "\n".join(z) + "\n"

    seiten: dict[str, list[dict]] = {}
    for b in befunde:
        seiten.setdefault(b["slug"], []).append(b)
    reihenfolge = sorted(
        seiten,
        key=lambda s: (
            0 if s in live else 1,
            0 if (live.get(s) or {}).get("urteil") in ("blockiert", "nicht beweisbar") else 1,
            min(STATUS_RANG.get(b["fassung_status"], 9) for b in seiten[s]),
            -max((b.get("alter_tage") or 0) for b in seiten[s]),
            s))
    add("## Seiten")
    add("")
    for slug in reihenfolge:
        eintraege = sorted(seiten[slug],
                           key=lambda b: (STATUS_RANG.get(b["fassung_status"], 9),
                                          -(b.get("alter_tage") or 0), b["id"]))
        info = live.get(slug) or {}
        kennung = (" · **LIVE**" if slug in live else " · nicht im Live-Bestand")
        if info.get("urteil") in ("blockiert", "nicht beweisbar"):
            kennung += f" ({info['urteil']})"
        if info.get("risikoklasse"):
            kennung += f" · Risikoklasse {info['risikoklasse']}"
        add(f"### `{slug}`{kennung} · {len(eintraege)} Befund(e)")
        add("")
        add(f"Datei: `content/posts/{slug}/index.md`" if slug in live
            else f"Seite: `{slug}`")
        add("")
        herkunft = sorted({b["ursprungs_slug"] for b in eintraege
                           if b.get("ursprungs_slug")})
        if herkunft:
            add("Herkunft nach Datums-Lift: " + ", ".join(
                f"`{alt}` → `{slug}`" for alt in herkunft) +
                ". Befund-ID und Fassungsanker bleiben unverändert; das Re-Dating "
                "ist keine fachliche Entscheidung.")
            add("")
        add("| Befund-ID | Typ | Alter | Fassung | Beanstandung | Beleg |")
        add("|---|---|---|---|---|---|")
        for b in eintraege:
            text = str(b.get("text") or "").replace("|", "\\|")
            beleg = b.get("beleg") or "–"
            if beleg != "–":
                beleg = f"[Quelle]({beleg})"
            add(f"| `{b['id']}` | {b.get('typ') or '–'} | "
                f"{_de_zahl(b.get('alter_tage'))} T | "
                f"{STATUS_TEXT.get(b['fassung_status'], b['fassung_status'])} | "
                f"{text} | {beleg} |")
        add("")
        add("```bash")
        for b in eintraege:
            add(ENTSCHEIDEN.format(id=b["id"]))
        add("```")
        add("")
    add("---")
    add("")
    add("_Diese Akte entscheidet nichts und schließt nichts. Sie macht sichtbar, "
        "was zu entscheiden ist, wer es entscheiden muss (Herausgeber/Redaktion) "
        "und wie der Schließweg lautet. Regel: "
        "`scripts/faktenfrische_befund_ledger.py`, Governance C46._")
    add("")
    return "\n".join(z)


def _schreiben(text: str, zustand: dict) -> None:
    AKTE_PATH.write_text(text, encoding="utf-8")
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(zustand, ensure_ascii=False, indent=2) + "\n",
                          encoding="utf-8")


def erstellen(stichtag: dt.date | None = None) -> dict:
    stichtag = stichtag or dt.date.today()
    cfg = _config()
    befunde = ledger.befunde_mit_status(stichtag=stichtag)
    live = live_seiten()
    zustand = zustand_bauen(befunde, live, frist_tage=cfg["frist_tage"],
                            eskalation_tage=cfg["eskalation_tage"],
                            stichtag=stichtag)
    zustand["akte"] = str(AKTE_PATH.relative_to(ROOT))
    zustand["regel"] = "scripts/faktenfrische_befund_ledger.py"
    try:
        belege = ledger.stellen_pruefen()
    except Exception:  # noqa: BLE001 – die Akte darf an der Rückprobe nicht sterben
        belege = None
    if belege is not None:
        zustand["belegstellen"] = belege.get("geprueft", 0)
        zustand["belegstellen_ohne"] = belege.get("ohne_stelle", 0)
        zustand["belegstellen_funde"] = len(belege.get("funde") or [])
    _schreiben(akte_bauen(befunde, live, zustand, belege), zustand)
    return zustand


def wache() -> dict:
    """Struktur und Schließweg – nicht die Arbeitsgeschwindigkeit der Menschen."""
    stand = ledger.wache()
    frisch = {}
    try:
        alt = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        frisch = {"akte_offen": alt.get("offen"),
                  "akte_stand": alt.get("stichtag"),
                  "veraltet": alt.get("offen") != stand["offen"]}
    except (OSError, ValueError):
        frisch = {"akte_offen": None, "akte_stand": None, "veraltet": True}
    stand.update(frisch)
    return stand


def selftest() -> int:
    stichtag = dt.date(2026, 11, 3)
    befunde = [
        {"slug": "live-seite", "id": "aaa1", "typ": "luecke",
         "text": "Preis ohne Beleg", "beleg": "https://www.bundesnetzagentur.de/x",
         "alter_tage": 4, "fassung_status": "ueberholt", "entscheidbar": True},
        {"slug": "live-seite", "id": "aaa2", "typ": "praezision",
         "text": "Superlativ ohne Daten", "beleg": "", "alter_tage": 30,
         "fassung_status": "aktuell", "entscheidbar": True},
        {"slug": "entwurf", "id": "bbb1", "typ": "luecke",
         "text": "Altbefund", "beleg": "", "alter_tage": 10,
         "fassung_status": "ohne-fassung", "entscheidbar": True},
    ]
    live = {"live-seite": {"urteil": "blockiert", "risikoklasse": "standard"}}
    zustand = zustand_bauen(befunde, live, frist_tage=14, eskalation_tage=21,
                            stichtag=stichtag)
    assert zustand["offen"] == 3 and zustand["seiten"] == 2, zustand
    assert zustand["live_seiten"] == 1 and zustand["live_befunde"] == 2, zustand
    assert zustand["ueber_frist"] == 1, zustand
    assert zustand["in_eskalation"] == 1, zustand
    assert zustand["aeltester_tage"] == 30, zustand
    text = akte_bauen(befunde, live, zustand)
    # Die Arbeitsdatei muss den Befehl, die Fassungs-Lage und die Frist nennen.
    assert "--entscheiden aaa1" in text, text
    assert "--von" in text and "--begruendung" in text
    assert "HEUTIGEN Text" in text
    assert "14 Tage" in text
    assert "**LIVE**" in text and "blockiert" in text
    assert "aaa1" in text and "bbb1" in text
    # Keine Scheinentscheidung, keine Behauptung „grün“.
    assert "geschlossen" not in text.lower() or "nichts" in text.lower()
    # Ein Befund ohne Seite ist nicht entscheidbar und wird so benannt.
    kaputt = dict(befunde[0], entscheidbar=False,
                  nicht_entscheidbar_grund="Seite nicht lesbar")
    zustand2 = zustand_bauen([kaputt], live, frist_tage=14, eskalation_tage=21,
                             stichtag=stichtag)
    assert zustand2["nicht_entscheidbar"] == 1, zustand2
    print("✅ Befundakte: Zählung, Live-Bezug, Frist/Eskalation, Arbeitsbefehl, "
          "Fassungs-Hinweis, keine Scheinentscheidung.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--schreiben", action="store_true",
                        help="BEFUND-AKTE.md und Zustand neu erzeugen")
    parser.add_argument("--wache", action="store_true",
                        help="Exit 1, wenn ein Befund keinen Schließweg hat")
    parser.add_argument("--json", action="store_true", help="Zustand auf stdout")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            return selftest()
        if args.wache:
            stand = wache()
            if args.json:
                print(json.dumps(stand, ensure_ascii=False, indent=2))
            else:
                print(f"Offene Fachbefunde: {stand['offen']} auf "
                      f"{stand['seiten']} Seiten · überholte Fassung: "
                      f"{stand['ueberholt']} · ohne Fassung: {stand['ohne_fassung']}")
                if stand.get("veraltet"):
                    print("⚠ BEFUND-AKTE.md ist nicht auf dem Stand der Queue – "
                          "`--schreiben` nachziehen.")
                if stand["gruen"]:
                    print("✅ Jeder offene Befund hat einen dokumentierten "
                          "Schließweg (menschliche Entscheidung am heutigen Text).")
                else:
                    print(f"❌ {stand['nicht_entscheidbar']} Befund(e) ohne "
                          "Schließweg:")
                    for fund in stand["funde"]:
                        print(f"   - {fund}")
            return 0 if stand["gruen"] else 1
        if args.schreiben or not args.json:
            zustand = erstellen()
            if args.json:
                print(json.dumps(zustand, ensure_ascii=False, indent=2))
            else:
                print(f"✅ {zustand['akte']} geschrieben: {zustand['offen']} "
                      f"offene Befunde auf {zustand['seiten']} Seiten "
                      f"({zustand['live_seiten']} live), ältester "
                      f"{_de_zahl(zustand['aeltester_tage'])} Tage, "
                      f"Frist {zustand['frist_tage']} Tage, "
                      f"{zustand['ueber_frist']} über der Frist.")
            return 0
        print(json.dumps(zustand_bauen(ledger.befunde_mit_status(),
                                       live_seiten(), **_config(),
                                       stichtag=dt.date.today()),
                         ensure_ascii=False, indent=2))
        return 0
    except ledger.LedgerFehler as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
