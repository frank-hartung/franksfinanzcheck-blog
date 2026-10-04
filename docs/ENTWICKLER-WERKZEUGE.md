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
npm run test:blogautomatik       # 45 Unit-Tests (Whisper, Brücke, Orchestrator)
npm run whisper:inbox            # wartende Sprachaufnahmen verarbeiten
npm run n8n:ping                 # Latenz- und Erreichbarkeitsprobe für n8n
```

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
entsteht – und damit, bevor die Meldung aus der CI kommt. Einmal einschalten:

```bash
npm run hooks:install     # setzt core.hooksPath auf .githooks
git config core.hooksPath # Kontrolle: .githooks
```

`npm install` erledigt das über `prepare` mit; ein Notausgang bleibt
(`git commit --no-verify`), dann greift das Gate im Push-Lauf.

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
