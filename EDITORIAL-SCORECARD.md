# 🏆 Chefredakteur-Scorecard
**Stand:** 2026-09-03 · **Auftrag:** Redaktionelle Gesamt-Steuerung

## Gesamt-Score: **83/100** · Ampel: **AMBER**

| Kennzahl | Wert | Ampel |
|---|---|---|
| Veröffentlichte Artikel | 26 | 🟢 |
| Entwürfe (Warteschlange) | 2 | 🟡 |
| Pillars / Themen-Cluster | 6 | 🟢 |
| Decay-Kandidaten (STALE+DECAYING) | 0 | 🟢 |
| Core-Web-Vitals | AMBER | 🟡 |
| Ø Lesbarkeit (Flesch) | n/a | 🟢 |
| Lektorat-Befunde | 110 | 🟡 |
| Tote Secrets | 0 | 🟢 |
| Affiliate-Klicks (Umsatz-Hebel) | 0 über 0 Artikel | 🟡 |
| Awin-Provision (Klicks→Umsatz) | 0.00 € (0.00 € bezahlt) über 0 Artikel | 🟡 |

## Affiliate-Klick-Attribution

_Noch keine Klick-Daten – Umami-Export nach `data/umami_clicks.json` legen, dann `scripts/click_attribution.py` ausführen._

## Awin-Provisions-Import (Monetarisierung)

_Noch keine Awin-Provisions-Daten – `scripts/awin_provisions.py` mit dem Awin-Transaktions-CSV ausführen (Dashboard → Reports → Transactions)._
- Hinweis: `--gen-subid-map` erzeugt `data/subid_map.yaml`; danach `--awin-csv <pfad>` → `AWIN-REPORT.md` + `data/awin_provisions.json`.

## Pillar-Verteilung

| Pillar | Artikel |
|---|---|
| frugalismus | 3 |
| internet-dsl | 7 |
| konto-karten | 4 |
| mietwagen | 2 |
| strom-sparen | 7 |
| versicherungen | 5 |

## Handlungsempfehlungen

- Core-Web-Vitals unter Soll – `scripts/cwv_guard.py` für Befunde; Covers als AVIF/WebP, Bilder < 220 KB, `<img>` mit width/height.
- **110** Lektorat-Befunde – `scripts/lektor_guard.py --fix` (Doppelwörter, Füll-Phrasen, Person-Mix).
- **2** Artikel in der Entwurf-Warteschlange – manuelle Qualitätsfreigabe prüfen (Kadenz- bzw. Qualitäts-Gate).

_Erzeugt von `scripts/editorial_scorecard.py` (Chefredakteur-View)._
