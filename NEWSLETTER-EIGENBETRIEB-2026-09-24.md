# Newsletter-Eigenbetrieb – Brevo-Ausstieg – Report 24.09.2026

**Anlass:** Dauerhafte Versandprobleme mit Brevo – im Test **und** im Live.
Die zuletzt dokumentierten Fälle (Run #26, „Test emails cannot be sent
to non-existent/blacklisted/without-contact-list users“, und davor die
#23-Reparatur) waren die Quittung für eine Struktur, nicht für einen
Codefehler: der kritische Pfad des Newsletters hing an einer fremden
Kampagnen-API, deren Kontakt-, Listen- und Testsemantik bei jedem
Änderungszyklus neu gelernt werden mussten – im öffentlichen Repo, mit
Adresslisten, die dort nichts zu suchen hatten, und mit einer Zustellung,
die sich nicht aus dem Repo beweisen ließ.

**Einordnung, ehrlich:** „Brevo zuverlässiger patchen“ war die falsche
Frage. Die richtige war: Wie viele bewegliche Teile muss ein
Newsletterlauf überleben? Die Antwort steht jetzt im Code: **einer
versendet** (GitHub Actions, Resend API als Default, SMTP schaltbar),
**einer sammelt** (Cloudflare Worker unter `abos.franksfinanzcheck.de`,
keine Mail), **null Adressen in Git** (Journal und Status tragen nur
Hashes, die Liste lebt in Cloudflare KV). Was Brevo als drei gekoppelte
Begriffe lieferte (Kampagne, Kontakt, Liste), ist jetzt: ein Mailer-Ruf,
ein KV-Speicher, ein Hash im Journal.

---

## 1. Architektur (die Entscheidung)

```
Besucher → /newsletter/ (Hugo) → POST Worker abos.franksfinanzcheck.de
            (KV: Adresse + Token + Themen + Consent-Nachweis;
             Double-Opt-In, One-Klick-Abmeldung, Präferenzen)
            → Dispatch → GitHub Actions (Bestätigungsmail, 14 Tage)
Besucher ← Resend API ← GitHub Actions daily 05:05 UTC (Di/Fr)
   Mail-Links → Worker: /abmeldung?token=, /praferenzen?token=, /status?token=
```

1. **Repo ist öffentlich → keine PII in Git.** Die Adressliste existiert
   nur in Cloudflare KV. `data/newsletter_journal.jsonl` und
   `data/newsletter_state.json` tragen ausschließlich
   SHA1-Adresshashes + Zustandsdaten. Geprüft (24.09.2026): kein
   Adressstring in Commit, Journal oder State.
2. **Der Worker versendet keine Mail.** Capture und Zustellung sind
   unabhängig testbar; der teure Sende-Aufruf steht an genau einer
   Stelle (Actions), wo er von allen Wachen beobachtet werden kann.
3. **Token-Forms rendert der Worker, nicht der Blog.** Seit der
   Hugo-Template-Reform (≥0.146, hier 0.164) laufen
   Inline-Template-Actions in Page-Content nicht mehr; Query-Strings
   sieht der Build nie. Eine statische „Abmelde“-Seite mit Token-Form
   wäre ein Knopf, der nur funktioniert – abgelehnt. Der Worker rendert
   die Journey-Seiten pro Anfrage (Token im HTML, normales POST-Formular,
   **ohne JavaScript** nutzbar); die Blog-Seiten
   `/newsletter/{bestaetigung,abmelden,praeferenzen}/` sind ehrliche
   Info-Seiten (Rechtliches, Wege, Daten) mit dem Wegweiser „der Link in
   deiner Mail ist die Aktion“.

## 2. Befunde

### F1 – Der Versand-Halt wurde angezeigt, aber nicht erzwungen

`sperre_pruefen` meldete `versand_unklar` in `main` – und `print`ete sie.
Ein Sende-Aufruf, der ohne Beleg geblieben ist, hätte also den nächsten
Listen-Versand nicht blockiert: genau das Doppelversand-Risiko, gegen das
die Sperre existiert. **Behoben:** Fail-Closed `return 1`. Der Testversand
(`--test-adresse`) ist ausdrücklich ausgenommen – er dupliziert keine
Ausgabe bei Subscribern, er ist die Suche nach dem Beleg. Test:
`test_newsletter_schedule.py::Versandpfad` (Halt blockt Listen-Versand,
blockt keinen Testversand; Reservierung verbraucht Termin; defekter Status
bleibt defekt).

### F2 – Die Journey passte nicht in einen statischen Build

Siehe Architektur-Entscheidung 3. Die drei Content-Seiten sind neu
geschrieben als Info-Seiten ohne JS/fetch-Maschinerie; die Aktion lebt im
Worker (`/abmeldung?token=` GET = One-Klick = List-Unsubscribe,
`/praferenzen?token=` pre-checked Formular). Worker-Tests: 38/38,
darunter Formular-Roundtrip **ohne** JavaScript.

### F3 – Ein leerer Capture-Endpunkt war ein Formular, das nur so tat

`newsletterFormAction` leer = Formular ohne Ziel. Seit dem
KRITISCH-Siegel im Integrity-Guard (Wert jetzt:
`https://abos.franksfinanzcheck.de/anmeldung`) und der Capture-Wache
(`--check`, N-Regeln gegen den echten Build) meldet jeder Lauf, ob der
Weg geschaltet ist – und die Studio-Wache `--brand` beweist, dass der
Wert auf der festen Worker-Subdomain bleibt.

### F4 – Zustellbarkeit wurde gehofft, jetzt wird gemessen

`scripts/newsletter_zustellbarkeit.py` (neu geschrieben) misst statt zu
annehmen: C1–C6 (SPF `include:resend.net`, beide Resend-DKIM-TXTs, DMARC
mit `rua` und Policy-Konsistenz, MX der Zone und der Absender-Domain),
C7 (Worker: CNAME + HTTPS-Antwort; ein Cloudflare-Kantenblock 403/1010
wird als **eigener Befund** gemeldet, nicht als „Absender-Problem“
verallgemeinert), B0–B3 (API-Netzweg 401-vs-Kante, Domain verifiziert,
Abonnentenstand aus dem **Worker-Export unabhängig vom Resend-Key**,
Free-Grenze), S1–S3 (Halt, pending, letzte_ausgabe). Grundsatz:
**Ohne Messung kein Grün** – `nicht gemessen` statt stiller Bestätigung.

### F5 – Idempotenz gegen die doppelte Ausgabe

`letzte_ausgabe` (Datum + Betreff) plus versandene Artikel-Hashes im
State: ein zweiter Lauf derselben Ausgabe springt bediente Empfänger
über. Der 4-Lauf-Lifecycle im Selftest (komplett → idempotent →
Teilverband → Nachgang) friert das ein.

### F6 – Brevo ist vollständig raus

Code, Workflows, Doku, Datenschutz, Wachen-Referenzen, QA-Hostliste:
keine Brevo-Stelle außer bewussten historischen Notizen („BREVO IST
RAUS“) in Modul-Köpfen. Gelöscht: `ANLEITUNG-NEWSLETTER.md`,
`FREISCHALTUNG-NEWSLETTER-CHECKLISTE.md`,
`NEWSLETTER-ZUSTELLBARKEIT-CLOUDFLARE-BREVO.md`.

## 3. Was gebaut ist (und was es beweist)

| Baustein | Beweismittel | Stand |
|---|---|---|
| Capture-Worker (`newsletter-worker/`) | `node --test` 38/38 | gebaut, **noch nicht deployed** |
| Digest (`scripts/newsletter_digest.py`) | Selftest 50, unittests 22 | gebaut |
| Mailer (`scripts/newsletter_versand.py`) | Selftest 28 | gebaut |
| Zustellbarkeits-Wache | Selftest 25, unittests 37 | gebaut |
| Workflows (daily neu verdrahtet, lifecycle neu) | Wachen-Schritt im Lauf | gebaut |
| Studio + Themen-Vertrag (JSON ↔ wrangler.toml) | Selftest 48, `--brand` | gebaut |
| QA (21 Regeln), Cadence (Di/Fr-Vertrag) | Selftests 40 / 14 | gebaut |
| Journey (Worker-GETs + drei Info-Seiten) | Worker-Tests + Site-Test 22 | gebaut |
| Rechtstexte (Datenschutz § 8: Resend + Cloudflare, DPA/DPF) | Site-Test (Pflichtbegriffe) | gebaut |
| Doku (`docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md`) | Site-Test (Doku-Existenz, keine überholten Versprechen) | gebaut |
| Build | `hugo --minify` sauber | gebaut |

## 4. Was NICHT erledigt ist (ehrlich)

1. **Worker-Deployment:** Kein Cloudflare-Account in dieser Umgebung.
   `wrangler login/deploy`, KV `ABO`, Secrets `GITHUB_PAT` + `EXPORT_KEY`,
   CNAME `abos` – steht in der Anleitung § 3 Schritte 1–2.
2. **Resend-Konto + Domain:** Signup, `franksfinanzcheck.de` als
   Sending Domain, SPF `include:resend.net` in den **einen** SPF-Record,
   `_resend`/`_resend2` TXTs, DMARC – Anleitung § 3 Schritt 3.
3. **GitHub Secrets:** `RESEND_API_KEY`, `NEWSLETTER_WORKER_EXPORT_KEY`
   (= Worker `EXPORT_KEY`), Variable `NEWSLETTER_WORKER_BASE` – § 3/4.
4. **Push/PR:** Das GitHub-Token dieser Umgebung ist abgelaufen
   (`gh auth status`: „token in GH_TOKEN is no longer valid“) – der
   Push auf `arena/01a0d446-franksfinanzcheck-blog` und der PR nach
   `main` stehen aus, bis der GitHub-Login verbunden ist. Die Commits
   liegen im Working Tree (5 Commits auf `f11c9b5`).
5. **Der eine Schalter:** `hugo.toml` trägt **bereits** den
   Worker-Endpunkt (Endzustand). Daraus folgt die Reihenfolge:
   **Schritte 1–4 zuerst, dann mergen.** Vorher merged, zeigt die Site
   „Anmeldung aktiv“ auf einen noch nicht erreichbaren Endpunkt –
   der Daily-Lauf meldet das sofort laut (C7 + `--strict-inert`),
   aber die Minuten gehören dem Besucher, nicht der Wache.

## 5. Was der Betreiber als Nächstes tut (Reihenfolge)

1. Worker deployen (`newsletter-worker/`, `wrangler`), KV + Secrets.
2. CNAME `abos` → Worker-Domain (orange cloud); `/healthz` prüfen.
3. Resend: Domain + DNS (SPF/DKIM/DMARC), API-Key.
4. GitHub: Secrets + Variablen (Anleitung § 3/4).
5. `python3 scripts/newsletter_zustellbarkeit.py --pruefen` → kein Fund.
6. **Mergen** (bzw. den Stand übernehmen) – die Wachen laufen.
7. Testlauf: Workflow `test_adresse` = eigene Adresse →
   `✅ TESTVERSAND ERFOLGT: 1 Adresse(n)`.
8. Erster regulärer Versandtag (Di/Fr 05:05 UTC): 0 Abonnenten =
   ehrliche Leermeldung, keine Mail.
9. Secrets, die Brevo je betraut haben, in GitHub löschen
   (Rotation ist kostenlos; ein toter Key in den Settings ist ein
   Einladungsschreiben).

---

## Korrektur (25.09.2026): Resend-DNS-Modell

Dieser Report ging für Schritt 5/6 vom SPF/DKIM-Bild aus, das bei der
Programmierung galt (`include:resend.net` in der Apex-SPF + zwei DKIM-
Selektoren). Die aktuelle offizielle Resend-Dokumentation (SES-Modell)
verlangt stattdessen: **SPF-TXT + Bounce-MX auf der `send.`-Subdomain**,
**ein** DKIM-TXT (`resend._domainkey`), **Apex-SPF unverändert**, DMARC
unverändert (steht bereits in der Zone). Zustellbarkeits-Wache (C2/C3)
und `docs/ANLEITUNG-NEWSLETTER-EIGENBETRIEB.md` § 3 sind darauf
umgestellt; die Zeilen in § 4 (F4) und § 5 (Schritt 3) dieses Reports
sind entsprechend zu lesen. Außerdem: der Mailer schaltet
`open_tracking`/`click_tracking` jetzt explizit **aus** (sonst würde der
Resend-Konto-Default greifen und das „kein Tracking"-Versprechen brechen).
Alles Weitere in diesem Report gilt.
