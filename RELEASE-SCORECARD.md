# Release-Scorecard – die Produktionswahrheit

**Stand:** 2026-11-03 · **Modus:** kandidaten · **Engine:** `scripts/release_scorecard.py` · **SSOT:** `data/release_scorecard.yaml`

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
| ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ➖ nicht erforderlich | ✅ bestanden |

## Live-Bestand (Artikel für Artikel)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-10-dsl-wechselbonus-sichern` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **blockiert** |
| `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **freigabe-reif** |
| `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | ⚠️ warnung | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **blockiert** |
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | ❌ blockiert | ✅ bestanden | ❌ blockiert | ✅ bestanden | ❌ blockiert | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
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
| `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **freigabe-reif** |
| `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-13 | **warnung** |
| `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-18 | **freigabe-reif** |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-19 | **freigabe-reif** |
| `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-06 | **freigabe-reif** |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-23 | **freigabe-reif** |
| `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-07 | **freigabe-reif** |
| `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-05 | **freigabe-reif** |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-06 | **freigabe-reif** |
| `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **warnung** |
| `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-14 | **freigabe-reif** |
| `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **freigabe-reif** |
| `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-25 | **freigabe-reif** |

## Was blockiert – nach Prüfung, nicht nach Dimension

_Die Dimension sagt, wo es weh tut; der Check sagt, was zu tun ist. Besitz und Entscheidung stehen in `data/release_scorecard.yaml`._

| Check | Dimension | Wirkung | Entscheidet | Artikel |
|---|---|---|---|---|
| **F4-fachbefund** | faktenalter | blockiert | Mensch (Herausgeber/Redaktion) | 13 |
| **RD2-einzigartigkeit** | redundanz | blockiert | Mensch (Herausgeber/Redaktion) | 3 |
| **RD1-duplikate** | redundanz | blockiert | Maschine (deterministisch) | 2 |
| **T5-lesbarkeit** | technik | blockiert | Maschine (deterministisch) | 2 |
| **T1w-zeichenlaenge-optimum** | technik | warnung | Maschine (deterministisch) | 1 |

- **F4-fachbefund** – Schließweg: scripts/faktenfrische_befund_ledger.py (via publish_gate.fakten_befund_failures) · betroffen: `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas`, `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026`, `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden`, `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit`, `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub`, `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` …
- **RD2-einzigartigkeit** – Schließweg: scripts/check_uniqueness.py U1–U2 (via publish_gate.uniqueness_failures) · betroffen: `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas`, `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026`, `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen`

## Offene Fachbefunde (F4) – was die Redaktion entscheiden muss

**73** offene Befunde auf **17** Seiten (live: 53 auf 13 Artikeln) · ältester **4 Tage** · Frist 14 Tage · über der Frist: **0**.

**Ein Prüfdatum schließt keinen Fachbefund.** F1 (Alter) und F4 (Inhalt) sind getrennte Verträge; die Maschine entscheidet nie fachlich. Die Arbeitsdatei mit jeder Befund-ID, dem Fassungsstand und dem fertigen Entscheidungsbefehl ist `BEFUND-AKTE.md` (`python3 scripts/faktenfrische_befund_akte.py --schreiben`).

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

✅ **F1 (Faktenalter) ist nicht die Ursache:** Die Deckung trägt den Bestand; rot ist der Inhalt, nicht der Takt.

## Faktenfrische-Deckung (der Takt gegen den Bestand)

_Ein Faktenalter wird nicht „plötzlich“ rot: Es wird überfällig, weil der Bestand mehr Prüfungen braucht, als der Takt liefert. Diese Rechnung ist die Ursache der F1-Funde – nicht der F4-Funde._

| Kennzahl | Wert |
|---|---|
| Seiten im Bestand (Posts + Ratgeber) | 112 |
| Fällig heute / überfällig | 0 / 0 |
| Bedarf | 2,73 Prüfungen/Tag (19,1/Woche) |
| Angebot | 4,00/Tag (Budget 4 × 1,00 Läufe/Tag) |
| **Deckung** | **146 %** |
| Rückstand abgebaut | **nicht abbaubar** im Horizont |
| Nächste Frist | `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` am 2026-11-06 (in 3 Tagen) |
| Empfohlenes Budget | 4 je Lauf (Limit 10) |

✅ Deckung ausreichend: Der Takt kann den Bestand halten. Ein roter Faktenstand ist damit ein echter Inhaltsbefund (F4), kein Kadenz-Artefakt.

## Blockierende Funde (13 Artikel)

### `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 124ff2c3cd3917c274aa (praezision): Die Bewerbung des Vergleichsportals mit dem Superlativ 'Die besten Tarife' erfolgt ohne messbare Daten oder Auswahlkriterien in der Recherchegrundlage.; 7bdec96c0329769bebe6 (luecke): Die im Artikel als Fakten genannten Gaspreise für Oktober 2026 (11 bis 13 Cent/kWh) sind nicht durch die Fundstelle belegt, die lediglich eine allgemeine Themenübersicht darstellt.; a56734aa032e0ed9e0c4 (luecke): Der für den Verbraucherschutz zentrale Regulierungsrahmen (Sonderkündigungsrecht, Informationspflichten der Versorger) wird in der Fundstelle nicht inhaltlich bestätigt.
- **RD1-duplikate** [redundanz]: D4-X: Fast-Duplikat über Artikel (Ratio 0.86, content/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/index.md ≈ content/posts/2026-08-24-preisgarantie-gas-so-schu
- **RD2-einzigartigkeit** [redundanz]: U1-PHRASEN: 5 gleiche 7-Wort-Phrasen mit 2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026 (z. B. „bei weiterem verbrauch je nach fall grund“) – ab 5 ist es Dopplung, Passage umschreiben; U1-PHRASEN: 16 gleiche 7-Wort-Phrasen mit 2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen (z. B. „aenderung kuendigen der vertrag endet am vortag“) – ab 5 ist es Dopplung, Passage umschreiben

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 30caa57be394afb62947 (luecke): Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg.; 32a3ea879f2cf126b3a7 (luecke): Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist.; c583efe1ce02df3ca2d7 (luecke): Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt.
- **RD2-einzigartigkeit** [redundanz]: U1-PHRASEN: 5 gleiche 7-Wort-Phrasen mit 2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas (z. B. „bei weiterem verbrauch je nach fall grund“) – ab 5 ist es Dopplung, Passage umschreiben
- **T5-lesbarkeit** [technik]: Flesch 57.8 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 437b809ffbf41e5af434 (luecke): Keine Quelle für die Aussage, dass das Gesetz bei einem Tarifwechsel die Grundversorgung garantiert – regulatorischer Rahmen fehlt.; 9fbacd9942c2dfa1447f (luecke): Keine Quelle für die Behauptung, dass ein Grad weniger Raumtemperatur rund 6 % Energie einspart – Prozent‑Angabe fehlt.; da30cbb5fbc8c801daf0 (luecke): Keine Quelle für die Angabe, dass durch Optimierungsmaßnahmen 10‑15 % Einsparungen realistisch sind – Prozent‑Wert unbelegt.; db8a69f08dc0020adebd (luecke): Keine Quelle für die Aussage, dass im Oktober 2026 bessere Gaspreise gelten – Preis‑Trend‑Behauptung fehlt.; e834f4702e87194affe7 (luecke): Keine Quelle für die Angabe, dass ein Einfamilienhaus typischerweise 18.000 kWh/Jahr verbraucht – Verbrauchszahl ist unbelegt.

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 47f855cb4f0fe1e5c65f (luecke): Angaben zu möglichen Einsparungen beim Kfz‑Versicherungswechsel (150 €‑400 € bzw. 180 €‑350 €) sind ohne Quellenangabe; keine der genannten Zahlen findet sich in den bereitgestellten Statistiken.; 6b0aa3429d97e8c74ed8 (luecke): Die Behauptung, technische Maßnahmen beim Heizen senken den Energieverbrauch um 8 %‑12 %, wird nicht belegt; die bereitgestellten Daten enthalten lediglich die allgemeine Preisentwicklung von Energie (+14,9 %).; 7f66ec82ee1a3f095b0c (praezision): Die Aussage, der Herbst sei die „lukrativste Spar‑Saison des Jahres“, ist nicht durch messbare Daten gestützt; ein Vergleich mit anderen Jahreszeiten fehlt.; 84c991c5d152b14a2675 (luecke): Gesamteinsparungen von 500 €‑1.300 € pro Haushalt werden als Modellrechnung präsentiert, jedoch ohne Kennzeichnung als Modell und ohne Quellenangabe.; a70e7adc97c58317ccc1 (luecke): Das angegebene Sparpotenzial von 50 €‑80 € durch saisonale Lebensmittel‑ und Vorratshaltung ist nicht mit einer Quelle untermauert.

### `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 0051151e6c46f4c2bdb3 (luecke): Der Artikel nennt eine Kautionshöhe von 900 € bis 2.500 €, ohne dass die Verbraucherzentrale diese Spanne angibt.; 0790f52160dfaa819917 (luecke): Die angegebene Ersparnis von 145 € bei einer einwöchigen Anmietung ist nicht durch Zahlen der Verbraucherzentrale gedeckt.; 53c3fde8e986e6560890 (luecke): Die Behauptung, dass Flughafen‑Mietstationen 15 %‑25 % teurer sind, wird von der Verbraucherzentrale nicht bestätigt.; 89adecebaae75c147402 (luecke): Die Aussage, dass eine „Zero‑Excess“-Option die Kaution komplett auf 0 € senkt und dafür 5 €‑12 € pro Tag kostet, wird von der Verbraucherzentrale nicht belegt.; a1a269b73a1b9c2dfc88 (luecke): Der Hinweis, dass eine Vollkasko ohne Selbstbeteiligung nur 3 €‑8 € pro Tag mehr kostet, fehlt in den Angaben der Verbraucherzentrale.

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 252413dcc16cea146beb (luecke): Der Artikel behauptet, dass eine Preisänderung meist einen Monat vorher angekündigt werden muss, ohne dafür eine Quelle anzugeben.; 48a0a962046c8315270e (praezision): Die Behauptung, dass eine Preisgarantie einen Teil des Risikos auf den Anbieter überträgt und dafür ein höherer Startpreis üblich ist, fehlt eine konkrete Quelle und bleibt vage.; 9326152f4d788cff56bd (praezision): Die Aussage, dass man „in der Regel“ zum Zeitpunkt der Preisänderung Sonderkündigungsrecht hat, ist unpräzise und wird nicht durch eine konkrete Regelung belegt.; ab4d084fd367c8e4d518 (luecke): Der angegebene durchschnittliche Gaspreis von 11,93 Cent/kWh für 2026 (laut BDEW) wird nicht durch eine Quelle belegt.; d215addd22dea72c44df (luecke): Die Angabe, dass die Verbraucherzentrale etwa 6 % weniger Heizenergie pro Grad niedrigerer Raumtemperatur nennt, fehlt eine Quellenangabe.
- **RD1-duplikate** [redundanz]: D4-X: Fast-Duplikat über Artikel (Ratio 0.86, content/posts/2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas/index.md ≈ content/posts/2026-08-24-preisgarantie-gas-so-schu
- **RD2-einzigartigkeit** [redundanz]: U1-PHRASEN: 16 gleiche 7-Wort-Phrasen mit 2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas (z. B. „aenderung kuendigen der vertrag endet am vortag“) – ab 5 ist es Dopplung, Passage umschreiben
- **T5-lesbarkeit** [technik]: Flesch 56.9 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 3f0a88ede9d44ee910cb (luecke): Es fehlt der Hinweis auf das offizielle Beschwerdeportal der Bundesnetzagentur, über das Verbraucher Probleme mit Anbietern direkt melden können.; 51e259fd2d8582e774f7 (luecke): Der Ratgeber versäumt es, bei der Tarifprüfung auf die behördlichen Schlichtungsverfahren hinzuweisen, die Verbrauchern bei Streitigkeiten mit Energieversorgern zur Verfügung stehen.; 55f8eeedc587cf0895ee (luecke): Der Artikel erwähnt keine behördlichen Informationsquellen wie das Verbraucher-Radar, das Transparenz über den Energiemarkt und Verbraucherschutzthemen bietet.

### `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 045ff990e44a7035e9a0 (luecke): Es fehlt der Hinweis auf die behördliche Anlaufstelle für Anfragen und Beschwerden im Bereich Energie, die über die rein zivilrechtliche Meldung beim Vermieter hinausgeht.; 8919c2d1145af782d17a (luecke): Der Ratgeber empfiehlt Tarifvergleiche und Mängelmeldungen, lässt aber den für den Energiemarkt relevanten Regulierungsrahmen für den Verbraucherschutz (Schlichtungsverfahren) unerwähnt.; c39938841291b1e9e140 (praezision): Die Markttransparenz und der Verbraucherschutz im Energiesektor werden durch das 'Verbraucher-Radar' der Bundesnetzagentur statistisch erfasst; dieser Kontext fehlt bei der Einordnung von Marktdaten.

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 0aa915539d57841e5014 (luecke): Die Aussage, dass die Verbraucherzentrale empfiehlt, Boni im ersten Vergleich auszublenden, fehlt eine Quellenangabe.; 5e1be48085014a836807 (luecke): Der angegebene BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird nicht belegt.; 6fdf31c3b68b6122bd0d (praezision): Die pauschale Formulierung, dass bei zentraler Heizung der Vermieter oder die Eigentümergemeinschaft den Anbieter wählt, ist zu ungenau und nicht belegt.; c27c182c615bd7ca3b78 (luecke): Der Artikel behauptet, dass laut Bundesnetzagentur Preisänderungen klar angekündigt und begründet sein müssen, liefert jedoch keinen Beleg dafür.; e1e40e9bbbdd109df86e (luecke): Es wird angegeben, dass bei einer Preisänderung in der Regel ein Sonderkündigungsrecht besteht, ohne dafür eine Quelle zu nennen.

### `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 334751e6f61ad0033fe4 (luecke): Die Angabe, dass ein Gaslieferantenwechsel bei 20.000 kWh im Januar 2026 im Schnitt etwa 360 € spart, fehlt jede Quellenangabe.; 36759a5efe5e8e5163d0 (luecke): Die Faustregel der Verbraucherzentrale, dass pro Grad weniger Raumtemperatur der Heizbedarf um etwa 6 % sinkt, wird ohne Quelle angegeben.; 942922d1afd7844618e9 (luecke): Die Rechnung „1 Cent pro kWh bei 18.000 kWh Jahresverbrauch ergibt rund 180 € im Jahr“ wird nicht belegt.; d41f0d5ce8798df0211b (praezision): Die Aussage „Die besten Tarife findest du über unseren Partner‑Vergleich“ ist ein Superlativ ohne messbare Daten oder Vergleichskriterien.; e139d0769faadd04392a (luecke): Der BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird ohne Quellenangabe genannt.

### `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 04e40219cb4ff593b415 (praezision): Die Angabe, dass Anbieter den Abschlag auf elf oder zwölf Raten verteilen, ist ohne Beleg ungenau, da die Ratenzahl vertraglich variieren kann.; 2d01dc2629ad9c81f569 (luecke): Die Aussage, dass die Grundversorgung fast immer der teuerste Tarif ist, wird nicht durch eine Quelle belegt.; 3fd64026f55df4965cc9 (luecke): Die Angabe, dass ein Grad weniger Raumtemperatur rund 6 % Heizenergie einspart, fehlt eine Quellenangabe.; 799c93c89a10fc3cf267 (luecke): Das Sonderkündigungsrecht bei Preiserhöhungen im Winter wird genannt, ohne regulatorische Grundlage zu nennen.; cd81b3d9001b04c0a4e1 (luecke): Die Behauptung, der Grundtarif der Stadtwerke sei ausschließlich eine Notversorgung und nie ein Bestpreis, ist unbelegt.

### `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 58f03a64adaaf8125959 (praezision): Während der Artikel vor hohen Kosten für Festmenüs warnt, liegt die Preissteigerung bei Nahrungsmitteln laut Destatis im Oktober 2026 bei lediglich +0,4 % und damit deutlich unter der allgemeinen Inflation.; a7f5f01ef15a38839a0d (praezision): Die Pauschale für 'Anreise und Mobilität' (10 % des Budgets) berücksichtigt nicht die überdurchschnittliche Preissteigerung bei Energie von +14,9 %, die Fahrtkosten im Vergleich zum Vorjahr massiv verteuern kann.; bcc2bdf06220d5097133 (luecke): Die Modellrechnung für das Weihnachtsbudget (600 €) lässt die aktuelle Teuerungsrate unberücksichtigt. Laut Statistischen Bundesamt liegt die Inflationsrate im Oktober 2026 bei +2,8 %, was als Referenzwert für die Budgetplanung zum Vorjahr fehlt.

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 089b89138417e63a3dcf (luecke): Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet.; 1158934e7a18c7b2099b (luecke): Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt.; 3716cfd3ab5aec6d774b (praezision): Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote.

## Warnungen ohne Blockade (2 Artikel)

- `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` – T1w-zeichenlaenge-optimum: Zeichenlänge ueber-optimum (18140 Zeichen, Optimum 12.000–18.000)
- `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` – T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (10306 Zeichen, Optimum 12.000–18.000)

## Entwürfe – was vor dem Livegang noch offen ist

| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |
|---|---|---|---|---|
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | hoch | vorhanden | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | hoch | vorhanden | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | hoch | vorhanden | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | hoch | vorhanden | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | hoch | vorhanden | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | hoch | vorhanden | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | standard | nicht erforderlich | frisch geprüft vor 37 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 32 Tagen (Intervall 45 Tage) | 2026-11-16 |
| `2026-10-05-die-50-30-20-regel-einfach-erklaert` | standard | nicht erforderlich | frisch geprüft vor 29 Tagen (Intervall 90 Tage) | 2027-01-03 |
| `2026-10-06-markt-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 26 Tagen (Intervall 90 Tage) | 2027-01-06 |
| `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` | standard | nicht erforderlich | frisch geprüft vor 26 Tagen (Intervall 45 Tage) | 2026-11-22 |
| `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 21 Tagen (Intervall 30 Tage) | 2026-11-12 |
| `2026-10-09-7-gewohnheiten-fuer-finanzielle-freiheit` | standard | nicht erforderlich | frisch geprüft vor 21 Tagen (Intervall 90 Tage) | 2027-01-11 |
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 28 Tagen (Intervall 45 Tage) | 2026-11-20 |
| `2026-10-12-stromfresser-im-haushalt-entlarven` | standard | nicht erforderlich | frisch geprüft vor 21 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` | standard | nicht erforderlich | frisch geprüft vor 19 Tagen (Intervall 30 Tage) | 2026-11-14 |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 14 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet` | standard | nicht erforderlich | frisch geprüft vor 14 Tagen (Intervall 90 Tage) | 2027-01-18 |
| `2026-10-19-urlaubskasse-clever-aufbessern` | standard | nicht erforderlich | frisch geprüft vor 14 Tagen (Intervall 30 Tage) | 2026-11-19 |
| `2026-10-21-mietwagen-fallen-im-urlaub-vermeiden` | standard | nicht erforderlich | frisch geprüft vor 12 Tagen (Intervall 30 Tage) | 2026-11-21 |
| `2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen` | standard | nicht erforderlich | frisch geprüft vor 5 Tagen (Intervall 45 Tage) | 2026-12-13 |
| `2026-10-26-gastarife-vergleichen-vor-dem-herbst` | standard | nicht erforderlich | frisch geprüft vor 5 Tagen (Intervall 30 Tage) | 2026-11-28 |
| `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 45 Tage) | 2026-12-12 |
| `2026-10-30-gaspreiserhoehung-sonderkuendigungsrecht-raus-aus-dem` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` | erhoeht | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 45 Tage) | 2026-12-15 |
| `2026-11-01-energieeffiziente-geraete-so-sinken-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-11-01-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | 2026-11-29 |
| `2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck` | standard | nicht erforderlich | frisch geprüft vor 2 Tagen (Intervall 45 Tage) | 2026-12-16 |
| `2026-11-01-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` | standard | nicht erforderlich | frisch geprüft vor 27 Tagen (Intervall 30 Tage) | 2026-11-06 |
| `2026-11-02-last-minute-urlaubsangebote-sichern` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 30 Tage) | 2026-12-03 |

## Ausnahmen (Falsch-Alarm-Protokoll)

Keine aktiven Ausnahmen – alle Checks wirken unverändert.

---
_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer Beweis ist niemals „bestanden“._
