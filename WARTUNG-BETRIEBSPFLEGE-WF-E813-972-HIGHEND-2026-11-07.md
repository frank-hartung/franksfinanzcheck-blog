# Wartung · Betriebspflege · WF-E813 / #972 · 07.11.2026

## Ausgangslage und Geltungsbereich

Der letzte hier ausgewertete produktive Sicherheits-Wache-Lauf `42230276255`
vom 06.11.2026 meldet F-01 als BEFUND (keine Cloudflare-Proxy-Spuren) und den
Worker als STOERUNG (alter Deploy bzw. unvollständiges authentifiziertes
Betriebsbild). Die seit 05.11. vorhandene Annotation-Budget-Heilung ist bereits
wirksam und wurde nicht neu gebaut. Die Sandbox kann die Website und die
Cloudflare-API nicht live erreichen; das ist kein aktueller Produktionsbeweis.
Der Issue bleibt offen; diese Änderung kommentiert oder schließt ihn nicht.

## Änderung: kontrollierte F-01-Selbstheilung

- `scripts/live_selbstheilung.py` validiert den F-01-Messvertrag und die
  Übereinstimmung von JSON und Markdown, verlangt beide erfolgreich gemessenen
  Originalziele, einen ausdrücklichen Betreiber-Opt-in, ein separates Zone-Token
  und die konkreten B7-Textbausteine. Andere Klassen, unvollständige oder
  widersprüchliche Nachweise, fehlende Rechte/Freigabe und B7 blockieren.
- Nach einem API-Vorherbefund führt das bereits vorhandene Werkzeug
  `cloudflare_edge_freigabe.anwenden` höchstens einen Versuch aus; es schützt
  die Reihenfolge Regel → SSL → DNS, erhält `strict` und misst via API gegen.
  Danach erfolgt eine unabhängige öffentliche Header-Gegenmessung. Ist die API
  schon im Soll, wird nicht auf Verdacht geschrieben. Fehler können
  Teiländerungen hinterlassen; ein Rollback wird nicht behauptet.
- Der Workflow bewahrt den ursprünglichen Auswerte- und Abschlussvertrag:
  Heilung findet **nach** dem Abschlussversuch statt, nur bei Zeitplan/Zuruf auf
  `main` nach den Quellseiten-Tests. Ein ursprünglich roter Lauf wird durch die
  Heilung nicht grün; ein späterer vollständiger Live-Lauf muss Header, Worker
  und Abschlussblocker erneut belegen. Ein Laufprotokoll ohne Secrets wird im
  Artifact 90 Tage vorgehalten; ein Abbruch kann dessen Upload verhindern.
- Der Heiler benutzt ausschließlich `CF_EDGE_HEAL_TOKEN`, nicht den für
  Workers AI verwendeten `CLOUDFLARE_API_TOKEN` und nicht den Deploy-Token.
  Keine automatische Änderung von Worker-Deploys, GitHub-Environments, Secrets,
  Datenschutztexten oder Issues. Die Dokumentation steht im Runbook A1c.

## Offen / Betreiberpflichten

1. B7 rechtlich und operativ prüfen, den korrekten Text im Repository und dessen
   Veröffentlichung sicherstellen. Der aktuelle lokale B7-Check meldet noch
   Vor-Proxy-Aussagen. Die Codeprüfung beweist weder die Veröffentlichung noch
   die rechtliche Eignung und ist absichtlich nicht hinreichend für die Freigabe.
2. Erst nach Prüfung ein auf die Zone begrenztes eigenes Actions-Secret
   `CF_EDGE_HEAL_TOKEN` mit den im Runbook genannten Rechten einrichten und
   `CF_EDGE_AUTOHEAL=true` bewusst setzen. Ob ein entsprechendes Secret derzeit
   existiert, konnte wegen fehlender GitHub-Administrationsrechte nicht geprüft
   werden. Ohne beides bleibt die Automatik bei Befund gesperrt und nennt die
   Betreiberaufgabe.
3. Worker-Environment und Deployment wie in A1b/D2 durch den Betreiber
   einrichten/freigeben. Dann einen vollständigen Live-Lauf auf `main` ausführen.
   Erst dessen echter Erfolg kann #972 gemäß bestehendem Workflow schließen.

Es wurden keine Produktionsregeln geändert, keine Secrets gelesen oder gesetzt,
kein Worker deployt und keine GitHub-Environment-Einstellungen verändert.

## Offline-Nachweise

Die neue Testsuite arbeitet ausschließlich mit Netz-/API-Attrappen: gültige
Heilung und Gegenmessung, unveränderte Ursprungsmessung, fehlende Freigabe oder
B7, Klassen-/Ziel-Sabotage, API-Soll/Störung, Teilfehler, fehlender Auditpfad,
CLI-Berichtswiderspruch sowie Workflow-Verdrahtung. Das ist kein Live-Test.

- `npm run test:sicherheit`: erfolgreich (bestehende 334 + 43 Tests sowie neue
  Selbsttests; ein bestehender Test übersprungen).
- `selftest_runner.py` mit hashgesperrten CI-Abhängigkeiten: 275 Wachen und
  550 Uhr-Proben erfolgreich.
- `governance_contract.py --quick`: 46 Regeln erfüllt.
- `trigger_wache.py --check`: 100 Workflows, 0 Befunde.
- `skript_syntax_wache.py`: 667 Dateien erfolgreich.
- `integrity_guard.py --gate`: 55 versiegelte Dateien unverändert.

Der erste Selbsttest-Runner-Versuch ohne CI-Abhängigkeiten war erwartungsgemäß
rot; nach Installation des bestehenden hashgesperrten Lockfiles in einer
separaten temporären virtuellen Umgebung wurde er erfolgreich wiederholt.
