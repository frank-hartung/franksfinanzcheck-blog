# Technischer Voll-Audit & Selbstheilung – FranksFinanzcheck

**Prüfstand:** 10.11.2026 · **Branch:** `arena/51596455-franksfinanzcheck-blog`

## Management-Zusammenfassung

Der Quellbestand hat bereits eine ungewöhnlich umfangreiche Automatisierung:
102 GitHub-Workflows, davon 73 mit Zeitplan, tägliche redaktionelle
Selbstheilung, tägliche Faktenfrische- und Produktionswachen, Build-, SEO-,
Accessibility-, Security-, Affiliate- und Regressions-Gates. Deshalb wurde
keine zweite, konkurrierende „Master-Wache“ daneben gebaut. Stattdessen wurden
beim vollständigen Repository-/Build-/Browser-Audit die vorhandenen Gates
repariert und ihre Regressionen an den bestehenden Prüfpfad gebunden. Die
Nachprüfung hat außerdem zwei Messfehler im Automation-Audit korrigiert und die
übrig gebliebenen Workflow-, Fallback- und Pagefind-Punkte umgesetzt, statt sie
als offene Empfehlung stehen zu lassen.

**Ergebnis:** Nach den Reparaturen ist der vollständige Python-Regressionslauf
mit **5.699 Tests erfolgreich** (4 dokumentierte Umgebungs-/Fixture-Skips; 5.703 insgesamt ausgeführt),
der vollständige Playwright-Lauf mit **180/180 E2E-Tests erfolgreich**. Die
zuletzt geänderte Sprachdatei-Whitelist wurde zusätzlich mit
`ResourceWarning` als Fehler geprüft. Die kritischen Accessibility- und
Faktenfrische-Gegenproben wurden nach der Reparatur erneut gezielt ausgeführt.

## Umfang und Messungen

| Bereich | Messung | Ergebnis |
|---|---:|---|
| Hugo-Produktionsbuild | Hugo Extended 0.168.0, echter Build | **grün** · 121 Seiten, 19 Paginatoren, 40 Nicht-Seiten-Dateien, 2.450 statische Dateien |
| Suchindex | 412 gebaute HTML-Dateien | **111 indexierbare Seiten = 111 im Pagefind-Index**; 301 Ausschlüsse sind laut Indexvertrag beabsichtigt |
| SEO-Cockpit | 136 geprüfte Seiten, 111 indexierbar | **P1: 0, P2: 0, P3: 10**; Description-/Heading-Blocker: 0 |
| Accessibility / Browser | vollständige E2E-Suite, Desktop und Mobile | **180/180 grün**; Axe/WCAG-Seitenabdeckung, Pillars, Artikel, Werkzeuge und Themen-Ratgeber eingeschlossen |
| Affiliate | echte Browser-Regressionssuite | Redirect-Stubs, `sponsored`/`nofollow`/`noopener`, Disclosure und Messparameter grün |
| Metadaten | 156 Frontmatter-Dateien | **0 Blocker, 0 Hinweise** |
| URL-/Weiterleitungsbestand | 251 Redirect-Regeln, 115 Live-URLs | Quelle und gerenderte Seiten stimmen überein; 12 neu hinzugekommene Live-URLs sind als Bestandshinweis erfasst, kein Fehler |
| Workflow-Kontrollfläche | 102 Workflows, 73 geplant | **0** ungepinnte Action-Refs, **0** Jobs ohne Timeout, **0** Workflows ohne explizite Permissions, **0** fehlende/ungültige Workflow- oder Job-Concurrency-Verträge, **0** doppelte Namen |
| Selbstheilungs-/Faktenfrische-Regression | 126 Artikel | Sockel 5, Limit 18; 163 % aktuelle Deckung; 0 überfällige Artikel; 0 projizierte Fristverletzungen bis 10.03.2027 |
| Regressionstests | `unittest discover -s scripts/tests` | **5.699 bestanden, 4 übersprungen, 0 fehlgeschlagen** |

Die Pagefind-Warnung zur textförmigen Google-Verifikationsdatei wurde
beseitigt, ohne die Verifikation oder Auslieferung zu ändern: `scripts/pagefind_build.py`
nimmt `google*.html` nur während des Indexlaufs aus `public/` und stellt die
Datei anschließend bytegleich wieder her. Pagefind fand danach 411 zu parsende
HTML-Dateien; die unabhängige Index-Wache bestätigt weiterhin 412 gebaute
HTML-Seiten, 111 indexierbare Seiten und exakt 111 im Index. Regressionen
prüfen die bytegleiche Wiederherstellung sowohl bei Erfolg als auch bei einem
Pagefind-Fehler.

## Behobene Befunde

### 1. Faktenfrische: echter SLA-Bruch bei realem Bestandswachstum

Die Vollregression am Bestand von 126 Artikeln fand zwei Randfälle, die der
frühere Vertrag nicht mehr deckte:

- Beim alten Sockel **4** rissen bei einem simulierten siebentägigen Ausfall ab
  Tag 10 zwei YMYL-Fristen jeweils um einen Tag.
- Beim +97-Tage-Vollrückstand wurde das gesamte harte Limit **16** benötigt;
  die versprochene Kapazitätsreserve war damit nicht vorhanden.

**Dauerhafte Reparatur:** Die SSOT `data/agent_reach/faktenfrische.yaml` setzt
den Sockel auf **5** und das harte Limit auf **18**. Das ist die kleinste
getestete Untergrenze, die Ausfälle ab Tag 3, 10 und 20 ohne Fristverletzung
trägt; die beiden zusätzlichen Plätze geben dem Vollrückstandsszenario Reserve.
Die Automatik läuft im Normalbetrieb mit ihrem empfohlenen Budget, nicht
ständig am harten Limit. Rechercheintervalle, fachliche Schwellen und
Freigaben wurden nicht abgesenkt oder verändert.

**Regressionsschutz:**
`test_faktenfrische_kapazitaet.py` misst die reale Workflow-Kadenz, den
+97-Tage-Vollrückstand und die Ausfallpfade. Die Gegenprobe mit Sockel 4 bleibt
absichtlich rot. Die tägliche Faktenfrische-Wache misst dieselbe SSOT live;
bei künftiger Unterdeckung bleibt der vorhandene deduplizierte Schließpfad
sichtbar, statt ein falsches grünes Siegel zu erzeugen. Ein langer Volltest
legte außerdem eine Minuten-Grenze in der Ledger-Regression offen: Zwei
identische Inhaltsbefunde bekommen absichtlich einen aktualisierten
`zuletzt_gesehen`-Zeitstempel. Der Test vergleicht nun fachliche Identität und
Inhalt getrennt vom erwartbar fortgeschriebenen Zeitfeld; der Testlauf ist
nicht mehr von einer zufälligen Minutengrenze abhängig. Details stehen im
Nachtrag von `docs/ANLEITUNG-FAKTENFRISCHE.md`.

### 2. Accessibility: sichtbarer Text passte nicht zum Namen der Vorlese-Schaltfläche

Der Browser-Audit fand auf Artikeln und allen sechs Pillar-Seiten den ernsten
Axe-Befund `label-content-name-mismatch` (WCAG 2.5.3). Betroffen war der
Vorlese-Knopf: Sein zugänglicher Name beschrieb die Funktion, enthielt aber
nicht durchgängig alle sichtbaren Knopfwörter – auch das sichtbare Siegel
„KI-Stimme“ fehlte. Der erste E2E-Lauf machte die Rückfallklasse mit 18 roten
Prüfungen auf Desktop und Mobile sichtbar.

**Dauerhafte Reparatur:** Der sichtbare Text führt nun den zugänglichen Namen
an: „Vorlesen“ bzw. in Englisch „Listen“, zusammen mit dem sichtbaren
„KI-Stimme“-/„AI voice“-Siegel. Die dynamischen Zustände Pausieren,
Weiterlesen und Beenden erhalten ebenfalls passende Namen; die Herkunft der
synthetischen Stimme bleibt dabei explizit. Anfangs-Markup und Laufzeit-Engine
sind auf denselben Vertrag gebracht.

**Regressionsschutz:** `scripts/ff_voice_toolbar_check.py` prüft die Namen und
Herkunftsangaben beider Sprachen strukturell. Die vorhandene Axe-/Playwright-
Suite prüft gebaute Artikel und Pillars in Desktop- und Mobile-Projekten; der
vollständige Lauf war 180/180 grün. Nach der letzten Textpräzisierung liefen
die betroffenen Artikelprüfungen nochmals für Desktop und Mobile grün. Das
Provenienz-Gate prüft weiterhin die Offenlegung maschineller Stimmen.

### 3. Warnungsfreie Dateiverarbeitung in den Scorecards

Der vollständige Testlauf machte `ResourceWarning` für ungeöffnete Dateien in
`editorial_scorecard.py` sichtbar; eine spätere strikte Messung fand denselben
Musterfehler beim Lesen der Grammatik-Whitelist.

**Dauerhafte Reparatur:** Leseroutinen verwenden jetzt `Path.read_text()` bzw.
einen geschlossenen `with open(...)`-Kontext. Die Scorecard-Sammlung und die
Whitelist-Regression wurden mit `ResourceWarning` als Fehler ausgeführt – beide
grün. Das schließt Ressourcenlecks, die bei lang laufenden Prozessen oder
wiederholten Prüfungen auflaufen könnten.

### 4. Kontrollflächen-Audit gab überholte Handlungsempfehlungen aus und übersah Job-Verträge

Der Workflow-Audit empfahl Actions zu pinnen und Timeouts/Berechtigungen zu
ergänzen, obwohl der Bestand bereits **0** entsprechende Befunde hatte.
Außerdem prüfte er Concurrency nur auf Workflow-Ebene und meldete dadurch
`auto-assign-pr.yml` fälschlich als ungeschützt: Der Workflow besitzt bereits
einen Job-Vertrag je PR.

**Dauerhafte Reparatur:** `automation_premium_audit.py` koppelt Empfehlungen an
die Messwerte und erkennt nun wohlgeformte Workflow- sowie Job-Level-Verträge
(nichtleere Gruppe plus explizites `cancel-in-progress`). Das gilt auch im
dependency-freien Parser-Fallback. Der `--strict`-Modus blockiert fehlende
oder ungültige Verträge; Regressionstests prüfen Job-Level-Erkennung,
Vertragsvalidierung und den vollständigen Bestand.

### 5. Acht tatsächliche Concurrency-Lücken – Ereignisse erhalten statt pauschal abbrechen

Nach Korrektur der Metrik blieben acht Workflows ohne Vertrag. Die jeweils
gewählte Gruppe und Abbruchpolitik folgt dem Ereignis:

- `alert-on-failure.yml`: pro abgeschlossenem beobachtetem Run, nicht abbrechen;
  keine Meldung wird durch einen neueren Workflow-Run ersetzt.
- `codeql.yml`: Pull Requests werden über die PR-Nummer gruppiert und veraltete
  Prüfungen dürfen abgebrochen werden; andere Ereignisse bleiben als eigene
  Runs erhalten.
- `dependabot-automerge.yml`: pro PR gruppiert, veraltete Synchronisationsläufe
  abbrechbar.
- `issue-cleanup.yml`, `issue-triage.yml` und `uptime-monitor.yml`: pro Run
  getrennt, kein Abbruch eines aktiven Vorgangs bzw. Alarms.
- `publication-reliability-tests.yml` und `visual-data-gate.yml`: PR-Läufe je
  PR gruppiert und bei neuer Revision abbrechbar; manuelle Läufe sind separat.

**Nachmessung:** 102 Workflows, darunter der bereits vorhandene
Job-Level-Vertrag in `auto-assign-pr.yml`; 0 fehlende/ungültige Verträge.
`--strict` ist grün.

### 6. `continue-on-error`: echte YAML-Schritte und überprüfbare Fallback-Signale

Der Textsuchwert **120** enthielt fünf Kommentare. PyYAML zählt **115 echte
Schritte**. Die Kontrollfläche hält sie einzeln im JSON-Bericht fest und
klassifiziert das erkennbare Signal: 44 verwenden ein Outcome/Conclusion oder
Step-Output im nachgelagerten Vertrags-/Gatepfad, 33 schreiben im selben Schritt
eine Annotation, Summary, Report- oder Artefaktspur, und 38 haben einen
nachgelagerten Report-/Issue-/Gate-Marker. Kein echter Schritt ist im aktuellen Bestand ohne solches strukturelles
Signal. Das ist ein überprüfbarer Hinweis auf den Meldeweg, aber kein Ersatz für
die fachliche Entscheidung, ob ein Befund blockieren soll.

Die gezielte semantische Nachprüfung der nicht unmittelbar an Outcome-Ausdrücke
gebundenen Fälle bestätigte die vorgesehenen Verträge: Bestands-/Qualitäts-
Befunde bleiben sichtbar und werden über Report, Issue oder Abschluss-Gate
behandelt; optionale Netz-/Audio-/Cache-Arbeiten dürfen den Hauptlauf nicht
stoppen, müssen aber eine Diagnose hinterlassen. Zwei bislang nur im Runner-Log
erkennbare Schreibpfade wurden verbessert: das Sichern des Search-Console-
Kontingentgedächtnisses und des Watchdog-Routing-Zustands schreiben nun Erfolg
oder konkreten Fehler in die Job-Summary und annotieren Fehlschläge.

Ein Regressionstest verlangt eine erkennbare Signal-Klasse für jeden
`continue-on-error`-Schritt und meldet neue stumme Fälle. Die Prüfung ist
absichtlich strukturell: Die fachliche Validität eines beliebigen zukünftigen
Reporttexts wird nicht allein aus Schlüsselwörtern behauptet.

## Dauerhafte Selbstheilungs- und Qualitätskette

- `blog-health-daily.yml` führt täglich idempotente, deterministische
  Inhalts-/Metadaten-Reparaturen aus und lässt fachlich mehrdeutige Änderungen
  ausdrücklich bei Menschen.
- `faktenfrische.yml` misst tägliche Kapazität und Fristen anhand der
  gemeinsamen Regeln und des echten Cron-Plans.
- `publication-reliability-tests.yml` prüft PR-Änderungen an Content, Scripts,
  Layouts, Assets, Themes, Daten, Workflows und Abhängigkeiten; hier laufen die
  umfassende Offline-Regressionssuite und die Browser-E2E-Suite.
- `deploy.yml` baut den echten Produktionsstand und hält die bestehenden
  fail-closed-, Verifikations- und Veröffentlichungs-Gates.
- Die Reparaturen sind in der SSOT, im Produktions-Markup und in den
  Regressionsverträgen verankert. Ein späterer Rückfall wird dadurch
  reproduzierbar rot; er kann nicht still als „erledigt“ gelten.

Es wurde bewusst **kein** automatisches Umschreiben von Finanzbehauptungen,
Rechtspositionen oder fachlichen Empfehlungen ergänzt. Maschinen reparieren
nur eindeutige Struktur-/Label-/Kapazitätsverträge; Fachfreigabe bleibt
menschlich.

## Verbleibende Grenzen

Die technischen Restpunkte des Quell-/Workflow-Audits sind geschlossen und
nachgemessen. Was lokal nicht wahrheitsgemäß als „grün“ zertifiziert werden
kann, bleibt ausdrücklich als externe Prüfgrenze bzw. Content-Priorität stehen:

1. **Live-Betrieb und externe Provider:** Dieses Audit verifiziert Quellcode,
   lokalen Produktionsbuild, Repository-Daten und die vorhandenen
   Test-/Workflow-Verträge. Es bestätigt nicht den aktuellen Live-Zustand der
   Search Console, GitHub-Environments/Secrets, Cloudflare, Newsletter- oder
   Social-Zugangsdaten und ersetzt keinen externen Internet-Crawl. Dafür sind
   authentifizierte Provider-Messungen und ein Live-Crawl nötig; fehlende
   Credentials wurden nicht simuliert oder als Erfolg ausgegeben.
2. **Nicht blockierende SEO-Hinweise:** Das SEO-Cockpit meldete 10 P3-Hinweise
   bei 0 P1/0 P2. Sie sind kein technischer Release-Blocker; eine redaktionelle
   SEO-Priorisierung bleibt fachliche Folgearbeit.

## Reproduktion der zentralen Prüfungen

```bash
npm ci
npm ci --prefix tools/ff-voice-qa
npm run build
python3 -m unittest discover -s scripts/tests -v
npm run test:e2e
npm run seo:check
npm run frontmatter:check
npm run tags:check
npm run weiterleitungen:check
python3 scripts/automation_premium_audit.py --strict
python3 scripts/faktenfrische_kapazitaet.py --wache --json
```

**Abnahme:** Die acht Concurrency-Lücken sind geschlossen; der Audit erkennt
Workflow- und Job-Verträge. Die 115 tatsächlichen `continue-on-error`-Schritte
haben jeweils einen klassifizierten Fallback-Hinweis (ohne unbelegte Aussage,
dass jeder Hinweis fachlich blockierend sein müsse). Pagefind indexiert die
Google-Verifikationsdatei nicht mehr, während sie im ausgelieferten
Produktionsbaum bytegleich verbleibt. Externe Live-Zustände und die 10 P3-SEO-
Hinweise sind bewusst als Grenzen/Folgepriorität benannt, nicht als lokal
„grün“ behauptet.
