#!/usr/bin/env python3
"""
engine_capacity.py – EIN Besitzer für die Frage „Was darf die Engine heute
überhaupt veröffentlichen?“
==========================================================================

WARUM ES DIESE DATEI GIBT (02.10.2026, Issue #521 – 0/2 LIVE)
-------------------------------------------------------------
Am 02.10.2026 (Freitag, Publikationstag) hat die Content-Engine vier Artikel
produziert und **keinen einzigen** veröffentlicht. Der Lauf war nicht
„zufällig schwach“ – er war **planbar erfolglos**:

  * ``data/topics.yaml`` enthält 187 Themen. **46 davon (24,6 %) sind
    YMYL-Hochrisiko** (Versicherung, Kredit, Baufinanzierung, Altersvorsorge).
  * Für genau diese Klasse ist ``editorial_review_gate.py`` **fail-closed**:
    Ohne namentlichen Fachprüfer, Prüfprotokoll mit Textankern, belegten
    Zahlen, zwei Quellen von der Allowlist und passendem Freigabe-Hash geht
    nichts live. Das ist korrekt und bleibt so (Governance C15).
  * Die Themen-Disposition (``reserve_topics.disponieren``) wusste davon
    **nichts**. Sie hat am 02.10. zwei Hochrisiko-Themen in die Tagesquote
    gegeben („Vergleich von Hausratversicherungen“,
    „Reisekrankenversicherung“), die KI hat sie ausgeschrieben, das Gate hat
    sie – wie vorgesehen – gehalten.

Die Maschine hat also ihr Tagesbudget für Arbeit ausgegeben, die sie selbst
nicht ausliefern darf. Das ist kein Gate-Fehler und kein KI-Fehler, sondern
ein **Kapazitätsplanungs-Fehler**: Es gab nie eine Stelle, die „produzierbar“
von „veröffentlichbar“ unterschieden hat.

Der Schaden ist messbar und älter als dieser eine Tag: Im Bestand liegen
**11 Hochrisiko-Entwürfe ohne Freigabe**, der älteste vom 12.08.2026. Jeder
davon hat einmal einen Produktionsslot gekostet.

ZWEI BAHNEN, EINE QUELLE
------------------------
    AUTO            Themen, die die Automatik bis LIVE bringen darf.
                    Nur sie füllen die Tagesquote (MIN_ARTIKEL_PRO_TAG).
    FACHFREIGABE    YMYL-Hochrisiko. Wertvoll, aber per Vertrag
                    menschlich gegenzuzeichnen. Diese Bahn hat ein
                    WIP-Limit: Sie produziert nichts Neues, solange der
                    Prüfstapel nicht abgearbeitet ist. Ein Vorrat
                    unsignierter Entwürfe ist kein Vorrat, sondern Halde.

Die Einstufung wird **nicht** nachgebaut: ``bahn_fuer_thema()`` ruft
``editorial_review_gate.classify_text()`` mit demselben Material auf, das
``inferred_risk()`` später am fertigen Artikel benutzt (Titel + die ersten
zwei Keywords + Pillar). Eine Quelle, zwei Zeitpunkte.

Die Vorhersage ist bewusst **asymmetrisch konservativ**: Ein als „hoch“
erkanntes Thema kommt nie in die Quote. Ein als „auto“ eingestuftes Thema
kann am fertigen Text trotzdem hochgestuft werden – dann greift weiterhin
das fail-closed Gate. Die Bahn ersetzt kein Gate, sie verhindert nur, dass
die Maschine sehenden Auges gegen eines läuft.

DIE ZWEITE LÜGE: „157 frei“ vs. „3 frei“
----------------------------------------
``bot_preflight.check_topics()`` hat die freien Themen mit der laxen
60-%-Token-Regel aus ``generate_drafts.topic_already_covered`` gezählt und
am 02.10. **157 freie Themen** gemeldet. Die Disposition, die das Thema
tatsächlich auswählt (Leitbegriff-Kollision + Cooldown-Gedächtnis), fand zur
selben Zeit **3**. Ein Pre-Flight, der mit einem anderen Maß misst als der
Disponent, ist kein Pre-Flight – er ist eine grüne Lampe am falschen Kabel.

``lage()`` misst deshalb ausschließlich mit dem Maß des Disponenten und
trennt zusätzlich nach Bahn. Erst diese Zahl beantwortet die einzige Frage,
die am Morgen eines Publikationstages zählt: **Reicht das für heute?**

NUTZUNG
    python3 scripts/engine_capacity.py              # Lage im Klartext
    python3 scripts/engine_capacity.py --json
    python3 scripts/engine_capacity.py --strict     # Exit 1 bei Engpass
    python3 scripts/engine_capacity.py --selftest   # Sabotage-Schutz

EXIT: 0 = ok · 1 = Engpass (nur mit --strict) · 2 = Selbsttest rot
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "content" / "posts"
sys.path.insert(0, str(ROOT / "scripts"))

import editorial_review_gate as erg  # noqa: E402  – Einstufungs-SSOT

BAHN_AUTO = "auto"
BAHN_FACHFREIGABE = "fachfreigabe"
BAHNEN = (BAHN_AUTO, BAHN_FACHFREIGABE)

# WIP-Limit der Fachfreigabe-Bahn. Kanban, nicht Kosmetik: Solange mehr als
# so viele Hochrisiko-Entwürfe auf eine Unterschrift warten, produziert die
# Maschine keinen weiteren dazu. Am 02.10.2026 lag der Stapel bei 11.
WIP_LIMIT_DEFAULT = 3
WIP_LIMIT_MIN = 0
WIP_LIMIT_MAX = 25
ENV_WIP_LIMIT = "YMYL_WIP_LIMIT"

# Wie viele frei disponierbare AUTO-Themen ein Publikationstag mindestens
# braucht, um nicht auf Kante zu laufen. Ein Tag will MIN_ARTIKEL_PRO_TAG
# Artikel; jeder Versuch kann an Provider oder Profi-Gate scheitern, deshalb
# rechnen wir mit einem Faktor statt mit der nackten Zahl.
RESERVE_FAKTOR = 3
ENV_MIN_PRO_TAG = "MIN_ARTIKEL_PRO_TAG"
MIN_PRO_TAG_DEFAULT = 2

VERDIKT_OK = "ok"
VERDIKT_KNAPP = "knapp"
VERDIKT_ERSCHOEPFT = "erschoepft"


# ---------------------------------------------------------------------------
#  Konfiguration (geklemmt, nie still verschluckt – wie reserve_economy.py)
# ---------------------------------------------------------------------------
def _zahl_aus_env(name: str, default: int, minimum: int, maximum: int,
                  warnungen: list[str], env: dict | None = None) -> int:
    quelle = os.environ if env is None else env
    roh = quelle.get(name)
    if roh is None or str(roh).strip() == "":
        return default
    try:
        wert = int(str(roh).strip())
    except (TypeError, ValueError):
        warnungen.append(f"{name}={roh!r} ist keine ganze Zahl – es gilt "
                         f"der Default {default}.")
        return default
    if wert < minimum:
        warnungen.append(f"{name}={wert} liegt unter dem Minimum {minimum} – "
                         f"auf {minimum} angehoben.")
        return minimum
    if wert > maximum:
        warnungen.append(f"{name}={wert} liegt über dem Maximum {maximum} – "
                         f"auf {maximum} gedeckelt.")
        return maximum
    return wert


def wip_limit(warnungen: list[str] | None = None,
              env: dict | None = None) -> int:
    return _zahl_aus_env(ENV_WIP_LIMIT, WIP_LIMIT_DEFAULT, WIP_LIMIT_MIN,
                         WIP_LIMIT_MAX, warnungen if warnungen is not None else [],
                         env)


def min_pro_tag(warnungen: list[str] | None = None,
                env: dict | None = None) -> int:
    wert = _zahl_aus_env(ENV_MIN_PRO_TAG, MIN_PRO_TAG_DEFAULT, 1, 10,
                         warnungen if warnungen is not None else [], env)
    # Dauervorgabe Mo/Mi/Fr: 2–3 LIVE. Unter 2 gibt es kein Tagesziel.
    return max(2, wert)


# ---------------------------------------------------------------------------
#  Einstufung: welche Bahn gehört zu diesem Thema / diesem Artikel?
# ---------------------------------------------------------------------------
def _material(titel: str, keywords, pillar: str) -> tuple[str, str]:
    """Dasselbe Material, das `editorial_review_gate.inferred_risk` benutzt.

    Titel + die ersten ZWEI Keywords sind die redaktionelle Themenzusage.
    Beschreibung und Tags bleiben bewusst draußen: Ein Girokonto-Artikel darf
    nicht wegen eines Nebensatzes über den Dispo in die Fachfreigabe rutschen.
    """
    if keywords is None:
        keywords = []
    if not isinstance(keywords, (list, tuple)):
        keywords = [keywords]
    text = " ".join([str(titel or ""), erg._text(list(keywords)[:2])]).strip()
    return text, str(pillar or "")


def risikoklasse_fuer_thema(topic: dict) -> str:
    """Risikoklasse eines Themenpool-Eintrags – über die Gate-SSOT."""
    topic = topic or {}
    text, pillar = _material(topic.get("title"), topic.get("keywords"),
                             topic.get("pillar"))
    return erg.classify_text(text, pillar)


def bahn_fuer_thema(topic: dict) -> str:
    """AUTO oder FACHFREIGABE – die einzige erlaubte Antwort auf die Frage,
    ob ein Thema die Tagesquote füllen darf."""
    return (BAHN_FACHFREIGABE
            if risikoklasse_fuer_thema(topic) == erg.RISK_HIGH
            else BAHN_AUTO)


def bahn_fuer_artikel(fm: dict) -> str:
    """Dieselbe Frage am fertigen Artikel (Frontmatter)."""
    return (BAHN_FACHFREIGABE
            if erg.inferred_risk(fm or {}) == erg.RISK_HIGH
            else BAHN_AUTO)


def nach_bahn(topics: list) -> dict[str, list]:
    """Themenpool in die beiden Bahnen aufteilen (Originalobjekte)."""
    out: dict[str, list] = {BAHN_AUTO: [], BAHN_FACHFREIGABE: []}
    for topic in topics or []:
        if not (topic or {}).get("title"):
            continue
        out[bahn_fuer_thema(topic)].append(topic)
    return out


def nur_auto(topics: list) -> list:
    """Filter für die Tagesquote. Reihenfolge bleibt erhalten."""
    return [t for t in (topics or [])
            if (t or {}).get("title") and bahn_fuer_thema(t) == BAHN_AUTO]


# ---------------------------------------------------------------------------
#  WIP der Fachfreigabe-Bahn: wie viele Entwürfe warten auf eine Unterschrift?
# ---------------------------------------------------------------------------
def offene_fachfreigaben(posts_dir: Path = POSTS) -> list[dict]:
    """Hochrisiko-Artikel ohne gültige Freigabe – Entwürfe zuerst.

    Das ist der Stapel, den ein Mensch abarbeiten muss. Er ist die
    Gegenkraft zur Produktion: Wächst er, schließt die Bahn.
    """
    posts_dir = Path(posts_dir)
    out: list[dict] = []
    if not posts_dir.is_dir():
        return out
    for index in sorted(posts_dir.glob("*/index.md")):
        try:
            fm, body, _ = erg.load_article(index)
        except Exception:  # noqa: BLE001 – kaputte Datei ist nicht unser Thema
            continue
        if erg.inferred_risk(fm) != erg.RISK_HIGH:
            continue
        try:
            urteil = erg.validate_article(fm, body)
        except Exception:  # noqa: BLE001
            continue
        if urteil.get("approved"):
            continue
        out.append({
            "slug": index.parent.name,
            "draft": bool(fm.get("draft")),
            "reserve": bool(fm.get("reserve")),
            "codes": sorted({f["code"] for f in urteil.get("findings", [])}),
        })
    out.sort(key=lambda e: (not e["draft"], e["slug"]))
    return out


def fachfreigabe_bahn(posts_dir: Path = POSTS, *, limit: int | None = None,
                      warnungen: list[str] | None = None) -> dict:
    """Darf die Fachfreigabe-Bahn heute etwas Neues produzieren?"""
    limit = wip_limit(warnungen) if limit is None else limit
    offen = offene_fachfreigaben(posts_dir)
    frei = max(0, limit - len(offen))
    return {
        "limit": limit,
        "offen": len(offen),
        "offene_entwuerfe": sum(1 for e in offen if e["draft"]),
        "freie_plaetze": frei,
        "geoeffnet": frei > 0,
        "grund": ("WIP frei" if frei > 0 else
                  f"{len(offen)} Hochrisiko-Artikel warten auf eine "
                  f"Fachfreigabe (Limit {limit}) – die Bahn bleibt zu, bis "
                  f"der Stapel abgearbeitet ist"),
        "stapel": offen,
    }


# ---------------------------------------------------------------------------
#  Die eigentliche Kapazität: was ist HEUTE frei – mit dem Maß des Disponenten
# ---------------------------------------------------------------------------
def lage(topics: list | None = None, *, posts_dir: Path = POSTS,
         ledger: Path | None = None, jetzt=None,
         env: dict | None = None) -> dict:
    """Die ehrliche Tageslage. Keine zweite Zählregel, keine Schätzung."""
    warnungen: list[str] = []
    if topics is None:
        import generate_drafts as g  # noqa: PLC0415 – optional/teuer
        topics = g.load_topics()

    import reserve_topics as rt  # noqa: PLC0415 – Maß des Disponenten

    bahnen = nach_bahn(topics)
    bestand = rt.bestands_titel(Path(posts_dir))

    # WICHTIG: dasselbe `disponieren`, das die Engine aufruft – inklusive
    # Kollisions- und Cooldown-Logik. Eine abweichende Zählung wäre genau
    # der Fehler, den diese Datei beendet.
    frei_auto = rt.disponieren(bahnen[BAHN_AUTO], posts_dir=Path(posts_dir),
                               pfad=ledger, limit=10_000, jetzt=jetzt,
                               bestand=bestand, bahn=BAHN_AUTO)
    frei_fach = rt.disponieren(bahnen[BAHN_FACHFREIGABE],
                               posts_dir=Path(posts_dir), pfad=ledger,
                               limit=10_000, jetzt=jetzt, bestand=bestand,
                               bahn=BAHN_FACHFREIGABE)

    minimum = min_pro_tag(warnungen, env)
    bedarf = minimum * RESERVE_FAKTOR
    n_auto = len(frei_auto)
    if n_auto == 0:
        verdikt = VERDIKT_ERSCHOEPFT
    elif n_auto < bedarf:
        verdikt = VERDIKT_KNAPP
    else:
        verdikt = VERDIKT_OK

    fach = fachfreigabe_bahn(posts_dir, warnungen=warnungen)

    if verdikt == VERDIKT_ERSCHOEPFT:
        befund = (f"Kein frei disponierbares AUTO-Thema. Die Engine kann das "
                  f"Tagesziel von {minimum} LIVE-Artikeln heute nicht aus "
                  f"eigener Kraft erreichen – Themennachschub ist die "
                  f"Ursache, nicht die KI.")
    elif verdikt == VERDIKT_KNAPP:
        befund = (f"Nur {n_auto} frei disponierbare AUTO-Themen für ein "
                  f"Tagesziel von {minimum} (Puffer-Bedarf {bedarf}). Ein "
                  f"Provider-Ausfall oder zwei Gate-Stopps kippen den Tag.")
    else:
        befund = (f"{n_auto} frei disponierbare AUTO-Themen – Tagesziel "
                  f"{minimum} ist gedeckt (Puffer-Bedarf {bedarf}).")

    return {
        "themen_gesamt": len(topics),
        "themen_auto": len(bahnen[BAHN_AUTO]),
        "themen_fachfreigabe": len(bahnen[BAHN_FACHFREIGABE]),
        "frei_auto": n_auto,
        "frei_fachfreigabe": len(frei_fach),
        "naechste_auto": [t.get("title") for t in frei_auto[:5]],
        "min_artikel_pro_tag": minimum,
        "puffer_bedarf": bedarf,
        "verdikt": verdikt,
        "befund": befund,
        "fachfreigabe": {k: v for k, v in fach.items() if k != "stapel"},
        "fachfreigabe_stapel": fach["stapel"],
        "warnungen": warnungen,
    }


def bericht_markdown(daten: dict) -> str:
    symbol = {VERDIKT_OK: "✅", VERDIKT_KNAPP: "⚠️",
              VERDIKT_ERSCHOEPFT: "🛑"}[daten["verdikt"]]
    fach = daten["fachfreigabe"]
    zeilen = [
        "# Kapazität der Content-Engine",
        "",
        f"**Verdikt:** {symbol} {daten['verdikt'].upper()}  ",
        f"**Befund:** {daten['befund']}",
        "",
        "| Kennzahl | Wert |",
        "|---|---|",
        f"| Themen gesamt | {daten['themen_gesamt']} |",
        f"| davon AUTO-Bahn (quotenfähig) | {daten['themen_auto']} |",
        f"| davon FACHFREIGABE-Bahn (YMYL) | {daten['themen_fachfreigabe']} |",
        f"| **Frei disponierbar AUTO** | **{daten['frei_auto']}** |",
        f"| Frei disponierbar FACHFREIGABE | {daten['frei_fachfreigabe']} |",
        f"| Tagesziel LIVE | {daten['min_artikel_pro_tag']} |",
        f"| Puffer-Bedarf AUTO | {daten['puffer_bedarf']} |",
        f"| Fachfreigabe: offen / Limit | {fach['offen']} / {fach['limit']} |",
        f"| Fachfreigabe-Bahn | {'offen' if fach['geoeffnet'] else 'geschlossen'} |",
        "",
    ]
    if daten["naechste_auto"]:
        zeilen.append("**Nächste AUTO-Themen:** "
                      + ", ".join(f"„{t}“" for t in daten["naechste_auto"]))
        zeilen.append("")
    if not fach["geoeffnet"]:
        zeilen.append(f"_{fach['grund']}._")
        zeilen.append("")
    for warnung in daten["warnungen"]:
        zeilen.append(f"- ⚠️ {warnung}")
    return "\n".join(zeilen).rstrip() + "\n"


# ---------------------------------------------------------------------------
#  Sabotage-Schutz
# ---------------------------------------------------------------------------
def run_selftest() -> int:
    import tempfile
    fehler: list[str] = []

    def erwarte(bedingung, meldung):
        if not bedingung:
            fehler.append(meldung)

    # ST1 – DIE ECHTEN THEMEN VOM 02.10.2026. Genau diese zwei haben einen
    #       Produktionsslot gekostet und konnten nie live gehen.
    for titel in ("Vergleich von Hausratversicherungen und wie du sparst",
                  "Reisekrankenversicherung: Wann sie sich wirklich lohnt",
                  "Günstigen Ratenkredit mit Bestzins sichern",
                  "Hauskauf finanzieren: Darlehen clever vergleichen",
                  "Riester-Rente: Lohnt sie sich 2026 noch?"):
        erwarte(bahn_fuer_thema({"title": titel}) == BAHN_FACHFREIGABE,
                f"ST1: „{titel}“ muss in die Fachfreigabe-Bahn "
                f"(Issue #521: genau diese Klasse hat die Quote verbrannt)")

    # ST2 – und die Gegenprobe: normale Spar-Themen bleiben in der Quote.
    for titel in ("Black Friday DSL-Deals: Diese Angebote lohnen sich wirklich",
                  "Stromfresser im Haushalt entlarven",
                  "Haushaltsbuch führen: App, Excel oder Papier?",
                  "Weihnachtsgeld klug einsetzen: Tilgen, sparen oder genießen?"):
        erwarte(bahn_fuer_thema({"title": titel}) == BAHN_AUTO,
                f"ST2: „{titel}“ darf nicht aus der Tagesquote fallen")

    # ST3 – Der Pillar allein stuft hoch. Ein Versicherungs-Artikel ohne das
    #       Wort „Versicherung“ im Titel darf nicht durchrutschen.
    erwarte(bahn_fuer_thema({"title": "Schutz fürs Fahrrad im Winter",
                             "pillar": "versicherungen"}) == BAHN_FACHFREIGABE,
            "ST3: Pillar „versicherungen“ muss die Fachfreigabe erzwingen")

    # ST4 – Keine zweite Musterliste: Die Bahn MUSS der Gate-Einstufung
    #       folgen. Wird erg.classify_text sabotiert, muss die Bahn mitgehen.
    original = erg.classify_text
    try:
        erg.classify_text = lambda text, pillar="": erg.RISK_HIGH
        erwarte(bahn_fuer_thema({"title": "Kochbuch für Sparfüchse"})
                == BAHN_FACHFREIGABE,
                "ST4: Bahn folgt nicht der Gate-SSOT – hier wurde die "
                "Einstufung nachgebaut statt wiederverwendet")
    finally:
        erg.classify_text = original

    # ST5 – nur_auto() filtert, ohne die Reihenfolge zu würfeln.
    pool = [{"title": "Stromfresser im Haushalt entlarven"},
            {"title": "Kfz-Versicherung vergleichen und sparen"},
            {"title": "Haushaltsbuch führen: App, Excel oder Papier?"}]
    gefiltert = [t["title"] for t in nur_auto(pool)]
    erwarte(gefiltert == ["Stromfresser im Haushalt entlarven",
                          "Haushaltsbuch führen: App, Excel oder Papier?"],
            f"ST5: nur_auto() filtert oder sortiert falsch: {gefiltert}")

    # ST6 – WIP-Limit: ein voller Prüfstapel schließt die Bahn.
    bahn = fachfreigabe_bahn.__wrapped__ if hasattr(fachfreigabe_bahn, "__wrapped__") else fachfreigabe_bahn
    with tempfile.TemporaryDirectory() as tmp:
        leer = Path(tmp)
        zustand = bahn(leer, limit=3)
        erwarte(zustand["geoeffnet"] and zustand["offen"] == 0,
                "ST6a: leerer Stapel muss die Fachfreigabe-Bahn öffnen")
        zustand = bahn(leer, limit=0)
        erwarte(not zustand["geoeffnet"],
                "ST6b: Limit 0 muss die Fachfreigabe-Bahn schließen")

    # ST7 – Konfiguration wird geklemmt, nicht still übernommen.
    warnungen: list[str] = []
    erwarte(wip_limit(warnungen, {"YMYL_WIP_LIMIT": "999"}) == WIP_LIMIT_MAX
            and warnungen,
            "ST7a: absurdes WIP-Limit muss gedeckelt UND gemeldet werden")
    warnungen = []
    erwarte(wip_limit(warnungen, {"YMYL_WIP_LIMIT": "drei"})
            == WIP_LIMIT_DEFAULT and warnungen,
            "ST7b: unlesbares WIP-Limit muss auf Default fallen UND melden")
    erwarte(min_pro_tag([], {"MIN_ARTIKEL_PRO_TAG": "1"}) == 2,
            "ST7c: Tagesziel darf nie unter 2 fallen (Dauervorgabe Mo/Mi/Fr)")

    if fehler:
        print("❌ engine_capacity Selbsttest ROT:")
        for f in fehler:
            print(f"   · {f}")
        return 2
    print("✅ engine_capacity Selbsttest grün (7 Prüfungen, "
          "echte Themen vom 02.10.2026 eingefroren).")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--md", action="store_true")
    parser.add_argument("--strict", action="store_true",
                        help="Exit 1, wenn die AUTO-Bahn erschöpft ist")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return run_selftest()

    daten = lage()
    if args.json:
        print(json.dumps(daten, ensure_ascii=False, indent=2))
    elif args.md:
        print(bericht_markdown(daten), end="")
    else:
        symbol = {VERDIKT_OK: "✅", VERDIKT_KNAPP: "⚠️",
                  VERDIKT_ERSCHOEPFT: "🛑"}[daten["verdikt"]]
        print(f"{symbol} Engine-Kapazität: {daten['befund']}")
        print(f"   Themen {daten['themen_gesamt']} = "
              f"AUTO {daten['themen_auto']} + "
              f"FACHFREIGABE {daten['themen_fachfreigabe']}")
        print(f"   frei disponierbar: AUTO {daten['frei_auto']} · "
              f"FACHFREIGABE {daten['frei_fachfreigabe']}")
        fach = daten["fachfreigabe"]
        print(f"   Fachfreigabe-Bahn: "
              f"{'offen' if fach['geoeffnet'] else 'GESCHLOSSEN'} "
              f"({fach['offen']}/{fach['limit']} im Prüfstapel)")
        if daten["naechste_auto"]:
            print("   nächste AUTO-Themen: "
                  + " · ".join(daten["naechste_auto"][:3]))
        for warnung in daten["warnungen"]:
            print(f"   ⚠️ {warnung}")

    if args.strict and daten["verdikt"] == VERDIKT_ERSCHOEPFT:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
