# Wartung · Inhaltsqualität · Vorgang WF-1F8C (#602) — Dauerheilung auf Premium-Niveau

**Datum:** 2026-10-05 · **Issue:** #602 · **Workflow:** `Kadenz-Endkontrolle (Mo/Mi/Fr – 2–3 LIVE erzwingen)`

## Kurzfassung

#602 war kein zusätzlicher Inhaltsfehler. Die Kadenz-Endkontrolle tat fachlich
das Richtige: Sie blieb bei **1/2 LIVE** ehrlich rot und legte den Befund in den
Fachkanal `engine-deficit` (#601). Das zentrale Fehler-Alerting sah danach aber
nur „Workflow rot“ und eröffnete ein zweites, generisches Wartungs-Issue mit
API-Key-/GitHub-/Transient-Runbook. Ergebnis: doppelte Buchführung und eine
falsche Handlungsanweisung.

Die Dauerheilung trennt jetzt sauber:

1. **Tagesdefizit** bleibt rot, wird aber ausschließlich über das
   auto-schließende Fach-Issue `engine-deficit` bearbeitet.
2. **Release-/Build-/Gate-Crashs** bleiben generische Produktionsfehler und
   werden weiterhin vom zentralen Fehler-Alerting gemeldet.
3. Das zentrale Alerting schweigt nur, wenn der rote Schritt ausdrücklich als
   `TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig` klassifiziert ist
   **und** ein offenes, für diesen Lauf frisch aktualisiertes
   `engine-deficit`-Issue mit Marker nachweisbar ist. Fehlt dieser Fachkanal
   oder ist nur ein altes Defizit-Issue übrig, bleibt das Alerting fail-open.

## Ursache

Der bisherige rote Schluss der Kadenz-Endkontrolle war ein Sammelschritt:

```bash
python3 scripts/engine_issue.py --deficit
python3 scripts/publication_check.py
test '${{ steps.release.outcome }}' = success
```

Damit waren drei unterschiedliche Klassen im selben GitHub-Schritt verborgen:

| Klasse | Fachliche Bedeutung | Alter Effekt |
|---|---|---|
| Tagesdefizit | Quote unter Minimum, Fachkanal `engine-deficit` zuständig | generisches `auto-report`-Duplikat (#602) |
| Release-Crash | Hugo/Gate/Tool blockiert die Endabnahme | sollte generisch laut bleiben |
| Vorprüfungs-/Gate-Crash | Cover-/Korrektur-Schritt scheitert vor der Endabnahme | sollte generisch laut bleiben |

Das zentrale Alerting konnte diese Klassen nicht unterscheiden und musste
fail-open melden. Für #602 war das zu laut; für einen echten Build-Crash wäre
Stummschalten gefährlich gewesen.

## Umsetzung

### 1. Kadenz-Endkontrolle klassifiziert maschinenlesbar

`Final gates and validated reserve` schreibt jetzt neben dem Exit-Code auch
eine Klasse in `GITHUB_OUTPUT`:

* `ok`
* `tagesdefizit`
* `release-crash`
* `cover-crash`
* `unknown`

Der Reconcile-Schritt gleicht weiterhin `engine_issue.py --deficit` und
`publication_check.py` ab, endet aber selbst mit `exit 0`. Rot werden danach
nur noch dedizierte Folgeschritte:

* `RELEASE-CRASH – Endabnahme blockiert`
* `KADENZ-GATE-CRASH – Vorprüfung oder Endabnahme unklassifiziert`
* `TAGESDEFIZIT – Fachmeldung engine-deficit ist zuständig`

Damit steht die echte Fehlerklasse direkt in der Job-Step-Liste, die das
Alerting ohnehin ausliest.

### 2. Fehler-Alerting dedupliziert nur den Fachkanal-Fall

`alert-on-failure.yml` erkennt den Tagesdefizit-Schritt und sucht in den
offenen Issues nach:

* Label `engine-deficit`
* Marker `<!-- engine-deficit-id: tagesdefizit -->`
* `updated_at` mindestens in Reichweite des aktuellen Laufs

Nur wenn alle drei Signale vorhanden sind, wird kein generisches
`auto-report`-Issue angelegt. Fehlt der Fachkanal, ist er veraltet oder konnte
er nicht aktualisiert werden, entsteht bewusst weiterhin der generische Alarm
(fail-open), denn dann ist nicht das Defizit das Problem, sondern die
Zustellung der Fachmeldung.

### 3. Regressionstests

Neu abgesichert:

* `scripts/tests/test_kadenz_endkontrolle_workflow.py` prüft die
  maschinenlesbaren Klassen, den nicht mehr roten Reconcile-Sammelschritt und
  die getrennten roten Folgeschritte.
* `scripts/tests/test_alert_scoping.py` prüft die neue Fachkanal-Regel im
  Alerting.
* `scripts/tests/sim/alert_scoping_sim.mjs` simuliert zusätzlich:
  * Tagesdefizit **mit** offenem `engine-deficit` → kein Duplikat.
  * Tagesdefizit **ohne** Fach-Issue → generischer Alarm bleibt fail-open.
  * Tagesdefizit mit **veraltetem** Fach-Issue → generischer Alarm bleibt
    ebenfalls fail-open.

## Ergebnis

Die Kadenz-Endkontrolle kann weiterhin ehrlich rot melden, ohne den Betreiber
mit einem zweiten, fachlich falschen Wartungs-Issue zu wecken. Gleichzeitig
werden echte Crashs nicht verschluckt: Sie haben eigene Schritt-Namen und
laufen nicht durch die `engine-deficit`-Stummschaltung.
