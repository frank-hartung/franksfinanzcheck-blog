# Wartung · Sicherung · WF-9E5A #923 — Highend-Dauerheilung (02.11.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #923 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Branch:** `arena/964aa8dd-franksfinanzcheck-blog`
**Basis:** `876ea5afe959374c5f96ee61d6e1f5e4507432ce` (`main`, 02.11.2026)
**Bearbeiter:** Arena Agent · **Vorgänger:** `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-01.md`

---

## 1. Warum dieser Bericht nicht die Fortschreibung des letzten ist

Die Vorgängerberichte haben den **Live-Blocker** korrekt beschrieben (E1–E6
fehlen, E8 offen, Einrichtung ist Inhaber-Sache) und den Rückweg-Beweis
gehärtet. Genau deshalb ist die Meldung am 02.11.2026 noch offen — und genau
deshalb war der bisherige Blick zu schmal: **Alle sichtbaren Wachen waren
grün, während die eigentliche Sicherung seit dem 15.10.2026 nicht ein einziges
Mal gelaufen ist.** Diesmal habe ich nicht den Bericht gelesen, sondern die
Wachen selbst ausgeführt — und dabei vier echte Fehlverhalten reproduziert, die
alle zur selben Klasse gehören: *„grün, ohne geprüft zu haben“*.

## 2. Live-Befund (02.11.2026, 09:20 UTC, gegen die echte GitHub-API)

| Prüfung | Ergebnis |
|---|---|
| Lauf `41295239096` (01.11., 09:56 UTC) | `backup` **success**, `kv-backup` **failure** in „Voraussetzungen prüfen“ |
| Zehn Läufe 23.10.–01.11. | **alle** `failure`, derselbe Schritt, dieselbe Ursache |
| Erwarteter Lauf **02.11., 03:00 UTC** | **fehlt** — Scheduler-Aussetzer, nicht nachgeholt |
| Frischwache `41335523844` (01.11., 18:13 UTC) | **success** — bei offenem E1/E2 und **null** Sicherungen |
| Environment `backup` | `deployment_branch_policy: null`, `protection_rules: []` |
| `frank-hartung/franksfinanzcheck-backup` | **404** — existiert nicht |
| Variablen/Secrets lesen (Agenten-Token) | `403 Resource not accessible by integration` |

Die Inhaber-Einrichtung ist unverändert der Blocker und kann von einem Agenten
nicht hergestellt werden. Was ein Agent aber **muss**, ist dafür zu sorgen,
dass dieser Zustand nicht als Erfolg gemeldet wird. Drei Wachen taten genau
das.

### 2a. Nachtrag 12:55 UTC — der Lauf von heute bestätigt die Heilung

Zwischen Befund und Abgabe lief **`41428440948` (02.11., 10:23 UTC)**, der erste
Lauf nach dem fail-closed-Stand im Offsite-Workflow:

| Job | Ergebnis |
|---|---|
| `backup` (Bundle + Release) | success |
| `KV-/D1-Backup` | **failure**, Schritt 4 „Voraussetzungen prüfen (fail-closed – kein Schein-Grün)“ |
| Frischwache | noch nicht neu gelaufen — dort greift diese Abgabe |

Der Job scheitert jetzt **an der Sache** und nennt sie im Klartext (Annotation
aus dem Lauf, gekürzt):

- `Environment backup: jeder Branch darf das Environment nutzen … Selected → nur main`
- `fehlt → KV_NAMESPACE_ID_ABO` (Repository-Variable)
- `fehlt → CF_KV_BACKUP_TOKEN` (Secret, Workers KV: Read)
- `fehlt → BACKUP_PASSPHRASE` (Secret, 32+ Zeichen)
- `fehlt → BACKUP_REPO_TOKEN` (Secret, fine-grained, nur Backup-Repo)
- `fehlt → BACKUP_REPO` (Variable; Repo `frank-hartung/franksfinanzcheck-backup` → 404)

Das ist der gewünschte Zustand: **rot an der richtigen Stelle, mit Adresse**
statt grün über einer offenen Lücke. Kein Punkt davon ist durch Code heilbar –
jeder braucht eine Entscheidung des Inhabers. Nachgeprüft um 12:55 UTC:
`backup` hat weiterhin `protection_rules: []` und
`deployment_branch_policy: null`, das Ziel-Repo antwortet **404**.

## 3. Die vier Defekte — reproduziert, nicht behauptet

### L-01 · Die RPO-Wache meldete zehnmal grün, ohne etwas zu überwachen

**Reproduktion (Lauf 41335523844):** Job `Backup-Frische pruefen (RPO 24 h /
52 h)` = **success**, Schritt 6 „Frische messen“ = success — obwohl
`BACKUP_REPO` und `BACKUP_REPO_TOKEN` fehlten. Ursache: Schritt 5 hieß
„Einrichtung als Kontext (kein Block, nur Einordnung)“ und endete fest mit
`exit 0`; der Fehlstand erschien als `::notice::` im Log, das kein Alerting
liest. Schritt 6 übersprang die Messung stillschweigend mit
`::warning::` und `exit 0`.

> Eine Wache, die „es gibt keine Sicherung“ als Erfolg ausgibt, verdeckt genau
> den Ausfall, den sie überwacht — für alle Zeit, weil niemand mehr hinsieht.

**Heilung:** Der Schritt heißt jetzt „Voraussetzungen prüfen (fail-closed – kein
Schein-Grün)“, ruft `backup_einrichtung.py --pruefen` und wird bei offenem
Punkt rot. Das Alerting ordnet ihn der Klasse `backup-einrichtung` zu (nicht
`backup-frisch`): Ein Scheduler-Hänger ist keine plausible Ursache für eine
Sicherung, die nie eingerichtet wurde.

### L-02 · Der Einrichtungs-Wizard meldete „alle Pflichtpunkte eingerichtet“ bei vier ungeprüften Secrets

**Reproduktion (echter Aufruf mit einer `gh`-Attrappe: Variablen lesbar,
Secret-Liste 403, Environment-API 404):**

```text
❌ → vorher:
  ⚠️  E8 nicht prüfbar (...)          ⚠️  E3/E2/E5 nicht prüfbar (...)
==> Ergebnis
  Alle Pflichtpunkte sind eingerichtet.        EXIT 0
```

`hinweis()` zählte nicht in `OFFENE`; der Abschluss prüfte nur `OFFENE == 0`.
Fünf von acht Punkten waren also **nicht bestätigt** — und das Ergebnis lautete
Grün. Genau dieser Aufruf steht als `npm run backup:status` in der Anleitung.

**Heilung:** Eigener Zustand `ungeprueft` (Symbol ❓, eigener Zähler). Grün nur
noch bei `OFFENE == 0 && UNGEPRUEFT == 0`. Fehlen nur Leserechte, sagt der
Abschluss ausdrücklich „NICHT bestätigt — das ist kein Grün“ und verweist auf
den echten Beleg (Lauf + Job-Zusammenfassung). Exit 1.

### L-03 · Der Export verwandelte Fehler in „leer“ — an drei Stellen

| Fall | vorher | jetzt |
|---|---|---|
| D1 antwortet `success: false` (HTTP 200) | Tabelle mit `[]` Zeilen, Export gültig, Probe grün | `RuntimeError` mit Cloudflare-Code (7403), Lauf rot |
| KV-Namespace enthält 0 Schlüssel (falsche ID/Konto) | Probe `[]` → „vollständig“ | Befund; akzeptiert nur mit live gelesenem Namespace-Titel (`leer_bestaetigt`) |
| `--wrangler-bulk` verwirft alle Schlüssel (Ablauf vorbei) | leere Datei, **Exit 0** | Hinweis mit Präfix+Kurzhash, **Exit 1** bei leerer Datei |
| Probe bemängelt den Export (`kv_backup.py --out`) | nur `::warning::`, Datei wurde trotzdem verschlüsselt und abgelegt | `::error::` + **Exit 1**, nichts wird abgelegt |

Die erste Zeile ist die gefährlichste: Ein Klick-Zähler, der still auf 0
zurückfällt, wäre erst im Ernstfall aufgefallen — also in dem Moment, in dem die
Sicherung gebraucht wird. Zusatzbefund derselben Prüfung: Ein TLS-Abbruch
erzeugte einen rohen Traceback statt einer Zeile mit Abhilfe (`NetzwekFehler`,
jetzt eine Meldung mit Statuslink).

### L-04 · Probe und Wache machten zwei verschiedene Zusagen über dieselbe Sicherung

`restore_drill.sh` warnte erst ab **48 h** und meldete danach weiter
„RESTORE-DRILL BESTANDEN“, während `backup_freshness_guard.py` dieselbe
Sicherung ab **52 h** als RPO-Verstoß rot färbt (Gelb ab 36 h). Zwei Grenzen für
eine Zusage sind eine Zusage zu viel.

**Heilung:** `MAX_ALTER_WARN_H=36`, `MAX_ALTER_ROT_H=52` — über der Toleranz
endet der Drill mit Exit 1 und nennt den Datenverlust in Stunden. Anleitung und
ein Vertragstest halten die Zahlen an der Wache fest.

## 4. Regressionsschutz (dauerhaft, nicht punktuell)

| Vertrag | Datei | Inhalt |
|---|---|---|
| `Exportvertrag` (5 Tests) | `scripts/tests/test_backup_einrichtung.py` | D1-Störung ≠ leere Tabelle · Leerstand nur mit Beleg · D1 ohne Zeilenliste · leere Rückspiel-Datei = Exit 1 · Probe-Befund beendet den Export rot |
| `FrischwacheEinrichtungVertrag` (3) | dieselbe Datei | Einrichtung blockiert die Wache (kein `exit 0`, kein `\|\| true`) · Schrittname wird vom Alerting erkannt · Simulation prüft beide Richtungen |
| `WizardScheinGruenVertrag` (2) | dieselbe Datei | `ungeprueft` ist eigener Zustand; Abschluss verlangt beide Zähler · **echter Aufruf gegen eine `gh`-Attrappe** muss Exit 1 liefern |
| `RueckwegFrischeVertrag` (2) | dieselbe Datei | Drill-Grenzen = Wachen-Grenzen (36/52) · Anleitung nennt dieselben Zahlen |
| Selbsttest `kv_backup.py` F-E1…F-E7 | `scripts/kv_backup.py` | sieben neue Fallgruppen, offline, inkl. Netzausfall ohne Traceback und ohne Exportdatei |
| Simulation `#923` + 2 Gegenproben | `scripts/tests/sim/alert_scoping_sim.mjs` | **76 Szenarien**; der neue Rat wird ausgeführt, nicht im Text gesucht |

Bewusste Gegenproben (damit die Heilung nicht überzieht): Ein echter
Frischebefund behält den RPO-Rat; derselbe Schrittname in einem fremden
Workflow behält sein Runbook; ein belegt leerer Namespace bleibt gültig.

## 5. Abnahme (alle Befehle in diesem Stand ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/kv_backup.py --selftest` | ✅ inkl. F-E1…F-E7 |
| `python3 scripts/backup_einrichtung.py --selftest` | ✅ 18 Fallgruppen |
| `python3 scripts/backup_freshness_guard.py --selftest` | ✅ 13 Fallgruppen |
| `python3 -m unittest scripts.tests.test_backup_einrichtung` | ✅ **60 Tests** (lokal 13 YAML-Skips; in CI-Nachahmung mit PyYAML alle 60) |
| `python3 -m unittest scripts.tests.test_alert_scoping` | ✅ 30 Tests, Simulation **76/76** |
| `bash scripts/restore_drill.sh --repo … --nur-git --nur-kv` | ✅ Exit 2, „Es wurde NICHTS geprüft“ |
| `python3 scripts/workflow_js_wache.py --check` | ✅ alle `github-script`-Blöcke kompilieren |
| `python3 scripts/trigger_wache.py --check` | ✅ 98 Workflows, 0 Befunde |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ 626 Dateien |
| `python3 scripts/wachen_vertrag.py` | ✅ 372 Skripte, 0 Funde |
| `python3 scripts/alert_issue_identity.py --selftest` | ✅ 65 Workflows, 65 eindeutige Codes |
| `python3 scripts/manifest_guard.py` · `abhaengigkeits_wache.py --check` | ✅ grün |
| Wizard `--check` gegen `gh`-Attrappe | ✅ **Exit 1**, „5 Punkt(e) NICHT bestätigt“ |
| YAML-Parse beider Backup-Workflows | ✅ (Schrittfolge geprüft) |
| **Volle Suite unter CI-Bedingungen** (`GITHUB_ACTIONS=true`, `requirements-ci.txt` im venv) | ✅ **5030 Tests, OK** (15 Skips) |
| Uhr-Probe (`selftest_clock.py --trap-discover scripts/tests --offset 97`) | ✅ 5030 Tests unter +97 Tagen grün |
| KI-Probe `selftest_ki.py --trap-workflows` | ✅ 153 Selbsttests ohne Modell/Netz |

### 5a. Nebenbefund aus der CI (gefunden, nicht gesucht)

Der erste CI-Lauf dieser Abgabe war im Job „Code-Regression“ rot — **nicht**
wegen des Backups, sondern wegen zweier Fehler in der Prüftechnik:

1. Mein neuer Wizard-Vertrag lief unter `GITHUB_ACTIONS=true` in den CI-Riegel
   des Wizards („In CI verweigert“) statt in den geprüften Befund. Er hätte
   also lokal grün und in der CI rot gemeldet — ein Test, der die Umgebung
   nicht kennt, ist kein Vertrag. **Heilung:** Befundpfad läuft ohne
   CI-Marker, und der CI-Riegel ist jetzt selbst ein Vertrag
   (`test_in_ci_wird_der_menschen_schritt_verweigert`): Die Einrichtung darf in
   CI **nie** durchlaufen, weil die Runner-Rechte andere sind als am Rechner
   des Inhabers.
2. Zwei Sabotage-Tests von `actions_version_guard` schrieben ihr `::error::`
   auf stderr. In GitHub Actions wird daraus eine rote Annotation
   **„Actions-Pin-Drift – keine SHA erraten“**, die auf `.github` zeigt —
   obwohl die Wache driftfrei ist (`drift: 0`). Wer den Job liest, sucht den
   Fehler dann in den Actions-Pins statt in der Suite. **Heilung:** beide
   Tests fangen stderr ab; die Suite gibt unter CI-Bedingungen **0**
   `::error::`-Zeilen aus (gemessen).

## 6. Betriebsrisiko, das dieser Stand NICHT behebt — und was er stattdessen tut

1. **Fehlender Lauf am 02.11.** Der 03:00-UTC-Cron hat nicht gefeuert. Das ist
   ein Scheduler-Aussetzer, kein Codefehler; die Frischwache hätte ihn ab
   13:00 UTC erkannt (jetzt sogar als rot, siehe L-01).
2. **Ein Agent kann die Einrichtung nicht herstellen.** An Secrets, PAT und
   Cloudflare-Konto kommt er nicht; die Schreibendpunkte antworten mit 403. Es
   wurden **keine** Secrets, Variablen, Repositories oder Environment-Regeln
   erfunden, überschrieben oder in Chat/Repo abgelegt.
3. **Was der Inhaber tun muss (unverändert):**

```bash
npm run backup:einrichten     # E8 zuerst, dann E1–E7; Geheimnisse verdeckt
npm run backup:status         # Stand prüfen, ohne etwas zu ändern
```

Danach Actions → „Offsite-Backup“ → „Run workflow“ (`main`), anschließend
`npm run backup:probe`. **Abnahmekriterium für #923:** ein grüner
`KV-/D1-Backup`-Job auf `main`, ein privates Entwurfs-Release `kv-backup-*`
mit Größen-/Draft-Nachweis und ein bestandener Restore-Drill.

Bis dahin bleibt #923 offen — der korrekte, auditierbare Zustand. Ab jetzt ist
er allerdings **sichtbar**: Die Frischwache wird rot, statt zehn weitere Tage
grün zu bleiben, und der Wizard behauptet kein Grün mehr, das er nicht belegen
kann.

## 7. Bewusste Grenzen

- Keine Secrets, Passphrasen oder Token im Code, in Issues, im Bericht oder in
  Logs; kein erfundener Wert, um „grün“ zu erzeugen.
- Kein `continue-on-error`, kein `|| true`, kein Absenken einer Prüfung.
- Keine manuelle Umschrift offener Alarm-Issues — das Alerting führt sie mit
  dem nächsten roten Lauf selbst nach.
- Leerstand wird nicht bestraft, sondern belegt: Ein tatsächlich leerer
  Namespace bleibt gültig, sobald er live bestätigt ist.
