# Bot-Watchdog #810 · Dauerheilung der Weiterleitungs-Blockade

- **Stand:** 19.10.2026 · **Issue:** [#810](https://github.com/frank-hartung/franksfinanzcheck-blog/issues/810)
- **Workflow:** `.github/workflows/deploy.yml` · Schritt „Weiterleitungen – Selbsttest, Quelle und Unit-Tests (fail-closed)“
- **Betroffene Läufe:** u. a. `39273233716` (14:54 UTC); derselbe Schritt war auch im späteren Lauf `39291922041` (17:10 UTC) rot.

## Kurzbefund

Der Deploy-Stop war **kein Fehler der Weiterleitungs-Engine und kein fehlendes Werkzeug**. Der Snapshot-Test fand eine echte, zuvor öffentliche URL, die durch einen Qualitäts-Hold aus dem Build gefallen war, aber noch keine dokumentierte Route hatte:

`/posts/2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026/`

Der Artikel liegt weiterhin im Repository, ist aber seit `2026-10-19T13:09:54Z` `draft: true`; das Frontmatter nennt `Redaktions-Standard: RS1, RS2, RS3`. `data/url_snapshot.json` belegt den früheren öffentlichen Stand. Weil keine Weiterleitung und kein bewusster 404-Eintrag existierte, brach `Snapshot.test_snapshot_ist_aktuell` zu Recht fail-closed ab.

## Dauerhafte Korrektur

- Die historische URL ist in `data/weiterleitungen.yaml` als **Regel C** erfasst und führt auf die live Versicherungs-Pillar-Seite `/pillar/versicherungen/`. Das ist der passende fachliche Fallback: Ein gleichwertiger Live-Beitrag ist aktuell nicht vorhanden.
- `scripts/weiterleitungen.py --build` hat die markierte statische Weiterleitungsseite unter `static/posts/…/index.html` erzeugt. Die Quelle bleibt die YAML-Datei; die generierte Seite wird nicht von Hand gepflegt.
- `data/url_snapshot.json` wurde **absichtlich nicht neu geschrieben**. Der historische Nachweis bleibt erhalten und kann eine spätere, nicht dokumentierte URL-Änderung weiter erkennen.
- Der Regressionstest fixiert jetzt den korrekten Pillar-Fallback; Bestandszahl, Anleitung und Implementierungsbeschreibung sind auf 115 Weiterleitungen / 118 ehemals veröffentlichte Post-URLs aktualisiert. Die Anleitung beschreibt außerdem wieder korrekt, dass die Deploy-CI bereits `--check`, `--verify` und den Unit-Test ausführt.

## Qualitäts- und Sicherheitsgrenzen

Der Artikel wurde **nicht** manuell veröffentlicht, nicht inhaltlich verändert und nicht aus seinem Qualitäts-Hold gehoben. Das wäre bei einem als hochriskant geprüften Versicherungsthema keine technische Reparatur. Ebenso wurden weder Qualitäts-Schwellen gelockert noch Snapshot-Daten überschrieben.

Die GitHub-Pages-Weiterleitung ist – wie im Projekt dokumentiert – eine Meta-Refresh-Seite mit Canonical und `noindex,follow`, kein echter HTTP-301. Ein 301 bleibt von einem aktiven Cloudflare-Proxy und dessen Betreiberfreigabe abhängig.

Sollte der Artikel später wieder live gehen, meldet die Quellenprüfung die dann überflüssige Weiterleitung absichtlich als Konflikt. Sie muss in diesem Fall entfernt und die generierte Seite neu gebaut werden, damit statische Ausgabe niemals eine wieder veröffentlichte Seite überdeckt.

## Verifikation

Vor der Korrektur reproduzierte `Snapshot.test_snapshot_ist_aktuell` den Blocker mit genau dieser fehlenden URL. Nach der Korrektur liefen die Prüfungen erfolgreich:

- `scripts/weiterleitungen.py --selftest`: **18/18** Fälle bestanden.
- `scripts/weiterleitungen.py --check`: **115** Weiterleitungen, **7** dokumentierte 404 und **97** Live-URLs; grün.
- `scripts/weiterleitungen.py --verify`: alle **115** erzeugten Seiten stimmen mit der Quelle überein.
- `npm run test:weiterleitungen`: **16** Unit-Tests bestanden, inklusive Snapshot- und Zielregression.
- `npm run weiterleitungen:check`: URL-Wache grün, Snapshot unverändert. Der Lauf meldet außerdem eine neue Live-URL als unverbindlichen Hinweis.
- `git diff --check`: grün.

Ein Hugo-Produktionsbuild war lokal nicht ausführbar, da das Hugo-Binary in der Sandbox nicht installiert ist. Der behobene Schritt liegt vor dem Build; Quellvertrag, Snapshot-Entscheidung und statisches Artefakt sind lokal vollständig geprüft.
