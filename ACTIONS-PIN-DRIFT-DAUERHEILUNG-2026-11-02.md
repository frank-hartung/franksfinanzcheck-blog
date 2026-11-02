# Actions-Pin-Drift: Dauerheilung zu PR #1014

**Datum:** 02.11.2026  
**Auslöser:** Dependabot-PR #1014 (`github-actions`-Gruppe)  
**Betroffene Updates:** `actions/setup-python` 7.0.0 → 7.1.0, `github/codeql-action/{init,analyze,upload-sarif}` 4.39.0 → 4.39.1, `peter-evans/create-issue-from-file` 4.0.1 → 6.0.0

## Befund

PR #1014 war nicht wegen der Action-Updates rot. Die Regressionssuite scheiterte
an zwei bereits auf `main` vorhandenen Bestandsdrifts:

1. `data/lcp_images.json` enthielt drei am 02.11.2026 wieder veröffentlichte
   Versicherungsartikel nicht.
2. Der Versicherungs-Pillar verlinkte dieselben drei Artikel nicht mehr. Die
   Links waren am 27.10.2026 entfernt worden, während die Artikel noch Entwürfe
   waren; nach der Wiederveröffentlichung griff der Cluster-Vertrag wieder.

Zusätzlich hatte die alte `actions_version_guard.py` eine strukturelle Lücke:
Regel A3 ließ vollständige SHA-Pins unangetastet. Damit konnte die Wache weder
Teil-Bumps noch widersprüchliche Versionskommentare erkennen. Die gruppierte
Dependabot-Konfiguration konnte außerdem ein Major-Update mit Patch/Minor-Updates
in einen PR legen, der dann komplett manuell geprüft werden musste.

## Dauerhafte Lösung

* `scripts/actions_version_guard.py` prüft jetzt **einen SHA und eine exakte
  Version je Anbieter-Repository** über alle Workflows und Composite-Actions.
  CodeQL-Unteraktionen werden zusammengeführt. Tags/Branches sind keine Pins.
  Mehrere gültige SHA/Version-Paare sind ein Befund ohne automatischen Kandidaten;
  `--fix` repariert nur Kommentare zu einem bereits eindeutigen SHA.
* Dependabot trennt `github-actions` (Patch/Minor) und `github-actions-major`
  (Major). Der Auto-Merge akzeptiert ausdrücklich nur Patch/Minor; unbekannte
  Semver-Stufen gehen in die manuelle Prüfung.
* Der Deploy erzeugt das LCP-Manifest nach den finalen Inhalts-Gates und vor dem
  Rebuild/Upload aus dem tatsächlichen Live-Bestand. Fehlende AVIF-Varianten
  stoppen den Deploy. Der Schreiber ist idempotent, damit unveränderte Policy
  keine Timestamp-Commits erzeugt.
* Der Versicherungs-Pillar verlinkt die drei wieder live geschalteten Artikel
  erneut relativ; `lastmod` wurde auf das tatsächliche Änderungsdatum gesetzt.

## Nachweise

* Upstream-Tags wurden gegen die PR-Pins aufgelöst (annotierte Tags bis zum Commit
  dereferenziert): `setup-python` v7.1.0 = `6d4fd22b…`, CodeQL v4.39.1 =
  `9b325408…`, `create-issue-from-file` v6.0.0 = `fca9117c…`.
* `create-issue-from-file` v6 nutzt Node 24 (Runner ≥ 2.327.1); die betroffenen
  Jobs laufen auf `ubuntu-24.04`. `labels`/`assignees` bleiben Zeichenketten.
* Fokussierte Regressionen, Actions-Pin-Gate, Workflow-Vertrag online,
  Blustradius, Trigger-Wache, Governance, Integrität, Hugo-Build, SEO-/Link-Gates,
  vollständige Python-Suite und Uhr-Probe (+97 Tage) wurden lokal geprüft.

## Betriebsregel

Action-Updates werden nicht mehr „kommentarlos“ nachgezogen. Ein PR muss SHA und
Versionskommentar gemeinsam aktualisieren; die Pin-Wache erzwingt die Konsistenz,
die Workflow-Vertrag-Wache prüft Anbieter-Existenz und Eingabe-Verträge. Major-
Updates bleiben eine eigene, manuell zu beurteilende Gruppe.
