# Wartung · Sicherung · WF-3150 #1030 — Selbstheilung (07.11.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-3150 #1030 Bitte dauerhaft auf
Highend-Level einer Profi-Agentur beheben mit automatischer Selbstheilung.`
**Branch:** `arena/7d8af7bd-franksfinanzcheck-blog` · **Basis:** `4d60e22`
(`main`, 07.11.2026, 08:40 UTC) · **Bearbeiter:** Arena Agent
**Vorgänger:** `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-03.md`,
`WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-02.md`, `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-01.md`

---

## 1 · Das Ergebnis in vier Sätzen

Die Sicherung wird weiterhin **nicht** ausgeführt – das kann ohne die
Inhaber-Zugänge niemand ändern, und ein Grün an dieser Stelle wäre ein
Betrug am eigenen RPO. Geheilt ist die **zweite** Hälfte des Problems: Die
Frischwache hat den Ausfall bisher nur **gemeldet**; der eine wirksame
Schritt („Offsite-Backup“ starten) war ein Handbefehl, den niemand kannte.
Seit diesem Stand **stößt die Wache die Sicherung selbst an**, wartet
begrenzt, misst erneut – und wird nur grün, wenn danach wirklich ein frisches
Release mit Inhalt existiert. Dazu fallen zwei stille Schein-Grün-Pfade: ein
**Release ohne Datei** (Hülle) zählte als Sicherung, und ein **unlesbares
JSON** konnte die Auswertung grün verlassen.

| Kennzahl | vorher | jetzt | Beleg |
|---|---|---|---|
| Heilung des operativen Ausfalls | Handbefehl („Run workflow“) | **automatisch**, 1 Anstoß je Lauf, max. 3/24 h | `scripts/backup_selbstheilung.py`, `.github/workflows/backup-frischwache.yml` |
| Grün-Nachweis | erste Messung | **zweite Messung nach dem Anstoß** | `heile()` – Attrappen-Test „zwei Messungen“ |
| „Frisch“-Erkennung | Alter des Releases | Alter **und** Inhalt (Assets) | `backup_freshness_guard.py` F13/F14 |
| Unlesbares Messergebnis | stillschweigend grün möglich | **rot** (fail-closed) | Schritt „Urteil fällen“ |
| Rückweg-Nachweis bei rotem Backup | wurde übersprungen | läuft (Urteil fällt am Ende) | Schrittfolge im Job |
| Selbsttest-Fälle | 13 | **15** (Frische) + **18** (Heilung) | `--selftest` |
| Regressionstests der Kette | 64 | **98** (+34) | `test_backup_einrichtung`, `test_backup_selbstheilung` |
| Alarm-Simulation | – | **+2 Szenarien** (#1030 und Gegenprobe) | `alert_scoping_sim.mjs` |

---

## 2 · Live-Befund (07.11.2026, gegen die echte GitHub-API)

| Prüfung | Ergebnis |
|---|---|
| Offsite-Läufe | **24 geplante Läufe in Folge `failure`** (15.10.–07.11.; der 14.10. war grün); jüngster `42359904795`, 07.11. 09:31 UTC |
| Frischwache | 8 Läufe in Folge `failure` seit 02.11. (geplante und Push-Läufe); jüngster `42282938395`, 06.11. 20:48 UTC |
| Fehlgeschlagener Schritt | jedes Mal „Voraussetzungen prüfen (fail-closed – kein Schein-Grün)“ |
| Offene Pflichtpunkte (Lauf-Annotationen) | **E1** `BACKUP_REPO`, **E2** `BACKUP_REPO_TOKEN`, **E3** `BACKUP_PASSPHRASE`, **E5** `CF_KV_BACKUP_TOKEN`, **E6** `KV_NAMESPACE_ID_ABO` |
| E4 `CLOUDFLARE_ACCOUNT_ID` | vorhanden (kein Fehlalarm – die Heilung vom 03.11. greift) |
| E8 Environment `backup` | `protection_rules: []`, `deployment_branch_policy: null` → Hinweis „jeder Branch darf das Environment nutzen“ |
| Repository `frank-hartung/franksfinanzcheck-backup` | **HTTP 404** – existiert nicht |
| Variablen/Secrets (Agenten-Token) | `403 Resource not accessible by integration` – nichts erfunden, nichts gesetzt |
| Issue #1030 | offen, Rat korrekt, Lauf-Nachweis nachgeführt (06.11. 20:48) |

**Einordnung:** Das ist ein Einrichtungsbefund, kein Codefehler. Die Meldung
sagt seit dem 02.11. das Richtige. Was fehlte, war die **Ausführung**: Eine
Wache, die einen Ausfall täglich neu misst und deren Heilung niemand anstößt,
ist eine Warteschlange (dieselbe Klasse, die am 06.11.2026 die
GSC-Verlinkung geheilt hat – `GSC-VERLINKUNG-SELBSTHEILUNG-1097-HIGHEND-2026-11-06.md`, §2.1).

---

## 3 · Die vier Defekte — reproduziert, nicht behauptet

### N-01 · Die Heilung war vorhanden, aber nicht verdrahtet

**Beleg:** Der Job `frischwache` hatte genau zwei Ausgänge: grün oder rot.
Ein Rot erzeugte (korrekt) die Meldung – und sonst nichts. Der nächste
Versuch war der nächste Tag. Bei einem Scheduler-Aussetzer (belegt: Läufe
07:47–10:23 UTC statt 03:00, mehrfach ganztägig ausgefallen – 02.11.) lagen
zwischen Erkennung und Heilung bis zu **24 h**, im schlechtesten Fall mehr.

**Heilung:** `scripts/backup_selbstheilung.py` schließt den Kreis in fünf
Schritten: messen → entscheiden → genau einmal anstoßen → begrenzt warten →
**erneut messen**. Der Anstoß ist `workflow_dispatch` von
`backup-offsite.yml` auf `main` – der geprüfte Weg; es gibt **keine zweite
Sicherungslogik**.

Die Entscheidung ist eine reine Funktion mit fester Reihenfolge (und in
beiden Richtungen getestet):

| Lage | Aktion | Warum |
|---|---|---|
| jede Familie jünger als 26 h | `nichts` | kein Fehlalarm bei Scheduler-Verspätung (bis 7 h belegt) |
| Tagesfenster verpasst (> 26 h) | `anfordern` | Ausfall wird **am selben Tag** geheilt, 26 h vor der 52-h-Meldung |
| Sicherung `queued`/`in_progress` | `warten` | kein Doppellauf |
| letzter Lauf < 15 Min. her | `warten` | kein Doppellauf |
| ≥ 3 Anstöße in 24 h | `aufgeben` | kein Dauerfeuer; Rot **mit Grund** bleibt |
| Lauf-Historie nicht lesbar | `aufgeben` | ein blinder Anstoß könnte doppelt sichern (fail-closed) |

**Warum 26 h:** Sicherung 03:00 UTC, Messung 13:00 UTC. Ein gesunder Lauf
ergibt ≤ 17 h (10 h + belegte 7 h Verspätung), ein ausgefallener ≥ 34 h.
26 h liegt dazwischen – kein Fehlalarm, aber der Ausfall wird **vor** der
ersten Warnstufe (36 h) geheilt.

### N-02 · Eine Hülle galt als Sicherung

**Befund (Code, reproduzierbar):** `backup_freshness_guard.py` bewertete
ausschließlich `created_at` des neuesten Releases. `backup-offsite.yml` legt
den Entwurf **vor** dem Upload an und lädt danach hoch; scheitert der Upload,
wird der Teil-Release gelöscht – bleibt diese Löschung ebenfalls hängen (oder
legt jemand von Hand einen Release mit passendem Tag an), stand ein Release
**ohne eine einzige Datei** als „frisch“ da. Die Wache hätte den Ausfall
verdeckt, statt ihn zu melden.

**Heilung:** Ein Release ohne Assets ist rot; fehlt die Asset-Liste in der
Antwort ganz, ebenfalls („nicht belegt“ ist kein Grün). Selbsttest F13/F14
mit der echten API-Form (`assets: []`).

### N-03 · Unlesbares Messergebnis konnte grün verlassen

**Befund:** Der Messschritt schrieb `… --json > /tmp/frische.json 2>&1`.
Jede Zeile auf stderr – etwa eine Warnung – machte das JSON unlesbar. Die
alte Auswertung prüfte `RC`, und im RC-0-Zweig fragte sie per
`json.loads(...)` nach `warnung`; ein kaputtes JSON wurde dabei als
„nicht warnung“ gewertet und der Lauf endete **grün**. Der Fehlerkanal
gehört nicht in die Messdatei, und „nicht lesbar“ ist kein Erfolg.

**Heilung:** stderr separat (sichtbar im Log), JSON rein; das Urteil wird
explizit gelesen und bei Unlesbarkeit rot. Der Schluss-Schritt „Urteil
fällen“ prüft zusätzlich, dass `urteil` aus `{ok, warnung, fehler}` stammt.

### N-04 · Der Rückweg-Nachweis hing am Ausgang der Frische

**Befund:** Der Schritt „Kurzprüfung Wiederherstellbarkeit“ stand **hinter**
der Frische-Messung, und die Messung brach bei Rot ab. Solange kein frisches
Backup existierte, wurde der Rückweg also **nie** geprüft – der einzige
automatisierte Nachweis der Wiederherstellbarkeit fiel genau dann aus, wenn
man ihn am ehesten braucht.

**Heilung:** Die Messung fällt kein Urteil mehr; der Rückweg-Nachweis läuft
anschließend immer (solange die Einrichtung nicht schon rot ist), und das
Urteil fällt **danach** im letzten Schritt. Ein Rot bleibt ein Rot – aber
mit vollständiger Beweislage.

---

## 4 · Die Selbstheilungs-Kette im Workflow

```
Selbsttest (Wache prüft sich selbst – fail-closed)
Voraussetzungen prüfen (fail-closed – kein Schein-Grün)      ← Einrichtung: E1–E8
Frische messen …                                             ← misst, urteilt NICHT
Selbstheilung – fehlende Sicherung anstoßen (fail-closed)    ← nur bei urteil != ok
Kurzprüfung Wiederherstellbarkeit (strukturell, ohne Secrets) ← läuft jetzt auch bei Rot
Urteil fällen (fail-closed – ohne Nachweis kein Grün)        ← die EINE rote Stelle
```

**Eingegrenzt, nicht „irgendwie erlaubt“:**

- **Ein Schritt** hat das Dispatch-Recht (`actions: write`), **ein** Aufruf,
  **ein** Workflow. Die Messung darüber läuft weiter mit dem fein
  eingeschränkten Ziel-Token (`BACKUP_REPO_TOKEN`), E8 mit dem Lauf-Token.
  Die Endpunkt-Liste des Moduls ist als Konstante festgenagelt
  (`ENDPUNKTE`) und vertraglich geprüft: genau drei GitHub-Pfade, `POST` nur
  für `/dispatches`, kein `DELETE`/`PUT`/`PATCH`.
- **Kein Anstoß ohne Einrichtung:** Der Job prüft E1–E8 **vor** der Messung.
  Ist die Einrichtung offen, endet der Lauf im Einrichtungs-Rat (Klasse
  `backup-einrichtung`) – die Heilung kommt gar nicht zum Zug.
- **Kein Grün ohne zweite Messung:** Ein angestoßener Lauf ist eine Absicht,
  kein Nachweis. Der Schluss-Schritt liest das Ergebnis der zweiten Messung;
  scheitert der angestoßene Lauf, bleibt es rot – **mit Link auf ihn**.

**Alarm-Klassen bleiben stabil:** Der Einrichtungsfall heißt weiter
`backup-einrichtung` (Schritt „Voraussetzungen prüfen“), der Rückweg-Fall
`backup-restore` (Schritt „Wiederherstellbarkeit“), der Frische-Fall
`backup-frisch` (Workflow-Klasse). Zwei neue Simulationsszenarien halten das
fest – inklusive Gegenprobe, dass ein Werkzeugfehler **in** der
Selbstheilung nicht als Einrichtungs- oder Rückwegproblem gelesen wird.
Der Rat der Klasse `backup-frisch` sagt jetzt, dass die Wache bereits
gehandelt hat („sonst würde er zu genau dem Schritt raten, den der Lauf
schon getan hat“); die Einrichtungs-Meldung sagt, dass nach dem Abschluss
**kein Handbefehl** mehr nötig ist.

---

## 5 · Was diese Sitzung NICHT heilt (und nicht heilen darf)

Die fünf offenen Punkte sind Zugangsdaten und Ziel-Entscheidungen des
Inhabers. Der Agenten-Token erhält auf Variablen, Secrets, Repositories und
Environment-Regeln `403 Resource not accessible by integration`:

| Punkt | Was fehlt | Wo es erledigt wird |
|---|---|---|
| E8 | Environment `backup` ohne Branch-Regel | Settings → Environments → `backup` → „Selected branches“ = `main` |
| E1 | Variable `BACKUP_REPO` | Repository-Variable, privates Ziel-Repo |
| E3 | Secret `BACKUP_PASSPHRASE` | Environment `backup`, 32+ Zeichen, **vorher** in den Passwort-Manager |
| E2 | Secret `BACKUP_REPO_TOKEN` | fine-grained PAT, **nur** das Ziel-Repo, Contents: Read and write |
| E5 | Secret `CF_KV_BACKUP_TOKEN` | Cloudflare-Token, nur „Workers KV Storage: Read“ |
| E6 | Variable `KV_NAMESPACE_ID_ABO` | 32-Hex-ID des Namespace `ABO` |

Werkzeug: `npm run backup:einrichten` (interaktiv, verdeckte Eingabe) bzw.
`npm run backup:status` (nur prüfen). Anleitung mit vorbelegten Links:
`docs/ANLEITUNG-OFFSITE-BACKUP.md`, Abschnitt „Kurz: Was ist zu tun?“.

**Warum #1030 offen bleibt:** Es ist die Wahrheit über den Betrieb. Ein
Issue, das geschlossen wird, weil der Code hübscher geworden ist, wäre
derselbe Schein wie ein grüner Lauf ohne Sicherung. Der Vorgang schließt
sich von selbst, sobald die Kette grün ist – durch den **Resolve-Gate**-Pfad
des Alertings (Job-Beweis), nicht durch einen Handgriff.

---

## 6 · Ab wann es automatisch geht

1. Inhaber erledigt E1–E8 (10 Minuten, Links vorbelegt).
2. Nächster Frischwache-Lauf (täglich **13:00 UTC**, manuell erzwingbar):
   - „Voraussetzungen prüfen“ wird grün,
   - „Frische messen“ findet **keine** Releases → `fehler`,
   - „Selbstheilung“ stößt `backup-offsite.yml` an, wartet (max. 15 Min.),
   - zweite Messung sieht `backup-*` **und** `kv-backup-*` mit Assets → grün.
3. Der grüne Lauf schließt #1030 (und, über den Offsite-Lauf, #923)
   automatisch – der Job ist im auflösenden Lauf vorhanden und `success`.

Ab dann gilt: Fällt der nächtliche Lauf aus, heilt die Wache um 13:00 UTC
selbst (bis 3 Versuche/Tag). Bleibt es rot, ist es ein echter Fehler mit
Grund – nicht ein vergessener Knopf.

---

## 7 · Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/backup_selbstheilung.py` | **neu** – Messen → Entscheiden → Anstoßen → Warten → erneut Messen; 18 Selbsttest-Fallgruppen; festgenagelte Endpunkt-Liste |
| `scripts/backup_freshness_guard.py` | Hülle ohne Assets ist rot (F13/F14); Fallzahl 15 |
| `.github/workflows/backup-frischwache.yml` | Messung urteilt nicht mehr; Schritt „Selbstheilung“; Schluss-Schritt „Urteil fällen“; `actions: write` (begründet); Trigger-Pfade für die neuen Dateien |
| `.github/workflows/alert-on-failure.yml` | Rat `backup-frisch` nennt die Selbstheilung; Einrichtungs-Rat: kein Handbefehl mehr nötig |
| `scripts/tests/test_backup_selbstheilung.py` | **neu** – 34 Tests (Entscheidungstabelle, Kreis, Rechte-Trennung, Endpunkte, Workflow-Vertrag, Hüllen-Regel) |
| `scripts/tests/test_backup_einrichtung.py` | Rechte-Vertrag auf `actions: write` nachgezogen (mit Begründung); neuer Selbsttest in der Annotations-Probe |
| `scripts/tests/sim/alert_scoping_sim.mjs` | 2 Szenarien (#1030 + Gegenprobe) |
| `docs/ANLEITUNG-OFFSITE-BACKUP.md` | Abschnitt „Selbstheilung“; Live-Status 07.11.2026; Betriebszusagen aktualisiert |
| `package.json` | `backup:selbstheilung`, `backup:heilen`; `test:backup` umfasst die neue Suite |

## 8 · Nachweise (lokal gefahren)

```text
python3 scripts/backup_selbstheilung.py --selftest     → ✅ 18 Fallgruppen
python3 scripts/backup_freshness_guard.py --selftest   → ✅ 15 Fallgruppen
python3 -m unittest scripts.tests.test_backup_einrichtung \
                     scripts.tests.test_backup_selbstheilung
                                                       → Ran 98 tests … OK
python3 -m unittest scripts.tests.test_alert_scoping    → Ran 32 tests … OK (inkl. node-Simulation)
                                                       → zusammen 130 Tests, alle grün
python3 scripts/skript_syntax_wache.py --check          → ✅ 667 Dateien (inkl. Trigger-Wache W1–W3)
python3 scripts/workflow_js_wache.py --check            → ✅ alle github-script-Blöcke kompilieren
python3 scripts/workflow_vertrag_wache.py --gate        → ✅ 100 Workflows vertragsgemäß
```

Der Messschritt des Workflows wurde zusätzlich **aus dem YAML extrahiert und
mit Bash ausgeführt** (fehlende Eingaben → rot; Attrappen-Token → `urteil=fehler`,
`GITHUB_OUTPUT` geschrieben, Summary geschrieben), ebenso der Schluss-Schritt
(`::error::` + Exit 1). Ein Test, der nur den Text prüft, hätte den
Heredoc-/Bash-Fehler nicht gefunden.

**Probe gegen die echte GitHub-API (ohne Anstoß, `--probe`):**

```text
Backup-Selbstheilung · frank-hartung/franksfinanzcheck-blog
🛑 Backup überfällig oder unprüfbar – Details je Familie unten.
  ❌ backup- backup-20260920-0809 (Entwurf) ist 1154 h alt – älter als 52 h
  ❌ kv-backup- Kein kv-backup-*-Release in … – lief das Backup schon einmal grün?
  → Selbstheilung: anfordern – kein laufender Sicherungslauf (Probe: nicht angestoßen.)
Exit 1
```

**Uhrfest (Lehre vom 18.09.2026):** Der erste CI-Lauf des PR hat die neue
Selbstheilung rot gemacht – zu Recht: `heile()` las den Zeitpunkt der
**zweiten** Messung aus der echten Uhr. Unter der um 97 bzw. 1461 Tage
vorgestellten Uhr des Qualitäts-Gates (`scripts/selftest_clock.py`) galten
die Test-Fixtures dann als Jahre alt, und S11 meldete „nicht grün“. Genau
so entstehen Zeitbomben – grün am Tag des Schreibens, rot an einem Feiertag
drei Monate später. Geheilt: `heile()` hat jetzt einen eigenen Parameter
`jetzt_neu`; Selbsttest und Unit-Tests stempeln beide Messungen auf
denselben Testzeitpunkt. Nachweis:

```text
python3 scripts/selftest_clock.py --trap scripts/backup_selbstheilung.py --offset 97    → ✅
python3 scripts/selftest_clock.py --trap scripts/backup_selbstheilung.py --offset 1461  → ✅
python3 scripts/selftest_clock.py --trap-modul scripts.tests.test_backup_selbstheilung --offset 97 → ✅
```

Damit ist live belegt: (a) der Release-Leser versteht die echte API-Form, (b)
die Lauf-Historie ist mit `actions: read` lesbar (die Entscheidung stützt sich
nicht auf eine Attrappe), (c) ein echter Backup-Release **trägt Assets** – die
Hülle-Regel erzeugt an echten Daten keinen Fehlalarm, und (d) `--probe` stößt
nichts an. Nicht live belegt ist der Dispatch selbst: Er ist mit Attrappen
getestet, und einen echten Anstoß löst bewusst erst der erste Lauf nach der
Inhaber-Einrichtung aus.

---

## 9 · Restrisiken, bewusst benannt

| Risiko | Wirkung | Gegenmaßnahme |
|---|---|---|
| Lauf-Token ohne `actions: write` (Org-Policy) | Anstoß wird mit 403 abgelehnt | Ausgabe nennt genau das; Lauf bleibt rot statt still grün |
| Owner startet 3× manuell am Tag | Budget erschöpft, keine Selbstheilung mehr | gewollt: nach drei Läufen ist es kein Scheduler-Problem mehr |
| KV-Job dauerhaft rot bei grüner Einrichtung | bis zu 3 Anstöße/Tag, jeder endet rot | Budget begrenzt; die Ursache steht in der Meldung zu „Offsite-Backup“ |
| GitHub-API-Störung bei der Historie | kein Anstoß | fail-closed (kein blinder Anstoß), Lauf rot mit Grund |
| Selbstheilung als „Reparatur“ missverstanden | sie kann keine Secrets erzeugen | Grenze im Code, im Bericht und in der Anleitung ausdrücklich benannt |

---

## 10 · Fremdbefund: `regression` ist auf `main` rot — nicht die Wache

Der PR #1115 war am 07.11. ab 13:05 UTC **nicht** vollständig grün. Rot waren
genau zwei Schritte des `regression`-Jobs (Run
[42374748169](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/42374748169),
Job 128409942661): „Code-Regression – Suite und Selbsttests“ und „Uhr-Probe“.
Alles, was diese Änderung anfasst (`gate`, CodeQL, Playwright, Workflow-Gate),
war grün.

**Nachweis, dass es nicht an dieser Änderung liegt:**

| Probe | Ergebnis |
|---|---|
| Volle Suite auf dem Zweigstand `eb1427c` (Basis `4d60e22`) | `Ran 5453 tests … OK (skipped=22)` |
| Volle Suite auf `main` `688812d` (eigener Worktree, `/tmp/mainwt`) | 2 × `FAIL` |
| Die beiden Module isoliert auf `main` `e103bc3` — dem Stand, gegen den CI gemerged hat | `FAILED (failures=2)` |
| Dieselben zwei Module auf `eb1427c` | `OK` |

Die beiden roten Tests:

- `test_faktenfrische_763.Faktenfrische763MetaTests.test_faktenfrische_queue_haelt_befunde_geschlossen`
- `test_faktenfrische_823.Faktenfrische823MetaTests.test_faktenfrische_queue_haelt_befunde_geschlossen`

Beide lesen `data/faktenfrische_queue.json` und verbieten, dass die dort
`offen` geführten Einträge die bereits geschlossenen Slugs
`2026-10-14-heizperiode-…` und `2026-10-15-saison-update-…` enthalten.

**Ursache:** Die Datei hat sich auf `main` zwischen `4d60e22` und `e103bc3` um
748 Zeilen verändert (Writer-Commit `eb1c25c`, „chore(scorecard): …
Live-Bestand versiegelt“). `offen` führt seither **24** Einträge, darunter die
beiden Artikel mit `faellig: false` und dem Grund „frisch geprüft vor 23 Tagen
(Intervall 30 Tage)“ — also Artikel, die die Queue selbst als *nicht fällig*
führt. Ein Eintrag, der „offen“ heißt und gleichzeitig „frisch geprüft,
Frist 2026-11-14“ sagt, ist ein Widerspruch in derselben Zeile.

Damit stehen zwei Lesarten offen, und **beide gehören der Sitzung, die die
Queue schreibt** — nicht dieser hier:

1. **Writer zu weit:** `offen` sollte nur fällige/befundbehaftete Artikel
   führen; dann muss die Erzeugung filtern.
2. **Wächter zu streng:** `offen` meint inzwischen „alle Artikel mit Vorlauf“;
   dann muss der Test auf `faellig` oder auf vorhandene Befunde einschränken.

Diese Sitzung hat die Queue **nicht** angefasst. Ein Eintrag aus `offen` zu
löschen, nur damit `regression` grün wird, wäre genau das Schein-Grün, das
diese Akte an anderer Stelle ausschließt — und `data/` ist versionierter
Beweisbestand (history_guard H6), kein Kosmetikfeld.

**Gegenprobe gegen „nur mein Zweig“:** Der zeitgleiche Lauf der fremden
Sitzung `arena/923586ec-…` (Run 42374807863) ist mit demselben Job rot — die
Wache ist nicht zweigspezifisch. Und der `regression`-Job dieses Zweigs war um
10:06 UTC (Run 42362500106, `7d0a712`) noch grün: rot wurde er, als `main`
weiterlief, nicht als dieser Zweig sich änderte.

Der Befund ist als eigenes Issue festgehalten:
[#1126](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/1126), damit
er nicht in einem PR-Kommentar verschwindet; reproduziert sowohl auf `e103bc3`
(Stand des roten Laufs) als auch auf `f0bff16` (Stand beim Schreiben).

**Folge für #1030:** Keine. Die Frischwache, ihre Selbstheilung, die
Vertragstests und das Workflow-Gate sind unabhängig von diesem Befund grün;
die Backend-Lücke E1–E8 bleibt der einzige offene Punkt. PR #1115 kann erst
grün werden, wenn `main` Queue und Wächter wieder in Übereinstimmung bringt.

— *Ende der Akte. Nichts an dieser Änderung schaltet einen Schutz ab; nichts
davon behauptet eine Sicherung, die nicht existiert.*
