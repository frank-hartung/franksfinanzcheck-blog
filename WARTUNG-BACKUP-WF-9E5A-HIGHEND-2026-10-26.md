# Wartung · Sicherung · WF-9E5A #761 — Highend-Dauerheilung, Lagebild-Verfall absichern + Wizard-Kurzbefehle (26.10.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #761 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Datum:** 26.10.2026 · **Branch:** `arena/69a6dae3-franksfinanzcheck-blog` · **Basis nach Merge:** `bc9a038` (main, inkl. #909)
**Bearbeiter:** Arena Agent (Profi-Agentur-Niveau)
**Vorgänger:** `WF-9E5A-761-DAUERHEILUNG-PREMIUM-2026-10-15.md`, `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-22.md`, `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-24.md`
**Parallel:** `WARTUNG-BETRIEBSPFLEGE-WF-E813-815-HIGHEND-2026-10-26.md` (PR #909, derselbe Tag)

---

## 1. Ausgangslage (Live-Audit 26.10.2026)

Die drei Vorgänger-Runden haben die fachliche Backup-Kette vollständig
aufgebaut (E1–E8-Prüfung, vier Alerting-Klassen, Fristwarnung, Frischwache
13:00 UTC, Restore-Drill, Einrichtungs-Wizard, Anleitung, Tests). Offen ist
weiterhin die **Inhaber-Einrichtung** (Secrets, privates Repo,
Environment-Schutz) – Agenten können sie nicht setzen (Audit M-11). Live gegen
die GitHub-API belegt (nur lesend; Schreibversuche auf Variablen/Secrets
werden mit 403 abgewiesen):

| Befund | Beleg |
|---|---|
| Zwölf nächtliche `Offsite-Backup`-Läufe durchgängig fehlgeschlagen | `gh run list --workflow=backup-offsite.yml`, jüngster Lauf `40291597993` (26.10. 08:20 UTC) |
| Privates Backup-Repo existiert nicht | `GET repos/frank-hartung/franksfinanzcheck-backup` → **404** |
| Environment `backup` ohne Branch-Regel (E8 offen) | Environments-API: `deployment_branch_policy: null` |
| Issue #761 weiter offen, Körper zuletzt am 16.10. angefasst | Issues-API; Body verweist auf Lauf `38869284948` (15.10.) |

### Gefundene Lücken dieses Durchgangs

| # | Lücke | Risiko | Schwere |
|---|---|---|---|
| L-10 | **#761 log systematisch veraltet.** Der Nachführ-Pfad von 15.10. schwieg komplett, solange der Klassen-Marker `backup-einrichtung` schon im Body stand (blankes `return`). Zehn weitere Rot-Läufe liefen ins Land, während der Body wörtlich behauptete: *„Mit dem jüngsten Lauf nachgeführt – Rat und Lauf oben sind aktuell.“* Der `alert-jobs`-Marker für den Auto-Close alterte mit. Dieselbe Lücke betraf jede offene Auto-Report-Meldung mit gleich bleibender Fehlerklasse (am selben Tag unabhängig über #815 bestätigt). | Eine Meldung, der man nicht mehr traut; der Inhaber öffnet einen toten Lauf mit veralteter Checkliste. | **Hoch** |
| L-11 | **Der Einrichtungs-Wizard war nicht auffindbar.** `backup_einrichten_wizard.sh` (seit 25.10.) kannte keinen npm-Kurzbefehl; der Einstieg führte nur über den langen Dateipfad in der Anleitung. Genau dieser Wizard ist das Werkzeug für die einzige verbliebene #761-Aufgabe (Inhaber, ~10 Min.). | Reibung beim einzigen Menschen-Schritt, der #761 wirklich schließt. | Mittel |

Geprüft und **bewusst unverändert**: Die `Backup-Frischwache` geht im
unkonfigurierten Zustand mit `::warning::` und Exit 0 durch (kein Messwert
möglich, E1/E2 offen). Ein roter Zweit-Alarm wäre ein Duplikat zu #761; der
Primärpfad (nächtlicher Rot-Lauf → #761) bleibt alarmierend. Ab Konfiguration
gelten wieder 36 h gelb / 52 h rot.

---

## 2. Parallelbefund #909 und die Merge-Entscheidung

Während der Erstellung dieses Zweigs hat **PR #909** (WF-E813/#815,
„Betriebspflege Stufe 3“) dieselbe Fehlerklasse L-10 auf einem anderen Vorgang
gefunden und auf `main` gelöst – mit einem **Lagebild-Verfall** genannten
Mechanismus direkt im produktiven Inline-Skript:

- Bei gleichem Klassen-Marker wird die im Body aufgezeichnete Lauf-ID per
  Regex `/(?:actions\/)?runs\/(\d+)/` gelesen und mit dem aktuellen Lauf
  verglichen.
- Jüngerer Lauf → der bestehende `nachzufuehren`-Pfad schreibt den Body neu
  (gleicher Rat, frische Laufdaten, aktueller `alert-jobs`-Marker).
- Gleicher oder **älterer** Lauf (Redelivery, verspätete Webhook-Zustellung)
  → keine Umschrift (Reihenfolgeschutz, ein Schutz über die reine
  URL-Gleichheit der ersten Lösung dieses Zweigs hinaus).
- Denselben fail-open-Update-Block nutzend, ohne neue Variable.
- Zusätzlich: Zwei stille Kanäle auf die Wacht-Liste geholt
  (`Cloudflare-Worker deployen`, `CodeQL-Sicherheitswache`) mit vier eigenen
  Runbook-Klassen und Sim-Szenarien.

**Entscheidung nach Profi-Maßstab:** Keinen zweiten, konkurrierenden Mechanismus
pflegen. Der Branch wurde mit `main` zusammengeführt und übernimmt den
#909-Mechanismus eins zu eins (inkl. des stärkeren Reihenfolgeschutzes). Die
Eigenleistung dieses PRs liegt danach auf den drei Säulen unten.

## 3. Dauerhafte Korrektur (Bestandteil dieses PR nach dem Merge)

### 3.1 Strukturvertrag für den Lagebild-Verfall — Absicherung von L-10

#909 deckte das Verhalten nur über die Verhaltens-Simulation ab. Dieser PR
ergänzt den **Python-Strukturvertrag**
`test_stille_frischhaltung_bei_gleichem_rat_aber_neuem_lauf`, der festnagelt:

- die Lauf-ID-Regex steht im Gleiche-Klasse-Zweig,
- die Reihenfolge *Marker → Lauf-Alter-Prüfung → Nachführen* ist fixiert,
- der Rückweg ohne Update (`return;`) ist vorhanden (kein älteres Ereignis
  darf ein jüngeres Lagebild überschreiben),
- der gemeinsame Update-Block bleibt fail-open und endet ohne Duplikat,
- die Simulations-Nadeln „Lagebild-Verfall“, „Reihenfolgeschutz“ und
  „Nachführung idempotent“ müssen vorhanden sein.

Dazu ein **zusätzliches Sim-Szenario**: Schlägt die Issue-API gerade auf dem
Verfalls-Pfad (gleiche Klasse, älterer Lauf) ab, bleibt es bei Absturfreiheit,
keinem Duplikat und der offenen Meldung – der fail-open-Contract damit auch
für den neuen Pfad einzeln bewiesen, nicht nur über den Klassenwechsel.

### 3.2 Kurzbefehle für den Inhaber-Schnellweg — L-11

| Datei | Änderung |
|---|---|
| `package.json` | `backup:einrichten` → Wizard interaktiv (E8 dann E1–E7); `backup:status` → Wizard `--check` (nur prüfen). Manifest-Wache grün; Skript-Blöcke brauchen keinen Lockfile-Eintrag. |
| `scripts/backup_einrichten_wizard.sh` | Abschluss-Hinweis nennt zusätzlich `npm run backup:einrichten`; Verhalten unverändert (CI-Sperre, TTY, verdeckte Eingaben). |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` | Kopf auf Stand 26.10.2026, Komfort-Weg mit beiden Kurzbefehlen, Wizard in der Kopfzeile, Testzahl aktualisiert (33). |

### 3.3 Verträge und Leitplanken

| Datei | Änderung |
|---|---|
| `scripts/tests/test_backup_einrichtung.py` | Neue Klasse `WizardVertrag` (4 Tests): Bash-Syntax, CI-Verweigerung, alle sieben Einstellungen + E8-Reihenfolge, npm-Kurzbefehle deckungsgleich mit der Anleitung. Modul **33 Tests.** |
| `scripts/tests/test_alert_scoping.py` | Strukturvertrag Lagebild-Verfall (3.1), Klassenwechsel-Test auf den gemeinsamen Update-Block gezogen, Modul-Doku Punkt 9 auf den Regex-/Reihenfolge-Mechanismus geschrieben. **27 Tests.** |
| `CLAUDE.md` | Leitplanke „Lagebild-Verfall / stille Frischhaltung“ mit Regex, Reihenfolgeschutz und fail-open; Inhaber-Schnellweg `npm run backup:einrichten/status`; Berichtsindex ergänzt. |
| `scripts/tests/sim/alert_scoping_sim.mjs` | Nach dem Merge **58 Szenarien** (54 von #909 inkl. Worker-Deploy/CodeQL + 4 neue Kanäle; plus dem zusätzlichen fail-open-Verfalls-Szenario dieses PRs). |

---

## 4. Was *nicht* getan wurde (bewusste Grenzen)

| Nicht getan | Begründung |
|---|---|
| Kein Setzen von Secrets/Variablen, keine Repo-Anlage, keine Environment-Regel durch den Agenten | Inhaber-Sphäre (M-11), 403 belegt. Der Wizard trägt die vorbelegten Links zusammen. |
| Kein paralleler Frischhaltungs-Mechanismus neben #909 | Zwei Codepfade für denselben Effekt sind die nächste Regression; der #909-Mechanismus mit Reihenfolgeschutz ist fachlich überlegen und wurde vollständig übernommen. |
| Kein Hand-Kommentar und keine Hand-Umschrift von #761 | Markenfläche; der nächste rote Lauf nach dem Merge schreibt #761 über produktionsidentischen Code automatisch frisch. |
| Kein `continue-on-error`, keine Aufweichung des Fail-Closed-Prinzips | Der rote Nachtlauf ist korrekt: Ohne Einrichtung keine Sicherung. |
| Kein Umbau der Frischwachen-Semantik im unkonfigurierten Zustand | Warnung statt Zweit-Alarm; #761 ist der designierte offene Kanal. |
| Keine neuen Netzaufrufe oder Hosts | `ki_transportweg`-Verträge bleiben grün; alle Änderungen spielen im bestehenden Issue-API-Pfad. |

---

## 5. Verifikation

### 5.1 Automatisierte Tests

| Befehl | Ergebnis |
|---|---|
| `python3 -m unittest scripts.tests.test_alert_scoping` | **27 OK** (1 Skip ohne PyYAML lokal; CI hat PyYAML) |
| Beide Module unter PyYAML (wie CI) | **60 OK, 0 Skip** (27 Alerting + 33 Backup) |
| Verhaltens-Simulation (`node alert_scoping_sim.mjs`) | **58/58 Szenarien korrekt** |
| `python3 -m unittest scripts.tests.test_backup_einrichtung` | **33 OK** (11 Skip ohne PyYAML) |
| `test_alert_resolve_gate` · `test_alert_router` · `test_alerting_heartbeat` | **64 OK** |
| `test_ki_transportweg` + `ki_transportweg.py --selftest` (PyYAML) | **36 OK**, Selbsttest grün |
| `python3 scripts/manifest_guard.py` | **GRÜN**, 0 Befunde (13 Manifeste) |
| YAML-Parser gegen alle drei Backup/Alerting-Workflows | valide |
| `node --check` (eingehüllt wie github-script), `bash -n` Wizard, `git diff --check` | grün |

### 5.2 Mutationsproben an den neuen Verträgen

| Mutation | Folge | Restaurierung |
|---|---|---|
| Lauf-ID-Regex aus dem Workflow entfernt | Strukturvertrag `test_stille_frischhaltung…` rot | zurück auf grün |
| Reihenfolgeschutz (`>=`-Wache) entfernt | Sim „Reihenfolgeschutz“ + Strukturvertrag rot | zurück auf grün |
| (vor dem Merge an der Eigenlösung bewiesen) Idempotenzwache entfernt / Frischhaltung komplett entfernt | Sim bzw. Strukturvertrag rot | durch #909-Übernahme obsolet geworden |

### 5.3 Live-Beweis nur lesend mit dem zusammengeführten Produktiv-Code

Der nach dem Merge extrahierte Produktions-Code (#909-Mechanismus) wurde mit
dem **echten** #761-Körper und den **echten** Jobs des Laufs
`40291597993` ausgeführt; `issues.update` war im Harness abgefangen
(Protokoll statt Schreibzugriff):

```
Gleicher Rat „backup-einrichtung“, aber Lauf 40291597993 ist jünger als Lauf 38869284948 – Lagebild in #761 wird erneuert.
create-Aufrufe: 0 (erwartet 0) · update-Aufrufe: 1 (erwartet 1)
✅ Ziel ist #761                ✅ Titel unverändert
✅ Klasse bleibt backup-einrichtung
✅ neuer Lauf 40291597993 verlinkt · ✅ alter Lauf 38869284948 verschwunden
✅ Einrichtungs-Rat bleibt      ✅ kein GROQ/GEMINI-Rat
✅ „Offen seit“ bleibt 15.10.2026, 09:54:25 (Erstanlage)
✅ Job-Marker aktuell (KV-/D1-Backup-Job)
```

9/9 Erwartungen erfüllt, kein API-Schreibzugriff aus der Sandbox.

### 5.4 Gesamt-Suite und CI

| Stand | Tests | Failures | Errors | Skipped |
|---|---|---|---|---|
| Basis `ba8dfc9` (vor #909, gestasht gemessen) | 3068 | 87 | 136 | 103 |
| Dieser Branch vor dem Merge | 3073 (+5) | 87 | 136 | 103 |

Die 223 Umgebungsbefunde sind identisch vor und nach den Änderungen (fehlende
Binären/optionale Module/Netzsperren in der Sandbox) – keine neue Regression.
Der PR-CI-Lauf **vor** dem Merge war vollständig grün (14 Checks, inkl.
`regression` mit kompletter Suite und echtem Hugo-Produktionsbuild in 18 Min.,
CodeQL js/python, Playwright, Manifest- und Integritäts-Wachen). Nach dem
Merge mit `main` läuft die Abnahme erneut.

### 5.5 Wizard-Probe in der Sandbox

- `GITHUB_ACTIONS=true bash … --check` → Exit 1 mit der CI-Sperrmeldung.
- `--check` mit dem eingeschränkten Token: E8/E1/E6 als offen benannt,
  unlesbare Secrets sauber als „nicht prüfbar“ deklariert, kein Absturz, Exit 1.

---

## 6. Betriebshandbuch (ab Merge 26.10.2026)

1. **Automatisch in der Nacht nach dem Merge:** Der nächste rote
   `Offsite-Backup`-Lauf löst den Lagebild-Verfall aus – #761 zeigt dann ohne
   Kommentar oder neue Nummer auf den jüngsten Lauf, bei unverändertem
   Einrichtungs-Rat (der Live-Harness in 5.3 hat genau das trocken bewiesen).
2. **Inhaber-Einrichtung (einmalig, ~10 Min., schließt #761 wirklich):**
   `npm run backup:einrichten` am eigenen Rechner (oder die sieben Schritte in
   `docs/ANLEITUNG-OFFSITE-BACKUP.md`; Reihenfolge E8 → E1–E7 ist erzwungen).
   Zustand zwischendurch: `npm run backup:status`.
3. **Abnahme:** Der erste grüne `Offsite-Backup`-Lauf schließt #761 über den
   `resolve`-Job selbst; danach `npm run backup:probe` (Restore-Drill) als
   Wiederherstellungsbeweis. Die Frischwache (13:00 UTC) wechselt ab
   Konfiguration von „nicht messbar“ auf echte 36/52-h-Messung.

## 7. Dauerhaftigkeit

| Mechanismus | Verankert | Bricht bei Regression |
|---|---|---|
| Lagebild-Verfall mit Reihenfolgeschutz (#909) | `alert-on-failure.yml` | 58 Sim-Szenarien + neuer Python-Strukturvertrag rot |
| Fail-open auch auf dem Verfalls-Pfad | gemeinsamer Update-Block | eigenes Sim-Szenario (API-Ablehnung bei Verfall) |
| Wizard-Kurzbefehle | `package.json`, Anleitung, `WizardVertrag` | Kabelbruch npm ↔ Wizard ↔ Anleitung wird Testrot |
| Fail-closed der Sicherung unangetastet | keine Workflow-Entschärfung | bestehende Backup-Verträge (33 Tests) |
| Manifest-Schutz | `manifest_guard.py` grün | L2 bei Lock/Manifest-Drift |

**Ergebnis:** Die seit dem 15.10. offene #761-Lücke „stale Meldung“ ist auf
`main` doppelt abgesichert – verhaltensgetrieben durch #909 und
vertraglich durch diesen PR – und der einzige verbliebene Auftragsteil
(Inhaber-Einrichtung) hat jetzt einen einzigen merkbaren Befehl. Der
nächste rote Nachtlauf hält #761 automatisch ehrlich; der erste grüne Lauf
nach der Einrichtung schließt den Vorgang wie vorgesehen selbst.
