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
| Die gepinnte URL leitet selbst weiter (Meta-Refresh) | niedrig | ausgeschlossen – Artikel liefern direkt aus (Check P10) |
| Zu viele Affiliate-Links / unmarkierte Affiliate-Links | niedrig | im Griff: max. 4/Artikel, `rel="sponsored nofollow"` (P11/P12) |
| Blockierte Affiliate-Domain als Pin-Ziel | niedrig | Pins zeigen auf Artikel, nicht auf /go/ |

**Unsere technischen Checks (automatisiert, `pinterest_check.py`):**
- P10: Artikel-Seiten haben KEINEN eigenen Redirect ✅
- P11: max. 5 Affiliate-Links pro Artikel ✅
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
  05:30 UTC – baut die Site, läuft `pinterest_check.py --fix` (13 Checks),
  committet PINTEREST-REPORT.md, öffnet bei Problemen ein Issue (Label `pinterest`).
- **Lokal:** `python3 scripts/pinterest_check.py` (Check) / `--fix` (Selbstheilung)

---

*Ergänzt am 12.08.2026 · Teil der FrankAutoOps-Dokumentation.*

## 6. Trust-Shield (automatisch, Stand 24.08.2026)

`python3 scripts/pinterest_trust_shield.py --fix` prüft und heilt 12 Anti-Spam-Signale:

| Code | Signal |
|---|---|
| T1 | Pin-Ziel = Artikel-URL (nie /go/, nie Shortener) |
| T2 | Kein Meta-Refresh/JS-Redirect auf Artikeln |
| T3 | max. 5 Affiliate-Links, nur über /go/ + sponsored |
| T4 | Werbekennzeichnung (*Werbung \| in pin_description) |
| T5 | E-E-A-T: author + erfahrung |
| T6 | ≥2 interne Links, keine dünnen Seiten |
| T7 | Cover 2:3 + pin_title/pin_description |
| T8 | robots: Pinterestbot Allow, /go/ Disallow |
| T9 | Rate-Limit max. 2–3 Pins/Lauf, ≥45 s Pause |
| T10 | RSS mit Cover-Enclosure (Auto-Publish) |
| T11 | /go/* noindex |
| T12 | p:domain_verify |

Report: `PINTEREST-TRUST-REPORT.md`. Läuft im Pinterest-Watchdog (vor Hugo-Build).
