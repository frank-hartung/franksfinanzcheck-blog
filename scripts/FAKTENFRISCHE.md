# Faktenfrische: Betrieb und Grenzen

`scripts/faktenfrische.py` recherchiert nach dem Vertrag in
`data/agent_reach/faktenfrische.yaml`. Der reguläre Lauf ist ein Trockenlauf
**für Artikeländerungen**: Report, Queue, Historie und Dossiers werden auch
ohne `--apply` geschrieben. `--offline` verzichtet auf Netz und KI, schreibt
aber ebenfalls diese Laufartefakte. `--apply` aktiviert Frontmatter-Änderungen;
der Artikeltext und `lastmod` bleiben unangetastet. Ein Faktencheck-Stempel
wird nur gesetzt, wenn mindestens eine allowlistfähige Quelle vorliegt und
die KI-Fachprüfung vollständig und schema-konform abgeschlossen wurde.
Bei Ausfall bleibt der Artikel unverändert und in der Queue; `--apply`
liefert Exit 4 (bei vollständigem Kanalausfall Exit 3). Der Bestands-Workflow
sichert Diagnoseartefakte und meldet den Lauf anschließend als fehlgeschlagen.
YMYL-Schutz und Re-Queue-Gate bleiben maßgeblich.

Seiten sind isoliert (#984, 01.11.2026): Wirft eine Seite, wird sie mit
Seite und Ursache als Abbruch geführt, der Lauf arbeitet weiter und schreibt
Queue, Report, Historie und Ledger. Der Lauf endet dann mit Exit 5 – die
Beweise überleben den Fehler, der Ausfall bleibt trotzdem sichtbar. Nach dem
Schreiben wird die hinterlassene Fassung neu gelesen; sie ersetzt den
Lauf-Datensatz nicht, dessen `_faellig`/`_geo`/`bereich` nur der Lauf kennt.

KI-Antworten müssen das erwartete JSON-Schema erfüllen, andernfalls wird der
nächste verfügbare Anbieter versucht. Quellen-URLs müssen im Dossier stehen und
auf der Allowlist liegen; Titel und Datum stammen aus dem Dossier, der
Herausgeber aus der Allowlist. Ungedeckte Beleg-URLs in Befunden werden
entfernt, die Befunde selbst bleiben zur redaktionellen Prüfung erhalten.
Ein Dossier-Treffer oder eine erlaubte Domain beweist **nicht**, dass eine
konkrete Aussage richtig ist. Auch ein Faktencheck-Stempel ist keine
redaktionelle Freigabe. Der Report und die Queue zeigen den KI-Status, damit
„keine Befunde“ nicht mit einer durchgeführten Fachprüfung verwechselt wird.

RSS- und Web-Abrufe sind zeitlich und auf 2 MiB pro Antwort begrenzt. Ein
seit dem Einlesen geänderter Artikel wird nicht überschrieben. Vor dem
Schreiben führt `--apply` den Selbsttest aus.

## Offene Fachbefunde (F4): Arbeitsliste statt Handarbeit (#912)

Ein Befund verschwindet nicht durch Zeit. Er wird an genau **einem**
dokumentierten menschlichen Entscheid geschlossen, gebunden an den
**Text-Hash** (ohne Quellen) – nicht an die Prüffassung. Damit bleibt ein
Befund auch dann schließbar, wenn der Text zu seiner Heilung geändert wurde
oder der Lauf die Belegkette erneuert hat (bis 02.11.2026 war genau das
nicht möglich: 21 von 57 Befunden standen an einer überholten Fassung,
20 weitere ohne Hash).

```sh
python3 scripts/faktenfrische_befund_akte.py --schreiben   # BEFUND-AKTE.md + Zustand
python3 scripts/faktenfrische_befund_akte.py --wache       # Exit 1 ohne Schließweg
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> \
  --von "Name" --begruendung "was geprüft/geändert wurde" [--beleg URL]
python3 scripts/faktenfrische_befund_ledger.py --wache     # dito, Ledger-scharf
```

`BEFUND-AKTE.md` ist die Sicht für Menschen (ID, Typ, Alter, Fassungsstand,
Beanstandung, Beleg, fertiger Befehl), `data/faktenfrische_befunde_state.json`
das Siegel (Zahlen für Ticket und Scorecard), `data/faktenfrische_entscheidungen.yaml`
die Schließakte. Frist und Eskalation stehen in `befunde.*` der SSOT. Die
Akte entscheidet nichts; ohne Person und Begründung (≥ 20 Zeichen) schreibt
der Befehl nichts. Governance: C46.

### Datums-Lift und Befundidentität (#1073)

Der Reserve-Finisher darf einen Entwurf auf das aktuelle Datum heben. Der
Ordner-Slug ändert sich dabei, die Identität bereits erhobener Fachbefunde
nicht. `reserve_finisher.lift_to_today()` trägt den bisherigen Slug deshalb
idempotent in `faktenfrische_aliases` am aktuellen Artikel ein und bewahrt
frühere Einträge. Beispiel:

```yaml
faktenfrische_aliases:
  - "2026-11-01-thema"
  - "2026-11-03-thema"
```

Das ist **interne Herkunft**, keine öffentliche Weiterleitung und kein
Ersatz für `data/weiterleitungen.yaml`. Das Ledger löst die Kette auf den
aktuellen Slug auf, lässt Befund-ID, Beanstandung und beide Fassungs-Hashes
unverändert und zeigt `ursprungs_slug` in Akte und Zustand. Alte menschliche
Entscheidungen bleiben auffindbar; eine spätere Textänderung öffnet sie wie
bisher erneut. `publish_gate.fakten_befund_failures()` blockiert dadurch den
aktuellen Kandidaten-Slug weiterhin. Ein Re-Dating schließt nichts.

Alias und Artikel stehen im selben Finisher-Snapshot: Das katastrophale
Rollback stellt beide gemeinsam wieder her. Bei einer anderen manuellen
Ordner-Umbenennung muss die Redaktion den alten Slug ebenfalls in dieses Feld
aufnehmen. Fehlt die Herkunft oder wurde die Seite wirklich gelöscht, bleibt
die Schließweg-Wache absichtlich rot. Ungültige Listen, Selbstreferenzen,
Schleifen, Kollisionen mit einem aktuellen Slug und ein Alias mit zwei
Zielartikeln sind Werkzeugfehler – niemals ein stiller Abschluss.

```sh
python3 scripts/faktenfrische.py --selftest
python3 -m unittest scripts.tests.test_faktenfrische_robustheit
python3 -m unittest scripts.tests.test_faktenfrische_befund_akte
python3 -m unittest scripts.tests.test_faktenfrische_slug_identitaet
python3 scripts/faktenfrische.py --offline --max 3
```

Die Offline-Tests benötigen die Projektabhängigkeiten PyYAML und feedparser;
sie verwenden weder echte Netzabrufe noch KI-Schlüssel. Live-Kanäle und
Provider müssen separat in der vorgesehenen Betriebsumgebung geprüft werden.

## Nachlese: kein Befund bleibt nur im Dossier (#984)

Ein Dossier entsteht **vor** der Bilanz des Laufs. Bricht der Lauf danach ab,
lagen seine Befunde bis zum 01.11.2026 ausschließlich in
`data/research/artikel/<slug>.json` – unsichtbar für Redaktion, Publish-Gate
und Scorecard, während die Maschine „nichts gefunden“ meldete. Die Nachlese
liest die Dossiers und ergänzt ausschließlich, was im Ledger fehlt:

```sh
python3 scripts/faktenfrische_befund_ledger.py --nachlese           # Trockenlauf
python3 scripts/faktenfrische_befund_ledger.py --nachlese --apply   # ergänzen
```

Sie ist idempotent, schließt nie einen Befund und übernimmt nichts ohne
echten Fassungs-Hash – eine Entscheidung muss an genau die geprüfte Fassung
gebunden bleiben. Der Bestands-Workflow fährt sie nach jedem Lauf (auch nach
einem Abbruch) und committet das Ergebnis mit den Dossiers.

## Befund-Register und Dauerheilung

Ein Laufbericht ist ein Schnappschuss; die Queue wird beim nächsten Lauf
überschrieben. Eine redaktionelle Heilung braucht deshalb eine eigene
Schließakte: `data/faktenfrische_befunde_<issue>.yaml` hält je Befund
die Entscheidung, den Status, den Beleg (Allowlist **und** Artikelquelle)
sowie Bedeutungsanker fest. Die zugehörige Regression prüft zusätzlich
Rechenwege, Metadaten, GEO-Reife, Publish-Gates und den Prüfauftrag im
SYSTEM_PROMPT. Damit ist „behoben“ nachvollziehbar, und ein Rückfall wird
rot, bevor er als neuer Befund teuer wird. Die Registerdatei ist – wie
dieser Vertrag – menschlich kuratiert; die Maschine schreibt sie nie.

Beispiel #911 (30.10.2026): zehn Befunde in zwei Artikeln, Register
`data/faktenfrische_befunde_911.yaml`, Regression
`scripts/tests/test_faktenfrische_911.py`, Aufruf
`npm run test:faktenfrische:911`.

Beispiel #996 (03.11.2026): 16 Befunde in vier Gasartikeln, Register
`data/faktenfrische_befunde_996.yaml`, Regression
`scripts/tests/test_faktenfrische_996.py`, Aufruf
`npm run test:faktenfrische:996`. Die Heilung fand zwei Rückfälle auf den
Werbeflächen (`pin_description`), die auf `main` eine rote Regression
hinterließen. Seitdem gilt: Pin-/Social-Texte sind Aussageflächen – die
Fachprüfung erhält sie (`PIN-TITEL`/`PIN-BESCHREIBUNG`), Regel 11 des
SYSTEM_PROMPT prüft sie mit, und `pruef_hash` bindet sie in die Fassung
ein. Eine redaktionelle Heilung ist keine Ledger-Signatur: Die Befunde
bleiben offen, bis der Inhaber sie fassungsgebunden entscheidet
(`data/faktenfrische_entscheidungen.yaml`).

## KI-Routing

Die Reihenfolge stammt zur Laufzeit aus `routing.faktenpruefung` in
`data/ki_transportweg.yaml`: Gemini zuerst, danach Groq, NVIDIA und
Cloudflare. Gemini bringt ein anderes Modellhaus in die erste Position;
die Hoster-Rotation fängt technische Ausfälle ab. Das ist eine
Architekturentscheidung, kein Nachweis höherer Qualität oder Verfügbarkeit.
Die Modell-ID stammt aus dem gemeinsamen Client (`GEMINI_MODEL` kann sie
überschreiben); der konfigurierte Gemini-Standard ist ein Preview-Modell und
muss im Zielkonto verfügbar sein. Kontingente und Kostenbedingungen des
jeweiligen Kontos sind vor Produktivbetrieb zu prüfen.

Pro Anbieter wird nur eine nachweislich vollständig abgeschlossene Antwort
mit gültigem Schema akzeptiert; bei Fehler oder ungültiger Antwort folgt der
nächste verfügbare Anbieter. Timeout und Versuche stehen im Recherchevertrag.
Ein gesetzter Schlüssel ist kein Verfügbarkeitsnachweis; zum Betrieb muss
mindestens ein funktionierender API-Zugang als Actions-Secret vorhanden sein.
Die Fachprüfung ersetzt keine menschliche Abnahme.

### Nachlauf der Befundakte (#1120)

Die Akte und ihr JSON-Zustand sind eine abgeleitete Arbeitsliste, keine
redaktionelle Entscheidung. `--wache --json` prüft die vollständige Projektion
am dokumentierten Stichtag (einschließlich Markdown, Befund-IDs, Fassungen,
Konfiguration und Live-Sicht); nur der technische Erzeugungszeitpunkt wird
ignoriert. Ein gleicher Zähler allein beweist keine Aktualität. Bei
`veraltet: true` beide Dateien mit `--schreiben` neu erzeugen und gemeinsam
prüfen. Ledger-/Werkzeugfehler bleiben getrennt sichtbar.

Der Workflow **Befundakte nachziehen** reagiert auf relevante menschliche
Pushes und läuft zusätzlich alle drei Stunden, weil GitHub Pushes mit
`GITHUB_TOKEN` und `[skip ci]` nicht zuverlässig als Workflow-Auslöser
behandelt. GitHub-Zeitläufe sind Best Effort, keine garantierte Frist; bei
Bedarf auf `main` manuell starten. Der Nachzug holt den neuesten `main`-Stand,
berechnet beide Dateien darauf und pusht nur Fast-Forward. Bei einem Rennen
wird neu berechnet statt eine alte Projektion zu rebasen; nach fünf erfolglosen
Pushes bleibt der Lauf rot. Strukturreparaturen der Schließakte werden vorher
separat geprüft und gesichert; Fachentscheidungen trifft die Automatik nicht.
Die unabhängige Nachlauf-Wache meldet Abweichungen weiterhin, sie blockiert
keine Auslieferung. Regressionen: `python3 -m unittest scripts.tests.test_befund_akte_nachlauf`.
