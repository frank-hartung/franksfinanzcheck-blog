# 📡 Authority-Radar #1076 – Dauerheilung (Highend-Report 05.11.2026)

**Vorgang:** Issue #1076 (`Authority-Radar: Distribution und Nachweise prüfen (2026-11-05)`)  
**Stichtag:** 2026-11-05 (UTC) · Berichtsmonat der Heilung: **2026-10**  
**Status:** ✅ Radar misst wieder die Wirklichkeit – 2 Befunde der Ausgabe vom 05.11. waren strukturell falsch, 1 echter Handlungsbedarf bleibt (menschlicher Export).

---

## 1. Befund: Was das Ticket behauptete – und was davon stimmte

Die automatisch erzeugte Ausgabe #1076 sagte:

| Behauptung im Ticket | Prüfung am 05.11.2026 | Urteil |
|---|---|---|
| „Für **2026-11** fehlt der aggregierte GSC-Import (inkl. Markensuche).“ | Der 5. November liegt **im** November. Der Monat ist nicht abgeschlossen, Google liefert final verzögert. Diesen Import kann es nie geben. | ❌ **falscher Adressat** |
| „Für **2026-11** fehlen Newsletter-, Retention- und Conversion-Aggregate.“ | Retention ist laut Hausentscheidung **nicht messbar** (kein Besucherzähler), Conversion **nicht aktiv** (Klickzähler nicht deployt). Zwei von drei Forderungen waren unerfüllbar. | ❌ **unerfüllbare Forderung** |
| „**Messimporte: 0**“ | 44 Tage echte Search-Console-Daten lagen im Repo (`data/gsc/tagesdaten.jsonl`, 20.09.–02.11.2026, davon Oktober **31/31 Tage**). Der Radar sah sie nicht. | ❌ **zweite Wahrheit** |
| „Redaktionelle Links / Mediennennungen / Interviews / Kooperationen: 0“ | Evidenzregister ist leer und wurde geprüft. | ✅ **korrekt** |
| Quartals-Asset Q4 live | Inhaltsseite, Methodik-Anker, CSV, Pressegrafik, zwei Quellen vorhanden. | ✅ **korrekt** |
| „Unbekannt bleibt unbekannt: `null` ist niemals `0`“ | Stand im Vorspann – wurde aber vom eigenen Code gebrochen (Marken-Klicks wurden ohne Suchanfragen-Spalte als `0` geschrieben). | ⚠️ **Anspruch ohne Deckung** |

**Kern des Befunds:** Der Radar war nicht „zu streng“, sondern **unadressierbar**. Ein Ticket, das
jeden Monat etwas verlangt, was am Ausspieltag physikalisch nicht existieren kann, wird nach zwei
Ausgaben ignoriert – und nimmt den einen echten Befund mit (fehlender Newsletter-Export).

---

## 2. Ursachen (Root Cause)

1. **Kalendermonat statt Berichtsmonat.** `evaluate()` prüfte `as_of.strftime("%Y-%m")` – also den
   *laufenden* Monat. Der Workflow läuft am 5. Damit war der GSC-Befund ein Dauerbefund.
2. **Zweiter Speicher für dieselbe Zahl (SSOT-Bruch).** GSC-Monatswerte mussten manuell als CSV nach
   `data/authority_measurements/` importiert werden, obwohl `scripts/gsc_import.py` die Daten täglich
   nach `data/gsc/` schreibt. Zwei Wahrheiten für eine Kennzahl – die schlechtere gewinnt.
3. **Kein Modus je Kennzahl.** `retention` und `conversion` standen in derselben P2-Zeile wie der
   Newsletter. Ob eine Kennzahl *erhebbar*, *manuell* oder *bewusst nicht gemessen* ist, war nirgends
   erklärt – also wurde alles eingefordert.
4. **`0` statt „unbekannt“.** Der CSV-Import setzte Marken-Klicks auf `0.0`, wenn die Datei keine
   Suchanfragen-Spalte hatte. Der Report nannte keine Quelle je Kennzahl und erklärt nicht, wann `0`
   gilt.
5. **Deklaration ohne Abgleich.** `measurement.periods` stand seit dem 02.10. auf `awaiting_import`,
   während die Daten längst im Ledger lagen. Niemand verglich Erklärung und Messlage.
6. **Belege nicht prüfbar.** Das Evidenzregister akzeptierte eigene Domains, fehlende Herausgeber und
   dieselbe URL doppelt; die Asset-Reife (Methodik-Anker, Presseformat, Datensatz) wurde behauptet,
   nicht geprüft.

---

## 3. Dauerheilung

### A. Messkette: eine Quelle pro Zahl (`scripts/authority_engine.py`)

* **GSC wird abgeleitet, nicht kopiert.** Neue Funktionen `load_gsc()`, `gsc_month()`,
  `gsc_health()`, `brand_window()` lesen `data/gsc/tagesdaten.jsonl`, `meta.json` und
  `top_suchbegriffe_28t.json` **read-only**. Ein CSV-Import bleibt als ausdrücklicher Vorrang möglich
  (nur er kennt Marken-Suchanfragen) – er ist kein Pflichtschritt mehr.
* **Berichtsmonat statt Kalendermonat.** `reporting_month(as_of, lag)` liefert den letzten final
  messbaren Monat (`reporting_lag_days: 4`): am 05.11. → 2026-10, am 04.11. → 2026-09. Der laufende
  Monat wird gezeigt, aber nie eingefordert.
* **Messvertrag mit Modus je Quelle** (`data/authority_strategy.yaml` → `measurement.sources`):
  `automatisch` (GSC, ableitbar), `manuell` (Newsletter, Fälligkeit `manual_due_day`),
  `nicht_messbar` (Retention: kein Zähler), `nicht_aktiv` (Conversion: Klickzähler aus). Jede
  Kennzahl gehört **genau einer** Quelle; nicht implementierte Automatikquellen sind ein
  Vertragsfehler (Exit 2), damit keine Kennzahl still ungeprüft bleibt.
* **Messkette als P1, Datenlücke als P2.** Steht der Ledger länger als `gsc_max_age_days`, meldet der
  Radar das als P1 („die Messung steht“) – eine andere Aussage als „der Monat ist unvollständig“ (P2).
* **Aktivierungssignal.** Liefert ein als `nicht_aktiv` geführter Kanal plötzlich Daten
  (`data/klickmessung.yaml: aktiv=true`, `data/provisionen_aggregat.json`), meldet der Radar
  „Vertrag nachziehen“ statt weiter an der Wirklichkeit vorbeizumessen.
* **Deklarationsabgleich.** `measurement.periods` wird gegen die Messlage geprüft: „belegt“ ohne
  Beleg → P2, „offen“ trotz vollständiger Belege → P2. Die YAML wird **nicht** automatisch
  umgeschrieben – eine automatisch erzeugte Deklaration wäre keine Erklärung.

### B. `null` ist niemals `0` – jetzt im Code

* `import_gsc()` schreibt Marken-Werte nur, wenn die Datei eine Suchanfragen-Spalte hat; sonst `null`.
* `validate_measurements()` prüft zusätzlich `brand_clicks ≤ clicks`, `brand_impressions ≤
  impressions`, unbekannte Kennzahlen (Tippfehler werden abgewiesen statt still verworfen) und
  Markenwerte in zulässigen Bereichen.
* Der Report trennt sichtbar: **`0` = gemessen und null**, **`—` = unbekannt**. Jede KPI-Zeile nennt
  Quelle und Beleg (Datei, Zeitraum, Abdeckung, Provenienz). Fehlt ein Beleg, steht der Grund da
  („Tages-Ledger führt keine Suchanfragen“, „bewusst nicht gemessen: …“, „nicht in Betrieb: …“).

### C. Belege und Assets werden geprüft, nicht behauptet

* Evidenz: eigene Domain ist kein Beleg, Herausgeber und Titel sind Pflicht, Tracking-Parameter und
  doppelte URLs werden abgewiesen, `target` muss auf eine eigene Seite zeigen.
* Assets: Methodik-Link muss auf die eigene Inhaltsseite zeigen **und** der Anker in der Seite
  existieren (Hugo-Überschriften-ID oder `{#anker}`); Datensatz und Presseformat müssen als Datei
  unter `static/downloads/` liegen; Quellen müssen eindeutige öffentliche HTTPS-URLs sein.
* Report: neue Sektion **Asset-Reife** (5 Kriterien je Live-Asset) und **Distribution (menschlich,
  nicht automatisiert)** – der Radar listet Outreach-Vorlagen, behauptet aber weder Versand noch
  Wirkung.

### D. Report als Agentur-Artefakt (`AUTHORITY-RADAR.md`)

Neu strukturiert: Kopfzeile mit Berichtsmonat, Abdeckung, Quartal, belegten Messquellen und
P1/P2-Zahl · Handlungsqueue mit Fälligkeit und exaktem Befehl · Datenlage je Quelle mit Modus, Stand,
Status und Beleg · Audience-Kennzahlen mit Belegspalte · Markensichtbarkeit als ausdrücklich
**rollierendes** 28-Tage-Fenster · Verdiente Signale mit Lesehilfe · Nachweisregister mit
Herausgeber · Quartalsprogramm mit Reife · Messverlauf (letzte 6 Monate) · Betriebsregel, Grenzen und
nächste Fälligkeiten. Zusätzlich `--json <pfad>` für maschinelle Weiterverarbeitung (ohne
Suchanfragen, ohne Empfängerbezug).

### E. Tests: 7 → 31 (`scripts/tests/test_authority_engine.py`)

Die Tests halten beide Fehlerklassen fest – falsche Forderungen **und** falsche Zahlen:

* `test_evaluate_never_demands_the_running_month` (Regression zu #1076),
  `test_reporting_month_respects_lag_and_year_end`, `test_manual_export_is_only_demanded_after_its_due_date`
* `test_report_separates_zero_from_unknown`, `test_report_without_data_claims_nothing`,
  `test_gsc_import_without_query_column_keeps_brand_unknown`
* `test_repository_lage_derives_gsc_from_ledger` – der echte Oktober muss aus dem Ledger belegt sein
* `test_ledger_health_marks_stale_data`, `test_ledger_line_is_validated`,
  `test_not_active_source_with_signals_demands_contract_update`
* `test_declaration_must_not_claim_unproven_values`, `test_declaration_drift_becomes_action`
* `test_evidence_contract_rejects_own_domain_and_missing_publisher`,
  `test_measurement_contract_rejects_impossible_brand_totals`,
  `test_audience_import_rejects_unknown_fields_and_missing_provenance`,
  `test_asset_readiness_needs_all_five_artifacts`,
  `test_missing_methodology_anchor_is_a_contract_error`,
  `test_json_output_contains_no_search_queries`

---

## 4. Beweise (Befehle und Ausgaben)

```text
$ python3 scripts/authority_engine.py --selftest
Authority Engine: Selbsttest grün (Berichtsmonat, Ledger, Markenfenster, Belegform)

$ python3 -m unittest scripts.tests.test_authority_engine
Ran 31 tests in 0.06s
OK

$ python3 scripts/authority_engine.py --as-of 2026-11-05
Authority-Radar: 1 Maßnahme(n), AUTHORITY-RADAR.md
$ echo $?
1

$ python3 scripts/authority_engine.py --as-of 2026-11-04
# Berichtsmonat 2026-09 (Verzögerung respektiert) – keine Forderung für 2026-10
```

Vorher/nachher am selben Stichtag:

| Kennzahl | Ausgabe #1076 (vorher) | Ausgabe nach der Heilung |
|---|---|---|
| Handlungsbedarf | 2 × P2, beide unerfüllbar/teilweise falsch | 1 × P2 (echter, terminierter Mensch-Auftrag) |
| GSC-Import | „fehlt für 2026-11“ | **abgeleitet**: 2026-10, 0 Klicks, 240 Impressionen, 31/31 Tage |
| Ledger-Stand | nicht erwähnt | letzter Tag 2026-11-02 (3 Tage alt), Status frisch, Import `ok` |
| Markensichtbarkeit | „Markensuche fehlt“, sonst nichts | rollierend 2026-10-06–2026-11-02: 53 Top-Suchanfragen, 183 Impressionen, 0 markenbezogen – ausdrücklich kein Monatswert |
| Retention/Conversion | als fehlender Import gefordert | als `nicht_messbar`/`nicht_aktiv` mit Grund und Entscheidungsdatum geführt, nicht gefordert |
| Asset-Reife | nicht geprüft | 5/5 Kriterien maschinell geprüft |
| Messquellen belegt | „0 Importe“ | 1 von 2 erhebbaren Quellen belegt |

Sabotage-Proben (laufen in der Testsuite, schreiben nur in `tmp`): Klicks > Impressionen im Ledger,
Marken-Klicks > Gesamt-Klicks, eigene Domain als Beleg, fehlender Herausgeber, unbekannte
Audience-Kennzahl, fehlender Methodik-Anker, `nicht_aktiv` mit Aktivierungssignal, „belegt“-Deklaration
ohne Kennzahlen.

---

## 5. Was bewusst offen bleibt (und warum das kein Defekt ist)

* **P2: Newsletter-Aggregat 2026-10.** Der einzige echte Handlungsbedarf. Die Zahlen liegen im
  Newsletter-Studio/Resend; ein Dienstkonto-Export existiert im Repo nicht, und der Radar-Workflow
  läuft ohne diese Secrets. Aufwand: eine Vorlage erzeugen, zwei Zahlen ablesen, einlesen
  (`--template` → `--import-audience`). Alternativ ist ein belegter Leerzustand (`0` **mit**
  `provenance`) ein gültiger Messwert. Der Befund verschwindet damit nicht durch Weglassen, sondern
  durch einen Beleg.
* **Retention und Conversion bleiben `—`.** Ohne Besucherzähler bzw. mit abgeschaltetem Klickzähler
  wäre jede Zahl geraten. Diese Entscheidungen stehen mit Datum im Vertrag; nimmt ein Kanal den
  Betrieb auf, meldet der Radar die Abweichung.
* **Outreach wird nicht gezählt.** Der Radar listet nur die Vorlagen (`docs/outreach/…`) und
  behauptet weder Versand noch Wirkung.
* **Kein Workflow-Eingriff nötig.** `.github/workflows/authority-radar.yml` ruft weiterhin
  `--selftest`, die Unittests und `--check` auf, committet `AUTHORITY-RADAR.md` und synchronisiert
  genau ein Ticket. Die neuen Zustände (`P2` mit Fälligkeit, `P1` bei stehender Messung) passen in
  die bestehende Lifecycle-Logik; die Issue-Deduplizierung bleibt unverändert.

Ticketabschluss nach Hausmuster (vgl. #598 → #593): Die Heilung schließt den Radar-Vorgang mit
Nachweis, der verbleibende P2 steht mit Termin und Befehl in der jeweils aktuellen Ausgabe und wird
vom monatlichen Lauf weiterverfolgt.

---

## 6. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/authority_engine.py` | Messlage aus dem GSC-Ledger, Berichtsmonat mit Verzögerung, Quellenvertrag mit Modi, P1/P2-Trennung, Aktivierungs- und Deklarationsabgleich, Markenfenster, Belegprüfung, Asset-Reife, neuer Report, `--template`, `--json`, erweiterter Selbsttest |
| `scripts/tests/test_authority_engine.py` | 31 Vertragstests inkl. Regression #1076 und `null`-statt-`0`-Schutz |
| `data/authority_strategy.yaml` | Messvertrag (`sources` mit Modus, Fristen), Periodendeklaration auf `offen` mit Quelle, Asset-Regeln unverändert |
| `docs/AUTORITAET-DISTRIBUTION-RUNBOOK.md` | Monatsablauf neu: GSC automatisch, Newsletter-Export als einziger Handgriff, Grenzen und Modi erklärt |
| `AUTHORITY-RADAR.md` | neu erzeugte, belegte Ausgabe vom 05.11.2026 |
| `AUTHORITY-RADAR-1076-DAUERHEILUNG-HIGHEND-2026-11-05.md` | dieser Bericht |
