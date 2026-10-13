# Faktenfrische #731 – 13 fachliche Befunde dauerhaft behoben

Stand: 13.10.2026. Lokale Umsetzung auf dem Arbeitsbranch; Freigabe über Pull
Request („Closes #731“), danach übernimmt der Abschlussvermerk-Workflow die
Meldung.

## Ausgangslage

Issue #731 meldete 13 offene fachliche Befunde aus dem Faktenfrische-Lauf von
13.10.2026, 12:08 UTC. Alle drei betroffenen Seiten standen zur **Erstrecherche**
an (noch nie faktengeprüft); die Maschine hatte zuvor korrekt nur die
Frontmatter-Felder `faktencheck` und `quellen` gesetzt – den Text berührt sie
nicht (KI-Redaktions-Statut). Die Textarbeit ist genau diese hier.

| Seite | Befunde | GEO-Reife vorher | GEO-Reife nachher |
|---|---|---|---|
| Energie-Update: Was sich jetzt für dich ändert (08.10.) | 5 | 17 % (1/6) | **100 % (6/6)** |
| 7 Gewohnheiten für finanzielle Freiheit (09.10.) | 3 | 50 % (3/6) | **100 % (6/6)** |
| Stromfresser im Haushalt entlarven (12.10.) | 5 | 50 % (3/6) | **100 % (6/6)** |

Gemessen mit der Maschinenlogik selbst (`geo_reife()` aus
`scripts/faktenfrische.py`, je Artikel 6/6 Kriterien erfüllt).

## Befund für Befund: was geändert wurde

### Energie-Update: Was sich jetzt für dich ändert (5 Befunde)

1. **Präzision – „Marktrisiko bleibt beim Anbieter“ (falsch).** Die
   Risikozuordnung war invertiert. Neu: Bei einem variablen Tarif werden die
   Spot-Markt-Preise an den Verbraucher weitergegeben – das Preisrisiko trägt
   du. Der Festpreis kehrt das Verhältnis um: Der Anbieter übernimmt das
   Marktrisiko für die Laufzeit und kalkuliert dafür einen Aufschlag. Die
   Gegenprobe („sparst nur, wenn die Preise wirklich steigen“) wurde zu
   „… über deinem Festpreis bleiben“ präzisiert.
2. **Lücke – Preisobergrenzen bei variablen Tarifen.** Neuer Bullet
   „Zwischenformen beachten“: variable Tarife mit Preisgarantie oder
   Preisobergrenze; Preis bleibt beweglich, steigt aber nur bis zur
   vereinbarten Deckelung. Zusätzlich als eigene Spalte „Variabel mit
   Preisdeckel“ in der neuen Vergleichstabelle.
3. **Veraltet – „Stand: 08.10.2026“ suggerierte 2026er-Preisdaten.** Stand auf
   13.10.2026 aktualisiert und ehrlich gerahmt: Belegbare Zahlen stammen aus
   den zuletzt veröffentlichten amtlichen Daten der Bundesnetzagentur;
   gesicherte Prognosen für 2026 gibt es nicht. Die Einleitung
   („2026 liegen die Preise …“) wurde zu „Aktuell …“ entschärft.
4. **Präzision – Festpreisschutz zu pauschal.** Überall qualifiziert auf die
   Vertragslaufzeit: Bullet „Deine Kosten schwanken“, Faustregel 2 („während
   der Laufzeit … danach gelten wieder Marktpreise“) und der Hintergrund-Absatz
   („Läuft die Laufzeit aus, gilt wieder der Markt.“).
5. **Lücke – Informationspflichten des Anbieters.** Schritt 2 erweitert:
   Grundpreis und Arbeitspreis müssen getrennt ausgewiesen werden
   (Transparenzpflicht, Bundesnetzagentur); erst die Summe beider Komponenten
   ist vergleichbar.

Dazu die GEO-Aufstockung: `kurzantwort` im Frontmatter (Kurzantwort-Box),
Vergleichstabelle der drei Tarifformen sowie ein konkretes Rechenbeispiel
(4 000 kWh × 0,40 € = 1 600 €, + 10 € Grundpreis/Monat = 1 720 €; ein Cent
Mehrpreis = 40 €/Jahr).

### 7 Gewohnheiten für finanzielle Freiheit (3 Befunde)

1. **Lücke – Inflation 3,3 % (Destatis) fehlte.** Nach dem
   7‑200‑€-Rechenbeispiel: Bei 3,3 % jährlicher Teuerung sind die 7 200 € nach
   einem Jahr real nur noch rund 6 970 € wert (7 200 ÷ 1,033). Sparziele in
   heutiger Kaufkraft setzen.
2. **Lücke – Energiepreise +14,9 % (Destatis) fehlten.** Im Abschnitt
   „Fixkosten regelmäßig prüfen“: Die Energiepreise sind zuletzt um 14,9 %
   gestiegen; wer Tarife nicht prüft, zahlt solche Sprünge still mit.
3. **Präzision – ETF-Endkapital nur nominal.** Nach der 9‑800‑€-Rechnung: Bei
   anhaltend 3,3 % Inflation pro Jahr entspricht das Endkapital in heutiger
   Kaufkraft rund 7 080 € (9 800 ÷ 1,033¹⁰); die 7 % Rendite sind vor Inflation
   gerechnet.

Dazu die GEO-Aufstockung: `kurzantwort` im Frontmatter mit der Kaufkraft-Zahl.
`lastmod: 2026-10-13` gesetzt (echte inhaltliche Überarbeitung, nicht
Frische-Inflation – `lastmod` bleibt vom Faktenfrische-Skript bewusst
unberührt; diese manuelle Überarbeitung belegt es).

### Stromfresser im Haushalt entlarven (5 Befunde)

1. **Veraltet – 30 ct/kWh.** Sämtliche Rechnungen konsistent auf den
   aktuellen Durchschnittsendpreis von rund 40 ct/kWh (Bundesnetzagentur)
   umgestellt: Standby-Beispiel (1,08 → 1,44 €/Monat, 5 Geräte über 7 €/Monat,
   ~86 €/Jahr), Smart-Plug TV-Ecke (8,70 → knapp 12 €/Jahr, Amortisation unter
   zwei Jahren), Router (1,30 → 1,70 €/Monat, ~10 €/Jahr bei Nachtabschaltung),
   Kaffeemaschine (42 → rund 60 Cent), Kühlschrank (45 → 60 €/Jahr).
2. **Lücke – EU-Energieeffizienzkennzeichnung.** Jetzt explizit: das
   verpflichtende EU-Energieeffizienzlabel, Skala A–G, Jahresverbrauch in
   Kilowattstunden direkt auf dem Label.
3. **Präzision – Standby-Werte zu hoch.** Tabelle auf realistische Werte für
   aktuelle Geräte gestellt (0,5–2 W laut Bundesnetzagentur; Fernseher 2 W,
   Konsole 1 W, AV-Receiver 1,5 W, Kaffeemaschine 1 W, Ladegerät 0,5 W – kWh-
   und Euro-Spalten konsistent neu gerechnet bei 0,40 €/kWh). Der 5-W-Fernseher
   bleibt als klar markiertes **älteres** Gerät im Rechenbeispiel. Auch die
   FAQ-Schwelle („mehr als 5 Watt“) korrigiert: aktuelle Geräte 0,5–2 W,
   deutlich darüber = Verdachtsfall.
4. **Lücke – kostenloses Online-Tool der Bundesnetzagentur.** Messabschnitt
   beginnt jetzt kostenlos: Online-Analyse des Stromverbrauchs bei der
   Bundesnetzagentur (0 €) vor den Kauf-Optionen; neue erste Tabellenzeile
   „Online-Analyse (Bundesnetzagentur) · gering · grob · 0“.
5. **Präzision – Amortisation unpräzise („9–10 Jahre“).** Die
   Fünf-Jahres-Orientierung der Bundesnetzagentur ist nun die Faustregel (drei
   Stellen: Faustregel-Block, Kühlschrank-Rechnung, FAQ): Ersparnis muss den
   Kaufpreis in spätestens fünf Jahren hereinbringen (mind. ein Fünftel pro
   Jahr). Beispiel ehrlich nachgerechnet: 450 € Gerät = 7,5 Jahre → zu lang;
   300 € = genau 5 Jahre; 280 € = gut 4,5 Jahre. Das „ein Drittel pro Jahr“
   (3-Jahre-Untergrenze) wurde an keiner Stelle mehr benutzt.

Dazu die GEO-Aufstockung: `kurzantwort` im Frontmatter (mit Online-Tool,
0,5–2 W, 40 ct, Fünf-Jahres-Regel).

## Belegdisziplin (Anti-Halluzinations-Vertrag unangetastet)

- Alle neuen Sachaussagen stammen aus den dokumentierten Befunden von #731 und
  dem Dossier; als Quellen werden nur die beiden schon im Frontmatter
  stehenden, allowlist-fähigen Belege genannt: Bundesnetzagentur
  (bundesnetzagentur.de, Rang 1) und Statistisches Bundesamt (destatis.de,
  Rang 1). Keine neue URL erfunden, keine Affiliate-Quelle belegfähig gemacht.
- Die Maschine hat weiterhin nur `faktencheck`/`quellen` geschrieben; jeder
  Texteingriff ist redaktionell und hier belegt.
- `lastmod` nur dort gesetzt, wo inhaltlich überarbeitet wurde (keine
  Frische-Inflation).

## Lokale Nachweise

- `python3 scripts/faktenfrische.py --selftest`: **23/23 Fälle grün**.
- `geo_reife()` je Artikel: **6/6 (100 %)** für alle drei Seiten (vorher
  17/50/50 %); gemessen gegen den unveränderten Prüfcode.
- Rechenkonsistenz: alle 30 neuen Zahlenangaben programmatisch gegengerechnet
  (Watt→kWh→Euro bei 0,40 €/kWh, Amortisationszeiten, Inflation 3,3 % auf
  7 200 € und 9 800 €, Grund-/Arbeitspreis-Beispiel) – **alle konsistent**.
- `python3 scripts/zeit_rechtschreibung.py --offline`: 56 Artikel, **0 Funde**.
- `python3 scripts/seo_audit.py`: **0 Probleme** in 56 Artikeln.
- `python3 scripts/editorial_review_gate.py --published --strict`: **0 Hoch-
  risiko, 0 blockiert** (Live-Bestand unberührt; alle drei Seiten sind
  Entwürfe ohne Siegel – kein Siegelbruch, keine Neuversiegelung nötig).
- Maschineneigene Lauf-Dateien (`data/faktenfrische_queue.json`, Historie,
  Dossiers) wurden nach einem lokalen Offline-Probelauf **zurückgesetzt** –
  sie gehören dem nächsten echten CI-Lauf mit Netz (Do, 04:40 UTC).

## Ehrliche Grenzen

- Die lokale Fachprüfung konnte nicht live nachrecherchieren (keine
  Netz-Kanäle/Modell-Schlüssel in dieser Umgebung). Die nexte geplante
  Bestands-Recherche (Dienstag/Donnerstag) prüft live; die drei Artikel sind
  durch `faktencheck: 2026-10-13` für 45 Tage (YMYL) bzw. 90 Tage (Standard)
  nicht fällig – der echte Gegenbeweis läuft dann automatisch.
- Die beiden Artikel „Energie-Update“ und „7 Gewohnheiten“ tragen daneben
  **unabhängige** Entwurfs-Blocker (Mindestlänge < 10 000 Zeichen, interne
  Verlinkung < 2). Die gehören zur eigenen Heilungs-Pipeline des
  Content-Engine-Publish-Pfads (length_guard, link_density_guard) und wurden
  hier bewusst nicht berührt – Issue #731 umfasst sie nicht.
- Verbleibende GEO-Lücken im Gesamtbestand (z. B. 11 Kurzantwort-Boxen,
  10 Tabellen) betreffen **andere** Artikel und laufen über die
  Rotations-Budgets der künftigen Läufe; sie sind nicht Teil dieser Meldung.

## Dauerhaftigkeit

Die Korrekturen sind im Artikeltext verankert, nicht als Overlays: Jede Zahl
wurde konsistent auf die neue Belegbasis (40 ct/kWh, Inflation 3,3 %)
umgerechnet statt nur annotiert; falsche Kernsätze wurden ersetzt, nicht
widerlegt. Beim nächsten Fälligkeitslauf (YMYL: ~27.11.2026, Standard:
~11.01.2027) prüft die Fachprüfung die Seiten erneut – wer hier nachlässt,
fällt dort auf.
