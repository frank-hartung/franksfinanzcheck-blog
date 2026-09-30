# GitHub-Premium-Betrieb: wenige E-Mails, keine blinden Stellen

Stand: 30.09.2026

## Zielbild

GitHub meldet dem Betreiber nur handlungsrelevante Produktionsstörungen. Entwicklungsfehler bleiben als PR-Checks sichtbar, erzeugen aber keinen Betreiberalarm.

### Was als Alarm gilt

- `failure` oder `timed_out` eines überwachten Workflows auf dem Default-Branch
- ein abgebrochener Produktionslauf nur, wenn bereits Schritte ausgeführt wurden
- ein Ausfall des Alerting-Kanals selbst, erkannt durch den täglichen Herzschlag

### Was ausdrücklich kein Alarm ist

- Fehler auf PR-, Arena- oder Dependabot-Zweigen
- ein verdrängter Wartelauf ohne ausgeführten Schritt
- erfolgreiche, übersprungene oder neutrale Läufe
- ein zweites Issue für dieselbe noch offene Störung

Der technische Vertrag liegt in `.github/workflows/alert-on-failure.yml`. Regressionstests stehen in `scripts/tests/test_alert_scoping.py`; der unabhängige Zustellnachweis liegt in `.github/workflows/alerting-heartbeat.yml`.

## Einmalige persönliche GitHub-Einstellung

Repository-Code darf persönliche E-Mail-Präferenzen absichtlich nicht ändern. Im GitHub-Konto:

1. **Settings → Notifications** öffnen.
2. Unter **Default notifications email** die gewünschte Betriebsadresse auswählen.
3. Unter **Actions** nur Benachrichtigungen für fehlgeschlagene Workflows aktivieren; erfolgreiche Workflow-Runs nicht per E-Mail zustellen lassen.
4. Auf der Repository-Seite **Watch → Custom** wählen und allgemeine Issue-/PR-Aktivität nicht pauschal abonnieren. Wer das Repository mit „All Activity“ beobachtet, umgeht die Lärmfilter des Repositories.
5. Unter **System → Email** Web und Mobile nach Wunsch belassen, aber nur **Email** für die tatsächlich benötigten Kategorien auswählen.
6. Bestehende, nicht handlungsrelevante Threads über **Unsubscribe** verlassen. Offene `auto-report`-Issues nicht stummschalten: Sie sind der Produktionskanal.

GitHub verändert die Oberfläche gelegentlich. Entscheidend ist die Policy: **keine pauschale Repository-Beobachtung, Actions nur bei Fehlern, Produktionsalarme über `auto-report`.**

## Empfohlene Repository-Regeln (Admin-Schritt)

Für `main` in **Settings → Rules → Rulesets**:

- Pull Request vor Merge verlangen
- Branch muss vor Merge aktuell sein
- erforderliche Checks: Qualitäts-Gate, Integritäts-Lock und die für den Änderungstyp relevanten Tests
- Force-Push und Branch-Löschung verbieten
- Umgehung nur für einen klar benannten Notfall-Administrator
- signierte Commits dort verlangen, wo alle eingesetzten Bots sie unterstützen
- Secret Scanning, Push Protection, Dependabot Alerts und private Vulnerability Reporting aktivieren

Diese Einstellungen benötigen Repository-Adminrechte und lassen sich mit dem in dieser Agentensitzung verfügbaren, nicht-administrativen GitHub-Zugriff nicht sicher setzen.

## Betrieb und Entstörung

1. Alarm-Issue öffnen und den direkt verlinkten roten Schritt prüfen.
2. Ursache beheben oder den Lauf nach einem nachweislich transienten Fehler erneut starten.
3. Das Issue nicht manuell als „gelöst“ schließen. Erst ein grüner Produktionslauf darf automatisch entwarnen.
4. Bleibt der Alerting-Herzschlag rot, Actions-Runs direkt prüfen: Dann ist möglicherweise die Ereigniszustellung gestört.

## Wartungsvertrag

```bash
python3 -m unittest scripts.tests.test_alert_scoping scripts.tests.test_alerting_heartbeat
python3 scripts/automation_premium_audit.py
```

Action-Abhängigkeiten werden schrittweise auf vollständige Commit-SHAs gepinnt. Dependabot bleibt für die kontrollierte Aktualisierung verantwortlich; eine bewegliche Major-Version ist keine gleichwertige Supply-Chain-Garantie.
