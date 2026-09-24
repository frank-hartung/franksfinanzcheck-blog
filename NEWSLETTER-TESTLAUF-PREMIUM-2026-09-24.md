# Newsletter-Testlauf Premium-Reparatur – Report 24.09.2026

**Anlass:** Lauf **#26** von *Newsletter-Daily (Capture-Wache + Digest)*
(Actions-Run `36024129599`, 24.09.2026, `workflow_dispatch` mit
`test_adresse=frankhartung@web.de, kontakt@franksfinanzcheck.de`) endete rot:
„Digest-Versand fehlgeschlagen (Exit 1) – es ist nichts versandt.
❌ Versand fehlgeschlagen (HTTP 400: Test emails cannot be sent to
non-existent/blacklisted/without-contact-list users · invalid_parameter).“

**Einordnung, ehrlich:** #26 war kein neuer Gegner, sondern die Quittung für
die Reparatur von #23 – ein Fehler zweiter Ordnung. Der #23-Fix
(`NEWSLETTER-PROBELAUF-REPARATUR-2026-09-24.md`) stellte den Probelauf so auf:
Vorprüfung legt den fehlenden Kontakt an (**ohne** Listen-Eintrag), der
Nachtrag holt die Liste nach, „wenn Brevo genau das verlangt“. Was niemand
maß: Brevo verlangt es in genau dem Fall **ohne Adressliste** – die generische
Absage nennt keine einzige Adresse, also gab es für den Nachtrag nichts
nachzutragen. Die Vorprüfung produzierte deterministisch den Zustand (Kontakt
da, null Listen), an dem der erste `sendTest` deterministisch starb – und der
Retry schaute zu, weil er nur das dokumentierte Format mit
`blackListedEmails` & Co. verstand. Zwei Anläufe, zwei Adressen, null Mails:
nicht trotz, sondern wegen der Mechanik.

---

## 1. Befunde

### F1 – Die Vorprüfung erzeugte den Zustand, an dem der Versand starb

`testadressen_pruefen()` legte fehlende Kontakte an, prüfte die
Listen-Zugehörigkeit aber nie – sie kannte die Zielliste nicht einmal (kein
`liste`-Parameter). Jeder Probelauf an einer frischen Adresse endete damit bei
`sendTest` in genau der Absage, die der Retry nicht lesen konnte (F2).

**Behoben:** Die Vorprüfung misst jetzt alle drei Brevo-Bedingungen (Kontakt?
Sperre? Liste?) und nimmt einen Kontakt ohne Liste **VORAB** in die Zielliste
auf – mit Freigabe (`test_kontakt`, Default an), mit Protokoll, mit Quittung.
Der erste `sendTest` gelingt dadurch sofort; der Fehler wird verhindert, statt
repariert. Ohne Freigabe bricht derselbe Zustand mit Klickweg ab, bevor eine
Kampagne oder ein Kontakt entsteht.

### F2 – Die generische Absage hatte keinen Leser

Brevo kennt zwei 400-Formen für `sendTest`: die dokumentierte („…could not be
sent to the following email addresses“ + Adresslisten) und die generische
(„…cannot be sent to non-existent/blacklisted/without-contact-list users“,
ohne jede Liste – belegt im eigenen Lauf #26 wie in
vjpixel/diaria-studio#8436). `testmail_abweisung()` verstand nur die erste;
für die zweite gab es keinen Nachtrag, keinen Retry, keinen Klickweg – nur den
rohen Anbietersatz.

**Behoben:** `testmail_generisch()` erkennt das Format am `message`-Feld
(kompakt-normalisiert, damit der Feldname `withoutListEmails` der anderen Form
nicht fälschlich zieht); `testmail_nachtragen()` misst dann jede Adresse
einzeln nach (Kontakt? Sperre? – eine gesperrte Adresse rutscht nie in den
Nachtrag), trägt Kontakt (idempotent) und Liste nach und wiederholt **genau
einmal**. `testmail_hinweis()` übersetzt das nicht Reparierbare – Sperrliste
nur, Tageslimit (50/Tag), generische Absage nach gescheitertem Nachtrag – in
den Klickweg; Unbekanntes bleibt ohne Deutung.

### F3 – Der Teilerfolg log („alle“ nach Retry an „eine“)

Erreichte der Retry nur eine Teilmenge (klassisch: eine Adresse gesperrt, eine
repariert), meldete der Lauf trotzdem „✅ Testversand an A, B“ – und verbuchte
den Status für alle. Bei zwei Adressen ist das die Lüge, die #26 hinterlassen
hätte.

**Behoben:** `versandt_an` trägt, an wen der erfolgreiche Aufruf wirklich
ging. Voller Erfolg → ✅ + Status; Teil → **TEILVERSAND** (rc 1, damit der
Befund im Alerting landet; erreich­te und unerreichte Adressen je beim Namen,
„nichts versandt“ kommt nicht vor); nichts → ❌ wie bisher. Der Workflow
spricht TEILVERSAND als eigene Annotation („TEILWEISE zugestellt“) aus.

### F4 – Ein Test-Glitch blockierte den echten Versand

Der UNKLAR-Zweig (Antwort verloren, Akte unlesbar) setzte `versand_unklar`
immer – auch für einen `sendTest`, dessen Doppelung harmlos ist und der über
die Liste nichts aussagt. Ein Test mit Netzflackern hätte den nächsten
Live-Versand angehalten, bis ein Mensch den Block löst.

**Behoben:** Der Halt bleibt dem Live-Versand vorbehalten. Der Test meldet
TESTVERSAND-STATUS UNKLAR (eigene Workflow-Annotation: erneut laufen lassen
ist gefahrlos, kein Halt gesetzt) und verbucht nichts.

### F5 – Die Doku versprach „Liste unangetastet“

`ANLEITUNG-NEWSLETTER.md` behauptete an zwei Stellen, der Probelauf fasse die
Liste nicht an – seit dem Vorab-Eintrag falsch, und falsch in die Richtung,
die Vertrauen kostet (eine Testadresse in „Blog-Abonnenten“ ist sichtbar).

**Behoben:** Beide Stellen nennen jetzt den Vorab-Eintrag mit Grund und
Schalter; die Checkliste (6a + Schritt 4) beschreibt Vorab-Mechanik,
Beide-Formate-Nachtrag und TEILVERSAND – plus die Falle der konkreten
#26-Adressen: `kontakt@franksfinanzcheck.de` ist eine **Weiterleitung**, kein
Postfach; die Testmail landet im dahinterliegenden Zielpostfach (dort auch
Spam prüfen) und im Cloudflare-Routing-Log. Geht die eine Adresse und die
andere nicht, ist es die Weiterleitung, kein Versandfehler.

---

## 2. Was die Reparatur NICHT ist

* **Kein Aufweichen der Verriegelung:** `NEWSLETTER_SEND=ja`, Secrets-Gate,
  Vorflug (Absender verifiziert? Liste vorhanden?), 0-Abonnenten-Sperre für
  Live, Duplikatschutz, QA-Gate und Versandpause bleiben unverändert; der
  Testversand bleibt ein `sendTest`, nie `sendNow`.
* **Kein Auto-Entsperren, kein stilles Abo:** Gesperrte Adressen werden nie
  angefasst (Vorprüfung wie Nachtrag); der Listen-Eintrag passiert nur mit
  Freigabe, nur für die eingetippten Testadressen, und steht im Protokoll –
  jede Mail trägt den Ein-Klick-Abmeldelink.
* **Kein zweiter Anlauf fürs Schreiben:** Kampagne anlegen und Senden laufen
  je genau einmal; der einzige Retry ist der quittierte Testmail-Nachtrag
  nach einem 400-Beleg, dass nichts rausging.

## 3. Beweise

| Prüfung | Ergebnis |
|---|---|
| `newsletter_digest.py --selftest` | **83 Fälle grün** (vorher 73) – neu: Vorab-Eintrag VOR der Kampagne mit genau EINEM `sendTest`; Kontakt-ohne-Liste ohne Freigabe bricht schreiblos ab; generische Absage mit Nachtrag genau einmal; TEILVERSAND mit beiden Namen; generisch-vs-dokumentiert-Trennung, Hinweis-Abdeckung |
| `scripts/tests/test_newsletter_digest.py` | **36 Tests OK** (1 übersprungen) – neu: generische Absage (Nachmessen, Sperre liegt, ohne Freigabe kein Schreiben), Hinweis-Klickwege (Sperre/Limit/generisch/unbekannt), TEILVERSAND-Ehrlichkeit, Test-UNKLAR ohne Listen-Halt |
| `scripts/tests/test_newsletter_schedule.py` | 26 Tests OK – unverändert grün (Probelauf verbraucht keinen Termin) |
| `test_newsletter*.py` gesamt | **179 Tests OK** (1 übersprungen) |
| `report_hygiene.py --check` | sortenrein (dieser Report ist von der Checkliste referenziert) |
| `git diff --check` | sauber |

## 4. Der Weg zur ersten Testmail (Reihenfolge zählt)

1. Actions → *Newsletter-Daily (Capture-Wache + Digest)* → *Run workflow*:
   `test_adresse` = `frankhartung@web.de, kontakt@franksfinanzcheck.de`,
   `live` **aus**, `tage` = 7, `test_kontakt` = **an** (Default).
2. Erwartet im Log: `ℹ️ Testadresse … als Kontakt angelegt` und/oder
   `ℹ️ … VORAB in die Zielliste … aufgenommen` (je nur, falls nötig), dann
   `✅ Testversand an frankhartung@web.de, kontakt@franksfinanzcheck.de
   (Kampagne …)` – plus je eine Mail: direkt in Frank's Postfach (web.de,
   auch Spam prüfen) und im Zielpostfach hinter `kontakt@…` (dort ebenfalls
   Spam + Cloudflare-Routing-Log prüfen).
3. Steht dort stattdessen TEILVERSAND oder ein Abbruch mit Klickweg, ist der
   Weg ausgeschrieben – kein Rätseln, kein Wiederholen ins Blaue.

**Offen zum Redaktionsschluss:** Der Beweis am echten Konto ist der Lauf mit
beiden Adressen selbst; er wird nach dem Merge dieses Branches gefahren. Die
Mechanik (Vorab-Eintrag, Beide-Formate-Nachtrag, TEILVERSAND) ist oben belegt,
die Zustellung in beide Postfächer ist Sache des Laufs – ein Report, der sie
vorwegnähme, wäre eine Behauptung.
