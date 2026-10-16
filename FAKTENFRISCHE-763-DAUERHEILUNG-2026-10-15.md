# Faktenfrische #763 – redaktionelle Korrektur und Regression

Stand: 16. Oktober 2026 (Nachlesung unten); Erstkorrektur 15. Oktober 2026. Umfang: die zwei Entwürfe aus Issue #763 und die Prüfanweisung der Faktenfrische. Keine Veröffentlichung, keine Freigabe und kein Schließen des Issues vorgenommen.

## Die neun Befunde

| Nr. | Befund | Umsetzung |
|---|---|---|
| 1 | Entlüften spare pauschal 5 % | Quote und daraus abgeleitete Modellrechnung entfernt; Wirkung nur bei tatsächlicher Luftproblematik, keine garantierte Ersparnis |
| 2 | Raumthermostat pauschal 20 °C | Nur möglicher Ausgangspunkt; Nutzung, Wärmebedarf, Gebäude und Feuchtigkeit ausdrücklich berücksichtigen |
| 3 | Router im Standby mit 5 W | Gerätebehauptung entfernt; Betrieb und Standby unterschieden, Messung und Herstellerangaben statt pauschaler Werte |
| 4 | CHECK24 durch Behördenquelle gestützt | Werbung und fachliche Quelle getrennt; keine behördliche Empfehlung, keine vollständige Marktübersicht oder Bestpreisgarantie behauptet |
| 5 | Reiseangebote 2026 preislich stabilisiert | Unbelegte Marktbehauptung entfernt; konkrete Angebote für Reisedatum und Leistungsumfang vergleichen |
| 6 | Bank-Cashback als wesentliche Budgetquelle | Keine pauschale Verfügbarkeit behauptet; optionale Rückvergütung mit Bedingungen, Gebühren, Grenzen und Datenschutzprüfung |
| 7 | Gesponserter Mietwagenvergleich fachlich belegt | Werbelink ausdrücklich von der Verbraucherzentrale abgegrenzt; keine unbelegten Preis- und Transparenzvorteile |
| 8 | Digitale Vertragstransparenz als Trend 2026 | Zeitgebundene Behauptung entfernt; stattdessen praktische Vertrags- und Fristenübersicht |
| 9 | Pauschale Cashback-Rate 2 % | Rate und sämtliche Folgehochrechnungen entfernt; 500-€-Modell ohne Cashback, ausdrücklich frei gewählte Annahmen |

## Zusätzlich behoben

- Faktor-zehn-Fehler bei Wattstunden: 3 × 5 W × 24 h × 365 = 131.400 Wh = 131,4 kWh; bei angenommenen 0,30 €/kWh: 39,42 €. Separates 8-Stunden-Beispiel: 13,14 €.
- Tarifbeispiele nennen Grundpreis, Voraussetzungen und keine aktuellen Marktangebote. 105 € Differenz sind 10 % der angenommenen Strom-Verbrauchskosten, nicht 8 % einer unbekannten Gesamtrechnung.
- Keine pauschalen Warmwassertemperaturen oder Warmwasser-Sparquoten; Hygiene/Legionellen und Fachzuständigkeit ergänzt. Keine Heimwerkerempfehlung an Brennern oder Gasleitungen.
- Keine pauschale Kündigung von Lebensversicherungen zugunsten des Urlaubsbudgets; Schutz und mögliche Nachteile berücksichtigt.
- Unbelegte 200–300-€-Sparratenempfehlung für Familien und pauschale Sicherheitszusage zu Cashback-Apps entfernt.
- Erfunden wirkendes Veröffentlichungsdatum `2024-01-01` der Bundesnetzagentur-Übersicht entfernt, nicht durch ein anderes Datum ersetzt.
- Beschreibung, Pinterest-Text, Kurzantwort und sichtbare redaktionelle Einordnung konsistent angepasst. `lastmod` dokumentiert den tatsächlichen Texteingriff. Vorhandenes `faktencheck` nicht vordatiert oder fortgeschrieben.

## Dauerhafte Absicherung

`scripts/tests/test_faktenfrische_763.py` enthält sieben Offline-Regressionstests (Stand 15.10.; am 16.10. auf Bedeutungs-Invarianten umgestellt und auf 16 Tests erweitert – siehe Nachlesung) zu den konkreten Fehlern, Rechenwerten, Quellenabgrenzungen, Metadaten, GEO-Kriterien und dem Prüfvertrag. Die vorhandene Publication-reliability-CI entdeckt das Modul über `unittest discover`; Änderungen an Content und Scripts lösen diesen Workflow bereits aus.

Der Systemprompt in `scripts/faktenfrische.py` unterscheidet nun ausdrücklich Modellannahmen, Tatsachenbehauptungen und Werbung. Fehlende Erwähnung in einer Übersichtsseite darf nicht als Widerlegung dargestellt werden. Modellannahmen werden auf Rechnung, Einheiten und Kennzeichnung geprüft. Werbung erfordert keine behördliche Empfehlung, darf aber keine unbelegten Preis- oder Vollständigkeitsvorteile behaupten. Quellen-Publikationsdaten dürfen nicht erfunden werden. URL-Allowlist, Antwortvalidierung und Schreibgrenzen bleiben unverändert.

Diese Regeln verbessern die Prüfanweisung, garantieren aber nicht die Befolgung durch ein Sprachmodell. Die Offline-Tests sind gezielte Regressionen, kein allgemeiner automatischer Wahrheitsbeweis.

## Nachweise

- `.venv/bin/python -m unittest scripts.tests.test_faktenfrische_763 scripts.tests.test_publish_gate_faktenfrische`: **12/12 grün** (Nachlesung 16.10.: die zwei 763er-Tests mit Exaktzeichenketten drifteten nach der #766-Gliederung und sind durch die invarianten Tests ersetzt – aktuelle Zahl 21/21).
- `.venv/bin/python scripts/faktenfrische.py --selftest`: **23/23 grün**.
- Reale Artikel über `lade_artikel()` und `geo_reife()` eingelesen: jeweils **6/6 Kriterien, 100 %**. Das ist Strukturreife, keine Bestätigung aller Sachinformationen.
- `zeit_rechtschreibung.py --offline`: **58 veröffentlichte Artikel, 0 Funde**.
- `seo_audit.py`: **58 veröffentlichte Artikel, 0 Probleme** (ein bestehender interner Linkhinweis bei einem anderen Artikel).
- `editorial_review_gate.py --published --strict`: **58 veröffentlichte Artikel, 0 blockiert**.
- `git diff --check`: sauber.

## Grenzen und Freigabe

Keine neue Live-Recherche bei Verbraucherzentrale oder Bundesnetzagentur: Diese Hosts sind in der Arbeitsumgebung nicht für direkten Internetzugriff freigegeben. Deshalb keine neuen vermeintlich aktuellen Marktdaten und keine erfundenen Detailquellen. Die bekannten Übersichtsquellen bleiben ausdrücklich als Einstieg eingeordnet, nicht als Universalbeleg. Historische Dossiers, Queue und Faktenfrische-Historie bleiben als ursprüngliche Prüfbeweise unverändert.

Hugo ist lokal nicht installiert; kein vollständiger Hugo-Build oder Browsernachweis. Die komplette Repository-Testsuite wurde nicht ausgeführt. Bestandsprüfungen mit `--published` erfassen die beiden Entwürfe nicht; diese wurden separat mit dem neuen Testmodul und dem echten Faktenfrische-Parser geprüft.

Beide Artikel bleiben `draft: true`, die redaktionelle Prüfung bleibt ausstehend. Es wurde kein Prüfsiegel ausgestellt. Der Heizartikel hat derzeit rund 9.100 Body-Zeichen; ein gegebenenfalls erforderliches 10.000-Zeichen-Publish-Minimum wird damit nicht als erfüllt behauptet. Reguläre Freigabe, Publish-Gates und erneute externe Fachprüfung bleiben erforderlich. Die Änderung ist die Korrektur der gemeldeten Befunde, keine vorgetäuschte Veröffentlichungsreife.

## Nachlesung 2026-10-16 – Regression nachgeschärft, Gates geheilt

Auftrag: die neun Befunde dauerhaft auf Highend-Level einer Profi-Agentur beheben.
Der 15.10.-Stand blieb inhaltlich unangetastet; diese Nachlesung schließt die
drei Befunde, die der 15.10.-Lauf selbst als offen markiert hatte.

### 1. Die Regression war blind geworden (Kern des „dauerhaft“)

Die Tests vom 15.10. prüften Exaktzeichenketten. Nach den Folgeläufen
(#766-Gliederung, Lesbarkeits-Glättung, „Euro“ statt „€“) standen zwei von
sieben Tests rot – ohne dass ein Sachfehler zurückgekehrt war. Ein Test, den
jede harmlose Umformung bricht, schützt nichts; er provoziert nur seinen
eigenen Abriss. `scripts/tests/test_faktenfrische_763.py` ist jetzt auf
Bedeutungs-Invarianten verankert:

- verneinungstolerante Satzprüfung pro Befund (B1–B9): die neun gemeldeten
  Fehlbehauptungen dürfen behauptend nie zurück, Leserfragen und Dämpfungen
  bleiben erlaubt;
- Rechenzellen werden nachgerechnet (131,4 kWh = 15 W · 24 h · 365 d ÷ 1.000;
  39,42 € = 131,4 · 0,30; Reise-Summe 120 + 12 × 25 + 80 = 500), unabhängig
  von der Zahlen-Schreibweise;
- Werbe-/Quellentrennung auf Absatz- und Satzebene inkl. Reihenfolge der
  Offenlegung vor dem ersten `/go/`-Link;
- Metadaten-Korridor: `lastmod` ≥ Eingriffsdatum, `faktencheck` nicht
  vorgeschrieben fortgeschrieben, keine erfundenen Quellen-Daten,
  description 70–165 Zeichen, GEO-Reife 6/6;
- Gate-Parität: beide Entwürfe müssen Zeichenkorridor (≥ 10.000),
  Lesbarkeits-Harte (Score ≥ 75, Flesch ≥ 60) und harte
  Textverständnis-Regeln (R2–R17) bestehen – genau die Gates, an denen der
  Reiseartikel am 16.10. von der Kadenz gehalten wurde;
- Queue-Hygiene: `faktenfrische_queue.json` darf die zwei Slugs nicht mehr als
  offen führen.

Sabotage-Nachweis statt Vertrauenssache: alle 13 wiederinjizierten
Fehlvarianten (die neun Befunde, manipulierte Summenzelle, Faktor-Zehn-
Wattleer, geändertes Rechenzellenergebnis, entfernter FAQ-Anker) werden von der
Suite gefangen; 12/13 fing bereits der erste Entwurf, die Lücken
(„Mietwagenvergleich“ als Kompositum, Tabellen-Arithmetik) sind geschlossen.
Suite: 16/16 grün.

### 2. Lesbarkeits-Hemmung des Reiseartikels behoben

Der Reiseartikel war am 16.10. 04:36 UTC vom Kadenz-Gate zurückgestuft worden
(`cadence_grund`: Score 65/100, Flesch 40). Heilung durch glättende Redaktion,
nicht durch KI-Umschreibung: kürzere Wörter und Sätze, zwei Tabellenzeilen
gestrafft, lange Absätze zerlegt, je ein neuer Abschnitt zur Prüfung
unterwegs anfallender Gebühren und ein Monatscheck, dazu ein
„Was dieser Ratgeber nicht kann“-Abschnitt. Ergebnis: **100/100, Flesch 65,2**
(zuvor 65/100 · 40,0), 11.631 Zeichen (Floor erfüllt; unter-Optimum ist
Information, kein Gate-Befund). Alle neun Befunde und alle Sicherungen des
15.10. bleiben wortweise oder im Sinne erhalten – der neue Regressionstest
belegt es.

### 3. Heizartikel auf Korpus-Level geglättet

Absatzketten über vier Sätze aufgelöst (R5), Satzanfangs-Echos „Auch/Die/Ein“
unter die Meldeschwelle gedrückt (R4), die zwei doppelten Transparenz-Blöcke zu
einer korrekten Offenlegung zusammengeführt, die Attrappen-Überschrift
„## FAQ – …“ vor den echten „## Häufige Fragen“ entfernt (doppelter
FAQ-Anker, kein Mehrwert), die Weiterlesen-Punkte auf die drei existierenden
Artikel verlinkt und die doppelte description-Doppelpunkt-Kette bereinigt.
Ergebnis: **100/100, Flesch 75,0**, 12.046 Zeichen – damit erstmals im
Optimum-Band; das im 15.10.-Lauf bezweifelte 10.000-Zeichen-Minimum ist
überschritten.

### Nachweise 2026-10-16

- `python3 -m unittest scripts.tests.test_faktenfrische_763`: **16/16 grün**;
  mit `test_publish_gate_faktenfrische`: **21/21 grün**.
- Sabotage-Matrix 13/13 gefangen (siehe oben), danach Suite wieder grün.
- `faktenfrische.py --selftest`: 23/23 · `readability_check.py --selftest`: OK.
- `seo_audit.py`: 61 Artikel, 0 Probleme · `zeit_rechtschreibung.py --offline`:
  61 Artikel, 0 Funde · `check_length.py --include-drafts`: beide Entwürfe
  ohne Verstoß · `editorial_review_gate.py --published --strict`: 0 blockiert.
- `textverstaendnis_guard` (harte Regeln): bei beiden Artikeln ohne Befund.
- Vollständige Suite nach Rebase auf `origin/main` (6bbc805):
  **keine neuen Fehler** gegenüber dem unveränderten Main; zwei auf Main rote
  Alt-Tests des 15.10. (Zeichenketten-Drift) werden von dieser Nachlesung grün.

### Grenzen

- `draft: true` bleibt; die Park-Fahne `cadence_grund` des Reiseartikels ist
  historischer Beleg und wird nicht manuell überschrieben – die Hemmung löst
  die Kadenz, sobald Freigabe erteilt wird.
- Keine Live-Recherche bei Verbraucherzentrale/Bundesnetzagentur (Hosts in der
  Arbeitsumgebung nicht freigegeben); keine neuen Marktdaten, keine erfundenen
  Detailquellen.
- Die Tests garantieren Rückfallschutz gegen die gemeldeten Befunde – sie sind
  kein allgemeiner Wahrheitsbeweis und ersetzen nicht die redaktionelle
  Freigabe oder eine erneute externe Fachprüfung.
