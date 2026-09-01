# 🏆 Chefredakteur-Scorecard
**Stand:** 2026-09-01 · **Auftrag:** Redaktionelle Gesamt-Steuerung

## Gesamt-Score: **90/100** · Ampel: **GREEN**

| Kennzahl | Wert | Ampel |
|---|---|---|
| Veröffentlichte Artikel | 24 | 🟢 |
| Entwürfe (Warteschlange) | 1 | 🟡 |
| Pillars / Themen-Cluster | 6 | 🟢 |
| Decay-Kandidaten (STALE+DECAYING) | 0 | 🟢 |
| Core-Web-Vitals | UNKNOWN | 🔴 |
| Ø Lesbarkeit (Flesch) | n/a | 🟢 |
| Lektorat-Befunde | 100 | 🟡 |
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
| konto-karten | 3 |
| mietwagen | 1 |
| strom-sparen | 7 |
| versicherungen | 4 |

## Handlungsempfehlungen

- Core-Web-Vitals unter Soll – `scripts/cwv_guard.py` für Befunde; Covers als AVIF/WebP, Bilder < 220 KB, `<img>` mit width/height.
- **100** Lektorat-Befunde – `scripts/lektor_guard.py --fix` (Doppelwörter, Füll-Phrasen, Person-Mix).
- **1** Artikel in der Entwurf-Warteschlange – manuelle Qualitätsfreigabe prüfen (Kadenz- bzw. Qualitäts-Gate).

_Erzeugt von `scripts/editorial_scorecard.py` (Chefredakteur-View)._
