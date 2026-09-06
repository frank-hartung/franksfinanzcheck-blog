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

## 6. Rechts-Fristen-Erinnerungssystem (30.08.2026)

```
data/recht-fristen.yaml          # Fristen-Kalender (redaktionell gepflegt)
data/fristen_state.json          # Erledigungen + Issue-/Eskalations-Marker (Bot)
scripts/fristen_check.py         # Auswertung + Scan + Eskalation
.github/workflows/fristen-check.yml   # täglich 07:55 MESZ – LIEGT ALS PATCH BEREIT:
patches/fristen-check-2026-08-30-workflows.patch  # (Agent-Token ohne workflows-Scope;
                                   #  einmalig anwenden + committen, dann aktiv)
FRISTEN-REPORT.md                # generierter Status-Report
```

- **Fristen:** Rechtstexte-Halbjahrescheck (Generator-Abgleich eRecht24 Basis /
  Dr. Schwenke), KI-VO-Kennzeichnung Bestandssysteme (02.12.2026),
  DPF-Zertifikats-Check GitHub/Cloudflare (quartalsweise),
  Affiliate-Partnerbedingungen (quartalsweise), Rechtslage-Screening
  (quartalsweise), BFSG-Scope-Bewertung (einmalig).
- **Eskalation:** GitHub-Issues, Label `frist` (Erinnerung, ab konfigurierter
  Fälligkeits-Nähe) → `frist-eskalation` (am Stichtag, +14 Tage, +30 Tage –
  jeweils genau ein Kommentar, Marker im State-File).
- **Sofort-Prüfungen täglich:** Veraltungs-Scan der Live-Verzeichnisse
  (content/, layouts/, static/) nach TMG/TTDSG/OS-Plattform/Privacy-Shield/
  Safe-Harbor-Resten (Fund = hartes Eskalations-Issue) + Stand-Alter der
  Rechtstexte (max. 365 Tage).
- **Erledigen:** Workflow „Fristen-Check (Recht)" manuell starten mit
  `erledigt=<frist-id>` → Frist neu terminiert, Issue geschlossen.
  (Nur Issue schließen genügt nicht – Bot legt sonst neu an, gewollt.)
- **Fail-Safety:** Der Workflow selbst steht in der zentralen
  Fehler-Alerting-Liste (alert-on-failure.yml). Fristen-Überschreitung
  erzeugt bewusst KEINEN roten Run, sondern eigene Issues (klare Trennung
  Technik-Fehler vs. fachliche Frist).
- **Doku:** Abgleich-Historie der Rechtstexte: `RECHT-UPDATE-REPORT.md`.

---

*Diese Datei ist die maßgebliche Referenz. Änderungen an der Infrastruktur
müssen hier dokumentiert werden (Audit-Pflicht).*
