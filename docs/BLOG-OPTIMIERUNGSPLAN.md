# 🚀 BLOG-OPTIMIERUNGSPLAN – FranksFinanzcheck

> **Stand:** 08.08.2026 · Letzte Aktualisierung nach Abschluss des Domain-Umzugs auf `franksfinanzcheck.de`
> Dieser Plan dokumentiert den aktuellen Zustand, was bereits auf Top-Level-Niveau umgesetzt ist und welche Punkte noch offen sind.

---

## ✅ 1. Technische Basis (alles erledigt)

| Bereich | Status | Details |
|---|---|---|
| **Eigene Domain** | ✅ LIVE | `https://franksfinanzcheck.de` (INWX-Registrierung, Cloudflare vorgeschaltet, apex als Hauptdomain) |
| **Hosting** | ✅ | GitHub Pages (Branch-Methode, `gh-pages`), Custom Domain per `CNAME`-Datei im Repo dauerhaft abgesichert |
| **CDN** | ✅ | Cloudflare (Proxy aktiv, globales Edge-CDN) |
| **HTTPS** | ✅ | Cloudflare-Zertifikat aktiv; GitHub-Origin-Zertifikat wird automatisch ausgestellt (→ dann SSL-Modus „Full (strict)" umstellen) |
| **Redirect** | ✅ | Alte `github.io`-URL leitet per 301 auf die neue Domain um (SEO-Signale wandern mit) |
| **Seitenstruktur** | ✅ | 38 Posts als Page-Bundles (`content/posts/<slug>/index.md`) + 6 Pillar-Pages (Themen-Cluster) |

## ✅ 2. Performance (Top-Level erreicht)

| Maßnahme | Status | Messwert |
|---|---|---|
| **LCP-Preload** (Cover-Bild `as=image` + `fetchpriority=high`) | ✅ live | LCP warm ~292 ms, kalt ~752 ms (Grün-Schwelle < 2,5 s) |
| **Font-Preloads** (Inter + Montserrat, first-party) | ✅ live | Starten parallel zum HTML |
| **Inter-Variable-Font** (1 Datei, 37,5 KB, subsettet) | ✅ | Body-Text ohne Google Fonts, keine Drittanbieter |
| **Cache-TTL 1 Jahr** | ✅ live | `cache-control: max-age=31536000` (Cloudflare Browser-TTL) – Lighthouse-Punkt grün |
| **Service Worker** | ✅ | Langzeit-Caching aller Assets; Wiederholungsbesuche 0 KiB Netzwerk |
| **0 Drittanbieter** | ✅ | Alle Fonts/Bilder first-party, kein externes CDN außer Cloudflare (eigene Infrastruktur) |
| **CLS 0 / TBT 0** | ✅ | Kein Layout-Shift, keine Blocking-Time |
| **Erzwungener Reflow eliminiert** | ✅ | Menü-Scroll-Restore erst nach `window.load` + `requestIdleCallback` |
| **LCP auf Mobile** | ✅ | Cover erscheint ÜBER dem Titel (kleine Viewports), immer im Viewport |
| **DOM-Größe** | ✅ | 259–459 Elemente pro Seite (Warnschwelle 1.400) – weit unter jeder Grenze |

## ✅ 3. Qualitäts-Gates (alles automatisiert, 100/100)

| Gate | Status | Wert |
|---|---|---|
| **Rechtschreibung** (Hunspell de_DE) | ✅ | 0 Funde (Whitelist gepflegt) |
| **Grammatik** (LanguageTool de-DE) | ✅ | 0 offene Funde (nur Stil-Hinweise) |
| **Lesbarkeit** (deutsche Amstad-Formel) | ✅ | Alle 38 Artikel ≥ 75, Ø 100 |
| **Meta-Qualität** (Titel/Description/Keywords) | ✅ | Ø Score 100/100, Ø Titel 55, Ø Desc 140 |
| **Profi-Text-Gate** (KI-Floskeln, Struktur, Keywords) | ✅ | 100/100 |
| **Einzigartigkeit** (Pin-Konflikt + interne Duplikate) | ✅ | bestanden |
| **Satzanfangs-Großschreibung** | ✅ | Deterministische Regeln (Absatzanfang, nach Satzende, nach Überschrift) mit Abkürzungs-/Marken-Schutz |
| **Tag-Schreibweise** | ✅ | `titleCaseStyle = "none"` + `normalize_tags()` für Bot-Artikel |

## ✅ 4. Automatisierung (vollständig widerstandsfähig)

| System | Status | Funktion |
|---|---|---|
| **Content-Bot** (`daily-content.yml`) | ✅ aktiv | 2×/Tag (08:10 + 19:40 MESZ) + Fallback-Crons; Phase-1-Commit (Artikel sofort live) → Phase-2-Qualität (weich) → Phase-3-Optimierung (Meta, Links, IndexNow) |
| **Tageslimit** | ✅ | 2 Posts/Tag (steuerbar auf 4 via Repository-Variable `MAX_ARTIKEL_PRO_TAG`) |
| **Selbstheilender Themenpool** | ✅ | 116+ Themen; KI generiert automatisch 16 neue, wenn < 8 frei |
| **Pre-Flight-Check** | ✅ | Prüft Syntax, API-Keys, Themenpool vor jedem Lauf |
| **Fehler-Isolation** | ✅ | Ein fehlerhaftes Thema stoppt nie den ganzen Lauf |
| **Bot-Watchdog** | ✅ täglich 10:30 | Prüft: Artikel < 30 h, Skript-Syntax, Live-Site, GitHub-TLS-Zertifikat (→ automatisches Issue) |
| **Fehler-Alerting** | ✅ | Erstellt bei jedem Workflow-Fehler automatisch ein GitHub-Issue |
| **Bot-Status-Dashboard** | ✅ | `BOT-STATUS.md` im Repo (Artikel heute, Themenpool, letzter Commit) |
| **Affiliate-Link-Checker** | ✅ | Prüft Deep-Links + Partner-IDs bei jedem Lauf, korrigiert automatisch |
| **Cover-Checker** | ✅ | Prüft alle 8 Cover-Varianten, zieht fehlende automatisch nach |
| **Concurrency-Sperre** | ✅ | Keine parallelen/nachgeholten Crons (kein git-push-Konflikt) |

## ✅ 5. SEO & Sichtbarkeit

| Maßnahme | Status |
|---|---|
| **Eigene Domain** | ✅ `franksfinanzcheck.de` (Domain-Autorität, Marken-URL) |
| **Themen-Cluster** (6 Pillar-Pages) | ✅ bidirektional verlinkt, automatisch gewartet |
| **Interne Verlinkung** | ✅ automatisch (Related-Posts, Pillar-Box, Cluster-Karten) |
| **Google Search Console** | ✅ Property + Sitemap eingereicht (Verifikationsdatei live) |
| **Bing Webmaster** | ✅ Meta-Tag verifiziert (`5079875E…`) + Sitemap eingereicht |
| **IndexNow** | ✅ 39 URLs unter neuer Domain eingereicht; neue Artikel automatisch |
| **Sitemap** | ✅ `https://franksfinanzcheck.de/sitemap.xml` (135 URLs, HTTP 200) |
| **Strukturierte Daten** | ✅ FAQ-Schema (Posts + Pillars), Person-Schema, WebSite-Schema |
| **E-E-A-T** | ✅ Autorenprofil, Erfahrungs-Marker, Trust-Box, „Über mich" |

## ⏳ 6. Noch offen (in Prioritätsreihenfolge)

| # | Punkt | Status | Aufwand |
|---|---|---|---|
| 1 | **Cloudflare SSL „Full (strict)"** | GitHub-Zertifikat noch nicht ausgestellt (Stand 08.08. abends) – Watchdog prüft täglich und meldet es per Issue, sobald da | 1 Min |
| 2 | **Pinterest-API-Token** | App beantragt; Token (`pina_…`) steht aus → dann Secret `PINTEREST_ACCESS_TOKEN` + Variable `PINTEREST_BOARD_ID` anlegen, `repin-weekly.yml` aktivieren | 10 Min (sobald Token da) |
| 3 | **4 Posts/Tag aktivieren** | Variable `MAX_ARTIKEL_PRO_TAG = "4"` in GitHub-Settings setzen (Zeitfenster stehen bereit) | 1 Min |
| 4 | **Google Search Console – Domain-Property** | Optional: zusätzlich Domain-Property (DNS-TXT bei Cloudflare) für bessere Abdeckung | 5 Min |
| 5 | **E-Mail auf eigener Domain** | Optional: `hallo@franksfinanzcheck.de` (dann MX/SPF bei Cloudflare anpassen – aktuell Null-MX) | je nach Anbieter |
| 6 | **alte `github.io`-Links in Artikeln** | Redirect läuft bereits; ggf. in einigen Monaten direkt auf neue Domain umschreiben | gering |

## 📈 7. Kennzahlen (aktuell)

| Kennzahl | Wert |
|---|---|
| Artikel gesamt | 38 (35 Seed + 3 Bot) |
| Posts pro Tag | 2 (Bot) |
| Pillar-Pages | 6 |
| Themenpool | 116+ (frei: ~75) |
| Tags | 81 (alle korrekt geschrieben) |
| Lighthouse Performance | 100 (Desktop) |
| LCP | ~0,3–0,8 s (warm/kalt) |
| Cache-TTL | 1 Jahr (Cloudflare) |
| Drittanbieter | 0 |
| Domain | `franksfinanzcheck.de` (Cloudflare vorgeschaltet) |

---

*Automatisch gepflegt – Stand 08.08.2026 · Bei größeren Änderungen aktualisieren.*

## 💡 8. Neue Optimierungsideen (Stand 08.08.2026)

### Schnell umsetzbar (je 5–15 Min)

| # | Idee | Warum | Aufwand |
|---|---|---|---|
| 1 | **AI Overviews / Featured-Snippets optimieren** | FAQ-Schema ist da – jetzt pro Artikel 1 knackige „Kurzantwort“ (2–3 Sätze) direkt unter der H2, die Google als Snippet übernehmen kann | 10 Min/Artikel |
| 2 | **Interne Verlinkung vertiefen** | `internal_linker.py --max 3` läuft – auf 5 erhöhen für noch mehr Topic-Signale (bei 38 Artikeln unkritisch) | 2 Min |
| 3 | **`lastmod`-Datum bei Updates** | Wöchentlicher SEO-Workflow aktualisiert Artikel – `lastmod` im Frontmatter setzen, damit Google das Update erkennt | 5 Min |
| 4 | **Alt-Texte der Covers prüfen** | Bot-Covers haben generische Alt-Texte („Spar-Tipp: …“) – durch keywordreiche, natürliche Alt-Texte ersetzen | 15 Min |
| 5 | **OG-Image je Artikel** | Beim Teilen auf WhatsApp/LinkedIn erscheint aktuell kein individuelles Vorschau-Bild – `og:image` pro Post setzen (Cover reicht) | 10 Min |

### Mittelfristig (je 1–3 h)

| # | Idee | Warum | Aufwand |
|---|---|---|---|
| 6 | **„Beste Angebote“-Infobox je Pillar** | Eine wiederkehrende Vergleichs-Box (aktueller Strom-/DSL-/Versicherungs-Tarif mit Affiliate-Link) erhöht Conversion & Verweildauer | 2 h |
| 7 | **E-Mail-Newsletter (alternativlos für Wiederkehr)** | Auch ohne eigenen Mailserver: kostenloser Anbieter (z. B. Buttondown/Beehiiv) mit „Neuer Artikel“-Benachrichtigung | 2 h |
| 8 | **Eigene Domain-E-Mail** | `hallo@franksfinanzcheck.de` (z. B. über Cloudflare Email Routing kostenlos) – seriöser für Backlink-Outreach | 30 Min |
| 9 | **YouTube/Short-Videos je Artikel** | 60-Sek-Video mit Kern-Tipps → Link im Artikel, neue Reichweite | je 1 h |
| 10 | **Backlink-Aufbau intensivieren** | `backlink_automation.py` liefert Prospects – monatlich 5 Gastbeiträge/Listen-Platzierungen anstreben (Domain-Autorität) | laufend |

### Strategisch (größere Projekte)

| # | Idee | Warum | Aufwand |
|---|---|---|---|
| 11 | **Eigene Domain-E-Mail + Google Workspace** | Maximale Seriosität für E-E-A-T & Outreach (statt Free-Mail im Impressum) | 1 Tag |
| 12 | **Umami-Selfhosting / Analytics-Ausbau** | Aktuell cookieless – mit Umami-Dashboard Conversion-Pfade (Affiliate-Klicks) messen | 1 Tag |
| 13 | **Mehrsprachigkeit (EN)** | Englische Version der Top-20-Artikel → internationaler Traffic (Nische „Frugalismus“ ist global) | groß |
| 14 | **Digitaler Produktverkauf** | Z. B. „Sparplan-Excel“ oder „CHECK24-Wechsel-Checkliste“ als PDF (5–15 €) – erste Monetarisierung unabhängig von Affiliate | 1–2 Tage |
| 15 | **Pinterest voll ausrollen** | 73-Pin-Plan liegt bereit – sobald API-Token da: automatisierte Pins, Board-Strategie, Pin-Optimierung nach Impressions | laufend |

### Kontinuierliche Qualitäts-Schleife (bereits aktiv, ausbauen)

- **Monatliches Content-Audit:** Älteste 5 Artikel nach 6 Monaten aktualisieren (Zahlen, Links, Screenshots) → `lastmod`-Signal
- **Quartalsweises Keyword-Refresh:** `keyword_optimizer.py` auf die 10 wichtigsten Seiten anwenden
- **Saisonale Inhalte:** 4 Wochen VOR Saisonstart (Heizperiode: August, Steuererklärung: Januar) publizieren

---

*Dokument wird bei größeren Änderungen aktualisiert – Stand 08.08.2026 (abends).*
