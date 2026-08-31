#!/usr/bin/env python3
"""
PINTEREST-PLAN-GUARD – Validierung für data/pinterest_plan.yaml (P0-Fix 31.08.2026)

Prüft:
  P1  Alle Pins tragen *Werbung | (UWG + Pinterest Ad-Policy, seit 31.08. alle Affiliate)
  P2  Board-Counts >=5 (6 Premium-Boards)
  P3  pinwand Namen existieren in pinterest_boards.yaml
  P4  73 Pins vorhanden (oder >= Mindestanzahl)
  P5  Titel ≤100, Beschreibung ≤500

Modi:
  --check  nur prüfen (Exit 1 bei Fehler)
  --fix    heilt P1 (Werbung ergänzen) + kürzt zu lange Felder

Ausgabe: PINTEREST-PLAN-GUARD-REPORT.md
"""
import sys, yaml, re
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "data/pinterest_plan.yaml"
BOARDS_FILE = ROOT / "data/pinterest_boards.yaml"
REPORT = ROOT / "PINTEREST-PLAN-GUARD-REPORT.md"

DO_FIX = "--fix" in sys.argv

def load_yaml(p):
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}

plan = load_yaml(PLAN)
pins = plan.get("pins", []) if isinstance(plan, dict) else []
boards_cfg = load_yaml(BOARDS_FILE)
valid_boards = {b["name"] for b in boards_cfg.get("boards", [])} if boards_cfg else set()

errors = []
fixed = 0

# P4
if len(pins) < 60:
    errors.append(f"P4: Nur {len(pins)} Pins (erwartet >=60, aktuell 73)")

# P1, P5, P3
by_board = Counter()
for i, pin in enumerate(pins):
    title = pin.get("titel") or pin.get("title") or ""
    desc = pin.get("beschreibung") or pin.get("description") or ""
    board = pin.get("pinwand") or pin.get("board") or ""

    by_board[board] += 1

    # P1 Werbung
    if not desc.lstrip().startswith("*Werbung"):
        if DO_FIX:
            # idempotent fix
            new_desc = "*Werbung | " + desc.strip()
            # kürzen an Wortgrenze 500
            if len(new_desc) > 500:
                cut = new_desc[:500]
                sp = cut.rfind(" ")
                new_desc = cut[:sp].rstrip(" –—-:,;") if sp>0 else cut
            pin["beschreibung"] = new_desc[:500]
            fixed += 1
        else:
            errors.append(f"P1 Pin {i+1} '{title[:30]}' ohne *Werbung |")

    # P5 Länge
    if len(title) > 100:
        errors.append(f"P5 Titel zu lang ({len(title)}): {title[:40]}")
        if DO_FIX:
            pin["titel"] = title[:100]
            fixed += 1
    if len(desc) > 500 and not DO_FIX:
        errors.append(f"P5 Beschreibung zu lang ({len(desc)}): {title[:30]}")

    # P3 Board-Name
    if valid_boards and board not in valid_boards:
        errors.append(f"P3 Unbekanntes Board '{board}' bei Pin '{title[:30]}'")

# P2 Board-Counts
for board_name, cnt in by_board.items():
    if cnt < 5:
        errors.append(f"P2 Board '{board_name}' nur {cnt} Pins (<5)")

# Auch fehlende Boards aus Config melden
for vb in valid_boards:
    if by_board.get(vb,0) < 5:
        if vb not in by_board:
            errors.append(f"P2 Board '{vb}' fehlt komplett")
        # else already reported

# Fix speichern
if DO_FIX and fixed>0:
    # safe_dump mit width
    with open(PLAN, "w", encoding="utf-8") as f:
        yaml.safe_dump(plan, f, allow_unicode=True, sort_keys=False, width=1000)
    print(f"Fix: {fixed} Pins geheilt (Werbung ergänzt)")

# Report
with open(REPORT, "w", encoding="utf-8") as out:
    out.write("# 📌 PINTEREST-PLAN-GUARD-REPORT\n\n")
    out.write(f"**Stand:** {len(pins)} Pins, {len(by_board)} Boards, Fix: {fixed}\n\n")
    if not errors:
        out.write("🎉 Plan sauber: alle Pins mit *Werbung |, Boards ≥5, Titel/Desc im Limit.\n")
    else:
        out.write(f"**Fehler:** {len(errors)}\n\n")
        for e in errors:
            out.write(f"- {e}\n")

if errors and not DO_FIX:
    print(f"❌ {len(errors)} Fehler im Pinterest-Plan:")
    for e in errors[:20]:
        print(" ", e)
    sys.exit(1)
else:
    if not errors:
        print(f"✅ Plan sauber: {len(pins)} Pins, Boards: {dict(by_board)}")
    else:
        print(f"⚠️ {len(errors)} Fehler, aber {fixed} geheilt")
    sys.exit(0)
