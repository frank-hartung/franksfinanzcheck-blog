# Schließakte: Struktur-Dauerheilung, Fail-closed-Guard und Selbstheilung

**Stand:** 08.11.2026 · **Vorgänge:** #1098 (Release-Scorecard: F4 nicht beweisbar),
#1126 (Regressionssuite repo-weit rot), #1120 (Akte nicht auf dem Stand der Queue),
#1072 (Befund-Ledger) · **Klasse:** Beweis-/Strukturfehler, kein Fachurteil

> **Kurzfassung.** Die menschliche Schließakte
> `data/faktenfrische_entscheidungen.yaml` war strukturell beschädigt: 20
> Folgeentscheidungen standen nicht als eigener Listenpunkt, sondern als
> zweiter Schlüsselblock **innerhalb** eines fremden Eintrags. YAML
> überschreibt doppelte Schlüssel still mit dem letzten Wert. Dadurch trug
> ein Eintrag eine `geprueft_fassung` und einen
> `vorgaenger_geprueft_fassung` aus **zwei verschiedenen Ketten** – die
> Scorecard brach als Werkzeugfehler ab („Ungültige Folgeentscheidung …
> Vorgänger fehlt oder stimmt nicht", #1098), die Akte konnte nicht
> nachziehen (#1120), und zwei Regressionstests lasen an der falschen Stelle
> (#1126). Behoben sind alle drei – mit einer Heilung, die sich selbst
> beweist und ab jetzt automatisch läuft.

---

## 1. Der Befund (gemessen, nicht vermutet)

```
$ python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen
❌ 11 Listeneintrag/-einträge tragen mehrere Entscheidungen untereinander:
   - Zeile 2383: 2 Entscheidungen in einem Listeneintrag …
   - Zeile 2419: 3 Entscheidungen in einem Listeneintrag …
   … (insgesamt 11 Einträge, 20 verlorene Entscheidungen)

$ python3 scripts/veroeffentlichungs_wache.py --wache
⚠ 1 Werkzeugfehler (kein Inhaltsbefund):
   · [akte] Wache nicht ausführbar: LedgerFehler: Ungültige Folgeentscheidung
     für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag',
     'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht
```

**Warum das kein „Inhaltsproblem" war.** Jede betroffene Entscheidung war
belegt: Person, Datum, Begründung, Beanstandung, Befund-ID und Fassung waren
vorhanden – nur nicht an der Stelle, an der YAML sie liest. Ein pauschales
„rot ist rot, dann löschen wir die Einträge" wäre Schein-Grün auf
versioniertem Beweisbestand (history_guard H6) gewesen.

## 2. Ursache in drei Schichten

| Schicht | Defekt | Wirkung |
|---|---|---|
| Daten | Folgeentscheidungen wurden in bestehende Listeneinträge **eingehängt** (Writer-Fehler beim Anfügen) | 20 Entscheidungen unsichtbar; Eintrag widerspricht sich selbst |
| Leser | `yaml.safe_load` überschreibt doppelte Schlüssel **still** | Der Fehler wurde zur „Fachmeinung" umgedeutet statt als Strukturfehler zu scheitern |
| Tests | `test_faktenfrische_823` las `queue = ROOT / 'data' / …` und rief `.get()` auf einem `Path`; beide #763/#823-Tests trugen noch den alten `offen`-Vergleich samt drei Docstrings in einer Methode | `AttributeError` + Fehlalarm auf `main` – **jeder** PR rot (#1126) |

## 3. Was jetzt gilt (vier Schichten, eine Regel)

### 3.1 Fail-closed-Leser (`StrengerLoader`)

`entscheidungen_laden()` liest die Akte über einen Loader, der einen doppelten
Schlüssel **laut** ablehnt – mit Datei-Zeile und Heilbefehl. Ein solcher
Eintrag gilt nie mehr als „nichts gesehen"; er ist ein **Werkzeugbefund**.
Der stille Letzter-gewinnt-Leser existiert nur noch als `_laden_tolerant()`
für den Vorher/Nachher-Beweis im Heiler.

### 3.2 Beweisbarer Heiler (`--reparieren [--apply]`)

Der Heiler zerlegt jeden Listeneintrag an seinen doppelten Schlüsseln wieder
in eigenständige Entscheidungen. Er ist bewusst konservativ:

* **Kein Inhalt wird erfunden.** Beanstandung, Beleg, Person, Datum und
  Begründung bleiben zeichengenau.
* **Zuordnung nur mit Zeugen.** Ein herausgerissener Block hat keinen Slug und
  keine Befund-ID; er wird ausschließlich über seinen **Beanstandungstext**
  einem Ledger-Eintrag zugeordnet – und nur, wenn genau **ein** Eintrag passt.
  Sonst: `fail-closed`, kein Schreiben.
* **Nur verlorene Felder werden ergänzt** (Slug, Befund-ID, Befundfassung,
  geprüft-Fassung), und Kettenfelder nur, wenn sie fehlen
  (`kette_ergaenzt: true` dokumentiert das in der Akte).
* **Fragmente ohne Person/Begründung werden ausgewiesen und verworfen** –
  sie sind per Schema keine Entscheidung. Zusätzlich gilt: Ein verworfener
  Block darf **nie der jüngste Beleg** seines Befunds sein, sonst bricht der
  Heiler ab (Handprüfung statt Datenverlust).
* **Zwei Beweise vor dem Commit:** (1) jeder Block ist vorher/nachher
  feldgleich, (2) die Akte ist streng lesbar und alle Ketten stimmen. Schlägt
  eines fehl, werden die **Original-Bytes** zurückgeschrieben.

### 3.3 Kettenregel: Vorgänger muss existieren, nicht „der letzte" sein

Ein Anfügeprotokoll ist nicht streng chronologisch (zwei Personen bestätigen
denselben Text, ein Lauf zieht ältere Dokumentation nach). Verlangt wird
deshalb: Die `vorgaenger_geprueft_fassung` muss eine Fassung sein, die für
**diesen** Befund bereits dokumentiert wurde. Ein Vorgänger, den es in der
Kette nie gab, bleibt ein Strukturfehler.

### 3.4 Bildzeilen: Herkunft statt Wortlaut

`*Abbildung:`-Zeilen galten pauschal als abgeleitet. Damit fiel eine
**handgeschriebene** Unterschrift mit Prozentwert still aus dem Aussage-Hash –
die Entscheidung wäre blind geblieben. Jetzt zählt die Herkunft: Der Ableiter
schreibt „(eigene Darstellung …)" in die Zeile (bzw. das dokumentierte
Altformat „Gliederung zu … – N Stationen von … bis …"). Alles andere ist
Redaktion und bleibt gebunden. **Beweis, dass das nichts verschiebt:** Alle 40
Bildzeilen des Bestands tragen den Vermerk; die Zahl der offenen Befunde
bleibt bei 24 (vorher/nachher gemessen).

## 4. Automatische Selbstheilung (eingehängt, nicht nur dokumentiert)

| Lauf | Schritt | Wirkung |
|---|---|---|
| `release-scorecard.yml` | „Schließakte strukturell heilen (Selbstheilung, fail-closed)" **vor** jeder Messung: `--selftest` → `--reparieren --apply` → `--struktur-pruefen` | Die Scorecard misst nie mehr auf einer unlesbaren Akte; die Heilung wird mitcommittet |
| `befund-akte-nachziehen.yml` | gleicher Schritt **vor** dem Erzeugen der Akte, eigener Commit-Pfad für die Akte | Push auf `main` heilt die Struktur und zieht die Akte nach (#1120) |
| `faktenfrische.yml` | Heilung **vor** der Dossier-Nachlese, Akte im Commit-Pfad | Der Tageslauf kann keine neue Struktur-Korruption festschreiben |

Jeder dieser Läufe ist **idempotent**: ein zweiter Lauf ohne Defekt schreibt
nichts (`strukturfehler == 0`). Ein doppelter Schlüssel ist ab jetzt in jedem
Lauf Exit 1 – nie wieder „grün, weil unlesbar".

## 5. Verifikation (lokal nachgefahren)

```
$ python3 scripts/faktenfrische_befund_ledger.py --reparieren --apply
✅ 20 verlorene Folgeentscheidung(en) wieder als eigener Listeneintrag geführt
   (187 Entscheidungen gesamt).

$ python3 scripts/faktenfrische_befund_ledger.py --struktur-pruefen
✅ Schließakte strukturell sauber (187 Listeneinträge, keine doppelten Schlüssel).

$ python3 scripts/faktenfrische_befund_ledger.py --wache
Offene Fachbefunde: 24 auf 7 Seiten · überholte Fassung: 16 · ohne Fassung: 0
✅ Jeder offene Befund hat einen Schließweg (eine menschliche Entscheidung am
   heutigen Text).

$ python3 scripts/faktenfrische_befund_akte.py --schreiben
✅ BEFUND-AKTE.md geschrieben: 24 offene Befunde auf 7 Seiten (5 live),
   ältester 5 Tage, Frist 14 Tage, 0 über der Frist.

$ python3 scripts/veroeffentlichungs_wache.py --wache
✅ Nachlauf-Wache grün: Frontmatter, Metadaten, Register, Akte und Kanaltreue
   stimmen.
```

**Semantik-Beweis der Reparatur** (nicht nur „läuft durch"): Für alle 146
Befund-Schlüssel ist die jüngste Entscheidung dieselbe wie vor der Reparatur –
mit **zwei richtigen Ausnahmen**, und genau das war der Defekt:

| Befund | vor der Reparatur | nach der Reparatur | Beleg |
|---|---|---|---|
| `2026-10-07-campingurlaub…` · `3716cfd3` | `3b3904ec` (falsch: Fassung des Vorgängers) | `b2693d4a` | Beanstandung nennt Verbraucherzentrale/Buchungsangaben |
| `2026-09-23-5-einfache-frugalismus…` · `f83f21c1` | `b2693d4a` (fremde Fassung aus dem Camping-Artikel) | `16af0cf1` | eigene Beanstandung: Nahrungsmittel-Inflation |

**Tests:**

| Suite | Ergebnis |
|---|---|
| `scripts.tests.test_faktenfrische_befund_ledger` (20 Tests) | **OK** (vorher 1 Failure, 3 Errors) |
| `test_faktenfrische_763` + `…_823` | **OK** (29 Tests, 1 Skip) |
| `discover -p 'test_faktenfrische*.py'` | **256 Tests OK** |
| `faktenfrische_befund_ledger.py --selftest` | **OK** – inklusive neuer Proben: doppelter Schlüssel scheitert laut, Heiler trennt beweisbar, Fragment ohne Person wird ausgewiesen, zweiter Lauf ändert nichts |
| `governance_contract.py --selftest` (C1–C49) | **OK** |
| Alle 102 Workflows | YAML-valide |

## 6. Was ausdrücklich **nicht** maschinell entschieden wurde

* **#1107 Kadenz-Horizont** – der Takt/Intervall-Korridor bleibt
  Herausgeber-Entscheidung (`docs/ANLEITUNG-FAKTENFRISCHE.md`). Die Wache
  meldet, sie entscheidet nicht.
* **#1028 KI-VO** – das Gate heilt, was mechanisch heilbar ist (Anker,
  RSS-Spiegel, unmarkierte Ableitungen). Die 12 offenen `menschlich`-Einträge
  im Register (`data/ki_kennzeichnung.yaml`, Frist 02.12.2026) brauchen den
  Betreiber: Ob ein Mensch die redaktionelle Verantwortung übernommen hat,
  kann keine Maschine belegen.
* **#448 Pinterest** – Domain-Sperre, Kanal geparkt; Runbook
  `docs/PINTEREST-SPIELBUCH.md`.
* **#1137 Reserve-Zertifikat veraltet** – die Heilung ist der reguläre
  `content-reserve.yml`-Lauf (03:25 UTC) mit `reserve_readiness.py`; das
  Zertifikat wird erst nach vollständiger Messung neu versiegelt. Lokal ist
  die Messung ohne Hugo nicht beweisbar (`hugo fehlt im PATH`) – sie darf
  deshalb hier nicht „nachgestellt" werden.

## 7. Betriebsregeln für die Zukunft

1. **Ein Listeneintrag, eine Entscheidung.** Angehängt wird immer als neuer
   `- slug:`-Block, nie als Feldblock in einem bestehenden Eintrag.
2. **Doppelter Schlüssel = Werkzeugfehler**, nicht „letzter gewinnt".
3. **Kein Freibrief durch Reparatur:** Der Heiler ändert nur Struktur und
   fehlende Felder; er schließt und öffnet keinen Befund fachlich.
4. **Wer heilt, beweist:** Vorher/Nachher-Gleichheit aller Blöcke plus
   strenges Nachlesen – sonst Rollback auf die Original-Bytes.

---

# Nachtrag (zweiter Befund): die rote CI war ein kaputter Merge – nicht ein Testfehler

Beim Warten auf den `regression`-Job des PR fiel auf: Der Job war **auch auf
`main` rot**, und zwar nicht wegen der zwei bekannten #763/#823-Tests allein.
Lokal (voller Lauf, `discover -s scripts/tests`, 5674 Tests) waren es
**7 Failures und 3 Errors** – und alle zehn waren mit `git worktree` auf dem
Basis-Commit `d0828dc` reproduzierbar. Sie stammten also nicht aus diesem PR.

## 1. Die Ursache: ein Merge, der zwei Stände halb zusammengeführt hat

Am 07.11.2026 liefen **zwei** Vorgänge parallel am selben Werkzeug:

* `WF-3150 / #1030` – Selbstheilung: eigener Heilschritt, 18 Selbsttest-Gruppen
  (`WARTUNG-BACKUP-WF-3150-1030-SELBSTHEILUNG-HIGHEND-2026-11-07.md`).
* `WF-9E5A / #923` – Messhöhe: Klassen `scheduler`/`leerlauf`/`scheinbeweis`/
  `einrichtung`, Job-Ebene, Zeugen-Filter, Exit 3/4, `--vertrag`, `--plan`
  (`WARTUNG-BACKUP-WF-9E5A-HIGHEND-2026-11-07.md`).

In `main` landeten **die Verbraucher des zweiten Vorgangs** (Workflow-Schritt,
Alerting-Klasse `backup-leerlauf`, Simulationsszenarien, 11 Vertragstests) –
**aber nicht das Modul**. `scripts/backup_selbstheilung.py` ist der Stand des
ersten Vorgangs: kein `KLASSEN`, kein `pruefe_leerlauf`, kein `_zeugt_lauf`,
kein `--vertrag`, kein Exit 3/4. Zusätzlich standen danach **zwei** Schritte im
selben Job, die beide `--heilen` aufriefen.

Das erklärt jeden einzelnen der zehn Fehlschläge:

| Fehlschlag | Ursache |
|---|---|
| `AttributeError: KLASSEN` / `pruefe_leerlauf` | Modul ohne die 07.11-Funktionen |
| `erwartet genau einen Schritt mit „Selbstheilung“` (2 ≠ 1) | zwei Heilschritte im Job |
| `--vertrag` in `backup-frischwache.yml` | Flag existierte nicht → der tägliche Selbsttest-Schritt wäre rot geworden |
| `#1030-Gegenprobe` in der Simulation | Alerting las **jedes** „Selbstheilung“ als Leerlauf |
| `test_keine_github_expression_in_run_bloecken` | `${GITHUB-OUTPUT}` direkt im `run:` von `ki-provenienz-wache.yml` |

Der `--vertrag`-Fall ist der ernsteste: Er wäre nicht im PR aufgefallen, sondern
erst im **nächtlichen** Lauf – ein Selbsttest, der das Werkzeug prüft, das ihn
nicht kennt.

## 2. Was jetzt gilt (und was der Vertrag prüft)

* **Ein Schreiber.** Genau ein Schritt ruft `--heilen` (Dispatch-Recht,
  `AKTION_TOKEN`). Der zweite, gleichnamige Schritt ist jetzt eine **lesende**
  Prüfung: `Leerlauf prüfen – grüner Lauf ohne Sicherung (fail-closed)` mit
  `--leerlauf`. Zwei Heilschritte hätten im selben Lauf zweimal anstoßen können;
  der Test hält die Zahl der Schreiber fest (`--heilen` genau einmal).
* **Die Klasse hängt am Wortlaut, nicht an der Stimmung.** Das Alerting liest
  `Leerlauf prüfen` → `backup-leerlauf`, `Selbstheilung` → `backup-frisch`.
  Vorher verschluckte der Leerlauf-Rat jeden Werkzeugfehler der Heilung.
* **Die Messhöhe ist Vertrag.** `_zeugt_lauf()` überspringt `skipped`-Läufe mit
  0 Schritten (live belegt: Lauf 42386235574); `pruefe_leerlauf()` misst den Job
  `backup`, **nie** den KV-Job; `pruefe_scheinbeweis()` macht aus einem
  übersprungenen Rückweg-Nachweis einen Befund.
* **Der Klassenvertrag ist ausführbar.** `--vertrag` gibt die vier Klassen aus
  und endet rot, wenn mehr als `scheduler` heilbar wäre. `--plan`/`--leerlauf`
  lesen nur; Exit 3 (Einrichtung, Vorrang) · 4 (Leerlauf) · 1 (Scheinbeweis) ·
  2 (Werkzeugfehler) – dieselbe Sprache wie das Alerting.
* **Kein neuer Endpunkt.** Der Jobs-Aufruf nutzt die von GitHub gelieferte
  `jobs_url`; die Endpunkt-Liste bleibt bei drei Pfaden, `POST` nur auf
  `/dispatches`.
* **Kein Geheimnis in der Prüfung.** `pruefe_leerlauf()` bekommt nur
  **Anwesenheit** (`ziel_gesetzt`, `pflicht_gesetzt`), nie Werte – die
  Klartext-Wache (`FLUSS`) hat die erste Fassung sofort beanstandet, und sie
  hatte recht.
* **Die Simulation testet das, was läuft.** Die Attrappe für
  `github.rest.actions.getWorkflowRun` fehlte; die Verhaltens-Probe landete
  dadurch im Fehlerpfad (`fail-open`) statt in der Regel (Live-Nachladen des
  Abschlusszustands, Phantom-Filter WF-A3AD/#604).

## 3. Nachweise (lokal gefahren)

| Prüfung | Ergebnis |
|---|---|
| `unittest discover -s scripts/tests` | **2** Fehlschläge (vorher 10) – beide **nicht** inhaltlich: der Feed-Test misst `public/` (lokal ohne Hugo-Build nicht beweisbar; in CI gebaut) |
| `test_backup_einrichtung` + `test_backup_selbstheilung` | **109 Tests OK** (vorher 75 + 3 rote) |
| `test_alert_scoping` (inkl. node-Simulation, 80 Szenarien) | **32 Tests OK** |
| `backup_selbstheilung.py --selftest` / `--vertrag` | **21 Fallgruppen** / Vertrag eingehalten |
| `clear_text_logging_guard.py` | **0 Befunde im Hauscode** |
| `trigger_wache --check` · `workflow_vertrag_wache --gate` · `skript_syntax_wache --check` · `wachen_vertrag` · `workflow_js_wache --check` | alle grün (102 Workflows) |
| `governance_contract.py --selftest` (C1–C49) | OK |

## 4. Die Lehre

Ein Merge, der **Aufrufer** übernimmt und **das Werkzeug** nicht, sieht grün aus,
weil niemand die Aufrufer mehr ausführt, bis der Scheduler es tut. Was das
verhindert, ist nicht mehr Sorgfalt, sondern ein **Selbsttest des Werkzeugs im
Workflow** (`--selftest`, `--vertrag`) *vor* der Heilung – und ein Vertrag, der
die Zahl der Schreiber prüft. Beides steht jetzt im Lauf.

## 5. Der rote Deploy (#1129) – ein Prüfstand ohne einen Baustein

Der Deploy auf `main` war seit `d0828dc` rot: Schritt „KI-Transparenz – Text,
Bild und Provenienz testen“, Job `Auslieferungs-Siegel` als Folge. Die Logs
sind aus der Sandbox nicht abrufbar (results-receiver gesperrt) – also wurde
der Befund **nachgebaut** statt geraten: Hugo 0.168.0 extended aus dem
PyPI-Paket `hugo` installiert (dieselbe Zweitquelle, die
`.github/actions/install-hugo` benutzt), echter Build, dann derselbe Befehl wie
im Workflow.

**Ergebnis (rot, reproduziert):**

```
ERROR error building site: render: … partial "_funcs/ki_modalitaeten.html" not found
```

`test_ki_provenienz_render` baut ein Mini-Site mit den **echten** Vorlagen –
aber seine Liste `TEILVORLAGEN` nannte nur vier. Der Umbau vom 07.11.2026 hatte
die Modalitäten-Logik in den Helfer `_funcs/ki_modalitaeten.html` ausgelagert
(Single Source of Truth für Text/Bild/Ton, Verbraucher: `ki_provenienz.html`
und der Feed). Der Prüfstand kannte den Helfer nicht – und weil Hugo fehlte,
war der Test **lokal übersprungen** (`skipUnless(hugo)`) und fiel erst im
Deploy auf. Ein übersprungener Test ist kein grüner.

**Heilung:** Der Helfer steht jetzt in der Liste (mit Begründung im Test).
Anschließend lief die Suite zum ersten Mal hier **vollständig mit Hugo**:
`Ran 5676 tests … OK (skipped=6)` – inklusive der Render-Verträge, die ohne
Hugo nie gelaufen waren.

**Nebenbefund, mitbehoben:** Die Notbremse des `regression`-Jobs stand bei 30
Minuten, während zwei volle Suiten allein 2 × 14m29s brauchen (gemessen). Lauf
`42504141712` wurde bei 30m0s als `cancelled` abgeschnitten – ein Gate, das
durch Rechenzeit rot wird, misst nicht den Code. Grenze jetzt 45 Minuten, mit
Messung und Begründung im Workflow.

## 6. `test_bestand_ist_gruen` – der Test, der an seiner eigenen Kante maß

Der zweite CI-Befund (Annotation aus dem Lauf, nicht aus dem Log – das Log war
aus der Sandbox nicht abrufbar):

```
AssertionError: 49 not greater than or equal to 50
```

Die Zusage lautete `feed_items_geprueft >= 50`, die RSS-Vorlage kappt aber
**genau bei 50** (`services.rss.limit`). Damit ist die Schwelle eine Messung
auf der Kante: Ein einziges Feed-Item, das keine Seite im Bestand hat, macht
aus 50 eine 49 – und die Meldung nennt nur die Zahl, nicht das Item. Die
Ursache war so aus dem Lauf nicht lesbar (und ist es bis heute nicht: das
Item wird im Gate **stillsch** übersprungen, `continue`).

**Heilung – strenger, nicht lockerer:**

* `regel_m5()` sammelt ungemappte Items und gibt sie zurück
  (`feed_items_ohne_seite`), statt sie zu verschlucken.
* Der Test prüft die eigentliche Zusage jetzt **namentlich**:
  `feed_items_ohne_seite == []` – ein Item ohne Seite ist eine Lücke in der
  Messung, kein Alias.
* Die Blindheitsschwelle sinkt auf `>= 25` und ist damit keine Kante mehr;
  die Zahl bleibt als „M5 ist nicht blind“-Nachweis erhalten.
* Der Selbsttest des Gates prüft den neuen Zähler mit (er hätte das stille
  Überspringen sonst nie bemerkt).

Der nächste rote Lauf nennt damit das Item beim Namen – oder er ist grün, weil
alle 49 Items belegt sind. Beides ist ehrlich; „49 < 50“ war es nicht.

## 7. Das Item hat einen Namen – und der Name zeigt auf ein Messproblem

Kaum nannte der Test das Item (`7b7318a`), lautete die Annotation aus Lauf
`42518243347` / Job `128855045803`:

```
AssertionError: Lists differ:
['2026-11-05-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen'] != []
```

Das ist der Beweis, dass die Diagnose-Kette funktioniert: aus `49 < 50` (nicht
handelbar) wurde ein Slug (handelbar). Und der Slug war **kein** Inhaltsfehler.

**Was das Item ist:** ein regulärer Beitrag mit `draft: true` und
`reserve: true` – also bewusst zurückgehalten, kein Defekt. Er steht nicht im
Feed (richtig, `buildDrafts = false`), das Gate meldet nur, dass ein
Feed-Item keine Seite im Bestand hat.

**Die eigentliche Ursache war Zeit, nicht Inhalt.** Der `regression`-Job baute
`public/` in Schritt 6. Danach liefen die KI-Cover-Provenienz und der
Reserve-Snapshot – beide **ändern `data/`**. Die Suite in Schritt 11 maß damit
ein Messobjekt, das älter war als der Baum, aus dem es stammte. Ein
Nachbau mit demselben Baum liefert `feed_items: 50`, `feed_items_ohne_seite:
[]`, 109/109 Seiten. Gegenprobe: `ki_cover_provenienz.py --gate` und
`automation_premium_audit.py --strict` verändern unter `content/` nichts – der
Baum war unschuldig.

**Heilung:** neuer Schritt **„Prüf-Build vor der Suite (gleicher Stand wie die
Messung)“** unmittelbar vor der Suite, über dieselbe Aktion wie der Deploy
(`./.github/actions/hugo-build`, `--minify --destination public
--cleanDestinationDir`, ~3 s). Damit gilt: was gemessen wird, ist der Stand, der
gemessen werden soll. In Lauf `42524620687` waren Schritt 10 (Prüf-Build) und
Schritt 11 (Code-Regression) zum ersten Mal grün.

**Die Regel dahinter (generalisierbar):** Ein Gate darf sein Messobjekt nicht
vor den Schritten bauen, die den Baum verändern. Wer ein Artefakt vor der
Messung erzeugt, muss es vor der Messung neu erzeugen – oder die Messung
deklariert, auf welchem Stand sie läuft.

**Fallstrick, dokumentiert, weil er fast zur Fehldiagnose geführt hätte:** Ein
`hugo --buildDrafts`-Build ist **kein** Beweis. Er zeigt 22–28 Items statt 50,
weil das Feed `where site.RegularPages "Section" "posts"` nimmt und Entwürfe
die Liste verschieben – daraus wurden scheinbar 22+ Items „ohne Seite“. Feed-
Messungen nur auf einem normalen Build (`buildDrafts = false`) beurteilen.

**Nebenbefund, mitbehoben:** Die Uhr-Probe meldete nur `exit code 1`. Sie
schreibt jetzt nach `/tmp/uhr.log`, zeigt `tail -80`, und setzt pro
FAIL/ERROR eine eigene Annotation `::error title=Uhr-Probe::<name>`; der
Exit-Code wird durchgereicht (`c4ae916`). Dieselbe Regel wie in §6: ein rotes
Gate nennt seinen Zeugen.
