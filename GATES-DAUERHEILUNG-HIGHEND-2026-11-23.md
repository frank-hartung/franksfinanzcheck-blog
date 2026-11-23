# Gates-Dauerheilung auf Highend-Niveau — 23.11.2026

**Auftrag.** Die sechs beim Merge von PR #1317 rot gewesenen Qualitäts- und
Content-Gates — `Integritäts-Siegel`, `Playwright-Suite`, `YMYL-Siegelprüfung`,
`Entity-Marken-Gate`, `Gate`, `Skript-Syntax` — vollständig und dauerhaft auf
dem Niveau einer Profi-Agentur beheben. Der Betreiber stellte ausdrücklich
klar, dass diese Gates **inhaltlich Teil des Auftrags** sind und nicht
„separates Repo-Geschäft".

**Vorausgegangene Runde.** PR #1317, gemerged als Squash `d3b318a` am
22.11.2026 20:54:30 UTC (23 Dateien, +2469/−61). Seine Akte:
`GATES-DAUERHEILUNG-HIGHEND-2026-11-22.md`. Alle dortigen Heilungen sind im
Bestand nachgewiesen (siehe Abschnitt 2.3).

**Messumgebung.** `.venv` aus `requirements-ci.txt` (`--require-hashes`) plus
`hugo==0.168.0`; `npm ci --ignore-scripts` + `npm run browser:setup`
(gebündelter Chromium 153.0.8010.0 unter
`/tmp/franksfinanzcheck-chromium/153.0.0/chromium`). Alle Messungen in dieser
Akte sind selbst gefahren, nicht abgelesen.

---

## 1. Ergebnis in einem Absatz

Die sechs genannten Gates sind am liegenden Stand **grün** — lokal gemessen und
in CI bestätigt (Abschnitt 2). Grün allein war aber keine Antwort auf den
Auftrag, denn „dauerhaft" heißt: Rot muss **wieder laut werden können**. Genau
das war es nicht. Die Wurzel dieser Runde liegt nicht in einem der sechs Gates,
sondern im Meldeweg: **37 von 105 Workflow-Dateien standen nicht auf der
Wacht-Liste des Fehler-Alertings**, darunter vier der sechs Gates des Auftrags.
Wer auf `main` rot wurde, erzeugte kein Issue. Belegter Schaden: die
`KI-Provenienz-Wache` lief **8 von 8 Malen rot** — 12 ungeklärte Register-Fälle,
9 Tage vor der Rechtsfrist 2026-12-02 — und es entstand **keine einzige
Meldung**, obwohl ihr Befund wörtlich „braucht Menschen" sagt (Abschnitt 3).
Dazu drei Bestandswunden: zwei Inhaltsseiten ohne jeden redaktionellen Inlink
(Abschnitt 4 — von `main` parallel bytgleich geheilt, der Befund und die
Messung bleiben, die doppelte Buchhaltung nicht), eine Inhalts-Wache ohne einen
einzigen Aufrufer (Abschnitt 5) und ein Schreibschutz, der ein Siegel
behauptete, wo keines war (Abschnitt 6). Übrig bleiben **8 Dateien** Delta,
reine Ingenieursarbeit.

---

## 2. Die sechs Gates: Messung am liegenden Stand

Gemessen am 23.11.2026 auf `48da9e8` (= `origin/main`,
`chore(scorecard): Release-Scorecard aktualisiert + Live-Bestand versiegelt`),
nach Fast-Forward von `35c7f36`.

### 2.1 Lokal gefahrene Prüfer

| Gate des Auftrags | Prüfer | Messung | Urteil |
|---|---|---|---|
| Integritäts-Siegel | `integrity_guard.py` | Selbsttest + Bestand | ✅ Exit 0 |
| Playwright-Suite | `npx playwright test` | **184 passed (9.0m)**, Exit 0 | ✅ |
| YMYL-Siegelprüfung | `ymyl_siegel_wache.py` | **139 Artikel · 0 Befunde** | ✅ |
| Entity-Marken-Gate | `entity_marken_gate.py` | **0 Fehler, 0 Warnungen** | ✅ |
| Gate (Frontmatter, ohne Build) | `fm_boundary_guard.py --selftest` / `--check` | 18 Wert- + 4 Grenz-Fälle · **175 Dateien sauber** | ✅ |
| Skript-Syntax | `skript_syntax_wache.py` | **736 Dateien grün** | ✅ |

Begleitend, weil dieselbe Fläche: `h1_wache` (jede Seite genau eine H1) ✅ ·
`linktext_wache` (428 Seiten, 14811 Links, 933 Bilder; L3 368 `alt=""`, 413
Ankertexte > 60 Z., **0 über der Fehlergrenze 80**) ✅ · `schema_seo_gate` ✅ ·
`seo_cockpit` (152 Seiten, 123 indexierbar, P1 0 / P2 0 / P3 10) ✅ ·
`ki_bild_markierung --gate` (0/0/0) ✅ · `check_covers` (**145 Covers, 0
Probleme, 0 Stale, 0 Brand, 0 Text**) ✅ · `check_titles` (**145 Titel, 0
Verstöße**) ✅ · `metadaten_wache` (13 Proben inkl. M5) ✅ ·
`frontmatter_wache` (175 Dateien, 0 Blocker, 0 Hinweise) ✅ ·
`governance_contract --quick` (**alle 47 Regeln in beide Richtungen**) ✅ ·
`konfliktmarker_wache` (6686 → 6703 Dateien, keine Marker) ✅ ·
`workflow_js_wache --check` ✅ · `hugo_build_vertrag` ✅ · Hugo-Build Exit 0,
**3171 Dateien** in `public/`.

### 2.2 CI am aktuellen `main`-Stand

Letzte Läufe der sechs Gates (Abfrage `actions/workflows/<slug>.yml/runs`):

| Workflow | letzte drei Läufe |
|---|---|
| `integrity-lock` | success 10:15 · success 10:12 · cancelled 10:11 |
| `e2e` (Playwright) | in_progress 10:15 · success 10:12 · cancelled 10:11 |
| `ymyl-siegelwache` | success 10:15 · success 10:12 · success 10:11 |
| `entity-marken-gate` | success 09:59 · success 09:59 · success 22.11. 20:54 |
| `seo-paritaet` (Job „Gate (Frontmatter, ohne Build)") | success 09:59 · success 20:54 · success 20:04 |
| `skript-syntax` | success 10:15 · success 10:12 · success 10:11 |
| `link-check` (Qualitäts-Gate) | in_progress 10:15 · in_progress 10:12 · cancelled 10:11 |

`cancelled` 10:11 sind `concurrency`-Abbrüche durch nachrückende Commits
(`group: linkcheck-${{ github.ref }}`, `cancel-in-progress`), keine Fehlschläge.

### 2.3 Die Heilungen aus #1317 sind im Bestand angekommen

Nachweis über den Inhalt, nicht über den SHA (der Klon ist flach, `d3b318a`
ist lokal nicht auflösbar):

| Heilung | Nachweis auf `origin/main` |
|---|---|
| Rechtsnorm statt Modellwert (`sprachkern.py`) | `_zaahlbehauptung` 5× vorhanden |
| Beleg-Drift-Klasse (`ki_cover_herkunft.py`) | `beleg_veraltet` 3× vorhanden |
| Trigger-Vertrag (`trigger_wache.py`) | `relevante_workflows` 8× vorhanden |
| Notbremse (`git_sync.sh`) | `trigger_notbremse` 3× vorhanden |
| Inhalts-Wache erweitert (`ff_inhalts_wache.py`) | `feld_proben` 3× vorhanden |
| Tests beider Richtungen | `RechtsnormStattModellwert` vorhanden |
| Akte | `GATES-DAUERHEILUNG-HIGHEND-2026-11-22.md` vorhanden |

Wirkung im Betrieb, selbst gemessen: `ki_cover_herkunft.py --pruefen` →
**„145 Cover reproduziert, 2 außerhalb des Renderbereichs
(Marken-/statische Seiten), 0 Befund(e)"** — dieselbe Klasse, die am 22.11.
noch 14 Befunde zählte, ist strukturell still.

---

## 3. Wurzelheilung H — Blindstelle im Fehler-Alerting

### 3.1 Befund

`alert-on-failure.yml` („Fehler-Alerting") verspricht im Kopfsatz:
**„Beobachtet ALLE automatischen Workflows."** Gemessen am 23.11.2026 standen
auf der Wacht-Liste (`on.workflow_run.workflows`) **68 Namen**; im Bestand
liegen **105 Workflow-Dateien**. Die Lücke: **37**.

Darunter **vier der sechs Gates dieses Auftrags**:

| Workflow-Datei | Name | Gate des Auftrags |
|---|---|---|
| `entity-marken-gate.yml` | Entity-Marken-Gate (Marken-Identität) | ✅ Entity-Marken-Gate |
| `ymyl-siegelwache.yml` | YMYL-Siegelwache | ✅ YMYL-Siegelprüfung |
| `seo-paritaet.yml` | SEO-Parität (Cornerstones · Fokus-Keywords · Social-Karten) | ✅ trägt den Job „Gate (Frontmatter, ohne Build)" |
| `integrity-lock.yml` | Integritäts-Lock (PR-Gate) | ✅ Integritäts-Siegel |

Dazu `lesbarkeit-live-diff.yml`, `beweis-gate.yml`,
`bestand-regression-wache.yml`, `endredaktion.yml`, `cockpit.yml`,
`schaltwerk.yml`, `werkbank.yml`, `redaktionelle-ymyl-pruefung.yml`,
`release-scorecard.yml`, `robustheit.yml`, `spam-schutz-wache.yml`,
`sprach-qualitaet-pipeline.yml`, `ki-provenienz-wache.yml` und 16 weitere.

### 3.2 Belegter Schaden — nicht vermutet

Die `KI-Provenienz-Wache` ist **chronisch rot**, acht Läufe in Folge, alle vor
und nach dem Merge von #1317, also unabhängig von dieser Arbeit:

| Run | Commit | Zeit |
|---|---|---|
| 45069072213 | `d3b318a` | 22.11. 20:54 |
| 45062204321 | `b3445bb` | 22.11. 19:41 |
| 45048494558 | `fa3e8d0` | 22.11. 17:16 |
| 45043399916 | `bc1e022` | 22.11. 16:21 |
| 45038283842 | `5c5ee46` | 22.11. 15:26 |
| 45023756848 | `8a1d01c` | 22.11. 12:43 |
| 45019893738 | `dccdf19` | 22.11. 11:58 |
| 45018465675 | `41bcb4e` | 22.11. 11:40 |

Roter Schritt jedes Mal: `11: Befund durchreichen (rot bleibt rot)` — das
korrekte fail-closed-Verhalten. Der Befund selbst, lokal reproduziert mit
`python3 scripts/ki_provenienz_gate.py --wache` (Exit 1):

```
- Selbstheilung: 0 Eingriff(e), 1 Eskalation(en)
  - ⚠️ braucht Menschen (register) `data/ki_kennzeichnung.yaml`: 12 Fälle aus
    Register und Wachzustand sind 9 Tage vor der Frist (2026-12-02) ungeklärt –
    ältester seit 16 Tagen (2026-08-14-internet-dsl-wechseln-praxis-tipps-…)
- Funde nach der Heilung: 0
- Deckung: 123/123 Seiten, 50 Feed-Items, 0 deklarierte KI-Cover
```

**Und es entstand keine Meldung.** Offene `auto-report`-Issues am 23.11.2026:
acht — #1152, #1191, #1230, #1235, #1248, #1280, #1283, #1284. Keines für die
KI-Provenienz-Wache. Ein Befund, der wörtlich „braucht Menschen" sagt,
erreichte neun Tage vor einer Rechtsfrist keinen Menschen.

Das ist **Befund E** (18.09.2026: 14 rote Gate-Läufe, null Meldungen, ~35 %
Ereignisverlust) eine Ebene höher. Dort verlor der Kanal Ereignisse; hier war
der Lauf nie gelistet, es gab also nicht einmal ein Ereignis, das man hätte
verlieren können. Der Herzschlag (`alerting_heartbeat.py`) konnte das nicht
merken, denn sein Vertrag lautet in `abgleich()` wörtlich: „nur gelistete
Workflows". **Ein Kanal, der seine eigene Reichweite nicht misst, meldet seine
Blindstelle nicht.**

### 3.3 Warum Schein-Deckung keine Deckung ist

Nicht jeder der 37 fehlenden Namen durfte einfach eingetragen werden. Die
Alarm-Logik scopet auf Produktion (`alert-on-failure.yml:310`):

```js
const isProdRun = branch === defaultBranch && event !== 'pull_request';
```

Ein Workflow, der **ausschließlich** auf `pull_request` läuft, kann danach nie
eine Meldung erzeugen. Ihn zu listen wäre Schein-Deckung: Die Liste täuschte
Vollzähligkeit vor, während die Meldung strukturell ausbleibt — schlimmer als
eine ehrliche Ausnahme. Rote PR-Läufe sind als Checks am PR sichtbar und
gehören zum Handwerk (Reparatur der Fehlalarm-Klasse #343).

Klassifizierung aller 37, maschinell über `trigger_wache.trigger()` gelesen:
**31 können auf `main` laufen** (`push`, `schedule`, `workflow_dispatch`,
`repository_dispatch`, `pull_request_target`) → aufgenommen. **4 können es
nicht** → begründet ausgenommen. Dazu die 2 bereits dokumentierten Ausnahmen.

### 3.4 Heilung

**(a) Wacht-Liste: 68 → 99 Namen.** Jeder Eintrag mit Grund im Hausstil, die
belegten Schäden wörtlich genannt (z. B. „war am 22.11. 13:18 rot – keine
Meldung" für den GSC-Tageslauf, 13:15 für die Release-Scorecard, 16:00 für den
wöchentlichen Live-SEO-Crawl). Identitäten mussten nicht gepflegt werden:
`alert_issue_identity.py` leitet Code, Bereich und Titel aus
`sha256(name)` ab — Selbsttest danach **99 Workflows, 99 eindeutige Codes,
Titel markenfrei**.

**(b) Begründete Ausnahmen: 4 neu, im Kopfblock „BEWUSST NICHT ÜBERWACHT".**
`🤖 Auto-Assign PR zu frank-hartung` und `Lesbarkeit (Live-Änderungen)` (beide
nur `pull_request` → #343), `Reserve-Nachweis` und `Reserve-Nachweis #614`
(Einmal-Proben auf einem fremden Ref). Eine undokumentierte Lücke gibt es
danach nicht mehr.

**(c) Die Deckung selbst unter Wache gestellt** — das ist der dauerhafte Teil,
denn eine einmal korrigierte Liste altert wieder. Neu in
`alerting_heartbeat.py`:

* `workflow_bestand()` — zählt jede Workflow-Datei über
  `trigger_wache.workflow_dateien()` (eine Wahrheit, zwei Orte) und liest
  `name:` und Trigger-Arten aus der Datei, nie abgetippt.
* `bewusst_nicht_beobachtet()` — liest die Ausnahmen **aus dem Kopf der
  Workflow-Datei selbst**. Fehlt der Marker, gilt alles als blind: fail-closed
  in die sichere Richtung.
* `deckung_pruefen()` — vier Befundklassen, alle fail-closed:

| Klasse | Bedeutung |
|---|---|
| `blind` | kann auf `main` laufen, ist aber weder gelistet noch ausgenommen — **Rot würde niemand erfahren** |
| `scheindeckung` | steht auf der Liste, kann aber nicht auf `main` laufen — die Deckung ist nur Schein (#343) |
| `unbegruendet` | kann nicht auf `main` laufen und ist weder gelistet noch begründet ausgenommen — die Entscheidung versteckt sich |
| `verwaist` | Name auf der Liste passt zu keiner Workflow-Datei (umbenannt/gelöscht) — der Eintrag feuert nie wieder |

* **Netzunabhängig.** Die Deckung wird in `main()` **vor** der Token-Prüfung
  gemessen und auch im Fehlerpfad gemeldet: Ist der Token weg oder die API tot,
  fällt genau diese Prüfung nicht mit aus (C33: ausgefallene Messung ist kein
  Grün). Nachweis: `env -u GH_TOKEN -u GITHUB_TOKEN python3
  scripts/alerting_heartbeat.py` → Exit 2 **und** der volle Deckungs-Bericht.
* Sie läuft bei jedem Herzschlag mit, nicht nur auf Zuruf (`--deckung`).

**(d) Proben in beide Richtungen.** `D1–D10` im Selbsttest des Herzschlags:
vollständige Deckung grün · blinder Workflow rot **und beim Namen genannt** ·
begründete Ausnahme heilt denselben Fall · Schein-Deckung rot · unbegründete
Lücke rot · verwaister Eintrag rot · leere Liste = Status 2, nicht grün ·
Ausnahmen werden gelesen und nie erfunden · echter Bestand grün ·
**Sabotage-Gegenprobe** (ohne `KI-Provenienz-Wache` muss es rot werden).

**(e) Vertrag als CI-Test.** Neue Klasse `DeckungsWache` in
`scripts/tests/test_alerting_heartbeat.py`, **12 Tests**, darunter
`test_gates_des_auftrags_sind_gelistet` (die sechs Gates plus
KI-Provenienz-Wache dürfen nie wieder blind sein) und
`test_deckung_laeuft_ohne_token`.

### 3.5 Gegenprobe: die Wache ist nicht stumpf

Drei Sabotagen am **echten** Bestand, jedes Mal `--deckung` gemessen, danach
Rückbau:

| Sabotage | Erwartung | Messung |
|---|---|---|
| `KI-Provenienz-Wache` aus der Liste | rot, Klasse `blind`, Name genannt | **Exit 1**, `BLIND … **1**`, ❌ nennt `KI-Provenienz-Wache` |
| Phantom-Name `Workflow den es nie gab` eingetragen | rot, Klasse `verwaist` | **Exit 1**, `Verwaiste Namen … **1**`, ❌ nennt den Phantom-Namen |
| Ausnahme-Begründung für `Lesbarkeit (Live-Änderungen)` gelöscht | rot, Klasse `unbegruendet` | **Exit 1**, `Unbegründete Lücke … **1**`, ❌ nennt den Workflow |
| Rückbau auf die geheilte Fassung | grün | **Exit 0**, „✅ Jede Workflow-Datei ist beobachtet oder begründet ausgenommen" |

Messung am geheilten Bestand: **105 Dateien · 99 beobachtet · 7 begründet
ausgenommen · blind 0 · scheindeckung 0 · unbegruendet 0 · verwaist 0**, ein
ehrlicher Hinweis (die Ausnahme `Textverständnis-Patches einspielen (einmalig)`
zeigt auf einen Workflow, den es nicht mehr gibt — Entscheidungs-Geschichte,
kein Schaden).

---

## 4. Zwei Inhaltsseiten ohne redaktionellen Inlink

### 4.1 Befund

Die Voll-Suite war auf `main` **rot**, an zwei aufeinanderfolgenden Ständen
(`35c7f36` und `48da9e8`) gleich:

```
FAIL: test_keine_inhaltsseite_ohne_redaktionellen_inlink
      (test_gsc_abdeckung.BestandOhneInseln.test_keine_inhaltsseite_ohne_redaktionellen_inlink)
  File "scripts/tests/test_gsc_abdeckung.py", line 1232
AssertionError: Lists differ: ['/posts/2026-11-13-geschirrspueler-voll-s…'] != []
  - '/posts/2026-11-13-geschirrspueler-voll-so-sparst-du-wasser-und-strom/'
  - '/posts/2026-11-20-mehrwegflaschen-pfand-so-optimierst-du-deine-fixkosten/'
Ran 6367 tests · FAILED (failures=1, skipped=17)
```

Zwei veröffentlichte Artikel, die **kein einziger** anderer Artikel verlinkt —
Inseln. Für eine Profi-Agentur ist das nicht nur SEO-Technik: Eine Seite ohne
redaktionellen Inlink ist für den Leser nicht erreichbar und für den Crawler
nur über die Sitemap. Der Test ist selbst die Nachmessung der Wache aus #1097.

### 4.2 Heilung über den sanktionierten Weg

Nicht von Hand verlinkt, sondern mit dem Heiler des Hauses
(`gsc_abdeckung.py --verlinkung --heilen --max 10`, seit 06.11.2026 #1097), der
die Sperren prüft (YMYL-Siegel, Goldkorridor, Entwürfe), in die
„Weiterlesen"-Zeile einfügt, jeden Eingriff in `data/verlinkung_history.jsonl`
belegt und **danach nachmisst**:

```
Selbstheilung verwaister Seiten
  vorher ohne Inlink:  2
  Auftrag:             4 Paare (Grenze 10)
  eingefügt:           4
  nachher ohne Inlink: 0
✅ Keine Inhaltsseite ohne redaktionellen Inlink.
```

Die vier Paare: `standby-kosten-reduzieren` → `geschirrspueler-voll` ·
`mehrwegflaschen-pfand` → `geschirrspueler-voll` ·
`waermepumpe-vs-gasheizung` → `mehrwegflaschen-pfand` · `geschirrspueler-voll`
→ `mehrwegflaschen-pfand`. Nachmessung: `Ran 2 tests · OK`.

Folgeprüfung der Fläche: `linktext_wache` ✅ (0 über der Fehlergrenze) ·
`lesbarkeit_diff_wache --basis origin/main` ✅ („Keine neue
Lesbarkeits-Regression unter Flesch 60") · `check_covers` **0 Stale** (die
„Weiterlesen"-Zeile berührt keine Titel, also altern keine Cover) ·
`ki_cover_herkunft --pruefen` **0 Befunde** · `frontmatter_wache` 0 Blocker.

**F4-Dossier:** geschrieben und `--check` aktuell, **2750 Zeilen, bytgleich zu
`main`** — die Datei erschien nicht im Delta. Das ist der praktische Nachweis
für #1324: Das Dossier bindet die **Aussage** (`ledger.text_hash()`, Projektion
`betrieb-v4`), nicht die Datei-Bytes. Eine „Weiterlesen"-Zeile lässt es nicht
altern. Am 22.11. hätte derselbe Eingriff das Dossier neu geschrieben.

### 4.3 `main` heilte dieselben Inseln parallel — Bestand gewinnt

Ehrliche Chronologie, weil sie die Lehre trägt: Während dieser Runde zog `main`
weiter. Commit `8dfe3d9` („Betreiber-Entscheidungen 23.11.") führte **dieselbe**
Heilung aus, 40 Minuten früher und unabhängig:

| | `main` (`8dfe3d9`) | diese Runde |
|---|---|---|
| Zeitstempel im Ledger | `2026-11-23T09:58:30Z` | `2026-11-23T10:38:31Z` |
| Paare | 4, Grund „gleicher Pillar" | 4, **dieselben**, derselbe Grund |
| Artikel-Inhalt | identisch | identisch |

Der Rebase auf `5f12dcc` löste den einzigen echten Konflikt
(`data/gsc/abdeckung/verlinkungsheilung.json`) mit **Bestand gewinnt**; die vier
Artikel-Edits fielen von selbst aus dem Delta, weil sie bytgleich waren. Zwei
Ableitungen wurden bewusst auf den Bestand zurückgesetzt:

* `data/verlinkung_history.jsonl` — dieselben vier Paare standen dort bereits;
  meine Zeilen wären doppelte Audit-Einträge für eine Heilung ohne Netto-Änderung.
* `data/gsc/abdeckung/verlinkungsauftrag.json` — die Fassung des Bestands ist
  die jüngere.

Nachmessung auf der rebasierten Basis: `Ran 2 tests · OK` und
**„Verlinkungsauftrag: 0 Paare"**. Die Inseln sind geheilt — der Nachweis bleibt,
die doppelte Buchhaltung nicht. **„Bestand gewinnt" heißt nicht „eigene Arbeit
wertlos"** (`GIT_SYNC_BESTAND_POLICY`, #590): Der Befund war richtig, die Messung
war richtig, und die Heilung ist im Bestand — nur stammt sie jetzt aus zwei
Läufen, von denen einer genügt.

---

## 5. Wurzelheilung I — eine Inhalts-Wache ohne Aufrufer

### 5.1 Befund

`scripts/ff_inhalts_wache.py` prüft den Artikel-Bestand auf Inhalts-Fehler
FF1–FF5 und trägt einen echten `--selftest`. Offen in §9.3 der Akte vom
22.11. stand: „hat keinen Aufrufer außer `discover`". Jetzt gemessen, nicht
vermutet — mit `trigger_wache.relevante_workflows()` und `trigger_wache.trigger()`
gegen alle 105 Workflow-Dateien:

| Frage | Messung |
|---|---|
| Namentliche Aufrufer in `.github/`, `package.json`, `scripts/*.sh` | **0** |
| Workflows, die bei einer Änderung in `content/posts/**` laufen | **92** (80 ohne jeden `paths`-Filter + 12 mit passendem) |
| davon rufen `ff_inhalts_wache.py` auf | **0** |

Ihr Selbsttest lief über `selftest_runner.py` (die Kennung `"--selftest"` ist
echt, 292 Wachen / 584 Uhr-Proben), die **Prüfung selbst lief nirgends**. Ein
Gate, das nur seine eigene Lauffähigkeit beweist, ist eine Warteschlange und
keine Wache — dieselbe Lehre wie #1097, wo ein Verlinkungs-Auftrag zehn Tage
lang niemand ausführte.

Eine eigene Fehleinschätzung dieser Runde, korrigiert: `relevante_workflows()`
nannte für `scripts/ff_inhalts_wache.py` zunächst **2** Workflows. Das ist für
ihren Zweck (Notbremse vor dem Commit: referenz- oder waisenbruchig?) richtig —
Fall b erfasst jeden Workflow, der einen geänderten Pfad aufruft. Für die
Diagnose-Frage „wer läuft bei Content-Änderungen" ist die Zahl zu klein, denn
Workflows **ohne** `paths`-Filter laufen ebenfalls. Ehrliche Zahl: 92. Die
Funktion wurde deshalb **nicht** geändert; sie war nie falsch, die Frage war
eine andere.

### 5.2 Heilung

Neuer Schritt in `link-check.yml` („Qualitäts-Gate (Build + interne Links)"),
dem Gate, das bei jedem PR, jedem Push auf `main` und per Cron läuft — also
genau dort, wo Content-Änderungen ohnehin geprüft werden:

```yaml
- name: Inhalts-Wache FF1–FF5 (Artikel-Bestand, ohne Build)
  run: |
    set -o pipefail
    python3 scripts/ff_inhalts_wache.py | tee ff_inhalt.log
```

Fail-closed: Exit 1 bei Befund, `set -o pipefail` gegen die Pipe-Falle, kein
`|| true`, kein `continue-on-error`, keine neue Schwelle. Am Bestand:
**„Inhalts-Wache FF1–FF5: 0 Befund(e)"**. Verträge danach neu gemessen:
`workflow_aufruf_vertrag` ✅ · `trigger_wache --check` ✅ (105 Workflows, keine
Befunde) · `hugo_build_vertrag` ✅ · `governance_contract --quick` ✅ (47
Regeln).

**Nachweis im echten CI-Lauf**, nicht nur lokal — Run `45168930434`, Job
`137673060826` („Qualitäts-Gate (Build + interne Links)", Prüfung `gate`,
**pass in 8m38s**), Schrittliste auszugsweise:

```
 4 success Governance-Selbsttests (alle Wachen – entdeckt, uhrfest, schreibfrei)
 5 success Governance-Vertrag C1–C49 (…)
 6 success Skill-Vertrag (Kernbudget, Router, Herkunft, Lizenz, Siegelstand)
 7 success Inhalts-Wache FF1–FF5 (Artikel-Bestand, ohne Build)   ← NEU
 8 success Hugo-Build-Vertrag (eine Fehlerausgabe für alle Workflows)
12 success Bestands-Einzigartigkeit (Diff-Tor, nur Neu-Erzeugtes)
13 success Interne Links prüfen
```

Die Wache läuft damit dort, wo Content-Änderungen ohnehin geprüft werden — bei
jedem PR, jedem Push auf `main` und im Nachtcron. Aus „0 von 92 Workflows" ist
„1 von 92, und zwar der richtige" geworden, und der Schritt steht **vor** dem
Hugo-Bau: Ein Inhalts-Befund bricht den Lauf, bevor Rechenzeit in den Build
geht.

---

## 6. Wurzelheilung J — Schreibschutz ohne unterscheidbaren Grund

### 6.1 Befund

`editorial_review_gate.automatic_write_protected()` ist die konservative
Vorprüfung für Engines, die nur überspringen können. **14 Heiler** hängen daran
(`check_titles`, `meta_optimizer`, `profi_polish`, `update_articles`,
`internal_linker`, `faktenfrische`, `generate_kurzantworten`, `sprachkern`,
`unit_guard`, `pinterest_seo_healer`, `redaktions_standard`,
`release_bestand_heiler`, `compound_guard`, `gsc_abdeckung`). Sie antwortete
`True` für **jeden** Fehler — auch für einen Pfad, den es nicht gibt:

```
existiert, versiegelt    → True      (richtig: Siegel)
existiert, normal        → False     (richtig: frei)
existiert NICHT          → True      (konservativ, aber stumm)
Verzeichnis              → True      (IsADirectoryError)
Leerstring / None        → True      (TypeError)
```

Das Verhalten ist für einen Schreibschutz richtig: nicht schreiben, wenn die
Lage unklar ist. Unbeobachtbar war es trotzdem, und an einer Stelle wurde es
zur **unwahren Aussage**. `check_titles.py:566` druckte für jedes `True`:

```
YMYL: Titel bleibt versiegelt: <pfad>
```

also „dieser Artikel ist redaktionell versiegelt" über eine Datei, die es nicht
gab. Eine falsche Aussage über einen Rechtszustand ist schlimmer als keine: Sie
beruhigt, wo nichts geprüft wurde (C33).

Richtigstellung einer eigenen Notiz vom 22.11.: `--seal --file <fehlender Pfad>`
meldet **ehrlich** „🛑 Freigabe nicht versiegelt: [Errno 2] No such file or
directory" mit Exit 2. Die Maskierung saß nie im Siegel-Bericht, sondern in der
Booleschen Vorprüfung der Heiler.

### 6.2 Heilung

Die Entscheidung bleibt unverändert konservativ; nur ihre Begründung wird
ehrlich. Neu in `editorial_review_gate.py`:

* `automatic_write_protected_grund(path) -> (bool, str)` mit den Gründen
  `siegel` (inhalt_sha256) · `status:<wert>` (freigegeben/approved) ·
  `datei_fehlt` · `unlesbar:<Klasse>`. Leer = nicht geschützt.
* `schutz_meldung(grund)` — Menschentext, der ein Siegel nur behauptet, wenn
  eines da ist: „Freigabe ist versiegelt (inhalt_sha256)" gegen „Datei fehlt –
  nicht versiegelt, sondern NICHT PRÜFBAR".
* `automatic_write_protected()` **delegiert** an die Grund-Funktion: eine
  Wahrheit, Boolesches und Begründung können nie auseinanderlaufen.
* `check_titles.py` nutzt den Grund und druckt bei `datei_fehlt`/`unlesbar:`
  „🛑 Titel nicht prüfbar – <wahre Ursache>" statt der Siegel-Behauptung.

**Nachweis, dass kein Heiler umlernt:** Boolesches bitgleich in allen sechs
Fällen der Tabelle oben (`alt == neu` überall `True`). Bestand danach:
`check_titles` **145 Titel, 0 Verstöße**, Exit 0.

**Proben.** `W1–W14` im Selbsttest des Siegel-Gates: fünf Zustände
(versiegelt · Status-Freigabe · offen · fehlend · Verzeichnis) jeweils auf
Entscheidung **und** Grund geprüft, dazu die Eine-Wahrheit-Probe, kaputtes
Frontmatter (fail-closed, aber ohne Siegel-Behauptung), die Meldungstexte und
eine Sabotage-Gegenprobe. Vier Sabotage-Varianten, im Speicher gesetzt und
gemessen:

| Sabotage | W-Proben rot |
|---|---|
| `datei_fehlt` wird wieder als `siegel` ausgegeben (Maskierung zurück) | **1** |
| immer `(True, "")` — Begründung abgeschaltet | **7** |
| Meldung behauptet Siegel bei fehlendem Pfad | **1** |
| fail-open: `unlesbar` gilt als nicht geschützt | **4** |

Ausgangslage unverändert: **0 Fehler**, `--selftest` Exit 0.

### 6.3 Lage im Bestand: latent, nicht lebendig

Gemessen über alle **175** Content-Dateien mit der neuen Grund-Funktion:
**165 nicht geschützt · 10 `siegel` · 0 fehlend/unlesbar.** Der Befund ist also
**latent** — genau wie der Modellwert-Injektor am 22.11.: keine akute falsche
Meldung heute, aber eine Klasse, die beim ersten kaputten Pfad eine
Rechtsbehauptung erfunden hätte. (Die 10 Siegel stammen aus `48da9e8`
„Live-Bestand versiegelt"; am 22.11. war es eines.)

---

## 7. Nachweis

Alles selbst gefahren am Stand `48da9e8` plus dem Delta dieser Runde, jede
Prüfung einzeln mit Exit-Code — nicht „ein Skript lief durch".

### 7.1 Die beiden Langläufe

| Lauf | Messung | Urteil |
|---|---|---|
| **Code-Regression** (Voll-Suite) | `Ran 6379 tests in 1436.990s` → **`OK (skipped=17)`**, `SUITE_EXIT=0` | ✅ |
| **Uhr-Probe** `--trap-discover scripts/tests --offset 97` | `Ran 6379 tests in 1303.849s` → **`OK (skipped=19)`**, `UHR_EXIT=0`, „✅ scripts/tests: bleibt unter einer um 97 Tage vorgestellten Uhr grün." | ✅ |

Zum Vergleich **vor** der Heilung, derselbe Befehl auf `35c7f36` und auf
`48da9e8`: `Ran 6367 tests` → **`FAILED (failures=1, skipped=17)`**, der rote
Test `test_keine_inhaltsseite_ohne_redaktionellen_inlink` (Abschnitt 4). Die
Testzahl stieg 6367 → **6379** um genau die 12 neuen Deckungs-Tests.

### 7.2 Build und ausgelieferte Seite

| Prüfung | Messung |
|---|---|
| `hugo_build_vertrag.py` | ✅ Vertrag erfüllt |
| `hugo --minify --cleanDestinationDir` | **Exit 0**, 3171 Dateien, 6.3 s |
| **Playwright-Suite** | **184 passed (9.5m)**, Exit 0 |
| `h1_wache --public public` | ✅ jede Seite genau eine H1 |
| `linktext_wache --public public` | ✅ 428 Seiten, 14811 Links, 933 Bilder; 0 über der Fehlergrenze 80 |
| `check_internal_links.sh` | ✅ **5427 interne Links, 0 defekt** — die vier neuen Inlinks lösen auf |
| `schema_seo_gate` | ✅ |
| `seo_cockpit` | ✅ 152 Seiten, 123 indexierbar, P1 0 / P2 0 / P3 10 |
| `entity_marken_gate` | ✅ 0 Fehler, 0 Warnungen |
| `integrity_guard` | ✅ |
| `ki_bild_markierung --gate` | ✅ 0 / 0 / 0 |
| `fm_boundary_guard --check` | ✅ 175 Dateien |
| `bestand_einzigartigkeit_gate --basis origin/main` | ✅ Diff-Tor: 4 geänderte Artikel, **keine neue** kritische Duplikation |

**Build-Gates ROT = 0** nach dem redaktionellen Eingriff.

### 7.3 Selbsttests (die aus CI-Schritt 11 plus die berührten)

`engine_generate` ✅ · `reserve_pool` ✅ · `cadence_guard` ✅ ·
`fm_boundary_guard` ✅ · `social_studio` ✅ · `sprachkern` ✅ (19 Proben:
Rechtsnorm vs. Modellwert) · `editorial_review_gate` ✅ (mit den neuen W1–W14) ·
`alerting_heartbeat` ✅ (mit den neuen D1–D10) · `alert_issue_identity` ✅
(**99 Workflows, 99 eindeutige Codes**, Titel markenfrei) · `selftest_runner` ✅
(Entdeckung, SSOT-Abgleich) · `trigger_wache` ✅ · `gsc_abdeckung` ✅
(**111 Fälle**). **ROT = 0.**

### 7.4 Workflow- und Bestandsverträge

| Prüfer | Messung |
|---|---|
| `workflow_aufruf_vertrag` | ✅ 832 Aufrufe mit Schaltern in 103 Workflows, 0 Verstoß |
| `trigger_wache --check` | ✅ **105 Workflows, keine Befunde** |
| `workflow_js_wache --check` | ✅ alle `github-script`-Blöcke kompilieren |
| `skript_syntax_wache` | ✅ **736 Dateien grün** |
| `governance_contract --quick` | ✅ **alle 47 Regeln in beide Richtungen** |
| `konfliktmarker_wache` | ✅ keine Merge-Marker in 6703 Dateien |
| `hugo_build_vertrag` | ✅ |
| `casing_guard` | ✅ Exit 0 (Report: 1 Datei, 2 Fundstellen C12-guard — vorbestehend) |

### 7.5 Ableitungskette in der Reihenfolge aus Regel 8.7

| Schritt | Messung |
|---|---|
| `belegketten_wache --nur-hochrisiko --report` | ✅ Exit 0 |
| `editorial_review_gate --published --strict` | ✅ **92 Artikel · 4 Hochrisiko · 4 freigegeben · 0 blockiert** |
| `check_covers` | ✅ **145 Covers · 0 Probleme · 0 Stale · 0 Brand · 0 Text** |
| `check_titles` | ✅ **145 Titel · 0 Verstöße** |
| `ki_cover_herkunft --pruefen` | ✅ **145 Cover reproduziert, 2 außerhalb des Renderbereichs, 0 Befund(e)** |
| `faktenfrische_befund_akte --check` | ✅ folgt ihrer Quelle, **301 offene Befunde**, Stichtag 2026-11-23 |
| `abgeleitete_register --check` | ✅ aktuell (3 geprüft) |
| `ff_inhalts_wache` | ✅ **FF1–FF5: 0 Befund(e)** |
| `metadaten_wache` | ✅ 13 Proben inkl. M5 |
| `frontmatter_wache` | ✅ 175 Dateien, 0 Blocker, 0 Hinweise |
| `ymyl_siegel_wache` | ✅ **139 Artikel · 0 Befunde** |
| `lesbarkeit_diff_wache --basis origin/main` | ✅ keine neue Regression unter Flesch 60 |
| `f4_entscheidungsvorlage` + `--check` | ✅ **2750 Zeilen, bytgleich zu `main`** (Abschnitt 4.2) |

**ROT = 0** in allen drei Batterien (7.2 Build-Gates, 7.4 Verträge, 7.5 Kette).

### 7.6 Die Deckungs-Wache am geheilten Bestand

```
Workflow-Dateien im Bestand                     105
Beobachtet (Wacht-Liste)                         99
Begründet ausgenommen                             7
BLIND (kann auf main laufen, nicht gelistet)      0
Schein-Deckung (gelistet, kann nicht auf main)    0
Unbegründete Lücke                                0
Verwaiste Namen auf der Liste                     0
```

Zusatznachweise: PyYAML-Parser und Regex-Fallback liefern **dieselben 99
Namen** (Vertrag `test_beide_parser_gleich` am echten Bestand, nicht nur am
Test-Fixture) · keine Duplikate · `Fehler-Alerting` und der Herzschlag stehen
nicht auf der eigenen Liste · die zwei Alarm-Testmodule zusammen **64 Tests OK**
· ohne Token (`env -u GH_TOKEN -u GITHUB_TOKEN`) liefert der Herzschlag Exit 2
**und** den vollen Deckungs-Bericht.

---

## 8. Ehrlich offen

### 8.1 Die KI-Provenienz-Wache bleibt rot — und darf es

**Nicht geheilt, sondern meldbar gemacht.** Die 12 ungeklärten Register-Fälle
in `data/ki_kennzeichnung.yaml` sind eine **Entscheidung des Betreibers**, und
das Register sagt das selbst: „Diese Liste ist KEIN Befund, den ein Skript
entscheiden darf: Ob ein Mensch die redaktionelle Verantwortung übernommen hat,
weiß nur der Betreiber" (`ki_provenienz.ungeklaert()`), und: „Register und
Kennzeichnung erst nach belegter Entscheidung ändern; das bloße Löschen eines
Eintrags belegt keine KI-Herkunft oder Freigabe."

Ein Skript, das diese Liste leer macht, würde eine Rechtsbehauptung erfinden
(EU-KI-Verordnung Art. 50 Abs. 4). Deshalb: **kein Eingriff ins Register.**
Geheilt ist der Meldeweg (Abschnitt 3) — der nächste rote Lauf erzeugt jetzt
eine Meldung mit Name, Bereich, Run-Link und den roten Schritten.

**Entscheidungsvorlage für den Betreiber, Frist 2026-12-02.** Herkunft aus der
Commit-Historie über die GitHub-API geholt (der lokale Klon ist flach, 3
Commits, und kann sie nicht belegen). Alle 12 Artikel entstanden in **fünf
Automatik-Batches** unter dem Konto `frank-hartung`:

| Entstehungs-Commit | Datum | Artikel |
|---|---|---|
| `content: Kadenz-Lücken 17.08. + 19.08. geschlossen` | 2026-08-19 | girokonto-ohne-gebuehren · privathaftpflicht |
| `feat(seo): optimize articles for Google ranking, Pin…` | 2026-08-25 | internet-dsl-wechseln · sparen-im-herbst · wohngebaeudeversicherung · dsl-tarif-zuhause |
| `Fehlende Blogartikel ergänzt: 6 Premium-Ratgeber (Fr…)` | 2026-08-25 | haushaltsbuch · mietwagen-ohne-kaution · kfz-versicherung-vergleich |
| `fix(build): Qualitäts-Gate wiederherstellen – head.h…` | 2026-08-26 | handytarif-vergleichen · tagesgeld-zinsen |
| `fix(cadence): 2-3 LIVE an Mo/Mi/Fr dauerhaft garanti…` | 2026-09-03 | kreditkarte-vergleichen |

Commit-Zahlen je Artikel zwischen 47 und 101. Drei der fünf Batches tragen die
Sprache der Kadenz- und SEO-Automatik, einer sagt wörtlich „6 Premium-Ratgeber
ergänzt". Das Register vermerkt zu denselben Artikeln: „teils lauten die
Commits ‚optimize articles …', was auf KI-Agenten hindeutet. BITTE PRÜFEN."
**Die Belege sprechen für maschinelle Herkunft — entscheiden muss das der
Betreiber**, und zwar vor dem 02.12.2026. Diese Akte ändert deshalb weder das
Register noch ein `ai_generated`.

### 8.2 Weitere offene Punkte

* **Sicherheits-Wache, Job „Live-Messung"** — rot am 23.11. 09:58 auf `main`
  (Run 45151875836), Schritte 4 (Header F-01), 6 (Worker F-02/F-03/F-08), 7, 10.
  Das ist die Messung der **ausgelieferten** Seite, nicht des Repo-Standes; die
  Jobs `quellseite` und `abhaengigkeiten` sind grün. Nicht Teil dieses Auftrags,
  nicht in dieser Runde geheilt — aber seit Abschnitt 3 meldbar.
* **192 Modellwert-Stempel** im Bestand — die Zahl bleibt, der Injektor ist
  seit #1317 geheilt (`sprachkern._zaahlbehauptung` mit `_ist_rechtskontext`).
  Akute Treffer 0; die Stempel sind historische Artefakte.
* **Ausnahme ohne Workflow** — `Textverständnis-Patches einspielen (einmalig)`
  steht im Kopfblock, die Datei gibt es nicht mehr. Als Hinweis sichtbar
  gehalten, nicht still gelöscht: Sie belegt Entscheidungs-Geschichte.
* **Casing-Guard** meldet im Report-Modus 1 Datei, 2 Fundstellen
  (`2026-11-22-deine-naechtliche-grundlast-strom-…`, Regel C12-guard), Exit 0.
  Vorbestehend, nicht von dieser Runde berührt.

### 8.3 Was bewusst NICHT geändert wurde

Kein Gate wurde entschärft. Keine Schwelle, kein Siegel, kein Fail-closed
wurde angetastet:

| Fläche | Zustand |
|---|---|
| `ki_provenienz_gate.py` | unverändert — Eskalation bei ≤ 30 Tagen bleibt scharf |
| `data/ki_kennzeichnung.yaml` | unverändert — keine Register-Entscheidung erfunden |
| `automatic_write_protected()` | Entscheidung bitgleich, nur begründet |
| Flesch-Boden 60 / Score 75 | unverändert |
| `alert_resolve_gate.py` (Auto-Close nur mit Job-Beweis) | unverändert |
| Produktions-Scoping #343 | unverändert — es ist der Grund, warum PR-only-Läufe Ausnahmen sind |
| Titel-Grenzen `TITLE_MIN/MAX = 30, 60` | unverändert |

Dazu die Lehre aus Abschnitt 8.7 der Akte vom 22.11., die #1324 wörtlich
bestätigt hat: **Ableitungen zuletzt.** Reihenfolge dieser Runde —
Bestandswachen → `check_covers`/`check_titles` messen → `ki_cover_herkunft` →
`faktenfrische_befund_akte` → `abgeleitete_register` → `f4_entscheidungsvorlage`
**zuletzt** → `lesbarkeit_diff_wache` → Voll-Suite.

---

## 9. Delta dieser Runde

**8 Dateien, +1507/−19** — nach dem Rebase auf `5f12dcc` reine
Ingenieursarbeit: kein Content, keine abgeleiteten Ledger.

| Datei | +/- | Was |
|---|---|---|
| `.github/workflows/alert-on-failure.yml` | +60 | Wacht-Liste 68 → 99, 4 begründete Ausnahmen, Audit-Kommentar der Blindstelle |
| `.github/workflows/link-check.yml` | +19 | neuer Schritt „Inhalts-Wache FF1–FF5", fail-closed |
| `scripts/alerting_heartbeat.py` | +391/−9 | `workflow_bestand`, `bewusst_nicht_beobachtet`, `deckung_pruefen` (4 Klassen), `deckung_md`, `--deckung`, netzunabhängig in `main()`, Proben D1–D10 |
| `scripts/editorial_review_gate.py` | +113/−7 | `automatic_write_protected_grund`, `schutz_meldung`, Delegation, Proben W1–W14 |
| `scripts/check_titles.py` | +15/−3 | wahre Meldung statt Siegel-Behauptung |
| `scripts/tests/test_alerting_heartbeat.py` | +156 | Klasse `DeckungsWache`, 12 Tests |
| `GATES-DAUERHEILUNG-HIGHEND-2026-11-23.md` | +728 | diese Akte |
| `GATES-DAUERHEILUNG-HIGHEND-2026-11-22.md` | +25 | zwei Nachträge in §9.3 (beide offene Punkte erledigt) |

**Nicht im Delta, obwohl angefasst:**

* die vier Artikel und `data/gsc/abdeckung/verlinkungsheilung.json` — `main`
  heilte identisch (Abschnitt 4.3), Bestand gewinnt.
* `data/verlinkung_history.jsonl`, `data/gsc/abdeckung/verlinkungsauftrag.json`
  — bewusst auf den Bestand zurückgesetzt: doppelte Audit-Einträge für eine
  Heilung ohne Netto-Änderung, und die Auftrags-Datei schrieb ein eigener
  Messlauf (`--verlinkung`, trocken) neu. Ihre Veraltung stammt aus dem
  Bestand, nicht aus dieser Runde; der nächste Lauf der Abdeckung schreibt sie
  ohnehin. Wahrheit bleibt gemessen: **0 Paare**, Test `OK`.
* `.casing_report.json`, `data/casing_history.jsonl`,
  `data/editorial_review_history.jsonl`, `data/integrity_history.jsonl`,
  `data/schema_seo_history.jsonl` — reines Messrauschen der eigenen Läufe
  (Zeitstempel und Report-Zeilen), keine Entscheidung.
* `F4-ENTSCHEIDUNGSVORLAGE.md` — geschrieben und bytgleich zu `main`
  (Abschnitt 4.2), also kein Delta.
