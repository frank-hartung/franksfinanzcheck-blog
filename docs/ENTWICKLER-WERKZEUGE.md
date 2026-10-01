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

## Marken-Oberfläche prüfen (vor jedem README-Commit)

```bash
python3 scripts/brand_surface_guard.py --selftest           # Detektor-Beweis
python3 scripts/brand_surface_guard.py --only readme --gate --offline
```

Ausnahmen gehören mit Begründung in `data/brand_surface_allowlist.txt`.
Hintergrund und Admin-Fahrplan: [MARKEN-OBERFLAECHE-RUNBOOK.md](MARKEN-OBERFLAECHE-RUNBOOK.md).

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
