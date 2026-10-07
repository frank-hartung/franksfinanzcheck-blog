# Auslieferungs-SLO · Vorgang WF-7C1F (#611) — Dauerheilung auf Premium-Niveau

**Datum:** 07.10.2026
**Auslöser:** Wartungs-Issue **#611** („Publication Delivery (öffentlicher
Nachweis) schlägt fehl", Alert-Key `WF-7C1F`) — zweimal rot am 06.10.2026.
**Verwandt:** P1-Kanal **#610** („Öffentliche Artikel-Auslieferung unter
Mindestziel") und der Zustandskanal **#608** (Regel C23).

## Kurzfassung

Der Vorfall war **kein API-Key-Problem, kein GitHub-Ausfall und kein
transienter Fehler** — die drei Ursachen, die das automatisch erzeugte Issue
#611 zur Prüfung anbot. Der Beleg sprach für sich selbst:

```json
{"day": "2026-10-05", "mode": "public", "minimum": 2, "maximum": 3,
 "source": ["2026-10-02-preiswert-surfen-…"],
 "delivered": ["2026-10-02-preiswert-surfen-…"],
 "errors": [], "ok": false}
```

`delivered == source`, `errors: []` — **die Auslieferung war vollständig; die
Quelle trug den gemessenen Montag (05.10.) nur mit 1/2 LIVE.** Der Montag endete
bei 1/2 (der 19:22-UTC-Slot rettete genau einen Artikel; Nachtragen von Inhalten
ist verboten). Kein Lauf kann diesen Tag mehr bestätigen, und da der
Fehlerpfad nur ein **Sammel-Boolean** prüfte („Missing public delivery is a
failed run"), nannte kein Lauf die Ursache. Das zentrale Fehler-Alerting legte
deshalb das generische Wartungs-Issue **#611** mit falschem Runbook an — obwohl
der Fachkanal `engine-deficit` (C23, #602/#608) für genau diesen Zustand
existiert.

Die Heilung trennt die zwei Wahrheiten, die in `ok` steckten, und gibt jeder
einen **Besitzer**: Der Beleg trägt jetzt eine **Klasse**
(`quelle_unter` · `quelle_ueber` · `auslieferung` · `unbekannt` · `ok`), der
Workflow antwortet der Klasse mit einem **eigenen, ehrlichen roten Schritt**,
und nur das Bestandsdefizit ruft den Defizit-Fachkanal — mit Frischebeweis
**vor** dem roten Exit. Regel **C28** friert den Vertrag ein.

## Befund

### Die Beweiskette des Vorfalls (alle Zeiten UTC)

| Zeit | Ereignis |
|---|---|
| 05.10.2026, 12:17 | Geplanter Nachweis-Lauf; der Montag endet später bei 1/2 LIVE (Slot 19:22:11) |
| 06.10.2026, 01:17:23 | Lauf `37398400068` (Commit `8d4a880d`, schedule) startet |
| 06.10.2026, ~01:26 | Beleg rot (`day 2026-10-05`, `source: 1`, `delivered: 1`, `errors: []`); Wiederherstellung läuft, zweiter Beleg ebenfalls rot; Sammel-Schritt „Missing public delivery is a failed run" schlägt fehl |
| 06.10.2026, 01:26:36 | Zentrale Fehler-Alerting legt **#611** an (WF-7C1F) — mit API-Key-/Transient-Runbook |
| 06.10.2026, 14:10:38 | Lauf `37476766911` (Commit `52c03f02`) — identisches Muster |
| 06.10.2026, 14:15:07 | `publication_incident.py` aktualisiert den P1-Kanal #610 mit den Tageszahlen |
| 06.10.2026, 14:20:38 | Lauf rot beendet — erneut ohne genannte Ursache |

### Die Schrittkette beider Läufe (identisch)

```
✓ Verify sitemap AND article HTML; retry CDN propagation     ← outcome: failure
✓ Run bounded recovery and wait for its deploy
✓ Re-check public receipt after recovery                     ← outcome: failure
– Close incident when the recovered receipt is public        ← skipped (korrekt)
✗ Missing public delivery is a failed run                    ← der Befund
```

Die Häkchen auf den Belegschritten täuschen: Beide tragen
`continue-on-error: true`, führen also `conclusion: success`, obwohl ihr
`outcome` `failure` ist. Der Abschluss-Schritt prüft korrekt die `outcome`s —
und der Sammel-Schritt davor/danach sagte nur **dass** etwas fehlt, nie **was**.

### Warum jeder weitere Lauf rot bleiben musste

Der gemessene Tag ist `cadence_guard.letzter_publikationstag` — am Dienstag
(06.10., kein Publikationstag) also Montag, der 05.10. Dieser Tag war
**unheilbar**: Öffentlich fehlte nichts (beide Slugs der Quelle waren live
erreichbar, der Beleg sagt `errors: []`), und die Quelle hätte den Tag nur
durch nachträgliches Publizieren erreichen können — genau das ist verboten.
Die Wiederherstellungskette (Kadenz-Backstop + Deploy) kann einen
Auslieferungsfehler heilen, aber kein Bestandsdefizit. Der Workflow musste
also rot bleiben; nur die **Meldung** war falsch adressiert.

### Die zwei Wahrheiten in `ok` — und ihre zwei Besitzer

`ok = (minimum ≤ delivered ≤ maximum) and not errors` vermischt:

* **Bestand** — wie viele LIVE-Artikel trägt der gemessene Tag?
  Besitzer: die Defizit-Wache / Nachfüllung (`engine-deficit`, C23).
* **Auslieferung** — ist jeder davon öffentlich erreichbar?
  Besitzer: Deploy/CDN, P1-Kanal (`publication-delivery-slo`, #610).

Die Aufteilung ist vollständig und überschneidungsfrei, weil `delivered` immer
eine Teilmenge von `source` ist: Liegt `source` außerhalb des Zielbands
(2–3/Tag), kann die Auslieferung den Tag gar nicht bestätigen → der **Bestand**
ist der Fall (`quelle_unter`/`quelle_ueber`). Liegt `source` im Band, kann jede
Abweichung nur aus der **Auslieferung** kommen. Ohne lesbaren Beleg ist die
Klasse `unbekannt` — und unbekannt ist laut, nie still.

### Was nicht die Ursache war

* **Kein API-Key-/Token-Problem:** kein Aufruf im Lauf benutzte einen Schlüssel.
* **Kein GitHub-/Runner-Ausfall:** alle Schritte liefen normal durch.
* **Kein CDN-/Deploy-Problem:** die öffentliche Website war intakt. Der
  07.10.-Nachweis (unten) belegt: Beide LIVE-Artikel des Tages rendern
  vollständig inklusive Cover, Inhaltsverzeichnis und C24-Tagesgeld-Box.
* **Kein überhöhtes Mindestziel:** Das Band stand auf 2–3/Tag; der Montag
  verfehlte es real.

## Umsetzung

### 1. Die Klasse gehört in den Beleg (`scripts/publication_check.py`)

* Neue reine Funktion **`klasse(result)`** — `ok` zuerst (ein bestätigter Tag
  hat keine Defizitklasse), danach das Bestandsband, zuletzt die Auslieferung;
  fehlender/kaputter Beleg → `unbekannt` (fail-closed).
* Konstanten `KLASSE_OK`, `KLASSE_QUELLE_UNTER`, `KLASSE_QUELLE_UEBER`,
  `KLASSE_AUSLIEFERUNG`, `KLASSE_UNBEKANNT` + Tupel `KLASSEN`.
* **`klasse_aus_beleg(report)`** liest die Klasse des gespeicherten Belegs —
  ohne Netz, ohne Schreiben, mit Meldung im Fehlerfall.
* **`besitzer(kls)`** liefert dieselbe Zuordnung wie der Workflow (Tabelle
  unten), als Dokumentation im Code.
* `check()` schreibt `result['klasse']`; `beleg_schreiben()` schreibt die
  Klasse in die versionierte Historie (`data/publication-delivery-history.jsonl`),
  damit ein roter Tag später seinem Besitzer zuordenbar bleibt; fehlt sie,
  wird sie nachgerechnet.
* CLI **`--klasse [--report …]`**: gibt nur die Klasse aus, Exit 2 ohne Beleg.
  Kein Netz, kein Schreiben — die Wache ist eine reine Leseoperation.
* `beleg_schreiben()` **garantiert** die Klasse: Gibt ein Aufrufer sie
  nicht mit, wird sie nachgerechnet – ein Beleg ohne Klasse wäre ein
  Beleg, den der Workflow nicht zuordnen kann.
* **`--selftest`**: Logik-Beweis (Klasse, fail-closed, Beleg + Historie)
  ohne Netz und ohne Schreiben in den Arbeitsbaum. Der
  `selftest_runner.py` entdeckt ihn automatisch; er läuft seit dieser
  Heilung in jedem Qualitäts-Gate mit – zusätzlich unter einer um
  +97 und +1461 Tage vorgestellten Uhr (uhrfest).
* **`ok` bleibt unverändert** (Minimum ≤ öffentlich bestätigt ≤ Maximum und
  keine Fehler). Kein Aufrufer verliert ein Feld; alle bestehenden Tests laufen
  weiter.

### 2. Der Workflow antwortet der Klasse (`.github/workflows/publication-delivery.yml`)

Der Sammel-Schritt

```yaml
      - name: Missing public delivery is a failed run
        run: |
          if [ '${{ steps.receipt.outcome }}' = success ]; then exit 0; fi
          test '${{ steps.recovered_receipt.outcome }}' = success
```

ist ersetzt. Nach den Belegen liest ein Schritt **„Auslieferungsklasse des
gültigen Belegs"** (`id: klasse`) die Klasse des **gültigen** Nachweises (der
zweite Lauf überschreibt `tmp/publication-receipt.json`; der erste bleibt als
tagesgenaues Artefakt erhalten). Dann antwortet je ein eigener roter Schritt:

| Klasse | Roter Schritt | Wirkung |
|---|---|---|
| `quelle_unter` | „TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig (Auslieferungs-SLO)" | belegt den Fachkanal (`engine_issue.py --deficit`) **vor** dem `exit 1`; der Name trägt beide Kennwörter, an denen das zentrale Fehler-Alerting die Fachkanal-Stummschaltung festmacht (#602-Regel) |
| `quelle_ueber` | „KADENZ-ÜBERSCHUSS – Bestand über dem Tagesmaximum" | laut mit Besitzer Kadenz-Gate; im nächsten Deploy wird zurückgestuft |
| `auslieferung` / `unbekannt` | „AUSLIEFERUNGS-DEFIZIT – öffentlicher Nachweis fehlt" | laut mit Besitzer P1-Kanal (#610) bzw. fail-closed ohne Beleg |

Alle drei Schritte enden ehrlich rot (`exit 1`) — die SLO wird nicht
schöngeredet; nur die **Adresse** der Meldung ist jetzt korrekt. Kann der
Fachkanal nicht belegt werden, erscheint eine ausdrückliche `::warning::`
(„Melder-Defekt, kein Quotendefekt") — fail-open bleibt sichtbar.

### 3. Der P1-Kanal bleibt der Buchhalter des Tages

`publication_incident.py` ist unangetastet: Er verbucht einen Fehltag als
**Quittung** („verbucht, nicht behoben"), schließt nur mit einem Nachweis
**desselben** Tages und verweigert Backdating. Die Klasse bestimmt nur, **wer
gerufen wird** — und wer nicht.

### 4. Vertrag C28 („Die Klasse geht dem Kanal vor")

`scripts/governance_contract.py` erhält Regel **C28** (C24 bleibt für die
C24-Bank-Marke reserviert). Sie friert ein:

* **Beleg:** alle vier Defizitklassen, reine `klasse(result)`, `ok` zuerst,
  `result['klasse']`, `klasse_aus_beleg`, Klasse in der Historie.
* **Workflow:** kein Sammel-Schritt mehr; Klassenschritt; eigener roter
  Schritt je Klasse; genau **ein** Schritt trägt „TAGESDEFIZIT" +
  „engine-deficit" und belegt den Fachkanal **vor** dem roten Exit.
* **Alerting:** `alert-on-failure.yml` behält beide Kennwörter in der
  Stummschaltungs-Regel und beobachtet diesen Workflow weiterhin.
* **Sechs Kunstbefunde** im Kontrakt-Selbsttest: Beleg ohne Klasse, Historie
  ohne Klasse, Rückkehr des Sammel-Booleans, Frischebeweis **hinter** dem
  roten Exit, Schrittname ohne Kennwörter, still unterdrückter unbekannter
  Beleg. Jeder wird rot, der gute Zustand bleibt still.

### 5. Tests

* **Neu:** `scripts/tests/test_publication_delivery_workflow.py` — 6
  Workflow-Verträge (Klassenschritt liest den gültigen Beleg; Klasse kommt vor
  jedem Verdikt; Fachkanal-Schritt mit Namen, Bedingung, Reihenfolge und
  `exit 1`; Alerting-Kennwörter im `routedToEngineDeficit`-Ausdruck;
  `quelle_ueber`/`auslieferung`/`unbekannt` bleiben laut; Sammel-Boolean
  dauerhaft entfernt).
* **Erweitert:** `KlassenRoutingTests` in
  `scripts/tests/test_publication_reliability.py` (Klasse in Beleg, Historie
  und CLI; fail-closed ohne Beleg; `ok` unverändert additiv).
* **Selbsttest mit Zähnen:** `publication_check.py --selftest` lief erst
  rot, als ein fehlendes Klassenfeld im Beleg geprüft wurde – geheilt wurde
  über die Beleg-Garantie, nicht über eine weichere Erwartung.
* **Bedienung:** `npm run delivery:klasse` · `npm run test:delivery`.

### 6. Dokumentation

`CLAUDE.md` (Abschnitt „Die Klasse geht dem Kanal vor", C28, seit #611) und
`docs/publication-reliability.md` (Nachtrag 07.10.2026) erklären Vorfall,
Klassentabelle und Bedienung; `docs/GOVERNANCE-KONTRAKT.md` wurde über
`governance_contract.py --quick --md` neu erzeugt (enthält C28).

## Nachweis

### Die Beweisläufe (lokal, ohne Netz für die Logik)

```
$ python3 scripts/publication_check.py --selftest
✅ publication_check-Selbsttest grün (Klasse, fail-closed, Beleg + Historie;
   ohne Netz, ohne Repo-Schreiben).

$ python3 -m unittest scripts.tests.test_publication_reliability \
      scripts.tests.test_publication_delivery_workflow
Ran 62 tests in 0.154s
OK

$ python3 -m unittest discover -s scripts/tests
Ran 2005 tests in 120.067s
OK (skipped=23)

$ python3 scripts/selftest_runner.py            # das Qualitäts-Gate
SELBSTTEST-RUNNER · 166 Wachen gelaufen · 332 Uhr-Proben · 102.6 s
  ✅ Jeder Selbsttest grün – und unter einer um +97, +1461 Tage
     vorgestellten Uhr ebenfalls.
```

Der Beweis-Ledger (Regel C27) blieb unberührt: `git status --porcelain --
data/audit` ist leer. Ein Nebenbefund mit Vorführwert: Der
Kontrakt-Selbsttest meldete den eigenen, veralteten Sabotage-Anker, als die
Beleg-Garantie den Historien-Literal änderte – ein Kunstbefund, der sich
selbst meldet, statt still zu veralten.

### Der Vertrag prüft in beide Richtungen

```
$ python3 scripts/governance_contract.py --selftest
✅ KONTRAKT-SELFTEST bestanden (C1–C28 mit Kunstbefunden: Fehler erkannt,
   gutes Setup bleibt still).

$ python3 scripts/governance_contract.py --quick --md docs/GOVERNANCE-KONTRAKT.md
🔒 GOVERNANCE-VERTRAG erfüllt – alle 27 Regeln prüfen in beide Richtungen
   (Fehler UND Schein-Sicherheit).
```

### Die Klasse am echten Beleg

Ohne Beleg (fail-closed, wie im CI-Fall vor dem ersten Lauf):

```
$ python3 scripts/publication_check.py --klasse
⚠ Kein lesbarer Beleg unter tmp/publication-receipt.json (FileNotFoundError)
  – fail-closed: ohne Beleg keine Klasse.
unbekannt                              (Exit 2)
```

Am Beleg des gemessenen Tages (2/3 LIVE bestätigt) liefert `klasse()` `ok`;
der eingefrorene Fehltag-Fixpunkt aus #610 (`source: 1`, Band 2–3,
`delivered == source`) liefert `quelle_unter` — genau die Klasse, die den
Fachkanal ruft.

### Die Auslieferung ist intakt (07.10.2026, öffentlich abgerufen)

* `…/posts/2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest/`
  — rendert vollständig (Titel, Cover, Inhaltsverzeichnis, „Kurz & knapp",
  C24-Tagesgeld-Box).
* `…/posts/2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert/`
  — rendert vollständig.

Beide sind die zwei LIVE-Artikel des 07.10. — der Tag steht bei 2/2.

### Erwartete Konvergenz

* **#611:** schließt sich beim nächsten **grünen** Lauf auf `main`
  (das zentrale Alerting schließt nur gegen einen echten grünen Lauf).
* **#610:** Der nächste grüne Lauf mit Tagesbeleg quittiert den Fehltag
  05.10. („verbucht, nicht behoben") — der Tag selbst bleibt ehrlich rot.

## Was bewusst **nicht** getan wurde

* **Kein Nachdatieren** und keine Rückwirkend-Begrünung des 05.10.
* **Keine Absenkung** des Mindestziels und kein Aufweichen von `ok`.
* **Keine stille Deaktivierung** des Alertings: Unbekannte Belege, Überschuss
  und Auslieferungsdefizit bleiben laut; nur die Zuständigkeit ist korrekt.
* **Keine Änderung am P1-Kanal** (`publication_incident.py`) — der Buchhalter
  des Tages war nie defekt.
* **Keine kosmetische Schritt-Umbenennung:** Der Zuordnungsvertrag
  (Schrittname ↔ Alerting-Regel) wird in beide Richtungen geprüft
  (Governance C28 + Workflow-Test).

## Bedienung

| Befehl | Zweck |
|---|---|
| `npm run delivery:klasse` | Klasse des gültigen Belegs (ohne Netz; Exit 2 = kein Beleg) |
| `python3 scripts/publication_check.py --selftest` | Logik-Beweis der Klasse (uhrfest, schreibfrei) |
| `npm run test:delivery` | Workflow-Verträge + Auslieferungs-Regressionen |
| `python3 scripts/publication_check.py --online` | voller Nachweis (schreibt Beleg + Historie) |
| `python3 scripts/governance_contract.py --selftest` | Kontrakt C1–C28 inkl. sechs C28-Kunstbefunden |

## Geänderte Dateien

| Datei | Änderung |
|---|---|
| `scripts/publication_check.py` | Klasse (`klasse`, `klasse_aus_beleg`, `besitzer`, `KLASSE_*`), `--klasse`, `--selftest`, Klasse in Beleg/Historie |
| `.github/workflows/publication-delivery.yml` | Klassenschritt + drei klassenspezifische rote Schritte; Sammel-Boolean entfernt |
| `.github/workflows/alert-on-failure.yml` | **unverändert** — die Gegenseite des Vertrags |
| `scripts/tests/test_publication_delivery_workflow.py` | neu: 6 Workflow-Verträge |
| `scripts/tests/test_publication_reliability.py` | `KlassenRoutingTests` ergänzt |
| `scripts/governance_contract.py` | Regel C28 (Prüfung, RULE_TEXT, LABEL, sechs Kunstbefunde) |
| `docs/GOVERNANCE-KONTRAKT.md` | regeneriert, enthält C28 |
| `CLAUDE.md`, `docs/publication-reliability.md` | Betriebsdokumentation |
| `package.json` | `delivery:klasse`, `test:delivery` |
