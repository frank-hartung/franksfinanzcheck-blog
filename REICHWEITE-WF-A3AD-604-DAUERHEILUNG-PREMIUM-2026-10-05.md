# Reichweite WF-A3AD · #604 – Dauerheilung

**Datum:** 05.10.2026  
**Auslöser:** Social-Autopilot, Run `37374009762`, als `failure` gemeldet; der
Run war bei der Nachprüfung tatsächlich `cancelled` und hatte keinen
ausgeführten Schritt.

## Befund

Das Alarming wertete den `workflow_run`-Webhook-Snapshot aus. Zwischen
Webhook-Zustellung und Verarbeitung kann GitHub einen Lauf noch als
Zwischenzustand liefern. Bei einem durch Concurrency/Scheduler verdrängten
Lauf wurde dadurch ein Phantom-Issue erzeugt, obwohl der finale Zustand
`cancelled` war. Das bestehende Phantom-Fangnetz prüfte zwar Jobs und Schritte,
aber erst nachdem es den möglicherweise veralteten Abschlusszustand aus dem
Payload übernommen hatte.

## Dauerhafte Reparatur

`.github/workflows/alert-on-failure.yml` lädt vor der Diagnose und vor jeder
Issue-Erstellung den Lauf über `actions.getWorkflowRun` live nach und verwendet
dessen aktuellen `conclusion`, Branch, Event und URL. Damit greift der bereits
vorhandene Schutz zuverlässig:

- `cancelled` ohne erfolgreich ausgeführten Schritt → verdrängter Wartelauf,
  **kein** Alarm;
- `cancelled` mit bereits ausgeführten Schritten → echter Abbruch, Alarm;
- `failure` und `timed_out` → weiterhin Alarm;
- fällt die Live-Abfrage aus, bleibt das Verhalten fail-open und der ursprüngliche
  Fehler wird nicht verschluckt.

Die Reparatur liegt vor Scoping, Job-Diagnose, Dedupe und Issue-Erzeugung. Ein
veralteter Webhook kann somit weder einen Phantom-Alarm erzeugen noch die
Dedupe-Sperre für einen späteren echten Produktionsfehler vergiften.

## Nachweis

- `python3 -m unittest scripts.tests.test_alert_scoping -v` → **18 Tests, 0 Fehler, 2 lokal übersprungen** (PyYAML nicht installiert; CI installiert es).
- `git diff --check` → **grün**.
- Bestehende Simulation deckt weiterhin Produktions-Scoping, Phantom-Filter,
  Diagnose und Dedupe ab.

**Ergebnis:** Die konkrete Meldungsklasse von WF-A3AD/#604 ist an der Ursache
behoben; nicht nur der einzelne Lauf wurde wiederholt.
