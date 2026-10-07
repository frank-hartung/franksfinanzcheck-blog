# Wartung · Inhaltsqualität · Vorgang WF-1F8C (#608) — Dauerheilung auf Premium-Niveau

**Datum:** 07.10.2026 · **Issue:** #608 · **Workflow:** `Kadenz-Endkontrolle (Mo/Mi/Fr – 2–3 LIVE erzwingen)`
**Reparatur-Vorschlag:** PR #616 („Closes #608“) · **Vorgänger-Vorgänge:** #602 (Melde-Routing), #601 (Tagesdefizit 05.10.), #603 (Slot-Wache)

## Kurzfassung

#608 war **kein** API-Key-Problem, kein GitHub-Ausfall und kein transienter
Fehler – das Runbook der Meldung führte in die Irre. Der Befund hinter dem
Befund:

> Die Tagesquote ist ein **Zustand**. Ihr Fachkanal `engine-deficit` wurde aber
> wie ein **Arbeitsauftrag** behandelt: Ein Reparatur-Merge schloss ihn, ein
> Ruhetag übersprang ihn – und als die Kadenz-Endkontrolle danach ehrlich rot
> meldete, gab es für das zentrale Fehler-Alerting keinen offenen, frischen
> Fachkanal mehr. Es musste fail-open melden und legte das generische
> Wartungs-Issue #608 an.

Die Dauerheilung gibt dem Kanal seinen rechtmäßigen Besitzer: **die Messung
selbst** (`scripts/engine_issue.py`).

1. **Kadenz: jeder Tag.** Gemessen wird immer der jüngste Publikationstag
   (`cadence_guard.letzter_publikationstag`, eine Kalenderquelle für alle
   Melder) – an Ruhetagen wie an Publikationstagen. Die Produktions-Wache
   belegt den Kanal zusätzlich täglich um 20:00 UTC.
2. **Schließpfad: nur die eigene Messung** – in zwei ehrlichen Fällen: Ziel am
   Tag selbst noch erreicht, oder der Fehltag ist vorbei (nicht nachholbar,
   weil Inhalte nie nachträglich datiert werden) und ein folgender
   Publikationstag erreicht das Ziel nachweislich. Der Schließvermerk sagt
   das ausdrücklich.
3. **Reopen: Wer den Kanal rot schließt, findet ihn offen.** Merge, Hand oder
   Missverständnis – die nächste Messung öffnet ihn wieder, mit Begründung.
   Danach schließt er sich von selbst: kein Dauerläufer.
4. **Ein Vertrag hält es fest:** Regel **C23** in `governance_contract.py`
   friert Besitz, Kalender-SSOT, Ruhetag-Messung, Reopen und die
   Marker-Identität ein; der Kontrakt-Selbsttest wird rot, wenn eines davon
   still zurückgebaut wird.

---

## Befund

### Die Beweiskette des Vorfalls (alle Zeiten UTC)

Die Kadenz feuert Mo/Mi/Fr um 10:35/16:35/19:35/21:35 UTC
(`kadenz-endkontrolle.yml`). Am Montag, dem 05.10., kam davon nur ein Teil an –
GitHub-Schedules laufen bei Last spät, nie früh, und einzelne Slots fallen
ersatzlos weg. Zwei Schedule-Runs sind überliefert; ihre Zuordnung ergibt sich
aus dem Versatz zum Raster (+2 h 47 bzw. +3 h 20), nicht aus einem
Slot-Namen im Beleg (GitHub liefert den Cron-Slot nicht mit):

| Run (UTC) | Versatz zum Raster | Wirkung |
|---|---|---|
| 05.10. 19:22:22 | +2 h 47 (Raster 16:35) | Backstop rettet genau EINEN Artikel („Preiswert surfen … DSL‑Anschluss“, `date: 19:22:11Z`) → **1/2 LIVE** · Lauf 37362926801 |
| 05.10. 21:21:50 | `workflow_dispatch`, abgebrochen | kein Beleg über diesen Lauf · Lauf 37375385214 |
| 06.10. 00:55:57 | +3 h 20 (Raster 21:35) | läuft in den Dienstag hinein · Lauf 37396558364 |

Für die Slots **10:35 und 19:35 des Montags existiert kein Run** – sie wurden
ersatzlos ausgelassen. Genau dafür ist die Slot-Wache aus #601 da; am 05.10.
war sie noch nicht in Kraft (Merge erst 21:21).

| Zeit | Ereignis | Beleg |
|---|---|---|
| 05.10. 19:23:46 | `engine_issue.py --deficit` eröffnet **#601** („Content-Engine: Tagesdefizit 2026-10-05 (1/2 LIVE)“, LIVE-Slug dsl-anschluss) – korrekt | Issue #601 |
| 05.10. 21:21:16 | PR **#603** („Slot-Wache“) wird gemergt. Sein Body beginnt mit **„Closes #601“** – ein Reparatur-Vorschlag, der die Ursache behebt (verpasste Slots werden nachgeholt) | PR #603 · Merge-Commit `2c33fccf` |
| 05.10. 21:21:18 | GitHub schließt **#601** – **obwohl der gemessene Tag rot blieb** (05.10. = 1/2; der 19:35-Slot war ausgefallen, der 21:35-Slot stand noch aus) | Timeline #601 |
| 05.10. 21:26:32 | Der Vorgangs-Abschluss setzt den Vermerk „✅ Erledigt und nachgeprüft. Behoben mit #603.“ | Kommentar #601 |
| 06.10. 00:55:57 | Der nachgelieferte **21:35-Slot** startet – jetzt ist Dienstag, ein **Ruhetag** | Lauf 37396558364 (`schedule`) |
| 06.10. 00:56 | `engine_issue.py --deficit` tut **nichts**: `today.weekday() not in PUBLICATION_DAYS` → „Kein Publikationstag – Defizit-Wache übersprungen.“ (Exit 0) | `b89c717`-Fassung von `engine_issue.py` |
| 06.10. 00:56 | `publication_check.py` misst dagegen den **letzten Publikationstag** (05.10.) → `check_rc=1`, während `publication_release.py` `class=ok` liefert. Genau diese Kombination feuert den roten Schritt „TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig“ | Job 112053833949 · Bedingung `class == 'ok' && check_rc != '0'` |
| 06.10. 00:56 | Das zentrale Fehler-Alerting sucht einen **offenen, für diesen Lauf frischen** `engine-deficit`-Fachkanal. Es gibt keinen: #601 ist geschlossen, und an Ruhetagen wurde er nie belegt → **fail-open** | Lauf 37396603733 |
| 06.10. 00:56:36 | Es legt **#608** an – „Häufigste Ursachen: API-Key abgelaufen / GitHub-Ausfall / transienter Fehler“. Ein Runbook für Zustände, die es nicht gibt | Issue #608 |
| 06.10. 14:15:09 | Ein weiterer Kadenz-Dispatch-Lauf scheitert genauso. Das Alerting läuft um 14:20:41 und legt **kein** zweites Issue an – die Kette endet, weil #608 (dieselbe Identität) noch offen ist: Ein Meldungs-Issue wird zum Dauerkanal für einen Zustand, den es nicht kennt (kein Kommentar bis heute) | Lauf 37477392829 · Alerting-Lauf 37478159347 · #608 `updatedAt == createdAt` |
| 07.10. 10:58 | Der Betrieb erholt sich, die Vergangenheit bleibt: **07.10. = 2/2 LIVE** (`erfuellt`), **05.10. = 1/2** und damit `verbucht`. #601 bleibt geschlossen – ein vergangener Fehltag wird nicht nachträglich wieder aufgemacht. | `engine_issue.py --lage` |

**Der 05.10. wurde nie nachgeholt.** Er konnte es auch nicht: Nachtragen von
Inhalten ist ausdrücklich verboten (`publication_check.main`: „never backdate
content“). Genau deshalb ist die Quote ein *Zustand* und kein Auftrag.

### Die drei Ursachen – in der Reihenfolge ihrer Wirkung

**U1 — Der Kanal gehörte dem falschen Besitzer.** Die Quote ist ein Messwert.
Ein Messwert endet nicht mit einem Merge; er endet mit einer neuen Messung.
„Closes #601“ war für einen Reparatur-Vorschlag die *technisch* richtige
Syntax und die *fachlich* falsche Handlung: #603 hat die Ursache
(verpasste Slots) behoben, aber den Zustand nicht – und mit dem Schließen
verschwand die Existenzberechtigung des Fachkanals.

**U2 — An Ruhetagen existierte der Kanal nicht.** `engine_issue.py` kehrte bei
`today.weekday() not in PUBLICATION_DAYS` vorzeitig zurück („Kein
Publikationstag – Defizit-Wache übersprungen“). Damit gab es an Di/Do/Sa/So
keinen Ort für „der letzte Publikationstag liegt unter dem Ziel“ – obwohl ein
verspäteter Slot genau dann (00:55 Uhr!) darüber berichtet. Die
Dedupe-Regel aus #602 verlangt einen *frischen, offenen* Kanal; an Ruhetagen
war das **konstruktiv unmöglich**. Der Fehlalarm war also nicht Pech, sondern
programmiert.

**U3 — Drei Werkzeuge maßen drei verschiedene Tage.** `engine_issue.py` nahm
`date.today()` (und übersprang den Dienstag), `publication_check.py` maß den
letzten Publikationstag (05.10.), die Produktions-Wache baute sich denselben
Tag in einer eigenen Schleife nach. Der Alarm sprach über den 05.10., der
Melder über den 06.10. Wo keine gemeinsame Wahrheit ist, entsteht ein
Zwischenraum – und in ihm stand #608.

---

## Umsetzung

### 1. Der Kanal gehört der Messung (`scripts/engine_issue.py`)

Der Melder ist jetzt eine kleine, prüfbare Zustandsmaschine. Die Messung ist
rein (`quoten_lage(heute, posts, minimum)` → `offen` · `verbucht` ·
`erfuellt`), die Entscheidung ebenfalls (`urteil(lage, offen, geschlossen)` →
`nichts` · `oeffnen` · `kommentieren` · `wieder_oeffnen` · `schliessen`), und
erst ganz außen stehen die `gh`-Aufrufe (im Selbsttest durch Stubs ersetzt).

| Zustand | Bedeutung | Handlung |
|---|---|---|
| `offen` | Publikationstag läuft, Ziel noch nicht erreicht | Kanal offen halten und **belegen** (Kommentar = Frischebeweis für das Alerting) |
| `verbucht` | Tag vorbei, nicht nachholbar | Kanal **offen halten** und belegen; Titel nennt „– nicht nachholbar“ |
| `erfuellt` | Ziel erreicht | Kanal **schließen** – mit dem Vermerk, ob der Fehltag nachgeholt wurde (er wurde es nie) |

Dazu:

* **Wiederöffnen:** Ist der gemessene Tag rot und der Kanal geschlossen (und
  gehört er zu ebendiesem Tag), öffnet die Messung ihn wieder – mit
  Begründung im Kommentar und korrigiertem Titel. Gehört der geschlossene
  Kanal zu einem **älteren** Tag, entsteht ein **neuer** Kanal: Die
  Vergangenheit bleibt als eigener Vorgang ablesbar.
* **Altauflage erkannt:** `tag_aus_body()` liest den Tag bevorzugt aus dem
  neuen Marker und sonst aus der alten Zeile `- **Tag:** …`. Ohne diesen Pfad
  wäre aus #601 (Vorgängerversion) beim Wiederöffnen ein zweiter Kanal
  geworden.
* **Ehrliche Diagnose:** Der Body trägt eine Tabelle der letzten drei
  Publikationstage. Ein verbuchter Fehltag verschwindet damit nicht aus dem
  Alarm, nur weil ein neuerer Tag gemessen wird.
* **Fail-loud statt still:** Kann der Kanal nicht belegt werden (Rechte,
  `gh`-Ausfall), endet der Aufruf mit Exit 2 und einer `::warning::`-Zeile.
  Genau dann greift die Fail-open-Regel des Alertings – und das soll man
  sehen, nicht raten.
* **`--lage`** zeigt den Zustand ohne Schreibzugriff (kein Token nötig).

### 2. Eine Kalenderquelle (`cadence_guard.letzter_publikationstag`)

`letzter_publikationstag(heute)` und `publikationstage_zurueck(heute, n)`
stehen jetzt in der Kadenz-SSOT; `publication_check.expected_day()` delegiert
dorthin (Name bleibt, Aufrufer bleiben stabil). Die Produktions-Wache maß
ihren Tag schon immer selbst – der Vertrag **C23** verlangt jetzt, dass
Defizit-Wache und Auslieferungs-SLO die SSOT benutzen.

### 3. Täglicher Beleg (`produktions-wache.yml`)

Die Produktions-Wache (täglicher Takt, **20:00 UTC** = 22:00 MESZ, nach dem
letzten Engine-Slot; `issues: write`) ruft den Kanal **vor** ihrem eigenen
Alarm-Schritt auf und nur außerhalb der `WARTEND`-Frist (die gilt für
Engine-Läufe vor 18:30 UTC, wenn die Fallback-Slots 14:10/17:40 noch laufen).
Damit gibt es an jedem Kalendertag einen Beleg, unabhängig davon, ob ein
Kadenz-Slot ankommt. Die Kadenz-Endkontrolle
belegt ihn weiterhin in ihrem Reconcile-Schritt (jetzt ausdrücklich **vor**
der Quotenmessung – das Alerting liest nach dem Lauf).

### 4. Vertrag C23 (`governance_contract.py`)

Neue Regel **„Zustandskanal (Besitz, Kadenz, Schließpfad)“** mit
Kunstbefund-Proben im Kontrakt-Selbsttest:

| Probe | Wird rot, wenn … |
|---|---|
| Ruhetag-Sprung wieder eingebaut | `engine_issue.py` an Ruhetagen vorzeitig zurückkehrt |
| zweiter Kalender | der Melder `cg.letzter_publikationstag(` nicht mehr benutzt |
| Wiederöffnen entfernt | `gh("issue", "reopen"` fehlt |
| Tagesbeleg entfernt | `produktions-wache.yml` den Aufruf verliert |
| Marker/Label verändert | die Fachkanal-Dedupe des Alertings erblindet (#602) |
| Kalender-SSOT entfernt | `cadence_guard` die Funktion verliert |
| Schließpfad verwässert | mehr als ein `gh("issue", "close"` auftaucht oder der Vermerk die Nicht-Nachholbarkeit verschweigt |

`engine_issue.py` steht zusätzlich in `GUARDS`, sein `--selftest` läuft damit
in C6 („eine Wache, die niemand verlangt, führt irgendwann niemand mehr aus“).

### 5. Tests und Verhaltens-Simulation

* `scripts/tests/test_engine_issue.py` (**neu**, 39 Tests): Messung an jedem
  Wochentag, Entscheidungen, Wortlaut, `tag_aus_body` (inkl. Altauflage),
  `abgleichen()` mit gestubbtem GitHub (öffnen/belegen/reopen/schließen/still),
  Werkzeugfehler wird laut, Workflow-Verträge, Kalender-SSOT.
* `scripts/tests/sim/alert_scoping_sim.mjs`: zwei neue Szenarien – **#608**
  (Ruhetag-Lauf, frisch wiedereröffneter Fachkanal → **kein** Duplikat) und
  die Gegenprobe (Fachkanal blieb geschlossen → generischer Alarm
  **fail-open**, korrekt).
* `scripts/cadence_guard.py --selftest`: Kalender-SSOT für alle sieben
  Wochentage, deterministisch (keine Wanduhr).

### 6. Dokumentation

`CLAUDE.md` (Dauervorgabe), `docs/ANLEITUNG-ENGINE-KAPAZITAET.md` (neuer
Abschnitt „Wenn der Tag unter dem Mindestziel bleibt“ mit Besitzer/Kadenz/
Schließpfad-Tabelle), `docs/QUALITAETS-REGELWERK.md` (Selbstheilungs-Matrix +
Dauervorgaben), `package.json` (`npm run engine:deficit`,
`npm run test:engine:deficit`).

---

## Nachweis

### Der Vorfall, nachgestellt (ohne Netz, ohne Wanduhr)

`python3 scripts/engine_issue.py --selftest` stellt den 05./06.10. mit
Fixtures nach: Montag 19:23 → `offen`; **Dienstag 00:55 → `verbucht` mit
gemessenem Tag 05.10.**; geschlossener Kanal mit passendem Tag →
`wieder_oeffnen`; geschlossener Kanal zu einem älteren Tag → `oeffnen`;
Ziel erreicht → `schließen` (mit dem Vermerk „nicht nachgeholt“); ruhiger
Zustand → **kein** Schreibzugriff.

### Die Beweisläufe

| Lauf | Ergebnis |
|---|---|
| `python3 scripts/engine_issue.py --selftest` | **bestanden** – der 05./06.10. ist als Fixture nachgestellt (siehe unten) |
| `python3 scripts/engine_issue.py --lage` | `tag: 2026-10-07`, `n: 2`, `ziel: 2`, `zustand: erfuellt` – der heutige Tag ist im Ziel |
| `python3 -m unittest discover -s scripts/tests` | **Ran 1929 tests · OK (skipped=23)** – darin die **39 neuen** Tests aus `test_engine_issue.py` |
| `node scripts/tests/sim/alert_scoping_sim.mjs` | **16/16 Szenarien korrekt** (inkl. #608 und Gegenprobe) |
| `python3 scripts/governance_contract.py --selftest` | **bestanden (C1–C23** mit Kunstbefunden: Fehler erkannt, gutes Setup bleibt still) |
| `python3 scripts/governance_contract.py` (voll) | „🔒 GOVERNANCE-VERTRAG erfüllt – alle 23 Regeln prüfen in beide Richtungen“ |
| `python3 scripts/cadence_guard.py --selftest` | bestanden (inkl. Kalender-SSOT) |
| `python3 scripts/automation_premium_audit.py --strict` | Exit 0 – 79 Workflows, 60 geplant, 0 Jobs ohne Timeout, 0 ohne Permissions |
| `python3 scripts/integrity_guard.py --gate` | „✅ Integritäts-Gate grün: 45 Kerndateien entsprechen exakt dem signierten Stand“ – der Vorgang hat keine versiegelte Kerndatei berührt |

### Selbstsabotage-Proben (Test wird rot, wenn die Heilung fällt)

| Sabotage | Ergebnis |
|---|---|
| Ruhetag-Kurzschluss wieder eingebaut | Kontrakt-Selbsttest **C23** rot („überspringt Ruhetage wieder“) |
| Melder misst `heute` statt `letzter_publikationstag` | **C23** rot („ein zweiter Kalender im Melder“) |
| Wiederöffnen-Pfad entfernt | **C23** rot („kennt kein Wiederöffnen“) + `test_rot_geschlossen_wird_wieder_geoeffnet` rot |
| Tagesbeleg aus `produktions-wache.yml` gestrichen | **C23** rot („an Ruhetagen bliebe er unbesetzt“) |
| Marker `<!-- engine-deficit-id: tagesdefizit -->` verändert | **C23** rot (Dedupe aus #602 würde blind) |
| `cadence_guard.letzter_publikationstag` entfernt | **C23** rot (Kalender-SSOT fehlt) |
| `abgleichen()` schließt einen roten Tag | `test_erfuellter_tag_schliesst_den_kanal` (Verhalten) rot |
| Schließvermerk ohne „nachgeholt“ | Selbsttest + `test_schliessvermerk_verspricht_kein_nachholen` rot |

---

## Was bewusst **nicht** getan wurde

* **Der 05.10. wird nicht nachträglich grün gerechnet.** Er bleibt 1/2 LIVE –
  verbucht, nicht geheilt. Der Vorgang repariert die Ursache, nicht die
  Statistik.
* **#601 wird nicht rückwirkend wiedereröffnet.** Die Wiedereröffnung gilt dem
  *gemessenen* Tag. Der 05.10. ist Vergangenheit und damit `verbucht`; ihn
  wieder aufzumachen hieße, einen alten Zustand als neu zu verkaufen. Sichtbar
  bleibt er trotzdem: Die Rückstands-Tabelle im Kanal führt die letzten drei
  Publikationstage inklusive ❌ 2026-10-05.
* **Kein Verbot von „Closes #…“ in Reparatur-Vorschlägen.** Ein Verbot wäre
  Papier: Es kann nicht erzwungen werden, und es verlagerte das Problem in die
  Disziplin. Die Messung ist die stärkere Regel – sie öffnet den Kanal wieder,
  gleichgültig wer ihn geschlossen hat.
* **Keine zweite oder dritte Meldung für denselben Zustand.** Die
  Produktions-Wache (#609) und die Auslieferungs-SLO (#610) behalten ihre
  Kanäle: Sie beantworten andere Fragen (Engine-Lage bzw. öffentliche
  Auslieferung) und haben eigene Runbooks. Neu ist nur, dass der *generische*
  Alarm des zentralen Alertings sich ausschließlich auf den Quotenkanal
  stützt – und der wird jetzt an jedem Tag belegt.
* **Kein Auto-Retry für fehlgeschlagene Läufe** – unverändert. Ein roter Lauf
  gehört dem Alerting und dem Betreiber; nachgeholt wird nur, was NIE
  gestartet ist (Slot-Wache, #601).
* **Kein Feiertags-/Pausenkalender erfunden.** Die Kadenz kommt weiterhin
  ausschließlich aus `cadence_guard.PUBLICATION_DAYS`. Wer den Betrieb
  bewusst pausiert, ändert diese eine Quelle – nicht fünf Melder.
* **Keine Handänderung an den offenen Issues #609/#610.** Sie schließen sich
  über ihre eigene Messung (bzw. bleiben zu Recht offen, solange die
  Auslieferung nicht belegt ist). Ein grüner Zustand wird gemessen, nicht
  geklickt.

---

## Offen (kein Automatik-Thema)

* **Der 05.10. bleibt verbucht.** Beim nächsten Publikationstag im Ziel
  schließt die Messung den Kanal mit dem ausdrücklichen Vermerk, dass der
  Fehltag nicht nachgeholt wurde; die Kennzahl „verpasste Publikationstage“
  gehört in die Betrachtung der Auslieferung, nicht in eine korrigierte
  Statistik.
* **#608 selbst** schließt über den Reparatur-Vorschlag dieses Vorgangs
  (**PR #616**, „Closes #608“); der Vorgangs-Abschluss setzt danach als
  zweites, unabhängiges Signal den Prüfvermerk des Repositories.

---

## Bedienung

```bash
npm run engine:deficit            # Zustand in einem Blick (Trockenlauf, kein Schreibzugriff)
python3 scripts/engine_issue.py --deficit   # Kanal belegen (CI: Engine, Kadenz, Produktions-Wache)
python3 scripts/engine_issue.py --selftest  # Vorfall 05./06.10. nachgestellt
npm run test:engine:deficit       # Selbsttest + 39 Unit-Tests
```

Anleitung: `docs/ANLEITUNG-ENGINE-KAPAZITAET.md`, Abschnitt „Wenn der Tag
unter dem Mindestziel bleibt“. Regel: `governance_contract.py` **C23**.

---

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/engine_issue.py` | **Zustandsmaschine** statt Tages-Melder: `quoten_lage`/`urteil`, tägliche Kadenz (auch Ruhetage), Wiederöffnen rot geschlossener Kanäle, ehrliche Schließvermerke, `--lage`, `--selftest`, Fail-loud (Exit 2) bei Melder-Defekt |
| `scripts/cadence_guard.py` | **Kalender-SSOT**: `letzter_publikationstag()` + `publikationstage_zurueck()`; Selbsttest prüft alle sieben Wochentage |
| `scripts/publication_check.py` | `expected_day()` delegiert an die SSOT (Name und Aufrufer unverändert) |
| `.github/workflows/produktions-wache.yml` | neuer Schritt „Quoten-Fachkanal belegen (auch an Ruhetagen)“ – täglicher Beleg, außerhalb `WARTEND` |
| `.github/workflows/kadenz-endkontrolle.yml` | Reconcile belegt den Fachkanal ausdrücklich **vor** der Quotenmessung; Warnung benennt den Melder-Defekt statt „Defizit-Fachmeldung“ |
| `scripts/governance_contract.py` | **Regel C23** + `engine_issue.py` in `GUARDS` + sieben Kunstbefund-Proben im Kontrakt-Selbsttest |
| `scripts/tests/test_engine_issue.py` | **neu** – 39 Tests (Messung, Entscheidung, Wortlaut, Verhalten mit gestubbtem GitHub, Workflow-Verträge, Kalender-SSOT) |
| `scripts/tests/sim/alert_scoping_sim.mjs` | zwei Szenarien: #608 (kein Duplikat) und Gegenprobe (fail-open) |
| `docs/ANLEITUNG-ENGINE-KAPAZITAET.md` | Abschnitt „Wenn der Tag unter dem Mindestziel bleibt“ (Besitzer/Kadenz/Schließpfad) |
| `docs/QUALITAETS-REGELWERK.md` | Dauervorgabe + Selbstheilungs-Matrix auf den Zustandskanal umgestellt |
| `CLAUDE.md` | Dauervorgabe „Eine Quote ist ein Zustand, kein Arbeitsauftrag“ |
| `package.json` | `engine:deficit` · `test:engine:deficit` |
