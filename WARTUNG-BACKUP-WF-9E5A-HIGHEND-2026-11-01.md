# Wartung · Sicherung · WF-9E5A #923 — Highend-Dauerheilung (01.11.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #923 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Branch:** `arena/fd10df48-franksfinanzcheck-blog`
**Basis:** `49a4abdbc971319f1c761c1503ae62f8830e3137` (`main`, 31.10.2026)
**Bearbeiter:** Arena Agent · **Vorgänger:** `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-10-29.md`

---

## 1. Live-Befund — nachgewiesen, nicht geraten

| Prüfung (01.11.2026, gegen die echte GitHub-API) | Ergebnis |
|---|---|
| Issue [#923](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/923) | offen, zuletzt nachgeführt 31.10. 09:09 UTC |
| Lauf `41187477202` (31.10.) | `backup`-Job **success**, `kv-backup`-Job **failure** im Schritt „Voraussetzungen prüfen (fail-closed – kein Schein-Grün)“ |
| Zwölf Läufe vom 22.–31.10. | **alle** `failure` — derselbe Schritt, dieselbe Ursache |
| Check-Run-Annotationen | E1 `BACKUP_REPO`, E2 `BACKUP_REPO_TOKEN`, E3 `BACKUP_PASSPHRASE`, E5 `CF_KV_BACKUP_TOKEN`, E6 `KV_NAMESPACE_ID_ABO` fehlen; E4 vorhanden; E7 optional; E8 Warnung |
| Environment `backup` | `deployment_branch_policy: null`, `protection_rules: []` (E8 offen) |
| Repository `frank-hartung/franksfinanzcheck-backup` | **404** — existiert nicht |
| `backup-frischwache.yml` (13:00 UTC) | seit 27.10. durchgehend **grün** — sie meldet bewusst kein Rot, sondern einen Hinweis (E1/E2 offen) |

**Kann ein Agent das schließen?** Nein — und das ist belegt, nicht behauptet.
Die Schreib-Endpunkte wurden angesprochen und antworten mit
`403 Resource not accessible by integration`:

```text
PUT    repos/…/environments/backup          → 403   (E8)
POST   repos/…/actions/variables             → 403   (E1, E6)
POST   user/repos   (privates Ziel anlegen)  → 403   (E1)
GET    repos/…/actions/secrets               → 403   (Nachweis E2/E3/E5)
```

Es wurden **keine** Secrets, Variablen, Repositories oder Environment-Regeln
erfunden, überschrieben oder in Chat/Repository abgelegt. Secret-Werte sind aus
GitHub grundsätzlich nicht lesbar. Der Live-Blocker ist damit transparent auf
die Inhaber-Einrichtung reduziert (`npm run backup:einrichten`, E8 → E1–E7).

---

## 2. Was in diesem Stand tatsächlich dauerhaft geheilt wurde

Der Auftrag lautet „dauerhaft auf Highend-Niveau“. Die Einrichtung kann nur der
Inhaber vornehmen — **die Widerstandsfähigkeit der Wachen kann und muss der Code
leisten.** Drei echte Defekte wurden reproduziert und behoben. Alle drei gehören
zur Klasse „grün, ohne geprüft zu haben“ — der Klasse, aus der auch #923
entstanden ist.

### L-01 · Der Restore-Drill meldete „bestanden“, ohne etwas geprüft zu haben

**Reproduktion (vorher, echter Aufruf):**

```text
$ bash scripts/restore_drill.sh --repo a/b --nur-git --nur-kv
== Restore-Drill (2026-11-01 09:34 UTC) · Quelle: a/b (privat, Entwürfe) ==
✅ RESTORE-DRILL BESTANDEN – die geprüften Sicherungen sind vollständig wiederherstellbar.
```

Exit **0**, keine Datei angesehen. Genau dieser Satz wäre im Betrieb als
Wiederherstellungs-Nachweis zitiert worden — und `restore_drill.sh` ist die
einzige Stelle, die die Kernzusage „RTO < 60 Min., wiederherstellbar“ belegt.

**Ursache:** Beide Familien sind voreingestellt (`GIT=1`, `KV=1`); wer beide
abwählt, überspringt beide Blöcke und fällt ungebremst in den Erfolgssatz.

**Heilung:**
- Der Lauf zählt die **tatsächlich geprüften Familien** (`GEPRUEFT`).
- Ohne geprüfte Familie: Exit **2** mit „Es wurde NICHTS geprüft“ — kein
  Bestanden, kein stiller Erfolg.
- Der Abschluss nennt den Nachweis: `geprüft: Abonnenten (KV), Repository
  (Git-Bundle, 25 Dateien).`
- Zusatzbefund derselben Prüfung: `git clone` aus einem Bundle, dessen HEAD auf
  keinen enthaltenen Ref zeigt, legt mit einer bloßen **Warnung** einen leeren
  Arbeitsbaum an. Der Drill wählte daraufhin keinen Branch und scheiterte mit
  „kein HEAD im Restore“, obwohl das Bundle in Ordnung war. Jetzt wird der
  Branch aus `git bundle list-heads` bestimmt (`main` bevorzugt) und mit
  `--branch` geklont.

### L-02 · Die Frische-Wache verwarf ihre eigene Eingabe (`--repo`)

**Reproduktion (vorher):**

```text
$ python3 scripts/backup_freshness_guard.py --repo frank-hartung/franksfinanzcheck-backup --json
{ "repo": "", "urteil": "fehler", "text": "Kein gültiges Backup-Repo angegeben …" }   # Exit 1
$ python3 scripts/backup_freshness_guard.py frank-hartung/franksfinanzcheck-backup
error: unrecognized arguments: …                                                        # Exit 2
```

Genau diese beiden Formen stehen in der Anleitung und in
`npm run backup:frische`. Ursache war ein Vorrang-Fehler in einer Zeile:

```python
repo = args.repo or sys.argv[1] if len(sys.argv) > 1 and "/" in sys.argv[1] else ""
#     └──────────── (a or b) if Bedingung else ""  ────────────┘
```

Die Bedingung gilt auch für den über `--repo` übergebenen Wert: ohne
Positionsargument immer `""` — ein Fehlalarm über eine Eingabe, die da war.
Im Workflow fiel das nie auf, weil dort `BACKUP_REPO` als Umgebungsvariable
greift; lokal und in jeder Anleitung war die Wache unbrauchbar.

**Heilung:** `repo_bestimmen()` (Flag → Positionsargument → `BACKUP_REPO` →
`ZIEL_REPO`, fail-closed ohne jede Angabe) und `token_bestimmen()` (Ziel-Secret
vor dem allgemeinen Lauf-Token), dazu ein Positionsargument im Parser.
Der Selbsttest prüft zusätzlich den **echten Kommandozeilenweg**.

### L-03 · Ein roter Rückweg-Nachweis bekam den falschen Rat — und lief zu spät

- Der Schritt „Kurzprüfung Wiederherstellbarkeit“ in `backup-frischwache.yml`
  trug `if: always()`. Eine **Nachweis**-Prüfung, die auch nach einem roten
  Vorgänger läuft, ist die Umkehrung von fail-closed: Ihr Ergebnis hing am
  Ausgang einer anderen Messung. `if: always()` entfernt — der Schritt läuft
  jetzt schlicht immer, solange der Job nicht abgebrochen ist.
- War der Schritt rot, griff der allgemeine Frische-Rat („Scheduler-Hänger,
  Token widerrufen, neu starten“). Ein Syntaxfehler in `restore_drill.sh`
  bleibt bei jedem Neustart. Neue Alarm-Klasse **`backup-restore`** mit eigenem
  Rat (Code reparieren, `npm run test:backup`, `npm run backup:probe`), gebunden
  an die beiden Backup-Workflows — ein gleichnamiger Schritt in einem fremden
  Kanal behält sein Runbook (Gegenprobe in der Simulation).
- Dieselbe Kurzprüfung führt jetzt die **Gegenprobe** aus: Ein Drill ohne
  geprüfte Familie muss Exit 2 liefern, sonst ist der Schritt rot. Damit ist
  L-01 jeden Tag automatisch bewacht, nicht nur im Test.

---

## 3. Regressionsschutz (dauerhaft, nicht punktuell)

| Vertrag | Datei | Inhalt |
|---|---|---|
| `RueckwegVertrag` (3 Tests) | `scripts/tests/test_backup_einrichtung.py` | Exit 2 ohne geprüfte Familie · gesunde Sicherung wird **mit Nachweis** bestanden (echtes Bundle + echtes `openssl`) · falsche Passphrase bleibt rot |
| `FrischwacheKommandozeile` (3 Tests) | dieselbe Datei | `--repo` ohne Positionsargument kommt an · Positionsargument bleibt erlaubt · ohne jede Angabe fail-closed |
| Selbsttest F12/F13 | `scripts/backup_freshness_guard.py` | `repo_bestimmen`/`token_bestimmen` inkl. Kommandozeile (13. Fallgruppe) |
| `test_wf_9e5a_923_rueckweg_hat_eigenes_runbook` | `scripts/tests/test_alert_scoping.py` | Klasse `backup-restore` existiert, steht **vor** `backup-frisch` und **nach** `backup-einrichtung`; Rat nennt echte Dateien; Simulationsszenario + Gegenprobe vorhanden |
| Simulation `#923` + `#923-Gegenprobe` | `scripts/tests/sim/alert_scoping_sim.mjs` | 71 Szenarien; der neue Rat wird **ausgeführt**, nicht nur im Text gesucht |

---

## 4. Abnahme

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/backup_freshness_guard.py --selftest` | ✅ 13 Fallgruppen |
| `python3 scripts/backup_einrichtung.py --selftest` | ✅ 18 Fallgruppen |
| `python3 scripts/kv_backup.py --selftest` | ✅ |
| `python3 -m unittest scripts.tests.test_backup_einrichtung` | ✅ 47 Tests (13 YAML-Skips ohne PyYAML lokal) |
| `python3 -m unittest scripts.tests.test_alert_scoping` | ✅ 29 Tests, Simulation **71/71** Szenarien |
| `python3 scripts/workflow_js_wache.py --check` | ✅ alle `github-script`-Blöcke kompilieren |
| `python3 scripts/trigger_wache.py --check` | ✅ 98 Workflows, 0 Befunde |
| `python3 scripts/alert_issue_identity.py --selftest` | ✅ 65 Workflows, 65 eindeutige Codes |
| `bash -n scripts/restore_drill.sh` · `bash -n scripts/backup_einrichten_wizard.sh` | ✅ |
| YAML-Parse beider Backup-Workflows (PyYAML) | ✅ |
| Restore-Drill gegen echtes Bundle + echtes KV-Export (positiv, negativ, Gegenprobe) | ✅ |

---

## 5. Was der Inhaber noch tun muss (unverändert, ehrlich)

Die Sicherung selbst kann nur mit echten Zugangsdaten laufen. Am eigenen Rechner:

```bash
npm run backup:einrichten     # E8 zuerst, dann E1–E7; Geheimnisse verdeckt
npm run backup:status         # Stand prüfen, ohne etwas zu ändern
```

Alternativ die sieben Schritte in `docs/ANLEITUNG-OFFSITE-BACKUP.md`.
Danach Actions → „Offsite-Backup“ → „Run workflow“ (`main`) und anschließend
`npm run backup:probe`.

**Abnahmekriterium für #923:** ein grüner `KV-/D1-Backup`-Job auf `main`, ein
privates Entwurfs-Release `kv-backup-*` mit Größen-/Draft-Nachweis und danach
ein erfolgreicher Restore-Drill. Bis dahin bleibt #923 offen — das ist der
korrekte, auditierbare Zustand. Ein `Run workflow` ohne Einrichtung wäre kein
Fix, sondern nur ein weiterer roter Nachweis.

---

## 6. Bewusste Grenzen

- Keine Secrets, Passphrasen oder Token im Code, in Issues, im Bericht oder in
  Logs; kein erfundener Wert, um „grün“ zu erzeugen.
- Kein `continue-on-error`, kein Überspringen des KV-Exports, kein
  automatisches Schließen von #923.
- Keine manuelle Umschrift offener Alarm-Issues — das Alerting führt sie mit
  dem nächsten roten Lauf selbst nach.
- Kein Öffnen des Drill-Erfolgssatzes „aus Prinzip“: Exit 2 nur dort, wo
  tatsächlich nichts geprüft wurde; ein echter Lauf bleibt Exit 0.
