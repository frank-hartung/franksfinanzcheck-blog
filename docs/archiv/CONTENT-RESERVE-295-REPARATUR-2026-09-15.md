# Content-Reserve (täglicher Vorrat) – Issue #295 dauerhaft repariert (15.09.2026)

**Betroffener Workflow:** `.github/workflows/content-reserve.yml` (03:25 UTC, täglich)
**Fehlerlauf:** Actions-Run `34949097389` (Commit `72cea5e7`, Laufzeit 12 m 13 s)
**Ergebnis vor der Reparatur:** 12 von 12 Fachstufen grün – trotzdem roter Lauf
(Stufe „Sichern“ gescheitert, End-Gate „Stock shortage“ gescheitert).

---

## 1. Befund (was wirklich passierte)

Der Lauf hatte **zwei** voneinander unabhängige Fehlschläge:

| Schritt | Ergebnis | Ursache |
|---|---|---|
| 1–12 (Produktion, Veredelung, Zertifizierung, Konvergenz, Triage) | ✅ | – |
| 13 „Entwürfe, Zertifikate und Reporte sichern“ | ❌ | `git_sync.sh`: Rebase-Konflikt gegen `origin/main` → „Kein Push“ |
| 14 „Stock shortage must not look successful“ | ❌ | Zertifikat meldete 0/6 (bzw. real 5 Entwürfe, Ziel 6) |

Die Annotation des Schritts 13 ist eindeutig:

> `git_sync.sh: Rebase-Konflikt gegen origin/main (ein paralleler Workflow hat dieselben Zeilen geändert). Kein Push – Arbeitsstand bleibt lokal sauber. Nur echte Content-Konflikte benötigen manuelles Mergen; generierte Report-/JSONL-Konflikte werden automatisch geheilt.`

Beweis für den Konfliktgegenstand: Während der Reserve-Lauf sicherte, schrieb der
Deploy-/Auslieferungslauf `344bc20` (15.09.2026, **10:50:30 UTC**) genau dieselbe
Datei nach `main`, die der Reserve-Lauf gerade neu erzeugt hatte:
**`data/reserve-readiness.json`** (im Commit-Diff enthalten, 67 Zeilen geändert).
Die Auto-Heilung in `git_sync.sh` kannte bis dahin nur Reports, JSONL-Historien
und Cache-Dateien – ein Zertifikatskonflikt war für sie ein „echter“
Content-Konflikt und beendete den Lauf.

## 2. Root-Cause-Analyse (vier Ursachen, nicht eine)

### Ursache A – Push-Konflikt auf einem reinen Maschinen-Artefakt
`data/reserve-readiness.json` ist ein hash-gesichertes Zertifikat und wird von
**jedem** Lauf komplett neu erzeugt. Es ist kein redaktioneller Text und darf
nie manuell gemergt werden. Ein einzelner Konflikt darauf machte den ganzen
Nachtlauf rot, obwohl der Pool gesund war.

### Ursache B – Der Zielbestand war strukturell unerreichbar
- Der Reserve-Top-up produzierte **höchstens einen** Roh-Kandidaten pro Nacht
  (`for _ in range(2)` mit In-Flight-Schutz), während Publikationstage 1–3
  Artikel aus dem Pool verbrauchen (`reserve_pool.publish_to_min` als
  Brandschutzlinie). Ein Vorrat, der mit 1/Nacht aufgefüllt und mit bis zu
  3/Tag geleert wird, kann ein Ziel von 6 nie halten.
- Zusätzlich blockierte der In-Flight-Schutz den Nachschub **innerhalb**
  derselben Nacht: `reserve_finisher.lift_to_today()` hebt jeden offenen
  Kandidaten auf „heute“ – danach gilt *jeder* unzertifizierte Kandidat als
  „in flight“, also lief die frühere Konvergenz (ein einzelner Nachschub-Block)
  garantiert ins Leere. Der Pool pendelte bei 5/6 und der harte End-Gate wurde
  jede Nacht rot.

### Ursache C – Zwei Kandidaten hingen dauerhaft unter dem Gate
Die Reserve-Veredelung ruft `check_length.py --fix` korpusweit auf. Dieses
Skript **überspringt Entwürfe** (`draft: true`) – die Pool-Kandidaten sind aber
bewusst Entwürfe. Folge: Die beiden zu kurzen Kandidaten wurden nie verlängert
und blieben unter der Struktur-Schwelle des Quality-Scores (Wortzahl < 1.200 →
Teilscore 0.70). Nachweis (lokaler Reproduktionslauf auf `main`):

```
2026-09-11-finanzieller-puffer-…   1135 Wörter / 7.900 Zeichen  → structure 0.70, Score 0.845
2026-09-13-gasrechnung-senken-…    1158 Wörter / 7.845 Zeichen  → structure 0.70, meta 0.70, Score 0.800
                                    (Schwelle: 0.85)
```
Beide Defizite sind deterministisch heilbar: Verlängerung auf ≥ 1.400 Wörter
(Struktur 1.0, +0,045) und ein fehlender Satzpunkt am Description-Ende
(Meta 1.0, +0,045/0,09 – das erledigt der Meta-Heiler der Kette).

### Ursache D – Der Lauf committete LIVE-Bestand mit
Die Veredelungs-Kette enthält bewusst die *bewährten* Heiler der Live-Engine –
darunter korpusweite Läufe (`--fix` ohne Scope) sowie `generate_covers.py`
und `check_covers.py`. Sie heilen Live-Posts (die ebenfalls auf „heute“ datiert
sind), rendern Live-Cover neu und schreiben Manifeste. Der Sicherungs-Schritt
staggte mit `git add -A` alles davon. Zwei Folgen:
1. Die Konfliktoberfläche explodierte (Content **und** Cover-Binärdateien).
2. Es verletzte das Besitzverhältnis: Live-Content gehört der Engine-/
   Deploy-Kette, nicht dem Reservisten.

## 3. Dauerhafte Reparatur

### 3.1 `scripts/git_sync.sh` – maschinengenerierte Artefakte heilen selbst
Neue Auto-Heilungs-Regel (letzter Schreiber gewinnt, `--theirs` = der frische
Lauf, dessen Ergebnis gerade gepusht wird):

```
data/reserve-readiness.json|data/covers_manifest.json)
  git checkout --theirs -- "$f" … git add -- "$f"
```

Beide Dateien werden bei jedem Lauf vollständig neu erzeugt; ein Blatt-Merge
verliert keine Information. **Echte Content-Konflikte bleiben ein harter
Stopp** (unverändert, inklusive Test).

### 3.2 `scripts/git_sync.sh` – Reserve-Kandidaten sind maschinenverwaltet
Der Lift der Veredelungs-Stufe benennt jeden Kandidaten um; ein parallel
laufender Korpus-Heiler, der eine stale Kopie desselben Kandidaten anfasst,
erzeugt daraus einen echten Rebase-Konflikt. Da Kandidaten bis zur
Veröffentlichung ausschließlich der Reserve-Stufe gehören (und ihr
sha256-Zertifikat exakt für diese Bytes gilt), heilt `git_sync.sh` diesen Fall
nach derselben Regel: **frischer Lauf gewinnt** – aber nur, wenn *beide* Seiten
unmissverständlich Reserve-Entwürfe sind (`reserve: true`, kein `draft: false`).
Live-Artikel, Re-Queue-Posts und Hand-Entwürfe lösen weiterhin den harten
Stopp aus (drei Regressionen, siehe Abschnitt 4).

### 3.3 `scripts/reserve_finisher.py` – Live-Korpus-Isolation
Ein deterministischer Wächter friert vor der Heiler-Kette den Arbeitsbaum-Zustand
aller geschützten Wurzeln (`content/ static/ data/ layouts/ assets/
archetypes/ hugo.toml`) ein und stellt danach **jede** Änderung außerhalb der
erlaubten Kandidaten-Pfade bytegenau zurück:

| Klasse | Behandlung |
|---|---|
| getrackte Fremd-Datei geändert/gelöscht | `git checkout -- <pfad>` (bytegenau auf HEAD) |
| neue Fremd-Datei | Quarantäne `$TMP/reserve-isolation-quarantine` (nichts wird gelöscht) |
| erlaubt | Kandidatenordner `content/posts/<slug>/`, Cover `static/images/covers/<slug>*`, `data/reserve-readiness.json`, `data/covers_manifest.json`, Append-only-Historien `data/**/*.jsonl` |

Zusätzlich rendert die Kette Cover jetzt **pro Kandidat**
(`generate_covers.py --slug {slug}`, neuer Scope `slug` in `HEALER_CHAIN`) statt
korpusweit – der Bedarf an Fremd-Änderungen entsteht gar nicht mehr.
Jeder Eingriff wird in `RESERVE-FINISH-REPORT.md` protokolliert.

### 3.4 `scripts/reserve_stage_guard.py` – Staging-Politik (neu)
`git add -A` ist ersetzt: Das Skript stagt nur Pool-Pfade, prüft **jede**
gestagte Content-Datei auf `reserve: true`, nimmt Fremd-Content wieder aus dem
Index (und setzt getrackte Live-Dateien bytegenau auf HEAD zurück) und meldet,
was bewusst liegen bleibt. Selbsttestend, unabhängig vom Isolation-Wächter
(zwei Lagen, eine fällt aus → die andere greift).

### 3.5 `scripts/reserve_converge.py` – zielgerichtete Konvergenz (neu)
Stufe 4 ist jetzt eine begrenzte Schleife statt eines wirkungslosen
Einzelblocks:

```
Runde 1..3:
  brauche := RESERVE_TARGET − zertifizierte Kandidaten
  wenn brauche == 0 → fertig (grün)
  Produktion   engine_generate --reserve-only   (RESERVE_FORCE_TOPUP=1,
               RESERVE_TOPUP_BATCH=min(brauche,4))
  Veredelung   reserve_finisher.py --finish
  Zertifizierung reserve_readiness.py
  wenn kein Fortschritt (weder READY noch Pool gewachsen) → Abbruch
```

Der In-Flight-Schutz bleibt im Normalbetrieb unverändert streng; nur die
Konvergenz-Stufe hebt ihn ausdrücklich und begrenzt auf (Ziel, Kapazitätsdeckel
12, Themen-Dedup `_pool_conflicts`). Abbruchkriterien verhindern Endlosschleifen
und unbegrenzte KI-Kosten. Die Stufe meldet ehrlich `exit 1`, wenn das Ziel
nicht erreicht wurde – die Bewertung macht der End-Gate.

### 3.6 `scripts/check_length.py` – Entwürfe heilen (Reserve #4-Klasse)
Neu: `--include-drafts` und `--file <pfad>` (datei-bezirkelt). Der Finisher ruft
die Längenheilung jetzt als `check_length.py --fix --include-drafts --file
<candidate>` auf. Damit wird ein zu kurzer Pool-Kandidat per
`extend_articles.py --slug <slug>` auf ≥ 1.400 Wörter gebracht – und **nur**
er, nie der Korpus.

### 3.7 `scripts/reserve_gate.py` – kein veraltetes Zertifikat als Nachweis
Der End-Gate prüft zusätzlich das Alter (`generated_at`, Grenze
`RESERVE_CERT_MAX_AGE_H`, Default 36 h). Ein Zertifikat ohne verwertbaren
Zeitstempel wird gewarnt, ein zu altes ist blockierend – die Klasse
„Zertifikat von gestern sagt 6/6, Pool hat real 4 Entwürfe“ ist damit tot.

### 3.8 `.github/workflows/content-reserve.yml`
- Selbsttest-Stufe prüft jetzt auch `reserve_converge.py` und
  `reserve_stage_guard.py` (Sabotageschutz: ein kaputter Heiler darf nicht
  still weiterarbeiten).
- Stufe 4 ruft `scripts/reserve_converge.py --runden 3` auf.
- Sicherungs-Schritt nutzt `reserve_stage_guard.py` statt `git add -A` und
  schreibt die gestagten Änderungen ins Log.

## 4. Beweise (Regressionen)

| Test | Beweist |
|---|---|
| `scripts/tests/test_git_sync.py::RaceUndKonfliktTests::test_reserve_zertifikat_konflikt_heilt_frischer_lauf_gewinnt` | Der Konflikt, der den Lauf rot machte, heilt jetzt (frischer Lauf gewinnt) |
| `…::test_cover_manifest_konflikt_heilt_frischer_lauf_gewinnt` | Dasselbe für das Cover-Manifest |
| `…::test_content_konflikt_bleibt_harter_stopp` (Bestand) | Echter Content-Konflikt bleibt hart – kein Blind-Merge |
| `scripts/tests/test_git_sync.py::ReserveKandidatKonfliktTests::test_beide_seiten_reserve_entwurf_heilt` | Konflikt auf einem Reserve-Kandidaten (beide Seiten `draft+reserve`) heilt – frischer Lauf gewinnt |
| `…::test_live_artikel_bleibt_harter_stopp` / `…::test_hand_entwurf_ohne_reserve_marker_bleibt_harter_stopp` | Live-Content und Hand-Entwürfe werden NIE automatisch gemergt |
| `scripts/tests/test_reserve_pipeline.py::LiveKorpusIsolationTests` | Fremd-Änderungen (Live-Post, Live-Cover) werden bytegenau zurückgestellt, neue Fremd-Dateien wandern in Quarantäne, Kandidaten/manifeste/JSONL bleiben |
| `…::StagingPolicyTests` | Live-Content wird nie gestagt; der Staging-Selbsttest bleibt grün |
| `…::KonvergenzTests` | Ziel-Abbruch ohne Produktion, Fortschritts-Abbruch nach einer Runde, Runden- und Batch-Deckel (max. 4) |
| `…::GateFrischeTests` | Altes Zertifikat ⇒ kein Nachweis; frisches Zertifikat trägt |
| `…::LaengenHeilungTests` | Entwürfe werden nur mit `--include-drafts`/`--file` gesehen (Live-Korpuslauf unverändert) |
| `python3 scripts/reserve_converge.py --selftest` | Konvergenz ohne API/Hugo (Fake-Runner) |
| `python3 scripts/reserve_stage_guard.py --selftest` | Staging-Politik gegen ein Wegwerf-Repo |

Alle Tests laufen im bestehenden PR-Gate
`.github/workflows/publication-reliability-tests.yml`
(`python3 -m unittest discover -s scripts/tests`).

## 5. Betrieb (Runbook)

- **Grün** heißt: `data/reserve-readiness.json` führt mindestens
  `RESERVE_TARGET` (Default 6) `ready: true`-Kandidaten, das Zertifikat ist
  jünger als 36 h, und der Stand ist in `main` angekommen.
- **Rot bei echter Knappheit bleibt rot** („Stock shortage must not look
  successful“). Die Diagnose steht je Kandidat im Zertifikat (`reason`) und im
  `RESERVE-FINISH-REPORT.md`.
- **Notbremse/Stellschrauben** (Repository-Variablen bzw. Env):
  `RESERVE_TARGET` (Ziel), `RESERVE_TOPUP_BATCH` (1–4, Deckel im Generator),
  `RESERVE_FORCE_TOPUP` (nur Konvergenz-Stufe setzt das),
  `RESERVE_CERT_MAX_AGE_H` (Frische-Grenze des Zertifikats).
- **Wenn der Pool trotz grüner Stufen leer bleibt:** zuerst
  `python3 scripts/reserve_converge.py --status` (Zählung aus der
  Kandidatenliste), dann das KI-Quota prüfen – der Nachschub ist der einzige
  Schritt, der von den Providern abhängt.
