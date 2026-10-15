# Wartung · Sicherung · WF-9E5A · #761 – Dauerhafte Heilung

**Datum:** 15.10.2026

**Auslöser:** [Lauf `38701800402`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/38701800402)
des Workflows „Offsite-Backup“ (Zeitplan, `main`, Commit `19dbd96a`, 07:53 UTC). Der Job
**„KV-/D1-Backup (Abonnenten + Einwilligungsnachweise)“** schlug im Schritt
**„Voraussetzungen prüfen (fail-closed – kein Schein-Grün)“** fehl; gemeldet als
[Issue #761](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/761). Der Repo-Job
`backup` war grün.

**Urteil:** Weder ein vorübergehender Fehler noch ein abgelaufener API-Key. Der KV-Job kam am
15.10. um 00:09 UTC mit #750 (Sicherheitsaudit M-11) hinzu, und seine Zugänge wurden **nie
eingerichtet**: Fünf von sechs Voraussetzungen fehlten. Jeder weitere Lauf wäre rot geblieben,
ein Neustart hilft nicht. Das Rot selbst ist richtig – ohne Sicherung darf der Lauf nicht grün
sein. Falsch war alles drumherum: der Rat im Alarm, die Prüftiefe, ein toter Verweis, der
fehlende Vorlauf vor dem Ablauf eines Tokens und eine Rückspiel-Anleitung, die nichts
zurückgespielt hätte.

## 1. Befund (belegt)

| Beleg | Quelle |
|---|---|
| `kv-backup`: Schritt 4 rot, Selbsttest (Schritt 3) grün, Export und Ablage übersprungen | Jobs-API, Lauf 38701800402 |
| Annotation „KV-Backup nicht eingerichtet“: es fehlen Variable `BACKUP_REPO`, Secret `BACKUP_REPO_TOKEN`, Secret `BACKUP_PASSPHRASE`, Secret `CF_KV_BACKUP_TOKEN` und Variable `KV_NAMESPACE_ID_ABO`; vorhanden ist `CLOUDFLARE_ACCOUNT_ID` | `check-runs/116311519313/annotations` |
| Das Environment `backup` hat der erste Lauf angelegt (07:53:21 UTC) – **ohne Branch-Regel und ohne Schutzregeln** | Environments-API (live gelesen) |
| Der Worker-Deploy überspringt den Newsletter-Worker, weil `KV_NAMESPACE_ID_ABO` fehlt | Lauf 38657279461, Annotation |
| Das Formular ist geschaltet (`newsletterFormAction`), der Worker antwortet: „0 aktive Abonnenten“ | `hugo.toml` Z. 202; Newsletter-Lauf 38394201061 (13.10.) |

**Dringlichkeit:** Nach dem letzten Messpunkt (13.10.) gibt es noch keine aktiven Abonnenten.
Jede neue Anmeldung erzeugt aber einen Einwilligungsnachweis nach Art. 7 Abs. 1 DSGVO, der heute
**nur** in Cloudflare läge. Einzurichten ist deshalb jetzt, vor den ersten Anmeldungen.

**Bei der Analyse gefundene Folgefehler** (alle behoben, siehe Abschnitt 2):

1. **Falscher Rat im Alarm.** Er empfahl „API-Key abgelaufen (GROQ/GEMINI)“ und „neu starten“.
   Beides hilft bei einer unvollständigen Einrichtung nicht.
2. **Nur „gesetzt?“ geprüft.** Ein falscher Token-Umfang, ein falsches Konto oder ein baldiger
   Ablauf wären erst mitten im Export oder gar nicht aufgefallen. Die Antworten 401 und 404
   wurden als „nicht privat (UNBEKANNT)“ fehlgedeutet.
3. **Toter Verweis.** „siehe Umsetzungs-Runbook“ zeigte auf keine Datei im Repo.
4. **Latente Falle im Repo-Job.** `backup` lief ohne `environment: backup` und hätte die dort
   empfohlenen Secrets nicht gesehen. Folge wäre ein stiller Rückfall auf die 7-Tage-Kopie oder
   ein Abbruch mit „nicht privat“ gewesen.
5. **Kein Vorlauf vor dem Token-Ablauf.** GitHub schlägt für neue Tokens 30 Tage vor. Die
   Sicherung hätte nach einem Monat still aufgehört.
6. **Rückspielen ohne Wirkung.** Die dokumentierte Notfall-Wiederherstellung
   (`wrangler kv bulk put … --namespace-id <ID>`) schreibt mit dem gepinnten Wrangler 4.149.0 in
   die **lokale Simulation** und meldet trotzdem Erfolg. Am Paket geprüft:
   `isLocal(args, defaultValue = true)`.
7. **Veraltete Wiederherstellungs-Probe.** `restore_drill.sh` lud aus dem öffentlichen Repo (dort
   liegen seit dem 20.09. keine Sicherungen mehr), konnte nicht entschlüsseln und ließ die
   KV-Daten ganz aus.
8. **Veraltete Doku.** `INFRASTRUKTUR.md` und `ops_report.py` beschrieben noch einen S3-Plan.
9. **Der falsche Rat wäre stehen geblieben.** Das Alerting fasste eine offene Meldung nie wieder
   an (Dedupe → `return`). #761 hätte deshalb auch nach der Korrektur weiter zu GROQ/GEMINI
   geraten und auf den Lauf von 07:53 verlinkt, der noch keine Checkliste hat – bis zum ersten
   grünen Lauf. Dieselbe Lücke betraf jeden Vorgang, dessen Einordnung sich ändert.

## 2. Dauerhafte Korrektur

| Baustein | Änderung | Wirkung |
|---|---|---|
| `scripts/backup_einrichtung.py` (neu) | Prüft E1–E8 live: Ziel ≠ Quelle, Ziel **privat** und nicht archiviert, GitHub-Token gültig samt Ablaufdatum, Passphrase-Länge, Konto-ID, Cloudflare-Token aktiv (Nutzer- oder Konto-Token) samt Ablauf, Namespace mit **genau diesem** Token lesbar (Titel zur Kontrolle), D1 optional, Environment nur für `main` (Hinweis). 3 Versuche bei Netz-/5xx-Fehlern. | Jeder offene Punkt erscheint als Annotation **und** als Checkliste mit vorbelegtem Link in der Job-Zusammenfassung. Fail-closed bleibt (Exit 1). |
| Fristen | Ablaufdaten wandern als `BACKUP_FRIST_TAGE` in die Job-Umgebung; neuer letzter Schritt „Fristwarnung“ (`--fristen`) | Unter 30 Tagen: Hinweis. Unter 14 Tagen: Schritt rot und das Alerting meldet sich – **nach** der Sicherung, nicht statt ihr. |
| `backup-offsite.yml` | Die Inline-Prüfung wird durch den Prüfer ersetzt (Schrittname bleibt). Selbsttest im Job. Repo-Job mit `environment: backup`. KV-Ablage prüft Entwurf + Größe und räumt Teil-Releases ab. Ehrliche Fehlertexte (API-Antwort statt „UNBEKANNT“). Lesendes `actions: read` für E8. | Keine Schein-Grün-Lücke, keine halben Sicherungen in der Aufbewahrung, keine stille Environment-Falle. |
| `alert-on-failure.yml` | Drei Klassen, gebunden an `wfName === 'Offsite-Backup'`: **Einrichtung unvollständig** (Neustart hilft nicht → Checkliste + Anleitung), **Fristwarnung** (Sicherung gelaufen, Zugang erneuern), übrige Backup-Fehler (Status-Seiten, Fehlerbilder). Anleitung und Läufe sind verlinkt statt nur benannt. | Kein GROQ/GEMINI-Rat mehr für Backup-Fehler. Gleichnamige Schritte in anderen Workflows behalten ihr Runbook (Gegenprobe in der Simulation). |
| `alert-on-failure.yml` – Lagebild nachführen | Jeder Body trägt die Klasse seines Rats (`<!-- alert-runbook: … -->`), eine Quelle für Marker **und** Runbook-Wahl. Ändert sich die Klasse, schreibt der nächste rote Lauf die offene Meldung neu: gleiche Nummer und Titel, aktueller Lauf, „Offen seit“, keine Benachrichtigung. Gleiche Klasse → keine Umschrift. Unbekannte Job-Lage → keine Umschrift. API-Fehler → fail-open. | #761 bekommt beim ersten roten Lauf nach dem Merge den Einrichtungs-Rat und den Link auf die Läufe mit Checkliste – ohne Handkommentar. Gilt für jeden Vorgang; offene Meldungen ohne Klassen-Marker (#761, #767) werden einmal nachgeführt. |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` (neu) | Einrichtung in 7 Schritten mit vorbelegten Links, Prüfpunkt-Tabelle, Fehlerbilder, „Zugänge erneuern“, Probe und Notfall-Wiederherstellung | Ersetzt den toten Verweis. Die Links sind wörtlich dieselben wie im Prüfer (per Test erzwungen). |
| `scripts/restore_drill.sh` | Holt die neuesten Entwürfe aus dem privaten Repo, entschlüsselt in ein 0700-Temp-Verzeichnis, beweist KV (`kv_backup.py --pruefen`) und Git (Clone + Struktur), warnt ab 48 h Alter. Läuft auch unter macOS. | Wiederherstellung wird beweisbar statt angenommen. |
| `scripts/kv_backup.py` (nur Kopfkommentar) | Rückspielen mit `--remote`, mit Begründung | Die Notfall-Wiederherstellung schreibt wirklich nach Cloudflare. |
| `scripts/ki_transportweg.py` | T6-Ausnahme für den Prüfer (Verwaltungs-API, kein Modell), wie zuvor für `kv_backup.py` | Ausgleich: Ein Test erlaubt nur die vier Verwaltungspfade – kein `/ai/`, kein anderer Anbieter. |
| `CLAUDE.md`, `INFRASTRUKTUR.md`, `ops_report.py`, `package.json` | Dauervorgabe „Fail-closed bleibt“, aktuelle Backup-Beschreibung, `npm run test:backup` | Der nächste Agent „heilt“ das Rot nicht mit `continue-on-error`. |

**Bewusst nicht getan:**

- **Kein Grün ohne Sicherung.** Es gibt weder `continue-on-error` noch eine Bedingung „nur wenn
  das Secret gesetzt ist“.
- **Keine Wiederverwendung fremder Tokens.** `CLOUDFLARE_API_TOKEN` (Workers AI) und
  `CF_WORKERS_DEPLOY_TOKEN` (schreibend) bleiben außen vor.
- **Keine Einstellungen am Environment.** Sie sind Inhabersache; der Prüfer meldet sie nur.
- **Kein Kommentar an #761.** Issue-Kommentare sind Markenfläche.

## 3. Was nur der Inhaber tun kann (etwa 10 Minuten)

Agenten können Secrets weder lesen noch setzen. Die Schritte im Einzelnen (mit vorbelegten Links)
stehen in [`docs/ANLEITUNG-OFFSITE-BACKUP.md`](docs/ANLEITUNG-OFFSITE-BACKUP.md):

1. Privates Repo `franksfinanzcheck-backup` anlegen und Repository-Variable `BACKUP_REPO` setzen.
2. Passphrase (32+ Zeichen) **erst im Passwort-Manager speichern**, dann als Secret
   `BACKUP_PASSPHRASE` im Environment `backup` eintragen.
3. Fine-grained Token anlegen: nur das Backup-Repo, Contents Read/Write, **366 Tage**. Als
   `BACKUP_REPO_TOKEN` im Environment `backup` speichern.
4. Cloudflare-Konto-Token anlegen, nur „Workers KV Storage: Read“. Als `CF_KV_BACKUP_TOKEN` im
   Environment `backup` speichern.
5. ID des Namespace, den der laufende Worker `ff-newsletter` als `ABO` gebunden hat, als
   Repository-Variable `KV_NAMESPACE_ID_ABO` eintragen. **Hinweis:** Damit gilt auch der
   Worker-Deploy als bereit (siehe Anleitung, Schritt 5).
6. Environment `backup`: Deployment branches **nur `main`**, keine Required reviewers.
7. Actions → „Offsite-Backup“ → „Run workflow“ (Branch `main`). Der grüne Lauf schließt #761
   automatisch (Job `resolve`). Danach einmal die Probe fahren:
   `bash scripts/restore_drill.sh --repo frank-hartung/franksfinanzcheck-backup`.

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| Nachstellung der #761-Lage (nur Konto-ID gesetzt) | **exakt die 5 offenen Punkte des echten Laufs** (E1, E2, E3, E5, E6), Exit 1, je Punkt Annotation + Link |
| E8 live gegen das echte Environment `backup` | Hinweis „jeder Branch darf das Environment nutzen“ – entspricht der API (Branch-Regel `null`) |
| `backup_einrichtung.py --selftest` | 16 Fallgruppen grün (u. a. öffentliches Ziel, 401/404, Fristen, Konto-Token, KV-/D1-Rechte, Netzausfall + Wiederholung, vergiftete Secret-Werte, Kodierung) |
| Mutationsproben am Prüfer | 4 von 4 eingebauten Fehlern erkannt (öffentliches Ziel, Secret in der Ausgabe, Wiederholung entfernt, Fristgrenze) |
| `npm run test:backup` (`test_backup_einrichtung`) | 24 Tests grün; 6 Mutationsproben an Workflow, Anleitung, Namen und Transport erkannt |
| Alarm-Simulation (`alert_scoping_sim.mjs`) | **34/34** Szenarien grün, davon 10 neu: #761-Nachstellung, Fristwarnung, Export-Fehler, Gegenprobe fremder Workflow; Nachführung des echten #761-Bodys, Idempotenz, Klassenwechsel, Job-API-Ausfall, API-Fehler beim Nachführen, Bestand eines fremden Workflows. Jede Klasse wird beim Anlegen auf ihren Marker geprüft; Abstürze zählen als benannter Fehler. |
| Mutationsproben am Alarm-Skript | 8 von 8 erkannt (Nachführung fehlt, Job-Lage-Wächter fehlt, kein catch, tägliche Umschrift, Klassen vertauscht, Marker fehlt, falsche Zeitquelle, Duplikat trotz Nachführung); am Struktur-Test 7 von 7 |
| `restore_drill.sh` mit echten Artefakten (gleiche openssl-Parameter wie der Workflow) | 6/6 Fälle korrekt: Bestanden · falsche Passphrase · verwaister Token · altes Aufrufformat · kein Ziel · kein Terminal; keine Klartext-Reste |
| `selftest_ki.py --trap-workflows` | 123 Selbsttests ohne Netz grün (der neue wird erkannt) |
| `selftest_clock.py` (Uhr +97 / −400 / +3650 Tage) | Selbsttest und Testmodul deterministisch grün |
| `test_workflow_yaml`, `test_alert_scoping`, `test_zugangs_namensvertrag`, `test_ki_transportweg` | grün |
| Gesamte Suite `unittest discover -s scripts/tests` | **3217 Tests grün** (12 übersprungen, Vorbestand; keiner davon aus dieser Änderung) |
| `bash -n` aller `run:`-Blöcke, `py_compile`, `node --check`, YAML, `git diff --check`, `manifest_guard.py` | grün |

**Grenzen dieser Umgebung:**

- **Kein Live-Test mit echten Zugängen.** Cloudflare-Konto und Secrets sind hier nicht
  erreichbar. Die Live-Pfade E2/E5/E6/E7 sind deshalb mit nachgebildeten API-Antworten geprüft.
  Der Prüfer wertet HTTP-Status aus; Cloudflare-Fehlercodes zeigt er nur an.
- **Wiederherstellung bis zum Download geprüft.** `gh release download` löst Release und Asset
  korrekt auf (an einem öffentlichen Repo belegt). Den Download selbst blockiert diese Umgebung
  (Asset-Host gesperrt).
- **Kein Hugo-Build.** Hugo ist hier nicht installiert; die Probe prüft dann strukturell (so
  vorgesehen).

## 5. Abschluss des Vorgangs

Der Vorschlag nennt **`Refs #761`**, nicht `Closes #761`. Schlösse der Merge die Meldung, stünde
dort „behoben“, während die Sicherung bis zur Einrichtung weiter rot wäre – ein Schein-Grün auf
Vorgangsebene. Nachweis ist der erste grüne Lauf von „Offsite-Backup“; ihn erkennt der Job
`resolve` in `alert-on-failure.yml` und schließt #761 dann selbst.

Bis dahin hält sich #761 selbst aktuell: Der erste rote Lauf nach dem Merge ersetzt den
GROQ/GEMINI-Rat durch den Einrichtungs-Rat und verlinkt die Läufe mit der Checkliste. Es entsteht
keine neue Nummer und kein Kommentar.
