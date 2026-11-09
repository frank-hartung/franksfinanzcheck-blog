# Release-Scorecard – die Produktionswahrheit

**Stand:** 2026-11-09 · **Modus:** live · **Engine:** `scripts/release_scorecard.py` · **SSOT:** `data/release_scorecard.yaml`

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
| ❌ blockiert | ⚠️ warnung | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ➖ nicht erforderlich | ✅ bestanden |

## Heutige Live-Kandidaten (Deploy-Scope)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-10-30-gaspreiserhoehung-sonderkuendigungsrecht-raus-aus-dem` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-14 | **freigabe-reif** |
| `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` | ✅ bestanden | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **warnung** |

## Live-Bestand (Artikel für Artikel)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-10-dsl-wechselbonus-sichern` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **freigabe-reif** |
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **blockiert** |
| `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-11-19 | **freigabe-reif** |
| `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-22 | **blockiert** |
| `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **blockiert** |
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **freigabe-reif** |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **blockiert** |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (erhöht) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-07 | **freigabe-reif** |
| `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **freigabe-reif** |
| `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **freigabe-reif** |
| `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **freigabe-reif** |
| `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **freigabe-reif** |
| `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **freigabe-reif** |
| `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **blockiert** |
| `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-13 | **blockiert** |
| `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **freigabe-reif** |
| `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-18 | **freigabe-reif** |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-19 | **freigabe-reif** |
| `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-23 | **freigabe-reif** |
| `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **blockiert** |
| `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-07 | **freigabe-reif** |
| `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-05 | **freigabe-reif** |
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **freigabe-reif** |
| `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **warnung** |
| `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-14 | **freigabe-reif** |
| `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **freigabe-reif** |
| `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-25 | **freigabe-reif** |
| `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-12 | **freigabe-reif** |
| `2026-10-30-gaspreiserhoehung-sonderkuendigungsrecht-raus-aus-dem` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-14 | **freigabe-reif** |
| `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` | ✅ bestanden | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **warnung** |

## Was blockiert – nach Prüfung, nicht nach Dimension

_Die Dimension sagt, wo es weh tut; der Check sagt, was zu tun ist. Besitz und Entscheidung stehen in `data/release_scorecard.yaml`._

| Check | Dimension | Wirkung | Entscheidet | Artikel |
|---|---|---|---|---|
| **T6-textverstaendnis** | technik | blockiert | Maschine (deterministisch) | 20 |
| **F4-fachbefund** | faktenalter | blockiert | Mensch (Herausgeber/Redaktion) | 19 |
| **RD1-duplikate** | redundanz | blockiert | Maschine (deterministisch) | 18 |
| **T1w-zeichenlaenge-optimum** | technik | warnung | Maschine (deterministisch) | 5 |
| **T2-seo-audit** | technik | blockiert | Maschine (deterministisch) | 1 |
| **T5-lesbarkeit** | technik | blockiert | Maschine (deterministisch) | 1 |

- **F4-fachbefund** – Schließweg: scripts/faktenfrische_befund_ledger.py (via publish_gate.fakten_befund_failures) · betroffen: `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026`, `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden`, `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit`, `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren`, `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden`, `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` …

## Offene Fachbefunde (F4) – was die Redaktion entscheiden muss

**117** offene Befunde auf **28** Seiten (live: 77 auf 19 Artikeln) · ältester **10 Tage** · Frist 14 Tage · über der Frist: **0**.

**Ein Prüfdatum schließt keinen Fachbefund.** F1 (Alter) und F4 (Inhalt) sind getrennte Verträge; die Maschine entscheidet nie fachlich. Die Arbeitsdatei mit jeder Befund-ID, dem Fassungsstand und dem fertigen Entscheidungsbefehl ist `BEFUND-AKTE.md` (`python3 scripts/faktenfrische_befund_akte.py --schreiben`).

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

⚠️ **92 Befunde** wurden an einem älteren Text erhoben; der Text wurde seither geändert. Entschieden wird der HEUTIGE Text – genau das macht `--entscheiden` fassungsgebunden.

✅ **F1 (Faktenalter) ist nicht die Ursache:** Die Deckung trägt den Bestand; rot ist der Inhalt, nicht der Takt.

## Faktenfrische-Deckung (der Takt gegen den Bestand)

_Ein Faktenalter wird nicht „plötzlich“ rot: Es wird überfällig, weil der Bestand mehr Prüfungen braucht, als der Takt liefert. Diese Rechnung ist die Ursache der F1-Funde – nicht der F4-Funde._

| Kennzahl | Wert |
|---|---|
| Seiten im Bestand (Posts + Ratgeber) | 125 |
| Fällig heute / überfällig | 4 / 0 |
| Bedarf | 3,06 Prüfungen/Tag (21,4/Woche) |
| Angebot | 4,00/Tag (Budget 4 × 1,00 Läufe/Tag) |
| **Deckung** | **131 %** |
| Rückstand abgebaut | in 0 Tagen (Frist 7 Tage) |
| Nächste Frist | `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` am 2026-11-12 (in 3 Tagen) |
| Empfohlenes Budget | 4 je Lauf (Limit 16) |
| Spitzentag (#1039) | ✅ mitgemessen (58 Bündeltage, kein Befund) |

✅ Deckung ausreichend: Der Takt kann den Bestand halten. Ein roter Faktenstand ist damit ein echter Inhaltsbefund (F4), kein Kadenz-Artefakt.

## Blockierende Funde (30 Artikel)

### `2026-08-10-dsl-wechselbonus-sichern` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1305 ≈ Z.1059): *Abbildung: Merkkarte zu „DSL-Wechselbonus sichern: So sparst du beim Internetvertrag“ (eigene Darst…; D1-EXAKT: Absatz doppelt (Z.9100 ≈ Z.8765): *Abbildung: Gliederung zu „DSL-Wechselbonus sichern: So sparst du beim Internetvertrag“ – 5 Statione…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu DSL-Wechselbo“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: DSL-Wechselbonu“)

### `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1126 ≈ Z.880): *Abbildung: Merkkarte zu „Geld abheben im Ausland: Wo die Gebühren wirklich entstehen“ (eigene Darst…; D1-EXAKT: Absatz doppelt (Z.8758 ≈ Z.8454): *Abbildung: Gliederung zu „Geld abheben im Ausland: Wo die Gebühren wirklich entstehen“ – 5 Statione…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Geld abheben “); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Geld abheben im“)

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 30caa57be394afb62947 (luecke): Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg.; 32a3ea879f2cf126b3a7 (luecke): Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist.; c583efe1ce02df3ca2d7 (luecke): Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt.

### `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 437b809ffbf41e5af434 (luecke): Keine Quelle für die Aussage, dass das Gesetz bei einem Tarifwechsel die Grundversorgung garantiert – regulatorischer Rahmen fehlt.; 9fbacd9942c2dfa1447f (luecke): Keine Quelle für die Behauptung, dass ein Grad weniger Raumtemperatur rund 6 % Energie einspart – Prozent‑Angabe fehlt.; da30cbb5fbc8c801daf0 (luecke): Keine Quelle für die Angabe, dass durch Optimierungsmaßnahmen 10‑15 % Einsparungen realistisch sind – Prozent‑Wert unbelegt.; db8a69f08dc0020adebd (luecke): Keine Quelle für die Aussage, dass im Oktober 2026 bessere Gaspreise gelten – Preis‑Trend‑Behauptung fehlt.; e834f4702e87194affe7 (luecke): Keine Quelle für die Angabe, dass ein Einfamilienhaus typischerweise 18.000 kWh/Jahr verbraucht – Verbrauchszahl ist unbelegt.
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Gasrechnung s“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Gasrechnung sen“)

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 47f855cb4f0fe1e5c65f (luecke): Angaben zu möglichen Einsparungen beim Kfz‑Versicherungswechsel (150 €‑400 € bzw. 180 €‑350 €) sind ohne Quellenangabe; keine der genannten Zahlen findet sich in den bereitgestellten Statistiken.; 6b0aa3429d97e8c74ed8 (luecke): Die Behauptung, technische Maßnahmen beim Heizen senken den Energieverbrauch um 8 %‑12 %, wird nicht belegt; die bereitgestellten Daten enthalten lediglich die allgemeine Preisentwicklung von Energie (+14,9 %).; 7f66ec82ee1a3f095b0c (praezision): Die Aussage, der Herbst sei die „lukrativste Spar‑Saison des Jahres“, ist nicht durch messbare Daten gestützt; ein Vergleich mit anderen Jahreszeiten fehlt.; 84c991c5d152b14a2675 (luecke): Gesamteinsparungen von 500 €‑1.300 € pro Haushalt werden als Modellrechnung präsentiert, jedoch ohne Kennzeichnung als Modell und ohne Quellenangabe.; a70e7adc97c58317ccc1 (luecke): Das angegebene Sparpotenzial von 50 €‑80 € durch saisonale Lebensmittel‑ und Vorratshaltung ist nicht mit einer Quelle untermauert.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.2265 ≈ Z.2029): *Abbildung: Merkkarte zu „Sparen im Herbst: Spartipps für die goldene Jahreszeit“ (eigene Darstellun…; D1-EXAKT: Absatz doppelt (Z.14799 ≈ Z.14481): *Abbildung: Gliederung zu „Sparen im Herbst: Spartipps für die goldene Jahreszeit“ – 5 Stationen von…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Sparen im Her“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Sparen im Herbs“)

### `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.9273 ≈ Z.8946): *Abbildung: Gliederung zu „WLAN verbessern: So bringst du stabilen Speed in jede Ecke“ – 5 Stationen…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu WLAN verbesse“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: WLAN verbessern“)

### `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 1dbeb2f8c51e78d11d49 (luecke): Behauptung, dass klassische Filialbanken jährlich 150 € bis 250 € an reinen Gebühren kosten, ist unbelegt.; 33e736ac6afe996b491a (luecke): Behauptung, dass Echtzeit‑Überweisungen bei kostenlosen Konten generell gebührenfrei sind, fehlt jede Quelle.; 96b7b7768d402884810c (luecke): Aussage, dass Einlagen bis 100.000 € durch die deutsche Einlagensicherung geschützt sind, wird nicht belegt.; a25bb6bbcb25ba8b0e22 (luecke): Angabe von Dispozinsen von 8 % bis 11 % ohne Quellenangabe.; f94f8ba1e4342e67e45a (luecke): Angabe, dass ein Kontowechsel 120 € bis 180 € im Jahr spart, fehlt jede Quelle.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1408 ≈ Z.1174): *Abbildung: Merkkarte zu „Kostenloses Girokonto: Ein Konto ohne Gebühren finden“ (eigene Darstellung…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Kostenloses G“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Kostenloses Gir“)

### `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.9825 ≈ Z.9488): *Abbildung: Gliederung zu „DSL-Vergleich: So findest du den günstigsten Internettarif“ – 5 Stationen…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu DSL-Vergleich“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: DSL-Vergleich: “)

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 43470330b3b48c9cee49 (luecke): Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer.; 8ddc1025e45be176ad3a (luecke): Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text.; 95d6d2877620e5a056ce (luecke): Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht.; ab16029999747466a638 (luecke): Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird.; b057dee3603e09f494b5 (luecke): Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1060 ≈ Z.824): *Abbildung: Merkkarte zu „Energiediebe stoppen: So kannst du Stromfresser finden“ (eigene Darstellun…; D1-EXAKT: Absatz doppelt (Z.9971 ≈ Z.9648): *Abbildung: Gliederung zu „Energiediebe stoppen: So kannst du Stromfresser finden“ – 5 Stationen von…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Energiediebe “); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Energiediebe st“)

### `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1937 ≈ Z.1699): *Abbildung: Merkkarte zu „DSL-Tarif für dein Zuhause: Das passende Angebot finden“ (eigene Darstellu…; D1-EXAKT: Absatz doppelt (Z.9496 ≈ Z.9150): *Abbildung: Gliederung zu „DSL-Tarif für dein Zuhause: Das passende Angebot finden“ – 5 Stationen vo…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu DSL-Tarif für“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: DSL-Tarif für d“)

### `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 4afb8daed73677ee6224 (luecke): Angabe, dass 58 % der Nutzer ihr Haushaltsbuch digital führen, beruft sich angeblich auf Statista 2025, jedoch wird keine Quelle genannt.; 9eb9a90899cc8ca66020 (luecke): Sparpotenzial‑Beispiele (z. B. DSL‑Tarifwechsel von 44 € auf 24 €) enthalten konkrete Zahlen ohne Quellenangabe.; b4bd085bc84a6131b644 (luecke): Behauptung, dass 60 % der Haushalte in Deutschland ihr Geld nicht nachverfolgen, wird mit einer Auswertung der Stiftung Warentest angegeben, jedoch fehlt ein entsprechender Nachweis.; baed76dc211bd15dd46f (praezision): Versprechen, dass ein Haushaltsbuch „schnell“ zeigt, welche Posten sich lohnen, ist nicht quantifiziert und fehlt an konkreten Evidenzangaben.; d7c3cfb422310cf26ca6 (praezision): Die Aussage, dass die 50‑30‑20‑Regel für ein Nettoeinkommen von 2.500 € realistisch sei, wird ohne Hinweis auf regionale Unterschiede oder empirische Daten präsentiert.

### `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 0051151e6c46f4c2bdb3 (luecke): Der Artikel nennt eine Kautionshöhe von 900 € bis 2.500 €, ohne dass die Verbraucherzentrale diese Spanne angibt.; 0790f52160dfaa819917 (luecke): Die angegebene Ersparnis von 145 € bei einer einwöchigen Anmietung ist nicht durch Zahlen der Verbraucherzentrale gedeckt.; 53c3fde8e986e6560890 (luecke): Die Behauptung, dass Flughafen‑Mietstationen 15 %‑25 % teurer sind, wird von der Verbraucherzentrale nicht bestätigt.; 89adecebaae75c147402 (luecke): Die Aussage, dass eine „Zero‑Excess“-Option die Kaution komplett auf 0 € senkt und dafür 5 €‑12 € pro Tag kostet, wird von der Verbraucherzentrale nicht belegt.; a1a269b73a1b9c2dfc88 (luecke): Der Hinweis, dass eine Vollkasko ohne Selbstbeteiligung nur 3 €‑8 € pro Tag mehr kostet, fehlt in den Angaben der Verbraucherzentrale.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1339 ≈ Z.1105): *Abbildung: Merkkarte zu „Mietwagen ohne Kautionsfallen: So sparst du im Urlaub“ (eigene Darstellung…; D1-EXAKT: Absatz doppelt (Z.10678 ≈ Z.10348): *Abbildung: Gliederung zu „Mietwagen ohne Kautionsfallen: So sparst du im Urlaub“ – 5 Stationen von …
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Mietwagen ohn“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Mietwagen ohne “)

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 252413dcc16cea146beb (luecke): Der Artikel behauptet, dass eine Preisänderung meist einen Monat vorher angekündigt werden muss, ohne dafür eine Quelle anzugeben.; 48a0a962046c8315270e (praezision): Die Behauptung, dass eine Preisgarantie einen Teil des Risikos auf den Anbieter überträgt und dafür ein höherer Startpreis üblich ist, fehlt eine konkrete Quelle und bleibt vage.; 9326152f4d788cff56bd (praezision): Die Aussage, dass man „in der Regel“ zum Zeitpunkt der Preisänderung Sonderkündigungsrecht hat, ist unpräzise und wird nicht durch eine konkrete Regelung belegt.; ab4d084fd367c8e4d518 (luecke): Der angegebene durchschnittliche Gaspreis von 11,93 Cent/kWh für 2026 (laut BDEW) wird nicht durch eine Quelle belegt.; d215addd22dea72c44df (luecke): Die Angabe, dass die Verbraucherzentrale etwa 6 % weniger Heizenergie pro Grad niedrigerer Raumtemperatur nennt, fehlt eine Quellenangabe.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.7474 ≈ Z.7163): *Abbildung: Gliederung zu „Preisgarantie Gas: Was bei Preiserhöhung hilft“ – 5 Stationen von „Wenn e…
- **T5-lesbarkeit** [technik]: Flesch 59.7 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Preisgarantie“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Preisgarantie G“)

### `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1151 ≈ Z.911): *Abbildung: Merkkarte zu „DNS-Server wechseln: Datenschutz, Filter und Einrichtung“ (eigene Darstell…; D1-EXAKT: Absatz doppelt (Z.10834 ≈ Z.10525): *Abbildung: Gliederung zu „DNS-Server wechseln: Datenschutz, Filter und Einrichtung“ – 5 Stationen v…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu DNS-Server we“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: DNS-Server wech“)

### `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` (blockiert, Risikoklasse erhoeht)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1200 ≈ Z.960): *Abbildung: Merkkarte zu „Tagesgeld-Zinsen 2026: Die besten Zinssätze im Vergleich“ (eigene Darstell…; D1-EXAKT: Absatz doppelt (Z.9457 ≈ Z.9144): *Abbildung: Gliederung zu „Tagesgeld-Zinsen 2026: Die besten Zinssätze im Vergleich“ – 5 Stationen v…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Tagesgeld-Zin“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Tagesgeld-Zinse“)

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 16b3b8584ff802803aa9 (luecke): Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Referenz.; 7ff042b6fe804cdf101b (praezision): Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und ohne messbare Daten unpräzise.; bec83c4b814183fa1086 (luecke): Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Quelle gestützt.; f9aff86b6eba71b153a6 (luecke): Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt.; fed9215b770ea4879eda (luecke): Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird ohne jegliche Quelle angegeben.

### `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 20c08cb650ef6e24af64 (luecke): Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet.; 6aafb23c0c6dbb06ce3b (veraltet): Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.10395 ≈ Z.10038): *Abbildung: Gliederung zu „Finanzielle Freiheit erreichen: Denke dich reich – Geld“ – 5 Stationen vo…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Finanzielle F“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Finanzielle Fre“)

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 24f05ddc03ffdd50118f (praezision): Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht.; 4816322f061dfdc03bcd (luecke): Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln.; 7017065ee7c74c7ae452 (veraltet): Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen.

### `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 1e06a96f6f71e104ce0b (praezision): Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von nur 0,4 %, was die Priorisierung der Sparbemühungen relativiert.; 81c6a707139046b83ccd (luecke): Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 % unerwähnt, die ein wesentlicher Treiber der Haushaltsausgaben ist.; 8cc00288af8a1f2b02d8 (veraltet): Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-Annahmen im Haushaltsbuch beeinflusst.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.10243 ≈ Z.9070): *Abbildung: Gliederung zu „Alltagsfehler vermeiden: 5 Frugalismus-Tipps im Überblick“ – 5 Stationen …
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Alltagsfehler“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Alltagsfehler v“)

### `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1982 ≈ Z.1746): *Abbildung: Merkkarte zu „Notgroschen: Die Wahrheit über das finanzielle Polster“ (eigene Darstellun…; D1-EXAKT: Absatz doppelt (Z.8701 ≈ Z.8379): *Abbildung: Gliederung zu „Notgroschen: Die Wahrheit über das finanzielle Polster“ – 5 Stationen von…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Notgroschen: “); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Notgroschen: Di“)

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 5a1bf10697f58e5fe14a (luecke): Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Stand Oktober 2026) unerwähnt, die den finanziellen Druck auf Haushalte massiv erhöht.; e48f9237cff6397c49a6 (praezision): Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von +2,8 % gesetzt, welche die reale Kaufkraft des gesparten Geldes mindert.; f6de6b078d49f9d42e0e (praezision): Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei Nahrungsmitteln, was diesen Hebel gegenüber den stark steigenden Energiekosten relativiert.

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 6cb2229c5eb83b02da23 (veraltet): Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet.; f00055a1cb65ee22165f (luecke): Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.1611 ≈ Z.1369): *Abbildung: Merkkarte zu „50-30-20-Regel: Beherrsche dein Budget – Fixkosten senken“ (eigene Darstel…; D1-EXAKT: Absatz doppelt (Z.10983 ≈ Z.9525): *Abbildung: Gliederung zu „50-30-20-Regel: Beherrsche dein Budget – Fixkosten senken“ – 5 Stationen …
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu 50-30-20-Rege“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: 50-30-20-Regel:“)

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 0aa915539d57841e5014 (luecke): Die Aussage, dass die Verbraucherzentrale empfiehlt, Boni im ersten Vergleich auszublenden, fehlt eine Quellenangabe.; 5e1be48085014a836807 (luecke): Der angegebene BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird nicht belegt.; 6fdf31c3b68b6122bd0d (praezision): Die pauschale Formulierung, dass bei zentraler Heizung der Vermieter oder die Eigentümergemeinschaft den Anbieter wählt, ist zu ungenau und nicht belegt.; c27c182c615bd7ca3b78 (luecke): Der Artikel behauptet, dass laut Bundesnetzagentur Preisänderungen klar angekündigt und begründet sein müssen, liefert jedoch keinen Beleg dafür.; e1e40e9bbbdd109df86e (luecke): Es wird angegeben, dass bei einer Preisänderung in der Regel ein Sonderkündigungsrecht besteht, ohne dafür eine Quelle zu nennen.

### `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 334751e6f61ad0033fe4 (luecke): Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quellenangabe.; 36759a5efe5e8e5163d0 (luecke): Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird ohne Quelle angegeben.; 942922d1afd7844618e9 (luecke): Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt.; d41f0d5ce8798df0211b (praezision): Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder Vergleichskriterien.; e139d0769faadd04392a (luecke): Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt.

### `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` (blockiert, Risikoklasse standard)

- **T2-seo-audit** [technik]: harte SEO-Mängel (score_issues > 0, seo_audit.py)

### `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` (blockiert, Risikoklasse standard)

- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Last Minute U“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Last Minute Url“)

### `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 58f03a64adaaf8125959 (praezision): Während der Artikel vor hohen Kosten für Festmenüs warnt, liegt die Preissteigerung bei Nahrungsmitteln laut Destatis im Oktober 2026 bei lediglich +0,4 % und damit deutlich unter der allgemeinen Inflation.; a7f5f01ef15a38839a0d (praezision): Die Pauschale für 'Anreise und Mobilität' (10 % des Budgets) berücksichtigt nicht die überdurchschnittliche Preissteigerung bei Energie von +14,9 %, die Fahrtkosten im Vergleich zum Vorjahr massiv verteuern kann.; bcc2bdf06220d5097133 (luecke): Die Modellrechnung für das Weihnachtsbudget (600 €) lässt die aktuelle Teuerungsrate unberücksichtigt. Laut Statistischen Bundesamt liegt die Inflationsrate im Oktober 2026 bei +2,8 %, was als Referenzwert für die Budgetplanung zum Vorjahr fehlt.

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 089b89138417e63a3dcf (luecke): Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet.; 1158934e7a18c7b2099b (luecke): Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt.; 3716cfd3ab5aec6d774b (praezision): Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote.
- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.973 ≈ Z.749): *Abbildung: Merkkarte zu „Campingurlaub planen: Budget für Platz und Fahrt“ (eigene Darstellung aus …
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Campingurlaub“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Campingurlaub p“)

### `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 7067eabb89a917ae67a4 (luecke): Die Verbraucherzentrale sammelt Hinweise zu Reisebuchungen, auch zu unklaren Angeboten und Problemen mit Online-Buchungen.; af2ccb4222eeb195222f (praezision): Ein Mietwagenvergleich kann Angebote sichtbar machen, prüft aber nicht automatisch, ob das Auto zum individuellen Urlaub passt – ohne Messgröße bleibt die Aussage ungenau.; d9c8b522bf1dcaed0340 (luecke): Die Verbraucherzentrale beschreibt, dass sich eine Pauschalreise unter bestimmten Bedingungen auf eine andere Person übertragen lässt.; e2975509f3f130de0755 (luecke): Die Verbraucherzentrale empfiehlt, größere Ausgaben vorauszuplanen und das eigene Budget im Blick zu behalten.; f1704e45e970a8f4b078 (luecke): Bei einer Pauschalreise gilt die Mitteilung als rechtzeitig, wenn sie dem Veranstalter spätestens sieben Tage vor Reisebeginn zugeht (§ 651e BGB).

### `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` (blockiert, Risikoklasse standard)

- **RD1-duplikate** [redundanz]: D1-EXAKT: Absatz doppelt (Z.2016 ≈ Z.1784): *Abbildung: Merkkarte zu „Energiekosten senken: Smarte Helfer für den Haushalt“ (eigene Darstellung …; D1-EXAKT: Absatz doppelt (Z.9382 ≈ Z.9027): *Abbildung: Gliederung zu „Energiekosten senken: Smarte Helfer für den Haushalt“ – 5 Stationen von „…
- **T6-textverstaendnis** [technik]: R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-merkkarte. svg“ (Anker: „Merkkarte: Kernaussagen zu Energiekosten“); R8-URL-LEERZEICHEN: URL mit Leerzeichen: „abbildung-ablauf. svg“ (Anker: „Gliederung des Beitrags: Energiekosten s“)

## Warnungen ohne Blockade (2 Artikel)

- `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` – T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (10252 Zeichen, Optimum 12.000–18.000)
- `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` – Q2-quellen-vorhanden: keine Belegkette im Frontmatter (quellen) – nachpflegen (faktenfrische)

## Entwürfe – was vor dem Livegang noch offen ist

| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |
|---|---|---|---|---|
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 10 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | hoch | vorhanden | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | hoch | vorhanden | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | hoch | vorhanden | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | hoch | vorhanden | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | standard | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 45 Tage) | 2026-12-21 |
| `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 38 Tagen (Intervall 45 Tage) | 2026-11-16 |
| `2026-10-05-die-50-30-20-regel-einfach-erklaert` | standard | nicht erforderlich | frisch geprüft vor 35 Tagen (Intervall 90 Tage) | 2027-01-03 |
| `2026-10-06-markt-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 32 Tagen (Intervall 90 Tage) | 2027-01-06 |
| `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` | standard | nicht erforderlich | frisch geprüft vor 32 Tagen (Intervall 45 Tage) | 2026-11-22 |
| `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 27 Tagen (Intervall 30 Tage) | 2026-11-12 |
| `2026-10-09-7-gewohnheiten-fuer-finanzielle-freiheit` | standard | nicht erforderlich | frisch geprüft vor 27 Tagen (Intervall 90 Tage) | 2027-01-11 |
| `2026-10-12-stromfresser-im-haushalt-entlarven` | standard | nicht erforderlich | frisch geprüft vor 27 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` | standard | nicht erforderlich | frisch geprüft vor 25 Tagen (Intervall 30 Tage) | 2026-11-14 |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 20 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet` | standard | nicht erforderlich | frisch geprüft vor 20 Tagen (Intervall 90 Tage) | 2027-01-18 |
| `2026-10-19-urlaubskasse-clever-aufbessern` | standard | nicht erforderlich | frisch geprüft vor 20 Tagen (Intervall 30 Tage) | 2026-11-19 |
| `2026-10-21-mietwagen-fallen-im-urlaub-vermeiden` | standard | nicht erforderlich | frisch geprüft vor 18 Tagen (Intervall 30 Tage) | 2026-11-21 |
| `2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen` | standard | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 45 Tage) | 2026-12-13 |
| `2026-10-26-gastarife-vergleichen-vor-dem-herbst` | standard | nicht erforderlich | frisch geprüft vor 11 Tagen (Intervall 30 Tage) | 2026-11-28 |
| `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` | erhoeht | nicht erforderlich | frisch geprüft vor 9 Tagen (Intervall 45 Tage) | 2026-12-15 |
| `2026-11-01-energieeffiziente-geraete-so-sinken-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-12-16 |
| `2026-11-02-last-minute-urlaubsangebote-sichern` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | 2026-12-05 |
| `2026-11-05-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 30 Tage) | 2026-11-29 |
| `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` | standard | nicht erforderlich | frisch geprüft vor 2 Tagen (Intervall 30 Tage) | 2026-12-07 |
| `2026-11-09-gas-anbieter-wechseln-strategien-gegen-hohe-heizkosten` | erhoeht | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 30 Tage) | 2026-12-09 |
| `2026-11-09-geschirrspueler-voll-so-sparst-du-wasser-und-strom` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 45 Tage) | 2026-12-24 |
| `2026-11-09-handytarife-vergleichen-so-findest-du-den-guenstigsten-tarif` | erhoeht | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-09-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-09-kaffeemaschine-stromverbrauch-was-kostet-die-tasse-kaffee` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 45 Tage) | 2026-12-24 |
| `2026-11-09-mehrwegflaschen-pfand-so-optimierst-du-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 45 Tage) | 2026-12-24 |
| `2026-11-09-reisekasse-fuellen-7-wege-zu-mehr-budget-fuer-den-urlaub` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 30 Tage) | 2026-12-09 |
| `2026-11-09-strompreis-2026-herbst-check-fuer-deine-stromkosten` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 30 Tage) | 2026-12-09 |
| `2026-11-09-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-09-wlan-frust-loesen-so-findest-du-den-besten-router-standort` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-09-wlan-verbessern-mesh-system-oder-repeater-im-check` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |

## Ausnahmen (Falsch-Alarm-Protokoll)

Keine aktiven Ausnahmen – alle Checks wirken unverändert.

---
_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer Beweis ist niemals „bestanden“._
