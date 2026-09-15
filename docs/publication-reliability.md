# Veröffentlichungs-Zuverlässigkeit – Issue #217 / #287

## Befund am 15.09.2026 (Issue #287 – öffentlicher Mindestziel-Bruch)

- Mo 14.09. UTC: Source hatte zeitweise nur **1 LIVE-Artikel**. Der öffentliche
  Nachweis (`publication_check.py --online`) meldete zu Recht
  `delivered=[frugalismus-tricks]`, `ok=false` → Issue #287.
- Root-Cause: `publish_gate.py` im **Deploy** verwarf den neuen Tages-Artikel
  (`2026-09-14-finanzplan-…`, FM-Korruption `---TITEL:`) und stufte/verwarf
  weitere Kandidaten. Die Quote-Nachfüllung (Re-Queue + Reserve) lief nur in
  Engine-Endabnahme und Kadenz-Backstop – **nicht** im Deploy. Zwischen
  Gate-Verwurf (~22:23 UTC) und nächtlichem Backstop (~23:11 UTC) stand die
  öffentliche Site unter dem Mindestziel.
- Zweitrangig: `data/reserve-readiness.json` zählte bereits live geschaltete
  Slugs weiter als `ready=true` → Content-Reserve-Gate sah 6/6, obwohl der
  echte Pool kleiner war (Issue #295).

### Dauerhafte Reparatur 15.09.2026

1. `publication_release.refill_to_min()` – gemeinsame Brandschutzlinie
   (Re-Queue → Reserve bis LIVE-Minimum, ohne KI).
2. `deploy.yml` ruft nach `publish_gate` `publication_release.py --refill-only`
   auf; Heilungen laufen über den bestehenden Gate-Diff-Commit.
3. `reserve_readiness`/`reserve_gate` zählen ready **nur** aus aktuellen
   `draft+reserve`-Entwürfen (kein Blindvertrauen auf das `ready`-Feld).
4. `reserve_pool.reserve_drafts()` priorisiert hash-zertifizierte Kandidaten.
5. `publication_incident` stößt bei Source-Defizit zuerst die Kadenz-
   Endkontrolle an, nicht nur Deploy.
6. Regressionen: `scripts/tests/test_publication_reliability.py`
   (`QuoteRefillAfterGateLossTests`, `ReserveCertFreshnessTests`).

## Befund am 15.09.2026 (Issue #295 – Content-Reserve tagelang rot)

- Der nächtliche Reserve-Lauf `34949097389` (03:25 UTC) war nach 12 grünen
  Fachstufen rot: Der Sicherungs-Schritt kollidierte beim Rebase mit dem
  parallel laufenden Deploy-/Auslieferungslauf genau auf
  `data/reserve-readiness.json` (Deploy-Commit `344bc20`, 10:50:30 UTC), und der
  End-Gate meldete zu Recht Knappheit (Pool 5 Entwürfe < Ziel 6).
- Drei weitere Ursachen machten die Knappheit chronisch: Der Top-up produzierte
  höchstens einen Kandidaten pro Nacht (Verbrauch: bis 3/Tag), der
  In-Flight-Schutz blockierte den Nachschub derselben Nacht, und
  `check_length.py` übersprang Entwürfe – zwei Pool-Kandidaten wurden deshalb
  nie verlängert (Struktur-Score 0.70 bei < 1.200 Wörtern).
- Zusätzlich staggte der Lauf mit `git add -A` auch LIVE-Content und Live-Cover
  mit, die korpusweite Heiler der Veredelungs-Kette nebenbei verändert hatten.

### Dauerhafte Reparatur 15.09.2026

0. **Heiler-Deckung (Nachtrag 15.09.2026):** Jedes Gate, das über die Reife
   entscheidet, hat jetzt einen Heiler. Das Meta-Gate verlangt ein Satzende der
   Description (−0,3) – `meta_optimizer.py` prüfte bisher nur die Länge, ein
   Kandidat mit punktloser Description hing damit dauerhaft bei `meta 0.70`
   unter der Schwelle 0.85 und der Pool erreichte `RESERVE_TARGET` nie
   (Schwesterbefund zum Struktur-Gate, das `check_length.py` heilt). Der Heiler
   spiegelt das Gate (`desc_has_sentence_end`), repariert deterministisch ohne
   KI und wird am Ende der Kette erneut angewendet (letzte Instanz).
1. `git_sync.sh`: Zertifikat und Cover-Manifest sind maschinengenerierte
   Artefakte → Auto-Heilung nach „letzter Schreiber gewinnt“. Ebenso heilt ein
   Konflikt auf einem Reserve-Kandidaten (beide Seiten `draft+reserve`):
   Kandidaten sind maschinenverwaltet und ihr Hash-Zertifikat gilt exakt für
   diese Bytes. Live-Content, Re-Queue-Posts und Hand-Entwürfe bleiben ein
   harter Stopp (kein Blind-Merge).
2. `reserve_finisher.py`: **Live-Korpus-Isolation** – außerhalb der
   Pool-Kandidaten wird jede Änderung bytegenau zurückgestellt, neue
   Fremd-Dateien wandern in Quarantäne; Cover werden nur noch pro Kandidat
   gerendert.
3. `reserve_stage_guard.py` (neu): Staging-Politik – nur Pool-Content wird
   committet, Live-Content wird gemeldet statt mitgeschrieben.
4. `reserve_converge.py` (neu): begrenzte, zielgerichtete Konvergenz
   (max. 3 Runden, Batch = Fehlbestand, Dedup + Kapazitätsdeckel) ersetzt den
   wirkungslosen Einzel-Nachschub; `RESERVE_FORCE_TOPUP` hebt den
   In-Flight-Schutz nur dort und nur begrenzt auf.
5. `check_length.py`: `--include-drafts` + `--file` – Pool-Kandidaten werden
   verlängert, der Korpus bleibt unangetastet (Reserve-#4-Klasse).
6. `reserve_gate.py`: Frische-Prüfung des Zertifikats
   (`RESERVE_CERT_MAX_AGE_H`, Default 36 h) – veraltete Zertifikate sind kein
   Reife-Nachweis.
7. Regressionen: `scripts/tests/test_reserve_pipeline.py` (neu),
   `scripts/tests/test_git_sync.py` (Zertifikat-/Manifest-Konflikt),
   Selbsttests in `content-reserve.yml`.

Details, Beweise und Runbook:
`docs/archiv/CONTENT-RESERVE-295-REPARATUR-2026-09-15.md`.

## Befund am 08.09.2026

- Issue #217 dokumentiert am 07.09. mehrfach 0 veröffentlichte Artikel und
  bis zu sechs Gate-Holds (Länge, Qualitäts-Score, Titel, Textverständnis).
- Engine-Erfolg bezog sich auf Frontmatter **vor** späteren Gates.
- Der Backstop zählte vor seiner Reserve-Veröffentlichung, nicht nach den
  Deploy-Gates, und konnte trotz Defizit erfolgreich enden.
- `publish_day_check.py` akzeptierte bereits einen Entwurf als erfüllte Kadenz.
- Im untersuchten Checkout liegen **keine Reserve-Entwürfe**. Zwei Artikel
  haben dort ein freigegebenes Frontmatter für Montag; das ist kein Beleg,
  dass beide öffentlich ausgeliefert wurden. Der öffentliche Abruf aus der
  Arbeitsumgebung scheiterte mit TLS-EOF. Die Nutzerbeobachtung „nur einer“
  wird deshalb nicht durch die Repository-Zahl widerlegt.

## Neuer Betriebsvertrag

UTC bleibt die Zeitbasis der bestehenden Kadenz (Mo/Mi/Fr, mindestens 2,
standardmäßig höchstens 3). Keine Rückdatierung, keine Veröffentlichung am
Dienstag zur nachträglichen Schönung des Montags. GitHub-Cron ist best effort;
eine absolute Ausfallfreiheit kann weder GitHub noch ein KI-Provider garantieren.

1. Engine und Backstop verwenden dieselbe `content-bot`-Sperre.
2. Nach allen Engine-Optimierungen: Score >= 0,85, echter Hugo-Build,
   Publish-Gates, Reserve-Nachfüllen, erneute Gates und Abschlusszählung.
   Gate-/Werkzeugfehler werden nicht in Erfolg umgewandelt.
3. Reserve-Kandidaten werden **einzeln** vor Freigabe am Qualitäts-Score und
   denselben Publish-Gates einschließlich gerendertem Affiliate-Nachweis geprüft.
   Ablehnung stellt den ursprünglichen Entwurf wieder her und versucht den
   nächsten Kandidaten; Werkzeugfehler stellen ebenfalls wieder her und stoppen.
4. Backstop um 10:35, 16:35, 19:35 und 21:35 UTC. Commit auch bei Teildefizit,
   expliziter Deploy auch bei unverändertem Source-Stand. Fehlende Quote = rot.
5. Reserve-Produktion täglich um 03:25 UTC, unabhängig vom Publikationstag.
   Ziel sechs **gate-geprüfte** Kandidaten, Bestand auf zwölf begrenzt.
   Der Nachschub ist bedarfsgesteuert statt mengenbegrenzt: Die Konvergenz-Stufe
   produziert in bis zu drei Runden exakt den Fehlbestand
   (`RESERVE_TOPUP_BATCH`, hart gedeckelt auf vier Generierungen pro Aufruf)
   und bricht bei Zielerreichung oder ohne Fortschritt ab. Ein Hash schützt vor
   veralteten Zertifikaten, ein Alter-Gate (36 h) vor eingefrorenen Nachweisen.
   Vorprüfung schreibt `data/reserve-readiness.json`. Freigabe prüft erneut;
   das Zertifikat ist niemals ein Gate-Bypass.
6. Öffentlicher Nachweis um 20:17/22:17 UTC und am Folgetag 07:17 UTC:
   Datum aus Source, URL in öffentlicher Sitemap **und** HTTP 200 am exakten
   Artikelziel mit Artikel-HTML. Redirects zur Homepage gelten nicht als Erfolg.
   Fünf Versuche mit 60 Sekunden Pause. JSON-Beleg als Actions-Artefakt.
7. Ein dedupliziertes Delivery-Issue bleibt bis zum erfolgreichen öffentlichen
   Nachweis offen. Bei Defizit: Deploy erneut anstoßen, am Publikationstag
   zusätzlich Backstop. Keine rekursive `workflow_run`-Reparaturschleife.
8. Die neuen Workflows sind im zentralen Fehler-Alerting erfasst.

## Inbetriebnahme / Abnahme

Änderungen müssen zunächst über den PR nach `main` übernommen werden. Die
Produktions-Jobs sind absichtlich auf `main` beschränkt; ein Feature-Branch darf
keine Produktionsartikel oder Deploys erzeugen.

Danach:

1. `Content-Reserve (täglicher Vorrat)` manuell starten; Bestand/Zertifikat prüfen.
   Die erstmalige Befüllung benötigt mehrere Läufe (Kostenlimit zwei Artikel/Lauf).
2. Bei zwölf Kandidaten und weniger als sechs Freigaben: Bericht und Gate-Logs
   redaktionell prüfen. Blockierte Texte nicht blind freigeben. Provider- und
   Themenprobleme können weiterhin menschliche Hilfe erfordern; sie sind nun rot
   und alarmiert, statt als gefüllter Pool zu gelten.
3. Am nächsten Publikationstag Engine und Endkontrolle prüfen. Nach dem Deploy
   `Publication Delivery (öffentlicher Nachweis)` starten. Abnahme erst bei
   mindestens zwei nachgewiesenen URLs und ohne Gate-Rückstufung im Folge-Deploy.
4. Issue #217 erst nach diesem öffentlichen Nachweis schließen. Ein erfolgreiches
   Dispatch oder ein Commit ist ausdrücklich kein Veröffentlichungsbeweis.
5. Über zwei Wochen mindestens sechs Publikationstage samt Folgetagsnachweis
   beobachten. Bei anhaltendem Provider-/Gate-Problem: Qualität reparieren,
   nicht Mindestschwellen absenken oder Veröffentlichungsdaten manipulieren.

## Lokale Regressionen

```sh
python3 -m unittest discover -s scripts/tests -v
python3 scripts/engine_generate.py --selftest
python3 scripts/reserve_pool.py --selftest
python3 scripts/publication_release.py --selftest
python3 scripts/cadence_guard.py --selftest
```

Abgedeckt: Entwürfe zählen nicht, Wochenendkadenz, Mindestziel, Gate-Ablehnung
mit nächstem Kandidaten, Wiederholung ohne Doppelveröffentlichung, manueller
Entwurfsschutz, Werkzeugfehler mit Rollback, Off-Day-Schutz, HTTP-Soft-404,
Netzfehler, Folgetagsalarm trotz eines vorhandenen Artikels, **Quote-Nachfüllung
nach Gate-Verlust im Deploy (#287)**, Reserve-Zertifikat ohne LIVE-Geister (#295).

Vollständige Provider-/Hugo-/Pages-Integration wird in der Produktionsabnahme
geprüft; lokale Unit-Tests allein beweisen keine erfolgreiche Auslieferung.
