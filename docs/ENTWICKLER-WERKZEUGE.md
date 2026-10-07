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
npm run test:h1       # 20 Regressionstests der Wache
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

**Hintergrund:** Meldung #623 (07.10.2026), Bericht
`A11Y-EINE-H1-DAUERHEILUNG-PREMIUM-2026-10-07.md`, Vertrag C30 in
`scripts/governance_contract.py`.
