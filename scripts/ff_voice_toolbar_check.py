#!/usr/bin/env python3
"""ff_voice_toolbar_check.py — Infrastruktur-Wache der Lesehilfen.

Prüft, dass Layout, Engine, Styling, Tests und Workflow der Vorlese-
Funktion zusammenpassen — und dass vom alten TTS-Modell NICHTS übrig
geblieben ist.

Geprüft werden:
  1. PARTIAL    — Rollen, aria-Attribute und alle IDs, die die Engine
                  erwartet (sonst startet der Reader stillschweigend nicht).
  2. EINBINDUNG — Blogbeiträge, Ratgeberseiten und Pillar-Seiten.
  3. STYLING    — jede Klasse, die die Engine setzt, ist gestaltet
                  (Slot-Höhe, Mini-Player, Fortschritt, Dialog).
  4. ENGINE     — First-Party, kein Tracking, keine Fremd-CDNs, kein
                  Netzwerkaufruf zur Laufzeit, keine Debug-Ausgaben.
  5. RÜCKBAU    — keine Reste des entfernten TTS-Modells im Repository.
  6. WORKFLOW   — das Gate führt alle neuen Suiten aus.

Aufruf: python3 scripts/ff_voice_toolbar_check.py
"""

from __future__ import annotations

import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

PARTIAL = os.path.join(ROOT, "layouts", "_partials", "ff_voice_toolbar.html")
ENGINE = os.path.join(ROOT, "static", "premium", "ff-voice.js")
CSS = os.path.join(ROOT, "assets", "css", "extended", "ff-voice.css")
GATE = os.path.join(ROOT, ".github", "workflows", "lesehilfen-gate.yml")
DEPLOY = os.path.join(ROOT, ".github", "workflows", "deploy.yml")
QA_PKG = os.path.join(ROOT, "tools", "ff-voice-qa", "package.json")

LAYOUTS = [
    os.path.join(ROOT, "layouts", "single.html"),
    os.path.join(ROOT, "layouts", "_default", "single.html"),
    os.path.join(ROOT, "layouts", "pillar", "single.html"),
]

REQUIRED_IDS = [
    "ff-voice-slot", "ff-voice-bar", "ff-voice-play", "ff-voice-play-label",
    "ff-voice-prev", "ff-voice-next", "ff-voice-stop", "ff-voice-summary",
    "ff-voice-summary-label", "ff-voice-status", "ff-voice-remaining",
    "ff-voice-progress", "ff-voice-config",
]

REQUIRED_CSS_CLASSES = [
    "ff-voice-slot", "ff-voice-bar", "ff-voice-btn", "ff-voice-progress",
    "ff-voice-bar--floating", "ff-voice-active", "ff-voice-dialog",
    "ff-voice-figures", "ff-voice-toc",
]

REMOVED_MARKERS = [
    "ff-reader", "reader_toolbar", "generate_reader_audio", "reader_tts_backends",
    "reader_functional_test", "reader_qa_lib", "reader_tts", "reader_prosody_parity",
    "reader_toolbar_check", "reader_blocks_dump", "reader_voice_ab",
    "reader_engine_check", "reader_male_voice_highend_test", "reader_parity_probe",
    "reader_playback_function_test", "reader_v7_function_test",
    "reader_structure_loudness_test", "reader_table_progress_test",
    "summary_engine_check", "tools/reader-qa",
]

REMOVED_FILES = [
    "static/premium/ff-reader.js",
    "assets/css/extended/ff-reader.css",
    "layouts/_partials/reader_toolbar.html",
    "scripts/generate_reader_audio.py",
    "scripts/reader_tts_backends.py",
    "scripts/reader_prosody_parity_check.py",
    "scripts/reader_toolbar_check.py",
    "scripts/reader_blocks_dump.py",
    "scripts/reader_voice_ab.py",
    "scripts/reader_functional_test.mjs",
    "scripts/reader_qa_lib.mjs",
    "scripts/reader_structure_loudness_test.mjs",
    "scripts/reader_table_progress_test.mjs",
    "scripts/reader_engine_check.js",
    "scripts/reader_male_voice_highend_test.js",
    "scripts/reader_parity_probe.js",
    "scripts/reader_playback_function_test.js",
    "scripts/reader_v7_function_test.js",
    "scripts/summary_engine_check.js",
    "tools/reader-qa/package.json",
]

SCAN_DIRS = ["layouts", "static", "scripts", "assets", "content", "tools", ".github", "docs", "patches"]
SCAN_SUFFIXES = (".html", ".js", ".mjs", ".py", ".css", ".yml", ".yaml", ".toml", ".md", ".json", ".sh")


def read(path):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read()
    except Exception:
        return ""


def main() -> int:
    results = []

    def check(name, cond, detail=""):
        results.append((name, bool(cond), detail))

    # ---------- 1 · Partial ----------
    partial = read(PARTIAL)
    check("Partial vorhanden", bool(partial), PARTIAL)
    check("Partial: Region mit aria-label", 'role="region"' in partial and "aria-label=" in partial)
    check("Partial: Status als Live-Region",
          'role="status"' in partial and 'aria-live="polite"' in partial)
    check("Partial: Kurzfassung als Dialog", 'aria-haspopup="dialog"' in partial)
    check("Partial: Konfigurationsblock", 'id="ff-voice-config"' in partial)
    check("Partial: Engine wird nachgeladen", 'premium/ff-voice.js' in partial)
    check("Partial: Script mit defer (kein Render-Blocker)", "defer" in partial)
    check("Partial: Abschaltbar pro Seite", "hideReaderToolbar" in partial)
    for ident in REQUIRED_IDS:
        check("Partial: id %s" % ident, ('id="%s"' % ident) in partial)
    for sec in ("posts", "pillar", "ratgeber"):
        check("Partial: greift bei Sektion %s" % sec, ('"%s"' % sec) in partial)

    # ---------- 2 · Einbindung ----------
    for layout in LAYOUTS:
        text = read(layout)
        name = os.path.relpath(layout, ROOT)
        check("%s bindet die Lesehilfen ein" % name, 'ff_voice_toolbar.html' in text)

    # ---------- 3 · Styling ----------
    css = read(CSS)
    check("Stylesheet vorhanden", bool(css), CSS)
    for cls in REQUIRED_CSS_CLASSES:
        check("CSS: Klasse .%s gestaltet" % cls, ("." + cls) in css)
    check("CSS: Slot reserviert Höhe (kein CLS)", "min-height" in css)
    check("CSS: Mini-Player fixiert", "position: fixed" in css)
    check("CSS: Darkmode berücksichtigt", 'data-theme="dark"' in css)
    check("CSS: prefers-reduced-motion berücksichtigt", "prefers-reduced-motion" in css)
    check("CSS: Fokus sichtbar", ":focus-visible" in css)
    check("CSS: Druckausgabe ohne Toolbar", "@media print" in css)

    # ---------- 4 · Engine ----------
    engine = read(ENGINE)
    check("Engine vorhanden", bool(engine), ENGINE)
    check("Engine: Version geführt", "VOICE_VERSION" in engine)
    check("Engine: keine Debug-Ausgaben", "console.log" not in engine)
    check("Engine: keine Tracking-Aufrufe",
          not re.search(r"\b(gtag|ga\(|_paq|fbq|dataLayer)\b", engine))
    check("Engine: kein Fremd-CDN",
          not re.search(r"https?://(?!www\.w3\.org)", engine))
    check("Engine: keine Laufzeit-Netzaufrufe",
          not re.search(r"\b(fetch\(|XMLHttpRequest|navigator\.sendBeacon|importScripts)\b", engine))
    check("Engine: Tonspur-Vertrag dokumentiert", "ff-voice-track-config" in engine)
    check("Engine: zwei Tonpfade", "track" in engine and "speech" in engine)
    check("Engine: keine Stimmenwahl in der UI", "ff-voice-select" not in engine)
    check("Engine: Wiedereinstieg gemerkt", "localStorage" in engine)
    check("Engine: Abschnittsnavigation", "jumpBlock" in engine)
    check("Engine: Live-Markierung", "ff-voice-active" in engine)

    # ---------- 5 · Rückbau ----------
    for rel in REMOVED_FILES:
        check("Alt entfernt: %s" % rel, not os.path.exists(os.path.join(ROOT, rel)))
    leftovers = []
    for folder in SCAN_DIRS:
        abs_folder = os.path.join(ROOT, folder)
        if not os.path.isdir(abs_folder):
            continue
        for dirpath, dirnames, filenames in os.walk(abs_folder):
            dirnames[:] = [d for d in dirnames if d not in ("node_modules", ".git")]
            for filename in filenames:
                if not filename.endswith(SCAN_SUFFIXES):
                    continue
                path = os.path.join(dirpath, filename)
                rel = os.path.relpath(path, ROOT)
                if rel.startswith("docs/") and "FF-VOICE" in rel:
                    continue
                # Diese Wache listet die Alt-Dateien absichtsvoll auf –
                # sie ist die Dokumentation des Rückbaus, nicht sein Rest.
                if rel == os.path.relpath(__file__, ROOT):
                    continue
                text = read(path)
                if not text:
                    continue
                for marker in REMOVED_MARKERS:
                    if marker in text:
                        leftovers.append("%s (%s)" % (rel, marker))
                        break
    check("Keine Referenzen auf das alte TTS-Modell", not leftovers,
          ", ".join(leftovers[:5]))

    # ---------- 6 · Workflow & Abhängigkeiten ----------
    gate = read(GATE)
    check("Gate vorhanden", bool(gate), GATE)
    for suite in ("ff_voice_functional_test.mjs", "ff_voice_voice_test.js",
                  "ff_voice_parity_check.py", "ff_voice_toolbar_check.py",
                  "ff_voice_audio.py", "ff_voice_backends.py"):
        check("Gate führt %s aus" % suite, suite in gate)
    check("Gate installiert jsdom", "ff-voice-qa" in gate)
    check("Gate prüft die Engine-Syntax", "node --check" in gate)

    deploy = read(DEPLOY)
    check("Deploy: keine alten Audio-Schritte", "generate_reader_audio" not in deploy)
    check("Deploy: erzeugt die Tonspur neu", "ff_voice_audio.py" in deploy)
    check("Deploy: blockiert nie wegen der Tonspur",
          "|| true" in deploy or "|| echo" in deploy)

    qa = read(QA_PKG)
    if qa:
        try:
            pkg = json.loads(qa)
            check("QA-Paket: jsdom als Abhängigkeit",
                  "jsdom" in (pkg.get("devDependencies") or {}))
        except Exception:
            check("QA-Paket lesbar", False, "kein gültiges JSON")
    else:
        check("QA-Paket vorhanden", False, QA_PKG)

    # ---------- Ergebnis ----------
    failed = [(n, d) for n, ok, d in results if not ok]
    for name, detail in failed:
        print("  ✗ %s%s" % (name, (" — " + detail) if detail else ""))
    total = len(results)
    print("FF-VOICE-TOOLBAR – Wache: %d/%d bestanden" % (total - len(failed), total))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
