# Issue-Prüfung und Reparaturen – 14.11.2026

## Umfang und Aussagegrenze

Alle 27 beim Start offenen GitHub-Issues wurden eingelesen und nach Ursachen
zusammengefasst. Das ist **kein vollständiger Produktionsabschluss**. Die
Änderungen liegen auf dem Arbeitsbranch; kein Merge, kein Deploy und keine
Issue-Schließung wurden ausgelöst. Historische Issue-Texte sind kein Beweis
für den heutigen Checkout oder Live-Stand.

GitHub-Issues waren über `gh` lesbar. Der Abruf der Actions-Logs scheiterte
beim Weiterleiten auf `results-receiver.actions.githubusercontent.com`
(Netzbeschränkung der Arbeitsumgebung). Externe Quellen und Live-Dienste sind
hier nicht allgemein erreichbar. Deshalb keine spekulativen Schlüsselwechsel,
Cloudflare-Änderungen, Produktionsfreigaben oder massenhaften Workflow-Neustarts.

## Behoben und lokal nachgewiesen

### Metadaten / #1179

Aktuell reproduzierbarer Befund: 65 Zeichen im Titel des Kreditkarten-Entwurfs
vom 11.11.2026. Der Titel ist auf 57 Zeichen gekürzt; Entwurfsstatus und
fachliche Freigabe bleiben unverändert. Cover einschließlich 14 responsiven
JPG-/WebP-/AVIF-Varianten und Manifest wurden mit dem vorhandenen Renderer neu
erzeugt. Der Herkunftsbeleg wurde danach passend zur tatsächlichen Datei
aktualisiert. Das neu generierte FCP-Manifest beseitigt nebenbei den zuvor
doppelten JSON-Schlüssel `generatedAt`.

Zusätzlicher Regressionstest in `test_metadaten_wache.py`: Der echte
Repository-Bestand einschließlich Entwürfen muss die Metadatenprüfung bestehen.
Er prüft nur, heilt und veröffentlicht nichts. Isolierte Parser-Tests allein
würden einen redaktionell neu eingeführten Bestandsfehler nicht erkennen.

### Rollen-Wiedervorlage / #1181, #1216, Teil von #1211

Die Wiedervorlage 13.11.2026 war abgelaufen. Nicht das Weiterleitungswerkzeug,
sondern die dokumentierte Rollenentscheidung war lokal rot.

Neubewertung der zwei Seiten am 14.11.2026:

- Kontrollpfad: Vertragsprüfung an einem Nachmittag.
- Jahresplan: Abbuchungen sammeln, Kategorien und Fristen anlegen.
- Titelüberschneidung 0,00; keine gemeinsamen Zwischenüberschriften;
  0,0 % identische Sätze bei 188/137 Sätzen.
- Rollenlinks stehen in beiden Richtungen im Artikeltext.
- Vorhandener GSC-Import, Metadatenstand 12.11.2026: Kontrollpfad
  24 Impressionen / Position 45,92; Jahresplan 1 / 7,0.
  **Keine neue Live-Messung** und kein Nachweis einer Indexierungsverbesserung.

Die Rollentrennung wird deshalb beibehalten; keine Zusammenführung nach Regel F.
Begründungen und Historie stehen im Entscheidungsregister, nächste Prüfung
12.12.2026. Das ist ausdrücklich keine fachliche Freigabe der Artikel.

Dauerhafter Rückfallschutz: Der bestehende Aufruf `konsolidierung.py --rollenpaare`
warnt ab sieben Tagen vor Fälligkeit mit einer GitHub-Actions-Annotation;
JSON-Ausgabe enthält zusätzlich `warnungen`. Fristen werden nie automatisch
verlängert. Ungültige und überfällige Fristen bleiben harte Befunde. Tests
prüfen die Grenzen −1/0/1/7/8 Tage, Unveränderlichkeit des Registers und die
Trennung zwischen Warnung und hartem Fehler. Keine Workflow-Schutzregel geändert.

## Prüfungen

Mit isolierter Python-Umgebung und den vorhandenen hash-gepinnten Requirements:

- 124 gezielte Unit-/Regressionstests bestanden:
  `test_metadaten_wache`, `test_keyword_optimizer`, `test_meta_optimizer`,
  `test_weiterleitungen`, `test_konsolidierung`, `test_veroeffentlichungs_wache`.
- Konsolidierungs-Selbsttest: 34 Fälle bestanden.
- Weiterleitungen: Selbsttest grün; 251 Quellen und erzeugte Seiten konsistent.
- Rollenpaarprüfung: keine Befunde und aktuell keine Vorwarnungen.
- Nachlauf-Wache: grün (Metadaten, Frontmatter, Register, Akte, Kanaltreue).
- Cover-Herkunft: 132 Cover reproduziert, 0 Befunde; zwei statische/Markenseiten
  liegen definitionsgemäß außerhalb des Renderbereichs.
- Hugo 0.168.0 Extended: Build erfolgreich.
- SEO-Cockpit nach erneutem Build: 142 Seiten, 115 indexierbar, P1=0, P2=0,
  P3=10; Grenzen für Description-Länge, -Breite und Überschriftenfolge bestanden.
- `git diff --check`: grün.

Ein zusätzlich begonnener Gesamtlauf aller Python-Tests wurde nach längerer
Laufzeit ohne Abschluss gestoppt. Er wird ausdrücklich **nicht** als bestanden
gezählt. Browser-E2E und vollständige Produktionsabnahme wurden nicht ausgeführt.

## Vollständige Zuordnung der offenen Issues

| Issues | Ergebnis / noch erforderlicher Nachweis |
|---|---|
| #1179 | Aktuellen M1-Befund behoben; Nachlauf und Metadaten lokal grün. Vollständiger E2E-Lauf auf integriertem Stand fehlt. |
| #1181, #1216 | Rollenentscheidung nach tatsächlicher Quellenprüfung erneuert, Vorwarnung ergänzt. Erfolgreiche reguläre Läufe auf `main` fehlen. |
| #1211 | Lokaler Rollen-Blocker behoben. Reserve-Zertifizierung und erfolgreiche Live-Auslieferung weiterhin gesondert nachzuweisen. |
| #1204, #1202, #1200, #1190, #1186, #1178, #1158, #1156, #1155, #1150, #1146 | Historische Nachlauf-Befunde: aktuelle Nachlauf-Wache grün. Keine Quellen oder Aktenentscheidungen bloß zum Schließen der Tickets erfunden. Integrierten Nachlauf abwarten. |
| #1110 | Aktuelle Metadatenprüfung meldet keine fehlende Kurzantwort mehr. Keine neue redaktionelle Freigabe vorgenommen; historisches Issue nicht ohne integrierten Nachweis schließen. |
| #1072 | Weiterhin echte Facharbeit: aktuelle lokale Akte zählt 155 offene Befunde auf 39 Seiten, davon 97 auf 25 Live-Seiten; 15 Befunde über Frist. 102 beziehen sich auf inzwischen geänderte Fassungen und benötigen Prüfung des heutigen Texts. Nicht pauschal entschieden oder ausgebucht. |
| #1193 | Lokal erfolgreicher Build und SEO-/Nachlaufprüfung ersetzen keine Release-Scorecard. Fehlgeschlagenen Produktionsschritt anhand erreichbarer Logs/Artefakte diagnostizieren und Scorecard auf integriertem Stand neu messen. |
| #1215 | Content-Engine-Abschluss meldet laut Issue Defizit. Ohne konkrete Classifier-Annotation keine belegte Ursache; Reserve-/Tagesziel nicht absenken und Abschluss nicht auf Erfolg umstellen. |
| #1191 | Recherche unvollständig. Laufdiagnose und konkrete Quellenerreichbarkeit fehlen; keine pauschale Ausbuchung von Fachbefunden. |
| #1194 | Belegfähige Werkbank-Quelle fehlt. SearXNG/API und Quellenerreichbarkeit im Produktionslauf prüfen; Allowlist nicht blind erweitern. |
| #1196 | Zwei externe Live-Prüfungen fehlen: Header und Worker. Cloudflare-/Environment-Freigaben und kompletter Live-Nachweis nach vorhandenem Betriebsrunbook nötig. Keine Schutzmechanismen abgeschaltet. |
| #1153 | Design-Budgetmessung nicht reproduziert; Messartefakte und vollständige Browser-/Budgetprüfung nötig. Keine Budgets gelockert. |
| #1152 | Felddaten-/Laborurteil nicht reproduziert; CrUX-/Lighthouse-Artefakte nötig. Keine Felddaten erfunden. |
| #1151 | Lesbarkeit der genannten Entwürfe bleibt redaktionelle Aufgabe; keine Publish-Schwelle gesenkt oder Freigabe fingiert. |
| #1028 | Rechts-/Betreiber- und Live-Abnahme bleibt offen; vorhandene KI-Transparenz-Checkliste abarbeiten. Lokaler Cover-Nachweis allein genügt nicht. |
| #448 | Externe Domain-Sperre bei Pinterest und anschließende Autorisierung erfordern den Betreiber; Kanal bleibt geparkt. |

## Nächster sicherer Abnahmeweg

1. Änderungen reviewen und reguläre Branch-Prüfungen ausführen.
2. Nach Integration regulären Deploy, Gesundheitscheck, Nachlauf und E2E
   beobachten; nur ein erfolgreicher Produktionslauf belegt deren Heilung.
3. Fachbefunde aus #1072 je ID anhand aktueller Texte und erreichbarer Quellen
   bearbeiten; nur tatsächlich geprüfte Änderungen fachlich entscheiden.
4. Externe Betriebs-/Rechtsfreigaben (#1196, #1028, #448) getrennt nachweisen.
5. Issues erst anhand dieser Nachweise schließen, nicht aufgrund dieses Berichts.
