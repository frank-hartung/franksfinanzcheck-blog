# Umami-Analytics-Aktivierung — Schritt-für-Schritt-Anleitung

> **Stand:** 26.10.2026 · **Zweck:** Umami-Tracking auf `stats.franksfinanzcheck.de` aktivieren,
> ohne API-Kosten. Das Tracking-Skript (`umami.js`) ist kostenlos; der API-Zugang ist es nicht.
> **Voraussetzungen:** Cloudflare-Account mit Zone `franksfinanzcheck.de`, Domain `stats.franksfinanzcheck.de`
> als Cloudflare-Proxy (orange Wolke), API-Token mit Worker-/D1-Rechten.

---

## 0. Warum Umami und nicht etwas anderes

| Option | Kosten | DSGVO | Eigenhosting | Notes |
|--------|--------|-------|-------------|-------|
| Umami self-hosted (Open Source) | **0 €** | ✅ cookiefrei | ✅ Docker/node | Das, was dieses Projekt nutzt |
| Umami Cloud (umami.is) | kostenpflichtig | ✅ | ❌ SaaS | API-Funktionen kostenpflichtig |
| Cloudflare Web Analytics | **0 €** | ✅ | ❌ (Cloudflare-eigen) | Alternative, wenn Umami nicht gewünscht |
| Google Analytics 4 | **0 €** | ⚠️ (Cookies) | ❌ | Nicht DSGVO-optimal ohne Konsent |

**Entscheidung:** Umami self-hosted auf `stats.franksfinanzcheck.de` — Tracking-Skript ohne API-Zugang.

---

## 1. Was 설치t werden muss (Server-Infrastruktur)

Umami selbst gehostet benötigt:

- Einen Server mit Node.js ≥ 18 (oder Docker)
- Eine Postgres-Datenbank (oder SQLite für kleine Seiten)
- Das Umami-Applikationspaket

**Option A — Docker (einfachste Variante, empfohlen):**

```bash
# Server ssh'en (z.B. Hetzner, DigitalOcean, eigener VPS)
ssh user@dein-server

# Umami mit Docker Compose installieren:
mkdir -p ~/umami && cd ~/umami

cat > docker-compose.yml << 'EOF'
version: '3.8'
services:
  umami:
    image: umami/umami:latest
    ports:
      - "127.0.0.1:3000:3000"
    environment:
      DATABASE_URL: postgresql://umami:GEHEIMPASSWORT@db:5432/umami
    depends_on:
      - db
  db:
    image: postgres:15-alpine
    environment:
      POSTGRES_USER: umami
      POSTGRES_PASSWORD: GEHEIMPASSWORT
      POSTGRES_DB: umami
    volumes:
      - umami-db-data:/var/lib/postgresql/data
volumes:
  umami-db-data:
EOF

docker compose up -d
```

Danach: Umami Web-UI unter `http://localhost:3000` aufrufen, Website erstellen, Website-ID kopieren.

**Option B — Cloudflare Worker (serverlos, ohne Docker):**

> ⚠️ Umami ist primär als Node.js/Postgres-Anwendung ausgelegt. Ein Betrieb als Cloudflare Worker
> erfordert eine Next.js-basierte Anpassung mit Cloudflare-Adapter. Das ist aufwändiger.
> Für einen schnellen Start: **Option A (Docker auf VPS)**.

---

## 2. Umami hinter Cloudflare-Proxy betreiben

Damit das Tracking-Skript `https://stats.franksfinanzcheck.de/umami.js` lädt und die
Datenerfassung über die eigene Domain läuft:

1. Im Cloudflare Dashboard → DNS → Record für `stats.franksfinanzcheck.de`:
   - Type: A (oder CNAME)
   - Content: IP des Servers (oder Domain des VPS)
   - Proxy status: **Proxied** (orange Wolke)

2. SSL/TLS Mode: **Full (strict)** oder **Full**

3. Umami-URL für das Skript:
   - Domain: `https://stats.franksfinanzcheck.de`
   - Skript-Pfad: `/umami.js`
   - Die Umami-Instanz liefert dieses Skript aus (wird von Umami mitgeliefert)

---

## 3. Website-ID in hugo.toml eintragen

Nach Umami-Installation und Website-Erstellung (in der Umami Web-UI):

1. Website-ID notieren (z.B. `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
2. In `hugo.toml` eintragen:

```toml
[params.analytics.umami]
  website = "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"  # <-- hier einfügen
  domain  = "stats.franksfinanzcheck.de"
```

**Ohne diesen Eintrag:** Das Skript wird nicht geladen (bereits in `umami.html` kodiert).

---

## 4. CSP-Anpassung (falls nötig)

In `cloudflare/edge-schutz.md` A1 (Header-Regel `FF Sicherheits-Header`) ist die CSP:

```
Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com; ...
```

Das Tracking-Skript lädt von `stats.franksfinanzcheck.de` — das ist **self** (gleiche Domain).
Es wird **kein** externes Skript von einem Drittanbieter geladen. **Keine CSP-Anpassung nötig.**

Falls Umami auf einem anderen Server gehostet wird (z.B. `umami.example.com`):
```
script-src 'self' https://challenges.cloudflare.com https://umami.example.com
```

---

## 5. Datenschutz-Text (bereits in datenschutz/index.md ergänzt)

Der Datenschutz-Text in `content/datenschutz/index.md` wurde bereits am 26.10.2026 ergänzt:
- Abschnitt 1: Beschreibung des Tracking-Skripts (kostenlos, ohne API)
- Abschnitt 2 Tabelle: Zeile „Cookielose Analytics (Umami, Tracking-Skript, nach Activation)" + Zeile „Umami Dashboard-API (nicht genutzt)"

**Kein Consent-Popup nötig** — Umami ohne Cookies, ohne IP-Speicherung.

---

## 6. Test nach Aktivierung

Nach Eintrag der Website-ID in `hugo.toml` und Deploy:

1. Hugo-Build: `hugo --minify` (oder Deploy über GitHub Actions)
2. Seite aufrufen: `https://franksfinanzcheck.de/`
3. In den Browser-Entwickler-Tools (Netzwerk-Tab): prüfen, ob `https://stats.franksfinanzcheck.de/umami.js` geladen wird
4. In Umami Dashboard: erste Pageview sollte innerhalb von 1–2 Minuten erscheinen

**Automatische Prüfung (nach Deploy):**
```bash
# Skript prüft, ob Skript geladen wird (nach Deploy auf main)
curl -sI https://franksfinanzcheck.de/ | grep -i "umami"
# oder im Browser:
open https://franksfinanzcheck.de/
# → Network-Tab: umami.js aufrufen?
```

---

## 7. Kosten im Überblick

| Position | Kosten |
|---------|--------|
| Umami Software (Open Source) | **0 €** |
| Umami Tracking-Skript (Client) | **0 €** |
| Umami Dashboard-API | **0 €** (nicht genutzt) |
| Server (VPS für Umami-Docker) | ca. 3–6 €/Monat (Hetzner CPX11 etc.) |
| Cloudflare Proxy (stats.franksfinanzcheck.de) | **0 €** (bereits vorhanden) |
| Postgres Datenbank (in Docker auf VPS) | **0 €** (auf VPS, keine externe DB) |

**Gesamtkosten:** Nur VPS-Kosten (3–6 €/Monat). Keine API-Gebühren, keine SaaS-Gebühren.

---

## 8. Was nicht gemacht wird (und warum)

| Vermeideter Schritt | Grund |
|-------------------|-------|
| Umami API-Token in hugo.toml | Kostenpflichtig (Pro-Funktion), nicht nötig für Tracking |
| Umami Cloud (umami.is) | Kostenpflichtig |
| Automatisierte Datenimporte per API | Kostenpflichtig |
| Google Analytics 4 | Cookies → DSGVO-Komplexität |

---

## 9. Wenn Umami nicht verfügbar sein sollte (Fallback)

Falls Umami nicht deployed werden kann (kein Server, keine Zeit), ist die Alternative:

**Cloudflare Web Analytics** — ebenfalls kostenlos, ebenfalls DSGVO-konform (kein Cookie).
Aktivierung: Cloudflare Dashboard → Analytics → Web Analytics → Website hinzufügen →
Website-ID notieren → in hugo.toml eintragen (ähnlicher Aufbau wie Umami).

Code-Fragment (ähnlich Umami, für Cloudflare Web Analytics):
```html
<script>
  (function(){
    var d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
    g.async = true; g.src = 'https://static.cloudflareinsights.com/beacon.min.js';
    g.dataset.cfBeacon = '{"token": "CLOUDFLARE-WEB-ANALYTICS-TOKEN"}';
    s.parentNode.insertBefore(g, s);
  })();
</script>
```

**Empfehlung:** Umami self-hosted, solange ein VPS verfügbar ist. Cloudflare Web Analytics
nur als Fallback, wenn kein Server zur Verfügung steht.

---

**Erstellt:** 26.10.2026 · **Zusammen mit PR #890** · **Verantwortlich:** Frank Hartung

---

## 10. Cloudflare Web Analytics als Alternative (ohne Server)

Falls kein VPS zur Verfügung steht, ist **Cloudflare Web Analytics** die Alternative.
Kostenlos, DSGVO-konform (kein Cookie), kein eigenes Hosting, kein API-Zugang.

### ZWEI WEGE (wahlweise, nicht kombiniert)

Cloudflare Web Analytics unterstützt zwei Einbindungswege. Der automatische Weg (A) ist
empfohlen — kein Code-Aufwand, keine hugo.toml-Änderung nötig.

#### Weg A — Automatisch (empfohlen)

Cloudflare injiziert das Skript (`beacon.min.js`) automatisch über die Edge-Infrastruktur
in jede Seite auf der Domain. Das automatische Injecting ist die Standard-Methode von
Cloudflare Web Analytics.

1. **Cloudflare Dashboard öffnen** (cloudflare.com → Anmelden → franksFinanzcheck.de auswählen)
2. **Navigation:** Analytics → Web Analytics → „Website hinzufügen"
3. **Website-URL eingeben:** `https://franksfinanzcheck.de`
4. **Aktivierung** → Cloudflare injiziert das Skript automatisch in alle Seiten
5. **Test:** Seite aufrufen, Browser-Entwickler-Tools → Netzwerk → prüfen ob
   `static.cloudflareinsights.com/beacon.min.js` geladen wird

**Vorteile Weg A:**
- Kein Code-Aufwand (kein hugo.toml-Eintrag, kein Partial-Nutzung)
- Kein Deploy nötig nach Aktivierung
- Sofort einsatzbereit nach Dashboard-Aktivierung
- Automatisches Injecting über Cloudflare Edge

**Nachteile Weg A:**
- Kein separates Dashboard nur für Analytics (nur Cloudflare Analytics Dashboard)
- Keine explizite Kontrolle über den Einbindungspunkt im HTML

#### Weg B — Manuell (fallback, optional)

Das Skript wird beim Hugo-Build über das Partial `cloudflare_analytics.html` eingebunden.
Voraussetzung: Website-ID + Beacon-Token aus Cloudflare Dashboard in `hugo.toml` eintragen.

1. **Cloudflare Dashboard öffnen** (wie Weg A)
2. **Analytics → Web Analytics → Website hinzufügen**
3. **Website-ID und Token notieren** (aus der Website-Konfiguration im Dashboard)
4. **In hugo.toml eintragen:**

   ```toml
   [params.analytics.cloudflare]
     mode    = "manual"                          # manuellen Weg aktivieren
     website = "NOTIERTE-WEBSITE-ID"             # aus Dashboard
     token   = "NOTIERTER-BEACON-TOKEN"         # aus Dashboard
     domain  = "franksfinanzcheck.de"
   ```

5. **Deploy** (GitHub Actions oder lokal: `hugo --minify`)
6. **Test:** Seite aufrufen, Browser-Entwickler-Tools → Netzwerk → prüfen ob
   `static.cloudflareinsights.com/beacon.min.js` geladen wird

**Vorteile Weg B:**
- Vollständige Kontrolle über den Einbindungspunkt im HTML
- Optional: Token im Code (für Debugging, Audit)
- Funktioniert auch, wenn das automatische Injecting nicht verfügbar ist

**Nachteile Weg B:**
- Code-Aufwand (hugo.toml-Eintrag, Partial muss geladen werden)
- Deploy nach Konfigurationsänderung nötig
- Website-ID + Token manuell in hugo.toml pflegen

### Keine API-Kosten

Cloudflare Web Analytics hat **keine API-Gebühren**. Das Beacon-Skript sendet Daten an
Cloudflare-Infrastruktur. Es gibt kein API-Token für Reports (im Gegensatz zu Umami-API).
Das gilt für beide Wege (A und B).

### Was nicht funktioniert ohne Cloudflare Dashboard-Zugang

Ohne Login in cloudflare.com (Dashboard-Zugang) kann weder Weg A noch Weg B aktiviert werden:
- Weg A: Braucht Dashboard für Aktivierung + automatisches Injecting
- Weg B: Braucht Dashboard für Website-ID + Token

Das ist eine Außenwirkung wie der Cloudflare-Proxy.

### Vergleich Umami vs. Cloudflare Web Analytics

| Kriterium | Umami (self-hosted) | Cloudflare Web Analytics |
|-----------|---------------------|--------------------------|
| Kosten | 0 € (Software) + VPS-Kosten (~3-6 €/Monat) | 0 € |
| Server erforderlich | Ja (Docker auf VPS) | Nein |
| Eigenes Hosting | Ja (stats.franksfinanzcheck.de) | Nein (Cloudflare-Infrastruktur) |
| Dashboard | Ja (eigenes Umami Dashboard) | Ja (Cloudflare Dashboard) |
| API für Reports | Nein (kostenpflichtig, nicht genutzt) | Nein (nicht nötig) |
| DSGVO | ✅ cookiefrei | ✅ cookiefrei |
| Domain für Skript | stats.franksfinanzcheck.de | static.cloudflareinsights.com |
| Einrichtungsaufwand | Mittel (Docker + Postgres) | Gering (Dashboard-Klick, Weg A) |
| Code-Aufwand | Kein (automatisches Injecting möglich) | Minimal (Weg A, Standard) / Mittel (Weg B) |

**Empfehlung:** Cloudflare Web Analytics (Weg A, automatisch) ist die beste Wahl für
diesen Blog, weil kein VPS erforderlich ist und das automatische Injecting den
Code-Aufwand auf null reduziert. Umami self-hosted ist die bessere Wahl, wenn ein VPS
verfügbar ist und eigenes Dashboard bevorzugt wird.

### Code-Fragment (für Weg B, bereits in cloudflare_analytics.html)

```html
<script>
  (function() {
    var d = document, g = d.createElement('script'), s = d.getElementsByTagName('script')[0];
    g.async = true; g.src = 'https://static.cloudflareinsights.com/beacon.min.js';
    g.dataset.cfBeacon = '{"token": "WEBSEITE-TOKEN-AUS-DASHBOARD"}';
    s.parentNode.insertBefore(g, s);
  })();
</script>
```

Das Fragment in `cloudflare_analytics.html` ist identisch, aber mit Hugo-Template-Variablen:
- `site.Params.analytics.cloudflare.token` → Token-Platzhalter
- Das Skript wird **nur geladen, wenn** `mode = "manual"` UND `token` gesetzt ist

---

### Zusammenfassung: Was im Repo vorbereitet ist

| Komponente | Status | Bedeutung |
|-----------|--------|-----------|
| `cloudflare_analytics.html` | ✅ Erstellt | Manual-Einbindung (Weg B), nur aktiv wenn mode="manual" + token gesetzt |
| `hugo.toml` [params.analytics.cloudflare] | ✅ Vorbereitet | Optionale Werte: mode, website, token, domain |
| `head.html` | ✅ Eingebunden | cloudflare_analytics.html nach umami.html |
| `datenschutz/index.md` | ✅ Ergänzt | Cloudflare Web Analytics als Option in Abschnitt 1 + Tabelle |
| `ANLEITUNG-UMAMI-AKTIVIERUNG.md` | ✅ Erweitert | Abschnitt 10: Zwei Wege dokumentiert (A automatisch, B manuell) |

### Was du tun musst (Außenwirkung)

**Weg A (empfohlen):**
1. Cloudflare Dashboard login (cloudflare.com)
2. Analytics → Web Analytics → Website hinzufügen → `https://franksfinanzcheck.de`
3. Aktivierung → automatisches Injecting → fertig (kein Code, kein Deploy)

**Weg B (optional):**
1. Wie Weg A, aber nach Schritt 2: Website-ID + Token notieren
2. In hugo.toml eintragen: `mode = "manual"`, `website`, `token`
3. Deploy (Push → GitHub Actions oder lokaler `hugo --minify`)

**Kein Weg (ohne Dashboard-Zugang):**
- Kein Tracking einsatzbar (außer /go/-Klickzähler als Alternative)
- Blog mit Search Console + /go/-Klickzähler als Messung arbeiten
