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
| 1 | **Cloudflare SSL „Full (strict)"** | Sobald GitHub das TLS-Zertifikat ausstellt (automatisch, Watchdog meldet es per Issue) | 1 Min |
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

---

*Automatisch gepflegt – Stand 08.08.2026 · Bei größeren Änderungen aktualisieren.*
