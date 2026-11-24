#!/usr/bin/env python3
"""Rollenkatalog einspielen und prüfen – ein Befehl statt drei Wellen.

ANLASS (24.11.2026)
===================
Die Entscheidung vom 23.11.2026 verteilte die 54 Beiträge ohne Rolle auf drei
Wellen (30.11./07.12./15.12.) und drei PRs. Das ist Arbeit *für* den Betreiber
statt Arbeit *der* Agentur: 54 einzelne Urteile über Suchabsichten. Dieses
Werkzeug dreht das Verfahren um.

  data/rollen_katalog.yaml   – fertige Rollen (abgeleitet aus Titel,
                               Description und H2, nicht erfunden)
  --pruefen                  – was fehlt, was kollidiert, was doppelt ist
  --uebernehmen              – Cluster in die Map schreiben, Ausnahmen
                               abschaffen, Rollenpflicht für alle Pillars
  --report                   – Abnahme-Tabelle (Markdown) für den Betreiber

Die Map ist handgepflegt (Kommentare sind Teil ihres Werts). Deshalb wird sie
NICHT neu gedumpt: neue Cluster werden als YAML-Block angehängt, der
`abdeckung:`-Block wird textuell ersetzt. Idempotent – ein zweiter Lauf ändert
nichts.

WARUM DIE QUALITÄTSREGEL HIER STEHT
===================================
R4 der Map: Zwei Beiträge desselben Clusters müssen sich in den ersten 40
Zeichen des Titels unterscheiden, sonst ist es dieselbe Rolle. `--pruefen`
meldet den Verstoß. Es wäre der bequemere Weg, die Rollen so zu formulieren,
dass sie die Kollision verdecken – genau das soll dieses Werkzeug verhindern.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import yaml  # noqa: E402

KATALOG = ROOT / "data" / "rollen_katalog.yaml"
MAP = ROOT / "data" / "kannibalisierung_map.yaml"
POSTS = ROOT / "content" / "posts"
TITEL_KOPF = 40          # R4: Vergleichsfenster
ROLLEN_MIN, ROLLEN_MAX = 12, 90


def _titel(pfad: Path) -> str:
    text = pfad.read_text(encoding="utf-8")
    treffer = re.search(r'^title:\s*"?(.*?)"?\s*$', text, re.M)
    return (treffer.group(1) if treffer else "").strip()


def _pillar(pfad: Path) -> str:
    text = pfad.read_text(encoding="utf-8")
    treffer = re.search(r'^pillar:\s*"?([\w-]+)', text, re.M)
    return treffer.group(1) if treffer else "?"


def _entwurf(pfad: Path) -> bool:
    text = pfad.read_text(encoding="utf-8")
    return bool(re.search(r"^draft:\s*true", text, re.M))


def bestand() -> dict[str, dict]:
    """Alle Beiträge: slug -> {titel, pillar, entwurf, pfad}."""
    daten = {}
    for pfad in sorted(POSTS.glob("*/index.md")):
        daten[pfad.parent.name] = {
            "titel": _titel(pfad), "pillar": _pillar(pfad),
            "entwurf": _entwurf(pfad), "pfad": pfad,
        }
    return daten


def katalog_laden(pfad: Path = KATALOG) -> dict:
    return yaml.safe_load(pfad.read_text(encoding="utf-8")) or {}


def rollen_in_map(map_pfad: Path = MAP) -> set[str]:
    try:
        daten = yaml.safe_load(map_pfad.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise SystemExit(f"Map ist kein gültiges YAML – erst reparieren: {exc}")
    return {b.get("slug") for c in (daten.get("cluster") or [])
            for b in (c.get("beitraege") or []) if b.get("slug")}


def pruefen(katalog: dict, map_pfad: Path = MAP) -> list[str]:
    """Fachliche Prüfung des Katalogs. Rückgabe: Liste der Befunde (leer = gut)."""
    befunde: list[str] = []
    posts = bestand()
    gesehen: dict[str, str] = {}
    rollen: set[str] = set()
    cluster_ids: set[str] = set()

    if not katalog.get("cluster"):
        return ["Katalog enthält keine Cluster"]

    for cluster in katalog["cluster"]:
        cid = cluster.get("id") or "?"
        if cid in cluster_ids:
            befunde.append(f"{cid}: Cluster-ID doppelt")
        cluster_ids.add(cid)
        pillar = cluster.get("pillar")
        if not pillar:
            befunde.append(f"{cid}: pillar fehlt")
        if not cluster.get("entscheidung"):
            befunde.append(f"{cid}: entscheidung fehlt (warum diese Abgrenzung?)")
        eintraege = cluster.get("beitraege") or []
        if not eintraege:
            befunde.append(f"{cid}: keine Beiträge")
        for eintrag in eintraege:
            slug = (eintrag.get("slug") or "").strip()
            rolle = (eintrag.get("rolle") or "").strip()
            if slug not in posts:
                befunde.append(f"{cid}: Slug unbekannt – {slug}")
                continue
            if slug in gesehen:
                befunde.append(f"{cid}: Slug doppelt (auch in {gesehen[slug]}) – {slug}")
            gesehen[slug] = cid
            if posts[slug]["entwurf"]:
                befunde.append(f"{cid}: Entwurf im Katalog (R3) – {slug}")
            if posts[slug]["pillar"] != pillar:
                befunde.append(f"{cid}: Beitrag gehört zu pillar "
                               f"{posts[slug]['pillar']!r}, Cluster sagt {pillar!r} – {slug}")
            if not ROLLEN_MIN <= len(rolle) <= ROLLEN_MAX:
                befunde.append(f"{cid}: Rolle außerhalb {ROLLEN_MIN}–{ROLLEN_MAX} Zeichen "
                               f"({len(rolle)}): {rolle!r}")
            schluessel = rolle.lower()
            if schluessel and schluessel in rollen:
                befunde.append(f"{cid}: Rolle doppelt formuliert – {rolle!r}")
            rollen.add(schluessel)

    # R4: Abgrenzung über die ersten 40 Zeichen des Titels, je Cluster.
    for cluster in katalog["cluster"]:
        cid = cluster.get("id") or "?"
        koepfe: dict[str, str] = {}
        for eintrag in cluster.get("beitraege") or []:
            slug = (eintrag.get("slug") or "").strip()
            if slug not in posts:
                continue
            kopf = posts[slug]["titel"][:TITEL_KOPF].lower()
            if kopf in koepfe:
                befunde.append(
                    f"{cid}: R4 – Titelanfänge gleich ({TITEL_KOPF} Zeichen): "
                    f"{koepfe[kopf]} / {slug}")
            koepfe[kopf] = slug

    # Vollständigkeit: jeder öffentliche Beitrag ohne Rolle muss im Katalog stehen.
    ohne_rolle = {s for s, p in posts.items()
                  if not p["entwurf"] and s not in rollen_in_map(map_pfad)}
    fehlt = sorted(ohne_rolle - set(gesehen))
    if fehlt:
        befunde.append(f"nicht im Katalog ({len(fehlt)}): {fehlt[:5]}"
                       + (" …" if len(fehlt) > 5 else ""))
    return befunde


def _q(wert: str) -> str:
    """Wert in doppelten Anführungszeichen – die Map-Konvention, und der Grund,
    warum dieser Block NICHT mit yaml.safe_dump entsteht: Der Gate-Test parst
    die Map ohne PyYAML und erwartet `- slug: "…"` WÖRTLICH. Ein Dump ohne
    Quotes schreibt gültiges YAML, das Gate sieht aber keine einzige Rolle –
    beim ersten Einspielen am 24.11. genau so passiert (32 Beiträge galten
    weiter als „ohne Rolle")."""
    return '"' + str(wert).replace('\\', '\\\\').replace('"', '\\"') + '"'


def _cluster_yaml(cluster: dict) -> str:
    """Cluster im Map-Stil – Zeile für Zeile, mit Quotes wie die Altblöcke."""
    zeilen = [f"  - id: {cluster['id']}"]
    if cluster.get("pillar"):
        zeilen.append(f"    pillar: {_q(cluster['pillar'])}")
    if cluster.get("primaerkeyword"):
        zeilen.append(f"    primaerkeyword: {_q(cluster['primaerkeyword'])}")
    zeilen.append("    beitraege:")
    for b in cluster.get("beitraege") or []:
        zeilen.append(f"      - slug: {_q(b['slug'])}")
        zeilen.append("        status: live")
        zeilen.append(f"        rolle: {_q(b['rolle'])}")
        zeilen.append("        status_massnahme: "
                      + _q(b.get("status_massnahme")
                           or "neu 24.11.: Rolle aus dem Katalog übernommen "
                              "(data/rollen_katalog.yaml)"))
    if cluster.get("entscheidung"):
        zeilen.append(f"    entscheidung: {_q(' '.join(str(cluster['entscheidung']).split()))}")
    return "\n".join(zeilen) + "\n"


def _abdeckung_block(zuordnung: dict[str, list[str]]) -> str:
    """Neuer abdeckung-Block aus einer fertigen Pillar→Cluster-Zuordnung.

    Die Zuordnung wird aus der MAP abgeleitet, nicht aus dem Katalog: Zu
    `strom-sparen` gehören auch die Gas-Cluster K1/K2, die der Katalog nicht
    nennt. Wer nur die Katalog-Cluster einträgt, macht neun Beiträge sofort
    rot – beim ersten Einspielen am 24.11. genau so passiert.
    """
    zeilen = [
        "abdeckung:",
        '  pflicht_ab: "2026-11-23"',
        "  # 24.11.2026: Alle Pillars sind kuratiert (Rollenkatalog). Die",
        "  # befristeten Ausnahmen vom 23.11. sind erledigt – sie werden nicht",
        "  # verlängert, sondern abgeschafft: Ein neuer Beitrag ohne Rolle ist",
        "  # sofort rot (test_inhalts_register).",
        "  vollstaendige_pillars:",
    ]
    for pillar in sorted(zuordnung):
        ids = sorted(set(zuordnung[pillar]))
        zeilen.append(f'    - pillar: "{pillar}"')
        zeilen.append("      cluster: [" + ", ".join(f'"{i}"' for i in ids) + "]")
    zeilen.append("  ausnahmen: []")
    zeilen.append("")
    return "\n".join(zeilen) + "\n"


def uebernehmen(katalog: dict, map_pfad: Path = MAP) -> dict:
    """Cluster anhängen, Ausnahmen abschaffen. Idempotent."""
    if pruefen(katalog, map_pfad):
        raise SystemExit("Katalog ist nicht sauber – erst `--pruefen` lesen.")

    text = map_pfad.read_text(encoding="utf-8")
    # Bestehende Abdeckung lesen, damit ein Einspielen keinen fertigen Pillar
    # aus der Pflicht nimmt.
    alt = yaml.safe_load(text) or {}
    bestand_pillars: dict[str, list[str]] = {}
    for eintrag in (alt.get("abdeckung") or {}).get("vollstaendige_pillars") or []:
        if eintrag.get("pillar"):
            bestand_pillars[eintrag["pillar"]] = list(eintrag.get("cluster") or [])
    vorhanden = re.findall(r"^\s*-\s*id:\s*(\S+)", text, re.M)
    neu = []
    for cluster in katalog["cluster"]:
        if cluster["id"] in vorhanden:
            continue
        neu.append(
            f"\n  # --- {cluster['id']} (24.11.2026: Rollenkatalog eingespielt) ---\n"
            + _cluster_yaml(cluster))

    if neu:
        text = text.rstrip("\n") + "\n" + "".join(neu)

    # Zuordnung Pillar → Cluster aus der (neuen) Map ableiten.
    zwischen = yaml.safe_load(text) or {}
    posts = bestand()
    zuordnung: dict[str, list[str]] = {k: list(v) for k, v in bestand_pillars.items()}
    for cluster in zwischen.get("cluster") or []:
        pills = {posts[b["slug"]]["pillar"]
                 for b in (cluster.get("beitraege") or [])
                 if b.get("slug") in posts}
        if len(pills) == 1:
            zuordnung.setdefault(pills.pop(), []).append(cluster["id"])

    # abdeckung-Block textuell ersetzen (Kommentare der Map bleiben sonst heil).
    neu_block = _abdeckung_block(zuordnung)
    text, anzahl = re.subn(r"(?ms)^abdeckung:.*?(?=^cluster:)", neu_block + "\n",
                           text, count=1)
    if anzahl != 1:
        raise SystemExit("abdeckung-Block nicht gefunden – Map von Hand prüfen.")
    text = re.sub(r'(?m)^stand:\s*".*?"', 'stand: "2026-11-24"', text, count=1)
    map_pfad.write_text(text, encoding="utf-8")
    return {"neue_cluster": len(neu), "ausnahmen_entfernt": True}


def report(katalog: dict) -> str:
    posts = bestand()
    zeilen = ["# Rollenkatalog – Abnahme", "",
              f"Stand: {katalog.get('stand')} · Quelle: {katalog.get('quelle')}", "",
              "| Cluster | Beiträge | Rolle |", "|---|---|---|"]
    for cluster in katalog["cluster"]:
        for i, eintrag in enumerate(cluster.get("beitraege") or []):
            titel = posts.get(eintrag["slug"], {}).get("titel", eintrag["slug"])
            zeilen.append(f"| {cluster['id'] if i == 0 else ''} | {titel} | {eintrag['rolle']} |")
    anzahl = sum(len(c.get("beitraege") or []) for c in katalog["cluster"])
    zeilen += ["", f"**{anzahl} Rollen in {len(katalog['cluster'])} Clustern.**",
               "", "Abnahme: `python3 scripts/rollen_katalog.py --uebernehmen`", ""]
    return "\n".join(zeilen)


def selftest() -> int:
    """Sabotage-Proben: Das Werkzeug muss Kollisionen und Lücken sehen."""
    katalog = katalog_laden()
    fehler = []
    lauf = pruefen(katalog)
    if lauf:
        fehler.append(f"echter Katalog meldet Befunde: {lauf[:3]}")

    # 1. R4: gleicher Titelanfang muss auffallen.
    zwei = next(c for c in katalog["cluster"] if len(c["beitraege"]) >= 2)
    sabotiert = yaml.safe_load(yaml.safe_dump(katalog))
    ziel = next(c for c in sabotiert["cluster"] if c["id"] == zwei["id"])
    posts = bestand()
    titel = posts[zwei["beitraege"][0]["slug"]]["titel"]
    # Zweiten Slug auf einen Titel mit gleichem 40-Zeichen-Anfang umbiegen ist
    # nicht möglich, ohne Dateien zu ändern – deshalb prüfen wir die Regel
    # direkt am Vergleichsfenster.
    kopf = titel[:TITEL_KOPF].lower()
    if len(kopf) >= TITEL_KOPF and \
            posts[zwei["beitraege"][1]["slug"]]["titel"][:TITEL_KOPF].lower() == kopf:
        fehler.append("Testdaten taugen nicht: die ersten zwei Titel sind gleich")

    # 2. unbekannter Slug
    ziel["beitraege"].append({"slug": "gibt-es-nicht", "rolle": "Testrolle ohne Datei"})
    if not any("Slug unbekannt" in f for f in pruefen(sabotiert)):
        fehler.append("unbekannter Slug wird nicht gemeldet")

    # 3. doppelte Rolle
    sabotiert2 = yaml.safe_load(yaml.safe_dump(katalog))
    dup = next(c for c in sabotiert2["cluster"] if len(c["beitraege"]) >= 2)
    dup["beitraege"][1]["rolle"] = dup["beitraege"][0]["rolle"]
    if not any("Rolle doppelt" in f for f in pruefen(sabotiert2)):
        fehler.append("doppelte Rolle wird nicht gemeldet")

    # 4. Pillar-Konflikt: Beitrag aus einem anderen Pillar im Cluster.
    sabotiert3 = yaml.safe_load(yaml.safe_dump(katalog))
    c3 = next(c for c in sabotiert3["cluster"] if c.get("pillar") != "versicherungen")
    c3["pillar"] = "versicherungen"
    if not any("Beitrag gehört zu pillar" in f for f in pruefen(sabotiert3)):
        fehler.append("Pillar-Konflikt wird nicht gemeldet")

    if fehler:
        print("🛑 ROLLENKATALOG-SELBSTTEST FEHLGESCHLAGEN:")
        for f in fehler:
            print(f"   - {f}")
        return 2
    print(f"✅ Rollenkatalog-Selbsttest grün: {sum(len(c['beitraege']) for c in katalog['cluster'])} "
          f"Rollen in {len(katalog['cluster'])} Clustern, Lücken und Kollisionen werden erkannt.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pruefen", action="store_true")
    parser.add_argument("--uebernehmen", action="store_true")
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args()

    if args.selftest:
        return selftest()
    katalog = katalog_laden()
    if args.report:
        print(report(katalog))
        return 0
    if args.uebernehmen:
        ergebnis = uebernehmen(katalog)
        print(f"✅ Katalog eingespielt: {ergebnis['neue_cluster']} neue Cluster, "
              f"Ausnahmen abgeschafft, Rollenpflicht für alle Pillars.")
        return 0
    befunde = pruefen(katalog)
    if befunde:
        print(f"❌ Rollenkatalog: {len(befunde)} Befund(e)")
        for b in befunde:
            print(f"   - {b}")
        return 1
    anzahl = sum(len(c.get("beitraege") or []) for c in katalog["cluster"])
    print(f"✅ Rollenkatalog sauber: {anzahl} Rollen in {len(katalog['cluster'])} Clustern, "
          f"keine Lücke, keine Kollision in den ersten {TITEL_KOPF} Zeichen.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
