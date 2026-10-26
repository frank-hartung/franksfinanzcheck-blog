# Konsolidierung der vier offenen Pull Requests – 26.10.2026

| Ausgangs-PR | Befund und Entscheidung |
|---|---|
| #855 Reserve | Alter Branch gegenüber `main` überholt: aktuelle Implementierungen u. a. von `affiliate_marketer`, `r5_absatz_splitter`, `reserve_finisher` und `reserve_healer_coverage` sind bereits vorhanden. Blindes Mergen würde neuere RS5-/Zahlen-Heilungen und Datenzustände überschreiben. Fehlende Integritätssignatur/Regressionen im alten PR. Nicht übernehmen; schließen, sobald die Konsolidierung gesichert ist. |
| #880 Actions | Nur drei CodeQL-Action-Refs auf v4.39.0 und einen Download-Artifact-Ref auf v8.0.2 übernehmen. **Nicht** den alten Workflow-Kopf oder die Entfernung der ReDoS-Sicherheitsregel und des unabhängigen ReDoS-Jobs übernehmen: CodeQL `py/redos` ist ein echter Sicherheitsfund. |
| #882 Hugo | Ein isolierter Pin für das lokale Wheel wäre inkonsistent mit 25 CI-Workflows, der GitHub-Release-Prüfsumme und dem PyPI-Fallback. Alle produktiven Hugo-Pfade auf 0.168.0 synchronisiert; Linux-x86_64-Wheel-Hash gegen PyPI und Release-Archiv-Digest gegen die GitHub-Release-API geprüft; echten Extended-Build ausgeführt. Die Action akzeptiert keine andere bereits installierte Extended-Version mehr. Die neue Hugo-Version hat einen alten falschen Go-Datumsformatstring sichtbar gemacht (`YYYYMMdd` → `20060102`); korrigiert und per Build verifiziert. Der Regressionstest zur alten Sitemap-Störung besitzt auch unter Hugo 0.168 wieder eine wirksame Sabotageprobe. |
| #883 n8n | Offizieller Tag `n8n@2.44.3` (Bugfix, 16.10.2026) verifiziert und Compose-Tag aktualisiert; kein automatischer Produktions-Rollout. Host-Backup, Migrations- und Rollback-Pfad: `tools/n8n/UPGRADE.md`. |

## Basisdefekte, die Dependabot-PRs blockiert haben

Fünf Artikel hatten unquotierte Doppelpunkte im YAML-Frontmatter; die Offline-Wächter konnten sie nicht parsen. Die Beschreibungen wurden ohne Inhaltsänderung als YAML-Strings gequotet. Eine zwischenzeitlich wieder eingeführte Analytics-Anbindung stand im Widerspruch zur bestehenden Datenschutz-Freigabe und Governance-Sperre; Konfiguration, Partial, Loader, irreführende Rechtstext-Zeilen und veraltete Aktivierungsanleitung wurden entfernt. Sechs veraltete Bildunterschriften wurden mit dem vorhandenen artikelgenauen Generator regeneriert, das Fachprüfungs-Register aus dem Bestand aktualisiert und das Integritäts-Siegel für geänderte Kerndateien neu signiert.

Zwei als READY markierte Reserve-Entwürfe hatten andere Bytes als ihre alten SHA-256-Zertifikate. Die lokale vollständige Nachzertifizierung wurde **verweigert**, weil `hunspell/de_DE` hier nicht vorhanden ist (die Rechtschreibnote wäre sonst nur eine Schätzung). `reserve_artifacts.py --withdraw-invalid` zieht ausschließlich nicht mehr gültige READY-Behauptungen zurück, ohne Hash, Messzeit oder Messkontext zu fälschen. Ergebnis: derzeit **2/5 READY, Ziel 6**. `reserve_recert.py --check` meldet weiterhin drei geänderte Kandidaten; auf dem Produktions-Runner mit Hugo **und** Hunspell ist `reserve_recert.py --fix` auszuführen, danach Reserve-Heiler/Volllauf und `reserve_gate.py`. Bis dahin ist die Kapazität **nicht** bestätigt. Die Regression beweist Idempotenz, Beleg-Herkunft und fail-closed bei defektem Snapshot.

## Lokal geprüft

- `hugo v0.168.0+extended --minify --destination /tmp/ff-pr-hugo-build --cleanDestinationDir`: Erfolg (109 Seiten).
- `python scripts/artefakt_waechter.py`, `scripts/fremdmessung_sperre.py`, `scripts/reserve_artifacts.py --check`, `scripts/governance_contract.py --quick`, `scripts/integrity_guard.py --gate`, `scripts/actions_version_guard.py --gate`: grün (mit PyYAML-Umgebung).
- `python -m unittest discover -s scripts/tests`: 3915 Tests, 3 Fehler vor Commit/Staging; zwei waren die notwendige Commit- bzw. Staging-Probe für das Siegel/einen gelöschten Partial-Pfad, der dritte die nun angepasste Hugo-Sabotageprobe. Nach Commit und Staging erneut prüfen.

**Grenze:** Docker-Image und Datenbankmigration am Host nicht in dieser Sandbox ausführbar. Der Reserve-Bestand ist nicht stillschweigend auf 6/6 hochgerechnet. GitHub-CI nach Push und der Host-Migrationsnachweis sind eigenständige Abnahmen.

## CI-Nachprüfung des ersten Konsolidierungs-Commits

Der erste PR-Lauf brachte zwei zusätzliche Basisbefunde ans Licht: Qualitäts-/Layout-Gate scheiterten am **nicht existierenden PDF-Link** der veröffentlichten Studie. Der Link und eine irreführende Behauptung über ein angeblich vorhandenes PDF wurden entfernt; Methodik und Rechnung sind über den echten Abschnitt `#methodik` erreichbar. Danach: 3984 interne Links, 0 defekte; statisches Layout-Audit ohne kritische Funde. Die Browser-Frühwarnung bei 1385 DOM-Elementen bleibt sichtbar, aber ist laut bestehendem Severity-Vertrag unter dem harten Lighthouse-Limit 1400 und nicht der rote Befund.

Zusätzlich fand die 97-Tage-Uhrprobe einen bisher undichten Test in `test_gsc_abdeckung.py`: Der angebliche Zwei-CSV-Fälle-Test las das produktive Entscheidungsregister und die echte Wanduhr; unter fremdem Datum wurden vier Fälle gezählt. Die Testnaht übergibt jetzt einen festen Tag und leeres Register/Verlauf – **84 GSC-Tests unter fremder Uhr grün**. Keine Produktions-Triage-Regel gelockert.
