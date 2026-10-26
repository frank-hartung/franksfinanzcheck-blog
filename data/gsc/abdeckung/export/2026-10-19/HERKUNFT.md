# Herkunft dieses Exports

**Geladen:** 26.10.2026 aus der Google Search Console (Property
`sc-domain:franksfinanzcheck.de`), Bereich **Indexierung → Seiten**.
**Datenstand des Berichts:** 19.10.2026 (letzter Tag im Diagramm).

Die Dateien wurden unverändert übernommen, nur umbenannt. Grund für die
Umbenennung: Die Originalnamen der Oberfläche („Kritische Probleme.csv“,
„Nicht kritische Probleme.csv“) beschreiben eine Bewertung, die im Ablauf
keine Rolle spielt – erkannt wird der Dateityp am Kopf, nicht am Namen
(`scripts/gsc_abdeckung.py`, `erkenne_art`).

| Datei hier | Originalname der Search Console | Inhalt |
|---|---|---|
| `uebersicht.csv` | Kritische Probleme.csv | Grund, Quelle, Validierung, Seiten |
| `diagramm.csv` | Diagramm.csv | Datum, nicht indexiert, indexiert, Impressionen |
| `metadaten.csv` | Metadaten.csv | Property, Sitemap |
| `nicht-kritische-probleme.csv` | Nicht kritische Probleme.csv | leer bis auf die Kopfzeile |

## Was fehlt

Die Search Console exportiert die betroffenen **URLs** nur über die
Detail-Listen je Grund („Nicht gefunden (404).csv“ und so weiter). Diese Listen
gehörten nicht zum vorliegenden Export. Genau darum steht im Befund eine offene
Beweisfrage statt einer geschätzten Zuordnung: Ohne URL-Liste lassen sich von
den 223 gemeldeten 404ern nur die 30 erklären, die der Repo-Bestand hergibt
(Taxonomie-URLs und bewusst entfallene Alt-URLs).

Sobald eine Detail-Liste vorliegt:

```bash
python3 scripts/gsc_abdeckung.py --vorschlaege "details/Nicht gefunden (404).csv"
```

Das Werkzeug schlägt Ziele über den datumsbereinigten Slug vor und schreibt
nichts. Die Entscheidung bleibt bei einem Menschen (Regeln A–E in
`data/weiterleitungen.yaml`).
