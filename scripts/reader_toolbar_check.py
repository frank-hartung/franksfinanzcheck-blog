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
    required_ids = ["ff-reader-toolbar", "ff-listen-btn", "ff-listen-stop", "ff-listen-prev", "ff-listen-next", "ff-summary-btn", "ff-reader-status", "ff-reader-progress-bar", "ff-reader-config", "ff-reader-remaining"]
    for rid in required_ids:
        if rid not in content:
            return False, f"ID '{rid}' fehlt in reader_toolbar.html"

    # Highend-Vorgabe: keine manuellen Regler, keine Tempo-Anzeige, kein Tastatur-Hinweis
    forbidden = {
        "ff-reader-speed": "Tempo-Regler darf nicht vorhanden sein (automatische Qualitätsanpassung)",
        "ff-reader-voice": "Stimmenwahl darf nicht vorhanden sein (männliche Highend-Stimme wird automatisch gewählt)",
        "ff-reader-toolbar__hint": "Tastatur-Hinweis (Alt + L …) darf nicht angezeigt werden",
        "Alt + L": "Tastatur-Hinweis (Alt + L …) darf nicht angezeigt werden",
        "Alt + ←": "Tastatur-Hinweis (Alt + ←/→) darf nicht angezeigt werden",
        "Alt + ↑": "Tastatur-Hinweis (Alt + ↑/↓ Tempo) darf nicht angezeigt werden",
    }
    for token, msg in forbidden.items():
        if token in content:
            return False, f"{msg} – Token '{token}' in reader_toolbar.html gefunden"
    return True, "reader_toolbar.html vollständig (ohne Tempo-Regler, Stimmenwahl und Tastatur-Hinweis)"

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
        
    # Highend-Sprachausgabe: Prosodie, Chunking, Steuerung
    highend_tokens = [
        "PROSODY", "splitForSpeech", "buildTimeline", "pauseAfterChunk",
        "setupMediaSession", "rankVoices", "jumpBlock",
        "estimateRemaining", "startKeepAlive", "STUDIO_VOICES",
    ]
    for token in highend_tokens:
        if token not in content:
            return False, f"Highend-Sprachausgabe unvollständig (Token '{token}' fehlt)"

    # Automatische Qualitätsanpassung (statt manueller Regler)
    for token in ["QUALITY_PROFILES", "calibrateQuality", "qualityTierForScore", "degradeLevel", "quality.maxChunk", "quality.rate"]:
        if token not in content:
            return False, f"Automatische Qualitätsanpassung unvollständig (Token '{token}' fehlt)"

    # Verboten: manuelle Regler, Tempo-Anzeige, Tastenkürzel
    forbidden_js = {
        "ff-reader-speed": "Tempo-Regler",
        "ff-reader-voice": "Stimmenwahl",
        "speedSet": "Tempo-Anzeige (Status 'Tempo: x-fach')",
        "e.altKey": "Alt-Tastenkürzel",
        "e.key === 'Escape') { e.preventDefault(); endReading": "Esc-Tastenkürzel zum Beenden des Vorlesens",
        "ff-reader:rate": "gespeichertes Nutzer-Tempo",
        "ff-reader:voice": "gespeicherte Nutzer-Stimme",
    }
    for token, what in forbidden_js.items():
        if token in content:
            return False, f"{what} darf nicht mehr in ff-reader.js vorkommen (Token '{token}')"

    # Redaktionelle Aussprache-Veredelung
    for token in ["Paragraf ", "Sozialgesetzbuch", "September", "die Webseite ", "E T F"]:
        if token not in content:
            return False, f"Aussprache-Veredelung unvollständig (Token '{token}' fehlt)"

    # Kurzfassung v4 (Verlagshaus-Highend: Capital/WiWo/ZEIT)
    summary_tokens = [
        "extractKeyBullets", "extractKeyFigures", "extractToc", "extractTables",
        "buildSummaryData", "buildPlainText", "summarySentences", "maskSentenceDots",
        "signalScore", "trapFocus", "lockScroll", "summaryToc", "summaryAuthor",
        "summaryStand", "summaryRowCount", "summaryJump", "summaryJumpTable",
    ]
    for token in summary_tokens:
        if token not in content:
            return False, f"Kurzfassung v4 unvollständig (Token '{token}' fehlt)"

    return True, "ff-reader.js (Highend-Prosodie, männliche Studio-Stimme, Auto-Qualität, DE/EN, Tabellen-Barrierefreiheit + Kurzfassung v4) vollständig"

def check_css():
    path = ROOT / "assets" / "css" / "extended" / "ff-reader.css"
    if not path.is_file():
        return False, "assets/css/extended/ff-reader.css fehlt"
    content = path.read_text(encoding="utf-8")
    required_classes = [".ff-reader-toolbar", ".ff-reader-btn--listen", ".ff-reader-btn--summary", ".ff-reader-active", "tr.ff-reader-active", ".ff-reader-btn--nav", ".ff-reader-toolbar__remaining"]
    for cls in required_classes:
        if cls not in content:
            return False, f"CSS-Klasse '{cls}' fehlt in ff-reader.css"
    # Kurzfassung v4 (Verlagshaus-Highend)
    for cls in [".ff-summary__hero", ".ff-summary__bullets", ".ff-summary__bullet", ".ff-summary__jump", ".ff-summary__figures", ".ff-summary__figure", ".ff-summary__figure-value", ".ff-summary__figure-label", ".ff-summary__toc", ".ff-summary__toc-lead", ".ff-summary__table", ".ff-summary__table-row", ".ff-summary__empty"]:
        if cls not in content:
            return False, f"CSS-Klasse '{cls}' fehlt in ff-reader.css (Kurzfassung v4)"
    for cls in [".ff-reader-select", ".ff-reader-field", ".ff-reader-toolbar__hint"]:
        if cls in content:
            return False, f"Veraltete CSS-Klasse '{cls}' (Regler/Tastatur-Hinweis) muss entfernt sein"
    return True, "ff-reader.css (Styling & A11y-Highlighting + Kurzfassung v4) vollständig"

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
