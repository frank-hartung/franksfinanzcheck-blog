# YMYL-Prüfqueue #826 – Nachprüfung und Betriebshärtung

Stand: 25.10.2026. Ergänzt den Reparaturbericht vom 24.10., ersetzt keine
fachliche Freigabe und bescheinigt keine erneute Online-Quellenprüfung.

## Verifizierter Bestand

`editorial_review_gate.py --all --strict`: **95 Artikel, 10 Hochrisiko,
10 freigegeben, 0 blockiert**, Exit 0. Keine Artikel, Prüfpersonen, Daten oder
Siegel verändert. Die ursprünglichen vier offenen Freigaben sind im aktuellen
Checkout bereits behoben; ein erneutes Versiegeln wäre unnötig.

## Verbliebene Betriebsfehler behoben

- Der Ticket-Job läuft auf einem anderen Runner als das Gate. Er lädt jetzt den
  Gate-Bericht als Artefakt herunter, statt eine dort nicht vorhandene Datei
  zu lesen. Fehlt der Bericht, wird dies ausdrücklich gemeldet. Shell-Fehler
  werden nicht mehr durch fehlendes `set -e` verschluckt.
- Automatische Queue-Erledigung verlangt zusätzlich einen erfolgreichen
  Gate-Job und `--require-complete` der Belegketten-Wache: Unklare Abrufe und
  Weiterleitungen bleiben Prüfaufträge, statt eine Erledigung zu erlauben.
  Der bisherige Diagnosemodus `--strict` bleibt kompatibel: Netzstörungen
  werden nicht als tote Quellen ausgegeben.
- Unlesbare Artikel verschwinden nicht mehr als leere Quellenlisten aus dem
  Ergebnis: Sie erzeugen einen blockierenden Frontmatter-Befund.
- Jede exakte URL wird je Lauf nur einmal abgerufen; Befunde bleiben separat
  jedem betroffenen Artikel und jeder Quellen-ID zugeordnet.
- HTTP 403/429 und alle 5xx werden konsistent als unklar behandelt, unabhängig
  davon, ob der Abruf einen Status zurückgibt oder HTTPError auslöst.

`actions/download-artifact` ist auf den über die GitHub-API geprüften Commit
von v7.0.0 gepinnt, nicht auf einen veränderlichen Tag.

## Nachweise

Ausgeführt in isolierter `.venv` mit PyYAML:

- Gate-Selbsttest: bestanden.
- `test_editorial_review_gate.py`: 17 Tests bestanden.
- `test_ymyl_write_contract.py`: 10 Tests bestanden.
- `test_belegketten_wache.py`: 12 Tests bestanden, einschließlich neuer
  Regressionen für Lesefehler, einmalige Abrufe, HTTP-Klassifizierung und
  fail-closed Queue-Erledigung.
- `git diff --check`: bestanden.

## Grenzen / Betrieb

Die Sandbox erlaubt ausgehende Verbindungen nicht zu den zitierten
Verbraucher-/Primärquellen. Ein erneuter realer Online-Abgleich wird daher
hier **nicht behauptet**. Den liefert der bestehende planmäßige bzw. manuelle
Workflow nach Übernahme der Änderungen. Inhaltliche Quellenänderungen unter
identischer URL erkennt die reine Erreichbarkeitsprüfung weiterhin nicht;
fachliche Nachprüfung bleibt erforderlich. Das Issue wird in diesem Lauf
nicht manuell geschlossen. Eine erfolgreiche Online-Prüfung und die Übernahme
der Änderungen sind noch ausstehend.
