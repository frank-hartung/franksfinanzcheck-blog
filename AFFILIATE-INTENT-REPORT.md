# 🎯 AFFILIATE-INTENT-REPORT (affiliate_intent_guard.py)

**Stand:** 2026-09-30 10:10:47 UTC · **Modus:** FIX · **Status:** 🟢 Jeder Link liefert das versprochene Angebot

**Geprüfte Artikel:** 68 · **Gateway-Links:** 206 · **Routen im Register:** 20 · **Nie-Paare:** 17 · **Geheilt:** 0

## 🟡 Hinweise – nicht blockierend (ehrliches Cross-Selling, redaktioneller Prüfpunkt)

### IW4 – Nie-Paare (2)

- `content/posts/2026-09-30-e-bike-sichern-lohnt-sich-eine-fahrradversicherung/index.md`:41 [top] /go/hausrat/ «Hausratversicherung prüfen & sparen» – Verbotenes Paar: Artikelthema „Wohngebäudeversicherung“ → Route „Hausratversicherung“. Fund 19.09.2026: Wohngebäude-Vergleich, Top-CTA → /go/hausrat/ (Gebäude ≠ Hausrat: zwei verschiedene Policen). – Der Anker nennt das Ziel ehrlich, deshalb kein Täuschungs-Fund, aber ein redaktioneller Prüfpunkt: Fehlt dem Artikel das Hauptangebot /go/wohngebaeudeversicherung/? (ℹ️ Hinweis)
- `content/posts/2026-09-30-e-bike-sichern-lohnt-sich-eine-fahrradversicherung/index.md`:106 [mid] /go/hausrat/ «Jetzt Hausratversicherung vergleichen» – Verbotenes Paar: Artikelthema „Wohngebäudeversicherung“ → Route „Hausratversicherung“. Fund 19.09.2026: Wohngebäude-Vergleich, Top-CTA → /go/hausrat/ (Gebäude ≠ Hausrat: zwei verschiedene Policen). – Der Anker nennt das Ziel ehrlich, deshalb kein Täuschungs-Fund, aber ein redaktioneller Prüfpunkt: Fehlt dem Artikel das Hauptangebot /go/wohngebaeudeversicherung/? (ℹ️ Hinweis)

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
