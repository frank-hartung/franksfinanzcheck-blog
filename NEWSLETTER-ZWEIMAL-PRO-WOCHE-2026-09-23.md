# Newsletter: zweimal pro Woche und sichtbar im Blog-Kopf

Stand: 23.09.2026. Implementiert im Arbeitszweig `arena/01a0cecd-franksfinanzcheck-blog`, noch nicht veröffentlicht. Es wurden keine echten Newsletter versendet und keine Brevo-Kontoeinstellungen verändert.

## Versandvertrag

- Dienstag und Freitag, jeweils geplant um 05:05 UTC (07:05 MESZ / 06:05 MEZ). GitHub und der E-Mail-Anbieter können die Zustellung verzögern.
- Höchstens zwei Newsletter-Ausgaben pro ISO-Kalenderwoche in `Europe/Berlin`, höchstens eine pro Versandtag. Ohne neue Inhalte keine Ausgabe.
- `scripts/newsletter_schedule.py` enthält den gemeinsamen Kalendervertrag. Sowohl manuelle Listenversände als auch Cron/Nachhol-Läufe unterliegen der Prüfung; auch `--trotz-qa` umgeht sie nicht.
- Cron `5 5 * * 2,5`; Nachhol-Wache `11 8 * * 2,5`. Vor der Nachkontrollzeit bzw. an Ruhetagen wird nichts nachgeholt.
- Sammelfenster auf sieben Tage erweitert, damit Artikel zwischen den beiden Terminen berücksichtigt werden. Die bestehende Artikel-Deduplizierung bleibt aktiv.
- Ein Versandtermin wird vor `sendNow` atomar im Journal reserviert. Bei Sendeproblemen bleibt er vorsichtshalber belegt. Defekte oder fehlende Journale blockieren den Listenversand; beschädigtes JSON wird auch beim Vorschau-Build nicht still überschrieben.
- Explizite Einzeltests nutzen ausschließlich `sendTest` und separate Teststatusfelder. Sie zählen ebenso wenig wie die Double-Opt-In-Bestätigung als Newsletter-Ausgabe.
- GitHub-Listenversand nur vom Standardzweig mit gemeinsamem Journal. Vorschauen und Einzeltests bleiben auf Arbeitszweigen möglich. Concurrency bleibt serialisiert; der Checkout lädt den aktuellen Branchstand. Ein fehlgeschlagener Status-Push ist nun ein harter Fehler statt einer beschwichtigenden Warnung.

### Reparatur der Artikelverbuchung

Bisher begrenzte erst die Mailvorlage auf fünf Artikel, während der Digest sämtliche gesammelten Artikel als versandt verbuchen konnte. Jetzt wird vor dem Rendern begrenzt und ausschließlich tatsächlich enthaltenes Material in `pending` übernommen.

## Anmeldung und Gestaltung

- Genau eine Newsletter-Leiste direkt unter der Navigation auf Startseite, Blogübersicht und Artikelseiten.
- Smaragdgrüner Hintergrund, gelber Anmeldebutton, klares Versprechen „Nur 2× pro Woche“, Versandtage und Abmeldehinweis.
- Regulärer Dokumentfluss, kein Pop-up, kein Sticky-Overlay und keine neuen externen Assets.
- Der Button führt direkt zum bestehenden Formular auf `/newsletter/#newsletter-anmeldung`. Das Formular steht jetzt vor der Musterausgabe.
- Doppelte Footer-/Artikel-CTAs entfernt. Newsletter- und Rechtsseiten bleiben ohne zusätzliche Anmeldewerbung.
- Sichtbarer Tastaturfokus, ausreichend große Touch-Ziele, mobile Darstellung und gesonderte Dark-Mode-Regeln. Die Kontrastprüfung berücksichtigt jetzt auch halbtransparente Textfarben; dadurch wurde ein Konflikt mit dem vorhandenen Dark-Mode-Farbtoken erkannt und behoben.
- Versandversprechen in Konfiguration, Landingpage, Formular, Präferenzseite, Datenschutz und aktueller Betriebsdokumentation aktualisiert. Historische Vorfallberichte bleiben historisch.

## Verifikation

| Prüfung | Ergebnis |
|---|---|
| Hugo Extended 0.164.0 Build | erfolgreich |
| `python3 -m unittest discover -s scripts/tests -p 'test_newsletter*.py'` | 147 Tests grün |
| `python3 scripts/newsletter_digest.py --selftest` | 55 Fälle grün |
| `python3 scripts/newsletter_cadence.py --selftest` | 14 Fälle grün |
| `python3 scripts/newsletter_qa.py --selftest` | 35 Fälle grün |
| `npx playwright test --workers=2` | 51 Tests grün |
| Newsletter-Browsersuite nach finaler Dark-Mode-Korrektur | 15 Tests grün |
| `python3 scripts/newsletter_studio.py --brand` | Marken-/Themenprüfung grün |
| `python3 scripts/newsletter_digest.py --check` | Capture im Build aktiv, keine Funde |
| `python3 scripts/layout_audit.py` | keine neuen Layoutfehler, DOM-Budget eingehalten |
| `git diff --check` | sauber |

Browser: Chromium aus dem dokumentierten `@sparticuz/chromium`-Fallback, weil der Playwright-CDN-Download in dieser Umgebung fehlschlug. Keine Änderung der Projektabhängigkeiten. Responsive Newsletter-Prüfung bei 320, 390, 768 und 1280 Pixeln, Hell/Dunkel, Tastatur und zusätzlich ohne JavaScript. Screenshots liegen lokal unter `shots/newsletter-{desktop,mobile}-{light,dark}.png` (nicht versioniert).

## Offene Produktionsfreigabe

**Owner: human · Severity: P2 · Channel: Produktionsfreigabe / Integrität**

`python3 scripts/integrity_guard.py --drift-audit` meldet zwei bewusst geänderte, geschützte Kerndateien:

1. `hugo.toml`: Versandversprechen von werktäglich auf zweimal wöchentlich geändert.
2. `layouts/_partials/extend_footer.html`: doppelten Newsletter-Kasten entfernt; die zentrale Platzierungslogik liegt jetzt in `newsletter_strip.html`.

Das Gate verlangt hierfür eine Betreiberentscheidung. Das Siegel wurde weder manuell bearbeitet noch automatisch neu signiert. Vor Merge/Deployment Änderungen prüfen und nach bewusster Freigabe den vorgesehenen Signaturweg `python3 scripts/integrity_guard.py --set-current` verwenden. Anschließend Integritätsprüfung und normale Deployment-Pipeline ausführen. Es wurde nichts gepusht und kein Produktionsworkflow ausgelöst.

Vor dem ersten produktiven Versand zusätzlich die Brevo-Kampagnenhistorie mit `data/newsletter_state.json` abgleichen. Das hier vorhandene Journal enthält nur `pending`, keine belegte Versandhistorie. Ein eventuell bereits erfolgter Versand dieser Woche muss als `versand_termine` mit zeitzonenbehaftetem ISO-Zeitstempel übernommen werden; sonst kennt der neue Zähler diese alte Ausgabe nicht.

**Betriebsgrenze:** Der Schutz gilt für diesen Repository-Versand und sein gesichertes Journal, nicht für unabhängig im Brevo-Konto eingerichtete Kampagnen oder Automationen. Diese wurden nicht geprüft. Bei abgebrochenem Runner oder fehlgeschlagenem Journal-Push vor einem weiteren Lauf die Brevo-Historie abgleichen; ein nur lokal reservierter Termin ist ohne erfolgreichen Status-Push nicht über Runner hinweg gesichert. Der Schließpfad ist Freigabe, Journalabgleich, Deployment und Prüfung des ersten planmäßigen Laufs – kein automatisches Wiederholen bei unklarem Ergebnis.

### Nachtrag: ausdrücklicher Merge-Auftrag am 23.09.2026

Nach Eröffnung von PR #359 hat der Betreiber ausdrücklich dessen Merge beauftragt.
Die oben noch offene Freigabe der beiden geschützten Dateien wurde daraufhin über
`python3 scripts/integrity_guard.py --set-current` umgesetzt. Das Werkzeug hat
nur diese zwei abweichenden Kerndateien neu gezeichnet und den Ursprung `8c360de`
in der Integritätsakte dokumentiert. Das Gate selbst bleibt unverändert aktiv.
Der technische Merge erfolgt erst nach Prüfung des aktualisierten PR-Stands;
Brevo-Konto-/Historienabgleich und unabhängige Automationen wurden weiterhin
nicht geprüft, und es wurde kein Newsletter manuell ausgelöst.
