# 🛡️ PINTEREST-TRUST-REPORT (Anti-Spam / Domain-Vertrauen)

**Stand:** 2026-08-31 15:34 UTC · **Modus:** CHECK

Probleme: **2** · Geheilt: **0**

## Warum Pinterest Domains als Spam einstuft (2026)

1. **Redirect-Ketten** (Meta-Refresh, Shortener, Tracking-Hops)
2. **Affiliate-Landingpages** als Pin-Ziel (/go/, a.check24.net)
3. **Pin-Flooding** (viele Pins in kurzer Zeit, gleiche URL)
4. **Fehlende Domain-Verifikation** / Rich-Pin-Meta
5. **Dünne/duplicate Seiten**, unmarkierte Werbung
6. **SSL/Hosting-Reputation**, Safe-Browsing-Flags

## Was dieser Blog technisch absichert

| Signal | Status | Mechanik |
|---|---|---|
| Pin-Ziel = Artikel-URL | T1 | Engine-Guard, nie /go/ |
| Kein Artikel-Redirect | T2 | Check + Publish-Gate |
| Affiliate nur /go/ + sponsored | T3 | affiliate_shield + render-hook |
| Werbekennzeichnung | T4 | pin_description + Trust-Box |
| E-E-A-T (Autor/Erfahrung) | T5 | Frontmatter + Person-Schema |
| Interne Verlinkung | T6 | internal_linker |
| Cover 2:3 + Pin-SEO | T7 | pinterest_seo_healer |
| robots: Pinterestbot, /go/ block | T8 | layouts/robots.txt |
| Rate-Limit 2–3 Pins, ≥45 s | T9 | pinterest_engine |
| RSS mit Cover (Auto-Publish) | T10 | layouts/_default/rss.xml |
| /go/ noindex | T11 | static/go/*/index.html |
| Domain-Verify Meta | T12 | hugo.toml pinterestVerify |

## Offene Punkte

| Code | Artikel | Problem |
|---|---|---|
| T9 | - | Pinterest-Engine ohne sicheres Rate-Limit (Flooding-Risiko) |
| T9 | - | keine Pause zwischen Pins (Spam-Muster) |

## Manuelle Schritte (einmalig, Business-Konto)

1. **Website beanspruchen** (falls abgelaufen): Pinterest Business → Einstellungen → Beanspruchte Konten → franksfinanzcheck.de
2. **URL-Debugger**: https://developers.pinterest.com/tools/url-debugger/ → 2–3 Artikel-URLs prüfen → „Apply for Rich Pins“
3. **Sitemap**: `https://franksfinanzcheck.de/sitemap.xml` im Business-Konto hinterlegen
4. **Bei Sperre**: 48 h Pause, dann Support unter „Pins erstellen/bearbeiten“ (nicht „Domain blockiert“) – siehe `docs/PINTEREST-SPIELBUCH.md`
5. **Pin-Verhalten**: max. 2–3 Pins/Tag, Abstand ≥1–2 h, nie dieselbe URL am selben Tag

---
*Erzeugt von `scripts/pinterest_trust_shield.py` – FrankAutoOps Anti-Spam.*
