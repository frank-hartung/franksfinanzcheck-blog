# 🏆 Chefredakteur-Scorecard
**Stand:** 2026-09-07 · **Auftrag:** Redaktionelle Gesamt-Steuerung · erster erfasster Lauf

## Gesamt-Score: **85/100** · Ampel: **GREEN**

| Kennzahl | Wert | Ampel |
|---|---|---|
| Veröffentlichte Artikel | 31 | 🟢 |
| Entwürfe (Warteschlange) | 1 | ⚪ |
| Pillars / Themen-Cluster | 6 | 🟢 |
| Decay-Kandidaten (STALE+DECAYING) | 0 | 🟢 |
| Core-Web-Vitals | GREEN | 🟢 |
| Ø Lesbarkeit (Flesch) | 53.3 | 🟡 |
| Lektorat-Befunde (auto-behebbar) | 0 | 🟢 |
| Stil-Hinweise (Lektorat, nur Info) | 18 | ℹ️ |
| Secrets (rot / gelb / bewiesen) | 1 / 0 / 3 von 4 | 🔴 |
| Affiliate-Klicks (Umsatz-Hebel) | 0 über 0 Artikel | ⚪ |
| Awin-Provision (Klicks→Umsatz) | 0.00 € (0.00 € bezahlt) über 0 Artikel | ⚪ |

## Affiliate-Klick-Attribution

_Noch keine Klick-Daten – Umami-Export nach `data/umami_clicks.json` legen, dann `scripts/click_attribution.py` ausführen._

## Awin-Provisions-Import (Monetarisierung)

_Noch keine Awin-Provisions-Daten – `scripts/awin_provisions.py` mit dem Awin-Transaktions-CSV ausführen (Dashboard → Reports → Transactions)._
- Hinweis: `--gen-subid-map` erzeugt `data/subid_map.yaml`; danach `--awin-csv <pfad>` → `AWIN-REPORT.md` + `data/awin_provisions.json`.

## Datenlagen (Messabdeckung)

| Kennzahl | Quelle | Stand | Bewertung |
|---|---|---|---|
| Core-Web-Vitals | `data/cwv_manifest.json` | 0 d | gemessen |
| Decay-Radar | `data/decay_queue.json` | - | 0 Kandidat(en) |
| Secrets | `SECRETS-REPORT.md + data/secrets_state.json` | RED | 3/4 live bewiesen |
| Lektorat | `LEKTOR-REPORT.md` | heute | 0 auto-behebbar, 18 Stil-Hinweise |
| Affiliate-Klicks | `data/umami_clicks.json (via scripts/umami_clicks.py)` | 2026-09-07 | Pipeline wartet auf Secret `UMAMI_API_TOKEN` |
| Awin-Provision | `data/awin_transactions.csv` | - | CSV-Export fehlt |

## Pillar-Verteilung

| Pillar | Artikel |
|---|---|
| frugalismus | 4 |
| internet-dsl | 9 |
| konto-karten | 4 |
| mietwagen | 3 |
| strom-sparen | 7 |
| versicherungen | 5 |

## Handlungsempfehlungen

- **1** rote Secret-Befunde – Kanal ist tot oder abgelaufen: `python3 scripts/secrets_age_guard.py --verify` zeigt live, welche API den Token ablehnt (Pinterest 30-Tage-Token, Mastodon, KI-Keys).
- Ø Lesbarkeit 53.3 (Ziel ≥ 70, Amstad-deutsch) – lange Sätze splittern, Nominalstil auflösen; Hebel pro Artikel zeigt `python3 scripts/readability_check.py` bzw. `lektor_guard.py`. Lesbarkeit ist bei Pinterest-/Suchtraffic der Verweil-Dauer-Hebel.
- **1** Artikel in der Entwurf-Warteschlange – Freigabe prüfen (`python3 scripts/publish_gate.py` bzw. Kadenz-Gate). Vorrat ist kein Mangel – erst > 8 Entwürfe werden zu Altlasten.
- Umsatz-Daten fehlen, weil die Pipeline nie gefüllt wurde – nicht, weil niemand klickt: `python3 scripts/umami_clicks.py --fetch` (Secret `UMAMI_API_TOKEN`; Website-ID steht schon in `hugo.toml`).

_Erzeugt von `scripts/editorial_scorecard.py` (Chefredakteur-View)._
