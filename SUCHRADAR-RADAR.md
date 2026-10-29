# SUCHRADAR – Status

> Stand: 2026-10-29 13:56:18 Uhr · Anbieter: searxng, duckduckgo, duckduckgo_lite, mojeek, wikipedia
> Schlüssellos · 0 € · Anleitung: `docs/ANLEITUNG-SUCHRADAR.md`

## Lauf

| Kennzahl | Wert |
|---|---|
| Anfragen geplant | 25 |
| Erfolgreich | 20 |
| Aus dem Zwischenspeicher | 0 |
| Fehlgeschlagen | 5 |
| Übersprungen (Budget) | 0 |
| Treffer gesamt | 166 |
| Davon organisch | 10 |
| Eigene Treffer | 0 von 20 Anfragen |

## Datenqualität

| Kennzahl | Wert |
|---|---|
| Anfragen mit echtem Suchindex | 1 von 20 |
| Anfragen nur mit Wissens-Rückfall | 19 |
| Organische Treffer | 10 von 166 |
| Rückfall-Anteil | 94 % |
| Aussagekraft | eingeschraenkt |

_Nur organische Treffer gehen in Rang und Wettbewerb ein. Der Wikipedia-Rückfall verhindert leere Läufe, ist aber kein Ranking._

## Abrufbudget heute

| Anbieter | Abrufe | Limit |
|---|---|---|
| searxng | 1 | 400 |
| wikipedia | 19 | 300 |

## Eigene Sichtbarkeit

_Kein eigener Treffer in den gemessenen Anfragen._

## Wettbewerb

| Domäne | Treffer | Top 3 | Ø Rang | Bester Rang |
|---|---|---|---|---|
| ing.de | 1 | 1 | 1.0 | 1 |
| lexware.de | 1 | 1 | 2.0 | 2 |
| finanzenfroh.com | 1 | 1 | 3.0 | 3 |
| genialetricks.de | 1 | 0 | 4.0 | 4 |
| verivox.de | 1 | 0 | 5.0 | 5 |
| bank99.at | 1 | 0 | 6.0 | 6 |
| sparschweinclub.de | 1 | 0 | 7.0 | 7 |
| falk-ratgeber.de | 1 | 0 | 8.0 | 8 |
| schuldnerberatung.de | 1 | 0 | 9.0 | 9 |
| mlp-financify.de | 1 | 0 | 10.0 | 10 |

## Störungen

| Suchbegriff | Meldung |
|---|---|
| franksfinanzcheck.de | Kein Anbieter lieferte Treffer für 'franksfinanzcheck.de': searxng: SearXNG: keine Instanz lieferte Treffer – https://opnxng.com: keine Treffer / https://paulgo.io: keine Treffer / |
| Gaskosten senken | Kein Anbieter lieferte Treffer für 'Gaskosten senken': searxng: SearXNG: keine Instanz lieferte Treffer – https://opnxng.com: keine Treffer / https://paulgo.io: keine Treffer / htt |
| SF-Klasse retten | Kein Anbieter lieferte Treffer für 'SF-Klasse retten': searxng: SearXNG: keine Instanz lieferte Treffer – https://opnxng.com: keine Treffer / https://paulgo.io: keine Treffer / htt |
| Secondhand Möbel | Kein Anbieter lieferte Treffer für 'Secondhand Möbel': searxng: SearXNG: keine Instanz lieferte Treffer – https://opnxng.com: keine Treffer / https://paulgo.io: keine Treffer / htt |
| Seniorenkonto | Kein Anbieter lieferte Treffer für 'Seniorenkonto': searxng: SearXNG: keine Instanz lieferte Treffer – https://opnxng.com: keine Treffer / https://paulgo.io: keine Treffer / https: |

## Einordnung

Ohne API-Schlüssel gibt es kein Google-Original-Ranking: SearXNG
bündelt den Google-Index über fremde Instanzen, DuckDuckGo und
Mojeek sind eigene Indizes. Die Ränge sind Indikationen, keine
Positionsgarantie. Für die exakte Position ist die Google Search
Console die richtige Quelle – ebenfalls kostenlos. Ergänzend liegt
ein **einmalig live geprüfter Google-SERP-Snapshot** unter
`data/serp/` (siehe `SERP-LIVE-PRUEFUNG-HIGHEND-2026-10-25.md`);
die Wache `scripts/serp_live_wache.py` hält ihn und die eigenen
Snippets dauerhaft im Blick. Automatisiertes google.com-Scraping
bleibt aus Vertrags- und Datenqualitätsgründen tabu.

Kein Treffer aus diesem Bericht wird ungeprüft in einen Artikel
übernommen. Das Radar misst; die Entscheidung trifft Frank.
