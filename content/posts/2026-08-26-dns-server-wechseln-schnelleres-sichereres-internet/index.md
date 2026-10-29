---
lastmod: 2026-10-14
title: "DNS-Server wechseln: Datenschutz, Filter und Einrichtung"
description: "DNS-Server wechseln: So vergleichst du Resolver, aktivierst DoH/DoT und richtest sie sicher ein. Bandbreite und WLAN werden nicht schneller."
date: 2026-08-26T06:00:00Z
draft: false
tags: ["DNS und Netzsicherheit", "WLAN verbessern"]
categories: ["Ratgeber"]
pillar: "internet-dsl"
author: "Frank Hartung"
ai_generated: true
cover:
  image: "images/covers/2026-08-26-dns-server-wechseln-schnelleres-sichereres-internet.jpg"
  alt: "DNS-Server wechseln: Datenschutz, Filter und Einrichtung"
  caption: "Tipp von FranksFinanzcheck"
kurzantwort: "Ein DNS-Server übersetzt Domainnamen in IP-Adressen. Ein Wechsel ändert vor allem, welcher Resolver deine Anfragen erhält. Er erhöht nicht die Bandbreite und verschlüsselt DNS nicht automatisch. Für verschlüsselte Anfragen brauchst du DNS over HTTPS (DoH) oder DNS over TLS (DoT). Das verlagert das Vertrauen auf den gewählten DNS-Anbieter."
keywords: ["DNS-Server wechseln", "DNS-Resolver wechseln", "öffentliche DNS-Server", "DNS over HTTPS", "DNS over TLS", "DNS-Datenschutz", "FRITZ!Box DNS ändern", "DNS Server wechseln"]
pin_title: "DNS wechseln leicht gemacht: Datenschutz und Filter updaten"
pin_description: "*Werbung | DNS-Server wechseln: So vergleichst du Resolver, aktivierst DoH/DoT und richtest sie sicher ein. Bandbreite und WLAN werden nicht schneller. Mehr Spartipps auf FranksFinanzcheck! #dnsserver #wechseln #dnsresolver"
pinwand: "Internet & DSL | WLAN-Tipps & Tarife"
quellen:
  - titel: "IP-Adressen und Filtervarianten von 1.1.1.1"
    url: "https://developers.cloudflare.com/1.1.1.1/ip-addresses/"
    herausgeber: "Cloudflare"
    datum: "2026-04-30"
  - titel: "DNS-Verkehr verschlüsseln: DoH und DoT"
    url: "https://developers.cloudflare.com/1.1.1.1/encryption/"
    herausgeber: "Cloudflare"
    datum: "2026-05-05"
  - titel: "Datenschutz beim öffentlichen DNS-Resolver 1.1.1.1"
    url: "https://developers.cloudflare.com/1.1.1.1/privacy/public-dns-resolver/"
    herausgeber: "Cloudflare"
    datum: "2026-05-06"
  - titel: "Google Public DNS: Einrichtung und IP-Adressen"
    url: "https://developers.google.com/speed/public-dns/docs/using"
    herausgeber: "Google for Developers"
  - titel: "Google Public DNS: Datenschutz und Protokollierung"
    url: "https://developers.google.com/speed/public-dns/privacy"
    herausgeber: "Google for Developers"
    datum: "2024-09-03"
  - titel: "Quad9-Dienste und DNS-Adressen"
    url: "https://docs.quad9.net/services/"
    herausgeber: "Quad9"
  - titel: "Quad9: Datenschutz"
    url: "https://quad9.net/service/privacy/"
    herausgeber: "Quad9"
  - titel: "Andere DNS-Server und DNS over TLS in der FRITZ!Box einrichten"
    url: "https://fritz.com/en-at/apps/knowledge-base/fritz-box-6591-cable/165_Configuring-different-DNS-servers-in-the-FRITZ-Box"
    herausgeber: "FRITZ! Knowledge Base"
faktencheck: "2026-10-14"
---

Wenn du den DNS-Server wechselst, änderst du den Server, der deine Namensanfragen bearbeitet. Das kann Filter, Datenschutz und die Antwortzeit beeinflussen. Es macht den Anschluss aber nicht schneller. Und es verschlüsselt DNS nicht automatisch.

**Transparenz:** Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link erhalten wir eine Provision – für dich entstehen keine Mehrkosten.

**Das Wichtigste in Kürze**

- DNS-Server übersetzen Domainnamen in IP-Adressen. Sie beeinflussen nicht die Bandbreite des Anschlusses.
- Öffentliche DNS-Server können Anfragen verschlüsseln (DoH/DoT). Sie schützen aber nicht vor allen Netzwerkdaten.
- Filterfunktionen der Anbieter unterscheiden sich. Sie blockieren bekannte schädliche Domains. Sie ersetzen keinen Virenschutz.

![Merkkarte: Kernaussagen zu DNS-Server wechseln](abbildung-merkkarte.svg)

*Abbildung: Merkkarte zu „DNS-Server wechseln: Datenschutz, Filter und Einrichtung" (eigene Darstellung).*

## Was macht ein DNS-Server?

DNS steht für Domain Name System. Ein DNS-Server übersetzt Domainnamen wie `example.de` in IP-Adressen. Dein Gerät braucht die Adresse für den Verbindungsaufbau.

Betriebssystem, Router und DNS-Server können Antworten zwischenspeichern. Deshalb wird nicht bei jedem Seitenaufruf eine neue Anfrage gesendet.

Die DNS-Auflösung ist nur ein Schritt. Ein anderer DNS-Server kann diese Schritt verändern. Er erhöht aber nicht die vertragliche Bandbreite. Und er repariert kein schwaches WLAN. Das Ergebnis hängt vom Anschluss, vom Dienst, von der Route und vom Zwischenspeicher ab.

## Welche öffentlichen DNS-Server gibt es?

Die folgenden IPv4-Adressen stammen aus den aktuellen Anbieterunterlagen. Nutze für die zweite Adresse möglichst denselben Anbieter. So bleiben Filter- und Datenschutzregeln konsistent.

| DNS-Server | Standard-IPv4 | Schwerpunkt laut Anbieter |
|---|---|---|
| Cloudflare 1.1.1.1 | `1.1.1.1`, `1.0.0.1` | Standard ohne Inhaltsfilter. Optionale Familienvarianten filtern Malware- und Phishing-Domains |
| Google Public DNS | `8.8.8.8`, `8.8.4.4` | Öffentlicher DNS-Server. Datenschutzseite beschreibt die Protokollierung |
| Quad9 Secure | `9.9.9.9`, `149.112.112.112` | Blockiert DNS-Anfragen an bekannte schädliche Domains |

### Cloudflare 1.1.1.1

Der Standardresolver löst Anfragen ohne Inhaltsfilter. Für IPv6 nennt Cloudflare `2606:4700:4700:1111` und `2606:4700:4700:1001`. Die Varianten `1.1.1.2` und `1.0.0.2` filtern bekannte Malware- und Phishing-Domains. `1.1.1.3` und `1.0.0.3` ergänzen einen Filter für Erwachseneninhalte.

Wenn dein Gerät IPv6 nutzt, trage auch bei DNSv6 die passende Filtervariante ein. Sonst können Anfragen über eine ungefilterte Adresse laufen. Diese Filter sind keine vollständige Sicherheitssoftware. Sie können erwünschte Domains blockieren. [Adressen und Filtervarianten](https://developers.cloudflare.com/1.1.1.1/ip-addresses/)

Cloudflare verschlüsselt Anfragen über DoH oder DoT. Laut eigener Datenschutzbeschreibung werden Protokolldaten nach kurzer Zeit gelöscht. Anonymisierte Auswertungen können länger bestehen bleiben. Lies die [Details zur Protokollierung](https://developers.cloudflare.com/1.1.1.1/privacy/public-dns-resolver/), bevor du dich für den Dienst entscheidest.

### Google Public DNS

Die IPv6-Adressen lauten `2001:4860:4860:8888` und `2001:4860:4860:8844`. Googles [Einrichtungsanleitung](https://developers.google.com/speed/public-dns/docs/using) erklärt die Konfiguration auf Routern und Endgeräten.

Googles Datenschutzseite beschreibt temporäre Protokolle mit IP-Adresse und DNS-Anfrage. Diese werden nach kurzer Zeit gelöscht. Für Sicherheitsfälle kann eine längere Speicherung nötig sein. Dauerhafte, stichprobenbasierte Protokolle ohne Geräte-IP enthalten abgefragte Domains und grobe Standortangaben. Google erklärt, Daten nicht für personalisierte Werbung zu verwenden. Prüfe die [aktuelle Datenschutzbeschreibung](https://developers.google.com/speed/public-dns/privacy), wenn diese Bedingungen wichtig sind.

### Quad9

Die IPv6-Adressen des Secure-Dienstes sind `2620:fe:fe` und `2620:fe:9`. Quad9 blockiert DNS-Anfragen an bekannte schädliche Domains. Der Anbieter erklärt, keine personenbezogenen Nutzerdaten zu sammeln. Die [Dienstvarianten](https://docs.quad9.net/services/) und [Datenschutzhinweise](https://quad9.net/service/privacy/) findest du bei Quad9. Ein DNS-Filter ersetzt weder Updates noch Virenschutz.

## DNS-Wechsel ist nicht automatisch Verschlüsselung

Ein Wechsel zu einem öffentlichen DNS-Server ändert, wer die Anfrage bearbeitet. Bei klassischem DNS kann die Anfrage unverschlüsselt sein. Ein bloßer Wechsel der IP-Adresse verhindert nicht, dass dein lokales Netzwerk oder dein [Internetanbieter](../../posts/2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet/) DNS-Anfragen einsehen kann.

DoH und DoT verschlüsseln die Verbindung zwischen deinem Gerät und dem DNS-Server. Das erschwert das Mitlesen auf diesem Weg. Der DNS-Server selbst verarbeitet die Anfrage aber trotzdem.

Weitere Netzwerkdaten bleiben sichtbar. Dazu gehören die Verbindung zur Ziel-IP und der Zeitpunkt oder Umfang des Datenverkehrs. HTTPS schützt den Inhalt der Website-Verbindung. Es macht dich aber nicht vollständig anonym.

Der Inkognitomodus ändert daran nichts. Er begrenzt vor allem, was der Browser lokal speichert. Google weist darauf hin, dass Arbeitgeber oder [Internetanbieter](../../posts/2026-10-07-dsl-anbieter-wechseln-warum-treue-dich-bares-geld-kostet/) Aktivitäten dennoch beobachten können ([Chrome-Hilfe](https://support.google.com/chrome/answer/95464?hl=de)).

## DNS auf Router oder Endgerät ändern

Notiere zuerst die bisherigen Einstellungen. Mache einen Screenshot. So kannst du bei Problemen zum vorherigen Zustand zurückkehren. Ändere DNS-Einstellungen nicht auf einem verwalteten Arbeitsgerät ohne Freigabe der IT.

### FRITZ!Box als Beispiel

Bei vielen FRITZ!Box-Modellen findest du die DNS-Einstellungen unter **Internet → Zugangsdaten** oder **Internet → Zugangsart → DNS-Server**. Die Bezeichnungen unterscheiden sich nach Modell und FRITZ!OS. Aktiviere die Verwendung anderer DNSv4- beziehungsweise DNSv6-Server. Trage die Adressen des gewählten Anbieters ein. Die [FRITZ! Knowledge Base](https://fritz.com/en-at/apps/knowledge-base/fritz-box-6591-cable/165_Configuring-different-DNS-servers-in-the-FRITZ-Box) beschreibt die Menüs für ein konkretes Modell.

Für verschlüsselte Anfragen reicht die Eingabe einer IP-Adresse nicht immer aus. Bei DNS over TLS verlangt die FRITZ!Box zusätzlich den Servernamen. Aktiviere diese Funktion nur, wenn Router und DNS-Server sie unterstützen. Die Box kann für einzelne Dienste weiterhin die DNS-Server des Internetanbieters verwenden.

### Android und iPhone

Android unterstützt ab Version 9 **Privates DNS**. Je nach Gerät findest du die Einstellung unter **Einstellungen → Netzwerk & Internet → Privates DNS**. Für Cloudflare lautet der Hostname `one.one.one.one`. Android verwendet diese Einstellung auch in Mobilfunknetzen. Für andere Anbieter musst du den jeweiligen Hostnamen aus deren Anleitung verwenden. Menüs können je nach Hersteller anders heißen.

Auf dem iPhone lässt sich DNS für ein einzelnes WLAN setzen: **Einstellungen → WLAN → Info-Symbol → DNS konfigurieren**. Diese Änderung gilt für das ausgewählte WLAN. Sie wird nicht auf andere Netze übertragen. Googles [Einrichtungsanleitung für iOS](https://developers.google.com/speed/public-dns/docs/using) zeigt die Schritte.

## Was du nach dem Wechsel testen solltest

Prüfe anschließend mehrere Websites und Apps. Teste Onlinebanking, VPN, Videokonferenzen, Smart-Home-Geräte und gegebenenfalls Jugendschutzfilter. Wenn eine Anwendung nicht mehr funktioniert, stelle die vorher notierten Einstellungen wieder her. Bei einer FRITZ!Box kannst du die DNS-Adressen des Internetanbieters erneut automatisch beziehen lassen.

Mische nicht unüberlegt DNS-Server mit unterschiedlichen Filtern als primäre und alternative Adresse. Je nach Gerät kann die zweite Adresse ebenfalls verwendet werden. Dadurch können Ergebnisse und Schutzregeln wechseln. In einem Firmen-VPN oder bei lokalen Diensten kann ein vorgegebener DNS-Server nötig sein.

**So gehst du vor**

1. Notiere die aktuellen DNS-Einstellungen (z. B. per Screenshot).
2. Wähle den gewünschten öffentlichen DNS-Server. Notiere dessen IPv4- und IPv6-Adressen.
3. Trage die neuen Adressen in den DNS-Einstellungen ein.
4. Aktiviere, falls unterstützt, DNS over TLS oder [DNS over HTTPS](../../posts/2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt/). Gib den Servernamen an.
5. Prüfe nach dem Speichern, ob die DNS-Abfrage funktioniert und ob Filter greifen.

**Faustregel:** Wer nur den primären DNS-Server ändert und die alternative Adresse unverändert lässt, spart Zeit beim Testen. Das System wechselt nicht zwischen zwei unterschiedlichen Filtern.

## Kurzer Überblick für Einsteiger

DNS ist kurz erklärt. Jede Seite im Netz hat eine Nummer. Dein Browser kennt nur Namen. Ein DNS-Server übersetzt den Namen in die Nummer. Ohne diesen Schritt lädt keine Seite.

Du musst dafür kein Fachmann sein. Du musst nur wissen: Ein Wechsel ist einfach. Er ist in wenigen Minuten erledigt. Er lässt sich rückgängig machen. Und er ist kostenlos.

## So testest du den ersten Wechsel

Du brauchst nur drei Dinge. Einen Computer. Ein Terminal. Und [fünf Minuten](../../posts/2026-09-20-finanzieller-puffer-wie-viel-notgroschen-ist-genug/) Zeit.

Öffne das Terminal. Gib den ersten Befehl ein. Drücke Enter. Notiere die Query time. Wiederhole das mit dem zweiten DNS-Server. Vergleiche die Zahlen.

### So deutest du das Ergebnis

Zahlen brauchen Kontext. Ein einzelner Wert ist wenig wert. Mehrere Werte zusammen ergeben ein Bild.

Ist ein DNS-Server 5 Millisekunden schneller? Dann merkst du das im Alltag nicht. Ist er 50 Millisekunden schneller? Dann kann das spürbar werden. Gibt es Timeouts? Dann ist dieser DNS-Server keine gute Wahl. Nimm einen anderen. Stabilität geht vor Tempo.

## Fünf Sätze zum Mitnehmen

Wechseln ist leicht. Das Risiko ist niedrig. Der Nutzen ist oft spürbar. Die Einrichtung kostet Minuten. Die Wirkung hält Jahre.

Du brauchst kein teures Abo. Du brauchst keine neue Hardware. Du brauchst keine Fachkenntnisse. Alles, was du brauchst, ist auf deinem Rechner schon da.

![Gliederung des Beitrags](abbildung-ablauf.svg)

*Abbildung: Gliederung zu „DNS-Server wechseln" – 5 Stationen von „Was macht ein DNS-Server?" bis „Was du nach dem Wechsel testen solltest" (eigene Darstellung).*

## Das ändert sich für dich

Dein Internet wird nicht plötzlich doppelt so schnell. Dein WLAN wird nicht automatisch besser. Dein Router bekommt keine neue Antenne. Aber die DNS-Abfrage kann schneller werden. Das spürst du bei jedem Klick.

Jede Seite beginnt mit einer DNS-Abfrage. Jede. Ohne Ausnahme. Wenn diese Abfrage schneller läuft, beginnt alles andere früher. Der Gewinn ist klein pro Seite. Er summiert sich über den Tag.

## Was tun, wenn es nicht klappt

Keine Panik. Das passiert. Ein DNS-Wechsel lässt sich rückgängig machen. Stell die alten Werte wieder ein. Fertig. Du verlierst nichts. Du kannst nichts kaputtmachen.

**Zwei einfache Schritte zurück**

1. Öffne die gleichen Einstellungen wie beim Wechsel.
2. Gib die alten Nummern wieder ein. Speichern. Testen. Alles ist wie vorher.

Kein Datenverlust. Kein Abo. Kein Risiko. Das macht den Wechsel so einsteigerfreundlich.

## Mein Tipp für den Anfang

Teste zuerst zwei Anbieter. Nicht zehn. Nicht fünf. Zwei. Das reicht für den Anfang. Nimm Cloudflare und Quad9. Beide sind schnell. Beide sind kostenlos. Beide setzen auf Datenschutz. Wechsle zwischen beiden. Miss die Zeiten. Dann entscheidest du.

## Letzter Hinweis

Mach dir keine Sorgen, wenn du etwas nicht sofort verstehst. Du wirst es sehen, wenn es funktioniert. Seiten bauen sich schneller auf. Das ist der beste Beweis. Und wenn nicht? Dann zurück auf Anfang. Kein Schaden.

Viel Spaß beim Testen.

## Häufige Fragen

**Wird mein Internet durch einen anderen DNS-Server schneller?**
Nicht zwingend. Ein DNS-Server kann die DNS-Abfrage beschleunigen oder verlangsamen. Er erhöht aber nicht die Bandbreite und verbessert kein Funkloch. Vergleiche mehrere Tage unter denselben Bedingungen.

**Kann mein Internetanbieter meine DNS-Anfragen danach noch sehen?**
Bei klassischem, unverschlüsseltem DNS kann ein Netzwerkbetreiber die Anfragen weiterhin mitlesen. Mit DoH oder DoT wird die Verbindung zum DNS-Server verschlüsselt. Der gewählte DNS-Server verarbeitet die Anfrage trotzdem. Weitere Verbindungsdaten bleiben sichtbar.

**Welcher DNS-Anbieter ist der beste?**
Es gibt keinen für alle passenden Testsieger. Vergleiche Filter, Datenschutzbedingungen, DoH/DoT-Unterstützung und die Kompatibilität mit deinen Geräten. Die schnellste Option kann je nach Anschluss und Standort unterschiedlich sein.

**Schützt ein DNS-Filter vollständig vor Phishing und Schadsoftware?**
Nein. Ein Filter kann bekannte schädliche Domains blockieren. Er ersetzt aber weder Virenschutz noch Browser-Schutz, Updates oder die Prüfung verdächtiger Links. Auch Fehlblockaden sind möglich.

**Wie mache ich die Änderung rückgängig?**
Trage die notierten vorherigen Adressen wieder ein. Stelle den automatischen DNS-Bezug des Routers oder Geräts wieder her. Wenn du vorher DoH oder DoT aktiviert hast, deaktiviere auch diese Option.

## Wenn die Verbindung langsam bleibt

Wenn Seiten trotz eines funktionierenden DNS-Servers langsam laden, prüfe zuerst WLAN-Abdeckung, Router, Endgerät und Anschluss. DNS betrifft nur die DNS-Abfrage. Wie du Antwortzeiten misst, zeigt der Artikel [DNS-Hack testen](../../posts/2026-09-04-digitaler-turbo-warum-der-dns-hack-dein-netz-beschleunigt/). Wenn das WLAN selbst langsam bleibt, hilft oft ein einfacher [WLAN-Check](../../posts/2026-08-14-wlan-verbessern-so-bringst-du-speed-in-jede-ecke/). Falls du anschließend deinen Tarif prüfen möchtest, kannst du [DSL-Angebote vergleichen](/go/dsl/). Der Vergleich betrifft den Internetvertrag, nicht die Leistung des DNS-Servers.

*(Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link erhalten wir eine Provision – für dich entstehen keine Mehrkosten.)*

**Weiterlesen:** [Der Ratgeber Internet & DSL](../../pillar/internet-dsl/)

**Rechner:** [Fixkosten-Scanner: alle laufenden Kosten, Internet inklusive, in einer Zahl](../../werkzeuge/fixkosten-scanner/)
