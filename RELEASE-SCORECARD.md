# Release-Scorecard – die Produktionswahrheit

**Stand:** 2026-11-05 · **Modus:** live · **Engine:** `scripts/release_scorecard.py` · **SSOT:** `data/release_scorecard.yaml`

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
| ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ❌ blockiert | ✅ bestanden | ➖ nicht erforderlich | ✅ bestanden |

## Live-Bestand (Artikel für Artikel)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-10-dsl-wechselbonus-sichern` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **blockiert** |
| `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **blockiert** |
| `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **blockiert** |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-11-19 | **blockiert** |
| `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **blockiert** |
| `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **blockiert** |
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **blockiert** |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **blockiert** |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **blockiert** |
| `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **blockiert** |
| `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **blockiert** |
| `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **blockiert** |
| `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **blockiert** |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **blockiert** |
| `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **blockiert** |
| `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **blockiert** |
| `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **blockiert** |
| `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-13 | **blockiert** |
| `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-18 | **blockiert** |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-19 | **blockiert** |
| `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **blockiert** |
| `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **blockiert** |
| `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **blockiert** |
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **blockiert** |
| `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-23 | **blockiert** |
| `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **blockiert** |
| `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-07 | **blockiert** |
| `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-05 | **blockiert** |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **blockiert** |
| `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **blockiert** |
| `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **blockiert** |
| `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **blockiert** |
| `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **blockiert** |
| `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **blockiert** |
| `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-14 | **blockiert** |
| `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **blockiert** |
| `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-25 | **blockiert** |

## Was blockiert – nach Prüfung, nicht nach Dimension

_Die Dimension sagt, wo es weh tut; der Check sagt, was zu tun ist. Besitz und Entscheidung stehen in `data/release_scorecard.yaml`._

| Check | Dimension | Wirkung | Entscheidet | Artikel |
|---|---|---|---|---|
| **T7-render-beweis** | technik | blockiert | Maschine (deterministisch) | 76 |
| **T1w-zeichenlaenge-optimum** | technik | warnung | Maschine (deterministisch) | 4 |
| **RD1-duplikate** | redundanz | blockiert | Maschine (deterministisch) | 2 |
| **RD2-einzigartigkeit** | redundanz | blockiert | Mensch (Herausgeber/Redaktion) | 2 |
| **T6-textverstaendnis** | technik | blockiert | Maschine (deterministisch) | 1 |

- **RD2-einzigartigkeit** – Schließweg: scripts/check_uniqueness.py U1–U2 (via publish_gate.uniqueness_failures) · betroffen: `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich`, `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum`

## Faktenfrische-Deckung (der Takt gegen den Bestand)

_Ein Faktenalter wird nicht „plötzlich“ rot: Es wird überfällig, weil der Bestand mehr Prüfungen braucht, als der Takt liefert. Diese Rechnung ist die Ursache der F1-Funde – nicht der F4-Funde._

| Kennzahl | Wert |
|---|---|
| Seiten im Bestand (Posts + Ratgeber) | 114 |
| Fällig heute / überfällig | 0 / 0 |
| Bedarf | 2,79 Prüfungen/Tag (19,5/Woche) |
| Angebot | 4,00/Tag (Budget 4 × 1,00 Läufe/Tag) |
| **Deckung** | **143 %** |
| Rückstand abgebaut | **nicht abbaubar** im Horizont |
| Nächste Frist | `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` am 2026-11-11 (in 6 Tagen) |
| Empfohlenes Budget | 4 je Lauf (Limit 16) |

✅ Deckung ausreichend: Der Takt kann den Bestand halten. Ein roter Faktenstand ist damit ein echter Inhaltsbefund (F4), kein Kadenz-Artefakt.

## Blockierende Funde (76 Artikel)

### `2026-08-10-dsl-wechselbonus-sichern` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` (blockiert, Risikoklasse hoch)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` (blockiert, Risikoklasse erhoeht)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` (blockiert, Risikoklasse hoch)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` (blockiert, Risikoklasse hoch)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` (blockiert, Risikoklasse hoch)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` (blockiert, Risikoklasse erhoeht)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` (blockiert, Risikoklasse erhoeht)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D3-X: Absatz wortgleich in 2 Artikeln (content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md ≈ content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-; D4-X: Fast-Duplikat über Artikel (Ratio 1.00, content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md ≈ content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit
- **RD2-einzigartigkeit** [redundanz]: U1-PHRASEN: 6 gleiche 7-Wort-Phrasen mit 2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum (z. B. „energieprodukte kosteten laut statistischem bundesamt verbraucherpreisindex im“) – ab 5 ist es Dopplung, Passage umschreiben
- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.7919 ≈ Z.6060): [Quelle: Statistisches Bundesamt, Verbraucherpreisindex und Inflationsrate in Deutschland, https://w…; D3-X: Absatz wortgleich in 2 Artikeln (content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md ≈ content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit-durch-; D4-X: Fast-Duplikat über Artikel (Ratio 1.00, content/posts/2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich/index.md ≈ content/posts/2026-09-07-frugalismus-tipps-mehr-freiheit
- **RD2-einzigartigkeit** [redundanz]: U1-PHRASEN: 6 gleiche 7-Wort-Phrasen mit 2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich (z. B. „energieprodukte kosteten laut statistischem bundesamt verbraucherpreisindex im“) – ab 5 ist es Dopplung, Passage umschreiben
- **T6-textverstaendnis** [technik]: R15-PHRASEN-DOPPEL: identische 10-Wort-Sequenz im Fließtext: „…quelle statistisches bundesamt verbraucherpreisindex und inflationsrate in deutschland https www…“ – doppelte Passage, manuell reparieren
- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` (blockiert, Risikoklasse erhoeht)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` (blockiert, Risikoklasse erhoeht)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` (blockiert, Risikoklasse erhoeht)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` (blockiert, Risikoklasse erhoeht)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

### `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` (blockiert, Risikoklasse standard)

- **T7-render-beweis** [technik]: Artikel fehlt im Build (public/posts/<slug>/index.html) – Beweisbasis aller Render-Checks nicht vorhanden
- ❔ **A1-link-integritaet** [affiliate]: nicht beweisbar – Affiliate-Integrität NICHT beweisbar (Werkzeugfehler – fail-closed, kein Kandidat geht ungeprüft live): Render-Beweis nicht möglich: public/ fehlt (--no-build)
- ❔ **A3-offenlegung** [affiliate]: nicht beweisbar – Offenlegung NICHT beweisbar: offenlegung_gate.py lieferte kein Ergebnis (fail-closed – kein Kandidat geht ungeprüft live)

## Warnungen ohne Blockade (0 Artikel)

Keine.

## Entwürfe – was vor dem Livegang noch offen ist

| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |
|---|---|---|---|---|
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 6 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | hoch | vorhanden | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | hoch | vorhanden | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | hoch | vorhanden | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | hoch | vorhanden | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | standard | nicht erforderlich | frisch geprüft vor 39 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 34 Tagen (Intervall 45 Tage) | 2026-11-16 |
| `2026-10-05-die-50-30-20-regel-einfach-erklaert` | standard | nicht erforderlich | frisch geprüft vor 31 Tagen (Intervall 90 Tage) | 2027-01-03 |
| `2026-10-06-markt-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 28 Tagen (Intervall 90 Tage) | 2027-01-06 |
| `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` | standard | nicht erforderlich | frisch geprüft vor 28 Tagen (Intervall 45 Tage) | 2026-11-22 |
| `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 23 Tagen (Intervall 30 Tage) | 2026-11-12 |
| `2026-10-09-7-gewohnheiten-fuer-finanzielle-freiheit` | standard | nicht erforderlich | frisch geprüft vor 23 Tagen (Intervall 90 Tage) | 2027-01-11 |
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 30 Tagen (Intervall 45 Tage) | 2026-11-20 |
| `2026-10-12-stromfresser-im-haushalt-entlarven` | standard | nicht erforderlich | frisch geprüft vor 23 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` | standard | nicht erforderlich | frisch geprüft vor 21 Tagen (Intervall 30 Tage) | 2026-11-14 |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 16 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet` | standard | nicht erforderlich | frisch geprüft vor 16 Tagen (Intervall 90 Tage) | 2027-01-18 |
| `2026-10-19-urlaubskasse-clever-aufbessern` | standard | nicht erforderlich | frisch geprüft vor 16 Tagen (Intervall 30 Tage) | 2026-11-19 |
| `2026-10-21-mietwagen-fallen-im-urlaub-vermeiden` | standard | nicht erforderlich | frisch geprüft vor 14 Tagen (Intervall 30 Tage) | 2026-11-21 |
| `2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen` | standard | nicht erforderlich | frisch geprüft vor 7 Tagen (Intervall 45 Tage) | 2026-12-13 |
| `2026-10-26-gastarife-vergleichen-vor-dem-herbst` | standard | nicht erforderlich | frisch geprüft vor 7 Tagen (Intervall 30 Tage) | 2026-11-28 |
| `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-12-12 |
| `2026-10-30-gaspreiserhoehung-sonderkuendigungsrecht-raus-aus-dem` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` | erhoeht | nicht erforderlich | frisch geprüft vor 5 Tagen (Intervall 45 Tage) | 2026-12-15 |
| `2026-11-01-energieeffiziente-geraete-so-sinken-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | 2026-12-16 |
| `2026-11-02-last-minute-urlaubsangebote-sichern` | standard | nicht erforderlich | frisch geprüft vor 2 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 30 Tage) | 2026-12-05 |
| `2026-11-05-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 30 Tage) | 2026-11-29 |
| `2026-11-05-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` | standard | nicht erforderlich | frisch geprüft vor 2 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 45 Tage) | 2026-12-20 |

## Ausnahmen (Falsch-Alarm-Protokoll)

Keine aktiven Ausnahmen – alle Checks wirken unverändert.

---
_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer Beweis ist niemals „bestanden“._
