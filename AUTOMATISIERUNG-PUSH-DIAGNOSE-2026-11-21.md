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
