#!/usr/bin/env python3
"""KI-Provenienz-Gate – die maschinenlesbare Kennzeichnung bleibt dran (#1028).

Befund, der dieses Gate nötig macht
-----------------------------------
Die sichtbare Kennzeichnung („Mit KI erstellt oder bearbeitet") ist seit dem
02.08.2026 da und durch ki_kennzeichnung_gate.py gesichert. Maschinenlesbar
war bis zum 05.11.2026 aber nur `data-ff-ki-label`, ein Selektor für eigene
Tests. Issue #1028 (Frist 02.12.2026) verlangt die maschinenlesbare Ebene.
Sie liegt jetzt auf vier Kanälen – und dieses Gate sorgt dafür, dass ein
späterer Template-Umbau sie nicht still wieder entfernt.

Regeln
------
M1  Auslieferung: Jede gebaute Seite mit `ai_generated: true` trägt
    `<meta name="ai-generated" content="true">`. Seiten ohne dieses Flag
    tragen es NICHT (Abwesenheit ist keine Behauptung „rein menschlich").
M2  Vertrag: head.html bindet ki_provenienz.html ein, schema_article.html
    emittiert `creditText`, cover.html emittiert `data-digital-source-type`,
    das Impressum trägt den Anker `#ki-hinweis`.
M3  Bilddatei: Jedes als KI deklarierte Cover trägt IPTC
    `DigitalSourceType` in der Datei (ki_bild_markierung.py).
M4  Kanaltreue: Auf posts/ läuft das Meta-Signal nicht ohne den sichtbaren
    Hinweis (`data-ff-ki-label`) und umgekehrt – Leser und Maschine sehen
    dieselbe Wahrheit.

Grenze: Ein grünes Laufergebnis ist kein Herkunftsbeweis und keine
Anbieter-Markierung nach Art. 50 Abs. 2 KI-VO (siehe
docs/KI-TRANSPARENZ-ABNAHME.md).

Aufruf
------
    python3 scripts/ki_provenienz_gate.py                 # Befund
    python3 scripts/ki_provenienz_gate.py --gate          # Exit 1 bei Fund
    python3 scripts/ki_provenienz_gate.py --selftest
    python3 scripts/ki_provenienz_gate.py --json

Exit: 0 = sauber · 1 = Fund (--gate) · 2 = Fehler
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PARTIAL = "layouts/_partials/ki_provenienz.html"
META_MUSTER = re.compile(r"<meta\s+name=[\"']?ai-generated[\"']?\s+content=[\"']?(true|false)[\"']?", re.I)
SICHTBAR_MUSTER = re.compile(r"data-ff-ki-label")
BAU = "public"


def kopf_von(text: str) -> str:
    if not text.startswith("---"):
        return ""
    ende = text.find("\n---", 3)
    return text[3:ende] if ende > 0 else ""


def feld(kopf: str, name: str) -> str | None:
    m = re.search(rf"(?m)^{name}:\s*(.+?)\s*$", kopf)
    return m.group(1).strip().strip("\"'") if m else None


def seiten(posts: Path):
    """(Inhaltspfad, Slug, ai_generated, Entwurf) für alle Artikel."""
    for p in sorted(posts.rglob("*.md")):
        if p.name == "_index.md":
            continue
        kopf = kopf_von(p.read_text(encoding="utf-8", errors="ignore"))
        if not kopf:
            continue
        slug = p.parent.name if p.name == "index.md" else p.stem
        yield p, slug, feld(kopf, "ai_generated") == "true", feld(kopf, "draft") == "true"


def regel_m1(bau: Path, posts: Path):
    """Meta-Signal im Bauprodukt gegen das Frontmatter prüfen."""
    funde, geprueft = [], 0
    if not bau.is_dir():
        return [{"regel": "M1", "text": f"kein Bauprodukt unter {bau}/ – Auslieferung nicht geprüft "
                                        "(nach `hugo` erneut laufen lassen)"}], 0
    for pfad, slug, ki, entwurf in seiten(posts):
        if entwurf:
            continue
        datei = bau / "posts" / slug / "index.html"
        if not datei.is_file():
            funde.append({"regel": "M1", "text": f"{slug}: kein Bauprodukt unter "
                                                 f"{datei.relative_to(bau.parent)} – Auslieferung nicht prüfbar"})
            continue
        html = datei.read_text(encoding="utf-8", errors="ignore")
        treffer = META_MUSTER.search(html)
        geprueft += 1
        if ki and not (treffer and treffer.group(1).lower() == "true"):
            funde.append({"regel": "M1", "text": f"{slug}: ai_generated: true, aber das gebaute HTML "
                                                 "trägt kein <meta name=\"ai-generated\" content=\"true\">"})
        elif not ki and treffer and treffer.group(1).lower() == "true":
            funde.append({"regel": "M1", "text": f"{slug}: ohne ai_generated: true wird eine KI-Erzeugung "
                                                 "ausgewiesen – Signal entfernen oder Herkunft klären"})
    return funde, geprueft


def regel_m2(root: Path):
    """Vertrag der Vorlagen: die Kanäle müssen eingebunden bleiben."""
    funde = []
    erwartungen = [
        ("layouts/_partials/head.html", "ki_provenienz.html",
         "head.html bindet ki_provenienz.html nicht mehr ein"),
        ("layouts/_partials/schema_article.html", "creditText",
         "schema_article.html emittiert kein creditText mehr"),
        ("layouts/_partials/cover.html", "data-digital-source-type",
         "cover.html emittiert kein data-digital-source-type mehr"),
        ("content/impressum/index.md", "{#ki-hinweis}",
         "der Anker #ki-hinweis im Impressum fehlt – rel=\"describedby\" läuft ins Leere"),
    ]
    for rel, nadel, meldung in erwartungen:
        datei = root / rel
        if not datei.is_file():
            funde.append({"regel": "M2", "text": f"{rel} fehlt"})
        elif nadel not in datei.read_text(encoding="utf-8", errors="ignore"):
            funde.append({"regel": "M2", "text": f"{rel}: {meldung}"})
    return funde


def regel_m3(root: Path):
    """Maschinenlesbare Markierung in den deklarierten KI-Bilddateien."""
    sys.path.insert(0, str(root / "scripts"))
    try:
        import ki_bild_markierung  # noqa: PLC0415
    except ImportError as exc:
        return [{"regel": "M3", "text": f"ki_bild_markierung.py nicht ladbar: {exc}"}]
    try:
        _, fehler = ki_bild_markierung.pruefen(root)
    except (OSError, ValueError) as exc:
        return [{"regel": "M3", "text": f"Bildbestand nicht lesbar: {exc}"}]
    return [{"regel": "M3", "text": f} for f in fehler]


def regel_m4(bau: Path, posts: Path):
    """Sichtbarer Hinweis und Meta-Signal dürfen nicht auseinanderlaufen.

    Verglichen wird, was tatsächlich im Bauprodukt steht – nicht das
    Frontmatter. Damit fällt auch eine halbe Regression auf: ein Kanal da,
    der andere weg.
    """
    funde = []
    if not bau.is_dir():
        return funde
    gebaute = {slug for _, slug, _, entwurf in seiten(posts) if not entwurf}
    for slug in sorted(gebaute):
        datei = bau / "posts" / slug / "index.html"
        if not datei.is_file():
            continue
        html = datei.read_text(encoding="utf-8", errors="ignore")
        meta = META_MUSTER.search(html)
        signal = bool(meta and meta.group(1).lower() == "true")
        sichtbar = bool(SICHTBAR_MUSTER.search(html))
        if signal and not sichtbar:
            funde.append({"regel": "M4", "text": f"{slug}: maschinenlesbares Signal ohne sichtbaren "
                                                 "Hinweis am Artikel"})
        elif sichtbar and not signal:
            funde.append({"regel": "M4", "text": f"{slug}: sichtbarer Hinweis ohne maschinenlesbares "
                                                 "Signal im Dokumentkopf"})
    return funde


def pruefen(root: Path = ROOT, bau: Path | None = None):
    bau = bau or root / BAU
    posts = root / "content" / "posts"
    if not posts.is_dir():
        return [], 0
    m1, geprueft = regel_m1(bau, posts)
    funde = m1 + regel_m2(root) + regel_m3(root) + regel_m4(bau, posts)
    return funde, geprueft


def selbsttest() -> int:
    """Prüft die Regeln an einer künstlichen, aber echten Dateilage."""
    import shutil
    import tempfile

    fehler = []
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "content" / "posts" / "ki-artikel").mkdir(parents=True)
        (root / "content" / "posts" / "mensch-artikel").mkdir(parents=True)
        (root / "content" / "posts" / "entwurf").mkdir(parents=True)
        (root / "content" / "posts" / "ki-artikel" / "index.md").write_text(
            "---\ntitle: KI\nai_generated: true\n---\nText\n", encoding="utf-8")
        (root / "content" / "posts" / "mensch-artikel" / "index.md").write_text(
            "---\ntitle: Mensch\nai_generated: false\n---\nText\n", encoding="utf-8")
        (root / "content" / "posts" / "entwurf" / "index.md").write_text(
            "---\ntitle: Entwurf\nai_generated: true\ndraft: true\n---\nText\n", encoding="utf-8")
        # M2: Vorlagen-Vertrag aus dem echten Bestand übernehmen
        for rel in ("layouts/_partials/head.html", "layouts/_partials/schema_article.html",
                    "layouts/_partials/cover.html", "content/impressum/index.md"):
            ziel = root / rel
            ziel.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy(ROOT / rel, ziel)
        # M3: leeres Bildregister → keine Funde erwartet
        (root / "scripts").mkdir(exist_ok=True)
        shutil.copy(ROOT / "scripts" / "ki_bild_markierung.py", root / "scripts" / "ki_bild_markierung.py")
        shutil.copy(ROOT / "scripts" / "ki_cover_provenienz.py", root / "scripts" / "ki_cover_provenienz.py")

        # 1) ohne Bauprodukt: M1 meldet den Hinweis, sonst ist alles grün
        funde, _ = pruefen(root)
        if [f["regel"] for f in funde] != ["M1"]:
            fehler.append(f"ohne Bauprodukt: {[f['text'] for f in funde]}")

        # 2) korrektes Bauprodukt: keine Funde
        bau = root / BAU
        for slug, meta, sichtbar in (("ki-artikel", True, True), ("mensch-artikel", False, False)):
            datei = bau / "posts" / slug / "index.html"
            datei.parent.mkdir(parents=True, exist_ok=True)
            kopf = '<meta name="ai-generated" content="true">' if meta else ""
            label = '<span data-ff-ki-label>Mit KI erstellt oder bearbeitet</span>' if sichtbar else ""
            datei.write_text(f"<html><head>{kopf}</head><body>{label}</body></html>", encoding="utf-8")
        funde, geprueft = pruefen(root)
        if funde:
            fehler.append(f"korrekter Stand meldet {[f['text'] for f in funde]}")
        if geprueft != 2:
            fehler.append(f"{geprueft} Seiten geprüft statt 2 (Entwurf muss übersprungen werden)")

        # 3) Meta-Signal fehlt bei KI-Artikel → M1 und M4
        datei = bau / "posts" / "ki-artikel" / "index.html"
        datei.write_text('<html><head></head><body><span data-ff-ki-label>x</span></body></html>',
                         encoding="utf-8")
        regeln = sorted({f["regel"] for f in pruefen(root)[0]})
        if regeln != ["M1", "M4"]:
            fehler.append(f"fehlendes Meta-Signal: {regeln} statt ['M1', 'M4']")

        # 4) unbelegtes Signal auf menschlichem Artikel → M1
        datei.write_text('<html><head><meta name="ai-generated" content="true"></head>'
                         '<body><span data-ff-ki-label>x</span></body></html>', encoding="utf-8")
        (bau / "posts" / "mensch-artikel" / "index.html").write_text(
            '<html><head><meta name="ai-generated" content="true"></head><body></body></html>',
            encoding="utf-8")
        regeln = sorted({f["regel"] for f in pruefen(root)[0]})
        if "M1" not in regeln:
            fehler.append(f"unbelegtes Signal: {regeln} statt M1-Fund")

        # 5) M2: Einbindung entfernt → Fund
        kopf = root / "layouts/_partials/head.html"
        kopf.write_text(kopf.read_text(encoding="utf-8").replace("ki_provenienz.html", "weg.html"),
                        encoding="utf-8")
        if not any(f["regel"] == "M2" for f in pruefen(root)[0]):
            fehler.append("M2 merkt die entfernte Einbindung nicht")

    for f in fehler:
        print(f"❌ {f}")
    if fehler:
        return 2
    print("✅ KI-Provenienz-Gate: M1 Auslieferung, M2 Vorlagenvertrag, M3 Bilddatei, M4 Kanaltreue.")
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    gruppe = parser.add_mutually_exclusive_group()
    gruppe.add_argument("--gate", action="store_true")
    gruppe.add_argument("--selftest", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--public", default=None, help="Ort des Bauprodukts (Voreinstellung public/)")
    args = parser.parse_args(argv)

    if args.selftest:
        return selbsttest()
    bau = Path(args.public) if args.public else ROOT / BAU
    try:
        funde, geprueft = pruefen(bau=bau)
    except (OSError, ValueError) as exc:
        print(f"KI-Provenienz-Gate nicht ausführbar: {exc}")
        return 2

    if args.json:
        print(json.dumps({"gepruefte_seiten": geprueft, "funde": funde}, ensure_ascii=False, indent=2))
    else:
        print(f"KI-Provenienz: {geprueft} gebaute Seiten geprüft, {len(funde)} Fund(e).")
        for f in funde:
            print(f"::error title=KI-Provenienz {f['regel']}::{f['text']}")
        if not funde:
            print("✅ Maschinenlesbare Kennzeichnung liegt auf allen Kanälen "
                  "(Meta, schema.org creditText, Bildattribut, IPTC-Feld).")
    if args.gate and funde:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
