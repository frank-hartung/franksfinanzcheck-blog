# Qualitätsprüfung #759: Mitternachtsfehler im Reserve-Selbsttest

Stand: 15.10.2026 · Bezug: [Issue #759](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/759)

## Befund und Ursache

Der [Qualitätslauf 38657279385](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/38657279385)
auf `36a5e137` lief vom 14.10., 23:58:25 UTC, bis 15.10., 00:00:46 UTC.
Die Meldung entstand um 00:00:43 UTC. Gemeldet wurde:

```text
scripts/reserve_pool.py --selftest Exit 2:
Ein-Thema-Pool: 0 Artikel statt genau 1 – entweder verschenkte Kadenz oder Dublette
```

Der Fehler ließ sich vor der Änderung ohne Netz und ohne echte Artikel
reproduzieren:

| Eingestellte UTC-Uhr | Alter Selbsttest |
|---|---|
| 14.10.2026, 23:59:59 | grün |
| 15.10.2026, 00:00:00 | rot, identischer Befund |
| 15.10.2026, 00:00:30 | rot, identischer Befund |
| 15.10.2026, 00:00:59 | rot, identischer Befund |
| 15.10.2026, 00:01:00 | grün |
| 15.10.2026, 12:00:00 | grün |

Drei zusammenwirkende Stellen erklären das exakt:

1. Die Fixtures und `publish_to_min()` lasen `date.today()`.
2. `now_utc_iso()` zieht absichtlich eine Minute ab, damit ein veröffentlichter
   Artikel für Hugo nicht in der Zukunft liegt.
3. `publish_to_min()` verweigert einen Zeitstempel außerhalb des aktuellen
   Tages. In der ersten UTC-Minute gehört der Stempel noch zum Vortag.

**Die Produktionssperre arbeitete richtig. Der Test erwartete das Falsche.**
Der Helfer `_als_publikationstag()` erweiterte die Publikationstage auf alle
sieben Wochentage, löste aber den Datumswiderspruch nicht. Die bestehenden
Uhr-Proben verschieben außerdem die Tageszeit um 3:07 Stunden; sie garantieren
keine Probe genau an der Mitternachtsgrenze.

## Änderung

- Der Selbsttest nutzt die vorhandene `selftest_clock.uhr()` mit einem festen,
  echten Publikationstag: Montag, 28.09.2026, 12:00 UTC. Testdaten und
  Produktionsfunktionen erhalten dieselbe Uhr; der echte Minutenabzug läuft mit.
- Der kalenderverändernde Helfer entfällt. Auch seine beiden bisherigen
  Aufrufer in `test_reserve_pipeline.py` verwenden jetzt konsistente Testuhren
  und feste Fixture-Daten statt Echtzeit oder eines einzelnen Zeitstempel-Stubs.
- Ein eigener temporärer Root verhindert, dass echte Reserve-Zertifikate
  Testkandidaten priorisieren oder die Probe vom Produktionsbestand abhängt.
  Fixture-Verzeichnisse werden unter diesem Root angelegt und entfernt.
- Die Uhrbindungen werden auch bei Ausnahmen zurückgestellt. Das gilt für den
  Import- und den `__main__`-Pfad sowie für verschachtelte Uhr-Proben.
- Der Selbsttest prüft zusätzlich, dass ein gemeldeter Erfolg durch Validator
  **und** tatsächlichen LIVE-Testbestand belegt ist. Die gesperrte Dublette
  darf weder zum Validator gelangen noch ihre Datei verändern.

**Unverändert:** produktive Veröffentlichung, Mo/Mi/Fr-Regel, Tageslimits,
Minutenabzug, Tageswechsel- und Dublettensperren, Gate-Exitcodes, Workflows,
Alarmierung und Inhalte. Kein Skip, Retry oder Ausnahme-Eintrag kaschiert den
Fehler. Die erste UTC-Minute bleibt produktiv gesperrt; ab 00:01:00 ist ein
Zeitstempel desselben Tages wieder möglich.

## Dauerhafter Regressionsschutz

`scripts/tests/test_reserve_pool_clock.py` enthält 15 neue Tests mit
parametrisierten Unterfällen:

- exakte Mitternachtsgrenzen einschließlich des Meldezeitpunkts;
- alle Wochentage, Monats-/Jahreswechsel, Schalttag und UTC-Offsets +14/-12;
- strikte äußere Uhr, die jeden unkontrollierten Kalenderzugriff verweigert;
- unveränderter Publikationskalender während der echten Testveröffentlichung;
- Wiederherstellung von Uhr, Root und Umgebung bei Erfolg und Testabbruch;
- kein Lesen echter Zertifikate;
- Sabotageproben: keine Veröffentlichung, nur behaupteter Erfolg, fehlende
  Themensperre und deaktivierter Publikationskalender müssen weiter auffallen;
- echter CLI-Aufruf in einem frischen Prozess;
- unveränderte Produktionssperre vor 00:01, Freigabe ab 00:01, Mo/Mi/Fr und
  unveränderter Entwurf beim Tageswechsel.

Die vorhandene `unittest discover`-Verdrahtung führt diese Tests in der
Publication-Reliability-Prüfung automatisch aus, sowohl normal als auch mit
+97 Tagen. Die Selbsttest-Entdeckung prüft weiterhin `reserve_pool.py` mit
+97 und +1461 Tagen. Eine Workflow-Änderung ist dafür nicht erforderlich.

## Lokale Abnahme

Verwendet: Python 3.11.2, hash-gepinnte `requirements-ci.txt`, Hugo Extended
0.164.0 aus dem hash-gepinnten PyPI-Fallback der vorhandenen Install-Action.

| Prüfung | Ergebnis |
|---|---|
| Neue Regressionen | 15 Tests grün |
| Alle Selbsttests (`selftest_runner.py`) | 207 Wachen + 414 Uhr-Proben grün; kein C15-Schreibbefund |
| Reserve-Selbsttest unter strikter Uhr | grün |
| Gesamte Python-Suite | 3.194 Tests, 0 Fehler, 3 übersprungen |
| Gesamte Python-Suite mit +97 Tagen | 3.194 Tests, 0 Fehler, 5 übersprungen |
| Governance-Vertrag `--quick` | alle 36 Regeln erfüllt |
| Linkcheck-Reporting und Hugo-Build-Verträge | 23 Unit-Tests grün |
| Hugo-Build-Vertrag | H1–H8 erfüllt |
| Hugo-Build über die gemeinsame Action | grün, 98 Seiten |
| Newsletter-Capture / Versandprüfung | grün / 100 von 100 Punkten |
| Interne Links | 3.191 geprüft, 0 defekt |
| Schema-/SEO-Gate | 133 Seiten, 64 Money-Pages; 0 harte Funde, 0 Hinweise |

Die drei regulären Skips betreffen optionale Umgebungsnachweise: jsdom,
hunspell und den zusätzlich erzeugten Pagefind-Suchindex. Unter fremder Uhr
werden außerdem die beiden ausdrücklich echtzeitabhängigen Bestandsproben
(Newsletter/Reserve) ausgelassen. Das sind bestehende Skip-Regeln, keine
Änderung dieser Reparatur. Alle neuen Tests laufen ohne Skip.

Reproduktion der wichtigsten Abnahmeschritte nach Installation der bestehenden
CI-Abhängigkeiten:

```bash
python3 -m unittest scripts.tests.test_reserve_pool_clock -v
python3 scripts/reserve_pool.py --selftest
python3 scripts/selftest_clock.py --trap scripts/reserve_pool.py --strikt
python3 scripts/selftest_runner.py
python3 -m unittest discover -s scripts/tests -v
python3 scripts/selftest_clock.py --trap-discover scripts/tests --offset 97
python3 scripts/governance_contract.py --quick
python3 scripts/hugo_build_vertrag.py
```

Die lokalen Abnahmeergebnisse sind kein Nachweis einer Auslieferung auf `main`.
Der PR muss regulär geprüft und zusammengeführt werden; das bestehende
Qualitäts-Gate bestätigt danach den Produktionsstand. Echte Inhalte,
Zertifikate und Beweis-Ledger sind nicht Teil des Änderungssatzes.
