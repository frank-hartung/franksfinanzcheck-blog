---
lastmod: 2026-10-14
title: "DNS-Server wechseln: Datenschutz, Filter und Einrichtung"
description: "DNS-Server wechseln kann Datenschutz und Filter verändern, nicht die Bandbreite. So vergleichst du Resolver, DoH/DoT und richtest sie sicher ein."
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
kurzantwort: "Ein DNS-Server übersetzt Domainnamen in IP-Adressen. Ein Wechsel ändert vor allem, welcher Resolver deine Anfragen erhält; er erhöht weder die Bandbreite noch verschlüsselt er DNS automatisch. Für verschlüsselte Anfragen brauchst du DNS over HTTPS (DoH) oder DNS over TLS (DoT). Dabei verlagert sich das Vertrauen auf den gewählten DNS-Anbieter."

social_posted: true
keywords: ["DNS-Server wechseln", "DNS-Resolver wechseln", "öffentliche DNS-Server", "DNS over HTTPS", "DNS over TLS", "DNS-Datenschutz", "FRITZ!Box DNS ändern"]
pin_title: "DNS-Server wechseln: Was es kann – und was nicht"
pin_description: "*Werbung | Ein anderer DNS-Resolver kann Filter und Zuständigkeiten ändern, aber keine Bandbreite zaubern. Vergleiche Datenschutz, Verschlüsselung und Anbieterbedingungen."
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
  - titel: "Im Inkognitomodus surfen"
    url: "https://support.google.com/chrome/answer/95464?hl=de"
    herausgeber: "Google Chrome-Hilfe"
  - titel: "Verschlüsseltes DNS unter Android einrichten"
    url: "https://developers.cloudflare.com/1.1.1.1/setup/android/"
    herausgeber: "Cloudflare"
    datum: "2026-06-23"
faktencheck: "2026-10-14"
---

Wenn du den DNS-Server wechseln möchtest, änderst du zunächst den Resolver, an den dein Gerät seine Namensanfragen schickt. Das kann Filter, Datenschutzbedingungen und die Antwortzeit bei einer Namensauflösung beeinflussen. Es macht deinen Internetanschluss aber nicht automatisch schneller oder anonymer.

## Was ein DNS-Server macht

DNS steht für Domain Name System. Ein Resolver übersetzt einen Domainnamen wie `example.de` in eine IP-Adresse, die dein Gerät für den Verbindungsaufbau benötigt. Betriebssystem, Router und Resolver können Antworten zwischenspeichern. Deshalb wird nicht bei jedem Seitenaufruf eine neue DNS-Anfrage gesendet.

Die DNS-Auflösung ist nur ein Schritt vor der Verbindung zur Website. Ein anderer Resolver kann die Dauer dieses Schritts verändern, aber weder die vertragliche Bandbreite erhöhen noch ein schwaches WLAN reparieren. Das Ergebnis hängt unter anderem von deinem Anschluss, dem gewählten Dienst, der Route und dem Zwischenspeicher ab. Eine allgemeingültige Rangliste der schnellsten Anbieter gibt es für jeden Haushalt nicht.

## Öffentliche DNS-Resolver im Vergleich

Die folgenden IPv4-Adressen stammen aus den aktuellen Anbieterunterlagen. Nutze für die zweite Adresse möglichst denselben Anbieter. So bleiben Filter- und Datenschutzregeln konsistent, falls dein Gerät beide Resolver verwendet.

| Resolver | Standard-IPv4 | Schwerpunkt laut Anbieter |
|---|---|---|
| Cloudflare 1.1.1.1 | `1.1.1.1`, `1.0.0.1` | Standard ohne Inhaltsfilter; optionale Familienvarianten filtern bekannte Malware- und Phishing-Domains, teils auch Erwachseneninhalte |
| Google Public DNS | `8.8.8.8`, `8.8.4.4` | Öffentlicher Resolver; Googles Datenschutzseite beschreibt die Protokollierung von Anfragen |
| Quad9 Secure | `9.9.9.9`, `149.112.112.112` | Blockiert laut Quad9 DNS-Anfragen an bekannte schädliche Domains |

### Cloudflare 1.1.1.1

Der Standardresolver löst DNS-Anfragen ohne Inhaltsfilter auf. Für IPv6 nennt Cloudflare `2606:4700:4700::1111` und `2606:4700:4700::1001`. Die Varianten `1.1.1.2` und `1.0.0.2` filtern laut Anbieter bekannte Malware- und Phishing-Domains. `1.1.1.3` und `1.0.0.3` ergänzen einen Filter für Erwachseneninhalte. Die entsprechenden IPv6-Adressen sind `2606:4700:4700::1112` und `2606:4700:4700::1002` beziehungsweise `2606:4700:4700::1113` und `2606:4700:4700::1003`. Wenn dein Gerät IPv6 nutzt, trage auch bei DNSv6 die passende Filtervariante ein; sonst können Anfragen über eine ungefilterte IPv6-Adresse laufen. Diese Filter sind keine vollständige Sicherheitssoftware und können erwünschte Domains blockieren. [Adressen und Filtervarianten](https://developers.cloudflare.com/1.1.1.1/ip-addresses/)

Cloudflare dokumentiert, dass der Resolver Anfragen verschlüsselt über DoH oder DoT entgegennehmen kann. Laut eigener Datenschutzbeschreibung werden bestimmte Resolver-Protokolldaten innerhalb von 25 Stunden gelöscht; anonymisierte aggregierte Auswertungen können länger bestehen bleiben. Lies die [Details zur Protokollierung](https://developers.cloudflare.com/1.1.1.1/privacy/public-dns-resolver/), bevor du dich für den Dienst entscheidest.

### Google Public DNS

Die IPv6-Adressen lauten `2001:4860:4860::8888` und `2001:4860:4860::8844`. Googles [Einrichtungsanleitung](https://developers.google.com/speed/public-dns/docs/using) erklärt die Konfiguration auf Routern und Endgeräten.

Googles Datenschutzseite beschreibt temporäre Protokolle, die IP-Adresse und DNS-Anfrage enthalten und normalerweise innerhalb von 24 bis 48 Stunden gelöscht werden. Für Sicherheits- oder Missbrauchsfälle kann eine begrenzte längere Speicherung nötig sein. Daneben nennt Google dauerhafte, stichprobenbasierte Protokolle ohne Geräte-IP, die unter anderem abgefragte Domains, technische DNS-Daten und grobe Standortangaben auf Stadt- oder Regionsebene enthalten. Google erklärt, Daten aus Public DNS nicht für personalisierte Werbung zu verwenden. Prüfe die [aktuelle Datenschutzbeschreibung](https://developers.google.com/speed/public-dns/privacy), wenn diese Bedingungen für deine Wahl wichtig sind.

### Quad9

Die IPv6-Adressen des Secure-Dienstes sind `2620:fe::fe` und `2620:fe::9`. Quad9 beschreibt den Dienst als Schutz vor DNS-Anfragen an bekannte schädliche Domains. Der Anbieter erklärt, keine personenbezogenen Nutzerdaten zu sammeln. Die konkreten [Dienstvarianten](https://docs.quad9.net/services/) und die [Datenschutzhinweise](https://quad9.net/service/privacy/) findest du bei Quad9. Auch ein DNS-Filter ersetzt weder Updates noch Virenschutz oder umsichtiges Verhalten.

## DNS-Wechsel ist nicht automatisch Verschlüsselung

Ein Wechsel von den DNS-Adressen deines Internetanbieters zu einem öffentlichen Resolver ändert, wer die Anfrage bearbeitet. Wird klassisches DNS verwendet, kann die Anfrage auf dem Weg zum Resolver weiterhin unverschlüsselt sein. Ein bloßer Wechsel der IP-Adresse verhindert daher nicht zuverlässig, dass dein lokales Netzwerk oder dein Internetanbieter DNS-Anfragen einsehen kann.

DoH und DoT verschlüsseln die DNS-Verbindung zwischen deinem Gerät beziehungsweise Router und dem gewählten Resolver. Das erschwert das Mitlesen auf diesem Übertragungsweg. Der Resolver selbst muss die Anfrage aber verarbeiten. Außerdem bleiben andere Netzwerkdaten sichtbar, etwa die Verbindung zu einer Ziel-IP und Zeitpunkt oder Umfang des Datenverkehrs. HTTPS schützt den Inhalt der Verbindung zur Website, macht dich aber nicht vollständig anonym.

Auch der Inkognitomodus ändert daran nichts: Er begrenzt vor allem, was der Browser lokal speichert. Google weist darauf hin, dass besuchte Websites und Netzwerkbetreiber wie Arbeitgeber oder Internetanbieter Aktivitäten dennoch beobachten können ([Chrome-Hilfe](https://support.google.com/chrome/answer/95464?hl=de)).

## DNS auf Router oder Endgerät ändern

Notiere zuerst die bisherigen Einstellungen oder mache einen Screenshot. So kannst du bei Problemen zum vorherigen Zustand zurückkehren. Ändere DNS-Einstellungen nicht auf einem verwalteten Arbeitsgerät oder in einem Firmennetz ohne Freigabe der IT.

### FRITZ!Box als Beispiel

Bei vielen FRITZ!Box-Modellen findest du die DNS-Einstellungen unter **Internet → Zugangsdaten** oder **Internet → Zugangsart → DNS-Server**. Die Bezeichnungen und verfügbaren Optionen unterscheiden sich nach Modell, FRITZ!OS und Anbieter. Aktiviere die Verwendung anderer DNSv4- beziehungsweise DNSv6-Server und trage die Adressen des gewählten Anbieters ein. Die [FRITZ! Knowledge Base](https://fritz.com/en-at/apps/knowledge-base/fritz-box-6591-cable/165_Configuring-different-DNS-servers-in-the-FRITZ-Box) beschreibt die Menüs für ein konkretes Modell.

Wenn du verschlüsselte Anfragen nutzen möchtest, reicht die Eingabe einer IP-Adresse nicht immer aus. Bei DNS over TLS verlangt die FRITZ!Box zusätzlich den passenden Servernamen. Aktiviere diese Funktion nur, wenn dein Router und der gewählte Resolver sie unterstützen. Laut FRITZ! kann die Box für einzelne Dienste weiterhin die DNS-Server des Internetanbieters verwenden; bei manchen Kabelanschlüssen fehlt die Einstellung ganz.

### Android und iPhone

Android unterstützt ab Version 9 **Privates DNS** mit verschlüsselten Anfragen. Je nach Gerät findest du die Einstellung unter **Einstellungen → Netzwerk & Internet → Privates DNS**. Für Cloudflare lautet der dokumentierte Hostname `one.one.one.one`; Android verwendet diese Einstellung laut [Cloudflare-Anleitung](https://developers.cloudflare.com/1.1.1.1/setup/android/) auch in Mobilfunknetzen. Für andere Anbieter musst du den jeweiligen Hostnamen aus deren Anleitung verwenden. Menüs können je nach Hersteller anders heißen.

Auf dem iPhone lässt sich DNS für ein einzelnes WLAN unter **Einstellungen → WLAN → Info-Symbol → DNS konfigurieren** manuell setzen. Diese Änderung gilt für das ausgewählte WLAN und wird nicht automatisch auf jedes andere Netz übertragen. Googles [Einrichtungsanleitung für iOS](https://developers.google.com/speed/public-dns/docs/using) zeigt die Schritte am Beispiel von Google Public DNS. Für andere Systeme nutze die jeweils aktuelle Anleitung des Geräte- oder Resolver-Anbieters.

## Was du nach dem Wechsel testen solltest

Prüfe anschließend mehrere Websites und Apps. Teste auch Onlinebanking, VPN, Videokonferenzen, Smart-Home-Geräte und gegebenenfalls Jugendschutzfilter. Wenn eine Anwendung nicht mehr funktioniert, stelle zunächst die vorher notierten Einstellungen wieder her. Bei einer FRITZ!Box kannst du die DNS-Adressen des Internetanbieters erneut automatisch beziehen lassen.

Mische nicht unbedacht Resolver mit unterschiedlichen Filtern als primäre und alternative Adresse. Je nach Gerät kann die zweite Adresse ebenfalls verwendet werden; dadurch können Ergebnisse und Schutzregeln wechseln. In einem Firmen-VPN oder bei lokalen Diensten kann außerdem ein vorgegebener DNS-Resolver nötig sein.

## Häufige Fragen

### Wird mein Internet durch einen anderen DNS-Server schneller?
Nicht zwingend. Ein Resolver kann die Namensauflösung in manchen Situationen beschleunigen oder verlangsamen. Er erhöht aber nicht die Bandbreite und verbessert kein Funkloch. Vergleiche mehrere Tage unter denselben Bedingungen, statt dich auf einen pauschalen Millisekundenwert zu verlassen.

### Kann mein Internetanbieter meine DNS-Anfragen danach noch sehen?
Bei klassischem, unverschlüsseltem DNS kann ein Netzwerkbetreiber die Anfragen weiterhin mitlesen. Mit DoH oder DoT wird die Verbindung zum Resolver verschlüsselt; der gewählte Resolver verarbeitet die Anfrage trotzdem. Auch andere Verbindungsdaten bleiben sichtbar.

### Welcher DNS-Anbieter ist der beste?
Es gibt keinen für alle passenden Testsieger. Vergleiche Filter, Datenschutzbedingungen, Unterstützung für DoH oder DoT und die Kompatibilität mit deinen Geräten. Die schnellste Option kann je nach Anschluss und Standort unterschiedlich sein.

### Schützt ein DNS-Filter vollständig vor Phishing und Schadsoftware?
Nein. Ein Filter kann laut Anbieter bekannte schädliche Domains blockieren. Er ersetzt aber weder Virenschutz noch Browser-Schutz, Updates oder eine Prüfung verdächtiger Links. Auch Fehlblockaden sind möglich.

### Wie mache ich die Änderung rückgängig?
Trage die notierten vorherigen Adressen wieder ein oder stelle den automatischen DNS-Bezug des Routers beziehungsweise Geräts wieder her. Wenn du vorher DoH oder DoT aktiviert hast, deaktiviere auch diese Option.

## Wenn die Verbindung langsam bleibt

Wenn Seiten trotz eines funktionierenden Resolvers langsam laden, prüfe zuerst WLAN-Abdeckung, Router, Endgerät und Anschluss. DNS betrifft nur die Namensauflösung. Falls du anschließend deinen Tarif prüfen möchtest, kannst du [DSL-Angebote vergleichen](/go/dsl/). Der Vergleich betrifft den Internetvertrag, nicht die Leistung des DNS-Servers.

*(Dieser Artikel enthält Affiliate-Links (Werbung). Beim Abschluss über einen Link erhalten wir eine Provision – für dich entstehen keine Mehrkosten.)*

**Weiterlesen:** [Der Ratgeber Internet & DSL](../../pillar/internet-dsl/)
