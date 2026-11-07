# Release-Scorecard – die Produktionswahrheit

**Stand:** 2026-11-07 · **Modus:** kandidaten · **Engine:** `scripts/release_scorecard.py` · **SSOT:** `data/release_scorecard.yaml`

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
| ⚠️ warnung | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | ✅ bestanden | ➖ nicht erforderlich | ✅ bestanden |

## Live-Bestand (Artikel für Artikel)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-10-dsl-wechselbonus-sichern` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **nicht beweisbar** |
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **nicht beweisbar** |
| `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **nicht beweisbar** |
| `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **nicht beweisbar** |
| `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` | ⚠️ warnung | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **nicht beweisbar** |
| `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **nicht beweisbar** |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **nicht beweisbar** |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-11-19 | **nicht beweisbar** |
| `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-22 | **nicht beweisbar** |
| `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **nicht beweisbar** |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | ⚠️ warnung | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **nicht beweisbar** |
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **nicht beweisbar** |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **nicht beweisbar** |
| `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **nicht beweisbar** |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **nicht beweisbar** |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-07 | **nicht beweisbar** |
| `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **nicht beweisbar** |
| `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **nicht beweisbar** |
| `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **nicht beweisbar** |
| `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **nicht beweisbar** |
| `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **nicht beweisbar** |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | ⚠️ warnung | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **nicht beweisbar** |
| `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **nicht beweisbar** |
| `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **nicht beweisbar** |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **nicht beweisbar** |
| `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **nicht beweisbar** |
| `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **nicht beweisbar** |
| `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **nicht beweisbar** |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **nicht beweisbar** |
| `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **nicht beweisbar** |
| `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **nicht beweisbar** |
| `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | ⚠️ warnung | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-13 | **nicht beweisbar** |
| `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **nicht beweisbar** |
| `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-18 | **nicht beweisbar** |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **nicht beweisbar** |
| `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-19 | **nicht beweisbar** |
| `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **nicht beweisbar** |
| `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **nicht beweisbar** |
| `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **nicht beweisbar** |
| `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **nicht beweisbar** |
| `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **nicht beweisbar** |
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **nicht beweisbar** |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **nicht beweisbar** |
| `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-23 | **nicht beweisbar** |
| `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **nicht beweisbar** |
| `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-07 | **nicht beweisbar** |
| `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-05 | **nicht beweisbar** |
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **nicht beweisbar** |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **nicht beweisbar** |
| `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **nicht beweisbar** |
| `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **nicht beweisbar** |
| `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **nicht beweisbar** |
| `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **nicht beweisbar** |
| `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **nicht beweisbar** |
| `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` | ⚠️ warnung | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **nicht beweisbar** |
| `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-14 | **nicht beweisbar** |
| `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **nicht beweisbar** |
| `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-25 | **nicht beweisbar** |
| `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar` | ✅ bestanden | ✅ bestanden | ❔ nicht beweisbar | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-12 | **nicht beweisbar** |

## Was blockiert – nach Prüfung, nicht nach Dimension

_Die Dimension sagt, wo es weh tut; der Check sagt, was zu tun ist. Besitz und Entscheidung stehen in `data/release_scorecard.yaml`._

| Check | Dimension | Wirkung | Entscheidet | Artikel |
|---|---|---|---|---|
| **T1w-zeichenlaenge-optimum** | technik | warnung | Maschine (deterministisch) | 5 |


## Faktenfrische-Deckung (der Takt gegen den Bestand)

_Ein Faktenalter wird nicht „plötzlich“ rot: Es wird überfällig, weil der Bestand mehr Prüfungen braucht, als der Takt liefert. Diese Rechnung ist die Ursache der F1-Funde – nicht der F4-Funde._

| Kennzahl | Wert |
|---|---|
| Seiten im Bestand (Posts + Ratgeber) | 115 |
| Fällig heute / überfällig | 0 / 0 |
| Bedarf | 2,82 Prüfungen/Tag (19,8/Woche) |
| Angebot | 4,00/Tag (Budget 4 × 1,00 Läufe/Tag) |
| **Deckung** | **142 %** |
| Rückstand abgebaut | **nicht abbaubar** im Horizont |
| Nächste Frist | `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` am 2026-11-12 (in 5 Tagen) |
| Empfohlenes Budget | 4 je Lauf (Limit 16) |
| Spitzentag (#1039) | ✅ mitgemessen (56 Bündeltage, kein Befund) |

✅ Deckung ausreichend: Der Takt kann den Bestand halten. Ein roter Faktenstand ist damit ein echter Inhaltsbefund (F4), kein Kadenz-Artefakt.

## Blockierende Funde (78 Artikel)

### `2026-08-10-dsl-wechselbonus-sichern` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` (nicht beweisbar, Risikoklasse hoch)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` (nicht beweisbar, Risikoklasse erhoeht)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` (nicht beweisbar, Risikoklasse hoch)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` (nicht beweisbar, Risikoklasse hoch)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` (nicht beweisbar, Risikoklasse hoch)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` (nicht beweisbar, Risikoklasse erhoeht)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` (nicht beweisbar, Risikoklasse erhoeht)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` (nicht beweisbar, Risikoklasse erhoeht)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` (nicht beweisbar, Risikoklasse erhoeht)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` (nicht beweisbar, Risikoklasse erhoeht)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` (nicht beweisbar, Risikoklasse erhoeht)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

### `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar` (nicht beweisbar, Risikoklasse standard)

- ❔ **F4-fachbefund** [faktenalter]: nicht beweisbar – Fachbefund-Ledger nicht beweisbar: Ungültige Folgeentscheidung für ('2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag', 'f83f21c1f2e2012f672e'): Vorgänger fehlt oder stimmt nicht

## Warnungen ohne Blockade (0 Artikel)

Keine.

## Entwürfe – was vor dem Livegang noch offen ist

| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |
|---|---|---|---|---|
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 8 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | hoch | vorhanden | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | hoch | vorhanden | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | hoch | vorhanden | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | hoch | vorhanden | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | standard | nicht erforderlich | frisch geprüft vor 1 Tagen (Intervall 45 Tage) | 2026-12-21 |
| `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 36 Tagen (Intervall 45 Tage) | 2026-11-16 |
| `2026-10-05-die-50-30-20-regel-einfach-erklaert` | standard | nicht erforderlich | frisch geprüft vor 33 Tagen (Intervall 90 Tage) | 2027-01-03 |
| `2026-10-06-markt-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 30 Tagen (Intervall 90 Tage) | 2027-01-06 |
| `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` | standard | nicht erforderlich | frisch geprüft vor 30 Tagen (Intervall 45 Tage) | 2026-11-22 |
| `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 25 Tagen (Intervall 30 Tage) | 2026-11-12 |
| `2026-10-09-7-gewohnheiten-fuer-finanzielle-freiheit` | standard | nicht erforderlich | frisch geprüft vor 25 Tagen (Intervall 90 Tage) | 2027-01-11 |
| `2026-10-12-stromfresser-im-haushalt-entlarven` | standard | nicht erforderlich | frisch geprüft vor 25 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` | standard | nicht erforderlich | frisch geprüft vor 23 Tagen (Intervall 30 Tage) | 2026-11-14 |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 18 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet` | standard | nicht erforderlich | frisch geprüft vor 18 Tagen (Intervall 90 Tage) | 2027-01-18 |
| `2026-10-19-urlaubskasse-clever-aufbessern` | standard | nicht erforderlich | frisch geprüft vor 18 Tagen (Intervall 30 Tage) | 2026-11-19 |
| `2026-10-21-mietwagen-fallen-im-urlaub-vermeiden` | standard | nicht erforderlich | frisch geprüft vor 16 Tagen (Intervall 30 Tage) | 2026-11-21 |
| `2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen` | standard | nicht erforderlich | frisch geprüft vor 9 Tagen (Intervall 45 Tage) | 2026-12-13 |
| `2026-10-26-gastarife-vergleichen-vor-dem-herbst` | standard | nicht erforderlich | frisch geprüft vor 9 Tagen (Intervall 30 Tage) | 2026-11-28 |
| `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-30-gaspreiserhoehung-sonderkuendigungsrecht-raus-aus-dem` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` | erhoeht | nicht erforderlich | frisch geprüft vor 7 Tagen (Intervall 45 Tage) | 2026-12-15 |
| `2026-11-01-energieeffiziente-geraete-so-sinken-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | 2026-12-16 |
| `2026-11-02-last-minute-urlaubsangebote-sichern` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` | standard | nicht erforderlich | frisch geprüft vor 2 Tagen (Intervall 30 Tage) | 2026-12-05 |
| `2026-11-05-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 30 Tage) | 2026-11-29 |
| `2026-11-05-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` | standard | nicht erforderlich | frisch geprüft vor 2 Tagen (Intervall 45 Tage) | 2026-12-20 |
| `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 30 Tage) | 2026-12-07 |

## Ausnahmen (Falsch-Alarm-Protokoll)

Keine aktiven Ausnahmen – alle Checks wirken unverändert.

---
_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer Beweis ist niemals „bestanden“._
