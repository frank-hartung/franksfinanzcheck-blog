# ANLEITUNG – Feedback-Widget („War dieser Ratgeber hilfreich?")

> **Seit:** 28.09.2026 · **Ursprung:** Quick Win H4 aus der
> Konkurrenz-Analyse Finanztip (`KONKURRENZ-ANALYSE-FINANZTIP-KI-TOOLS-2026-09-28.md`)
> **Teile:** `layouts/_partials/ff_feedback.html` (Renderer) ·
> `static/premium/ff-feedback.js` (Logik) ·
> `assets/css/extended/z-premium-blog.css` (Optik, Block „FEEDBACK") ·
> `newsletter-worker/src/index.js` (Endpoint `POST/GET /feedback`)

---

## Warum gibt es das?

Finanztip zeigt unter jedem Ratgeber „War dieser Ratgeber hilfreich?"
mit öffentlicher Quote („81 % fanden diesen Ratgeber hilfreich") –
Leserqualität wird am Nutzerverhalten gespiegelt. Franks Variante
misst dasselbe, aber **ohne Tracking**: kein Umami (das ist
consent-geprüft und würde Feedback ohne Einwilligung verlieren),
keine Cookies, kein Fingerprinting.

## Architektur

```
Artikelseite (posts + pillar)
  └─ ff_feedback.html  – Section mit data-endpoint/data-slug
      └─ ff-feedback.js – Klick → POST { slug, hilfreich }
            └─ abos.franksfinanzcheck.de/feedback (Newsletter-Worker)
                  └─ KV: feedback:<slug> → { ja, nein, letzte }
```

* **Endpoint-Ableitung:** `site.Params.newsletterFormAction`
  (`…/anmeldung`) → `…/feedback`. Kein eigener hugo.toml-Parameter.
* **Slug:** Posts = Ordnername (`2026-08-26-tagesgeld-…`), Ratgeber =
  `pillar-<themenwelt>` (z. B. `pillar-strom-sparen`).
* **Datenschutz by design:** gespeichert wird NUR der aggregierte
  Zählerstand je Slug. Missbrauchsschutz: kurzer IP-Hash-Schlüssel
  (`fb:<sha256(ip|slug)>`, TTL 6 h) verhindert Doppelzählen – keine
  Klartext-IPs, keine personenbezogenen Bestände.
* **Fehlervertrag:** Erreicht der POST den Worker nicht (z. B. noch
  nicht neu deployt), bekommt der Leser trotzdem sein Dankeschön.
  Es geht nichts kaputt – es wird nur nicht gezählt.

## Deploy (einmalig nötig!)

Der Endpoint lebt im Newsletter-Worker. Nach dem Merge:

```bash
cd newsletter-worker
npx wrangler deploy
```

Danach gilt: `https://abos.franksfinanzcheck.de/healthz` → Worker
läuft, `POST /feedback` zählt (Tests:
`cd newsletter-worker && node --test test/index.test.js`, 60 grün).

## Zählerstände lesen (Ausbaustufe „Quote anzeigen")

```
GET https://abos.franksfinanzcheck.de/feedback?slug=<slug>
→ { ok: true, slug, ja: 12, nein: 3 }
```

**Noch bewusst NICHT angebaut:** die öffentliche Anzeige („X von Y
fanden das hilfreich"). Sie kommt erst, sobald die Zahlen sozial
belastbar sind – ein „0 von 0" ist schlechter als kein Sozialbeweis
(Ehrlichkeit vor Buzz, Marken-Stimme in PRODUCT.md). Wenn du sie
willst: in `ff-feedback.js` nach dem Seitenaufruf `GET /feedback`
holen und ab z. B. 5 Stimmen die Quote in `ff-feedback__dank`-Manier
nachreichen.

## Verwandte Dokumente

* `KONKURRENZ-ANALYSE-FINANZTIP-KI-TOOLS-2026-09-28.md` – Herleitung (H4)
* `docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md` – Worker-Betrieb allgemein
