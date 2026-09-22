#!/usr/bin/env python3
"""
reserve_quarantine.py – Dauer-Blocker aus dem Reserve-Pool ausmustern.

WARUM DIESE DATEI EXISTIERT (Reparatur 15.09.2026, Issue #295,
Run 34967470666):
  Der harte End-Gate der Content-Reserve verlangt RESERVE_TARGET gate-fertige
  Kandidaten („Stock shortage must not look successful“). Damit ist der Lauf
  strukturell erpressbar: EIN Kandidat, den kein Heiler reparieren kann,
  macht das Ziel dauerhaft unerreichbar, sobald die Themen-Dedup keinen
  Ersatz mehr hergibt. Genau so stand es am 15.09.:

      Pool 6 Entwürfe · 5 gate-fertig · 1 mit verstümmelter Mid-CTA
      („Spar‑Tipp zwischendurch … –“, ohne Link, Label mit U+2011)

  Der Fund war deterministisch, aber unbehandelbar (kein Heiler kannte die
  Klasse, die Wache selbst durfte im STRICT-DRY-RUN nicht schreiben). Der
  Konvergenz-Nachschub fand kein freies Thema mehr, also blieb der Stand
  Nacht für Nacht 5/6 – roter Lauf ohne Handlungsoption.

  Reserve ist ein VORRAT, keine Geiselnahme. Diese Wache zieht die Reißleine
  deterministisch, spät und nachvollziehbar:

    * NUR deterministische Content-Funde. Werkzeug-/API-Ausnahmen
      („Gate-Ausnahme: …“) zählen nicht – ein Hugo-Timeout ist kein Urteil
      über den Artikel.
    * Erst nach RESERVE_QUARANTINE_HITS (Default 2) LÄUFEN mit DEMSELBEN Fund
      (Reparatur 22.09.2026, #349: vorher zählte jede ZERTIFIZIERUNG – und ein
      einziger Nachtlauf zertifiziert mehrfach: Stufe 3, dann jede Runde der
      Konvergenz. Ein Kandidat konnte damit nach EINER Nacht ausgemustert
      werden, obwohl der Vertrag „zwei Läufe“ lautet und jeder Lauf von einem
      vollen Durchgang der Heiler-Kette gedeckt sein soll. Der Zähler trägt
      jetzt die Lauf-Kennung (`GITHUB_RUN_ID`), die Zertifizierungen desselben
      Laufs zählen zusammen genau einmal. Jede Zertifizierung ist von einem
      vollen Durchlauf der Heiler-Kette gedeckt – zwei gleiche Funde in zwei
      Läufen heißen also: reparatur-resistent, nicht Pech.
    * Nichts wird gelöscht. Der Entwurf bleibt im content/-Baum, verliert die
      `reserve: true`-Fahne und bekommt `reserve_blocked` + `reserve_blocked_at`.
      Damit zählt er nicht mehr in den Pool (reserve_pool.reserve_drafts),
      draft_triage zeigt ihn weiterhin mit seinen Blockern, und die Redaktion
      kann ihn durch Entfernen der Fahne jederzeit wieder aufnehmen.

  Der Zustand liegt in data/reserve-quarantine.json (mitlaufend im Repo, also
  über Läufe hinweg gültig). Jeder Eingriff wird zusätzlich nach
  data/audit/<datum>.jsonl geschrieben, falls audit_log verfügbar ist.

MODI:
    python3 scripts/reserve_quarantine.py                 # Zustand melden
    python3 scripts/reserve_quarantine.py --status --json # maschinenlesbar
    python3 scripts/reserve_quarantine.py --selftest      # Sabotage-Schutz

EXIT: 0 = ok · 2 = Selbsttest fehlgeschlagen
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from post_utils import join_article  # noqa: E402  – Naht-SSOT (FM-Grenze)

STATE = ROOT / "data" / "reserve-quarantine.json"
POSTS_DIR = ROOT / "content" / "posts"
HITS_DEFAULT = 2

# Werkzeug-/Infrastruktur-Fehler sind KEIN Urteil über den Artikel. Solche
# Kandidaten bleiben im Pool und zählen nicht auf die Quarantäne ein.
TRANSIENT = ("Gate-Ausnahme", "timeout", "Traceback", "Connection",
             "temporär", "temporaer")


def hits_limit() -> int:
    try:
        return max(1, int(os.environ.get("RESERVE_QUARANTINE_HITS")
                          or HITS_DEFAULT))
    except ValueError:
        return HITS_DEFAULT


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def signatur(grund: str) -> str:
    """Stabile Fund-Signatur: gleiche Ursache = gleiche Signatur.

    Zahlen, Slugs und Zeitstempel werden entfernt – sonst gilt „1.134 Wörter
    zu kurz“ und „1.141 Wörter zu kurz“ als zwei verschiedene Funde und die
    Quarantäne greift nie.
    """
    text = (grund or "").strip().lower()
    text = re.sub(r"\d{4}-\d{2}-\d{2}[-\w]*", "<slug>", text)
    text = re.sub(r"0\.\d+", "<score>", text)
    text = re.sub(r"\d+", "<n>", text)
    text = re.sub(r"\s+", " ", text)
    return text[:200]


def is_transient(grund: str) -> bool:
    return any(z.lower() in (grund or "").lower() for z in TRANSIENT)


def lauf_kennung() -> str:
    """Identität des laufenden Reserve-Laufs (eine Nacht = eine Kennung).

    GitHub Actions setzt `GITHUB_RUN_ID` in jedem Step – auch die Zertifizierung
    der Stufe 3 und jede Konvergenz-Runde gehören zu DEMSELBEN Lauf. Außerhalb
    von Actions (Handlauf, Selbsttest) zählt der Kalendertag; ein Handlauf
    erzeugt damit höchstens einen Zähler pro Tag.
    """
    run_id = (os.environ.get("GITHUB_RUN_ID") or "").strip()
    if run_id:
        return f"run:{run_id}"
    return "lokal:" + dt.datetime.now(dt.timezone.utc).date().isoformat()


def load_state(path: Path = STATE) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def save_state(state: dict, path: Path = STATE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2,
                               sort_keys=True) + "\n", encoding="utf-8")


def audit(slug: str, grund: str, hits: int) -> None:
    """Eingriff ins Audit-Log – Quarantäne darf nie unsichtbar sein."""
    try:
        import audit_log
        audit_log.log("reserve_quarantine", "block",
                      {"slug": slug, "hits": hits, "grund": grund},
                      status="ok")
    except Exception:  # noqa: BLE001 – Audit ist Beigabe, nie Blockade
        pass


def block_candidate(slug: str, grund: str, posts_dir: Path = POSTS_DIR) -> str | None:
    """Nimmt den Kandidaten aus dem Pool: reserve-Fahne raus, Grund rein.

    Rückgabe: gesetzter Grund (str) oder None, wenn nichts zu tun war.
    Der Entwurf selbst bleibt unangetastet – nur die Pool-Zugehörigkeit
    ändert sich. JSON-Quoting liefert gültiges YAML (Doppelquote).
    """
    index = posts_dir / slug / "index.md"
    if not index.is_file():
        return None
    text = index.read_text(encoding="utf-8")
    parts = text.split("---", 2)
    if len(parts) != 3 or parts[0] != "":
        return None
    fm = parts[1]
    if re.search(r"(?m)^reserve_blocked:", fm):
        return None                      # bereits ausgemustert
    eintrag = (f'reserve_blocked: {json.dumps(grund[:180], ensure_ascii=False)}\n'
               f'reserve_blocked_at: {now_iso()}')
    # Die Fahne wird ZEILENGENAU durch den Grund ersetzt (lesbarer Diff, kein
    # Anhängen ans Frontmatter-Ende). Lambda statt String-Ersetzung: JSON-
    # Quoting enthält Backslashes, die re.sub sonst als Gruppe liest.
    fm_neu, n = re.subn(r"(?m)^reserve:\s*(?:true|yes|1)\s*$",
                        lambda _m: eintrag, fm, count=1)
    if not n:
        return None                      # kein Pool-Kandidat -> nichts tun
    index.write_text(join_article(fm_neu, parts[2]), encoding="utf-8")
    return grund


def record(rows: list[dict], state_path: Path | None = None,
           posts_dir: Path | None = None, *, apply: bool = True,
           run_key: str | None = None) -> list[dict]:
    """Zählt Funde je Kandidat und mustert Reparatur-resistenten aus.

    `rows` ist die Kandidatenliste der Zertifizierung (data/reserve-readiness
    .json-Format). Rückgabe: Liste der in DIESEM Aufruf blockierten Kandidaten
    [{"slug", "grund", "hits"}].

    `run_key` ist die Identität des LAUFS (Default: `lauf_kennung()`, also
    `GITHUB_RUN_ID`). Mehrere Zertifizierungen derselben Nacht (Stufe 3 +
    Konvergenz-Runden) zählen zusammen genau EINEN Zähler – vorher zählte jede
    Zertifizierung, weshalb ein Kandidat nach einer einzigen Nacht ausgemustert
    wurde, obwohl der Vertrag zwei Läufe verlangt (#349).

    Pfade werden BEIM AUFRUF aufgelöst, nicht als Default-Wert gebunden: Ein
    Default-Argument friert den Wert beim Import ein – Aufrufer (und Tests)
    können STATE/POSTS_DIR dann nicht mehr umlenken, und die Wache schreibt
    still in den echten Bestand. Befund aus dem Integrationstest 15.09.2026.
    """
    key = run_key if run_key is not None else lauf_kennung()
    state_path = Path(state_path) if state_path else STATE
    posts_dir = Path(posts_dir) if posts_dir else POSTS_DIR
    limit = hits_limit()
    state = load_state(state_path)
    blocked: list[dict] = []
    seen = set()

    for row in rows:
        slug = row.get("slug")
        if not slug:
            continue
        seen.add(slug)
        if row.get("ready") is True:
            state.pop(slug, None)        # geheilt -> Zähler zurück
            continue
        grund = row.get("reason") or "unbekannter Gate-Fund"
        if is_transient(grund):
            continue                     # Infrastruktur, kein Content-Urteil
        sig = signatur(grund)
        eintrag = state.get(slug)
        if not eintrag or eintrag.get("signatur") != sig:
            eintrag = {"signatur": sig, "hits": 0, "first": now_iso(),
                       "grund": grund}
        # Ein Lauf zählt genau einmal – auch wenn die Zertifizierung in
        # derselben Nacht mehrfach läuft (#349). Ein neuer Fund (andere
        # Signatur) beginnt wieder bei null und zählt in diesem Lauf.
        if eintrag.get("lauf") != key:
            eintrag["hits"] = int(eintrag.get("hits", 0)) + 1
            eintrag["lauf"] = key
            laeufe = [l for l in (eintrag.get("laeufe") or []) if l != key]
            laeufe.append(key)
            eintrag["laeufe"] = laeufe[-5:]      # Nachweis, gedeckelt
        eintrag["last"] = now_iso()
        eintrag["grund"] = grund
        state[slug] = eintrag
        if eintrag["hits"] < limit:
            continue
        if apply:
            gesetzt = block_candidate(slug, grund, posts_dir)
            if gesetzt is None:
                continue                 # z. B. schon blockiert / kein Entwurf
            audit(slug, grund, eintrag["hits"])
        blocked.append({"slug": slug, "grund": grund, "hits": eintrag["hits"]})

    # Kandidaten, die gar nicht mehr im Pool sind, brauchen keinen Zähler.
    for slug in [s for s in state if s not in seen]:
        state.pop(slug, None)

    if apply:
        save_state(state, state_path)
    return blocked


def status(state_path: Path | None = None, as_json: bool = False) -> int:
    state = load_state(Path(state_path) if state_path else STATE)
    if as_json:
        print(json.dumps(state, ensure_ascii=False, indent=1, sort_keys=True))
        return 0
    if not state:
        print("🟢 Reserve-Quarantäne: keine offenen Zähler "
              f"(Grenze {hits_limit()} Läufe mit demselben Fund).")
        return 0
    print(f"🧱 Reserve-Quarantäne: {len(state)} Kandidat(en) mit offenen "
          f"Zählern (Grenze {hits_limit()} Läufe mit demselben Fund):")
    for slug, e in sorted(state.items()):
        print(f"   - {slug}: {e.get('hits')}/{hits_limit()} · "
              f"{(e.get('grund') or '')[:120]}")
    return 0


def run_selftest() -> int:
    fehler: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        posts = root / "content" / "posts"
        (posts / "2026-09-15-block").mkdir(parents=True)
        (posts / "2026-09-15-block" / "index.md").write_text(
            "---\ntitle: \"Block\"\ndraft: true\nreserve: true\n"
            "pillar: \"frugalismus\"\n---\n\nText.\n", encoding="utf-8")
        (posts / "2026-09-15-gut").mkdir(parents=True)
        (posts / "2026-09-15-gut" / "index.md").write_text(
            "---\ntitle: \"Gut\"\ndraft: true\nreserve: true\n---\n\nText.\n",
            encoding="utf-8")
        state_path = root / "reserve-quarantine.json"

        rows = [{"slug": "2026-09-15-block", "ready": False,
                 "reason": "quality-score 0.83 < 0.85 (schwach: spelling 0.50, "
                           "typography 0.78)"},
                {"slug": "2026-09-15-gut", "ready": True}]

        # 1) Erster Fund: Zähler steht, aber es wird NICHT eingegriffen.
        blocked = record(rows, state_path, posts, apply=True,
                         run_key="run:1")
        if blocked:
            fehler.append(f"erster Fund darf nicht blockieren: {blocked}")
        text = (posts / "2026-09-15-block" / "index.md").read_text("utf-8")
        if "reserve_blocked" in text or "reserve: true" not in text:
            fehler.append("nach dem ersten Fund muss der Kandidat im Pool bleiben")
        # 1b) REPARATUR 22.09.2026 (#349): Die Zertifizierung läuft in EINER
        #     Nacht mehrfach (Stufe 3 + jede Konvergenz-Runde). Derselbe Fund
        #     in DEMSELBEN Lauf ist EIN Zähler – vorher reichte eine Nacht,
        #     um einen heilbaren Kandidaten auszumustern.
        blocked = record(rows, state_path, posts, apply=True,
                         run_key="run:1")
        if blocked:
            fehler.append(f"zweite Zertifizierung desselben Laufs darf nicht "
                          f"blockieren: {blocked}")
        if int(load_state(state_path)["2026-09-15-block"]["hits"]) != 1:
            fehler.append("mehrere Zertifizierungen eines Laufs zählen mehrfach")

        # 2) Zweiter LAUF mit demselben Fund (andere Messwerte -> gleiche
        #    Signatur) -> Quarantäne greift.
        rows[0]["reason"] = ("quality-score 0.84 < 0.85 (schwach: spelling "
                             "0.52, typography 0.80)")
        blocked = record(rows, state_path, posts, apply=True,
                         run_key="run:2")
        if len(blocked) != 1 or blocked[0]["slug"] != "2026-09-15-block":
            fehler.append(f"zweiter gleicher Fund muss blockieren: {blocked}")
        text = (posts / "2026-09-15-block" / "index.md").read_text("utf-8")
        if "reserve_blocked:" not in text:
            fehler.append("blockierter Kandidat braucht reserve_blocked-Feld")
        if re.search(r"(?m)^reserve:\s*true", text):
            fehler.append("blockierter Kandidat darf nicht mehr reserve:true sein")
        if "pillar: \"frugalismus\"" not in text or "Text." not in text:
            fehler.append("Quarantäne darf den Entwurf nicht beschädigen")
        if text.startswith("---\n") is False or "\n---\n" not in text:
            fehler.append("Frontmatter-Grenzen müssen intakt bleiben")

        # 3) Idempotenz: Derselbe Fund in einem dritten Lauf – der Kandidat ist
        #    bereits ausgemustert, also kein zweiter Eingriff, kein Churn.
        before = text
        blocked2 = record([{"slug": "2026-09-15-block", "ready": False,
                            "reason": rows[0]["reason"]}], state_path, posts,
                          apply=True, run_key="run:3")
        if blocked2:
            fehler.append(f"bereits blockiert darf nicht erneut melden: {blocked2}")
        if (posts / "2026-09-15-block" / "index.md").read_text("utf-8") != before:
            fehler.append("Quarantäne ist nicht idempotent (churnt)")

        # 4) Geheilter Kandidat: Zähler verschwindet.
        state = load_state(state_path)
        state["2026-09-15-gut"] = {"signatur": "x", "hits": 1, "grund": "alt"}
        save_state(state, state_path)
        record([{"slug": "2026-09-15-gut", "ready": True}], state_path, posts)
        if "2026-09-15-gut" in load_state(state_path):
            fehler.append("geheilter Kandidat muss den Zähler verlieren")

        # 5) Werkzeugfehler zählen nicht (kein Content-Urteil) – auch nicht
        #    über mehrere Läufe hinweg.
        record([{"slug": "2026-09-15-gut", "ready": False,
                 "reason": "Gate-Ausnahme: hugo timeout"}], state_path, posts,
               run_key="run:1")
        record([{"slug": "2026-09-15-gut", "ready": False,
                 "reason": "Gate-Ausnahme: hugo timeout"}], state_path, posts,
               run_key="run:2")
        if "2026-09-15-gut" in load_state(state_path):
            fehler.append("Werkzeug-/API-Ausnahmen dürfen nicht aufzählen")
        text_gut = (posts / "2026-09-15-gut" / "index.md").read_text("utf-8")
        if "reserve_blocked" in text_gut:
            fehler.append("wegen Werkzeugfehler darf niemand ausgemustert werden")

    # 6) Lauf-Kennung: GitHub-Actions-Läufe sind über GITHUB_RUN_ID getrennt,
    #    außerhalb von Actions zählt der Kalendertag (Handlauf).
    alt = os.environ.get("GITHUB_RUN_ID")
    try:
        os.environ["GITHUB_RUN_ID"] = "987654"
        if lauf_kennung() != "run:987654":
            fehler.append(f"GITHUB_RUN_ID nicht übernommen: {lauf_kennung()}")
        os.environ.pop("GITHUB_RUN_ID", None)
        if not lauf_kennung().startswith("lokal:"):
            fehler.append(f"Ohne Actions muss der Kalendertag zählen: "
                          f"{lauf_kennung()}")
    finally:
        if alt is None:
            os.environ.pop("GITHUB_RUN_ID", None)
        else:
            os.environ["GITHUB_RUN_ID"] = alt

    # 7) Signatur: Zahlen/Slugs dürfen die Ursache nicht verschleiern.
    a = signatur("Länge 1.134 Wörter < 1.200 (Struktur 0.70)")
    b = signatur("Länge 1.141 Wörter < 1.200 (Struktur 0.70)")
    if a != b:
        fehler.append(f"gleiche Ursache muss gleiche Signatur haben: {a} != {b}")
    if signatur("Titel fehlt") == signatur("Cover fehlt"):
        fehler.append("verschiedene Ursachen brauchen verschiedene Signaturen")

    if fehler:
        for f in fehler:
            print(f"   ✗ {f}")
        return 2
    print("✅ Selbsttest reserve_quarantine: Zähler je LAUF (#349), Schwelle, "
          "Idempotenz, Heilung, Werkzeugfehler-Ausnahme, Lauf-Kennung, "
          "Signatur-Bildung.")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Reserve-Kandidaten nach wiederholtem Fund ausmustern")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--state", default=str(STATE))
    args = ap.parse_args()
    if args.selftest:
        return run_selftest()
    return status(Path(args.state), args.json)


if __name__ == "__main__":
    raise SystemExit(main())
