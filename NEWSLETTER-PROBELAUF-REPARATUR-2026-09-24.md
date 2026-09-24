# Newsletter-Probelauf-Reparatur – Report 24.09.2026

**Anlass:** Lauf **#23** von *Newsletter-Daily (Capture-Wache + Digest)*
(Actions-Run `36015927654`, 24.09.2026 14:52 UTC, `workflow_dispatch` mit
`test_adresse`) endete rot:
„Digest-Versand fehlgeschlagen (Exit 1) – es ist nichts versandt.
❌ Kampagne nicht angelegt (HTTP 400: There are no contacts associated with the
given recipients info · invalid_parameter).“

**Einordnung, ehrlich:** Der Fehler saß weder in der Testadresse noch am
Anbieter – er saß **im Probelauf selbst**. Seit der Versand-Reparatur (23.09.,
`NEWSLETTER-VERSAND-REPARATUR-2026-09-23.md`) war die Kette technisch in
Ordnung, aber sie konnte den in Checkliste 6a dokumentierten Weg nicht gehen:
Die TEST-Kampagne trug `recipients.listIds` auf „Blog-Abonnenten“ mit **0
Abonnenten**, und Brevo löst die Empfänger bereits beim **Anlegen** der
Kampagne auf. Ein Probelauf, der die Liste braucht, die er noch nicht haben
darf, ist per Konstruktion unmöglich – deshalb kam über zwei Anläufe hinweg
keine Testmail an, obwohl „nur“ eine Adresse das Ziel war.

---

## 1. Befunde

### F1 – Die TEST-Kampagne trug Empfänger (auf eine leere Liste)

`kampagnen_payload()` setzte `recipients.listIds` **immer** – auch für den
Probelauf. `vorflug()` prüft „0 Abonnenten“ bewusst nur für den echten
Listen-Versand (sonst wäre der Probelauf vor den ersten Abonnenten blockiert);
Brevo prüfte dann selbst und lehnte schon das **Anlegen** ab:
`HTTP 400 · invalid_parameter · "There are no contacts associated with the
given recipients info"`. Der `sendTest` wurde nie erreicht, es ging nichts
raus.

**Behoben:** Eine TEST-Kampagne wird **ohne `recipients`** angelegt – das Feld
ist im `CreateEmailCampaign`-Schema optional, und `sendTest` braucht nur
`emailTo` (Quelle: developers.brevo.com/reference/create-email-campaign bzw.
`…/send-test-email`). Der Live-/Cron-Versand bleibt unverändert streng:
`recipients.listIds` ist dort Pflicht, die 0-Abonnenten-Sperre greift weiter.
Die Testkampagne heißt jetzt sprechend `TESTLAUF <Datum> – Probe an <Adressen>`,
der Listen-Versand weiter `Digest <Datum>`.

### F2 – Brevo nimmt Testmails nur an „richtige“ Kontakte

Die offizielle 400-Antwort von `sendTest` nennt drei Adressklassen:
`blackListedEmails`, `unexistingEmails`, `withoutListEmails` – also gesperrte,
unbekannte und Kontakte **ohne Listen-Zugehörigkeit**. Der Lauf hatte keine
Vorprüfung; er hätte die Absage erst nach dem Anlegen der Kampagne gesehen.

**Behoben:** `testadressen_pruefen()` misst jede Testadresse **vor** der
Kampagne (`GET /v3/contacts/{email}`: Kontakt? `emailBlacklisted`? `listIds`?)
und ist fail-closed: Ein unklarer Ausgang bricht ab, statt zu senden. Ein
fehlender Kontakt wird – nur mit Freigabe – als Kontakt angelegt
(`POST /v3/contacts` mit `updateEnabled: true`, **ohne** Listen-Eintrag, also
kein Abo nebenbei). Eine Sperre wird **nie** automatisch gelöst: „Unblock“ ist
eine Betreiber-Entscheidung (Beschwerde/Bounce), der Befund nennt den Klickweg.

### F3 – Die Absage kam als nackter Anbieter-Satz an

`❌ Versand fehlgeschlagen (HTTP 400: Test email could not be sent to the
following email addresses · invalid_parameter)` sagt einem Betreiber nicht,
welche Adresse warum abgelehnt wurde und was zu tun ist.

**Behoben:** `testmail_abweisung()` zerlegt die Antwort in die drei Klassen;
`testmail_nachtragen()` repariert **nur** die reparierbaren Klassen (fehlender
Kontakt → `POST /v3/contacts`; ohne Liste → `POST
/v3/contacts/lists/{id}/contacts/add`, das hinzufügt statt zu ersetzen) und
wiederholt `sendTest` danach **genau einmal**. Ein 400 ist der Beleg, dass
nichts rausging – der Retry ist also kein Doppelversand. Gesperrte Adressen
werden nicht angefasst. Bekannte Absagen (leere Liste, DMARC, Konto-Validierung,
Guthaben) bekommen über `kampagnen_absage_hinweis()` ihren nächsten Schritt;
unbekannte Absagen bleiben **ohne erfundene Deutung**.

### F4 – Die Freigabe ist ein Schalter, kein Automatismus

Neue Workflow-Eingabe **`test_kontakt`** (Default: **an**) steuert, ob der Lauf
im Brevo-Konto schreiben darf; `--test-kontakt-nicht-anlegen` invertiert sie auf
der Kommandozeile. Mit „aus“ endet ein fehlender oder gesperrter Kontakt in
einem Abbruch mit Klickweg – **ohne jeden Schreibzugriff**; das ist die Wahl des
Betreibers, nicht des Werkzeugs.

---

## 2. Was die Reparatur NICHT ist

* **Kein Aufweichen der Verriegelung:** `NEWSLETTER_SEND=ja`, Secrets-Gate
  (ohne `BREVO_API_KEY`/`BREVO_LIST_ID` kein Netzversuch), Vorflug,
  0-Abonnenten-Sperre, Duplikatschutz und Versandpause bleiben unverändert.
* **Kein Listen-Versand im Probelauf:** eine TEST-Kampagne trägt keine
  Empfänger, `sendTest` trifft genau die eingegebenen Adressen. Nur wenn Brevo
  die Adresse als „ohne Liste“ abweist, wird sie nachgetragen – und jede Mail
  trägt den Ein-Klick-Abmeldelink.
* **Kein Auto-Entsperren:** `blackListedEmails` bleibt gesperrt (F2), der
  Befund nennt den Unblock-Klickweg statt ihn zu gehen.

## 3. Beweise

| Prüfung | Ergebnis |
|---|---|
| `newsletter_digest.py --selftest` | **73 Fälle grün** – neu: „Probelauf an leerer Liste“ mit Brevo-Nachbau (ABLEHNUNG bei `recipients` auf leerer Liste, Kontakt-/Listen-Nachtrag **genau einmal**, Sperre ohne Auto-Entsperren) |
| `scripts/tests/test_newsletter_digest.py` | 32 Tests OK (1 übersprungen) – neu: Payload ohne `recipients`, Vorprüfung mit/ohne Freigabe, Absage-Klassen, Retry-Zählung |
| `scripts/tests/test_newsletter_schedule.py` | angepasst: der Testversand-Mock kennt die Kontakt-Vorprüfung; 175 Newsletter-Tests gesamt **OK** (1 übersprungen) |
| Root-Hygiene (`report_hygiene.py --check`) | sortenrein – dieser Report ist von der Checkliste referenziert |

## 4. Der Weg zur ersten Testmail (Reihenfolge zählt)

1. Actions → *Newsletter-Daily (Capture-Wache + Digest)* → *Run workflow*:
   `test_adresse` = deine Adresse (mehrere mit Komma), `live` **aus**,
   `tage` = 7, `test_kontakt` = **an** (Default).
2. Erwartet im Log: `ℹ️ Testadresse … als Kontakt angelegt` (nur falls nötig),
   `ℹ️ … in die Zielliste … aufgenommen` (nur wenn Brevo es verlangt) und
   `✅ Testversand an <Adresse> (Kampagne …)` – plus die Mail im Postfach.
3. Steht dort stattdessen ein Abbruch mit Klickweg, ist der Weg ausgeschrieben
   (Contacts → *Add a contact* / Kontakt → *Unblock*) – kein Rätseln.

**Offen zum Redaktionsschluss:** Der Beweis am echten Konto ist der Lauf mit
`test_adresse=frankhartung@web.de` selbst; er wird nach dem Merge dieses
Branches gefahren. Die Testlauf-Mechanik ist oben belegt, die Zustellung
(Frank's Postfach) ist Sache des Laufs – ein Report, der sie vorwegnähme,
wäre eine Behauptung.
