#!/usr/bin/env python3
"""Aktualisiert Workbook + README mit dem Nach-Pinnen-Hinweis."""

# 1) Workbook (Markdown)
p = 'PINTEREST-WACHSTUMS-WORKBOOK.md'
s = open(p, encoding='utf-8').read()
old = "- [ ] **Neue Blog-Artikel der Woche** (14 Stück vom Bot) als Pins nachpinnen"
new = ("- [x] **Neue Blog-Artikel nachpinnen** – läuft automatisch montags um 17:30 Uhr "
       "(Workflow 'Wöchentliches Nach-Pinnen', sobald Pinterest-API eingerichtet ist). "
       "Nur bei Fehlern manuell prüfen: GitHub → Actions → Workflow-Log")
if old in s:
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)
    print("OK Workbook")
else:
    print("Muster Workbook nicht gefunden – suche Variante…")
    import re
    m = re.search(r"- \[ \].*?nachpinnen.*", s)
    if m:
        s = s.replace(m.group(0), new)
        open(p, 'w', encoding='utf-8').write(s)
        print("OK Workbook (per Regex)")
    else:
        print("FEHLER Workbook")

# 2) README
p = 'README.md'
s = open(p, encoding='utf-8').read()
old = "**Automatisches Einzigartigkeits-Audit (Qualitäts-Gate):**"
new = """**📌 Automatisches Nach-Pinnen bei Pinterest (montags 17:30 Uhr):**

Der Workflow **„Wöchentliches Nach-Pinnen"** erstellt jeden Montag um 17:30 Uhr (DE)
automatisch Pins für alle neuen Blog-Artikel (Cover-Bild, Beschreibung, Artikel-URL,
Hashtags) über die Pinterest API v5. Jeder Artikel wird nur einmal gepinnt
(`pinned: true`-Flag im Frontmatter).

**Einmalige Einrichtung (~10 Min.):** Siehe `ANLEITUNG-PINTEREST-API.md`
- Pinterest-Developer-App + Access-Token → Secret `PINTEREST_ACCESS_TOKEN`
- Board-ID (`python3 scripts/generate_pins.py --list-boards`) → Variable `PINTEREST_BOARD_ID`

**Automatisches Einzigartigkeits-Audit (Qualitäts-Gate):**"""
if old in s:
    s = s.replace(old, new)
    open(p, 'w', encoding='utf-8').write(s)
    print("OK README")
else:
    print("FEHLER README")
