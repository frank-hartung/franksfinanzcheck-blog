# 📧 Absender-E-Mail hinterlegen: Cloudflare **und** Brevo (Schritt für Schritt)

**Stand: 23. September 2026.** Einmalige Einrichtung, danach nie wieder anfassen.
Diese Anleitung ist der genaue Wortlaut zu **Schritt 2** der
[FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md](FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md)
und ergänzt [E-MAIL-WEITERLEITUNG-CLOUDFLARE.md](E-MAIL-WEITERLEITUNG-CLOUDFLARE.md)
um die Versand-Seite. Sie ist aus dem Befund von
**Newsletter-Daily (Capture-Wache + Digest) #15** (und dem Cron #16)
am 23.09.2026 geschrieben – beide Läufe scheiterten mit:

```
❌ Vorprüfung fehlgeschlagen: Absender-Vorprüfung nicht möglich
   (HTTP 401: Key not found · unauthorized) – kein Versand: lieber
   fail-closed, als eine Kampagne mit ungeprüftem Absender anzulegen.
```

(Seit diesem Run spricht der Vorflug den Fall selbst aus: der Befund endet nicht
mehr bei „fail-closed“, sondern nennt den API-Key als Prüfobjekt –
`scripts/newsletter_digest.py`, `vorflug()`.)

> **Die wichtigste Erkenntnis daraus, vor aller DNS-Arbeit:** #15 ist **kein**
> SPF-/DKIM-Problem. Die Vorprüfung konnte die Sender-Liste bei Brevo gar nicht
> erst lesen – der API-Schlüssel wird von Brevo abgelehnt. Wer jetzt DNS-Einträge
> baut, repariert nichts. **Deshalb zuerst Abschnitt 1 (Schritt 0).**

---

## 0. Wovon der Code ausgeht (eine Quelle, kein Raten)

Der Versand liest den Absender **nicht** aus einer Eingabemaske, sondern aus der
Studio-SSOT `data/newsletter_studio.json` → `email`
(`absender_konfig()` in `scripts/newsletter_digest.py`):

| Feld | Wert (SSOT) | Wer prüft ihn | Was Brevo/Cloudflare liefern müssen |
|---|---|---|---|
| Absender-**Name** | `Frank von FranksFinanzcheck` | geht in den Kampagnen-Payload `sender.name` | im Brevo-Sender **derselbe** Name (nur Anzeige, aber Identität für den Leser) |
| Absender-**E-Mail** | `news@franksfinanzcheck.de` | `vorflug()` → `GET /v3/senders`, **exakter** Abgleich (Groß-/Kleinschreibung egal) **und** `active: true` | genau diese Adresse, verifiziert/aktiv |
| **Reply-To** | `kontakt@franksfinanzcheck.de` | geht als `replyTo.email` in den Payload | Cloudflare-Routing-Regel für `kontakt` → bestätigte Zieladresse |
| Listen-ID | Secret `BREVO_LIST_ID` (Zahl) | `GET /v3/contacts/lists/{id}`, `totalSubscribers` | Liste `Blog-Abonnenten`, ID aus der Listen-URL |

Zwei Regeln, die die meisten „geht trotzdem nicht"-Läufe erzeugen:

1. **Was in Brevo steht, muss mit der SSOT übereinstimmen.** Weicht sie ab – etwa
   weil die Adresse in Brevo `kontakt@…` heißt, das Studio aber `news@…` nennt –
   bricht der Lauf mit „existiert im Brevo-Konto nicht" ab, **bevor** eine
   Kampagne entsteht. Das ist gewollt fail-closed, kein Bug.
2. **`NEWSLETTER_ABSENDER` schlägt die SSOT.** Die optionale
   Repository-**Variable** (nicht Secret) überschreibt `email.absender.email`.
   Sie ist nur für den Fall gedacht, dass der Absender je wechseln soll. Steht
   dort ein anderer Wert als in Brevo verifiziert ist, prüft der Vorflug die
   falsche Adresse. **Standard: Variable leer lassen.**

`news@` statt `kontakt@` als Absender ist übrigens eine Entscheidung, kein
Versehen: `kontakt@` ist die **Antwort**adresse (Weiterleitung, bewusst kein
eigenes Postfach), `news@` die **Versand**adresse einer Liste, die wachsen soll.

---

## 1. Schritt 0 – das Credential (der echte Blocker aus #15/#16)

Der Workflow streicht `--send` still, **wenn ein Secret fehlt** (Meldung:
„Kein Absender konfiguriert … – nur gebaut"). Läuft die Vorprüfung dagegen bis
zu Brevo durch und kommt **401 `Key not found`**, dann ist ein Secret **vorhanden,
aber unbrauchbar**. Vorweg: Der Key ist keine Versandfreigabe – er macht den
Absender nur **lesbar**. Die Checkliste schiebt Schritt 4 (Secrets) bewusst nach
hinten, damit kein Cron in eine leere Liste sendet; das Credential selbst darf
früher sitzen, es passiert damit nichts Unbeabsichtigtes. Ursachen, in absteigender Häufigkeit:

| # | Ursache | So prüfst du es |
|---|---|---|
| 1 | **SMTP-Schlüssel statt API-v3-Key** – beide sehen gleich aus, sind aber verschiedene Credentials | Brevo → **Settings → SMTP & API → API keys** (Reiter „API keys", **nicht** „SMTP"). Dort neu erzeugen. |
| 2 | Key gehört zu **einem anderen Brevo-Konto** (zweites Konto, Team-/Sub-Account-Wechsel, altes Sendinblue-Konto) | Im Browser ausloggen → in dem Konto einloggen, in dem Liste `Blog-Abonnenten` und Formular liegen → dort den Key erzeugen |
| 3 | Key wurde **gelöscht oder regeneriert** (Rotierung macht den alten Wert ungültig) | Settings → SMTP & API → API keys: steht der im Repo hinterlegte Key dort noch drin? |
| 4 | Secret heißt nicht exakt `BREVO_API_KEY` oder liegt als **Environment-Secret** (der Workflow hat kein `environment:` – Environment-Secrets sind für ihn unsichtbar) | Repo → Settings → Secrets and variables → Actions → Reiter **„Secrets"** (nicht „Variables"), Scope **Repository secrets** |
| 5 | `BREVO_LIST_ID` ist keine Zahl (z. B. der Name der Liste) | Secret muss die **Zahl aus der Listen-URL** sein (`…/lists/7` → `7`) |

Tippfehler, Leerzeichen und Zeilenumbrüche beim Kopieren sind **kein** Fehlerbild:
der Code strippt die Werte (`os.environ.get(...).strip()`). Ein 401 heißt also:
der Schlüssel ist, wie er ist, bei Brevo unbekannt.

**30-Sekunden-Probe** (Schlüssel niemals ins Repo, in einen Commit, ein Issue oder
einen Chat-Verlauf – hier liest er nur aus der Shell):

```bash
read -rs BREVO_API_KEY && printf '\n'
curl -s -o /tmp/brevo.json -w "HTTP %{http_code}\n" \
  -H "api-key: $BREVO_API_KEY" https://api.brevo.com/v3/senders
python3 -c "import json;print(json.load(open('/tmp/brevo.json')))"
```

Erwartet: `HTTP 200` und eine `senders`-Liste. `401` = Schritt 0 ist noch nicht
erledigt, alles Weitere ist dann zweitrangig.

---

## 2. Brevo – **Domain authentifizieren**, dann Sender anlegen

`news@franksfinanzcheck.de` hat **kein Postfach**: Cloudflare leitet nur Adressen
weiter, für die eine Routing-Regel existiert, und einen Catch-all gibt es hier
bewusst nicht. Genau das entscheidet über den Weg:

| Weg | Wann | Ablauf |
|---|---|---|
| **A – Domain-Authentifizierung** (empfohlen) | immer, wenn die DNS-Zone bei Cloudflare liegt (ist der Fall) | Brevo verifiziert **alle** Sender der Domain automatisch, sobald SPF/DKIM/Verifikations-Record grün sind – **kein Bestätigungscode nötig** |
| B – nur Sender + 6-stelliger Code | nur wenn die Domain (noch) nicht authentifisiert werden kann | Brevo schickt einen Bestätigungscode an `news@…` → **der kommt nirgends an**, solange es keine Routing-Regel für `news` gibt. Erst Cloudflare-Regel `news` → Zieladresse, dann Weg B |

### Weg A, in Brevo (≈ 5 Min. plus DNS)

1. Brevo → **Settings → Senders, Domains & Dedicated IPs → Domains** →
   **Add domain** / **Authenticate this domain** → `franksfinanzcheck.de`.
2. Brevo zeigt jetzt **eine Liste von DNS-Einträgen**. Diese Liste ist die
   Wahrheit für Abschnitt 3 – **nicht** diese Anleitung, **nicht** ein alter Screenshot.
   Typischer Inhalt (je nach Konto unterschiedlich, immer dem Panel folgen):
   - Verifikations-**TXT** am Root (`brevo-code:…`),
   - **DKIM** – entweder ein TXT am Selector `mail._domainkey` (bzw. bei
     Altkonten `_brevo._domainkey`) **oder zwei CNAMEs** `brevo1._domainkey` +
     `brevo2._domainkey`,
   - **SPF-Include** `include:spf.brevo.com` (bei Bestandskonten noch
     `include:spf.sendinblue.com`).
3. Eintrag für Eintrag **kopieren** (nicht abtippen) → Abschnitt 3 (Cloudflare).
4. Zurück in Brevo: **Verify / Authenticate** drücken. Grün kann Minuten dauern,
   neue Absenderdomains prüft Brevo stichprobenartig – bleibt „Pending" nach
   einigen Stunden, hilft ein Support-Ticket (das ist üblich, kein Konfigurationsfehler).
5. **Settings → Senders, Domains & Dedicated IPs → Senders & IPs → Add sender**:
   - E-Mail exakt `news@franksfinanzcheck.de`
   - Name exakt `Frank von FranksFinanzcheck`
   - Speichern. Nach authentifizierter Domain **keine Code-Abfrage**; der Sender
     steht auf `active` (= genau das, was `vorflug()` sieht).
6. Falls das Panel einen **DMARC-Vorschlag** zeigt: mitnehmen (Abschnitt 3, Zeile 4).

### Reply-To nachziehen

`replyTo` zeigt auf `kontakt@franksfinanzcheck.de`. Das ist eine Antwortadresse,
kein Versand – eine **verifizierte** Sender-Identität braucht Brevo dafür in der
Regel nicht. Weigert sich Brevo beim Kampagnen-Dialog/API-Aufruf trotzdem
(„replyTo must be a verified sender"), dann `kontakt@franksfinanzcheck.de`
**zusätzlich** unter *Senders* anlegen – nach Domain-Authentifizierung ist er
sofort aktiv. An der Studio-Konfiguration ändert sich dadurch nichts.

---

## 3. Cloudflare – die Zone `franksfinanzcheck.de`

Cloudflare ist hier **nur DNS**-Player: Es gibt bei Cloudflare keinen Mailversand
für diesen Newsletter (Email **Sending** auf dem `cf-bounce`-Subdomain-Zweig wird
nicht benötigt). Eingetragen wird in **DNS → Records**, alle Mail-Records
**grau = DNS only**.

| # | Typ | Name | Inhalt | Proxy | Hinweis |
|---|---|---|---|---|---|
| 1 | TXT | `@` | **ein** SPF, zusammengeführt: `v=spf1 include:_spf.mx.cloudflare.net include:spf.brevo.com ~all` | – (TXT) | **genau ein** `v=spf1`-Record am Root. Zwei Records = `PermError` = beide Anbieter defekt |
| 2 | TXT/CNAME | wie Brevo zeigt (`mail._domainkey`, alt `_brevo._domainkey`, oder `brevo1._domainkey` + `brevo2._domainkey`) | **wortwörtlich** aus dem Brevo-Panel | **DNS only** | CNAMEs für `_domainkey` dürfen nicht proxyt werden; sonst löst der Selector nicht auf |
| 3 | TXT | `@` | Brevo-Verifikationscode (`brevo-code:…`) | – | falls das Panel ihn zeigt |
| 4 | TXT | `_dmarc` | `v=DMARC1; p=none;` – optional `rua=mailto:…` für Reports | – | **bewusst `p=none`**: dieselbe Zone leitet `kontakt@` weiter. `p=quarantine`/`p=reject` auf einer Forwarding-Domain kann echte Leser-Mails kosten. Hochziehen erst, wenn einige Wochen saubere Reports da sind |
| 5 | MX | `@` | die drei `route1/2/3.mx.cloudflare.net` des Email Routing **unverändert lassen** | **DNS only** (MX ist nie proxyt) | **kein** `MX @ . 0` (Null-MX) mehr – der blockiert Email Routing und war schon 21.09. das Problem |

**Was hier nicht passiert:** keine neuen MX für Brevo (Brevo versendet über seine
eigenen Server, braucht keine MX auf deiner Domain), kein zweiter Mailanbieter,
kein Catch-all, keine Änderung an A-/CNAME-Einträgen der Website (oranges Wölkchen
bleibt, wie es ist), kein Handanlegen an den von Email Routing verwalteten
Einträgen (die stehen auf „Locked"; für eine Änderung kurz entsperren, danach wieder sperren).

**SPF-Limit im Blick behalten:** eine SPF-Zeile darf höchstens 10 `include`-DNS-Lookups
auslösen. Zwei Includes sind weit davon entfernt – aber wenn später noch Outlook/
Google/Forms dazu kommen, gehört alles in **einen** Record, nicht in einen zweiten.

Geprüft wird danach per Kommandozeile (oder Cloudflare-Dashboard → Records):

```bash
dig +short TXT franksfinanzcheck.de | grep -c v=spf1          # Erwartet: 1
dig +short TXT franksfinanzcheck.de                            # enthält beide include:
dig +short TXT mail._domainkey.franksfinanzcheck.de            # bzw. brevo1/brevo2
dig +short TXT _dmarc.franksfinanzcheck.de
dig +short MX franksfinanzcheck.de                             # drei routeN.mx.cloudflare.net
```

Änderungen sind bei Cloudflare meist in Minuten wirksam, global bis 24 h.

---

## 4. Reihenfolge, die funktioniert

```
0  BREVO_API_KEY gegenprüft → HTTP 200 auf /v3/senders        (Abschnitt 1)
1  Brevo-Domänendialog öffnen, alle angezeigten Records holen (Abschnitt 2)
2  Cloudflare: SPF mergen (1 Record!), DKIM(s), Verifikation  (Abschnitt 3)
3  Brevo: Verify → Domain grün                                (Abschnitt 2, Punkt 4)
4  Brevo: Sender news@franksfinanzcheck.de + Name → active    (Abschnitt 2, Punkt 5)
5  Cloudflare: Routing-Regel für kontakt@ live (Antwortpfad)  (E-MAIL-WEITERLEITUNG)
6  GitHub: Secrets gegenprüft, NEWSLETTER_ABSENDER leer/gleich (Abschnitt 1)
7  Actions → Newsletter-Daily → run with test_adresse          (Checkliste 6a)
8  Actions → Newsletter-Daily → live                           (Checkliste 6b)
```

Schritt 7 vor 8 ist kein Aberglauben: `sendTest` trifft genau eine Adresse, die
Liste bleibt unangetastet – und seit der Reparatur vom 23.09. scheitert der
Testversand auch nicht mehr an einer noch leeren Liste.

---

## 5. Abnahme – erst dann ist der Absender „richtig hinterlegt"

- [ ] `GET /v3/senders` liefert einen Eintrag mit `"email": "news@franksfinanzcheck.de"`
      **und** `"active": true` — das ist exakt die Bedingung aus `vorflug()`.
- [ ] `data/newsletter_studio.json` → `email.absender.email` == diese Adresse
      (und `NEWSLETTER_ABSENDER` widerspricht ihr nicht).
- [ ] Genau **ein** `v=spf1` am Root, mit Cloudflare-**und** Brevo-Include.
- [ ] Brevo zeigt SPF **und** DKIM grün; DMARC-Record vorhanden (`p=none`).
- [ ] Der letzte **Newsletter-Daily**-Lauf hat keine `❌`-Vorflug-Zeile, und die
      Testmail liegt im Postfach.
- [ ] In einer angekommenen Mail (Webmailer → „Original anzeigen") steht
      `spf=pass`, `dkim=pass`, `dmarc=pass` und `Signed-by: franksfinanzcheck.de`.
      Ein `dkim=fail` bei sonst grün = DNS noch nicht propagiert, 30 Min. warten.

---

## 6. Wenn es wieder rot wird: Befund → Ursache → nächster Schritt

Wortlaut genau so, wie `scripts/newsletter_digest.py` ihn ausspricht:

| Befund im Lauf | Ursache | Nächster Schritt |
|---|---|---|
| `Kein Absender konfiguriert (BREVO_API_KEY / BREVO_LIST_ID)` (gelbe Warnung, Lauf bleibt grün) | mindestens ein Secret fehlt/ist leer oder als **Variable** angelegt | Checkliste Schritt 4; `BREVO_LIST_ID` ist zwingend ein **Secret** |
| `Absender-Vorprüfung nicht möglich (HTTP 401: Key not found · unauthorized)` | Credential falsch (Typ, Konto, rotiert) | **Abschnitt 1** – nicht DNS |
| `Absender … existiert im Brevo-Konto nicht` | Sender fehlt in Brevo **oder** heißt anders als die SSOT **oder** `NEWSLETTER_ABSENDER` überschreibt still | Brevo → Senders & IPs → Add sender (Abschnitt 2, Punkt 5); Variable prüfen |
| `Absender … ist im Brevo-Konto vorhanden, aber NICHT verifiziert` | Bestätigungscode fehlt / SPF+DKIM noch nicht grün | Abschnitt 2, Punkt 4 (Domain grün machen) bzw. Routing-Regel für `news` (Weg B), dann erneut laufen lassen |
| `Liste … existiert im Brevo-Konto nicht (HTTP 404)` | `BREVO_LIST_ID` zeigt auf eine andere Liste | Zahl aus der Listen-URL neu eintragen |
| `Die Zielliste hat 0 Abonnenten` (nur bei `live`) | noch keine Double-Opt-In-Anmeldung | erst 6a mit `test_adresse`, Liste läuft voll, dann `live` |
| `Digest ist leer` (gelbe Warnung) | im Zeitraum liegt kein unversandter Artikel | `tage` im Dispatch vergrößern (z. B. 3) |

Seit 23.09. erscheint ein roter Lauf zusätzlich als **Issue** mit Diagnose
(`alert-on-failure.yml` wacht über beide Newsletter-Workflows) und als Annotation
in der Actions-Übersicht; fehlt der Cron-Lauf eines Werktags komplett, holt die
Kadenz-Wache (~08:11 UTC) ihn nach. Reporte:
[`NEWSLETTER-VERSAND-REPARATUR-2026-09-23.md`](../NEWSLETTER-VERSAND-REPARATUR-2026-09-23.md),
[`NEWSLETTER-KADENZ-ABSICHERUNG-2026-09-23.md`](../NEWSLETTER-KADENZ-ABSICHERUNG-2026-09-23.md).

---

## 7. Was diese Anleitung bewusst nicht einrichtet

* **Kein Postfach.** `news@` und `kontakt@` bleiben Weiterleitung/Adresse ohne
  eigene Mailbox; Antworten gehen an das persönliche Fach.
* **Kein SMTP-Relay.** Der Digest spricht die REST-API (`api.brevo.com/v3`),
  keinen SMTP-Versand aus dem Runner.
* **Keine zweite Wahrheit.** `data/newsletter_studio.json` bleibt die Quelle für
  Absender und Reply-To; `hugo.toml` ist versiegelt.
* **Kein Secret im Klartext.** API-Key, Zieladresse und List-Inhalte gehören
  weder ins Repo noch in Issues noch in Doku-Auszüge.

Weiter: [ANLEITUNG-NEWSLETTER.md](ANLEITUNG-NEWSLETTER.md) (Konto, Liste, Formular,
Rechtstexte) · [ANLEITUNG-NEWSLETTER-STUDIO.md](ANLEITUNG-NEWSLETTER-STUDIO.md)
(Layout-Engine, QA, ESP-Export) ·
[FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md](FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md)
(Runbook in Reihenfolge) ·
[DNS-CLOUDFLARE-GITHUB-PAGES.md](DNS-CLOUDFLARE-GITHUB-PAGES.md) (Website-DNS).
