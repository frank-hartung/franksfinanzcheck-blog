# Bot-Watchdog #614: Reserve wieder am Ziel, Fortschritt bis zur Freigabe führen

Stand: 08.10.2026 · Ergänzung zu `BOT-WATCHDOG-614-DAUERHEILUNG-PREMIUM-2026-10-07.md`

## Ergebnis in dieser Arbeitskopie

**6/6 zertifizierte Kandidaten bei 15 Reserveentwürfen.** Alle 15 wurden
mit dem echten `reserve_readiness.certify_one` erneut geprüft, nicht mit
Stub-Modell oder simuliertem Publikations-Gate. Das Ergebnis liegt in
`data/reserve-readiness.json`; `recert.renewed` nennt sämtliche 15 Slugs.

- Hugo Extended **0.164.0**, Hunspell **1.7.2** mit deutschem Wörterbuch;
  `reserve_recert.gate_verfuegbar()` bestätigt die Messkette.
- `quality_score` und `publish_gate` im unveränderten **STRICT/dry-run**,
  inklusive Hugo-Build und gerenderter Affiliate-Prüfung.
- Alle Entwürfe nach der Messung bytegenau wiederhergestellt; sämtliche
  Zertifikats-Hashes mit den tatsächlichen Dateien abgeglichen.
- `reserve_gate.py`: **grün, 6/6, frisch**.
- `reserve_recert.py --check`: **kein Drift**.
- Keine Live-Artikel bearbeitet, nichts veröffentlicht. Die neun übrigen
  Kandidaten bleiben ehrlich blockiert; sie werden nicht als READY gezählt.

| Frisch zertifizierter Kandidat (Kurzname) | Flesch |
|---|---:|
| 7 Gewohnheiten für finanzielle Freiheit | 65,8 |
| Handyvertrag kündigen | 60,8 |
| Smart-Home-Geräte / Stromrechnung | 62,7 |
| Campingurlaub 2026 | 60,8 |
| DSL-Anbieter wechseln | **63,1** |
| Urlaub sparen | 60,6 |

Das ist ein **lokaler Produktions-Gate-Nachweis**, kein neuer GitHub-
Produktionslauf. Die Änderungen müssen noch zusammengeführt werden. Der
anschließende reguläre oder Watchdog-Recovery-Lauf auf `main` bestätigt den
Betrieb samt Persistierung und Alarmabgleich. Der Produktionsworkflow wurde
hier weder auf einen anderen Ref umgebogen noch vorzeitig ausgelöst.

## Was gegenüber den bisherigen Reparaturen noch fehlte

Der Issue-Body meldete ursprünglich 2 bereit, Ziel 6, Alarm unter 4. Im
Checkout standen bereits **5** bereit. Der zuletzt per GitHub API abrufbare
Reservelauf `37645894042` war dagegen weiterhin am Schritt „Stock shortage
must not look successful“ gescheitert. Die Archiv-Logs waren aus dieser
Umgebung nicht abrufbar; der Schrittstatus wurde über die Jobs-API gelesen.

Die vorhandenen Satz-Heiler-Reparaturen lösen die Textbearbeitung, aber
nicht deren vollständige Steuerung:

1. **Teilfortschritt wurde als Stillstand behandelt.** Der Satz-Heiler darf
   sichere Sprünge ab +0,3 Flesch unterhalb 60 speichern. `reserve_converge`
   sah jedoch ausschließlich READY-Anzahl und Poolgröße. Bei gleich großem
   Pool beendet etwa 58,0 → 59,0 die Arbeit nach einer Runde. Der grobe
   Lesbarkeits-Score kann dabei unverändert 80/100 bleiben.
2. **Das Zeitbudget galt dreifach.** Das Restbudget wurde nur am Anfang
   einer Runde berechnet und an alle drei Prozesse identisch übergeben.
   `max(300, …)` gewährte sogar bei fast leerem Budget neue fünf Minuten.
3. **Timeouts ließen Kindprozesse zurück.** `subprocess.run(timeout=…)`
   beendet den direkten Prozess, nicht dessen weitere Heiler-Kinder.
4. **Eingerückte Sätze hatten erneut falsche Zeiger.** Der Zeilen-Einzug
   wurde zweimal addiert. Die Schutzprüfung verwarf dadurch korrekte
   Ersatzvorschläge statt sie im Body einzusetzen.

## Dauerhafte Änderungen

- Zertifikate enthalten jetzt je Kandidat den tatsächlichen **Flesch-Wert
  der gehashten Originalbytes**, gemessen mit der bestehenden Messfunktion.
  Alte Zertifikate ohne dieses Feld bleiben lesbar; fehlende Messwerte
  werden nicht als Fortschritt interpretiert.
- Die Konvergenz erkennt den messbaren Sprung desselben blockierten
  Kandidaten mit verändertem Hash. Schwelle und Mindestfortschritt kommen
  aus den vorhandenen Quellen. Hashwechsel allein, neue Slugs, Rückschritte,
  NaN oder unbekannte Werte reichen nicht. **Teilfortschritt bleibt ungleich
  READY**; Runden- und Kostenbegrenzungen bleiben bestehen.
- Vor jedem Prozess wird das verbleibende Gesamtbudget neu bestimmt.
  Nach Ablauf startet kein weiterer Schritt. Timeouts beenden die Runde;
  unerwartete Zertifizierungs-Exitcodes ergeben keinen Erfolg aus einem
  alten Zertifikat. Rückgabecodes und Teilfortschritte stehen im Bericht.
- Prozesse laufen in einer eigenen Prozessgruppe. Beim Timeout werden
  Eltern und Kinder beendet (TERM, maximal fünf Sekunden Aufräumfrist,
  anschließend KILL auch für TERM-ignorierende Kinder).
- Die doppelte Addition des Einzugs im Satz-Finder ist entfernt.
- Der DSL-Entwurf wurde redaktionell an neun Stellen vereinfacht:
  **59,5 → 63,1**, Qualitäts-Score nach erneuter Messung **0,982**.
  Keine Schwelle, kein Zielbestand und keine Gate-Regel wurden gelockert.

## Regressionen und Nachweise

Neue Datei: `scripts/tests/test_reserve_convergence_progress.py` mit
**13 Tests**, automatisch durch den vorhandenen CI-Discover erfasst.

| Prüfung | Ergebnis |
|---|---|
| Gesamtsuite `unittest discover -s scripts/tests` | **2.165 Tests OK**, 1 Skip |
| Neue Regressionen + Satz-Heiler + Nachzertifizierung | **42 Tests OK** |
| Abschlusslauf einschließlich bestehender Reserve-Pipeline-Tests | **171 Tests OK** |
| Gesamte Uhr-Probe +97 Tage, ohne vorgebautes `public/` (wie im CI-Testjob) | **2.163 Tests OK**, 7 Skips |
| Neue Regressionen unter +97 und +1461 Tagen | jeweils **13 Tests OK** |
| `reserve_converge --selftest`, einschließlich neuer Fortschritts-/Budgetproben | grün, auch unter +97/+1461 Tagen |
| `satz_heiler --selftest` | grün |
| `reserve_healer_coverage --selftest` | grün |
| `integrity_guard --gate` | grün, 47 Kerndateien unverändert |
| Echter Vollnachtest aller 15 Kandidaten | **6 READY**, 9 weiterhin blockiert |
| `reserve_gate` / `reserve_recert --check` | grün / kein Drift |

**Abgrenzung der Uhr-Probe:** Mit dem zuvor für die Zertifizierung gebauten
Echtzeit-`public/` scheiterte ein bestehender, fachfremder Saisontest:
Der Herbst-Build wurde gegen die um 97 Tage vorgestellte Winter-Uhr geprüft.
Der reguläre Gesamttest mit passender Echtzeituhr war grün. Für die vollständige
Fremduhr-Probe wurde deshalb wie im CI-Testjob ohne vorgebautes `public/`
geprüft; danach wurde der Build wiederhergestellt. Saisoncode und dieser
Integrationstest wurden nicht geändert. Die neuen Regressionen bestehen
unabhängig davon unter beiden Fremduhren.

Die Timeout-Regression startet einen echten Enkelprozess, der SIGTERM
ignoriert und später eine Datei schreiben würde. Nach dem Timeout wird
bewiesen, dass er nicht weiterläuft und die Datei nicht geschrieben hat.
Tests und lokale Gate-Nachweise schreiben ihre Audit-/Chronikdaten nach
`.cache/`, nicht ins versionierte Produktions-Ledger.

## Betriebsabnahme nach dem Merge

1. `content-reserve.yml` regulär laufen lassen oder den bestehenden
   Watchdog-Recovery-Dispatch nutzen; keine Workflow-Schutzbedingungen ändern.
2. Frisches Zertifikat: mindestens Zielbestand 6, passende Datei-Hashes,
   Reserve-End-Gate grün, Sicherungs-Push erfolgreich.
3. Watchdog-Abgleich ohne maschinellen Restbefund; #614 nicht allein aufgrund
   einer grünen Unit-Test-Suite als produktiv erledigt behandeln.

Die Live-KI-Provider und der vollständige GitHub-Produktionslauf wurden hier
nicht ausgeführt. Deren Erfolg wird nicht aus den lokalen Tests abgeleitet.
