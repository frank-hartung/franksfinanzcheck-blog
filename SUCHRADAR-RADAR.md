# SUCHRADAR – Status

> Stand: 2026-11-05 15:41:29 Uhr · Anbieter: searxng, duckduckgo, duckduckgo_lite, mojeek, wikipedia
> Schlüssellos · 0 € · Anleitung: `docs/ANLEITUNG-SUCHRADAR.md`

## Lauf

| Kennzahl | Wert |
|---|---|
| Anfragen geplant | 25 |
| Erfolgreich | 23 |
| Aus dem Zwischenspeicher | 0 |
| Fehlgeschlagen | 2 |
| Übersprungen (Budget) | 0 |
| Treffer gesamt | 197 |
| Davon organisch | 0 |
| Eigene Treffer | 0 von 23 Anfragen |

## Datenqualität

| Kennzahl | Wert |
|---|---|
| Anfragen mit echtem Suchindex | 0 von 23 |
| Anfragen nur mit Wissens-Rückfall | 23 |
| Organische Treffer | 0 von 197 |
| Rückfall-Anteil | 100 % |
| Aussagekraft | keine |

_Nur organische Treffer gehen in Rang und Wettbewerb ein. Der Wikipedia-Rückfall verhindert leere Läufe, ist aber kein Ranking._

## Abrufbudget heute

| Anbieter | Abrufe | Limit |
|---|---|---|
| wikipedia | 23 | 300 |

## Eigene Sichtbarkeit

_Kein eigener Treffer in den gemessenen Anfragen._

## Wettbewerb

_Keine Treffer ausgewertet._

## Störungen

| Suchbegriff | Meldung |
|---|---|
| franksfinanzcheck.de | Kein Anbieter lieferte Treffer für 'franksfinanzcheck.de': searxng: SearXNG: keine Instanz lieferte Treffer – https://priv.au: keine Treffer / https://opnxng.com: keine Treffer / h |
| Gaskosten senken | Kein Anbieter lieferte Treffer für 'Gaskosten senken': searxng: SearXNG: keine Instanz lieferte Treffer – https://priv.au: keine Treffer / https://opnxng.com: keine Treffer / https |

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
