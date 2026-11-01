# SUCHRADAR – Status

> Stand: 2026-11-01 14:12:01 Uhr · Anbieter: searxng, duckduckgo, duckduckgo_lite, mojeek, wikipedia
> Schlüssellos · 0 € · Anleitung: `docs/ANLEITUNG-SUCHRADAR.md`

## Lauf

| Kennzahl | Wert |
|---|---|
| Anfragen geplant | 25 |
| Erfolgreich | 22 |
| Aus dem Zwischenspeicher | 0 |
| Fehlgeschlagen | 3 |
| Übersprungen (Budget) | 0 |
| Treffer gesamt | 187 |
| Davon organisch | 10 |
| Eigene Treffer | 0 von 22 Anfragen |

## Datenqualität

| Kennzahl | Wert |
|---|---|
| Anfragen mit echtem Suchindex | 1 von 22 |
| Anfragen nur mit Wissens-Rückfall | 21 |
| Organische Treffer | 10 von 187 |
| Rückfall-Anteil | 95 % |
| Aussagekraft | eingeschraenkt |

_Nur organische Treffer gehen in Rang und Wettbewerb ein. Der Wikipedia-Rückfall verhindert leere Läufe, ist aber kein Ranking._

## Abrufbudget heute

| Anbieter | Abrufe | Limit |
|---|---|---|
| searxng | 1 | 400 |
| wikipedia | 21 | 300 |

## Eigene Sichtbarkeit

_Kein eigener Treffer in den gemessenen Anfragen._

## Wettbewerb

| Domäne | Treffer | Top 3 | Ø Rang | Bester Rang |
|---|---|---|---|---|
| ing.de | 1 | 1 | 1.0 | 1 |
| lexware.de | 1 | 1 | 2.0 | 2 |
| bank99.at | 1 | 1 | 3.0 | 3 |
| mlp-financify.de | 1 | 0 | 4.0 | 4 |
| schuldnerberatung.de | 1 | 0 | 5.0 | 5 |
| sparkasse.de | 1 | 0 | 6.0 | 6 |
| peaks.com | 1 | 0 | 7.0 | 7 |
| meetadam.io | 1 | 0 | 8.0 | 8 |
| fonio.ai | 1 | 0 | 9.0 | 9 |
| verivox.de | 1 | 0 | 10.0 | 10 |

## Störungen

| Suchbegriff | Meldung |
|---|---|
| franksfinanzcheck.de | Kein Anbieter lieferte Treffer für 'franksfinanzcheck.de': searxng: SearXNG: keine Instanz lieferte Treffer – https://opnxng.com: keine Treffer / https://paulgo.io: keine Treffer / |
| Gaskosten senken | Kein Anbieter lieferte Treffer für 'Gaskosten senken': searxng: SearXNG: keine Instanz lieferte Treffer – https://opnxng.com: keine Treffer / https://paulgo.io: keine Treffer / htt |
| Tarife Sofortleistung Haken | Kein Anbieter lieferte Treffer für 'Tarife Sofortleistung Haken': searxng: SearXNG: keine Instanz lieferte Treffer – https://opnxng.com: keine Treffer / https://paulgo.io: keine Tr |

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
