# Blockaden der Auslieferung – Blustradius, Siegel, Messkette

> Wörtlich aus `CLAUDE.md` übernommen am 01.11.2026 (Skill-Umbau). Kein Satz wurde umformuliert, gekürzt oder erfunden; die Überschriften sind eine Ebene tiefer gehängt. Änderungen hier sind Änderungen am Regelwerk – sie brauchen denselben Nachweis wie vorher: Selbsttest der betroffenen Wache, dann Commit.

### Ein Befund darf nicht die ganze Seite einfrieren (Blustradius, C34, seit #676, 09.10.2026)

Am 09.10.2026 meldete der Bot-Watchdog `P1 · Neuester Artikel nicht live`:
`campingurlaub-2026` lieferte HTTP 404. Der Artikel war gesund, `draft: false`,
fertig gebaut. Er war nur nie ausgeliefert worden – weil **jeder** Deploy seit
02:12 UTC rot war (13 Fehlschläge in Folge, letzter grüner Lauf
`37851368576`). Rot wurde der Schritt `Release-Scorecard` mit Exit 1, alles
dahinter fiel aus, auch `pages-deployment`.

Der Auslöser war ein einziger Satz in einem **anderen** Artikel: Der End-CTA von
`7-gewohnheiten-…` (Z. 216) war wortgleich mit `etf-sparplan-…` (Z. 164) – und
beide waren richtig, weil `cta_builder.cta_end_block()` sie aus derselben
Vertrags-SSOT erzeugt. Die Duplikat-Wache maß Haus-Format als Inhaltsklau
(`RD1-duplikate`, `wirkung: blockiert`). Der Befund war echt, die **Wirkung**
war falsch: Ein Artikel mit einem Format-Befund fror die Auslieferung aller 75
Artikel ein. Der Deploy-Catchup wiederholte stündlich denselben Fehlschlag,
denn er baute neu, ohne die Ursache zu berühren.

Vier Schichten halten die Klasse jetzt:

- **Die Ausnahme kommt aus der Quelle, nicht aus einer Liste.**
  `duplikat_guard.py` erkennt Haus-Templates aus `affiliate_intent_contract`
  (CTA-Register), `ki_shared.DISCLAIMER`, `cta_builder.END_DISCLOSURE` /
  `_END_SATZ_FALLBACK` und `news_writer.STAND_INTRO` (Formel mit `{today}`).
  Eine Whitelist hätte denselben Widerspruch beim nächsten Partner neu
  erzeugt. **Gelesen wird per AST, nicht per Import:** `ki_shared`,
  `cta_builder` und `news_writer` ziehen PyYAML nach – ohne AST-Lesart fiele
  die Ausnahme in jeder pyyaml-freien Umgebung *still* aus und #676 käme als
  Dauer-Fehlalarm zurück. Eine nicht lesbare Quelle ist darum ein
  Werkzeugfehler (Exit 2, `haus_template_luecken()`), nie ein Verzicht.
  Normalisiert wird über `affiliate_intent_contract.norm()` – dieselbe
  Vergleichsform wie die Intent-Wache (der weiche Bindestrich U+2011 war die
  Unsichtbarkeits-Ursache).
- **Ausnahmen sind sichtbar.** `haus_template_grund()` nennt die Quelle im
  Report. Eine stille Ausnahme wäre Scheingrün (Lektion #521, C19). Ein
  einziger Redaktionssatz hebt jede Ausnahme auf – die Wache wird nicht blind.
- **Blockiert heißt isoliert, nicht gestoppt.** `scripts/release_isolation.py`
  nimmt blockierte Kandidaten aus der Auslieferung (`park_state.hold()` –
  **nie** `park()`, Frontmatter-only, mit `cadence_grund`, der die Check-ID
  und #676 nennt), füllt die Quote nach (`refill_until_min(finalize=False)`),
  baut neu und misst **über dieselbe Scorecard-Engine** nach. Begrenzte
  Runden (`--runden`, `MAX_ISOLATIONEN_PRO_LAUF = 6`), Exit `0` ausgeliefert /
  `1` weiterhin blockiert / `2` Werkzeugfehler. Bei Werkzeugfehler greift die
  Isolation bewusst nicht: Sie würde sonst auf einer Messung handeln, die
  nichts gemessen hat (C33). Verdrahtet in `deploy.yml` **vor** dem
  Heal-Diff/Rebuild; die Scorecard bleibt der harte Endpunkt – ohne
  `|| true`, ohne `continue-on-error`.
- **Der Alarm nennt die Ursache, nicht das Symptom.** `bot_watchdog.py`
  schreibt bei `live-site` die Deploy-Ausfallspur dazu: fehlender Workflow,
  Anzahl aufeinanderfolgender Fehlschläge, Job, Schritt, Run-ID – und den
  Hinweis, dass ein Catchup denselben Fehlschlag wiederholt. Live geprüft:
  `laeufe_fehlend: 13`, Job `deploy`, Schritt `Release-Scorecard
  (Produktionswahrheit versiegeln, fail-closed)`, Run `37963585911`.
- **Dasselbe gilt auf der Prüfebene.** `publication-reliability-tests.yml`
  ist der einzige Workflow mit vollständiger Unit-Test-Suite. Sein erster
  fachlicher Schritt prüft einen **Daten**-Zustand
  (`reserve_artifacts.py --check`); war der rot, wurde die Suite `skipped` –
  und es lief im ganzen Repo kein Regressionstest mehr, auch die neuen nicht.
  Die vier Prüf-Schritte tragen jetzt `if: ${{ !cancelled() }}`: Der Job
  bleibt über den Daten-Befund rot (fail-closed, #634, kein `|| true`), aber
  er liefert wieder Signal. Ein Befund über einen Zustand darf die Prüfung
  des Codes nicht einfrieren.

Dazu repariert: `release_scorecard.bewerte_artikel()` hatte einen `NameError`
bei einer nicht deklarierten Check-ID – roher Traceback, Exit 2, blockierter
Deploy. Eine Messregel kann nicht gleichzeitig Messung und Absturz sein.

Bedienung: `npm run release:isolation` (Trockenlauf) ·
`npm run release:isolation:probe` · `npm run test:isolation` ·
`npm run duplikate:check` · `npm run test:duplikate`. Runbook:
`docs/ANLEITUNG-AUSLIEFERUNGS-ISOLATION.md`. Regression:
`scripts/tests/test_release_isolation.py` (21) ·
`scripts/tests/test_duplikat_guard.py` (23, davon 2 nur mit PyYAML).
Vorgangsbericht: `WF-A535-676-DAUERHEILUNG-PREMIUM-2026-10-09.md`.

Vertrag: **C34** in `governance_contract.py` (Isolations-Bausteine · `hold`
statt `park` · Messung über die Scorecard · Exit-Werkzeugfehler ·
Verdrahtungs-Reihenfolge in `deploy.yml` ohne Still-Schalter ·
Ausfallspur im Watchdog · SSOT-Haus-Templates statt Whitelist · beide Wachen
in `GUARDS` mit Regressionstest und Runbook · Suite läuft auch nach einem
Daten-Befund).

### Auslieferung vor Siegel (kein Mess-Schritt blockiert die Live-Site, C34, seit #676, 10.10.2026)

Am 09.10.2026 fror die öffentliche Auslieferung **19 h 38 min** ein: Der
`deploy`-Job scheiterte 20× in Folge am Schritt „Release-Scorecard
(Produktionswahrheit versiegeln, fail-closed)" – einem **Beweislauf**, der vor
der Auslieferung steht. Die Schritte 50–60 sprangen, inklusive „Artefakt für
offizielles Pages-Deployment hochladen"; `pages-deployment` startete nie. Der um
14:02 UTC veröffentlichte Artikel lieferte 4 h 11 min HTTP 404 (Ticket #676).

- **Ein Beweislauf wertet seinen Exit-Code aus.** `0` → weiter · `1` → echter
  Inhaltsbefund, harter Stopp (unverändert fail-closed) · `2` → **Werkzeugfehler**:
  die Messung ist kaputt, das ist kein Inhaltsbefund und darf die Auslieferung
  nicht als Geisel nehmen. Der Fehler wird Job-Output und `::error::`-Annotation.
- **Nach dem Auslieferungs-Beleg (`id: artefakt`, direkt nach
  `actions/upload-pages-artifact`) folgt im `deploy`-Job nichts mehr.** Jeder
  spätere Schritt wäre ein neuer Kandidat für dieselbe Blockade. Meldeschritte
  gehören hinter die Veröffentlichung.
- **Das Siegel liegt danach:** Job `release-seal` (`needs: [deploy-gate, deploy,
  pages-deployment]`, `if: always()`) macht den Lauf rot, wenn der Beleg fehlt,
  der `deploy`-Job vor der Auslieferung abbrach oder die Scorecard einen
  Werkzeugfehler meldete. Fail-closed bleibt erhalten – nur die Reihenfolge
  stimmt: **erst liefern, dann siegeln.** `release-seal` ist bewusst kein
  `needs`-Vorlauf von `pages-deployment`.
- **Die Wache nennt die Ursache.** `bot_watchdog.classify_deploy_jobs()` erkennt
  am deploy-Job, ob die Auslieferung blockiert ist, und benennt den blockierenden
  Schritt (`CHECK3B`, Befund `deploy-blockade`) – unabhängig vom HTTP-Status,
  damit eine eingefrorene Site auch ohne neuen 404-Artikel auffällt (Klasse #537).
- **Der Befund heilt sich selbst:** `watchdog_recovery.py --live-site` löst
  `deploy-catchup.yml` aus, aber **nicht** in eine blockierte Kette (Exit 3 – der
  Dispatch scheiterte am selben Schritt) und nie doppelt. Die Nachmessung deckt
  `CHECK3`/`CHECK3B` ab, damit ein geheilter Befund kein Ticket erzeugt.
- Tests: `scripts/tests/test_deploy_publication_priority.py` (Reihenfolge,
  Exit-Zweige, Siegel-Job) und `scripts/tests/test_bot_watchdog_live_site.py`
  (Diagnose, Befund, Heiler). Vorgangsbericht:
  `BOT-WATCHDOG-676-DAUERHEILUNG-PREMIUM-2026-10-10.md`.

Vertrag: **C34** in `governance_contract.py` (Exit-Auswertung · Inhaltsbefund
stoppt weiter · nichts nach dem Auslieferungs-Beleg · Siegel nach der
Veröffentlichung · Ursachen-Nennung · Selbstheilung · Verdrahtung ·
Regressionstest).

### Eine Messkette gehört in jeden Lauf, der misst – und ein Crash ist ein Crash (Dauerheilung #740, 14.10.2026)

Am 14.10.2026 fror die öffentliche Auslieferung über 14 h ein (10 rote
`deploy.yml`-Läufe, nur ein grüner ohne neue Inhalte): Die Quote-Nachfüllung
muss an einem Publikationstag mit `live < Minimum` Reserve-Kandidaten **messen** –
und der `deploy`-Job trug die Messkette unvollständig (kein `hunspell`; die sechs
Schwester-Workflows der Kette hatten es alle). Dazu ein Doppelmodul-Bug:
`reserve_pool` importiert `publication_release` by name; in `__main__`-Ausführung
baut das eine **zweite Instanz mit eigener `ReleaseBuildCrash`-Klasse**, deren
Crash den `except`-Haken in `main()` verfehlte → roher Traceback, Exit 1 statt
des Diagnose-Vertrags (Exit 3). Der Schritt reichte den Exit unevaluiert durch →
geiselte die ganze Seite für ein kaputtes Messwerkzeug (Klasse #676).

- **Jeder Workflow, der `quality_score`/`spellcheck` ausführt, installiert
  `hunspell hunspell-de-de`** (apt, in der Abhängigkeits-Zeile, vor den Gates).
  Neue Workflows in der Messkette ohne die Zeile sind ein Audit-Befund.
- **Skripte, die als `python3 scripts/foo.py` laufen UND von Gate-Tools by name
  importiert werden, registrieren vor `main()` den Alias**
  `sys.modules['foo'] = sys.modules[__name__]` – sonst existiert pro Prozess eine
  zweite Instanz mit eigenen Exception-Klassen, und `except`-Haken fangen
  Import-Pfad-Crashs nicht (Selftest-Prüfung: Modul-Identität, Sektion 4 des
  `publication_release`-Selbsttests).
- **Auflösung von Defaults wie `validator or foo` gehört in den aufrufenden
  Prozess** (`refill_to_min` löst `accept_candidate` explizit auf), nicht in
  importierten Helfermodulen.
- **Schritte, die VOR der Auslieferung stehen und MESSEN (statt Inhalten
  zu heilen), werten ihren Exit-Code aus** (0/1/sonst) wie der Scorecard-Schritt:
  Werkzeugfehler → `::error::` + Job-Output, Auslieferung läuft weiter,
  `release-seal` macht den Lauf NACH der Veröffentlichung rot. Kein
  `continue-on-error`, kein `|| true` – Auswertung statt Durchreichen (C34).
- **Ein roter Schritt benennt die Ursache** (`Ursache: <Exception>`): Der
  `ReleaseBuildCrash`-Haken in `main()` druckt sie für jeden Crash-Pfad, nicht
  nur für `build_site()` (WF-A535-Lektion).

Tests: `scripts/tests/test_publication_release_wache.py`
(`DoppelmodulRegressionTests`, `DeployQuoteRefillVerdrahtungTests`) + Selftest-
Sektionen 4–6. Vorgangsbericht:
`BOT-WATCHDOG-740-DAUERHEILUNG-PREMIUM-2026-10-14.md`.

### Werkzeug blockiert nie die Auslieferung (C38, seit #740 Teil 2, 14.10.2026)

Drei Stunden nach der ersten Heilung meldete der Watchdog #740 erneut: wieder
eine eingefrorene Live-Site, wieder ein Mess-Schritt, der kein Inhalts-Gate
ist. Die Lehre aus #676 war **einem** Schritt beigebracht worden (der
Release-Scorecard), nicht dem Job. Von 64 Schritten des `deploy`-Jobs konnten
60 die Auslieferung anhalten, ohne dass irgendwo stand, ob sie das dürfen. Eine
Heilung, die nur den Schritt repariert, der gerade gebrannt hat, ist keine
Dauerheilung – sie ist eine Warteschlange.

- **Jeder Schritt kennt seinen Blustradius.** `data/blustradius-deploy.yml`
  deklariert alle Schritte des `deploy`-Jobs mit Klasse und Begründung:
  `infra` (ohne ihn gibt es keine Auslieferung) · `inhalt` (fachliches Gate,
  darf hart stoppen) · `gate-selbsttest` (fail-closed gewollt) · `werkzeug`
  (Mess-/Melde-Schritt, **darf nie** blockieren). `scripts/blustradius_register.py
  --check` prüft Register gegen Workflow: ein neuer Schritt ohne Eintrag ist
  ein Befund, kein Zufall – und ein `werkzeug`-Schritt, der hart aussteigt,
  ebenfalls.
- **Ein Meldeweg für alle.** `scripts/werkzeugbefund.py --melden <schritt>
  <grund>` schreibt in EINEN Sammelkanal, der Sammelschritt
  (`id: werkzeugbefunde`, vor dem Artefakt-Upload) macht daraus EIN Output-Paar
  (`werkzeugbefunde`, `werkzeugbefunde_anzahl`), und `release-seal` macht den
  Lauf **nach** der Veröffentlichung rot. Pro Schritt ein eigenes
  `*_werkzeugfehler`-Output zu bauen, war die Copy-Paste-Klasse hinter dem
  Ausfall; der Melder endet grundsätzlich mit Exit 0 (#227).
- **Kein Messlauf ohne sein Werkzeug.** `scripts/measurement_chain.py` ist die
  SSOT der Messkette (Binary, Wörterbuch, Installationszeile).
  `--audit-workflows` liest ALLE Workflows und meldet jeden Job, der ein
  registriertes Mess-Skript aufruft, ohne die Kette vorher im selben Job zu
  installieren (`--selftest`-Aufrufe zählen nicht: Selbsttests laufen mit
  Attrappen, vgl. KI-Probe #138). Das hat sofort einen zweiten, unsichtbaren
  Fall gefunden: `frankautoops-report.yml` maß die Qualitätskennzahl des
  **gesamten Bestands** täglich ohne `hunspell` – jeder Artikel fiel still auf
  „Rechtschreibung unbekannt" zurück. Eine tote Messung ist gefährlicher als
  keine: Sie liefert eine Zahl.
- **Der Vorflug fragt vorher.** `refill_to_min()` ruft `measurement_chain.require()`
  VOR dem ersten Kandidaten: Der Befund heißt dann „hunspell fehlt,
  Installation: `sudo apt-get install -y -qq hunspell hunspell-de-de`" (Exit 3),
  statt nach Vorheilung und Hugo-Build als Traceback aufzuschlagen.
- **Der Watchdog urteilt, statt zu fragen.** `bot_watchdog.blockade_klasse()`
  schlägt den blockierenden Schritt im Register nach; das Ticket nennt die
  Klasse und den nächsten Schritt (Werkzeug → Exit-Code auswerten und melden ·
  Inhalt → Fachkanal, kein Catchup · Infra → erst Werkzeug, dann Catchup ·
  unbekannt → Register nachtragen). Ein Ticket, das fragt „darf das
  blockieren?", erzieht zum Wegsehen (WF-A535 #529).
- Tests: `scripts/tests/test_blustradius_register.py` (19 – inkl. Ausführung der
  ECHTEN `run`-Blöcke aus `deploy.yml` gegen Attrappen),
  `scripts/tests/test_measurement_chain.py` (23),
  `scripts/tests/test_werkzeugbefund.py` (7).

Vertrag: **C38** in `governance_contract.py` (Register vollständig · zwei
Ausgänge · ein Meldeweg · Messkette verdrahtet · Watchdog urteilt ·
Regressionstest) – mit fünf Sabotageproben im Kontrakt-Selbsttest.

### Ein wartender Deploy ist kein grüner Deploy (WF-829B/#922, 01.11.2026)

Der Vorgang #922 bestand bis zum 31.10. aus einer richtigen Entscheidung
(„kein Worker-Deploy ohne nachgewiesene Produktionsfreigabe“) und einem
Zustand, den das Repository nicht herstellen kann: `cloudflare-produktion`
trägt seit seiner automatischen Anlage am 25.10.2026 13:20:15 UTC
`protection_rules: []`, `deployment_branch_policy: null` und
`can_admins_bypass: true`. Ein Schreibversuch mit dem Agenten-Token endet
mit HTTP 403 (gemessen am 30.10. und erneut am 01.11.2026) – „Resource not
accessible by integration“ ist ein **Rechtebefund**, keine Code-Regression.
Der Schalter bleibt ein Handgriff im Dashboard; alles andere ist vorbereitet.

- **Die zweite Stufe hat einen stillen Preis.** Mit Required Reviewer und
  abgeschaltetem Admin-Bypass hält jeder Deploy an, bis ein Mensch freigibt.
  Ein solcher Lauf wird **nicht rot**, meldet nichts und belegt dabei den
  Concurrency-Slot `worker-deploy`; der nächste Push reiht sich dahinter ein,
  und der Nachweis für #922 entsteht nie. Genau das ist die Lehre vom
  24.10.2026 in neuer Form: nicht der laute Ausfall fehlt, sondern der leise.
- **Die Wache:** `scripts/worker_freigabe_wache.py` liest ausschließlich die
  Läufe von `worker-deploy.yml` und `worker-zugang-pruefen.yml`
  (`actions: read`), bewertet `waiting`/`pending`/`action_required` gegen eine
  Schwelle (Standard 120 Minuten) und nennt Alter und Lauf-Link. Junge Wartung
  bleibt still; über der Schwelle ist es eine Warnung mit Schließpfad
  (freigeben oder abbrechen), unlesbare Antworten sind Exit 2 (C33).
  Lauf-Links werden aus geprüfter Repository-Angabe und geprüfter Lauf-ID
  gebaut, nie aus der API-Antwort übernommen; das Token steht nur im Header.
- **Einordnung:** Warnstufe statt Rot, weil ein wartender Lauf kein Defekt ist,
  sondern eine offene Entscheidung – rot ohne Schließpfad wäre der Dauer-Alarm,
  den C14 verbietet. „Nicht belegbar“ bleibt dagegen rot.
- **Vertrag:** `worker_freigabe_wache.py` steht im vertraglichen Minimum
  (GUARDS/C6), ihr Selbsttest (20 Fälle) und 23 Vertragstests laufen im
  Sicherheits-Lauf mit; `test:sicherheit`, `npm run worker:freigabe`,
  `npm run test:worker:freigabe` und der tägliche Schritt „Wartende
  Deploy-Freigaben“ halten sie scharf.
- Runbook: `docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, A4 („Die Freigabe ist ein
  Klick“) und D2. Vorgang:
  `WARTUNG-VEROEFFENTLICHUNG-WF-829B-922-DAUERHEILUNG-HIGHEND-2026-11-01.md`.
- **Was #922 schließt:** zwei grüne Deploy-Jobs, nachgewiesen über
  `scripts/alert_resolve_gate.py` – nicht ein grüner Plan, nicht ein grüner
  Zugangs-Check und nicht ein grüner Freigabe-Bericht.
