# 🛠️ Entwickler-Werkzeuge (interne Dokumentation)

**Warum diese Datei existiert:** Das README ist eine **Markenfläche** – es wird
von Suchmaschinen indexiert und steht bei einer Markensuche neben dem Ratgeber.
Betriebssprache (Automatik, Workflows, Gates, SEO-Werkzeuge, Dateipfade) gehört
deshalb nicht dorthin, sondern hierher. Die Wache
`scripts/brand_surface_guard.py` setzt diese Trennung durch (ROT bei Verstoß im
README); Dokumente unter `docs/` sind bewusst ausgenommen.

Beim Ergänzen gilt: **Neue technische Abschnitte immer hier**, im README nur der
Verweis.

---

## Premium-Kontrollturm für die Produktionsautomatik

Die Automatik wird nicht nur funktional, sondern auch als Produktionsplattform
überwacht. Der schreibgeschützte Workflow-Audit prüft alle GitHub-Actions auf
explizite Berechtigungen, Concurrency-Verträge, Laufzeit-Timeouts, doppelte
Workflow-Namen, ungepinnte Drittanbieter-Actions und sichtbar gemachte
`continue-on-error`-Stellen:

```bash
npm run automation:audit       # lesbarer Agentur-Befund
npm run automation:audit:json  # maschinenlesbar für CI/Reporting
python3 scripts/automation_premium_audit.py --strict
```

`--strict` ist bewusst ein kleiner Basisschutz und ändert keine Workflows. Der
Audit-Bericht liefert die priorisierte Härtungsliste, bevor neue Automatik
hinzukommt: zuerst Timeout und Least-Privilege-Rechte, dann unveränderliche
Action-Versionen und zuletzt jede tolerierte Teilstörung mit Issue- oder
Summary-Fallback. So bleibt die Automatik beobachtbar, statt nur größer zu
werden.

---

## Kostenloses SEO-Cockpit (lokal)

Eigenständiges, lokales Werkzeug mit technischem Audit, Seiten-/Linkinventar,
Maßnahmenexport, Snippet-Werkstatt und privatem Search-Console-CSV-Import.
Keine Anmeldung, keine APIs, keine laufenden Dienstgebühren.

```bash
npm run seo:audit  # Hugo-Build + Audit → .cache/seo-cockpit/index.html
npm run seo:serve  # im eigenen Browser: http://127.0.0.1:4174
npm run seo:check  # gleicher Audit, Exit 1 bei technischen P1-Befunden
npm run test:seo   # Python- und CSV-Regressionstests
```

Voraussetzungen: Hugo Extended 0.164.0, Python ≥ 3.11, Node.js/npm.
Das Cockpit kann nach dem Audit auch direkt als lokale HTML-Datei geöffnet
werden. Es wird **nicht** mit dem Blog veröffentlicht.

[Bedienung, Datenschutz und Grenzen](ANLEITUNG-SEO-COCKPIT.md) ·
[Audit und Maßnahmenplan vom 20.09.2026](SEO-OPTIMIERUNG-2026-09-20.md)

---

## 0 € Redaktionsarchitektur (Whisper lokal · n8n · Pages)

Stand 03.10.2026 – der Betriebsunterbau der Redaktion, bewusst ohne laufende
Dienstgebühren. **Dieser Abschnitt stand bis zum 04.10.2026 im README und hat
die Markenfläche verletzt** (Vorgang WF-A4E0, Meldung #552); er gehört hierher.

- **Whisper lokal:** vollständig on-premise Spracherkennung (`faster-whisper`,
  CTranslate2) für Diktate, Sprachnotizen und die Audio-Abnahme – ohne externe
  Schnittstellenkosten.
- **n8n self-hosted:** Ablauf-Orchestrierung über Docker Compose und die
  Webhook-Brücke `scripts/n8n_bridge.py`.
- **GitHub Pages:** Auslieferung des gebauten Standes plus die Qualitätsgates
  der CI.

```bash
npm run blogautomatik:status     # Live-Status aller drei Säulen
npm run blogautomatik:audit      # 0 € Kosten- und Einsparungs-Audit
npm run blogautomatik:selftest   # Offline-Selbsttest (fail-closed)
npm run test:blogautomatik       # 39 Unit-Tests (Whisper, Brücke, Orchestrator)
npm run whisper:inbox            # wartende Sprachaufnahmen verarbeiten
npm run n8n:ping                 # Latenz- und Erreichbarkeitsprobe für n8n
```

Sicherheits-Vertrag der Whisper-Engine (Meldung #559, Code-Scanning-Alert 60,
04.10.2026): Externe Audio-Pfade werden kanonisiert und geprüft, das
whisper.cpp-Backend erhält sie nur noch als Datei-Deskriptor
(`/proc/self/fd/<n>`), Modell-/Sprachwerte nur aus Whitelists — erzwungen durch
`scripts/tests/test_command_execution_security.py` und die Selbsttests.
Details: [ANLEITUNG-WHISPER-N8N-GITHUB-PAGES.md](ANLEITUNG-WHISPER-N8N-GITHUB-PAGES.md),
Abschnitt 7 · Report:
[WHISPER-BEFEHLSZEILEN-WACHE-PREMIUM-2026-10-04.md](../WHISPER-BEFEHLSZEILEN-WACHE-PREMIUM-2026-10-04.md)

Bedienung, Smartphone-Anbindung und Kostenvergleich:
[ANLEITUNG-WHISPER-N8N-GITHUB-PAGES.md](ANLEITUNG-WHISPER-N8N-GITHUB-PAGES.md) ·
Einbau-Protokoll: [WHISPER-N8N-INTEGRATION-PREMIUM-2026-10-03.md](../WHISPER-N8N-INTEGRATION-PREMIUM-2026-10-03.md)

---

## Marken-Oberfläche prüfen (vor jedem README-Commit)

```bash
npm run marke:check                                         # Selbsttest + README-Gate
python3 scripts/brand_surface_guard.py --selftest           # Detektor-Beweis
python3 scripts/brand_surface_guard.py --only readme --gate --offline
python3 scripts/brand_surface_guard.py --only readme --gate --offline \
        --datei /pfad/zu/einer/README.md                    # beliebige Fassung prüfen
```

**Commit-Sperre statt Nachlauf (seit 04.10.2026):** Der Haken
`.githooks/pre-commit` prüft den **gestageten** README-Stand, bevor der Commit
entsteht – und damit, bevor die Meldung aus der CI kommt.

**Sie stellt sich selbst scharf (seit 04.10.2026, zweite Stufe).** Git führt
mitgelieferte Haken nie von allein aus; „einmal pro Arbeitskopie einschalten"
war eine Bitte, keine Leitplanke. `scripts/haken_wache.py` übernimmt das an
jedem Eingang, den eine Arbeitskopie realistisch nimmt – `npm install`
(über `prepare`), jeder Marken-Lauf (`npm run marke:check`) und der
ausdrückliche Befehl:

```bash
npm run hooks:install   # scharfstellen (idempotent, mit Nachprüfung)
npm run hooks:status    # Zustandsbericht dieser Arbeitskopie
npm run hooks:check     # Exit 1, wenn die Sperre nicht scharf ist
npm run test:haken      # 11 Fallgruppen im Wegwerf-Repo + Unit-Tests
python3 scripts/haken_wache.py --status --json   # maschinenlesbar
```

Eingehängt wird als **Weiterleitung** in der Hakenablage, die git wirklich
benutzt (`git rev-parse --git-path hooks`) – nicht mehr über
`core.hooksPath=.githooks`. Grund: Diese Einstellung legt *alle* anderen Haken
still, lautlos (Signatur-, Trailer- oder Lint-Haken anderer Werkzeuge). Eine
Leitplanke, die anderen Leitplanken die Bremse zieht, ist keine.

- Ein bereits vorhandener `pre-commit` wird **bewahrt**: er wandert nach
  `pre-commit.lokal` und läuft weiterhin, und zwar vor der Markenflächen-Sperre.
- Arbeitskopien, die noch auf `core.hooksPath=.githooks` stehen, bleiben gültig;
  sobald diese Einstellung echte Haken stilllegt, zieht `npm run hooks:install`
  sie auf die Weiterleitung um und sagt im Protokoll, warum.
- Ein fremdes Hakenwerkzeug (z. B. `.husky`) wird **nie** überschrieben – der
  Wächter meldet den Fall mit zwei konkreten Wegen.
- Ohne Git-Arbeitsbaum (Export, Tarball) ist der Lauf grün und still;
  `npm install` scheitert daran nicht.

Ein Notausgang bleibt (`git commit --no-verify`), dann greift das Gate im
Push-Lauf.

Ausnahmen gehören mit Begründung in `data/brand_surface_allowlist.txt`.
Hintergrund und Admin-Fahrplan: [MARKEN-OBERFLAECHE-RUNBOOK.md](MARKEN-OBERFLAECHE-RUNBOOK.md) ·
Vorfall und Beweise: [MARKENFLAECHE-README-PREMIUM-2026-10-04.md](../MARKENFLAECHE-README-PREMIUM-2026-10-04.md)

---

## Automatische Fehlermeldungen: Vorgangscodes

Fehlermeldungen tragen markenneutrale Titel („🔧 Wartung · Inhaltsqualität ·
Vorgang WF-8F6F"). Welcher Workflow dahintersteht, zeigt:

```bash
python3 scripts/alert_issue_identity.py --tabelle
python3 scripts/alert_issue_identity.py --workflow "Faktenfrische (Bestand)"
python3 scripts/alert_issue_identity.py --selftest
```

Die Identität einer Meldung ist der unsichtbare Marker im Body
(`<!-- alert-key: WF-XXXX -->`), **nicht** der Titel – wer den Titel von Hand
ändert, zerstört also nichts. Hintergrund: Runbook, Abschnitt 7.

---

## Abschlussvermerk an die Meldung (Vorgangs-Abschluss)

Eine Meldung, die sich über „Closes #…" beim Zusammenführen schließt, schließt
sich **stumm**: Wer sie Wochen später liest, sieht nur „geschlossen". Der
Vermerk wurde bis zum 04.10.2026 von Hand nachgetragen – und genau daran
scheiterte es bei Meldung #552: das persönliche Zugangsrecht darf keine
Kommentare schreiben (HTTP 403). Ein Abschluss, der am Recht einer einzelnen
Person hängt, ist kein Verfahren.

Seitdem schreibt das Repository den Vermerk selbst
(`.github/workflows/vorgangs-abschluss.yml`, Recht `issues: write`):

```bash
npm run vorgang:abschluss -- --pr 558            # Plan (schreibt nichts)
npm run vorgang:abschluss -- --pr 558 --apply    # Vermerk setzen
npm run vorgang:nachtrag -- --tage 14            # fehlende Vermerke finden
npm run test:vorgang                             # 12 Fallgruppen + Unit-Tests
```

Eigenschaften, auf die es ankommt:

- **Zwei Wege.** Sofort beim Zusammenführen *und* täglich 04:40 UTC als
  Nachlauf. Ereignisse fallen aus, Läufe brechen ab – der Nachlauf trägt nach,
  was fehlt.
- **Wiederholbar.** Ein unsichtbarer Marker (`<!-- vorgangs-abschluss: PR-N -->`)
  verhindert Doppelungen; zweimal laufen lassen schadet nie.
- **Nachprüfung.** Geschrieben gilt nur, was danach zurückgelesen wurde.
- **Markenfläche.** Issue-Kommentare sind öffentlich. Der Text läuft vor dem
  Absenden durch `scripts/brand_surface_guard.py`; trägt der Titel des
  Vorschlags Betriebssprache, geht die neutrale Kurzform raus – oder gar nichts.
- **Kein fremder Code.** `pull_request_target` checkt den Zielzweig aus und
  liest vom Vorschlag nur Nummer, Titel und Beschreibung.

## Genau eine H1 pro Seite (Barrierefreiheit)

Zwei H1 auf einer Seite sind unsichtbarer Schaden: Der Leser merkt kaum etwas,
Screenreader, Inhaltsverzeichnis und KI-Antworten aber verlieren die Gliederung
(WCAG 1.3.1 / 2.4.6). Deshalb gehört die H1 dem **Layout**, nie dem
Markdown-Fließtext.

```bash
npm run h1:check      # Sabotageproben + Quelle + Hugo-Build + gebaute Seiten
npm run a11y:check    # dieselbe Wache, danach das vollständige A11y-Audit
npm run test:h1       # H1-Wache + Voll-Audit (33 Regressionstests)
npm run test:a11y     # fokussierte Vollscan-/Fail-closed-Regressionen
python3 scripts/h1_wache.py --source-only    # nur Quelle (kein Build nötig)
python3 scripts/h1_wache.py --public public  # nur die gebauten Seiten
python3 scripts/h1_wache.py --json           # maschinenlesbar
```

**Für die Redaktion:** Wer statt des Titels eine eigene Schirmzeile über dem
Artikel will, setzt sie als `heading:` ins Frontmatter – die H1 übernimmt
diesen Text, Titel, Breadcrumb und SEO-Zeile bleiben unangetastet:

```markdown
---
title: "Daten & Studien"
heading: "Daten, die man prüfen und zitieren kann"
---
```

Eine `# …`-Zeile im Fließtext ist dagegen tabu: Sie erzeugt die zweite H1, die
Meldung #623 auslöste. Genau deshalb **heilt die Wache nicht selbst** – eine H1
automatisch zu löschen hieße, einen redaktionellen Satz zu vernichten. Der
Befund nennt Datei, Zeile und den Handgriff.

### Was seit Stufe 2 (08.10.2026) zusätzlich geprüft wird

Drei Ränder waren auch nach der Dauerheilung offen; einer davon war ein
**echter, live Befund**:

1. **Markdown-Wahrheit statt `#`-Suche.** Die Quellprüfung kennt jetzt alle
   Formen, die Goldmark als `<h1>` rendert: ATX mit bis zu drei führenden
   Leerzeichen (`   # Titel`), Setext (`Titel` + `=====`) und rohes
   `<h1 …>` (hugo.toml setzt `unsafe = true`). Code-Zäune, eingerückter Code
   und Inline-Code-Spans bleiben Text – dort ist die Raute keine Überschrift.
2. **Die Ausnahme, die einen Befund verdeckte.** `page/N/` galt pauschal als
   „Blätter-Redirect ohne Inhalt“. Seit `[pagination] disableAliases = true`
   (29.09.2026) gibt es diese Redirects aber nicht mehr: `/page/2/` … sind
   echte, verlinkte Seiten – und trugen **gar keine H1**. Die Ausnahme ist
   entfernt; Blätterseiten werden geprüft, die Startseiten-Blätter bekommen
   ihre H1 aus `layouts/_default/list.html` (Marker `H1-BLÄTTERKOPF`, an
   `scripts/h1_wache.py` gebunden).
3. **Vollständiges H1-Inventar.** `layouts/` enthält neun Dateien, die eine H1
   rendern dürfen. Jede steht mit Anzahl und Grund in `H1_QUELLEN`, jede
   Seitenart in `SEITENARTEN`; beide Sichten müssen zusammenpassen. Eine neue
   H1-Quelle ohne Eintrag ist ein Befund – **fail-closed**. Die
   Einzelansichten mit eigener Vorlage (`layouts/pillar/single.html`,
   `layouts/werkzeuge/single.html`) müssen `heading:` genauso ehren wie der
   gemeinsame Baustein.

Der **Pull Request** misst die gebaute Wahrheit jetzt ebenfalls: `e2e.yml`
führt direkt nach dem Hugo-Build `python3 scripts/h1_wache.py --public public`
aus (und die Browser-Suite prüft `/page/2/` und `/posts/page/2/`).

**Hintergrund:** Meldung #623 (07.10.2026), Berichte
`A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-07.md` (Stufe 1) und
`A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-08.md` (Stufe 2), Vertrag C30 in
`scripts/governance_contract.py`.

---

## Linktexte und Alt-Texte (SEO-Sicht auf den Build)

Ein Link ohne Ankertext ist für Crawler kein Link, sondern eine Fläche; ein
Bild ohne `alt` ist für die Bildersuche unsichtbar. Beides war am 27.10.2026
im Seobility-Check der Startseite ein Befund („8 Links haben keinen
Linktext", „1 Bild ohne Alt-Attribut") – und beides entsteht nicht im
Template, sondern erst beim Rendern. Deshalb prüft die Wache den **fertigen
Build**, dateiweise, und nicht die Quelle:

```bash
npm run links:check        # Sabotageproben + Hugo-Build + alle 262 Seiten
npm run links:check:json   # maschinenlesbar
npm run test:links         # beide Wachen + 30 Regressionstests
python3 scripts/linktext_wache.py --public public
```

| Regel | Prüft | Bewertung |
|---|---|---|
| **L1** | `<a href>` ohne sichtbaren Text (auch `<area>`) | **Fehler** |
| **L2** | `<img>` ohne `alt`-Attribut | **Fehler** |
| **L3** | `alt=""` (dekorativ) und Ankertexte über 60 Zeichen | Hinweis, kein Fehler |
| **L4** | Ankertext eines **Kartenlinks** über 80 Zeichen | **Fehler** |

Drei Grenzen sind bewusst gezogen:

- **`aria-label` zählt nicht als Linktext.** Es ist die richtige Antwort auf
  die Frage „Wie heißt dieser Link?" und die falsche auf „Worauf verlinkt
  diese Seite?" – Crawler lesen den Textknoten. Der frühere Overlay-Link
  `.entry-link` war a11y-konform und SEO-leer; heute trägt der Kartentitel
  den Anker, die Trefferfläche zieht `::after`.
- **Ausnahmen werden benannt, nicht stillschweigend geduldet.** Ein Link mit
  `data-ff-linktext-frei` wird übersprungen; wer die Ausnahme setzt, schreibt
  im Template dazu, welche Wache die Fläche stattdessen abdeckt.
- **L4 gilt nur für Kartenlinks.** Der erste Versuch (80 Zeichen auf *allen*
  Links) bestrafte redaktionelle Prosa, FAQ-Antworten und Quellenzeilen – er
  wurde verworfen, nicht aufgeweicht. L4 greift, wenn die Klasse des Links
  oder eines Vorfahren auf Kartenmuster passt (`card`, `karte`, `tile`,
  `entry-title`) und die Seite indexierbar ist. Die sechs Kartenfamilien
  (Themenwelten, Saison, Pillar, Related, Werkzeug-Raster, Werkzeug-Weiter)
  tragen deshalb genau *einen* Titel-Link; Titel sind kurz, die Beschreibung
  steht daneben, nicht im Anker. WCAG 2.5.3 bleibt erfüllt, weil der Namen
  des Links dem sichtbaren Kartentitel entspricht und die Trefferfläche per
  `::after { inset: 0 }` über die ganze Karte liegt.
- **`alt=""` ist kein Fehler.** Dekorative Bilder (Logos in Wortmarken-Links,
  Icons) *sollen* leer bleiben (WCAG 1.1.1). Gezählt wird es trotzdem, damit
  niemand versehentlich ein Inhaltsbild versteckt.

**Noch nicht in CI.** Die Wache läuft über `npm run links:check`; sie in
`.github/workflows/**` zu hängen, ist eine Änderung an der Lieferkette und
braucht die ausdrückliche Freigabe des Inhabers (CLAUDE.md, Sicherheitsregel 3).
Vorlage für den Einstieg: ein Schritt nach `python3 scripts/a11y_audit.py`
in `seo-weekly.yml` mit
`python3 scripts/linktext_wache.py --public public`.

## Einbett-Blöcke (der einzige Text, den Fremde kopieren sollen)

Der Seobility-Punkt „Externe Faktoren 0 %" lässt sich nicht im eigenen HTML
lösen – er hängt an fremden Seiten. Der einzige Hebel, der ohne Gegenleistung
funktioniert, ist ein Angebot, das keine Arbeit macht: Bild plus Quellenzeile
als fertiger Copy-Paste-Block. `layouts/_partials/ff_einbetten.html` liefert
ihn (Shortcode `einbetten`, verwendet in der Q4-Studie und auf `/presse/`).

```bash
npm run links:check                          # enthält die Einbett-Wache
python3 scripts/einbetten_wache.py --selftest
python3 scripts/einbetten_wache.py --public public
```

| Regel | Prüft | Bewertung |
|---|---|---|
| **E1** | Block hat einen Namen: `aria-labelledby` → existierende Überschrift (steht **außerhalb** der `<section>`, s. Chunker-Vertrag) | **Fehler** |
| **E2** | genau ein `<figure>`/`<img>`, `src` absolut, `width`/`height`, `alt` | **Fehler** |
| **E3** | Bild und Quellenzeile absolut, **gleiches** Ziel, kein `nofollow`/`sponsored` | **Fehler** |
| **E4** | kein Kampagnen-Parameter (`utm_*`, `gclid`, `fbclid`, `ref`, …) | **Fehler** |
| **E5** | kein `<script>`, `<iframe>`, `<form>`, `<object>`, `<embed>` | **Fehler** |
| **E6** | Kopier-Knopf zeigt auf die `<pre>`-ID, Live-Bereich `role="status"` vorhanden | **Fehler** |

Die Überschrift des Blocks steht bewusst **vor** der `<section>`: Der
Chunker-Vertrag in `scripts/layout_audit.py` verlangt, dass jede H2 mit `id`
im Artikelinhalt ein direkter Block des Inhalts ist – sonst reißt die
Text-Teilung den Container auf. Der Name der Section zeigt trotzdem auf
genau diese Überschrift. Derselbe Lauf hat auch den Link-Scanner des Audits
gehärtet: `<pre>`-Blöcke sind Text, kein Markup (sonst meldet das
Code-Beispiel „kaputte interne Links“).

Ein fehlerhaftes Angebot ist schlimmer als keins: Ein relativer `src` zeigt
beim Einbau auf die *fremde* Domain, ein `nofollow` bittet um genau den Link,
den die Seite nicht bekommt. Deshalb ist die Wache fail-closed – auch ein
verschwundener Block (`0 Blöcke`) ist rot.

**Noch nicht in CI**, gleiche Begründung wie oben (Sicherheitsregel 3).

## ReDoS-Wache: mehrzeilige Muster nicht dem Backtracking überlassen

Code-Scanning-Alert Nr. 87 (`py/redos`, 26.10.2026) entstand in der
GSC-Abdeckung: Ein Regex sollte aus Frontmatter nur `sitemap.disable: true`
lesen, kombinierte aber `\s+`, `.*` und einen weiteren `\s+` über mehrere
Zeilen. Die Eingabe `sitemap:\n` mit vielen `\t\n`-Paaren erzeugte exponentiell
viele Zerlegungen. Die Heilung ist ein zeilenweiser Parser
(`sitemap_deaktiviert()`), kein vorsichtiger umgeschriebener Ausdruck.

```bash
npm run redos:wache          # 12 Eigenproben + 539 Python-Dateien
npm run redos:wache:json     # maschinenlesbarer Bericht
npm run test:redos           # Wache + 98 Vertragstests
python3 scripts/redos_guard.py --root /pfad/zu/einem/anderen/baum
```

Die Wache `scripts/redos_guard.py` liest den Python-AST, erkennt Muster auch in
Aliasen, Konstanten und f-Strings und meldet zwei Klassen: **R0-SYNTAX**
(unlesbare Datei = fail-closed) und **R1-NEWLINE-PUMP** (die historische
Struktur). Sie ersetzt CodeQL nicht: Alle vier ReDoS-Regeln für Python und
JavaScript bleiben zusätzlich namentlich im Security-Gate von
`.github/workflows/codeql.yml` hart verdrahtet. Der CI-Job `redos-wache`
läuft unabhängig vom SARIF-Upload.

**Hausregel für neue Parser:** Bei eingerückten Blöcken zuerst `splitlines()`
und eine Schleife mit klarer Blockgrenze. Wenn doch ein Regex nötig ist, muss
zwischen zwei unbegrenzten Quantoren ein eindeutiges Pflichtzeichen stehen.
Kein `# codeql[...]`, keine Whitelist, kein Dismiss. Details:
[`CODE-SCANNING-ALERT-87-REDAUERHEILUNG-HIGHEND-2026-10-26.md`](../CODE-SCANNING-ALERT-87-REDAUERHEILUNG-HIGHEND-2026-10-26.md)
und `SECURITY.md`.

---

## Sitecheck-Wache: vier Prüfbereiche gegen den gebauten Blog

`scripts/sitecheck_wache.py` prüft, was der [Pergamon Website Check](https://www.pergamon-interactive.de/sitecheck-2016.html)
in den Bereichen **Meta, Struktur, Technik und Konfiguration** verlangt – nicht
nur auf der Startseite, sondern auf allen indexierbaren Seiten des Builds.
Es liest ausschließlich `public/` (oder `--site <ordner>`), braucht kein Netz
und keine Fremdpakete.

```bash
npm run test:sitecheck       # 27 Sabotageproben + 23 Unit-Tests, offline
npm run sitecheck:check      # Selbsttest + Hugo-Build + Vollprüfung
python3 scripts/sitecheck_wache.py --site public --json
```

Zwei Besonderheiten: `<title>` in eingebetteten SVG-Diagrammen zählt **nicht**
als Seitentitel, und ein `<a id="anker">` ohne `href` ist ein Sprungziel, kein
toter Link. Die Wache ergänzt `h1_wache.py`, `a11y_audit.py`,
`metadaten_wache.py` und `schema_seo_gate.py` – sie ersetzt keine davon.

Welche Empfehlungen von 2016 bewusst **nicht** übernommen wurden (meta
keywords, meta expires, mod_pagespeed, JS zwangsweise zusammenfassen) und
warum, steht im Report
[`SITECHECK-2016-OPTIMIERUNG-2026-10-27.md`](../SITECHECK-2016-OPTIMIERUNG-2026-10-27.md).
