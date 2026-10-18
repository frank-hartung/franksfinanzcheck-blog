# Release-Scorecard – die Produktionswahrheit

**Stand:** 2026-10-18 · **Modus:** kandidaten · **Engine:** `scripts/release_scorecard.py` · **SSOT:** `data/release_scorecard.yaml`

> Eine Zeile pro Artikel, acht Dimensionen, ein Wahrheitsort. Was hier rot ist, ist rot – nichts wird weggeklammert.

**Die sechs Fragen – kurz beantwortet (ausführlich: `docs/ANLEITUNG-RELEASE-SCORECARD.md`)**

| Frage | Antwort |
|---|---|
| 1. Was blockiert Veröffentlichung? | jeder Check mit `wirkung: blockiert` in der SSOT – maschinell durchgesetzt (Governance C19) |
| 2. Was warnt nur? | Checks mit `wirkung: warnung` – sichtbar, stoppen nicht |
| 3. Wer entscheidet fachlich? | Herausgeber Frank Hartung (`eskalation` in der SSOT); die Maschine entscheidet fachlich nie |
| 4. Falsche Positivmeldungen? | keine zweite Messregel (Scorecard nutzt die Publish-Gate-Collectoren), fail-closed bei nicht führbarem Beweis, befristete Ausnahmen mit Ablaufdatum |
| 5. Fachliche Freigabe? | Risikoklasse hoch: Prüfer + Belegkette + Zahlenprotokoll + `--seal`; sonst AUTO-Bahn der Gate-Kette |
| 6. Nachweis der geprüften Version? | Release-Siegel: SHA-256 je Artikel + Dimensionen + Deploy-Commit in `data/release_scorecard_state.json` (Historie append-only) |

## Gesamtergebnis je Dimension (Live-Bestand)

| Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung |
|---|---|---|---|---|---|---|---|
| ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ➖ nicht erforderlich | ✅ bestanden |

## Live-Bestand (Artikel für Artikel)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-10-dsl-wechselbonus-sichern` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-27 | **freigabe-reif** |
| `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **freigabe-reif** |
| `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-27 | **freigabe-reif** |
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **freigabe-reif** |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **freigabe-reif** |
| `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **freigabe-reif** |
| `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **freigabe-reif** |
| `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **freigabe-reif** |
| `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-13 | **freigabe-reif** |
| `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-03 | **freigabe-reif** |
| `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-18 | **freigabe-reif** |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-03 | **freigabe-reif** |
| `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-19 | **freigabe-reif** |
| `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-06 | **freigabe-reif** |
| `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-06 | **freigabe-reif** |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-23 | **freigabe-reif** |
| `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |

## Blockierende Funde (0 Artikel)

Keine – der komplette Live-Bestand ist frei von blockierenden Funden.
## Warnungen ohne Blockade (0 Artikel)

Keine.

## Entwürfe – was vor dem Livegang noch offen ist

| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |
|---|---|---|---|---|
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | hoch | vorhanden | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | standard | nicht erforderlich | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 16 Tagen (Intervall 45 Tage) | 2026-11-16 |
| `2026-10-05-die-50-30-20-regel-einfach-erklaert` | standard | nicht erforderlich | frisch geprüft vor 13 Tagen (Intervall 90 Tage) | 2027-01-03 |
| `2026-10-06-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` | standard | nicht erforderlich | frisch geprüft vor 12 Tagen (Intervall 45 Tage) | 2026-11-20 |
| `2026-10-06-energieeffizienz-im-haushalt-5-schnelle-spartricks` | standard | nicht erforderlich | frisch geprüft vor 12 Tagen (Intervall 45 Tage) | 2026-11-20 |
| `2026-10-06-markt-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 90 Tage) | 2027-01-06 |
| `2026-10-07-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` | erhoeht | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 45 Tage) | 2026-11-21 |
| `2026-10-07-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` | standard | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 30 Tage) | 2026-11-06 |
| `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | 2026-11-22 |
| `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 5 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-09-7-gewohnheiten-fuer-finanzielle-freiheit` | standard | nicht erforderlich | frisch geprüft vor 5 Tagen (Intervall 90 Tage) | 2027-01-11 |
| `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | standard | nicht erforderlich | frisch geprüft vor 9 Tagen (Intervall 90 Tage) | 2027-01-07 |
| `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | standard | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 90 Tage) | 2027-01-05 |
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 12 Tagen (Intervall 45 Tage) | 2026-11-20 |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | standard | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 90 Tage) | 2027-01-05 |
| `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | standard | nicht erforderlich | frisch geprüft vor 12 Tagen (Intervall 45 Tage) | 2026-11-20 |
| `2026-10-12-stromfresser-im-haushalt-entlarven` | standard | nicht erforderlich | frisch geprüft vor 5 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-12-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | standard | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 45 Tage) | 2026-11-21 |
| `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | standard | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 30 Tage) | 2026-11-06 |
| `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` | standard | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 30 Tage) | 2026-11-14 |
| `2026-10-14-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` | standard | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 30 Tage) | 2026-11-14 |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |

## Ausnahmen (Falsch-Alarm-Protokoll)

Keine aktiven Ausnahmen – alle Checks wirken unverändert.

---
_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer Beweis ist niemals „bestanden“._
