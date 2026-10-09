# 🎯 AFFILIATE-INTENT-REPORT (affiliate_intent_guard.py)

**Stand:** 2026-10-09 11:03:52 UTC · **Modus:** FIX · **Status:** 🟢 Jeder Link liefert das versprochene Angebot

**Geprüfte Artikel:** 81 · **Gateway-Links:** 225 · **Routen im Register:** 20 · **Nie-Paare:** 17 · **Geheilt:** 0

## 🟡 Hinweise – nicht blockierend (ehrliches Cross-Selling, redaktioneller Prüfpunkt)

### IW2 – Primär-CTA ↔ Artikelthema (2)

- `content/posts/2026-10-07-campingurlaub-2026-clever-sparen-ohne-komfortverlust/index.md`:183 [end] /go/mietwagen/ «→ Mietwagen mit Vollkasko ohne Selbstbeteiligung vergleichen» – end-CTA führt zu „Mietwagen“, das Artikelthema ist aber „Pauschalreisen“ (ohne Kontextbeweis an der CTA) – Anker nennt das Ziel, also ehrliches Cross-Selling (Prüfpunkt, keine Täuschung) (ℹ️ Hinweis)
- `content/posts/2026-10-08-energie-update-was-sich-jetzt-fuer-dich-aendert/index.md`:81 [end] /go/allgemein/ «→ Jetzt Fixkosten auf CHECK24 prüfen» – end-CTA führt zu „CHECK24-Vergleichsportal“, das Artikelthema ist aber „Stromtarife“ (ohne Kontextbeweis an der CTA) – Anker nennt das Ziel, also ehrliches Cross-Selling (Prüfpunkt, keine Täuschung) (ℹ️ Hinweis)

### IW4 – Nie-Paare (3)

- `content/posts/2026-10-07-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu/index.md`:50 [top] /go/strom/ «Stromanbieter vergleichen & wechseln» – Verbotenes Paar: Artikelthema „Gastarife“ → Route „Stromtarife“. Fund 19.09.2026: Gas-Rechnungsartikel mit Anker „Gasvergleich“ → /go/strom/ – Gas und Strom sind getrennte Rechner; der Haupt-CTA eines Gas-Artikels gehört auf Gas. – Der Anker nennt das Ziel ehrlich, deshalb kein Täuschungs-Fund, aber ein redaktioneller Prüfpunkt: Fehlt dem Artikel das Hauptangebot /go/gas/? (ℹ️ Hinweis)
- `content/posts/2026-10-07-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu/index.md`:81 [mid] /go/strom/ «Stromanbieter vergleichen & sparen» – Verbotenes Paar: Artikelthema „Gastarife“ → Route „Stromtarife“. Fund 19.09.2026: Gas-Rechnungsartikel mit Anker „Gasvergleich“ → /go/strom/ – Gas und Strom sind getrennte Rechner; der Haupt-CTA eines Gas-Artikels gehört auf Gas. – Der Anker nennt das Ziel ehrlich, deshalb kein Täuschungs-Fund, aber ein redaktioneller Prüfpunkt: Fehlt dem Artikel das Hauptangebot /go/gas/? (ℹ️ Hinweis)
- `content/posts/2026-10-07-heizoel-preise-2026-so-findest-du-den-optimalen-kaufzeitpu/index.md`:158 [end] /go/strom/ «→ Jetzt Stromtarife vergleichen» – Verbotenes Paar: Artikelthema „Gastarife“ → Route „Stromtarife“. Fund 19.09.2026: Gas-Rechnungsartikel mit Anker „Gasvergleich“ → /go/strom/ – Gas und Strom sind getrennte Rechner; der Haupt-CTA eines Gas-Artikels gehört auf Gas. – Der Anker nennt das Ziel ehrlich, deshalb kein Täuschungs-Fund, aber ein redaktioneller Prüfpunkt: Fehlt dem Artikel das Hauptangebot /go/gas/? (ℹ️ Hinweis)

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
