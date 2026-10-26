---
title: "Datenschutzerklärung"
description: "Datenschutzhinweise zu Hosting, eigenem Klickzähler, Affiliate-Links, Newsletter, Feedback und deinen Rechten"
draft: false
showToc: true
---

## 1. Datenschutz auf einen Blick

### Verantwortliche Stelle

**Frank Hartung**
Karl-Marx-Str. 13
19376 Ruhner Berge OT Marnitz
Deutschland

**Kontakt:** E-Mail: kontakt@franksfinanzcheck.de

Verantwortlich im Sinne der Datenschutz-Grundverordnung (DSGVO) und anderer Datenschutzvorschriften ist der oben genannte Betreiber dieser Website.

### Das Wichtigste in Kürze

- **Cookielose Analytics (Umami, optional, noch nicht aktiv).** Wir haben **ein Tracking-Skript vorbereitet** (Umami, selbst gehostet auf stats.franksfinanzcheck.de), das Seitenaufrufe aggregiert ohne Cookies, ohne IP-Speicherung und ohne Daten an Dritte zu senden. Einbindung: `layouts/_partials/umami.html` — das Skript wird **nur geladen, wenn** in `hugo.toml` `params.analytics.umami.website` gesetzt ist (aktuell: **nicht gesetzt** → kein Tracking). Die Umami-Instanz (Web-UI, API-Zugang für Reports) ist **kostenpflichtig im Gratisplan** und wird **nicht genutzt**: Kein API-Token, keine API-Importe. Tracking (Skript) und Dashboard-API sind zwei verschiedene Dinge — dieses Projekt nutzt nur das Skript. Ausführliche Angaben: Abschnitt 2 unten und `layouts/_partials/umami.html` im Quelltext. Eine Einwilligung ist nicht erforderlich. Du kannst den Einsatz durch Browsereinstellungen (Script-Blockierung für `stats.franksfinanzcheck.de`, Privacy Badger etc.) einschränken.
- **Eigener Klickzähler ohne Cookies.** Wir zählen, wie oft Partnerlinks angeklickt werden – als Tageszähler je Partner und Artikel. Wir speichern dabei weder Cookies noch deine IP-Adresse. Wenn dein Browser „Do Not Track“ oder „Global Privacy Control“ meldet, wird nichts gezählt.
- **Affiliate-Partner.** Beim Klick auf einen Partnerlink verlässt du unsere Website. Dann gelten die Datenschutzhinweise und Cookie-Einstellungen des Partners.
- **Newsletter und Feedback** sind freiwillig. Für den Newsletter gilt das Double-Opt-In.
- **Keine Einwilligung nötig für den Betrieb der Website.** Für die Partnerseiten entscheidet der jeweilige Anbieter selbst.

---

## 2. Übersicht der Verarbeitungen

| Verarbeitung | Zweck | Rechtsgrundlage | Speicherdauer | Empfänger |
|---|---|---|---|---|
| Aufruf der Website (Server-Logfiles) | Auslieferung, Sicherheit, Stabilität | Art. 6 Abs. 1 lit. f DSGVO | Vom Hosting-Anbieter festgelegt; wir haben darauf keinen Einfluss | GitHub (Hosting); Cloudflare (DNS) |
| Klickzähler für Partnerlinks (`/go/`) | Aggregierte Zählung von Klicks je Partner und Artikel | Art. 6 Abs. 1 lit. f DSGVO | Tageszähler bis zu 13 Monate | Cloudflare (Workers und Datenbank) |
| Feedback „War dieser Ratgeber hilfreich?“ | Verbesserung der Ratgeber, Schutz vor Mehrfachabgaben | Art. 6 Abs. 1 lit. f DSGVO | Missbrauchsschutz-Hash 6 Stunden; Zähler ohne Personenbezug | Cloudflare (Workers) |
| Newsletter-Anmeldung und -Versand | Versand des Newsletters, Nachweis der Einwilligung | Art. 6 Abs. 1 lit. a und f DSGVO | Siehe Abschnitt 8 | Cloudflare, GitHub, Resend |
| Kontakt per E-Mail | Bearbeitung deiner Anfrage | Art. 6 Abs. 1 lit. b oder lit. f DSGVO | Bis zur Erledigung, danach nach gesetzlichen Fristen | E-Mail-Dienst des Betreibers |
| Klick auf Partnerlink | Vermittlung, Provision | Art. 6 Abs. 1 lit. f DSGVO (unsere Verlinkung); beim Partner nach dessen Regeln | Nach den Richtlinien des Partners | CHECK24, Tarifcheck24 bzw. deren Dienstleister |
| Website-Suche | Suche nach Inhalten | Keine Übermittlung an uns | Nur im Browser | Keine |
| Cookielose Analytics (Umami, Tracking-Skript, nach Activation) | Aggregierte Auswertung von Seitenaufrufen (URL, Referrer, Datum, Browser-Sprache) ohne Cookies, ohne IP-Speicherung | Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse am Verbesserung des Angebots); nach Aktivierung der Umami-Instanz | Server-Logs auf stats.franksfinanzcheck.de (selbst gehostet); aggregiert, nicht personenbezogen | Keine (selbst gehostet, keine Dritt übermittlung) |
| Umami Dashboard-API (nicht genutzt) | Automatisierte Datenimporte, Reports per API-Token | NICHT ANGESPROCCHEN — API-Zugang nicht im Gratisplan verfügbar (vgl. AFFILIATE-MASTERPLAN 11.10.2026); kein API-Token in hugo.toml | keine | keine |
| Zwischenspeicher (Service Worker) | Schnellere Ladezeiten | § 25 Abs. 2 TDDDG (technisch erforderlich) | Bis zum Löschen der Browserdaten | Keine |

Ob ein Speichern oder Auslesen von Informationen auf deinem Endgerät erlaubt ist, richtet sich nach § 25 TDDDG. Die DSGVO-Rechtsgrundlage ist davon getrennt. Details zu Browser-Speichern stehen in Abschnitt 7.

---

## 3. Hosting, Domain und Server-Logfiles

### Hosting

Diese Website wird von **GitHub Pages** ausgeliefert (GitHub, Inc., 88 Colin P. Kelly Jr. Street, San Francisco, CA 94107, USA). Die Domain franksfinanzcheck.de zeigt direkt auf die Server von GitHub Pages. Zum Stand 11. Oktober 2026 ist kein Proxy von Cloudflare vor die Website geschaltet.

GitHub verarbeitet beim Abruf technische Zugriffsdaten wie IP-Adresse, Zeitpunkt, angeforderte Adresse, Browsertyp und Referrer. Die Server stehen auch außerhalb der EU, insbesondere in den USA. Weitere Informationen: [GitHub-Datenschutzerklärung](https://docs.github.com/en/site-policy/privacy-policies/github-privacy-statement).

**Rechtsgrundlage:** Art. 6 Abs. 1 lit. f DSGVO (sicherer und stabiler Betrieb der Website).

### Domain und DNS

Die Verwaltung der Domain (DNS) übernimmt **Cloudflare, Inc.** (101 Townsend St., San Francisco, CA 94107, USA). Cloudflare erhält dabei keine Informationen über Seitenaufrufe, sondern nur die Auflösung des Domainnamens. Weitere Informationen: [Cloudflare-Datenschutzhinweise](https://www.cloudflare.com/privacypolicy/).

### Server-Logfiles

Der Hosting-Anbieter erstellt automatisch Server-Logfiles mit: Browsertyp und -version, Betriebssystem, Referrer-URL, Hostname des zugreifenden Rechners, Uhrzeit der Anfrage und IP-Adresse. Wir führen diese Daten nicht mit anderen Quellen zusammen und haben keinen Zugriff auf die Logfiles des Hosting-Anbieters. Die Aufbewahrungsfristen legt der Anbieter fest.

---

## 4. Schriftarten und eingebundene Dateien

Diese Website verwendet die Schriftfamilien **Inter** und **Playfair Display**. Die Schriftdateien liegen auf unserem Hosting. Beim Aufruf entsteht **keine Verbindung zu Google Fonts** (fonts.googleapis.com, fonts.gstatic.com), und es werden keine Daten an Google übermittelt.

Alle Skripte und Stylesheets dieser Website werden von unserem Hosting ausgeliefert. Es sind keine Videos, Karten, Social-Media-Widgets oder sonstigen Fremdinhalte eingebettet, die beim Seitenaufruf Verbindungen zu Dritten aufbauen.

---

## 5. Klickzähler für Partnerlinks (`/go/`)

{{< klickmessung_status >}}

### Was passiert

Partnerlinks in unseren Artikeln führen zunächst auf eine Übergabeseite unter `/go/<partner>/` auf unserer Website. Diese Seite sendet beim Aufruf einen Zählimpuls an unseren eigenen Zähler unter `stats.franksfinanzcheck.de`, einen Cloudflare Worker. Danach leitet die Seite dich weiter zum Partner.

Der Zählimpuls enthält nur:

- Den Partner-Schlüssel (z. B. „strom“ oder „haftpflicht“),
- die Artikel-Kennung aus dem Link (den Artikel-Slug, z. B. „2026-10-02-gasabschlag-…“).

### Was nicht passiert

- Es wird **kein Cookie** gesetzt und kein Gerät wiedererkannt.
- Wir speichern **keine IP-Adresse**, keinen User-Agent, keinen Referrer und keine Kennung.
- Es entsteht **kein Nutzerprofil**. Gespeichert wird nur, wie viele Klicks es an einem Tag je Partner und Artikel gab.
- Bei Do-Not-Track oder Global Privacy Control wird **nichts gesendet**. Der Zähler ignoriert solche Anfragen außerdem auf dem Server.

### Technischer Hinweis zur IP-Adresse

Damit der Zählimpuls ankommt, wird deine IP-Adresse technisch über die Netzinfrastruktur von Cloudflare übermittelt. Cloudflare verarbeitet sie dabei zur Verbindung. Wir speichern sie nicht. Zum Schutz vor Missbrauch (massenhaft gefälschte Klicks) nutzt der Zähler die IP-Adresse außerdem kurzzeitig für eine Mengenbegrenzung: Cloudflare zählt dafür höchstens 60 Sekunden lang mit, wie viele Zählimpulse von derselben Verbindung kommen. Die IP-Adresse wird dabei nicht in unserer Datenbank gespeichert und nicht mit den Tageszählern verknüpft.

### Rechtsgrundlage und Speicherdauer

- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f DSGVO. Wir haben ein berechtigtes Interesse daran zu erfahren, welche Ratgeber zu Partnerangeboten führen. Die Auswertung erfolgt ausschließlich aggregiert.
- **§ 25 TDDDG:** Es werden keine Informationen auf deinem Gerät gespeichert oder ausgelesen.
- **Speicherdauer:** Die Tageszähler werden höchstens 13 Monate aufbewahrt und danach gelöscht.
- **Empfänger:** Cloudflare (Workers und Datenbank) als Dienstleister.

---

## 6. Affiliate-Partner und Provisionen

Diese Website nimmt an Partnerprogrammen teil. Kommt über einen Partnerlink ein Vertrag oder Kauf zustande, erhalten wir eine Provision. Für dich entstehen dadurch **keine Mehrkosten**. Alle Affiliate-Links sind als Werbung gekennzeichnet.

| Partner | Angebote | Weiterleitung über | Datenschutzerklärung des Partners |
|---|---|---|---|
| **CHECK24** (CHECK24-Vergleichsportal GmbH, Erika-Mann-Str. 62, 80636 München) | Strom, Gas, DSL, Mobilfunk, Girokonto, Kredit, Kreditkarte, Tagesgeld, Kfz-Versicherung, Reisen, Mietwagen, Flüge | a.check24.net | https://www.check24.de/popup/datenschutz-check24-gmbh/ |
| **Tarifcheck24 GmbH** (Zollstr. 11b, 21465 Wentorf bei Hamburg) | Versicherungen: Haftpflicht, Hausrat, Unfall, Zahnzusatz, Reisekranken, Hunde, Wohngebäude | a.partner-versicherung.de | https://www.tarifcheck.de/datenschutz |

Die Partnerlinks führen direkt auf die Adressen der genannten Partner.

### Was beim Klick übergeben wird

Beim Weiterleiten übergeben wir in der Link-Adresse:
| Partner | Anbieter (Verantwortlicher) | Datenschutzerklärung |
|---|---|---|
| **CHECK24** (Strom, Gas, DSL, Girokonto, Kredit, Kfz, Reisen, Mietwagen, Flüge) | CHECK24-Vergleichsportal GmbH, Erika-Mann-Str. 62, 80636 München | https://www.check24.de/datenschutz/ |
| **Tarifcheck** (Versicherungen: Haftpflicht, Hausrat, Unfall, Zahnzusatz, Reisekranken) | Tarifcheck24 GmbH, Zollstr. 11b, 21465 Wentorf bei Hamburg | https://www.tarifcheck.de/datenschutz/ |

- Die **Artikel-Kennung** (SubID), damit sich Abschlüsse dem Artikel zuordnen lassen,
- **Kampagnen-Kennungen** (UTM-Parameter, z. B. `utm_source=franksfinanzcheck`, `utm_medium=affiliate`, `utm_campaign=<Kategorie>`).

Wir übergeben keinen Namen, keine E-Mail-Adresse und keine Angaben aus dem Newsletter.

### Was auf der Partnerseite passiert

Ab dem Klick gelten die Datenschutzhinweise des Partners. Dort können Cookies und ähnliche Technologien eingesetzt werden, auch zur Erfolgsmessung der Vermittlung. Die Einstellungen kannst du dort und in deinem Browser verwalten.

Wir erhalten von den Partnern Abrechnungsinformationen zu Provisionen. Welche Angaben darin enthalten sind, richtet sich nach den Vereinbarungen mit dem jeweiligen Partner. Wir betreiben keine eigene Verfolgung deines Verhaltens über die Partnerseiten hinaus.

**Rechtsgrundlage unserer Verlinkung:** Art. 6 Abs. 1 lit. f DSGVO (Finanzierung des redaktionellen Angebots). Für Cookies auf den Partnerseiten holt der jeweilige Anbieter die nötige Einwilligung ein. Unsere Website erteilt dafür keine Einwilligung.

<a id="partner-kennzeichnung"></a>

### Eingebettete Anbieterkennzeichnung im Impressum

Auf der Seite [Impressum](/impressum/) kannst du die Anbieterkennzeichnung des Tarifcheck-Partnerprogramms als eingebettetes Dokument laden. Das Dokument wird nicht automatisch beim Seitenaufruf abgerufen, sondern erst, wenn du die Schaltfläche „Angaben des Partners hier laden“ wählst (Zwei-Klick-Lösung). Dann ruft dein Browser ein Dokument von a.partner-versicherung.de ab (Partner-ID 47086). Dabei werden technische Zugriffsdaten an diesen Server übermittelt, insbesondere IP-Adresse, Zeitpunkt, Browserkennung und die Herkunft des Abrufs. Das eingebettete Dokument läuft in einer eingeschränkten Umgebung (sandbox): Es kann diese Seite nicht umleiten und keine Formulare absenden.

Ob der Anbieter dabei Cookies setzt, weitere Empfänger beteiligt oder Daten außerhalb der EU verarbeitet, ist anhand der Partnerunterlagen zu prüfen. Diese Erklärung behauptet das nicht.

Zweck: die vom Partnerprogramm geforderte, stets aktuelle Kennzeichnung der Unternehmen, die für Vergleichsformulare und die Vermittlung der darüber angefragten Versicherungen zuständig sind. Die Einbindung erfolgt nur auf der Impressumsseite, nicht auf Artikeln, Werkzeugen oder der Startseite.

Rechtsgrundlage unserer Einbindung: Art. 6 Abs. 1 lit. f DSGVO (berechtigtes Interesse an einer vollständigen Anbieterkennzeichnung und an der Einhaltung der Programmbedingungen); der Abruf findet nur statt, wenn du ihn ausdrücklich anforderst. Für ein Speichern oder Auslesen auf deinem Endgerät durch den Partner ist § 25 TDDDG eigenständig zu prüfen. Eine Einwilligung ist erforderlich, soweit keine Ausnahme greift. Ob eine Ausnahme greift, ist an der konkreten Technik des Dokuments noch nicht geprüft.

Die Kennzeichnung lässt sich auch direkt beim Partner öffnen, über den Link unter dem Dokument im Impressum.

---

## 7. Cookies und Speicher auf deinem Gerät

**Wir setzen keine Cookies für Analyse, Reichweitenmessung oder Werbung.** Frühere Einwilligungs-Cookies (`ff_cookie_consent` und `ff_analytics_consent_v2`) aus der Zeit vor der Entfernung der Reichweitenmessung löscht die Website beim Besuch automatisch. Die Partnerseiten können nach einem Klick eigene Cookies setzen (siehe Abschnitt 6).
Derzeit setzen wir **kein Analytics-Consent-Cookie** und zeigen keinen Analyse-Banner: Die Reichweitenmessung ist abgeschaltet. Ein noch vorhandenes früheres `ff_cookie_consent`-Cookie wird beim nächsten Besuch durch die Website gelöscht. Externe Partner können eigene Speichertechniken einsetzen, sobald du einen Partnerlink anklickst. Das Kennzeichnungsdokument des Tarifcheck-Partnerprogramms im Impressum wird erst nach deiner Auswahl geladen (Zwei-Klick-Lösung, siehe oben). Unsere Website kann die Einstellungen der Partner nicht verwalten.

Auf deinem Gerät können folgende lokale Speicherwerte liegen. Sie werden nur gesetzt, wenn du die jeweilige Funktion nutzt, und bleiben im Browser. Wir übertragen sie nicht an uns oder Dritte.

| Schlüssel / Funktion | Zweck und Auslöser | Löschen |
|---|---|---|
| `ff_nl`, `ff_nl_themen` | Statushinweis nach der Newsletter-Anmeldung bzw. Themenauswahl | Browserdaten löschen; die Themenauswahl wird nach erfolgreicher Anmeldung entfernt |
| `ff_fixkosten_cockpit_v1` | Fixkosten-Eingaben, nur wenn du „auf diesem Gerät speichern“ wählst | „Zurücksetzen“ im Werkzeug oder Browserdaten löschen |
| `ff_werkzeug_*_v1` | Eingaben einzelner Werkzeuge nach Aktivierung der lokalen Speicheroption | Speicheroption im Werkzeug deaktivieren oder Browserdaten löschen |
| `ff-voice-pos:*` | Leseposition beim freiwillig genutzten Vorlesewerkzeug | Im Werkzeug zurücksetzen oder Browserdaten löschen |

`localStorage` läuft nicht automatisch ab. Du kannst die Werte in den Browsereinstellungen jederzeit entfernen. Für Funktionen, die du ausdrücklich nutzt, greift die Ausnahme des § 25 Abs. 2 Nr. 2 TDDDG.

### Zwischenspeicher (Service Worker)

Zur Beschleunigung speichert ein Service Worker bereits geladene Schriftarten, Bilder und Dateien im Cache deines Browsers. Dabei werden keine Daten an uns oder Dritte übertragen. Den Cache kannst du durch Löschen der Browserdaten entfernen.

---

## 8. Newsletter / Kontaktaufnahme

{{< newsletter_status >}} Du kannst dich freiwillig über [die Anmeldeseite](/newsletter/) für den Newsletter anmelden. Wir verarbeiten deine E-Mail-Adresse, die gewählten Themen, den Zeitpunkt der Anmeldung und Bestätigung sowie IP-Adresse, Browserkennung (User-Agent) und Herkunft der Anmeldung. Die letzten drei Angaben dienen dem Nachweis der Einwilligung und dem Schutz vor Missbrauch.

- **Double-Opt-In:** Der Versand beginnt erst nach Klick auf den Bestätigungslink. Die Bestätigung ist 14 Tage lang möglich.
- **Inhalt:** bis zu zwei E-Mails pro Woche (dienstags und freitags) mit Spartipps, Fristen, Rechnern und gekennzeichneten Partnerlinks.
- **Rechtsgrundlagen:** Deine Einwilligung für den Versand (Art. 6 Abs. 1 lit. a DSGVO). Nachweis und Missbrauchsschutz (Art. 6 Abs. 1 lit. f DSGVO). Die Themenauswahl dient der Gestaltung des Newsletters.
- **Widerruf:** über den Abmeldelink in jeder E-Mail, über [das Abmeldeformular](/newsletter/abmelden/) oder per E-Mail an kontakt@franksfinanzcheck.de. Der Widerruf wirkt für die Zukunft und ist ohne Begründung möglich. Jede E-Mail enthält einen List-Unsubscribe-Header.
- **Speicherdauer:**
  - Aktive Adressen bleiben bis zur Abmeldung gespeichert.
  - Nach der Abmeldung werden Abo-Eintrag und Token innerhalb von 30 Tagen gelöscht.
  - Unbestätigte Anmeldungen werden nach Ablauf der Bestätigungsfrist (14 Tage) technisch spätestens nach 15 Tagen entfernt.
  - Der Nachweis der Anmeldung (E-Mail-Adresse, IP-Adresse, User-Agent und Zeitpunkte) wird bis zu drei Jahre gespeichert, soweit er zur Abwehr von Ansprüchen erforderlich ist.
  - IP-basierte Zähler für das Anmelde-Limit verfallen nach 15 Minuten.
  - Für den Schutz des Dienstes führen wir ein **Tagesbudget** der Anmeldungen (nur eine Zahl pro Kalendertag, kein Personenbezug). Ist es erreicht, nimmt der Dienst bis Mitternacht (UTC) keine neuen Anmeldungen mehr an; bereits angemeldete Abonnentinnen und Abonnenten können sich jederzeit weiter abmelden.
- **Bot-Schutz des Formulars:** Damit die Anmeldung nicht von Programmen für fremde Adressen missbraucht wird (Mail-Verstärker), prüft das Formular **Cloudflare Turnstile** – ein Dienst der Cloudflare, Inc., der ohne Cookies und ohne Nutzerprofil arbeitet („Managed Challenge"). Dabei wird nur die technische Frage „Mensch oder Programm?“ geprüft; es entstehen keine Werbe- oder Verlaufsprofile. Der Dienst wird **ausschließlich beim Absenden des Formulars** geladen, nicht beim Lesen der Seite. Details: https://www.cloudflare.com/privacypolicy/
- **Empfänger und Verarbeitung:** Das Anmeldeformular läuft über `abos.franksfinanzcheck.de`, einen Cloudflare Worker. Die Anmeldedaten liegen im Cloudflare Workers KV. Für den Versand stößt der Worker GitHub-Actions-Läufe an. Der Versand erfolgt über den Dienst **Resend**, der die E-Mails zustellt. Dabei können Daten in Drittländern verarbeitet werden (siehe Abschnitt 12). Die geltenden Verträge, Datenstandorte und Logfristen für Cloudflare und Resend sind anhand der Betreiberkonten gesondert zu überprüfen; eine ausschließliche EU-Speicherung wird nicht zugesichert.

**Kontakt per E-Mail:** Wenn du uns schreibst, verarbeiten wir deine Angaben (E-Mail-Adresse, ggf. Name, Inhalt der Nachricht) zur Bearbeitung deiner Anfrage. Die Daten löschen wir, sobald sie nicht mehr erforderlich sind und keine gesetzlichen Aufbewahrungspflichten entgegenstehen.

---

## 9. Feedback „War dieser Ratgeber hilfreich?“

Unter jedem Ratgeber kannst du mit „Ja“ oder „Nein“ abstimmen. Dabei sendet dein Browser deine Auswahl und die Artikel-Kennung an `abos.franksfinanzcheck.de/feedback`, einen Cloudflare Worker. Ohne Klick findet keine Übermittlung statt.

- **Zähler:** Der Worker speichert je Artikel nur die Anzahl der Ja- und Nein-Stimmen ohne Personenbezug.
- **Missbrauchsschutz:** Damit eine Person nicht mehrfach am selben Tag abstimmt, wird ein aus IP-Adresse und Artikel-Kennung gebildeter, gekürzter Hash im Tageszähler gespeichert. Der Hash ist kein Klartext. Er gilt dennoch als personenbezogenes Datum und wird mit der täglichen Zusammenfassung gelöscht, in der Regel innerhalb von 48 Stunden, technisch spätestens nach 8 Tagen. Die Zahl der gezählten Stimmen pro Tag ist begrenzt.
- **Rechtsgrundlage:** Art. 6 Abs. 1 lit. f DSGVO (Verbesserung der Ratgeber und Schutz vor Mehrfachabgaben).

---

## 10. Website-Suche

Die Suche läuft im Browser. Suchbegriffe werden nicht an einen Suchdienst übermittelt und nicht als Suchhistorie gespeichert. Der Browser lädt dafür statische Indexdateien von unserer Website.

---

## 11. Links und soziale Medien

- **Pinterest und Mastodon:** Wir verlinken unsere Profile. Es werden keine Daten an Pinterest oder Mastodon übermittelt, solange du den Link nicht anklickst. Für Pinterest ist die **Pinterest Europe Ltd.** (Palmerston House, 2nd Floor, Fenian Street, Dublin 2, Irland) verantwortlich: https://policy.pinterest.com/de/privacy-policy
- **Antworten auf Kommentare (Mastodon):** Wenn du unsere Beiträge öffentlich kommentierst, kann unser Antwort-Assistent deinen öffentlichen Kommentar abrufen, einordnen und einen Antwortentwurf vorbereiten; einfache Dankesantworten können automatisch gesendet werden, alles andere geben wir von Hand frei. Verarbeitet werden die Kommentar-Kennung, der Link zum Kommentar, der Kommentartext (gekürzt) und dein Benutzername. Den Benutzernamen speichern wir nur pseudonymisiert (verschlüsselter Hash), um dir nicht mehrfach kurz hintereinander zu Antworten. Kommentartexte offener Vorgänge werden nach Erledigung bzw. spätestens nach Ablauf der Freigabefrist entfernt. Die Bearbeitungsdaten liegen – der Benutzername nur pseudonymisiert – in unserem öffentlich einsehbaren Code-Repository bei GitHub (siehe Abschnitt 12). Für die Antworttexte nutzen wir KI-Dienste; dabei wird der Kommentartext an den jeweiligen Anbieter übermittelt. Rechtsgrundlage: Art. 6 Abs. 1 lit. f DSGVO (Beantwortung öffentlicher Anfragen zu unseren Beiträgen). Du kannst jederzeit widersprechen, z. B. per E-Mail an kontakt@franksfinanzcheck.de.
- **Kalender-Links:** Einzelne Seiten bieten Links zum Eintragen in einen Kalender an. Mit dem Klick öffnest du den jeweiligen Kalenderdienst, der die übergebenen Termindaten verarbeitet.
- **Andere externe Links:** Auf die Datenverarbeitung auf verlinkten Seiten Dritter haben wir keinen Einfluss. Dafür ist der jeweilige Betreiber verantwortlich.

---

## 12. Empfänger, Auftragsverarbeitung und Drittlandübermittlung

Wir setzen folgende Dienstleister ein:

| Dienstleister | Aufgabe | Sitz |
|---|---|---|
| GitHub, Inc. | Hosting der Website, Ausführung der Versand-Automatisierung | USA |
| Cloudflare, Inc. | DNS, Cloudflare Workers, Workers KV, Datenbank | USA (mit Infrastruktur weltweit) |
| Resend | Versand der Newsletter-E-Mails | USA |

Mit Dienstleistern, die personenbezogene Daten in unserem Auftrag verarbeiten, schließen wir Verträge nach Art. 28 DSGVO.

Einige Dienstleister verarbeiten Daten in den USA. Die Übermittlung stützt sich auf den Angemessenheitsbeschluss der EU-Kommission zum EU-US Data Privacy Framework, sofern der Anbieter zertifiziert ist. Andernfalls gelten Standardvertragsklauseln der EU-Kommission. Die Partner nach Abschnitt 6 sind eigenständig verantwortlich.

---

## 13. Deine Rechte als betroffene Person

Du hast im Rahmen der Datenschutzgesetze jederzeit das Recht auf:

1. **Auskunft** (Art. 15 DSGVO): Informationen über die verarbeiteten Daten und eine Kopie davon
2. **Berichtigung** (Art. 16 DSGVO)
3. **Löschung** (Art. 17 DSGVO), sofern die Voraussetzungen vorliegen
4. **Einschränkung der Verarbeitung** (Art. 18 DSGVO)
5. **Datenübertragbarkeit** (Art. 20 DSGVO): Daten in einem maschinenlesbaren Format
6. **Widerspruch** (Art. 21 DSGVO) gegen die Verarbeitung auf Grundlage berechtigter Interessen
7. **Widerruf** erteilter Einwilligungen mit Wirkung für die Zukunft (Art. 7 Abs. 3 DSGVO)
8. **Beschwerde bei einer Aufsichtsbehörde** (Art. 77 DSGVO)

**Kontakt für deine Rechte:** kontakt@franksfinanzcheck.de

**Zuständige Aufsichtsbehörde:** Der Landesbeauftragte für Datenschutz und Informationsfreiheit Mecklenburg-Vorpommern, https://www.datenschutz-mv.de

Bei Direktwerbung kannst du der Verarbeitung jederzeit ohne Angabe von Gründen widersprechen (Art. 21 Abs. 2 DSGVO).

---

## 14. Pflicht zur Bereitstellung der Daten

Du bist nicht verpflichtet, personenbezogene Daten bereitzustellen. Für die Darstellung der Website übermittelt dein Browser jedoch technisch notwendige Daten wie die IP-Adresse. Ohne diese Daten ist die Website nicht nutzbar.

---

## 15. Widerspruch gegen Werbe-E-Mails

Der Nutzung der im Impressum veröffentlichten Kontaktdaten zur Übersendung nicht ausdrücklich angeforderter Werbung und Informationsmaterialien wird hiermit widersprochen. Der Betreiber behält sich rechtliche Schritte bei unverlangter Werbung, etwa Spam-E-Mails, ausdrücklich vor.

---

## 16. SSL-/TLS-Verschlüsselung

Diese Website nutzt eine SSL-/TLS-Verschlüsselung, erkennbar am Schloss-Symbol in der Adressleiste. Daten, die du an diese Website übermittelst, können so nicht von Dritten mitgelesen werden.

---

## 17. Automatisierte Entscheidungsfindung

Eine automatisierte Entscheidungsfindung einschließlich Profiling im Sinne des Art. 22 DSGVO findet auf dieser Website nicht statt.

---

## 18. Aktualität und Änderungen

**Stand: 11. Oktober 2026.** Diese Erklärung beschreibt die Verarbeitungen, wie sie in der Website angelegt sind. Ändern sich Dienste, Dienstleister, Partner oder Speicherfristen, passen wir die Erklärung an.
**Redaktioneller Stand: 11. Oktober 2026.** Diese Fassung bildet den geprüften Quellcode nach der Einbindung der Partner-Anbieterkennzeichnung im Impressum, der vorsorglichen Abschaltung der Reichweitenmessung und der Ergänzung der Newsletter-Löschroutine ab. Sie beschreibt nicht automatisch die bereits laufende Produktion: Vor dem Einsatz müssen Deployment, Verträge, Empfänger, Drittlandgarantien und tatsächliche Fristen durch den Betreiber überprüft und nötigenfalls hier nachgetragen werden. Ob das eingebettete Partnerdokument Cookies setzt, ist noch nicht an der Live-Antwort geprüft. Änderungen der Dienste oder des Geschäftsmodells erfordern eine erneute Prüfung.
