#!/usr/bin/env python3
# ============================================================
#  READER-TOOLBAR-CHECK – Dauerhafte Barrierefreiheits-Wache
#  (Vorlesen mit männlicher Stimme, DE & EN, Tabellen & Übersichten)
# ============================================================

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

def check_toolbar_partial():
    path = ROOT / "layouts" / "_partials" / "reader_toolbar.html"
    if not path.is_file():
        return False, "layouts/_partials/reader_toolbar.html fehlt"
    content = path.read_text(encoding="utf-8")
    required_ids = ["ff-reader-toolbar", "ff-listen-btn", "ff-listen-stop", "ff-summary-btn", "ff-reader-status", "ff-reader-progress-bar", "ff-reader-config"]
    for rid in required_ids:
        if rid not in content:
            return False, f"ID '{rid}' fehlt in reader_toolbar.html"
    return True, "reader_toolbar.html vollständig"

def check_js_engine():
    path = ROOT / "static" / "premium" / "ff-reader.js"
    if not path.is_file():
        return False, "static/premium/ff-reader.js fehlt"
    content = path.read_text(encoding="utf-8")
    
    # Prüfe männliche Stimme
    male_tokens = ["pickMaleVoice", "stefan", "conrad", "florian", "david", "george", "guy", "mark"]
    for token in male_tokens:
        if token not in content:
            return False, f"Männliche Stimmenlogik unvollständig (Token '{token}' fehlt)"
            
    # Prüfe Zweisprachigkeit (DE & EN)
    if "detectArticleLanguage" not in content or "I18N" not in content:
        return False, "Automatische Mehrsprachigkeit (DE/EN) fehlt in ff-reader.js"
        
    # Prüfe Tabellen- und Übersichten-Barrierefreiheit
    table_tokens = ["extractTableSpeechBlocks", "tableIntro", "tableRow", "ff-reader-active"]
    for token in table_tokens:
        if token not in content:
            return False, f"Tabellen-Sprachausgabe unvollständig (Token '{token}' fehlt)"
            
    # Prüfe Lautschrift-Normalisierung
    if "speechNormalize" not in content:
        return False, "Lautschrift- & Einheiten-Normalisierung fehlt in ff-reader.js"
        
    return True, "ff-reader.js (Männliche Stimme, DE/EN, Tabellen-Barrierefreiheit) vollständig"

def check_css():
    path = ROOT / "assets" / "css" / "extended" / "ff-reader.css"
    if not path.is_file():
        return False, "assets/css/extended/ff-reader.css fehlt"
    content = path.read_text(encoding="utf-8")
    required_classes = [".ff-reader-toolbar", ".ff-reader-btn--listen", ".ff-reader-btn--summary", ".ff-reader-active", "tr.ff-reader-active"]
    for cls in required_classes:
        if cls not in content:
            return False, f"CSS-Klasse '{cls}' fehlt in ff-reader.css"
    return True, "ff-reader.css (Styling & A11y-Highlighting) vollständig"

def check_layouts():
    layouts = [
        ROOT / "layouts" / "_default" / "single.html",
        ROOT / "layouts" / "single.html",
        ROOT / "layouts" / "pillar" / "single.html",
    ]
    for lp in layouts:
        if not lp.is_file():
            return False, f"Layout {lp.name} fehlt"
        content = lp.read_text(encoding="utf-8")
        if 'partial "reader_toolbar.html"' not in content:
            return False, f"reader_toolbar.html ist nicht in {lp.name} eingebunden"
    return True, "Alle Single- und Ratgeber-Layouts binden reader_toolbar.html ein"

def check_archetypes():
    archs = [
        ROOT / "archetypes" / "default.md",
        ROOT / "archetypes" / "posts.md",
        ROOT / "archetypes" / "pillar.md",
    ]
    for ap in archs:
        if not ap.is_file():
            return False, f"Archetype {ap.name} fehlt"
    return True, "Alle Archetypes vorhanden (Zukünftige Artikel gesichert)"

def main():
    checks = [
        ("Reader-Toolbar Layout", check_toolbar_partial),
        ("JS Speech-Engine (Männliche Stimme, DE/EN, Tabellen)", check_js_engine),
        ("CSS & Highlighting", check_css),
        ("Layout-Einbindung (Posts & Pillar)", check_layouts),
        ("Archetypes (Zukunftssicherheit)", check_archetypes),
    ]
    all_ok = True
    print("=== Prüfung: Reader-Toolbar & Barrierefreiheit ===")
    for name, func in checks:
        ok, msg = func()
        status = "✅" if ok else "❌"
        print(f"{status} {name}: {msg}")
        if not ok:
            all_ok = False
            
    if not all_ok:
        print("\n❌ Reader-Toolbar-Prüfung fehlgeschlagen!")
        sys.exit(1)
        
    print("\n🎉 Alle Prüfungen erfolgreich: Vorlesen (männliche Stimme, DE & EN, Tabellen & Übersichten) dauerhaft gesichert.")
    sys.exit(0)

if __name__ == "__main__":
    main()
