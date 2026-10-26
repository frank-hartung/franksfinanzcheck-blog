# Wartung · Sicherung · WF-9E5A #761 — Highend-Dauerheilung, Stille Frischhaltung (26.10.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #761 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 26.10.2026 · **Branch:** `arena/69a6dae3-franksfinanzcheck-blog` · **Basis:** `ba8dfc9` (main)
**Bearbeiter:** Arena Agent (Profi-Agentur-Niveau)
**Vorgänger:** `WF-9E5A-761-DAUERHEILUNG-PREMIUM-2026-10-15.md`, `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-22.md`, `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-24.md`

---

## 1. Ausgangslage (Live-Audit 26.10.2026)

Die drei Vorgänger-Runden haben die fachliche Kette vollständig aufgebaut
(E1–E8-Prüfung, 4 Alerting-Klassen, Fristwarnung, Frischwache 13:00 UTC,
Restore-Drill, Wizard, Anleitung, Tests). Alle Nachtläufe bleiben dennoch rot –
aus dem erwarteten Grund: Die **Inhaber-Einrichtung** (Secrets, privates Repo,
Environment-Schutz) ist weiterhin nicht erfolgt. Live gegen die GitHub-API
belegt (nur lesend, Agenten-Token kann Secrets/Variabeln nicht schreiben):

| Befund | Beleg |
|---|---|
| Zwölf nächtliche `Offsite-Backup`-Läufe durchgängig fehlgeschlagen | `gh run list --workflow=backup-offsite.yml`, jüngster Lauf `40291597993` (26.10. 08:20 UTC) |
| Privates Backup-Repo existiert nicht | `GET repos/frank-hartung/franksfinanzcheck-backup` → **404** |
| Environment `backup` ohne Branch-Regel (E8 offen) | Environments-API: `deployment_branch_policy: null` |
| Variablen-/Secret-Listen für den Agenten gesperrt | HTTP **403** „Resource not accessible by integration“ (Inhaber-Sphäre, Audit M-11) |
| Issue #761 weiter offen, Körper zuletzt am 16.10. 07:46 UTC angefasst | Issues-API; Body verweist auf Lauf `38869284948` (15.10.) |

### Gefundene Lücken dieses Durchgangs

| # | Lücke | Risiko | Schwere |
|---|---|---|---|
| L-10 | **#761 log systematisch veraltet.** Der Nachführ-Mechanismus von 15.10. schwieg komplett, solange der Klassen-Marker `backup-einrichtung` schon im Body stand (blankes `return`). Zehn weitere Rot-Läufe liefen ins Land, während der Body wörtlich behauptete: *„Mit dem jüngsten Lauf nachgeführt – Rat und Lauf oben sind aktuell.“** Der verlinkte Lauf war elf Tage alt; der `alert-jobs`-Marker für den Auto-Close bezog sich ebenso auf den alten Befund. | Eine Meldung, der man nicht mehr traut; der Inhaber öffnet einen toten Lauf und sieht eine veraltete Checkliste. Dieselbe Lücke betrifft **jede** offene Auto-Report-Meldung mit gleich bleibender Fehlerklasse. | **Hoch** |
| L-11 | **Der Einrichtungs-Wizard war nicht auffindbar.** `backup_einrichten_wizard.sh` (seit 25.10.) existierte, aber `package.json` kannte keinen Kurzbefehl; der einzige Einstieg war der lange Pfad über die Anleitung. Genau dieser Wizard ist das Werkzeug, das die einzige verbliebene #761-Aufgabe (Inhaber, ~10 Min.) auf die kürzeste Strecke bringt. | Reibung beim einzigen Menschen-Schritt, der #761 tatsächlich schließt; niedrigere Drill-/Wiederholungsrate. | Mittel |

Geprüft und **bewusst unverändert** gelassen: Die `Backup-Frischwache` geht im
unkonfigurierten Zustand mit `::warning::` und Exit 0 durch (kein Messwert
möglich, E1/E2 offen). Das ist korrekt so – ein roter Zweit-Alarm wäre ein
Duplikat zu #761, und der Primärpfad (nächtlicher Rot-Lauf → #761) bleibt
alarmierend. Die Summary sagt unmissverständlich „Frische kann nicht gemessen
werden“; ab Konfiguration gilt wieder 36 h gelb / 52 h rot.

---

## 2. Dauerhafte Korrektur (26.10.2026)

### 2.1 Stille Frischhaltung offener Meldungen — L-10

**Datei:** `.github/workflows/alert-on-failure.yml` (Inline-Skript des `alarm`-Jobs)

Der Dedupe-Pfad kennt jetzt drei klar getrennte Fälle statt zwei:

| Fall | Bedingung | Verhalten |
|---|---|---|
| 1. **Klassenwechsel** | Marker fehlt oder Runbook-Klasse ist eine andere | Body neu: neuer Rat, aktuelle Laufdaten (bestehender Pfad, `nachzufuehren`) |
| 2. **Stille Frischhaltung (neu)** | Gleiche Klasse, aber der Body verweist noch auf einen **älteren** Lauf | Body neu mit **demselben Rat**, aber frischem Run-Link, Zeit, Commit, Schritt- und `alert-jobs`-Marker (`aufzufrischen`) |
| 3. **Kein Schreibzugriff** | Job-Lage unbekannt **oder** Body verweist bereits auf genau diesen Lauf (Webhook-Redelivery, Neuversuch) | Keine Umschrift; Idempotenz pro Lauf |

Weitere Eigenschaften:

- Beide Schreibpfade teilen sich **einen** Update-Block (`bestehendeMeldung`)
  mit dem bestehenden fail-open-`catch`: Lehnnt die Issue-API ab, bleibt die
  Meldung unverändert offen, und es entsteht kein Duplikat.
- Es wird weiter ausschließlich `issues.update` auf die **bestehende Nummer**
  genutzt – kein Kommentar, kein neuer Titel, kein neues Issue. Ein Body-Edit
  benachrichtigt keine Beobachter (denselben Sachverhalt nutzt schon der
  Klassenwechsel seit 15.10.).
- „Offen seit“ bleibt das Erstanlage-Datum (`created_at`), in jedem Modus.
- Die Archivierung (`issue-cleanup.yml`) fasst nur **geschlossene** Meldungen
  an – tägliche Frischhaltung offener Meldungen kann keine Sperrkette auslösen.
- Der `alert-jobs`-Marker bleibt so auf dem jüngsten Befund; der Auto-Close
  (`alert_resolve_gate.py`) prüft danach den aktuellen Rot-Zustand.

### 2.2 Kurzbefehle für den Inhaber-Schnellweg — L-11

| Datei | Änderung |
|---|---|
| `package.json` | `backup:einrichten` → Wizard interaktiv (E8 dann E1–E7); `backup:status` → Wizard `--check` (nur prüfen). Manifest-Wache bestätigt: Skript-Blöcke brauchen keinen Lockfile-Eintrag; `manifest_guard.py` ist grün. |
| `scripts/backup_einrichten_wizard.sh` | Abschluss-Hinweis nennt zusätzlich `npm run backup:einrichten`; Verhalten unverändert (CI-Sperre, TTY, verdeckte Eingaben). |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` | Kopf auf Stand 26.10.2026, Komfort-Weg mit beiden Kurzbefehlen, Wizard in der Kopfzeile, Testzahl aktualisiert (33). |

### 2.3 Tests und Verträge (Dauerhaftigkeit)

| Datei | Änderung |
|---|---|
| `scripts/tests/sim/alert_scoping_sim.mjs` | 48 → **51 Szenarien**: der allgemeine Dedupe-Fall prüft jetzt die Frischhaltung (Update statt Stille); drei neue Backup-Fälle — Refresh bei älterem Lauf (Rat bleibt, Lauf-URL neu, alte URL weg, „Offen seit“ bleibt), Idempotenz bei gleichem Lauf, fail-open bei API-Ablehnung auch im Refresh-Pfad. |
| `scripts/tests/test_alert_scoping.py` | Neuer Strukturvertrag `test_stille_frischhaltung_bei_gleichem_rat_aber_neuem_lauf` (Reihenfolge, Run-URL-Wache, gemeinsamer fail-open-Block, Sim-Nadeln); Klassenwechsel-Test auf den gemeinsamen Update-Block gezogen; Modul-Doku Punkt 9 erweitert. **27 Tests.** |
| `scripts/tests/test_backup_einrichtung.py` | Neue Klasse `WizardVertrag` (4 Tests): Bash-Syntax, CI-Verweigerung, alle sieben Einstellungen + E8-Reihenfolge, npm-Kurzbefehle deckungsgleich mit Anleitung. Modul jetzt **33 Tests.** |
| `CLAUDE.md` | Leitplanke „Stille Frischhaltung“ mit den drei Fällen und der Idempotenz-Regel; Inhaber-Schnellweg `npm run backup:einrichten/status`; Berichtsindex um die drei Highend-Dossiers ergänzt. |

---

## 3. Was *nicht* getan wurde (bewusste Grenzen)

| Nicht getan | Begründung |
|---|---|
| Kein Setzen von Secrets/Variablen, keine Repo-Anlage, keine Environment-Regel durch den Agenten | Inhaber-Sphäre (M-11); der Token wird mit 403 abgewiesen. Genau dafür trägt der Wizard die vorbelegten Links zusammen. |
| Kein Hand-Kommentar und keine Hand-Umschrift von #761 | Markenfläche; der nächste rote Lauf nach dem Merge schreibt #761 über den produktionsidentischen Code automatisch frisch (mit dem Lauf der Nacht 27.10., 03:00 UTC). |
| Keine tägliche Body-Umschrift bei identischem Lauf | Run-URL-Wache macht den Pfad pro Lauf idempotent (Redelivery/Neuversuch = kein API-Schreibzugriff). |
| Kein `continue-on-error` und keine Aufweichung der Fail-Closed-Kette | Der rote Nachtlauf ist korrekt: Ohne Einrichtung gibt es keine Sicherung. |
| Kein Umbau der Frischwachen-Semantik im unkonfigurierten Zustand | Warnung statt Zweit-Alarm; #761 ist der designierte offene Kanal (siehe 1). |
| Keine neuen Netzaufrufe, keine neuen Hosts | `ki_transportweg`-Verträge bleiben grün (36 Tests unter PyYAML); alle Änderungen spielen im bestehenden Issue-API-Pfad. |

---

## 4. Verifikation

### 4.1 Automatisierte Tests

| Befehl | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_alert_scoping` | **27 OK** (1 Skip ohne PyYAML lokal; CI hat PyYAML) |
| Simulation direkt (`node alert_scoping_sim.mjs`) | **51/51 Szenarien korrekt** |
| `python3 -m unittest scripts.tests.test_backup_einrichtung` | **33 OK** (11 Skip ohne PyYAML) |
| Beide Module unter PyYAML (VENV wie CI) | **60 OK, 0 Skip** |
| `python3 -m unittest scripts.tests.test_alert_resolve_gate test_alert_router test_alerting_heartbeat` | **64 OK** |
| `test_ki_transportweg` + `ki_transportweg.py --selftest` (PyYAML-VENV) | **36 OK**, Selbsttest grün (16 Sabotage- + 2 Driftproben) |
| `python3 scripts/manifest_guard.py` | **GRÜN**, 0 Befunde/0 Warnungen (13 Manifeste) |
| YAML-Parser gegen alle drei Backup/Alerting-Workflows | valide |
| `node --check` (eingehüllt wie github-script), `bash -n` Wizard, `git diff --check` | grün |

### 4.2 Mutationsproben (die neuen Verträge müssen beißen)

| Mutation | Folge | Restaurierung |
|---|---|---|
| Run-URL-Idempotenzwache entfernt | Sim-Szenario „Frischhaltung idempotent“ rot | zurück auf grün |
| Frischhaltung komplett entfernt (alter `return`-Zustand) | 2 Fehler: Sim-Refresh-Szenario + neuer Strukturvertrag | zurück auf grün |

### 4.3 Live-Beweis nur lesend (kein API-Schreibzugriff)

Der extrahierte Produktions-Code wurde mit dem **echten** #761-Körper und den
**echten** Jobs des Laufs `40291597993` ausgeführt; `issues.update` war im
Harness abgefangen (Protokoll statt Schreibzugriff). Ergebnis 10/10:

```
↻ Meldung #761 still frisch gehalten: Rat „backup-einrichtung“ bleibt, Laufdaten aktualisiert aus Lauf 40291597993.
create-Aufrufe: 0 (erwartet 0) · update-Aufrufe: 1 (erwartet 1)
✅ Ziel ist #761                ✅ Titel unverändert
✅ Klasse bleibt backup-einrichtung
✅ neuer Lauf 40291597993 verlinkt · ✅ alter Lauf 38869284948 verschwunden
✅ Einrichtungs-Rat bleibt      ✅ kein GROQ/GEMINI-Rat
✅ „Offen seit“ bleibt 15.10.2026, 09:54:25 (Erstanlage)
✅ Job-Marker aktuell (KV-/D1-Backup-Job)
```

### 4.4 Gesamt-Suite (Regression)

| Stand | Tests | Failures | Errors | Skipped |
|---|---|---|---|---|
| Basis `ba8dfc9` (gestasht) | 3068 | 87 | 136 | 103 |
| Dieser Branch | **3073** (+5 neue) | **87** | **136** | 103 |

Die 223 Vorbehaltsfälle sind identisch vor und nach der Änderung
(Umgebungs-Abhängigkeiten: fehlendes Hugo/binäre Werkzeuge, optionale Module,
Netzsperren in der Sandbox). **Keine neue Regression**, alle vom Änderungsbereich
berührten Tests sind grün.

### 4.5 Wizard-Probe in der Sandbox

- `GITHUB_ACTIONS=true bash … --check` → Exit 1 mit der CI-Sperrmeldung.
- `--check` mit dem eingeschränkten Token: E8/E1/E6 als offen benannt,
  unlesbare Secrets sauber als „nicht prüfbar“ deklariert, kein Absturz, Exit 1.

---

## 5. Betriebshandbuch (ab Merge 26.10.2026)

1. **Automatisch in der Nacht nach dem Merge:** Der nächste rote
   `Offsite-Backup`-Lauf führt die stille Frischhaltung aus – #761 zeigt dann
   ohne Kommentar oder neue Nummer auf den jüngsten Lauf, bei unverändertem
   Einrichtungs-Rat.
2. **Inhaber-Einrichtung (einmalig, ~10 Min., das schließt #761 wirklich):**
   `npm run backup:einrichten` am eigenen Rechner (oder die sieben Schritte in
   `docs/ANLEITUNG-OFFSITE-BACKUP.md`; Reihenfolge E8 → E1–E7 ist erzwungen).
   Zustand zwischendurch: `npm run backup:status`.
3. **Abnahme:** Erster grüner `Offsite-Backup`-Lauf schließt #761 über den
   `resolve`-Job selbst; danach `npm run backup:probe` (Restore-Drill) als
   operativer Wiederherstellungsbeweis. Die Frischwache (13:00 UTC) bewegt sich
   ab Konfiguration von „nicht messbar“ auf echte 36/52-h-Messung.

## 6. Dauerhaftigkeit

| Mechanismus | Verankert | Bricht bei Regression |
|---|---|---|
| Drei Nachführ-Modi + Idempotenz pro Lauf | `alert-on-failure.yml` | Strukturvertrag + 51 Sim-Szenarien rot |
| Fail-open beim Frischhalten | gemeinsamer Update-Block | Sim „scheitert an der API“ + Strukturtest |
| Wizard-Kurzbefehle | `package.json`, Anleitung, `WizardVertrag` | Kabelbruch zwischen npm, Wizard und Anleitung wird Testrot |
| Fail-closed der Sicherung bleibt unangetastet | keine Workflow-Entschärfung | bestehende Backup-Verträge (33 Tests) |
| Manifest-Schutz | `manifest_guard.py` grün | L2 bei Lock/Manifest-Drift |

**Ergebnis:** Die Sicherungskette war fachlich vollständig; was diese Runde
schließt, ist die letzte operative Ehrlichkeitslücke im Meldungssystem selbst:
Eine offene Störungsmeldung kann nicht mehr auf einen toten Lauf verweisen und
gleichzeitig Aktualität behaupten – sie hält sich jetzt bei jeder neuen
festgestellten Störung selbst frisch, stillschweigend, idempotent und
fail-open. Der verbleibende Abschluss von #761 ist und bleibt die zehnminütige
Inhaber-Einrichtung, dafür gibt es jetzt einen einzigen merkbaren Befehl.
