# Wartung · Veröffentlichung · Vorgang WF-829B (#922) — Siegel-Dauerheilung, 04.11.2026

**Vorgang:** WF-829B · **Issue:** [#922](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/922)
**Auftrag:** [#1039](https://github.com/frank-hartung/franksfinanzcheck-blog/pull/1039) — „Bitte dauerhaft auf Highend-Level einer Profi-Agentur beheben."
**Stand der Messungen:** 04.11.2026, 09:45–11:10 UTC · alle Werte am echten Baum und am echten Artefakt gemessen
**Vorberichte:** `…-2026-10-29.md` · `…-2026-10-30.md` · `…-2026-11-01.md` · `…-2026-11-03.md`

---

## 1. Kurzfassung

PR #1039 war rot. Der Bericht war es nicht — das **Siegel** war es. In `main` stand seit dem 02.11.2026 ein `data/integrity_lock.json`, in dem **drei Fassungen zeilenweise übereinanderlagen**. Aufgefallen ist das nur, weil zwischen zwei Blöcken ein Komma fehlte; die Datei war dadurch unparsebar und `--gate` meldete „ZERSTÖRT". Mit diesem einen Komma wäre sie **gültiges JSON** gewesen — und das Gate hätte „ok" gesagt.

Genau diese Lücke ist jetzt geschlossen, und zwar an vier Stellen mit je eigenem Beweis: im Prüfer, vor jedem Urteil (Eichprobe), in der Commit-Sperre und im PR-Gate.

| Nr. | Befund | Heilung | Stand 04.11. |
|---|---|---|---|
| **A** | Der Lock in `main` ist ein Zusammenschnitt aus drei Fassungen (13:23 / 14:32 / 19:13 UTC des 01./02.11.) | Kein Handanlegen: `--repair-lock` nimmt die belegte Fassung — hier ist `main` selbst bereits wieder signiert (55 Kerndateien, Kette 12 Einträge); dieser PR zeichnet den neuen Stand | **geheilt** |
| **B** | Ein **parsebarer** Zusammenschnitt galt als `ok` — `json.loads()` nimmt still den letzten Wert, Kette und Map-Prüfsumme bilden sich aus genau dieser Mischung | `_doppelte_schluessel()` prüft die Bytes vor jeder anderen Frage; Befund `beschaedigt` / `zusammenschnitt` mit Namen der doppelten Schlüssel | **geheilt**, mit Vorher/Nachher-Messung belegt |
| **C** | Der Prüfer konnte sich unbemerkt verschlechtern: Läuft in der CI eine ältere Fassung, meldet sie „ok" | **Eichprobe vor jedem Urteil** (`_messfaehigkeit_pruefen`): baut den Vorfall ohne Dateizugriff und verlangt das beschädigte Urteil. Sonst Exit 3 „Messgerät nicht eichfähig" — in `--gate` **und** im Standardlauf | **geheilt** |
| **D** | `scripts/tests/test_integrity_guard.py` (die Verträge des Prüfers) lief in **keinem** Workflow — ein Vertrag ohne Lauf ist Prosa | Eigener Schritt im `Integritäts-Siegel`-Job: `python3 -m unittest scripts.tests.test_integrity_guard` (66 Tests, offline) | **geheilt** |
| **E** | Der Fehler entstand beim **Commit**, nicht im PR-Gate Tage später | `.githooks/pre-commit` prüft den **gestageten** Lock auf doppelte Schlüssel und Gesundheit — in einem Wegwerf-Verzeichnis, offline, < 1 s | **geheilt** |
| **F** | #922 selbst: Environment `cloudflare-produktion` ohne Reviewer, ohne Branch-Regel, mit Admin-Bypass | Nicht im Repository heilbar — heute **erneut gemessen**: `--anwenden` → HTTP **403** (Rechtebefund), `--check` Exit 1, `--pruefen` 3 Ziele offen | **Inhaber** (Abschnitt 6) |

**Nichts wurde gelockert, um Grün zu erzeugen.** Der harte Stopp bleibt hart, die Rechte-Grenze bleibt eine Grenze, und der Befund steht im Bericht statt in einem Kommentar.

---

## 2. Forensischer Befund

### 2.1 Was in `main` stand — Bytes, nicht Vermutung

`git show 1854c1092:data/integrity_lock.json` (Zweig von PR #1039, auf `main`-Stand 038b04fee):

```
{\n  "schema": 2,\n
  "signed_at": "2026-11-02T13:23:38.630367+00:00",\n  "head": "26eedfa",\n
  "signed_at": "2026-11-01T14:32:11.060118+00:00",\n  "head": "887248e",\n
  "files": { … },\n            ← 19:13-Fassung beginnt hier (Byte 550)
  "signed_at": "2026-11-01T19:13:31.294398+00:00",\n  "head": "4366b11",\n
  "files": { … }
```

Messung am Original: `schema` 1×, `signed_at` **3×**, `head` **3×**, `files` **2×**. Bruchstelle: Byte 13638 von 25044, „Expecting ',' delimiter".

Gefunden wurde das nicht von einer Wache, sondern von `scripts/tests/test_fremdmessung_sperre.py` — einem fachlich völlig unbeteiligten Test, der den Lock liest und an `json.JSONDecodeError` starb.

### 2.2 Der teure Teil: es hätte auch PARSEBAR sein können

Der Unterschied zwischen „rot" und „still falsch" war **ein Komma**. Gegenprobe am echten Artefakt:

```text
Vorher (Stand main):        Zusammenschnitt MIT fehlendem Komma  → beschaedigt / abbruch
Nachher (gehärtet, Komma ergänzt, Datei PARST):
  alter Prüfer (main)  → Zustand: ok          · Detail: „Kette, Map-Prüfsumme und Generation sind in Ordnung"
  neuer Prüfer         → Zustand: beschaedigt  · Verdacht: zusammenschnitt
```

Der alte Prüfer sagt also **`ok`** zu einer Datei, die eine Map der 19:13-Fassung mit einer `signed_at` der 13:23-Fassung verbindet. Kette und `files_sha256` konnten das nie bemerken: Beide werden aus den **geparsten** Daten gebildet, also aus genau der Mischung.

### 2.3 Dieselbe Klasse am selben Tag, andere Datei

`cf1b80786` („Siegel für den Skill-Regelkern", 02.11.) trägt im Lock-Diff drei Zeilen, die es in einem Werkzeug-Schreibvorgang nicht gibt:

```
+    "scripts/publikations_vertrag.py": "70fb8867…",
+    "scripts/redaktions_standard.py": "78ad7d32…",
     "scripts/publikations_vertrag.py": "aed03d79…",   ← dieselbe Datei, zweiter Wert
     "scripts/redaktions_standard.py": "da9e8f2a…",
     "scripts/redaktions_standard.py": "0d1a4384…",   ← dritter Wert
```

Dazu im selben Commit `skills_vertrag.py` mit **doppelten Funktionsdefinitionen** und ein `scripts/safe_xml.py`, dessen `selftest`-Zeile fehlt (dieselbe `Quote fehlt`-Klasse, die `selftest_runner.py` noch heute für `net_safety.py`/`safe_xml.py` meldet). Ein Muster, keine Serie von Zufällen: Der Regelkern wurde an mindestens einer Stelle wie Text behandelt.

### 2.4 Was der Branch-Schutz dazu sagt — und warum es niemand aufhielt

`gh pr checks 1021` (der Merge, der das kaputte Siegel nach `main` brachte): `Integritäts-Siegel` **fail**, `gate` **fail**, `regression` **fail** — und der PR wurde gemergt. Das ist kein neuer Befund, sondern der in `docs/PFLICHT-CHECK-RUNBOOK.md` dokumentierte Dauerzustand (C18): Das Ruleset verlangt diesen Check nicht. Der Bericht wiederholt es hier, weil es die Ursache dafür ist, dass ein rotes Siegel **in** `main` liegen konnte — nicht, um es zu entschuldigen.

---

## 3. Dauerhafte Heilung — vier Schichten

### S1 · Erkennung im Prüfer (`scripts/integrity_guard.py`)

`_doppelte_schluessel(text)` liest die **Bytes** und fragt: Steht ein Objektschlüssel in einem Objekt mehrfach? Der Befund kommt **vor** Map- und Kettenfrage — fail-closed:

```text
**Siegel ZERSTÖRT (kein gültiges JSON)** · 25044 Bytes · Verdacht: zusammenschnitt
- 3 Objektschlüssel stehen mehrfach im Siegel (`schema`, `signed_at`, `head`) –
  zwei Fassungen wurden übereinandergelegt, `json.loads()` nimmt still den letzten Wert.
- Ein solches Siegel ist für KEINEN Zeitpunkt eine Messung: Map und Akte können aus
  verschiedenen Generationen stammen, auch wenn Kette und Prüfsumme zufällig passen.
- Reparatur: `--repair-lock` (belegte Quelle aus Git oder Bergung) – keine Handarbeit.
```

`--repair-lock` bleibt der einzige Weg zurück und zeichnet **keine** Datei neu (Akte: `art: repair`, Quelle, Bruchstelle, Bytes).

### S2 · Eichprobe vor jedem Urteil (`zusammenschnitt_probe`, `_messfaehigkeit_pruefen`)

Der Selbsttest prüft den Code, der ihn gerade ausführt — nicht den Code, der in der CI läuft. Deshalb baut die Eichprobe den Vorfall **im Speicher** (kein Dateizugriff, C15) und verlangt:

```text
parsebar=True · Zustand=beschaedigt · Verdacht=zusammenschnitt
```

Weicht das ab, gibt das Gate **keine** Freigabe: Exit 3 mit „MESSGERÄT NICHT EICHFÄHIG", erwartetem und gemessenem Ergebnis und Reparaturzeile. Das gilt für `--gate` **und** für den Standardlauf (`verify`) — der Zustand „ok" ist ein Urteil, und ein Urteil ohne geprüftes Messgerät ist eine Behauptung.

### S3 · Commit-Sperre (`.githooks/pre-commit`)

Der Fehler entstand am 02.11. beim Schreiben, nicht beim Review. Der Haken prüft jetzt — **vor** dem Markenflächen-Teil, unabhängig von ihm — den **gestageten** Lock:

```bash
git show :data/integrity_lock.json > "$PRUEFSTAND_SIEGEL/lock.json"
python3 - "$PRUEFSTAND_SIEGEL/lock.json" <<'PY'   # derselbe Prüfer wie das Gate
…  ig._doppelte_schluessel(text) → doppelt?  → Exit 1
…  ig._zustand_aus_bytes(...)    → nicht gesund? → Exit 1
PY
```

Kein zweiter Wahrheitsbegriff: Es läuft `integrity_guard`, nicht eine Kopie seiner Regel. Ein Trap räumt **beide** Prüfstände (der alte Haken hatte zwei `trap`s, der zweite ersetzte den ersten).

### S4 · Verträge im PR-Gate (`.github/workflows/integrity-lock.yml`)

Neuer Schritt im Pflicht-Check-Job, direkt nach `--selftest`:

```yaml
- name: Siegel-Verträge (Regressionstests des Prüfers selbst)
  run: python3 -m unittest scripts.tests.test_integrity_guard
```

Neu in `scripts/tests/test_integrity_guard.py`:

- `ParsebarerZusammenschnittTests` (7 Fälle): doppelte Schlüssel werden gefunden · parsebarer Zusammenschnitt ist **nicht** gesund · `--gate` ist rot und nennt `--repair-lock` · Dry-Run schreibt nichts (C15) · Reparatur stellt **eine** Fassung her und die Map ist die belegte · Akte sagt `repair` · Signieren adelt den Fehler nicht.
- `EichprobeTests` (2 Fälle): Die Probe ist parsebar und wird erkannt · **Sabotage** (Doppelte-Schlüssel-Prüfung fällt aus) ⇒ Gate Exit 3 mit „NICHT EICHFÄHIG".

Der Selbsttest des Guards zählt jetzt **11** eingefrorene Fälle (vorher 9): `parsebarer_zusammenschnitt_erkannt`, `signatur_mit_doppeltem_schluessel_abgelehnt`.

### Dokumentation

`docs/SICHERHEIT-BETRIEB-RUNBOOK.md` § **G3b** (neu): Vorfall, Tabelle der vier Schichten, Vorher/Nachher-Messung, Reparaturweg — und ausdrücklich das, was **offen** bleibt (§ 5).

---

## 4. Verifikation (04.11.2026, alles lokal ausgeführt)

| Prüfung | Ergebnis |
|---|---|
| `python3 scripts/integrity_guard.py --selftest` | ✅ 11 Fälle + Kern-Beweis, ohne Schreibzugriff auf den Baum |
| `python3 -m unittest scripts.tests.test_integrity_guard` | ✅ 66 Tests OK (vorher 59) |
| Uhr-Probe `selftest_clock.py --trap-modul …test_integrity_guard --offset 97` | ✅ grün |
| Uhr-Probe `--offset 1461` | ✅ grün |
| `python3 scripts/integrity_guard.py --gate` | ✅ 55 Kerndateien == signierter Stand, Eichprobe bestanden |
| Vorher/Nachher am echten Artefakt (parsebarer Zusammenschnitt) | ✅ alt: `ok` → neu: `beschaedigt` / `zusammenschnitt` |
| Commit-Sperre, Wegwerf-Repo, 4 Fälle | ✅ gesund: durch · parsebarer Zusammenschnitt: **blockiert** · unparsebar: **blockiert** · nur README: durch, Prüfstände aufgeräumt (0 Reste) |
| `python3 scripts/workflow_vertrag_wache.py --selftest` / `--gate` | ✅ 98 Workflows, kein Befund (V1–V6) |
| `python3 scripts/trigger_wache.py --check` | ✅ 98 Workflows, 0 Befunde |
| `python3 scripts/wachen_vertrag.py` | ✅ 374 Skripte, 0 Funde (inkl. `W5-MERGE-BINARY`) |
| `python3 scripts/governance_contract.py --quick` | ✅ 45 Regeln grün |
| `python3 scripts/skript_syntax_wache.py --check` | ✅ 632 Dateien grün |
| `python3 scripts/artefakt_waechter.py` | ✅ 564 Artefakte strukturell heil |
| `bash -n .githooks/pre-commit` | ✅ Syntax grün |
| `python3 scripts/selftest_runner.py --ohne-uhr-probe` | ✅ 265 Wachen gelaufen; **eine** rote = `cover_render_check.py` (Prüfgrundlage: `pillow` fehlt in dieser Sandbox, #1001-Klasse, kein Wachen-Defekt) |
| `python3 scripts/worker_environment_guard.py --check` (live, GITHUB_TOKEN) | ✅ Exit **1** — fail-closed, 3 Befunde (erwartet, ungesichert) |
| `python3 scripts/worker_environment_einrichten.py --pruefen` | ✅ Exit 1 — MACHBAR / OBERFLAECHE / MACHBAR korrekt beziffert |
| `python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung` | ✅ Exit 1 — **HTTP 403**, Rechtebefund (unverändert) |
| `python3 scripts/worker_freigabe_wache.py --check` (live) | ✅ Exit 0 — kein Lauf wartet über der Schwelle |

---

## 5. Grenzen dieser Heilung (bewusst benannt)

- **Wie die Datei nach `main` kam, ist nicht vollständig erklärt.** `merge=binary` steht seit #346 in `.gitattributes`, es gibt keinen Konfliktmarker, und der Commit `cf1b80786` hat keinen Merge-Elternteil an dieser Datei. Drei Fassungen in einer Datei entstehen aber nicht durch einen einzelnen Schreiber (`lock_schreiben` prüft den erzeugten Text **vor** dem Schreiben und liest ihn zurück). Der Weg dorthin ist damit offen — **nicht** offen ist, ob es jemand merkt: Commit, Prüfer und Gate melden es jetzt an drei Stellen, jede mit eigenem Beweis.
- **Ein Text-Merge-Verbot ist keine Unfallversicherung.** `.gitattributes` gilt für `git merge`; was außerhalb davon Dateien schreibt (Skripte, Automationen, Werkzeuge mit eigenem Schreibpfad), hält es nicht auf. Deshalb prüft die Heilung das **Ergebnis** (Bytes), nicht nur den Weg (Merge-Strategie).
- **Der Branch-Schutz verlangt diesen Check weiterhin nicht** (C18-Dauerzustand). Ein rotes `Integritäts-Siegel` hält einen Merge nachweislich nicht auf (PR #1021 ist dafür der jüngste Beleg). Das ist eine Admin-Entscheidung, keine Code-Frage — der Bericht nennt sie, statt sie zu umgehen.
- **Die Eichprobe prüft den Prüfer, nicht die Welt.** Sie beweist, dass die Messung den Vorfall noch sieht. Sie beweist nicht, dass jede denkbare Beschädigung erkannt wird.
- **#922 selbst bleibt eine Inhaber-Aufgabe.** `can_admins_bypass` nimmt keine API an, und dem Token fehlt `Environments: write` (403, heute erneut belegt).

---

## 6. Was offen bleibt — Inhaber-Aufgabe (unverändert, heute erneut gemessen)

**Schritt 1 — Environment absichern** (Settings → Environments → [`cloudflare-produktion`](https://github.com/frank-hartung/franksfinanzcheck-blog/settings/environments)):

1. *Required reviewers* → **Frank Hartung**.
2. *Deployment branches and tags* → **Selected branches and tags** → Regel `main`, sonst nichts.
3. *Allow administrators to bypass configured protection rules* → **aus**.

Punkte 1 und 2 nimmt die API an, sobald das Token sie darf; Punkt 3 ist ausschließlich Dashboard (REST: `additionalProperties: false`; GraphQL kennt das Feld nicht).

```bash
export GITHUB_TOKEN=…   # feingranular: Environments: read/write
python3 scripts/worker_environment_einrichten.py --anwenden --reviewer frank-hartung
npm run worker:environment        # muss danach Exit 0 melden
```

**Schritt 2 — Deploy starten und freigeben** (Actions → „Cloudflare-Worker deployen" → Run workflow): Der Job `deploy` hält an (*Review deployments*) — das ist die gewollte Wirkung. Freigeben über die Oberfläche oder:

```bash
R=frank-hartung/franksfinanzcheck-blog
gh api "repos/$R/actions/runs/<run_id>/pending_deployments"
gh api -X POST "repos/$R/actions/runs/<run_id>/pending_deployments" \
  -F environment_ids[]=<id> -f state=approved -f comment="Produktionsdeploy freigegeben"
```

**Abschluss:** Zwei grüne Deploy-Jobs, `/healthz` liefert `bau == ff-newsletter-2026-10-24`, `scripts/alert_resolve_gate.py` bestätigt den Job-Beweis. Erst dann schließt #922 automatisch — ein grüner Plan oder dieser Bericht schließen ihn ausdrücklich **nicht**.

---

## 7. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/integrity_guard.py` | `_doppelte_schluessel`, Befund im Zustand, `zusammenschnitt_probe`, `_messfaehigkeit_pruefen` (Gate **und** Verify), Selbsttest-Fälle 10d/10e, `SELFTEST` 9 → 11 |
| `scripts/tests/test_integrity_guard.py` | `ParsebarerZusammenschnittTests` (7), `EichprobeTests` (2) |
| `.github/workflows/integrity-lock.yml` | Schritt „Siegel-Verträge" (66 Tests) im Pflicht-Check-Job |
| `.githooks/pre-commit` | Siegel-Prüfung des gestageten Locks, ein gemeinsamer Trap |
| `docs/SICHERHEIT-BETRIEB-RUNBOOK.md` § G3b | Vorfall, vier Schichten, Messung, offene Grenzen |
| `WARTUNG-…-2026-11-03.md` | Nachtrag mit Verweis auf diesen Bericht |
| `data/integrity_lock.json`, `data/integrity_history.jsonl` | neu signiert (`set-current`, 55 Kerndateien, Akte 12 Einträge) — der Siegel-Sperre-Haken prüft genau diesen Stand |

---

*Geheilt, gemessen und dokumentiert am 04.11.2026. Der Bericht von gestern bleibt gültig — er beschrieb den Vorgang; dieser beschreibt, warum er blockiert war und was jetzt verhindert, dass es unbemerkt bleibt.*
