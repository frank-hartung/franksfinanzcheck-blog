# 🛡 Newsletter-Zustellbarkeit: Cloudflare-Zone + Brevo-Konto (Agentur-Runbook)

**Stand: 23. September 2026.** Anlass: Newsletter-Daily **Lauf #21** (12:16 UTC,
rot) und die Frage, warum ein grüner Versandlauf trotzdem keine Mail bedeuten
kann. Dieses Runbook ist die dauerhafte Antwort auf zwei getrennte Baustellen,
die vorher als eine galten: **die Kante** (Netz/Cloudflare) und **das Konto**
(Brevo). Gemessen, nicht geraten – jeder Ist-Wert unten stammt aus einer
Live-DNS-Abfrage vom 23.09.2026.

Alles hier ist **nachprüfbar ohne Dashboard**:

```bash
python3 scripts/newsletter_zustellbarkeit.py --pruefen            # Zone + Konto
python3 scripts/newsletter_zustellbarkeit.py --pruefen --strict   # Freigabe-Gate
python3 scripts/newsletter_zustellbarkeit.py --pruefen --md       # Summary-Block
python3 scripts/newsletter_zustellbarkeit.py --selftest           # 40 Fälle, netzfrei
```

---

## 1. Der Befund des Tages (zwei Klassen, eine Meldung gewesen)

| # | Was passierte | Wie es gemeldet wurde | Was es wirklich war |
|---|---|---|---|
| 1 | Die Kante vor `api.brevo.com` antwortete HTTP 403 mit `Error 1010: Access denied – blocked based on your browser's signature` | „❌ Vorprüfung fehlgeschlagen: Absender-Vorprüfung nicht möglich“ → klang nach Konto | **Der Client.** `urllib` sendete ohne `User-Agent` die Bibliotheks-Standardkennung `Python-urllib/3.11`; Signaturfilter werfen genau die raus, **bevor** Brevos Authentifizierung die Anfrage sieht. Brevo hat den API-Key an diesem Lauf nie gelesen. |
| 2 | Checkliste sagte: „SPF um `include:spf.brevo.com` erweitern, dann ist der Absender authentifiziert“ | als freischaltender Schritt notiert | **Zu pauschal.** Auf Brevos geteiltem Versandweg bleibt der Return-Path beim Anbieter; ein SPF-Include in der eigenen Zone bringt **kein** DMARC-Alignement. Was trägt, ist das **Domain-DKIM** – und das ist in dieser Zone längst gesetzt (`brevo1`/`brevo2._domainkey` → `b1.`/`b2.franksfinanzcheck-de.dkim.brevo.com`). |

**Heilung 1 (Transport, `scripts/newsletter_digest.py`)**

* Der Client nennt sich selbst: `franksfinanzcheck-newsletter/1.1 (+https://…;
  Brevo-REST-v3; GitHub-Actions)`, mit einer zweiten, weiterhin ehrlichen
  Kennung als Reserve (`Mozilla/5.0 (compatible; …)` – Selbstauskunft, **kein**
  Browser-Imitat: einen Browser vorzuspielen wäre Betrug an der Kante und beim
  nächsten strenger werdenden Signaturfilter wieder eine Störung).
* `kanten_block()` unterscheidet Blockage (Nicht-JSON/Cloudflare-Marken,
  `cf-ray`) von einer echten Anbieter-Absage (JSON mit `code`/`message`). Der
  Befund heißt jetzt „**Kante blockiert** … Brevo hat die Anfrage nie gesehen“
  – und nicht länger, der Absender sei schuld.
* **Lesen wird wiederholt, Schreiben niemals.** Ein `POST …/sendNow`, das beim
  Anbieter angenommen wurde und dessen Antwort verloren ging, ist eine
  *ausgeführte* Handlung. Die alte Fassung wiederholte transiente Ausfälle bis
  zu dreimal – auf `sendNow` heißt das: dieselbe Ausgabe ein zweites und
  drittes Mal an die ganze Liste. Jetzt: ein Versuch, dann **Nachlese** in der
  Kampagnen-Akte (`GET /emailCampaigns/{id}` → `status`, `statistics`). Belegt
  sie die Sendung, meldet der Lauf „VERSAND ERFOLGT“; bleibt sie dunkel,
  schreibt er einen Halt (`versand_unklar` in `data/newsletter_state.json`), der
  jeden weiteren **Listen**-Versand blockiert (Testversände bleiben möglich).
  Aufheben kann den Halt nur ein Mensch.
* `BREVO_API_HOST` (optional, z. B. für `api.us.brevo.com`) ist nur für
  Brevo-eigene Domains erlaubt – ein fremder Host würde den `api-key`
  mitnehmen, deshalb: Befund statt Netzversuch.

**Heilung 2 (Messung, `scripts/newsletter_zustellbarkeit.py`)** – siehe §§ 2–4.

---

## 2. Cloudflare-Zone: gemessener Stand und Soll-Zustand

Zone `franksfinanzcheck.de`, Nameserver bei Cloudflare, Website **DNS only**
auf GitHub Pages (A `185.199.108–111.153`), Mail-Eingang über Cloudflare Email
Routing. Abgefragt am 23.09.2026 über DNS-over-HTTPS:

| Record | Ist (gemessen) | Urteil | Soll / nächster Schritt |
|---|---|---|---|
| `TXT @` SPF | `v=spf1 include:_spf.mx.cloudflare.net ~all` | ✅ | genau **ein** Eintrag – so lassen. `include:spf.brevo.com` erst mit Dedicated IP/eigenem Return-Path |
| `TXT @` `brevo-code:` | vorhanden | ✅ | – (Eigentumsnachweis, Domain-Status in Brevo damit abgeschlossen) |
| `CNAME brevo1._domainkey` | `b1.franksfinanzcheck-de.dkim.brevo.com.` | ✅ | nicht anfassen, nicht „verschönern“ |
| `CNAME brevo2._domainkey` | `b2.franksfinanzcheck-de.dkim.brevo.com.` | ✅ | – |
| `MX @` | `route1/2/3.mx.cloudflare.net` | ✅ | Email Routing aktiv → `kontakt@` (Reply-To) ist ein Briefkasten |
| `TXT _dmarc` | `v=DMARC1; p=reject; adkim=s; aspf=s; rua=mailto:…@dmarc-reports.cloudflare.net;` | ⚠️ **Schärfe ohne Notwendigkeit** | siehe § 3 |

Nicht aus der Zone lesbar und deshalb **bewusst nicht als „geprüft“ gemeldet**:
Bot Fight Mode, Security Level, WAF-Regeln, Email-Routing-Regeln, DNSSEC. Dazu
sagt die Wache nichts – die Prüfschritte stehen in § 4.

---

## 3. DMARC: die Policy ist eine Anweisung an Gmail und Yahoo

Der Ist-Wert `p=reject` mit `adkim=s` **und** `aspf=s` ist auf dieser Strecke die
engste denkbare Kombination:

* `adkim=s` verlangt exakte Übereinstimmung von Signatur-Domain (`d=`) und
  From-Domain. Das geleistete Domain-DKIM tut das → **träge Wirkung, korrekt**.
* `aspf=s` verlangt exakte Übereinstimmung der SPF-Domain mit der From-Domain.
  Auf Brevos geteiltem Weg liegt der Return-Path beim Anbieter → **diese Leg kann
  hier niemals alignen.** Sie liefert also keinen zweiten Beleg, sondern nur den
  Ausschluss des ersten.
* Die Folgenkombination: fällt DKIM je aus (Schlüssel-Rotation, ein Absender auf
  fremder Domain, eine manuell angelegte Kampagne aus einem zweiten Konto),
  scheitert DMARC **und** `p=reject` weist hart ab. „Kommt nicht an“ ist in
  diesem Setup nicht ein Spam-Ordner-Problem, sondern ein Zustell-Ausfall – und
  der Duplikatsschutz nützt nichts, wenn niemand etwas erhält.

**Empfohlene Stufenfolge** (jeweils ein TXT-Edit in Cloudflare → DNS → Records →
`_dmarc`):

| Stufe | Wortlaut | wann |
|---|---|---|
| 1 – beobachten | `v=DMARC1; p=none; aspf=r; rua=mailto:<deine Adresse>;` | ab sofort, bis ein Testversand **und** eine Liste mit echten Abonnenten belegt ankamen |
| 2 – drosseln | `v=DMARC1; p=quarantine; pct=25; aspf=r; rua=…` | nach dem ersten Werktag mit sauberer Berichterstattung |
| 3 – schließen | `v=DMARC1; p=quarantine; aspf=r; adkim=s; rua=…` | Dauerzustand für eine Domain, die nur über Brevo sendet |
| 4 – hart | `p=reject` | erst, wenn die Berichte 4 Wochen keine Fremd-Signatur zeigen; `aspf=s` nur mit Dedicated IP/eigener Bounce-Domain |

Zusätzlich empfohlen: Brevos Berichtadresse als **zweiten** `rua`-Empfänger
eintragen (`rua=mailto:dein@postfach.de;mailto:rua@dmarc.brevo.com`) – ohne
`rua` ist der einzige Beweis „kam an“ ein Zufallspostfach.

Null-MX (`MX @ .`) darf in dieser Zone **nie** wieder auftauchen: er sagt der
ganzen Welt „nimmt keine Mail an“ und killt Reply-To und Rückläufer zugleich.

---

## 4. Brevo-Konto: was die API zeigt, was nur das UI zeigt

Geprüft von `newsletter_zustellbarkeit.py`, sobald `BREVO_API_KEY` gesetzt ist:

| Regel | Was sie liest | Fund-Fall |
|---|---|---|
| **B0** Netzweg | unauthentisierte `GET /senders`-Sonde; Kante oder Anbieter? | HTTP 403 mit Signaturfilter-Marke → Kanten-Befund (kein Konto-Befund!); HTTP 0 mit Key → Blocker; HTTP 0 ohne Key → Messlücke (gelb) |
| **B1** Absender | `GET /senders` → `active` | fehlt oder `active: false` → kein Listen-Versand |
| **B2** Liste | `GET /lists/{BREVO_LIST_ID}` → `name`, `totalSubscribers` | 404 → Secret falsch; 0 Abonnenten → Hinweis (Live-Versand ginge ins Leere) |
| **B3** Plan-Grenze | `GET /account` → `plan[].allowSentEmails`, `plan[].name` | **Liste > Tagesgrenze** → Fund: ein Werktagsversand erreicht nicht alle, der Lauf bleibt aber grün |
| **B4** Themen | Studio-`capture.feld_themen` gegen Brevos Attributpfad | `themen` (ohne `attributes[…]`) → Hinweis: die Themen-Chips der Site landen bei Brevo nicht an |
| **S1–S3** Status | `data/newsletter_state.json` | Halt `versand_unklar` aktiv → Fund; kein `zuletzt_versandt` → Hinweis |

**Was die API nicht hergibt (bewusste Lücken, nicht „geprüft“):**

* **Double-Opt-In pro Formular** – Brevo zeigt das nur im Formular-Editor.
  Kontrolle: Brevo → *Contacts → Forms → Blog-Anmeldung → Settings →
  „Require double opt-in“ = AN*. Die Site verspricht zwei Klicks; hält das nur
  dieses Formular.
* **Interessen/Präferenzen** – damit `{{update_profile}}` (der
  „Präferenzen“-Link in jeder Mail) tatsächlich ein Feld zum Ändern bekommt, muss
  das Zielfeld im Konto existieren: *Contacts → Attributes* →
  z. B. `attributes[THEMEN]` anlegen, dann in
  `data/newsletter_studio.json` → `capture.feld_themen` auf genau diesen Namen
  setzen. Solange das nicht gesetzt ist, sind die Themen-Chips ein
  Formularelement ohne Empfänger – die Wache meldet das als B4.
* **RFC 8058 (One-Click-Abmeldung)** – Brevo spritzt die
  `List-Unsubscribe`/`List-Unsubscribe-Post`-Header **für authentifizierte
  Domains**. Domain-Authentifizierung ist hier vorhanden (DKIM ✅), also ist das
  erfüllt; `newsletter_qa.py` (Q19) hält zusätzlich fest, dass die Mail keinen
  zweiten, im HTML gebastelten Abmelde-Header trägt.
* **Absender-Postfach `news@`** – Senden braucht keine Mailbox, aber
  eingehende Briefe an `news@` (Rückfragen, Rückläufer) laufen ins Leere, weil
  Cloudflare Email Routing nur die Regel `kontakt` kennt und bewusst **kein**
  Catch-all läuft. Empfehlung: *Cloudflare → Email → Routing → Routing Rules →
  Create rule*: Muster `news` → dieselbe Zieladresse. (Bewusst keine
  Catch-all-Regel: die wäre ein Spam-Fänger.)

---

## 5. Kadenz, Halt und Freigabe – was die Wache nicht ist

* Sie **repariert nichts**: keine DNS-Schreibaktion, kein POST an Brevo (nur
  `GET`). Einstellen muss ein Mensch, in zwei Oberflächen, mit den Werten aus § 2
  und § 4.
* Sie **blockiert den Listen-Versand** dort, wo ein Zweifel belegt ist: im
  Versandlauf (`newsletter-daily.yml`) vor dem Anlegen der Kampagne, und über
  den Halt `versand_unklar` so lange, bis nachgesehen wurde. Der Testversand
  (Workflow-Eingabe `test_adresse`) bleibt in beiden Fällen möglich – er ist der
  vorgesehene Probelauf *vor* der Freischaltung.
* Sie **meldet Messlücken gelb, nicht rot**: DoH-Ausfall, fehlender Key,
  Offline-Lauf → „nicht gemessen“. `--strict` (Freigabe-Gate) macht daraus einen
  Fehler, damit ein ungeprüftes Grün nicht als Bestehen zählt.
* Sie **verwechselt Lücke nicht mit Befund**: ist ein Record nicht abfragbar, steht
  da „nicht gemessen“ – und die erreichbaren Schichten werden trotzdem bewertet.
  Eine halbe DKIM-Lage (eine von zwei Delegationen sichtbar) ist ein Hinweis, kein
  Fund; ein wackelnder DoH-Endpunkt darf niemanden in die laufende Zone greifen
  lassen. Das ist dieselbe Unterscheidung, die Lauf #21 fehlte (Kante vs. Konto).
* Ihr `--selftest` (40 Fälle) hängt im Governance-Minimum
  (`scripts/governance_contract.py`, GUARDS/C6) – eine Wache, die niemand
  regelmäßig laufen lässt, veraltet still.

---

## 6. Abnahme nach jeder Änderung (Kopierblock)

```bash
# 1) Zone: was wirklich veröffentlicht ist (Soll aus § 2)
dig +short TXT franksfinanzcheck.de
dig +short TXT _dmarc.franksfinanzcheck.de
dig +short CNAME brevo1._domainkey.franksfinanzcheck.de
# 2) Wache: Zone + Konto, ein Befund pro Zeile, mit Klickweg
python3 scripts/newsletter_zustellbarkeit.py --pruefen --strict
# 3) Versand-Kette: Vorprüfung, QA, digester Bau (netzlos)
python3 scripts/newsletter_digest.py --selftest
python3 scripts/newsletter_digest.py --check
python3 scripts/newsletter_digest.py --build --days 1 --out /tmp/nl
# 4) Beweislauf in Actions: erst Probe, dann Liste
#    Actions → Newsletter-Daily (Capture-Wache + Digest) → Run workflow
#    · test_adresse = eigene Adresse  → sendTest, Liste unangetastet
#    · live = an                      → sendNow an die Liste
```

Kommt die Probel-Mail nicht an, ist die Reihenfolge: (a) steht im Lauf
„Kante blockiert“, ist es der Netzweg, nicht das Konto; (b) bei „Absender …
NICHT verifiziert“ fehlt der Bestätigungscode in Brevo; (c) bei „0 Abonnenten“
hat die Liste keinen Double-Opt-In-Durchlauf; (d) läuft der Loop grün und die
Mail ist nicht da, liegt es an der **Empfängerseite** → `p=reject`-Ablehnung
nachlesen (rua-Bericht oder Postfach-Spam-Ordner des Zielkontos).

---

## 7. Verwandte Dokumente

* `docs/FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md` – die Reihenfolge zum Freischalten
* `docs/ANLEITUNG-NEWSLETTER.md` – Konto, Formular, Secrets, Probelauf
* `docs/DNS-CLOUDFLARE-GITHUB-PAGES.md` – Proxy/TLS/Bot-Frage für Website und Crawler
* `docs/E-MAIL-WEITERLEITUNG-CLOUDFLARE.md` – Email Routing für `kontakt@`
* `NEWSLETTER-ZUSTELLBARKEIT-PREMIUM-2026-09-23.md` – Audit-Report dieses Auftrags
