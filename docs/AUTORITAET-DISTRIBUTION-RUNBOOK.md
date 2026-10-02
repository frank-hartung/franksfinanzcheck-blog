# Externe Autorität & Distribution – Runbook

**Verbindliche Quellen:** `data/authority_strategy.yaml` · `data/authority_evidence.yaml`  
**Wache:** `scripts/authority_engine.py` · **Report:** `AUTHORITY-RADAR.md`  
**Öffentlich:** `/studien/` · `/presse/`

## Was damit dauerhaft erzwungen wird

1. **Mindestens ein Linkable Asset pro Quartal.** Ein Live-Status ist nur gültig, wenn Landingpage, Methodik, mindestens zwei Quellen, CSV/Datensatz und Presseformat tatsächlich existieren.
2. **Keine Phantomautorität.** Mediennennung, Interview, Kooperation und Editorial-Link zählen nur mit Typ, Datum und öffentlicher HTTPS-URL im Evidenzregister.
3. **Keine erfundenen Kennzahlen.** Unbekannte Werte bleiben `null`. Zahlen ohne Import-/Evidenzbeleg machen den Check rot.
4. **Audience statt Vanity.** Monatlich werden GSC, Newsletter, Returning Reader, Conversion und Markensuche geprüft. Roh-Suchanfragen werden nie eingecheckt.
5. **Menschliches Qualitäts-Gate.** Die Automatik plant, prüft und meldet; sie verschickt keine Pitches und postet nicht in Communities.

## Monatlicher Ablauf (30–45 Minuten)

### 1. GSC aggregiert importieren

In Google Search Console den Leistungsbericht als CSV exportieren. Danach lokal:

```bash
python3 scripts/authority_engine.py \
  --import-gsc ~/Downloads/Leistung.csv \
  --period 2026-10
```

Der Import speichert nur Summen und Marken-Summen unter `data/authority_measurements/`. Suchanfragen werden im Arbeitsspeicher ausgewertet und nicht versioniert.

### 2. Weitere Kennzahlen belegen

Newsletter-Abonnenten und Klickrate, Returning-Reader-Rate sowie Conversions immer mit Zeitraum und Export-/Dashboard-Beleg erfassen. Dafür eine lokale, nicht zu committende Datei anlegen:

```json
{
  "newsletter_subscribers": 120,
  "newsletter_click_rate": 0.084,
  "returning_reader_rate": 0.21,
  "conversions": 7,
  "provenance": "Newsletter-Studio + Umami Monatsauszug 2026-10"
}
```

Dann ausschließlich die validierten Aggregate übernehmen:

```bash
python3 scripts/authority_engine.py \
  --import-audience ~/Downloads/audience-2026-10.json \
  --period 2026-10
```

Keine Schätzung und keine Umdeutung von `null` zu null Ereignissen. Sensible Rohdaten bleiben außerhalb des Repositorys; versioniert werden Aggregate.

### 3. Verdiente Signale registrieren

Nur tatsächliche Belege in `data/authority_evidence.yaml` aufnehmen:

```yaml
- id: beispiel-2026-10
  kind: editorial_link
  title: "Titel des redaktionellen Beitrags"
  publisher: "Medium"
  url: "https://medium.example/beitrag"
  published: 2026-10-20
  target: "https://franksfinanzcheck.de/studien/fixkosten-index-2026-q4/"
  rel: editorial
```

Gültige Typen: `editorial_link`, `media_mention`, `interview`, `cooperation`. Eigene Social-Posts, Presseportale ohne redaktionelle Auswahl, gekaufte Links und Affiliate-Platzierungen zählen nicht.

### 4. Radar laufen lassen

```bash
npm run authority:selftest
npm run authority:check
```

Exit 1 bedeutet redaktionellen Handlungsbedarf, nicht Softwaredefekt. Exit 2 bedeutet ungültigen Vertrag oder fehlende Asset-Datei und blockiert den Workflow.

## Quartalsproduktion

Spätestens sechs Wochen vor dem Release:

1. Fragestellung und Aussagegrenze festlegen.
2. Primärquellen und feste Berechnungsmethode dokumentieren.
3. CSV oder maschinenlesbaren Datensatz erzeugen.
4. Landingpage mit Stand, Autor, Methodik, Quellen, Limitationen und Korrekturweg veröffentlichen.
5. Pressegrafik und konkrete Zitierweise bereitstellen.
6. Pressebereich aktualisieren.
7. Erst danach individuelle Redaktionen, Fachleute und passende Organisationen ansprechen.
8. Drei Monate später Wirkung anhand belegter Links, Erwähnungen, GSC und wiederkehrender Leser bewerten.

## Veröffentlichungsplan

- Q4 2026: Fixkosten-Index Energie-Baseline – live
- Q1 2027: Kündigungsfristen-Kalender
- Q2 2027: Studie zu versteckten Vertragskosten
- Q3 2027: Strom- und Gaspreis-Tracker
- Q4 2027: Versicherungs-Klausel-Atlas

Der monatliche GitHub-Workflow `.github/workflows/authority-radar.yml` öffnet bei fehlendem Import, überfälligem Release oder Refresh genau ein dedupliziertes Issue.
