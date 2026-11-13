# Release-Scorecard – die Produktionswahrheit

**Stand:** 2026-11-13 · **Modus:** live · **Engine:** `scripts/release_scorecard.py` · **SSOT:** `data/release_scorecard.yaml`

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
| ⚠️ warnung | ⚠️ warnung | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ➖ nicht erforderlich | ✅ bestanden |

## Heutige Live-Kandidaten (Deploy-Scope)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-11-12-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein` | ⚠️ warnung | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-24 | **warnung** |
| `2026-11-10-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **freigabe-reif** |

## Live-Bestand (Artikel für Artikel)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-10-dsl-wechselbonus-sichern` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-12-geld-abheben-im-ausland-gebuehren-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **freigabe-reif** |
| `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` | ⚠️ warnung | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **blockiert** |
| `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-17-abos-und-vertraege-stiller-posten-haushaltsplan` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-11-19 | **freigabe-reif** |
| `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-22 | **blockiert** |
| `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **freigabe-reif** |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **blockiert** |
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-01 | **blockiert** |
| `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **freigabe-reif** |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (hoch, freigegeben) | vorhanden | 2026-12-14 | **freigabe-reif** |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-07 | **blockiert** |
| `2026-08-28-lastschrift-und-dauerauftrag-abbuchungen-pruefen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-31-nachtstrom-tarife-wann-sich-ein-doppeltarifzaehler-noch-lohnt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-08-31-stoerung-beim-internetanbieter-so-sicherst-du-deine-rechte` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **freigabe-reif** |
| `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-19 | **blockiert** |
| `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-12 | **freigabe-reif** |
| `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-09-04-umzug-mit-internet-anschluss-und-rufnummer-mitnehmen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **blockiert** |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | ⚠️ warnung | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **freigabe-reif** |
| `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-21 | **blockiert** |
| `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **freigabe-reif** |
| `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-25 | **blockiert** |
| `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **blockiert** |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-02 | **freigabe-reif** |
| `2026-09-21-grundversorgung-strom-und-gas-was-sie-leistet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-23-einlagensicherung-wie-viel-guthaben-geschuetzt-ist` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-28-zaehlerstand-ablesen-und-melden-schaetzwerte-vermeiden` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-09-30-grosseinkauf-und-vorrat-wann-bevorraten-sich-rechnet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-11 | **freigabe-reif** |
| `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **blockiert** |
| `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **freigabe-reif** |
| `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-27 | **blockiert** |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **freigabe-reif** |
| `2026-10-05-bueroausstattung-steuerlich-clever-absetzen-so-vermeidest` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-12-27 | **freigabe-reif** |
| `2026-10-05-erster-eigener-haushalt-fixkosten-richtig-ordnen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-27 | **freigabe-reif** |
| `2026-10-07-7-gewohnheiten-fuer-finanzielle-freiheit` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **blockiert** |
| `2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-handyvertrag-kuendigen-raus-aus-der-kostenfalle-verlaengerung` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-07-urlaub-sparen-7-clevere-wege-deine-kasse-zu-fuellen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **freigabe-reif** |
| `2026-10-07-wie-smart-home-geraete-deine-stromrechnung-wirklich-druecken` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-09-balkonkraftwerk-foerderung-so-holst-du-dir-geld-zurueck` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-23 | **freigabe-reif** |
| `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-28 | **blockiert** |
| `2026-10-09-vpn-zuhause-schutzschild-oder-unnoetige-fixkosten-falle` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-07 | **freigabe-reif** |
| `2026-10-12-dein-weg-zu-geringeren-monatskosten-schritt-fuer-schritt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-01-05 | **freigabe-reif** |
| `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-28 | **blockiert** |
| `2026-10-12-haushaltskosten-reduzieren-so-gewinnst-du-die-kontrolle` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-28 | **blockiert** |
| `2026-10-12-waermepumpe-vs-gasheizung-2026-so-entscheidest-du-richtig` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-03 | **freigabe-reif** |
| `2026-10-23-stromkosten-senken-clevere-haushaltsgeraete-im-ueberblick` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-21 | **freigabe-reif** |
| `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` | ✅ bestanden | ✅ bestanden | ❌ blockiert | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-28 | **blockiert** |
| `2026-10-24-energieeffizienz-im-haushalt-5-schnelle-spartricks` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-20 | **freigabe-reif** |
| `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-21 | **warnung** |
| `2026-10-25-strategisch-sparen-so-kannst-du-deine-reisekasse-fuellen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **freigabe-reif** |
| `2026-10-27-frugalismus-familie-clever-sparen-ohne-verzicht` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-11 | **freigabe-reif** |
| `2026-10-28-flugvergleich-im-winter-so-findest-du-echte-billigfluege` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-25 | **freigabe-reif** |
| `2026-10-28-oekostrom-anbieter-wechseln-sicher-gruen-und-bezahlbar` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-12 | **freigabe-reif** |
| `2026-10-30-gaspreiserhoehung-sonderkuendigungsrecht-raus-aus-dem` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-14 | **freigabe-reif** |
| `2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck` | ✅ bestanden | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-16 | **warnung** |
| `2026-11-05-waschmaschine-beladen-weniger-kosten-bei-jedem-waschgang` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-20 | **freigabe-reif** |
| `2026-11-10-fenster-abdichten-so-stoppst-du-zugluft-an-alten-rahmen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-29 | **freigabe-reif** |
| `2026-11-10-wlan-frust-loesen-so-findest-du-den-besten-router-standort` | ✅ bestanden | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2027-02-07 | **warnung** |
| `2026-11-12-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein` | ⚠️ warnung | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-24 | **warnung** |

## Was blockiert – nach Prüfung, nicht nach Dimension

_Die Dimension sagt, wo es weh tut; der Check sagt, was zu tun ist. Besitz und Entscheidung stehen in `data/release_scorecard.yaml`._

| Check | Dimension | Wirkung | Entscheidet | Artikel |
|---|---|---|---|---|
| **F4-fachbefund** | faktenalter | blockiert | Mensch (Herausgeber/Redaktion) | 24 |
| **T1w-zeichenlaenge-optimum** | technik | warnung | Maschine (deterministisch) | 2 |

- **F4-fachbefund** – Schließweg: scripts/faktenfrische_befund_ledger.py (via publish_gate.fakten_befund_failures) · betroffen: `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas`, `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026`, `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit`, `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren`, `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden`, `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` …

## Offene Fachbefunde (F4) – was die Redaktion entscheiden muss

**155** offene Befunde auf **39** Seiten (live: 94 auf 24 Artikeln) · ältester **14 Tage** · Frist 14 Tage · über der Frist: **0**.

**Ein Prüfdatum schließt keinen Fachbefund.** F1 (Alter) und F4 (Inhalt) sind getrennte Verträge; die Maschine entscheidet nie fachlich. Die Arbeitsdatei mit jeder Befund-ID, dem Fassungsstand und dem fertigen Entscheidungsbefehl ist `BEFUND-AKTE.md` (`python3 scripts/faktenfrische_befund_akte.py --schreiben`).

```bash
python3 scripts/faktenfrische_befund_ledger.py --entscheiden <ID> --von "<Name>" --begruendung "<was geprüft/geändert wurde>"
```

⚠️ **96 Befunde** wurden an einem älteren Text erhoben; der Text wurde seither geändert. Entschieden wird der HEUTIGE Text – genau das macht `--entscheiden` fassungsgebunden.

✅ **F1 (Faktenalter) ist nicht die Ursache:** Die Deckung trägt den Bestand; rot ist der Inhalt, nicht der Takt.

## Faktenfrische-Deckung (der Takt gegen den Bestand)

_Ein Faktenalter wird nicht „plötzlich“ rot: Es wird überfällig, weil der Bestand mehr Prüfungen braucht, als der Takt liefert. Diese Rechnung ist die Ursache der F1-Funde – nicht der F4-Funde._

| Kennzahl | Wert |
|---|---|
| Seiten im Bestand (Posts + Ratgeber) | 132 |
| Fällig heute / überfällig | 1 / 0 |
| Bedarf | 3,20 Prüfungen/Tag (22,4/Woche) |
| Angebot | 5,00/Tag (Budget 5 × 1,00 Läufe/Tag) |
| **Deckung** | **156 %** |
| Rückstand abgebaut | in 0 Tagen (Frist 7 Tage) |
| Nächste Frist | `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` am 2026-11-19 (in 6 Tagen) |
| Empfohlenes Budget | 5 je Lauf (Limit 18) |
| Spitzentag (#1039) | ✅ mitgemessen (58 Bündeltage, kein Befund) |

✅ Deckung ausreichend: Der Takt kann den Bestand halten. Ein roter Faktenstand ist damit ein echter Inhaltsbefund (F4), kein Kadenz-Artefakt.

## Blockierende Funde (24 Artikel)

### `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 124ff2c3cd3917c274aa (praezision): Die Bewerbung des Vergleichsportals mit dem Superlativ 'Die besten Tarife' erfolgt ohne messbare Daten oder Auswahlkriterien in der Recherchegrundlage.; 7bdec96c0329769bebe6 (luecke): Die im Artikel als Fakten genannten Gaspreise für Oktober 2026 (11 bis 13 Cent/kWh) sind nicht durch die Fundstelle belegt, die lediglich eine allgemeine Themenübersicht darstellt.; a56734aa032e0ed9e0c4 (luecke): Der für den Verbraucherschutz zentrale Regulierungsrahmen (Sonderkündigungsrecht, Informationspflichten der Versorger) wird in der Fundstelle nicht inhaltlich bestätigt.

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 30caa57be394afb62947 (luecke): Für den angeführten BDEW-Durchschnittspreis von 11,93 Cent/kWh fehlt in den Recherche-Fundstellen ein entsprechender Beleg.; 32a3ea879f2cf126b3a7 (luecke): Der Artikel lässt den in der Quelle explizit genannten Regulierungsrahmen der 'Unternehmenspflichten' unerwähnt, der für den Schutz der Verbraucher beim Anbieterwechsel zentral ist.; c583efe1ce02df3ca2d7 (luecke): Die im Artikel genannte Ersparnis-Berechnung der Bundesnetzagentur für Januar 2026 (360 €) wird durch die allgemeine Übersichtsseite der Behörde nicht gestützt.

### `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 47f855cb4f0fe1e5c65f (luecke): Angaben zu möglichen Einsparungen beim Kfz‑Versicherungswechsel (150 €‑400 € bzw. 180 €‑350 €) sind ohne Quellenangabe; keine der genannten Zahlen findet sich in den bereitgestellten Statistiken.; 6b0aa3429d97e8c74ed8 (luecke): Die Behauptung, technische Maßnahmen beim Heizen senken den Energieverbrauch um 8 %‑12 %, wird nicht belegt; die bereitgestellten Daten enthalten lediglich die allgemeine Preisentwicklung von Energie (+14,9 %).; 7f66ec82ee1a3f095b0c (praezision): Die Aussage, der Herbst sei die „lukrativste Spar‑Saison des Jahres“, ist nicht durch messbare Daten gestützt; ein Vergleich mit anderen Jahreszeiten fehlt.; 84c991c5d152b14a2675 (luecke): Gesamteinsparungen von 500 €‑1.300 € pro Haushalt werden als Modellrechnung präsentiert, jedoch ohne Kennzeichnung als Modell und ohne Quellenangabe.; a70e7adc97c58317ccc1 (luecke): Das angegebene Sparpotenzial von 50 €‑80 € durch saisonale Lebensmittel‑ und Vorratshaltung ist nicht mit einer Quelle untermauert.

### `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 1dbeb2f8c51e78d11d49 (luecke): Behauptung, dass klassische Filialbanken jährlich 150 € bis 250 € an reinen Gebühren kosten, ist unbelegt.; 33e736ac6afe996b491a (luecke): Behauptung, dass Echtzeit‑Überweisungen bei kostenlosen Konten generell gebührenfrei sind, fehlt jede Quelle.; 96b7b7768d402884810c (luecke): Aussage, dass Einlagen bis 100.000 € durch die deutsche Einlagensicherung geschützt sind, wird nicht belegt.; a25bb6bbcb25ba8b0e22 (luecke): Angabe von Dispozinsen von 8 % bis 11 % ohne Quellenangabe.; f94f8ba1e4342e67e45a (luecke): Angabe, dass ein Kontowechsel 120 € bis 180 € im Jahr spart, fehlt jede Quelle.

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 43470330b3b48c9cee49 (luecke): Der Artikel empfiehlt, Kühl- und Gefriergeräte mindestens 24 Stunden, besser mehrere Tage zu messen, liefert jedoch keine Quelle für diese Messdauer.; 8ddc1025e45be176ad3a (luecke): Es wird kein regulatorischer Rahmen (z. B. Aufgaben der Bundesnetzagentur) genannt, obwohl das Thema Stromversorgung berührt wird; entsprechende Vorgaben fehlen im Text.; 95d6d2877620e5a056ce (luecke): Die Aussage, dass Verbraucherzentralen oder Bibliotheken Messgeräte verleihen, wird ohne Beleg gemacht.; ab16029999747466a638 (luecke): Die Berechnung mit einem Arbeitspreis von 0,37 €/kWh wird angegeben, ohne dass ein aktueller Preis‑ oder Marktwert belegt wird.; b057dee3603e09f494b5 (luecke): Das Amortisationsbeispiel (Kaufpreis 650 €, Amortisationszeit 10,3 Jahre) enthält keine Quelle für die zugrunde liegenden Annahmen oder Preise.

### `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 0051151e6c46f4c2bdb3 (luecke): Der Artikel nennt eine Kautionshöhe von 900 € bis 2.500 €, ohne dass die Verbraucherzentrale diese Spanne angibt.; 0790f52160dfaa819917 (luecke): Die angegebene Ersparnis von 145 € bei einer einwöchigen Anmietung ist nicht durch Zahlen der Verbraucherzentrale gedeckt.; 53c3fde8e986e6560890 (luecke): Die Behauptung, dass Flughafen‑Mietstationen 15 %‑25 % teurer sind, wird von der Verbraucherzentrale nicht bestätigt.; 89adecebaae75c147402 (luecke): Die Aussage, dass eine „Zero‑Excess“-Option die Kaution komplett auf 0 € senkt und dafür 5 €‑12 € pro Tag kostet, wird von der Verbraucherzentrale nicht belegt.; a1a269b73a1b9c2dfc88 (luecke): Der Hinweis, dass eine Vollkasko ohne Selbstbeteiligung nur 3 €‑8 € pro Tag mehr kostet, fehlt in den Angaben der Verbraucherzentrale.

### `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 3fe383f6d452737f66f2 (praezision): Die im Teaser und Text genannten monatlichen Ersparnisse von 350 € bis 600 € werden als Marktfakten ohne Quellenbeleg oder methodische Herleitung (z. B. Referenzhaushalt des Statistischen Bundesamtes) angeführt.; 7bba759bbb4ca14c7f35 (luecke): Der Ratgeber empfiehlt Tarifwechsel bei Energie zur Kostensenkung, verschweigt aber den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die Kalkulation der 50-Prozent-Fixkostenquote gefährdet.; e8e32a383b6f803cc8d4 (veraltet): Die Einschätzung zur Inflation ist unpräzise: Die aktuelle Inflationsrate liegt laut Destatis bei +2,8 % (Oktober 2026), wodurch die genannten Tagesgeldzinsen von 0,5 % bis 1,5 % den Wertverlust deutlich weniger ausgleichen als suggeriert.

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 252413dcc16cea146beb (luecke): Der Artikel behauptet, dass eine Preisänderung meist einen Monat vorher angekündigt werden muss, ohne dafür eine Quelle anzugeben.; 48a0a962046c8315270e (praezision): Die Behauptung, dass eine Preisgarantie einen Teil des Risikos auf den Anbieter überträgt und dafür ein höherer Startpreis üblich ist, fehlt eine konkrete Quelle und bleibt vage.; 9326152f4d788cff56bd (praezision): Die Aussage, dass man „in der Regel“ zum Zeitpunkt der Preisänderung Sonderkündigungsrecht hat, ist unpräzise und wird nicht durch eine konkrete Regelung belegt.; ab4d084fd367c8e4d518 (luecke): Der angegebene durchschnittliche Gaspreis von 11,93 Cent/kWh für 2026 (laut BDEW) wird nicht durch eine Quelle belegt.; d215addd22dea72c44df (luecke): Die Angabe, dass die Verbraucherzentrale etwa 6 % weniger Heizenergie pro Grad niedrigerer Raumtemperatur nennt, fehlt eine Quellenangabe.

### `2026-08-26-warmwasser-sparen-rechnung-hinter-dem-hahn` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 278d89267d9122a1e9d8 (luecke): Angaben zu gesetzlichen Vorgaben für Warmwassertemperaturen zur Vermeidung von Legionellen werden nicht durch die bereitgestellten Quellen gestützt.; 450c3aa629342062825e (luecke): Die Aussage, dass Warmwasser der zweitgrößte Kostenposten im Haushalt ist, wird nicht durch eine der bereitgestellten Quellen belegt.; 7601167c9f3560093fb0 (luecke): Die Behauptung, dass Warmwasser in der Heizkostenabrechnung üblicherweise als eigener Block ausgewiesen wird, fehlt eine Quellenangabe.; 7efbcd7a4275fe1577bb (luecke): Verweise auf die Verbraucherzentrale (Tipps zum Heizkosten sparen, Heizung optimieren) können nicht mit den angegebenen Fundstellen belegt werden.; 971a719f94ca492f640e (luecke): Der Preis von 0,30 € pro Kilowattstunde in der Modellrechnung ist nicht mit einer Quelle belegt.

### `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` (blockiert, Risikoklasse erhoeht)

- **F4-fachbefund** [faktenalter]: 16b3b8584ff802803aa9 (luecke): Angaben zum Fremdwährungsentgelt von „fast zwei Prozent“ bei Zahlungen in fremder Währung fehlen jede belegbare Referenz.; 7ff042b6fe804cdf101b (praezision): Formulierungen wie „einige Anbieter ohne Auslandsgebühr gehören zu den besten Karten für Reisen“ sind pauschal und ohne messbare Daten unpräzise.; bec83c4b814183fa1086 (luecke): Die Aussage, dass die kostenlose Sperr‑Notrufnummer 116 für alle Karten in Deutschland gilt, wird nicht durch eine Quelle gestützt.; f9aff86b6eba71b153a6 (luecke): Die Angabe, dass Sollzinsen bei Teilzahlung zwischen 12 % und 20 % liegen, ist nicht mit einer Quelle belegt.; fed9215b770ea4879eda (luecke): Die Behauptung, dass eine gute Kreditkarte im Jahr nichts kostet (keine Jahres‑ und keine Fremdwährungsgebühr), wird ohne jegliche Quelle angegeben.

### `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 20c08cb650ef6e24af64 (luecke): Der Ratgeber vernachlässigt bei der Kalkulation der Sparfähigkeit die massive Preissteigerung bei Energie (+14,9 %), die das Budget für monatliche Sparraten erheblich belastet.; 6aafb23c0c6dbb06ce3b (veraltet): Die im Rechenbeispiel zur Realrendite genutzte Inflationsrate von 2 % ist veraltet; die vorläufige Rate für Oktober 2026 beträgt laut Statistischem Bundesamt 2,8 %.

### `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 24f05ddc03ffdd50118f (praezision): Die Kalkulation der Fixkostenersparnis bei Energie (Strom/Gas) ist unpräzise, da sie den aktuellen Preisanstieg von +14,9 % bei Energieprodukten nicht einbezieht.; 4816322f061dfdc03bcd (luecke): Bei den Einsparpotenzialen für Lebensmittel fehlt der Bezug zur aktuellen Preissteigerung von +0,4 % bei Nahrungsmitteln.; 7017065ee7c74c7ae452 (veraltet): Der Artikel nutzt Kostenszenarien für 2024/2025, während aktuelle Daten für Oktober 2026 eine Inflationsrate von +2,8 % ausweisen.

### `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 1e06a96f6f71e104ce0b (praezision): Während Meal Prep als großer Sparhebel betont wird, zeigt die Marktlage für Nahrungsmittel eine moderate Teuerung von nur 0,4 %, was die Priorisierung der Sparbemühungen relativiert.; 81c6a707139046b83ccd (luecke): Der Ratgeber empfiehlt die Revision von Fixkosten, lässt aber die drastische Preissteigerung bei Energie von +14,9 % unerwähnt, die ein wesentlicher Treiber der Haushaltsausgaben ist.; 8cc00288af8a1f2b02d8 (veraltet): Die Budget-Tipps berücksichtigen nicht die aktuelle Inflationsrate von 2,8 % (Stand Oktober 2026), was die Kaufkraft-Annahmen im Haushaltsbuch beeinflusst.

### `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 5a1bf10697f58e5fe14a (luecke): Der Ratgeber nennt Sparbeispiele für Heizkosten, lässt aber die aktuelle Preissteigerung bei Energie von +14,9 % (Stand Oktober 2026) unerwähnt, die den finanziellen Druck auf Haushalte massiv erhöht.; e48f9237cff6397c49a6 (praezision): Die in Aussicht gestellten Ersparnisse von bis zu 200 € werden nicht ins Verhältnis zur aktuellen Inflationsrate von +2,8 % gesetzt, welche die reale Kaufkraft des gesparten Geldes mindert.; f6de6b078d49f9d42e0e (praezision): Beim Fokus auf Lebensmittelplanung fehlt der Hinweis auf die vergleichsweise moderate Preissteigerung von +0,4 % bei Nahrungsmitteln, was diesen Hebel gegenüber den stark steigenden Energiekosten relativiert.

### `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 6cb2229c5eb83b02da23 (veraltet): Die Kalkulation der Fixkosten (Energie 140 €) und die Empfehlung zur Senkung der Kosten ignorieren den aktuellen Markttrend massiv steigender Energiepreise (+14,9 %), was die 50-Prozent-Quote für notwendige Ausgaben gefährdet.; f00055a1cb65ee22165f (luecke): Der Ratgeber verspricht eine 'planbare' Budgetierung, lässt aber die aktuelle Inflationsrate von 2,8 % unerwähnt, die insbesondere den Block der notwendigen Ausgaben (Nahrungsmittel +0,4 %) dynamisch belastet.

### `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 7a87eaaa2b863ba8cc46 (luecke): Ein relevanter regulatorischer Rahmen (z. B. Vorgaben der Bundesnetzagentur oder BDEW) wird nicht genannt, obwohl die Fundstelle darauf hinweist, dass solche Vorgaben existieren.; 9d67a5e6bd11212c7c1e (praezision): Die Aussage, dass bestimmte Gerätegruppen (TV‑Ecke, Homeoffice, alte Audio‑Technik) zuerst zu senken „lohnt“, wird ohne messbare Daten oder Vergleichskriterien gemacht.; a54abc1cad73d20fb689 (luecke): Die konkreten Jahreskosten (z. B. 32 € für 10 W Standby) beruhen auf dem nicht belegten Strompreis und werden nicht als Modellrechnung gekennzeichnet.; a7d1cf6485921e117919 (luecke): Der angegebene durchschnittliche Strompreis von 37,3 Cent/kWh (BDEW‑Schnitt) wird ohne Quellenangabe genannt.; a7f69a854430d62a4a3e (luecke): Die Empfehlung, dass ein günstigerer Arbeitspreis der zweite wichtigste Hebel sei, fehlt jede Quelle oder regulatorische Einordnung.

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 0aa915539d57841e5014 (luecke): Die Aussage, dass die Verbraucherzentrale empfiehlt, Boni im ersten Vergleich auszublenden, fehlt eine Quellenangabe.; 5e1be48085014a836807 (luecke): Der angegebene BDEW‑Durchschnittspreis von 11,93 Cent/kWh für 2026 wird nicht belegt.; 6fdf31c3b68b6122bd0d (praezision): Die pauschale Formulierung, dass bei zentraler Heizung der Vermieter oder die Eigentümergemeinschaft den Anbieter wählt, ist zu ungenau und nicht belegt.; c27c182c615bd7ca3b78 (luecke): Der Artikel behauptet, dass laut Bundesnetzagentur Preisänderungen klar angekündigt und begründet sein müssen, liefert jedoch keinen Beleg dafür.; e1e40e9bbbdd109df86e (luecke): Es wird angegeben, dass bei einer Preisänderung in der Regel ein Sonderkündigungsrecht besteht, ohne dafür eine Quelle zu nennen.

### `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 33278b9e7942ebfdbbac (luecke): Definition des Begriffs „Last Minute“ (maximal 14 Tage zwischen Buchung und Abreise) wird mit dem Deutschen Reiseverband angegeben, jedoch fehlt ein Nachweis.; 6ad7358a9afcfef3babb (praezision): Angabe, dass Preisalarme keinen Tiefstpreis garantieren, wird nicht durch konkrete Zahlen oder Vergleichsstudien belegt.; 7c375a3e1a9bfab1468c (luecke): Hinweis auf § 651r BGB (Insolvenzsicherung bei Pauschalreisen) enthält keinen Verweis auf eine Rechtsquelle oder Verbraucherzentrale‑Information.; ea11d36614fa115503b4 (luecke): Behauptung, dass Nachlässe von bis zu 50 % nur Einzelfälle sind, wird ohne Quellenangabe präsentiert.; f7b1c869dd8e442eaf16 (praezision): Aussage, dass der „beste Zeitpunkt zum Buchen“ ein Modellwert sei, bleibt vage und ohne messbare Daten oder Studien untermauert.

### `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 6b5921bdc76490587167 (luecke): Seit 2026 nutzen die großen Anbieter die Technik mit dem Namen Vectoring; das ist ein Modellwert. Sie senkt das Rauschen auf der Leitung. In der Stadt sind damit bis zu 250 Mbps stabil drin.; 8436b91bdb63a6316979 (praezision): Preisgarantie über mindestens 12 Monate; ohne Garantie darf der Anbieter bald erhöhen, oft um bis zu 10 %.; a4ff01e649b789f19e6a (luecke): Für 50 Mbps zahlst du heute meist ca. 20–40 € im Monat; das ist ein Beispielwert.

### `2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 089b89138417e63a3dcf (luecke): Es fehlt der für Campingbuchungen relevante Regulierungsrahmen (Unterscheidung Mietrecht bei Stellplätzen vs. Reiserecht), den die Fundstelle für den Bereich Reise nur allgemein andeutet.; 1158934e7a18c7b2099b (luecke): Die Preisangabe von 20 bis 45 € pro Nacht wird als realistischer Wert positioniert, ist jedoch nicht durch Marktdaten oder eine Referenzstelle in den Fundstellen belegt.; 3716cfd3ab5aec6d774b (praezision): Der Verweis auf die Verbraucherzentrale zur Prüfung von Buchungsangaben führt auf eine allgemeine Übersichtsseite ohne konkrete Checklisten für Camping-Angebote.

### `2026-10-09-energiekosten-senken-smarte-helfer-fuer-den-haushalt` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 4d0125136c5b940946e4 (luecke): Lichtsteuerung: Bedarfssteuerung – 2 bis 5 % des Stromverbrauchs.; 7aeb2098034d16a46885 (luecke): Anbieter locken mit Neukundenboni, die nach der üblichen Erstlaufzeit entfallen; danach steigt der Arbeitspreis massiv an.; ea97b5dd6695de127fd2 (luecke): Heizungssteuerung: Smarte Thermostate können Heizkosten einsparen. Die Spanne von 10 bis 25 % ist ein Beispielwert aus der Rechnung unten.

### `2026-10-12-energieausweis-was-das-dokument-fuer-deine-fixkosten` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 1dc0f20f9ab3a6b783bc (luecke): Behauptung, dass ein fehlender Ausweis zu empfindlichen Bußgeldern führt, fehlt eine belegbare Quelle.; 7b94ca07b36c0b7cb1cc (luecke): Aussage, dass Baudenkmäler von der Ausweispflicht befreit sind, wird nicht durch die angegebene Quelle gestützt.; 985f506ee04087bf7253 (luecke): Angabe, dass ein Wechsel von Energieeffizienzklasse F zu C über 2.000 € Jahresersparnis bringt, ist unbelegt.; ee321fa37210590f7e9b (luecke): Keine Quelle für die Angabe, dass ein Energieausweis ein volles Jahrzehnt gültig ist, sofern keine größeren Umbauten erfolgen.

### `2026-10-12-kleine-energiespar-tricks-die-deine-kosten-sofort-senken` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 19ab248b17415c73edfb (luecke): Thermostat um 1 °C senken | 4 % – 6 % der Heizkosten; 372bb51051e8bd7c5f71 (luecke): Viele Anbieter belohnen einen niedrigen Verbrauch mit besseren Konditionen; 6aaff85e3a7591d0c5b2 (luecke): für dich entstehen keine Mehrkosten; 7e6087a4117a857a92c8 (luecke): Durch diese zwei Maßnahmen sparst du in dieser Beispielrechnung jährlich rund 140 €; e28b4ad1f6d608d2ec77 (luecke): Strom (LED‑Umrüstung) | 100 € – 140 € | etwa 8 %

### `2026-10-24-bankgebuehren-senken-7-schritte-zum-guenstigeren-konto` (blockiert, Risikoklasse standard)

- **F4-fachbefund** [faktenalter]: 04ae33652c1c5eb4e2b8 (luecke): Ein kurzer Check spart dir oft mehrere hundert Euro im Jahr.; 5223a3c7287ff81939cd (luecke): Faustregel: ... mehr als 5 % deines Nettoeinkommens ... Meist sinken diese Kosten um über 80 %; 9800545ae945ec280b34 (luecke): Ein Wechsel ist für dich in der Regel komplett kostenlos als Beispielwert.; bc0e4f2eb357a682c674 (luecke): Bei einem normalen Einkommen sollten die Gebühren fast Null sein.

## Warnungen ohne Blockade (4 Artikel)

- `2026-10-24-etf-sparplan-starten-schritt-fuer-schritt-zum-monatlichen` – T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (10252 Zeichen, Optimum 12.000–18.000)
- `2026-11-01-flugverspaetung-entschaedigung-so-holst-du-dein-geld-zurueck` – Q2-quellen-vorhanden: keine Belegkette im Frontmatter (quellen) – nachpflegen (faktenfrische)
- `2026-11-10-wlan-frust-loesen-so-findest-du-den-besten-router-standort` – Q2-quellen-vorhanden: keine Belegkette im Frontmatter (quellen) – nachpflegen (faktenfrische)
- `2026-11-12-wie-viel-streaming-bandbreite-du-wirklich-brauchst-dein` – Q2-quellen-vorhanden: keine Belegkette im Frontmatter (quellen) – nachpflegen (faktenfrische); T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (10788 Zeichen, Optimum 12.000–18.000)

## Entwürfe – was vor dem Livegang noch offen ist

| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |
|---|---|---|---|---|
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 14 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | hoch | vorhanden | frisch geprüft vor 14 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | hoch | vorhanden | frisch geprüft vor 14 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | hoch | vorhanden | frisch geprüft vor 14 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | hoch | vorhanden | frisch geprüft vor 14 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | standard | nicht erforderlich | frisch geprüft vor 7 Tagen (Intervall 45 Tage) | 2026-12-21 |
| `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 2 Tagen (Intervall 45 Tage) | 2026-12-26 |
| `2026-10-05-die-50-30-20-regel-einfach-erklaert` | standard | nicht erforderlich | frisch geprüft vor 39 Tagen (Intervall 90 Tage) | 2027-01-03 |
| `2026-10-06-markt-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 36 Tagen (Intervall 90 Tage) | 2027-01-06 |
| `2026-10-07-notgroschen-aufbauen-wie-viel-reicht-wirklich` | standard | nicht erforderlich | frisch geprüft vor 36 Tagen (Intervall 45 Tage) | 2026-11-22 |
| `2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 30 Tage) | 2026-12-10 |
| `2026-10-09-7-gewohnheiten-fuer-finanzielle-freiheit` | standard | nicht erforderlich | frisch geprüft vor 31 Tagen (Intervall 90 Tage) | 2027-01-11 |
| `2026-10-12-stromfresser-im-haushalt-entlarven` | standard | nicht erforderlich | frisch geprüft vor 31 Tagen (Intervall 45 Tage) | 2026-11-27 |
| `2026-10-14-heizperiode-vorbereiten-im-spaetsommer` | standard | nicht erforderlich | frisch geprüft vor 2 Tagen (Intervall 30 Tage) | 2026-12-11 |
| `2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert` | hoch | vorhanden | frisch geprüft vor 24 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-10-16-dns-server-aendern-fuer-schnelleres-internet` | standard | nicht erforderlich | frisch geprüft vor 24 Tagen (Intervall 90 Tage) | 2027-01-18 |
| `2026-10-19-urlaubskasse-clever-aufbessern` | standard | nicht erforderlich | frisch geprüft vor 1 Tagen (Intervall 30 Tage) | 2026-12-12 |
| `2026-10-21-mietwagen-fallen-im-urlaub-vermeiden` | standard | nicht erforderlich | frisch geprüft vor 22 Tagen (Intervall 30 Tage) | 2026-11-21 |
| `2026-10-23-stromanbieter-wechseln-und-bis-zu-300-euro-sparen` | standard | nicht erforderlich | frisch geprüft vor 15 Tagen (Intervall 45 Tage) | 2026-12-13 |
| `2026-10-26-gastarife-vergleichen-vor-dem-herbst` | standard | nicht erforderlich | frisch geprüft vor 15 Tagen (Intervall 30 Tage) | 2026-11-28 |
| `2026-10-28-dsl-und-internet-flat-guenstig-sichern` | standard | nicht erforderlich | frisch geprüft vor 14 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-10-30-kostenloses-girokonto-ohne-gebuehren-finden` | erhoeht | nicht erforderlich | frisch geprüft vor 13 Tagen (Intervall 45 Tage) | 2026-12-15 |
| `2026-11-01-energieeffiziente-geraete-so-sinken-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 14 Tagen (Intervall 45 Tage) | 2026-12-14 |
| `2026-11-02-last-minute-urlaubsangebote-sichern` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-04-guenstigen-mietwagen-fuer-den-urlaub-buchen` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 30 Tage) | 2026-12-05 |
| `2026-11-06-guenstige-fluege-fuer-den-spaetsommer-finden` | standard | nicht erforderlich | frisch geprüft vor 6 Tagen (Intervall 30 Tage) | 2026-12-07 |
| `2026-11-09-handytarife-vergleichen-so-findest-du-den-guenstigsten-tarif` | erhoeht | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 45 Tage) | 2026-12-25 |
| `2026-11-09-reisekasse-fuellen-7-wege-zu-mehr-budget-fuer-den-urlaub` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | 2026-12-09 |
| `2026-11-09-wlan-verbessern-mesh-system-oder-repeater-im-check` | standard | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 45 Tage) | 2026-12-25 |
| `2026-11-10-kaffeemaschine-stromverbrauch-was-kostet-die-tasse-kaffee` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | 2026-12-24 |
| `2026-11-11-kreditkarte-ohne-jahresgebuehr-die-besten-kostenlosen-karten` | erhoeht | nicht erforderlich | frisch geprüft vor 1 Tagen (Intervall 45 Tage) | 2026-12-27 |
| `2026-11-13-deine-naechtliche-grundlast-strom-so-erkennst-du-wo` | standard | nicht erforderlich | frisch geprüft vor 1 Tagen (Intervall 45 Tage) | 2026-12-27 |
| `2026-11-13-gas-anbieter-wechseln-strategien-gegen-hohe-heizkosten` | erhoeht | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | 2026-12-09 |
| `2026-11-13-geschenkkarte-was-du-beim-kauf-und-aufladen-wissen-musst` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 45 Tage) | 2026-12-28 |
| `2026-11-13-geschirrspueler-voll-so-sparst-du-wasser-und-strom` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | 2026-12-24 |
| `2026-11-13-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu` | standard | nicht erforderlich | frisch geprüft vor 10 Tagen (Intervall 30 Tage) | 2026-12-03 |
| `2026-11-13-mehrwegflaschen-pfand-so-optimierst-du-deine-fixkosten` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 45 Tage) | 2026-12-24 |
| `2026-11-13-mesh-wlan-nachruesten-schluss-mit-funkloechern-in-der-wohnung` | standard | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 90 Tage) | 2027-02-08 |
| `2026-11-13-secondhand-kleidung-so-erkennst-du-qualitaet-sparst` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 90 Tage) | 2027-02-11 |
| `2026-11-13-strompreis-2026-herbst-check-fuer-deine-stromkosten` | standard | nicht erforderlich | frisch geprüft vor 4 Tagen (Intervall 30 Tage) | 2026-12-09 |
| `2026-11-13-tagesgeld-und-zinsen-so-parkst-du-dein-geld-sicher` | erhoeht | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-11-13-weniger-spontankaeufe-dein-essensplan-woche-ohne-reste` | standard | nicht erforderlich | frisch geprüft vor 0 Tagen (Intervall 45 Tage) | 2026-12-28 |

## Ausnahmen (Falsch-Alarm-Protokoll)

Keine aktiven Ausnahmen – alle Checks wirken unverändert.

---
_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer Beweis ist niemals „bestanden“._
