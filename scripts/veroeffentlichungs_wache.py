#!/usr/bin/env python3
# ============================================================
#  VEROEFFENTLICHUNGS-WACHE – der Nachlauf für Automatik-Commits
#  ------------------------------------------------------------
#  BEFUND 06.11.2026 (nach #1097): Die Automatik (Reserve, GSC-Heilung,
#  Suchradar, Scorecard) schreibt mit `GITHUB_TOKEN` direkt auf `main`.
#  Solche Commits lösen KEINE Pull-Request-Prüfung aus. Deshalb konnte
#  `main` rot werden, ohne dass es jemand merkte:
#    · Der Ökostrom-Artikel ging ohne `kurzantwort` live (Metadaten-Wache
#      M4) – sichtbar wurde es erst Tage später, als ein fremder PR die
#      E2E-Suite über den ganzen Baum laufen ließ.
#    · Das Fachprüfungs-Register war veraltet, die Befund-Akte wies 11
#      Befunde aus, während der Ledger 19 kannte.
#    · Ein Satz aus dem Artikel („… lückenlose Versorgung garantiert")
#      machte den Artikel auf Reddit in JEDEM Winkel unsendbar.
#
#  Diese Wache prüft genau diese vier Dinge NACH der Veröffentlichung und
#  öffnet bei einem NEUEN Befund ein Issue, statt still zu committen.
#  Sie heilt nicht selbst: Heilung braucht einen Besitzer (Redaktion oder
#  ein benannter Heiler wie `--verlinkung --heilen`).
#
#  DREI ENTSCHEIDUNGEN, die den Unterschied machen
#    1. DEDUPE: Ein Befund, der schon gemeldet ist, erzeugt kein zweites
#       Issue. Der Fingerabdruck der Befundmenge liegt in
#       `data/veroeffentlichung/wache_state.json`.
#    2. TRENNUNG: Ein Werkzeugfehler (fehlende Bibliothek, kaputte Wache)
#       ist KEIN Inhaltsbefund und wird als solcher gemeldet – sonst
#       diskreditiert ein Umgebungsproblem die echten Befunde.
#    3. KEIN BLOCKIEREN DER AUSLIEFERUNG: Exitcode 1 meldet Befunde, aber
#       die Wache steht nicht im Deploy-Pfad. Ein Artikel darf wegen einer
#       fehlenden Kurzantwort nicht offline gehen (C34, #925).
#
#  NUTZUNG
#    python3 scripts/veroeffentlichungs_wache.py --wache
#    python3 scripts/veroeffentlichungs_wache.py --wache --json --schreiben
#    python3 scripts/veroeffentlichungs_wache.py --selftest
#
#  EXIT  0 = grün · 1 = Befund(e) · 2 = Werkzeugfehler (fail-closed)
# ============================================================
from __future__ import annotations

import argparse
import contextlib
import glob
import hashlib
import io
import json
import os
import sys
from datetime import datetime, timezone

SCRIPTS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(SCRIPTS)
sys.path.insert(0, SCRIPTS)
sys.path.insert(0, ROOT)

STATE_REL = os.path.join("data", "veroeffentlichung", "wache_state.json")
BEFUND_REL = os.path.join("data", "veroeffentlichung", "wache_befund.json")
BEREICHE = ("frontmatter", "metadaten", "register", "akte", "winkel")


# ------------------------------------------------------------- Prüfbereiche
def pruefe_frontmatter(root: str) -> tuple[list[dict], list[dict]]:
    """Frontmatter-Gerüst: doppelte Schlüssel und unlesbare Blöcke (Blocker).

    AM 06.11.2026 AKUT: Der Ökostrom-Artikel trug `kurzantwort` zweimal – die
    Reserve-Automatik hatte den Block neu geschrieben, der alte Schlüssel
    blieb stehen. Hugo bricht daran den Bau ab („mapping key already
    defined"); ein YAML-Parser nimmt still den letzten Wert. Kein PR hat es
    gesehen, weil der Commit von der Automatik kam.
    """
    import frontmatter_wache as fw
    befunde: list[dict] = []
    blocker, _anzahl, _tief = fw.run([os.path.join(root, "content")])
    for b in blocker:
        if b.get("schwere") != fw.BLOCKER:
            continue
        befunde.append({"bereich": "frontmatter",
                        "text": f"{b.get('regel')}: {b.get('meldung')} "
                                f"({b.get('pfad')}:{b.get('zeile')})",
                        "datei": str(b.get("pfad") or "")})
    return befunde, []


def pruefe_metadaten(root: str) -> tuple[list[dict], list[dict]]:
    """Metadaten-Wache: Snippet-SSOT, lastmod und die Pflichtfelder (M4)."""
    import metadaten_wache
    befunde, werkzeug = [], []
    findings, geprueft, _ = metadaten_wache.run(root=root)
    for f in findings:
        text = f"{f.get('rule', '?')}: {f.get('msg', '')} – {f.get('file', '')}"
        ziel = befunde
        # Die Wache meldet fehlende Pillow-Logik selbst als M6-Befund;
        # das ist ein Umgebungsthema, kein Textbefund.
        if "nicht ladbar" in str(f.get("msg", "")):
            ziel = werkzeug
        ziel.append({"bereich": "metadaten", "text": text, "datei": f.get("file", "")})
    return befunde, werkzeug


def pruefe_register(root: str) -> tuple[list[dict], list[dict]]:
    """Fachprüfungs-Register: Die Auskunft muss zum Bestand passen."""
    import fachpruefung_register as fpr
    puffer = io.StringIO()
    with contextlib.redirect_stdout(puffer):
        rc = fpr.main(["--check"])
    if rc == 0:
        return [], []
    meldung = puffer.getvalue().strip().splitlines()[-1:] or ["Register veraltet"]
    return [{"bereich": "register", "text": meldung[0], "datei":
             os.path.join("data", "fachpruefung_register.yaml")}], []


def pruefe_akte(root: str) -> tuple[list[dict], list[dict]]:
    """Befund-Akte: Arbeitsliste und Ledger müssen denselben Stand zeigen."""
    import faktenfrische_befund_akte as akte
    stand = akte.wache()
    if not stand.get("veraltet"):
        return [], []
    return [{"bereich": "akte",
             "text": (f"BEFUND-AKTE.md oder Zustand stimmt nicht mit dem Ledger überein "
                      f"(Akte: {stand.get('akte_offen')} offen, Ledger: "
                      f"{stand.get('offen')}) – `python3 scripts/faktenfrische_"
                      f"befund_akte.py --schreiben`"),
             "datei": "BEFUND-AKTE.md"}], []


def pruefe_winkel(root: str, meta: dict | None = None,
                  channels: dict | None = None) -> tuple[list[dict], list[dict]]:
    """Kanaltreue (#716): Jeder Kanal braucht je Artikel einen sendbaren Winkel.

    Ohne diese Prüfung fällt ein Kanal still aus – ein blockierter Slot ist
    kein Fehler, den irgendwo eine rote Ampel zeigt.
    """
    import social_channels as sch
    import social_copywriter as copy
    import social_gate as gate

    def _fehler(fehler: Exception) -> list[dict]:
        return [{"bereich": "winkel", "text": f"Kanaltreue nicht messbar: {fehler}",
                 "datei": ""}]

    try:
        cfg = sch.load_config()
        meta = meta if meta is not None else sch.meta_of(cfg)
        channels = channels if channels is not None else sch.channel_map(cfg)
        pool = copy.article_pool(base_url=str((meta or {}).get("base_url") or copy.DEFAULT_BASE))
    except Exception as fehler:                      # noqa: BLE001
        return [], _fehler(fehler)

    befunde: list[dict] = []
    for cid, ch in channels.items():
        if not ch.get("enabled", True):
            continue
        unsendbar: list[str] = []
        for art in pool:
            frei = False
            for angle in (ch.get("angles") or ["nutzen"]):
                pkg = copy.compose(dict(art), cid, ch, angle, meta, use_llm=False)
                # Bildkanäle (Instagram, Pinterest) verlangen ein Medium (L10).
                # Im echten Lauf hängt `social_images` es an; hier wird es
                # nachgestellt, sonst meldet die Wache 78 falsche Befunde.
                quelle = os.path.join(root, "static", art.get("cover") or "")
                if os.path.isfile(quelle):
                    pkg["media_path"] = quelle
                    pkg["media_url"] = (f"{str((meta or {}).get('base_url') or '').rstrip('/')}"
                                        f"/{art.get('cover')}")
                ok, _verstoesse, _m = gate.check(pkg, ch, meta, history=[])
                if ok:
                    frei = True
                    break
            if not frei:
                unsendbar.append(art.get("slug") or "?")
        if unsendbar:
            befunde.append({"bereich": "winkel",
                            "text": (f"{cid}: {len(unsendbar)} Artikel in keinem "
                                     f"Winkel sendbar – {', '.join(unsendbar[:5])}"),
                            "datei": ""})
    return befunde, []


PRUEFUNGEN = {
    "frontmatter": pruefe_frontmatter,
    "metadaten": pruefe_metadaten,
    "register": pruefe_register,
    "akte": pruefe_akte,
    "winkel": pruefe_winkel,
}


# ------------------------------------------------------------------ Lauf
def _fingerabdruck(befunde: list[dict]) -> str:
    roh = "\n".join(sorted(f"{b.get('bereich')}|{b.get('text')}" for b in befunde))
    return hashlib.sha256(roh.encode("utf-8")).hexdigest()[:16] if roh else ""


def _state_lesen(root: str) -> dict:
    try:
        with open(os.path.join(root, STATE_REL), encoding="utf-8") as fh:
            daten = json.load(fh)
        return daten if isinstance(daten, dict) else {}
    except (OSError, ValueError):
        return {}


def pruefe(root: str = ROOT, bereiche: tuple[str, ...] = BEREICHE) -> dict:
    """Führt die Prüfungen aus und liefert den Bericht (ohne Dateizugriff)."""
    befunde: list[dict] = []
    werkzeug: list[dict] = []
    gelaufen: list[str] = []
    for name in bereiche:
        funktion = PRUEFUNGEN.get(name)
        if funktion is None:
            werkzeug.append({"bereich": name, "text": "unbekannter Prüfbereich",
                             "datei": ""})
            continue
        try:
            b, w = funktion(root)
        except Exception as fehler:                  # noqa: BLE001 – fail-closed
            w = [{"bereich": name,
                  "text": f"Wache nicht ausführbar: {type(fehler).__name__}: {fehler}",
                  "datei": ""}]
            b = []
        befunde += b
        werkzeug += w
        gelaufen.append(name)
    fp = _fingerabdruck(befunde)
    alt = _state_lesen(root)
    neu = bool(befunde) and fp != str(alt.get("fingerabdruck") or "")
    return {
        "stand": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "geprueft": gelaufen,
        "gruen": not befunde and not werkzeug,
        "befunde": befunde,
        "werkzeugfehler": werkzeug,
        "fingerabdruck": fp,
        "neu": neu,
        "bisher_gemeldet": str(alt.get("fingerabdruck") or ""),
    }


def _schreiben(bericht: dict, root: str = ROOT) -> None:
    for rel, inhalt in ((BEFUND_REL, bericht),
                        (STATE_REL, {"fingerabdruck": bericht["fingerabdruck"],
                                     "stand": bericht["stand"],
                                     "anzahl": len(bericht["befunde"])})):
        pfad = os.path.join(root, rel)
        os.makedirs(os.path.dirname(pfad), exist_ok=True)
        with open(pfad, "w", encoding="utf-8") as fh:
            json.dump(inhalt, fh, ensure_ascii=False, indent=2, sort_keys=True)
            fh.write("\n")


LABEL = "nachlauf-wache"


def _gh(args: list[str]) -> str:
    """Ruft `gh` auf (GitHub-CLI ist im Runner vorhanden und authentifiziert)."""
    import subprocess
    ergebnis = subprocess.run(["gh", *args], capture_output=True, text=True)
    if ergebnis.returncode != 0:
        raise RuntimeError((ergebnis.stderr or ergebnis.stdout or "gh-Fehler").strip())
    return ergebnis.stdout


def _issue_koerper(bericht: dict) -> str:
    zeilen = [
        "Die Nachlauf-Wache hat auf `main` Befunde gefunden, die kein "
        "Pull-Request geprüft hat (Automatik-Commits lösen keine PR-Prüfung aus).",
        "",
        f"**Stand:** {bericht['stand']} · **Fingerabdruck:** "
        f"`{bericht['fingerabdruck']}`",
        "",
        "## Befunde",
    ]
    for b in bericht["befunde"]:
        zeilen.append(f"- **[{b['bereich']}]** {b['text']}")
    if bericht["werkzeugfehler"]:
        zeilen += ["", "## Werkzeugfehler (kein Inhaltsbefund)"]
        for w in bericht["werkzeugfehler"]:
            zeilen.append(f"- **[{w['bereich']}]** {w['text']}")
    zeilen += ["", f"Reproduzieren: `python3 scripts/veroeffentlichungs_wache.py "
                   f"--wache`", "",
               "_Kein Befund dieser Wache blockiert die Auslieferung (C34). Sie "
               "meldet, sie entscheidet nicht._"]
    return "\n".join(zeilen)


def issue_oeffnen(bericht: dict, runner=None) -> str | None:
    """Öffnet EIN Issue je Befundmenge – oder keins, wenn schon eins offen ist.

    Dedupe über den Fingerabdruck im Titel: derselbe Befund erzeugt kein
    zweites Issue, ein veränderter Befund schon (dann ist er neu).
    Rückgabe: Titel des geöffneten Issues oder None.
    """
    fp = str(bericht.get("fingerabdruck") or "")
    if not bericht.get("befunde") or not fp:
        return None
    runner = runner or _gh
    titel = f"🩺 Nachlauf-Wache: Befund auf main ({fp})"
    vorhanden = runner(["issue", "list", "--label", LABEL, "--state", "open",
                        "--search", fp, "--json", "number", "--jq", "length"])
    if str(vorhanden).strip() not in ("", "0"):
        return None
    runner(["issue", "create", "--title", titel, "--label", LABEL,
            "--body", _issue_koerper(bericht)])
    return titel


def _text(bericht: dict) -> str:
    zeilen = []
    if bericht["gruen"]:
        zeilen.append("✅ Nachlauf-Wache grün: Frontmatter, Metadaten, Register, "
                      "Akte und Kanaltreue stimmen.")
        return "\n".join(zeilen)
    if bericht["befunde"]:
        zeilen.append(f"🛑 Nachlauf-Wache: {len(bericht['befunde'])} Befund(e) auf "
                      f"dem veröffentlichten Stand")
        for b in bericht["befunde"]:
            zeilen.append(f"   · [{b['bereich']}] {b['text']}")
    if bericht["werkzeugfehler"]:
        zeilen.append(f"⚠ {len(bericht['werkzeugfehler'])} Werkzeugfehler "
                      "(kein Inhaltsbefund):")
        for w in bericht["werkzeugfehler"]:
            zeilen.append(f"   · [{w['bereich']}] {w['text']}")
    if bericht["befunde"]:
        zeilen.append("→ " + ("NEU: Issue öffnen." if bericht["neu"]
                              else "bereits gemeldet – kein zweites Issue."))
    return "\n".join(zeilen)


# --------------------------------------------------------------- Selbsttest
COVER = "images/covers/probe.jpg"


def _artikel(kurzantwort: str | None) -> str:
    """Veröffentlichter Artikel – mit allem außer (je nach Fall) der Kurzantwort."""
    kopf = ('---\ntitle: "Probe"\n'
            'description: "Diese Beschreibung ist absichtlich lang genug für '
            'das Snippet-Fenster des Hauses und beschreibt den Testfall."\n'
            'date: 2026-11-06T00:00:00Z\ndraft: false\n')
    if kurzantwort:
        kopf += f'kurzantwort: "{kurzantwort}"\n'
    return (kopf +
            'cover:\n  image: "images/covers/probe.jpg"\n  alt: "Probe-Bild"\n'
            'quellen:\n  - titel: "Bundesnetzagentur"\n'
            '    url: "https://www.bundesnetzagentur.de/x"\n'
            'faktencheck: 2026-11-06\n---\n\nText.\n')


def _fixture(root: str) -> None:
    """Kleiner Bestand: ein veröffentlichter Artikel OHNE Kurzantwort."""
    pfad = os.path.join(root, "content", "posts", "2026-11-06-probe")
    os.makedirs(pfad, exist_ok=True)
    cover = os.path.join(root, "static", COVER)
    os.makedirs(os.path.dirname(cover), exist_ok=True)
    with open(cover, "wb") as fh:          # 1×1-Pixel, nur Existenz zählt
        fh.write(bytes.fromhex("89504e470d0a1a0a"))
    with open(os.path.join(pfad, "index.md"), "w", encoding="utf-8") as fh:
        fh.write(_artikel(None))


def selbsttest() -> int:
    """Prüft Befund, Dedupe, Werkzeugtrennung und Schreibfreiheit (C15)."""
    import tempfile
    faelle, rot = 0, []

    def fest(name: str, bedingung: bool) -> None:
        nonlocal faelle
        faelle += 1
        if not bedingung:
            rot.append(name)

    with tempfile.TemporaryDirectory() as tmp:
        _fixture(tmp)
        bericht = pruefe(tmp, bereiche=("metadaten",))
        fest("K1 Befund erkannt", not bericht["gruen"] and bericht["befunde"])
        fest("K2 Bereich", all(b["bereich"] == "metadaten" for b in bericht["befunde"]))
        fest("K3 Fingerabdruck", len(bericht["fingerabdruck"]) == 16)
        fest("K4 neu beim ersten Mal", bericht["neu"] is True)

        # Dedupe: gleicher Befund → kein zweites Issue
        _schreiben(bericht, root=tmp)
        zweiter = pruefe(tmp, bereiche=("metadaten",))
        fest("K5 Dedupe", zweiter["neu"] is False
               and zweiter["fingerabdruck"] == bericht["fingerabdruck"])

        # Nach der Heilung: grün, und der Zustand bleibt lesbar
        pfad = os.path.join(tmp, "content", "posts", "2026-11-06-probe", "index.md")
        with open(pfad, "w", encoding="utf-8") as fh:
            fh.write(_artikel("Ja, das ist der Fall."))
        dritter = pruefe(tmp, bereiche=("metadaten",))
        fest("K6 nach Heilung grün", dritter["gruen"] and dritter["neu"] is False)

        # Werkzeugfehler werden getrennt gemeldet, nicht als Inhaltsbefund
        alt = PRUEFUNGEN.get("metadaten")
        try:
            def _kaputt(_root: str):
                raise RuntimeError("Absicht")
            PRUEFUNGEN["metadaten"] = _kaputt
            vierter = pruefe(tmp, bereiche=("metadaten",))
        finally:
            if alt is not None:
                PRUEFUNGEN["metadaten"] = alt
        fest("K7 Werkzeugfehler getrennt", vierter["werkzeugfehler"]
               and not vierter["befunde"] and not vierter["gruen"])

        # C15: Der Selbsttest schreibt nie in den echten Baum
        echt = os.path.join(ROOT, STATE_REL)
        fest("K8 schreibfrei", not os.path.exists(echt)
               or os.path.getmtime(echt) <= os.path.getmtime(__file__))

    if rot:
        print("🛑 VEROEFFENTLICHUNGS-WACHE SELBSTTEST – Befunde:")
        for name in rot:
            print(f"   ✗ {name}")
        return 1
    print(f"✅ VEROEFFENTLICHUNGS-WACHE SELBSTTEST: {faelle} Fälle grün "
          "(Befund, Dedupe, Heilung, Werkzeugtrennung, schreibfrei).")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        description="Nachlauf-Wache für Automatik-Commits (Metadaten, Register, "
                    "Befund-Akte, Kanaltreue).")
    p.add_argument("--wache", action="store_true", help="prüfen, Exit 1 bei Befund")
    p.add_argument("--json", action="store_true", help="Bericht als JSON")
    p.add_argument("--schreiben", action="store_true",
                   help="Bericht und Zustand (für die Dedupe) schreiben")
    p.add_argument("--nur", default="", help="nur diese Bereiche (Komma-Liste)")
    p.add_argument("--root", default=ROOT, help=argparse.SUPPRESS)
    p.add_argument("--issue", action="store_true",
                   help="bei NEUEM Befund ein GitHub-Issue öffnen (Dedupe im Skript)")
    p.add_argument("--selftest", action="store_true")
    args = p.parse_args(argv)

    if args.selftest:
        return selbsttest()

    bereiche = tuple(b.strip() for b in args.nur.split(",") if b.strip()) or BEREICHE
    bericht = pruefe(args.root, bereiche=bereiche)
    if args.schreiben:
        _schreiben(bericht, root=args.root)
    if args.json:
        print(json.dumps(bericht, ensure_ascii=False, indent=2, sort_keys=True))
    else:
        print(_text(bericht))
    if args.issue:
        try:
            titel = issue_oeffnen(bericht)
        except Exception as fehler:                  # noqa: BLE001
            print(f"::warning::Nachlauf-Wache: Issue nicht geöffnet ({fehler})")
        else:
            if titel:
                print(f"::notice::Nachlauf-Wache: Issue geöffnet – {titel}")
            elif bericht["befunde"]:
                print("::notice::Nachlauf-Wache: Befund bereits gemeldet – kein "
                      "zweites Issue.")
    if bericht["werkzeugfehler"]:
        return 2
    return 0 if not bericht["befunde"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
