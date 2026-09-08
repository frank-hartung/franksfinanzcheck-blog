# Veröffentlichungs-Zuverlässigkeit – Issue #217

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
   Maximal zwei Generierungen pro Lauf; Ziel sechs **gate-geprüfte** Kandidaten,
   Bestand auf zwölf begrenzt. Ein Hash schützt vor veralteten Zertifikaten.
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
python3 scripts/cadence_guard.py --selftest
```

Abgedeckt: Entwürfe zählen nicht, Wochenendkadenz, Mindestziel, Gate-Ablehnung
mit nächstem Kandidaten, Wiederholung ohne Doppelveröffentlichung, manueller
Entwurfsschutz, Werkzeugfehler mit Rollback, Off-Day-Schutz, HTTP-Soft-404,
Netzfehler und Folgetagsalarm trotz eines vorhandenen Artikels.

Vollständige Provider-/Hugo-/Pages-Integration wird in der Produktionsabnahme
geprüft; lokale Unit-Tests allein beweisen keine erfolgreiche Auslieferung.
