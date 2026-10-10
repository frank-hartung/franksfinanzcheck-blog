# Bot-Watchdog · Auslieferung · Vorgang #676
# DAUERHEILUNG (Premium-Level) – 10.10.2026

**Vorgang:** Bot-Watchdog #676
**Bereich:** Öffentliche Auslieferung (deploy.yml) + Alarm-Wache (bot-watchdog.yml)
**Klasse:** DAUERHEILUNG (kein manueller Eingriff mehr nötig)
**Ziel:** Kein Mess-, Report- oder Siegel-Schritt darf die öffentliche Auslieferung
blockieren – und ein 404-Befund muss seine Ursache benennen und sich selbst heilen.

---

## 📋 Zusammenfassung des Vorfalls

| Feld | Wert |
|---|---|
| **Issue** | [#676](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/676) – „Bot-Watchdog: Automatisierung braucht Eingriff" |
| **Befund im Ticket** | `P1 · Neuester Artikel nicht live` → HTTP 404 auf `/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/` |
| **Ticket-Stand** | 2026-10-09 15:28 UTC |
| **Workflow** | `deploy.yml` (Deploy auf GitHub Pages) |
| **Gestorbener Schritt** | `49. Release-Scorecard (Produktionswahrheit versiegeln, fail-closed)` |
| **Folge** | Schritte 50–60 sprangen, inkl. `Artefakt für offizielles Pages-Deployment hochladen`; Job `pages-deployment` startete nie |
| **Letzte Auslieferung vorher** | 2026-10-08 22:35:05 UTC (Pages-Deployment `ca97b1b3`) |
| **Erste Auslieferung danach** | 2026-10-09 18:13:15 UTC (Pages-Deployment `b9a8b012`, Status `success` 18:13:57) |
| **Dauer der Sperre** | **19 h 38 min** ohne öffentliche Auslieferung |
| **404-Dauer des Artikels** | **4 h 11 min** (veröffentlicht 14:02:27 UTC → live 18:13 UTC) |

### Belegte Zeitkette

Alle Angaben sind über die GitHub-API erhoben (`runs`, `jobs`, `deployments`,
`contents`). Die Actions-Log-Dateien selbst waren aus dieser Umgebung nicht
lesbar (`results-receiver.actions.githubusercontent.com` ist nicht erreichbar);
die Beweise stammen deshalb aus Lauf-/Schritt-/Deployment-Abschlüssen.

| Zeit (UTC) | Ereignis | Beleg |
|---|---|---|
| 07.10. 22:44:32 | Artikel kommt auf `main` (Rückholung #614) | Commit `564b86f18a` |
| 08.10. 22:35:05 | **Letztes** öffentliches Pages-Deployment vor der Sperre | Deployment `ca97b1b3` |
| 09.10. 02:12:40 | Erster roter Deploy-Lauf der Serie | Run `37873477112` |
| 09.10. 14:02:27 | Artikel wird veröffentlicht (`date: 2026-10-09T14:01:19Z`, `draft: false`) | Commit `7633656ba4` |
| 09.10. 15:28 | **Ticket #676**: HTTP 404 | Issue-Body |
| 09.10. 17:43:10 | Letzter roter Lauf der Serie | Run `37968247786` |
| 09.10. 17:45:30 | Reparatur der Scorecard-Messung (PR #677, Issue #674) | Commit `b9a8b01279` |
| 09.10. 18:13:15 | **Erstes** öffentliches Pages-Deployment mit dem Artikel | Deployment `b9a8b012`, `success` |
| 10.10. 07:40:50 | Aktuell letztes Deployment (Artikel ausgeliefert) | Deployment `a6e0d208`, `success` |

**Lückenlose Fehlerserie:** zwischen 08.10. 22:06 und 09.10. 17:45 gab es
**20 fehlgeschlagene und 1 verdrängten** `deploy.yml`-Lauf. Stichproben über die
gesamte Spanne (02:12, 09:08, 11:32, 12:40, 14:35, 16:15, 17:00, 17:43) nennen
jedes Mal denselben Fehlerschritt:

```
deploy → FEHLER-SCHRITT: 49. Release-Scorecard (Produktionswahrheit versiegeln, fail-closed) → failure
deploy → 50.–60. Schritt: skipped   (inkl. „Artefakt für offizielles Pages-Deployment hochladen")
An GitHub Pages ausliefern (Environment github-pages) → skipped
```

---

## 🔍 Wurzelursache – und warum sie strukturell ist

PR #677 hat am 09.10. **den Auslöser** geheilt: Die Scorecard maß Redundanz über
eine eigene Schleife, das Publish-Gate über eine andere; eine wortgleiche
Tagesgeld-CTA fiel deshalb erst im letzten Deploy-Schritt auf. Seit #677 messen
beide denselben Collector.

**Geblieben ist die Architektur, die aus einem Messfehler einen 19-Stunden-Ausfall
macht.** Die Release-Scorecard steht im `deploy`-Job **vor** der Auslieferung und
bricht bei jedem von Null abweichenden Exit-Code hart ab:

```
48. Anker-Wache                     ← Inhalts-Gate (darf blockieren)
49. Release-Scorecard  ✗ fail-closed ← BEWEISLAUF (maß falsch – und blockierte)
50. Scorecard committen              skipped
51.–57. Audio, Pagefind              skipped
58. Deploy auf gh-pages              skipped
60. Pages-Artefakt hochladen         skipped   ← ohne das gibt es keine Auslieferung
    pages-deployment                 skipped   (needs: deploy, implizit success())
```

Die Scorecard ist laut `docs/ANLEITUNG-RELEASE-SCORECARD.md` ein *Beweislauf ohne
Heilung*. Ihr Exit-Vertrag trennt zwei grundverschiedene Zustände:

| Exit | Bedeutung | Darf die Auslieferung stoppen? |
|---|---|---|
| `0` | Bestand versiegelt | – |
| `1` | heutige Kandidaten fachlich blockiert | **ja** – echter Inhaltsbefund |
| `2` | **Werkzeugfehler** (Messung kaputt) | **nein** – das ist kein Inhaltsbefund |

Der Deploy behandelte beide gleich. Damit ist jede künftige Störung des
Messwerkzeugs – neue Dimension, geändertes Datenformat, Detektorfehler – ein
Kandidat für denselben Ausfall. Genau deshalb ist #676 mit der Reparatur von
#677 **nicht** erledigt.

**Zweite Wurzelursache (Wache):** Der Befund trug den Besitzer `auto`
(„eine Maschine kann ihn heilen"), geheilt hat ihn niemand. Der nächste Schritt
im Ticket war eine Arbeitsanweisung an einen Menschen („Deploy prüfen, ggf.
Deploy-Catchup triggern"), und die Ursache – der blockierende Schritt – stand
nicht darin. Ein Deploy-Catchup hätte zudem 20× dasselbe getan: am selben
Schritt scheitern.

---

## ✅ DAUERHEILUNG

### 1. `deploy.yml` – Auslieferung vor Siegel

* **Scorecard wertet den Exit-Code aus** (`id: scorecard`): `0` → weiter ·
  `1` → harter Stopp, nichts geht live (unverändert fail-closed) ·
  `2`/andere → Werkzeugfehler: Auslieferung läuft weiter, der Fehler wird als
  Job-Output gemerkt und `::error::` annotiert.
* **Auslieferungs-Beleg** (`id: artefakt`) direkt nach
  `actions/upload-pages-artifact` – der maschinenlesbare Beweis „die
  Veröffentlichung ist raus". Er ist **der letzte Schritt** des `deploy`-Jobs:
  Danach darf nichts mehr folgen, was den Job rot machen kann.
* **Neuer Job `release-seal`** (`needs: [deploy-gate, deploy, pages-deployment]`,
  `if: always()`): legt das Siegel **nach** der Veröffentlichung und macht den
  Lauf rot, wenn
  * der Auslieferungs-Beleg fehlt, obwohl das Gate einen Deploy verlangte
    („Auslieferung ausgeblieben" – Klasse #537/#676),
  * der `deploy`-Job vor der Auslieferung abbrach (Ursache wird benannt),
  * das Artefakt bestätigt ist, aber `pages-deployment` nicht `success` war,
  * die Scorecard einen Werkzeugfehler meldete (Siegel fehlt für diesen Stand).

  Ein verdrängter Lauf (`cancelled`, Issue #218) ist ausdrücklich **kein** Befund.
  `release-seal` ist kein `needs`-Vorlauf von `pages-deployment` – das Siegel
  kann die Auslieferung nicht mehr blockieren. Fail-closed bleibt erhalten:
  `alert-on-failure.yml` meldet den roten Job weiterhin samt Schrittnamen.

### 2. `scripts/bot_watchdog.py` – Ursache statt Symptom

* `classify_deploy_jobs(jobs)` bewertet die Job-Liste eines `deploy.yml`-Laufs
  **rein funktional** (ohne I/O, damit der Vertrag testbar ist):
  `ausgeliefert` · `blockiert` (+ Name des blockierenden Schritts) ·
  `uebersprungen` (kein Deploy verlangt / verdrängt) · `unbekannt` (kein Urteil).
* `deploy_blockade()` liest den letzten abgeschlossenen Lauf über `gh` und
  reicht ihn an die Klassifikation. gh-Fehler, offene Läufe und leere Fenster
  ergeben `unbekannt` – **Offline ist kein Ausfall**, daraus entsteht kein Befund.
* **Neuer Befund `deploy-blockade`** (P1, Besitzer `auto`): „Auslieferung
  blockiert (Live-Stand eingefroren)" – **unabhängig vom HTTP-Status**. Am
  09.10. fror die Site 19,6 h ein; sichtbar wurde das erst, als ein neuer
  Artikel 404 lief. Solange kein neuer Artikel erscheint, war ein blockierter
  Auslieferungsweg unsichtbar.
* **Befund `live-site` trägt jetzt Ursache und Heilungsweg**: blockierender
  Schritt im Detail und als `BLOCKIERENDER_SCHRITT=`-Beleg, dazu der
  maschinelle Heilungsweg statt der Arbeitsanweisung an einen Menschen.

### 3. `scripts/watchdog_recovery.py --live-site` – der Heiler

Reihenfolge wie bei der Reserve-Heilung (#661): erst prüfen, ob ein Dispatch
überhaupt heilen kann, dann Doppel-Dispatch vermeiden, dann auslösen.

| Lage | Verhalten | Exit |
|---|---|---|
| Auslieferung blockiert | **kein** Dispatch (er scheiterte am selben Schritt) – Fehler benennt den Schritt | `3` |
| Deploy/Catchup läuft bereits | kein Doppel-Dispatch (gemeinsame `pages-deploy`-Gruppe, #218) | `0` |
| Kette gesund, Artikel fehlt | `gh workflow run deploy-catchup.yml --ref main` | `0` |
| gh/Token fehlt | keine Aktion, `::warning::` | `2` |
| Kette nicht messbar | Dispatch trotzdem (Unklarheit darf die einzige Reparaturroute nicht abschalten) | `0` |

### 4. `bot-watchdog.yml` – Heilung vor Ticket

* Neuer Schritt „Deploy-Catchup bei nicht live-gegangenem Artikel selbst
  auslösen" (`if: CHECK3 FAIL || CHECK3B FAIL`, `continue-on-error: true`).
* Die **Nachmessung** deckt jetzt auch `CHECK3`/`CHECK3B` ab: Ein im selben Lauf
  geheilter Befund erzeugt kein Ticket mehr (Vertrag aus #446/#661).

### 5. Governance-Vertrag **C34 „Auslieferung vor Siegel"**

`scripts/governance_contract.py` prüft den Vertrag in beide Richtungen
(Fehler **und** Schein-Sicherheit) und läuft im PR-Pfad:

| Prüfung | Sabotage, die der Selftest einspielt |
|---|---|
| Scorecard wertet Exit-Code aus | `case`-Auswertung entfernt |
| Inhaltsbefund stoppt weiter | `exit 1` aus dem `1)`-Zweig entfernt |
| Werkzeugfehler blockiert nicht | `exit 1` in den `*)`-Zweig eingebaut |
| Nichts nach dem Auslieferungs-Beleg | Schritt hinter dem Beleg eingefügt |
| `release-seal` vorhanden, `always()`, laut | Job entfernt |
| Watchdog nennt die Ursache | `classify_deploy_jobs` entfernt |
| Heiler dispatcht nicht blind | `return 3` → `return 0` |
| Heilung verdrahtet | `--live-site` aus `bot-watchdog.yml` entfernt |
| Regressionstest vorhanden | Testdatei fehlt |

---

## 🧪 Nachweis

| Prüfung | Befehl | Ergebnis |
|---|---|---|
| Neue Vertragstests Deploy | `python3 -m unittest scripts.tests.test_deploy_publication_priority` | **20 Tests, OK** |
| Neue Watchdog-Tests | `python3 -m unittest scripts.tests.test_bot_watchdog_live_site` | **24 Tests, OK** |
| Regressions-Umfeld (21 Module) | `python3 -m unittest scripts.tests.test_deploy_* scripts.tests.test_bot_watchdog_* …` | **515 Tests, 2 Fehler** – beide in `test_reserve_pipeline` und **vorbestehend** (identisch auf `4bd6f49` ohne diese Änderung) |
| Watchdog-Selbsttest | `python3 scripts/bot_watchdog.py --selftest` | ✅ inkl. neuer #676-Regression |
| Heiler-Selbsttest | `python3 scripts/watchdog_recovery.py --selftest` | ✅ |
| Governance-Vertrag | `python3 scripts/governance_contract.py --selftest` | ✅ C1–C34 (alle Sabotagen erkannt, echter Baum still) |
| Governance-Vertrag real | `python3 scripts/governance_contract.py --quick` | ✅ 32 Regeln erfüllt |
| YAML + Shell der Workflows | `yaml.safe_load` + `bash -n` je geändertem `run:`-Block | ✅ 6/6 Blöcke |
| Verhalten des Siegel-Schritts | echter `run:`-Block aus `deploy.yml`, mit 6 Umgebungs-Lagen ausgeführt | ✅ grün / Werkzeugfehler rot / Auslieferung ausgeblieben rot / Abbruch benannt / `cancelled` still / Pages-Job rot – je erwarteter Exit-Code und Meldung |
| Mutationsprobe | Werkzeugfehler wieder hart abbrechen / Diagnose blind schalten | ✅ 1 bzw. 3 Tests rot, danach wieder grün |

**Nicht prüfbar aus dieser Umgebung:** der öffentliche HTTP-Status von
`https://franksfinanzcheck.de/...` (nur `github.com`, `npmjs.org` und `pypi.org`
sind erreichbar). Der Auslieferungsbeleg stammt deshalb aus dem offiziellen
Pages-Deployment (`a6e0d208`, `success`, 10.10. 07:41 UTC) und aus
`posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/index.html`
auf `gh-pages`.

---

## 📌 Was sich für den Betrieb ändert

| Vorher | Nachher |
|---|---|
| Kaputtes Messwerkzeug friert die Live-Site ein | Auslieferung läuft, der Lauf wird **nach** der Veröffentlichung rot |
| Ticket sagt „HTTP 404, Deploy prüfen" | Ticket nennt den **blockierenden Schritt** und den Heiler |
| 404 wird erst sichtbar, wenn ein neuer Artikel fehlt | `deploy-blockade` meldet die eingefrorene Auslieferung sofort |
| Catchup muss ein Mensch triggern | Watchdog triggert ihn selbst – und lässt es, wenn es nichts heilen würde |
| Reihenfolge per Konvention | Reihenfolge per Vertrag **C34** (PR-Gate) + 44 Unit-Tests |

**Runbook:** `docs/ANLEITUNG-RELEASE-SCORECARD.md` (Scorecard),
`docs/ANLEITUNG-HUGO-BUILD.md` (Deploy-Kette).
