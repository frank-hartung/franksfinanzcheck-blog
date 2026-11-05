# Authority-Radar – 2026-11-05

> Belegt externe Autorität, Distribution und Audience-Kennzahlen. `0` heißt **gemessen und null**. `—` heißt **unbekannt**. Unbekannt bleibt unbekannt.

**Berichtsmonat:** 2026-10 (31/31 Tage im GSC-Ledger) · **Aktuelles Quartal:** 2026-Q4 · **Belegte Messquellen:** 1/2 · **Handlungsbedarf:** 0 × P1, 1 × P2

## Handlungsqueue

- **P2:** Newsletter (Worker/Resend): Aggregate für 2026-10 fehlen (newsletter_subscribers, newsletter_click_rate), fällig seit 2026-11-05. Export belegen und einlesen: `python3 scripts/authority_engine.py --import-audience <datei> --period 2026-10` (Vorlage: `--template`; Runbook: docs/AUTORITAET-DISTRIBUTION-RUNBOOK.md). Unbekannt bleibt unbekannt – eine 0 gilt nur mit Beleg.

## Datenlage

| Quelle | Modus | Stand | Status | Beleg |
|---|---|---|---|---|
| Google Search Console | automatisch | 2026-10-01–2026-10-31 · 31/31 Tage | ✅ belegt | `data/gsc/tagesdaten.jsonl` · 31/31 Tage |
| Newsletter (Worker/Resend) | manuell | — | ❌ offen seit 2026-11-05 | — |
| Wiederkehrende Leser | nicht_messbar | Entscheidung 2026-09-24 | ⏸ bewusst nicht gemessen | — |
| Conversion/Provision | nicht_aktiv | Entscheidung 2026-10-14 | ⏸ bewusst nicht gemessen | — |

- **Wiederkehrende Leser** (nicht_messbar): Es läuft bewusst kein Besucherzähler und kein Cookie-Tracking; eine Returning-Rate wäre geraten.

- **Conversion/Provision** (nicht_aktiv): Der Klickzähler ist nicht deployt (data/klickmessung.yaml: aktiv=false) und es liegt keine Provisions-Tabelle vor.

Ledger-Kopf: letzter Tag **2026-11-02** (3 Tage alt, Status frisch, Import ok). Der laufende Monat 2026-11 wird gezeigt, aber nie eingefordert – er ist noch nicht abgeschlossen.

## Audience-Kennzahlen 2026-10

| Kennzahl | Wert | Quelle | Beleg |
|---|---:|---|---|
| GSC-Klicks | 0 | Google Search Console | `data/gsc/tagesdaten.jsonl` · 31/31 Tage |
| GSC-Impressionen | 240 | Google Search Console | `data/gsc/tagesdaten.jsonl` · 31/31 Tage |
| Marken-Klicks | — | Google Search Console | Tages-Ledger führt keine Suchanfragen (monatsscharf nur per CSV-Export) |
| Newsletter-Abonnenten | — | Newsletter (Worker/Resend) | kein Beleg vorhanden |
| Newsletter-Klickrate | — | Newsletter (Worker/Resend) | kein Beleg vorhanden |
| Wiederkehrende Leser | — | Wiederkehrende Leser | bewusst nicht gemessen: Es läuft bewusst kein Besucherzähler und kein Cookie-Tracking; eine Returning-Rate wäre geraten. |
| Conversions | — | Conversion/Provision | nicht in Betrieb: Der Klickzähler ist nicht deployt (data/klickmessung.yaml: aktiv=false) und es liegt keine Provisions-Tabelle vor. |
| Conversion-Rate | — | Conversion/Provision | nicht in Betrieb: Der Klickzähler ist nicht deployt (data/klickmessung.yaml: aktiv=false) und es liegt keine Provisions-Tabelle vor. |

Abgeleiteter CTR aus dem Ledger: **0,0 %** (Klicks 0 / Impressionen 240, 2026-10-01–2026-10-31).

## Markensichtbarkeit (rollierend, nicht monatsscharf)

Fenster **2026-10-06–2026-11-02** (28 Tage) aus `data/gsc/top_suchbegriffe_28t.json`: 53 Suchanfragen in den Top-500, davon 0 mit Markenbezug.

- Impressionen gesamt (Top-500): **183**, davon markenbezogen **0** (0,0 %).
- Klicks gesamt: **0**, davon markenbezogen **0**.

_Das Fenster ist rollierend und deckt die Top-500-Suchanfragen ab. Es ist kein Monatswert und ersetzt keinen Monats-Export mit Markensuche._

## Verdiente externe Signale

| Signal | Anzahl |
|---|---:|
| Redaktionelle Links | 0 |
| Mediennennungen | 0 |
| Experteninterviews | 0 |
| Aktive Kooperationen | 0 |

_Alle vier Register geprüft. `0` heißt: kein prüfbarer Beleg eingetragen – das ist der belegte Ist-Stand, kein Nachweis von Wirkung._

## Nachweisregister

_Keine externe Autorität behauptet: Im Evidenzregister liegt noch kein prüfbarer Beleg. Eigene Posts, Verzeichnisse und Affiliate-Platzierungen zählen nicht._

## Distribution (menschlich, nicht automatisiert)

Der Radar versendet nichts und zählt keine Pitches. Belegt ist hier nur, welche Outreach-Vorlagen im Repo liegen – **nicht**, ob sie verschickt wurden oder gewirkt haben.

- `docs/outreach/PR-KIT-ENERGIE-BASELINE-Q4-2026.md` (Stand 28.10.2026)

Grenzen dieser Ausgabe: Der Markenanteil ist ein rollierendes 28-Tage-Fenster der Top-500-Suchanfragen, kein Monatswert. Ohne Besucherzähler gibt es keine Returning-Rate. Wirkung wird nicht kausal zugerechnet.

## Quartalsprogramm und Asset-Reife

| Quartal | Asset | Status | Termin | Reife |
|---|---|---|---|---|
| 2026-Q4 | `fixkosten-index-2026-q4` | live | 2026-10-02 | 5/5 Kriterien |
| 2027-Q1 | `kuendigungsfristen-kalender-2027` | planned | 2027-02-15 | — |
| 2027-Q2 | `vertragskosten-studie-2027` | planned | 2027-05-15 | — |
| 2027-Q3 | `strom-gas-preis-tracker-2027-q3` | planned | 2027-08-15 | — |
| 2027-Q4 | `versicherungs-klausel-atlas-2027` | planned | 2027-10-15 | — |

**Fixkosten-Index Deutschland: Energie-Baseline Q4 2026** (live seit 2026-10-02)

- Reife: ✅ Inhaltsseite · ✅ Methodik-Anker · ✅ Datensatz/CSV · ✅ Presseformat · ✅ Quellen (≥ 2)
- Quellen: <https://www.bdew.de/service/daten-und-grafiken/bdew-strompreisanalyse/> · <https://www.bdew.de/service/daten-und-grafiken/bdew-gaspreisanalyse/>

## Messverlauf

| Monat | GSC-Klicks | GSC-Impressionen | Abdeckung | Audience-Aggregat |
|---|---:|---:|---|---|
| 2026-09 | 0 | 31 | 11/30 Tage | — |
| 2026-10 | 0 | 240 | 31/31 Tage | — |
| 2026-11 (laufend) | 0 | 40 | 2/30 Tage | — |

## Betriebsregel und Takt

Ein Asset ist erst live, wenn Inhaltsseite, Methodik, Rohdaten/CSV, Quellen und Presseformat vorhanden sind. Outreach bleibt menschlich; der Radar versendet nichts.

GSC wird aus `data/gsc/tagesdaten.jsonl` **abgeleitet** (ein Tageslauf, eine Wahrheit); der CSV-Import bleibt für Marken-Suchanfragen möglich. Manuelle Audience-Aggregate werden monatlich belegt (`--import-audience`). Was nicht messbar ist, steht mit Grund und Entscheidungsdatum im Vertrag – und wird nie als `0` behauptet.

Nächste Fälligkeiten: manueller Audience-Export für 2026-10 (2026-11-05) · nächster Quartalsrelease (2027-02-15) · nächster Radar-Lauf am 5. des Folgemonats.
