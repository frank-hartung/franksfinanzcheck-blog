# YMYL-Prüfqueue #713 – Siegelbruch beheben und Schreibpfade absichern

Stand: 12.10.2026. Lokale Umsetzung auf dem Arbeitsbranch; noch nicht gemergt oder auf Produktion nachgewiesen.

## Befund und belegte Ursache

Issue #713 meldete einen offenen Entwurf mit E17, acht gültige Freigaben und keine offenen Live-Reviews. Die lokale Prüfung reproduzierte genau diesen Befund.

`f95c3929a639bf37fdb0d50279df81279cad0a88` (Content-Bot, 09.10.2026) ergänzte im Privathaftpflicht-Artikel den Einstieg `Privathaftpflicht im Check: `. Der Keyword-Optimierer (`heal_first_paragraph` → `heal_article_file`, aufgerufen vom Publish-Gate) änderte damit einen bereits versiegelten Body. Das Publish-Gate erkannte den Siegelbruch korrekt und parkte den Artikel als Entwurf. Der vorangehende Commit `94b85bb` hatte lediglich Betriebsmetadaten geändert.

Die Absicherung aus #613 erfasste diesen SEO-Schreiber nicht. Außerdem prüften Sprachkern und Redaktionsstandard nur aktuell gültige Freigaben: Ein abgelaufenes oder beschädigtes Siegel machte den Text wieder automatisch bearbeitbar. Fehler der Vorprüfung führten ebenfalls zu einer Schreibfreigabe.

## Reparatur ohne fingierte Fachprüfung

Nur der nachträgliche Keyword-Zusatz wird zurückgenommen. Danach stimmt der Inhalt wieder mit dem vorhandenen SHA-256 `75156bc19868208b89163daaee087863dc28cfe35f64cd26a96e19dd805f7cf7` überein.

- Kein `--seal`, keine Änderung an Prüfer, Prüfdatum, Review-Termin oder Belegen.
- Keine zusätzliche Freigabehistorie und keine Behauptung einer neuen externen Quellenprüfung.
- `draft: true` und der historische Park-Grund bleiben erhalten. Keine automatische Re-Queue, Veröffentlichung oder Umgehung anderer Publikationskriterien.
- Ein gültiger technischer Prüfdatensatz ist kein eigenständiger Nachweis fachlicher Richtigkeit. Die dokumentierten Quellen und Bewertungen wurden in diesem Auftrag nicht erneut extern verifiziert.

## Dauerhafte technische Absicherung

Ein gemeinsamer Schreibvertrag in `editorial_review_gate.py` vergleicht geplante Alt-/Neufassungen anhand des bestehenden Fingerprint-Vertrags:

- Sobald im Ausgangstext ein Siegel oder `status: freigegeben` vorliegt, sind gebundene Inhalte und Prüfprotokolle vor automatischen Änderungen geschützt – unabhängig von Risikoeinstufung, Ablaufdatum und aktueller Hash-Gültigkeit.
- Titel, Beschreibung, Kurzantwort, Autor, Quellen, Body und Review bleiben gebunden. Das Entfernen des Reviews oder das Austauschen des Hashes ist kein Ausweg.
- Unlesbare/ungültige Fassungen blockieren die Schreiboperation (fail-closed).
- Betriebsmetadaten und bereits zulässige typografische Normalisierung bleiben möglich. Die Hash-Regeln selbst werden nicht aufgeweicht.

Eingebunden in:

| Schreibpfad | Verhalten |
|---|---|
| Keyword-Optimierer | Prüfung unmittelbar vor dem Schreiben; keine falsche Erfolgsmeldung bei Blockade |
| Gemeinsamer Publikationsvertrag | YMYL-Verstoß zusätzlich zu Lesbarkeit und Textverständnis; damit auch im Lesbarkeits-Heiler wirksam |
| Endredaktion | Prüfung am zentralen Dateischreiber; bei Ablehnung Arbeitskopie zurückladen und keinen Erfolg melden |
| Absatz-Heiler am Publish-Gate | Vor dem Schreiben prüfen; abgelehnte Reparaturen nicht als geheilt zählen |
| Sprachkern / Redaktionsstandard | Vorprüfung sperrt auch beschädigte und abgelaufene Freigaben; Messfehler öffnen die Sperre nicht |

Das ist eine Absicherung der genannten Schreibpfade, keine Behauptung einer repositoryweiten Dateisystemsperre. Neue Automatik-Schreiber müssen denselben Vertrag vor ihrer Schreiboperation aufrufen. Manuelle Änderungen sind weiterhin möglich und erfordern bei Siegelbruch eine echte redaktionelle Nachprüfung.

## Regression und Betrieb

`test_ymyl_write_contract.py` enthält zehn Offline-Regressionstests: Keyword-Stempel, gebundene Felder, Neuversiegelung/Review-Entfernung, erlaubte Metadaten/Typografie, unversiegelte Entwürfe, Parsefehler, Keyword-Dateischreiber, Endredaktions-Dateischreiber, konservative Vorprüfung und gemeinsamer Publikationsvertrag.

Die bestehende PR-Testsuite entdeckt diese Tests automatisch. Der werktägliche YMYL-Workflow führt nun zusätzlich die Gate-Tests und Schreibvertrags-Tests aus, bevor er die Queue erzeugt. Bei Testfehlern entsteht damit kein neuer grüner Queue-Abschluss.

Lokaler Nachweis:

- 114 Tests grün: YMYL-Schreibvertrag (10), Editorial-Gate (17), Endredaktion (22), Lesbarkeits-Heiler (31), Redaktionsstandard (8), Sprachpolitur (26).
- Selbsttests grün: Editorial-Gate, Publikationsvertrag, Endredaktion, Keyword-Optimierer, Redaktionsstandard, Grammar-Check und Sprachglatt.
- `editorial_review_gate.py --all --strict --report`: **76 Artikel, 9 Hochrisiko, 9 freigegeben, 0 blockiert**.
- `editorial_review_gate.py --published --strict`: **44 Artikel, 0 Hochrisiko, 0 blockiert**.
- `automation_premium_audit.py --strict` und `git diff --check`: Exit 0.
- Keine vollständige repositoryweite Testsuite oder Produktionsausführung in diesem Auftrag behauptet.

## Redaktioneller Ablauf bei einem neuen E17

1. Entwurf/Publikationssperre beibehalten; keine automatische Neuversiegelung.
2. Git-Diff und vorhandenes Siegel prüfen. Eine belegte unerwünschte Automatik-Änderung darf gezielt zurückgenommen werden, wenn danach das ursprüngliche Siegel wieder passt.
3. Bei gewollten inhaltlichen Änderungen: benannter fachlicher Prüfer, Aussagen-/Zahlenanker, aktuelle Belege, Änderungsgrund und Review-Termin; erst anschließend versiegeln.
4. Queue und striktes Gate erneut ausführen. Andere Publikationsgates bleiben eigenständig bindend.
5. Nach Merge den YMYL-Workflow auf dem integrierten Stand laufen lassen. Der bestehende Workflow pflegt bzw. schließt #713 anhand der neu gemessenen Queue; das Issue wird hier nicht vorzeitig geschlossen.
