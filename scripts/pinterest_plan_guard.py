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
from collections import Counter, defaultdict

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "data/pinterest_plan.yaml"
BOARDS_FILE = ROOT / "data/pinterest_boards.yaml"
REPORT = ROOT / "PINTEREST-PLAN-GUARD-REPORT.md"

DO_FIX = "--fix" in sys.argv
SELFTEST = "--selftest" in sys.argv

# --- P6/P7: Repeat-Pin-Schutz (02.09.2026, nach Pinterest-Spam-Sperre) -------
# Anlass: Der Plan verteilte 73 Pins auf nur 29 Ziel-URLs – ein Artikel bekam
# 9 Pins, vier Ziele sogar ZWEI Pins am selben Tag. Genau dieses Muster
# (viele Pins, wenige echte Ziele) wertet Pinterest als Link-Spam. Dass die
# Pin-Texte einzigartig formuliert sind, entlastet nicht – es sieht eher nach
# bewusster Umgehung aus.
#
# Die Grenzen sind bewusst konservativ für eine junge Affiliate-Domain:
MAX_PINS_PRO_ZIEL = 3      # mehr als 3 Pins pro URL im Planungsfenster = Spam-Risiko
MIN_TAGE_ABSTAND = 7       # derselbe Link frühestens nach einer Woche erneut

# --- P8: Ziel-Link-Wache (02.09.2026) ---------------------------------------
# Der eigentliche Sperrgrund vom 15.08.2026: Pins verlinkten das EIGENE
# Pinterest-Profil statt der Blogartikel. Folge: irreführende Verlinkung
# (Titel verspricht Ratgeber, Ziel ist ein Profil), eine Pinterest->Pinterest-
# Schleife ohne Mehrwert, und faktisch alle Pins auf eine einzige URL.
# P8 macht diesen Fehler technisch unmöglich. Harte Regel, kein Auto-Fix:
# Ein falsches Ziel kann das Skript nicht erraten - das muss ein Mensch setzen.
EIGENE_DOMAIN = "franksfinanzcheck.de"
VERBOTENE_ZIEL_HOSTS = (
    "pinterest.com", "pinterest.de", "pin.it",      # Selbstreferenz
    "bit.ly", "tinyurl.com", "t.co", "ow.ly",       # URL-Kürzer
)


def norm_url(u: str) -> str:
    """Ziel-URL ohne Query/Trailing-Slash – UTM-Varianten sind KEIN neues Ziel.

    Wichtig: Pinterest bewertet das Ziel, nicht den Tracking-Parameter. Zwei
    Pins auf dieselbe Seite mit verschiedenen utm_campaign-Werten sind für die
    Spam-Erkennung derselbe Link.
    """
    return re.sub(r"\?.*$", "", (u or "").strip()).rstrip("/")

def load_yaml(p):
    return yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}


def _selftest():
    """Eingefrorene Faelle fuer den Repeat-Pin-Schutz (P6/P7)."""
    fails = []

    # norm_url: UTM-Varianten sind dasselbe Ziel
    a = norm_url("https://x.de/posts/abc/?utm_source=pinterest&utm_campaign=pins")
    b = norm_url("https://x.de/posts/abc?utm_source=rss")
    if a != b:
        fails.append(f"norm_url: UTM-Varianten nicht gleich ({a!r} != {b!r})")
    if norm_url("https://x.de/posts/abc/") == norm_url("https://x.de/posts/xyz/"):
        fails.append("norm_url: verschiedene Ziele faelschlich gleich")

    def run(cases):
        """Miniatur-Nachbau der P6/P7-Auswahl; liefert Indizes der Streichungen."""
        bt = defaultdict(list)
        for i, p in enumerate(cases):
            bt[norm_url(p["url"])].append(i)
        drop = set()
        for _t, idxs in bt.items():
            ordered = sorted(idxs, key=lambda i: (cases[i]["tag"], i))
            kept = []
            for i in ordered:
                tg = cases[i]["tag"]
                if len(kept) >= MAX_PINS_PRO_ZIEL:
                    drop.add(i); continue
                if any(abs(tg - t) < MIN_TAGE_ABSTAND for t in kept):
                    drop.add(i); continue
                kept.append(tg)
        return drop

    U = "https://x.de/posts/a/"
    V = "https://x.de/posts/b/"

    # 1) Zwei Pins am SELBEN Tag auf dasselbe Ziel -> zweiter faellt (P7)
    d = run([{"url": U, "tag": 1}, {"url": U, "tag": 1}])
    if d != {1}:
        fails.append(f"P7 same-day nicht erkannt: {d}")

    # 2) Sauberer Abstand -> nichts faellt
    d = run([{"url": U, "tag": 1}, {"url": U, "tag": 8}, {"url": U, "tag": 15}])
    if d:
        fails.append(f"P7 bestraft gueltigen Abstand: {d}")

    # 3) Vier Pins mit gutem Abstand -> vierter faellt (P6-Deckel)
    d = run([{"url": U, "tag": 1}, {"url": U, "tag": 8},
             {"url": U, "tag": 15}, {"url": U, "tag": 22}])
    if d != {3}:
        fails.append(f"P6 Deckel greift nicht: {d}")

    # 4) Verschiedene Ziele am selben Tag sind ERLAUBT (kein Repeat)
    d = run([{"url": U, "tag": 3}, {"url": V, "tag": 3}])
    if d:
        fails.append(f"P6/P7 bestraft verschiedene Ziele: {d}")

    # 5) UTM-Variante desselben Ziels zaehlt als Wiederholung
    d = run([{"url": U, "tag": 1}, {"url": U + "?utm_source=x", "tag": 2}])
    if d != {1}:
        fails.append(f"UTM-Variante nicht als Repeat erkannt: {d}")

    # --- P8: Ziel-Link-Wache (der echte Sperrgrund vom 15.08.2026) ---
    def p8(raw):
        """Liefert den Fehlercode oder None, wenn das Ziel in Ordnung ist."""
        host = re.sub(r"^https?://", "", raw).split("/")[0].lower().lstrip("www.")
        pfad = re.sub(r"^https?://[^/]+", "", re.sub(r"\?.*$", "", raw)).strip("/")
        if not raw: return "leer"
        if any(h in host for h in VERBOTENE_ZIEL_HOSTS): return "verboten"
        if EIGENE_DOMAIN not in host: return "fremd"
        if not pfad: return "startseite"
        if raw.startswith("http://"): return "http"
        return None

    p8_faelle = [
        # (Ziel, erwarteter Code) – die ersten drei sind der reale Sperrgrund
        ("https://de.pinterest.com/franksfinanzcheck/",      "verboten"),
        ("https://www.pinterest.de/franksfinanzcheck/",      "verboten"),
        ("https://pin.it/abc123",                            "verboten"),
        ("http://franksfinanzcheck.de",                      "startseite"),
        ("https://franksfinanzcheck.de/",                    "startseite"),
        ("http://franksfinanzcheck.de/posts/abc/",           "http"),
        ("https://bit.ly/xyz",                               "verboten"),
        ("https://check24.de/dsl",                           "fremd"),
        ("",                                                 "leer"),
        # gueltig:
        ("https://franksfinanzcheck.de/posts/abc/",          None),
        ("https://franksfinanzcheck.de/pillar/frugalismus/", None),
        ("https://franksfinanzcheck.de/posts/abc/?utm_source=pinterest", None),
    ]
    for ziel, erwartet in p8_faelle:
        ist = p8(ziel)
        if ist != erwartet:
            fails.append(f"P8 {ziel!r}: erwartet {erwartet}, bekam {ist}")

    if fails:
        print("❌ PLAN-GUARD-SELFTEST FEHLGESCHLAGEN:")
        for f in fails:
            print("   -", f)
        return 2
    print("✅ PLAN-GUARD-SELFTEST bestanden (P6/P7 Repeat-Pin-Schutz + "
          "P8 Ziel-Link-Wache, 17 Faelle).")
    return 0


if SELFTEST:
    sys.exit(_selftest())

plan = load_yaml(PLAN)
pins = plan.get("pins", []) if isinstance(plan, dict) else []
boards_cfg = load_yaml(BOARDS_FILE)
valid_boards = {b["name"] for b in boards_cfg.get("boards", [])} if boards_cfg else set()

errors = []
fixed = 0

# P4 – Mindestmenge.
# 02.09.2026: Von 60 auf 40 gesenkt. Die alte Schwelle stammt aus der Zeit vor
# dem Repeat-Pin-Schutz und liess sich nur erreichen, indem derselbe Artikel
# mehrfach bepinnt wurde – also genau durch das Muster, das P6/P7 jetzt
# verbietet. Eine Mengenvorgabe, die man nur per Wiederholung erfuellen kann,
# ist ein Anreiz zum Spam. Mehr Pins entstehen ab jetzt durch mehr ARTIKEL,
# nicht durch mehr Pins pro Artikel.
if len(pins) < 40:
    errors.append(f"P4: Nur {len(pins)} Pins (erwartet >=40)")

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

# --- P6/P7: Repeat-Pin-Schutz -----------------------------------------------
# P6: max. MAX_PINS_PRO_ZIEL Pins pro Ziel-URL
# P7: mindestens MIN_TAGE_ABSTAND Tage zwischen zwei Pins auf dasselbe Ziel
#
# Heilung (--fix): überzählige Pins werden aus dem PLAN entfernt, nicht
# gelöscht – sie wandern nach data/pinterest_plan_parked.yaml und können
# später mit neuem Ziel (eigener Artikel!) reaktiviert werden. Behalten wird
# immer der jeweils früheste Pin je Ziel, danach nur, wer den Abstand wahrt.
# --- P8: Ziel-Link-Wache ----------------------------------------------------
for i, pin in enumerate(pins):
    raw = (pin.get("url") or pin.get("link") or "").strip()
    titel = (pin.get("titel") or pin.get("title") or "")[:40]
    host = re.sub(r"^https?://", "", raw).split("/")[0].lower().lstrip("www.")
    pfad = re.sub(r"^https?://[^/]+", "", re.sub(r"\?.*$", "", raw)).strip("/")

    if not raw:
        errors.append(f"P8 Pin '{titel}' hat KEIN Ziel")
    elif any(h in host for h in VERBOTENE_ZIEL_HOSTS):
        errors.append(
            f"P8 Pin '{titel}' verlinkt '{host}' – Pins muessen auf einen "
            f"eigenen Artikel zeigen, nie auf Pinterest/Kuerzer (Sperrgrund 15.08.)")
    elif EIGENE_DOMAIN not in host:
        errors.append(f"P8 Pin '{titel}' verlinkt Fremddomain '{host}'")
    elif not pfad:
        errors.append(
            f"P8 Pin '{titel}' zeigt auf die nackte Startseite – "
            f"Pins brauchen eine konkrete Zielseite")
    elif raw.startswith("http://"):
        errors.append(f"P8 Pin '{titel}' nutzt http:// statt https://")

by_target = defaultdict(list)
for i, pin in enumerate(pins):
    by_target[norm_url(pin.get("url") or pin.get("link") or "")].append(i)

drop_idx = set()
parked = []
for target, idxs in sorted(by_target.items()):
    if not target:
        continue
    # nach Tag sortieren (stabil), damit die Auswahl deterministisch ist
    ordered = sorted(idxs, key=lambda i: (pins[i].get("tag") or 0, i))
    kept_tags = []
    for i in ordered:
        tag = pins[i].get("tag") or 0
        titel = (pins[i].get("titel") or pins[i].get("title") or "")[:40]
        short = target.replace("https://franksfinanzcheck.de", "")
        if len(kept_tags) >= MAX_PINS_PRO_ZIEL:
            errors.append(
                f"P6 {len(ordered)} Pins auf dasselbe Ziel (max {MAX_PINS_PRO_ZIEL}): "
                f"{short[:48]} – Pin '{titel}' (Tag {tag})")
            drop_idx.add(i)
            continue
        too_close = [t for t in kept_tags if abs(tag - t) < MIN_TAGE_ABSTAND]
        if too_close:
            errors.append(
                f"P7 Abstand {abs(tag - too_close[-1])} Tage (min {MIN_TAGE_ABSTAND}): "
                f"{short[:48]} – Pin '{titel}' (Tag {tag})")
            drop_idx.add(i)
            continue
        kept_tags.append(tag)

if drop_idx:
    if DO_FIX:
        parked = [pins[i] for i in sorted(drop_idx)]
        keep = [p for i, p in enumerate(pins) if i not in drop_idx]
        plan["pins"] = keep
        pins = keep
        fixed += len(parked)
        park_file = ROOT / "data/pinterest_plan_parked.yaml"
        prev = load_yaml(park_file) or {}
        prev_pins = prev.get("pins", []) if isinstance(prev, dict) else []
        with open(park_file, "w", encoding="utf-8") as pf:
            yaml.safe_dump({"hinweis":
                            "Von P6/P7 (Repeat-Pin-Schutz) geparkte Pins. Kein "
                            "Content-Verlust: Diese Pins brauchen ein EIGENES "
                            "Ziel (neuer Artikel), dann koennen sie zurueck in "
                            "den Plan.",
                            "pins": prev_pins + parked},
                           pf, allow_unicode=True, sort_keys=False, width=1000)

# P2 Board-Counts (Untergrenze 02.09.2026 von 5 auf 3 gesenkt – gleiche
# Begruendung wie P4: die alte Schwelle war nur durch Repeat-Pins erreichbar.)
# by_board wurde VOR der P6/P7-Heilung gezaehlt; nach dem Parken neu zaehlen.
by_board = Counter((p.get("pinwand") or p.get("board") or "") for p in pins)
for board_name, cnt in by_board.items():
    if cnt < 3:
        errors.append(f"P2 Board '{board_name}' nur {cnt} Pins (<3)")

# Auch fehlende Boards aus Config melden
for vb in valid_boards:
    if vb not in by_board:
        errors.append(f"P2 Board '{vb}' fehlt komplett")

# Fix speichern
if DO_FIX and fixed>0:
    # safe_dump mit width
    with open(PLAN, "w", encoding="utf-8") as f:
        yaml.safe_dump(plan, f, allow_unicode=True, sort_keys=False, width=1000)
    print(f"Fix: {fixed} Pins geheilt "
          f"(P1 Werbung/P5 Länge: {fixed - len(parked)}, "
          f"P6/P7 geparkt: {len(parked)})")

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
