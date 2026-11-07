# Release-Scorecard #1098 – Dauerheilung mit transaktionaler Selbstheilung

**Stand:** 2026-11-07 · **Branch:** `arena/d587c477-franksfinanzcheck-blog`

## Befund

Die tägliche Release-Scorecard war seit 01.11.2026 rot. Der Eröffnungstext von
#1098 war bereits überholt: RD1/RD2/T6-Altlasten sind auf `main` geheilt. Eine
frische Vollmessung über **78 Live-Artikel** ergab:

| Urteil | Artikel |
|---|---:|
| freigabe-reif | 68 |
| Warnung | 4 |
| blockiert | 6 |
| Werkzeugfehler | 0 |

Alle sechs Blocker sind **F4-Fachbefunde** (19 offene Befunde). Sie verlangen
eine dokumentierte menschliche Entscheidung. Ein neues Prüfdatum, ein
Recherche-Lauf oder eine Maschine dürfen sie nicht schließen.

## Was jetzt dauerhaft anders ist

1. **Messung und Heilung bleiben getrennt.** `release_scorecard.py` bleibt
   Beweislauf (`DRY_RUN=True`, C15). Der neue Schreiber
   `release_bestand_heiler.py` läuft im Workflow *vor* der Messung.
2. **Nur sichere deterministische Teilmenge.** T5 Lesbarkeit (Stufe A),
   T6 Textverständnis (Politur + R5) und artikelinterne RD1-Duplikate
   (formbewahrende Teilmenge). RD2, F4, Siegel, Freigaben und YMYL bleiben
   menschlich. Ein Artikel mit zusätzlichem Human-Blocker wird ganz verschont.
3. **Transaktion statt Hoffnung.** Budget max. 8 Artikel, sauberer Bestand,
   SHA-256-CAS pro Datei, deterministische Wiederholung vor jedem Schreiben,
   atomarer Dateiersatz, Journal vor dem ersten Content-Byte. Fremde Änderungen
   werden nie überschrieben.
4. **Beweispflicht nach dem Schreiben.** Gemeinsame Hugo-Build-Action, dann
   vollständige Live-Scorecard. Bestätigung nur wenn Basis-Commit, Live-Menge,
   Nicht-Ziel-Hashes und Ziel-Hashes stimmen, mindestens ein Ziel-Check
   verschwindet und kein neuer Blocker/Werkzeugfehler entsteht. Sonst exakter
   Byte-Rollback aus dem Basis-Commit, erneuter Build und Nachmessung.
5. **Kein Stale-State-Ticket.** Werkzeugfehler stehen jetzt im Siegel.
   Übersprungene/abgebrochene Messungen und Siegel mit falschem Commit oder
   zu altem Zeitstempel erzeugen „Messung nicht beweisbar“ statt alte
   Inhaltsblocker als heutige Wahrheit auszugeben. Der Ticket-Kopf wird bei
   Rot aktualisiert; ein Kommentar erscheint nur bei Ursachenwechsel.
6. **Regressionsschutz.** Modul-Selbsttest, neue Tests, Aufnahme in
   `governance_contract.GUARDS`, `npm run test:release`, Workflow-Ordnungs-
   und Commit-Gate-Tests. Die vollständige Suite lief grün: **5454 Tests,
   6 übersprungen**. Dazu Governance-/Kontrakt-Selbsttests, Syntax für 667
   Python-Dateien, Workflow-JS, Wachen-Vertrag, Premium-Audit, Artefakt-,
   History-, Manifest- und Skill-Vertrag. Keine Schwelle, kein Gate und keine
   Ausnahme wurde gelockert; keine Actions-Version geändert.

## Bedienung

```bash
npm run release:heilung:plan   # read-only, schreibt kein Betriebsbuch
npm run test:release           # Selbsttests + Regression
# Schreibend nur mit sauberem content/posts und gebautem public/:
python3 scripts/release_bestand_heiler.py --apply
hugo --minify --destination public --cleanDestinationDir
python3 scripts/release_scorecard.py --live --streng --commit-sha "$(git rev-parse HEAD)"
python3 scripts/release_bestand_heiler.py --bestaetigen
# Bei Abbruch:
python3 scripts/release_bestand_heiler.py --zurueckrollen
```

Der Workflow führt diese Kette inklusive Rollback-Nachmessung selbst aus.
Exit-Vertrag: 0 = sicher abgeschlossen (menschlicher Rest darf bleiben),
1 = Versuch verworfen und zurückgerollt, 2 = Werkzeug-/Vertragsfehler.

## Verbleibender menschlicher Schließweg für #1098

Die Automatisierung ist absichtlich nicht befugt, die sechs F4-Artikel
freizusprechen. Arbeitsdatei: `BEFUND-AKTE.md`. Pro Befund:

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> \
  --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

Betroffen sind Preisgarantie-Gas (2), Frugalismus (2), 50/30/20-Budget (1)
und Campingurlaub (1). Die genauen Befund-IDs stehen im aktuellen
`RELEASE-SCORECARD.md` und in der Befundakte. Erst wenn alle fachlich
entschieden sind und die Nachmessung grün ist, schließt der Workflow #1098.
