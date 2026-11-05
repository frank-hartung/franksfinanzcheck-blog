# Externe Autorität & Distribution – Runbook

**Verbindliche Quellen:** `data/authority_strategy.yaml` · `data/authority_evidence.yaml`  
**Wache:** `scripts/authority_engine.py` · **Report:** `AUTHORITY-RADAR.md`  
**Öffentlich:** `/studien/` · `/presse/`

## Was damit dauerhaft erzwungen wird

1. **Mindestens ein Linkable Asset pro Quartal.** Ein Live-Status ist nur gültig, wenn Landingpage, Methodik-Anker, mindestens zwei Quellen, CSV/Datensatz und Presseformat tatsächlich existieren.
2. **Keine Phantomautorität.** Mediennennung, Interview, Kooperation und Editorial-Link zählen nur mit Typ, Datum, Herausgeber und öffentlicher HTTPS-URL im Evidenzregister. Eigene Domains, Tracking-URLs und Doppelmeldungen werden abgewiesen.
3. **Keine erfundenen Kennzahlen.** Unbekannte Werte bleiben `null` (im Report `—`). `0` heißt gemessen und null. Zahlen ohne Import-/Evidenzbeleg machen den Check rot.
4. **Eine Quelle pro Zahl.** GSC-Reichweite wird aus dem Tages-Ledger **abgeleitet**, nicht in einen zweiten Speicher kopiert.
5. **Nur erhebbare Forderungen.** Der Radar verlangt nie einen Monat, der noch nicht abgeschlossen ist, und nie eine Kennzahl, die im Vertrag als „nicht messbar“ oder „nicht aktiv“ erklärt ist.
6. **Menschliches Qualitäts-Gate.** Die Automatik plant, prüft und meldet; sie verschickt keine Pitches und postet nicht in Communities.

## Messvertrag lesen

`data/authority_strategy.yaml` → `measurement`:

| Feld | Bedeutung |
|---|---|
| `reporting_lag_days: 4` | Der Berichtsmonat ist der letzte Monat, der zum Stichtag final messbar ist. Am 5. ist das der Vormonat, am 3. der Monat davor. |
| `manual_due_day: 5` | Fälligkeit eines manuellen Exports im Folgemonat. Vorher ist der Befund „🕒 fällig ab …“, kein P2. |
| `gsc_max_age_days: 5` | Älter darf der letzte Ledger-Tag nicht sein, sonst P1 (Messkette steht). |
| `sources[].mode` | `automatisch` (ableitbar), `manuell` (Export mit Fälligkeit), `nicht_messbar`/`nicht_aktiv` (Entscheidung mit Grund und Datum). |

Jede Kennzahl gehört **genau einer** Quelle. Ein neuer Kanal (z. B. „Klickzähler aktiv“) erbt keinen
Automatismus: Modus im Vertrag ändern, sonst meldet der Radar die Abweichung.

## Monatlicher Ablauf (10–15 Minuten)

### 1. Google Search Console – nichts zu tun

`scripts/gsc_import.py` schreibt täglich `data/gsc/tagesdaten.jsonl`. Der Radar leitet daraus den
Berichtsmonat ab (Klicks, Impressionen, CTR, Tagesabdeckung) und zeigt den laufenden Monat nur zur
Information. Fehlt der Ledger oder ist er älter als `gsc_max_age_days`, meldet der Radar **P1** –
dann ist nicht die Zahl falsch, sondern die Messung steht.

Marken-Suchanfragen führt der Tages-Ledger nicht. Der Radar zeigt deshalb ein **rollierendes
28-Tage-Fenster** aus `data/gsc/top_suchbegriffe_28t.json` (Top-500, ausdrücklich kein Monatswert).
Ein monatsscharfer Markenwert entsteht nur über einen CSV-Export:

```bash
python3 scripts/authority_engine.py --import-gsc ~/Downloads/Leistung.csv --period 2026-10
```

Der Import speichert ausschließlich Summen (inklusive Marken-Summen) unter
`data/authority_measurements/`. Suchanfragen werden im Arbeitsspeicher ausgewertet und nicht
versioniert. Ohne Suchanfragen-Spalte bleiben Markenwerte `null` – nie `0`.

### 2. Newsletter-Kennzahlen belegen (der einzige monatliche Handgriff)

Vorlage erzeugen, im Newsletter-Studio bzw. bei Resend ablesen, ausfüllen:

```bash
python3 scripts/authority_engine.py --template --period 2026-10 > /tmp/audience-2026-10.json
# Zahlen aus dem Dashboard/Export eintragen (Raten als Anteil 0..1), dann:
python3 scripts/authority_engine.py --import-audience /tmp/audience-2026-10.json --period 2026-10
```

Regeln: nur Zahlen, die wirklich ablesbar sind. Ein belegter Leerzustand (`0` mit
`provenance: "Worker-Export …"`) ist eine Messung; „weiß nicht“ bleibt `null`. Unbekannte Felder
werden abgewiesen, damit keine Kennzahl still verschwindet. Empfängeradressen gehören nie ins Repo.

`returning_reader_rate` und `conversions` stehen im Vertrag als `nicht_messbar` bzw. `nicht_aktiv`
(kein Besucherzähler, Klickzähler nicht deployt). Sie werden **nicht** eingefordert und nie als `0`
behauptet. Wer einen Zähler in Betrieb nimmt, ändert zuerst den Vertrag – der Radar meldet die
Abweichung mit Signal (`data/klickmessung.yaml: aktiv=true`, `data/provisionen_aggregat.json`).

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

Gültige Typen: `editorial_link`, `media_mention`, `interview`, `cooperation`. Abgewiesen werden:
eigene Domain (`franksfinanzcheck.de`), Tracking-Parameter (`utm_*`, `gclid`, `fbclid`, …), fehlender
Herausgeber/Titel, ungültiges Datum und dieselbe URL als zweiter Beleg. Eigene Social-Posts,
Verzeichnisse, Presseportale ohne redaktionelle Auswahl, gekaufte Links und Affiliate-Platzierungen
zählen nicht.

### 4. Radar laufen lassen

```bash
npm run authority:selftest     # Selbsttest + 31 Vertragstests (offline)
npm run authority:check        # Report schreiben, Exit 0/1
python3 scripts/authority_engine.py --as-of 2026-11-05 --json /tmp/radar.json   # Stichtag + Maschinenlesbarkeit
```

Exit 1 bedeutet redaktionellen Handlungsbedarf, nicht Softwaredefekt. Exit 2 bedeutet ungültigen
Vertrag, ungültigen Ledger oder fehlende Asset-Datei und blockiert den Workflow.

## Deklaration im Vertrag

`measurement.periods` ist die **Erklärung**, die Messlage der **Befund**. Beides muss zusammenpassen:

- `status: belegt` bei fehlenden Kennzahlen → P2 („Deklaration ohne Beleg ist eine Behauptung“).
- `status: offen`/`teilweise`, obwohl alle Kennzahlen belegt sind → P2 (Deklaration nachziehen).

Der Radar korrigiert die YAML nicht selbst. Eine automatisch umgeschriebene Deklaration wäre keine
Erklärung mehr.

## Quartalsproduktion

Spätestens sechs Wochen vor dem Release:

1. Fragestellung und Aussagegrenze festlegen.
2. Primärquellen und feste Berechnungsmethode dokumentieren (`## Methodik` ist Pflichtanker).
3. CSV oder maschinenlesbaren Datensatz erzeugen.
4. Landingpage mit Stand, Autor, Methodik, Quellen, Limitationen und Korrekturweg veröffentlichen.
5. Pressegrafik und konkrete Zitierweise bereitstellen.
6. Pressebereich aktualisieren.
7. Erst danach individuelle Redaktionen, Fachleute und passende Organisationen ansprechen.
8. Drei Monate später Wirkung anhand belegter Links, Erwähnungen, GSC und wiederkehrender Leser bewerten.

Der Radar prüft Punkt 1–5 maschinell (Asset-Reife: Inhaltsseite, Methodik-Anker, Datensatz,
Presseformat, ≥ 2 Quellen) und meldet fehlende Dateien als Vertragsfehler (Exit 2).

## Veröffentlichungsplan

- Q4 2026: Fixkosten-Index Energie-Baseline – live
- Q1 2027: Kündigungsfristen-Kalender
- Q2 2027: Studie zu versteckten Vertragskosten
- Q3 2027: Strom- und Gaspreis-Tracker
- Q4 2027: Versicherungs-Klausel-Atlas

Der monatliche GitHub-Workflow `.github/workflows/authority-radar.yml` öffnet bei überfälligem
Release, fälligem manuellem Export, fehlender GSC-Abdeckung oder stehender Messkette genau ein
dedupliziertes Issue und schließt es, sobald der Radar keine Maßnahme mehr hat. Die Historie der
Fassungen steht im Report selbst (Berichtsmonat, Abdeckung, Belege) – der Issue-Text ist nur die
jeweils letzte Ausgabe.
