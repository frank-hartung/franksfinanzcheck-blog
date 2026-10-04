# Sicherheitsrichtlinie

## Sicherheitslücken vertraulich melden

Bitte veröffentliche Sicherheitslücken **nicht** als öffentliches Issue.
Nutze stattdessen GitHubs private Sicherheitsmeldungen:

1. Öffne **Security → Advisories → New draft security advisory**.
2. Beschreibe Auswirkung, betroffene Dateien/Versionen und – soweit möglich – eine Reproduktion.
3. Teile keine Zugangsdaten, Tokens, personenbezogenen Daten oder Newsletter-Adressen in Logs oder Screenshots.

Falls private Meldungen auf GitHub nicht angeboten werden, kontaktiere den Betreiber über die im Impressum der Website genannte Adresse und kennzeichne die Nachricht mit „VERTRAULICH – SECURITY“.

## Reaktionsziel

- Eingangsbestätigung: möglichst innerhalb von 3 Werktagen
- Erste Risikobewertung: möglichst innerhalb von 7 Werktagen
- Veröffentlichung: erst nach Bereinigung oder abgestimmter Frist

## Unterstützte Version

Unterstützt wird ausschließlich der aktuelle Stand des Default-Branches `main` und die daraus veröffentlichte Website.

## Geheimnisse

GitHub-Tokens, API-Schlüssel und Newsletter-Geheimnisse gehören ausschließlich in GitHub Actions Secrets bzw. die dafür vorgesehene Betriebsumgebung. Ein versehentlich veröffentlichtes Geheimnis muss sofort widerrufen und ersetzt werden; das bloße Entfernen aus der Git-Historie genügt nicht.

## Prozessstarts

Produktive Python-Skripte starten externe Programme ausschließlich mit expliziten Argumentvektoren (`subprocess.run([...], shell=False)`). Shell-Ausführung (`shell=True`, `os.system`, `os.popen`) ist untersagt: dynamische Werte wie Slugs, Workflow-Namen und Pfade müssen jeweils ein einzelnes Argument bleiben und, wo sinnvoll, vorab validiert oder URL-kodiert werden.

Der Regressionstest `scripts/tests/test_command_execution_security.py` erzwingt diese Regel für alle produktiven Skripte. Änderungen an einem Prozessstart müssen diesen Test erweitern und dürfen keine Ausnahme von der Regel einführen.
