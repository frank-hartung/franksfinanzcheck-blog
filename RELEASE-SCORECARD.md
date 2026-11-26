# Release-Scorecard – die Produktionswahrheit

**Stand:** 2026-11-26 · **Modus:** live · **Engine:** `scripts/release_scorecard.py` · **SSOT:** `data/release_scorecard.yaml`

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
| ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ➖ nicht erforderlich | ✅ bestanden |

## Live-Bestand (Artikel für Artikel)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-10-dsl-wechselbonus-sichern` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-03 | **blockiert** |
| `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-03 | **blockiert** |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **freigabe-reif** |
| `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-04 | **freigabe-reif** |
| `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **warnung** |
| `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-04 | **blockiert** |
| `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-04 | **blockiert** |
| `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-01 | **blockiert** |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2027-01-05 | **freigabe-reif** |
| `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-04 | **blockiert** |
| `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-22 | **blockiert** |
| `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-04 | **blockiert** |
| `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **warnung** |
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **freigabe-reif** |
| `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **freigabe-reif** |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | ⚠️ warnung | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-04 | **blockiert** |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2027-01-05 | **blockiert** |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | ⚠️ warnung | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-05 | **blockiert** |
| `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-07 | **blockiert** |
| `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-05 | **blockiert** |
| `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-05 | **blockiert** |
| `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-05 | **blockiert** |
| `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **freigabe-reif** |
| `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **freigabe-reif** |
| `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | ⚠️ warnung | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-05 | **blockiert** |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **freigabe-reif** |
| `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-25 | **blockiert** |
| `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-07 | **blockiert** |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **freigabe-reif** |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-07 | **blockiert** |
| `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-07 | **blockiert** |
| `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-07 | **freigabe-reif** |
| `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-08 | **blockiert** |
| `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | ⚠️ warnung | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **blockiert** |
| `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **freigabe-reif** |
| `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-27 | **blockiert** |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-27 | **freigabe-reif** |
| `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-30 | **blockiert** |
| `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-30 | **freigabe-reif** |
| `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-31 | **blockiert** |
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-31 | **blockiert** |
| `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-02 | **blockiert** |
| `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-28 | **blockiert** |
| `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-07 | **freigabe-reif** |
| `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-03 | **blockiert** |
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-13 | **blockiert** |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-31 | **freigabe-reif** |
| `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-13 | **blockiert** |
| `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-01 | **blockiert** |
| `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-28 | **blockiert** |
| `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-31 | **blockiert** |
| `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` | ⚠️ warnung | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2027-01-01 | **blockiert** |
| `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **blockiert** |
| `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **freigabe-reif** |
| `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-12 | **freigabe-reif** |
| `2026-10-30-gaspreiserhoehung-sonderkuendigungsrecht-raus-aus-dem` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-14 | **freigabe-reif** |
| `2026-11-01-energieeffiziente-geraete-so-sinken-deine-fixkosten` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-14 | **freigabe-reif** |
| `2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-16 | **warnung** |
| `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-11-10-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **freigabe-reif** |
| `2026-11-10-kaffeemaschine-stromverbrauch-was-kostet-die-tasse-kaffee` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-24 | **freigabe-reif** |
| `2026-11-10-wlan-frust-loesen-so-findest-du-den-besten-router-standort` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-02-07 | **freigabe-reif** |
| `2026-11-12-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-02-07 | **warnung** |
| `2026-11-13-geschenkkarte-was-du-beim-kauf-und-aufladen-wissen-musst` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-28 | **freigabe-reif** |
| `2026-11-13-geschirrspueler-voll-so-sparst-du-wasser-und-strom` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-24 | **freigabe-reif** |
| `2026-11-13-mesh-wlan-nachruesten-schluss-mit-funkloechern-in-der-wohnung` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-25 | **freigabe-reif** |
| `2026-11-13-secondhand-kleidung-so-erkennst-du-qualitaet-sparst` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-02-11 | **freigabe-reif** |
| `2026-11-18-gas-anbieter-wechseln-strategien-gegen-hohe-heizkosten` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-09 | **freigabe-reif** |
| `2026-11-20-mehrwegflaschen-pfand-so-optimierst-du-deine-fixkosten` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-24 | **freigabe-reif** |

## Was blockiert – nach Prüfung, nicht nach Dimension

_Die Dimension sagt, wo es weh tut; der Check sagt, was zu tun ist. Besitz und Entscheidung stehen in `data/release_scorecard.yaml`._

| Check | Dimension | Wirkung | Entscheidet | Artikel |
|---|---|---|---|---|
| **F4-fachbefund** | faktenalter | blockiert | Mensch (Herausgeber/Redaktion) | 53 |
| **T1w-zeichenlaenge-optimum** | technik | warnung | Maschine (deterministisch) | 5 |
| **T1-zeichenlaenge** | technik | blockiert | Maschine (deterministisch) | 1 |
| **T5-lesbarkeit** | technik | blockiert | Maschine (deterministisch) | 1 |

- **F4-fachbefund** – Schließweg: scripts/faktenfrische_befund_ledger.py (via publish_gate.fakten_befund_failures) · betroffen: `2026-08-10-dsl-wechselbonus-sichern`, `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas`, `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden`, `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026`, `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke`, `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` …

## Offene Fachbefunde (F4) – was die Redaktion entscheiden muss

**295** offene Befunde auf **83** Seiten (live: 179 auf 53 Artikeln) · ältester **27 Tage** · Frist 14 Tage · über der Frist: **144**.

**Ein Prüfdatum schließt keinen Fachbefund.** F1 (Alter) und F4 (Inhalt) sind getrennte Verträge; die Maschine entscheidet nie fachlich. Die Arbeitsdatei mit jeder Befund-ID, dem Fassungsstand und dem fertigen Entscheidungsbefehl ist `BEFUND-AKTE.md` (`python3 scripts/faktenfrische_befund_akte.py --schreiben`).

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

⚠️ **256 Befunde** wurden an einem älteren Text erhoben; der Text wurde seither geändert. Entschieden wird der HEUTIGE Text – genau das macht `--entscheiden` fassungsgebunden.

🔴 **Eskalation:** 144 Befunde sind älter als 14 Tage. Fachliche Entscheidung: Herausgeber.

✅ **F1 (Faktenalter) ist nicht die Ursache:** Die Deckung trägt den Bestand; rot ist der Inhalt, nicht der Takt.

## Faktenfrische-Deckung (der Takt gegen den Bestand)

_Ein Faktenalter wird nicht „plötzlich“ rot: Es wird überfällig, weil der Bestand mehr Prüfungen braucht, als der Takt liefert. Diese Rechnung ist die Ursache der F1-Funde – nicht der F4-Funde._

| Kennzahl | Wert |
|---|---|
| Seiten im Bestand (Posts + Ratgeber) | 151 |
| Fällig heute / überfällig | 10 / 0 |
| Bedarf | 3,61 Prüfungen/Tag (25,3/Woche) |
| Angebot | 10,00/Tag (Budget 10 × 1,00 Läufe/Tag) |
| **Deckung** | **277 %** |
| Rückstand abgebaut | in 0 Tagen (Frist 7 Tage) |
| Nächste Frist | `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` am 2026-11-27 (in 1 Tagen) |
| Empfohlenes Budget | 10 je Lauf (Limit 21) |
| Spitzentag (#1039) | ✅ mitgemessen (58 Bündeltage, kein Befund) |

✅ Deckung ausreichend: Der Takt kann den Bestand halten. Ein roter Faktenstand ist damit ein echter Inhaltsbefund (F4), kein Kadenz-Artefakt.

## Blockierende Funde (54 Artikel)

### `2026-08-10-dsl-wechselbonus-sichern` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 1b7c9b9cac0290f71242 (luecke): Aktuelle Wechselangebote ermöglichen oft Einsparungen von ca. 10 € bis 25 € pro Monat im Vergleich zu veralteten Bestandskundentarifen.; ee260c27a6bfdd60fa04 (luecke): Ein Tarif mit ca. 200 € bis 300 € Bonus wirkt auf den ersten Blick unschlagbar; das ist ein Modellwert.

### `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 124ff2c3cd3917c274aa (praezision): Die Bewerbung des Vergleichsportals mit dem Superlativ 'Die besten Tarife' erfolgt ohne messbare Daten oder Auswahlkriterien in der Recherchegrundlage.; 7bdec96c0329769bebe6 (luecke): Die im Artikel als Fakten genannten Gaspreise für Oktober 2026 (11 bis 13 Cent/kWh) sind nicht durch die Fundstelle belegt, die lediglich eine allgemeine Themenübersicht darstellt.; a56734aa032e0ed9e0c4 (luecke): Der für den Verbraucherschutz zentrale Regulierungsrahmen (Sonderkündigungsrecht, Informationspflichten der Versorger) wird in der Fundstelle nicht inhaltlich bestätigt.

### `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 1d4095501e717fb30d7b (luecke): Der Hinweis auf einen „Wochenend‑Effekt“ bei Devisenkursen wird ohne Quellenangabe gemacht.; 77520584b5afd8ebd7f7 (luecke): Es wird angegeben, dass der Kurs am Automaten häufig über dem Referenzkurs der Bank liegt, jedoch fehlt ein Beleg dafür.; a3be3d50280d4fe0a1d8 (luecke): Der Artikel behauptet, dass der Betreiber des Automaten ein eigenes Entgelt verlangt, ohne dafür eine Quelle anzugeben.; d6cc7bae16dead3e610b (praezision): Die Empfehlung, nur Automaten von Banken und nicht von Aufstellern in Touristenzonen zu nutzen, ist unspezifisch und nicht durch Daten belegt.

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 30caa57be394afb62947 (luecke): Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg.; 32a3ea879f2cf126b3a7 (luecke): Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist.; c583efe1ce02df3ca2d7 (luecke): Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt.

### `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 29eea3c457afaba3d7bd (luecke): Ein Wechsel zum modernen Provider bringt oft über 350 € in 24 Monaten; das ist eine Modellannahme.; 8a0df5531569ec042ec4 (praezision): Ein freier Standplatz steigert den Empfang um bis zu 40 %.; bda1b543db068b3e00ff (luecke): Im Check: Du zahlst jeden Monat rund 45 € für einen schnellen Anschluss; das ist ein Modellwert.

### `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 3a3269aa4a2e95d780ad (luecke): Ein Jahresabo ohne Abbuchung im letzten Monat ist im Haushalt trotzdem eine laufende Verpflichtung; c3ff13d7ca048da95112 (luecke): Bei einer Lastschrift kannst du die Abbuchung über deine Bank zurückgeben lassen; ec052a0155f98740a3b5 (praezision): Ein Dienst, der gegen Gebühr kündigt, ändert nichts an den Fristen; ee3a722844f4b84b84b8 (luecke): Die häufigste Panne ist die Kündigung zum falschen Zeitpunkt

### `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 1dbeb2f8c51e78d11d49 (luecke): Behauptung, dass klassische Filialbanken jährlich 150 € bis 250 € an reinen Gebühren kosten, ist unbelegt.; 33e736ac6afe996b491a (luecke): Behauptung, dass Echtzeit‑Überweisungen bei kostenlosen Konten generell gebührenfrei sind, fehlt jede Quelle.; 96b7b7768d402884810c (luecke): Aussage, dass Einlagen bis 100.000 € durch die deutsche Einlagensicherung geschützt sind, wird nicht belegt.; a25bb6bbcb25ba8b0e22 (luecke): Angabe von Dispozinsen von 8 % bis 11 % ohne Quellenangabe.; f94f8ba1e4342e67e45a (luecke): Angabe, dass ein Kontowechsel 120 € bis 180 € im Jahr spart, fehlt jede Quelle.

### `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 991bda7b2298b751f4e6 (praezision): Die Behauptung einer garantierten Versorgung ist rechtlich zu weitgehend; die Bundesnetzagentur führt lediglich Unternehmenspflichten und die Grundversorgung als Aufsichtsthemen auf.; ae71596724d7a243217b (luecke): Der Artikel ignoriert die regulatorisch und technisch relevante Kupfer-Glas-Migration, welche die langfristige Verfügbarkeit und den Wechselzwang von DSL-Anschlüssen maßgeblich beeinflusst.

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 43470330b3b48c9cee49 (luecke): Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer.; 8ddc1025e45be176ad3a (luecke): Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text.; 95d6d2877620e5a056ce (luecke): Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht.; ab16029999747466a638 (luecke): Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird.; b057dee3603e09f494b5 (luecke): Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise.

### `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 91894b9b1535765acdca (luecke): Der Artikel versäumt es, den gesetzlichen Regulierungsrahmen (z. B. Entschädigung bei Wechselproblemen) zu nennen, obwohl die Fachseite der Aufsichtsbehörde als Beleg angeführt wird.; f7b9c93c6a9be1368b06 (veraltet): Die Einstufung von Glasfaser als teure 'Premium-Variante' ist überholt, da neue Schnäppchentarife den Markt preislich verändern.

### `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 4afb8daed73677ee6224 (luecke): Angabe, dass 58 % der Nutzer ihr Haushaltsbuch digital führen, beruft sich angeblich auf Statista 2025, jedoch wird keine Quelle genannt.; 9eb9a90899cc8ca66020 (luecke): Sparpotenzial‑Beispiele (z. B. DSL‑Tarifwechsel von 44 € auf 24 €) enthalten konkrete Zahlen ohne Quellenangabe.; b4bd085bc84a6131b644 (luecke): Behauptung, dass 60 % der Haushalte in Deutschland ihr Geld nicht nachverfolgen, wird mit einer Auswertung der Stiftung Warentest angegeben, jedoch fehlt ein entsprechender Nachweis.; baed76dc211bd15dd46f (praezision): Versprechen, dass ein Haushaltsbuch „schnell“ zeigt, welche Posten sich lohnen, ist nicht quantifiziert und fehlt an konkreten Evidenzangaben.; d7c3cfb422310cf26ca6 (praezision): Die Aussage, dass die 50‑30‑20‑Regel für ein Nettoeinkommen von 2.500 € realistisch sei, wird ohne Hinweis auf regionale Unterschiede oder empirische Daten präsentiert.

### `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 3fe383f6d452737f66f2 (praezision): Die im Teaser und Text genannten monatlichen Ersparnisse von 350 € bis 600 € werden als Marktfakten ohne Quellenbeleg oder methodische Herleitung (z. B. Referenzhaushalt des Statistischen Bundesamtes) angeführt.; 7bba759bbb4ca14c7f35 (luecke): Der Ratgeber empfiehlt Tarifwechsel bei Energie zur Kostensenkung, verschweigt aber den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die Kalkulation der 50-Prozent-Fixkostenquote gefährdet.; e8e32a383b6f803cc8d4 (veraltet): Die Einschätzung zur Inflation ist unpräzise: Die aktuelle Inflationsrate liegt laut Destatis bei +2,8 % (Oktober 2026), wodurch die genannten Tagesgeldzinsen von 0,5 % bis 1,5 % den Wertverlust deutlich weniger ausgleichen als suggeriert.

### `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 0b4755213f0c38321710 (luecke): Behauptung 'kein üblicher Wechselgewinn' ohne Daten; 3e0c5fa74179e97866b8 (luecke): Preisangabe 9,99 € monatlich ohne Quelle; ae90ebae2842ff9f97f1 (praezision): Aussage über Downloadwert vs Gesprächsqualität ohne Beleg; b2611d9120121d0ad785 (praezision): Empfehlung, nicht den günstigsten Tarif zu wählen, fehlt Beleg; fcb8168c18bd423c5180 (praezision): Unterschiedliche Aufgaben von 2‑Jahres‑ vs monatlich kündbarem Vertrag ohne Beleg

### `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` (blockiert, Risikoklasse hoch)

- **T1-zeichenlaenge** [technik]: Zeichenlänge zu-kurz/zu-lang (check_length.py)
- **T5-lesbarkeit** [technik]: Flesch 51.5 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 3ad12cdcf94bd8459bd8 (luecke): Bei der Erläuterung von Vermittlungsportalen fehlt die Einordnung als 'Kreditdienstleistungsinstitute', die die Bundesbank als spezifischen Aspekt der Finanzaufsicht führt.

### `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 278d89267d9122a1e9d8 (luecke): Angaben zu gesetzlichen Vorgaben für Warmwassertemperaturen zur Vermeidung von Legionellen werden nicht durch die bereitgestellten Quellen gestützt.; 450c3aa629342062825e (luecke): Die Aussage, dass Warmwasser der zweitgrößte Kostenposten im Haushalt ist, wird nicht durch eine der bereitgestellten Quellen belegt.; 7601167c9f3560093fb0 (luecke): Die Behauptung, dass Warmwasser in der Heizkostenabrechnung üblicherweise als eigener Block ausgewiesen wird, fehlt eine Quellenangabe.; 7efbcd7a4275fe1577bb (luecke): Verweise auf die Verbraucherzentrale (Tipps zum Heizkosten sparen, Heizung optimieren) können nicht mit den angegebenen Fundstellen belegt werden.; 971a719f94ca492f640e (luecke): Der Preis von 0,30 € pro Kilowattstunde in der Modellrechnung ist nicht mit einer Quelle belegt.

### `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 1cc830a25d3ae505dd0e (praezision): Die Frist von acht Wochen gilt für autorisierte Lastschriften (ohne Angabe von Gründen). Bei unautorisierten Lastschriften (ohne Mandat) beträgt die gesetzliche Frist zur Rückgabe 13 Monate.; 32f827af8f4695488e97 (praezision): Banken dürfen vom Zahler (Kontoinhaber) in der Regel kein Entgelt für eine Rücklastschrift verlangen, die mangels Deckung oder wegen eines berechtigten Widerspruchs erfolgt.; 642d9c53e557ff642257 (luecke): Es fehlt der Hinweis auf die gesetzliche 13-Monats-Frist gemäß Zahlungsdiensterecht (PSD2) für die Meldung nicht autorisierter oder fehlerhafter Kartenzahlungen.; 8230373c2c33722d66d8 (praezision): Die Bezeichnung als 'wirksamste Maßnahme' ist ein Superlativ ohne messbare Datenbasis oder Vergleich mit anderen Sicherheitsmechanismen.; efee7b0cefffa501cc57 (praezision): Stromabschläge sind untypisch für Daueraufträge, da sich die Beträge nach Jahresabrechnungen meist ändern; hier ist die Lastschrift der Standard, um Zahlungsfehler zu vermeiden.

### `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: dc1e5d50a58f50e0ade1 (luecke): Die verlinkte Seite der Bundesnetzagentur ist eine reine Navigations-Übersicht und enthält keine der im Text versprochenen Beschreibungen zu Tarifbestandteilen oder Preisregelungen.; def8ad23c34566c795fe (praezision): Die Verknüpfung der HT/NT-Definition mit der Bundesnetzagentur ist unpräzise, da die verlinkte Seite lediglich eine Themenübersicht ohne fachliche Definitionen darstellt.

### `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 19a724ba20628f34cd01 (luecke): Eine feste Frist für die Entstörung nennt das Gesetz nicht.; 4126d33a9dd92716b286 (luecke): Ein unentschuldigter no-show zählt nur, wenn du ihn zeitnah meldest.; 67fbe0b49bb4e6bb48b7 (luecke): Die Pflichten aus dem TKG gelten für alle Zugangsarten.; cb5f849bfd26ad8121eb (luecke): Der Anbieter muss die Störung beheben; eine pauschale Wartezeit gibt es nicht, aber eine Pflicht zur zeitnahen Entstörung.; f108d554ff8861370b64 (luecke): Bei einem längeren Ausfall hast du zwei Hebel: die Gutschrift für die ausgefallene Leistung und bei einigen Verzögerungen die Entschädigung.

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 16b3b8584ff802803aa9 (luecke): Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Referenz.; 7ff042b6fe804cdf101b (praezision): Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und ohne messbare Daten unpräzise.; bec83c4b814183fa1086 (luecke): Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Quelle gestützt.; f9aff86b6eba71b153a6 (luecke): Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt.; fed9215b770ea4879eda (luecke): Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird ohne jegliche Quelle angegeben.

### `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 20c08cb650ef6e24af64 (luecke): Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet.; 6aafb23c0c6dbb06ce3b (veraltet): Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %.

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 24f05ddc03ffdd50118f (praezision): Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht.; 4816322f061dfdc03bcd (luecke): Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln.; 7017065ee7c74c7ae452 (veraltet): Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen.

### `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 1e06a96f6f71e104ce0b (praezision): Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von nur 0,4 %, was die Priorisierung der Sparbemühungen relativiert.; 81c6a707139046b83ccd (luecke): Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 % unerwähnt, die ein wesentlicher Treiber der Haushaltsausgaben ist.; 8cc00288af8a1f2b02d8 (veraltet): Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-Annahmen im Haushaltsbuch beeinflusst.

### `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 3f0a88ede9d44ee910cb (luecke): Es fehlt der Hinweis auf das offizielle Beschwerdeportal der Bundesnetzagentur, über das Verbraucher Probleme mit Anbietern direkt melden können.; 51e259fd2d8582e774f7 (luecke): Der Ratgeber versäumt es, bei der Tarifprüfung auf die behördlichen Schlichtungsverfahren hinzuweisen, die Verbrauchern bei Streitigkeiten mit Energieversorgern zur Verfügung stehen.; 55f8eeedc587cf0895ee (luecke): Der Artikel erwähnt keine behördlichen Informationsquellen wie das Verbraucher-Radar, das Transparenz über den Energiemarkt und Verbraucherschutzthemen bietet.

### `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 009906e47bcc8265b36a (luecke): Angestellte reichen oft drei bis sechs Monatsausgaben als Sicherheit; e0293a43782c64955b27 (luecke): Selbstständige sollten sechs‑ bis zwölf‑Monats‑Ausgaben als Reserve planen

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 5a1bf10697f58e5fe14a (luecke): Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Stand Oktober 2026) unerwähnt, die den finanziellen Druck auf Haushalte massiv erhöht.; e48f9237cff6397c49a6 (praezision): Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von +2,8 % gesetzt, welche die reale Kaufkraft des gesparten Geldes mindert.; f6de6b078d49f9d42e0e (praezision): Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei Nahrungsmitteln, was diesen Hebel gegenüber den stark steigenden Energiekosten relativiert.

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 6cb2229c5eb83b02da23 (veraltet): Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet.; f00055a1cb65ee22165f (luecke): Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet.

### `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 7a87eaaa2b863ba8cc46 (luecke): Ein relevanter regulatorischer Rahmen (z. B. Vorgaben der Bundesnetzagentur oder BDEW) wird nicht genannt, obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren.; 9d67a5e6bd11212c7c1e (praezision): Die Aussage, dass bestimmte Gerätegruppen (TV‑Ecke, Homeoffice, alte Audio‑Technik) zuerst zu senken „lohnt“, wird ohne messbare Daten oder Vergleichskriterien gemacht.; a54abc1cad73d20fb689 (luecke): Die konkreten Jahreskosten (z. B. 32 € für 10 W Standby) beruhen auf dem nicht belegten Strompreis und werden nicht als Modellrechnung gekennzeichnet.; a7d1cf6485921e117919 (luecke): Der angegebene durchschnittliche Strompreis von 37,3 Cent/kWh (BDEW‑Schnitt) wird ohne Quellenangabe genannt.; a7f69a854430d62a4a3e (luecke): Die Empfehlung, dass ein günstigerer Arbeitspreis der zweite wichtigste Hebel sei, fehlt jede Quelle oder regulatorische Einordnung.

### `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 3eab428a91b1b16b7df8 (luecke): Die aktuelle Inflationsrate von +2,8 % wird nicht genannt, obwohl sie für die empfohlene regelmäßige Prüfung der Pufferhöhe die zentrale Rechengröße darstellt.; 7da9383cbc6a45e1a3ac (praezision): Der Modellwert für Lebensmittel (320 €) wird nicht mit der aktuellen Preissteigerung von +0,4 % abgeglichen, um die Validität der Kalkulationsbasis zu stützen.; da7852bcca291061c39b (praezision): Die Modellrechnung für Fixkosten berücksichtigt nicht die spezifische Teuerung bei Energie (+12,7 %), was bei der Kalkulation von Strom und Gas zu einer Unterdeckung führen kann.

### `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 334751e6f61ad0033fe4 (luecke): Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quellenangabe.; 36759a5efe5e8e5163d0 (luecke): Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird ohne Quelle angegeben.; 942922d1afd7844618e9 (luecke): Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt.; d41f0d5ce8798df0211b (praezision): Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder Vergleichskriterien.; e139d0769faadd04392a (luecke): Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt.

### `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 68afba3e6a16a364ce45 (praezision): Die Kündigungsfrist in der Grundversorgung ist gesetzlich exakt auf zwei Wochen festgelegt, was für den Leser eine wichtigere Information ist als die vage Bezeichnung 'kurze Fristen'.; dc5ff05c5dda79d01373 (luecke): Es fehlt der Hinweis auf die gesetzliche Befristung der Ersatzversorgung auf maximal drei Monate, nach denen sie automatisch endet.

### `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 5c096f87730532352820 (luecke): Gesetze nennen konkrete Auszahlungsfristen im Einlagensicherungsfall.

### `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 06bc5a6bc11098317697 (luecke): Keine Quelle für Umrechnungsfaktor von Kubikmetern in Kilowattstunden angegeben.; 471944cae24a034c7c00 (luecke): Keine Quelle für Aufbewahrungsfrist von drei Jahren angegeben.; 780af701a2eaa465d46a (luecke): Behauptung, dass die meisten Versorger Selbstablesungen außerhalb des Fensters akzeptieren, fehlt belegt.

### `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 33278b9e7942ebfdbbac (luecke): Definition des Begriffs „Last Minute“ (maximal 14 Tage zwischen Buchung und Abreise) wird mit dem Deutschen Reiseverband angegeben, jedoch fehlt ein Nachweis.; 6ad7358a9afcfef3babb (praezision): Angabe, dass Preisalarme keinen Tiefstpreis garantieren, wird nicht durch konkrete Zahlen oder Vergleichsstudien belegt.; 7c375a3e1a9bfab1468c (luecke): Hinweis auf § 651r BGB (Insolvenzsicherung bei Pauschalreisen) enthält keinen Verweis auf eine Rechtsquelle oder Verbraucherzentrale‑Information.; ea11d36614fa115503b4 (luecke): Behauptung, dass Nachlässe von bis zu 50 % nur Einzelfälle sind, wird ohne Quellenangabe präsentiert.; f7b1c869dd8e442eaf16 (praezision): Aussage, dass der „beste Zeitpunkt zum Buchen“ ein Modellwert sei, bleibt vage und ohne messbare Daten oder Studien untermauert.

### `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 6b5921bdc76490587167 (luecke): Seit 2026 nutzen die großen Anbieter die Technik mit dem Namen Vectoring; das ist ein Modellwert. Sie senkt das Rauschen auf der Leitung. In der Stadt sind damit bis zu 250 Mbps stabil drin.; 8436b91bdb63a6316979 (praezision): Preisgarantie über mindestens 12 Monate; ohne Garantie darf der Anbieter bald erhöhen, oft um bis zu 10 %.; a4ff01e649b789f19e6a (luecke): Für 50 Mbps zahlst du heute meist ca. 20–40 € im Monat; das ist ein Beispielwert.

### `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 58f03a64adaaf8125959 (praezision): Während der Artikel vor hohen Kosten für Festmenüs warnt, liegt die Preissteigerung bei Nahrungsmitteln laut Destatis im Oktober 2026 bei lediglich +0,4 % und damit deutlich unter der allgemeinen Inflation.; a7f5f01ef15a38839a0d (praezision): Die Pauschale für 'Anreise und Mobilität' (10 % des Budgets) berücksichtigt nicht die überdurchschnittliche Preissteigerung bei Energie von +14,9 %, die Fahrtkosten im Vergleich zum Vorjahr massiv verteuern kann.; bcc2bdf06220d5097133 (luecke): Die Modellrechnung für das Weihnachtsbudget (600 €) lässt die aktuelle Teuerungsrate unberücksichtigt. Laut Statistischen Bundesamt liegt die Inflationsrate im Oktober 2026 bei +2,8 %, was als Referenzwert für die Budgetplanung zum Vorjahr fehlt.

### `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 25d6b9a720f981e8e9df (praezision): Bei der Bewertung flexibler Kosten sollte die moderate Preisentwicklung bei Nahrungsmitteln (+0,4 %) den stark steigenden Energiekosten gegenübergestellt werden, um Sparpotenziale zu priorisieren.; 3693b612533c24dcd1ea (luecke): Der Ratgeber empfiehlt die Prüfung von Stromverträgen, vernachlässigt aber den massiven Preistrend bei Energie von +12,2 %, der die Kalkulation der Fixkosten aktuell dominiert.; c877eeff8842942c0071 (praezision): Die allgemeine Budget-Transparenz ist ohne Einbezug der Inflationsrate von 2,8 % unvollständig, da Preissteigerungen die Planungssicherheit der 'festen Kosten' kontinuierlich untergraben.

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 089b89138417e63a3dcf (luecke): Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet.; 1158934e7a18c7b2099b (luecke): Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt.; 3716cfd3ab5aec6d774b (praezision): Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote.

### `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 26b1c694d76bcc7af50f (luecke): Der Ratgeber versäumt es, den für den Verbraucherschutz zentralen Regulierungsrahmen der 'Unternehmenspflichten' zu nennen, den die Bundesnetzagentur explizit als Fachthema führt.; 9593e535bce55f4283e6 (praezision): Die Empfehlung zum Preisvergleich lässt den aktuellen Marktdruck (sinkende Umsätze bei O2) außer Acht, der für die Verhandlung von Rückholangeboten bei Kündigung entscheidend sein kann.

### `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 7067eabb89a917ae67a4 (luecke): Die Verbraucherzentrale sammelt Hinweise zu Reisebuchungen, auch zu unklaren Angeboten und Problemen mit Online-Buchungen.; af2ccb4222eeb195222f (praezision): Ein Mietwagenvergleich kann Angebote sichtbar machen, prüft aber nicht automatisch, ob das Auto zum individuellen Urlaub passt – ohne Messgröße bleibt die Aussage ungenau.; d9c8b522bf1dcaed0340 (luecke): Die Verbraucherzentrale beschreibt, dass sich eine Pauschalreise unter bestimmten Bedingungen auf eine andere Person übertragen lässt.; e2975509f3f130de0755 (luecke): Die Verbraucherzentrale empfiehlt, größere Ausgaben vorauszuplanen und das eigene Budget im Blick zu behalten.; f1704e45e970a8f4b078 (luecke): Bei einer Pauschalreise gilt die Mitteilung als rechtzeitig, wenn sie dem Veranstalter spätestens sieben Tage vor Reisebeginn zugeht (§ 651e BGB).

### `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: a10511ed618384aa7b88 (luecke): Der Artikel nennt keine regulatorischen Vorgaben oder Zertifizierungen (z. B. CE‑Kennzeichnung, Sicherheitsanforderungen) für Smart‑Home‑Geräte, obwohl solche Vorgaben von der Bundesnetzagentur beschrieben werden.

### `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: a74029dd4e284794d697 (luecke): Eine separate Meldung beim Netzbetreiber ist im Standardfall nicht mehr nötig.; c45ea4bb1a6f2330679a (luecke): Keine bundesweite Zuschusspflicht: Zuschüsse kommen, wenn überhaupt, von Städten, Gemeinden oder Ländern.

### `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 4d0125136c5b940946e4 (luecke): Lichtsteuerung: Bedarfssteuerung – 2 bis 5 % des Stromverbrauchs.; 7aeb2098034d16a46885 (luecke): Anbieter locken mit Neukundenboni, die nach der üblichen Erstlaufzeit entfallen; danach steigt der Arbeitspreis massiv an.; ea97b5dd6695de127fd2 (luecke): Heizungssteuerung: Smarte Thermostate können Heizkosten einsparen. Die Spanne von 10 bis 25 % ist ein Beispielwert aus der Rechnung unten.

### `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 7c2624072c861d136c96 (luecke): Die pauschale Behauptung zu Preisunterschieden zwischen Standardtarifen und Angeboten ist ein Marktdatum ohne Beleg oder eigene Messung (Regel 9a/9e).; d9d3004fbc05895c3f79 (praezision): Die Aussage zum steigenden Strompreis ist unpräzise; die Quelle belegt einen konkreten Anstieg der Energiepreise um +12,7 %.

### `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 1dc0f20f9ab3a6b783bc (luecke): Behauptung, dass ein fehlender Ausweis zu empfindlichen Bußgeldern führt, fehlt eine belegbare Quelle.; 7b94ca07b36c0b7cb1cc (luecke): Aussage, dass Baudenkmäler von der Ausweispflicht befreit sind, wird nicht durch die angegebene Quelle gestützt.; 985f506ee04087bf7253 (luecke): Angabe, dass ein Wechsel von Energieeffizienzklasse F zu C über 2.000 € Jahresersparnis bringt, ist unbelegt.; ee321fa37210590f7e9b (luecke): Keine Quelle für die Angabe, dass ein Energieausweis ein volles Jahrzehnt gültig ist, sofern keine größeren Umbauten erfolgen.

### `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 19ab248b17415c73edfb (luecke): Thermostat um 1 °C senken | 4 % – 6 % der Heizkosten; 372bb51051e8bd7c5f71 (luecke): Viele Anbieter belohnen einen niedrigen Verbrauch mit besseren Konditionen; 6aaff85e3a7591d0c5b2 (luecke): für dich entstehen keine Mehrkosten; 7e6087a4117a857a92c8 (luecke): Durch diese zwei Maßnahmen sparst du in dieser Beispielrechnung jährlich rund 140 €; e28b4ad1f6d608d2ec77 (luecke): Strom (LED‑Umrüstung) | 100 € – 140 € | etwa 8 %

### `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 34e4bb2acfa235699da5 (luecke): Der Artikel erwähnt keinen regulatorischen Rahmen (z. B. Bundesnetzagentur) obwohl diese Institution für Strom‑ und Gasmärkte zuständig ist.; 42b9d842341d892d42d0 (luecke): Angaben zu staatlichen Zuschüssen (bis zu 70 %) und deren Auswirkung auf den Eigenanteil fehlen eine Quellenangabe.; 866d8b711dc2de369444 (luecke): Hinweis, dass ein spezieller Stromtarif für Wärmepumpen die Kosten senkt, wird nicht durch eine Quelle belegt.; bd4c46a336f33a639f05 (luecke): Preisannahmen für Strom (30 ¢/kWh), Gas (10 ¢/kWh) und CO₂‑Aufschlag (5 ¢/kWh) werden ohne belegbare Daten präsentiert.; e76768fdef3ef5afa026 (luecke): Die behauptete Amortisationsdauer von 10‑12 Jahren für eine Wärmepumpe basiert auf einer Modellrechnung ohne nachweisbare Quelle.

### `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 1eae5c7e2bbd95a3362c (luecke): Tabelle mit konkreten kWh‑Werten und Euro‑Ersparnissen für neue vs. alte Geräte.; 8547ce3daa75aabb30d4 (luecke): Annahme von 40 ct/kWh und daraus resultierende Jahres‑Ersparnis von 52 € für einen Kühlschrank‑Tausch.; c8b197692bd0023c87bf (luecke): Behauptung, dass ein neuer Wärmepumpentrockner „sogar noch schneller“ die Anschaffungskosten amortisiert.; e40a2ee5c7baa5f8567b (luecke): Sparsame Geräte senken deinen Verbrauch in der Beispielrechnung unten um bis zu 40 %.; feb71513c6fb7064dc92 (luecke): Der Stromverbrauch von Kühlschrank und Waschmaschine macht in der Modellrechnung rund 30 % der Kosten im Haushalt aus.

### `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 04ae33652c1c5eb4e2b8 (luecke): Ein kurzer Check spart dir oft mehrere hundert Euro im Jahr.; 5223a3c7287ff81939cd (luecke): Faustregel: ... mehr als 5 % deines Nettoeinkommens ... Meist sinken diese Kosten um über 80 %; 9800545ae945ec280b34 (luecke): Ein Wechsel ist für dich in der Regel komplett kostenlos als Beispielwert.; bc0e4f2eb357a682c674 (luecke): Bei einem normalen Einkommen sollten die Gebühren fast Null sein.

### `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 0d1977a0b6a7b59136f2 (praezision): Die Bezeichnung als 'beste Tarife' ist ein Superlativ ohne messbare Daten oder eigene Vergleichsmetrik.; 228ef205074fdc3fb4b3 (luecke): Der Heiz-Faustwert (6 % Ersparnis pro Grad) fehlt in der angegebenen Quelle und ist nicht am Satz belegt.; d7c301604b02d49e8d65 (luecke): Der behauptete Budgetanteil von 30 % für Energie ist ein spezifischer Marktwert, der in der angegebenen Quelle nicht vorkommt.

### `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 3bfeb0118af92a780a47 (luecke): Bei 5 % Rendite im Jahr entstehen rund 30.000 € – keine Quelle für die angenommene Rendite angegeben.; ed2161154dcee85da1ee (luecke): Angabe, dass die Einrichtung eines Sparplans meist weniger als 15 Minuten dauert, fehlt belegt.; f593fe21275bd9dcefef (luecke): Behauptung, dass einige Broker bereits ab 1 € monatlich starten, ohne Quelle.

### `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 98eb45f772ad7a0aac7b (luecke): Das Sparversprechen von '500 € mehr' in der PIN-Beschreibung nutzt im Text Referenzwerte (120 € Strom, 80 € Kfz), für die in der Quelle keine Marktdaten oder Durchschnittswerte als Beleg vorliegen.; b7f0d52968d89cdf8c5b (praezision): Die Einschätzung zur Datensicherheit von Cashback-Apps bleibt ohne Nennung konkreter rechtlicher Grundlagen (DSGVO) unpräzise, während die Quelle explizit auf rechtliche Verbraucherthemen fokussiert.; be911855d67f998be662 (luecke): Der Ratgeber nennt keinen Regulierungsrahmen für Reisebuchungen (z. B. Fluggastrechte oder Stornierungsregeln), obwohl die Quelle diese als zentrale Informationsbereiche ausweist.

### `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 381dd90113dd1ee72f39 (praezision): Das Versprechen, 'alle Gebühren' auf Portalen zu sehen, ist ohne Messgröße unpräzise, da Portale systembedingt nur eine Marktauswahl zeigen.; 4483a81dd1c292034cd0 (praezision): Die Warnung vor einer 'sehr hohen Strafgebühr' am Gate ist ein Superlativ ohne messbare Daten oder konkrete Preisbeispiele.; 6f4b591e9cadb27adf49 (luecke): Bei der Erwähnung von Stornierungen durch Airlines fehlt der Hinweis auf den rechtlichen Rahmen (z. B. EU-Fluggastrechte).; cf60024b74a5e86b50c0 (luecke): Die statistische Aussage zur Preisgünstigkeit von Dienstag und Mittwoch ist eine Marktprognose ohne Beleg in der genannten Quelle.

### `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 4284fd2d9c9005e7af8f (praezision): Behauptung, dass Überladung der Maschine zu schnellerem Verschleiß und teuren Reparaturen führt, wird ohne konkrete Daten oder Messgröße angegeben.; 84e247f17354e224c973 (praezision): Aussage, dass das richtige Beladen allein die Fixkosten senkt, ohne weitere Maßnahmen, ist ein pauschales Leistungsversprechen ohne Nennung von Mechanismen oder Grenzen.; a2a7dc69f10393af6531 (luecke): Die Modellrechnung (0,9 kWh/50 L bei vollem Waschgang, 0,6 kWh/35 L bei halbem Waschgang, Strompreis 0,40 €/kWh, Wasserpreis 0,005 €/L) und die daraus resultierende Jahresersparnis von 22 € fehlen einer fundierten Quelle.; cb794331f1cc0c715a55 (luecke): Die Aussage, dass bei 4 Waschgängen pro Woche ein durchschnittlicher Haushalt rund 5 € jährlich an Strom‑ und Wasserkosten spart, ist nicht mit einer Quelle belegt.; e6729081522126e972c2 (luecke): Angabe, dass ein optimal beladener Trommel (ca. 80 % Kapazität) bis zu 15 % weniger Wasser und Energie verbraucht, wird nicht durch eine Quelle belegt.

## Warnungen ohne Blockade (4 Artikel)

- `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` – T1w-zeichenlaenge-optimum: Zeichenlänge ueber-optimum (18809 Zeichen, Optimum 12.000–18.000)
- `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` – T1w-zeichenlaenge-optimum: Zeichenlänge ueber-optimum (18252 Zeichen, Optimum 12.000–18.000)
- `2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck` – T1w-zeichenlaenge-optimum: Zeichenlänge ueber-optimum (18150 Zeichen, Optimum 12.000–18.000)
- `2026-11-12-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein` – T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (11340 Zeichen, Optimum 12.000–18.000)

## Entwürfe – was vor dem Livegang noch offen ist

| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |
|---|---|---|---|---|
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | hoch | ausstehend | frisch geprüft vor 27 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | hoch | vorhanden | frisch geprüft vor 27 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | hoch | vorhanden | frisch geprüft vor 27 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | hoch | ausstehend | frisch geprüft vor 27 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | hoch | vorhanden | frisch geprüft vor 27 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | standard | nicht erforderlich | frisch geprüft vor 20 Tagen (Intervall 45 Tage) | 2026-12-21 |
| `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 15 Tagen (Intervall 45 Tage) | 2026-12-26 |
| `2026-10-05-die-50-30-20-regel-einfach-erklaert` | standard | nicht erforderlich | frisch geprüft vor 52 Tagen (Intervall 90 Tage) | 2027-01-03 |
| `2026-10-06-markt-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 49 Tagen (Intervall 90 Tage) | 2027-01-06 |
| `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2027-01-02 |
| `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 16 Tagen (Intervall 45 Tage) | 2026-12-25 |
| `2026-10-09-7-gewohnheiten-fuer-finanzielle-freiheit` | standard | nicht erforderlich | frisch geprüft vor 44 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-12-stromfresser-im-haushalt-entlarven` | standard | nicht erforderlich | frisch geprüft vor 44 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` | standard | nicht erforderlich | frisch geprüft vor 15 Tagen (Intervall 30 Tage) | 2026-12-11 |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 8 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet` | standard | nicht erforderlich | frisch geprüft vor 37 Tagen (Intervall 90 Tage) | 2027-01-18 |
| `2026-10-19-urlaubskasse-clever-aufbessern` | standard | nicht erforderlich | frisch geprüft vor 14 Tagen (Intervall 30 Tage) | 2026-12-12 |
| `2026-10-21-mietwagen-fallen-im-urlaub-vermeiden` | standard | nicht erforderlich | frisch geprüft vor 9 Tagen (Intervall 30 Tage) | 2026-12-17 |
| `2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen` | standard | nicht erforderlich | frisch geprüft vor 28 Tagen (Intervall 45 Tage) | 2026-12-13 |
| `2026-10-26-gastarife-vergleichen-vor-dem-herbst` | standard | nicht erforderlich | frisch geprüft vor 28 Tagen (Intervall 30 Tage) | 2026-11-28 |
| `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | standard | nicht erforderlich | frisch geprüft vor 27 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` | erhoeht | nicht erforderlich | frisch geprüft vor 26 Tagen (Intervall 45 Tage) | 2026-12-15 |
| `2026-11-02-last-minute-urlaubsangebote-sichern` | standard | nicht erforderlich | frisch geprüft vor 23 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` | standard | nicht erforderlich | frisch geprüft vor 21 Tagen (Intervall 30 Tage) | 2026-12-05 |
| `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` | standard | nicht erforderlich | frisch geprüft vor 19 Tagen (Intervall 30 Tage) | 2026-12-07 |
| `2026-11-09-handytarife-vergleichen-so-findest-du-den-guenstigsten-tarif` | erhoeht | nicht erforderlich | frisch geprüft vor 16 Tagen (Intervall 45 Tage) | 2026-12-25 |
| `2026-11-11-kreditkarte-ohne-jahresgebuehr-die-besten-kostenlosen-karten` | erhoeht | nicht erforderlich | frisch geprüft vor 14 Tagen (Intervall 45 Tage) | 2026-12-27 |
| `2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` | erhoeht | nicht erforderlich | frisch geprüft vor 23 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-13-tagesgeld-und-zinsen-so-parkst-du-dein-geld-sicher` | erhoeht | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 45 Tage) | 2026-12-30 |
| `2026-11-16-die-50-30-20-regel-bringt-ordnung-wohin-mit-dem-gehalt` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | 2026-12-31 |
| `2026-11-16-e-auto-laden-so-senkst-du-deine-stromkosten` | erhoeht | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | 2026-12-31 |
| `2026-11-16-stabile-gaskosten-lohnt-sich-eine-preisgarantie-fuer-dich` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | 2026-12-31 |
| `2026-11-18-strom-sparen-im-haushalt-20-tipps-fuer-die-naechste-rechnung` | standard | nicht erforderlich | frisch geprüft vor 7 Tagen (Intervall 45 Tage) | 2027-01-03 |
| `2026-11-20-standby-kosten-senken-die-fiesesten-stromfresser-im-check` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | 2027-01-04 |
| `2026-11-20-waermepumpe-vs-gasheizung-was-lohnt-sich-2026` | standard | nicht erforderlich | frisch geprüft vor 5 Tagen (Intervall 30 Tage) | 2026-12-21 |
| `2026-11-22-strompreis-2026-herbst-check-fuer-deine-stromkosten` | standard | nicht erforderlich | frisch geprüft vor 17 Tagen (Intervall 30 Tage) | 2026-12-09 |
| `2026-11-22-wertvolle-gebrauchte-moebel-finden-so-pruefst-du-qualitaet` | standard | nicht erforderlich | frisch geprüft vor 9 Tagen (Intervall 90 Tage) | 2027-02-15 |
| `2026-11-23-photovoltaik-lohnt-sich-eine-solaranlage-2026` | standard | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 45 Tage) | 2027-01-07 |
| `2026-11-25-balkonkraftwerk-der-einfache-einstieg-in-die-solarenergie` | standard | nicht erforderlich | frisch geprüft vor 1 Tagen (Intervall 45 Tage) | 2027-01-09 |
| `2026-11-25-dsl-wechseln-ohne-ausfall-so-sparst-du-beim-internet` | standard | nicht erforderlich | frisch geprüft vor 1 Tagen (Intervall 45 Tage) | 2027-01-09 |
| `2026-11-25-internet-tuning-kostenlos-dns-server-fuer-mehr-speed` | standard | nicht erforderlich | frisch geprüft vor 1 Tagen (Intervall 90 Tage) | 2027-02-23 |
| `2026-11-26-carsharing-kosten-lohnt-sich-das-auto-teilen-fuer-dich` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-deine-naechtliche-grundlast-strom-so-erkennst-du-wo` | standard | nicht erforderlich | frisch geprüft vor 14 Tagen (Intervall 45 Tage) | 2026-12-27 |
| `2026-11-26-ferienwohnung-vergleich-so-rechnest-du-kosten-ehrlich` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-handy-kosten-senken-so-entlarvst-du-teure-tarif-fallen` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-heizperiode-beginn-2026-warum-der-gas-check-im-oktober` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-homeoffice-zu-zweit-reicht-deine-leitung-wirklich-aus` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-kleiderkreislauf-im-freundeskreis-so-klappt-dein-tausch` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-kreditkarte-ohne-fremdwaehrungsgebuehr-2026` | erhoeht | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-lebensmittel-retten-clever-planen-statt-teuer-wegwerfen` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-strom-sparen-sommer-10-smarte-tipps-fuer-heisse-tage` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-26-vorrat-planen-leicht-gemacht-so-sparst-du-beim` | standard | nicht erforderlich | frisch geprüft vor 9 Tagen (Intervall 90 Tage) | 2027-02-15 |
| `2026-11-26-wlan-verbessern-verstaerker-oder-mesh-was-passt` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |

## Ausnahmen (Falsch-Alarm-Protokoll)

Keine aktiven Ausnahmen – alle Checks wirken unverändert.

---
_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer Beweis ist niemals „bestanden“._
