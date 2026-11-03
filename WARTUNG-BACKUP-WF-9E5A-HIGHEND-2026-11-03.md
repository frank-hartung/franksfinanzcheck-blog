# Wartung · Sicherung · WF-9E5A #923 — Highend-Dauerheilung (03.11.2026)

**Auftrag:** `Wartung · Sicherung · Vorgang WF-9E5A #923 Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben.`
**Branch:** `arena/ad52d5e0-franksfinanzcheck-blog`
**Basis:** `b29c009cd677050580656a8b09fbb63bee0010e7` (`main`, 03.11.2026, 08:31 UTC)
**Bearbeiter:** Arena Agent · **Vorgänger:** `WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-02.md`

---

## 1. Warum dieser Bericht nicht die Fortschreibung des letzten ist

Der Stand vom 02.11. hat die Klasse „grün, ohne geprüft zu haben“ geschlossen –
die Wachen melden seither rot an der richtigen Stelle. Heute ging der Blick in
die **Gegenrichtung**, denn dieselbe Disziplin gilt für rote Signale: Ein Rot,
das nicht an der Sache hängt, ist derselbe Defekt wie ein Grün ohne Prüfung –
nur spiegelverkehrt. Beim Vergleich der beiden beteiligten Workflows sind zwei
echte, live belegte Defekte aufgefallen, die beide in eine Zukunft wiesen, in
der der Inhaber seine Einrichtung abschließt – **und die Wache trotzdem für
immer rot bliebe**. Dazu kam ein zweites, leiseres Problem: Die Selbsttests
der Backup-Kette schrieben simulierte Ausfälle als **echte** Fehler-
Annotationen in Produktionsläufe. Beides ist heute dauerhaft geheilt und
vertraglich verriegelt.

## 2. Live-Befund (03.11.2026, gegen die echte GitHub-API)

| Prüfung | Ergebnis |
|---|---|
| Offsite-Lauf `41428440948` (02.11., 10:23 UTC) | `backup` (Bundle+Release) **success**, `KV-/D1-Backup` **failure** in „Voraussetzungen prüfen (fail-closed – kein Schein-Grün)“ — gewollt, Einrichtung fehlt |
| Zwölf Läufe 22.10.–02.11. | **alle** `failure`, derselbe Schritt, dieselbe Ursache |
| Erwarteter Lauf 03.11., 03:00 UTC | **noch nicht eingetroffen** (Stand 09:51 UTC) — dasselbe belegte Scheduler-Bild wie seit dem 22.10. (Verspätungen 07:47–10:23 UTC beobachtet), RPO-Toleranz 52 h deckt es |
| Frischwache `41533983322` (02.11., 22:04 UTC) | **failure** in „Voraussetzungen prüfen (fail-closed – kein Schein-Grün)“ — die Heilung vom 02.11. greift im Live-Betrieb |
| Alarmführung | `#923` (Offsite, Klasse `backup-einrichtung`) und `#1030` (Frischwache, diesellebe Klasse) offen, **jüngster Lauf jeweils nachgeführt**, Rat korrekt — kein Handeingriff nötig, wie vorgesehen |
| Environment `backup` | `protection_rules: []`, `deployment_branch_policy: null` (E8 offen) |
| Repository `frank-hartung/franksfinanzcheck-backup` | **404** — existiert nicht |
| Variablen/Secrets (Agenten-Token) | weiterhin `403 Resource not accessible by integration` — nichts erfunden, nichts gesetzt |

Die Inhaber-Einrichtung (E1–E8) bleibt der einzige funktionale Blocker. Was
heute heilbar **war**, ist das Signal darum herum.

## 3. Die zwei Defekte — reproduziert, nicht behauptet

### N-01 · Die Frischwache prüfte Namen, die sie nie erhielt — „rot über Werten, die nicht da sein konnten“

**Reproduktion (Lauf `41533983322`, Job-Annotationen live gelesen):** Der
Schritt „Voraussetzungen prüfen“ der Frischwache meldete sechs Punkte offen –
darunter **E4 `CLOUDFLARE_ACCOUNT_ID`: „fehlt“**. Im selben Zeitraum zeigte
der KV-Job des Offsite-Workflows (gleiche Prüfung, vollständige
Umgebungs-Verdrahtung) E4 **nicht** als offen (Annotation-Liste des Laufs
`41428440948` sowie Live-Status 01.11./02.11.: „E4 ist vorhanden“).

E4 ist also eingerichtet – die Frischwache meldete es trotzdem als fehlend.
Ursache: `backup_einrichtung.py --pruefen` liest seine sieben Eingaben aus
festen Umgebungsnamen (`ZIEL_REPO`, `ZIEL_TOKEN`, `PASSWORT`, `CF_ACCOUNT_ID`,
`CF_API_TOKEN`, `KV_NAMESPACE_ID`, `D1_DATABASE_ID`). Der KV-Job bildet sie
ab; **die Frischwache tat es nie** – ihr Job setzte nur `BACKUP_REPO` und
`GH_TOKEN`. Der Prüfer fragte konsequenterweise: *leer → „fehlt“*.

Die Konsequenz wäre erst **nach** der Einrichtung sichtbar geworden, und dann
mit voller Härte: Der Inhaber erledigt E1–E8, der Offsite-Lauf wird grün,
Issue #923 schließt sich – aber die Frischwache bliebe bei jedem Push und
jeden Tag **rot**, meldete „Einrichtung unvollständig“ über eine abgeschlossene
Einrichtung und schriebe #1030 immer weiter fort. Ein Dauer-Fehlalarm ist
schlimmer als ein Ausfall, den man sieht: Er lehrt den Betreiber, rote
Wachen zu ignorieren – und zwar genau die Wache, die einen echten
Sicherungsausfall ab 52 h melden soll.

Zweiter Teil desselben Defekts, eine Schicht tiefer: Selbst mit gespiegelten
Eingaben hätte **E8** in der Frischwache nicht geprüft werden können. Der
Schritt erbte `GH_TOKEN = secrets.BACKUP_REPO_TOKEN`; der fine-grained Token
ist bewusst auf das Ziel-Repo begrenzt und **darf** die Environment-Regeln
des Quell-Repos gar nicht lesen – E8 wäre nach der Einrichtung dauerhaft auf
„nicht prüfbar“ gestanden.

**Heilung (`.github/workflows/backup-frischwache.yml`):**

- Der Job `frischwache` erhält denselben Umgebungs-Spiegel wie der KV-Job:
  `ZIEL_REPO`, `ZIEL_TOKEN`, `PASSWORT`, `CF_ACCOUNT_ID`, `CF_API_TOKEN`,
  `KV_NAMESPACE_ID`, `D1_DATABASE_ID` – aus denselben Quellen
  (`vars.BACKUP_REPO`, `secrets.*`, …), Vertraglich gegen den KV-Job
  verriegelt, damit nie wieder zwei Wahrheiten entstehen.
- Der Einrichtungs-Schritt läuft mit dem **Lauf-Token**
  (`env: GH_TOKEN: ${{ github.token }}`) und der Job erhält `actions: read` –
  exakt die Konstellation, mit der der KV-Job E8 heute prüft. Die
  Frische-Messung danach bleibt beim fein eingeschränkten Ziel-Token
  (Minimalrechte pro Schritt, Gegenprobe im Vertrag).
- Schrittname, Alarm-Klasse (`backup-einrichtung`), fail-closed-Verhalten:
  unverändert.

### N-02 · Selbsttests erzeugten echte Fehler-Annotationen in Produktionsläufen

**Reproduktion (derselbe Lauf `41533983322`):** Neben den echten Befunden
standen in den Run-Annotationen:

```text
failure | Probe: Anzahl 5 != 1 Werte (unvollständig gelesen)
failure | KV-Export abgebrochen: <urlopen error TLS/SSL connection has been closed>
warning | KV-Namespace „ABO“ wurde live gelesen und enthält 0 Schlüssel …
```

Keiner dieser drei Einträge ist ein echter Vorfall: Es sind die
Simulationspfade F-E4, F-E6 und F-E7 aus `kv_backup.py --selftest`, der im
Selbsttest-Schritt **jedes** Frischwache- und KV-Backup-Laufs läuft. Die
Simulation rief die echten Melde-Kanäle ohne Einfangen auf; GitHub macht aus
jeder Zeile, die mit `::error::`/`::warning::` beginnt, eine Annotation –
auch in einem **grünen** Schritt. Gemessen am Stand vor der Heilung gab der
Selbsttest exakt **3** solcher Zeilen aus; die Reihenfolge deckt sich 1:1 mit
den Live-Annotationen.

> Derselbe Defekt wurde gestern (Bericht 02.11., §5a) in der CI-Suite
> geheilt — dort `::error::` über stderr in Sabotage-Tests. Der Blick blieb
> damals bei der Unittest-Suite stehen; die Skript-Selbsttests, die direkt in
> den Workflows laufen, waren dieselbe Lücke in der zweiten Schicht.

**Heilung (`scripts/kv_backup.py`, nur Selbsttest):** Die drei Simulationen
laufen jetzt unter `contextlib.redirect_stdout/-stderr`. Das Einfangen ist
ausdrücklich **mit Gegenprobe** gebaut: Der Puffer wird auf die erwartete
`::error::`-/`::warning::`-Meldung geprüft – die Meldung muss im echten Lauf
weiterhin ankommen, nur eben nicht in der Simulation. Wer das Einfangen je
ausbaut und die Meldung mitlöscht, macht den Selbsttest rot.

## 4. Regressionsschutz (dauerhaft, nicht punktuell)

Alle neuen Verträge in `scripts/tests/test_backup_einrichtung.py`,
Klasse `FrischwacheEinrichtungVertrag`:

| Vertrag | Inhalt |
|---|---|
| `test_frischwache_gibt_dem_pruefer_seine_eingaben` | Job-`env` der Frischwache muss alle sieben Prüfer-Eingaben aus denselben Quellen wie der KV-Job abbilden (deckungsgleich geprüft, kein zweiter Wahrheitsort) |
| `test_e8_prueft_mit_lauf_token_und_lese_recht` | E8-Schritt nutzt `${{ github.token }}`, Job trägt `actions: read`; die Messung danach sieht ausschließlich das Ziel-Token |
| `test_selbsttests_lecken_keine_workflow_befehle` | Führt **alle drei** Backup-Selbsttests (`kv_backup`, `backup_einrichtung`, `backup_freshness_guard`) als Subprozess aus: grün **und** keine Zeile beginnt mit `::error::`/`::warning::` |

**Negativeproben ausgeführt (beide Richtungen, wie es die Hausdisziplin
verlangt):** Ohne die Workflow-Heilung schlagen genau die zwei neuen
Umgebungs-Verträge fehl (`FAILED (failures=2)` am gestashten Stand); ohne die
`kv_backup`-Heilung schlägt der Leck-Vertrag fehl (`FAILED (failures=1)`).
Mit den Heilungen sind alle sechs Klassentests grün.

Bewusste Gegenprobe zum Überziehen: Die drei Backup-Selbsttests von
`backup_einrichtung.py` und `backup_freshness_guard.py` gaben vorher und
nachher **null** Workflow-Befehle aus (gemessen) – geheilt wurde nur die
Stelle, die leckte.

## 5. Abnahme (alle Befehle in diesem Stand ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/kv_backup.py --selftest` | ✅ inkl. eingefangener und gegengeprüfter F-E4/F-E6/F-E7; **0** Workflow-Befehle im Log (vorher: 3) |
| `python3 scripts/backup_einrichtung.py --selftest` | ✅ 18 Fallgruppen |
| `python3 scripts/backup_freshness_guard.py --selftest` | ✅ 13 Fallgruppen |
| `python3 -m unittest scripts.tests.test_backup_einrichtung` (venv mit PyYAML 6.0.3, `--require-hashes`) | ✅ **63 Tests** (60 Bestand + 3 neu) |
| dieselbe Suite ohne PyYAML (Standard-Python) | ✅ 63 Tests, 15 YAML-Skips (Muster unverändert) |
| `python3 -m unittest scripts.tests.test_alert_scoping` (venv, node vorhanden) | ✅ 31 Tests inkl. Verhaltenssimulation (`test_kern_szenarien … ok`) |
| `python3 scripts/selftest_runner.py` (venv, voller `requirements-ci.txt`-Stack, `--require-hashes`) | ✅ **263 Wachen, 526 Uhr-Proben, alles grün** (inkl. +97/+1461-Tage-Uhr) |
| `python3 scripts/workflow_js_wache.py --check` | ✅ alle `github-script`-Blöcke kompilieren |
| `python3 scripts/trigger_wache.py --check` | ✅ 98 Workflows, 0 Befunde |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ 628 Dateien |
| `python3 scripts/wachen_vertrag.py` | ✅ 372 Skripte, 0 Funde |
| `python3 scripts/alert_issue_identity.py --selftest` | ✅ 65 Workflows, 65 eindeutige Codes |
| `python3 scripts/manifest_guard.py` · `abhaengigkeits_wache.py --check` | ✅ grün |
| `bash scripts/restore_drill.sh --repo probe/kein-zugriff --nur-git --nur-kv` | ✅ Exit 2, „Es wurde NICHTS geprüft“ (Schein-Grün-Riegel unverändert wirksam) |
| `bash -n` beider Bash-Skripte · YAML-Parse beider Backup-Workflows | ✅ |
| `python3 scripts/governance_contract.py --quick` (venv) | ✅ alle 43 Regeln |

### 5a. Umgebungskontext — gefunden, nicht verschwiegen, aber nicht dieser Vorgang

1. **Volle Unittest-Suite unter CI-Markierung** (`GITHUB_ACTIONS=true`,
   `unittest discover`, 245 Testmodule): 11 Failures + 4 Fehler, davon **null**
   in Backup-, Workflow- oder Einrichtungs-Dateien. Zur sauberen Abgrenzung
   wurde die identische Teil-Suite am **ungestauten Ursprungsstand** (alle
   drei Heilungen per `git stash` entfernt) erneut ausgeführt: **exakt
   dieselben 11 + 4**. Die Befunde (Integritäts-Siegel gegen den
   `main`-Baum, Fremdmessungs-Altlasten, Faktenfrische-996-Inhalte u. ä.) sind
   umgebungsgebunden und älter als diese Abgabe — verursacht von dieser
   Heilung ist nichts davon.
2. **Auf `main` rot, andere Vorgänge:** „Qualitäts-Gate“ (Governance C1–C18,
   Issue `#1031`) und „Deploy auf GitHub Pages“ (mehrfach, u. a. 06:52 UTC).
   Lokal prüft der Governance-Vertrag auf diesem Branch **grün** (43 Regeln,
   s. o.); beide Alarme haben eigene Vorgangs-Threads und gehören nicht zu
   `#923`. Kein Handeingriff durch diese Abgabe (Hausregel: offene
   Alarm-Issues nie von Hand umschreiben).
3. **Heutiger 03:00-UTC-Offsite-Lauf** zum Redaktionsschluss (09:51 UTC)
   noch nicht eingetroffen — belegtes Scheduler-Verspätungsbild seit dem
   22.10.; RPO-Fenster intakt, die Frischwache (13:00 UTC) würde einen echten
   Ausfall melden (aktuell ohnehin fail-closed rot wegen der Einrichtung).

## 6. Was der Inhaber weiterhin tun muss — und der neue, schärfere Abnahmepunkt

Unverändert (Einrichtung ist Inhaber-Sache; ein Agent kommt an Secrets, PAT
und Cloudflare-Konto nicht heran — die Schreib-Endpunkte antworten heute
erneut mit `403`):

```bash
npm run backup:einrichten     # E8 zuerst, dann E1–E7; Geheimnisse verdeckt
npm run backup:status         # Stand prüfen, ohne etwas zu ändern
```

Danach Actions → „Offsite-Backup“ → „Run workflow“ (`main`), anschließend
`npm run backup:probe`. **Abnahmekriterium für #923** — ergänzt um genau den
Punkt, den N-01 heute geschlossen hat:

1. grüner `KV-/D1-Backup`-Job auf `main`,
2. privates Entwurfs-Release `kv-backup-*` mit Größen-/Draft-Nachweis,
3. bestandener Restore-Drill,
4. **und die Frischwache wird danach grün** (Job „Backup-Frische pruefen“:
   „Voraussetzungen prüfen“ ok → „Frische messen“ ok → reflexiver Beweis, dass
   beide Wachen dieselbe Wahrheit sehen).

Bis dahin bleiben #923 und #1030 offen und rot — der korrekte, auditierbare
Zustand; das Alerting führt beide Meldungen bei jedem Lauf selbst nach.

## 7. Bewusste Grenzen

- Keine Secrets, Passphrasen oder Token im Code, in Issues, im Bericht oder in
  Logs; kein erfundener Wert, um „grün“ zu erzeugen. (Beleg: Der Prüfer-
  Selbsttest fährt weiterhin den vergifteten-Werte-Gegencheck; F12.)
- Kein `continue-on-error`, kein `|| true`, kein Absenken einer Prüfung; das
  fail-closed-Verhalten vom 02.11. ist unangetastet (Vertragstests dazu
  unverändert grün).
- Keine manuelle Umschrift offener Alarm-Issues; keine Schließung von Hand.
- Der Selbsttest-Eingriff berührt ausschließlich die Simulationsebene:
  Export, Probe, Bulk und Fehlerpfade des realen Codes sind bis auf das
  (geprüfte) Einfangen unverändert.
- `.claude/skills/**`, `CLAUDE.md` und fremde Vorgänge (`#1031`, Deploys)
  blieben bewusst unberührt — kein neuer Dauergrundsatz entstanden, kein
  fremder Alarm überschrieben.
