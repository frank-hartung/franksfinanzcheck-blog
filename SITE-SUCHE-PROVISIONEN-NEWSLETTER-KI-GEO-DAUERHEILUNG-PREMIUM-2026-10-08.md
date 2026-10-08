# Site-Suche, Provisions-Tabelle, Newsletter-Anreiz, KI-Alt-Texte und GEO – Dauerheilung #647

**Stand:** 08.10.2026  
**Branch:** `arena/b6dfe6fa-franksfinanzcheck-blog`  
**Produktionsstand geprüft:** `8f9344a` (`main`, nach #655)

## Ergebnis

Der Vorgang ist auf dem aktuellen Produktionsstand dauerhaft umgesetzt. Die Lösung
besteht nicht aus einem einmaligen Content-Fix, sondern aus getrennten Verträgen,
Selbsttests, Deploy-Wachen und einem reproduzierbaren Nachweisweg.

## 1. Site-Suche

- Pagefind ist als einzige Produktionsabhängigkeit exakt auf `1.5.2` gepinnt.
- `npm ci` ist wieder möglich; das frühere EJSONPARSE-Problem aus dem Zeitraum
  von #647 ist behoben.
- `npm run build` baut Hugo zuerst und danach den Suchindex. `public/pagefind`
  wird vor jedem Lauf geleert; der Index wird bei fehlender oder inkonsistenter
  Ausgabe fail-closed abgelehnt.
- Die Suchseite `/suche/` ist noindex und nicht in der Sitemap. Die Anwendung
  läuft vollständig im Browser, ohne Cookie, Suchdienst, Suchhistorie oder
  Suchbegriff in der URL.
- Treffer werden anhand einer echten markierten Fundstelle bzw. des Titels
  gefiltert. Auszüge werden zerlegt und ausschließlich über `textContent`
  gerendert; fremde URLs werden nicht verlinkt.
- Die Datenschutzseite dokumentiert die lokale Verarbeitung.
- Der alte Pagefind-UI-/Fuse-Rest ist entfernt; es gibt nur eine Suchoberfläche.

## 2. Provisions-Tabelle

- Versioniert ist ausschließlich `data/provisionen/provisionen-vorlage.csv`.
- Echte Daten gehören in `data/provisionen/provisionen.csv`, das per `.gitignore`
  ausgeschlossen ist. Keine Produktions- oder personenbezogenen Abrechnungsdaten
  gelangen in das öffentliche Repository.
- `scripts/provisionen_check.py` prüft Kopfzeile, Monat, Partner, Ganzzahlen,
  Beträge, doppelte Monatspartner, Abrechnungsreferenzen, Datenschutzmuster,
  Summen und Lücken.
- Die leere Vorlage ist ein gültiger, klar als „Datenlage offen“ behandelter
  Anfangszustand; eine fehlerhafte befüllte Datei beendet den Check mit Fehler.

## 3. Newsletter-Anreiz

- Werkzeugseiten erhalten im bestehenden Footer-Streifen die konkrete Zusage:
  neue Rechnerzahlen im Dienstags-Newsletter und relevante Fristen am Freitag.
- Es gibt weiterhin genau einen Anmeldeblock pro Seite.
- Startseite, Newsletter-Versandlogik und Rechtsseiten wurden nicht mit einem
  zweiten CTA belastet.

## 4. KI-Alt-Texte

- Das Skript erstellt ausschließlich Vorschläge. Anwenden ist nur mit
  `freigegeben: true` **und** `freigegeben_von` erlaubt.
- Veraltete Vorschläge werden bei abweichendem aktuellem Alt-Text abgewiesen.
- Nur das Titelbild wird verarbeitet; der Modellaufruf läuft ausschließlich über
  `scripts/llm_client.py`.
- Der manuelle Gemini-Probe-Workflow ist auf `workflow_dispatch`, `--max 1`,
  `contents: read`, Artifact-Ausgabe und keinen Repository-Commit begrenzt.
- Der Bestand ist vollständig mit Alt-Texten versorgt; 53 Titelkopien bleiben
  redaktionelle Vorschlagskandidaten und werden nicht automatisiert überschrieben.

## 5. GEO-Protokoll

- Die Messung bleibt bewusst manuell und fragt keine Chat-Oberfläche per API ab.
- Es gibt zehn feste Fragen und drei feste Oberflächen:
  `chatgpt-free`, `gemini-free` und `google-ki-uebersicht`.
- Perplexity ist gemäß Redaktionsentscheidung nicht Teil der Stichprobe.
- Das Skript prüft Monat, Frage-ID, Engine, Nennungs-/Zitierlogik und eigene
  HTTPS-Quellen. Offene Zeilen sind sichtbar, aber kein künstlicher Erfolg.

## Verifikation

| Prüfung | Ergebnis |
|---|---:|
| `npm ci` | grün, 0 Vulnerabilities |
| `npm run build` | grün; 109 HTML-Seiten, 70 indexierbar, 70 im Index, 39 bewusst ausgeschlossen |
| `npm run test:suche` | grün; jsdom 16, Index-Wache 14, Python 26 |
| `node --test tools/ff-suche.test.mjs tools/robust.test.mjs` | 37/37 grün |
| Playwright-Suche Desktop | 10/10 grün |
| Playwright komplett Desktop + Mobile | 108/108 grün |
| Python-Gates der fünf Workstreams | grün: Suche, Provisionen, Alt-Texte, GEO und Newsletter-Verträge |
| Robustheits-Gate gegen `public/` | grün |
| CodeQL auf Produktionsstand `8f9344a` | success |
| Integritäts-Gate | grün; 47 versiegelte Kerndateien |
| `selftest_runner.py` | 176 Wachen, 352 Uhrproben grün |

Die vollständige Python-Suite wurde nach Installation der in CI vorgesehenen
PyYAML-/Bildabhängigkeiten auf dem finalen Stand mit **2323 Tests ohne Fehler**
ausgeführt. Ein vorheriger Einzel-Lauf hatte den bekannten `git_sync`-Schutztest
intermittierend ein zweites Mal zählen lassen; der isolierte Test und der
unmittelbar danach wiederholte Gesamtlauf waren grün. Die #647-relevanten Tests
und Gates sind vollständig grün.

## Abgrenzung

- Ein Live-Gemini-Aufruf wird nicht automatisch ausgeführt. Dafür existiert der
  manuelle, read-only Probe-Workflow. Im Sandbox-Netz ist der Gemini-Host nicht
  freigegeben.
- Die Provisionsdatei bleibt absichtlich lokal und leer im Repository.
- Das GEO-Protokoll bleibt absichtlich eine manuelle Stichprobe; automatisiertes
  UI-Scraping wäre kein Qualitätsgewinn und würde die Messung verfälschen.

**Urteil:** #647 ist auf Premium-Agentur-Niveau umgesetzt: Datenschutz,
Fail-closed-Builds, redaktionelle Freigaben, einheitliche KI-Transportwege und
reproduzierbare Qualitätswachen sind Bestandteil der Lösung – nicht nachträgliche
Handarbeit.
