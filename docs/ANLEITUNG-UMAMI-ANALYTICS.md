# 📊 Umami Analytics – Setup-Anleitung (Privacy-freundlich, kostenlos)

**Warum Umami?** Cookieless (keine Cookies, kein Consent-Banner-Zwang nach § 25 TDDDG), keine
personenbezogenen Daten (IP wird gehasht), keine Daten an Google, Open Source, DSGVO-konform –
der professionelle Ersatz für Google Analytics.

**Achtung:** GitHub Pages kann **kein** Analytics self-hosten (nur statisches Hosting).
Du hast drei Wege – alle kostenlos:

---

## Option A: Umami Cloud (empfohlen – schnellster Weg, ~10 Min)

1. **Konto erstellen:** https://cloud.umami.is → Sign up (kostenlos)
2. **Website anlegen:** Settings → Websites → **Add website**
   - Name: `FranksFinanzcheck`
   - Domain: `frank-hartung.github.io/franksfinanzcheck-blog`
   - → Speichern → **Website-ID** kopieren (sieht aus wie eine UUID)
3. **ID im Blog eintragen:** `hugo.toml` →
   ```toml
   [params.umami]
     websiteId = "DEINE-WEBSITE-ID"          # ← hier einfügen
     consentRequired = true                  # streng: nur nach "Alle akzeptieren"
   ```
4. **Push + Deploy:** Änderung committen/pushen → Blog baut automatisch
5. **Test:** Blog öffnen, im Dashboard prüfen, ob der Besuch erscheint (~30 s Verzögerung)

**Kostenlos-Plan:** 1 Website, 10.000 Events/Monat – für einen Blog völlig ausreichend.

---

## Option B: Self-hosted auf Vercel (kostenlos, eigene Instanz)

1. **Vercel-Konto:** https://vercel.com (Hobby-Plan, kostenlos)
2. **Umami deployen:** https://vercel.com/new/clone?repository-url=https://github.com/umami-software/umami
   - Bei der Einrichtung wird nach **Vercel Postgres** (oder Neon) gefragt → verbinden (kostenloser Tier)
   - → **Deploy** (dauert ~3–5 Min)
3. **Admin-Zugang:** Nach dem Deploy die URL öffnen → Erst-Login: `admin` / `umami`
   → Passwort sofort ändern!
4. **Website anlegen:** Settings → Websites → Add website → **Website-ID** kopieren
5. **Im Blog eintragen** (`hugo.toml`):
   ```toml
   [params.umami]
     websiteId = "DEINE-WEBSITE-ID"
     src = "https://DEIN-PROJEKT.vercel.app/script.js"   # deine Instanz
     hostUrl = "https://DEIN-PROJEKT.vercel.app"
     consentRequired = true
   ```
6. **Push + Test** wie in Option A

**Hinweis:** Vercel-Hobby schläft nach längerer Inaktivität ein (erster Aufruf dauert dann ~5 s) –
für Analytics unkritisch, da die Messung serverseitig erfolgt, sobald jemand deine Seite besucht.

---

## Option C: Self-hosted auf eigenem VPS (maximale Kontrolle, ~4–6 €/Monat)

Für maximale Datenschutz-Kontrolle (EU-Server, eigene Domain für Umami):

1. **VPS mieten:** z. B. Hetzner CX22 (~4 €/Monat, Serverstandort Falkenstein/DE)
2. **Installieren** (Docker):
   ```bash
   # Umami auf dem VPS (offizielle Anleitung):
   # https://umami.is/docs/install
   git clone https://github.com/umami-software/umami.git
   cd umami
   # .env anlegen: DATABASE_URL (Postgres), APP_SECRET
   docker compose up -d
   ```
3. **Subdomain** (z. B. `stats.franksfinanzcheck.de`) per DNS + Reverse-Proxy (Caddy/Nginx) auf Umami
4. **Im Blog eintragen:**
   ```toml
   [params.umami]
     websiteId = "DEINE-WEBSITE-ID"
     src = "https://stats.franksfinanzcheck.de/script.js"
     hostUrl = "https://stats.franksfinanzcheck.de"
     consentRequired = true
   ```

**Tipp für die eigene Domain später:** Sobald `franksfinanzcheck.de` läuft, kannst du Umami
auch auf einer Subdomain dort hosten – dann ist ALLES unter deiner eigenen Domäne (maximales
Vertrauen + keine Drittanbieter-Labels in Lighthouse).

---

## Automatische Klick-Übernahme in den Blog & Betriebsmodi

### Standard: Kostenfreier Betrieb (Umami Free)

Im kostenfreien Plan von Umami Cloud steht kein API-Zugang zur Verfügung. Der Blog ist darauf optimal eingerichtet:
- Das Tracking läuft im Browser vollständig weiter (Seitenaufrufe + `affiliate_click`-Events).
- Alle Auswertungen stehen direkt im **Umami-Dashboard** bereit.
- In `data/monetization.yaml` ist `umami_api_import_enabled: false` hinterlegt.
- Die CI/Governance-Pipeline erwartet kein Token und erzeugt keinen Fehlalarm.

### Optional: API-Import bei Self-Hosting oder Umami Pro

Wenn du Umami selbst hostest (Option B / C) oder einen Pro-Plan nutzt, kann die Pipeline Daten vollautomatisch importieren:

```bash
# lokal / im Workflow (premium-governance.yml, Schritt „Umami-Klicks laden")
python3 scripts/umami_clicks.py --fetch --days 90
python3 scripts/umami_clicks.py --status     # Was ist der Stand der Pipeline?
```

Einrichtung bei Self-Hosting / Pro (2 Minuten):

1. **Umami Cloud (Pro) / Self-Hosted:** Avatar → *User Settings* → *API* → *Generate API Key*
   (self-hosted: `POST /api/access-tokens` bzw. Token im Admin-Bereich).
2. `data/monetization.yaml` auf `umami_api_import_enabled: true` stellen.
3. Repository-Secret anlegen: `gh secret set UMAMI_API_TOKEN`
4. Optional, wenn die Instanz nicht `https://api.umami.is/v1` ist:
   Repository-Variable `UMAMI_API_BASE` (z. B. `https://umami.example.com/api`).
5. Website-ID wird **nicht** als Secret gepflegt – `scripts/umami_clicks.py` liest sie
   aus `hugo.toml` (`[params.umami] websiteId`). Eine Wahrheit, kein zweiter Ort.

Was ankommt: `data/umami_clicks.json` (aggregierte Zähler je /go/-Stelle,
Quell-Artikel und Pillar) + `data/umami_clicks.meta.json` (Stand, Quelle, Grund
eines fehlenden Imports). Keine IPs, keine Profile, keine Sessions – und das
Token taucht in keinem Log und keiner Datei auf.

Bei Ausfall bleibt der letzte Bestand stehen (ein Analytics-Problem darf nicht wie
„0 Klicks" aussehen), und der Governance-Lauf meldet die Lücke als Hinweis, nicht
als Fehler.

**Seit 19.09.2026 – die komplette Umsatzmessung obendrauf:** dasselbe Token speist
nun auch `scripts/umami_views.py` (Seitenbesuche als Nenner) und den
`cta_click`-Import (Start-/Pillar-Buttons). Zusammen mit der Awin-Publisher-API
(`scripts/awin_fetch.py`) rechnet `scripts/revenue_funnel.py` den ganzen Trichter
(Besuche → Klicks → Antrag → Abschluss → Storno → Provision/EPC); der
`click_chain_guard` hält die Kette am gebauten Stand dicht. Setup, Testklick-SOP
und Eskalationswege: **`docs/UMSATZ-MESSUNG-PREMIUM.md`**.

## Konfigurations-Optionen (hugo.toml)

| Parameter | Bedeutung | Default |
|---|---|---|
| `websiteId` | Deine Umami-Website-ID – **leer = Analytics aus** | `""` |
| `src` | Skript-URL (Cloud oder eigene Instanz) | `https://cloud.umami.is/script.js` |
| `hostUrl` | Daten-Endpunkt bei self-hosted (sonst leer) | `""` |
| `consentRequired` | `true` = lädt erst nach „Alle akzeptieren" (streng); `false` = cookieless ohne Einwilligung, DNT wird respektiert | `true` |

## Datenschutz (in der Datenschutzerklärung bereits ergänzt)

- **Cookieless:** Keine Cookies → § 25 TDDDG nicht einschlägig
- **IP-Anonymisierung:** IP wird sofort gehasht, nie gespeichert
- **Rechtsgrundlage:** Einwilligung (strenger Modus) oder berechtigtes Interesse (Art. 6 Abs. 1 lit. f DSGVO)
- **Opt-out:** Do-Not-Track im Browser aktivieren oder „Nur notwendige" im Consent-Banner
- Der **Datenschutz-Disclaimer** ist bereits unter „Statistik und Reichweitenmessung (Umami)" in
  `content/datenschutz/index.md` eingebaut

## Test-Checkliste

- [ ] Website-ID in `hugo.toml` eingetragen
- [ ] Push → Deploy abgewartet (Live-SHA prüfen)
- [ ] Blog-Seite geöffnet → Umami-Dashboard zeigt Besuch
- [ ] Im Konsolen-Entwickler-Tools: `script.js` wird geladen (nur bei Zustimmung, wenn `consentRequired: true`)
- [ ] Datenschutzseite zeigt den Umami-Abschnitt
