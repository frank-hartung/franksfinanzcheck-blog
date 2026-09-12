# Reparatur #233 – Wöchentliche SEO-Optimierung (Premium, final)

**Datum:** 2026-09-09
**Workflow:** `Wöchentliche SEO-Optimierung` / `.github/workflows/seo-weekly.yml`
**Issue:** [#233](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/233) · gescheiterter Lauf 34328155997 (Schritt 17 von 35)

---

## 1. Befund (echte Ursache, aus Run-Annotations & Step-Log)

Der Lauf brach im Schritt **„Textverständnis-Report und -Fixes committen"** mit

```
git_sync.sh: Pull von origin/main fehlgeschlagen
(Netzwerk, Auth oder fehlende 'contents: write'-Berechtigung) – kein Konflikt.
```

ab. Analyse:

* Der Fehler kam aus dem **„kein Konflikt"-Zweig** – es lag also KEIN Rebase-Konflikt vor (die erste Reparaturstufe von heute Morgen war korrekt, griff hier aber nicht).
* **Pushes anderer Workflows funktionierten** zeitgleich problemlos (Bot-Commits im Tagesverlauf, `contents: write` vorhanden) → Auth/Berechtigung schieden aus.
* Es handelte sich um einen **einmaligen transienten Netzwerkfehler beim `git pull` (fetch)** – die gleiche Fehlerklasse („EOF" / „Empty reply") wie bei den Reparaturen #209/#220 am Hugo-Asset-Host.
* Der alte `git_sync.sh`-Kern hatte Retries **nur für den PUSH** – der FETCH/PULL hatte **keinerlei Wiederholung**. Ein einziger Blip reichte also, um den Schritt rot zu machen.

**Folgeschaden:** Durch den Abbruch wurden **18 nachfolgende Schritte komplett übersprungen** – Affiliate-Link-/Profi-Check, Bestand-Gate, Cover-Validierung, Meta-Qualitäts-Gate, Textbatterie, A11y-Audit und **IndexNow-Indexierung liefen nie**. Die wöchentliche SEO-Instandhaltung fiel komplett aus, obwohl der Content gesund war.

**Stiller Zweitbefund (aus dem Step-Log desselben Laufs):** Schritt 7 „LSI-Keyword-Änderungen committen" wurde **skipped**, weil `keyword_optimizer.py` mit Exit 1 endet, sobald ein Artikel unter 60/100 Punkten bleibt. Der Schritt lief damit **wochenlang nie** – obwohl `--apply` längst LSI-Fixe in die Artikel geschrieben hatte. Identische silent-gap-Klasse beim „Meta-Änderungen committen"-Schritt (`if: steps.meta.outcome == 'success'`).

## 2. Dauerhafte Härtung (fünf Lagen)

### Lage 1 – `scripts/git_sync.sh`: Fetch-Retry statt Einmal-Blindflug (Kernstück)

* **`fetch_mit_retry()`**: fetch wird pro Runde bis zu `GIT_SYNC_FETCH_TRIES`-mal (Default 3) mit **exponentiellem Backoff + Jitter** wiederholt; nach dem ersten Rückschlag werden die bekannten Gegenmittel `http.version HTTP/1.1` und `http.postBuffer 32 MiB` nachgerüstet (RPC/HTTP-2-Transients).
* **Fehlerklassifikation**: Auth-/Berechtigungsfehler (`could not read Username`, `403`, `Permission denied` …) werden **nicht** wiederholt, sondern sofort präzise gemeldet – nur echte Transients kommen in den Retry.
* **Rettungsanker**: Bleibt der fetch endgültig weg, wird ein **direkter Push** versucht – ist `origin/main` nicht weitergelaufen (wahrscheinlich bei einem Gesamt-Transient), geht er als sauberes Fast-Forward durch und der Lauf bleibt grün.
* **Runden-Logik `sync_und_push()`**: Rebase+Push als Gesamtzyklus (Default 3 Runden) – auch ein mitten im Rennen abgelehnter Push (paralleler Bot) heilt sich durch erneutes Angleichen selbst. NIEMALS force-push.
* **Auto-Resolve mehrstufig**: JSONL-Union-Merge und `--theirs` für generierte Reports jetzt **wellenfest** (auch mehrere konfliktierende Commits nacheinander werden geheilt, mit Guard und Abschluss-Verifikation). Content-Konflikte bleiben **harte Stopps** – kein Blind-Merge.
* Wirkt **systemweit für alle 26 Workflows**, die `git_sync.sh` nutzen (Content-Engine, Wachen, Watchdogs …) – dieselbe transient-Fehlerklasse ist damit überall kuriert.

### Lage 2 – Workflow-Kette: ein Sync-Fehler tötet nicht mehr 18 Schritte

Alle reinen Commit-/Sync-Schritte des Wochenlaufs sind jetzt `continue-on-error: true`. Ein transienter Sync-Fehler bricht die Kette nicht mehr ab – die Änderungen bleiben im Workspace liegen und werden später gesichert (siehe Lage 3). **Harte Gates bleiben bewusst streng rot** („nichts Ungeprüftes geht live"): Affiliate-Link-Check, Affiliate-Profi-Check, Cover-Validierung.

### Lage 3 – Fangnetz-Schritt (neu, Kernstück der Ketten-Resilienz)

Neuer Schritt **„Fangnetz – übergangene Änderungen sicher committen und pushen"** kurz vor Laufende:

* sammelt alles, was ein gescheiterter Commit-Schritt übriggelassen hat, in einem Sammel-Commit ein und pusht es mit dem gehärteten `git_sync.sh`,
* läuft **nicht**, wenn ein hartes Gate (Affiliate/Profi/Cover) rot war – nichts Ungeprüftes geht live,
** succeedet das Fangnetz → Lauf grün, nichts verloren (nur `::warning::`-Annotation); schlägt es aus → Lauf rot → zentrales Fehler-Alerting (Issue-Klasse #233) – aber jetzt mit vollständigem Diagnose-Output statt abgebrochener Kette.

### Lage 4 – Silent Gaps geschlossen (LSI- & Meta-Fixes)

* „LSI-Keyword-Änderungen committen" und „Meta-Änderungen committen" committen jetzt **immer** (`!cancelled()` statt `outcome == 'success'`) – der Exit-1 der Auditoren signalisiert „Rest-Bedarf", nicht „Fixes ungültig".
* Neuer Schritt **„Issue bei kritischen Keyword-Scores"** (mit Dedupe: offenes Issue → Kommentar statt Duplikat) macht den Rest-Bedarf sichtbar, der vorher wochenlang in `continue-on-error` verpuffte.
* Linker/Draft-Healer/lastmod sind gegen Einzelfehler gepanzert (`|| echo ::warning::` bzw. `continue-on-error`).

### Lage 5 – Betriebliche Politur

* `actions/checkout@v4` → **`@v5`** (Node-20-Deprecation-Warnung aus jedem Lauf entfernt).
* Erste Reparaturstufe von heute bleibt unverändert wirksam: Rebase-Konflikt-Autoheilung für generierte Artefakte, `.gitattributes`-Regel `*.jsonl merge=union`, `fetch-depth: 0`.

## 3. Sicherheitsprinzip (unverändert)

Maschinell erzeugte Artefakte (Reports, Statusdateien, JSONL-Historien) werden automatisch konvergiert; **redaktionelle Content-Konflikte bleiben echte Stopps**. Kein Force-Push, kein History-Rewrite, keine Blind-Merges.

## 4. Validierung

* `bash -n scripts/git_sync.sh` – OK
* **Neue Regressions-Suite `scripts/tests/test_git_sync.py`** (läuft automatisch in „Publication reliability regression tests" mit, da `scripts/**` getriggert wird) – 11 Tests gegen synthetische Repos, u. a.:
  * transiente fetch-Ausfälle heilen per Retry (#233-Szenario, deterministisch simuliert),
  * dauerhafter fetch-Ausfall + stehendes Remote → Rettungsanker-Push rettet den Lauf,
  * dauerhafter fetch-Ausfall + paralleler Bot → sauber rot, lokaler Commit unbeschädigt,
  * Push-Race → Auto-Rebase, lineare Historie,
  * Report-Konflikt → deterministisch `--theirs` (frischer Lauf gewinnt),
  * JSONL-Konflikt → deduplizierter Union-Merge,
  * Content-Konflikt → harter Stopp, kein Push.
* Komplettsuite: `python3 -m unittest discover -s scripts/tests` → **29/29 OK** (18 bestehende + 11 neue).
* YAML-Parse von `.github/workflows/seo-weekly.yml` – OK (36 Schritte).

## 5. Empfohlene Folgeoptimierung (außerhalb dieses Fixes)

Das Muster „continue-on-error auf Commit-Schritte + Fangnetz" ist auf die übrigen langen Ketten (z. B. `blog-health-daily.yml`, `premium-governance.yml`) übertragbar; der ge härtete `git_sync.sh`-Kern wirkt bereits ab sofort für alle 26 nutzenden Workflows.
