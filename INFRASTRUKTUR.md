# 🏗️ INFRASTRUKTUR – FranksFinanzcheck (maßgebliche Referenz für FrankAutoOps)

**Stand:** 10.08.2026 · **Gültig für:** alle Automatisierungen (FrankAutoOps, Content-Engine, Layout-AI, Watchdog, Reports)

> ⚠️ **WICHTIG:** Der Blog läuft auf **GitHub Pages + Cloudflare-Proxy (DNS)**.
> **NICHT** Cloudflare Pages, **NICHT** Cloudflare Workers. Automatisierungen
> und Reports müssen diese reale Architektur abbilden – kein Umzug geplant
> (unnötiges Risiko, aktuelle Lösung ist stabil und kostenlos).

---

## 1. Architektur-Überblick

```
Browser/Nutzer
   │  https://franksfinanzcheck.de
   ▼
Cloudflare (DNS + Proxy, SSL „Full")
   │  A-Records: 185.199.108-111.153 (GitHub Pages)
   │  Cache: HTML dynamisch, Assets 1 Jahr (Browser-TTL)
   ▼
GitHub Pages (Hosting)
   │  Branch: gh-pages (wird von deploy.yml gebaut & gepusht)
   │  Custom Domain: franksfinanzcheck.de (CNAME-Datei + API gesetzt)
   ▼
GitHub Repo frank-hartung/franksfinanzcheck-blog (main = Quelle)
```

| Ebene | Technologie | Rolle |
|---|---|---|
| DNS | Cloudflare (Nameserver damian/sloan.ns.cloudflare.com) | Domain-Auflösung |
| Proxy/CDN | Cloudflare-Proxy (Orange Cloud) | SSL, DDoS-Schutz, Edge-Cache |
| **Hosting** | **GitHub Pages** (Branch `gh-pages`) | Statische Auslieferung, global via Fastly |
| Quellcode | GitHub Repo (`main`) | Build-Quelle, Automatisierung |
| Backup | Objektspeicher (S3-kompatibel) | **Geplant, noch nicht eingerichtet** |

---

## 2. Deploy-Pipeline (real, funktionsfähig)

```
Push auf main
   → deploy.yml („Deploy auf GitHub Pages")
       1) Hugo v0.164 extended bauen (HUGO_JSDELIVR_SHA=<sha> als Cache-Buster)
       2) peaceiris/actions-gh-pages → gh-pages-Branch pushen
   → GitHub Pages veröffentlicht (Custom Domain bleibt via CNAME gesetzt)
   → Content-Bot stößt Deploy zusätzlich per workflow_dispatch an
     (GITHUB_TOKEN triggert keine neuen Workflows – deshalb expliziter Dispatch)
```

**Konsequenzen für Automation:**
- **Kein Cloudflare Pages Build, keine Workers** – Deploy-Trigger nur über GitHub.
- **Cache-Buster `?v=<sha>`** ist die primäre Cache-Invalidierung. Assets (Bilder,
  Fonts, CSS) werden mit `max-age=31536000` (1 Jahr) ausgeliefert; neue Deploys
  erzeugen neue URLs → sofort frischer Content. **Kein Cache-Purge nötig.**
- **HTML-Seiten** werden von Cloudflare als `DYNAMIC` behandelt (10-min-GitHub-TTL)
  → Änderungen sind nach Deploy + kurzer Wartezeit live.
- **SSL-Modus Cloudflare:** „Full" (aktuell korrekt – GitHub liefert Wildcard
  `*.github.io`). Sobald das GitHub-TLS-Zertifikat für franksfinanzcheck.de
  ausgestellt ist (SAN enthält die Domain), stellt der Bot-Watchdog (Check 4)
  automatisch ein Issue → dann manuell/API auf **„Full (strict)"** umstellen.

---

## 3. Cache-Matrix (real gemessen)

| Ressource | Cache-Header | Invalidierung |
|---|---|---|
| HTML (/, /posts/*) | `max-age=600` (GitHub Pages), Cloudflare DYNAMIC | Sofort nach Deploy |
| Bilder/Covers (JPG/WebP/AVIF) | `max-age=31536000` | `?v=<deploy-sha>` |
| Fonts (woff2) | `max-age=31536000` | `?v=<deploy-sha>` |
| CSS/JS (inline/minifiziert) | im HTML eingebettet | Mit HTML-Deploy |

**Regel für Automationen:** Nach jedem Deploy NIE Cache-Purge anstoßen –
der `?v=`-Buster (HUGO_JSDELIVR_SHA) erledigt die Invalidierung automatisch.
Ein Purge wäre nur nötig, wenn ohne SHA-Buster deployed würde (nie).

---

## 4. Was FrankAutoOps daraus ableitet (verbindlich)

1. **Hosting-Status:** `github-pages` (Branch gh-pages), **nicht** `cloudflare-pages`.
2. **Deploy-Trigger:** Nur GitHub (push/workflow_dispatch) – keine CF-Webhooks nötig.
3. **Cache-Aktionen:** Kein `cache.purge` – Buster-basiert. Falls ein Tool
   Cloudflare-API-Purge anbietet → deaktiviert lassen.
4. **SSL-Automation:** „Full" bis Watchdog-Issue → dann Umstellung auf
   „Full (strict)" (manuell 1 Min oder per Cloudflare-API mit Token).
5. **Backup:** GitHub-Repo ist bereits Offsite-Backup (Code+Content+History).
   Zusätzlich geplant: täglicher Export (public/ + content/) auf S3-kompatiblen
   Objektstore (Workflow vorbereitet, Credentials fehlen).
6. **Monitoring:** Uptime-Checks gegen `https://franksfinanzcheck.de` (über
   Cloudflare-Proxy) + `https://frank-hartung.github.io/franksfinanzcheck-blog/`
   (Origin, ohne Proxy) – so wird zwischen CF- und Origin-Problemen unterschieden.

---

## 5. Verifikations-Checks (immer wieder ausführen)

```bash
# 1) Live-Domain (via Cloudflare)
curl -sI https://franksfinanzcheck.de | grep -iE "server|cf-cache-status"

# 2) Origin (GitHub Pages, ohne Proxy – sollte 301 auf Custom Domain)
curl -sI https://frank-hartung.github.io/franksfinanzcheck-blog/ | grep -iE "^HTTP|location"

# 3) HTTPS-Redirect (http → https, Cloudflare „Always Use HTTPS")
curl -sI http://franksfinanzcheck.de | grep -iE "^HTTP|location"

# 4) Cache-Buster aktiv
curl -s https://franksfinanzcheck.de/ | grep -o "v=[a-f0-9]\{7\}" | head -1
```

---

## 6. Workspace-Budget & Frühwarnsystem (verbindlich)

**Problem:** Die Agent-Sandbox hat ein hartes Snapshot-Limit von **128 MB / 10.000
Dateien**. Überschreitungen führen zu nicht gespeicherten Dateien. Haupttreiber:
`public/` (Hugo-Build, 41 MB), `.git` (51 MB, Cover-History), `static/` (23 MB Covers).

**Lösung – zweistufig:**

```bash
# 1) LOKALER GUARD (Sandbox-Budget, misst /home/user) – am Ende jeder Sitzung:
python3 scripts/workspace_guard.py            # prüfen + automatisch aufräumen
python3 scripts/workspace_guard.py --force    # Stufe-1-Cleanup erzwingen
python3 scripts/workspace_guard.py --json     # Maschinenstatus

# 2) REMOTE-WATCHDOG (Repo-Größe, GitHub Actions):
#    .github/workflows/workspace-watchdog.yml – bei jedem Push + täglich 06:00 UTC
#    > 150 MB → Warning-Annotation · > 250 MB → Error/Exit 1
```

**Guard-Schwellwerte (MB / Dateien):** GRÜN < 80 / 6.000 · GELB ≥ 80 / 6.000 ·
ROT ≥ 95 / 8.000 (Stufe 1: `public/`, `__pycache__`, Caches, Audit-Retention,
`git gc --prune=now --aggressive`) · KRITISCH ≥ 115 / 9.500 (Stufe 2: zusätzlich
`/tmp`-Artefakte + Snapshot-exkludierte Ordner). Status: `data/workspace_guard.json`.

**Regeln für Agent-Sitzungen:**
- `public/` nach Builds NICHT liegen lassen – Guard löscht es (gitignored, neu baubar).
- Bei „Workspace over budget“-Meldung: `python3 scripts/workspace_guard.py --force`
  als ERSTE Aktion, dann Ursache prüfen (was ist neu gewachsen?).
- `uploads/` (11 MB Referenzmaterial) und `static/` (Covers) NICHT löschen.
- Der Remote-Watchdog warnt nur – Aufräumen der Repo-History ist manuell
  (`git gc`, alte Branches) und nur mit Bedacht (kein Force-Push ohne Grund).

## 7. Offsite-Backup & Uptime-Monitor (kostenlos, 12.08.2026)

**Offsite-Backup** (`.github/workflows/backup-offsite.yml`):
- Täglich 03:00 UTC + manuell (workflow_dispatch) → GitHub-Release `backup-YYYYMMDD-HHMM`
- Enthält `backup.bundle` (komplette Git-History) + `worktree.zip` (Arbeitskopie)
- Die letzten 14 Backups bleiben, ältere werden automatisch gelöscht
- Rollback: Release-Asset herunterladen → `git clone backup.bundle` bzw. Zip entpacken
- Kosten: 0 € (GitHub Free, Releases unbegrenzt)

**Uptime-Monitor** (`.github/workflows/uptime-monitor.yml`):
- Alle 15 Minuten: prüft `/`, `/posts/`, `/pillar/` auf HTTP 200 + Inhalt („FranksFinanzcheck")
- Ausfall → automatisches Issue (Label `uptime`), Wiederherstellung → Issue wird geschlossen;
  wiederholte Ausfälle ergänzen Kommentare
- Benachrichtigung: GitHub-Issue-Notification (E-Mail) an den Account-Inhaber
- Kosten: 0 € (öffentliches Repo → unbegrenzte Actions-Minuten)

**Manuell testen:**
```bash
# Backup sofort auslösen
gh workflow run backup-offsite.yml -R frank-hartung/franksfinanzcheck-blog
# Uptime sofort prüfen
gh workflow run uptime-monitor.yml -R frank-hartung/franksfinanzcheck-blog
# Backups auflisten
gh release list -R frank-hartung/franksfinanzcheck-blog
```

## 8. Pinterest-Profi-Signale & Watchdog (12.08.2026)

**Pinterest-Check mit Selbstheilung + Sabotage-Schutz** (scripts/pinterest_check.py):
- P1 robots.txt (Pinterest erlaubt) · P2 p:domain_verify · P3 Pin-Button je Artikel
- P4 Description einzigartig/≤500 Zeichen/keine Schablone · P5 Media erreichbar
- P6 Rich-Pin-Meta (og:type/title/description/image/url) · P7 og:image:width/height
- P8 Hashtags sauber (max. 3, keine Umlaute) · P9 Profil-Link
- SELBSTTEST läuft VOR jeder Fix-Aktion (Exit 2 = nichts verändert – Sabotage-Schutz)
- Report: PINTEREST-REPORT.md · Audit-Log

**Watchdog** (.github/workflows/pinterest-watchdog.yml): täglich 05:30 UTC + manuell,
baut die Site, läuft `pinterest_check.py --fix`, committet den Report, eröffnet/
schließt automatisch ein Issue (Label `pinterest`) bei Problemen.

**Lokal:**
```bash
python3 scripts/pinterest_check.py          # nur prüfen
python3 scripts/pinterest_check.py --fix    # selbstheilend
```

---

*Diese Datei ist die maßgebliche Referenz. Änderungen an der Infrastruktur
müssen hier dokumentiert werden (Audit-Pflicht).*
