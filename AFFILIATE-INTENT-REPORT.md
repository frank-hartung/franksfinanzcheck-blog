# 🎯 AFFILIATE-INTENT-REPORT (affiliate_intent_guard.py)

**Stand:** 2026-10-04 10:20:27 UTC · **Modus:** FIX · **Status:** 🟢 Jeder Link liefert das versprochene Angebot

**Geprüfte Artikel:** 66 · **Gateway-Links:** 199 · **Routen im Register:** 20 · **Nie-Paare:** 17 · **Geheilt:** 0

## 🟡 Hinweise – nicht blockierend (ehrliches Cross-Selling, redaktioneller Prüfpunkt)

### IW2 – Primär-CTA ↔ Artikelthema (2)

- `content/posts/2026-10-03-interrail-trick-mit-bahncard-guenstig-durch-ganz-europa/index.md`:45 [top] /go/allgemein/ «Jetzt Fixkosten auf CHECK24 prüfen» – top-CTA führt zu „CHECK24-Vergleichsportal“, das Artikelthema ist aber „Mietwagen“ (ohne Kontextbeweis an der CTA) – Anker nennt das Ziel, also ehrliches Cross-Selling (Prüfpunkt, keine Täuschung) (ℹ️ Hinweis)
- `content/posts/2026-10-03-interrail-trick-mit-bahncard-guenstig-durch-ganz-europa/index.md`:179 [end] /go/allgemein/ «→ Jetzt Fixkosten auf CHECK24 prüfen» – end-CTA führt zu „CHECK24-Vergleichsportal“, das Artikelthema ist aber „Mietwagen“ (ohne Kontextbeweis an der CTA) – Anker nennt das Ziel, also ehrliches Cross-Selling (Prüfpunkt, keine Täuschung) (ℹ️ Hinweis)

### IW4 – Nie-Paare (2)

- `content/posts/2026-10-03-photovoltaik-2026-lohnt-sich-der-kauf-jetzt-noch/index.md`:48 [top] /go/strom/ «Stromanbieter vergleichen & wechseln» – Verbotenes Paar: Artikelthema „Gastarife“ → Route „Stromtarife“. Fund 19.09.2026: Gas-Rechnungsartikel mit Anker „Gasvergleich“ → /go/strom/ – Gas und Strom sind getrennte Rechner; der Haupt-CTA eines Gas-Artikels gehört auf Gas. – Der Anker nennt das Ziel ehrlich, deshalb kein Täuschungs-Fund, aber ein redaktioneller Prüfpunkt: Fehlt dem Artikel das Hauptangebot /go/gas/? (ℹ️ Hinweis)
- `content/posts/2026-10-03-photovoltaik-2026-lohnt-sich-der-kauf-jetzt-noch/index.md`:265 [end] /go/strom/ «→ Jetzt Stromtarife vergleichen» – Verbotenes Paar: Artikelthema „Gastarife“ → Route „Stromtarife“. Fund 19.09.2026: Gas-Rechnungsartikel mit Anker „Gasvergleich“ → /go/strom/ – Gas und Strom sind getrennte Rechner; der Haupt-CTA eines Gas-Artikels gehört auf Gas. – Der Anker nennt das Ziel ehrlich, deshalb kein Täuschungs-Fund, aber ein redaktioneller Prüfpunkt: Fehlt dem Artikel das Hauptangebot /go/gas/? (ℹ️ Hinweis)

## Vertrag

| Prüfung | Garantie |
|:--|:--|
| IW1 | Nennt der Anker ein Produkt, liefert die Route genau dieses Produkt. |
| IW2 | Top-/Mid-/End-CTA dient dem Artikelthema (oder ist durch den CTA-Kontext gedeckt). |
| IW3 | Routen mit Abweichung (C24 Bank, Pauschalreise statt Flug) benennen das echte Ziel. |
| IW4 | Eingefrorene Nie-Paare (z. B. Kfz-Artikel → Haftpflicht) sind unmöglich. |
| IW5 | Jede /go/-Seite nennt das echte Ziel, ist noindex und leitet exakt auf die Register-URL. |
| IW6 | Die Engine-Vorlagen erzeugen für jede Route konforme CTAs (Quelle mitbewacht). |
| IW7 | Interne Lesetipps werden nicht zu Affiliate-Links entführt. |
| IW8 | Kein Anker bleibt generisch – jeder nennt das Angebot. |
| IW9 | Template- und Shortcode-CTAs gelten derselbe Kontrakt. |

---
_Wahrheit: `scripts/affiliate_intent_contract.py` (Angebote, Namen, ehrliche Anker, Nie-Paare). Selbsttest: `python3 scripts/affiliate_intent_guard.py --selftest`. Heilung: `--fix` (deterministisch, idempotent, keine KI)._
