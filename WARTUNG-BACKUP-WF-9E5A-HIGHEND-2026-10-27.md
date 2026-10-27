# Wartung · Sicherung · WF-9E5A #761 — E8-Restfehler und Setup-Dauerfix (27.10.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #761 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Branch:** `arena/c838a97b-franksfinanzcheck-blog` · **Basis:** `b6f0265`
**Vorgänger:** `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-22.md`, `…-2026-10-24.md`, `…-2026-10-26.md`
**Status:** Code-Pfad und Sicherheitsprüfung korrigiert; **Live-Backup bleibt bis zur Inhaber-Einrichtung absichtlich rot, Issue #761 bleibt offen.**

---

## 1. Live-Befund statt Annahme

Der jüngste Lauf, auf den Issue #761 zeigt, ist `40474184391` vom **27.10.2026, 08:32 UTC** (`schedule`, `main`, Commit `99599e7`). Der Repo-Job lief; im Job **„KV-/D1-Backup (Abonnenten + Einwilligungsnachweise)“** scheiterte ausschließlich der fail-closed-Schritt **„Voraussetzungen prüfen“**. Export und Ablage wurden folgerichtig übersprungen.

| Prüfpunkt | Befund aus den GitHub-Check-Run-Annotationen |
|---|---|
| E1 `BACKUP_REPO` | fehlt; das private Ziel-Repository ist außerdem per API nicht auffindbar (404) |
| E2 `BACKUP_REPO_TOKEN` | fehlt |
| E3 `BACKUP_PASSPHRASE` | fehlt |
| E4 `CLOUDFLARE_ACCOUNT_ID` | vorhanden / Formatprüfung bestanden |
| E5 `CF_KV_BACKUP_TOKEN` | fehlt |
| E6 `KV_NAMESPACE_ID_ABO` | fehlt |
| E7 `D1_DATABASE_ID` | optional, nicht gesetzt |
| E8 Environment `backup` | `deployment_branch_policy: null`; jeder Branch darf das Environment nutzen |

Ein zusätzlicher lesender Check bestätigte E8: Das Environment existiert, hat keine Deployment-Branch-Regel und keine Protection Rule. `bash scripts/backup_einrichten_wizard.sh --check` konnte E1, E6 und E8 im verfügbaren Sandbox-Kontext lesen; Geheimnis-Metadaten E2/E3/E5 und E4 waren mit dem hier verfügbaren GitHub-Recht nicht prüfbar. Es wurden **keine** Variablen, Secrets, Environment-Regeln oder Issues geschrieben. Der nicht zugängliche Actions-Log-Download lieferte EOF; für den Befund genügten die über die Check-Run-API lesbaren Annotationen.

**Bewertung:** Das aktuelle Rot ist kein Fehler im Exporter. Es verhindert korrekt ein Schein-Grün und bedeutet zugleich: Abonnenten und Einwilligungsnachweise sind derzeit **nicht offsite gesichert**. Die Zugangswerte und das private Ziel kann nur der Repository-Inhaber anlegen.

---

## 2. Neu gefundener technischer Root Cause

Die vorherige Runde hatte einen lokalen Einrichtungs-Wizard ergänzt, aber seine kritischste Sicherheitsstufe war nicht durch einen echten REST-Vertrag geschützt:

1. `branch_regel_setzen` verwendete `PUT` auf der Collection `/deployment-branch-policies` mit einem nicht unterstützten Body (`policy_type` / `allowed_branches`). Der GitHub-REST-Vertrag bietet auf dieser Collection `GET` und `POST`; die Environment-Branch-Policy wird am Environment gesetzt, einzelne Branch-Policies werden per `POST` angelegt und per ID gelöscht. Der Wizard unterdrückte den API-Fehler.
2. `pruefe_e8` konnte bei einer unsicheren Regel trotzdem Exit 0 liefern: Nach `offen` bzw. `link` war der letzte Shell-Befehl ein erfolgreiches `printf`. Dadurch konnte die Bedingung zur E8-Sperre übersprungen werden.
3. Die manuelle Rückfrage „Erledigt?“ wurde nicht durch einen erneuten API-Read-back abgesichert. Eine Ja-Antwort hätte allein genügt, um zu den Secret-Schritten weiterzugehen.
4. Sowohl Wizard als auch Laufzeitprüfung konnten „Protected branches“ als gleichbedeutend mit „nur `main`“ behandeln. Das beweist keine exklusive `main`-Freigabe.

Der API-Vertrag wurde gegen die offizielle GitHub-REST-Beschreibung (`github/rest-api-description`, über `api.github.com`) abgeglichen.

---

## 3. Dauerhafte Korrektur

### 3.1 Wizard: korrekter API-Pfad, kein Secret vor E8-Nachweis

`scripts/backup_einrichten_wizard.sh`:

- Aktiviert `custom_branch_policies` am Environment-Endpunkt.
- Liest bestehende Regeln paginiert, erhält oder erstellt zuerst `main` vom Typ `branch` und löscht erst danach die übrigen IDs. So bleibt bei vorhandenen Regeln der Schutz bestehen; jeder API-Fehler bricht ab.
- Liest E8 anschließend vollständig und paginiert zurück. Nur **genau eine** Regel `main (branch)`, ohne Required Reviewers, gilt als erfolgreich.
- `protected branches`, zusätzliche Branch-/Tag-Regeln, fehlende Regeln oder eine nicht lesbare API ergeben Exit 1.
- Nach manueller Korrektur wird E8 erneut live geprüft. Bleibt der Nachweis aus, bricht der Wizard **vor dem ersten Secret** ab; eine Bestätigung allein reicht nicht.

### 3.2 Laufzeitprüfung: „main-only“ nur bei explizitem Beleg

`scripts/backup_einrichtung.py` verlangt für einen grünen E8-Befund nun ebenfalls die explizite Auswahl genau des Branches `main`. Eine nicht lesbare Environment- oder Branch-Policy-API wird als Warnung und `environment_offen` ausgewiesen, nicht als Sicherheitserfolg.

E8 bleibt **laufzeitseitig ein Hinweis**, damit ein Branch-Schutz-Befund die tägliche Sicherung nicht still überspringt. Die harte Schranke liegt vor dem Eintragen der Secrets im Wizard. Solange weitere Pflichtzugänge fehlen, rückt E8 als „Zuerst E8“ an den Anfang der Checkliste.

### 3.3 Regressionsschutz und Dokumentation

- `scripts/tests/test_backup_einrichtung.py`: isolierte Funktionsproben mit gemocktem `gh` prüfen Environment-Body, REST-Methoden (GET/DELETE/POST), paginierte Policy-Liste, `main (branch)` sowie Ablehnung von `protected branches`, fremden Branches/Tags, Reviewers und nicht lesbaren Antworten. Ein Laufzeit-Vertrag setzt eine zusätzliche `arena/*`-Regel auf Seite 2 und beweist, dass sie E8 rot hält. Ein weiterer Vertrag stellt sicher, dass der Wizard nach manueller Rückmeldung erneut prüft und vor Secrets stoppt.
- `backup_einrichtung.py --selftest`: neue 18. Fallgruppe für „nur `main` nachweisbar“.
- `docs/ANLEITUNG-OFFSITE-BACKUP.md` und `CLAUDE.md`: REST-Verfahren, harte E8-Schranke, exakter Live-Befund und offene Inhaber-Aufgabe aktualisiert.

---

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/backup_einrichtung.py --selftest` | ✅ 18 Fallgruppen |
| `npm run test:backup` | ✅ 39 Unittests und 3 Selbsttests; in der nackten Sandbox 11 YAML-bezogene Skip-Fälle |
| `python3 -m unittest scripts.tests.test_backup_einrichtung scripts.tests.test_alert_scoping -v` mit lokal verfügbarem PyYAML | ✅ **66 Tests, 0 Skips** |
| `bash -n scripts/backup_einrichten_wizard.sh` | ✅ |
| Wizard-Funktionsproben (REST-Payload, echte Aufrufreihenfolge, E8-Fail-closed) | ✅ |
| Read-only `backup_einrichten_wizard.sh --check` | ✅ E1/E6/E8 als offen; Secret-Metadaten ausdrücklich „nicht prüfbar“, keine Schreibzugriffe |
| Live-Backup / Issue #761 | **weiterhin offen** – kein grüner Lauf, weil Inhaber-Zugänge fehlen |

---

## 5. Verbleibender Inhaber-Schritt und Abnahmekriterium

Die fehlenden Secrets dürfen weder erfunden noch durch einen breiten Agenten-Token ersetzt werden. Sobald der korrigierte Wizard im lokalen Checkout verfügbar ist, einmal als Inhaber mit Environment-Administrationsrecht ausführen:

```bash
npm run backup:einrichten
```

Der Wizard sichert zuerst E8 ab und weist den Zustand nach. Danach führt er durch privates Ziel-Repository, Passphrase (32+ zufällige Zeichen), Fine-grained GitHub-Token nur für das Backup-Repository, Cloudflare-Token mit KV-Leserecht und die KV-Namespace-ID. Anschließend kann der erste Lauf gestartet werden. Zwischenstand:

```bash
npm run backup:status
```

**Abnahme erst nach** einem grünen `Offsite-Backup`-Lauf (beide Backup-Familien verschlüsselt, im privaten Ziel nachgelesen) und anschließendem Restore-Drill `npm run backup:probe`. Der erste grüne Lauf schließt #761 wie vorgesehen automatisch. Bis dahin bleibt die Meldung offen und der KV-Job rot – das ist der sichere, ehrliche Zustand.
