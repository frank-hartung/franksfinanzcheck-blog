# Commit-/Push-Fehlschläge: Ursache belegen statt neu starten

**Stand:** 21.11.2026 · **Vorgänge:** #1254 · #1246 · #1245 · #1244 · #1252 · #1251 · #1229
**Bereich:** Technik / Automatisierung (WF-3CAD, WF-AD21, WF-66EE, WF-B16A)

Dieses Dokument beantwortet ausschließlich die eine Frage aus dem Auftrag:
**Berechtigung, Branch-Schutz, Konflikt – oder ein anderer Fehler?**
Es belegt die Antwort mit den Logs der betroffenen Läufe und nennt je Klasse
den nächsten wirksamen Schritt.

---

## 1. Beweislage (aus den Läufen selbst)

Die Run-Logs der Läufe vom 16./17.11.2026 sind abgelaufen („results-receiver
… EOF"). Die Schritt-Annotationen der Check-Runs sind es **nicht** – sie
enthalten den vollständigen `::error::`-Text von `git_sync.sh`:

```bash
gh api repos/<repo>/check-runs/<JOB-ID>/annotations
```

| Vorgang | Workflow | Roter Schritt | Annotation (Auszug) | Klasse |
|---|---|---|---|---|
| #1254 | Blog-Gesundheits-Check | `Run git config user.name …` | „Rebase-Konflikt gegen origin/main … Betroffen: `content/posts/2026-11-13-tagesgeld-und-zinsen…/index.md`" | **konflikt** |
| #1246 | FrankAutoOps-Report | `Audit-Log-Stand committen` | „Synchronisation nach 3 Runden fehlgeschlagen (zuletzt: **netzwerk**)" | **netzwerk** (Restmenge) |
| #1245 | Hemingway-Lesbarkeitscheck | `Änderungen committen & pushen` | dito | **netzwerk** (Restmenge) |
| #1244 | ZEIT-Niveau Rechtschreib-Wache | `Änderungen committen & pushen` | dito | **netzwerk** (Restmenge) |

### Was das ausschließt

* **Kein API-Schlüssel.** Alle vier Schritte sind reines `git`
  (`git config`, `git add`, `git commit`, `git push`). Kein GROQ, kein
  GEMINI, kein Netzdienst. Der Rat „API-Key abgelaufen" konnte in keinem
  dieser Läufe zutreffen.
* **Kein Branch-Schutz.** `git_sync.sh` klassifiziert GH001/GH006/GH013/GH014,
  „required status check", „protected branch" als `schutz` und bricht dann
  **sofort ohne Retry** ab („kein Retry sinnvoll, dieselbe Regel lehnt wieder
  ab"). In keinem der vier Läufe steht diese Meldung.
  Die drei Regelsets auf `main` („main – Unveränderlichkeit",
  „Integritäts-Lock (PR-Gate)", „Premium-Schutz für main") verlangen nur
  `deletion`, `non_fast_forward` und `required_linear_history` – **keine
  Pflicht-Checks, keine Reviews**. Sie blockieren keinen Bot-Push.
* **Keine Berechtigungslücke.** `contents: write` ist in allen vier
  Workflows gesetzt; ein 403 sähe anders aus (`ist_auth_fehler`).

### Was es belegt

**#1254 ist ein echter Inhalts-Konflikt.** Zwei Läufe heilten dieselbe
`index.md` (Tagesgeld/Zinsen). Der Bestand ist unantastbar – hier ist ein
harter Stopp die *richtige* Antwort, nicht ein Fehler.

**#1244–#1246 sind Push-Rennen, keine Netzwerkfehler.** Die Klasse
`netzwerk` in `git_sync.sh` ist die **Restmenge** („nicht als Konflikt, Auth
oder Schutz erkannt") – ein Non-Fast-Forward wird darunter einsortiert. Der
Zeitverlauf auf `main` belegt die Gleichzeitigkeit:

| Zeit (UTC) | Commit | Workflow |
|---|---|---|
| 14:02:25 | `ab677efe` | Endredaktion |
| 14:05:30 | `32976dca` | Blog-Gesundheit |
| 14:12:51 | `551f12a9` | Suchradar |

Dazu: `hemingway-check.yml` und `zeit-rechtschreibung.yml` checken mit
`fetch-depth: 0` aus, gleichen aber vor dem Commit **nicht** erneut an. Beide
starteten auf demselben Stand `88c3e658`; wer zuerst pusht, gewinnt, der
zweite scheitert. Genau das ist eingetreten.

---

## 2. Was dauerhaft geändert wurde

### 2.1 Diagnose statt Rateschluss — `scripts/push_diagnose.py`

```bash
python3 scripts/push_diagnose.py --tage 7          # Bericht
python3 scripts/push_diagnose.py --json            # maschinenlesbar
python3 scripts/push_diagnose.py --selftest        # Klassifikation beweisen
```

Das Werkzeug liest die roten Läufe, **nur** die Commit-/Push-Schritte,
holt die Annotationen und ordnet jede Meldung genau einer Klasse zu:

| Klasse | Bedeutung | Nächster wirksamer Schritt |
|---|---|---|
| `schutz` | Ruleset/Branch-Schutz hat abgelehnt | **Nicht lockern.** Bypass-Akteur im Ruleset oder PR-Pfad (`docs/PFLICHT-CHECK-RUNBOOK.md`, „Direkte Pushes") |
| `auth` | Token/Permission | `permissions: contents: write`, Token prüfen. Retry ist sinnlos |
| `konflikt` | echter Inhalts-Konflikt | heilende Läufe serialisieren; ggf. `GIT_SYNC_BESTAND_POLICY=bestand-gewinnt` (WF-A535/#590) |
| `push_rennen` | paralleler Bot-Commit | gemeinsame `concurrency`-Gruppe, mehr `GIT_SYNC_TRIES` |
| `netzwerk` | **Restmenge** | erst *nach* Ausschluss der Klassen oben ist „erneut versuchen" die Antwort |
| `unbekannt` | keine Git-Meldung | der Schritt selbst ist kaputt, nicht der Push |

Zwei Quellen, eine Regel: die Rohmeldung (Git/curl) gewinnt, wenn sie eine
Ursache **nennt**; sonst gilt die Selbsteinordnung des Laufs
(„zuletzt: …"). Bei `netzwerk` (Restmenge) schlägt eine konkretere
Rohmeldung die Restmenge. Rote Tests und Builds zählen **nicht** – sonst
wiederholte das Werkzeug den Fehler, den es behebt.

Der Selbsttest läuft in `scripts/tests/test_push_diagnose.py` gegen die
**unveränderten Annotationstexte** der vier Vorgänge.

### 2.2 Die Befund-Akte folgt ihrer Quelle — im selben Commit

**Befund (aus #1229/#1251/#1252/#1266/#1267/#1271):** `BEFUND-AKTE.md` und
`data/faktenfrische_befunde_state.json` sind eine Ableitung aus
`data/faktenfrische_queue.json` + `data/faktenfrische_entscheidungen.yaml`.
Sie standen **nicht** im Verzeichnis der abgeleiteten Register
(`scripts/abgeleitete_register.py`) – damit fehlte ihnen der Nachzug am
Erzeuger. Fünf offene Meldungen in fünf Tagen waren die Folge, jede nur mit
dem Satz „Akte: 202 offen, Ledger: 202" (zwei gleiche Zahlen, keine Ursache).

Drei Änderungen:

1. **Registriert.** Die Akte ist jetzt das dritte abgeleitete Register. Der
   bestehende PR-Test (`test_alle_register_sind_aktuell`) und der Nachzug im
   Deploy-Pfad gelten damit automatisch auch für sie.
2. **Nachzug am Erzeuger.** `scripts/git_sync.sh` hat einen Haken
   `faktenfrische_akte_nachziehen` – dieselbe Bauart wie der
   Abbildungs-Nachzug seit dem 30.10.2026. Wer Queue, Entscheidungen,
   Scorecard-Siegel oder Bestand committet, zieht die Akte **in denselben
   Commit**. Seine Artefakte werden einzeln gestagt (kein `git add -A`).
3. **Idempotent auf Bytes.** Der Schreiber stempelt keinen neuen Zeitstempel,
   wenn sich fachlich nichts geändert hat. Sonst hätte der Aufruf im
   Deploy-Pfad („Gate-Heilungen committen" hängt an `git status --short`)
   eine Schleife aus Commit → Rebuild → Commit erzeugt.

**Die Meldung nennt jetzt die Ursache.** Statt zweier gleicher Zahlen steht
dort zum Beispiel:

```
🛑 BEFUND-AKTE.md ist veraltet – Zustand weicht ab –
   ueberholt: Akte 247 ≠ Quelle 252.
   Heilung: python3 scripts/faktenfrische_befund_akte.py --schreiben
```

**Ein Urteil, zwei Leser.** Der Schreiber bietet `--check` (schreibfrei,
Exit 1 bei Drift) und wird von der Nachlauf-Wache über dieselbe Funktion
befragt (`pruefen()`). Vorher hatte die Wache eine eigene, abweichende
Logik.

### 2.3 Gleichartige Alarme werden gebündelt

**Befund:** Jede Befundänderung erzeugte einen neuen Fingerabdruck und damit
eine neue Issue-Nummer. Geschlossen wurde nur bei einem **grünen** Lauf –
also blieben #1229, #1251, #1252, #1266, #1267, #1271 gleichzeitig offen, für
einen Gegenstand.

**Änderung:** `issues_schliessen()` und der neue `issue_nachfuehren()` in
`scripts/veroeffentlichungs_wache.py`:

* Ein offenes Issue mit **demselben** Fingerabdruck ist die Meldung – keine
  zweite Nummer.
* Offene Issues mit **anderem** Fingerabdruck werden als **überholt**
  geschlossen, mit Verweis auf den neueren Stand. Das Wort „behoben" wird
  dabei bewusst **nicht** verwendet – die Meldung war nicht falsch, sie ist
  veraltet. Nichts wird gelöscht.

### 2.4 Der Frontmatter-Fehlalarm, der Artikel als unbaubar markierte

**Befund (#1285/#1287):** Die Nachlauf-Wache meldete auf `main`

```
F3: Schlüssel `id` steht doppelt (zuerst Zeile 39).
Hugo bricht den Bau daran ab (mapping key already defined)
```

für `content/posts/2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen/index.md`.
Die Datei enthält drei Quellen mit je einem `id` – **gültiges YAML**:

```
$ python3 -c "import yaml; print([q['id'] for q in yaml.safe_load(open(...))['quellen']])"
['Q1', 'Q3', 'Q5']
```

**Ursache:** `scanne_yaml` schnitt den Eintragsmarker `- ` ab, *bevor* es die
Doppelt-Prüfung fragte. `rest_zeile.startswith("-")` war danach für **jeden**
Top-Level-Listeneintrag falsch – die Prüfung hielt jeden Eintrag für ein
Feld des Wurzel-Mappings. Ein BLOCKER auf einer Datei, die Hugo fehlerfrei
baut.

**Änderung:** Der Marker wird vor dem Abschneiden gemerkt (`sequenz`).
`- key: wert` eröffnet ein **neues** Mapping je Eintrag – gleiche Schlüssel
in verschiedenen Einträgen sind YAML-korrekt.

**Gegenprobe bleibt scharf:** Ein echtes Duplikat auf oberster Ebene
(`draft: false` / `draft: true`) ist weiter BLOCKER – ohne Parser und mit
Parser. Der Fehlalarm ist nicht gegen einen Blindfleck getauscht.

### 2.4 Die Meldung selbst: aus „API-Key abgelaufen" wird die Git-Klasse

`push_diagnose.py` ist ein Werkzeug – solange niemand es aufruft, ändert es
keinen Rat. Deshalb ist es jetzt **verdrahtet**:

* `.github/workflows/alert-on-failure.yml` erkennt, wenn ein roter Schritt
  ein Commit-/Push-Schritt ist (`COMMIT_SCHRITT`-Muster), und vergibt die
  Runbook-Klasse `commit-push`.
* Der Rat nennt zuerst den **Beleg-Befehl** (`push_diagnose.py --tage 14`)
  und dann je Klasse genau einen nächsten Schritt. Er sagt ausdrücklich, was
  **nicht** hilft: ein API-Key kann diesen Schritt nicht rot machen, und
  „neu starten" ist nur bei `netzwerk` richtig.
* Die Erkennung ist **fail-open**: Fehlt das Werkzeug, bleibt der bisherige
  Rat stehen. Ein Melder darf nicht zum Vorfall werden.

Zwei Szenarien in `scripts/tests/sim/alert_scoping_sim.mjs` halten beides
fest – den echten Fall (#1246: „Audit-Log-Stand committen") und die
Gegenprobe (ein roter **Selbsttest** bleibt Code-Regression und wird NICHT
als Commit-Fehler gelesen).

### 2.45 Eine Falle, die beim Bauen dieser Klasse aufgefallen ist

GitHub drosselt mit **HTTP 429** – und tarnt das regelmäßig als **403**
(„secondary rate limit"). Das Auth-Muster liest `403`. Die erste Fassung
hatte `rate_limit` deshalb als *unbekannt* bzw. als *auth* eingeordnet:
Eine Drosselung wäre als angebliches Token-Problem gelesen worden – genau
der Fehler, den dieses Werkzeug behebt, nur eine Ebene tiefer.

Behoben in der **Rangfolge** (`KLASSEN`, aus der `RANG` entsteht):
`rate_limit` steht jetzt vor `auth` und vor `netzwerk`. Sieben Tests halten
die vier Richtungen fest: 429 → Drosselung, als 403 getarnte Drosselung →
Drosselung, echtes Auth → Auth, gewöhnlicher Netzwerkfehler → Netzwerk.

Der Rat für diese Klasse ist der einzige, der **widerspricht**: „ERNEUT
VERSUCHEN MACHT ES SCHLIMMER" – jede weitere Runde zählt auf dasselbe
erschöpfte Kontingent. Ein `Re-run` ist hier die falsche Antwort.

### 2.5 Nebenbefund aus dem PR-Lauf: Beacon ohne CSP-Erlaubnis

Der erste PR-Lauf (449…) meldete im Layout-Audit auf **jeder** betroffenen
Seite denselben Konsolenfehler:

```
Loading the script 'https://static.cloudflareinsights.com/beacon.min.js'
violates the following Content Security Policy directive:
"script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com"
```

`static/_headers` erlaubt Cloudflare nur für Turnstile
(`challenges.cloudflare.com`). Der Web-Analytics-Beacon läuft über eine
**andere** Domain. Das Partial `cloudflare_analytics.html` rendert nur bei
`mode = "manual"` **und** gesetztem `website`/`token` – in `hugo.toml` steht
davon nichts. Das Skript kam also über Cloudflares automatische Injektion
ins ausgelieferte HTML; das Repo konnte die CSP-Verletzung nicht verhindern.

**Geändert (vertretbar ohne Workflow-/Cloudflare-Rechte):**

* Der Vertrag steht jetzt **am Ort der Einbindung** statt nur in einem
  Bericht: Wer den Beacon lädt, ergänzt zuerst
  `https://static.cloudflareinsights.com` bei `script-src` **und**
  `connect-src` in `static/_headers` – und in `cloudflare/edge-schutz.md`,
  sonst driftet die Edge-Kante vom Repo.
* `scripts/tests/test_cloudflare_analytics_csp.py` prüft die Kombination
  (nicht die Einstellung): Ist der Beacon aktiv, MUSS die CSP ihn erlauben;
  ist er still, darf die Domain **nicht** in der CSP stehen (keine
  unnötige Angriffsfläche). Gegenprobe belegt: Bei simuliert aktiver
  Einbindung wird der Test rot.

**Nicht geändert:** `static/_headers` und `cloudflare/**` sind
sicherheitsrelevante Dateien (Sicherheitsregel 3, `CLAUDE.md`). Die
eigentliche Wahl – Beacon behalten und CSP erweitern **oder** die
automatische Injektion im Cloudflare-Dashboard abschalten – trifft der
Inhaber.

---

## 3. Was ausdrücklich NICHT geändert wurde

* **Branch-Schutz nicht gelockert.** Keines der drei Regelsets wurde
  angefasst. Die Beweislage zeigt: Sie haben keinen dieser Läufe blockiert.
  Wer „Push abgelehnt" sieht, prüft zuerst die Klasse – nicht das Ruleset.
* **Kein `git push --force`, kein Bypass, kein `continue-on-error`** auf den
  Commit-/Push-Schritten. Ein Rennen wird durch Serialisierung gelöst, nicht
  durch Überschreiben.
* **Live-Content bleibt unantastbar.** Der Konfliktfall #1254 bleibt ein
  harter Stopp; die opt-in-Politik `GIT_SYNC_BESTAND_POLICY` ist
  unverändert und wird nicht zum Default.

---

## 4. Nachweis

```bash
# 1. Klassen gegen die echten Vorgangs-Texte (offline)
python3 -m unittest scripts.tests.test_push_diagnose -v

# 2. Live-Diagnose über die letzten Tage (nur lesend, braucht gh)
python3 scripts/push_diagnose.py --tage 7

# 3. Die Befund-Akte folgt ihrer Quelle
python3 scripts/faktenfrische_befund_akte.py --check
python3 scripts/abgeleitete_register.py --check

# 4. Der Fehlalarm ist weg, die Erkennung bleibt scharf
python3 scripts/frontmatter_wache.py --selftest
python3 -m unittest scripts.tests.test_frontmatter_wache

# 5. Alarme werden gebündelt
python3 scripts/veroeffentlichungs_wache.py --selftest

# 6. Beacon-Behelf: keine Auslieferung gegen die eigene CSP
python3 -m unittest scripts.tests.test_cloudflare_analytics_csp
```

**Erwartete Ergebnisse (auf diesem Stand gemessen):**

| Prüfung | Ergebnis |
|---|---|
| `frontmatter_wache.py --selftest` | 25 Proben grün |
| `frontmatter_wache.py --kurzbefund` auf `content/` | 0 Blocker (vorher 2 Fehlalarme) |
| `faktenfrische_befund_akte.py --check` | grün, 293 offene Befunde |
| `abgeleitete_register.py --selftest` | 3 Register, Drift-Erkennung belegt |
| `veroeffentlichungs_wache.py --selftest` | 17 Fälle grün |
| `push_diagnose.py --selftest` | 8 Klassenproben grün |
| `python3 -m unittest scripts.tests.test_git_sync` | 60 Tests grün |
| `python3 -m unittest scripts.tests.test_cloudflare_analytics_csp` | 6 Tests grün |
| `integrity_guard.py --gate` · `--selftest` · 66 Vertragstests | grün |
| `workflow_vertrag_wache.py --online --gate` | 103 Workflows, 0 Verstoß |
| `artefakt_waechter.py` | 709 Artefakte heil |
| `pflichtcheck_guard.py` | Exit 0 (Bekannt-Befund, kein neuer Vorfall) |

---

## 5. Restrisiko und nächster Schritt

* **Serienbrief statt Einzelfall:** Push-Rennen bleiben möglich, solange
  mehrere Schreiber denselben `main` bedienen. `git_sync.sh` heilt sie
  (Rebase-Runden, `GIT_SYNC_TRIES`), aber sie kosten Läufe. Der nächste
  wirksame Schritt wäre eine gemeinsame `concurrency`-Gruppe für alle
  Schreiber auf `main` – das ist eine **Workflow-Änderung** und braucht den
  ausdrücklichen Auftrag des Inhabers (Sicherheitsregel 3 in `CLAUDE.md`).
  `push_diagnose.py` liefert dafür die Zahlen: es zählt die Rennen.
* **`netzwerk` bleibt eine Restmenge.** Das ist bewusst so: Ein Werkzeug,
  das aus „nicht erkannt" eine Ursache macht, würde wieder raten. Die
  Restmenge ist jetzt aber *benannt* und mit Belegquelle versehen.
* **Offene Meldungen aus der Zeit davor** (u. a. #1244, #1246, #1251,
  #1252, #1229) schließen sich über den regulären Weg: ein grüner Lauf auf
  `main` – oder der nächste Befundstand, der sie als überholt erklärt.
  Sie werden nicht von Hand „weggeschlossen".

---

## 7. Nachtrag: die beiden offenen Punkte sind entschieden (21.11.2026)

Der Inhaber hat beide Fragen beantwortet. Beide Antworten sind unten
umgesetzt — und bei beiden hat die Umsetzung meinen ersten Befund korrigiert.

### 7.1 Serialisierung: „Nur belegte Kollisionen"

**Die Entscheidung.** Nicht alle 61 Schreiber in eine Gruppe, sondern die
geometrisch belegten Kollisionen.

**Warum nicht alle — in Zahlen.** Eine Gruppe über alle 61 Schreiber hätte
als Obergrenze die Summe ihrer Job-Timeouts: **2.015 Minuten = 33,6
Stunden** Warteschlange, inklusive `deploy.yml` (170 min). `cancel-in-progress:
false` heißt: Es wird gewartet, nicht abgebrochen. Ein einzelner hängender
Lauf hätte die gesamte Nachtkette blockiert.

**Der eigentliche Befund.** Meine erste Erklärung („die drei Läufe starten
gleichzeitig") war **falsch**. Ihre Cron-Zeiten sind 04:35, 04:45 und 04:50 —
verschiedene Minuten. Der 16.11.2026 war ein **Montag**. Die Überlappung
kommt nicht von der Startminute, sondern von der **Laufzeit**:

| Workflow | Start | Gemessene Laufzeit |
|---|---|---|
| ZEIT-Rechtschreib-Wache | 04:35 | 40 s |
| FrankAutoOps-Report | 04:45 | **693 s (11,6 min)** → bis 04:56 |
| Hemingway-Check | 04:50 | 55 s |

04:45 + 11,6 min reicht über den Start der beiden anderen hinaus. Alle drei
hatten eine `concurrency`-Gruppe — aber eine **eigene**. Eine eigene Gruppe
serialisiert einen Workflow gegen *sich selbst* und gegen nichts sonst.

**Was jetzt gilt** (`scripts/schreiber_serialisierung.py`, Gruppe
`main-schreiber`):

* die Montagskette (`zeit-rechtschreibung`, `frankautoops-report`,
  `hemingway-check`) — der belegte Vorfall;
* die vier Minuten-Kollisionen aus dem Bericht (04:30, 04:53, 07:00, 09:30);
* **10 von 60** Schreibern.

**Was ausdrücklich draußen bleibt:** `deploy.yml`. Ein Deploy, der hinter
Bot-Läufen wartet, verzögert die Auslieferung. Die Ausnahme steht als
begründeter Eintrag (`EIGENE_GRUPPE`), nicht als Lücke.

**Was die Wache prüft** — und was sie NICHT prüft:

```
$ python3 scripts/schreiber_serialisierung.py
Schreiber-Serialisierung: 10/60 Schreiber teilen die Gruppe `main-schreiber`
51 Befund(e): …
```

Die 51 offenen Befunde sind **ehrlich offen**, nicht weggedrückt: Der
Zuschnitt ist eine Entscheidung, kein Messergebnis. Wird die Wache als
blockierendes Gate verdrahtet, wäre sie rot, solange der Zuschnitt gilt.
Deshalb läuft sie als **Messung** (Selbsttest blockierend im Governance-Gate,
`C6`/`GUARDS`): Die Regel wird bei jedem Lauf geprüft, der Ist-Zustand
berichtet. Wer einen weiteren Schreiber serialisieren will, trägt ihn ein —
und der Befund verschwindet, statt sich zu wiederholen.

**Drei Fehlversuche, die die Wache selbst gebaut haben** (alle als
Gegenprobe im Selbsttest, 12 Fälle):

1. Textsuche fand `git_sync.sh` in einem `#`-Kommentar.
2. Nach dem Filtern aller `#`-Zeilen fand sie es in einem `//`-Kommentar
   des JS-Blocks von `alert-on-failure.yml`.
3. Nach dem Filtern von `#` und `//` fand sie es in einem **JS-String** —
   dem Rat-Text „Was der Rat NICHT ist: … `git_sync.sh` benutzt kein
   Modell". Ein Stück Prosa, das zufällig einen Dateinamen enthält.

Drei Filter, drei neue Löcher. Die Wache liest deshalb **YAML strukturell**
und prüft ausschließlich `run:`-Blöcke. Ein vierter Fehler kam vom
Regressionstest, nicht von mir: `git -c user.name="Bot" push` wurde nicht
erkannt — genau die Form, die in mehreren Workflows steht.

### 7.2 CSP/Beacon: „CSP erweitern + Audit härten"

**Die Entscheidung.** Beacon bleibt, CSP erlaubt ihn, und der Audit belegt
künftig, woher eine CSP stammt.

**Erweitert** (`static/_headers` **und** `cloudflare/edge-schutz.md`, damit
die Edge-Kante nicht vom Repo driftet — geprüft von `blog_header_gate.py`,
Regel S1/S2):

```
script-src  … https://static.cloudflareinsights.com
connect-src … https://cloudflareinsights.com
```

**Gehärtet** (`scripts/layout_browser_check.js`): Der Audit nimmt jede
Antwort-Kopfzeile auf und unterscheidet:

* CSP-Verstoß **mit** beobachteter Direktive → Seitenbefund (rot, wie bisher).
* CSP-Verstoß **ohne** beobachtete Direktive → **unbelegt**: Er erscheint als
  Frühwarnung mit Grund, macht den Lauf aber nicht rot.

**Warum das nötig war, in einem Satz:** Die Meta-CSP im gebauten HTML hat
gar kein `script-src`, und der lokale Messserver setzt überhaupt keine
CSP-Kopfzeile. Die Direktive im Befund konnte aus keiner der beiden Quellen
stammen — der Audit hat eine Bedingung gemeldet, die er selbst nie gesehen
hatte. Ein Befund, dessen Ursache niemand zuordnen kann, ist eine
Behauptung, kein Befund.

**Ein Test musste umgeschrieben werden.** Die alte Prämisse von
`test_cloudflare_analytics_csp.py` war „der Beacon wird nie geladen, also
darf die Domain nicht in der CSP stehen". Der Befund vom 21.11. widerlegt
das: Der Beacon war im ausgelieferten HTML, obwohl das Partial nichts
rendert — die Injektion passiert an der Edge. Der Test hält jetzt die
Gegenrichtung fest (Gegenprobe: ohne die Freigabe wird er rot, 2 Tests).

### 7.3 Korrektur eines früheren Befunds von mir

Ich hatte behauptet, `main` erscheine in einem frischen Checkout **wegen
eines `chmod`-Artefakts im 06:56-Commit** als komplett neu. Das war
**falsch**. Ursache war meine eigene Umgebung: Der Checkout war *shallow*
(`git rev-parse --is-shallow-repository` → true), also hatte der einzige
sichtbare Commit keinen Vorfahren.

Mit voller Historie (`git fetch --unshallow`, 5.950 Commits) ist `8af6f73`
ein normaler Commit mit dem Elternteil `ce6d96b` und **drei geänderten
Dateien**. Alle Dateimodi im Baum sind `100644`/`100755` — kein
`chmod`-Artefakt. Die Behauptung ist damit zurückgezogen.

### 7.4 Nachweis

| Prüfung | Ergebnis |
|---|---|
| `schreiber_serialisierung.py --selftest` | 12/12 Fälle grün |
| `python3 -m unittest scripts.tests.test_schreiber_serialisierung` | 18 Tests grün |
| `python3 -m unittest scripts.tests.test_layout_audit_csp_beleg` | 7 Tests grün |
| `python3 -m unittest scripts.tests.test_cloudflare_analytics_csp` | 6 Tests grün |
| `blog_header_gate.py --offline` (S1/S2: Repo ↔ Edge-Vorlage) | grün |
| `governance_contract.py` (47 Regeln, C6/`GUARDS`) | erfüllt |
| `wachen_vertrag.py` | 408 Skripte, 0 Funde |
| `workflow_vertrag_wache.py --gate` | 103 Workflows, 0 Verstoß |
| `skript_syntax_wache.py --check` | 730 Dateien grün |
| `redos_guard.py` | 814 Dateien, 0 Funde |
