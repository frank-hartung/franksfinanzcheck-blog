# Edge-Schutz der Zone `franksfinanzcheck.de`

**Was hier steht:** die Cloudflare-Einstellungen, die den Blog schützen, aber
nicht im Repository liegen können — Sicherheits-Header, Mengenregeln auf
lesende Routen, Bot-Schutz und der Proxy-Entscheid. Alles kopierfertig, mit
Prüfkommando danach.

**Warum überhaupt:** GitHub Pages ignoriert `static/_headers` (steht dort selbst
als Kommentar). Deshalb fehlten live HSTS, `X-Frame-Options` und `nosniff` — der
Blog war in fremde Seiten einbettbar. Das lässt sich **nur** über einen Proxy
vor der Seite ändern; die Meta-Angaben im HTML können Weder-HSTS-noch-
`frame-ancestors` leisten. Wer das prüft, prüft `scripts/blog_header_gate.py`.

**Grundlage:** Sicherheitsaudit vom 14./15.10.2026 (F-01, F-02, F-03).
**Schritt-für-Schritt mit Nachweis:** `docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, Abschnitt A1–A3.

---

## 1. A1 — Sicherheits-Header (Finding F-01)

Cloudflare-Dashboard → Zone `franksfinanzcheck.de` → **Rules → Transform Rules →
Modify Response Header → Create rule**

- **Name:** `FF Sicherheits-Header`
- **Filter (Custom filter expression):**
  `(http.host eq "franksfinanzcheck.de" or http.host eq "www.franksfinanzcheck.de")`
- **Then → Set static** — folgende Kopfzeilen (jeweils „Set static"):

| Kopfzeile | Wert |
|---|---|
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains; preload` |
| `X-Content-Type-Options` | `nosniff` |
| `X-Frame-Options` | `DENY` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=(), payment=(), usb=()` |
| `Cross-Origin-Opener-Policy` | `same-origin` |
| `Cross-Origin-Resource-Policy` | `same-origin` |
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline' https://challenges.cloudflare.com; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' https://abos.franksfinanzcheck.de https://stats.franksfinanzcheck.de https://challenges.cloudflare.com; frame-src https://challenges.cloudflare.com; frame-ancestors 'none'; base-uri 'self'; form-action 'self' https://abos.franksfinanzcheck.de; object-src 'none'` |

**Warum die CSP so aussieht:** `'unsafe-inline'` bei `script-src` ist noch
nötig (Inline-Skripte für Theme und Service-Worker-Registrierung). Auch damit
ist die Regel ein Fortschritt: **fremde** Skripte, Frames und Formularziele sind
ausgeschlossen. Der nächste Ausbauschritt steht in Schritt 4.

**Ein Proxy ändert die Rechtslage** — deshalb steht der fertige
Datenschutz-Text in `docs/SICHERHEIT-BETRIEB-RUNBOOK.md`, Schritt B7. Er nennt
Cloudflare als Empfänger der Zugriffsdaten und stimmt damit überein, was
tatsächlich passiert.

**Prüfen:** `curl -sI https://franksfinanzcheck.de/ | grep -Ei 'strict-transport|x-frame|nosniff|content-security'`
→ fünf Zeilen. Automatisch mit Gegenproben: `npm run header:check`.
**Ein Befehl für die ganze Regel (seit 19.10.2026, WF-E813 / #809):**
`npm run edge:freigabe` misst DNS-Proxy, SSL-Modus und genau diese acht
Kopfzeilen gegen die Cloudflare-API; `npm run edge:freigabe:apply` stellt
sie idempotent her (`scripts/cloudflare_edge_freigabe.py`, Sollstand wird
aus der Tabelle oben gelesen – eine Quelle).

**Live-Messung mit Klassifikation:** `npm run header:check:live` (bzw. der
tägliche Job „Live-Messung“ der Sicherheits-Wache). Die Wache liefert vier
Klassen statt „rot oder grün“ — `BEFUND` (gemessen und mangelhaft, Exit 1),
`STOERUNG` (nicht messbar, Exit 2, **kein** Sicherheitsbefund), `TEILWEISE`
(ein Ziel gemessen, eines nicht) und `OK`. Transiente Netzfehler heilt sie
vorher selbst (vier Versuche, 2 s/8 s/30 s Pause). Steht in der Diagnose
„Proxy nicht aktiv“ (kein `cf-ray`), kann diese Regel gar nicht wirken — dann
ist Schritt 1 im Runbook fällig, nicht diese Regel hier.

---

## 2. A2 — Mengenregeln (Finding F-03)

Cloudflare-Dashboard → **Security → WAF → Rate limiting rules → Create rule**

| Name | Ausdruck (Filter) | Grenze | Aktion |
|---|---|---|---|
| `FF Anmeldung/Tor` | `(http.host eq "abos.franksfinanzcheck.de" and http.request.method eq "POST")` | 20 / 1 min | Block für 60 s |
| `FF Token-Seiten GET` | `(http.host eq "abos.franksfinanzcheck.de" and http.request.method eq "GET")` | 120 / 1 min | Managed Challenge |
| `FF Anmelde-Seite` | `(http.host eq "franksfinanzcheck.de" and http.request.uri.path contains "/newsletter")` | 60 / 1 min | Managed Challenge |
| `FF Zähler` | `(http.host eq "stats.franksfinanzcheck.de")` | 60 / 1 min | Block für 60 s |

**Warum gerade so:** Der Worker hat seit dem Audit eigene Limits
(`RATE_LIMITER`-Binding plus Mengenklassen im Code). Die WAF ist die *frühere*
Schicht: Sie zählt an der Edge, verbraucht keine KV-Lesevorgänge und schützt
auch dann, wenn der Worker gerade kalt startet. Die Grenzen sind bewusst derart
gesetzt, dass ein Mensch nie in ihre Nähe kommt (ein Leser öffnet wenige Seiten
pro Minute). Ohne WAF-Regel bleibt der Worker-Schutz als zweite Schicht aktiv —
die Regeln sind eine Verstärkung, keine Voraussetzung.

**Prüfen:** Dashboard → Security → Events, nach Regelname filtern; oder
`npm run betrieb:check` (liest den Worker-Zustand und meldet Budget,
Bot-Schutz-Zustand und die letzten Exportaufrufe).

---

## 3. A3 — Bot-Schutz des Anmeldeformulars (Finding F-02)

1. Cloudflare-Dashboard → **Turnstile → Add widget**: Name `FF Newsletter`,
   Domains `franksfinanzcheck.de`, `www.franksfinanzcheck.de`, Widget-Modus
   **Managed**.
2. **Site Key** an **zwei** Stellen eintragen (derselbe Wert): `hugo.toml`
   `params.turnstileSiteKey = "0x4AAA…"` **und** `newsletter-worker/wrangler.toml`
   `TURNSTILE_SITEKEY = "0x4AAA…"` (Paar-Vertrag, Spiegel für den Worker).
   Damit liefert `layouts/shortcodes/newsletter_form.html` das Widget aus und
   `static/premium/ff-newsletter.js` schickt das Token mit.
3. **Secret Key** im Worker hinterlegen:
   `cd newsletter-worker && npx wrangler secret put TURNSTILE_SECRET`
4. Datenschutz-Hinweis ist bereits eingearbeitet (`content/datenschutz/index.md`,
   Abschnitt Newsletter) — der Dienst wird nur beim Absenden geladen.

**Paar-Vertrag (seit 19.10.2026, WF-E813 / #809):** Der Worker prüft
fail-closed, sobald Secret **und** Site-Key gesetzt sind. Der halbgesetzte
Zustand „nur Secret“ war der Anmelde-Ausfall vom 15.10.2026 — jede Anmeldung
scheiterte an einer Sicherheitsprüfung ohne Widget. Seitdem heißt er
**„wartet“**: Die Anmeldung läuft weiter (Honeypot, Zeitfalle,
Mengenklassen, Tagesbudget), `/healthz` meldet den Zustand, und
`scripts/worker_betrieb_wache.py` meldet ihn täglich als Warnung — nebst
Spiegel-Prüfung beider Site-Key-Stellen. „Widget ohne Secret“ bleibt ein
**Fehler** („Fassade“).

**Ohne Turnstile?** Möglich, aber dann bleibt der Schutz bei Honeypot,
Zeitfalle, Mengenklassen und dem Tagesbudget (max. 100 Anmeldungen/Tag). Der
Melder sagt diesen Zustand ausdrücklich als Warnung an — nicht als „in
Ordnung".

---

## 4. Optionaler Ausbauschritt (empfohlen, 1 Sitzung)

`script-src 'unsafe-inline'` durch Hashes ersetzen (Hugo berechnet sie mit
`resources.FromString` + `sha256`), danach:

```
Content-Security-Policy: … script-src 'self' 'sha256-…' https://challenges.cloudflare.com …; style-src 'self' 'unsafe-inline'; …
```

Begleitend: `npm run content:check` (findet `<script`, `on*=`, `javascript:` in
`content/**`) bleibt scharf, damit kein Inline-Skript über einen automatisch
erzeugten Beitrag zurückkommt.

---

## 5. Proxy-Entscheidung (Finding F-01)

| | **A: Cloudflare-Proxy an** (orange Wolke) | **B: Ohne Proxy bleiben** |
|---|---|---|
| Header (A1) | möglich | **nicht möglich** — GitHub Pages liefert keine |
| Datenschutz | Text anpassen (Runbook B7) | Text bleibt gültig |
| Aufwand | 10 Minuten + Textänderung | keiner |
| Restrisiko | Zugriffsdaten laufen über Cloudflare; Vertrag/DPF prüfen | Clickjacking, fehlendes HSTS, fehlendes nosniff bleiben |

Empfehlung: **A**. Der Blog ist öffentlich und hat ein Anmeldeformular — ein
fehlender Frame-Schutz ist hier die teurere Lücke. Die Wache
`scripts/blog_header_gate.py` meldet in beiden Fällen ehrlich, was live fehlt — und unterscheidet seit WF-E813 (15.10.2026) zwischen „es fehlt etwas“ (BEFUND) und „es konnte nichts gemessen werden“ (STOERUNG).
