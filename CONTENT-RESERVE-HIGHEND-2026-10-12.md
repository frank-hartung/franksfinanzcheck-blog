# Content-Reserve: belastbare tägliche Produktionslinie

**Stand: 12. Oktober 2026 · Geltungsbereich: `Content-Reserve (täglicher Vorrat)`**

## Ergebnis und Abgrenzung

**Integrationshinweis:** Während der Arbeit wurde `main` durch die separaten
Reparaturen #720/#721 weiterentwickelt (Stand `05178f3`). Diese redaktionellen
Änderungen, Lesbarkeits-Verträge und YMYL-Schreibsperren wurden auf dem festen
Arbeitsbranch übernommen. Der nachfolgende Stand 7/6 und die vier damaligen
RS-Blocker dokumentieren ausdrücklich die erste Abnahme **vor** dieser
Integration, nicht den aktuellen Stand der inzwischen bearbeiteten Artikel.
Die Abnahme des integrierten Stands wird unten separat protokolliert.


Die Reserve-Automatik wurde im bestehenden System gehärtet, nicht durch eine
zweite Produktionslinie ersetzt. Das Vorratsziel bleibt in `reserve_economy.py`;
Publikations-, Fakten-, YMYL-, Affiliate- und Redaktions-Gates bleiben verbindlich.

Die echte lokale Neubewertung vom **12.10.2026, 21:17:13 UTC** bestätigt
**7 READY bei Ziel 6 aus 11 Entwürfen**. Sie lief mit Hugo Extended 0.164.0,
Hunspell 1.7.2 und dem tatsächlichen deutschen LibreOffice-Frami-Wörterbuch.
Alle Artikeldateien unter `content/` waren anschließend bytegenau unverändert.
Das damalige Zertifikat ist eine **lokale vollständige Messung**, kein vorgetäuschter
GitHub-Actions-Lauf. Die vier damals abgelehnten Entwürfe wurden in dieser Abnahme nicht freigegeben.

Damit ist auch die bereits im Ausgangsstand vorhandene SHA-Abweichung des
Entwurfs `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt`
durch eine echte neue Prüfung behoben, nicht durch Abschreiben eines Hashes.

Die Änderungen werden erst nach Übernahme nach `main` für den geplanten
Produktionslauf wirksam. Ein erfolgreicher künftiger Nachtlauf, erfolgreiche
KI-Neuproduktion, Push oder Veröffentlichung werden durch diese lokale Abnahme
**nicht** behauptet. Cronzeit und Veröffentlichungsrhythmus wurden nicht geändert.

## Warum der bisherige Zähler nicht genügte

Der untersuchte Actions-Lauf
[38240822821](https://github.com/frank-hartung/franksfinanzcheck-blog/actions/runs/38240822821)
endete mit 5/6 READY. Der danach gespeicherte Stand von 7 READY entstand durch
spätere lokale Reparatur, die ohne Hunspell ausgeführt wurde und den alten
Zeitstempel beibehielt. Das sind unterschiedliche Messzustände, kein Beweis
für eine Korruption innerhalb des ursprünglichen CI-Laufs.

Weitere strukturelle Risiken waren maskierte `continue-on-error`-Ergebnisse,
fehlende echte Messungen hinter numerischen Fallback-Werten, fehlendes
Gesamtzeitbudget und nicht mitgesicherte Hilfsgedächtnisse. Sie werden nun an
Ausführung, Belegen und Abschlussentscheidung abgesichert.

## Betriebsverträge

### 1. Vorhandene Arbeit vor zusätzlicher KI-Produktion

Vor der Generierung läuft eine Bestandsaufnahme über die bestehenden
Besitz-, Duplikat-, Triage- und Risikoregeln. Geänderte oder abgelaufene
Einzelnachweise werden gezielt am tatsächlichen Produktions-Gate erneuert.
Fehlt ein vollständiger lesbarer Nachweis, folgt zunächst eine echte Messung.

Ein gemessener Fehlbestand (`reserve_readiness.py`: rc 1) erlaubt Nachschub;
Artefakt-, Werkzeug- und Zeitfehler erlauben ihn nicht. Produktion, Finisher
und Konvergenz verlangen ausdrücklich erfolgreiche Selbsttests, Werkzeugprüfung,
Snapshot und Bestandsstufe. Der Finisher läuft im Workflow mit `--bedarf`:
Ist das Ziel bereits frisch und bytegebunden nachgewiesen, wird keine
zusätzliche KI-Politur für liegengebliebene Entwürfe beauftragt.

Die Engine prüft Frische und Besitz statt bloß `reserve: true` oder eines
alten READY-Zählers. Beschädigte Nachweise und vorhandener ungemessener
Bestand werden nicht als leeres, nachzufüllendes Lager interpretiert.

### 2. Echte Stufenausgänge statt Scheingrün

Prüfungen und Entscheidungen benutzen `steps.<id>.outcome`, nicht die durch
`continue-on-error` maskierbare `conclusion`. Der harte End-Gate bekommt
Produktion, Veredelung, Messung, Konvergenz und Sicherung als tatsächliche
Ausgänge. Die Chronik benutzt dieselbe Bewertungslogik.

Eine rote Wache oder Werkzeugprüfung verhindert weiterhin ein grünes
Gesamturteil. Eine spätere echte erfolgreiche Neubewertung darf dagegen einen
zwischenzeitlichen Produktions- oder Veredelungsfehler überwinden, wenn der
benötigte Vorrat anschließend wirklich nachgewiesen ist. Die ursprünglichen
Stufenfehler bleiben im Abschlussbericht sichtbar.

### 3. Frische gehört zur einzelnen Messung

Jede neu gemessene Zeile erhält `measured_at`. Die Grenze bleibt höchstens
**36 Stunden**; eine Konfiguration darf sie verschärfen, nicht verlängern.
Unzulässige Zukunftszeiten, fehlende oder ungültige Zeitpunkte sind keine
Nachweise. Fünf Minuten Uhrtoleranz sind keine zusätzliche Haltbarkeit.

Teil-Nachzertifizierung setzt bei unveränderten alten Zeilen ausdrücklich
deren ursprünglichen Messzeitpunkt. Ein neuer `generated_at` kann dadurch
nicht den gesamten alten Vorrat künstlich verjüngen.

CI verlangt außerdem einen Messkontext mit dem aktuellen `GITHUB_RUN_ID`
**und** `GITHUB_RUN_ATTEMPT`. Die Chronik dedupliziert je Lauf und Versuch:
Ein Wiederholungslauf behält seinen eigenen Verlauf. Lokale und ältere
Zertifikate bleiben außerhalb dieses ausdrücklich aktivierten CI-Vertrags lesbar.

### 4. Messausfall ist kein schlechtes Manuskript

`quality_score` weist Werkzeugfehler separat als `measurement_errors` aus.
Der numerische Fallback ist damit kein Zertifizierungsbeleg. Auch eine zweite
fehlgeschlagene Qualitätsmessung im Produktions-Gate kann nicht unbemerkt
als akzeptierter Kandidat enden.

Hunspell-Abfragen sind explizit UTF-8, zeitlich begrenzt und prüfen den
Rückgabecode. Die Vorprüfung testet korrekte Wörter **mit Umlauten** sowie ein
wirklich falsch geschriebenes Kontrollwort. Eine bloß vorhandene CLI oder
ein kaputtes Wörterbuch genügt nicht.

Bei ausgefallener Messung werden der bisherige vollständige Nachweis und die
Originalbytes erhalten. Es gibt dann keine Quarantäne-Abwertung aus einer
fehlenden Messung. Auch die technischen `NICHT BEWEISBAR`-Abbrüche des
Publish-Gates und ein nicht prüfbares RS-Gate werden als Messausfall behandelt.

Stufe 3 bleibt unabhängig ausführbar (`!cancelled()`, C33), auch nach roten
Voraussetzungen. In diesem Fall sind Custody-, Intake- und Quarantäne-Schreiber
explizit ausgeschaltet; gemessen werden darf weiterhin. Ein erschöpftes
Zeitbudget wird als Abbruch gemeldet, nicht als erfolgreicher Vorrat.

### 5. Begrenzte Arbeit, gesicherter Abschluss

`scripts/reserve_operations.py` verankert vor Installation und Selbsttests
ein gemeinsames **65-Minuten-Arbeitsfenster**. Das Verankern allein erteilt
kein Schreibrecht; der spätere echte Werkzeug-Preflight verlängert das Fenster
nicht. Ungültige oder erschöpfte Fristen stoppen neue Arbeit.

- Intake, Teilmessung, Erstproduktion und unabhängige Messung werden als
  ganze Prozesse auf das verbleibende Budget begrenzt, inklusive interner
  Wiederholungsversuche.
- Eine komplette Finisher-Heilerkette hat höchstens 20 Minuten; jedes Kind
  bekommt nur die verbleibende lokale und gemeinsame Zeit. Nach einem Timeout
  startet kein weiterer Heiler. Actions lässt Zeit für Isolation und Bericht.
- Konvergenz bleibt bei höchstens drei Runden, höchstens vier Nachschüben je
  Produktionsrunde und höchstens 45 Minuten innerhalb des gemeinsamen Fensters.
- Ein fehlender Messnachweis wird vor einer Produktionsrunde gemessen.
  Technisch fehlgeschlagene Schreiber stoppen weitere Schreiber.
- Timeout und Abbruch beenden Prozessgruppen, bevor die Isolation wiederhergestellt
  wird. SIGTERM führt temporär veröffentlichte Kandidaten durch die bytegenaue
  Wiederherstellung; der Finisher sichert auch bereits auf heute datierte Entwürfe.

Der 120-Minuten-Job behält damit eine getrennte Abschlussreserve für Chronik,
Sicherung, End-Gate und Artefakt. Git-Sicherung hat ihr eigenes Zeitlimit.

### 6. Hilfsgedächtnisse sind Belege, kein Wegwerfzustand

`data/reserve-intake.json` und `data/reserve-janitor-state.json` gehören jetzt
zum zulässigen Staging. Sie werden streng gelesen und atomar geschrieben;
defekte vorhandene Dateien werden nicht still durch leere Objekte ersetzt.
Scheitert das Intake-Provenienzjournal, wird die Besitzänderung am Entwurf
bytegenau zurückgenommen.

Beide Dateien sind `merge=binary`. Bei einem bekannten automatischen Konflikt
vereinigt `git_sync.sh` vollständige, unterschiedliche Intake-Ereignisse, ohne
wiederholte Adoptionen oder zusätzliche Herkunftsfelder wegzuwerfen. Janitor-Zähler
vereinigen nur unterschiedliche Läufe derselben Signatur; ein neuer Befund
erbt keine alten Lösch-Hits. Beschädigte Konfliktseiten stoppen die Sicherung.
LIVE- und menschliche Content-Konflikte erhalten keinen blinden Gewinner.

Die Snapshot-Heilung rekonstruiert diese Hilfsgedächtnisse ausdrücklich **nicht**:
Defekte Provenienz oder Löschbeweise stoppen, ohne einen intakten Nachweis
umzuschreiben oder die Historie auf null zu setzen. Die bestehenden drei
rekonstruierbaren/gesondert belegten primären Snapshot-Verträge bleiben getrennt.

### 7. Ein nachvollziehbarer Abschluss auch bei Push-Fehlern

`reserve_gate.py --report-json <pfad>` schreibt ein maschinenlesbares Urteil
und eine lesbare Step Summary: tatsächlicher frischer Vorrat, Ziel, Klasse,
Stufenausgänge, Kandidatenblocker und nächster Schritt. Ein echter Fehlbestand
ist `engpass`, nicht `ok`; stale/drift ist `nachweis`, Werkzeugausfall
`werkzeug`. Fehler beim Sichern bleiben Kettenfehler.

Nach dem Git-Sync werden die tatsächlichen Arbeitsbaum-Bytes erneut gegen
die Zertifikate geprüft. Fehlende Messungen begründen keine Vermutung über
API-Schlüssel oder Provider.

Der Workflow lädt JSON, End-Gate-Log, Zertifikate und vorhandene Fachberichte
mit `always()` als
`content-reserve-<run_id>-<run_attempt>` hoch (21 Tage Aufbewahrung,
versteckte Cache-Dateien eingeschlossen). Die Diagnose ist damit nicht vom
Erfolg des Push abhängig. Bei frühem Abbruch oder Cancellation können einzelne
Dateien fehlen; das Artefakt enthält dann die bereits vorhandenen Belege.

## Historische Blocker der ersten Abnahme (vor Main-Integration)

| Entwurf (Kurzname) | Verbleibender Grund |
|---|---|
| Energieausweis | RS3/RS4 und 16 unbelegte Zahlenbehauptungen |
| Kleine Energiespar-Tricks | 34 unbelegte Zahlenbehauptungen |
| Clevere Haushaltsgeräte | 43 unbelegte Zahlenbehauptungen |
| Wärmepumpe vs. Gasheizung | 29 unbelegte Zahlenbehauptungen; Flesch 59,6 |

Diese Zahlen sind Diagnosen der ersten realen lokalen Messung, keine aktuelle
Bestandsbehauptung nach den inzwischen übernommenen Reparaturen und keine pauschale
KI-Freigabe. Quellen-/Modellannahmen müssen redaktionell belegt werden; für
YMYL gelten weiterhin die vorhandenen menschlichen Freigaberegeln.

## Abnahme und Wiederholbarkeit

Die neue Regression `scripts/tests/test_reserve_operations.py` deckt Deadline,
Unterprozess-Abbruch, Frische, Wiederholungsläufe, Messausfälle, unveränderte
Originalbytes, schreibfreie Messung, bedarfsgerechte Arbeit und Workflow-Verträge
ab. `test_git_sync.py` enthält zusätzliche echte Rebase-Sabotageproben mit
Wegwerf-Remotes. Der Operations-Selbsttest ist im Governance-Minimum registriert;
`npm run test:reserve` enthält die neue Batterie.

**Lokale Abnahme vor Main-Integration:**

| Prüfung | Tatsächliches Ergebnis |
|---|---|
| Gesamtsuite | 2.889 Tests, grün; 2 ausgewiesene Skips (204,4 s) |
| Gesamtsuite unter Uhr +97 Tage | 2.889 Tests, grün; 4 ausgewiesene Skips (206,7 s) |
| KI-/Netz-Probe der Workflow-Selbsttests | 114 Selbsttests grün, ohne Modell und ohne Netz |
| Echte Reserve-Neubewertung | 7/6 READY aus 11 Entwürfen; Originalcontent unverändert |
| Reserve-Snapshot | Gültiges vollständiges JSON, echte SHA-256 und Redaktionsvertrag |
| Integritäts-Gate | 49 Kerndateien entsprechen dem echten verketteten Siegel |
| Governance | Quick-Prüfung und C1–C35-Selbsttest grün |
| Actions-Kontrollfläche | `automation_premium_audit.py --strict` grün |
| Syntax | Python, Workflow-YAML, package JSON, Bash und 3 Python-Heredocs grün |
| Produktions-Hugo-Build | Hugo Extended 0.164.0 grün; 84 Seiten, 1.838 statische Dateien |
| Produktions-Beweis-Ledger | `data/audit/` nach sämtlichen Prüfungen unverändert |

Die erste Gesamtsuite fand anpassungsbedürftige bestehende Vertragsfixtures
und das zunächst noch alte Integritäts-Siegel. Die Zeitprobe fand außerdem
einen Fixture-Zeitpunkt aus der verschobenen Elternuhr, während die getestete
CLI mit echter Uhr lief. Die Fixture benutzt jetzt ausdrücklich denselben
realen Zeitmaßstab wie ihr Kindprozess; weder Frische-Gate noch Zeitprobe
wurden abgeschwächt.

Die beiden geänderten FEST-Dateien wurden nach dem belegten Codecommit
`65d891f` mit dem echten `integrity_guard.py --heal` verkettet signiert und
mit `data/integrity_history.jsonl` committet. Keine kritische Datei wurde
neu gezeichnet; kein `--set-current`, kein manuell erfundenes Siegel.

Die neu eingebundene Artefakt-Action ist an den verifizierten Upstream-Commit
`cf430e030ddbb5b0abf93d22962f4752f3646cd9` (v7) gebunden, nicht an eine
bewegliche Tag-Referenz. Die Uhr- und KI-Proben sind keine Produktionsläufe:
Das spätere CI-Ergebnis des Pull Requests und der erste geplante Nachtlauf
sind getrennt von dieser lokalen Abnahme zu beurteilen.

Reproduzierbare Hauptprüfungen (in der installierten Projektumgebung):

```bash
python3 -m unittest discover -s scripts/tests -q
python3 scripts/selftest_clock.py --trap-discover scripts/tests --offset 97
python3 scripts/selftest_ki.py --trap-workflows
python3 scripts/reserve_artifacts.py --check
python3 scripts/governance_contract.py --quick
python3 scripts/integrity_guard.py --gate
hugo --minify --cleanDestinationDir
```

Echte Messung statt Neuproduktion:

```bash
python3 scripts/reserve_operations.py --preflight
RESERVE_WRITERS_ALLOWED=0 python3 scripts/reserve_readiness.py
python3 scripts/reserve_gate.py --report-json .cache/content-reserve/reserve-end-local.json
```

### Integrierter Stand und Konfliktauflösung

Der zunächst eröffnete PR #722 war wegen neuer Main-Commits konfliktbehaftet.
Es wurde `main` auf dem Arbeitsbranch integriert, nicht umgekehrt und ohne
Wechsel des Arena-Branches. Der Konflikt im Finisher verbindet nun beide
Schutzschichten: die neu hinzugekommene per-Heiler-Regressionsprüfung und
Rollback aus `main` **sowie** die begrenzten Prozessgruppen-/Budget-Aufrufe.
Die Schrittprüfung läuft auch nach Timeout/Abbruch; zwei zusätzliche Tests
beweisen die kombinierte Verdrahtung für Datei-, Slug- und Korpus-Scope.

Die vollständigen neuesten Maschinenartefakte und das Main-Siegel wurden
übernommen, nicht textweise zusammenkopiert. Anschließend wurde der belegte
FEST-Drift mit dem echten Signierer aus dem committeten Integrationsstand
`ad56631` geheilt. Dabei wurden auch zwei auf `main` bereits geänderte
FEST-Verträge (`publikations_vertrag.py`, `redaktions_standard.py`)
nachvollziehbar in das Siegel übernommen; die sechs kritischen Knoten wurden
nicht übersteuert. Die Redaktionstexte, Covers und Produktions-Audit-Ereignisse
aus `main` bleiben unverändert erhalten.

**Aktuelle Abnahme nach Integration:**

| Prüfung | Ergebnis des integrierten Stands |
|---|---|
| Gesamtsuite | **2.915 Tests grün**, 2 Skips (200,7 s) |
| Gesamtsuite unter Uhr +97 Tage | **2.915 Tests grün**, 4 Skips (200,0 s) |
| KI-/Netz-Probe | **114 Workflow-Selbsttests grün** |
| Kombinierter Budget-/Schritt-Regressionsschutz | 63 operative Tests; beide Schutzschichten bleiben aktiv |
| Echte komplette Neubewertung | **11/6 READY aus 11 Entwürfen**, 12.10.2026, **22:51:55 UTC** |
| Artikel und Produktions-Audit | Bytegenau wie im übernommenen Main-Stand `05178f3` |
| Integrität / Reserve-Snapshot / Actions-Audit | Alle grün; 49 signierte Kerndateien |
| Governance | C1–C36-Selbsttest und Quick-Prüfung grün |
| Produktions-Build | Hugo Extended 0.164.0 grün; 84 Seiten, 1.838 statische Dateien |

Die zwischenzeitlichen redaktionellen Main-Reparaturen beseitigten die vier
historischen Blocker. Das wurde hier nicht aus dem Main-Zähler übernommen,
sondern mit authentischen Werkzeugen erneut vollständig gemessen. Auch diese
Messung war lokal und schreibfrei für die Redaktion; keine CI-Lauf-ID wurde
erfunden. Das komplette aktuelle Zertifikat enthält echte Einzelzeitpunkte
und die unveränderten Bytes der inzwischen reparierten Artikel.

Die historische 7/6-Messung wird nicht als aktuelle Messung verkauft. Ebenso
sind die neuen Produktions-Audit-Ereignisse und Textänderungen ausschließlich
aus `main` übernommen; die lokalen Prüfungen ergänzten keine Produktionszeilen.
PR #722 ist die Übergabe für die Workflow-Änderungen. Ein Merge nach `main`,
ein Produktions-Dispatch und ein Deploy wurden nicht vorgenommen.

Lokale Tests und Publikationssimulationen gehören nicht in `data/audit/`.
Für diese Abnahme war das Audit-Ziel ausdrücklich ein ignorierter Cache-Pfad;
das versionierte Produktions-Beweis-Ledger wurde nicht verändert. Das
Integritäts-Siegel wird nur über den echten Signierer mit nachvollziehbarer
Herkunft aktualisiert, nicht per Hand oder durch eine Testattrappe.

## Runbook: Was bei Rot tun?

1. **Zuerst das Abschlussartefakt lesen**, nicht blind neue Texte generieren.
2. `wachen`: konkreten Selbsttest reparieren; keine Gate-Absenkung.
3. `werkzeug`: echten Preflight, Wörterbuch/UTF-8, Build und Paketinstallation
   prüfen; den unveränderten alten Nachweis nicht als frische Messung ausgeben.
4. `artefakt`: vollständige bekannte JSON-Fassung bzw. belegte Snapshot-Heilung;
   Hilfsgedächtnisse aus vollständiger vertrauenswürdiger Historie wiederherstellen,
   niemals zusammenkopieren oder kommentarlos leeren.
5. `nachweis`: bytegebunden neu messen (`reserve_recert.py --fix --refresh-stale`),
   bevor zusätzliche KI-Arbeit angefordert wird.
6. `engpass`: offene Kandidatengründe und freie Themen prüfen; nur belegbare
   Inhalte veredeln/produzieren. Faktische/YMYL-Freigaben nicht automatisieren.
7. Sicherungs-/Kettenfehler: tatsächlichen `git_sync`-Ausgang und Nach-Sync-Drift
   prüfen. Erst ein vollständiger, gesicherter aktueller Nachweis erfüllt den
   Produktionsvertrag.
