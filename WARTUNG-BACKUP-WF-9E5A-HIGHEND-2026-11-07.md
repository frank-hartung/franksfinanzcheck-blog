# Wartung · Sicherung · WF-9E5A #923 — Highend-Dauerheilung (07.11.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #923 — dauerhaft auf Highend-Level einer Profi-Agentur beheben, mit automatischer Selbstheilung.`
**Branch:** `arena/41cd7103-franksfinanzcheck-blog` · **Basis:** `4d60e220` (`main`, 07.11.2026, 08:40 UTC)
**Pull Request:** #1124 · **Bearbeiter:** Arena Agent · **Vorgänger:** `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-03.md`

---

## 0. Die eine Lehre dieses Tages

Dreimal habe ich heute **die richtige Frage an der falschen Stelle gemessen** —
und zweimal davon erst, nachdem ich den Fehler live vor mir hatte:

| # | Gemessen wurde | Richtig war | Folge des Fehlers |
|---|---|---|---|
| 1 | Gesamtlauf (`workflow_runs[].conclusion`) | **Job** („backup") | Der grüne Leerlauf wäre genau am Tag seines Zutreffens verschwunden |
| 2 | `queue["offen"]` (Arbeitsvorrat mit Fristen) | **Ledger** (`fachbefunde`) | Fehlalarm, der **jeden Pull-Request blockierte** – plus Schein-Sicherheit für echte Rückfälle |
| 3 | Jüngster Lauf (auch wenn er 0 Schritte hat) | jüngster Lauf **mit Schritten** | Der Scheinbeweis-Befund verschwand nach meinem eigenen Dispatch |

Das ist keine Sammlung von Pannen, das ist **ein** Muster. Es steht deshalb hier
oben und nicht in einer Fußnote: Ein System, das an der falschen Höhe misst, ist
nicht halb richtig — es ist in beide Richtungen falsch. Es meldet Fehler, die
keine sind, und es verschweigt Fehler, die welche sind.

Die Gegenmaßnahme ist überall dieselbe und steht jetzt im Code: **Miss die Höhe,
auf der die Aussage steht** — und mach die Messhöhe selbst zum Vertrag.

---

## 1. Live-Befund (07.11.2026, echte GitHub-API)

| Prüfung | Ergebnis |
|---|---|
| Offsite-Lauf `42359904795` | Job `KV-/D1-Backup` **failure** (gewollt, Einrichtung fehlt) · Job `backup` **success** |
| Annotationen des **grünen** Jobs | „Kein dauerhaftes Offsite-Ziel gesetzt" + „Kein BACKUP_PASSPHRASE" — **beide** aus der Lauf-API gelesen |
| Einrichtungsprüfung (live) | E1, E2, E3, E4, E5, E6 offen · E7 optional · E8 offen (`protection_rules: []`) |
| 24 Läufe 15.10.–07.11. | **alle** `failure`; Start 07:37–10:28 UTC statt 03:00 → Lauf fehlt, Datei ist in Ordnung |
| Frischwache, 6 Läufe in Folge | Rückweg-Nachweis jeweils **`skipped`** – zuletzt `42282938395` |
| Schreib-Endpunkte (Variable/Secret/Environment) | `403 Resource not accessible by integration` – nichts erfunden, nichts gesetzt |
| Ziel-Repository `frank-hartung/franksfinanzcheck-backup` | **404** – existiert nicht |

**Die Inhaber-Einrichtung (E1–E8) bleibt der einzige funktionale Blocker.**

---

## 2. Fundsache außerhalb des Vorgangs: der blockierte Pull-Request

Beim Absichern des PR fiel auf: Der CI-Job **„Code-Regression – Suite und
Selbsttests"** war rot — und zwar **auch auf `main`**. Kein PR konnte grün
werden. Lokal war die Suite grün; die Ursache lag also nicht im Code, sondern
in **Daten**, die ein Test als Wahrheit nahm.

**Reproduktion** (eigener Worktree auf `origin/main`, volle Suite):

```
FAIL: test_faktenfrische_queue_haelt_befunde_geschlossen (#763)
FAIL: test_faktenfrische_queue_haelt_befunde_geschlossen (#823)
Ran 5512 tests — FAILED (failures=2, skipped=22)
```

**Die Ursache, belegt:** Die drei Rückfall-Tests (#763, #823, #911) lasen
`queue["offen"]` und nannten das „offene Befunde". Dieses Feld ist aber der
**Arbeitsvorrat**: Seiten, die noch nicht dran waren, mit ihrer Frist.

```json
{"slug": "2026-10-14-heizperiode-vorbereiten-im-spaetsommer",
 "grund": "frisch geprüft vor 23 Tagen (Intervall 30 Tage)",
 "faellig": false, "frist": "2026-11-14", "geo": 100}
```

Kein `id`, kein `typ`, kein `text`, kein `fassung_sha256`. Das ist **kein
Befund** — es ist ein Termin. Am 07.11. rutschte die Heizperiode turnusgemäß
wieder in den Vorrat, und drei Tests wurden rot, ohne dass ein Artikel einen
Sachfehler hatte.

**Die zweite, gefährlichere Richtung** (nachgewiesen, nicht behauptet): Ein
echter zurückgekehrter Befund steht in `fachbefunde`. Über `offen` gemessen
wäre er **unsichtbar** geblieben. Der Fehlalarm war die harmlose Hälfte.

### Die Heilung an der Wurzel

* **`queue_daten_bauen()`** — reine Funktion: ein Datensatz, zwei Feldnamen.
  Neu **`arbeitsvorrat`** (sagt, was drin ist); `offen` bleibt als
  **gleichlautender Alias** stehen, damit kein Altleser bricht. Beide stammen
  aus derselben Liste — sie können nicht auseinanderlaufen.
* Die drei Tests messen jetzt im **Ledger** (`ledger.offene_befunde`).
* **Selbsttest ST9a–f** hält die Messhöhe fest.

Ein Detail, das ich beinahe falsch gemacht hätte: Meine erste Fassung von ST9
rief `main()` — der Selbsttest hing damit am **Recherche-Netz** (178 s, dann
OOM-Kill). Ein Selbsttest, der ins Netz greift, ist genau das, was die
KI-Probe (#138) zu Recht erschlägt. ST9 prüft jetzt die reine Funktion: **0,4 s.**

### Der Vertrag `scripts/tests/test_faktenfrische_messhoehe.py` (11 Tests)

Er prüft die Messhöhe selbst — Fehlalarm darf nicht zurückkehren **und**
Schein-Sicherheit nicht zurückkehren. Dabei ist er selbst einmal falsch
gewesen: Seine erste Fassung zählte `geo["offen"]` mit — die Liste offener
**GEO-Kriterien**, ein völlig anderes Feld mit gleichem Namen. Jetzt zählt nur,
was auf die Queue zeigt.

---

## 3. Die Heilungen am Vorgang

### H-01 · Selbstheilung als eigener Baustein — `scripts/backup_selbstheilung.py`

| Regel | Inhalt |
|---|---|
| **H1** Nur reparieren, was **beweisbar** kaputt ist | Befund ohne `beleg` ist nie heilbar |
| **H2** Nur reparieren, was **ohne Zugang** reparierbar ist | heilbare Klassen: **genau** `scheduler` |
| **H3** Heilung ist eine **Aktion mit Beweis** | Dispatch + neuer Lauf in der Läufe-Liste; „HTTP 204 angenommen" zählt nicht |

Klassen: `scheduler` (heilbar) · `leerlauf` · `scheinbeweis` · `einrichtung`.
Exit: 0 nichts zu tun · 1 Beweis ausgeblieben (rot) · 3 Inhaber-Schritt ·
4 Leerlauf bei vollständiger Einrichtung.

**Vorrang ist Absicht:** Ist die Einrichtung offen, hat **sie** Vorrang (Exit 3).
Der Leerlauf ist dann die Folge, nicht die Ursache — zwei Rot-Stellen für eine
Ursache wären Lärm.

### H-02 · Der übersprungene Nachweis

Der Schritt „Kurzpruefung Wiederherstellbarkeit" stand in sechs Läufen in Folge
als `skipped` (GitHubs Standardbedingung `success()`). Er läuft jetzt mit
`if: ${{ !cancelled() }}` und **sagt**, was ohne Einrichtung nicht prüfbar ist:

```
::warning title=Wiederherstellbarkeit nicht belegbar::Ohne Ziel, Zugang und
Passphrase existiert keine Sicherung, deren Rückweg prüfbar wäre. …
```

Kein `continue-on-error`, kein `|| true`.

### H-03 · Der grüne Leerlauf

Gemessen auf **Job-Ebene**, gemeldet als Exit 4 / Klasse `leerlauf`, im
Alerting eigene Runbook-Klasse **`backup-leerlauf`** — vor dem allgemeinen
Backup-Rat (sonst verschluckt er die einzige zutreffende Aussage), nach
`backup-einrichtung` (bei offener Einrichtung bleibt sie die erste Antwort).

---

## 4. Live-Nachweise (keine Zusagen)

**Der blockierende CI-Job ist grün — mit Beleg, Schritt für Schritt:**

```
Lauf 42383652276 · Job 128436351379 · conclusion: success
  success  Code-Regression – Suite und Selbsttests
  success  Uhr-Probe – die Suite muss an jedem Kalendertag grün sein
  success  KI-Probe – kein Selbsttest darf am Modell oder am Netz hängen (#138)
  success  Beweis-Ledger-Isolation (Selbsttests)
  success  Beweis-Ledger muss nach den Tests unberührt sein
```

**PR-Stand:** 14 Checks `pass`, 4 `skipping`, **0 fail**.

**Die Selbstheilung live gegen die echte API** (`--plan`):

```
🟢⚠️ [leerlauf/nicht heilbar]     Job „backup" grün ohne BACKUP_REPO/BACKUP_PASSPHRASE
🛑     [scheinbeweis/nicht heilbar] „Kurzpruefung Wiederherstellbarkeit" = skipped
🛑     [einrichtung/nicht heilbar]  E1, E2, E3, E4, E5, E6 offen
rc = 3  → Inhaber-Weg hat Vorrang
```

**Warum der Scheinbeweis-Befund hier noch steht, und warum das richtig ist:**
Ich habe den Frischwache-Workflow testweise gestartet — Ergebnis `42386235574`,
Job **`skipped`, 0 Schritte** (der Job-Guard `if: github.ref == main` greift auf
einem Branch). **Damit verschwand der Befund.** Genau das ist der Selbstfund aus
Abschnitt 0, Nummer 3: Ich hatte mit meinem eigenen Testwerkzeug die Messung
gelöscht, die ich beweisen wollte. `_zeugt_lauf()` behebt es; der Befund ist
seitdem wieder da — und er ist ehrlich, denn die Workflow-Heilung wirkt erst
auf `main`. Ein System, das hier „grün" gemeldet hätte, hätte gelogen.

**Wo die Selbstheilung live noch nicht laufen kann:** Der Heilschritt liegt im
Frischwache-Workflow, dessen Job auf `main` beschränkt ist (E8-Schutz). Auf
diesem Branch ist er nicht ausführbar — das ist der Zweck des Guards, keine
Lücke. Der Nachweis der Dispatch-Logik erfolgt deshalb über Selbsttest F13–F15
(mit UND ohne Beweis) und den Live-`--plan`; der Betriebsnachweis kommt mit dem
ersten `main`-Lauf nach dem Merge.

---

## 5. Regressionsschutz — beide Richtungen, mit Sabotageproben

| Sabotage | Ergebnis |
|---|---|
| Messhöhe zurück auf `queue['offen']` | ❌ 2 Fehlschläge |
| Feldname `arbeitsvorrat` entfernt | ❌ 2 Fehlschläge |
| `main()` im Selbsttest | ❌ 1 Fehlschlag |
| Echter Befund ins Ledger | ❌ #763, #823, #911 rot |
| Nur turnusgemäße Fälligkeit (kein Befund) | ✅ alle drei grün — **das war vorher rot** |
| `_zeugt_lauf()`-Filter entfernt | ❌ „der echte Lauf hätte Schritte liefern müssen" |
| `einrichtung` auf heilbar gesetzt | ❌ 2 Fehlschläge |
| `!cancelled()` vom Rückweg-Nachweis entfernt | ❌ 2 Fehlschläge |
| Heilungsaufrufe aus dem Workflow entfernt | ❌ 2 Fehlschläge |

**Eine Sabotage lief zuerst ins Leere** — ich hatte den neuen Test in der
falschen Klasse gesucht und bekam „OK" für einen Test, der gar nicht lief. Ein
grüner Sabotage-Lauf ist kein Beweis, sondern ein Verdacht. Nach der Korrektur
sprang er an. Das steht hier, weil es der Punkt ist.

---

## 6. Abnahme (alle Befehle in diesem Stand ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `unittest discover -s scripts/tests` | ✅ **5441 Tests**, 22 Skips |
| dieselbe Suite unter +97-Tage-Uhr (`selftest_clock`) | ✅ grün |
| `test_backup_einrichtung.py` | ✅ **75 Tests** |
| `backup_selbstheilung.py --selftest` / `--vertrag` | ✅ 21 Fallgruppen / ✅ |
| `faktenfrische.py --selftest` | ✅ **35/35** (vorher 29) |
| `test_faktenfrische_messhoehe.py` (neu) | ✅ 11 Tests |
| `selftest_runner.py` | ✅ **275 Wachen, 550 Uhr-Proben** |
| `governance_contract.py` (voll) | ✅ alle 46 Regeln |
| `trigger_wache.py --check` | ✅ 100 Workflows, 0 Befunde |
| `skript_syntax_wache.py --check` | ✅ 667 Dateien |
| `wachen_vertrag.py` | ✅ 386 Skripte, 0 Funde |
| CI-Job „Code-Regression" | ✅ **live grün** (Job 128436351379) |

---

## 7. Was der Inhaber tun muss (unverändert)

```bash
npm run backup:einrichten     # E8 zuerst, dann E1–E7; Geheimnisse verdeckt
npm run backup:status         # Stand prüfen, ohne etwas zu ändern
npm run backup:heilung        # was das System selbst reparieren darf
```

Danach Actions → „Offsite-Backup" → „Run workflow" (`main`), dann
`npm run backup:probe`.

**Abnahmekriterien für #923:** (1) grüner `KV-/D1-Backup`-Job auf `main`,
(2) privates Entwurfs-Release `kv-backup-*` mit Größen-/Draft-Nachweis,
(3) bestandener Restore-Drill, (4) grüne Frischwache (reflexiver Beweis, dass
beide Wachen dieselbe Wahrheit sehen), (5) **neu:** kein grüner `backup`-Job
mehr ohne dauerhaftes Ziel.

---

## 8. Bewusste Grenzen

- **Keine erfundenen Werte.** Kein Secret, kein Token, keine Variable, kein
  Environment-Recht gesetzt oder behauptet.
- **Kein Absenken einer Prüfung.** Kein `continue-on-error`, kein `|| true` in
  den Backup-Workflows. Die neue `!cancelled()`-Bedingung macht den
  Rückweg-Nachweis **häufiger** ausführbar, nicht schwächer.
- **Keine Heilung über die Grenze.** Automatisch reparierbar ist genau eine
  Klasse (`scheduler`), per Vertrag fixiert. „Einrichtung heilen" wäre
  Selbstbetrug mit gutem Namen.
- **Fremde Vorgänge unberührt** (#1030, #1098, #1096, #1107). Offene
  Alarm-Issues bleiben Sache ihres eigenen Schließpfads.
- **Keine Doku-Drift.** Der Live-Status der Anleitung trägt das Datum 07.11.2026
  mit den heute gelesenen Werten; Vorgängerstände sind als *Archiv* markiert.

---

## 9. Offen für den nächsten Lauf

1. Nach dem Merge den ersten `main`-Frischwache-Lauf beobachten: Der
   Rückweg-Nachweis muss **ausgeführt** werden (nicht `skipped`) und der
   Leerlauf-Befund muss als `::error title=Backup-Leerlauf::` erscheinen.
2. E4-Widerspruch auflösen: `--plan` meldet E4 offen, der Stand 03.11. nannte
   E4 vorhanden. Vermutlich ein Environment-/API-Unterschied — nicht geraten,
   sondern beim nächsten Lauf mit `backup_einrichtung.py --pruefen` zu klären.
3. `data/faktenfrische_queue.json` trägt den neuen Feldnamen erst nach dem
   nächsten echten Faktenfrische-Lauf (04:40 UTC). Bis dahin liest der Alias —
   und der Vertrag prüft den Erzeuger, nicht das Artefakt.
