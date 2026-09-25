# Newsletter: Abmeldelink im Testversand + Formular rechtssicher (DE)

**Stand: 25. September 2026.** Anlass: Im versendeten Test-Newsletter fehlte
der Abmelde-Link. Gleichzeitig Prüfung, ob das Anmeldeformular für Deutschland
rechtlich trägt.

Keine Rechtsberatung – die Änderungen schließen die messbaren Lücken, die eine
Abmahnung typischerweise trifft (UWG § 7, Art. 6/7/13 DSGVO, § 5 DDG, RFC 8058).

## 1. Warum der Abmeldelink „fehlte“

Der Testversand (`--test-adresse`) hat die Studio-Marken **ohne Token**
aufgelöst und `token: ""` an den Mailer gegeben. Drei Folgen, eine Wahrnehmung:

| Schicht | Vorher | Wirkung im Postfach |
|---|---|---|
| HTML-Fuß | Link auf `/newsletter/abmelden/` (Infoseite: „dieser Klick geht nicht“) | Der sichtbare „Abmelden“-Text führte ins Leere |
| 12,5 px, grau, hinter dem DOI-Satz | Leicht zu übersehen, Gmail klappt Fußzeilen ein | |
| SMTP-Header | `List-Unsubscribe` **nur mit Token** | Gmail/Yahoo zeigen **keinen** Abmelde-Knopf |
| Resend-Header | `…/abmeldung?token=` (leer) | Clients werten den Header als ungültig und blenden ihn aus |

Der Testversand war damit kein Kleid der Live-Ausgabe, sondern eine Mail ohne
wirksamen Widerruf – genau das, was § 7 UWG in jeder geschäftlichen Mail
verlangt.

## 2. Was jetzt gilt (eine Regel, jeder Weg)

1. **Nie ein leerer Token im Link.** `?token=` ohne Wert verlässt das Haus nicht
   (`marken_pflicht`, fail-closed vor dem Send).
2. **List-Unsubscribe immer.** Mit Abo-Token: HTTPS-One-Click auf den Worker
   **und** mailto. Ohne Token (Test an Nicht-Abonnenten): nur mailto – dafür
   **kein** `List-Unsubscribe-Post` (RFC 8058 darf nur stehen, wenn HTTPS
   wirklich abmeldet).
3. **RFC 8058 liest den Token aus der Query.** Gmail POSTet an die
   List-Unsubscribe-URL; der Body ist `List-Unsubscribe=One-Click`. Wer nur den
   Body las, sah keinen Token – der Knopf im Postfach war tot.
4. **Testadresse mit bestehendem Abo** bekommt dasselbe Token wie die
   Live-Ausgabe (`GET /export/kontakt`). Es wird **kein** Kontakt angelegt
   (kein Consent, keine Liste).
5. **Fuß der Mail:** eigene Zeile, 15 px, „Newsletter abmelden“ plus formloser
   mailto. Ladungsfähige Anschrift mit Straße, PLZ, Ort (§ 5 DDG).
6. **`/newsletter/abmelden/`** ist kein Infoschild mehr, sondern ein POST-Formular
   an den Worker (plus mailto). Unbekannte Adressen bekommen dieselbe
   Erfolgsmeldung – kein Enumerationsleck.

## 3. Anmeldeformular: was getragen hat, was fehlte

Getragen (unverändert, jetzt härter bewacht):

- Einwilligung **nicht** vorangekreuzt, `required`
- Double-Opt-In erklärt, Bestätigungsmail als CTA-Text
- HTTPS an die eigene Subdomain, Honeypot ohne Drittanbieter
- Nachweis (IP, Zeitpunkt, UA) 3 Jahre, Adresse nach Abmeldung 30 Tage
- Auftragsverarbeiter Resend + Cloudflare (AVV/DPA, SCC bzw. DPF) in § 8 DS
- Kein Öffnungs-/Klick-Tracking

Geschlossen in dieser Reparatur:

| Lücke | Risiko | Änderung |
|---|---|---|
| Consent nannte nicht den Verantwortlichen | Art. 13 Abs. 1 lit. a | „Frank Hartung (FranksFinanzcheck)“ |
| Consent deckte Partnerlinks/Werbung nicht ab | UWG § 7: Einwilligung muss die Werbung tragen | „als Werbung gekennzeichnete Partnerlinks“ |
| Kein Impressum neben der Einwilligung | Art. 13, Identität | Link Impressum + Datenschutz |
| Widerruf nur „Link in der Mail“ | Art. 7 Abs. 3, wenn die Mail weg ist | Abmeldeseite mit Formular + mailto |
| Mail-Fuß ohne Straße/PLZ | § 5 DDG, UWG § 5a | Anschrift wie im Impressum |
| Testmail ohne List-Unsubscribe | RFC 8058 / Gmail-Knopf | mailto immer, HTTPS wenn Token |

Was bewusst **nicht** in die Checkbox wandert (gehört in die DS, und steht dort):

- Speicherdauer, Empfänger im Detail, Drittlandtransfer, Betroffenenrechte –
  verlinkt, nicht als Roman in der Checkbox (sonst ist die Einwilligung
  unverständlich und angreifbar).

## 4. Beweise

Die Wachen und Tests dieser Änderung; der nächste Testversand an
`frankhartung@web.de` ist der Beweis im Postfach (Gmail-Knopf + Fuß-Link).

Siehe Selftests von `newsletter_versand.py`, `newsletter_digest.py`,
`newsletter_qa.py`, `newsletter_studio.py` und `newsletter-worker/test`.
