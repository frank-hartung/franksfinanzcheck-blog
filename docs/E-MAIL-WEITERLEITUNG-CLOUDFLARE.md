# 📧 E-Mail für FranksFinanzcheck: `kontakt@franksfinanzcheck.de`

**Stand:** 21. September 2026
**Zweck:** Eingehende Nachrichten an `kontakt@franksfinanzcheck.de` werden an
die bereits bestätigte persönliche Zieladresse weitergeleitet.

## Empfohlenes Setup

Für diesen statischen Blog (Hugo auf GitHub Pages, DNS bei Cloudflare) ist
**Cloudflare Email Routing** die schlankste Lösung: Die Domain bleibt bei
Cloudflare, es wird keine eigene Mailbox und kein Mailserver betrieben. Die
Weiterleitung ist damit vollständig vom Hosting bei GitHub Pages getrennt.

> **Wichtig:** Email Routing ist eine **Weiterleitung**, kein vollständiges
> Postfach. Antworten werden weiterhin aus dem persönlichen Postfach gesendet.
> Wer beim Antworten sichtbar von `kontakt@franksfinanzcheck.de` senden möchte,
> braucht zusätzlich einen Mailanbieter mit eigener Domain-Mailbox oder SMTP-
> Unterstützung (z. B. Brevo für den Newsletter-Versand – siehe
> [ANLEITUNG-NEWSLETTER.md](ANLEITUNG-NEWSLETTER.md)). Das ist in diesem Setup
> bewusst nicht als eigenes Postfach eingerichtet.

## Einmalige Einrichtung in Cloudflare

Die folgenden Schritte brauchen Zugriff auf das Cloudflare-Konto der Domain.
Passwörter, API-Tokens oder die private Zieladresse gehören **nicht** ins
Repository.

1. Cloudflare öffnen und die Zone **`franksfinanzcheck.de`** auswählen.
2. Zu **Compute → Email Service → Email Routing** gehen und **Onboard Domain**
   auswählen.
3. Für `franksfinanzcheck.de` die Einrichtung starten. Cloudflare zeigt die
   erforderlichen DNS-Einträge an und kann sie bei einer von Cloudflare
   verwalteten DNS-Zone automatisch anlegen:
   - MX-Einträge für den Eingang über Cloudflare,
   - SPF für die Weiterleitung,
   - DKIM für die Authentifizierung weitergeleiteter Nachrichten.
4. Unter **Destination Addresses** die bereits bestätigte persönliche
   Zieladresse hinzufügen. Die von Cloudflare gesendete Bestätigungs-Mail
   öffnen und die Zieladresse verifizieren. Ohne diese Bestätigung bleibt
   die Regel deaktiviert.
5. Unter **Routing Rules → Create routing rule** eine Regel anlegen:
   - **Email pattern:** `kontakt`
   - **Domain:** `franksfinanzcheck.de`
   - **Action/Destination:** die soeben verifizierte Zieladresse
6. **Keinen Catch-all** aktivieren. So werden Tippfehler und unbekannte
   Adressen nicht unnötig an das persönliche Postfach weitergeleitet.

### DNS-Sicherheitscheck (Null-MX-Konflikt)

- **Aktueller Befund dieser Domain:** Es ist ein sogenannter Null-MX-Eintrag
  veröffentlicht: `MX @ .` mit Priorität `0`. Der Punkt (`.`) ist kein
  Mailserver, sondern signalisiert ausdrücklich, dass die Domain keine
  E-Mails annimmt. Genau dieser Eintrag löst in Cloudflare den
  Routing-Konflikt aus.
- Vor dem Aktivieren im Cloudflare-DNS den Eintrag **`MX` / Name `@` /
  Ziel `.` / Priorität `0`** löschen. **Nur diesen Null-MX-Eintrag
  entfernen**; A-, CNAME- und TXT-Einträge der Website nicht löschen.
- Falls stattdessen echte MX-Einträge eines anderen Maildienstes vorhanden
  sind, diesen Maildienst zuerst identifizieren. Niemals zwei unabhängige
  Mailanbieter parallel für dieselbe Domain konfigurieren.
- Danach die Cloudflare-Einrichtung erneut starten. Cloudflare soll die
  Routing-MX-Einträge selbst verwalten; keine zusätzlichen MX-Einträge auf
  eigene Faust ergänzen.
- Falls bereits ein SPF-TXT-Eintrag existiert, darf **kein zweiter
  SPF-Eintrag** angelegt werden (zwei Einträge = `permerror`, dann scheitert
  *jede* Mail der Domain). Im Zweifel die von Cloudflare vorgeschlagene
  DNS-Konfiguration verwenden – für diese Zone ist das gemessene Ergebnis
  `v=spf1 include:_spf.mx.cloudflare.net ~all` (Stand 23.09.2026).
- **Kein** `include:spf.brevo.com` für den Newsletter nötig: Brevo versendet
  über seinen eigenen Return-Path, das Include in der eigenen Zone erzeugt
  daher kein SPF-Alignement und authentifiziert nichts. Nötig wird es erst mit
  Dedicated IP oder eigenem Return-Path – und nur durch Erweitern des
  **einen** Eintrags, nie durch einen zweiten. (Der Newsletter-Beleg ist das
  Domain-DKIM: `brevo1`/`brevo2._domainkey`, beide vorhanden. Details:
  [NEWSLETTER-ZUSTELLBARKEIT-CLOUDFLARE-BREVO.md](NEWSLETTER-ZUSTELLBARKEIT-CLOUDFLARE-BREVO.md).)
- **Regel für das Newsletter-Postfach anlegen:** der Versand läuft mit
  Absender `news@franksfinanzcheck.de`. Ohne eigene Regel landen Antworten und
  Rückläufer dorthin im Leergut → *Email → Routing → Routing Rules → Create
  rule*: Muster `news` → dasselbe Zielpostfach wie `kontakt`. **Keine**
  Catch-all-Regel anlegen (die wäre ein Spam-Fänger); `newsletter_zustellbarkeit.py`
  meldet fehlende `news`-Regel als Hinweis.
- MX-Einträge sind **nicht** proxied (DNS-only, graues Wölkchen). Die
  Website-A- und CNAME-Einträge bleiben von der Mail-Einrichtung
  unberührt (orangenes Wölkchen für die Web-Cache-Proxy-Funktion).

Siehe auch: [DNS-CLOUDFLARE-GITHUB-PAGES.md](DNS-CLOUDFLARE-GITHUB-PAGES.md)
für die Website-DNS-Konfiguration.

## Test und Abnahme

1. Von einem **anderen** Mailkonto eine Test-Mail an
   `kontakt@franksfinanzcheck.de` senden.
2. Prüfen, ob sie im Zielpostfach ankommt; auch den Spam-Ordner
   kontrollieren.
3. Auf die Test-Mail antworten und prüfen, dass die Zustellung
   funktioniert.
4. Danach in Cloudflare unter Email Routing die Aktivität bzw. das
   Routing-Log kontrollieren.

Cloudflare weist darauf hin, dass DNS-Änderungen meist nach wenigen
Minuten, weltweit aber in Einzelfällen erst nach bis zu 24 Stunden
sichtbar sind.

## Im Blog hinterlegt

Nach der Einrichtung verwendet der Blog die neue Adresse als öffentlichen
Kontakt in:

- Impressum, Datenschutz, Über-mich- und Methodik-Seite
- strukturierten Daten (JSON-LD `publisher.email`) und `security.txt`
- `hugo.toml` → `[params] contactEmail = "kontakt@franksfinanzcheck.de"`
  (einzige Quelle für alle Templates)
- README und `llms.txt`
- Newsletter-Anleitung und Datenschutz-Generator-Checkliste

Die persönliche Zieladresse wird **nicht** als öffentlicher Kontakt im
Repository geführt.

## Offizielle Dokumentation

- [Cloudflare: Domain für Email Routing einrichten](https://developers.cloudflare.com/email-routing/get-started/enable-email-routing/)
- [Cloudflare: Routing-Regeln und Zieladressen](https://developers.cloudflare.com/email-service/configuration/email-routing-addresses/)
- [Cloudflare: DNS-Konfiguration für Email Service](https://developers.cloudflare.com/email-service/configuration/domains/)
