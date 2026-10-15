# Faktenfrische #763 – redaktionelle Korrektur und Regression

Stand: 15. Oktober 2026. Umfang: die zwei Entwürfe aus Issue #763 und die Prüfanweisung der Faktenfrische. Keine Veröffentlichung, keine Freigabe und kein Schließen des Issues vorgenommen.

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

`scripts/tests/test_faktenfrische_763.py` enthält sieben Offline-Regressionstests zu den konkreten Fehlern, Rechenwerten, Quellenabgrenzungen, Metadaten, GEO-Kriterien und dem Prüfvertrag. Die vorhandene Publication-reliability-CI entdeckt das Modul über `unittest discover`; Änderungen an Content und Scripts lösen diesen Workflow bereits aus.

Der Systemprompt in `scripts/faktenfrische.py` unterscheidet nun ausdrücklich Modellannahmen, Tatsachenbehauptungen und Werbung. Fehlende Erwähnung in einer Übersichtsseite darf nicht als Widerlegung dargestellt werden. Modellannahmen werden auf Rechnung, Einheiten und Kennzeichnung geprüft. Werbung erfordert keine behördliche Empfehlung, darf aber keine unbelegten Preis- oder Vollständigkeitsvorteile behaupten. Quellen-Publikationsdaten dürfen nicht erfunden werden. URL-Allowlist, Antwortvalidierung und Schreibgrenzen bleiben unverändert.

Diese Regeln verbessern die Prüfanweisung, garantieren aber nicht die Befolgung durch ein Sprachmodell. Die Offline-Tests sind gezielte Regressionen, kein allgemeiner automatischer Wahrheitsbeweis.

## Nachweise

- `.venv/bin/python -m unittest scripts.tests.test_faktenfrische_763 scripts.tests.test_publish_gate_faktenfrische`: **12/12 grün**.
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
