# Redaktionelle Datensätze

Jede YAML-Datei in diesem Verzeichnis (außer `schema.yaml`) ist eine versionierte Single Source of Truth für eine Visualisierung. Regeln:

1. Werte niemals zusätzlich im Chart-Template pflegen.
2. Schema und Standard in `docs/DATEN-VISUALISUNGSSTANDARD.md` beachten.
3. Vor Veröffentlichung `python3 scripts/visual_data_gate.py` ausführen.
4. Sachänderungen in `changelog` dokumentieren.
5. Die Daten werden beim Hugo-Build in statisches SVG und eine HTML-Tabelle übersetzt.

Einbindung:

```go-html-template
{{</* chart dataset="tagesgeld_modell" */>}}
```

Optionale Parameter `title` und `summary` dürfen redaktionell präzisieren, aber keine Datenaussage verändern.
