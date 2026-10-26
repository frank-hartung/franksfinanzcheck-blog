# Detail-Listen der Search Console

Hier gehören die CSV-Exporte aus **Indexierung → Seiten → Grund → Exportieren**
hin – eine Datei je Grund, mit dem Namen, den die Oberfläche vergibt:

| Datei | Grund |
|---|---|
| `Nicht gefunden (404).csv` | Die 223 gemeldeten 404er (Stand 19.10.2026) |
| `Gefunden – zurzeit nicht indexiert.csv` | 69 Seiten ohne Crawl |
| `Gecrawlt – zurzeit nicht indexiert.csv` | 4 Seiten mit Prüfbedarf |
| `Seite mit Weiterleitung.csv` | 1 Seite |
| `Alternative Seite mit ordnungsgemäßem Canonical-Tag.csv` | Dubletten |
| `Durch robots.txt blockiert.csv` | Gateways (Soll-Zustand) |
| `Durch „noindex“-Tag ausgeschlossen.csv` | Vertragsseiten (M5) |
| `Indexierte Seiten.csv` | die 117 – nötig, um die 18 Altlasten zu benennen (M4) |

Zusätzlich eine Datei `.stand` mit dem Exportdatum in einer Zeile:

```
2026-10-26
```

Beides ist freiwillig – aber ohne die Dateien bleibt jede Triage eine Summe.
Der Befund sagt das in jeder Ausgabe (Regel **W9**) und der Tageslauf schickt
eine Warnung, solange der Ordner leer ist.

## Was danach passiert

```bash
npm run gsc:triage     # liest diesen Ordner → triage.md, redaktions_queue.md
```

Die Triage ordnet jeder URL eine Priorität (P0–P3), eine Aktion und einen
Beleg zu. Bereits getroffene Entscheidungen (`data/weiterleitungen.yaml`,
`data/url_entfallen.yaml`) werden **nicht** erneut vorgeschlagen; URLs, die
gebaut werden, gelten als erledigt. Was übrig bleibt, ist die Arbeitsliste.
