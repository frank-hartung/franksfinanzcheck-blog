# 📌 PINTEREST-SPIELBUCH – Profi-Level für franksfinanzcheck.de

**Stand:** 12.08.2026 · **Ziel:** Pinterest bestmöglich mit dem Blog verbinden,
Spam-Sperren vermeiden und beheben.

---

## 1. Die Meldung „Link gesperrt – leitet möglicherweise an eine Spam-Webseite weiter"

Diese Meldung bekommst du, wenn Pinterest die **Ziel-URL eines Pins** (oder deren
Weiterleitungskette) als verdächtig einstuft. Wichtige Einordnung:

| Mögliche Ursache | Wahrscheinlichkeit | Lösung |
|---|---|---|
| Domain nach früheren Massen-Pin-Versuchen auf Pinterest-Blocklist | **hoch** | Pinterest-Support/Business-Konto, siehe §4 |
| Die gepinnte URL leitet selbst weiter (Meta-Refresh) | niedrig | ab 24.10.2026 gemessen: Live-Artikel liefern direkt aus (P10), **Pin-Ziele** werden zusätzlich gegen die Live-SSOT geprüft (P14) – ein geparktes Ziel kommt nicht in den Plan |
| Zu viele Affiliate-Links / unmarkierte Affiliate-Links | niedrig | höchstens 5 je Artikel; sparsame Platzierung bevorzugt, `rel="sponsored nofollow"` (P11/P12) |
| Blockierte Affiliate-Domain als Pin-Ziel | niedrig | Pins zeigen auf Artikel, nicht auf /go/ |

**Unsere technischen Checks (automatisiert, `pinterest_check.py`):**
- P10: **Live**-Artikel-Seiten haben KEINEN eigenen Redirect ✅; eine geparkte URL
  (draft: true) darf weiterleiten, aber nur wenn `data/weiterleitungen.yaml` das
  erklärt – der Report nennt sie ausdrücklich (#822)
- P14: kein Pin-Ziel ist eine Weiterleitung, ein Entwurf oder fehlend ✅
  (Masterplan + Queue; Heilung nur über die SSOT, s. u.)
- P11: höchstens 5 Affiliate-Links pro Artikel; Überschreitungen werden gemeldet, nicht automatisch aus dem redaktionellen Text entfernt ✅
- P12: /go/-Links mit `rel="sponsored nofollow"` ✅
- P13: /go/-Seiten sind noindex (keine dünnen Seiten) ✅
- P1: robots.txt erlaubt Pinterest, blockt /go/ ✅

---

## 2. Sofort-Maßnahmen (wichtigste Profi-Schritte)

1. **NICHT weiter probieren.** Jeder weitere Pin-Versuch mit der Sperr-Meldung
   verstärkt die negative Bewertung. 24–48 h Pause.
2. **URL-Debugger von Pinterest nutzen:**
   https://developers.pinterest.com/tools/url-debugger/
   → Artikel-URL eingeben → „Check" → zeigt, was Pinterest von der Seite sieht
   (Titel, Bild, Beschreibung, Weiterleitungen). Dort steht oft der genaue Grund.
3. **Rich Pins aktualisieren:** Im URL-Debugger auf „Apply for Rich Pins" klicken
   (oder im Business-Konto). Unsere og-Tags sind vollständig (P6/P7) – die
   Freischaltung bestätigt Pinterest, dass die Domain „echter" Content ist.
4. **Website-Anspruch prüfen:** Pinterest Business → Einstellungen → Anspruch
   auf Website → sollte „Bestätigt" zeigen (p:domain_verify ist vorhanden, P2).
   Falls abgelaufen: neu verifizieren.
5. **Sitemap einreichen:** Pinterest Business → Anspruch → Sitemap-URL
   `https://franksfinanzcheck.de/sitemap.xml` hinterlegen.

---

## 3. Dauerhaftes Pin-Verhalten (Warm-up, Profi-Regeln)

| Regel | Wert |
|---|---|
| Pins pro Tag | **max. 2–3** |
| Abstand zwischen Pins | mind. 1–2 Stunden |
| Re-Pins desselben Artikels | **niemals** |
| Boards | verschiedene Boards nutzen, kein „Pin-Flooding" auf ein Board |
| Pin-Beschreibung | einzigartig (automatisch: Meta-Description + 3 Hashtags) |
| Pin-Ziel | immer die Artikel-URL (nie /go/, nie Affiliate-Direktlinks) |
| Bilder | 1000×1500 (2:3), Text-Overlay – automatisch so |

Die Pinterest-Engine (sobald Token hinterlegt) postet mit Rate-Limit:
**3 Pins/Lauf, 45 s Abstand** (`PINS_PRO_TAG`/`PIN_PAUSE_S` in pinterest_engine.py).

---

## 4. Wenn die Sperre bleibt (Pinterest-Support)

Nach 48 h Pause + URL-Debugger ohne Klärung:

1. **Business-Konto-Hilfe:** https://help.pinterest.com/de/contact
   (Thema: „Link/Bild gesperrt", Konto: Business)
2. **Meldung wörtlich angeben:** „Leider mussten wir diesen Link sperren, weil er
   möglicherweise an eine Spam-Webseite weiterleitet."
3. **Bereits erledigte Schritte auflisten:** Domain verifiziert (P2), Rich-Pin-Meta
   vollständig (P6/P7), robots.txt erlaubt Pinterest (P1), keine Weiterleitungen
   auf Artikel-Seiten (P10), Affiliate-Links markiert (P12).
4. **Gepinnte URL nennen** und dass die Seite direkt, ohne Redirect, ausgeliefert
   wird (kann man mit `curl -sI <URL>` belegen: HTTP 200, kein Location-Header).

---

## 5. Automatisierte Überwachung (bereits aktiv)

- **Pinterest-Watchdog** (`.github/workflows/pinterest-watchdog.yml`): täglich
  05:30 UTC – baut die Site, läuft `pinterest_check.py --fix` (P1–P14),
  danach die unabhängige Zielwache `pinterest_link_guard.py` (L1/L2: jedes
  Pin-Ziel gegen den Bestand),
  committet PINTEREST-REPORT.md, öffnet bei Problemen ein Issue (Label `pinterest`)
  und schließt es beim ersten grünen Lauf (Exit 0).
- **Lokal:** `python3 scripts/pinterest_check.py` (Check) / `--fix` (Selbstheilung)
- **Hashtags (P8, seit #729):** Die Regel H1–H6 (max. 3, nur `[a-z0-9]`,
  3–24 Zeichen, Zahlenschilder wie `#1` sind keine Tags, Block am Textende)
  steht in EINER Quelle: `scripts/pinterest_hashtags.py`. Die Regel ist als
  Wache im Governance-Vertrag (C6), ihre Wirkung als C37: Jeder
  Hashtag-Befund in einer `pin_description` wird deterministisch geheilt
  (falten, hinten kappen, Block ans Ende – idempotent), und ein neuer Artikel
  mit fünf Tags macht den Vertrag rot, bevor ein Issue entsteht. Beweise:
  `python3 scripts/pinterest_hashtags.py --selftest|--wirkungsprobe` ·
  `python3 -m unittest scripts.tests.test_pinterest_hashtags`.
- **Pin-Ziele (P14, seit #822):** Die Frage „ist dieses Ziel noch ein
  Artikel?“ beantwortet EINE Quelle: `scripts/pinterest_ziele.py` – über
  `weiterleitungen.live_urls()`, also dieselbe Live-Definition wie
  `url_wache.py`. Geheilt wird ohne Erfindung: Erklärt die SSOT einen
  gleichwertigen Live-Nachfolger (Regel A/B), wird der Pin umgeschrieben;
  sonst wandert er nach `data/pinterest_plan_parked.yaml` (kein
  Content-Verlust, wartet auf seinen eigenen Artikel). Queue-Einträge werden
  entfernt. Beweise: `python3 scripts/pinterest_ziele.py --selftest` ·
  `python3 -m unittest scripts.tests.test_pinterest_ziele`.
- **Report-Provenienz:** `PINTEREST-REPORT.md` enthält ab Schema 2 einen
  Quellfingerabdruck (Schema 5 seit #822, inklusive Hashtag-Regel,
  Weiterleitungs-SSOT, Masterplan/Queue und Zielwache). Der Bot-Watchdog
  verwirft alte oder ohne Nachweis übernommene Reports, statt daraus einen
  Phantom-Alarm zu erzeugen (Fix für Issue #390).

---

*Ergänzt am 12.08.2026 · Teil der FrankAutoOps-Dokumentation.*

## 6. Trust-Shield: Prüfliste ja, Skript nein (Stand 13.10.2026)

Die Prüfliste eines „Trust-Shield" (12 Anti-Spam-Signale T1–T12) ist als
**Checkliste** entstanden; das zugehörige Skript `scripts/pinterest_trust_shield.py`
und der Report `PINTEREST-TRUST-REPORT.md` sind nie in dieses Repository
gekommen (Wahrheitsprobe: `git ls-files | grep -i trust` → nur
`layouts/_partials/trust_box.html`). Eine Doku, die ein Skript beschreibt, das
es nicht gibt, ist selbst ein Befund – deshalb steht hier, was tatsächlich läuft:

| Signal | Wo es heute geprüft wird |
|---|---|
| T1 Pin-Ziel = Artikel-URL (nie /go/, nie Shortener) | `pinterest_check.py` P14 (Ziel gegen Live-SSOT) + `pinterest_link_guard.py` L1–L5 + Pin-Button-Layout |
| T2 Kein Meta-Refresh/JS-Redirect auf Artikeln | `pinterest_check.py` P10 (nur LIVE-Artikel; geparkt + erklärt ist Betriebszustand) + P14 |
| T3 max. 5 Affiliate-Links, nur /go/ + sponsored | `pinterest_check.py` P11 (Dichte) + P12 (Attribute) |
| T4 Werbekennzeichnung (`*Werbung \|`) | `pinterest_check.py` P4/P8, `spam_guard.py` B8 |
| T7 Cover 2:3 + pin_title/pin_description | `pinterest_check.py` P4, P4b, P5, P7 |
| T8 robots: Pinterestbot allow | `pinterest_check.py` P1 |
| T11 /go/* noindex | `pinterest_check.py` P13 |
| T12 p:domain_verify | `pinterest_check.py` P2 |
| T9 Rate-Limit (2–3 Pins/Lauf, ≥45 s) | `scripts/pinterest_engine.py` (`PINS_PRO_TAG`, `PIN_PAUSE_S`) |
| T10 RSS mit Cover-Enclosure | `layouts/rss.xml` (enclosure + media:content + media:thumbnail – Pinterest baut daraus Pins, deshalb ist die `pin_description` auch die Feed-Beschreibung) |
| T5 E-E-A-T (author + erfahrung), T6 interne Links | Template/Content-Gates (`layouts/`, `editorial_review_gate.py`, `internal_linker.py`) – nicht im Pinterest-Check |

Wer den Shield als eigenes Skript will, baut ihn auf dieser Liste als
**Bibliothek** neben `pinterest_check.py` – nicht als zweite Wahrheit daneben.
