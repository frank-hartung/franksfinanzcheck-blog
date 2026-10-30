# Prüfqueue #826 – Siegeldrift und Schutz vor erneutem Überschreiben

Historischer Zwischenstand vom 30.10.2026, Checkout `57a4361`. **Überholt:** Die anschließende Nachprüfung und der aktuelle Arbeitsstand stehen in `YMYL-PRUEFQUEUE-826-NACHPRUEFUNG-2026-10-30.md`. Die Zahlen und offenen Aufgaben unten beschreiben ausschließlich den damaligen Zwischenstand. Keine neue fachliche Freigabe.

## Befund und Wiederherstellung

Das Gate meldete 3 E17-Befunde, alle in Entwürfen. Die ursprünglichen Siegel und der restliche Inhalt der drei Artikel entsprechen `9bb3e86` (#940); einzig die gebundene Description wurde in `d396dd3` (#942) gekürzt. Wiederhergestellt wurden ausschließlich diese drei Description-Zeilen aus `9bb3e86`, ohne Prüfdaten, Quellen, Hash, Audit-Historie oder Entwurfsstatus anzutasten:

- `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026`
- `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet`
- `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich`

Die unveränderten bestehenden Hashes passen wieder. Das ist eine Wiederherstellung der freigegebenen Fassung, keine nachträgliche Freigabe der Änderungen aus #942 und kein Beleg für die aktuelle fachliche Richtigkeit.

## Dauerhafte Absicherung

- Der Snippet-Heiler der Metadaten-Wache prüft Änderungen vor der Übernahme mit dem bestehenden YMYL-Schreibvertrag. Das gilt auch für Entwürfe und ungültige/abgelaufene Siegel; blockierte Snippet-Befunde bleiben sichtbar. Unabhängige `lastmod`-Korrekturen bleiben möglich. Ist der Vertrag nicht auswertbar, wird nicht gekürzt.
- Der Schreibvertrag schützt nun auch den bereits vom Gate akzeptierten Status `approved`, selbst wenn ein Hash fehlt.
- Die neue reine Leseprüfung `scripts/ymyl_siegel_wache.py` prüft bestehende Siegel aller Post-Bundles unabhängig vom Veröffentlichungsstatus. Sie meldet auch unlesbares Frontmatter; normale offene Entwürfe und überfällige Reviews blockieren diese spezielle Driftprüfung nicht. Das bestehende fachliche Gate, seine Fristen und das Deploy-Gate bleiben unverändert. Ein ausdrücklich zurückgezogener Review ohne Hash ist keine Freigabe; vor Veröffentlichung greift weiterhin das fachliche Gate.
- `.github/workflows/ymyl-siegelwache.yml` führt die Schutztests und die Driftprüfung bei PRs nach `main`, Pushes auf `main` und manuell aus, ohne Issue-Schreibrechte. Für eine verbindliche Merge-Sperre muss der Check zusätzlich in der GitHub-Branch-Protection/Ruleset als erforderlich gesetzt sein; das wird hier nicht behauptet. Direkte Pushes werden erst nachträglich erkannt; bestehende Schreibverträge und das Veröffentlichungs-Gate bleiben deshalb notwendig.
- Der bisherige Metadaten-Dateitest schrieb im echten Checkout. Er arbeitet nun isoliert; zusätzliche Tests prüfen Dateischutz, fortbestehenden Befund und unabhängige `lastmod`-Heilung.

## Nachweise und offene Aufgaben

Lokal: Gate `--all --strict` 100 Artikel, 10 Hochrisiko, 10 freigegeben, 0 blockiert; `--published --strict` 72 Artikel, 0 blockiert; Siegelwache 100 Artikel, 0 Befunde. 79 Tests (Siegelwache, Schreibvertrag, Metadaten-Wache, Gate, Belegketten-Wache und Wartungsschreiber) sowie Gate-Selbsttest und `git diff --check` bestanden. `metadaten_wache.py --fix` lässt die drei Dateien unverändert und meldet **5** M2/M7-Befunde. Zwei der alten Descriptions enden mit Auslassungszeichen. Diese Qualitätsmängel müssen vor einer Veröffentlichung durch die Redaktion behoben und die neue Fassung fachlich geprüft und neu versiegelt werden. Die strenge Metadaten-Quellprüfung im E2E-Workflow meldet diese Befunde auch für Entwürfe und wird bis dahin voraussichtlich fehlschlagen; sie wurde nicht abgeschwächt. Das gerenderte Snippet-Gate betrifft hingegen veröffentlichte Seiten.

Die vier im Ticket unklaren Abrufe auf `gesetze-im-internet.de` waren hier wegen der Netzbeschränkung nicht online verifizierbar. Kein HTTP-Erfolg und keine Inhaltsprüfung werden behauptet. Ein realer Wachenlauf nach Übernahme und gegebenenfalls redaktionelle Prüfung der Quellen sind weiterhin nötig. Das Ticket bleibt offen, bis die fachlichen und externen Befunde geklärt sind; ein grüner Siegelcheck allein genügt nicht.
