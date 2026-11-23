# 🎯 AFFILIATE-INTENT-REPORT (affiliate_intent_guard.py)

**Stand:** 2026-11-23 13:55:56 UTC · **Modus:** FIX · **Status:** 🟢 Jeder Link liefert das versprochene Angebot

**Geprüfte Artikel:** 146 · **Gateway-Links:** 324 · **Routen im Register:** 20 · **Nie-Paare:** 17 · **Geheilt:** 0

## 🟡 Hinweise – nicht blockierend (ehrliches Cross-Selling, redaktioneller Prüfpunkt)

### IW2 – Primär-CTA ↔ Artikelthema (3)

- `content/posts/2026-10-15-saison-update-was-sich-jetzt-fuer-dich-aendert/index.md`:261 [end] /go/allgemein/ «→ Jetzt Fixkosten auf CHECK24 prüfen» – end-CTA führt zu „CHECK24-Vergleichsportal“, das Artikelthema ist aber „Stromtarife“ (ohne Kontextbeweis an der CTA) – Anker nennt das Ziel, also ehrliches Cross-Selling (Prüfpunkt, keine Täuschung) (ℹ️ Hinweis)
- `content/posts/2026-10-16-dns-server-aendern-fuer-schnelleres-internet/index.md`:186 [end] /go/allgemein/ «→ Jetzt Fixkosten auf CHECK24 prüfen» – end-CTA führt zu „CHECK24-Vergleichsportal“, das Artikelthema ist aber „DSL- & Internettarife“ (ohne Kontextbeweis an der CTA) – Anker nennt das Ziel, also ehrliches Cross-Selling (Prüfpunkt, keine Täuschung) (ℹ️ Hinweis)
- `content/posts/2026-11-20-waermepumpe-vs-gasheizung-was-lohnt-sich-2026/index.md`:164 [end] /go/allgemein/ «→ Jetzt Fixkosten auf CHECK24 prüfen» – end-CTA führt zu „CHECK24-Vergleichsportal“, das Artikelthema ist aber „Gastarife“ (ohne Kontextbeweis an der CTA) – Anker nennt das Ziel, also ehrliches Cross-Selling (Prüfpunkt, keine Täuschung) (ℹ️ Hinweis)

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
