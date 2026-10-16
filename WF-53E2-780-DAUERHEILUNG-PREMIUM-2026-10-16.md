# Wartung · Partnerhinweise · WF-53E2 · #780 – Dauerhafte Heilung

**Datum:** 16.10.2026

**Auslöser:** [Lauf `38875169146`](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/38875169146)
des Workflows „Affiliate-Integritäts-Wache (täglich)“ (Zeitplan, `main`, Commit `872023f8`, 08:39 UTC).
Der Schritt **„Detektor-Selbsttest (Wache muss sehen können)“** endete mit Exit 2. Danach wurden
Intent-Selbsttest, Hugo-Build, Render-Beweis und Intent-Wache übersprungen, und „Lauf bewerten“
stellte den Lauf fail-closed auf Rot. Gemeldet wurde das als
[Issue #780](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/780) – mit dem Rat
„API-Key abgelaufen (GROQ/GEMINI)“.

**Urteil:** Es war weder ein Netz-, Hugo- noch Schlüsselproblem, sondern eine Code-Regression aus einem
Merge, der nie grün war (PR #776). Die Wache tat das Richtige: Sie sah, dass ihr eigener Detektor nicht
mehr sehen konnte, und hielt an. Während dieser Vorgang bearbeitet wurde, brach `main` ein zweites Mal
am selben Code: Die parallelen Reparaturen #785 und #784 gingen binnen 77 Sekunden bei roten Checks
nach `main`. Ihre Zusammenführung ließ einen **Syntaxfehler** in `scripts/affiliate_integrity_gate.py`
zurück. Seitdem stürzt jeder Aufrufer ab, und **das Publish-Gate lässt keinen Artikel mehr live**.
Dieser Vorschlag heilt beide Stände, hält die Verträge aller drei Reparaturen zusammen und stellt
sicher, dass keine der beiden Bauarten unbemerkt zurückkommt.

## 1. Befund (belegt)

| Beleg | Quelle |
|---|---|
| Schritt 6 „Detektor-Selbsttest“ rot (Exit 2), Schritte 7–10 übersprungen, Schritt 17 „Lauf bewerten“ rot (Exit 1) | Jobs-API und Annotationen, Job `116888354398` |
| 14 grüne Tagesläufe vom 02. bis 15.10.; der letzte grüne lief am 15.10. um 08:44 UTC, **vor** #776. Der erste Lauf danach war rot | `gh run list` der Wache |
| Lokal nachgestellt: `affiliate_integrity_gate.py --selftest` → Exit 2, „eine gültige Ausnahme darf keinen 'kein Affiliate-Link'-Fund erzeugen“ und „die Ausnahme muss als Hinweis sichtbar bleiben“ | Reproduktion auf `e662cf0` |
| PR #776 (15.10.): Der umgesetzte Stand wurde gepusht, der **Merge folgte 22 s später** (18:18:59 UTC), bevor ein Check fertig war. Danach waren drei Checks rot: Integritäts-Siegel, Regressionstests, Qualitäts-Gate | PR-API, `statusCheckRollup` |
| Das Qualitäts-Gate auf `main` war ab `1e40a664` rot und öffnete um 18:22 UTC #777 – 14 Stunden vor #780 | Lauf `38784603892`, #777 |

**Mechanismus.** Die Konfliktauflösung von #776 hatte in `verify_article_render()` eine **zweite
Auswertung** derselben Ausnahme eingebaut. Ergebnis von Zeile 942 überschrieben (`exempt = False`),
Datei unter `article["path"]` erneut gelesen, selbst per `split("---", 2)` zerlegt, über den Adapter
einer anderen Wache (`affiliate_link_check`) ausgewertet – und **jeden Fehler** mit
`except Exception: exempt = False` verschluckt. Der sichtbare Ausnahme-Hinweis fiel dabei ganz weg. Der
Selbsttest prüft die Funktion mit Artikeln aus dem Speicher, deren Pfad nie geschrieben wird. Das
`FileNotFoundError` wurde zu „keine Ausnahme“, also zu einem Fehlalarm, und der Selbsttest wurde rot.
Dieselbe Bauart war ein Anti-Muster mit Vorgeschichte (#521, #676: zwei Wachen, ein Vertrag, zwei
Wahrheiten).

**Warum es grün aussah.** Alle 27 Unit-Tests blieben grün, denn jede Testvorlage schrieb den Artikel
auf die Platte. Weder der dateilose Fall noch der Hinweis waren getestet. Der Selbsttest selbst lief
im Qualitäts-Gate jedes PRs mit und war dort rot. Gemergt wurde trotzdem: Kein Branch-Schutz verlangt
die Checks (Dauerzustand seit 20.09., `docs/PFLICHT-CHECK-RUNBOOK.md`).

**Wirkung in der Produktion bis 15:22 UTC.** Weil die echte Datei existiert, galt die Ausnahme des
DNS-Artikels weiter. Der Hinweis fehlte aber (Gate-Lauf auf dem echten Bestand: 3 statt 4 Hinweise). Am
16.10. war die Wache blind: kein Render-Beweis, keine Intent-Wache, kein Herzschlag. Das Bestand-Gate
übersprang Bewertung und Heilung fail-closed, weil es den Detektor-Selbsttest als Vorbeweis fährt.

**Derselbe Merge erzeugte fünf Meldungen:**

| Meldung | Ursache aus #776 |
|---|---|
| #777 Qualitätsprüfung rot | Selbsttests von `affiliate_integrity_gate`, `bestand_gate` (hängt am ersten) und `redaktions_standard` (Faustregel-Pool aus #766 gelöscht) |
| #778 Content-Reserve | „Selbsttests aller Wachen“ – dieselben drei |
| #779 Affiliate-Wachen (Fachmeldung) | derselbe Lauf wie #780 |
| #780 Partnerhinweise | dieser Vorgang |
| #783 Redaktions-Standard neu | Selbsttest von `redaktions_standard` |

### Zweiter Bruch während der Bearbeitung (16.10., 15:21–15:25 UTC)

| Beleg | Quelle |
|---|---|
| #785 (für #779): erstellt um 15:20:20, **gemergt nach 58 s**; Siegel, Regression und Qualitäts-Gate rot | PR-API |
| #784 (für #777): **gemergt 77 s nach #785**, mit fünf roten Checks | PR-API |
| #786 (für #782): gemergt 39 s nach Erstellung, die Regressionstests liefen noch | PR-API |
| `scripts/affiliate_integrity_gate.py` auf `main` (`f7517a5`, `6bbc805`): zwei `if`-Köpfe und zwei Hinweistexte, also **`IndentationError` in Zeile 951** | `py_compile` auf `origin/main` |
| Der Lock aus #784 versiegelt genau diese kaputte Datei | `data/integrity_lock.json`, Akte |
| Publish-Gate auf `main`: „Affiliate-Integrität NICHT beweisbar … kein Kandidat geht ungeprüft live“ (Werkzeugfehler = alle Kandidaten blockiert). Der nächste Engine-Slot ist heute um 17:40 UTC | `publish_gate.affiliate_integrity_failures()` gegen `main` |
| Qualitäts-Gate rot (#787 neu); CodeQL-Klartext- und URL-Wache Exit 2 (sie parsen jede Python-Datei) | Läufe `38923824587` u. a. |
| #777 und #779 wurden von diesen Merges geschlossen, obwohl `main` danach roter war als vorher | Issue-API |

Beide Reparaturen waren für sich richtig; die Analyse von #785 deckt sich mit Abschnitt 1. Gebrochen
hat sie erst ihre Zusammenführung ohne grünen Lauf – dieselbe Bauart wie #776, 21 Stunden später.

**Bei der Analyse gefundene Folgefehler** (behoben, siehe Abschnitt 2):

1. **A8 hatte dieselbe Zweitauswertung.** `affiliate_profi_check._check_cta()` las die Datei erneut,
   zerlegte sie selbst, importierte über `affiliate_link_check` und verschluckte Fehler. Bei einer
   *ungültigen* Ausnahme hätte `--fix` (Content-Engine, SEO-Wochenlauf, Bestand-Gate) dem Artikel
   eine Werbe-CTA eingesetzt – gegen die erklärte Absicht der Redaktion.
2. **Falscher Rat im Alarm.** #778, #780 und #783 rieten zu GROQ/GEMINI und zum Neustart. Ein
   Selbsttest läuft offline mit Attrappen-Schlüsseln (KI-Probe, #138); beides kann ihn weder rot
   noch grün machen.
3. **Zerlegte Frontmatter-Texte.** Der „Bestand heilen“-Lauf in #776 hat Semikola auch im
   Frontmatter zu Punkten gemacht, ohne großzuschreiben. Die Ausnahme-Begründung des DNS-Artikels
   lautete seitdem „…Tarifangebot. ein Tarif-CTA…“; sie steht in Hinweis und Report.

## 2. Dauerhafte Korrektur

| Baustein | Änderung | Wirkung |
|---|---|---|
| `scripts/affiliate_integrity_gate.py` | Syntaktisch heil. **Ein** Hinweis (Wortlaut aus #784, mit Begründung, auch bei vorhandenen Links), **eine** Bedingung (`not gateway_anchors and not exempt`). Die Ausnahme kommt nur aus `article["fm"]`: kein Dateizugriff, kein zweiter Parser, kein Sammel-`except`. | Wache, Publish-Gate, Bestand-Gate und CodeQL-Wachen laufen wieder. Eine ungültige Ausnahme ohne Link ergibt beide Funde (Vertrag aus #785). |
| Selbsttest 8b (läuft in jedem Workflow) | Neu: (e) Die Platte widerspricht dem geladenen Stand in **beide** Richtungen – eine Zweitlesung fiele in genau einer davon um. Genau **ein** Ausnahme-Hinweis. Ungültige Ausnahme = beide Funde. | Der Detektor beweist seinen eigenen Vertrag, nicht nur den Normalfall. |
| `scripts/affiliate_exemption.py` | `exemption_for_text()` für Aufrufer mit Rohtext. Die Frontmatter-Grenze kommt von `post_utils.split_article` (wie Hugo) statt aus einem eigenen `split("---")`. Kopfvertrag „ein Vertrag, ein Auswerter“. | Ein „---“ in einem Wert zerschneidet die Auswertung nicht mehr. |
| `scripts/affiliate_profi_check.py` (A8) | Liest den Vertrag direkt auf dem schon gelesenen Text. **Gültig** → nichts schreiben. **Ungültig** → Fund A8, auch im FIX-Modus keine CTA. **Ohne Angabe** → CTA wie bisher. Der Selbsttest prüft alle drei Fälle; ist der Vertrag nicht ladbar, endet der Check mit Exit 2 und ändert nichts. | Kein Heiler überstimmt eine Redaktionsentscheidung, und ein Werkzeugfehler wird nie zu einer Werbe-CTA. |
| `scripts/tests/test_affiliate_exemption.py` | +16 Tests:<br>· Platte gegen geladenen Stand (beide Richtungen)<br>· genau ein Vertragsaufruf<br>· Vertragsfehler werden nicht verschluckt<br>· Hinweis im Report<br>· Detektor-Selbsttest als Unit-Test<br>· A8 in FIX und CHECK samt Selbsttest<br>· Text-Adapter inkl. „---“ im Wert<br>· **Strukturregeln am Code aller Skripte:** Nur der Vertrag liest die Schlüssel, Ausnahme-Importe nur aus dem Vertrag, kein Catch-all um einen Vertragsaufruf<br>Die Tests aus #785 und #784 bleiben unverändert. | Die tägliche Wache fährt diese Datei in Schritt 6 mit; die PR-Suite ebenfalls. |
| `.github/workflows/alert-on-failure.yml` | Neue Klasse `selbsttest`. Sie greift, wenn der **erste** rote Schritt ein Selbsttest ist (die Schlussbewertung danach ist nur die Folge), und steht hinter allen spezifischen Klassen (Engine, Backup, Installation, Sicherheits-Wache). Rat: Einordnung als Code-Regression, `selftest_runner.py`, `git log` der Wache, erst bei grünen Checks mergen. | Offene Meldungen werden über den Nachführ-Mechanismus aus #761 beim nächsten roten Lauf umgeschrieben (#778, #783). |
| `scripts/tests/sim/alert_scoping_sim.mjs`, `test_alert_scoping.py` | 6 neue Szenarien:<br>· #780 und #778 nachgestellt<br>· Gegenprobe „erster Schritt entscheidet“<br>· Vorrang von Installation und Backup<br>· Nachführung der offenen #780<br>Szenario 7 bekommt den Selbsttest-Rat (seine Zusage „kein Engine-Runbook“ bleibt). Neuer Strukturtest. | Verhalten statt Textsuche. |
| DNS-Artikel (nur `affiliate_exempt_reason`) | „…Tarifangebot – ein Tarif-CTA wäre sachfremd.“ (Gedankenstrich statt Semikolon, robust gegen Satz-Heiler) | Hinweis und Report zeigen wieder korrektes Deutsch; das Feld wird nicht gerendert. |
| `package.json` | `test:affiliate-links` enthält den Detektor-Selbsttest | Ein Befehl prüft den ganzen Affiliate-Vertrag. |
| `CLAUDE.md` | „Ein Rebase ist ein neuer Stand – erst grün, dann mergen“: `gh pr checks <nr> --watch --fail-fast`, Konflikt zwischen zwei Heilungen = beide behalten, danach `selftest_runner.py`, ein Auswerter, ungültige Ausnahme = Fund, Selbsttest-Alarm | Der nächste Agent merged nicht nach 22 Sekunden. |
| `data/integrity_lock.json` | Neu signiert über `integrity_guard.py --set-current` (Klasse fest, Herkunft `0c13fb3 · f7517a5 · 1a44e39` in der Akte) | Das Siegel deckt den heilen Stand, nicht den Syntaxfehler. |

**Bewusst nicht getan:**

- **Nichts abgeschwächt.** Der Selbsttest bleibt Pflichtstufe der Wache, fail-closed bleibt. Kein
  `continue-on-error`, kein Überspringen.
- **Keine Rücknahme von #785/#784.** Ihre Tests und Verträge sind erhalten. Mein eigener Test
  „ungültige Ausnahme = genau ein Fund“ widersprach dem gemergten Vertrag aus #785
  („…darf die Mindestpflicht nicht aufheben“) und wurde verworfen, nicht umgekehrt. Der Test „ohne
  Datei“ aus #785 ersetzt meinen gleichwertigen.
- **Kein Eingriff in `redaktions_standard.py`.** #784 hat den Faustregel-Pool aus #766
  wiederhergestellt; #778 und #783 sind eigene Vorgänge.
- **Keine Änderung an `affiliate-integrity-daily.yml`.** Die Doppelmeldung #779/#780 bei
  Werkzeugfehlern ist Bestandsdesign; beide schließen sich bei Grün selbst.
- **Kein Merge, kein Handstart, kein Issue-Kommentar** durch den Agenten.

## 3. Was nur der Inhaber tun kann

1. **Den PR erst mergen, wenn alle Checks dieses Commits abgeschlossen sind** (`gh pr checks <nr> --watch`).
   Bis dahin ist `main` kaputt (Abschnitt 1), und das Publish-Gate blockiert jeden Kandidaten.
   Es gibt **eine belegte Ausnahme**: `regression` ist auf jedem PR rot, solange die zwei
   Faktenfrische-Tests des Heizungsartikels rot sind (Bestand, nicht aus diesem PR). In seinem Log
   dürfen nur diese zwei Tests stehen; jeder andere rote Test heißt: nicht mergen.
2. Danach einmal *Actions → Affiliate-Integritäts-Wache (täglich) → Run workflow*. Der grüne Lauf
   führt den Render-Beweis auf dem echten Bestand und schließt #780 über `resolve`. Er erneuert
   außerdem den Herzschlag: Der Bot-Watchdog meldet „läuft rot“, seit der letzte grüne Lauf (15.10.,
   08:44 UTC) um 14:44 UTC aus seinem 30-Stunden-Fenster fiel.
3. **Empfehlung: Pflicht-Checks im Branch-Schutz.** Mindestens „Integritäts-Siegel“, Qualitäts-Gate
   (`gate`) und Regressionstests (`regression`) – Ablauf in `docs/PFLICHT-CHECK-RUNBOOK.md`. Die
   Entscheidung „Dauerzustand“ vom 20.09. ist durch diesen Tag neu zu bewerten: vier rot gemergte
   PRs in 21 Stunden, sieben Meldungen, ein Syntaxfehler auf `main` und eine blockierte
   Veröffentlichung. Kein Selbsttest und keine Agentenregel ersetzt einen Merge, der bei Rot nicht
   geht.

## 4. Verifikation

| Prüfung | Ergebnis |
|---|---|
| Nachstellung #780 (Stand `e662cf0`) | Selbsttest Exit 2, exakt die beiden Meldungen des echten Laufs |
| Stand `main` (`6bbc805`) | `py_compile`: `IndentationError` Z. 951; Selbsttest Exit 1; Bestand-Gate fail-closed; Publish-Gate: Werkzeugfehler, alle Kandidaten blockiert |
| `affiliate_integrity_gate.py --selftest`, `bestand_gate.py --selftest` | grün |
| Echter Bestand, Hugo 0.164.0 Extended (101 Seiten), `--dry-run --json --no-build` | Exit 0, 61 Artikel, 0 Render-Funde, 0 Markdown-Funde; DNS-Artikel: kein Fund, genau ein Hinweis mit Begründung |
| Publish-Gate gegen den echten Bestand | `({}, None, False)` – keine Funde, kein Werkzeugfehler |
| A8 auf dem echten Bestand (CHECK) | 0 Funde, 0 Änderungen – identisch zum Stand vor der Korrektur |
| Mutationsproben (Selbsttest + Unit-Tests) | **9 von 9 erkannt:** exakter Zustand von #776 · exakter Merge-Bruch #785/#784 · Hinweis entfernt · zwei Hinweistexte · Zweitlesung · Zweitlesung + Sammel-`except` · ungültige Ausnahme hebt Pflicht auf · A8 im Zustand von #776 · A8-CTA trotz ungültiger Ausnahme. Kontrolllauf grün. |
| Alarm-Simulation | **44/44** Szenarien grün (6 neu). Mutationen am Alarm-Skript: 5 von 5 erkannt (Klasse fehlt, „irgendein“ statt erster Schritt, falscher Vorrang, Schlüssel-Rat zurück) |
| `npm run test:affiliate-links` | Link-Check-Selbsttest, Detektor-Selbsttest, 46 Tests grün |
| `test_alert_scoping` (23), `test_integrity_guard` (59) | grün |
| Uhr-Proben (+97 / −400 / +3650 Tage) | Detektor-Selbsttest, `test_affiliate_exemption`, `test_alert_scoping` grün |
| KI-Probe `selftest_ki.py --trap-workflows` | **123/123 grün** (Stand `e662cf0`: 2 rot – Affiliate-Gate und `redaktions_standard`) |
| Selbsttest-Runner (alle Wachen, Uhr-Proben) | **208 Wachen, 416 Uhr-Proben: alle grün**, auch unter +97/+1461 Tagen (Stand `e662cf0`: 3 rot; Stand `6bbc805`: Affiliate-Gate stürzt ab, Bestand-Gate fail-closed) |
| Gesamte Suite `unittest discover -s scripts/tests` | 3307 Tests, 0 Fehler, 3 übersprungen, **2 rot – beide Bestand** (`test_faktenfrische_763`, Heizungsartikel; auf `main` genauso rot, siehe Nebenbefunde). Stand `e662cf0`: 3273 Tests, 8 rot (6× `redaktions_standard`, 2× Faktenfrische) |
| Governance-Vertrag (36 Regeln), `automation_premium_audit --strict`, Actions-Versions-Wache, Hugo-Build-Vertrag, FM-Grenzen (127 Dateien), Artefakt-Wächter (448), `integrity_guard --gate` (49 Kerndateien), `py_compile`, `node --check`, YAML, `git diff --check` | grün |
| PR-Checks (#789, Push `5668b63`) | grün: Qualitäts-Gate (`gate`), Integritäts-Siegel, CodeQL Python/JS samt Klartext- und URL-Wache (auf `main` Exit 2), Playwright Desktop + Mobile, Lesehilfen, Navigation, Beweis-Gate, Daten-Gate, Sicherheits-Quellseite. **Rot: `regression`** – Suite und Uhr-Probe, lokal nachgestellt: genau die zwei Faktenfrische-Tests aus dem Bestand |

**Grenzen dieser Umgebung:**

- **Lauf-Logs nicht abrufbar.** Die Log-Hosts von GitHub sind hier gesperrt. Belegt ist der Befund über
  Jobs-API, Annotationen und die lokale Nachstellung.
- **Python 3.11 statt 3.12.** Lokal lief 3.11.2 mit den hash-gepinnten CI-Abhängigkeiten. Die
  PR-Checks laufen auf 3.12.
- **Kein Lauf der Wache auf `main`.** Der Render-Beweis auf dem echten Bestand ist lokal mit
  derselben Hugo-Version geführt; den Produktionsnachweis liefert der erste Lauf nach dem Merge.

## 5. Abschluss des Vorgangs

Der Vorschlag nennt **`Closes #780`**. Die Korrektur ist deterministisch: Mit dem Merge ist der
Detektor-Selbsttest grün, und den Nachweis im Betrieb liefert der nächste Lauf der Wache.
`vorgangs-abschluss.yml` schreibt beim Merge den Abschlussvermerk; ein grüner Lauf hätte #780 über
`resolve` ohnehin geschlossen.

- **#779** wurde von #785 geschlossen. Ist der nächste Lauf grün, bleibt die Meldung zu; sonst öffnet
  die Wache sie selbst neu.
- **#787** (Qualitätsprüfung rot, neu seit 15:25 UTC) schließt sich, sobald das Qualitäts-Gate auf
  `main` grün ist.
- **#778 und #783** sind eigene Vorgänge. Bekommen sie vorher einen roten Lauf, schreibt das Alerting
  ihnen den Selbsttest-Rat statt des Schlüssel-Rats hinein.

**Offene Nebenbefunde (nicht Teil dieses Vorgangs):**

- `content/posts/2026-09-30-last-minute-urlaub-…/index.md`: #776 hat auch sichtbare Quellenangaben
  zerlegt – „WELT. mit Einschätzungen …“, „ZDFheute. zitiert …“ und der Gesetzestitel
  „BGB § 651r – Insolvenzsicherung. Sicherungsschein“ (vorher jeweils mit Semikolon). Der
  Gesundheits-Heiler vom 16.10. repariert nur den Fließtext, nicht das Frontmatter.
- `test_faktenfrische_763` (2 Tests) ist auf `main` rot und hält damit `regression` auf jedem PR rot.
  Bot-Läufe haben den Heizungsartikel aus #775 nachträglich umformuliert (Gate-Heilungen am 15.10.,
  Endredaktion am 16.10.) – etwa „39,42 €“ zu „39,42 Euro“. Dabei fielen Schutzformulierungen weg,
  die der Test wörtlich einfordert („kein allgemeines Optimum“ u. a.). Zu klären ist, ob die Sätze
  zurückmüssen oder der Test den Sinn statt des Wortlauts prüfen soll. Solange ein Check dauerhaft
  rot ist, lernt jeder, rote Checks zu übergehen – die Grundursache dieses Vorgangs.
