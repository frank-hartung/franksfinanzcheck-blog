# ANLEITUNG – Hemingway Editor für die Lesbarkeit

**Stand:** 2026-09-30 · **Tool:** [Hemingway Editor](https://hemingwayapp.com/) · **CI-Begleiter:** `scripts/hemingway_check.py`

## Warum Hemingway?

Der kostenlose Hemingway Editor ist eine etablierte Schlusskontrolle für Blogtexte. Er macht lange Sätze, schwer lesbare Wörter, Passiv und verschachtelte Absätze sichtbar. Das passt besser zur gewünschten Stilpflege als eine generative Modell-Politur: Die Redaktion entscheidet selbst, welche Änderung den Inhalt wirklich verbessert.

Der Editor ist browserbasiert und bietet keine offizielle CI-API. Darum gibt es im Repository einen kostenlosen, datenschutzfreundlichen Begleiter. Er arbeitet offline, braucht weder Konto noch API-Key und schreibt niemals automatisch Text um. Seine Auswertung nutzt die bereits gehärtete deutsche Lesbarkeits-Engine (`readability_check.py`) als Single Source of Truth und prüft:

- Flesch-Amstad-Score und Ziel/Floor
- durchschnittliche Satzlänge
- lange Wörter
- Schachtelsätze
- zu lange Absätze
- Passiv-Formulierungen
- Keyword-Dumps

## Nutzung

```bash
# Alle bestehenden Artikel prüfen
python3 scripts/hemingway_check.py

# Einen Artikel prüfen
python3 scripts/hemingway_check.py \
  --file content/posts/2026-09-30-notgroschen-aufbauen-wie-viel-reicht-wirklich/index.md

# Nur neue Artikel im Content-Geburtslauf
python3 scripts/hemingway_check.py --new-only

# Bestands-Gate mit maschinenlesbarem Report
python3 scripts/hemingway_check.py \
  --gate-bestand --report HEMINGWAY-REPORT.md

# JSON für weitere Automatisierung
python3 scripts/hemingway_check.py --json

# Regressionstest
python3 scripts/hemingway_check.py --selftest
```

Ein Befund ist ein redaktioneller Hinweis, keine automatische Umschreibung. Für die manuelle Schlussrunde Text in den [kostenlosen Hemingway Editor](https://hemingwayapp.com/) kopieren, Vorschläge prüfen und nur sinnvolle Änderungen in den Artikel übernehmen. Zahlen, Fakten, Links, Shortcodes und Marken bleiben dabei unter redaktioneller Kontrolle.

## Automation

| Workflow | Ausführung | Zweck |
|---|---|---|
| `hemingway-check.yml` | Mo/Mi/Fr 04:50 UTC | Offline-Grammatik und Sprachglättung, danach Hemingway-Lesbarkeitscheck über den Bestand |
| `content-engine-v2.yml` | bei neuen Artikeln | Lesbarkeitscheck nach der Qualitätskette (`--new-only`) |
| `redaktions-politur.yml` | manuell | Offline-Notlauf ohne Konto und ohne Netz |

Der Bestandslauf schreibt bei einem Lesbarkeitsbefund nicht heimlich am Artikel herum. Der Report bleibt im Workflow sichtbar; die manuelle Hemingway-Runde ist der bewusste nächste Schritt.

## Kosten und Datenschutz

- keine kostenpflichtige API
- kein Modell- oder Fremd-Token
- der CI-Check läuft vollständig offline
- nur wer die manuelle Schlussrunde nutzt, kopiert den ausgewählten Text in den Browser-Editor

## Qualitätsvertrag

Die bestehenden Schutzverträge gelten weiter: Frontmatter, Überschriften, Links, URLs, Shortcodes, Code und Fakten werden vom lokalen Check nicht verändert. Der Hemingway-Begleiter ist ein Mess- und Warnwerkzeug, kein Freifahrtschein für semantische Änderungen.
