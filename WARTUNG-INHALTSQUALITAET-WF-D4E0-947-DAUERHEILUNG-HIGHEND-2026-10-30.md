# 🏛️ WF-D4E0 (#947) – Forensische Kausalanalyse & Dauerheilung auf Agentur-Niveau

**Vorgang:** `WF-D4E0` · Issue **#947** (`🔧 Wartung · Inhaltsqualität · Vorgang WF-D4E0`)
**Workflow:** `.github/workflows/content-reserve.yml` (`Content-Reserve (täglicher Vorrat)`)
**Referenzlauf:** `40856100639` · Job `reserve` (`29.10.2026, 10:15:22Z`, `schedule`, Commit `76efccb4`)
**Datum der Dauerheilung:** `2026-10-30`
**Alarmbild:** `„Artefakt-Wächter (Maschinen-Artefakte strukturell heil)“ → „Stock shortage must not look successful“` – zwei rote Schritte, ein Ticket, und im Ticket nur eine Vorratsgeschichte.

---

## 1. Was der Lauf wirklich gemeldet hat (Beleg, nicht Erinnerung)

Der Meldetext des Alertings entsteht aus den **fehlgeschlagenen Schritten des Jobs**
(`alert-on-failure.yml`, `j.steps.map(...).join(' → ')`). Die Actions-API nennt für
Run `40856100639` genau zwei rote Schritte – der zweite ist nur die Folge des ersten:

| # | Schritt | Ergebnis |
|---|---|---|
| 21 | `Artefakt-Wächter (Maschinen-Artefakte strukturell heil)` | **failure** |
| 24 | `Stock shortage must not look successful` | **failure** |
| 16/17/19 | Stufe 1 / 2 / 4 | skipped (kein Bedarf im Lauf) |
| 18 | Stufe 3 – Reife durch Produktions-Gates beweisen | success |

Der Lauf war also **nicht** an einem leeren Vorrat gescheitert. Er war an einem
strukturellen Befund gescheitert, der in Parser-Sprache geliefert wurde:

```
🛑 ARTEFAKT-WÄCHTER: 1 Fund(e) in 515 Artefakten.
   [A6-FRONTMATTER] content/posts/2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt/index.md (-)
        Zeile 5: expected <block end>, but found '<scalar>'
```

Diese Zeile ist reproduzierbar: Der Baum des Lauf-Commits `76efccb4` wurde aus
GitHub geladen (Tarball) und der Wächter darauf gestartet – **1 Fund, genau diese
Datei**. Auf `main` von heute ist der Befund weg; er wurde am 29.10. um `10:41Z`
von #942 geheilt. Was blieb, war die **Klasse** – und die Blindstelle, die sie
eine Nacht lang in ein Vorratsproblem verwandelte.

---

## 2. Forensische Chronologie der Zeile

Kein „Naturereignis“, sondern eine belegbare Kette (Git-Historie der Datei,
Abfrage der Actions-API):

| Zeit (UTC) | Commit / Lauf | Was passiert |
|---|---|---|
| 27.10. 17:44 | `47fee362` | Zeile steht **korrekt**: `… Klasse „heilbar“ ist heilbar …` |
| 29.10. 10:11:41 | `3d050ea1` (#941, WF-D0C9 „Phase 1: Erste 9 Artikel bearbeitet“) | Frontmatter von **neun Live-Artikeln** neu getippt – dabei wird aus `„heilbar“` ein `„heilbar"` (**ASCII**) |
| 29.10. 10:11:47 | `76efccb4` | Scorecard-Commit, Reserve-Lauf checkt **diesen** Stand aus |
| 29.10. 10:15:22 | Run `40856100639` | Artefakt-Wächter A6 rot, End-Gate rot (3/6, Klasse `kette`) |
| 29.10. 10:24:56 | `649063b9` (#934, WF-D4E0 #884) | Die R5-/Vorheilungs-Heilung merged – **nach** dem Laufstart; der Lauf fuhr also noch den alten Kettencode |
| 29.10. 10:41:27 | `d396dd3e` (#942) | `frontmatter_wache.py` entsteht, die Zeile wird geheilt |
| 30.10. 10:16:56 | Run `41039588923` | Reserve-Lauf **grün**, `6/6`, Klasse `ok`, keine Blocker |

**Die Ursache in einem Satz:** Ein deutsches Schlusszeichen als ASCII-Zeichen
(`„heilbar"` statt `„heilbar“`) beendet einen YAML-Doppelpunkt-Wert beim ersten
`"`. Alles danach ist Text, der YAML-Parser bricht ab – und Hugo baut die Seite
nicht. Es wurde **nichts erfunden**: Die Heilung ersetzt genau dieses eine Zeichen.

---

## 3. Warum der Befund eine Nacht gekostet hat (und das Ticket in die Irre führte)

Drei Dinge griffen ineinander:

1. **Der Artefakt-Wächter durfte nicht heilen.** Seine Doktrin („A6 wird NICHT
   geheilt: Inhalt zu rekonstruieren hieße, Inhalt zu erfinden“, #653) ist
   richtig – sie passt nur nicht auf eine Klasse, die beweisbar **zitiert**
   statt rekonstruiert. Also blieb der Schritt rot.
2. **Die Meldung war Parser-Sprache.** `Zeile 5: expected <block end>` nennt
   weder Datei-Kontext, Spalte, Ursache noch Befehl – und der Fehlercode kam aus
   PyYAML, nicht aus der Hauswache.
3. **Niemand im Vorratslauf besaß die Klasse.** `frontmatter_wache.py` (die SSOT
   für genau diesen Befund) wurde am 29.10. um 10:41 gebaut – aber in
   `content-reserve.yml` nie aufgerufen. Der Vorratslauf erbte den Befund
   stattdessen am Ende, im Artefakt-Schritt, und verbuchte ihn als Vorrat.

Die zweite rote Stelle (3/6) war **nicht** dieselbe Ursache: Der Lauf fuhr den
Stand `76efccb4`, also vor der #884-Heilung. Beleg: Die Chronik
(`data/reserve-history.jsonl`) zeigt für `40856100639` `klasse: kette` – und der
nächste Lauf am 30.10. (`41039588923`) steht mit `6/6`, `klasse: ok`, `blocker: []`.

---

## 4. Dauerheilung: die Klasse schließen, nicht den Vorfall

### 4.1 Neues Gate `scripts/reserve_frontmatter_gate.py`

Ein Gate, das **keine zweite Wahrheit** baut:

| Zusage | Mechanismus |
|---|---|
| **Keine zweite Wahrheit** | Es parst kein Frontmatter. Befunde und Heilung kommen aus `frontmatter_wache.py` (SSOT, #942). Ist die SSOT nicht importierbar → **Exit 2** (fail-closed), nie „grün aus Unwissen“. |
| **Besitz statt Reichweite** | Geheilt wird nur Reserve-Eigentum (`reserve: true` / `reserve_blocked:`) – die Besitzregel wird aus `reserve_stage_guard.is_reserve_owned` **importiert**, nicht kopiert. Live-Content gehört der Engine-/Deploy-Kette und wird nie still verändert. |
| **Beweis statt Vertrauen** | Geschrieben wird nur, wenn **B1** die Wache den Fund als heilbar führt *und* einen Beleg liefert, **B2** der Artikeltext **bytegleich** bleibt, **B3** kein neuer Blocker entsteht, **B4** mindestens einer verschwindet. Sonst bleiben die Originalbytes stehen (`⊘ HEILUNG VERWORFEN` mit Grund). |
| **Ehrliche Diagnose** | Offene Befunde werden mit `Datei:Zeile:Spalte`, Regel, Ursache und **Reparaturbefehl** genannt – getrennt in „Reserve-Eigentum“ und „Live-Bestand“. |
| **Kein Schreib-Nebeneffekt** | Der Prüfaufruf (ohne `--fix`) schreibt nie (C15); die Heilung ist idempotent (beides im Selbsttest bewiesen). |

### 4.2 Verdrahtung im nächtlichen Lauf

Neuer Schritt **„Frontmatter-Gate (eine Content-Zeile darf den Vorrat nicht töten)“**
direkt **vor RUNDE 0** – also bevor Zertifizierung und Artefakt-Wächter auf den
Bestand sehen:

* `--selftest` → `--fix` (nur wenn der Wachen-Selbsttest grün ist) → `--md` in die
  Job-Summary, Log als Artefakt (`frontmatter-gate.log`, 21 Tage).
* **Nicht** `continue-on-error` (ein offener Blocker ist ein Befund), aber
  **nicht blockierend**: keine folgende Stufe hängt an `steps.frontmatter`, damit
  der Vorrat weiterarbeitet und der Befund nicht wieder als Engpass endet.

### 4.3 Registrierung und Beweise

* `governance_contract.GUARDS` → `reserve_frontmatter_gate.py` (mit Begründung):
  Der Selbsttest läuft damit im vertraglichen Minimum **jedes** Gates
  (`selftest_runner` entdeckt ihn, inklusive Uhr-Proben + C15).
* `package.json`: `reserve:frontmatter`, `reserve:frontmatter:fix`,
  `test:reserve:frontmatter`.
* `scripts/tests/test_reserve_frontmatter_gate.py`: 16 Regressionen
  (Vorfallbytes, Besitz-Grenze, B1–B4, Fail-closed, Idempotenz, CLI-Vertrag).

### 4.4 Beweisführung am echten Vorfall

Der Baum des roten Laufs (`76efccb4`) wurde erneut gemessen – **derselbe Befund,
nun in der Sprache, die man handeln kann**:

```
🛑 Frontmatter-Gate: 136 Dateien | geheilt: 0 | offen: 2 (0 Reserve, 2 fremd)
   ✗ OFFEN (Live-Bestand – gehört der Engine-/Deploy-Kette, wird NICHT angefasst):
     [F3] content/posts/2026-10-12-dein-weg-…/index.md:7:82 – Text hinter dem
     schließenden Anführungszeichen von `reserve_reaktiviert` … Heilung: das
     schließende Zitat als „ “ schreiben (`--fix`).
        python3 scripts/frontmatter_wache.py --fix --pfad content/posts/2026-10-12-…/index.md
```
`md5sum` der Datei vor und nach `--fix`: **identisch** – fremder Besitz bleibt
unangetastet. Im Reserve-Eigentum (Entwurf mit `reserve: true`) heilt derselbe
Befehl verlustfrei und belegt den Artikeltext als bytegleich (Selbsttest +
Wirkungsprobe).

---

## 5. Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/reserve_frontmatter_gate.py` | **neu** – Gate mit SSOT-Delegation, Besitz-Grenze, Beweisen B1–B4, `--check/--fix/--json/--md/--kurzbefund`, `--selftest` (7 Sabotage-Proben), `--wirkungsprobe` (#947-Bytes) |
| `scripts/tests/test_reserve_frontmatter_gate.py` | **neu** – 16 Regressionen inkl. Live-Content-Unberührbarkeit und Beweis-Verwurf |
| `.github/workflows/content-reserve.yml` | neuer Schritt + Kopf-Dokumentation der Kausalkette + `frontmatter-gate.log` im Nachweis-Artefakt |
| `scripts/governance_contract.py` | `GUARDS`-Eintrag (Selbsttest im vertraglichen Minimum, C6) |
| `package.json` | drei npm-Aliasse für Prüfung/Heilung/Test |

**Bewusst nicht angefasst:** `scripts/artefakt_waechter.py` (gesperrte Kerndatei)
und `data/integrity_lock.json`. Der Befund gehört jetzt an die Stelle, die ihn
heilen kann; der Wächter bleibt das strukturelle Netz am Ende der Kette und
seine A6-Regel unverändert scharf.

---

## 6. Verifikation

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Neue Regressionen | `python3 -m unittest scripts.tests.test_reserve_frontmatter_gate` | ✅ **17 Tests OK** |
| Nachbar-Suiten (Artefakt, Frontmatter, Reserve-Kette) | `… test_artefakt_waechter test_frontmatter_wache test_reserve_pipeline` | ✅ **214 Tests OK** |
| Gate-Selbsttest / Wirkungsprobe | `reserve_frontmatter_gate.py --selftest` / `--wirkungsprobe` | ✅ grün (Erkennung, Lesemodus schreibfrei, Besitz-Grenze, B1/B2, Fail-closed, Idempotenz) |
| Gate auf dem echten Bestand | `reserve_frontmatter_gate.py` | ✅ **139 Dateien, 0 Blocker** |
| Gate auf dem roten Lauf-Baum `76efccb4` | `reserve_frontmatter_gate.py --root <tarball>` | 🛑 **1 Datei, 2 Befunde, 0 Heilungen, Bytes unverändert** (Live-Besitz) – exakt der Befund des Laufs |
| Frontmatter-Wache (SSOT) | `frontmatter_wache.py` | ✅ 139 Dateien · 0 Blocker · 0 Hinweise (YAML-Parser) |
| Alle Wachen-Selbsttests (der CI-Schritt) | `python3 scripts/selftest_runner.py` | ✅ **251 Wachen · 502 Uhr-Proben** (+97/+1461 Tage) · 222 s · grün |
| Artefakt-Wächter | `artefakt_waechter.py` | ✅ 521 Artefakte strukturell heil |
| Governance-Vertrag | `governance_contract.py` | ✅ **42/42 Regeln** (beide Richtungen) |
| Integritäts-Siegel | `integrity_guard.py --gate` | ✅ 50 Kerndateien, HEAD `6d5ddd0` (kein Kern angefasst) |
| Workflow-Audit | `automation_premium_audit.py --strict` | ✅ rc 0 |
| Manifest-Wache | `manifest_guard.py` | ✅ grün (13 Dateien) |
| github-script-Blöcke | `workflow_js_wache.py --check` | ✅ alle Blöcke kompilieren |
| YAML des Workflows | `yaml.safe_load(content-reserve.yml)` | ✅ 27 Schritte, `id: frontmatter` genau einmal |
| Vollsuite | `python3 -m unittest discover -s scripts/tests` | **4.530 Tests, 13 Fehlschläge – alle 13 vorbestehend**: dieselben 13 Tests scheitern im unveränderten `main`-Baum (`6d5ddd0`) identisch (Baseline-Gegenprobe im separaten Worktree). **0 durch diese Heilung verursacht.** |

---

## 7. Was strukturell verhindert ist

* Ein **heilbarer** Frontmatter-Defekt im eigenen Vorrat kann keine Nacht mehr
  töten: Er wird geheilt, belegt (`Beleg: …`) und im Log geführt – der Artikeltext
  bytegleich.
* Eine Heilung, die **Prosa** verändert, ist unerzeugbar: B2 vergleicht den
  Artikeltext vor dem Schreiben; bei Abweichung bleiben die Originalbytes stehen.
* Ein **fremder** (Live-)Defekt wird nie mehr als Vorratsproblem erzählt: Datei,
  Zeile, Spalte, Regel, Ursache und Reparaturbefehl stehen im Log und in der
  Job-Summary; das Ticket beginnt künftig beim Namen der Ursache
  („Frontmatter-Gate → Artefakt-Wächter → Stock shortage“) statt beim Symptom.
* **Unwissen ist kein Grün**: Fehlt die SSOT, endet das Gate mit Exit 2 – es kann
  sich nicht stillschweigend für heil erklären (#661-Lehre).
* Das Gate ist im **vertraglichen Minimum** (`GUARDS`): Sein Selbsttest läuft in
  jedem Qualitäts-Gate, mit vorgestellter Uhr und Schreibfreiheits-Prüfung (C15).

---

## 8. Ehrliche Grenzen und Baseline-Befunde (nicht Teil dieser Heilung)

* **Keine neue Zertifizierung lokal:** Im Arbeits-Container fehlen `hugo` und
  `hunspell` (Download nur aus dem gesperrten Release-Host). Der Beweis, dass die
  Nacht wieder `6/6` liefert, liegt aber vor – **produktiv**: Run `41039588923`
  (30.10.) ist grün mit `6/6`, `klasse: ok`, `blocker: []`.
* **Baseline 1 (fremd, offen):** `Deploy auf GitHub Pages` auf `main`
  (`6d5ddd09`, Run `41042461051`) ist rot am Schritt „Weiterleitungen –
  Selbsttest, Quelle und Unit-Tests (fail-closed)“ sowie am Auslieferungs-Siegel.
  Dasselbe Bild zeigt die Vollsuite: `test_weiterleitungen` scheitert dreimal
  (`QuelleBestand`, `Snapshot`) – auch im unveränderten `main`-Baum. Das ist eine
  andere Klasse (Redirects/Siegel), nicht Frontmatter; sie wird hier **nicht**
  mitrepariert und gehört in einen eigenen Vorgang. Die übrigen vorbestehenden
  Fehlschläge der Vollsuite (Affiliate-Intent, LCP-Manifest, Social-Winkel für
  LinkedIn/Telegram, Inhalts-Register, Versicherungs-Pillar) sind aus demselben
  Grund nicht Teil dieser Heilung.
* **Baseline 2 (bereits upstream geheilt):** Bei der Verifikation fielen zwei
  Altlasten aus dem Merge von #955 auf (doppelter npm-Schlüssel
  `test:faktenfrische`, zweimal `const workerZugangFailed` → das zentrale
  Fehler-Alerting kompilierte nicht). Beide waren auf meinem Basisstand
  (`414629d`) vorhanden und sind upstream mit `dec5e0a7` (#956) behoben – nach dem
  Rebase auf `6d5ddd0` sind `manifest_guard.py` und `workflow_js_wache.py --check`
  grün. Hier wurde nichts doppelt „geheilt“.
* **Baseline 3 (fremd, offen):** Die `Playwright-Suite (Desktop + Mobile)`
  (`e2e.yml`) scheitert am Schritt „E2E-Suite ausführen“ – auf `main` bereits am
  28.10. und 29.10. (`f56e25c7`, `d5382e73`), also **vor** diesem PR und
  unabhängig von ihm (er berührt weder `layouts/`, `assets/`, `static/` noch
  `content/`). Das Qualitäts-Gate (Build + interne Links) ist mit dieser Änderung
  grün. Auch dieser Befund gehört in einen eigenen Vorgang.
* **Umgebungsabhängiger Einzelbefund:** `cover_render_check.py --selftest` braucht
  `pillow`; in diesem Container fehlte es (CI installiert es aus
  `requirements-ci.txt`). Nach `pip install pillow` grün – kein Code-Befund.

---

## 9. Erwarteter Lauf nach dieser Heilung

1. **Schritt 21 (Artefakt-Wächter)** sieht ein Frontmatter, das vorher schon
   geprüft und – soweit es dem Vorrat gehört – geheilt wurde. A6 kann nur noch
   feuern, wenn ein Fremd- oder ein nicht beweisbar heilbarer Befund übrig ist.
2. **Bei einem Live-Defekt** nennt das Ticket zuerst das Frontmatter-Gate, mit
   Datei, Zeile und Befehl; der End-Gate berichtet den Vorrat weiterhin ehrlich
   (Klasse `kette`/`engpass`), aber niemand liest mehr „Stock shortage“ über
   einem Build-Befund.
3. **Bei einem Pool-Defekt** heilt der Lauf selbst, schreibt die Bytes in den
   Reserve-Commit (Staging-Politik unverändert) und belegt die Heilung im Log.
4. **Kein stiller Schwund:** Der Prüfaufruf bleibt schreibfrei; jede Heilung ist
   idempotent und bytegenau nachweisbar.
