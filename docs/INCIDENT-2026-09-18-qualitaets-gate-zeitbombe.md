# Vorfall-Bericht: „Qualitäts-Gate (Build + interne Links)" rot auf main — Selbsttest als Zeitbombe

**Datum:** 18.09.2026 · **Status:** behoben (dauerhaft, mit Wache und Eigenmeldung) · **Schweregrad:** mittel
(Gate blind + Produktionslauf verbrannt, **kein** Live-Schaden an Artikeln, Links oder Builds)

## Kurzfassung

Zwei Dinge sind passiert: Das Gate war rot — **und es hat niemanden alarmiert,
kein einziges Mal.** Obwohl `alert-on-failure.yml` dieses Gate ausdrücklich
überwachen soll, erzeugten **14 rote Gate-Läufe seit dem 05.09.2026 keine
einzige Meldung**; repo-weit kamen seit dem 08.09. nur 602 Alerting-Läufe auf 922
abgeschlossene Läufe gelisteter Workflows (~35 % der Ereignisse fehlen). Deshalb
meldet sich das Gate jetzt selbst.

Die **Ursache der Röte** ist ein Selbsttest-Fixture, das die Wanduhr zweimal las —
einmal zum Prägen, einmal zum Vergleichen. Ab dem 13.09. drifteten beide Lesungen
auseinander, am 18.09. riss die Erwartung. Dieselbe Bauweise lag schlafend in
`audio_coverage_check.py` (Zündung 24.12.2026), und die Wachen-Liste im Gate war
eine still veraltete Handkopie des Regelwerks (5 Wachen ungeprüft).

Behebungen: `scripts/selftest_clock.py` (verschiebbare Uhr + System-Uhr-Falle),
deterministische Fixtures in `draft_triage.py` und `audio_coverage_check.py`,
`scripts/selftest_runner.py` (Entdeckung aller Selbsttests aus dem Regelwerk statt
Handkopie), `governance_contract.GUARDS` als einzige Liste und
`.github/workflows/link-check.yml` ohne kopierte Wachen-Liste, dafür mit
Eigenmeldung. Die Uhr-Falle deckt die ganze Befallsklasse ab, nicht nur die zwei
bekannten Fälle. Zwei weitere Befunde kamen beim Einbau dazu: Verdrahtungs-Tests,
die Namen in der YAML suchten (F), und ein Regelwerk-Import, der eine
Schatten-Kopie lesen konnte (G) — beide vom neuen Nachweis selbst entdeckt.

## Was gemeldet wurde

| Lauf | Workflow | Auslöser | Commit | Ergebnis |
|---|---|---|---|---|
| [35312783057](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35312783057) | Qualitäts-Gate (Build + interne Links) | schedule 01:15 UTC (03:15 MESZ) | `83526d5` | ❌ Schritt „Governance-Selbsttests (alle Wachen)" |
| [35324109630](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/35324109630) | Content-Reserve (täglicher Vorrat) | schedule | `27da912` | ❌ Stufe 5, Issue [#310](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/310) |

Meldung im Run-Log, beide Male dieselbe:

```
::error::scripts/draft_triage --selftest fehlgeschlagen
🛑 draft_triage-Selbsttest FEHLGESCHLAGEN:
  - Auffrischungs-Hinweis macht einen reifen Entwurf kaputt
  - Entscheidungs-Zähler verbiegt sich: 2
```

## Was tatsächlich passiert ist

**Niemand hatte den Code geändert.** Der Selbsttest war am 12.09.2026 grün und
wurde von allein rot — sechs Tage später, am 18.09.2026.

`scripts/draft_triage.py --selftest` baute seine Prüf-Fixtures mit

```python
alt   = (today - datetime.date.fromisoformat(tag)).days      # today = 2026-09-12 (hart codiert)
stamp = os.path.getmtime(pfad) - alt * 86400                 # JETZT = echte Wanduhr
```

und verglich das Ergebnis gegen dasselbe hart codierte `today`. Solange beide
Uhren denselben Tag zeigten, ging die Rechnung auf. Ab dem 13.09. drifteten sie:

| Tag des Laufs | Drift | Fall „Auffrischung" (Soll 27 Tage) | Gate |
|---|---|---|---|
| 12.09.2026 | 0 | 27 → `VERWAIST` | 🟢 |
| 16.09.2026 | 4 | 23 → `VERWAIST` | 🟢 (Run 35061978142) |
| 17.09.2026 | 5 | 22 → `VERWAIST` | 🟢 |
| **18.09.2026** | **6** | **21 → `REIF`** (Schwelle ist `> 21`) | 🔴 Run 35312783057 |

Der Selbsttest maß also nicht die Wache, sondern den Kalender. Folgen:

1. **Qualitäts-Gate rot** — und zwar *vor* dem Hugo-Build: Die Schritte „Seite
   bauen", „Interne Links prüfen" und „Schema-/SEO-Gate" liefen gar nicht erst.
   Das Gate war an diesem Tag nicht „rot wegen eines Fehlers", sondern blind.
2. **Content-Reserve Stufe 5** brach nach 7:27 min ab (Issue #310), nachdem die
   Stufen 1–4 (Kandidaten, Veredelung, Produktions-Gates, Konvergenz) gelaufen
   waren — die teuerste Stelle der Kette für die billigste Zeile Code.
3. **Aussagekraft verloren:** Ein rotes Gate, dessen Ursache „heute ist der
   18.09." lautet, trainiert Alarm-Müdigkeit — derselbe Effekt, den der
   Governance-Vertrag wegen Report #206 überhaupt eingeführt hat.

## Ursachen und Nebenfunde (7 unabhängig voneinander)

| # | Befund | Wirkung | Klasse |
|---|---|---|---|
| A | `draft_triage --selftest`: Fixtures von der echten Uhr, Erwartung aus hart codiertem Datum | Gate ab dem 18.09. täglich rot | Zeitbombe (scharf) |
| B | `audio_coverage_check --selftest`: Fixture `2026-12-24-c` als „Zukunft" hart codiert | Ab dem **24.12.2026** täglich rot — Gate, Governance C6, Content-Reserve, Lesehilfen | Zeitbombe (schlafend) |
| C | Die Wachen-Liste im Gate war eine **Handkopie** von `governance_contract.GUARDS` und still veraltet: `readability_check`, `pinterest_auth`, `social_studio`, `alert_router`, `affiliate_integrity_gate` liefen im Gate nicht mit | 5 Wachen ungeprüft, obwohl das Regelwerk sie verlangt | Abtippen statt Ableiten |
| D | `publish_gate.py` und `affiliate_marketer.py` erwähnen `--selftest` im Kommentar, **implementieren es nicht** | Ein Aufruf mit der Flagge startet die Standard-Aktion. Während der Diagnose real ausgelöst: `publish_gate` stufte einen LIVE-Artikel (`2026-09-11-wlan-probleme-loesen-…`) auf `draft: true` herab, weil der lokale `public/`-Build älter war als der Bestand. Änderung zurückgenommen, Artikel unverändert live. | Prüf-Aufruf heilt (C15) |
| E | **Das rote Gate hat niemanden alarmiert — und zwar nie.** `alert-on-failure.yml` listet das Gate korrekt (Name geparst **und** byteweise identisch, 39 eindeutige Einträge, `types: [completed]`), aber: **14 rote Gate-Läufe seit dem 05.09.2026** (10 seit dem 08.09.: 3 × schedule, 2 × push, 9 × pull_request) — **kein einziges Issue** mit dem Alerting-Titel existiert, in keinem Zustand, zu keinem Zeitpunkt. Für die Fehlschläge Run 35188605416 (17.09. 06:09:36 UTC Ende) und Run 35312783057 (18.09. 05:56:34 UTC Ende) gibt es keinen Alerting-Lauf; der nächste lief 43 min später. Repo-weit dasselbe Bild: seit dem 08.09. stehen **922 abgeschlossenen Läufen** gelisteter Workflows (ohne 90 `skipped`) nur **602 Fehler-Alerting-Läufe** gegenüber — rund **320 Ereignisse (~35 %) kamen nie an**. Andere Workflows treffen es ebenfalls (Uptime-Monitor 70/70, Content-Reserve 8/8 in der Stichprobe), das Gate 0/14. | Rotes Gate = keine Meldung, reproduzierbar; der Betreiber erfuhr es durch Nachschauen | Monitoring blind (`workflow_run`-Zustellung) |
| F | **Zwei Unittests bewiesen die Verdrahtung mit einer Namens-Suche in der YAML** (`assertIn("newsletter_digest", link-check.yml)`). Als die Bash-Liste durch den Runner ersetzt wurde, fiel `test_newsletter_digest` aus (CI-Lauf 35333234041, Issue #312) – und `test_draft_triage` bestand **nur noch, weil ein YAML-Kommentar** den Namen erwähnte. | Ein Test, der rot wird, obwohl die Wache läuft; und ein Test, der grün bleibt, obwohl er nichts mehr beweist | Text statt Mechanismus |
| G | **`selftest_runner.regelwerk()` konnte das falsche Regelwerk lesen.** `sys.path.insert(0, ziel)` ist wirkungslos, wenn der Ziel-Ordner bereits in `sys.path` liegt (beim Runner immer: sein eigener Ordner) – ein vorher eingefügter Stub-Ordner bleibt dann vorn und seine `GUARDS` werden als die echten gelesen. | SSOT-Abgleich gegen eine fremde Liste, unbemerkt | Gefunden vom neuen Verdrahtungs-Nachweis, nicht von einem Menschen |

Beweis für B (Selbsttest unter eine um 1461 Tage vorgestellte Uhr gelegt):

```
🛑 audio_coverage_check-Selbsttest FEHLGESCHLAGEN:
  - Live-Artikel falsch: ['2026-08-01-a', '2026-08-02-b', '2026-12-24-c']
  - Lücke nicht erkannt: ['2026-08-02-b', '2026-12-24-c']
```

## Behebung

**A — `scripts/draft_triage.py`: Selbsttest deterministisch**
- Fixtures sind **relativ zum Testdatum** beschrieben („42 Tage alt"), nie
  absolut (`2026-08-01`) und nie relativ zur echten Uhr.
- Dateialter wird **absolut** gestempelt (`selftest_clock.stempel`, lokaler
  Mittag — hält eine Zeitumstellung aus, weil ±1 h nie den Kalendertag kippt).
- Der ganze Ablauf läuft unter **Uhr-Zwang `strikt`**: ein einziger Lesezugriff
  auf `date.today()` / `datetime.now()` / `time.localtime()` bricht den Test.
- **Neues Kern-Assert:** gemessenes Alter == beabsichtigtes Alter, je Fall.
  Genau diese Zeile hätte den Ausfall am Tag des Einbaus gemeldet.
- Berichtskopf `as_md(..., stand=…)` ist injizierbar (vorher: echte Wanduhr im
  Selbsttest-Pfad).
10 Fälle × 6 Testdaten × 4 Zeitzonen, darunter der Schalttag 29.02.2028 und die
Zeitumstellung 25.10.2026. Neu abgedeckt: Verfalls-Schwelle exakt (21 = REIF,
22 = VERWAIST) und „Git-Nachweis schlägt mtime" (frisch gestempelt, alt
committet) — beides war vorher ungeprüft.

**B — `scripts/audio_coverage_check.py`: dieselbe Reparatur**
`live_artikel(root, heute=None)` und `auswerten(..., heute=None)` bekommen ein
injizierbares Referenzdatum (Produktion ruft weiter ohne Argument auf → echter
Kalendertag). Selbsttest: 5 Fälle × 5 Testdaten, ausdrücklich inklusive
23.12. **und 24.12.2026**.

**C — `scripts/selftest_runner.py` (neu) ersetzt die Bash-Liste im Gate**
- **entdecken** statt abtippen: jedes `scripts/*.py` mit echtem `--selftest`,
- **SSOT-Abgleich** gegen `governance_contract.GUARDS` (eine Quelle),
- **Uhr-Probe:** jeder Selbsttest läuft zusätzlich unter einer um **97** und
  **1461 Tage vorgestellten** Uhr (`selftest_clock.trap`) — Datums-Abhängigkeit
  kippt am Tag des Einbaus, nicht an einem Feiertag,
- **nur echte Kennung:** entdeckt wird das Argument in Anführungszeichen
  (`"--selftest"`), eine Kommentar-Erwähnung reicht nicht (Befund D),
- **C15-Wache:** ändert sich der Arbeitsbaum während des Laufs, ist das ein
  Befund — ein Prüf-Aufruf heilt nicht,
- **Zeitdeckel** 240 s je Wache (langsamste heute: 8,5 s), Timeout = Befund,
- **Ausnahmen brauchen einen Grund** und altern nicht still (Eintrag für ein
  geheiltes oder entferntes Skript wird selbst zum Befund).
Stand nach der Reparatur: **74 Wachen, 148 Uhr-Proben, ~50 s, grün, Arbeitsbaum
unberührt.** Ausnahme: `blog_doctor.py` (Kettenleiter, s. u.).

**D — `scripts/selftest_clock.py` (neu): Uhr-Zwang als Werkzeug**
`uhr(instant, modus, module=…)` (strict/verschoben), `stempel(pfad, tag)`
(absolutes Dateialter), `trap(script, offset)` (fremde Uhr um einen fremden
Selbsttest). `time.time()` bleibt **immer** echt — Dauer- und Timeout-Schleifen
dürfen nie einfrieren, sonst erzeugt die Garantie einen Hänger. `isinstance`
bleibt über eine Metaklasse in beide Richtungen wahr, damit Shim-Klassen keine
PyYAML-/C-API-Objekte entwerten. Verschachtelung ist erlaubt (die CI-Probe legt
eine fremde Uhr um einen Selbsttest, der selbst Uhr-Zwang einschaltet).

**E — `.github/workflows/link-check.yml`: das Gate meldet sich selbst**
Neuer Schritt „Gate-Fehlschlag melden (Selbsttests, Vertrag oder Build)" mit
`if: failure()` — unabhängig von jedem Fremd-Workflow und damit vom
Namens-Matching des zentralen Alertings. Er nennt die **gefallenen Schritte**
(aus der Actions-API, nicht geraten), hängt die `❌`-Zeilen des Runner-Protokolls
an, dedupliziert über das Label `auto-report` (kommentieren statt doppelt öffnen)
und wird bei Grün wieder geschlossen. Bewusst **nicht** bei Link-/Schema-Funden:
Dafür gibt es die beiden präziseren Meldungen, doppelt wäre Lärm. Der
Schließ-Schritt läuft jetzt auf `success()` und räumt alle drei Meldungstypen ab
— vorher blieb bei einem roten Selbsttest-Schritt eine alte „erledigt"-Meldung
offen stehen. Beide Pfade (Anlegen / Kommentieren / Schließen) wurden mit
einem `gh`-Stub durchgespielt.

**F — Verdrahtung wird über den Mechanismus bewiesen, nicht über den Text**
`selftest_runner.verdrahtet(name)` gibt die Gründe zurück, warum eine Wache im
Gate **nicht** läuft (leer = sie läuft): Datei vorhanden → `--selftest` wirklich
implementiert (quotierte Kennung) → in `governance_contract.GUARDS` → Gate ruft
`scripts/selftest_runner.py` auf → keine Ausnahme. Beide Unittests
(`test_draft_triage`, `test_newsletter_digest`) prüfen jetzt diese Funktion statt
die YAML; die `run:`-Texte werden dafür **kommentarbereinigt** gelesen
(`gate_aufrufe()`, PyYAML mit Rohtext-Fallback), denn ein Name im Kommentar ist
keine Verdrahtung. Nachweis durch Mutation: Aufruf ersetzt, Aufruf
auskommentiert, `--selftest`-Kennung entfernt, `verdrahtet()` auf `return []`
verstümmelt — alle vier Fälle werden rot, im Runner-Selbsttest **und** in den
beiden Unittests.

**G — `regelwerk()` lädt das Regelwerk über den Dateipfad**
`importlib.util.spec_from_file_location` unter privatem Modulnamen statt
`sys.path.insert` + `import governance_contract`: kein Import-Cache, der einem
anderen Prüfer ein fremdes Regelwerk unterschiebt, und kein Schatten-Ordner, der
vorn bleibt. Fehler steigen auf (`pruefen` meldet „Regelwerk nicht lesbar"),
statt still `[]` zu liefern — ein SSOT-Abgleich, der nichts abgleicht, ist
schlimmer als einer, der fehlt.

**Regelwerk** — `governance_contract.GUARDS` enthält `selftest_clock.py` und
`selftest_runner.py`: Der Vertrag prüft damit auch die Prüfer (C6).

**Workflow-Kopfzeile** — Die Kopfzeile von `link-check.yml` nannte seit Langem
„täglich um 05:00 UTC"; der Cron darunter läuft um 01:15 UTC. Korrektur nebenbei:
Eine veraltete Dokumentation ist dieselbe Fehlerklasse wie eine veraltete
Wachen-Liste — sie beschreibt nicht, was tatsächlich läuft.

## Nachweis (Mutationstests — der Test muss beißen)

Jede Mutation wurde in einer Kopie des Baums eingespielt; der Selbsttest **muss**
rot werden:

| Mutation | Ergebnis |
|---|---|
| Alter-Bombe zurück (`mtime = JETZT − n Tage`) | 🔴 „Alter 36 Tage gemessen, 42 beabsichtigt – der Prüfpfad liest eine andere Uhr als der Fixture-Bau" |
| Verfalls-Schwelle `>=` statt `>` | 🔴 „schwelle: Zustand VERWAIST statt REIF" |
| `fm-grenze`-Erkennung entfernt | 🔴 „geklebt: Hindernis „fm-grenze" fehlt" |
| Git-Alter ignoriert (nur mtime) | 🔴 „git-alter: Alter 0 Tage gemessen, 30 beabsichtigt" |
| Auffrischung wird Blocker | 🔴 „auffrischung: Zustand BLOCKIERT statt VERWAIST" |
| `audio_coverage_check`: feste Fixtures zurück | 🔴 „[Testdatum 2026-12-24] Live-Artikel falsch" |
| Runner: rote Wache / Datumsbombe / schreibender Selbsttest / leere Entdeckung / veraltete Ausnahme | 🔴 je eigener Befund |
| Runner: Gate-Aufruf ersetzt (Kommentar bleibt) / Aufruf auskommentiert / `--selftest`-Kennung aus `draft_triage` entfernt / `verdrahtet()` liefert immer `[]` | 🔴 je eigener Befund – **und** 🔴 in `test_draft_triage` + `test_newsletter_digest` |

Zusätzlich: komplettes Gate lokal nachgebaut (Selbsttests → Vertrag → `hugo
--minify` → interne Links → Schema-Gate): **grün**, 2861 interne Links ohne
Defekt, 385 Seiten, 0 harte Schema-Funde. Dazu die Regressionssuite des
`publication-reliability-tests`-Workflows (`python3 -m unittest discover -s
scripts/tests`): **271 Tests, 0 Fehler** — vor der Reparatur 270/1, weil ein
Verdrahtungs-Test noch die alte Bash-Liste suchte (Befund F).

## Folge-Befunde (nicht Teil dieses Laufs, bewusst nicht still mitrepariert)

1. **🔴 Integritäts-Lock steht auf HARD STOP.** `scripts/integrity_guard.py`
   meldet Exit 3: `data/integrity_lock.json` ist am 15.09.2026 (head `be04d2a`)
   signiert, seitdem drifteten 4 gesperrte Dateien —
   `layouts/_partials/head.html` (**kritisch**), `layouts/_partials/cover.html`,
   `scripts/affiliate_integrity_gate.py`, `scripts/affiliate_marketer.py`.
   Die Änderungen kamen über regulär gemergte PRs (#308/#309, LCP-Preload,
   Kadenz-/Cover-Heilungen), aber **ohne Neu-Signatur**. Einziger Abnehmer ist
   `blog_doctor.py --new-only` in `content-engine-v2.yml` — mit
   `|| echo "⚠ Doktor-Befund (nicht kritisch)"`. Damit ist der Sabotage-Schutz
   seit drei Tagen scharf ausgelöst und wird verschluckt.
   **Vorschlag:** Diff der vier Dateien sichten und dann
   `python3 scripts/integrity_guard.py --set-current` (Signatur ist laut
   Guard-Design eine Betreiber-Entscheidung, deshalb hier nicht automatisch
   gesetzt). Zusätzlich sollte ein Exit 3 des Doktors niemals in einem `|| echo`
   enden.
2. **`blog_doctor.py --selftest` ist kein Selbsttest.** Der Aufruf läuft die
   ganze Visite (24 Wachen im Trockenlauf) und schreibt `data/*.jsonl`
   (`doctor_history`, `integrity_history`). Deshalb ist er im Runner als
   Kettenleiter ausgenommen — mit Grund, maschinell geprüft. Sauber wäre:
   `--selftest` beweist nur die Logik, die Visite bekommt eine eigene Flagge.
3. **`content-reserve.yml` (Zeile 140–157)** hat dieselbe handkopierte
   Selbsttest-Liste wie das Gate vorher. Sie ist aktuell, aber nicht abgeglichen;
   ein Wechsel auf `scripts/selftest_runner.py` würde auch dort die Lücke C
   schließen (Kosten: ~50 s in einem 90-Minuten-Lauf).
4. **`alert-on-failure.yml` bekommt seine Ereignisse nicht** (Befund E). Die
   Konfiguration ist nachweislich korrekt (Name geparst und byteweise identisch,
   39 eindeutige Einträge, `types: [completed]`, `alarm` bei `failure`),
   trotzdem kamen seit dem 08.09. nur 602 Alerting-Läufe auf 922 abgeschlossene
   Läufe gelisteter Workflows — ~35 % der Ereignisse fehlen, beim Gate 14 von 14.
   Die Eigenmeldung des Gates macht **diesen** Betrieb wieder sicher, aber die
   Zustellung ist nicht repariert und andere Workflows derselben Liste sind
   weiterhin im Blindflug (Deploy: 13 rote Läufe seit 08.09., Lesehilfen-Gate: 9).
   **Vorschlag — „Alerting-Herzschlag":** ein täglicher Lauf, der genau die
   Rechnung dieses Berichts als Wache stellt: abgeschlossene Läufe gelisteter
   Workflows der letzten 24 h gegen Alerting-Läufe zählen, Differenz = Befund,
   Meldung als Issue (selbstmeldend wie das Gate, nicht abhängig von
   `workflow_run`). Alternativ/ergänzend: `workflow_run` durch einen
   Polling-Wächter ersetzen, der Runs per API abfragt — Zustellung, die man
   zählt, statt Ereignisse, die man erwartet.
5. **5 Entwürfe im Reserve-Bestand haben eine geklebte Frontmatter-Grenze**
   (`---Text`, Klasse `fm-grenze`) — von `draft_triage` korrekt als BLOCKIERT
   gemeldet, also kein neuer Befund, aber offene Redaktionsarbeit.

## Selbst prüfen

```bash
python3 scripts/selftest_clock.py --selftest            # Uhr-Zwang-Werkzeug
python3 scripts/selftest_runner.py --selftest           # Runner-Logik
python3 scripts/draft_triage.py --selftest              # 10 Fälle × 6 Daten × 4 Zonen
python3 scripts/audio_coverage_check.py --selftest      # 5 Fälle × 5 Daten
python3 scripts/selftest_runner.py                      # alle Wachen + Uhr-Proben
python3 scripts/selftest_clock.py --trap scripts/draft_triage.py --offset 1461
python3 -m unittest discover -s scripts/tests         # Regression (271 Tests)
```

---
_Ursache ohne Wache zu reparieren wäre eine Leihgabe: Deshalb liegt der Beweis
jetzt im Repo (`selftest_clock.py`, `selftest_runner.py`) und läuft bei jedem
Push, jedem PR und jede Nacht um 03:15 MESZ im Qualitäts-Gate mit._
