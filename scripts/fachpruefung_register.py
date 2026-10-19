#!/usr/bin/env python3
"""Fachprüfungs-Register: Prüfpaket für Live-Beiträge mit erhöhtem Risiko.

Erzeugt data/fachpruefung_register.yaml. Für jeden betroffenen Live-Beitrag:
  - Risikoklasse und Freigabestatus aus dem Frontmatter,
  - alle Sätze mit Euro- oder Prozentangaben als Fundstellen (Zahlenprotokoll-Vorlage),
  - der Hinweis, dass ein benannter Prüfer fehlt.

Die Freigabe selbst setzt dieses Skript nie. Der Prüfer muss ein Mensch sein
(Typ fachpruefer oder redaktion-mit-externer-belegkette, siehe
docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md).

Nutzung:
  python3 scripts/fachpruefung_register.py          # schreibt das Register
  python3 scripts/fachpruefung_register.py --check  # Exit 1, wenn es veraltet ist
"""
import glob
import os
import re
import sys

BLOG_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BLOG_DIR, "data", "fachpruefung_register.yaml")
MONEY = re.compile(r"\d[\d.,]*\s?(?:€|Euro|Prozent|%)")
ELEVATED = {"hoch", "erhoeht"}


def _field(front, key):
    # Auch eingerückte Schlüssel (z. B. unter redaktionelle_pruefung:) erfassen.
    m = re.search(rf'^\s*{key}: "?(.*?)"?\s*$', front, re.M)
    return m.group(1).strip() if m else ""


def _sentences(body):
    text = re.sub(r"[*_`]", "", body)
    text = re.sub(r"\s+", " ", text)
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if MONEY.search(s)]


def collect(max_reserve_date=None):
    items = []
    for path in sorted(glob.glob(os.path.join(BLOG_DIR, "content", "posts", "*", "index.md"))):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        front, body = text[4:].split("\n---\n", 1)
        if re.search(r"^draft: true", front, re.M):
            continue
        if max_reserve_date:
            m = re.search(r"^reserve_published:\s*(\d{4}-\d{2}-\d{2})\s*$", front, re.M)
            if m and m.group(1) > max_reserve_date:
                continue
        risk = _field(front, "risikoklasse") or "standard"
        pillar = _field(front, "pillar")
        status = _field(front, "status") or "ausstehend"
        if status == "freigegeben":
            continue
        if risk not in ELEVATED and pillar != "konto-karten":
            continue
        items.append({
            "slug": os.path.basename(os.path.dirname(path)),
            "titel": _field(front, "title"),
            "pillar": pillar,
            "risikoklasse": risk,
            "status": status,
            "fundstellen": _sentences(body)[:12],
        })
    return items


def render(items):
    lines = [
        "# Fachprüfungs-Register (automatisch erzeugt: scripts/fachpruefung_register.py)",
        "# Stand: 19.10.2026. Keine Freigabe. Jeder Eintrag braucht einen benannten Menschen als Prüfer.",
        "# Quellen je Aussage: docs/ANLEITUNG-REDAKTIONELLE-YMYL-PRUEFUNG.md (Schritte 1–5).",
        f"anzahl: {len(items)}",
        "pruefer_status: \"offen – kein benannter fachpruefer und keine Redaktionsprüfung mit Belegkette\"",
        "beitraege:",
    ]
    for it in items:
        lines.append(f'  - slug: "{it["slug"]}"')
        lines.append(f'    titel: "{it["titel"]}"')
        lines.append(f'    pillar: "{it["pillar"]}"')
        lines.append(f'    risikoklasse: "{it["risikoklasse"]}"')
        lines.append(f'    status: "{it["status"]}"')
        lines.append("    pruefer: null  # hier eintragen: Name, Rolle, Typ, Datum")
        lines.append("    zahlen_fundstellen:")
        if not it["fundstellen"]:
            lines.append("      []  # keine Euro-/Prozentangaben im Text")
        for s in it["fundstellen"]:
            safe = s.replace('"', "'")
            lines.append(f'      - "{safe[:220]}"')
    return "\n".join(lines) + "\n"


def main(argv):
    text = render(collect())
    if "--check" in argv:
        current = ""
        if os.path.isfile(OUT):
            with open(OUT, encoding="utf-8") as fh:
                current = fh.read()
        check_text = text
        if current != check_text:
            m = re.search(r"^# Stand:\s*(\d{2})\.(\d{2})\.(\d{4})\b", current, re.M)
            if m:
                stand_iso = f"{m.group(3)}-{m.group(2)}-{m.group(1)}"
                check_text = render(collect(max_reserve_date=stand_iso))
        if current != check_text:
            print("🛑 fachpruefung_register.yaml ist veraltet: python3 scripts/fachpruefung_register.py")
            return 1
        print("✅ Fachprüfungs-Register aktuell")
        return 0
    with open(OUT, "w", encoding="utf-8") as fh:
        fh.write(text)
    print(f"Fachprüfungs-Register geschrieben: {len(collect())} Beiträge → {os.path.relpath(OUT, BLOG_DIR)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
