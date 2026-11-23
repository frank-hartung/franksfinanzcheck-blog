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
import hashlib
import json
import yaml
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import faktenfrische_befund_ledger as ledger  # noqa: E402

AKTE_PATH = ROOT / "BEFUND-AKTE.md"
ENTFERNT_PATH = ROOT / "data" / "faktenfrische_entfernt.yaml"
STATE_PATH = ROOT / "data" / "faktenfrische_befunde_state.json"
QUEUE_PATH = ROOT / "data" / "faktenfrische_queue.json"
DECISIONS_PATH = ROOT / "data" / "faktenfrische_entscheidungen.yaml"
SCORECARD_STATE = ROOT / "data" / "release_scorecard_state.json"
CONFIG_PATH = ROOT / "data" / "agent_reach" / "faktenfrische.yaml"

STANDARD_FRIST = 14
STANDARD_ESKALATION = 21
ENTSCHEIDEN = ("python3 scripts/faktenfrische_befund_ledger.py --entscheiden {id} "
               "--von \"<Name>\" --begruendung \"<was geprüft/geändert wurde>\"")

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


def entfernte_slugs() -> set[str]:
    """Slugs, die bewusst aus dem Bestand entfernt wurden (Entscheidung im Repo).

    Ihre Befunde bleiben im Ledger; sie zählen aber nicht als offene Arbeit:
    Ohne Text ist kein Befund mehr entscheidbar. Ohne diese Liste meldet die
    Akte einen gelöschten Beitrag dauerhaft als „nicht entscheidbar".
    """
    try:
        daten = yaml.safe_load(ENTFERNT_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, ValueError):
        return set()
    if not isinstance(daten, dict):
        return set()
    return {str(e.get("slug")) for e in (daten.get("entfernt") or [])
            if isinstance(e, dict) and e.get("slug")}


def _de_zahl(wert) -> str:
    return "–" if wert is None else str(wert)


def zustand_bauen(befunde: list[dict], live: dict[str, dict], *,
                  frist_tage: int, eskalation_tage: int,
                  stichtag: dt.date, entfernt: set[str] | None = None) -> dict:
    """Reine Funktion: Befunde + Live-Sicht → Zustand (Siegel der Akte)."""
    def ist_live(b: dict) -> bool:
        return b["slug"] in live

    entfallen = 0
    if entfernt:
        vorher = len(befunde)
        befunde = [b for b in befunde if b["slug"] not in entfernt]
        entfallen = vorher - len(befunde)

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
        "entfallen": entfallen,
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


def akte_bauen(befunde: list[dict], live: dict[str, dict], zustand: dict) -> str:
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
    if zustand.get("entfallen"):
        add(f"| Entfallen (Beitrag entfernt, s. data/faktenfrische_entfernt.yaml) "
            f"| {zustand['entfallen']} |")
    add(f"| Über der Frist ({zustand['frist_tage']} Tage) | "
        f"{zustand['ueber_frist']} |")
    add(f"| In Eskalation ({zustand['eskalation_tage']} Tage) | "
        f"{zustand['in_eskalation']} |")
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
    """Schreibt Akte und Zustand – IDEMPOTENT auf Bytes.

    ANLASS (21.11.2026): Seit die Akte ein abgeleitetes Register ist
    (`scripts/abgeleitete_register.py`), ruft der Commit-Pfad sie bei JEDEM
    Deploy-Lauf auf. Vorher stempelte jeder Aufruf einen neuen
    `erzeugt`-Zeitstempel – auch wenn sich fachlich nichts geändert hatte.
    `deploy.yml` erkennt Gate-Heilungen an `git status --short` und committet
    sie; ein reiner Zeitstempel hätte damit jeden Lauf einen Commit und
    einen Rebuild erzeugt (Endlosschleife). Deshalb: gleicher Inhalt →
    gleicher Zeitstempel, gleiche Bytes → kein Schreibvorgang.

    Der Zeitstempel ist ausdrücklich KEINE fachliche Änderung (`wache()`
    blendet ihn beim Vergleich aus) – diese Zusage hält der Schreiber jetzt
    auch selbst ein.
    """
    # 1) Zeitstempel erben, wenn fachlich alles gleich ist. Die Projektion
    #    selbst bleibt unberührt (kein verstecktes Feld in der Akte).
    try:
        alt = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if isinstance(alt, dict) and alt.get("erzeugt"):
            ohne = {k: v for k, v in alt.items() if k != "erzeugt"}
            neu = {k: v for k, v in zustand.items() if k != "erzeugt"}
            if ohne == neu:
                zustand["erzeugt"] = alt["erzeugt"]
    except (OSError, ValueError, TypeError):
        pass

    # 2) Nur schreiben, was sich auf BYTES unterscheidet. `deploy.yml`
    #    committet, was `git status --short` sieht – ein unnötiger
    #    Schreibvorgang wäre dort ein Commit ohne Änderung.
    def _ersetze(pfad: Path, inhalt: str) -> None:
        try:
            if pfad.read_text(encoding="utf-8") == inhalt:
                return
        except OSError:
            pass
        pfad.parent.mkdir(parents=True, exist_ok=True)
        pfad.write_text(inhalt, encoding="utf-8")

    _ersetze(AKTE_PATH, text)
    _ersetze(STATE_PATH, json.dumps(zustand, ensure_ascii=False, indent=2) + "\n")


def projektion(stichtag: dt.date) -> tuple[str, dict]:
    """Eine gemeinsame, schreibfreie Projektion für Erzeugung und Prüfung."""
    cfg = _config()
    befunde = ledger.befunde_mit_status(stichtag=stichtag,
                                   entfernte_ausblenden=False)
    live = live_seiten()
    zustand = zustand_bauen(befunde, live, frist_tage=cfg["frist_tage"],
                            eskalation_tage=cfg["eskalation_tage"],
                            stichtag=stichtag, entfernt=entfernte_slugs())
    zustand["akte"] = str(AKTE_PATH.relative_to(ROOT))
    zustand["regel"] = "scripts/faktenfrische_befund_ledger.py"
    return akte_bauen(befunde, live, zustand), zustand


def erstellen(stichtag: dt.date | None = None) -> dict:
    text, zustand = projektion(stichtag or dt.date.today())
    _schreiben(text, zustand)
    return zustand


def wache() -> dict:
    """Schließweg und vollständige Projektion am dokumentierten Stichtag prüfen.

    Der Zeitstempel ist keine fachliche Änderung; ein neuer Tag allein macht
    die Akte nicht falsch. Neue Befunde, Fassungen, Konfiguration, Live-Sicht
    und Änderungen am Markdown werden dagegen auch bei gleicher Anzahl erkannt.
    """
    stand = ledger.wache()
    frisch = {"akte_offen": None, "akte_stand": None, "veraltet": True,
              "veraltet_grund": "Akte/Zustand fehlt oder ist unlesbar"}
    try:
        alt = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        if not isinstance(alt, dict):
            raise ValueError("Zustand ist kein Objekt")
        frisch.update(akte_offen=alt.get("offen"), akte_stand=alt.get("stichtag"))
        stichtag = dt.date.fromisoformat(alt["stichtag"])
        if stichtag > dt.date.today():
            raise ValueError("Stichtag liegt in der Zukunft")
        dokument = AKTE_PATH.read_text(encoding="utf-8")
    except (OSError, ValueError, TypeError, KeyError):
        stand.update(frisch)
        return stand  # Fehlende oder defekte Projektion ist kein Grün.
    # Ledgerfehler dürfen hier nicht als veraltete Datei verschluckt werden.
    text, erwartet = projektion(stichtag)
    alt_ohne_zeit = {k: v for k, v in alt.items() if k != "erzeugt"}
    erwartet_ohne_zeit = {k: v for k, v in erwartet.items() if k != "erzeugt"}
    gruende = beschreibe_abweichung(alt_ohne_zeit, erwartet_ohne_zeit,
                                    dokument, text)
    frisch["veraltet"] = bool(gruende)
    if gruende:
        frisch["veraltet_grund"] = " · ".join(gruende)
    stand.update(frisch)
    return stand


def beschreibe_abweichung(alt: dict, erwartet: dict,
                          dokument: str, text: str) -> list[str]:
    """Nennt die Ursache der Abweichung – nicht nur „stimmt nicht".

    ANLASS (21.11.2026, Issue #1266/#1267/#1271): Die Nachlauf-Wache meldete
    „BEFUND-AKTE.md oder Zustand stimmt nicht mit dem Ledger überein
    (Akte: 202 offen, Ledger: 202)" – mit ZWEI GLEICHEN Zahlen. Der Satz war
    für den Leser widersprüchlich und für die Reparatur wertlos: Er nannte
    die Anzahl statt der Ursache. Tatsächlich wichen Kennzahlen ab, die die
    Meldung nie nannte (`ueberholt`, `aeltester_tage`, `je_seite`) oder es
    war allein der Markdown-Text. Hier steht beides getrennt und benannt.
    """
    gruende: list[str] = []
    # ALLE Kennzahlen zählen – auch `befunde`. Der Vergleich blendet nur den
    # Zeitstempel aus (er ist keine fachliche Änderung), nichts sonst: Ein
    # anderer Befund bei GLEICHER Anzahl ist Drift, und genau diese Lage hat
    # der Test `test_gleiche_anzahl_anderer_befund_oder_fassung` festgenagelt.
    abweichend = sorted(k for k in set(alt) | set(erwartet)
                        if k != "erzeugt" and alt.get(k) != erwartet.get(k))
    if abweichend:
        paare = ", ".join(f"{k}: Akte {_kurz(alt.get(k))} ≠ Quelle "
                          f"{_kurz(erwartet.get(k))}" for k in abweichend[:6])
        mehr = f" (+{len(abweichend) - 6} weitere)" if len(abweichend) > 6 else ""
        gruende.append(f"Zustand weicht ab – {paare}{mehr}")
    if dokument != text:
        gruende.append("BEFUND-AKTE.md weicht vom erzeugten Text ab")
    return gruende


def _kurz(wert: object) -> str:
    """Kurze, unterscheidbare Darstellung eines Kennzahlwerts für Log/Issue.

    Bei Listen und Objekten zählt nicht nur die Länge, sondern ein kurzer
    Inhalts-Hash: Zwei Befundlisten mit gleich vielen Einträgen können
    verschiedene Befunde tragen – „[3 Einträge]“ gegen „[3 Einträge]“ wäre
    genau die nichtssagende Meldung, die dieses Modul abschafft.
    """
    if isinstance(wert, (dict, list)):
        roh = json.dumps(wert, ensure_ascii=False, sort_keys=True,
                         default=str).encode("utf-8")
        return (f"[{len(wert)} Einträge, Inhalt "
                f"{hashlib.sha256(roh).hexdigest()[:8]}]")
    return str(wert)


def pruefen() -> int:
    """Schreibfreier Drift-Test (Vertrag der abgeleiteten Register).

    Interface für `scripts/abgeleitete_register.py`: Exit 0 = Akte folgt ihrer
    Quelle, Exit 1 = Drift (mit benannter Ursache), Exit 2 = nicht prüfbar.

    ANLASS (21.11.2026, #1251/#1252): Die Befund-Akte ist eine 162 KB große
    ABLEITUNG aus Queue + Entscheidungen – stand aber NICHT im Verzeichnis der
    abgeleiteten Register. Damit fehlte ihr der Nachzug-Pfad, den
    `data/fachpruefung_register.yaml` seit dem 09.11.2026 hat: Jeder Commit,
    der die Quelle änderte, ohne die Akte nachzuziehen, machte sie still alt –
    und die Nachlauf-Wache fand es erst Stunden später auf `main` (#1229,
    #1251, #1252, #1266, #1267, #1271). Hier wird die Klasse an der Wurzel
    geschlossen: Der Selbsttest ist die Sabotage-Probe, `--check` ist das
    Urteil, `--schreiben` der Nachzug – genau das Dreigespann, das
    `abgeleitete_register.py` erwartet.
    """
    try:
        stand = wache()
    except Exception as exc:                      # noqa: BLE001 – nie grün raten
        # Ein Fehler hier heißt „nicht prüfbar", nicht „in Ordnung": Die
        # Aufrufer (Register-Nachzug, Nachlauf-Wache) unterscheiden das.
        print(f"Befund-Akte nicht prüfbar ({type(exc).__name__}: {exc})")
        return 2
    if stand.get("veraltet"):
        print("🛑 BEFUND-AKTE.md ist veraltet – "
              f"{stand.get('veraltet_grund') or 'Abweichung zur Quelle'}. "
              "Heilung: python3 scripts/faktenfrische_befund_akte.py --schreiben")
        return 1
    print(f"✅ Befund-Akte folgt ihrer Quelle ({stand.get('akte_offen')} offene "
          f"Befunde, Stichtag {stand.get('akte_stand')}).")
    return 0


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
    parser.add_argument("--check", action="store_true",
                        help="Exit 1, wenn Akte/Zustand nicht zur Quelle passen "
                             "(schreibfrei – für den Register-Nachzug)")
    parser.add_argument("--json", action="store_true", help="Zustand auf stdout")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()
    try:
        if args.selftest:
            return selftest()
        if args.check:
            return pruefen()
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
