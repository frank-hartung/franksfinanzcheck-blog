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

## Verifikation nach der Umstellung

```bash
# Soll: 4 GitHub-IPs, keine Cloudflare-IPs
dig +short franksfinanzcheck.de A
# Soll: HTTP 200 über HTTPS, gültiges Zertifikat
curl -sSI https://franksfinanzcheck.de/ | head -1
curl -sS https://franksfinanzcheck.de/pinterest-e238f.html -o /dev/null -w "%{http_code}\n"
```

Dann den Appeal stellen, dass die Domain technisch wieder sauber erreichbar
ist (siehe `PINTEREST-SPAM-SPERRE-AKTIONSPLAN.md`, Phase 2–3).
