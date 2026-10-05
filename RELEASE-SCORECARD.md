# Release-Scorecard – die Produktionswahrheit

**Stand:** 2026-10-05 · **Modus:** kandidaten · **Engine:** `scripts/release_scorecard.py` · **SSOT:** `data/release_scorecard.yaml`

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
| ❌ blockiert | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ➖ nicht erforderlich | ✅ bestanden |

## Live-Bestand (Artikel für Artikel)

| Artikel | Technik | Quellen | Faktenalter | Affiliate-Integrität | Redundanz | YMYL-Risiko | menschliche Freigabe | nächste Überprüfung | Urteil |
|---|---|---|---|---|---|---|---|---|---|
| `2026-08-10-dsl-wechselbonus-sichern` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **blockiert** |
| `2026-08-10-sicher-heizen-so-schuetzt-dich-eine-preisgarantie-gas` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **freigabe-reif** |
| `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **blockiert** |
| `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **blockiert** |
| `2026-08-14-internet-dsl-wechseln-praxis-tipps-fuer-den-anbieterwechsel` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-14-sparen-im-herbst-die-besten-spartipps-fuer-die-goldene-jahreszeit` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-27 | **freigabe-reif** |
| `2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-11 | **warnung** |
| `2026-08-19-dsl-vergleich-so-findest-du-guenstigeres-internet` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **blockiert** |
| `2026-08-20-so-findest-du-den-richtigen-dsl-tarif-fuer-dein-zuhause` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-21-haushaltsbuch-fuehren-app-excel-oder-papier` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-21-mietwagen-buchen-ohne-kaution-fallen-urlaub` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-27 | **freigabe-reif** |
| `2026-08-24-mehr-freiheit-durch-verzicht-clevere-frugalismus-tipps` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **blockiert** |
| `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **blockiert** |
| `2026-08-26-handytarif-vergleichen-2026-guenstige-tarife` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-11 | **blockiert** |
| `2026-09-02-september-roadtrip-clevere-wege-zum-mietwagen-schnaeppchen` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **freigabe-reif** |
| `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (erhöht) | nicht erforderlich | 2026-11-11 | **warnung** |
| `2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **freigabe-reif** |
| `2026-09-04-finanzielle-freiheit-erreichen-denke-dich-reich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-07-frugalismus-tipps-mehr-freiheit-durch-bewussten-konsum` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-07-frugalismus-tipps-so-vermeidest-du-teure-alltagsfehler` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **blockiert** |
| `2026-09-09-notgroschen-die-wahrheit-ueber-das-finanzielle-polster` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-11-5-einfache-frugalismus-tricks-fuer-den-alltag` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-11-50-30-20-regel-beherrsche-dein-budget-im-jahr-2026` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **blockiert** |
| `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-12 | **blockiert** |
| `2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-11 | **freigabe-reif** |
| `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **blockiert** |
| `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` | ❌ blockiert | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-10-28 | **blockiert** |
| `2026-09-27-wlan-verstaerker-vs-mesh-wlan-was-brauchst-du-wirklich` | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-12-26 | **freigabe-reif** |
| `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-01 | **warnung** |
| `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` | ⚠️ warnung | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-03 | **warnung** |
| `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` | ⚠️ warnung | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-18 | **warnung** |
| `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` | ⚠️ warnung | ⚠️ warnung | ✅ bestanden | ✅ bestanden | ✅ bestanden | geprüft (kein Hochrisiko) | nicht erforderlich | 2026-11-03 | **warnung** |

## Blockierende Funde (12 Artikel)

### `2026-08-10-dsl-wechselbonus-sichern` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 55.4 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-08-12-preisgarantie-gas-so-sicherst-du-dir-guenstige-tarife-fuer-2026` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 57.6 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-08-14-gasrechnung-senken-fehler-im-spaetsommer-vermeiden` (blockiert, Risikoklasse standard)

- **T6-textverstaendnis** [technik]: R10-DOPPELWORT: Verdopplung mit Quantor-Einschub „senken um bis zu 15 % senken“ ⟦…ichtigen Vorgehen lässt sich die gasrechnung senken um bis zu 15 % senken.…⟧ – Klebe-Rest, Quantor gehört vor das Verb

### `2026-08-19-energiediebe-stoppen-so-kannst-du-stromfresser-finden` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 56.4 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-08-24-preisgarantie-gas-so-schuetzt-du-dich-vor-preisspruengen` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 55.8 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet` (blockiert, Risikoklasse standard)

- **T6-textverstaendnis** [technik]: R3-TERMINOLOGIE: Konzept „DNS-Server“: 5 Synonym-Vorkommen (Resolver×3, Namensauflösung×2) – Leitbegriff verwenden

### `2026-08-26-tagesgeld-zinsen-2026-die-besten-zinssaetze-im-vergleich` (blockiert, Risikoklasse erhoeht)

- **T6-textverstaendnis** [technik]: R3-TERMINOLOGIE: Konzept „Tagesgeldkonto“: 9 Synonym-Vorkommen (Tagesgeld×9) – Leitbegriff verwenden

### `2026-09-07-heizkosten-senken-mit-diesen-strategien-sparst-du-sofort` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 55.8 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-09-11-guenstig-durch-den-winter-heizungs-check-im-spaetsommer` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 55.8 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-09-11-standby-kosten-reduzieren-so-entlarvst-du-stromfresser` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 55.4 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-09-20-gasrechnung-senken-so-bereitest-du-dich-im-spaetsommer-vor` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 56.7 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

### `2026-09-20-gasrechnung-senken-spaetsommer-check-spart-hunderte-euro` (blockiert, Risikoklasse standard)

- **T5-lesbarkeit** [technik]: Flesch 57.4 (Mindestwert 60) – ein Artikel unter dieser Schwelle zieht den Bestands-Durchschnitt nach unten (#585)

## Warnungen ohne Blockade (6 Artikel)

- `2026-08-17-kostenloses-girokonto-so-findest-du-ein-konto-ohne-gebuehren` – T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (11718 Zeichen, Optimum 12.000–18.000)
- `2026-09-03-kreditkarte-vergleichen-kostenlos-sicher-bezahlen` – T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (11888 Zeichen, Optimum 12.000–18.000)
- `2026-09-30-last-minute-urlaub-so-schnappst-du-dir-das-sommer-schnaepp` – T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (11420 Zeichen, Optimum 12.000–18.000)
- `2026-10-02-gasabschlag-berechnen-so-planst-du-die-heizsaison-richtig` – Q2-quellen-vorhanden: keine Belegkette im Frontmatter (quellen) – nachpflegen (faktenfrische); T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (10269 Zeichen, Optimum 12.000–18.000)
- `2026-10-02-preiswert-surfen-so-findest-du-den-optimalen-dsl-anschluss` – Q2-quellen-vorhanden: keine Belegkette im Frontmatter (quellen) – nachpflegen (faktenfrische); T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (11118 Zeichen, Optimum 12.000–18.000)
- `2026-10-02-weihnachten-budget-planen-ohne-schulden-durch-die-feiertage` – Q2-quellen-vorhanden: keine Belegkette im Frontmatter (quellen) – nachpflegen (faktenfrische); T1w-zeichenlaenge-optimum: Zeichenlänge unter-optimum (11577 Zeichen, Optimum 12.000–18.000)

## Entwürfe – was vor dem Livegang noch offen ist

| Artikel | Risikoklasse | Freigabe | Faktenstand | Nächste Prüfung |
|---|---|---|---|---|
| `2026-08-12-dein-haus-sicher-schuetzen-das-neue-vorsorge-update-2026` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-08-17-privathaftpflicht-warum-sie-so-wichtig-ist-und-was-sie-kostet` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-08-18-geld-sparen-im-alltag-einfache-tipps-die-jeder-umsetzen-kann` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-08-18-wohngebaeudeversicherung-vergleich-worauf-du-achten-musst` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-08-26-kfz-versicherung-vergleich-bis-zu-800-euro-sparen` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 30 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-10-energie-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-09-17-versicherung-update-was-sich-jetzt-fuer-dich-aendert` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-7-gewohnheiten-fuer-finanzielle-freiheit` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-09-21-ratenkredit-vergleich-zinsen-kosten-fallen` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-tierkrankenversicherung-hund-katze-kosten` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-unfallversicherung-vergleich-sinnvoll-kosten` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-21-zahnzusatzversicherung-kosten-leistungen-vergleich` | hoch | ausstehend | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | unbekannt ⚠️ überfällig |
| `2026-09-22-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-09-23-5-einfache-frugalismus-tricks-fuer-den-alltag` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-09-24-internet-dsl-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 8 Tagen (Intervall 45 Tage) | 2026-11-11 |
| `2026-09-29-konto-karten-update-was-sich-jetzt-fuer-dich-aendert` | standard | nicht erforderlich | frisch geprüft vor 3 Tagen (Intervall 45 Tage) | 2026-11-16 |
| `2026-10-05-bankgebuehren-sparen-so-halbierst-du-deine-kosten` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-05-budget-app-2026-so-beherrschst-du-deine-ausgaben-ohne-auf` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-05-die-50-30-20-regel-einfach-erklaert` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-05-digital-banking-vorteile-moderner-online-konten-nutzen` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-05-dns-server-aendern-schnelleres-internet-ohne-mehrkosten` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-05-e-auto-ladekosten-so-drueckst-du-deine-ausgaben-massiv` | erhoeht | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-05-konto-wechseln-2026-so-sparst-du-gebuehren-ohne-stress` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-05-oekostrom-anbieter-wechseln-clever-sparen-und-gruen-bleiben` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |
| `2026-10-05-strom-und-gas-teure-fehler-beim-vergleichen-vermeiden` | standard | nicht erforderlich | Erstrecherche – noch nie faktengeprüft | unbekannt (Erstrecherche ausstehend) ⚠️ überfällig |

## Ausnahmen (Falsch-Alarm-Protokoll)

Keine aktiven Ausnahmen – alle Checks wirken unverändert.

---
_Exit-Code-Vertrag: 0 = freigabe-reif · 1 = blockierende Funde im Scope · 2 = Werkzeugfehler (fail-closed). Ein nicht führbarer Beweis ist niemals „bestanden“._
