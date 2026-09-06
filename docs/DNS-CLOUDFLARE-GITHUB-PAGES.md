# 🌐 DNS- & HTTPS-Reparatur: franksfinanzcheck.de (Cloudflare → GitHub Pages)

**Stand:** 27.08.2026 · **Problem:** GitHub Pages „Enforce HTTPS“ ausgegraut
(*„domain is not properly configured to support HTTPS“*), Pinterest-Crawler
liefert 404 → Domain als Spam markiert.

## Befund (Live-DNS-Abfrage 27.08.2026)

| Eintrag | Ist-Wert | Soll-Wert (GitHub Pages) |
|---|---|---|
| Nameserver | `damian.ns.cloudflare.com`, `sloan.ns.cloudflare.com` (Cloudflare) | — |
| A `franksfinanzcheck.de` | `104.21.18.115`, `172.67.181.202` (**Cloudflare-Proxy** 🟠) | 4× GitHub-Pages-IPs |
| A `www.franksfinanzcheck.de` | `104.21.18.115`, `172.67.181.202` (Cloudflare-Proxy 🟠) | CNAME auf den GitHub-Zielhost |

**Ursache:** Die Domain läuft über die **Cloudflare-Proxy-Wolke** (orangenes
Wölkchen). GitHub Pages bekommt keine direkte Verbindung zur Domain und kann
daher über die HTTP-Challenge **kein Let's-Encrypt-Zertifikat ausstellen** →
„Enforce HTTPS“ bleibt gesperrt. Da Cloudflare gleichzeitig die komplette
Edge-Terminierung übernimmt (und je nach Einstellung Bots mit Challenge/403
abwehrt), kann Pinterests Crawler die Seite nicht wie erwartet erreichen →
404/Spam-Markierung.

GitHub-Pages-Referenz-IPs (für A-Records):
`185.199.108.153`, `185.199.109.153`, `185.199.110.153`, `185.199.111.153`

---

## 🏆 PFLEGELEICHTESTE & DAUERHAFTESTE EMPFEHLUNG (Agentur-Entscheidung)

**Graues Wölkchen (DNS only), Cloudflare bleibt DNS-Anbieter, GitHub Pages
macht HTTPS.** Einmal eingerichtet, läuft es dauerhaft ohne Wartung:

| Kriterium | **Grau (DNS only) – EMPFOHLEN** | Orange (Proxy + Zertifikats-Tanz) |
|---|---|---|
| Zertifikat | GitHub (Let's Encrypt), **Auto-Renewal für immer** | Edge Cloudflare; Origin-Zertifikat kann nach 90 T. **Fehler 526** werfen |
| Wartung | **0 Aufwand dauerhaft** | alle ~60–90 Tage ggf. grau/orange schalten |
| Fehlerquellen für Crawler | keine (direkt zu GitHub) | Bot Fight Mode, Security Level, Rocket Loader, WAF |
| Performance/Cache | GitHub-CDN (Fastly, global) reicht für statischen Blog völlig | Cloudflare-CDN (Mehrwert nur bei hohem Traffic nötig) |
| Du bleibst bei Cloudflare | **ja** (DNS-Zone bleibt dort) | ja |

**Warum das für DIESEN Blog die Premium-Wahl ist:** Es ist eine kleine
statische Hugo-Seite ohne dynamische Requests, ohne Login, ohne Formulare –
es gibt nichts, was ein Proxy-Caching oder eine WAF schützen müsste. GitHub
Pages stellt TLS, CDN und Skalierung kostenlos und automatisch bereit. Damit
entfällt jede Dauerbaustelle (Zertifikats-Tanz, 526-Fehler, Bot-Blocking) –
und der Pinterest-Crawler hat eine stabile, unveränderliche Zieladresse.

**Faustregel:** Proxy (orange) lohnt sich erst, wenn du gezielt Cloudflare-
Features brauchst (z. B. Redirect-Rules im großen Stil, Rate-Limiting bei
starkem Bot-Traffic, Workers). Für einen Affiliate-Ratgeber-Blog ist das
nicht der Fall – **grau ist hier das professionelle Setup.**

---

## Empfohlener Weg (einfach & robust für einen statischen Blog): Cloudflare-Proxy AUS, GitHub direkt

Ein kleiner statischer Hugo-Blog braucht keinen Proxy davor – GitHub Pages
liefert TLS, CDN/Caching und Bot-Erreichbarkeit direkt. Das minimiert
Fehlerquellen für den Pinterest-Crawler.

### In Cloudflare (dash.cloudflare.com → Domain franksfinanzcheck.de → DNS)

1. **Apex (franksfinanzcheck.de)** – bestehende A-Records mit Cloudflare-IPs
   **löschen** und neu anlegen:
   - Typ `A`, Name `@` (oder `franksfinanzcheck.de`), Inhalt
     `185.199.108.153`, **Proxy-Status: DNS only** (graues Wölkchen)
   - gleich 3× wiederholen für `185.199.109.153`,
     `185.199.110.153`, `185.199.111.153`
2. **www** – Eintrag ändern auf:
   - Typ `CNAME`, Name `www`, Inhalt
     `frank-hartung.github.io` (dein GitHub-Pages-Zielhost),
     **Proxy-Status: DNS only** (grau)
3. Sicherstellen, dass **kein** A/AAAA-Record mehr auf `104.21.*` /
   `172.67.*` zeigt und **kein AAAA**-Record existiert (GitHub Pages hat
   keine eigenen AAAA-Einträge; ein Cloudflare-AAAA würde die Prüfung stören).
4. **CAA-Einträge** (falls vorhanden) so setzen, dass GitHub/Let's Encrypt
   ausstellen darf (kein restriktives CAA oder `letsencrypt.org` erlauben).

### Danach bei GitHub

5. **Warten** bis DNS propagiert ist (meist 10–60 Min., max. 24 h).
6. Repo → **Settings → Pages**: Das Feld *„Enforce HTTPS“* wird nach
   erfolgreichem Zertifikat (GitHub stellt es automatisch aus) anklickbar →
   **Häkchen setzen**.
7. Prüfen:
   - `https://franksfinanzcheck.de/` lädt ohne Zertifikatswarnung
   - `https://franksfinanzcheck.de/pinterest-e238f.html` (Claim) erreichbar
   - Rich-Pin-Debugger (developers.pinterest.com/tools/url-debugger) liefert
     OG-Daten statt 404.

---

## Alternativer Weg (Cloudflare-Proxy behalten)

Nur, wenn Cloudflare bewusst als CDN/Firewall bleiben soll. Kritischer, weil
falsche Einstellungen den Crawler weiter blockieren:

1. DNS-Records auf die GitHub-IPs legen und **Proxy an** (orange) lassen.
2. Cloudflare **SSL/TLS → Overview**: Modus **„Full (strict)“** (GitHub hat
   ein gültiges Zertifikat; auf KEINEN Fall „Flexible“ → Redirect-Loops).
3. **SSL/TLS → Edge Certificates**: „Always Use HTTPS“ an.
4. **Bot-Abschaltung für Pinterest**:
   - *Security → Bots*: **Bot Fight Mode AUS** (sonst werden fremde Crawler
     mit JS-Challenge/CAPTCHA blockiert – Pinterestbot kommt nicht durch).
   - *Security → WAF*: keine Rule, die unbekannte User-Agents blockt.
   - *Security → Settings*: Security Level **„Medium“ oder niedriger**
     („I'm Under Attack“/High erzeugt 403/503 für Crawler).
5. GitHub stellt in diesem Setup u. U. **kein** eigenes Zertifikat aus
   (Challenge erreicht GitHub nicht) – dann läuft TLS ausschließlich über
   Cloudflares Edge-Zertifikat (das ist funktionsfähig; der „Enforce HTTPS“-
   Schalter bei GitHub bleibt aber ggf. aus, weil GitHub die Domain nicht
   direkt prüfen kann).

➡️ Für die Pinterest-Entsperrung ist der **erste Weg (Proxy aus)** deutlich
sicherer: Es gibt keine Stelle mehr, die den Crawler blockieren könnte.

---

## ⭐ ABSOLUTE PREMIUM-EMPFEHLUNG: Cloudflare behalten UND GitHub-Zertifikat

### Die zentrale TLS-Wahrheit (sonst baut man es falsch)

Auf einer Verbindung kann nur **eine** Stelle das öffentliche Zertifikat
ausspielen — die am Rand (Edge):

| Modus | Wer stellt das Zertifikat aus, das Besucher/Pinterest sehen? |
|---|---|
| **Graues** Wölkchen (DNS only) | **GitHub** (Let's Encrypt) |
| **Oranges** Wölkchen (Proxied) | **Cloudflare** (Universal SSL) |

Du kannst Pinterest also **nicht** das GitHub-Zertifikat zeigen, während
Cloudflare proxyt. Was aber sehr wohl geht: GitHub **am Origin** ein gültiges
Zertifikat ausstellen lassen und Cloudflare dann davor schalten — Cloudflare
verbindet sich zu GitHub über **Full (strict)** mit genau diesem gültigen
GitHub-Zertifikat. So hast du **beides**: Cloudflare mit allen Funktionen
(CDN, WAF, Analytics, Page Rules) **und** ein valides GitHub-Zertifikat.

### Der „Zertifikats-Tanz“ (1×, ~30 Min.)

**Schritt A — GitHub ausstellen lassen (kurz grau):**
1. Cloudflare → DNS: Apex als 4× `A` auf `185.199.108/109/110/111.153`,
   `www` als `CNAME` auf `frank-hartung.github.io` — alle **grau (DNS only)**.
2. 10–60 Min. warten, bis GitHub das Let's-Encrypt-Zertifikat ausgestellt hat.
3. GitHub → **Settings → Pages**: „Enforce HTTPS“ wird klickbar → **Häkchen setzen**.
4. Prüfen: `https://franksfinanzcheck.de/` direkt über GitHub gültig
   (Issuer = Let's Encrypt, kein Warnhinweis).

**Schritt B — Cloudflare-Proxy wieder an (orange) mit Pflicht-Settings:**
5. Die gleichen Records auf **orange (Proxied)** schalten.
6. **SSL/TLS → Overview: `Full (strict)`** — NICHT „Flexible“ (Redirect-Loop),
   nicht „Full“ ohne strict. Strict funktioniert, weil GitHub jetzt am Origin
   ein echtes Zertifikat vorhält.
7. **SSL/TLS → Edge Certificates:**
   - „Always Use HTTPS“ **an**
   - Minimum TLS Version **1.2**
   - „Automatic HTTPS Rewrites“ **an**
   - Universal SSL = aktiv (deckt Apex + `*.franksfinanzcheck.de`, also www)
8. **Security → Bots: `Bot Fight Mode` AUS** (blockiert sonst den Pinterestbot).
9. **Security → Settings:** Security Level **Medium** oder niedriger
   (High / „I'm Under Attack“ erzeugt 403/503/Challenge für Crawler).
10. **Security → WAF:** keine Rule, die fremde User-Agents oder Datacenter-IPs
    blockt; „Block AI bots“ so lassen, dass Pinterestbot nicht mitgefangen wird.
11. **Speed → Optimization:** `Rocket Loader` **AUS** (injiziert JS, kann
    OpenGraph/JSON-LD für den Crawler stören); Auto Minify darf bleiben.

### Pflege-Hinweis (Premium-Transparenz)
- GitHub-Zertifikate laufen **90 Tage** und erneuern sich automatisch. Hinter
  Orange **kann** eine Erneuerung scheitern (Challenge läuft über Cloudflare).
- Für Besucher/Pinterest ist das Edge-Zertifikat (Cloudflare) maßgeblich —
  das bleibt gültig, es gibt also **keine** sichtbare Zertifikatswarnung.
  Nur die Origin-Verbindung unter Full(strict) könnte nach Ablauf einen
  **Fehler 526** werfen.
- Gegenmaßnahme bei 526 (alle ~60–90 Tage oder wenn es auftritt): Records
  kurz auf **grau** schalten, 10–30 Min. warten (GitHub erneuert), dann
  wieder **orange**. Einfachste dauerhafte Entspannung: „Full (strict)“
  mit aktiviertem Edge-Zertifikat — der 526 betrifft dann nur den Origin-Hop.

### Reihenfolge für die aktuelle Pinterest-Sperre
**Jetzt währen des Appeals:** grau (GitHub direkt) — entfernt jede Stelle, die
den Crawler blockieren könnte, und ist der sauberste Beweis „Domain
erreichbar“. **Nach** bestätigter Entsperrung und stabilem Traffic: den
Zertifikats-Tanz durchführen und Cloudflare-Proxy (orange) wie gewohnt nutzen.

---

## Verifikation nach der Umstellung

```bash
# Grau = 4 GitHub-IPs (185.199.x); Orange = Cloudflare-IPs (104.x/172.x)
dig +short franksfinanzcheck.de A
# Soll in beiden Fällen: HTTP 200 über HTTPS
curl -sSI https://franksfinanzcheck.de/ | head -1
# Wer stellt das Edge-Zertifikat aus? (grau = Let's Encrypt, orange = Cloudflare)
echo | openssl s_client -servername franksfinanzcheck.de -connect franksfinanzcheck.de:443 2>/dev/null \
  | openssl x509 -noout -issuer
# Claim + ein Artikel müssen 200 liefern
curl -sS https://franksfinanzcheck.de/pinterest-e238f.html -o /dev/null -w "%{http_code}\n"
# Pinterestbot darf NICHT blockiert werden (soll 200, nicht 403/503/Challenge)
curl -sS -A "Pinterestbot/1.0 (+https://help.pinterest.com/en/business/article/pinterest-crawler)" \
  https://franksfinanzcheck.de/ -o /dev/null -w "%{http_code}\n"
```

Dann den Appeal stellen, dass die Domain technisch wieder sauber erreichbar
ist (siehe `PINTEREST-SPAM-SPERRE-AKTIONSPLAN.md`, Phase 2–3).
