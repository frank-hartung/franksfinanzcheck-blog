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

```sh
python3 scripts/faktenfrische.py --selftest
python3 -m unittest scripts.tests.test_faktenfrische_robustheit
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
